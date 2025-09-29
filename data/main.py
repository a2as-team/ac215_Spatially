from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from collector.census import CensusCollector

if __name__ == "__main__":
    schema = {
        "type": SmartArgItem(
            flags=["--type"],
            prompt="The type of data to collect",
            arg_type=str,
            required=True,
        ),
        "level": SmartArgItem(
            flags=["--level"],
            prompt="The level of data to collect (state, county, tract)",
            arg_type=str,
            required=True,
        ),
        "year": SmartArgItem(
            flags=["--year"],
            prompt="The year of data to collect",
            arg_type=int,
            required=True,
        ),
        "state": SmartArgItem(
            flags=["--state"],
            prompt="The state of data to collect",
            arg_type=str,
            required=False,
        ),
        "county": SmartArgItem(
            flags=["--county"],
            prompt="The county of data to collect",
            arg_type=str,
            required=False,
        ),
        "tract": SmartArgItem(
            flags=["--tract"],
            prompt="The tract of data to collect",
            arg_type=str,
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = CensusCollector()
    if args["type"] not in collector.caller_map:
        raise ValueError(
            f"Invalid type: {args['type']}, must be one of {collector.caller_map.keys()}"
        )

    df = collector.collect(
        type=args["type"],
        level=args["level"],
        year=args["year"],
        state=args["state"],
        county=args["county"],
        tract=args["tract"],
    )
    print(df)
