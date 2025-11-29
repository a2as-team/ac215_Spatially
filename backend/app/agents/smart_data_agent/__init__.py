"""Smart Data Agent - Factory for creating data agents.

This module provides:
- SmartDataAgent: Factory that creates LocationDataAgent or CityDataAgent
- SmartDataAgentRunner: Runner with session management and mode switching

For direct access to individual agents, use:
- app.agents.location_data_agent.LocationDataAgent
- app.agents.city_data_agent.CityDataAgent
"""

from .agent import SmartDataAgent
from .runner import SmartDataAgentRunner, ChatMessage
from .prompts import (
    LOCATION_AGENT_INSTRUCTION,
    CITY_AGENT_INSTRUCTION,
    LOCATION_AGENT_DESCRIPTION,
    CITY_AGENT_DESCRIPTION,
)

# Re-export individual agents for convenience
from app.agents.location_data_agent import LocationDataAgent
from app.agents.city_data_agent import CityDataAgent

__all__ = [
    # Factory
    "SmartDataAgent",
    # Runner
    "SmartDataAgentRunner",
    "ChatMessage",
    # Individual agents
    "LocationDataAgent",
    "CityDataAgent",
    # Prompts
    "LOCATION_AGENT_INSTRUCTION",
    "CITY_AGENT_INSTRUCTION",
    "LOCATION_AGENT_DESCRIPTION",
    "CITY_AGENT_DESCRIPTION",
]
