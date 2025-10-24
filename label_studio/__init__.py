"""
Label Studio service framework for NER annotation.

This package provides base classes and utilities for managing Label Studio
annotation services across different dataset types (development_plans, zba, etc.).
"""

from .base import BaseLabelStudioService

__all__ = ["BaseLabelStudioService"]
