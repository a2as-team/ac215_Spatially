import sys
import unittest
from pathlib import Path

# Add parent directory to path to import collector modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.zba.boston import BostonZBACollector


class TestBostonZBACollector(unittest.TestCase):
    """Test cases for Boston ZBA video URL collector."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used by all test methods."""
        cls.collector = BostonZBACollector()

    def test_collect_video_urls_returns_dict(self):
        """Test that collect_video_urls returns a dictionary."""
        video_data = self.collector.collect_video_urls()
        self.assertIsInstance(video_data, dict)

    def test_collect_video_urls_not_empty(self):
        """Test that collect_video_urls finds at least one video."""
        video_data = self.collector.collect_video_urls()
        self.assertGreater(len(video_data), 0)

    def test_video_data_structure(self):
        """Test that video data has correct structure (dates -> URLs)."""
        video_data = self.collector.collect_video_urls()

        for date, urls in video_data.items():
            # Date should be a string
            self.assertIsInstance(date, str)

            # URLs can be either a single string or a list of strings
            if isinstance(urls, list):
                for url in urls:
                    self.assertIsInstance(url, str)
                    self.assertTrue(url.startswith("https://www.youtube.com/watch?v="))
            else:
                self.assertIsInstance(urls, str)
                self.assertTrue(urls.startswith("https://www.youtube.com/watch?v="))

    def test_date_format(self):
        """Test that dates are in expected format (Month Day, Year)."""
        import re

        video_data = self.collector.collect_video_urls()
        date_pattern = re.compile(r"^[A-Z][a-z]+\s+\d{1,2},\s+\d{4}$")

        for date in video_data.keys():
            self.assertIsNotNone(
                date_pattern.match(date), f"Date '{date}' doesn't match expected format"
            )


if __name__ == "__main__":
    unittest.main()
