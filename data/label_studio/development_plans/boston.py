"""Boston-specific Label Studio service for development plans NER annotation."""

from .base import BaseDevelopmentPlansLabelStudio


class BostonDevelopmentPlansLabelStudio(BaseDevelopmentPlansLabelStudio):
    """Label Studio service for Boston development plans."""

    @classmethod
    def city(cls) -> str:
        """Return city name."""
        return "boston"

    @classmethod
    def download_directory(cls) -> str:
        """Return download directory path."""
        return "downloads/development_plans/boston"

    @classmethod
    def get_document_types(cls) -> dict:
        """Return Boston-specific document types."""
        return {
            "all": "All document types",
            "spra": "Small Project Review Application",
            "loi": "Letter of Intent",
            "bpda": "BPDA Board Approval",
            "pda": "Planned Development Area",
            "imp": "Institutional Master Plan",
        }
