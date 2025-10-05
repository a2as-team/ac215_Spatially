"""CLI entry point for Chicago zoning code data collection."""

import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.chicago.base import ChicagoZoningCollector

if __name__ == "__main__":
    schema = {
        "headless": SmartArgItem(
            flags=["--headless"],
            prompt="Run browser in headless mode (no GUI)",
            arg_type=bool,
            required=False,
            default=True,
        ),
        "download_dir": SmartArgItem(
            flags=["--download_dir"],
            prompt="Directory to save downloaded files (default: collected_data_chicago)",
            arg_type=str,
            required=False,
            default=None,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Initialize collector
    collector = ChicagoZoningCollector(
        headless=args["headless"],
        download_dir=args["download_dir"]
    )

    # Run collection
    print("\n" + "=" * 60)
    print("Chicago Municipal Code Data Collector")
    print("=" * 60)
    print(f"URL: {collector.base_url}")
    print(f"Download directory: {collector.download_dir}")
    print(f"Headless mode: {collector.headless}")
    print("=" * 60 + "\n")

    try:
        results = collector.collect()

        # Validate results
        if collector.validate(results):
            print("\n" + "=" * 60)
            print("Collection Results")
            print("=" * 60)
            print("✓ Collection completed successfully!")
            print(f"Files downloaded: {len(results['files_downloaded'])}")
            for file_path in results["files_downloaded"]:
                print(f"  - {file_path}")
            print("=" * 60 + "\n")
        else:
            print("\n" + "=" * 60)
            print("Collection Failed")
            print("=" * 60)
            print("✗ Collection failed validation")
            if results.get("errors"):
                print("Errors:")
                for error in results["errors"]:
                    print(f"  - {error}")
            print("=" * 60 + "\n")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


"""
Example usage: (you must be in the /data directory)

python collector/chicago/run.py --headless True

or

python collector/chicago/run.py --headless False --download_dir /path/to/custom/dir
"""
