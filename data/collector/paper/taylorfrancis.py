# data/collector/paper/taylorfrancis.py
from __future__ import annotations
import os
import re
from time import sleep, time
from typing import List, Dict, Optional
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    HAS_WDM = True
except Exception:
    HAS_WDM = False

from .base import BasePaperCollector

BASE = "https://www.tandfonline.com"


class TaylorFrancisCollector(BasePaperCollector):
    """
    Taylor & Francis (tandfonline) collector.

    Strategy:
    - Build volume URLs using ?treeId=v<journal_code>-<vol>, where vol=(year-2013)+1
    - From volume page, collect issue links (exclude '/current')
    - From issue TOC, collect article landing links (/doi/* but NOT /pdf)
    - Normalize links to one per DOI (priority: full > abs > ref > epdf > epub > plain)
    - Derive /doi/pdf/<DOI>?download=true
    - Download PDF via `requests` with Selenium cookies (cf_clearance/session)
    - Optionally attach to an existing Chrome via debugger_address (pass CF manually)
    """

    def __init__(
        self,
        *,
        journal_code: str = "rupt20",
        from_year: int = 2013,
        to_year: int = 2025,
        debugger_address: Optional[str] = None,  # e.g., "127.0.0.1:9222"
        headless: bool = False,  # used when not attaching
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.journal_code = journal_code
        self.from_year = from_year
        self.to_year = to_year
        self.debugger_address = debugger_address
        self._headless = headless

    # -------- Base hooks (not used by TFO flow but required) --------
    def home_url(self) -> str:
        return f"{BASE}/loi/{self.journal_code}"

    def build_search_url(self, *, page: int, query: Optional[str]) -> str:
        # Not applicable to TFO flow
        return self.home_url()

    def collect_article_links(self) -> List[str]:
        # Not applicable to TFO flow
        return []

    def find_pdf_link(self) -> Optional[str]:
        # Not applicable to TFO flow
        return None

    # ----------------------------- main entry -----------------------------
    def collect(self, *, query: Optional[str], max_pages: int) -> List[os.PathLike]:
        """
        `query` and `max_pages` are ignored for TFO; we iterate year range instead.

        Returns: list of downloaded file paths.
        """
        dl_dir = self.out_dir.resolve()
        dl_dir.mkdir(parents=True, exist_ok=True)

        driver, wait = self._ensure_tfo_driver(download_dir=str(dl_dir))
        saved_files: List[os.PathLike] = []

        try:
            for year in range(self.from_year, self.to_year + 1):
                vol = (year - 2013) + 1
                vol_url = (
                    f"{BASE}/loi/{self.journal_code}?treeId=v{self.journal_code}-{vol}"
                )
                print(f"\n=== Year {year} | Volume {vol} ===")
                print("[*] volume:", vol_url)
                driver.get(vol_url)
                sleep(self.polite_sleep_s)

                if self._is_cloudflare(driver.page_source):
                    print("⚠️  Cloudflare challenge on volume page... waiting")
                    if not self._wait_cf_pass(driver, timeout=120):
                        print("   skip year (CF not passed).")
                        continue

                issues = self._collect_issue_links(driver)
                print(f"[*] issues found: {len(issues)}")
                if not issues:
                    continue

                for issue_url in issues:
                    print("[*] open issue:", issue_url)
                    driver.get(issue_url)
                    sleep(self.polite_sleep_s)

                    if self._is_cloudflare(driver.page_source):
                        print("⚠️  Cloudflare challenge on issue page... waiting")
                        if not self._wait_cf_pass(driver, timeout=120):
                            print("   skip issue (CF not passed).")
                            continue

                    self._expand_toc(driver)
                    sleep(0.4)

                    arts = self._find_article_landings(driver)
                    arts = self._normalize_by_doi(arts)
                    print(f"[*] unique DOIs on TOC: {len(arts)}")

                    for idx, aurl in enumerate(arts, 1):
                        print(f"  - [{idx}/{len(arts)}] article:", aurl)
                        pdf_url = self._derive_pdf_url(aurl)
                        if not pdf_url:
                            print("    -> cannot derive pdf url; skip")
                            continue

                        out_path = self._requests_download(
                            pdf_url, driver, str(dl_dir), referer=aurl
                        )
                        if out_path:
                            saved_files.append(os.fspath(out_path))
                            sleep(self.polite_sleep_s)

        finally:
            if not self.debugger_address:
                # only close when we created the browser
                self._teardown_driver()

        return [self.out_dir / os.path.basename(p) for p in saved_files]

    # ----------------------------- driver management -----------------------------
    def _ensure_tfo_driver(
        self, *, download_dir: str
    ) -> tuple[webdriver.Chrome, WebDriverWait]:
        # If a driver already exists (from Base), reuse it
        if self._driver is not None and self._wait is not None:
            return self._driver, self._wait

        if self.debugger_address:
            opts = Options()
            opts.debugger_address = self.debugger_address
            opts.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": download_dir,
                    "download.prompt_for_download": False,
                    "plugins.always_open_pdf_externally": True,
                },
            )
            driver = webdriver.Chrome(options=opts)
        else:
            # Start a fresh driver (may hit Cloudflare if heavy crawling)
            from selenium.webdriver.chrome.options import Options as StdOptions

            opts = StdOptions()
            if self._headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_experimental_option(
                "prefs",
                {
                    "download.default_directory": download_dir,
                    "download.prompt_for_download": False,
                    "plugins.always_open_pdf_externally": True,
                },
            )
            if HAS_WDM:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=opts)
            else:
                driver = webdriver.Chrome(options=opts)

        wait = WebDriverWait(driver, self.per_page_timeout_s)
        self._driver = driver
        self._wait = wait
        return driver, wait

    # ----------------------------- page helpers -----------------------------
    @staticmethod
    def _is_cloudflare(html: str) -> bool:
        if not html:
            return False
        needles = [
            "/cdn-cgi/challenge-platform",
            "cf-turnstile",
            "正在验证您是否是真人",
            "Checking your browser before accessing",
            "Please stand by, while we are checking your browser",
            "Ray ID:",
        ]
        return any(n in html for n in needles)

    @staticmethod
    def _wait_cf_pass(driver: webdriver.Chrome, timeout: int = 120) -> bool:
        t0 = time()
        while time() - t0 < timeout:
            if not TaylorFrancisCollector._is_cloudflare(driver.page_source):
                return True
            sleep(2.0)
        return False

    def _collect_issue_links(self, driver: webdriver.Chrome) -> List[str]:
        anchors = driver.find_elements(
            By.CSS_SELECTOR, f"a[href*='/toc/{self.journal_code}']"
        )
        links = []
        for a in anchors:
            href = (a.get_attribute("href") or "").split("#")[0]
            if href and "/current" not in href:
                links.append(href)
        # dedupe
        seen, out = set(), []
        for u in links:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    @staticmethod
    def _expand_toc(driver: webdriver.Chrome):
        selectors = [
            "#tocListWidget button[aria-expanded='false']",
            "#tocListWidget .accordion button[aria-expanded='false']",
            "#tocListWidget [data-toggle='collapse']",
            "#tocListWidget .accordion-toggle",
            "#tocListWidget button",
        ]
        clicks = 0
        for sel in selectors:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for b in btns:
                try:
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                        sleep(0.08)
                        clicks += 1
                except Exception:
                    continue
        if clicks:
            print(f"[*] expanded {clicks} toc buttons")

    @staticmethod
    def _find_article_landings(driver: webdriver.Chrome) -> List[str]:
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/doi/']")
        links = []
        for a in anchors:
            href = (a.get_attribute("href") or "").split("#")[0]
            if not href:
                continue
            if "/doi/pdf/" in href:
                continue
            if any(
                x in href
                for x in (
                    "/figure",
                    "/suppl",
                    "/tables",
                    "/metrics",
                    "/book",
                    "/authors",
                )
            ):
                continue
            if "/doi/" in href:
                links.append(href)
        # dedupe
        seen, uniq = set(), []
        for u in links:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        return uniq

    @staticmethod
    def _normalize_by_doi(links: List[str]) -> List[str]:
        """Keep one landing per DOI with priority full > abs > ref > epdf > epub > (plain)"""
        prio = {"full": 0, "abs": 1, "ref": 2, "epdf": 3, "epub": 4, "": 5}
        best: Dict[str, tuple[int, str]] = {}
        for u in links:
            path = urlparse(u).path
            m = re.search(r"/doi/(full|abs|ref|epdf|epub)/(.+)$", path)
            if m:
                k, doi = m.group(1), m.group(2)
            else:
                m2 = re.search(r"/doi/([^/].+)$", path)
                if not m2:
                    continue
                k, doi = "", m2.group(1)
            rank = prio.get(k, 9)
            if doi not in best or rank < best[doi][0]:
                best[doi] = (rank, u)
        return [v for _, v in sorted((v for v in best.values()), key=lambda t: t[0])]

    @staticmethod
    def _derive_pdf_url(url: str) -> Optional[str]:
        path = urlparse(url).path
        if "/doi/pdf/" in path:
            doi = path.split("/doi/pdf/")[1]
            return f"{BASE}/doi/pdf/{doi}?download=true"
        m = re.search(r"/doi/(?:full|abs|citedby|ref|suppl|epub|epdf)/(.+)$", path)
        if m:
            return f"{BASE}/doi/pdf/{m.group(1)}?download=true"
        m2 = re.search(r"/doi/([^/].+)$", path)
        if m2:
            return f"{BASE}/doi/pdf/{m2.group(1)}?download=true"
        return None

    @staticmethod
    def _requests_download(
        pdf_url: str, driver: webdriver.Chrome, out_dir: str, *, referer: str = ""
    ) -> Optional[str]:
        try:
            sess = requests.Session()
            for c in driver.get_cookies():
                sess.cookies.set(c.get("name"), c.get("value"), domain=c.get("domain"))
            ua = driver.execute_script("return navigator.userAgent;") or "Mozilla/5.0"
            headers = {
                "User-Agent": ua,
                "Accept": "application/pdf,*/*;q=0.8",
            }
            if referer:
                headers["Referer"] = referer
            with sess.get(pdf_url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                doi_part = (
                    pdf_url.split("/doi/pdf/")[-1].split("?")[0].replace("/", "_")
                )
                fname = f"{doi_part}.pdf"
                out_path = os.path.join(out_dir, fname)
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
            if os.path.getsize(out_path) > 1024:
                print(f"    -> saved {out_path} ({os.path.getsize(out_path)} bytes)")
                return out_path
            os.remove(out_path)
            return None
        except Exception as e:
            print("    -> requests download failed:", e)
            return None
