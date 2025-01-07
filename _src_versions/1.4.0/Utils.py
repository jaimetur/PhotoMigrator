import os, sys
import platform
import subprocess
import shutil
import zipfile
import logging
import fnmatch
import re
import hashlib
import argparse
import textwrap
import time
from datetime import datetime

######################
# FUNCIONES AUXILIARES
######################

def resource_path(relative_path):
    """Obtener la ruta absoluta al recurso, manejando el entorno de PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def fix_metadata_with_gpth_tool(input_folder, output_folder,skip_extras=False, move_takeout_folder=False, ignore_takeout_structure=False):
    """Runs the GPTH Tool command to process photos."""
    logger.info(f"INFO: Running GPTH Tool from '{input_folder}' to '{output_folder}'...")
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    script_name = ""
    if current_os == "Linux":
        script_name = "gpth"
    elif current_os == "Darwin":
        script_name = "gpth"
    elif current_os == "Windows":
        script_name = "gpth.exe"
    # Usar resource_path para acceder a archivos o directorios:
    gpth_tool_path = resource_path(os.path.join("gpth_tool",script_name))
    gpth_command = [
        gpth_tool_path,
        "--input", input_folder,
        "--output", output_folder,
        "--no-interactive", "--albums", "duplicate-copy"
    ]
    # Append --skip-extras to the gpth tool call based on the value of flag -se, --skip-extras
    if skip_extras:
            gpth_command.append("--skip-extras")
    # Append --copy/--no-copy to the gpth tool call based on the values of move_takeout_folder
    if move_takeout_folder:
        gpth_command.append("--no-copy")
    else:
        gpth_command.append("--copy")
    # By default force --no-divide-to-dates and the script will create date structure if needed
    gpth_command.append("--no-divide-to-dates")
    # If ignore_takeout_structure is True, we append --fix input_folder to the gpth tool call
    if ignore_takeout_structure:
        gpth_command.append("--fix")
        gpth_command.append(input_folder)
    try:
        # print (" ".join(gpth_command))
        result = subprocess.run(gpth_command, check=True, capture_output=False)
        logger.info(f"INFO: GPTH Tool finxing completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: GPTH Tool fixing failed:\n{e.stderr}")

def fix_metadata_with_exif_tool(output_folder):
    """Runs the EXIF Tool command to fix photo metadata."""
    logger.info(f"INFO: Fixing EXIF metadata in '{output_folder}'...")
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    script_name = ""
    if current_os == "Linux":
        script_name = "exiftool"
    elif current_os == "Darwin":
        script_name = "exiftool"
    elif current_os == "Windows":
        script_name = "exiftool.exe"
    # Usar resource_path para acceder a archivos o directorios:
    exif_tool_path = resource_path(os.path.join("exif_tool",script_name))
    exif_command = [
        exif_tool_path,
        "-overwrite_original",
        "-ExtractEmbedded",
        "-r",
        '-datetimeoriginal<filemodifydate',
        "-if", "(not $datetimeoriginal or ($datetimeoriginal eq '0000:00:00 00:00:00'))",
        output_folder
    ]
    try:
        # print (" ".join(exif_command))
        result = subprocess.run(exif_command, check=False)
        logger.info(f"INFO: EXIF Tool fixing completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: EXIF Tool fixing failed:\n{e.stderr}")

def count_files_in_folder(folder_path):
    """Counts the number of files in a folder."""
    total_files = 0
    for root, dirs, files in os.walk(folder_path):
        total_files += len(files)
    return total_files

def unpack_zips(zip_folder, takeout_folder):
    """Unzips all ZIP files from a folder into another."""
    if not os.path.exists(zip_folder):
        logger.error(f"ERROR: ZIP folder '{zip_folder}' does not exist.")
        return
    os.makedirs(takeout_folder, exist_ok=True)
    for zip_file in os.listdir(zip_folder):
        if zip_file.endswith(".zip"):
            zip_path = os.path.join(zip_folder, zip_file)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    logger.info(f"INFO: Unzipping: {zip_file}")
                    zip_ref.extractall(takeout_folder)
            except zipfile.BadZipFile:
                logger.error(f"ERROR: Could not unzip file: {zip_file}")

def fix_mp4_files(input_folder):
    """
    Look for all .MP4 files that have the same name of any Live picture and is in the same folder.
    If found any, then copy the .json file of the original Live picture and change its name to the name of the .MP4 file
    """
    # Traverse all subdirectories in the input folder
    for root, _, files in os.walk(input_folder):
        # Filter files with .mp4 extension (case-insensitive)
        mp4_files = [f for f in files if f.lower().endswith('.mp4')]
        
        for mp4_file in mp4_files:
            # Get the base name of the MP4 file (without extension)
            mp4_base_name = os.path.splitext(mp4_file)[0]

            # Define possible JSON extensions (case-insensitive)
            json_extensions = ['.heic.json', '.jpg.json', '.jpeg.json']
            # Search for JSON files with the same base name but ignoring case for the extension
            for ext in json_extensions:
                json_file_candidates = [
                    f for f in files
                    if f.startswith(mp4_base_name) and f.lower().endswith(ext.lower())
                ]
                for json_file in json_file_candidates:
                    json_path = os.path.join(root, json_file)
                    # Generate the new name for the duplicated file
                    new_json_name = f"{mp4_file}.json"
                    new_json_path = os.path.join(root, new_json_name)
                    # Check if the target file already exists to avoid overwriting
                    if not os.path.exists(new_json_path):
                        # Copy the original JSON file to the new file
                        shutil.copy(json_path, new_json_path)
                        logger.info(f"INFO: Fixed: {json_path} -> {new_json_path}")
                    else:
                        logger.info(f"INFO: Skipped: {new_json_path} already exists")


def sync_mp4_timestamps_with_images(input_folder):
    """
    Look for .MP4 files with the same name of any Live Picture file (.HEIC, .JPG, .JPEG) in the same folder.
    If found, then set the date and time of the .MP4 file to the same date and time of the original Live Picture.
    """
    for root, dirs, files in os.walk(input_folder):
        # Crear un diccionario que mapea nombres base a extensiones y nombres de archivos
        file_dict = {}
        for filename in files:
            name, ext = os.path.splitext(filename)
            base_name = name.lower()
            ext = ext.lower()
            if base_name not in file_dict:
                file_dict[base_name] = {}
            file_dict[base_name][ext] = filename  # Guardar el nombre original del archivo
        for base_name, ext_file_map in file_dict.items():
            if '.mp4' in ext_file_map:
                mp4_filename = ext_file_map['.mp4']
                mp4_file_path = os.path.join(root, mp4_filename)
                # Buscar si existe un archivo .heic, .jpg o .jpeg con el mismo nombre
                image_exts = ['.heic', '.jpg', '.jpeg']
                image_file_found = False
                for image_ext in image_exts:
                    if image_ext in ext_file_map:
                        image_filename = ext_file_map[image_ext]
                        image_file_path = os.path.join(root, image_filename)
                        # Obtener los tiempos de acceso y modificación del archivo de imagen
                        image_stats = os.stat(image_file_path)
                        atime = image_stats.st_atime  # Tiempo de último acceso
                        mtime = image_stats.st_mtime  # Tiempo de última modificación
                        # Aplicar los tiempos al archivo .MP4
                        os.utime(mp4_file_path, (atime, mtime))
                        logger.info(f"INFO: Date and time attributes synched for: {os.path.relpath(mp4_file_path,input_folder)} using:  {os.path.relpath(image_file_path,input_folder)}")
                        image_file_found = True
                        break  # Salir después de encontrar el primer archivo de imagen disponible
                if not image_file_found:
                    pass
                    #logger.warning(f"WARNING: Cannot find Live picture file to sync with: {os.path.relpath(mp4_file_path,input_folder)}")


def organize_files_by_date(base_dir, type='year', exclude_subfolders=[]):
    """
    Organizes files into subfolders based on their modification date.

    Args:
        base_dir (str): The base directory containing the files.
        type (str): 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (list): A list of subfolder names to exclude from processing.

    Raises:
        ValueError: If the value of `type` is invalid.
    """
    if type not in ['year', 'year/month', 'year-month']:
        raise ValueError("The 'type' parameter must be 'year' or 'year/month'.")
    for root, dirs, files in os.walk(base_dir, topdown=True):
        # Exclude specified subfolders
        dirs[:] = [d for d in dirs if d not in exclude_subfolders]
        for file in files:
            file_path = os.path.join(root, file)
            if not os.path.isfile(file_path):
                continue
            # Get the file's modification date
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            year_folder = mod_time.strftime('%Y')
            if type == 'year':
                # Organize by year only
                target_dir = os.path.join(root, year_folder)
            elif type == 'year/month':
                # Organize by year/month
                month_folder = mod_time.strftime('%m')
                target_dir = os.path.join(root, year_folder, month_folder)
            elif type == 'year-month':
                 year_month_folder = mod_time.strftime('%Y-%m')
                 target_dir = os.path.join(root, year_month_folder)
            # Create the target directory (and subdirectories) if they don't exist
            os.makedirs(target_dir, exist_ok=True)
            # Move the file to the target directory
            shutil.move(file_path, os.path.join(target_dir, file))
    logger.info(f"INFO: Organization completed. Folder structure per {type} have been created in '{base_dir}'.")


def copy_move_folder(src, dst, ignore_patterns=None, move=False):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    try:
        # Ensure the source folder exists
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source folder does not exist: '{src}'")
        # Create the destination folder if it doesn't exist
        os.makedirs(dst, exist_ok=True)
        # Ignore function
        def ignore_function(dir, files):
            if ignore_patterns:
                # Convert to a list if a single pattern is provided
                patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
                ignored = []
                for pattern in patterns:
                    ignored.extend(fnmatch.filter(files, pattern))
                return set(ignored)
            return set()
        if move:
            # Traverse the directory tree and move files/directories
            for root, dirs, files in os.walk(src, topdown=True):
                # Compute relative path
                rel_path = os.path.relpath(root, src)
                # Destination path
                dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                # Apply ignore function to files and dirs
                ignore = ignore_function(root, files + dirs)
                # Filter dirs in-place to skip ignored directories
                dirs[:] = [d for d in dirs if d not in ignore]
                # Create destination directory
                os.makedirs(dest_path, exist_ok=True)
                # Move files
                for file in files:
                    if file not in ignore:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_path, file)
                        shutil.move(src_file, dst_file)
            logger.info(f"INFO: Folder moved successfully from {src} to {dst}")
        else:
            # Copy the folder contents
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
            logger.info(f"INFO: Folder copied successfully from {src} to {dst}")
    except Exception as e:
        logger.error(f"ERROR: Error {'moving' if move else 'copying'} folder: {e}")


def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str): Path to the input folder containing the albums.
        albums_subfolder (str): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    if isinstance(exclude_subfolder, str):
        exclude_subfolder = [exclude_subfolder]
    albums_path = os.path.join(input_folder, albums_subfolder)
    exclude_subfolder_paths = [os.path.abspath(os.path.join(input_folder, sub)) for sub in (exclude_subfolder or [])]
    for folder in os.listdir(input_folder):
        folder_path = os.path.join(input_folder, folder)
        if (
            os.path.isdir(folder_path)
            and folder != albums_subfolder
            and os.path.abspath(folder_path) not in exclude_subfolder_paths
        ):
            logger.info(f"INFO: Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'..")
            os.makedirs(albums_path, exist_ok=True)
            shutil.move(folder_path, albums_path)


def change_file_extension(root_folder, current_extension, new_extension):
    """
    Changes the extension of all files with a specific extension
    within a folder and its subfolders.

    Args:
        root_folder (str): Path to the root folder to search for files.
        current_extension (str): Current file extension (includes the dot, e.g., ".txt").
        new_extension (str): New file extension (includes the dot, e.g., ".md").

    Returns:
        None
    """
    for path, folders, files in os.walk(root_folder):
        for file in files:
            # Check if the file has the current extension
            if file.endswith(current_extension):
                # Build the full paths of the original and new files
                original_file = os.path.join(path, file)
                new_file = os.path.join(path, file.replace(current_extension, new_extension))
                # Rename the file
                os.rename(original_file, new_file)
                logger.info(f"INFO: Renamed: {original_file} -> {new_file}")


def delete_subfolders(base_folder, folder_name_to_delete):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        base_folder (str): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
    """
    for root, dirs, files in os.walk(base_folder, topdown=False):
        for name in dirs:
            if name == folder_name_to_delete:
                dir_path = os.path.join(root, name)
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"INFO: Deleted directory: {dir_path}")
                except Exception as e:
                    logger.error(f"ERROR: Error deleting {dir_path}: {e}")


