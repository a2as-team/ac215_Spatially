"""Smart Data Agent Factory.

This module provides a factory class that creates the appropriate agent
(LocationDataAgent or CityDataAgent) based on the provided parameters.

Reference: https://google.github.io/adk-docs/agents/custom-agents/#part-4-instantiating-and-running-the-custom-agent
"""

from typing import Optional
from google.adk.agents import LlmAgent
from app.agents.location_data_agent import LocationDataAgent
from app.agents.city_data_agent import CityDataAgent


class SmartDataAgent:
    """Factory class that creates the appropriate agent based on parameters.

    This is a convenience class that automatically chooses between
    LocationDataAgent and CityDataAgent based on the provided parameters.

    Usage:
        # Location-based agent (lat/long provided)
        agent = SmartDataAgent(
            city="boston",
            latitude=42.3601,
            longitude=-71.0589,
        )

        # City-based agent (no location)
        agent = SmartDataAgent(city="boston")

        # Get the LlmAgent
        llm_agent = agent.create()
    """

    def __init__(
        self,
        city: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        model: str = "gemini-2.0-flash",
    ):
        """
        Initialize the smart data agent.

        Args:
            city: City name (required)
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
            model: Gemini model to use

        Note:
            If both latitude and longitude are provided, creates a LocationDataAgent.
            Otherwise, creates a CityDataAgent.
        """
        self.city = city.lower()
        self.latitude = latitude
        self.longitude = longitude
        self.model = model

        # Determine which agent type to use
        if latitude is not None and longitude is not None:
            self._agent = LocationDataAgent(
                latitude=latitude,
                longitude=longitude,
                city=city,
                model=model,
            )
            self.agent_type = "location"
        else:
            self._agent = CityDataAgent(city=city, model=model)
            self.agent_type = "city"

    def create(self) -> LlmAgent:
        """Create the appropriate LlmAgent."""
        return self._agent.create()

    def get_context(self) -> dict:
        """Get the agent's context for session transfer."""
        return self._agent.get_context()

    def is_location_based(self) -> bool:
        """Check if this is a location-based agent."""
        return self.agent_type == "location"
