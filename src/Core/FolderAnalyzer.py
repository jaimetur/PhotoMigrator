# ========================
# 📦 IMPORTS
# ========================
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from pathlib import Path
from datetime import datetime, timezone
from subprocess import run
import logging
import platform

from PIL import Image, ExifTags
from dateutil import parser
import time
from Utils.GeneralUtils import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from Core.GlobalFunctions import set_LOGGER
from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import TIMESTAMP, FOLDERNAME_EXIFTOOL, LOGGER, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, FOLDERNAME_EXTRACTED_DATES, MSG_TAGS
from Utils.DateUtils import normalize_datetime_utc, is_date_valid, guess_date_from_filename
from Utils.GeneralUtils import print_dict_pretty
from Utils.StandaloneUtils import get_exif_tool_path, custom_print, change_working_dir

# ========================
# 📂 FolderAnalyzer CLASS
# ========================
class FolderAnalyzer:
    def __init__(self, folder_path=None, metadata_json_file=None, extracted_dates=None, force_date_extraction=True, logger=None, step_name='', filter_ext=None, filter_from_epoch=None, filter_to_epoch=None, log_level=None):
    # def __init__(self, folder_path=None, extracted_dates=None, logger=None, step_name=''):
        """
        Initialize the FolderAnalyzer from a given folder or existing extracted_dates.
        If folder_path is provided, walk through all files.
        """
        self.folder_path = Path(folder_path).resolve().as_posix() if folder_path else None
        self.metadata_json_file = metadata_json_file

        # Main attributes of the Class to store file_list, filtered_file_list and extracted_dates
        self.file_list = []                                     # all files (no filter)
        self.filtered_file_list = []                            # files after applying filters
        self.extracted_dates = extracted_dates or {}            # extracted_dates dict

        # Store per-file sizes and aggregated folder sizes
        self.file_sizes = {}                                    # map file_path -> size of each file
        self.folder_sizes = {}                                  # map folder_path -> size of filtered files
        self.folder_assets = {}                                 # map folder_path -> count of filtered files

        # New fields: filtering criteria
        self.filter_ext = filter_ext  # set of extensions or None
        self.filter_from_epoch = filter_from_epoch or 0  # start timestamp or 0
        self.filter_to_epoch = filter_to_epoch or float('inf')  # end timestamp or float('inf')

        if logger:
            self.logger = logger
        else:
            self.logger = set_LOGGER()

        # 3 different ways to build initialize the Constructor:
        # 1) if extracted_dates dictionary is given
        if self.extracted_dates and isinstance(self.extracted_dates, dict):
            self._build_file_list_from_extracted_dates(step_name=step_name)
            self._apply_filters(step_name=step_name, log_level=log_level)
        # 2) if metadata_json_file is given
        elif self.metadata_json_file:
            self.load_from_json(input_file=self.metadata_json_file, step_name=step_name)
            self._build_file_list_from_extracted_dates(step_name=step_name)
            self._apply_filters(step_name=step_name, log_level=log_level)
        # 3) if folder_path is given
        elif self.folder_path:
            self._build_file_list_from_disk(step_name=step_name)
            if not self.extracted_dates and force_date_extraction:
                self.extract_dates(step_name=step_name)
            self._apply_filters(step_name=step_name, log_level=log_level)

        # finally compute folder sizes based on filtered_file_list (if any) or full file_list
        self._compute_folder_sizes(step_name)

    def _build_file_list_from_disk(self, step_name='', log_level=None):
        with set_log_level(self.logger, log_level):
            # Gather all file paths under folder_path
            if not os.path.isdir(self.folder_path):
                LOGGER.warning(f"{step_name}❌ Folder does not exist: {self.folder_path}")
                return
            # Build raw list of files (no filtering)
            self.file_list = [
                (Path(root) / name).as_posix()
                for root, _, files in os.walk(self.folder_path, followlinks=True)
                for name in files
            ]
            LOGGER.info(f"{step_name}Built file_list from disk: {len(self.file_list)} files.")

    def _build_file_list_from_extracted_dates(self, step_name='', log_level=None):
        with set_log_level(self.logger, log_level):
            # English: rebuild file_list from existing extracted_dates keys
            self.file_list = list(self.extracted_dates.keys())
            LOGGER.debug(f"{step_name}Built file_list from extracted_dates: {len(self.file_list)} entries.")

    def _apply_filters(self, step_name='', log_level=None):
        """
        Apply filtering criteria to self.file_list and optional self.extracted_dates,
        populating filtered_file_list and folder_assets.
        """
        with set_log_level(self.logger, log_level):
            # reset filtered lists and counts
            self.filtered_file_list = []
            self.folder_assets = {}

            no_filters = (
                    not self.filter_ext
                    and self.filter_from_epoch == 0
                    and self.filter_to_epoch == float('inf')
            )
            if no_filters:
                # include everything
                for p in self.file_list:
                    self.filtered_file_list.append(p)
                    parent = Path(p).parent.resolve().as_posix()
                    self.folder_assets[parent] = self.folder_assets.get(parent, 0) + 1
                self.logger.info(f"{step_name}✅ No filters applied to Analyzer Object: {len(self.filtered_file_list)} files, {len(self.folder_assets)} folders.")
                return

            # otherwise, apply ext + date filters
            self.logger.info(f"{step_name}🔍 Applying filters to Analyzer Object. This may take some time. Please be patient...")
            for p in self.file_list:
                file = Path(p)
                ext = file.suffix.lower()

                # extension filter
                if self.filter_ext:
                    if self.filter_ext == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in self.filter_ext:
                        continue

                # date filter
                date_val = self.get_date(p, step_name)
                if date_val is None:
                    continue
                ts = date_val.timestamp()
                if ts < self.filter_from_epoch or ts > self.filter_to_epoch:
                    continue

                # keep it
                self.filtered_file_list.append(p)
                parent = file.parent.resolve().as_posix()
                self.folder_assets[parent] = self.folder_assets.get(parent, 0) + 1

            self.logger.info(f"{step_name}✅ Analyzer Object Filtered to {len(self.filtered_file_list)} files; {len(self.folder_assets)} folders.")

    def _compute_folder_sizes(self, step_name='', log_level=None):
        """
        Compute per-file and per-folder byte sizes, based on the filtered file list.
        If self.filtered_file_list is populated, only those files are considered;
        otherwise falls back to self.file_list.
        """
        with set_log_level(self.logger, log_level):
            # decide which list to size
            source_list = self.filtered_file_list if hasattr(self, 'filtered_file_list') and self.filtered_file_list else self.file_list

            # reset previous size maps
            self.file_sizes = {}
            self.folder_sizes = {}

            for file_path in source_list:
                file = Path(file_path)

                # skip files that no longer exist
                if not file.exists():
                    LOGGER.debug(f"{step_name}Skipping missing file: {file_path}")
                    continue

                try:
                    size = file.stat().st_size
                except Exception as e:
                    LOGGER.warning(f"{step_name}Could not get size for {file_path}: {e}")
                    continue

                # store individual file size
                self.file_sizes[file_path] = size

                # accumulate into its parent folder
                parent = file.parent.resolve().as_posix()
                self.folder_sizes[parent] = self.folder_sizes.get(parent, 0) + size

            LOGGER.info(f"{step_name}🧮 Computed sizes for {len(self.file_sizes)} files and {len(self.folder_sizes)} folders.")

    def get_extracted_dates(self):
        """
        Return the full dictionary of extracted date metadata for all files.

        Returns:
            dict: A dictionary where each key is a file path (TargetFile) and each value
                  is a dictionary containing metadata such as OldestDate and Source.
        """
        return self.extracted_dates

    def get_attribute(self, file_path, attr="OldestDate", step_name=""):
        """
        Return one or more attributes from extracted_dates by TargetFile.
        """
        path = Path(file_path).resolve().as_posix()
        item = self.extracted_dates.get(path)
        if not item:
            self.logger.debug(f"{step_name}No se encontró '{file_path}' en los datos.")
            return None

        if isinstance(attr, list):
            result = {key: item.get(key) for key in attr}
        else:
            result = item.get(attr)

        self.logger.debug(f"{step_name}Atributo(s) '{attr}' para '{file_path}': {result}")
        return result

    def get_date(self, file_path, step_name=""):
        """
        Return the OldestDate as a datetime object for the given file.
        If the stored value is a string, it will be parsed.
        If the value is missing or invalid, returns None.
        """
        raw_date = self.get_attribute(file_path, attr="OldestDate", step_name=step_name)
        if isinstance(raw_date, datetime):
            return raw_date
        if isinstance(raw_date, str) and raw_date.strip():
            try:
                return parser.parse(raw_date.strip())
            except Exception as e:
                self.logger.warning(f"{step_name}⚠️ Could not parse OldestDate for {file_path}: {e}")
        return None

    def get_date_as_str(self, file_path, step_name=""):
        """
        Return only the OldestDate for the given file.
        """
        return self.get_attribute(file_path, attr="OldestDate", step_name=step_name)

    def update_target_file(self, current_path, new_target_path, step_name=""):
        """
        Update the TargetFile of a single file after moving/renaming.
        """
        current_path = Path(current_path).resolve().as_posix()
        new_target_path = Path(new_target_path).resolve().as_posix()

        # Elimina la ruta antigua de si existía
        item = self.extracted_dates.pop(current_path, None)
        if not item:
            self.logger.warning(f"{step_name}No se encontró el archivo por '{current_path}'")
            return False

        # Asigna el nuevo TargetFile como índice
        item["TargetFile"] = new_target_path
        self.extracted_dates[new_target_path] = item

        self.logger.info(f"{step_name}TargetFile actualizado: {current_path} → {new_target_path}")
        return True

    def update_folder(self, old_folder, new_folder, apply_filters=True, compute_folder_size=True, step_name="", log_level=None):
        """
        Bulk-update all entries whose key or TargetFile/SourceFile starts with old_folder,
        replacing that prefix with new_folder, and then refresh all dependent attributes.
        """
        with set_log_level(self.logger, log_level):
            old_prefix = Path(old_folder).resolve().as_posix()
            new_prefix = Path(new_folder).resolve().as_posix()
            new_extracted = {}
            updated_count = 0

            # iterate over all existing entries
            for key, item in self.extracted_dates.items():
                # 1) update the dict key if needed
                new_key = key
                if key.startswith(old_prefix):
                    new_key = key.replace(old_prefix, new_prefix, 1)

                # 2) update TargetFile inside metadata
                tgt = item.get("TargetFile")
                if tgt and tgt.startswith(old_prefix):
                    item["TargetFile"] = tgt.replace(old_prefix, new_prefix, 1)
                    updated_count += 1

                # store the (possibly) updated item under the (possibly) updated key
                new_extracted[new_key] = item

            # replace the extracted_dates mapping
            self.extracted_dates = new_extracted
            LOGGER.debug(f"{step_name}Updated {updated_count} paths within folder: {old_prefix} → {new_prefix}")

            # rebuild file_list and all dependent attributes
            self.file_list = list(self.extracted_dates.keys())
            if apply_filters:
                self._apply_filters(step_name=step_name, log_level=log_level)
            if compute_folder_size:
                self._compute_folder_sizes(step_name=step_name, log_level=log_level)

            return updated_count

    def update_folders_bulk(self, replacements, step_name="", log_level=None):
        """
        Apply update_folder() for each (old_folder, new_folder) in replacements.
        Returns the total number of files updated across all folders.
        """
        with set_log_level(self.logger, log_level):
            total_updated = 0
            total_updated_folders = 0
            for old_folder, new_folder in replacements:
                updated = self.update_folder(old_folder, new_folder, apply_filters=False, compute_folder_size=False, step_name=step_name, log_level=log_level)
                LOGGER.debug(f"{step_name}Folder update: {old_folder} → {new_folder}, files updated: {updated}")
                total_updated += updated
                total_updated_folders += 1
            # Now Apply filters and compute folder sizes
            self._apply_filters(step_name=step_name, log_level=log_level)
            self._compute_folder_sizes(step_name=step_name, log_level=log_level)
            LOGGER.info(f"{step_name}Total files updated: {total_updated}. Total folders updated: {total_updated_folders}.")
            return total_updated

    def apply_replacements(self, replacements=None, step_name="", log_level=None):
        """
        Apply bulk path replacements in self.extracted_dates, then
        update all related attributes (file_list, filtered_file_list,
        folder_assets, file_sizes, folder_sizes).
        """
        with set_log_level(self.logger, log_level):
            if not replacements:
                LOGGER.debug(f"{step_name}No replacements to apply.")
                return 0

            updated_count = 0
            new_extracted_dates = {}

            # process each (old → new) pair
            for old_path, new_path in replacements:
                old_resolved = Path(old_path).resolve().as_posix()
                new_resolved = Path(new_path).resolve().as_posix()

                # pop returns and elimina la entrada vieja directamente de self.extracted_dates
                item = self.extracted_dates.pop(old_resolved, None)
                if item:
                    # actualiza TargetFile en el diccionario
                    item["TargetFile"] = new_resolved
                    new_extracted_dates[new_resolved] = item
                    updated_count += 1
                    LOGGER.debug(f"{step_name}✔️ Replaced: {old_resolved} → {new_resolved}")
                else:
                    LOGGER.debug(f"{step_name}⚠️ Not found for replacement: {old_resolved}")

            # agrega de nuevo las entradas renombradas
            self.extracted_dates.update(new_extracted_dates)
            LOGGER.debug(f"{step_name}✅ {updated_count} replacements applied to extracted_dates.")

            # reconstruye file_list basándote en las claves actuales
            self.file_list = list(self.extracted_dates.keys())
            LOGGER.debug(f"{step_name}Rebuilt file_list: {len(self.file_list)} entries.")

            # reaplica filtros y recalcula tamaños
            self._apply_filters(step_name=step_name, log_level=log_level)
            self._compute_folder_sizes(step_name)

            return updated_count

    def has_been_renamed(self, file_path: str) -> bool:
        """
        Devuelve True si el archivo fue renombrado (tiene 'TargetFile' distinta de 'SourceFile').
        """
        file_path = Path(file_path).resolve().as_posix()
        entry = self.extracted_dates.get(file_path)
        return bool(entry and entry.get("TargetFile") != entry.get("SourceFile"))

    def save_to_json(self, output_file, step_name=''):
        """
        Export extracted_dates to a JSON file.
        """
        # Ensure output_file has an extension; default to .json
        if not os.path.splitext(output_file)[1]:
            output_file = output_file + '.json'
        # Separate output_filename and output_ext
        output_filename, output_ext = os.path.splitext(output_file)
        # Add TIMESTAMP to output_file
        output_filename = f"{TIMESTAMP}_{output_filename}"
        output_file = f"{output_filename}{output_ext}"
        output_filepath = os.path.join(FOLDERNAME_EXTRACTED_DATES, output_file)
        os.makedirs(FOLDERNAME_EXTRACTED_DATES, exist_ok=True)

        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(self.extracted_dates, f, ensure_ascii=False, indent=2)
        self.logger.info(f"{step_name}EXIF Dates saved into JSON: {output_filepath}")

    def load_from_json(self, input_file, step_name=''):
        """
        Load extracted_dates from a JSON file.
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            self.extracted_dates = json.load(f)
        self.logger.info(f"{step_name}EXIF Dates loaded from JSON: {input_file}")


    def show_files_without_dates(self, relative_folder, step_name=""):
        """
        Displays a summary of files that do not have a valid OldestDate field in self.extracted_dates.

        Args:
            relative_folder: Base path to which file paths will be shown relatively.
            step_name (str): Optional prefix for log messages.
        """
        if self.logger.isEnabledFor(logging.INFO):
            files_with_missing_dates = []
            relative_base = Path(relative_folder).resolve()
            for file_path, info in self.extracted_dates.items():
                oldest_date = info.get("OldestDate")
                if oldest_date is None:
                    try:
                        rel_path = str(Path(file_path).resolve().relative_to(relative_base))
                    except ValueError:
                        rel_path = str(Path(file_path).resolve())
                    files_with_missing_dates.append(rel_path)
            self.logger.info(f"{step_name}📋 Total Files Without Date in Output folder: {len(files_with_missing_dates)}")
            for rel_path in files_with_missing_dates:
                self.logger.info(f"{step_name}📋 File Without Date: {rel_path}")

    def extract_dates(self, step_name='', block_size=1_000, use_fallback_to_filename=True, log_level=None, max_workers=None):
        """
        Extract dates from EXIF, PIL or fallback to filesystem timestamp. Store results in self.extracted_dates.
        """

        if max_workers is None:
            max_workers = cpu_count() * 16
        self.extracted_dates = {}
        candidate_tags = ['DateTimeOriginal', 'CreateDate', 'DateCreated', 'CreationDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'ModifyDate', 'FileModifyDate', 'FileNameDate', 'FilePathDate']
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        reference = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)

        # --- Internal function to process a single block
        def _process_block(block_index, block_files):
            local_metadata = {}

            # --- Try ExifTool
            if Path(exif_tool_path).exists():
                if platform.system() == 'Windows':
                    filename_charset = 'cp1252'
                else:
                    filename_charset = 'utf8'

                command = [
                    exif_tool_path,
                    '-charset', f'filename={filename_charset}',  # leer nombres en CP1252 en Win, UTF-8 en Linux/macOS
                    '-charset', 'exif=utf8',  # emitir todos los campos EXIF en UTF-8
                    '-j', '-n', '-time:all', '-fast', '-fast2', '-s',
                    *block_files
                ]
                try:
                    if len(block_files) <= 10:
                        files_preview = ' '.join(block_files)
                    else:
                        files_preview = ' '.join(block_files[:10]) + ' ...'
                    base_cmd = ' '.join(command[:7])
                    self.logger.debug(f"{step_name}⏳ Running: {base_cmd} {files_preview}")
                    result = run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)

                    if result.stdout.strip():
                        try:
                            raw_metadata_list = json.loads(result.stdout)
                            metadata_list = []
                            # Filter raw_metadata_list to include only the tags in candidate_tags
                            for entry in raw_metadata_list:
                                filtered_entry = {"SourceFile": entry.get("SourceFile")}
                                for tag in candidate_tags:
                                    if tag in entry:
                                        filtered_entry[tag] = entry[tag]
                                metadata_list.append(filtered_entry)
                            self.logger.debug(f"{step_name}✅ Exiftool returned {len(metadata_list)} entries for block {block_index}.")
                        except json.JSONDecodeError as e:
                            self.logger.debug(f"{step_name}⚠️ [Block {block_index}]: JSON error: {e}")
                            self.logger.debug(f"{step_name}🔴 STDOUT:\n{result.stdout}")
                            metadata_list = []
                    else:
                        self.logger.warning(f"{step_name}❌ [Block {block_index}]: No output from Exiftool.")
                        self.logger.debug(f"{step_name}🔴 STDERR:\n{result.stderr}")
                        metadata_list = []
                except Exception as e:
                    self.logger.exception(f"{step_name}❌ Error running Exiftool: {e}")
                    metadata_list = []

            # If Exiftool is not found, show a warning
            else:
                self.logger.warning(f"{step_name}⚠️ Exiftool not found at '{exif_tool_path}'. Using PIL and filesystem fallback.")
                metadata_list = [{"SourceFile": f} for f in block_files]

            for entry in metadata_list:
                src = entry.get("SourceFile")
                if not src:
                    continue

                # file_path = Path(src).resolve().as_posix()                 # resolve symlinks to target file
                file_path = Path(src).as_posix()                             # don't resolve symlinks to target file

                # Creamos full_info con SourceFile y TargetFile al principio
                full_info = {
                    "SourceFile": file_path,
                    "TargetFile": file_path,
                }
                # Ahora añadimos el resto de claves originales que estén en candidate_tags
                full_info.update(entry)

                dt_final = None
                source = ""

                # Buscar la fecha más antigua entre las claves del EXIF
                for tag, value in entry.items():
                    if isinstance(value, str):
                        try:
                            raw_clean = value.strip()
                            if raw_clean[:10].count(":") == 2 and "+" in raw_clean:
                                dt = normalize_datetime_utc(datetime.strptime(raw_clean, "%Y:%m:%d %H:%M:%S%z"))
                            elif raw_clean[:10].count(":") == 2:
                                dt = normalize_datetime_utc(datetime.strptime(raw_clean, "%Y:%m:%d %H:%M:%S"))
                            else:
                                dt = normalize_datetime_utc(parser.parse(raw_clean))
                            if is_date_valid(dt, reference):
                                if not dt_final or dt < dt_final:
                                    dt_final = dt
                                    source = f"EXIF:{tag}"
                        except:
                            continue

                # Fallback a PIL solo si aún no se tiene una fecha válida
                if not dt_final:
                    try:
                        img = Image.open(file_path)
                        exif_data = img._getexif() or {}
                        for tag_name in ("DateTimeOriginal", "DateTime"):
                            tag_id = next((tid for tid, name in ExifTags.TAGS.items() if name == tag_name), None)
                            raw = exif_data.get(tag_id)
                            if isinstance(raw, str):
                                dt = datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
                                if is_date_valid(dt, reference):
                                    full_info[f"PIL:{tag_name}"] = dt.isoformat()
                                    if not dt_final or dt < dt_final:
                                        dt_final = dt
                                        source = f"PIL:{tag_name}"
                                    break
                    except:
                        pass

                # Fallback al nombre del fichero o path si aún no hay ninguna
                if not dt_final and use_fallback_to_filename:
                    try:
                        guessed_date, guessed_source = guess_date_from_filename(file_path, step_name=step_name)
                        if guessed_date:
                            dt = parser.isoparse(guessed_date)
                            if is_date_valid(dt, reference):
                                file_path_obj = Path(file_path)
                                if guessed_source == "filename":
                                    full_info["FileNameDate"] = dt.isoformat()
                                    source = f"FILENAME:{file_path_obj.name}"
                                elif guessed_source == "filepath":
                                    full_info["FilePathDate"] = dt.isoformat()
                                    source = f"FILEPATH:{file_path_obj.parent}"
                                dt_final = dt
                    except:
                        pass

                # Fallback a fecha del sistema si aún no hay ninguna
                if not dt_final:
                    try:
                        fs_ctime = datetime.fromtimestamp(os.path.getctime(file_path)).replace(tzinfo=timezone.utc)
                        if is_date_valid(fs_ctime, reference):
                            full_info["FileSystem:CTime"] = fs_ctime.isoformat()
                            dt_final = fs_ctime
                            source = "FileSystem:CTime"
                    except:
                        pass

                # Añadir OldestDate y Source al diccionario
                full_info["OldestDate"] = dt_final.isoformat() if dt_final else None
                full_info["Source"] = source or "None"

                local_metadata[file_path] = full_info

            return local_metadata

        # --- Main execution
        def main():
            with set_log_level(self.logger, log_level):
                self.logger.info(f"{step_name}📅 Extracting Dates for '{self.folder_path}'...")
                json_files = [f for f in self.file_list if Path(f).suffix.lower() == '.json']

                # Filter the file list to only include supported photo and video extensions
                media_files = [f for f in self.file_list if Path(f).suffix.lower() in set(PHOTO_EXT).union(VIDEO_EXT)]

                # Filter the file list to only include supported photo and video extensions, and exclude any symlinks (only real files).
                # media_files = [f for f in self.file_list if not Path(f).is_symlink() and Path(f).suffix.lower() in set(PHOTO_EXT).union(VIDEO_EXT)]

                symlinks = [f for f in self.file_list if Path(f).is_symlink()]

                file_blocks = [media_files[i:i + block_size] for i in range(0, len(media_files), block_size)]
                total_blocks = len(file_blocks)
                total_files = len(self.file_list)
                total_media_files = len(media_files)
                total_json_files = len(json_files)
                total_symlinks = len(symlinks)

                # Clean memory
                del media_files
                del json_files
                del symlinks

                # ⏱️ Start timing
                start_time = time.time()
                completed_blocks = 0
                avg_block_time = None

                # Parallel execution using ThreadPoolExecutor
                workers = max(1, min(total_blocks, max_workers, 64))    # Ensure at least 1 worker and maximum max_workers (saturated to 64 workers)
                self.logger.info(f"{step_name}🧵 {total_files} files found ({total_media_files} media files | {total_json_files} JSON files | {total_symlinks} Symlinks)")
                self.logger.info(f"{step_name}🧵 Launching {total_blocks} blocks of maximum {block_size} files")
                self.logger.info(f"{step_name}🧵 Using {workers} workers for parallel extraction")
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future_to_index = {
                        executor.submit(_process_block, idx, block): idx
                        for idx, block in enumerate(file_blocks, 1)
                    }

                    with tqdm(total=total_blocks, desc=f"{MSG_TAGS['INFO']}{step_name}📊 Progress", unit="block", smoothing=0.1, dynamic_ncols=True, leave=True) as pbar:
                        for future in as_completed(future_to_index):
                            result = future.result()
                            self.extracted_dates.update(result)
                            completed_blocks += 1
                            elapsed = time.time() - start_time
                            current_block_time = elapsed / completed_blocks
                            avg_block_time = current_block_time if avg_block_time is None else (avg_block_time + current_block_time) / 2
                            est_total = avg_block_time * total_blocks
                            est_remain = est_total - elapsed
                            pbar.set_postfix({
                                "Elapsed": f"{int(elapsed // 60)}m",
                                "ETA": f"{int(est_remain // 60)}m",
                                "Total": f"{int(est_total // 60)}m"
                            })
                            pbar.update(1)

        # Call the main function to start the process
        main()


    def count_files(self, exclude_ext=None, include_ext=None, step_name='', log_level=None):
        """
        Count all files in the folder by type (photos, videos, metadata, sidecar),
        with special handling for symlinks and size. Uses self.extracted_dates
        if available to count media files with/without valid dates.
        """
        with set_log_level(self.logger, log_level):
            self.logger.info(f"{step_name}📊 Counting Files for '{self.folder_path}'...")
            counters = init_count_files_counters()

            # Normalize extensions
            excluded_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (exclude_ext or [])} or None
            included_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (include_ext or [])} or None

            total_bytes = 0
            media_file_paths = []

            # Decide source of file list: use in-memory analyzer list if available
            if getattr(self, 'file_list', None):
                # English comment: iterate over cached file list
                paths = self.file_list
            else:
                # English comment: fallback to walking the disk
                paths = []
                for root, dirs, files in os.walk(self.folder_path):
                    # Skip hidden folders and Synology folders
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '@eaDir']
                    for filename in files:
                        paths.append(os.path.join(root, filename))

            for full_path in paths:
                ext = Path(full_path).suffix.lower()

                # Skip by extension if requested
                if excluded_extensions and ext in excluded_extensions:
                    continue
                if included_extensions and ext not in included_extensions:
                    continue

                is_symlink = os.path.islink(full_path)
                if is_symlink:
                    try:
                        link_target = os.readlink(full_path)
                        resolved_target = os.path.abspath(
                            os.path.join(os.path.dirname(full_path), link_target)
                        )
                        if not os.path.exists(resolved_target):
                            self.logger.info(f"{step_name}Excluded broken symlink: {full_path}")
                            continue
                    except OSError as e:
                        self.logger.warning(f"{step_name}⚠️ Failed to read symlink {full_path}: {e}")
                        continue

                counters['total_files'] += 1
                if is_symlink:
                    counters['total_symlinks'] += 1

                supported = ext in (PHOTO_EXT + VIDEO_EXT + METADATA_EXT + SIDECAR_EXT)
                if supported:
                    counters['supported_files'] += 1
                    if is_symlink:
                        counters['supported_symlinks'] += 1
                else:
                    counters['unsupported_files'] += 1

                media_category = None
                if ext in PHOTO_EXT:
                    media_category = 'photos'
                    counters['photo_files'] += 1
                    counters['media_files'] += 1
                    counters['photos']['total'] += 1
                    if is_symlink:
                        counters['photo_symlinks'] += 1
                        counters['media_symlinks'] += 1
                        counters[media_category]['symlinks'] += 1
                elif ext in VIDEO_EXT:
                    media_category = 'videos'
                    counters['video_files'] += 1
                    counters['media_files'] += 1
                    counters['videos']['total'] += 1
                    if is_symlink:
                        counters['video_symlinks'] += 1
                        counters['media_symlinks'] += 1
                        counters[media_category]['symlinks'] += 1

                if ext in METADATA_EXT:
                    counters['metadata_files'] += 1
                if ext in SIDECAR_EXT:
                    counters['sidecar_files'] += 1
                if ext in METADATA_EXT or ext in SIDECAR_EXT:
                    counters['non_media_files'] += 1

                if media_category:
                    media_file_paths.append(full_path)

                if not is_symlink:
                    try:
                        total_bytes += os.path.getsize(full_path)
                    except:
                        pass

            counters['total_size_mb'] = round(total_bytes / (1024 * 1024), 1)

            # If we have extracted dates, count valid/invalid per media type
            if self.extracted_dates:
                for path, entry in self.extracted_dates.items():
                    oldest_date = entry.get("OldestDate")
                    media_type = None
                    ext = Path(path).suffix.lower()
                    if ext in PHOTO_EXT:
                        media_type = 'photos'
                    elif ext in VIDEO_EXT:
                        media_type = 'videos'
                    if media_type:
                        if oldest_date:
                            counters[media_type]['with_date'] += 1
                        else:
                            counters[media_type]['without_date'] += 1

                for media_type in ['photos', 'videos']:
                    total = counters[media_type].get('total', 0)
                    symlinks = counters[media_type].get('symlinks', 0)
                    with_date = counters[media_type].get('with_date', 0)
                    without_date = counters[media_type].get('without_date', 0)

                    # real_total = total - symlinks
                    real_total = total
                    if real_total > 0:
                        counters[media_type]['pct_with_date'] = (with_date / real_total) * 100
                        counters[media_type]['pct_without_date'] = (without_date / real_total) * 100
                    else:
                        counters[media_type]['pct_with_date'] = 0.0
                        counters[media_type]['pct_without_date'] = 0.0

            return counters

def run_full_pipeline(input_folder, logger, max_workers=None):
    import time
    from datetime import timedelta

    start_time = time.time()

    # 🕒 Inicializar FolderAnalyzer y extrae fechas
    t0 = time.time()
    analyzer = FolderAnalyzer(folder_path=input_folder, force_date_extraction=True, logger=logger)
    elapsed = timedelta(seconds=round(time.time() - t0))
    logger.info(f"🕒 FolderAnalyzer initialized in {elapsed}")

    # # 🕒 Extraer fechas
    # t0 = time.time()
    # analyzer.extract_dates(step_name=f"🕒 [Extract Dates | workers={max_workers}] : ", max_workers=max_workers)
    # elapsed = timedelta(seconds=round(time.time() - t0))
    # logger.info(f"🕒 Dates extracted in {elapsed}")

    # 🕒 Contar ficheros
    t0 = time.time()
    counters = analyzer.count_files(step_name="📊 [STEP]-[Count Files  ] : ")
    logger.info("📋 Counting Results:")
    print_dict_pretty(counters)
    elapsed = timedelta(seconds=round(time.time() - t0))
    logger.info(f"🕒 Files counted in {elapsed}")

    # 🕒 Guardar JSON
    t0 = time.time()
    analyzer.save_to_json(rf'extracted_dates_{str(max_workers)}_workers.json', step_name="💾 [STEP]-[Save JSON    ] : ")
    elapsed = timedelta(seconds=round(time.time() - t0))
    logger.info(f"💾 JSON saved in {elapsed}")

    # 🕒 Mostrar duración total
    total_elapsed = timedelta(seconds=round(time.time() - start_time))
    logger.info(f"✅ Total execution time: {total_elapsed}")


##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    change_working_dir(change_dir=True)

    custom_print(f"Setting Global LOGGER...", log_level=logging.INFO)
    logger = set_LOGGER('info')

    # Define tu carpeta
    input_folder = "/mnt/homes/jaimetur/PhotoMigrator/data/Zip_files_50GB_2025_processed_20250710-180016"

    # Lista de valores a probar
    worker_values = [cpu_count()*16, cpu_count()*8, cpu_count()*6, cpu_count()*4, cpu_count()*2, cpu_count()*1]

    for workers in worker_values:
        print(f"\n🚀 Running pipeline with max_workers = {workers}")
        run_full_pipeline(input_folder, logger, max_workers=workers)



