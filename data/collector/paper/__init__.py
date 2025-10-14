# collector/paper/__init__.py
from __future__ import annotations
from typing import Optional, Dict, Type
from .mdpi import MDPICollector

class PaperCollector:
    # registry maps provider name -> collector class (not instance)
    registry: Dict[str, Type[MDPICollector]] = {
        "mdpi": MDPICollector,
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
    ):
        """
        Dispatch to the appropriate provider collector.

        For MDPI:
          - `journal` is the MDPI journal slug (e.g., 'land', 'sensors').
          - `query` optional keyword; if None, dumps latest.
          - `pages` number of search/listing pages to walk.
        """
        provider = provider.lower()
        if provider not in self.registry:
            raise ValueError(f"Unknown provider '{provider}'. Available: {list(self.registry)}")

        CollectorCls = self.registry[provider]
        out_dir = out_dir or f"downloads/{provider}/{journal}"

        collector = CollectorCls(
            journal=journal,
            out_dir=out_dir,
            headless=headless,
            per_page_timeout_s=per_page_timeout_s,
            polite_sleep_s=polite_sleep_s,
            download_wait_s=download_wait_s,
        )
        collector.collect(query=query, max_pages = pages)