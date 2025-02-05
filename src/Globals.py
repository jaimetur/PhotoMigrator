# Module to define Globals Variables accesible to all other modules
import os, sys
from datetime import datetime
from LoggerConfig import log_setup
from HelpTexts import set_help_texts
from ParseArgs import parse_arguments, checkArgs, getParser

LOG_FOLDER_FILENAME = ""

# Initialize the Logger
def log_init():
    global LOG_FOLDER_FILENAME
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    log_filename=f"{script_name}_{TIMESTAMP}"
    log_folder="Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename)
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)
    return LOGGER

# Script version & date
SCRIPT_NAME         = "CloudPhotoMigrator"
SCRIPT_VERSION      = "v3.0.0-alpha"
SCRIPT_DATE         = "2025-02-03"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"

# Script description
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Multi-Platform/Multi-Arch toot designed to Interact and Manage different Photo Cloud 
Services such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

(c) 2024-2025 by Jaime Tur (@jaimetur)
"""

# List of Folder to Desprioritize when looking for duplicates.
DEPRIORITIZE_FOLDERS_PATTERNS = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*No-Albums', '*Others', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

# Create START_TIME and TIMESTAMP
START_TIME = datetime.now()
TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")

# Set HELP Texts
HELP_TEXTS = set_help_texts()
# Obtain Input Arguments and Parse to check them.
ARGS = checkArgs(parse_arguments())
# Obtain the parser
PARSER = getParser()
# Initialize the logger.
LOGGER = log_init()





