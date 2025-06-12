# CustomLogger.py
import os,sys
import logging
from colorama import Fore, Style
from contextlib import contextmanager
import threading


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
                "DEBUG": Fore.CYAN,
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
    """Intercepta stdout y stderr para redirigirlos al LOGGER."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())  # Enviar a LOGGER
    def flush(self):
        """No es necesario hacer nada aquí, pero lo definimos para compatibilidad."""
        pass
    def isatty(self):
        """Evitar errores en detección de terminal."""
        return False


# 🚀 Clase para capturar `print()` y `stderr` sin afectar `rich.Live`
class LoggerCapture:
    """Captura stdout y stderr y los redirige al LOGGER sin afectar Rich.Live"""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())  # Guardar en el LOGGER sin imprimir en pantalla
    def flush(self):
        pass  # No es necesario para logging


# Integrar tqdm con el logger
class LoggerConsoleTqdm:
    """Redirige la salida de tqdm solo a los manejadores de consola del LOGGER."""
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


def log_setup(log_folder="Logs", log_filename=None, log_level=logging.INFO, timestamp=None, skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """
    from GlobalFunctions import resolve_path
    if not log_filename:
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        if timestamp:
            log_filename=f"{script_name}_{timestamp}"
        else:
            log_filename=script_name

    # Crear la carpeta de logs si no existe
    # Resolver log_folder a ruta absoluta
    log_folder = resolve_path(log_folder)
    os.makedirs(log_folder, exist_ok=True)

    # Clear existing handlers to avoid duplicate logs
    LOGGER = logging.getLogger('PhotoMigrator')

    if LOGGER.hasHandlers():
        LOGGER.handlers.clear()

    if not skip_console:
        # Set up console handler (simple output without asctime and levelname)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        console_handler.is_console_output = True
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

    # Set the log level for the root logger
    LOGGER.setLevel(log_level)
    LOGGER.propagate = False # <-- IMPORTANTE PARA EVITAR USAR EL LOOGER RAIZ

    return LOGGER

# ==============================================================================
#                               LOGGING FUNCTIONS
# ==============================================================================
def check_color_support(log_level=logging.INFO):
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
    filtro = ThreadLevelFilter(level)
    logger.addFilter(filtro)
    try:
        yield
    finally:
        logger.removeFilter(filtro)


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