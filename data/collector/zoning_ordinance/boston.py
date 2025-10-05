import os
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import sys

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from collector.zoning_ordinance.base import ZoningOrdinanceBaseCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZoningCodeCollector(ZoningOrdinanceBaseCollector):
    """
    Collector for Boston zoning code data from Municode library.
    Uses Selenium to automate downloading Excel files for each zoning article.
    """

    URL = "https://library.municode.com/ma/boston/codes/redevelopment_authority"

    # Sections to exclude from download
    EXCLUDED_SECTIONS = {
        "PROOF ONLY ZONING CODE CITY OF BOSTON, MASSACHUSETTS",
        "SUPPLEMENT HISTORY TABLE",
        "All Zoning Maps",
        "CODE COMPARATIVE TABLE",
        "CODE COMPARATIVE TABLE - ORDINANCES",
    }

    def __init__(self, headless=True, download_dir=None):
        """
        Initialize the ZoningCodeCollector.

        Args:
            headless (bool): Whether to run browser in headless mode
            download_dir (str): Directory to save downloaded files.
                              Defaults to boston_collected_data in the zoning_ordinance directory.
        """
        super().__init__(headless=headless, download_dir=download_dir)

    def _get_default_download_dir(self) -> Path:
        """Get the default download directory for Boston collector."""
        return Path(__file__).parent / "boston_collected_data"

    def _normalize_heading(self, text):
        """
        Normalize a heading string for robust comparison.

        Collapses internal whitespace and trims.
        """
        if text is None:
            return ""
        normalized = " ".join(text.split())
        return normalized.strip()

    def _wait_for_element(self, by, value, timeout=10):
        """
        Wait for an element to be present and visible.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum time to wait in seconds

        Returns:
            WebElement if found
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {value}")
            raise

    def _click_element(self, by, value, timeout=10):
        """
        Wait for an element to be clickable and click it.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Maximum time to wait in seconds
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            logger.info(f"Clicked element: {value}")
        except TimeoutException:
            logger.error(f"Timeout waiting to click element: {value}")
            raise

    def _dismiss_popups(self):
        """
        Dismiss any tour/help popups that might interfere with clicking.
        Looks for common popup close buttons and dismisses them.
        """
        # Be conservative; avoid closing our export modal by mistake
        popup_selectors = [
            ".hopscotch-bubble-close",  # Hopscotch tour close button
            ".hopscotch-cta button",     # Hopscotch CTA button
        ]

        for selector in popup_selectors:
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        logger.info(f"Dismissed popup with selector: {selector}")
                        time.sleep(0.5)
            except Exception as e:
                # If popup doesn't exist or can't be closed, that's fine
                pass

    def _get_sections_with_buttons(self):
        """
        Extract all sections with their clickable buttons from TOC.

        Returns:
            List[tuple]: (section_name, button_element, has_select_all, li_element)
        """
        sections = []

        # Wait for the expandable TOC to load
        self._wait_for_element(By.CSS_SELECTOR, ".exp-toc", timeout=15)
        time.sleep(1.5)  # Reduced from 2s - Angular render wait

        # Collect sections and buttons from the top-level TOC
        toc_items = self.driver.find_elements(By.CSS_SELECTOR, "ul.gen-toc-nav > li")

        for li_elem in toc_items:
            try:
                heading_elem = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector span[data-ng-bind]")
                raw_name = heading_elem.text
                section_name = self._normalize_heading(raw_name)

                # Exclude exact matches only (as specified)
                if section_name in self.EXCLUDED_SECTIONS:
                    logger.info(f"Skipping excluded section: {section_name}")
                    continue

                # Try to find SELECT ALL button first
                button = None
                has_select_all = False
                try:
                    button = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
                    has_select_all = True
                except NoSuchElementException:
                    # Fall back to checkbox selector
                    button = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")

                sections.append((section_name, button, has_select_all, li_elem))
            except NoSuchElementException:
                continue

        return sections

    def _find_section_button(self, section_name):
        """
        Locate the clickable button for a given section by its heading text.

        Prefers the "SELECT ALL" control when available; falls back to the
        checkbox selector when a select-all is not present.

        Args:
            section_name (str): Visible heading text of the section

        Returns:
            tuple[WebElement, bool]: (button element, has_select_all)
        """
        # Wait for list to exist
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.gen-toc-nav > li"))
        )

        # Try to find exact match by iterating visible items
        toc_items = self.driver.find_elements(By.CSS_SELECTOR, "ul.gen-toc-nav > li")
        normalized_target = self._normalize_heading(section_name)
        li_elem = None

        for item in toc_items:
            try:
                span = item.find_element(By.CSS_SELECTOR, "button.expToc-selector span[data-ng-bind]")
                current = self._normalize_heading(span.text)
                if current == normalized_target:
                    li_elem = item
                    break
            except NoSuchElementException:
                continue

        # Fallback: partial match on prefix to handle rare whitespace issues
        if li_elem is None:
            prefix = normalized_target[:24]
            for item in toc_items:
                try:
                    span = item.find_element(By.CSS_SELECTOR, "button.expToc-selector span[data-ng-bind]")
                    current = self._normalize_heading(span.text)
                    if current.startswith(prefix):
                        li_elem = item
                        break
                except NoSuchElementException:
                    continue

        if li_elem is None:
            raise TimeoutException(f"Section not found in TOC: {section_name}")

        # Prefer select-all when present
        try:
            btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
            return btn, True
        except NoSuchElementException:
            pass

        # Fall back to the checkbox selector
        btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")
        return btn, False

    def _wait_export_enabled(self, timeout=5):
        """
        Wait until the Export (.xlsx) button becomes enabled (aria-disabled != 'true').

        Returns:
            WebElement: The export button once enabled
        """
        def _find_enabled_export(driver):
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(@ng-click, 'doSaveAsExcel')]")
                if btn.get_attribute("aria-disabled") != "true":
                    return btn
            except Exception:
                return None
            return None

        return WebDriverWait(self.driver, timeout).until(_find_enabled_export)

    def _wait_for_download(self, timeout=30, pre_existing_files=None):
        """
        Wait for a file to finish downloading.

        Args:
            timeout: Maximum time to wait in seconds
        """
        end_time = time.time() + timeout
        if pre_existing_files is None:
            pre_existing_files = set(os.listdir(self.download_dir))
        while time.time() < end_time:
            # Check if there are any .crdownload files (Chrome partial download)
            downloading = False
            for filename in os.listdir(self.download_dir):
                if filename.endswith('.crdownload') or filename.endswith('.tmp'):
                    downloading = True
                    break

            current_files = set(os.listdir(self.download_dir))
            new_files = [f for f in current_files - pre_existing_files if f.endswith('.xlsx')]

            if not downloading and new_files:
                time.sleep(1)  # Wait a bit more to ensure file is complete
                logger.info("Download completed")
                return True

            time.sleep(0.5)

        logger.warning("Download timeout reached")
        return False

    def _rename_downloaded_file(self, section_name):
        """
        Rename the most recently downloaded file to match the section name.

        Args:
            section_name: Name of the section being downloaded
        """
        # Get the most recent .xlsx file
        files = [f for f in os.listdir(self.download_dir) if f.endswith('.xlsx')]
        if not files:
            logger.warning("No .xlsx file found after download")
            return

        # Sort by modification time
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
        latest_file = files[0]

        # Create sanitized filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in section_name)
        safe_name = safe_name.strip().replace(' ', '_')
        new_filename = f"{safe_name}.xlsx"

        old_path = os.path.join(self.download_dir, latest_file)
        new_path = os.path.join(self.download_dir, new_filename)

        # If file already exists, add a number suffix
        counter = 1
        while os.path.exists(new_path):
            new_filename = f"{safe_name}_{counter}.xlsx"
            new_path = os.path.join(self.download_dir, new_filename)
            counter += 1

        os.rename(old_path, new_path)
        logger.info(f"Renamed file to: {new_filename}")

    def _retry_failed_sections(self, all_sections, failed_section_names, max_retries=3):
        """
        Retry downloading failed sections.

        Args:
            all_sections: List of all (section_name, button, has_select_all, li_elem) tuples
            failed_section_names: List of section names that failed
            max_retries: Maximum number of retry attempts

        Returns:
            dict: Results of retry attempts
        """
        # Create lookup for failed sections
        failed_lookup = {name: (btn, has_select_all, li_elem)
                        for name, btn, has_select_all, li_elem in all_sections
                        if name in failed_section_names}

        downloaded = 0
        still_failed = []

        for section_name in failed_section_names:
            success = False

            for attempt in range(max_retries):
                try:
                    logger.info(f"Retry {attempt + 1}/{max_retries} for: {section_name}")

                    if section_name not in failed_lookup:
                        logger.warning(f"Section not found in lookup: {section_name}")
                        still_failed.append(section_name)
                        break

                    select_all_btn, has_select_all, li_elem = failed_lookup[section_name]

                    # Dismiss any popups
                    self._dismiss_popups()
                    time.sleep(0.5)  # Reduced from 1s

                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", select_all_btn)
                    time.sleep(0.5)  # Reduced from 1s

                    # Use JavaScript click to bypass popup interception
                    try:
                        self.driver.execute_script("arguments[0].click();", select_all_btn)
                    except Exception:
                        # Re-find within li if stale
                        if has_select_all:
                            select_all_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
                        else:
                            select_all_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")
                        self.driver.execute_script("arguments[0].click();", select_all_btn)

                    time.sleep(0.5)  # Reduced from 1s

                    # Wait for export enabled and click
                    export_btn = self._wait_export_enabled()
                    try:
                        export_btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", export_btn)

                    # Wait for download
                    pre_files = set(os.listdir(self.download_dir))
                    if self._wait_for_download(pre_existing_files=pre_files):
                        self._rename_downloaded_file(section_name)
                        downloaded += 1
                        success = True
                        logger.info(f"✓ Successfully downloaded on retry: {section_name}")

                        # Deselect
                        time.sleep(0.5)  # Reduced from 1s
                        try:
                            self.driver.execute_script("arguments[0].click();", select_all_btn)
                        except Exception:
                            # Re-find if needed
                            if has_select_all:
                                select_all_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
                            else:
                                select_all_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")
                            self.driver.execute_script("arguments[0].click();", select_all_btn)
                        time.sleep(0.3)  # Reduced from 0.5s
                        break
                    else:
                        logger.warning(f"Download timeout on retry {attempt + 1}")

                except Exception as e:
                    logger.error(f"Retry {attempt + 1} failed for '{section_name}': {e}")
                    time.sleep(1)  # Reduced from 2s - Wait before next retry

            if not success:
                still_failed.append(section_name)
                logger.error(f"✗ All retries failed for: {section_name}")

        return {
            "downloaded": downloaded,
            "failed_sections": still_failed
        }

    def collect(self):
        """
        Main collection method. Downloads all zoning code sections.

        Returns:
            dict: Summary of collection results
        """
        try:
            self._setup_driver()

            # Navigate to the page
            logger.info(f"Navigating to {self.URL}")
            self.driver.get(self.URL)

            # Wait for page to load
            self._wait_for_element(By.ID, "print-download-toc", timeout=15)
            time.sleep(2)

            # Click the print/download button
            logger.info("Clicking print/download button")
            self._click_element(By.ID, "print-download-toc")

            # Wait for modal to appear
            self._wait_for_element(By.CSS_SELECTOR, ".modal-content", timeout=10)
            time.sleep(2)

            # Get all sections with buttons upfront (O(n) instead of O(n²))
            sections = self._get_sections_with_buttons()
            logger.info(f"Found {len(sections)} sections to download")

            downloaded_count = 0
            failed_sections = []

            # Dismiss popups once at the start
            self._dismiss_popups()

            # Download each section
            for section_name, clickable_btn, has_select_all, li_elem in sections:
                try:
                    logger.info(f"Processing section: {section_name}")

                    # Scroll element into view (center it inside the modal)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable_btn)
                    time.sleep(0.3)  # Reduced from 0.6s

                    # Click selection button with stale element recovery
                    try:
                        clickable_btn.click()
                    except Exception as e:
                        # Try JS click first
                        try:
                            self.driver.execute_script("arguments[0].click();", clickable_btn)
                        except Exception:
                            # If stale, re-find button quickly within the same li element
                            logger.warning(f"Stale element, re-finding button for: {section_name}")
                            if has_select_all:
                                clickable_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
                            else:
                                clickable_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")
                            self.driver.execute_script("arguments[0].click();", clickable_btn)

                    time.sleep(0.3)  # Reduced from 0.6s

                    # Wait until Export is enabled, then click
                    export_btn = self._wait_export_enabled()
                    try:
                        export_btn.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", export_btn)

                    # Wait for download to complete
                    if self._wait_for_download(pre_existing_files=set(os.listdir(self.download_dir))):
                        self._rename_downloaded_file(section_name)
                        downloaded_count += 1
                    else:
                        logger.warning(f"Download timeout for section: {section_name}")
                        failed_sections.append(section_name)

                    # Deselect all (click the same button again to reset)
                    time.sleep(0.5)  # Reduced from 1s
                    try:
                        clickable_btn.click()
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", clickable_btn)
                        except Exception:
                            # Re-find if needed
                            if has_select_all:
                                clickable_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-select-all")
                            else:
                                clickable_btn = li_elem.find_element(By.CSS_SELECTOR, "button.expToc-selector")
                            self.driver.execute_script("arguments[0].click();", clickable_btn)
                    time.sleep(0.2)  # Reduced from 0.5s

                except Exception as e:
                    logger.error(f"Error downloading section '{section_name}': {e}")
                    failed_sections.append(section_name)

            # Retry failed sections
            if failed_sections:
                logger.info(f"\nRetrying {len(failed_sections)} failed sections...")
                retry_results = self._retry_failed_sections(sections, failed_sections)
                downloaded_count += retry_results["downloaded"]
                failed_sections = retry_results["failed_sections"]

            results = {
                "total_sections": len(sections),
                "downloaded": downloaded_count,
                "failed": len(failed_sections),
                "failed_sections": failed_sections,
                "download_directory": self.download_dir
            }

            logger.info(f"Collection complete: {downloaded_count}/{len(sections)} sections downloaded")
            return results

        except Exception as e:
            logger.error(f"Collection failed: {e}")
            raise
        finally:
            self._cleanup_driver()

    def validate(self, data: dict) -> bool:
        """
        Validate the collected data.

        Args:
            data: The collection results to validate

        Returns:
            True if validation passes, False otherwise
        """
        if not data:
            logger.error("No data provided for validation")
            return False

        if data.get("failed", 0) > 0:
            logger.warning(f"Collection had {data['failed']} failed sections")
            # Not a hard failure - some sections may fail

        if data.get("downloaded", 0) == 0:
            logger.error("No sections were downloaded")
            return False

        logger.info("Validation passed")
        return True
