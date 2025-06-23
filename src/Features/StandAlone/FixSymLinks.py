import os

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import TAG_INFO, LOGGER
from Utils.GeneralUtils import tqdm


def fix_symlinks_broken(input_folder, step_name="", log_level=None):
    """
    Searches and fixes broken symbolic links in a directory and its subdirectories.
    Optimized to handle very large numbers of files by indexing files beforehand.

    :param step_name:
    :param log_level:
    :param input_folder: Path (relative or absolute) to the main directory where the links should be searched and fixed.
    :return: A tuple containing the number of corrected symlinks and the number of symlinks that could not be corrected.
    """

    # ===========================
    # AUX FUNCTIONS
    # ===========================
    def build_file_index(input_folder, log_level=None):
        """
        Index all non-symbolic files in the directory and its subdirectories by their filename.
        Returns a dictionary where keys are filenames and values are lists of their full paths.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            file_index = {}
            # Contar el total de carpetas
            total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
            if total_files == 0:
                return file_index
            # Mostrar la barra de progreso basada en carpetas
            with tqdm(total=total_files, smoothing=0.1, desc=f"{TAG_INFO}{step_name}Building Index files in '{input_folder}'", unit=" files") as pbar:
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

    def find_real_file(file_index, target_name, log_level=None):
        """
        Given a pre-built file index (dict: filename -> list of paths),
        return the first available real file path for the given target_name.
        If multiple matches exist, return the first found.
        If none is found, return None.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            if target_name in file_index and file_index[target_name]:
                return file_index[target_name][0]
            return None

    # ===========================
    # END AUX FUNCTIONS
    # ===========================
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        corrected_count = 0
        failed_count = 0
        # Validate the directory existence
        if not os.path.isdir(input_folder):
            LOGGER.error(f"{step_name}The directory '{input_folder}' does not exist or is not valid.")
            return 0, 0
        # Step 1: Index all real non-symbolic files
        file_index = build_file_index(input_folder)
        # Step 2: Search for broken symbolic links and fix them using the index
        already_warned = False
        total_files = sum([len(files) for _, _, files in os.walk(input_folder)])  # Contar el total de carpetas
        if total_files == 0:
            corrected_count, failed_count
        with tqdm(total=total_files, smoothing=0.1, desc=f"{TAG_INFO}{step_name}Fixing Symbolic Links in '{input_folder}'", unit=" files") as pbar:  # Mostrar la barra de progreso basada en carpetas
            for path, _, files in os.walk(input_folder):
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if os.path.islink(file_path) and not os.path.exists(file_path):
                        # It's a broken symbolic link
                        target = os.readlink(file_path)
                        # LOGGER.info(f"Broken link found: {file_path} -> {target}")
                        target_name = os.path.basename(target)

                        fixed_path = find_real_file(file_index, target_name)
                        if fixed_path:
                            # Create the correct symbolic link
                            relative_path = os.path.relpath(fixed_path, start=os.path.dirname(file_path))
                            # LOGGER.info(f"Fixing link: {file_path} -> {relative_path}")
                            os.unlink(file_path)
                            os.symlink(relative_path, file_path)
                            corrected_count += 1
                        else:
                            if not already_warned:
                                LOGGER.warning("")
                                already_warned = True
                            LOGGER.warning(f"{step_name}Could not find the file for {file_path} within {input_folder}")
                            failed_count += 1
        return corrected_count, failed_count
