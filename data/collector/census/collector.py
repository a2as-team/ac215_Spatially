
import importlib, pkgutil, inspect
from .tables import __path__ as tables_pkg_path
from .base import BaseCensusCaller

class CensusCollector:
    def __init__(self):
        self.caller_map = {}
        for modinfo in pkgutil.iter_modules(tables_pkg_path):
            module = importlib.import_module(f".tables.{modinfo.name}", package=__package__)
            if hasattr(module, "TABLE_CODE"):
                # Dynamically find the Caller class that inherits from BaseCensusCaller
                caller_class = None
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj != BaseCensusCaller and issubclass(obj, BaseCensusCaller):
                        caller_class = obj
                        break
                if caller_class:
                    self.caller_map[module.TABLE_CODE] = caller_class()

    def collect(self, table_code, year, state, county=None, tract=None):
        if table_code not in self.caller_map:
            raise ValueError(f"Invalid table_code: {table_code}. Must be one of {list(self.caller_map.keys())}")
        return self.caller_map[table_code].call(year=year, state=state, county=county, tract=tract)
