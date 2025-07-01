import base64
import ctypes
import hashlib
import logging
import os
import platform
import re
import stat
import subprocess
import sys
import time
from dataclasses import is_dataclass, asdict
from datetime import datetime

import piexif
from tqdm import tqdm as original_tqdm

# import Core.GlobalVariables as GV
from Core.CustomLogger import set_log_level
from Core.GlobalVariables import ARGS, LOGGER, VIDEO_EXT, PHOTO_EXT, MSG_TAGS, VERBOSE_LEVEL_NUM


# ------------------------------------------------------------------
# Integrar tqdm con el logger
class TqdmLoggerConsole:
    """Redirige la salida de tqdm solo a los manejadores de consola del GV.LOGGER."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self.levelname = logging.getLevelName(level)
    def write(self, message):
        message = message.strip()
        if message:
            if self.levelname == "VERBOSE":
                message = message.replace("VERBOSE : ", "")
            elif self.levelname == "DEBUG":
                message = message.replace("DEBUG   : ", "")
            elif self.levelname == "INFO":
                message = message.replace("INFO    : ", "")
            elif self.levelname == "WARNING":
                message = message.replace("WARNING : ", "")
            elif self.levelname == "ERROR":
                message = message.replace("ERROR   : ", "")
            elif self.levelname == "CRITICAL":
                message = message.replace("CRITICAL: ", "")

            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler):  # Solo handlers de consola
                    handler.emit(logging.LogRecord(
                        name=self.logger.name,
                        level=self.level,
                        pathname="",
                        lineno=0,
                        msg=message,
                        args=(),
                        exc_info=None
                    ))
    def flush(self):
        pass  # Necesario para compatibilidad con tqdm
    def isatty(self):
        """Engañar a tqdm para que lo trate como un terminal interactivo."""
        return True

# Crear instancia global del wrapper
TQDM_LOGGER_INSTANCE = TqdmLoggerConsole(LOGGER, logging.INFO)

######################
# FUNCIONES AUXILIARES
######################
# -------------------------------------------------------------
# Set Profile to analyze and optimize code:
# -------------------------------------------------------------
def profile_and_print(function_to_analyze, *args, step_name_for_profile='', live_stats=True, interval=10, top_n=10, **kwargs):
    """
    Ejecuta cProfile solo sobre function_to_analyze (dejando el sleep
    del wrapper fuera del profiling), vuelca stats a LOGGER.debug si
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
                    LOGGER.debug(f"{step_name_for_profile}⏱️ Intermediate Stats (top %d):\n\n%s", top_n, stream.getvalue() )

            final_result = result
        else:
            # Si no queremos live stats, esperamos a que acabe y ya está
            final_result = future.result()

    # Informe final
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
    LOGGER.debug(f"{step_name_for_profile}Final Profile Report (top %d):\n\n%s", top_n, stream.getvalue() )

    return final_result


# Redefinir `tqdm` para usar `TQDM_LOGGER_INSTANCE` si no se especifica `file` y estamos en modo Automatic-Migration con dashboard=true
def tqdm(*args, **kwargs):
    if ARGS['AUTOMATIC-MIGRATION'] and ARGS['dashboard'] == True:
        if 'file' not in kwargs:  # Si el usuario no especifica `file`, usar `TQDM_LOGGER_INSTANCE`
            kwargs['file'] = TQDM_LOGGER_INSTANCE
    return original_tqdm(*args, **kwargs)


