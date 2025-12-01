import os
import sys
from pathlib import Path

# Add project root to path for shared_config imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from shared_config.city_service import CityService

# Import all collector components
from pipelines.collector.development_plans import DevelopmentPlansCollectorComponent
from pipelines.collector.census import CensusCollectorComponent
from pipelines.collector.zoning_ordinance import ZoningOrdinanceCollectorComponent
from pipelines.collector.zoning_codes import ZoningCodesCollectorComponent

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
from pipelines.zoning_codes_parallel import ZoningCodesParallelPipeline

# Map to classes
available = {
    # Full pipelines
    "all": AllPipeline,
    "zoning-ordinance": ZoningOrdinancePipeline,
    "census": CensusPipeline,
    "zoning-codes-parallel": ZoningCodesParallelPipeline,
    # Individual collectors
    "collector-development-plans": DevelopmentPlansCollectorComponent,
    "collector-census": CensusCollectorComponent,
    "collector-zoning-ordinance": ZoningOrdinanceCollectorComponent,
    "collector-zoning-maps": ZoningMapsCollectorComponent,
    "collector-zoning-codes": ZoningCodesCollectorComponent,
    # Individual processors
    "processor-development-plans-label-studio": DevelopmentPlansLabelStudioProcessorComponent,
    "processor-zoning-ordinance": ZoningOrdinanceProcessorComponent,
    "processor-census": CensusProcessorComponent,
}

# Components that don't require a city parameter
no_city_required = {"collector-zoning-codes", "zoning-codes-parallel"}


def run(city: str = None, pipeline_type: str = "all", test_mode: bool = False):
    global available
    """
    Run a pipeline or component

    Args:
        city: City to process data for (not required for some components)
        pipeline_type: Type to run
            Pipelines (multiple components):
            - "all": All collectors + processors (default)
            - "zoning-ordinance": Zoning ordinance & maps collector + processor (DOCX→MD, chunk, embed, save to PostgreSQL)
            - "census": Census collector + processor (API→CSV→Database)
            - "zoning-codes-parallel": Zoning codes collector for ALL 50 states in parallel (fastest)

            Individual Components:
            - "collector-development-plans": Just development plans collector
            - "collector-census": Just census collector
            - "collector-zoning-ordinance": Just zoning ordinance collector
            - "collector-zoning-maps": Just zoning maps collector
            - "collector-zoning-codes": Zoning codes collector (single job, sequential states)
            - "processor-development-plans-label-studio": Just development plans processor
            - "processor-zoning-ordinance": Zoning ordinance processor (DOCX→MD, chunk, embed, save to PostgreSQL)
            - "processor-census": Census processor (CSV→Database)
        test_mode: If True, run in test mode (for zoning-codes: only first state with limited cities)
    """
    if pipeline_type not in available:
        raise ValueError(
            f"Unknown type: {pipeline_type}. " f"Available: {list(available.keys())}"
        )

    # Handle components that don't require a city
    if pipeline_type in no_city_required:
        print(f"Running {pipeline_type}...")
        obj = available[pipeline_type](test_mode=test_mode)
    else:
        print(f"Running {pipeline_type} for {city}...")
        obj = available[pipeline_type](city=city)

    job = obj.run()

    print(f"Submitted successfully! Job: {job.display_name}")
    return job


if __name__ == "__main__":
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to process (not required for collector-zoning-codes)",
            arg_type=str,
            required=False,
            default=None,
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
        "test_mode": SmartArgItem(
            flags=["--test-mode"],
            prompt="Run in test mode (e.g., only first state for zoning-codes)",
            arg_type=bool,
            required=False,
            default=False,
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    pipeline_type = args["pipeline_type"]
    city = args.get("city")
    test_mode = args.get("test_mode", False)

    # Validate city is provided for components that require it
    if pipeline_type not in no_city_required:
        if not city:
            raise ValueError(
                f"--city is required for {pipeline_type}. "
                f"Use --city <city_name> to specify the city."
            )
        city = city.lower()

        # Validate city exists in database
        with CityService() as service:
            if not service.city_exists(city):
                available_cities = [c["name"] for c in service.get_all_cities()]
                raise ValueError(
                    f"Unknown city: {city}. "
                    f"Available cities: {', '.join(available_cities[:10])}..."
                )

    # Run the selected pipeline or component
    run(city=city, pipeline_type=pipeline_type, test_mode=test_mode)
