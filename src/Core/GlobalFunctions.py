# Module to define Globals Variables accesible to all other modules
import logging
import os
import sys

import Core.GlobalVariables as GV
from Core.ArgsParser import parse_arguments, checkArgs
from Core.CustomLogger import log_setup
from Core.HelpTexts import set_help_texts
from Utils.StandaloneUtils import resolve_external_path, resolve_internal_path


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# FUNCTIONS TO INITIALIZE GLOBAL LOGGER AND GLOBAL ARGS TO BE USED BY OTHER MODULES
# Since we cannot import other modules directly on the GlobalVariables.py module to avoid circular references, we need to initialize those variables using independent functions.
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def set_ARGS_PARSER():
    args, parser = parse_arguments()
    args = checkArgs(args, parser)
    GV.ARGS = args
    GV.PARSER = parser

def set_FOLDERS():
    GV.FOLDERNAME_ALBUMS            = GV.ARGS.get('foldername-albums')                                  or GV.FOLDERNAME_ALBUMS
    GV.FOLDERNAME_NO_ALBUMS         = GV.ARGS.get('foldername-no-albums')                               or GV.FOLDERNAME_NO_ALBUMS
    GV.CONFIGURATION_FILE           = resolve_external_path(GV.ARGS.get('configuration-file')           or GV.CONFIGURATION_FILE)
    GV.FOLDERNAME_EXIFTOOL_OUTPUT   = resolve_external_path(GV.ARGS.get('foldername-exiftool-output')   or GV.FOLDERNAME_EXIFTOOL_OUTPUT)
    GV.FOLDERNAME_DUPLICATES_OUTPUT = resolve_external_path(GV.ARGS.get('foldername-duplicates-output') or GV.FOLDERNAME_DUPLICATES_OUTPUT)
    GV.FOLDERNAME_LOGS              = resolve_external_path(GV.ARGS.get('foldername-logs')              or GV.FOLDERNAME_LOGS)
    # GV.FOLDERNAME_GPTH              = resolve_external_path(GV.ARGS.get('exec-gpth-tool'))                or resolve_internal_path(GV.FOLDERNAME_GPTH)
    # GV.FOLDERNAME_EXIFTOOL          = resolve_external_path(GV.ARGS.get('exec-exif-tool'))                or resolve_internal_path(GV.FOLDERNAME_EXIFTOOL)
    # Now resolve GV.FOLDERNAME_GPTH and GV.FOLDERNAME_EXIFTOOL depending on if the user passed them as argument or not. If not we need to resolve using resolve_internal_path to find it within the binary file.
    gpth_arg = GV.ARGS.get('exec-gpth-tool') or ''
    exif_arg = GV.ARGS.get('exec-exif-tool') or ''
    gpth_resolved = resolve_external_path(gpth_arg) if gpth_arg.strip() else None
    exif_resolved = resolve_external_path(exif_arg) if exif_arg.strip() else None
    GV.FOLDERNAME_GPTH = gpth_resolved if gpth_resolved and os.path.exists(gpth_resolved) else resolve_internal_path(GV.FOLDERNAME_GPTH)
    GV.FOLDERNAME_EXIFTOOL = exif_resolved if exif_resolved and os.path.exists(exif_resolved) else resolve_internal_path(GV.FOLDERNAME_EXIFTOOL)


def set_LOGGER(level_str=None):
    tool_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    current_directory = os.getcwd()
    log_folder = resolve_external_path(GV.FOLDERNAME_LOGS)
    log_filename = f"{GV.TOOL_NAME}_{GV.TOOL_VERSION}_{GV.TIMESTAMP}"
    GV.LOG_FILENAME = os.path.join(current_directory, log_folder, log_filename)

    # 1) Inicializas el logger con el nivel por defecto
    GV.LOGGER = log_setup(
        log_folder=log_folder,
        log_filename=log_filename,
        log_level=GV.LOG_LEVEL_MIN,
        skip_logfile=False,
        skip_console=False,
        format=(GV.ARGS.get('log-format') if GV.ARGS else 'log')
    )

    # Determina el nivel de log: prioridad al argumento recibido
    if level_str is None:
        level_str = GV.ARGS.get('log-level', 'info') if GV.ARGS else 'info'
    level_str = level_str.lower()

    # 2) Mapeo explícito de niveles soportados
    level_mapping = {
        'verbose'   : GV.VERBOSE_LEVEL_NUM,
        'debug'     : logging.DEBUG,
        'info'      : logging.INFO,
        'warning'   : logging.WARNING,
        'error'     : logging.ERROR,
        'critical'  : logging.CRITICAL,
    }

    if level_str in level_mapping:
        new_level = level_mapping[level_str]
        GV.LOG_LEVEL = new_level

        # Cambiamos el nivel del logger
        GV.LOGGER.setLevel(new_level)
        # Y de cada handler
        for handler in GV.LOGGER.handlers:
            handler.setLevel(new_level)
        GV.LOGGER.info(f"Logging level changed to {level_str.upper()}")
    else:
        GV.LOGGER.warning(f"Unknown Logging level: {GV.ARGS['log-level']}")
    return GV.LOGGER

def set_HELP_TEXTS():
    GV.HELP_TEXTS  = set_help_texts()


