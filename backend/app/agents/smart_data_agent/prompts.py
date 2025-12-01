"""Prompts for Smart Data Agent.

Note: The actual prompts are defined in the individual agent modules:
- app.agents.location_data_agent.prompts
- app.agents.city_data_agent.prompts

This module re-exports them for backwards compatibility.
"""

from app.agents.location_data_agent.prompts import (
    INSTRUCTION as LOCATION_AGENT_INSTRUCTION,
    DESCRIPTION as LOCATION_AGENT_DESCRIPTION,
)
from app.agents.city_data_agent.prompts import (
    INSTRUCTION as CITY_AGENT_INSTRUCTION,
    DESCRIPTION as CITY_AGENT_DESCRIPTION,
)

__all__ = [
    "LOCATION_AGENT_INSTRUCTION",
    "LOCATION_AGENT_DESCRIPTION",
    "CITY_AGENT_INSTRUCTION",
    "CITY_AGENT_DESCRIPTION",
]
