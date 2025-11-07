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
        
        # This is for ensuring that we don't have duplicate zoning maps in the database.
        self._delete_zoning_map_for_city(self.db, self.city()) 
            
    def gcp_storage_parent_directory(self) -> str:
        """Return the GCS storage path for this collector."""
        return f"zoning_maps/{self.city()}"
    
    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        return os.path.abspath(f"tmp/zoning_maps/{self.city()}")
 
    def _create_zoning_maps_table(self):
        """Create the zoning maps table in the database with PostGIS geometry."""
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS zoning_maps (
                id SERIAL PRIMARY KEY,
                city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                code VARCHAR(100) NOT NULL,
                article VARCHAR(100),
                usage VARCHAR(100),
                geom GEOMETRY(Geometry, {self.EPSG_CODE}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_zoning_maps_city ON zoning_maps(city_id);
            CREATE INDEX IF NOT EXISTS idx_zoning_maps_code ON zoning_maps(code);
            CREATE INDEX IF NOT EXISTS idx_zoning_maps_geom ON zoning_maps USING GIST(geom);
        """)
    
    def _get_city_id(self, db: DBAccessor, city_name: str) -> int:
        """Get city_id from city name."""
        db.connect()
        with db.conn.cursor() as cur:
            cur.execute("SELECT id FROM cities WHERE name = %s", (city_name,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"City '{city_name}' not found in database")
            return result[0]
    
    # This is just for not mistakenly adding the same city
    def _delete_zoning_map_for_city(self, db: DBAccessor, city: str):
        """Delete all zoning maps for a city."""
        city_id = self._get_city_id(db, city)
        # Check if the zoning_maps table exists before attempting delete
        db.connect()
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'zoning_maps'
                )
            """)
            table_exists = cur.fetchone()[0]
            if table_exists:
                db.execute("DELETE FROM zoning_maps WHERE city_id = %s", (city_id,))
    
    
    def _insert_zoning_map(self, db: DBAccessor, city: str, code: str, article: str, usage: str, geometry_wkt: str):
        """Insert a zoning map record. Update only if geometry is different."""
        city_id = self._get_city_id(db, city)
        query = f"""
            INSERT INTO zoning_maps (city_id, code, article, usage, geom)
            VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, {self.EPSG_CODE}))
        """
        db.execute(query, (city_id, code, article, usage, geometry_wkt))
        
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
    def zoning_article_column(self) -> str:
        """Return the zoning article."""
        pass
    
    @abstractmethod
    def zoning_usage_column(self) -> str:
        """Return the zoning usage."""
        pass
    
    @abstractmethod
    def zoning_code_column(self) -> str:
        """Return the zoning code."""
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
    
