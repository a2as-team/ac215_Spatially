import os
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from census import CensusCollector
from shared_config.cities import City

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city to collect data for (will be mapped to state)",
            arg_type=str,
            required=True,
        ),
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
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Map city to state using City registry
    city_upper = args["city"].upper()
    if City.is_valid(city_upper):
        state = City.get_state(city_upper)
        if state:
            args["state"] = state
            print(f"Mapping city '{args['city']}' to state '{args['state']}'")
        else:
            raise ValueError(f"City '{args['city']}' found but has no state defined. Please add state to cities.json")
    else:
        raise ValueError(f"Unknown city: {args['city']}. Known cities: {City.get_all()}")

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
        county=None,
        tract=None,
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
python census/run.py \
    --city chicago \
    --type population \
    --level tract \
    --year 2020

Note: City names are case-insensitive. Available cities are defined in config/cities.json
"""
