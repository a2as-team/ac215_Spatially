from utils.selenium import SeleniumUtil
from .base import ZoningMapsBaseCollector
from shared_config.cities import City
import time
from pathlib import Path


class BostonZoningMapsCollector(ZoningMapsBaseCollector):
    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())


    def city(self) -> str:
        return City.BOSTON
    
    def zoning_static_resource_url(self) -> list[str]:
        """This has the list of zoning map static resources."""
        return "https://www.bostonplans.org/3d-data-maps/map-library/zoning-maps?viewall=1"
    
    def zoning_geospatial_resource_url(self) -> list[str]:
        return {
            "zoning_districts": "https://gis.bostonplans.org/hosting/rest/services/Zoning_Districts/FeatureServer",
            "zoning_subdistricts": "https://gis.bostonplans.org/hosting/rest/services/Zoning_Subdistricts_Data/FeatureServer"
        }

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
        """
        Collect all zoning map PDFs from Boston Plans website.

        The page contains links to PDFs with relative URLs like:
        /getattachment/{uuid}/

        We need to:
        1. Navigate to the page
        2. Find all PDF download links
        3. Download each PDF (wait for completion)
        4. Upload to GCS (if available)
        5. Store metadata in database
        """
        import os
        from selenium.webdriver.common.by import By

        url = self.zoning_static_resource_url()
        self.logger.info(f"Collecting zoning maps from: {url}")

        # Create download directory
        os.makedirs(self.download_directory(), exist_ok=True)

        # Navigate to the page
        self.selenium_util.get(url)
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
                title = link.text.strip()

                if not title:
                    # Try to get title from parent or sibling elements
                    title = f"Zoning_Map_{idx}"

                self.logger.info(f"[{idx}/{len(links)}] Downloading: {title}")

                # Click to start download
                link.click()

                # Wait for the download to complete
                downloaded_file = self._wait_for_download_complete(expected_extension='.pdf', timeout=30)

                # Rename the file to a clean name
                clean_filename = f"{title.replace(' ', '_').replace('/', '-')}.pdf"
                final_filepath = Path(self.download_directory()) / clean_filename

                # Rename if different
                if downloaded_file.name != clean_filename:
                    downloaded_file.rename(final_filepath)
                    self.logger.info(f"Renamed to: {clean_filename}")
                else:
                    final_filepath = downloaded_file

                # Store metadata
                downloaded_files.append({
                    "title": title,
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
        """
        Collect geospatial data from ArcGIS FeatureServer endpoints.

        Downloads GeoJSON data from each layer in the FeatureServer and saves it locally.
        The data can then be uploaded to GCS for further processing.
        """
        from utils.featureserver_downloader import FeatureServerDownloader
        import os

        urls = self.zoning_geospatial_resource_url()
        self.logger.info(f"Collecting geospatial data from {len(urls)} FeatureServer endpoints")

        # Create download directory
        os.makedirs(self.download_directory(), exist_ok=True)

        # Initialize the downloader utility
        downloader = FeatureServerDownloader(logger=self.logger, epsg_code=self.EPSG_CODE)

        all_downloaded_files = []

        # Download from each FeatureServer endpoint
        for resource_name, base_url in urls.items():
            try:
                self.logger.info(f"Processing FeatureServer: {resource_name}")

                # Download all layers from this FeatureServer
                downloaded_files = downloader.download_all_layers(
                    base_url=base_url,
                    output_dir=self.download_directory(),
                    filename_prefix=resource_name,
                    use_pagination=False  # Set to True if datasets are very large
                )

                # Enhance metadata with title for consistency with other methods
                for file_info in downloaded_files:
                    file_info['title'] = f"{resource_name} - {file_info['layer_name']}"
                    file_info['url'] = f"{base_url}/{file_info['layer_id']}/query"

                all_downloaded_files.extend(downloaded_files)

            except Exception as e:
                self.logger.error(f"Error processing {resource_name}: {e}")
                continue

        # Upload downloaded files to GCS

        self.logger.info(f"Successfully collected {len(all_downloaded_files)} geospatial layers")
        return all_downloaded_files
    
    def upload_to_gcs(self, file_infos: list[dict], folder_name: str):
        """Upload the files to GCS."""
        for file_info in file_infos:
            self.gcp_storage.upload_file(
                file_path=file_info["filepath"],
                destination_path=f"{self.gcp_storage_parent_directory()}/{file_info['filename']}"
            )
    
    def upload_to_db(self, file_infos: list[dict]):
        """Upload the files to the database."""
        for file_info in file_infos:
            self.db.execute(
                "INSERT INTO zoning_maps (filename, filepath) VALUES (%s, %s)",
                (file_info["filename"], file_info["filepath"])
            )

    def collect(self):
        """
        Collect zoning maps data.
        """
        static_files = self.download_zoning_static_files()
        geospatial_files = self.download_zoning_geospatial_files()

        self.upload_to_gcs(static_files)
        self.upload_to_gcs(geospatial_files)