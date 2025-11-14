
import requests
from typing import Dict

def fetch_table_variables(dataset: str, year: int, table_code: str) -> Dict[str, str]:
    url = f"https://api.census.gov/data/{year}/{dataset}/variables.json"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    meta = r.json().get("variables", {})
    out = {}
    alias_counts = {}  # Track alias usage to handle duplicates
    prefix = f"{table_code}_"
    for var, props in meta.items():
        if var.startswith(prefix):
            label = props.get("label") or var
            alias = ''.join(ch.lower() if ch.isalnum() else '_' for ch in label).strip('_')

            # Handle duplicate aliases by appending a suffix
            if alias in alias_counts:
                alias_counts[alias] += 1
                alias = f"{alias}_{alias_counts[alias]}"
            else:
                alias_counts[alias] = 0

            out[var] = alias
    if not out and table_code in meta:
        out[table_code] = table_code.lower()
    return out
