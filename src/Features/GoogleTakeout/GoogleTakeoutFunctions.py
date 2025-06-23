import fnmatch
import json
import logging
import math
import multiprocessing
import os
import platform
import re
import shutil
import stat
import subprocess
import time
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from colorama import init, Style

from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import LOGGER, TAG_INFO, SUPPLEMENTAL_METADATA, SPECIAL_SUFFIXES, EDITTED_SUFFIXES, COLORTAG_ERROR, COLORTAG_WARNING, COLORTAG_DEBUG, COLORTAG_VERBOSE, COLORTAG_INFO, PHOTO_EXT, VIDEO_EXT, TIMESTAMP, METADATA_EXT, SIDECAR_EXT
from Utils.FileUtils import is_valid_path
from Utils.GeneralUtils import tqdm, timed_subprocess


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
    Look for all .MP4 files that have the same base name as any Live Picture in the same folder.
    If found, copy the associated .json file (including those with a truncated '.supplemental-metadata')
    and rename it to match the .MP4 file, completing the truncated suffix if necessary.

    Args:
        input_folder (str): The root folder to scan.
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
        :param step_name:
    """
    with set_log_level(LOGGER, log_level):  # Set desired log level
        counter_mp4_files_changed = 0
        # Count total .mp4 files for progress bar
        all_mp4_files = []
        for _, _, files in os.walk(input_folder, topdown=True):
            for file in files:
                if file.lower().endswith('.mp4'):
                    all_mp4_files.append(file)
        total_files = len(all_mp4_files)
        if total_files == 0:
            return 0
        # Mostrar la barra de progreso basada en carpetas
        disable_tqdm = log_level < logging.WARNING
        with tqdm(total=total_files, smoothing=0.1, desc=f"{TAG_INFO}{step_name}Fixing .MP4 files in '{input_folder}'", unit=" files", disable=disable_tqdm) as pbar:
            for path, _, files in os.walk(input_folder):
                # Filter files with .mp4 extension (case-insensitive)
                mp4_files = [f for f in files if f.lower().endswith('.mp4')]
                for mp4_file in mp4_files:
                    pbar.update(1)
                    # Get the base name of the MP4 file (without extension)
                    mp4_base = os.path.splitext(mp4_file)[0]
                    # Search for JSON files with the same base name but ignoring case for the extension
                    for candidate in files:
                        if not candidate.lower().endswith('.json'):
                            continue
                        candidate_path = os.path.join(path, candidate)
                        candidate_no_ext = candidate[:-5]  # Remove .json
                        # Build a regex pattern to match: (i.e: IMG_1094.HEIC(.supplemental-metadata)?.json)

                        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
                        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + SUPPLEMENTAL_METADATA
                        # common part
                        base_pattern = rf'({re.escape(mp4_base)}\.(?:heic|jpg|jpeg))'
                        # parte con llaves literales y variable
                        supp_pattern = r'(?:\{' + SUPPLEMENTAL_METADATA_WITH_DOT + r'\}.*)?$'
                        full_pattern = base_pattern + supp_pattern
                        match = re.match(full_pattern, candidate_no_ext, re.IGNORECASE)

                        if match:
                            base_part = match.group(1)
                            suffix = match.group(3) or ''
                            # Check if it's a truncated version of '.supplemental-metadata'
                            if suffix and not suffix.lower().startswith(SUPPLEMENTAL_METADATA):
                                # Try to match a valid truncation
                                for i in range(2, len(SUPPLEMENTAL_METADATA) + 1):
                                    if suffix.lower() == SUPPLEMENTAL_METADATA[:i]:
                                        suffix = '.'+SUPPLEMENTAL_METADATA
                                        break
                            # Generate the new name for the duplicated file
                            new_json_name = f"{mp4_file}{suffix}.json"
                            new_json_path = os.path.join(path, new_json_name)
                            # Check if the target file already exists to avoid overwriting
                            if not os.path.exists(new_json_path):
                                # Copy the original JSON file to the new file
                                if candidate_path.lower != new_json_path.lower():
                                    shutil.copy(candidate_path, new_json_path)
                                    LOGGER.info(f"{step_name}Copied: {candidate} -> {new_json_name}")
                                    counter_mp4_files_changed += 1
                                    continue # if already found a matched candidate, then continue with the next file
                            else:
                                LOGGER.info(f"{step_name}Skipped: {new_json_name} already exists")
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
                                        # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                        file = new_name
                                        old_path = new_path
                                        if not file_modified:
                                            counters["non_json_files_fixed"] += 1
                                            counters["total_files_fixed"] += 1
                                            file_modified = True
                                    break # Once one truncation of the current suf is applied, stop trying shorter ones

                    # B.2) Fix Editted Suffixes (multi-language): '-editted', '-edytowane', '-bearbeitet', '-bewerkt', '-編集済み', '-modificato', '-modifié', '-ha editado', '-editat'
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
                        print(f"\r{TAG_INFO}{step_name}{line}", end='', flush=True)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    # impresión en pantalla
                    if print_messages:
                        print(f"\r{TAG_INFO}{step_name}{line}", end='', flush=True)
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
            if print_messages:
                if is_error:
                    print(f"{COLORTAG_ERROR}{step_name}{line}{Style.RESET_ALL}")
                else:
                    if "ERROR" in line:
                        print(f"{COLORTAG_ERROR}{step_name}{line}{Style.RESET_ALL}")
                    elif "WARNING" in line:
                        print(f"{COLORTAG_WARNING}{step_name}{line}{Style.RESET_ALL}")
                    elif "DEBUG" in line:
                        print(f"{COLORTAG_DEBUG}{step_name}{line}{Style.RESET_ALL}")
                    elif "VERBOSE" in line:
                        print(f"{COLORTAG_VERBOSE}{step_name}{line}{Style.RESET_ALL}")
                    else:
                        print(f"{COLORTAG_INFO}{step_name}{line}{Style.RESET_ALL}")

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
        with tqdm(
                total=total_files,
                smoothing=0.1,
                desc=f"{TAG_INFO}{step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'",
                unit=" files"
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


def force_remove_directory(folder, log_level=None):
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(folder):
            shutil.rmtree(folder, onerror=onerror)
            LOGGER.info(f"The folder '{folder}' and all its contant have been deleted.")
        else:
            LOGGER.warning(f"Cannot delete the folder '{folder}'.")


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
                LOGGER.error(f"{step_name}The path '{src}' is not valid for the execution plattform. Cannot copy/move folders from it.")
                return False
            if not is_valid_path(dst):
                LOGGER.error(f"{step_name}The path '{dst}' is not valid for the execution plattform. Cannot copy/move folders to it.")
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
                with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"{TAG_INFO}{step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
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
        with tqdm(total=total_files, smoothing=0.1, desc=f"{TAG_INFO}{step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files") as pbar:
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


def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder=None, step_name="", log_level=None):
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
        subfolders = [subfolder for subfolder in subfolders if not subfolder == '@eaDir' and not subfolder == 'No-Albums']
        for subfolder in tqdm(subfolders, smoothing=0.1, desc=f"{TAG_INFO}{step_name}Moving Albums in '{input_folder}' to Subolder '{albums_subfolder}'", unit=" albums"):
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


def count_valid_albums(folder_path, excluded_folders=[], step_name="", log_level=None):
    """
    Counts the number of subfolders within folder_path and its sublevels
    that contain at least one valid image or video file.

    A folder is considered valid if it contains at least one file with an extension
    defined in PHOTO_EXT or VIDEO_EXT.

    The following folders (and all their subfolders) are excluded from the count:
    - Any folder named 'Photos from YYYY' where YYYY starts with 1 or 2.
    - Folders named exactly as excluded_folder list.
    """
    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    with set_log_level(LOGGER, log_level):  # Change log level temporarily
        valid_albums = 0
        for root, dirs, files in os.walk(folder_path):
            folder_name = os.path.basename(root)
            # Skip current folder if it matches any exclusion rule
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()  # Prevent descending into subdirectories
                continue
            # Also remove excluded subfolders from being walked into
            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]
            # Check for at least one valid image or video file
            if any(os.path.splitext(file)[1].lower() in PHOTO_EXT or os.path.splitext(file)[1].lower() in VIDEO_EXT for file in files):
                valid_albums += 1
        return valid_albums


def get_oldest_date(file_path, extensions, tag_ids, skip_exif=True, skip_json=True, log_level=None):
    """
    Return the earliest valid timestamp found by:
      1) Birthtime/mtime for video files (early exit if ext in VIDEO_EXT)
      2) EXIF tags (if skip_exif=False and ext in extensions)
      3) JSON sidecar (<file>.json) (if skip_json=False)
      4) File birthtime and modification time via one os.stat() fallback
    Caches results per (file_path, skip_exif, skip_json) on the function.
    """
    # initialize per‐call cache
    if not hasattr(get_oldest_date, "_cache"):
        get_oldest_date._cache = {}
    cache = get_oldest_date._cache
    key = (file_path, bool(skip_exif), bool(skip_json))
    if key in cache:
        return cache[key]

    with set_log_level(LOGGER, log_level):
        ext = Path(file_path).suffix.lower()

        # 1) Videos → no EXIF/JSON, just return birthtime or mtime
        if ext in VIDEO_EXT:
            try:
                st = os.stat(file_path, follow_symlinks=False)
                bt = getattr(st, "st_birthtime", None)
                result = datetime.fromtimestamp(bt) if bt else datetime.fromtimestamp(st.st_mtime)
            except Exception:
                result = None
            cache[key] = result
            return result

        dates = []

        # 2) EXIF extraction for supported extensions
        if not skip_exif and ext in extensions:
            try:
                exif = Image.open(file_path).getexif()
                if len(exif) > 0:
                    for tag_id in tag_ids:
                        raw = exif.get(tag_id)
                        if isinstance(raw, str) and len(raw) >= 19:
                            # fast parse 'YYYY:MM:DD HH:MM:SS'
                            y, mo, d = int(raw[0:4]), int(raw[5:7]), int(raw[8:10])
                            hh, mm, ss = int(raw[11:13]), int(raw[14:16]), int(raw[17:19])
                            dates.append(datetime(y, mo, d, hh, mm, ss))
                            break
            except Exception:
                pass

        # 3) JSON sidecar parsing
        if not skip_json:
            js = Path(file_path).with_suffix(ext + ".json")
            if js.exists():
                try:
                    data = json.loads(js.read_text(encoding="utf-8"))
                    for name in ("photoTakenTime", "creationTime", "creationTimestamp"):
                        ts = data.get(name)
                        if isinstance(ts, dict):
                            ts = ts.get("timestamp")
                        if ts:
                            dates.append(datetime.fromtimestamp(int(ts)))
                            break
                except Exception:
                    pass

        # 4) Fallback to birthtime + mtime
        try:
            st = os.stat(file_path, follow_symlinks=False)
            bt = getattr(st, "st_birthtime", None)
            if bt is not None:
                dates.append(datetime.fromtimestamp(bt))
            dates.append(datetime.fromtimestamp(st.st_mtime))
        except Exception:
            pass

        result = min(dates) if dates else None
        cache[key] = result
        return result


def get_embedded_datetime(file_path, step_name=''):
    """
    Devuelve la fecha embebida más antigua encontrada como datetime.datetime,
    usando exiftool desde ./gpth_tool/exif_tool/. Si no hay fechas embebidas válidas, retorna None.

    Usa PHOTO_EXT, VIDEO_EXT y LOGGER.

    Args:
        file_path (str, Literal or Path): Ruta al archivo.

    Returns:
        datetime.datetime or None
        :param step_name:
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext not in PHOTO_EXT and ext not in VIDEO_EXT:
        return None

    is_windows = platform.system().lower() == 'windows'
    exiftool_path = Path("gpth_tool/exif_tool/exiftool.exe" if is_windows else "gpth_tool/exif_tool/exiftool").resolve()

    if not exiftool_path.exists():
        LOGGER.debug(f"{step_name}[get_embedded_datetime] exiftool not found at: {exiftool_path}")
        return None

    try:
        result = subprocess.run(
            [str(exiftool_path), '-j', '-time:all', '-s', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding='utf-8',
            check=True
        )
        metadata_list = json.loads(result.stdout)
        if not metadata_list or not isinstance(metadata_list, list) or not metadata_list[0]:
            LOGGER.debug(f"{step_name}[get_embedded_datetime] No metadata returned for: {file_path.name}")
            return None

        metadata = metadata_list[0]

        candidate_tags = [
            'DateTimeOriginal',
            'CreateDate',
            'MediaCreateDate',
            'TrackCreateDate',
            'EncodedDate',
            'MetadataDate',
        ]

        available_tags = [tag for tag in candidate_tags if tag in metadata]
        if not available_tags:
            LOGGER.debug(f"{step_name}[get_embedded_datetime] No embedded date tags found in metadata for: {file_path.name}")
            return None

        date_formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d",
            "%Y-%m-%d",
        ]

        found_dates = []

        for tag in available_tags:
            raw_value = metadata[tag].strip()
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(raw_value, fmt)
                    found_dates.append((tag, parsed_date))
                    break
                except ValueError:
                    continue

        if not found_dates:
            LOGGER.debug(f"{step_name}[get_embedded_datetime] None of the embedded date fields could be parsed for: {file_path.name}")
            return None

        oldest = min(found_dates, key=lambda x: x[1])
        LOGGER.debug(f"{step_name}[get_embedded_datetime] Selected tag '{oldest[0]}' with date {oldest[1]} for: {file_path.name}")
        return oldest[1]

    except Exception as e:
        LOGGER.error(f"{step_name}[get_embedded_datetime] Error processing '{file_path}': {e}")
        return None


