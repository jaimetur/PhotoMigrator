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
    Converts a given user_path into a valid absolute path.
    If running inside Docker and the path is an absolute Windows path (C:/...),
    it raises an error to prevent mapping outside /data.

    Example flows:
    - ".\\folder" -> /data/folder
    - "C:\\Absolute\\path" -> ValueError (in Docker)
    """
    if not isinstance(user_path, str) or user_path.strip() == "":
        return user_path

    original = user_path
    print(f"DEBUG1 - original user_path: {original!r}")

    user_path = user_path.strip()
    print(f"DEBUG2 - stripped user_path: {user_path!r}")

    # Reemplazar backslashes
    user_path = user_path.replace("\\", "/")
    print(f"DEBUG3 - replaced backslash: {user_path!r}")

    # Normalizar con os.path.normpath
    user_path = os.path.normpath(user_path)
    print(f"DEBUG4 - normpath: {user_path!r}")

    if is_inside_docker():
        print(f"DEBUG: path_clean after slash replace = {user_path}")
        # Si detectamos drive letter (C:/, D:/...) en Docker, lanzamos error
        if re.match(r"^[a-zA-Z]:/", user_path):
            print("DEBUG3 matched drive letter!")
            raise ValueError(
                f"Cannot use absolute Windows path '{user_path}' inside Docker. "
                "Please provide a relative path inside the mounted folder."
            )
        else:
            print("DEBUG3 no match. path_clean=", user_path)
        # Caso normal: ruta relativa en Docker
        path_clean = user_path.lstrip("/")
        path_norm = os.path.normpath(path_clean)
        return os.path.abspath(os.path.join("/data", path_norm))
    else:
        # Fuera de Docker, normalizamos y retornamos absoluto
        path_norm = os.path.normpath(user_path)
        return os.path.abspath(path_norm)


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








