import base64
import ctypes
import fnmatch
import hashlib
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import piexif
from tqdm import tqdm as original_tqdm

from Core import GlobalVariables as GV
from Core.CustomLogger import LoggerConsoleTqdm, set_log_level
from Core.DateFunctions import parse_text_datetime_to_epoch

# Crear instancia global del wrapper
TQDM_LOGGER_INSTANCE = LoggerConsoleTqdm(GV.LOGGER, logging.INFO)

######################
# FUNCIONES AUXILIARES
######################
# -------------------------------------------------------------
# Set Profile to analyze and optimize code:
# -------------------------------------------------------------
def profile_and_print(function_to_analyze, *args, step_name_for_profile='', live_stats=True, interval=10, top_n=10, **kwargs):
    """
    Ejecuta cProfile solo sobre function_to_analyze (dejando el sleep
    del wrapper fuera del profiling), vuelca stats a GV.LOGGER.debug si
    live_stats=True, y devuelve el resultado de la función analizada.
    """
    import io
    import cProfile
    import pstats
    from concurrent.futures import ThreadPoolExecutor, TimeoutError

    profiler = cProfile.Profile()

    # Ejecutamos la función BAJO profiler.runcall, de modo que
    # el wrapper (y sus sleep) no entren en el perfil
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            profiler.runcall,
            function_to_analyze, *args, **kwargs
        )

        if live_stats:
            # Mientras la tarea no termine, volcamos stats cada interval
            while True:
                try:
                    # Esperamos como máximo interval segundos
                    result = future.result(timeout=interval)
                    break
                except TimeoutError:
                    # Si no ha acabado, imprimimos stats parciales
                    stream = io.StringIO()
                    stats = pstats.Stats(profiler, stream=stream)
                    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
                    GV.LOGGER.debug(f"{step_name_for_profile}⏱️ Intermediate Stats (top %d):\n\n%s", top_n, stream.getvalue() )

            final_result = result
        else:
            # Si no queremos live stats, esperamos a que acabe y ya está
            final_result = future.result()

    # Informe final
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
    GV.LOGGER.debug(f"{step_name_for_profile}Final Profile Report (top %d):\n\n%s", top_n, stream.getvalue() )

    return final_result


# Redefinir `tqdm` para usar `TQDM_LOGGER_INSTANCE` si no se especifica `file`
def tqdm(*args, **kwargs):
    if GV.ARGS['AUTOMATIC-MIGRATION'] and GV.ARGS['dashboard'] == True:
        if 'file' not in kwargs:  # Si el usuario no especifica `file`, usar `TQDM_LOGGER_INSTANCE`
            kwargs['file'] = TQDM_LOGGER_INSTANCE
    return original_tqdm(*args, **kwargs)


def dir_exists(dir):
    return os.path.isdir(dir)


