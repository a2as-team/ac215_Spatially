"""Query census data using natural language."""

from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


def query_census_data(
    question: str,
    city: str,
    year: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
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
        latitude: Optional latitude coordinate for location-specific queries
        longitude: Optional longitude coordinate for location-specific queries

    Returns:
        A formatted string with the census data results or an error message.

    Examples:
        - "What is the median household income?"
        - "How many housing units are owner-occupied?"
        - "What is the population by age group?"
    """
    try:
        logger.info(f"Census query: {question}, city: {city}, year: {year}, lat: {latitude}, lon: {longitude}")

        # If lat/long provided, find the census tract geoid
        geoid = None
        if latitude is not None and longitude is not None:
            try:
                from app.utils.spatial_query.census_tract import CensusTractSpatialQuery
                from app.core.config import settings
                spatial_query = CensusTractSpatialQuery(db_name=settings.POSTGRES_DB)
                geoid = spatial_query.get_census_tract_by_location(latitude, longitude)
                if not geoid:
                    error_msg = f"No census tract found for location ({latitude}, {longitude})"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                logger.info(f"Found census tract {geoid} for location ({latitude}, {longitude})")
            except ValueError:
                raise
            except Exception as e:
                error_msg = f"Error finding census tract for location ({latitude}, {longitude}): {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e

        # Build the query with city, location, and year context
        query_parts = [question]
        if city:
            query_parts.append(f"for {city}")
        if geoid:
            # Include the geoid in the query so the SQL agent can filter by it
            query_parts.append(f"for census tract with geoid {geoid}")
        if year:
            query_parts.append(f"for year {year}")
        
        full_question = " ".join(query_parts)

        # Use SQL agent to answer the question
        # Lazy import to avoid circular dependency
        from app.agents.sql_agent.runner import SQLAgentRunner
        runner = SQLAgentRunner()
        
        # Run the agent (synchronous wrapper for async function)
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use a different approach
                # Create a new event loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, runner.run(full_question))
                    response = future.result()
            else:
                response = loop.run_until_complete(runner.run(full_question))
        except RuntimeError:
            # No event loop exists, create one
            response = asyncio.run(runner.run(full_question))
        
        return response

    except Exception as e:
        logger.error(f"Error querying census data: {e}")
        return f"Error querying census data: {str(e)}"
