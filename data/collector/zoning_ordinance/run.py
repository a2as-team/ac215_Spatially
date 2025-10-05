"""CLI entry point for zoning ordinance data collection."""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.zoning_ordinance.boston import ZoningCodeCollector as BostonCollector
from collector.zoning_ordinance.chicago import ChicagoZoningCollector

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="Which city? (boston or chicago)",
            arg_type=str,
            required=True,
        ),
        "headless": SmartArgItem(
            flags=["--headless"],
            prompt="Run browser in headless mode (no GUI)",
            arg_type=bool,
            required=False,
            default=True,
        ),
        "download_dir": SmartArgItem(
            flags=["--download_dir"],
            prompt="Directory to save downloaded files (optional)",
            arg_type=str,
            required=False,
            default=None,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    city = args["city"].lower()

    if city == "boston":
        print("\n" + "=" * 60)
        print("Boston Zoning Code Data Collector")
        print("=" * 60)

        collector = BostonCollector(
            headless=args["headless"],
            download_dir=args["download_dir"]
        )

        try:
            results = collector.collect()
            print("\n" + "=" * 60)
            print("Collection Results")
            print("=" * 60)
            print(f"Total sections found: {results['total_sections']}")
            print(f"Successfully downloaded: {results['downloaded']}")
            print(f"Failed: {results['failed']}")

            if results['failed_sections']:
                print("\nFailed sections:")
                for section in results['failed_sections']:
                    print(f"  - {section}")

            print(f"\nFiles saved to: {results['download_directory']}")
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"\nError: {e}")
            sys.exit(1)

    elif city == "chicago":
        print("\n" + "=" * 60)
        print("Chicago Municipal Code Data Collector")
        print("=" * 60)

        collector = ChicagoZoningCollector(
            headless=args["headless"],
            download_dir=args["download_dir"]
        )

        try:
            results = collector.collect()

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
    else:
        print(f"Error: Unknown city '{city}'. Must be 'boston' or 'chicago'.")
        sys.exit(1)


"""
Example usage: (you must be in the /data directory)

python collector/zoning_ordinance/run.py --city boston --headless True

or

python collector/zoning_ordinance/run.py --city chicago --headless False
"""
