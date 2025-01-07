import os, sys
import shutil
import argparse
import subprocess
import zipfile
import logging
import fnmatch
import re
import platform
from datetime import datetime, timedelta

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v1.2.0"
SCRIPT_DATE         = "2024-11-27"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, fix metadata, organize per year/month folder, and separate Albums).
(c) by Jaime Tur (@jaimetur)
"""

# Detect the operating system
current_os = platform.system()

# Determine the script name based on the OS
if current_os == "Linux":
    print ("Script running on Linux system")
elif current_os == "Darwin":
    print ("Script running on MacOS system")
elif current_os == "Windows":
    print ("Script running on Windows system")
else:
    print(f"Unsupported operating system: {current_os}")


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

def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder="ALL_PHOTOS"):
    """Moves album folders to a specific subfolder, excluding the specified subfolder."""
    albums_path = os.path.join(input_folder, albums_subfolder)
    os.makedirs(albums_path, exist_ok=True)
    exclude_subfolder_path = os.path.abspath(os.path.join(input_folder, exclude_subfolder))
    for folder in os.listdir(input_folder):
        folder_path = os.path.join(input_folder, folder)
        if os.path.isdir(folder_path) and folder != albums_subfolder and os.path.abspath(folder_path) != exclude_subfolder_path:
            shutil.move(folder_path, albums_path)

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
                logger.info(f"INFO: Folder: '{dir_name}' not flattened due to exclude patterns detection")
                continue
            subfolder_path = os.path.join(root, dir_name)
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
            logger.info(f"INFO: Folder: '{dir_name}' flattened")

    for root, dirs, files in os.walk(input_folder, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # Si la carpeta está vacía
                os.rmdir(dir_path)

def fix_metadata_with_gpth_tool(input_folder, output_folder, flatten_albums, flatten_no_albums):
    """Runs the GPTH Tool command to process photos."""
    logger.info(f"INFO: Running GPTH Tool from '{input_folder}' to '{output_folder}'...")

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
        "--no-interactive", "--skip-extras", "--copy", "--albums", "duplicate-copy"
    ]
    if flatten_albums and flatten_no_albums:
        gpth_command.append("--no-divide-to-dates")
    else:
        gpth_command.append("--divide-to-dates")
    try:
        # print (" ".join(gpth_command))
        result = subprocess.run(gpth_command, check=True)
        logger.info(f"INFO: GPTH Tool finxing completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"ERROR: GPTH Tool fixing failed:\n{e.stderr}")

def fix_metadata_with_exif_tool(output_folder):
    """Runs the EXIF Tool command to fix photo metadata."""
    logger.info(f"INFO: Fixing EXIF metadata in '{output_folder}'...")
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

def copy_folder(src, dst):
    """
    Copia una carpeta completa, incluyendo subcarpetas y archivos, a otra ubicación.

    :param src: Ruta de la carpeta de origen.
    :param dst: Ruta de la carpeta de destino.
    :return: None
    """
    try:
        # Asegurarse de que la carpeta de origen existe
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source folder does not exists: '{src}'")

        # Crear la carpeta de destino si no existe
        os.makedirs(dst, exist_ok=True)

        # Copiar el contenido de la carpeta
        shutil.copytree(src, dst, dirs_exist_ok=True)
        logger.info(f"INFO: Folder copied succesfully from {src} to {dst}")
    except Exception as e:
        logger.error(f"ERROR: Error copying folder: {e}")


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
        # Configura la posición inicial de las descripciones (más ancha)
        kwargs['max_help_position'] = 55  # Ajusta la posición de inicio de las descripciones
        kwargs['width'] = 180  # Ancho total del texto de ayuda
        super().__init__(*args, **kwargs)
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

if __name__ == "__main__":
    def parse_arguments():
        parser = argparse.ArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=WideHelpFormatter,  # Aplica el formatter
        )
        parser.add_argument("-z",  "--zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
        parser.add_argument("-t",  "--takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to unzip input files. Default: 'Takeout'")
        parser.add_argument("-s",  "--suffix", metavar="<SUFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
        parser.add_argument("-sl", "--skip-log", action="store_true", help="Skip saving output messages to log file.")
        #parser.add_argument("-su", "--skip-unzip", action="store_true", help="Skip unzipping files.")
        parser.add_argument("-sg", "--skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool.")
        parser.add_argument("-se", "--skip-exif-tool", action="store_true", help="Skip processing files with EXIF Tool.")
        parser.add_argument("-sm", "--skip-move-albums", action="store_true", help="Skip moving albums to Albums folder.")
        parser.add_argument("-fa", "--flatten-albums", action="store_true", help="Flatten photos/videos within each album folder.")
        parser.add_argument("-fn", "--flatten-no-albums", action="store_true", help="Flatten photos/videos within ALL_PHOTOS folder.")
        args = parser.parse_args()
        if not args.zip_folder=="": args.zip_folder = args.zip_folder.rstrip('/\\')
        args.takeout_folder = args.takeout_folder.rstrip('/\\')
        args.suffix = args.suffix.lstrip('_')
        return args

def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')
    args = parse_arguments()

    # Create timestamp, start_time and define output_folder
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_time = datetime.now()
    output_folder = f"{args.takeout_folder}_{args.suffix}_{timestamp}"

    # Set a global variable for logger and Set up logger based on the skip-log argument
    global logger
    log_filename=f"execution_log_{timestamp}"
    log_folder="Logs"
    log_folder_filename = os.path.join(log_folder,log_filename+'.log')
    logger = logger_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=args.skip_log, plain_log=False)

    logger.info(SCRIPT_DESCRIPTION)
    logger.info("")
    logger.info("====================")
    logger.info("STARTING PROCESS...")
    logger.info("====================")
    logger.info("")

    # Mensajes informativos
    if not args.zip_folder=="": logger.info(f"INFO: Using Zip folder     : '{args.zip_folder}'")
    logger.info(f"INFO: Using Takeout folder : '{args.takeout_folder}'")
    logger.info(f"INFO: Using Suffix         : '{args.suffix}'")
    logger.info(f"INFO: Using Output folder  : '{output_folder}'")
    if not args.skip_log:
        logger.info(f"INFO: Execution Log file   : '{log_folder_filename}'")

    logger.info(f"")
    if args.zip_folder=="":
        logger.warning(f"WARNING: No argument '-z or --zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
    if args.skip_gpth_tool:
        logger.warning(f"WARNING: Flag detected '-sg, --skip-gpth-toot'. Skipping Processing photos with GPTH Tool...")
    if args.skip_exif_tool:
        logger.warning(f"WARNING: Flag detected '-se, --skip-exif-tool'. Skipping Processing photos with EXIF Tool...")
    if args.skip_move_albums:
        logger.warning(f"WARNING: Flag detected '-sm, --skip-move-albums'. Skipping Moving Albums to Albums folder...")
    if args.flatten_albums:
        logger.warning(f"WARNING: Flag detected '-fa, --flatten-albums'. All files within each album folder will be flattened (without year/month folder structure)...")
    if args.flatten_no_albums:
        logger.warning(f"WARNING: Flag detected '-fn, --flatten-no-albums'. All files within ALL_PHOTOS folder will be flattened on ALL_PHOTOS folder (without year/month folder structure)...")
    if args.skip_log:
        logger.warning(f"WARNING: Flag detected '-sl, --skip-log'. Skipping saving output into log file...")

    # Step 1: Unzip files
    logger.info("")
    logger.info("==============================")
    logger.info("1. UNPACKING TAKEOUT FOLDER...")
    logger.info("==============================")
    logger.info("")
    if not args.zip_folder=="":
        step_start_time = datetime.now()
        unpack_zips(args.zip_folder, args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 1 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Unzipping skipped (no argument '-z or --zip-folder <ZIP_FOLDER>' given).")

    # Step 2: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    logger.info("")
    logger.info("===========================================")
    logger.info("2. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    logger.info("===========================================")
    logger.info("")
    if not args.skip_gpth_tool:
        step_start_time = datetime.now()
        fix_metadata_with_gpth_tool(
            input_folder=args.takeout_folder,
            output_folder=output_folder,
            flatten_albums=args.flatten_albums,
            flatten_no_albums=args.flatten_no_albums
        )
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 2 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Metadata fixing with GPTH tool skipped ('-sg, --skip-gpth-tool' flag detected).")
        logger.info("")
        logger.info("=====================================")
        logger.info("2b. COPYING FILES TO OUTPUT FOLDER...")
        logger.info("=====================================")
        logger.info("")
        logger.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        copy_folder (args.takeout_folder, output_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 2 completed in {formatted_duration}.")

    # Step 3: Flatten Folders
    logger.info("")
    logger.info("========================")
    logger.info("3. FLATTENING FOLDERS...")
    logger.info("========================")
    logger.info("")
    if args.flatten_albums or args.flatten_no_albums:
        step_start_time = datetime.now()
        # Only flatten albums
        if args.flatten_albums and not args.flatten_no_albums:
            flatten_subfolders(input_folder=output_folder, exclude_subfolders=["ALL_PHOTOS"], max_depth=0, flatten_root_folder=False)
        # Only flatten no albums
        elif not args.flatten_albums and args.flatten_no_albums:
            flatten_subfolders(input_folder=os.path.join(output_folder,'ALL_PHOTOS'), max_depth=1, flatten_root_folder=True)
        # If flatten both but gpth tool is not skipped, then the output of gpth tool is already flattened
        elif args.flatten_albums and args.flatten_no_albums and args.skip_gpth_tool:
            flatten_subfolders(input_folder=output_folder, exclude_subfolders=["ALL_PHOTOS"], max_depth=0, flatten_root_folder=False)
            flatten_subfolders(input_folder=os.path.joint(output_folder,'ALL_PHOTOS'), max_depth=1, flatten_root_folder=True)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 3 completed in {formatted_duration}.")
    # No flatten anything
    else:
        logger.warning("WARNING: Flattening skipped. No flatten arguments ('-fa, --flatten-albums' / '-fn, --flatten-no-albums') found.")

    # Step 4: Move albums
    logger.info("")
    logger.info("==========================")
    logger.info("4. MOVING ALBUMS FOLDER...")
    logger.info("==========================")
    logger.info("")
    if not args.skip_move_albums:
        step_start_time = datetime.now()
        move_albums(output_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 4 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --skip-move-albums' flag detected).")

    # Step 5: Fix metadata with EXIF Tool
    logger.info("")
    logger.info("===========================================")
    logger.info("5. FIXING PHOTOS METADATA WITH EXIF TOOL...")
    logger.info("===========================================")
    logger.info("")
    if not args.skip_exif_tool:
        step_start_time = datetime.now()
        fix_metadata_with_exif_tool(output_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 5 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Metadata fixing with EXIF tool skipped ('-se, --skip-exif-tool' flag detected).")


    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time-start_time).seconds))
    logger.info("")
    logger.info("==================================================")
    logger.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    logger.info("==================================================")
    logger.info("")
    logger.info("==================================================")
    logger.info("                  FINAL SUMMARY:                  ")
    logger.info("==================================================")
    logger.info(f"Total files in Takeout folder           : {count_files_in_folder(args.takeout_folder)}")
    logger.info(f"Total files processed by GPTH/EXIF TooL : {count_files_in_folder(output_folder)}")
    albums_found = 0
    if not args.skip_move_albums:
        album_folder = os.path.join(output_folder, 'Albums')
        if os.path.isdir(album_folder):
            albums_found = len(os.listdir(album_folder))
    else:
        if os.path.isdir(output_folder):
            albums_found = len(os.listdir(output_folder))-1
    logger.info(f"Total Albums folders found              : {albums_found}")

    logger.info("")
    logger.info(f"Total time elapsed                      : {formatted_duration}")
    logger.info("==================================================")
    logger.info("")

if __name__ == "__main__":
    main()
