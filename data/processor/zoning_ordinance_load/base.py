import os
import json
import hashlib
import logging
import sys
import pandas as pd
import chromadb
from template import BaseProceesor
from utils.gcp_storage import GCPStorage


class ZoningOrdinanceChromaDBLoader(BaseProceesor):
    def __init__(self):
        super().__init__()

        # Set up logger
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # GCP configuration
        self.gcp_project = os.environ.get("GCP_PROJECT", "spatially")
        self.gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")

        # ChromaDB Cloud configuration
        self.chromadb_api_key = os.environ.get("CHROMADB_API_KEY")
        self.chromadb_tenant = os.environ.get("CHROMADB_TENANT")
        self.chromadb_database = os.environ.get("CHROMADB_DATABASE")

        if not self.chromadb_api_key or not self.chromadb_tenant or not self.chromadb_database:
            raise ValueError("CHROMADB_API_KEY, CHROMADB_TENANT, and CHROMADB_DATABASE must be set")

        # Initialize GCS client
        self.storage = GCPStorage(
            gcp_project=self.gcp_project,
            bucket_name=self.gcs_bucket_name
        )

        self.logger.info(f"Initialized ChromaDB loader for bucket: {self.gcs_bucket_name}")

    def get_chromadb_client(self):
        """Connect to ChromaDB Cloud"""
        self.logger.info(f"Connecting to ChromaDB Cloud (tenant: {self.chromadb_tenant}, database: {self.chromadb_database})")

        client = chromadb.CloudClient(
            api_key=self.chromadb_api_key,
            tenant=self.chromadb_tenant,
            database=self.chromadb_database
        )

        return client

# ============================================================================
# TEMPORARY: Truncate to 36 bytes to fit ChromaDB free tier limit
# TODO: Remove once ChromaDB quota is increased
# ============================================================================


    def normalize_district_code_to_field(self, code):
        """Convert district code to valid ChromaDB field name (max 36 bytes)"""
        normalized = code.replace('.', '_').replace('-', '_').replace(' ', '_').replace('/', '_')
        field_name = f"district_{normalized}"
        
        if len(field_name) > 36:
            field_name = field_name[:36]
        

        return field_name

    def normalize_category_to_field(self, category):
        """Convert category to valid ChromaDB field name (max 36 bytes)"""
        # Use abbreviations for long category names
        abbreviations = {
            "Industrial / Manufacturing Districts": "cat_Industrial_Mfg",
            "Mixed Use Districts": "cat_Mixed_Use",
            "Residential Districts": "cat_Residential",
            "Local Business Districts": "cat_Local_Business",
            "General Business Districts": "cat_General_Business",
            "Open Space Districts": "cat_Open_Space"
        }

        if category in abbreviations:
            return abbreviations[category]

        # Fallback: normalize and truncate
        normalized = category.replace(' ', '_').replace('/', '_')
        field_name = f"cat_{normalized}"

        # TEMPORARY: Truncate to 36 bytes to fit ChromaDB free tier limit
        # TODO: Remove once ChromaDB quota is increased
        if len(field_name) > 36:
            field_name = field_name[:36]

        return field_name


