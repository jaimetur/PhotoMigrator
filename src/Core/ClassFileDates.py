import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timezone, datetime
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Union

from PIL import ExifTags
from PIL.Image import Image
from dateutil.parser import parser

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import TIMESTAMP, FOLDERNAME_EXIFTOOL, LOGGER
from Utils.DateUtils import normalize_datetime_utc, is_date_valid
from Utils.StandaloneUtils import get_exif_tool_path


class ClassFileDates:
    def __init__(self, data=None, logger=None):
        """
        Inicializa la clase con una lista de diccionarios.
        Cada diccionario debe tener al menos 'SourceFile'.
        """
        self.logger = logger
        self.data = data if data else []
        self.index = {}
        if self.data:
            self._build_index()

    def _build_index(self):
        """
        Construye el índice para búsquedas rápidas.
        Si existe 'TargetFile', se prioriza sobre 'SourceFile'.
        """
        self.index.clear()
        for item in self.data:
            source = item.get("SourceFile")
            target = item.get("TargetFile")

            if target:
                self.index[target] = item
            elif source:
                self.index[source] = item

        if self.logger:
            self.logger.debug(f"Índice creado con {len(self.index)} elementos.")

    def get_attribute(self, file_path: str, attr: Union[str, list] = "SelectedDate", step_name: str = "", log_level=None):
        """
        Busca un archivo en el índice y devuelve uno o varios atributos.
        """
        item = self.index.get(file_path)
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

    def update_target_file(self, current_path: str, new_target_path: str, step_name: str = ""):
        """
        Actualiza o asigna 'TargetFile' a un archivo identificado por su ruta actual
        (ya sea la ruta original en 'SourceFile' o la última ruta en 'TargetFile').
        """
        item = self.index.get(current_path)
        if not item:
            if self.logger:
                self.logger.warning(f"{step_name}No se encontró el archivo por '{current_path}'")
            return False

        # Elimina la ruta antigua de TargetFile si existía
        old_target = item.get("TargetFile")
        if old_target and old_target in self.index:
            del self.index[old_target]

        # Asigna el nuevo TargetFile y actualiza el índice
        item["TargetFile"] = new_target_path
        self.index[new_target_path] = item

        if self.logger:
            self.logger.info(f"{step_name}TargetFile actualizado: {current_path} → {new_target_path}")
        return True

    def bulk_update_folder(self, old_folder: str, new_folder: str, step_name: str = ""):
        """
        Actualiza en bloque todos los archivos cuyo 'TargetFile' o 'SourceFile' empiece por old_folder.
        """
        count = 0
        for item in self.data:
            current_path = item.get("TargetFile") or item.get("SourceFile")
            if current_path and current_path.startswith(old_folder):
                new_target = current_path.replace(old_folder, new_folder, 1)

                if current_path in self.index:
                    del self.index[current_path]

                item["TargetFile"] = new_target
                self.index[new_target] = item
                count += 1

        if self.logger:
            self.logger.info(f"{step_name}Se actualizaron {count} rutas TargetFile: {old_folder} → {new_folder}")
        return count

    def has_been_renamed(self, file_path: str) -> bool:
        """
        Devuelve True si el archivo fue renombrado (tiene 'TargetFile').
        """
        item = self.index.get(file_path)
        return bool(item and "TargetFile" in item)

    def save_to_json(self, filepath: str):
        """
        Guarda la lista de diccionarios en un archivo JSON.
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        if self.logger:
            self.logger.info(f"Guardado en JSON: {filepath}")

    def load_from_json(self, filepath: str):
        """
        Carga la lista de diccionarios desde un archivo JSON y reconstruye el índice.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self._build_index()

        if self.logger:
            self.logger.info(f"Cargado desde JSON: {filepath}")

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
                entry = self.index.get(src)
                if not entry:
                    entry = {"SourceFile": src}
                    self.data.append(entry)
                entry["SelectedDate"] = result["SelectedDate"]
                entry["Source"] = result["Source"]
                self.index[src] = entry
                updated += 1

            if self.logger:
                self.logger.info(f"{step_name}🧪 Fechas extraídas y aplicadas a {updated} archivos.")