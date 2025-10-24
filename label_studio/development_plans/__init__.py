from .boston import BostonDevelopmentPlansLabelStudio


class DevelopmentPlansLabelStudio:
    def __init__(self, city: str):
        self.city = city
        self.label_studio_map = {
            "boston": BostonDevelopmentPlansLabelStudio(),
        }
        self.service = self.label_studio_map[city]

    def prepare(self, doc_type_filter: str = None):
        """Prepare annotation data for the specified city and doc type."""
        return self.service.prepare_annotation_data(
            doc_type_filter=doc_type_filter
        )

    def import_file(self, doc_type: str = "all"):
        """Return path to import file."""
        return self.service.import_file(doc_type=doc_type)

    def get_document_types(self) -> dict:
        """Get document types for the current city."""
        return self.service.get_document_types()
