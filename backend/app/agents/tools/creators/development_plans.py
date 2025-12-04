"""Tool creator for development plans queries with bound city parameter."""

from typing import Optional, List, Callable
from app.agents.tools.functions import query_development_plans


def create_development_plans_tool(city: str) -> Callable:
    """
    Create a development plans query tool with city pre-bound.

    Args:
        city: City name to bind to the tool

    Returns:
        A callable tool function with city pre-bound
    """

    def query_development_plans_for_city(
        question: str,
        article_reference: Optional[List[str]] = None,
        project_name_contains: Optional[str] = None,
        top_k: int = 5,
    ) -> str:
        """Query development plans for the configured city."""
        return query_development_plans(
            question=question,
            city=city,
            article_reference=article_reference,
            project_name_contains=project_name_contains,
            top_k=top_k,
        )

    query_development_plans_for_city.__name__ = "query_development_plans"
    query_development_plans_for_city.__doc__ = f"""Search development plans documents for {city.title()}.

Use this tool when the user asks about:
- Proposed development projects and their details
- Project descriptions, building uses, and specifications
- Development approvals and requirements
- Article references in development plans (e.g., Article 50, Section 32)
- Project timelines, status, and outcomes
- Development proposals in specific areas or zones
- Building heights, units, parking in proposed projects

IMPORTANT: Only use the article_reference filter when the user EXPLICITLY 
mentions specific articles. For example:
- "Show me projects requiring Article 50" → use article_reference=["Article 50"]
- "What projects are proposed?" → do NOT use article_reference filter

Args:
    question: Natural language question about development plans
    article_reference: Optional list of article references to filter by (e.g., ["Article 50"])
                      ONLY use when explicitly requested by user
    project_name_contains: Optional text to filter project names
    top_k: Number of relevant passages to return (default: 5)

Returns:
    A formatted string with relevant development plan passages.

Examples:
    - "What development projects are proposed in the city?"
    - "Show me projects that mention Article 50" → article_reference=["Article 50"]
    - "What are the parking requirements in proposed developments?"
"""

    return query_development_plans_for_city

