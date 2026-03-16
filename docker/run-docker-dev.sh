#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Timezone
TZ="Europe/Madrid"

# Container Name
CONTAINER_NAME="photomigrator-dev"

# Port
PORT=6071

# Change if you have other folder's deployment
APP_DIR="../"
CONFIG_DIR="../config"
DATA_DIR="../data"

# Change to your PUID/PGID
PUID=1001
PGID=1001

export TZ
export CONTAINER_NAME
export PORT
export APP_DIR
export CONFIG_DIR
export DATA_DIR
export PUID
export PGID

mkdir -p "$APP_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR"

echo "Stopping any running container publishing port $PORT (no removal)..."
ids="$(docker ps -q --filter "publish=$PORT" || true)"
if [[ -n "$ids" ]]; then
  # shellcheck disable=SC2086
  docker stop $ids >/dev/null || true
fi

echo "Removing only the compose container name if it exists: $CONTAINER_NAME"
if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null || true
fi

echo "Removing dangling and horphans images..."
docker image prune -a -f

echo "Starting compose (build + force recreate + remove orphans)..."
docker compose -f "$COMPOSE_FILE" build --no-cache
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

# echo "Logs:"
# docker compose -f "$COMPOSE_FILE" logs -f
