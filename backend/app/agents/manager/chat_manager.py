"""Unified chat management for agents.

This module provides ChatManager, which composes:
- ChatHistoryManager: Disk persistence for chat history
- Per-chat AgentContext: Tool execution data (ordinance sources, etc.)

This replaces the global AgentContext approach, providing proper
isolation between concurrent chat sessions.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

from .history_manager import ChatHistoryManager
from .context import AgentContext

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Represents an active chat session with its context."""
    chat_id: str
    session_id: str
    context: AgentContext = field(default_factory=AgentContext)


class ChatManager:
    """Manages chat sessions with history persistence and per-chat context.

    This class provides:
    1. Chat history persistence via ChatHistoryManager
    2. Per-chat AgentContext for tool execution data
    3. Session management without global state

    Usage:
        manager = ChatManager(model="gemini-2.0-flash")

        # Get context for a chat (creates if needed)
        context = manager.get_context(chat_id, session_id)

        # Tools use the context during execution
        context.add_ordinance_sources(results)

        # After agent run, get the sources
        sources = context.get_ordinance_sources_dict()

        # Save chat
        manager.save_chat(chat_data, session_id)
    """

    def __init__(self, model: str, history_dir: str = "chat-history"):
        """Initialize the chat manager.

        Args:
            model: Model name for history organization
            history_dir: Base directory for history storage
        """
        self._history_manager = ChatHistoryManager(model=model, history_dir=history_dir)
        self._active_sessions: Dict[str, ChatSession] = {}

    def _session_key(self, chat_id: str, session_id: str) -> str:
        """Generate a unique key for a chat session."""
        return f"{session_id}:{chat_id}"

    def get_context(self, chat_id: str, session_id: str) -> AgentContext:
        """Get or create the AgentContext for a chat session.

        Args:
            chat_id: Chat ID
            session_id: Session ID

        Returns:
            AgentContext for this chat session
        """
        key = self._session_key(chat_id, session_id)

        if key not in self._active_sessions:
            self._active_sessions[key] = ChatSession(
                chat_id=chat_id,
                session_id=session_id,
                context=AgentContext(),
            )
            logger.debug(f"Created new chat session: {key}")

        return self._active_sessions[key].context

    def clear_context(self, chat_id: str, session_id: str):
        """Clear the context for a chat session.

        Args:
            chat_id: Chat ID
            session_id: Session ID
        """
        key = self._session_key(chat_id, session_id)

        if key in self._active_sessions:
            self._active_sessions[key].context.clear()
            logger.debug(f"Cleared context for session: {key}")
        else:
            # Create a fresh session
            self._active_sessions[key] = ChatSession(
                chat_id=chat_id,
                session_id=session_id,
                context=AgentContext(),
            )

    def remove_session(self, chat_id: str, session_id: str):
        """Remove a chat session from active sessions.

        Args:
            chat_id: Chat ID
            session_id: Session ID
        """
        key = self._session_key(chat_id, session_id)
        if key in self._active_sessions:
            del self._active_sessions[key]
            logger.debug(f"Removed session: {key}")

    # Delegate history operations to ChatHistoryManager

    def save_chat(self, chat_to_save: Dict, session_id: str) -> Optional[bool]:
        """Save a chat to disk.

        Args:
            chat_to_save: Chat data with 'chat_id' and 'messages'
            session_id: Session ID

        Returns:
            True on success, None on error
        """
        return self._history_manager.save_chat(chat_to_save, session_id)

    def get_chat(self, chat_id: str, session_id: str) -> Optional[Dict]:
        """Load a chat from disk.

        Args:
            chat_id: Chat ID
            session_id: Session ID

        Returns:
            Chat data dictionary, or empty dict if not found
        """
        return self._history_manager.get_chat(chat_id, session_id)

    def get_recent_chats(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        """Get recent chats for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of chats to return

        Returns:
            List of chat data dictionaries
        """
        return self._history_manager.get_recent_chats(session_id, limit)

    def delete_chat(self, chat_id: str, session_id: str) -> bool:
        """Delete a chat from disk and remove its session.

        Args:
            chat_id: Chat ID
            session_id: Session ID

        Returns:
            True on success, False on error
        """
        # Remove from active sessions
        self.remove_session(chat_id, session_id)
        # Delete from disk
        return self._history_manager.delete_chat(chat_id, session_id)
