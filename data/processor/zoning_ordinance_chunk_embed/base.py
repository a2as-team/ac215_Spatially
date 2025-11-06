from abc import ABC, abstractmethod
import logging
import sys
from template import BaseProceesor


class ZoningOrdinanceEmbeddingsBaseProcessor(BaseProceesor, ABC):
    def __init__(self):
        super().__init__()

        # Set up logger
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

    @classmethod
    def input_gcs_storage_path(cls) -> str:
        """Return the GCS storage path for input ordinance files."""
        return f"zoning_ordinance/{cls.city()}"

    @classmethod
    def output_gcs_storage_path(cls) -> str:
        """Return the GCS storage path for output embeddings."""
        return f"zoning_ordinance_embeddings/{cls.city()}"
