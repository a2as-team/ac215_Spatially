"""
Database initialization module for the collector.

This module provides a class-based approach to initialize the database:
1. Creates the database if it doesn't exist
2. Enables PostGIS extension
3. Creates the cities table
4. Populates the cities table with data from shared_config
"""

import os
import sys
import logging

from utils.db_accessor import DBAccessor
from shared_config.cities import CITIES


class DatabaseInitializer:
    """
    Handles database initialization including table creation and data population.
    """

    def __init__(self, db_name: str = None, logger: logging.Logger = None):
        """
        Initialize the database initializer.

        Args:
            db_name: Database name. If None, reads from APP_DB_NAME environment variable.
            logger: Logger instance. If None, creates a new logger.
        """
        self.db_name = db_name or os.environ.get("APP_DB_NAME")
        if not self.db_name:
            raise ValueError("Database name must be provided or APP_DB_NAME must be set")

        self.logger = logger or self._setup_logging()
        self.db = None

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the initializer."""
        logger = logging.getLogger(__name__)
        if not logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def create_cities_table(self):
        """Create the cities table in the database."""
        self.logger.info("Creating cities table...")

        create_table_query = """
            CREATE TABLE IF NOT EXISTS cities (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                state VARCHAR(2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name);
        """

        self.db.execute(create_table_query)
        self.logger.info("Cities table created successfully")

    def populate_cities_table(self, cities_config: dict):
        """
        Populate the cities table with data from the configuration.

        Args:
            cities_config: Dictionary of city configurations
        """
        self.logger.info("Populating cities table...")

        for city_name, city_data in cities_config.items():
            # Use INSERT ... ON CONFLICT to handle updates if city already exists
            insert_query = """
                INSERT INTO cities (name, display_name, state)
                VALUES (%s, %s, %s)
                ON CONFLICT (name)
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    state = EXCLUDED.state,
                    updated_at = CURRENT_TIMESTAMP;
            """

            self.db.execute(
                insert_query,
                (city_name, city_data['display_name'], city_data.get('state'))
            )

            self.logger.info(f"Inserted/Updated city: {city_name} ({city_data['display_name']})")

        self.logger.info(f"Successfully populated {len(cities_config)} cities")

    def run(self):
        """
        Execute the complete database initialization process.

        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        self.logger.info(f"Initializing database: {self.db_name}")

        try:
            # Initialize database accessor
            self.db = DBAccessor(db_name=self.db_name)

            # Ensure database exists
            self.db.create_database_if_not_exists()

            # Enable PostGIS extension
            self.logger.info("Enabling PostGIS extension...")
            self.db.enable_postgis()

            # Create cities table
            self.create_cities_table()

            # Populate cities table from shared_config
            self.logger.info(f"Populating cities table with {len(CITIES)} cities from shared_config")
            self.populate_cities_table(CITIES)

            # Close database connection
            self.db.close()

            self.logger.info("Database initialization completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            if self.db:
                self.db.close()
            return False
