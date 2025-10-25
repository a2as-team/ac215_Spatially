import os
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from development_plans_label_studio import DevelopmentPlansLabelStudio

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to process",
            arg_type=str,
            required=True,
        ),
         "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (only process first few pages)",
            arg_type=bool,
            required=False,
            default=False,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    processor = DevelopmentPlansLabelStudio()
    processor.process(city=args["city"], test_mode=args["test"])