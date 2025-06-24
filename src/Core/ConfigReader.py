import os
import re
import sys
from configparser import ConfigParser

from Core.GlobalVariables import LOGGER, FOLDERNAME_LOGS, CONFIGURATION_FILE
from Utils.StandaloneUtils import resolve_path

CONFIG = None

def load_config(config_file=CONFIGURATION_FILE, section_to_load='all'):
    #
    # Load and Set Global CONFIG variable
    #
    global CONFIG

    if CONFIG:
        sections_loaded = CONFIG.keys()
        if section_to_load in sections_loaded:
            return CONFIG  # Configuration already read previously
    else:
        CONFIG = {}
        
    # Resolver correctamente la ruta al archivo de configuración
    config_file = resolve_path(config_file)

    LOGGER.info(f"Searching for section(s) [{section_to_load}] in configuration file '{config_file}'...")
    if not os.path.exists(config_file):
        LOGGER.error(f"Configuration file '{config_file}' not found. Exiting...")
        sys.exit(1)  # Termina el programa si no encuentra el archivo

    LOGGER.info(f"Configuration file found. Loading configuration for section(s) '{section_to_load}'...")

    # Preprocesar el archivo para eliminar claves duplicadas antes de leerlo con ConfigParser
    seen_keys = set()  # Conjunto para almacenar claves únicas
    logged_warnings = set()  # Conjunto para evitar repetir advertencias de claves duplicadas
    cleaned_lines = []

    with open(config_file, 'r', encoding='utf-8') as f:
        section = None
        for line in f:
            stripped_line = line.strip()
            if stripped_line.startswith("[") and stripped_line.endswith("]"):  # Detectar sección
                section = stripped_line
                if section_to_load in section or section_to_load.lower() == 'all':
                    cleaned_lines.append(line)
            elif "=" in stripped_line and section:  # Detectar clave dentro de una sección
                # Only process those sections indicated in section_to_load
                if section_to_load in section or section_to_load.lower() == 'all':
                    key = stripped_line.split("=", 1)[0].strip()
                    unique_key = (section, key)  # Crear clave única combinando sección y clave
                    if unique_key in seen_keys:
                        if unique_key not in logged_warnings:  # Solo mostrar el mensaje una vez
                            LOGGER.warning(f"Duplicate key found in '{config_file}. Key: '{key}' in section {section}, keeping first.")
                            logged_warnings.add(unique_key)  # Registrar que ya mostramos el mensaje
                        continue  # Omitir clave duplicada
                    seen_keys.add(unique_key)
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)  # Mantener comentarios y líneas vacías

    # Guardar el archivo limpio en memoria
    cleaned_config = "\n".join(cleaned_lines)

    # Cargar el archivo limpio con ConfigParser
    config = ConfigParser()
    config.optionxform = str  # Mantener sensibilidad a mayúsculas/minúsculas
    config.read_string(cleaned_config)  # Leer desde la cadena limpia

    # Remove in-line comments from config_file
    def clean_value(value):
        if value.strip().startswith('#'):
            return ''
        return re.split(r'\s+#', value, maxsplit=1)[0].strip()

    # Define the Sections and Keys to find in config_file
    config_keys = {
        'Synology Photos': [
            'SYNOLOGY_URL',
            'SYNOLOGY_USERNAME_1',
            'SYNOLOGY_PASSWORD_1',
            'SYNOLOGY_USERNAME_2',
            'SYNOLOGY_PASSWORD_2',
            'SYNOLOGY_USERNAME_3',
            'SYNOLOGY_PASSWORD_3',
        ],
        'Immich Photos': [
            'IMMICH_URL',
            'IMMICH_API_KEY_ADMIN',
            'IMMICH_API_KEY_USER_1',
            'IMMICH_USERNAME_1',
            'IMMICH_PASSWORD_1',
            'IMMICH_API_KEY_USER_2',
            'IMMICH_USERNAME_2',
            'IMMICH_PASSWORD_2',
            'IMMICH_API_KEY_USER_3',
            'IMMICH_USERNAME_3',
            'IMMICH_PASSWORD_3',
        ],
        'Apple Photos': [
            'max_photos',
            'appleid',
            'applepwd',
            'album',
            'to_directory',
            'date_from',
            'date_to',
            'asset_from',
            'asset_to'],
        'TimeZone': ['timezone']
    }

    # Read all defined keys
    for section, keys in config_keys.items():
        if section == section_to_load or section_to_load.lower() == 'all':
            if section not in CONFIG:
                CONFIG[section] = {}  # Asegurar que la sección existe en el diccionario

            for key in keys:
                if config.has_option(section, key):
                    value = clean_value(config.get(section, key, raw=True))
                    CONFIG[section][key] = value  # Agregar al diccionario sin sobrescribir otros valores
                    if key.strip() == '':
                        LOGGER.warning(f"WARNING: Missing value for key '{key}' in section '{section}', skipping.")
                else:
                    LOGGER.warning(f"WARNING: Missing key '{key}' in section '{section}', skipping.")

    LOGGER.info(f"Configuration Read Successfully from '{config_file}' for section '{section_to_load}'.")
    return CONFIG


if __name__ == "__main__":
    # Create timestamp, and initialize LOGGER.
    from datetime import datetime
    from CustomLogger import log_setup
    from Core.GlobalVariables import LOG_LEVEL, ARGS

    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{sys.argv[0]}_{TIMESTAMP}"
    log_folder = resolve_path(FOLDERNAME_LOGS)
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(
        log_folder=log_folder,
        log_filename=log_filename,
        log_level=LOG_LEVEL,
        skip_logfile=False,
        skip_console=False,
        format=ARGS['log-format']
    )

    if len(sys.argv[1:]) == 0:
        CONFIG = load_config(config_file=f'../../{CONFIGURATION_FILE}', section_to_load='Synology Photos')
        print(f"\nUsing Configuration File: ['{CONFIGURATION_FILE}']\n")
    else:
        CONFIG = load_config(config_file=sys.argv[1], section_to_load='All')
        print("\nUsing Configuration File:", sys.argv[1:], "\n")

    # Imprimir cada clave-valor en líneas separadas
    for key, value in CONFIG.items():
        print(f"{key}: {value}")
