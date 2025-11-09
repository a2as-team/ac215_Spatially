from .base import BaseCensusCaller
import pandas as pd


class VacancyCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict={
            "B25004_001E": "total_vacant_units",
            "B25004_005E": "vacant_for_rent_units",
            "B25004_007E": "vacant_for_sale_units",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # No preprocessing needed
        return df
