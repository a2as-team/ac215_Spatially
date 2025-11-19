import os
from typing import List, Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values
import logging
from psycopg2.extras import RealDictCursor


class DBConnector:
    def __init__(self, db_name):
        self.conn = None
        if not db_name:
            raise ValueError("db_name is required")
        self.db_name = db_name
        self.db_user = os.environ.get("POSTGRE_USER")
        self.db_password = os.environ.get("POSTGRE_PASSWORD")
        self.db_host = os.environ.get("POSTGRE_HOST")
        self.db_port = os.environ.get("POSTGRE_PORT", "5432")
        self.logger = logging.getLogger(__name__)
        self._db_ensured = False  # Track if database existence has been checked

    def connect(self):
        """Connect to PostgreSQL database. Creates database if it doesn't exist."""
        if self.conn is None:
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
                self.logger.info(f"Connected to database: {self.db_name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to database: {e}")
                raise
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed")

    def execute(self, query, params=None):
        """
        Execute a SQL query and return results.
        For SELECT queries, returns list of results.
        For INSERT/UPDATE/DELETE, commits and returns None.
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                # Check if query returns results (SELECT queries have description)
                if cur.description:
                    return cur.fetchall()
                else:
                    # For INSERT/UPDATE/DELETE
                    self.conn.commit()
                    return None
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            self.logger.error(f"Query execution failed: {e}")
            raise

    def get_city_id(self, city_name: str) -> Optional[int]:
        try:
            results = self.execute("SELECT id FROM cities WHERE name = %s", (city_name.lower(),))
            if results:
                return results[0]["id"]
            return None
        except Exception as e:
            self.logger.error(f"Error getting city ID: {e}")
            raise

    def embedding_to_pgvector(self, embedding: List[float]) -> str:
        return "[" + ",".join(str(x) for x in embedding) + "]"
