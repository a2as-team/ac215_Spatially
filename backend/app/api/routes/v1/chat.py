import time
from app.utils.chat.history_manager import ChatHistoryManager, ChatMessage
from app.utils.chat.llm_chat_client import LLMChatClient
from app.utils.chat.model_config import LLM_GENERIC_MODEL
import uuid
from app.utils.chat.system_config import ZONING_CHAT_SYSTEM_INSTRUCTIONS
from fastapi import APIRouter, HTTPException, Query, Header
from typing import List, Dict, Any, Optional
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery
from app.core.config import settings

router = APIRouter(prefix="/chats", tags=["chat"])

chat_manager = ChatHistoryManager(model=LLM_GENERIC_MODEL)

DEFAULT_SESSION_ID = "default"


@router.get("/")
async def get_chats(
    x_session_id: str = Header(None, alias="X-Session-ID"), limit: Optional[int] = None
):
    """Get all chats for a session"""
    # Use default session if none provided
    session_id = x_session_id or "default"
    print(f"Getting chats for session {session_id}")
    return chat_manager.get_recent_chats(session_id=session_id, limit=limit)


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Get a chat by id"""
    # Use default session if none provided
    session_id = x_session_id or "default"
    print(f"Getting chat {chat_id} for session {session_id}")
    chat = chat_manager.get_chat(chat_id=chat_id, session_id=session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("/")
async def start_chat(
    message: ChatMessage,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    # Use default session if none provided
    session_id = x_session_id or "default"
    message_dict = message.model_dump()
    print("content:", message_dict["content"])
    print("session_id:", session_id)
    chat_id = str(uuid.uuid4())
    current_time = int(time.time())

    chat_client = LLMChatClient(
        model=LLM_GENERIC_MODEL, system_instructions=ZONING_CHAT_SYSTEM_INSTRUCTIONS
    )
    # create a new chat session
    chat_session = chat_client.create_chat_session()

    # Add id and role to the user message
    message_dict["message_id"] = str(uuid.uuid4())
    message_dict["role"] = "user"

    assistant_response = chat_client.generate_response(
        chat_session=chat_session, message=message_dict
    )

    # Create a chat response
    title = message_dict.get("content")
    if title == "":
        title = "Image chat"
    title = title[:50] + "..." if len(title) > 50 else title
    chat_response = {
        "chat_id": chat_id,
        "title": title,
        "dts": current_time,
        "messages": [
            message_dict,
            {
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": assistant_response,
            },
        ],
    }

    # Save the chat response
    chat_manager.save_chat(chat_to_save=chat_response, session_id=session_id)
    return chat_response


@router.post("/{chat_id}")
async def continue_chat(
    chat_id: str,
    message: ChatMessage,
    x_session_id: str = Header(None, alias="X-Session-ID"),
):
    """Continue a chat"""
    # Use default session if none provided
    session_id = x_session_id or "default"
    message_dict = message.model_dump()
    print("content:", message_dict["content"])
    print("session_id:", session_id)
    chat = chat_manager.get_chat(chat_id=chat_id, session_id=session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat_client = LLMChatClient(
        model=LLM_GENERIC_MODEL, system_instructions=ZONING_CHAT_SYSTEM_INSTRUCTIONS
    )

    chat_session = chat_client.rebuild_chat_session(chat_history=chat["messages"])

    # Update timestamp
    current_time = int(time.time())
    chat["dts"] = current_time

    # Add message Id and role
    message_dict["message_id"] = str(uuid.uuid4())
    message_dict["role"] = "user"

    # Generate response
    assistant_response = chat_client.generate_response(
        chat_session=chat_session, message=message_dict
    )

    # Add assistant response to chat
    chat["messages"].append(message_dict)
    chat["messages"].append(
        {
            "message_id": str(uuid.uuid4()),
            "role": "assistant",
            "content": assistant_response,
        }
    )
    chat_manager.save_chat(chat_to_save=chat, session_id=session_id)
    return chat
