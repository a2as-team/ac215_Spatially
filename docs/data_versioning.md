# Data Versioning and Reproducibility

## Overview

Spatially uses **Google Cloud Storage (GCS)** as the primary data versioning system for large datasets, including zoning ordinances, zoning maps, census tract boundaries, and development plans. This approach provides scalable, cost-effective storage with built-in versioning capabilities and easy integration with our data processing pipelines.

## Methodology

### Why GCS?

We chose GCS over alternatives like DVC (Data Version Control) for the following reasons:

1. **Scale**: Zoning documents, maps, and development plans are large (hundreds of MBs to GBs), making Git-based solutions impractical
2. **Integration**: Our data processing pipelines already run on Google Cloud Platform (Vertex AI), making GCS a natural fit
3. **Accessibility**: GCS integrates seamlessly with our collectors, processors, and training jobs
4. **Versioning**: GCS object versioning and organized directory structures enable data lineage tracking

### Data Organization Structure

Data in GCS is organized by data type and city, following a consistent directory structure:

```
gs://{bucket-name}/
├── census/
│   └── {city}/
│       └── {table_code}_{year}.csv
│
├── zoning_ordinance/
│   └── {city}/
│       ├── {document_name}.xlsx
│       ├── {document_name}.pdf
│       └── metadata.json
│
├── zoning_maps/
│   └── {city}/
│       ├── static/
│       │   └── {static_file}.*
│       └── geojson/
│           └── {geojson_file}.geojson
│
├── census_tracts/
│   └── {city}/
│       └── {tract_file}.*
│
└── development_plans/
    └── {city}/
        ├── {project_name}/
        │   └── {document_type}.pdf
        └── ner_training_data/
            └── annotations.json
```

### Versioning Strategy

#### 1. Directory-Based Versioning

Each data collection run creates files in city-specific directories. When data is updated:

- New files are uploaded with the same name (overwriting old versions)
- Metadata files track collection timestamps and source URLs
- Historical versions can be preserved by using dated subdirectories if needed

#### 2. Metadata Tracking

Some collectors generate a `metadata.json` file that includes basic collection information:

- **Zoning Ordinance**: Stores `resource_url` (source URL of the zoning ordinance)
- **Development Plans**: Uses file hashes (MD5) for duplicate detection during upload, but not stored in metadata

Current metadata structure for zoning ordinance:

```json
{
  "resource_url": "https://library.municode.com/ma/boston/codes/redevelopment_authority"
}
```

**Note**: The current implementation stores minimal metadata. Enhanced versioning features (collection timestamps, file hashes, file lists) are not yet implemented but could be added for better data lineage tracking.

#### 3. Census Data Versioning

Census data is versioned by:

- **Year**: Each ACS release year is stored separately
- **Table**: Each ACS table (DP04, S1901, etc.) is stored as a separate file
- **State**: Data is organized by state FIPS code

File naming convention: `{CITY}_{STATE}_{TABLE_CODE}_{YEAR}.csv`

Example: `25_DP04_2023.csv` (Massachusetts, Housing Characteristics, 2023)

## Implementation

### GCS Storage Client

The `GCPStorage` class (`data/collector/utils/gcp_storage.py`) provides a unified interface for GCS operations:

```python
from utils.gcp_storage import GCPStorage

storage = GCPStorage(
    gcp_project="your-project",
    bucket_name="your-bucket"
)

# Upload file
storage.upload_file(
    file_path="local_file.xlsx",
    destination_path="zoning_ordinance/boston/article_1.xlsx"
)

# Download file
storage.download_file(
    source_path="zoning_ordinance/boston/article_1.xlsx",
    destination_path="local_file.xlsx"
)

# List files
files = storage.list_files(prefix="zoning_ordinance/boston/", recursive=True)
```

### Collector Integration

All collectors extend base classes that automatically handle GCS uploads:

```python
class ZoningOrdinanceBaseCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.gcp_storage = GCPStorage(
            gcp_project=os.environ.get("GCP_PROJECT"),
            bucket_name=os.environ.get("GCS_BUCKET_NAME")
        )

    def gcp_storage_parent_directory(self) -> str:
        return f"zoning_ordinance/{self.city()}"
```

### Processor Integration

Processors download data from GCS before processing:

```python
class ZoningOrdinanceProcessor:
    def __init__(self, city: str):
        self.storage = GCPStorage(...)
        self.city = city

    def gcp_storage_source_directory(self) -> str:
        return f"zoning_ordinance/{self.city}"
```

## Data Retrieval Instructions

### Retrieving Data from GCS

All data retrieval uses the `GCPStorage` class from `utils.gcp_storage`. Here are examples based on how the codebase actually implements data retrieval:

