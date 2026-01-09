import logging
import os
import platform
import posixpath
import sys
from pathlib import Path

from colorama import Style

from Core.GlobalVariables import MSG_TAGS, RESOURCES_IN_CURRENT_FOLDER, TOOL_NAME, MSG_TAGS_COLORED, PROJECT_ROOT
import Core.GlobalVariables as GV


def change_working_dir(change_dir=None):
    """
    Changes the current working directory to a predefined path when `change_dir` is provided.

    Notes:
        The target directory is currently hardcoded as:
        r"R:\\jaimetur\\PhotoMigrator"
    """
    if change_dir:
        """ Define the desired working path """
        WORKING_DIR = r"R:\jaimetur\PhotoMigrator"
        # Check whether the folder exists and switch to it if it does
        if os.path.exists(WORKING_DIR) and os.path.isdir(WORKING_DIR):
            os.chdir(WORKING_DIR)
            current_directory = os.getcwd()
            print(f"{MSG_TAGS['INFO']}Directory changed to: {os.getcwd()}")


def get_gpth_tool_path(base_path: str, exec_name: str, step_name='') -> str:
    """
    Returns the path to the GPTH executable.

    - If `base_path` is an executable file (exists and is executable), it is used as-is.
      The filename does not matter: gpth_v2, gpth-dev, whatever.

    - Otherwise, it is assumed to be a folder and `exec_name` is appended to it.
    """
    p = Path(base_path)

    # --------- Case 1: looks like a full executable ----------
    # `exists()` avoids false positives with non-existing folder paths
    # `os.access(..., os.X_OK)` ensures it is actually executable (optional but useful)
    if p.exists() and p.is_file() and os.access(p, os.X_OK):
        return resolve_internal_path(path_to_resolve=str(p), step_name=step_name)

    # --------- Case 2: directory (or a not-yet-created path) ----------
    # Use resolve_internal_path to access files or folders that will be packaged in binary executable mode:
    return resolve_internal_path(path_to_resolve=str(p / exec_name), step_name=step_name)


def get_exif_tool_path(base_path: str, step_name='') -> str:
    """
    Returns the path to the ExifTool executable.

    - If `base_path` is an existing executable file, it is returned as-is.
    - Otherwise, it is assumed to be a directory and the appropriate executable
      name is appended:
        * Linux / macOS → 'exiftool'
        * Windows       → 'exiftool.exe'
    """
    p = Path(base_path)

    # --------- Case 1: it is already a valid executable ----------
    if p.exists() and p.is_file() and os.access(p, os.X_OK):
        return resolve_internal_path(path_to_resolve=str(p), step_name=step_name)

    # --------- Case 2: it is (or will be) a directory ----------
    exec_name = "exiftool.exe" if platform.system().lower() == "windows" else "exiftool"
    return resolve_internal_path(path_to_resolve=str(p / exec_name), step_name=step_name)


