"""Spatially Agents.

This module provides AI agents for answering questions about city data.

Available agents:
- SmartDataAgent: Factory that creates the appropriate agent based on parameters
- SmartDataAgentRunner: Runner with session management and mode switching
- LocationDataAgent: Agent for location-specific queries (lat/long provided)
- CityDataAgent: Agent for city-wide queries (no specific location)

Management:
- ChatManager: Unified chat management with history persistence and per-chat context
- ChatHistoryManager: Disk-based persistence for chat history
- AgentContext: Per-chat context for tool execution data

Configuration:
- configure_vertexai: Configure Google GenAI to use Vertex AI
"""

from .smart_data_agent import (
    SmartDataAgent,
    SmartDataAgentRunner,
    ChatMessage,
    LocationDataAgent,
    CityDataAgent,
)
from .manager import ChatManager, ChatHistoryManager, AgentContext
from .config import configure_vertexai

__all__ = [
    "SmartDataAgent",
    "SmartDataAgentRunner",
    "ChatMessage",
    "LocationDataAgent",
    "CityDataAgent",
    "ChatManager",
    "ChatHistoryManager",
    "AgentContext",
    "configure_vertexai",
]
