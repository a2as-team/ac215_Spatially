"""Generic tool for agent to cite sources to show to the user.

This tool works with any registered store type (ordinances, development_plans, etc.)
"""

from typing import List, Optional
import logging

from app.agents.manager import get_current_context

logger = logging.getLogger(__name__)


def cite_sources(
    store_name: str,
    source_indices: List[int],
    highlights: Optional[List[str]] = None,
    reasons: Optional[List[str]] = None,
) -> str:
    """
    Cite specific sources to show to the user.

    Use this tool AFTER querying data to mark which sources should be
    displayed to the user in the sidebar. Only cited sources will be shown.

    IMPORTANT: You should cite sources when:
    - The source text directly answers the user's question
    - You want to provide official documentation as reference
    - The user might want to read the original text

    You should NOT cite sources when:
    - The query was just for your internal understanding
    - The results weren't relevant to the user's question
    - You're doing follow-up queries to find specific details

    Args:
        store_name: Name of the store ("ordinances", "development_plans", etc.)
        source_indices: 0-based indices of sources to cite.
                       Index 0 is the first result, 1 is the second, etc.
        highlights: Optional key excerpts to highlight for each source.
                   Quote the most important sentence that answers the question.
        reasons: Optional brief explanations of why each source is relevant.

    Returns:
        Confirmation message.

    Example:
        After querying zoning ordinances about height limits:

        cite_sources(
            store_name="ordinances",
            source_indices=[0, 2],
            highlights=["Maximum height shall be 35 feet", "Height measured from grade"],
            reasons=["Defines max height", "Explains measurement"]
        )
    """
    try:
        context = get_current_context()
        store = context.get_store(store_name)
        return store.cite(source_indices, highlights, reasons)
    except KeyError as e:
        logger.error(f"Store not found: {e}")
        return f"Error: Store '{store_name}' not found."
    except Exception as e:
        logger.error(f"Error citing sources: {e}")
        return f"Error citing sources: {str(e)}"


def cite_recent_sources(
    store_name: str,
    count: int = 5,
    reason: Optional[str] = None,
) -> str:
    """
    Cite the most recent sources from a store to show to the user.

    Use this as a simpler alternative when all recent query results are relevant.

    Args:
        store_name: Name of the store ("ordinances", "development_plans", etc.)
        count: Number of most recent sources to cite (default: 5)
        reason: Brief explanation of why these sources are relevant

    Returns:
        Confirmation message.

    Example:
        cite_recent_sources(
            store_name="ordinances",
            count=3,
            reason="Height and setback regulations"
        )
    """
    try:
        context = get_current_context()
        store = context.get_store(store_name)
        return store.cite_recent(count, reason or "")
    except KeyError as e:
        logger.error(f"Store not found: {e}")
        return f"Error: Store '{store_name}' not found."
    except Exception as e:
        logger.error(f"Error citing sources: {e}")
        return f"Error citing sources: {str(e)}"
