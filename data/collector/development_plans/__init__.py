from .boston import BostonDevelopmentPlansCollector


class DevelopmentPlansCollector:
    def __init__(self):
        self.development_plans_collector_map = {
            "boston": BostonDevelopmentPlansCollector(),
        }

    def collect(self, city: str):
        return self.development_plans_collector_map[city].collect()
