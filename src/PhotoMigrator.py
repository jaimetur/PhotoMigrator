# src/PhotoMigrator.py

import importlib
import logging
import os
import sys
from pathlib import Path

from Core.CustomLogger import custom_log
from Core.GlobalFunctions import set_GLOBAL_VARIABLES
from Core.GlobalVariables import MSG_TAGS

# Añadir 'src/' al PYTHONPATH
src_path = os.path.dirname(__file__)
sys.path.insert(0, src_path)            # Now src is the root for imports

from Core import GlobalVariables as GV
from Utils.StandaloneUtils import change_working_dir, custom_print

ORIGINAL_LAUNCH_CWD = Path.cwd().resolve()


def _runtime_is_frozen() -> bool:
    return bool(
        getattr(sys, "frozen", False)
        or hasattr(sys, "_MEIPASS")
        or ("NUITKA_ONEFILE_PARENT" in os.environ)
        or (globals().get("__compiled__") is not None)
    )


def _looks_like_python_runtime_path(path: Path | None) -> bool:
    if path is None:
        return False
    name = path.name.strip().lower()
    stem = path.stem.strip().lower()
    return stem.startswith("python") or name.startswith("python")


def _launcher_name_patterns() -> list[str]:
    if sys.platform.startswith("win"):
        return [f"{GV.TOOL_NAME}*.exe"]
    if sys.platform == "darwin":
        return [f"{GV.TOOL_NAME}*.command", f"{GV.TOOL_NAME}*"]
    return [f"{GV.TOOL_NAME}*.bin", GV.TOOL_NAME, f"{GV.TOOL_NAME}*"]


def _record_launcher_context() -> None:
    os.environ.setdefault("PHOTOMIGRATOR_ORIGINAL_CWD", str(ORIGINAL_LAUNCH_CWD))
    if not _runtime_is_frozen():
        return
    if os.environ.get("PHOTOMIGRATOR_LAUNCHER_PATH"):
        return

    orig_argv = getattr(sys, "orig_argv", None) or []
    for raw_candidate in [
        orig_argv[0] if orig_argv else "",
        sys.argv[0] if sys.argv else "",
        sys.executable,
    ]:
        text = str(raw_candidate or "").strip()
        if not text:
            continue
        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = (ORIGINAL_LAUNCH_CWD / candidate).resolve(strict=False)
        if candidate.exists() and not _looks_like_python_runtime_path(candidate):
            os.environ["PHOTOMIGRATOR_LAUNCHER_PATH"] = str(candidate.resolve(strict=False))
            return

    for pattern in _launcher_name_patterns():
        matches = sorted(
            (path for path in ORIGINAL_LAUNCH_CWD.glob(pattern) if path.is_file()),
            key=lambda path: (len(path.name), path.name.lower()),
        )
        for match in matches:
            if not _looks_like_python_runtime_path(match):
                os.environ["PHOTOMIGRATOR_LAUNCHER_PATH"] = str(match.resolve(strict=False))
                return


