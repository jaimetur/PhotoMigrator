import logging
import os
import platform
import posixpath
import sys
from pathlib import Path

from colorama import Style

from Core.GlobalVariables import MSG_TAGS, RESOURCES_IN_CURRENT_FOLDER, TOOL_NAME, MSG_TAGS_COLORED


def change_working_dir(change_dir=None):
    if change_dir:
        """ Definir la ruta de trabajo deseada """
        WORKING_DIR = r"R:\jaimetur\PhotoMigrator"
        # Verificar si la carpeta existe y cambiar a ella si existe
        if os.path.exists(WORKING_DIR) and os.path.isdir(WORKING_DIR):
            os.chdir(WORKING_DIR)
            current_directory = os.getcwd()
            print(f"{MSG_TAGS['INFO']}Directorio cambiado a: {os.getcwd()}")


def get_gpth_tool_path(base_path: str, exec_name: str) -> str:
    """
    Devuelve la ruta al ejecutable GPTH.

    - Si `base_path` es un fichero (existe y es ejecutable), se usa tal cual.
      No importa cómo se llame: gpth_v2, gpth-dev, lo-que-sea.

    - En cualquier otro caso se asume que es una carpeta y se concatena `tool_name`.
    """
    p = Path(base_path)

    # --------- Caso 1: parece un ejecutable completo ----------
    # `exists()` evita falsos positivos con rutas de carpetas inexistentes
    # `os.access(..., os.X_OK)` asegura que sea realmente ejecutable (opcional pero útil)
    if p.exists() and p.is_file() and os.access(p, os.X_OK):
        return resource_path(str(p))

    # --------- Caso 2: directorio (o ruta aún no creada) ----------
    # Usar resource_path para acceder a archivos o directorios que se empaquetarán en el modo de ejecutable binario:
    return resource_path(str(p / exec_name))


def get_exif_tool_path(base_path: str) -> str:
    """
    Devuelve la ruta al ejecutable de ExifTool.

    - Si `base_path` es un fichero ejecutable existente, se devuelve tal cual.
    - En caso contrario se asume que es un directorio y se concatena el
      nombre apropiado del ejecutable:
        * Linux / macOS → 'exiftool'
        * Windows       → 'exiftool.exe'
    """
    p = Path(base_path)

    # --------- Caso 1: ya es un ejecutable válido ----------
    if p.exists() and p.is_file() and os.access(p, os.X_OK):
        return resource_path(str(p))

    # --------- Caso 2: es (o será) un directorio ----------
    exec_name = "exiftool.exe" if platform.system().lower() == "windows" else "exiftool"
    return resource_path(str(p / exec_name))


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta al recurso 'relative_path', funcionando en:
    - PyInstaller (onefile o standalone)
    - Nuitka (onefile o standalone)
    - Python directo (desde cwd o desde dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because is also used by build-binary.py which has not any LOGGER created.
    compiled_source = globals().get("__compiled__")
    DEBUG_MODE = False  # Cambia a False para silenciar
    if DEBUG_MODE:
        custom_print(f"---DEBUG INFO", log_level=logging.DEBUG)
        custom_print(f"RESOURCES_IN_CURRENT_FOLDER : {RESOURCES_IN_CURRENT_FOLDER}", log_level=logging.DEBUG)
        custom_print(f"sys.frozen                  : {getattr(sys, 'frozen', False)}", log_level=logging.DEBUG)
        custom_print(f"NUITKA_ONEFILE_PARENT       : {'YES' if 'NUITKA_ONEFILE_PARENT' in os.environ else 'NO'}", log_level=logging.DEBUG)
        custom_print(f"sys.argv[0]                 : {sys.argv[0]}", log_level=logging.DEBUG)
        custom_print(f"sys.executable              : {sys.executable}", log_level=logging.DEBUG)
        custom_print(f"os.getcwd()                 : {os.getcwd()}", log_level=logging.DEBUG)
        custom_print(f"__file__                    : {globals().get('__file__', 'NO __file__')}", log_level=logging.DEBUG)
        try:
            custom_print(f"__compiled__.containing_dir : {compiled_source.containing_dir}", log_level=logging.DEBUG)
        except NameError:
            custom_print(f"__compiled__ not defined", log_level=logging.DEBUG)
        if hasattr(sys, '_MEIPASS'):
            custom_print(f"_MEIPASS                    : {sys._MEIPASS}", log_level=logging.DEBUG)
        else:
            custom_print(f"_MEIPASS not defined", log_level=logging.DEBUG)
        print("")
    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        if DEBUG_MODE: custom_print(f"Entra en modo PyInstaller -> (sys._MEIPASS)", log_level=logging.DEBUG)
    # Nuitka onefile
    elif "NUITKA_ONEFILE_PARENT" in os.environ:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if DEBUG_MODE: custom_print(f"Entra en modo Nuitka --onefile -> (__file__)", log_level=logging.DEBUG)
    # Nuitka standalone
    elif compiled_source:
    # elif "__compiled__" in globals():
        base_path = os.path.join(compiled_source.containing_dir, TOOL_NAME + '.dist')
        # base_path = compiled_source
        if DEBUG_MODE: custom_print(f"Entra en modo Nuitka --standalone -> (__compiled__.containing_dir)", log_level=logging.DEBUG)
    # Python normal
    elif "__file__" in globals():
        if RESOURCES_IN_CURRENT_FOLDER:
            base_path = os.getcwd()
            if DEBUG_MODE: custom_print(f"Entra en Python .py -> (cwd)", log_level=logging.DEBUG)
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if DEBUG_MODE: custom_print(f"Entra en Python .py -> (dirname(dirname(__file__)))", log_level=logging.DEBUG)
    else:
        base_path = os.getcwd()
        if DEBUG_MODE: custom_print(f"Entra en fallback final -> os.getcwd()", log_level=logging.DEBUG)
    if DEBUG_MODE:
        custom_print(f"return path                 : {os.path.join(base_path, relative_path)}", log_level=logging.DEBUG)
        custom_print(f"--- END DEBUG INFO", log_level=logging.DEBUG)
    return os.path.join(base_path, relative_path)


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


def is_inside_docker():
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"

#------------------------------------------------------------------
# Replace original print to use the same GV.LOGGER formatter
def custom_print(*args, log_level=logging.INFO, **kwargs):
    message = " ".join(str(a) for a in args)
    log_level_name = logging.getLevelName(log_level)
    colortag = MSG_TAGS_COLORED.get(log_level_name, MSG_TAGS_COLORED['INFO'])
    print(f"{colortag}{message}{Style.RESET_ALL}", **kwargs)
