"""
Cloud Run Deployment Orchestrator

Orchestrates the full deployment process: build image, push to registry, deploy to Cloud Run.
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from registry.publish_images import publish_local_docker_images
from deploy.cloudrun.service import CloudRunService
from deploy.cloudrun.config import CloudRunConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CloudRunDeploy:
    """
    Cloud Run deployment orchestrator for a specific service.

    Handles the full deployment lifecycle:
    1. Build Docker image
    2. Push to Artifact Registry
    3. Deploy to Cloud Run
    """

    def __init__(self, service_name: str):
        """
        Initialize Cloud Run deployer for a specific service.

        Args:
            service_name: Name of the service to deploy (e.g., "ner-service")
        """
        self.service_name = service_name
        logger.info(f"CloudRunDeploy initialized for service: {service_name}")

    def build_and_push_image(self):
        """
        Build and push the service Docker image to Artifact Registry.

        Raises:
            RuntimeError: If build or push fails
        """
        logger.info(f"Building and pushing {self.service_name} image...")
        print(f"\n{'='*80}")
        print(f"Building Docker image for {self.service_name}")
        print(f"{'='*80}\n")

        success = publish_local_docker_images(images=[self.service_name])

        if not success:
            raise RuntimeError(f"Failed to build and push {self.service_name} image")

        logger.info(f"{self.service_name} image built and pushed successfully!")
        print(f"\n{'='*80}")
        print(f"✓ Image built and pushed successfully")
        print(f"{'='*80}\n")

    def deploy_service(self) -> str:
        """
        Deploy the Cloud Run service.

        Returns:
            Service URL

        Raises:
            ValueError: If service name is unknown
            RuntimeError: If deployment fails
        """
        # Get GCP configuration from environment
        gcp_project = os.environ.get("GCP_PROJECT")
        gcp_region = os.environ.get("GCP_REGION", "us-central1")

        if not gcp_project:
            raise RuntimeError("GCP_PROJECT environment variable must be set")

        logger.info(f"Deploying {self.service_name} to Cloud Run...")
        logger.info(f"  Project: {gcp_project}")
        logger.info(f"  Region: {gcp_region}")

        # Get service configuration
        service_configs = CloudRunConfig.get_service_configs(gcp_region, gcp_project)
        if self.service_name not in service_configs:
            available = ", ".join(service_configs.keys())
            raise ValueError(
                f"Unknown service: {self.service_name}. "
                f"Available services: {available}"
            )

        config = service_configs[self.service_name]

        # Deploy service
        print(f"\n{'='*80}")
        print(f"Deploying {self.service_name} to Cloud Run")
        print(f"{'='*80}\n")

        service = CloudRunService(config)
        url = service.deploy()

        # Print success message
        print(f"\n{'='*80}")
        print(f"✓ {self.service_name} deployed successfully!")
        print(f"{'='*80}")
        print(f"Service URL: {url}")
        print(f"Region: {gcp_region}")
        print(f"Authentication: Required")
        print(f"\nNext steps:")
        print(f"1. Grant backend compute SA invoke permission:")
        print(f"   gcloud run services add-iam-policy-binding {self.service_name} \\")
        print(f"     --region={gcp_region} \\")
        print(f"     --member=\"serviceAccount:968366835427-compute@developer.gserviceaccount.com\" \\")
        print(f"     --role=\"roles/run.invoker\"")
        print(f"\n2. Update backend environment:")
        print(f"   USE_CLOUDRUN_NER=true")
        print(f"   NER_SERVICE_URL={url}")
        print(f"{'='*80}\n")

        return url

    def deploy(self):
        """
        Full deployment: build image + push + deploy to Cloud Run.

        Returns:
            Service URL
        """
        self.build_and_push_image()
        return self.deploy_service()

    def deploy_only(self):
        """
        Deploy only (skip image build).

        Use this when the image has already been built and pushed.

        Returns:
            Service URL
        """
        logger.info("Skipping image build (deploy-only mode)")
        return self.deploy_service()

    def delete_service(self):
        """Delete the Cloud Run service."""
        # Get GCP configuration from environment
        gcp_project = os.environ.get("GCP_PROJECT")
        gcp_region = os.environ.get("GCP_REGION", "us-central1")

        if not gcp_project:
            raise RuntimeError("GCP_PROJECT environment variable must be set")

        # Get service configuration
        service_configs = CloudRunConfig.get_service_configs(gcp_region, gcp_project)
        if self.service_name not in service_configs:
            available = ", ".join(service_configs.keys())
            raise ValueError(
                f"Unknown service: {self.service_name}. "
                f"Available services: {available}"
            )

        config = service_configs[self.service_name]

        # Delete service
        print(f"\n{'='*80}")
        print(f"Deleting {self.service_name} from Cloud Run")
        print(f"{'='*80}\n")

        service = CloudRunService(config)
        service.delete()

        print(f"\n{'='*80}")
        print(f"✓ {self.service_name} deleted successfully!")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Deploy a service to Cloud Run")
    parser.add_argument(
        "--service",
        required=True,
        choices=["ner-service"],
        help="Service to deploy"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["deploy", "deploy-only", "delete"],
        help="Action to perform"
    )

    args = parser.parse_args()

    deployer = CloudRunDeploy(args.service)

    if args.action == "deploy":
        deployer.deploy()
    elif args.action == "deploy-only":
        deployer.deploy_only()
    elif args.action == "delete":
        deployer.delete_service()
