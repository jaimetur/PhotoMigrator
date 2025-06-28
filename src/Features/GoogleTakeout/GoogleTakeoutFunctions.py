import fnmatch
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

from colorama import init

from Core.CustomLogger import set_log_level, custom_print
from Core.GlobalVariables import LOGGER, MSG_TAGS, SUPPLEMENTAL_METADATA, SPECIAL_SUFFIXES, EDITTED_SUFFIXES, PHOTO_EXT, VIDEO_EXT, FOLDERNAME_NO_ALBUMS, FOLDERNAME_ALBUMS
from Utils.FileUtils import is_valid_path
from Utils.GeneralUtils import tqdm


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-CHECKS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def unpack_zips(input_folder, unzip_folder, step_name="", log_level=None):
    """ Unzips all ZIP files from a folder into another """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if not os.path.exists(input_folder):
            LOGGER.error(f"{step_name}ZIP folder '{input_folder}' does not exist.")
            return
        os.makedirs(unzip_folder, exist_ok=True)
        for zip_file in os.listdir(input_folder):
            if zip_file.endswith(".zip"):
                zip_path = os.path.join(input_folder, zip_file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        LOGGER.info(f"{step_name}Unzipping: {zip_file}")
                        zip_ref.extractall(unzip_folder)
                except zipfile.BadZipFile:
                    LOGGER.error(f"{step_name}Could not unzip file: {zip_file}")


def contains_takeout_structure(input_folder, step_name="", log_level=None):
    """
    Iteratively scans directories using a manual stack instead of recursion or os.walk.
    This can reduce overhead in large, nested folder structures.
    """
    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Looking for Google Takeout structure in input folder...")
        stack = [input_folder]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            name = entry.name
                            if name.startswith("Photos from ") and name[12:16].isdigit():
                                # LOGGER.info(f"Found Takeout structure in folder: {entry.path}")
                                LOGGER.info(f"{step_name}Found Takeout structure in folder: {current}")
                                return True
                            stack.append(entry.path)
            except PermissionError:
                LOGGER.warning(f"{step_name}Permission denied accessing: {current}")
            except Exception as e:
                LOGGER.warning(f"{step_name}Error scanning {current}: {e}")
        LOGGER.info(f"{step_name}No Takeout structure found in input folder.")
        return False


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def fix_mp4_files(input_folder, step_name="", log_level=None):
    """
    Busca archivos .MP4/.MOV/.AVI sin su JSON correspondiente. Si existe un archivo .HEIC/.JPG/.JPEG
    con el mismo nombre base y sí tiene JSON (posiblemente truncado con .supplemental-metadata),
    copia ese JSON renombrándolo con el nombre del vídeo, completando el sufijo si es necesario.

    Args:
        input_folder: Carpeta raíz donde buscar.
        step_name: Prefijo de mensajes de log.
        log_level: Nivel de log.
    """
    with set_log_level(LOGGER, log_level):
        counter_mp4_files_changed = 0
        video_exts = ['.mp4', '.mov', '.avi']
        image_exts = ['.heic', '.jpg', '.jpeg']
        supplemental = SUPPLEMENTAL_METADATA  # ya definido globalmente como 'supplemental-metadata'
        disable_tqdm = log_level < logging.WARNING

        all_video_files = []
        for _, _, files in os.walk(input_folder):
            all_video_files += [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

        if not all_video_files:
            return 0

        with tqdm(total=len(all_video_files), smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Fixing video JSONs", unit=" files", disable=disable_tqdm) as pbar:
            for root, _, files in os.walk(input_folder):
                file_set = set(files)

                video_files = [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

                for video_file in video_files:
                    pbar.update(1)
                    base_name, ext = os.path.splitext(video_file)
                    target_json = f"{video_file}.json"

                    if target_json in file_set:
                        continue

                    # Buscar posibles imágenes con el mismo nombre base
                    matched_candidate = None
                    for image_ext in image_exts:
                        candidate_base = f"{base_name}{image_ext}"

                        # Buscar json exacto o con posible truncación del supplemental
                        for f in files:
                            if not f.lower().endswith('.json'):
                                continue

                            json_base = f[:-5]  # sin el .json
                            if not json_base.lower().startswith(candidate_base.lower()):
                                continue

                            # ¿Tiene .supplemental-metadata (truncado o completo)?
                            suffix = json_base[len(candidate_base):]
                            if suffix == '':
                                matched_candidate = f
                                break
                            elif supplemental.startswith(suffix.lstrip('.')):
                                matched_candidate = f
                                break

                        if matched_candidate:
                            break  # no seguir buscando si ya tenemos uno

                    if matched_candidate:
                        src_path = os.path.join(root, matched_candidate)
                        dst_path = os.path.join(root, target_json)
                        shutil.copy(src_path, dst_path)
                        LOGGER.debug(f"{step_name}Copied: {matched_candidate} → {target_json}")
                        counter_mp4_files_changed += 1

        return counter_mp4_files_changed



def fix_truncations(input_folder, step_name="", log_level=logging.INFO, name_length_threshold=46):
    """
    Recursively traverses `input_folder` and fixes:
      1) .json files with a truncated '.supplemental-metadata' suffix.
      2) .json files whose original extension is truncated (e.g. .jp.json → .jpg.json),
         by finding the real asset file in the same directory.
      3) Non-.json files with truncated special suffixes (based on SPECIAL_SUFFIXES).
      4) Non-.json files with truncated edited suffixes in multiple languages (based on EDITTED).

    Only processes files whose base name (without extension) exceeds `name_length_threshold` characters.

    Args:
        input_folder (str): Path to the root folder to scan.
        step_name (str): Prefix for log messages (e.g. "DEBUG   : ").
        log_level (int): Logging level for this operation.
        name_length_threshold (int): Minimum length of the base filename (sans extension) to consider.

    Returns:
        dict: Counters of changes made, with keys:
          - total_files: total number of files found
          - total_files_fixed: number of files that were renamed at least once
          - json_files_fixed: number of .json files modified
          - non_json_files_fixed: number of non-.json files modified
          - supplemental_metadata_fixed: count of '.supplemental-metadata' fixes
          - extensions_fixed: count of JSON extension corrections
          - special_suffixes_fixed: count of special-suffix completions
          - edited_suffixes_fixed: count of edited-suffix completions
    """
    def repl(m):
        tail = m.group(0)[len(sub):-len(ext)]
        return suf + tail + ext

    # 1) Pre-count all files for reporting
    total_files = sum(len(files) for _, _, files in os.walk(input_folder))

    counters = {
        "total_files": total_files,
        "total_files_fixed": 0,
        "json_files_fixed": 0,
        "non_json_files_fixed": 0,
        "supplemental_metadata_fixed": 0,
        "extensions_fixed": 0,
        "special_suffixes_fixed": 0,
        "edited_suffixes_fixed": 0,
    }

    # 2) Build a combined regex for ANY truncated prefix of any special or edited suffix
    def make_variant_pattern(suffix_list):
        variants = set(suffix_list)
        for s in suffix_list:
            for i in range(2, len(s)):
                variants.add(s[:i])
        # sort longest first so regex matches the largest truncation before smaller ones
        return '|'.join(sorted(map(re.escape, variants), key=len, reverse=True))

    variants_specials_pattern = make_variant_pattern(SPECIAL_SUFFIXES)
    variants_editted_pattern = make_variant_pattern(EDITTED_SUFFIXES)
    optional_counter = r'(?:\(\d+\))?'  # allow "(n)" counters
    with set_log_level(LOGGER, log_level):
        # --------------------------
        # --- Case A: JSON files ---
        # --------------------------
        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + SUPPLEMENTAL_METADATA
        # Calculate max allowed truncation length (excluding the initial '.su')
        MAX_TRUNC = len(SUPPLEMENTAL_METADATA_WITH_DOT) - len('.su')
        # Compile pattern to capture truncated stub and optional counter like '(1)'
        pattern = re.compile(
            rf'(?P<base>.*?)(?P<stub>\.su[\w-]{{0,{MAX_TRUNC}}})(?P<counter>\(\d+\))?$',
            re.IGNORECASE
        )

        # Walk through all subdirectories to process only JSON files
        for root, _, files in os.walk(input_folder):
            files_set = set(files)  # for matching JSON sidecars
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() == '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # A.1) Fix truncated '.supplemental-metadata' suffix
                    match = pattern.match(name)
                    if match and '.su' in name.lower():  # quick sanity check before applying the pattern
                        base = match.group('base')
                        counter = match.group('counter') or ''  # preserve any '(n)' counter
                        new_name = f"{base}{SUPPLEMENTAL_METADATA_WITH_DOT}{counter}{ext}"
                        new_path = Path(root) / new_name
                        if str(old_path).lower() != str(new_path).lower():
                            os.rename(old_path, new_path)
                            LOGGER.verbose(f"{step_name}Fixed JSON Supplemental Ext: {file} → {new_name}")
                            counters["supplemental_metadata_fixed"] += 1
                            # We need to medify file and old_path for next steps
                            file = new_name
                            old_path = new_path
                            name, ext = os.path.splitext(file)  # Refresh name and ext
                            files_set = set(os.listdir(root))   # Refresh to include any renamed files
                            if not file_modified:
                                counters["json_files_fixed"] += 1
                                counters["total_files_fixed"] += 1
                                file_modified = True
                    # end A.1

                    # A.2) Fix truncated original extension by locating the real asset file
                    parts = name.split('.')
                    if len(parts) >= 2:
                        # determine base_name and raw truncated ext (with possible "(n)")
                        if len(parts) == 2:
                            base_name, raw_trunc = parts
                        else:
                            base_name = '.'.join(parts[:-2])
                            raw_trunc = parts[-2]

                        # strip counter from raw_trunc, but save it
                        m_cnt = re.match(r'^(?P<ext>.*?)(\((?P<num>\d+)\))?$', raw_trunc)
                        trunc_ext = m_cnt.group('ext')
                        counter = f"({m_cnt.group('num')})" if m_cnt.group('num') else ''

                        # look for a matching asset: stem starts with base_name, ext starts with trunc_ext
                        full_ext = None
                        for cand in files_set:
                            if cand.lower().endswith('.json'):
                                continue
                            cand_stem = Path(cand).stem
                            if not cand_stem.lower().startswith(base_name.lower()):
                                continue
                            ext_cand = Path(cand).suffix.lstrip('.')
                            if ext_cand.lower().startswith(trunc_ext.lower()):
                                full_ext = Path(cand).suffix  # e.g. ".JPG"
                                break # Once a candidate has matched, skipp looping other candidates

                        if full_ext:
                            # replace the first ".trunc_ext" in the JSON name with the full_ext, leaving any "(n)" counter at the end untouched, then append ".json"
                            new_core = name.replace(f'.{trunc_ext}', full_ext, 1)
                            if counter and new_core.endswith(counter):
                                # If the counter is already present in `name`, don't re-append it
                                new_name = f"{new_core}{ext}"
                            else:
                                # re-attach the counter just before the ".json"
                                new_name = f"{new_core}{counter}{ext}"
                            new_path = Path(root) / new_name
                            if not new_path.exists() and str(old_path).lower() != str(new_path).lower():
                                os.rename(old_path, new_path)
                                LOGGER.verbose(f"{step_name}Fixed JSON Origin File Ext : {file} → {new_name}")
                                counters["extensions_fixed"] += 1
                                if not file_modified:
                                    counters["json_files_fixed"] += 1
                                    counters["total_files_fixed"] += 1
                                    file_modified = True
                    # end A.2

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed JSON File  : {original_file} → {new_name}")

        # ------------------------------------------------------------
        # --- Case B: Non-JSON files (special suffixes or editted) ---
        # ------------------------------------------------------------
        # Walk through all subdirectories to process only Non-JSON files
        for root, _, files in os.walk(input_folder):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # B.1) Fix Special Suffixes: '-effects', '-smile', '-mix', 'collage'
                    for suf in SPECIAL_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}(?=(-|_|\.|{variants_editted_pattern}|{SUPPLEMENTAL_METADATA})?(?:\(\d+\))?{re.escape(ext)}$)",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                match = pattern.search(file)
                                if match:
                                    start = match.start()
                                    end = match.end()
                                    tail = file[end:]  # everything after the matched truncation
                                    new_name = file[:start] + suf + tail
                                    new_path = Path(root) / new_name
                                    if str(old_path).lower() != str(new_path).lower():
                                        os.rename(old_path, new_path)
                                        LOGGER.verbose(f"{step_name}Fixed ORIGIN Special Suffix: {file} → {new_name}")
                                        counters["special_suffixes_fixed"] += 1
                                        # We need to modify file and old_path for next steps and to keep changes if other suffixes are found
                                        file = new_name
                                        old_path = new_path
                                        if not file_modified:
                                            counters["non_json_files_fixed"] += 1
                                            counters["total_files_fixed"] += 1
                                            file_modified = True
                                    break # Once one truncation of the current suf is applied, stop trying shorter ones

                    # B.2) Fix Edited Suffixes (multi-language): '-edited', '-edytowane', '-bearbeitet', '-bewerkt', '-編集済み', '-modificato', '-modifié', '-ha editado', '-editat'
                    for suf in EDITTED_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}"
                                rf"(?:(?:{variants_editted_pattern}){optional_counter})*"
                                rf"{optional_counter}"
                                rf"{re.escape(ext)}$",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                new_name = pattern.sub(repl, file)
                                new_path = Path(root) / new_name
                                if str(old_path).lower() != str(new_path).lower():
                                    os.rename(old_path, new_path)
                                    LOGGER.verbose(f"{step_name}Fixed ORIGIN Edited Suffix : {file} → {new_name}")
                                    counters["edited_suffixes_fixed"] += 1
                                    # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                    file = new_name
                                    old_path = new_path
                                    if not file_modified:
                                        counters["non_json_files_fixed"] += 1
                                        counters["total_files_fixed"] += 1
                                        file_modified = True
                                break # Once one truncation of the current suf is applied, stop trying shorter ones

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed MEDIA File : {original_file} → {new_name}")
    return counters


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def run_command(command, capture_output=False, capture_errors=True, print_messages=True, step_name=""):
    """
    Ejecuta un comando. Muestra en consola actualizaciones de progreso sin loguearlas.
    Loguea solo líneas distintas a las de progreso. Corrige pegado de líneas en consola.
    """
    from Core.CustomLogger import suppress_console_output_temporarily
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_stream(stream, is_error=False):
        init(autoreset=True)

        progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)$')
        last_was_progress = False
        printed_final = set()

        while True:
            raw = stream.readline()
            if not raw:
                break

            # Limpiar ANSI y espacios finales
            ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', raw).rstrip()

            # Prefijo para agrupar barras
            common_part = line.split(' : ')[0] if ' : ' in line else line

            # 1) ¿Es barra de progreso?
            m = progress_re.search(line)
            if m:
                n, total = int(m.group(1)), int(m.group(2))

                # 1.a) Barra vacía (0/x)
                if n == 0:
                    if not print_messages:
                        # Log inicial
                        log_msg = f"{step_name}{line}"
                        if is_error:
                            LOGGER.error(log_msg)
                        else:
                            LOGGER.info(log_msg)
                    # nunca imprimo 0/x en pantalla
                    last_was_progress = True
                    continue

                # 1.b) Progreso intermedio (1 <= n < total)
                if n < total:
                    if print_messages:
                        print(f"\r{MSG_TAGS['INFO']}{step_name}{line}", end='', flush=True)
                        # custom_print(f"\r{step_name}{line}", end='', flush=True, log_level=logging.INFO)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    # impresión en pantalla
                    if print_messages:
                        print(f"\r{MSG_TAGS['INFO']}{step_name}{line}", end='', flush=True)
                        # custom_print(f"\r{step_name}{line}", end='', flush=True, log_level=logging.INFO)
                        print()
                    # log final
                    log_msg = f"{step_name}{line}"
                    if is_error:
                        LOGGER.error(log_msg)
                    else:
                        LOGGER.info(log_msg)

                    printed_final.add(common_part)

                last_was_progress = False
                continue

            # 2) Mensaje normal: si venía de progreso vivo, forzamos salto
            if last_was_progress and print_messages:
                print()
            last_was_progress = False

            # 3) Impresión normal
            warning_keywords = [
                "WARNING",
                "ExifTool command failed with exit code",
                "Error output",
            ]
            if print_messages:
                if is_error:
                    # print(f"{MSG_TAGS_COLORED['ERROR']}{step_name}{line}{Style.RESET_ALL}")
                    custom_print(f"{step_name}{line}", log_level=logging.ERROR)
                else:
                    if "VERBOSE" in line:
                        # print(f"{MSG_TAGS_COLORED['VERBOSE']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.VERBOSE)         # Could raise error if we have not previously set logging.VERBOSE properly
                        # custom_print(f"{step_name}{line}", log_level=VERBOSE_LEVEL_NUM)
                    elif "DEBUG" in line:
                        # print(f"{MSG_TAGS_COLORED['DEBUG']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.DEBUG)
                    elif "WARNING" in line:
                        # print(f"{MSG_TAGS_COLORED['WARNING']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.WARNING)
                    elif any(kw in line for kw in warning_keywords):
                        # print(f"{MSG_TAGS_COLORED['WARNING']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.WARNING)
                    elif "ERROR" in line:
                        # print(f"{MSG_TAGS_COLORED['ERROR']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.ERROR)
                    else:
                        # print(f"{MSG_TAGS_COLORED['INFO']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.INFO)

            # 4) Logging normal
            if is_error:
                LOGGER.error(f"{step_name}{line}")
            else:
                if "ERROR" in line:
                    LOGGER.error(f"{step_name}{line}")
                elif "WARNING" in line:
                    LOGGER.warning(f"{step_name}{line}")
                elif "DEBUG" in line:
                    LOGGER.debug(f"{step_name}{line}")
                elif "VERBOSE" in line:
                    LOGGER.verbose(f"{step_name}{line}")
                elif any(kw in line for kw in warning_keywords):
                    LOGGER.warning(f"{step_name}{line}")
                else:
                    LOGGER.info(f"{step_name}{line}")

        # 5) Al cerrar stream, si quedó un progreso vivo, cerramos línea
        if last_was_progress and print_messages:
            print()

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    with suppress_console_output_temporarily(LOGGER):
        if not capture_output and not capture_errors:
            return subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace").returncode
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True, encoding = "utf-8", errors = "replace"
            )
            if capture_output:
                handle_stream(process.stdout, is_error=False)
            if capture_errors:
                handle_stream(process.stderr, is_error=True)

            process.wait()  # Esperar a que el proceso termine
            return process.returncode


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT POST-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sync_mp4_timestamps_with_images(input_folder, step_name="", log_level=None):
    """
    Look for .MP4 files with the same base name as any Live Picture file (.HEIC, .JPG, .JPEG)
    in the same folder. If found, set the date and time of the .MP4 file (or the symlink itself)
    to match the original Live Picture.
    """
    # Set logging level for this operation
    with set_log_level(LOGGER, log_level):
        # Count total files for progress bar
        total_files = sum(len(files) for _, _, files in os.walk(input_folder))
        with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'", unit=" files"
                  ) as pbar:
            # Walk through all directories and files
            for path, _, files in os.walk(input_folder):
                # Build a mapping from base filename to its extensions
                file_dict = {}
                for filename in files:
                    pbar.update(1)
                    name, ext = os.path.splitext(filename)
                    base_name = name.lower()
                    ext = ext.lower()
                    file_dict.setdefault(base_name, {})[ext] = filename
                # For each group of files sharing the same base name
                for base_name, ext_file_map in file_dict.items():
                    if '.mp4' not in ext_file_map:
                        continue
                    mp4_filename = ext_file_map['.mp4']
                    mp4_file_path = os.path.join(path, mp4_filename)
                    # Detect if the .mp4 is a symlink
                    is_mp4_link = os.path.islink(mp4_file_path)
                    # Look for a matching Live Picture image
                    image_exts = ['.heic', '.jpg', '.jpeg']
                    for image_ext in image_exts:
                        if image_ext not in ext_file_map:
                            continue
                        image_filename = ext_file_map[image_ext]
                        image_file_path = os.path.join(path, image_filename)
                        try:
                            # Get the image's atime and mtime
                            image_stats = os.stat(image_file_path)
                            atime, mtime = image_stats.st_atime, image_stats.st_mtime
                            if is_mp4_link:
                                # Apply timestamps to the symlink itself
                                os.utime(mp4_file_path, (atime, mtime), follow_symlinks=False)
                                LOGGER.debug(f"{step_name}Timestamps applied to symlink: {os.path.relpath(mp4_file_path, input_folder)}")
                            else:
                                # Apply timestamps to the regular .mp4 file
                                os.utime(mp4_file_path, (atime, mtime))
                                LOGGER.debug(f"{step_name}Timestamps applied to file: {os.path.relpath(mp4_file_path, input_folder)}")
                        except FileNotFoundError:
                            # Warn if either the .mp4 or the image file is missing
                            LOGGER.warning(f"{step_name}File not found. MP4: {mp4_file_path} | Image: {image_file_path}")
                        except Exception as e:
                            # Log any other errors encountered
                            LOGGER.error(f"{step_name}Error syncing {mp4_file_path}: {e}")
                        # Only sync with the first matching image
                        break


