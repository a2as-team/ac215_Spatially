from .mobility import MobilityCaller
from .population import PopulationCaller


class CensusCollector:
    caller_map = {}

    def __init__(self):
        self.caller_map = {
            "population": PopulationCaller(),
            "mobility": MobilityCaller(),
        }

    def collect(
        self,
        type: str,
        level: str,
        year: int,
        state: str,
        county: str | None,
        tract: str | None,
    ):
        return self.caller_map[type].call(level, year, state, county, tract)
