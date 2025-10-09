# data/collector/paper/__init__.py
from __future__ import annotations
from typing import Optional, Dict, Type

from .mdpi import MDPICollector
from .taylorfrancis import TaylorFrancisCollector

class PaperCollector:
    registry: Dict[str, Type] = {
        "mdpi": MDPICollector,
        "tfo": TaylorFrancisCollector,
    }

    def collect(
        self,
        provider: str = "mdpi",
        *,
        journal: str = "land",
        query: Optional[str] = None,
        pages: int = 1,
        out_dir: Optional[str] = None,
        headless: bool = True,
        per_page_timeout_s: int = 25,
        polite_sleep_s: float = 1.2,
        download_wait_s: int = 90,
        # TFO-specific:
        journal_code: Optional[str] = None,
        from_year: int = 2013,
        to_year: int = 2025,
        debugger: Optional[str] = None,
    ):
        provider = provider.lower()
        if provider not in self.registry:
            raise ValueError(f"Unknown provider '{provider}'. Available: {list(self.registry)}")

        CollectorCls = self.registry[provider]
        out_dir = out_dir or f"downloads/{provider}/{journal or journal_code or 'journal'}"

        if provider == "mdpi":
            collector = CollectorCls(
                journal=journal,
                out_dir=out_dir,
                headless=headless,
                per_page_timeout_s=per_page_timeout_s,
                polite_sleep_s=polite_sleep_s,
                download_wait_s=download_wait_s,
            )
            return collector.collect(query=query, max_pages=pages)

        if provider == "tfo":
            collector = CollectorCls(
                journal_code=(journal_code or "rupt20"),
                from_year=from_year,
                to_year=to_year,
                debugger_address=debugger,
                headless=headless,
                out_dir=out_dir,
                per_page_timeout_s=per_page_timeout_s,
                polite_sleep_s=polite_sleep_s,
                download_wait_s=download_wait_s,
            )
            # query/pages not used for tfo
            return collector.collect(query=None, max_pages=1)