def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
    """

    # Count number of sep of input_folder
    sep_input = input_folder.count(os.sep)
    # Convert wildcard patterns to regex patterns for matching
    exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
    for root, dirs, files in os.walk(input_folder, topdown=True):
        # Count number of sep of root folder
        sep_root = int(root.count(os.sep))
        depth = sep_root - sep_input
        # print (f"Depth: {depth}")
        if depth > max_depth:
            # Skip deeper levels
            continue
        # If flatten_root_folder=True, then only need to flatten the root folder and it recursively will flatten all subfolders
        if flatten_root_folder:
            dirs = [os.path.basename(root)]
            root = os.path.dirname(root)
        # Process files in subfolders and move them to the root of the subfolder
        for dir_name in dirs:
            # If 'Albums' folder is found, invoke the script recursively on its subdirectories
            if os.path.basename(dir_name) == "Albums":
                for album_subfolder in dirs:
                    subfolder_path = os.path.join(root, album_subfolder)
                    flatten_subfolders(input_folder=subfolder_path, exclude_subfolders=exclude_subfolders, max_depth=max_depth+1)
                continue
            # Skip processing if the current directory matches any exclude pattern
            if any(pattern.match(os.path.basename(dir_name)) for pattern in exclude_patterns):
                logger.info(f"INFO: Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                continue
            subfolder_path = os.path.join(root, dir_name)
            logger.info(f"INFO: Flattening folder: '{dir_name}'")
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
    for root, dirs, files in os.walk(input_folder, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # Si la carpeta está vacía
                os.rmdir(dir_path)


def logger_setup(log_folder="Logs", log_filename="execution_log", skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """
    os.makedirs(log_folder, exist_ok=True)
    log_level = logging.INFO

    # Clear existing handlers to avoid duplicate logs
    global logger
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()
    if not skip_console:
        # Set up console handler (simple output without timestamps)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if not skip_logfile:
        if detail_log:
            # Set up file handler (detailed output with timestamps)
            # Clase personalizada para formatear solo el manejador detallado
            class CustomFormatter(logging.Formatter):
                def format(self, record):
                    # Crear una copia del mensaje para evitar modificar record.msg globalmente
                    original_msg = record.msg
                    if record.levelname == "INFO":
                        record.msg = record.msg.replace("INFO: ", "")
                    elif record.levelname == "WARNING":
                        record.msg = record.msg.replace("WARNING: ", "")
                    elif record.levelname == "ERROR":
                        record.msg = record.msg.replace("ERROR: ", "")
                    formatted_message = super().format(record)
                    # Restaurar el mensaje original
                    record.msg = original_msg
                    return formatted_message
            log_file = os.path.join(log_folder, log_filename + '.log')
            file_handler_detailed = logging.FileHandler(log_file, encoding="utf-8")
            file_handler_detailed.setLevel(log_level)
            # Formato personalizado para el manejador de ficheros detallado
            detailed_format = CustomFormatter(
                fmt='%(asctime)s [%(levelname)-8s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler_detailed.setFormatter(detailed_format)
            logger.addHandler(file_handler_detailed)

        if plain_log:
            log_file = os.path.join(log_folder, 'plain_' + log_filename + '.txt')
            file_handler_plain = logging.FileHandler(log_file, encoding="utf-8")
            file_handler_plain.setLevel(log_level)

            # Formato estándar para el manejador de ficheros plano
            file_formatter = logging.Formatter('%(message)s')
            file_handler_plain.setFormatter(file_formatter)
            logger.addHandler(file_handler_plain)

    # Set the log level for the root logger
    logger.setLevel(log_level)
    return logger


class WideHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, *args, **kwargs):
        # Configura la anchura máxima del texto de ayuda
        kwargs['width'] = 90  # Ancho total del texto de ayuda
        kwargs['max_help_position'] = 55  # Ajusta la posición de inicio de las descripciones
        super().__init__(*args, **kwargs)
    def _format_action(self, action):
        # Encabezado del argumento
        parts = [self._format_action_invocation(action)]
        # Texto de ayuda, formateado e identado
        if action.help:
            help_text = textwrap.fill(
                action.help,
                width=self._width,
                initial_indent="       ",
                subsequent_indent="       "
            )
            parts.append(f"\n{help_text}")  # Salto de línea adicional
        return "".join(parts)
    def _format_action_invocation(self, action):
        if not action.option_strings:
            # Para argumentos posicionales
            return super()._format_action_invocation(action)
        else:
            # Combina los argumentos cortos y largos con espacio adicional si es necesario
            option_strings = []
            for opt in action.option_strings:
                # Argumento corto, agrega una coma detrás
                if opt.startswith("-") and not opt.startswith("--"):
                    if len(opt) == 3:
                        option_strings.append(f"{opt},")
                    elif len(opt) == 2:
                        option_strings.append(f"{opt}, ")
                else:
                    option_strings.append(f"{opt}")
            # Combina los argumentos cortos y largos, y agrega el parámetro si aplica
            formatted_options = " ".join(option_strings).rstrip(",")
            metavar = f" {action.metavar}" if action.metavar else ""
            return f"{formatted_options}{metavar}"
    def _join_parts(self, part_strings):
        # Asegura que cada argumento quede separado por un salto de línea
        return "\n".join(part for part in part_strings if part)


