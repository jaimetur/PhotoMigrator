from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION
import os, sys
from datetime import datetime, timedelta
import Utils
import logging
import threading
from CustomLogger import set_log_level
from Duplicates import find_duplicates, process_duplicates_actions
from ClassGoogleTakeout import ClassGoogleTakeout
from ClassSynologyPhotos import ClassSynologyPhotos
from ClassImmichPhotos import ClassImmichPhotos


####################################
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_DASHBOARD_AUTOMATED_MIGRATION(temp_folder):
    import json
    import queue
    from pathlib import Path

    # Create the Objects for source_client and target_client
    # source_client = ClassSynologyPhotos()
    # target_client = ClassImmichPhotos()
    source_client = ClassImmichPhotos()
    target_client = ClassSynologyPhotos()

    ###################################################################
    # Declare shared variables to pass as reference to both functions #
    ###################################################################

    # Cola que contendrá los mensajes de log en memoria
    SHARED_LOGS_QUEUE = queue.Queue()

    # Contadores globales
    SHARED_COUNTERS = {
        'total_downloaded_assets': 0,
        'total_downloaded_photos': 0,
        'total_downloaded_videos': 0,
        'total_downloaded_albums': 0,
        'total_download_skipped_assets': 0,

        'total_uploaded_assets': 0,
        'total_uploaded_photos': 0,
        'total_uploaded_videos': 0,
        'total_uploaded_albums': 0,
        'total_upload_skipped_assets': 0,
        'total_upload_duplicates_assets': 0,
    }

    # Get source client statistics:
    all_albums = source_client.get_albums_including_shared_with_user()
    all_assets = source_client.get_all_assets()
    all_photos = [asset for asset in all_assets if asset['type'].lower() in ['photo', 'live', 'image']]
    all_videos = [asset for asset in all_assets if asset['type'].lower() in ['video']]

    # Obtiene el directorio de del script actual y calculamos el path del log relativo al directorio de trabajo
    script_dir = Path(__file__).resolve().parent
    log_file = Path(Utils.get_logger_filename(LOGGER))
    log_file_relative = log_file.relative_to(script_dir)

    SHARED_INPUT_INFO = {
        "total_assets": len(all_assets),
        "total_photos": len(all_photos),
        "total_videos": len(all_videos),
        "total_albums": len(all_albums),
        "total_metadata": 0,
        "total_unsopported": 0,
        "log_file": log_file_relative,
    }
    # LOGGER.info(json.dumps(input_info, indent=4))

    # Call the parallel_automated_migration module to do the whole migration process
    # parallel_automated_migration(source_client=source, target_client=target, temp_folder=temp_folder)

    # 1) Lanzamos la migración en un thread
    migration_thread = threading.Thread(
        target=parallel_automated_migration,
        args=(source_client, target_client, temp_folder, SHARED_COUNTERS, SHARED_LOGS_QUEUE),
        kwargs={'log_level': logging.INFO, 'memory_log': True},
        daemon=True
    )
    migration_thread.start()

    # 2) Lanzamos el dashboard en el hilo principal (o viceversa).
    title = f"{source_client.get_client_name()} ➜ {target_client.get_client_name()} - Automated Migration - CloudPhotoMigrator v3.1.0"
    show_dashboard(
        migration_thread=migration_thread,
        SHARED_INPUT_INFO=SHARED_INPUT_INFO,
        SHARED_COUNTERS=SHARED_COUNTERS,
        SHARED_LOGS_QUEUE=SHARED_LOGS_QUEUE,
        title=title,
        log_level=logging.INFO)

    # 3) Cuando show_dashboard termine, esperar la finalización (si hace falta)
    migration_thread.join()


