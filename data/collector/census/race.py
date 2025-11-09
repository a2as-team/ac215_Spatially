from .base import BaseCensusCaller
import pandas as pd


class PopulationCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict = {
        "B02001_001E": "race_total",
        "B02001_002E": "white_alone",
        "B02001_003E": "black_or_african_american_alone",
        "B02001_004E": "american_indian_alaska_native_alone",
        "B02001_005E": "asian_alone",
        "B02001_006E": "native_hawaiian_pacific_islander_alone",
        "B02001_007E": "some_other_race_alone",
        "B02001_008E": "two_or_more_races",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
