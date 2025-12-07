"""Chat API routes using SmartDataAgentRunner."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.agents import SmartDataAgentRunner
from app.agents.manager import ChatManager


class ChatMessage(BaseModel):
    """Chat message for API requests."""
    content: str = Field(..., description="The message content")


class StartChatRequest(BaseModel):
    """Request to start a new chat."""
    content: str = Field(..., description="The message content")
    city: str = Field(default="boston", description="City name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class ContinueChatRequest(BaseModel):
    """Request to continue an existing chat."""
    content: str = Field(..., description="The message content")
    latitude: Optional[float] = Field(None, description="New latitude (for mode switch)")
    longitude: Optional[float] = Field(None, description="New longitude (for mode switch)")


router = APIRouter(prefix="/chats", tags=["chat"])

# Use gemini-2.0-flash as the model name for chat manager
AGENT_MODEL = "gemini-2.0-flash"
chat_manager = ChatManager(model=AGENT_MODEL)


@router.get("/")
async def get_chats(
    x_session_id: str = Header(None, alias="X-Session-ID"),
    limit: Optional[int] = None,
):
    """Get all chats for a session."""
    session_id = x_session_id or "default"
    return chat_manager.get_recent_chats(session_id=session_id, limit=limit)


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Get a chat by id."""
    session_id = x_session_id or "default"
    chat = chat_manager.get_chat(chat_id=chat_id, session_id=session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("/")
async def start_chat(
    request: StartChatRequest,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Start a new chat with the SmartDataAgent."""
    session_id = x_session_id or "default"
    chat_id = str(uuid.uuid4())

    # Clear context for this chat before running
    chat_manager.clear_context(chat_id, session_id)

    # Create the agent runner
    runner = SmartDataAgentRunner(
        city=request.city,
        latitude=request.latitude,
        longitude=request.longitude,
        model=AGENT_MODEL,
        session_id=session_id,
        chat_id=chat_id,
        chat_manager=chat_manager,
    )

    # Run the agent
    await runner.run(request.content)

    # Get sources from the runner's context
    agent_context = runner.get_agent_context()
    ordinance_sources = agent_context.get_store("ordinances").to_dict_list()
    development_plan_sources = agent_context.get_store("development_plans").to_dict_list()

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Chat response sources: {len(ordinance_sources)} ordinances, {len(development_plan_sources)} dev plans")

    # Generate title from first message
    title = request.content[:50]
    if len(request.content) > 50:
        title += "..."

    # Save to disk
    runner.save_to_disk(title=title)

    # Build response
    chat_response = {
        "chat_id": chat_id,
        "title": title,
        "dts": int(time.time()),
        "messages": runner.get_history(),
        "context": {
            "city": runner.city,
            "latitude": runner.latitude,
            "longitude": runner.longitude,
            "agent_type": runner.agent_type,
        },
        "ordinance_sources": ordinance_sources,
        "development_plan_sources": development_plan_sources,
    }

    return chat_response


@router.post("/{chat_id}")
async def continue_chat(
    chat_id: str,
    request: ContinueChatRequest,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Continue an existing chat."""
    session_id = x_session_id or "default"

    # Load existing chat
    chat = chat_manager.get_chat(chat_id=chat_id, session_id=session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Get context from saved chat
    context = chat.get("context", {})
    city = context.get("city", "boston")
    saved_latitude = context.get("latitude")
    saved_longitude = context.get("longitude")

    # Check if user wants to switch modes
    new_latitude = request.latitude
    new_longitude = request.longitude

    # Clear context for this chat before running
    chat_manager.clear_context(chat_id, session_id)

    # Create runner with saved context
    runner = SmartDataAgentRunner(
        city=city,
        latitude=saved_latitude,
        longitude=saved_longitude,
        model=AGENT_MODEL,
        session_id=session_id,
        chat_id=chat_id,
        chat_manager=chat_manager,
    )

    # Restore history
    runner.set_history(chat.get("messages", []))

    # Handle mode switching
    if new_latitude is not None and new_longitude is not None:
        # User selected a new location
        if saved_latitude != new_latitude or saved_longitude != new_longitude:
            # switch_to_location_mode replays history with location change notice
            await runner.switch_to_location_mode(
                latitude=new_latitude,
                longitude=new_longitude,
            )
        else:
            # Same location, replay history
            await runner.replay_history()
    else:
        # No location or same as before, replay history
        await runner.replay_history()

    # Run the agent
    await runner.run(request.content)

    # Get sources from the runner's context
    agent_context = runner.get_agent_context()
    ordinance_sources = agent_context.get_store("ordinances").to_dict_list()
    development_plan_sources = agent_context.get_store("development_plans").to_dict_list()

    # Save to disk
    runner.save_to_disk(title=chat.get("title"))

    # Build response
    chat_response = {
        "chat_id": chat_id,
        "title": chat.get("title"),
        "dts": int(time.time()),
        "messages": runner.get_history(),
        "context": {
            "city": runner.city,
            "latitude": runner.latitude,
            "longitude": runner.longitude,
            "agent_type": runner.agent_type,
        },
        "ordinance_sources": ordinance_sources,
        "development_plan_sources": development_plan_sources,
    }

    return chat_response


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Delete a chat."""
    session_id = x_session_id or "default"
    success = chat_manager.delete_chat(chat_id=chat_id, session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "deleted", "chat_id": chat_id}
