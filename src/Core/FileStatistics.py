import json
import multiprocessing
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from subprocess import run, DEVNULL
from tempfile import TemporaryDirectory

from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import LOGGER, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, TIMESTAMP


# ---------------------------------------------------------------------------------------------------------------------------
# FILES STATISTICS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------

# ===================================================================================================================================================
# NEW VERSION OF COUNT_FILES_PER_TYPE_AND_DATE USING MULTI-PROCESS (BETTER THAN MULTI-THREADS HIGH CPU OPERATIONS). DON'T SUPPORT EMBEDDED FUNCTIONS)
# ===================================================================================================================================================
#
# Auxiliary Functions cannot be embedded within the main function because multi-thread processing does not support that.
#
# ------------------------------------------------------------------
# Aux: merge counters from multiple blocks
# ------------------------------------------------------------------
def merge_counters(list_of_counter_dicts):
    merged_counters = init_count_files_counters()
    for counter_dict in list_of_counter_dicts:
        for key, value in counter_dict.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    merged_counters[key][subkey] += subvalue
            else:
                merged_counters[key] += value
    return merged_counters

# ------------------------------------------------------------------
# Aux: merge JSON outputs from each block into one file
# ------------------------------------------------------------------
def merge_json_files(temporary_directory, final_output_path):
    combined_metadata = []
    for chunk_file in sorted(Path(temporary_directory).glob("metadata_chunk_*.json")):
        try:
            with open(chunk_file, "r", encoding="utf-8") as handle:
                combined_metadata.extend(json.load(handle))
        except Exception:
            continue
    with open(final_output_path, "w", encoding="utf-8") as handle:
        json.dump(combined_metadata, handle, ensure_ascii=False, indent=2)

# ------------------------------------------------------------------
# Aux: process a list of files, extract EXIF-date and count types
# ------------------------------------------------------------------
def process_block(file_paths, block_index, temporary_directory, extract_dates, step_name):
    candidate_date_tags = [
        'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
        'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate'
    ]
    date_formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d",
        "%Y-%m-%d"
    ]
    supported_extensions = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
    reference_timestamp = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")

    counters = init_count_files_counters()
    dates_by_path = {}
    total_bytes = 0

    chunk_json_path = os.path.join(temporary_directory, f"metadata_chunk_{block_index}.json")

    # 1) Extract dates If extract_dates is enabled --> run exiftool and load metadata
    if extract_dates:
        command = [
            "./gpth_tool/exif_tool/exiftool",
            "-j", "-n", "-time:all", "-fast", "-fast2", "-s"
        ] + file_paths
        try:
            with open(chunk_json_path, "w", encoding="utf-8") as output_handle:
                run(command, stdout=output_handle, stderr=DEVNULL, check=True)
            metadata_list = json.load(open(chunk_json_path, "r", encoding="utf-8"))
            metadata_map = {
                entry["SourceFile"]: entry
                for entry in metadata_list
                if "SourceFile" in entry
            }
        except Exception as error:
            LOGGER.warning(f"{step_name}📅[block {block_index}] exiftool failed: {error}")
            metadata_map = {}
    else:
        metadata_map = {}

    # 2) Iterate files and update counters and dates
    for file_path in file_paths:
        counters['total_files'] += 1
        ext = Path(file_path).suffix.lower()
        if ext in supported_extensions:
            counters['supported_files'] += 1
        else:
            counters['unsupported_files'] += 1

        try:
            total_bytes += os.path.getsize(file_path)
        except:
            pass

        media_category = None
        if ext in PHOTO_EXT:
            counters['photo_files'] += 1; counters['media_files'] += 1; media_category='photos'
        elif ext in VIDEO_EXT:
            counters['video_files'] += 1; counters['media_files'] += 1; media_category='videos'
        if ext in METADATA_EXT: counters['metadata_files'] += 1
        if ext in SIDECAR_EXT:  counters['sidecar_files'] += 1
        if ext in METADATA_EXT or ext in SIDECAR_EXT:
            counters['non_media_files'] += 1

        # If dates not extracted, record None and increment totals
        if not extract_dates:
            dates_by_path[file_path] = None
            if media_category:
                counters[media_category]['total'] += 1
            continue

        # Otherwise, parse metadata for this file
        entry = metadata_map.get(file_path)
        if not entry:
            dates_by_path[file_path] = None
            continue

        found_dates = []
        for tag in candidate_date_tags:
            raw_value = entry.get(tag)
            if isinstance(raw_value, str):
                for fmt in date_formats:
                    try:
                        found_dates.append(datetime.strptime(raw_value.strip(), fmt))
                        break       # No try with another date format if one of them has already matched
                    except ValueError:
                        continue    # Try with another date format if the current one does not match

        oldest_date = min(found_dates) if found_dates else None
        dates_by_path[file_path] = oldest_date

        if media_category:
            counters[media_category]['total'] += 1
            # If the oldest_date found is after current execution TIMESTAMP (reference_timestamp) means that only tag FileModifyDate have been found
            # and the modification have been done by this tool while unpacking, so not count this asset as asset with date
            if oldest_date and oldest_date < reference_timestamp:
                counters[media_category]['with_date'] += 1
            else:
                counters[media_category]['without_date'] += 1

    counters['total_size_mb'] = round(total_bytes / (1024 * 1024), 1)
    return counters, dates_by_path

