import functools
import logging
import os
import re
import shutil
import sys
import threading
import time
import traceback
import unicodedata
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty
from typing import Union, cast

from Core.CustomLogger import set_log_level, CustomInMemoryLogHandler, CustomConsoleFormatter, get_logger_filename
from Core.GlobalVariables import TOOL_NAME_VERSION, TOOL_VERSION, ARGS, HELP_TEXTS, MSG_TAGS, TIMESTAMP, LOGGER, FOLDERNAME_LOGS, TOOL_DATE, FOLDERNAME_EXTRACTED_DATES
from Features.GoogleTakeout.ClassTakeoutFolder import ClassLocalFolder, ClassTakeoutFolder, contains_takeout_structure
from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
from Features.GooglePhotos.ClassGooglePhotos import ClassGooglePhotos
from Features.NextCloudPhotos.ClassNextCloudPhotos import ClassNextCloudPhotos
from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos
from Utils.FileUtils import remove_empty_dirs, contains_zip_files, normalize_path
from Utils.GeneralUtils import confirm_continue, TQDM_DASHBOARD_PREFIX, TQDM_DASHBOARD_META_PREFIX
from Utils.StandaloneUtils import change_working_dir, resolve_external_path

terminal_width = shutil.get_terminal_size().columns


class SharedData:
    def __init__(self, info, counters, logs_queue):
        self.info = info
        self.counters = counters
        self.logs_queue = logs_queue


def _pull_has_content(pulled_result) -> bool:
    if isinstance(pulled_result, bool):
        return pulled_result
    if isinstance(pulled_result, (int, float)):
        return pulled_result > 0
    if isinstance(pulled_result, str):
        return bool(pulled_result.strip())
    if isinstance(pulled_result, (list, tuple, set, dict)):
        return len(pulled_result) > 0
    return bool(pulled_result)


def _is_nextcloud_photo_not_found_error(error: Exception) -> bool:
    return "photo not found for user" in str(error or "").lower()


def restore_log_info_on_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # En caso de cualquier excepción, forzamos INFO
            LOGGER.setLevel(logging.INFO)
            LOGGER.exception("Excepción capturada: nivel de log restaurado a INFO")
            # Re-levantamos para no silenciar el error
            raise
    return wrapper


####################################
# FEATURE: AUTOMATIC-MIGRATION: #
####################################
def mode_AUTOMATIC_MIGRATION(source=None, target=None, show_dashboard=None, show_gpth_info=None, show_gpth_errors=None, parallel=None, log_level=None):
    with set_log_level(LOGGER, log_level):
        # ───────────────────────────────────────────────────────────────
        # Declare shared variables to pass as reference to both functions
        # ───────────────────────────────────────────────────────────────

        # Inicializamos start_time para medir el tiempo de procesamiento
        start_time = datetime.now()

        # Cola que contendrá los mensajes de log en memoria
        logs_queue = Queue()

        # Contadores globales
        counters = {
            'total_pulled_assets': 0,
            'total_pulled_photos': 0,
            'total_pulled_videos': 0,
            'total_pulled_albums': 0,
            'total_pull_failed_assets': 0,
            'total_pull_failed_photos': 0,
            'total_pull_failed_videos': 0,
            'total_pull_failed_albums': 0,
            'total_albums_blocked': 0,
            'total_assets_blocked': 0,

            'total_pushed_assets': 0,
            'total_pushed_photos': 0,
            'total_pushed_videos': 0,
            'total_pushed_albums': 0,
            'total_push_failed_assets': 0,
            'total_push_failed_photos': 0,
            'total_push_failed_videos': 0,
            'total_push_failed_albums': 0,
            'total_push_duplicates_assets': 0,
        }

        # Input INFO
        input_info = {
            "source_client_name": "Source Client",
            "target_client_name": "Target Client",
            "total_assets": 0,
            "total_photos": 0,
            "total_videos": 0,
            "total_albums": 0,
            "total_albums_blocked": 0,
            "total_metadata": 0,
            "total_sidecar": 0,
            "total_invalid": 0,
            "assets_in_queue": 0,
            "elapsed_time": 0,
            "start_time": start_time
        }

        SHARED_DATA = SharedData(input_info, counters, logs_queue)

        # Check if parallel=None, and in that case, get it from ARGS
        if parallel is None: parallel = ARGS['parallel-migration']

        # Detect source and target from the given arguments if have not been provided on the function call
        if not source: source = ARGS['source']
        if not target: target = ARGS['target']

        # Detect show_dashboard from the given arguments if it has not been provided on the function call
        if show_dashboard is None: show_dashboard = ARGS['dashboard']

        # Detect show_gpth_info and show_gpth_errors from the given arguments if it has not been provided on the function call
        if show_gpth_info is None: show_gpth_info = ARGS['show-gpth-info']
        if show_gpth_errors is None: show_gpth_errors = ARGS['show-gpth-errors']

        # Define the INTERMEDIATE_FOLDER
        INTERMEDIATE_FOLDER = resolve_external_path(f'./Automatic_Migration_Push_Failed_{TIMESTAMP}')

        # ---------------------------------------------------------------------------------------------------------
        # 1) Creamos los objetos source_client y target_client en función de los argumentos source y target
        # ---------------------------------------------------------------------------------------------------------
        def get_client_object(client_type):
            """Retorna la instancia del cliente en función del tipo de fuente o destino."""

            # Return ClassSynologyPhotos
            if client_type.lower() in ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1'] and not ARGS['account-id'] > 1:
                return ClassSynologyPhotos(account_id=1)
            elif client_type.lower() in ['synology-photos-2', 'synology-photos2', 'synology-2', 'synology2']:
                return ClassSynologyPhotos(account_id=2)
            elif client_type.lower() in ['synology-photos-3', 'synology-photos3', 'synology-3', 'synology3']:
                return ClassSynologyPhotos(account_id=3)
            elif client_type.lower() in ['synology-photos', 'synology'] and ARGS['account-id'] > 1:
                return ClassSynologyPhotos(account_id=ARGS['account-id'])

            # Return ClassImmichPhotos
            elif client_type.lower() in ['immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1'] and not ARGS['account-id'] > 1:
                return ClassImmichPhotos(account_id=1)
            elif client_type.lower() in ['immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']:
                return ClassImmichPhotos(account_id=2)
            elif client_type.lower() in ['immich-photos-3', 'immich-photos3', 'immich-3', 'immich3']:
                return ClassImmichPhotos(account_id=3)
            elif client_type.lower() in ['immich-photos', 'immich'] and ARGS['account-id'] > 1:
                return ClassImmichPhotos(account_id=ARGS['account-id'])

            # Return ClassNextCloudPhotos
            elif client_type.lower() in ['nextcloud-photos', 'nextcloud', 'nextcloud-photos-1', 'nextcloud-photos1', 'nextcloud-1', 'nextcloud1'] and not ARGS['account-id'] > 1:
                return ClassNextCloudPhotos(account_id=1)
            elif client_type.lower() in ['nextcloud-photos-2', 'nextcloud-photos2', 'nextcloud-2', 'nextcloud2']:
                return ClassNextCloudPhotos(account_id=2)
            elif client_type.lower() in ['nextcloud-photos-3', 'nextcloud-photos3', 'nextcloud-3', 'nextcloud3']:
                return ClassNextCloudPhotos(account_id=3)
            elif client_type.lower() in ['nextcloud-photos', 'nextcloud'] and ARGS['account-id'] > 1:
                return ClassNextCloudPhotos(account_id=ARGS['account-id'])

            # Return ClassGooglePhotos
            elif client_type.lower() in ['google-photos', 'googlephotos', 'google-photos-1', 'googlephotos-1', 'google-1', 'google1'] and not ARGS['account-id'] > 1:
                return ClassGooglePhotos(account_id=1)
            elif client_type.lower() in ['google-photos-2', 'googlephotos-2', 'google-2', 'google2']:
                return ClassGooglePhotos(account_id=2)
            elif client_type.lower() in ['google-photos-3', 'googlephotos-3', 'google-3', 'google3']:
                return ClassGooglePhotos(account_id=3)
            elif client_type.lower() in ['google-photos', 'googlephotos'] and ARGS['account-id'] > 1:
                return ClassGooglePhotos(account_id=ARGS['account-id'])

            # Return ClassTakeoutFolder
            elif Path(client_type).is_dir() and (contains_zip_files(client_type, log_level=logging.WARNING) or contains_takeout_structure(client_type, log_level=logging.INFO)):
                return ClassTakeoutFolder(client_type)  # In this clase, client_type is the path to the Takeout Folder

            # Return ClassLocalFolder
            elif Path(client_type).is_dir():
                return ClassLocalFolder(base_folder=client_type)  # In this clase, client_type is the path to the base Local Folder
            else:
                raise ValueError(f"{MSG_TAGS['ERROR']}Tipo de cliente no válido: {client_type}")

        # Creamos los objetos source_client y target_client y obtenemos sus nombres para mostrar en el show_dashboard
        source_client = get_client_object(source)
        source_client_name = source_client.get_client_name()
        SHARED_DATA.info.update({"source_client_name": source_client_name})

        target_client = get_client_object(target)
        target_client_name = target_client.get_client_name()
        SHARED_DATA.info.update({"target_client_name": target_client_name})

        # Check if source_client support specified filters
        unsupported_text = ""
        if isinstance(source_client, ClassTakeoutFolder) or isinstance(source_client, ClassLocalFolder):
            unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

        # Check if '-move, --move-assets' have been passed as argument
        move_assets = ARGS.get('move-assets', False)

        # Get the values from the arguments (if exists)
        type = ARGS.get('filter-by-type', None)
        from_date = ARGS.get('filter-from-date', None)
        to_date = ARGS.get('filter-to-date', None)
        country = ARGS.get('filter-by-country', None)
        city = ARGS.get('filter-by-city', None)
        person = ARGS.get('filter-by-person', None)

        LOGGER.info(f"")
        LOGGER.info(f"*** Automatic Migration Mode *** detected")
        LOGGER.info('-' * (terminal_width-10))
        if not isinstance(source_client, ClassTakeoutFolder):
            LOGGER.warning(HELP_TEXTS["AUTOMATIC-MIGRATION"].replace('<SOURCE>', f"'{source}'").replace('<TARGET>', f"'{target}'"))
        else:
            LOGGER.warning(HELP_TEXTS["AUTOMATIC-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{source}'").replace('<TARGET>', f"'{target}'").replace('Pulling', 'Analyzing and Fixing'))
        LOGGER.info('-' * (terminal_width-10))
        LOGGER.info(f"Source Client  : {source_client_name}")
        LOGGER.info(f"Target Client  : {target_client_name}")
        LOGGER.info(f"Temp Folder    : {INTERMEDIATE_FOLDER}")

        if parallel:
            LOGGER.info(f"Migration Mode : Parallel")
        else:
            LOGGER.info(f"Migration Mode : Sequential")

        LOGGER.info(f"Move Assets    : {move_assets}")

        if from_date or to_date or type or country or city or person:
            LOGGER.info(f"Assets Filters :")
        else:
            LOGGER.info(f"Assets Filters : None")
        if from_date:
            date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"     from Date : {date_obj.strftime('%Y-%m-%d')}")
        if to_date:
            date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"       to Date : {date_obj.strftime('%Y-%m-%d')}")
        if type:
            LOGGER.info(f"       by Type : {type}")
        if country:
            LOGGER.info(f"    by Country : {country} {unsupported_text}")
        if city:
            LOGGER.info(f"       by City : {city} {unsupported_text}")
        if person:
            LOGGER.info(f"     by Person : {person} {unsupported_text}")

        LOGGER.info(f"")
        if not confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
            # Call the parallel_automatic_migration module to do the whole migration process
            # parallel_automatic_migration(source, target, temp_folder, SHARED_DATA.input_info, SHARED_DATA.counters, SHARED_DATA.logs_queue)
            # and if show_dashboard=True, launch start_dashboard function to show a Live Dashboard of the whole process
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

            # ---------------------------------------------------------------------------------------------------------
            # 1) Creamos un evento para indicar cuándo termina la migración
            migration_finished = threading.Event()
            # ---------------------------------------------------------------------------------------------------------

            # ------------------------------------------------------------------------------------------------------
            # 2) Lanzamos el start_dashboard en un hilo secundario (o viceversa).
            # ------------------------------------------------------------------------------------------------------
            if show_dashboard:
                dashboard_thread = threading.Thread(
                    target=start_dashboard,
                    kwargs={
                        "migration_finished": migration_finished,  # Pasamos un evento para indicar cuando ha terminado el proceso de migración
                        "SHARED_DATA": SHARED_DATA,  # Pasamos la instancia de la clase
                        "parallel": parallel,  # Pasamos el modo de migración (parallel=True/False)
                        "log_level": logging.INFO
                    },
                    daemon=True  # El show_dashboard se cierra si el proceso principal termina
                )
                dashboard_thread.start()

                # Pequeña espera para garantizar que el show_dashboard ha arrancado antes de la migración
                time.sleep(2)

            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"🚀 AUTOMATIC MIGRATION JOB STARTED - {source_client_name} ➜ {target_client_name}")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")

            # ------------------------------------------------------------------------------------------------------
            # 3) Verifica y procesa source_client y target_client si es una instancia de ClassTakeoutFolder
            print_messages = False if show_dashboard else True
            if isinstance(source_client, ClassTakeoutFolder):
                if source_client.needs_unzip or source_client.needs_process:
                    LOGGER.info(f"🔢 Source Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")

                    # Process the Takeout if needed
                    source_client.process(capture_output=show_gpth_info, capture_errors=show_gpth_errors, print_messages=print_messages)

                    # Ensure object analyzer from class FolderAnalyzer is created on source_client when source_client is ClassTakeout instance
                    output_metadata_json = os.path.join(FOLDERNAME_EXTRACTED_DATES, f"{TIMESTAMP}_takeout_output_dates_metadata_final.json")
                    if os.path.isfile(output_metadata_json):
                        source_client._ensure_analyzer(metadata_json_file=output_metadata_json,  log_level=log_level)
                    else:
                        source_client._ensure_analyzer(log_level=log_level)

            if isinstance(target_client, ClassTakeoutFolder):
                if target_client.needs_unzip or target_client.needs_process:
                    LOGGER.info(f"🔢 Target Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")
                    target_client.process(capture_output=show_gpth_info, capture_errors=show_gpth_errors, print_messages=print_messages)

            # ---------------------------------------------------------------------------------------------------------
            # 4) Ejecutamos la migración en el hilo principal (ya sea con descargas y subidas en paralelo o secuencial)
            # ---------------------------------------------------------------------------------------------------------
            try:
                parallel_automatic_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, parallel=parallel, log_level=logging.INFO)
            except Exception:
                # 1) Mostrar el stack trace completo en stderr (o stdout)
                traceback.print_exc()
                # 2) Registrar en el logger con stack trace
                LOGGER.exception("ERROR executing Automatic Migration Feature")
            finally:
                migration_finished.set()

            # ---------------------------------------------------------------------------------------------------------
            # 5) Cuando la migración termine, notificamos al show_dashboard
            migration_finished.set()
            # ---------------------------------------------------------------------------------------------------------

            # ---------------------------------------------------------------------------------------------------------
            # 6) Esperamos a que el show_dashboard termine (si sigue corriendo después de la migración)
            # ---------------------------------------------------------------------------------------------------------
            if show_dashboard:
                dashboard_thread.join()