def get_embedded_datetimes_bulk(folder, step_name=''):
    """
    Devuelve un diccionario con la fecha embebida más antigua de cada archivo multimedia en la carpeta y subcarpetas.

    Args:
        folder (str or Path): Carpeta raíz

    Returns:
        dict[Path, datetime.datetime]: mapping de archivo → fecha más antigua encontrada
        :param step_name:
    """
    folder = Path(folder).resolve()
    step_name = f"{step_name}[get_embedded_datetimes_bulk] : "

    is_windows = platform.system().lower() == 'windows'
    exiftool_path = Path("gpth_tool/exif_tool/exiftool.exe" if is_windows else "gpth_tool/exif_tool/exiftool").resolve()
    if not exiftool_path.exists():
        LOGGER.error(f"{step_name}❌ exiftool not found at: {exiftool_path}")
        return {}

    try:
        # result = subprocess.run(
        #     [str(exiftool_path), "-r", "-j", "-time:all", "-s", str(folder)],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.DEVNULL,
        #     encoding='utf-8',
        #     check=False  # <== importante
        # )
        return_code, out, err = timed_subprocess(
            [str(exiftool_path), "-r", "-j", "-time:all", "-s", str(folder)],
            step_name=step_name
        )
        if return_code != 0:
            LOGGER.warning(f"{step_name}❌ exiftool return code: %d", return_code)

        # Decodifica el stdout:
        output = out.decode("utf-8")

        metadata_list = json.loads(output)
    except Exception as e:
        LOGGER.error(f"{step_name}❌ Failed to run exiftool: {e}")
        return {}

    date_formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d",
        "%Y-%m-%d",
    ]

    candidate_tags = [
        'DateTimeOriginal',
        'CreateDate',
        'MediaCreateDate',
        'TrackCreateDate',
        'EncodedDate',
        'MetadataDate',
    ]

    result_dict = {}

    for entry in metadata_list:
        source_file = entry.get("SourceFile")
        if not source_file:
            continue
        file_path = Path(source_file)
        ext = file_path.suffix.lower()
        if ext not in PHOTO_EXT and ext not in VIDEO_EXT:
            continue

        found_dates = []
        for tag in candidate_tags:
            if tag in entry:
                raw_value = str(entry[tag]).strip()
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(raw_value, fmt)
                        found_dates.append(dt)
                        break
                    except ValueError:
                        continue

        if found_dates:
            oldest = min(found_dates)
            result_dict[file_path] = oldest
            LOGGER.debug(f"{step_name}✅ {oldest} →  {file_path.name}")

    return result_dict


