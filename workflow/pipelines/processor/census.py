from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class CensusProcessorComponent(BaseComponent):
    """Component for processing census data and ingesting into database"""

    def __init__(self, city: str):
        """
        Initialize census processor component.

        Args:
            city: City name to process data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "processor-census"

    def get_component(self):
        """Return the KFP component for census processing"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT
        app_db_name = self.APP_DB_NAME
        postgre_user = self.POSTGRE_USER
        postgre_password = self.POSTGRE_PASSWORD
        postgre_host = self.POSTGRE_HOST
        postgre_port = self.POSTGRE_PORT

        @dsl.container_component
        def census_processor_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export GCP_REGION={gcp_region} && "
                f"export APP_DB_NAME={app_db_name} && "
                f"export POSTGRE_USER={postgre_user} && "
                f"export POSTGRE_PASSWORD={postgre_password} && "
                f"export POSTGRE_HOST={postgre_host} && "
                f"export POSTGRE_PORT={postgre_port} && "
                f"/home/app/.venv/bin/python /app/census/run.py "
                f"--city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_processor_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return census_processor_component
