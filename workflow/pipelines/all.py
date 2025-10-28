from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip

# Import all collector components
from pipelines.collector.development_plans import DevelopmentPlansCollectorComponent
from pipelines.collector.census import CensusCollectorComponent

# Import all processor components
from pipelines.processor.development_plans_label_studio import DevelopmentPlansLabelStudioProcessorComponent


class AllPipeline(BasePipeline):
    """Pipeline that runs all data collectors in parallel, then all processors"""

    def __init__(self, city: str):
        super().__init__(city)
        self.pipeline_name = "all"
        self.city = city

    def create_pipeline(self):
        """Create and return the pipeline with all collectors and processors"""
        city = self.city

        # Initialize all collector components
        dev_plans_collector = DevelopmentPlansCollectorComponent(city=city).get_component()
        census_collector = CensusCollectorComponent(city=city).get_component()
    

        # Initialize processor components
        dev_plans_label_studio_processor = DevelopmentPlansLabelStudioProcessorComponent(city=city).get_component()

        @dsl.pipeline(name=f"{self.pipeline_name}-pipeline-{city}")
        def all_pipeline():
            # All collectors run in parallel (no .after() dependency)
            dev_plans_collector_task = (
                dev_plans_collector()
                .set_display_name(f"collector-development-plans-{city}")
                .set_cpu_limit("2000m")  # Selenium web scraping needs more resources
                .set_memory_limit("8G")
            )

            census_collector_task = (
                census_collector()
                .set_display_name(f"collector-census-{city}")
                .set_cpu_limit("1000m")  # API calls, moderate resources
                .set_memory_limit("4G")
            )
            
            # Processor runs after development plans collector completes
            dev_plans_processor_task = (
                dev_plans_label_studio_processor()
                .set_display_name(f"processor-development-plans-label-studio-{city}")
                .set_cpu_limit("1000m")  # Data processing, moderate resources
                .set_memory_limit("4G")
                .after(dev_plans_collector_task)  # Wait for collector to finish
            )

        return all_pipeline

    def run(self):
        """Compile and submit the pipeline to Vertex AI"""
        pipeline = self.create_pipeline()

        # Compile the pipeline
        pipeline_file = f"{self.pipeline_name}_pipeline_{self.city}.yaml"
        compiler.Compiler().compile(pipeline, package_path=pipeline_file)

        # Initialize Vertex AI
        aip.init(project=self.GCP_PROJECT, staging_bucket=self.BUCKET_URI)

        # Create and submit the job
        job_id = self.generate_uuid()
        city_suffix = f"_{self.city}" if hasattr(self, 'city') else ""
        display_name = f"{self.project_name}-{self.pipeline_name}{city_suffix}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=pipeline_file,
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")

        return job
