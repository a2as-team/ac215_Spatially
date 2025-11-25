import os
import sys
from pathlib import Path

# Add project root to path for shared_config imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from shared_config.cities import City

# Import all collector components
from pipelines.collector.development_plans import DevelopmentPlansCollectorComponent
from pipelines.collector.census import CensusCollectorComponent
from pipelines.collector.zoning_ordinance import ZoningOrdinanceCollectorComponent

# Import all processor components
from pipelines.processor.development_plans_label_studio import (
    DevelopmentPlansLabelStudioProcessorComponent,
)
from pipelines.processor.zoning_ordinance import ZoningOrdinanceProcessorComponent
from pipelines.processor.census import CensusProcessorComponent
from pipelines.collector.zoning_maps import ZoningMapsCollectorComponent

# Import full pipelines
from pipelines.all import AllPipeline
from pipelines.zoning_ordinance import ZoningOrdinancePipeline
from pipelines.census import CensusPipeline

# Map to classes
available = {
    # Full pipelines
    "all": AllPipeline,
    "zoning-ordinance": ZoningOrdinancePipeline,
    "census": CensusPipeline,
    # Individual collectors
    "collector-development-plans": DevelopmentPlansCollectorComponent,
    "collector-census": CensusCollectorComponent,
    "collector-zoning-ordinance": ZoningOrdinanceCollectorComponent,
    "collector-zoning-maps": ZoningMapsCollectorComponent,
    # Individual processors
    "processor-development-plans-label-studio": DevelopmentPlansLabelStudioProcessorComponent,
    "processor-zoning-ordinance": ZoningOrdinanceProcessorComponent,
    "processor-census": CensusProcessorComponent,
}


def run(city: str, pipeline_type: str = "all"):
    global available
    """
    Run a pipeline or component

    Args:
        city: City to process data for
        pipeline_type: Type to run
            Pipelines (multiple components):
            - "all": All collectors + processors (default)
            - "zoning-ordinance": Zoning ordinance & maps collector + processor (DOCX→MD, chunk, embed, save to PostgreSQL)
            - "census": Census collector + processor (API→CSV→Database)

            Individual Components:
            - "collector-development-plans": Just development plans collector
            - "collector-census": Just census collector
            - "collector-zoning-ordinance": Just zoning ordinance collector
            - "collector-zoning-maps": Just zoning maps collector
            - "processor-development-plans-label-studio": Just development plans processor
            - "processor-zoning-ordinance": Zoning ordinance processor (DOCX→MD, chunk, embed, save to PostgreSQL)
            - "processor-census": Census processor (CSV→Database)
    """
    print(f"Running {pipeline_type} for {city}...")

    if pipeline_type not in available:
        raise ValueError(
            f"Unknown type: {pipeline_type}. " f"Available: {list(available.keys())}"
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
            choices=[
                city.lower() for city in City.get_all()
            ],  # Support lowercase input
        ),
        "pipeline_type": SmartArgItem(
            flags=["--pipeline"],
            prompt="Type of pipeline or component to run",
            arg_type=str,
            required=True,
            default="all",
            choices=[
                # Automate by deriving from available.keys(), maintaining order
                *[k for k in available.keys()],
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
    city_upper = args["city"].lower()
    if not City.is_valid(city_upper):
        raise ValueError(
            f"Unknown city: {args['city']}. "
            f"Available cities: {', '.join(c.lower() for c in City.get_all())}"
        )

    # Run the selected pipeline or component (pass lowercase for compatibility)
    run(city=args["city"].lower(), pipeline_type=args["pipeline_type"])
