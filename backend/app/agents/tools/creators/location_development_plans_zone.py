"""Tool creator for location-based development plans queries using zoning district."""

from typing import Optional, List, Callable
from app.agents.tools.functions import query_development_plans_by_zone


def create_location_development_plans_zone_tool(
    latitude: float,
    longitude: float,
    city: str,
) -> Callable:
    """
    Create a zoning district-based development plans query tool with coordinates pre-bound.

    Args:
        latitude: Latitude coordinate to bind
        longitude: Longitude coordinate to bind
        city: City name to bind

    Returns:
        A callable tool function with location pre-bound
    """

    def query_development_plans_in_zone(
        question: str,
        article_reference: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> str:
        """Query development plans in the same zoning district as the configured location."""
        return query_development_plans_by_zone(
            question=question,
            latitude=latitude,
            longitude=longitude,
            city=city,
            article_reference=article_reference,
            top_k=top_k,
        )

    query_development_plans_in_zone.__name__ = "query_development_plans_in_zone"
    query_development_plans_in_zone.__doc__ = f"""Search development plans in the same zoning district as location ({latitude}, {longitude}) in {city.title()}.

Use this tool when the user asks about development plans in the ZONING DISTRICT:
- "What developments are happening in this zone?"
- "Show me all projects in this zoning district"
- "What are people building in this area's zone?"
- "What's the development activity in this zone?"

This returns ALL projects within the same zoning district boundary,
not just nearby projects. This is useful for understanding broader 
zoning district development patterns and activity.

The location has already been set to:
- Latitude: {latitude}
- Longitude: {longitude}
- City: {city.title()}

The tool will:
1. Determine which zoning district contains this location
2. Find all development plans that fall within that zoning district boundary
3. Return results ranked by semantic relevance to the question

Args:
    question: Natural language question about development plans
    article_reference: Optional article filter (ONLY use if explicitly requested)
    top_k: Number of relevant passages to return (default: 10, higher for zone-wide)

Returns:
    A formatted string with development plans in the same zoning district.

Examples:
    - "What developments are happening in this zoning district?"
    - "Show me all projects in the same zone as this location"
    - "What's being built in this zone that requires Article 50?" → article_reference=["Article 50"]
"""

    return query_development_plans_in_zone

