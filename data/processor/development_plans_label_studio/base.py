from abc import ABC, abstractmethod
import os
import shutil
from template.label_studio_base import LabelStudioBaseProcessor


class DevelopmentPlansLabelStudioBaseProcessor(LabelStudioBaseProcessor, ABC):
    @classmethod
    @abstractmethod
    def city(cls) -> str:
        """Return the city name for this collector."""
        pass

    @classmethod
    @abstractmethod
    def resource_url(cls) -> str:
        """Return the resource URL for this collector."""
        pass

    @classmethod
    def download_directory(cls) -> str:
        """Return the download directory path for this collector."""
        return f"tmp/development_plans/{cls.city()}"

    def __init__(self):
        # Access class-level properties
        if not self.city():
            raise ValueError("City is required")
        if not self.resource_url():
            raise ValueError("Resource URL is required")
        
    @abstractmethod
    def upload_to_gcs(self):
        """Upload the data to GCS."""
        pass

    # def __del__(self):
    #     # when the object is deleted, we should delete the download directory
    #     # since we uploaded the files to GCS, we don't need to delete the local files
    #     if os.path.exists(self.download_directory()):
    #         shutil.rmtree(self.download_directory())