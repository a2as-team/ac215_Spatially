from .base import BaseCensusCaller
import pandas as pd


class PopulationCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict = {
        # B01002: Median Age
        "B01002_001E": "median_age",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
