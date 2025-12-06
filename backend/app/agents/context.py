"""Context for tracking agent execution data.

This module provides a way to store and retrieve data generated during
agent tool executions, such as ordinance query results that should be
passed back to the frontend.

Uses a simple global variable since tools may run in thread pools
where contextvars don't propagate properly.
"""

import threading
from typing import List, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrdinanceSource:
    """A single ordinance source from vector search."""
    title: str
    subtitle: str = ""
    zoning_codes: List[str] = field(default_factory=list)
    content: str = ""
    similarity_score: float = 0.0


@dataclass
class AgentContext:
    """Context data collected during agent execution."""
    ordinance_sources: List[OrdinanceSource] = field(default_factory=list)

    def clear(self):
        """Clear all context data."""
        self.ordinance_sources = []

    def add_ordinance_sources(self, results: List[Dict[str, Any]]):
        """Add ordinance sources from vector query results."""
        for result in results:
            source = OrdinanceSource(
                title=result.get("document_title", "Unknown"),
                subtitle=result.get("document_subtitle", ""),
                zoning_codes=result.get("zoning_codes", []),
                content=result.get("text_chunk", ""),
                similarity_score=result.get("similarity_score", 0.0),
            )
            self.ordinance_sources.append(source)
        logger.debug(f"AgentContext now has {len(self.ordinance_sources)} sources")

    def get_ordinance_sources_dict(self) -> List[Dict[str, Any]]:
        """Get ordinance sources as a list of dictionaries."""
        return [
            {
                "title": s.title,
                "subtitle": s.subtitle,
                "zoning_codes": s.zoning_codes,
                "content": s.content,
                "similarity_score": s.similarity_score,
            }
            for s in self.ordinance_sources
        ]


# Global context with thread lock for safety
# Using a simple global since FastAPI uses a single event loop
# and tools may run in thread pools where contextvars don't propagate
_global_context: AgentContext = AgentContext()
_context_lock = threading.Lock()


def get_agent_context() -> AgentContext:
    """Get the current agent context."""
    return _global_context


def clear_agent_context():
    """Clear the agent context."""
    with _context_lock:
        _global_context.clear()
    logger.debug("Agent context cleared")


def set_agent_context(context: AgentContext):
    """Set the agent context (replaces global)."""
    global _global_context
    with _context_lock:
        _global_context = context
