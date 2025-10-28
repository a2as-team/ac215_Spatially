from .boston import BostonDevelopmentPlansLabelStudioProcessor

class DevelopmentPlansLabelStudio:
    def __init__(self):
        self.processor_map = {
            "boston": BostonDevelopmentPlansLabelStudioProcessor(),
        }

    def process(self, city: str, test_mode: bool = False):
        return self.processor_map[city].process(test_mode=test_mode)