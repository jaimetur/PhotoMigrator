# CustomLogger.py
import os,sys
import logging
from colorama import Fore, Style
from contextlib import contextmanager

def check_color_support(log_level=logging.INFO):
    """ Detect if Terminal has supports colors """
    if sys.stdout.isatty():  # Verifica si es un terminal interactivo
        term = os.getenv("TERM", "")
        if term in ("dumb", "linux", "xterm-mono"):  # Terminales sin colores
            return False
        return True
    return False

# Clase personalizada para formatear los mensajes que van a la consola (Añadimos colorees según el nivel del mensaje)
class CustomConsoleFormatter(logging.Formatter):
    def format(self, record):
        # Crear una copia del mensaje para evitar modificar record.msg globalmente
        original_msg = record.msg
        formatted_message = super().format(record)
        # Restaurar el mensaje original
        record.msg = original_msg
        color_support = check_color_support()
        if color_support:
            """Formato personalizado con colores ANSI."""
            COLORS = {
                "DEBUG": Fore.BLUE,
                # "INFO": Fore.GREEN,
                # "INFO": Fore.WHITE,
                "INFO": Fore.LIGHTWHITE_EX,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED,
                "CRITICAL": Fore.MAGENTA,
            }
            # Aplicamos el color según el nivel de logging
            color = COLORS.get(record.levelname, "")
            formatted_message = f"{color}{formatted_message}{Style.RESET_ALL}"
        return formatted_message

# Clase personalizada para formatear los mensajes que van al fichero plano txt (sin colores)
class CustomTxtFormatter(logging.Formatter):
    def format(self, record):
        # Crear una copia del mensaje para evitar modificar record.msg globalmente
        original_msg = record.msg
        formatted_message = super().format(record)
        # Restaurar el mensaje original
        record.msg = original_msg
        return formatted_message

# Clase personalizada para formatear los mensajes que van al fichero de log (Sin colores, y sustituyendo INFO:, WARNING:, ERROR:, CRITICAL:, DEBUG   : por '')
class CustomLogFormatter(logging.Formatter):
    def format(self, record):
        # Crear una copia del mensaje para evitar modificar record.msg globalmente
        original_msg = record.msg
        if record.levelname == "DEBUG":
            record.msg = record.msg.replace("DEBUG   : ", "")
        elif record.levelname == "INFO":
            record.msg = record.msg.replace("INFO    : ", "")
        elif record.levelname == "WARNING":
            record.msg = record.msg.replace("WARNING : ", "")
        elif record.levelname == "ERROR":
            record.msg = record.msg.replace("ERROR   : ", "")
        elif record.levelname == "CRITICAL":
            record.msg = record.msg.replace("CRITICAL: ", "")
        formatted_message = super().format(record)
        # Restaurar el mensaje original
        record.msg = original_msg
        return formatted_message

# Integrar tqdm con el logger
class TqdmToLogger:
    """Clase para redirigir los mensajes de tqdm al logger."""
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.level = log_level
    def write(self, msg):
        # Evita mensajes vacíos
        if msg.strip():
            self.logger.log(self.level, msg.strip())
    def flush(self):
        pass  # Requerido por tqdm, pero no es necesario implementar


def log_setup(log_folder="Logs", log_filename=None, log_level=logging.INFO, timestamp=None, skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """
    if not log_filename:
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        if timestamp:
            log_filename=f"{script_name}_{timestamp}"
        else:
            log_filename=script_name

    # Crear la carpeta de logs si no existe
    current_directory = os.getcwd()
    log_folder = os.path.join(current_directory, log_folder)
    os.makedirs(log_folder, exist_ok=True)

    # Clear existing handlers to avoid duplicate logs
    LOGGER = logging.getLogger()
    if LOGGER.hasHandlers():
        LOGGER.handlers.clear()

    if not skip_console:
        # Set up console handler (simple output without asctime and levelname)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        LOGGER.addHandler(console_handler)
    if not skip_logfile:
        if detail_log:
            # Set up logfile handler (detailed output with asctime and levelname)
            log_file = os.path.join(log_folder, log_filename + '.log')
            file_handler_detailed = logging.FileHandler(log_file, encoding="utf-8")
            file_handler_detailed.setLevel(log_level)
            file_handler_detailed.setFormatter(CustomLogFormatter(fmt='%(asctime)s [%(levelname)-8s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            LOGGER.addHandler(file_handler_detailed)
        if plain_log:
            # Set up txt file handler (output without asctime and levelname)
            log_file = os.path.join(log_folder, log_filename + '.txt')
            file_handler_plain = logging.FileHandler(log_file, encoding="utf-8")
            file_handler_plain.setLevel(log_level)
            # Formato estándar para el manejador de ficheros plano
            file_handler_plain.setFormatter(CustomTxtFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            LOGGER.addHandler(file_handler_plain)

    # Añadir TqdmToLogger como atributo al logger
    LOGGER.tqdm_stream = TqdmToLogger(LOGGER, log_level=logging.INFO)

    # Set the log level for the root logger
    LOGGER.setLevel(log_level)
    return LOGGER

# Crear un contexto para cambiar el nivel del logger temporalmente
@contextmanager
def set_log_level(logger, level):
    old_level = logger.level  # Guardar nivel actual
    logger.setLevel(level)  # Cambiar nivel
    try:
        yield
    finally:
        logger.setLevel(old_level)  # Restaurar nivel original