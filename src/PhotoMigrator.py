import os,sys
from pathlib import Path

# Añadir 'src/' al PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent))

# Change Working Dir before to import GlobalVariables or other Modules that depends on it.
from Globals.ChangeWorkingDir import change_working_dir
change_working_dir(change_dir=True)


import Globals.GlobalVariables as GV
import importlib
print("")
print ("Loading Tool...")
# Remove Splash image from Pyinstaller
if '_PYI_SPLASH_IPC' in os.environ and importlib.util.find_spec("pyi_splash"):
    import pyi_splash
    pyi_splash.update_text('UI Loaded ...')
    pyi_splash.close()

# Remove Splash image from Nuitka
if "NUITKA_ONEFILE_PARENT" in os.environ:
    import tempfile
    splash_filename = os.path.join(
        tempfile.gettempdir(),
        "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
    )
    with open(splash_filename, "wb") as f:
        f.write(b"READY")

    if os.path.exists(splash_filename):
        os.unlink(splash_filename)
print("Tool loaded!")
print("")

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
if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
    print(f"{GV.TAG_INFO}Valid folder detected as input: '{sys.argv[1]}'")
    print(f"{GV.TAG_INFO}Executing Google Takeout Photos Processor Feature with the provided input folder...")
    sys.argv.insert(1, "--google-takeout")

# Verificar si el script se ejecutó sin argumentos, en ese caso se pedira al usuario queue introduzca la ruta de la caroeta que contiene el Takeout a procesar
elif len(sys.argv) == 1:
    print(f"{GV.TAG_INFO}No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.")
    has_display = os.environ.get("DISPLAY") is not None or sys.platform == "win32"
    selected_folder = None

    if has_display and TKINTER_AVAILABLE:
        print(f"{GV.TAG_INFO}GUI environment detected. Opening folder selection dialog...")
        selected_folder = select_folder_gui()
    else:
        if not TKINTER_AVAILABLE and has_display:
            print(f"{GV.TAG_WARNING}Tkinter is not installed. Falling back to console input.")
        else:
            print(f"{GV.TAG_INFO}No GUI detected. Using console input.")
        print(f"Please type the full path to the Takeout folder:")
        selected_folder = input("Folder path: ").strip()

    if selected_folder and os.path.isdir(selected_folder):
        print(f"{GV.TAG_INFO}Folder selected: '{selected_folder}'")
        sys.argv.append("--google-takeout")
        sys.argv.append(selected_folder)
    else:
        print(f"{GV.TAG_ERROR}No valid folder selected. Exiting.")
        sys.exit(1)

from Utils import check_OS_and_Terminal
from GlobalVariables import LOGGER, ARGS, SCRIPT_DESCRIPTION, LOG_FOLDER_FILENAME, SCRIPT_NAME
from ExecutionModes import detect_and_run_execution_mode
from CustomLogger import print_verbose, print_debug, print_info, print_warning, print_critical

# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    # Print the Header (common for all modules)
    LOGGER.info(f"")
    LOGGER.info(f"==========================================")
    LOGGER.info(f"Sarting {SCRIPT_NAME} Process...")
    LOGGER.info(f"==========================================")
    LOGGER.info(SCRIPT_DESCRIPTION)

    # Check OS and Terminal
    check_OS_and_Terminal()

    LOGGER.info(f"Log Level         : {str(ARGS['log-level']).upper()}")
    if not ARGS['no-log-file']:
        LOGGER.info(f"Log File Location : {LOG_FOLDER_FILENAME+'.log'}")
        LOGGER.info(f"")

    # Test different LOG_LEVELS
    print_verbose   ("This is a test message with logLevel: VERBOSE")
    print_debug     ("This is a test message with logLevel: DEBUG")
    print_info      ("This is a test message with logLevel: INFO")
    print_warning   ("This is a test message with logLevel: WARNING")
    print_critical  ("This is a test message with logLevel: CRITICAL")

    # Get the execution mode and run it.
    detect_and_run_execution_mode()

if __name__ == "__main__":
    main()
