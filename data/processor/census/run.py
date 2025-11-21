"""
Census Processor CLI entry point.

This script processes census CSV files from GCS and ingests them into the database.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to enable imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from census import CensusProcessor


if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="City to process census data for",
            arg_type=str,
            required=True,
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (only process first 3 files)",
            arg_type=bool,
            required=False,
            default=False,
            action="store_true",
        ),
    }

    parser = SmartArgParser(schema)
    args = parser.parse()

    processor = CensusProcessor(city=args["city"])
    processor.process(test_mode=args["test"])
