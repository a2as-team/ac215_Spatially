from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningOrdinanceProcessorComponent(BaseComponent):
    """Component for converting DOCX to markdown, chunking and generating embeddings for zoning ordinance data"""

    def __init__(self, city: str):
        """
        Initialize zoning ordinance embed component.

        Args:
            city: City name to process data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.city = city

    def get_component_name(self):
        """Return the component name"""
        return "processor-zoning-ordinance-embed"

    def get_component(self):
        """Return the KFP component for zoning ordinance embedding"""
        city = self.city
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT
        app_db_name = self.APP_DB_NAME
        postgre_user = self.POSTGRE_USER
        postgre_password = self.POSTGRE_PASSWORD
        postgre_host = self.POSTGRE_HOST
        postgre_port = self.POSTGRE_PORT

        @dsl.container_component
        def zoning_ordinance_embed_component():
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export GCP_REGION={gcp_region} && "
                f"export APP_DB_NAME={app_db_name} && "
                f"export POSTGRE_USER={postgre_user} && "
                f"export POSTGRE_PASSWORD={postgre_password} && "
                f"export POSTGRE_HOST={postgre_host} && "
                f"export POSTGRE_PORT={postgre_port} && "
                f"/home/app/.venv/bin/python /app/zoning_ordinance_embed/run.py --city '{city}'"
            )
            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.data_processor_image(gcp_region, gcp_project)[
                    "image_uri"
                ],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_ordinance_embed_component
