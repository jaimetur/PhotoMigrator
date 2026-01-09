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
    Enable VERBOSE level in the standard `logging` module, allowing:
    - logging.VERBOSE to expose the numeric level.
    - logger.verbose(...) to log messages at that level.
    """
    # 0) Avoid redefining if it is already enabled
    if hasattr(logging, "VERBOSE"):
        return

    # 1) Register the level name
    logging.addLevelName(level_num, "VERBOSE")

    # 2) Add as attribute to logging module
    logging.VERBOSE = level_num

    # 3) Define .verbose() method
    def verbose(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    # 4) Inject the method into logging.Logger so it is available for all loggers
    logging.Logger.verbose = verbose
#------------------------------------------------------------------
# Execute at import time to enable the VERBOSE level from the beginning of the tool
enable_verbose_level()

#------------------------------------------------------------------
# Standard helper to send any message to GV.LOGGER with a specific log_level
def custom_log(*args, log_level=logging.INFO, **kwargs):
    message = " ".join(str(a) for a in args)
    GV.LOGGER.log(log_level, message, **kwargs)
#------------------------------------------------------------------


# Class to downgrade from INFO to DEBUG/WARNING/ERROR when certain tag is detected in the message
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
        # Only intercept records emitted with logger.info()
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
        # Only affects the current thread
        if threading.get_ident() == self.thread_id:
            return record.levelno >= self.level
        return True  # other threads unaffected


# Custom formatter for console messages (adds ANSI colors based on log level)
class CustomConsoleFormatter(logging.Formatter):
    def format(self, record):
        # Keep original message to avoid mutating record.msg globally
        original_msg = record.msg
        formatted_message = super().format(record)
        # Restore original message
        record.msg = original_msg

        color_support = check_color_support()
        if color_support:
            # Custom ANSI color formatting
            COLORS = {
                "VERBOSE": Fore.CYAN,
                "DEBUG": Fore.LIGHTCYAN_EX,
                "INFO": Fore.LIGHTWHITE_EX,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED,
                "CRITICAL": Fore.MAGENTA,
            }
            # Apply color by logging level
            color = COLORS.get(record.levelname, "")
            formatted_message = f"{color}{formatted_message}{Style.RESET_ALL}"
        return formatted_message


# Custom formatter for plain txt file handler (no colors)
class CustomTxtFormatter(logging.Formatter):
    def format(self, record):
        # Keep original message to avoid mutating record.msg globally
        original_msg = record.msg
        formatted_message = super().format(record)
        # Restore original message
        record.msg = original_msg
        return formatted_message


# Custom formatter for .log file handler (no colors; removes "INFO : ", "WARNING : ", etc. prefixes)
class CustomLogFormatter(logging.Formatter):
    def format(self, record):
        # Keep original message to avoid mutating record.msg globally
        original_msg = record.msg

        # Remove the tag prefixes depending on the log level
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

        # Restore original message
        record.msg = original_msg
        return formatted_message


class CustomInMemoryLogHandler(logging.Handler):
    """
    Store logging records into a queue/list in memory.
    Then `start_dashboard` can read from that queue to display logs on a live dashboard.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue  # shared queue to store messages

    def emit(self, record):
        # Format message
        msg = self.format(record)
        # Store into the queue
        self.log_queue.put(msg)
        # Store into list (alternative)
        # self.log_queue.append(msg)


class LoggerStream:
    """Intercept stdout and stderr to redirect them to GV.LOGGER."""
    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())  # send to GV.LOGGER

    def flush(self):
        """No operation required, but defined for compatibility."""
        pass

    def isatty(self):
        """Avoid terminal detection errors."""
        return False


# 🚀 Class to capture `print()` and `stderr` without affecting `rich.Live`
class LoggerCapture:
    """Capture stdout and stderr and redirect them to GV.LOGGER without affecting Rich.Live."""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip():
            # Store into GV.LOGGER without printing to the screen
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass  # not required for logging


