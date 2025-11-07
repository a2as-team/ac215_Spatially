from utils.selenium import SeleniumUtil
from .base import ZoningMapsBaseCollector
from config.cities import City


class BostonZoningMapsCollector(ZoningMapsBaseCollector):
    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())


    def city(self) -> str:
        return City.BOSTON
    
    def zoning_static_resource_url(self) -> list[str]:
        """This has the list of zoning map static resources."""
        return "https://www.bostonplans.org/3d-data-maps/map-library/zoning-maps"
    
    def zoning_geospatial_resource_url(self) -> list[str]:
        return "https://data.boston.gov/dataset/boston-zoning-subdistricts"
    
    
    