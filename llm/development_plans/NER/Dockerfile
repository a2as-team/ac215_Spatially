# Lightweight local development image
# For Vertex AI deployment, this Dockerfile is NOT used - only package/setup.py matters
FROM python:3.13-slim-bullseye

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies using uv (much faster than pip)
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the source code (including package with config, run.py, etc.)
COPY . ./

# Create directory for model outputs
RUN mkdir -p /app/tmp /app/models /app/outputs

# Add package to PYTHONPATH so imports work correctly
ENV PYTHONPATH="/app/package:${PYTHONPATH}"

# Default command - allows running interactively or with commands
ENTRYPOINT ["/bin/bash"]
CMD ["-c", "exec bash"]