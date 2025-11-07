
from utils.selenium import SeleniumUtil
from utils.db_accessor import DBAccessor
from .base import CensusTractBaseCollector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from shared_config.cities import City
import geopandas as gpd
import time
from pathlib import Path


class BostonCensusTractCollector(CensusTractBaseCollector):
    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())

    def city(self) -> str:
        return City.boston

    def resource_url(self) -> str:
        return "https://gis.bostonplans.org/hosting/rest/services/Hosted/Census_2020_Tracts/FeatureServer"
    
    def geoid_column(self) -> str:
        return "geoid20"

    
    def upload_to_gcs(self, file_path: str, gcs_filename: str):
        """Upload the file to GCS."""
        self.gcp_storage.upload_file(file_path=file_path, destination_path=f"{self.gcp_storage_parent_directory()}/{gcs_filename}")
    
    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the geopandas dataframe to the database."""
        # Create table if needed (database is auto-created on first connect)
        self._create_census_tract_table(self.db)

        # Ensure GeoDataFrame is in the correct CRS
        gdf = self._ensure_crs(gdf)

        # Insert each row
        geoid_col = self.geoid_column()

        for _, row in gdf.iterrows():
            geoid = row[geoid_col]
            # Convert geometry to WKT (Well-Known Text)
            geometry_wkt = row['geometry'].wkt

            self._insert_census_tract(self.db, geoid, geometry_wkt)


    def _wait_for_download_complete(self, timeout=60):
        """Wait for download to complete by checking for downloaded file."""
        download_dir = Path(self.download_directory())
        end_time = time.time() + timeout

        self.logger.info(f"Waiting for download in: {download_dir}")

        while time.time() < end_time:
            # Check for .geojson or .json files
            files = list(download_dir.glob("*.geojson")) + list(download_dir.glob("*.json"))

            # Filter out .crdownload or .tmp files (incomplete downloads)
            complete_files = [f for f in files if not any(
                str(f).endswith(ext) for ext in ['.crdownload', '.tmp', '.part']
            )]

            if complete_files:
                # Check if file is still growing (still downloading)
                latest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                initial_size = latest_file.stat().st_size
                time.sleep(1)

                # If size hasn't changed, download is complete
                if latest_file.stat().st_size == initial_size and initial_size > 0:
                    self.logger.info(f"Download complete: {latest_file.name} ({initial_size} bytes)")
                    return latest_file


            time.sleep(0.5)

        raise TimeoutError(f"Download did not complete within {timeout} seconds")

    def download_file(self):
        from utils.featureserver_downloader import FeatureServerDownloader
        import os
        url = self.resource_url()
        
        os.makedirs(self.download_directory(), exist_ok=True)
        
        # Initialize the downloader utility
        downloader = FeatureServerDownloader(logger=self.logger, epsg_code=self.EPSG_CODE)
        
        # Download the file
        try:
            self.logger.info(f"Downloading file from: {url}")
            downloaded_files = downloader.download_all_layers(
                base_url=url,
                output_dir=self.download_directory(),
                filename_prefix="census_tracts",
                use_pagination=False
            )
            for file_info in downloaded_files:
                file_info['title'] = f"census_tracts - {file_info['layer_name']}"
                file_info['url'] = f"{url}/{file_info['layer_id']}/query"
        except Exception as e:
            raise Exception(f"Error downloading census tracts file: {e}")
        
        if len(downloaded_files) == 1:
            return downloaded_files[0]
        else:
            raise Exception(f"Expected 1 downloaded file, got {len(downloaded_files)}")

    def collect(self):
        # Download the file
        downloaded_file = self.download_file()

        # Upload to GCS
        print(downloaded_file)
        self.upload_to_gcs(file_path=downloaded_file['filepath'], gcs_filename=downloaded_file['layer_name'])

        # Parse to GeoDataFrame and upload to database
        gdf = gpd.read_file(downloaded_file['filepath'])
        self.upload_to_db(gdf)

        self.logger.info(f"Collection complete for {self.city()}")
        