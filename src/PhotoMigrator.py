# src/PhotoMigrator.py

import importlib
import logging
import os
import sys

from Core.CustomLogger import custom_log
from Core.GlobalFunctions import set_FOLDERS

# Añadir 'src/' al PYTHONPATH
src_path = os.path.dirname(__file__)
sys.path.insert(0, src_path)            # Now src is the root for imports

from Core import GlobalVariables as GV
from Utils.StandaloneUtils import change_working_dir, custom_print


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

    # Check if the tool was executed with only a valid path as argument or without arguments
    # IMPORTANT: This need to be done before call set_ARGS_PARSER().
    pre_parse_args()

    # Initialize ARGS_PARSER, LOGGER and HELP_TEXT
    # IMPORTANT: DO NOT IMPORT ANY TOOL's MODULE (except Utils.StandaloneUtils or Core.GlobalVariables) BEFORE TO RUN set_ARGS_PARSER AND set_LOGGER
    #            otherwise the ARGS, PARSER, LOGGER and HELP_TEXTS variables will be None on those imported modules.
    from Core.GlobalFunctions import set_ARGS_PARSER, set_LOGGER, set_HELP_TEXTS
    custom_print(f"Setting ARGS...", log_level=logging.INFO)
    set_ARGS_PARSER()   # Need to be called first of all
    custom_print(f"Setting Global Folders...", log_level=logging.INFO)
    set_FOLDERS()       # Need to be called after set_ARGS_PARSER() but before set_LOGGER()
    custom_print(f"Setting Global LOGGER...", log_level=logging.INFO)
    set_LOGGER()        # Need to be called after set_FOLDERS()
    custom_print(f"Setting Global HELP_TEXTS...", log_level=logging.INFO)
    set_HELP_TEXTS()

    # Now we can safety import any other tool's module
    from Utils.GeneralUtils import check_OS_and_Terminal
    from Core.ExecutionModes import detect_and_run_execution_mode

    # Check OS and Terminal before to import GlobalVariables or other Modules that depends on it
    check_OS_and_Terminal()

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

    # Print the command used to run the tool
    command = ' '.join(sys.argv)
    custom_log(f"▶️ Command used to run this tool:", log_level=logging.INFO)
    custom_log(f"▶️ {command}", log_level=logging.INFO)

    # Print the Header (common for all modules)
    GV.LOGGER.info(f"\n{GV.BANNER}\n{GV.TOOL_DESCRIPTION}")

    GV.LOGGER.info(f"==========================================")
    GV.LOGGER.info(f"Starting {GV.TOOL_NAME} Tool...")
    GV.LOGGER.info(f"==========================================")
    GV.LOGGER.info(f"Tool Configured with the following Global Settings:")
    GV.LOGGER.info(f"  - Project Root                  : {GV.PROJECT_ROOT}")
    GV.LOGGER.info(f"  - Configuration File            : {GV.CONFIGURATION_FILE}")
    GV.LOGGER.info(f"  - Folder/Binary for GPTH TOOL   : {GV.FOLDERNAME_GPTH}")
    GV.LOGGER.info(f"  - Folder/Binary for EXIF TOOL   : {GV.FOLDERNAME_EXIFTOOL}")
    GV.LOGGER.info(f"  - Folder for Duplicates Outputs : {GV.FOLDERNAME_DUPLICATES_OUTPUT}")
    GV.LOGGER.info(f"  - Folder for Exiftool Outputs   : {GV.FOLDERNAME_EXTRACTED_DATES}")
    if not GV.ARGS['no-log-file']:
        GV.LOGGER.info(f"  - Folder for Logs               : {GV.FOLDERNAME_LOGS}")
        GV.LOGGER.info(f"  - Log File Location             : {GV.LOG_FILENAME + '.log'}")
        GV.LOGGER.info(f"  - Log Level                     : {logging.getLevelName(GV.LOG_LEVEL)} ({str(GV.LOG_LEVEL).upper()})")
    GV.LOGGER.info(f"  - SubFolder for Albums          : <OUTPUT_FOLDER>/{GV.FOLDERNAME_ALBUMS}")
    GV.LOGGER.info(f"  - SubFolder for No-Albums       : <OUTPUT_FOLDER>/{GV.FOLDERNAME_NO_ALBUMS}")
    GV.LOGGER.info(f"")

    # Get the execution mode and run it.
    detect_and_run_execution_mode()


