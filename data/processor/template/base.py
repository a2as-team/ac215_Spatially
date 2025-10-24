"""Base Label Studio service for development plans NER annotation."""

from abc import ABC, abstractmethod


class BaseProceesor(ABC):
    @abstractmethod
    def process(self):
        """Abstract method for processing the data. Must be implemented by subclasses."""
        pass