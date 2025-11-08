from pipelines import BasePipeline
from kfp import dsl, compiler
import google.cloud.aiplatform as aip

# Import zoning ordinance components
from pipelines.collector.zoning_ordinance import ZoningOrdinanceCollectorComponent
from pipelines.processor.zoning_ordinance_embed import ZoningOrdinanceEmbedComponent
from pipelines.processor.zoning_ordinance_load import ZoningOrdinanceLoadComponent


class ZoningOrdinancePipeline(BasePipeline):
    """Pipeline for zoning ordinance: collect → embed (docx→md, chunk, embed) → load to ChromaDB"""

    def __init__(self, city: str, collection_name: str = "zoning-ordinance"):
        super().__init__()
        self.pipeline_name = "zoning-ordinance"
        self.city = city
        self.collection_name = collection_name

    def create_pipeline(self):
        """Create and return the zoning ordinance pipeline with 3 sequential components"""
        city = self.city
        collection_name = self.collection_name

        # Initialize components
        collector = ZoningOrdinanceCollectorComponent(city=city).get_component()
        processor = ZoningOrdinanceEmbedComponent(city=city).get_component()
        loader = ZoningOrdinanceLoadComponent(
            city=city,
            collection_name=collection_name
        ).get_component()

        @dsl.pipeline(name=f"{self.pipeline_name}-pipeline-{city}")
        def zoning_ordinance_pipeline():
            # Step 1: Collect ordinance data from city websites
            collector_task = (
                collector()
                .set_display_name(f"collector-zoning-ordinance-{city}")
                .set_cpu_limit("2000m")  # Web scraping needs resources
                .set_memory_limit("8G")
            )

            # Step 2: Convert DOCX to markdown, chunk and generate embeddings (waits for collector)
            processor_task = (
                processor()
                .set_display_name(f"processor-zoning-ordinance-embed-{city}")
                .set_cpu_limit("4000m")  # Embedding generation is CPU intensive
                .set_memory_limit("16G")  # Large documents need more memory
                .after(collector_task)
            )

            # Step 3: Load embeddings to ChromaDB Cloud (waits for processor)
            loader_task = (
                loader()
                .set_display_name(f"processor-zoning-ordinance-load-{city}")
                .set_cpu_limit("1000m")
                .set_memory_limit("4G")
                .after(processor_task)
            )

        return zoning_ordinance_pipeline

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
        display_name = f"{self.project_name}-{self.pipeline_name}_{self.city}-{job_id}"

        job = aip.PipelineJob(
            display_name=display_name,
            template_path=pipeline_file,
            pipeline_root=self.PIPELINE_ROOT,
            enable_caching=False,
        )

        job.submit(service_account=self.GCS_SERVICE_ACCOUNT)

        print(f"Pipeline job submitted: {job.resource_name}")
        print(f"City: {self.city}")
        print(f"Collection: {self.collection_name}")

        return job