# def pre_parse_args():
#     # Verificar si el script se ejecutó con un solo argumento que sea una ruta de una carpeta existente
#     if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
#         custom_print(f"Valid folder detected as input: '{sys.argv[1]}'", log_level=logging.INFO)
#         custom_print(f"Executing Google Takeout Photos Processor Feature with the provided input folder...", log_level=logging.INFO)
#         sys.argv.insert(1, "--google-takeout")
#
#     # Verificar si el script se ejecutó sin argumentos, en ese caso se pedirá al usuario queue introduzca la ruta de la carpeta que contiene el Takeout a procesar
#     elif len(sys.argv) == 1:
#         def select_folder_gui():
#             root = tk.Tk()
#             root.withdraw()
#             return filedialog.askdirectory(title="Select the Google Takeout folder to process")
#         try:
#             import tkinter as tk
#             from tkinter import filedialog
#             TKINTER_AVAILABLE = True
#         except ImportError:
#             TKINTER_AVAILABLE = False
#
#         custom_print(f"No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.", log_level=logging.INFO)
#         has_display = os.environ.get("DISPLAY") is not None or sys.platform == "win32"
#
#         if has_display and TKINTER_AVAILABLE:
#             custom_print(f"GUI environment detected. Opening folder selection dialog...", log_level=logging.INFO)
#             custom_print(f"Please, Select the Google Takeout folder to process...", log_level=logging.INFO)
#             selected_folder = select_folder_gui()
#         else:
#             if not TKINTER_AVAILABLE and has_display:
#                 custom_print(f"Tkinter is not installed. Falling back to console input.", log_level=logging.WARNING)
#             else:
#                 custom_print(f"No GUI detected. Using console input.", log_level=logging.INFO)
#             custom_print(f"Please type the full path to the Takeout folder to process:", log_level=logging.WARNING)
#             selected_folder = input("Folder path: ").strip()
#
#         if selected_folder and os.path.isdir(selected_folder):
#             custom_print(f"Folder selected: '{selected_folder}'", log_level=logging.INFO)
#             sys.argv.append("--google-takeout")
#             sys.argv.append(selected_folder)
#         else:
#             custom_print(f"No valid folder selected. Exiting.", log_level=logging.ERROR)
#             sys.exit(1)

