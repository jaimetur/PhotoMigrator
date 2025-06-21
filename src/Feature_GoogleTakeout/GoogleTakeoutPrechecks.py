import os
import zipfile

from Globals import GlobalVariables as GV
from CustomLogger import set_log_level


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-CHECKS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def unpack_zips(input_folder, unzip_folder, step_name="", log_level=None):
    """ Unzips all ZIP files from a folder into another """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        if not os.path.exists(input_folder):
            GV.LOGGER.error(f"{step_name}ZIP folder '{input_folder}' does not exist.")
            return
        os.makedirs(unzip_folder, exist_ok=True)
        for zip_file in os.listdir(input_folder):
            if zip_file.endswith(".zip"):
                zip_path = os.path.join(input_folder, zip_file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        GV.LOGGER.info(f"{step_name}Unzipping: {zip_file}")
                        zip_ref.extractall(unzip_folder)
                except zipfile.BadZipFile:
                    GV.LOGGER.error(f"{step_name}Could not unzip file: {zip_file}")


def contains_takeout_structure(input_folder, step_name="", log_level=None):
    """
    Iteratively scans directories using a manual stack instead of recursion or os.walk.
    This can reduce overhead in large, nested folder structures.
    """
    with set_log_level(GV.LOGGER, log_level):
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"{step_name}Looking for Google Takeout structure in input folder...")
        stack = [input_folder]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            name = entry.name
                            if name.startswith("Photos from ") and name[12:16].isdigit():
                                # GV.LOGGER.info(f"Found Takeout structure in folder: {entry.path}")
                                GV.LOGGER.info(f"{step_name}Found Takeout structure in folder: {current}")
                                return True
                            stack.append(entry.path)
            except PermissionError:
                GV.LOGGER.warning(f"{step_name}Permission denied accessing: {current}")
            except Exception as e:
                GV.LOGGER.warning(f"{step_name}Error scanning {current}: {e}")
        GV.LOGGER.info(f"{step_name}No Takeout structure found in input folder.")
        return False
