"""
Generic Cloud Run Service Deployment

Provides a reusable class for deploying and managing Cloud Run services.
"""
import subprocess
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CloudRunService:
    """
    Generic Cloud Run service deployer.

    This class provides a reusable interface for deploying any service to Cloud Run
    using gcloud commands. It handles service creation, updates, and deletion.
    """

    def __init__(self, service_config: Dict):
        """
        Initialize Cloud Run service deployer.

        Args:
            service_config: Dictionary with configuration:
                - name: Service name (e.g., "ner-service")
                - image_uri: Full image URI from Artifact Registry
                - region: GCP region (e.g., "us-central1")
                - project: GCP project ID
                - env_vars: Dict of environment variables (optional)
                - memory: Memory limit (e.g., "2Gi")
                - cpu: CPU limit (e.g., "2")
                - max_instances: Max autoscale instances (e.g., 10)
                - min_instances: Min instances (0 for scale-to-zero)
                - concurrency: Max concurrent requests per instance (e.g., 10)
                - timeout: Request timeout in seconds (e.g., 300)
                - port: Container port (default: 8080)
                - allow_unauthenticated: Public access (default: False)
        """
        self.name = service_config["name"]
        self.image_uri = service_config["image_uri"]
        self.region = service_config["region"]
        self.project = service_config["project"]
        self.env_vars = service_config.get("env_vars", {})
        self.memory = service_config.get("memory", "2Gi")
        self.cpu = service_config.get("cpu", "2")
        self.max_instances = service_config.get("max_instances", 10)
        self.min_instances = service_config.get("min_instances", 0)
        self.concurrency = service_config.get("concurrency", 10)
        self.timeout = service_config.get("timeout", 300)
        self.port = service_config.get("port", 8080)
        self.allow_unauthenticated = service_config.get("allow_unauthenticated", False)

        logger.info(f"CloudRunService initialized for: {self.name}")

    def service_exists(self) -> bool:
        """
        Check if the Cloud Run service already exists.

        Returns:
            True if service exists, False otherwise
        """
        try:
            cmd = [
                "gcloud", "run", "services", "describe", self.name,
                "--region", self.region,
                "--project", self.project,
                "--format", "json"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Error checking service existence: {e}")
            return False

    def deploy(self) -> str:
        """
        Deploy or update the Cloud Run service.

        This method is idempotent - it creates the service if it doesn't exist,
        or updates it if it does.

        Returns:
            Service URL

        Raises:
            RuntimeError: If deployment fails
        """
        logger.info(f"Deploying Cloud Run service: {self.name}")
        logger.info(f"  Image: {self.image_uri}")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Memory: {self.memory}, CPU: {self.cpu}")
        logger.info(f"  Min instances: {self.min_instances}, Max instances: {self.max_instances}")

        # Build gcloud command
        cmd = [
            "gcloud", "run", "deploy", self.name,
            "--image", self.image_uri,
            "--region", self.region,
            "--project", self.project,
            "--platform", "managed",
            "--memory", self.memory,
            "--cpu", self.cpu,
            "--max-instances", str(self.max_instances),
            "--min-instances", str(self.min_instances),
            "--concurrency", str(self.concurrency),
            "--timeout", str(self.timeout),
            "--port", str(self.port),
            "--quiet",
        ]

        # Add environment variables if provided
        if self.env_vars:
            env_str = ",".join([f"{k}={v}" for k, v in self.env_vars.items()])
            cmd.extend(["--set-env-vars", env_str])
            logger.info(f"  Environment variables: {len(self.env_vars)} variables set")

        # Add authentication setting
        if self.allow_unauthenticated:
            cmd.append("--allow-unauthenticated")
            logger.info("  Authentication: Public (unauthenticated access allowed)")
        else:
            cmd.append("--no-allow-unauthenticated")
            logger.info("  Authentication: Required (authenticated access only)")

        # Execute deployment
        try:
            logger.info("Executing gcloud run deploy...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Deployment command completed successfully")

            # Get service URL
            url = self.get_url()
            logger.info(f"Service URL: {url}")

            return url

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to deploy Cloud Run service: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def delete(self):
        """
        Delete the Cloud Run service.

        Raises:
            RuntimeError: If deletion fails
        """
        if not self.service_exists():
            logger.info(f"Service {self.name} does not exist, nothing to delete")
            return

        logger.info(f"Deleting Cloud Run service: {self.name}")

        cmd = [
            "gcloud", "run", "services", "delete", self.name,
            "--region", self.region,
            "--project", self.project,
            "--quiet"
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Service {self.name} deleted successfully")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to delete Cloud Run service: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def get_url(self) -> str:
        """
        Get the URL of the deployed Cloud Run service.

        Returns:
            Service URL

        Raises:
            RuntimeError: If URL cannot be retrieved
        """
        cmd = [
            "gcloud", "run", "services", "describe", self.name,
            "--region", self.region,
            "--project", self.project,
            "--format", "value(status.url)"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            url = result.stdout.strip()
            return url

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to get service URL: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def set_iam_policy(self, member: str, role: str):
        """
        Grant IAM permissions to a member.

        This is typically used to grant invoker role to service accounts
        for authenticated service-to-service communication.

        Args:
            member: IAM member (e.g., "serviceAccount:email@project.iam.gserviceaccount.com")
            role: IAM role (e.g., "roles/run.invoker")

        Raises:
            RuntimeError: If IAM policy update fails
        """
        logger.info(f"Granting {role} to {member} on {self.name}")

        cmd = [
            "gcloud", "run", "services", "add-iam-policy-binding", self.name,
            "--region", self.region,
            "--project", self.project,
            "--member", member,
            "--role", role
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"IAM policy updated successfully")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to update IAM policy: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
