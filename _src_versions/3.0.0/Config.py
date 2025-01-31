from configparser import ConfigParser
import os, sys

CONFIG = None

def load_config(config_file='Config.ini'):
    #
    # Load and Set Global CONFIG variable
    #
    from LoggerConfig import LOGGER  # Import global LOGGER
    global CONFIG

    if CONFIG:
        return CONFIG  # Configuration already read previously

    CONFIG = {}
    LOGGER.info(f"INFO: Searching for configuration file '{config_file}'...")

    config = ConfigParser()
    config.optionxform = str  # Mantener sensibilidad a mayúsculas/minúsculas
    config.read(config_file)

    # Remove in-line comments from config_file
    def clean_value(value):
        return value.split('#', 1)[0].strip() if value else None  # Evita errores si el valor es None

    # Define the Sections and Keys to find in config_file
    config_keys = {
        'Synology Photos': ['SYNOLOGY_URL', 'SYNOLOGY_USERNAME', 'SYNOLOGY_PASSWORD', 'SYNOLOGY_ROOT_PHOTOS_PATH' ],
        'Immich Photos': ['IMMICH_URL', 'IMMICH_API_KEY', 'IMMICH_USERNAME', 'IMMICH_PASSWORD'],
        'Apple Photos': ['max_photos', 'appleid', 'applepwd', 'album', 'to_directory', 'date_from', 'date_to', 'asset_from', 'asset_to'],
        'TimeZone': ['timezone']
    }

    # Read all defined keys
    for section, keys in config_keys.items():
        for key in keys:
            if config.has_option(section, key):
                CONFIG[key] = clean_value(config.get(section, key, raw=True))
                if CONFIG[key].strip() == '':
                    LOGGER.warning(f"WARNING: Missing value for key '{key}' in section '{section}', skipping.")
            else:
                LOGGER.warning(f"WARNING: Missing key '{key}' in section '{section}', skipping.")

    # Additional default values to add to CONFIG
    CONFIG['downloadedphotos'] = 0
    CONFIG['skippedphotos'] = 0
    CONFIG['photofileexists'] = 0

    LOGGER.info(f"INFO: Configuration Read Successfully from '{config_file}'.")
    return CONFIG

if __name__ == "__main__":
    # Create timestamp, and initialize LOGGER.
    from datetime import datetime
    from LoggerConfig import log_setup
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{sys.argv[0]}_{TIMESTAMP}"
    log_folder = "Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)

    if len(sys.argv[1:]) == 0:
        CONFIG = load_config('Config.ini')
        print("\nUsing Configuration File: ['Config.ini']\n")
    else:
        CONFIG = load_config(sys.argv[1:])
        print("\nUsing Configuration File:", sys.argv[1:], "\n")

    # Imprimir cada clave-valor en líneas separadas
    for key, value in CONFIG.items():
        print(f"{key}: {value}")
