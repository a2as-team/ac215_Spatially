from .base import BaseCensusCaller
import pandas as pd


class PopulationCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5",
        column_dict={
            "B01003_001E": "total_population",
        },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
