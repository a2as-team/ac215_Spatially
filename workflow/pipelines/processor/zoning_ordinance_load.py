from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig
import os


class ZoningOrdinanceLoadComponent(BaseComponent):
    """Component for loading embeddings into Milvus Cloud"""

    def __init__(self, city: str = None, collection_name: str = "zoning_ordinance"):
        """
        Initialize zoning ordinance load component.

        Args:
            city: City name to load data for (optional, loads all if None)
            collection_name: Milvus collection name
        """
        super().__init__()
        self.city = city
        self.collection_name = collection_name

        # Read Milvus credentials from environment
        self.milvus_uri = os.environ.get("MILVUS_PUBLIC_ENDPOINT", "")
        self.milvus_token = os.environ.get("MILVUS_API_KEY", "")

    def get_component_name(self):
        """Return the component name"""
        return "processor-zoning-ordinance-load"

    def get_component(self):
        """Return the KFP component for zoning ordinance Milvus loading"""
        city = self.city
        collection_name = self.collection_name
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT
        milvus_uri = self.milvus_uri
        milvus_token = self.milvus_token

        @dsl.container_component
        def zoning_ordinance_load_component():
            city_arg = f"--city '{city}'" if city else ""
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export MILVUS_PUBLIC_ENDPOINT={milvus_uri} && "
                f"export MILVUS_API_KEY={milvus_token} && "
                f"/home/app/.venv/bin/python /app/zoning_ordinance_load/run.py "
                f"{city_arg} --collection '{collection_name}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.zoning_ordinance_load_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_ordinance_load_component
