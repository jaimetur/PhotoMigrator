# CustomLogger.py
import logging
import os
import sys
import threading
from contextlib import contextmanager

from colorama import Fore, Style

from Core.StandaloneFunctions import resolve_path
from Core import GlobalVariables as GV

#------------------------------------------------------------------
# 1) Definir el nuevo nivel VERBOSE (valor 5)
logging.addLevelName(GV.VERBOSE_LEVEL_NUM, "VERBOSE")

# 2) Añadir el método `verbose()` a Logger
def verbose(self, message, *args, **kws):
    if self.isEnabledFor(GV.VERBOSE_LEVEL_NUM):
        self._log(GV.VERBOSE_LEVEL_NUM, message, args, **kws)
logging.Logger.verbose = verbose
#------------------------------------------------------------------

#------------------------------------------------------------------
# Replace original print to use the same GV.LOGGER formatter
def print_verbose(*args, **kwargs):
    # Construimos el mensaje igual que print normal
    message = " ".join(str(a) for a in args)
    # Y lo enviamos al GV.LOGGER como INFO (o al nivel que quieras)
    GV.LOGGER.verbose(message)
def print_debug(*args, **kwargs):
    # Construimos el mensaje igual que print normal
    message = " ".join(str(a) for a in args)
    # Y lo enviamos al GV.LOGGER como INFO (o al nivel que quieras)
    GV.LOGGER.debug(message)
def print_info(*args, **kwargs):
    # Construimos el mensaje igual que print normal
    message = " ".join(str(a) for a in args)
    # Y lo enviamos al GV.LOGGER como INFO (o al nivel que quieras)
    GV.LOGGER.info(message)
def print_warning(*args, **kwargs):
    # Construimos el mensaje igual que print normal
    message = " ".join(str(a) for a in args)
    # Y lo enviamos al GV.LOGGER como INFO (o al nivel que quieras)
    GV.LOGGER.warning(message)
def print_critical(*args, **kwargs):
    # Construimos el mensaje igual que print normal
    message = " ".join(str(a) for a in args)
    # Y lo enviamos al GV.LOGGER como INFO (o al nivel que quieras)
    GV.LOGGER.critical(message)
#------------------------------------------------------------------
# Class to Downgrade from INFO to DEBUG/WARNING/ERROR when certain chain is detected
class ChangeLevelFilter(logging.Filter):
    TAG_LEVEL_MAP = {
        '[DEBUG]': logging.DEBUG,
        '[WARNING]': logging.WARNING,
        '[ERROR]': logging.ERROR,
    }
    def filter(self, record):
        # Solo intervenimos mensajes lanzados con logger.info()
        if record.levelno == logging.INFO:
            msg = record.getMessage()
            for tag, lvl in self.TAG_LEVEL_MAP.items():
                if tag in msg:
                    record.levelno = lvl
                    record.levelname = logging.getLevelName(lvl)
                    break
        return True


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
                "VERBOSE": Fore.CYAN,
                "DEBUG": Fore.LIGHTCYAN_EX,
                "INFO": Fore.LIGHTWHITE_EX,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED,
                "CRITICAL": Fore.MAGENTA,
            }
            # Aplicamos el color según el nivel de logging
            color = COLORS.get(record.levelname, "")
            formatted_message = f"{color}{formatted_message}{Style.RESET_ALL}"
        return formatted_message

# # Clase personalizada para formatear los mensajes que van al fichero plano txt (sin colores)
# class CustomTxtFormatter(logging.Formatter):
#     def format(self, record):
#         # Crear una copia del mensaje para evitar modificar record.msg globalmente
#         original_msg = record.msg
#         formatted_message = super().format(record)
#         # Restaurar el mensaje original
#         record.msg = original_msg
#         return formatted_message

# # Clase personalizada para formatear los mensajes que van al fichero de log (Sin colores, y sustituyendo INFO:, WARNING:, ERROR:, CRITICAL:, DEBUG:, VERBOSE: por '')
# class CustomLogFormatter(logging.Formatter):
#     def format(self, record):
#         # Crear una copia del mensaje para evitar modificar record.msg globalmente
#         original_msg = record.msg
#         if record.levelname == "VERBOSE":
#             record.msg = record.msg.replace("VERBOSE : ", "")
#         elif record.levelname == "DEBUG":
#             record.msg = record.msg.replace("DEBUG   : ", "")
#         elif record.levelname == "INFO":
#             record.msg = record.msg.replace("INFO    : ", "")
#         elif record.levelname == "WARNING":
#             record.msg = record.msg.replace("WARNING : ", "")
#         elif record.levelname == "ERROR":
#             record.msg = record.msg.replace("ERROR   : ", "")
#         elif record.levelname == "CRITICAL":
#             record.msg = record.msg.replace("CRITICAL: ", "")
#         formatted_message = super().format(record)
#         # Restaurar el mensaje original
#         record.msg = original_msg
#         return formatted_message

