from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from app.utils.vector_query.census import CensusQuery
from app.core.config import settings

router = APIRouter(prefix="/census", tags=["census"])


@router.get("/search")
def search_census(
    question: str = Query(..., description="Your question about census data"),
    city: Optional[str] = Query(None, description="Optional: City name to filter results (e.g., 'boston', 'cambridge')"),
    latitude: Optional[float] = Query(None, description="Optional: Latitude to search at specific location", ge=-90, le=90),
    longitude: Optional[float] = Query(None, description="Optional: Longitude to search at specific location", ge=-180, le=180),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results to return"),
) -> Dict[str, Any]:
    """
    Search census data using natural language queries with text-to-SQL conversion.

    This endpoint converts your natural language question into a SQL query and executes it
    against the census database. It supports multiple search modes:
    1. **Basic search**: Provide a question about census data
    2. **City-based search**: Add city name to filter results by location
    3. **Location-based search**: Add latitude/longitude to filter by specific geographic location

    How it works:
    - Converts your natural language question to SQL using Google's Gemini model
    - Executes the SQL query against the census database
    - Returns structured results with census data

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
        limit: Maximum number of results to return (1-1000, default: 100)

    Returns:
        Dictionary with:
        - query: The original question
        - sql: The generated SQL query
        - results: List of census data results
        - count: Number of results returned
        - city: City filter if applied
        - location: Location filter if applied
    """
    try:
        query_client = CensusQuery(db_name=settings.POSTGRES_DB)

        # Location-based search if lat/lon provided
        if latitude is not None and longitude is not None:
            results = query_client.query_by_location(
                user_query=question,
                latitude=latitude,
                longitude=longitude,
                limit=limit,
            )
            return results

        # Regular search with optional city filter
        results = query_client.query(
            user_query=question,
            city=city,
            limit=limit,
        )

        return results

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/")
def get_census():
    """Health check endpoint for census API."""
    return {"message": "Census API is running. Use /search endpoint to query census data."}
