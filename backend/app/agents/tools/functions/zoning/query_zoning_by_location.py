"""Query zoning ordinance by location coordinates."""

import logging
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_zoning_results
from app.agents.manager import get_current_context

logger = logging.getLogger(__name__)


def query_zoning_by_location(
    question: str,
    latitude: float,
    longitude: float,
    city: str,
    top_k: int = 5,
) -> str:
    """
    Search zoning ordinance documents for a specific geographic location.

    Use this tool when the user provides coordinates or a specific address
    and wants to know what zoning regulations apply to that location.

    Args:
        question: Natural language question about zoning at this location
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        city: City name (e.g., "boston", "cambridge")
        top_k: Number of relevant passages to return (default: 5)

    Returns:
        A formatted string with relevant zoning ordinance passages
        for the zoning district(s) at that location.

    Examples:
        - "What can I build at this location?"
        - "What are the zoning restrictions here?"
    """
    try:
        logger.info(
            f"Location-based zoning query: {question}, "
            f"lat: {latitude}, lon: {longitude}, city: {city}"
        )

        vector_query = ZoningOrdinanceVectorQuery(db_name=settings.POSTGRES_DB)

        results = vector_query.query_by_location(
            query_text=question,
            latitude=latitude,
            longitude=longitude,
            city=city.lower(),
            top_k=top_k,
        )

        if not results:
            return (
                f"No zoning ordinance information found for the location "
                f"({latitude}, {longitude}) in {city}."
            )

        # Store results in agent context for frontend access
        context = get_current_context()
        context.get_store("ordinances").add(results)

        formatted_results = format_zoning_results(results)
        return (
            f"Zoning Ordinance Results for location ({latitude}, {longitude}) "
            f"in {city.title()}:\n{formatted_results}"
        )

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying zoning by location: {e}")
        return f"Error querying zoning by location: {str(e)}"
