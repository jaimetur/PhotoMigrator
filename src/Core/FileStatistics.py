import json
import multiprocessing
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from datetime import timezone
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

from PIL import ExifTags, Image
from dateutil import parser

from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import LOGGER, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, TIMESTAMP, FOLDERNAME_EXIFTOOL_OUTPUT, FOLDERNAME_EXIFTOOL
from Features.GoogleTakeout.MetadataFixers import get_exif_tool_path


# ---------------------------------------------------------------------------------------------------------------------------
# FILES STATISTICS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
# ================================================================================================================================================
# NEW VERSION OF COUNT_FILES_PER_TYPE_AND_DATE USING MULTI-THREADS (BETTER THAN MULTI-PROCESS FOR I/O OPERATIONS) AND SUPPORTS EMBEDDED FUNCTIONS)
# ================================================================================================================================================
def count_files_and_extract_dates(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="dates_metadata.json", extract_dates=True, step_name='', log_level=None):
    """
        Main orchestration: divides files into fixed 10 000-file blocks, runs each block
        in parallel via process_block, shows overall progress as blocks complete,
        merges JSON outputs and counters, then computes final percentages.
    """

    # ====================
    # AUX FUNCTIONS
    # ====================
    # Ensure output_file has an extension; default to .json
    if not os.path.splitext(output_file)[1]:
        output_file = output_file + '.json'
    # Separate output_filename and output_ext
    output_filename, output_ext = os.path.splitext(output_file)
    # Add TIMESTAMP to output_file
    output_filename = f"{TIMESTAMP}_{output_filename}"
    output_file = f"{output_filename}{output_ext}"
    # ------------------------------------------------------------------
    # Aux: merge counters from multiple blocks
    # ------------------------------------------------------------------
    def merge_counters(list_of_counter_dicts):
        merged_counters = init_count_files_counters()
        for counter_dict in list_of_counter_dicts:
            for media_category in ['photos', 'videos']:
                for key in ['total', 'with_date', 'without_date']:
                    merged_counters[media_category][key] += counter_dict[media_category][key]
        return merged_counters

    # ------------------------------------------------------------------
    # Aux: merge JSON outputs from each block into one file
    # ------------------------------------------------------------------
    def merge_json_files(temporary_directory, final_output_path):
        combined_metadata = []
        for chunk_file in sorted(Path(temporary_directory).glob(f"{TIMESTAMP}_{output_filename}_*{output_ext}")):
            try:
                # Read and accumulate metadata_chunk
                with open(chunk_file, "r", encoding="utf-8") as handle:
                    combined_metadata.extend(json.load(handle))
                # Remove metadata_chunk once read
                os.remove(chunk_file)
            except Exception:
                continue
        # Write to final JSON
        with open(final_output_path, "w", encoding="utf-8") as handle:
            json.dump(combined_metadata, handle, ensure_ascii=False, indent=2)
    # ------------------------------------------------------------------
    # Aux: process a list of files, extract EXIF-date and count types
    # ------------------------------------------------------------------
    def process_block(file_paths, block_index, temporary_directory, extract_dates, step_name):
        block_index += 1
        candidate_date_tags = [
            'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
            'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate'
        ]
        supported_extensions = set(PHOTO_EXT + VIDEO_EXT)
        reference_timestamp = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S")

        counters = init_count_files_counters()
        dates_by_path = {}

        # chunk_json in temporary directory and error_log in current directory
        chunk_json_path = os.path.join(
            temporary_directory,
            f"{TIMESTAMP}_{output_filename}_{block_index}{output_ext}"
        )
        error_log_path = os.path.abspath(
            os.path.join(
                FOLDERNAME_EXIFTOOL_OUTPUT,
                f"{TIMESTAMP}_exiftool_log.log"
            )
        )

        # 1) Extract dates If extract_dates is enabled --> run exiftool and load metadata (or fallback to PIL)
        metadata_map = {}
        if extract_dates:
            # Get exiftool complete path
            exif_tool_path = get_exif_tool_path(FOLDERNAME_EXIFTOOL)
            if Path(exif_tool_path).exists():
                # Prepare exiftool command
                command = [
                    exif_tool_path,
                    "-j", "-n", "-time:all", "-fast", "-fast2", "-s"
                ] + file_paths
                try:
                    with open(chunk_json_path, "w", encoding="utf-8") as out_json, \
                            open(error_log_path, "a", encoding="utf-8") as out_err:
                        run(command, stdout=out_json, stderr=out_err, check=True)
                except Exception:
                    LOGGER.debug(f"{step_name}📅 [Block {block_index}] exiftool failed to extract some files")

                # Parse exiftool output
                with open(chunk_json_path, "r", encoding="utf-8") as out_json:
                    metadata_list = json.load(out_json)

                for entry in metadata_list:
                    src = entry.get("SourceFile")
                    if not src:
                        continue
                    norm = Path(src).resolve().as_posix().lower()
                    found = []
                    for tag in candidate_date_tags:
                        raw = entry.get(tag)
                        if isinstance(raw, str):
                            try:
                                found.append(parser.parse(raw.strip()))
                            except (ValueError, OverflowError):
                                continue

                    # Normaliza todos a timezone.utc (offset-aware)
                    normalized = [dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc) for dt in found]
                    metadata_map[norm] = min(normalized) if normalized else None

            else:
                LOGGER.warning(f"{step_name}📅 [Block {block_index}] exiftool not found at {exif_tool_path}, falling back to PIL")
                for p in file_paths:
                    norm = Path(p).resolve().as_posix().lower()
                    try:
                        img = Image.open(p)
                        exif_data = img._getexif() or {}
                        dt_found = None
                        for tag_name in ("DateTimeOriginal", "DateTime"):
                            tag_id = next((tid for tid, name in ExifTags.TAGS.items() if name == tag_name), None)
                            raw = exif_data.get(tag_id)
                            if isinstance(raw, str):
                                dt_found = datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S")
                                break
                        metadata_map[norm] = dt_found
                    except Exception as e:
                        LOGGER.debug(f"{step_name}📅 [Block {block_index}] PIL failed on {p}: {e}")
                        metadata_map[norm] = None

        # 2) Count only per-media category with/without date
        for file_path in file_paths:
            norm_filepath = Path(file_path).resolve().as_posix().lower()
            ext = Path(file_path).suffix.lower()

            media_category = None
            if ext in PHOTO_EXT:
                media_category = 'photos'
            elif ext in VIDEO_EXT:
                media_category = 'videos'

            if not media_category:
                continue

            counters[media_category]['total'] += 1

            file_date = metadata_map.get(norm_filepath) if extract_dates else None
            dates_by_path[norm_filepath] = file_date

            # Determine effective date
            effective_date = file_date
            if not file_date or (file_date and file_date >= reference_timestamp):
                try:
                    fs_ctime = datetime.fromtimestamp(os.path.getctime(file_path))
                except Exception:
                    fs_ctime = None
                effective_date = fs_ctime

            if effective_date and effective_date < reference_timestamp:
                counters[media_category]['with_date'] += 1
            else:
                counters[media_category]['without_date'] += 1

        return counters, dates_by_path
    # ====================
    # END OF AUX FUNCTIONS
    # ====================

    # ====================
    # MAIN FUNCTION LOGIC
    # ====================
    def main():
        with set_log_level(LOGGER, log_level):
            # --- 1) Prepare extension filters
            excluded_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (exclude_ext or [])} or None    # Accepts exclude_ext with and without '.'
            included_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (include_ext or [])} or None    # Accepts include_ext with and without '.'

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
                    if excluded_extensions and extension in excluded_extensions:
                        continue
                    if included_extensions and extension not in included_extensions:
                        continue
                    all_file_paths.append(full_path)
                    if max_files and len(all_file_paths) >= max_files:
                        break
                if max_files and len(all_file_paths) >= max_files:
                    break

            total_files = len(all_file_paths)
            total_non_json = sum(1 for f in all_file_paths if Path(f).suffix.lower() != ".json")
            LOGGER.info(f"{step_name}{total_files} files selected ({total_non_json} excluding .json)")
            if total_files == 0:
                return init_count_files_counters(), {}

            # --- 3) Perform global count of file types before block processing
            final_counters = init_count_files_counters()
            total_bytes = 0
            media_file_paths = []
            supported_extensions = set(PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)

            for file_path in all_file_paths:
                final_counters['total_files'] += 1
                ext = Path(file_path).suffix.lower()

                if ext in supported_extensions:
                    final_counters['supported_files'] += 1
                else:
                    final_counters['unsupported_files'] += 1

                try:
                    total_bytes += os.path.getsize(file_path)
                except:
                    pass

                media_category = None
                if ext in PHOTO_EXT:
                    final_counters['photo_files'] += 1
                    final_counters['media_files'] += 1
                    final_counters['photos']['total'] += 1
                    media_category = 'photos'
                elif ext in VIDEO_EXT:
                    final_counters['video_files'] += 1
                    final_counters['media_files'] += 1
                    final_counters['videos']['total'] += 1
                    media_category = 'videos'
                if ext in METADATA_EXT:
                    final_counters['metadata_files'] += 1
                if ext in SIDECAR_EXT:
                    final_counters['sidecar_files'] += 1
                if ext in METADATA_EXT or ext in SIDECAR_EXT:
                    final_counters['non_media_files'] += 1

                if media_category:
                    media_file_paths.append(file_path)

            final_counters['total_size_mb'] = round(total_bytes / (1024 * 1024), 1)

            # --- 4) Always split into 10 000-file blocks (only media files)
            block_size = 10_000
            file_blocks = [
                media_file_paths[i: i + block_size]
                for i in range(0, len(media_file_paths), block_size)
            ]
            num_blocks = len(file_blocks)
            LOGGER.info(f"{step_name}Launching {num_blocks} blocks of maximum ~{block_size} files")

            # --- 5) Run blocks in parallel, reporting overall progress
            start_time = time.time()
            completed_blocks = 0
            merged_counters_list = []
            merged_dates = {}

            with TemporaryDirectory() as temp_dir:
                # Number of threads (default, 2 * #cores)
                num_threads = multiprocessing.cpu_count()*2

                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    # enviamos cada bloque al executor
                    future_to_block = {
                        executor.submit(process_block, block, idx, temp_dir, extract_dates, step_name): idx
                        for idx, block in enumerate(file_blocks)
                    }
                    for future in as_completed(future_to_block):
                        block_counters, block_dates = future.result()
                        completed_blocks += 1

                        # Progress report
                        elapsed = time.time() - start_time
                        avg_block_time = elapsed / completed_blocks
                        estimated_total = avg_block_time * num_blocks
                        estimated_remaining = avg_block_time * (num_blocks - completed_blocks)
                        LOGGER.info(f"{step_name}📊 Block {completed_blocks}/{num_blocks} done • Elapsed: {int(elapsed // 60)}m • Estimated Total: {int(estimated_total // 60)}m • Estimated Remaining: {int(estimated_remaining // 60)}m")

                        merged_counters_list.append(block_counters)
                        merged_dates.update(block_dates)

                # Merge JSON outputs if we extracted dates
                if extract_dates:
                    os.makedirs(FOLDERNAME_EXIFTOOL_OUTPUT, exist_ok=True)
                    merge_json_files(temp_dir, os.path.join(FOLDERNAME_EXIFTOOL_OUTPUT, output_file))

            # --- 6) Merge all block counters and compute final percentages
            blocks_merged = merge_counters(merged_counters_list)
            for media_category in ['photos', 'videos']:
                final_counters[media_category]['with_date'] = blocks_merged[media_category]['with_date']
                final_counters[media_category]['without_date'] = blocks_merged[media_category]['without_date']
                total_count = final_counters[media_category]['total']
                if total_count > 0 and extract_dates:
                    with_date = final_counters[media_category]['with_date']
                    final_counters[media_category]['pct_with_date'] = (with_date / total_count) * 100
                    final_counters[media_category]['pct_without_date'] = ((total_count - with_date) / total_count) * 100
                else:
                    final_counters[media_category]['pct_with_date'] = 0
                    final_counters[media_category]['pct_without_date'] = 0

            return final_counters, merged_dates
    
    
    # Call to main() function
    return main()