def _selected_feature_details(args: dict) -> tuple[str, str | None, list[str]]:
    """Return the feature selected by the CLI and its effective required arguments."""
    is_set = lambda dest: bool(args.get(dest))
    cloud_feature_names = {
        "google-photos": "Google Photos",
        "synology": "Synology Photos",
        "immich": "Immich Photos",
        "nextcloud": "NextCloud Photos",
    }
    cloud_feature_name = cloud_feature_names.get(str(args.get("client") or "").strip().lower(), "Cloud Photos")
    feature_definitions = (
        (is_set("source") and is_set("target"), "Automatic Migration", None, ["source", "target"]),
        (is_set("google-takeout"), "Google Takeout Processor", None, ["google-takeout"]),
        (is_set("icloud-takeout"), "iCloud Takeout Processor", None, ["icloud-takeout"]),
        (is_set("upload-albums"), cloud_feature_name, "Upload Albums", ["client", "upload-albums"]),
        (is_set("upload-all"), cloud_feature_name, "Upload All", ["client", "upload-all"]),
        (is_set("download-albums"), cloud_feature_name, "Download Albums", ["client", "download-albums", "output-folder"]),
        (is_set("download-all"), cloud_feature_name, "Download All", ["client", "download-all"]),
        (is_set("remove-albums"), cloud_feature_name, "Remove Albums", ["client", "remove-albums"]),
        (is_set("rename-albums"), cloud_feature_name, "Rename Albums", ["client", "rename-albums"]),
        (is_set("consolidate-albums-names"), cloud_feature_name, "Consolidate Album Names", ["client", "consolidate-albums-names"]),
        (is_set("remove-empty-albums"), cloud_feature_name, "Remove Empty Albums", ["client", "remove-empty-albums"]),
        (is_set("remove-duplicates-albums"), cloud_feature_name, "Remove Duplicate Albums", ["client", "remove-duplicates-albums"]),
        (is_set("remove-duplicates-assets"), cloud_feature_name, "Remove Duplicate Assets", ["client", "remove-duplicates-assets"]),
        (is_set("merge-duplicates-albums"), cloud_feature_name, "Merge Duplicate Albums", ["client", "merge-duplicates-albums"]),
        (is_set("remove-all-albums"), cloud_feature_name, "Remove All Albums", ["client", "remove-all-albums"]),
        (is_set("remove-all-assets"), cloud_feature_name, "Remove All Assets", ["client", "remove-all-assets"]),
        (is_set("fix-symlinks-broken"), "Other Features", "Fix Broken Symlinks", ["fix-symlinks-broken"]),
        (args.get("find-duplicates") != ["list", ""], "Other Features", "Find Duplicates", ["find-duplicates"]),
        (is_set("process-duplicates"), "Other Features", "Process Duplicates", ["process-duplicates"]),
        (is_set("rename-folders-content-based"), "Other Features", "Rename Folders Content Based", ["rename-folders-content-based"]),
        (is_set("organize-local-folder-by-date"), "Other Features", "Organize Local Folder By Date", ["organize-local-folder-by-date"]),
    )
    for selected, feature_name, module_name, required_dests in feature_definitions:
        if selected:
            return feature_name, module_name, required_dests
    return "Unknown", None, []


def _parser_option_details(parser) -> dict[str, tuple[str, str]]:
    """Map normalized argument destinations to their preferred long option and parser destination."""
    details = {}
    for action in getattr(parser, "_actions", []):
        option_strings = list(getattr(action, "option_strings", []) or [])
        if not option_strings:
            continue
        normalized_dest = str(getattr(action, "dest", "") or "").replace("_", "-")
        long_option = next((option for option in option_strings if option.startswith("--")), option_strings[0])
        details[normalized_dest] = (long_option, str(getattr(action, "dest", "") or ""))
    return details


def _format_startup_value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _general_argument_dests() -> list[str]:
    """Return arguments shared by the tool rather than owned by one feature."""
    return [
        "configuration-file", "request-user-confirmation", "no-log-file", "log-level", "log-format",
        "date-separator", "range-separator", "foldername-albums", "foldername-no-albums", "foldername-logs",
        "foldername-duplicates-output", "foldername-extracted-dates", "exec-gpth-tool", "exec-exif-tool",
        "filter-from-date", "filter-to-date", "filter-by-type", "filter-by-country",
        "filter-by-city", "filter-by-person", "exclude-folders", "exclude-files", "albums-folders",
        "remove-albums-assets", "preview-album-actions",
    ]


