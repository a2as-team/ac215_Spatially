from abc import ABC, abstractmethod
import logging
from template import BaseCollector
import sys
import os 
import geopandas as gpd
from utils.db_accessor import DBAccessor
from utils.gcp_storage import GCPStorage

class ZoningMapsBaseCollector(BaseCollector, ABC):
    # Standard CRS for all zoning map data
    EPSG_CODE = 4326  # WGS84 - used for database storage
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
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
            
    def gcp_storage_parent_directory(self) -> str:
        """Return the GCS storage path for this collector."""
        return f"zoning_maps/{self.city()}"
    
    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        return os.path.abspath(f"tmp/zoning_maps/{self.city()}")
    
    
    def _create_zoning_maps_table(self):
        """Create the zoning maps table in the database."""
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS zoning_maps (
                id SERIAL PRIMARY KEY,
                city VARCHAR(100) NOT NULL,
                code VARCHAR(100) NOT NULL,
            )
        """)
    
    @abstractmethod
    def city(self) -> str:
        if not self.city():
            raise ValueError("City is required")
        return self.city()
    
    @abstractmethod
    def zoning_static_resource_url(self) -> list[str]:
        """Return the URL for the zoning map static resource."""
        pass
    
    @abstractmethod
    def zoning_geospatial_resource_url(self) -> list[str]:
        """Return ther URL for the zoning map geospatial resource."""
        pass
    
    @abstractmethod
    def download_zoning_static_files(self):
        """Collect zoning map static files."""
        pass
    
    @abstractmethod
    def download_zoning_geospatial_files(self):
        """Collect zoning map geospatial files."""
        pass
    
    @abstractmethod
    def upload_to_gcs(self):
        """Upload the file to GCS."""
        pass
    
    @abstractmethod
    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the geopandas dataframe to the database."""
        pass
    
    @abstractmethod
    def collect(self):
        """Collect zoning maps data."""
        pass
    
