"""
Health Check Module for NER Service

Provides health and readiness check functionality for Cloud Run.
"""
import logging

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health checker for NER service.

    Tracks service health and model loading status for Cloud Run probes.
    """

    def __init__(self):
        self._model_loaded = False
        logger.info("HealthChecker initialized")

    def is_healthy(self) -> bool:
        """
        Check if service is healthy.

        Always returns True for basic liveness probe.
        Cloud Run uses this to determine if container should be restarted.
        """
        return True

    def is_ready(self) -> bool:
        """
        Check if service is ready to accept traffic.

        Returns True only when NER model is loaded and ready for inference.
        Cloud Run uses this to determine when to start routing traffic.
        """
        return self._model_loaded

    def mark_model_loaded(self):
        """Mark the NER model as loaded and ready."""
        self._model_loaded = True
        logger.info("Model marked as loaded - service is ready")

    def mark_model_unloaded(self):
        """Mark the NER model as unloaded (for cleanup/restart scenarios)."""
        self._model_loaded = False
        logger.info("Model marked as unloaded")


# Global health checker instance
health_checker = HealthChecker()
