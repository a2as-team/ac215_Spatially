from .base import BaseCensusCaller
import pandas as pd


class HomeValueDistributionCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5/profile",
        column_dict={
            "DP04_0081E": "owner_occ_units_value_less_100k",
            "DP04_0082E": "owner_occ_units_value_100k_199k",
            "DP04_0083E": "owner_occ_units_value_200k_299k",
            "DP04_0084E": "owner_occ_units_value_300k_499k",
            "DP04_0085E": "owner_occ_units_value_500k_999k",
            "DP04_0086E": "owner_occ_units_value_1m_or_more",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # No preprocessing needed
        return df
