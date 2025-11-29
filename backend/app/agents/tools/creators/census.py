"""Tool creator for census queries with bound city parameter."""

from typing import Optional, Callable
from app.agents.tools.functions import query_census_data


def create_census_tool(city: str) -> Callable:
    """
    Create a census query tool with city pre-bound.

    This creates a tool function where the city parameter is already set,
    so the agent only needs to provide the question.

    Args:
        city: City name to bind to the tool

    Returns:
        A callable tool function with city pre-bound
    """

    def query_census_for_city(
        question: str,
        year: Optional[int] = None,
    ) -> str:
        """Query census demographic data for the configured city."""
        return query_census_data(question=question, city=city, year=year)

    # Preserve function metadata for Google ADK
    query_census_for_city.__name__ = "query_census_data"
    query_census_for_city.__doc__ = f"""Query census demographic data for {city.title()}.

Use this tool when the user asks about:
- Population statistics (total population, age distribution, gender)
- Housing data (housing units, occupancy, home values, rent)
- Income and poverty levels
- Employment and education statistics
- Household composition and family structures
- Any demographic or socioeconomic data from the American Community Survey (ACS)

Args:
    question: Natural language question about census/demographic data
    year: Optional year for the ACS data (e.g., 2022, 2021)

Returns:
    A formatted string with the census data results.

Examples:
    - "What is the median household income?"
    - "How many housing units are owner-occupied?"
    - "What is the population by age group?"
"""

    return query_census_for_city
