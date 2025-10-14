from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def parse(self, *args, **kwargs):
        """
        Abstract method for parsing the data. Must be implemented by subclasses.
        """
        pass
