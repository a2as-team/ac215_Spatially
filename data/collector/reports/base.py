from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from typing import Iterator, Optional
import time


@dataclass
class ReportItem:
    """Represents a single report item with metadata."""
    url: str
    title: str
    report_type: str
    location: str
    year: int
    quarter: Optional[str] = None
    extra: Optional[dict] = None


class BaseReportCollector:
    """Base class for report collectors."""
    
    def __init__(self):
        self.session = None
    
    def _fetch(self, url: str) -> str:
        """Fetch HTML content from URL with basic error handling."""
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def fetch_select_options(self) -> dict:
        """Fetch and return select options for filtering reports."""
        # Default implementation - can be overridden by subclasses
        return {}
    
    def iter_reports(self, limit: Optional[int] = None) -> Iterator[ReportItem]:
        """Iterate through all available reports."""
        count = 0
        for page_url in self._iter_report_pages():
            for item in self._parse_report_links(page_url):
                if limit and count >= limit:
                    return
                yield item
                count += 1
    
    def _iter_report_pages(self) -> Iterator[str]:
        """Iterate through pagination URLs. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def _parse_report_links(self, html_url: str) -> Iterator[ReportItem]:
        """Parse report links from HTML page. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def download_all(self, dest_dir: str, dry_run: bool = False) -> list[str]:
        """Download all reports to destination directory."""
        downloaded_files = []
        os.makedirs(dest_dir, exist_ok=True)
        
        for item in self.iter_reports():
            filename = self._generate_filename(item)
            filepath = os.path.join(dest_dir, filename)
            
            if dry_run:
                print(f"Would download: {item.title} -> {filepath}")
                downloaded_files.append(filepath)
            else:
                try:
                    self._download_file(item.url, filepath)
                    print(f"Downloaded: {item.title} -> {filepath}")
                    downloaded_files.append(filepath)
                    # Add small delay to be respectful to the server
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Failed to download {item.url}: {e}")
        
        return downloaded_files
    
    def _generate_filename(self, item: ReportItem) -> str:
        """Generate filename for report item."""
        # Clean up title for filename
        safe_title = "".join(c for c in item.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        return f"{item.year}_{item.quarter or 'Q0'}_{safe_title}.pdf"
    
    def _download_file(self, url: str, filepath: str):
        """Download file from URL to filepath."""
        with urllib.request.urlopen(url) as response:
            with open(filepath, 'wb') as f:
                f.write(response.read())

