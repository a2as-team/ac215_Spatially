import os
from utils.smart_arg_parser import SmartArgItem, SmartArgParser

# Import all collector components
from pipelines.collector.development_plans import DevelopmentPlansCollectorComponent
from pipelines.collector.census import CensusCollectorComponent

# Import all processor components
from pipelines.processor.development_plans_label_studio import DevelopmentPlansLabelStudioProcessorComponent

# Import full pipelines
from pipelines.all import AllPipeline


def run(city: str, pipeline_type: str = "all"):
    """
    Run a pipeline or component

    Args:
        city: City to process data for
        pipeline_type: Type to run
            Pipelines (multiple components):
            - "all": All collectors + processors (default)
            - "development_plans": Development plans collector + processor

            Individual Components:
            - "collector-development-plans": Just development plans collector
            - "collector-census": Just census collector
            - "processor-development-plans-label-studio": Just processor
    """
    print(f"Running {pipeline_type} for {city}...")

    # Map to classes
    available = {
        # Full pipelines
        "all": AllPipeline,

        # Individual collectors
        "collector-development-plans": DevelopmentPlansCollectorComponent,
        "collector-census": CensusCollectorComponent,

        # Individual processors
        "processor-development-plans-label-studio": DevelopmentPlansLabelStudioProcessorComponent,
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
        ),
        "pipeline_type": SmartArgItem(
            flags=["--pipeline"],
            prompt="Type of pipeline or component to run",
            arg_type=str,
            required=False,
            default="all",
            choices=[
                "all",
                "collector-development-plans",
                "collector-census",
                "processor-development-plans-label-studio",
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

    # Run the selected pipeline or component
    run(city=args["city"], pipeline_type=args["pipeline_type"])
