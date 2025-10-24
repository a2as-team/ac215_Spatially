import logging
from utils.selenium import SeleniumUtil
import pandas as pd
import os
import time
from .base import BaseDevelopmentPlansCollector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

# Set up the logger for this module at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
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
    def download_directory(cls) -> str:
        # Return absolute path of download directory
        return "downloads/development_plans/boston"

    @classmethod
    def pdf_base_directory(cls) -> str:
        return f"{cls.download_directory()}/pdfs"

    @classmethod
    def csv_file(cls) -> str:
        return f"{cls.download_directory()}/data.csv"

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
        self.selenium_util = SeleniumUtil(headless=True)
        self.all_results = []
        self.result_df = None
        self.logger = logger  # Use the module-level logger

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

    def collect_data_from_current_page(self, ALLOWED_DOCUMENT_KEYWORDS):
        """
        Collects data from the current page and appends allowed results to self.all_results.
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
            if not project_name:
                continue
            # Only append if document_type contains one of the allowed keywords
            if any(keyword in document_type for keyword in ALLOWED_DOCUMENT_KEYWORDS):
                self.all_results.append(
                    {
                        "project_name": project_name,
                        "project_link": project_link,
                        "neighborhood": neighborhood,
                        "document_type": document_type,
                        "document_link": document_link,
                        "date": date,
                    }
                )

    def collect_document_links(self):
        """
        Collects the document links from the current page.
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
        while True:
            # Get the text of the first row before scraping, for later comparison
            tbody = driver.find_element(By.XPATH, "//table[@role='grid']/tbody")
            first_row = tbody.find_element(By.TAG_NAME, "tr")
            current_first_row_text = first_row.text

            self.collect_data_from_current_page(self.ALLOWED_DOCUMENT_KEYWORDS)

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

        # Save results to CSV
        self.result_df = pd.DataFrame(self.all_results)
        if not os.path.exists(self.download_directory()):
            os.makedirs(self.download_directory())
        self.result_df.to_csv(self.csv_file(), index=False)

    def collect_metadata_from_csv(self):
        """
        Collects project metadata from unique project names in the CSV file.
        First searches for the project using project_link to find project status/type,
        then navigates to detailed project page to extract metadata.
        """
        if self.result_df is None:
            self.result_df = pd.read_csv(self.csv_file())

        df = self.result_df

        # Initialize new columns if they don't exist
        new_columns = [
            "project_status",
            "project_type",
            "board_approval_date",
            "address",
            "land_sq_feet",
            "gross_floor_area",
            "contact",
            "project_description",
        ]
        for col in new_columns:
            if col not in df.columns:
                df[col] = None

        driver = self.selenium_util.driver

        # Get unique project names and their first occurrence link
        unique_projects = df.groupby("project_name").first()["project_link"].to_dict()
        total_unique = len(unique_projects)

        self.logger.info(
            f"Found {total_unique} unique projects out of {len(df)} total rows"
        )

        # Create a dictionary to store metadata for each unique project
        metadata_cache = {}

        for count, (project_name, project_link) in enumerate(
            unique_projects.items(), 1
        ):
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

                # Cache the metadata for this project
                metadata_cache[project_name] = project_metadata
                self.logger.info(f"Successfully collected metadata for {project_name}")

            except Exception as e:
                self.logger.error(f"Error collecting metadata for {project_name}: {e}")
                continue

        # Apply cached metadata to all matching rows in the dataframe
        self.logger.info("Applying metadata to all rows...")
        for idx, row in df.iterrows():
            project_name = row["project_name"]
            if project_name in metadata_cache:
                for key, value in metadata_cache[project_name].items():
                    df.at[idx, key] = value

        # Save updated dataframe
        self.result_df = df
        df.to_csv(self.csv_file(), index=False)
        self.logger.info(f"Saved metadata to {self.csv_file()}")

    def collect_pdf_from_document_link(self):
        """
        Downloads PDFs from document links (Box shared links).
        Creates folder structure: downloads/development_plans/Boston/pdfs/[project_name]/[document_type].pdf
        Each project gets its own folder, and files are named by document type.
        """
        import requests
        import shutil
        import glob

        if self.result_df is None:
            self.result_df = pd.read_csv(self.csv_file())

        df = self.result_df

        # Create base PDF directory
        if not os.path.exists(self.pdf_base_directory()):
            os.makedirs(self.pdf_base_directory())

        driver = self.selenium_util.driver

        # Get unique document links to avoid downloading duplicates (with project_name and document_type)
        unique_docs = df[df["document_link"].notna()][
            ["project_name", "document_type", "document_link"]
        ].drop_duplicates(subset=["document_link"])
        total_docs = len(unique_docs)

        self.logger.info(f"Found {total_docs} unique documents to download")

        for count, (idx, row) in enumerate(unique_docs.iterrows(), 1):
            project_name = row["project_name"]
            document_type = row["document_type"]
            document_link = row["document_link"]

            # Sanitize project name for folder name
            safe_project_name = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_" for c in project_name
            )
            safe_project_name = safe_project_name.strip().replace(" ", "_")

            # Sanitize document type for filename
            safe_doc_type = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_" for c in document_type
            )
            safe_doc_type = safe_doc_type.strip().replace(" ", "_")

            # Create project-specific folder
            project_folder = f"{self.pdf_base_directory()}/{safe_project_name}"
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)

            # Create full path with document type as filename
            pdf_path = f"{project_folder}/{safe_doc_type}.pdf"

            # Skip if already downloaded
            if os.path.exists(pdf_path):
                self.logger.info(
                    f"Skipping {count}/{total_docs}: {project_name} - {document_type} (already downloaded)"
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
                    download_button.click()
                    self.logger.info(
                        f"Clicked download button for {project_name} - {document_type}"
                    )

                    # Wait for download to appear in downloads folder
                    import time

                    time.sleep(3)

                    # Check default Downloads folder for the file
                    downloads_folder = os.path.expanduser("~/Downloads")

                    # Wait for download to complete (look for .pdf files, not .crdownload)
                    max_wait = 30
                    for _ in range(max_wait):
                        pdf_files = glob.glob(f"{downloads_folder}/*.pdf")
                        if pdf_files:
                            # Get the most recent PDF
                            latest_pdf = max(pdf_files, key=os.path.getctime)
                            # Check if it was created in the last 10 seconds
                            if os.path.getctime(latest_pdf) > (time.time() - 10):
                                shutil.move(latest_pdf, pdf_path)
                                self.logger.info(
                                    f"Successfully moved downloaded PDF to {pdf_path}"
                                )
                                break
                        time.sleep(1)
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

    def collect(self):
        """
        Collects all allowed development plan documents from Boston's BPDA records library,
        handling pagination, and saves the results as a CSV.
        """

        try:
            if not os.path.exists(self.download_directory()):
                os.makedirs(self.download_directory())
            if not os.path.exists(self.csv_file()):
                self.collect_document_links()
            self.collect_metadata_from_csv()
            self.collect_pdf_from_document_link()
        except Exception as e:
            raise Exception(f"Error during collection: {e}")
