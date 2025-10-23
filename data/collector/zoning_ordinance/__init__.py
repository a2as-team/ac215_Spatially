"""Zoning ordinance data collectors for multiple cities."""

from .boston import ZoningCodeCollector as BostonCollector
from .chicago import ChicagoZoningCollector

__all__ = ["BostonCollector", "ChicagoZoningCollector"]
