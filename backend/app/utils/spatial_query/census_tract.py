from typing import Any, Dict, Optional
from app.utils.db_accessor import DBConnector
import json
import logging


class CensusTractSpatialQuery:
    def __init__(self, db_name):
        self.logger = logging.getLogger(__name__)
        self.db = DBConnector(db_name)

    def get_census_tract_by_location(
        self, latitude: float, longitude: float
    ) -> Optional[Dict[str, Any]]:
        """
        Find the census tract that contains a given point (latitude, longitude).
        
        Args:
            latitude: Latitude of the point
            longitude: Longitude of the point
            
        Returns:
            Dictionary with geoid and geometry, or None if no tract found
        """
        try:
            query = """
                SELECT 
                    geoid,
                    ST_Y(ST_Centroid(geom)) as latitude,
                    ST_X(ST_Centroid(geom)) as longitude,
                    ST_AsGeoJSON(geom) as geometry
                FROM census_tracts
                WHERE ST_DWithin(
                    ST_Centroid(geom),
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    0.001  -- ~100 meters tolerance
                );
            """
            results = self.db.execute(query, (longitude, latitude))

            if not results:
                self.logger.warning(
                    f"No census tract found for location ({latitude}, {longitude})"
                )
                return None

            row = results[0]
            tract_data = dict(row)
            tract_data["geometry"] = (
                json.loads(tract_data["geometry"]) if tract_data["geometry"] else None
            )
            # Convert datetime to ISO format string for JSON serialization
            if tract_data.get("created_at"):
                tract_data["created_at"] = tract_data["created_at"].isoformat()
            
            self.logger.info(
                f"Found census tract {tract_data['geoid']} at ({latitude}, {longitude})"
            )
            return tract_data
        except Exception as e:
            self.logger.error(f"Error querying census tract by location: {e}")
            raise
        finally:
            self.db.close()

    def get_census_tract_geoid_by_location(
        self, latitude: float, longitude: float
    ) -> Optional[str]:
        """
        Get just the geoid (census tract ID) for a given location.
        This is a convenience method for when you only need the geoid.
        
        Args:
            latitude: Latitude of the point
            longitude: Longitude of the point
            
        Returns:
            Census tract geoid (string) or None if not found
        """
        tract = self.get_census_tract_by_location(latitude, longitude)
        return tract["geoid"] if tract else None

