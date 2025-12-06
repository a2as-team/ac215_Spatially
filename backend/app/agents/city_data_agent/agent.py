"""City Data Agent using Google ADK.

This agent handles general city-wide queries when no specific location
is selected.
"""

from google.adk.agents import LlmAgent
from app.agents.tools import (
    create_census_tool,
    create_zoning_tool,
    create_development_plans_tool,
    create_cite_sources_tool,
)
from .prompts import INSTRUCTION


class CityDataAgent:
    """Agent for city-wide queries (no specific location).

    This agent is used when the user wants to ask general questions
    about a city without a specific location selected.

    The agent has access to:
    - Census data for the city
    - Zoning ordinance search for the entire city

    Usage:
        agent = CityDataAgent(city="boston")
        llm_agent = agent.create()
    """

    def __init__(
        self,
        city: str,
        model: str = "gemini-2.0-flash",
    ):
        """
        Initialize the city-based data agent.

        Args:
            city: City name (e.g., "boston", "cambridge")
            model: Gemini model to use (default: gemini-2.0-flash)
        """
        self.city = city.lower()
        self.model = model

    def create(self) -> LlmAgent:
        """
        Create the LlmAgent with city-bound tools.

        Returns:
            LlmAgent configured for city-wide queries
        """
        # Create tools with city pre-bound
        census_tool = create_census_tool(city=self.city)
        zoning_tool = create_zoning_tool(city=self.city)
        development_plans_tool = create_development_plans_tool(city=self.city)
        cite_tool = create_cite_sources_tool()

        # Build instruction with city context
        instruction = INSTRUCTION.format(city=self.city.title())

        agent = LlmAgent(
            name="CityDataAgent",
            model=self.model,
            instruction=instruction,
            tools=[census_tool, zoning_tool, development_plans_tool, cite_tool],
        )

        return agent

    def get_context(self) -> dict:
        """Get the agent's context for session transfer."""
        return {
            "agent_type": "city",
            "city": self.city,
        }
