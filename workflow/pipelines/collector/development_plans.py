from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class DevelopmentPlansCollectorComponent(BaseComponent):
    """Component for collecting development plans data"""

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
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["python", "/app/development_plans/run.py"],
                args=["--city", city],
            )
            return container_spec

        return development_plans_collector_component