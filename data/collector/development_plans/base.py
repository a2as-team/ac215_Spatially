from abc import ABC, abstractmethod

from collector.base import BaseCollector


class BaseDevelopmentPlansCollector(BaseCollector, ABC):
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
    @abstractmethod
    def download_directory(cls) -> str:
        """Return the download directory path for this collector."""
        pass

    def __init__(self):
        # Access class-level properties
        if not self.city():
            raise ValueError("City is required")
        if not self.resource_url():
            raise ValueError("Resource URL is required")
