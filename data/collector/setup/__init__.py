"""
Setup package for the collector.

This package contains modules for initializing and configuring the collector environment.
"""

from .init_db import DatabaseInitializer

__all__ = ['DatabaseInitializer']
