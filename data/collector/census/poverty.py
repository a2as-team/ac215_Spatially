from .base import BaseCensusCaller
import pandas as pd


class PopulationCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5/subject",
        column_dict = {
        # S1701: Poverty Status in the Past 12 Months
        # C02_001E: Percent - All people - Below poverty level
        "S1701_C02_001E": "poverty_rate_all_people",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
