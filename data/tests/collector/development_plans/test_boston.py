import sys
import unittest
from pathlib import Path

# Add parent directory to path to import collector modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from collector.development_plans.boston import BostonDevelopmentPlansCollector
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
        driver = self.collector.selenium_util.driver
        driver.get(self.collector.resource_url())

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table[@role='grid']/tbody"))
        )

        # Collect data from first page
        self.collector.collect_data_from_current_page(
            self.collector.ALLOWED_DOCUMENT_KEYWORDS()
        )

        # Should have collected at least some results
        self.assertGreater(
            len(self.collector.all_results),
            0,
            "Should collect at least one matching document from first page",
        )

        print(f"Collected {len(self.collector.all_results)} matching documents")

        # Verify structure
        first_result = self.collector.all_results[0]
        self.assertIn("project_name", first_result)
        self.assertIn("project_link", first_result)
        self.assertIn("neighborhood", first_result)
        self.assertIn("document_type", first_result)


if __name__ == "__main__":
    unittest.main()
