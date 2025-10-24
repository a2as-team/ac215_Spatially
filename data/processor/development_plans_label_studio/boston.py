"""Boston-specific Label Studio service for development plans NER annotation."""

from .base import DevelopmentPlansLabelStudioBaseProcessor
from collector.development_plans.boston import BostonDevelopmentPlansCollector

class BostonDevelopmentPlansLabelStudioProcessor(DevelopmentPlansLabelStudioBaseProcessor):
    """Processor for Boston development plans Label Studio."""

    @classmethod
    def city(cls) -> str:
        """Return city name."""
        return BostonDevelopmentPlansCollector.city()

    @classmethod
    def get_document_types(cls) -> dict:
        """
        For ease of managing label studio, we will use document types 
        """
        return {
            "spra": "Small Project Review Application",
            "loi": "Letter of Intent",
            "bpda": "BPDA Board",
            "pda": "Planned Development Area",
            "imp": "Institutional Master Plan",
        }

    def upload_ner_labeling_ready_json(self):
        """Upload the NER labeling ready JSON file to GCS."""
        pass
    
    def process(self):
        """Process the data."""
        pass