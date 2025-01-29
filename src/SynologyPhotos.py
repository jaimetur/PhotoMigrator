# -*- coding: utf-8 -*-

"""
SynologyPhotos.py
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
import subprocess
import Utils
import fnmatch
from tqdm import tqdm

# -----------------------------------------------------------------------------
#                          GLOBAL VARIABLES
# -----------------------------------------------------------------------------
global CONFIG
global NAS_IP
global USERNAME
global PASSWORD
global ROOT_PHOTOS_PATH
global SYNOLOGY_URL
global SESSION
global SID

# Initialize global variables
CONFIG = None
SESSION = None
SID = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                           AUXILIARY FUNNCTIONS                             #
##############################################################################
# -----------------------------------------------------------------------------
#                          CONFIGURATION READING
# -----------------------------------------------------------------------------
def read_synology_config(config_file='Synology.config', show_info=True):
    """
    Reads the Synology configuration file and updates global variables.
    If the configuration file is not found, prompts the user to manually input required data.

    Args:
        config_file (str): The path to the Synology configuration file. Default is 'Synology.config'.
        show_info (bool): Whether to display the loaded configuration information. Default is True.

    Returns:
        dict: The loaded configuration dictionary.
    """
    global CONFIG
    global NAS_IP
    global USERNAME
    global PASSWORD
    global ROOT_PHOTOS_PATH
    global SYNOLOGY_URL
    from LoggerConfig import LOGGER  # Import the logger inside the function

    if CONFIG:
        return CONFIG

    CONFIG = {}
    LOGGER.info(f"INFO: Looking for Synology config file: '{config_file}'")
    try:
        # Try to open the file
        with open(config_file, 'r') as file:
            for line in file:
                line = line.split('#')[0].strip()  # Remove comments and whitespace
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().upper()
                    value = value.strip()
                    # Add only if the key does not already exist
                    if key not in CONFIG:
                        CONFIG[key] = value
    except FileNotFoundError:
        LOGGER.warning(f"WARNING: The file {config_file} was not found. You must introduce required data manually...")

    # Extract specific values
    NAS_IP = CONFIG.get('NAS_IP')
    USERNAME = CONFIG.get('USERNAME')
    PASSWORD = CONFIG.get('PASSWORD')
    ROOT_PHOTOS_PATH = CONFIG.get('ROOT_PHOTOS_PATH')

    # Verify required parameters and prompt on screen if missing
    if not NAS_IP:
        LOGGER.warning(f"WARNING: NAS_IP not found. It will be requested on screen.")
        CONFIG['NAS_IP'] = input("\nEnter NAS_IP: ")
    if not USERNAME:
        LOGGER.warning(f"WARNING: USERNAME not found. It will be requested on screen.")
        CONFIG['USERNAME'] = input("\nEnter USERNAME: ")
    if not PASSWORD:
        LOGGER.warning(f"WARNING: PASSWORD not found. It will be requested on screen.")
        CONFIG['PASSWORD'] = input("\nEnter PASSWORD: ")
    if not ROOT_PHOTOS_PATH:
        LOGGER.warning(f"WARNING: ROOT_PHOTOS_PATH not found. It will be requested on screen.")
        CONFIG['ROOT_PHOTOS_PATH'] = input("\nEnter ROOT_PHOTOS_PATH: ")

    # Update global connection variables
    NAS_IP = CONFIG['NAS_IP']
    USERNAME = CONFIG['USERNAME']
    PASSWORD = CONFIG['PASSWORD']
    ROOT_PHOTOS_PATH = CONFIG['ROOT_PHOTOS_PATH']
    SYNOLOGY_URL = f"http://{NAS_IP}:5000"

    if show_info:
        # Display global connection variables
        masked_password = '*' * len(PASSWORD)
        LOGGER.info(f"INFO: NAS_IP           : {NAS_IP}")
        LOGGER.info(f"INFO: USERNAME         : {USERNAME}")
        LOGGER.info(f"INFO: PASSWORD         : {masked_password}")
        LOGGER.info(f"INFO: ROOT_PHOTOS_PATH : {ROOT_PHOTOS_PATH}")

    return CONFIG

# -----------------------------------------------------------------------------
#                          AUTHENTICATION / LOGOUT
# -----------------------------------------------------------------------------
def login_synology():
    """
    Logs into the NAS and returns the active session with the SID and Synology DSM URL.
    """
    global SESSION
    global SID
    from LoggerConfig import LOGGER

    # If a session is already active, return it instead of creating a new one
    if SESSION and SID:
        return SESSION, SID

    # Read server configuration
    read_synology_config()

    SESSION = requests.Session()
    url = f"{SYNOLOGY_URL}/webapi/auth.cgi"
    params = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": USERNAME,
        "passwd": PASSWORD,
        "format": "sid",
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if data.get("success"):
        SESSION.cookies.set("id", data["data"]["sid"])  # Set the SID as a cookie
        LOGGER.info("INFO: Authentication successful: Session initiated successfully.")
        SID = data["data"]["sid"]
        return SESSION, SID
    else:
        LOGGER.error(f"ERROR: Unable to authenticate with the provided NAS data: {data}")
        sys.exit(-1)

def logout_synology():
    """
    Logs out from the Synology NAS and clears the active session and SID.
    """
    global SESSION
    global SID
    from LoggerConfig import LOGGER

    if SESSION and SID:
        url = f"{SYNOLOGY_URL}/webapi/auth.cgi"
        params = {
            "api": "SYNO.API.Auth",
            "version": "3",
            "method": "logout",
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            LOGGER.info("INFO: Session closed successfully.")
            SESSION = None
            SID = None
        else:
            LOGGER.error("ERROR: Unable to close session in Synology NAS.")

# -----------------------------------------------------------------------------
#                          FOLDERS FUNCTIONS
# -----------------------------------------------------------------------------
def get_photos_root_folder_id():
    """
    Retrieves the folder_id of the root folder in Synology Photos.

    Returns:
        int: The ID of the folder (folder_id).
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Browse.Folder",
        "method": "get",
        "version": "2",
    }
    # Make the request
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        LOGGER.error("ERROR: Cannot obtain Photos Root Folder ID due to an error in the API call.")
        sys.exit(-1)
    # Extract the folder_id
    folder_name = data["data"]["folder"]["name"]
    folder_id = str(data["data"]["folder"]["id"])
    if not folder_id or folder_name != "/":
        LOGGER.error("ERROR: Cannot obtain Photos Root Folder ID.")
        sys.exit(-1)
    return folder_id


