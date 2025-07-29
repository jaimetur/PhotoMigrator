import logging
import os
import textwrap
from datetime import datetime

from colorama import Fore

#---------------------------------------
# GLOBAL VARIABLES FOR THE WHOLE PROJECT
#---------------------------------------
COPYRIGHT_TEXT                  = "(c) 2024-2025 - Jaime Tur (@jaimetur)"
TOOL_NAME                       = "PhotoMigrator"
TOOL_VERSION_WITHOUT_V          = "3.4.4"
TOOL_VERSION                    = f"v{TOOL_VERSION_WITHOUT_V}"
TOOL_DATE                       = "2025-07-25"
TOOL_NAME_VERSION               = f"{TOOL_NAME} {TOOL_VERSION}"

GPTH_VERSION                    = "4.0.9"
EXIF_VERSION                    = "13.30"
INCLUDE_EXIF_TOOL               = True
COMPILE_IN_ONE_FILE             = True
RESOURCES_IN_CURRENT_FOLDER     = True
START_TIME                      = datetime.now()
TIMESTAMP                       = datetime.now().strftime("%Y%m%d-%H%M%S")

# Define Project root folder
PROJECT_ROOT                    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Customizable DIR Folders
CONFIGURATION_FILE              = "Config.ini"                                  # To be Changed in set_FOLDERS
FOLDERNAME_GPTH                 = 'gpth_tool'                                   # To be Changed in set_FOLDERS
FOLDERNAME_EXIFTOOL             = 'exif_tool'                                   # To be Changed in set_FOLDERS
FOLDERNAME_ALBUMS               = "Albums"                                      # To be Changed in set_FOLDERS
FOLDERNAME_NO_ALBUMS            = "ALL_PHOTOS"                                  # To be Changed in set_FOLDERS
FOLDERNAME_DUPLICATES_OUTPUT    = "Duplicates_outputs"                          # To be Changed in set_FOLDERS
FOLDERNAME_EXTRACTED_DATES      = "Extracted_Dates"                             # To be Changed in set_FOLDERS
FOLDERNAME_LOGS                 = "Logs"                                        # To be Changed in set_FOLDERS
LOG_FILENAME                    = "PhotoMigrator"                               # To be Changed in set_LOGGER
LOG_LEVEL                       = logging.INFO                                  # To be Changed in set_LOGGER

VERBOSE_LEVEL_NUM               = 5
LOG_LEVEL_MIN                   = VERBOSE_LEVEL_NUM
HELP_TEXTS                      = None                                          # To be Changed in set_HELP_TEXTS
ARGS                            = None                                          # To be Changed in set_ARGS_PARSER
PARSER                          = None                                          # To be Changed in set_ARGS_PARSER
LOGGER                          = None                                          # To be Changed in set_LOGGER

# Configure parameters for CustomHelpFormatter & CustomPager
MAX_SHORT_ARGUMENT_LENGTH       = 13
MAX_HELP_POSITION               = 120
IDENT_ARGUMENT_DESCRIPTION      = MAX_SHORT_ARGUMENT_LENGTH + 2
IDENT_USAGE_DESCRIPTION         = 24
SHORT_LONG_ARGUMENTS_SEPARATOR  = ';'

# TAG and TAGS Colored for messages output (in console and log)
MSG_TAGS = {
    'VERBOSE'                   : "VERBOSE : ",
    'DEBUG'                     : "DEBUG   : ",
    'INFO'                      : "INFO    : ",
    'WARNING'                   : "WARNING : ",
    'ERROR'                     : "ERROR   : ",
    'CRITICAL'                  : "CRITICAL: ",
}
MSG_TAGS_COLORED = {
    'VERBOSE'                   : f"{Fore.CYAN}{MSG_TAGS['VERBOSE']}",
    'DEBUG'                     : f"{Fore.LIGHTCYAN_EX}{MSG_TAGS['DEBUG']}",
    'INFO'                      : f"{Fore.LIGHTWHITE_EX}{MSG_TAGS['INFO']}",
    'WARNING'                   : f"{Fore.YELLOW}{MSG_TAGS['WARNING']}",
    'ERROR'                     : f"{Fore.RED}{MSG_TAGS['ERROR']}",
    'CRITICAL'                  : f"{Fore.MAGENTA}{MSG_TAGS['CRITICAL']}",
}

# Supplemental Metadata Suffix
SUPPLEMENTAL_METADATA           = "supplemental-metadata"

# List of special suffixes from Google Photos:
SPECIAL_SUFFIXES = [
    '-EFFECTS',
    '-MOTION',
    '-ANIMATION',
    '-SMILE',
    '-COLLAGE',
    '-MIX',
]

EDITTED_SUFFIXES = [
    '-edited',      # EN
    '-edytowane',   # PL
    '-bearbeitet',  # DE
    '-bewerkt',     # NL
    '-編集済み',     # JA
    '-modificato',  # IT
    '-modifié',     # FR
    '-ha editado',  # ES
    '-editat',      # CA
]

# List of Folder to Deprioritize when looking for duplicates.
DEPRIORITIZE_FOLDERS_PATTERNS   = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*No-Albums', '*Others', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

# Supported Extensions Lists
PIL_SUPPORTED_EXTENSIONS        = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp']
PHOTO_EXT                       = ['.3fr', '.ari', '.arw', '.cap', '.cin', '.cr2', '.cr3', '.crw', '.dcr', '.dng', '.erf', '.fff', '.iiq', '.k25', '.kdc', '.mrw', '.nef', '.nrw', '.orf', '.ori', '.pef', '.psd', '.raf', '.raw', '.rw2', '.rwl', '.sr2', '.srf', '.srw', '.x3f', '.avif', '.bmp', '.gif', '.heic', '.heif', '.hif', '.insp', '.jp2', '.jpe', '.jpeg', '.jpg', '.jxl', '.png', '.svg', '.tif', '.tiff', '.webp']
VIDEO_EXT                       = ['.3gp', '.3gpp', '.avi', '.flv', '.insv', '.m2t', '.m2ts', '.m4v', '.mkv', '.mov', '.mp4', '.mpe', '.mpeg', '.mpg', '.mts', '.vob', '.webm', '.wmv']
METADATA_EXT                    = ['.json']
SIDECAR_EXT                     = ['.xmp']

# Tool Banner
BANNER = textwrap.dedent(rf"""
         ____  _           _        __  __ _                 _
        |  _ \| |__   ___ | |_ ___ |  \/  (_) __ _ _ __ __ _| |_ ___  _ __
        | |_) | '_ \ / _ \| __/ _ \| |\/| | |/ _` | '__/ _` | __/ _ \| '__|
        |  __/| | | | (_) | || (_) | |  | | | (_| | | | (_| | || (_) | |
        |_|   |_| |_|\___/ \__\___/|_|  |_|_|\__, |_|  \__,_|\__\___/|_|
                                             |___/ {TOOL_VERSION} ({TOOL_DATE})
        """).lstrip("\n")  # Elimina solo la primera línea en blanco

# Tool description
TOOL_DESCRIPTION = textwrap.dedent(f"""{TOOL_NAME_VERSION} - {TOOL_DATE}

          Multi-Platform/Multi-Arch tool designed to Interact and Manage different Photo Cloud Services
          such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

          ©️ 2024-2025 by Jaime Tur (@jaimetur)
          """
                                   )





