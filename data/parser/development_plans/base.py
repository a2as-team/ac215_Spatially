from abc import ABC, abstractmethod
from parser.base import BaseParser


class BaseDevelopmentPlansParser(BaseParser, ABC):
    @classmethod
    @abstractmethod
    def city(cls) -> str:
        """Return the city name for this parser."""
        pass

    resource_download_directory = ""

    # We should later create code to parse not only the text but also the street image and plan diagram

    def __init__(self, resource_download_directory: str = None):
        # only check if the static methods are defined
        self.resource_download_directory = resource_download_directory
        if not self.city():
            raise ValueError("City is required")
        if not self.resource_download_directory:
            raise ValueError("Download directory is required")
