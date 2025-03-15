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
import Utils
from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION, SCRIPT_VERSION, SCRIPT_NAME_VERSION
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
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_AUTOMATED_MIGRATION(source=None, target=None, show_dashboard=None, parallel=True, log_level=logging.INFO):
    
    with set_log_level(LOGGER, log_level):

        # ───────────────────────────────────────────────────────────────
        # Declare shared variables to pass as reference to both functions
        # ───────────────────────────────────────────────────────────────

        # Cola que contendrá los mensajes de log en memoria
        logs_queue = Queue()

        # Contadores globales
        counters = {
            'total_downloaded_assets': 0,
            'total_downloaded_photos': 0,
            'total_downloaded_videos': 0,
            'total_downloaded_albums': 0,
            'total_download_failed_assets': 0,
            'total_download_failed_photos': 0,
            'total_download_failed_videos': 0,
            'total_download_failed_albums': 0,

            'total_uploaded_assets': 0,
            'total_uploaded_photos': 0,
            'total_uploaded_videos': 0,
            'total_uploaded_albums': 0,
            'total_upload_failed_assets': 0,
            'total_upload_failed_photos': 0,
            'total_upload_failed_videos': 0,
            'total_upload_failed_albums': 0,
            'total_upload_duplicates_assets': 0,
        }

        # Input INFO
        input_info = {
            "source_client_name": "Source Client",
            "target_client_name": "Target Client",
            "total_assets": 0,
            "total_photos": 0,
            "total_videos": 0,
            "total_albums": 0,
            "total_metadata": 0,
            "total_sidecar": 0,
            "total_unsupported": 0,
            "assets_in_queue": 0,
            "elapsed_time": 0,
        }

        SHARED_DATA = SharedData(input_info, counters, logs_queue)

        if not source: source = ARGS['AUTOMATED-MIGRATION'][0]
        if not target: target = ARGS['AUTOMATED-MIGRATION'][1]
        if not show_dashboard: show_dashboard = ARGS['dashboard']

        # Define the INTERMEDIATE_FOLDER
        INTERMEDIATE_FOLDER = f'./Temp_folder_{TIMESTAMP}'

        # ---------------------------------------------------------------------------------------------------------
        # 1) Creamos los objetos source_client y target_client en función de los argumentos source y target
        # ---------------------------------------------------------------------------------------------------------
        def get_client_object(client_type):
            """Retorna la instancia del cliente en función del tipo de fuente o destino."""

            # Return ClassSynologyPhotos
            if client_type.lower() in ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1']:
                return ClassSynologyPhotos(ACCOUNT_ID=1)
            elif client_type.lower() in ['synology-photos-2', 'synology-photos2', 'synology-2', 'synology2']:
                return ClassSynologyPhotos(ACCOUNT_ID=2)

            # Return ClassImmichPhotos
            elif client_type.lower() in ['immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1']:
                return ClassImmichPhotos(ACCOUNT_ID=1)
            elif client_type.lower() in ['immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']:
                return ClassImmichPhotos(ACCOUNT_ID=2)

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

        LOGGER.info("")
        LOGGER.info(f"INFO    : -AUTO, --AUTOMATED-MIGRATION Mode detected")
        if not isinstance(source_client, ClassTakeoutFolder):
            LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE>', f"'{source}'").replace('<TARGET>', f"'{target}'"))
        else:
            LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{source}'").replace('<TARGET>', f"'{target}'").replace('Downloading', 'Analyzing and Fixing'))
        LOGGER.info(f"INFO    : Selected source : {source_client_name}")
        LOGGER.info(f"INFO    : Selected target : {target_client_name}")
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
                        "log_level": logging.INFO
                    },
                    daemon=True  # El show_dashboard se cierra si el proceso principal termina
                )
                dashboard_thread.start()

                # Pequeña espera para garantizar que el show_dashboard ha arrancado antes de la migración
                time.sleep(1)

            LOGGER.info("")
            LOGGER.info(f'=========================================================================================================')
            LOGGER.info(f'INFO    : AUTOMATED MIGRATION JOB STARTED -  {source_client_name} -> {target_client_name}')
            LOGGER.info(f'=========================================================================================================')
            LOGGER.info("")

            # ------------------------------------------------------------------------------------------------------
            # 3) Verifica y procesa source_client y target_client si es una instancia de ClassTakeoutFolder
            if isinstance(source_client, ClassTakeoutFolder):
                if source_client.needs_unzip or source_client.needs_process:
                    source_client.pre_process()
            if isinstance(target_client, ClassTakeoutFolder):
                if target_client.needs_unzip or target_client.needs_process:
                    target_client.pre_process()

            # ---------------------------------------------------------------------------------------------------------
            # 4) Ejecutamos la migración en el hilo principal (ya sea con descargas y subidas en paralelo o secuencial)
            # ---------------------------------------------------------------------------------------------------------
            try:
                if parallel:
                    parallel_automated_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, log_level=logging.INFO)
                else:
                    secuencial_automated_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, log_level=logging.INFO)
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
def parallel_automated_migration(source_client, target_client, temp_folder, SHARED_DATA, log_level=logging.INFO):
    """
    Sincroniza fotos y vídeos entre un 'source_client' y un 'destination_client',
    descargando álbumes y assets desde la fuente, y luego subiéndolos a destino,
    de forma concurrente mediante una cola de proceso.

    Parámetros:
    -----------
    source_client: objeto con los métodos:
        - get_albums_including_shared_with_user() -> [ { 'id': ..., 'name': ... }, ... ]
        - get_album_assets(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_no_albums_assets() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - download_asset(asset_id, download_path) -> str (ruta local del archivo descargado)

    target_client: objeto con los métodos:
        - create_album(album_name) -> album_id
        - album_exists(album_name) -> (bool, album_id_o_None)
        - upload_asset(asset_file_path, asset_datetime) -> asset_id
        - add_asset_to_album(album_id, asset_id) -> None

    temp_folder: str
        Carpeta temporal donde se descargarán los assets antes de subirse.
    """

    start_time = datetime.now()

    # Preparar la cola que compartiremos entre descargas y subidas
    upload_queue = Queue()

    # Set global para almacenar paths ya añadidos
    added_file_paths = set()

    # Lock global para proteger el acceso concurrente
    file_paths_lock = threading.Lock()

    temp_folder = Utils.normalize_path(temp_folder)

    # --------------------------------------------------------------------------------
    # 1) DESCARGAS: Función downloader_worker para descargar assets y poner en la cola
    # --------------------------------------------------------------------------------
    def downloader_worker(log_level=logging.INFO):

        def enqueue_unique(upload_queue, item_dict):
            """
            Añade item_dict a la cola si su asset_file_path no ha sido añadido previamente.
            Thread-safe gracias al lock global.
            """
            with file_paths_lock:
                asset_file_path = item_dict['asset_file_path']
                SHARED_DATA.info['assets_in_queue'] = upload_queue.qsize()

                if asset_file_path in added_file_paths:
                    # El item ya fue añadido anteriormente
                    return False

                # Pausa si la cola tiene más de 100 elementos, pero no bloquea innecesariamente
                while upload_queue.qsize() >= 100:
                    time.sleep(10)  # Hacemos una pausa de 10s para que la cola se vacíe
                    SHARED_DATA.info['assets_in_queue'] = upload_queue.qsize()

                # Si la cola está muy llena (entre 50 y 100), reducir la velocidad en vez de bloquear
                if upload_queue.qsize() > 50:
                    time.sleep(0.15)  # Pequeña pausa para no sobrecargar la cola
                    pass

                # Añadir a la cola y al registro global
                upload_queue.put(item_dict)
                added_file_paths.add(asset_file_path)
                return True

        with set_log_level(LOGGER, log_level):
            # 1.1) Descarga de álbumes
            albums = source_client.get_albums_including_shared_with_user()
            downloaded_assets = 0
            for album in albums:
                album_id = album['id']
                album_name = album['albumName']

                # Incrementamos contador de álbumes descargados
                SHARED_DATA.counters['total_downloaded_albums'] += 1

                # Descargar todos los assets de este álbum
                try:
                    album_assets = source_client.get_album_assets(album_id)
                    if not album_assets:
                        SHARED_DATA.counters['total_download_failed_albums'] += 1
                except:
                    SHARED_DATA.counters['total_download_failed_albums'] += 1

                for asset in album_assets:
                    asset_id = asset['id']
                    asset_type = asset['type']
                    asset_datetime = asset.get('time')
                    asset_filename = asset.get('filename')

                    # Skip download metadata and sidecar for the time being
                    if asset_type in ['metadata', 'sidecar']:
                        continue

                    # Crear carpeta del álbum dentro de temp_folder
                    album_folder = os.path.join(temp_folder, album_name)
                    os.makedirs(album_folder, exist_ok=True)

                    try:
                        # Ruta del archivo descargado
                        local_file_path = os.path.join(album_folder, asset_filename)

                        # Archivo de bloqueo temporal
                        lock_file = local_file_path + ".lock"

                        # Crear archivo de bloqueo antes de la descarga
                        with open(lock_file, 'w') as lock:
                            lock.write("Downloading")
                            # Descargar el asset
                            downloaded_assets = source_client.download_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=album_folder, log_level=logging.WARNING)
                        # Eliminar archivo de bloqueo después de la descarga
                        os.remove(lock_file)
                    except Exception as e:
                        LOGGER.error(f"ERROR  : Error Downloading Asset: '{os.path.basename(asset_filename)}'")
                        SHARED_DATA.counters['total_download_failed_assets'] += 1

                    # set_log_level(LOGGER, log_level)
                    LOGGER.info(f"INFO    : Asset Downloaded: '{os.path.join(album_folder, os.path.basename(asset_filename))}'")
                    # LOGGER.debug(f"DEBUG   : Asset Downloaded: '{os.path.basename(asset_filename)}'")

                    # Actualizamos Contadores de descargas
                    if downloaded_assets > 0:
                        SHARED_DATA.counters['total_downloaded_assets'] += downloaded_assets
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_downloaded_videos'] += downloaded_assets
                        else:
                            SHARED_DATA.counters['total_downloaded_photos'] += downloaded_assets
                    else:
                        SHARED_DATA.counters['total_download_failed_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_download_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_download_failed_photos'] += 1

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
                    enqueue_unique(upload_queue, asset_dict)
                    # upload_queue.put(asset_dict)
                    # sys.stdout.flush()
                    # sys.stderr.flush()

                LOGGER.info(f"INFO    : Album Downloaded: '{album_name}'")

            # 1.2) Descarga de assets sin álbum
            try:
                assets_no_album = source_client.get_no_albums_assets()
            except Exception as e:
                LOGGER.error(f"ERROR  : Error Getting Asset without Albums")
                SHARED_DATA.counters['total_download_failed_albums'] += 1

            downloaded_assets = 0
            for asset in assets_no_album:
                asset_id = asset['id']
                asset_type = asset['type']
                asset_datetime = asset.get('time')
                asset_filename = asset.get('filename')

                # Skip download metadata and sidecar for the time being
                if asset_type in ['metadata', 'sidecar']:
                    continue

                try:
                    # Ruta del archivo descargado
                    local_file_path = asset_id

                    # Archivo de bloqueo temporal
                    lock_file = local_file_path + ".lock"

                    # Crear archivo de bloqueo antes de la descarga
                    with open(lock_file, 'w') as lock:
                        lock.write("Downloading")
                        # Descargar directamente en temp_folder
                        downloaded_assets = source_client.download_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=temp_folder, log_level=logging.WARNING)
                    # Eliminar archivo de bloqueo después de la descarga
                    os.remove(lock_file)
                except Exception as e:
                    LOGGER.error(f"ERROR  : Error Downloading Asset: '{os.path.basename(asset_filename)}'")
                    SHARED_DATA.counters['total_download_failed_assets'] += 1

                local_file_path = os.path.join(temp_folder, asset_filename)
                # set_log_level(LOGGER, log_level)
                LOGGER.info(f"INFO    : Asset Downloaded: '{os.path.join(temp_folder, os.path.basename(asset_filename))}'")

                # Actualizamos Contadores de descargas
                if downloaded_assets > 0:
                    SHARED_DATA.counters['total_downloaded_assets'] += downloaded_assets
                    if asset_type.lower() == 'video':
                        SHARED_DATA.counters['total_downloaded_videos'] += downloaded_assets
                    else:
                        SHARED_DATA.counters['total_downloaded_photos'] += downloaded_assets
                else:
                    SHARED_DATA.counters['total_download_failed_assets'] += 1
                    if asset_type.lower() == 'video':
                        SHARED_DATA.counters['total_download_failed_videos'] += 1
                    else:
                        SHARED_DATA.counters['total_download_failed_photos'] += 1

                # Enviar a la cola sin album_name
                asset_dict = {
                    'asset_id': asset_id,
                    'asset_file_path': local_file_path,
                    'asset_datetime': asset_datetime,
                    'asset_type': asset_type,
                    'album_name': None,
                }
                # añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                enqueue_unique(upload_queue, asset_dict)
                # upload_queue.put(asset_dict)
                # sys.stdout.flush()
                # sys.stderr.flush()

            LOGGER.info("INFO    : Downloader Task Finished!")

    # ----------------------------------------------------------------------------
    # 2) SUBIDAS: Función uploader_worker para SUBIR (consumir de la cola)
    # ----------------------------------------------------------------------------
    def uploader_worker(log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):
            # Lista para marcar álbumes procesados (ya contados y/o creados en el destino)
            processed_albums = []
            while True:
                # with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
                try:
                    # Extraemos el siguiente asset de la cola
                    asset = upload_queue.get()
                    SHARED_DATA.info['assets_in_queue'] = upload_queue.qsize()
                    if asset is None:
                        # Si recibimos None, significa que ya no hay más trabajo
                        upload_queue.task_done()
                        break

                    # Obtenemos las propiedades del asset extraido de la cola.
                    asset_id = asset['asset_id']
                    asset_file_path = asset['asset_file_path']
                    asset_datetime = asset['asset_datetime']
                    asset_type = asset['asset_type']
                    album_name = asset['album_name']
                    asset_uploaded = False
                    try:
                        # SUBIR el asset
                        asset_id, isDuplicated = target_client.upload_asset(file_path=asset_file_path, log_level=logging.WARNING)

                        # Actualizamos Contadores de subidas
                        if asset_id:
                            asset_uploaded = True
                            if isDuplicated:
                                LOGGER.info(f"INFO    : Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped")
                                SHARED_DATA.counters['total_upload_duplicates_assets'] += 1
                            else:
                                SHARED_DATA.counters['total_uploaded_assets'] += 1
                                if asset_type.lower() == 'video':
                                    SHARED_DATA.counters['total_uploaded_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_uploaded_photos'] += 1
                                LOGGER.info(f"INFO    : Asset Uploaded  : '{asset_file_path}'")
                        else:
                            SHARED_DATA.counters['total_upload_failed_assets'] += 1
                            if asset_type.lower() == 'video':
                                SHARED_DATA.counters['total_upload_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_upload_failed_photos'] += 1

                        # Borrar asset de la carpeta temp_folder tras subir
                        if os.path.exists(asset_file_path):
                            try:
                                os.remove(asset_file_path)
                            except:
                                pass
                    except:
                        SHARED_DATA.counters['total_upload_failed_assets'] += 1
                        if asset_type.lower() == 'video':
                            SHARED_DATA.counters['total_upload_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_upload_failed_photos'] += 1

                    # Si existe album_name, manejar álbum en destino
                    if album_name and asset_uploaded:
                        # Comprobamos si ya procesamos antes este álbum
                        if album_name not in processed_albums:
                            processed_albums.append(album_name)  # Lo incluimos en la lista de albumes procesados
                            SHARED_DATA.counters['total_uploaded_albums'] += 1
                            LOGGER.info(f"INFO    : Album Created  : '{album_name}'")
                        try:
                            # Si el álbum no existe en destino, lo creamos
                            album_exists, album_id_dest = target_client.album_exists(album_name=album_name, log_level=logging.WARNING)
                            if not album_exists:
                                album_id_dest = target_client.create_album(album_name=album_name, log_level=logging.WARNING)

                            # Añadir el asset al álbum
                            target_client.add_assets_to_album(album_id=album_id_dest, asset_ids=asset_id, album_name=album_name, log_level=logging.WARNING)
                        except:
                            SHARED_DATA.counters['total_upload_failed_albums'] += 1

                        # Verificar si la carpeta local del álbum está vacía y borrarla
                        album_folder_path = os.path.join(temp_folder, album_name)
                        if os.path.exists(album_folder_path):
                            # Si la carpeta está vacía (o solo hay subcarpetas vacías), la borramos
                            try:
                                os.rmdir(album_folder_path)
                            except OSError:
                                # Si no está vacía, ignoramos el error
                                pass

                    upload_queue.task_done()
                    # sys.stdout.flush()
                    # sys.stderr.flush()

                except Exception as e:
                    LOGGER.error(f"ERROR   : Error in Uploader worker while uploading asset: {asset}")
                    LOGGER.error(f"ERROR   : Catched Exception: {e}")

            LOGGER.info(f"INFO    : Uploader Task Finished!")

    # ------------------
    # 3) HILO PRINCIPAL
    # ------------------
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Get source and target client names
        source_client_name = source_client.get_client_name()
        target_client_name = target_client.get_client_name()
        LOGGER.info(f"")
        LOGGER.info(f"INFO    : Starting Downloading/Uploading Process...")
        LOGGER.info(f"INFO    : Source Client: {source_client_name}")
        LOGGER.info(f"INFO    : Target Client: {target_client_name}")
        LOGGER.info(f"INFO    : Starting Automated Migration Process: {source_client_name} ➜ {target_client_name}...")

        # Get source client statistics:
        all_albums = source_client.get_albums_including_shared_with_user()
        all_supported_assets = source_client.get_all_assets()

        all_photos = [asset for asset in all_supported_assets if asset['type'].lower() in ['photo', 'live', 'image']]
        all_videos = [asset for asset in all_supported_assets if asset['type'].lower() in ['video']]
        all_medias = all_photos + all_videos
        all_metadata = [asset for asset in all_supported_assets if asset['type'].lower() in ['metadata']]
        all_sidecar = [asset for asset in all_supported_assets if asset['type'].lower() in ['sidecar']]
        all_unsupported = [asset for asset in all_supported_assets if asset['type'].lower() in ['unknown']]

        SHARED_DATA.info.update({
            "total_assets": len(all_medias),
            "total_photos": len(all_photos),
            "total_videos": len(all_videos),
            "total_albums": len(all_albums),
            "total_metadata": len(all_metadata),
            "total_sidecar": len(all_sidecar),
            "total_unsupported": len(all_unsupported),  # Corrección de "unsopported" → "unsupported"
        })
        LOGGER.info(f"INFO    : Input Info Analysis: ")
        for key, value in SHARED_DATA.info.items():
            LOGGER.info(f"INFO    :    {key}: {value}")

        # ------------------------------------------------------------------------------------------------------
        # 1) Iniciar uno o varios hilos de descargas y subidas para manejar las descargas y subidas concurrentes
        # ------------------------------------------------------------------------------------------------------
        # Obtain the number of Threads for the CPU and launch as many Upload workers as max(1, int(cpu_total_threads/2))
        cpu_total_threads = os.cpu_count()
        LOGGER.info("")
        LOGGER.info(f"INFO    : CPU Total Threads Detected = {cpu_total_threads}")
        num_upload_threads = max(1, int(cpu_total_threads / 2))
        LOGGER.info(f"INFO    : Launching {num_upload_threads} Upload workers in parallel...")
        num_download_threads = 1  # no Iniciar más de 1 hilo de descarga, de lo contrario los assets se descargarán multiples veces.

        # Crear hilos
        download_threads = [threading.Thread(target=downloader_worker, daemon=True) for _ in range(num_download_threads)]
        upload_threads = [threading.Thread(target=uploader_worker, daemon=True) for _ in range(num_upload_threads)]

        # Iniciar hilos
        for t in upload_threads:
            t.start()
        for t in download_threads:
            t.start()

        # ----------------------------------------------------------------------------------------------
        # 2) Esperamos a que terminen los hilos de descargas para mandar Nones a la cola de subida,
        #    luego esperamos que la cola termine y finalmente esperamos que terminen los hilos de subida
        # ----------------------------------------------------------------------------------------------

        # Esperar a que terminen los hilos de descargas
        for t in download_threads:
            t.join()

        # Enviamos tantos None como hilos de subida para avisar que finalicen
        for _ in range(num_upload_threads):
            upload_queue.put(None)

        # Esperamos a que la cola termine de procesarse
        upload_queue.join()

        # Esperar a que terminen los hilos de subida
        for t in upload_threads:
            t.join()

        # En este punto todas las descargas y subidas están listas y la cola está vacía.

        # Finalmente, borrar carpetas vacías que queden en temp_folder
        Utils.remove_empty_dirs(temp_folder)

        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - start_time).seconds))

        # ----------------------------------------------------------------------------
        # 4) Mostrar o retornar contadores
        # ----------------------------------------------------------------------------
        LOGGER.info(f"")
        LOGGER.info(f"INFO    : 🚀 All assets downloaded and uploaded successfully!")
        LOGGER.info(f"")
        LOGGER.info(f"INFO    : ----- SINCRONIZACIÓN FINALIZADA -----")
        LOGGER.info(f"INFO    : {source_client_name} --> {target_client_name}")
        LOGGER.info(f"INFO    : Downloaded Albums           : {SHARED_DATA.counters['total_downloaded_albums']}")
        LOGGER.info(f"INFO    : Uploaded Albums             : {SHARED_DATA.counters['total_uploaded_albums']}")
        LOGGER.info(
            f"INFO    : Downloaded Assets           : {SHARED_DATA.counters['total_downloaded_assets']} (Fotos: {SHARED_DATA.counters['total_downloaded_photos']}, Videos: {SHARED_DATA.counters['total_downloaded_videos']})")
        LOGGER.info(
            f"INFO    : Uploaded Assets             : {SHARED_DATA.counters['total_uploaded_assets']} (Fotos: {SHARED_DATA.counters['total_uploaded_photos']}, Videos: {SHARED_DATA.counters['total_uploaded_videos']})")
        LOGGER.info(f"INFO    : Upload Duplicates (skipped) : {SHARED_DATA.counters['total_upload_duplicates_assets']}")
        LOGGER.info(f"INFO    : Download Failed Assets      : {SHARED_DATA.counters['total_download_failed_assets']}")
        LOGGER.info(f"INFO    : Upload Failed Assets        : {SHARED_DATA.counters['total_upload_failed_assets']}")
        LOGGER.info(f"")
        LOGGER.info(f"INFO    : Migration Job completed in  : {formatted_duration}")
        LOGGER.info(f"")
        LOGGER.info(f"")
        return SHARED_DATA.counters


