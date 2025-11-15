from .ner_json_processor import NerJsonProcessor
from utils.gcp_storage import GCPStorage
import os


class DevelopmentPlansProcessor:
    def __init__(self, city: str):
        self._init_gcp()
        self.city = city

    def gcp_storage_source_directory(self) -> str:
        """Return the GCS storage path for this processor."""
        return f"development_plans/{self.city}"

    def _init_gcp(self):
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.gcp_region = os.environ.get("GCP_REGION")
        self.gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if not self.gcp_project:
            raise ValueError("GCP_PROJECT environment variable not set")
        if not self.gcp_region:
            raise ValueError("GCP_REGION environment variable not set")
        if not self.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable not set")

        self.storage = GCPStorage(
            gcp_project=self.gcp_project, bucket_name=self.gcs_bucket_name
        )

    def choose_processor_based_on_metadata(self):
        """
        Choose the appropriate processor based on available files in GCS.
        Currently checks for .ner.json files and uses NerJsonProcessor.
        """
        # Check if there are any .ner.json files in the bucket
        prefix = f"{self.gcp_storage_source_directory()}/"
        files = self.storage.list_files(prefix=prefix, recursive=True)
        ner_json_files = [
            f for f in files if f.endswith(".ner.json") and not f.endswith("metadata.json")
        ]

        if ner_json_files:
            # Use NerJsonProcessor for .ner.json files
            return NerJsonProcessor(
                city=self.city,
                storage=self.storage,
                gcp_project=self.gcp_project,
                gcp_region=self.gcp_region,
                gcp_storage_source_directory=self.gcp_storage_source_directory(),
            )
        else:
            raise ValueError(
                f"No supported file format found for {self.city}. "
                f"Currently supported formats: .ner.json files (excluding metadata.json). "
                f"Please run the NER pipeline first."
            )

    def process(self, test_mode: bool = False):
        processor = self.choose_processor_based_on_metadata()
        return processor.process(test_mode=test_mode)
