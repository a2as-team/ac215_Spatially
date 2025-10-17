"""Base Label Studio service for development plans NER annotation."""

from abc import abstractmethod
from pathlib import Path
from label_studio.base import BaseLabelStudioService


class BaseDevelopmentPlansLabelStudio(BaseLabelStudioService):
    """
    Base service class for Label Studio NER annotation of development plans.

    This service extends the base Label Studio service with development plans
    specific functionality like document type inference and metadata handling.
    """

    @classmethod
    @abstractmethod
    def city(cls) -> str:
        """Return city name."""
        pass

    @classmethod
    @abstractmethod
    def download_directory(cls) -> str:
        """Return download directory path."""
        pass

    @classmethod
    def get_document_types(cls) -> dict:
        """
        Return mapping of document type shortcuts to full names.

        Override this method in city-specific subclasses to provide
        city-specific document types.

        Returns:
            Dictionary mapping short codes to document type descriptions
        """
        return {
            "all": "All document types",
        }

    def pdf_directory(self) -> Path:
        """Return path to PDF directory."""
        return self.base_dir / self.download_directory() / "pdfs"

    def csv_file(self) -> Path:
        """Return path to collector CSV file."""
        return self.base_dir / self.download_directory() / "data.csv"

    def import_file(self, doc_type: str = "all") -> Path:
        """Return path to Label Studio import file."""
        return (
            self.label_studio_dir
            / "development_plans"
            / "imports"
            / self.city()
            / f"{self.city()}_{doc_type}_import.json"
        )

    def config_file(self) -> Path:
        """Return path to Label Studio config file."""
        return self.label_studio_dir / "development_plans" / "config.xml"

    def export_directory(self) -> Path:
        """Return path to exports directory."""
        return self.label_studio_dir / "development_plans" / "exports" / self.city()