#########################################
# parallel_automatic_migration Function #
#########################################
# @restore_log_info_on_exception
def parallel_automatic_migration(source_client, target_client, temp_folder, SHARED_DATA, parallel=None, log_level=logging.INFO):
    """
    Sincroniza fotos y vídeos entre un 'source_client' y un 'destination_client',
    descargando álbumes y assets desde la fuente, y luego subiéndolos a destino,
    de forma concurrente mediante una cola de proceso.

    Parámetros:
    -----------
    source_client: objeto con los métodos:
        - get_client_name()
        - get_albums_including_shared_with_user() -> [ { 'id': ..., 'name': ... }, ... ]
        - get_all_assets_from_all_albums() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_without_albums() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_from_album(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_from_album_shared(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - pull_asset(asset_id, download_path) -> str (ruta local del archivo descargado)

    target_client: objeto con los métodos:
        - get_client_name()
        - album_exists(album_name) -> (bool, album_id_o_None)
        - create_album(album_name) -> album_id
        - add_asset_to_album(album_id, asset_id) -> None
        - push_asset(asset_file_path, asset_datetime) -> asset_id

    temp_folder: str
        Carpeta temporal donde se descargarán los assets antes de subirse.
    """

    # Protector para que no se pisen las actualizaciones de métricas
    metrics_lock = threading.Lock()
    class MonitoredQueue(Queue):
        def put(self, item, *args, **kwargs):
            super().put(item, *args, **kwargs)
            with metrics_lock:
                SHARED_DATA.info['assets_in_queue'] = self.qsize()

        def get(self, *args, **kwargs):
            item = super().get(*args, **kwargs)
            with metrics_lock:
                SHARED_DATA.info['assets_in_queue'] = self.qsize()
            return item

    # -------------------------------------------------------------------
    # Variables compartidas para controlar la creación de álbumes
    # -------------------------------------------------------------------
    # Creamos un diccionario created_albums (protegido por candado para evitar condiciones de carrera entre workers) para registrar los albums que ya han sido creados y de este modo evitar que un album se cree 2 o más veces por varios workers en paralelo.
    album_creation_lock = threading.Lock()
    created_albums = {}
    immich_uploaded_records = []
    immich_uploaded_records_lock = threading.Lock()

    # ----------------------------------------------------------------------------------------
    # function to ensure that the puller put only 1 asset with the same filepath to the queue
    # ----------------------------------------------------------------------------------------
    def enqueue_unique(push_queue, item_dict, parallel=True):
        """
        Añade item_dict a la cola si su asset_file_path no ha sido añadido previamente.
        Thread-safe gracias al lock global.
        """
        with file_paths_lock:
            asset_file_path = item_dict['asset_file_path']
            SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

            if asset_file_path in added_file_paths:
                # El item ya fue añadido anteriormente
                return False

            # If parallel mode, then manage waiting time to avoid queue size go beyond 100 elements.
            if parallel:
                # Pausa si la cola tiene más de 100 elementos, pero no bloquea innecesariamente, y reanuda cuando tenga 10.
                while push_queue.qsize() >= 100:
                    while push_queue.qsize() > 25:
                        time.sleep(1)  # Hacemos pausas de 1s hasta que la cola se vacíe (25 elementos)
                        # SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

                # Si la cola está muy llena (entre 50 y 100), reducir la velocidad en vez de bloquear
                if push_queue.qsize() > 50:
                    time.sleep(0.1)  # Pequeña pausa para no sobrecargar la cola
                    pass

            # Añadir a la cola y al registro global
            push_queue.put(item_dict)
            added_file_paths.add(asset_file_path)
            return True

    def is_asset_in_queue(queue, path):
        """Comprueba si el path está presente en la cola (sin distinguir mayúsculas/minúsculas)."""
        with queue.mutex:
            return any(item['asset_file_path'].lower() == path.lower() for item in list(queue.queue))

    def infer_asset_type_from_path(file_path, fallback_type):
        """Infers media type from extension; falls back to source type when unknown."""
        ext = os.path.splitext(file_path)[1].lower()
        source_video_exts = [e.lower() for e in getattr(source_client, "ALLOWED_VIDEO_EXTENSIONS", [])]
        source_photo_exts = [e.lower() for e in getattr(source_client, "ALLOWED_PHOTO_EXTENSIONS", [])]
        if ext in source_video_exts:
            return "video"
        if ext in source_photo_exts:
            return "photo"
        return fallback_type

    def collect_pulled_asset_paths(download_folder, asset_filename):
        """
        Returns pulled file paths for one logical asset.
        For Synology Live Photo ZIP payloads, this includes companion video files sharing the same stem.
        """
        primary_path = os.path.join(download_folder, asset_filename)
        stem = os.path.splitext(asset_filename)[0]
        found = []

        # Resolve actual filename case from directory entries (important on Linux/NAS).
        try:
            entries = os.listdir(download_folder)
        except Exception:
            entries = []
        lower_to_real = {name.lower(): name for name in entries}

        primary_real_name = lower_to_real.get(asset_filename.lower())
        if primary_real_name:
            primary_path = os.path.join(download_folder, primary_real_name)

        if os.path.exists(primary_path):
            found.append(primary_path)

        source_video_exts = [e.lower() for e in getattr(source_client, "ALLOWED_VIDEO_EXTENSIONS", [])]
        stem_lower = stem.lower()
        for entry in entries:
            entry_base, entry_ext = os.path.splitext(entry)
            if entry_base.lower() != stem_lower:
                continue
            if entry_ext.lower() not in source_video_exts:
                continue
            companion = os.path.join(download_folder, entry)
            if companion.lower() != primary_path.lower():
                found.append(companion)

        return found

    def path_key(path):
        """
        OS-agnostic normalized key for case-insensitive path comparisons.
        """
        return os.path.normpath(path).replace("\\", "/").lower()

    def resolve_existing_path_case_insensitive(path):
        """
        Resolve an existing path even if provided filename casing does not match filesystem entry.
        """
        if not path:
            return path
        if os.path.exists(path):
            return path
        folder = os.path.dirname(path) or "."
        wanted_name = os.path.basename(path)
        try:
            for entry in os.listdir(folder):
                if entry.lower() == wanted_name.lower():
                    candidate = os.path.join(folder, entry)
                    if os.path.exists(candidate):
                        return candidate
        except Exception:
            pass
        return path

    def safe_remove_local_file(path, retries=3, delay_s=0.15):
        """
        Try to remove a local file with small retries (Windows/NAS transient locks).
        """
        if not path:
            return True
        resolved = resolve_existing_path_case_insensitive(path)
        if not os.path.exists(resolved):
            return True
        last_exc = None
        for _ in range(max(1, retries)):
            try:
                os.remove(resolved)
                return True
            except Exception as e:
                last_exc = e
                time.sleep(delay_s)
        LOGGER.warning(f"Could not remove file '{resolved}': {last_exc}")
        return False

    def find_immich_live_video_companion(photo_file_path, pulled_file_paths):
        """
        Finds the companion video path for a given photo path within pulled files when target is Immich.
        """
        if not isinstance(target_client, ClassImmichPhotos):
            return None
        photo_ext = os.path.splitext(photo_file_path)[1].lower()
        if photo_ext not in ['.heic', '.heif', '.jpg', '.jpeg']:
            return None
        photo_stem = os.path.splitext(photo_file_path)[0]
        candidate_paths = {path_key(p): p for p in pulled_file_paths}
        for video_ext in (getattr(target_client, "ALLOWED_IMMICH_VIDEO_EXTENSIONS", []) or []):
            candidate_norm = path_key(f"{photo_stem}{video_ext.lower()}")
            if candidate_norm in candidate_paths:
                return candidate_paths[candidate_norm]
        return None

    def parse_capture_epoch(asset_datetime):
        if isinstance(asset_datetime, (int, float)):
            return float(asset_datetime)
        if isinstance(asset_datetime, str):
            try:
                return datetime.fromisoformat(asset_datetime.replace("Z", "+00:00")).timestamp()
            except Exception:
                return None
        return None

    # ------------------
    # 1) HILO PRINCIPAL
    # ------------------
    def main_thread(parallel=None, log_level=logging.INFO):
        def is_unsupported_source(client) -> bool:
            return isinstance(client, (ClassTakeoutFolder, ClassLocalFolder))

        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # Get Log_filename
            log_file = get_logger_filename(LOGGER)

            # Get source and target client names
            source_client_name = source_client.get_client_name()
            target_client_name = target_client.get_client_name()

            # Check if source_client support specified filters
            unsupported_text = ""
            if is_unsupported_source(source_client):
                unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

            # Check if '-move, --move-assets' have been passed as argument
            move_assets = ARGS.get('move-assets', False)

            # Check if there is some filter applied
            with_filters = False
            if ARGS.get('filter-by-type', None) or ARGS.get('filter-from-date', None) or ARGS.get('filter-to-date', None) or ARGS.get('filter-by-country', None) or ARGS.get('filter-by-city', None) or ARGS.get('filter-by-person', None):
                with_filters = True

            # Get the values from the arguments (if exists)
            type = ARGS.get('filter-by-type', None)
            from_date = ARGS.get('filter-from-date', None)
            to_date = ARGS.get('filter-to-date', None)
            country = ARGS.get('filter-by-country', None)
            city = ARGS.get('filter-by-city', None)
            person = ARGS.get('filter-by-person', None)

            LOGGER.info(f"🚀 Starting Automatic Migration Process: {source_client_name} ➜ {target_client_name}...")
            LOGGER.info(f"Source Client  : {source_client_name}")
            LOGGER.info(f"Target Client  : {target_client_name}")
            LOGGER.info(f"Temp Folder    : {temp_folder}")
            LOGGER.info(f"Log File       : {log_file}")

            if parallel:
                LOGGER.info(f"Migration Mode : Parallel")
            else:
                LOGGER.info(f"Migration Mode : Sequential")

            LOGGER.info(f"Move Assets    : {move_assets}")

            LOGGER.info(f"")
            if from_date or to_date or type or country or city or person:
                LOGGER.info(f"Assets Filters :")
            else:
                LOGGER.info(f"Assets Filters : None")
            if from_date:
                date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"     from Date : {date_obj.strftime('%Y-%m-%d')}")
            if to_date:
                date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"       to Date : {date_obj.strftime('%Y-%m-%d')}")
            if type:
                LOGGER.info(f"       by Type : {type}")
            if country:
                LOGGER.info(f"    by Country : {country} {unsupported_text}")
            if city:
                LOGGER.info(f"       by City : {city} {unsupported_text}")
            if person:
                LOGGER.info(f"     by Person : {person} {unsupported_text}")

            LOGGER.info(f"")
            LOGGER.info(f"Starting Pulling/Pushing Workers...")
            LOGGER.info(f"Analyzing Source client and Applying filters. This process may take some time, please be patient...")

            # Get source client statistics:
            blocked_assets = []
            total_albums_blocked_count = 0
            total_assets_blocked_count = 0
            all_albums = []
            try:
                LOGGER.info(f"Retrieving Albums on '{source_client_name}' matching filters criteria (if any). This process may take some time, please be patient...")
                all_albums = source_client.get_albums_including_shared_with_user(filter_assets=with_filters, log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Albums from '{source_client_name}'. - {e}")

            # Defensive dedupe for NextCloud sources:
            # when same logical album exists both as native PhotosDAV album and as folder album,
            # keep only one (prefer native).
            if isinstance(source_client, ClassNextCloudPhotos):
                def _album_key(name: str) -> str:
                    normalized = unicodedata.normalize("NFKC", str(name or "")).casefold().strip()
                    normalized = re.sub(r"^\d+[-_\s]+", "", normalized).strip()
                    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
                    normalized = re.sub(r"\s*\((copy|\d+)\)\s*$", "", normalized).strip()
                    normalized = re.sub(r"\s+", " ", normalized).strip()
                    return normalized

                dedup: dict[str, dict] = {}
                for album in all_albums:
                    key = _album_key(album.get("albumName", ""))
                    if not key:
                        continue
                    existing = dedup.get(key)
                    if existing is None:
                        dedup[key] = album
                        continue
                    existing_ns = str(existing.get("source_namespace", "")).strip().lower()
                    current_ns = str(album.get("source_namespace", "")).strip().lower()
                    if current_ns == "photos" and existing_ns != "photos":
                        dedup[key] = album
                if len(dedup) != len(all_albums):
                    LOGGER.info(
                        f"NextCloud albums deduplicated by name: before={len(all_albums)}, after={len(dedup)}"
                    )
                all_albums = sorted(list(dedup.values()), key=lambda a: str(a.get("albumName", "")).lower())

            LOGGER.info(f"{len(all_albums)} Albums found on '{source_client_name}' matching filters criteria")
            for album in all_albums:
                album_id = album['id']
                album_name = album['albumName']
                album_passphrase = album.get('passphrase')  # Obtiene el valor si existe, si no, devuelve None
                permissions = album.get('additional', {}).get('sharing_info', {}).get('permission', [])  # Obtiene el valor si existe, si no, devuelve None
                if permissions:
                    album_shared_role = permissions[0].get('role')  # Obtiene el valor si existe, si no, devuelve None
                else:
                    album_shared_role = ""  # O cualquier valor por defecto que desees
                if album_shared_role.lower() == 'view':
                    LOGGER.info(f"Album '{album_name}' cannot be pulled because is a blocked shared album. Skipped!")
                    total_albums_blocked_count += 1
                    total_assets_blocked_count += album.get('item_count')
                    try:
                        blocked_assets.extend(source_client.get_all_assets_from_album_shared(album_id=album_id, album_name=album_name, album_passphrase=album_passphrase, log_level=logging.WARNING))
                    except Exception as e:
                        LOGGER.error(f"Error Retrieving Shared Albums's Assets from '{source_client_name}' - {e}")
            # Get all assets and filter out those blocked assets (from blocked shared albums) if any
            all_no_albums_assets = []
            try:
                all_no_albums_assets = source_client.get_all_assets_without_albums(log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving Assets without albums from '{source_client_name}' - {e}")
            all_albums_assets = []
            try:
                all_albums_assets = source_client.get_all_assets_from_all_albums(log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving Albums's Assets from '{source_client_name}' - {e}")

            all_supported_assets = all_no_albums_assets + all_albums_assets
            blocked_assets_ids = {asset["id"] for asset in blocked_assets}
            filtered_all_supported_assets = [asset for asset in all_supported_assets if asset["id"] not in blocked_assets_ids]

            all_photos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in image_labels]
            all_videos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in video_labels]
            all_assets = all_photos + all_videos
            all_metadata = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in metadata_labels]
            all_sidecar = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in sidecar_labels]
            all_invalid = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['unknown']]

            SHARED_DATA.info.update({
                "total_assets": len(all_assets),
                "total_photos": len(all_photos),
                "total_videos": len(all_videos),
                "total_albums": len(all_albums),
                "total_albums_blocked": total_albums_blocked_count,
                "total_metadata": len(all_metadata),
                "total_sidecar": len(all_sidecar),
                "total_invalid": len(all_invalid),
            })

            SHARED_DATA.counters['total_albums_blocked'] = total_albums_blocked_count
            SHARED_DATA.counters['total_assets_blocked'] = total_assets_blocked_count

            LOGGER.info(f"Input Info Analysis: ")
            for key, value in SHARED_DATA.info.items():
                LOGGER.info(f"   {key}: {value}")

            # Delete unneeded vars to clean memory
            del all_albums
            del all_supported_assets
            del blocked_assets_ids
            del filtered_all_supported_assets
            del all_assets
            del all_photos
            del all_videos
            del all_metadata
            del all_sidecar
            del all_invalid

            # Lista para marcar álbumes procesados (ya contados y/o creados en el destino)
            processed_albums = []

            # ------------------------------------------------------------------------------------------------------
            # 1) Iniciar uno o varios hilos de pull y push para manejar los pull y push concurrentes
            # ------------------------------------------------------------------------------------------------------
            # Obtain the number of Threads for the CPU and launch as many Push workers as max(1, int(cpu_total_threads*2))
            cpu_total_threads = os.cpu_count()
            LOGGER.info(f"")
            LOGGER.info(f"CPU Total Cores Detected = {cpu_total_threads}")
            num_pull_threads = 1  # no Iniciar más de 1 hilo de descarga, de lo contrario los assets se descargarán multiples veces.
            LOGGER.info(f"Launching {num_pull_threads} Pull worker in parallel...")
            num_push_threads = max(1, int(cpu_total_threads * 2))
            LOGGER.info(f"Launching {num_push_threads} Push workers in parallel...")

            pull_threads = [threading.Thread(target=puller_worker, kwargs={"parallel": parallel}, daemon=True) for _ in range(num_pull_threads)]
            push_threads = [threading.Thread(target=pusher_worker, kwargs={"processed_albums": processed_albums, "worker_id": worker_id + 1}, daemon=True) for worker_id in range(num_push_threads)]

            # 1) Arrancar pullers
            for t in pull_threads:
                t.start()

            # 2) Si modo paralelo, arranca ya los pushers
            if parallel:
                for t in push_threads:
                    t.start()

            # 3) Esperar a que terminen los pullers
            for t in pull_threads:
                t.join()

            # 4) Si modo secuencial, ahora sí arranca los pushers
            if not parallel:
                for t in push_threads:
                    t.start()

            # 5) Esperar a que la cola se vacíe (assets reales y todos los re‑enqueues)
            push_queue.join()

            # 6) Inyectar un None por cada pusher para que lean la señal de fin
            for _ in range(num_push_threads):
                push_queue.put(None)

            # 7) Esperar a que los pushers consuman su None y terminen
            for t in push_threads:
                t.join()

            # En este punto todos los pulls y pushs están listas y la cola está vacía.

            # Auto-stack burst photos in Immich target using uploaded records.
            if isinstance(target_client, ClassImmichPhotos):
                try:
                    target_client.auto_stack_bursts(immich_uploaded_records, context_label="Automatic Migration", log_level=logging.INFO)
                except Exception as e:
                    LOGGER.warning(f"Unable to auto-stack bursts in Immich after migration: {e}")

            # Finalmente, borrar carpetas vacías que queden en temp_folder
            remove_empty_dirs(temp_folder)

            end_time = datetime.now()
            migration_formatted_duration = str(timedelta(seconds=round((end_time - migration_start_time).total_seconds())))
            total_formatted_duration = str(timedelta(seconds=round((end_time - SHARED_DATA.info["start_time"]).total_seconds())))

            # ----------------------------------------------------------------------------
            # 4) Mostrar o retornar contadores
            # ----------------------------------------------------------------------------
            LOGGER.info(f"")
            total_failed_assets = (
                SHARED_DATA.counters['total_pull_failed_assets']
                + SHARED_DATA.counters['total_push_failed_assets']
            )
            if total_failed_assets > 0:
                LOGGER.warning(f"{MSG_TAGS['WARNING']}Migration finished with partial failures.")
            else:
                LOGGER.info(f"🚀 All assets pulled and pushed successfully!")
            LOGGER.info(f"")
            LOGGER.info(f"----- MIGRATION FINISHED  -----")
            LOGGER.info(f"{source_client_name} --> {target_client_name}")
            LOGGER.info(f"Pulled Albums               : {SHARED_DATA.counters['total_pulled_albums']}")
            LOGGER.info(f"Pushed Albums               : {SHARED_DATA.counters['total_pushed_albums']}")
            LOGGER.info(f"Pulled Assets               : {SHARED_DATA.counters['total_pulled_assets']} (Photos: {SHARED_DATA.counters['total_pulled_photos']}, Videos: {SHARED_DATA.counters['total_pulled_videos']})")
            LOGGER.info(f"Pushed Assets               : {SHARED_DATA.counters['total_pushed_assets']} (Photos: {SHARED_DATA.counters['total_pushed_photos']}, Videos: {SHARED_DATA.counters['total_pushed_videos']})")
            LOGGER.info(f"Push Duplicates (skipped)   : {SHARED_DATA.counters['total_push_duplicates_assets']}")
            LOGGER.info(f"Pull Failed Assets          : {SHARED_DATA.counters['total_pull_failed_assets']}")
            LOGGER.info(f"Push Failed Assets          : {SHARED_DATA.counters['total_push_failed_assets']}")
            LOGGER.info(f"")
            LOGGER.info(f"Migration Job completed in  : {migration_formatted_duration}")
            LOGGER.info(f"Total Elapsed Time          : {total_formatted_duration}")
            LOGGER.info(f"")
            LOGGER.info(f"")
            return SHARED_DATA.counters

    # --------------------------------------------------------------------------------
    # 1) PULLER: Función puller_worker para descargar assets y poner en la cola
    # --------------------------------------------------------------------------------
    def puller_worker(parallel=None, log_level=logging.INFO):
        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"puller-{thread_id}")

        # Check if there is some filter applied
        with_filters = False
        if ARGS.get('filter-by-type', None) or ARGS.get('filter-from-date', None) or ARGS.get('filter-to-date', None) or ARGS.get('filter-by-country', None) or ARGS.get('filter-by-city', None) or ARGS.get('filter-by-person', None):
            with_filters = True

        with set_log_level(LOGGER, log_level):

            # 1.1) Descarga de álbumes
            albums = []
            try:
                albums = source_client.get_albums_including_shared_with_user(filter_assets=with_filters, log_level=logging.ERROR)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Albums - {e} \n{traceback.format_exc()}")
                LOGGER.info(f"Albums Assets Skipped")

            pulled_assets = 0
            for album in albums:
                album_assets = []
                album_id = album['id']
                album_name = album['albumName']
                album_passphrase = album.get('passphrase')  # Obtiene el valor si existe, si no, devuelve None
                permissions = album.get('additional', {}).get('sharing_info', {}).get('permission', [])  # Obtiene el valor si existe, si no, devuelve None
                if permissions:
                    album_shared_role = permissions[0].get('role')  # Obtiene el valor si existe, si no, devuelve None
                else:
                    album_shared_role = ""
                is_shared = album_passphrase is not None and album_passphrase != ""  # Si tiene passphrase, es compartido

                # Descargar todos los assets de este álbum
                try:
                    if not is_shared:
                        album_assets = source_client.get_all_assets_from_album(album_id=album_id, album_name=album_name, log_level=logging.ERROR)
                    else:
                        if album_shared_role.lower() != 'view':
                            album_assets = source_client.get_all_assets_from_album_shared(album_id=album_id, album_name=album_name, album_passphrase=album_passphrase, log_level=logging.ERROR)
                    if not album_assets:
                        # SHARED_DATA.counters['total_pull_failed_albums'] += 1     # If we uncomment this line, it will count as failed Empties albums
                        continue
                except Exception as e:
                    LOGGER.error(f"Error Retrieving All Assets from album {album_name} - {e} \n{traceback.format_exc()}")
                    SHARED_DATA.counters['total_pull_failed_albums'] += 1
                    continue

                # Crear carpeta del álbum dentro de temp_folder, y bloquea su eliminación hasta que terminen las descargas del album
                album_folder = os.path.join(temp_folder, album_name)
                os.makedirs(album_folder, exist_ok=True)
                # Crear archivo `.active` para marcar que la carpeta está en uso
                active_file = os.path.join(album_folder, ".active")
                with open(active_file, 'w') as lock_album_folder:
                    lock_album_folder.write("Pulling Album")
                try:
                    for asset in album_assets:
                        asset_id = asset['id']
                        asset_type = asset['type']
                        asset_datetime = asset.get('time')
                        asset_filename = asset.get('filename')

                        # Skip pull metadata and sidecar for the time being
                        if asset_type in ['metadata', 'sidecar']:
                            continue

                        # Ruta del archivo descargado
                        local_file_path = os.path.join(album_folder, asset_filename)

                        # Archivo de bloqueo temporal para que el pusher no borre el fichero mientras que el puller lo está creando
                        lock_file = local_file_path + ".lock"
                        # Crear archivo de bloqueo antes de la descarga
                        with open(lock_file, 'w') as lock:
                            lock.write("Pulling Asset")
                        # Descargar el asset (tolerante por-asset para no abortar todo el álbum).
                        skipped_not_found = False
                        try:
                            pulled_assets = source_client.pull_asset(
                                asset_id=asset_id,
                                asset_filename=asset_filename,
                                asset_time=asset_datetime,
                                download_folder=album_folder,
                                album_passphrase=album_passphrase,
                                log_level=logging.ERROR,
                            )
                        except Exception as e:
                            if _is_nextcloud_photo_not_found_error(e):
                                skipped_not_found = True
                                LOGGER.warning(
                                    f"Asset Pull Skip : '{os.path.basename(asset_filename)}' from Album '{album_name}' - "
                                    f"Photo not found for user"
                                )
                            else:
                                LOGGER.error(
                                    f"Asset Pull Error: '{os.path.basename(asset_filename)}' from Album '{album_name}' - {e}"
                                )
                            pulled_assets = 0
                        finally:
                            # Eliminar archivo de bloqueo después de la descarga
                            if os.path.exists(lock_file):
                                os.remove(lock_file)

                        # Actualizamos Contadores de descargas
                        if _pull_has_content(pulled_assets):
                            pulled_file_paths = collect_pulled_asset_paths(album_folder, asset_filename)
                            if not pulled_file_paths:
                                pulled_file_paths = [local_file_path]

                            immich_live_companion = find_immich_live_video_companion(local_file_path, pulled_file_paths)
                            for idx, pulled_file_path in enumerate(pulled_file_paths):
                                if immich_live_companion and path_key(pulled_file_path) == path_key(immich_live_companion):
                                    continue
                                normalized_asset_type = infer_asset_type_from_path(pulled_file_path, asset_type)
                                count_push_stats = (idx == 0)
                                LOGGER.info(f"Asset Pulled    : '{os.path.basename(pulled_file_path)}'")
                                SHARED_DATA.counters['total_pulled_assets'] += 1
                                if normalized_asset_type.lower() in video_labels:
                                    SHARED_DATA.counters['total_pulled_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_pulled_photos'] += 1

                                # Enviar a la cola con la información necesaria para la subida
                                asset_dict = {
                                    'asset_id': asset_id,
                                    'asset_file_path': pulled_file_path,
                                    'asset_datetime': asset_datetime,
                                    'asset_type': normalized_asset_type,
                                    'album_name': album_name,
                                    'count_push_stats': count_push_stats,
                                }
                                if immich_live_companion and path_key(pulled_file_path) == path_key(local_file_path):
                                    asset_dict['live_photo_video_path'] = immich_live_companion
                                # añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                                unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)
                                if not unique:
                                    LOGGER.info(f"Asset Duplicated: '{os.path.basename(pulled_file_path)}' from Album '{album_name}. Skipped")
                                    SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                    # Solo borramos si ya no está en la cola (ignorando mayúsculas)
                                    if not is_asset_in_queue(push_queue, pulled_file_path) and os.path.exists(pulled_file_path):
                                        safe_remove_local_file(pulled_file_path)
                                    companion_to_cleanup = asset_dict.get('live_photo_video_path')
                                    if companion_to_cleanup and os.path.exists(companion_to_cleanup):
                                        companion_lock = companion_to_cleanup + ".lock"
                                        if (not is_asset_in_queue(push_queue, companion_to_cleanup)) and (not os.path.exists(companion_lock)):
                                            safe_remove_local_file(companion_to_cleanup)
                        else:
                            if skipped_not_found:
                                SHARED_DATA.counters['total_pull_failed_assets'] += 1
                                if asset_type.lower() in video_labels:
                                    SHARED_DATA.counters['total_pull_failed_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_pull_failed_photos'] += 1
                                continue
                            LOGGER.warning(f"Asset Pull Fail : '{os.path.basename(local_file_path)}' from Album '{album_name}'")
                            SHARED_DATA.counters['total_pull_failed_assets'] += 1
                            if asset_type.lower() in video_labels:
                                SHARED_DATA.counters['total_pull_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pull_failed_photos'] += 1

                except Exception as e:
                    LOGGER.error(f"Album Pull Error: '{album_name}' - {e}")
                    SHARED_DATA.counters['total_pull_failed_albums'] += 1
                    continue
                finally:
                    # Eliminar archivo .active después de la descarga
                    if os.path.exists(active_file):
                        os.remove(active_file)

                # Incrementamos contador de álbumes descargados
                SHARED_DATA.counters['total_pulled_albums'] += 1
                LOGGER.info(f"Album Pulled    : '{album_name}'")

            # 1.2) Descarga de assets sin álbum
            assets_no_album = []
            try:
                assets_no_album = source_client.get_all_assets_without_albums(log_level=logging.ERROR)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Assets without Albums - {e} \n{traceback.format_exc()}")

            # Crear carpeta temp_folder si no existe, y bloquea su eliminación hasta que terminen las descargas
            os.makedirs(temp_folder, exist_ok=True)
            # Crear archivo `.active` para marcar que la carpeta está en uso
            active_file = os.path.join(temp_folder, ".active")
            with open(active_file, 'w') as lock_temp_folder:
                lock_temp_folder.write("Pulling Asset")
            try:
                pulled_assets = 0
                for asset in assets_no_album:
                    asset_id = asset['id']
                    asset_type = asset['type']
                    asset_datetime = asset.get('time')
                    asset_filename = asset.get('filename')

                    # Skip pull metadata and sidecar for the time being
                    if asset_type in ['metadata', 'sidecar']:
                        continue

                    try:
                        # Ruta del archivo descargado
                        local_file_path = os.path.join(temp_folder, asset_filename)

                        # Archivo de bloqueo temporal para que el pusher no borre el fichero mientras que el puller lo está creando
                        lock_file = local_file_path + ".lock"
                        # Crear archivo de bloqueo antes de la descarga
                        with open(lock_file, 'w') as lock:
                            lock.write("Pulling")
                        # Descargar directamente en temp_folder
                        pulled_assets = source_client.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=temp_folder, log_level=logging.ERROR)
                        # Eliminar archivo de bloqueo después de la descarga
                        os.remove(lock_file)
                    except Exception as e:
                        if _is_nextcloud_photo_not_found_error(e):
                            LOGGER.warning(
                                f"Asset Pull Skip : '{os.path.basename(local_file_path)}' - Photo not found for user"
                            )
                        else:
                            LOGGER.error(f"Asset Pull Error: '{os.path.basename(local_file_path)}' - {e}")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() in video_labels:
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
                        continue

                    # Si se ha hecho correctamente el pull del asset, actualizamos contadores y enviamos el asset a la cola de push
                    if _pull_has_content(pulled_assets):
                        pulled_file_paths = collect_pulled_asset_paths(temp_folder, asset_filename)
                        if not pulled_file_paths:
                            pulled_file_paths = [local_file_path]

                        immich_live_companion = find_immich_live_video_companion(local_file_path, pulled_file_paths)
                        for idx, pulled_file_path in enumerate(pulled_file_paths):
                            if immich_live_companion and path_key(pulled_file_path) == path_key(immich_live_companion):
                                continue
                            normalized_asset_type = infer_asset_type_from_path(pulled_file_path, asset_type)
                            count_push_stats = (idx == 0)
                            # Actualizamos Contadores de descargas
                            LOGGER.info(f"Asset Pulled    : '{os.path.basename(pulled_file_path)}'")
                            SHARED_DATA.counters['total_pulled_assets'] += 1
                            if normalized_asset_type.lower() in video_labels:
                                SHARED_DATA.counters['total_pulled_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pulled_photos'] += 1

                            # Enviar a la cola de push con la información necesaria para la subida (sin album_name)
                            asset_dict = {
                                'asset_id': asset_id,
                                'asset_file_path': pulled_file_path,
                                'asset_datetime': asset_datetime,
                                'asset_type': normalized_asset_type,
                                'album_name': None,
                                'count_push_stats': count_push_stats,
                            }
                            if immich_live_companion and path_key(pulled_file_path) == path_key(local_file_path):
                                asset_dict['live_photo_video_path'] = immich_live_companion
                            unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)
                            if not unique:
                                LOGGER.info(f"Asset Duplicated: '{os.path.basename(pulled_file_path)}'. Skipped")
                                SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                # Solo borramos si ya no está en la cola (ignorando mayúsculas)
                                if not is_asset_in_queue(push_queue, pulled_file_path) and os.path.exists(pulled_file_path):
                                    safe_remove_local_file(pulled_file_path)
                                companion_to_cleanup = asset_dict.get('live_photo_video_path')
                                if companion_to_cleanup and os.path.exists(companion_to_cleanup):
                                    companion_lock = companion_to_cleanup + ".lock"
                                    if (not is_asset_in_queue(push_queue, companion_to_cleanup)) and (not os.path.exists(companion_lock)):
                                        safe_remove_local_file(companion_to_cleanup)
                    else:
                        LOGGER.warning(f"Asset Pull Fail : '{os.path.basename(local_file_path)}'")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() in video_labels:
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
            finally:
                # Eliminar archivo .active después de la descarga
                if os.path.exists(active_file):
                    os.remove(active_file)

            LOGGER.info(f"Puller Task Finished!")

    # ----------------------------------------------------------------------------
    # 2) PUSHER: Función pusher_worker para SUBIR (consumir de la cola)
    # ----------------------------------------------------------------------------
    def pusher_worker(processed_albums=None, worker_id=1, log_level=logging.INFO):
        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"pusher-{thread_id}")

        if processed_albums is None:
            processed_albums = []
        removed_source_asset_ids = set()

        with set_log_level(LOGGER, log_level):
            move_assets = ARGS.get('move-assets', None)
            while True:
                try:
                    # Extraemos el siguiente asset de la cola
                    # time.sleep(0.7)  # Esto es por si queremos ralentizar el worker de subidas
                    asset = push_queue.get()
                    # Actualizamos inmediatamente el tamaño tras el get
                    # SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

                    if asset is None:
                        # Señal de fin: marcamos la tarea y salimos
                        push_queue.task_done()
                        break

                    # Obtenemos las propiedades del asset extraído de la cola.
                    asset_id = asset['asset_id']
                    asset_file_path = asset['asset_file_path']
                    asset_datetime = asset['asset_datetime']
                    asset_type = asset['asset_type']
                    album_name = asset['album_name']
                    count_push_stats = asset.get('count_push_stats', True)
                    live_photo_video_path = asset.get('live_photo_video_path', None)
                    asset_pushed = False
                    treat_as_consumed = False

                    # Antes de llamar, guardamos el nivel actual (debería ser INFO)
                    orig_level = LOGGER.level
                    try:
                        # SUBIR el asset
                        if isinstance(target_client, ClassImmichPhotos) and live_photo_video_path:
                            asset_id, isDuplicated = target_client.push_live_photo(photo_file_path=asset_file_path, live_photo_video_path=live_photo_video_path, log_level=logging.ERROR)
                        else:
                            asset_id, isDuplicated = target_client.push_asset(file_path=asset_file_path, log_level=logging.ERROR)

                        # Actualizamos Contadores de subidas
                        if asset_id:
                            asset_pushed = True
                            treat_as_consumed = True
                            if isDuplicated:
                                LOGGER.info(f"Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped")
                                if count_push_stats:
                                    SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                            else:
                                if count_push_stats:
                                    SHARED_DATA.counters['total_pushed_assets'] += 1
                                    if asset_type.lower() in video_labels:
                                        SHARED_DATA.counters['total_pushed_videos'] += 1
                                    else:
                                        SHARED_DATA.counters['total_pushed_photos'] += 1
                                LOGGER.info(f"Asset Pushed    : '{os.path.basename(asset_file_path)}'")
                                if isinstance(target_client, ClassImmichPhotos) and asset_type.lower() in image_labels and not str(asset_id).startswith("duplicate::"):
                                    try:
                                        file_size = os.path.getsize(asset_file_path) if os.path.exists(asset_file_path) else 0
                                    except Exception:
                                        file_size = 0
                                    rec = target_client._build_burst_record(
                                        asset_id=asset_id,
                                        file_path=asset_file_path,
                                        capture_epoch=parse_capture_epoch(asset_datetime),
                                        file_size=file_size
                                    )
                                    with immich_uploaded_records_lock:
                                        immich_uploaded_records.append(rec)
                        else:
                            # Si entramos aqui es porque asset_id no existe, probablemente se haya producido una excepción en push_asset, y el LOGGER se haya quedado con el nivel ERROR
                            # Restauramos el LOGGER al nivel que tenía antes de llamar a push_asset
                            # LOGGER.setLevel(orig_level)
                            set_log_level(LOGGER, orig_level)
                            if isDuplicated:
                                LOGGER.info(f"Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped")
                                treat_as_consumed = True
                                if count_push_stats:
                                    SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                            else:
                                if album_name:
                                    LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                                else:
                                    LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                                if count_push_stats:
                                    SHARED_DATA.counters['total_push_failed_assets'] += 1
                                    if asset_type.lower() in video_labels:
                                        SHARED_DATA.counters['total_push_failed_videos'] += 1
                                    else:
                                        SHARED_DATA.counters['total_push_failed_photos'] += 1

                        # Borrar asset de 'source' client si hemos pasado el argumento '-move, --move-assets'
                        if move_assets and asset.get('asset_id') and asset['asset_id'] not in removed_source_asset_ids:
                            source_client.remove_assets(asset_ids=asset['asset_id'], log_level=log_level)
                            removed_source_asset_ids.add(asset['asset_id'])

                        # Borrar asset de la carpeta Automatic_Migration_Push_Failed tras subir
                        if asset_pushed or treat_as_consumed:
                            safe_remove_local_file(asset_file_path)
                            if live_photo_video_path:
                                safe_remove_local_file(live_photo_video_path)
                    except Exception as e:
                        # 1) Restaura el nivel a INFO
                        LOGGER.setLevel(logging.INFO)

                        # 2) Loguea el fallo
                        if album_name:
                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                        else:
                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                        LOGGER.error(f"Caught Exception: {str(e)} \n{traceback.format_exc()}")

                        # 3) Actualiza contadores
                        if count_push_stats:
                            SHARED_DATA.counters['total_push_failed_assets'] += 1
                            if asset_type.lower() in video_labels:
                                SHARED_DATA.counters['total_push_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_push_failed_photos'] += 1

                        # 4) Marca la tarea como completada y pasa al siguiente asset
                        push_queue.task_done()
                        # SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()
                        continue

                    finally:
                        # Pase lo que pase (return o excepción dentro de push_asset),
                        # aquí restauramos siempre el nivel original
                        LOGGER.setLevel(orig_level)

                    # Si existe album_name y el asset ya fue subido, manejamos el álbum en destino
                    if album_name and asset_pushed:
                        # 1) Asegurarnos de que el álbum existe (sólo un hilo lo crea)
                        with album_creation_lock:
                            if album_name not in created_albums:
                                exists, aid = target_client.album_exists(album_name=album_name, log_level=logging.ERROR)
                                if not exists:
                                    aid = target_client.create_album(album_name=album_name, log_level=logging.ERROR)
                                    LOGGER.info(f"Album Created   : '{album_name}' by pusher_worker={worker_id}")
                                created_albums[album_name] = aid
                        # 2) Recuperar album_id cached que ya debe existir (añadido por este worker o cualquier otro worker previamente)
                        album_id_dest = created_albums.get(album_name)
                        try:
                            # 3) Añadir el asset al álbum existente
                            target_client.add_assets_to_album(album_id=album_id_dest, asset_ids=asset_id, album_name=album_name, log_level=logging.ERROR)
                        except Exception as e:
                            LOGGER.error(f"Album Push Fail : '{album_name}'")
                            LOGGER.error(f"Caught Exception: {str(e)}\n{traceback.format_exc()}")
                            # 4) Actualizar contador de fallos de álbum
                            SHARED_DATA.counters['total_push_failed_albums'] += 1

                        # Verificar si la carpeta local del álbum está vacía y borrarla
                        album_folder_path = os.path.join(temp_folder, album_name)
                        if os.path.exists(album_folder_path):
                            try:
                                # Si la carpeta tiene un archivo .active, significa que aún está en uso → NO BORRAR
                                active_file = os.path.join(album_folder_path, ".active")
                                if os.path.exists(active_file):
                                    # No se borra porque aún está en uso
                                    push_queue.task_done()
                                    continue
                                # Si la carpeta está vacía (o solo hay subcarpetas vacías), la borramos, de lo contrario saltaremos al bloque except generando una excepción que ignoraremos
                                os.rmdir(album_folder_path)
                                # Actualizamos contadores si el borrado de la carpeta ha tenido éxito (significa que el album está totalmente subido ya que el puller ha quitado el archivo .active y los pusher han borrado todos los archivos subidos)
                                # Sólo actualizamos contadores si el album no había sido procesado antes
                                if album_name not in processed_albums:
                                    processed_albums.append(album_name)  # Lo incluimos en la lista de albumes procesados
                                    SHARED_DATA.counters['total_pushed_albums'] += 1
                                    SHARED_DATA.counters['total_pushed_albums'] = min(SHARED_DATA.counters['total_pushed_albums'], SHARED_DATA.counters['total_pulled_albums'])  # Avoid to set total_pushed_albums > total_pulled_albums
                                    LOGGER.info(f"Album Pushed    : '{album_name}'")
                            except OSError:
                                # Si no está vacía, ignoramos el error
                                pass

                    # Finalmente, marco la tarea como procesada
                    push_queue.task_done()
                    # SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

                except Exception as e:
                    if album_name:
                        LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                    else:
                        LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                    LOGGER.error(f"Caught Exception: {str(e)} \n{traceback.format_exc()}")
                    SHARED_DATA.counters['total_push_failed_assets'] += 1
                    if asset_type.lower() in video_labels:
                        SHARED_DATA.counters['total_push_failed_videos'] += 1
                    else:
                        SHARED_DATA.counters['total_push_failed_photos'] += 1

            LOGGER.info(f"Pusher {worker_id} - Task Finished!")

    # ----------------------------
    # 4) LLAMADA AL HILO PRINCIPAL
    # ----------------------------

    # Inicializamos start_time para medir el tiempo de procesamiento
    migration_start_time = datetime.now()

    # Preparar la cola que compartiremos entre descargas y subidas
    # push_queue = Queue()
    push_queue = MonitoredQueue()

    # Set global para almacenar paths ya añadidos
    added_file_paths = set()

    # Lock global para proteger el acceso concurrente
    file_paths_lock = threading.Lock()

    # Normalizamos temp_folder
    temp_folder = normalize_path(temp_folder)

    # Listas de posibles etiquetas para los distintos tipos de archivos en los diferentes clientes
    image_labels = ['photo', 'image']
    video_labels = ['video', 'live']
    metadata_labels = ['metadata']
    sidecar_labels = ['sidecar']

    # Check if parallel=None, and in that case, get it from ARGS
    if parallel is None: parallel = ARGS['parallel-migration']

    # Llamada al hilo principal
    main_thread(parallel=parallel, log_level=log_level)


