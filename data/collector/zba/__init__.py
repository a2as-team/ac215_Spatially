from .boston import BostonZBACollector


class ZBACollector:
    def __init__(self):
        self.zba_collector_map = {
            "boston": BostonZBACollector(),
        }

    def collect(self, city: str):
        return self.zba_collector_map[city].collect()
