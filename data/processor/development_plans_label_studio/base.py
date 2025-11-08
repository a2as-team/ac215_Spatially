from abc import ABC, abstractmethod
import logging
import os
import shutil
from template import BaseProcessor

class DevelopmentPlansLabelStudioBaseProcessor(BaseProcessor, ABC):
    def __init__(self):
        super().__init__()

        # Set up logger
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
        if not self.original_pdf_gcs_storage_path():
            raise ValueError("Original PDF GCS storage path is required")

    @classmethod
    @abstractmethod
    def city(cls) -> str:
        """Return the city name for this processor."""
        pass

    @classmethod
    def original_pdf_gcs_storage_path(cls) -> str:
        """
        Return the GCS storage parent directory for this processor.
        You should get this from the collector.
        """
        return None
