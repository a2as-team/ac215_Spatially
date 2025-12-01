import sys
import unittest
from pathlib import Path

# Add parent directory to path to import collector modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from development_plans.boston import BostonDevelopmentPlansCollector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestBostonConnection(unittest.TestCase):
    """Test if Boston development plans website is accessible and parseable."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.collector = BostonDevelopmentPlansCollector()

    @classmethod
    def tearDownClass(cls):
        """Clean up selenium driver."""
        if hasattr(cls.collector, "selenium_util"):
            cls.collector.selenium_util.quit()

    def test_website_connection_and_table_exists(self):
        """Test that we can connect to Boston website and find the table."""
        driver = self.collector.selenium_util.driver
        driver.get(self.collector.resource_url())

        # Wait for table to load - this is the critical part
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table[@role='grid']/tbody")
                )
            )
            # If we get here, connection works and table exists
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Failed to load Boston development plans table: {e}")

    def test_can_find_rows_in_table(self):
        """Test that we can find rows in the table."""
        driver = self.collector.selenium_util.driver
        driver.get(self.collector.resource_url())

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@role='grid']/tbody"))
        )

        rows = self.collector.find_rows()
        self.assertGreater(len(rows), 0, "No rows found in table")
        print(f"Found {len(rows)} rows in the table")

    def test_can_parse_first_row(self):
        """Test that we can parse the first row successfully."""
        driver = self.collector.selenium_util.driver
        driver.get(self.collector.resource_url())

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@role='grid']/tbody"))
        )

        rows = self.collector.find_rows()
        self.assertGreater(len(rows), 0)

        # Try to parse the first row
        first_row = rows[0]
        project_name, project_link, neighborhood, document_type, document_link, date = (
            self.collector.parse_row(first_row)
        )

        # Verify we got some data
        self.assertIsNotNone(project_name, "Project name should not be None")
        self.assertIsNotNone(project_link, "Project link should not be None")
        print(f"Successfully parsed: {project_name} - {neighborhood} - {document_type}")

    def test_collect_from_first_page(self):
        """Test that we can collect data from the first page."""
        import json
        import os
        import shutil

        # Clean up any existing test data
        base_dir = self.collector.pdf_base_directory()
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.makedirs(base_dir)

        driver = self.collector.selenium_util.driver
        driver.get(self.collector.resource_url())

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@role='grid']/tbody"))
        )

        # First, check if there are any matching documents on the first page
        rows = self.collector.find_rows()
        self.assertGreater(len(rows), 0, "Should have rows in table")

        # Count how many rows match the allowed keywords
        matching_count = 0
        for row in rows:
            _, _, _, document_type, _, _ = self.collector.parse_row(row)
            if document_type and any(keyword in document_type for keyword in self.collector.ALLOWED_DOCUMENT_KEYWORDS()):
                matching_count += 1

        print(f"Found {matching_count} matching documents out of {len(rows)} total rows")

        # Collect data from first page
        self.collector.collect_metadata_from_current_page(
            self.collector.ALLOWED_DOCUMENT_KEYWORDS()
        )

        # Check that download directory exists
        self.assertTrue(os.path.exists(base_dir), "Download directory should exist")

        # Get all project folders (directories in base_dir)
        project_folders = [d for d in os.listdir(base_dir)
                          if os.path.isdir(os.path.join(base_dir, d))]

        # The number of project folders should be at most the number of matching documents
        # (multiple documents can belong to the same project)
        self.assertGreater(
            len(project_folders),
            0,
            "Should collect at least one project folder"
        )
        self.assertLessEqual(
            len(project_folders),
            matching_count,
            f"Project folders ({len(project_folders)}) should not exceed matching documents ({matching_count})",
        )

        # Only verify metadata structure if we found matching documents
        if matching_count > 0:
            print(f"Collected {len(project_folders)} projects with matching documents")

            # Verify structure of first project's metadata.json
            first_project_folder = project_folders[0]
            metadata_path = os.path.join(base_dir, first_project_folder, "metadata.json")
            self.assertTrue(os.path.exists(metadata_path), "metadata.json should exist")

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            self.assertIn("project_name", metadata)
            self.assertIn("project_link", metadata)
            self.assertIn("neighborhood", metadata)
            self.assertIn("documents", metadata)
            self.assertGreater(len(metadata["documents"]), 0, "Should have at least one document")

            # Verify document structure
            first_doc = metadata["documents"][0]
            self.assertIn("document_type", first_doc)
        else:
            print("No matching documents found on first page - test passed (collector working correctly)")


if __name__ == "__main__":
    unittest.main()
