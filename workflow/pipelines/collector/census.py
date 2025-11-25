from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class CensusCollectorComponent(BaseComponent):
    """Component for collecting census data"""

    def __init__(self, city: str):
        """
        Initialize census collector component.

        Args:
            city: City name to collect data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "collector-census"

    def get_component(self):
        """Return the KFP component for census collection"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def census_collector_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"/home/app/.venv/bin/python /app/census/run.py "
                f"--city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return census_collector_component
