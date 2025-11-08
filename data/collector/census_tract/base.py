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
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self.logger = logger
        self.gcp_storage = None
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.db_name = os.environ.get("APP_DB_NAME") # We will store the census tracts in the app database
        self.db = DBAccessor(db_name=self.db_name)
        # Understand app database as the database that we will use to store our application resources like census tracts, etc.
        if self.bucket_name and self.gcp_project:
            try:
                self.gcp_storage = GCPStorage(gcp_project=self.gcp_project, bucket_name=self.bucket_name)
                self.logger.info("GCS connection established")
            except Exception as e:
                self.logger.warning(f"Could not connect to GCS: {e}. Will operate without GCS features.")
        else:
            self.logger.warning("GCS credentials not found (GCS_BUCKET_NAME or GCP_PROJECT). Will operate without GCS features.")
    
    def city(self) -> str:
        if not self.city():
            raise ValueError("City is required")
        return self.city()
    
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
    
    @abstractmethod
    def upload_to_db(self):
        """Upload the data to the database."""
        pass

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

    def _insert_census_tract(self, db: DBAccessor, geoid: str, geometry_wkt: str):
        """Insert a census tract record. Update only if geometry is different."""
        # No, this is not correct: the VALUES clause has one too many placeholders (%s, %s, ST_GeomFromText(%s, ...)) -- 
        # geom should be set using ST_GeomFromText, so there should be only two placeholders in VALUES.
        query = f"""
            INSERT INTO census_tracts (geoid, geom)
            VALUES (%s, ST_GeomFromText(%s, {self.EPSG_CODE}))
            ON CONFLICT (geoid)
            DO UPDATE SET
                geom = EXCLUDED.geom,
                created_at = CURRENT_TIMESTAMP
            WHERE census_tracts.geom IS DISTINCT FROM EXCLUDED.geom;
        """
        db.execute(query, (geoid, geometry_wkt))

    def _ensure_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Ensure GeoDataFrame is in the correct CRS (EPSG:4326).

        Args:
            gdf: Input GeoDataFrame

        Returns:
            GeoDataFrame reprojected to EPSG:4326 if necessary
        """
        if gdf.crs is None:
            self.logger.warning(f"GeoDataFrame has no CRS defined. Assuming EPSG:{self.EPSG_CODE}")
            gdf = gdf.set_crs(epsg=self.EPSG_CODE)
        elif gdf.crs.to_epsg() != self.EPSG_CODE:
            self.logger.info(f"Reprojecting from {gdf.crs} to EPSG:{self.EPSG_CODE}")
            gdf = gdf.to_crs(epsg=self.EPSG_CODE)
        else:
            self.logger.info(f"GeoDataFrame already in EPSG:{self.EPSG_CODE}")

        return gdf