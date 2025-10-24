"""Boston-specific Label Studio service for development plans NER annotation."""
import json
import os
from .base import DevelopmentPlansLabelStudioBaseProcessor
from collector.development_plans.boston import BostonDevelopmentPlansCollector
from utils.gcp_storage import GCPStorage
import pandas as pd
from utils.pdf_parser import PDFParser

class BostonDevelopmentPlansLabelStudioProcessor(DevelopmentPlansLabelStudioBaseProcessor):
    """Processor for Boston development plans Label Studio."""
    
    def __init__(self):
        super().__init__()
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable not set")

        gcp_project = os.environ.get("GCP_PROJECT")
        if not gcp_project:
            raise ValueError("GCP_PROJECT environment variable not set")
        
        self.bucket_name = bucket_name
        self.gcp_project = gcp_project
        
        self.gcp_storage = GCPStorage(gcp_project=self.gcp_project, bucket_name=self.bucket_name)
    
    def load_metadata_from_csv(self):
        """Load the metadata from the csv file."""
        # find the metadata csv file in the gcp_storage_parent_directory
        
        metadata_csv_file = self.gcp_storage.list_files(self.original_pdf_gcs_storage_path())[0]
        # load the metadata from the csv file
        metadata = pd.read_csv(metadata_csv_file)
        self.metadata = metadata
        
    @classmethod
    def city(cls) -> str:
        """Return city name."""
        return BostonDevelopmentPlansCollector.city()
    
    @classmethod
    def original_pdf_gcs_storage_path(cls) -> str:
        """
        Return the original PDF GCS storage path.
        Remember that we have stored the development plan pdf per project in the GCS.
        """
        return BostonDevelopmentPlansCollector.gcp_storage_parent_directory()

    
    def prepare_annotation_data(self, doc_type: str):
        """Prepare the annotation data for the given document type."""
        
        pass


    def clean_value(self, val):
        """Convert pandas NaN to None for valid JSON."""
        if pd.isna(val):
            return None
        return val
            
    def create_task_from_pdf_and_metadata(self, pdf_blob, metadata_blob, file_url):
        text = PDFParser.extract_text_from_pdf(pdf_blob)

        # Handle GCS blob for metadata JSON
        if hasattr(metadata_blob, 'download_as_text'):
            # It's a GCS blob - download as text and parse
            metadata_text = metadata_blob.download_as_text()
            metadata = json.loads(metadata_text)
        else:
            # It's a file object
            metadata = json.load(metadata_blob)
        task = {
            "data": {
                "text": text,
                "project_name": metadata.get("project_name"),
                "project_id": metadata.get("project_id"),
                "file_name": pdf_blob.name,
                "file_path": file_url,
            },
            "meta": {
                "source": file_url,
                "project": metadata.get("project_name"),
                "doc_type_hint": metadata.get("document_type"),
                "char_count": len(text),
                "storage_mode": "gcs",
                "neighborhood": self.clean_value(metadata.get("neighborhood")),
                "address": self.clean_value(metadata.get("address")),
                "project_status": self.clean_value(metadata.get("project_status")),
                "project_type": self.clean_value(metadata.get("project_type")),
                "gross_floor_area": self.clean_value(metadata.get("gross_floor_area")),
                "land_sq_feet": self.clean_value(metadata.get("land_sq_feet")),
                "latitude": self.clean_value(metadata.get("latitude")),
                "longitude": self.clean_value(metadata.get("longitude")),
            },
        }
        return task

        
    def process(self, test_mode: bool = False):
        """Process the data."""
        # We will use pymupdf to extract the text from the pdf files.
        # we will go through each folder inside the gcp_storage_parent_directory
        self.logger.info(f"Processing development plans for {self.city()}")

        gcs_path = self.original_pdf_gcs_storage_path()
        # Ensure the path ends with / for list_dirs to work properly
        if not gcs_path.endswith('/'):
            gcs_path += '/'

        self.logger.info(f"Listing project folders in GCS path: {gcs_path}")
        self.logger.info(f"Using GCS bucket: {self.bucket_name}")

        # Debug: try listing all files first to see if anything exists
        all_files = self.gcp_storage.list_files(gcs_path)
        self.logger.info(f"Total files found under {gcs_path}: {len(all_files)}")
        if all_files:
            self.logger.info(f"Sample files: {all_files[:3]}")

        project_folders = self.gcp_storage.list_dirs(gcs_path)
        self.logger.info(f"Found {len(project_folders)} project folders: {project_folders[:3] if len(project_folders) > 3 else project_folders}...")

        if test_mode:
            self.logger.info(f"TEST MODE: Limiting to 5 projects")
            project_folders = project_folders[:5]
        for project_folder in project_folders:
            # we will go through each pdf file in the project folder
            files = self.gcp_storage.list_files(project_folder)
            pdf_files = [file for file in files if file.endswith(".pdf")]
            metadata_file = [file for file in files if file.endswith("metadata.json")][0]
        
            for pdf_file in pdf_files:
                # we will extract the text from the pdf file
                self.logger.info(f"Creating annotation ready JSON from {pdf_file}")

                # Get blob objects
                pdf_blob = self.gcp_storage.get_blob(pdf_file)
                metadata_blob = self.gcp_storage.get_blob(metadata_file)

                # Generate public URL for the PDF file
                file_url = self.gcp_storage.get_public_url(pdf_file)

                # Create the task
                try:
                    task = self.create_task_from_pdf_and_metadata(pdf_blob, metadata_blob, file_url)
                except Exception as e:
                    self.logger.error(f"Error creating task from {pdf_file}: {e}")
                    continue

                # Upload the task to GCS in the same project folder with .ner.json suffix
                # Extract filename from pdf_file path and change extension
                pdf_filename = pdf_file.split('/')[-1]  # Get filename from path
                ner_filename = pdf_filename.replace('.pdf', '.ner.json')
                destination_path = f"{project_folder}{ner_filename}"

                self.logger.info(f"Uploading task to {destination_path}")
                self.gcp_storage.upload_json(task, destination_path)