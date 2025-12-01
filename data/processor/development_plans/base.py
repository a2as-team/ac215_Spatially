from abc import ABC, abstractmethod
import os
import logging
import sys
from template import BaseProcessor
from utils.gcp_storage import GCPStorage
from utils.db_accessor import DBAccessor
from utils.pgvector_utils import PgVectorUtils
from google import genai
from google.genai import types, errors
from utils.semantic_splitter import SemanticChunker
import pandas as pd
import time
from psycopg2.extras import Json


class DevelopmentPlansBaseProcessor(BaseProcessor, ABC):
    def __init__(
        self,
        city: str,
        gcp_project: str,
        gcp_region: str,
        gcp_storage_source_directory: str,
    ):
        super().__init__()
        # Set city first since it's needed by _init_db()
        self.city = city
        self._init_logger()
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region
        self._init_llm_client()
        self._init_semantic_splitter()  # Must be before _init_db() since it sets embedding_dimension
        self._init_db()  # Needs embedding_dimension and self.city
        self.gcp_storage_source_directory = gcp_storage_source_directory

    def gcp_storage_output_directory(self) -> str:
        """Return the GCS storage path for this processor."""
        return f"development_plans_embed/{self.city}"

    def download_directory(self) -> str:
        """Return the download directory path for this processor."""
        return os.path.abspath(f"tmp/development_plans_embed/{self.city}")

    def _init_logger(self):
        import sys

        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _init_llm_client(self):
        self.llm_client = genai.Client(
            vertexai=True, project=self.gcp_project, location=self.gcp_region
        )

    def _init_semantic_splitter(self):
        self.embedding_model = "text-embedding-004"
        self.embedding_dimension = 768
        self.text_splitter = SemanticChunker(
            embedding_function=self._generate_text_embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=95,
            buffer_size=1,
        )

    def _init_db(self):
        self.db_name = os.environ.get(
            "APP_DB_NAME"
        )  # We will store the embeddings in the app database
        self.db = DBAccessor(db_name=self.db_name)
        # Enable pgvector extension
        PgVectorUtils.enable_extension(self.db)
        # Create table if it doesn't exist
        self._create_development_plans_embed_table()
        # Delete existing embeddings for this city to avoid duplicates
        self._delete_city_embeddings(self.city)

    def _generate_text_embeddings(
        self, chunks, batch_size=250, max_retries=5, retry_delay=5
    ):
        """Generate embeddings using Vertex AI text-embedding-004"""
        all_embeddings = []
        current_batch_size = batch_size

        i = 0
        while i < len(chunks):
            batch = chunks[i : i + current_batch_size]

            retry_count = 0
            while retry_count <= max_retries:
                try:
                    response = self.llm_client.models.embed_content(
                        model=self.embedding_model,
                        contents=batch,
                        config=types.EmbedContentConfig(
                            output_dimensionality=self.embedding_dimension
                        ),
                    )
                    all_embeddings.extend(
                        [embedding.values for embedding in response.embeddings]
                    )
                    i += current_batch_size
                    break

                except errors.APIError as e:
                    # Check if it's a token limit error
                    if e.code == 400 and "input token count" in str(e.message):
                        # Reduce batch size and retry immediately
                        new_batch_size = max(1, current_batch_size // 2)
                        if new_batch_size < current_batch_size:
                            self.logger.warning(
                                f"Token limit exceeded with batch size {current_batch_size}. "
                                f"Reducing to {new_batch_size} and retrying..."
                            )
                            current_batch_size = new_batch_size
                            batch = chunks[i : i + current_batch_size]
                            retry_count = 0  # Reset retry count for new batch size
                            continue
                        else:
                            # If batch_size is already 1, we can't reduce further
                            self.logger.error(
                                f"Token limit exceeded even with batch_size=1. "
                                f"Individual chunk is too large: {len(batch[0])} characters"
                            )
                            raise

                    retry_count += 1
                    if retry_count > max_retries:
                        self.logger.error(
                            f"Failed to generate embeddings after {max_retries} attempts. Last error: {str(e)}"
                        )
                        raise

                    wait_time = retry_delay * (2 ** (retry_count - 1))
                    self.logger.warning(
                        f"API error (code: {e.code}): {e.message}. Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})..."
                    )
                    time.sleep(wait_time)

        return all_embeddings

    def _create_development_plans_embed_table(self):
        """Create the development_plans_embed table with pgvector support."""
        self.db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS development_plans_embed (
                id SERIAL PRIMARY KEY,
                city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                chunk_hash TEXT UNIQUE NOT NULL,
                text_chunk TEXT NOT NULL,
                project_name VARCHAR(500),
                file_name VARCHAR(500),
                embedding vector({self.embedding_dimension}),
                zoning_codes TEXT[],
                article_reference TEXT[],
                location_context TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_development_plans_embed_city_id
                ON development_plans_embed(city_id);
            CREATE INDEX IF NOT EXISTS idx_development_plans_embed_chunk_hash
                ON development_plans_embed(chunk_hash);
            CREATE INDEX IF NOT EXISTS idx_development_plans_embed_embedding
                ON development_plans_embed USING hnsw (embedding vector_cosine_ops);
        """
        )
        self.logger.info("development_plans_embed table created/verified")

    def _get_city_id(self, city_name: str) -> int:
        """Get city_id from city name."""
        self.db.connect()
        with self.db.conn.cursor() as cur:
            cur.execute("SELECT id FROM cities WHERE name = %s", (city_name,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"City '{city_name}' not found in database")
            return result[0]

    def _delete_city_embeddings(self, city_name: str):
        """Delete all embeddings for a city to avoid duplicates."""
        city_id = self._get_city_id(city_name)
        # Check if table exists
        self.db.connect()
        with self.db.conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'development_plans_embed'
                )
            """
            )
            table_exists = cur.fetchone()[0]
            if table_exists:
                self.db.execute(
                    "DELETE FROM development_plans_embed WHERE city_id = %s", (city_id,)
                )
                self.logger.info(f"Deleted existing embeddings for {city_name}")

    def _insert_embeddings_to_db(self, embeddings_data: list, batch_size: int = 100):
        """
        Insert embeddings into the database in batches.

        Args:
            embeddings_data: List of dicts with keys: text_chunk, project_name, file_name,
                           zoning_codes, article_reference, location_context, embedding, metadata
            batch_size: Number of records to insert per batch

        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        city_id = self._get_city_id(self.city)
        self.logger.info(f"Inserting {len(embeddings_data)} embeddings for {self.city}")

        inserted_count = 0
        skipped_count = 0

        self.db.connect()
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i : i + batch_size]

            for data in batch:
                try:
                    # Compute hash for deduplication
                    chunk_hash = PgVectorUtils.compute_text_hash(data["text_chunk"])

                    # Convert embedding to pgvector format
                    embedding_str = PgVectorUtils.embedding_to_pgvector(
                        data["embedding"]
                    )

                    # Insert with ON CONFLICT to skip duplicates
                    insert_query = """
                        INSERT INTO development_plans_embed (
                            city_id, chunk_hash, text_chunk, project_name,
                            file_name, embedding, zoning_codes, article_reference,
                            location_context, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s, %s, %s)
                        ON CONFLICT (chunk_hash) DO NOTHING
                        RETURNING id;
                    """

                    with self.db.conn.cursor() as cur:
                        cur.execute(
                            insert_query,
                            (
                                city_id,
                                chunk_hash,
                                data["text_chunk"],
                                data.get("project_name", ""),
                                data.get("file_name", ""),
                                embedding_str,
                                data.get("zoning_codes", []),
                                data.get("article_reference", []),
                                data.get("location_context", ""),
                                Json(
                                    data.get("metadata", {})
                                ),  # Use Json() for JSONB field
                            ),
                        )
                        result = cur.fetchone()
                        if result:
                            inserted_count += 1
                            # Log progress every 50 records for visibility
                            if inserted_count % 50 == 0:
                                self.logger.info(
                                    f"  → Progress: {inserted_count}/{len(embeddings_data)} embeddings inserted"
                                )
                        else:
                            skipped_count += 1

                except Exception as e:
                    self.logger.error(f"Failed to insert embedding: {e}")
                    skipped_count += 1
                    continue

            # Commit after each batch
            self.db.conn.commit()

        self.logger.info(
            f"Database insertion complete: {inserted_count} inserted, {skipped_count} skipped"
        )
        return inserted_count, skipped_count

    @abstractmethod
    def process(self, test_mode: bool = False):
        pass
