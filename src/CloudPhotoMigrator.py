import os,sys
from Utils import check_OS_and_Terminal
from datetime import datetime
from HelpTexts import set_help_texts
from ParseArgs import parse_arguments
from LoggerConfig import log_setup
from ExecutionModes import detect_and_run_execution_mode

# Script version & date
global TIMESTAMP, LOG_FOLDER_FILENAME, SCRIPT_NAME, SCRIPT_VERSION, SCRIPT_DATE, SCRIPT_NAME_VERSION, SCRIPT_DESCRIPTION, HELP_TEXTS, START_TIME, OUTPUT_TAKEOUT_FOLDER, DEPRIORITIZE_FOLDERS_PATTERNS, ARGS, PARSER

SCRIPT_NAME         = "CloudPhotoMigrator"
SCRIPT_VERSION      = "v3.0.0-alpha"
SCRIPT_DATE         = "2025-02-03"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Multi-Platform/Multi-Arch toot designed to Interact and Manage different Photo Cloud 
Services such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

(c) 2024-2025 by Jaime Tur (@jaimetur)
"""

# -------------------------------------------------------------
# Configure the LOGGER
# -------------------------------------------------------------
def log_init():
    global LOGGER
    global TIMESTAMP
    global LOG_FOLDER_FILENAME
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    log_filename=f"{script_name}_{TIMESTAMP}"
    log_folder="Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)

# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def main():
    global HELP_TEXTS, START_TIME, OUTPUT_TAKEOUT_FOLDER, DEPRIORITIZE_FOLDERS_PATTERNS, ARGS

    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    # Set HELP Texts
    HELP_TEXTS = set_help_texts()

    # Obtain Input Arguments Parsed
    ARGS = parse_arguments()

    # Initialize the logger.
    log_init()

    # List of Folder to Desprioritize when looking for duplicates.
    DEPRIORITIZE_FOLDERS_PATTERNS = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*Others', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

    # Create timestamp, start_time and define OUTPUT_TAKEOUT_FOLDER
    START_TIME = datetime.now()
    OUTPUT_TAKEOUT_FOLDER = f"{ARGS['google-input-takeout-folder']}_{ARGS['google-output-folder-suFldfix']}_{TIMESTAMP}"

    # Print the Header (common for all modules)
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")

    # Check OS and Terminal
    check_OS_and_Terminal()

    # Get the execution mode and run it.
    detect_and_run_execution_mode()


if __name__ == "__main__":
    # Verificar si el script se ejecutó sin argumentos
    # if len(sys.argv) == 1:
    #     # Agregar argumento predeterminado
    #     sys.argv.append("-z")
    #     sys.argv.append("Zip_folder")
    #     print(f"INFO: No argument detected. Using default value '{sys.argv[2]}' for <ZIP_FOLDER>'.")
    main()
