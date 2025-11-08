from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningMapsCollectorComponent(BaseComponent):
    """Component for collecting zoning maps data"""

    def __init__(self, city: str):
        """
        Initialize zoning maps collector component.

        Args:
            city: City name to collect data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "collector-zoning-maps"

    def get_component(self):
        """Return the KFP component for zoning maps collection"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def zoning_maps_collector_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export APP_DB_NAME={self.APP_DB_NAME} && "
                f"export POSTGRE_USER={self.POSTGRE_USER} && "
                f"export POSTGRE_PASSWORD={self.POSTGRE_PASSWORD} && "
                f"export POSTGRE_HOST={self.POSTGRE_HOST} && "
                f"export POSTGRE_PORT={self.POSTGRE_PORT} && "
                f"/home/app/.venv/bin/python /app/zoning_maps/run.py --city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_maps_collector_component
