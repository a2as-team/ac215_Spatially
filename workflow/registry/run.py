
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
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    publish_local_docker_images(to_where=args["to_where"])