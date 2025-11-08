from .base import ZoningOrdinanceBaseCollector
from shared_config.cities import City
from utils.scrapers.municode_scraper import MunicodeScraper
import time

class CambridgeZoningOrdinanceCollector(ZoningOrdinanceBaseCollector):
    def __init__(self):
        super().__init__()
        self.scraper = MunicodeScraper(url=self.resource_url(), download_dir=self.download_directory())

    def city(self) -> str:
        return City.cambridge

    def resource_url(self) -> str:
        return "https://library.municode.com/ma/cambridge/codes/zoning_ordinance?nodeId=ZOORCAMA"
    
    def upload_to_gcs(self, downloaded_files: list):
        """Upload all downloaded files to GCS."""
        if not self.gcp_storage:
            self.logger.warning("GCS not configured, skipping upload")
            return

        for file_path in downloaded_files:
            # Retry logic for handling file lock issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.gcp_storage.upload_file(
                        file_path=str(file_path),
                        destination_path=f"zoning_ordinance/{self.city()}/{file_path.name}"
                    )
                    self.logger.info(f"Uploaded {file_path.name} to GCS")
                    break  # Success, exit retry loop
                except OSError as e:
                    if e.errno == 35 and attempt < max_retries - 1:
                        # Resource deadlock - wait and retry
                        self.logger.warning(f"File lock on {file_path.name}, retrying in 2s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                    else:
                        self.logger.error(f"Failed to upload {file_path.name}: {e}")
                        break
                except Exception as e:
                    self.logger.error(f"Failed to upload {file_path.name}: {e}")
                    break

    def collect(self):
        self.logger.info(f"Collecting zoning ordinance for {self.city()}")
        downloaded_files = self.scraper.scrape()
        self.logger.info(f"Downloaded {len(downloaded_files)} sections")

        # Wait for files to be fully flushed and Chrome to release file handles
        self.logger.info("Waiting for files to be fully released...")
        time.sleep(3)

        self.upload_to_gcs(downloaded_files)
        return downloaded_files