# --------------------
# MAIN FUNCTION LOGIC
# --------------------
def count_files_per_type_and_extract_dates_multi_process(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="dates_metadata.json", extract_dates=True, step_name='', log_level=None):
    """
        Main orchestration: divides files into fixed 10 000-file blocks, runs each block
        in parallel via process_block, shows overall progress as blocks complete,
        merges JSON outputs and counters, then computes final percentages.
    """
    with set_log_level(LOGGER, log_level):
        # --- 1) Prepare extension filters
        excluded_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (exclude_ext or [])} | {".json"}    # Accepts exclude_ext with and without '.' and union also with '.json' that always will be excluded.
        included_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (include_ext or [])} or None        # Accepts include_ext with and without '.'

        # --- 2) Collect all file paths
        all_file_paths = []
        for root, dirs, files in os.walk(input_folder):
            # always skip hidden dirs and Synology @eaDir
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '@eaDir']
            for filename in files:
                full_path = os.path.join(root, filename)
                if os.path.islink(full_path):
                    continue
                extension = Path(filename).suffix.lower()
                if extension in excluded_extensions:
                    continue
                if included_extensions and extension not in included_extensions:
                    continue
                all_file_paths.append(full_path)
                if max_files and len(all_file_paths) >= max_files:
                    break
            if max_files and len(all_file_paths) >= max_files:
                break

        total_files = len(all_file_paths)
        LOGGER.debug(f"{step_name}{total_files} files selected")

        if total_files == 0:
            return init_count_files_counters(), {}

        # --- 3) Always split into 10 000-file blocks
        block_size = 10_000
        file_blocks = [
            all_file_paths[i: i + block_size]
            for i in range(0, total_files, block_size)
        ]
        num_blocks = len(file_blocks)
        LOGGER.debug(f"{step_name}Launching {num_blocks} blocks of ~{block_size} files")

        # --- 4) Run blocks in parallel, reporting overall progress
        start_time = time.time()
        completed_blocks = 0
        merged_counters_list = []
        merged_dates = {}

        with TemporaryDirectory() as temp_dir:
            with multiprocessing.Pool() as pool:
                async_results = [
                    pool.apply_async(process_block, (block, idx, temp_dir, extract_dates, step_name))
                    for idx, block in enumerate(file_blocks)
                ]
                for async_res in async_results:
                    block_counters, block_dates = async_res.get()
                    completed_blocks += 1

                    # Progress report
                    elapsed = time.time() - start_time
                    avg_block_time = elapsed / completed_blocks
                    remaining = avg_block_time * (num_blocks - completed_blocks)
                    LOGGER.info(
                        f"{step_name}📊 Block {completed_blocks}/{num_blocks} done • "
                        f"Elapsed: {int(elapsed // 60)}m • Estimated Remaining: {int(remaining // 60)}m"
                    )

                    merged_counters_list.append(block_counters)
                    merged_dates.update(block_dates)

            # Merge JSON outputs if we extracted dates
            if extract_dates:
                merge_json_files(temp_dir, output_file)

        # --- 5) Merge all block counters and compute final percentages
        final_counters = merge_counters(merged_counters_list)
        for media_category in ['photos', 'videos']:
            total_count = final_counters[media_category]['total']
            if total_count > 0 and extract_dates:
                with_date = final_counters[media_category]['with_date']
                final_counters[media_category]['pct_with_date'] = (with_date / total_count) * 100
                final_counters[media_category]['pct_without_date'] = ((total_count - with_date) / total_count) * 100
            else:
                final_counters[media_category]['pct_with_date'] = None
                final_counters[media_category]['pct_without_date'] = None

        return final_counters, merged_dates




