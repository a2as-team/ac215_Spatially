# data/collector/paper/run.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.paper import PaperCollector

if __name__ == "__main__":
    schema = {
        # Shared-ish args (MDPI original)
        "query": SmartArgItem(flags=["--query"], prompt="Search keyword (type 'none' for latest papers)", arg_type=str, required=False),
        "pages": SmartArgItem(flags=["--pages"], prompt="Number of pages to scrape", arg_type=int, required=False),
        "journal": SmartArgItem(flags=["--journal"], prompt="MDPI journal slug (e.g., land, sensors, electronics)", arg_type=str, required=False),
        "provider": SmartArgItem(flags=["--provider"], prompt="Paper provider (mdpi or tfo)", arg_type=str, required=True),

        # TFO-specific
        "journal_code": SmartArgItem(flags=["--journal_code"], prompt="TFO journal code (e.g., rupt20)", arg_type=str, required=False),
        "from_year": SmartArgItem(flags=["--from_year"], prompt="From year (e.g., 2013)", arg_type=int, required=False),
        "to_year": SmartArgItem(flags=["--to_year"], prompt="To year (e.g., 2025)", arg_type=int, required=False),
        "debugger": SmartArgItem(flags=["--debugger"], prompt="Attach Chrome like 127.0.0.1:9222 (optional)", arg_type=str, required=False),
        "out_dir": SmartArgItem(flags=["--out_dir"], prompt="Output directory", arg_type=str, required=False),
        "headless": SmartArgItem(flags=["--headless"], prompt="Headless? (true/false)", arg_type=str, required=False),
    }

    parser = SmartArgParser(schema)
    args = parser.parse()

    provider = (args.get("provider") or "mdpi").lower()

    # Normalize MDPI args
    query = args.get("query")
    if query and isinstance(query, str) and query.lower() == "none":
        query = None
    pages = int(args.get("pages", 1))
    journal = (args.get("journal") or "land").lower()

    # TFO args
    journal_code = args.get("journal_code") or "rupt20"
    from_year = int(args.get("from_year", 2013))
    to_year = int(args.get("to_year", 2025))
    debugger = args.get("debugger")  # e.g., "127.0.0.1:9222"

    # common
    out_dir = args.get("out_dir")
    headless = str(args.get("headless") or "true").lower() in {"1", "true", "yes"}

    pc = PaperCollector()

    if provider == "mdpi":
        pc.collect(
            provider="mdpi",
            journal=journal,
            query=query,
            pages=pages,
            out_dir=out_dir,
            headless=headless,
        )
    elif provider == "tfo":
        pc.collect(
            provider="tfo",
            journal_code=journal_code,
            from_year=from_year,
            to_year=to_year,
            out_dir=out_dir,
            headless=headless,
            debugger=debugger,
        )
    else:
        raise SystemExit(f"Unknown provider: {provider}")
