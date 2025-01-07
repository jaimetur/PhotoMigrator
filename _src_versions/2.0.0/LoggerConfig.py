# LoggerConfig.py
import os
import logging

LOGGER = None  # Variable interna para el Singleton

def log_setup(log_folder="Logs", log_filename="execution_log", skip_logfile=False, skip_console=False, detail_log=True, plain_log=False):
    """
    Configura el logger como Singleton con los argumentos proporcionados.
    """
    global LOGGER

    if logger is not None:
        logger = logger  # Sincroniza la variable global si ya está configurado
        return logger

    # Crear la carpeta de logs si no existe
    os.makedirs(log_folder, exist_ok=True)
    log_level = logging.INFO

    logger = logging.getLogger("my_application_logger")

    # Limpia manejadores existentes para evitar duplicados
    if logger.hasHandlers():
        logger.handlers.clear()

    # Configuración de manejadores
    if not skip_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if not skip_logfile:
        log_file = os.path.join(log_folder, log_filename + '.log')
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(log_level)
    logger.info("INFO: Logger initialized successfully.")

    return logger
