import os, sys
import platform
import subprocess
import shutil
import zipfile
import logging
import fnmatch
import re

######################
# FUNCIONES AUXILIARES
######################

def resource_path(relative_path):
    """Obtener la ruta absoluta al recurso, manejando el entorno de PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(""), relative_path)

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

def sync_mp4_timestamps_with_images(input_folder):
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
                        print(f"Atributos de fecha y hora sincronizados para: {os.path.relpath(mp4_file_path,input_folder)} usando {os.path.relpath(image_file_path,input_folder)}")
                        image_file_found = True
                        break  # Salir después de encontrar el primer archivo de imagen disponible

                if not image_file_found:
                    print(f"No se encontró archivo de imagen para sincronizar con: {os.path.relpath(mp4_file_path,input_folder)}")

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

def fix_metadata_with_gpth_tool(input_folder, output_folder, flatten_albums=True, flatten_no_albums=False, move_takeout_folder=False, ignore_takeout_structure=False):
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
        "--no-interactive", "--skip-extras", "--albums", "duplicate-copy"
    ]

    # Append --copy/--no-copy to the gpth tool call based on the values of move_takeout_folder
    if move_takeout_folder:
        gpth_command.append("--no-copy")
    else:
        gpth_command.append("--copy")

    # Append --no-divide-to-dates or --divide-to-dates to the gpth tool call based on the values of flatten_albums and flatten_no_albums
    if flatten_albums and flatten_no_albums:
        gpth_command.append("--no-divide-to-dates")
    else:
        gpth_command.append("--divide-to-dates")

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
        script_name = "gpth"
    elif current_os == "Darwin":
        script_name = "gpth"
    elif current_os == "Windows":
        script_name = "gpth.exe"
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

# class WideHelpFormatter(argparse.RawDescriptionHelpFormatter):
#     def __init__(self, *args, **kwargs):
#         # Configura la posición inicial de las descripciones (más ancha)
#         kwargs['max_help_position'] = 55  # Ajusta la posición de inicio de las descripciones
#         kwargs['width'] = 80  # Ancho total del texto de ayuda
#         super().__init__(*args, **kwargs)
#     def _format_action_invocation(self, action):
#         if not action.option_strings:
#             # Para argumentos posicionales
#             return super()._format_action_invocation(action)
#         else:
#             # Combina los argumentos cortos y largos con espacio adicional si es necesario
#             option_strings = []
#             for opt in action.option_strings:
#                 # Argumento corto, agrega una coma detrás
#                 if opt.startswith("-") and not opt.startswith("--"):
#                     if len(opt) == 3:
#                         option_strings.append(f"{opt},")
#                     elif len(opt) == 2:
#                         option_strings.append(f"{opt}, ")
#                 else:
#                     option_strings.append(f"{opt}")
#
#             # Combina los argumentos cortos y largos, y agrega el parámetro si aplica
#             formatted_options = " ".join(option_strings).rstrip(",")
#             metavar = f" {action.metavar}" if action.metavar else ""
#             return f"{formatted_options}{metavar}"


import argparse
import textwrap
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
