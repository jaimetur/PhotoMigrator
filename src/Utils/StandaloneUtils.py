import logging
import os
import platform
import posixpath
import shutil
import sys
import zipfile
from pathlib import Path

from colorama import Fore, Style

from Core.GlobalVariables import MSG_TAGS, RESOURCES_IN_CURRENT_FOLDER, TOOL_NAME, PROJECT_ROOT
import Core.GlobalVariables as GV


def _embedded_exiftool_module_path(executable_path: str | Path) -> Path:
    return Path(executable_path).resolve().parent / "lib" / "Image" / "ExifTool.pm"


def _extract_exiftool_bundle_if_needed(executable_path: str | Path) -> None:
    exe_path = Path(executable_path).resolve()
    module_path = _embedded_exiftool_module_path(exe_path)
    if module_path.exists():
        return

    bundle_root = exe_path.parent
    archive_candidates = [bundle_root / "others.zip"]
    if exe_path.suffix.lower() == ".exe":
        archive_candidates.insert(0, bundle_root / "windows.zip")

    for archive_path in archive_candidates:
        if not archive_path.exists():
            continue
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(bundle_root)
        except Exception:
            continue
        if module_path.exists():
            return


def _is_valid_exiftool_candidate(candidate_path: str | Path) -> bool:
    candidate = Path(candidate_path)
    if not candidate.exists() or not candidate.is_file():
        return False

    executable_name = candidate.name.lower()
    if executable_name not in {"exiftool", "exiftool.exe"}:
        return True

    module_path = _embedded_exiftool_module_path(candidate)
    if module_path.exists():
        return True

    sibling_archives = [candidate.parent / "others.zip", candidate.parent / "windows.zip"]
    return not any(archive.exists() for archive in sibling_archives)


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
    # Return the file even if it is not executable yet; ensure_executable() can fix permissions later.
    if p.exists() and p.is_file():
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
    raw_base_path = str(base_path or "").strip()
    p = Path(raw_base_path or ".")
    exec_name = "exiftool.exe" if platform.system().lower() == "windows" else "exiftool"

    # --------- Case 1: it is already a file path ----------
    # Return the file even if it is not executable yet; ensure_executable() can fix permissions later.
    if p.exists() and p.is_file():
        resolved_file = resolve_internal_path(path_to_resolve=str(p), step_name=step_name)
        _extract_exiftool_bundle_if_needed(resolved_file)
        if _is_valid_exiftool_candidate(resolved_file):
            return resolved_file

    # --------- Case 2: the user supplied an executable name available in PATH ----------
    if raw_base_path and not any(sep and sep in raw_base_path for sep in (os.sep, os.altsep)):
        direct_lookup = shutil.which(raw_base_path)
        if direct_lookup:
            return direct_lookup

    # --------- Case 3: it is (or will be) a directory ----------
    candidate = resolve_internal_path(path_to_resolve=str(p / exec_name), step_name=step_name)
    if os.path.exists(candidate):
        _extract_exiftool_bundle_if_needed(candidate)
    if _is_valid_exiftool_candidate(candidate):
        return candidate

    fallback_dirs = [
        os.path.join(PROJECT_ROOT, "exif_tool"),
        os.path.join(PROJECT_ROOT, "exif_Tool"),
        os.path.join(os.getcwd(), "exif_tool"),
        os.path.join(os.getcwd(), "exif_Tool"),
    ]
    for folder in fallback_dirs:
        fallback = os.path.join(folder, exec_name)
        if os.path.exists(fallback):
            _extract_exiftool_bundle_if_needed(fallback)
        if _is_valid_exiftool_candidate(fallback):
            return fallback

    system_candidate = shutil.which(exec_name)
    if system_candidate:
        return system_candidate
    return candidate


