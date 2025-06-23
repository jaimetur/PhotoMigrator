import json
import multiprocessing
import os
import time
from datetime import datetime
from pathlib import Path
from subprocess import run, DEVNULL
import platform
from tempfile import TemporaryDirectory
from PIL import Image
import subprocess

from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, TIMESTAMP, LOGGER
from Utils.GeneralUtils import timed_subprocess


# ---------------------------------------------------------------------------------------------------------------------------
# FILES STATISTICS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------------------------------------------------------
# COUNT_FILES_PER_TYPE_AND_DATE FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------

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


# ===========================================================================================================================
# NEW VERSION OF COUNT_FILES_PER_TYPE_AND_DATE USING MULTI-THREADS
# ===========================================================================================================================
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
    candidate_tags = [
        'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
        'TrackCreateDate', 'EncodedDate', 'MetadataDate',
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
        for tag in candidate_tags:
            raw_value = entry.get(tag)
            if isinstance(raw_value, str):
                for fmt in date_formats:
                    try:
                        found_dates.append(datetime.strptime(raw_value.strip(), fmt))
                        break
                    except ValueError:
                        continue

        oldest_date = min(found_dates) if found_dates else None
        dates_by_path[file_path] = oldest_date

        if media_category:
            counters[media_category]['total'] += 1
            if oldest_date and oldest_date <= reference_timestamp:
                counters[media_category]['with_date'] += 1
            else:
                counters[media_category]['without_date'] += 1

    counters['total_size_mb'] = round(total_bytes / (1024 * 1024), 1)
    return counters, dates_by_path

# --------------------
# MAIN FUNCTION LOGIC
# --------------------
def count_files_per_type_and_date(input_folder, max_files=None, exclude_ext=None, include_ext=None, output_file="dates_metadata.json", extract_dates=True, step_name='', log_level=None):
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
                        f"Elapsed: {int(elapsed // 60)}m • Remaining: {int(remaining // 60)}m"
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
