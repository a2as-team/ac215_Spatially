import os
import random
import string
from datetime import datetime


class BaseJob:
    """
    Base class for job submission scripts.

    Provides common utilities for all jobs:
    - GCP environment configuration
    - Job naming helpers (UUID, timestamp)
    - Project-level constants

    Each job type (training, batch processing, etc.) can extend this class
    and implement their own submission logic as needed.
    """

    def __init__(self):
        """Initialize base job with common GCP configuration."""
        self.GCP_PROJECT = os.environ.get("GCP_PROJECT")
        self.GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
        self.GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
        self.GCS_BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}" if self.GCS_BUCKET_NAME else None
        self.project_name = "spatially"

        # Validate required environment variables
        if not self.GCP_PROJECT:
            raise ValueError("GCP_PROJECT environment variable not set")
        if not self.GCS_BUCKET_NAME:
            raise ValueError("GCS_BUCKET_NAME environment variable not set")

    def generate_uuid(self, length: int = 8) -> str:
        """Generate a random UUID for job naming."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def get_timestamp(self) -> str:
        """Get current timestamp in YYYYMMDD-HHMMSS format."""
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def print_job_header(self, title: str = "Job Configuration"):
        """Print a formatted header for job configuration."""
        print("=" * 80)
        print(title)
        print("=" * 80)