# ================================================================================================================================================
# NEW VERSION OF COUNT_FILES_PER_TYPE_AND_DATE USING MULTI-THREADS (BETTER THAN MULTI-PROCESS FOR I/O OPERATIONS) AND SUPPORTS EMBEDDED FUNCTIONS)
# ================================================================================================================================================
def count_files_per_type_and_extract_dates_multi_threads(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="dates_metadata.json", extract_dates=True, step_name='', log_level=None):
    """
        Main orchestration: divides files into fixed 10 000-file blocks, runs each block
        in parallel via process_block, shows overall progress as blocks complete,
        merges JSON outputs and counters, then computes final percentages.
    """

    # ====================
    # AUX FUNCTIONS
    # ====================

    # ------------------------------------------------------------------
    # Aux: merge counters from multiple blocks
    # ------------------------------------------------------------------
    def merge_counters(list_of_counter_dicts):
        merged_counters = init_count_files_counters()
        for counter_dict in list_of_counter_dicts:
            for key, value in counter_dict.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        merged_counters[key][subkey] += subvalue
                else:
                    merged_counters[key] += value
        return merged_counters

    # ------------------------------------------------------------------
    # Aux: merge JSON outputs from each block into one file
    # ------------------------------------------------------------------
    def merge_json_files(temporary_directory, final_output_path):
        combined_metadata = []
        for chunk_file in sorted(Path(temporary_directory).glob("metadata_chunk_*.json")):
            try:
                with open(chunk_file, "r", encoding="utf-8") as handle:
                    combined_metadata.extend(json.load(handle))
            except Exception:
                continue
        with open(final_output_path, "w", encoding="utf-8") as handle:
            json.dump(combined_metadata, handle, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Aux: process a list of files, extract EXIF-date and count types
    # ------------------------------------------------------------------
    def process_block(file_paths, block_index, temporary_directory, extract_dates, step_name):
        candidate_date_tags = [
            'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
            'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate'
        ]
        date_formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d",
            "%Y-%m-%d"
        ]
        supported_extensions = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
        reference_timestamp = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")

        counters = init_count_files_counters()
        dates_by_path = {}
        total_bytes = 0

        chunk_json_path = os.path.join(temporary_directory, f"metadata_chunk_{block_index}.json")

        # 1) Extract dates If extract_dates is enabled --> run exiftool and load metadata
        if extract_dates:
            command = [
                          "./gpth_tool/exif_tool/exiftool",
                          "-j", "-n", "-time:all", "-fast", "-fast2", "-s"
                      ] + file_paths
            try:
                with open(chunk_json_path, "w", encoding="utf-8") as output_handle:
                    run(command, stdout=output_handle, stderr=DEVNULL, check=True)
                metadata_list = json.load(open(chunk_json_path, "r", encoding="utf-8"))
                metadata_map = {
                    entry["SourceFile"]: entry
                    for entry in metadata_list
                    if "SourceFile" in entry
                }
            except Exception as error:
                LOGGER.warning(f"{step_name}📅[block {block_index}] exiftool failed: {error}")
                metadata_map = {}
        else:
            metadata_map = {}

        # 2) Iterate files and update counters and dates
        for file_path in file_paths:
            counters['total_files'] += 1
            ext = Path(file_path).suffix.lower()
            if ext in supported_extensions:
                counters['supported_files'] += 1
            else:
                counters['unsupported_files'] += 1

            try:
                total_bytes += os.path.getsize(file_path)
            except:
                pass

            media_category = None
            if ext in PHOTO_EXT:
                counters['photo_files'] += 1;
                counters['media_files'] += 1;
                media_category = 'photos'
            elif ext in VIDEO_EXT:
                counters['video_files'] += 1;
                counters['media_files'] += 1;
                media_category = 'videos'
            if ext in METADATA_EXT: counters['metadata_files'] += 1
            if ext in SIDECAR_EXT:  counters['sidecar_files'] += 1
            if ext in METADATA_EXT or ext in SIDECAR_EXT:
                counters['non_media_files'] += 1

            # If dates not extracted, record None and increment totals
            if not extract_dates:
                dates_by_path[file_path] = None
                if media_category:
                    counters[media_category]['total'] += 1
                continue

            # Otherwise, parse metadata for this file
            entry = metadata_map.get(file_path)
            if not entry:
                dates_by_path[file_path] = None
                continue

            found_dates = []
            for tag in candidate_date_tags:
                raw_value = entry.get(tag)
                if isinstance(raw_value, str):
                    for fmt in date_formats:
                        try:
                            found_dates.append(datetime.strptime(raw_value.strip(), fmt))
                            break  # No try with another date format if one of them has already matched
                        except ValueError:
                            continue  # Try with another date format if the current one does not match

            oldest_date = min(found_dates) if found_dates else None
            dates_by_path[file_path] = oldest_date

            if media_category:
                counters[media_category]['total'] += 1
                # If the oldest_date found is after current execution TIMESTAMP (reference_timestamp) means that only tag FileModifyDate have been found
                # and the modification have been done by this tool while unpacking, so not count this asset as asset with date
                if oldest_date and oldest_date < reference_timestamp:
                    counters[media_category]['with_date'] += 1
                else:
                    counters[media_category]['without_date'] += 1

        counters['total_size_mb'] = round(total_bytes / (1024 * 1024), 1)
        return counters, dates_by_path

    # ====================
    # AUX FUNCTIONS
    # ====================
    # --------------------
    # MAIN FUNCTION LOGIC
    # --------------------
    with set_log_level(LOGGER, log_level):
        # --- 1) Prepare extension filters
        excluded_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (exclude_ext or [])} | {".json"}    # Accepts exclude_ext with and without '.' and union also with '.json' that always will be excluded.
        included_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (include_ext or [])} or None        # Accepts include_ext with and without '.'

        # --- 2) Collect all file paths
        all_file_paths = []
        for root, dirs, files in os.walk(input_folder):
            # always skip hidden dirs and Synology @eaDir
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '@eaDir']
            for filename in files:
                full_path = os.path.join(root, filename)
                if os.path.islink(full_path):
                    continue
                extension = Path(filename).suffix.lower()
                if extension in excluded_extensions:
                    continue
                if included_extensions and extension not in included_extensions:
                    continue
                all_file_paths.append(full_path)
                if max_files and len(all_file_paths) >= max_files:
                    break
            if max_files and len(all_file_paths) >= max_files:
                break

        total_files = len(all_file_paths)
        LOGGER.debug(f"{step_name}{total_files} files selected")

        if total_files == 0:
            return init_count_files_counters(), {}

        # --- 3) Always split into 10 000-file blocks
        block_size = 10_000
        file_blocks = [
            all_file_paths[i: i + block_size]
            for i in range(0, total_files, block_size)
        ]
        num_blocks = len(file_blocks)
        LOGGER.debug(f"{step_name}Launching {num_blocks} blocks of ~{block_size} files")

        # --- 4) Run blocks in parallel, reporting overall progress
        start_time = time.time()
        completed_blocks = 0
        merged_counters_list = []
        merged_dates = {}

        with TemporaryDirectory() as temp_dir:

            # Number of threads (default, #cores)
            num_threads = multiprocessing.cpu_count()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # enviamos cada bloque al executor
                future_to_block = {
                    executor.submit(process_block, block, idx, temp_dir, extract_dates, step_name): idx
                    for idx, block in enumerate(file_blocks)
                }

                completed_blocks = 0
                start = time.time()
                merged_counters_list = []
                merged_dates = {}

                for future in as_completed(future_to_block):
                    block_counters, block_dates = future.result()
                    completed_blocks += 1

                    # Progress report
                    elapsed = time.time() - start
                    avg_block_time = elapsed / completed_blocks
                    remain = avg_block_time * (num_blocks - completed_blocks)
                    LOGGER.debug(f"{step_name}📊 Block {completed_blocks}/{num_blocks} done • "
                                 f"Elapsed: {int(elapsed // 60)}m • Estimated Remaining: {int(remain // 60)}m")

                    merged_counters_list.append(block_counters)
                    merged_dates.update(block_dates)

            # Merge JSON outputs if we extracted dates
            if extract_dates:
                merge_json_files(temp_dir, output_file)

        # --- 5) Merge all block counters and compute final percentages
        final_counters = merge_counters(merged_counters_list)
        for media_category in ['photos', 'videos']:
            total_count = final_counters[media_category]['total']
            if total_count > 0 and extract_dates:
                with_date = final_counters[media_category]['with_date']
                final_counters[media_category]['pct_with_date'] = (with_date / total_count) * 100
                final_counters[media_category]['pct_without_date'] = ((total_count - with_date) / total_count) * 100
            else:
                final_counters[media_category]['pct_with_date'] = None
                final_counters[media_category]['pct_without_date'] = None

        return final_counters, merged_dates