def _feature_optional_dests(feature_name: str, module_name: str | None, args: dict) -> list[str]:
    """Return optional flags owned by the selected feature/module."""
    if feature_name == "Automatic Migration":
        result = [
            "move-assets", "dashboard", "parallel-migration", "prefer-canonical-album-names",
            "consolidate-similar-albums",
        ]
        endpoints = f"{args.get('source', '')} {args.get('target', '')}".lower()
        if "synology" in endpoints:
            result.append("one-time-password")
        return result
    if feature_name in {"Google Photos", "Synology Photos", "Immich Photos", "NextCloud Photos"}:
        result = ["account-id"]
        if feature_name == "Synology Photos":
            result.append("one-time-password")
        if module_name in {"Upload Albums", "Upload All"}:
            result.extend(["prefer-canonical-album-names", "consolidate-similar-albums"])
            if feature_name == "Immich Photos":
                result.append("import-people")
        elif module_name in {"Rename Albums", "Consolidate Album Names"}:
            result.append("preview-album-actions")
        elif module_name == "Remove Albums":
            result.append("preview-album-actions")
            if feature_name in {"Synology Photos", "Immich Photos", "NextCloud Photos"}:
                result.append("remove-albums-assets")
        elif module_name == "Remove Duplicate Assets":
            if feature_name == "Immich Photos":
                result.extend(["immich-duplicates-algorithm", "immich-duplicates-deletion"])
            result.append("duplicate-asset-keeper")
        return result
    if feature_name == "Google Takeout Processor":
        return [
            "output-folder", "google-output-folder-suffix", "google-albums-folders-structure",
            "google-no-albums-folders-structure", "google-ignore-check-structure", "google-no-symbolic-albums",
            "google-remove-duplicates-files", "google-rename-albums-folders", "google-skip-extras-files",
            "google-skip-move-albums", "google-skip-gpth-tool", "google-skip-preprocess",
            "google-skip-postprocess", "google-keep-takeout-folder", "show-gpth-info", "show-gpth-errors",
            "gpth-no-log", "google-process-people",
        ]
    if feature_name == "iCloud Takeout Processor":
        return [
            "output-folder", "icloud-output-folder-suffix", "icloud-albums-folders-structure",
            "icloud-no-albums-folders-structure", "icloud-no-symbolic-albums", "icloud-include-memories",
            "icloud-prefer-native-exif-writer",
        ]
    if feature_name == "Other Features" and module_name == "Organize Local Folder By Date":
        return ["output-folder", "organize-output-folder-suffix", "organize-folder-structure", "move-original-files"]
    return []


def _startup_flag_value(dest: str, args: dict):
    """Return the effective value used for a startup flag, including resolved defaults."""
    resolved_values = {
        "configuration-file": GV.CONFIGURATION_FILE,
        "date-separator": GV.DATE_SEPARATOR,
        "range-separator": GV.RANGE_OF_DATES_SEPARATOR,
        "foldername-albums": GV.FOLDERNAME_ALBUMS,
        "foldername-no-albums": GV.FOLDERNAME_NO_ALBUMS,
        "foldername-logs": GV.FOLDERNAME_LOGS,
        "foldername-duplicates-output": GV.FOLDERNAME_DUPLICATES_OUTPUT,
        "foldername-extracted-dates": GV.FOLDERNAME_EXTRACTED_DATES,
        "exec-gpth-tool": GV.FOLDERNAME_GPTH,
        "exec-exif-tool": GV.FOLDERNAME_EXIFTOOL,
    }
    if dest == "exclude-folders":
        from Utils.FileUtils import DEFAULT_FOLDER_EXCLUSION_PATTERNS, merge_exclusion_patterns
        return merge_exclusion_patterns(args.get(dest, []), default_patterns=DEFAULT_FOLDER_EXCLUSION_PATTERNS)
    if dest == "exclude-files":
        from Utils.FileUtils import DEFAULT_FILE_EXCLUSION_PATTERNS, merge_exclusion_patterns
        return merge_exclusion_patterns(args.get(dest, []), default_patterns=DEFAULT_FILE_EXCLUSION_PATTERNS)
    return resolved_values.get(dest, args.get(dest, ""))


