import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.zoningcode import ZoningCodeCollector

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
            prompt="Directory to save downloaded files (default: collected_data)",
            arg_type=str,
            required=False,
            default=None,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Initialize collector
    collector = ZoningCodeCollector(
        headless=args["headless"],
        download_dir=args["download_dir"]
    )

    # Run collection
    print("\n" + "=" * 60)
    print("Boston Zoning Code Data Collector")
    print("=" * 60)
    print(f"URL: {collector.URL}")
    print(f"Download directory: {collector.download_dir}")
    print(f"Headless mode: {collector.headless}")
    print("=" * 60 + "\n")

    try:
        results = collector.collect()

        # Print results
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


"""
Example usage: (you must be in the /data directory)

python collector/zoningcode/run.py --headless True

or

python collector/zoningcode/run.py --headless False --download_dir /path/to/custom/dir
"""
