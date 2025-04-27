# Change Working Dir before to import GlobalVariables or other Modules that depends on it.
import ChangeWorkingDir
ChangeWorkingDir.change_working_dir(change_dir=True)

import os,sys
# Verificar si el script se ejecutó con un solo argumento que sea una ruta de una carpeta existente
if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
    print(f"INFO    : Valid folder detected as input: '{sys.argv[1]}'")
    print(f"INFO    : Executing Google Takeout Photos Processor Feature with the provided input folder...")
    input_folder = sys.argv[1]
    sys.argv[1] = "--google-takeout-to-process"
    sys.argv.append(input_folder)

from Utils import check_OS_and_Terminal
from GlobalVariables import LOGGER, ARGS, SCRIPT_DESCRIPTION, LOG_FOLDER_FILENAME
from ExecutionModes import detect_and_run_execution_mode

# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    # Print the Header (common for all modules)
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")

    # Check OS and Terminal
    check_OS_and_Terminal()

    LOGGER.info(f"INFO    : Log Level           : '{ARGS['log-level']}'")
    if not ARGS['no-log-file']:
        LOGGER.info(f"INFO    : Log File Location   : '{LOG_FOLDER_FILENAME+'.log'}'")
        LOGGER.info("")

    # Get the execution mode and run it.
    detect_and_run_execution_mode()

if __name__ == "__main__":
    main()
