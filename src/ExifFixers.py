import os,sys
import platform
import subprocess
import logging
import select
import threading
import queue
import re
import time

from CustomLogger import set_log_level
from GlobalVariables import LOGGER

def resource_path(relative_path, log_level=logging.INFO):
    """Obtener la ruta absoluta al recurso, manejando el entorno de PyInstaller."""
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)


def run_command(command, logger, capture_output=False, capture_errors=True):
    """
    Ejecuta un comando en un subproceso y maneja la salida en tiempo real si capture_output=True.
    Evita registrar múltiples líneas de barras de progreso en el log.
    """
    if capture_output or capture_errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
            stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace"
        )
        if capture_output:
            for line in process.stdout:
                logger.info(f"INFO    : {line.strip()}")
        if capture_errors:
            for line in process.stderr:
                logger.error(f"ERROR   : {line.strip()}")
        process.wait()  # Esperar a que el proceso termine
        return process.returncode
    else:
        # Ejecutar sin capturar la salida (dejar que se muestre en consola)
        result = subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace")
        return result.returncode


def fix_metadata_with_gpth_tool(input_folder, output_folder, capture_output=False, capture_errors=True, skip_extras=False, symbolic_albums=False, move_takeout_folder=False, ignore_takeout_structure=False, log_level=logging.INFO):
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        """Runs the GPTH Tool command to process photos."""
        input_folder = os.path.abspath(input_folder)
        output_folder = os.path.abspath(output_folder)
        LOGGER.info(f"INFO    : Running GPTH Tool...")
        LOGGER.info(f"INFO    : Input Folder: '{input_folder}'")
        LOGGER.info(f"INFO    : Output Folder: '{output_folder}'")

        # Detect the operating system
        current_os = platform.system()

        # Determine the Tool name based on the OS
        tool_name = ""
        if current_os == "Linux":
            tool_name = "gpth_linux.bin"
        elif current_os == "Darwin":
            tool_name = "gpth_macos.bin"
        elif current_os == "Windows":
            tool_name = "gpth_windows.exe"

        # Usar resource_path para acceder a archivos o directorios:
        gpth_tool_path = resource_path(os.path.join("gpth_tool", tool_name))

        gpth_command = [gpth_tool_path, "--input", input_folder, "--output", output_folder, "--no-interactive"]

        # If ignore_takeout_structure is True, we append --fix input_folder to the gpth tool call
        if ignore_takeout_structure:
            gpth_command.append("--fix")
            gpth_command.append(input_folder)

        # By default force --no-divide-to-dates and the Tool will create date structure if needed
        gpth_command.append("--no-divide-to-dates")

        # Append --albums shortcut / duplicate-copy based on value of flag -sa, --symbolic-albums
        gpth_command.append("--albums")
        if symbolic_albums:
            LOGGER.info(f"INFO    : Symbolic Albums will be created with links to the original files...")
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

        try:
            command = ' '.join(gpth_command)
            LOGGER.debug(f"DEBUG   : Command: {command}")
            result = run_command(gpth_command, LOGGER, capture_output=capture_output, capture_errors=capture_errors)      # Shows the output in real time and capture it to the LOGGER.
            # result = subprocess.run(gpth_command, check=True, capture_output=capture_output, text=True)


            # Rename folder 'ALL_PHOTOS' by 'No-Albums'
            all_photos_path = os.path.join(output_folder, 'ALL_PHOTOS')
            others_path = os.path.join(output_folder, 'No-Albums')
            if os.path.exists(all_photos_path) and os.path.isdir(all_photos_path):
                os.rename(all_photos_path, others_path)

            LOGGER.info(f"INFO    : ✅ GPTH Tool finxing completed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR   : ❌ GPTH Tool fixing failed:\n{e.stderr}")
            return False
        

def fix_metadata_with_exif_tool(output_folder, log_level=logging.INFO):
    """Runs the EXIF Tool command to fix photo metadata."""
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Fixing EXIF metadata in '{output_folder}'...")
        # Detect the operating system
        current_os = platform.system()
        # Determine the Tool name based on the OS
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
            LOGGER.info(f"INFO    : EXIF Tool fixing completed successfully.")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR   : EXIF Tool fixing failed:\n{e.stderr}")
        