def get_folder_id(search_in_folder_id, folder_name):
    """
    Retrieves the folder_id of a folder in Synology Photos given the parent folder ID
    and the name of the folder to search for.

    Args:
        search_in_folder_id (str): ID of the Synology Photos folder where the subfolder is located.
        folder_name (str): Name of the folder to search for in the Synology Photos folder structure.

    Returns:
        int: The ID of the folder (folder_id), or None if not found.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # First, get folder_name for search_in_folder_id
    params = {
        "api": "SYNO.Foto.Browse.Folder",
        "method": "get",
        "version": "2",
        "id": search_in_folder_id,
    }
    # Make the request
    response = SESSION.get(url, params=params, verify=False)
    data = response.json()
    if not data.get("success"):
        LOGGER.error(f"ERROR: Cannot obtain name for folder ID '{search_in_folder_id}' due to an error in the API call.")
        sys.exit(-1)
    search_in_folder_name = data["data"]["folder"]["name"]
    offset = 0
    limit = 5000
    subfolders_dict = []
    folder_id = None
    while True:
        params = {
            "api": "SYNO.Foto.Browse.Folder",
            "method": "list",
            "version": "2",
            "id": search_in_folder_id,
            "offset": offset,
            "limit": limit
        }
        # Make the request
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            LOGGER.error(f"ERROR: Cannot obtain ID for folder '{folder_name}' due to an error in the API call.")
            sys.exit(-1)
        # Build a dictionary with IDs of all subfolders found in the parent folder
        subfolders_dict = {item["name"].replace(search_in_folder_name, '').replace('/', ''): str(item["id"]) for item in data["data"]["list"] if "id" in item}

        # Check if fewer elements than the limit were returned or if the folder was already found
        if len(data["data"]["list"]) < limit or folder_name in subfolders_dict.keys():
            break
        # Increment the offset for the next page
        offset += limit
    # Check if the folder ID was found; if so, return it
    folder_id = subfolders_dict.get(folder_name)
    if folder_id:
        return folder_id
    # If not found, recursively iterate through all subfolders and search
    else:
        for subfolder_id in subfolders_dict.values():
            folder_id = get_folder_id(search_in_folder_id=subfolder_id, folder_name=folder_name)
            if folder_id:
                return folder_id
        # If the folder is still not found after recursion, return None
        return folder_id


# Function to obtain or create a folder
def get_folder_id_or_create_folder(folder_name, parent_folder_id=None):
    """
    Retrieves the folder ID of a given folder name within a parent folder in Synology Photos.
    If the folder does not exist, it will be created.

    Args:
        folder_name (str): The name of the folder to find or create.
        parent_folder_id (str, optional): The ID of the parent folder.
            If not provided, the root folder of Synology Photos is used.

    Returns:
        str: The folder ID if found or successfully created, otherwise None.
    """
    from LoggerConfig import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # Use Synology Photos root folder if no parent folder ID is provided
    if not parent_folder_id:
        photos_root_folder_id = get_photos_root_folder_id()
        parent_folder_id = photos_root_folder_id
        LOGGER.info(f"INFO: Parent Folder ID not provided, using Synology Photos root folder ID: '{photos_root_folder_id}' as parent folder.")

    # Check if the folder already exists
    folder_id = get_folder_id(search_in_folder_id=parent_folder_id, folder_name=folder_name)
    if folder_id:
        LOGGER.warning(f"WARNING: The folder '{folder_name}' already exists.")
        return folder_id

    # If the folder does not exist, create it
    params = {
        'api': 'SYNO.Foto.Browse.Folder',
        'version': '1',
        'method': 'create',
        'target_id': parent_folder_id,
        'name': folder_name
    }
    response = SESSION.get(url, params=params, verify=False)
    data = response.json()
    if data.get("success"):
        LOGGER.info(f"INFO: Folder '{folder_name}' successfully created.")
        return data['data']['folder']['id']
    else:
        LOGGER.error(f"ERROR: Failed to create the folder: '{folder_name}'")
        return None


# -----------------------------------------------------------------------------
#                          ALBUMS FUNCTIONS
# -----------------------------------------------------------------------------
def list_albums():
    """
    Lists all albums in Synology Photos.

    Returns:
        dict: A dictionary with album IDs as keys and album names as values.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    offset = 0
    limit = 5000
    albums_dict = []
    while True:
        params = {
            "api": "SYNO.Foto.Browse.NormalAlbum",
            "method": "list",
            "version": "3",
            "offset": offset,
            "limit": limit
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if data["success"]:
            # Add IDs filtered by supported extensions
            albums_dict = {str(item["id"]): item["name"] for item in data["data"]["list"] if "id" in item}
        else:
            LOGGER.error("ERROR: Failed to list albums: ", data)
            return -1
        # Check if fewer items than the limit were returned
        if len(data["data"]["list"]) < limit:
            break
        # Increment offset for the next page
        offset += limit
    return albums_dict


def list_albums_own_and_shared():
    """
    Lists both own and shared albums in Synology Photos.

    Returns:
        list: A list of albums.
    """
    from LoggerConfig import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    offset = 0
    limit = 5000
    album_list = []
    while True:
        params = {
            'api': 'SYNO.Foto.Browse.Album',
            'version': '4',
            'method': 'list',
            'category': 'normal_share_with_me',
            'sort_by': 'start_time',
            'sort_direction': 'desc',
            'additional': '["sharing_info", "thumbnail"]',
            "offset": offset,
            "limit": limit
        }
        try:
            response = SESSION.get(url, params=params, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error("ERROR: Failed to list own albums:", data)
                return []
            album_list.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        except Exception as e:
            LOGGER.error("ERROR: Exception while listing own albums:", e)
            return []
    return album_list[0]


def list_album_photos(album_name, album_id):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from LoggerConfig import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    offset = 0
    limit = 5000
    album_items = []
    while True:
        params = {
            'api': 'SYNO.Foto.Browse.Item',
            'version': '4',
            'method': 'list',
            'album_id': album_id,
            "offset": offset,
            "limit": limit
        }
        try:
            response = SESSION.get(url, params=params, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR: Failed to list photos in the album '{album_name}'")
                return []
            album_items.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        except Exception as e:
            LOGGER.error(f"ERROR: Exception while listing photos in the album '{album_name}'", e)
            return []
    return album_items[0]


def delete_album(album_id, album_name):
    """
    Deletes an album in Synology Photos.

    Args:
        album_id (str): ID of the album to delete.
        album_name (str): Name of the album to delete.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Browse.Album",
        "method": "delete",
        "version": "3",
        "id": f"[{album_id}]",
        "name": album_name,
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.warning(f"WARNING: Could not delete album {album_id}: ", data)


def get_album_items_count(album_id, album_name):
    """
    Gets the number of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.

    Returns:
        int: Number of items in the album.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Browse.Item",
        "method": "count",
        "version": "4",
        "album_id": album_id,
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.warning(f"WARNING: Cannot count files for album: '{album_name}' due to API call error. Skipped!")
        return -1
    num_files = data["data"]["count"]
    return num_files


def get_album_items_size(album_id, album_name):
    """
    Gets the total size of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.

    Returns:
        int: Total size of the items in the album in bytes.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    offset = 0
    limit = 5000
    album_size = 0
    album_items = []
    while True:
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "list",
            "version": "4",
            "album_id": album_id,
            "offset": offset,
            "limit": limit
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING: Cannot list files for album: '{album_name}' due to API call error. Skipped!")
            return -1
        album_items.append(data["data"]["list"])
        # Check if fewer items than the limit were returned
        if len(data["data"]["list"]) < limit:
            break
        # Increment offset for the next page
        offset += limit
    for set in album_items:
        for item in set:
            album_size += item.get("filesize")
    return album_size


def add_assets_to_album(folder_id, album_name):
    """
    Adds photos from a folder to an album.

    Args:
        folder_id (str): The ID of the folder containing the assets.
        album_name (str): The name of the album to create or add assets to.

    Returns:
        int: The total number of assets added to the album, or -1 in case of an error.
    """
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # Ensure the folder has at least one asset indexed
    params = {
        "api": "SYNO.Foto.Browse.Item",
        "method": "count",
        "version": "4",
        "folder_id": folder_id,
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.warning(f"WARNING: Cannot count files in folder: '{album_name}' due to API call error. Skipped!")
        return -1

    # Check if there are assets to add
    num_files = data["data"]["count"]
    if not num_files > 0:
        LOGGER.warning(f"WARNING: No supported assets found in folder: '{album_name}'. Skipped!")
        return -1

    # Retrieve the IDs of all assets in the folder
    file_ids = []
    offset = 0
    limit = 5000
    while True:
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "list",
            "version": "4",
            "folder_id": folder_id,
            "offset": offset,
            "limit": limit
        }
        # Make the request
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING: Cannot list files in folder: '{album_name}' due to API call error. Skipped!")
            return -1
        file_ids.extend([str(item["id"]) for item in data["data"]["list"] if "id" in item])
        # Check if fewer items than the limit were returned
        if len(data["data"]["list"]) < limit:
            break
        # Increment the offset for the next page
        offset += limit

    # Create the album if the folder contains supported files
    if not len(file_ids) > 0:
        LOGGER.warning(f"WARNING: No supported assets found in folder: '{album_name}'. Skipped!")
        return -1
    params = {
        "api": "SYNO.Foto.Browse.NormalAlbum",
        "method": "create",
        "version": "3",
        "name": f'"{album_name}"',
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.error(f"ERROR: Unable to create album '{album_name}': {data}")
        return -1
    album_id = data["data"]["album"]["id"]
    LOGGER.info(f"INFO: Album '{album_name}' created with ID: {album_id}.")

    # Add the files to the album in batches of 100
    batch_size = 100
    total_added = 0
    for i in range(0, len(file_ids), batch_size):
        batch = file_ids[i:i + batch_size]  # Divide into batches of 100
        items = ",".join(batch)  # Send the photos as a comma-separated list
        params = {
            "api": "SYNO.Foto.Browse.NormalAlbum",
            "method": "add_item",
            "version": "1",
            "id": album_id,
            "item": f"[{items}]",
        }
        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING: Unable to add assets to album '{album_name}' (Batch {i // batch_size + 1}). Skipped!")
            continue
        total_added += len(batch)
    return total_added



# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS) FUNCTIONS
# -----------------------------------------------------------------------------
def upload_assets(file_path, album_name=None):
    """
    Uploads a file (photo or video) to a Synology Photos folder.

    Args:
        file_path (str): Path to the file to upload.
        album_name (str, optional): Name of the album associated with the upload.

    Returns:
        int: Status code indicating success or failure.
    """
    stats = os.stat(file_path)
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

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
    response = SESSION.post(url, data=params, files=files, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.warning(f"WARNING: Cannot upload assets to folder: '{album_name}' due to API call error. Skipped!")
        return -1


def download_assets(folder_id, folder_name, photos_list):
    """
    Copies a list of photos to a specified folder in Synology Photos.

    Args:
        folder_id (str): ID of the target folder.
        folder_name (str): Name of the target folder.
        photos_list (list): List of photo objects to copy.

    Returns:
        int: Number of photos successfully copied.
    """
    from LoggerConfig import LOGGER
    from math import ceil
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # Split the photo list into batches of 100
    batch_size = 100
    total_batches = ceil(len(photos_list) / batch_size)
    try:
        for i in range(total_batches):
            # Get the current batch
            batch = photos_list[i * batch_size:(i + 1) * batch_size]
            items_id = ','.join([str(photo['id']) for photo in batch])
            params_copy = {
                'api': 'SYNO.Foto.BackgroundTask.File',
                'version': '1',
                'method': 'copy',
                'target_folder_id': folder_id,
                "item_id": f"[{items_id}]",
                "folder_id": "[]",  # This can be adjusted based on specific use case
                'action': 'skip'
            }
            response = SESSION.get(url, params=params_copy, verify=False)
            data = response.json()
            if data['success']:
                LOGGER.info(f"INFO: Batch {i + 1}/{total_batches} of assets successfully copied to the folder '{folder_name}' (ID:{folder_id}).")
            else:
                LOGGER.error(f"ERROR: Failed to copy batch {i + 1}/{total_batches} of assets: {data}")
        extracted_photos = len(photos_list)
        return extracted_photos
    except Exception as e:
        LOGGER.error(f"ERROR: Exception while copying assets batches: {e}")


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
    from LoggerConfig import LOGGER  # Local import of the logger

    login_synology()

    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    params = {
        "api": "SYNO.Foto.Index",
        "version": 1,
        "method": "reindex",
        "runner": USERNAME,
        "type": type
    }
    try:
        result = SESSION.get(url, params=params, verify=False).json()
        if result.get("success"):
            if type == 'basic':
                LOGGER.info(f"INFO: Reindexing started in Synology Photos database for user: '{USERNAME}'.")
                LOGGER.info("INFO: This process may take several minutes or even hours to finish depending on the number of files to index. Please be patient...")
        else:
            if result.get("error").get("code") == 105:
                LOGGER.error(f"ERROR: The user '{USERNAME}' does not have sufficient privileges to start reindexing services. Wait for the system to index the folder before adding its content to Synology Photos albums.")
            else:
                LOGGER.error(f"ERROR: Error starting reindexing: {result.get('error')}")
                start_reindex_synology_photos_with_command(type=type)
        return result

    except Exception as e:
        LOGGER.error(f"ERROR: Connection error: {str(e)}")
        return {"success": False, "error": str(e)}


# Function to start reindexing in Synology Photos using a command
def start_reindex_synology_photos_with_command(type='basic'):
    """
    Starts reindexing a folder in Synology Photos using a shell command.

    Args:
        type (str): 'basic' or 'thumbnail'.
    """
    from LoggerConfig import LOGGER  # Local import of the logger

    command = [
        'sudo',  # Run with administrator privileges
        'synowebapi',
        '--exec',
        'api=SYNO.Foto.Index',
        'method=reindex',
        'version=1',
        f'runner={USERNAME}',
        f'type={type}'
    ]
    command_str = " ".join(command)
    if Utils.run_from_synology():
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            if type == 'basic':
                LOGGER.info(f"INFO: Reindexing started in Synology Photos database for user: '{USERNAME}'.")
                LOGGER.info("INFO: This process may take several minutes or even hours to finish depending on the number of files to index. Please be patient...")
                LOGGER.info(f"INFO: Starting reindex with command: '{command_str}'")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"ERROR: Failed to execute reindexing with command '{command_str}'")
            LOGGER.error(e.stderr)
    else:
        LOGGER.error(f"ERROR: The command '{command_str}' can only be executed from a Synology NAS terminal.")


# Function to wait for Synology Photos reindexing to complete
def wait_for_reindexing_synology_photos():
    """
    Waits for reindexing to complete by checking the status every 10 seconds.
    Logs the reindexing progress.
    """
    from LoggerConfig import LOGGER  # Local import of the logger
    import time  # Local import of time
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

        with tqdm(total=files_to_index, smoothing=0.8, desc="INFO: Reindexing files", unit=" files") as pbar:
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
                    LOGGER.error("ERROR: Error getting reindex status.")
                    return False
    else:
        LOGGER.error("ERROR: Error getting reindex status.")
        return False


##############################################################################
#                           END OF AUX FUNCTIONS                             #
##############################################################################


##############################################################################
#           MAIN FUNCTIONS TO CALL FROM OTHER MODULES                        #
##############################################################################
# Function to delete duplicate albums in Synology Photos
def synology_delete_duplicates_albums():
    """
    Deletes all duplicate albums in Synology Photos.

    Returns:
        int: The number of duplicate albums deleted.
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()

    # List albums and identify duplicates
    albums_dict = list_albums()
    albums_deleted = 0
    albums_data = {}
    if albums_dict != -1:
        LOGGER.info("INFO: Looking for duplicate albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc="INFO: Processing Albums", unit=" albums"):
            item_count = get_album_items_count(album_id=album_id, album_name=album_name)
            item_size = get_album_items_size(album_id=album_id, album_name=album_name)
            albums_data.setdefault((item_count, item_size), []).append((album_id, album_name))

        ids_to_delete = {}
        for (item_count, item_size), duplicates in albums_data.items():
            if len(duplicates) > 1:
                min_id = 0
                min_name = ""
                for album_id, album_name in duplicates:
                    if min_id == 0:
                        min_id = album_id
                        min_name = album_name
                    elif int(album_id) < int(min_id):
                        ids_to_delete.setdefault(min_id, []).append(min_name)
                        min_id = album_id
                        min_name = album_name
                    else:
                        ids_to_delete.setdefault(album_id, []).append(album_name)

        for album_id, album_name in ids_to_delete.items():
            LOGGER.info(f"INFO: Deleting duplicate album: '{album_name}' (ID: {album_id})")
            delete_album(album_id=album_id, album_name=album_name)
            albums_deleted += 1

    LOGGER.info("INFO: Deleting duplicate albums process finished!")
    logout_synology()
    return albums_deleted


# Function to delete empty albums in Synology Photos
def synology_delete_empty_albums():
    """
    Deletes all empty albums in Synology Photos.

    Returns:
        int: The number of empty albums deleted.
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()

    # List albums and identify empty ones
    albums_dict = list_albums()
    albums_deleted = 0
    if albums_dict != -1:
        LOGGER.info("INFO: Looking for empty albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc="INFO: Processing Albums", unit=" albums"):
            item_count = get_album_items_count(album_id=album_id, album_name=album_name)
            if item_count == 0:
                LOGGER.info(f"INFO: Deleting empty album: '{album_name}' (ID: {album_id})")
                delete_album(album_id=album_id, album_name=album_name)
                albums_deleted += 1

    LOGGER.info("INFO: Deleting empty albums process finished!")
    logout_synology()
    return albums_deleted


# Function synology_upload_folder()
# TODO: synology_upload_folder()
def synology_upload_folder(folder):
    """
    Upload folder into Synology Photos.

    Args:
        folder (str): Base path on the NAS where the album folders are located.

    Returns:
        tuple: folders_created, folders_skipped, assets_added
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()

    LOGGER.warning("WARNING: This mode is not yet supported. Exiting.")
    sys.exit(-1)

    # # Check if albums_folder is inside ROOT_PHOTOS_PATH
    # folder = Utils.remove_quotes(folder)
    # if folder.endswith(os.path.sep):
    #     folder = folder[:-1]
    # if not os.path.isdir(folder):
    #     LOGGER.error(f"ERROR: Cannot find folder '{folder}'. Exiting...")
    #     sys.exit(-1)
    # LOGGER.info(f"INFO: Folder Path: '{folder}'")
    # folder_full_path = os.path.realpath(folder)
    # ROOT_PHOTOS_PATH_full_path = os.path.realpath(ROOT_PHOTOS_PATH)
    # ROOT_PHOTOS_PATH_full_path = Utils.remove_server_name(ROOT_PHOTOS_PATH_full_path)
    # folder_full_path = Utils.remove_server_name(folder_full_path)
    # if ROOT_PHOTOS_PATH_full_path not in folder_full_path:
    #     LOGGER.error(f"ERROR: Folder: '{folder_full_path}' should be inside ROOT_PHOTOS_PATH: '{ROOT_PHOTOS_PATH_full_path}'")
    #     sys.exit(-1)
    #
    # LOGGER.info("INFO: Reindexing Synology Photos database before adding content...")
    # if wait_for_reindexing_synology_photos():
    #     # Step 1: Get the root folder ID of Synology Photos for the authenticated user
    #     photos_root_folder_id = get_photos_root_folder_id()
    #     LOGGER.info(f"INFO: Synology Photos root folder ID: {photos_root_folder_id}")
    #
    #     # Step 2: Get the folder ID of the directory containing the albums
    #     folder_relative_path = os.path.relpath(folder_full_path, ROOT_PHOTOS_PATH_full_path)
    #     folder_relative_path = "/" + os.path.normpath(folder_relative_path).replace("\\", "/")
    #     folder_id = get_folder_id(search_in_folder_id=photos_root_folder_id, folder_name=os.path.basename(folder))
    #     LOGGER.info(f"INFO: Folder ID: {folder_id}")
    #     if not folder_id:
    #         LOGGER.error(f"ERROR: Cannot obtain ID for folder '{folder_relative_path}/{folder}'. The folder may not have been indexed yet. Try forcing indexing and retry.")
    #         sys.exit(-1)
    #
    #     # Process folders
    #     folders_created = 0
    #     folders_skipped = 0
    #     assets_added = 0
    #
    #     # Filter albums_folder to exclude '@eaDir'
    #     folder_filtered = os.listdir(folder)
    #     folder_filtered[:] = [d for d in folder_filtered if d != '@eaDir']
    #     LOGGER.info(f"INFO: Processing all subfolders in folder '{folder}' and uploading corresponding assets into Synology Photos...")
    #     for folder in tqdm(folder_filtered, desc="INFO: Uploading Folder", unit=" folders"):
    #         # Step 3: For each album folder, get the folder ID in the directory containing the albums
    #         individual_folder_id = get_folder_id(search_in_folder_id=folder_id, folder_name=os.path.basename(folder))
    #         if not individual_folder_id:
    #             LOGGER.error(f"ERROR: Cannot obtain ID for folder '{folder_relative_path}/{folder}'. The folder may not have been indexed yet. Skipping this folder creation.")
    #             folders_skipped += 1
    #             continue
    #
    #         # Step 4: Add all photos or videos in the album folder to the newly created album
    #         # TODO: ESTA PARTE SOBRA PORQUE NO QUIERO AÑADIR LOS ASSETS A NINGÚN ALBÚM, PERO SI NO HACEMOS ESTO, EN REALIDAD NO ESTAMOS HACIENDO NADA, YA QUE LA CARPETA A AÑADIR YA ESTÁ DENTRO DE SYNOLOGY PHOTOS Y POR TANTO ESTÁ SIENDO INDEXADA
    #         # TODO: BUSCAR LA FORMA DE AÑADIR UNA CARPETA DESDE EL EXTERIOR DE SYNOOGY FOTOS.
    #         res = add_assets_to_album(folder_id=individual_folder_id, album_name=folder)
    #         if res == -1:
    #             folders_skipped += 1
    #         else:
    #             folders_created += 1
    #             assets_added += res
    #
    # LOGGER.info("INFO: Folder Uploaded into Synology Photos!")
    # logout_synology()
    # return folders_created, folders_skipped, assets_added

# Function to upload albums to Synology Photos
def synology_upload_albums(albums_folder):
    """
    Upload albums into Synology Photos based on folders in the NAS.

    Args:
        albums_folder (str): Base path on the NAS where the album folders are located.

    Returns:
        tuple: albums_created, albums_skipped, assets_added
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()

    # Check if albums_folder is inside ROOT_PHOTOS_PATH
    albums_folder = Utils.remove_quotes(albums_folder)
    if albums_folder.endswith(os.path.sep):
        albums_folder = albums_folder[:-1]
    if not os.path.isdir(albums_folder):
        LOGGER.error(f"ERROR: Cannot find album folder '{albums_folder}'. Exiting...")
        sys.exit(-1)
    LOGGER.info(f"INFO: Albums Folder Path: '{albums_folder}'")
    albums_folder_full_path = os.path.realpath(albums_folder)
    ROOT_PHOTOS_PATH_full_path = os.path.realpath(ROOT_PHOTOS_PATH)
    ROOT_PHOTOS_PATH_full_path = Utils.remove_server_name(ROOT_PHOTOS_PATH_full_path)
    albums_folder_full_path = Utils.remove_server_name(albums_folder_full_path)
    if ROOT_PHOTOS_PATH_full_path not in albums_folder_full_path:
        LOGGER.error(f"ERROR: Albums folder: '{albums_folder_full_path}' should be inside ROOT_PHOTOS_PATH: '{ROOT_PHOTOS_PATH_full_path}'")
        sys.exit(-1)

    LOGGER.info("INFO: Reindexing Synology Photos database before adding content...")
    if wait_for_reindexing_synology_photos():
        # Step 1: Get the root folder ID of Synology Photos for the authenticated user
        photos_root_folder_id = get_photos_root_folder_id()
        LOGGER.info(f"INFO: Synology Photos root folder ID: {photos_root_folder_id}")

        # Step 2: Get the folder ID of the directory containing the albums
        albums_folder_relative_path = os.path.relpath(albums_folder_full_path, ROOT_PHOTOS_PATH_full_path)
        albums_folder_relative_path = "/" + os.path.normpath(albums_folder_relative_path).replace("\\", "/")
        albums_folder_id = get_folder_id(search_in_folder_id=photos_root_folder_id, folder_name=os.path.basename(albums_folder))
        LOGGER.info(f"INFO: Albums folder ID: {albums_folder_id}")
        if not albums_folder_id:
            LOGGER.error(f"ERROR: Cannot obtain ID for folder '{albums_folder_relative_path}/{albums_folder}'. The folder may not have been indexed yet. Try forcing indexing and retry.")
            sys.exit(-1)

        # Process folders and create albums
        albums_created = 0
        albums_skipped = 0
        assets_added = 0

        # Filter albums_folder to exclude '@eaDir'
        albums_folder_filtered = os.listdir(albums_folder)
        albums_folder_filtered[:] = [d for d in albums_folder_filtered if d != '@eaDir']
        LOGGER.info(f"INFO: Processing all albums in folder '{albums_folder}' and creating corresponding albums into Synology Photos...")
        for album_folder in tqdm(albums_folder_filtered, desc="INFO: Uploading Albums", unit=" albums"):
            # Step 3: For each album folder, get the folder ID in the directory containing the albums
            individual_album_folder_id = get_folder_id(search_in_folder_id=albums_folder_id, folder_name=os.path.basename(album_folder))
            if not individual_album_folder_id:
                LOGGER.error(f"ERROR: Cannot obtain ID for folder '{albums_folder_relative_path}/{album_folder}'. The folder may not have been indexed yet. Skipping this album creation.")
                albums_skipped += 1
                continue

            # Step 4: Add all photos or videos in the album folder to the newly created album
            res = add_assets_to_album(folder_id=individual_album_folder_id, album_name=album_folder)
            if res == -1:
                albums_skipped += 1
            else:
                albums_created += 1
                assets_added += res

    LOGGER.info("INFO: Album creation in Synology Photos completed!")
    logout_synology()
    return albums_created, albums_skipped, assets_added


# Function to download albums from Synology Photos
def synology_download_albums(albums_name='ALL', output_folder='Downloads_Synology'):
    """
    Downloads albums from Synology Photos to a specified folder, supporting wildcard patterns.

    Args:
        albums_name (str or list): The name(s) of the album(s) to download. Use 'ALL' to download all albums.
        output_folder (str): The output folder where download the assets.

    Returns:
        tuple: albums_downloaded, assets_downloaded
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()
    # Variables to return
    albums_downloaded = 0
    assets_downloaded = 0

    # Create or obtain the main folder 'Albums_Synology_Photos'
    main_folder_id = get_folder_id_or_create_folder(output_folder)
    if not main_folder_id:
        LOGGER.error(f"ERROR: Failed to obtain or create the main folder '{output_folder}'.")
        return albums_downloaded, assets_downloaded

    parent_folder_id = get_folder_id_or_create_folder("Albums", parent_folder_id=main_folder_id)
    if not parent_folder_id:
        LOGGER.error(f"ERROR: Failed to obtain or create the folder 'Albums'.")
        return albums_downloaded, assets_downloaded

    download_folder = os.path.join(output_folder, 'Albums')
    # List own and shared albums
    all_albums = list_albums_own_and_shared()
    # Determine the albums to copy
    if isinstance(albums_name, str) and albums_name.strip().upper() == 'ALL':
        albums_to_download = all_albums
        LOGGER.info(f"INFO: All albums ({len(albums_to_download)}) from Synology Photos will be downloaded to the folder '{download_folder} within Synology Photos root folder'...")
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
            LOGGER.error("ERROR: The parameter albums_name must be a string or a list of strings.")
            return albums_downloaded, assets_downloaded

        albums_to_download = []
        for album in all_albums:
            album_name = album['name']
            for pattern in albums_names:
                # Search for the album by name or pattern (case-insensitive)
                # TODO: La siguiente linea no encuentra ningún match.
                if fnmatch.fnmatch(album_name.strip().lower(), pattern.lower()):
                    albums_to_download.append(album)
                    break

        if not albums_to_download:
            LOGGER.error("ERROR: No albums found matching the provided patterns.")
            return albums_downloaded, assets_downloaded
        LOGGER.info(f"INFO: {len(albums_to_download)} albums from Synology Photos will be downloaded to '{download_folder}' within Synology Photos root folder...")

    albums_downloaded = len(albums_to_download)
    # Iterate over each album to copy
    for album in tqdm(albums_to_download, desc="INFO: Downloading Albums", unit=" albums"):
        album_name = album['name']
        album_id = album['id']
        LOGGER.info(f"INFO: Processing album: '{album_name}' (ID: {album_id})")
        # List photos in the album
        photos = list_album_photos(album_name, album_id)
        LOGGER.info(f"INFO: Number of photos in the album '{album_name}': {len(photos)}")
        if not photos:
            LOGGER.warning(f"WARNING: No photos to download in the album '{album_name}'.")
            continue
        # Create or obtain the destination folder for the album within output_folder/Albums
        target_folder_name = f'{album_name}'
        target_folder_id = get_folder_id_or_create_folder(target_folder_name, parent_folder_id=parent_folder_id)
        if not target_folder_id:
            LOGGER.warning(f"WARNING: Failed to obtain or create the destination folder for the album '{album_name}'.")
            continue
        # Copy the photos to the destination folder
        assets_downloaded += download_assets(target_folder_id, target_folder_name, photos)

    LOGGER.info(f"INFO: Album(s) downloaded successfully. You can find them in '{os.path.join(ROOT_PHOTOS_PATH, download_folder)}'")
    return albums_downloaded, assets_downloaded


# Function to download albums from Synology Photos
# TODO: CREAR LA FUNCIÓN synology_download_no_albums()
def synology_download_no_albums(output_folder='Downloads_Synology'):
    """
    Downloads assets no associated to any albums from Synology Photos to a specified folder.

    Args:
        output_folder (str): The output folder where download the assets.

    Returns:
        downloaded_assets
    """

    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()
    output_folder = os.path.join(output_folder,"Albums")
    os.makedirs(output_folder, exist_ok=True)
    # Variables to return
    assets_downloaded = 0
    # Create or obtain the main folder 'Albums_Synology_Photos'
    main_folder = output_folder
    main_folder_id = get_folder_id_or_create_folder(main_folder)
    if not main_folder_id:
        LOGGER.error(f"ERROR: Failed to obtain or create the main folder '{main_folder}'.")
        return  assets_downloaded

    return  assets_downloaded


# Function synology_download_ALL()
def synology_download_ALL(output_folder="Downloads_Synology"):
    # Import logger and log in to the NAS
    from LoggerConfig import LOGGER
    login_synology()

    LOGGER.warning("WARNING: This mode is not yet supported. Exiting.")
    sys.exit(-1)

    synology_download_albums(albums_name='ALL', output_folder=output_folder)
    synology_download_no_albums(output_folder=output_folder)

##############################################################################
#                           END OF MAIN FUNCTIONS                            #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Create timestamp, and initialize LOGGER.
    from datetime import datetime
    from LoggerConfig import log_setup
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename=f"{sys.argv[0]}{TIMESTAMP}"
    log_folder="Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)

    # 0) Read configuration and log in
    read_synology_config()
    login_synology()

    # 1) Example: Delete empty albums
    print("=== EXAMPLE: synology_delete_empty_albums() ===")
    deleted = synology_delete_empty_albums()
    print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # 2) Example: Delete duplicate albums
    print("=== EXAMPLE: synology_delete_duplicates_albums() ===")
    duplicates = synology_delete_duplicates_albums()
    print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Others'
    print("\n=== EXAMPLE: synology_upload_folder() ===")
    input_others_folder = "/volume1/homes/jaimetur_ftp/Photos/Others"     # For Linux (NAS)
    input_others_folder = r"r:\jaimetur_ftp\Photos\Others"                # For Windows
    synology_upload_folder(input_others_folder)

    # 4) Example: Create albums from subfolders in 'r:\jaimetur\OrganizeTakeoutPhotos\Upload_folder\Albums'
    print("\n=== EXAMPLE: synology_upload_albums() ===")
    input_albums_folder = "/volume1/homes/jaimetur_ftp/Photos/Albums"     # For Linux (NAS)
    input_albums_folder = r"r:\jaimetur_ftp\Photos\Albums"                # For Windows
    synology_upload_albums(input_albums_folder)

    # 5) Example: Download all photos from ALL albums
    print("\n=== EXAMPLE: synology_download_albums() ===")
    # total = synology_download_albums('ALL', output_folder="Downloads_Synology")
    total = synology_download_albums(albums_name='Cadiz', output_folder="Downloads_Synology")
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # 6) Example: Download everything in the structure /Albums/<albumName>/ + /Others/yyyy/mm
    print("=== EXAMPLE: synology_download_ALL() ===")
    total_struct = synology_download_ALL(output_folder="Downloads_Synology")
    print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # 7) Local logout
    logout_synology()


    # Define albums_folder_path
    albums_folder_path = "/volume1/homes/jaimetur_ftp/Photos/Albums"     # For Linux (NAS)
    albums_folder_path = r"r:\jaimetur_ftp\Photos\Albums"                 # For Windows

    # ExtractSynologyPhotosAlbums(album_name='ALL')
    synology_download_albums(albums_name='Cadiz')

    # result = wait_for_reindexing_synology_photos()
    # LOGGER.info(f"INFO: Index Result: {result}")

    # if wait_for_reindexing_synology_photos():
    #     delete_synology_photos_duplicates_albums()
    #     delete_synology_phptos_empty_albums()
    #     create_synology_photos_albums(albums_folder_path)