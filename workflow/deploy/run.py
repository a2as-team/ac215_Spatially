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
            choices=["deploy", "delete"],
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    if args["action"] == "deploy":
        # GKEDeploy handles cluster creation internally
        deploy = GKEDeploy()
        deploy.deploy(skip_ingress=False)
    elif args["action"] == "delete":
        cluster = GKECluster()
        cluster.delete_cluster()
    else:
        raise ValueError(f"Invalid action: {args['action']}")
