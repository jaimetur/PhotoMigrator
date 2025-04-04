import os, sys
from datetime import datetime, timedelta
import logging
import threading
from queue import Queue
from collections import deque
from pathlib import Path
import json
import time
import shutil
from threading import main_thread

import Utils
import traceback
from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION, SCRIPT_VERSION, SCRIPT_NAME_VERSION, resolve_path
from Duplicates import find_duplicates, process_duplicates_actions
from CustomLogger import set_log_level, CustomInMemoryLogHandler, CustomConsoleFormatter, CustomLogFormatter, clone_logger
from ClassTakeoutFolder import ClassTakeoutFolder
from ClassLocalFolder import ClassLocalFolder
from ClassSynologyPhotos import ClassSynologyPhotos
from ClassImmichPhotos import ClassImmichPhotos

class SharedData:
    def __init__(self, info, counters, logs_queue):
        self.info = info
        self.counters = counters
        self.logs_queue = logs_queue


####################################
# FEATURE: AUTOMATED-MIGRATION: #
####################################
def mode_AUTOMATED_MIGRATION(source=None, target=None, show_dashboard=None, show_gpth_progress=None, show_gpth_errors=None, parallel=None, log_level=logging.INFO):
    
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
        # if not source: source = ARGS['AUTOMATED-MIGRATION'][0]
        # if not target: target = ARGS['AUTOMATED-MIGRATION'][1]
        if not source: source = ARGS['source']
        if not target: target = ARGS['target']

        # Detect show_dashboard from the given arguments if it has not been provided on the function call
        if show_dashboard is None: show_dashboard = ARGS['dashboard']

        # Detect show_gpth_progress and show_gpth_errors from the given arguments if it has not been provided on the function call
        if show_gpth_progress is None: show_gpth_progress = ARGS['show-gpth-progress']
        if show_gpth_errors is None: show_gpth_errors = ARGS['show-gpth-errors']

        # Define the INTERMEDIATE_FOLDER
        INTERMEDIATE_FOLDER = resolve_path(f'./Temp_folder_{TIMESTAMP}')

        # ---------------------------------------------------------------------------------------------------------
        # 1) Creamos los objetos source_client y target_client en función de los argumentos source y target
        # ---------------------------------------------------------------------------------------------------------
        def get_client_object(client_type):
            """Retorna la instancia del cliente en función del tipo de fuente o destino."""

            # Return ClassSynologyPhotos
            if client_type.lower() in ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1']:
                return ClassSynologyPhotos(account_id=1)
            elif client_type.lower() in ['synology-photos-2', 'synology-photos2', 'synology-2', 'synology2']:
                return ClassSynologyPhotos(account_id=2)

            # Return ClassImmichPhotos
            elif client_type.lower() in ['immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1']:
                return ClassImmichPhotos(account_id=1)
            elif client_type.lower() in ['immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']:
                return ClassImmichPhotos(account_id=2)

            # Return ClassTakeoutFolder
            elif Path(client_type).is_dir() and (Utils.contains_zip_files(client_type) or Utils.contains_takeout_structure(client_type)):
                return ClassTakeoutFolder(client_type)              # In this clase, client_type is the path to the Takeout Folder

            # Return ClassLocalFolder
            elif Path(client_type).is_dir():
                return ClassLocalFolder(base_folder=client_type)    # In this clase, client_type is the path to the base Local Folder
            else:
                raise ValueError(f"ERROR   : Tipo de cliente no válido: {client_type}")

        # Creamos los objetos source_client y target_client y obtenemos sus nombres para mostrar en el show_dashboard
        source_client = get_client_object(source)
        source_client_name = source_client.get_client_name()
        SHARED_DATA.info.update({"source_client_name": source_client_name})

        target_client = get_client_object(target)
        target_client_name = target_client.get_client_name()
        SHARED_DATA.info.update({"target_client_name": target_client_name})

        # Check if source_client support specified filters
        unsupported_text = ""
        if isinstance(source_client, ClassTakeoutFolder) or isinstance(source_client, ClassTakeoutFolder):
            unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

        # Get the values from the arguments (if exists)
        type = ARGS.get('type', None)
        from_date = ARGS.get('from-date', None)
        to_date = ARGS.get('to-date', None)
        country = ARGS.get('country', None)
        city = ARGS.get('city', None)
        person = ARGS.get('person', None)

        LOGGER.info("")
        LOGGER.info(f"INFO    : -AUTO, --AUTOMATED-MIGRATION Mode detected")
        if not isinstance(source_client, ClassTakeoutFolder):
            LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE>', f"'{source}'").replace('<TARGET>', f"'{target}'"))
        else:
            LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{source}'").replace('<TARGET>', f"'{target}'").replace('Pulling', 'Analyzing and Fixing'))
        LOGGER.info(f"INFO    : Source Client  : {source_client_name}")
        LOGGER.info(f"INFO    : Target Client  : {target_client_name}")
        if parallel:
            LOGGER.info(f"INFO    : Migration Mode : Parallel")
        else:
            LOGGER.info(f"INFO    : Migration Mode : Secuential")
        if from_date or to_date or type or country or city or person:
            LOGGER.info(f"INFO    : Assets Filters :")
        else:
            LOGGER.info(f"INFO    : Assets Filters : None")
        if from_date:
            date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"INFO    : - From Date    : {date_obj.strftime('%Y-%m-%d')}")
        if to_date:
            date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"INFO    : - To Date      : {date_obj.strftime('%Y-%m-%d')}")
        if type:
            LOGGER.info(f"INFO    : - Type         : {type}")
        if country:
            LOGGER.info(f"INFO    : - Country      : {country} {unsupported_text}")
        if city:
            LOGGER.info(f"INFO    : - City         : {city} {unsupported_text}")
        if person:
            LOGGER.info(f"INFO    : - Person       : {person} {unsupported_text}")
        LOGGER.info(f"INFO    : Temp Folder    : {INTERMEDIATE_FOLDER}")
        LOGGER.info("")
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)

        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
            # Call the parallel_automated_migration module to do the whole migration process
            # parallel_automated_migration(source, target, temp_folder, SHARED_DATA.input_info, SHARED_DATA.counters, SHARED_DATA.logs_queue)
            # and if show_dashboard=True, launch start_dashboard function to show a Live Dashboard of the whole process
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

            # ---------------------------------------------------------------------------------------------------------
            # 1) Creamos un evento para indicar cuándo termina la migración
            migration_finished = threading.Event()
            # ---------------------------------------------------------------------------------------------------------

            # ------------------------------------------------------------------------------------------------------
            # 2) Lanzamos el show_dashboard en un hilo secundario (o viceversa).
            # ------------------------------------------------------------------------------------------------------
            if show_dashboard:
                dashboard_thread = threading.Thread(
                    target=start_dashboard,
                    kwargs={
                        "migration_finished": migration_finished,  # Pasamos un evento para indicar cuando ha terminado el proceso de migración
                        "SHARED_DATA": SHARED_DATA,  # Pasamos la instancia de la clase
                        "parallel": parallel, # Pasamos el modo de migración (parallel=True/False)
                        "log_level": logging.INFO
                    },
                    daemon=True  # El show_dashboard se cierra si el proceso principal termina
                )
                dashboard_thread.start()

                # Pequeña espera para garantizar que el show_dashboard ha arrancado antes de la migración
                time.sleep(2)

            LOGGER.info("")
            LOGGER.info(f'=======================================================================================================================================================')
            LOGGER.info(f'INFO    : 🚀 AUTOMATED MIGRATION JOB STARTED - {source_client_name} ➜ {target_client_name}')
            LOGGER.info(f'========================================================================================================================================================')
            LOGGER.info("")

            # ------------------------------------------------------------------------------------------------------
            # 3) Verifica y procesa source_client y target_client si es una instancia de ClassTakeoutFolder
            if isinstance(source_client, ClassTakeoutFolder):
                if source_client.needs_unzip or source_client.needs_process:
                    source_client.pre_process(capture_output=show_gpth_progress, capture_errors=show_gpth_errors)
            if isinstance(target_client, ClassTakeoutFolder):
                if target_client.needs_unzip or target_client.needs_process:
                    target_client.pre_process(capture_output=show_gpth_progress, capture_errors=show_gpth_errors)

            # ---------------------------------------------------------------------------------------------------------
            # 4) Ejecutamos la migración en el hilo principal (ya sea con descargas y subidas en paralelo o secuencial)
            # ---------------------------------------------------------------------------------------------------------
            try:
                parallel_automated_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, parallel=parallel, log_level=logging.INFO)
                # if parallel:
                #     parallel_automated_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, parallel=parallel, log_level=logging.INFO)
                # else:
                #     sequential_automated_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, log_level=logging.INFO)
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
# parallel_automated_migration Function #
#########################################
def parallel_automated_migration(source_client, target_client, temp_folder, SHARED_DATA, parallel=None, log_level=logging.INFO):
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
                        SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

                # Si la cola está muy llena (entre 50 y 100), reducir la velocidad en vez de bloquear
                if push_queue.qsize() > 50:
                    time.sleep(0.1)  # Pequeña pausa para no sobrecargar la cola
                    pass

            # Añadir a la cola y al registro global
            push_queue.put(item_dict)
            added_file_paths.add(asset_file_path)
            return True


    # ------------------
    # 1) HILO PRINCIPAL
    # ------------------
    def main_thread(parallel=None, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # Get source and target client names
            source_client_name = source_client.get_client_name()
            target_client_name = target_client.get_client_name()

            # Check if source_client support specified filters
            unsupported_text = ""
            if isinstance(source_client, ClassTakeoutFolder) or isinstance(source_client, ClassTakeoutFolder):
                unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

            # Get the values from the arguments (if exists)
            type = ARGS.get('type', None)
            from_date = ARGS.get('from-date', None)
            to_date = ARGS.get('to-date', None)
            country = ARGS.get('country', None)
            city = ARGS.get('city', None)
            person = ARGS.get('person', None)

            LOGGER.info(f"INFO    : 🚀 Starting Automated Migration Process: {source_client_name} ➜ {target_client_name}...")
            LOGGER.info(f"INFO    : Source Client  : {source_client_name}")
            LOGGER.info(f"INFO    : Target Client  : {target_client_name}")
            if parallel:
                LOGGER.info(f"INFO    : Migration Mode : Parallel")
            else:
                LOGGER.info(f"INFO    : Migration Mode : Sequential")

            if from_date or to_date or type or country or city or person:
                LOGGER.info(f"INFO    : Assets Filters :")
            else:
                LOGGER.info(f"INFO    : Assets Filters : None")
            if from_date:
                date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"INFO    : - From Date    : {date_obj.strftime('%Y-%m-%d')}")
            if to_date:
                date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"INFO    : - To Date      : {date_obj.strftime('%Y-%m-%d')}")
            if type:
                LOGGER.info(f"INFO    : - Type         : {type}")
            if country:
                LOGGER.info(f"INFO    : - Country      : {country} {unsupported_text}")
            if city:
                LOGGER.info(f"INFO    : - City         : {city} {unsupported_text}")
            if person:
                LOGGER.info(f"INFO    : - Person       : {person} {unsupported_text}")
            LOGGER.info(f"INFO    : Temp Folder    : {temp_folder}")
            LOGGER.info("")
            LOGGER.info(f"INFO    : Starting Pulling/Pushing Workers...")
            LOGGER.info(f"INFO    : Analyzing Source client and Applying filters. This process may take some time, please be patient...")

            # Get source client statistics:
            blocked_assets = []
            total_albums_blocked_count = 0
            total_assets_blocked_count = 0

            all_albums = source_client.get_albums_including_shared_with_user(log_level=logging.WARNING)
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
                    LOGGER.info(f"INFO    : Album '{album_name}' cannot be pulled because is a blocked shared album. Skipped!")
                    total_albums_blocked_count += 1
                    total_assets_blocked_count += album.get('item_count')
                    blocked_assets.extend(source_client.get_all_assets_from_album_shared(album_passphrase=album_passphrase, album_id=album_id, album_name=album_name, log_level=logging.WARNING))

            # Get all assets and filter out those blocked assets (from blocked shared albums) if any
            all_no_albums_assets = source_client.get_all_assets_without_albums(log_level=logging.WARNING)
            all_albums_assets = source_client.get_all_assets_from_all_albums(log_level=logging.WARNING)
            all_supported_assets = all_no_albums_assets + all_albums_assets
            blocked_assets_ids = {asset["id"] for asset in blocked_assets}
            filtered_all_supported_assets = [asset for asset in all_supported_assets if asset["id"] not in blocked_assets_ids]

            all_photos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['photo', 'live', 'image']]
            all_videos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['video']]
            all_assets = all_photos + all_videos
            all_metadata = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['metadata']]
            all_sidecar = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['sidecar']]
            all_invalid = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['unknown']]

            SHARED_DATA.info.update({
                "total_assets": len(all_assets),
                "total_photos": len(all_photos),
                "total_videos": len(all_videos),
                "total_albums": len(all_albums),
                "total_albums_blocked": total_albums_blocked_count,
                "total_metadata": len(all_metadata),
                "total_sidecar": len(all_sidecar),
                "total_invalid": len(all_invalid),  # Corrección de "unsopported" → "invalid"
            })

            SHARED_DATA.counters['total_albums_blocked'] = total_albums_blocked_count
            SHARED_DATA.counters['total_assets_blocked'] = total_assets_blocked_count

            LOGGER.info(f"INFO    : Input Info Analysis: ")
            for key, value in SHARED_DATA.info.items():
                LOGGER.info(f"INFO    :    {key}: {value}")

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
            # Obtain the number of Threads for the CPU and launch as many Push workers as max(1, int(cpu_total_threads/2))
            cpu_total_threads = os.cpu_count()
            LOGGER.info("")
            LOGGER.info(f"INFO    : CPU Total Threads Detected = {cpu_total_threads}")
            num_pull_threads = 1  # no Iniciar más de 1 hilo de descarga, de lo contrario los assets se descargarán multiples veces.
            LOGGER.info(f"INFO    : Launching {num_pull_threads} Pull worker in parallel...")
            num_push_threads = max(1, int(cpu_total_threads / 2))
            LOGGER.info(f"INFO    : Launching {num_push_threads} Push workers in parallel...")

            # Crear hilos
            pull_threads = [threading.Thread(target=puller_worker, kwargs={"parallel": parallel}, daemon=True) for _ in range(num_pull_threads)]
            push_threads = [threading.Thread(target=pusher_worker, kwargs={"processed_albums": processed_albums, "worker_id": worker_id + 1}, daemon=True) for worker_id in range(num_push_threads)]

            # Initiate pull threads
            for t in pull_threads:
                t.start()

            # If parallel mode, then initiate push threads in parallel
            if parallel:
                for t in push_threads:
                    t.start()

            # ----------------------------------------------------------------------------------------------
            # 2) Esperamos a que terminen los hilos de pull para mandar Nones a la cola de push,
            #    luego esperamos que la cola termine y finalmente esperamos que terminen los hilos de push
            # ----------------------------------------------------------------------------------------------

            # Esperar a que terminen los hilos de pull
            for t in pull_threads:
                t.join()

            # Enviamos tantos None como hilos de push para avisar que finalicen
            for _ in range(num_push_threads):
                push_queue.put(None)

            # If sequential mode, then initiate push threads only when pull threads have finished
            if not parallel:
                for t in push_threads:
                    t.start()

            # Esperamos a que la cola termine de procesarse
            # push_queue.join()

            # Esperar a que terminen los hilos de push
            for t in push_threads:
                t.join()

            # En este punto todos los pulls y pushs están listas y la cola está vacía.

            # Finalmente, borrar carpetas vacías que queden en temp_folder
            Utils.remove_empty_dirs(temp_folder)

            end_time = datetime.now()
            migration_formatted_duration = str(timedelta(seconds=(end_time - migration_start_time).seconds))
            total_formatted_duration = str(timedelta(seconds=(end_time - SHARED_DATA.info["start_time"]).seconds))

            # ----------------------------------------------------------------------------
            # 4) Mostrar o retornar contadores
            # ----------------------------------------------------------------------------
            LOGGER.info(f"")
            LOGGER.info(f"INFO    : 🚀 All assets pulled and pushed successfully!")
            LOGGER.info(f"")
            LOGGER.info(f"INFO    : ----- SINCRONIZACIÓN FINALIZADA -----")
            LOGGER.info(f"INFO    : {source_client_name} --> {target_client_name}")
            LOGGER.info(f"INFO    : Pulled Albums               : {SHARED_DATA.counters['total_pulled_albums']}")
            LOGGER.info(f"INFO    : Pushed Albums               : {SHARED_DATA.counters['total_pushed_albums']}")
            LOGGER.info(f"INFO    : Pulled Assets               : {SHARED_DATA.counters['total_pulled_assets']} (Photos: {SHARED_DATA.counters['total_pulled_photos']}, Videos: {SHARED_DATA.counters['total_pulled_videos']})")
            LOGGER.info(f"INFO    : Pushed Assets               : {SHARED_DATA.counters['total_pushed_assets']} (Photos: {SHARED_DATA.counters['total_pushed_photos']}, Videos: {SHARED_DATA.counters['total_pushed_videos']})")
            LOGGER.info(f"INFO    : Push Duplicates (skipped)   : {SHARED_DATA.counters['total_push_duplicates_assets']}")
            LOGGER.info(f"INFO    : Pull Failed Assets          : {SHARED_DATA.counters['total_pull_failed_assets']}")
            LOGGER.info(f"INFO    : Push Failed Assets          : {SHARED_DATA.counters['total_push_failed_assets']}")
            LOGGER.info(f"")
            LOGGER.info(f"INFO    : Migration Job completed in  : {migration_formatted_duration}")
            LOGGER.info(f"INFO    : Total Elapsed Time          : {total_formatted_duration}")
            LOGGER.info(f"")
            LOGGER.info(f"")
            return SHARED_DATA.counters

    # --------------------------------------------------------------------------------
    # 1) PULLER: Función puller_worker para descargar assets y poner en la cola
    # --------------------------------------------------------------------------------
    def puller_worker(parallel=None, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):

            # 1.1) Descarga de álbumes
            albums = source_client.get_albums_including_shared_with_user(log_level=logging.WARNING)
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
                is_shared = album_passphrase is not None and album_passphrase != "" # Si tiene passphrase, es compartido

                # Descargar todos los assets de este álbum
                try:
                    if not is_shared:
                        album_assets = source_client.get_all_assets_from_album(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                    else:
                        if album_shared_role.lower() != 'view':
                            album_assets = source_client.get_all_assets_from_album_shared(album_id=album_id, album_name=album_name, album_passphrase=album_passphrase, log_level=logging.WARNING)
                    if not album_assets:
                        # SHARED_DATA.counters['total_pull_failed_albums'] += 1     # If we uncomment this line, it will count as failed Empties albums
                        continue
                except Exception as e:
                    LOGGER.error(f"ERROR   : Error listing Album Assets for album {album_name} - {e} \n{traceback.format_exc()}")
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
                        # Descargar el asset
                        pulled_assets = source_client.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, album_passphrase=album_passphrase, download_folder=album_folder, log_level=logging.WARNING)
                        # Eliminar archivo de bloqueo después de la descarga
                        os.remove(lock_file)

                        # Actualizamos Contadores de descargas
                        if pulled_assets > 0:
                            LOGGER.info(f"INFO    : Asset Pulled    : '{os.path.join(album_folder, os.path.basename(asset_filename))}'")
                            # pulled_assets_ids.add(asset["id"])
                            SHARED_DATA.counters['total_pulled_assets'] += 1
                            if asset_type.lower() == 'video':
                                SHARED_DATA.counters['total_pulled_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pulled_photos'] += 1
                            # Enviar a la cola con la información necesaria para la subida
                            local_file_path = os.path.join(album_folder, asset_filename)
                            asset_dict = {
                                'asset_id': asset_id,
                                'asset_file_path': local_file_path,
                                'asset_datetime': asset_datetime,
                                'asset_type': asset_type,
                                'album_name': album_name,
                            }
                            # añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                            unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)  # Añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                            if not unique:
                                LOGGER.info(f"INFO    : Asset Duplicated: '{os.path.basename(local_file_path)}' from Album '{album_name}. Skipped")
                                SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                # Borrar asset de la carpeta temp_folder
                                if os.path.exists(local_file_path):
                                    try:
                                        os.remove(local_file_path)
                                    except:
                                        pass
                        else:
                            LOGGER.warning(f"WARNING : Asset Pull Fail : '{os.path.join(album_folder, os.path.basename(asset_filename))}' from Album '{album_name}'")
                            SHARED_DATA.counters['total_pull_failed_assets'] += 1
                            if asset_type.lower() == 'video':
                                SHARED_DATA.counters['total_pull_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pull_failed_photos'] += 1

                except Exception as e:
                    LOGGER.error(f"ERROR  : Asset Pull Error: '{os.path.basename(asset_filename)}' from Album '{album_name}' - {e} \n{traceback.format_exc()}")
                    SHARED_DATA.counters['total_pull_failed_assets'] += 1
                    if asset_type.lower() == 'video':
                        SHARED_DATA.counters['total_pull_failed_videos'] += 1
                    else:
                        SHARED_DATA.counters['total_pull_failed_photos'] += 1
                    continue
                finally:
                    # Eliminar archivo .active después de la descarga
                    if os.path.exists(active_file):
                        os.remove(active_file)

                # Incrementamos contador de álbumes descargados
                SHARED_DATA.counters['total_pulled_albums'] += 1
                LOGGER.info(f"INFO    : Album Pulled    : '{album_name}'")

            # 1.2) Descarga de assets sin álbum
            assets_no_album = []
            try:
                assets_no_album = source_client.get_all_assets_without_albums(log_level=logging.WARNING)
            except Exception as e:
                LOGGER.error(f"ERROR  : Error Getting Asset without Albums - {e} \n{traceback.format_exc()}")

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
                        pulled_assets = source_client.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=temp_folder, log_level=logging.WARNING)
                        # Eliminar archivo de bloqueo después de la descarga
                        os.remove(lock_file)
                    except Exception as e:
                        LOGGER.error(f"ERROR  : Asset Pull Error: '{os.path.basename(asset_filename)}' - {e} \n{traceback.format_exc()}")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
                        continue

                    # Si se ha hecho correctamente el pull del asset, actualizamos contadores y enviamos el asset a la cola de push
                    if pulled_assets > 0:
                        # Actualizamos Contadores de descargas
                        LOGGER.info(f"INFO    : Asset Pulled    : '{os.path.join(temp_folder, os.path.basename(asset_filename))}'")
                        SHARED_DATA.counters['total_pulled_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_pulled_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pulled_photos'] += 1

                        # Enviar a la cola de push con la información necesaria para la subida (sin album_name)
                        local_file_path = os.path.join(temp_folder, asset_filename)
                        asset_dict = {
                            'asset_id': asset_id,
                            'asset_file_path': local_file_path,
                            'asset_datetime': asset_datetime,
                            'asset_type': asset_type,
                            'album_name': None,
                        }
                        unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)  # Añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                        if not unique:
                            LOGGER.info(f"INFO    : Asset Duplicated: '{os.path.basename(local_file_path)}'. Skipped")
                            SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                            # Borrar asset de la carpeta temp_folder
                            if os.path.exists(local_file_path):
                                try:
                                    os.remove(local_file_path)
                                except:
                                    pass
                    else:
                        LOGGER.warning(f"WARNING : Asset Pull Fail : '{os.path.basename(asset_filename)}'")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
            finally:
                # Eliminar archivo .active después de la descarga
                if os.path.exists(active_file):
                    os.remove(active_file)

            LOGGER.info("INFO    : Puller Task Finished!")

    # ----------------------------------------------------------------------------
    # 2) PUSHER: Función pusher_worker para SUBIR (consumir de la cola)
    # ----------------------------------------------------------------------------
    def pusher_worker(processed_albums=[], worker_id=1, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):
            while True:
                try:
                    # Extraemos el siguiente asset de la cola
                    # time.sleep(0.7)  # Esto es por si queremos ralentizar el worker de subidas
                    asset = push_queue.get()
                    SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()
                    if asset is None:
                        # Si recibimos None, significa que ya no hay más trabajo
                        push_queue.task_done()
                        break

                    # Obtenemos las propiedades del asset extraido de la cola.
                    asset_id = asset['asset_id']
                    asset_file_path = asset['asset_file_path']
                    asset_datetime = asset['asset_datetime']
                    asset_type = asset['asset_type']
                    album_name = asset['album_name']
                    asset_pushed = False
                    try:
                        # SUBIR el asset
                        asset_id, isDuplicated = target_client.push_asset(file_path=asset_file_path, log_level=logging.WARNING)

                        # Actualizamos Contadores de subidas
                        if asset_id:
                            asset_pushed = True
                            if isDuplicated:
                                LOGGER.info(f"INFO    : Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped")
                                SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                            else:
                                SHARED_DATA.counters['total_pushed_assets'] += 1
                                if asset_type.lower() == 'video':
                                    SHARED_DATA.counters['total_pushed_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_pushed_photos'] += 1
                                LOGGER.info(f"INFO    : Asset Pushed    : '{asset_file_path}'")
                        else:
                            LOGGER.warning(f"WARNING : Asset Push Fail : '{os.path.basename(asset_filename)}'")
                            SHARED_DATA.counters['total_push_failed_assets'] += 1
                            if asset_type.lower() == 'video':
                                SHARED_DATA.counters['total_push_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_push_failed_photos'] += 1

                        # Borrar asset de la carpeta temp_folder tras subir
                        if os.path.exists(asset_file_path):
                            try:
                                os.remove(asset_file_path)
                            except:
                                pass
                    except:
                        LOGGER.error(f"ERROR   : Asset Push Fail : '{os.path.basename(asset_filename)}'")
                        LOGGER.error(f"ERROR   : Error Pushing Asset: '{os.path.basename(asset_file_path)}'")
                        LOGGER.error(f"ERROR   : Caught Exception: {e} \n{traceback.format_exc()}")
                        SHARED_DATA.counters['total_push_failed_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_push_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_push_failed_photos'] += 1

                    # Si existe album_name, manejar álbum en destino
                    if album_name and asset_pushed:
                        try:
                            # Si el álbum no existe en destino, lo creamos
                            album_exists, album_id_dest = target_client.album_exists(album_name=album_name, log_level=logging.WARNING)
                            if not album_exists:
                                album_id_dest = target_client.create_album(album_name=album_name, log_level=logging.WARNING)
                            # Añadir el asset al álbum
                            target_client.add_assets_to_album(album_id=album_id_dest, asset_ids=asset_id, album_name=album_name, log_level=logging.WARNING)
                        except Exception as e:
                            LOGGER.error(f"ERROR   : Album Push Fail : '{album_name}'")
                            LOGGER.error(f"ERROR   : Caught Exception: {e} \n{traceback.format_exc()}")
                            SHARED_DATA.counters['total_push_failed_albums'] += 1

                        # Verificar si la carpeta local del álbum está vacía y borrarla
                        album_folder_path = os.path.join(temp_folder, album_name)
                        if os.path.exists(album_folder_path):
                            try:
                                # Si la carpeta tiene un archivo .active, significa que aún está en uso → NO BORRAR
                                active_file = os.path.join(album_folder_path, ".active")
                                if os.path.exists(active_file):
                                    # No se borra porque aún está en uso
                                    continue
                                # Si la carpeta está vacía (o solo hay subcarpetas vacías), la borramos, de lo contrario saltaremos al bloque except generando una excepción que ignoraremos
                                os.rmdir(album_folder_path)
                                # Actualizamos contadores si el borrado de la carpeta ha tenido éxito (significa que el album está totalmente subido ya que el puller ha quitado el archivo .active y los pusher han borrado todos los archivos subidos)
                                # Sólo actualizamos contadores si el album no había sido procesado antes
                                if album_name not in processed_albums:
                                    processed_albums.append(album_name)  # Lo incluimos en la lista de albumes procesados
                                    SHARED_DATA.counters['total_pushed_albums'] += 1
                                    SHARED_DATA.counters['total_pushed_albums'] = min(SHARED_DATA.counters['total_pushed_albums'], SHARED_DATA.counters['total_pulled_albums'])  # Avoid to set total_pushed_albums > total_pulled_albums
                                    LOGGER.info(f"INFO    : Album Pushed    : '{album_name}'")
                            except OSError:
                                # Si no está vacía, ignoramos el error
                                pass

                    push_queue.task_done()

                except Exception as e:
                    LOGGER.error(f"ERROR   : Error in Pusher worker while pushing asset: {asset}")
                    LOGGER.error(f"ERROR   : Caught Exception: {e} \n{traceback.format_exc()}")

            LOGGER.info(f"INFO    : Pusher {worker_id} - Task Finished!")


    # ----------------------------
    # 4) LLAMADA AL HILO PRINCIPAL
    # ----------------------------

    # Inicializamos start_time para medir el tiempo de procesamiento
    migration_start_time = datetime.now()

    # Preparar la cola que compartiremos entre descargas y subidas
    push_queue = Queue()

    # Set global para almacenar paths ya añadidos
    added_file_paths = set()

    # Lock global para proteger el acceso concurrente
    file_paths_lock = threading.Lock()

    # Normalizamos temp_folder
    temp_folder = Utils.normalize_path(temp_folder)

    # Check if parallel=None, and in that case, get it from ARGS
    if parallel is None: parallel = ARGS['parallel-migration']

    # Llamada al hilo principal
    main_thread(parallel=parallel, log_level=log_level)


