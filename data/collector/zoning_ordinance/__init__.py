"""Zoning ordinance data collectors for multiple cities."""

from collector.zoning_ordinance.boston import ZoningCodeCollector as BostonCollector
from collector.zoning_ordinance.chicago import ChicagoZoningCollector

__all__ = ["BostonCollector", "ChicagoZoningCollector"]
