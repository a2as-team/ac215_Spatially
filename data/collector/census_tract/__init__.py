from .boston import BostonCensusTractCollector
from .cambridge import CambridgeCensusTractCollector


class CensusTractCollector:
    caller_map = {}

    def __init__(self):
        self.caller_map = {
            "boston": BostonCensusTractCollector(),
            "cambridge": CambridgeCensusTractCollector(),
        }

    def collect(self, city: str):
        return self.caller_map[city].collect()
