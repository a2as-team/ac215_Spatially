from .base import BaseCensusCaller
import pandas as pd


class MobilityCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict = {
        # B25077: Median Value (Owner-occupied)
        "B25077_001E": "median_home_value",
        # B25064: Median Gross Rent
        "B25064_001E": "median_gross_rent",
        # B25035: Median Year Structure Built
        "B25035_001E": "median_year_built",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