###########################################
# secuencial_automated_migration Function #
###########################################
def secuencial_automated_migration(source_client, target_client, temp_folder, SHARED_DATA, log_level=logging.INFO):
    """
    Sincroniza fotos y vídeos entre un 'source_client' y un 'destination_client',
    descargando álbumes y assets desde la fuente, y luego subiéndolos a destino,
    de forma secuencial, primero descargas y luego subidas (requiere suficiente espacio en disco).

    Parámetros:
    -----------
    source_client: objeto con los métodos:
        - get_albums_including_shared_with_user() -> [ { 'id': ..., 'name': ... }, ... ]
        - get_album_assets(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_no_albums_assets() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - download_asset(asset_id, download_path) -> str (ruta local del archivo descargado)

    target_client: objeto con los métodos:
        - create_album(album_name) -> album_id
        - album_exists(album_name) -> (bool, album_id_o_None)
        - upload_asset(asset_file_path, asset_datetime) -> asset_id
        - add_asset_to_album(album_id, asset_id) -> None

    temp_folder: str
        Carpeta temporal donde se descargarán los assets antes de subirse.
    """
    
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # =========================
        # FIRST PROCESS THE SOURCE:
        # =========================
        LOGGER.info("")
        LOGGER.info(f'============================================================================')
        LOGGER.info(f'INFO    : STEP 1 - DOWNLOAD/PROCESS ASSETS FROM: {SOURCE}')
        LOGGER.info(f'============================================================================')
        LOGGER.info("")
        LOGGER.info(f'INFO    : Downloading/Processing Assets to: {SOURCE}...')

        source_client.download_ALL(output_folder=temp_folder, log_level=log_level)

        # =========================
        # SECOND PROCESS THE TARGET:
        # =========================
        LOGGER.info("")
        LOGGER.info(f'============================================================================')
        LOGGER.info(f'INFO    : STEP 2 - UPLOAD/PROCESS ASSETS TO: {TARGET}')
        LOGGER.info(f'============================================================================')
        LOGGER.info("")
        LOGGER.info(f'INFO    : Uploading/Processing Assets to: {TARGET}...')

        target_client.upload_ALL(input_folder=temp_folder, remove_duplicates=True, log_level=log_level)


