"""
Database initialization module for the collector.

This module initializes the database and populates the cities table
by scraping city data from Zoneomics using Selenium.

Steps:
1. Creates the database if it doesn't exist
2. Enables PostGIS extension
3. Creates the cities table
4. Scrapes cities from Zoneomics and populates the table
"""

import os
import sys
import logging
import time
import re

from utils.db_accessor import DBAccessor

# Try to import Selenium, fall back gracefully if not available
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Try to import Playwright as fallback
try:
    from utils.playwright_util import PlaywrightUtil
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class DatabaseInitializer:
    """
    Handles database initialization including table creation and city population.
    """

    BASE_URL = "https://www.zoneomics.com"

    # US states with their URL slugs
    US_STATES = [
        ("Alabama", "alabama"),
        ("Alaska", "alaska"),
        ("Arizona", "arizona"),
        ("Arkansas", "arkansas"),
        ("California", "california"),
        ("Colorado", "colorado"),
        ("Connecticut", "connecticut"),
        ("Delaware", "delaware"),
        ("Florida", "florida"),
        ("Georgia", "georgia"),
        ("Hawaii", "hawaii"),
        ("Idaho", "idaho"),
        ("Illinois", "illinois"),
        ("Indiana", "indiana"),
        ("Iowa", "iowa"),
        ("Kansas", "kansas"),
        ("Kentucky", "kentucky"),
        ("Louisiana", "louisiana"),
        ("Maine", "maine"),
        ("Maryland", "maryland"),
        ("Massachusetts", "massachusetts"),
        ("Michigan", "michigan"),
        ("Minnesota", "minnesota"),
        ("Mississippi", "mississippi"),
        ("Missouri", "missouri"),
        ("Montana", "montana"),
        ("Nebraska", "nebraska"),
        ("Nevada", "nevada"),
        ("New Hampshire", "new-hampshire"),
        ("New Jersey", "new-jersey"),
        ("New Mexico", "new-mexico"),
        ("New York", "new-york"),
        ("North Carolina", "north-carolina"),
        ("North Dakota", "north-dakota"),
        ("Ohio", "ohio"),
        ("Oklahoma", "oklahoma"),
        ("Oregon", "oregon"),
        ("Pennsylvania", "pennsylvania"),
        ("Rhode Island", "rhode-island"),
        ("South Carolina", "south-carolina"),
        ("South Dakota", "south-dakota"),
        ("Tennessee", "tennessee"),
        ("Texas", "texas"),
        ("Utah", "utah"),
        ("Vermont", "vermont"),
        ("Virginia", "virginia"),
        ("Washington", "washington"),
        ("West Virginia", "west-virginia"),
        ("Wisconsin", "wisconsin"),
        ("Wyoming", "wyoming"),
    ]

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
        self.driver = None
        self.playwright_util = None

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
                state VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name);
            CREATE INDEX IF NOT EXISTS idx_cities_state ON cities(state);
        """

        self.db.execute(create_table_query)

        # Migration: ensure state column is VARCHAR(100) for full state names
        self.logger.info("Running migrations...")
        self.db.execute("""
            ALTER TABLE cities
            ALTER COLUMN state TYPE VARCHAR(100);
        """)

        self.logger.info("Cities table created successfully")

    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        if not SELENIUM_AVAILABLE:
            return False

        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

            self.driver = webdriver.Chrome(options=options)
            self.logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize Selenium: {e}")
            return False

    def _init_playwright(self):
        """Initialize Playwright as fallback."""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        try:
            self.playwright_util = PlaywrightUtil(headless=True, logger=self.logger)
            self.logger.info("Playwright initialized")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize Playwright: {e}")
            return False

    def _find_cities_selenium(self, state_name: str, state_slug: str) -> list[dict]:
        """Find cities for a state using Selenium."""
        state_url = f"{self.BASE_URL}/all-cities/usa/{state_slug}"
        self.logger.info(f"Fetching cities from {state_url}")

        try:
            self.driver.get(state_url)
            time.sleep(3)

            # Find all links
            links = self.driver.find_elements(By.TAG_NAME, "a")

            cities = []
            seen_slugs = set()

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip() if link.text else ""

                    # Match pattern: /zoning-maps/{state}/{city}
                    match = re.search(r"/zoning-maps/([^/]+)/([^/]+)/?$", href)
                    if match and match.group(1) == state_slug:
                        city_slug = match.group(2)
                        if city_slug not in seen_slugs:
                            city_name = text if text else city_slug.replace("-", " ").title()
                            cities.append({
                                "name": city_name,
                                "slug": city_slug,
                                "state": state_name,
                            })
                            seen_slugs.add(city_slug)
                except Exception:
                    continue

            return cities
        except Exception as e:
            self.logger.error(f"Error fetching cities for {state_name}: {e}")
            return []

    def _find_cities_playwright(self, state_name: str, state_slug: str) -> list[dict]:
        """Find cities for a state using Playwright."""
        state_url = f"{self.BASE_URL}/all-cities/usa/{state_slug}"
        self.logger.info(f"Fetching cities from {state_url}")

        try:
            self.playwright_util.goto(state_url, wait_until="networkidle")

            # Find all links
            links = self.playwright_util.query_selector_all("a")

            cities = []
            seen_slugs = set()

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text_content().strip() if link.text_content() else ""

                    # Match pattern: /zoning-maps/{state}/{city}
                    match = re.search(r"/zoning-maps/([^/]+)/([^/]+)/?$", href)
                    if match and match.group(1) == state_slug:
                        city_slug = match.group(2)
                        if city_slug not in seen_slugs:
                            city_name = text if text else city_slug.replace("-", " ").title()
                            cities.append({
                                "name": city_name,
                                "slug": city_slug,
                                "state": state_name,
                            })
                            seen_slugs.add(city_slug)
                except Exception:
                    continue

            return cities
        except Exception as e:
            self.logger.error(f"Error fetching cities for {state_name}: {e}")
            return []

    def _insert_city(self, city_slug: str, display_name: str, state: str):
        """
        Insert a city into the database.

        Uses simple slug by default. Only adds state suffix when there's a
        name conflict with a different state.
        """
        state_abbrev = state.lower()[:2] if state else ""

        self.db.connect()
        with self.db.conn.cursor() as cur:
            # Check if city with this slug exists
            cur.execute(
                "SELECT id, state FROM cities WHERE name = %s",
                (city_slug,),
            )
            result = cur.fetchone()

            if result:
                existing_id, existing_state = result
                # Same city and same state - skip
                if existing_state == state:
                    return

                # Conflict: same name but different state
                slug_with_state = f"{city_slug}-{state_abbrev}"

                # Check if suffixed version already exists
                cur.execute(
                    "SELECT id FROM cities WHERE name = %s",
                    (slug_with_state,),
                )
                if cur.fetchone():
                    return  # Already exists with suffix

                # Create new city with state suffix
                cur.execute(
                    """
                    INSERT INTO cities (name, display_name, state)
                    VALUES (%s, %s, %s)
                    """,
                    (slug_with_state, display_name, state),
                )
                self.db.conn.commit()
                self.logger.info(f"Created city with suffix due to conflict: {slug_with_state}")
                return

            # No existing city - create with simple slug
            cur.execute(
                """
                INSERT INTO cities (name, display_name, state)
                VALUES (%s, %s, %s)
                """,
                (city_slug, display_name, state),
            )
            self.db.conn.commit()

    def populate_cities(self, test_mode: bool = False):
        """
        Populate cities table by scraping Zoneomics.

        Args:
            test_mode: If True, only process the first state.
        """
        self.logger.info("Populating cities table from Zoneomics...")

        # Try Selenium first, then Playwright
        use_selenium = self._init_selenium()
        use_playwright = False

        if not use_selenium:
            use_playwright = self._init_playwright()

        if not use_selenium and not use_playwright:
            self.logger.error("Neither Selenium nor Playwright available. Cannot populate cities.")
            return

        browser_name = "Selenium" if use_selenium else "Playwright"
        self.logger.info(f"Using {browser_name} to scrape cities")

        states = self.US_STATES
        if test_mode:
            states = states[:1]
            self.logger.info("TEST MODE: Only processing first state")

        total_cities = 0

        for state_name, state_slug in states:
            self.logger.info(f"Processing state: {state_name}")

            if use_selenium:
                cities = self._find_cities_selenium(state_name, state_slug)
            else:
                cities = self._find_cities_playwright(state_name, state_slug)

            self.logger.info(f"Found {len(cities)} cities in {state_name}")

            for city in cities:
                self._insert_city(city["slug"], city["name"], city["state"])
                total_cities += 1

            # Be polite to the server
            time.sleep(1)

        self.logger.info(f"Populated {total_cities} cities from {len(states)} states")

        # Cleanup
        if self.driver:
            self.driver.quit()
        if self.playwright_util:
            self.playwright_util.quit()

    def run(self, populate: bool = True, test_mode: bool = False):
        """
        Execute the complete database initialization process.

        Args:
            populate: If True, populate cities from Zoneomics.
            test_mode: If True, only process first state when populating.

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

            # Populate cities from Zoneomics
            if populate:
                self.populate_cities(test_mode=test_mode)

            # Close database connection
            self.db.close()

            self.logger.info("Database initialization completed successfully!")
            return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            if self.db:
                self.db.close()
            return False
