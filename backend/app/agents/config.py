"""Google ADK configuration for Vertex AI.

This module configures the Google GenAI/ADK to use Vertex AI
instead of the Google AI API by setting environment variables.

The ADK reads these environment variables:
- GOOGLE_GENAI_USE_VERTEXAI: Set to "true" to use Vertex AI
- GOOGLE_CLOUD_PROJECT: GCP project ID
- GOOGLE_CLOUD_LOCATION: GCP region (e.g., us-central1)

Reference: https://google.github.io/adk-docs/agents/models/
"""

import os


_configured = False


def configure_vertexai(project: str = None, location: str = None):
    """
    Configure Google GenAI/ADK to use Vertex AI via environment variables.

    Args:
        project: GCP project ID (defaults to GCP_PROJECT env var)
        location: GCP region (defaults to GCP_REGION env var)

    This should be called once at application startup.
    """
    global _configured

    if _configured:
        return

    # Get project from various possible env var names
    project = (
        project
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
    )
    location = (
        location
        or os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("GCP_REGION")
        or "us-central1"
    )

    if not project:
        raise ValueError(
            "GCP_PROJECT or GOOGLE_CLOUD_PROJECT environment variable not set. "
            "Required for Vertex AI authentication."
        )

    # Set the environment variables that ADK expects
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["GOOGLE_CLOUD_LOCATION"] = location

    _configured = True


def ensure_configured():
    """Ensure Vertex AI is configured, configuring if needed."""
    if not _configured:
        configure_vertexai()