def force_remove_directory(folder, step_name='', log_level=None):
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(folder):
            shutil.rmtree(folder, onerror=onerror)
            LOGGER.info(f"{step_name}The folder '{folder}' and all its content have been deleted.")
            return True
        else:
            LOGGER.info(f"{step_name}Cannot delete the folder '{folder}'.")
            return False


def copy_move_folder(src, dst, ignore_patterns=None, move=False, step_name="", log_level=None):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param step_name:
    :param log_level:
    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Ignore function
        action = 'Moving' if move else 'Copying'
        try:
            if not is_valid_path(src):
                LOGGER.error(f"{step_name}The path '{src}' is not valid for the execution platform. Cannot copy/move folders from it.")
                return False
            if not is_valid_path(dst):
                LOGGER.error(f"{step_name}The path '{dst}' is not valid for the execution platform. Cannot copy/move folders to it.")
                return False

            def ignore_function(files, ignore_patterns):
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
                raise FileNotFoundError(f"{step_name}Source folder does not exist: '{src}'")
            # Create the destination folder if it doesn't exist
            os.makedirs(dst, exist_ok=True)

            if move:
                # Contar el total de carpetas
                total_files = sum([len(files) for _, _, files in os.walk(src)])
                # Mostrar la barra de progreso basada en carpetas
                with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                    for path, dirs, files in os.walk(src, topdown=True):
                        pbar.update(1)
                        # Compute relative path
                        rel_path = os.path.relpath(path, src)
                        # Destination path
                        dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        # Apply ignore function to files and dirs
                        ignore = ignore_function(files + dirs, ignore_patterns=ignore_patterns)
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
                    LOGGER.info(f"{step_name}Folder moved successfully from {src} to {dst}")
            else:
                # Copy the folder contents
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
                LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst}")
                return True
        except Exception as e:
            LOGGER.error(f"{step_name}Error {action} folder: {e}")
            return False


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[], step_name="", log_level=None):
    """
    Organizes files into subfolders based on their EXIF or modification date.

    Args:
        input_folder (str, Path): The base directory containing the files.
        type: 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (str, Path or list): A list of subfolder names to exclude from processing.

    Raises:
        ValueError: If the value of `type` is invalid.
        :param step_name:
        :param log_level:
    """
    import os
    import shutil
    from datetime import datetime
    import piexif
    def get_exif_date(image_path):
        try:
            exif_dict = piexif.load(image_path)
            for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                tag_id = piexif.ExifIFD.__dict__.get(tag)
                value = exif_dict["Exif"].get(tag_id)
                if value:
                    return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    with set_log_level(LOGGER, log_level):
        if type not in ['year', 'year/month', 'year-month']:
            raise ValueError(f"{step_name}The 'type' parameter must be 'year', 'year/month' or 'year-month'.")
        total_files = 0
        for _, dirs, files in os.walk(input_folder):
            dirs[:] = [d for d in dirs if d not in exclude_subfolders]
            total_files += len(files)
        with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_subfolders]
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                    mod_time = None
                    ext = os.path.splitext(file)[1].lower()
                    # Intentar obtener fecha EXIF si es imagen
                    if ext in PHOTO_EXT:
                        try:
                            mod_time = get_exif_date(file_path)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Error reading EXIF from {file_path}: {e}")
                    # Si no hay EXIF o no es imagen, usar fecha de sistema
                    if not mod_time:
                        try:
                            mtime = os.path.getmtime(file_path)
                            mod_time = datetime.fromtimestamp(mtime if mtime > 0 else 0)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Error reading mtime for {file_path}: {e}")
                            mod_time = datetime(1970, 1, 1)
                    LOGGER.verbose(f"{step_name}Using date {mod_time} for file {file_path}")
                    # Determinar carpeta destino
                    if type == 'year':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'))
                    elif type == 'year/month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'), mod_time.strftime('%m'))
                    elif type == 'year-month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y-%m'))
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(file_path, os.path.join(target_dir, file))
        LOGGER.info(f"{step_name}Organization completed. Folder structure per '{type}' created in '{input_folder}'.")