#########################################
# parallel_automated_migration Function #
#########################################
def parallel_automated_migration(source_client, target_client, temp_folder, SHARED_COUNTERS, SHARED_LOGS_QUEUE, log_level=logging.INFO, memory_log=False):
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
    import os
    import shutil
    import threading
    from queue import Queue
    from CustomLogger import CustomInMemoryLogHandler, CustomConsoleFormatter, CustomLogFormatter, clone_logger

    LOGGER_THREADS = clone_logger(LOGGER)
    parent_log_level = LOGGER_THREADS.level
    with set_log_level(LOGGER_THREADS, log_level):  # Change Log Level to log_level for this function
        if memory_log:
            # Crea el handler y configúralo con un formatter
            memory_handler = CustomInMemoryLogHandler(SHARED_LOGS_QUEUE)
            # memory_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            memory_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

            # Agrega el handler al LOGGER
            LOGGER_THREADS.addHandler(memory_handler)

            # Opcional: si NO quieres imprimir por consola, puedes quitar el StreamHandler que tenga el logger por defecto (así solo se registran en la lista).
            # Por ejemplo:
            LOGGER_THREADS.handlers = [memory_handler]
            LOGGER_THREADS.propagate = False

        # Preparar la cola que compartiremos entre descargas y subidas
        upload_queue = Queue()

        # Diccionario para marcar álbumes procesados (ya contados y/o creados en el destino)
        processed_albums = {}

        # ----------------------------------------------------------------------------
        # 1) Función Worker para SUBIR (consumir de la cola)
        # ----------------------------------------------------------------------------
        def upload_worker(log_level=logging.INFO):
            parent_log_level = LOGGER_THREADS.level

            while True:
                with set_log_level(LOGGER_THREADS, log_level):  # Change Log Level to log_level for this function
                    # Extraemos el siguiente asset de la cola
                    item = upload_queue.get()
                    if item is None:
                        # Si recibimos None, significa que ya no hay más trabajo
                        upload_queue.task_done()
                        break

                    # Obtenemos las propiedades del asset extraido de la cola.
                    asset_id        = item['asset_id']
                    asset_file_path = item['asset_file_path']
                    asset_datetime  = item['asset_datetime']
                    asset_type      = item['asset_type']
                    album_name      = item['album_name']

                    # SUBIR el asset
                    asset_id, isDuplicated = target_client.upload_asset(file_path=asset_file_path, log_level=logging.WARNING)

                    # Actualizamos Contadores de subidas
                    if asset_id:
                        if isDuplicated:
                            SHARED_COUNTERS['total_upload_duplicates_assets'] += 1
                            LOGGER_THREADS.info(f"INFO    : Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped")
                        else:
                            SHARED_COUNTERS['total_uploaded_assets'] += 1
                            if asset_type.lower() == 'video':
                                SHARED_COUNTERS['total_uploaded_videos'] += 1
                            else:
                                SHARED_COUNTERS['total_uploaded_photos'] += 1
                            LOGGER_THREADS.info(f"INFO    : Asset Uploaded: '{os.path.basename(asset_file_path)}'")
                    else:
                        SHARED_COUNTERS['total_upload_skipped_assets'] += 1

                    # Borrar asset de la carpeta temp_folder tras subir
                    if os.path.exists(asset_file_path):
                        try:
                            os.remove(asset_file_path)
                        except:
                            pass
                        finally:
                            # Restore log_level of the parent method
                            # set_log_level(logger_threads, parent_log_level, manual=True)
                            pass

                    # Si existe album_name, manejar álbum en destino
                    if album_name:
                        # Comprobamos si ya procesamos antes este álbum
                        if album_name not in processed_albums:
                            processed_albums[album_name] = None  # Marcamos que se procesó
                            SHARED_COUNTERS['total_uploaded_albums'] += 1
                            LOGGER_THREADS.info(f"INFO    : Album Uploaded: '{album_name}'")

                        # Si el álbum no existe en destino, lo creamos
                        album_exists, album_id_dest = target_client.album_exists(album_name=album_name, log_level=logging.WARNING)
                        if not album_exists:
                            album_id_dest = target_client.create_album(album_name=album_name, log_level=logging.WARNING)

                        # Añadir el asset al álbum
                        target_client.add_assets_to_album(album_id=album_id_dest,asset_ids=asset_id, album_name=album_name, log_level=logging.WARNING)

                        # Verificar si la carpeta local del álbum está vacía y borrarla
                        album_folder_path = os.path.join(temp_folder, album_name)
                        if os.path.exists(album_folder_path):
                            # Si la carpeta está vacía (o solo hay subcarpetas vacías), la borramos
                            try:
                                os.rmdir(album_folder_path)
                            except OSError:
                                # Si no está vacía, ignoramos el error
                                pass
                            finally:
                                # Restore log_level of the parent method
                                # set_log_level(logger_threads, parent_log_level, manual=True)
                                pass

                    upload_queue.task_done()
                    sys.stdout.flush()
                    sys.stderr.flush()

        # ----------------------------------------------------------------------------
        # 2) Iniciar uno o varios hilos para manejar la subida concurrente
        # ----------------------------------------------------------------------------
        num_upload_threads = 2  # Ajustar según tus necesidades
        for _ in range(num_upload_threads):
            t = threading.Thread(target=upload_worker, daemon=True)
            t.start()

        # ----------------------------------------------------------------------------
        # 3) DESCARGAS: Obtener álbumes y sus assets, descargar y poner en cola
        # ----------------------------------------------------------------------------

        # 3.1) Descarga de álbumes
        albums = source_client.get_albums_including_shared_with_user()
        for album in albums:
            album_id = album['id']
            album_name = album['albumName']

            # Descargar todos los assets de este álbum
            album_assets = source_client.get_album_assets(album_id)

            # Incrementamos contador de álbumes descargados
            SHARED_COUNTERS['total_downloaded_albums'] += 1

            for asset in album_assets:
                asset_id = asset['id']
                asset_type = asset['type']
                asset_datetime = asset.get('time')
                asset_filename = asset.get('filename')

                # Crear carpeta del álbum dentro de temp_folder
                album_folder = os.path.join(temp_folder, album_name)
                os.makedirs(album_folder, exist_ok=True)

                try:
                    # Descargar el asset
                    downloaded_assets = source_client.download_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=album_folder, log_level=logging.WARNING)
                except Exception as e:
                    LOGGER_THREADS.error(f"ERROR  : Error Downloading Asset: '{os.path.basename(asset_filename)}'")

                LOGGER_THREADS.info(f"INFO    : Asset Downloaded: '{os.path.basename(asset_filename)}'")
                # LOGGER_THREADS.debug(f"DEBUG   : Asset Downloaded: '{os.path.basename(asset_filename)}'")

                # Actualizamos Contadores de descargas
                if downloaded_assets>0:
                    SHARED_COUNTERS['total_downloaded_assets'] += downloaded_assets
                    if asset_type.lower() == 'video':
                        SHARED_COUNTERS['total_downloaded_videos'] += downloaded_assets
                    else:
                        SHARED_COUNTERS['total_downloaded_photos'] += downloaded_assets
                else:
                    SHARED_COUNTERS['total_download_skipped_assets'] += 1

                # Enviar a la cola con la información necesaria para la subida
                local_file_path = os.path.join(album_folder, asset_filename)
                item_dict = {
                    'asset_id': asset_id,
                    'asset_file_path': local_file_path,
                    'asset_datetime': asset_datetime,
                    'asset_type': asset_type,
                    'album_name': album_name,
                }
                upload_queue.put(item_dict)
                sys.stdout.flush()
                sys.stderr.flush()
            LOGGER_THREADS.info(f"INFO    : Album Downloaded: '{album_name}'")


        # 3.2) Descarga de assets sin álbum
        try:
            assets_no_album = source_client.get_no_albums_assets()
        except Exception as e:
            LOGGER_THREADS.error(f"ERROR  : Error Getting Asset without Albums")

        for asset in assets_no_album:
            asset_id = asset['id']
            asset_type = asset['type']
            asset_datetime = asset.get('time')
            asset_filename = asset.get('filename')

            try:
                # Descargar directamente en temp_folder
                downloaded_assets = source_client.download_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=temp_folder, log_level=logging.WARNING)
            except Exception as e:
                LOGGER_THREADS.error(f"ERROR  : Error Downloading Asset: '{os.path.basename(asset_filename)}'")

            local_file_path = os.path.join(temp_folder, asset_filename)
            LOGGER_THREADS.info(f"INFO    : Asset Downloaded: '{os.path.basename(asset_filename)}'")

            # Actualizamos Contadores de descargas
            if downloaded_assets > 0:
                SHARED_COUNTERS['total_downloaded_assets'] += downloaded_assets
                if asset_type.lower() == 'video':
                    SHARED_COUNTERS['total_downloaded_videos'] += downloaded_assets
                else:
                    SHARED_COUNTERS['total_downloaded_photos'] += downloaded_assets
            else:
                SHARED_COUNTERS['total_download_skipped_assets'] += 1

            # Enviar a la cola sin album_name
            item_dict = {
                'asset_id': asset_id,
                'asset_file_path': local_file_path,
                'asset_datetime': asset_datetime,
                'asset_type': asset_type,
                'album_name': None,
            }
            upload_queue.put(item_dict)
            sys.stdout.flush()
            sys.stderr.flush()

        # ----------------------------------------------------------------------------
        # 4) Finalizar subidas y limpiar carpetas vacías
        # ----------------------------------------------------------------------------

        # Enviamos tantos None como hilos de subida para avisar que finalicen
        for _ in range(num_upload_threads):
            upload_queue.put(None)

        # Esperamos a que la cola termine de procesarse
        upload_queue.join()

        # Finalmente, borrar carpetas vacías que queden en temp_folder
        Utils.remove_empty_dirs(temp_folder)

        # En este punto todas las subidas están listas y la cola está vacía

        # ----------------------------------------------------------------------------
        # 5) Mostrar o retornar contadores
        # ----------------------------------------------------------------------------
        LOGGER_THREADS.info(f"")
        LOGGER_THREADS.info(f"INFO    : 🚀 All assets downloaded and uploaded successfully!")
        LOGGER_THREADS.info(f"")
        LOGGER_THREADS.info(f"INFO    : ----- SINCRONIZACIÓN FINALIZADA -----")
        LOGGER_THREADS.info(f"INFO    : {source_client.get_client_name()} --> {target_client.get_client_name()}")
        LOGGER_THREADS.info(f"INFO    : Downloaded Albums : {SHARED_COUNTERS['total_downloaded_albums']}")
        LOGGER_THREADS.info(f"INFO    : Uploaded Albums   : {SHARED_COUNTERS['total_uploaded_albums']}")
        LOGGER_THREADS.info(f"INFO    : Downloaded Assets : {SHARED_COUNTERS['total_downloaded_assets']} (Fotos: {SHARED_COUNTERS['total_downloaded_photos']}, Videos: {SHARED_COUNTERS['total_downloaded_videos']})")
        LOGGER_THREADS.info(f"INFO    : Uploaded Assets   : {SHARED_COUNTERS['total_uploaded_assets']} (Fotos: {SHARED_COUNTERS['total_uploaded_photos']}, Videos: {SHARED_COUNTERS['total_uploaded_videos']})")

        return SHARED_COUNTERS

