import os
from census_tract import CensusTractCollector
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from census import CensusCollector

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to collect data for",
            arg_type=str,
            required=True,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = CensusTractCollector()
    collector.collect(args["city"])