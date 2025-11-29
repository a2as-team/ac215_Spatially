"""Query census data filtered by GeoJSON polygon."""

from typing import Optional, Union
import logging
import json
from app.utils.db_accessor import DBConnector
from app.core.config import settings
from .query_census_by_geoids import query_census_by_geoids

logger = logging.getLogger(__name__)


def query_census_by_geojson(
    question: str,
    geojson: Union[str, dict],
    city: str,
    year: Optional[int] = None,
) -> str:
    """
    Query census data for census tracts within a GeoJSON polygon.

    Use this tool when you want to get demographic data for a specific
    geographic area defined by a GeoJSON polygon (e.g., a zoning district).

    Args:
        question: Natural language question about census/demographic data
        geojson: GeoJSON polygon as string or dict defining the area of interest
        city: City name for context
        year: Optional year for the ACS data

    Returns:
        A formatted string with the census data results for tracts
        that intersect with the provided polygon.

    Examples:
        - question: "What is the median household income?"
          geojson: {"type": "Polygon", "coordinates": [...]}
    """
    try:
        # Parse GeoJSON if string
        if isinstance(geojson, str):
            geojson = json.loads(geojson)

        geojson_str = json.dumps(geojson)
        logger.info(f"Census query by GeoJSON: {question}, city: {city}")

        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            # Find census tracts that intersect with the polygon
            tract_query = """
                SELECT DISTINCT ct.geoid
                FROM census_tract ct
                WHERE ST_Intersects(
                    ct.geom,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                )
            """
            tract_results = db.execute(tract_query, (geojson_str,))

            if not tract_results:
                return f"No census tracts found within the specified area in {city}."

            geoids = [row["geoid"] for row in tract_results]
            logger.info(f"Found {len(geoids)} census tracts in the polygon")

            # Now query census data for these tracts
            return query_census_by_geoids(
                question=question,
                geoids=geoids,
                year=year,
            )

        finally:
            db.close()

    except json.JSONDecodeError as e:
        return f"Invalid GeoJSON format: {str(e)}"
    except Exception as e:
        logger.error(f"Error querying census by GeoJSON: {e}")
        return f"Error querying census data: {str(e)}"
