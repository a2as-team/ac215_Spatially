"""
Kubernetes Ingress Setup Module

This module handles the installation and configuration of:
1. NGINX Ingress Controller - Routes external traffic to services
2. cert-manager - Automatic TLS certificate management
3. ClusterIssuer - Let's Encrypt certificate issuer
4. Ingress resource - Routes zoning-api.teamspatially.com to backend

All installations use official Kubernetes manifests (no Helm required).
"""

import os
import subprocess
import time
from pathlib import Path


class IngressSetup:
    """Handles HTTPS/Ingress setup for Kubernetes."""

    # Official manifest URLs for cloud providers (GKE, EKS, AKS)
    NGINX_MANIFEST_URL = (
        "https://raw.githubusercontent.com/kubernetes/ingress-nginx/"
        "controller-v1.9.4/deploy/static/provider/cloud/deploy.yaml"
    )
    CERT_MANAGER_URL = (
        "https://github.com/cert-manager/cert-manager/releases/download/"
        "v1.13.2/cert-manager.yaml"
    )

    def __init__(self):
        # Directory where YAML files are located (k8s/)
        self.k8s_dir = Path(__file__).parent
        # Any email works - Let's Encrypt uses it for expiry notifications
        self.cert_email = os.environ.get("CERT_EMAIL")
        if not self.cert_email:
            raise ValueError("CERT_EMAIL environment variable is required")

        # Domain for ExternalDNS filtering and ingress host
        self.domain_filter = os.environ.get("DOMAIN_FILTER")
        if not self.domain_filter:
            raise ValueError("DOMAIN_FILTER environment variable is required")

        # Construct ingress host from domain filter
        self.ingress_host = f"zoning-api.{self.domain_filter}"

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

    def install_nginx_ingress(self):
        """
        Install NGINX Ingress Controller using official Kubernetes manifests.

        The ingress controller:
        - Creates a LoadBalancer service with an external IP
        - Routes HTTP/HTTPS traffic to your services based on Ingress rules
        - Handles TLS termination (HTTPS)
        """
        print("\n" + "=" * 60)
        print("  Installing NGINX Ingress Controller")
        print("=" * 60)

        print("\nApplying nginx-ingress manifest...")
        self.run_command(["kubectl", "apply", "-f", self.NGINX_MANIFEST_URL])

        print("\nWaiting for nginx-ingress controller to be ready...")
        self.run_command(
            [
                "kubectl",
                "wait",
                "--namespace",
                "ingress-nginx",
                "--for=condition=ready",
                "pod",
                "--selector=app.kubernetes.io/component=controller",
                "--timeout=300s",
            ],
            ignore_error=True,
        )

        print("\n✓ NGINX Ingress Controller installed!")

    def install_cert_manager(self):
        """
        Install cert-manager for automatic TLS certificate management.

        cert-manager:
        - Automatically requests certificates from Let's Encrypt
        - Renews certificates before they expire
        - Stores certificates as Kubernetes Secrets
        """
        print("\n" + "=" * 60)
        print("  Installing cert-manager")
        print("=" * 60)

        print("\nApplying cert-manager manifest...")
        self.run_command(["kubectl", "apply", "-f", self.CERT_MANAGER_URL])

        print("\nWaiting for cert-manager to be ready...")
        self.run_command(
            [
                "kubectl",
                "wait",
                "--namespace",
                "cert-manager",
                "--for=condition=available",
                "deployment/cert-manager",
                "--timeout=120s",
            ],
            ignore_error=True,
        )

        print("\n✓ cert-manager installed!")

    def install_external_dns(self):
        """
        Install ExternalDNS for automatic DNS record management.

        ExternalDNS:
        - Watches Ingress resources for hostnames
        - Automatically creates/updates DNS records in Cloudflare
        - Uses the Cloudflare API token from Kubernetes secret
        """
        print("\n" + "=" * 60)
        print("  Installing ExternalDNS (Cloudflare)")
        print("=" * 60)

        # Read and substitute domain filter
        external_dns_yaml = (self.k8s_dir / "external-dns.yaml").read_text()
        external_dns_yaml = external_dns_yaml.replace(
            "${DOMAIN_FILTER}", self.domain_filter
        )

        print(f"\nConfiguring ExternalDNS for domain: {self.domain_filter}")
        self.run_command(["kubectl", "apply", "-f", "-"], input=external_dns_yaml)

        print("\nWaiting for ExternalDNS to be ready...")
        self.run_command(
            [
                "kubectl",
                "wait",
                "--for=condition=available",
                "deployment/external-dns",
                "--timeout=120s",
            ],
            ignore_error=True,
        )

        print("\n✓ ExternalDNS installed!")

    def setup_cluster_issuer(self):
        """
        Setup Let's Encrypt ClusterIssuer for automatic TLS certificates.

        The ClusterIssuer:
        - Connects to Let's Encrypt ACME server
        - Uses HTTP-01 challenge to verify domain ownership
        - Works cluster-wide (any namespace can request certificates)
        """
        print("\n" + "=" * 60)
        print("  Setting up Let's Encrypt ClusterIssuer")
        print("=" * 60)

        issuer_yaml = (self.k8s_dir / "cluster-issuer.yaml").read_text()
        issuer_yaml = issuer_yaml.replace("${CERT_EMAIL}", self.cert_email)

        print(f"\nConfiguring with email: {self.cert_email}")
        self.run_command(["kubectl", "apply", "-f", "-"], input=issuer_yaml)

        print("\n✓ ClusterIssuer 'letsencrypt-prod' configured!")

    def deploy_ingress(self):
        """
        Deploy the Ingress resource.

        The Ingress:
        - Routes traffic from the configured host to backend
        - Requests TLS certificate from Let's Encrypt automatically
        - Redirects HTTP to HTTPS
        """
        print("\n" + "=" * 60)
        print("  Deploying Ingress")
        print("=" * 60)

        # Read and substitute ingress host
        ingress_yaml = (self.k8s_dir / "ingress.yaml").read_text()
        ingress_yaml = ingress_yaml.replace("${INGRESS_HOST}", self.ingress_host)

        print(f"\nConfiguring Ingress for host: {self.ingress_host}")
        self.run_command(["kubectl", "apply", "-f", "-"], input=ingress_yaml)
        print("\n✓ Ingress deployed!")

    def get_ingress_ip(self, max_attempts: int = 30) -> str | None:
        """Wait for and return the external IP of nginx-ingress LoadBalancer."""
        print("\nWaiting for Ingress external IP...")

        for i in range(max_attempts):
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "service",
                    "ingress-nginx-controller",
                    "-n",
                    "ingress-nginx",
                    "-o",
                    "jsonpath={.status.loadBalancer.ingress[0].ip}",
                ],
                capture_output=True,
                text=True,
            )
            ip = result.stdout.strip()
            if ip:
                return ip
            print(f"  Waiting for IP... ({i + 1}/{max_attempts})")
            time.sleep(10)

        return None

    def setup(self):
        """Complete ingress setup: nginx + cert-manager + external-dns + issuer + ingress."""
        print("\n" + "=" * 60)
        print("  HTTPS/INGRESS SETUP")
        print("=" * 60)

        self.install_nginx_ingress()
        self.install_cert_manager()
        self.install_external_dns()
        self.setup_cluster_issuer()
        self.deploy_ingress()

        external_ip = self.get_ingress_ip()
        self._print_summary(external_ip)

    def _print_summary(self, external_ip: str | None):
        """Print setup summary."""
        print("\n" + "=" * 60)
        print("  HTTPS SETUP COMPLETE!")
        print("=" * 60)

        if external_ip:
            print(
                f"""
  External IP: {external_ip}

  ExternalDNS will automatically create DNS records in Cloudflare.

  Your site will be available at:
    https://{self.ingress_host}

  DNS propagation may take 1-5 minutes.

  To check ExternalDNS logs:
    kubectl logs -l app=external-dns
"""
            )
        else:
            print(
                """
  External IP not yet assigned. Check later with:
    kubectl get service ingress-nginx-controller -n ingress-nginx
"""
            )

    def status(self):
        """Check the status of all ingress components."""
        print("\n--- Ingress Controller Pods ---")
        self.run_command(["kubectl", "get", "pods", "-n", "ingress-nginx"])

        print("\n--- Ingress Controller Service ---")
        self.run_command(["kubectl", "get", "service", "-n", "ingress-nginx"])

        print("\n--- cert-manager Pods ---")
        self.run_command(["kubectl", "get", "pods", "-n", "cert-manager"])

        print("\n--- ClusterIssuer ---")
        self.run_command(["kubectl", "get", "clusterissuer"], ignore_error=True)

        print("\n--- Ingress ---")
        self.run_command(["kubectl", "get", "ingress"])

        print("\n--- Certificate ---")
        self.run_command(["kubectl", "get", "certificate"], ignore_error=True)
