# src/PhotoMigrator.py

import os, sys
import importlib
import logging

from Core.CustomLogger import custom_log
from Core.GlobalFunctions import set_FOLDERS

# Añadir 'src/' al PYTHONPATH
src_path = os.path.dirname(__file__)
sys.path.insert(0, src_path)            # Now src is the root for imports

from Core import GlobalVariables as GV
from Utils.StandaloneUtils import change_working_dir
# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    change_working_dir(change_dir=True)

    # Load Tool while splash image is shown (only for Windows)
    print("")
    print("Loading Tool...")
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
        
    # Initialize ARGS_PARSER, LOGGER and HELP_TEXT
    # IMPORTANT: DO NOT IMPORT ANY TOOL's MODULE (except Utils.StandaloneUtils or Core.GlobalVariables) BEFORE TO RUN set_ARGS_PARSER AND set_LOGGER
    #            otherwise the ARGS, PARSER, LOGGER and HELP_TEXTS variables will be None on those imported modules.
    from Core.GlobalFunctions import set_ARGS_PARSER, set_LOGGER, set_HELP_TEXTS
    set_ARGS_PARSER()   # Need to be called first of all
    set_FOLDERS()       # Need to be called after set_ARGS_PARSER() but before set_LOGGER()
    set_LOGGER()        # Need to be called after set_FOLDERS()
    set_HELP_TEXTS()

    # Now we can safety import any other tool's module
    from Utils.GeneralUtils import check_OS_and_Terminal
    from Core.CustomLogger import custom_print
    from Core.ExecutionModes import detect_and_run_execution_mode

    # Check OS and Terminal before to import GlobalVariables or other Modules that depends on it
    check_OS_and_Terminal()

    # Verificar si el script se ejecutó con un solo argumento que sea una ruta de una carpeta existente
    if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        # print(f"{GV.TAG_INFO}Valid folder detected as input: '{sys.argv[1]}'")
        # print(f"{GV.TAG_INFO}Executing Google Takeout Photos Processor Feature with the provided input folder...")
        custom_print(f"Valid folder detected as input: '{sys.argv[1]}'", log_level=logging.INFO)
        custom_print(f"Executing Google Takeout Photos Processor Feature with the provided input folder...", log_level=logging.INFO)
        sys.argv.insert(1, "--google-takeout")

    # Verificar si el script se ejecutó sin argumentos, en ese caso se pedira al usuario queue introduzca la ruta de la caroeta que contiene el Takeout a procesar
    elif len(sys.argv) == 1:
        def select_folder_gui():
            root = tk.Tk()
            root.withdraw()
            return filedialog.askdirectory(title="Select the Google Takeout folder to process")
        try:
            import tkinter as tk
            from tkinter import filedialog
            TKINTER_AVAILABLE = True
        except ImportError:
            TKINTER_AVAILABLE = False

        # print(f"{GV.TAG_INFO}No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.")
        custom_print(f"No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.", log_level=logging.INFO)
        has_display = os.environ.get("DISPLAY") is not None or sys.platform == "win32"
        selected_folder = None

        if has_display and TKINTER_AVAILABLE:
            # print(f"{GV.TAG_INFO}GUI environment detected. Opening folder selection dialog...")
            custom_print(f"GUI environment detected. Opening folder selection dialog...", log_level=logging.INFO)
            selected_folder = select_folder_gui()
        else:
            if not TKINTER_AVAILABLE and has_display:
                # print(f"{GV.TAG_WARNING}Tkinter is not installed. Falling back to console input.")
                custom_print(f"Tkinter is not installed. Falling back to console input.", log_level=logging.WARNING)
            else:
                # print(f"{GV.TAG_INFO}No GUI detected. Using console input.")
                custom_print(f"No GUI detected. Using console input.", log_level=logging.INFO)
            # print(f"Please type the full path to the Takeout folder:")
            custom_print(f"Please type the full path to the Takeout folder:", log_level=logging.WARNING)
            selected_folder = input("Folder path: ").strip()

        if selected_folder and os.path.isdir(selected_folder):
            # print(f"{GV.TAG_INFO}Folder selected: '{selected_folder}'")
            custom_print(f"Folder selected: '{selected_folder}'", log_level=logging.INFO)
            sys.argv.append("--google-takeout")
            sys.argv.append(selected_folder)
        else:
            # print(f"{GV.TAG_ERROR}No valid folder selected. Exiting.")
            custom_print(f"No valid folder selected. Exiting.", log_level=logging.ERROR)
            sys.exit(1)


    # Test different LOG_LEVELS
    custom_print("Testing Custom Print Function for all different logLevels.")
    custom_print("All logLevel should be displayed on console:")
    custom_print("This is a test message with logLevel: VERBOSE", log_level=logging.VERBOSE)
    custom_print("This is a test message with logLevel: DEBUG", log_level=logging.DEBUG)
    custom_print("This is a test message with logLevel: INFO", log_level=logging.INFO)
    custom_print("This is a test message with logLevel: WARNING", log_level=logging.WARNING)
    custom_print("This is a test message with logLevel: ERROR", log_level=logging.ERROR)
    custom_print("This is a test message with logLevel: CRITICAL", log_level=logging.CRITICAL)
    custom_print("", log_level=logging.INFO)

    custom_log("Testing Custom Log Function for all different logLevels. ")
    custom_log("Only logLevel Higher or Equal than given by '-logLevel, --log-level' should be displayed on console and Log file:")
    custom_log("This is a test message with logLevel: VERBOSE", log_level=logging.VERBOSE)
    custom_log("This is a test message with logLevel: DEBUG", log_level=logging.DEBUG)
    custom_log("This is a test message with logLevel: INFO", log_level=logging.INFO)
    custom_log("This is a test message with logLevel: WARNING", log_level=logging.WARNING)
    custom_log("This is a test message with logLevel: ERROR", log_level=logging.ERROR)
    custom_log("This is a test message with logLevel: CRITICAL", log_level=logging.CRITICAL)
    custom_log("", log_level=logging.INFO)

    # Print the Header (common for all modules)
    GV.LOGGER.info(f"==========================================")
    GV.LOGGER.info(f"Starting {GV.SCRIPT_NAME} Tool...")
    GV.LOGGER.info(f"==========================================")
    GV.LOGGER.info(GV.SCRIPT_DESCRIPTION)
    GV.LOGGER.info(f"Tool Configured with the following Global Settings:")
    GV.LOGGER.info(f"  - Configuration File            : {GV.CONFIGURATION_FILE}")
    GV.LOGGER.info(f"  - Folder/Binary for GPTH TOOL   : {GV.FOLDERNAME_GPTH}")
    GV.LOGGER.info(f"  - Folder/Binary for EXIF TOOL   : {GV.FOLDERNAME_EXIFTOOL}")
    GV.LOGGER.info(f"  - Folder for Duplicates Outputs : {GV.FOLDERNAME_DUPLICATES_OUTPUT}")
    GV.LOGGER.info(f"  - Folder for Exiftool Outputs   : {GV.FOLDERNAME_EXIFTOOL_OUTPUT}")
    if not GV.ARGS['no-log-file']:
        GV.LOGGER.info(f"  - Folder for Logs               : {GV.FOLDERNAME_LOGS}")
        GV.LOGGER.info(f"  - Log File Location             : {GV.LOG_FOLDER_FILENAME+'.log'}")
        GV.LOGGER.info(f"  - Log Level                     : {logging.getLevelName(GV.LOG_LEVEL)} ({str(GV.LOG_LEVEL).upper()})")
    GV.LOGGER.info(f"")
    GV.LOGGER.info(f"  - SubFolder for Albums          : <OUTPUT_FOLDER>/{GV.FOLDERNAME_ALBUMS}")
    GV.LOGGER.info(f"  - SubFolder for No-Albums       : <OUTPUT_FOLDER>/{GV.FOLDERNAME_NO_ALBUMS}")
    GV.LOGGER.info(f"")

    # Get the execution mode and run it.
    detect_and_run_execution_mode()

if __name__ == "__main__":
    main()
