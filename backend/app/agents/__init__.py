"""Spatially Agents.

This module provides AI agents for answering questions about city data.

Available agents:
- SmartDataAgent: Factory that creates the appropriate agent based on parameters
- SmartDataAgentRunner: Runner with session management and mode switching
- LocationDataAgent: Agent for location-specific queries (lat/long provided)
- CityDataAgent: Agent for city-wide queries (no specific location)

Persistence:
- ChatHistoryManager: Disk-based persistence for chat history

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
from .history_manager import ChatHistoryManager
from .config import configure_vertexai

__all__ = [
    "SmartDataAgent",
    "SmartDataAgentRunner",
    "ChatMessage",
    "LocationDataAgent",
    "CityDataAgent",
    "ChatHistoryManager",
    "configure_vertexai",
]
