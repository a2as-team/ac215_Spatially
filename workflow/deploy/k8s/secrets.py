"""
Kubernetes Secrets Management Module

This module handles creation and management of Kubernetes Secrets.
Works on any Kubernetes cluster (GKE, EKS, AKS, etc.) since it uses kubectl.
"""

import os
import subprocess


class SecretsManager:
    """Manages Kubernetes Secrets for the application."""

    def __init__(self):
        # Secret names
        self.db_secret_name = "spatially-db-secrets"
        self.gcp_secret_name = "spatially-gcp-secrets"
        self.gcp_sa_key_secret_name = "gcp-sa-key"
        self.cloudflare_secret_name = "cloudflare-api-token"

    def run_command(
        self,
        cmd: list[str],
        check: bool = True,
        capture_output: bool = False,
        ignore_error: bool = False,
        input: str | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a kubectl command and handle errors."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, check=check, capture_output=capture_output, text=True, input=input
            )
            return result
        except subprocess.CalledProcessError as e:
            if ignore_error:
                print(f"Command failed (ignored): {e}")
                return e
            raise

    def create_or_update_secret(self, name: str, literals: dict):
        """
        Create or update a Kubernetes Secret.

        Uses --dry-run=client + kubectl apply for idempotent updates.
        """
        cmd = ["kubectl", "create", "secret", "generic", name]
        for key, value in literals.items():
            cmd += ["--from-literal", f"{key}={value}"]
        cmd += ["--dry-run=client", "-o", "yaml"]

        yaml_output = subprocess.check_output(cmd, text=True)
        self.run_command(["kubectl", "apply", "-f", "-"], input=yaml_output)

    def delete_secret(self, name: str):
        """Delete a Kubernetes Secret (ignores if not exists)."""
        self.run_command(["kubectl", "delete", "secret", name], ignore_error=True)

    def remove_existing_secrets(self):
        """Remove all application secrets (for clean redeployment)."""
        print("\n--- Removing existing secrets ---")
        self.delete_secret(self.db_secret_name)
        self.delete_secret(self.gcp_secret_name)
        self.delete_secret(self.gcp_sa_key_secret_name)
        self.delete_secret(self.cloudflare_secret_name)

    def setup_db_secrets(self):
        """
        Setup database secrets from environment variables.

        Required env vars:
        - POSTGRE_HOST
        - POSTGRE_USER
        - POSTGRE_PASSWORD
        - APP_DB_NAME

        Optional:
        - POSTGRE_PORT (default: 5432)
        """
        print("\n--- Setting up database secrets ---")

        postgre_host = os.environ.get("POSTGRE_HOST")
        postgre_user = os.environ.get("POSTGRE_USER")
        postgre_password = os.environ.get("POSTGRE_PASSWORD")
        app_db_name = os.environ.get("APP_DB_NAME")
        postgre_port = os.environ.get("POSTGRE_PORT", "5432")

        if not all([postgre_host, postgre_user, postgre_password, app_db_name]):
            raise ValueError(
                "Missing required environment variables: "
                "POSTGRE_HOST, POSTGRE_USER, POSTGRE_PASSWORD, APP_DB_NAME"
            )

        self.create_or_update_secret(
            self.db_secret_name,
            {
                "POSTGRE_HOST": postgre_host,
                "POSTGRE_USER": postgre_user,
                "POSTGRE_PASSWORD": postgre_password,
                "APP_DB_NAME": app_db_name,
                "POSTGRE_PORT": postgre_port,
            },
        )
        print(f"✓ Secret '{self.db_secret_name}' configured")

    def setup_gcp_secrets(self):
        """
        Setup GCP secrets from environment variables.

        Required env vars:
        - GCP_PROJECT
        - GCP_REGION

        Optional env vars:
        - FRONTEND_HOST (for CORS, defaults to http://localhost:3000)
        - BACKEND_CORS_ORIGINS (comma-separated list of additional origins)
        """
        print("\n--- Setting up GCP secrets ---")

        gcp_project = os.environ.get("GCP_PROJECT")
        gcp_region = os.environ.get("GCP_REGION")

        if not all([gcp_project, gcp_region]):
            raise ValueError(
                "Missing required environment variables: GCP_PROJECT, GCP_REGION"
            )

        secrets_data = {
            "GCP_PROJECT": gcp_project,
            "GCP_REGION": gcp_region,
        }

        # Add CORS settings - derive frontend host from DOMAIN_FILTER and add to BACKEND_CORS_ORIGINS
        domain_filter = os.environ.get("DOMAIN_FILTER")
        cors_origins = os.environ.get("BACKEND_CORS_ORIGINS", "")

        # Derive frontend host from DOMAIN_FILTER (e.g., teamspatially.com -> https://zoning.teamspatially.com)
        if domain_filter:
            frontend_host = f"https://zoning.{domain_filter}"
            if cors_origins:
                cors_origins = f"{cors_origins},{frontend_host}"
            else:
                cors_origins = frontend_host

        if cors_origins:
            secrets_data["BACKEND_CORS_ORIGINS"] = cors_origins
            print(f"  CORS allowed origins: {cors_origins}")

        self.create_or_update_secret(self.gcp_secret_name, secrets_data)
        print(f"✓ Secret '{self.gcp_secret_name}' configured")

    def setup_gcp_sa_key_secret(self):
        """
        Setup GCP service account key secret from file.

        Required env var:
        - GOOGLE_APPLICATION_CREDENTIALS (path to service account key JSON file)
        """
        print("\n--- Setting up GCP service account key secret ---")

        sa_key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if not sa_key_path:
            raise ValueError(
                "Missing required environment variable: GOOGLE_APPLICATION_CREDENTIALS"
            )

        if not os.path.exists(sa_key_path):
            raise ValueError(f"Service account key file not found: {sa_key_path}")

        # Create secret from file
        cmd = [
            "kubectl", "create", "secret", "generic", self.gcp_sa_key_secret_name,
            f"--from-file=key.json={sa_key_path}",
            "--dry-run=client", "-o", "yaml"
        ]
        yaml_output = subprocess.check_output(cmd, text=True)
        self.run_command(["kubectl", "apply", "-f", "-"], input=yaml_output)

        print(f"✓ Secret '{self.gcp_sa_key_secret_name}' configured")

    def setup_cloudflare_secrets(self):
        """
        Setup Cloudflare secrets for ExternalDNS.

        Required env vars:
        - CLOUDFLARE_API_TOKEN
        """
        print("\n--- Setting up Cloudflare secrets ---")

        cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")

        if not cf_token:
            raise ValueError(
                "Missing required environment variable: CLOUDFLARE_API_TOKEN"
            )

        self.create_or_update_secret(
            self.cloudflare_secret_name,
            {
                "api-token": cf_token,
            },
        )
        print(f"✓ Secret '{self.cloudflare_secret_name}' configured")

    def setup_all(self):
        """Setup all application secrets."""
        self.remove_existing_secrets()
        self.setup_db_secrets()
        self.setup_gcp_secrets()
        self.setup_gcp_sa_key_secret()
        self.setup_cloudflare_secrets()

    def status(self):
        """Show status of all secrets."""
        print("\n--- Secrets Status ---")
        self.run_command(["kubectl", "get", "secrets"])


if __name__ == "__main__":
    import sys

    secrets = SecretsManager()

    if len(sys.argv) > 1:
        action = sys.argv[1]
        actions = {
            "setup": secrets.setup_all,
            "status": secrets.status,
            "db": secrets.setup_db_secrets,
            "gcp": secrets.setup_gcp_secrets,
            "remove": secrets.remove_existing_secrets,
        }
        if action in actions:
            actions[action]()
        else:
            print(f"Unknown action: {action}")
    else:
        print("Usage: python secrets.py [setup|status|db|gcp|remove]")
