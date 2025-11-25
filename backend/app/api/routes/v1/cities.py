from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.utils.db_accessor import DBConnector
from app.core.config import settings

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("/")
def get_cities() -> Dict[str, Any]:
    """
    Get all available cities in the database.

    Returns a list of all cities that have zoning data available.
    Each city includes:
    - id: Unique city identifier
    - name: City name
    - created_at: When the city data was added

    Returns:
        Dictionary with:
        - cities: List of city objects
        - count: Number of cities available
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        cities = db.get_all_cities()

        # Convert datetime to ISO format string for JSON serialization
        for city in cities:
            if city.get("created_at"):
                city["created_at"] = city["created_at"].isoformat()

        db.close()

        return {
            "cities": cities,
            "count": len(cities),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve cities: {str(e)}"
        )


@router.get("/{city_name}")
def get_city(city_name: str) -> Dict[str, Any]:
    """
    Get information about a specific city.

    Args:
        city_name: Name of the city (case-insensitive)

    Returns:
        Dictionary with:
        - id: City ID
        - name: City name
        - created_at: When the city data was added
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        city_id = db.get_city_id(city_name)

        if city_id is None:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

        # Get full city details
        results = db.execute(
            "SELECT id, name, created_at FROM cities WHERE id = %s", (city_id,)
        )

        if not results:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

        city = dict(results[0])
        if city.get("created_at"):
            city["created_at"] = city["created_at"].isoformat()

        db.close()

        return city

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve city: {str(e)}"
        )
