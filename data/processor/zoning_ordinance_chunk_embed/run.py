#!/usr/bin/env python
"""Entry point for zoning ordinance embeddings processor."""

from utils.smart_arg_parser import SmartArgParser, SmartArgItem
from zoning_ordinance_chunk_embed import ZoningOrdinanceEmbeddingsProcessor


def main():
    # Define argument schema
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to process (boston or chicago)",
            arg_type=str,
            required=True,
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (process only 1 file)",
            arg_type=bool,
            default=False,
            action="store_true",
        ),
    }

    # Parse arguments
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Run processor
    processor = ZoningOrdinanceEmbeddingsProcessor()
    processor.process(city=args["city"], test_mode=args["test"])


if __name__ == "__main__":
    main()
