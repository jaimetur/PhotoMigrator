# LoggerConfig.py
import os
import logging

LOGGER = None  # Variable interna para el Singleton

def log_setup(log_folder="Logs", log_filename="execution_log", skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
    """
    Configures logger to a log file and console simultaneously.
    The console messages do not include timestamps.
    """
    global LOGGER

    # Crear la carpeta de logs si no existe
    os.makedirs(log_folder, exist_ok=True)
    log_level = logging.INFO

    # Clear existing handlers to avoid duplicate logs
    LOGGER = logging.getLogger()
    if LOGGER.hasHandlers():
        LOGGER.handlers.clear()
    if not skip_console:
        # Set up console handler (simple output without timestamps)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        LOGGER.addHandler(console_handler)
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
                fmt='%(asctime)s [%(levelname)-12s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler_detailed.setFormatter(detailed_format)
            LOGGER.addHandler(file_handler_detailed)
        if plain_log:
            log_file = os.path.join(log_folder, 'plain_' + log_filename + '.txt')
            file_handler_plain = logging.FileHandler(log_file, encoding="utf-8")
            file_handler_plain.setLevel(log_level)
            # Formato estándar para el manejador de ficheros plano
            file_formatter = logging.Formatter('%(message)s')
            file_handler_plain.setFormatter(file_formatter)
            LOGGER.addHandler(file_handler_plain)
    # Set the log level for the root logger
    LOGGER.setLevel(log_level)
    return LOGGER