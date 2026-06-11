#!/bin/bash

CONFIG_DIR="/docker"
DOCKER_CONF_FILE="$CONFIG_DIR/docker.conf"
DEFAULT_DOCKER_CONF_FILE="/app/default_docker.conf"

CONFIG_FILE="$CONFIG_DIR/Config.ini"
DEFAULT_CONFIG="/app/default_config.ini"

# To enter in interective shell moode we can call this from Shell:
# docker run -it --rm -v "${PWD}:/docker" -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest bash
if [[ "$1" == "bash" ]]; then
    echo "🔧 Entering interactive shell..."
    exec /bin/bash
fi

echo "📂 Checking mounted files in /docker:"
ls -l "$CONFIG_DIR"

# docker.conf
if [ ! -r "$DOCKER_CONF_FILE" ]; then
    echo "❌ docker.conf not found or not readable in current folder ($DOCKER_CONF_FILE)"
    if [ -w "$CONFIG_DIR" ]; then
        echo "🛠️  Creating a default docker.conf file..."
        cp "$DEFAULT_DOCKER_CONF_FILE" "$DOCKER_CONF_FILE"
    else
        echo "⚠️  Cannot write to $CONFIG_DIR. Please create docker.conf manually."
    fi
else
    echo "✅ docker.conf found"
fi

# Config.ini
echo "🚀 Initializing container and launching PhotoMigrator..."
if [ ! -r "$CONFIG_FILE" ]; then
    echo "❌ Config.ini not found or not readable in current folder ($CONFIG_FILE)"
    if [ -w "$CONFIG_DIR" ]; then
        echo "🛠️  Creating a default configuration file..."
        cp "$DEFAULT_CONFIG" "$CONFIG_FILE"
        echo "✏️  Please edit Config.ini with your settings and run the script again."
    else
        echo "⚠️  Cannot write to $CONFIG_DIR. Please create Config.ini manually."
    fi
    exit 1
else
    echo "✅ Config.ini found"
fi

exec python3 /app/src/PhotoMigrator.py "$@"
