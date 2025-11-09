from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip

# Import zoning ordinance components
from pipelines.collector.zoning_ordinance import ZoningOrdinanceCollectorComponent
from pipelines.collector.zoning_maps import ZoningMapsCollectorComponent
from pipelines.processor.zoning_ordinance import ZoningOrdinanceProcessorComponent


class ZoningOrdinancePipeline(BasePipeline):
    """Pipeline for zoning ordinance: collect ordinances & maps → process (docx→md, chunk, embed, save to PostgreSQL)"""

    def __init__(self, city: str):
        super().__init__()
        self.pipeline_name = "zoning-ordinance"
        self.city = city

    def create_pipeline(self):
        """Create and return the zoning ordinance pipeline with 3 components"""
        city = self.city

        # Initialize components
        ordinance_collector = ZoningOrdinanceCollectorComponent(city=city).get_component()
        maps_collector = ZoningMapsCollectorComponent(city=city).get_component()
        processor = ZoningOrdinanceProcessorComponent(city=city).get_component()

        @dsl.pipeline(name=f"{self.pipeline_name}-pipeline-{city}")
        def zoning_ordinance_pipeline():
            # Step 1a: Collect ordinance documents from city websites
            ordinance_collector_task = (
                ordinance_collector()
                .set_display_name(f"collector-zoning-ordinance-{city}")
                .set_cpu_limit("2000m")  # Web scraping needs resources
                .set_memory_limit("8G")
            )

            # Step 1b: Collect zoning maps (runs in parallel with ordinance collection)
            maps_collector_task = (
                maps_collector()
                .set_display_name(f"collector-zoning-maps-{city}")
                .set_cpu_limit("2000m")
                .set_memory_limit("8G")
            )

            # Step 2: Process DOCX files: convert to markdown, chunk, generate embeddings, save to PostgreSQL
            # Waits for both collectors to complete
            processor_task = (
                processor()
                .set_display_name(f"processor-zoning-ordinance-{city}")
                .set_cpu_limit("4000m")  # Embedding generation is CPU intensive
                .set_memory_limit("16G")  # Large documents need more memory
                .after(ordinance_collector_task)
                .after(maps_collector_task)
            )

        return zoning_ordinance_pipeline

    def run(self):
        """Compile and submit the pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile the pipeline to pipeline_outputs directory
        pipeline_file = self.pipeline_outputs_dir / f"{self.pipeline_name}_pipeline_{self.city}.yaml"
        compiler.Compiler().compile(pipeline, package_path=str(pipeline_file))

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Create and submit the job
        job_id = self.generate_uuid()
        display_name = f"{self.project_name}-{self.pipeline_name}_{self.city}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=str(pipeline_file),
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        print(f"City: {self.city}")

        return job
