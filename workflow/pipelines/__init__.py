"""
Pipeline package initialization.
Exports base classes for components and pipelines.
"""

from pipelines.base_component import BaseComponent
from pipelines.base_pipeline import BasePipeline

__all__ = ["BaseComponent", "BasePipeline"]