###########################
# start_dashboard Function #
###########################
def start_dashboard(migration_finished, SHARED_DATA, parallel=True, step_name='', log_level=None):
    with set_log_level(LOGGER, log_level):
        import time
        from datetime import datetime
        from rich.console import Console
        from rich.layout import Layout
        from rich.progress import Progress, BarColumn, TextColumn
        from rich.table import Table
        from rich.panel import Panel
        from rich.live import Live
        from rich.text import Text
        from rich.markup import escape
        import textwrap
        import traceback

        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"dashboard-{thread_id}")

        # 🚀 Guardar stdout y stderr originales
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # Creamos la consola antes de enganchar excepciones
        console = Console()

        # Install a global exception hook for this thread
        def exception_hook(exctype, value, tb):
            """Catch uncaught exceptions and log + print them, then restore cursor."""
            error_msg = "".join(traceback.format_exception(exctype, value, tb))
            LOGGER.warning(f"{step_name}Unhandled exception in Live Dashboard:\n{error_msg}")
            try:
                console.show_cursor()
            except:
                pass
            original_stdout.write(error_msg)

        # 🚀 Capturar e interceptar manualmente cualquier error antes de que `rich` lo maneje
        sys.excepthook = exception_hook

        try:
            # Min Terminal Height and Width to display the Live Dashboard
            MIN_TERMINAL_HEIGHT = 30
            MIN_TERMINAL_WIDTH = 100

            # Calculate terminal_height and terminal_width
            terminal_height = console.size.height
            terminal_width = console.size.width

            LOGGER.info(f"Detected terminal height = {terminal_height}")
            LOGGER.info(f"Detected terminal width  = {terminal_width}")

            # In web-interface mode, the browser dashboard is the canonical live renderer.
            if os.environ.get("PHOTOMIGRATOR_WEB_MODE") == "1":
                LOGGER.info("Using Web Interface Live Dashboard...")
                ARGS['dashboard'] = False
                return

            if terminal_height < MIN_TERMINAL_HEIGHT:
                LOGGER.info(f"Cannot display Live Dashboard because the detected terminal height = {terminal_height} and the minumum needed height = {MIN_TERMINAL_HEIGHT}. Continuing without Live Dashboard...")
                ARGS['dashboard'] = False  # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
                return

            if terminal_width < MIN_TERMINAL_WIDTH:
                LOGGER.info(f"Cannot display Live Dashboard because the detected terminal width = {terminal_width} and the minumum needed width = {MIN_TERMINAL_WIDTH}. Continuing without Live Dashboard...")
                ARGS['dashboard'] = False  # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
                return

            # Iniciamos el contador de tiempo transcurrido
            step_start_time = datetime.now()

            layout = Layout()
            layout.size = terminal_height

            # # 🚀 Forzar la redirección de sys.stderr globalmente para asegurar que no se imprima en pantalla
            # sys.stderr = sys.__stderr__ = LoggerCapture(LOGGER, logging.ERROR)
            #
            # # 🚀 Capturar e interceptar manualmente cualquier error antes de que `rich` lo maneje
            # def log_exceptions(exctype, value, tb):
            #     """Captura todas las excepciones no manejadas y las guarda en el LOGGER sin imprimir en pantalla"""
            #     error_message = "".join(traceback.format_exception(exctype, value, tb))
            #     LOGGER.error(f"Excepción no manejada:\n" + error_message)  # Guardar en logs sin imprimir en consola
            #
            # sys.excepthook = log_exceptions

            # Eliminar solo los StreamHandler sin afectar los FileHandler
            for handler in list(LOGGER.handlers):  # Hacer una copia de la lista para evitar problemas al modificarla
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    LOGGER.removeHandler(handler)

            # Crea el handler y configúralo con un formatter
            memory_handler = CustomInMemoryLogHandler(SHARED_DATA.logs_queue)
            memory_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            memory_handler.setLevel(log_level if log_level is not None else logging.INFO)
            memory_handler.accept_tqdm = True

            # Agrega el handler al LOGGER
            LOGGER.addHandler(memory_handler)

            # Opcional: si NO quieres imprimir por consola, puedes quitar el StreamHandler que tenga el logger por defecto (así solo se registran en la lista).
            # Por ejemplo:
            LOGGER.propagate = False
            log_file = get_logger_filename(LOGGER)

            # Split layout: header_panel (8 lines), title_panel (3 lines), content_panel (12 lines),
            # logs fill remainder, background_progress_panel (6 lines) at the bottom.
            layout.split_column(
                Layout(name="empty_line_1", size=1),  # Línea vacía
                Layout(name="header_panel", size=8),
                Layout(name="title_panel", size=3),
                Layout(name="content_panel", size=12),
                Layout(name="logs_panel", ratio=1),
                Layout(name="background_progress_panel", size=6),
                Layout(name="empty_line_2", size=1),  # Línea vacía
            )

            # Obtener el height de cada panel
            empty_line_1_height = layout["empty_line_1"].size
            header_panel_height = layout["header_panel"].size
            title_panel_height = layout["title_panel"].size
            content_panel_height = layout["content_panel"].size
            background_progress_panel_height = layout["background_progress_panel"].size
            empty_line_2_height = layout["empty_line_2"].size

            # Calcular logs_panel en función del espacio restante
            fixed_heights = sum([empty_line_1_height, header_panel_height, title_panel_height, content_panel_height, background_progress_panel_height, empty_line_2_height])
            logs_panel_height = terminal_height - fixed_heights  # Espacio restante

            # Asegurar que la línea vacía no tenga bordes ni contenido visible
            layout["empty_line_1"].update("")
            layout["empty_line_2"].update("")

            # Split content_panel horizontally into 3 panels
            layout["content_panel"].split_row(
                Layout(name="info_panel", ratio=3),
                Layout(name="pulls_panel", ratio=4),
                Layout(name="pushs_panel", ratio=4),
            )

            # ─────────────────────────────────────────────────────────────────────────
            # 0) Header Panel
            # ─────────────────────────────────────────────────────────────────────────
            header = textwrap.dedent(rf"""
             ____  _           _        __  __ _                 _
            |  _ \| |__   ___ | |_ ___ |  \/  (_) __ _ _ __ __ _| |_ ___  _ __
            | |_) | '_ \ / _ \| __/ _ \| |\/| | |/ _` | '__/ _` | __/ _ \| '__|
            |  __/| | | | (_) | || (_) | |  | | | (_| | | | (_| | || (_) | |
            |_|   |_| |_|\___/ \__\___/|_|  |_|_|\__, |_|  \__,_|\__\___/|_|
                                                 |___/ {TOOL_VERSION} ({TOOL_DATE})
            """).lstrip("\n")  # Elimina solo la primera línea en blanco

            layout["header_panel"].update(Panel(f"[gold1]{header}[/gold1]", border_style="gold1", expand=True))

            # ─────────────────────────────────────────────────────────────────────────
            # 1) Title Panel
            # ─────────────────────────────────────────────────────────────────────────
            title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automatic Migration - {TOOL_NAME_VERSION}"

            layout["title_panel"].update(Panel(f"🚀 {title}", border_style="bright_blue", expand=True))

            def update_title_panel():
                title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automatic Migration - {TOOL_NAME_VERSION}"
                layout["title_panel"].update(Panel(f"🚀 {title}", border_style="bright_blue", expand=True))

            # ─────────────────────────────────────────────────────────────────────────
            # 2) Info Panel
            # ─────────────────────────────────────────────────────────────────────────

            def build_info_panel(clean_queue_history=False):
                """Construye el panel de información con historial de la cola."""
                # 🔹 Calcular el ancho real de "info_panel"

                total_ratio = 3 + 4 + 4  # Suma de los ratios en split_row()
                info_panel_ratio = 3  # Ratio de "info_panel"

                # Estimación del ancho de info_panel antes de que Rich lo calcule
                info_panel_width = (terminal_width * info_panel_ratio) // total_ratio

                # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # # Histograma temporal de la cola con barras como estas "  ▁▂▃▄▅▆▇█"  o estas "▁▂▄▆█"
                # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # # 🔹 Unicode para representar la barra de progreso vertical (10 niveles)
                # BARS = "  ▁▂▃▄▅▆▇█"     # Se agregan 10 barras
                # BARS = "▁▂▄▆█"          # # Se agregan 5 barras
                #
                # # 🔹 Inicializar el historial de la cola dentro de la función
                # if not hasattr(build_info_panel, "queue_history"):
                #     build_info_panel.queue_history = collections.deque(maxlen=info_panel_width-31)
                # queue_history = build_info_panel.queue_history
                #
                # # 🔹 Obtener el tamaño actual de la cola
                # current_queue_size = SHARED_DATA.info.get('assets_in_queue', 0)
                #
                # # 🔹 Actualizar historial de la cola
                # queue_history.append(current_queue_size)
                #
                # # 🔹 Definir los rangos de normalización (10 bloques de tamaño 10 cada uno)
                # num_blocks = len(BARS)
                # block_size = 100 / num_blocks  # Cada bloque cubre 10 unidades
                #
                # # 🔹 Asignar la barra correspondiente a cada valor de la cola
                # progress_bars = [BARS[min(int(val // block_size), num_blocks - 1)] for val in queue_history]
                #
                # # 🔹 Unimos todas las barras
                # queue_display = "".join(progress_bars)

                # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # Barra de cola actual. Muestre una barra horizontal rellenable "███████████████████", cuando esté llena "██████████" cuando esté a la mitad, "██" cuando esté casi vacía
                # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # 🔹 Definir el ancho de la barra de progreso dinámicamente
                BAR_WIDTH = max(1, info_panel_width - 34)  # Asegurar que al menos sea 1
                # 🔹 Obtener el tamaño actual de la cola
                current_queue_size = SHARED_DATA.info.get('assets_in_queue', 0)
                # 🔹 Normalizar el tamaño de la cola dentro del rango de la barra
                filled_blocks = min(int((current_queue_size / 100) * BAR_WIDTH), BAR_WIDTH)
                empty_blocks = BAR_WIDTH - filled_blocks
                # 🔹 Crear la barra de progreso con "█" y espacios
                queue_bar = "█" * filled_blocks + " " * empty_blocks
                if parallel:
                    # 🔹 Mostrar la barra con la cantidad actual de elementos en la cola y el máximo de 100 al final
                    queue_bar = f"[{queue_bar}] {current_queue_size:>3}/100"
                else:
                    # 🔹 Mostrar la barra con la cantidad actual de elementos en la cola aquí sin máximo, y dando espacio para 7 dígitos
                    queue_bar = f"[{queue_bar}] {current_queue_size:>7}"
                # 🔹 borra la barra al final
                if clean_queue_history:
                    queue_bar = 0

                # 🔹 Datos a mostrar
                info_data = [
                    ("🎯 Total Assets", SHARED_DATA.info.get('total_assets', 0)),
                    ("📷 Total Photos", SHARED_DATA.info.get('total_photos', 0)),
                    ("🎬 Total Videos", SHARED_DATA.info.get('total_videos', 0)),
                    ("📂 Total Albums", SHARED_DATA.info.get('total_albums', 0)),
                    ("🔒 Blocked Albums", SHARED_DATA.info.get('total_albums_blocked', 0)),
                    ("📜 Total Metadata", SHARED_DATA.info.get('total_metadata', 0)),
                    ("🔗 Total Sidecar", SHARED_DATA.info.get('total_sidecar', 0)),
                    ("🔍 Invalid Files", SHARED_DATA.info.get('total_invalid', 0)),
                    ("📊 Assets in Queue", f"{queue_bar}"),
                    ("🕒 Elapsed Time", SHARED_DATA.info.get('elapsed_time', 0)),
                ]

                # 🔹 Crear la tabla
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=20, no_wrap=True)
                table.add_column(justify="right", ratio=1)
                for label, value in info_data:
                    table.add_row(f"[bright_magenta]{label:<17}: [/bright_magenta]", f"[bright_magenta]{value}[/bright_magenta]")

                # 🔹 Devolver el panel
                return Panel(table, title="📊 Info Panel", border_style="bright_magenta", expand=True, padding=(0, 1))


            # ─────────────────────────────────────────────────────────────────────────
            # 3) Progress Bars for pulls / pushs
            #    Show "X / total" with a bar, no custom chars
            # ─────────────────────────────────────────────────────────────────────────
            def create_progress_bar(color: str) -> Progress:
                """
                Creates a bar with a longer width and displays 'X / total items' in color.
                """
                counter = f"{{task.completed}}/{{task.total}}"
                return Progress(
                    BarColumn(
                        bar_width=100,  # longer bar for better visuals
                        style=f"{color} dim",
                        complete_style=f"{color} bold",
                        finished_style=f"{color} bold",
                        pulse_style="bar.pulse"
                        # pulse_style=f"{color} bold"
                    ),
                    TextColumn(f"[{color}]{counter:>15}[/{color}]"),
                    console=console,
                    expand=True
                )


            # PULLS (Cyan)
            pull_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
                "🎯 Pulled Assets": (create_progress_bar("cyan"), 'total_pulled_assets', "total_assets"),
                "📷 Pulled Photos": (create_progress_bar("cyan"), 'total_pulled_photos', "total_photos"),
                "🎬 Pulled Videos": (create_progress_bar("cyan"), 'total_pulled_videos', "total_videos"),
                "📂 Pulled Albums": (create_progress_bar("cyan"), 'total_pulled_albums', "total_albums"),
            }
            failed_pulls = {
                "🔒 Blocked Albums": 'total_albums_blocked',
                "🔒 Blocked Assets": 'total_assets_blocked',
                "🚩 Failed Assets": 'total_pull_failed_assets',
                "🚩 Failed Photos": 'total_pull_failed_photos',
                "🚩 Failed Videos": 'total_pull_failed_videos',
                "🚩 Failed Albums": 'total_pull_failed_albums',
            }
            pull_tasks = {}
            for label, (bar, completed_label, total_label) in pull_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                pull_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))

            # PUSHS (Green)
            push_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
                "🎯 Pushed Assets": (create_progress_bar("green"), 'total_pushed_assets', "total_assets"),
                "📷 Pushed Photos": (create_progress_bar("green"), 'total_pushed_photos', "total_photos"),
                "🎬 Pushed Videos": (create_progress_bar("green"), 'total_pushed_videos', "total_videos"),
                "📂 Pushed Albums": (create_progress_bar("green"), 'total_pushed_albums', "total_albums"),
            }
            failed_pushs = {
                "🧩 Duplicates": 'total_push_duplicates_assets',
                "🚩 Failed Assets": 'total_push_failed_assets',
                "🚩 Failed Photos": 'total_push_failed_photos',
                "🚩 Failed Videos": 'total_push_failed_videos',
                "🚩 Failed Albums": 'total_push_failed_albums',
            }
            push_tasks = {}
            for label, (bar, completed_label, total_label) in push_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                push_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))


            # ─────────────────────────────────────────────────────────────────────────
            # 4) Build the Pull/Push Panels
            # ─────────────────────────────────────────────────────────────────────────
            def build_pull_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=20)
                table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in pull_bars.items():
                    table.add_row(f"[cyan]{label:<17}:[/cyan]", bar)
                    bar.update(pull_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                for label, counter_label in failed_pulls.items():
                    value = SHARED_DATA.counters[counter_label]
                    table.add_row(f"[cyan]{label:<17}:[/cyan]", f"[cyan]{value}[/cyan]")
                return Panel(table, title=f'📥 From: {SHARED_DATA.info.get("source_client_name", "Source Client")}', border_style="cyan", expand=True)


            def build_push_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=19)
                table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in push_bars.items():
                    table.add_row(f"[green]{label:<16}:[/green]", bar)
                    bar.update(push_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                for label, counter_label in failed_pushs.items():
                    value = SHARED_DATA.counters[counter_label]
                    table.add_row(f"[green]{label:<16}:[/green]", f"[green]{value}[/green]")
                return Panel(table, title=f'📤 To: {SHARED_DATA.info.get("target_client_name", "Source Client")}', border_style="green", expand=True)

            # -------------------------------------------------------------------------
            # 5) Background Progress Panel (capture any tqdm emitted in background)
            # -------------------------------------------------------------------------
            ansi_escape_re = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
            tqdm_progress_re = re.compile(
                r"(?P<pct>\d{1,3})%\|[^|]*\|\s*(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)"
            )
            custom_progress_re = re.compile(
                r"^(?P<desc>.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+"
                r"(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)\s+\d+(?:\.\d+)?%\s*$"
            )
            bg_progress_rows = {}
            bg_progress_colors = ["bright_yellow", "bright_blue", "bright_magenta", "bright_green"]
            bg_completed_retention_sec = 5.0
            bg_progress_next_color_idx = 0
            bg_progress_version = 0

            def _parse_int(value, default=0):
                try:
                    return int(str(value or "").replace(",", "").strip())
                except (TypeError, ValueError):
                    return default

            def _normalize_desc(desc):
                text = re.sub(r"\s+", " ", str(desc or "")).strip(" :-")
                text = re.sub(r"^(VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*:\s*", "", text, flags=re.IGNORECASE)
                return text or "Progress"

            def _create_bg_bar(color):
                counter = "{task.completed}/{task.total}"
                return Progress(
                    BarColumn(
                        bar_width=None,
                        style=f"{color} dim",
                        complete_style=f"{color} bold",
                        finished_style=f"{color} bold",
                        pulse_style="bar.pulse",
                    ),
                    TextColumn(f"[{color}]{counter:>15}[/{color}]"),
                    console=console,
                    expand=True,
                )

            def _upsert_bg_progress(desc, current, total):
                nonlocal bg_progress_next_color_idx, bg_progress_version
                total_value = max(1, int(total))
                if int(total) <= 0:
                    return False

                label = _normalize_desc(desc)
                key = f"{label.lower()}::{total_value}"
                if key not in bg_progress_rows:
                    color = bg_progress_colors[bg_progress_next_color_idx % len(bg_progress_colors)]
                    bg_progress_next_color_idx += 1
                    bar = _create_bg_bar(color)
                    task_id = bar.add_task(label, completed=0, total=total_value)
                    bg_progress_rows[key] = {
                        "label": label,
                        "color": color,
                        "bar": bar,
                        "task_id": task_id,
                        "last_update": time.time(),
                        "completed": False,
                    }

                info = bg_progress_rows[key]
                done = max(0, min(int(current), total_value))
                info["bar"].update(info["task_id"], completed=done, total=total_value)
                info["last_update"] = time.time()
                info["completed"] = done >= total_value
                bg_progress_version += 1
                return True

            def _prune_bg_progress_rows(now=None):
                nonlocal bg_progress_version
                if now is None:
                    now = time.time()
                to_delete = []
                for key, info in bg_progress_rows.items():
                    if info.get("completed") and now - float(info.get("last_update", now)) > bg_completed_retention_sec:
                        to_delete.append(key)
                if not to_delete:
                    return False
                for key in to_delete:
                    bg_progress_rows.pop(key, None)
                bg_progress_version += 1
                return True

            def _consume_progress_line(line):
                raw = str(line or "")
                if not raw:
                    return False

                if raw.startswith(TQDM_DASHBOARD_META_PREFIX):
                    payload = raw[len(TQDM_DASHBOARD_META_PREFIX):]
                    parts = payload.split("\t")
                    if len(parts) == 3:
                        desc = parts[0]
                        current = _parse_int(parts[1], 0)
                        total = _parse_int(parts[2], 0)
                        return _upsert_bg_progress(desc, current, total)
                    return False

                plain = ansi_escape_re.sub("", raw.replace("\r", "")).strip()
                if plain.startswith(TQDM_DASHBOARD_PREFIX):
                    plain = plain[len(TQDM_DASHBOARD_PREFIX):].strip()
                plain = re.sub(r"^(VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*:\s*", "", plain, flags=re.IGNORECASE)

                custom_match = custom_progress_re.match(plain)
                if custom_match:
                    desc = custom_match.group("desc")
                    current = _parse_int(custom_match.group("current"), 0)
                    total = _parse_int(custom_match.group("total"), 0)
                    return _upsert_bg_progress(desc, current, total)

                tqdm_match = tqdm_progress_re.search(plain)
                if tqdm_match:
                    desc = plain[:tqdm_match.start()].strip(" :-")
                    if not desc:
                        return False
                    current = _parse_int(tqdm_match.group("current"), 0)
                    total = _parse_int(tqdm_match.group("total"), 0)
                    return _upsert_bg_progress(desc, current, total)

                return False

            def build_background_progress_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=35, no_wrap=True, overflow="ellipsis")
                table.add_column(justify="left", ratio=1, no_wrap=True)

                if bg_progress_rows:
                    visible_limit = max(1, background_progress_panel_height - 2)
                    ordered = list(bg_progress_rows.values())  # preserve creation order for visual stability
                    for info in ordered[:visible_limit]:
                        label = escape(str(info.get("label", "Progress")))
                        table.add_row(f"[{info['color']}]{label}:[/{info['color']}]", info["bar"])
                else:
                    table.add_row("", "")

                return Panel(table, title="⏳ Background Progress", border_style="bright_cyan", expand=True, padding=(0, 1))

            # ─────────────────────────────────────────────────────────────────────────
            # 6) Logging Panel from Memmory Handler
            # ─────────────────────────────────────────────────────────────────────────
            # Lista (o deque) para mantener todo el historial de logs ya mostrados
            logs_panel_height = terminal_height - fixed_heights - 2  # Espacio restante. Restamos 2 para quitar las líneas del borde superior e inferior del panel de Logs
            ACCU_LOGS = deque(maxlen=max(2000, logs_panel_height))
            logs_version = 0

            def _drain_logs_queue():
                """
                Consume queued logs/events and updates in-memory states.
                Returns True when log panel content changed.
                """
                nonlocal logs_version
                changed = False
                while True:
                    try:
                        line = SHARED_DATA.logs_queue.get_nowait()
                    except Empty:
                        break

                    # Route tqdm/progress lines to Background Progress panel.
                    if _consume_progress_line(line):
                        continue

                    clean_line = ansi_escape_re.sub("", str(line or "").replace("\r", "")).rstrip()
                    if not clean_line:
                        continue
                    safe_line = clean_line

                    line_lower = clean_line.lower()
                    if "warning :" in line_lower:
                        line_style = "yellow"
                    elif "error   :" in line_lower:
                        line_style = "red"
                    elif "debug   :" in line_lower:
                        line_style = "#EEEEEE"
                    elif "delayed" in line_lower:
                        line_style = "bright_black"
                    elif "album created" in line_lower:
                        line_style = "bright_white"
                    elif "album pulled" in line_lower:
                        line_style = "bright_cyan"
                    elif "album pushed" in line_lower:
                        line_style = "bright_green"
                    elif "fail" in line_lower:
                        line_style = "yellow"
                    elif "pull" in line_lower and not "push" in line_lower:
                        line_style = "cyan"
                    elif any(word in line_lower for word in ("push", "created", "duplicated")) and not "pull" in line_lower:
                        line_style = "green"
                    else:
                        line_style = "bright_white"

                    for visual_line in str(safe_line).splitlines():
                        if visual_line.strip():
                            ACCU_LOGS.append((visual_line, line_style))
                            changed = True

                if changed:
                    logs_version += 1
                return changed

            def build_log_panel():
                title_logs_panel = f"📜 Logs Panel (Only last {logs_panel_height} rows shown. Complete log file at: '{FOLDERNAME_LOGS}/{os.path.basename(log_file)}')"
                try:
                    if ACCU_LOGS:
                        logs_text = Text(no_wrap=True, overflow="crop")
                        visible_logs = list(ACCU_LOGS)[-max(1, logs_panel_height):]
                        logs_count = len(visible_logs)
                        for idx, entry in enumerate(visible_logs):
                            visual_line, visual_style = entry
                            logs_text.append(visual_line, style=visual_style)
                            if idx < logs_count - 1:
                                logs_text.append("\n")
                    else:
                        logs_text = Text("Initializing...", no_wrap=True, overflow="crop")
                    return Panel(logs_text, title=title_logs_panel, border_style="bright_red", expand=True, title_align="left")
                except Exception as e:
                    LOGGER.error(f"Building Log Panel: {e}")
                    return Panel("Error building log panel", title="📜 Logs Panel", border_style="bright_red", expand=True, title_align="left")

            def _build_info_signature():
                keys = (
                    "total_assets", "total_photos", "total_videos", "total_albums", "total_albums_blocked",
                    "total_metadata", "total_sidecar", "total_invalid", "assets_in_queue",
                )
                return tuple(SHARED_DATA.info.get(k) for k in keys)

            def _build_pull_signature():
                completed_keys = [cfg[1] for cfg in pull_bars.values()]
                total_keys = [cfg[2] for cfg in pull_bars.values()]
                failed_keys = list(failed_pulls.values())
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                )

            def _build_push_signature():
                completed_keys = [cfg[1] for cfg in push_bars.values()]
                total_keys = [cfg[2] for cfg in push_bars.values()]
                failed_keys = list(failed_pushs.values())
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                )


            # ─────────────────────────────────────────────────────────────────────────
            # 6) Main Live Loop
            # ─────────────────────────────────────────────────────────────────────────
            LOGGER.debug(f"{step_name}Dashboard initialized (parallel={parallel})")
            with Live(layout, refresh_per_second=4, auto_refresh=False, screen=True, console=console, vertical_overflow="crop") as live:
                try:
                    min_refresh_interval_sec = 1.0 / 60.0
                    elapsed_refresh_interval_sec = 1.0
                    last_render_ts = 0.0
                    last_elapsed_update_ts = 0.0
                    last_info_signature = None
                    last_pull_signature = None
                    last_push_signature = None
                    last_bg_version = -1
                    last_logs_version = -1

                    update_title_panel()
                    _drain_logs_queue()
                    _prune_bg_progress_rows()
                    SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                    layout["info_panel"].update(build_info_panel())
                    layout["pulls_panel"].update(build_pull_panel())
                    layout["pushs_panel"].update(build_push_panel())
                    layout["background_progress_panel"].update(build_background_progress_panel())
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()
                    last_render_ts = time.time()
                    last_elapsed_update_ts = last_render_ts
                    last_info_signature = _build_info_signature()
                    last_pull_signature = _build_pull_signature()
                    last_push_signature = _build_push_signature()
                    last_bg_version = bg_progress_version
                    last_logs_version = logs_version

                    # Continue the loop until migration_finished.is_set()
                    LOGGER.debug(f"{step_name}Starting Live loop")
                    while not migration_finished.is_set():
                        dirty = False

                        if _drain_logs_queue():
                            dirty = True
                        if _prune_bg_progress_rows():
                            dirty = True

                        info_signature = _build_info_signature()
                        if info_signature != last_info_signature:
                            layout["info_panel"].update(build_info_panel())
                            last_info_signature = info_signature
                            dirty = True

                        pull_signature = _build_pull_signature()
                        if pull_signature != last_pull_signature:
                            layout["pulls_panel"].update(build_pull_panel())
                            last_pull_signature = pull_signature
                            dirty = True

                        push_signature = _build_push_signature()
                        if push_signature != last_push_signature:
                            layout["pushs_panel"].update(build_push_panel())
                            last_push_signature = push_signature
                            dirty = True

                        if bg_progress_version != last_bg_version:
                            layout["background_progress_panel"].update(build_background_progress_panel())
                            last_bg_version = bg_progress_version
                            dirty = True

                        if logs_version != last_logs_version:
                            layout["logs_panel"].update(build_log_panel())
                            last_logs_version = logs_version
                            dirty = True

                        now_ts = time.time()
                        if now_ts - last_elapsed_update_ts >= elapsed_refresh_interval_sec:
                            SHARED_DATA.info["elapsed_time"] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                            layout["info_panel"].update(build_info_panel())
                            last_info_signature = _build_info_signature()
                            last_elapsed_update_ts = now_ts
                            dirty = True

                        if dirty and (now_ts - last_render_ts >= min_refresh_interval_sec):
                            live.refresh()
                            last_render_ts = now_ts
                        time.sleep(0.01)

                    # Pequeña pausa adicional para asegurar el dibujado final
                    time.sleep(1)

                    # Al terminar, asegurarse que todos los paneles finales se muestren
                    _drain_logs_queue()
                    _prune_bg_progress_rows()
                    SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                    layout["info_panel"].update(build_info_panel(clean_queue_history=True))  # Limpiamos el histórico de la cola
                    layout["pulls_panel"].update(build_pull_panel())
                    layout["pushs_panel"].update(build_push_panel())
                    layout["background_progress_panel"].update(build_background_progress_panel())
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()

                except ModuleNotFoundError as error:
                    missing = str(getattr(error, "name", "") or "")
                    if "rich._unicode_data.unicode" in missing:
                        LOGGER.warning(
                            f"{step_name}Live Dashboard disabled because bundled binary is missing Rich unicode tables "
                            f"({missing}). Continuing without dashboard."
                        )
                        ARGS['dashboard'] = False
                        return
                    err = traceback.format_exc()
                    LOGGER.warning(f"{step_name}Exception during Live Dashboard execution:\n{err}")
                    try:
                        console.show_cursor()
                    except:
                        pass
                    original_stdout.write(err)
                    raise
                except Exception:
                    # Catch any exception from Live Dashboard
                    err = traceback.format_exc()
                    LOGGER.warning(f"{step_name}Exception during Live Dashboard execution:\n{err}")
                    try:
                        console.show_cursor()
                    except:
                        pass
                    original_stdout.write(err)
                    raise

                finally:
                    # Always restore cursor and stdout/stderr
                    try:
                        console.show_cursor()
                    except:
                        pass
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr

        except Exception:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            traceback.print_exc()
            LOGGER.exception(f"ERROR during Automatic Migration Feature")
            raise
        finally:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
######################
# CALL FROM __MAIN__ #
######################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.

    change_working_dir(change_dir=False)

    # # Paths para Windows
    local_folder = r'r:\jaimetur\PhotoMigrator\LocalFolderClient'
    takeout_folder = r'r:\jaimetur\PhotoMigrator\Takeout'
    takeout_folder_zipped = r'r:\jaimetur\PhotoMigrator\Zip_files_prueba_rapida'

    # Paths para Linux
    # local_folder = r'/mnt/homes/jaimetur/PhotoMigrator/LocalFolderClient'
    # takeout_folder = r'/mnt/homes/jaimetur/PhotoMigrator/Takeout'
    # takeout_folder_zipped = r'/mnt/homes/jaimetur/PhotoMigrator/Zip_files_prueba_rapida'

    # Define source and target
    source = takeout_folder_zipped
    target = 'synology-photos'

    mode_AUTOMATIC_MIGRATION(source=source, target=target, show_dashboard=True, parallel=True, show_gpth_info=True)
