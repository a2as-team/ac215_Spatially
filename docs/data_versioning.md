# Data Versioning and Reproducibility

## Overview

Spatially uses **Google Cloud Storage (GCS)** as the primary data storage system for large datasets, including census ACS table data, zoning ordinances, zoning maps, census tract boundaries, and development plans. This approach provides scalable, cost-effective storage with easy integration with our data processing pipelines.

## Methodology

### Why GCS?

We chose GCS over alternatives like DVC (Data Version Control) for the following reasons:

1. **Scale**: Census data, zoning documents, maps, and development plans are large (hundreds of MBs to GBs), making Git-based solutions impractical
2. **Integration**: Our data processing pipelines already run on Google Cloud Platform (Vertex AI), making GCS a natural fit
3. **Accessibility**: GCS integrates seamlessly with our collectors, processors, and training jobs
4. **Versioning**: GCS object versioning and organized directory structures enable data lineage tracking

### Data Organization Structure

Data in GCS is organized by data type and city, following a consistent directory structure:

```
gs://{bucket-name}/
├── census/
│   └── {city}/
│       ├── {city}_{state}_{table_code}_{year}.csv
│       └── manifest.csv
│
├── zoning_ordinance/
│   └── {city}/
│       ├── {document_name}.docx
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
        │   └── {document_type}.json
        └── ner_training_data/
            └── {annotations}.json (label studio json export)
```

### Versioning Strategy

#### 1. Directory-Based Versioning

Each data collection run creates files in city-specific directories. When data is updated:

- Metadata files track source URLs (zoning ordinance)
- Manifest files track collected tables and years (census data)
- Historical versions can be preserved by using dated subdirectories if needed

#### 2. Metadata Tracking

Different collectors use different metadata approaches:

- **Zoning Ordinance**: Generates `metadata.json` file storing `resource_url` (source URL of the zoning ordinance)
- **Census Data**: Generates `manifest.csv` file listing all collected tables with city, state, table code, year, and row counts
- **Development Plans**: Uses file hashes (MD5) for duplicate detection during upload, but not stored in metadata

Census manifest structure (CSV):

```csv
city,state,table,year,rows
boston,ma,DP04,2023,1234
boston,ma,S1901,2023,567
...
```

#### 3. Census Data Versioning

Census ACS table data is versioned by:

- **City**: Each city has its own directory
- **Year**: Each ACS release year is stored separately (2009-2023)
- **Table**: Each ACS table (DP04, S1901, etc.) is stored as a separate file
- **State**: State abbreviation is included in filename

File naming convention: `{city}_{state}_{table_code}_{year}.csv`

Example: `boston_ma_DP04_2023.csv` (Boston, Massachusetts, Housing Characteristics, 2023)

GCS storage path: `census/{city}/{city}_{state}_{table_code}_{year}.csv`

The collector also generates a `manifest.csv` file listing all collected tables:

- GCS path: `census/{city}/manifest.csv`
- Contains: city, state, table, year, and row count for each file

**Note**: Files are saved both locally (`data/collector/census/downloads/`) and uploaded to GCS. If GCS upload fails, files remain available locally.

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
    file_path="local_file.docx",
    destination_path="zoning_ordinance/boston/article_1.docx"
)

# Download file
storage.download_file(
    source_path="zoning_ordinance/boston/article_1.docx",
    destination_path="local_file.docx"
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
# Example 1: List files in a directory
city = "boston"
files = storage.list_files(prefix=f"zoning_ordinance/{city}/", recursive=True)
print(f"Found {len(files)} files for {city}")

# Example 2: Download a specific file
storage.download_file(
    source_path="zoning_ordinance/boston/article_1.docx",
    destination_path="./local/article_1.docx"
)

# Example 3: Download an entire directory
storage.download_dir(
    source_path="zoning_ordinance/boston/",
    destination_path="./local/zoning_ordinance/boston/"
)

# Example 4: List blob objects and filter by file type
blobs = storage.list_blobs(prefix="zoning_ordinance/boston/")
for blob in blobs:
    if blob.name.endswith(".docx"):
        print(f"Found DOCX file: {blob.name}")
        # Download using blob object
        storage.download_blob_to_file(blob.name, f"./local/{os.path.basename(blob.name)}")

# Example 5: List directories (cities)
cities = storage.list_dirs(prefix="zoning_ordinance/")
print(f"Available cities: {cities}")

# Example 6: Download census data
storage.download_file(
    source_path="census/boston/boston_ma_DP04_2023.csv",
    destination_path="./local/boston_ma_DP04_2023.csv"
)

# Example 7: Download census manifest
storage.download_file(
    source_path="census/boston/manifest.csv",
    destination_path="./local/manifest.csv"
)
```

**Note**: Census ACS table data is stored in GCS at `census/{city}/` with files named `{city}_{state}_{table_code}_{year}.csv`. The collector also generates a `manifest.csv` file listing all collected tables. Files are saved both locally (`data/collector/census/downloads/`) and uploaded to GCS. If GCS credentials are not configured, files remain available locally only.

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
blob_name = "zoning_ordinance/boston/article_1.docx"
all_versions = list(bucket.list_blobs(prefix=blob_name, versions=True))
print(f"Found {len(all_versions)} versions of {blob_name}")

# Download a specific version by generation number
target_generation = 1234567890000000  # Example generation number
blob_with_version = bucket.blob(blob_name, generation=target_generation)
blob_with_version.download_to_filename("./local/article_1_v1.docx")
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
blob = storage.get_blob("zoning_ordinance/boston/article_1.docx")
if blob:
    blob.reload()  # Fetch metadata
    print(f"Created: {blob.time_created}")
    print(f"Updated: {blob.updated}")
```

## Reproducibility

### Data Processing Reproducibility

- Data Processors download data from GCS (organized by city and data type)
- Processing code is versioned in Git

### Model Training Reproducibility

Model training uses versioned data from GCS:

1. Training data is stored in GCS: `gs://bucket/development_plans/{city}/ner_training_data`
2. Training scripts are versioned in Git
3. Training parameters are logged to Weights & Biases
4. Model checkpoints are saved to GCS with timestamps
