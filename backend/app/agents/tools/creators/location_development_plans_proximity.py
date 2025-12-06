"""Tool creator for location-based development plans queries using proximity."""

from typing import Optional, List, Callable
from app.agents.tools.functions import query_development_plans_by_proximity


def create_location_development_plans_proximity_tool(
    latitude: float,
    longitude: float,
    city: str,
) -> Callable:
    """
    Create a proximity-based development plans query tool with coordinates pre-bound.

    Args:
        latitude: Latitude coordinate to bind
        longitude: Longitude coordinate to bind
        city: City name to bind

    Returns:
        A callable tool function with location pre-bound
    """

    def query_development_plans_nearby(
        question: str,
        radius_km: float = 1.0,
        article_reference: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> str:
        """Query development plans near the configured location."""
        return query_development_plans_by_proximity(
            question=question,
            latitude=latitude,
            longitude=longitude,
            city=city,
            radius_km=radius_km,
            article_reference=article_reference,
            top_k=top_k,
        )

    query_development_plans_nearby.__name__ = "query_development_plans_nearby"
    query_development_plans_nearby.__doc__ = f"""Search development plans near location ({latitude}, {longitude}) in {city.title()}.

Use this tool when the user asks about development plans NEAR their selected location:
- "What's being built near me?"
- "What projects are nearby?"
- "Show me developments in the immediate area"
- "What construction is happening around here?"

This uses radius-based filtering. The default radius is 1.0 km, but you can 
adjust it based on the user's question:
- "What's nearby?" → use default radius_km=1.0
- "Show me projects within 2km" → use radius_km=2.0
- "What's in the broader area?" → use radius_km=3.0 or higher

The location has already been set to:
- Latitude: {latitude}
- Longitude: {longitude}
- City: {city.title()}

Args:
    question: Natural language question about development plans
    radius_km: Search radius in kilometers (default: 1.0, adjustable)
    article_reference: Optional article filter (ONLY use if explicitly requested)
    top_k: Number of relevant passages to return (default: 5)

Returns:
    A formatted string with development plans near this location, 
    including distance from the selected point.

Examples:
    - "What's being built near this location?"
    - "Show me projects within 2km" → radius_km=2.0
    - "What developments are nearby that mention Article 50?" → article_reference=["Article 50"]
"""

    return query_development_plans_nearby

