"""Chat and context management for agents.

This module provides unified management of:
- Chat history persistence
- Per-chat agent context (tool execution data)
- Modular source stores for different data types
"""

from .chat_manager import ChatManager
from .history_manager import ChatHistoryManager
from .context import (
    AgentContext,
    SourceStore,
    set_current_context,
    get_current_context,
    clear_current_context,
)

# Import stores to trigger registration with AgentContext
from .stores import OrdinanceSource, OrdinanceSourceStore

__all__ = [
    # Chat management
    "ChatManager",
    "ChatHistoryManager",
    # Context
    "AgentContext",
    "SourceStore",
    "set_current_context",
    "get_current_context",
    "clear_current_context",
    # Stores
    "OrdinanceSource",
    "OrdinanceSourceStore",
]
