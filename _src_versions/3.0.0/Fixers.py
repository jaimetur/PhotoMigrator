import os,sys
import platform
import subprocess

def resource_path(relative_path):
    """Obtener la ruta absoluta al recurso, manejando el entorno de PyInstaller."""
    from LoggerConfig import LOGGER
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def fix_metadata_with_gpth_tool(input_folder, output_folder, skip_extras=False, symbolic_albums=False, move_takeout_folder=False, ignore_takeout_structure=False):
    """Runs the GPTH Tool command to process photos."""
    from LoggerConfig import LOGGER
    LOGGER.info(f"INFO: Running GPTH Tool from '{input_folder}' to '{output_folder}'...")
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    tool_name = ""
    if current_os == "Linux":
        tool_name = "gpth_linux.bin"
    elif current_os == "Darwin":
        tool_name = "gpth_macos.bin"
    elif current_os == "Windows":
        tool_name = "gpth_windows.exe"
    # Usar resource_path para acceder a archivos o directorios:
    gpth_tool_path = resource_path(os.path.join("gpth_tool",tool_name))
    gpth_command = [
        gpth_tool_path,
        "--input", input_folder,
        "--output", output_folder,
        "--no-interactive"
    ]
    # By default force --no-divide-to-dates and the script will create date structure if needed
    gpth_command.append("--no-divide-to-dates")

    # Append --albums shortcut / duplicate-copy based on value of flag -sa, --symbolic-albums
    gpth_command.append("--albums")
    if symbolic_albums:
        LOGGER.info(f"INFO: Symbolic Albums will be created with links to the original files...")
        gpth_command.append("shortcut")
    else:
        gpth_command.append("duplicate-copy")

    # Append --skip-extras to the gpth tool call based on the value of flag -se, --skip-extras
    if skip_extras:
        gpth_command.append("--skip-extras")

    # Append --copy/--no-copy to the gpth tool call based on the values of move_takeout_folder
    if move_takeout_folder:
        gpth_command.append("--no-copy")
    else:
        gpth_command.append("--copy")

    # If ignore_takeout_structure is True, we append --fix input_folder to the gpth tool call
    if ignore_takeout_structure:
        gpth_command.append("--fix")
        gpth_command.append(input_folder)
    try:
        #print (" ".join(gpth_command))
        result = subprocess.run(gpth_command, check=True, capture_output=False)

        # Rename folder 'ALL_PHOTOS' by 'Others'
        all_photos_path = os.path.join(output_folder, 'ALL_PHOTOS')
        others_path = os.path.join(output_folder, 'Others')
        if os.path.exists(all_photos_path) and os.path.isdir(all_photos_path):
            os.rename(all_photos_path, others_path)

        LOGGER.info(f"INFO: GPTH Tool finxing completed successfully.")
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"ERROR: GPTH Tool fixing failed:\n{e.stderr}")

def fix_metadata_with_exif_tool(output_folder):
    """Runs the EXIF Tool command to fix photo metadata."""
    from LoggerConfig import LOGGER
    LOGGER.info(f"INFO: Fixing EXIF metadata in '{output_folder}'...")
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    script_name = ""
    if current_os == "Linux":
        script_name = "exiftool"
    elif current_os == "Darwin":
        script_name = "exiftool"
    elif current_os == "Windows":
        script_name = "exiftool.exe"
    # Usar resource_path para acceder a archivos o directorios:
    exif_tool_path = resource_path(os.path.join("exif_tool",script_name))
    exif_command = [
        exif_tool_path,
        "-overwrite_original",
        "-ExtractEmbedded",
        "-r",
        '-datetimeoriginal<filemodifydate',
        "-if", "(not $datetimeoriginal or ($datetimeoriginal eq '0000:00:00 00:00:00'))",
        output_folder
    ]
    try:
        # print (" ".join(exif_command))
        result = subprocess.run(exif_command, check=False)
        LOGGER.info(f"INFO: EXIF Tool fixing completed successfully.")
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"ERROR: EXIF Tool fixing failed:\n{e.stderr}")