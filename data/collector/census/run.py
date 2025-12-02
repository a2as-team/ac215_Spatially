
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
from utils.gcp_storage import GCPStorage
from census import CensusCollector
from shared_config.city_service import CityService
import pandas as pd

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(flags=["--city"], prompt="City to collect", arg_type=str, required=True),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    city_key = args["city"].strip().lower()
    with CityService() as service:
        city = service.get_city(city_key)
        if city:
            state = city.get("state")
            if state:
                args["state"] = state
                print(f"Mapping city '{args['city']}' to state '{args['state']}'")
            else:
                raise ValueError(f"City '{args['city']}' found but has no state defined.")
        else:
            available = [c["name"] for c in service.get_all_cities()]
            raise ValueError(f"Unknown city: {args['city']}. Known cities: {available[:10]}...")

    collector = CensusCollector()
    table_codes = list(collector.caller_map.keys())
    years = list(range(2009, 2024))  # Include 2023

    out_dir = os.path.join(os.path.dirname(__file__), "downloads")
    os.makedirs(out_dir, exist_ok=True)

    # Initialize GCP Storage for uploading files
    gcp_project = os.environ.get("GCP_PROJECT")
    gcs_bucket = os.environ.get("GCS_BUCKET_NAME")
    print(f"Environment check: GCP_PROJECT={gcp_project}, GCS_BUCKET_NAME={gcs_bucket}")

    gcp_storage = None
    if gcp_project and gcs_bucket:
        try:
            gcp_storage = GCPStorage(gcp_project=gcp_project, bucket_name=gcs_bucket)
            print(f"✅ GCP Storage initialized successfully: bucket={gcs_bucket}")
        except Exception as e:
            print(f"❌ Failed to initialize GCP Storage: {e}")
            print(f"   This means files will be saved locally but NOT uploaded to GCS!")
    else:
        print(f"⚠️  GCP Storage NOT initialized (missing environment variables)")

    manifests = []
    for table_code in table_codes:
        for year in years:
            print(f"Collecting: table={table_code} year={year}")
            try:
                # Request tract-level data by passing tract="*"
                # This fetches all tracts in the state and returns state, county, and tract columns
                # for proper 11-digit geoid construction (state + county + tract)
                df = collector.collect(table_code=table_code, year=year, state=args["state"], tract="*")
            except Exception as e:
                print(f"Skipping {table_code} {year}: {e}")
                continue

            # Save to local file
            filename = f"{city_key}_{args['state']}_{table_code}_{year}.csv"
            out_path = os.path.join(out_dir, filename)
            df.to_csv(out_path, index=False)

            # Upload to GCS
            if gcp_storage:
                gcs_path = f"census/{city_key}/{filename}"
                try:
                    print(f"  → Uploading {filename} to GCS...")
                    gcp_storage.upload_file(file_path=out_path, destination_path=gcs_path)
                    print(f"  ✅ Uploaded to GCS: gs://{gcs_bucket}/{gcs_path}")
                except Exception as e:
                    print(f"  ❌ Failed to upload to GCS: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"  ⚠️  Skipping GCS upload (storage not initialized)")

            manifests.append({"city": city_key, "state": args["state"], "table": table_code, "year": year, "rows": len(df)})

    if manifests:
        # Save manifest locally
        manifest_path = os.path.join(out_dir, "manifest.csv")
        pd.DataFrame(manifests).to_csv(manifest_path, index=False)

        # Upload manifest to GCS
        if gcp_storage:
            gcs_manifest_path = f"census/{city_key}/manifest.csv"
            try:
                print(f"Uploading manifest.csv to GCS...")
                gcp_storage.upload_file(file_path=manifest_path, destination_path=gcs_manifest_path)
                print(f"✅ Manifest uploaded to GCS: gs://{gcs_bucket}/{gcs_manifest_path}")
            except Exception as e:
                print(f"❌ Failed to upload manifest to GCS: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  Skipping manifest upload (storage not initialized)")

        print(f"Done. Collected {len(manifests)} files.")
    else:
        print("No outputs were generated.")
