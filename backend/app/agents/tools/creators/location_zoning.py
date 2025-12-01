"""Tool creator for location-based zoning queries with bound coordinates."""

from typing import Callable
from app.agents.tools.functions import query_zoning_by_location


def create_location_zoning_tool(
    latitude: float,
    longitude: float,
    city: str,
) -> Callable:
    """
    Create a location-based zoning query tool with coordinates pre-bound.

    Args:
        latitude: Latitude coordinate to bind
        longitude: Longitude coordinate to bind
        city: City name to bind

    Returns:
        A callable tool function with location pre-bound
    """

    def query_zoning_at_location(
        question: str,
        top_k: int = 5,
    ) -> str:
        """Query zoning ordinance for the configured location."""
        return query_zoning_by_location(
            question=question,
            latitude=latitude,
            longitude=longitude,
            city=city,
            top_k=top_k,
        )

    query_zoning_at_location.__name__ = "query_zoning_at_location"
    query_zoning_at_location.__doc__ = f"""Search zoning ordinance for location ({latitude}, {longitude}) in {city.title()}.

Use this tool when the user asks about zoning at their selected location:
- What can be built at this location
- Zoning restrictions and requirements
- Allowed uses and building parameters
- Height, setback, and density limits

The location has already been set to:
- Latitude: {latitude}
- Longitude: {longitude}
- City: {city.title()}

Args:
    question: Natural language question about zoning at this location
    top_k: Number of relevant passages to return (default: 5)

Returns:
    A formatted string with relevant zoning ordinance passages for this location.
"""

    return query_zoning_at_location
