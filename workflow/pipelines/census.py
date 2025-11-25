from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip

# Import census collector and processor components
from pipelines.collector.census import CensusCollectorComponent
from pipelines.processor.census import CensusProcessorComponent


class CensusPipeline(BasePipeline):
    """
    Complete Census Data Pipeline.

    This pipeline:
    1. Runs the Census Collector to fetch data from Census API and save to GCS
    2. Runs the Census Processor to ingest CSV data from GCS into the database
    """

    def __init__(self, city: str):
        """
        Initialize census pipeline.

        Args:
            city: City name to collect and process data for (e.g., "boston", "cambridge")
        """
        super().__init__()
        self.pipeline_name = "census"
        self.city = city

    def create_pipeline(self):
        """Create and return the census pipeline"""
        city = self.city

        # Initialize collector and processor components
        census_collector = CensusCollectorComponent(city=city).get_component()
        census_processor = CensusProcessorComponent(city=city).get_component()

        @dsl.pipeline(name=f"{self.pipeline_name}-pipeline-{city}")
        def census_pipeline():
            # Step 1: Run census collector
            collector_task = (
                census_collector()
                .set_display_name(f"collector-census-{city}")
                .set_cpu_limit("2000m")
                .set_memory_limit("8G")
            )

            # Step 2: Run census processor (after collector completes)
            processor_task = (
                census_processor()
                .set_display_name(f"processor-census-{city}")
                .set_cpu_limit("2000m")
                .set_memory_limit("8G")
                .after(collector_task)  # Wait for collector to finish
            )

        return census_pipeline

    def run(self):
        """Compile and submit the census pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile the pipeline to pipeline_outputs directory
        pipeline_file = self.pipeline_outputs_dir / f"{self.pipeline_name}_pipeline_{self.city}.yaml"
        compiler.Compiler().compile(pipeline, package_path=str(pipeline_file))

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Create and submit the job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{self.pipeline_name}-{self.city}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=str(pipeline_file),
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        print(f"Pipeline will run: Census Collector -> Census Processor for {self.city}")

        return job
