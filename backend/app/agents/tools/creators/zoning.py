"""Tool creator for zoning queries with bound city parameter."""

from typing import Optional, List, Callable
from app.agents.tools.functions import query_zoning_ordinance


def create_zoning_tool(city: str) -> Callable:
    """
    Create a zoning ordinance query tool with city pre-bound.

    Args:
        city: City name to bind to the tool

    Returns:
        A callable tool function with city pre-bound
    """

    def query_zoning_for_city(
        question: str,
        zoning_codes: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> str:
        """Query zoning ordinance for the configured city."""
        return query_zoning_ordinance(
            question=question,
            city=city,
            zoning_codes=zoning_codes,
            top_k=top_k,
        )

    query_zoning_for_city.__name__ = "query_zoning_ordinance"
    query_zoning_for_city.__doc__ = f"""Search zoning ordinance documents for {city.title()}.

Use this tool when the user asks about:
- Zoning regulations and rules
- What is allowed or prohibited in a zoning district
- Building height, setback, or density requirements
- Land use permissions (residential, commercial, industrial)
- Zoning code definitions and descriptions
- Special permits or variances
- Parking requirements

Args:
    question: Natural language question about zoning regulations
    zoning_codes: Optional list of specific zoning codes to filter by
    top_k: Number of relevant passages to return (default: 5)

Returns:
    A formatted string with relevant zoning ordinance passages.
"""

    return query_zoning_for_city
