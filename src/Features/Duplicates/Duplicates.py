import csv
import fnmatch
import hashlib
import os
import re
import shutil
import time
from collections import namedtuple
from pathlib import Path

from Core import GlobalVariables as GV
from Core.CustomLogger import set_log_level
from Core.GlobalFunctions import resolve_path
from Core.Utils import remove_empty_dirs, tqdm
from Features.GoogleTakeout import GoogleTakeoutPreprocess as GT_PREP


# ========================
# Find Duolicates Function
# ========================
def find_duplicates(duplicates_action='list', duplicates_folders='./', exclusion_folders=None, deprioritize_folders_patterns=None, timestamp=None, step_name="", log_level=None):
    """
    This function searches for duplicate files based on their size and content (hash),
    ignoring file names or modification dates.

    Selection rules for the principal file:
    1. If duplicates are in multiple input folders, pick from the earliest folder in the provided list.
       If multiple files in that folder, choose shortest filename.
    2. If all duplicates are in one folder, choose shortest filename among them.
    3. With deprioritized folders, any folder matching given patterns is less prioritized.
       Among multiple patterns, the last pattern is highest priority. If all are deprioritized,
       pick from the one with highest priority pattern. If tie remains, apply original logic.

    Additional notes:
    - If find_duplicates_in_folders is a string separated by commas/semicolons, convert to a list.
    - If any folder doesn't exist, log error and return -1.
    - Create "Duplicates" and "Duplicates_<timestamp>" directories, store "Duplicates_<timestamp>.csv".
    - CSV format: Num_Duplicates, Principal, Duplicate, Principal_Path, Duplicate_Path, Action, [Destination if move].
    - Return number of duplicates (excluding principals).
    - If move/remove, perform actions and then remove empty dirs.
    - Ignore files in '@eaDir' subfolders.
    - Patterns are case-insensitive and checked against full paths and each subpart.

    Optimizations:
    - Cache folder priority results to avoid recalculations.
    - Skip symbolic links and inaccessible files early.
    - Only hash files with same size more than once.
    - Maintain a memory of chosen principal folder in ties to keep consistency across sets.
    - Use efficient lookups and caches to reduce overhead in large directories.
    """

    # ===========================
    # AUX FUNCTIONS
    # ===========================

    def calculate_file_hash_optimized(path, full_hash=False, chunk_size=1024 * 1024, log_level=None):
        """
        Calculate the hash of a file. Optionally calculates a partial hash for speed.
        Args:
            path (str): The path to the file.
            full_hash (bool): If True, calculate the full file hash.
                              If False, calculate hash of the first `chunk_size` bytes.
            chunk_size (int): Size of chunks to read from the file.

        Returns:
            str: The calculated hash.
        """
        with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
            hasher = hashlib.md5()
            with open(path, 'rb') as f:
                if not full_hash:
                    # Read only the first `chunk_size` bytes for partial hash
                    chunk = f.read(chunk_size)
                    hasher.update(chunk)
                else:
                    # Calculate the full hash by reading the file in chunks
                    for chunk in iter(lambda: f.read(chunk_size), b''):
                        hasher.update(chunk)
            return hasher.hexdigest()

    def folder_pattern_priority_regex_support(folder, log_level=None):
        """
        Evalúa la prioridad de un folder basándose en patrones fnmatch.
        Retorna (is_deprioritized, priority).
        """
        with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
            # Reutilizar resultados almacenados en caché
            if folder in cache_folders_priority:
                return cache_folders_priority[folder]
            matched_priorities = []
            for i, pattern_lower in enumerate(deprioritize_folders_patterns):
                # Convertimos el patrón fnmatch a regex usando fnmatch.translate,
                # el cual produce un regex anclado, por ejemplo: '(?s:.*Photos from [1-2][0-9][0-9][0-9])\Z'
                regex_pattern = fnmatch.translate(pattern_lower)
                # Removemos la ancla \Z al final para permitir coincidencias parciales
                if regex_pattern.endswith('\\Z'):
                    regex_pattern = regex_pattern[:-2]
                # Ahora usamos re.search en vez de re.fullmatch para permitir coincidencia en cualquier parte
                if re.search(regex_pattern, folder, re.IGNORECASE):
                    matched_priorities.append(i)
                    break  # Nos detenemos al encontrar la primera coincidencia
            if not matched_priorities:
                result = (False, None)
            else:
                result = (True, max(matched_priorities))
            # Guardar el resultado en caché
            cache_folders_priority[folder] = result
            return result

    def remove_empty_dirs(root_dir, log_level=None):
        """
        Remove empty directories recursively.
        """
        with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
            removed_folders = 0
            for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
                filtered_dirnames = [d for d in dirnames if d != '@eaDir']
                if not filtered_dirnames and not filenames:
                    try:
                        os.rmdir(dirpath)
                        removed_folders += 1
                        GV.LOGGER.debug(f"{step_name}Removed empty directory in path {dirpath}")
                    except OSError:
                        pass
            return removed_folders

    def is_under_exclusion(path: str) -> bool:
        """
        True si 'path' es exactamente una ruta excluida o está debajo de alguna de ellas.
        """
        return any(
            path == ex or path.startswith(ex + os.sep)
            for ex in exclusion_folders
        )

    # ===========================
    # INITIALIZATION AND SETUP
    # ===========================
    
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        removed_empty_folders = 0
        if deprioritize_folders_patterns is None:
            deprioritize_folders_patterns = []

        # —————————————
        # NORMALIZAR duplicates_folders
        # —————————————
        if isinstance(duplicates_folders, (str, Path)):
            # Si es str, puede venir "a,b;c", así que lo troceamos
            s = str(duplicates_folders)
            duplicates_folders = [f.strip() for f in re.split(r'[;,]', s) if f.strip()]
        elif isinstance(duplicates_folders, list):
            # Convertimos cada elemento (Path o str) a str limpio
            duplicates_folders = [str(f).strip() for f in duplicates_folders if str(f).strip()]
        else:
            raise TypeError(f"{GV.TAG_ERROR}duplicates_folders must be str, Path or List, no {type(duplicates_folders)}")

        # Convert exclusion_folders to list if is str
        if exclusion_folders is None:
            exclusion_folders = []
        elif isinstance(exclusion_folders, str):
            exclusion_folders = [f.strip() for f in re.split(r'[;,]', exclusion_folders) if f.strip()]

        # ————————————————
        # EXPANDIR a rutas absolutas bajo cada duplicates_folder
        # ————————————————
        abs_exclusions = []
        for excl in exclusion_folders:
            if os.path.isabs(excl):
                abs_exclusions.append(os.path.normpath(excl))
            else:
                for root in duplicates_folders:
                    abs_exclusions.append(
                        os.path.normpath(os.path.join(root, excl))
                    )
        exclusion_folders = abs_exclusions
        GV.LOGGER.debug(f"{step_name} Exclusiones absolutas: {exclusion_folders}")

        if not duplicates_folders:
            duplicates_folders = [resolve_path('../../../../../../../../../')]
        GV.LOGGER.debug(f"{step_name}Checking folder existence")
        for folder in duplicates_folders:
            if not os.path.isdir(folder):
                GV.LOGGER.error(f"{step_name}The folder '{folder}' does not exist.")
                return -1, -1
        duplicates_folders = [os.path.abspath(f) for f in duplicates_folders]
        GV.LOGGER.debug(f"{step_name}Absolute folder paths: {duplicates_folders}")
        if timestamp is None:
            timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
        cache_folders_priority = {}

        # ===========================
        # PROCESSING FILES BY SIZE
        # ===========================
        GV.LOGGER.debug(f"{step_name}Grouping files by size")
        size_dict = {}
        total_folders = 0
        total_files = 0
        total_symlinks = 0
        for folder in duplicates_folders:
            GV.LOGGER.debug(f"{step_name}Walking folder {folder}")

            # ===========================
            # CALCULAR TOTAL DE FICHEROS
            # ===========================
            total_files_to_process = 0
            for path, dirs, files in os.walk(folder, topdown=True):
                # Si el directorio padre ya está excluido, no desciendas más
                if is_under_exclusion(path):
                    dirs[:] = []  # impide seguir profundizando
                    continue

                # Excluir '@eaDir' y subdirectorios inmediatos en exclusion_folders
                dirs[:] = [d for d in dirs
                           if d != '@eaDir'
                           and not is_under_exclusion(os.path.join(path, d))]

                # Sumar ficheros de este nivel
                total_files_to_process += len(files)
            GV.LOGGER.debug(f"{step_name}Total files to process: {total_files_to_process}")

            # Show progress bar per fies
            with tqdm(total=total_files_to_process, smoothing=0.1,  desc=f"{GV.TAG_INFO}{step_name}Processing files'", unit=" files") as pbar:
                # Recursively traverse the folder and excluding '@eaDir' folders
                for path, dirs, files in os.walk(folder, topdown=True):
                    # 1) Si estamos en un árbol excluido, lo saltamos entero
                    if is_under_exclusion(path):
                        dirs[:] = []
                        continue

                    # 2) Filtrar '@eaDir' y cualquier subcarpeta excluida
                    dirs[:] = [d for d in dirs
                               if d != '@eaDir'
                               and not is_under_exclusion(os.path.join(path, d))]

                    total_folders += len(dirs)
                    for file in files:
                        pbar.update(1)
                        total_files += 1
                        full_path = os.path.join(path, file)
                        if os.path.islink(full_path):
                            total_symlinks += 1
                            continue
                        try:
                            file_size = os.path.getsize(full_path)
                        except (PermissionError, OSError):
                            GV.LOGGER.warning(f"{step_name}Skipping inaccessible file {full_path}")
                            continue
                        
                        size_dict.setdefault(file_size, []).append(full_path)

        # Optimización: Filtrar directamente los tamaños con más de un archivo
        sizes_with_duplicates_dict = {size: paths for size, paths in size_dict.items() if len(paths) > 1}
        GV.LOGGER.debug(f"{step_name}Symbolic Links files will be excluded from Find Duplicates Algorithm (they don't use disk space)")
        GV.LOGGER.debug(f"{step_name}Total subfolders found: {total_folders+len(duplicates_folders)}")
        GV.LOGGER.debug(f"{step_name}Total files found: {total_files}")
        GV.LOGGER.debug(f"{step_name}Total Symbolic Links files found: {total_symlinks}")
        GV.LOGGER.debug(f"{step_name}Total files (not Symbolic Links) found: {total_files-total_symlinks}")
        GV.LOGGER.debug(f"{step_name}Total Groups of different files size found: {len(size_dict)}")
        GV.LOGGER.debug(f"{step_name}Filtering out groups with only one file with the same size")
        GV.LOGGER.debug(f"{step_name}Groups with more than one file with the same size found: {len(sizes_with_duplicates_dict)}")
        del size_dict  # Liberar memoria anticipadamente

        # ===============================================================================
        # IF FOUND MORE THAN ONE FILE WITH SAME SIZE, START THE FIND_DUPLICATES ALGORITHM
        # ===============================================================================
        duplicates_counter = 0
        if len(sizes_with_duplicates_dict)>0:
            # ===========================
            # HASHING FILES
            # ===========================
            PARTIAL_HASHES = False
            if PARTIAL_HASHES:
                # Calcular tamaño medio de los archivos en relevant_sizes
                total_size = sum(size * len(paths) for size, paths in sizes_with_duplicates_dict.items())
                total_relevant_files = sum(len(paths) for paths in sizes_with_duplicates_dict.values())
                average_size = total_size // total_relevant_files if total_relevant_files > 0 else 0

                # Ajustar CHUNK_SIZE según el tamaño medio
                if average_size <= 10 * 1024 * 1024:  # ≤ 10 MB
                    CHUNK_SIZE = max(4 * 1024, average_size // 10)  # 10% del tamaño medio, mínimo 4 KB
                elif average_size <= 100 * 1024 * 1024:  # 10 MB - 100 MB
                    CHUNK_SIZE = 1 * 1024 * 1024  # 1 MB
                else:  # > 100 MB
                    CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB
                CHUNK_SIZE = max(4 * 1024, average_size // 100)  # 10% del tamaño medio, mínimo 4 KB

                GV.LOGGER.debug(f"{step_name}Hashing files with same size ")
                GV.LOGGER.debug(f"{step_name}Applying partial/full hashing technique")
                GV.LOGGER.debug(f"{step_name}Using dynamic chunk_size of {round(CHUNK_SIZE / 1024, 0)} KB based on average file size of {round(average_size / 1024, 2)} KB for sizes with more than one file")
                partial_hash_dict = {}
                hash_dict = {}

                GV.LOGGER.debug(f"{step_name}Calculating Partial Hashes (chunk_size={round(CHUNK_SIZE / 1024, 0)} KB) for {len(sizes_with_duplicates_dict)} groups of sizes with more than one file")
                for file_size, paths in tqdm(sizes_with_duplicates_dict.items(), smoothing=0, desc=f"{GV.TAG_INFO}Partial Hashing Progress", unit=" groups"):
                    for path in paths:
                        try:
                            partial_hash = calculate_file_hash_optimized(path, full_hash=False, chunk_size=CHUNK_SIZE)
                            partial_hash_dict.setdefault(partial_hash, []).append(path)
                        except (PermissionError, OSError):
                            GV.LOGGER.warning(f"{step_name}Skipping file due to error {path}")
                            continue
                        
                del sizes_with_duplicates_dict
                partial_hash_with_duplicates_dict = {partial_hash: partial_hash_paths for partial_hash, partial_hash_paths in partial_hash_dict.items() if len(partial_hash_paths) > 1}
                del partial_hash_dict
                GV.LOGGER.debug(f"{step_name}Groups with same Partial Hash found: {len(partial_hash_with_duplicates_dict)}")
                if len(partial_hash_with_duplicates_dict)>0:
                    GV.LOGGER.debug(f"{step_name}Calculating Full Hashes for {len(partial_hash_with_duplicates_dict)} groups of partial hashes with more than one file")
                    for partial_hash, paths in tqdm(partial_hash_with_duplicates_dict.items(), smoothing=0, desc=f"{GV.TAG_INFO}Full Hashing Progress", unit=" groups"):
                        for path in paths:
                            try:
                                full_hash = calculate_file_hash_optimized(path, full_hash=True)
                                hash_dict.setdefault(full_hash, []).append(path)
                            except (PermissionError, OSError):
                                GV.LOGGER.warning(f"{step_name}Skipping file due to error {path}")
                                continue
                            
                del partial_hash_with_duplicates_dict
            else:
                GV.LOGGER.debug(f"{step_name}Hashing files with same size")
                hash_dict = {}
                for file_size, paths in tqdm(sizes_with_duplicates_dict.items(), smoothing=0, desc=f"{GV.TAG_INFO}Full Hashing Progress", unit=" groups"):
                    for path in paths:
                        try:
                            full_hash = calculate_file_hash_optimized(path, full_hash=True)
                            hash_dict.setdefault(full_hash, []).append(path)
                        except (PermissionError, OSError):
                            GV.LOGGER.warning(f"{step_name}Skipping file due to error {path}")
                            continue
                        
                del sizes_with_duplicates_dict

            duplicates = {hash: paths for hash, paths in hash_dict.items() if len(paths) > 1}
            GV.LOGGER.debug(f"{step_name}Groups with same Full Hash found: {len(duplicates)}")
            del hash_dict

            # ===========================
            # IDENTIFYING DUPLICATES
            # ===========================
            GV.LOGGER.debug(f"{step_name}Identifying duplicates by hash.")
            GV.LOGGER.debug(f"{step_name}{len(duplicates)} duplicate sets found")

            if len(duplicates)>0:
                # ===========================
                # CSV WRITING
                # ===========================
                GV.LOGGER.info(f"{step_name}Creating duplicates directories")
                duplicates_root = resolve_path('')
                timestamp_dir = os.path.join(duplicates_root, 'Duplicates_' + timestamp)
                os.makedirs(timestamp_dir, exist_ok=True)
                GV.LOGGER.info(f"{step_name}Results in {timestamp_dir}")
                duplicates_csv_path = os.path.join(timestamp_dir, f'Duplicates_{timestamp}.csv')
                header = ['Num_Duplicates', 'Principal', 'Duplicate', 'Principal_Path', 'Duplicate_Path', 'Action', 'Reason for Principal']
                if duplicates_action == 'move':
                    header.append('Destination')

                GV.LOGGER.debug(f"{step_name}Writing CSV header.")
                with open(duplicates_csv_path, 'w', encoding='utf-8-sig', newline='') as duplicates_file:
                    writer = csv.writer(duplicates_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(header)

                    # ===================================================================
                    # START OF DUPLICATES LOGIC TO DETERMINE ThE PRINCIPAL DUPLICATE FILE
                    # ===================================================================
                    GV.LOGGER.debug(f"{step_name}Processing each duplicates set to determine the principal file and move/remove the duplicates ones (if duplicates_action = move/remove).")

                    # Memory to keep consistent principal folder selection in tie scenarios
                    cache_principal_folders = {}

                    for file_hash, duplicates_path_list in duplicates.items():
                        reasson_for_principal = ""
                        duplicates_path_list_filtered = duplicates_path_list
                        for folder in duplicates_folders:
                            # Filtrar path_list para paths que comienzan con la carpeta actual
                            matched_paths = [path for path in duplicates_path_list if path.startswith(folder)]
                            if matched_paths:
                                duplicates_path_list_filtered = matched_paths
                                break  # Detener la búsqueda una vez encontrada la primera coincidencia

                        # If there is only one file in the duplicate set that belongs to the main input folder (first folder of the duplicates_folders with duplicates in this duplicates set), then this is the principal
                        if len(duplicates_path_list_filtered)==1:
                            principal = duplicates_path_list_filtered[0]
                            reasson_for_principal += " / Input folder order priority" # Reasson 1

                        # If not possible to determine principal file based only on inputs folders order we apply the ful logic based on deprioritized folders and filename length but only taking into account duplicates within the most prio input folder (duplicates_path_list_filtered)
                        else:
                            folders_datainfo_dic = []
                            for path in duplicates_path_list_filtered:
                                base_dir = os.path.dirname(path)
                                file_name = os.path.basename(path)
                                is_deprioritized, priority = folder_pattern_priority_regex_support(base_dir)
                                folders_datainfo_dic.append((base_dir, is_deprioritized, priority, file_name))

                            # Converts tuples to FolderData objects
                            FolderData = namedtuple('FolderData', ['path', 'isDeprio', 'priority', 'filename'])
                            folders_datainfo_objects = [FolderData(*data) for data in folders_datainfo_dic]

                            # Distinguish non-deprioritized and deprioritized
                            folders_non_deprioritized = [folder_data for folder_data in folders_datainfo_objects if not folder_data.isDeprio]
                            folders_deprioritized = [folder_data for folder_data in folders_datainfo_objects if folder_data.isDeprio]

                            # Create a tie scenario key (folder path + deprio state + priority)
                            tie_scenario = tuple(sorted((folder_data.path, folder_data.isDeprio, folder_data.priority) for folder_data in folders_datainfo_objects))

                            chosen_folder_data = None
                            # If there is any Non-Deprioritized foledr
                            if folders_non_deprioritized:
                                reasson_for_principal += " / Non-Deprioritized Folder(s)" # This is not an end reasson bacause always will have another string behind
                                if tie_scenario in cache_principal_folders:
                                    chosen_folder_path = cache_principal_folders[tie_scenario]
                                    for folder_data in folders_non_deprioritized:
                                        if folder_data.path == chosen_folder_path:
                                            chosen_folder_data = folder_data
                                            chosen_folder = chosen_folder_data[0]
                                            reasson_for_principal += " / Folders set in cache" # Reasson 2
                                            break
                                if chosen_folder_data is None: # No cache,
                                    chosen_folder_data = folders_non_deprioritized[0]
                                    chosen_folder = chosen_folder_data.path
                                    cache_principal_folders[tie_scenario] = chosen_folder
                                    if len(folders_non_deprioritized)==1:
                                        reasson_for_principal += " / Only one" # Reasson 3
                                    else:
                                        reasson_for_principal += " / First non-deprioritized Folder" # Reasson 4

                                # If there is more than one duplicates files within the chosen folder, then choose the shortest filename
                                chosen_folder_duplicates_files = [folder_data[3] for folder_data in folders_non_deprioritized if folder_data[0]==chosen_folder]
                                chosen_folder_duplicates_files_list = chosen_folder_duplicates_files if isinstance(chosen_folder_duplicates_files, list) else [chosen_folder_duplicates_files]
                                if len(chosen_folder_duplicates_files_list)>1:
                                    principal = min(chosen_folder_duplicates_files_list, key=lambda x: len(os.path.basename(x)))
                                    reasson_for_principal += " / Shortest File Name" # Reasson 5 & 6 (bacause could be appened to / Only one or / First non-deprioritized Folder
                                else:
                                    principal = chosen_folder_duplicates_files_list[0]

                            # If all folders are deprioritized folder
                            else:
                                if not folders_deprioritized:
                                    continue
                                reasson_for_principal += " / All Folders are deprioritized" # This is not an end reasson bacause always will have another string behind
                                max_priority = max(folder_data.priority for folder_data in folders_deprioritized)
                                folders_with_max_priority = [folder_data for folder_data in folders_deprioritized if folder_data.priority == max_priority]

                                if tie_scenario in cache_principal_folders:
                                    chosen_folder_path = cache_principal_folders[tie_scenario]
                                    for folder_data in folders_with_max_priority:
                                        if folder_data.path == chosen_folder_path:
                                            chosen_folder_data = folder_data
                                            chosen_folder = chosen_folder_data.path
                                            reasson_for_principal += " / Folders set in cache" # Reasson 7
                                            break
                                if chosen_folder_data is None: # No cache,
                                    chosen_folder_data = folders_with_max_priority[0]
                                    chosen_folder = chosen_folder_data.path
                                    cache_principal_folders[tie_scenario] = chosen_folder
                                    if len(folders_with_max_priority)==1:
                                        reasson_for_principal += f" / Only one Deprioritized Folder with Highest Priority ({max_priority})" # Reasson 8
                                    else:
                                        reasson_for_principal += f" / First Deprioritized Folder with Highest Priority ({max_priority})" # Reasson 9

                                # If there is more than one duplicates files within the chosen folder, then choose the shortest filename
                                chosen_folder_duplicates_files = [folder_data.filename for folder_data in folders_with_max_priority  if folder_data.path==chosen_folder]
                                chosen_folder_duplicates_files_list = chosen_folder_duplicates_files if isinstance(chosen_folder_duplicates_files, list) else [chosen_folder_duplicates_files]
                                if len(chosen_folder_duplicates_files_list)>1:
                                    principal = min(chosen_folder_duplicates_files_list, key=lambda x: len(os.path.basename(x)))
                                    reasson_for_principal += " / Shortest File Name" # Reasson 10 & 11 (bacause could be appened to / Only one Deprioritized Folder with Highest Priority or / First Deprioritized Folder with Highest Priority
                                else:
                                    principal = chosen_folder_duplicates_files_list[0]

                            principal = os.path.join(chosen_folder, principal)

                        if reasson_for_principal.startswith(' / '):
                            reasson_for_principal = reasson_for_principal [3:]

                        # ===========================
                        # START DUPLICATES ACTIONS
                        # ===========================
                        # Once we have determined wich is the principal file, we can continue with the duplicates action
                        duplicates_for_this_set = [path for path in duplicates_path_list if path != principal]
                        num_duplicates = len(duplicates_for_this_set)
                        display_action = 'keep' if duplicates_action == 'list' else duplicates_action
                        for duplicated in sorted(duplicates_for_this_set):
                            row = [num_duplicates, principal, duplicated, os.path.dirname(principal), os.path.dirname(duplicated), display_action, reasson_for_principal]
                            if duplicates_action == 'move':
                                relative_path = None
                                source_root = None
                                for folder in duplicates_folders:
                                    if duplicated.startswith(folder):
                                        source_root = folder
                                        relative_path = os.path.relpath(duplicated, folder)
                                        break
                                if relative_path is None:
                                    source_root = duplicates_folders[0]
                                    relative_path = os.path.relpath(duplicated, source_root)
                                top_level_folder = os.path.basename(source_root)
                                final_relative_path = os.path.join(top_level_folder, relative_path)
                                destination_path = os.path.join(timestamp_dir, final_relative_path)
                                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                                shutil.move(duplicated, destination_path)
                                row.append(destination_path)
                            elif duplicates_action == 'remove':
                                try:
                                    os.remove(duplicated)
                                except OSError:
                                    GV.LOGGER.warning(f"{step_name}Could not remove file {duplicated}")

                            writer.writerow(row)
                            duplicates_counter += 1

                if duplicates_action in ('move', 'remove'):
                    GV.LOGGER.info(f"{step_name}Removing empty directories in original folders...")
                    for folder in duplicates_folders:
                        removed_empty_folders += remove_empty_dirs(folder, log_level=log_level)

        GV.LOGGER.info(f"{step_name}Finished processing. Total duplicates (excluding principals): {duplicates_counter}")
        return duplicates_counter, removed_empty_folders


def process_duplicates_actions(csv_revised: str, log_level=None):
    import unicodedata

    def normalize_path(path: str, log_level=None) -> str:
        with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
            return unicodedata.normalize('NFC', path)

    
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Initialize counters
        removed_count = 0
        restored_count = 0
        replaced_count = 0

        # Keep track of directories where files have been removed
        removed_dirs = set()

        # Check if the CSV file exists
        if not os.path.isfile(csv_revised):
            GV.LOGGER.info(f"File {csv_revised} does not exist.")
            return removed_count, restored_count, replaced_count

        # Open the CSV file once and read lines, using UTF-8.
        # 'errors=replace' will replace any problematic characters,
        # ensuring we don't crash if there's a bad byte.
        with open(csv_revised, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)

            # Read the header and normalize it
            try:
                header = next(reader)
            except StopIteration:
                GV.LOGGER.info(f"The file {csv_revised} is empty.")
                return removed_count, restored_count, replaced_count


            normalized_header = [col.strip().lower() for col in header]

            def get_index(col_name, log_level=None):
                
                with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
                    try:
                        return normalized_header.index(col_name)
                    except ValueError:
                        return -1
                    

            principal_index = get_index("principal")
            duplicate_index = get_index("duplicate")
            action_index = get_index("action")
            destination_index = get_index("destination")

            # Check if all required columns are present
            if any(i == -1 for i in [principal_index, duplicate_index, action_index]):
                GV.LOGGER.info(f"Columns 'Principal', 'Duplicate' or 'Action' not found in {csv_revised}.")
                return removed_count, restored_count, replaced_count

            # If no Destination Column found, use Duplicate column as destination
            if destination_index == -1:
                destination_index = duplicate_index

            # Process each row
            for row in reader:
                # Skip empty rows
                if not row:
                    continue

                # Normalize file paths
                principal_file = normalize_path(row[principal_index].strip())
                duplicate_file = normalize_path(row[duplicate_index].strip())
                action = row[action_index].strip().lower()
                destination_file = normalize_path(row[destination_index].strip())

                if action in ("replace_duplicate", "replace-duplicate", "replace"):
                    if os.path.isfile(destination_file):
                        target_dir = os.path.dirname(duplicate_file)
                        if target_dir and not os.path.exists(target_dir):
                            os.makedirs(target_dir, exist_ok=True)
                        os.rename(destination_file, duplicate_file)
                        GV.LOGGER.info(f"Restored: {duplicate_file}")

                        if os.path.isfile(principal_file):
                            os.remove(principal_file)
                            GV.LOGGER.info(f"Removed: {principal_file}")
                            removed_dirs.add(os.path.dirname(principal_file))
                        replaced_count += 1
                    else:
                        GV.LOGGER.info(f"File {destination_file} does not exist. Skipping.")

                elif action in ("restore_duplicate", "restore-duplicate", "restore"):
                    if os.path.isfile(destination_file):
                        target_dir = os.path.dirname(duplicate_file)
                        if target_dir and not os.path.exists(target_dir):
                            os.makedirs(target_dir, exist_ok=True)
                        os.rename(destination_file, duplicate_file)
                        GV.LOGGER.info(f"Restored: {duplicate_file}")
                        restored_count += 1
                    else:
                        GV.LOGGER.info(f"File {destination_file} does not exist. Skipping restore.")

                elif action in ("remove_duplicate", "remove-duplicate", "remove"):
                    if os.path.isfile(destination_file):
                        os.remove(destination_file)
                        GV.LOGGER.info(f"Removed: {destination_file}")
                        removed_dirs.add(os.path.dirname(destination_file))
                        removed_count += 1
                    else:
                        GV.LOGGER.info(f"File {destination_file} does not exist. Skipping remove.")

                else:
                    GV.LOGGER.warning(f"Not recognized action: {action}. Skipped duplicate '{duplicate_file}'")

        # Attempt to remove empty directories from all paths where files have been removed.
        for d in removed_dirs:
            # Verificar si el directorio no contiene ficheros
            if not any(os.path.isfile(os.path.join(d, f)) for f in os.listdir(d)):
                GT_PREP.delete_subfolders(d, 'eaDir')
            remove_empty_dirs(d)
            GV.LOGGER.info(f"Removed empty directories in path {d}")

        return removed_count, restored_count, replaced_count