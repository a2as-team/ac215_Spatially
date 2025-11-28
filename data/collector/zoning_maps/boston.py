from utils.selenium import SeleniumUtil
from .base import ZoningMapsBaseCollector
import time
from pathlib import Path
import geopandas as gpd


class BostonZoningMapsCollector(ZoningMapsBaseCollector):
    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())

    def city(self) -> str:
        return "boston"
    
    def zoning_static_resource_url(self) -> list[str]:
        """This has the list of zoning map static resources."""
        return "https://www.bostonplans.org/3d-data-maps/map-library/zoning-maps?viewall=1"
    
    def zoning_geospatial_resource_url(self) -> list[str]:
        return "https://gis.bostonplans.org/hosting/rest/services/Zoning_Subdistricts_Data/FeatureServer"
    
    # The below 3 are the columns we will extract from the zoning map static files.
    def zoning_article_column(self) -> str:
        return "Article"
    
    def zoning_usage_column(self) -> str:
        return "Subdistrict_Use"

    def zoning_code_column(self) -> str:
        return "Zoning_Subdistrict"

    def _wait_for_download_complete(self, expected_extension='.pdf', timeout=60):
        """
        Wait for download to complete by checking for downloaded file.

        Args:
            expected_extension: The file extension to look for (e.g., '.pdf', '.zip')
            timeout: Maximum time to wait in seconds

        Returns:
            Path: Path to the downloaded file
        """
        download_dir = Path(self.download_directory())
        end_time = time.time() + timeout

        self.logger.info(f"Waiting for {expected_extension} download in: {download_dir}")

        while time.time() < end_time:
            # Check for files with expected extension
            files = list(download_dir.glob(f"*{expected_extension}"))

            # Filter out incomplete downloads (.crdownload, .tmp, .part)
            complete_files = [f for f in files if not any(
                str(f).endswith(ext) for ext in ['.crdownload', '.tmp', '.part']
            )]

            if complete_files:
                # Get the most recently modified file
                latest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                initial_size = latest_file.stat().st_size
                time.sleep(1)

                # If size hasn't changed, download is complete
                if latest_file.stat().st_size == initial_size and initial_size > 0:
                    self.logger.info(f"Download complete: {latest_file.name} ({initial_size} bytes)")
                    return latest_file

            time.sleep(0.5)

        raise TimeoutError(f"Download did not complete within {timeout} seconds")

    def download_zoning_static_files(self):
        import os
        from selenium.webdriver.common.by import By

        url = self.zoning_static_resource_url()
        self.logger.info(f"Collecting zoning maps from: {url}")

        # Create download directory
        os.makedirs(self.download_directory(), exist_ok=True)

        # Navigate to the page
        self.selenium_util.driver.get(url)
        time.sleep(3)  # Wait for page to fully load

        # Find all PDF download links
        # Looking for <a> tags with href containing "/getattachment/"
        links = self.selenium_util.driver.find_elements(
            By.XPATH,
            "//a[contains(@href, '/getattachment/')]"
        )

        self.logger.info(f"Found {len(links)} zoning map PDFs")

        downloaded_files = []

        for idx, link in enumerate(links, 1):
            try:
                # Get the link details before clicking (element might become stale)
                href = link.get_attribute("href")

                # Try multiple methods to get a meaningful title
                title = None

                # Method 1: Get text from the link itself
                link_text = link.text.strip()
                if link_text and link_text not in ['View Now', 'Download', 'PDF', 'Click Here', '']:
                    title = link_text

                # Method 2: Try to get title from aria-label attribute
                if not title:
                    aria_label = link.get_attribute("aria-label")
                    if aria_label and aria_label.strip():
                        title = aria_label.strip()

                # Method 3: Try to extract from the URL itself
                if not title and href:
                    import re
                    # URLs often look like: /getattachment/abc-def/Map-5A-Dorchester.pdf
                    url_match = re.search(r'/([^/]+\.pdf)', href, re.IGNORECASE)
                    if url_match:
                        title = url_match.group(1).replace('.pdf', '').replace('-', '_')

                # Method 4: Try parent element text
                if not title:
                    try:
                        parent_text = link.find_element(By.XPATH, '..').text.strip()
                        if parent_text and parent_text not in ['View Now', 'Download', 'PDF']:
                            title = parent_text.split('\n')[0]  # Take first line
                    except:
                        pass

                # Fallback: Use index-based name
                if not title:
                    title = f"Zoning_Map_{idx}"

                self.logger.info(f"[{idx}/{len(links)}] Downloading: {title}")

                # Clear download directory of .crdownload files before download
                download_dir = Path(self.download_directory())
                for temp_file in download_dir.glob("*.crdownload"):
                    try:
                        temp_file.unlink()
                    except:
                        pass

                # Scroll element into view and click to start download
                try:
                    self.selenium_util.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)  # Give time for scroll to complete
                    link.click()
                except Exception as click_error:
                    # If regular click fails, use JavaScript click
                    self.logger.warning(f"Regular click failed, using JavaScript click: {click_error}")
                    self.selenium_util.driver.execute_script("arguments[0].click();", link)

                # Wait for the download to complete
                downloaded_file = self._wait_for_download_complete(expected_extension='.pdf', timeout=30)

                # Use the actual downloaded filename (which is usually correct from the server)
                actual_filename = downloaded_file.name

                # Clean up the filename but keep it close to the original
                clean_filename = actual_filename.replace(' ', '_').replace('/', '-').replace('(', '').replace(')', '')
                final_filepath = Path(self.download_directory()) / clean_filename

                # Rename if different
                if downloaded_file.name != clean_filename:
                    # Check if target already exists
                    if final_filepath.exists():
                        # Add timestamp to make it unique
                        import time as time_module
                        timestamp = int(time_module.time())
                        base_name = clean_filename.replace('.pdf', '')
                        clean_filename = f"{base_name}_{timestamp}.pdf"
                        final_filepath = Path(self.download_directory()) / clean_filename

                    downloaded_file.rename(final_filepath)
                    self.logger.info(f"Renamed '{downloaded_file.name}' to '{clean_filename}'")
                else:
                    final_filepath = downloaded_file

                # Store metadata
                downloaded_files.append({
                    "title": actual_filename.replace('.pdf', ''),
                    "original_title": title,
                    "url": href,
                    "filename": clean_filename,
                    "filepath": str(final_filepath)
                })

            except Exception as e:
                self.logger.error(f"Error downloading {title if 'title' in locals() else f'link {idx}'}: {e}")
                continue

        self.logger.info(f"Successfully collected {len(downloaded_files)} zoning maps")
        return downloaded_files
    
    def download_zoning_geospatial_files(self):
        from utils.featureserver_downloader import FeatureServerDownloader
        import os

        url = self.zoning_geospatial_resource_url()
        os.makedirs(self.download_directory(), exist_ok=True)

        downloader = FeatureServerDownloader(logger=self.logger, epsg_code=self.EPSG_CODE)
        file_info = downloader.download_as_single_geojson(
            base_url=url,
            output_dir=self.download_directory(),
            merged_filename="boston_zoning.geojson",
            layer_name="Boston Zoning (Combined)"
        )

        file_info["title"] = "Boston Zoning (Combined)"
        return file_info
    
    def upload_to_db(self, gdf: gpd.GeoDataFrame):
        """Upload the files to the database."""
        self._create_zoning_maps_table()

        # let us first delete the existing zoning maps for the city
        # This is for ensuring that we don't have duplicate zoning maps in the database.


        gdf = self._ensure_crs(gdf)

        article_col = self.zoning_article_column()
        usage_col = self.zoning_usage_column()
        code_col = self.zoning_code_column()

        city = self.city()

        success_count = 0
        error_count = 0

        for idx, row in gdf.iterrows():
            try:
                article = row[article_col]
                usage = row[usage_col]
                code = row[code_col]
                geometry_wkt = row['geometry'].wkt
                self._insert_zoning_map(self.db, city, code, article, usage, geometry_wkt)
                success_count += 1
            except Exception as e:
                raise e

        self.logger.info(f"Successfully uploaded {success_count}/{len(gdf)} zoning maps to database ({error_count} errors)")

    def upload_to_gcs(self, file_path: str, gcs_filename: str):
        """Upload the files to GCS."""
        self.gcp_storage.upload_file(
            file_path=file_path,
            destination_path=f"{self.gcp_storage_parent_directory()}/{gcs_filename}"
        )
    

    
    def collect(self):
        """
        Collect zoning maps data.
        """
        static_files = self.download_zoning_static_files()
        
        for file_info in static_files:
            self.upload_to_gcs(file_path=file_info['filepath'], gcs_filename=f"static/{file_info['filename']}")

        geospatial_file = self.download_zoning_geospatial_files()
        self.upload_to_gcs(file_path=geospatial_file['filepath'], gcs_filename=f"geojson/{geospatial_file['filename']}")
        
        gdf = gpd.read_file(geospatial_file['filepath'])
        self.upload_to_db(gdf)
        
        
        self.logger.info(f"Collection complete for {self.city()}")
    