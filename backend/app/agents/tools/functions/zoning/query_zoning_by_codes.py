"""Query zoning ordinance filtered by specific zoning codes."""

from typing import List
import logging
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_zoning_results
from app.agents.manager import get_current_context

logger = logging.getLogger(__name__)


def query_zoning_by_codes(
    question: str,
    zoning_codes: List[str],
    city: str,
    top_k: int = 5,
) -> str:
    """
    Search zoning ordinance filtered by specific zoning codes.

    Use this tool when you have a list of zoning codes and want
    to find relevant ordinance text for those specific zones.

    Args:
        question: Natural language question about zoning regulations
        zoning_codes: List of zoning codes to filter by (e.g., ["R-1", "B-2"])
        city: City name (e.g., "boston", "cambridge")
        top_k: Number of relevant passages to return (default: 5)

    Returns:
        A formatted string with relevant zoning ordinance passages
        filtered to the specified zoning codes.

    Examples:
        - question: "What are the height limits?"
          zoning_codes: ["R-1", "R-2"]
    """
    try:
        if not zoning_codes:
            return "No zoning codes provided. Please specify at least one zoning code."

        logger.info(f"Zoning query by codes: {question}, codes: {zoning_codes}")

        vector_query = ZoningOrdinanceVectorQuery(db_name=settings.POSTGRES_DB)

        results = vector_query.query(
            query_text=question,
            city=city.lower(),
            top_k=top_k,
            zoning_codes=zoning_codes,
        )

        if not results:
            codes_str = ", ".join(zoning_codes)
            return f"No zoning ordinance information found for codes [{codes_str}] in {city}."

        # Store results in agent context for frontend access
        context = get_current_context()
        context.get_store("ordinances").add(results)

        formatted_results = format_zoning_results(results)
        codes_str = ", ".join(zoning_codes)
        return (
            f"Zoning Ordinance Results for zones [{codes_str}] "
            f"in {city.title()}:\n{formatted_results}"
        )

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying zoning by codes: {e}")
        return f"Error querying zoning data: {str(e)}"
