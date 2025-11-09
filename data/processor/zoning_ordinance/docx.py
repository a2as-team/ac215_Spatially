from utils.gcp_storage import GCPStorage
from .base import ZoningOrdinanceBaseProcessor
import os
import pandas as pd
from markitdown import MarkItDown


class DocxProcessor(ZoningOrdinanceBaseProcessor):
    """
    General DOCX processor for embedding zoning ordinance documents.
    Assumes files follow a title/subtitle naming structure separated by FILE_NAME_SEPARATOR.
    """

    FILE_NAME_SEPARATOR = "⫸"

    def __init__(
        self,
        city: str,
        storage: GCPStorage,
        gcp_project: str,
        gcp_region: str,
        gcp_storage_source_directory: str,
    ):
        super().__init__(city, gcp_project, gcp_region, gcp_storage_source_directory)
        self.logger.info(
            f"Initialized {self.__class__.__name__} processor for {self.city}"
        )
        self.storage = storage
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region

    def load_docx_files_from_gcp(self, test_mode: bool = False):
        """Load all .docx files from GCS bucket."""
        # download the docx files from the resource url
        blobs = self.storage.list_blobs(prefix=f"{self.gcp_storage_source_directory}")
        docx_blobs = [blob for blob in blobs if blob.name.endswith(".docx")]

        if len(docx_blobs) == 0:
            raise ValueError(
                f"No docx files found for {self.city}. Please collect the zoning ordinance first."
            )

        if test_mode:
            docx_blobs = docx_blobs[:1]

        return docx_blobs

    def process_single_docx_file(self, docx_blob):
        """
        Process a single DOCX file: download it, extract title/subtitle from filename,
        convert to markdown, and save the markdown file.

        Args:
            docx_blob: GCS blob object for the DOCX file

        Returns:
            tuple: (text_content, title, subtitle, download_path, source_gcs_path)
        """
        # Ensure download directory exists
        os.makedirs(self.download_directory(), exist_ok=True)

        # download the docx file to a temp location
        temp_path = f"{self.download_directory()}/{os.path.basename(docx_blob.name)}"
        self.storage.download_blob_to_file(docx_blob.name, temp_path)

        # Extract title and subtitle from the filename
        # Assumes format: "title⫸subtitle.docx" or just "title.docx"
        filename = os.path.basename(docx_blob.name)
        filename_without_ext = os.path.splitext(filename)[0]
        split_name = filename_without_ext.split(self.FILE_NAME_SEPARATOR)

        title = split_name[0].strip()
        subtitle = split_name[1].strip() if len(split_name) > 1 else ""

        # Convert DOCX to markdown using MarkItDown
        md = MarkItDown()
        result = md.convert(temp_path)

        # Save markdown file
        download_path = f"{self.download_directory()}/{filename}.md"
        with open(download_path, "w", encoding="utf-8") as file:
            file.write(result.text_content)

        return result.text_content, title, subtitle, download_path, docx_blob.name

    def create_chunk_data(
        self,
        all_chunk_data: list,
        text_content: str,
        title: str,
        subtitle: str,
        download_path: str,
        source_gcs_path: str,
    ):
        """
        Create chunks from text content and extract zoning codes.

        Args:
            all_chunk_data: List to append chunk data to
            text_content: The markdown text content
            title: Document title
            subtitle: Document subtitle
            download_path: Path to the markdown file
            source_gcs_path: GCS path to the original DOCX file
        """
        chunks = self.text_splitter.create_documents([text_content])
        chunk_texts = [doc.page_content for doc in chunks]

        # Create markdown GCS path
        markdown_filename = os.path.basename(source_gcs_path) + ".md"
        markdown_gcs_path = (
            f"{self.gcp_storage_markdown_directory()}/{markdown_filename}"
        )

        # Create metadata with GCS information
        bucket_name = self.storage.bucket.name
        metadata = {
            "source_docx_gcs_path": source_gcs_path,
            "markdown_gcs_path": markdown_gcs_path,
            "bucket_name": bucket_name,
            "source_docx_url": f"gs://{bucket_name}/{source_gcs_path}",
            "markdown_url": f"gs://{bucket_name}/{markdown_gcs_path}",
        }

        for chunk_text in chunk_texts:
            zoning_codes = self.zoning_code_extractor.extract_zoning_codes_from_text(
                chunk_text
            )
            chunk_data = {
                "text_chunk": chunk_text,
                "document_title": title,
                "document_subtitle": subtitle,
                "download_path": download_path,
                "zoning_codes": zoning_codes,
                "metadata": metadata,
            }
            all_chunk_data.append(chunk_data)

        if not all_chunk_data:
            self.logger.warning(f"No chunks created for {title} {subtitle}")

    def generate_embedding_table(self, all_chunk_data: list):
        """
        Generate embeddings for all chunks and create a dataframe.

        Args:
            all_chunk_data: List of chunk dictionaries

        Returns:
            DataFrame with chunks and their embeddings
        """
        data_df = pd.DataFrame(all_chunk_data)
        chunks = data_df["text_chunk"].values.tolist()
        embeddings = self._generate_text_embeddings(chunks, batch_size=15)
        data_df["embedding"] = embeddings
        return data_df

    def process(self, test_mode: bool = False):
        """
        Main processing method: loads DOCX files from GCS, converts to markdown,
        creates chunks, generates embeddings, and uploads results.

        Args:
            test_mode: If True, only process the first file for testing
        """
        self.logger.info(
            f"Starting {self.__class__.__name__} processor (test_mode={test_mode})"
        )
        docx_blobs = self.load_docx_files_from_gcp(test_mode=test_mode)
        total_files = len(docx_blobs)
        self.logger.info(f"Found {total_files} DOCX file(s) to process")
        all_chunk_data = []

        for idx, docx_blob in enumerate(docx_blobs, 1):
            self.logger.info(f"\n[{idx}/{total_files}] Processing: {docx_blob.name}")
            text_content, title, subtitle, download_path, source_gcs_path = (
                self.process_single_docx_file(docx_blob)
            )
            self.create_chunk_data(
                all_chunk_data,
                text_content,
                title,
                subtitle,
                download_path,
                source_gcs_path,
            )
            self.logger.info(
                f"[{idx}/{total_files}] Created {len(all_chunk_data)} chunks so far"
            )

            # Upload markdown file to GCS
            markdown_filename = os.path.basename(docx_blob.name) + ".md"
            self.storage.upload_file(
                download_path,
                f"{self.gcp_storage_markdown_directory()}/{markdown_filename}",
            )
            self.logger.info(f"[{idx}/{total_files}] Uploaded markdown to GCS")

        # Generate embeddings
        self.logger.info(f"\nGenerating embeddings for {len(all_chunk_data)} chunks...")
        data_df = self.generate_embedding_table(all_chunk_data)
        self.logger.info(f"✓ Generated {len(data_df)} embeddings")

        # Save to JSONL in GCS
        jsonl_content = data_df.to_json(orient="records", lines=True)
        self.storage.upload_string_to_blob(
            jsonl_content, f"{self.gcp_storage_markdown_directory()}/embeddings.jsonl"
        )
        self.logger.info(
            f"Uploaded embeddings to: {self.gcp_storage_markdown_directory()}/embeddings.jsonl"
        )

        # Save internally as JSON for better readability
        data_df.to_json(
            os.path.join(self.download_directory(), "embeddings.json"),
            orient="records",
            indent=2,
        )

        # Save embeddings to PostgreSQL database
        # Convert dataframe back to list of dicts with embeddings
        embeddings_with_data = data_df.to_dict("records")
        self.logger.info("\nSaving embeddings to database...")
        inserted, skipped = self._insert_embeddings_to_db(embeddings_with_data)

        # Final summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Files processed:     {len(docx_blobs)}/{total_files}")
        self.logger.info(f"Chunks created:      {len(all_chunk_data)}")
        self.logger.info(f"Embeddings generated: {len(data_df)}")
        self.logger.info(f"Database records:    {inserted} inserted, {skipped} skipped")
        self.logger.info("=" * 60)
