"""Query census data filtered by specific geoids."""

from typing import Optional, List
import logging
from app.utils.text2sql.census import CensusText2SQL
from app.utils.db_accessor import DBConnector
from app.core.config import settings
from app.agents.tools.formatters import format_census_results

logger = logging.getLogger(__name__)


def query_census_by_geoids(
    question: str,
    geoids: List[str],
    year: Optional[int] = None,
) -> str:
    """
    Query census data filtered by specific census tract geoids.

    Use this tool when you have a list of census tract IDs and want
    to get demographic data specifically for those tracts.

    Args:
        question: Natural language question about census/demographic data
        geoids: List of census tract geoids to filter by (e.g., ["25025010100", "25025010200"])
        year: Optional year for the ACS data

    Returns:
        A formatted string with the census data results.

    Examples:
        - question: "What is the total population?"
          geoids: ["25025010100", "25025010200"]
    """
    try:
        logger.info(f"Census query by geoids: {question}, geoids: {geoids[:3]}...")

        if not geoids:
            return "No geoids provided. Please specify census tract IDs."

        # Generate SQL with geoid filter
        text2sql = CensusText2SQL()
        base_query = text2sql.generate_sql(user_query=question, year=year)

        # Add geoid filter to the query
        geoid_list = ", ".join(f"'{g}'" for g in geoids)

        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            # Try to add WHERE clause for geoids
            if "WHERE" in base_query.upper():
                filtered_query = base_query.replace(
                    "WHERE", f"WHERE ct.geoid IN ({geoid_list}) AND"
                )
            else:
                filtered_query = base_query + f" WHERE ct.geoid IN ({geoid_list})"

            results = db.execute(filtered_query)

            if not results:
                return f"No census data found for the specified {len(geoids)} census tracts."

            formatted_results = format_census_results(results)
            return f"Census Data for {len(geoids)} census tracts:\n{formatted_results}"

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error querying census by geoids: {e}")
        return f"Error querying census data: {str(e)}"
