from utils.smart_arg_parser import SmartArgParser, SmartArgItem
from development_plans import DevelopmentPlansProcessor


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
            prompt="Run in test mode (process only first few files)",
            arg_type=bool,
            default=False,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    processor = DevelopmentPlansProcessor(city=args["city"])
    processor.process(test_mode=args["test"])


if __name__ == "__main__":
    main()
