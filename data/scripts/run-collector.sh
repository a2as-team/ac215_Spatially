#!/bin/bash
# Run collector script for Docker containers
# Uses environment variables: COLLECTOR_NAME, CITY

set -e

# Check required environment variables
if [ -z "$COLLECTOR_NAME" ]; then
    echo "Error: COLLECTOR_NAME environment variable is not set"
    exit 1
fi

if [ -z "$CITY" ]; then
    echo "Error: CITY environment variable is not set"
    exit 1
fi

echo "=========================================="
echo "Running $COLLECTOR_NAME collector for $CITY"
echo "=========================================="

# Run the appropriate collector
python "/app/collector/${COLLECTOR_NAME}/run.py" --city "$CITY"

echo "=========================================="
echo "Collector completed successfully"
echo "=========================================="
