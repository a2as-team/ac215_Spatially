from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class DevelopmentPlansCollectorComponent(BaseComponent):
    """Component for collecting development plans data"""

    def __init__(self, city: str):
        """
        Initialize development plans collector component.

        Args:
            city: City name to collect data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "collector-development-plans"

    def get_component(self):
        """Return the KFP component for development plans collection"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def development_plans_collector_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"/home/app/.venv/bin/python /app/development_plans/run.py --city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return development_plans_collector_component