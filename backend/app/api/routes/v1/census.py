from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import asyncio
import logging
from app.utils.spatial_query.census_tract import CensusTractSpatialQuery
from app.core.config import settings

router = APIRouter(prefix="/census", tags=["census"])
logger = logging.getLogger(__name__)


@router.get("/search")
def search_census(
    question: str = Query(..., description="Your question about census data"),
    city: Optional[str] = Query(None, description="Optional: City name to filter results (e.g., 'boston', 'cambridge')"),
    latitude: Optional[float] = Query(None, description="Optional: Latitude to search at specific location", ge=-90, le=90),
    longitude: Optional[float] = Query(None, description="Optional: Longitude to search at specific location", ge=-180, le=180),
    year: Optional[int] = Query(
        None,
        ge=2000,
        le=2100,
        description="Optional: Census year to focus on (e.g., 2020)",
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results to return"),
) -> Dict[str, Any]:
    """
    Search census data using natural language queries with SQL agent.

    This endpoint uses a SQL agent powered by Gemini 2.0 Flash to answer questions
    about census data. The agent uses tools to:
    1. List available tables
    2. Check table schemas
    3. Validate SQL queries
    4. Execute SQL queries safely

    It supports multiple search modes:
    1. **Basic search**: Provide a question about census data
    2. **City-based search**: Add city name to filter results by location
    3. **Location-based search**: Add latitude/longitude to filter by specific geographic location

    How it works:
    - Uses a SQL agent with Gemini 2.0 Flash to understand your question
    - The agent automatically explores the database schema
    - Generates and validates SQL queries
    - Executes queries and returns natural language answers

    The database contains:
    - Census tracts with geographic boundaries
    - ACS (American Community Survey) tables (DP04, S1901, S2503, etc.)
    - ACS variables and values by tract, year, and release
    - Metadata about tables, variables, and releases

    Example queries:
    - "What is the median household income in Boston?"
    - "Show me rent data for census tracts in 2023"
    - "What are the poverty rates by census tract?"
    - "Find housing characteristics for areas near latitude 42.36, longitude -71.06"

    Args:
        question: Your natural language question about census data
        city: Optional city name to filter results
        latitude: Optional latitude for location-based search
        longitude: Optional longitude for location-based search
        year: Optional census year to scope the results
        limit: Maximum number of results to return (1-1000, default: 100)

    Returns:
        Dictionary with:
        - query: The original question
        - answer: The agent's natural language response
        - city: City filter if applied
        - location: Location filter if applied
    """
    try:
        # Lazy import to avoid circular dependency
        from app.agents.sql_agent.runner import SQLAgentRunner

        # If lat/long provided, find the census tract geoid
        geoid = None
        if latitude is not None and longitude is not None:
            try:
                spatial_query = CensusTractSpatialQuery(db_name=settings.POSTGRES_DB)
                geoid = spatial_query.get_census_tract_by_location(latitude, longitude)
                if geoid:
                    logger.info(f"Found census tract {geoid} for location ({latitude}, {longitude})")
                else:
                    logger.warning(f"No census tract found for location ({latitude}, {longitude})")
            except Exception as e:
                logger.warning(f"Error finding census tract for location: {e}")

        # Build the query with context
        query_parts = [question]
        if city:
            query_parts.append(f"for {city}")
        if geoid:
            # Include the geoid in the query so the SQL agent can filter by it
            query_parts.append(f"for census tract with geoid {geoid}")
        elif latitude is not None and longitude is not None:
            # Fallback to lat/long if geoid lookup failed
            query_parts.append(f"at location latitude {latitude}, longitude {longitude}")
        if year:
            query_parts.append(f"for year {year}")
        if limit != 100:
            query_parts.append(f"limit results to {limit}")

        full_question = " ".join(query_parts)

        # Create SQL agent runner
        runner = SQLAgentRunner()

        # Run the agent (synchronous wrapper for async function)
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new event loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, runner.run(full_question))
                    answer = future.result()
            else:
                answer = loop.run_until_complete(runner.run(full_question))
        except RuntimeError:
            # No event loop exists, create one
            answer = asyncio.run(runner.run(full_question))

        # Build response
        response: Dict[str, Any] = {
            "query": question,
            "answer": answer,
        }

        if city:
            response["city"] = city
        if latitude is not None and longitude is not None:
            response["location"] = {"latitude": latitude, "longitude": longitude}
            if geoid:
                response["census_tract"] = {"geoid": geoid}
        if year:
            response["year"] = year

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing census query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/")
def get_census():
    """Health check endpoint for census API."""
    return {"message": "Census API is running. Use /search endpoint to query census data."}