def run_from_synology(log_level=None):
    """ Check if the srcript is running from a Synology NAS """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        return os.path.exists('/etc.defaults/synoinfo.conf')


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def print_arguments_pretty(arguments, title="Arguments", step_name="", use_logger=True, use_custom_print=True):
    """
    Prints a list of command-line arguments in a structured and readable one-line-per-arg format.

    Args:
        :param arguments:
        :param step_name:
        :param title:
        :param use_custom_print:
        :param arguments (list): List of arguments (e.g., for PyInstaller).
        :param title (str): Optional title to display above the arguments.
        :param use_logger:
    """
    print("")
    indent = "    "
    i = 0
    if use_logger:
        GV.LOGGER.info(f"{step_name}{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                GV.LOGGER.info(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                GV.LOGGER.info(f"{step_name}{indent}{arg}")
                i += 1
    else:
        if use_custom_print:
            from CustomLogger import print_info
            print_info(f"{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    print_info(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    print_info(f"{step_name}{indent}{arg}")
                    i += 1
        else:
            pass
            print(f"{GV.TAG_INFO}{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    print(f"{GV.TAG_INFO}{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    print(f"{GV.TAG_INFO}{step_name}{indent}{arg}")
                    i += 1
    print("")


def ensure_executable(path):
    if platform.system() != "Windows":
        # Añade permisos de ejecución al usuario, grupo y otros sin quitar los existentes
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def normalize_path(path, log_level=None):
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # return os.path.normpath(path).strip(os.sep)
        return os.path.normpath(path)


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta al recurso 'relative_path', funcionando en:
    - PyInstaller (onefile o standalone)
    - Nuitka (onefile o standalone)
    - Python directo (desde cwd o desde dirname(__file__))
    """
    # IMPORTANT: Don't use GV.LOGGER in this function because is also used by build-binary.py which has not any GV.LOGGER created.
    DEBUG_MODE = False  # Cambia a False para silenciar
    if DEBUG_MODE:
        print("---DEBUG INFO")
        print(f"{GV.COLORTAG_DEBUG}GV.RESOURCES_IN_CURRENT_FOLDER : {GV.RESOURCES_IN_CURRENT_FOLDER}")
        print(f"{GV.COLORTAG_DEBUG}sys.frozen                  : {getattr(sys, 'frozen', False)}")
        print(f"{GV.COLORTAG_DEBUG}NUITKA_ONEFILE_PARENT       : {'YES' if 'NUITKA_ONEFILE_PARENT' in os.environ else 'NO'}")
        print(f"{GV.COLORTAG_DEBUG}sys.argv[0]                 : {sys.argv[0]}")
        print(f"{GV.COLORTAG_DEBUG}sys.executable              : {sys.executable}")
        print(f"{GV.COLORTAG_DEBUG}os.getcwd()                 : {os.getcwd()}")
        print(f"{GV.COLORTAG_DEBUG}__file__                    : {globals().get('__file__', 'NO __file__')}")
        try:
            print(f"{GV.COLORTAG_DEBUG}__compiled__.containing_dir : {__compiled__.containing_dir}")
        except NameError:
            print(f"{GV.COLORTAG_DEBUG}__compiled__ not defined")
        if hasattr(sys, '_MEIPASS'):
            print(f"{GV.COLORTAG_DEBUG}_MEIPASS                    : {sys._MEIPASS}")
        else:
            print(f"{GV.COLORTAG_DEBUG}_MEIPASS not defined")
        print("")
    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en modo PyInstaller -> (sys._MEIPASS)")
    # Nuitka onefile
    elif "NUITKA_ONEFILE_PARENT" in os.environ:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en modo Nuitka --onefile -> (__file__)")
    # Nuitka standalone
    elif "__compiled__" in globals():
        base_path = os.path.join(__compiled__.containing_dir, GV.SCRIPT_NAME+'.dist')
        # base_path = __compiled__
        if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en modo Nuitka --standalone -> (__compiled__.containing_dir)")
    # Python normal
    elif "__file__" in globals():
        if GV.RESOURCES_IN_CURRENT_FOLDER:
            base_path = os.getcwd()
            if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en Python .py -> (cwd)")
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en Python .py -> (dirname(dirname(__file__)))")
    else:
        base_path = os.getcwd()
        if DEBUG_MODE: print(f"{GV.COLORTAG_DEBUG}Entra en fallback final -> os.getcwd()")
    if DEBUG_MODE:
        print(f"{GV.COLORTAG_DEBUG}return path                 : {os.path.join(base_path, relative_path)}")
        print("--- END DEBUG INFO")
    return os.path.join(base_path, relative_path)


def get_os(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized operating system name (linux, macos, windows)"""
    if use_logger:
        with set_log_level(GV.LOGGER, log_level):
            current_os = platform.system()
            if current_os in ["Linux", "linux"]:
                os_label = "linux"
            elif current_os in ["Darwin", "macOS", "macos"]:
                os_label = "macos"
            elif current_os in ["Windows", "windows", "Win"]:
                os_label = "windows"
            else:
                GV.LOGGER.error(f"{step_name}Unsupported Operating System: {current_os}")
                os_label = "unknown"
            GV.LOGGER.info(f"{step_name}Detected OS: {os_label}")
    else:
        current_os = platform.system()
        if current_os in ["Linux", "linux"]:
            os_label = "linux"
        elif current_os in ["Darwin", "macOS", "macos"]:
            os_label = "macos"
        elif current_os in ["Windows", "windows", "Win"]:
            os_label = "windows"
        else:
            print(f"{GV.TAG_ERROR}{step_name}Unsupported Operating System: {current_os}")
            os_label = "unknown"
        print(f"{GV.TAG_INFO}{step_name}Detected OS: {os_label}")
    return os_label


def get_arch(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized system architecture (e.g., x64, arm64)"""
    if use_logger:
        with set_log_level(GV.LOGGER, log_level):
            current_arch = platform.machine()
            if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
                arch_label = "x64"
            elif current_arch in ["aarch64", "arm64", 'ARM64']:
                arch_label = "arm64"
            else:
                GV.LOGGER.error(f"{step_name}Unsupported Architecture: {current_arch}")
                arch_label = "unknown"
            GV.LOGGER.info(f"{step_name}Detected architecture: {arch_label}")
    else:
        current_arch = platform.machine()
        if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
            arch_label = "x64"
        elif current_arch in ["aarch64", "arm64", "ARM64"]:
            arch_label = "arm64"
        else:
            print(f"{GV.TAG_ERROR}{step_name}Unsupported Architecture: {current_arch}")
            arch_label = "unknown"
        print(f"{GV.TAG_INFO}{step_name}Detected architecture: {arch_label}")
    return arch_label


def check_OS_and_Terminal(log_level=None):
    """ Check OS, Terminal Type, and System Architecture """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Detect the operating system
        current_os = get_os(log_level=logging.WARNING)
        # Detect the machine architecture
        arch_label = get_arch(log_level=logging.WARNING)
        # Logging OS
        if current_os == "linux":
            if run_from_synology():
                GV.LOGGER.info(f"Script running on Linux System in a Synology NAS")
            else:
                GV.LOGGER.info(f"Script running on Linux System")
        elif current_os == "macos":
            GV.LOGGER.info(f"Script running on MacOS System")
        elif current_os == "windows":
            GV.LOGGER.info(f"Script running on Windows System")
        else:
            GV.LOGGER.error(f"Unsupported Operating System: {current_os}")
        # Logging Architecture
        GV.LOGGER.info(f"Detected architecture: {arch_label}")
        # Terminal type detection
        if sys.stdout.isatty():
            GV.LOGGER.info(f"Interactive (TTY) terminal detected for stdout")
        else:
            GV.LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdout")
        if sys.stdin.isatty():
            GV.LOGGER.info(f"Interactive (TTY) terminal detected for stdin")
        else:
            GV.LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdin")
        GV.LOGGER.info(f"")


def remove_empty_dirs(input_folder, log_level=None):
    """
    Remove empty directories recursively.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        for path, dirs, files in os.walk(input_folder, topdown=False):
            filtered_dirnames = [d for d in dirs if d != '@eaDir']
            if not filtered_dirnames and not files:
                try:
                    os.rmdir(path)
                    GV.LOGGER.info(f"Removed empty directory {path}")
                except OSError:
                    pass

def remove_folder(folder, log_level=None):
    """
    Removes the specified `folder` and all of its contents, logging events
    at the specified `log_level`.

    Parameters:
    - folder (str or Path): Path to the folder to remove.
    - log_level (str): Logging level to use ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').

    Returns:
    - True if the folder was removed successfully.
    - False if an error occurred.
    """
    with set_log_level(GV.LOGGER, log_level):  # Temporarily adjust GV.LOGGER’s level for this operation
        folder_path = Path(folder)
        try:
            GV.LOGGER.debug(f"Attempting to remove: {folder_path}")
            shutil.rmtree(folder_path)
            GV.LOGGER.info(f"Folder '{folder_path}' removed successfully.")
            return True

        except FileNotFoundError:
            GV.LOGGER.warning(f"Folder not found: '{folder_path}'.")
            return False

        except PermissionError:
            GV.LOGGER.error(f"Insufficient permissions to remove: '{folder_path}'.")
            return False

        except Exception as e:
            GV.LOGGER.critical(f"Unexpected error while removing '{folder_path}': {e}")
            return False


def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False, log_level=None):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
        :param input_folder:
        :param exclude_subfolders:
        :param max_depth:
        :param flatten_root_folder:
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Count number of sep of input_folder
        sep_input = input_folder.count(os.sep)
        # Convert wildcard patterns to regex patterns for matching
        exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
        for path, dirs, files in Utils.tqdm(os.walk(input_folder, topdown=True), ncols=120, smoothing=0.1, desc=f"{GV.TAG_INFO}Flattening Subfolders in '{input_folder}'", unit=" subfolders"):
            # Count number of sep of root folder
            sep_root = int(path.count(os.sep))
            depth = sep_root - sep_input
            GV.LOGGER.verbose(f"Depth: {depth}")
            if depth > max_depth:
                # Skip deeper levels
                continue
            # If flatten_root_folder=True, then only need to flatten the root folder, and it recursively will flatten all subfolders
            if flatten_root_folder:
                dirs = [os.path.basename(path)]
                path = os.path.dirname(path)
            # Process files in subfolders and move them to the root of the subfolder
            for folder in dirs:
                # If 'Albums' folder is found, invoke the Tool recursively on its subdirectories
                if os.path.basename(folder) == "Albums":
                    for album_subfolder in dirs:
                        subfolder_path = os.path.join(path, album_subfolder)
                        flatten_subfolders(input_folder=subfolder_path, exclude_subfolders=exclude_subfolders, max_depth=max_depth+1)
                    continue
                # Skip processing if the current directory matches any exclude pattern
                if any(pattern.match(os.path.basename(folder)) for pattern in exclude_patterns):
                    # GV.LOGGER.warning(f"Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                    continue
                subfolder_path = os.path.join(path, folder)
                # GV.LOGGER.info(f"Flattening folder: '{dir_name}'")
                for sub_root, _, sub_files in os.walk(subfolder_path):
                    for file_name in sub_files:
                        file_path = os.path.join(sub_root, file_name)
                        new_location = os.path.join(subfolder_path, file_name)
                        # Avoid overwriting files by appending a numeric suffix if needed
                        if os.path.exists(new_location):
                            base, ext = os.path.splitext(file_name)
                            counter = 1
                            while os.path.exists(new_location):
                                new_location = os.path.join(subfolder_path, f"{base}_{counter}{ext}")
                                counter += 1
                        shutil.move(file_path, new_location)
        for path, dirs, files in os.walk(input_folder, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(path, dir)
                if not os.listdir(dir_path):  # Si la carpeta está vacía
                    os.rmdir(dir_path)


def unzip_to_temp(zipfile_path):
    """
    Unzips the contents of `zip_path` into a temporary directory.
    The directory is created using tempfile and is valid on all platforms.

    Returns:
        str: Path to the temporary extraction directory.
    """
    if not zipfile.is_zipfile(zipfile_path):
        raise ValueError(f"{zipfile_path} is not a valid zip file.")

    temp_dir = tempfile.mkdtemp()  # Creates a unique temp dir, persists until deleted manually
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        print(f"ZIP file extracted to: {temp_dir}")

    return temp_dir


def unzip(zipfile_path, dest_folder):
    """
    Unzips a ZIP file into the specified destination folder.

    Args:
        zipfile_path (str): Path to the ZIP file.
        dest_folder (str): Destination folder where the contents will be extracted.
    """
    # Check if the ZIP file exists
    if not os.path.exists(zipfile_path):
        raise FileNotFoundError(f"The ZIP file does not exist: {zipfile_path}")
    # Check if the file is a valid ZIP file
    if not zipfile.is_zipfile(zipfile_path):
        raise zipfile.BadZipFile(f"The file is not a valid ZIP archive: {zipfile_path}")
    # Create the destination folder if it doesn't exist
    os.makedirs(dest_folder, exist_ok=True)
    # Extract all contents of the ZIP file into the destination folder
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        zip_ref.extractall(dest_folder)
        print(f"ZIP file extracted to: {dest_folder}")


def unzip_flatten(zipfile_path, dest_folder):
    """
    Unzips a ZIP file into the specified destination folder,
    stripping the top-level directory if all files are inside it.

    Args:
        zipfile_path (str): Path to the ZIP file.
        dest_folder (str): Destination folder where the contents will be extracted.
    """
    if not os.path.exists(zipfile_path):
        raise FileNotFoundError(f"The ZIP file does not exist: {zipfile_path}")
    if not zipfile.is_zipfile(zipfile_path):
        raise zipfile.BadZipFile(f"The file is not a valid ZIP archive: {zipfile_path}")
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        # Get the list of all file paths in the ZIP
        members = zip_ref.namelist()
        # Check if all files are under a common top-level folder
        top_level_dirs = set(p.split('/')[0] for p in members if '/' in p)
        if len(top_level_dirs) == 1:
            prefix_to_strip = next(iter(top_level_dirs)) + '/'
        else:
            prefix_to_strip = None
        for member in members:
            target_path = member
            if prefix_to_strip and member.startswith(prefix_to_strip):
                target_path = member[len(prefix_to_strip):]
            if target_path:
                final_path = os.path.join(dest_folder, target_path)
                if member.endswith('/'):
                    os.makedirs(final_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    with zip_ref.open(member) as source, open(final_path, 'wb') as target:
                        target.write(source.read())
        print(f"ZIP file extracted to: {dest_folder}")


def zip_folder(temp_dir, output_file):
    print(f"Creating packed file: {output_file}...")

    # Convertir output_file a un objeto Path
    output_path = Path(output_file)

    # Crear los directorios padres si no existen
    if not output_path.parent.exists():
        print(f"Creating needed folder for: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                # Añade al zip respetando la estructura de carpetas
                zipf.write(file_path, file_path.relative_to(temp_dir))
            for dir in dirs:
                dir_path = Path(root) / dir
                # Añade directorios vacíos al zip
                if not os.listdir(dir_path):
                    zipf.write(dir_path, dir_path.relative_to(temp_dir))
    print(f"File successfully packed: {output_file}")


def confirm_continue(log_level=None):
    # If argument 'no-request-user-confirmarion' is true then don't ask and wait for user confirmation
    if GV.ARGS['no-request-user-confirmarion']:
        return True

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        while True:
            response = input("Do you want to continue? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                GV.LOGGER.info(f"Continuing...")
                return True
            elif response in ['no', 'n']:
                GV.LOGGER.info(f"Operation canceled.")
                return False
            else:
                GV.LOGGER.warning(f"Invalid input. Please enter 'yes' or 'no'.")


def remove_quotes(input_string: str, log_level=logging.INFO) -> str:
    """
    Elimina todas las comillas simples y dobles al inicio o fin de la cadena.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        return input_string.strip('\'"')


def remove_server_name(path, log_level=None):
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Expresión regular para rutas Linux (///servidor/)
        path = re.sub(r'///[^/]+/', '///', path)
        # Expresión regular para rutas Windows (\\servidor\)
        path = re.sub(r'\\\\[^\\]+\\', '\\\\', path)
        return path


def fix_paths(path, log_level=None):
    fixed_path = path.replace('/', os.path.sep).replace('\\', os.path.sep)
    return fixed_path


def is_valid_path(path, log_level=None):
    """
    Verifica si la ruta es válida en la plataforma actual.
    — Debe ser una ruta absoluta.
    — No debe contener caracteres inválidos para el sistema operativo.
    — No debe usar un formato incorrecto para la plataforma.
    """
    from pathvalidate import validate_filepath, ValidationError
    
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Verifica si `ruta` es válida como path en la plataforma actual.
            validate_filepath(path, platform="auto")
            return True
        except ValidationError as e:
            GV.LOGGER.error(f"Path validation ERROR: {e}")
            return False
        

def get_unique_items(list1, list2, key='filename', log_level=None):
    """
    Returns items that are in list1 but not in list2 based on a specified key.

    Args:
        list1 (list): First list of dictionaries.
        list2 (list): Second list of dictionaries.
        key (str): Key to compare between both lists.

    Returns:
        list: Items present in list1 but not in list2.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        set2 = {item[key] for item in list2}  # Create a set of filenames from list2
        unique_items = [item for item in list1 if item[key] not in set2]
        return unique_items


def update_metadata(file_path, date_time, log_level=None):
    """
    Updates the metadata of a file (image, video, etc.) to set the creation date.

    Args:
        file_path (str): Path to the file.
        date_time (str): Date and time in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext in GV.PHOTO_EXT:
                update_exif_date(file_path, date_time, log_level=log_level)
            elif file_ext in GV.VIDEO_EXT:
                update_video_metadata(file_path, date_time, log_level=log_level)
            GV.LOGGER.debug(f"Metadata updated for {file_path} with timestamp {date_time}")
        except Exception as e:
            GV.LOGGER.error(f"Failed to update metadata for {file_path}. {e}")
        

def update_exif_date(image_path, asset_time, log_level=None):
    """
    Updates the EXIF metadata of an image to set the DateTimeOriginal and related fields.

    Args:
        image_path (str): Path to the image file.
        asset_time (int or str): Timestamp in UNIX Epoch format or a date string in "YYYY-MM-DD HH:MM:SS".
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Si asset_time es una cadena en formato 'YYYY-MM-DD HH:MM:SS', conviértelo a timestamp UNIX
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError as e:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}. {e}")
                    return
            # Convertir el timestamp UNIX a formato EXIF "YYYY:MM:DD HH:MM:SS"
            date_time_exif = datetime.fromtimestamp(asset_time).strftime("%Y:%m:%d %H:%M:%S")
            date_time_bytes = date_time_exif.encode('utf-8')
            # Backup original timestamps
            original_times = os.stat(image_path)
            original_atime = original_times.st_atime
            original_mtime = original_times.st_mtime
            # Cargar EXIF data o crear un diccionario vacío si no tiene metadatos
            try:
                exif_dict = piexif.load(image_path)
            except Exception:
                # GV.LOGGER.warning(f"No EXIF metadata found in {image_path}. Creating new EXIF data.")
                # exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
                GV.LOGGER.warning(f"No EXIF metadata found in {image_path}. Skipping it....")
                return
            # Actualizar solo si existen las secciones
            if "0th" in exif_dict:
                exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_bytes
            if "Exif" in exif_dict:
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_bytes
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_bytes
            # Verificar y corregir valores incorrectos antes de insertar
            for ifd_name in ["0th", "Exif"]:
                for tag, value in exif_dict.get(ifd_name, {}).items():
                    if isinstance(value, int):
                        exif_dict[ifd_name][tag] = str(value).encode('utf-8')
            try:
                # Dump and insert updated EXIF data
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                # Restaurar timestamps originales del archivo
                os.utime(image_path, (original_atime, original_mtime))
                GV.LOGGER.debug(f"EXIF metadata updated for {image_path} with timestamp {date_time_exif}")
            except Exception:
                GV.LOGGER.error(f"Error when restoring original metadata to file: '{image_path}'")
                return
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update EXIF metadata for {image_path}. {e}")
        

def update_video_metadata(video_path, asset_time, log_level=None):
    """
    Updates the file system timestamps of a video file to set the creation and modification dates.

    This does NOT modify embedded metadata within the file, only the timestamps visible to the OS.

    Args:
        video_path (str): Path to the video file.
        asset_time (int | str): Timestamp in UNIX Epoch format or a string in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Convert asset_time to UNIX timestamp if it's in string format
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
                    return
            # Convert timestamp to system format
            mod_time = asset_time
            create_time = asset_time
            # Update last modified and last accessed time (works on all OS)
            os.utime(video_path, (mod_time, mod_time))
            # Update file creation time (Windows only)
            if platform.system() == "Windows":
                try:
                    # Convert timestamp to Windows FILETIME format (100-nanosecond intervals since 1601-01-01)
                    windows_time = int((create_time + 11644473600) * 10000000)
                    # Open the file handle
                    handle = ctypes.windll.kernel32.CreateFileW(video_path, 256, 0, None, 3, 128, None)
                    if handle != -1:
                        ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ctypes.c_int64(windows_time)), None, None)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        GV.LOGGER.debug(f"DEBUG     : File creation time updated for {video_path}")
                except Exception as e:
                    GV.LOGGER.warning(f"Failed to update file creation time on Windows. {e}")
            GV.LOGGER.debug(f"File system timestamps updated for {video_path} with timestamp {datetime.fromtimestamp(mod_time)}")
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")


def update_video_metadata_with_ffmpeg(video_path, asset_time, log_level=None):
    """
    Updates the metadata of a video file to set the creation date without modifying file timestamps.

    Args:
        video_path (str): Path to the video file.
        asset_time (int): Timestamp in UNIX Epoch format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Si asset_time es una cadena en formato 'YYYY-MM-DD HH:MM:SS', conviértelo a timestamp UNIX
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
                    return
            # Convert asset_time (UNIX timestamp) to format used by FFmpeg (YYYY-MM-DDTHH:MM:SS)
            formatted_date = datetime.fromtimestamp(asset_time).strftime("%Y-%m-%dT%H:%M:%S")
            # Backup original file timestamps
            original_times = os.stat(video_path)
            original_atime = original_times.st_atime
            original_mtime = original_times.st_mtime
            temp_file = video_path + "_temp.mp4"
            command = [
                "ffmpeg", "-i", video_path,
                "-metadata", f"creation_time={formatted_date}",
                "-metadata", f"modify_time={formatted_date}",
                "-metadata", f"date_time_original={formatted_date}",
                "-codec", "copy", temp_file
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            os.replace(temp_file, video_path)  # Replace original file with updated one
            # Restore original file timestamps
            os.utime(video_path, (original_atime, original_mtime))
            GV.LOGGER.debug(f"Video metadata updated for {video_path} with timestamp {formatted_date}")
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")
        

# Convert to list
def convert_to_list(input_string, log_level=None):
    """ Convert a String to List"""
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            output = input_string
            if isinstance(output, list):
                pass  # output ya es una lista
            elif isinstance(output, str):
                if ',' in output:
                    output = [item.strip() for item in output.split(',') if item.strip()]
                else:
                    output = [output.strip()] if output.strip() else []
            elif isinstance(output, (int, float)):
                output = [output]
            elif output is None:
                output = []
            else:
                output = [output]
        except Exception as e:
            GV.LOGGER.warning(f"Failed to convert string to List for {input_string}. {e}")
        
        return output


def convert_asset_ids_to_str(asset_ids):
    """Convierte asset_ids a strings, incluso si es una lista de diferentes tipos."""
    if isinstance(asset_ids, list):
        return [str(item) for item in asset_ids]
    else:
        return [str(asset_ids)]


def sha1_checksum(file_path):
    """Calcula el SHA-1 hash de un archivo y devuelve tanto en formato HEX como Base64"""
    sha1 = hashlib.sha1()  # Crear un objeto SHA-1

    with open(file_path, "rb") as f:  # Leer el archivo en modo binario
        while chunk := f.read(8192):  # Leer en bloques de 8 KB para eficiencia
            sha1.update(chunk)

    sha1_hex = sha1.hexdigest()  # Obtener en formato HEX
    sha1_base64 = base64.b64encode(sha1.digest()).decode("utf-8")  # Convertir a Base64

    return sha1_hex, sha1_base64


def match_pattern(string, pattern):
    """
    Returns True if the regex pattern is found in the given string.
    """
    return re.search(pattern, string) is not None


def replace_pattern(string, pattern, pattern_to_replace):
    """
    Replaces all occurrences of the regex pattern in the string with replace_pattern.
    """
    return re.sub(pattern, pattern_to_replace, string)


def has_any_filter():
    return GV.ARGS.get('filter-by-type', None) or GV.ARGS.get('filter-from-date', None) or GV.ARGS.get('filter-to-date', None) or GV.ARGS.get('filter-by-country', None) or GV.ARGS.get('filter-by-city', None) or GV.ARGS.get('filter-by-person', None)


def get_filters():
    filters = {}
    keys = [
        'filter-by-type',
        'filter-from-date',
        'filter-to-date',
        'filter-by-country',
        'filter-by-city',
        'filter-by-person',
    ]
    for key in keys:
        filters[key] = GV.ARGS.get(key)
    return filters


def is_date_outside_range(date_to_check):
    from_date = parse_text_datetime_to_epoch(GV.ARGS.get('filter-from-date'))
    to_date = parse_text_datetime_to_epoch(GV.ARGS.get('filter-to-date'))
    date_to_check = parse_text_datetime_to_epoch(date_to_check)
    if from_date is not None and date_to_check < from_date:
        return True
    if to_date is not None and date_to_check > to_date:
        return True
    return False


def capitalize_first_letter(text):
    if not text:
        return text
    return text[0].upper() + text[1:]


def get_subfolders_with_exclusions(input_folder, exclude_subfolder=None):
    all_entries = os.listdir(input_folder)
    subfolders = [
        entry for entry in all_entries
        if os.path.isdir(os.path.join(input_folder, entry)) and
           (exclude_subfolder is None or entry not in exclude_subfolder)
    ]
    return subfolders


def contains_zip_files(input_folder, log_level=None):
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"Searching .zip files in input folder...")
        for file in os.listdir(input_folder):
            if file.endswith('.zip'):
                return True
        GV.LOGGER.info(f"No .zip files found in input folder.")
        return False


def print_dict_pretty(result):
    for key, value in result.items():
        GV.LOGGER.info(f"{key:35}: {value}")