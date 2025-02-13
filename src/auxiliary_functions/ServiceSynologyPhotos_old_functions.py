# -*- coding: utf-8 -*-

"""
ServiceSynologyPhotos.py
---------------
Python module with example functions to interact with Synology Photos, including followfing functions:
  - Configuration (read config)
  - Authentication (login/logout)
  - Indexing and Reindexing functions
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Deleting empty or duplicate albums
  - Main functions for use in other modules:
     - synology_delete_empty_albums()
     - synology_delete_duplicates_albums()
     - synology_upload_folder()
     - synology_upload_albums()
     - synology_download_albums()
     - synology_download_ALL()
"""

import os, sys
import requests
import urllib3
import json
import subprocess
import fnmatch
import logging
from tqdm import tqdm
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder

# -----------------------------------------------------------------------------
#                          GLOBAL VARIABLES
# -----------------------------------------------------------------------------
global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD, SYNOLOGY_ROOT_PHOTOS_PATH
global SESSION, SID

# Initialize global variables
CONFIG = None
SESSION = None
SID = None
SYNO_TOKEN_HEADER = {}
ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS = ['.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.3fr', '.arw', '.cr2', '.cr3', '.crw', '.dcr', '.dng', '.erf', '.k25', '.kdc', '.mef', '.mos', '.mrw', '.nef', '.orf', '.ptx', '.pef', '.raf', '.raw', '.rw2', '.sr2', '.srf', '.TIFF', '.HEIC', '.3G2', '.3GP', '.ASF', '.AVI', '.DivX', '.FLV', '.M4V', '.MOV', '.MP4', '.MPEG', '.MPG', '.MTS', '.M2TS', '.M2T', '.QT', '.WMV', '.XviD']
ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS = [ext.lower() for ext in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS]
ALLOWED_SYNOLOGY_SIDECAR_EXTENSIONS = None
ALLOWED_SYNOLOGY_EXTENSIONS = ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                            AUXILIARY FUNCTIONS                             #
##############################################################################

# -----------------------------------------------------------------------------
#                          INDEXING FUNCTIONS
# -----------------------------------------------------------------------------
# Function to start reindexing in Synology Photos using API
def start_reindex_synology_photos_with_api(type='basic'):
    """
    Starts reindexing a folder in Synology Photos using the API.

    Args:
        type (str): 'basic' or 'thumbnail'.
    """
    from GlobalVariables import LOGGER  # Local import of the logger
    # login into Synology Photos if the session if not yet started
    login_synology()

    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Index",
        "version": 1,
        "method": "reindex",
        "runner": SYNOLOGY_USERNAME,
        "type": type
    }
    try:
        result = SESSION.get(url, params=params, verify=False).json()
        if result.get("success"):
            if type == 'basic':
                LOGGER.info(f"INFO    : Reindexing started in Synology Photos database for user: '{SYNOLOGY_USERNAME}'.")
                LOGGER.info("INFO    : This process may take several minutes or even hours to finish depending on the number of files to index. Please be patient...")
        else:
            if result.get("error").get("code") == 105:
                LOGGER.error(f"ERROR   : The user '{SYNOLOGY_USERNAME}' does not have sufficient privileges to start reindexing services. Wait for the system to index the folder before adding its content to Synology Photos albums.")
            else:
                LOGGER.error(f"ERROR   : Error starting reindexing: {result.get('error')}")
                start_reindex_synology_photos_with_command(type=type)
        return result

    except Exception as e:
        LOGGER.error(f"ERROR   : Connection ERROR   : {str(e)}")
        return {"success": False, "error": str(e)}


# Function to start reindexing in Synology Photos using a command
def start_reindex_synology_photos_with_command(type='basic'):
    """
    Starts reindexing a folder in Synology Photos using a shell command.

    Args:
        type (str): 'basic' or 'thumbnail'.
    """
    from GlobalVariables import LOGGER  # Local import of the logger
    # login into Synology Photos if the session if not yet started
    login_synology()

    command = [
        'sudo',  # Run with administrator privileges
        'synowebapi',
        '--exec',
        'api=SYNO.Foto.Index',
        'method=reindex',
        'version=1',
        f'runner={SYNOLOGY_USERNAME}',
        f'type={type}'
    ]
    command_str = " ".join(command)
    if Utils.run_from_synology():
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            if type == 'basic':
                LOGGER.info(f"INFO    : Reindexing started in Synology Photos database for user: '{SYNOLOGY_USERNAME}'.")
                LOGGER.info(f"INFO    : This process may take several minutes or even hours to finish depending on the number of files to index. Please be patient...")
                LOGGER.info(f"INFO    : Starting reindex with command: '{command_str}'")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR   : Failed to execute reindexing with command '{command_str}'")
            LOGGER.error(e.stderr)
    else:
        LOGGER.error(f"ERROR   : The command '{command_str}' can only be executed from a Synology NAS terminal.")


