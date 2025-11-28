"""
CityService - Database-backed city registry.

This service queries the cities table in the database, making it the single
source of truth for city data. Cities are dynamically added by collectors
(e.g., zoning_codes collector) and can be queried by other collectors.

Usage:
    from shared_config.city_service import CityService

    service = CityService()

    # Get all cities
    cities = service.get_all_cities()

    # Get cities by state
    alabama_cities = service.get_cities_by_state("Alabama")

    # Check if city exists
    if service.city_exists("boston"):
        city = service.get_city("boston")

    # Get city by ID
    city = service.get_city_by_id(123)
"""

import os
import logging
from typing import Optional

import psycopg2


class CityService:
    """
    Database-backed city service.

    Provides methods to query cities from the database, which serves as the
    single source of truth for city data across all collectors.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the city service.

        Args:
            logger: Logger instance. If None, creates a new logger.
        """
        self.db_name = os.environ.get("APP_DB_NAME")
        self.db_user = os.environ.get("POSTGRE_USER")
        self.db_password = os.environ.get("POSTGRE_PASSWORD")
        self.db_host = os.environ.get("POSTGRE_HOST")
        self.db_port = os.environ.get("POSTGRE_PORT", "5432")

        if not all([self.db_name, self.db_user, self.db_password, self.db_host]):
            raise ValueError(
                "Database credentials must be set: APP_DB_NAME, POSTGRE_USER, "
                "POSTGRE_PASSWORD, POSTGRE_HOST"
            )

        self.logger = logger or logging.getLogger(__name__)
        self._conn = None

    def _connect(self):
        """Establish database connection if not already connected."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
            )

    def get_all_cities(self) -> list[dict]:
        """
        Get all cities from the database.

        Returns:
            List of city dictionaries with keys: id, name, display_name, state
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, state
                FROM cities
                ORDER BY state, display_name
            """)
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "state": row[3],
            }
            for row in rows
        ]

    def get_cities_by_state(self, state: str) -> list[dict]:
        """
        Get all cities in a specific state.

        Args:
            state: State name (e.g., "Alabama", "Massachusetts")

        Returns:
            List of city dictionaries
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, state
                FROM cities
                WHERE state = %s
                ORDER BY display_name
            """, (state,))
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "state": row[3],
            }
            for row in rows
        ]

    def get_city(self, name: str) -> Optional[dict]:
        """
        Get a city by its slug name.

        Args:
            name: City slug name (e.g., "boston", "new-york-city")

        Returns:
            City dictionary or None if not found
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, state
                FROM cities
                WHERE name = %s
            """, (name,))
            row = cur.fetchone()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "state": row[3],
            }
        return None

    def get_city_by_id(self, city_id: int) -> Optional[dict]:
        """
        Get a city by its database ID.

        Args:
            city_id: City database ID

        Returns:
            City dictionary or None if not found
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, state
                FROM cities
                WHERE id = %s
            """, (city_id,))
            row = cur.fetchone()

        if row:
            return {
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "state": row[3],
            }
        return None

    def city_exists(self, name: str) -> bool:
        """
        Check if a city exists in the database.

        Args:
            name: City slug name

        Returns:
            True if city exists, False otherwise
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM cities WHERE name = %s", (name,))
            return cur.fetchone() is not None

    def get_city_count(self) -> int:
        """
        Get the total number of cities in the database.

        Returns:
            Number of cities
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM cities")
            return cur.fetchone()[0]

    def get_states(self) -> list[str]:
        """
        Get all unique states that have cities.

        Returns:
            List of state names, sorted alphabetically
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT state
                FROM cities
                WHERE state IS NOT NULL
                ORDER BY state
            """)
            rows = cur.fetchall()

        return [row[0] for row in rows]

    def search_cities(self, query: str, limit: int = 20) -> list[dict]:
        """
        Search cities by name (case-insensitive partial match).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching city dictionaries
        """
        self._connect()
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, state
                FROM cities
                WHERE display_name ILIKE %s OR name ILIKE %s
                ORDER BY display_name
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", limit))
            rows = cur.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "display_name": row[2],
                "state": row[3],
            }
            for row in rows
        ]

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()
