from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig
import os


class ZoningOrdinanceLoadComponent(BaseComponent):
    """Component for loading embeddings into ChromaDB Cloud"""

    def __init__(self, city: str = None, collection_name: str = "zoning-ordinance"):
        """
        Initialize zoning ordinance load component.

        Args:
            city: City name to load data for (optional, loads all if None)
            collection_name: ChromaDB collection name
        """
        super().__init__()
        self.city = city
        self.collection_name = collection_name

        # Read ChromaDB credentials from environment
        self.chromadb_api_key = os.environ.get("CHROMADB_API_KEY", "")
        self.chromadb_tenant = os.environ.get("CHROMADB_TENANT", "")
        self.chromadb_database = os.environ.get("CHROMADB_DATABASE", "")

    def get_component_name(self):
        """Return the component name"""
        return "processor-zoning-ordinance-load"

    def get_component(self):
        """Return the KFP component for zoning ordinance ChromaDB loading"""
        city = self.city
        collection_name = self.collection_name
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT
        chromadb_api_key = self.chromadb_api_key
        chromadb_tenant = self.chromadb_tenant
        chromadb_database = self.chromadb_database

        @dsl.container_component
        def zoning_ordinance_load_component():
            city_arg = f"--city '{city}'" if city else ""
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export CHROMADB_API_KEY={chromadb_api_key} && "
                f"export CHROMADB_TENANT={chromadb_tenant} && "
                f"export CHROMADB_DATABASE={chromadb_database} && "
                f"/home/app/.venv/bin/python /app/zoning_ordinance_load/run.py "
                f"{city_arg} --collection '{collection_name}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.zoning_ordinance_load_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_ordinance_load_component
