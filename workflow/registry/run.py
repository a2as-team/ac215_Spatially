
from publish_images import publish_local_docker_images
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    schema = {
        "to_where": SmartArgItem(
            flags=["--to-where"],
            prompt="The registry to publish the images to",
            arg_type=str,
            default="gcp",
            required=False,
            choices=["gcp", "dockerhub"],
        ),
        "cleanup_after_push": SmartArgItem(
            flags=["--cleanup-after-push"],
            prompt="Remove local images after successful push to save disk space",
            arg_type=bool,
            default=False,
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    publish_local_docker_images(
        to_where=args["to_where"],
        cleanup_after_push=args["cleanup_after_push"]
    )