# ============================================================================

    def load_embeddings_to_collection(self, collection, data_df, batch_size=500):
        """Load embeddings DataFrame into ChromaDB collection"""

        # Generate ids
        data_df["id"] = data_df.index.astype(str)
        hashed_docs = data_df["document"].apply(
            lambda x: hashlib.sha256(x.encode()).hexdigest()[:16]
        )
        data_df["id"] = hashed_docs + "-" + data_df["id"]

        # Process in batches
        total_inserted = 0
        for i in range(0, data_df.shape[0], batch_size):
            batch = data_df.iloc[i:i+batch_size].copy().reset_index(drop=True)

            ids = batch["id"].tolist()
            documents = batch["chunk"].tolist()
            embeddings = batch["embedding"].tolist()

            # Build metadata for each row
            metadatas = []
            for _, row in batch.iterrows():
                metadata = {
                    "document": row["document"],
                    "city": row["city"],
                    "district_code": json.dumps(row["district_code"]) if isinstance(row["district_code"], list) else row["district_code"],
                    "district_category": json.dumps(row["district_category"]) if isinstance(row["district_category"], list) else row["district_category"]
                }

                # Add flattened boolean fields for filtering district codes
                if isinstance(row["district_code"], list):
                    for code in row["district_code"]:
                        if code:
                            field_name = self.normalize_district_code_to_field(code)
                            metadata[field_name] = True

                # Add flattened boolean fields for filtering district categories
                if isinstance(row["district_category"], list):
                    for category in row["district_category"]:
                        if category:
                            cat_field = self.normalize_category_to_field(category)
                            metadata[cat_field] = True

                # Handle Boston vs Chicago metadata
                if "article" in row and row["article"]:
                    metadata["article"] = row["article"]

                if "section" in row and row["section"]:
                    metadata["section"] = row["section"]

                if "url" in row and row["url"]:
                    metadata["url"] = row["url"]

                if "heading" in row and row["heading"]:
                    metadata["heading"] = row["heading"]

                if "chapter" in row and row.get("chapter"):
                    metadata["chapter"] = row["chapter"]

                if "title" in row and row.get("title"):
                    metadata["title"] = row["title"]

                # ============================================================================
                # TEMPORARY WORKAROUND: ChromaDB free tier has 32 metadata key limit
                # TODO: REMOVE THIS ONCE CHROMADB QUOTA IS INCREASED OR MOVED TO PAID TIER
                # ============================================================================
                if len(metadata) > 32:
                    self.logger.warning(
                        f"Metadata has {len(metadata)} keys, exceeding ChromaDB limit of 32. "
                        f"Truncating to 32 keys. This is a TEMPORARY workaround. "
                        f"TODO: Upgrade ChromaDB tier or request quota increase."
                    )
                    # Keep only first 32 keys (preserves city, document, district_code, district_category, and some flattened fields)
                    metadata = dict(list(metadata.items())[:32])
                # ============================================================================

                metadatas.append(metadata)

            # Insert batch
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            total_inserted += len(batch)
            self.logger.info(f"Inserted {total_inserted} items...")

        self.logger.info(
            f"Finished inserting {total_inserted} items into collection '{collection.name}'"
        )

    def process(self, city: str = None, collection_name: str = "zoning-ordinance", test_mode: bool = False):
        """Load embeddings from GCS into ChromaDB Cloud"""
        self.logger.info(f"Starting ChromaDB loader (city={city}, collection={collection_name}, test_mode={test_mode})")

        # Clear ChromaDB cache
        chromadb.api.client.SharedSystemClient.clear_system_cache()

        # Connect to ChromaDB Cloud
        client = self.get_chromadb_client()

        # Create or get collection
        self.logger.info(f"Creating/getting collection: {collection_name}")

        try:
            # Check if collection exists
            existing_collections = client.list_collections()
            collection_exists = any(c.name == collection_name for c in existing_collections)

            if collection_exists and not test_mode:
                self.logger.info(f"Collection '{collection_name}' already exists. Deleting for fresh load.")
                client.delete_collection(name=collection_name)

            collection = client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self.logger.info(f"Created collection '{collection_name}'")

        except Exception as e:
            self.logger.warning(f"Could not recreate collection: {e}. Getting existing collection.")
            collection = client.get_collection(name=collection_name)

        # List all embedding JSONL files from GCS
        if city:
            # Load only specific city
            prefix = f"zoning_ordinance_embeddings/{city}/"
        else:
            # Load all cities
            prefix = "zoning_ordinance_embeddings/"

        self.logger.info(f"Listing embeddings from GCS path: {prefix}")

        blobs = self.storage.list_blobs(prefix=prefix)
        jsonl_blobs = [blob for blob in blobs if blob.name.endswith('.jsonl') and 'embeddings-' in blob.name]

        if test_mode:
            jsonl_blobs = jsonl_blobs[:1]

        self.logger.info(f"Found {len(jsonl_blobs)} embedding files to load")

        # Process each file
        for blob in jsonl_blobs:
            self.logger.info(f"Processing file: {blob.name}")

            # Download blob content as string
            jsonl_content = self.storage.download_blob_as_string(blob.name)

            # Parse JSONL
            data_df = pd.read_json(jsonl_content, lines=True)
            self.logger.info(f"Loaded {len(data_df)} records")

            # Load into ChromaDB
            self.load_embeddings_to_collection(collection, data_df)

        self.logger.info(f"ChromaDB loading complete! Total items in collection: {collection.count()}")


__all__ = ["ZoningOrdinanceChromaDBLoader"]
