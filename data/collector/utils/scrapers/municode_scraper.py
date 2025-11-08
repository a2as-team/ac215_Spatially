from utils.selenium import SeleniumUtil
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import base64
from pathlib import Path

class MunicodeScraper:
    def __init__(self, url: str, download_dir: str):
        if not url.startswith("https://library.municode.com"):
            raise ValueError("Invalid URL. Must start with https://library.municode.com")
        self.url = url
        self.download_dir = download_dir
        self.selenium_util = SeleniumUtil(headless=True, download_dir=download_dir)

    def _dismiss_popups(self):
        """
        Dismiss any tour/help popups that might interfere with clicking.
        Looks for common popup close buttons and dismisses them.
        """
        # Be conservative; avoid closing our export modal by mistake
        popup_selectors = [
            ".hopscotch-bubble-close",  # Hopscotch tour close button
            ".hopscotch-cta button",  # Hopscotch CTA button
        ]

        for selector in popup_selectors:
            try:
                close_buttons = self.selenium_util.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in close_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except Exception as e:
                # If popup doesn't exist or can't be closed, that's fine
                pass
    def _normalize_heading(self, text):
        """
        Normalize a heading string for robust comparison.

        Collapses internal whitespace and trims.
        """
        if text is None:
            return ""
        normalized = " ".join(text.split())
        return normalized.strip()
    
    def _get_sections_with_buttons(self):
        """
        Extract all sections with their clickable buttons from TOC.

        Returns:
            List[tuple]: (section_name, button_element, has_select_all, li_element)
        """
        sections = []

        # Wait for the expandable TOC to load
        self.selenium_util.wait_for_element(By.CSS_SELECTOR, ".exp-toc", timeout=15)
        time.sleep(1.5)  # Reduced from 2s - Angular render wait

        # Collect sections and buttons from the top-level TOC
        toc_items = self.selenium_util.find_elements(By.CSS_SELECTOR, "ul.gen-toc-nav > li")

        for li_elem in toc_items:
            try:
                heading_elem = li_elem.find_element(
                    By.CSS_SELECTOR, "button.expToc-selector span[data-ng-bind]"
                )
                raw_name = heading_elem.text
                section_name = self._normalize_heading(raw_name)

                # Try to find SELECT ALL button first
                button = None
                has_select_all = False
                try:
                    button = li_elem.find_element(
                        By.CSS_SELECTOR, "button.expToc-select-all"
                    )
                    has_select_all = True
                except NoSuchElementException:
                    # Fall back to checkbox selector
                    button = li_elem.find_element(
                        By.CSS_SELECTOR, "button.expToc-selector"
                    )

                sections.append((section_name, button, has_select_all, li_elem))
            except NoSuchElementException:
                continue

        return sections
    
    def _print_to_pdf(self, filename="zoning_ordinance.pdf"):
        """
        Use Chrome DevTools Protocol to print the current page to PDF.

        Args:
            filename: Name of the PDF file to save

        Returns:
            Path: Path to the saved PDF file
        """
        print("Generating PDF using Chrome DevTools Protocol...")

        # Use CDP to print to PDF
        result = self.selenium_util.driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "landscape": False,
            "scale": 1,
            "paperWidth": 8.5,
            "paperHeight": 11,
            "marginTop": 0.4,
            "marginBottom": 0.4,
            "marginLeft": 0.4,
            "marginRight": 0.4,
        })

        # Decode base64 PDF data
        pdf_data = base64.b64decode(result['data'])

        # Save to file
        download_dir = Path(self.download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = download_dir / filename

        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)

        print(f"PDF saved: {pdf_path} ({len(pdf_data)} bytes)")
        return pdf_path

    def _wait_for_download_complete(self, expected_extension='.pdf', timeout=60):
        """
        Wait for download to complete by checking for downloaded file.

        Args:
            expected_extension: The file extension to look for (e.g., '.pdf', '.zip')
            timeout: Maximum time to wait in seconds

        Returns:
            Path: Path to the downloaded file
        """
        download_dir = Path(self.download_dir)
        end_time = time.time() + timeout

        print(f"Waiting for {expected_extension} download in: {download_dir}")

        while time.time() < end_time:
            # Check for files with expected extension
            files = list(download_dir.glob(f"*{expected_extension}"))

            # Filter out incomplete downloads (.crdownload, .tmp, .part)
            complete_files = [f for f in files if not any(
                str(f).endswith(ext) for ext in ['.crdownload', '.tmp', '.part']
            )]

            if complete_files:
                # Get the most recently modified file
                latest_file = max(complete_files, key=lambda f: f.stat().st_mtime)
                initial_size = latest_file.stat().st_size
                time.sleep(1)

                # If size hasn't changed, download is complete
                if latest_file.stat().st_size == initial_size and initial_size > 0:
                    print(f"Download complete: {latest_file.name} ({initial_size} bytes)")
                    return latest_file

            time.sleep(0.5)

        raise TimeoutError(f"Download did not complete within {timeout} seconds")

    def scrape(self):
        try:
            print(f"Navigating to {self.url}")
            self.selenium_util.driver.get(self.url)

            # Dismiss any popups that might interfere
            self._dismiss_popups()
            time.sleep(1)

            # Click the Download (Docx) button to open the offcanvas panel
            print("Clicking Download (Docx) button to open selection panel")
            self.selenium_util.click_element(By.XPATH, "//button[.//span[contains(text(), 'Download (Docx)')]]", timeout=15)

            # Wait for offcanvas panel to appear
            print("Waiting for offcanvas panel to appear")
            self.selenium_util.find_element(By.CSS_SELECTOR, ".offcanvas-pane.active", timeout=10)
            time.sleep(2)

            # Find and click all checkbox buttons to select all sections
            print("Selecting all checkboxes")
            checkboxes = self.selenium_util.find_elements(By.XPATH, "//button[@role='checkbox']")
            print(f"Found {len(checkboxes)} checkboxes")

            for checkbox in checkboxes:
                if checkbox.get_attribute("aria-checked") == "false":
                    checkbox.click()
                    time.sleep(0.2)

            # Click the final Download button to trigger the download
            print("Clicking Download button to download DOCX file")
            self.selenium_util.click_element(By.XPATH, "//button[contains(., 'Download') and contains(@class, 'btn-primary')]", timeout=10)

            # Wait for the DOCX file to download
            print("Waiting for DOCX download to complete...")
            downloaded_file = self._wait_for_download_complete(expected_extension='.docx', timeout=120)

            print(f"Scraping completed successfully. File saved to: {downloaded_file}")
            return downloaded_file

        except Exception as e:
            print(f"Error scraping Municode: {e}")
            raise e
        finally:
            self.selenium_util.quit()