from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip

from pipelines.collector.zoning_codes import ZoningCodesCollectorComponent


class ZoningCodesParallelPipeline(BasePipeline):
    """Pipeline for collecting zoning codes from all US states in parallel.

    This pipeline launches up to 50 parallel tasks (one per state) to dramatically
    speed up the collection process. Each state task uses concurrent workers
    internally to process cities in parallel.

    Performance:
    - Sequential (old): ~50 states * ~100 cities/state * ~10s/city = ~14 hours
    - Parallel (new): ~50 parallel jobs * ~100 cities / 4 workers * ~10s/city = ~4 minutes per state
    """

    def __init__(
        self,
        test_mode: bool = False,
        max_workers: int = 4,
        states: list[str] = None,
    ):
        """
        Initialize the parallel zoning codes pipeline.

        Args:
            test_mode: If True, only process limited cities per state
            max_workers: Number of concurrent workers per state (default: 4)
            states: List of state slugs to process. If None, processes all 50 states.
        """
        super().__init__()
        self.pipeline_name = "zoning-codes-parallel"
        self.test_mode = test_mode
        self.max_workers = max_workers
        self.states = states or ZoningCodesCollectorComponent.US_STATE_SLUGS

    def create_pipeline(self):
        """Create a pipeline that runs all state collectors in parallel"""
        test_mode = self.test_mode
        max_workers = self.max_workers
        states = self.states

        # Create components for each state
        state_components = {}
        for state_slug in states:
            component = ZoningCodesCollectorComponent(
                source="zoneomics",
                test_mode=test_mode,
                state_slug=state_slug,
                max_workers=max_workers,
            )
            state_components[state_slug] = component.get_component()

        @dsl.pipeline(name=f"{self.pipeline_name}-pipeline")
        def zoning_codes_parallel_pipeline():
            # Launch all states in parallel - no dependencies between them
            for state_slug, component in state_components.items():
                (
                    component()
                    .set_display_name(f"zoning-codes-{state_slug}")
                    .set_cpu_limit("4000m")  # 4 CPUs for concurrent workers
                    .set_memory_limit("12G")  # 12G for multiple Playwright instances
                )

        return zoning_codes_parallel_pipeline

    def run(self):
        """Compile and submit the pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile the pipeline
        num_states = len(self.states)
        pipeline_file = self.pipeline_outputs_dir / f"{self.pipeline_name}_{num_states}states.yaml"
        compiler.Compiler().compile(pipeline, package_path=str(pipeline_file))

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Create and submit the job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{self.pipeline_name}-{num_states}states-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=str(pipeline_file),
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        print(f"Processing {num_states} states in parallel")
        print(f"Workers per state: {self.max_workers}")
        print(f"Test mode: {self.test_mode}")

        return job
