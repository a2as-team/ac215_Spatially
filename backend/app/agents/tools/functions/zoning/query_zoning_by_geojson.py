"""Query zoning ordinance filtered by GeoJSON polygon."""

from typing import Union
import logging
import json
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery
from app.core.config import settings
from .query_zoning_by_codes import query_zoning_by_codes
from .query_zoning_ordinance import query_zoning_ordinance

logger = logging.getLogger(__name__)


def query_zoning_by_geojson(
    question: str,
    geojson: Union[str, dict],
    city: str,
    top_k: int = 5,
) -> str:
    """
    Search zoning ordinance for areas within a GeoJSON polygon.

    Use this tool when you want to get zoning information for a specific
    geographic area defined by a GeoJSON polygon. This will find all
    zoning codes that intersect with the polygon and search for relevant
    ordinance text.

    Args:
        question: Natural language question about zoning regulations
        geojson: GeoJSON polygon as string or dict defining the area of interest
        city: City name (e.g., "boston", "cambridge")
        top_k: Number of relevant passages to return (default: 5)

    Returns:
        A formatted string with relevant zoning ordinance passages
        for zoning districts that intersect with the polygon.

    Examples:
        - question: "What are the building requirements?"
          geojson: {"type": "Polygon", "coordinates": [...]}
    """
    try:
        # Parse GeoJSON if string
        if isinstance(geojson, str):
            geojson = json.loads(geojson)

        geojson_str = json.dumps(geojson)
        logger.info(f"Zoning query by GeoJSON: {question}, city: {city}")

        # Query zoning codes that intersect with the polygon
        spatial_query = ZoningMapSpatialQuery(db_name=settings.POSTGRES_DB)

        # Get zoning codes from the polygon
        zoning_codes = spatial_query.get_zoning_by_geojson(
            geojson=geojson_str,
            city=city.lower(),
        )

        if not zoning_codes:
            return f"No zoning districts found within the specified area in {city}."

        # Extract unique codes
        codes = list(set(z.get("code") for z in zoning_codes if z.get("code")))
        logger.info(f"Found {len(codes)} zoning codes in polygon: {codes}")

        # Now query zoning ordinance filtered by these codes
        return query_zoning_by_codes(
            question=question,
            zoning_codes=codes,
            city=city,
            top_k=top_k,
        )

    except json.JSONDecodeError as e:
        return f"Invalid GeoJSON format: {str(e)}"
    except AttributeError:
        # If get_zoning_by_geojson doesn't exist, fall back to regular query
        logger.warning("get_zoning_by_geojson not available, using regular query")
        return query_zoning_ordinance(
            question=question,
            city=city,
            top_k=top_k,
        )
    except Exception as e:
        logger.error(f"Error querying zoning by GeoJSON: {e}")
        return f"Error querying zoning data: {str(e)}"
