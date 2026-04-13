#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1
clear
python3 rename_gpth_neo_files.py
echo "El proceso ha terminado. Pulsa Enter para salir..."
read