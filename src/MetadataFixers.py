import os,sys
import platform
import subprocess
import logging
import select
import threading
import queue
import re
import time
from packaging.version import Version

from CustomLogger import set_log_level
from GlobalVariables import LOGGER, GPTH_VERSION
from Utils import get_os, get_arch, resource_path, ensure_executable, run_command, print_arguments_pretty

def fix_metadata_with_gpth_tool(input_folder, output_folder, capture_output=False, capture_errors=True, print_messages=True, skip_extras=False, symbolic_albums=False, move_takeout_folder=False, ignore_takeout_structure=False, step_name="", log_level=logging.INFO):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        """Runs the GPTH Tool command to process photos."""
        input_folder = os.path.abspath(input_folder)
        output_folder = os.path.abspath(output_folder)
        LOGGER.info("")
        LOGGER.info(f"INFO    : {step_name}Running GPTH Tool...")
        LOGGER.info(f"INFO    : {step_name}GPTH Version : '{GPTH_VERSION}'")
        LOGGER.info(f"INFO    : {step_name}Input Folder : '{input_folder}'")
        LOGGER.info(f"INFO    : {step_name}Output Folder: '{output_folder}'")

        # Detect the operating system
        current_os = get_os(step_name=step_name)
        current_arch = get_arch(step_name=step_name)

        # Determine the Tool name based on the OS
        tool_name = f"gpth-{GPTH_VERSION}-{current_os}-{current_arch}"
        if current_os in ("linux", "macos"):
            tool_name  +=".bin"
        elif current_os == "windows":
            tool_name += ".exe"
        else:
            LOGGER.error(f"ERROR   : {step_name}Invalid OS: {current_os}. Exiting...")
            sys.exit(-1)

        LOGGER.info(f"INFO    : {step_name}Using GPTH Tool file: '{tool_name}'...")
        # Usar resource_path para acceder a archivos o directorios que se empaquetarán en el modo de ejecutable binario:
        gpth_tool_path = resource_path(os.path.join("gpth_tool", tool_name))

        # Check if the file exists
        if not os.path.exists(gpth_tool_path):
            LOGGER.error(f"ERROR   : {step_name}❌ GPTH was not found at: {gpth_tool_path}")
            return False
        else:
            LOGGER.info(f"INFO    : {step_name}✅ GPTH found at: {gpth_tool_path}")

        # Ensure exec permissions for the binary file
        ensure_executable(gpth_tool_path)

        # Basic GPTH Command
        gpth_command = [gpth_tool_path, "--input", input_folder, "--output", output_folder, "--no-interactive"]

        # If ignore_takeout_structure is True, we append --fix input_folder to the gpth tool call
        if ignore_takeout_structure:
            gpth_command.append("--fix")
            gpth_command.append(input_folder)

        # By default, force --no-divide-to-dates and the Tool will create date structure if needed
        if Version(GPTH_VERSION) >= Version("3.6.0"):
            # The new version of GPTH have changed this argument:
            gpth_command.append("--divide-to-dates=0")  # 0: No divide, 1: year, 2: year/month, 3: year/month/day
        else:
            # For previous versions of the original GPTH tool
            gpth_command.append("--no-divide-to-dates") 

        # Append --albums shortcut / duplicate-copy based on value of flag -sa, --symbolic-albums
        gpth_command.append("--albums")
        if symbolic_albums:
            LOGGER.info(f"INFO    : {step_name}Symbolic Albums will be created with links to the original files...")
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

        if Version(GPTH_VERSION) >= Version("3.6.0"):
            # Use the new feature to Delete the "supplemental-metadata" suffix from .json files to ensure that script works correctly
            # Flag removed on 4.0.7 (incorporated in the native logic)
            # gpth_command.append("--modify-json")

            # Use the new feature to Transform Pixel .MP or .MV extensions to ".mp4"
            gpth_command.append("--transform-pixel-mp")

            # Use the new feature to Set creation time equal to the last modification date at the end of the program. (Only Windows supported)
            gpth_command.append("--update-creation-time")

        if Version(GPTH_VERSION) >= Version("4.0.0"):
            gpth_command.append("--write-exif")

        if Version(GPTH_VERSION) >= Version("4.0.8"):
            gpth_command.append("--fix-extensions=standard")
            # gpth_command.append("--fix-extensions=conservative")
            # gpth_command.append("--fix-extensions=solo")
            # gpth_command.append("--fix-extensions=none")

        try:
            command = ' '.join(gpth_command)
            LOGGER.info(f"INFO    : {step_name}🛠️ Fixing and 🧩 organizing all your Takeout photos and videos.")
            LOGGER.info(f"INFO    : {step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂.")
            LOGGER.debug(f"DEBUG   : {step_name}Running GPTH with following command: {command}")
            print_arguments_pretty(gpth_command, title='GPTH Command', step_name=step_name, use_logger=True)

            # Run GPTH Tool
            ok = run_command(gpth_command, LOGGER, capture_output=capture_output, capture_errors=capture_errors, print_messages=print_messages, step_name=step_name)      # Shows the output in real time and capture it to the LOGGER.

            # Rename folder 'ALL_PHOTOS' by 'No-Albums'
            all_photos_path = os.path.join(output_folder, 'ALL_PHOTOS')
            others_path = os.path.join(output_folder, 'No-Albums')
            if os.path.exists(all_photos_path) and os.path.isdir(all_photos_path):
                os.rename(all_photos_path, others_path)

            # Check the result of GPTH process
            if ok==0:
                LOGGER.info(f"INFO    : {step_name}✅ GPTH Tool fixing completed successfully.")
                return True
            else:
                # TODO: Change this to False and remove comment below when GPTH fix the return code
                # LOGGER.error(f"ERROR   : {step_name}❌ GPTH Tool fixing failed.")
                # return False
                return True
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR   : {step_name}❌ GPTH Tool fixing failed:\n{e.stderr}")
            return False
        

def fix_metadata_with_exif_tool(output_folder, log_level=logging.INFO):
    """Runs the EXIF Tool command to fix photo metadata."""
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Fixing EXIF metadata in '{output_folder}'...")
        # Detect the operating system
        current_os = platform.system()
        # Determine the Tool name based on the OS
        script_name = ""
        if current_os == "Linux":
            script_name = "exiftool"
        elif current_os == "Darwin":
            script_name = "exiftool"
        elif current_os == "Windows":
            script_name = "exiftool.exe"
        # Usar resource_path para acceder a archivos o directorios:
        exif_tool_path = resource_path(os.path.join("exif_tool",script_name))

        # Ensure exec permissions for the binary file
        ensure_executable(exif_tool_path)

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
            LOGGER.info(f"INFO    : EXIF Tool fixing completed successfully.")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR   : EXIF Tool fixing failed:\n{e.stderr}")
        