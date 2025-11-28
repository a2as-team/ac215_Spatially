from zoning_codes import ZoningCodesCollector
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


if __name__ == "__main__":
    schema = {
        "source": SmartArgItem(
            flags=["--source"],
            prompt="The source to collect zoning codes for (choices: "
            + ", ".join(ZoningCodesCollector().collector_map.keys())
            + ")",
            arg_type=str,
            choices=[
                source.lower() for source in ZoningCodesCollector().collector_map.keys()
            ],
            required=True,
        ),
        "test_mode": SmartArgItem(
            flags=["--test-mode"],
            prompt="Run in test mode (only process first state)",
            action="store_true",
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = ZoningCodesCollector()
    collector.collect(args["source"], test_mode=args.get("test_mode", False))

# example usage:
# python zoning_codes/run.py --source zoneomics --test-mode
# python zoning_codes/run.py --source zoneomics
