from .base import BaseCensusCaller
import pandas as pd


class MobilityCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict = {
        # B19013: Median Household Income
        "B19013_001E": "median_household_income",
        # B19301: Per Capita Income
        "B19301_001E": "per_capita_income",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df