def _log_feature_and_optional_flags(*, include_feature: bool = True, include_optional: bool = True) -> None:
    """Log the selected feature, its effective options, and shared arguments."""
    args = GV.ARGS or {}
    option_details = _parser_option_details(GV.PARSER)
    feature_name, module_name, required_dests = _selected_feature_details(args)

    if include_feature:
        GV.LOGGER.info(f"Selected Feature:")
        GV.LOGGER.info(f"  - Feature                       : {feature_name}")
        if module_name:
            GV.LOGGER.info(f"  - Module                        : {module_name}")
        GV.LOGGER.info(f"  - Required Flags:")
        if required_dests:
            for dest in required_dests:
                option, _ = option_details.get(dest, (f"--{dest}", dest.replace("-", "_")))
                GV.LOGGER.info(f"    {option:<30}: {_format_startup_value(args.get(dest, ''))}")
        else:
            GV.LOGGER.info("    - None")
        GV.LOGGER.info("")

    if include_optional:
        optional_dests = [
            dest for dest in _feature_optional_dests(feature_name, module_name, args)
            if dest not in required_dests
        ]
        GV.LOGGER.info("Optional Flags Provided:")
        if optional_dests:
            for dest in optional_dests:
                option, _ = option_details.get(dest, (f"--{dest}", dest.replace("-", "_")))
                GV.LOGGER.info(f"  {option:<32}: {_format_startup_value(_startup_flag_value(dest, args))}")
        else:
            GV.LOGGER.info("  - None")
        GV.LOGGER.info("")

        general_dests = _general_argument_dests()
        GV.LOGGER.info("General Arguments:")
        if general_dests:
            for dest in general_dests:
                option, _ = option_details.get(dest, (f"--{dest}", dest.replace("-", "_")))
                GV.LOGGER.info(f"  {option:<32}: {_format_startup_value(_startup_flag_value(dest, args))}")
        else:
            GV.LOGGER.info("  - None")
        GV.LOGGER.info("")


# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def PhotoMigrator():
    # Limpiar la pantalla y parseamos argumentos de entrada
    _record_launcher_context()
    if os.name == 'nt':
        os.system('cls')
    elif os.environ.get('TERM') and sys.stdout.isatty():
        os.system('clear')

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
    set_GLOBAL_VARIABLES()       # Need to be called after set_ARGS_PARSER() but before set_LOGGER()
    custom_print(f"Setting Global LOGGER...", log_level=logging.INFO)
    set_LOGGER()        # Need to be called after set_GLOBAL_VARIABLES()
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
    _log_feature_and_optional_flags(include_optional=False)
    _log_feature_and_optional_flags(include_feature=False)
    GV.LOGGER.info(f"Tool Configured with the following Global Settings:")
    GV.LOGGER.info(f"  - Project Root                  : {GV.PROJECT_ROOT}")
    GV.LOGGER.info(f"  - GPTH TOOL Version             : {GV.GPTH_VERSION}")
    GV.LOGGER.info(f"  - EXIF TOOL Version             : {GV.EXIFTOOL_VERSION}")
    if not GV.ARGS['no-log-file']:
        GV.LOGGER.info(f"  - Generated Log File Location   : {GV.LOG_FILENAME + '.log'}")
    GV.LOGGER.info(f"")

    # Get the execution mode and run it.
    detect_and_run_execution_mode()
    GV.LOGGER.info("PhotoMigrator finished. Exit code: 0")

