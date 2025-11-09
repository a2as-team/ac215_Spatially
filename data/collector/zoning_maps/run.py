import os
from zoning_maps import ZoningMapsCollector
from utils.smart_arg_parser import SmartArgItem, SmartArgParser

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to collect zoning maps for",
            arg_type=str,
            required=True,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = ZoningMapsCollector()
    collector.collect(args["city"].lower())
