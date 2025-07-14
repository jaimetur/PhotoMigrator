# CustomLogger.py
import logging
import os
import sys
import threading
from contextlib import contextmanager

from colorama import Fore, Style

from Core import GlobalVariables as GV
from Core.GlobalVariables import VERBOSE_LEVEL_NUM
from Utils.StandaloneUtils import resolve_external_path, custom_print


#------------------------------------------------------------------
def enable_verbose_level(level_num=GV.VERBOSE_LEVEL_NUM):
    """
    Activa el nivel VERBOSE en el módulo logging, permitiendo:
    - logging.VERBOSE para obtener el nivel numérico.
    - logger.verbose(...) para registrar mensajes con ese nivel.
    """
    # 0) Evitar redefinir si ya está activado
    if hasattr(logging, "VERBOSE"):
        return

    # 1) Register the level_name
    logging.addLevelName(level_num, "VERBOSE")

    # 2) Add as attribute to logging module
    logging.VERBOSE = level_num

    # 3) define .verbose() method
    def verbose(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    # 4) Inject the method verbose to the class logging.Logger to be available in all loggers
    logging.Logger.verbose = verbose
#------------------------------------------------------------------
# Execute the function at the beginning to enable verbose level from the beginning of the tool
enable_verbose_level()

#------------------------------------------------------------------
# Create standard logging function to send to GV.LOGGER any message with the right log_level
def custom_log(*args, log_level=logging.INFO, **kwargs):
    message = " ".join(str(a) for a in args)
    GV.LOGGER.log(log_level, message, **kwargs)
#------------------------------------------------------------------
# Class to Downgrade from INFO to DEBUG/WARNING/ERROR when certain chain is detected
class ChangeLevelFilter(logging.Filter):
    TAG_LEVEL_MAP = {
        '[VERBOSE]': VERBOSE_LEVEL_NUM,
        '[DEBUG]': logging.DEBUG,
        '[INFO]': logging.INFO,
        '[WARNING]': logging.WARNING,
        '[ERROR]': logging.ERROR,
        '[CRITICAL]': logging.CRITICAL,
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

# Clase personalizada para formatear los mensajes que van al fichero plano txt (sin colores)
class CustomTxtFormatter(logging.Formatter):
    def format(self, record):
        # Crear una copia del mensaje para evitar modificar record.msg globalmente
        original_msg = record.msg
        formatted_message = super().format(record)
        # Restaurar el mensaje original
        record.msg = original_msg
        return formatted_message

# Clase personalizada para formatear los mensajes que van al fichero de log (Sin colores, y sustituyendo INFO:, WARNING:, ERROR:, CRITICAL:, DEBUG:, VERBOSE: por '')
class CustomLogFormatter(logging.Formatter):
    def format(self, record):
        # Crear una copia del mensaje para evitar modificar record.msg globalmente
        original_msg = record.msg
        if record.levelname == "VERBOSE":
            record.msg = record.msg.replace("VERBOSE : ", "")
        elif record.levelname == "DEBUG":
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


def log_setup(log_folder="Logs", log_filename=None, log_level=logging.INFO, skip_logfile=False, skip_console=False, format='log'):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """

    if not log_filename:
        log_filename=GV.TOOL_NAME

    # Crear la carpeta de logs si no existe
    # Resolver log_folder a ruta absoluta
    log_folder = resolve_external_path(log_folder)
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
            # print (f"{GV.TAG_INFO}Unknown format '{format}' for Logger. Please select a valid format between: ['log', 'txt', 'all].")
            custom_print(f"Unknown format '{format}' for Logger. Please select a valid format between: ['log', 'txt', 'all].", log_level=logging.INFO)

    # Set the log level for the root logger
    GV.LOGGER.setLevel(log_level)
    GV.LOGGER.propagate = False # <-- IMPORTANTE PARA EVITAR USAR EL LOOGER RAIZ

    # 2) Define e instala el hook global de excepciones en hilos
    def thread_exc_hook(args):
        GV.LOGGER.setLevel(logging.INFO)
        GV.LOGGER.error(
            f"Excepción no capturada en hilo {args.thread.name}: {args.exc_value}",
            exc_info=args.exc_value
        )

    threading.excepthook = thread_exc_hook

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

# # Crear un contexto para cambiar el nivel del logger y de todos los handlers temporalmente incluyendo threads
# @contextmanager
# def set_log_level(logger: logging.Logger, level: int, include_threads=False):
#     """
#     Context manager que:
#       1) guarda el estado actual de logger.level y de cada handler.level,
#          y todos los filtros ThreadLevelFilter instalados,
#       2) quita esos filtros ThreadLevelFilter antiguos (para "romper" el contexto padre),
#       3) instala un ThreadLevelFilter nuevo a `level`,
#       4) ajusta logger.level y todos los handler.level a `level`,
#       5) al salir, restaura los filtros, el logger.level y handler.level a sus valores originales.
#     """
#     # If no level have been passed, or level=None, assign the GlovalVariable level defined by user arguments
#     if not level:
#         level = GV.LOG_LEVEL
#
#     # 1) Guardar estados originales
#     orig_logger_level   = logger.level
#     orig_handler_states = [(h, h.level) for h in logger.handlers]
#
#     if include_threads:
#         # Guardar los filtros ThreadLevelFilter que hubiera
#         orig_thread_filters = [f for f in logger.filters if isinstance(f, ThreadLevelFilter)]
#
#         # 2) Quitar los filtros de hilo anteriores
#         for f in orig_thread_filters:
#             logger.removeFilter(f)
#
#         # 3) Crear e instalar el filtro nuevo
#         new_filter = ThreadLevelFilter(level)
#         logger.addFilter(new_filter)
#
#     # 4) Ajustar niveles
#     logger.setLevel(level)
#     for handler, _ in orig_handler_states:
#         handler.setLevel(level)
#
#     try:
#         yield
#     finally:
#         if include_threads:
#             # 5a) Quitar el filtro que acabamos de poner
#             logger.removeFilter(new_filter)
#             # 5b) Restaurar los filtros originales
#             for f in orig_thread_filters:
#                 logger.addFilter(f)
#         # 5c) Restaurar niveles originales
#         logger.setLevel(orig_logger_level)
#         for handler, old_level in orig_handler_states:
#             handler.setLevel(old_level)

# Crear un contexto para cambiar el nivel del logger temporalmente
@contextmanager
def set_log_level(logger, level):
    """
    Context manager that temporarily sets a specific logging level for the current thread only.

    This function adds a thread-specific filter to the given logger, ensuring that the specified
    logging level affects exclusively the current thread, without modifying the global logger level.
    It is thread-safe and suitable for both single-threaded and multi-threaded environments.

    Args:
        logger (logging.Logger): The logger instance to which the temporary logging level applies.
        level (int): The logging level to apply temporarily (e.g., logging.INFO, logging.ERROR).

    Usage example:
        with set_threads_log_level(LOGGER, logging.ERROR):
            LOGGER.info("This message will NOT be shown in this thread.")
            LOGGER.error("This message will be shown in this thread.")
        # Outside the context, the logger reverts to its original behavior.

    Important:
        - This context manager does NOT change the global logging level.
        - It only affects log messages emitted from the thread executing this context.
        - After exiting the context, the original logging behavior is restored automatically.
    """
    if logger is None:
        yield  # do nothing if logger is None
        return

    # If no level have been passed, or level=None, assign the GlovalVariable level defined by user arguments
    if not level:
        level = GV.LOG_LEVEL
    filtro = ThreadLevelFilter(level)
    logger.addFilter(filtro)
    try:
        yield
    finally:
        logger.removeFilter(filtro)


# Crear un contexto para cambiar el nivel del logger y de todos los handlers temporalmente
@contextmanager
def set_log_level_simple(logger: logging.Logger, level: int):
    # If no level have been passed, or level=None, assign the GlovalVariable level defined by user arguments
    if not level:
        level = GV.LOG_LEVEL

    orig = logger.level
    for h in logger.handlers:
        h_orig = h.level
        h.setLevel(level)
        try:
            yield
        finally:
            logger.setLevel(orig)
            for h, lvl in zip(logger.handlers, [h.level for h in logger.handlers]):
                h.setLevel(h_orig)

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