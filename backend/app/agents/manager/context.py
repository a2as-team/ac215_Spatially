"""Base context management for agent execution.

This module provides the core abstractions for storing data generated during
agent tool executions. Specific data stores (ordinances, census, etc.) are
defined in the stores/ subdirectory.

Context is managed per-request using contextvars for async-safe isolation.
"""

from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import List, Dict, Any, TypeVar, Generic, Type
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SourceStore(ABC, Generic[T]):
    """Abstract base class for storing source data from tool executions.

    Subclass this to create stores for different data types
    (ordinances, census, development plans, etc.)

    Features:
    - Add sources from tool results
    - Cite specific sources to show to user (with highlights/reasons)
    - Only cited sources are returned in API response

    Example:
        class MySourceStore(SourceStore[MySource]):
            def __init__(self):
                super().__init__()
                self._sources: List[MySource] = []

            def add(self, results: List[Dict[str, Any]]) -> None:
                for result in results:
                    source = MySource(...)
                    self._sources.append(source)

            def get_all(self) -> List[MySource]:
                return self._sources

            def _source_to_dict(self, source: MySource, highlight: str, reason: str) -> Dict:
                return {"field": source.field, "highlight": highlight, "reason": reason}

            def clear(self) -> None:
                super().clear()
                self._sources = []
    """

    def __init__(self):
        # Track which sources are cited and their metadata
        self._cited: Dict[int, Dict[str, str]] = {}  # index -> {highlight, reason}

    @abstractmethod
    def add(self, results: List[Dict[str, Any]]) -> None:
        """Add results from a tool execution."""
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all stored items."""
        pass

    @abstractmethod
    def _source_to_dict(self, source: T, highlight: str, reason: str) -> Dict[str, Any]:
        """Convert a single source to dict for API response.

        Args:
            source: The source item
            highlight: Key excerpt to highlight (may be empty)
            reason: Why this source is relevant (may be empty)

        Returns:
            Dictionary representation of the source
        """
        pass

    def cite(
        self,
        indices: List[int],
        highlights: List[str] = None,
        reasons: List[str] = None,
    ) -> str:
        """Cite specific sources to show to the user.

        Args:
            indices: 0-based indices of sources to cite
            highlights: Key excerpts to highlight for each source
            reasons: Why each source is relevant

        Returns:
            Confirmation message.
        """
        sources = self.get_all()
        if not sources:
            return "No sources available to cite."

        highlights = highlights or []
        reasons = reasons or []
        cited_count = 0

        for i, idx in enumerate(indices):
            if 0 <= idx < len(sources):
                self._cited[idx] = {
                    "highlight": highlights[i] if i < len(highlights) else "",
                    "reason": reasons[i] if i < len(reasons) else "",
                }
                cited_count += 1

        logger.debug(f"Cited {cited_count} sources. Total cited: {len(self._cited)}")
        return f"Cited {cited_count} sources to show to user."

    def cite_recent(self, count: int = 5, reason: str = "") -> str:
        """Cite the most recent sources.

        Args:
            count: Number of most recent sources to cite
            reason: Why these sources are relevant (applies to all)

        Returns:
            Confirmation message.
        """
        sources = self.get_all()
        if not sources:
            return "No sources available to cite."

        start_idx = max(0, len(sources) - count)
        indices = list(range(start_idx, len(sources)))
        reasons = [reason] * len(indices) if reason else []

        return self.cite(indices, reasons=reasons)

    def get_cited(self) -> List[T]:
        """Get only the cited sources."""
        sources = self.get_all()
        return [sources[i] for i in sorted(self._cited.keys()) if i < len(sources)]

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert cited sources to dict list for API response."""
        sources = self.get_all()
        result = []
        for idx in sorted(self._cited.keys()):
            if idx < len(sources):
                meta = self._cited[idx]
                result.append(self._source_to_dict(
                    sources[idx],
                    highlight=meta.get("highlight", ""),
                    reason=meta.get("reason", ""),
                ))
        return result

    def clear(self) -> None:
        """Clear cited sources. Subclasses should also clear their _sources list."""
        self._cited = {}

    def __len__(self) -> int:
        return len(self.get_all())


class AgentContext:
    """Context data collected during agent execution.

    Provides modular stores for different data types. Stores are
    registered and accessed by name, allowing easy extension.

    Usage:
        context = get_current_context()

        # Register a store (usually done once at module import)
        context.register_store("ordinances", OrdinanceSourceStore)

        # Get a store and add data
        context.get_store("ordinances").add(results)

        # Or use the convenience property (if defined)
        context.ordinances.add(results)

        # Get all sources for API response
        response = context.to_dict()
    """

    # Class-level registry of store factories
    _store_registry: Dict[str, Type[SourceStore]] = {}

    @classmethod
    def register_store_type(cls, name: str, store_class: Type[SourceStore]):
        """Register a store type globally.

        Args:
            name: Store name (e.g., "ordinances", "census")
            store_class: SourceStore subclass to instantiate
        """
        cls._store_registry[name] = store_class
        logger.debug(f"Registered store type: {name}")

    def __init__(self):
        self._stores: Dict[str, SourceStore] = {}

    def get_store(self, name: str) -> SourceStore:
        """Get or create a store by name.

        Args:
            name: Store name (must be registered via register_store_type)

        Returns:
            The store instance

        Raises:
            KeyError: If store type is not registered
        """
        if name not in self._stores:
            if name not in self._store_registry:
                raise KeyError(f"Store type '{name}' not registered. "
                             f"Available: {list(self._store_registry.keys())}")
            self._stores[name] = self._store_registry[name]()
        return self._stores[name]

    def clear(self):
        """Clear all stores."""
        for store in self._stores.values():
            store.clear()
        logger.debug("AgentContext cleared all stores")

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert all stores to a dictionary for API response."""
        return {
            name: store.to_dict_list()
            for name, store in self._stores.items()
            if len(store) > 0
        }


# --- Context Variable for async-safe access ---

_current_context: ContextVar[AgentContext] = ContextVar("agent_context", default=None)


def set_current_context(context: AgentContext):
    """Set the current context for tool execution.

    Called by SmartDataAgentRunner before running the agent.
    Tools access it via get_current_context().

    Uses contextvars for async-safe isolation between concurrent requests.
    """
    _current_context.set(context)
    logger.debug("Current context set for this async task")


def get_current_context() -> AgentContext:
    """Get the current context for tool execution.

    Returns:
        The current AgentContext, or a new one if not set.

    Uses contextvars so each async request gets its own context.
    """
    context = _current_context.get()
    if context is None:
        logger.warning("No context set, creating temporary context")
        context = AgentContext()
        _current_context.set(context)
    return context


def clear_current_context():
    """Clear the current context."""
    context = _current_context.get()
    if context is not None:
        context.clear()
    logger.debug("Current context cleared")
