from .zoneomics import ZoneomicsCollector


class ZoningCodesCollector:
    def __init__(self):
        self.collector_map = {
            "zoneomics": ZoneomicsCollector,
        }

    def collect(self, source: str, test_mode: bool = False):
        if source not in self.collector_map:
            raise ValueError(
                f"Unsupported source: {source}. Available: {list(self.collector_map.keys())}"
            )

        return self.collector_map[source]().collect(test_mode=test_mode)
