import os,sys

def change_working_dir():
    """ Definir la ruta de trabajo deseada """
    WORKING_DIR = r"R:\jaimetur\CloudPhotoMigrator"
    # Verificar si la carpeta existe y cambiar a ella si existe
    if os.path.exists(WORKING_DIR) and os.path.isdir(WORKING_DIR):
        os.chdir(WORKING_DIR)
        current_directory = os.getcwd()
        print(f"INFO    : Directorio cambiado a: {os.getcwd()}")

# Change Working Dir before to import GlobalVariables or other Modules that depends on it.
change_working_dir()

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
    # Verificar si el script se ejecutó sin argumentos
    # if len(sys.argv) == 1:
    #     # Agregar argumento predeterminado
    #     sys.argv.append("-z")
    #     sys.argv.append("Zip_folder")
    #     print(f"INFO    : No argument detected. Using default value '{sys.argv[2]}' for <ZIP_FOLDER>'.")
    main()
