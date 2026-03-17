#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Load and export variables from .env to avoid duplicating config in this script.
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "Warning: .env file not found at $ENV_FILE. Falling back to defaults."
fi

# Dev-first mapping (uses *_DEV if provided in .env, otherwise regular vars/defaults)
TZ="${TZ:-Europe/Madrid}"
CONTAINER_NAME="${CONTAINER_NAME_DEV:-${CONTAINER_NAME:-photomigrator-dev}}"
PORT="${PORT_DEV:-${PORT:-6071}}"
APP_DIR="${APP_DIR:-../}"
CONFIG_DIR="${CONFIG_DIR:-../config}"
DATA_DIR="${DATA_DIR:-../data}"
VOLUMES_DIR="${VOLUMES_DIR:-/volume1}"
PUID="${PUID:-1001}"
PGID="${PGID:-1001}"
PHOTOMIGRATOR_WEB_DELETE_ROOTS="${PHOTOMIGRATOR_WEB_DELETE_ROOTS:-/app/data,/app/config,/app/volumes}"

export TZ CONTAINER_NAME PORT APP_DIR CONFIG_DIR DATA_DIR VOLUMES_DIR PUID PGID PHOTOMIGRATOR_WEB_DELETE_ROOTS

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