###########################
# start_dashboard Function #
###########################
def start_dashboard(migration_finished, SHARED_DATA, log_level=logging.INFO):
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


    # Guardar referencias originales
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Redirigir stdout y stderr al LOGGER después de que esté inicializado
    # sys.stdout = LoggerStream(LOGGER, logging.INFO)  # Redirige print() a LOGGER.info()
    # sys.stderr = LoggerStream(LOGGER, logging.ERROR)  # Redirige errores a LOGGER.error()

    # # Redirigir a /dev/null
    # sys.stdout = open(os.devnull, 'w')
    # sys.stderr = open(os.devnull, 'w')

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

    # Split layout: header_panel (8 lines), title_panel (3 lines), content_panel (11 lines), logs fill remainder
    layout.split_column(
        Layout(name="empty_line_1", size=1),  # Línea vacía
        Layout(name="header_panel", size=8),
        Layout(name="title_panel", size=3),
        Layout(name="content_panel", size=11),
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
        Layout(name="downloads_panel", ratio=4),
        Layout(name="uploads_panel", ratio=4),
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
    title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] ➜ [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automated Migration - {SCRIPT_NAME_VERSION}"

    layout["title_panel"].update(Panel(f"📂 {title}", border_style="bright_blue", expand=True))

    def update_title_panel():
        title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] ➜ [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automated Migration - {SCRIPT_NAME_VERSION}"
        layout["title_panel"].update(Panel(f"📂 {title}", border_style="bright_blue", expand=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 2) Info Panel
    # ─────────────────────────────────────────────────────────────────────────
    # Historial de tamaño de la cola (se ajustará dinámicamente al ancho del panel)
    queue_history = collections.deque(maxlen=10)  # Se ajustará según el ancho del panel

    def build_info_panel(clean_queue_history=False):
        """Construye el panel de información con historial de la cola."""
        # 🔹 Calcular el ancho real de "info_panel"
        total_ratio = 3 + 4 + 4  # Suma de los ratios en split_row()
        info_panel_ratio = 3  # Ratio de "info_panel"

        # Estimación del ancho de info_panel antes de que Rich lo calcule
        info_panel_width = (terminal_width * info_panel_ratio) // total_ratio

        # 🔹 Unicode para representar la barra de progreso vertical (10 niveles)
        BARS = "  ▁▂▃▄▅▆▇█"     # Se agregan 10 barras
        BARS = "▁▂▄▆█"          # # Se agregan 5 barras

        # 🔹 Inicializar el historial de la cola dentro de la función
        if not hasattr(build_info_panel, "queue_history"):
            build_info_panel.queue_history = collections.deque(maxlen=info_panel_width-31)
        queue_history = build_info_panel.queue_history

        # 🔹 Obtener el tamaño actual de la cola
        current_queue_size = SHARED_DATA.info.get('assets_in_queue', 0)

        # 🔹 Actualizar historial de la cola
        queue_history.append(current_queue_size)

        # 🔹 Definir los rangos de normalización (10 bloques de tamaño 10 cada uno)
        num_blocks = len(BARS)
        block_size = 100 / num_blocks  # Cada bloque cubre 10 unidades

        # 🔹 Asignar la barra correspondiente a cada valor de la cola
        progress_bars = [BARS[min(int(val // block_size), num_blocks - 1)] for val in queue_history]

        # 🔹 Unimos todas las barras
        queue_display = "".join(progress_bars)

        if clean_queue_history:
            queue_display = ""

        # 🔹 Datos a mostrar
        info_data = [
            ("🎯 Total Assets", SHARED_DATA.info.get('total_assets', 0)),
            ("📷 Total Photos", SHARED_DATA.info.get('total_photos', 0)),
            ("🎬 Total Videos", SHARED_DATA.info.get('total_videos', 0)),
            ("📂 Total Albums", SHARED_DATA.info.get('total_albums', 0)),
            ("📜 Total Metadata", SHARED_DATA.info.get('total_metadata', 0)),
            ("🔗 Total Sidecar", SHARED_DATA.info.get('total_sidecar', 0)),
            ("🔍 Unsupported Files", SHARED_DATA.info.get('total_unsupported', 0)),
            ("📊 Assets in Queue", f"{queue_display} {current_queue_size}"),
            ("🕒 Elapsed Time", SHARED_DATA.info.get('elapsed_time', 0)),
        ]

        # 🔹 Crear la tabla
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=22, no_wrap=True)
        table.add_column(justify="right", ratio=1)
        for label, value in info_data:
            table.add_row(f"[bright_magenta]{label:<19}: [/bright_magenta]", f"[bright_magenta]{value}[/bright_magenta]")

        # 🔹 Devolver el panel
        return Panel(table, title="📊 Info Panel", border_style="bright_magenta", expand=True, padding=(0, 1))


    # ─────────────────────────────────────────────────────────────────────────
    # 3) Progress Bars for downloads / uploads
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

    # DOWNLOADS (Cyan)
    download_bars = { # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
        "🎯 Downloaded Assets": (create_progress_bar("cyan"), 'total_downloaded_assets', "total_assets"),
        "📷 Downloaded Photos": (create_progress_bar("cyan"), 'total_downloaded_photos', "total_photos"),
        "🎬 Downloaded Videos": (create_progress_bar("cyan"), 'total_downloaded_videos', "total_videos"),
        "📂 Downloaded Albums": (create_progress_bar("cyan"), 'total_downloaded_albums', "total_albums"),
    }
    failed_downloads = {
        "🚩 Assets Failed": 'total_download_failed_assets',
        "🚩 Photos Failed": 'total_download_failed_photos',
        "🚩 Videos Failed": 'total_download_failed_videos',
        "🚩 Albums Failed": 'total_download_failed_albums',
    }
    download_tasks = {}
    for label, (bar, completed_label, total_label) in download_bars.items():
        # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
        download_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))

    # UPLOADS (Green)
    upload_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
        "🎯 Uploaded Assets": (create_progress_bar("green"), 'total_uploaded_assets', "total_assets"),
        "📷 Uploaded Photos": (create_progress_bar("green"), 'total_uploaded_photos', "total_photos"),
        "🎬 Uploaded Videos": (create_progress_bar("green"), 'total_uploaded_videos', "total_videos"),
        "📂 Uploaded Albums": (create_progress_bar("green"), 'total_uploaded_albums', "total_albums"),
    }
    failed_uploads = {
        "🧩 Duplicates": 'total_upload_duplicates_assets',
        "🚩 Assets Failed": 'total_upload_failed_assets',
        "🚩 Photos Failed": 'total_upload_failed_photos',
        "🚩 Videos Failed": 'total_upload_failed_videos',
        "🚩 Albums Failed": 'total_upload_failed_albums',
    }
    upload_tasks = {}
    for label, (bar, completed_label, total_label) in upload_bars.items():
        # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
        upload_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # 4) Build the Download/Upload Panels
    # ─────────────────────────────────────────────────────────────────────────
    def build_download_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=22)
        table.add_column(justify="right")
        for label, (bar, completed_labeld, total_label) in download_bars.items():
            table.add_row(f"[cyan]{label:<19}:[/cyan]", bar)
            bar.update(download_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
        for label, counter_label in failed_downloads.items():
            value = SHARED_DATA.counters[counter_label]
            table.add_row(f"[cyan]{label:<19}:[/cyan]", f"[cyan]{value}[/cyan]")
        return Panel(table, title=f'📥 {SHARED_DATA.info.get("source_client_name", "Source Client")} Downloads', border_style="cyan", expand=True)

    def build_upload_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=20)
        table.add_column(justify="right")
        for label, (bar, completed_labeld, total_label) in upload_bars.items():
            table.add_row(f"[green]{label:<17}:[/green]", bar)
            bar.update(upload_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
        for label, counter_label in failed_uploads.items():
            value = SHARED_DATA.counters[counter_label]
            table.add_row(f"[green]{label:<17}:[/green]", f"[green]{value}[/green]")
        return Panel(table, title=f'📤 {SHARED_DATA.info.get("target_client_name", "Source Client")} Uploads', border_style="green", expand=True)


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
        title_logs_panel = f"📜 Logs Panel (Only last {logs_panel_height} rows showed. Complete log file at: '{log_file}')"
        try:
            while True:
                # 1) Vaciamos la cola de logs, construyendo el historial completo
                try:
                    line = SHARED_DATA.logs_queue.get_nowait()  # lee un mensaje de la cola
                except queue.Empty:
                    break

                # Opcional: aplica color según la palabra “download”/”upload”
                line_lower = line.lower()
                if "warning :" in line_lower:
                    line_colored = f"[yellow]{line}[/yellow]"
                elif "error   :" in line_lower:
                    line_colored = f"[red]{line}[/red]"
                elif "debug   :" in line_lower:
                    line_colored = f"[#EEEEEE]{line}[/#EEEEEE]"
                elif "download" in line_lower:
                    line_colored = f"[cyan]{line}[/cyan]"
                elif any(word in line_lower for word in ("upload", "created", "duplicated")):
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
            layout["downloads_panel"].update(build_download_panel())
            layout["uploads_panel"].update(build_upload_panel())
            layout["logs_panel"].update(build_log_panel())
            # layout["logs_panel"].update(log_panel)  # inicializamos el panel solo una vez aquí

            # Continue the loop until migration_finished.is_set()
            while not migration_finished.is_set():
                SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=(datetime.now() - step_start_time).seconds))
                layout["info_panel"].update(build_info_panel())
                layout["downloads_panel"].update(build_download_panel())
                layout["uploads_panel"].update(build_upload_panel())
                layout["logs_panel"].update(build_log_panel())
                time.sleep(0.5)  # Evita un bucle demasiado agresivo

            # Pequeña pausa adicional para asegurar el dibujado final
            time.sleep(1)

            # Al terminar, asegurarse que todos los paneles finales se muestren
            layout["info_panel"].update(build_info_panel(clean_queue_history=True))     # Limpiamos el histórico de la cola
            layout["downloads_panel"].update(build_download_panel())
            layout["uploads_panel"].update(build_upload_panel())
            layout["logs_panel"].update(build_log_panel())

        finally:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

######################
# CALL FROM __MAIN__ #
######################
if __name__ == "__main__":
    from Utils import change_workingdir

    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    change_workingdir()

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

    mode_AUTOMATED_MIGRATION(source=source, target=target, show_dashboard=True, parallel=True)
