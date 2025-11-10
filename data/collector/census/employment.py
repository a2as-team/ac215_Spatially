from .base import BaseCensusCaller
import pandas as pd


class MobilityCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5/profile",
        column_dict = {
        # EMPLOYMENT STATUS - Employed (count)
        "DP03_0004E": "employed",
        # Unemployed (% of civilian labor force)
        "DP03_0005PE": "unemployment_rate",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
