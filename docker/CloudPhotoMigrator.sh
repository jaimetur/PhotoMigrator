#!/bin/bash

# Get the current directory (from the user context)
CURRENT_DIR="$(pwd)"

# Pull the latest version of the image to avoid using a cached one
docker pull jaimetur/cloudphotomigrator:latest

# Run the Docker container with the current directory mounted to /data
docker run --rm \
  -v "$CURRENT_DIR":/data \
  jaimetur/cloudphotomigrator:latest "$@"
