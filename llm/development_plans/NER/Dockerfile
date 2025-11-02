# Use GCP's Vertex AI PyTorch GPU base image
# This image comes pre-installed with PyTorch, CUDA, and is optimized for Vertex AI
#
# Note: This image works on CPU-only machines too (for local development/testing)
# The GPU libraries are only used if GPU is available at runtime.
#
# For faster local builds on CPU-only machines, you can optionally use:
# --build-arg BASE_IMAGE=us-docker.pkg.dev/vertex-ai/training/pytorch-cpu.2-0.py310:latest
ARG BASE_IMAGE=us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-0.py310:latest
FROM ${BASE_IMAGE}

# Python wants UTF-8 locale
ENV LANG=C.UTF-8

# Tell Python to disable buffering so we don't lose any logs.
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Install Python dependencies
# Note: PyTorch is already installed in the base image
RUN pip install --no-cache-dir -r pyproject.toml

# Copy the source code
COPY --chown=app:app . ./

# Create directory for model outputs
RUN mkdir -p /app/tmp /app/models /app/outputs

# Default command to run the trainer with GCS data
ENTRYPOINT ["/bin/bash"]
# Get into the uv virtual environment shell
CMD ["-c", "exec bash"]