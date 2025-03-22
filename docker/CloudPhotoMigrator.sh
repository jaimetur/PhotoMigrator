#!/bin/bash

# Get the current directory
CURRENT_DIR="$(pwd)"

# Run the Docker container with the current directory mounted to /data
docker run --rm \
  -v "$CURRENT_DIR":/data \
  jaimetur/cloudphotomigrator:latest "$@"
