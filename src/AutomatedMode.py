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
import time
import random
import threading
import queue


####################################
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_AUTOMATED_MIGRATION(log_level=logging.INFO):

    console = Console()

    # Layout structure
    layout = Layout()

    # Header at full width
    layout.split(
        Layout(name="header", size=3),
        Layout(name="content"),
        Layout(name="logs", size=12)
    )

    # Splitting content into three columns with enough space
    layout["content"].split_row(
        Layout(name="input_analysis", ratio=2),
        Layout(name="downloads", ratio=3),
        Layout(name="uploads", ratio=3)
    )

    # Header Panel
    layout["header"].update(Panel("[bold cyan]📂 Synology Photos → Immich Photos Migration[/bold cyan]", expand=True))

    # Input Analysis Panel (Static Information)
    input_analysis_data = """\
    📊 Total Assets:     5000
    🖼️ Total Images:     4000
    🎥 Total Videos:      800
    📂 Total Albums:      200
    📑 Total Metadata:   4500
    🗂️ Total Sidecars:    300
    🚫 Unsupported Files:  50
    """

    # Progress bars for downloads
    download_progress = Progress(
        TextColumn("[cyan]📥 Downloads:[/]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        expand=True
    )

    # Progress bars for uploads
    upload_progress = Progress(
        TextColumn("[green]📤 Uploads:[/]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        expand=True
    )

    # Adding tasks for tracking progress
    task_assets_downloaded = download_progress.add_task("✅ Assets", total=5000)
    task_photos_downloaded = download_progress.add_task("✅ Images", total=4000)
    task_videos_downloaded = download_progress.add_task("✅ Videos", total=800)
    task_albums_downloaded = download_progress.add_task("✅ Albums", total=200)
    task_metadata_downloaded = download_progress.add_task("✅ Metadata", total=4500)
    task_assets_failed = download_progress.add_task("❌ Assets Failed", total=5000)
    task_photos_failed = download_progress.add_task("❌ Images Failed", total=4000)
    task_videos_failed = download_progress.add_task("❌ Videos Failed", total=800)
    task_albums_failed = download_progress.add_task("❌ Albums Failed", total=200)

    task_assets_uploaded = upload_progress.add_task("✅ Assets", total=5000)
    task_photos_uploaded = upload_progress.add_task("✅ Images", total=4000)
    task_videos_uploaded = upload_progress.add_task("✅ Videos", total=800)
    task_albums_uploaded = upload_progress.add_task("✅ Albums", total=200)
    task_metadata_uploaded = upload_progress.add_task("✅ Metadata", total=4500)
    task_assets_failed_upload = upload_progress.add_task("❌ Assets Failed", total=5000)
    task_photos_failed_upload = upload_progress.add_task("❌ Images Failed", total=4000)
    task_videos_failed_upload = upload_progress.add_task("❌ Videos Failed", total=800)
    task_albums_failed_upload = upload_progress.add_task("❌ Albums Failed", total=200)

    # Logs Panel
    log_panel = Panel("", title="📜 Logs", border_style="red")

    # Function to update logs
    def log_message(message):
        global log_panel
        log_text = log_panel.renderable if log_panel.renderable else ""
        log_panel = Panel(f"{log_text}\n{message}", title="📜 Logs", border_style="red")

    # Simulated download function
    def simulate_downloads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            download_progress.advance(task_assets_downloaded, 50)
            download_progress.advance(task_photos_downloaded, 40)
            download_progress.advance(task_videos_downloaded, 8)
            download_progress.advance(task_albums_downloaded, 2)
            download_progress.advance(task_metadata_downloaded, 45)

            # Simulate failed assets
            download_progress.advance(task_assets_failed, 5)
            download_progress.advance(task_photos_failed, 4)
            download_progress.advance(task_videos_failed, 1)
            download_progress.advance(task_albums_failed, 1)

            log_message("[cyan]Downloading asset...[/cyan]")

    # Simulated upload function
    def simulate_uploads():
        for _ in range(100):
            time.sleep(random.uniform(0.05, 0.2))
            upload_progress.advance(task_assets_uploaded, 50)
            upload_progress.advance(task_photos_uploaded, 40)
            upload_progress.advance(task_videos_uploaded, 8)
            upload_progress.advance(task_albums_uploaded, 2)
            upload_progress.advance(task_metadata_uploaded, 45)

            # Simulate failed uploads
            upload_progress.advance(task_assets_failed_upload, 5)
            upload_progress.advance(task_photos_failed_upload, 4)
            upload_progress.advance(task_videos_failed_upload, 1)
            upload_progress.advance(task_albums_failed_upload, 1)

            log_message("[green]Uploading asset...[/green]")

    # Live display in the terminal
    with Live(layout, refresh_per_second=10, console=console):
        layout["input_analysis"].update(Panel(input_analysis_data, title="📊 Input Analysis", border_style="blue", expand=True))
        layout["downloads"].update(Panel(download_progress, title="📥 Synology Photos Downloads", border_style="cyan", expand=True))
        layout["uploads"].update(Panel(upload_progress, title="📤 Immich Photos Uploads", border_style="green", expand=True))
        layout["logs"].update(log_panel)

        # Start downloads and uploads in separate threads
        thread1 = threading.Thread(target=simulate_downloads)
        thread2 = threading.Thread(target=simulate_uploads)

        thread1.start()
        thread2.start()

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
    # main()
    mode_AUTOMATED_MIGRATION()