def log_setup(log_folder="Logs", log_filename=None, log_level=logging.INFO, skip_logfile=False, skip_console=False, format='log'):
    """
    Configure a logger to write to console and to log files simultaneously.
    Console messages do not include timestamps.
    """

    if not log_filename:
        log_filename = GV.TOOL_NAME

    # Create logs folder if it does not exist
    # Resolve log_folder to an absolute path
    log_folder = resolve_external_path(log_folder)
    os.makedirs(log_folder, exist_ok=True)

    # Clear existing handlers to avoid duplicate logs
    GV.LOGGER = logging.getLogger('PhotoMigrator')

    if GV.LOGGER.hasHandlers():
        GV.LOGGER.handlers.clear()

    if not skip_console:
        # Set up console handler (simple output without asctime)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            CustomConsoleFormatter(
                fmt="%(levelname)-8s: %(message)s",
                datefmt="%H:%M:%S"
            )
        )
        # Add filter to downgrade from INFO to DEBUG/WARNING/ERROR when tag chains are detected
        console_handler.addFilter(ChangeLevelFilter())
        console_handler.is_console_output = True
        GV.LOGGER.addHandler(console_handler)

    if not skip_logfile:
        if format.lower() in ['log', 'all']:
            # Set up .log file handler (detailed output with asctime and levelname)
            log_file = os.path.join(log_folder, log_filename + '.log')
            file_handler_detailed = logging.FileHandler(log_file, encoding="utf-8-sig")
            file_handler_detailed.setLevel(log_level)
            file_handler_detailed.setFormatter(
                logging.Formatter(
                    fmt='%(asctime)s [%(levelname)-8s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
            file_handler_detailed.addFilter(ChangeLevelFilter())
            GV.LOGGER.addHandler(file_handler_detailed)

        elif format.lower() in ['txt', 'all']:
            # Set up .txt file handler (plain output, no timestamp/level)
            log_file = os.path.join(log_folder, log_filename + '.txt')
            file_handler_plain = logging.FileHandler(log_file, encoding="utf-8-sig")
            file_handler_plain.setLevel(log_level)
            file_handler_plain.setFormatter(
                logging.Formatter(
                    fmt='%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
            file_handler_plain.addFilter(ChangeLevelFilter())
            GV.LOGGER.addHandler(file_handler_plain)

        else:
            # Unknown format fallback (do not crash, just notify)
            custom_print(
                f"Unknown format '{format}' for Logger. Please select a valid format between: ['log', 'txt', 'all].",
                log_level=logging.INFO
            )

    # Set the log level for the logger
    GV.LOGGER.setLevel(log_level)
    GV.LOGGER.propagate = False  # IMPORTANT: avoid using the root logger

    # Install a global thread exception hook
    def thread_exc_hook(args):
        GV.LOGGER.setLevel(logging.INFO)
        GV.LOGGER.error(
            f"Uncaught exception in thread {args.thread.name}: {args.exc_value}",
            exc_info=args.exc_value
        )

    threading.excepthook = thread_exc_hook

    return GV.LOGGER


# ==============================================================================
#                               LOGGING FUNCTIONS
# ==============================================================================
def check_color_support(log_level=None):
    """Detect whether the current terminal supports ANSI colors."""
    if sys.stdout.isatty():  # Check if this is an interactive terminal
        term = os.getenv("TERM", "")
        if term in ("dumb", "linux", "xterm-mono"):  # Terminals without colors
            return False
        return True
    return False


def get_logger_filename(logger):
    """Return the logfile path used by a logger (first FileHandler found), or empty string if none."""
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return ""


# Create context to temporarily disable console output
@contextmanager
def suppress_console_output_temporarily(logger):
    """
    Temporarily remove handlers marked with `.is_console_output = True` from the logger.
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


# Create a context to temporarily change the logger level for the current thread only
@contextmanager
def set_log_level(logger, level):
    """
    Context manager that temporarily enforces a specific logging level for the CURRENT THREAD ONLY.

    This function installs a thread-specific filter on the given logger, ensuring that the chosen
    logging level affects exclusively the thread executing this context, without modifying the
    global logger level. It is thread-safe and suitable for both single-threaded and multi-threaded
    environments.

    Args:
        logger (logging.Logger): Logger instance to which the temporary level applies.
        level (int): Logging level to apply temporarily (e.g., logging.INFO, logging.ERROR).

    Usage example:
        with set_log_level(LOGGER, logging.ERROR):
            LOGGER.info("This message will NOT be shown in this thread.")
            LOGGER.error("This message will be shown in this thread.")
        # Outside the context, the logger reverts to its original behavior.

    Important:
        - This context manager does NOT change the global logger level.
        - It only affects log records emitted from the thread executing this context.
        - After exiting the context, the original behavior is restored automatically.
    """
    if logger is None:
        yield  # Do nothing if logger is None
        return

    # If no level has been passed (or level=None), use the global level defined by user arguments
    if not level:
        level = GV.LOG_LEVEL

    filtro = ThreadLevelFilter(level)
    logger.addFilter(filtro)
    try:
        yield
    finally:
        logger.removeFilter(filtro)


# Create a context to temporarily change the logger level and all handlers levels
@contextmanager
def set_log_level_simple(logger: logging.Logger, level: int):
    # If no level has been passed (or level=None), use the global level defined by user arguments
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
    Create a new logger with the same level and handlers as the original one,
    avoiding duplicated messages.

    Args:
        original_logger (logging.Logger): The original logger.
        new_name (str): Optional name for the new logger.

    Returns:
        logging.Logger: An independent logger instance with the same handlers.
    """
    new_logger_name = new_name if new_name else f"{original_logger.name}_copy"
    new_logger = logging.getLogger(new_logger_name)

    # Copy log level
    new_logger.setLevel(original_logger.level)

    # Avoid adding duplicate handlers
    if not new_logger.hasHandlers():
        for handler in original_logger.handlers:
            # Reuse the same handler reference (no deep copy)
            new_logger.addHandler(handler)

    return new_logger
