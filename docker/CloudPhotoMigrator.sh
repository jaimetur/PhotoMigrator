#!/bin/bash

# Set default tag
RELEASE_TAG="latest"

# Load from .env if exists
if [ -f ".env" ]; then
  source .env
fi

# Get current directory
CURRENT_DIR="$(pwd)"

echo "🐳 Pulling Docker image: jaimetur/cloudphotomigrator:${RELEASE_TAG}"
docker pull "jaimetur/cloudphotomigrator:${RELEASE_TAG}"

echo "🚀 Launching container with tag: ${RELEASE_TAG}"
docker run -it --rm \
  -v "$CURRENT_DIR":/data \
  "jaimetur/cloudphotomigrator:${RELEASE_TAG}" "$@"
