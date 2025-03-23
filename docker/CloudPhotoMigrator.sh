#!/bin/bash

# Set default tag
RELEASE_TAG="latest"

# Set a default TZ (e.g. UTC) in case docker.conf does not provide one
TZ="UTC"

# Load from docker.conf if exists
if [ -f "docker.conf" ]; then
  source docker.conf
fi

# Get current directory
CURRENT_DIR="$(pwd)"

echo "🐳 Pulling Docker image: jaimetur/cloudphotomigrator:${RELEASE_TAG}"
docker pull "jaimetur/cloudphotomigrator:${RELEASE_TAG}"

echo "🚀 Launching container with tag: ${RELEASE_TAG}"
docker run -it --rm \
  -v "$CURRENT_DIR":/docker \
  -e TZ="${TZ}" \
  "jaimetur/cloudphotomigrator:${RELEASE_TAG}" "$@"
