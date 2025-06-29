# Module to define Globals Variables accesible to all other modules
import logging
import os
import sys

import Core.GlobalVariables as GV
from Core.ArgsParser import parse_arguments, checkArgs
from Core.CustomLogger import log_setup
from Core.GlobalVariables import FOLDERNAME_LOGS
from Core.HelpTexts import set_help_texts
from Utils.StandaloneUtils import resolve_path


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
    GV.FOLDERNAME_ALBUMS            = GV.ARGS.get('foldername-albums')                          or GV.FOLDERNAME_ALBUMS
    GV.FOLDERNAME_NO_ALBUMS         = GV.ARGS.get('foldername-no-albums')                       or GV.FOLDERNAME_NO_ALBUMS
    GV.CONFIGURATION_FILE           = resolve_path(GV.ARGS.get('configuration-file'))           or resolve_path(GV.CONFIGURATION_FILE)
    GV.FOLDERNAME_GPTH              = resolve_path(GV.ARGS.get('exec-gpth-tool'))               or resolve_path(GV.FOLDERNAME_GPTH)
    GV.FOLDERNAME_EXIFTOOL          = resolve_path(GV.ARGS.get('exec-exif-tool'))               or resolve_path(GV.FOLDERNAME_EXIFTOOL)
    GV.FOLDERNAME_EXIFTOOL_OUTPUT   = resolve_path(GV.ARGS.get('foldername-exiftool-output'))   or resolve_path(GV.FOLDERNAME_EXIFTOOL_OUTPUT)
    GV.FOLDERNAME_DUPLICATES_OUTPUT = resolve_path(GV.ARGS.get('foldername-duplicates-output')) or resolve_path(GV.FOLDERNAME_DUPLICATES_OUTPUT)
    GV.FOLDERNAME_LOGS              = resolve_path(GV.ARGS.get('foldername-logs'))              or resolve_path(GV.FOLDERNAME_LOGS)


def set_LOGGER():
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    current_directory = os.getcwd()
    log_folder = resolve_path(GV.FOLDERNAME_LOGS)
    log_filename = f"{script_name}_{GV.TIMESTAMP}"
    GV.LOG_FILENAME = os.path.join(current_directory, log_folder, log_filename)

    # 1) Inicializas el logger con el nivel por defecto
    GV.LOGGER = log_setup(
        log_folder=log_folder,
        log_filename=log_filename,
        log_level=GV.LOG_LEVEL_MIN,
        skip_logfile=False,
        skip_console=False,
        format=GV.ARGS['log-format']
    )

    # 2) Mapeo explícito de niveles soportados
    level_str = GV.ARGS['log-level'].lower()
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

def set_HELP_TEXTS():
    GV.HELP_TEXTS  = set_help_texts()














