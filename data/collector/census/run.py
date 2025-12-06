
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
from utils.db_accessor import DBAccessor
from census import CensusCollector
from census.state_fips import get_city_county
import pandas as pd

if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(flags=["--city"], prompt="City to collect", arg_type=str, required=True),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    city_key = args["city"].strip().lower()

    # Get county FIPS code for the city (required - no fallback)
    city_county_info = get_city_county(city_key)
    args["state"] = city_county_info["state"]
    args["county"] = city_county_info["county"]
    print(f"City '{city_key}' mapped to state={args['state']}, county={args['county']}")

    # Get valid geoids from database (only Boston's 207 tracts)
    db_name = os.environ.get("APP_DB_NAME")
    valid_geoids = set()
    if db_name:
        try:
            db = DBAccessor(db_name=db_name)
            try:
                results = db.execute("SELECT DISTINCT geoid FROM census_tract")
                valid_geoids = {row["geoid"] for row in results}
                print(f"✅ Found {len(valid_geoids)} valid geoids in census_tract table")
            except Exception as e:
                print(f"⚠️  Could not query database for geoids: {e}")
                print(f"   Will collect all data without filtering")
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️  Could not connect to database: {e}")
            print(f"   Will collect all data without filtering")
    else:
        print(f"⚠️  APP_DB_NAME not set, will collect all data without filtering")

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
                # Request tract-level data for specific county only
                # Passing county FIPS and tract="*" fetches all tracts in that county
                # Returns state, county, and tract columns for proper 11-digit geoid construction
                df = collector.collect(
                    table_code=table_code,
                    year=year,
                    state=args["state"],
                    county=args["county"],
                    tract="*"
                )
            except Exception as e:
                print(f"Skipping {table_code} {year}: {e}")
                continue

            # Filter to only valid geoids if we have them
            if valid_geoids:
                # Construct geoid from geography columns (same logic as processor)
                if 'state' in df.columns and 'county' in df.columns and 'tract' in df.columns:
                    df['geoid'] = (
                        df['state'].astype(str).str.zfill(2) +
                        df['county'].astype(str).str.zfill(3) +
                        df['tract'].astype(str).str.zfill(6)
                    )
                    # Filter to only rows with valid geoids
                    initial_rows = len(df)
                    df = df[df['geoid'].isin(valid_geoids)]
                    filtered_rows = len(df)
                    if initial_rows != filtered_rows:
                        print(f"  → Filtered from {initial_rows} to {filtered_rows} rows (kept {len(df['geoid'].unique())} unique geoids)")
                    # Remove temporary geoid column (processor will reconstruct it)
                    df = df.drop(columns=['geoid'])
                else:
                    print(f"  ⚠️  Could not construct geoid from CSV columns, skipping filter")

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
