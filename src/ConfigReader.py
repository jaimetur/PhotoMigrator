from configparser import ConfigParser
import os, sys

CONFIG = None

def load_config(config_file='CONFIG.ini'):
    #
    # Load and Set Global CONFIG variable
    #
    from GlobalVariables import LOGGER  # Import global LOGGER
    global CONFIG

    if CONFIG:
        return CONFIG  # Configuration already read previously

    LOGGER.info(f"INFO    : Searching for configuration file '{config_file}'...")
    if not os.path.exists(config_file):
        LOGGER.error(f"ERROR   : Configuration file '{config_file}' not found. Exiting...")
        sys.exit(1)  # Termina el programa si no encuentra el archivo

    CONFIG = {}
    LOGGER.info(f"INFO    : Configuration file found. Loading configuration...")

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
                cleaned_lines.append(line)
            elif "=" in stripped_line and section:  # Detectar clave dentro de una sección
                key = stripped_line.split("=", 1)[0].strip()
                unique_key = (section, key)  # Crear clave única combinando sección y clave
                if unique_key in seen_keys:
                    if unique_key not in logged_warnings:  # Solo mostrar el mensaje una vez
                        LOGGER.warning(f"WARNING : Duplicate key '{key}' in section {section}, keeping first.")
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
        return value.split('#', 1)[0].strip() if value else None  # Evita errores si el valor es None

    # Define the Sections and Keys to find in config_file
    config_keys = {
        'Synology Photos': ['SYNOLOGY_URL', 'SYNOLOGY_USERNAME', 'SYNOLOGY_PASSWORD', 'SYNOLOGY_ROOT_PHOTOS_PATH'],
        'Immich Photos': ['IMMICH_URL', 'IMMICH_ADMIN_API_KEY', 'IMMICH_USER_API_KEY', 'IMMICH_USERNAME', 'IMMICH_PASSWORD', 'IMMICH_FILTER_ARCHIVE', 'IMMICH_FILTER_FROM', 'IMMICH_FILTER_TO', 'IMMICH_FILTER_COUNTRY', 'IMMICH_FILTER_CITY', 'IMMICH_FILTER_PERSON'],
        'Apple Photos': ['max_photos', 'appleid', 'applepwd', 'album', 'to_directory', 'date_from', 'date_to', 'asset_from', 'asset_to'],
        'TimeZone': ['timezone']
    }

    # Read all defined keys
    for section, keys in config_keys.items():
        for key in keys:
            if config.has_option(section, key):
                CONFIG[key] = clean_value(config.get(section, key, raw=True))
                if CONFIG[key].strip() == '':
                    LOGGER.warning(f"WARNING : Missing value for key '{key}' in section '{section}', skipping.")
            else:
                LOGGER.warning(f"WARNING : Missing key '{key}' in section '{section}', skipping.")

    # Additional default values to add to CONFIG
    CONFIG['downloadedphotos'] = 0
    CONFIG['skippedphotos'] = 0
    CONFIG['photofileexists'] = 0

    LOGGER.info(f"INFO    : Configuration Read Successfully from '{config_file}'.")
    return CONFIG


if __name__ == "__main__":
    # Create timestamp, and initialize LOGGER.
    from datetime import datetime
    from CustomLogger import log_setup
    import logging
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{sys.argv[0]}_{TIMESTAMP}"
    log_folder = "Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename, log_level=logging.DEBUG)

    if len(sys.argv[1:]) == 0:
        CONFIG = load_config('CONFIG.ini')
        print("\nUsing Configuration File: ['CONFIG.ini']\n")
    else:
        CONFIG = load_config(sys.argv[1:])
        print("\nUsing Configuration File:", sys.argv[1:], "\n")

    # Imprimir cada clave-valor en líneas separadas
    for key, value in CONFIG.items():
        print(f"{key}: {value}")
