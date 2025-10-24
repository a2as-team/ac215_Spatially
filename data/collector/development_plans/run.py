import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from development_plans import DevelopmentPlansCollector

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to collect",
            arg_type=str,
            required=True,
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (only process first few pages)",
            arg_type=bool,
            required=False,
            default=False,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = DevelopmentPlansCollector()
    collector.collect(args["city"], test_mode=args["test"])
