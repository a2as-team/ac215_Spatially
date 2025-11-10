from .population import PopulationCaller
from .age import AgeCaller
from .race import RaceCaller
from .income import IncomeCaller
from .education import EducationCaller
from .employment import EmploymentCaller
from .transportation import TransportationCaller
from .housing import HousingCaller
from .home_value_distribution import HomeValueDistributionCaller
from .owner_cost_burden import OwnerCostBurdenCaller
from .rent_burden import RentBurdenCaller
from .vacancy import VacancyCaller
from .year_built_distribution import YearBuiltDistributionCaller
from .poverty import PovertyCaller
from .tenure import TenureCaller


class CensusCollector:
    def __init__(self):
        self.caller_map = {
            "population": PopulationCaller(),
            "age": AgeCaller(),
            "race": RaceCaller(),
            "income": IncomeCaller(),
            "education": EducationCaller(),
            "employment": EmploymentCaller(),
            "transportation": TransportationCaller(),
            "housing": HousingCaller(),
            "home_value_distribution": HomeValueDistributionCaller(),
            "owner_cost_burden": OwnerCostBurdenCaller(),
            "rent_burden": RentBurdenCaller(),
            "vacancy": VacancyCaller(),
            "year_built_distribution": YearBuiltDistributionCaller(),
            "poverty": PovertyCaller(),
            "tenure": TenureCaller(),
        }

    def collect(self, type, level, year, state, county=None, tract=None):
        if type not in self.caller_map:
            raise ValueError(f"Invalid type: {type}. Must be one of {list(self.caller_map.keys())}")
        caller = self.caller_map[type]
        return caller.call(level, year, state, county, tract)
