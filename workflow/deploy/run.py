import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    from gke.cluster import GKECluster
    from scripts.gke_deploy import GKEDeploy

    schema = {
        "action": SmartArgItem(
            flags=["--action"],
            prompt="Action to perform",
            arg_type=str,
            required=True,
            choices=["deploy", "deploy-app", "deploy-ingress", "delete"],
        ),
        "skip_ingress": SmartArgItem(
            flags=["--skip-ingress"],
            prompt="Skip ingress setup",
            arg_type=bool,
            required=False,
            default=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

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
        raise ValueError(f"Invalid action: {args['action']}")
