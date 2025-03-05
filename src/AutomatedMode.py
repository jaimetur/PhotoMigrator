from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION
import os, sys
from datetime import datetime, timedelta
import Utils
import logging
from CustomLogger import set_log_level
from Duplicates import find_duplicates, process_duplicates_actions
from ServiceGooglePhotos import google_takeout_processor
from ServiceSynologyPhotos import login_synology, logout_synology, synology_upload_albums, synology_upload_ALL, synology_download_albums, synology_download_ALL, synology_remove_empty_albums, synology_remove_duplicates_albums, synology_remove_all_assets, synology_remove_all_albums
from ServiceImmichPhotos import login_immich, logout_immich, immich_upload_albums, immich_upload_ALL, immich_download_albums, immich_download_ALL, immich_remove_empty_albums, immich_remove_duplicates_albums, immich_remove_all_assets, immich_remove_all_albums, immich_remove_orphan_assets, remove_duplicates_assets

####################################
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_DASHBOARD_AUTOMATED_MIGRATION(log_level=logging.INFO):
    import time, random, threading
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.live import Live
    from rich.text import Text
    from rich.table import Table

    global log_panel

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

    # Logs panel
    log_panel = Panel("", title="📜 Logs", border_style="red", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 1) Header
    # ─────────────────────────────────────────────────────────────────────────
    layout["header"].update(
        Panel("[bold cyan]📂 Synology Photos → Immich Photos Migration[/bold cyan]", expand=True)
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2) Input Analysis (Magenta)
    # ─────────────────────────────────────────────────────────────────────────
    analysis_data = [
        ("📊 Total Assets", 5000),
        ("📷 Total Photos", 4000),
        ("🎥 Total Videos", 800),
        ("📂 Total Albums", 200),
        ("📑 Total Metadata", 4500),
        ("📑 Total Sidecars", 300),
        ("🚫 Unsupported Files", 50),
    ]

    def build_analysis_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=20)
        table.add_column(justify="right")

        for label, value in analysis_data:
            table.add_row(
                f"[bright_magenta]{label:<20}:[/bright_magenta]",
                f"[bright_magenta]{value}[/bright_magenta]"
            )

        return Panel(
            table,
            title="📊 Input Analysis",
            border_style="bright_magenta",
            expand=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3) Progress Bars for downloads / uploads
    #    Show "X / total" with a bar, no custom chars
    # ─────────────────────────────────────────────────────────────────────────
    def create_progress_bar(color: str) -> Progress:
        """
        Creates a bar with a longer width and displays 'X / total items' in color.
        """
        return Progress(
            BarColumn(
                bar_width=100,           # longer bar for better visuals
                style=color,
                complete_style="bar.complete",
                finished_style="bar.finished",
                pulse_style="bar.pulse"
                # pulse_style=f"{color} dim"
            ),
            TextColumn(f"[{color}]{{task.completed}}/{{task.total}}[/{color}]"),
            console=console,
            expand=True
        )

    # DOWNLOADS (Cyan)
    download_bars = {
        "📊 Downloaded Assets": create_progress_bar("cyan"),
        "📷 Downloaded Photos": create_progress_bar("cyan"),
        "🎥 Downloaded Videos": create_progress_bar("cyan"),
        "📂 Downloaded Albums": create_progress_bar("cyan"),
    }
    failed_downloads = {
        "Assets Failed": 0,
        "Photos Failed": 0,
        "Videos Failed": 0,
        "Albums Failed": 0,
    }
    download_tasks = {}
    for label, bar in download_bars.items():
        download_tasks[label] = bar.add_task(label, total=5000)

    # UPLOADS (Green)
    upload_bars = {
        "📊 Uploaded Assets": create_progress_bar("green"),
        "📷 Uploaded Photos": create_progress_bar("green"),
        "🎥 Uploaded Videos": create_progress_bar("green"),
        "📂 Uploaded Albums": create_progress_bar("green"),
    }
    failed_uploads = {
        "Assets Failed": 0,
        "Photos Failed": 0,
        "Videos Failed": 0,
        "Albums Failed": 0,
    }
    upload_tasks = {}
    for label, bar in upload_bars.items():
        upload_tasks[label] = bar.add_task(label, total=5000)

    # ─────────────────────────────────────────────────────────────────────────
    # 4) Logging
    # ─────────────────────────────────────────────────────────────────────────
    def log_message(message: str):
        global log_panel
        old_text = log_panel.renderable or ""
        new_text = f"{old_text}\n{message}"
        log_panel = Panel(new_text, title="📜 Logs", border_style="red", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5) Simulation
    # ─────────────────────────────────────────────────────────────────────────
    def simulate_downloads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            for label, bar in download_bars.items():
                bar.advance(download_tasks[label], random.randint(1, 50))

            failed_downloads["Assets Failed"] += random.randint(0, 5)
            failed_downloads["Photos Failed"] += random.randint(0, 4)
            failed_downloads["Videos Failed"] += random.randint(0, 2)
            failed_downloads["Albums Failed"] += random.randint(0, 1)

            log_message("[cyan]Downloading asset...[/cyan]")

    def simulate_uploads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            for label, bar in upload_bars.items():
                bar.advance(upload_tasks[label], random.randint(1, 50))

            failed_uploads["Assets Failed"] += random.randint(0, 5)
            failed_uploads["Photos Failed"] += random.randint(0, 4)
            failed_uploads["Videos Failed"] += random.randint(0, 2)
            failed_uploads["Albums Failed"] += random.randint(0, 1)

            log_message("[green]Uploading asset...[/green]")

    # ─────────────────────────────────────────────────────────────────────────
    # 6) Build the Download/Upload Panels
    # ─────────────────────────────────────────────────────────────────────────
    def build_download_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=25)
        table.add_column(justify="right")

        for label, bar in download_bars.items():
            table.add_row(f"[cyan]{label:<20}:[/cyan]", bar)

        for label, val in failed_downloads.items():
            table.add_row(f"[cyan]❌ {label:<18}:[/cyan]", f"[cyan]{val}[/cyan]")

        return Panel(table, title="📥 Synology Photos Downloads", border_style="cyan", expand=True)

    def build_upload_panel():
        table = Table.grid(expand=True)
        table.add_column(justify="left", width=23)
        table.add_column(justify="right")

        for label, bar in upload_bars.items():
            table.add_row(f"[green]{label:<18}:[/green]", bar)

        for label, val in failed_uploads.items():
            table.add_row(f"[green]❌ {label:<16}:[/green]", f"[green]{val}[/green]")

        return Panel(table, title="📤 Immich Photos Uploads", border_style="green", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 7) Main Live Loop
    # ─────────────────────────────────────────────────────────────────────────
    with Live(layout, refresh_per_second=10, console=console, vertical_overflow="crop"):
        layout["input_analysis"].update(build_analysis_panel())
        layout["downloads"].update(build_download_panel())
        layout["uploads"].update(build_upload_panel())
        layout["logs"].update(log_panel)

        thread_d = threading.Thread(target=simulate_downloads)
        thread_u = threading.Thread(target=simulate_uploads)
        thread_d.start()
        thread_u.start()

        while thread_d.is_alive() or thread_u.is_alive():
            time.sleep(0.1)
            layout["downloads"].update(build_download_panel())
            layout["uploads"].update(build_upload_panel())
            layout["logs"].update(log_panel)

        thread_d.join()
        thread_u.join()



