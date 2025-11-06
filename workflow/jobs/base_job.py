import os
import random
import string
import google.cloud.aiplatform as aip
from abc import ABC, abstractmethod
from datetime import datetime


class BaseJob(ABC):
    """Base class for job submission scripts."""
    JOB_NAME = "spatially-job"  # Override this in subclasses
    BASIC_ENVIRONMENT_VARIABLES = {
        "PJRT_DEVICE": "CUDA",          # 👈 tell PyTorch XLA to use CUDA
        "XLA_USE_BF16": "0",
        "USE_TORCH_XLA": "false",
    }

    def __init__(self):
        """Initialize job with GCP environment variables."""
        self.GCP_PROJECT = os.environ["GCP_PROJECT"]
        self.GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
        self.GCS_BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}"
        self.GCP_REGION = os.environ["GCP_REGION"]
        self.job = None

    def generate_uuid(self, length: int = 8) -> str:
        """Generate a random UUID for job naming."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def get_timestamp(self) -> str:
        """Get formatted timestamp for job naming."""
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def print_job_header(self, title: str):
        """Print a formatted header for job configuration."""
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)

    @abstractmethod
    def create_job(self):
        """Create the Vertex AI training job. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def run_job(self):
        """Run the Vertex AI training job. Must be implemented by subclasses."""
        pass