# Module to define Globals Variables accesible to all other modules
from datetime import datetime
import textwrap
import os,sys
import logging

#---------------------------------------
# GLOBAL VARIABLES FOR THE WHOLE PROJECT
#---------------------------------------
SCRIPT_NAME                     = "CloudPhotoMigrator"
SCRIPT_VERSION                  = "v3.1.0-beta1"
SCRIPT_DATE                     = "2025-03-31"
SCRIPT_NAME_VERSION             = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
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
                                
                                Multi-Platform/Multi-Arch toot designed to Interact and Manage different Photo Cloud Services
                                such as Google Photos, Synology Photos, Immich Photos & Apple Photos.
                                
                                (c) 2024-2025 by Jaime Tur (@jaimetur)
                                """
                                )

PHOTO_EXT                       = ['.3fr', '.ari', '.arw', '.cap', '.cin', '.cr2', '.cr3', '.crw', '.dcr', '.dng', '.erf', '.fff', '.iiq', '.k25', '.kdc', '.mrw', '.nef', '.nrw', '.orf', '.ori', '.pef', '.psd', '.raf', '.raw', '.rw2', '.rwl', '.sr2', '.srf', '.srw', '.x3f', '.avif', '.bmp', '.gif', '.heic', '.heif', '.hif', '.insp', '.jp2', '.jpe', '.jpeg', '.jpg', '.jxl', '.png', '.svg', '.tif', '.tiff', '.webp']
VIDEO_EXT                       = ['.3gp', '.3gpp', '.avi', '.flv', '.insv', '.m2t', '.m2ts', '.m4v', '.mkv', '.mov', '.mp4', '.mpe', '.mpeg', '.mpg', '.mts', '.vob', '.webm', '.wmv']
SIDECAR_EXT                     = ['.xmp', '.json']

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# FUNCTIONS TO INITIALIZE GLOBAL VARIABLES THAT DEPENDS OF OTHER MODULES
# Since we cannot import other modules directly on the GlobalVariables.py module to avoid circular references, we need to initialize those variables using independent functions.
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def is_inside_docker():
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"

def resolve_path(user_path):
    """
    Converts a user_path into a valid absolute path.

    Inside Docker:
      - If the path has a Windows drive letter (e.g., C:), raise an error.
      - If it's an absolute path and doesn't start with /docker, raise an error.
      - If it's relative, map it under /docker.
      - If it's absolute and starts with /docker, accept it as is.
    Outside Docker:
      - Return the absolute path normally (e.g., C:/ for Windows, /home for Linux).
    """

    # Skip non-string or empty inputs
    if not isinstance(user_path, str) or user_path.strip() == "":
        return user_path

    # Remove extra spaces and convert backslashes to forward slashes
    path_clean = user_path.strip().replace("\\", "/")

    # Normalize (handles . , .. , etc.)
    path_clean = os.path.normpath(path_clean)

    # Split any Windows drive letter, e.g. "C:/stuff" => drive="C:", tail="/stuff"
    drive, tail = os.path.splitdrive(path_clean)

    if is_inside_docker():
        # 1) If there's a Windows drive letter (e.g., "C:"), raise an error
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            raise ValueError(
                f"Cannot use a Windows drive letter '{drive}' inside Docker. "
                "Please provide a path under /docker or a relative path."
            )

        # 2) Check if path is absolute in a Unix sense
        if os.path.isabs(path_clean):
            # If it's an absolute path and does not start with /docker, raise an error
            if not path_clean.startswith("/docker"):
                raise ValueError(
                    f"Absolute path '{path_clean}' is outside Docker foder '/docker'. "
                    "Please provide a relative path or a /docker-based path."
                )
            # Otherwise, accept it as is (absolute under /docker)
            return os.path.abspath(path_clean)
        else:
            # 3) If it's relative, map it under /docker
            final_path = os.path.join("/docker", path_clean.lstrip("/"))
            return os.path.abspath(final_path)
    else:
        # Outside Docker, return absolute path on the local system
        return os.path.abspath(path_clean)


def set_ARGS_PARSER():
    from ArgsParser import parse_arguments, checkArgs, getParser
    global ARGS, PARSER
    ARGS, PARSER = parse_arguments()
    ARGS = checkArgs(ARGS, PARSER)
    # PARSER = getParser()

def set_LOGGER():
    from CustomLogger import log_setup
    global LOGGER, LOG_FOLDER_FILENAME
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    current_directory = os.getcwd()
    log_folder = resolve_path("Logs")
    log_filename=f"{script_name}_{TIMESTAMP}"
    LOG_FOLDER_FILENAME = os.path.join(current_directory, log_folder, log_filename)
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename, log_level=LOG_LEVEL_MIN, plain_log=False)
    LOGGER.setLevel(LOG_LEVEL)

def set_HELP_TEXT():
    from HelpTexts import set_help_texts
    global HELP_TEXTS
    HELP_TEXTS  = set_help_texts()

set_LOGGER()
set_ARGS_PARSER()
set_HELP_TEXT()