def run_from_synology(log_level=None):
    """ Check if the srcript is running from a Synology NAS """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
        :param use_logger:
    """
    print("")
    indent = "    "
    i = 0
    if use_logger:
        LOGGER.info(f"{step_name}{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                LOGGER.info(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                LOGGER.info(f"{step_name}{indent}{arg}")
                i += 1
    else:
        if use_custom_print:
            from Utils.StandaloneUtils import custom_print
            custom_print(f"{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    custom_print(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    custom_print(f"{step_name}{indent}{arg}")
                    i += 1
        else:
            pass
            print(f"{MSG_TAGS['INFO']}{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}")
                    i += 1
    print("")


def ensure_executable(path):
    if platform.system() != "Windows":
        # Añade permisos de ejecución al usuario, grupo y otros sin quitar los existentes
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


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
                LOGGER.error(f"{step_name}Unsupported Operating System: {current_os}")
                os_label = "unknown"
            LOGGER.info(f"{step_name}Detected OS: {os_label}")
    else:
        current_os = platform.system()
        if current_os in ["Linux", "linux"]:
            os_label = "linux"
        elif current_os in ["Darwin", "macOS", "macos"]:
            os_label = "macos"
        elif current_os in ["Windows", "windows", "Win"]:
            os_label = "windows"
        else:
            print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Operating System: {current_os}")
            os_label = "unknown"
        print(f"{MSG_TAGS['INFO']}{step_name}Detected OS: {os_label}")
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
                LOGGER.error(f"{step_name}Unsupported Architecture: {current_arch}")
                arch_label = "unknown"
            LOGGER.info(f"{step_name}Detected architecture: {arch_label}")
    else:
        current_arch = platform.machine()
        if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
            arch_label = "x64"
        elif current_arch in ["aarch64", "arm64", "ARM64"]:
            arch_label = "arm64"
        else:
            print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Architecture: {current_arch}")
            arch_label = "unknown"
        print(f"{MSG_TAGS['INFO']}{step_name}Detected architecture: {arch_label}")
    return arch_label


def check_OS_and_Terminal(log_level=None):
    """ Check OS, Terminal Type, and System Architecture """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Detect the operating system
        current_os = get_os(log_level=logging.WARNING)
        # Detect the machine architecture
        arch_label = get_arch(log_level=logging.WARNING)
        # Logging OS
        if current_os == "linux":
            if run_from_synology():
                LOGGER.info(f"Script running on Linux System in a Synology NAS")
            else:
                LOGGER.info(f"Script running on Linux System")
        elif current_os == "macos":
            LOGGER.info(f"Script running on MacOS System")
        elif current_os == "windows":
            LOGGER.info(f"Script running on Windows System")
        else:
            LOGGER.error(f"Unsupported Operating System: {current_os}")
        # Logging Architecture
        LOGGER.info(f"Detected architecture: {arch_label}")
        # Terminal type detection
        if sys.stdout.isatty():
            LOGGER.info(f"Interactive (TTY) terminal detected for stdout")
        else:
            LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdout")
        if sys.stdin.isatty():
            LOGGER.info(f"Interactive (TTY) terminal detected for stdin")
        else:
            LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdin")
        LOGGER.info(f"")


def confirm_continue(log_level=None):
    # If argument 'no-request-user-confirmation' is true then don't ask and wait for user confirmation
    if ARGS['no-request-user-confirmation']:
        return True

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        while True:
            response = input("Do you want to continue? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                LOGGER.info(f"Continuing...")
                return True
            elif response in ['no', 'n']:
                LOGGER.info(f"Operation canceled.")
                return False
            else:
                LOGGER.warning(f"Invalid input. Please enter 'yes' or 'no'.")


def remove_quotes(input_string: str, log_level=logging.INFO) -> str:
    """
    Elimina todas las comillas simples y dobles al inicio o fin de la cadena.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        return input_string.strip('\'"')


