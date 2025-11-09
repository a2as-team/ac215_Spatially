from .base import BaseCensusCaller
import pandas as pd


class OwnerCostBurdenCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict={
            "B25093_001E": "median_owner_cost_pct_income",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # No preprocessing needed
        return df
