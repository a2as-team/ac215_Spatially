"""
Development Plans API Routes

This module provides REST API endpoints for querying development plan documents
using semantic vector search and NER-based entity extraction.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery

router = APIRouter(prefix="/development-plans", tags=["development-plans"])


# ==================== Pydantic Models ====================


class ExtractEntitiesRequest(BaseModel):
    """Request body for entity extraction."""

    text: str = Field(
        ...,
        description="Text to extract article references from",
        min_length=1,
    )


class ExtractEntitiesResponse(BaseModel):
    """Response containing extracted article references."""

    article_references: List[str] = Field(
        ..., description="List of unique article references found in text"
    )
    count: int = Field(..., description="Number of article references found")


# ==================== Endpoints ====================


@router.get("/search")
def search_development_plans(
    city: str = Query(..., description="City name (e.g., 'boston', 'cambridge')"),
    question: str = Query(
        ..., description="Your question about development plans"
    ),
    top_k: int = Query(
        5, ge=1, le=20, description="Number of results to return"
    ),
    similarity_threshold: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score (0-1)"
    ),
    latitude: Optional[float] = Query(
        None,
        description="Optional: Latitude to search at specific location",
        ge=-90,
        le=90,
    ),
    longitude: Optional[float] = Query(
        None,
        description="Optional: Longitude to search at specific location",
        ge=-180,
        le=180,
    ),
    radius_km: float = Query(
        1.0,
        ge=0.1,
        le=50,
        description="Search radius in kilometers (only used with lat/lon, default: 1.0)",
    ),
    article_reference: Optional[List[str]] = Query(
        None,
        description="Optional: Filter by article references (e.g., ['Article 50', 'Section 32'])",
    ),
    project_name_contains: Optional[str] = Query(
        None, description="Optional: Filter by project name substring"
    ),
    file_name_contains: Optional[str] = Query(
        None, description="Optional: Filter by file name substring"
    ),
) -> Dict[str, Any]:
    """
    Search development plans using semantic vector search.

    This endpoint supports multiple search modes:
    1. **Basic search**: Provide city + question
    2. **Location-based search**: Add latitude/longitude to find plans near that location
    3. **Article reference filter**: Add article_reference to filter by specific articles
    4. **Project/file filter**: Add project_name_contains or file_name_contains

    How it works:
    - Converts your question to an embedding using Vertex AI text-embedding-004
    - Searches the pgvector database for similar text chunks (cosine similarity)
    - If lat/lon provided: filters to development plans within radius_km of the location
    - Returns the most relevant development plan information with scores

    Args:
        city: City name to search in (e.g., "boston")
        question: Your natural language question
        top_k: How many results to return (1-20, default: 5)
        similarity_threshold: Minimum similarity score (0=any, 1=exact match)
        latitude: Optional latitude for location-based search
        longitude: Optional longitude for location-based search
        radius_km: Search radius in kilometers (default: 1.0, only used with lat/lon)
        article_reference: Optional list of article references to filter by
        project_name_contains: Optional text to filter project names (case-insensitive)
        file_name_contains: Optional text to filter file names (case-insensitive)

    Returns:
        Dictionary with:
        - query: The original question
        - city: The city searched
        - location: The location (if lat/lon provided) with radius
        - filters: Applied filters (if any)
        - results: List of matching development plan chunks with scores
        - count: Number of results returned

    Raises:
        HTTPException 404: City not found in database
        HTTPException 500: Internal server error during query

    Example:
        GET /development-plans/search?city=boston&question=What%20are%20the%20height%20restrictions?&top_k=5
        GET /development-plans/search?city=boston&question=parking%20requirements&latitude=42.3601&longitude=-71.0589&radius_km=0.5
    """
    try:
        query_client = DevelopmentPlansVectorQuery(db_name=settings.POSTGRES_DB)

        # Location-based search if lat/lon provided
        if latitude is not None and longitude is not None:
            results = query_client.query_by_location(
                query_text=question,
                latitude=latitude,
                longitude=longitude,
                city=city.lower(),
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                radius_km=radius_km,
            )

            return {
                "query": question,
                "city": city,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_km": radius_km,
                },
                "results": results,
                "count": len(results),
            }

        # Regular search with optional filters
        results = query_client.query(
            query_text=question,
            city=city.lower(),  # Normalize city name to lowercase
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            article_reference=article_reference,
            project_name_contains=project_name_contains,
            file_name_contains=file_name_contains,
        )

        response = {
            "query": question,
            "city": city,
            "results": results,
            "count": len(results),
        }

        # Only include filters in response if they were used
        if article_reference or project_name_contains or file_name_contains:
            response["filters"] = {
                "article_reference": article_reference,
                "project_name_contains": project_name_contains,
                "file_name_contains": file_name_contains,
            }

        return response

    except ValueError as e:
        # City not found or invalid parameters
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Database errors, unexpected failures
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.post("/extract-entities")
def extract_entities(
    request: ExtractEntitiesRequest,
) -> ExtractEntitiesResponse:
    """
    Extract ARTICLE_REFERENCE entities from text using NER model.

    This endpoint uses a fine-tuned BERT model (nlpaueb/legal-bert-base-uncased)
    to identify article references in development plan text.

    Useful for:
    - Pre-filtering search queries by extracting article references
    - Extracting references from user-provided text
    - Validating article reference filters before search

    The NER model can identify references like:
    - "Article 50"
    - "Section 32"
    - "Article 10, Section 5"
    - "Section 6.3.2"
    - etc.

    Args:
        request: JSON body with 'text' field containing text to analyze

    Returns:
        Dictionary with:
        - article_references: List of unique article references found
        - count: Number of references extracted

    Raises:
        HTTPException 503: NER service unavailable (model loading failed)
        HTTPException 500: Internal server error during extraction

    Example:
        POST /development-plans/extract-entities
        {
            "text": "This project requires approval under Article 50 and Section 32."
        }

        Response:
        {
            "article_references": ["Article 50", "Section 32"],
            "count": 2
        }
    """
    try:
        from app.utils.ner.development_plans_ner import DevelopmentPlansNER

        ner_service = DevelopmentPlansNER()
        article_refs = ner_service.extract_article_references(request.text)

        return ExtractEntitiesResponse(
            article_references=article_refs, count=len(article_refs)
        )

    except RuntimeError as e:
        # Model loading failed or dependencies missing
        raise HTTPException(status_code=503, detail=f"NER service unavailable: {str(e)}")
    except Exception as e:
        # Extraction errors
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.get("/projects")
def get_projects(
    city: str = Query(..., description="City name to get projects for")
) -> Dict[str, Any]:
    """
    Get all development plan projects for a city with metadata.

    Returns a list of distinct projects with aggregated information about
    each project. This is useful for:
    - Browsing available projects in a city
    - Building project filters in UI
    - Understanding data coverage
    - Exploring what development plans are available

    Args:
        city: City name to query (e.g., "boston", "cambridge")

    Returns:
        Dictionary with:
        - city: The city queried
        - projects: List of project dictionaries with:
            - project_name: Name of the development project
            - file_count: Number of files/documents in the project
            - article_references: Unique article references mentioned across project
        - count: Number of projects

    Raises:
        HTTPException 404: City not found in database
        HTTPException 500: Internal server error during query

    Example:
        GET /development-plans/projects?city=boston

        Response:
        {
            "city": "boston",
            "projects": [
                {
                    "project_name": "100 Hood Park Drive",
                    "file_count": 3,
                    "article_references": ["Article 50", "Section 32"]
                },
                ...
            ],
            "count": 25
        }
    """
    try:
        query_client = DevelopmentPlansVectorQuery(db_name=settings.POSTGRES_DB)
        projects = query_client.get_projects_by_city(city.lower())

        return {
            "city": city,
            "projects": projects,
            "count": len(projects),
        }

    except ValueError as e:
        # City not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Database errors
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )
