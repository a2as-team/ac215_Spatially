from typing import Optional
from app.utils.db_accessor import DBConnector
import logging


class CensusTractSpatialQuery:
    def __init__(self, db_name):
        self.logger = logging.getLogger(__name__)
        self.db = DBConnector(db_name)

    def get_census_tract_by_location(
        self, latitude: float, longitude: float
    ) -> Optional[str]:
        """
        Find the census tract geoid that contains a given point (latitude, longitude).
        
        Args:
            latitude: Latitude of the point
            longitude: Longitude of the point
            
        Returns:
            Census tract geoid (string) or None if no tract found
        """
        try:
            query = """
                SELECT geoid
                FROM census_tracts
                WHERE ST_Contains(
                    geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                );
            """
            results = self.db.execute(query, (longitude, latitude))

            if not results:
                self.logger.warning(
                    f"No census tract found for location ({latitude}, {longitude})"
                )
                return None

            geoid = results[0]["geoid"]
            self.logger.info(
                f"Found census tract {geoid} at ({latitude}, {longitude})"
            )
            return geoid
        except Exception as e:
            self.logger.error(f"Error querying census tract by location: {e}")
            raise
        finally:
            self.db.close()