def move_albums(input_folder, albums_subfolder=f"{FOLDERNAME_ALBUMS}", exclude_subfolder=None, step_name="", log_level=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str, Path): Path to the input folder containing the albums.
        albums_subfolder (str, Path): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
        :param step_name:
        :param log_level:
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
        subfolders = [subfolder for subfolder in subfolders if not subfolder == '@eaDir' and not subfolder == FOLDERNAME_NO_ALBUMS]
        for subfolder in tqdm(subfolders, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Moving Albums in '{input_folder}' to Subolder '{albums_subfolder}'", unit=" albums"):
            folder_path = os.path.join(input_folder, subfolder)
            if os.path.isdir(folder_path) and subfolder != albums_subfolder and os.path.abspath(folder_path) not in exclude_subfolder_paths:
                LOGGER.debug(f"{step_name}Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'")
                os.makedirs(albums_path, exist_ok=True)
                safe_move(folder_path, albums_path)
        # Finally Move Albums to Albums root folder (removing 'Takeout' and 'Google Fotos' / 'Google Photos' folders if exists
        move_albums_to_root(albums_path, step_name=step_name, log_level=logging.INFO)


def move_albums_to_root(albums_root, step_name="", log_level=None):
    """
    Moves all albums from nested subdirectories ('Takeout/Google Fotos' or 'Takeout/Google Photos')
    directly into the 'Albums' folder, removing unnecessary intermediate folders.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        possible_google_folders = ["Google Fotos", "Google Photos"]
        takeout_path = os.path.join(albums_root, "Takeout")
        # Check if 'Takeout' exists
        if not os.path.exists(takeout_path):
            LOGGER.debug(f"{step_name}'Takeout' folder not found at {takeout_path}. Exiting.")
            return
        # Find the actual Google Photos folder name
        google_photos_path = None
        for folder in possible_google_folders:
            path = os.path.join(takeout_path, folder)
            if os.path.exists(path):
                google_photos_path = path
                break
        if not google_photos_path:
            LOGGER.debug(f"{step_name}No valid 'Google Fotos' or 'Google Photos' folder found inside 'Takeout'. Exiting.")
            return
        LOGGER.debug(f"{step_name}Found Google Photos folder: {google_photos_path}")
        LOGGER.info(f"{step_name}Moving Albums to Albums root folder...")
        # Move albums to the root 'Albums' directory
        for album in os.listdir(google_photos_path):
            album_path = os.path.join(google_photos_path, album)
            target_path = os.path.join(albums_root, album)
            if os.path.isdir(album_path):  # Ensure it's a directory (album)
                new_target_path = target_path
                count = 1
                # Handle naming conflicts by adding a suffix
                while os.path.exists(new_target_path):
                    new_target_path = f"{target_path}_{count}"
                    count += 1
                # Move the album
                shutil.move(album_path, new_target_path)
                LOGGER.debug(f"{step_name}Moved: {album_path} → {new_target_path}")
        # Attempt to remove empty folders
        try:
            shutil.rmtree(takeout_path)
            LOGGER.debug(f"{step_name}'Takeout' folder successfully removed.")
        except Exception as e:
            LOGGER.error(f"{step_name}Failed to remove 'Takeout': {e}")


def count_valid_albums(folder_path, excluded_folders=None, step_name="", log_level=None):
    """
    Walk every sub-folder in *folder_path* and count how many of them contain at
    least one photo or video (direct file, POSIX symlink, or Windows .lnk).
    """
    if excluded_folders is None:
        excluded_folders = ()

    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    MEDIA_EXT = set(PHOTO_EXT) | set(VIDEO_EXT)         # union once → O(1) lookup

    valid_albums = 0
    visited_dirs = set()

    with set_log_level(LOGGER, log_level):
        for root, dirs, files in os.walk(folder_path, followlinks=True):
            real_root = os.path.realpath(root)
            if real_root in visited_dirs:               # avoid loops with symlinked dirs
                continue
            visited_dirs.add(real_root)

            folder_name = os.path.basename(root)

            # ── skip folders by name ────────────────────────────────────────────
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()
                continue

            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]

            # ── inspect files inside this folder ───────────────────────────────
            for fname in files:
                fpath = Path(root) / fname
                link_ext = fpath.suffix.lower()                 # ext of the file itself
                target_ext = ''                                 # will be filled below

                try:
                    if fpath.is_symlink():                      # POSIX / NTFS symlink
                        target_ext = fpath.resolve(strict=False).suffix.lower()

                    elif os.name == 'nt' and link_ext == '.lnk':
                        # Windows shortcut (.lnk): try to infer inner extension from its stem
                        target_ext = Path(fpath.stem).suffix.lower()
                        # NOTE: we don't parse the .lnk binary; good enough if names keep the ext.

                    else:
                        target_ext = link_ext                   # normal file (no link)

                    if link_ext in MEDIA_EXT or target_ext in MEDIA_EXT:
                        valid_albums += 1
                        LOGGER.debug(f"{step_name}✅ Valid album at: {root}")
                        break                                   # next folder

                except Exception as exc:
                    LOGGER.warning(f"{step_name}⚠️ Cannot inspect {fpath}: {exc}")

    return valid_albums


import os
import platform
import shutil
import subprocess

def clone_backup_if_needed(input_folder, cloned_folder, step_name="", log_level=None):
    """
    Clones the given input folder into cloned_folder using the fastest available method.
    It prioritizes robocopy (Windows), rsync (Linux/macOS), and falls back to shutil.copytree.
    Returns the cloned_folder if successful, or input_folder if the cloning fails.
    Accepts both str and Path objects.
    """
    from LoggerConfig import logger as LOGGER
    from contextlib import contextmanager

    @contextmanager
    def set_log_level(logger, level):
        original_level = logger.level
        if level is not None:
            logger.setLevel(level)
        try:
            yield
        finally:
            logger.setLevel(original_level)

    # Ensure string paths for compatibility with subprocess
    input_folder = str(input_folder)
    cloned_folder = str(cloned_folder)

    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"{step_name}Creating temporary working folder at: {cloned_folder}")

        try:
            system = platform.system()

            if system == "Windows":
                # Use robocopy with mirror mode
                result = subprocess.run([
                    "robocopy", input_folder, cloned_folder, "/MIR", "/R:0", "/W:0", "/NFL", "/NDL", "/NJH", "/NJS"
                ], capture_output=True, text=True)
                if result.returncode <= 7:  # Exit codes 0–7 mean success
                    LOGGER.info(f"{step_name}Temporary cloned successfully {input_folder} -> {cloned_folder}")
                    return cloned_folder
                else:
                    raise Exception(f"robocopy failed with code {result.returncode}: {result.stderr}")

            elif system in ["Linux", "Darwin"]:
                # Use rsync for fast copying
                subprocess.run([
                    "rsync", "-a", "--info=progress2", input_folder + "/", cloned_folder
                ], check=True)
                LOGGER.info(f"{step_name}Temporary cloned successfully {input_folder} -> {cloned_folder}")
                return cloned_folder

            else:
                LOGGER.warning(f"{step_name}Unknown system '{system}', using fallback method.")

        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ Fast cloning failed: {e}. Falling back to shutil.copytree...")

        # Fallback to shutil.copytree
        try:
            shutil.copytree(input_folder, cloned_folder)
            LOGGER.info(f"{step_name}Temporary cloned successfully {input_folder} -> {cloned_folder}")
            return cloned_folder
        except Exception as e:
            LOGGER.warning(f"{step_name}❌ Failed to clone {input_folder}: {e}")
            return input_folder