# Function to wait for Synology Photos reindexing to complete
def wait_for_reindexing_synology_photos():
    """
    Waits for reindexing to complete by checking the status every 10 seconds.
    Logs the reindexing progress.
    """
    from GlobalVariables import LOGGER  # Local import of the logger
    import time  # Local import of time
    # login into Synology Photos if the session if not yet started
    login_synology()

    start_reindex_synology_photos_with_api(type='basic')

    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Index",
        "version": 1,
        "method": "get"
    }
    time.sleep(5)  # Wait 5 seconds for the first query to allow indexing calculations
    result = SESSION.get(url, params=params, verify=False).json()
    if result.get("success"):
        files_to_index = int(result["data"].get("basic"))
        remaining_files_previous_step = files_to_index

        with S(total=files_to_index, smoothing=0.8, desc="INFO    : Reindexing files", unit=" files") as pbar:
            while True:
                result = SESSION.get(url, params=params, verify=False).json()
                if result.get("success"):
                    remaining_files = int(result["data"].get("basic"))
                    if remaining_files > files_to_index:
                        files_to_index = remaining_files
                        remaining_files_previous_step = files_to_index
                        pbar.total = files_to_index
                    indexed_in_step = remaining_files_previous_step - remaining_files
                    remaining_files_previous_step = remaining_files
                    pbar.update(indexed_in_step)
                    if remaining_files == 0:
                        start_reindex_synology_photos_with_api(type='thumbnail')
                        time.sleep(10)
                        return True
                    else:
                        time.sleep(5)  # Wait 5 seconds before querying again
                else:
                    LOGGER.error("ERROR   : Error getting reindex status.")
                    return False
    else:
        LOGGER.error("ERROR   : Error getting reindex status.")
        return False

# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS) FUNCTIONS
# -----------------------------------------------------------------------------
# TODO: Review this function because I think it does not work. Use the id that returns upload_asset() to associate it to a folder
def add_asset_to_folder(file_path, album_name=None, log_level=logging.INFO):
    """
    Uploads a file (photo or video) to a Synology Photos folder.

    Args:
        file_path (str): Path to the file to upload.
        album_name (str, optional): Name of the album associated with the upload.

    Returns:
        int: Status code indicating success or failure.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)

        stats = os.stat(file_path)
        # Ensure the folder has at least one supported file indexed
        params = {
            "api": "SYNO.Foto.Upload.Item",
            "method": "upload_to_folder",
            "version": "1",
            "duplicate": "ignore",
            "name": os.path.basename(file_path),
            "mtime": stats.st_mtime,
            "folder_id": 10234,  # Replace with the appropriate folder ID
            "file": 454          # Replace with the appropriate file ID if needed
        }

        files = {
            'assetData': open(file_path, 'rb')
        }
        response = SESSION.post(url, data=params, headers=headers, files=files, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING : Cannot upload assets to folder: '{album_name}' due to API call error. Skipped!")
            return -1


def download_assets(folder_id, folder_name, assets_list, show_info_messages=True):
    """
    Copies a list of photos to a specified folder in Synology Photos.

    Args:
        folder_id (str): ID of the target folder.
        folder_name (str): Name of the target folder.
        assets_list (list): List of photo objects to copy.

    Returns:
        int: Number of photos successfully copied.
    """
    from GlobalVariables import LOGGER
    from math import ceil
    # login into Synology Photos if the session if not yet started
    login_synology()
    # Define the url for the request
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
    headers = {}
    if SYNO_TOKEN_HEADER:
        headers.update(SYNO_TOKEN_HEADER)

    # Split the photo list into batches of 100
    batch_size = 100
    total_batches = ceil(len(assets_list) / batch_size)
    try:
        for i in range(total_batches):
            # Get the current batch
            batch = assets_list[i * batch_size:(i + 1) * batch_size]
            items_id = ','.join([str(photo['id']) for photo in batch])
            params = {
                'api': 'SYNO.Foto.BackgroundTask.File',
                'version': '1',
                'method': 'copy',
                'target_folder_id': folder_id,
                "item_id": f"[{items_id}]",
                "folder_id": "[]",  # This can be adjusted based on specific use case
                'action': 'skip'
            }
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            data = response.json()
            if not data['success']:
                LOGGER.error(f"ERROR   : Failed to copy batch {i + 1}/{total_batches} of assets: {data}")
                return 0
            # LOGGER.info(f"INFO    : Batch {i + 1}/{total_batches} of assets successfully downloaded to the folder '{folder_name}' (ID:{folder_id}).")
        extracted_photos = len(assets_list)
        return extracted_photos
    except Exception as e:
        LOGGER.error(f"ERROR   : Exception while copying assets batches: {e}")

##############################################################################
#                           END OF AUX FUNCTIONS                             #
##############################################################################
# Function to download albums from Synology Photos
def synology_download_albums(albums_name='ALL', output_folder='Downloads_Synology', show_info_messages=True):
    """
    Downloads albums from Synology Photos to a specified folder, supporting wildcard patterns.

    Args:
        albums_name (str or list): The name(s) of the album(s) to download. Use 'ALL' to download all albums.
        output_folder (str): The output folder where download the assets.

    Returns:
        tuple: albums_downloaded, assets_downloaded
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()
    # Variables to return
    albums_downloaded = 0
    assets_downloaded = 0

    # Create or obtain the main folder 'Albums_Synology_Photos'
    main_folder_id = create_folder(output_folder)
    if not main_folder_id:
        LOGGER.error(f"ERROR   : Failed to obtain or create the main folder '{output_folder}'.")
        return albums_downloaded, assets_downloaded

    main_subfolder_id = create_folder("Albums", parent_folder_id=main_folder_id)
    if not main_subfolder_id:
        LOGGER.error(f"ERROR   : Failed to obtain or create the folder 'Albums'.")
        return albums_downloaded, assets_downloaded

    download_folder = os.path.join(output_folder, 'Albums')
    # List own and shared albums
    all_albums = get_albums_own_and_shared()
    # Determine the albums to copy
    if isinstance(albums_name, str) and albums_name.strip().upper() == 'ALL':
        albums_to_download = all_albums
        if show_info_messages:
            LOGGER.info(f"INFO    : All albums ({len(albums_to_download)}) from Synology Photos will be downloaded to the folder '{download_folder} within Synology Photos root folder'...")
    else:
        # Ensure album_name is a list if it's not a string
        if isinstance(albums_name, str):
            # Split album names by commas or spaces
            albums_names = [name.strip() for name in albums_name.replace(',', ' ').split() if name.strip()]
        elif isinstance(albums_name, list):
            # Flatten and clean up the list, splitting on commas within each item
            albums_names = []
            for item in albums_name:
                if isinstance(item, str):
                    albums_names.extend([name.strip() for name in item.split(',') if name.strip()])
        else:
            LOGGER.error("ERROR   : The parameter albums_name must be a string or a list of strings.")
            logout_synology()
            return albums_downloaded, assets_downloaded

        albums_to_download = []
        for album in all_albums:
            album_name = album['name']
            for pattern in albums_names:
                # Search for the album by name or pattern (case-insensitive)
                if fnmatch.fnmatch(album_name.strip().lower(), pattern.lower()):
                    albums_to_download.append(album)
                    break

        if not albums_to_download:
            LOGGER.error("ERROR   : No albums found matching the provided patterns.")
            logout_synology()
            return albums_downloaded, assets_downloaded
        if show_info_messages:
            LOGGER.info(f"INFO    : {len(albums_to_download)} albums from Synology Photos will be downloaded to '{download_folder}' within Synology Photos root folder...")

    albums_downloaded = len(albums_to_download)
    # Iterate over each album to copy
    for album in tqdm(albums_to_download, desc="INFO    : Downloading Albums", unit=" albums"):
        album_name = album['name']
        album_id = album['id']
        # LOGGER.info(f"INFO    : Processing album: '{album_name}' (ID: {album_id})")
        # List assets in the album
        photos = get_assets_from_album(album_name, album_id)
        # LOGGER.info(f"INFO    : Number of photos in the album '{album_name}': {len(photos)}")
        if not photos:
            LOGGER.warning(f"WARNING : No photos to download in the album '{album_name}'.")
            continue
        # Create or obtain the destination folder for the album within output_folder/Albums
        target_folder_name = f'{album_name}'
        target_folder_id = create_folder(target_folder_name, parent_folder_id=main_subfolder_id)
        if not target_folder_id:
            LOGGER.warning(f"WARNING : Failed to obtain or create the destination folder for the album '{album_name}'.")
            continue
        # Download the photos to the destination folder
        assets_downloaded += download_assets(target_folder_id, target_folder_name, photos)

    if show_info_messages:
        LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{os.path.join(SYNOLOGY_ROOT_PHOTOS_PATH, download_folder)}'")
    logout_synology()
    return albums_downloaded, assets_downloaded