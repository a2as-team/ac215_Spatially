from __future__ import annotations

from typing import List, Optional

from .lee_and_associates import LeeAndAssociatesCollector


class ReportsCollector:
    """Dispatcher for multiple report sources (extensible)."""

    def __init__(self):
        self.caller_map = {
            "lee_and_associates": LeeAndAssociatesCollector(),
        }

    def options(self, source: str, limit: Optional[int] = None) -> dict:
        return self.caller_map[source].get_select_options(limit=limit)

    def list_urls(self, source: str, **filters) -> List[str]:
        return self.caller_map[source].list_urls_for(**filters)

    def download(self, source: str, dest_root: str, **filters) -> List[str]:
        return self.caller_map[source].download_for_options(dest_root=dest_root, **filters)
