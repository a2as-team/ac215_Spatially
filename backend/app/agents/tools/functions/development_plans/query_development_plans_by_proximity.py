"""Query development plans by proximity using radius-based location search."""

from typing import Optional, List
import logging
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_development_plans_results
from app.agents.manager import get_current_context

logger = logging.getLogger(__name__)


def query_development_plans_by_proximity(
    question: str,
    latitude: float,
    longitude: float,
    city: str,
    radius_km: float = 1.0,
    article_reference: Optional[List[str]] = None,
    top_k: int = 5,
) -> str:
    """
    Search development plans near a specific location using radius-based filtering.

    Use this tool when the user asks about:
    - "What's being built near me?"
    - "What projects are nearby?"
    - "Show me developments in the immediate area"
    - Any question about projects within a specific distance

    Args:
        question: Natural language question about development plans
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        city: City name
        radius_km: Search radius in kilometers (default: 1.0, adjustable by LLM)
        article_reference: Optional article filter (use only when explicitly requested)
        top_k: Number of results to return (default: 5)

    Returns:
        Formatted string with development plans near the location.

    Examples:
        - "What's being built near this location?"
        - "Show me projects within 2km" (adjust radius_km to 2.0)
        - "What developments are nearby that mention Article 50?"
    """
    try:
        logger.info(
            f"Proximity-based development plans query: {question}, "
            f"location: ({latitude}, {longitude}), city: {city}, "
            f"radius: {radius_km}km, article_ref: {article_reference}"
        )

        vector_query = DevelopmentPlansVectorQuery(db_name=settings.POSTGRES_DB)

        # Use existing query_by_location method
        results = vector_query.query_by_location(
            query_text=question,
            latitude=latitude,
            longitude=longitude,
            city=city.lower(),
            top_k=top_k,
            radius_km=radius_km,
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
                f"No development plans found within {radius_km}km of "
                f"({latitude}, {longitude}) in {city}."
            )

        # Store results in context for later citation
        context = get_current_context()
        if context:
            store = context.get_store("development_plans")
            store.add(results)
            logger.debug(f"Added {len(results)} development plan sources to context")

        formatted_results = format_development_plans_results(results, include_distance=True)
        return (
            f"Development Plans within {radius_km}km of location "
            f"in {city.title()}:\n\n{formatted_results}"
        )

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying development plans by proximity: {e}")
        return f"Error querying development plans by proximity: {str(e)}"

