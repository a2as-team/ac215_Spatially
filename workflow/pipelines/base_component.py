from abc import ABC, abstractmethod
import os
import random
import string
from kfp import dsl, compiler
import google.cloud.aiplatform as aip


class BaseComponent(ABC):
    """Base class for pipeline components"""

    def __init__(self):
        self.GCP_PROJECT = os.environ["GCP_PROJECT"]
        self.GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
        self.BUCKET_URI = f"gs://{self.GCS_BUCKET_NAME}"
        self.PIPELINE_ROOT = f"{self.BUCKET_URI}/pipeline_root/root"
        self.GCS_SERVICE_ACCOUNT = os.environ["GCS_SERVICE_ACCOUNT"]
        self.GCS_PACKAGE_URI = os.environ["GCS_PACKAGE_URI"]
        self.GCP_REGION = os.environ["GCP_REGION"]
        self.APP_DB_NAME = os.environ["APP_DB_NAME"]
        # Database connection parameters
        self.POSTGRE_USER = os.environ["POSTGRE_USER"]
        self.POSTGRE_PASSWORD = os.environ["POSTGRE_PASSWORD"]
        self.POSTGRE_HOST = os.environ["POSTGRE_HOST"]
        self.POSTGRE_PORT = os.environ.get("POSTGRE_PORT", "5432")
        self.project_name = "spatially"

    @abstractmethod
    def get_component(self):
        """Return the KFP component"""
        pass

    @abstractmethod
    def get_component_name(self):
        """Return a short name for this component (used in pipeline naming)"""
        pass

    def generate_uuid(self, length: int = 8) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def create_pipeline(self):
        """Create a simple pipeline that runs just this component"""
        component_name = self.get_component_name()
        component = self.get_component()

        # Include city in naming if component has city attribute
        city_suffix = f"-{self.city}" if hasattr(self, 'city') else ""
        pipeline_name = f"{component_name}-pipeline{city_suffix}"
        display_name = f"{component_name}{city_suffix}"

        @dsl.pipeline(name=pipeline_name)
        def single_component_pipeline():
            task = (
                component()
                .set_display_name(display_name)
                .set_cpu_limit("2000m")
                .set_memory_limit("8G")
            )

        return single_component_pipeline

    def run(self):
        """Compile and submit a pipeline containing just this component"""
        pipeline = self.create_pipeline()
        component_name = self.get_component_name()

        # Include city in naming if component has city attribute
        city_suffix = f"_{self.city}" if hasattr(self, 'city') else ""

        # Compile the pipeline
        pipeline_file = f"{component_name}_pipeline{city_suffix}.yaml"
        compiler.Compiler().compile(pipeline, package_path=pipeline_file)

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Create and submit the job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{component_name}{city_suffix}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=pipeline_file,
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")

        return job
