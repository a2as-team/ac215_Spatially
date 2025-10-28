from .boston import BostonDevelopmentPlansCollector


class DevelopmentPlansCollector:
    def __init__(self):
        self.development_plans_collector_map = {
            "boston": BostonDevelopmentPlansCollector(),
        }

    def collect(self, city: str, test_mode: bool = False):
        return self.development_plans_collector_map[city].collect(test_mode=test_mode)