def pre_parse_args():
    def has_display():
        # Detect if a graphical environment is available
        return os.environ.get("DISPLAY") or sys.platform.startswith("win") or sys.platform == "darwin"

    def launch_gui_config(folder_already_provided, default_folder=""):
        import tkinter as tk
        from tkinter import ttk, filedialog

        class GoogleConfigPanel:
            def __init__(self, master, default_folder):
                self.master = master
                master.title("Google Takeout Fixing Configuration")
                # self.master.geometry("700x600")  # Wider window

                # -------- Folder Selection --------
                self.takeout_folder = tk.StringVar(value=default_folder)

                folder_frame = tk.Frame(master)
                folder_frame.pack(anchor="w", padx=20, pady=(10, 4))

                row_folder = tk.Frame(folder_frame)
                row_folder.pack(anchor="w", pady=2)
                tk.Label(row_folder, text="Takeout Folder:", width=28, anchor="w").pack(side="left")
                self.folder_entry = tk.Entry(row_folder, textvariable=self.takeout_folder, width=110)
                self.folder_entry.pack(side="left")
                tk.Button(row_folder, text="Select Folder", command=self.browse_folder).pack(side="left", padx=8)

                self.takeout_folder.trace_add("write", self.validate_folder)

                # -------- Output Suffix --------
                suffix_frame = tk.Frame(master)
                suffix_frame.pack(anchor="w", pady=(10, 4), padx=20)
                self.output_suffix = tk.StringVar(value="processed")
                row_suffix = tk.Frame(suffix_frame)
                row_suffix.pack(anchor="w", pady=2)
                tk.Label(row_suffix, text="Output folder suffix:", width=28, anchor="w").pack(side="left")
                tk.Entry(row_suffix, textvariable=self.output_suffix, width=21).pack(side="left")
                tk.Label(row_suffix, text=" " * 2, font=("Courier", 10)).pack(side="left")  # padding left
                tk.Label(row_suffix, text="Suffix to append to processed folder", anchor="w", font=("Courier", 10)).pack(side="left", padx=2)

                # -------- Dropdowns for Folder Structures --------
                options = ["flatten", "year", "year/month", "year-month"]
                self.albums_structure = tk.StringVar(value="flatten")
                self.no_albums_structure = tk.StringVar(value="year/month")
                structure_frame = tk.Frame(master)
                structure_frame.pack(anchor="w", pady=(10, 4), padx=20)
                row1 = tk.Frame(structure_frame)
                row1.pack(anchor="w", pady=2)
                tk.Label(row1, text="Albums folder structure:", width=28, anchor="w").pack(side="left")
                ttk.Combobox(row1, textvariable=self.albums_structure, values=options, state="readonly", width=18).pack(side="left")
                tk.Label(row1, text=" " * 2, font=("Courier", 10)).pack(side="left")  # align with flag label width
                tk.Label(row1, text="Structure for albums folder", anchor="w", font=("Courier", 10)).pack(side="left", padx=2)

                row2 = tk.Frame(structure_frame)
                row2.pack(anchor="w", pady=2)
                tk.Label(row2, text="No-albums folder structure:", width=28, anchor="w").pack(side="left")
                ttk.Combobox(row2, textvariable=self.no_albums_structure, values=options, state="readonly", width=18).pack(side="left")
                tk.Label(row2, text=" " * 2, font=("Courier", 10)).pack(side="left")  # fine-tune alignment
                tk.Label(row2, text="Structure for no-albums folder", anchor="w", font=("Courier", 10)).pack(side="left", padx=2)

                # -------- Flags with Descriptions --------
                self.flags = {
                    "--google-ignore-check-structure": ("Ignore Takeout structure checking", tk.BooleanVar()),
                    "--google-no-symbolic-albums": ("Duplicate assets instead of create symlink for albums", tk.BooleanVar()),
                    "--google-remove-duplicates-files": ("Remove duplicate assets (only useful if before flag is unchecked", tk.BooleanVar()),
                    "--google-rename-albums-folders": ("Rename albums based on its assets dates (useful for a better organization)", tk.BooleanVar()),
                    "--google-skip-extras-files": ("Skip Google-edited/effect files", tk.BooleanVar()),
                    "--google-skip-move-albums": ("Do not move albums to ALBUMS_FOLDER", tk.BooleanVar()),
                    "--google-skip-gpth-tool": ("Skip GPTH tool (only recommended for testing purposses)", tk.BooleanVar()),
                    "--google-skip-preprocess": ("Skip pre-processing step (not recommended)", tk.BooleanVar()),
                    "--google-skip-postprocess": ("Skip post-processing step (not recommended)", tk.BooleanVar()),
                    "--google-keep-takeout-folder": ("Keep untouched Takeout copy (uses double disk space)", tk.BooleanVar()),
                }

                tk.Label(master, text="Flags:").pack(anchor="w", pady=(8, 0))
                flags_frame = tk.Frame(master)
                flags_frame.pack(anchor="w", padx=20)

                for flag, (desc, var) in self.flags.items():
                    row = tk.Frame(flags_frame)
                    row.pack(anchor="w", pady=1)
                    tk.Checkbutton(row, variable=var).pack(side="left")
                    tk.Label(row, text=f"{flag:<40} {desc}", anchor="w", justify="left", font=("Courier", 10)).pack(side="left")

                # -------- Boolean Options --------
                self.show_info = tk.BooleanVar(value=True)
                self.show_errors = tk.BooleanVar(value=True)
                # tk.Checkbutton(master, text="--show-gpth-info", variable=self.show_info).pack(anchor="w")
                # tk.Checkbutton(master, text="--show-gpth-errors", variable=self.show_errors).pack(anchor="w")
                info_frame = tk.Frame(master)
                info_frame.pack(anchor="w", pady=(8, 0), padx=20)

                row1 = tk.Frame(info_frame)
                row1.pack(anchor="w", pady=1)
                tk.Checkbutton(row1, variable=self.show_info).pack(side="left")
                tk.Label(row1, text=f"{'--show-gpth-info':<40} Show GPTH progress messages", anchor="w", justify="left", font=("Courier", 10)).pack(side="left")

                row2 = tk.Frame(info_frame)
                row2.pack(anchor="w", pady=1)
                tk.Checkbutton(row2, variable=self.show_errors).pack(side="left")
                tk.Label(row2, text=f"{'--show-gpth-errors':<40} Show GPTH error messages", anchor="w", justify="left", font=("Courier", 10)).pack(side="left")

                # -------- Buttons --------
                btn_frame = tk.Frame(master)
                btn_frame.pack(pady=12)
                tk.Button(btn_frame, text="Accept", command=self.submit, width=12).pack(side="left", padx=10)
                tk.Button(btn_frame, text="Cancel", command=self.cancel, width=12).pack(side="left", padx=10)

            def browse_folder(self):
                folder = filedialog.askdirectory()
                if folder:
                    self.takeout_folder.set(folder)

            def submit(self):
                # Takeout folder is always required
                folder = self.takeout_folder.get().strip()
                if not folder or not os.path.isdir(folder):
                    custom_print(f"No valid folder selected. Exiting.", log_level=logging.ERROR)
                    sys.exit(1)
                if not folder_already_provided:
                    sys.argv += ["--google-takeout", folder]

                # Only add suffix if it's not the default
                suffix = self.output_suffix.get().strip()
                if suffix != "processed":
                    sys.argv += ["--google-output-folder-suffix", suffix]

                # Only add structure options if not default
                if self.albums_structure.get() != "flatten":
                    sys.argv += ["--google-albums-folders-structure", self.albums_structure.get()]
                if self.no_albums_structure.get() != "year/month":
                    sys.argv += ["--google-no-albums-folders-structure", self.no_albums_structure.get()]

                # Add flags if selected
                for flag, (desc, var) in self.flags.items():
                    if var.get():
                        sys.argv.append(flag)

                # Only add info/error options if not default (default is True)
                if self.show_info.get() is False:
                    sys.argv += ["--show-gpth-info", "false"]
                if self.show_errors.get() is False:
                    sys.argv += ["--show-gpth-errors", "false"]

                # Show final command line
                print("\n💡 Final command line:\n" + " ".join(f'"{arg}"' if " " in arg else arg for arg in sys.argv))

                # Close the GUI window completely
                self.master.destroy()

            def cancel(self):
                custom_print("Configuration cancelled by user.", log_level=logging.WARNING)
                self.master.destroy()
                sys.exit(0)

            def is_valid_folder(self):
                path = self.takeout_folder.get().strip()
                return os.path.isdir(path)

            def validate_folder(self, *args):
                if self.is_valid_folder():
                    self.accept_btn.config(state="normal")
                else:
                    self.accept_btn.config(state="disabled")

        root = tk.Tk()
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 1000
        window_height = 600
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        app = GoogleConfigPanel(root, default_folder=default_folder)
        root.mainloop()

    def launch_console_config(folder_already_provided):
        def ask_input(prompt, default=None):
            full_prompt = f"{prompt} [default: {default}] → Press Enter to use default value:"
            value = input(f"{full_prompt} ").strip()
            return value if value else default

        # -------- Folder Selection --------
        if not folder_already_provided:
            while True:
                folder = ask_input("📁 Path to Takeout folder", default="MyTakeout")
                if folder and os.path.isdir(folder):
                    sys.argv += ["--google-takeout", folder]
                    break
                elif folder == "":
                    print("❌ Folder path is required. Please enter a valid path.")
                else:
                    print(f"❌ Folder does not exists: '{folder}'. Please try again.")

        # -------- Output Folder Suffix --------
        suffix = ask_input("📦 Output folder suffix", default="processed")
        if suffix != "processed":
            sys.argv += ["--google-output-folder-suffix", suffix]

        # -------- Folder Structures --------
        def ask_structure(name, default="flatten"):
            choices = ["flatten", "year", "year/month", "year-month"]
            while True:
                value = ask_input(f"{name} structure ({' / '.join(choices)})", default)
                if value in choices:
                    return value
                print("❌ Invalid choice.")

        albums_structure = ask_structure("Albums folder", default="flatten")
        if albums_structure != "flatten":
            sys.argv += ["--google-albums-folders-structure", albums_structure]

        no_albums_structure = ask_structure("No-albums folder", default="year/month")
        if no_albums_structure != "year/month":
            sys.argv += ["--google-no-albums-folders-structure", no_albums_structure]

        # -------- Flags (yes/no questions) --------
        flag_questions = {
            "--google-ignore-check-structure": "Ignore Takeout structure checking",
            "--google-no-symbolic-albums": "Duplicate assets instead of symlink",
            "--google-remove-duplicates-files": "Remove duplicate assets",
            "--google-rename-albums-folders": "Rename albums based on asset dates",
            "--google-skip-extras-files": "Skip Google-edited/effect files",
            "--google-skip-move-albums": "Do not move albums to ALBUMS_FOLDER",
            "--google-skip-gpth-tool": "Skip GPTH tool (only for testing)",
            "--google-skip-preprocess": "Skip pre-processing (not recommended)",
            "--google-skip-postprocess": "Skip post-processing (not recommended)",
            "--google-keep-takeout-folder": "Keep untouched Takeout copy",
        }

        for flag, description in flag_questions.items():
            answer = ask_input(f"{flag}? {description}", "n").lower()
            if answer == "y":
                sys.argv.append(flag)

        # -------- Boolean Flags with true/false --------
        def ask_bool(flag, description, default="true"):
            answer = ask_input(f"{flag} {description}", default).lower()
            return answer if answer in ["true", "false"] else default

        info = ask_bool("--show-gpth-info", "Show GPTH progress messages", "true")
        if info != "true":
            sys.argv += ["--show-gpth-info", info]

        errors = ask_bool("--show-gpth-errors", "Show GPTH error messages", "true")
        if errors != "true":
            sys.argv += ["--show-gpth-errors", errors]

        # -------- Final summary --------
        print("\n💡 Final command line:\n" + " ".join(f'"{arg}"' if " " in arg else arg for arg in sys.argv))

    # -----------------------------------------------------------------------------------
    # END OF AUX FUNCTIONS
    # -----------------------------------------------------------------------------------

    # Case 1: Called with a single argument and it's a valid folder
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        takeout_path = sys.argv[1]
        custom_print(f"Valid folder detected as input: '{takeout_path}'", log_level=logging.INFO)
        custom_print(f"Executing Google Takeout Photos Processor Feature with the provided input folder...", log_level=logging.INFO)
        sys.argv.insert(1, "--google-takeout")
        folder_already_provided = True

    # Case 2: Called without arguments → Launch full config prompt
    elif len(sys.argv) == 1:
        takeout_path = ""
        custom_print(f"No input folder provided. By default, the Google Takeout Photos Processor feature will be executed.", log_level=logging.INFO)
        folder_already_provided = False

    else:
        return  # Exit early if arguments don't match any valid condition

    # Import tkinter only if needed
    import importlib.util
    gui_available = has_display()
    TKINTER_AVAILABLE = False

    # ──────────────────────────────────────────────────────
    # Detect GUI and import tkinter modules if needed
    # ──────────────────────────────────────────────────────
    if gui_available and importlib.util.find_spec("tkinter") is not None:
        try:
            import tkinter as tk
            from tkinter import ttk, filedialog
            TKINTER_AVAILABLE = True
        except Exception:
            TKINTER_AVAILABLE = False

    # ──────────────────────────────────────────────────────
    # Launch GUI or fallback to console
    # ──────────────────────────────────────────────────────
    if gui_available and TKINTER_AVAILABLE:
        custom_print(f"GUI environment detected. Opening configuration panel...", log_level=logging.INFO)
        launch_gui_config(folder_already_provided, default_folder=takeout_path)
    else:
        if gui_available and not TKINTER_AVAILABLE:
            custom_print(f"Tkinter is not installed. Falling back to console input.", log_level=logging.WARNING)
        else:
            custom_print(f"No GUI detected. Using console input.", log_level=logging.INFO)
        launch_console_config(folder_already_provided)


if __name__ == "__main__":
    main()
