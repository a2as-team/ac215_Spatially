"""Runner for the SQL Agent with session management."""

import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.sql_agent import SQLAgent
from app.agents.config import ensure_configured


@dataclass
class ChatMessage:
    """Represents a chat message in the conversation history."""
    role: str  # "user" or "assistant"
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class SQLAgentRunner:
    """Runner for SQL Agent with session management.

    This runner handles:
    1. Creating the SQL agent with 4 tools (list_tables, check_schema, check_query, run_query)
    2. Managing conversation sessions
    3. Executing SQL queries through the agent

    Usage:
        runner = SQLAgentRunner()
        response = await runner.run("What is the median household income in Boston?")
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize the SQL agent runner.

        Args:
            model: Gemini model to use
            session_id: Optional session ID for continuity
            user_id: Optional user ID
        """
        self.model = model
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or str(uuid.uuid4())
        self.app_name = "sql-agent"

        # Chat history
        self._history: List[ChatMessage] = []

        # Session service
        self.session_service = InMemorySessionService()

        # Track if session has been initialized
        self._session_initialized = False

        # Ensure Vertex AI is configured
        ensure_configured()

        # Initialize the agent
        self._init_agent()

    def _init_agent(self):
        """Initialize the agent and runner."""
        # Create the SQL agent
        self._agent_wrapper = SQLAgent(model=self.model)

        # Create the LlmAgent
        self._agent = self._agent_wrapper.create()

        # Create the runner
        self._runner = Runner(
            app_name=self.app_name,
            agent=self._agent,
            session_service=self.session_service,
        )

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
                state={"agent_type": "sql"},
            )
            self._session_initialized = True

    async def run(self, user_message: str) -> str:
        """
        Run the SQL agent and return the complete response.

        Args:
            user_message: The user's question or SQL query request

        Returns:
            The agent's response as a string
        """
        await self._ensure_session()

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
        Run the SQL agent and stream response chunks.

        Args:
            user_message: The user's question or SQL query request

        Yields:
            Response chunks as they become available
        """
        await self._ensure_session()

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

    def clear_history(self):
        """Clear the conversation history."""
        self._history = []

