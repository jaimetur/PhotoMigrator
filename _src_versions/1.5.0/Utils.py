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
import csv
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

def fix_metadata_with_gpth_tool(input_folder, output_folder, skip_extras=False, symbolic_albums=False, move_takeout_folder=False, ignore_takeout_structure=False):
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
        "--no-interactive"
    ]
    # By default force --no-divide-to-dates and the script will create date structure if needed
    gpth_command.append("--no-divide-to-dates")

    # Append --albums shortcut / duplicate-copy based on value of flag -sa, --symbolic-albums
    gpth_command.append("--albums")
    if symbolic_albums:
        logger.info(f"INFO: Symbolic Albums will be created with links to the original files...")
        gpth_command.append("shortcut")
    else:
        gpth_command.append("duplicate-copy")

    # Append --skip-extras to the gpth tool call based on the value of flag -se, --skip-extras
    if skip_extras:
        gpth_command.append("--skip-extras")

    # Append --copy/--no-copy to the gpth tool call based on the values of move_takeout_folder
    if move_takeout_folder:
        gpth_command.append("--no-copy")
    else:
        gpth_command.append("--copy")

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
                        pass
                        # logger.info(f"INFO: Skipped: {new_json_path} already exists")


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


def log_setup(log_folder="Logs", log_filename="execution_log", skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
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


def fix_symlinks_broken(base_dir):
    """
    Searches and fixes broken symbolic links in a directory and its subdirectories.
    Optimized to handle very large numbers of files by indexing files beforehand.

    :param base_dir: Path (relative or absolute) to the main directory where the links should be searched and fixed.
    :return: A tuple containing the number of corrected symlinks and the number of symlinks that could not be corrected.
    """

    # Validate the directory existence
    if not os.path.isdir(base_dir):
        logger.error(f"ERROR: The directory '{base_dir}' does not exist or is not valid.")
        return 0, 0

    # Paso 1: Indexar todos los archivos reales no simbólicos
    file_index = build_file_index(base_dir)

    corrected_count = 0
    failed_count = 0

    # Paso 2: Buscar enlaces simbólicos rotos y corregirlos usando el índice
    for root, _, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.islink(file_path) and not os.path.exists(file_path):
                # Es un enlace simbólico roto
                target = os.readlink(file_path)
                # logger.info(f"INFO: Broken link found: {file_path} -> {target}")
                target_name = os.path.basename(target)

                fixed_path = find_real_file(file_index, target_name)
                if fixed_path:
                    # Crear enlace simbólico correcto
                    relative_path = os.path.relpath(fixed_path, start=os.path.dirname(file_path))
                    logger.info(f"INFO: Fixing link: {file_path} -> {relative_path}")
                    os.unlink(file_path)
                    os.symlink(relative_path, file_path)
                    corrected_count += 1
                else:
                    logger.warning(f"WARNING: Could not find the file for {file_path} within {base_dir}")
                    failed_count += 1

    return corrected_count, failed_count


def build_file_index(directory):
    """
    Index all non-symbolic files in the directory and its subdirectories by their filename.
    Returns a dictionary where keys are filenames and values are lists of their full paths.
    """
    file_index = {}
    for root, _, files in os.walk(directory):
        for fname in files:
            full_path = os.path.join(root, fname)
            # Solo indexar archivos reales (no enlaces simbólicos)
            if os.path.isfile(full_path) and not os.path.islink(full_path):
                # Agregar la ruta al índice
                if fname not in file_index:
                    file_index[fname] = []
                file_index[fname].append(full_path)
    return file_index


def find_real_file(file_index, target_name):
    """
    Given a pre-built file index (dict: filename -> list of paths),
    return the first available real file path for the given target_name.
    If multiple matches exist, return the first found.
    If none is found, return None.
    """
    if target_name in file_index and file_index[target_name]:
        return file_index[target_name][0]
    return None

def find_duplicates(duplicates_action='list', find_duplicates_in_folders='./', deprioritize_folders_patterns=None, timestamp=None):
    """
    This function searches for duplicate files based on their size and content (hash),
    ignoring file names or modification dates.

    Selection rules for the principal file:
    1. If duplicates are in multiple input folders, pick from the earliest folder in the provided list.
       If multiple files in that folder, choose shortest filename.
    2. If all duplicates are in one folder, choose shortest filename among them.
    3. With deprioritized folders, any folder matching given patterns is less prioritized.
       Among multiple patterns, the last pattern is highest priority. If all are deprioritized,
       pick from the one with highest priority pattern. If tie remains, apply original logic.

    Additional notes:
    - If find_duplicates_in_folders is a string separated by commas/semicolons, convert to a list.
    - If any folder doesn't exist, log error and return -1.
    - Create "Duplicates" and "Duplicates_<timestamp>" directories, store "Duplicates_<timestamp>.csv".
    - CSV format: Num_Duplicates, Principal, Duplicate, Action, [Destination if move].
    - Return number of duplicates (excluding principals).
    - If move/remove, perform actions and then remove empty dirs.
    - Ignore files in '@eaDir' subfolders.
    - Patterns are case-insensitive and checked against full paths and each subpart.

    Optimizations:
    - Cache folder priority results to avoid recalculations.
    - Skip symbolic links and inaccessible files early.
    - Only hash files with same size more than once.
    - Maintain a memory of chosen principal folder in ties to keep consistency across sets.
    - Use efficient lookups and caches to reduce overhead in large directories.
    """
    # Auxiliary Functions:
    def calculate_file_hash(path, chunk_size=64*1024):
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def folder_pattern_priority(folder):
        # Return (is_deprioritized, priority)
        # Lower index = less priority pattern, higher index = more priority pattern
        # The code uses max(...) to pick final pattern => last pattern in the list is highest priority
        folder_lower = folder.lower()
        if folder_lower in cache_folders_priority:
            return cache_folders_priority[folder_lower]
        matched_priorities = []
        for i, pattern_lower in enumerate(deprioritize_folders_patterns):
            if fnmatch.fnmatch(folder_lower, pattern_lower):
                matched_priorities.append(i)
                break
        if not matched_priorities:
            result = (False, None)
        else:
            # max(...) means last pattern in the list is the highest priority
            result = (True, max(matched_priorities))
        cache_folders_priority[folder_lower] = result
        return result

    def remove_empty_dirs(root_dir):
        for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
            filtered_dirnames = [d for d in dirnames if d != '@eaDir']
            if not filtered_dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                    logger.info(f"INFO: Removed empty directory {dirpath}")
                except OSError:
                    pass

    # If deprioritize_folders is None, create an empty list.
    if deprioritize_folders_patterns is None:
        deprioritize_folders_patterns = []

    # Check if find_duplicates_in_folders and deprioritize_folders are strings, if so, converts them to list.
    if isinstance(find_duplicates_in_folders, (str, bytes)):
        find_duplicates_in_folders = [find_duplicates_in_folders]
    if isinstance(deprioritize_folders_patterns, (str, bytes)):
        deprioritize_folders_patterns = [deprioritize_folders_patterns]

    action = duplicates_action.lower()
    logger.info("")
    logger.info("INFO: Finding Duplicates. This may take a long time, be patient...")
    logger.info("")

    logger.info(f"INFO: Deprioritize Folders Patterns: {deprioritize_folders_patterns}")
    deprioritize_folders_patterns = [cadena.lower() for cadena in deprioritize_folders_patterns]

    logger.info(f"INFO: Processing folders.")
    if isinstance(find_duplicates_in_folders, str):
        input_folders_list = [f.strip() for f in re.split('[,;]', find_duplicates_in_folders) if f.strip()]
    else:
        input_folders_list = find_duplicates_in_folders

    if not input_folders_list:
        input_folders_list = ['./']
    logger.info(f"INFO: Folders: {input_folders_list}")

    logger.info("INFO: Checking folder existence.")
    for folder in input_folders_list:
        if not os.path.isdir(folder):
            logger.error(f"ERROR: The folder '{folder}' does not exist.")
            return -1

    input_folders_list = [os.path.abspath(f) for f in input_folders_list]
    logger.info(f"INFO: Absolute folder paths: {input_folders_list}")

    if timestamp is None:
        timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())

    logger.info("INFO: Creating duplicates directories.")
    duplicates_root = os.path.join(os.getcwd(), 'Duplicates')
    timestamp_dir = os.path.join(duplicates_root, 'Duplicates_' + timestamp)
    os.makedirs(timestamp_dir, exist_ok=True)
    logger.info(f"INFO: Results in {timestamp_dir}")

    # Cache for folder priorities to avoid repeated calculations
    cache_folders_priority = {}

    logger.info("INFO: Grouping files by size.")
    size_dict = {}
    # Collect files by size, skip links and inaccessible early
    for folder in input_folders_list:
        logger.info(f"INFO: Walking folder {folder}")
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d != '@eaDir']
            for file in files:
                full_path = os.path.join(root, file)
                if os.path.islink(full_path):
                    continue
                try:
                    file_size = os.path.getsize(full_path)
                except (PermissionError, OSError):
                    logger.warning(f"WARNING: Skipping inaccessible file {full_path}")
                    continue
                size_dict.setdefault(file_size, []).append(full_path)

    logger.info("INFO: Hashing files with same size.")
    hash_dict = {}
    for file_size, paths in size_dict.items():
        if len(paths) > 1:
            for path in paths:
                try:
                    file_hash = calculate_file_hash(path)
                except (PermissionError, OSError):
                    logger.warning(f"WARNING: Skipping file due to error {path}")
                    continue
                hash_dict.setdefault(file_hash,[]).append(path)

    del size_dict

    logger.info("INFO: Identifying duplicates by hash.")
    duplicates = {hash: path for hash, path in hash_dict.items() if len(path) > 1}
    del hash_dict
    logger.info(f"INFO: {len(duplicates)} duplicate sets found")

    duplicates_csv_path = os.path.join(timestamp_dir, f'Duplicates_{timestamp}.csv')
    header = ['Num_Duplicates','Principal','Duplicate','Action','Reasson for Principal']
    if action == 'move':
        header.append('Destination')

    logger.info("INFO: Writing CSV header.")
    with open(duplicates_csv_path, 'w', encoding='utf-8-sig', newline='') as duplicates_file:
        writer = csv.writer(duplicates_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(header)

        duplicates_counter = 0
        logger.info("INFO: Processing each duplicates set.")

        # Memory to keep consistent principal folder selection in tie scenarios
        cache_principal_folders = {}

        for file_hash, path_list in duplicates.items():
            directories_encountered = {}
            for path in path_list:
                belonging_folder = None
                for folder in input_folders_list:
                    if path.startswith(folder):
                        belonging_folder = folder
                        break
                if belonging_folder:
                    directories_encountered.setdefault(belonging_folder, []).append(path)

            folders_datainfo_dic = []
            for belonging_folder, paths_in_folder in directories_encountered.items():
                for path in paths_in_folder:
                    base_dir = os.path.dirname(path)
                    file_name = os.path.basename(path)
                    is_deprioritized, priority = folder_pattern_priority(base_dir)
                    folders_datainfo_dic.append((base_dir, is_deprioritized, priority, file_name))

            # Distinguish non-deprioritized and deprioritized
            folders_non_deprioritized = [folder_data for folder_data in folders_datainfo_dic if not folder_data[1]]
            folders_deprioritized = [folder_data for folder_data in folders_datainfo_dic if folder_data[1]]

            # Create a tie scenario key (folder path + deprio state + priority)
            tie_scenario = tuple(sorted((folder_data[0], folder_data[1], folder_data[2]) for folder_data in folders_datainfo_dic))

            reasson_for_principal = ""
            # If there is no any foledr no deprioritized
            if folders_non_deprioritized:
                reasson_for_principal += " / Non-Deprioritized Folder"
                if len(folders_non_deprioritized)>1:
                    reasson_for_principal += "s / Using Input_Folder_List order to chose Principal"
                    # If there is more than one folder with max_prio, then choose the folder contained in the first input_folder_list
                    folders_non_deprioritized.sort(
                        key=lambda x: next(
                            (index for index, prefix in enumerate(input_folders_list) if x[0].startswith(prefix)),
                            len(input_folders_list)  # Valor predeterminado si no coincide con ningún prefijo
                        )
                    )

                if tie_scenario in cache_principal_folders:
                    chosen_folder_path = cache_principal_folders[tie_scenario]
                    chosen_folder_data = None
                    for folder_data in folders_non_deprioritized:
                        if folder_data[0] == chosen_folder_path:
                            chosen_folder_data = folder_data
                            chosen_folder = chosen_folder_data[0]
                            reasson_for_principal += " / Folder in cache"
                            break
                    if chosen_folder_data is None:
                        chosen_folder_data = folders_non_deprioritized[0]
                        chosen_folder = chosen_folder_data[0]
                        reasson_for_principal += " / First Folder non-deprioritized"
                        cache_principal_folders[tie_scenario] = chosen_folder
                else:
                    # No cache, pick first
                    reasson_for_principal += " / First Folder non-deprioritized"
                    chosen_folder_data = folders_non_deprioritized[0]
                    chosen_folder = chosen_folder_data[0]
                    cache_principal_folders[tie_scenario] = chosen_folder

                # If there is more than one duplicates files within the chosen folder, then choose the shortest filename
                chosen_folder_duplicates_files = [folder_data[3] for folder_data in folders_non_deprioritized if folder_data[0]==chosen_folder]
                chosen_folder_duplicates_files_list = chosen_folder_duplicates_files if isinstance(chosen_folder_duplicates_files, list) else [chosen_folder_duplicates_files]
                if len(chosen_folder_duplicates_files_list)>1:
                    principal = min(chosen_folder_duplicates_files_list, key=lambda x: len(os.path.basename(x)))
                    reasson_for_principal += " / Shortest Name"
                else:
                    principal = chosen_folder_duplicates_files_list[0]
                principal = os.path.join(chosen_folder, principal)

            # If all folders are deprioritized folder
            else:
                if not folders_deprioritized:
                    continue
                reasson_for_principal += " / All Folderes are deprioritized"
                max_priority = max(folder_data[2] for folder_data in folders_deprioritized)
                folders_with_max_priority = [folder_data for folder_data in folders_deprioritized if folder_data[2] == max_priority]
                if len(folders_with_max_priority)>1:
                    reasson_for_principal += " / Using Input_Folder_List order to chose Principal"
                    # If there is more than one folder with max_prio, then choose the folder contained in the first input_folder_list
                    folders_with_max_priority.sort(
                        key=lambda x: next(
                            (index for index, prefix in enumerate(input_folders_list) if x[0].startswith(prefix)),
                            len(input_folders_list)  # Valor predeterminado si no coincide con ningún prefijo
                        )
                    )
                if tie_scenario in cache_principal_folders:
                    chosen_folder_path = cache_principal_folders[tie_scenario]
                    chosen_folder_data = None
                    for folder_data in folders_with_max_priority:
                        if folder_data[0] == chosen_folder_path:
                            chosen_folder_data = folder_data
                            chosen_folder = chosen_folder_data[0]
                            reasson_for_principal += " / Deprioritized Folder in cache"
                            break
                    if chosen_folder_data is None:
                        chosen_folder_data = folders_with_max_priority[0]
                        chosen_folder = chosen_folder_data[0]
                        reasson_for_principal += f" / First Deprioritized Folder with Higher Priority ({chosen_folder_data[2]})"
                        cache_principal_folders[tie_scenario] = chosen_folder_data[0]
                else:
                    chosen_folder_data = folders_with_max_priority[0]
                    reasson_for_principal += f" / First Deprioritized Folder with Higher Priority ({chosen_folder_data[2]})"
                    chosen_folder = chosen_folder_data[0]
                    cache_principal_folders[tie_scenario] = chosen_folder

                # If there is more than one duplicates files within the chosen folder, then choose the shortest filename
                chosen_folder_duplicates_files = [folder_data[3] for folder_data in folders_with_max_priority  if folder_data[0]==chosen_folder]
                chosen_folder_duplicates_files_list = chosen_folder_duplicates_files if isinstance(chosen_folder_duplicates_files, list) else [chosen_folder_duplicates_files]
                if len(chosen_folder_duplicates_files_list)>1:
                    principal = min(chosen_folder_duplicates_files_list, key=lambda x: len(os.path.basename(x)))
                    reasson_for_principal += " / Shortest Name"
                else:
                    principal = chosen_folder_duplicates_files_list[0]
                principal = os.path.join(chosen_folder, principal)


            duplicates_for_this_set = [p for p in path_list if p != principal]
            num_duplicates = len(duplicates_for_this_set)
            display_action = 'keep' if action == 'list' else action

            if reasson_for_principal.startswith(' / '):
                reasson_for_principal = reasson_for_principal [3:]

            for duplicate_path in sorted(duplicates_for_this_set):
                row = [num_duplicates, principal, duplicate_path, display_action, reasson_for_principal]
                if action == 'move':
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
                    destination_path = os.path.join(timestamp_dir, final_relative_path)
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    shutil.move(duplicate_path, destination_path)
                    row.append(destination_path)
                elif action == 'remove':
                    try:
                        os.remove(duplicate_path)
                    except OSError:
                        logger.warning(f"WARNING: Could not remove file {duplicate_path}")

                writer.writerow(row)
                duplicates_counter += 1

    if action in ('move', 'remove'):
        logger.info("INFO: Removing empty directories in original folders.")
        for folder in input_folders_list:
            remove_empty_dirs(folder)

    logger.info(f"INFO: Finished processing. Total duplicates (excluding principals): {duplicates_counter}")
    return duplicates_counter