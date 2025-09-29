from ..base import BaseCollector
from .caller import PopulationCaller
from .caller import MobilityCaller


class CensusCollector(BaseCollector):
    def __init__(self):
        self.population_caller = PopulationCaller()
        self.mobility_caller = MobilityCaller()

    def collect(
        self,
        type: str,
        level: str,
        year: int,
        state: str,
        county: str | None,
        tract: str | None,
    ):
        if type == "population":
            return self.population_caller.call(level, year, state, county, tract)
        elif type == "mobility":
            return self.mobility_caller.call(level, year, state, county, tract)
        else:
            raise ValueError(f"Invalid type: {type}")
