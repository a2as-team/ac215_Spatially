import os
import random
import string
import google.cloud.aiplatform as aip
from abc import ABC, abstractmethod


class BaseJob(ABC):
    """Base class for job submission scripts."""
    JOB_NAME = "spatially-job" # customize this

    def __init__(self):
        self.GCP_PROJECT = os.environ["GCP_PROJECT"]
        self.GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
        self.GCS_BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}"
        self.GCS_SERVICE_ACCOUNT = os.environ["GCS_SERVICE_ACCOUNT"]
        self.GCS_PACKAGE_URI = os.environ["GCS_PACKAGE_URI"]
        self.GCP_REGION = os.environ["GCP_REGION"]
        self.project_name = "spatially"
        self.job_id = self.generate_uuid()
        self.DISPLAY_NAME = f"{self.JOB_NAME}-{self.job_id}"
        self.job = None

    def generate_uuid(self, length: int = 8) -> str:
        """Generate a random UUID for job naming."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @abstractmethod
    def create_job(self):
        pass

    @abstractmethod
    def run_job(self):
        pass