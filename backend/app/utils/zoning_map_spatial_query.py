"""
Utility for querying zoning map geodata using PostGIS spatial queries.
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ZoningMapSpatialQuery:
    """Query zoning map data using PostGIS spatial functions."""

    def __init__(
        self,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
        db_host: str | None = None,
        db_port: str | None = None,
    ):
        """
        Initialize ZoningMapSpatialQuery client.

        Args:
            db_name: Database name (defaults to env var APP_DB_NAME)
            db_user: Database user (defaults to env var POSTGRE_USER)
            db_password: Database password (defaults to env var POSTGRE_PASSWORD)
            db_host: Database host (defaults to env var POSTGRE_HOST)
            db_port: Database port (defaults to env var POSTGRE_PORT)
        """
        # Database configuration
        self.db_name = db_name or os.environ.get("APP_DB_NAME")
        self.db_user = db_user or os.environ.get("POSTGRE_USER")
        self.db_password = db_password or os.environ.get("POSTGRE_PASSWORD")
        self.db_host = db_host or os.environ.get("POSTGRE_HOST")
        self.db_port = db_port or os.environ.get("POSTGRE_PORT", "5432")

        if not all([self.db_name, self.db_user, self.db_password, self.db_host]):
            raise ValueError(
                "Database credentials not fully configured. "
                "Please set environment variables: APP_DB_NAME, POSTGRE_USER, "
                "POSTGRE_PASSWORD, POSTGRE_HOST"
            )

        self.conn = None

    def _connect(self):
        """Establish database connection."""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    host=self.db_host,
                    port=self.db_port,
                    sslmode="prefer",  # Use SSL if available (required for AWS RDS)
                    cursor_factory=RealDictCursor,  # Return results as dictionaries
                )
                logger.info(f"Connected to database: {self.db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.conn

    def _close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

    def _get_city_id(self, city_name: str) -> Optional[int]:
        """
        Get city_id from city name.

        Args:
            city_name: Name of the city (e.g., "boston", "cambridge")

        Returns:
            City ID or None if not found
        """
        self._connect()
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM cities WHERE name = %s", (city_name.lower(),))
            result = cur.fetchone()
            if result:
                return result["id"]
            return None

    def get_zoning_by_location(
        self,
        latitude: float,
        longitude: float,
        city: str,
    ) -> List[Dict[str, Any]]:
        """
        Get complete zoning information for a specific location.

        Args:
            latitude: Latitude of the point
            longitude: Longitude of the point
            city: City name to filter results

        Returns:
            List of dictionaries containing:
                - id: Zoning map record ID
                - code: Zoning code (e.g., "MFR", "R2")
                - article: Zoning article reference
                - usage: Zoning usage description
                - geometry: GeoJSON geometry
                - created_at: Record creation timestamp

        Raises:
            ValueError: If city not found
        """
        try:
            # Get city ID
            city_id = self._get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Query zoning_maps table with full geodata
            self._connect()
            with self.conn.cursor() as cur:
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
                        AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    ORDER BY code;
                """
                cur.execute(query, (city_id, longitude, latitude))
                results = cur.fetchall()

            if not results:
                logger.warning(
                    f"No zoning data found for location ({latitude}, {longitude}) in {city}"
                )
                return []

            # Convert geometry JSON string to dict
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

            logger.info(
                f"Found {len(zoning_data)} zoning areas at ({latitude}, {longitude}) in {city}"
            )
            return zoning_data

        except Exception as e:
            logger.error(f"Error querying zoning geodata by location: {e}")
            raise
        finally:
            self._close()

    def get_zoning_codes_by_location(
        self,
        latitude: float,
        longitude: float,
        city: str,
    ) -> List[str]:
        """
        Get only zoning codes for a specific location (lightweight query).

        Args:
            latitude: Latitude of the point
            longitude: Longitude of the point
            city: City name to filter results

        Returns:
            List of zoning codes that contain the given point

        Raises:
            ValueError: If city not found
        """
        try:
            # Get city ID
            city_id = self._get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Query zoning_maps table using PostGIS ST_Contains
            # Point is in EPSG:4326 (WGS84), same as stored geometries
            self._connect()
            with self.conn.cursor() as cur:
                query = """
                    SELECT DISTINCT code
                    FROM zoning_maps
                    WHERE city_id = %s
                        AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    ORDER BY code;
                """
                cur.execute(query, (city_id, longitude, latitude))
                results = cur.fetchall()

            if not results:
                logger.warning(
                    f"No zoning codes found for location ({latitude}, {longitude}) in {city}"
                )
                return []

            zoning_codes = [row["code"] for row in results]
            logger.info(
                f"Found zoning codes at ({latitude}, {longitude}) in {city}: {zoning_codes}"
            )
            return zoning_codes

        except Exception as e:
            logger.error(f"Error querying zoning codes by location: {e}")
            raise
        finally:
            self._close()

    def get_zoning_by_code(
        self,
        code: str,
        city: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all zoning areas with a specific code in a city.

        Args:
            code: Zoning code to search for (e.g., "MFR", "R2")
            city: City name to filter results

        Returns:
            List of zoning areas with the specified code

        Raises:
            ValueError: If city not found
        """
        try:
            # Get city ID
            city_id = self._get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            self._connect()
            with self.conn.cursor() as cur:
                query = """
                    SELECT
                        id,
                        code,
                        article,
                        usage,
                        ST_AsGeoJSON(geom) as geometry,
                        created_at
                    FROM zoning_maps
                    WHERE city_id = %s AND code = %s
                    ORDER BY id;
                """
                cur.execute(query, (city_id, code))
                results = cur.fetchall()

            # Convert geometry JSON string to dict
            zoning_data = []
            for row in results:
                data = dict(row)
                data["geometry"] = (
                    json.loads(data["geometry"]) if data["geometry"] else None
                )
                if data.get("created_at"):
                    data["created_at"] = data["created_at"].isoformat()
                zoning_data.append(data)

            logger.info(f"Found {len(zoning_data)} zoning areas with code '{code}' in {city}")
            return zoning_data

        except Exception as e:
            logger.error(f"Error querying zoning by code: {e}")
            raise
        finally:
            self._close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed."""
        self._close()
