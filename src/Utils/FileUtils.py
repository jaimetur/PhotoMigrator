import fnmatch
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
import unicodedata

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import LOGGER, MSG_TAGS, FOLDERNAME_ALBUMS
from Utils.GeneralUtils import tqdm


# ---------------------------------------------------------------------------------------------------------------------------
# FILES & FOLDERS MANAGEMENT FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def fix_paths(path, log_level=None):
    """
    Normalizes path separators to the current OS separator.

    Args:
        path (str): Input path (may contain '/' or '\\').
        log_level: Unused (kept for API consistency).

    Returns:
        str: Path using the current OS separator.
    """
    fixed_path = path.replace('/', os.path.sep).replace('\\', os.path.sep)
    return fixed_path


def is_valid_path(path, log_level=None):
    """
    Checks whether the path is valid on the current platform.
    — It must be an absolute path.
    — It must not contain invalid characters for the operating system.
    — It must not use an incorrect format for the platform.
    """
    from pathvalidate import validate_filepath, ValidationError

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Checks whether `path` is valid as a filepath on the current platform.
            validate_filepath(path, platform="auto")
            return True
        except ValidationError as e:
            LOGGER.error(f"Path validation ERROR: {e}")
            return False

def dir_exists(dir):
    """
    Checks whether a directory exists.

    Args:
        dir (str | Path): Directory path.

    Returns:
        bool: True if the directory exists and is a directory, otherwise False.
    """
    return os.path.isdir(dir)

