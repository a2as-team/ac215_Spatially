from abc import ABC, abstractmethod
from template import BaseCollector
from utils.selenium import SeleniumUtil
from utils.db_accessor import DBAccessor
import logging
import sys
import os
import geopandas as gpd
from utils.gcp_storage import GCPStorage


class CensusTractBaseCollector(BaseCollector, ABC):
    # Standard CRS for all census tract data
    EPSG_CODE = 4326  # WGS84 - used for database storage

    def __init__(self):
        super().__init__()
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.hasHandlers():
            # Use stdout instead of stderr for Vertex AI logging
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self.logger = logger
        self.gcp_storage = None
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.db_name = os.environ.get(
            "APP_DB_NAME"
        )  # We will store the census tracts in the app database
        self.db = DBAccessor(db_name=self.db_name)
        # Understand app database as the database that we will use to store our application resources like census tracts, etc.
        if self.bucket_name and self.gcp_project:
            try:
                self.gcp_storage = GCPStorage(
                    gcp_project=self.gcp_project, bucket_name=self.bucket_name
                )
                self.logger.info("GCS connection established")
            except Exception as e:
                self.logger.warning(
                    f"Could not connect to GCS: {e}. Will operate without GCS features."
                )
        else:
            self.logger.warning(
                "GCS credentials not found (GCS_BUCKET_NAME or GCP_PROJECT). Will operate without GCS features."
            )

    @abstractmethod
    def city(self) -> str:
        """Return the city name (e.g., 'cambridge', 'boston')."""
        pass

    @abstractmethod
    def state(self) -> str:
        """Return the state name (e.g., 'Massachusetts')."""
        pass

    def gcp_storage_parent_directory(self) -> str:
        """Return the GCS storage path for this collector."""
        return f"census_tracts/{self.city()}"

    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        return os.path.abspath(f"tmp/census_tracts/{self.city()}")

    @abstractmethod
    def resource_url(self) -> str:
        pass

    @abstractmethod
    def geoid_column(self) -> str:
        pass

    @abstractmethod
    def upload_to_gcs(self):
        """Upload the data to GCS."""
        pass

    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the geopandas dataframe to the database.

        Args:
            gdf: GeoDataFrame containing census tract geometries.
        """
        # Create table if needed
        self._create_census_tract_table(self.db)

        # Ensure GeoDataFrame is in the correct CRS
        gdf = self._ensure_crs(gdf)

        # Get or create city_id
        city_id = self._get_or_create_city_id(self.city(), self.state())
        self.logger.info(f"Using city_id={city_id} for {self.city()}, {self.state()}")

        # Insert each row
        geoid_col = self.geoid_column()

        for _, row in gdf.iterrows():
            geoid = row[geoid_col]
            # Convert geometry to WKT (Well-Known Text)
            geometry_wkt = row["geometry"].wkt

            self._insert_census_tract(self.db, geoid, city_id, geometry_wkt)

    @abstractmethod
    def collect(self):
        pass

    def _create_census_tract_table(self, db: DBAccessor):
        """Create census_tract table with PostGIS geometry column."""
        try:
            db.enable_postgis()
            query = f"""
                CREATE TABLE IF NOT EXISTS census_tracts (
                    geoid VARCHAR(50) PRIMARY KEY,
                    city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                    geom GEOMETRY(Geometry, {self.EPSG_CODE}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            db.execute(query)

            # Create indexes for better query performance
            index_queries = """
                CREATE INDEX IF NOT EXISTS idx_census_tracts_geom ON census_tracts USING GIST(geom);
            """
            db.execute(index_queries)

            self.logger.info("census_tracts table created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create census_tracts table: {e}")
            raise

    def _get_or_create_city_id(self, city_name: str, state_name: str) -> int:
        """
        Get city_id from city name, or create city if it doesn't exist.

        Uses simple slug (e.g., "boston") by default for consistency with other collectors.
        Only adds state suffix (e.g., "springfield-ma") when there's a name conflict
        with a different state.

        Args:
            city_name: Name of the city.
            state_name: Name of the state.

        Returns:
            int: The city_id from the database.
        """
        city_slug = city_name.lower().replace(" ", "-")
        state_abbrev = state_name.lower()[:2] if state_name else ""

        self.db.connect()
        with self.db.conn.cursor() as cur:
            # First, check if city with this slug exists
            cur.execute(
                "SELECT id, state FROM cities WHERE name = %s",
                (city_slug,),
            )
            result = cur.fetchone()

            if result:
                existing_id, existing_state = result
                # Same city and same state - return existing
                if existing_state == state_name:
                    return existing_id

                # Conflict: same name but different state
                # Try with state suffix (e.g., "springfield-ma")
                slug_with_state = f"{city_slug}-{state_abbrev}"
                cur.execute(
                    "SELECT id FROM cities WHERE name = %s",
                    (slug_with_state,),
                )
                result_with_state = cur.fetchone()
                if result_with_state:
                    return result_with_state[0]

                # Create new city with state suffix
                cur.execute(
                    """
                    INSERT INTO cities (name, display_name, state)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (slug_with_state, city_name, state_name),
                )
                self.db.conn.commit()
                self.logger.info(
                    f"Created city with suffix due to conflict: {slug_with_state}"
                )
                return cur.fetchone()[0]

            # No existing city - create with simple slug
            cur.execute(
                """
                INSERT INTO cities (name, display_name, state)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (city_slug, city_name, state_name),
            )
            self.db.conn.commit()
            return cur.fetchone()[0]

    def _insert_census_tract(
        self, db: DBAccessor, geoid: str, city_id: int, geometry_wkt: str
    ):
        """Insert a census tract record. Update only if geometry is different.

        Args:
            db: Database accessor instance.
            geoid: The census tract GEOID.
            city_id: The city's database ID.
            geometry_wkt: The geometry in WKT format.
        """
        query = f"""
            INSERT INTO census_tracts (geoid, city_id, geom)
            VALUES (%s, %s, ST_GeomFromText(%s, {self.EPSG_CODE}))
            ON CONFLICT (geoid)
            DO UPDATE SET
                city_id = EXCLUDED.city_id,
                geom = EXCLUDED.geom,
                created_at = CURRENT_TIMESTAMP
            WHERE census_tracts.geom IS DISTINCT FROM EXCLUDED.geom
               OR census_tracts.city_id IS DISTINCT FROM EXCLUDED.city_id;
        """
        db.execute(query, (geoid, city_id, geometry_wkt))

    def _ensure_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Ensure GeoDataFrame is in the correct CRS (EPSG:4326).

        Args:
            gdf: Input GeoDataFrame

        Returns:
            GeoDataFrame reprojected to EPSG:4326 if necessary
        """
        if gdf.crs is None:
            self.logger.warning(
                f"GeoDataFrame has no CRS defined. Assuming EPSG:{self.EPSG_CODE}"
            )
            gdf = gdf.set_crs(epsg=self.EPSG_CODE)
        elif gdf.crs.to_epsg() != self.EPSG_CODE:
            self.logger.info(f"Reprojecting from {gdf.crs} to EPSG:{self.EPSG_CODE}")
            gdf = gdf.to_crs(epsg=self.EPSG_CODE)
        else:
            self.logger.info(f"GeoDataFrame already in EPSG:{self.EPSG_CODE}")

        return gdf
