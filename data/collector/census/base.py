from abc import ABC, abstractmethod
import requests, pandas as pd
from us import states
import os, sys, argparse, urllib.parse


class BaseCensusCaller(ABC):
    API_BASE = "https://api.census.gov/data"
    api_key = os.getenv("CENSUS_API_KEY")
    column_dict = {}

    def __init__(self, dataset, column_dict):
        self.dataset = dataset
        self.column_dict = column_dict

    @staticmethod
    def _state_fips(name_or_abbrev: str) -> str:
        s = states.lookup(name_or_abbrev)
        if not s:
            raise ValueError(f"Unknown state: {name_or_abbrev}")
        return s.fips.zfill(2)

    @staticmethod
    def _geo_params(level: str, ss: str, county: str | None, tract: str | None):
        level = level.lower()
        if level == "state":
            return f"for=state:{ss}", None
        if level == "county":
            if county:
                return f"for=county:{county}", f"in=state:{ss}"
            return "for=county:*", f"in=state:{ss}"
        if level == "tract":
            if tract and county:
                return f"for=tract:{tract}", f"in=state:{ss} county:{county}"
            if county:
                return "for=tract:*", f"in=state:{ss} county:{county}"
            return "for=tract:*", f"in=state:{ss}"  # all tracts statewide
        raise ValueError("level must be state|county|tract")

    def _build_url(
        self,
        state: str,
        level: str,
        year: int,
        county: str | None,
        tract: str | None,
    ):
        spec = self.column_dict
        dataset = self.dataset
        ss = BaseCensusCaller._state_fips(state)
        f, i = BaseCensusCaller._geo_params(level, ss, county, tract)
        vars_ = ",".join(["NAME"] + list(spec.keys()))  # include NAME + requested vars
        query = f"get={urllib.parse.quote(vars_)}"
        parts = [f"{self.API_BASE}/{year}/{dataset}?{query}", f]
        if i:
            parts.append(i)
        if self.api_key:
            parts.append(f"key={self.api_key}")
        return "&".join(parts), dataset

    @staticmethod
    def _add_geoid(df: pd.DataFrame, level: str) -> pd.DataFrame:
        if level == "state":
            df["geoid"] = df["state"]
        elif level == "county":
            df["geoid"] = df["state"] + df["county"]
        elif level == "tract":
            df["geoid"] = df["state"] + df["county"] + df["tract"]

        # save geoid as string
        df["geoid"] = df["geoid"].astype(str)
        return df

    @abstractmethod
    def preprocess_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Abstract method for preprocessing the data. Must be implemented by subclasses.
        This can be used when there are specific transformations that need to be applied to the data.
        """
        return df

    def call(
        self, level, year, state, county: str | None, tract: str | None
    ) -> pd.DataFrame:
        url, dataset = self._build_url(state, level, year, county, tract)
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            header, *rows = r.json()
            df = pd.DataFrame(rows, columns=header)
            df = self.preprocess_df(df)
            df = BaseCensusCaller._add_geoid(df, level)
            # rename columns
            df = df.rename(columns=self.column_dict)
            return df
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling Census API: {e}")
