import logging
from utils.selenium import SeleniumUtil
import pandas as pd
import os
import time
import json
from .base import BaseDevelopmentPlansCollector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from utils.geo_locater import GeoLocater
from utils.gcp_storage import GCPStorage
from utils.file_hash_checker import FileHashChecker


# Set up the logger for this module at the module level
import sys
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    # Use stdout instead of stderr for Vertex AI logging
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BostonDevelopmentPlansCollector(BaseDevelopmentPlansCollector):
    @classmethod
    def city(cls) -> str:
        return "boston"

    @classmethod
    def resource_url(cls) -> str:
        return "https://apps.bostonplans.org/recordslibrary/"

    @classmethod
    def pdf_base_directory(cls) -> str:
        return f"{cls.download_directory()}"

    @classmethod
    def csv_file(cls) -> str:
        """Return the CSV file path for overview of all projects."""
        return f"{cls.download_directory()}/metadata.csv"

    @classmethod
    def ALLOWED_DOCUMENT_KEYWORDS(cls):
        return [
            "BPDA Board",
            "Small Project Review Application",
            "Institutional Master Plan Notification Form",
            "Planned Development Area",
            "Letter of Intent",
        ]

    def __init__(self):
        super().__init__()
        self.selenium_util = SeleniumUtil(headless=True, download_dir=self.download_directory())
        self.projects = {}  # Dictionary keyed by project_id
        self.logger = logger  # Use the module-level logger

        # Initialize GCP Storage connection (optional - gracefully handle if credentials missing)
        self.gcp_storage = None
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
        gcp_project = os.environ.get("GCP_PROJECT")

        if bucket_name and gcp_project:
            try:
                self.gcp_storage = GCPStorage(gcp_project=gcp_project, bucket_name=bucket_name)
                self.logger.info("GCS connection established")
            except Exception as e:
                self.logger.warning(f"Could not connect to GCS: {e}. Will operate without GCS features.")
        else:
            self.logger.warning("GCS credentials not found (GCS_BUCKET_NAME or GCP_PROJECT). Will operate without GCS features.")

    def is_next_page_button_enabled(self):
        next_page_button = self.selenium_util.driver.find_element(
            By.XPATH, "//button[@title='Next page']"
        )
        return "Mui-disabled" not in next_page_button.get_attribute("class")

    def find_rows(self):
        return self.selenium_util.driver.find_element(
            By.XPATH, "//table[@role='grid']/tbody"
        ).find_elements(By.TAG_NAME, "tr")

    def parse_row(self, row):
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 3:
            project_name = cells[0].text.strip()
            project_link = cells[0].find_element(By.TAG_NAME, "a").get_attribute("href")
            neighborhood = cells[1].text.strip()
            document_type = cells[2].text.strip()
            try:
                document_link = (
                    cells[2].find_element(By.TAG_NAME, "a").get_attribute("href")
                )
            except NoSuchElementException:
                document_link = None
            date = cells[2].text.strip() if len(cells) > 2 else None
            return (
                project_name,
                project_link,
                neighborhood,
                document_type,
                document_link,
                date,
            )
        else:
            self.logger.warning(f"Row {row} has less than 3 cells")
            return None, None, None, None, None, None
    
    def create_safe_project_name(self, project_name: str) -> str:
        """
        Creates a safe project name for the project.
        """
        return "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in project_name
        ).strip().replace(" ", "_")
    
    def create_safe_document_type(self, document_type: str) -> str:
        """
        Creates a safe document type for the document.
        """
        return "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in document_type
        ).strip().replace(" ", "_")
    
    def create_project_id(self, project_name: str, document_type: str) -> str:
        """Create a project id for the project using sanitized names."""
        safe_name = self.create_safe_project_name(project_name)
        return f"{safe_name}"
    
    def get_project_metadata_path(self, project_name: str) -> str:
        """Get the path to the metadata.json file for a project."""
        safe_project_name = self.create_safe_project_name(project_name)
        project_folder = f"{self.pdf_base_directory()}/{safe_project_name}"
        return f"{project_folder}/metadata.json"
    
    def save_project_metadata(self, project_name: str, metadata: dict):
        """Save metadata for a single project to its metadata.json file."""
        safe_project_name = self.create_safe_project_name(project_name)
        project_folder = f"{self.pdf_base_directory()}/{safe_project_name}"
        
        # Create project folder if it doesn't exist
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
        
        metadata_path = self.get_project_metadata_path(project_name)
        
        # Load existing metadata if it exists
        existing_metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                existing_metadata = json.load(f)
        
        # Merge with new metadata (new data takes precedence)
        existing_metadata.update(metadata)
        
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(existing_metadata, f, indent=2)
    
    def load_project_metadata(self, project_name: str) -> dict:
        """Load metadata for a single project from its metadata.json file."""
        metadata_path = self.get_project_metadata_path(project_name)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {}

    def should_skip_download_from_gcs(self, project_name: str, document_link: str) -> bool:
        """
        Check if we should skip downloading by checking if the document_link already exists in GCS.
        Returns True if the metadata.json in GCS contains any document with the same document_link.

        Args:
            project_name: Name of the project
            document_link: Document link to check

        Returns:
            bool: True if download should be skipped (link already in GCS), False otherwise
        """
        # If GCS is not available, cannot skip
        if not self.gcp_storage:
            return False

        try:
            safe_project_name = self.create_safe_project_name(project_name)
            gcs_parent_dir = self.gcp_storage_parent_directory()

            # Check if metadata.json exists in GCS
            metadata_gcs_path = f"{gcs_parent_dir}/{safe_project_name}/metadata.json"
            metadata_blob = self.gcp_storage.bucket.blob(metadata_gcs_path)

            if not metadata_blob.exists():
                # Metadata doesn't exist in GCS, need to download
                return False

            # Download and parse metadata from GCS
            metadata_content = metadata_blob.download_as_text()
            gcs_metadata = json.loads(metadata_content)

            # Check if any document has the same document_link
            gcs_documents = gcs_metadata.get("documents", [])
            for doc in gcs_documents:
                gcs_doc_link = doc.get("document_link")
                if gcs_doc_link == document_link:
                    # Found matching document link, skip download
                    return True

            # Document link not found in GCS metadata, need to download
            return False

        except Exception as e:
            self.logger.warning(f"Error checking GCS for {project_name}: {e}")
            # On error, proceed with download to be safe
            return False

    def get_all_projects(self) -> list:
        """Get list of all project folders (project names) in the download directory."""
        base_dir = self.pdf_base_directory()
        if not os.path.exists(base_dir):
            return []
        
        projects = []
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            # Only include directories (project folders)
            if os.path.isdir(item_path):
                projects.append(item)
        return projects
    
    def generate_csv_from_json(self):
        """
        Generate metadata.csv from all individual JSON files for easy overview.
        Each document type becomes a row in the CSV.
        """
        project_folders = self.get_all_projects()
        all_rows = []
        
        for safe_project_name in project_folders:
            metadata_path = f"{self.pdf_base_directory()}/{safe_project_name}/metadata.json"
            if not os.path.exists(metadata_path):
                continue
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Get project-level fields
            project_fields = {
                'project_id': metadata.get('project_id'),
                'project_name': metadata.get('project_name'),
                'project_link': metadata.get('project_link'),
                'neighborhood': metadata.get('neighborhood'),
                'project_status': metadata.get('project_status'),
                'project_type': metadata.get('project_type'),
                'board_approval_date': metadata.get('board_approval_date'),
                'address': metadata.get('address'),
                'land_sq_feet': metadata.get('land_sq_feet'),
                'gross_floor_area': metadata.get('gross_floor_area'),
                'contact': metadata.get('contact'),
                'project_description': metadata.get('project_description'),
                'latitude': metadata.get('latitude'),
                'longitude': metadata.get('longitude'),
            }
            
            # Create a row for each document
            documents = metadata.get('documents', [])
            if documents:
                for doc in documents:
                    row = project_fields.copy()
                    row['document_type'] = doc.get('document_type')
                    row['document_link'] = doc.get('document_link')
                    row['date'] = doc.get('date')
                    # Add GCS path for the metadata.json
                    gcs_parent_dir = self.gcp_storage_parent_directory()
                    row['gcs_metadata_path'] = f"gs://{os.environ.get('GCS_BUCKET_NAME', 'YOUR_BUCKET')}/{gcs_parent_dir}/{safe_project_name}/metadata.json"
                    all_rows.append(row)
            else:
                # No documents, but still add the project
                row = project_fields.copy()
                row['document_type'] = None
                row['document_link'] = None
                row['date'] = None
                gcs_parent_dir = self.gcp_storage_parent_directory()
                row['gcs_metadata_path'] = f"gs://{os.environ.get('GCS_BUCKET_NAME', 'YOUR_BUCKET')}/{gcs_parent_dir}/{safe_project_name}/metadata.json"
                all_rows.append(row)
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(all_rows)
        
        # Reorder columns to put important ones first
        preferred_order = [
            'project_id', 'project_name', 'neighborhood', 'document_type',
            'project_status', 'project_type', 'address', 'document_link',
            'gcs_metadata_path', 'project_link', 'board_approval_date',
            'land_sq_feet', 'gross_floor_area', 'contact', 'date',
            'latitude', 'longitude', 'project_description'
        ]
        
        # Only include columns that exist
        columns = [col for col in preferred_order if col in df.columns]
        # Add any remaining columns not in preferred_order
        columns.extend([col for col in df.columns if col not in columns])
        df = df[columns]
        
        df.to_csv(self.csv_file(), index=False)
        self.logger.info(f"Generated CSV with {len(df)} rows from {len(project_folders)} projects: {self.csv_file()}")
        
        return df

    def collect_metadata_from_current_page(self, ALLOWED_DOCUMENT_KEYWORDS):
        """
        Collects data from the current page and saves to individual project metadata files.
        """
        rows = self.find_rows()
        for row in rows:
            (
                project_name,
                project_link,
                neighborhood,
                document_type,
                document_link,
                date,
            ) = self.parse_row(row)
            project_id = self.create_project_id(project_name)
            if not project_name:
                continue
            # Only process if document_type contains one of the allowed keywords
            if any(keyword in document_type for keyword in ALLOWED_DOCUMENT_KEYWORDS):
                # Load existing metadata for this project
                metadata = self.load_project_metadata(project_name)
                
                # Add document info to the documents list
                if "documents" not in metadata:
                    metadata["documents"] = []
                
                # Check if this document already exists (by document_type)
                doc_exists = False
                for doc in metadata["documents"]:
                    if doc.get("document_type") == document_type:
                        # Update existing document
                        doc.update({
                            "document_link": document_link,
                            "date": date,
                        })
                        doc_exists = True
                        break
                
                if not doc_exists:
                    # Add new document
                    metadata["documents"].append({
                        "document_type": document_type,
                        "document_link": document_link,
                        "date": date,
                    })
                
                # Update project-level metadata
                metadata.update({
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_link": project_link,
                    "neighborhood": neighborhood,
                })
                
                # Save metadata to JSON file
                self.save_project_metadata(project_name, metadata)

    def collect_document_links(self, test_mode: bool = False):
        """
        Collects the document links from the current page.

        Args:
            test_mode: If True, only collect first 2-3 pages for testing.
        """
        driver = self.selenium_util.driver
        self.selenium_util.driver.get(self.resource_url())
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[@role='grid']/tbody"))
        )
        # Find pagination info: "1-25 of 8800"
        pagination_data = driver.find_element(
            By.XPATH, "//p[contains(@class, 'MuiTablePagination-caption')]"
        )
        pagination_text = pagination_data.text  # e.g., "1-25 of 8800"
        self.logger.info(f"Pagination text: {pagination_text}")

        # Parse "1-25 of 8800" format
        parts = pagination_text.split(" of ")
        range_part = parts[0]  # "1-25"
        total_element_cnt = int(parts[1])  # 8800

        # Extract page size from range (e.g., "1-25" -> page size is 25)
        range_nums = range_part.split("-")
        start_idx = int(range_nums[0])  # 1
        end_idx = int(range_nums[1])  # 25
        page_element_cnt = end_idx - start_idx + 1  # 25

        # Calculate total pages
        total_page_cnt = (total_element_cnt + page_element_cnt - 1) // page_element_cnt
        self.logger.info(
            f"Total elements: {total_element_cnt}, Page size: {page_element_cnt}, Total pages: {total_page_cnt}"
        )

        last_seen_first_row_text = None
        page_number = 1
        max_test_pages = 1  # In test mode, only process 1 page

        while True:
            # Get the text of the first row before scraping, for later comparison
            tbody = driver.find_element(By.XPATH, "//table[@role='grid']/tbody")
            first_row = tbody.find_element(By.TAG_NAME, "tr")
            current_first_row_text = first_row.text

            self.collect_metadata_from_current_page(self.ALLOWED_DOCUMENT_KEYWORDS())

            # In test mode, stop after a few pages
            if test_mode and page_number >= max_test_pages:
                self.logger.info(f"TEST MODE: Stopping after {max_test_pages} pages")
                break

            # Try to find 'Next page' button and check if enabled
            try:
                next_page_btn = driver.find_element(
                    By.XPATH, "//button[@title='Next page']"
                )
            except NoSuchElementException:
                # No next page button found, break the loop
                break

            classes = next_page_btn.get_attribute("class") or ""
            if "Mui-disabled" in classes:
                break  # if disabled, we're on the last page

            # Store the current first row text before clicking
            last_seen_first_row_text = current_first_row_text

            # Go to the next page
            next_page_btn.click()
            page_number += 1
            self.logger.info(f"Collecting page {page_number} of {total_page_cnt}")

            # Wait for the first row text to actually change, confirming page navigation
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(
                    By.XPATH, "//table[@role='grid']/tbody/tr"
                ).text
                != last_seen_first_row_text
            )

            # Wait for the loading indicator to disappear from the first row
            WebDriverWait(driver, 10).until(
                lambda d: "loading"
                not in d.find_element(
                    By.XPATH, "//table[@role='grid']/tbody/tr"
                ).text.lower()
            )

        self.logger.info(f"Document links collection completed. Metadata saved to individual JSON files.")
        
        # Generate CSV from JSON files for easy overview
        self.generate_csv_from_json()

    def collect_metadata_from_projects(self):
        """
        Collects project metadata from unique project names found in JSON files.
        First searches for the project using project_link to find project status/type,
        then navigates to detailed project page to extract metadata.
        """
        driver = self.selenium_util.driver

        # Get all project folders
        project_folders = self.get_all_projects()
        total_unique = len(project_folders)

        self.logger.info(f"Found {total_unique} unique projects")

        for count, safe_project_name in enumerate(project_folders, 1):
            # Load existing metadata
            metadata_path = f"{self.pdf_base_directory()}/{safe_project_name}/metadata.json"
            if not os.path.exists(metadata_path):
                self.logger.warning(f"No metadata.json found for {safe_project_name}, skipping")
                continue
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            project_name = metadata.get("project_name")
            project_link = metadata.get("project_link")
            
            if not project_name or not project_link:
                self.logger.warning(f"Missing project_name or project_link in {safe_project_name}, skipping")
                continue
            
            self.logger.info(f"Processing {count}/{total_unique}: {project_name}")
            self.logger.info(f"Link: {project_link}")

            try:
                # Step 1: Navigate to project_link (search results page)
                driver.get(project_link)

                # Wait for search results
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "projectTableWrapper")
                    )
                )

                # Parse search results
                soup = BeautifulSoup(driver.page_source, "html.parser")
                table_wrappers = soup.find_all("div", class_="projectTableWrapper")

                project_detail_link = None
                project_metadata = {}

                # Step 2: Find tables with "Project Type" (not "Plan Type")
                for wrapper in table_wrappers:
                    table = wrapper.find("table", class_="devprojectTable")
                    if not table:
                        continue

                    # Check if this table has "Project Type" header
                    headers = table.find_all("th")
                    has_project_type = False

                    for header in headers:
                        header_text = header.get_text(strip=True)
                        if "Project Type" in header_text:
                            has_project_type = True
                            break

                    if not has_project_type and len(table_wrappers) > 1:
                        continue  # Skip tables with "Plan Type"

                    # Extract project status, type, and approval date from headers
                    for header in headers:
                        h2 = header.find("h2")
                        if h2:
                            main_text = h2.contents[0].strip() if h2.contents else ""
                            sub_header = h2.find("span", class_="tableSubHeader")
                            sub_text = (
                                sub_header.get_text(strip=True) if sub_header else ""
                            )

                            if sub_text == "Project Status":
                                project_metadata["project_status"] = main_text
                            elif sub_text == "Project Type":
                                project_metadata["project_type"] = main_text
                            elif sub_text == "Board Approval Date":
                                project_metadata["board_approval_date"] = main_text
                            elif sub_text == "Plan Status":
                                project_metadata["project_status"] = main_text
                            elif sub_text == "Plan Type":
                                project_metadata["project_type"] = main_text

                    # Get the project detail link from caption
                    caption = table.find("caption")
                    if caption:
                        link = caption.find("a")
                        if link and link.get("href"):
                            project_detail_link = (
                                "https://www.bostonplans.org" + link.get("href")
                            )
                            break  # Found a valid project, stop looking

                # Step 3: Navigate to project detail page if found
                if project_detail_link:
                    self.logger.info(
                        f"Found project detail page: {project_detail_link}"
                    )
                    driver.get(project_detail_link)

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "projATimelineDetails")
                        )
                    )

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    details_div = soup.find("div", class_="projATimelineDetails")

                    if details_div:
                        detail_containers = details_div.find_all(
                            "div", class_="detailsContainer"
                        )

                        for container in detail_containers:
                            header = container.find("div", class_="bpdaPrjHeader")
                            detail = container.find("div", class_="bpdaPrjDetails")

                            if header and detail:
                                header_text = header.get_text(strip=True)
                                detail_text = detail.get_text(strip=True)

                                if header_text == "Address":
                                    project_metadata["address"] = detail_text
                                    latitude, longitude = GeoLocater().geocode(detail_text \
                                        + ", " \
                                        + self.city() \
                                        + ", " \
                                        + "MA"
                                    )
                                    # This is a necessary step for the label studio
                                    project_metadata["latitude"] = latitude
                                    project_metadata["longitude"] = longitude
                                elif header_text == "Land Sq. Feet":
                                    project_metadata["land_sq_feet"] = detail_text
                                elif header_text == "Gross Floor Area":
                                    project_metadata["gross_floor_area"] = detail_text
                                elif header_text == "Contact":
                                    project_metadata["contact"] = detail_text
                                elif header_text == "Project Description":
                                    desc_div = container.find(
                                        "div",
                                        style=lambda x: x and "font-size:20px" in x,
                                    )
                                    if desc_div:
                                        project_metadata["project_description"] = (
                                            desc_div.get_text(strip=True)
                                        )
                                    else:
                                        project_metadata["project_description"] = (
                                            detail_text
                                        )

                # Save the metadata back to the project's JSON file
                self.save_project_metadata(project_name, project_metadata)
                self.logger.info(f"Successfully collected and saved metadata for {project_name}")

            except Exception as e:
                self.logger.error(f"Error collecting metadata for {project_name}: {e}")
                continue

        self.logger.info(f"Metadata collection completed for {total_unique} projects")
        
        # Regenerate CSV from updated JSON files
        self.generate_csv_from_json()

    def collect_pdf_from_document_link(self, test_mode: bool = False):
        """
        Downloads PDFs from document links (Box shared links).
        Creates folder structure: downloads/development_plans/Boston/[project_name]/[document_type].pdf
        Each project gets its own folder, and files are named by document type.

        Args:
            test_mode: If True, only download first 5 documents for testing.
        """
        import requests
        import shutil

        # Create base PDF directory
        if not os.path.exists(self.pdf_base_directory()):
            os.makedirs(self.pdf_base_directory())

        driver = self.selenium_util.driver

        # Get all project folders and collect documents
        project_folders = self.get_all_projects()
        documents_to_download = []

        for safe_project_name in project_folders:
            metadata_path = f"{self.pdf_base_directory()}/{safe_project_name}/metadata.json"
            if not os.path.exists(metadata_path):
                continue
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            project_name = metadata.get("project_name")
            if not project_name:
                continue
            
            # Get all documents for this project
            documents = metadata.get("documents", [])
            for doc in documents:
                document_type = doc.get("document_type")
                document_link = doc.get("document_link")
                
                if document_link:
                    documents_to_download.append({
                        "project_name": project_name,
                        "document_type": document_type,
                        "document_link": document_link
                    })

        # Limit to 5 documents in test mode
        if test_mode:
            documents_to_download = documents_to_download[:5]
            self.logger.info(f"TEST MODE: Limiting to 5 documents")

        total_docs = len(documents_to_download)
        self.logger.info(f"Found {total_docs} documents to download")

        for count, doc_info in enumerate(documents_to_download, 1):
            project_name = doc_info["project_name"]
            document_type = doc_info["document_type"]
            document_link = doc_info["document_link"]

            # Sanitize project name for folder name
            safe_project_name = self.create_safe_project_name(project_name)

            # Sanitize document type for filename
            safe_document_type = self.create_safe_document_type(document_type)

            # Create project-specific folder
            project_folder = f"{self.pdf_base_directory()}/{safe_project_name}"
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)

            # Create full path with document type as filename
            pdf_path = f"{project_folder}/{safe_document_type}.pdf"

            # Skip if document link already exists in GCS
            if self.should_skip_download_from_gcs(project_name, document_link):
                self.logger.info(
                    f"Skipping {count}/{total_docs}: {project_name} - {document_type} (already in GCS with same link)"
                )
                continue

            self.logger.info(
                f"Downloading {count}/{total_docs}: {project_name} - {document_type}"
            )
            self.logger.info(f"Link: {document_link}")

            try:
                # Use requests library to download directly from Box shared link
                # Box shared links work with direct requests if we follow redirects
                if "box.com" in document_link:
                    # Try direct download using requests
                    try:
                        response = requests.get(
                            document_link, allow_redirects=True, timeout=30
                        )

                        # Check if we got a PDF
                        if (
                            response.status_code == 200
                            and "application/pdf"
                            in response.headers.get("Content-Type", "")
                        ):
                            with open(pdf_path, "wb") as f:
                                f.write(response.content)
                            self.logger.info(
                                f"Successfully downloaded {project_name} - {document_type} using direct request"
                            )
                            continue
                    except Exception as e:
                        self.logger.warning(
                            f"Direct download failed, trying Selenium approach: {e}"
                        )

                # Fallback: Use Selenium to navigate and download
                driver.get(document_link)

                # Wait for the page to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Try to find and click the download button
                download_button = None
                selectors_to_try = [
                    (By.CSS_SELECTOR, "button[data-resin-target='download']"),
                    (By.XPATH, "//button[contains(., 'Download')]"),
                    (By.CSS_SELECTOR, "button[aria-label*='Download']"),
                    (By.CSS_SELECTOR, "a.btn-download"),
                    (By.XPATH, "//a[contains(@class, 'download')]"),
                ]

                for by, selector in selectors_to_try:
                    try:
                        download_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        break
                    except:
                        continue

                if download_button:
                    # Get list of files in download directory before clicking download
                    download_dir = self.download_directory()
                    existing_files = set()
                    for root, _dirs, files in os.walk(download_dir):
                        for f in files:
                            existing_files.add(os.path.join(root, f))

                    download_button.click()
                    self.logger.info(
                        f"Clicked download button for {project_name} - {document_type}"
                    )

                    # Wait for download to complete
                    import time
                    max_wait = 60  # Increased timeout for larger files
                    download_complete = False

                    for i in range(max_wait):
                        time.sleep(1)
                        current_files = set()
                        for root, _dirs, files in os.walk(download_dir):
                            for f in files:
                                current_files.add(os.path.join(root, f))

                        new_files = current_files - existing_files

                        # Check for new PDF files (and ensure no .crdownload or .tmp files)
                        pdf_files = [f for f in new_files if f.endswith('.pdf')]
                        temp_files = [f for f in new_files if f.endswith(('.crdownload', '.tmp', '.part'))]

                        if pdf_files and not temp_files:
                            # Found a completed PDF download
                            downloaded_file = pdf_files[0]
                            shutil.move(downloaded_file, pdf_path)
                            self.logger.info(
                                f"Successfully downloaded and moved PDF to {pdf_path}"
                            )
                            download_complete = True
                            break

                        if i % 10 == 0 and i > 0:
                            self.logger.info(f"Waiting for download to complete... ({i}s)")

                    if not download_complete:
                        self.logger.warning(
                            f"Download timeout for {project_name} - {document_type}"
                        )
                else:
                    self.logger.warning(
                        f"Could not find download button for {project_name} - {document_type}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Error downloading PDF for {project_name} - {document_type}: {e}"
                )
                continue

        self.logger.info(f"PDF download process completed")

    def collect(self, test_mode: bool = False):
        """
        Collects all allowed development plan documents from Boston's BPDA records library,
        handling pagination, and saves the results as individual JSON files per project.
        Also generates a CSV file for easy overview of all projects.

        Args:
            test_mode: If True, only process first 2-3 pages to test GCP upload functionality.
        """

        try:
            if not os.path.exists(self.download_directory()):
                os.makedirs(self.download_directory())
            
            # Step 1: Collect document links from the website
            logger.info("Collecting document links" + (" (TEST MODE - limited pages)" if test_mode else ""))
            self.collect_document_links(test_mode=test_mode)
            
            # Step 2: Collect detailed metadata for each project
            logger.info("Collecting metadata from projects")
            self.collect_metadata_from_projects()
            
            # Step 3: Download PDFs
            logger.info("Collecting PDFs from document links. This will take a while...")
            self.collect_pdf_from_document_link(test_mode=test_mode)
            
            # Step 4: Generate CSV from all JSON files
            logger.info("Generating final CSV from all JSON files...")
            self.generate_csv_from_json()
            
            # Step 5: Upload to GCS
            self.upload_to_gcs()
        except Exception as e:
            raise Exception(f"Error during collection: {e}")

    def upload_to_gcs(self):
        """
        Upload the data to GCS, avoiding duplicate uploads by comparing file hashes.

        Files are uploaded to: {gcp_storage_parent_directory}/{safe_project_name}/{filename}
        For example: development_plans/boston/Project_Name/Document_Type.pdf
        """
        if not self.gcp_storage:
            raise ValueError("GCS connection not available. Ensure GCS_BUCKET_NAME and GCP_PROJECT environment variables are set.")

        download_dir = self.download_directory()
        gcs_parent_dir = self.gcp_storage_parent_directory()
        bucket_name = os.environ.get("GCS_BUCKET_NAME")

        uploaded_count = 0
        skipped_count = 0

        # List local files to upload (pdf, csv, etc.)
        for root, _dirs, files in os.walk(download_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                # Create GCS path relative to download directory
                rel_path = os.path.relpath(local_path, start=download_dir)
                # Normalize path separators for GCS (use forward slashes)
                rel_path = rel_path.replace(os.sep, '/')

                # Prepend the GCS parent directory
                gcs_blob_path = f"{gcs_parent_dir}/{rel_path}"

                try:
                    # Check if blob exists in GCS
                    blob = self.gcp_storage.bucket.blob(gcs_blob_path)
                    if blob.exists():
                        # Reload blob metadata to get the MD5 hash
                        blob.reload()
                        gcs_md5 = blob.md5_hash  # base64-encoded

                        # Compare hashes using FileHashChecker utility
                        if FileHashChecker.compare_file_with_gcs_hash(local_path, gcs_md5):
                            self.logger.info(
                                f"Skipping upload for {gcs_blob_path} (already uploaded, hash matches)"
                            )
                            skipped_count += 1
                            continue  # skip upload

                    # Upload file using GCPStorage utility
                    self.gcp_storage.upload_file(local_path, gcs_blob_path)
                    self.logger.info(f"Uploaded {gcs_blob_path} to GCS bucket {bucket_name}")
                    uploaded_count += 1

                except Exception as e:
                    self.logger.error(f"Error uploading {gcs_blob_path}: {e}")
                    continue

        self.logger.info(
            f"Upload complete: {uploaded_count} files uploaded, {skipped_count} files skipped (duplicates)."
        )
