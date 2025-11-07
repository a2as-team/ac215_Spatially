import os
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from shared_config.cities import City

# Import all collector components
from pipelines.collector.development_plans import DevelopmentPlansCollectorComponent
from pipelines.collector.census import CensusCollectorComponent
from pipelines.collector.zoning_ordinance import ZoningOrdinanceCollectorComponent

# Import all processor components
from pipelines.processor.development_plans_label_studio import DevelopmentPlansLabelStudioProcessorComponent
from pipelines.processor.zoning_ordinance_chunk_embed import ZoningOrdinanceChunkEmbedComponent
from pipelines.processor.zoning_ordinance_load import ZoningOrdinanceLoadComponent

# Import full pipelines
from pipelines.all import AllPipeline
from pipelines.zoning_ordinance import ZoningOrdinancePipeline


def run(city: str, pipeline_type: str = "all"):
    """
    Run a pipeline or component

    Args:
        city: City to process data for
        pipeline_type: Type to run
            Pipelines (multiple components):
            - "all": All collectors + processors (default)
            - "zoning-ordinance": Zoning ordinance collector + chunk-embed + load

            Individual Components:
            - "collector-development-plans": Just development plans collector
            - "collector-census": Just census collector
            - "collector-zoning-ordinance": Just zoning ordinance collector
            - "processor-development-plans-label-studio": Just development plans processor
            - "processor-zoning-ordinance-chunk-embed": Just zoning ordinance chunk & embed
            - "processor-zoning-ordinance-load": Just zoning ordinance ChromaDB load
    """
    print(f"Running {pipeline_type} for {city}...")

    # Map to classes
    available = {
        # Full pipelines
        "all": AllPipeline,
        "zoning-ordinance": ZoningOrdinancePipeline,

        # Individual collectors
        "collector-development-plans": DevelopmentPlansCollectorComponent,
        "collector-census": CensusCollectorComponent,
        "collector-zoning-ordinance": ZoningOrdinanceCollectorComponent,

        # Individual processors
        "processor-development-plans-label-studio": DevelopmentPlansLabelStudioProcessorComponent,
        "processor-zoning-ordinance-chunk-embed": ZoningOrdinanceChunkEmbedComponent,
        "processor-zoning-ordinance-load": ZoningOrdinanceLoadComponent,
    }

    if pipeline_type not in available:
        raise ValueError(
            f"Unknown type: {pipeline_type}. "
            f"Available: {list(available.keys())}"
        )

    # Instantiate and run
    obj = available[pipeline_type](city=city)
    job = obj.run()

    print(f"Submitted successfully! Job: {job.display_name}")
    return job


if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to process",
            arg_type=str,
            required=True,
            choices=[city.lower() for city in City.get_all()],  # Support lowercase input
        ),
        "pipeline_type": SmartArgItem(
            flags=["--pipeline"],
            prompt="Type of pipeline or component to run",
            arg_type=str,
            required=False,
            default="all",
            choices=[
                "all",
                "zoning-ordinance",
                "collector-development-plans",
                "collector-census",
                "collector-zoning-ordinance",
                "processor-development-plans-label-studio",
                "processor-zoning-ordinance-chunk-embed",
                "processor-zoning-ordinance-load",
            ],
        ),
        "test": SmartArgItem(
            flags=["--test"],
            prompt="Run in test mode (only process first few pages)",
            arg_type=bool,
            required=False,
            default=False,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Validate and normalize city name
    city_upper = args["city"].upper()
    if not City.is_valid(city_upper):
        raise ValueError(
            f"Unknown city: {args['city']}. "
            f"Available cities: {', '.join(c.lower() for c in City.get_all())}"
        )

    # Run the selected pipeline or component (pass lowercase for compatibility)
    run(city=args["city"].lower(), pipeline_type=args["pipeline_type"])
