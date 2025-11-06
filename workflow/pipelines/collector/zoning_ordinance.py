from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningOrdinanceCollectorComponent(BaseComponent):
    """Component for collecting zoning ordinance data"""

    def __init__(self, city: str):
        """
        Initialize zoning ordinance collector component.

        Args:
            city: City name to collect data for (e.g., "boston", "chicago")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "collector-zoning-ordinance"

    def get_component(self):
        """Return the KFP component for zoning ordinance collection"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def zoning_ordinance_collector_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"/home/app/.venv/bin/python /app/zoning_ordinance/run.py --city '{city}' --headless true --download_dir '/app/downloads/zoning_ordinance/{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_ordinance_collector_component
