from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class ZoningCodesCollectorComponent(BaseComponent):
    """Component for collecting zoning codes data from Zoneomics.

    Uses the Playwright-based collector image for better compatibility
    with Next.js and bot-protected sites.

    Supports:
    - Single state processing via state_slug parameter
    - Concurrent city processing via max_workers parameter
    - Test mode for quick validation
    """

    # All US state slugs for parallel pipeline
    US_STATE_SLUGS = [
        "alabama", "alaska", "arizona", "arkansas", "california",
        "colorado", "connecticut", "delaware", "florida", "georgia",
        "hawaii", "idaho", "illinois", "indiana", "iowa",
        "kansas", "kentucky", "louisiana", "maine", "maryland",
        "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
        "montana", "nebraska", "nevada", "new-hampshire", "new-jersey",
        "new-mexico", "new-york", "north-carolina", "north-dakota", "ohio",
        "oklahoma", "oregon", "pennsylvania", "rhode-island", "south-carolina",
        "south-dakota", "tennessee", "texas", "utah", "vermont",
        "virginia", "washington", "west-virginia", "wisconsin", "wyoming",
    ]

    def __init__(
        self,
        source: str = "zoneomics",
        test_mode: bool = False,
        state_slug: str = None,
        max_workers: int = 4,
    ):
        """
        Initialize zoning codes collector component.

        Args:
            source: Data source to collect from (default: "zoneomics")
            test_mode: If True, only process first state with limited cities
            state_slug: If provided, only process this specific state (e.g., "california")
            max_workers: Number of concurrent workers for processing cities (default: 4)
        """
        super().__init__()
        self.source = source
        self.test_mode = test_mode
        self.state_slug = state_slug
        self.max_workers = max_workers

    def get_component_name(self):
        """Return the component name"""
        if self.state_slug:
            return f"collector-zoning-codes-{self.state_slug}"
        return "collector-zoning-codes"

    def get_component(self):
        """Return the KFP component for zoning codes collection"""
        source = self.source
        test_mode = self.test_mode
        state_slug = self.state_slug
        max_workers = self.max_workers
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def zoning_codes_collector_component():
            # Build command flags
            flags = []
            if test_mode:
                flags.append("--test-mode")
            if state_slug:
                flags.append(f"--state '{state_slug}'")
            flags.append(f"--max-workers {max_workers}")
            flags_str = " ".join(flags)

            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"export APP_DB_NAME={self.APP_DB_NAME} && "
                f"export POSTGRE_HOST={self.POSTGRE_HOST} && "
                f"export POSTGRE_PORT={self.POSTGRE_PORT} && "
                f"export POSTGRE_USER={self.POSTGRE_USER} && "
                f"export POSTGRE_PASSWORD={self.POSTGRE_PASSWORD} && "
                f"/home/pwuser/.venv/bin/python /app/zoning_codes/run.py "
                f"--source '{source}' {flags_str}"
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
