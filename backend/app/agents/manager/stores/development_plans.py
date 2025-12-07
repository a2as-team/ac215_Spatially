"""Development plans source store.

Stores development plan data retrieved from vector search during agent execution.
The agent can cite specific sources to show to the user with highlighted excerpts.
Includes geojson location data for map display.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from ..context import SourceStore, AgentContext

logger = logging.getLogger(__name__)


@dataclass
class DevelopmentPlanSource:
    """A single development plan source from vector search."""
    project_name: str
    file_name: str = ""
    text_chunk: str = ""
    zoning_codes: List[str] = field(default_factory=list)
    article_reference: List[str] = field(default_factory=list)
    location_context: str = ""
    similarity_score: float = 0.0
    distance_km: Optional[float] = None
    # Location data from metadata for map display
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DevelopmentPlanSourceStore(SourceStore[DevelopmentPlanSource]):
    """Store for development plan sources.

    Sources are stored when retrieved, but only cited sources
    are returned to the user. The agent decides which sources
    are relevant via the cite() method.

    Includes geojson point data for displaying plan locations on the map.
    """

    def __init__(self):
        super().__init__()
        self._sources: List[DevelopmentPlanSource] = []

    def add(self, results: List[Dict[str, Any]]) -> None:
        """Add development plan sources from vector query results.

        Location data is extracted from the 'metadata' JSONB field which
        contains 'latitude' and 'longitude' keys.
        """
        for result in results:
            # Extract latitude/longitude from metadata JSONB
            metadata = result.get("metadata", {}) or {}
            latitude = None
            longitude = None

            if isinstance(metadata, dict):
                lat_val = metadata.get("latitude")
                lon_val = metadata.get("longitude")
                if lat_val is not None:
                    try:
                        latitude = float(lat_val)
                    except (ValueError, TypeError):
                        pass
                if lon_val is not None:
                    try:
                        longitude = float(lon_val)
                    except (ValueError, TypeError):
                        pass

            source = DevelopmentPlanSource(
                project_name=result.get("project_name", "Unknown Project"),
                file_name=result.get("file_name", ""),
                text_chunk=result.get("text_chunk", ""),
                zoning_codes=result.get("zoning_codes", []) or [],
                article_reference=result.get("article_reference", []) or [],
                location_context=result.get("location_context", ""),
                similarity_score=result.get("similarity_score", 0.0),
                distance_km=result.get("distance_km"),
                latitude=latitude,
                longitude=longitude,
            )
            self._sources.append(source)
        logger.debug(f"DevelopmentPlanSourceStore now has {len(self._sources)} sources")

    def get_all(self) -> List[DevelopmentPlanSource]:
        """Get all retrieved sources."""
        return self._sources

    def _source_to_dict(self, source: DevelopmentPlanSource, highlight: str, reason: str) -> Dict[str, Any]:
        """Convert a single source to dict for API response."""
        result = {
            "title": source.project_name,
            "subtitle": source.file_name,
            "content": source.text_chunk,
            "zoning_codes": source.zoning_codes,
            "article_reference": source.article_reference,
            "similarity_score": source.similarity_score,
            "highlight": highlight,
            "reason": reason,
        }

        # Add distance if available
        if source.distance_km is not None:
            result["distance_km"] = source.distance_km

        # Add geojson point if location is available
        if source.latitude is not None and source.longitude is not None:
            result["geojson"] = {
                "type": "Point",
                "coordinates": [source.longitude, source.latitude]
            }
            result["latitude"] = source.latitude
            result["longitude"] = source.longitude

        return result

    def clear(self) -> None:
        super().clear()
        self._sources = []


# Register this store type with AgentContext
AgentContext.register_store_type("development_plans", DevelopmentPlanSourceStore)
