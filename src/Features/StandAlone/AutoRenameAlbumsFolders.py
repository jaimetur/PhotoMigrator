import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime

import piexif

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import MSG_TAGS, PHOTO_EXT, LOGGER, VIDEO_EXT
from Utils.GeneralUtils import tqdm, get_subfolders_with_exclusions


def rename_album_folders(input_folder: str, exclude_subfolder=None, type_date_range='complete', step_name="", log_level=None):
    # ===========================
    # AUXILIARY FUNCTIONS
    # ===========================
    def clean_name_and_remove_dates(input_string: str, log_level=logging.INFO) -> dict:
        """
        Removes date or date range prefixes from the input string and returns a dictionary
        with the cleaned name and the extracted date(s).

        Returns:
            dict: {
                "clean-name": str,  # The input string with the date(s) removed
                "dates": str        # The removed date(s) prefix, or empty string if none found
            }
        """
        import re
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
            # Patrón para detectar fecha o rango de fechas al inicio del string
            pattern = re.compile(
                r"""^                   # inicio del string
                (                                           # ← aquí empieza grupo 1
                    (?:19|20)\d{2}                          # yyyy (año)
                    (?:[._-](?:0[1-9]|1[0-2]))?             # opcional: .mm o -mm o _mm (mes precedido de '.', '-' o '_')
                    (?:[._-](?:0[1-9]|[12]\d|3[01]))?       # opcional: .dd o -dd o _dd (día precedido de '.', '-' o '_')
                    (?:\s*[-_]\s*                           # comienzo de rango opcional (comienza al detectar el separador del rango)
                        (?:19|20)\d{2}                      # yyyy (año) dentro del rango opcional
                        (?:[._-](?:0[1-9]|1[0-2]))?         # opcional dentro del rango opcional: .mm o -mm o _mm (mes precedido de '.', '-' o '_')
                        (?:[._-](?:0[1-9]|[12]\d|3[01]))?   # opcional dentro del rango opcional: .dd o -dd o _dd (día precedido de '.', '-' o '_')
                    )?                                      # fin rango opcional
                )                                           # ← aquí termina grupo 1                 
                \s*[-_]\s*                                  # separador tras la fecha o rango (FUERA de grupo 1)               
                """,
                flags=re.VERBOSE
            )
            match = pattern.match(input_string)
            original_dates = match.group(1) if match else ""
            clean_name = input_string[match.end():] if match else input_string
            return {
                "clean-name": clean_name,
                "original-dates": original_dates
            }

    def get_exif_oldest_date_using_exiftool(image_path, step_name='', log_level=None):
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.debug(f"{step_name} Executing exiftool for {image_path}")
                # Llama a exiftool con todos los flags recomendados
                result = subprocess.check_output([
                    "./gpth_tool/exif_tool/exiftool",
                    "-j", "-n", "-time:all", "-fast", "-fast2", "-s",
                    image_path
                ], stderr=subprocess.STDOUT)
                metadata = json.loads(result)[0]

                candidate_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
                                  'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate']
                date_formats = ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%d"]
                found_dates = []

                for tag in candidate_tags:
                    raw_value = metadata.get(tag)
                    if not raw_value:
                        continue  # No value for this tag
                    for fmt in date_formats:
                        try:
                            parsed = datetime.strptime(str(raw_value).strip(), fmt)
                            found_dates.append(parsed)
                            LOGGER.debug(f"{step_name} Parsed {parsed} from tag {tag}")
                            break
                        except ValueError:
                            continue

                if found_dates:
                    oldest = min(found_dates)
                    LOGGER.debug(f"{step_name} Oldest EXIF date: {oldest}")
                    return oldest

                LOGGER.debug(f"{step_name} No EXIF dates found")
                return None

            except subprocess.CalledProcessError as e:
                LOGGER.debug(f"{step_name} exiftool error: {e.output.decode(errors='ignore')}")
                return None
            except Exception as e:
                LOGGER.debug(f"{step_name} Unexpected error retrieving EXIF date: {e}")
                return None

    def get_exif_oldest_date_using_piexif(image_path, step_name='', log_level=None):
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.debug(f"{step_name} Loading EXIF from {image_path}")
                exif_dict = piexif.load(image_path)
                # Candidate EXIF date tags
                candidate_date_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate']
                # Supported date formats
                date_formats = ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%d"]
                found_dates = []
                for tag in candidate_date_tags:
                    tag_id = piexif.ExifIFD.__dict__.get(tag)
                    if tag_id is None:
                        continue  # Tag not defined in ExifIFD
                    raw_value = exif_dict.get("Exif", {}).get(tag_id)
                    if not raw_value:
                        continue  # No value for this tag
                    # Normalize raw_value to string if it's bytes
                    raw_str = raw_value.decode('utf-8', errors='ignore') if isinstance(raw_value, (bytes, bytearray)) else raw_value
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(raw_str.strip(), fmt)
                            found_dates.append(parsed_date)
                            LOGGER.debug(f"{step_name} Parsed {parsed_date} from tag {tag}")
                            break
                        except ValueError:
                            continue
                if found_dates:
                    oldest = min(found_dates)
                    LOGGER.debug(f"{step_name} Oldest EXIF date: {oldest}")
                    return oldest
                LOGGER.debug(f"{step_name} No EXIF dates found")
                return None
            except Exception as e:
                LOGGER.debug(f"{step_name} Error retrieving EXIF date: {e}")
                return None

    def get_content_based_year_range(folder: str, exif_search=False, log_level=logging.INFO) -> str:
        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                years = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    exif_date = None
                    fs_date = None
                    if ext in PHOTO_EXT+VIDEO_EXT:
                        # Intenta obtener EXIF
                        if exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_piexif(f, step_name=step_name)
                                # exif_date = get_exif_oldest_date_using_exiftool(f, step_name=step_name)
                            except Exception as e:
                                LOGGER.warning(f"{step_name}Error reading EXIF from {f}: {e}")
                        # Intenta obtener mtime
                        try:
                            ts = os.path.getmtime(f)
                            if ts > 0:
                                fs_date = datetime.fromtimestamp(ts)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Cannot read timestamp from {f}: {e}")
                    # Elige la fecha más antigua entre EXIF y mtime
                    chosen_date = None
                    if exif_date and fs_date:
                        chosen_date = min(exif_date, fs_date)
                    else:
                        chosen_date = exif_date or fs_date
                    if chosen_date:
                        years.append(chosen_date.year)
                if not years:
                    LOGGER.warning(f"{step_name}No valid timestamps found in {folder}")
                    return False
                # Extraer componentes
                oldest_year = min(years)
                latest_year = max(years)
                if oldest_year == latest_year:
                    return str(oldest_year)
                else:
                    return f"{oldest_year}-{latest_year}"
            except Exception as e:
                LOGGER.error(f"{step_name}Error obtaining year range: {e}")
            return False

    def get_content_based_date_range(folder: str, exif_search=False, log_level=logging.INFO) -> str:
        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                dates = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    exif_date = None
                    fs_date = None
                    if ext in PHOTO_EXT+VIDEO_EXT:
                        # Intenta obtener EXIF
                        if exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_piexif(f, step_name=step_name)
                                # exif_date = get_exif_oldest_date_using_exiftool(f, step_name=step_name)
                            except Exception as e:
                                LOGGER.warning(f"{step_name}Error reading EXIF from {f}: {e}")
                        # Intenta obtener mtime
                        try:
                            ts = os.path.getmtime(f)
                            if ts > 0:
                                fs_date = datetime.fromtimestamp(ts)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Cannot read timestamp from {f}: {e}")
                        # Escoger la fecha más antigua disponible
                        chosen_date = None
                        if exif_date and fs_date:
                            chosen_date = min(exif_date, fs_date)
                        else:
                            chosen_date = exif_date or fs_date
                        if chosen_date:
                            dates.append(chosen_date)
                if not dates:
                    LOGGER.warning(f"{step_name}No valid timestamps found in {folder}")
                    return False
                # Extraer componentes
                years = {dt.year for dt in dates}
                months = {(dt.year, dt.month) for dt in dates}
                days = {(dt.year, dt.month, dt.day) for dt in dates}
                if len(days) == 1:
                    dt = dates[0]
                    return f"{dt.year:04}.{dt.month:02}.{dt.day:02}"
                elif len(months) == 1:
                    y, m = next(iter(months))
                    return f"{y:04}.{m:02}"
                elif len(years) == 1:
                    sorted_months = sorted(months)
                    start = f"{sorted_months[0][0]:04}.{sorted_months[0][1]:02}"
                    end = f"{sorted_months[-1][0]:04}.{sorted_months[-1][1]:02}"
                    return f"{start}-{end}"
                else:
                    return f"{min(years):04}-{max(years):04}"
            except Exception as e:
                LOGGER.error(f"{step_name}Error obtaining date range: {e}")
                return False

    # ===========================
    # END AUX FUNCTIONS
    # ===========================
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Initial template for rename results
        renamed_album_folders = 0
        duplicates_album_folders = 0
        duplicates_albums_fully_merged = 0
        duplicates_albums_not_fully_merged = 0
        verbose_messages = []
        debug_messages = []
        info_messages = []
        warning_messages = []

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]

        total_folders = get_subfolders_with_exclusions(input_folder, exclude_subfolder)

        for original_folder_name in tqdm(total_folders, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Renaming Albums folders in '<OUTPUT_TAKEOUT_FOLDER>'", unit=" folders"):
            item_path = os.path.join(input_folder, original_folder_name)
            if os.path.isdir(item_path):
                resultado = clean_name_and_remove_dates(original_folder_name)
                cleaned_folder_name = resultado["clean-name"]
                original_dates = resultado["original-dates"]
                # If folder name does not start with a year (19xx or 20xx)
                if not re.match(r'^(19|20)\d{2}', cleaned_folder_name):
                    # Determine the date prefix depending on the argument type_date_range: year:2022-2024 or complete: 2022.06-2024-01
                    if type_date_range.lower() == 'complete':
                        content_based_date_range = get_content_based_date_range(item_path)
                    elif type_date_range.lower() == 'year':
                        content_based_date_range = get_content_based_year_range(item_path)
                    else:
                        warning_messages.append(f"{step_name}No valid type_date_range: '{type_date_range}'")
                    # if not possible to find a date_raange, keep the original_dates (if exits) as prefix of the cleaned_folder_name
                    if content_based_date_range:
                        cleaned_folder_name = f"{content_based_date_range} - {cleaned_folder_name}"
                        verbose_messages.append(f"Added date prefix '{content_based_date_range}' to folder: '{os.path.basename(cleaned_folder_name)}'")
                    else:
                        if original_dates:
                            cleaned_folder_name = f"{original_dates} - {cleaned_folder_name}"
                            verbose_messages.append(f"Keep date prefix '{original_dates}' in folder: '{os.path.basename(cleaned_folder_name)}'")
                        else:
                            cleaned_folder_name = f"{cleaned_folder_name}"
                            verbose_messages.append(f"No date prefix found in folder: '{os.path.basename(cleaned_folder_name)}'")

                # Skip renaming if the clean name is the same as the original
                if cleaned_folder_name != original_folder_name:
                    new_folder_path = os.path.join(input_folder, cleaned_folder_name)
                    if os.path.exists(new_folder_path):
                        duplicates_album_folders += 1
                        warning_messages.append(f"{step_name}Folder '{new_folder_path}' already exists. Merging contents...")
                        for item in os.listdir(item_path):
                            src = os.path.join(item_path, item)
                            dst = os.path.join(new_folder_path, item)
                            if os.path.exists(dst):
                                # Compare file sizes to decide if the original should be deleted
                                if os.path.isfile(dst) and os.path.getsize(src) == os.path.getsize(dst):
                                    os.remove(src)
                                    debug_messages.append(f"{step_name}Deleted duplicate file: '{src}'")
                            else:
                                shutil.move(src, dst)
                                debug_messages.append(f"{step_name}Moved '{src}' → '{dst}'")
                        # Check if the folder is empty before removing it
                        if not os.listdir(item_path):
                            os.rmdir(item_path)
                            debug_messages.append(f"{step_name}Removed empty folder: '{item_path}'")
                            duplicates_albums_fully_merged += 1
                        else:
                            # LOGGER.warning(f"Folder not empty, skipping removal: {item_path}")
                            duplicates_albums_not_fully_merged += 1
                    else:
                        if item_path != new_folder_path:
                            os.rename(item_path, new_folder_path)
                            debug_messages.append(f"{step_name}Renamed folder: '{os.path.basename(item_path)}' → '{os.path.basename(new_folder_path)}'")
                            renamed_album_folders += 1

        # Finally we log all the messages captured during the process
        for verbose_message in verbose_messages:
            LOGGER.verbose(verbose_message)
        for debug_message in debug_messages:
            LOGGER.debug(debug_message)
        for info_message in info_messages:
            LOGGER.info(info_message)
        for warning_message in warning_messages:
            LOGGER.warning(warning_message)

        return {
            'renamed_album_folders': renamed_album_folders,
            'duplicates_album_folders': duplicates_album_folders,
            'duplicates_albums_fully_merged': duplicates_albums_fully_merged,
            'duplicates_albums_not_fully_merged': duplicates_albums_not_fully_merged,
        }
