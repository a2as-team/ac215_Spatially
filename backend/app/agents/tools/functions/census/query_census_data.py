"""Query census data using natural language."""

from typing import Optional
import logging
from app.utils.text2sql.census import CensusText2SQL
from app.utils.db_accessor import DBConnector
from app.core.config import settings
from app.agents.tools.formatters import format_census_results

logger = logging.getLogger(__name__)


def query_census_data(
    question: str,
    city: str,
    year: Optional[int] = None,
) -> str:
    """
    Query census demographic data using natural language.

    Use this tool when the user asks about:
    - Population statistics (total population, age distribution, gender)
    - Housing data (housing units, occupancy, home values, rent)
    - Income and poverty levels
    - Employment and education statistics
    - Household composition and family structures
    - Any demographic or socioeconomic data from the American Community Survey (ACS)

    Args:
        question: Natural language question about census/demographic data
        city: City name to query data for (e.g., "boston", "cambridge")
        year: Optional year for the ACS data (e.g., 2022, 2021). If not specified,
              returns data from the most recent available year.

    Returns:
        A formatted string with the census data results or an error message.

    Examples:
        - "What is the median household income?"
        - "How many housing units are owner-occupied?"
        - "What is the population by age group?"
    """
    try:
        logger.info(f"Census query: {question}, city: {city}, year: {year}")

        # Generate SQL from natural language
        question_with_city = f"{question} (for {city})"
        text2sql = CensusText2SQL()
        sql_query = text2sql.generate_sql(user_query=question_with_city, year=year)

        # Execute the generated SQL
        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            results = db.execute(sql_query)

            if not results:
                return f"No census data found for {city} matching your query."

            formatted_results = format_census_results(results)
            return f"Census Data Results for {city.title()}:\n{formatted_results}"

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error querying census data: {e}")
        return f"Error querying census data: {str(e)}"
