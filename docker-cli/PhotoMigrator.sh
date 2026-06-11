#!/bin/bash

# Set default tag
RELEASE_TAG="latest-stable"

# Set a default TZ (e.g. UTC) in case docker.conf does not provide one
TZ="UTC"

# Linux image repo
IMAGE_REPO="jaimetur/photomigrator-linux"

# Load from docker.conf if exists and
# manually parse docker.conf to support inline and full-line comments
if [ -f "docker.conf" ]; then
  while IFS= read -r line; do
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" || "$line" == \#* ]] && continue
    line=$(echo "$line" | cut -d '#' -f1 | sed 's/[[:space:]]*$//')

    key=$(echo "$line" | cut -d '=' -f1 | sed 's/[[:space:]]//g')
    value=$(echo "$line" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ "$key" == "RELEASE_TAG" ]]; then
      RELEASE_TAG="$value"
    elif [[ "$key" == "TZ" ]]; then
      TZ="$value"
    fi
  done < docker.conf
fi

CURRENT_DIR="$(pwd)"

echo "Pulling Docker image: ${IMAGE_REPO}:${RELEASE_TAG}"
docker pull "${IMAGE_REPO}:${RELEASE_TAG}"

echo "Launching container with TAG='${RELEASE_TAG}' and TZ='${TZ}'..."
docker run -it --rm \
  -v "$CURRENT_DIR":/docker \
  -e TZ="${TZ}" \
  "${IMAGE_REPO}:${RELEASE_TAG}" "$@"

