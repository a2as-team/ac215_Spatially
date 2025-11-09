from utils.smart_arg_parser import SmartArgParser, SmartArgItem
from zoning_ordinance import ZoningOrdinanceProcessor


def main():
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to process",
            arg_type=str,
            required=True,
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (process only 1 file)",
            arg_type=bool,
            default=True,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    processor = ZoningOrdinanceProcessor(city=args["city"])
    processor.process(test_mode=args["test"])


if __name__ == "__main__":
    main()