def FindDuplicates(duplicates_action='List', find_duplicates_in_folders='./'):
    """
    This function searches for duplicate files based on their size and content (hash),
    ignoring file names or modification dates.

    The selection of the "principal" file (the one that won't be moved or removed) follows these rules:
    1. If duplicates are found in multiple input folders:
       - Identify the earliest folder in the provided folder list that contains duplicates.
       - Among the duplicates found in that earliest folder, if there is more than one,
         choose the one with the shortest filename.
    2. If all duplicates are found within the same single input folder:
       - The principal file is determined by the shortest filename among those duplicates.

    Additional points:
    - If find_duplicates_in_folders is a string separated by commas or semicolons,
      it will be converted to a list.
    - If any of the provided input folders do not exist, the function logs an error and returns -1.
    - A "Duplicates" directory and a timestamped subdirectory ("Duplicates_<timestamp>") are created,
      where a "Duplicates_<timestamp>.txt" file is written listing the duplicates.
      This text file will have the same timestamp as the directory.
    - The "Duplicates_<timestamp>.txt" file has a first column "Action" (duplicates_action),
      and subsequent columns named "Duplicate_1", "Duplicate_2", etc., containing full paths
      of the duplicates. "Duplicate_1" corresponds to the principal file.
    - The function returns the number of duplicate sets found.
    - If duplicates_action='move', duplicates except the principal are moved to the
      timestamped directory, preserving the same directory structure based on the input folder
      where each duplicate was found.
    - If duplicates_action='remove', duplicates except the principal are removed.
    - If duplicates_action='list', only the listing is done.
    - If after moving or removing duplicates any empty directories remain in the original folders,
      they are removed.
    - All files found inside any subfolder named '@eaDir' are ignored.
      Además, las subcarpetas '@eaDir' no se consideran para impedir que una carpeta se considere vacía.

    Optimization notes:
    - Files are first grouped by size to avoid unnecessary hashing.
    - Large chunk sizes for hashing are used to handle large files efficiently.
    """

    action = duplicates_action.lower()
    logger.info("")
    logger.info("INFO: Finding Duplicates. This process may take a long time. Be patient and don't close this window...")
    logger.info("")

    logger.info("INFO: Processing input folders.")
    if isinstance(find_duplicates_in_folders, str):
        input_folders_list = [f.strip() for f in re.split('[,;]', find_duplicates_in_folders) if f.strip()]
    else:
        input_folders_list = find_duplicates_in_folders

    if not input_folders_list:
        input_folders_list = ['./']
    logger.info(f"INFO: Folders to search: {input_folders_list}")

    logger.info("INFO: Checking that all provided folders exist.")
    for f in input_folders_list:
        if not os.path.isdir(f):
            logger.error(f"ERROR: The folder '{f}' does not exist.")
            return -1

    input_folders_list = [os.path.abspath(f) for f in input_folders_list]
    logger.info(f"INFO: Absolute paths of folders: {input_folders_list}")

    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())

    logger.info("INFO: Creating duplicates directories.")
    duplicates_root = os.path.join(os.getcwd(), 'Duplicates')
    timestamp_dir = os.path.join(duplicates_root, 'Duplicates_' + timestamp)
    os.makedirs(timestamp_dir, exist_ok=True)
    logger.info(f"INFO: Results will be stored in {timestamp_dir}")

    def calculate_file_hash(path, chunk_size=64*1024):
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    logger.info("INFO: Grouping files by size.")
    size_dict = {}
    for folder in input_folders_list:
        logger.info(f"INFO: Walking through folder {folder}")
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d != '@eaDir']
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(full_path)
                except (PermissionError, OSError):
                    logger.warning(f"WARNING: Skipping inaccessible file {full_path}")
                    continue
                if file_size not in size_dict:
                    size_dict[file_size] = []
                size_dict[file_size].append(full_path)

    logger.info("INFO: Identifying which files need hashing (files with same size) and calculating hash for them.")
    hash_dict = {}
    for file_size, paths in size_dict.items():
        if len(paths) > 1:
            for path in paths:
                try:
                    file_hash = calculate_file_hash(path)
                except (PermissionError, OSError):
                    logger.warning(f"WARNING: Skipping file due to error accessing {path}")
                    continue
                if file_hash not in hash_dict:
                    hash_dict[file_hash] = []
                hash_dict[file_hash].append(path)
    del size_dict

    logger.info("INFO: Identifying duplicates based on hash.")
    duplicates = {h: p for h, p in hash_dict.items() if len(p) > 1}
    del hash_dict

    logger.info(f"INFO: Number of duplicate sets found: {len(duplicates)}")

    duplicates_txt_path = os.path.join(timestamp_dir, f'Duplicates_{timestamp}.txt')

    logger.info("INFO: Determining maximum number of duplicates per set.")
    max_duplicates_count = 0
    for paths in duplicates.values():
        if len(paths) > max_duplicates_count:
            max_duplicates_count = len(paths)

    header_columns = ['Action'] + [f'Duplicate_{i}' for i in range(1, max_duplicates_count+1)]
    logger.info("INFO: Writing header to the duplicates file.")

    with open(duplicates_txt_path, 'w', encoding='utf-8-sig') as duplicates_file:
        duplicates_file.write('\t'.join(header_columns) + '\n')

        duplicates_counter = 0

        logger.info("INFO: Processing each set of duplicates.")
        for file_hash, path_list in duplicates.items():
            logger.info(f"INFO: Processing duplicates for hash {file_hash}.")

            directories_encountered = {}
            for path in path_list:
                belonging_folder = None
                for folder in input_folders_list:
                    if path.startswith(folder):
                        belonging_folder = folder
                        break
                if belonging_folder:
                    if belonging_folder not in directories_encountered:
                        directories_encountered[belonging_folder] = []
                    directories_encountered[belonging_folder].append(path)

            if len(directories_encountered) == 1:
                logger.info("INFO: All duplicates found in a single folder.")
                principal = min(path_list, key=lambda x: len(os.path.basename(x)))
            else:
                logger.info("INFO: Duplicates found in multiple folders.")
                principal = None
                for folder in input_folders_list:
                    if folder in directories_encountered:
                        duplicates_in_earliest = directories_encountered[folder]
                        principal = min(duplicates_in_earliest, key=lambda x: len(os.path.basename(x)))
                        break

            other_files = [p for p in path_list if p != principal]
            sorted_for_output = [principal] + sorted(other_files)
            logger.info(f"INFO: Duplicates set: '{sorted_for_output}'")

            logger.info(f"INFO: Principal file determined: {principal}")
            duplicates_for_this_set = [p for p in path_list if p != principal]

            row = [duplicates_action] + sorted_for_output
            if len(sorted_for_output) < max_duplicates_count:
                row += [''] * (max_duplicates_count - len(sorted_for_output))
            duplicates_file.write('\t'.join(row) + '\n')

            if action == 'move':
                logger.info("INFO: Moving duplicates except principal.")
                for duplicate_path in duplicates_for_this_set:
                    relative_path = None
                    source_root = None
                    for folder in input_folders_list:
                        if duplicate_path.startswith(folder):
                            source_root = folder
                            relative_path = os.path.relpath(duplicate_path, folder)
                            break
                    if relative_path is None:
                        source_root = input_folders_list[0]
                        relative_path = os.path.relpath(duplicate_path, source_root)

                    top_level_folder = os.path.basename(source_root)
                    final_relative_path = os.path.join(top_level_folder, relative_path)
                    new_path = os.path.join(timestamp_dir, final_relative_path)
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    shutil.move(duplicate_path, new_path)

            elif action == 'remove':
                logger.info("INFO: Removing duplicates except principal.")
                for duplicate_path in duplicates_for_this_set:
                    try:
                        os.remove(duplicate_path)
                    except OSError:
                        logger.warning(f"WARNING: Could not remove file {duplicate_path}")

            else:
                logger.info("INFO: Action is 'list', no move/remove performed.")

            duplicates_counter += 1

    def remove_empty_dirs(root_dir):
        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
            # Filtra las subcarpetas '@eaDir' para no tenerlas en cuenta
            filtered_dirnames = [d for d in dirnames if d != '@eaDir']
            if not filtered_dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                    logger.info(f"INFO: Removed empty directory {dirpath}")
                except OSError:
                    pass

    if action in ('move', 'remove'):
        logger.info("INFO: Removing empty directories in original folders.")
        for folder in input_folders_list:
            remove_empty_dirs(folder)

    logger.info(f"INFO: Finished processing. Total duplicate sets: {duplicates_counter}")
    return duplicates_counter


