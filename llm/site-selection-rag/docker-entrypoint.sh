#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"

# Change to the correct working directory
cd /app/llm/site-selection-rag

# Set ChromaDB connection for Docker environment
export CHROMADB_HOST="site-selection-rag-chromadb"
export CHROMADB_PORT="8000"

echo "Environment ready! Virtual environment activated."
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"
echo "ChromaDB: $CHROMADB_HOST:$CHROMADB_PORT"

# Activate virtual environment
echo "Activating virtual environment..."
source /.venv/bin/activate

# Keep a shell open
exec /bin/bash