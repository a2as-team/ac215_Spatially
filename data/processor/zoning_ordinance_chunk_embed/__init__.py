from .boston import BostonZoningOrdinanceEmbeddingsProcessor
from .chicago import ChicagoZoningOrdinanceEmbeddingsProcessor


class ZoningOrdinanceEmbeddingsProcessor:
    def __init__(self):
        self.processor_map = {
            "boston": BostonZoningOrdinanceEmbeddingsProcessor(),
            "chicago": ChicagoZoningOrdinanceEmbeddingsProcessor(),
        }

    def process(self, city: str, test_mode: bool = False):
        if city not in self.processor_map:
            raise ValueError(f"Unsupported city: {city}. Available: {list(self.processor_map.keys())}")

        return self.processor_map[city].process(test_mode=test_mode)


__all__ = ["ZoningOrdinanceEmbeddingsProcessor"]
