from __future__ import annotations

import os
import re
import time
import pathlib
from abc import ABC, abstractmethod
from typing import Callable, Iterable, List, Optional, Union


class BaseReportCollector(ABC):
    """
    Minimal, generic base for *any* report source.
    - Does NOT assume pagination, HTML, or a specific data model.
    - Provides a common downloader for a list of URLs.
    - Subclasses must implement `get_downloadable_file_urls()`.
    - Subclasses may implement `get_select_options()` if the source supports options.
    - Subclasses can also expose convenience methods like `list_urls_for(...)`.
    """

    def __init__(self, polite_delay_sec: float = 0.5):
        self.polite_delay_sec = polite_delay_sec

    # ---------- Required ----------
    @abstractmethod
    def get_downloadable_file_urls(self, limit: Optional[int] = None) -> List[str]:
        """Return a list of downloadable file URLs (typically PDFs)."""
        raise NotImplementedError

    # ---------- Optional (per-source) ----------
    def get_select_options(self, limit: Optional[int] = None) -> dict:
        """Return available select options (e.g., report_types/locations/years) if applicable."""
        raise NotImplementedError("This source does not expose select options.")

    # ---------- Common utility ----------
    def download_urls(
        self,
        urls: Iterable[str],
        dest_dir: Union[str, os.PathLike],
        filename_fn: Optional[Callable[[str], str]] = None,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Download a set of URLs into `dest_dir`. Returns list of local filepaths.
        - `filename_fn(url) -> str` lets subclasses decide filenames; default uses the URL basename.
        - No assumptions about metadata; suitable for sources without pages/options.
        """
        import urllib.request

        outdir = pathlib.Path(dest_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        saved: List[str] = []

        for url in urls:
            fname = filename_fn(url) if filename_fn else _basename(url)
            outpath = outdir / fname
            if dry_run:
                print(f"Would download: {url} -> {outpath}")
                saved.append(str(outpath))
                continue

            try:
                with urllib.request.urlopen(url) as r, open(outpath, "wb") as f:
                    f.write(r.read())
                saved.append(str(outpath))
                time.sleep(self.polite_delay_sec)
            except Exception as e:
                print(f"Failed to download {url}: {e}")
        return saved


def _basename(url: str) -> str:
    name = url.split("/")[-1]
    name = re.sub(r"[^\w.\-]+", "-", name)
    return name
