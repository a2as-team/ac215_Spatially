import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from registry.config import RegistryConfig


class GKECluster:
    def __init__(self):
        # Required
        self.project = os.environ.get("GCP_PROJECT")
        if not self.project:
            raise ValueError("GCP_PROJECT environment variable is required")

        # Cluster config
        self.region = os.environ.get("GCP_REGION", "us-central1")
        self.zone = os.environ.get("GKE_ZONE", "us-central1-a")  # For node pool
        self.app_name = os.environ.get("APP_NAME", "spatially")
        self.cluster_name = self.app_name + "-cluster"
        self.container_name = self.app_name + "-container"
        self.node_pool_name = self.app_name + "-node-pool"

        # Node pool config (matching Pulumi)
        self.machine_type = os.environ.get("GKE_MACHINE_TYPE", "n2d-standard-2")
        self.disk_size_gb = int(os.environ.get("GKE_DISK_SIZE", "50"))
        self.min_nodes = int(os.environ.get("GKE_MIN_NODES", "1"))
        self.max_nodes = int(os.environ.get("GKE_MAX_NODES", "3"))
        self.num_nodes = int(os.environ.get("GKE_NUM_NODES", "1"))

    @property
    def backend_image_repo(self):
        return RegistryConfig.backend_image(self.region, self.project)["image_uri"]

    def run_command(
        self,
        cmd: list[str],
        check: bool = True,
        capture_output: bool = False,
        ignore_error: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run a shell command and handle errors."""
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, check=check, capture_output=capture_output, text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            if ignore_error:
                print(f"Command failed (ignored): {e}")
                return e
            raise

    def cluster_exists(self) -> bool:
        cluster_check_cmd = [
            "gcloud",
            "container",
            "clusters",
            "list",
            "--project",
            self.project,
            "--zone",
            self.zone,
            "--filter",
            f"name={self.cluster_name}",
            "--format",
            "value(name)",
        ]
        result = self.run_command(cluster_check_cmd, capture_output=True)
        return self.cluster_name in result.stdout

    def create_cluster(self, preemptible: bool = True):
        if self.cluster_exists():
            print(f"Cluster '{self.cluster_name}' already exists.")
            # delete the cluster
            return

        print(f"Creating GKE cluster '{self.cluster_name}'...")
        print("This may take several minutes...")

        # Create cluster with autoscaling on default node pool
        create_cluster_cmd = [
            "gcloud",
            "container",
            "clusters",
            "create",
            self.cluster_name,
            "--zone",
            self.zone,
            "--machine-type",
            self.machine_type,
            "--disk-size",
            str(self.disk_size_gb),
            "--num-nodes",
            str(self.num_nodes),
            "--enable-autoscaling",
            "--min-nodes",
            str(self.min_nodes),
            "--max-nodes",
            str(self.max_nodes),
            "--scopes",
            "gke-default",
            "--enable-ip-alias",
        ]
        if preemptible:
            create_cluster_cmd.append("--preemptible")

        self.run_command(create_cluster_cmd)
        print(f"Cluster '{self.cluster_name}' created successfully!")

    def get_credentials(self):
        """Configure kubectl to use the GKE cluster."""
        print(f"Getting credentials for cluster '{self.cluster_name}'...")
        get_creds_cmd = [
            "gcloud",
            "container",
            "clusters",
            "get-credentials",
            self.cluster_name,
            "--zone",
            self.zone,
        ]
        self.run_command(get_creds_cmd)
        print("kubectl configured successfully!")

    def delete_cluster(self):
        if not self.cluster_exists():
            print(f"Cluster '{self.cluster_name}' does not exist.")
            return

        print(f"Deleting GKE cluster '{self.cluster_name}'...")
        delete_cluster_cmd = [
            "gcloud",
            "container",
            "clusters",
            "delete",
            self.cluster_name,
            "--zone",
            self.zone,
            "--quiet",
        ]
        self.run_command(delete_cluster_cmd)
        print(f"Cluster '{self.cluster_name}' deleted successfully!")

    def confirm_cluster(self):
        # we use kubectl cluster-info to confirm the cluster is created
        cluster_info_cmd = [
            "kubectl",
            "cluster-info",
        ]
        self.run_command(cluster_info_cmd)

    def get_pods(self):
        pods_cmd = [
            "kubectl",
            "get",
            "pods",
        ]
        self.run_command(pods_cmd)

    def get_services(self):
        services_cmd = [
            "kubectl",
            "get",
            "services",
        ]
        self.run_command(services_cmd)

    def get_deployments(self):
        deployments_cmd = [
            "kubectl",
            "get",
            "deployments",
        ]
        self.run_command(deployments_cmd)

    def get_ingresses(self):
        ingresses_cmd = [
            "kubectl",
            "get",
            "ingresses",
        ]
        self.run_command(ingresses_cmd)

    def create_and_check_cluster(self):
        self.create_cluster()
        self.get_credentials()
        self.confirm_cluster()
