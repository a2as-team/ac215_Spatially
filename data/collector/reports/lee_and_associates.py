
from __future__ import annotations

import re
import urllib.parse
from typing import Iterator, Optional

from base import BaseReportCollector, ReportItem


class LeeAndAssociatesCollector(BaseReportCollector):
    """
    Collector for https://www.lee-associates.com/research/ .
    Strategy:
      1) Paginate listing pages (`/research/`, `/research/page/2`, ...).
      2) On each page, extract all anchors that directly link to PDF files under
         `/wp-content/uploads/` and parse metadata from the filename or link text.
      3) Normalize into (Report Type, Location, Year, Quarter).
    """

    START_URL = "https://www.lee-associates.com/research/"
    PDF_PATTERN = re.compile(r"/wp-content/uploads/.+?\.pdf($|\?)", re.IGNORECASE)

    def _iter_report_pages(self) -> Iterator[str]:
        # The site exposes classic WP pagination paths: /research/page/2/, /page/3/, ...
        page = 1
        while True:
            url = self.START_URL if page == 1 else urllib.parse.urljoin(self.START_URL, f"page/{page}/")
            html = self._fetch(url)
            yield url

            # simple heuristic: stop when the page has no "Next" or repeats (empty list)
            # If no PDFs found on a page, we break after one more attempt.
            # To keep runtime reasonable for demos, cap at 200 pages.
            page += 1
            if page > 200:
                break

            # If there is no "Next »" marker on the page, we assume the end.
            if "Next »" not in html and "Older" not in html:
                break

    def _parse_report_links(self, html_url: str) -> Iterator[ReportItem]:
        html = self._fetch(html_url)
        # Grep all hrefs naïvely to avoid depending on JS-rendered DOM.
        urls = self.PDF_PATTERN.findall(html)  # this returns only the matched tail, need to re-scan
        # Fallback: search manually for full URLs ending in .pdf
        candidates = re.findall(r"https?://[^\"'> ]+?\.pdf", html, flags=re.IGNORECASE)
        seen = set()
        for href in candidates:
            if href in seen:
                continue
            seen.add(href)
            item = self._from_pdf_url_or_text(href)
            if item:
                yield item

    def _from_pdf_url_or_text(self, url: str) -> Optional[ReportItem]:
        """
        Parse metadata from the typical filename conventions used on the site:
          - 2024-Q4-Atlanta-GA-Industrial.pdf
          - 2024.Q4-North-America-Market-Report.pdf
          - 2025-Q2-Economic-Report.pdf  (if present)
        """
        fname = url.split("/")[-1]
        name = re.sub(r"\.pdf$", "", fname, flags=re.IGNORECASE)

        # 1) Local market pattern: 2024-Q4-Atlanta-GA-Industrial
        m = re.match(
            r"(?i)^(?P<year>\d{4})[-._]?(?P<q>Q[1-4])?[-._]?(?P<city>[A-Za-z.&\s]+?)[-._](?P<state>[A-Z]{2})[-._](?P<type>Industrial|Office|Retail|Multifamily)$",
            name.replace("%20", "-").replace(" ", "-"),
        )
        if m:
            year = int(m.group("year"))
            quarter = m.group("q")
            city = m.group("city").replace("-", " ").replace(".", "").strip()
            state = m.group("state")
            rtype = m.group("type").title()
            location = f"United States/{state}/{city}"
            title = f"{year} {quarter or ''} {city}, {state} - {rtype}".strip()
            return ReportItem(
                url=url,
                title=title,
                report_type=rtype,
                location=location,
                year=year,
                quarter=quarter,
                extra={"source": "filename"},
            )

        # 2) North America Market / Economic Reports e.g. 2024.Q4-North-America-Market-Report.pdf
        m2 = re.match(
            r"(?i)^(?P<year>\d{4})[-._]?(?P<q>Q[1-4])?[-._]?(?P<name>North[- ]America[- ]Market[- ]Report|Economic[- ]Report)$",
            name.replace("%20", "-").replace(" ", "-"),
        )
        if m2:
            year = int(m2.group("year"))
            quarter = m2.group("q")
            report_name = m2.group("name").replace("-", " ")
            if "Economic" in report_name:
                rtype = "Economic Report"
            else:
                rtype = "North America Market Report"
            location = "North America"
            title = f"{year} {quarter or ''} {rtype}".strip()
            return ReportItem(
                url=url,
                title=title,
                report_type=rtype,
                location=location,
                year=year,
                quarter=quarter,
                extra={"source": "filename"},
            )

        # 3) Fallback – use basic inference from tokens
        # Try to get year and quarter anywhere in the string
        year_match = re.search(r"(20\d{2})", name)
        q_match = re.search(r"(Q[1-4])", name, flags=re.IGNORECASE)
        year = int(year_match.group(1)) if year_match else 0
        quarter = q_match.group(1).upper() if q_match else None
        # Heuristics for type
        if re.search(r"industrial", name, re.I):
            rtype = "Industrial"
        elif re.search(r"multifamily", name, re.I):
            rtype = "Multifamily"
        elif re.search(r"office", name, re.I):
            rtype = "Office"
        elif re.search(r"retail", name, re.I):
            rtype = "Retail"
        elif re.search(r"economic", name, re.I):
            rtype = "Economic Report"
        elif re.search(r"north[-._ ]america", name, re.I):
            rtype = "North America Market Report"
        else:
            rtype = "Market Report"

        # Location heuristics: "...-City-ST-..." pattern
        loc = None
        mloc = re.search(r"([A-Za-z.&\s]+?)[-._]([A-Z]{2})(?:[-._]|$)", name)
        if mloc:
            city = mloc.group(1).replace("-", " ").strip()
            state = mloc.group(2)
            loc = f"United States/{state}/{city}"
        else:
            loc = "North America"

        if year:
            return ReportItem(
                url=url,
                title=name,
                report_type=rtype,
                location=loc,
                year=year,
                quarter=quarter,
                extra={"source": "heuristic"},
            )
        return None
