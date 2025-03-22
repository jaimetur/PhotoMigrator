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
    Converts user_path into a valid absolute path.

    Inside Docker:
      - If user_path is an absolute Windows path, check if it's inside HOST_MOUNT_PATH.
        If so, strip that prefix and map the remainder to /data.
        If outside, raise ValueError.
      - If user_path is a relative path, join it under /data.
      - If user_path starts with /data, accept it as is.
    Outside Docker:
      - Return the absolute local path normally.
    """

    if not isinstance(user_path, str) or user_path.strip() == "":
        return user_path

    path_clean = user_path.strip()

    # Convert backslashes to forward slashes for consistency
    path_clean = path_clean.replace("\\", "/")

    # Normalize (e.g. handle ./, ../)
    path_clean = os.path.normpath(path_clean)

    if is_inside_docker():
        host_mount = get_host_mount_path().replace("\\", "/").rstrip("/")
        # If HOST_MOUNT_PATH is empty, we can't handle absolute Windows paths
        # so any such path is invalid.

        # Detect if the user_path ya es una ruta /data
        if path_clean.startswith("/data"):
            # The user gave a Docker-based absolute path, accept it
            return os.path.abspath(path_clean)

        # If path is absolute in a Unix sense (like /folder), but not /data → error
        if path_clean.startswith("/"):
            raise ValueError(
                f"Absolute path '{user_path}' is outside /data in Docker. "
                f"Please use a relative path or a path under /data."
            )

        drive, tail = os.path.splitdrive(path_clean)
        # Check if there's a drive letter like 'C:'
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            if not host_mount:
                raise ValueError(
                    f"Cannot use absolute Windows path '{user_path}' because HOST_MOUNT_PATH is not defined."
                )
            # e.g. drive="C:", tail="/Temp_Unsync/Folder"
            # Confirm it's inside host_mount
            absolute_win_path = drive + tail  # "C:/Temp_Unsync/Folder"

            # If the host_mount is "C:/Temp_Unsync", then absolute_win_path must start with that
            # after normalization. For safety, let's ensure both are absolute and normalized.
            absolute_win_path = os.path.normpath(absolute_win_path.lstrip("/"))
            host_mount_norm = os.path.normpath(host_mount.lstrip("/"))

            # Check if it starts with e.g. "C:/Temp_Unsync"
            if not absolute_win_path.startswith(host_mount_norm):
                raise ValueError(
                    f"The path '{user_path}' is outside the mounted folder '{host_mount}'."
                )
            # Remove that prefix. E.g. if host_mount_norm="C:/Temp_Unsync"
            # and absolute_win_path="C:/Temp_Unsync/Folder/Sub"
            # remainder = "Folder/Sub"
            remainder = absolute_win_path[len(host_mount_norm):].lstrip("/\\")
            # Map remainder under /data
            return os.path.abspath(os.path.join("/data", remainder))
        else:
            # If no drive letter, treat as relative to /data
            return os.path.abspath(os.path.join("/data", path_clean.lstrip("/")))
    else:
        # Outside Docker: just return absolute local path
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








