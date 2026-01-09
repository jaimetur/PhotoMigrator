# ------------------------------------------------------------
# Add 'src/' folder to sys.path to import any module from 'src/'.
import os, sys
current_dir = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(current_dir, "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
# ------------------------------------------------------------


import glob
import shutil
import subprocess
import tempfile
from colorama import Fore
from pathlib import Path

from Core.GlobalVariables import TOOL_NAME, TOOL_VERSION, GPTH_VERSION, INCLUDE_EXIF_TOOL, COPYRIGHT_TEXT, COMPILE_IN_ONE_FILE, FOLDERNAME_GPTH, FOLDERNAME_EXIFTOOL
# from Utils.GeneralUtils import clear_screen, print_arguments_pretty, get_os, get_arch, ensure_executable
# from Utils.FileUtils import unzip_to_temp, zip_folder, unzip
# from Utils.StandaloneUtils import resolve_internal_path

global OPERATING_SYSTEM
global ARCHITECTURE
global TOOL_SOURCE_NAME
global TOOL_VERSION_WITHOUT_V
global TOOL_NAME_VERSION
global root_dir
global tool_name_with_version_os_arch
global script_zip_file
global archive_path_relative

# ---------------------------- GLOBAL VARIABLES ----------------------------
# COMPILE_IN_ONE_FILE = True

# Tag and colored tags for message output (console and log)
MSG_TAGS = {
    'VERBOSE'                   : "VERBOSE : ",
    'DEBUG'                     : "DEBUG   : ",
    'INFO'                      : "INFO    : ",
    'WARNING'                   : "WARNING : ",
    'ERROR'                     : "ERROR   : ",
    'CRITICAL'                  : "CRITICAL: ",
}
MSG_TAGS_COLORED = {
    'VERBOSE'                   : f"{Fore.CYAN}{MSG_TAGS['VERBOSE']}",
    'DEBUG'                     : f"{Fore.LIGHTCYAN_EX}{MSG_TAGS['DEBUG']}",
    'INFO'                      : f"{Fore.LIGHTWHITE_EX}{MSG_TAGS['INFO']}",
    'WARNING'                   : f"{Fore.YELLOW}{MSG_TAGS['WARNING']}",
    'ERROR'                     : f"{Fore.RED}{MSG_TAGS['ERROR']}",
    'CRITICAL'                  : f"{Fore.MAGENTA}{MSG_TAGS['CRITICAL']}",
}
# --------------------------------------------------------------------------

# ---------------------------------- HELPERS -------------------------------
def _clear_screen():
    """
    Clears the console screen in a cross-platform way.

    Uses:
      - 'clear' on POSIX systems
      - 'cls' on Windows
    """
    os.system('clear' if os.name == 'posix' else 'cls')


def _get_os(step_name=""):
    """Return normalized operating system name (linux, macos, windows)."""
    current_os = platform.system()
    if current_os in ["Linux", "linux"]:
        os_label = "linux"
    elif current_os in ["Darwin", "macOS", "macos"]:
        os_label = "macos"
    elif current_os in ["Windows", "windows", "Win"]:
        os_label = "windows"
    else:
        print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Operating System: {current_os}")
        os_label = "unknown"
    print(f"{MSG_TAGS['INFO']}{step_name}Detected OS: {os_label}")
    return os_label


def _get_arch(step_name=""):
    """Return normalized system architecture (e.g., x64, arm64)."""
    current_arch = platform.machine()
    if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
        arch_label = "x64"
    elif current_arch in ["aarch64", "arm64", "ARM64"]:
        arch_label = "arm64"
    else:
        print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Architecture: {current_arch}")
        arch_label = "unknown"
    print(f"{MSG_TAGS['INFO']}{step_name}Detected architecture: {arch_label}")
    return arch_label


def _print_arguments_pretty(arguments, title="Arguments", step_name="", use_custom_print=True):
    """
    Prints a list of command-line arguments in a structured and readable one-line-per-arg format.

    Args:
        :param arguments:
        :param step_name:
        :param title:
        :param use_custom_print:
        :param use_logger:
    """
    print("")
    indent = "    "
    i = 0

    if use_custom_print:
        from utils_infrastructure.StandaloneUtils import custom_print
        custom_print(f"{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                custom_print(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                custom_print(f"{step_name}{indent}{arg}")
                i += 1
    else:
        pass
        print(f"{MSG_TAGS['INFO']}{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}")
                i += 1
    print("")


# Replace original print to use the same GV.LOGGER formatter
def _custom_print(*args, log_level=logging.INFO, **kwargs):
    """
    Prints a message with the same color tags used by this build script.

    Args:
        *args: Message parts to be joined with spaces.
        log_level (int): Logging level used to select a color tag.
        **kwargs: Extra keyword arguments passed to `print()`.
    """
    message = " ".join(str(a) for a in args)
    log_level_name = logging.getLevelName(log_level)
    colortag = MSG_TAGS_COLORED.get(log_level_name, MSG_TAGS_COLORED['INFO'])
    print(f"{colortag}{message}{Style.RESET_ALL}", **kwargs)


def _zip_folder(temp_dir, output_file):
    """
    Creates a ZIP archive from `temp_dir` and writes it to `output_file`.

    Notes:
        - Preserves folder structure.
        - Adds empty directories as entries when detected.
    """
    print(f"Creating packed file: {output_file}...")

    # Convert output_file to a Path object
    output_path = Path(output_file)

    # Create parent directories if they don't exist
    if not output_path.parent.exists():
        print(f"Creating needed folder for: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                # Add to the zip preserving the folder structure
                zipf.write(file_path, file_path.relative_to(temp_dir))
            for dir in dirs:
                dir_path = Path(root) / dir
                # Add empty directories to the zip
                if not os.listdir(dir_path):
                    zipf.write(dir_path, dir_path.relative_to(temp_dir))
    print(f"File successfully packed: {output_file}")


def _unzip(zipfile_path, dest_folder):
    """
    Unzips a ZIP file into the specified destination folder.

    Args:
        zipfile_path (str): Path to the ZIP file.
        dest_folder (str): Destination folder where the contents will be extracted.
    """
    # Check if the ZIP file exists
    if not os.path.exists(zipfile_path):
        raise FileNotFoundError(f"The ZIP file does not exist: {zipfile_path}")
    # Check if the file is a valid ZIP file
    if not zipfile.is_zipfile(zipfile_path):
        raise zipfile.BadZipFile(f"The file is not a valid ZIP archive: {zipfile_path}")
    # Create the destination folder if it doesn't exist
    os.makedirs(dest_folder, exist_ok=True)
    # Extract all contents of the ZIP file into the destination folder
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        zip_ref.extractall(dest_folder)
        print(f"ZIP file extracted to: {dest_folder}")


def _unzip_to_temp(zipfile_path):
    """
    Unzips the contents of `zip_path` into a temporary directory.
    The directory is created using tempfile and is valid on all platforms.

    Returns:
        str: Path to the temporary extraction directory.
    """
    if not zipfile.is_zipfile(zipfile_path):
        raise ValueError(f"{zipfile_path} is not a valid zip file.")

    temp_dir = tempfile.mkdtemp()  # Creates a unique temp dir, persists until deleted manually
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        print(f"ZIP file extracted to: {temp_dir}")

    return temp_dir


def _ensure_executable(path):
    """
    Ensures the file at `path` has executable permissions on non-Windows systems.
    """
    if platform.system() != "Windows":
        # Add execute permissions for user, group and others without removing existing ones
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _resolve_internal_path(path_to_resolve, step_name=''):
    """
    Returns the absolute path to the resource 'relative_path', working in:
    - PyInstaller (onefile or standalone)
    - Nuitka (onefile or standalone)
    - Direct Python (from cwd or from dirname(__file__))
    """
    # IMPORTANT: Don't use LOGGER in this function because is also used by build-binary.py which has not any LOGGER created.
    compiled_source = globals().get("__compiled__")
    DEBUG_MODE = GV.LOG_LEVEL <= logging.DEBUG  # Set to False to silence
    if DEBUG_MODE:
        _custom_print(f"{step_name}DEBUG_MODE = {DEBUG_MODE}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}---RESOURCE_PATH DEBUG INFO", log_level=logging.DEBUG)
        _custom_print(f"{step_name}PATH TO RESOLVE             : {path_to_resolve}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}RESOURCES_IN_CURRENT_FOLDER : {RESOURCES_IN_CURRENT_FOLDER}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}sys.frozen                  : {getattr(sys, 'frozen', False)}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}NUITKA_ONEFILE_PARENT       : {'YES' if 'NUITKA_ONEFILE_PARENT' in os.environ else 'NO'}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}PROJECT_ROOT                : {PROJECT_ROOT}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}sys.argv[0]                 : {sys.argv[0]}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}sys.executable              : {sys.executable}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}os.getcwd()                 : {os.getcwd()}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}__file__                    : {globals().get('__file__', 'NO __file__')}", log_level=logging.DEBUG)
        try:
            if compiled_source:
                _custom_print(f"{step_name}__compiled__.containing_dir : {compiled_source.containing_dir}", log_level=logging.DEBUG)
            else:
                _custom_print(f"{step_name}__compiled__ not defined", log_level=logging.DEBUG)
        except NameError:
            _custom_print(f"{step_name}__compiled__ not defined", log_level=logging.DEBUG)
        if hasattr(sys, '_MEIPASS'):
            _custom_print(f"_MEIPASS                    : {sys._MEIPASS}", log_level=logging.DEBUG)
        else:
            _custom_print(f"{step_name}_MEIPASS not defined", log_level=logging.DEBUG)
        print("")

    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        if DEBUG_MODE: _custom_print(f"{step_name}Enter PyInstaller mode     -> base_path={base_path} (sys._MEIPASS)", log_level=logging.DEBUG)
    # Nuitka onefile
    elif "NUITKA_ONEFILE_PARENT" in os.environ:
        # base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(sys.executable)
        # base_path = PROJECT_ROOT
        if DEBUG_MODE: _custom_print(f"{step_name}Enter Nuitka --onefile mode    -> base_path={base_path} (sys.executable)", log_level=logging.DEBUG)
    # Nuitka standalone
    elif compiled_source:
    # elif "__compiled__" in globals():
        base_path = os.path.join(compiled_source.containing_dir, TOOL_NAME + '.dist')
        # base_path = compiled_source
        if DEBUG_MODE: _custom_print(f"{step_name}Enter Nuitka --standalone mode     -> base_path={base_path} (__compiled__.containing_dir)", log_level=logging.DEBUG)
    # Normal Python
    elif "__file__" in globals():
        if RESOURCES_IN_CURRENT_FOLDER:
            base_path = os.getcwd()
            if DEBUG_MODE: _custom_print(f"{step_name}Enter Python mode (with RESOURCES_IN_CURRENT_FOLDER={RESOURCES_IN_CURRENT_FOLDER})  -> base_path={base_path} (os.getcwd())", log_level=logging.DEBUG)
        else:
            # base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_path = PROJECT_ROOT
            if DEBUG_MODE: _custom_print(f"{step_name}Enter Python mode (with RESOURCES_IN_CURRENT_FOLDER={RESOURCES_IN_CURRENT_FOLDER})  -> base_path={base_path} (PROJECT_ROOT)", log_level=logging.DEBUG)
    else:
        base_path = os.getcwd()
        if DEBUG_MODE: _custom_print(f"{step_name}Enter final fallback   -> base_path={base_path} (os.getcwd())", log_level=logging.DEBUG)

    # ✅ If the path already exists (absolute or relative), return it directly
    if path_to_resolve and os.path.exists(path_to_resolve):
        resolved_path = path_to_resolve
    else:
        resolved_path = os.path.join(base_path, path_to_resolve)
    if DEBUG_MODE:
        _custom_print(f"{step_name}return path                 : {resolved_path}", log_level=logging.DEBUG)
        _custom_print(f"{step_name}--- END RESOURCE_PATH DEBUG INFO", log_level=logging.DEBUG)
    return resolved_path


def _include_extrafiles_and_zip(input_file, output_file):
    """
    Copies additional files into a temporary folder alongside the compiled binary
    and creates a ZIP with the expected release structure.

    Args:
        input_file (str): Compiled binary path to include at ZIP root.
        output_file (str): Output ZIP file path.
    """
    extra_files_to_subdir = [
        {
            'subdir': '',  # Indicates these files go to the script root directory
            'files': ["./Config.ini"]
        },
        {
            'subdir': 'assets/logos',  # These files go to the 'assets' subdirectory
            # 'files': ["./assets/logos/logo.png"]
            'files': ["./assets/logos/logo_17*.png"]
        },
        {
            'subdir': 'docs',  # These files go to the 'docs' subdirectory
            'files': ["./README.md", "./CHANGELOG.md", "./ROADMAP.md", "./DOWNLOAD.md", "./CONTRIBUTING.md", "./CODE_OF_CONDUCT.md", "./LICENSE"]
        },
        {
            'subdir': 'help',  # These files go to the 'help' subdirectory
            'files': ["./help/*.md"]
        }
    ]
    if not input_file or not output_file:
        print("Ussage: _include_extrafiles_and_zip(input_file, output_file)")
        sys.exit(1)
    if not Path(input_file).is_file():
        print(f"ERROR   : The input file '{input_file}' does not exists.")
        sys.exit(1)
    temp_dir = Path(tempfile.mkdtemp())
    tool_version_dir = os.path.join(temp_dir, TOOL_NAME_VERSION)
    print(tool_version_dir)
    os.makedirs(tool_version_dir, exist_ok=True)
    shutil.copy(input_file, tool_version_dir)

    # Now we copy the extra files
    for subdirs_dic in extra_files_to_subdir:
        subdir = subdirs_dic.get('subdir', '')  # If 'subdir' is empty, it will copy to the root directory
        files = subdirs_dic.get('files', [])  # Ensure there is always a list of files
        subdir_path = os.path.join(tool_version_dir, subdir) if subdir else tool_version_dir
        os.makedirs(subdir_path, exist_ok=True)  # Create the folder if it doesn't exist
        for file_pattern in files:
            # Convert the relative path into an absolute path
            absolute_pattern = os.path.abspath(file_pattern)
            # Search for files matching the pattern
            matched_files = glob.glob(absolute_pattern)
            # If no files were found and the path is a valid file, treat it as such
            if not matched_files and os.path.isfile(absolute_pattern):
                matched_files = [absolute_pattern]
            # Copy the files to the destination directory
            for file in matched_files:
                shutil.copy(file, subdir_path)
    # Compress the temporary directory and then delete it
    zip_folder(temp_dir, output_file)
    shutil.rmtree(temp_dir)


def _get_tool_version(file):
    """
    Reads a Python file and extracts the TOOL_VERSION value from a line like:
        TOOL_VERSION = "x.y.z"

    Args:
        file (str): Path to the file to inspect.

    Returns:
        str | None: Extracted tool version string if found, otherwise None.
    """
    if not Path(file).is_file():
        print(f"ERROR   : The file {file} does not exists.")
        return None
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("TOOL_VERSION"):
                return line.split('"')[1]
    print("ERROR   : Not found any value between colons after TOOL_VERSION.")
    return None


def _get_clean_version(version: str):
    """
    Removes a leading 'v' from a version string (if present).

    Args:
        version (str): Version string, e.g. "v1.2.3" or "1.2.3".

    Returns:
        str: Version without the leading 'v'.
    """
    # Remove the 'v' if it exists at the beginning
    clean_version = version.lstrip('v')
    return clean_version


def _extract_release_body(input_file, output_file, download_file):
    """Extracts two specific sections from the changelog file, modifies a header, and appends them along with additional content from another file."""
    # Open the file and read its content into a list
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    # Initialize key indices and counter
    changelog_index = None
    second_release_index = None
    release_count = 0
    # Loop through lines to find the start of the "Changelog" section and locate the second occurrence of "## Release"
    for i, line in enumerate(lines):
        if line.strip() == "# 🗓️ CHANGELOG":
            changelog_index = i
            # lines[i] = lines[i].replace("# 🗓️ CHANGELOG", "# 🗓️ Changelog")
        if "## Release:" in line:
            release_count += 1
            if release_count == 2:
                second_release_index = i
                break
    # Validate that the changelog section exists
    if changelog_index is None:
        print("Required sections not found in the file.")
        return
    # Extract content from "## Changelog:" to the second "## Release"
    if second_release_index is not None:
        release_section = lines[changelog_index:second_release_index]
    else:
        release_section = lines[changelog_index:]
    # Read content of download_file
    with open(download_file, 'r', encoding='utf-8') as df:
        download_content = df.readlines()
    # Append both the download file content and the release section to the output file
    # If the file already exists, delete it
    if os.path.exists(output_file):
        os.remove(output_file)
    with open(output_file, 'a', encoding='utf-8') as outfile:
        outfile.writelines(release_section)
        outfile.writelines(download_content)


def _add_roadmap_to_readme(readme_file, roadmap_file):
    """
    Replaces the ROADMAP block in the README file with the content of another ROADMAP file.
    If the block does not exist, it inserts it before the line that contains "## Credits".

    Args:
        readme_file (str): Path to README.md file.
        roadmap_file (str): Path to ROADMAP.md file.
    """
    # Read the content of the README file
    with open(readme_file, "r", encoding="utf-8") as f:
        readme_lines = f.readlines()
    # Read the content of the ROADMAP file
    with open(roadmap_file, "r", encoding="utf-8") as f:
        roadmap_content = f.read().strip() + "\n\n"  # Ensure a final line break
    # Search for the existing ROADMAP block
    start_index, end_index = None, None
    for i, line in enumerate(readme_lines):
        if line.strip() == "## 📅 ROADMAP":
            start_index = i
        if start_index is not None and line.strip() == "## 🎖️ Credits":
            end_index = i
            break
    if start_index is not None and end_index is not None:
        # Replace the existing ROADMAP block
        print("'ROADMAP' block found")
        updated_readme = readme_lines[:start_index] + [roadmap_content] + readme_lines[end_index:]
    else:
        # Search for the line where "## 🎖️ Credits" starts to insert the ROADMAP block before it
        credits_index = next((i for i, line in enumerate(readme_lines) if line.strip() == "## 🎖️ Credits:"), None)
        if credits_index is not None:
            print("'CREDITS' block found but 'ROADMAP' block not found")
            updated_readme = readme_lines[:credits_index] + [roadmap_content] + readme_lines[credits_index:]
        else:
            # If "## 🎖️ Credits" is not found, simply add it to the end of the file
            print("'CREDITS' block not found")
            updated_readme = readme_lines + [roadmap_content]
    # Write the updated content to the README file
    with open(readme_file, "w", encoding="utf-8") as f:
        f.writelines(updated_readme)
# ------------------------ END OF HELPERS ---------------------------------


def main(compiler='pyinstaller', compile_in_one_file=COMPILE_IN_ONE_FILE):
    """
    Entry point for the build script:
      - Detects OS/arch
      - Creates build_info.txt
      - Extracts RELEASE-NOTES.md body from CHANGELOG.md
      - Invokes compilation (PyInstaller or Nuitka)
    """
    # =======================
    # Create global variables
    # =======================
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global TOOL_SOURCE_NAME
    global TOOL_VERSION_WITHOUT_V
    global TOOL_NAME_VERSION
    global root_dir
    global tool_name_with_version_os_arch
    global script_zip_file
    global archive_path_relative

    # Detect the operating system and architecture
    OPERATING_SYSTEM = get_os(use_logger=False)
    ARCHITECTURE = get_arch(use_logger=False)

    # Script names
    TOOL_SOURCE_NAME = f"{TOOL_NAME}.py"
    TOOL_VERSION_WITHOUT_V = _get_clean_version(TOOL_VERSION)
    TOOL_NAME_VERSION = f"{TOOL_NAME}_{TOOL_VERSION}"

    # Get the working directory
    root_dir = os.getcwd()
    # Get the root directory one level above the working directory
    # root_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

    # Calculate the relative path
    tool_name_with_version_os_arch = f"{TOOL_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    script_zip_file = Path(f"./PhotoMigrator-builds/{TOOL_VERSION_WITHOUT_V}/{tool_name_with_version_os_arch}.zip").resolve()
    archive_path_relative = os.path.relpath(script_zip_file, root_dir)
    # ========================
    # End of global variables
    # ========================

    _clear_screen()
    print("")
    print("=================================================================================================")
    print(f"INFO:    Running Main Module - main(compiler={compiler}, compile_in_one_file={compile_in_one_file})...")
    print("=================================================================================================")
    print("")

    # print("Adding neccesary packets to Python environment before to compile...")
    # subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    # subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', './requirements.txt'])
    # if OPERATING_SYSTEM == 'windows' and ARCHITECTURE == 'x64)':
    #     subprocess.run([sys.executable, '-m', 'pip', 'install', 'windows-curses'])
    # print("")

    if TOOL_VERSION:
        print(f"TOOL_VERSION found: {TOOL_VERSION_WITHOUT_V}")
    else:
        print("Caanot find TOOL_VERSION.")

    # Extract the RELEASE-NOTES body and add ROADMAP to the README.md file
    # print("Extracting body of RELEASE-NOTES and adding ROADMAP to file README.md...")
    print("Extracting body of RELEASE-NOTES...")

    # Paths for CHANGELOG.md, RELEASE-NOTES.md, README.md and ROADMAP.md
    download_filepath = os.path.join(root_dir, 'DOWNLOAD.md')
    changelog_filepath = os.path.join(root_dir, 'CHANGELOG.md')
    current_release_filepath = os.path.join(root_dir, 'RELEASE-NOTES.md')
    roadmap_filepath = os.path.join(root_dir, 'ROADMAP.md')
    readme_filepath = os.path.join(root_dir, 'README.md')

    # Extract the body of the current Release from CHANGELOG.md
    _extract_release_body(input_file=changelog_filepath, output_file=current_release_filepath, download_file=download_filepath)
    print(f"File '{current_release_filepath}' created successfully!.")

    # Add the ROADMAP into the README file
    # _add_roadmap_to_readme(readme_filepath, roadmap_filepath)
    # print(f"File 'README.md' updated successfully with ROADMAP.md")

    # Save build_info.txt into a text file
    with open(os.path.join(root_dir, 'build_info.txt'), 'w') as file:
        file.write('OPERATING_SYSTEM=' + OPERATING_SYSTEM + '\n')
        file.write('ARCHITECTURE=' + ARCHITECTURE + '\n')
        file.write('TOOL_NAME=' + TOOL_NAME + '\n')
        file.write('TOOL_VERSION=' + TOOL_VERSION_WITHOUT_V + '\n')
        file.write('ROOT_PATH=' + root_dir + '\n')
        file.write('ARCHIVE_PATH=' + archive_path_relative + '\n')
        print('')
        print(f'OPERATING_SYSTEM: {OPERATING_SYSTEM}')
        print(f'ARCHITECTURE: {ARCHITECTURE}')
        print(f'TOOL_NAME: {TOOL_NAME}')
        print(f'TOOL_VERSION: {TOOL_VERSION_WITHOUT_V}')
        print(f'ROOT_PATH: {root_dir}')
        print(f'ARCHIVE_PATH: {archive_path_relative}')

    ok = True
    # Run compile
    if compiler:
        ok = compile(compiler=compiler, compile_in_one_file=compile_in_one_file)
    return ok


def compile(compiler='pyinstaller', compile_in_one_file=COMPILE_IN_ONE_FILE):
    """
    Compiles the tool using the selected compiler (PyInstaller or Nuitka),
    then packages the output and cleans temporary folders/files.

    Args:
        compiler (str): 'pyinstaller' or 'nuitka'
        compile_in_one_file (bool): True for onefile mode, False for onedir/standalone.

    Returns:
        bool: True if compilation succeeded, otherwise False.
    """
    global OPERATING_SYSTEM
    global ARCHITECTURE
    global TOOL_SOURCE_NAME
    global TOOL_VERSION_WITHOUT_V
    global TOOL_NAME_VERSION
    global root_dir
    global tool_name_with_version_os_arch
    global script_zip_file
    global archive_path_relative

    # Initialize variables
    TOOL_NAME_WITH_VERSION_OS_ARCH      = f"{TOOL_NAME_VERSION}_{OPERATING_SYSTEM}_{ARCHITECTURE}"
    splash_image                        = "assets/logos/logo_17_1024x1024.png"  # Splash image for Windows
    gpth_folder                         = FOLDERNAME_GPTH
    exif_folder                         = FOLDERNAME_EXIFTOOL
    gpth_tool                           = os.path.join(gpth_folder, f"gpth-{GPTH_VERSION}-{OPERATING_SYSTEM}-{ARCHITECTURE}.ext")
    exif_tool                           = os.path.join(exif_folder, "<ZIP_NAME>.zip")
    exif_folder_dest                    = exif_folder
    if OPERATING_SYSTEM == 'windows':
        script_compiled = f'{TOOL_NAME}.exe'
        script_compiled_with_version_os_arch_extension = f"{TOOL_NAME_WITH_VERSION_OS_ARCH}.exe"
        gpth_tool = gpth_tool.replace(".ext", ".exe")
        exif_tool = exif_tool.replace('<ZIP_NAME>', 'windows')
    else:
        if compiler == 'pyinstaller':
            script_compiled = f'{TOOL_NAME}'
        else:
            script_compiled = f'{TOOL_NAME}.bin'
        script_compiled_with_version_os_arch_extension = f"{TOOL_NAME_WITH_VERSION_OS_ARCH}.run"
        gpth_tool = gpth_tool.replace(".ext", ".bin")
        exif_tool = exif_tool.replace('<ZIP_NAME>', 'others')

    # Use _resolve_internal_path to access files or directories that will be packaged in the binary executable mode
    gpth_tool_path = _resolve_internal_path(gpth_tool)

    # Ensure exec permissions for gpth binary file
    _ensure_executable(gpth_tool_path)

    # Append build_info.txt with compilation metadata
    with open(os.path.join(root_dir, 'build_info.txt'), 'a') as file:
        file.write('COMPILER=' + str(compiler) + '\n')
        file.write('SCRIPT_COMPILED=' + os.path.abspath(script_compiled_with_version_os_arch_extension) + '\n')
        file.write('GPTH_TOOL=' + gpth_tool + '\n')
        file.write('EXIF_TOOL=' + exif_tool + '\n')
        print('')
        print(f'COMPILER: {compiler}')
        print(f'COMPILE_IN_ONE_FILE: {compile_in_one_file}')
        print(f'SCRIPT_COMPILED: {script_compiled}')
        print(f'GPTH_TOOL: {gpth_tool}')
        print(f'EXIF_TOOL: {exif_tool}')

    print("")
    print("=================================================================================================")
    print(f"INFO:    Compiling with '{compiler}' for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}'...")
    print("=================================================================================================")
    print("")

    success = False
    # ===============================================================================================================================================
    # COMPILE WITH PYINSTALLER...
    # ===============================================================================================================================================
    if compiler == 'pyinstaller':
        print("Compiling with Pyinstaller...")
        import PyInstaller.__main__

        # Build and dist folders for PyInstaller
        build_path = "./pyinstaller_build"
        dist_path = "./pyinstaller_dist"

        # Delete temporary files and directories from previous compilations
        print("Removing temporary files from previous compilations...")
        Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare PyInstaller command
        pyinstaller_command = ['./src/' + TOOL_SOURCE_NAME]

        # onefile or onedir mode
        if compile_in_one_file:
            pyinstaller_command.extend(["--onefile"])
        else:
            pyinstaller_command.extend(['--onedir'])

        # Add splash image to .exe file (only supported in Windows)
        if OPERATING_SYSTEM == 'windows':
            pyinstaller_command.extend(("--splash", splash_image))

        # Add generic arguments to PyInstaller
        pyinstaller_command.extend(["--noconfirm"])
        pyinstaller_command.extend(("--distpath", dist_path))
        pyinstaller_command.extend(("--workpath", build_path))
        pyinstaller_command.extend(("--add-data", gpth_tool + ':gpth_tool'))

        # If INCLUDE_EXIF_TOOL is True, unzip, adjust permissions, and include ExifTool files in the compiled binary
        if INCLUDE_EXIF_TOOL:
            # Unzip ExifTool and include it in the compiled binary with PyInstaller
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            # exif_folder_tmp = _unzip_to_temp(exif_tool)
            # Better avoid using _unzip_to_temp() to reduce the chance of anti-virus detection
            exif_folder_tmp = f"exif_tool_extracted"
            _unzip(exif_tool, exif_folder_tmp)

            # Grant execution permission to exiftool
            exiftool_bin = Path(exif_folder_tmp) / "exiftool"
            if exiftool_bin.exists():
                _ensure_executable(exiftool_bin)

            # Add ExifTool files to the binary
            pyinstaller_command.extend(("--add-data", f"{exif_folder_tmp}:{exif_folder_dest}"))

            # Walk exif_folder_tmp to add all files and subfolders to the binary file
            # (no simpler way found for PyInstaller)
            for path in Path(exif_folder_tmp).rglob('*'):
                if path.is_dir():
                    # Check if it contains at least one file
                    has_files = any(f.is_file() for f in path.iterdir())
                    if not has_files:
                        continue  # Skip folders without files
                    relative_path = path.relative_to(exif_folder_tmp).as_posix()
                    dest_path = f"{exif_folder_dest}/{relative_path}"
                    src_path = path.as_posix()
                    # Add all files directly inside that folder
                    pyinstaller_command.extend(("--add-data", f"{src_path}:{dest_path}"))

        # On Linux, set runtime tmp dir to /var/tmp for Synology compatibility
        # (/tmp does not have access rights in Synology NAS)
        if OPERATING_SYSTEM == 'linux':
            pyinstaller_command.extend(("--runtime-tmpdir", '/var/tmp'))

        # Run PyInstaller with the configured settings
        print_arguments_pretty(pyinstaller_command, title="Pyinstaller Arguments", use_logger=False, use_custom_print=False)

        try:
            PyInstaller.__main__.run(pyinstaller_command)
            print("[OK] PyInstaller finished successfully.")
            success = True
        except SystemExit as e:
            if e.code == 0:
                print("[OK] PyInstaller finished successfully.")
                success = True
            else:
                print(f"[ERROR] PyInstaller failed with error code: {e.code}")

    # ===============================================================================================================================================
    # COMPILE WITH NUITKA...
    # ===============================================================================================================================================
    elif compiler == 'nuitka':
        print("Compiling with Nuitka...")
        # # Force C Compiler based on the Platform used (it is better to let Nuita find the best C Compilar installed on the system)
        # if ARCHITECTURE in ["amd64", "x86_64", "x64"]:
        #     os.environ['CC'] = 'gcc'
        # elif ARCHITECTURE in ["arm64", "aarch64"]:
        #     if sys.platform == "linux":
        #         os.environ['CC'] = 'aarch64-linux-gnu-gcc'
        #     elif sys.platform == "darwin":
        #         os.environ['CC'] = 'clang'  # explicit for macOS
        # else:
        #     print(f"Unknown architecture: {ARCHITECTURE}")
        #     return False
        # print("")

        # Build and dist folders for Nuitka
        dist_path = "./nuitka_dist"
        build_path = f"{dist_path}/{TOOL_NAME}.build"

        # Delete temporary files and directories from previous compilations
        print("Removing temporary files from previous compilations...")
        Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
        shutil.rmtree(build_path, ignore_errors=True)
        shutil.rmtree(dist_path, ignore_errors=True)
        print("")

        # Prepare Nuitka command
        nuitka_command = [sys.executable, '-m', 'nuitka', './src/' + TOOL_SOURCE_NAME]

        # onefile or standalone mode
        if compile_in_one_file:
            nuitka_command.extend(['--onefile'])
            # nuitka_command.append('--onefile-no-compression)
            # if OPERATING_SYSTEM == 'windows':
            #     nuitka_command.extend([f'--onefile-windows-splash-screen-image={splash_image}'])
        else:
            nuitka_command.extend(['--standalone'])

        # Add generic arguments to Nuitka
        nuitka_command.extend([
            '--jobs=4',
            '--assume-yes-for-downloads',
            '--enable-plugin=tk-inter',
            '--disable-cache=ccache',
            '--lto=yes',
            '--nofollow-imports',
            '--nofollow-import-to=unused_module',

            # '--remove-output',
            f'--output-dir={dist_path}',
            f'--include-data-file={gpth_tool}={gpth_tool}',

            f'--windows-icon-from-ico=./assets/ico/PhotoMigrator.ico',
            f'--copyright={COPYRIGHT_TEXT}',
            f"--company-name={TOOL_NAME}",
            f"--product-name={TOOL_NAME}",
            f"--file-description={TOOL_NAME_VERSION} by Jaime Tur",
            f"--file-version={TOOL_VERSION_WITHOUT_V.split('-')[0]}",
            f"--product-version={TOOL_VERSION_WITHOUT_V.split('-')[0]}",
        ])

        # If INCLUDE_EXIF_TOOL is True, unzip, adjust permissions, and include ExifTool files in the compiled binary
        if INCLUDE_EXIF_TOOL:
            # Unzip ExifTool and include it in the compiled binary with Nuitka
            print("\nUnzipping EXIF Tool to include it in binary compiled file...")
            # exif_folder_tmp = _unzip_to_temp(exif_tool)
            # Better avoid using _unzip_to_temp() to reduce the chance of anti-virus detection
            exif_folder_tmp = f"exif_tool_extracted"
            _unzip(exif_tool, exif_folder_tmp)

            # Grant execution permission to exiftool
            exiftool_bin = Path(exif_folder_tmp) / "exiftool"
            if exiftool_bin.exists():
                _ensure_executable(exiftool_bin)

            # Add ExifTool files to the binary
            nuitka_command.extend([f'--include-data-files={exif_folder_tmp}={exif_folder_dest}/=**/*.*'])
            nuitka_command.extend([f'--include-data-dir={exif_folder_tmp}={exif_folder_dest}'])
            # nuitka_command.extend(['--include-data-dir=../exif_tool=exif_tool'])

        # Set runtime tmp dir to a specific folder within /var/tmp or %TEMP% to reduce the chance of anti-virus detection
        if OPERATING_SYSTEM != 'windows':
            # On Linux, use /var/tmp for Synology compatibility (/tmp does not have access rights in Synology NAS)
            nuitka_command.extend([f'--onefile-tempdir-spec=/var/tmp/{TOOL_NAME_WITH_VERSION_OS_ARCH}'])
        else:
            nuitka_command.extend([rf'--onefile-tempdir-spec=%TEMP%\{TOOL_NAME_WITH_VERSION_OS_ARCH}'])

        # Run Nuitka with the configured settings
        print_arguments_pretty(nuitka_command, title="Nuitka Arguments", use_logger=False, use_custom_print=False)
        result = subprocess.run(nuitka_command)
        success = (result.returncode == 0)
        if not success:
            print(f"[ERROR] Nuitka failed with code: {result.returncode}")

    else:
        print(f"Compiler '{compiler}' not supported. Valid options are 'pyinstaller' or 'nuitka'. Compilation skipped.")
        return success

    # ===============================================================================================================================================
    # PACKAGING AND CLEANUP...
    # ===============================================================================================================================================
    # If compilation failed, exit early.
    if success:
        print("[OK] Compilation process finished successfully.")
    else:
        print("[ERROR] There was some error during compilation process.")
        return success

    # Compiled script absolute path
    script_compiled_abs_path = ''
    if compiler == 'pyinstaller':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{script_compiled}")
    elif compiler == 'nuitka':
        script_compiled_abs_path = os.path.abspath(f"{dist_path}/{TOOL_NAME}.dist/{script_compiled}")

    # Move the compiled script to the parent folder
    if compile_in_one_file:
        print('')
        print(f"Moving compiled script '{script_compiled_with_version_os_arch_extension}'...")
        shutil.move(f'{dist_path}/{script_compiled}', f'./{script_compiled_with_version_os_arch_extension}')
        # Compress the folder with the compiled script and the files/directories to include
        _include_extrafiles_and_zip(f'./{script_compiled_with_version_os_arch_extension}', script_zip_file)
        script_compiled_abs_path = os.path.abspath(script_compiled_with_version_os_arch_extension)

    # Delete temporary files and folders created during compilation
    print('')
    print("Deleting temporary compilation files...")
    Path(f"{TOOL_NAME}.spec").unlink(missing_ok=True)
    Path(f"nuitka-crash-report.xml").unlink(missing_ok=True)
    shutil.rmtree(build_path, ignore_errors=True)
    try:
        shutil.rmtree(exif_folder_tmp, ignore_errors=True)
    except NameError:
        pass
    if compile_in_one_file:
        shutil.rmtree(dist_path, ignore_errors=True)
    print("Temporary compilation files successfully deleted!")

    print('')
    print("=================================================================================================")
    print(f"Compilation for OS: '{OPERATING_SYSTEM}' and architecture: '{ARCHITECTURE}' completed successfully!!!")
    print('')
    print(f"SCRIPT_COMPILED: {script_compiled_abs_path}")
    print(f"SCRIPT_ZIPPED  : {script_zip_file}")
    print('')
    print("All compilations have finished successfully.")
    print("=================================================================================================")
    print('')
    return success


if __name__ == "__main__":
    # Read arguments if they exist
    arg1 = sys.argv[1] if len(sys.argv) > 1 else None
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None

    # Parse compiler argument
    if arg1 is not None:
        arg_lower = arg1.lower()
        if arg_lower in ['false', '-false', '--false', '0', 'no', 'n', 'none', '-none', '--none', 'no-compile', '-no-compile', '--no-compile', 'no-compiler', '-no-compiler', '--no-compiler']:
            compiler = None
        elif arg_lower in ['pyinstaller', '-pyinstaller', '--pyinstaller']:
            compiler = 'pyinstaller'
        elif arg_lower in ['nuitka', '-nuitka', '--nuitka']:
            compiler = 'nuitka'
        else:
            print(f"Unrecognized compiler: '{arg1}'. Using 'PyInstaller' by default...")
            compiler = 'pyinstaller'
    else:
        compiler = False  # Default value

    # Parse onefile/onedir argument
    if arg2 is not None:
        arg_lower = arg2.lower()
        if arg_lower in ['false', '-false', '--false', '0', 'no', 'n', 'none', '-none', '--none', 'onedir', '-onedir', '--onedir', 'standalone', '-standalone', '--standalone', 'no-onefile', '-no-onefile', '--no-onefile']:
            onefile = False
        else:
            onefile = True
    else:
        onefile = True  # Default value

    ok = main(compiler=compiler, compile_in_one_file=onefile)
    if ok:
        print('INFO    : COMPILATION FINISHED SUCCESSFULLY!')
        sys.exit(0)
    else:
        print('ERROR   : BUILD FINISHED WITH ERRORS!')
        sys.exit(-1)
