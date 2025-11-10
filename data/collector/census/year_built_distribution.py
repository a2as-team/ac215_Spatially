from .base import BaseCensusCaller
import pandas as pd


class YearBuiltDistributionCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict={
            "B25034_001E": "total_units_by_year_built",
            "B25034_010E": "built_2020_or_later",
            "B25034_009E": "built_2010_to_2019",
            "B25034_008E": "built_2000_to_2009",
            "B25034_007E": "built_1990_to_1999",
            "B25034_006E": "built_1980_to_1989",
            "B25034_005E": "built_1970_to_1979",
            "B25034_004E": "built_1960_to_1969",
            "B25034_003E": "built_1950_to_1959",
            "B25034_002E": "built_before_1950",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # No preprocessing needed
        return df
