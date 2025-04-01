#!/bin/bash

# Set default tag
RELEASE_TAG="latest-stable"

# Set a default TZ (e.g. UTC) in case docker.conf does not provide one
TZ="UTC"

# Load from docker.conf if exists and
# Manually parse docker.conf to support inline and full-line comments
if [ -f "docker.conf" ]; then
  while IFS= read -r line; do
    # Remove leading/trailing whitespace
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Skip empty lines or full-line comments
    [[ -z "$line" || "$line" == \#* ]] && continue

    # Remove inline comment after value
    line=$(echo "$line" | cut -d '#' -f1 | sed 's/[[:space:]]*$//')

    # Parse key=value pairs
    key=$(echo "$line" | cut -d '=' -f1 | sed 's/[[:space:]]//g')
    value=$(echo "$line" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ "$key" == "RELEASE_TAG" ]]; then
      RELEASE_TAG="$value"
    elif [[ "$key" == "TZ" ]]; then
      TZ="$value"
    fi
  done < docker.conf
fi

# Get current directory
CURRENT_DIR="$(pwd)"

echo "🐳 Pulling Docker image: jaimetur/cloudphotomigrator:${RELEASE_TAG}"
docker pull "jaimetur/cloudphotomigrator:${RELEASE_TAG}"

echo "🚀 Launching container with TAG:'${RELEASE_TAG}' and TZ=: '${TZ}'..."
docker run -it --rm \
  -v "$CURRENT_DIR":/docker \
  -e TZ="${TZ}" \
  "jaimetur/cloudphotomigrator:${RELEASE_TAG}" "$@"
