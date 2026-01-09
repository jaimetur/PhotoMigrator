import os
import re
import sys
from configparser import ConfigParser

from Core.GlobalVariables import LOGGER, FOLDERNAME_LOGS, CONFIGURATION_FILE
from Utils.StandaloneUtils import resolve_external_path

CONFIG = None


def load_config(config_file=CONFIGURATION_FILE, section_to_load='all'):
    """
    Load the configuration file and populate the global CONFIG dict.

    Args:
        config_file (str): Path to the configuration file.
        section_to_load (str): Section name to load, or 'all' to load everything
                               from the predefined config_keys map.

    Returns:
        dict: Global CONFIG dictionary with loaded sections/keys.

    Notes:
        - This function caches results in the global CONFIG.
        - If a section was already loaded before, it won't be reloaded.
        - It performs a preprocessing step to ignore duplicate keys inside the same section,
          keeping the first occurrence and logging a warning once per duplicated key.
        - It also removes inline comments (starting with '#') from values.
    """
    # Load and set global CONFIG variable
    global CONFIG

    # If configuration is already loaded and contains the requested section, return it
    if CONFIG:
        sections_loaded = CONFIG.keys()
        if section_to_load in sections_loaded:
            return CONFIG  # Configuration already read previously
    else:
        CONFIG = {}

    # Resolve config file path properly (works for docker and non-docker environments)
    config_file = resolve_external_path(config_file)

    LOGGER.info(f"Searching for section(s) [{section_to_load}] in configuration file '{config_file}'...")
    if not os.path.exists(config_file):
        LOGGER.error(f"Configuration file '{config_file}' not found. Exiting...")
        sys.exit(1)  # Exit program if config file is not found

    LOGGER.info(f"Configuration file found. Loading configuration for section(s) '{section_to_load}'...")

    # Preprocess the file to remove duplicate keys before reading it with ConfigParser
    seen_keys = set()          # Set to store unique (section, key) pairs
    logged_warnings = set()    # Set to avoid logging duplicate warnings multiple times
    cleaned_lines = []

    with open(config_file, 'r', encoding='utf-8') as f:
        section = None
        for line in f:
            stripped_line = line.strip()

            # Detect section headers
            if stripped_line.startswith("[") and stripped_line.endswith("]"):
                section = stripped_line
                if section_to_load in section or section_to_load.lower() == 'all':
                    cleaned_lines.append(line)

            # Detect key-value within a section
            elif "=" in stripped_line and section:
                # Only process the sections indicated in section_to_load
                if section_to_load in section or section_to_load.lower() == 'all':
                    key = stripped_line.split("=", 1)[0].strip()
                    unique_key = (section, key)  # Unique key composed by section + key
                    if unique_key in seen_keys:
                        # Log warning only once per duplicate key
                        if unique_key not in logged_warnings:
                            LOGGER.warning(f"Duplicate key found in '{config_file}. Key: '{key}' in section {section}, keeping first.")
                            logged_warnings.add(unique_key)
                        continue  # Skip duplicated key
                    seen_keys.add(unique_key)
                    cleaned_lines.append(line)

            else:
                # Keep comments and empty lines
                cleaned_lines.append(line)

    # Keep cleaned configuration in-memory
    cleaned_config = "\n".join(cleaned_lines)

    # Load cleaned config using ConfigParser
    config = ConfigParser()
    config.optionxform = str  # Preserve case sensitivity
    config.read_string(cleaned_config)  # Read from cleaned string

    # Remove inline comments from config values
    def clean_value(value):
        if value.strip().startswith('#'):
            return ''
        return re.split(r'\s+#', value, maxsplit=1)[0].strip()

    # Define the sections and keys to read from config file
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
            'asset_to'
        ],
        'TimeZone': ['timezone']
    }

    # Read all defined keys
    for section, keys in config_keys.items():
        if section == section_to_load or section_to_load.lower() == 'all':
            if section not in CONFIG:
                CONFIG[section] = {}  # Ensure section exists in CONFIG dict

            for key in keys:
                if config.has_option(section, key):
                    value = clean_value(config.get(section, key, raw=True))
                    CONFIG[section][key] = value  # Add to dict without overwriting other sections
                    if key.strip() == '':
                        LOGGER.warning(f"WARNING: Missing value for key '{key}' in section '{section}', skipping.")
                else:
                    LOGGER.warning(f"WARNING: Missing key '{key}' in section '{section}', skipping.")

    LOGGER.info(f"Configuration Read Successfully from '{config_file}' for section '{section_to_load}'.")
    return CONFIG


if __name__ == "__main__":
    # Create timestamp and initialize LOGGER for standalone execution
    from datetime import datetime
    from CustomLogger import log_setup
    from Core.GlobalVariables import LOG_LEVEL, ARGS

    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{sys.argv[0]}_{TIMESTAMP}"
    log_folder = resolve_external_path(FOLDERNAME_LOGS)
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

    # Print each key-value in separate lines
    for key, value in CONFIG.items():
        print(f"{key}: {value}")
