from __future__ import annotations
from typing import List, Optional
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from collector.paper.base import BasePaperCollector

BASE = "https://www.mdpi.com"

class MDPICollector(BasePaperCollector):
    """
    MDPI implementation using Selenium.

    Notes:
      - Non-headless often avoids 403s from static HTTP libraries.
      - We favor flexible CSS selectors to be resilient to minor layout changes.
    """

    def __init__(self, journal: str = "land", **kwargs):
        """
        Args:
            journal: MDPI journal slug (e.g., 'land', 'electronics', 'sensors')
            **kwargs: forwarded to BasePaperCollector (out_dir, headless, etc.)
        """
        super().__init__(**kwargs)
        self.journal = journal

    def home_url(self) -> str:
        return f"{BASE}/journal/{self.journal}"

    def build_search_url(self, *, page: int, query: Optional[str]) -> str:
        # Example (latest): https://www.mdpi.com/search?q=&journal=land&sort=pubdate&page_no=1
        q_param = "" if not query else query
        return (
            f"{BASE}/search?q={q_param}"
            f"&journal={self.journal}"
            f"&sort=pubdate&page_no={page}"
        )

    def collect_article_links(self) -> List[str]:
        driver, wait = self._driver, self._wait
        assert driver and wait

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.title-link[href]")))

        links = set()
        for a in driver.find_elements(
            By.CSS_SELECTOR,
            "div.generic-item.article-item a.title-link[href], a.title-link[href]"
        ):
            href = (a.get_attribute("href") or "").split("#")[0]
            if not href:
                continue
            href = urljoin(BASE, href)

            # Optional skips
            if "special-issue" in href or "/editorial" in href:
                continue

            links.add(href)

        return sorted(links)

    def find_pdf_link(self) -> Optional[str]:
        driver, wait = self._driver, self._wait
        assert driver and wait

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Primary: MDPI uses an anchor with class 'UD_ArticlePDF'
        try:
            anchor = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.UD_ArticlePDF[href]"))
            )
            href = (anchor.get_attribute("href") or "").split("#")[0]
            return urljoin(BASE, href) if href else None
        except Exception:
            # Fallbacks if MDPI changes the class
            # Look for <a> with href ending .pdf or containing '/pdf'
            for sel in ["a[href$='.pdf']", "a[href*='/pdf']"]:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    href = (els[0].get_attribute("href") or "").split("#")[0]
                    return urljoin(BASE, href)
            return None