###########################
# show_dashboard Function #
###########################
def show_dashboard(migration_thread, SHARED_INPUT_INFO, SHARED_COUNTERS, SHARED_LOGS_QUEUE, title="Automated Migration Process - CloudPhotoMigrator", log_level=logging.INFO):
    import time, random, threading
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.live import Live
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    import queue
    import textwrap

    # Lista (o deque) para mantener todo el historial de logs ya mostrados
    ACCU_LOGS = []

    KEY_MAPING = {
        "📊 Downloaded Assets": "total_downloaded_assets",
        "📷 Downloaded Photos": "total_downloaded_photos",
        "🎥 Downloaded Videos": "total_downloaded_videos",
        "📂 Downloaded Albums": "total_downloaded_albums",
        "📂 Download Skipped Assets": "total_download_skipped_assets",

        "📊 Uploaded Assets": "total_uploaded_assets",
        "📷 Uploaded Photos": "total_uploaded_photos",
        "🎥 Uploaded Videos": "total_uploaded_videos",
        "📂 Uploaded Albums": "total_uploaded_albums",
        "📂 Upload Skipped Assets": "total_upload_skipped_assets",
    }

    total_assets = SHARED_INPUT_INFO.get('total_assets')
    total_photos = SHARED_INPUT_INFO.get('total_photos')
    total_videos = SHARED_INPUT_INFO.get('total_videos')
    total_albums = SHARED_INPUT_INFO.get('total_albums')
    total_metadata = SHARED_INPUT_INFO.get('total_metadata')
    total_unsopported = SHARED_INPUT_INFO.get('total_unsopported')
    log_file = SHARED_INPUT_INFO.get('log_file')

    console = Console()
    # Reduce total height by 1 line so the output doesn't overflow
    total_height = console.size.height - 2

    layout = Layout()
    layout.size = total_height

    # Split layout: header (3 lines), content (10 lines), logs fill remainder
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="content", size=10),
        Layout(name="logs", ratio=1),
    )

    # Split content horizontally into 3 panels
    layout["content"].split_row(
        Layout(name="input_analysis", ratio=3),
        Layout(name="downloads", ratio=4),
        Layout(name="uploads", ratio=4),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1) Header Panel
    # ─────────────────────────────────────────────────────────────────────────
    layout["header"].update(Panel(f"[bold cyan]📂 {title}[/bold cyan]", expand=True))

    # ─────────────────────────────────────────────────────────────────────────
    # 2) Input Info Panel
    # ─────────────────────────────────────────────────────────────────────────
    def build_info_panel():

        info_data = [
            ("📊 Total Assets", total_assets),
            ("📷 Total Photos", total_photos),
            ("🎥 Total Videos", total_videos),
            ("📂 Total Albums", total_albums),
            ("📑 Total Metadata", total_metadata),
            ("🚫 Unsupported Files", total_unsopported),
            ("📑 Log File", log_file),
        ]
        # table = Table.grid(expand=True)
        # table.add_column(justify="left", width=20)
        # table.add_column(justify="right")

        # Creamos la tabla usando Grid
        table = Table.grid(expand=True)  # Grid evita líneas en blanco al inicio
        table.add_column(justify="left", width=23, no_wrap=True)
        table.add_column(justify="right", ratio=1)

        for i, (label, value) in enumerate(info_data):
            if i < len(info_data) - 1:  # Todos menos el último
                table.add_row(
                    f"[bright_magenta]{label:<20}: [/bright_magenta]",  # Asegura alineación
                    f"[bright_magenta]{value}[/bright_magenta]"
                )
            else:  # Último elemento con ajuste de línea
                wrapped_value = "\n".join(textwrap.wrap('.'+os.path.sep+str(value), width=55))
                table.add_row(
                    f"[bright_magenta]{label:<20}: [/bright_magenta]",
                    f"[bright_magenta]{wrapped_value}[/bright_magenta]"  # Se asegura de que el contenido largo haga wrap sin desalinear
                )

        return Panel(
            table,
            title="📊 Input Analysis",
            border_style="bright_magenta",
            expand=True,
            padding=(0, 1)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3) Build the Download/Upload Panels
    # ─────────────────────────────────────────────────────────────────────────
    def build_download_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=25)
        table.add_column(justify="right")

        for label, (bar, total) in download_bars.items():
            table.add_row(f"[cyan]{label:<20}:[/cyan]", bar)

        for label, val in failed_downloads.items():
            table.add_row(f"[cyan]❌ {label:<18}:[/cyan]", f"[cyan]{val}[/cyan]")

        return Panel(table, title="📥 Synology Photos Downloads", border_style="cyan", expand=True)

    def build_upload_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=23)
        table.add_column(justify="right")

        for label, (bar, total) in upload_bars.items():
            table.add_row(f"[green]{label:<18}:[/green]", bar)

        for label, val in failed_uploads.items():
            table.add_row(f"[green]❌ {label:<16}:[/green]", f"[green]{val}[/green]")

        return Panel(table, title="📤 Immich Photos Uploads", border_style="green", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4) Logging Panel from Memmory Handler
    # ─────────────────────────────────────────────────────────────────────────
    def build_log_panel():
        """
        Lee todos los mensajes pendientes en SHARED_LOGS_QUEUE y los añade
        a ACCU_LOGS, que conserva el historial completo.
        Devuelve un Panel con todo el historial (de modo que se pueda hacer
        scroll en la terminal si usas vertical_overflow='visible').
        """

        # 1) Vaciamos la cola de logs, construyendo el historial completo
        while True:
            try:
                line = SHARED_LOGS_QUEUE.get_nowait()  # lee un mensaje de la cola
            except queue.Empty:
                break

            # Opcional: aplica color según la palabra “download”/”upload”
            l_lower = line.lower()
            if "warning" in l_lower:
                line_colored = f"[yellow]{line}[/yellow]"
            elif "error" in l_lower:
                line_colored = f"[red]{line}[/red]"
            elif "debug" in l_lower:
                line_colored = f"[#EEEEEE]{line}[/#EEEEEE]"
            elif "download" in l_lower:
                line_colored = f"[cyan]{line}[/cyan]"
            elif "upload" in l_lower:
                line_colored = f"[green]{line}[/green]"
            else:
                line_colored = f"[bright_white]{line}[/bright_white]"

            # Añadimos la versión coloreada al historial
            ACCU_LOGS.append(line_colored)

        # 2) Unimos todo el historial en un solo string
        if ACCU_LOGS:
            logs_text = "\n".join(ACCU_LOGS)
        else:
            logs_text = "No logs yet..."

        # 3) Construimos el panel
        log_panel = Panel(
            logs_text,
            title="📜 Logs",
            border_style="red",
            expand=True
        )
        return log_panel

    # ─────────────────────────────────────────────────────────────────────────
    # 5) Progress Bars for downloads / uploads
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
    download_bars = {
        "📊 Downloaded Assets": (create_progress_bar("cyan"), total_assets),
        "📷 Downloaded Photos": (create_progress_bar("cyan"), total_photos),
        "🎥 Downloaded Videos": (create_progress_bar("cyan"), total_videos),
        "📂 Downloaded Albums": (create_progress_bar("cyan"), total_albums),
    }
    failed_downloads = {
        "Assets Failed": 0,
        "Photos Failed": 0,
        "Videos Failed": 0,
        "Albums Failed": 0,
    }
    download_tasks = {}
    for label, (bar, total) in download_bars.items():
        download_tasks[label] = bar.add_task(label, total=total)

    # UPLOADS (Green)
    upload_bars = {
        "📊 Uploaded Assets": (create_progress_bar("green"), total_assets),
        "📷 Uploaded Photos": (create_progress_bar("green"), total_photos),
        "🎥 Uploaded Videos": (create_progress_bar("green"), total_videos),
        "📂 Uploaded Albums": (create_progress_bar("green"), total_albums),
    }
    failed_uploads = {
        "Assets Failed": 0,
        "Photos Failed": 0,
        "Videos Failed": 0,
        "Albums Failed": 0,
    }
    upload_tasks = {}
    for label, (bar, total) in upload_bars.items():
        upload_tasks[label] = bar.add_task(label, total=total)


    # ─────────────────────────────────────────────────────────────────────────
    # 6) Update Downloads/Uploads Panels
    # ─────────────────────────────────────────────────────────────────────────
    def update_downloads():
        # for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            for label, (bar, total) in download_bars.items():
                current_value = SHARED_COUNTERS[KEY_MAPING[label]]
                bar.update(download_tasks[label], completed=current_value)
                # bar.advance(download_tasks[label], random.randint(1, 50))

            failed_downloads["Assets Failed"] += random.randint(0, 5)
            failed_downloads["Photos Failed"] += random.randint(0, 4)
            failed_downloads["Videos Failed"] += random.randint(0, 2)
            failed_downloads["Albums Failed"] += random.randint(0, 1)

            # log_message("[cyan]Downloading asset...[/cyan]")

    def update_uploads():
        # for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            for label, (bar, total) in upload_bars.items():
                current_value = SHARED_COUNTERS[KEY_MAPING[label]]
                bar.update(upload_tasks[label], completed=current_value)
                # bar.advance(upload_tasks[label], random.randint(1, 50))

            failed_uploads["Assets Failed"] += random.randint(0, 5)
            failed_uploads["Photos Failed"] += random.randint(0, 4)
            failed_uploads["Videos Failed"] += random.randint(0, 2)
            failed_uploads["Albums Failed"] += random.randint(0, 1)

            # log_message("[green]Uploading asset...[/green]")

    # ─────────────────────────────────────────────────────────────────────────
    # 7) Optional: Print Log Message in Logging Panel
    # ─────────────────────────────────────────────────────────────────────────
    def log_message(message: str):
        old_text = log_panel.renderable or ""
        new_text = f"{old_text}\n{message}"
        log_panel = Panel(new_text, title="📜 Logs", border_style="red", expand=True)


    # ─────────────────────────────────────────────────────────────────────────
    # 8) Main Live Loop
    # ─────────────────────────────────────────────────────────────────────────
    with Live(layout, refresh_per_second=10, console=console, vertical_overflow="visible"):
        layout["input_analysis"].update(build_info_panel())
        layout["downloads"].update(build_download_panel())
        layout["uploads"].update(build_upload_panel())
        layout["logs"].update(build_log_panel())
        # layout["logs"].update(log_panel)

        # while thread_downloads.is_alive() or thread_uploads.is_alive():
        while migration_thread.is_alive():
            time.sleep(0.1) # Evita un bucle demasiado agresivo
            update_downloads()
            update_uploads()
            layout["downloads"].update(build_download_panel())
            layout["uploads"].update(build_upload_panel())
            layout["logs"].update(build_log_panel())

            # if SHARED_LOGS:
            #     message = "\n".join(SHARED_LOGS)
            #     log_message(message)
            #     layout["logs"].update(log_panel)
            #     SHARED_LOGS.clear()



#####################
# CALL FROM __main_ #
#####################
if __name__ == "__main__":
    from Utils import change_workingdir

    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    change_workingdir()

    # Define the Temporary Folder for the downloaded assets.
    temp_folder = './Temp_folder'

    mode_DASHBOARD_AUTOMATED_MIGRATION(temp_folder=temp_folder)
