from google.cloud import storage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class GCSAccessor:
    """Utility class for accessing Google Cloud Storage."""

    def __init__(self, bucket_name: str | None = None):
        self.client = storage.Client(project=settings.GCP_PROJECT)
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)

    def download_as_text(self, gcs_path: str) -> str:
        """
        Download a blob from GCS and return its content as text.

        Args:
            gcs_path: Path to the blob within the bucket (without gs:// prefix)

        Returns:
            The content of the blob as a string

        Raises:
            google.cloud.exceptions.NotFound: If the blob doesn't exist
        """
        blob = self.bucket.blob(gcs_path)
        content = blob.download_as_text()
        logger.info(f"Downloaded {gcs_path} from bucket {self.bucket_name}")
        return content

    def blob_exists(self, gcs_path: str) -> bool:
        """Check if a blob exists in the bucket."""
        blob = self.bucket.blob(gcs_path)
        return blob.exists()

    def list_blobs(self, prefix: str) -> list[str]:
        """List all blob names with a given prefix."""
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
