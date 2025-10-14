import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.paper import PaperCollector

if __name__ == "__main__":
    # Define schema for CLI arguments
    schema = {
        "query": SmartArgItem(
            flags=["--query"],
            prompt="Search keyword (type 'none' for latest papers)",
            arg_type=str,
            required=False,
        ),
        "pages": SmartArgItem(
            flags=["--pages"],
            prompt="Number of pages to scrape",
            arg_type=int,
            required=False,
        ),
        "journal": SmartArgItem(
            flags=["--journal"],
            prompt="MDPI journal slug (e.g., land, sensors, electronics)",
            arg_type=str,
            required=False,
        ),
        "provider": SmartArgItem(
            flags=["--provider"],
            prompt="Paper provider (default: mdpi)",
            arg_type=str,
            required=False,
        ),
    }

    parser = SmartArgParser(schema)
    args = parser.parse()

    # Fallback defaults if user skipped some arguments
    query = args.get("query")
    if query and query.lower() == "none":
        query = None
    pages = args.get("pages", 1)
    journal = args.get("journal", "land").lower()
    provider = args.get("provider", "mdpi").lower()

    # Run collector
    paper_collector = PaperCollector()
    paper_collector.collect(
        provider=provider,
        journal=journal,
        query=query,
        pages=pages,
    )