
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
        return City.BOSTON

    def resource_url(self) -> str:
        return "https://gis.data.mass.gov/datasets/boston::2020-census-tracts-in-boston/explore"
    
    def geoid_column(self) -> str:
        return "geoid20"
    

    
    def upload_to_gcs(self, file_path: str):
        """Upload the file to GCS."""
        self.gcp_storage.upload_file(file_path=file_path, destination_path=f"{self.gcp_storage_parent_directory()}/{file_path.name}")
    
    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the geopandas dataframe to the database."""
        # Create table if needed (database is auto-created on first connect)
        self._create_census_tract_table(self.db)

        # Ensure GeoDataFrame is in the correct CRS
        gdf = self._ensure_crs(gdf)

        # Insert each row
        city = self.city().lower()
        geoid_col = self.geoid_column()

        self.logger.info(f"Uploading {len(gdf)} census tracts to database...")

        for _, row in gdf.iterrows():
            geoid = row[geoid_col]
            # Convert geometry to WKT (Well-Known Text)
            geometry_wkt = row['geometry'].wkt

            self._insert_census_tract(self.db, city, geoid, geometry_wkt)

        self.logger.info(f"Successfully uploaded {len(gdf)} census tracts for {city}")

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
        """Download census tract data by clicking the Download button."""
        try:
            self.logger.info(f"Navigating to: {self.resource_url()}")
            self.selenium_util.driver.get(self.resource_url())

            # Wait for page to fully load
            time.sleep(5)  # Give ArcGIS Hub time to fully render

            self.logger.info("Page loaded, looking for Download button...")

            # Try multiple selectors for the Download button
            download_button = None
            selectors = [
                "//button[contains(@class, 'btn-info') and contains(., 'Download')]",
                "//button[contains(@class, 'btn') and normalize-space(.)='Download']",
                "//button[contains(@class, 'btn') and contains(., 'Download')]",
                "//button[contains(text(), 'Download')]",
            ]

            for selector in selectors:
                try:
                    download_button = WebDriverWait(self.selenium_util.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.logger.info(f"Found Download button with selector: {selector}")
                    break
                except:
                    continue

            if not download_button:
                raise Exception("Could not find Download button with any selector")

            self.logger.info("Clicking Download button...")
            download_button.click()

            # Wait for download options to appear (in shadow DOM)
            self.logger.info("Waiting for download options to appear...")
            time.sleep(3)

            # Find and click GeoJSON download button using JavaScript (to access shadow DOM)
            self.logger.info("Finding and clicking GeoJSON download button in shadow DOM...")
            script = """
            // Find all download list items
            const downloadList = document.querySelector('arcgis-hub-download-list');
            if (!downloadList || !downloadList.shadowRoot) return false;

            const items = downloadList.shadowRoot.querySelectorAll('arcgis-hub-download-list-item');

            // Find the GeoJSON item and click its button
            for (const item of items) {
                if (!item.shadowRoot) continue;

                const title = item.shadowRoot.querySelector('.download-option-card-title');
                if (title && title.textContent.includes('GeoJSON')) {
                    // Find the button inside this item and click it
                    const button = item.shadowRoot.querySelector('calcite-button');
                    if (button && button.shadowRoot) {
                        const nativeButton = button.shadowRoot.querySelector('button');
                        if (nativeButton) {
                            nativeButton.click();
                            return true;
                        }
                    }
                }
            }
            return false;
            """

            clicked = self.selenium_util.driver.execute_script(script)

            if not clicked:
                raise Exception("Could not find or click GeoJSON download button in shadow DOM")

            self.logger.info("Download started...")
            # Wait for download to complete by checking for file in download directory
            return self._wait_for_download_complete()

        except Exception as e:
            self.logger.error(f"Error during download: {e}")
            # Save screenshot for debugging
            try:
                screenshot_path = Path(self.download_directory()) / "error_screenshot.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                self.selenium_util.driver.save_screenshot(str(screenshot_path))
                self.logger.error(f"Screenshot saved to: {screenshot_path}")
            except Exception as screenshot_error:
                self.logger.error(f"Could not save screenshot: {screenshot_error}")
            raise

    def collect(self):
        # Download the file
        downloaded_file = self.download_file()

        # Upload to GCS
        self.upload_to_gcs(downloaded_file)

        # Parse to GeoDataFrame and upload to database
        gdf = gpd.read_file(downloaded_file)
        self.upload_to_db(gdf)

        self.logger.info(f"Collection complete for {self.city()}")
        