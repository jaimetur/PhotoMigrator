#!/bin/bash

DOCKER_CONF_FILE="/docker/docker.conf"
DEFAULT_DOCKER_CONF_FILE="/app/default_docker.conf"

CONFIG_FILE="/docker/Config.ini"
DEFAULT_CONFIG="/app/default_config.ini"

# To enter in interective shell moode we can call this from Shell:
# docker run -it --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/cloudphotomigrator:latest bash
if [[ "$1" == "bash" ]]; then
    echo "🔧 Entering interactive shell..."
    exec /bin/bash
fi

if [ ! -f "$DOCKER_CONF_FILE" ]; then
    echo "❌ docker.conf not found in the current folder."
    echo "Creating a default docker.conf file..."
    cp "$DEFAULT_DOCKER_CONF_FILE" "$DOCKER_CONF_FILE"
fi

echo "🚀 Initializing container and launching PhotoMigrator..."
echo "Looking for: Config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config.ini not found in the current folder."
    echo "Creating a default configuration file..."
    cp "$DEFAULT_CONFIG" "$CONFIG_FILE"
    echo "Please edit Config.ini with your settings and run the script again."
    exit 1
fi

exec python3 /app/src/PhotoMigrator.py "$@"
