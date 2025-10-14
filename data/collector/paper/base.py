from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Sequence
from pathlib import Path
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class BasePaperCollector(ABC):
    def __init__(
        self,
        out_dir: str | Path = "downloads/journals",
        headless: bool = True,
        per_page_timeout_s: int = 25,
        polite_sleep_s: float = 1.2,
        download_wait_s: int = 90,
        chrome_extra_args: Optional[Sequence[str]] = None,
    ):
        self.out_dir = Path(out_dir).resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.headless = headless
        self.per_page_timeout_s = per_page_timeout_s
        self.polite_sleep_s = polite_sleep_s
        self.download_wait_s = download_wait_s
        self.chrome_extra_args = list(chrome_extra_args or [])

        self._driver: Optional[webdriver.Chrome] = None
        self._wait: Optional[WebDriverWait] = None

    # ---------- Required, site-specific pieces ----------
    @abstractmethod
    def home_url(self) -> str:
        """Landing page to initiate the session (e.g., journal root)."""

    @abstractmethod
    def build_search_url(self, *, page: int, query: Optional[str]) -> str:
        """
        Return a results/search URL for the given page and query.
        If query is None or empty, return the 'latest' listing for that page.
        """

    @abstractmethod
    def collect_article_links(self) -> List[str]:
        """
        On the current results page (already loaded in driver),
        return absolute article URLs to visit.
        """

    @abstractmethod
    def find_pdf_link(self) -> Optional[str]:
        """
        On the current article page (already loaded), return the absolute PDF URL.
        Return None if not found.
        """

    def collect(self, *, query: Optional[str], max_pages: int) -> List[Path]:
        dl_dir = (self.out_dir / query).resolve()
        dl_dir.mkdir(parents=True, exist_ok=True)

        driver, wait = self._ensure_driver(download_dir=dl_dir)
        downloaded: List[Path] = []

        try:
            # Establish session
            driver.get(self.home_url())
            time.sleep(self.polite_sleep_s)

            # Walk paginated results
            for page in range(1, max_pages + 1):
                driver.get(self.build_search_url(page=page, query=query))
                time.sleep(self.polite_sleep_s)

                article_links = self.collect_article_links()
                if not article_links:
                    break

                for url in article_links:
                    # open in new tab
                    driver.execute_script("window.open(arguments[0], '_blank');", url)
                    driver.switch_to.window(driver.window_handles[-1])

                    try:
                        # Let subclass find the PDF link
                        pdf_url = self.find_pdf_link()

                        # One gentle refresh attempt if missing (sites build DOM via JS)
                        if not pdf_url:
                            driver.refresh()
                            time.sleep(0.8)
                            pdf_url = self.find_pdf_link_on_article()

                        if pdf_url:
                            driver.get(pdf_url)
                            time.sleep(0.8)
                            self._wait_for_downloads_to_finish(dl_dir, timeout_s=self.download_wait_s)

                            # pick the most recent PDF
                            latest = self._latest_pdf(dl_dir)
                            if latest:
                                downloaded.append(latest)

                    finally:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        time.sleep(self.polite_sleep_s)

                time.sleep(self.polite_sleep_s)

        finally:
            self._teardown_driver()

        # De-dup by filename, keep only existing
        uniq: List[Path] = []
        seen: set[str] = set()
        for p in downloaded:
            if p.exists() and p.name not in seen:
                uniq.append(p)
                seen.add(p.name)
        return uniq

    # ---------- Driver & download helpers ----------
    def _ensure_driver(self, *, download_dir: Path) -> tuple[webdriver.Chrome, WebDriverWait]:
        if self._driver is not None and self._wait is not None:
            return self._driver, self._wait

        opts = Options()
        if self.headless:
            # new headless mode (Chrome 109+)
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        for a in self.chrome_extra_args:
            opts.add_argument(a)

        prefs = {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
        }
        opts.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=opts)
        wait = WebDriverWait(driver, self.per_page_timeout_s)

        self._driver = driver
        self._wait = wait
        return driver, wait

    def _teardown_driver(self):
        if self._driver is not None:
            try:
                self._driver.quit()
            finally:
                self._driver = None
                self._wait = None

    @staticmethod
    def _active_downloads_exist(path: Path) -> bool:
        return any(p.suffix == ".crdownload" for p in path.iterdir())

    def _wait_for_downloads_to_finish(self, path: Path, *, timeout_s: int):
        start = time.time()
        while time.time() - start < timeout_s:
            if not self._active_downloads_exist(path):
                return
            time.sleep(0.5)

    @staticmethod
    def _latest_pdf(path: Path) -> Optional[Path]:
        pdfs: Iterable[Path] = path.glob("*.pdf")
        try:
            return sorted(pdfs, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        except IndexError:
            return None
