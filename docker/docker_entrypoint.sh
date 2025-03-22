#!/bin/bash

CONFIG_FILE="/app/Config.ini"
DEFAULT_CONFIG="/app/default_config.ini"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config.ini not found in the current directory."
    echo "Creating a default configuration file..."
    cp "$DEFAULT_CONFIG" "$CONFIG_FILE"
    echo "Please edit Config.ini with your settings and run the script again."
    exit 1
fi

exec python3 /app/src/CloudPhotoMigrator.py "$@"