```python
import os
from utils.gcp_storage import GCPStorage

storage = GCPStorage(
    gcp_project=os.environ.get("GCP_PROJECT"),
    bucket_name=os.environ.get("GCS_BUCKET_NAME")
)
blobs = storage.list_blobs(prefix="zoning_ordinance/boston/")
for blob in blobs:
    if blob.name.endswith(".docx"):
        print(f"Found DOCX file: {blob.name}")
        # Download using blob object
        storage.download_blob_to_file(blob.name, f"./local/{os.path.basename(blob.name)}")
```

## Version History

### Tracking Versions

Version history is maintained through:

1. **GCS Object Timestamps**: GCS automatically tracks object creation and modification times. These can be accessed via blob metadata but are not explicitly used in the codebase.

2. **Git Commits**: Data collection scripts are versioned in Git, providing a link between code versions and collection runs. To track when data was collected, check the Git commit history for when collectors were run.

3. **Database Timestamps**: Processed data stored in PostgreSQL includes `created_at` timestamps (e.g., `zoning_maps.created_at`, `zoning_ordinance_embed.created_at`), which indicate when data was inserted into the database.

### Accessing Historical Versions

**Current State**: GCS object versioning is not currently enabled or implemented in the codebase. When files are re-uploaded, previous versions are overwritten.

**To Enable Historical Version Access**:

If you enable object versioning on your GCS bucket, you can access historical versions using the GCS client:

```bash
# Enable object versioning
gsutil versioning set on gs://your-bucket
```

Then access historical versions programmatically:

```python
from google.cloud import storage
import os

# Initialize GCS client
client = storage.Client(project=os.environ.get("GCP_PROJECT"))
bucket = client.bucket(os.environ.get("GCS_BUCKET_NAME"))

# List all versions of a specific file
blob_name = "zoning_ordinance/boston/article_1.xlsx"
all_versions = list(bucket.list_blobs(prefix=blob_name, versions=True))
print(f"Found {len(all_versions)} versions of {blob_name}")

# Download a specific version by generation number
target_generation = 1234567890000000  # Example generation number
blob_with_version = bucket.blob(blob_name, generation=target_generation)
blob_with_version.download_to_filename("./local/article_1_v1.xlsx")
```

**Alternative: Accessing GCS Object Timestamps**

Even without versioning enabled, you can check when files were last modified:

```python
from utils.gcp_storage import GCPStorage
import os

storage = GCPStorage(
    gcp_project=os.environ.get("GCP_PROJECT"),
    bucket_name=os.environ.get("GCS_BUCKET_NAME")
)

# Get blob metadata including timestamps
blob = storage.get_blob("zoning_ordinance/boston/article_1.xlsx")
if blob:
    blob.reload()  # Fetch metadata
    print(f"Created: {blob.time_created}")
    print(f"Updated: {blob.updated}")
```

## Reproducibility

### Data Collection Reproducibility

To reproduce a data collection run:

1. **Check Git Commit**: Identify the commit hash of the collector code

   ```bash
   git log --oneline data/collector/census/
   ```

2. **Check Metadata**: Review the metadata file for collection parameters

   ```python
   import json
   from utils.gcp_storage import GCPStorage
   import os

   storage = GCPStorage(
       gcp_project=os.environ.get("GCP_PROJECT"),
       bucket_name=os.environ.get("GCS_BUCKET_NAME")
   )

   # Download and read metadata
   storage.download_file(
       source_path="zoning_ordinance/boston/metadata.json",
       destination_path="./tmp/metadata.json"
   )
   with open("./tmp/metadata.json", "r") as f:
       metadata = json.load(f)
   print(f"Resource URL: {metadata.get('resource_url')}")

   # Note: Collection timestamps are not currently stored in metadata.
   # Check GCS blob timestamps or Git commit history for collection dates.

   # For census tract data, list files
   census_tract_files = storage.list_files(prefix="census_tracts/boston/", recursive=True)
   print(f"Census tract files: {census_tract_files}")
   ```

3. **Re-run Collector**: Execute the collector with the same parameters
   ```bash
   python data/collector/zoning_ordinance/run.py --city boston
   ```

### Processing Reproducibility

Processing steps are reproducible because:

- Processors download data from GCS (versioned source)
- Processing code is versioned in Git
- Processing parameters can be specified via command-line arguments

### Model Training Reproducibility

Model training uses versioned data from GCS:

1. Training data is stored in GCS: `gs://bucket/development_plans/{city}/ner_training_data`
2. Training scripts are versioned in Git
3. Training parameters are logged to Weights & Biases
4. Model checkpoints are saved to GCS with versioned paths
