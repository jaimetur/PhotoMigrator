# Module to define Globals Variables accesible to all other modules
import os
import posixpath

import Core.GlobalVariables as GV


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
      - If the path has a Windows drive letter (e.g. C:), raise an error.
      - If it's an absolute path and doesn't start with /docker, raise an error.
      - If it's absolute and starts with /docker, accept it as is.
      - If it's relative, join it under /docker, then normalize. If the result
        escapes /docker (e.g. /docker/../somefolder => /somefolder), raise an error.
    Outside Docker:
      - Return the absolute path normally.
    """

    # 1) Skip non-string or empty inputs
    if not isinstance(user_path, str) or user_path.strip() == "":
        return user_path

    # 2) Clean up the string and unify slashes
    path_clean = user_path.strip().replace("\\", "/")

    # 3) Normalize (handles ".", "..", etc.)
    path_clean = posixpath.normpath(path_clean)

    # 4) Split any Windows drive letter (e.g. "C:/stuff" => drive="C:", tail="/stuff")
    drive, tail = os.path.splitdrive(path_clean)

    if is_inside_docker():
        # (a) If there's a Windows drive letter, raise an error
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            raise ValueError(
                f"Cannot use paths with a Windows drive letter '{drive}' inside Docker."
                f"\nWrong Path detected: {user_path}"
                f"\nPlease provide a path under /docker or under the execution folder."
            )

        # (b) Check if path is absolute in a Unix sense
        if path_clean.startswith("/"):
            # Must start with "/docker" or raise an error
            if not path_clean.startswith("/docker"):
                raise ValueError(
                    f"Absolute path '{path_clean}' is outside the '/docker' folder."
                    f"\nPlease provide a path under /docker or under the execution folder."
                )
            # Normalize again and ensure it still stays under /docker
            final_path = posixpath.normpath(path_clean)
            if not final_path.startswith("/docker"):
                raise ValueError(
                    f"Path '{user_path}' escapes from '/docker' after normalization."
                    f"\nResult: '{final_path}'"
                    f"\nPlease provide a path under /docker or under the execution folder."
                )
            return final_path

        # (c) If it's relative, join it under /docker and then normalize again
        else:
            joined_path = posixpath.join("/docker", path_clean)
            final_path = posixpath.normpath(joined_path)

            # If after normalization it no longer starts with /docker, that means
            # we used '..' to escape the /docker directory => raise an error
            if not final_path.startswith("/docker"):
                raise ValueError(
                    f"Relative path '{user_path}' escapes from '/docker' after normalization.\n"
                    f"Resulting path: '{final_path}'\n"
                    "Please do not use '..' to go outside /docker."
                )
            return final_path
    else:
        # Outside Docker, return absolute path on the local system
        return os.path.abspath(path_clean)


def set_LOGGER():
    import logging
    import Core.GlobalVariables as GV
    from Core.GlobalVariables import ARGS
    from Core.CustomLogger import log_setup, VERBOSE_LEVEL_NUM  # traemos la constante de verbose
    from Core.GlobalFunctions import resolve_path
    import os, sys

    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    current_directory = os.getcwd()
    log_folder = resolve_path("Logs")
    log_filename = f"{script_name}_{GV.TIMESTAMP}"
    GV.LOG_FOLDER_FILENAME = os.path.join(current_directory, log_folder, log_filename)

    # 1) Inicializas el logger con el nivel por defecto
    GV.LOGGER = log_setup(
        log_folder=log_folder,
        log_filename=log_filename,
        log_level=GV.LOG_LEVEL_MIN,
        skip_logfile=False,
        skip_console=False,
        format=ARGS['log-format']
    )

    # 2) Mapeo explícito de niveles soportados
    level_str = ARGS['log-level'].lower()
    level_mapping = {
        'verbose'   : VERBOSE_LEVEL_NUM,
        'debug'     : logging.DEBUG,
        'info'      : logging.INFO,
        'warning'   : logging.WARNING,
        'error'     : logging.ERROR,
        'critical'  : logging.CRITICAL,
    }

    if level_str in level_mapping:
        new_level = level_mapping[level_str]
        GV.LOG_LEVEL = new_level

        # Cambiamos el nivel del logger
        GV.LOGGER.setLevel(new_level)
        # Y de cada handler
        for handler in GV.LOGGER.handlers:
            handler.setLevel(new_level)

        GV.LOGGER.info(f"Logging level changed to {level_str.upper()}")
    else:
        GV.LOGGER.warning(f"Unknown Logging level: {ARGS['log-level']}")

def set_ARGS_PARSER():
    from Core.ArgsParser import parse_arguments, checkArgs
    args, parser = parse_arguments()
    args = checkArgs(args, parser)
    GV.ARGS = args
    GV.PARSER = parser

def set_HELP_TEXT():
    from Core.HelpTexts import set_help_texts
    GV.HELP_TEXTS  = set_help_texts()