def pre_parse_args():
    def extract_ui_launcher_state(argv_items):
        explicit_tui = "--tui" in argv_items
        explicit_gui = "--gui" in argv_items
        filtered_args = []
        config_path = ""
        index = 0
        while index < len(argv_items):
            arg = argv_items[index]
            if arg in {"--tui", "--gui"}:
                index += 1
                continue
            if arg in {"--configuration-file", "-config"}:
                if index + 1 >= len(argv_items):
                    filtered_args.append(arg)
                    index += 1
                    continue
                config_path = str(argv_items[index + 1] or "").strip()
                index += 2
                continue
            if arg.startswith("--configuration-file="):
                config_path = str(arg.split("=", 1)[1] or "").strip()
                index += 1
                continue
            if arg.startswith("-config="):
                config_path = str(arg.split("=", 1)[1] or "").strip()
                index += 1
                continue
            filtered_args.append(arg)
            index += 1
        initial_values = {}
        if config_path:
            initial_values["configuration-file"] = config_path
        return explicit_tui, explicit_gui, filtered_args, initial_values

    def supports_graphical_terminal():
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return False
        term = str(os.environ.get("TERM") or "").strip().lower()
        if sys.platform.startswith("win"):
            return True
        return term not in {"", "dumb"}

    def has_display():
        # Detect if a graphical environment is available
        return bool(os.environ.get("DISPLAY") or sys.platform.startswith("win") or sys.platform == "darwin")

    def launch_textual_tui(initial_values=None):
        from UI.cli_tui import run_cli_tui

        run_cli_tui(
            project_root=Path(__file__).resolve().parent.parent,
            cli_entrypoint=Path(__file__).resolve(),
            initial_values=initial_values or {},
        )

    def launch_tk_gui(initial_values=None):
        from UI.tk_gui import run_tk_gui

        run_tk_gui(
            project_root=Path(__file__).resolve().parent.parent,
            cli_entrypoint=Path(__file__).resolve(),
            initial_values=initial_values or {},
        )

    def queue_help_fallback(message):
        custom_print(message, log_level=logging.WARNING)
        if "--help" not in sys.argv[1:] and "-h" not in sys.argv[1:]:
            sys.argv.append("--help")

    def try_launch_gui(initial_values=None):
        try:
            from UI.tk_gui import tkinter_runtime_available

            gui_ok, gui_error = tkinter_runtime_available()
            if not gui_ok:
                custom_print(
                    f"Desktop GUI is not available ({gui_error}).",
                    log_level=logging.WARNING,
                )
                return False
            if not has_display():
                custom_print(
                    "Desktop GUI is not available (no graphical display detected).",
                    log_level=logging.WARNING,
                )
                return False
            custom_print("Opening PhotoMigrator desktop GUI...", log_level=logging.INFO)
            launch_tk_gui(initial_values=initial_values or {})
            sys.exit(0)
        except Exception as exc:
            custom_print(
                f"Unable to launch the desktop GUI ({exc}).",
                log_level=logging.WARNING,
            )
            return False

    def try_launch_tui(initial_values=None):
        if not supports_graphical_terminal():
            custom_print(
                "Interactive terminal UI is not available (terminal is not compatible).",
                log_level=logging.WARNING,
            )
            return False
        try:
            from UI.cli_tui import textual_runtime_available

            textual_ok, textual_error = textual_runtime_available()
            if not textual_ok:
                custom_print(
                    f"Textual TUI is not available ({textual_error}).",
                    log_level=logging.WARNING,
                )
                return False
            custom_print("Opening PhotoMigrator CLI TUI...", log_level=logging.INFO)
            launch_textual_tui(initial_values=initial_values or {})
            sys.exit(0)
        except Exception as exc:
            custom_print(
                f"Unable to launch the CLI TUI ({exc}).",
                log_level=logging.WARNING,
            )
            return False

    def launch_gui_config(folder_already_provided, default_folder=""):
        import tkinter as tk
        from tkinter import ttk, filedialog

        class GoogleConfigPanel:
            def __init__(self, master, default_folder):
                self.master = master
                master.title("Google Takeout Fixing Configuration")
                # Cambiar icono
                icon_path = Path(__file__).resolve().parent.parent / "assets" / "ico" / "PhotoMigrator.ico"
                if icon_path.exists():
                    self.master.iconbitmap(icon_path)

                # -------- Folder Selection --------
                self.takeout_folder = tk.StringVar(value=default_folder)

                folder_frame = tk.Frame(master)
                folder_frame.pack(anchor="w", padx=20, pady=(10, 4))

                row_folder = tk.Frame(folder_frame)
                row_folder.pack(anchor="w", pady=2)
                tk.Label(row_folder, text="Input Folder:", width=28, anchor="w").pack(side="left")
                self.folder_entry = tk.Entry(row_folder, textvariable=self.takeout_folder, width=110)
                self.folder_entry.pack(side="left")
                tk.Button(row_folder, text="Select Folder", command=self.browse_folder).pack(side="left", padx=8)

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
                    "--google-no-symbolic-albums": ("No Creates symbolic links for Albums", tk.BooleanVar()),
                    "--google-remove-duplicates-files": ("Remove duplicate assets (only useful if before flag is unchecked", tk.BooleanVar()),
                    "--google-rename-albums-folders": ("Rename albums based on its assets dates (useful for a better organization)", tk.BooleanVar()),
                    "--google-skip-extras-files": ("Skip Google-edited/effect files", tk.BooleanVar()),
                    "--google-skip-move-albums": ("Do not move albums to ALBUMS_FOLDER", tk.BooleanVar()),
                    "--google-skip-gpth-tool": ("Skip GPTH tool (only recommended for testing purposes)", tk.BooleanVar()),
                    "--google-skip-preprocess": ("Skip pre-processing step (not recommended)", tk.BooleanVar()),
                    "--google-skip-postprocess": ("Skip post-processing step (not recommended)", tk.BooleanVar()),
                    "--google-keep-takeout-folder": ("Keep untouched Takeout copy (uses double disk space)", tk.BooleanVar()),
                    "--google-process-people": ("Process people labels from Google JSON sidecars", tk.BooleanVar(value=True)),
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

                # -------- Bottom buttons --------
                button_frame = tk.Frame(master)
                button_frame.pack(pady=(10, 10))

                # ⛔ Primero se crea el botón Accept, y empieza desactivado
                self.accept_btn = tk.Button(button_frame, text="Accept", command=self.submit, state="disabled")
                self.accept_btn.pack(side="right", padx=5)

                # ❌ Y si tienes botón Cancel, va en medio o al lado izquierdo
                cancel_btn = tk.Button(button_frame, text="Cancel", command=self.cancel)
                cancel_btn.pack(side="left", padx=5)

                # ⚠️ Warning label (initially hidden)
                self.warning_label = tk.Label(master, text="You must select a valid Input Folder", fg="red", font=("Arial", 10))
                self.warning_label.pack()
                self.warning_label.pack_forget()  # Oculta la etiqueta al inicio

                self.takeout_folder.trace_add("write", self.validate_folder)
                self.validate_folder()

            def browse_folder(self):
                folder = filedialog.askdirectory()
                if folder:
                    self.takeout_folder.set(folder)
                    self.validate_folder()  # 👈 Esto activa el botón Accept si la carpeta es válida

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
                if self.flags["--google-process-people"][1].get() is False:
                    sys.argv += ["--google-process-people", "false"]

                # Only add info/error options if not default (default is True)
                if self.show_info.get() is False:
                    sys.argv += ["--show-gpth-info", "false"]
                if self.show_errors.get() is False:
                    sys.argv += ["--show-gpth-errors", "false"]

                # -------- Final command summary --------
                print()
                custom_print("▶️ Final command line: " + " ".join(f'"{arg}"' if " " in arg else arg for arg in sys.argv), log_level=logging.INFO)

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
                folder = self.takeout_folder.get()
                if folder and os.path.isdir(folder):
                    self.accept_btn.config(state="normal")
                    self.warning_label.pack_forget()
                else:
                    self.accept_btn.config(state="disabled")
                    self.warning_label.pack()

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
        PAD_DESC = 58
        PAD_DEFAULT = 14
        PAD_PROMPT = 44
        HEADER_WIDTH = PAD_DESC + PAD_DEFAULT + PAD_PROMPT + 40

        def ask_input(label, description="", default=None, icon="ℹ️", is_flag=False):
            if is_flag:
                prompt_str = f"{icon} {label} (y/n)".ljust(PAD_PROMPT-3) + ": "
            else:
                prompt_str = f"{icon} Introduce {label}".ljust(PAD_PROMPT-3) + ": "
            desc_str = f"{icon} {description}".ljust(PAD_DESC-1)
            default_str = f"[{default}]".ljust(PAD_DEFAULT) if default is not None else ""
            input_row = f"{MSG_TAGS['INFO']}{desc_str}{default_str}{prompt_str}"
            try:
                import readline
                readline.set_startup_hook(lambda: readline.insert_text(str(default)))
                # value = input(input_row).strip()
                try:
                    value = input(input_row).strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    custom_print("Configuration cancelled by user.", log_level=logging.WARNING)
                    sys.exit(0)
            finally:
                try:
                    readline.set_startup_hook(None)
                except:
                    pass
            return value if value else default

        def ask_bool(flag, description, default="true", icon="❓"):
            return ask_input(flag, description=description, icon=icon, default=default, is_flag=True).lower()

        def ask_structure(name, default="flatten", icon="📂"):
            choices = ["flatten", "year", "year/month", "year-month"]
            while True:
                value = ask_input(f"{name} structure", description=f"Structure for {name.lower()} folder", default=default, icon=icon)
                if value in choices:
                    return value
                custom_print("❌ Invalid choice. Please try again.", log_level=logging.ERROR)

        # -------- Header --------
        print()
        custom_print("🧩 CONFIGURATION PANEL (Console Mode) - Pres CTRL+C to Interrupt...\n", log_level=logging.INFO)
        custom_print("DESCRIPTION:".ljust(PAD_DESC) + "DEFAULT:".ljust(PAD_DEFAULT) + "PROMPT:".ljust(PAD_PROMPT) + "INPUT:", log_level=logging.INFO)
        custom_print("-" * HEADER_WIDTH, log_level=logging.INFO)

        # -------- Takeout folder --------
        if not folder_already_provided:
            while True:
                folder = ask_input("Path to Takeout folder", description="Google Takeout input folder", default="MyTakeout", icon="📁")
                if folder and os.path.isdir(folder):
                    sys.argv += ["--google-takeout", folder]
                    break
                elif folder == "":
                    custom_print("❌ Folder path is required. Please enter a valid path.", log_level=logging.ERROR)
                else:
                    custom_print("❌ Invalid folder. Please try again.", log_level=logging.ERROR)

        # -------- Output suffix --------
        suffix = ask_input("Output folder suffix", description="Suffix for the processed output folder", default="processed", icon="🔤")
        if suffix != "processed":
            sys.argv += ["--google-output-folder-suffix", suffix]

        # -------- Folder structure options --------
        albums_structure = ask_structure("Albums folder", default="flatten", icon="📂")
        if albums_structure != "flatten":
            sys.argv += ["--google-albums-folders-structure", albums_structure]

        no_albums_structure = ask_structure("No-albums folder", default="year/month", icon="📂")
        if no_albums_structure != "year/month":
            sys.argv += ["--google-no-albums-folders-structure", no_albums_structure]

        # -------- Flags --------
        flag_questions = {
            "--google-ignore-check-structure": "Ignore Takeout structure checking",
            "--google-no-symbolic-albums": "No Creates symbolic links for Albums",
            "--google-remove-duplicates-files": "Remove duplicate assets",
            "--google-rename-albums-folders": "Rename albums based on its asset dates",
            "--google-skip-extras-files": "Skip Google-edited/effect files",
            "--google-skip-move-albums": "Do not move albums to ALBUMS_FOLDER",
            "--google-skip-gpth-tool": "Skip GPTH tool (only recommended for testing purposes)",
            "--google-skip-preprocess": "Skip pre-processing (not recommended)",
            "--google-skip-postprocess": "Skip post-processing (not recommended)",
            "--google-keep-takeout-folder": "Keep untouched Takeout copy (uses double disk space)",
        }

        for flag, desc in flag_questions.items():
            answer = ask_bool(flag=flag, description=desc, default="no", icon="❓").lower()
            if answer in ["y", "yes", "true"]:
                sys.argv.append(flag)

        answer = ask_bool(
            flag="--google-process-people",
            description="Process people labels from Google JSON sidecars",
            default="yes",
            icon="❓",
        ).lower()
        if answer in ["n", "no", "false"]:
            sys.argv += ["--google-process-people", "false"]

        # -------- Boolean options --------
        answer = ask_bool(flag="--show-gpth-info", description="Show GPTH progress messages", default="yes", icon="❓").lower()
        if answer not in ["y", "yes", "true"]:
            sys.argv += ["--show-gpth-info", answer]

        answer = ask_bool(flag="--show-gpth-errors", description="Show GPTH error messages", default="yes", icon="❓").lower()
        if answer not in ["y", "yes", "true"]:
            sys.argv += ["--show-gpth-errors", answer]

        # -------- Final command summary --------
        print()
        custom_print("▶️ Final command line: " + " ".join(f'"{arg}"' if " " in arg else arg for arg in sys.argv), log_level=logging.INFO)

    # -----------------------------------------------------------------------------------
    # END OF AUX FUNCTIONS
    # -----------------------------------------------------------------------------------

    explicit_tui, explicit_gui, filtered_args, initial_tui_values = extract_ui_launcher_state(sys.argv[1:])
    no_arguments_provided = False
    folder_already_provided = False

    # Case 1: Called with a single argument and it's a valid folder
    if len(filtered_args) == 1 and os.path.isdir(filtered_args[0]):
        takeout_path = filtered_args[0]
        custom_print(f"Valid folder detected as input: '{takeout_path}'", log_level=logging.INFO)
        custom_print(f"Executing Google Takeout Photos Processor Feature with the provided input folder...", log_level=logging.INFO)
        initial_tui_values.update({
            "active_module": "google_takeout",
            "google-takeout": takeout_path,
        })
        sys.argv.insert(1, "--google-takeout")
        folder_already_provided = True

    # Case 2: Called without arguments
    elif len(filtered_args) == 0:
        no_arguments_provided = True
        custom_print(
            "No execution arguments provided. PhotoMigrator will try to open the desktop GUI by default.",
            log_level=logging.INFO,
        )
    else:
        return  # Exit early if arguments don't match any valid condition

    if explicit_tui:
        if try_launch_tui(initial_values=initial_tui_values):
            return
        queue_help_fallback("Unable to launch the CLI TUI. Falling back to command-line help.")
        return

    if explicit_gui:
        if try_launch_gui(initial_values=initial_tui_values):
            return
        if try_launch_tui(initial_values=initial_tui_values):
            return
        queue_help_fallback("Unable to launch the desktop GUI or the CLI TUI. Falling back to command-line help.")
        return

    if no_arguments_provided:
        if try_launch_gui(initial_values=initial_tui_values):
            return
        if try_launch_tui(initial_values=initial_tui_values):
            return
        queue_help_fallback("Unable to launch the desktop GUI or the CLI TUI. Falling back to command-line help.")
        return

    if folder_already_provided and try_launch_tui(initial_values=initial_tui_values):
        return

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
        launch_tk_gui(initial_values=initial_tui_values)
        sys.exit(0)
    else:
        if gui_available and not TKINTER_AVAILABLE:
            custom_print(f"Tkinter is not installed. Falling back to console input.", log_level=logging.WARNING)
        else:
            custom_print(f"No GUI detected. Using console input. You will be prompted for each configuration option for 'Google Takeout Fixing' feature...", log_level=logging.INFO)
        launch_console_config(folder_already_provided)


if __name__ == "__main__":
    try:
        PhotoMigrator()
    except KeyboardInterrupt:
        try:
            print("")
            if GV.LOGGER:
                GV.LOGGER.warning("Execution interrupted by user (Ctrl+C).")
            else:
                custom_print("Execution interrupted by user (Ctrl+C).", log_level=logging.WARNING)
        except Exception:
            pass
        finally:
            logging.shutdown()
        raise SystemExit(130)
