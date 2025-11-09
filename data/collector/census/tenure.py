from .base import BaseCensusCaller
import pandas as pd


class PopulationCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict = {
        # B25003: Tenure
        "B25003_001E": "occupied_housing_units_total",
        "B25003_002E": "owner_occupied_units",
        "B25003_003E": "renter_occupied_units",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
