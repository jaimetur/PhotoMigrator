import fnmatch
import logging
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from Core.CustomLogger import set_log_level, custom_print
from Core.GlobalVariables import LOGGER, MSG_TAGS, RESOURCES_IN_CURRENT_FOLDER, SCRIPT_NAME
from Utils.GeneralUtils import tqdm


# ---------------------------------------------------------------------------------------------------------------------------
# FILES & FOLDERS MANAGEMENT FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
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

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Verifica si `ruta` es válida como path en la plataforma actual.
            validate_filepath(path, platform="auto")
            return True
        except ValidationError as e:
            LOGGER.error(f"Path validation ERROR: {e}")
            return False

def dir_exists(dir):
    return os.path.isdir(dir)

def delete_subfolders(input_folder, folder_name_to_delete, step_name="", log_level=None):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        input_folder (str, Path): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
        :param step_name:
        :param log_level:
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Contar el total de carpetas
        total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_dirs, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Deleting files within subfolders '{folder_name_to_delete}' in '{input_folder}'", unit=" subfolders") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=False):
                for folder in dirs:
                    pbar.update(1)
                    if folder == folder_name_to_delete:
                        dir_path = os.path.join(path, folder)
                        try:
                            shutil.rmtree(dir_path)
                            # LOGGER.info(f"Deleted directory: {dir_path}")
                        except Exception as e:
                            LOGGER.error(f"{step_name}Error deleting {dir_path}: {e}")


def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False, log_level=None):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
        :param log_level:
        :param input_folder:
        :param exclude_subfolders:
        :param max_depth:
        :param flatten_root_folder:
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Count number of sep of input_folder
        sep_input = input_folder.count(os.sep)
        # Convert wildcard patterns to regex patterns for matching
        exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
        for path, dirs, files in tqdm(os.walk(input_folder, topdown=True), ncols=120, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Flattening Subfolders in '{input_folder}'", unit=" subfolders"):
            # Count number of sep of root folder
            sep_root = int(path.count(os.sep))
            depth = sep_root - sep_input
            LOGGER.verbose(f"Depth: {depth}")
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
                    # LOGGER.warning(f"Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                    continue
                subfolder_path = os.path.join(path, folder)
                # LOGGER.info(f"Flattening folder: '{dir_name}'")
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


def remove_empty_dirs(input_folder, log_level=None):
    """
    Remove empty directories recursively.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        for path, dirs, files in os.walk(input_folder, topdown=False):
            filtered_dirnames = [d for d in dirs if d != '@eaDir']
            if not filtered_dirnames and not files:
                try:
                    os.rmdir(path)
                    LOGGER.info(f"Removed empty directory {path}")
                except OSError:
                    pass


def remove_folder(folder, step_name='', log_level=None):
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
    with set_log_level(LOGGER, log_level):  # Temporarily adjust LOGGER’s level for this operation
        folder_path = Path(folder)
        try:
            LOGGER.debug(f"{step_name}Attempting to remove: {folder_path}")
            shutil.rmtree(folder_path)
            LOGGER.info(f"{step_name}Folder '{folder_path}' removed successfully.")
            return True

        except FileNotFoundError:
            LOGGER.info(f"{step_name}Folder '{folder_path}' was not found. Nothing to remove!")
            return False

        except PermissionError:
            LOGGER.error(f"{step_name}Insufficient permissions to remove: '{folder_path}'.")
            return False

        except Exception as e:
            LOGGER.critical(f"{step_name}Unexpected error while removing '{folder_path}': {e}")
            return False


def resource_path(relative_path):
    """
    Devuelve la ruta absoluta al recurso 'relative_path', funcionando en:
    - PyInstaller (onefile o standalone)
    - Nuitka (onefile o standalone)
    - Python directo (desde cwd o desde dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because is also used by build-binary.py which has not any LOGGER created.
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
            custom_print(f"__compiled__.containing_dir : {__compiled__.containing_dir}", log_level=logging.DEBUG)
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
    elif "__compiled__" in globals():
        base_path = os.path.join(__compiled__.containing_dir, SCRIPT_NAME+'.dist')
        # base_path = __compiled__
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


def contains_zip_files(input_folder, log_level=None):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Searching .zip files in input folder...")
        for file in os.listdir(input_folder):
            if file.endswith('.zip'):
                return True
        LOGGER.info(f"No .zip files found in input folder.")
        return False


def normalize_path(path, log_level=None):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # return os.path.normpath(path).strip(os.sep)
        return os.path.normpath(path)
