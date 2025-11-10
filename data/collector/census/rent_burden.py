from .base import BaseCensusCaller
import pandas as pd


class RentBurdenCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict={
            "B25070_001E": "median_gross_rent_pct_income",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # No preprocessing needed
        return df
