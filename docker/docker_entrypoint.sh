#!/bin/bash

DOCKER_CONF_FILE="/data/docker.conf"
DEFAULT_DOCKER_CONF_FILE="/app/default_docker.conf"

CONFIG_FILE="/data/Config.ini"
DEFAULT_CONFIG="/app/default_config.ini"

if [[ "$1" == "bash" ]]; then
    echo "🔧 Entering interactive shell..."
    exec /bin/bash
fi

if [ ! -f "$DOCKER_CONF_FILE" ]; then
    echo "❌ docker.conf not found in the current folder."
    echo "Creating a default docker.conf file..."
    cp "$DEFAULT_DOCKER_CONF_FILE" "$DOCKER_CONF_FILE"
fi

echo "🚀 Initializing container and launching CloudPhotoMigrator..."
echo "Looking for: Config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config.ini not found in the current folder."
    echo "Creating a default configuration file..."
    cp "$DEFAULT_CONFIG" "$CONFIG_FILE"
    echo "Please edit Config.ini with your settings and run the script again."
    exit 1
fi

exec python3 /app/src/CloudPhotoMigrator.py "$@"
