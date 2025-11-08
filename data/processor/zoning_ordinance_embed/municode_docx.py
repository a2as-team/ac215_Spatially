from .base import ZoningOrdinanceEmbedBaseProcessor
import os


class MunicodeDocxProcessor(ZoningOrdinanceEmbedBaseProcessor):
    def __init__(self):
        super().__init__()
        self.gcp_project = os.environ.get("GCP_PROJECT", "spatially")
        self.gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.embedding_model = "text-embedding-004"
        self.embedding_dimension = 768
        self.gcp_location = "us-central1"

        # Initialize LLM client
        self.llm_client = genai.Client(
            vertexai=True,
            project=self.gcp_project,