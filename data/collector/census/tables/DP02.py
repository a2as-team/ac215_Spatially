from ..base import BaseCensusCaller
from ..utils_table_vars import fetch_table_variables

TABLE_CODE = "DP02"
DATASET = "acs/acs5/profile"

class SocialCharacteristicsInclHouseholdTypesCaller(BaseCensusCaller):
    def __init__(self, dataset=DATASET):
        super().__init__(dataset)

    def call(self, year: int, state: str, county: str | None = None, tract: str | None = None):
        variables = fetch_table_variables(self.dataset, year, TABLE_CODE)
        if not variables:
            raise ValueError(f"No variables found for table {TABLE_CODE} in {year}/{self.dataset}")
        return self._query(year=year, variables=variables, state=state, county=county, tract=tract)