# Simulated functions
def download_asset(asset_id, download_queue):
    """Simulates downloading an asset and puts it into the upload queue."""
    time.sleep(random.uniform(0.5, 2))  # Simulate network delay
    print(f"✅ Downloaded asset {asset_id}")
    download_queue.put(asset_id)  # Add to upload queue

def upload_asset(asset_id):
    """Simulates uploading an asset."""
    time.sleep(random.uniform(0.5, 2))  # Simulate network delay
    print(f"📤 Uploaded asset {asset_id}")

def download_worker(download_queue, asset_ids):
    """Thread worker that downloads assets and puts them into the queue."""
    for asset_id in asset_ids:
        download_asset(asset_id, download_queue)

    # Signal that all downloads are done
    download_queue.put(None)

def upload_worker(download_queue):
    """Thread worker that uploads assets from the queue."""
    while True:
        asset_id = download_queue.get()
        if asset_id is None:  # Exit signal
            break
        upload_asset(asset_id)

# Main execution
def main():
    asset_ids = range(1, 21)  # Simulated asset list
    download_queue = queue.Queue()

    # Create threads
    download_thread = threading.Thread(target=download_worker, args=(download_queue, asset_ids))
    upload_thread = threading.Thread(target=upload_worker, args=(download_queue,))

    # Start threads
    download_thread.start()
    upload_thread.start()

    # Wait for completion
    download_thread.join()
    upload_thread.join()

    print("🚀 All assets downloaded and uploaded successfully!")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    # main()
    mode_DASHBOARD_AUTOMATED_MIGRATION()

