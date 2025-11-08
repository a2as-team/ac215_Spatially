from .cambridge import CambridgeZoningOrdinanceCollector
from .boston import BostonZoningOrdinanceCollector
from shared_config.cities import City


class ZoningOrdinanceCollector:
    def __init__(self):
        self.collector_map = {
            City.cambridge: CambridgeZoningOrdinanceCollector,
            City.boston: BostonZoningOrdinanceCollector,
        }
    
    def collect(self, city: str):
        if city not in self.collector_map:
            raise ValueError(f"Unsupported city: {city}. Available: {list(self.collector_map.keys())}")

        print(f"Collecting zoning ordinance for {city}")
        return self.collector_map[city]().collect()