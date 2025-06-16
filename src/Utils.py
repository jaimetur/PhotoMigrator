import os, sys
import shutil
import zipfile
import tempfile
import fnmatch
import re
import stat
from datetime import datetime
import ctypes
import platform
import piexif
import subprocess
import logging
from CustomLogger import set_log_level
from PIL import Image, ExifTags
import hashlib
import base64
import inspect
from pathlib import Path
from typing import Union
import glob
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from dateutil import parser as date_parser
from tqdm import tqdm as original_tqdm
from CustomLogger import LoggerConsoleTqdm
from GlobalVariables import LOGGER, ARGS, TIMESTAMP, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, RESOURCES_IN_CURRENT_FOLDER, SCRIPT_NAME, SUPPLEMENTAL_METADATA, SPECIAL_SUFFIXES, EDITTED_SUFFIXES

# Crear instancia global del wrapper
TQDM_LOGGER_INSTANCE = LoggerConsoleTqdm(LOGGER, logging.INFO)

######################
# FUNCIONES AUXILIARES
######################

# Redefinir `tqdm` para usar `TQDM_LOGGER_INSTANCE` si no se especifica `file`
def tqdm(*args, **kwargs):
    if ARGS['AUTOMATIC-MIGRATION'] and ARGS['dashboard'] == True:
        if 'file' not in kwargs:  # Si el usuario no especifica `file`, usar `TQDM_LOGGER_INSTANCE`
            kwargs['file'] = TQDM_LOGGER_INSTANCE
    return original_tqdm(*args, **kwargs)


def dir_exists(dir):
    return os.path.isdir(dir)


