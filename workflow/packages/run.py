from publish_packages import publish_trainer_packages
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    schema = {
        "packages": SmartArgItem(
            flags=["--packages"],
            prompt="Specific packages to publish (comma-separated). Leave empty for all.",
            arg_type=str,
            default="",
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Parse packages argument
    packages = None
    if args["packages"]:
        packages = [p.strip() for p in args["packages"].split(",")]

    # Publish packages
    success = publish_trainer_packages(packages=packages)

    # Exit with appropriate code
    sys.exit(0 if success else 1)
