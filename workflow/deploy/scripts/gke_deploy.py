from gke.cluster import GKECluster
from k8s.ingress import IngressSetup
from k8s.secrets import SecretsManager
import subprocess
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
K8S_DIR = SCRIPT_DIR.parent / "k8s"

# Import RegistryConfig and publish_images
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
from registry.config import RegistryConfig
from registry.publish_images import publish_local_docker_images


class GKEDeploy:
    def __init__(self):
        self.cluster = GKECluster()
        self.ingress = IngressSetup()
        self.secrets = SecretsManager()

    def run_command(
        self,
        cmd: list[str],
        check: bool = True,
        capture_output: bool = False,
        ignore_error: bool = False,
        input: bytes | str | None = None,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a shell command and handle errors."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, check=check, capture_output=capture_output, text=text, input=input
            )
            return result
        except subprocess.CalledProcessError as e:
            if ignore_error:
                print(f"Command failed (ignored): {e}")
                return e
            raise

    def build_and_push_backend_image(self):
        """Build and push the backend Docker image to Artifact Registry."""
        print("Building and pushing backend image...")
        success = publish_local_docker_images(images=["backend"])
        if not success:
            raise RuntimeError("Failed to build and push backend image")
        print("Backend image built and pushed successfully!")

    def deploy_deployment_and_service(self):
        # Get the correct image URI from RegistryConfig
        backend_image = RegistryConfig.backend_image(
            self.cluster.region, self.cluster.project
        )["image_uri"]

        # Apply PVC for persistent storage (chat history)
        print("\nApplying PersistentVolumeClaim for chat history...")
        self.run_command(["kubectl", "apply", "-f", str(K8S_DIR / "pvc.yaml")])

        # Read deployment.yaml and substitute the image
        deployment_yaml = (K8S_DIR / "deployment.yaml").read_text()
        deployment_yaml = deployment_yaml.replace("${BACKEND_IMAGE}", backend_image)

        # Apply deployment via stdin
        print(f"Deploying with image: {backend_image}")
        self.run_command(["kubectl", "apply", "-f", "-"], input=deployment_yaml)

        # Apply service
        self.run_command(["kubectl", "apply", "-f", str(K8S_DIR / "service.yaml")])

        # Apply HPA (Horizontal Pod Autoscaler)
        print("\nApplying Horizontal Pod Autoscaler...")
        self.run_command(["kubectl", "apply", "-f", str(K8S_DIR / "hpa.yaml")])

    def wait_for_deployment(self, deployment_name: str = "spatially-backend"):
        """Wait for deployment to complete and show status."""
        print(f"\nWaiting for deployment '{deployment_name}' to be ready...")

        # Wait for rollout to complete
        self.run_command(
            [
                "kubectl",
                "rollout",
                "status",
                f"deployment/{deployment_name}",
                "--timeout=300s",
            ]
        )

        # Show final pod status
        print("\n--- Pod Status ---")
        self.run_command(["kubectl", "get", "pods", "-l", f"app={deployment_name}"])

        # Show service info
        print("\n--- Service Status ---")
        self.run_command(["kubectl", "get", "service", deployment_name])

        # Show HPA status
        print("\n--- HPA (Autoscaler) Status ---")
        self.run_command(["kubectl", "get", "hpa", f"{deployment_name}-hpa"])

        print("\n" + "=" * 50)
        print("✓ Backend deployment ready!")
        print("  Service type: ClusterIP (internal)")
        print("  External access will be via Ingress controller")
        print("=" * 50 + "\n")

    def restart_deployment(self, deployment_name: str = "spatially-backend"):
        """Restart deployment to pick up new secrets/config."""
        print(f"\nRestarting deployment '{deployment_name}' to apply changes...")
        self.run_command(
            ["kubectl", "rollout", "restart", f"deployment/{deployment_name}"]
        )

    def deploy(self, skip_ingress: bool = False):
        """
        Full deployment pipeline:
        1. Create GKE cluster (gke/)
        2. Build and push backend image (registry/)
        3. Setup secrets (k8s/)
        4. Deploy app - deployment, service, HPA (k8s/)
        5. Setup HTTPS ingress (k8s/)
        """
        # GKE-specific: Create cluster
        self.cluster.create_and_check_cluster()

        # Registry: Build and push image
        self.build_and_push_backend_image()

        # K8s: Setup secrets
        self.secrets.setup_all()

        # K8s: Deploy app
        self.deploy_deployment_and_service()
        self.restart_deployment()  # Ensure pods pick up new secrets
        self.wait_for_deployment()

        # K8s: Setup HTTPS/Ingress
        if not skip_ingress:
            self.ingress.setup()
