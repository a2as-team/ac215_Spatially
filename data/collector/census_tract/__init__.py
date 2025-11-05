from .boston import BostonCensusTractCollector

class CensusTractCollector:
    caller_map = {}

    def __init__(self):
        self.caller_map = {
            "boston": BostonCensusTractCollector(),
        }

    def collect(self, city: str):
        return self.caller_map[city].collect()