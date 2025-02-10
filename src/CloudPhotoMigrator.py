from GLOBALS import LOGGER, ARGS, SCRIPT_DESCRIPTION, LOG_FOLDER_FILENAME
import os,sys
from Utils import check_OS_and_Terminal
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
    if not ARGS['no-log-file']:
        LOGGER.info(f"INFO    : Log File Location: '{LOG_FOLDER_FILENAME+'.log'}'")
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

    # Definir la ruta de trabajo deseada
    target_directory = r"R:\jaimetur\CloudPhotoMigrator"
    # Verificar si la carpeta existe y cambiar a ella si existe
    if os.path.exists(target_directory) and os.path.isdir(target_directory):
        os.chdir(target_directory)
        print(f"Directorio cambiado a: {os.getcwd()}")
        current_directory = os.getcwd()
        print(current_directory)
    main()
