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
    def original_pdf_gcs_storage_path(cls) -> str:
        """
        Return the original PDF GCS storage path.
        Remember that we have stored the development plan pdf per project in the GCS.
        """
        return BostonDevelopmentPlansCollector.gcp_storage_parent_directory()
    
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
    
    def prepare_annotation_data(self, doc_type: str):
        """Prepare the annotation data for the given document type."""
        
        pass

    def upload_ner_labeling_ready_json(self):
        """Upload the NER labeling ready JSON file to GCS."""
        pass
    
    def process(self, doc_type_filter: str = None):
        """Process the data."""
        if doc_type_filter:
            self.doc_type_filter = doc_type_filter
        else:
            self.doc_type_filter = "all"
        doc_types = self.get_document_types() if self.doc_type_filter == "all" else [self.doc_type_filter]
        for doc_type in doc_types:
            self.upload_ner_labeling_ready_json(doc_type)
        pass