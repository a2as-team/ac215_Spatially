"""Get zoning codes at a specific location."""

from typing import List
import logging
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_zoning_codes_at_location(
    latitude: float,
    longitude: float,
    city: str,
) -> List[dict]:
    """
    Get the zoning codes at a specific location.

    This is a helper function that returns the raw zoning code data
    rather than formatted text. Useful for getting zoning codes to
    pass to other functions.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        city: City name (e.g., "boston", "cambridge")

    Returns:
        List of zoning code dictionaries with 'code' and other attributes.
        Returns empty list if no codes found or on error.

    Example:
        codes = get_zoning_codes_at_location(42.3601, -71.0589, "boston")
        # Returns: [{"code": "R-1", "description": "Residential"}, ...]
    """
    try:
        spatial_query = ZoningMapSpatialQuery(db_name=settings.POSTGRES_DB)
        return spatial_query.get_zoning_by_location(
            latitude=latitude,
            longitude=longitude,
            city=city.lower(),
        )
    except Exception as e:
        logger.error(f"Error getting zoning codes at location: {e}")
        return []
