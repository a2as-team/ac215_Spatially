from __future__ import annotations

import os
import re
import time
import pathlib
from typing import Iterable, List, Optional, Union

import requests
from bs4 import BeautifulSoup

from .base import BaseReportCollector


class LeeAndAssociatesCollector(BaseReportCollector):
    """
    Lee & Associates collector.

    Public API:
      - get_downloadable_file_urls(limit): flat list of PDF URLs
      - get_select_options(limit): dict(report_types, locations, years)
      - list_urls_for(report_type, location, year, limit): filtered URLs
      - download_for_options(...): download subset into structured folders
    """

    START_URL = "https://www.lee-associates.com/research/"
    PDF_RE = re.compile(r"https?://[^\"'> ]+?\.pdf", re.I)

    # ---------- Required ----------
    def get_downloadable_file_urls(self, limit: Optional[int] = None) -> List[str]:
        entries = self._discover_entries(limit=limit)
        return [e["url"] for e in entries]

    # ---------- Options for this source ----------
    def get_select_options(self, limit: Optional[int] = None) -> dict:
        types, locs, years = set(), set(), set()
        for e in self._discover_entries(limit=limit):
            if e.get("report_type"):
                types.add(e["report_type"])
            if e.get("location"):
                locs.add(e["location"])
            if e.get("year"):
                years.add(str(e["year"]))
        return {
            "report_types": sorted(types),
            "locations": sorted(locs),
            "years": sorted(years),
        }

    # ---------- Targeted URL selection ----------
    def list_urls_for(
        self,
        report_type: Optional[str] = None,
        location: Optional[str] = None,
        year: Optional[Union[int, str]] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        entries = self._discover_entries(limit=limit)
        if isinstance(year, str) and year.isdigit():
            year = int(year)
        out: List[str] = []
        for e in entries:
            if report_type and e.get("report_type") != report_type:
                continue
            if location and e.get("location") != location:
                continue
            if year and e.get("year") != year:
                continue
            out.append(e["url"])
        return out

    # ---------- Download only the requested subset ----------
    def download_for_options(
        self,
        report_type: Optional[str],
        location: Optional[str],
        year: Optional[Union[int, str]],
        dest_root: Union[str, os.PathLike],
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> List[str]:
        entries = self._discover_entries(limit=limit)
        if isinstance(year, str) and year.isdigit():
            year = int(year)

        saved: List[str] = []
        for e in entries:
            if report_type and e.get("report_type") != report_type:
                continue
            if location and e.get("location") != location:
                continue
            if year and e.get("year") != year:
                continue

            # <dest_root>/<report_type>/<location>/<year>/
            rtype = _slug(e.get("report_type", "unknown"))
            loc = _slug(e.get("location", "unknown"))
            yr = str(e.get("year", "unknown"))
            folder = pathlib.Path(dest_root) / rtype / loc / yr
            folder.mkdir(parents=True, exist_ok=True)

            fname = self._filename_for_entry(e)
            url = e["url"]
            outpath = folder / fname

            if dry_run:
                print(f"Would download: {url} -> {outpath}")
                saved.append(str(outpath))
                continue

            try:
                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(outpath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                saved.append(str(outpath))
                time.sleep(self.polite_delay_sec)
            except Exception as ex:
                print(f"Failed to download {url}: {ex}")
        return saved

    # ---------- Internal crawl & parse ----------
    def _discover_entries(self, limit: Optional[int] = None) -> List[dict]:
        entries: List[dict] = []
        for page_url in self._paginate():
            html = self._fetch(page_url)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not self.PDF_RE.search(href):
                    continue
                meta = self._parse_from_filename(href)
                meta["url"] = href
                entries.append(meta)
                if limit and len(entries) >= limit:
                    return entries
        return entries

    def _paginate(self) -> Iterable[str]:
        # Use presence of posts/cards to decide when to stop (no hard reliance on "Next »" text)
        page = 1
        while True:
            url = (
                self.START_URL
                if page == 1
                else f"{self.START_URL.rstrip('/')}/page/{page}/"
            )
            html = self._fetch(url)
            soup = BeautifulSoup(html, "html.parser")
            posts = soup.select("article, .post, .entry, .grid .card, .et_pb_post")
            if page == 1 or posts:
                yield url
            if page > 1 and not posts:
                break
            page += 1
            if page > 200:
                break  # safety cap

    def _fetch(self, url: str) -> str:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _parse_from_filename(url: str) -> dict:
        name = url.split("/")[-1]
        stem = re.sub(r"\.pdf$", "", name, flags=re.I)
        token = stem.replace("%20", "-").replace(" ", "-")

        # Pattern A: 2024-Q4-Atlanta-GA-Industrial
        m = re.match(
            r"(?i)^(?P<year>20\d{2})[-._]?(?P<q>Q[1-4])?[-._]?(?P<city>[A-Za-z.&\s]+?)[-._](?P<state>[A-Z]{2})[-._](?P<type>Industrial|Office|Retail|Multifamily)$",
            token,
        )
        if m:
            year = int(m.group("year"))
            q = m.group("q")
            city = m.group("city").replace("-", " ").replace(".", "").strip()
            state = m.group("state")
            rtype = m.group("type").title()
            return {
                "year": year,
                "quarter": q,
                "report_type": rtype,
                "location": f"United States/{state}/{city}",
            }

        # Pattern B: 2024.Q4-North-America-Market-Report / Economic-Report
        m2 = re.match(
            r"(?i)^(?P<year>20\d{2})[-._]?(?P<q>Q[1-4])?[-._]?(?P<name>North[- ]America[- ]Market[- ]Report|Economic[- ]Report)$",
            token,
        )
        if m2:
            year = int(m2.group("year"))
            q = m2.group("q")
            name = m2.group("name").replace("-", " ")
            rtype = (
                "Economic Report"
                if "Economic" in name
                else "North America Market Report"
            )
            return {
                "year": year,
                "quarter": q,
                "report_type": rtype,
                "location": "North America",
            }

        # Fallback
        out = {"year": None, "quarter": None, "report_type": None, "location": None}
        ym = re.search(r"(20\d{2})", token)
        if ym:
            out["year"] = int(ym.group(1))
        qm = re.search(r"(Q[1-4])", token, flags=re.I)
        if qm:
            out["quarter"] = qm.group(1).upper()

        if re.search(r"industrial", token, re.I):
            out["report_type"] = "Industrial"
        elif re.search(r"multifamily", token, re.I):
            out["report_type"] = "Multifamily"
        elif re.search(r"office", token, re.I):
            out["report_type"] = "Office"
        elif re.search(r"retail", token, re.I):
            out["report_type"] = "Retail"
        elif re.search(r"economic", token, re.I):
            out["report_type"] = "Economic Report"
        elif re.search(r"north[-._ ]america", token, re.I):
            out["report_type"] = "North America Market Report"

        mloc = re.search(r"([A-Za-z.&\s]+?)[-._]([A-Z]{2})(?:[-._]|$)", token)
        if mloc:
            city = mloc.group(1).replace("-", " ").strip()
            state = mloc.group(2)
            out["location"] = f"United States/{state}/{city}"
        return out

    @staticmethod
    def _filename_for_entry(e: dict) -> str:
        year = str(e.get("year") or "").strip()
        q = (e.get("quarter") or "").strip()
        loc = (e.get("location") or "").replace("/", "-")
        rtyp = e.get("report_type") or "report"
        parts = [p for p in [year, q, loc, rtyp] if p]
        stem = "-".join(_slug(p) for p in parts) or "report"
        return f"{stem}.pdf"


def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-\/]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")
