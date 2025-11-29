"""Location Data Agent using Google ADK.

This agent handles queries when the user has selected a specific location
(latitude/longitude) on the map.
"""

from google.adk.agents import LlmAgent
from app.agents.tools import (
    create_census_tool,
    create_location_zoning_tool,
    create_location_zoning_code_tool,
)
from .prompts import INSTRUCTION


class LocationDataAgent:
    """Agent for location-specific queries (lat/long provided).

    This agent is used when the user has selected a specific location
    on the map and wants to ask questions about that location.

    The agent has access to:
    - Census data for the city
    - Zoning ordinance search filtered by the location's zoning codes

    Usage:
        agent = LocationDataAgent(
            latitude=42.3601,
            longitude=-71.0589,
            city="boston"
        )
        llm_agent = agent.create()
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        city: str,
        model: str = "gemini-2.0-flash",
    ):
        """
        Initialize the location-based data agent.

        Args:
            latitude: Latitude coordinate of the selected location
            longitude: Longitude coordinate of the selected location
            city: City name (e.g., "boston", "cambridge")
            model: Gemini model to use (default: gemini-2.0-flash)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.city = city.lower()
        self.model = model

    def create(self) -> LlmAgent:
        """
        Create the LlmAgent with location-bound tools.

        Returns:
            LlmAgent configured for location-specific queries
        """
        # Create tools with location/city pre-bound
        census_tool = create_census_tool(city=self.city)
        zoning_code_tool = create_location_zoning_code_tool(
            latitude=self.latitude,
            longitude=self.longitude,
            city=self.city,
        )
        zoning_ordinance_tool = create_location_zoning_tool(
            latitude=self.latitude,
            longitude=self.longitude,
            city=self.city,
        )

        # Build instruction with location context
        instruction = INSTRUCTION.format(
            latitude=self.latitude,
            longitude=self.longitude,
            city=self.city.title(),
        )

        agent = LlmAgent(
            name="LocationDataAgent",
            model=self.model,
            instruction=instruction,
            tools=[census_tool, zoning_code_tool, zoning_ordinance_tool],
        )

        return agent

    def get_context(self) -> dict:
        """Get the agent's context for session transfer."""
        return {
            "agent_type": "location",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
        }
