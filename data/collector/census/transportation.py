from .base import BaseCensusCaller
import pandas as pd


class MobilityCaller(BaseCensusCaller):
    def __init__(
        self,
        dataset="acs/acs5/profile",
        column_dict = {
        # Means of transportation (% of workers 16+)
        "DP03_0019PE": "pct_drive_alone",          # Car, truck, or van—drove alone
        "DP03_0020PE": "pct_carpool",              # Carpooled
        "DP03_0021PE": "pct_public_transport",     # Public transportation (excl. taxicab)
        "DP03_0022PE": "pct_walked",               # Walked
        "DP03_0023PE": "pct_other_means",          # Other means
        "DP03_0024PE": "pct_work_from_home",       # Worked from home
        # Mean travel time to work (minutes)
        "DP03_0025E":  "mean_travel_time_minutes",
    },
    ):
        super().__init__(dataset, column_dict)

    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # We will do nothing for now
        return df
