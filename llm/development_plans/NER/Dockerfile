# Use the official Debian-hosted Python image
FROM python:3.12-slim-bookworm

ARG DEBIAN_PACKAGES="build-essential git curl"

# Prevent apt from showing prompts
ENV DEBIAN_FRONTEND=noninteractive

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Tell uv to copy packages from the wheel into the site-packages
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ${DEBIAN_PACKAGES} && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Copy the rest of the application
COPY config/ ./config/
COPY train.py ./
COPY tmp/ ./tmp/

# Create directory for model outputs
RUN mkdir -p /app/models /app/outputs

# Default command to run the trainer
CMD ["python", "-c", "from train import Trainer; trainer = Trainer(); trainer.train()"]