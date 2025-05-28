import os,sys
import platform
import subprocess
import logging
import select
import threading
import queue
import re
import time
from packaging.version import Version

from CustomLogger import set_log_level
from GlobalVariables import LOGGER, GPTH_VERSION, RESOURCES_PATH_CURRENT_FOLDER
import Utils

def resource_path(relative_path, log_level=logging.INFO):
    """
    Devuelve la ruta absoluta al recurso 'relative_path', funcionando en:
    - PyInstaller (onefile o standalone)
    - Nuitka (onefile o standalone)
    - Ejecución directa con Python (desde el directorio actual, o desde el directorio padre del script)
    """
    print("---DEBUG INFO")
    print(f"__file__           : {globals().get('__file__', 'NO __file__')}")
    print(f"sys.argv[0]        : {sys.argv[0]}")
    print(f"sys.executable     : {sys.executable}")
    print(f"sys.frozen         : {getattr(sys, 'frozen', False)}")
    print(f"os.getcwd()        : {os.getcwd()}")
    print("--- END DEBUG INFO")
    with set_log_level(LOGGER, log_level):
        try:
            # Compilado con Nuitka standalone
            base_path = __compiled__.containing_dir
        except NameError:
            if hasattr(sys, '_MEIPASS'):
                # Compilado con PyInstaller
                base_path = sys._MEIPASS
            elif "NUITKA_ONEFILE_PARENT" in os.environ:
                # Compilado con Nuitka onefile sin __compiled__
                base_path = os.path.dirname(os.path.abspath(__file__))
            elif "__file__" in globals():
                # Ejecución directa con Python (2 opciones):
                if RESOURCES_PATH_CURRENT_FOLDER:
                    # Buscar en la carpeta actual de ejecución
                    base_path = os.getcwd()
                else:
                    # Buscar un nivel por encima desde __file__ (que apuntará al .py correspondiente)
                    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            else:
                # Caso muy raro sin __file__
                base_path = os.getcwd()
        return os.path.join(base_path, relative_path)

def run_command(command, logger, capture_output=False, capture_errors=True):
    """
    Ejecuta un comando en un subproceso y maneja la salida en tiempo real si capture_output=True.
    Evita registrar múltiples líneas de barras de progreso en el log.
    """
    if capture_output or capture_errors:
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
        LOGGER.info(f"INFO    : GPTH Version : '{GPTH_VERSION}'")
        LOGGER.info(f"INFO    : Input Folder : '{input_folder}'")
        LOGGER.info(f"INFO    : Output Folder: '{output_folder}'")

        # Detect the operating system
        current_os = Utils.get_os()
        current_arch = Utils.get_arch()

        # Determine the Tool name based on the OS
        tool_name = f"gpth-{GPTH_VERSION}-{current_os}-{current_arch.replace('x64', 'x86_64')}"
        if current_os in ("linux", "macos"):
            tool_name  +=".bin"
        elif current_os == "windows":
            tool_name += ".exe"
        else:
            LOGGER.error(f"ERROR   : Invalid OS: {current_os}. Exiting...")
            sys.exit(-1)

        LOGGER.info(f"INFO    : Using GPTH Tool file: '{tool_name}'...")
        # Usar resource_path para acceder a archivos o directorios:
        gpth_tool_path = resource_path(os.path.join("gpth_tool", tool_name))

        if Version(GPTH_VERSION) >= Version("4.0.0"):
            gpth_command = [gpth_tool_path, "--input", input_folder, "--output", output_folder, "--no-interactive", "--write-exif"]
        else:
            gpth_command = [gpth_tool_path, "--input", input_folder, "--output", output_folder, "--no-interactive"]

        # If ignore_takeout_structure is True, we append --fix input_folder to the gpth tool call
        if ignore_takeout_structure:
            gpth_command.append("--fix")
            gpth_command.append(input_folder)

        # By default force --no-divide-to-dates and the Tool will create date structure if needed
        # gpth_command.append("--no-divide-to-dates") # For previous versions of the original GPTH tool

        # The new version of GPTH have changed this argument:
        gpth_command.append("--divide-to-dates=0")  # 0: No divide, 1: year, 2: year/month, 3: year/month/day

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

        # Use the new feature to Delete the "supplemental-metadata" suffix from .json files to ensure that script works correctly
        gpth_command.append("--modify-json")

        # Use the new feature to Transform Pixel .MP or .MV extensions to ".mp4"
        gpth_command.append("--transform-pixel-mp")

        # Use the new feature to Set creation time equal to the last modification date at the end of the program. (Only Windows supported)
        gpth_command.append("--update-creation-time")

        try:
            command = ' '.join(gpth_command)
            LOGGER.debug(f"DEBUG   : Running GPTH with following command: {command}")
            Utils.print_arguments_pretty(gpth_command, title='GPTH Command:')
            ok = run_command(gpth_command, LOGGER, capture_output=capture_output, capture_errors=capture_errors)      # Shows the output in real time and capture it to the LOGGER.
            # ok = subprocess.run(gpth_command, check=True, capture_output=capture_output, text=True)

            # Rename folder 'ALL_PHOTOS' by 'No-Albums'
            all_photos_path = os.path.join(output_folder, 'ALL_PHOTOS')
            others_path = os.path.join(output_folder, 'No-Albums')
            if os.path.exists(all_photos_path) and os.path.isdir(all_photos_path):
                os.rename(all_photos_path, others_path)

            # Check the result of GPTH process
            if ok==0:
                LOGGER.info(f"INFO    : ✅ GPTH Tool fixing completed successfully.")
                return True
            else:
                LOGGER.error(f"ERROR   : ❌ GPTH Tool fixing failed.")
                return False
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
        