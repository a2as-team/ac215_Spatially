from abc import ABC, abstractmethod
import os
import logging
import sys
from template import BaseProcessor
from utils.zoning_code_extractor import ZoningCodeExtractor
from utils.gcp_storage import GCPStorage
from utils.db_accessor import DBAccessor
from google import genai
from google.genai import types, errors
from utils.semantic_splitter import SemanticChunker
import pandas as pd
import time


class ZoningOrdinanceEmbedBaseProcessor(BaseProcessor, ABC):
    def __init__(
        self,
        city: str,
        gcp_project: str,
        gcp_region: str,
        gcp_storage_source_directory: str,
    ):
        super().__init__()
        # Validate required class properties
        self._init_logger()
        self._init_db()
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region
        self._init_llm_client()
        self._init_semantic_splitter()
        self.gcp_storage_source_directory = gcp_storage_source_directory

        self.city = city
        self.zoning_code_extractor = ZoningCodeExtractor(city=city)

    def gcp_storage_markdown_directory(self) -> str:
        """Return the GCS storage path for this processor."""
        return f"zoning_ordinance_markdown/{self.city}"

    def download_directory(self) -> str:
        """Return the download directory path for this processor."""
        return os.path.abspath(f"tmp/zoning_ordinance_embed/{self.city}")

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
        )  # We will store the census tracts in the app database
        self.db = DBAccessor(db_name=self.db_name)

    def _generate_text_embeddings(
        self, chunks, batch_size=250, max_retries=5, retry_delay=5
    ):
        """Generate embeddings using Vertex AI text-embedding-004"""
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

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
                    break

                except errors.APIError as e:
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

    @abstractmethod
    def process(self, test_mode: bool = False):
        pass
