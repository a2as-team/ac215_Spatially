from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class DevelopmentPlansLabelStudioProcessorComponent(BaseComponent):
    """Component for processing development plans data in Label Studio"""

    def get_component_name(self):
        """Return the component name"""
        return "processor-development-plans-label-studio"

    def get_component(self):
        """Return the KFP component for development plans Label Studio processing"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def development_plans_label_studio_processor_component():
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_processor_image(gcp_region, gcp_project)["image_uri"],
                command=["python", "/app/development_plans_label_studio/run.py"],
                args=["--city", city],
            )
            return container_spec

        return development_plans_label_studio_processor_component