def resolve_internal_path(path_to_resolve, step_name=''):
    """
    Returns the absolute path to the resource `path_to_resolve`, working in:
    - PyInstaller (onefile or standalone)
    - Nuitka (onefile or standalone)
    - Plain Python (from cwd or from dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because it is also used by tools/BuildBinary.py which does not have any LOGGER created.
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
        # When the working directory changes during long-running jobs, bundled relative resources
        # such as exif_tool/ or gpth_tool/ must still resolve back to the project root.
        if (
            path_to_resolve
            and not os.path.isabs(path_to_resolve)
            and not os.path.exists(resolved_path)
        ):
            project_candidate = os.path.join(PROJECT_ROOT, path_to_resolve)
            if os.path.exists(project_candidate):
                resolved_path = project_candidate
    if DEBUG_MODE:
        custom_print(f"{step_name}return path                 : {resolved_path}", log_level=logging.DEBUG)
        custom_print(f"{step_name}--- END RESOURCE_PATH DEBUG INFO", log_level=logging.DEBUG)
    return resolved_path


def resolve_external_path(user_path, step_name=''):
    """
    Converts a user_path into a valid absolute path.

    Inside Docker:
      - If the path has a Windows drive letter (e.g. C:), raise an error.
      - Absolute paths are allowed only under /docker or /app.
      - If it's relative, join it under docker base root (default: /docker),
        then normalize. If the result escapes that root, raise an error.
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
        docker_base_root = os.environ.get("PHOTOMIGRATOR_DOCKER_BASE_PATH", "/docker").strip() or "/docker"
        docker_base_root = posixpath.normpath(docker_base_root)
        allowed_roots = ["/docker", "/app", docker_base_root]

        def _is_under_allowed_root(candidate_path: str) -> bool:
            normalized_candidate = posixpath.normpath(candidate_path)
            for root in allowed_roots:
                normalized_root = posixpath.normpath(root)
                if normalized_candidate == normalized_root or normalized_candidate.startswith(normalized_root + "/"):
                    return True
            return False

        # (a) If there's a Windows drive letter, raise an error
        if len(drive) == 2 and drive[1] == ":" and drive[0].isalpha():
            raise ValueError(
                f"Cannot use paths with a Windows drive letter '{drive}' inside Docker."
                f"\nWrong Path detected: {user_path}"
                f"\nPlease provide a path under /docker, /app, or under the execution folder."
            )

        # (b) Check if path is absolute in a Unix sense
        if path_clean.startswith("/"):
            if not _is_under_allowed_root(path_clean):
                raise ValueError(
                    f"Absolute path '{path_clean}' is outside allowed Docker folders: {', '.join(allowed_roots)}."
                    f"\nPlease provide a path under /docker, /app, or under the execution folder."
                )
            # Normalize again and ensure it still stays under allowed Docker folders
            final_path = posixpath.normpath(path_clean)
            if not _is_under_allowed_root(final_path):
                raise ValueError(
                    f"Path '{user_path}' escapes from allowed Docker folders after normalization."
                    f"\nResult: '{final_path}'"
                    f"\nPlease provide a path under /docker, /app, or under the execution folder."
                )
            return final_path

        # (c) If it's relative, join it under docker base root and then normalize again
        else:
            joined_path = posixpath.join(docker_base_root, path_clean)
            final_path = posixpath.normpath(joined_path)

            # If after normalization it no longer starts with docker_base_root, that means
            # we used '..' to escape the configured root => raise an error
            if not (
                final_path == docker_base_root
                or final_path.startswith(docker_base_root + "/")
            ):
                raise ValueError(
                    f"Relative path '{user_path}' escapes from '{docker_base_root}' after normalization.\n"
                    f"Resulting path: '{final_path}'\n"
                    f"Please do not use '..' to go outside {docker_base_root}."
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


def _supports_ansi_colors() -> bool:
    """Best-effort ANSI color support detection."""
    force_color = str(os.environ.get("PHOTOMIGRATOR_FORCE_COLOR") or os.environ.get("FORCE_COLOR") or os.environ.get("PY_COLORS") or os.environ.get("CLICOLOR_FORCE") or "").strip().lower()
    if force_color not in {"", "0", "false", "no", "off"}:
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    if term in ("", "dumb", "linux", "xterm-mono"):
        return False
    return True

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
    if _supports_ansi_colors():
        color_tags = {
            "VERBOSE": f"{Fore.CYAN}{MSG_TAGS['VERBOSE']}",
            "DEBUG": f"{Fore.LIGHTBLUE_EX}{MSG_TAGS['DEBUG']}",
            "INFO": f"{Fore.LIGHTWHITE_EX}{MSG_TAGS['INFO']}",
            "WARNING": f"{Fore.YELLOW}{MSG_TAGS['WARNING']}",
            "ERROR": f"{Fore.RED}{MSG_TAGS['ERROR']}",
            "CRITICAL": f"{Fore.WHITE}{Style.BRIGHT}{MSG_TAGS['CRITICAL']}",
        }
        colortag = color_tags.get(log_level_name, color_tags["INFO"])
        print(f"{colortag}{message}{Style.RESET_ALL}", **kwargs)
    else:
        plain_tag = MSG_TAGS.get(log_level_name, MSG_TAGS['INFO'])
        print(f"{plain_tag}{message}", **kwargs)
