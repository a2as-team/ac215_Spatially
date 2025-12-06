"""Query development plans within the same zoning district."""

from typing import Optional, List
import logging
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_development_plans_results
from app.agents.manager import get_current_context

logger = logging.getLogger(__name__)


def query_development_plans_by_zone(
    question: str,
    latitude: float,
    longitude: float,
    city: str,
    article_reference: Optional[List[str]] = None,
    top_k: int = 10,
) -> str:
    """
    Search development plans within the same zoning district as the location.

    Use this tool when the user asks about:
    - "What developments are happening in this zone?"
    - "Show me all projects in this zoning district"
    - "What are people building in this area's zone?"
    - Questions about zone-wide development activity

    This returns ALL projects within the same zoning district boundary,
    not just nearby projects. Use this for understanding broader zoning
    district development patterns.

    Args:
        question: Natural language question about development plans
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        city: City name
        article_reference: Optional article filter (use only when explicitly requested)
        top_k: Number of results to return (default: 10, higher for zone-wide queries)

    Returns:
        Formatted string with development plans in the same zoning district.

    Examples:
        - "What developments are happening in this zoning district?"
        - "Show me all projects in the same zone as this location"
        - "What's being built in this zone that requires Article 50?"
    """
    try:
        logger.info(
            f"Zone-based development plans query: {question}, "
            f"location: ({latitude}, {longitude}), city: {city}, "
            f"article_ref: {article_reference}"
        )

        vector_query = DevelopmentPlansVectorQuery(db_name=settings.POSTGRES_DB)

        # Use new query_by_zoning_district method
        results = vector_query.query_by_zoning_district(
            query_text=question,
            latitude=latitude,
            longitude=longitude,
            city=city.lower(),
            top_k=top_k,
        )

        # Filter by article reference if provided (post-processing)
        if article_reference and results:
            results = [
                r for r in results
                if any(
                    article in r.get("article_reference", [])
                    for article in article_reference
                )
            ]

        if not results:
            return (
                f"No development plans found in the zoning district at "
                f"({latitude}, {longitude}) in {city}."
            )

        # Store results in context for later citation
        context = get_current_context()
        if context:
            store = context.get_store("development_plans")
            store.add(results)
            logger.debug(f"Added {len(results)} development plan sources to context")

        formatted_results = format_development_plans_results(results)

        # Extract zoning code if available
        zoning_code = results[0].get("_zoning_code", "this zone") if results else "this zone"

        return (
            f"Development Plans in {zoning_code} zoning district "
            f"in {city.title()}:\n\n{formatted_results}"
        )

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying development plans by zone: {e}")
        return f"Error querying development plans by zone: {str(e)}"

