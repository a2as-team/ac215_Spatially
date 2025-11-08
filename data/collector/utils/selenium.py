from selenium import webdriver
import logging
import random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SeleniumUtil:
    """
    Utility class to manage a single Selenium WebDriver instance with anti-detection configurations.
    Use the 'driver' property to access the current WebDriver from anywhere this util is used.
    """

    # List of realistic user agents to rotate through
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, headless: bool = True, logger: logging.Logger = None, download_dir: str = None):
        self.headless = headless
        self.logger = logger or logging.getLogger(__name__)
        self.download_dir = download_dir
        self._driver = None
        self.current_user_agent = None

    @property
    def driver(self):
        """
        Returns a managed driver instance, initializing if not already created.
        """
        if self._driver is None:
            self.initialize_driver()
        return self._driver

    def initialize_driver(self):
        # Select a random user agent
        self.current_user_agent = random.choice(self.USER_AGENTS)
        self.logger.info(f"Using User-Agent: {self.current_user_agent[:50]}...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process"
        )
        chrome_options.add_argument(f"--user-agent={self.current_user_agent}")
        # Enable kiosk printing to auto-print without dialog
        chrome_options.add_argument("--kiosk-printing")

        # Configure download directory if specified
        if self.download_dir:
            import os
            import json
            os.makedirs(self.download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,  # Disable Chrome's PDF viewer
                "safebrowsing.enabled": True,
                "printing.print_preview_sticky_settings.appState": json.dumps({
                    "recentDestinations": [{
                        "id": "Save as PDF",
                        "origin": "local",
                        "account": "",
                    }],
                    "selectedDestinationId": "Save as PDF",
                    "version": 2,
                    "isHeaderFooterEnabled": False,
                    "isLandscapeEnabled": False,
                    "isCssBackgroundEnabled": True,
                })
            }
            chrome_options.add_experimental_option("prefs", prefs)

        # ChromeDriver is installed via base image (infologistix/docker-selenium-python)
        self._driver = webdriver.Chrome(options=chrome_options)
        self.logger.info(f"Chrome WebDriver initialized (headless={self.headless})")

        # Enable downloads in headless mode
        if self.headless and self.download_dir:
            try:
                self._driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {
                        "behavior": "allow",
                        "downloadPath": self.download_dir,
                    }
                )
                self.logger.info(f"Enabled downloads to: {self.download_dir}")
            except Exception as e:
                self.logger.warning(f"Could not enable downloads: {e}")

        # Anti-detection: hide webdriver property
        try:
            self._driver.execute_cdp_cmd(
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
            self.logger.warning(f"Could not set webdriver property: {e}")
        return self._driver

    def find_element(self, by, value, timeout: int = 10):
        """
        Finds an element on the page.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def find_elements(self, by, value, timeout: int = 10):
        """
        Finds elements on the page.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )

    def click_element(self, by, value, timeout: int = 10):
        """
        Clicks an element on the page.
        """
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
    
    def wait_for_element(self, by, value, timeout: int = 10):
        """
        Waits for an element to be present and visible.
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def reinitialize_with_new_headers(self):
        """
        Reinitialize the driver with a new random user agent.
        Useful for avoiding detection when making many requests.
        """
        self.logger.info("Reinitializing driver with new headers...")
        self.quit()
        self.initialize_driver()
        return self._driver

    def quit(self):
        """
        Cleanly shuts down the driver if it's running.
        """
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info("Chrome WebDriver has been quit.")
            except Exception as e:
                self.logger.warning(f"Error quitting Chrome WebDriver: {e}")
            self._driver = None

    def __del__(self):
        # Ensure driver is closed if the util is garbage collected
        self.quit()