def delete_subfolders(input_folder, folder_name_to_delete, step_name="", log_level=None):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        input_folder (str, Path): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
        :param step_name:
        :param log_level:
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Count total number of folders
        total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(input_folder)])
        # Show progress bar based on folders
        with tqdm(total=total_dirs, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Deleting files within subfolders '{folder_name_to_delete}' in '{input_folder}'", unit=" subfolders") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=False):
                for folder in dirs:
                    pbar.update(1)
                    if folder == folder_name_to_delete:
                        dir_path = os.path.join(path, folder)
                        try:
                            shutil.rmtree(dir_path)
                            # LOGGER.info(f"Deleted directory: {dir_path}")
                        except Exception as e:
                            LOGGER.error(f"{step_name}Error deleting {dir_path}: {e}")


def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False, log_level=None):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
        :param log_level:
        :param input_folder:
        :param exclude_subfolders:
        :param max_depth:
        :param flatten_root_folder:
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Count number of path separators in input_folder
        sep_input = input_folder.count(os.sep)
        # Convert wildcard patterns to regex patterns for matching
        exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
        for path, dirs, files in tqdm(os.walk(input_folder, topdown=True), ncols=120, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Flattening Subfolders in '{input_folder}'", unit=" subfolders"):
            # Count number of path separators in the current root folder
            sep_root = int(path.count(os.sep))
            depth = sep_root - sep_input
            LOGGER.verbose(f"Depth: {depth}")
            if depth > max_depth:
                # Skip deeper levels
                continue
            # If flatten_root_folder=True, then only the root folder needs to be flattened, and it will recursively flatten all subfolders
            if flatten_root_folder:
                dirs = [os.path.basename(path)]
                path = os.path.dirname(path)
            # Process files in subfolders and move them to the root of the subfolder
            for folder in dirs:
                # If 'Albums' folder is found, invoke the Tool recursively on its subdirectories
                if os.path.basename(folder) == f"{FOLDERNAME_ALBUMS}":
                    for album_subfolder in dirs:
                        subfolder_path = os.path.join(path, album_subfolder)
                        flatten_subfolders(input_folder=subfolder_path, exclude_subfolders=exclude_subfolders, max_depth=max_depth+1)
                    continue
                # Skip processing if the current directory matches any exclude pattern
                if any(pattern.match(os.path.basename(folder)) for pattern in exclude_patterns):
                    # LOGGER.warning(f"Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                    continue
                subfolder_path = os.path.join(path, folder)
                # LOGGER.info(f"Flattening folder: '{dir_name}'")
                for sub_root, _, sub_files in os.walk(subfolder_path):
                    for file_name in sub_files:
                        file_path = os.path.join(sub_root, file_name)
                        new_location = os.path.join(subfolder_path, file_name)
                        # Avoid overwriting files by appending a numeric suffix if needed
                        if os.path.exists(new_location):
                            base, ext = os.path.splitext(file_name)
                            counter = 1
                            while os.path.exists(new_location):
                                new_location = os.path.join(subfolder_path, f"{base}_{counter}{ext}")
                                counter += 1
                        shutil.move(file_path, new_location)
        for path, dirs, files in os.walk(input_folder, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(path, dir)
                if not os.listdir(dir_path):  # If the folder is empty
                    os.rmdir(dir_path)


def remove_empty_dirs(input_folder, log_level=None):
    """
    Remove empty directories recursively.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        for path, dirs, files in os.walk(input_folder, topdown=False):
            filtered_dirnames = [d for d in dirs if d != '@eaDir']
            if not filtered_dirnames and not files:
                try:
                    os.rmdir(path)
                    LOGGER.info(f"Removed empty directory {path}")
                except OSError:
                    pass


def remove_folder(folder, step_name='', log_level=None):
    """
    Removes the specified `folder` and all of its contents, logging events
    at the specified `log_level`.

    Parameters:
    - folder (str or Path): Path to the folder to remove.
    - log_level (str): Logging level to use ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').

    Returns:
    - True if the folder was removed successfully.
    - False if an error occurred.
    """
    with set_log_level(LOGGER, log_level):  # Temporarily adjust LOGGER’s level for this operation
        folder_path = Path(folder)
        try:
            LOGGER.debug(f"{step_name}Attempting to remove: {folder_path}")
            shutil.rmtree(folder_path)
            LOGGER.info(f"{step_name}Folder '{folder_path}' removed successfully.")
            return True

        except FileNotFoundError:
            LOGGER.info(f"{step_name}Folder '{folder_path}' was not found. Nothing to remove!")
            return False

        except PermissionError:
            LOGGER.error(f"{step_name}Insufficient permissions to remove: '{folder_path}'.")
            return False

        except Exception as e:
            LOGGER.critical(f"{step_name}Unexpected error while removing '{folder_path}': {e}")
            return False


def contains_zip_files(input_folder, log_level=None):
    """
    Checks whether the given folder contains at least one .zip file.

    Args:
        input_folder (str | Path): Folder to scan.
        log_level: Optional log level override for this operation.

    Returns:
        bool: True if any file in the folder ends with '.zip', otherwise False.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Searching .zip files in input folder...")
        for file in os.listdir(input_folder):
            if file.endswith('.zip'):
                return True
        LOGGER.info(f"No .zip files found in input folder.")
        return False


def normalize_path(path, log_level=None):
    """
    Normalizes a filesystem path (collapses redundant separators and up-level references).

    Args:
        path (str | Path): Input path.
        log_level: Optional log level override for this operation.

    Returns:
        str: Normalized path string.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # return os.path.normpath(path).strip(os.sep)
        return os.path.normpath(path)


def zip_folder(temp_dir, output_file):
    """
    Creates a ZIP archive from the contents of a folder.

    Notes:
        - Preserves directory structure relative to `temp_dir`.
        - Adds empty directories to the ZIP as well.

    Args:
        temp_dir (str | Path): Folder whose contents will be zipped.
        output_file (str | Path): Destination ZIP file path.
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

def unzip_to_temp(zipfile_path):
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


def unzip(zipfile_path, dest_folder):
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


def unzip_flatten(zipfile_path, dest_folder):
    """
    Unzips a ZIP file into the specified destination folder,
    stripping the top-level directory if all files are inside it.

    Args:
        zipfile_path (str): Path to the ZIP file.
        dest_folder (str): Destination folder where the contents will be extracted.
    """
    if not os.path.exists(zipfile_path):
        raise FileNotFoundError(f"The ZIP file does not exist: {zipfile_path}")
    if not zipfile.is_zipfile(zipfile_path):
        raise zipfile.BadZipFile(f"The file is not a valid ZIP archive: {zipfile_path}")
    with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
        # Get the list of all file paths in the ZIP
        members = zip_ref.namelist()
        # Check if all files are under a common top-level folder
        top_level_dirs = set(p.split('/')[0] for p in members if '/' in p)
        if len(top_level_dirs) == 1:
            prefix_to_strip = next(iter(top_level_dirs)) + '/'
        else:
            prefix_to_strip = None
        for member in members:
            target_path = member
            if prefix_to_strip and member.startswith(prefix_to_strip):
                target_path = member[len(prefix_to_strip):]
            if target_path:
                final_path = os.path.join(dest_folder, target_path)
                if member.endswith('/'):
                    os.makedirs(final_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    with zip_ref.open(member) as source, open(final_path, 'wb') as target:
                        target.write(source.read())
        print(f"ZIP file extracted to: {dest_folder}")



def sanitize_and_unpack_zips(input_folder, unzip_folder, step_name="", log_level=None):
    """ Unzips all ZIP files from a folder into another (per-entry sanitized to avoid _ADMIN_*_WhiteSpaceConflict). """
    # ------------------------------- minimal helpers (inline) -------------------------------
    def sanitize_component(name, is_dir):
        # Normalize to NFC, strip trailing spaces/dots, replace control/SMB-illegal chars, avoid empty
        s = unicodedata.normalize('NFC', name)                      # compose accents (no visual loss)
        s = re.sub(r'[ .]+$', '', s)                                # drop trailing spaces/dots
        s = re.sub(r'[\x00-\x1F\x7F]', '_', s)                      # control chars
        s = re.sub(r'[:*?"<>|]', '_', s)                            # SMB/Windows illegal
        if s == '':                                                 # keep a safe placeholder
            s = '_'
        return s

    def safe_join_under(root_dir, parts):
        # Prevent absolute paths and traversal; always stay under root_dir
        tgt = Path(root_dir)
        for p in parts:
            if p in ('', '.', '..') or re.match(r'^[A-Za-z]:$', p):  # ignore unsafe parts and drive letters
                continue
            tgt = tgt / p
        try:
            # Ensure target remains under root_dir
            tgt.resolve().relative_to(Path(root_dir).resolve())
        except Exception:
            tgt = Path(root_dir) / "_unsafe" / Path(*parts)
        return tgt

    def unique_path(parent, name, is_dir):
        # Resolve collisions by appending ' (n)' before extension (files) or at end (dirs)
        base, ext = (name, '') if is_dir else os.path.splitext(name)
        candidate = name
        n = 1
        while (parent / candidate).exists():
            n += 1
            candidate = f"{base} ({n}){ext}"
        return parent / candidate
    # ---------------------------------------------------------------------------------------

    with set_log_level(LOGGER, log_level):
        if not os.path.exists(input_folder):
            LOGGER.warning(f"{step_name}ZIP folder '{input_folder}' does not exist.")
            return
        os.makedirs(unzip_folder, exist_ok=True)

        for zip_file in os.listdir(input_folder):
            if not zip_file.lower().endswith(".zip"):
                continue

            zip_path = os.path.join(input_folder, zip_file)
            try:
                with zipfile.ZipFile(zip_path, 'r', allowZip64=True) as zip_ref:
                    LOGGER.info(f"{step_name}Unzipping: {zip_file}")
                    for info in zip_ref.infolist():
                        # Split path into components and sanitize each one independently
                        raw_parts = Path(info.filename).parts
                        is_dir = info.is_dir()
                        sanitized_parts = []
                        for i, comp in enumerate(raw_parts):
                            comp_is_dir = is_dir or (i < len(raw_parts) - 1)
                            sanitized_parts.append(sanitize_component(comp, comp_is_dir))

                        # Build safe destination under unzip_folder
                        dst_path = safe_join_under(unzip_folder, sanitized_parts)
                        parent = dst_path.parent
                        parent.mkdir(parents=True, exist_ok=True)

                        if is_dir:
                            # Create directory (handle potential collisions after sanitization)
                            if not dst_path.exists():
                                dst_path.mkdir(parents=True, exist_ok=True)
                            continue

                        # Handle file collisions
                        if dst_path.exists():
                            dst_path = unique_path(parent, dst_path.name, is_dir=False)

                        # Stream copy file content
                        with zip_ref.open(info, 'r') as src, open(dst_path, 'wb') as out:
                            shutil.copyfileobj(src, out, length=1024 * 1024)

                LOGGER.debug(f"{step_name}Done: {zip_file}")

            except zipfile.BadZipFile:
                LOGGER.warning(f"{step_name}Could not unzip file (BadZipFile): {zip_file}")
            except Exception as e:
                LOGGER.warning(f"{step_name}Unzip error for {zip_file}: {e}")
