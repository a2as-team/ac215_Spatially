"""Base Label Studio service for development plans NER annotation."""

from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    @abstractmethod
    def process(self, test_mode: bool = False):
        """Abstract method for processing the data. Must be implemented by subclasses."""
        pass

__all__ = ["BaseProcessor"]
