"""Query zoning ordinance using semantic search."""

from typing import Optional, List
import logging
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_zoning_results

logger = logging.getLogger(__name__)


def query_zoning_ordinance(
    question: str,
    city: str,
    zoning_codes: Optional[List[str]] = None,
    top_k: int = 5,
) -> str:
    """
    Search zoning ordinance documents using semantic similarity.

    Use this tool when the user asks about:
    - Zoning regulations and rules
    - What is allowed or prohibited in a zoning district
    - Building height, setback, or density requirements
    - Land use permissions (residential, commercial, industrial)
    - Zoning code definitions and descriptions
    - Special permits or variances
    - Parking requirements
    - Any questions about local zoning laws and ordinances

    Args:
        question: Natural language question about zoning regulations
        city: City name (e.g., "boston", "cambridge")
        zoning_codes: Optional list of specific zoning codes to filter by
                     (e.g., ["R-1", "B-2", "C-1"])
        top_k: Number of relevant passages to return (default: 5)

    Returns:
        A formatted string with relevant zoning ordinance passages.

    Examples:
        - "What are the height restrictions for residential buildings?"
        - "Can I build a restaurant in zone B-2?"
        - "What is the minimum lot size for R-1 zoning?"
    """
    try:
        logger.info(f"Zoning query: {question}, city: {city}, codes: {zoning_codes}")

        vector_query = ZoningOrdinanceVectorQuery(db_name=settings.POSTGRES_DB)

        results = vector_query.query(
            query_text=question,
            city=city.lower(),
            top_k=top_k,
            zoning_codes=zoning_codes,
        )

        if not results:
            return f"No zoning ordinance information found for '{question}' in {city}."

        formatted_results = format_zoning_results(results)
        return f"Zoning Ordinance Results for {city.title()}:\n{formatted_results}"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying zoning ordinance: {e}")
        return f"Error querying zoning ordinance: {str(e)}"
