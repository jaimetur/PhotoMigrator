"""Rich terminal live dashboard for Automatic Migration."""

import logging
import os
import re
import sys
import textwrap
import time
import traceback
from collections import deque
from datetime import datetime, timedelta, timezone
from queue import Empty

from Core.CustomLogger import CustomConsoleFormatter, CustomInMemoryLogHandler, get_logger_filename, set_log_level
from Core.GlobalVariables import ARGS, FOLDERNAME_LOGS, LOGGER, TOOL_DATE, TOOL_NAME_VERSION, TOOL_VERSION
from Utils.GeneralUtils import TQDM_DASHBOARD_META_PREFIX, TQDM_DASHBOARD_PREFIX

BG_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
BG_TQDM_PROGRESS_RE = re.compile(
    r"(?P<pct>\d{1,3})%\|[^|]*\|\s*(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)"
)
BG_CUSTOM_PROGRESS_RE = re.compile(
    r"^(?P<desc>.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+"
    r"(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)\s+\d+(?:\.\d+)?%\s*$"
)
BG_SIMPLE_PROGRESS_RE = re.compile(
    r"^(?P<desc>.+?)\s*:\s*(?P<current>[0-9][0-9,]*)\s*/\s*(?P<total>[0-9][0-9,]*)\b.*$"
)
BG_INDETERMINATE_TQDM_RE = re.compile(
    r"(?P<current>[0-9][0-9,]*)\s+(?P<unit>[A-Za-z][A-Za-z0-9_./-]*)\s+\[[^\]]+\]\s*$"
)
BG_LEVEL_PREFIX_RE = re.compile(
    r"^(?:\[\s*(?:VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\]|(?:VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL))\s*:?\s*",
    flags=re.IGNORECASE,
)


