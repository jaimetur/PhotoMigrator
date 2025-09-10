import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime

import piexif

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import MSG_TAGS, PHOTO_EXT, LOGGER, VIDEO_EXT, FOLDERNAME_EXIFTOOL, DATE_SEPARATOR, RANGE_OF_DATES_SEPARATOR
from Utils.StandaloneUtils import get_exif_tool_path
from Utils.GeneralUtils import tqdm, get_subfolders_with_exclusions, batch_replace_sourcefiles_in_json


def rename_album_folders(input_folder: str, exclude_subfolder=None, type_date_range='complete', date_dict=None, step_name="", log_level=None):
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

    # quick validity check (coarse but safe for ranges)
    def _is_valid_dt(dt):
        try:
            return dt is not None and 1900 <= dt.year <= 2100
        except Exception:
            return False

    def get_dict_oldest_date(date_dict, image_path, step_name="", log_level=None):
        # English comment: Returns the parsed datetime for 'OldestDate' stored under image_path in date_dict; None if missing or invalid.
        from datetime import datetime

        with set_log_level(LOGGER, log_level):
            try:
                if not isinstance(date_dict, dict):
                    LOGGER.warning(f"{step_name}Invalid date_dict provided (not a dict)")
                    return None

                entry = date_dict.get(image_path)
                if entry is None:
                    LOGGER.debug(f"{step_name}No entry found in date_dict for: {image_path}")
                    return None

                oldest_str = entry.get("OldestDate")
                if not oldest_str:
                    LOGGER.debug(f"{step_name}'OldestDate' not found for: {image_path}")
                    return None

                try:
                    # English comment: Parse ISO-8601 string with timezone if present
                    oldest_dt = datetime.fromisoformat(str(oldest_str))
                    LOGGER.debug(f"{step_name}Parsed OldestDate for '{image_path}': {oldest_dt}")
                    return oldest_dt
                except Exception as pe:
                    LOGGER.warning(f"{step_name}Cannot parse OldestDate for '{image_path}': {oldest_str} ({pe})")
                    return None

            except Exception as e:
                LOGGER.warning(f"{step_name}Unexpected error accessing date_dict for '{image_path}': {e}")
                return None

    def get_exif_oldest_date_using_exiftool(image_path, step_name='', log_level=None):
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.debug(f"{step_name} Executing exiftool for {image_path}")
                exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)

                # --- Try ExifTool path
                if not Path(exif_tool_path).exists():
                    LOGGER.warning(f"{step_name}⚠️ Exiftool not found at '{exif_tool_path}'.")
                    return None

                # OS filename charset
                filename_charset = 'cp1252' if platform.system() == 'Windows' else 'utf8'

                # Local TZ for naive datetimes
                local_tz = datetime.now().astimezone().tzinfo

                candidate_tags = [
                    # 📷 EXIF (fotos)
                    'EXIF:DateTimeOriginal', 'EXIF:DateTime', 'EXIF:CreateDate', 'EXIF:DateCreated', 'EXIF:CreationDate',
                    'EXIF:MediaCreateDate', 'EXIF:TrackCreateDate', 'EXIF:EncodedDate', 'EXIF:MetadataDate', 'EXIF:ModifyDate',

                    # 📝 XMP
                    'XMP:DateTimeOriginal', 'XMP:DateTime', 'XMP:CreateDate', 'XMP:DateCreated', 'XMP:CreationDate',
                    'XMP:MediaCreateDate', 'XMP:TrackCreateDate', 'XMP:EncodedDate', 'XMP:MetadataDate', 'XMP:ModifyDate',

                    # 🎬 QuickTime / MP4 / MOV
                    'QuickTime:CreateDate', 'QuickTime:ModifyDate', 'QuickTime:TrackCreateDate', 'QuickTime:TrackModifyDate',
                    'QuickTime:MediaCreateDate', 'QuickTime:MediaModifyDate',

                    # 🎞️ Track/Media (otros contenedores ISO BMFF)
                    'Track:CreateDate', 'Track:ModifyDate', 'Media:CreateDate', 'Media:ModifyDate',

                    # 🎥 Matroska / MKV
                    'Matroska:DateUTC',

                    # 📼 AVI
                    'RIFF:DateTimeOriginal',

                    # 🛠️ File (solo referencia; no se considera “contenido”)
                    'File:FileModifyDate'
                ]

                exiftool_tag_args = [f"-{t}" for t in candidate_tags]

                command = [
                    exif_tool_path,
                    image_path,
                    '-charset', f'filename={filename_charset}',
                    '-charset', 'exif=utf8',
                    '-j', '-n', '-s',
                    '-G0',  # family-0 group names → EXIF:*, XMP:*, QuickTime:*, File:*
                    '-m', '-q', '-q',
                    '-api', 'largefilesupport=1',
                    '-fast',
                    *exiftool_tag_args,
                ]

                result = subprocess.check_output(command, stderr=subprocess.STDOUT)
                metadata = json.loads(result)[0]

                # result = subprocess.check_output([
                #     f"{exif_tool_path}",
                #     "-j", "-n", "-time:all", "-fast", "-fast2", "-s",
                #     image_path
                # ], stderr=subprocess.STDOUT)
                # metadata = json.loads(result)[0]

                # Parsers and helpers
                date_formats = [
                    "%Y:%m:%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z",
                    "%Y:%m:%d %H:%M:%SZ", "%Y-%m-%d %H:%M:%SZ",
                    "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y:%m:%d %H:%M%z", "%Y:%m:%d %H:%M",
                    "%Y:%m:%d", "%Y-%m-%d"
                ]

                def parse_any(raw_text):
                    """Try multiple formats; return tz-aware (local tz for naive)."""
                    txt = str(raw_text).strip()
                    # normalize +HH:MM -> +HHMM for %z
                    try:
                        txt = re.sub(r'([+\-]\d{2}):(\d{2})$', r'\1\2', txt)
                    except Exception:
                        pass
                    # handle trailing 'Z' for UTC with %z alt
                    for fmt in date_formats:
                        try:
                            dt = datetime.strptime(txt, fmt)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=local_tz)
                            return dt
                        except ValueError:
                            continue
                    return None

                exiftool_candidates = []  # (dt, tag, has_time)
                for tag in candidate_tags:
                    if tag == 'File:FileModifyDate':
                        continue  # not a content date
                    raw_value = metadata.get(tag)
                    if not raw_value:
                        continue
                    dt = parse_any(raw_value)
                    if not dt:
                        continue
                    has_time = not (dt.hour == 0 and dt.minute == 0 and dt.second == 0)
                    exiftool_candidates.append((dt, tag, has_time))
                    LOGGER.debug(f"{step_name} Parsed {dt} from tag {tag}")

                if not exiftool_candidates:
                    LOGGER.debug(f"{step_name} No EXIF/XMP/video dates found")
                    return None

                # --- Selection with global EXIF priority over XMP (even if XMP is older)
                exif_only = [c for c in exiftool_candidates if c[1].startswith('EXIF:')]
                pool = exif_only if exif_only else exiftool_candidates

                # Oldest calendar day within the chosen pool
                min_day = min(c[0].date() for c in pool)
                same_day = [c for c in pool if c[0].date() == min_day]

                # Prefer entries with real time (not midnight), then earliest time on that day
                chosen_dt, chosen_tag, chosen_has_time = min(
                    same_day,
                    key=lambda c: (0 if c[2] else 1, c[0])
                )

                LOGGER.debug(f"{step_name} Oldest (with EXIF priority & time-aware): {chosen_dt} from {chosen_tag}")
                return chosen_dt

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

                # Candidate EXIF date tags (ExifIFD) + ImageIFD.DateTime
                candidate_piexif_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'ModifyDate']
                date_formats = [
                    "%Y:%m:%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z",
                    "%Y:%m:%d %H:%M:%SZ", "%Y-%m-%d %H:%M:%SZ",
                    "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y:%m:%d %H:%M%z", "%Y:%m:%d %H:%M",
                    "%Y:%m:%d", "%Y-%m-%d"
                ]
                local_tz = datetime.now().astimezone().tzinfo

                def parse_any(raw_text):
                    """Parse EXIF-like string; return tz-aware (local tz for naive)."""
                    if raw_text is None:
                        return None
                    txt = str(raw_text).strip()

                    # Handle '... 24:xx:xx' → next day at 00:xx:xx
                    try:
                        parts = txt.split(' ', 1)
                        if len(parts) == 2 and parts[1].startswith('24:'):
                            base_dt = datetime.strptime(parts[0], "%Y:%m:%d")
                            rolled = base_dt + timedelta(days=1)
                            txt = rolled.strftime("%Y:%m:%d") + " 00" + parts[1][2:]
                    except Exception:
                        pass

                    # Normalize timezone "+HH:MM" → "+HHMM" for %z parsing
                    try:
                        txt = re.sub(r'([+\-]\d{2}):(\d{2})$', r'\1\2', txt)
                    except Exception:
                        pass

                    for fmt in date_formats:
                        try:
                            dt = datetime.strptime(txt, fmt)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=local_tz)
                            return dt
                        except ValueError:
                            continue
                    return None

                # Collect candidates as (dt, tag_key, has_time)
                candidates = []

                # From ExifIFD
                exif_ifd = exif_dict.get("Exif", {}) or {}
                for tag in candidate_piexif_tags:
                    tag_id = piexif.ExifIFD.__dict__.get(tag)
                    if tag_id is None:
                        continue
                    raw_value = exif_ifd.get(tag_id)
                    if not raw_value:
                        continue
                    raw_str = raw_value.decode('utf-8', errors='ignore') if isinstance(raw_value, (bytes, bytearray)) else raw_value
                    dt = parse_any(raw_str)
                    if not dt:
                        continue
                    has_time = not (dt.hour == 0 and dt.minute == 0 and dt.second == 0)
                    candidates.append((dt, f"EXIF:{tag}", has_time))
                    LOGGER.debug(f"{step_name} Parsed {dt} from tag EXIF:{tag}")

                # Also check ImageIFD.DateTime ("DateTime")
                try:
                    raw_dt0 = (exif_dict.get("0th", {}) or {}).get(piexif.ImageIFD.DateTime)
                    if raw_dt0:
                        raw_str0 = raw_dt0.decode('utf-8', errors='ignore') if isinstance(raw_dt0, (bytes, bytearray)) else raw_dt0
                        dt0 = parse_any(raw_str0)
                        if dt0:
                            has_time0 = not (dt0.hour == 0 and dt0.minute == 0 and dt0.second == 0)
                            candidates.append((dt0, "EXIF:DateTime", has_time0))
                            LOGGER.debug(f"{step_name} Parsed {dt0} from tag EXIF:DateTime")
                except Exception:
                    pass  # keep silent; optional path

                if not candidates:
                    LOGGER.debug(f"{step_name} No EXIF dates found")
                    return None

                # Selection: choose the oldest calendar day; within that day prefer real time, then earliest time
                min_day = min(c[0].date() for c in candidates)
                same_day = [c for c in candidates if c[0].date() == min_day]
                chosen_dt, chosen_tag, chosen_has_time = min(same_day, key=lambda c: (0 if c[2] else 1, c[0]))

                LOGGER.debug(f"{step_name} Oldest EXIF date (time-aware): {chosen_dt} from {chosen_tag}")
                return chosen_dt

            except Exception as e:
                LOGGER.debug(f"{step_name} Error retrieving EXIF date: {e}")
                return None

    def get_content_based_year_range(folder: str, exif_search=False, date_dict=None, log_level=logging.INFO) -> str:
        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                years = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in PHOTO_EXT + VIDEO_EXT:
                        # Compute the best 'oldest_date' per file using the following priority:
                        # 1) date_dict, 2) EXIF native (piexif), 3) EXIF exiftool, 4) filesystem ctime, 5) filesystem mtime.
                        chosen_date = None

                        # 1) Try dictionary (already-extracted oldest date)
                        if date_dict is not None:
                            try:
                                dict_date = get_dict_oldest_date(date_dict, f, step_name=step_name)
                                if _is_valid_dt(dict_date):
                                    chosen_date = dict_date
                                    LOGGER.verbose(f"{step_name}Using date_dict for '{f}': {dict_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}date_dict lookup failed for '{f}': {e}")

                        # 2) Try EXIF native (piexif) if exif_search is enabled
                        if chosen_date is None and exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_piexif(f, step_name=step_name)
                                if _is_valid_dt(exif_date):
                                    chosen_date = exif_date
                                    LOGGER.verbose(f"{step_name}Using EXIF (native) for '{f}': {exif_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Error reading EXIF (native) from {f}: {e}")

                        # Try EXIF via exiftool if still missing and exif_search is enabled
                        if chosen_date is None and exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_exiftool(f, step_name=step_name)
                                if _is_valid_dt(exif_date):
                                    chosen_date = exif_date
                                    LOGGER.verbose(f"{step_name}Using EXIF (exiftool) for '{f}': {exif_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}ExifTool EXIF failed for '{f}': {e}")

                        # 4) Fallback to filesystem creation time (ctime)
                        if chosen_date is None:
                            try:
                                ts_ctime = os.path.getctime(f)
                                if ts_ctime and ts_ctime > 0:
                                    ctime_date = datetime.fromtimestamp(ts_ctime)
                                    if _is_valid_dt(ctime_date):
                                        chosen_date = ctime_date
                                        LOGGER.verbose(f"{step_name}Using filesystem ctime for '{f}': {ctime_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Cannot read filesystem ctime for '{f}': {e}")

                        # 5) Fallback to modification time(mtime)
                        if chosen_date is None:
                            try:
                                ts_mtime = os.path.getmtime(f)
                                if ts_mtime and ts_mtime > 0:
                                    mtime_date = datetime.fromtimestamp(ts_mtime)
                                    if _is_valid_dt(mtime_date):
                                        chosen_date = mtime_date
                                        LOGGER.verbose(f"{step_name}Using filesystem mtime for '{f}': {mtime_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Cannot read filesystem mtime from {f}: {e}")

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
                    return f"{oldest_year}{RANGE_OF_DATES_SEPARATOR}{latest_year}"
            except Exception as e:
                LOGGER.error(f"{step_name}Error obtaining year range: {e}")
            return False

    def get_content_based_date_range(folder: str, exif_search=False, date_dict=None, log_level=logging.INFO) -> str:
        with set_log_level(LOGGER, log_level):
            try:
                files = [os.path.join(folder, f) for f in os.listdir(folder)]
                files = [f for f in files if os.path.isfile(f)]
                dates = []
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in PHOTO_EXT + VIDEO_EXT:
                        # Compute the best 'oldest_date' per file using the following priority:
                        # 1) date_dict, 2) EXIF native (piexif), 3) EXIF exiftool, 4) filesystem ctime, 5) filesystem mtime.
                        chosen_date = None

                        # 1) Try dictionary (already-extracted oldest date)
                        if date_dict is not None:
                            try:
                                dict_date = get_dict_oldest_date(date_dict, f, step_name=step_name)
                                if _is_valid_dt(dict_date):
                                    chosen_date = dict_date
                                    LOGGER.verbose(f"{step_name}Using date_dict for '{f}': {dict_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}date_dict lookup failed for '{f}': {e}")

                        # 2) Try EXIF native (piexif)
                        if chosen_date is None and exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_piexif(f, step_name=step_name)
                                if _is_valid_dt(exif_date):
                                    chosen_date = exif_date
                                    LOGGER.verbose(f"{step_name}Using EXIF (native) for '{f}': {exif_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Error reading EXIF from {f}: {e}")

                        # 3) Try EXIF via exiftool
                        if chosen_date is None and exif_search:
                            try:
                                exif_date = get_exif_oldest_date_using_exiftool(f, step_name=step_name)
                                if _is_valid_dt(exif_date):
                                    chosen_date = exif_date
                                    LOGGER.verbose(f"{step_name}Using EXIF (exiftool) for '{f}': {exif_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}ExifTool EXIF failed for '{f}': {e}")

                        # 4) Fallback to filesystem creation time (ctime)
                        if chosen_date is None:
                            try:
                                ts_ctime = os.path.getctime(f)
                                if ts_ctime and ts_ctime > 0:
                                    ctime_date = datetime.fromtimestamp(ts_ctime)
                                    if _is_valid_dt(ctime_date):
                                        chosen_date = ctime_date
                                        LOGGER.verbose(f"{step_name}Using filesystem ctime for '{f}': {ctime_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Cannot read filesystem ctime for '{f}': {e}")

                        # 5) Fallback to filesystem modification time (mtime)
                        if chosen_date is None:
                            try:
                                ts_mtime = os.path.getmtime(f)
                                if ts_mtime and ts_mtime > 0:
                                    fs_date = datetime.fromtimestamp(ts_mtime)
                                    if _is_valid_dt(fs_date):
                                        chosen_date = fs_date
                                        LOGGER.verbose(f"{step_name}Using filesystem mtime for '{f}': {fs_date}")
                            except Exception as e:
                                LOGGER.verbose(f"{step_name}Cannot read timestamp from {f}: {e}")

                        # push the decided date if any
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
                    return f"{dt.year:04}{DATE_SEPARATOR}{dt.month:02}{DATE_SEPARATOR}{dt.day:02}"
                elif len(months) == 1:
                    y, m = next(iter(months))
                    return f"{y:04}{DATE_SEPARATOR}{m:02}"
                elif len(years) == 1:
                    sorted_months = sorted(months)
                    start = f"{sorted_months[0][0]:04}{DATE_SEPARATOR}{sorted_months[0][1]:02}"
                    end = f"{sorted_months[-1][0]:04}{DATE_SEPARATOR}{sorted_months[-1][1]:02}"
                    return f"{start}{RANGE_OF_DATES_SEPARATOR}{end}"
                else:
                    return f"{min(years):04}{RANGE_OF_DATES_SEPARATOR}{max(years):04}"
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
        replacements = []

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
                        content_based_date_range = get_content_based_date_range(item_path, exif_search=True, date_dict=date_dict)
                    elif type_date_range.lower() == 'year':
                        content_based_date_range = get_content_based_year_range(item_path, exif_search=True, date_dict=date_dict)
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
                    replacements.append((item_path, new_folder_path))

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
            'replacements': replacements,
        }