def run_from_synology(log_level=logging.INFO):
    """ Check if the srcript is running from a Synology NAS """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        return os.path.exists('/etc.defaults/synoinfo.conf')


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def print_arguments_pretty(arguments, title="Arguments", step_name="", use_logger=True):
    """
    Prints a list of command-line arguments in a structured and readable one-line-per-arg format.

    Args:
        :param arguments (list): List of arguments (e.g., for PyInstaller).
        :param title (str): Optional title to display above the arguments.
        :param use_logger:
    """
    print("")
    indent = "    "
    i = 0
    if use_logger:
        LOGGER.info(f"INFO    : {step_name}{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                LOGGER.info(f"INFO    : {step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                LOGGER.info(f"INFO    : {step_name}{indent}{arg}")
                i += 1
    else:
        print(f"INFO    : {title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                print(f"INFO    : {step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                print(f"INFO    : {step_name}{indent}{arg}")
                i += 1
    print("")


def ensure_executable(path):
    if platform.system() != "Windows":
        # Añade permisos de ejecución al usuario, grupo y otros sin quitar los existentes
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def normalize_path(path, log_level=logging.INFO):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # return os.path.normpath(path).strip(os.sep)
        return os.path.normpath(path)


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta al recurso 'relative_path', funcionando en:
    - PyInstaller (onefile o standalone)
    - Nuitka (onefile o standalone)
    - Python directo (desde cwd o desde dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because is also used by build.py which has not any LOGGER created.
    DEBUG_MODE = False  # Cambia a False para silenciar
    if DEBUG_MODE:
        print("---DEBUG INFO")
        print(f"DEBUG   : RESOURCES_IN_CURRENT_FOLDER : {RESOURCES_IN_CURRENT_FOLDER}")
        print(f"DEBUG   : sys.frozen                  : {getattr(sys, 'frozen', False)}")
        print(f"DEBUG   : NUITKA_ONEFILE_PARENT       : {'YES' if 'NUITKA_ONEFILE_PARENT' in os.environ else 'NO'}")
        print(f"DEBUG   : sys.argv[0]                 : {sys.argv[0]}")
        print(f"DEBUG   : sys.executable              : {sys.executable}")
        print(f"DEBUG   : os.getcwd()                 : {os.getcwd()}")
        print(f"DEBUG   : __file__                    : {globals().get('__file__', 'NO __file__')}")
        try:
            print(f"DEBUG   : __compiled__.containing_dir : {__compiled__.containing_dir}")
        except NameError:
            print(f"DEBUG   : __compiled__ not defined")
        if hasattr(sys, '_MEIPASS'):
            print(f"DEBUG   : _MEIPASS                    : {sys._MEIPASS}")
        else:
            print(f"DEBUG   : _MEIPASS not defined")
        print("")
    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        if DEBUG_MODE: print("DEBUG   : Entra en modo PyInstaller -> (sys._MEIPASS)")
    # Nuitka onefile
    elif "NUITKA_ONEFILE_PARENT" in os.environ:
        base_path = os.path.dirname(os.path.abspath(__file__))
        if DEBUG_MODE: print("DEBUG   : Entra en modo Nuitka --onefile -> (__file__)")
    # Nuitka standalone
    elif "__compiled__" in globals():
        base_path = os.path.join(__compiled__.containing_dir, SCRIPT_NAME+'.dist')
        # base_path = __compiled__
        if DEBUG_MODE: print("DEBUG   : Entra en modo Nuitka --standalone -> (__compiled__.containing_dir)")
    # Python normal
    elif "__file__" in globals():
        if RESOURCES_IN_CURRENT_FOLDER:
            base_path = os.getcwd()
            if DEBUG_MODE: print("DEBUG   : Entra en Python .py -> (cwd)")
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if DEBUG_MODE: print("DEBUG   : Entra en Python .py -> (dirname(dirname(__file__)))")
    else:
        base_path = os.getcwd()
        if DEBUG_MODE: print("DEBUG   : Entra en fallback final -> os.getcwd()")
    if DEBUG_MODE:
        print(f"DEBUG   : return path                 : {os.path.join(base_path, relative_path)}")
        print("--- END DEBUG INFO")
    return os.path.join(base_path, relative_path)


def get_os(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized operating system name (linux, macos, windows)"""
    if use_logger:
        with set_log_level(LOGGER, log_level):
            current_os = platform.system()
            if current_os in ["Linux", "linux"]:
                os_label = "linux"
            elif current_os in ["Darwin", "macOS", "macos"]:
                os_label = "macos"
            elif current_os in ["Windows", "windows", "Win"]:
                os_label = "windows"
            else:
                LOGGER.error(f"ERROR   : {step_name}Unsupported Operating System: {current_os}")
                os_label = "unknown"
            LOGGER.info(f"INFO    : {step_name}Detected OS: {os_label}")
    else:
        current_os = platform.system()
        if current_os in ["Linux", "linux"]:
            os_label = "linux"
        elif current_os in ["Darwin", "macOS", "macos"]:
            os_label = "macos"
        elif current_os in ["Windows", "windows", "Win"]:
            os_label = "windows"
        else:
            print(f"ERROR   : {step_name}Unsupported Operating System: {current_os}")
            os_label = "unknown"
        print(f"INFO    : {step_name}Detected OS: {os_label}")
    return os_label


def get_arch(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized system architecture (e.g., x64, arm64)"""
    if use_logger:
        with set_log_level(LOGGER, log_level):
            current_arch = platform.machine()
            if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
                arch_label = "x64"
            elif current_arch in ["aarch64", "arm64", 'ARM64']:
                arch_label = "arm64"
            else:
                LOGGER.error(f"ERROR   : {step_name}Unsupported Architecture: {current_arch}")
                arch_label = "unknown"
            LOGGER.info(f"INFO    : {step_name}Detected architecture: {arch_label}")
    else:
        current_arch = platform.machine()
        if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
            arch_label = "x64"
        elif current_arch in ["aarch64", "arm64", "ARM64"]:
            arch_label = "arm64"
        else:
            print(f"ERROR   : {step_name}Unsupported Architecture: {current_arch}")
            arch_label = "unknown"
        print(f"INFO    : {step_name}Detected architecture: {arch_label}")
    return arch_label


def check_OS_and_Terminal(log_level=logging.INFO):
    """ Check OS, Terminal Type, and System Architecture """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Detect the operating system
        current_os = get_os(log_level=logging.WARNING)
        # Detect the machine architecture
        arch_label = get_arch(log_level=logging.WARNING)
        # Logging OS
        if current_os == "linux":
            if run_from_synology():
                LOGGER.info(f"INFO    : Script running on Linux System in a Synology NAS")
            else:
                LOGGER.info(f"INFO    : Script running on Linux System")
        elif current_os == "macos":
            LOGGER.info(f"INFO    : Script running on MacOS System")
        elif current_os == "windows":
            LOGGER.info(f"INFO    : Script running on Windows System")
        else:
            LOGGER.error(f"ERROR   : Unsupported Operating System: {current_os}")
        # Logging Architecture
        LOGGER.info(f"INFO    : Detected architecture: {arch_label}")
        # Terminal type detection
        if sys.stdout.isatty():
            LOGGER.info("INFO    : Interactive (TTY) terminal detected for stdout")
        else:
            LOGGER.info("INFO    : Non-Interactive (Non-TTY) terminal detected for stdout")
        if sys.stdin.isatty():
            LOGGER.info("INFO    : Interactive (TTY) terminal detected for stdin")
        else:
            LOGGER.info("INFO    : Non-Interactive (Non-TTY) terminal detected for stdin")
        LOGGER.info("")


def count_files_per_type_and_date(input_folder, log_level=logging.INFO):
    """
    Analyze all files in `input_folder`, counting:
      - total files
      - supported vs unsupported files based on global extension lists
      - image files vs video files vs metadata files vs sidecar files
      - media files (images + videos)
      - non-media files (metadata + sidecar)
      - for photos and videos, how many have an assigned date vs. not
      - percentage of photos/videos with and without date
    Uses global PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, and TIMESTAMP.
    """
    with set_log_level(LOGGER, log_level):
        timestamp_dt = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")

        # Initialize overall counters with pct keys for media
        counters = {
            'total_files': 0,
            'unsupported_files': 0,
            'supported_files': 0,
            'media_files': 0,
            'photo_files': 0,
            'video_files': 0,
            'non_media_files': 0,
            'metadata_files': 0,
            'sidecar_files': 0,
            # Nested counters for date assignment and percentages
            'photos':    {'total': 0, 'with_date': 0, 'without_date': 0, 'pct_with_date': 100, 'pct_without_date': 100},
            'videos':    {'total': 0, 'with_date': 0, 'without_date': 0, 'pct_with_date': 100, 'pct_without_date': 100},
        }

        supported_exts = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)

        # Walk through all subdirectories and files
        for root, dirs, files in os.walk(input_folder):
            for filename in files:
                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                # Count every file
                counters['total_files'] += 1

                # Determine support status
                if ext in supported_exts:
                    counters['supported_files'] += 1
                else:
                    counters['unsupported_files'] += 1

                # Categorize by extension
                if ext in PHOTO_EXT:
                    counters['photo_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'photos'
                elif ext in VIDEO_EXT:
                    counters['video_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'videos'
                else:
                    media_type = None

                # Count metadata and sidecar
                if ext in METADATA_EXT:
                    counters['metadata_files'] += 1
                if ext in SIDECAR_EXT:
                    counters['sidecar_files'] += 1
                if ext in METADATA_EXT or ext in SIDECAR_EXT:
                    counters['non_media_files'] += 1

                # Skip date logic for non-media
                if not media_type:
                    continue

                counters[media_type]['total'] += 1
                has_date = False

                # EXIF date for photos
                if media_type == 'photos':
                    try:
                        img = Image.open(os.path.join(root, filename))
                        exif = img._getexif() or {}
                        tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
                        for tag in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                            if tag in tag_map:
                                dt = tag_map[tag]
                                try:
                                    file_date = datetime.strptime(dt, "%Y:%m:%d %H:%M:%S")
                                    has_date = True
                                    break
                                except ValueError:
                                    pass
                    except Exception:
                        pass

                # Fallback to file mtime
                if not has_date:
                    try:
                        mtime = os.path.getmtime(os.path.join(root, filename))
                        file_date = datetime.fromtimestamp(mtime)
                        if file_date <= timestamp_dt:
                            has_date = True
                    except Exception:
                        has_date = False

                if has_date:
                    counters[media_type]['with_date'] += 1
                else:
                    counters[media_type]['without_date'] += 1

        # Calculate percentages for photos based on totals
        total_photos = counters['photos']['total']
        if total_photos > 0:
            counters['photos']['pct_with_date'] = (counters['photos']['with_date'] / total_photos) * 100
            counters['photos']['pct_without_date'] = (counters['photos']['without_date'] / total_photos) * 100

        # Calculate percentages for videos based on totals
        total_videos = counters['videos']['total']
        if total_videos > 0:
            counters['videos']['pct_with_date'] = (counters['videos']['with_date'] / total_videos) * 100
            counters['videos']['pct_without_date'] = (counters['videos']['without_date'] / total_videos) * 100

        return counters







def count_files_in_folder(folder_path, log_level=logging.INFO):
    """ Counts the number of files in a folder """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        total_files = 0
        for path, dirs, files in os.walk(folder_path):
            total_files += len(files)
        return total_files


def count_images_in_folder(folder_path, log_level=logging.INFO):
    """
    Counts the number of image files in a folder, considering
    as images only those files with extensions defined in
    the global variable IMAGE_EXT (in lowercase).
    """
    from GlobalVariables import PHOTO_EXT
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        total_images = 0
        for path, dirs, files in os.walk(folder_path):
            for file_name in files:
                # Extract the file extension in lowercase
                _, extension = os.path.splitext(file_name)
                if extension.lower() in PHOTO_EXT:
                    total_images += 1
        return total_images


def count_videos_in_folder(folder_path, log_level=logging.INFO):
    """
    Counts the number of video files in a folder, considering
    as videos only those files with extensions defined in
    the global variable VIDEO_EXT (in lowercase).
    """
    from GlobalVariables import VIDEO_EXT
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        total_videos = 0
        for path, dirs, files in os.walk(folder_path):
            for file_name in files:
                # Extract the file extension in lowercase
                _, extension = os.path.splitext(file_name)
                if extension.lower() in VIDEO_EXT:
                    total_videos += 1
        return total_videos


def count_videos_in_folder(folder_path, log_level=logging.INFO):
    """
    Counts the number of video files in a folder, considering
    as videos only those files with extensions defined in
    the global variable VIDEO_EXT (in lowercase).
    """
    from GlobalVariables import VIDEO_EXT
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        total_videos = 0
        for path, dirs, files in os.walk(folder_path):
            for file_name in files:
                # Extract the file extension in lowercase
                _, extension = os.path.splitext(file_name)
                if extension.lower() in VIDEO_EXT:
                    total_videos += 1
        return total_videos


def count_sidecars_in_folder(folder_path, log_level=logging.INFO):
    """
    Counts the number of sidecar files in a folder. A file is considered a sidecar if:
    1. Its extension is listed in the global variable SIDECAR_EXT (in lowercase).
    2. It shares the same base name as an image file in the same directory.
    3. The sidecar file name may include the image extension before the sidecar extension.
    """
    from GlobalVariables import PHOTO_EXT, SIDECAR_EXT
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        total_sidecars = 0
        for path, dirs, files in os.walk(folder_path):
            # Extract base names of image files without extensions
            image_base_names = set()
            for file_name in files:
                base_name, ext = os.path.splitext(file_name)
                if ext.lower() in PHOTO_EXT:
                    image_base_names.add(base_name)
            # Count valid sidecar files
            for file_name in files:
                base_name, ext = os.path.splitext(file_name)
                if ext.lower() in SIDECAR_EXT:
                    # Check if there's a matching image file (direct match or with image extension included)
                    if any(base_name.startswith(image_name) for image_name in image_base_names):
                        total_sidecars += 1
        return total_sidecars


def count_metadatas_in_folder(folder_path, log_level=logging.INFO):
    """
    Counts the number of metadata files in a folder. A file is considered a metadata if:
    1. Its extension is listed in the global variable METADATA_EXT (in lowercase).
    2. It shares the same base name as an image file in the same directory.
    3. The sidecar file name may include the image extension before the sidecar extension.
    """
    from GlobalVariables import METADATA_EXT
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        total_metadatas = 0
        for path, dirs, files in os.walk(folder_path):
            for file_name in files:
                # Extract the file extension in lowercase
                _, extension = os.path.splitext(file_name)
                if extension.lower() in METADATA_EXT:
                    total_metadatas += 1
        return total_metadatas


def change_file_extension(input_folder, current_extension, new_extension, log_level=logging.INFO):
    """
    Changes the extension of all files with a specific extension
    within a folder and its subfolders.

    Args:
        input_folder (str): Path to the root folder to search for files.
        current_extension (str): Current file extension (includes the dot, e.g., ".txt").
        new_extension (str): New file extension (includes the dot, e.g., ".md").

    Returns:
        None
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Contar el total de carpetas
        total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"INFO    : Changing File Extensions in '{input_folder}'", unit=" files") as pbar:
            for path, dirs, files in os.walk(input_folder):
                for file in files:
                    pbar.update(1)
                    # Check if the file has the current extension
                    if file.endswith(current_extension):
                        # Build the full paths of the original and new files
                        original_file = os.path.join(path, file)
                        new_file = os.path.join(path, file.replace(current_extension, new_extension))
                        # Rename the file
                        os.rename(original_file, new_file)
                        LOGGER.debug(f"DEBUG   : Renamed: {original_file} -> {new_file}")


def delete_folder(folder_path):
    """
    Deletes a folder and all its contents.

    Args:
        folder_path (str): Path to the folder to delete.
    """
    if not os.path.exists(folder_path):
        print(f"Folder does not exist: {folder_path}")
        return

    if not os.path.isdir(folder_path):
        # return
        raise ValueError(f"Specified path is not a folder: {folder_path}")

    shutil.rmtree(folder_path)
    print(f"Deleted folder and contents: {folder_path}")


def remove_empty_dirs(input_folder, log_level=logging.INFO):
    """
    Remove empty directories recursively.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        for path, dirs, files in os.walk(input_folder, topdown=False):
            filtered_dirnames = [d for d in dirs if d != '@eaDir']
            if not filtered_dirnames and not files:
                try:
                    os.rmdir(path)
                    LOGGER.info(f"INFO    : Removed empty directory {path}")
                except OSError:
                    pass
                

def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False, log_level=logging.INFO):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Count number of sep of input_folder
        sep_input = input_folder.count(os.sep)
        # Convert wildcard patterns to regex patterns for matching
        exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
        for path, dirs, files in tqdm(os.walk(input_folder, topdown=True), ncols=120, smoothing=0.1, desc=f"INFO    : Flattening Subfolders in '{input_folder}'", unit=" subfolders"):
            # Count number of sep of root folder
            sep_root = int(path.count(os.sep))
            depth = sep_root - sep_input
            # print (f"Depth: {depth}")
            if depth > max_depth:
                # Skip deeper levels
                continue
            # If flatten_root_folder=True, then only need to flatten the root folder and it recursively will flatten all subfolders
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
                    # LOGGER.warning(f"WARNING : Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                    continue
                subfolder_path = os.path.join(path, folder)
                # LOGGER.info(f"INFO    : Flattening folder: '{dir_name}'")
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


def confirm_continue(log_level=logging.INFO):
    # If argument 'request-user-confirmarion' is false then don't ask and wait for user confirmation
    if not ARGS['request-user-confirmarion']:
        return True

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        while True:
            response = input("Do you want to continue? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                LOGGER.info(f"INFO    : Continuing...")
                return True
            elif response in ['no', 'n']:
                LOGGER.info(f"INFO    : Operation canceled.")
                return False
            else:
                LOGGER.warning(f"WARNING : Invalid input. Please enter 'yes' or 'no'.")


def remove_quotes(input_string: str, log_level=logging.INFO) -> str:
    """
    Elimina todas las comillas simples y dobles al inicio o fin de la cadena.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        return input_string.strip('\'"')


def contains_zip_files(input_folder, log_level=logging.INFO):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info("INFO    : Searching .zip files in input folder...")
        for file in os.listdir(input_folder):
            if file.endswith('.zip'):
                return True
        LOGGER.info(f"INFO    : No .zip files found in input folder.")
        return False


def remove_server_name(path, log_level=logging.INFO):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Expresión regular para rutas Linux (///servidor/)
        path = re.sub(r'///[^/]+/', '///', path)
        # Expresión regular para rutas Windows (\\servidor\)
        path = re.sub(r'\\\\[^\\]+\\', '\\\\', path)
        return path


def fix_paths(path, log_level=logging.INFO):
    fixed_path = path.replace('/', os.path.sep).replace('\\', os.path.sep)
    return fixed_path


def is_valid_path(path, log_level=logging.INFO):
    """
    Verifica si la ruta es válida en la plataforma actual.
    - Debe ser una ruta absoluta.
    - No debe contener caracteres inválidos para el sistema operativo.
    - No debe usar un formato incorrecto para la plataforma.
    """
    from pathvalidate import validate_filepath, ValidationError
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Verifica si `ruta` es válida como path en la plataforma actual.
            validate_filepath(path, platform="auto")
            return True
        except ValidationError as e:
            LOGGER.error(f"ERROR   : Path validation ERROR   : {e}")
            return False
        

def get_unique_items(list1, list2, key='filename', log_level=logging.INFO):
    """
    Returns items that are in list1 but not in list2 based on a specified key.

    Args:
        list1 (list): First list of dictionaries.
        list2 (list): Second list of dictionaries.
        key (str): Key to compare between both lists.

    Returns:
        list: Items present in list1 but not in list2.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        set2 = {item[key] for item in list2}  # Create a set of filenames from list2
        unique_items = [item for item in list1 if item[key] not in set2]
        return unique_items


def update_metadata(file_path, date_time, log_level=logging.INFO):
    """
    Updates the metadata of a file (image, video, etc.) to set the creation date.

    Args:
        file_path (str): Path to the file.
        date_time (str): Date and time in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext in PHOTO_EXT:
                update_exif_date(file_path, date_time, log_level=log_level)
            elif file_ext in VIDEO_EXT:
                update_video_metadata(file_path, date_time, log_level=log_level)
            LOGGER.debug(f"DEBUG   : Metadata updated for {file_path} with timestamp {date_time}")
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to update metadata for {file_path}. {e}")
        

def update_exif_date(image_path, asset_time, log_level=logging.INFO):
    """
    Updates the EXIF metadata of an image to set the DateTimeOriginal and related fields.

    Args:
        image_path (str): Path to the image file.
        asset_time (int or str): Timestamp in UNIX Epoch format or a date string in "YYYY-MM-DD HH:MM:SS".
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Si asset_time es una cadena en formato 'YYYY-MM-DD HH:MM:SS', conviértelo a timestamp UNIX
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError as e:
                    LOGGER.warning(f"WARNING : Invalid date format for asset_time: {asset_time}. {e}")
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
                # LOGGER.warning(f"WARNING : No EXIF metadata found in {image_path}. Creating new EXIF data.")
                # exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
                LOGGER.warning(f"WARNING : No EXIF metadata found in {image_path}. Skipping it....")
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
                LOGGER.debug(f"DEBUG   : EXIF metadata updated for {image_path} with timestamp {date_time_exif}")
            except Exception:
                LOGGER.error(f"ERROR   : Error when restoring original metadata to file: '{image_path}'")
                return
        except Exception as e:
            LOGGER.warning(f"WARNING : Failed to update EXIF metadata for {image_path}. {e}")
        

def update_video_metadata(video_path, asset_time, log_level=logging.INFO):
    """
    Updates the file system timestamps of a video file to set the creation and modification dates.

    This does NOT modify embedded metadata within the file, only the timestamps visible to the OS.

    Args:
        video_path (str): Path to the video file.
        asset_time (int | str): Timestamp in UNIX Epoch format or a string in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Convert asset_time to UNIX timestamp if it's in string format
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    LOGGER.warning(f"WARNING : Invalid date format for asset_time: {asset_time}")
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
                        LOGGER.debug(f"DEBUG     : File creation time updated for {video_path}")
                except Exception as e:
                    LOGGER.warning(f"WARNING : Failed to update file creation time on Windows. {e}")
            LOGGER.debug(f"DEBUG   : File system timestamps updated for {video_path} with timestamp {datetime.fromtimestamp(mod_time)}")
        except Exception as e:
            LOGGER.warning(f"WARNING : Failed to update video metadata for {video_path}. {e}")


def update_video_metadata_with_ffmpeg(video_path, asset_time, log_level=logging.INFO):
    """
    Updates the metadata of a video file to set the creation date without modifying file timestamps.

    Args:
        video_path (str): Path to the video file.
        asset_time (int): Timestamp in UNIX Epoch format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Si asset_time es una cadena en formato 'YYYY-MM-DD HH:MM:SS', conviértelo a timestamp UNIX
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    LOGGER.warning(f"WARNING : Invalid date format for asset_time: {asset_time}")
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
            LOGGER.debug(f"DEBUG   : Video metadata updated for {video_path} with timestamp {formatted_date}")
        except Exception as e:
            LOGGER.warning(f"WARNING : Failed to update video metadata for {video_path}. {e}")
        

# Convert to list
def convert_to_list(input_string, log_level=logging.INFO):
    """ Convert a String to List"""
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
            LOGGER.warning(f"WARNING : Failed to convert string to List for {input_string}. {e}")
        
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


# ==============================================================================
#                               DATE PARSERS
# ==============================================================================
def parse_text_to_iso8601(date_str):
    """
    Intenta convertir una cadena de fecha a formato ISO 8601 (UTC a medianoche).

    Soporta:
    - Día/Mes/Año (varios formatos)
    - Año/Mes o Mes/Año (como '2024-03' o '03/2024')
    - Solo año (como '2024')

    Args:
        date_str (str): La cadena de fecha.

    Returns:
        str | None: Fecha en formato ISO 8601 o None si no se pudo convertir.
    """
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    # Lista de formatos con día, mes y año
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            continue
    # Año y mes: YYYY-MM, YYYY/MM, MM-YYYY, MM/YYYY
    try:
        match = re.fullmatch(r"(\d{4})[-/](\d{1,2})", date_str)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        match = re.fullmatch(r"(\d{1,2})[-/](\d{4})", date_str)
        if match:
            month, year = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
    except Exception:
        pass
    # Solo año
    if re.fullmatch(r"\d{4}", date_str):
        try:
            dt = datetime(int(date_str), 1, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except Exception:
            pass
    return None


def parse_text_datetime_to_epoch(value):
    """
    Converts a datetime-like input into a UNIX epoch timestamp (in seconds).

    Priority for string parsing:
    1. ISO 8601 with timezone or 'Z'
    2. ISO format without timezone
    3. Year only (e.g., '2024') → '2024-01-01'
    4. Year and month (various formats) → 'YYYY-MM-01'
    5. Float or int string (epoch-like)

    Args:
        value (str | int | float | datetime): The input value to convert.

    Returns:
        int | None: The epoch timestamp in seconds, or None if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            # Priority 1: ISO with timezone or 'Z'
            dt = date_parser.isoparse(value)
            return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 2: ISO without timezone
            dt = datetime.fromisoformat(value)
            return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 3: Year only
            if re.fullmatch(r"\d{4}", value):
                dt = datetime(int(value), 1, 1)
                return int(dt.timestamp())
            # Priority 4: Year and month (various formats)
            match = re.fullmatch(r"(\d{4})[-/](\d{1,2})", value)
            if match:
                year, month = int(match.group(1)), int(match.group(2))
                dt = datetime(year, month, 1)
                return int(dt.timestamp())
            match = re.fullmatch(r"(\d{1,2})[-/](\d{4})", value)
            if match:
                month, year = int(match.group(1)), int(match.group(2))
                dt = datetime(year, month, 1)
                return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 5: float/int string
            return int(float(value))
        except Exception:
            return None
    if isinstance(value, datetime):
        return int(value.timestamp())
    return None


# Deprecated fucntion
def iso8601_to_epoch(iso_date):
    """
    Convierte una fecha en formato ISO 8601 a timestamp Unix (en segundos).
    Si el argumento es None o una cadena vacía, devuelve el mismo valor.

    Ejemplo:
        iso8601_to_epoch("2021-12-01T00:00:00Z") -> 1638316800
        iso8601_to_epoch("") -> -1
        iso8601_to_epoch(None) -> -1
    """
    if iso_date is None:
        return None
    try:
        if iso_date.endswith("Z"):
            iso_date = iso_date.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_date)
        return int(dt.timestamp())
    except Exception:
        # En caso de error inesperado, se devuelve -1
        return -1


# Deprecated fucntion
def epoch_to_iso8601(epoch):
    """
    Convierte un timestamp Unix (en segundos) a una cadena en formato ISO 8601 (UTC).
    Si el argumento es None o una cadena vacía, devuelve el mismo valor.

    Ejemplo:
        epoch_to_iso8601(1638316800) -> "2021-12-01T00:00:00Z"
        epoch_to_iso8601("") -> ""
        epoch_to_iso8601(None) -> ""
    """
    if epoch is None or epoch == "":
        return ""

    try:
        # Asegura que sea un número entero
        epoch = int(epoch)
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        # En caso de error inesperado, se devuelve el valor original
        return ""


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
    return ARGS.get('filter-by-type', None) or ARGS.get('filter-from-date', None) or ARGS.get('filter-to-date', None) or ARGS.get('filter-by-country', None) or ARGS.get('filter-by-city', None) or ARGS.get('filter-by-person', None)


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
        filters[key] = ARGS.get(key)
    return filters


def is_date_outside_range(date_to_check):
    from_date = parse_text_datetime_to_epoch(ARGS.get('filter-from-date'))
    to_date = parse_text_datetime_to_epoch(ARGS.get('filter-to-date'))
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


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-CHECKS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def unpack_zips(zip_folder, takeout_folder, step_name="", log_level=logging.INFO):
    """ Unzips all ZIP files from a folder into another """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if not os.path.exists(zip_folder):
            LOGGER.error(f"ERROR   : {step_name}ZIP folder '{zip_folder}' does not exist.")
            return
        os.makedirs(takeout_folder, exist_ok=True)
        for zip_file in os.listdir(zip_folder):
            if zip_file.endswith(".zip"):
                zip_path = os.path.join(zip_folder, zip_file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        LOGGER.info(f"INFO    : {step_name}Unzipping: {zip_file}")
                        zip_ref.extractall(takeout_folder)
                except zipfile.BadZipFile:
                    LOGGER.error(f"ERROR   : {step_name}Could not unzip file: {zip_file}")


def contains_takeout_structure(input_folder, step_name="", log_level=logging.INFO):
    """
    Iteratively scans directories using a manual stack instead of recursion or os.walk.
    This can reduce overhead in large, nested folder structures.
    """
    with set_log_level(LOGGER, log_level):
        LOGGER.info("")
        LOGGER.info(f"INFO    : {step_name}Looking for Google Takeout structure in input folder...")
        stack = [input_folder]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            name = entry.name
                            if name.startswith("Photos from ") and name[12:16].isdigit():
                                # LOGGER.info(f"INFO    : Found Takeout structure in folder: {entry.path}")
                                LOGGER.info(f"INFO    : {step_name}Found Takeout structure in folder: {current}")
                                return True
                            stack.append(entry.path)
            except PermissionError:
                LOGGER.warning(f"WARNING : {step_name}Permission denied accessing: {current}")
            except Exception as e:
                LOGGER.warning(f"WARNING : {step_name}Error scanning {current}: {e}")
        LOGGER.info(f"INFO    : {step_name}No Takeout structure found in input folder.")
        return False


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def delete_subfolders(input_folder, folder_name_to_delete, step_name="", log_level=logging.INFO):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        input_folder (str, Path): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Contar el total de carpetas
        total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_dirs, smoothing=0.1, desc=f"INFO    : {step_name}Deleting files within subfolders '{folder_name_to_delete}' in '{input_folder}'", unit=" subfolders") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=False):
                for folder in dirs:
                    pbar.update(1)
                    if folder == folder_name_to_delete:
                        dir_path = os.path.join(path, folder)
                        try:
                            shutil.rmtree(dir_path)
                            # LOGGER.info(f"INFO    : Deleted directory: {dir_path}")
                        except Exception as e:
                            LOGGER.error(f"ERROR   : {step_name}Error deleting {dir_path}: {e}")


def fix_mp4_files(input_folder, step_name="", log_level=logging.INFO):
    """
    Look for all .MP4 files that have the same base name as any Live Picture in the same folder.
    If found, copy the associated .json file (including those with a truncated '.supplemental-metadata')
    and rename it to match the .MP4 file, completing the truncated suffix if necessary.

    Args:
        input_folder (str): The root folder to scan.
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
    """
    with set_log_level(LOGGER, log_level):  # Set desired log level
        counter_mp4_files_changed = 0
        # Count total .mp4 files for progress bar
        all_mp4_files = []
        for _, _, files in os.walk(input_folder, topdown=True):
            for file in files:
                if file.lower().endswith('.mp4'):
                    all_mp4_files.append(file)
        total_files = len(all_mp4_files)
        if total_files == 0:
            return 0
        # Mostrar la barra de progreso basada en carpetas
        disable_tqdm = log_level < logging.WARNING
        with tqdm(total=total_files, smoothing=0.1, desc=f"INFO    : {step_name}Fixing .MP4 files in '{input_folder}'", unit=" files", disable=disable_tqdm) as pbar:
            for path, _, files in os.walk(input_folder):
                # Filter files with .mp4 extension (case-insensitive)
                mp4_files = [f for f in files if f.lower().endswith('.mp4')]
                for mp4_file in mp4_files:
                    pbar.update(1)
                    # Get the base name of the MP4 file (without extension)
                    mp4_base = os.path.splitext(mp4_file)[0]
                    # Search for JSON files with the same base name but ignoring case for the extension
                    for candidate in files:
                        if not candidate.lower().endswith('.json'):
                            continue
                        candidate_path = os.path.join(path, candidate)
                        candidate_no_ext = candidate[:-5]  # Remove .json
                        # Build a regex pattern to match: (i.e: IMG_1094.HEIC(.supplemental-metadata)?.json)

                        match = re.match(rf'({re.escape(mp4_base)}\.(heic|jpg|jpeg))(\{SUPPLEMENTAL_METADATA}.*)?$', candidate_no_ext, re.IGNORECASE)
                        if match:
                            base_part = match.group(1)
                            suffix = match.group(3) or ''
                            # Check if it's a truncated version of '.supplemental-metadata'
                            if suffix and not suffix.lower().startswith(SUPPLEMENTAL_METADATA):
                                # Try to match a valid truncation
                                for i in range(2, len(SUPPLEMENTAL_METADATA) + 1):
                                    if suffix.lower() == SUPPLEMENTAL_METADATA[:i]:
                                        suffix = '.'+SUPPLEMENTAL_METADATA
                                        break
                            # Generate the new name for the duplicated file
                            new_json_name = f"{mp4_file}{suffix}.json"
                            new_json_path = os.path.join(path, new_json_name)
                            # Check if the target file already exists to avoid overwriting
                            if not os.path.exists(new_json_path):
                                # Copy the original JSON file to the new file
                                if candidate_path.lower != new_json_path.lower():
                                    shutil.copy(candidate_path, new_json_path)
                                    LOGGER.info(f"INFO    : {step_name}Copied: {candidate} -> {new_json_name}")
                                    counter_mp4_files_changed += 1
                                    continue # if already found a matched candidate, then continue with the next file
                            else:
                                LOGGER.info(f"INFO    : {step_name}Skipped: {new_json_name} already exists")
        return counter_mp4_files_changed


# Make sure to define these constants in your module:
# SUPPLEMENTAL_METADATA = 'supplemental-metadata'
# SPECIAL_SUFFIXES = ['EFFECTS', 'SMILE', ... ]
# EDITED_SUFFIXES = ['edited', 'ha editado',  ... ]
def fix_truncations(input_folder, step_name="", log_level=logging.INFO, name_length_threshold=46):
    """
    Recursively traverses `input_folder` and fixes:
      1) .json files with a truncated '.supplemental-metadata' suffix.
      2) .json files whose original extension is truncated (e.g. .jp.json → .jpg.json),
         by finding the real asset file in the same directory.
      3) Non-.json files with truncated special suffixes (based on SPECIAL_SUFFIXES).
      4) Non-.json files with truncated edited suffixes in multiple languages (based on EDITTED).

    Only processes files whose base name (without extension) exceeds `name_length_threshold` characters.

    Args:
        input_folder (str): Path to the root folder to scan.
        step_name (str): Prefix for log messages (e.g. "DEBUG   : ").
        log_level (int): Logging level for this operation.
        name_length_threshold (int): Minimum length of the base filename (sans extension) to consider.

    Returns:
        dict: Counters of changes made, with keys:
          - total_files: total number of files found
          - total_files_fixed: number of files that were renamed at least once
          - json_files_fixed: number of .json files modified
          - non_json_files_fixed: number of non-.json files modified
          - supplemental_metadata_fixed: count of '.supplemental-metadata' fixes
          - extensions_fixed: count of JSON extension corrections
          - special_suffixes_fixed: count of special-suffix completions
          - edited_suffixes_fixed: count of edited-suffix completions
    """
    def repl(m):
        tail = m.group(0)[len(sub):-len(ext)]
        return suf + tail + ext

    # 1) Pre-count all files for reporting
    total_files = sum(len(files) for _, _, files in os.walk(input_folder))

    counters = {
        "total_files": total_files,
        "total_files_fixed": 0,
        "json_files_fixed": 0,
        "non_json_files_fixed": 0,
        "supplemental_metadata_fixed": 0,
        "extensions_fixed": 0,
        "special_suffixes_fixed": 0,
        "edited_suffixes_fixed": 0,
    }

    # 2) Build a combined regex for ANY truncated prefix of any special or edited suffix
    def make_variant_pattern(suffix_list):
        variants = set(suffix_list)
        for s in suffix_list:
            for i in range(2, len(s)):
                variants.add(s[:i])
        # sort longest first so regex matches the largest truncation before smaller ones
        return '|'.join(sorted(map(re.escape, variants), key=len, reverse=True))

    variants_specials_pattern = make_variant_pattern(SPECIAL_SUFFIXES)
    variants_editted_pattern = make_variant_pattern(EDITTED_SUFFIXES)
    optional_counter = r'(?:\(\d+\))?'  # allow "(n)" counters

    with set_log_level(LOGGER, log_level):
        # --------------------------
        # --- Case A: JSON files ---
        # --------------------------
        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + SUPPLEMENTAL_METADATA
        # Calculate max allowed truncation length (excluding the initial '.su')
        MAX_TRUNC = len(SUPPLEMENTAL_METADATA_WITH_DOT) - len('.su')
        # Compile pattern to capture truncated stub and optional counter like '(1)'
        pattern = re.compile(
            rf'(?P<base>.*?)(?P<stub>\.su[\w-]{{0,{MAX_TRUNC}}})(?P<counter>\(\d+\))?$',
            re.IGNORECASE
        )

        # Walk through all subdirectories to process only JSON files
        for root, _, files in os.walk(input_folder):
            files_set = set(files)  # for matching JSON sidecars
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() == '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # A.1) Fix truncated '.supplemental-metadata' suffix
                    match = pattern.match(name)
                    if match:
                        base = match.group('base')
                        counter = match.group('counter') or ''  # preserve any '(n)' counter
                        new_name = f"{base}{SUPPLEMENTAL_METADATA_WITH_DOT}{counter}{ext}"
                        new_path = Path(root) / new_name
                        if str(old_path).lower() != str(new_path).lower():
                            os.rename(old_path, new_path)
                            # LOGGER.info(f"INFO    : {step_name}Fixed JSON Supplemental Ext: {file} → {new_name}")
                            counters["supplemental_metadata_fixed"] += 1
                            # We need to medify file and old_path for next steps
                            file = new_name
                            old_path = new_path
                            name, ext = os.path.splitext(file)  # Refresh name and ext
                            files_set = set(os.listdir(root))   # Refresh to include any renamed files
                            if not file_modified:
                                counters["json_files_fixed"] += 1
                                counters["total_files_fixed"] += 1
                                file_modified = True
                    # end A.1

                    # A.2) Fix truncated original extension by locating the real asset file
                    parts = name.split('.')
                    if len(parts) >= 2:
                        # determine base_name and raw truncated ext (with possible "(n)")
                        if len(parts) == 2:
                            base_name, raw_trunc = parts
                        else:
                            base_name = '.'.join(parts[:-2])
                            raw_trunc = parts[-2]

                        # strip counter from raw_trunc, but save it
                        m_cnt = re.match(r'^(?P<ext>.*?)(\((?P<num>\d+)\))?$', raw_trunc)
                        trunc_ext = m_cnt.group('ext')
                        counter = f"({m_cnt.group('num')})" if m_cnt.group('num') else ''

                        # look for a matching asset: stem starts with base_name, ext starts with trunc_ext
                        full_ext = None
                        for cand in files_set:
                            if cand.lower().endswith('.json'):
                                continue
                            cand_stem = Path(cand).stem
                            if not cand_stem.lower().startswith(base_name.lower()):
                                continue
                            ext_cand = Path(cand).suffix.lstrip('.')
                            if ext_cand.lower().startswith(trunc_ext.lower()):
                                full_ext = Path(cand).suffix  # e.g. ".JPG"
                                break # Once a candidate has matched, skipp looping other candidates

                        if full_ext:
                            # replace the first ".trunc_ext" in the JSON name with the full_ext, leaving any "(n)" counter at the end untouched, then append ".json"
                            new_core = name.replace(f'.{trunc_ext}', full_ext, 1)
                            # re-attach the counter just before the ".json"
                            new_name = f"{new_core}{counter}{ext}"  # ext is ".json"
                            new_path = Path(root) / new_name
                            if not new_path.exists() and str(old_path).lower() != str(new_path).lower():
                                os.rename(old_path, new_path)
                                # LOGGER.info(f"INFO    : {step_name}Fixed JSON Origin File Ext : {file} → {new_name}")
                                counters["extensions_fixed"] += 1
                                if not file_modified:
                                    counters["json_files_fixed"] += 1
                                    counters["total_files_fixed"] += 1
                                    file_modified = True
                    # end A.2

                    if file_modified:
                        LOGGER.info(f"INFO    : {step_name}Fixed JSON File  : {original_file} → {new_name}")

        # ------------------------------------------------------------
        # --- Case B: Non-JSON files (special suffixes or editted) ---
        # ------------------------------------------------------------
        # Walk through all subdirectories to process only Non-JSON files
        for root, _, files in os.walk(input_folder):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # B.1) Fix Special Suffixes: '-effects', '-smile', '-mix', 'collage'
                    for suf in SPECIAL_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}(?=(-|_|\.|{variants_editted_pattern}|{SUPPLEMENTAL_METADATA})?(?:\(\d+\))?{re.escape(ext)}$)",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                match = pattern.search(file)
                                if match:
                                    start = match.start()
                                    end = match.end()
                                    tail = file[end:]  # everything after the matched truncation
                                    new_name = file[:start] + suf + tail
                                    new_path = Path(root) / new_name
                                    if str(old_path).lower() != str(new_path).lower():
                                        os.rename(old_path, new_path)
                                        # LOGGER.info(f"INFO    : {step_name}Fixed ORIGIN Special Suffix: {file} → {new_name}")
                                        counters["special_suffixes_fixed"] += 1
                                        # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                        file = new_name
                                        old_path = new_path
                                        if not file_modified:
                                            counters["non_json_files_fixed"] += 1
                                            counters["total_files_fixed"] += 1
                                            file_modified = True
                                    break # Once one truncation of the current suf is applied, stop trying shorter ones

                    # B.2) Fix Editted Suffixes (multi-language): '-editted', '-edytowane', '-bearbeitet', '-bewerkt', '-編集済み', '-modificato', '-modifié', '-ha editado', '-editat'
                    for suf in EDITTED_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}"
                                rf"(?:(?:{variants_editted_pattern}){optional_counter})*"
                                rf"{optional_counter}"
                                rf"{re.escape(ext)}$",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                new_name = pattern.sub(repl, file)
                                new_path = Path(root) / new_name
                                if str(old_path).lower() != str(new_path).lower():
                                    os.rename(old_path, new_path)
                                    # LOGGER.info(f"INFO    : {step_name}Fixed ORIGIN Edited Suffix : {file} → {new_name}")
                                    counters["edited_suffixes_fixed"] += 1
                                    # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                    file = new_name
                                    old_path = new_path
                                    if not file_modified:
                                        counters["non_json_files_fixed"] += 1
                                        counters["total_files_fixed"] += 1
                                        file_modified = True
                                break # Once one truncation of the current suf is applied, stop trying shorter ones

                    if file_modified:
                        LOGGER.info(f"INFO    : {step_name}Fixed MEDIA File : {original_file} → {new_name}")
    return counters


# # Function replaced by fix_truncations()
# def fix_special_suffixes(input_folder, step_name="", log_level=logging.INFO):
#     """
#     Recursively traverses a folder and its subdirectories, renaming files whose names
#     end with a partial match of any suffix in SPECIAL_SUFFIXES (before the extension or a numbered copy).
#     If a filename includes a truncated '.supplemental-metadata' suffix, it completes it instead.
#     Ignores any file with a .json extension.
#
#     Args:
#         input_folder (str): Path to the folder to be scanned and processed.
#         log_level (str): Logging level to use within this function's context.
#     """
#     with ((((set_log_level(LOGGER, log_level))))):  # Temporarily set the desired log level
#         counter_supplemental_metadata_changes = 0
#         counter_special_suffixes_changes = 0
#         counter_json_files_changed = 0
#         counter_non_json_files_changed = 0
#         # Count all files to initialize the progress bar
#         special_files = []
#         for _, _, files in os.walk(input_folder, topdown=True):
#             special_files.extend(files)
#         total_files = len(special_files)
#         if total_files == 0:
#             return FixSpecialSuffixes()
#         # Start progress bar
#         disable_tqdm = log_level < logging.WARNING
#         with tqdm(total=total_files, smoothing=0.1, desc=f"INFO    : {step_name}Fixing Truncated Special Suffixes in '{input_folder}'", unit=" files", disable=disable_tqdm) as pbar:
#             for path, _, files in os.walk(input_folder):
#                 for file in files:
#                     changed_supplemental_metadata = False
#                     changed_special_suffixes = False
#                     pbar.update(1)
#                     old_path = os.path.join(path, file)
#                     name, ext = os.path.splitext(file)
#                     # 0. Truncated filenames (without extensions) noraally have a filename lenght of 46 chars, let's exclude filenames lenght <45
#                     if len(name) < 45:
#                         continue
#
#                     # 1. Detect and complete truncated .supplemental-metadata before .json (only applies for .json extensions)
#                     if ext.lower() == '.json':
#                         for i in range(len(SUPPLEMENTAL_METADATA), 1, -1):
#                             trunc = SUPPLEMENTAL_METADATA[:i]
#                             if name.lower().endswith(trunc.lower()):
#                                 corrected_name = name[:-len(trunc)] + SUPPLEMENTAL_METADATA
#                                 new_filename = corrected_name + ext
#                                 new_path = os.path.join(path, new_filename)
#                                 if old_path.lower() != new_path.lower():
#                                     os.rename(old_path, new_path)
#                                     LOGGER.info(f"INFO    : {step_name}Fixed: {file} → {new_filename}")
#                                     file = new_filename # We need to modify the file with the new assigned name to avoid falses positives in Step 2
#                                     counter_supplemental_metadata_changes += 1
#                                     changed_supplemental_metadata = True
#                                 break # after match, we don't need to continue iterating for shorter suffix versions
#
#                         # If you don't want to apply other renaming logic when found a supplemental metadata file, then uncomment below two lines, but it may happens that a supplemental metadata file also contains special suffixes on its names
#                         # if changed_supplemental_metadata:
#                         #     continue
#
#                     # Initially I thought that the special suffixes were only added to non .json files, but it can be added to all files.
#                     # if ext.lower() == '.json':
#                     #     continue
#
#                     # 2. Apply SPECIAL_SUFFIXES completion logic (applies to .json  and other filesfiles)
#                     # Preparamos una lista con todos los sufijos completos y sus posibles truncaciones (mínimo 2 caracteres)
#                     all_variants = set()
#                     for suf in SPECIAL_SUFFIXES:
#                         all_variants.add(suf)
#                         for i in range(2, len(suf)):
#                             all_variants.add(suf[:i])
#
#                     # Ordenamos de más largo a más corto para que el regex pruebe primero las coincidencias más específicas
#                     variants_pattern = '|'.join(sorted(map(re.escape, all_variants), key=len, reverse=True))
#                     optional_counter = r'(?:\(\d+\))?'
#
#                     for sufijo in SPECIAL_SUFFIXES:
#                         for i in range(len(sufijo), 1, -1):
#                             sub = sufijo[:i]
#                             # Ahora, tras 'sub' permitimos cero o más apariciones de cualquiera de los sufijos/variantes,
#                             # cada una con su contador opcional, antes del contador final y la extensión:
#                             pattern = re.compile(
#                                 rf"{re.escape(sub)}"  # la truncación actual
#                                 rf"(?:(?:{variants_pattern})"  # uno de los sufijos/variantes
#                                 rf"{optional_counter})*"  # con su contador opcional
#                                 rf"{optional_counter}"  # contador opcional final
#                                 rf"{re.escape(ext)}$"  # y la extensión al final
#                                 , flags=re.IGNORECASE
#                             )
#                             match = pattern.search(file)
#                             if not match:
#                                 continue
#
#                             # build the new filename by replacing just _that_ suffix+counter
#                             def _repl(match):
#                                 # match.group(0) == e.g. "-SMI(2).json"
#                                 # match.group(0)[len(sub):-len(ext)] == "(2)"  (or "" if none)
#                                 return sufijo + match.group(0)[len(sub):-len(ext)] + ext
#
#                             new_filename = pattern.sub(_repl, file)
#                             new_path = os.path.join(path, new_filename)
#
#                             # only rename if the name really changed (case-insensitive)
#                             if old_path.lower() != new_path.lower():
#                                 os.rename(old_path, new_path)
#                                 LOGGER.info(f"INFO    : {step_name}Fixed: {file} → {new_filename}")
#                                 counter_special_suffixes_changes += 1
#                                 changed_special_suffixes = True
#                                 # *** update for the next suffix check! ***
#                                 file = new_filename
#                                 old_path = new_path
#                             break # whether we renamed or not, stop trying shorter truncations
#
#                     # Count only 1 change per file even if more than one suffix have been changed in the same file
#                     if changed_supplemental_metadata or changed_special_suffixes:
#                         if ext.lower() == '.json':
#                             counter_json_files_changed += 1
#                         else:
#                             counter_non_json_files_changed += 1
#
#         return FixSpecialSuffixes(
#             total_files = total_files,
#             counter_json_files_changed = counter_json_files_changed,
#             counter_non_json_files_changed = counter_non_json_files_changed,
#             counter_supplemental_metadata_changes = counter_supplemental_metadata_changes,
#             counter_special_suffixes_changes = counter_special_suffixes_changes
#         )


# # Function replaced by fix_truncations()
# def fix_truncated_extensions(input_folder, fix_special_suffixes=True, step_name="", log_level=logging.INFO):
#     """
#     Recursively traverses a directory and fixes .ext.json files that were created with truncated extensions.
#     It matches each .ext.json file with a real asset file in the same folder. If the extension is truncated,
#     it completes it. If the name ends with a truncated special suffix or a truncated '.supplemental-metadata',
#     it is also completed.
#
#     Args:
#         input_folder (str): Path to the root directory to be scanned.
#         fix_special_suffixes (bool): Whether to correct truncated special suffixes.
#         log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
#
#     Returns:
#         total_json_files (int): Total number of .json files scanned.
#         counter_truncated_extension_files_changed (int): Number of files renamed.
#     """
#     with set_log_level(LOGGER, log_level):
#         counter_truncated_extension_files_changed = 0
#
#         # Count total files for progress bar
#         json_file_list = []
#         for root, _, files in os.walk(input_folder):
#             json_file_list.extend([
#                 (root, f) for f in files
#                 if f.lower().endswith('.json')
#             ])
#
#         total_json_files = len(json_file_list)
#         disable_tqdm = log_level < logging.WARNING
#         with tqdm(total=total_json_files, smoothing=0.1, desc=f"INFO    : {step_name}Fixing Truncated Extensions in JSON files within '{input_folder}'", unit=" files", disable=disable_tqdm) as pbar:
#             for root, _, files in os.walk(input_folder):
#                 files_set = set(files)
#                 # json_files = [f for f in files if re.match(r'^.+\.[^.]+\.(json)$', f, flags=re.IGNORECASE)] # This look for double extensions files where the last extension is .json
#                 json_files = [f for f in files if f.lower().endswith('.json')]
#                 for json_file in json_files:
#                     pbar.update(1)
#                     json_path = Path(root) / json_file
#
#                     # Split off '.json' first, then split on dots
#                     filename_nojson, _ = os.path.splitext(json_file)  # remove '.json'
#                     parts = filename_nojson.split('.')
#                     if len(parts) < 2:
#                         continue
#
#                     base_name = parts[0]  # e.g. '1234..._DSCN0091'
#                     trunc_ext = parts[1]  # e.g. 'J' or 'JP'
#                     suffix_trunc = parts[2] if len(parts) > 2 else ""  # e.g. 'supplemental-meta'
#
#                     # Step 0 Truncated filenames (without extensions) use to have a filename lenght of 46 chars, let's exclude filenames lenght <45
#                     if len(filename_nojson) < 45:
#                         continue
#
#                     # Optional: complete truncated special suffix if requested
#                     suffix_full = suffix_trunc
#                     if fix_special_suffixes and suffix_trunc:
#                         # Check for supplemental-metadata first
#                         if SUPPLEMENTAL_METADATA.lower().startswith(suffix_trunc.lower()) and suffix_trunc.lower() != SUPPLEMENTAL_METADATA.lower():
#                             suffix_full = SUPPLEMENTAL_METADATA
#                         else:
#                             # Then check other suffixes
#                             for suf in SPECIAL_SUFFIXES:
#                                 if suf.lower().startswith(suffix_trunc.lower()) and suffix_trunc.lower() != suf.lower():
#                                     suffix_full = suf
#                                     break
#
#                     # Step 1: find matching real file by matching truncated extension
#                     base_with_trunc = base_name + '.' + trunc_ext
#                     possible_matches = [
#                         f for f in files_set
#                         if f.lower().startswith(base_with_trunc.lower()) and not f.lower().endswith('.json')
#                     ]
#
#                     matched_file = None
#                     for candidate in possible_matches:
#                         candidate_ext = Path(candidate).suffix.lstrip('.')  # e.g. 'jpg'
#                         # extension starts with the truncated ext and is longer -> likely match
#                         if candidate_ext.lower().startswith(trunc_ext.lower()) and candidate_ext.lower() != trunc_ext.lower():
#                             matched_file = candidate
#                             break
#                     if not matched_file:
#                         continue
#
#                     # Step 2: get correct extension from matched file
#                     correct_ext = Path(matched_file).suffix  # includes leading dot, e.g. '.JPG'
#
#                     # Step 3: construct new filename, preserving completed suffix if any
#                     if suffix_full:
#                         suffix_full = '.'+suffix_full
#                     new_json_name = f"{base_name}{correct_ext}{suffix_full}.json"
#                     json_path_new = Path(root) / new_json_name
#
#                     # Avoid overwriting existing files
#                     if json_path_new.exists():
#                         LOGGER.warning(f"WARNING : {step_name}Destination already exists: {json_path_new}")
#                     else:
#                         # Only rename if paths differ in case or content
#                         if json_path.as_posix().lower() != json_path_new.as_posix().lower():
#                             os.rename(json_path, json_path_new)
#                             LOGGER.info(f"INFO    : {step_name}Fixed: {json_file} → {new_json_name}")
#                             counter_truncated_extension_files_changed += 1
#
#         return total_json_files, counter_truncated_extension_files_changed


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def run_command(command, logger, capture_output=False, capture_errors=True, print_messages=True, step_name=""):
    """
    Ejecuta un comando. Muestra en consola actualizaciones de progreso sin loguearlas.
    Loguea solo líneas distintas a las de progreso. Corrige pegado de líneas en consola.
    """
    from CustomLogger import suppress_console_output_temporarily
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_stream(stream, is_error=False):
        import re
        from colorama import init, Fore, Style
        init(autoreset=True)

        progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)$')
        last_was_progress = False
        printed_final = set()

        while True:
            raw = stream.readline()
            if not raw:
                break

            # Limpiar ANSI y espacios finales
            ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', raw).rstrip()

            # Prefijo para agrupar barras
            common_part = line.split(' : ')[0] if ' : ' in line else line

            # 1) ¿Es barra de progreso?
            m = progress_re.search(line)
            if m:
                n, total = int(m.group(1)), int(m.group(2))
                prefix = "ERROR   :" if is_error else "INFO    :"

                # 1.a) Barra vacía (0/x)
                if n == 0:
                    if not print_messages:
                        # Log inicial
                        log_msg = f"{prefix} {step_name}{line}"
                        if is_error:
                            logger.error(log_msg)
                        else:
                            logger.info(log_msg)
                    # nunca imprimo 0/x en pantalla
                    last_was_progress = True
                    continue

                # 1.b) Progreso intermedio (1 <= n < total)
                if n < total:
                    if print_messages:
                        print(f"\r{prefix} {step_name}{line}", end='', flush=True)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    # impresión en pantalla
                    if print_messages:
                        print(f"\r{prefix} {step_name}{line}", end='', flush=True)
                        print()
                    # log final
                    log_msg = f"{prefix} {step_name}{line}"
                    if is_error:
                        logger.error(log_msg)
                    else:
                        logger.info(log_msg)

                    printed_final.add(common_part)

                last_was_progress = False
                continue

            # 2) Mensaje normal: si venía de progreso vivo, forzamos salto
            if last_was_progress and print_messages:
                print()
            last_was_progress = False

            # 3) Impresión normal
            if print_messages:
                if is_error:
                    print(f"{Fore.RED}ERROR   : {step_name}{line}")
                else:
                    if "ERROR" in line:
                        print(f"{Fore.RED}ERROR   : {step_name}{line}")
                    elif "WARNING" in line:
                        print(f"{Fore.YELLOW}WARNING : {step_name}{line}")
                    else:
                        print(f"INFO    : {step_name}{line}")

            # 4) Logging normal
            if is_error:
                logger.error(f"ERROR   : {step_name}{line}")
            else:
                if "ERROR" in line:
                    logger.error(f"ERROR   : {step_name}{line}")
                elif "WARNING" in line:
                    logger.warning(f"WARNING : {step_name}{line}")
                else:
                    logger.info(f"INFO    : {step_name}{line}")

        # 5) Al cerrar stream, si quedó un progreso vivo, cerramos línea
        if last_was_progress and print_messages:
            print()

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    with suppress_console_output_temporarily(logger):
        if not capture_output and not capture_errors:
            return subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace").returncode
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True, encoding = "utf-8", errors = "replace"
            )
            if capture_output:
                handle_stream(process.stdout, is_error=False)
            if capture_errors:
                handle_stream(process.stderr, is_error=True)

            process.wait()  # Esperar a que el proceso termine
            return process.returncode


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT POST-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sync_mp4_timestamps_with_images(input_folder, step_name="", log_level=logging.INFO):
    """
    Look for .MP4 files with the same name of any Live Picture file (.HEIC, .JPG, .JPEG) in the same folder.
    If found, then set the date and time of the .MP4 file to the same date and time of the original Live Picture.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Contar el total de archivos (para la barra de progreso)
        total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_files, smoothing=0.1,  desc=f"INFO    : {step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'", unit=" files") as pbar:
            for path, _, files in os.walk(input_folder):
                # Crear un diccionario que mapea nombres base a extensiones y nombres de archivos
                file_dict = {}
                for filename in files:
                    pbar.update(1)
                    name, ext = os.path.splitext(filename)
                    base_name = name.lower()
                    ext = ext.lower()
                    if base_name not in file_dict:
                        file_dict[base_name] = {}
                    file_dict[base_name][ext] = filename  # Guardar el nombre original del archivo
                for base_name, ext_file_map in file_dict.items():
                    if '.mp4' in ext_file_map:
                        mp4_filename = ext_file_map['.mp4']
                        mp4_file_path = os.path.join(path, mp4_filename)
                        # Buscar si existe un archivo .heic, .jpg o .jpeg con el mismo nombre
                        image_exts = ['.heic', '.jpg', '.jpeg']
                        image_file_found = False
                        for image_ext in image_exts:
                            if image_ext in ext_file_map:
                                try:
                                    image_filename = ext_file_map[image_ext]
                                    image_file_path = os.path.join(path, image_filename)
                                    if os.path.exists(image_file_path) and os.path.exists(mp4_file_path):
                                        # Obtener los tiempos de acceso y modificación del archivo de imagen
                                        image_stats = os.stat(image_file_path)
                                        atime = image_stats.st_atime  # Tiempo de último acceso
                                        mtime = image_stats.st_mtime  # Tiempo de última modificación
                                        # Aplicar los tiempos al archivo .MP4
                                        os.utime(mp4_file_path, (atime, mtime))
                                        LOGGER.debug(f"DEBUG   : {step_name}Date and time attributes synched for: {os.path.relpath(mp4_file_path,input_folder)} using:  {os.path.relpath(image_file_path,input_folder)}")
                                        image_file_found = True
                                        break  # Salir después de encontrar el primer archivo de imagen disponible
                                    else:
                                        LOGGER.warning(f"WARNING : {step_name}File not found. MP4: {mp4_file_path} | Image: {image_file_path}")
                                except Exception as e:
                                    LOGGER.error(f"ERROR   : {step_name}Could not sync timestamps for {mp4_file_path}. Reason: {e}")
                        if not image_file_found:
                            LOGGER.debug(f"DEBUG   : {step_name}Cannot find Live picture file to sync with: {os.path.relpath(mp4_file_path,input_folder)}")
                            pass


def force_remove_directory(path, log_level=logging.INFO):
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(path):
            shutil.rmtree(path, onerror=onerror)
            LOGGER.info(f"INFO    : The folder '{path}' and all its contant have been deleted.")
        else:
            LOGGER.warning(f"WARNING : Cannot delete the folder '{path}'.")


def copy_move_folder(src, dst, ignore_patterns=None, move=False, step_name="", log_level=logging.INFO):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Ignore function
        action = 'Moving' if move else 'Copying'
        try:
            if not is_valid_path(src):
                LOGGER.error(f"ERROR   : {step_name}The path '{src}' is not valid for the execution plattform. Cannot copy/move folders from it.")
                return False
            if not is_valid_path(dst):
                LOGGER.error(f"ERROR   : {step_name}The path '{dst}' is not valid for the execution plattform. Cannot copy/move folders to it.")
                return False

            def ignore_function(files, ignore_patterns):
                if ignore_patterns:
                    # Convert to a list if a single pattern is provided
                    patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
                    ignored = []
                    for pattern in patterns:
                        ignored.extend(fnmatch.filter(files, pattern))
                    return set(ignored)
                return set()

            # Ensure the source folder exists
            if not os.path.exists(src):
                raise FileNotFoundError(f"{step_name}Source folder does not exist: '{src}'")
            # Create the destination folder if it doesn't exist
            os.makedirs(dst, exist_ok=True)

            if move:
                # Contar el total de carpetas
                total_files = sum([len(files) for _, _, files in os.walk(src)])
                # Mostrar la barra de progreso basada en carpetas
                with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"INFO    : {step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                    for path, dirs, files in os.walk(src, topdown=True):
                        pbar.update(1)
                        # Compute relative path
                        rel_path = os.path.relpath(path, src)
                        # Destination path
                        dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        # Apply ignore function to files and dirs
                        ignore = ignore_function(files + dirs, ignore_patterns=ignore_patterns)
                        # Filter dirs in-place to skip ignored directories
                        dirs[:] = [d for d in dirs if d not in ignore]
                        # Create destination directory
                        os.makedirs(dest_path, exist_ok=True)
                        # Move files
                        for file in files:
                            if file not in ignore:
                                src_file = os.path.join(path, file)
                                dst_file = os.path.join(dest_path, file)
                                shutil.move(src_file, dst_file)
                    LOGGER.info(f"INFO    : {step_name}Folder moved successfully from {src} to {dst}")
            else:
                # Copy the folder contents
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
                LOGGER.info(f"INFO    : {step_name}Folder copied successfully from {src} to {dst}")
                return True
        except Exception as e:
            LOGGER.error(f"ERROR   : {step_name}Error {action} folder: {e}")
            return False


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[], step_name="", log_level=logging.INFO):
    """
    Organizes files into subfolders based on their EXIF or modification date.

    Args:
        input_folder (str): The base directory containing the files.
        type (str): 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (list): A list of subfolder names to exclude from processing.

    Raises:
        ValueError: If the value of `type` is invalid.
    """
    import os
    import shutil
    from datetime import datetime
    import piexif
    from PIL import Image
    def get_exif_date(image_path):
        try:
            exif_dict = piexif.load(image_path)
            for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                tag_id = piexif.ExifIFD.__dict__.get(tag)
                value = exif_dict["Exif"].get(tag_id)
                if value:
                    return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None
    with set_log_level(LOGGER, log_level):
        if type not in ['year', 'year/month', 'year-month']:
            raise ValueError(f"{step_name}The 'type' parameter must be 'year', 'year/month' or 'year-month'.")
        total_files = 0
        for _, dirs, files in os.walk(input_folder):
            dirs[:] = [d for d in dirs if d not in exclude_subfolders]
            total_files += len(files)
        with tqdm(total=total_files, smoothing=0.1, desc=f"INFO    : {step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_subfolders]
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                    mod_time = None
                    ext = os.path.splitext(file)[1].lower()
                    # Intentar obtener fecha EXIF si es imagen
                    if ext in PHOTO_EXT:
                        try:
                            mod_time = get_exif_date(file_path)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Error reading EXIF from {file_path}: {e}")
                    # Si no hay EXIF o no es imagen, usar fecha de sistema
                    if not mod_time:
                        try:
                            mtime = os.path.getmtime(file_path)
                            mod_time = datetime.fromtimestamp(mtime if mtime > 0 else 0)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Error reading mtime for {file_path}: {e}")
                            mod_time = datetime(1970, 1, 1)
                    LOGGER.debug(f"DEBUG   : {step_name}Using date {mod_time} for file {file_path}")
                    # Determinar carpeta destino
                    if type == 'year':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'))
                    elif type == 'year/month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'), mod_time.strftime('%m'))
                    elif type == 'year-month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y-%m'))
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(file_path, os.path.join(target_dir, file))
        LOGGER.info(f"INFO    : {step_name}Organization completed. Folder structure per '{type}' created in '{input_folder}'.")


def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder=None, step_name="", log_level=logging.INFO):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str): Path to the input folder containing the albums.
        albums_subfolder (str): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        def safe_move(folder_path, albums_path):
            destination = os.path.join(albums_path, os.path.basename(folder_path))
            if os.path.exists(destination):
                if os.path.isdir(destination):
                    shutil.rmtree(destination)
                else:
                    os.remove(destination)
            shutil.move(folder_path, albums_path)

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]
        albums_path = os.path.join(input_folder, albums_subfolder)
        exclude_subfolder_paths = [os.path.abspath(os.path.join(input_folder, sub)) for sub in (exclude_subfolder or [])]
        subfolders = os.listdir(input_folder)
        subfolders = [subfolder for subfolder in subfolders if not subfolder == '@eaDir' and not subfolder == 'No-Albums']
        for subfolder in tqdm(subfolders, smoothing=0.1, desc=f"INFO    : {step_name}Moving Albums in '{input_folder}' to Subolder '{albums_subfolder}'", unit=" albums"):
            folder_path = os.path.join(input_folder, subfolder)
            if os.path.isdir(folder_path) and subfolder != albums_subfolder and os.path.abspath(folder_path) not in exclude_subfolder_paths:
                LOGGER.debug(f"DEBUG   : {step_name}Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'")
                os.makedirs(albums_path, exist_ok=True)
                safe_move(folder_path, albums_path)
        # Finally Move Albums to Albums root folder (removing 'Takeout' and 'Google Fotos' / 'Google Photos' folders if exists
        move_albums_to_root(albums_path, step_name=step_name, log_level=logging.INFO)


def move_albums_to_root(albums_root, step_name="", log_level=logging.INFO):
    """
    Moves all albums from nested subdirectories ('Takeout/Google Fotos' or 'Takeout/Google Photos')
    directly into the 'Albums' folder, removing unnecessary intermediate folders.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        possible_google_folders = ["Google Fotos", "Google Photos"]
        takeout_path = os.path.join(albums_root, "Takeout")
        # Check if 'Takeout' exists
        if not os.path.exists(takeout_path):
            LOGGER.debug(f"DEBUG   : {step_name}'Takeout' folder not found at {takeout_path}. Exiting.")
            return
        # Find the actual Google Photos folder name
        google_photos_path = None
        for folder in possible_google_folders:
            path = os.path.join(takeout_path, folder)
            if os.path.exists(path):
                google_photos_path = path
                break
        if not google_photos_path:
            LOGGER.debug(f"DEBUG   : {step_name}No valid 'Google Fotos' or 'Google Photos' folder found inside 'Takeout'. Exiting.")
            return
        LOGGER.debug(f"DEBUG   : {step_name}Found Google Photos folder: {google_photos_path}")
        LOGGER.info(f"INFO    : {step_name}Moving Albums to Albums root folder...")
        # Move albums to the root 'Albums' directory
        for album in os.listdir(google_photos_path):
            album_path = os.path.join(google_photos_path, album)
            target_path = os.path.join(albums_root, album)
            if os.path.isdir(album_path):  # Ensure it's a directory (album)
                new_target_path = target_path
                count = 1
                # Handle naming conflicts by adding a suffix
                while os.path.exists(new_target_path):
                    new_target_path = f"{target_path}_{count}"
                    count += 1
                # Move the album
                shutil.move(album_path, new_target_path)
                LOGGER.debug(f"DEBUG   : {step_name}Moved: {album_path} → {new_target_path}")
        # Attempt to remove empty folders
        try:
            shutil.rmtree(takeout_path)
            LOGGER.debug(f"DEBUG   : {step_name}'Takeout' folder successfully removed.")
        except Exception as e:
            LOGGER.error(f"ERROR   : {step_name}Failed to remove 'Takeout': {e}")


# def count_valid_albums(folder_path, step_name="", log_level=logging.INFO):
#     """
#     Counts the number of subfolders within folder_path and its sublevels
#     that contain at least one valid image or video file.
#
#     A folder is considered valid if it contains at least one file with an extension
#     defined in IMAGE_EXT or VIDEO_EXT.
#     """
#     import os
#     from GlobalVariables import PHOTO_EXT, VIDEO_EXT
#     with set_log_level(LOGGER, log_level):  # Change log level temporarily
#         valid_albums = 0
#         for root, dirs, files in os.walk(folder_path):
#             # Check if there's at least one valid image or video file
#             if any(os.path.splitext(file)[1].lower() in PHOTO_EXT or os.path.splitext(file)[1].lower() in VIDEO_EXT for file in files):
#                 valid_albums += 1
#         return valid_albums


def count_valid_albums(folder_path, excluded_folders=[], step_name="", log_level=logging.INFO):
    """
    Counts the number of subfolders within folder_path and its sublevels
    that contain at least one valid image or video file.

    A folder is considered valid if it contains at least one file with an extension
    defined in PHOTO_EXT or VIDEO_EXT.

    The following folders (and all their subfolders) are excluded from the count:
    - Any folder named 'Photos from YYYY' where YYYY starts with 1 or 2.
    - Folders named exactly as excluded_folder list.
    """
    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        valid_albums = 0
        for root, dirs, files in os.walk(folder_path):
            folder_name = os.path.basename(root)
            # Skip current folder if it matches any exclusion rule
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()  # Prevent descending into subdirectories
                continue
            # Also remove excluded subfolders from being walked into
            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]
            # Check for at least one valid image or video file
            if any(os.path.splitext(file)[1].lower() in PHOTO_EXT or os.path.splitext(file)[1].lower() in VIDEO_EXT for file in files):
                valid_albums += 1
        return valid_albums



def fix_symlinks_broken(input_folder, step_name="", log_level=logging.INFO):
    """
    Searches and fixes broken symbolic links in a directory and its subdirectories.
    Optimized to handle very large numbers of files by indexing files beforehand.

    :param input_folder: Path (relative or absolute) to the main directory where the links should be searched and fixed.
    :return: A tuple containing the number of corrected symlinks and the number of symlinks that could not be corrected.
    """
    # ===========================
    # AUX FUNCTIONS
    # ===========================
    def build_file_index(input_folder, log_level=logging.INFO):
        """
        Index all non-symbolic files in the directory and its subdirectories by their filename.
        Returns a dictionary where keys are filenames and values are lists of their full paths.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            file_index = {}
            # Contar el total de carpetas
            total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
            if total_files == 0:
                return file_index
            # Mostrar la barra de progreso basada en carpetas
            with tqdm(total=total_files, smoothing=0.1, desc=f"INFO    : {step_name}Building Index files in '{input_folder}'", unit=" files") as pbar:
                for path, _, files in os.walk(input_folder):
                    for fname in files:
                        pbar.update(1)
                        full_path = os.path.join(path, fname)
                        # Only index real files (not symbolic links)
                        if os.path.isfile(full_path) and not os.path.islink(full_path):
                            # Add the path to the index
                            if fname not in file_index:
                                file_index[fname] = []
                            file_index[fname].append(full_path)
            return file_index
    
    def find_real_file(file_index, target_name, log_level=logging.INFO):
        """
        Given a pre-built file index (dict: filename -> list of paths),
        return the first available real file path for the given target_name.
        If multiple matches exist, return the first found.
        If none is found, return None.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            if target_name in file_index and file_index[target_name]:
                return file_index[target_name][0]
            return None

    # ===========================
    # END AUX FUNCTIONS
    # ===========================
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        corrected_count = 0
        failed_count = 0
        # Validate the directory existence
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : {step_name}The directory '{input_folder}' does not exist or is not valid.")
            return 0, 0
        # Step 1: Index all real non-symbolic files
        file_index = build_file_index(input_folder)
        # Step 2: Search for broken symbolic links and fix them using the index
        already_warned = False
        total_files = sum([len(files) for _, _, files in os.walk(input_folder)]) # Contar el total de carpetas
        if total_files ==0:
            corrected_count, failed_count
        with tqdm(total=total_files, smoothing=0.1, desc=f"INFO    : {step_name}Fixing Symbolic Links in '{input_folder}'", unit=" files") as pbar: # Mostrar la barra de progreso basada en carpetas
            for path, _, files in os.walk(input_folder):
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if os.path.islink(file_path) and not os.path.exists(file_path):
                        # It's a broken symbolic link
                        target = os.readlink(file_path)
                        # LOGGER.info(f"INFO    : Broken link found: {file_path} -> {target}")
                        target_name = os.path.basename(target)

                        fixed_path = find_real_file(file_index, target_name)
                        if fixed_path:
                            # Create the correct symbolic link
                            relative_path = os.path.relpath(fixed_path, start=os.path.dirname(file_path))
                            # LOGGER.info(f"INFO    : Fixing link: {file_path} -> {relative_path}")
                            os.unlink(file_path)
                            os.symlink(relative_path, file_path)
                            corrected_count += 1
                        else:
                            if not already_warned:
                                LOGGER.warning("")
                                already_warned=True
                            LOGGER.warning(f"WARNING : {step_name}Could not find the file for {file_path} within {input_folder}")
                            failed_count += 1
        return corrected_count, failed_count


def rename_album_folders(input_folder: str, exclude_subfolder=None, type_date_range='complete', step_name="", log_level=logging.INFO):
    # ===========================
    # AUXILIARY FUNCTIONS
    # ===========================
    def clean_name_and_remove_dates(input_string: str, log_level=logging.INFO) -> dict:
        """
        Removes date or date range prefixes from the input string and returns a dictionary
        with the cleaned name and the extracted date(s).

        Returns:
            dict: {
                "clean-name": str,  # The input string with the date(s) removed
                "dates": str        # The removed date(s) prefix, or empty string if none found
            }
        """
        import re
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            input_string = input_string.strip()
            # Remove leading underscores or hyphens
            input_string = re.sub(r'^[-_]+', '', input_string)
            # Replace underscores or hyphens between numbers with dots (2023_11_23 → 2023.11.23)
            input_string = re.sub(r'(?<=\d)[_-](?=\d)', '.', input_string)
            # Convert yyyymmdd to yyyy.mm.dd (for years starting with 19xx or 20xx)
            input_string = re.sub(r'\b((19|20)\d{2})(\d{2})(\d{2})\b', r'\1.\3.\4', input_string)
            # Convert yyyymm to yyyy.mm (for years starting with 19xx or 20xx)
            input_string = re.sub(r'\b((19|20)\d{2})(\d{2})\b', r'\1.\3', input_string)
            # Convert ddmmyyyy to yyyy.mm.dd
            input_string = re.sub(r'\b(\d{2})(\d{2})((19|20)\d{2})\b', r'\3.\2.\1', input_string)
            # Convert mmyyyy to yyyy.mm
            input_string = re.sub(r'\b(\d{2})((19|20)\d{2})\b', r'\2.\1', input_string)
            # Replace underscores or hyphens between letters with spaces
            input_string = re.sub(r'(?<=[a-zA-Z])[_-](?=[a-zA-Z])', ' ', input_string)
            # Replace year ranges separated by dots with hyphens (1995.2004 → 1995-2004)
            input_string = re.sub(r'\b((19|20)\d{2})\.(?=(19|20)\d{2})', r'\1-', input_string)
            # Replace underscore/hyphen preceded by digit and followed by letter (1_A → 1 - A)
            input_string = re.sub(r'(?<=\d)[_-](?=[a-zA-Z])', ' - ', input_string)
            # Replace the last dot with an underscore in dddd.dd.dd.dd format anywhere in the string
            input_string = re.sub(r'((19|20)\d{2}\.\d{2}\.\d{2})\.(\d{2})', r'\1_\3', input_string)
            # Patrón para detectar fecha o rango de fechas al inicio del string
            pattern = re.compile(
                r"""^                   # inicio del string
                (                                           # ← aquí empieza grupo 1
                    (?:19|20)\d{2}                          # yyyy (año)
                    (?:[._-](?:0[1-9]|1[0-2]))?             # opcional: .mm o -mm o _mm (mes precedido de '.', '-' o '_')
                    (?:[._-](?:0[1-9]|[12]\d|3[01]))?       # opcional: .dd o -dd o _dd (día precedido de '.', '-' o '_')
                    (?:\s*[-_]\s*                           # comienzo de rango opcional (comienza al detectar el separador del rango)
                        (?:19|20)\d{2}                      # yyyy (año) dentro del rango opcional
                        (?:[._-](?:0[1-9]|1[0-2]))?         # opcional dentro del rango opcional: .mm o -mm o _mm (mes precedido de '.', '-' o '_')
                        (?:[._-](?:0[1-9]|[12]\d|3[01]))?   # opcional dentro del rango opcional: .dd o -dd o _dd (día precedido de '.', '-' o '_')
                    )?                                      # fin rango opcional
                )                                           # ← aquí termina grupo 1                 
                \s*[-_]\s*                                  # separador tras la fecha o rango (FUERA de grupo 1)               
                """,
                flags=re.VERBOSE
            )
            match = pattern.match(input_string)
            original_dates = match.group(1) if match else ""
            clean_name = input_string[match.end():] if match else input_string
            return {
                "clean-name": clean_name,
                "original-dates": original_dates
            }


    def get_content_based_year_range(folder: str, log_level=logging.INFO) -> str:
        def get_exif_date(image_path):
            try:
                exif_dict = piexif.load(image_path)
                for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                    tag_id = piexif.ExifIFD.__dict__.get(tag)
                    value = exif_dict["Exif"].get(tag_id)
                    if value:
                        return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
            return None

        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                years = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    exif_date = None
                    fs_date = None
                    if ext in PHOTO_EXT:
                        # Intenta obtener EXIF
                        try:
                            exif_date = get_exif_date(f)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Error reading EXIF from {f}: {e}")
                        # Intenta obtener mtime
                        try:
                            ts = os.path.getmtime(f)
                            if ts > 0:
                                fs_date = datetime.fromtimestamp(ts)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Cannot read timestamp from {f}: {e}")
                    # Elige la fecha más antigua entre EXIF y mtime
                    chosen_date = None
                    if exif_date and fs_date:
                        chosen_date = min(exif_date, fs_date)
                    else:
                        chosen_date = exif_date or fs_date
                    if chosen_date:
                        years.append(chosen_date.year)
                if not years:
                    LOGGER.warning(f"WARNING : {step_name}No valid timestamps found in {folder}")
                    return False
                # Extraer componentes
                oldest_year = min(years)
                latest_year = max(years)
                if oldest_year == latest_year:
                    return str(oldest_year)
                else:
                    return f"{oldest_year}-{latest_year}"
            except Exception as e:
                LOGGER.error(f"ERROR   : {step_name}Error obtaining year range: {e}")
            return False


    def get_content_based_date_range(folder: str, log_level=logging.INFO) -> str:
        def get_exif_date(image_path):
            try:
                exif_dict = piexif.load(image_path)
                for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                    tag_id = piexif.ExifIFD.__dict__.get(tag)
                    value = exif_dict["Exif"].get(tag_id)
                    if value:
                        return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
            return None

        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                dates = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    exif_date = None
                    fs_date = None
                    if ext in PHOTO_EXT:
                        try:
                            exif_date = get_exif_date(f)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Error reading EXIF from {f}: {e}")
                        try:
                            ts = os.path.getmtime(f)
                            if ts > 0:
                                fs_date = datetime.fromtimestamp(ts)
                        except Exception as e:
                            LOGGER.warning(f"WARNING : {step_name}Cannot read timestamp from {f}: {e}")
                        # Escoger la fecha más antigua disponible
                        chosen_date = None
                        if exif_date and fs_date:
                            chosen_date = min(exif_date, fs_date)
                        else:
                            chosen_date = exif_date or fs_date
                        if chosen_date:
                            dates.append(chosen_date)
                if not dates:
                    LOGGER.warning(f"WARNING : {step_name}No valid timestamps found in {folder}")
                    return False
                # Extraer componentes
                years = {dt.year for dt in dates}
                months = {(dt.year, dt.month) for dt in dates}
                days = {(dt.year, dt.month, dt.day) for dt in dates}
                if len(days) == 1:
                    dt = dates[0]
                    return f"{dt.year:04}.{dt.month:02}.{dt.day:02}"
                elif len(months) == 1:
                    y, m = next(iter(months))
                    return f"{y:04}.{m:02}"
                elif len(years) == 1:
                    sorted_months = sorted(months)
                    start = f"{sorted_months[0][0]:04}.{sorted_months[0][1]:02}"
                    end = f"{sorted_months[-1][0]:04}.{sorted_months[-1][1]:02}"
                    return f"{start}-{end}"
                else:
                    return f"{min(years):04}-{max(years):04}"
            except Exception as e:
                LOGGER.error(f"ERROR   : {step_name}Error obtaining date range: {e}")
                return False

    # ===========================
    # END AUX FUNCTIONS
    # ===========================
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Initial template for rename results
        renamed_album_folders = 0
        duplicates_album_folders = 0
        duplicates_albums_fully_merged = 0
        duplicates_albums_not_fully_merged = 0
        debug_messages = []
        info_messages = []
        warning_messages = []

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]

        total_folders = get_subfolders_with_exclusions(input_folder, exclude_subfolder)

        for original_folder_name in tqdm(total_folders, smoothing=0.1, desc=f"INFO    : {step_name}Renaming Albums folders in '<OUTPUT_TAKEOUT_FOLDER>'", unit=" folders"):
            item_path = os.path.join(input_folder, original_folder_name)
            if os.path.isdir(item_path):
                resultado = clean_name_and_remove_dates(original_folder_name)
                cleaned_folder_name = resultado["clean-name"]
                original_dates = resultado["original-dates"]
                # If folder name does not start with a year (19xx or 20xx)
                if not re.match(r'^(19|20)\d{2}', cleaned_folder_name):
                    # Determine the date prefix depending on the argument type_date_range: year:2022-2024 or complete: 2022.06-2024-01
                    if type_date_range.lower() == 'complete':
                        content_based_date_range = get_content_based_date_range(item_path)
                    elif type_date_range.lower() == 'year':
                        content_based_date_range = get_content_based_year_range(item_path)
                    else:
                        warning_messages.append(f"WARNING : {step_name}No valid type_date_range: '{type_date_range}'")
                    # if not possible to find a date_raange, keep the original_dates (if exits) as prefix of the cleaned_folder_name
                    if content_based_date_range:
                        cleaned_folder_name = f"{content_based_date_range} - {cleaned_folder_name}"
                        debug_messages.append(f"DEBUG   : Added date prefix '{content_based_date_range}' to folder: '{os.path.basename(cleaned_folder_name)}'")
                    else:
                        if original_dates:
                            cleaned_folder_name = f"{original_dates} - {cleaned_folder_name}"
                            debug_messages.append(f"DEBUG   : Keep date prefix '{original_dates}' in folder: '{os.path.basename(cleaned_folder_name)}'")
                        else:
                            cleaned_folder_name = f"{cleaned_folder_name}"
                            debug_messages.append(f"DEBUG   : No date prefix found in folder: '{os.path.basename(cleaned_folder_name)}'")

                # Skip renaming if the clean name is the same as the original
                if cleaned_folder_name != original_folder_name:
                    new_folder_path = os.path.join(input_folder, cleaned_folder_name)
                    if os.path.exists(new_folder_path):
                        duplicates_album_folders += 1
                        warning_messages.append(f"WARNING : {step_name}Folder '{new_folder_path}' already exists. Merging contents...")
                        for item in os.listdir(item_path):
                            src = os.path.join(item_path, item)
                            dst = os.path.join(new_folder_path, item)
                            if os.path.exists(dst):
                                # Compare file sizes to decide if the original should be deleted
                                if os.path.isfile(dst) and os.path.getsize(src) == os.path.getsize(dst):
                                    os.remove(src)
                                    info_messages.append(f"INFO    : {step_name}Deleted duplicate file: '{src}'")
                            else:
                                shutil.move(src, dst)
                                info_messages.append(f"INFO    : {step_name}Moved '{src}' → '{dst}'")
                        # Check if the folder is empty before removing it
                        if not os.listdir(item_path):
                            os.rmdir(item_path)
                            info_messages.append(f"INFO    : {step_name}Removed empty folder: '{item_path}'")
                            duplicates_albums_fully_merged += 1
                        else:
                            # LOGGER.warning(f"WARNING : Folder not empty, skipping removal: {item_path}")
                            duplicates_albums_not_fully_merged += 1
                    else:
                        if item_path != new_folder_path:
                            os.rename(item_path, new_folder_path)
                            info_messages.append(f"INFO    : {step_name}Renamed folder: '{os.path.basename(item_path)}' → '{os.path.basename(new_folder_path)}'")
                            renamed_album_folders += 1

        # Finally we log all the messages captured during the process
        for debug_message in debug_messages:
            LOGGER.debug(debug_message)
        for info_message in info_messages:
            LOGGER.info(info_message)
        for warning_message in warning_messages:
            LOGGER.warning(warning_message)

        # return renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged
        return {
            'renamed_album_folders': renamed_album_folders,
            'duplicates_album_folders': duplicates_album_folders,
            'duplicates_albums_fully_merged': duplicates_albums_fully_merged,
            'duplicates_albums_not_fully_merged': duplicates_albums_not_fully_merged,
        }
