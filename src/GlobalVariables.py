from datetime import datetime
import textwrap
import logging

#---------------------------------------
# GLOBAL VARIABLES FOR THE WHOLE PROJECT
#---------------------------------------

COPYRIGHT_TEXT                  = "(c) 2024-2025 - Jaime Tur (@jaimetur)"
SCRIPT_NAME                     = "PhotoMigrator"
SCRIPT_VERSION                  = "v3.3.1"
SCRIPT_DATE                     = "2025-06-10"
SCRIPT_NAME_VERSION             = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
GPTH_VERSION                    = "4.0.8"
EXIF_VERSION                    = "3.0.0"
INCLUDE_EXIF_TOOL               = True
COMPILE_IN_ONE_FILE             = True
RESOURCES_IN_CURRENT_FOLDER     = True
LOG_FOLDER_FILENAME             = ""
START_TIME                      = datetime.now()
TIMESTAMP                       = datetime.now().strftime("%Y%m%d-%H%M%S")
HELP_TEXTS                      = None
ARGS                            = None
PARSER                          = None
LOGGER                          = None
LOG_LEVEL_MIN                   = logging.DEBUG
LOG_LEVEL                       = logging.INFO

# List of Folder to Deprioritize when looking for duplicates.
DEPRIORITIZE_FOLDERS_PATTERNS   = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*No-Albums', '*Others', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

# Script description
SCRIPT_DESCRIPTION              = textwrap.dedent(f"""
                                {SCRIPT_NAME_VERSION} - {SCRIPT_DATE}
                                
                                Multi-Platform/Multi-Arch tool designed to Interact and Manage different Photo Cloud Services
                                such as Google Photos, Synology Photos, Immich Photos & Apple Photos.
                                
                                (c) 2024-2025 by Jaime Tur (@jaimetur)
                                """
                                )

PHOTO_EXT                       = ['.3fr', '.ari', '.arw', '.cap', '.cin', '.cr2', '.cr3', '.crw', '.dcr', '.dng', '.erf', '.fff', '.iiq', '.k25', '.kdc', '.mrw', '.nef', '.nrw', '.orf', '.ori', '.pef', '.psd', '.raf', '.raw', '.rw2', '.rwl', '.sr2', '.srf', '.srw', '.x3f', '.avif', '.bmp', '.gif', '.heic', '.heif', '.hif', '.insp', '.jp2', '.jpe', '.jpeg', '.jpg', '.jxl', '.png', '.svg', '.tif', '.tiff', '.webp']
VIDEO_EXT                       = ['.3gp', '.3gpp', '.avi', '.flv', '.insv', '.m2t', '.m2ts', '.m4v', '.mkv', '.mov', '.mp4', '.mpe', '.mpeg', '.mpg', '.mts', '.vob', '.webm', '.wmv']
SIDECAR_EXT                     = ['.xmp']
METADATA_EXT                    = ['.json']









