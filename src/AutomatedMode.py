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

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.text import Text
from rich.table import Table
import threading
import time
import random


####################################
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_AUTOMATED_MIGRATION(log_level=logging.INFO):
    global log_panel

    console = Console()

    # Prepare main layout
    layout = Layout()

    layout.split(
        Layout(name="header", size=3),
        Layout(name="content", ratio=10),
        Layout(name="logs", size=12)
    )

    layout["content"].split_row(
        Layout(name="input_analysis", ratio=3),
        Layout(name="downloads", ratio=4),
        Layout(name="uploads", ratio=4)
    )

    log_panel = Panel("", title="📜 Logs", border_style="red", expand=True)

    # Header
    layout["header"].update(
        Panel("[bold cyan]📂 Synology Photos → Immich Photos Migration[/bold cyan]", expand=True)
    )

    # Static info for Input Analysis
    input_analysis_data = """\
    📊 Total Assets:     5000
    🖼️ Total Photos:     4000
    🎥 Total Videos:      800
    📂 Total Albums:      200
    📑 Total Metadata:   4500
    🗂️ Total Sidecars:    300
    🚫 Unsupported Files:  50
    """

    # Function to create a progress bar + task
    def create_progress_bar(title):
        bar = Progress(
            TextColumn(f"[cyan]{title}:[/]"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            expand=True
        )
        return bar, title

    # Download progress bars
    download_bars = [
        create_progress_bar("📊 Downloaded Assets"),
        create_progress_bar("🖼️ Downloaded Photos"),
        create_progress_bar("🎥 Downloaded Videos"),
        create_progress_bar("📂 Downloaded Albums"),
        create_progress_bar("📑 Downloaded Metadata"),
    ]

    # Upload progress bars
    upload_bars = [
        create_progress_bar("📊 Uploaded Assets"),
        create_progress_bar("🖼️ Uploaded Photos"),
        create_progress_bar("🎥 Uploaded Videos"),
        create_progress_bar("📂 Uploaded Albums"),
        create_progress_bar("📑 Uploaded Metadata"),
    ]

    # Counters for failed items
    failed_downloads = {
        "❌ Assets Failed": 0,
        "❌ Photos Failed": 0,
        "❌ Videos Failed": 0,
        "❌ Albums Failed": 0,
    }

    failed_uploads = {
        "❌ Assets Failed": 0,
        "❌ Photos Failed": 0,
        "❌ Videos Failed": 0,
        "❌ Albums Failed": 0,
    }

    # Create task references
    download_tasks = {}
    for bar, title in download_bars:
        download_tasks[title] = bar.add_task(title, total=5000)

    upload_tasks = {}
    for bar, title in upload_bars:
        upload_tasks[title] = bar.add_task(title, total=5000)

    # Logging function
    def log_message(message):
        global log_panel
        log_text = log_panel.renderable or ""
        new_text = f"{log_text}\n{message}"
        log_panel = Panel(new_text, title="📜 Logs", border_style="red")

    # Simulated downloads
    def simulate_downloads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            # Advance each download bar
            for bar, title in download_bars:
                bar.advance(download_tasks[title], random.randint(1, 50))

            # Simulate failures
            failed_downloads["❌ Assets Failed"] += random.randint(0, 5)
            failed_downloads["❌ Photos Failed"] += random.randint(0, 4)
            failed_downloads["❌ Videos Failed"] += random.randint(0, 2)
            failed_downloads["❌ Albums Failed"] += random.randint(0, 1)

            log_message("[cyan]Downloading asset...[/cyan]")

    # Simulated uploads
    def simulate_uploads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            # Advance each upload bar
            for bar, title in upload_bars:
                bar.advance(upload_tasks[title], random.randint(1, 50))

            # Simulate failures
            failed_uploads["❌ Assets Failed"] += random.randint(0, 5)
            failed_uploads["❌ Photos Failed"] += random.randint(0, 4)
            failed_uploads["❌ Videos Failed"] += random.randint(0, 2)
            failed_uploads["❌ Albums Failed"] += random.randint(0, 1)

            log_message("[green]Uploading asset...[/green]")

    # Build panels with Table (1 column) to place bars + counters vertically
    def make_download_panel():
        table = Table.grid(expand=True)
        table.add_column()
        # Add all download bars in rows
        for bar, _ in download_bars:
            table.add_row(bar)

        # Add the failed counters
        for title, count in failed_downloads.items():
            table.add_row(Text(f"[cyan]{title}:[/] {count}"))

        return Panel(
            table,
            title="📥 Synology Photos Downloads",
            border_style="cyan",
            expand=True
        )

    def make_upload_panel():
        table = Table.grid(expand=True)
        table.add_column()
        # Add all upload bars in rows
        for bar, _ in upload_bars:
            table.add_row(bar)

        # Add the failed counters
        for title, count in failed_uploads.items():
            table.add_row(Text(f"[green]{title}:[/] {count}"))

        return Panel(
            table,
            title="📤 Immich Photos Uploads",
            border_style="green",
            expand=True
        )

    with Live(layout, refresh_per_second=10, console=console):
        # Input Analysis
        layout["input_analysis"].update(
            Panel(input_analysis_data, title="📊 Input Analysis", border_style="blue", expand=True)
        )

        # Initialize panels
        layout["downloads"].update(make_download_panel())
        layout["uploads"].update(make_upload_panel())
        layout["logs"].update(log_panel)

        # Start threads
        thread1 = threading.Thread(target=simulate_downloads)
        thread2 = threading.Thread(target=simulate_uploads)

        thread1.start()
        thread2.start()

        # Continuously refresh the panels
        while thread1.is_alive() or thread2.is_alive():
            time.sleep(0.1)
            # Re-render updated panels (to show updated counters)
            layout["downloads"].update(make_download_panel())
            layout["uploads"].update(make_upload_panel())
            layout["logs"].update(log_panel)

        thread1.join()
        thread2.join()


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
    mode_AUTOMATED_MIGRATION()

