from .docx import DocxProcessor
from utils.gcp_storage import GCPStorage
import os


class ZoningOrdinanceEmbedProcessor:
    def __init__(self, city: str):
        self._init_gcp()
        self.city = city

    def gcp_storage_source_directory(self) -> str:
        """Return the GCS storage path for this processor."""
        return f"zoning_ordinance/{self.city}"

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
        Currently checks for .docx files and uses DocxProcessor.
        """
        # Check if there are any .docx files in the bucket
        files = self.storage.list_files(
            prefix=f"{self.gcp_storage_source_directory()}/"
        )
        docx_files = [f for f in files if f.endswith(".docx")]

        if docx_files:
            # Use DocxProcessor for DOCX files
            return DocxProcessor(
                city=self.city,
                storage=self.storage,
                gcp_project=self.gcp_project,
                gcp_region=self.gcp_region,
                gcp_storage_source_directory=self.gcp_storage_source_directory(),
            )
        else:
            raise ValueError(
                f"No supported file format found for {self.city}. "
                f"Currently supported formats: .docx files. "
                f"Please collect the zoning ordinance first."
            )

    def process(self, test_mode: bool = False):
        processor = self.choose_processor_based_on_metadata()
        return processor.process(test_mode=test_mode)
