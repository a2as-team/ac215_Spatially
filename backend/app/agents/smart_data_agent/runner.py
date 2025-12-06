"""Runner for the Smart Data Agents with session management.

This module provides a runner class that:
1. Manages agent sessions with Google ADK
2. Supports switching between LocationDataAgent and CityDataAgent
3. Transfers chat history when switching agent modes
4. Optionally persists history using ChatHistoryManager

Note on InMemorySessionService:
    Google ADK's InMemorySessionService stores sessions in RAM only.
    Sessions are lost when the server restarts. For persistence,
    use the ChatHistoryManager integration or get_context()/from_context().
"""

import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.location_data_agent import LocationDataAgent
from app.agents.city_data_agent import CityDataAgent
from app.agents.manager import ChatManager, AgentContext, set_current_context
from app.agents.config import ensure_configured


@dataclass
class ChatMessage:
    """Represents a chat message in the conversation history."""
    role: str  # "user" or "assistant"
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class SmartDataAgentRunner:
    """Runner for Smart Data Agents with session and history management.

    This runner handles:
    1. Creating the appropriate agent (location-based or city-based)
    2. Managing conversation sessions
    3. Transferring history when switching between agent modes

    Usage:
        # Create a location-based runner
        runner = SmartDataAgentRunner(
            city="boston",
            latitude=42.3601,
            longitude=-71.0589,
        )

        # Run a query
        response = await runner.run("What can I build here?")

        # User deselects location, switch to city mode
        await runner.switch_to_city_mode()

        # Continue conversation (history is transferred to new agent)
        response = await runner.run("What about in residential zones?")
    """

    def __init__(
        self,
        city: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        model: str = "gemini-2.0-flash",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        chat_manager: Optional[ChatManager] = None,
        agent_context: Optional[AgentContext] = None,
    ):
        """
        Initialize the runner.

        Args:
            city: City name (required)
            latitude: Optional latitude for location-based queries
            longitude: Optional longitude for location-based queries
            model: Gemini model to use
            session_id: Optional session ID for continuity
            user_id: Optional user ID
            chat_id: Optional chat ID for persistence
            chat_manager: Optional ChatManager for disk persistence and context
            agent_context: Optional AgentContext (if not using ChatManager)
        """
        self.city = city.lower()
        self.latitude = latitude
        self.longitude = longitude
        self.model = model
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or str(uuid.uuid4())
        self.chat_id = chat_id or str(uuid.uuid4())
        self.app_name = "smart-data-agent"

        # Chat history for session transfer
        self._history: List[ChatMessage] = []

        # Chat manager for persistence and context
        self._chat_manager = chat_manager

        # Agent context - use provided, get from chat_manager, or create new
        if agent_context is not None:
            self._agent_context = agent_context
        elif chat_manager is not None:
            self._agent_context = chat_manager.get_context(self.chat_id, self.session_id)
        else:
            self._agent_context = AgentContext()

        # Session service (shared across agent switches)
        self.session_service = InMemorySessionService()

        # Track if session has been initialized
        self._session_initialized = False

        # Ensure Vertex AI is configured
        ensure_configured()

        # Initialize the agent
        self._init_agent()

    def _init_agent(self):
        """Initialize or reinitialize the agent and runner."""
        # Create the appropriate agent
        if self.latitude is not None and self.longitude is not None:
            self._agent_wrapper = LocationDataAgent(
                latitude=self.latitude,
                longitude=self.longitude,
                city=self.city,
                model=self.model,
            )
            self.agent_type = "location"
        else:
            self._agent_wrapper = CityDataAgent(
                city=self.city,
                model=self.model,
            )
            self.agent_type = "city"

        # Create the LlmAgent
        self._agent = self._agent_wrapper.create()

        # Create the runner
        self._runner = Runner(
            app_name=self.app_name,
            agent=self._agent,
            session_service=self.session_service,
        )

    async def _create_new_session(self):
        """Create a new session, generating a new session ID."""
        self.session_id = str(uuid.uuid4())
        self._session_initialized = False
        await self._ensure_session()

    async def _ensure_session(self):
        """Ensure a session exists, creating one if needed."""
        if self._session_initialized:
            return

        try:
            # Try to get existing session
            session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id,
            )
            if session is None:
                raise ValueError("Session not found")
            self._session_initialized = True
        except Exception:
            # Create new session
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id,
                state={"agent_type": self.agent_type},
            )
            self._session_initialized = True

    async def _replay_history_to_session(
        self,
        location_changed: bool = False,
        old_coords: tuple = None,
        new_coords: tuple = None,
    ):
        """
        Replay the conversation history to the new agent session.

        This injects the previous conversation context so the new agent
        understands what was discussed before the mode switch.

        Args:
            location_changed: Whether the location was changed
            old_coords: Tuple of (old_latitude, old_longitude)
            new_coords: Tuple of (new_latitude, new_longitude)
        """
        if not self._history:
            return

        # Build a context summary from history
        history_summary = self._build_history_summary()

        # Add location change notice if applicable
        location_notice = ""
        if location_changed and new_coords:
            location_notice = (
                f"\n\n**IMPORTANT: The user has selected a NEW LOCATION on the map.**\n"
                f"New coordinates: ({new_coords[0]:.6f}, {new_coords[1]:.6f})\n"
                f"You MUST query the zoning code at this NEW location using get_zoning_code_at_location.\n"
                f"Do NOT assume the previous zoning code (from earlier in the conversation) still applies.\n"
                f"The new location may have a completely different zoning designation.\n"
            )

        if history_summary or location_notice:
            # Send a system-like message to establish context
            context_text = "[Previous conversation context]\n"
            if history_summary:
                context_text += history_summary
            if location_notice:
                context_text += location_notice
            context_text += "\n\n[Continue from here]"

            context_message = types.Content(
                role="user",
                parts=[types.Part(text=context_text)],
            )

            # Run the agent with the context to prime it
            async for event in self._runner.run_async(
                user_id=self.user_id,
                session_id=self.session_id,
                new_message=context_message,
            ):
                # We don't need the response, just priming the session
                pass

    def _build_history_summary(self) -> str:
        """
        Build a summary of the conversation history for context transfer.

        Returns:
            A formatted string summarizing the previous conversation.
        """
        if not self._history:
            return ""

        lines = []
        for msg in self._history[-10:]:  # Last 10 messages for context
            role_label = "User" if msg.role == "user" else "Assistant"
            # Truncate long messages
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role_label}: {content}")

        return "\n".join(lines)

    async def switch_to_location_mode(
        self,
        latitude: float,
        longitude: float,
    ):
        """
        Switch to location-based mode.

        Args:
            latitude: New latitude coordinate
            longitude: New longitude coordinate

        Note:
            This preserves the conversation history and transfers it
            to the new location-based agent.
        """
        old_latitude = self.latitude
        old_longitude = self.longitude

        self.latitude = latitude
        self.longitude = longitude
        self._init_agent()

        # Create a new session for the new agent
        await self._create_new_session()

        # Replay history to give context to new agent, noting the location change
        await self._replay_history_to_session(
            location_changed=True,
            old_coords=(old_latitude, old_longitude),
            new_coords=(latitude, longitude),
        )

    async def switch_to_city_mode(self):
        """
        Switch to city-based mode (remove location context).

        Note:
            This preserves the conversation history and transfers it
            to the new city-wide agent.
        """
        self.latitude = None
        self.longitude = None
        self._init_agent()

        # Create a new session for the new agent
        await self._create_new_session()

        # Replay history to give context to new agent (no location change params needed)
        await self._replay_history_to_session()

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.

        Returns:
            List of message dictionaries with 'role', 'content', and 'message_id'
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "message_id": msg.message_id,
            }
            for msg in self._history
        ]

    def set_history(self, history: List[Dict[str, Any]]):
        """
        Set the conversation history (for restoring sessions).

        Args:
            history: List of message dictionaries
        """
        self._history = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                message_id=msg.get("message_id", str(uuid.uuid4())),
            )
            for msg in history
        ]

    async def replay_history(self):
        """
        Replay conversation history to the ADK session.

        This should be called after set_history() when continuing a chat
        so the LLM knows about the previous conversation context.
        """
        await self._ensure_session()
        await self._replay_history_to_session()

    def clear_history(self):
        """Clear the conversation history."""
        self._history = []

    def get_agent_context(self) -> AgentContext:
        """Get the agent context for this runner."""
        return self._agent_context

    async def run(self, user_message: str) -> str:
        """
        Run the agent and return the complete response.

        Args:
            user_message: The user's question

        Returns:
            The agent's response as a string
        """
        await self._ensure_session()

        # Set current context so tools can access it
        set_current_context(self._agent_context)

        # Add user message to history
        user_msg = ChatMessage(role="user", content=user_message)
        self._history.append(user_msg)

        # Create message for ADK
        message = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        # Run agent
        response_text = None
        async for event in self._runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text

        # Add assistant response to history
        if response_text:
            assistant_msg = ChatMessage(role="assistant", content=response_text)
            self._history.append(assistant_msg)

        return response_text or "No response generated."

    async def run_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Run the agent and stream response chunks.

        Args:
            user_message: The user's question

        Yields:
            Response chunks as they become available
        """
        await self._ensure_session()

        # Set current context so tools can access it
        set_current_context(self._agent_context)

        # Add user message to history
        user_msg = ChatMessage(role="user", content=user_message)
        self._history.append(user_msg)

        # Create message for ADK
        message = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        # Run agent and stream
        full_response = ""
        async for event in self._runner.run_async(
            user_id=self.user_id,
            session_id=self.session_id,
            new_message=message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    chunk = event.content.parts[0].text
                    full_response = chunk
                    yield chunk

        # Add complete response to history
        if full_response:
            assistant_msg = ChatMessage(role="assistant", content=full_response)
            self._history.append(assistant_msg)

    def get_context(self) -> Dict[str, Any]:
        """
        Get the current context for serialization.

        Returns:
            Dictionary with agent context and configuration
        """
        return {
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "agent_type": self.agent_type,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "history": self.get_history(),
        }

    def save_to_disk(self, title: Optional[str] = None) -> bool:
        """
        Save the current chat to disk using ChatManager.

        Args:
            title: Optional title for the chat

        Returns:
            True on success, False if no chat_manager or on error
        """
        if not self._chat_manager:
            return False

        import time
        chat_data = {
            "chat_id": self.chat_id,
            "title": title or self._generate_title(),
            "dts": int(time.time()),
            "messages": self.get_history(),
            "context": {
                "city": self.city,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "agent_type": self.agent_type,
            },
        }
        return self._chat_manager.save_chat(chat_data, self.session_id) or False

    def _generate_title(self) -> str:
        """Generate a title from the first user message."""
        for msg in self._history:
            if msg.role == "user":
                title = msg.content[:50]
                if len(msg.content) > 50:
                    title += "..."
                return title
        return "New Chat"

    @classmethod
    def load_from_disk(
        cls,
        chat_id: str,
        session_id: str,
        chat_manager: ChatManager,
        model: str = "gemini-2.0-flash",
    ) -> Optional["SmartDataAgentRunner"]:
        """
        Load a runner from disk.

        Args:
            chat_id: Chat ID to load
            session_id: Session ID
            chat_manager: ChatManager instance
            model: Gemini model to use

        Returns:
            SmartDataAgentRunner with restored state, or None if not found
        """
        chat_data = chat_manager.get_chat(chat_id, session_id)
        if not chat_data:
            return None

        context = chat_data.get("context", {})
        runner = cls(
            city=context.get("city", "boston"),
            latitude=context.get("latitude"),
            longitude=context.get("longitude"),
            model=model,
            session_id=session_id,
            chat_id=chat_id,
            chat_manager=chat_manager,
        )

        # Restore history
        if "messages" in chat_data:
            runner.set_history(chat_data["messages"])

        return runner

    @classmethod
    async def from_context(
        cls,
        context: Dict[str, Any],
        model: str = "gemini-2.0-flash",
        chat_manager: Optional[ChatManager] = None,
    ) -> "SmartDataAgentRunner":
        """
        Create a runner from a saved context.

        Args:
            context: Context dictionary from get_context()
            model: Gemini model to use
            chat_manager: Optional ChatManager for persistence

        Returns:
            SmartDataAgentRunner with restored state
        """
        runner = cls(
            city=context["city"],
            latitude=context.get("latitude"),
            longitude=context.get("longitude"),
            model=model,
            session_id=context.get("session_id"),
            user_id=context.get("user_id"),
            chat_id=context.get("chat_id"),
            chat_manager=chat_manager,
        )

        # Restore history if present
        if "history" in context:
            runner.set_history(context["history"])
            # Replay history to prime the agent
            await runner._ensure_session()
            await runner._replay_history_to_session()

        return runner

    def is_location_based(self) -> bool:
        """Check if the current agent is location-based."""
        return self.agent_type == "location"
