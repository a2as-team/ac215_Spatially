import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    from gke.cluster import GKECluster
    from scripts.gke_deploy import GKEDeploy
    from scripts.cloudrun_deploy import CloudRunDeploy

    schema = {
        "target": SmartArgItem(
            flags=["--target"],
            prompt="Deployment target",
            arg_type=str,
            required=True,
            choices=["gke", "cloudrun"],
        ),
        "action": SmartArgItem(
            flags=["--action"],
            prompt="Action to perform",
            arg_type=str,
            required=True,
            choices=["deploy", "deploy-app", "deploy-ingress", "deploy-only", "delete"],
        ),
        "service": SmartArgItem(
            flags=["--service"],
            prompt="Service name (for Cloud Run)",
            arg_type=str,
            required=False,
            choices=["ner-service"],
            default=None,
        ),
        "skip_ingress": SmartArgItem(
            flags=["--skip-ingress"],
            prompt="Skip ingress setup (for GKE)",
            arg_type=bool,
            required=False,
            default=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    if args["target"] == "gke":
        # GKE deployment
        if args["action"] == "deploy":
            # Full deployment: cluster + app + ingress
            deploy = GKEDeploy()
            deploy.deploy(skip_ingress=args.get("skip_ingress", False))
        elif args["action"] == "deploy-app":
            # App only: assumes cluster exists, skips cluster creation and ingress
            deploy = GKEDeploy()
            deploy.deploy_app_only()
        elif args["action"] == "deploy-ingress":
            # Ingress only: assumes cluster exists
            deploy = GKEDeploy()
            deploy.deploy_ingress_only()
        elif args["action"] == "delete":
            cluster = GKECluster()
            cluster.delete_cluster()
        else:
            raise ValueError(f"Invalid action for GKE: {args['action']}")

    elif args["target"] == "cloudrun":
        # Cloud Run deployment
        service_name = args.get("service")
        if not service_name:
            raise ValueError("--service is required for Cloud Run deployments")

        deploy = CloudRunDeploy(service_name)

        if args["action"] == "deploy":
            # Full deployment: build + push + deploy
            deploy.deploy()
        elif args["action"] == "deploy-only":
            # Skip image build, deploy existing image
            deploy.deploy_only()
        elif args["action"] == "delete":
            deploy.delete_service()
        else:
            raise ValueError(f"Invalid action for Cloud Run: {args['action']}")

    else:
        raise ValueError(f"Invalid target: {args['target']}")
