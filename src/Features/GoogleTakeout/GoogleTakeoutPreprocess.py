import logging
import os
import re
import shutil
from pathlib import Path

from Core import GlobalVariables as GV
from Core.CustomLogger import set_log_level
from Core.Utils import tqdm


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def delete_subfolders(input_folder, folder_name_to_delete, step_name="", log_level=None):
    """
    Deletes all subdirectories (and their contents) inside the given base directory and all its subdirectories,
    whose names match dir_name_to_delete, including hidden directories.

    Args:
        input_folder (str, Path): The path to the base directory to start the search from.
        folder_name_to_delete (str): The name of the subdirectories to delete.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Contar el total de carpetas
        total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(input_folder)])
        # Mostrar la barra de progreso basada en carpetas
        with tqdm(total=total_dirs, smoothing=0.1, desc=f"{GV.TAG_INFO}{step_name}Deleting files within subfolders '{folder_name_to_delete}' in '{input_folder}'", unit=" subfolders") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=False):
                for folder in dirs:
                    pbar.update(1)
                    if folder == folder_name_to_delete:
                        dir_path = os.path.join(path, folder)
                        try:
                            shutil.rmtree(dir_path)
                            # GV.LOGGER.info(f"Deleted directory: {dir_path}")
                        except Exception as e:
                            GV.LOGGER.error(f"{step_name}Error deleting {dir_path}: {e}")


def fix_mp4_files(input_folder, step_name="", log_level=None):
    """
    Look for all .MP4 files that have the same base name as any Live Picture in the same folder.
    If found, copy the associated .json file (including those with a truncated '.supplemental-metadata')
    and rename it to match the .MP4 file, completing the truncated suffix if necessary.

    Args:
        input_folder (str): The root folder to scan.
        log_level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
    """
    with set_log_level(GV.LOGGER, log_level):  # Set desired log level
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
        with tqdm(total=total_files, smoothing=0.1, desc=f"{GV.TAG_INFO}{step_name}Fixing .MP4 files in '{input_folder}'", unit=" files", disable=disable_tqdm) as pbar:
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
                        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + GV.SUPPLEMENTAL_METADATA
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
                            if suffix and not suffix.lower().startswith(GV.SUPPLEMENTAL_METADATA):
                                # Try to match a valid truncation
                                for i in range(2, len(GV.SUPPLEMENTAL_METADATA) + 1):
                                    if suffix.lower() == GV.SUPPLEMENTAL_METADATA[:i]:
                                        suffix = '.'+GV.SUPPLEMENTAL_METADATA
                                        break
                            # Generate the new name for the duplicated file
                            new_json_name = f"{mp4_file}{suffix}.json"
                            new_json_path = os.path.join(path, new_json_name)
                            # Check if the target file already exists to avoid overwriting
                            if not os.path.exists(new_json_path):
                                # Copy the original JSON file to the new file
                                if candidate_path.lower != new_json_path.lower():
                                    shutil.copy(candidate_path, new_json_path)
                                    GV.LOGGER.info(f"{step_name}Copied: {candidate} -> {new_json_name}")
                                    counter_mp4_files_changed += 1
                                    continue # if already found a matched candidate, then continue with the next file
                            else:
                                GV.LOGGER.info(f"{step_name}Skipped: {new_json_name} already exists")
        return counter_mp4_files_changed


def fix_truncations(input_folder, step_name="", log_level=logging.INFO, name_length_threshold=46):
    """
    Recursively traverses `input_folder` and fixes:
      1) .json files with a truncated '.supplemental-metadata' suffix.
      2) .json files whose original extension is truncated (e.g. .jp.json → .jpg.json),
         by finding the real asset file in the same directory.
      3) Non-.json files with truncated special suffixes (based on GV.SPECIAL_SUFFIXES).
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

    variants_specials_pattern = make_variant_pattern(GV.SPECIAL_SUFFIXES)
    variants_editted_pattern = make_variant_pattern(GV.EDITTED_SUFFIXES)
    optional_counter = r'(?:\(\d+\))?'  # allow "(n)" counters
    with set_log_level(GV.LOGGER, log_level):
        # --------------------------
        # --- Case A: JSON files ---
        # --------------------------
        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + GV.SUPPLEMENTAL_METADATA
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
                            GV.LOGGER.verbose(f"{step_name}Fixed JSON Supplemental Ext: {file} → {new_name}")
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
                                GV.LOGGER.verbose(f"{step_name}Fixed JSON Origin File Ext : {file} → {new_name}")
                                counters["extensions_fixed"] += 1
                                if not file_modified:
                                    counters["json_files_fixed"] += 1
                                    counters["total_files_fixed"] += 1
                                    file_modified = True
                    # end A.2

                    if file_modified:
                        GV.LOGGER.debug(f"{step_name}Fixed JSON File  : {original_file} → {new_name}")

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
                    for suf in GV.SPECIAL_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}(?=(-|_|\.|{variants_editted_pattern}|{GV.SUPPLEMENTAL_METADATA})?(?:\(\d+\))?{re.escape(ext)}$)",
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
                                        GV.LOGGER.verbose(f"{step_name}Fixed ORIGIN Special Suffix: {file} → {new_name}")
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
                    for suf in GV.EDITTED_SUFFIXES:
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
                                    GV.LOGGER.verbose(f"{step_name}Fixed ORIGIN Edited Suffix : {file} → {new_name}")
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
                        GV.LOGGER.debug(f"{step_name}Fixed MEDIA File : {original_file} → {new_name}")
    return counters
