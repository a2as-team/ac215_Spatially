#!/usr/bin/env python3
"""
Job class for submitting NER training jobs to Vertex AI.

This is a library module that defines the DevelopmentPlansNERJob class.
To submit a training job, use: workflow/jobs/run_development_plans_ner.py
"""
import sys
import time
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.base_job import BaseJob
from packages.config import PackageConfig


class DevelopmentPlansNERJob(BaseJob):
    """Submit NER training jobs to Vertex AI."""
    JOB_NAME = "ner-training"

    def __init__(
        self,
        batch_size: int = 4,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        model_name: str = "nlpaueb/legal-bert-base-uncased",
        machine_type: str = "n1-standard-4",
        accelerator_type: str = "NVIDIA_TESLA_T4",
        accelerator_count: int = 1,
    ):
        super().__init__()
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.model_name = model_name
        self.machine_type = machine_type
        self.accelerator_type = accelerator_type
        self.accelerator_count = accelerator_count

    def create_job(self):
        """Create the Vertex AI Python package training job."""
        import google.cloud.aiplatform as aip
        import os

        # Get package configuration
        package_config = PackageConfig.ner_trainer_package()
        package_gcs_uri = f"gs://{package_config['bucket']}/{package_config['gcs_path']}"
        container_uri = package_config['container_uri']

        # Use finetune-specific staging bucket and region (must be in same region)
        finetune_bucket = os.environ.get("FINETUNE_GCS_BUCKET")
        finetune_region = os.environ.get("FINETUNE_GCP_REGION")

        if not finetune_bucket or not finetune_region:
            raise ValueError(
                "FINETUNE_GCS_BUCKET and FINETUNE_GCP_REGION must be set. "
                "Make sure ac215-spatially-finetune.env is loaded."
            )

        staging_bucket_uri = f"gs://{finetune_bucket}"

        # Generate job name
        job_id = self.generate_uuid()
        timestamp = self.get_timestamp()
        model_short = self.model_name.split("/")[-1]
        display_name = f"ner-{model_short}-e{self.epochs}-{timestamp}-{job_id}"

        # Print configuration
        self.print_job_header("Vertex AI Python Package Training Job Configuration")
        print(f"Job name: {display_name}")
        print(f"Package URI: {package_gcs_uri}")
        print(f"Container URI: {container_uri}")
        print(f"Python module: run")
        print(f"Project: {self.GCP_PROJECT}")
        print(f"Region: {finetune_region}")
        print(f"Staging bucket: {staging_bucket_uri}")
        print(f"Machine type: {self.machine_type}")
        print(f"Accelerator: {self.accelerator_type} x {self.accelerator_count}")
        print(f"Model: {self.model_name}")
        print(f"Batch size: {self.batch_size}")
        print(f"Epochs: {self.epochs}")
        print(f"Learning rate: {self.learning_rate}")
        print(f"Data source: {self.GCS_BUCKET_URI}/development_plans/ner_training_data/ (us region)")
        print(f"Output location: {staging_bucket_uri}/ner_model_output/ (us-central1 region)")
        print("=" * 80)

        # Initialize Vertex AI with finetune staging bucket and region
        aip.init(
            project=self.GCP_PROJECT,
            location=finetune_region,
            staging_bucket=staging_bucket_uri
        )

        # Create custom Python package training job
        self.job = aip.CustomPythonPackageTrainingJob(
            display_name=display_name,
            python_package_gcs_uri=package_gcs_uri,
            python_module_name="run",
            container_uri=container_uri,
            project=self.GCP_PROJECT,
            labels={
                "type": "ner-training",
            }
            
        )

    def run_job(self, sync: bool = False):
        """Run the Vertex AI training job."""
        import os

        # Create the job if it hasn't been created yet
        if self.job is None:
            self.create_job()

        self.sync = sync

        # Training arguments
        args = [
            f"--batch-size={self.batch_size}",
            f"--epochs={self.epochs}",
            f"--learning-rate={self.learning_rate}",
            f"--model-name={self.model_name}",
        ]

        # Environment variables
        environment_variables = self.BASIC_ENVIRONMENT_VARIABLES | {
            "GCP_PROJECT": self.GCP_PROJECT,
            "GCS_BUCKET_NAME": self.GCS_BUCKET_NAME
        }

        # Add WANDB_API_KEY from environment
        if os.environ.get("WANDB_API_KEY"):
            environment_variables["WANDB_API_KEY"] = os.environ.get("WANDB_API_KEY")
            print("✓ Using WANDB_API_KEY from environment")
        else:
            print("⚠️  Warning: WANDB_API_KEY not set. Training will fail.")

        print(f"\n🚀 Launching Python package training job on Vertex AI...")
        print(f"Sync mode: {sync} (wait for completion: {sync})")

        # Get staging bucket for output (must match region)
        staging_bucket_uri = f"gs://{os.environ.get('FINETUNE_GCS_BUCKET')}"

        # Submit the training job
        custom_job = self.job.run(
            args=args,
            replica_count=1,
            machine_type=self.machine_type,
            accelerator_type=self.accelerator_type,
            accelerator_count=self.accelerator_count,
            base_output_dir=f"{staging_bucket_uri}/ner_model_output",
            environment_variables=environment_variables,
            sync=True,  # async mode
        )
        

        # let the user check the jobs in the console
        # exit after about 30 seconds just to let the user see the job in the console
        time.sleep(30)
        sys.exit(0)

                