def remove_server_name(path, log_level=None):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Expresión regular para rutas Linux (///servidor/)
        path = re.sub(r'///[^/]+/', '///', path)
        # Expresión regular para rutas Windows (\\servidor\)
        path = re.sub(r'\\\\[^\\]+\\', '\\\\', path)
        return path


def get_unique_items(list1, list2, key='filename', log_level=None):
    """
    Returns items that are in list1 but not in list2 based on a specified key.

    Args:
        list1 (list): First list of dictionaries.
        list2 (list): Second list of dictionaries.
        key (str): Key to compare between both lists.

    Returns:
        list: Items present in list1 but not in list2.
        :param log_level:
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext in PHOTO_EXT:
                update_exif_date(file_path, date_time, log_level=log_level)
            elif file_ext in VIDEO_EXT:
                update_video_metadata(file_path, date_time, log_level=log_level)
            LOGGER.debug(f"Metadata updated for {file_path} with timestamp {date_time}")
        except Exception as e:
            LOGGER.error(f"Failed to update metadata for {file_path}. {e}")
        

def update_exif_date(image_path, asset_time, log_level=None):
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
                    LOGGER.warning(f"Invalid date format for asset_time: {asset_time}. {e}")
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
                # LOGGER.warning(f"No EXIF metadata found in {image_path}. Creating new EXIF data.")
                # exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
                LOGGER.warning(f"No EXIF metadata found in {image_path}. Skipping it....")
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
                LOGGER.debug(f"EXIF metadata updated for {image_path} with timestamp {date_time_exif}")
            except Exception:
                LOGGER.error(f"Error when restoring original metadata to file: '{image_path}'")
                return
        except Exception as e:
            LOGGER.warning(f"Failed to update EXIF metadata for {image_path}. {e}")
        

def update_video_metadata(video_path, asset_time, log_level=None):
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
                    LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
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
                    LOGGER.warning(f"Failed to update file creation time on Windows. {e}")
            LOGGER.debug(f"File system timestamps updated for {video_path} with timestamp {datetime.fromtimestamp(mod_time)}")
        except Exception as e:
            LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")


def update_video_metadata_with_ffmpeg(video_path, asset_time, log_level=None):
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
                    LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
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
            LOGGER.debug(f"Video metadata updated for {video_path} with timestamp {formatted_date}")
        except Exception as e:
            LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")
        

# Convert to list
def convert_to_list(input_string, log_level=None):
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
            LOGGER.warning(f"Failed to convert string to List for {input_string}. {e}")
        
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


def capitalize_first_letter(text):
    if not text:
        return text
    return text[0].upper() + text[1:]


def get_subfolders_with_exclusions(input_folder, exclude_subfolders=None):
    """
    Devuelve la lista de subcarpetas directas dentro de `input_folder`,
    excluyendo las indicadas en `exclude_subfolders`.
    Si `input_folder` no existe o no es un directorio, devuelve una lista vacía.
    """
    if not os.path.isdir(input_folder):
        return []

    if exclude_subfolders is None:
        exclude = set()
    elif isinstance(exclude_subfolders, str):
        exclude = {exclude_subfolders}
    else:
        exclude = set(exclude_subfolders)

    return [
        entry
        for entry in os.listdir(input_folder)
        if os.path.isdir(os.path.join(input_folder, entry)) and entry not in exclude
    ]


def print_dict_pretty(result, log_level):
    # Si es un dataclass, lo convierto a dict
    if is_dataclass(result):
        result = asdict(result)
    # Compruebo que ahora sea un dict
    if not isinstance(result, dict):
        raise TypeError(f"Se esperaba dict o dataclass, pero recibí {type(result).__name__}")
    # Imprimo cada par clave:valor de forma alineada
    for key, value in result.items():
        if log_level == VERBOSE_LEVEL_NUM:
            LOGGER.verbose(f"{key:35}: {value}")
        elif log_level == logging.DEBUG:
            LOGGER.debug(f"{key:35}: {value}")
        elif log_level == logging.INFO:
            LOGGER.info(f"{key:35}: {value}")
        elif log_level == logging.WARNING:
            LOGGER.warning(f"{key:35}: {value}")
        elif log_level == logging.ERROR:
            LOGGER.error(f"{key:35}: {value}")


def timed_subprocess(cmd, step_name=""):
    """
    Ejecuta cmd con Popen, espera a que termine y registra sólo
    el tiempo total de ejecución al final.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.time()
    out, err = proc.communicate()
    total = time.time() - start
    LOGGER.debug(f"{step_name}✅ subprocess finished in {total:.2f}s")
    return proc.returncode, out, err
