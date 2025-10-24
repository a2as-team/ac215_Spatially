"""Base class for zoning ordinance data collectors."""

from abc import ABC, abstractmethod
import os
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys


from collector import BaseCollector

logger = logging.getLogger(__name__)


class ZoningOrdinanceBaseCollector(BaseCollector, ABC):
    """
    Base class for zoning ordinance collectors that use Selenium WebDriver.

    Provides common functionality for:
    - Chrome WebDriver setup with download configuration
    - Headless mode support
    - Download directory management
    - CDP command setup for downloads
    """

    def __init__(self, headless: bool = True, download_dir: str = None):
        """
        Initialize the zoning ordinance collector.

        Args:
            headless: Whether to run Chrome in headless mode
            download_dir: Directory to save downloaded files
        """
        super().__init__()
        self.headless = headless
        self.download_dir = self._setup_download_dir(download_dir)
        self.driver = None

    @abstractmethod
    def _get_default_download_dir(self) -> Path:
        """
        Get the default download directory for this collector.

        Returns:
            Path to the default download directory
        """
        pass

    def _setup_download_dir(self, download_dir: str = None) -> Path:
        """
        Set up and create the download directory.

        Args:
            download_dir: Optional custom download directory

        Returns:
            Resolved Path object for the download directory
        """
        if download_dir is None:
            dl_path = self._get_default_download_dir()
        else:
            dl_path = Path(download_dir)

        dl_path.mkdir(parents=True, exist_ok=True)
        return dl_path.resolve()

    def _setup_driver(self):
        """
        Initialize Chrome WebDriver with download-friendly options.

        Sets up:
        - Headless mode (if enabled)
        - Download directory preferences
        - CDP commands for download behavior
        - Anti-detection measures
        """
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # Common Chrome options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Enhanced anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Additional anti-detection for Cloudflare and similar
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process"
        )
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Set download preferences
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info(f"Chrome WebDriver initialized (headless={self.headless})")

        # Set navigator.webdriver to undefined to avoid detection
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
                },
            )
        except Exception as e:
            logger.warning(f"Could not set webdriver property: {e}")

        # Enable automatic downloads in headless mode via DevTools
        try:
            self.driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(self.download_dir)},
            )
            logger.info(f"Set download path via CDP: {self.download_dir}")
        except Exception as e:
            logger.warning(f"Could not set download behavior via CDP: {e}")
            # Best-effort; not all driver versions support this

    def _cleanup_driver(self):
        """Close the WebDriver if it exists."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

    @abstractmethod
    def collect(self) -> dict:
        """
        Collect zoning ordinance data.

        Returns:
            Dictionary with collection results
        """
        pass

    @abstractmethod
    def validate(self, data: dict) -> bool:
        """
        Validate the collected data.

        Args:
            data: The collection results to validate

        Returns:
            True if validation passes, False otherwise
        """
        pass


__all__ = ["ZoningOrdinanceBaseCollector", "BaseCollector"]
