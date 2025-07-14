# ========================
# 📦 IMPORTS
# ========================
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import multiprocessing
import json
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone
from subprocess import run
from collections import defaultdict
from tempfile import TemporaryDirectory
import logging

from PIL import Image, ExifTags
from dateutil import parser

from Core.GlobalFunctions import set_LOGGER
from Core.CustomLogger import set_log_level
from Core.DataModels import init_count_files_counters
from Core.GlobalVariables import TIMESTAMP, FOLDERNAME_EXIFTOOL, LOGGER, FOLDERNAME_EXIFTOOL_OUTPUT, PHOTO_EXT, VIDEO_EXT, METADATA_EXT, SIDECAR_EXT, LOG_FILENAME
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
        self.date_index = {}

        if self.file_dates:
            self._build_index(step_name=step_name)

        elif self.folder_path:
            self._build_file_list(step_name=step_name)

    def _build_file_list(self, step_name=''):
        """
        Build the list of files in the given folder (self.folder_path), excluding symlinks.
        If the folder does not exist, print an error message and skip file collection.
        """
        if not os.path.isdir(self.folder_path):
            message = f"❌ Folder does not exist: {self.folder_path}"
            if self.logger:
                self.logger.error(message)
            else:
                print(message)
            self.file_list = []
            return
        if self.logger:
            self.logger.info(f"{step_name}Building File List for '{self.folder_path}'...")
        else:
            custom_print(f"{step_name}Building File List for '{self.folder_path}'...", log_level=logging.INFO)
        self.file_list = []
        for root, _, files in os.walk(self.folder_path):
            for name in files:
                full_path = os.path.join(root, name)
                if not os.path.islink(full_path):
                    self.file_list.append(Path(full_path).resolve().as_posix())

    def _build_index(self, step_name=''):
        """
        Construye el índice para búsquedas rápidas.
        Si existe 'TargetFile', se prioriza sobre 'SourceFile'.
        """
        self.date_index.clear()
        if self.logger:
            self.logger.info(f"{step_name}Building Index for '{self.folder_path}'...")
        else:
            custom_print(f"{step_name}Building Index for '{self.folder_path}'...", log_level=logging.INFO)
        for item in self.file_dates:
            source = item.get("SourceFile")
            target = item.get("TargetFile")

            if target:
                self.date_index[target] = item
            elif source:
                self.date_index[source] = item

        if self.logger:
            self.logger.debug(f"Índice creado con {len(self.date_index)} elementos.")

    def get_attribute(self, file_path, attr="SelectedDate", step_name=""):
        """
        Return one or more attributes from extracted_dates by TargetFile.
        """
        path = Path(file_path).resolve().as_posix()
        item = self.date_index.get(path)
        if not item:
            if self.logger:
                self.logger.debug(f"{step_name}No se encontró '{file_path}' en el índice.")
            return None

        if isinstance(attr, list):
            result = {key: item.get(key) for key in attr}
        else:
            result = item.get(attr)

        if self.logger:
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
        item = self.date_index.get(current_path)
        if not item:
            if self.logger:
                self.logger.warning(f"{step_name}No se encontró el archivo por '{current_path}'")
            return False

        # Elimina la ruta antigua de TargetFile si existía
        old_target = item.get("TargetFile")
        if old_target and old_target in self.date_index:
            del self.date_index[old_target]

        # Asigna el nuevo TargetFile y actualiza el índice
        item["TargetFile"] = new_target_path
        self.date_index[new_target_path] = item

        if self.logger:
            self.logger.info(f"{step_name}TargetFile actualizado: {current_path} → {new_target_path}")
        return True

    def update_folder(self, old_folder: str, new_folder: str, step_name: str = ""):
        """
        Actualiza en bloque todos los archivos cuyo 'TargetFile' o 'SourceFile' empiece por old_folder.
        """
        count = 0
        for item in self.file_dates:
            current_path = item.get("TargetFile") or item.get("SourceFile")
            if current_path and current_path.startswith(old_folder):
                new_target = current_path.replace(old_folder, new_folder, 1)
                if current_path in self.date_index:
                    del self.date_index[current_path]
                item["TargetFile"] = new_target
                self.date_index[new_target] = item
                count += 1
        if self.logger:
            self.logger.info(f"{step_name}Se actualizaron {count} rutas TargetFile: {old_folder} → {new_folder}")
        return count

    def update_target_file_bulk(self, old_folder, new_folder):
        """
        Update all TargetFile entries when an entire folder has been renamed/moved.
        """
        old = Path(old_folder).resolve().as_posix()
        new = Path(new_folder).resolve().as_posix()
        for src, data in self.file_dates.items():
            tgt = data.get("TargetFile", src)
            if tgt.startswith(old):
                new_tgt = tgt.replace(old, new, 1)
                data["TargetFile"] = new_tgt
                self.date_index[new_tgt] = src

    def has_been_renamed(self, file_path: str) -> bool:
        """
        Devuelve True si el archivo fue renombrado (tiene 'TargetFile').
        """
        item = self.date_index.get(file_path)
        return bool(item and "TargetFile" in item)

    def save_to_json(self, output_path):
        """
        Export extracted_dates to a JSON file.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.file_dates, f, ensure_ascii=False, indent=2)

        if self.logger:
            self.logger.info(f"Guardado en JSON: {output_path}")

    def load_from_json(self, input_path):
        """
        Load extracted_dates from a JSON file.
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            self.file_dates = json.load(f)

        self._build_index()

        if self.logger:
            self.logger.info(f"Cargado desde JSON: {input_path}")

    def extract_dates(self, step_name='', log_level=None):
        """
        Extract dates from EXIF, PIL or fallback to filesystem timestamp. Store results in self.extracted_dates.
        """
        self.file_dates = {}
        self.date_index = {}

        candidate_tags = [
            'DateTimeOriginal', 'CreateDate', 'MediaCreateDate',
            'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'FileModifyDate'
        ]
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        file_blocks = [self.file_list[i:i + 10_000] for i in range(0, len(self.file_list), 10_000)]
        reference = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)

        with set_log_level(self.logger, log_level):
            if self.logger:
                self.logger.info(f"{step_name}Extracting Dates for '{self.folder_path}'...")
            else:
                custom_print(f"{step_name}Extracting Dates for '{self.folder_path}'...", log_level=logging.INFO)

            for block_index, file_block in enumerate(file_blocks, 1):
                metadata_map = {}

                # --- Try ExifTool
                if Path(exif_tool_path).exists():
                    error_log_path = f"{LOG_FILENAME}.log"
                    chunk_json_path = os.path.join(FOLDERNAME_EXIFTOOL_OUTPUT, f"{TIMESTAMP}_block_{block_index}.json")
                    command = [exif_tool_path, "-j", "-n", "-time:all", "-fast", "-fast2", "-s"] + file_block
                    try:
                        with open(chunk_json_path, "w", encoding="utf-8") as out_json, \
                                open(error_log_path, "a", encoding="utf-8") as out_err:
                            run(command, stdout=out_json, stderr=out_err, check=True)
                    except Exception:
                        self.logger.debug(f"{step_name}❗ [Block {block_index}]: exiftool failed to extract some files")

                    with open(chunk_json_path, "r", encoding="utf-8") as out_json:
                        metadata_list = json.load(out_json)
                else:
                    metadata_list = []

                for entry in metadata_list:
                    src = entry.get("SourceFile")
                    if not src:
                        continue
                    file_path = Path(src).resolve().as_posix()

                    # Clonamos todos los datos del JSON original
                    full_info = entry.copy()
                    full_info["SourceFile"] = file_path
                    full_info["TargetFile"] = file_path

                    dt_final = None
                    source = ""
                    reference = datetime.strptime(TIMESTAMP, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)

                    # Buscar la mejor fecha de entre las claves del EXIF
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

                    # Añadir SelectedDate y Source al diccionario
                    full_info["SelectedDate"] = dt_final.isoformat() if dt_final else None
                    full_info["Source"] = source or "None"

                    self.file_dates[file_path] = full_info
                    self.date_index[file_path] = file_path

    def count_files(self, exclude_ext=None, include_ext=None, step_name='', log_level=None):
        """
        Count all files in the folder by type (photos, videos, metadata, sidecar),
        with special handling for symlinks and size. Uses self.extracted_dates
        if available to count media files with/without valid dates.
        """
        with set_log_level(self.logger, log_level):
            if self.logger:
                self.logger.info(f"{step_name}Counting Files for '{self.folder_path}'...")
            else:
                custom_print(f"{step_name}Counting Files for '{self.folder_path}'...", log_level=logging.INFO)

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

            # If we have extracted_dates, count valid/invalid per media type
            if self.file_dates:
                for path, entry in self.file_dates.items():
                    selected_date = entry.get("SelectedDate")
                    media_type = None
                    ext = Path(path).suffix.lower()
                    if ext in PHOTO_EXT:
                        media_type = 'photos'
                    elif ext in VIDEO_EXT:
                        media_type = 'videos'
                    if media_type:
                        if selected_date:
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
    Añade 'SelectedDate' y 'Source' a cada entrada de self.data.
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
            selected_date = None
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
                selected_date, tag = min(valid_dates, key=lambda x: x[0])
                selected_source = f"🕒 EXIF date used: {selected_date.isoformat()} (tag: {tag})"
            else:
                try:
                    fs_ctime = datetime.fromtimestamp(os.path.getctime(norm)).replace(tzinfo=timezone.utc)
                    if is_date_valid(fs_ctime, ref_timestamp):
                        selected_date = fs_ctime
                        selected_source = f"📂 FS date used: {fs_ctime.isoformat()}"
                except:
                    pass

            results.append({
                "SourceFile": norm,
                "SelectedDate": selected_date.isoformat() if selected_date else None,
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
            entry["SelectedDate"] = result["SelectedDate"]
            entry["Source"] = result["Source"]
            self.date_index[src] = entry
            updated += 1

        if self.logger:
            self.logger.info(f"{step_name}🧪 Fechas extraídas y aplicadas a {updated} archivos.")
##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    change_working_dir(change_dir=True)

    custom_print(f"Setting Global LOGGER...", log_level=logging.INFO)
    logger = set_LOGGER()  # Need to be called after set_FOLDERS()


    # Ruta con tus fotos y vídeos
    # input_folder = "/mnt/homes/jaimetur/PhotoMigrator/data/LocalFolderFromTakeout"
    input_folder = r"c:\Temp_Unsync\Takeout"

    # Crear el analizador
    analyzer = FolderAnalyzer(folder_path=input_folder, logger=logger)

    # Extraer fechas de los ficheros
    analyzer.extract_dates(step_name="🕒 [STEP]-[Extract Dates] : ")

    # Contar ficheros con y sin fechas válidas
    counters = analyzer.count_files(step_name="📊 [STEP]-[Count Files] : ")
    print("📋 Resultados de conteo:")
    print_dict_pretty(counters)

    analyzer.save_to_json(r'r:\jaimetur\PhotoMigrator\Exiftool_outputs\extracted_dates.json')