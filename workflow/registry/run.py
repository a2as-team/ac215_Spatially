import sys
from pathlib import Path
from publish_images import publish_local_docker_images

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser

# Available images to publish
AVAILABLE_IMAGES = [
    "data-collector",
    "data-collector-playwright",
    "data-processor",
    "backend",
]

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
        "images": SmartArgItem(
            flags=["--images", "-i"],
            prompt=f"Images to publish (comma-separated). Available: {', '.join(AVAILABLE_IMAGES)}, all",
            arg_type=str,
            default="all",
            required=True,
        ),
        "cleanup_after_push": SmartArgItem(
            flags=["--cleanup-after-push"],
            prompt="Remove local images after successful push to save disk space",
            arg_type=bool,
            default=True,
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Parse images argument (comma-separated string to list)
    images = None
    if args.get("images"):
        if args["images"].lower() == "all":
            images = None  # None means all images
        else:
            images = [img.strip() for img in args["images"].split(",")]

    publish_local_docker_images(
        to_where=args["to_where"],
        images=images,
        cleanup_after_push=args["cleanup_after_push"],
    )
