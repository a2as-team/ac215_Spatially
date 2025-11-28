from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningCodesCollectorComponent(BaseComponent):
    """Component for collecting zoning codes data from Zoneomics.

    Uses the Playwright-based collector image for better compatibility
    with Next.js and bot-protected sites.
    """

    def __init__(self, source: str = "zoneomics", test_mode: bool = False):
        """
        Initialize zoning codes collector component.

        Args:
            source: Data source to collect from (default: "zoneomics")
            test_mode: If True, only process first state for testing
        """
        super().__init__()
        self.source = source
        self.test_mode = test_mode

    def get_component_name(self):
        """Return the component name"""
        return "collector-zoning-codes"

    def get_component(self):
        """Return the KFP component for zoning codes collection"""
        source = self.source
        test_mode = self.test_mode
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def zoning_codes_collector_component():
            test_mode_flag = "--test-mode" if test_mode else ""
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export APP_DB_NAME={self.APP_DB_NAME} && "
                f"export POSTGRE_HOST={self.POSTGRE_HOST} && "
                f"export POSTGRE_PORT={self.POSTGRE_PORT} && "
                f"export POSTGRE_USER={self.POSTGRE_USER} && "
                f"export POSTGRE_PASSWORD={self.POSTGRE_PASSWORD} && "
                f"/home/pwuser/.venv/bin/python /app/zoning_codes/run.py "
                f"--source '{source}' {test_mode_flag}"
            )
            container_spec = dsl.ContainerSpec(
                # Use Playwright-based image for Next.js compatibility
                image=RegistryConfig.data_collector_playwright_image(
                    gcp_region, gcp_project
                )["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return zoning_codes_collector_component
