from .base import BaseCensusCaller
import pandas as pd


class MobilityCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5/profile",
        column_dict = {
        # DP02: Educational Attainment
        # Percent!!Population 25 years and over!!High school graduate or higher
        "DP02_0066PE": "pct_high_school_or_higher",
        # Percent!!Population 25 years and over!!Bachelor's degree or higher
        "DP02_0067PE": "pct_bachelors_or_higher",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
