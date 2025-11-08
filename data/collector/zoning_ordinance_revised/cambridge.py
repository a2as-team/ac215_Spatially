from .base import ZoningOrdinanceBaseCollector
from shared_config.cities import City
from utils.scrapers.municode_scraper import MunicodeScraper

class CambridgeZoningOrdinanceCollector(ZoningOrdinanceBaseCollector):
    def __init__(self):
        super().__init__()
        self.scraper = MunicodeScraper(url=self.resource_url(), download_dir=self.download_directory())

    def city(self) -> str:
        return City.cambridge

    def resource_url(self) -> str:
        return "https://library.municode.com/ma/cambridge/codes/zoning_ordinance?nodeId=ZOORCAMA"
    
    def upload_to_gcs(self, downloaded_file: str):
        self.gcp_storage.upload_file(
            file_path=downloaded_file,
            destination_path=f"zoning_ordinance/{self.city()}/{downloaded_file.name}"
        )

    def collect(self):
        self.logger.info(f"Collecting zoning ordinance for {self.city()}")
        downloaded_file = self.scraper.scrape()
        self.upload_to_gcs(downloaded_file)