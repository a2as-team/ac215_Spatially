"""Zoning ordinance source store.

Stores zoning ordinance data retrieved from vector search during agent execution.
The agent can cite specific sources to show to the user with highlighted excerpts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import logging

from ..context import SourceStore, AgentContext

logger = logging.getLogger(__name__)


@dataclass
class OrdinanceSource:
    """A single ordinance source from vector search."""
    title: str
    subtitle: str = ""
    zoning_codes: List[str] = field(default_factory=list)
    content: str = ""
    similarity_score: float = 0.0


class OrdinanceSourceStore(SourceStore[OrdinanceSource]):
    """Store for zoning ordinance sources.

    Sources are stored when retrieved, but only cited sources
    are returned to the user. The agent decides which sources
    are relevant via the cite() method.
    """

    def __init__(self):
        super().__init__()
        self._sources: List[OrdinanceSource] = []

    def add(self, results: List[Dict[str, Any]]) -> None:
        """Add ordinance sources from vector query results."""
        for result in results:
            source = OrdinanceSource(
                title=result.get("document_title", "Unknown"),
                subtitle=result.get("document_subtitle", ""),
                zoning_codes=result.get("zoning_codes", []),
                content=result.get("text_chunk", ""),
                similarity_score=result.get("similarity_score", 0.0),
            )
            self._sources.append(source)
        logger.debug(f"OrdinanceSourceStore now has {len(self._sources)} sources")

    def get_all(self) -> List[OrdinanceSource]:
        """Get all retrieved sources."""
        return self._sources

    def _source_to_dict(self, source: OrdinanceSource, highlight: str, reason: str) -> Dict[str, Any]:
        """Convert a single source to dict for API response."""
        return {
            "title": source.title,
            "subtitle": source.subtitle,
            "zoning_codes": source.zoning_codes,
            "content": source.content,
            "similarity_score": source.similarity_score,
            "highlight": highlight,
            "reason": reason,
        }

    def clear(self) -> None:
        super().clear()
        self._sources = []


# Register this store type with AgentContext
AgentContext.register_store_type("ordinances", OrdinanceSourceStore)
