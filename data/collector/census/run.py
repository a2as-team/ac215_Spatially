import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from census import CensusCollector


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
    # save the dataframe to a csv file
    df_folder = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(df_folder, exist_ok=True)
    df.to_csv(
        os.path.join(
            df_folder,
            f"{args['state']}_{args['type']}_{args['level']}_{args['year']}.csv",
        ),
        index=False,
    )
    print(df.head())

"""
Example usage: (#you must be in the /data directory)
python collector/census/run.py \
    --type population \
    --level tract \
    --year 2020 \
    --state IL \
    --county "" \
    --tract ""
"""
