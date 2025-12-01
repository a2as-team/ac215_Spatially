from typing import Any, Dict, List, Optional
from app.utils.db_accessor import DBConnector
import json
import logging


class ZoningMapSpatialQuery:
    def __init__(self, db_name):
        self.logger = logging.getLogger(__name__)
        self.db = DBConnector(db_name)

    def query(self, query):
        return self.db.execute(query)

    def get_zoning_by_location(
        self, latitude: float, longitude: float, city: str
    ) -> List[Dict[str, Any]]:
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            query = """
                SELECT
                    id,
                    code,
                    article,
                    usage,
                    ST_AsGeoJSON(geom) as geometry,
                    created_at
                FROM zoning_maps
                WHERE city_id = %s
                  AND ST_Contains(
                        geom,
                        ST_SetSRID(
                            ST_MakePoint(%s, %s),
                            4326
                        )
                    )
                ORDER BY code;
            """
            results = self.db.execute(query, (city_id, longitude, latitude))

            if not results:
                raise ValueError(
                    f"No zoning data found for location ({latitude}, {longitude}) in {city}"
                )

            zoning_data = []
            for row in results:
                data = dict(row)
                data["geometry"] = (
                    json.loads(data["geometry"]) if data["geometry"] else None
                )
                # Convert datetime to ISO format string for JSON serialization
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                zoning_data.append(data)
            self.logger.info(
                f"Found {len(zoning_data)} zoning areas at ({latitude}, {longitude}) in {city}"
            )
            return zoning_data
        except Exception as e:
            self.logger.error(f"Error querying zoning geodata by location: {e}")
            raise
        finally:
            self.db.close()

    def get_all_zoning_for_city(self, city: str) -> List[Dict[str, Any]]:
        """Get all zoning data for a city"""
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            query = """
                SELECT
                    id,
                    code,
                    article,
                    usage,
                    ST_AsGeoJSON(geom) as geometry,
                    created_at
                FROM zoning_maps
                WHERE city_id = %s
                ORDER BY code;
            """
            results = self.db.execute(query, (city_id,))

            if not results:
                self.logger.warning(f"No zoning data found for city: {city}")
                return []

            zoning_data = []
            for row in results:
                data = dict(row)
                data["geometry"] = (
                    json.loads(data["geometry"]) if data["geometry"] else None
                )
                # Convert datetime to ISO format string for JSON serialization
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                zoning_data.append(data)

            self.logger.info(f"Found {len(zoning_data)} zoning areas in {city}")
            return zoning_data
        except Exception as e:
            self.logger.error(f"Error querying all zoning data for city: {e}")
            raise
        finally:
            self.db.close()

    def get_city_id(self, city_name: str) -> Optional[int]:
        try:
            query = "SELECT id FROM cities WHERE name = %s"
            cursor = self.db.execute(query, (city_name.lower(),))
            result = cursor.fetchone()
            if result:
                return result["id"]
            return None
        except Exception as e:
            self.logger.error(f"Error getting city ID: {e}")
            raise
