from typing import List, Optional
from google.cloud import storage
from google.oauth2 import service_account
import os
from pathlib import Path


class GCPStorage:
    def __init__(
        self, gcp_project: str, bucket_name: str, credentials_path: Optional[str] = None
    ):
        """
        Initialize GCP Storage client.

        Args:
            gcp_project (str): GCP project ID.
            bucket_name (str): Name of the GCS bucket.
            credentials_path (Optional[str]): Path to service account JSON key file.
                If not provided, uses default credentials (environment variable or gcloud auth).
        """
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = storage.Client(project=gcp_project, credentials=credentials)
        else:
            self.client = storage.Client(project=gcp_project)
        self.bucket = self.client.bucket(bucket_name)

    def list_files(self, prefix: str = "") -> List[str]:
        """_summary_

        Args:
            prefix (str, optional): _description_. Defaults to "".
            if empty string, returns all files in the bucket

        Returns:
            List[str]: _description_
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]

    def upload_file(self, file_path: str, destination_path: str):
        blob = self.bucket.blob(destination_path)
        blob.upload_from_filename(file_path)

    def upload_dir(self, source_path: str, destination_path: str):
        """
        Uploads all files from a local directory to a GCS "directory" (prefix),
        preserving the subdirectory structure.

        Args:
            source_path (str): Local directory path to upload from.
            destination_path (str): Prefix (directory) in the GCS bucket.
        """
        source_path = Path(source_path)

        # Walk through all files in the source directory
        for local_file in source_path.rglob("*"):
            if local_file.is_file():
                # Get the relative path from source to maintain directory structure
                rel_path = local_file.relative_to(source_path)
                # Create the GCS blob path
                gcs_path = f"{destination_path}/{rel_path}".replace("\\", "/")
                blob = self.bucket.blob(gcs_path)
                blob.upload_from_filename(str(local_file))

    def download_file(self, source_path: str, destination_path: str):
        blob = self.bucket.blob(source_path)
        blob.download_to_filename(destination_path)

    def download_dir(self, source_path: str, destination_path: str):
        """
        Downloads all files from a GCS "directory" (prefix) to a local directory,
        preserving the subdirectory structure.

        Args:
            source_path (str): Prefix (directory) in the GCS bucket.
            destination_path (Path or str): Local path to save files. Should be a directory.
        """

        # Ensure destination_path is a Path
        destination_path = Path(destination_path)

        blobs = self.bucket.list_blobs(prefix=source_path)
        for blob in blobs:
            # Skip "directory placeholder" blobs (GCS may return a blob with a trailing /)
            if blob.name.endswith("/"):
                continue
            # Remove the source_path prefix to get the relative path
            rel_path = os.path.relpath(blob.name, source_path)
            local_file = destination_path / rel_path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_file))
