from .boston import BostonZoningMapsCollector
from .cambridge import CambridgeZoningMapsCollector
from shared_config.cities import City

class ZoningMapsCollector:
    # Map city to collector CLASS (not instance) - no instantiation yet!
    COLLECTOR_CLASSES = {
        City.boston: BostonZoningMapsCollector,
        City.cambridge: CambridgeZoningMapsCollector,
        # Add more cities here as they are implemented
        # City.chicago: ChicagoZoningMapsCollector,
    }

    def __init__(self):
        pass

    def collect(self, city: str):
        """
        Collect zoning maps for a specific city.
        Only instantiates (and deletes old data for) the city being collected.
        """
        if city not in self.COLLECTOR_CLASSES:
            available = ", ".join(sorted(self.COLLECTOR_CLASSES.keys()))
            raise ValueError(f"Unknown city '{city}'. Available: {available}")

        # Instantiate the collector only when needed
        # This triggers deletion only for THIS city
        collector = self.COLLECTOR_CLASSES[city]()
        return collector.collect()
