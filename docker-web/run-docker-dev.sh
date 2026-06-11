#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-dev.yml"
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

mkdir -p "$APP_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR"

echo "Stopping any running container publishing port $PORT_DEV (no removal)..."
ids="$(docker ps -q --filter "publish=$PORT_DEV" || true)"
if [[ -n "$ids" ]]; then
  # shellcheck disable=SC2086
  docker stop $ids >/dev/null || true
fi

echo "Removing only the compose container name if it exists: ${CONTAINER_NAME}-dev"
if docker ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}-dev"; then
  docker rm -f "${CONTAINER_NAME}-dev" >/dev/null || true
fi

echo "Removing dangling and horphans images..."
docker image prune -a -f

echo "Starting compose (build + force recreate + remove orphans)..."
docker compose -f "$COMPOSE_FILE" build --no-cache
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans

# echo "Logs:"
# docker compose -f "$COMPOSE_FILE" logs -f
