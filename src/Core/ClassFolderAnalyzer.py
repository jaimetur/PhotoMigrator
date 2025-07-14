# ========================
# 📦 IMPORTS
# ========================
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import multiprocessing
import json
from pathlib import Path
from datetime import datetime, timezone
from subprocess import run
from tempfile import TemporaryDirectory
import logging

from PIL import Image, ExifTags
from dateutil import parser

from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from Core.GlobalFunctions import set_LOGGER
from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import TIMESTAMP, FOLDERNAME_EXIFTOOL, LOGGER, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT
from Utils.DateUtils import normalize_datetime_utc, is_date_valid
from Utils.GeneralUtils import print_dict_pretty
from Utils.StandaloneUtils import get_exif_tool_path, custom_print, change_working_dir

# ========================
# 📂 FolderAnalyzer CLASS
# ========================
class FolderAnalyzer:
    def __init__(self, folder_path=None, extracted_dates=None, logger=None, step_name=''):
        """
        Initialize the FolderAnalyzer from a given folder or existing extracted_dates.
        If folder_path is provided, walk through all files.
        """
        if logger:
            self.logger = logger
        else:
            self.logger = set_LOGGER()
        self.folder_path = Path(folder_path).resolve().as_posix() if folder_path else None
        self.file_dates = extracted_dates or {}
        self.file_list = []

        if self.folder_path:
            self._build_file_list(step_name=step_name)

    def _build_file_list(self, step_name=''):
        """
        Build the list of files in the given folder (self.folder_path), excluding symlinks.
        If the folder does not exist, print an error message and skip file collection.
        """
        if not os.path.isdir(self.folder_path):
            message = f"❌ Folder does not exist: {self.folder_path}"
            self.logger.error(message)
            self.file_list = []
            return
        self.logger.info(f"{step_name}Building File List for '{self.folder_path}'...")
        self.file_list = []
        for root, _, files in os.walk(self.folder_path):
            for name in files:
                full_path = os.path.join(root, name)
                if not os.path.islink(full_path):
                    self.file_list.append(Path(full_path).resolve().as_posix())

    def get_attribute(self, file_path, attr="SelectedDate", step_name=""):
        """
        Return one or more attributes from extracted_dates by TargetFile.
        """
        path = Path(file_path).resolve().as_posix()
        item = self.file_dates.get(path)
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
        Return only the SelectedDate for the given file.
        """
        return self.get_attribute(file_path, attr="SelectedDate", step_name=step_name)

    def update_target_file(self, current_path, new_target_path, step_name=""):
        """
        Update the TargetFile of a single file after moving/renaming.
        """
        current_path = Path(current_path).resolve().as_posix()
        new_target_path = Path(new_target_path).resolve().as_posix()

        # Elimina la ruta antigua de si existía
        item = self.file_dates.pop(current_path, None)
        if not item:
            self.logger.warning(f"{step_name}No se encontró el archivo por '{current_path}'")
            return False

        # Asigna el nuevo TargetFile como índice
        item["TargetFile"] = new_target_path
        self.file_dates[new_target_path] = item

        self.logger.info(f"{step_name}TargetFile actualizado: {current_path} → {new_target_path}")
        return True

    def update_folder(self, old_folder: str, new_folder: str, step_name: str = ""):
        """
        Actualiza en bloque todos los archivos cuyo 'TargetFile' o 'SourceFile' empiece por old_folder.
        """
        old_folder = Path(old_folder).resolve().as_posix()
        new_folder = Path(new_folder).resolve().as_posix()
        updated = {}
        count = 0
        for key, item in list(self.file_dates.items()):
            tgt = item.get("TargetFile", item.get("SourceFile"))
            if tgt and tgt.startswith(old_folder):
                new_tgt = tgt.replace(old_folder, new_folder, 1)
                item["TargetFile"] = new_tgt
                updated[new_tgt] = item
                count += 1
        self.file_dates = updated

        self.logger.info(f"{step_name}Se actualizaron {count} rutas TargetFile: {old_folder} → {new_folder}")
        return count

    def update_target_file_bulk(self, old_folder, new_folder):
        """
        Update all TargetFile entries when an entire folder has been renamed/moved.
        """
        self.update_folder(old_folder, new_folder)

    def has_been_renamed(self, file_path: str) -> bool:
        """
        Devuelve True si el archivo fue renombrado (tiene 'TargetFile' distinta de 'SourceFile').
        """
        file_path = Path(file_path).resolve().as_posix()
        entry = self.file_dates.get(file_path)
        return bool(entry and entry.get("TargetFile") != entry.get("SourceFile"))

    def save_to_json(self, output_path):
        """
        Export extracted_dates to a JSON file.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.file_dates, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Dates saved into JSON: {output_path}")

    def load_from_json(self, input_path):
        """
        Load extracted_dates from a JSON file.
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            self.file_dates = json.load(f)
        self.logger.info(f"Dates loaded from JSON: {input_path}")

    def extract_dates_old(self, step_name='', block_size=10_000, log_level=None):
        """
        Extract dates from EXIF, PIL or fallback to filesystem timestamp. Store results in self.extracted_dates.
        """
        self.file_dates = {}
        candidate_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate','TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate']
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        reference = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)

        # Filter the file list to only include supported photo and video extensions
        media_files = [f for f in self.file_list if Path(f).suffix.lower() in set(PHOTO_EXT).union(set(VIDEO_EXT))]

        # Split into blocks of 10,000 files each
        file_blocks = [media_files[i:i + block_size] for i in range(0, len(media_files), block_size)]

        with set_log_level(self.logger, log_level):
            self.logger.info(f"{step_name}⏳ Extracting Dates for '{self.folder_path}'...")
            num_blocks = len(file_blocks)
            self.logger.info(f"{step_name}Launching {num_blocks} blocks of maximum ~{block_size} files")
            for block_index, file_block in enumerate(file_blocks, 1):
                self.logger.info(f"{step_name}🔎 [Block {block_index}]: Running block {block_index} with exiftool...")
                metadata_map = {}

                # --- Try ExifTool (sin uso de archivos)
                if Path(exif_tool_path).exists():
                    command = [exif_tool_path, "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + file_block
                    try:
                        if len(file_block) <= 10:
                            files_preview = ' '.join(file_block)
                        else:
                            files_preview = ' '.join(file_block[:10]) + ' ...'
                        base_cmd = ' '.join(command[:7])  # exiftool path + flags
                        self.logger.debug(f"{step_name}⏳ Running: {base_cmd} {files_preview}")
                        result = run(command, capture_output=True, text=True, check=False)

                        if result.stdout.strip():
                            try:
                                metadata_list = json.loads(result.stdout)
                                self.logger.info(f"{step_name}✅ Exiftool returned {len(metadata_list)} entries for block {block_index}.")
                            except json.JSONDecodeError as e:
                                self.logger.debug(f"{step_name}⚠️ [Block {block_index}]: exiftool failed to extract some files. Error: {e}")
                                self.logger.debug(f"{step_name}🔴 STDOUT:\n{result.stdout}")
                                metadata_list = []
                        else:
                            self.logger.warning(f"{step_name}❌ [Block {block_index}]: Exiftool did not return any output.")
                            self.logger.debug(f"{step_name}🔴 STDERR:\n{result.stderr}")
                            metadata_list = []
                    except Exception as e:
                        self.logger.exception(f"{step_name}❌ Error running exiftool: {e}")
                        metadata_list = []
                # If Exiftool is not found, then fallback to PIL or filesystem
                else:
                    self.logger.warning(f"{step_name}⚠️ Exiftool not found at '{exif_tool_path}'. Using PIL and filesystem as fallback.")
                    metadata_list = [{"SourceFile": f} for f in file_block]  # Solo contiene la ruta de los archivos para procesar en el bucle

                for entry in metadata_list:
                    src = entry.get("SourceFile")
                    if not src:
                        continue
                    file_path = Path(src).resolve().as_posix()

                    # Creamos full_info con SourceFile y TargetFile al principio
                    full_info = {
                        "SourceFile": file_path,
                        "TargetFile": file_path,
                    }
                    # Ahora añadimos el resto de claves originales que estén en candidate_tags
                    for tag in candidate_tags:
                        if tag in entry:
                            full_info[tag] = entry[tag]

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

                    self.file_dates[file_path] = full_info

    def extract_dates(self, step_name='', block_size=10_000, log_level=None):
        """
        Extract dates from EXIF, PIL or fallback to filesystem timestamp. Store results in self.file_dates.
        """
        self.file_dates = {}
        candidate_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate']
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        reference = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)

        # --- Internal function to process a single block
        def _process_block(block_index, file_block, total_blocks, start_time):
            local_metadata = {}

            # --- Try ExifTool
            if Path(exif_tool_path).exists():
                command = [exif_tool_path, "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + file_block
                try:
                    if len(file_block) <= 10:
                        files_preview = ' '.join(file_block)
                    else:
                        files_preview = ' '.join(file_block[:10]) + ' ...'
                    base_cmd = ' '.join(command[:7])
                    self.logger.debug(f"{step_name}⏳ Running: {base_cmd} {files_preview}")
                    result = run(command, capture_output=True, text=True, check=False)

                    if result.stdout.strip():
                        try:
                            metadata_list = json.loads(result.stdout)
                            self.logger.info(f"{step_name}✅ Exiftool returned {len(metadata_list)} entries for block {block_index}.")
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

            # If Exiftool is not found, then fallback to PIL or filesystem
            else:
                self.logger.warning(f"{step_name}⚠️ Exiftool not found at '{exif_tool_path}'. Using PIL and filesystem fallback.")
                metadata_list = [{"SourceFile": f} for f in file_block]

            for entry in metadata_list:
                src = entry.get("SourceFile")
                if not src:
                    continue
                file_path = Path(src).resolve().as_posix()

                # Creamos full_info con SourceFile y TargetFile al principio
                full_info = {
                    "SourceFile": file_path,
                    "TargetFile": file_path,
                }
                # Ahora añadimos el resto de claves originales que estén en candidate_tags
                for tag in candidate_tags:
                    if tag in entry:
                        full_info[tag] = entry[tag]

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

            elapsed = time.time() - start_time
            avg_block_time = elapsed / block_index
            est_total = avg_block_time * total_blocks
            est_remain = est_total - elapsed
            self.logger.info(f"{step_name}📊 Block {block_index}/{total_blocks} done • Elapsed: {int(elapsed // 60)}m • Estimated Total: {int(est_total // 60)}m • Estimated Remaining: {int(est_remain // 60)}m")

            return local_metadata

        # --- Main execution
        def main():
            with set_log_level(self.logger, log_level):
                self.logger.info(f"{step_name}⏳ Extracting Dates for '{self.folder_path}'...")
                # Filter the file list to only include supported photo and video extensions
                media_files = [f for f in self.file_list if Path(f).suffix.lower() in set(PHOTO_EXT).union(VIDEO_EXT)]
                file_blocks = [media_files[i:i + block_size] for i in range(0, len(media_files), block_size)]
                total_blocks = len(file_blocks)
                self.logger.info(f"{step_name}Launching {total_blocks} blocks of ~{block_size} files")

                futures = []
                start_time = time.time()
                with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
                    for idx, block in enumerate(file_blocks, 1):
                        futures.append(executor.submit(_process_block, idx, block, total_blocks, start_time))

                    for future in as_completed(futures):
                        result = future.result()
                        self.file_dates.update(result)

        main()

    def count_files(self, exclude_ext=None, include_ext=None, step_name='', log_level=None):
        """
        Count all files in the folder by type (photos, videos, metadata, sidecar),
        with special handling for symlinks and size. Uses self.extracted_dates
        if available to count media files with/without valid dates.
        """
        with set_log_level(self.logger, log_level):
            self.logger.info(f"{step_name}📊Counting Files for '{self.folder_path}'...")
            counters = init_count_files_counters()

            # Normalize extensions
            excluded_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (exclude_ext or [])} or None
            included_extensions = {ext if ext.startswith('.') else f".{ext}" for ext in (include_ext or [])} or None

            total_bytes = 0
            media_file_paths = []

            for root, dirs, files in os.walk(self.folder_path):
                # Skip hidden folders and Synology folders
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '@eaDir']
                for filename in files:
                    full_path = os.path.join(root, filename)
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
                            resolved_target = os.path.abspath(os.path.join(os.path.dirname(full_path), link_target))
                            if not os.path.exists(resolved_target):
                                LOGGER.info(f"{step_name}Excluded broken symlink: {full_path}")
                                continue
                        except OSError as e:
                            LOGGER.warning(f"{step_name}⚠️ Failed to read symlink {full_path}: {e}")
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
            if self.file_dates:
                for path, entry in self.file_dates.items():
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
                    total = counters[media_type]['total']
                    with_date = counters[media_type]['with_date']
                    if total > 0:
                        counters[media_type]['pct_with_date'] = (with_date / total) * 100
                        counters[media_type]['pct_without_date'] = ((total - with_date) / total) * 100
                    else:
                        counters[media_type]['pct_with_date'] = 0
                        counters[media_type]['pct_without_date'] = 0
            # else:
            #     # If extract_dates hasn't been called yet
            #     for media_type in ['photos', 'videos']:
            #         counters[media_type]['with_date'] = 0
            #         counters[media_type]['without_date'] = 0
            #         counters[media_type]['pct_with_date'] = 0
            #         counters[media_type]['pct_without_date'] = 0

            return counters


def extract_dates_from_files(self, file_paths, step_name="", log_level=None):
    """
    Extrae fechas desde EXIF usando ExifTool (fallback: PIL y FS) en paralelo.
    Añade 'OldestDate' y 'Source' a cada entrada de self.data.
    Si el archivo no existía en self.data, se crea una nueva entrada.
    """
    def process_block(block_files, block_index, temp_dir):
        metadata_list = []
        ref_timestamp = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        output_file = os.path.join(temp_dir, f"block_{block_index}.json")

        # --- Try ExifTool
        if Path(exif_tool_path).exists():
            cmd = [exif_tool_path, "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + block_files
            try:
                with open(output_file, "w", encoding="utf-8") as out_json:
                    run(cmd, stdout=out_json, stderr=None, check=True)
                with open(output_file, "r", encoding="utf-8") as f:
                    metadata_list = json.load(f)
            except Exception:
                LOGGER.warning(f"{step_name}❌ ExifTool failed on block {block_index}")
                metadata_list = []

        # --- Fallback: PIL
        if not metadata_list:
            for path in block_files:
                try:
                    img = Image.open(path)
                    exif_data = img._getexif() or {}
                    for tag_name in ("DateTimeOriginal", "DateTime"):
                        tag_id = next((tid for tid, name in ExifTags.TAGS.items() if name == tag_name), None)
                        raw = exif_data.get(tag_id)
                        if isinstance(raw, str):
                            dt = datetime.strptime(raw.strip(), "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            metadata_list.append({"SourceFile": path, "DateTime": dt.isoformat(), "Source": "📷 PIL EXIF"})
                            break
                except:
                    continue

        # --- Add fallback FS date if needed
        results = []
        for entry in metadata_list:
            src = entry.get("SourceFile")
            norm = Path(src).resolve().as_posix()
            oldest_date = None
            selected_source = ""
            candidate_tags = ['DateTimeOriginal', 'CreateDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate', 'DateTime']

            valid_dates = []
            if "DateTime" in entry:
                candidate_tags.insert(0, "DateTime")  # PIL fallback tag

            for tag in candidate_tags:
                raw = entry.get(tag)
                if isinstance(raw, str):
                    try:
                        if raw[:10].count(":") == 2 and "+" in raw:
                            dt = normalize_datetime_utc(datetime.strptime(raw, "%Y:%m:%d %H:%M:%S%z"))
                        elif raw[:10].count(":") == 2:
                            dt = normalize_datetime_utc(datetime.strptime(raw, "%Y:%m:%d %H:%M:%S"))
                        else:
                            dt = normalize_datetime_utc(parser.parse(raw.strip()))
                        if is_date_valid(dt, ref_timestamp):
                            valid_dates.append((dt, tag))
                    except Exception:
                        continue

            if valid_dates:
                oldest_date, tag = min(valid_dates, key=lambda x: x[0])
                selected_source = f"🕒 EXIF date used: {oldest_date.isoformat()} (tag: {tag})"
            else:
                try:
                    fs_ctime = datetime.fromtimestamp(os.path.getctime(norm)).replace(tzinfo=timezone.utc)
                    if is_date_valid(fs_ctime, ref_timestamp):
                        oldest_date = fs_ctime
                        selected_source = f"📂 FS date used: {fs_ctime.isoformat()}"
                except:
                    pass

            results.append({
                "SourceFile": norm,
                "OldestDate": oldest_date.isoformat() if oldest_date else None,
                "Source": selected_source
            })

        return results

    with set_log_level(LOGGER, log_level):
        block_size = 10000
        file_blocks = [file_paths[i:i + block_size] for i in range(0, len(file_paths), block_size)]
        all_results = []

        with TemporaryDirectory() as temp_dir:
            with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 2) as executor:
                futures = {
                    executor.submit(process_block, block, idx, temp_dir): idx
                    for idx, block in enumerate(file_blocks)
                }
                for future in as_completed(futures):
                    all_results.extend(future.result())

        # --- Apply results to self.data
        updated = 0
        for result in all_results:
            src = result["SourceFile"]
            entry = self.date_index.get(src)
            if not entry:
                entry = {"SourceFile": src}
                self.file_dates.append(entry)
            entry["OldestDate"] = result["OldestDate"]
            entry["Source"] = result["Source"]
            self.date_index[src] = entry
            updated += 1

        self.logger.info(f"{step_name}🧪 Fechas extraídas y aplicadas a {updated} archivos.")
##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    if __name__ == "__main__":
        import time
        from datetime import timedelta

        # ⏱️ Start total timing
        start_time = time.time()

        change_working_dir(change_dir=True)

        custom_print(f"Setting Global LOGGER...", log_level=logging.INFO)
        logger = set_LOGGER('info')

        # Ruta con tus fotos y vídeos
        input_folder = "/mnt/homes/jaimetur/PhotoMigrator/data/Zip_files_50GB_2025_processed_20250710-180016"
        # input_folder = r"c:\Temp_Unsync\Takeout"

        # ⏱️ Inicializar FolderAnalyzer
        t0 = time.time()
        analyzer = FolderAnalyzer(folder_path=input_folder, logger=logger)
        elapsed = timedelta(seconds=round(time.time() - t0))
        print(f"⏱️ FolderAnalyzer initialized in {elapsed}")
        logger.info(f"⏱️ FolderAnalyzer initialized in {elapsed}")

        # ⏱️ Extraer fechas
        t0 = time.time()
        analyzer.extract_dates(step_name="🕒 [STEP]-[Extract Dates] : ")
        elapsed = timedelta(seconds=round(time.time() - t0))
        print(f"⏱️ Dates extracted in {elapsed}")
        logger.info(f"⏱️ Dates extracted in {elapsed}")

        # ⏱️ Contar ficheros
        t0 = time.time()
        counters = analyzer.count_files(step_name="📊 [STEP]-[Count Files  ] : ")
        print("📋 Counting Results:")
        print_dict_pretty(counters)
        elapsed = timedelta(seconds=round(time.time() - t0))
        print(f"⏱️ Files counted in {elapsed}")
        logger.info(f"⏱️ Files counted in {elapsed}")

        # ⏱️ Guardar JSON
        t0 = time.time()
        analyzer.save_to_json(r'r:\jaimetur\PhotoMigrator\Exiftool_outputs\extracted_dates.json')
        elapsed = timedelta(seconds=round(time.time() - t0))
        print(f"💾 JSON saved in {elapsed}")
        logger.info(f"💾 JSON saved in {elapsed}")

        # ⏱️ Mostrar duración total
        total_elapsed = timedelta(seconds=round(time.time() - start_time))
        print(f"✅ Total execution time: {total_elapsed}")
        logger.info(f"✅ Total execution time: {total_elapsed}")