class CustomInMemoryLogHandler(logging.Handler):
    """
    Almacena los registros de logging en una lista.
    Luego 'start_dashboard' leerá esa lista para mostrarlos en el panel de logs.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue   # lista compartida para almacenar los mensajes
    def emit(self, record):
        # Formatear mensaje
        msg = self.format(record)
        # Guardarlo en la cola
        self.log_queue.put(msg)
        # Guardarlo en la lista
        # self.log_queue.append(msg)

class LoggerStream:
    """Intercepta stdout y stderr para redirigirlos al GV.LOGGER."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())  # Enviar a GV.LOGGER
    def flush(self):
        """No es necesario hacer nada aquí, pero lo definimos para compatibilidad."""
        pass
    def isatty(self):
        """Evitar errores en detección de terminal."""
        return False


# 🚀 Clase para capturar `print()` y `stderr` sin afectar `rich.Live`
class LoggerCapture:
    """Captura stdout y stderr y los redirige al GV.LOGGER sin afectar Rich.Live"""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())  # Guardar en el GV.LOGGER sin imprimir en pantalla
    def flush(self):
        pass  # No es necesario para logging


# Integrar tqdm con el logger
class LoggerConsoleTqdm:
    """Redirige la salida de tqdm solo a los manejadores de consola del GV.LOGGER."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
    def write(self, message):
        message = message.strip()
        if message:
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


class ThreadLevelFilter(logging.Filter):
    def __init__(self, level):
        super().__init__()
        self.level = level
        self.thread_id = threading.get_ident()
    def filter(self, record):
        # Solo afecta al hilo actual
        if threading.get_ident() == self.thread_id:
            return record.levelno >= self.level
        return True  # otros hilos no afectados


def log_setup(log_folder="Logs", log_filename=None, log_level=logging.INFO, skip_logfile=False, skip_console=False, format='log'):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """

    if not log_filename:
        log_filename=GV.SCRIPT_NAME

    # Crear la carpeta de logs si no existe
    # Resolver log_folder a ruta absoluta
    log_folder = resolve_path(log_folder)
    os.makedirs(log_folder, exist_ok=True)

    # Clear existing handlers to avoid duplicate logs
    GV.LOGGER = logging.getLogger('PhotoMigrator')

    if GV.LOGGER.hasHandlers():
        GV.LOGGER.handlers.clear()

    if not skip_console:
        # Set up console handler (simple output without asctime and levelname)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            CustomConsoleFormatter(
                fmt="%(levelname)-8s: %(message)s",
                datefmt="%H:%M:%S"
            )
        )
        console_handler.addFilter(ChangeLevelFilter())      # Add Filter to Downgrade from INFO to DEBUG/WARNING/ERROR when detected chains
        console_handler.is_console_output = True
        GV.LOGGER.addHandler(console_handler)

    if not skip_logfile:
        if format.lower() in ['log', 'all']:
            # Set up logfile handler (detailed output with asctime and levelname)
            log_file = os.path.join(log_folder, log_filename + '.log')
            file_handler_detailed = logging.FileHandler(log_file, encoding="utf-8-sig")
            file_handler_detailed.setLevel(log_level)
            file_handler_detailed.setFormatter(
                logging.Formatter(
                    fmt='%(asctime)s [%(levelname)-8s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
            file_handler_detailed.addFilter(ChangeLevelFilter())  # Add Filter to Downgrade from INFO to DEBUG/WARNING/ERROR when detected chains
            GV.LOGGER.addHandler(file_handler_detailed)
        elif format.lower() in ['txt', 'all']:
            # Set up txt file handler (output without asctime and levelname)
            log_file = os.path.join(log_folder, log_filename + '.txt')
            file_handler_plain = logging.FileHandler(log_file, encoding="utf-8-sig")
            file_handler_plain.setLevel(log_level)
            # Formato estándar para el manejador de ficheros plano
            file_handler_plain.setFormatter(
                logging.Formatter(
                    fmt='%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
            file_handler_plain.addFilter(ChangeLevelFilter())  # Add Filter to Downgrade from INFO to DEBUG/WARNING/ERROR when detected chains
            GV.LOGGER.addHandler(file_handler_plain)
        else:
            print (f"{GV.TAG_INFO}Unknown format '{format}' for Logger. Please select a valid format between: ['log', 'txt', 'all].")

    # Set the log level for the root logger
    GV.LOGGER.setLevel(log_level)
    GV.LOGGER.propagate = False # <-- IMPORTANTE PARA EVITAR USAR EL LOOGER RAIZ

    return GV.LOGGER

# ==============================================================================
#                               LOGGING FUNCTIONS
# ==============================================================================
def check_color_support(log_level=None):
    """ Detect if Terminal has supports colors """
    if sys.stdout.isatty():  # Verifica si es un terminal interactivo
        term = os.getenv("TERM", "")
        if term in ("dumb", "linux", "xterm-mono"):  # Terminales sin colores
            return False
        return True
    return False

def get_logger_filename(logger):
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename  # Devuelve el path del archivo de logs
    return ""  # Si no hay un FileHandler, retorna ""


# Create context to temporarily disable console output
@contextmanager
def suppress_console_output_temporarily(logger):
    """
    Temporarily removes handlers marked with `.is_console_output = True` from the logger.
    """
    original_handlers = logger.handlers[:]
    original_propagate = logger.propagate
    logger.handlers = [h for h in original_handlers if not getattr(h, 'is_console_output', False)]
    logger.propagate = False
    try:
        yield
    finally:
        logger.handlers = original_handlers
        logger.propagate = original_propagate


# Crear un contexto para cambiar el nivel del logger temporalmente
@contextmanager
def set_log_level(logger: logging.Logger, level: int):
    """
    Context manager que:
      1) guarda el estado actual de logger.level y de cada handler.level,
         y todos los filtros ThreadLevelFilter instalados,
      2) quita esos filtros ThreadLevelFilter antiguos (para "romper" el contexto padre),
      3) instala un ThreadLevelFilter nuevo a `level`,
      4) ajusta logger.level y todos los handler.level a `level`,
      5) al salir, restaura los filtros, el logger.level y handler.level a sus valores originales.
    """
    # If no level have been passed, or level=None, assign the GlovalVariable level defined by user arguments
    if not level:
        level = GV.LOG_LEVEL

    # 1) Guardar estados originales
    orig_logger_level   = logger.level
    orig_handler_states = [(h, h.level) for h in logger.handlers]
    # Guardar los filtros ThreadLevelFilter que hubiera
    orig_thread_filters = [f for f in logger.filters if isinstance(f, ThreadLevelFilter)]

    # 2) Quitar los filtros de hilo anteriores
    for f in orig_thread_filters:
        logger.removeFilter(f)

    # 3) Crear e instalar el filtro nuevo
    new_filter = ThreadLevelFilter(level)
    logger.addFilter(new_filter)

    # 4) Ajustar niveles
    logger.setLevel(level)
    for handler, _ in orig_handler_states:
        handler.setLevel(level)

    try:
        yield
    finally:
        # 5a) Quitar el filtro que acabamos de poner
        logger.removeFilter(new_filter)
        # 5b) Restaurar los filtros originales
        for f in orig_thread_filters:
            logger.addFilter(f)
        # 5c) Restaurar niveles originales
        logger.setLevel(orig_logger_level)
        for handler, old_level in orig_handler_states:
            handler.setLevel(old_level)


def clone_logger(original_logger, new_name=None):
    """
    Crea un nuevo logger con el mismo nivel y handlers que el original,
    pero evitando la duplicación de mensajes.

    Args:
        original_logger (logging.Logger): El logger original.
        new_name (str): Nombre opcional para el nuevo logger.

    Returns:
        logging.Logger: Un nuevo logger independiente con los mismos handlers.
    """
    new_logger_name = new_name if new_name else f"{original_logger.name}_copy"
    new_logger = logging.getLogger(new_logger_name)

    # Copiar nivel de log
    new_logger.setLevel(original_logger.level)

    # Evitar agregar handlers duplicados
    if not new_logger.hasHandlers():
        for handler in original_logger.handlers:
            new_logger.addHandler(handler)  # Agregamos el mismo handler sin copiarlo

    return new_logger