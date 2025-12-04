"""Query development plans using semantic search - city-wide."""

from typing import Optional, List
import logging
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery
from app.core.config import settings
from app.agents.tools.formatters import format_development_plans_results

logger = logging.getLogger(__name__)


def query_development_plans(
    question: str,
    city: str,
    article_reference: Optional[List[str]] = None,
    project_name_contains: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """
    Search development plans documents using semantic similarity.

    Use this tool when the user asks about:
    - Proposed development projects and their details
    - Project descriptions, uses, and specifications
    - Development approvals and requirements
    - Article references in development plans (ONLY filter if explicitly requested)
    - Project timelines and status
    - Development proposals in specific areas

    IMPORTANT: Only use the article_reference filter when the user explicitly
    mentions specific articles (e.g., "show me projects requiring Article 50").
    Do NOT apply this filter for general queries.

    Args:
        question: Natural language question about development plans
        city: City name (e.g., "boston", "cambridge")
        article_reference: Optional list of article references to filter by
                          (e.g., ["Article 50", "Section 32"])
                          ONLY use when explicitly requested by user
        project_name_contains: Optional project name filter
        top_k: Number of relevant passages to return (default: 5)

    Returns:
        A formatted string with relevant development plan passages.

    Examples:
        - "What development projects are proposed in the city?"
        - "What does Article 50 require?" (use article_reference=["Article 50"])
        - "Show me details about the Hood Park Drive project"
    """
    try:
        logger.info(
            f"Development plans query: {question}, city: {city}, "
            f"article_ref: {article_reference}, project: {project_name_contains}"
        )

        vector_query = DevelopmentPlansVectorQuery(db_name=settings.POSTGRES_DB)

        results = vector_query.query(
            query_text=question,
            city=city.lower(),
            top_k=top_k,
            article_reference=article_reference,
            project_name_contains=project_name_contains,
        )

        if not results:
            return f"No development plans information found for '{question}' in {city}."

        formatted_results = format_development_plans_results(results)
        return f"Development Plans Results for {city.title()}:\n\n{formatted_results}"

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying development plans: {e}")
        return f"Error querying development plans: {str(e)}"

