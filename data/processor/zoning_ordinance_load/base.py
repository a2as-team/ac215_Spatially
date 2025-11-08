import os
import json
import hashlib
import logging
import sys
import pandas as pd
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
from template import BaseProceesor
from utils.gcp_storage import GCPStorage


class ZoningOrdinanceMilvusLoader(BaseProceesor):
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

        # Milvus Cloud configuration
        self.milvus_uri = os.environ.get("MILVUS_PUBLIC_ENDPOINT")
        self.milvus_token = os.environ.get("MILVUS_API_KEY")

        if not self.milvus_uri or not self.milvus_token:
            raise ValueError("MILVUS_PUBLIC_ENDPOINT and MILVUS_API_KEY must be set")

        # Initialize GCS client
        self.storage = GCPStorage(
            gcp_project=self.gcp_project,
            bucket_name=self.gcs_bucket_name
        )

        self.logger.info(f"Initialized Milvus loader for bucket: {self.gcs_bucket_name}")

    def get_milvus_client(self):
        """Connect to Milvus Cloud"""
        self.logger.info(f"Connecting to Milvus Cloud (endpoint: {self.milvus_uri})")

        client = MilvusClient(
            uri=self.milvus_uri,
            token=self.milvus_token
        )

        return client

    def load_embeddings_to_collection(self, client, collection_name, data_df, batch_size=500):
        """Load embeddings DataFrame into Milvus collection with optimal schema"""

        # Generate ids
        data_df["id"] = data_df.index.astype(str)
        hashed_docs = data_df["document"].apply(
            lambda x: hashlib.sha256(x.encode()).hexdigest()[:16]
        )
        data_df["id"] = hashed_docs + "-" + data_df["id"]

        # Fill NaN values with empty strings to ensure no None values
        string_fields = ["article", "section", "url", "heading", "chapter", "title"]
        for field in string_fields:
            if field in data_df.columns:
                data_df[field] = data_df[field].fillna("")

        # Process in batches
        total_inserted = 0
        for i in range(0, data_df.shape[0], batch_size):
            batch = data_df.iloc[i:i+batch_size].copy().reset_index(drop=True)

            # Build data for Milvus insert with optimal schema
            insert_data = []
            for _, row in batch.iterrows():
                # Ensure arrays are proper lists (not empty strings or None)
                district_codes = row["district_code"] if isinstance(row["district_code"], list) else []
                district_categories = row["district_category"] if isinstance(row["district_category"], list) else []

                # Create data entry matching the schema (use .get() for optional fields)
                data_entry = {
                    "id": row["id"],
                    "text": row["chunk"],
                    "vector": row["embedding"],
                    "city": row["city"],
                    "document": row["document"],
                    "district_codes": district_codes,
                    "district_categories": district_categories,
                    "article": row.get("article", ""),
                    "section": row.get("section", ""),
                    "url": row.get("url", ""),
                    "heading": row.get("heading", ""),
                    "chapter": row.get("chapter", ""),
                    "title": row.get("title", "")
                }
                insert_data.append(data_entry)

            # Insert batch into Milvus
            client.insert(collection_name=collection_name, data=insert_data)
            total_inserted += len(batch)
            self.logger.info(f"Inserted {total_inserted} items...")

        self.logger.info(
            f"Finished inserting {total_inserted} items into collection '{collection_name}'"
        )

    def process(self, city: str = None, collection_name: str = "zoning_ordinance", test_mode: bool = False):
        """Load embeddings from GCS into Milvus Cloud"""
        self.logger.info(f"Starting Milvus loader (city={city}, collection={collection_name}, test_mode={test_mode})")

        # Connect to Milvus Cloud
        client = self.get_milvus_client()

        # Create or get collection
        self.logger.info(f"Creating/getting collection: {collection_name}")

        # Check if collection exists
        if client.has_collection(collection_name):
            if not test_mode:
                self.logger.info(f"Collection '{collection_name}' already exists. Deleting for fresh load.")
                client.drop_collection(collection_name)
            else:
                self.logger.info(f"Test mode: Collection '{collection_name}' exists, will append data.")

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

        # Determine embedding dimension from first file
        embedding_dim = None
        if jsonl_blobs:
            first_blob = jsonl_blobs[0]
            jsonl_content = self.storage.download_blob_as_string(first_blob.name)
            sample_df = pd.read_json(jsonl_content, lines=True)
            if len(sample_df) > 0 and 'embedding' in sample_df.columns:
                embedding_dim = len(sample_df['embedding'].iloc[0])
                self.logger.info(f"Detected embedding dimension: {embedding_dim}")

        if embedding_dim is None:
            embedding_dim = 256  # Default fallback
            self.logger.warning(f"Could not detect embedding dimension, using default: {embedding_dim}")

        # Create collection with schema if it doesn't exist
        if not client.has_collection(collection_name):
            from pymilvus import DataType

            schema = client.create_schema(
                auto_id=False,
                enable_dynamic_field=False
            )

            # Primary key
            schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)

            # Document text
            schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)

            # Vector embedding
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

            # Filterable metadata fields
            schema.add_field(field_name="city", datatype=DataType.VARCHAR, max_length=50)
            schema.add_field(field_name="document", datatype=DataType.VARCHAR, max_length=500)

            # Array fields for multi-value filtering
            schema.add_field(
                field_name="district_codes",
                datatype=DataType.ARRAY,
                element_type=DataType.VARCHAR,
                max_capacity=100,  # Increased to handle documents with many district codes
                max_length=50
            )
            schema.add_field(
                field_name="district_categories",
                datatype=DataType.ARRAY,
                element_type=DataType.VARCHAR,
                max_capacity=10,
                max_length=100
            )

            # Optional metadata fields
            schema.add_field(field_name="article", datatype=DataType.VARCHAR, max_length=500)
            schema.add_field(field_name="section", datatype=DataType.VARCHAR, max_length=500)
            schema.add_field(field_name="url", datatype=DataType.VARCHAR, max_length=1000)
            schema.add_field(field_name="heading", datatype=DataType.VARCHAR, max_length=500)
            schema.add_field(field_name="chapter", datatype=DataType.VARCHAR, max_length=500)
            schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=500)

            # Create index for vector field
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                metric_type="COSINE",
                index_type="AUTOINDEX"
            )

            client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params
            )
            self.logger.info(f"Created collection '{collection_name}' with dimension {embedding_dim}")

        # Process each file
        for blob in jsonl_blobs:
            self.logger.info(f"Processing file: {blob.name}")

            # Download blob content as string
            jsonl_content = self.storage.download_blob_as_string(blob.name)

            # Parse JSONL
            data_df = pd.read_json(jsonl_content, lines=True)
            self.logger.info(f"Loaded {len(data_df)} records")

            # Load into Milvus
            self.load_embeddings_to_collection(client, collection_name, data_df)

        # Flush the collection to persist all data
        self.logger.info(f"Flushing collection to persist data...")
        client.flush(collection_name)
        self.logger.info(f"Data flushed successfully")

        # Get collection stats
        stats = client.get_collection_stats(collection_name)
        self.logger.info(f"Milvus loading complete! Collection stats: {stats}")


__all__ = ["ZoningOrdinanceMilvusLoader"]