def date_extractor(folder_path, max_files=None, exclude_ext=None, include_ext=None, output_file="metadata_output.json", progress_interval=300, step_name=''):
    """
    Extracts EXIF date metadata using exiftool with periodic progress reporting.

    Args:
        folder_path: Directory to scan.
        max_files: Maximum number of files to process. If None, processes all.
        exclude_ext: List of extensions to exclude (without dot).
        include_ext: List of extensions to include (without dot).
        output_file: Name of the output JSON file.
        progress_interval: Interval in seconds to report progress.
        step_name: Optional prefix for logging messages.
    """
    folder = Path(folder_path)
    exclude_ext = exclude_ext or ["json"]
    output_path = Path(output_file)

    # Step 1: Collect all files matching the criteria
    LOGGER.debug(f"{step_name}📅[date_extractor] Scanning directory: {folder}")
    all_files = list(folder.rglob("*"))
    selected_files = []

    for file in all_files:
        if not file.is_file():
            continue
        ext = file.suffix.lower()
        if ext in exclude_ext:
            continue
        if include_ext and ext not in include_ext:
            continue
        selected_files.append(str(file))

    if max_files:
        selected_files = selected_files[:max_files]

    LOGGER.debug(f"{step_name}📅[date_extractor] {len(selected_files)} files selected for processing.")

    if not selected_files:
        LOGGER.warning(f"{step_name}📅[date_extractor] No valid files found for processing.")
        return

    # Step 2: Launch exiftool in background
    exiftool_cmd = [
        "../gpth_tool/exif_tool/exiftool",
        "-j", "-n", "-time:all", "-fast", "-fast2", "-s"
    ] + selected_files

    LOGGER.debug(f"{step_name}📅[date_extractor] Starting exiftool...")

    with open(output_file, "w", encoding="utf-8") as fout:
        proc = subprocess.Popen(exiftool_cmd, stdout=fout, stderr=subprocess.PIPE)
        start_time = time.time()
        last_count = 0

        # Step 3: Periodic progress feedback while exiftool runs
        while proc.poll() is None:
            time.sleep(progress_interval)
            elapsed = int(time.time() - start_time)
            try:
                if output_path.exists():
                    with open(output_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        current_count = len(data)
                        LOGGER.debug(f"{step_name}📅[date_extractor] ⏱️ {elapsed//60} min → {current_count} files processed")
                        last_count = current_count
            except Exception:
                LOGGER.warning(f"{step_name}📅[date_extractor] ⚠️ Cannot read {output_file} yet to report progress.")

        # Step 4: Final report once exiftool finishes
        proc.communicate()
        total_time = int(time.time() - start_time)

        try:
            with open(output_file, "r", encoding="utf-8") as f:
                final_data = json.load(f)
                LOGGER.debug(f"{step_name}📅[date_extractor] ✅ Completed: {len(final_data)} files processed in {total_time//60} min")
        except Exception as e:
            LOGGER.warning(f"{step_name}📅[date_extractor] ⚠️ Failed to read final output '{output_file}': {e}")


# def count_files_per_type_and_date(input_folder, skip_exif=True, skip_json=True, step_name='', log_level=None):
#     """
#     Analyze all files in `input_folder`, counting:
#       - total files
#       - supported vs unsupported files based on global extension lists
#       - image files vs video files vs metadata files vs sidecar files
#       - media files (images + videos)
#       - non-media files (metadata + sidecar)
#       - for photos and videos, how many have an assigned date vs. not
#       - percentage of photos/videos with and without date
#     Uses global PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, and TIMESTAMP.
#     """
#     with set_log_level(LOGGER, log_level):
#         # This is used to check if files had any date before Takeout Processing started.
#         timestamp_dt = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")
#
#         # Initialize overall counters with pct keys for media
#         counters = init_count_files_counters()
#
#         # Inicializa contador de tamaño en bytes
#         total_size_bytes = 0
#
#         # Get total supported extensions
#         supported_exts = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
#
#         # 1) Set de extensiones soportadas para EXIF
#         MEDIA_EXT = set(ext.lower() for ext in PHOTO_EXT + VIDEO_EXT)
#
#         # 2) IDs de EXIF para DateTimeOriginal, DateTimeDigitized, DateTime
#         WANTED_TAG_IDS = {
#             tag_id
#             for tag_id, tag_name in ExifTags.TAGS.items()
#             if tag_name in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime')
#         }
#
#         # Create a dictionary with all files dates using exiftool
#         dates_dict = get_embedded_datetimes_bulk(folder=input_folder, step_name=step_name)
#
#         # Walk through all subdirectories and files
#         for root, dirs, files in os.walk(input_folder):
#             for filename in files:
#                 file_path = os.path.join(root, filename)
#
#                 # Saltar enlaces simbólicos
#                 if os.path.islink(file_path):
#                     continue  # Skip symbolic links
#
#                 # Sumar tamaño
#                 try:
#                     total_size_bytes += os.path.getsize(file_path)
#                 except Exception:
#                     pass
#
#                 _, ext = os.path.splitext(filename)
#                 ext = ext.lower()
#
#                 # Count every file
#                 counters['total_files'] += 1
#
#                 # Determine support status
#                 if ext in supported_exts:
#                     counters['supported_files'] += 1
#                 else:
#                     counters['unsupported_files'] += 1
#
#                 # Categorize by extension
#                 if ext in PHOTO_EXT:
#                     counters['photo_files'] += 1
#                     counters['media_files'] += 1
#                     media_type = 'photos'
#                 elif ext in VIDEO_EXT:
#                     counters['video_files'] += 1
#                     counters['media_files'] += 1
#                     media_type = 'videos'
#                 else:
#                     media_type = None
#
#                 # Count metadata and sidecar
#                 if ext in METADATA_EXT:
#                     counters['metadata_files'] += 1
#                 if ext in SIDECAR_EXT:
#                     counters['sidecar_files'] += 1
#                 if ext in METADATA_EXT or ext in SIDECAR_EXT:
#                     counters['non_media_files'] += 1
#
#                 # Skip date logic for non-media
#                 if not media_type:
#                     continue
#
#                 counters[media_type]['total'] += 1
#
#                 # file_date = get_oldest_date(file_path=file_path, skip_exif=skip_exif, skip_json=skip_json)
#                 # file_date = get_oldest_date(file_path=file_path, extensions=MEDIA_EXT, tag_ids=WANTED_TAG_IDS, skip_exif=skip_exif, skip_json=skip_json)
#                 # file_date = get_embedded_datetime(file_path=file_path)
#                 file_date = dates_dict.get(Path(file_path))
#                 has_date = file_date is not None and file_date <= timestamp_dt
#
#                 if has_date:
#                     counters[media_type]['with_date'] += 1
#                 else:
#                     counters[media_type]['without_date'] += 1
#
#         # Calculate percentages for photos based on totals
#         total_photos = counters['photos']['total']
#         if total_photos > 0:
#             counters['photos']['pct_with_date'] = (counters['photos']['with_date'] / total_photos) * 100
#             counters['photos']['pct_without_date'] = (counters['photos']['without_date'] / total_photos) * 100
#
#         # Calculate percentages for videos based on totals
#         total_videos = counters['videos']['total']
#         if total_videos > 0:
#             counters['videos']['pct_with_date'] = (counters['videos']['with_date'] / total_videos) * 100
#             counters['videos']['pct_without_date'] = (counters['videos']['without_date'] / total_videos) * 100
#
#         # Añade el tamaño total en MB al resultado
#         counters['total_size_mb'] = round(total_size_bytes / (1024 * 1024), 1)
#
#         return counters

# def count_files_per_type_and_date(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="metadata_output.json", progress_interval=300, extract_dates=True, step_name=''):
#     """
#     Analyzes files under `input_folder`, and optionally extracts oldest EXIF date per file using exiftool.
#     Returns both a counters summary and a dictionary of oldest dates per file.
#     """
#     exclude_ext = set((exclude_ext or ["json"]))
#     include_ext = set(include_ext) if include_ext else None
#     input_folder = os.fspath(input_folder)  # ensure str
#     output_file = os.fspath(output_file)
#
#     # Normalize extension lists once
#     supported_exts = set(ext.lower() for ext in PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
#     media_exts = set(ext.lower() for ext in PHOTO_EXT + VIDEO_EXT)
#     timestamp_dt = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")
#
#     counters = init_count_files_counters()
#     result = {}
#     total_size_bytes = 0
#
#     selected_files = []
#     ext_cache = {}  # extension normalization cache
#
#     # Fast and memory-efficient file collection
#     for root, _, files in os.walk(input_folder):
#         for name in files:
#             full_path = os.path.join(root, name)
#             if os.path.islink(full_path):
#                 continue
#             ext = os.path.splitext(name)[1].lower()
#             if ext in exclude_ext:
#                 continue
#             if include_ext and ext not in include_ext:
#                 continue
#             selected_files.append(full_path)
#             if max_files and len(selected_files) >= max_files:
#                 break
#         if max_files and len(selected_files) >= max_files:
#             break
#
#     total_files = len(selected_files)
#     LOGGER.debug(f"{step_name}📅[count_files_per_type_and_date] {total_files} files selected for processing.")
#     if total_files == 0:
#         LOGGER.warning(f"{step_name}📅[count_files_per_type_and_date] No valid files found for processing.")
#         return counters, {}
#
#     # Extract metadata only if requested
#     metadata_by_path = {}
#     if extract_dates:
#         LOGGER.debug(f"{step_name}📅[count_files_per_type_and_date] Starting exiftool...")
#         cmd = ["../gpth_tool/exif_tool/exiftool", "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + selected_files
#
#         with open(output_file, "w", encoding="utf-8") as fout:
#             proc = subprocess.Popen(cmd, stdout=fout, stderr=subprocess.DEVNULL)
#             start_time = time.time()
#
#             while proc.poll() is None:
#                 time.sleep(progress_interval)
#                 elapsed = time.time() - start_time
#                 try:
#                     if os.path.exists(output_file):
#                         with open(output_file, "r", encoding="utf-8") as f:
#                             metadata = json.load(f)
#                             current_count = len(metadata)
#                             rate = current_count / elapsed if elapsed else 0
#                             est_total = total_files / rate if rate else 0
#                             remaining = est_total - elapsed
#                             LOGGER.debug(f"{step_name}📅[count_files_per_type_and_date] ⏱️ {int(elapsed)//60} min → {current_count}/{total_files} files • Est. total: {int(est_total)//60} min • Remaining: {int(remaining)//60} min")
#                 except Exception:
#                     pass
#
#             proc.communicate()
#
#         try:
#             with open(output_file, "r", encoding="utf-8") as f:
#                 metadata = json.load(f)
#                 metadata_by_path = {entry.get("SourceFile"): entry for entry in metadata if "SourceFile" in entry}
#         except Exception as e:
#             LOGGER.warning(f"{step_name}📅[count_files_per_type_and_date] Failed to read output: {e}")
#             return counters, {}
#
#     # Prepare once
#     candidate_tags = {
#         'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
#         'TrackCreateDate', 'EncodedDate', 'MetadataDate',
#     }
#     date_formats = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%d")
#
#     for file_path in selected_files:
#         try:
#             ext = os.path.splitext(file_path)[1].lower()
#             counters['total_files'] += 1
#             if ext in supported_exts:
#                 counters['supported_files'] += 1
#             else:
#                 counters['unsupported_files'] += 1
#
#             try:
#                 total_size_bytes += os.path.getsize(file_path)
#             except Exception:
#                 pass
#
#             media_type = None
#             if ext in PHOTO_EXT:
#                 counters['photo_files'] += 1
#                 counters['media_files'] += 1
#                 media_type = 'photos'
#             elif ext in VIDEO_EXT:
#                 counters['video_files'] += 1
#                 counters['media_files'] += 1
#                 media_type = 'videos'
#
#             if ext in METADATA_EXT:
#                 counters['metadata_files'] += 1
#             if ext in SIDECAR_EXT:
#                 counters['sidecar_files'] += 1
#             if ext in METADATA_EXT or ext in SIDECAR_EXT:
#                 counters['non_media_files'] += 1
#
#             if not extract_dates:
#                 if media_type:
#                     counters[media_type]['total'] += 1
#                     counters[media_type]['with_date'] = None
#                     counters[media_type]['without_date'] = None
#                 result[file_path] = None
#                 continue
#
#             entry = metadata_by_path.get(file_path)
#             if not entry:
#                 result[file_path] = None
#                 continue
#
#             found_dates = []
#             for tag in candidate_tags:
#                 raw = entry.get(tag)
#                 if not raw or isinstance(raw, int):
#                     continue
#                 raw = raw.strip()
#                 for fmt in date_formats:
#                     try:
#                         parsed = datetime.strptime(raw, fmt)
#                         found_dates.append(parsed)
#                         break
#                     except ValueError:
#                         continue
#
#             oldest = min(found_dates) if found_dates else None
#             result[file_path] = oldest
#
#             if media_type:
#                 counters[media_type]['total'] += 1
#                 has_date = oldest is not None and oldest <= timestamp_dt
#                 if has_date:
#                     counters[media_type]['with_date'] += 1
#                 else:
#                     counters[media_type]['without_date'] += 1
#
#         except Exception as e:
#             LOGGER.warning(f"{step_name}📅[count_files_per_type_and_date] Error: {e}")
#
#     # Final stats
#     for media_type in ['photos', 'videos']:
#         total = counters[media_type]['total']
#         if total > 0 and extract_dates:
#             with_date = counters[media_type]['with_date']
#             without_date = counters[media_type]['without_date']
#             counters[media_type]['pct_with_date'] = (with_date / total) * 100 if with_date is not None else None
#             counters[media_type]['pct_without_date'] = (without_date / total) * 100 if without_date is not None else None
#         else:
#             counters[media_type]['pct_with_date'] = None
#             counters[media_type]['pct_without_date'] = None
#
#     counters['total_size_mb'] = round(total_size_bytes / (1024 * 1024), 1)
#
#     return counters, result


# ================================
# NEW VERSION USING MULTI-THREADS
# ================================
def count_files_per_type_and_date(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="metadata_output.json", progress_interval=300, extract_dates=True, step_name='', log_level=None):
    # ==============
    # AUX FUNCTIONS:
    # ==============
    def process_block(file_list, idx, output_dir, step_name=""):
        from subprocess import run, DEVNULL

        counters = init_count_files_counters()
        result = {}
        total_size_bytes = 0

        output_json = os.path.join(output_dir, f"metadata_chunk_{idx}.json")
        cmd = ["./gpth_tool/exif_tool/exiftool", "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + file_list

        try:
            with open(output_json, "w", encoding="utf-8") as fout:
                run(cmd, stdout=fout, stderr=DEVNULL, check=True)
        except Exception as e:
            LOGGER.warning(f"{step_name}📅[block {idx}] exiftool failed: {e}")
            return counters, result

        candidate_tags = [
            'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
            'TrackCreateDate', 'EncodedDate', 'MetadataDate',
        ]
        date_formats = [
            "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d", "%Y-%m-%d"
        ]
        supported_exts = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
        timestamp_dt = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")

        try:
            with open(output_json, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            LOGGER.warning(f"{step_name}📅[block {idx}] can't read JSON: {e}")
            return counters, result

        metadata_by_path = {entry["SourceFile"]: entry for entry in metadata if "SourceFile" in entry}

        for path in file_list:
            try:
                ext = Path(path).suffix.lower()
                counters['total_files'] += 1
                if ext in supported_exts:
                    counters['supported_files'] += 1
                else:
                    counters['unsupported_files'] += 1
                try:
                    total_size_bytes += os.path.getsize(path)
                except Exception:
                    pass
                media_type = None
                if ext in PHOTO_EXT:
                    counters['photo_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'photos'
                elif ext in VIDEO_EXT:
                    counters['video_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'videos'
                if ext in METADATA_EXT:
                    counters['metadata_files'] += 1
                if ext in SIDECAR_EXT:
                    counters['sidecar_files'] += 1
                if ext in METADATA_EXT or ext in SIDECAR_EXT:
                    counters['non_media_files'] += 1

                entry = metadata_by_path.get(path)
                if not entry:
                    result[path] = None
                    continue

                found_dates = []
                for tag in candidate_tags:
                    raw = entry.get(tag)
                    if not raw or isinstance(raw, int):
                        continue
                    raw = raw.strip()
                    for fmt in date_formats:
                        try:
                            parsed = datetime.strptime(raw, fmt)
                            found_dates.append(parsed)
                            break
                        except Exception:
                            continue

                oldest = min(found_dates) if found_dates else None
                result[path] = oldest
                if media_type:
                    counters[media_type]['total'] += 1
                    if oldest and oldest <= timestamp_dt:
                        counters[media_type]['with_date'] += 1
                    else:
                        counters[media_type]['without_date'] += 1
            except Exception as e:
                LOGGER.warning(f"{step_name}📅[block {idx}] error: {e}")

        counters['total_size_mb'] = round(total_size_bytes / (1024 * 1024), 1)
        return counters, result

    def merge_counters(list_of_counters):
        merged = init_count_files_counters()
        for c in list_of_counters:
            for key in merged:
                if isinstance(merged[key], dict):
                    for subkey in merged[key]:
                        merged[key][subkey] += c[key].get(subkey, 0)
                else:
                    merged[key] += c.get(key, 0)
        for media_type in ['photos', 'videos']:
            total = merged[media_type]['total']
            if total > 0:
                merged[media_type]['pct_with_date'] = (merged[media_type]['with_date'] / total) * 100
                merged[media_type]['pct_without_date'] = (merged[media_type]['without_date'] / total) * 100
            else:
                merged[media_type]['pct_with_date'] = None
                merged[media_type]['pct_without_date'] = None
        return merged

    def merge_json_files(temp_dir, final_output_path):
        merged = []
        for file in sorted(Path(temp_dir).glob("metadata_chunk_*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged.extend(data)
            except Exception:
                continue
        with open(final_output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    # =====================
    # END OF AUX FUNCTIONS:
    # =====================

    with set_log_level(LOGGER, log_level):
        counters = init_count_files_counters()
        dates = {}

        exclude_ext = set(exclude_ext) if exclude_ext else set()
        exclude_ext.update({"json"})  # siempre excluir .json
        include_ext = set(include_ext) if include_ext else None
        input_folder = os.fspath(input_folder)
        output_file = os.fspath(output_file)

        supported_exts = set(ext.lower() for ext in PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
        timestamp_dt = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")
        all_files = []

        for root, dirs, files in os.walk(input_folder):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '@eaDir']
            for name in files:
                full_path = os.path.join(root, name)
                if os.path.islink(full_path):
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext in exclude_ext:
                    continue
                if include_ext and ext not in include_ext:
                    continue
                all_files.append(full_path)
                if max_files and len(all_files) >= max_files:
                    break
            if max_files and len(all_files) >= max_files:
                break

        total_files = len(all_files)
        LOGGER.debug(f"{step_name}📅[count_files_per_type_and_date] {total_files} files selected for processing.")

        from collections import Counter
        ext_stats = Counter(Path(f).suffix.lower() for f in all_files)
        LOGGER.debug(f"{step_name}📊 Extensiones encontradas: {ext_stats}")

        if total_files == 0:
            LOGGER.warning(f"{step_name}📅[count_files_per_type_and_date] No valid files found.")
            return counters, dates

        if not extract_dates:
            for path in all_files:
                ext = os.path.splitext(path)[1].lower()
                counters['total_files'] += 1
                if ext in supported_exts:
                    counters['supported_files'] += 1
                else:
                    counters['unsupported_files'] += 1
                if ext in PHOTO_EXT:
                    counters['photo_files'] += 1
                    counters['media_files'] += 1
                    counters['photos']['total'] += 1
                elif ext in VIDEO_EXT:
                    counters['video_files'] += 1
                    counters['media_files'] += 1
                    counters['videos']['total'] += 1
                if ext in METADATA_EXT:
                    counters['metadata_files'] += 1
                if ext in SIDECAR_EXT:
                    counters['sidecar_files'] += 1
                if ext in METADATA_EXT or ext in SIDECAR_EXT:
                    counters['non_media_files'] += 1
                dates[path] = None

            for media_type in ['photos', 'videos']:
                counters[media_type]['with_date'] = None
                counters[media_type]['without_date'] = None
                counters[media_type]['pct_with_date'] = None
                counters[media_type]['pct_without_date'] = None

            counters['total_size_mb'] = round(sum(os.path.getsize(p) for p in all_files if os.path.exists(p)) / (1024 * 1024), 1)
            return counters, dates

        if total_files <= 10000:
            counters, dates = process_block(all_files, 0, os.path.dirname(output_file), step_name)
            shutil.move(os.path.join(os.path.dirname(output_file), "metadata_chunk_0.json"), output_file)
            return counters, dates

        num_cores = multiprocessing.cpu_count()
        chunk_size = math.ceil(total_files / num_cores)
        chunks = [all_files[i:i + chunk_size] for i in range(0, total_files, chunk_size)]

        LOGGER.debug(f"{step_name}📅[count_files_per_type_and_date] Launching {len(chunks)} parallel blocks...")

        with TemporaryDirectory() as temp_dir:
            with multiprocessing.Pool(processes=len(chunks)) as pool:
                results = [
                    pool.apply_async(process_block, args=(chunk, i, temp_dir, step_name))
                    for i, chunk in enumerate(chunks)
                ]
                results = [r.get() for r in results]

            all_counters = [r[0] for r in results]
            all_dicts = [r[1] for r in results]

            counters = merge_counters(all_counters)
            dates = {}
            for d in all_dicts:
                dates.update(d)

            merge_json_files(temp_dir, output_file)

        return counters, dates
