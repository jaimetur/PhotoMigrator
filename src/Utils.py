import os, sys
import shutil
import zipfile
import fnmatch
import re
import stat
from datetime import datetime
from tqdm import tqdm
import platform

######################
# FUNCIONES AUXILIARES
######################
def run_from_synology():
    return os.path.exists('/etc.defaults/synoinfo.conf')

def check_OS_and_Terminal():
    from GlobalVariables import LOGGER
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    if current_os == "Linux":
        if run_from_synology():
            LOGGER.info(f"INFO    : Script running on Linux System in a Synology NAS")
        else:
            LOGGER.info(f"INFO    : Script running on Linux System")
    elif current_os == "Darwin":
        LOGGER.info(f"INFO    : Script running on MacOS System")
    elif current_os == "Windows":
        LOGGER.info(f"INFO    : Script running on Windows System")
    else:
        LOGGER.error(f"ERROR   : Unsupported Operating System: {current_os}")

    if sys.stdout.isatty():
        LOGGER.info("INFO    : Interactive (TTY) terminal detected for stdout")
    else:
        LOGGER.info("INFO    : Non-Interactive (Non-TTY) terminal detected for stdout")
    if sys.stdin.isatty():
        LOGGER.info("INFO    : Interactive (TTY) terminal detected for stdin")
    else:
        LOGGER.info("INFO    : Non-Interactive (Non-TTY) terminal detected for stdin")
    LOGGER.info("")

def count_files_in_folder(folder_path):
    """Counts the number of files in a folder."""
    from GlobalVariables import LOGGER
    total_files = 0
    for path, dirs, files in os.walk(folder_path):
        total_files += len(files)
    return total_files

def unpack_zips(zip_folder, takeout_folder):
    """Unzips all ZIP files from a folder into another."""
    from GlobalVariables import LOGGER
    if not os.path.exists(zip_folder):
        LOGGER.error(f"ERROR   : ZIP folder '{zip_folder}' does not exist.")
        return
    os.makedirs(takeout_folder, exist_ok=True)
    for zip_file in os.listdir(zip_folder):
        if zip_file.endswith(".zip"):
            zip_path = os.path.join(zip_folder, zip_file)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    LOGGER.info(f"INFO    : Unzipping: {zip_file}")
                    zip_ref.extractall(takeout_folder)
            except zipfile.BadZipFile:
                LOGGER.error(f"ERROR   : Could not unzip file: {zip_file}")

def fix_mp4_files(input_folder):
    """
    Look for all .MP4 files that have the same name of any Live picture and is in the same folder.
    If found any, then copy the .json file of the original Live picture and change its name to the name of the .MP4 file
    """
    # Traverse all subdirectories in the input folder
    from GlobalVariables import LOGGER
    
    # Contar el total de carpetas
    mp4_files = []
    for _, _, files in os.walk(input_folder, topdown=True):
        for file in files:
            if file.lower().endswith('.mp4'):
                mp4_files.append(file)
    total_files = len(mp4_files)
    # Mostrar la barra de progreso basada en carpetas
    with tqdm(total=total_files, smoothing=0.1,  desc=f"INFO    : Fixing .MP4 files in '{input_folder}'", unit=" files") as pbar:
        for path, _, files in os.walk(input_folder):
            # Filter files with .mp4 extension (case-insensitive)
            mp4_files = [f for f in files if f.lower().endswith('.mp4')]
            for mp4_file in mp4_files:
                pbar.update(1)
                # Get the base name of the MP4 file (without extension)
                mp4_base_name = os.path.splitext(mp4_file)[0]

                # Define possible JSON extensions (case-insensitive)
                json_extensions = ['.heic.json', '.jpg.json', '.jpeg.json']
                # Search for JSON files with the same base name but ignoring case for the extension
                for ext in json_extensions:
                    json_file_candidates = [
                        f for f in files
                        if f.startswith(mp4_base_name) and f.lower().endswith(ext.lower())
                    ]
                    for json_file in json_file_candidates:
                        json_path = os.path.join(path, json_file)
                        # Generate the new name for the duplicated file
                        new_json_name = f"{mp4_file}.json"
                        new_json_path = os.path.join(path, new_json_name)
                        # Check if the target file already exists to avoid overwriting
                        if not os.path.exists(new_json_path):
                            # Copy the original JSON file to the new file
                            shutil.copy(json_path, new_json_path)
                            # LOGGER.info(f"INFO    : Fixed: {json_path} -> {new_json_path}")
                        else:
                            pass
                            # LOGGER.info(f"INFO    : Skipped: {new_json_path} already exists")


