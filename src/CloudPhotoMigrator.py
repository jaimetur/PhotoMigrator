# Change Working Dir before to import GlobalVariables or other Modules that depends on it.
import ChangeWorkingDir
ChangeWorkingDir.change_working_dir(change_dir=True)

import os,sys
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

def select_folder_gui():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Select the Google Takeout folder to process")

# Verificar si el script se ejecutó con un solo argumento que sea una ruta de una carpeta existente
if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
    print(f"INFO    : Valid folder detected as input: '{sys.argv[1]}'")
    print(f"INFO    : Executing Google Takeout Photos Processor Feature with the provided input folder...")
    input_folder = sys.argv[1]
    sys.argv[1] = "--google-takeout-to-process"
    sys.argv.append(input_folder)

# Verificar si el script se ejecutó sin argumentos, en ese caso se pedira al usuario queue introduzca la ruta de la caroeta que contiene el Takeout a procesar
elif len(sys.argv) == 1:
    print("INFO    : No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.")
    has_display = os.environ.get("DISPLAY") is not None or sys.platform == "win32"
    selected_folder = None

    if has_display and TKINTER_AVAILABLE:
        print("INFO    : GUI environment detected. Opening folder selection dialog...")
        selected_folder = select_folder_gui()
    else:
        if not TKINTER_AVAILABLE and has_display:
            print("WARNING : Tkinter is not installed. Falling back to console input.")
        else:
            print("INFO    : No GUI detected. Using console input.")
        print("Please type the full path to the Takeout folder:")
        selected_folder = input("Folder path: ").strip()

    if selected_folder and os.path.isdir(selected_folder):
        print(f"INFO    : Folder selected: '{selected_folder}'")
        sys.argv.append("--google-takeout-to-process")
        sys.argv.append(selected_folder)
    else:
        print("ERROR   : No valid folder selected. Exiting.")
        sys.exit(1)

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
