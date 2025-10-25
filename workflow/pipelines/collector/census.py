from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class CensusCollectorComponent(BaseComponent):
    """Component for collecting census data"""

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
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_collector_image(gcp_region, gcp_project)["image_uri"],
                command=["python", "/app/census/run.py"],
                # TODO: Make these arguments configurable
                args=["--city", city, "--type", "population", "--level", "tract", "--year", "2020", "--state", "IL", "--county", "", "--tract", ""],
            )
            return container_spec

        return census_collector_component