def _parse_int(value, default=0):
    try:
        return int(str(value or "").replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _format_hms_from_seconds(total_seconds):
    safe_seconds = max(0, int(round(float(total_seconds or 0))))
    return str(timedelta(seconds=safe_seconds))


def _compute_dashboard_estimated_time(elapsed_seconds, processed_assets, pending_assets, total_assets=None):
    total_assets = max(0, _parse_int(total_assets, 0))
    processed_assets = max(0, _parse_int(processed_assets, 0))
    pending_assets = max(0, _parse_int(pending_assets, 0))

    if total_assets <= 0 and (processed_assets > 0 or pending_assets > 0):
        total_assets = processed_assets + pending_assets
    if total_assets <= 0:
        return "-"
    if pending_assets <= 0:
        return "00:00:00"
    if processed_assets <= 0:
        return "Estimating..."

    safe_elapsed_seconds = max(0.0, float(elapsed_seconds or 0.0))
    avg_seconds_per_asset = safe_elapsed_seconds / float(processed_assets)
    estimated_remaining_seconds = avg_seconds_per_asset * float(pending_assets)
    return _format_hms_from_seconds(estimated_remaining_seconds)


def _strip_bg_level_prefix(text):
    value = str(text or "")
    previous = None
    while value != previous:
        previous = value
        value = BG_LEVEL_PREFIX_RE.sub("", value, count=1)
    return value


def _normalize_bg_progress_desc(desc):
    text = re.sub(r"\s+", " ", str(desc or "")).strip()
    text = _strip_bg_level_prefix(text)
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    text = _strip_bg_level_prefix(text.strip())
    text = re.sub(
        r"\s+\b(?:in|at|from)(?:\s+\w+){0,2}\s+[\"']?(?:[A-Za-z]:[\\/]|/)[^\"']*[\"']?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*:\s*$", "", text)
    return text.strip() or "Progress"


def _parse_dashboard_progress_line(line):
    raw = str(line or "")
    if not raw:
        return None
    plain = BG_ANSI_ESCAPE_RE.sub("", raw.replace("\r", "")).strip()
    if not plain:
        return None

    if plain.startswith(TQDM_DASHBOARD_META_PREFIX):
        parts = plain[len(TQDM_DASHBOARD_META_PREFIX):].split("\t")
        if len(parts) != 3:
            return None
        return {"desc": parts[0], "current": _parse_int(parts[1], 0), "total": _parse_int(parts[2], 0), "has_total": _parse_int(parts[2], 0) > 0}

    if plain.startswith(TQDM_DASHBOARD_PREFIX):
        plain = plain[len(TQDM_DASHBOARD_PREFIX):].strip()
    elif plain.upper().startswith("TQDM "):
        plain = plain[5:].strip()
    plain = _strip_bg_level_prefix(plain)

    custom_match = BG_CUSTOM_PROGRESS_RE.match(plain)
    simple_match = BG_SIMPLE_PROGRESS_RE.match(plain)
    tqdm_match = BG_TQDM_PROGRESS_RE.search(plain)
    if custom_match or simple_match or tqdm_match:
        match = custom_match or simple_match or tqdm_match
        total = _parse_int(match.group("total"), 0)
        desc = match.group("desc").strip(" :") if match is not tqdm_match else plain[:match.start()].strip(" :-")
        if not desc:
            return None
        return {"desc": desc, "current": _parse_int(match.group("current"), 0), "total": total, "has_total": total > 0}

    indeterminate_match = BG_INDETERMINATE_TQDM_RE.search(plain)
    if indeterminate_match:
        desc = plain[:indeterminate_match.start()].strip(" :-")
        if desc:
            return {"desc": desc, "current": _parse_int(indeterminate_match.group("current"), 0), "total": None, "has_total": False}
    return None


def _select_visible_bg_progress_rows(rows, visible_limit):
    ordered = list(rows or [])
    ordered.sort(
        key=lambda info: (
            bool(info.get("completed")),
            -float(info.get("last_update", 0.0)),
            str(info.get("label", "")).lower(),
        )
    )
    return ordered[:max(1, int(visible_limit or 1))]


def start_dashboard(migration_finished, SHARED_DATA, parallel=True, step_name='', log_level=None):
    with set_log_level(LOGGER, log_level):
        import time
        from datetime import datetime
        from rich.console import Console, Group
        from rich.layout import Layout
        from rich.progress import Progress, BarColumn, TextColumn
        from rich.table import Table
        from rich.panel import Panel
        from rich.rule import Rule
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

            # Background Progress Bar Tittle
            BG_PROGRESS_BAR_TITTLE_WIDTH = 60

            # Calculate terminal_height and terminal_width
            forced_height = int(str(os.environ.get("PHOTOMIGRATOR_TUI_LOG_HEIGHT") or "0").strip() or 0)
            forced_width = int(str(os.environ.get("PHOTOMIGRATOR_TUI_LOG_WIDTH") or "0").strip() or 0)
            terminal_height = forced_height if forced_height > 0 else console.size.height
            terminal_width = forced_width if forced_width > 0 else console.size.width

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

            # Split layout: header_panel (8 lines), title_panel (3 lines), content_panel (16 lines),
            # logs fill remainder, background_progress_panel (7 lines) at the bottom.
            layout.split_column(
                Layout(name="empty_line_1", size=1),  # Línea vacía
                Layout(name="header_panel", size=8),
                Layout(name="title_panel", size=3),
                Layout(name="content_panel", size=16),
                Layout(name="logs_panel", ratio=1),
                Layout(name="background_progress_panel", size=7),
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

                # Recompute with current terminal width on each render (supports resize).
                current_terminal_width = max(40, int(getattr(console.size, "width", terminal_width) or terminal_width))
                info_panel_width = max(30, (current_terminal_width * info_panel_ratio) // total_ratio)

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
                label_col_width = 20
                panel_overhead = 8  # panel borders + paddings + table separators (approx)
                counter_width = 8 if parallel else 7
                BAR_WIDTH = max(3, info_panel_width - label_col_width - panel_overhead - counter_width)
                current_queue_size = int(SHARED_DATA.info.get('assets_in_queue', 0) or 0)
                current_album_assoc_queue_size = int(SHARED_DATA.info.get('album_assoc_queue_size', 0) or 0)
                current_delayed_queue_size = int(SHARED_DATA.info.get('delayed_assets_pending', 0) or 0)
                total_assets = int(SHARED_DATA.info.get('total_assets', 0) or 0)
                processed_assets = min(
                    total_assets,
                    max(0, int(SHARED_DATA.counters.get('total_pulled_assets', 0) or 0))
                )
                pending_assets = max(0, total_assets - processed_assets)
                transfer_started_at_raw = SHARED_DATA.info.get("asset_transfer_start_time")
                transfer_started_at = None
                if isinstance(transfer_started_at_raw, datetime):
                    transfer_started_at = transfer_started_at_raw
                elif transfer_started_at_raw:
                    try:
                        transfer_started_at = datetime.fromisoformat(str(transfer_started_at_raw).replace("Z", "+00:00"))
                    except ValueError:
                        transfer_started_at = None
                elapsed_seconds = max(
                    0.0,
                    (datetime.now(timezone.utc) - transfer_started_at).total_seconds()
                ) if transfer_started_at else 0.0
                SHARED_DATA.info["estimated_time"] = _compute_dashboard_estimated_time(
                    elapsed_seconds=elapsed_seconds,
                    processed_assets=processed_assets,
                    pending_assets=pending_assets,
                    total_assets=total_assets,
                )

                def _format_queue_bar(current_value, max_value=None, show_total=False):
                    safe_max = max(1, int(max_value if max_value is not None else total_assets or 1))
                    safe_value = max(0, int(current_value or 0))
                    filled_blocks = min(int((safe_value / safe_max) * BAR_WIDTH), BAR_WIDTH)
                    empty_blocks = BAR_WIDTH - filled_blocks
                    bar = "█" * filled_blocks + " " * empty_blocks
                    if parallel or show_total:
                        return f"[{bar}] {safe_value:>3}/{safe_max}"
                    return f"[{bar}] {safe_value:>7}"

                queue_bar = _format_queue_bar(current_queue_size)
                delayed_queue_total = SHARED_DATA.counters.get('total_delayed_queue_assets', 0)
                album_assoc_queue_total = SHARED_DATA.counters.get('total_album_assoc_queue_assets', 0)
                delayed_queue_bar = _format_queue_bar(current_delayed_queue_size, delayed_queue_total, show_total=True)
                album_assoc_queue_bar = _format_queue_bar(current_album_assoc_queue_size, album_assoc_queue_total, show_total=True)
                if clean_queue_history:
                    queue_bar = 0
                    album_assoc_queue_bar = 0
                    delayed_queue_bar = 0

                # 🔹 Datos a mostrar
                info_data = [
                    ("🎯 Total Assets", SHARED_DATA.info.get('total_assets', 0)),
                    ("📷 Total Photos", SHARED_DATA.info.get('total_photos', 0)),
                    ("🎬 Total Videos", SHARED_DATA.info.get('total_videos', 0)),
                    ("📂 Total Albums", SHARED_DATA.info.get('total_albums', 0)),
                    ("🔒 Blocked Albums", SHARED_DATA.info.get('total_albums_blocked', 0)),
                    ("🔒 Blocked Assets", SHARED_DATA.counters.get('total_assets_blocked', 0)),
                    ("📜 Total Metadata", SHARED_DATA.info.get('total_metadata', 0)),
                    ("🔗 Total Sidecar", SHARED_DATA.info.get('total_sidecar', 0)),
                    ("❔ Unknown Files", SHARED_DATA.info.get('total_invalid', 0)),
                ]
                queue_data = [
                    ("📊 Assets in Queue", f"{queue_bar}"),
                    ("⏳ Delayed Retries Queue", f"{delayed_queue_bar}"),
                    ("🧾 Album Assoc Queue", f"{album_assoc_queue_bar}"),
                ]

                def _new_info_table():
                    table = Table.grid(expand=True)
                    table.add_column(justify="left", width=27, no_wrap=True)
                    table.add_column(justify="right", ratio=1, no_wrap=True, overflow="crop")
                    return table

                summary_table = _new_info_table()
                for label, value in info_data:
                    summary_table.add_row(f"[bright_magenta]{label:<17}: [/bright_magenta]", f"[bright_magenta]{value}[/bright_magenta]")
                queue_table = _new_info_table()
                for label, value in queue_data:
                    queue_table.add_row(f"[bright_magenta]{label:<17}: [/bright_magenta]", f"[bright_magenta]{value}[/bright_magenta]")

                # 🔹 Devolver el panel
                return Panel(
                    Group(summary_table, Rule(style="bright_magenta dim"), queue_table),
                    title="📊 Info Panel",
                    border_style="bright_magenta",
                    expand=True,
                    padding=(0, 1),
                )


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
            pull_failures = {
                "🎯 Pulled Assets": ("🚩 Failed Assets", 'total_pull_failed_assets'),
                "📷 Pulled Photos": ("🚩 Failed Photos", 'total_pull_failed_photos'),
                "🎬 Pulled Videos": ("🚩 Failed Videos", 'total_pull_failed_videos'),
                "📂 Pulled Albums": ("🚩 Failed Albums", 'total_pull_failed_albums'),
            }
            pull_tasks = {}
            for label, (bar, completed_label, total_label) in pull_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                pull_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))

            # PUSHS (Green)
            push_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
                "🎯 Pushed Assets": (create_progress_bar("green"), 'total_push_queued_assets', "total_assets"),
                "📷 Pushed Photos": (create_progress_bar("green"), 'total_push_queued_photos', "total_photos"),
                "🎬 Pushed Videos": (create_progress_bar("green"), 'total_push_queued_videos', "total_videos"),
                "📂 Pushed Albums": (create_progress_bar("green"), 'total_pushed_albums', "total_albums"),
            }
            push_outcomes = {
                "🎯 Pushed Assets": ("🔢 Total", 'total_pushed_assets', 'total_push_duplicates_assets', 'total_push_failed_assets'),
                "📷 Pushed Photos": ("🔢 Total", 'total_pushed_photos', 'total_push_duplicates_photos', 'total_push_failed_photos'),
                "🎬 Pushed Videos": ("🔢 Total", 'total_pushed_videos', 'total_push_duplicates_videos', 'total_push_failed_videos'),
                "📂 Pushed Albums": ("🔢 Total", 'total_pushed_albums', None, 'total_push_failed_albums'),
            }
            delayed_pushs = {
                "⏳ Delayed Retries": 'total_push_retry_scheduled_assets',
                "⏳ Delayed Recovered": 'total_push_retry_recovered_assets',
            }
            push_tasks = {}
            for label, (bar, completed_label, total_label) in push_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                push_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))


            # ─────────────────────────────────────────────────────────────────────────
            # 4) Build the Pull/Push Panels
            # ─────────────────────────────────────────────────────────────────────────
            def build_pull_panel():
                progress_table = Table.grid(expand=True)
                progress_table.add_column(justify="left", width=24, no_wrap=True)
                progress_table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in pull_bars.items():
                    progress_table.add_row(f"[cyan]{label:<17}:[/cyan]", bar)
                    bar.update(pull_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                    failed_label, failed_counter = pull_failures[label]
                    failed_value = SHARED_DATA.counters.get(failed_counter, 0)
                    progress_table.add_row(f"[cyan]  {failed_label}:[/cyan]", f"[cyan]{failed_value}[/cyan]")
                timing_table = Table.grid(expand=True)
                timing_table.add_column(justify="left", width=24, no_wrap=True)
                timing_table.add_column(justify="right")
                timing_table.add_row(f"[cyan]{'🕒 Elapsed Time':<17}:[/cyan]", f"[cyan]{SHARED_DATA.info.get('elapsed_time', 0)}[/cyan]")
                timing_table.add_row(f"[cyan]{'⏳ Remaining Time':<17}:[/cyan]", f"[cyan]{SHARED_DATA.info.get('estimated_time', '-')}[/cyan]")
                return Panel(
                    Group(progress_table, Text(""), Rule(style="cyan dim"), timing_table),
                    title=f'📥 From: {SHARED_DATA.info.get("source_client_name", "Source Client")}',
                    border_style="cyan",
                    expand=True,
                )


            def build_push_panel():
                progress_table = Table.grid(expand=True)
                progress_table.add_column(justify="left", width=40, no_wrap=True)
                progress_table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in push_bars.items():
                    progress_table.add_row(f"[green]{label:<16}:[/green]", bar)
                    bar.update(push_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                    outcome_label, new_counter, duplicate_counter, failed_counter = push_outcomes[label]
                    new_value = SHARED_DATA.counters.get(new_counter, 0)
                    duplicate_value = SHARED_DATA.counters.get(duplicate_counter, 0) if duplicate_counter else 0
                    failed_value = SHARED_DATA.counters.get(failed_counter, 0)
                    progress_table.add_row(
                        f"[green]  {outcome_label} (New / Duplicates / Failed):[/green]",
                        f"[green]{new_value} / {duplicate_value} / {failed_value}[/green]",
                    )
                delayed_table = Table.grid(expand=True)
                delayed_table.add_column(justify="left", width=40, no_wrap=True)
                delayed_table.add_column(justify="right")
                for label, counter_label in delayed_pushs.items():
                    value = SHARED_DATA.counters[counter_label]
                    delayed_table.add_row(f"[green]{label:<16}:[/green]", f"[green]{value}[/green]")
                return Panel(
                    Group(progress_table, Text(""), Rule(style="green dim"), delayed_table),
                    title=f'📤 To: {SHARED_DATA.info.get("target_client_name", "Source Client")}',
                    border_style="green",
                    expand=True,
                )

            # -------------------------------------------------------------------------
            # 5) Background Progress Panel (capture any tqdm emitted in background)
            # -------------------------------------------------------------------------
            bg_progress_rows = {}
            bg_progress_colors = ["bright_yellow", "bright_blue", "bright_magenta", "bright_green"]
            bg_completed_retention_sec = 5.0
            bg_indeterminate_idle_retention_sec = 2.0
            bg_progress_next_color_idx = 0
            bg_progress_version = 0

            def _create_bg_bar(color, has_total=True):
                counter = "{task.completed}/{task.total}" if has_total else "{task.completed}"
                pulse_style = "bar.pulse" if has_total else f"{color} bold"
                return Progress(
                    BarColumn(
                        bar_width=None,
                        style=f"{color} dim",
                        complete_style=f"{color} bold",
                        finished_style=f"{color} bold",
                        # pulse_style="bar.pulse",
                        pulse_style=pulse_style,
                    ),
                    TextColumn(f"[{color}]{counter:>15}[/{color}]"),
                    console=console,
                    expand=True,
                )

            def _upsert_bg_progress(desc, current, total=None):
                nonlocal bg_progress_next_color_idx, bg_progress_version
                label = _normalize_bg_progress_desc(desc)
                current_value = max(0, int(current))
                has_total = total is not None and int(total) > 0
                total_value = max(1, int(total)) if has_total else None
                key = f"{label.lower()}::{'determinate' if has_total else 'indeterminate'}::{total_value if has_total else 0}"
                if key not in bg_progress_rows:
                    color = bg_progress_colors[bg_progress_next_color_idx % len(bg_progress_colors)]
                    bg_progress_next_color_idx += 1
                    bar = _create_bg_bar(color, has_total=has_total)
                    task_id = bar.add_task(label, completed=0, total=total_value)
                    bg_progress_rows[key] = {
                        "label": label,
                        "color": color,
                        "bar": bar,
                        "task_id": task_id,
                        "last_update": time.time(),
                        "completed": False,
                        "has_total": has_total,
                    }

                info = bg_progress_rows[key]
                if info.get("has_total"):
                    done = max(0, min(current_value, total_value))
                    info["bar"].update(info["task_id"], completed=done, total=total_value)
                    info["completed"] = done >= total_value
                else:
                    info["bar"].update(info["task_id"], completed=current_value, total=None)
                    info["completed"] = False
                info["last_update"] = time.time()
                bg_progress_version += 1
                return True

            def _prune_bg_progress_rows(now=None):
                nonlocal bg_progress_version
                if now is None:
                    now = time.time()
                to_delete = []
                for key, info in bg_progress_rows.items():
                    age = now - float(info.get("last_update", now))
                    if info.get("completed") and age > bg_completed_retention_sec:
                        to_delete.append(key)
                        continue
                    if not info.get("has_total") and age > bg_indeterminate_idle_retention_sec:
                        to_delete.append(key)
                if not to_delete:
                    return False
                for key in to_delete:
                    bg_progress_rows.pop(key, None)
                bg_progress_version += 1
                return True

            def _consume_progress_line(line):
                parsed = _parse_dashboard_progress_line(line)
                if not parsed:
                    return False
                return _upsert_bg_progress(
                    parsed["desc"],
                    parsed["current"],
                    parsed["total"] if parsed.get("has_total") else None,
                )

            def build_background_progress_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=BG_PROGRESS_BAR_TITTLE_WIDTH, no_wrap=True, overflow="ellipsis")
                table.add_column(justify="left", ratio=1, no_wrap=True)

                if bg_progress_rows:
                    panel_height = int(getattr(layout["background_progress_panel"], "size", background_progress_panel_height) or background_progress_panel_height)
                    visible_limit = max(1, panel_height - 2)
                    ordered = _select_visible_bg_progress_rows(bg_progress_rows.values(), visible_limit)
                    for info in ordered:
                        label = escape(str(info.get("label", "Progress")))
                        table.add_row(f"[{info['color']}]{label}[/{info['color']}]", info["bar"])
                else:
                    table.add_row("", "")

                return Panel(table, title="⏳ Background Progress", border_style="bright_cyan", expand=True, padding=(0, 1))

            # ─────────────────────────────────────────────────────────────────────────
            # 6) Logging Panel from Memmory Handler
            # ─────────────────────────────────────────────────────────────────────────
            # Lista (o deque) para mantener todo el historial de logs ya mostrados
            ACCU_LOGS = deque(maxlen=2000)
            logs_version = 0

            def _current_logs_panel_height():
                panel_size = getattr(layout["logs_panel"], "size", None)
                if isinstance(panel_size, int) and panel_size > 0:
                    return max(1, panel_size - 2)
                return max(1, terminal_height - fixed_heights - 2)

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

                    clean_line = BG_ANSI_ESCAPE_RE.sub("", str(line or "").replace("\r", "")).rstrip()
                    if not clean_line:
                        continue
                    safe_line = clean_line

                    line_lower = clean_line.lower()
                    event_line = re.sub(r"^(VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*:\s*", "", clean_line, flags=re.IGNORECASE).strip()
                    event_lower = event_line.lower()
                    if "warning :" in line_lower:
                        line_style = "yellow"
                    elif "error   :" in line_lower:
                        line_style = "red"
                    elif "debug   :" in line_lower:
                        line_style = "#EEEEEE"
                    elif "delayed" in line_lower:
                        line_style = "bright_black"
                    elif event_lower.startswith("asset pulled"):
                        line_style = "cyan"
                    elif event_lower.startswith("asset pushed"):
                        line_style = "green"
                    elif event_lower.startswith("album created"):
                        line_style = "bright_white"
                    elif event_lower.startswith("album pulled"):
                        line_style = "bright_cyan"
                    elif event_lower.startswith("album pushed"):
                        line_style = "bright_green"
                    elif event_lower.startswith("asset duplicated"):
                        line_style = "#9da7ad"
                    elif event_lower.startswith("asset fail") or event_lower.startswith("asset failed"):
                        line_style = "yellow"
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
                logs_panel_height = _current_logs_panel_height()
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
                    "total_metadata", "total_sidecar", "total_invalid",
                    "assets_in_queue", "album_assoc_queue_size", "delayed_assets_pending",
                )
                return (
                    tuple(SHARED_DATA.info.get(k) for k in keys),
                    int(SHARED_DATA.counters.get('total_assets_blocked', 0) or 0),
                )

            def _build_pull_signature():
                completed_keys = [cfg[1] for cfg in pull_bars.values()]
                total_keys = [cfg[2] for cfg in pull_bars.values()]
                failed_keys = [counter for _, counter in pull_failures.values()]
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                    SHARED_DATA.info.get("elapsed_time", 0),
                    SHARED_DATA.info.get("estimated_time", "-"),
                )

            def _build_push_signature():
                completed_keys = [cfg[1] for cfg in push_bars.values()]
                total_keys = [cfg[2] for cfg in push_bars.values()]
                outcome_keys = [counter for outcome in push_outcomes.values() for counter in outcome[1:] if counter]
                failed_keys = outcome_keys + list(delayed_pushs.values())
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                )

            def _sync_terminal_size():
                nonlocal terminal_height, terminal_width
                new_height = max(1, int(getattr(console.size, "height", terminal_height) or terminal_height))
                new_width = max(1, int(getattr(console.size, "width", terminal_width) or terminal_width))
                if new_height == terminal_height and new_width == terminal_width:
                    return False
                terminal_height = new_height
                terminal_width = new_width
                layout.size = terminal_height
                return True

            def _wait_for_ctrl_c_to_close_dashboard():
                """
                Keep the final dashboard visible until the user presses Ctrl+C.
                """
                stdin_is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
                stdout_is_tty = bool(getattr(original_stdout, "isatty", lambda: False)())
                if not (stdin_is_tty and stdout_is_tty):
                    return
                try:
                    if os.name == "nt":
                        import msvcrt
                        # Flush pending keypresses (e.g., buffered Enter) to avoid instant close.
                        while msvcrt.kbhit():
                            msvcrt.getch()
                        while msvcrt.getch() != b"\x03":
                            pass
                    else:
                        import termios
                        import tty
                        fd = sys.stdin.fileno()
                        old_settings = termios.tcgetattr(fd)
                        try:
                            termios.tcflush(fd, termios.TCIFLUSH)
                            tty.setraw(fd)
                            while os.read(fd, 1) != b"\x03":
                                pass
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except KeyboardInterrupt:
                    pass
                except Exception:
                    # Never fail dashboard shutdown due to input handling issues.
                    pass

            def _notify_gui_migration_completed():
                """Notify the GUI while leaving the final Rich dashboard open."""
                if os.environ.get("PHOTOMIGRATOR_GUI_MODE") != "1":
                    return
                completion_file = str(os.environ.get("PHOTOMIGRATOR_DASHBOARD_COMPLETION_FILE") or "").strip()
                if not completion_file:
                    return
                try:
                    with open(completion_file, "w", encoding="utf-8") as status_file:
                        status_file.write("0")
                except OSError:
                    # The wrapper will still report its eventual process exit.
                    pass


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

                        if _sync_terminal_size():
                            layout["info_panel"].update(build_info_panel())
                            layout["pulls_panel"].update(build_pull_panel())
                            layout["pushs_panel"].update(build_push_panel())
                            layout["background_progress_panel"].update(build_background_progress_panel())
                            layout["logs_panel"].update(build_log_panel())
                            last_info_signature = _build_info_signature()
                            last_pull_signature = _build_pull_signature()
                            last_push_signature = _build_push_signature()
                            last_bg_version = bg_progress_version
                            last_logs_version = logs_version
                            dirty = True

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

                    # Report migration completion to the GUI before waiting so its
                    # controls reset while the final dashboard remains visible.
                    _notify_gui_migration_completed()
                    LOGGER.info("Automatic Migration completed. Press Ctrl+C to close the dashboard...")
                    _drain_logs_queue()
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()
                    _wait_for_ctrl_c_to_close_dashboard()

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
        
