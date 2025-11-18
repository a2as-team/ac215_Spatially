
import os
import sys
from pathlib import Path

# Add parent directory to path to enable imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Add project root to path for shared_config
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from census import CensusCollector
from shared_config.cities import City
import pandas as pd

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(flags=["--city"], prompt="City to collect", arg_type=str, required=True),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    city_key = args["city"].strip().lower()
    if City.is_valid(city_key):
        state = City.get_state(city_key)
        if state:
            args["state"] = state
            print(f"Mapping city '{args['city']}' to state '{args['state']}'")
        else:
            raise ValueError(f"City '{args['city']}' found but has no state defined.")
    else:
        raise ValueError(f"Unknown city: {args['city']}. Known cities: {City.get_all()}")

    collector = CensusCollector()
    table_codes = list(collector.caller_map.keys())
    years = list(range(2009, 2024))  # Include 2023

    out_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(out_dir, exist_ok=True)

    manifests = []
    for table_code in table_codes:
        for year in years:
            print(f"Collecting: table={table_code} year={year}")
            try:
                df = collector.collect(table_code=table_code, year=year, state=args["state"])
            except Exception as e:
                print(f"Skipping {table_code} {year}: {e}")
                continue
            out_path = os.path.join(out_dir, f"{city_key}_{args['state']}_{table_code}_{year}.csv")
            df.to_csv(out_path, index=False)
            manifests.append({"city": city_key, "state": args["state"], "table": table_code, "year": year, "rows": len(df)})
    if manifests:
        pd.DataFrame(manifests).to_csv(os.path.join(out_dir, "manifest.csv"), index=False)
        print("Done.")
    else:
        print("No outputs were generated.")
