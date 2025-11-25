
import pandas as pd
import requests
import warnings
from typing import Dict, Optional
from .state_fips import get_fips_code

class BaseCensusCaller:
    def __init__(self, dataset: str):
        self.dataset = dataset
        self.chunk_size = 50  # Maximum variables per request to avoid URL length issues

    def _query(self, year: int, variables: Dict[str, str], state: str, county: Optional[str] = None, tract: Optional[str] = None) -> pd.DataFrame:
        # Convert state abbreviation to FIPS code
        state_fips = get_fips_code(state)

        # Build geography parameter
        if tract:
            geo = f"for=tract:*&in=state:{state_fips}+county:{county}"
        elif county:
            geo = f"for=county:*&in=state:{state_fips}"
        else:
            geo = f"for=state:{state_fips}"

        # Split variables into chunks if too many
        var_keys = list(variables.keys())
        if len(var_keys) > self.chunk_size:
            return self._query_chunked(year, variables, geo, state)

        # Single request for small variable sets
        var_list = ",".join(var_keys)
        url = f"https://api.census.gov/data/{year}/{self.dataset}?get={var_list}&{geo}"
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

    def _query_chunked(self, year: int, variables: Dict[str, str], geo: str, state: str) -> pd.DataFrame:
        """Handle large variable sets by splitting into multiple requests."""
        var_keys = list(variables.keys())
        chunks = [var_keys[i:i + self.chunk_size] for i in range(0, len(var_keys), self.chunk_size)]

        dfs = []
        geo_cols = []  # Track geography columns to avoid duplicates

        for i, chunk in enumerate(chunks):
            var_list = ",".join(chunk)
            url = f"https://api.census.gov/data/{year}/{self.dataset}?get={var_list}&{geo}"

            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                rows = r.json()
                header, data = rows[0], rows[1:]

                if not data:
                    warnings.warn(f"No data rows in chunk {i+1}/{len(chunks)}")
                    continue

                df = pd.DataFrame(data, columns=header)

                # Identify geography columns (state, county, tract)
                if i == 0:
                    geo_cols = [col for col in df.columns if col in ['state', 'county', 'tract']]

                # Rename data columns
                chunk_vars = {k: v for k, v in variables.items() if k in chunk}
                rename_map = {k: v for k, v in chunk_vars.items() if k in df.columns}
                df = df.rename(columns=rename_map)

                dfs.append(df)

            except Exception as e:
                warnings.warn(f"Error fetching chunk {i+1}/{len(chunks)}: {e}")
                continue

        if not dfs:
            raise ValueError(f"No data retrieved for any chunk (year={year}, state={state})")

        # Merge all chunks on geography columns
        result = dfs[0]
        for df in dfs[1:]:
            result = result.merge(df, on=geo_cols, how='outer')

        return result
