
import pandas as pd
import requests
import warnings
from typing import Dict, Optional

class BaseCensusCaller:
    def __init__(self, dataset: str):
        self.dataset = dataset

    def _query(self, year: int, variables: Dict[str, str], state: str, county: Optional[str] = None, tract: Optional[str] = None) -> pd.DataFrame:
        var_list = ",".join(variables.keys())
        base = f"https://api.census.gov/data/{year}/{self.dataset}?get={var_list}"
        if tract:
            geo = f"for=tract:*&in=state:{state}+county:{county}"
        elif county:
            geo = f"for=county:*&in=state:{state}"
        else:
            geo = f"for=state:{state}"
        url = f"{base}&{geo}"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        rows = r.json()
        header, data = rows[0], rows[1:]

        # Check for empty data
        if not data:
            warnings.warn(f"No data rows returned for year={year}, dataset={self.dataset}, state={state}")

        df = pd.DataFrame(data, columns=header)
        rename_map = {k: v for k, v in variables.items() if k in df.columns}

        # Log missing variables
        missing_vars = set(variables.keys()) - set(df.columns)
        if missing_vars:
            warnings.warn(f"Missing variables in API response: {missing_vars}")

        df = df.rename(columns=rename_map)
        return df