def resolve_internal_path(path_to_resolve, step_name=''):
    """
    Returns the absolute path to the resource `path_to_resolve`, working in:
    - PyInstaller (onefile or standalone)
    - Nuitka (onefile or standalone)
    - Plain Python (from cwd or from dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because it is also used by build-binary.py which does not have any LOGGER created.
    compiled_source = globals().get("__compiled__")
    DEBUG_MODE = GV.LOG_LEVEL <= logging.DEBUG  # Set to False to silence
    if DEBUG_MODE:
        custom_print(f"{step_name}DEBUG_MODE = {DEBUG_MODE}", log_level=logging.DEBUG)
        custom_print(f"{step_name}---RESOURCE_PATH DEBUG INFO", log_level=logging.DEBUG)
        custom_print(f"{step_name}PATH TO RESOLVE             : {path_to_resolve}", log_level=logging.DEBUG)
        custom_print(f"{step_name}RESOURCES_IN_CURRENT_FOLDER : {RESOURCES_IN_CURRENT_FOLDER}", log_level=logging.DEBUG)
        custom_print(f"{step_name}sys.frozen                  : {getattr(sys, 'frozen', False)}", log_level=logging.DEBUG)
        custom_print(f"{step_name}NUITKA_ONEFILE_PARENT       : {'YES' if 'NUITKA_ONEFILE_PARENT' in os.environ else 'NO'}", log_level=logging.DEBUG)
        custom_print(f"{step_name}PROJECT_ROOT                : {PROJECT_ROOT}", log_level=logging.DEBUG)
        custom_print(f"{step_name}sys.argv[0]                 : {sys.argv[0]}", log_level=logging.DEBUG)
        custom_print(f"{step_name}sys.executable              : {sys.executable}", log_level=logging.DEBUG)
        custom_print(f"{step_name}os.getcwd()                 : {os.getcwd()}", log_level=logging.DEBUG)
        custom_print(f"{step_name}__file__                    : {globals().get('__file__', 'NO __file__')}", log_level=logging.DEBUG)
        try:
            if compiled_source:
                custom_print(f"{step_name}__compiled__.containing_dir : {compiled_source.containing_dir}", log_level=logging.DEBUG)
            else:
                custom_print(f"{step_name}__compiled__ not defined", log_level=logging.DEBUG)
        except NameError:
            custom_print(f"{step_name}__compiled__ not defined", log_level=logging.DEBUG)
        if hasattr(sys, '_MEIPASS'):
            custom_print(f"_MEIPASS                    : {sys._MEIPASS}", log_level=logging.DEBUG)
        else:
            custom_print(f"{step_name}_MEIPASS not defined", log_level=logging.DEBUG)
        print("")

    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        if DEBUG_MODE: custom_print(f"{step_name}Entering PyInstaller mode     -> base_path={base_path} (sys._MEIPASS)", log_level=logging.DEBUG)
    # Nuitka onefile
    elif "NUITKA_ONEFILE_PARENT" in os.environ:
        # base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(sys.executable)
        # base_path = PROJECT_ROOT
        if DEBUG_MODE: custom_print(f"{step_name}Entering Nuitka --onefile mode    -> base_path={base_path} (sys.executable)", log_level=logging.DEBUG)
    # Nuitka standalone
    elif compiled_source:
    # elif "__compiled__" in globals():
        base_path = os.path.join(compiled_source.containing_dir, TOOL_NAME + '.dist')
        # base_path = compiled_source
        if DEBUG_MODE: custom_print(f"{step_name}Entering Nuitka --standalone mode     -> base_path={base_path} (__compiled__.containing_dir)", log_level=logging.DEBUG)
    # Plain Python
    elif "__file__" in globals():
        if RESOURCES_IN_CURRENT_FOLDER:
            base_path = os.getcwd()
            if DEBUG_MODE: custom_print(f"{step_name}Entering Python mode (RESOURCES_IN_CURRENT_FOLDER={RESOURCES_IN_CURRENT_FOLDER})  -> base_path={base_path} (os.getcwd())", log_level=logging.DEBUG)
        else:
            # base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_path = PROJECT_ROOT
            if DEBUG_MODE: custom_print(f"{step_name}Entering Python mode (RESOURCES_IN_CURRENT_FOLDER={RESOURCES_IN_CURRENT_FOLDER})  -> base_path={base_path} (PROJECT_ROOT)", log_level=logging.DEBUG)
    else:
        base_path = os.getcwd()
        if DEBUG_MODE: custom_print(f"{step_name}Entering final fallback   -> base_path={base_path} (os.getcwd())", log_level=logging.DEBUG)

    # ✅ If the path already exists (absolute or relative), return it directly
    if path_to_resolve and os.path.exists(path_to_resolve):
        resolved_path = path_to_resolve
    else:
        resolved_path = os.path.join(base_path, path_to_resolve)
    if DEBUG_MODE:
        custom_print(f"{step_name}return path                 : {resolved_path}", log_level=logging.DEBUG)
        custom_print(f"{step_name}--- END RESOURCE_PATH DEBUG INFO", log_level=logging.DEBUG)
    return resolved_path


def resolve_external_path(user_path, step_name=''):
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
        # return resolve_internal_path(path_to_resolve=path_clean, step_name=step_name)


def is_inside_docker():
    """
    Detects whether the script is running inside a Docker container.

    Returns:
        bool: True if running inside Docker, otherwise False.
    """
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"

#------------------------------------------------------------------
# Replace original print to use the same GV.LOGGER formatter
def custom_print(*args, log_level=logging.INFO, **kwargs):
    """
    Prints messages with the same formatting/colors used by the GV.LOGGER output.

    Args:
        *args: Message parts to print.
        log_level (int): Logging level used to select the color tag.
        **kwargs: Extra keyword arguments passed to `print()`.
    """
    message = " ".join(str(a) for a in args)
    log_level_name = logging.getLevelName(log_level)
    colortag = MSG_TAGS_COLORED.get(log_level_name, MSG_TAGS_COLORED['INFO'])
    print(f"{colortag}{message}{Style.RESET_ALL}", **kwargs)
