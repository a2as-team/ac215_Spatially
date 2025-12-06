from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery
from app.utils.db_accessor import DBConnector
from app.utils.gcs_accessor import GCSAccessor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zoning_ordinance", tags=["zoning-ordinance"])


@router.get("/search")
def search_zoning_ordinance(
    city: str = Query(..., description="City name (e.g., 'boston', 'cambridge')"),
    question: str = Query(..., description="Your question about zoning ordinances"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
    similarity_threshold: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    ),
    latitude: float | None = Query(None, description="Optional: Latitude to search at specific location", ge=-90, le=90),
    longitude: float | None = Query(None, description="Optional: Longitude to search at specific location", ge=-180, le=180),
    zoning_codes: List[str] | None = Query(
        None, description="Optional: Filter by specific zoning codes (e.g., ['R1', 'R2'])"
    ),
    document_title_contains: str | None = Query(
        None, description="Optional: Filter by document title substring"
    ),
) -> Dict[str, Any]:
    """
    Search zoning ordinance documents using semantic search.

    This endpoint supports multiple search modes:
    1. **Basic search**: Provide city + question
    2. **Location-based search**: Add latitude/longitude to auto-filter by zoning codes at that location
    3. **Filtered search**: Add zoning_codes or document_title_contains to narrow results

    How it works:
    - Converts your question to an embedding using Vertex AI
    - Searches the pgvector database for similar text chunks
    - If lat/lon provided: automatically finds zoning codes at that location and filters
    - Returns the most relevant zoning ordinance information

    Args:
        city: City name to search in
        question: Your natural language question
        top_k: How many results to return (1-20)
        similarity_threshold: Minimum similarity score (0=any, 1=exact match)
        latitude: Optional latitude for location-based search
        longitude: Optional longitude for location-based search
        zoning_codes: Optional list of zoning codes to filter by
        document_title_contains: Optional text to filter document titles

    Returns:
        Dictionary with:
        - query: The original question
        - city: The city searched
        - location: The location (if lat/lon provided)
        - filters: Applied filters (if any)
        - results: List of matching zoning ordinance chunks with scores
        - count: Number of results returned
    """
    try:
        query_client = ZoningOrdinanceVectorQuery(db_name=settings.POSTGRES_DB)

        # Location-based search if lat/lon provided
        if latitude is not None and longitude is not None:
            results = query_client.query_by_location(
                query_text=question,
                latitude=latitude,
                longitude=longitude,
                city=city,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            return {
                "query": question,
                "city": city,
                "location": {"latitude": latitude, "longitude": longitude},
                "results": results,
                "count": len(results),
            }

        # Regular search with optional filters
        results = query_client.query(
            query_text=question,
            city=city,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            zoning_codes=zoning_codes,
            document_title_contains=document_title_contains,
        )

        response = {
            "query": question,
            "city": city,
            "results": results,
            "count": len(results),
        }

        # Only include filters in response if they were used
        if zoning_codes or document_title_contains:
            response["filters"] = {
                "zoning_codes": zoning_codes,
                "document_title_contains": document_title_contains,
            }

        return response

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/zoning")
def get_zoning_at_location(
    city: str = Query(..., description="City name"),
    latitude: float = Query(..., description="Latitude of the location", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude of the location", ge=-180, le=180),
) -> Dict[str, Any]:
    """
    Get zoning map information at a specific location.

    This endpoint uses PostGIS spatial queries to find which zoning areas contain
    the given point and returns complete zoning information including:
    - Zoning codes
    - Article references
    - Usage descriptions
    - GeoJSON geometries

    Args:
        city: City name
        latitude: Latitude of the location
        longitude: Longitude of the location

    Returns:
        Dictionary with:
        - location: The queried location
        - city: The city name
        - zoning_data: List of zoning areas containing the point with full geodata
        - count: Number of zoning areas found
    """
    try:
        spatial_query = ZoningMapSpatialQuery(db_name=settings.POSTGRES_DB)
        zoning_data = spatial_query.get_zoning_by_location(
            latitude=latitude,
            longitude=longitude,
            city=city,
        )

        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "city": city,
            "zoning_data": zoning_data,
            "count": len(zoning_data),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/document/{city}")
def get_full_document(
    city: str,
    title: str = Query(..., description="Document title"),
    subtitle: Optional[str] = Query("", description="Document subtitle (optional)"),
) -> Dict[str, Any]:
    """
    Fetch the full markdown content of a zoning ordinance document from GCS.

    This endpoint:
    1. Looks up the document metadata in the database
    2. Retrieves the GCS path from the metadata
    3. Downloads and returns the full markdown content

    Args:
        city: City name
        title: Document title
        subtitle: Document subtitle (optional)

    Returns:
        Dictionary with:
        - title: Document title
        - subtitle: Document subtitle
        - content: Full markdown content
        - city: City name
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        city_id = db.get_city_id(city)

        if city_id is None:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")

        # Get document metadata including GCS path
        results = db.execute(
            """
            SELECT DISTINCT metadata
            FROM zoning_ordinance_embed
            WHERE city_id = %s
              AND document_title = %s
              AND (document_subtitle = %s OR (%s = '' AND (document_subtitle IS NULL OR document_subtitle = '')))
            LIMIT 1
            """,
            (city_id, title, subtitle, subtitle),
        )

        db.close()

        if not results or not results[0].get("metadata"):
            raise HTTPException(
                status_code=404,
                detail=f"Document '{title}' not found for city '{city}'"
            )

        metadata = results[0]["metadata"]
        markdown_gcs_path = metadata.get("markdown_gcs_path")

        if not markdown_gcs_path:
            raise HTTPException(
                status_code=404,
                detail="Document GCS path not found in metadata"
            )

        # Download full markdown from GCS
        gcs = GCSAccessor()
        content = gcs.download_as_text(markdown_gcs_path)

        return {
            "title": title,
            "subtitle": subtitle or "",
            "content": content,
            "city": city,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch document: {str(e)}"
        )


@router.get("/{city}")
def get_zoning_map(city: str):
    """
    Get all zoning data for a city.

    Returns all zoning polygons with their geometries for visualization on a map.

    Args:
        city: City name

    Returns:
        Dictionary with:
        - city: The city name
        - zoning_data: List of all zoning areas with geometries
        - count: Number of zoning areas
    """
    try:
        zoning_query = ZoningMapSpatialQuery(db_name=settings.POSTGRES_DB)
        zoning_data = zoning_query.get_all_zoning_for_city(city)

        return {
            "city": city,
            "zoning_data": zoning_data,
            "count": len(zoning_data)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve zoning data: {str(e)}")
