#!/bin/bash

CONFIG_FILE="/data/Config.ini"
DEFAULT_CONFIG="/app/default_config.ini"

echo "Contenido en /data:"
ls -l /data

# Si no existe el archivo de configuración en la carpeta montada
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config.ini not found in the current folder."
    echo "Creating a default configuration file..."
    cp "$DEFAULT_CONFIG" "$CONFIG_FILE"
    echo "Please edit Config.ini with your settings and run the script again."
    exit 1
fi

# Ejecutar el script usando la configuración del volumen montado
exec python3 /app/src/CloudPhotoMigrator.py "$@"