def sync_mp4_timestamps_with_images(input_folder):
    """
    Look for .MP4 files with the same name of any Live Picture file (.HEIC, .JPG, .JPEG) in the same folder.
    If found, then set the date and time of the .MP4 file to the same date and time of the original Live Picture.
    """
    from GlobalVariables import LOGGER
    
    # Contar el total de carpetas
    total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
    # Mostrar la barra de progreso basada en carpetas
    with tqdm(total=total_files, smoothing=0.1,  desc=f"INFO    : Synchronizing .MP4 files with Live Pictures in '{input_folder}'", unit=" files") as pbar:
        for path, _, files in os.walk(input_folder):
            # Crear un diccionario que mapea nombres base a extensiones y nombres de archivos
            file_dict = {}
            for filename in files:
                pbar.update(1)
                name, ext = os.path.splitext(filename)
                base_name = name.lower()
                ext = ext.lower()
                if base_name not in file_dict:
                    file_dict[base_name] = {}
                file_dict[base_name][ext] = filename  # Guardar el nombre original del archivo
            for base_name, ext_file_map in file_dict.items():
                if '.mp4' in ext_file_map:
                    mp4_filename = ext_file_map['.mp4']
                    mp4_file_path = os.path.join(path, mp4_filename)
                    # Buscar si existe un archivo .heic, .jpg o .jpeg con el mismo nombre
                    image_exts = ['.heic', '.jpg', '.jpeg']
                    image_file_found = False
                    for image_ext in image_exts:
                        if image_ext in ext_file_map:
                            image_filename = ext_file_map[image_ext]
                            image_file_path = os.path.join(path, image_filename)
                            # Obtener los tiempos de acceso y modificación del archivo de imagen
                            image_stats = os.stat(image_file_path)
                            atime = image_stats.st_atime  # Tiempo de último acceso
                            mtime = image_stats.st_mtime  # Tiempo de última modificación
                            # Aplicar los tiempos al archivo .MP4
                            os.utime(mp4_file_path, (atime, mtime))
                            # LOGGER.info(f"INFO    : Date and time attributes synched for: {os.path.relpath(mp4_file_path,input_folder)} using:  {os.path.relpath(image_file_path,input_folder)}")
                            image_file_found = True
                            break  # Salir después de encontrar el primer archivo de imagen disponible
                    if not image_file_found:
                        #LOGGER.warning(f"WARNING : Cannot find Live picture file to sync with: {os.path.relpath(mp4_file_path,input_folder)}")
                        pass


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[]):
    """
    Organizes files into subfolders based on their modification date.

    Args:
        input_folder (str): The base directory containing the files.
        type (str): 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (list): A list of subfolder names to exclude from processing.

    Raises:
        ValueERROR   : If the value of `type` is invalid.
    """
    from GlobalVariables import LOGGER
    if type not in ['year', 'year/month', 'year-month']:
        raise ValueError("The 'type' parameter must be 'year' or 'year/month'.")
    
    # Contar el total de carpetas
    total_files = 0
    for _, dirs, files in os.walk(input_folder):
        dirs[:] = [d for d in dirs if d not in exclude_subfolders]
        total_files += sum([len(files)])
    # Mostrar la barra de progreso basada en carpetas
    with tqdm(total=total_files, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Organizing files with {type} structure in '{input_folder}'", unit=" files") as pbar:
        for path, dirs, files in os.walk(input_folder, topdown=True):
            # Exclude specified subfolders
            dirs[:] = [d for d in dirs if d not in exclude_subfolders]
            for file in files:
                pbar.update(1)
                file_path = os.path.join(path, file)
                if not os.path.isfile(file_path):
                    continue
                # Get the file's modification date
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                year_folder = mod_time.strftime('%Y')
                if type == 'year':
                    # Organize by year only
                    target_dir = os.path.join(path, year_folder)
                elif type == 'year/month':
                    # Organize by year/month
                    month_folder = mod_time.strftime('%m')
                    target_dir = os.path.join(path, year_folder, month_folder)
                elif type == 'year-month':
                     year_month_folder = mod_time.strftime('%Y-%m')
                     target_dir = os.path.join(path, year_month_folder)
                # Create the target directory (and subdirectories) if they don't exist
                os.makedirs(target_dir, exist_ok=True)
                # Move the file to the target directory
                shutil.move(file_path, os.path.join(target_dir, file))
    LOGGER.info(f"INFO    : Organization completed. Folder structure per {type} have been created in '{input_folder}'.")


def copy_move_folder(src, dst, ignore_patterns=None, move=False):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    from GlobalVariables import LOGGER
    try:
        if not is_valid_path(src):
            LOGGER.error(f"ERROR   : The path '{src}' is not valid for the execution plattform. Cannot copy/move folders from it.")
            return False
        if not is_valid_path(dst):
            LOGGER.error(f"ERROR   : The path '{dst}' is not valid for the execution plattform. Cannot copy/move folders to it.")
            return False

        def ignore_function(dir, files):
            if ignore_patterns:
                # Convert to a list if a single pattern is provided
                patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
                ignored = []
                for pattern in patterns:
                    ignored.extend(fnmatch.filter(files, pattern))
                return set(ignored)
            return set()

        # Ensure the source folder exists
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source folder does not exist: '{src}'")
        # Create the destination folder if it doesn't exist
        os.makedirs(dst, exist_ok=True)

        # Ignore function
        action = 'Moving' if move else 'Copying'
        if move:
            # Contar el total de carpetas
            total_files = sum([len(files) for _, _, files in os.walk(src)])
            # Mostrar la barra de progreso basada en carpetas
            with tqdm(total=total_files, ncols=120, smoothing=0.1,  desc=f"INFO    : {action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                for path, dirs, files in os.walk(src, topdown=True):
                    pbar.update(1)
                    # Compute relative path
                    rel_path = os.path.relpath(path, src)
                    # Destination path
                    dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                    # Apply ignore function to files and dirs
                    ignore = ignore_function(path, files + dirs)
                    # Filter dirs in-place to skip ignored directories
                    dirs[:] = [d for d in dirs if d not in ignore]
                    # Create destination directory
                    os.makedirs(dest_path, exist_ok=True)
                    # Move files
                    for file in files:
                        if file not in ignore:
                            src_file = os.path.join(path, file)
                            dst_file = os.path.join(dest_path, file)
                            shutil.move(src_file, dst_file)
                LOGGER.info(f"INFO    : Folder moved successfully from {src} to {dst}")
        else:
            # Copy the folder contents
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
            LOGGER.info(f"INFO    : Folder copied successfully from {src} to {dst}")
            return True
    except Exception as e:
        LOGGER.error(f"ERROR   : Error {action} folder: {e}")
        return False


def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str): Path to the input folder containing the albums.
        albums_subfolder (str): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    from GlobalVariables import LOGGER
    def safe_move(folder_path, albums_path):
        destination = os.path.join(albums_path, os.path.basename(folder_path))
        if os.path.exists(destination):
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            else:
                os.remove(destination)
        shutil.move(folder_path, albums_path)

    if isinstance(exclude_subfolder, str):
        exclude_subfolder = [exclude_subfolder]
    albums_path = os.path.join(input_folder, albums_subfolder)
    exclude_subfolder_paths = [os.path.abspath(os.path.join(input_folder, sub)) for sub in (exclude_subfolder or [])]
    subfolders = os.listdir(input_folder)
    subfolders = [subfolder for subfolder in subfolders if not subfolder=='@eaDir' and not subfolder=='No-Albums']
    for subfolder in tqdm(subfolders, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Moving Albums in '{input_folder}' to Subolder '{albums_subfolder}'", unit=" albums"):
        folder_path = os.path.join(input_folder, subfolder)
        if os.path.isdir(folder_path) and subfolder != albums_subfolder and os.path.abspath(folder_path) not in exclude_subfolder_paths:
            # LOGGER.info(f"INFO    : Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'")
            os.makedirs(albums_path, exist_ok=True)
            safe_move(folder_path, albums_path)


def change_file_extension(input_folder, current_extension, new_extension):
    """
    Changes the extension of all files with a specific extension
    within a folder and its subfolders.

    Args:
        input_folder (str): Path to the root folder to search for files.
        current_extension (str): Current file extension (includes the dot, e.g., ".txt").
        new_extension (str): New file extension (includes the dot, e.g., ".md").

    Returns:
        None
    """
    from GlobalVariables import LOGGER
    
    # Contar el total de carpetas
    total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
    # Mostrar la barra de progreso basada en carpetas
    with tqdm(total=total_files, ncols=120, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Changing File Extensions in '{input_folder}'", unit=" files") as pbar:
        for path, dirs, files in os.walk(input_folder):
            for file in files:
                pbar.update(1)
                # Check if the file has the current extension
                if file.endswith(current_extension):
                    # Build the full paths of the original and new files
                    original_file = os.path.join(path, file)
                    new_file = os.path.join(path, file.replace(current_extension, new_extension))
                    # Rename the file
                    os.rename(original_file, new_file)
                    # LOGGER.info(f"INFO    : Renamed: {original_file} -> {new_file}")


def delete_subfolders(input_folder, folder_name_to_delete):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        input_folder (str): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
    """
    from GlobalVariables import LOGGER
    
    # Contar el total de carpetas
    total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(input_folder)])
    # Mostrar la barra de progreso basada en carpetas
    with tqdm(total=total_dirs, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Deleting files within subfolders '{folder_name_to_delete}' in '{input_folder}'", unit=" subfolders") as pbar:
        for path, dirs, files in os.walk(input_folder, topdown=False):
            for folder in dirs:
                pbar.update(1)
                if folder == folder_name_to_delete:
                    dir_path = os.path.join(path, folder)
                    try:
                        shutil.rmtree(dir_path)
                        # LOGGER.info(f"INFO    : Deleted directory: {dir_path}")
                    except Exception as e:
                        LOGGER.error(f"ERROR   : Error deleting {dir_path}: {e}")


def remove_empty_dirs(input_folder):
    """
    Remove empty directories recursively.
    """
    from GlobalVariables import LOGGER
    for path, dirs, files in os.walk(input_folder, topdown=False):
        filtered_dirnames = [d for d in dirs if d != '@eaDir']
        if not filtered_dirnames and not files:
            try:
                os.rmdir(path)
                LOGGER.info(f"INFO    : Removed empty directory {path}")
            except OSError:
                pass


def flatten_subfolders(input_folder, exclude_subfolders=[], max_depth=0, flatten_root_folder=False):
    """
    Flatten subfolders inside the given folder, moving all files to the root of their respective subfolders.

    Args:
        input_folder (str): Path to the folder to process.
        exclude_subfolders (list or None): List of folder name patterns (using wildcards) to exclude from flattening.
    """
    from GlobalVariables import LOGGER
    # Count number of sep of input_folder
    sep_input = input_folder.count(os.sep)
    # Convert wildcard patterns to regex patterns for matching
    exclude_patterns = [re.compile(fnmatch.translate(pattern)) for pattern in exclude_subfolders]
    for path, dirs, files in tqdm(os.walk(input_folder, topdown=True), ncols=120, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Flattening Subfolders in '{input_folder}'", unit=" subfolders"):
        # Count number of sep of root folder
        sep_root = int(path.count(os.sep))
        depth = sep_root - sep_input
        # print (f"Depth: {depth}")
        if depth > max_depth:
            # Skip deeper levels
            continue
        # If flatten_root_folder=True, then only need to flatten the root folder and it recursively will flatten all subfolders
        if flatten_root_folder:
            dirs = [os.path.basename(path)]
            path = os.path.dirname(path)
        # Process files in subfolders and move them to the root of the subfolder
        for folder in dirs:
            # If 'Albums' folder is found, invoke the script recursively on its subdirectories
            if os.path.basename(folder) == "Albums":
                for album_subfolder in dirs:
                    subfolder_path = os.path.join(path, album_subfolder)
                    flatten_subfolders(input_folder=subfolder_path, exclude_subfolders=exclude_subfolders, max_depth=max_depth+1)
                continue
            # Skip processing if the current directory matches any exclude pattern
            if any(pattern.match(os.path.basename(folder)) for pattern in exclude_patterns):
                # LOGGER.warning(f"WARNING : Folder: '{dir_name}' not flattened due to is one of the exclude subfolder given in '{exclude_subfolders}'")
                continue
            subfolder_path = os.path.join(path, folder)
            # LOGGER.info(f"INFO    : Flattening folder: '{dir_name}'")
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
            if not os.listdir(dir_path):  # Si la carpeta está vacía
                os.rmdir(dir_path)


def fix_symlinks_broken(input_folder):
    """
    Searches and fixes broken symbolic links in a directory and its subdirectories.
    Optimized to handle very large numbers of files by indexing files beforehand.

    :param input_folder: Path (relative or absolute) to the main directory where the links should be searched and fixed.
    :return: A tuple containing the number of corrected symlinks and the number of symlinks that could not be corrected.
    """
    from GlobalVariables import LOGGER
    # ===========================
    # AUX FUNCTIONS
    # ===========================
    def build_file_index(input_folder):
        """
        Index all non-symbolic files in the directory and its subdirectories by their filename.
        Returns a dictionary where keys are filenames and values are lists of their full paths.
        """
        file_index = {}
        # Contar el total de carpetas
        total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_files, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Building Index files in '{input_folder}'", unit=" files") as pbar:
            for path, _, files in os.walk(input_folder):
                for fname in files:
                    pbar.update(1)
                    full_path = os.path.join(path, fname)
                    # Only index real files (not symbolic links)
                    if os.path.isfile(full_path) and not os.path.islink(full_path):
                        # Add the path to the index
                        if fname not in file_index:
                            file_index[fname] = []
                        file_index[fname].append(full_path)
        return file_index

    def find_real_file(file_index, target_name):
        """
        Given a pre-built file index (dict: filename -> list of paths),
        return the first available real file path for the given target_name.
        If multiple matches exist, return the first found.
        If none is found, return None.
        """
        if target_name in file_index and file_index[target_name]:
            return file_index[target_name][0]
        return None
    # ===========================
    # END AUX FUNCTIONS
    # ===========================

    corrected_count = 0
    failed_count = 0
    # Validate the directory existence
    if not os.path.isdir(input_folder):
        LOGGER.error(f"ERROR   : The directory '{input_folder}' does not exist or is not valid.")
        return 0, 0

    # Step 1: Index all real non-symbolic files
    file_index = build_file_index(input_folder)

    # Step 2: Search for broken symbolic links and fix them using the index
    already_warned = False
    total_files = sum([len(files) for _, _, files in os.walk(input_folder)]) # Contar el total de carpetas
    with tqdm(total=total_files, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Fixing Symbolic Links in '{input_folder}'", unit=" files") as pbar: # Mostrar la barra de progreso basada en carpetas
        for path, _, files in os.walk(input_folder):
            for file in files:
                pbar.update(1)
                file_path = os.path.join(path, file)
                if os.path.islink(file_path) and not os.path.exists(file_path):
                    # It's a broken symbolic link
                    target = os.readlink(file_path)
                    # LOGGER.info(f"INFO    : Broken link found: {file_path} -> {target}")
                    target_name = os.path.basename(target)

                    fixed_path = find_real_file(file_index, target_name)
                    if fixed_path:
                        # Create the correct symbolic link
                        relative_path = os.path.relpath(fixed_path, start=os.path.dirname(file_path))
                        # LOGGER.info(f"INFO    : Fixing link: {file_path} -> {relative_path}")
                        os.unlink(file_path)
                        os.symlink(relative_path, file_path)
                        corrected_count += 1
                    else:
                        if not already_warned:
                            LOGGER.warning("")
                            already_warned=True
                        LOGGER.warning(f"WARNING : Could not find the file for {file_path} within {input_folder}")
                        failed_count += 1
    return corrected_count, failed_count


def rename_album_folders(input_folder: str):
    from GlobalVariables import LOGGER
    # ===========================
    # AUXILIARY FUNCTIONS
    # ===========================
    def clean_name(input_string: str) -> str:
        import re
        input_string = input_string.strip()
        # Remove leading underscores or hyphens
        input_string = re.sub(r'^[-_]+', '', input_string)
        # Replace underscores or hyphens between numbers with dots (2023_11_23 → 2023.11.23)
        input_string = re.sub(r'(?<=\d)[_-](?=\d)', '.', input_string)
        # Convert yyyymmdd to yyyy.mm.dd (for years starting with 19xx or 20xx)
        input_string = re.sub(r'\b((19|20)\d{2})(\d{2})(\d{2})\b', r'\1.\3.\4', input_string)
        # Convert yyyymm to yyyy.mm (for years starting with 19xx or 20xx)
        input_string = re.sub(r'\b((19|20)\d{2})(\d{2})\b', r'\1.\3', input_string)
        # Convert ddmmyyyy to yyyy.mm.dd
        input_string = re.sub(r'\b(\d{2})(\d{2})((19|20)\d{2})\b', r'\3.\2.\1', input_string)
        # Convert mmyyyy to yyyy.mm
        input_string = re.sub(r'\b(\d{2})((19|20)\d{2})\b', r'\2.\1', input_string)
        # Replace underscores or hyphens between letters with spaces
        input_string = re.sub(r'(?<=[a-zA-Z])[_-](?=[a-zA-Z])', ' ', input_string)
        # Replace year ranges separated by dots with hyphens (1995.2004 → 1995-2004)
        input_string = re.sub(r'\b((19|20)\d{2})\.(?=(19|20)\d{2})', r'\1-', input_string)
        # Replace underscore/hyphen preceded by digit and followed by letter (1_A → 1 - A)
        input_string = re.sub(r'(?<=\d)[_-](?=[a-zA-Z])', ' - ', input_string)
        # Replace the last dot with an underscore in dddd.dd.dd.dd format anywhere in the string
        input_string = re.sub(r'((19|20)\d{2}\.\d{2}\.\d{2})\.(\d{2})', r'\1_\3', input_string)
        return input_string

    def get_year_range(folder: str) -> str:
        import os
        from datetime import datetime
        from GlobalVariables import LOGGER
        try:
            files = [os.path.join(folder, f) for f in os.listdir(folder)]
            files = [f for f in files if os.path.isfile(f)]
            if files:
                oldest_file = min(files, key=os.path.getmtime)
                latest_file = max(files, key=os.path.getmtime)
                oldest_year = datetime.fromtimestamp(os.path.getmtime(oldest_file)).year
                latest_year = datetime.fromtimestamp(os.path.getmtime(latest_file)).year
                # Return a single year if oldest and latest match
                if oldest_year == latest_year:
                    # LOGGER.info(f"INFO    : Single year {oldest_year} obtained from {folder}")
                    return str(oldest_year)
                else:
                    # LOGGER.info(f"INFO    : Year range {oldest_year}-{latest_year} obtained from {folder}")
                    return f"{oldest_year}-{latest_year}"
        except Exception as e:
            LOGGER.error(f"ERROR   : Error obtaining year range: {e}")
        return None
    # ===========================
    # END AUX FUNCTIONS
    # ===========================

    # Iterate over folders in albums_folder (only first level)
    renamed_album_folders = 0
    duplicates_album_folders = 0
    duplicates_albums_fully_merged = 0
    duplicates_albums_not_fully_merged = 0
    total_folders = os.listdir(input_folder)
    info_actions = []
    warning_actions = []
    for original_folder_name in tqdm(total_folders, smoothing=0.1, file=LOGGER.tqdm_stream, desc=f"INFO    : Renaming Albums folders in '{input_folder}'", unit=" folders"):
        item_path = os.path.join(input_folder, original_folder_name)
        if os.path.isdir(item_path):
            cleaned_folder_name = clean_name(original_folder_name)
            # If folder name does not start with a year (19xx or 20xx)
            if not re.match(r'^(19|20)\d{2}', cleaned_folder_name):
                year_range = get_year_range(item_path)
                if year_range:
                    cleaned_folder_name = f"{year_range} - {cleaned_folder_name}"
                    info_actions.append(f"INFO    : Added year prefix '{year_range}' to folder: '{os.path.basename(cleaned_folder_name)}'")
            # Skip renaming if the clean name is the same as the original
            if cleaned_folder_name != original_folder_name:
                new_folder_path = os.path.join(input_folder, cleaned_folder_name)
                if os.path.exists(new_folder_path):
                    duplicates_album_folders += 1
                    warning_actions.append(f"WARNING : Folder '{new_folder_path}' already exists. Merging contents...")
                    for item in os.listdir(item_path):
                        src = os.path.join(item_path, item)
                        dst = os.path.join(new_folder_path, item)
                        if os.path.exists(dst):
                            # Compare file sizes to decide if the original should be deleted
                            if os.path.isfile(dst) and os.path.getsize(src) == os.path.getsize(dst):
                                os.remove(src)
                                info_actions.append(f"INFO    : Deleted duplicate file: '{src}'")
                        else:
                            shutil.move(src, dst)
                            info_actions.append(f"INFO    : Moved '{src}' → '{dst}'")
                    # Check if the folder is empty before removing it
                    if not os.listdir(item_path):
                        os.rmdir(item_path)
                        info_actions.append(f"INFO    : Removed empty folder: '{item_path}'")
                        duplicates_albums_fully_merged += 1
                    else:
                        # LOGGER.warning(f"WARNING : Folder not empty, skipping removal: {item_path}")
                        duplicates_albums_not_fully_merged += 1
                else:
                    if item_path != new_folder_path:
                        os.rename(item_path, new_folder_path)
                        info_actions.append(f"INFO    : Renamed folder: '{os.path.basename(item_path)}' → '{os.path.basename(new_folder_path)}'")
                        renamed_album_folders += 1
    for info_action in info_actions:
        LOGGER.info(info_action)
    for warning_action in warning_actions:
        LOGGER.warning(warning_actions)

    return renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged

def confirm_continue():
    from GlobalVariables import LOGGER
    while True:
        response = input("Do you want to continue? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            LOGGER.info(f"INFO    : Continuing...")
            return True
        elif response in ['no', 'n']:
            LOGGER.info(f"INFO    : Operation canceled.")
            return False
        else:
            LOGGER.warning(f"WARNING : Invalid input. Please enter 'yes' or 'no'.")

def remove_quotes(s: str) -> str:
    """
    Elimina todas las comillas simples y dobles al inicio o fin de la cadena.
    """
    return s.strip('\'"')

def contains_zip_files(input_folder):
    for file in os.listdir(input_folder):
        if file.endswith('.zip'):
            return True
    return False

def remove_server_name(path):
    # Expresión regular para rutas Linux (///servidor/)
    path = re.sub(r'///[^/]+/', '///', path)
    # Expresión regular para rutas Windows (\\servidor\)
    path = re.sub(r'\\\\[^\\]+\\', '\\\\', path)
    return path

def force_remove_directory(path):
    from GlobalVariables import LOGGER
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if os.path.exists(path):
        shutil.rmtree(path, onerror=onerror)
        LOGGER.info(f"INFO    : The folder '{path}' and all its contant have been deleted.")
    else:
        print(f"WARNNING: Cannot delete the folder '{path}'.")

def fix_paths(path):
    fixed_path = path.replace('/', os.path.sep).replace('\\', os.path.sep)
    return fixed_path

def is_valid_path(path):
    """
    Verifica si la ruta es válida en la plataforma actual.
    - Debe ser una ruta absoluta.
    - No debe contener caracteres inválidos para el sistema operativo.
    - No debe usar un formato incorrecto para la plataforma.
    """
    from pathvalidate import validate_filepath, ValidationError
    from GlobalVariables import LOGGER
    try:
        # Verifica si `ruta` es válida como path en la plataforma actual.
        validate_filepath(path, platform="auto")
        return True
    except ValidationError as e:
        LOGGER.error(f"ERROR   : Path validation ERROR   : {e}")
        return False

