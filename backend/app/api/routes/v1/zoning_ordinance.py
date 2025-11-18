from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.utils.query_vectordb import VectorDBQuery
from app.utils.zoning_map_spatial_query import ZoningMapSpatialQuery
from app.core.config import settings

router = APIRouter(prefix="/zoning_ordinance", tags=["zoning-ordinance"])


@router.get("/search")
def search_zoning_ordinance(
    city: str = Query(..., description="City name (e.g., 'boston', 'cambridge')"),
    question: str = Query(..., description="Your question about zoning ordinances"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
    similarity_threshold: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    ),
) -> Dict[str, Any]:
    """
    Search zoning ordinance documents using semantic search.

    This endpoint:
    1. Converts your question to an embedding using Vertex AI
    2. Searches the pgvector database for similar text chunks
    3. Returns the most relevant zoning ordinance information

    Args:
        city: City name to search in
        question: Your natural language question
        top_k: How many results to return (1-20)
        similarity_threshold: Minimum similarity score (0=any, 1=exact match)

    Returns:
        Dictionary with:
        - query: The original question
        - city: The city searched
        - results: List of matching zoning ordinance chunks with scores
        - count: Number of results returned
    """
    try:
        # Initialize the vector query client
        with VectorDBQuery(
            gcp_project=settings.GCP_PROJECT,
            gcp_region=settings.GCP_REGION,
        ) as query_client:
            # Search the vector database
            results = query_client.query_zoning_ordinance(
                query_text=question,
                city=city,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            return {
                "query": question,
                "city": city,
                "results": results,
                "count": len(results),
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search/filtered")
def search_zoning_ordinance_filtered(
    city: str = Query(..., description="City name"),
    question: str = Query(..., description="Your question"),
    top_k: int = Query(5, ge=1, le=20),
    zoning_codes: List[str] | None = Query(
        None, description="Filter by specific zoning codes (e.g., ['R1', 'R2'])"
    ),
    document_title_contains: str | None = Query(
        None, description="Filter by document title substring"
    ),
) -> Dict[str, Any]:
    """
    Search zoning ordinances with additional filters.

    This allows you to narrow down results by:
    - Specific zoning codes (e.g., residential, commercial)
    - Document title keywords

    Args:
        city: City name to search in
        question: Your natural language question
        top_k: How many results to return
        zoning_codes: Optional list of zoning codes to filter by
        document_title_contains: Optional text to filter document titles

    Returns:
        Dictionary with filtered search results
    """
    try:
        with VectorDBQuery(
            gcp_project=settings.GCP_PROJECT,
            gcp_region=settings.GCP_REGION,
        ) as query_client:
            results = query_client.query_with_filters(
                query_text=question,
                city=city,
                top_k=top_k,
                zoning_codes=zoning_codes,
                document_title_contains=document_title_contains,
            )

            return {
                "query": question,
                "city": city,
                "filters": {
                    "zoning_codes": zoning_codes,
                    "document_title_contains": document_title_contains,
                },
                "results": results,
                "count": len(results),
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search/by-location")
def search_zoning_ordinance_by_location(
    city: str = Query(..., description="City name"),
    question: str = Query(..., description="Your question about zoning ordinances"),
    latitude: float = Query(..., description="Latitude of the location", ge=-90, le=90),
    longitude: float = Query(
        ..., description="Longitude of the location", ge=-180, le=180
    ),
    top_k: int = Query(5, ge=1, le=20),
    similarity_threshold: float = Query(0.0, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """
    Search zoning ordinances by location (latitude/longitude).

    This endpoint:
    1. Finds which zoning codes apply to the given location using PostGIS spatial query
    2. Generates embeddings for your question using Vertex AI
    3. Searches for relevant zoning ordinance text filtered by those zoning codes
    4. Returns ordinances specific to your location

    Args:
        city: City name to search in
        question: Your natural language question about zoning
        latitude: Latitude of the location (e.g., 42.3601)
        longitude: Longitude of the location (e.g., -71.0589)
        top_k: How many results to return (1-20)
        similarity_threshold: Minimum similarity score (0=any, 1=exact match)

    Returns:
        Dictionary with:
        - location: The queried location (lat, lon)
        - zoning_codes: List of zoning codes found at the location
        - results: List of matching zoning ordinance chunks with scores
        - count: Number of results returned
    """
    try:
        with VectorDBQuery(
            gcp_project=settings.GCP_PROJECT,
            gcp_region=settings.GCP_REGION,
        ) as query_client:
            result = query_client.query_by_location(
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
                **result,
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/zoning-info/by-location")
def get_zoning_info_by_location(
    city: str = Query(..., description="City name"),
    latitude: float = Query(..., description="Latitude of the location", ge=-90, le=90),
    longitude: float = Query(
        ..., description="Longitude of the location", ge=-180, le=180
    ),
) -> Dict[str, Any]:
    """
    Get zoning information (codes and geodata) for a specific location.

    This endpoint uses PostGIS spatial queries to find which zoning areas contain
    the given point and returns complete zoning information including geometries.

    Args:
        city: City name
        latitude: Latitude of the location
        longitude: Longitude of the location

    Returns:
        Dictionary with:
        - location: The queried location
        - zoning_data: List of zoning areas containing the point with full geodata
        - count: Number of zoning areas found
    """
    try:
        with ZoningMapSpatialQuery() as spatial_query:
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
