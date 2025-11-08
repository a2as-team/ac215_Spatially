from abc import ABC, abstractmethod
import logging
import sys
from template import BaseProcessor

class ZoningOrdinanceEmbedBaseProcessor(BaseProcessor, ABC):
    def __init__(self):
        super().__init__()
        import sys
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            # Use stdout instead of stderr for Vertex AI logging
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Validate required class properties
        if not self.city():
            raise ValueError("City is required")
    
    @classmethod
    @abstractmethod
    def city(cls) -> str:
        """Return the city name for this processor."""
        pass
        
    def process(self, test_mode: bool = False):
        pass