"""Tool creator for citing sources."""

from typing import Callable, List, Optional
from app.agents.tools.functions import cite_sources, cite_recent_sources


def create_cite_sources_tool() -> Callable:
    """
    Create a tool for the agent to cite sources.

    Returns:
        A callable tool function for citing sources.
    """

    def cite(
        store_name: str,
        source_indices: List[int],
        highlights: Optional[List[str]] = None,
        reasons: Optional[List[str]] = None,
    ) -> str:
        """Cite specific sources to show to the user in the sidebar.

        Use this AFTER querying data to mark which results should be displayed.
        Only cited sources will be shown to the user.

        WHEN TO CITE:
        - The source directly answers the user's question
        - You want to show official documentation as reference
        - The text contains specific numbers, limits, or requirements

        WHEN NOT TO CITE:
        - The query was for your own understanding
        - Results weren't relevant to the question
        - You're doing follow-up queries for details

        Args:
            store_name: "ordinances" for zoning, "development_plans" for projects
            source_indices: 0-based indices (0=first result, 1=second, etc.)
            highlights: Key excerpts to highlight - quote the important part
            reasons: Brief explanation of why each source matters

        Example:
            cite(
                store_name="ordinances",
                source_indices=[0, 2],
                highlights=["Maximum height: 35 feet", "Setback: 10 feet"],
                reasons=["Height limit", "Required setback"]
            )
        """
        return cite_sources(store_name, source_indices, highlights, reasons)

    cite.__name__ = "cite_sources"
    return cite