###########################
# start_dashboard Function #
###########################
def start_dashboard(migration_finished, SHARED_DATA, parallel=True, log_level=logging.INFO):
    import time, random, threading
    from datetime import datetime
    from rich.console import Console
    from rich.layout import Layout
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.columns import Columns
    import collections
    import queue
    import textwrap
    from CustomLogger import LoggerStream
    from CustomLogger import LoggerCapture

    # Min Terminal Height and Width to display the Live Dashboard
    MIN_TERMINAL_HEIGHT = 30
    MIN_TERMINAL_WIDTH  = 100

    # Calculate terminal_height and terminal_width
    console = Console()
    terminal_height = console.size.height
    terminal_width = console.size.width

    LOGGER.info(f"INFO    : Detected terminal height = {terminal_height}")
    LOGGER.info(f"INFO    : Detected terminal width  = {terminal_width}")

    if terminal_height < MIN_TERMINAL_HEIGHT:
        LOGGER.info(f"INFO    : Cannot display Live Dashboard because the detected terminal height = {terminal_height} and the minumum needed height = {MIN_TERMINAL_HEIGHT}. Continuing without Live Dashboard...")
        ARGS['dashboard'] = False # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
        return

    if terminal_width < MIN_TERMINAL_WIDTH:
        LOGGER.info(f"INFO    : Cannot display Live Dashboard because the detected terminal width = {terminal_width} and the minumum needed width = {MIN_TERMINAL_WIDTH}. Continuing without Live Dashboard...")
        ARGS['dashboard'] = False  # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
        return

    # Iniciamos el contador de tiempo transcurrido
    step_start_time = datetime.now()

    layout = Layout()
    layout.size = terminal_height

    # 🚀 Guardar stdout y stderr originales
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # # 🚀 Forzar la redirección de sys.stderr globalmente para asegurar que no se imprima en pantalla
    # sys.stderr = sys.__stderr__ = LoggerCapture(LOGGER, logging.ERROR)
    #
    # # 🚀 Capturar e interceptar manualmente cualquier error antes de que `rich` lo maneje
    # def log_exceptions(exctype, value, tb):
    #     """Captura todas las excepciones no manejadas y las guarda en el LOGGER sin imprimir en pantalla"""
    #     error_message = "".join(traceback.format_exception(exctype, value, tb))
    #     LOGGER.error("Excepción no manejada:\n" + error_message)  # Guardar en logs sin imprimir en consola
    #
    # sys.excepthook = log_exceptions

    # Eliminar solo los StreamHandler sin afectar los FileHandler
    for handler in list(LOGGER.handlers):  # Hacer una copia de la lista para evitar problemas al modificarla
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            LOGGER.removeHandler(handler)

    # Crea el handler y configúralo con un formatter
    memory_handler = CustomInMemoryLogHandler(SHARED_DATA.logs_queue)
    memory_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    memory_handler.setLevel(log_level)

    # Agrega el handler al LOGGER
    LOGGER.addHandler(memory_handler)

    # Opcional: si NO quieres imprimir por consola, puedes quitar el StreamHandler que tenga el logger por defecto (así solo se registran en la lista).
    # Por ejemplo:
    LOGGER.propagate = False
    log_file = Utils.get_logger_filename(LOGGER)

    # Split layout: header_panel (8 lines), title_panel (3 lines), content_panel (12 lines), logs fill remainder
    layout.split_column(
        Layout(name="empty_line_1", size=1),  # Línea vacía
        Layout(name="header_panel", size=8),
        Layout(name="title_panel", size=3),
        Layout(name="content_panel", size=12),
        Layout(name="logs_panel", ratio=1),
        Layout(name="empty_line_2", size=1),  # Línea vacía
    )

    # Obtener el height de cada panel
    empty_line_1_height = layout["empty_line_1"].size
    header_panel_height = layout["header_panel"].size
    title_panel_height = layout["title_panel"].size
    content_panel_height = layout["content_panel"].size
    empty_line_2_height = layout["empty_line_2"].size

    # Calcular logs_panel en función del espacio restante
    fixed_heights = sum([empty_line_1_height, header_panel_height, title_panel_height, content_panel_height, empty_line_2_height])
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
    header =  textwrap.dedent(rf"""
      ____ _                 _ ____  _           _        __  __ _                 _
     / ___| | ___  _   _  __| |  _ \| |__   ___ | |_ ___ |  \/  (_) __ _ _ __ __ _| |_ ___  _ __
    | |   | |/ _ \| | | |/ _` | |_) | '_ \ / _ \| __/ _ \| |\/| | |/ _` | '__/ _` | __/ _ \| '__|
    | |___| | (_) | |_| | (_| |  __/| | | | (_) | || (_) | |  | | | (_| | | | (_| | || (_) | |
     \____|_|\___/ \__,_|\__,_|_|   |_| |_|\___/ \__\___/|_|  |_|_|\__, |_|  \__,_|\__\___/|_|
                                                                   |___/ {SCRIPT_VERSION}
    """).lstrip("\n")  # Elimina solo la primera línea en blanco
    layout["header_panel"].update(Panel(f"[gold1]{header}[/gold1]", border_style="gold1", expand=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 1) Title Panel
    # ─────────────────────────────────────────────────────────────────────────
    title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automated Migration - {SCRIPT_NAME_VERSION}"

    layout["title_panel"].update(Panel(f"🚀 {title}", border_style="bright_blue", expand=True))

    def update_title_panel():
        title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automated Migration - {SCRIPT_NAME_VERSION}"
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
                bar_width=100,           # longer bar for better visuals
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
    pull_bars = { # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
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


    # ─────────────────────────────────────────────────────────────────────────
    # 5) Logging Panel from Memmory Handler
    # ─────────────────────────────────────────────────────────────────────────
    # Lista (o deque) para mantener todo el historial de logs ya mostrados
    logs_panel_height = terminal_height - fixed_heights - 2  # Espacio restante. Restamos 2 para quitar las líneas del borde superior e inferior del panel de Logs
    ACCU_LOGS = deque(maxlen=logs_panel_height)

    def build_log_panel():
        """
        Lee todos los mensajes pendientes en shared_data.logs_queue y los añade
        a ACCU_LOGS, que conserva el historial completo.
        Devuelve un Panel con todo el historial (de modo que se pueda hacer
        scroll en la terminal si usas vertical_overflow='visible').
        """
        title_logs_panel = f"📜 Logs Panel (Only last {logs_panel_height} rows shown. Complete log file at: '{log_file}')"
        try:
            while True:
                # 1) Vaciamos la cola de logs, construyendo el historial completo
                try:
                    line = SHARED_DATA.logs_queue.get_nowait()  # lee un mensaje de la cola
                except queue.Empty:
                    break

                # Opcional: aplica color según la palabra “pull”/”push”
                line_lower = line.lower()
                if "warning :" in line_lower:
                    line_colored = f"[yellow]{line}[/yellow]"
                elif "error   :" in line_lower:
                    line_colored = f"[red]{line}[/red]"
                elif "debug   :" in line_lower:
                    line_colored = f"[#EEEEEE]{line}[/#EEEEEE]"
                elif "pull" in line_lower and not "push" in line_lower:
                    line_colored = f"[cyan]{line}[/cyan]"
                elif any(word in line_lower for word in ("push", "created", "duplicated")) and not "pull" in line_lower:
                    line_colored = f"[green]{line}[/green]"
                else:
                    line_colored = f"[bright_white]{line}[/bright_white]"

                # Añadimos la versión coloreada al historial
                ACCU_LOGS.append(line_colored)

            # 2) Unimos todo el historial en un solo string
            if ACCU_LOGS:
                logs_text = "\n".join(ACCU_LOGS)
            else:
                logs_text = "Initializing..."

            # 3) Construimos el panel y lo devolvemos
            log_panel = Panel(logs_text, title=title_logs_panel, border_style="bright_red", expand=True, title_align="left")
            return log_panel

        except Exception as e:
            LOGGER.error(f"ERROR   : Building Log Panel: {e}")


    # ─────────────────────────────────────────────────────────────────────────
    # 6) Main Live Loop
    # ─────────────────────────────────────────────────────────────────────────
    with Live(layout, refresh_per_second=1, console=console, vertical_overflow="crop"):
        try:
            update_title_panel()
            layout["info_panel"].update(build_info_panel())
            layout["pulls_panel"].update(build_pull_panel())
            layout["pushs_panel"].update(build_push_panel())
            layout["logs_panel"].update(build_log_panel())
            # layout["logs_panel"].update(log_panel)  # inicializamos el panel solo una vez aquí

            # Continue the loop until migration_finished.is_set()
            while not migration_finished.is_set():
                SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=(datetime.now() - step_start_time).seconds))
                layout["info_panel"].update(build_info_panel())
                layout["pulls_panel"].update(build_pull_panel())
                layout["pushs_panel"].update(build_push_panel())
                layout["logs_panel"].update(build_log_panel())
                time.sleep(0.5)  # Evita un bucle demasiado agresivo

            # Pequeña pausa adicional para asegurar el dibujado final
            time.sleep(1)

            # Al terminar, asegurarse que todos los paneles finales se muestren
            layout["info_panel"].update(build_info_panel(clean_queue_history=True))     # Limpiamos el histórico de la cola
            layout["pulls_panel"].update(build_pull_panel())
            layout["pushs_panel"].update(build_push_panel())
            layout["logs_panel"].update(build_log_panel())

        finally:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr


######################
# CALL FROM __MAIN__ #
######################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    import ChangeWorkingDir
    ChangeWorkingDir.change_working_dir(change_dir=False)

    # # Paths para Windows
    local_folder = r'r:\jaimetur\CloudPhotoMigrator\LocalFolderClient'
    takeout_folder = r'r:\jaimetur\CloudPhotoMigrator\Takeout'
    takeout_folder_zipped = r'r:\jaimetur\CloudPhotoMigrator\Zip_files_prueba_rapida'
    
    # Paths para Linux
    # local_folder = r'/mnt/homes/jaimetur/CloudPhotoMigrator/LocalFolderClient'
    # takeout_folder = r'/mnt/homes/jaimetur/CloudPhotoMigrator/Takeout'
    # takeout_folder_zipped = r'/mnt/homes/jaimetur/CloudPhotoMigrator/Zip_files_prueba_rapida'

    # Define source and target
    source = takeout_folder_zipped
    target = 'synology-photos'

    mode_AUTOMATED_MIGRATION(source=source, target=target, show_dashboard=True, parallel=True, show_gpth_progress=True)
