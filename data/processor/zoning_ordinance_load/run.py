#!/usr/bin/env python
"""Entry point for zoning ordinance Milvus loader."""

from utils.smart_arg_parser import SmartArgParser, SmartArgItem
from zoning_ordinance_load import ZoningOrdinanceMilvusLoader


def main():
    # Define argument schema
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to load (optional, loads all if not specified)",
            arg_type=str,
            required=False,
            default=None,
        ),
        "collection": SmartArgItem(
            flags=["--collection"],
            prompt="Milvus collection name",
            arg_type=str,
            required=False,
            default="zoning_ordinance",
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (load only 1 file)",
            arg_type=bool,
            default=False,
            action="store_true",
        ),
    }

    # Parse arguments
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Run loader
    loader = ZoningOrdinanceMilvusLoader()
    loader.process(
        city=args["city"],
        collection_name=args["collection"],
        test_mode=args["test"]
    )


if __name__ == "__main__":
    main()
