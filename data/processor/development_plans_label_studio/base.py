from abc import ABC, abstractmethod
import os
import shutil
from template.label_studio_base import LabelStudioBaseProcessor


class DevelopmentPlansLabelStudioBaseProcessor(LabelStudioBaseProcessor, ABC):
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

    def __init__(self):
        # Access class-level properties
        if not self.city():
            raise ValueError("City is required")
        if not self.original_pdf_gcs_storage_path():
            raise ValueError("Original PDF GCS storage path is required")
        
    @abstractmethod
    def upload_to_gcs(self):
        """Upload the data to GCS."""
        pass
