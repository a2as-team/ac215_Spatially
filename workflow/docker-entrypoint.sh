#!/bin/bash

echo "Container is running!"

# Authenticate gcloud using service account if credentials are provided
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Authenticating with GCP using service account..."
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"

    if [ -n "$GCP_PROJECT_ID" ]; then
        gcloud config set project "$GCP_PROJECT_ID"
        echo "Set GCP project to: $GCP_PROJECT_ID"
    fi
fi

# Activate the virtual environment
source /.venv/bin/activate

# Keep the container running with an interactive shell
exec /bin/bash
