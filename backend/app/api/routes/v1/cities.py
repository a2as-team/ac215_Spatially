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


@router.get("/{city_name}/zoning-codes")
def get_city_zoning_codes(city_name: str) -> Dict[str, Any]:
    """
    Get all zoning codes for a specific city.

    Args:
        city_name: Name of the city (case-insensitive)

    Returns:
        Dictionary with:
        - zoning_codes: List of zoning code objects with zone_code, zone_subtype, etc.
        - count: Number of zoning codes
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        city_id = db.get_city_id(city_name)

        if city_id is None:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

        results = db.execute(
            """
            SELECT id, zone_code, zone_subtype, area_acres, description, created_at
            FROM zoning_codes
            WHERE city_id = %s
            ORDER BY zone_code
            """,
            (city_id,),
        )

        zoning_codes = []
        if results:
            for row in results:
                code = dict(row)
                if code.get("created_at"):
                    code["created_at"] = code["created_at"].isoformat()
                if code.get("area_acres"):
                    code["area_acres"] = float(code["area_acres"])
                zoning_codes.append(code)

        db.close()

        return {
            "zoning_codes": zoning_codes,
            "count": len(zoning_codes),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve zoning codes: {str(e)}"
        )


@router.get("/{city_name}/documents")
def get_city_documents(city_name: str) -> Dict[str, Any]:
    """
    Get all unique document titles and subtitles for a specific city.

    This returns the list of available zoning ordinance documents that can be
    browsed. Each document has a title and optional subtitle.

    Args:
        city_name: Name of the city (case-insensitive)

    Returns:
        Dictionary with:
        - documents: List of document objects with title and subtitle
        - count: Number of unique documents
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        city_id = db.get_city_id(city_name)

        if city_id is None:
            raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

        # Get distinct document title/subtitle pairs
        results = db.execute(
            """
            SELECT DISTINCT document_title, document_subtitle
            FROM zoning_ordinance_embed
            WHERE city_id = %s
            ORDER BY document_title, document_subtitle
            """,
            (city_id,),
        )

        documents = []
        if results:
            for row in results:
                doc = {
                    "title": row["document_title"],
                    "subtitle": row["document_subtitle"] or "",
                }
                documents.append(doc)

        db.close()

        return {
            "documents": documents,
            "count": len(documents),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve documents: {str(e)}"
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
