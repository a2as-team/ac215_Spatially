from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningOrdinanceChunkEmbedComponent(BaseComponent):
    """Component for chunking and generating embeddings for zoning ordinance data"""

    def __init__(self, city: str):
        """
        Initialize zoning ordinance chunk-embed component.

        Args:
            city: City name to process data for (e.g., "boston", "chicago")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "processor-zoning-ordinance-chunk-embed"

    def get_component(self):
        """Return the KFP component for zoning ordinance chunking and embedding"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def zoning_ordinance_chunk_embed_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"/home/app/.venv/bin/python /app/zoning_ordinance_chunk_embed/run.py --city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.zoning_ordinance_chunk_embed_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_ordinance_chunk_embed_component
