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
import Utils
import fnmatch
from tqdm import tqdm
import mimetypes

# -----------------------------------------------------------------------------
#                          GLOBAL VARIABLES
# -----------------------------------------------------------------------------
global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD, SYNOLOGY_ROOT_PHOTOS_PATH
global SESSION, SID

# Initialize global variables
CONFIG = None
SESSION = None
SID = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                            AUXILIARY FUNCTIONS                             #
##############################################################################
# -----------------------------------------------------------------------------
#                          CONFIGURATION READING
# -----------------------------------------------------------------------------
def read_synology_config(config_file='CONFIG.ini', show_info=True):
    """
    Reads the Synology configuration file and updates global variables.
    If the configuration file is not found, prompts the user to manually input required data.

    Args:
        config_file (str): The path to the Synology configuration file. Default is 'Synology.config'.
        show_info (bool): Whether to display the loaded configuration information. Default is True.

    Returns:
        dict: The loaded configuration dictionary.
    """
    global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD, SYNOLOGY_ROOT_PHOTOS_PATH
    from GlobalVariables import LOGGER  # Import the logger inside the function
    from ConfigReader import load_config

    if CONFIG:
        return CONFIG

    # Load CONFIG from config_file
    CONFIG = {}
    CONFIG = load_config(config_file)

    # Extract specific values for Synology from CONFIG.
    SYNOLOGY_URL                = CONFIG.get('SYNOLOGY_URL', None)
    SYNOLOGY_USERNAME           = CONFIG.get('SYNOLOGY_USERNAME', None)
    SYNOLOGY_PASSWORD           = CONFIG.get('SYNOLOGY_PASSWORD', None)
    SYNOLOGY_ROOT_PHOTOS_PATH   = CONFIG.get('SYNOLOGY_ROOT_PHOTOS_PATH', None)
    SYNOLOGY_ROOT_PHOTOS_PATH   = Utils.fix_paths(SYNOLOGY_ROOT_PHOTOS_PATH)

    # Verify required parameters and prompt on screen if missing
    if not SYNOLOGY_URL or SYNOLOGY_URL.strip()=='':
        LOGGER.warning(f"WARNING : SYNOLOGY_URL not found. It will be requested on screen.")
        CONFIG['SYNOLOGY_URL'] = input("\nEnter SYNOLOGY_URL: ")
        SYNOLOGY_URL = CONFIG['SYNOLOGY_URL']
    if not SYNOLOGY_USERNAME or SYNOLOGY_USERNAME.strip()=='':
        LOGGER.warning(f"WARNING : SYNOLOGY_USERNAME not found. It will be requested on screen.")
        CONFIG['SYNOLOGY_USERNAME'] = input("\nEnter SYNOLOGY_USERNAME: ")
        SYNOLOGY_USERNAME = CONFIG['SYNOLOGY_USERNAME']
    if not SYNOLOGY_PASSWORD or SYNOLOGY_PASSWORD.strip()=='':
        LOGGER.warning(f"WARNING : SYNOLOGY_PASSWORD not found. It will be requested on screen.")
        CONFIG['SYNOLOGY_PASSWORD'] = input("\nEnter SYNOLOGY_PASSWORD: ")
        SYNOLOGY_PASSWORD = CONFIG['SYNOLOGY_PASSWORD']
    if not SYNOLOGY_ROOT_PHOTOS_PATH or SYNOLOGY_ROOT_PHOTOS_PATH.strip()=='':
        LOGGER.warning(f"WARNING : SYNOLOGY_ROOT_PHOTOS_PATH not found. It will be requested on screen.")
        CONFIG['SYNOLOGY_ROOT_PHOTOS_PATH'] = input("\nEnter SYNOLOGY_ROOT_PHOTOS_PATH: ")
        SYNOLOGY_ROOT_PHOTOS_PATH = CONFIG['SYNOLOGY_ROOT_PHOTOS_PATH']

    if show_info:
        LOGGER.info("")
        LOGGER.info(f"INFO    : Synology Config Read:")
        LOGGER.info(f"INFO    : ---------------------")
        masked_password = '*' * len(SYNOLOGY_PASSWORD)
        LOGGER.info(f"INFO    : SYNOLOGY_URL              : {SYNOLOGY_URL}")
        LOGGER.info(f"INFO    : SYNOLOGY_USERNAME         : {SYNOLOGY_USERNAME}")
        LOGGER.info(f"INFO    : SYNOLOGY_PASSWORD         : {masked_password}")
        LOGGER.info(f"INFO    : SYNOLOGY_ROOT_PHOTOS_PATH : {SYNOLOGY_ROOT_PHOTOS_PATH}")

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
    from GlobalVariables import LOGGER

    # If a session is already active, return it instead of creating a new one
    if SESSION and SID:
        return SESSION, SID

    # Read server configuration
    read_synology_config()

    LOGGER.info("")
    LOGGER.info(f"INFO    : Authenticating on Synology Photos and getting Session...")

    SESSION = requests.Session()
    url = f"{SYNOLOGY_URL}/webapi/auth.cgi"
    params = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": SYNOLOGY_USERNAME,
        "passwd": SYNOLOGY_PASSWORD,
        "format": "sid",
    }
    response = SESSION.get(url, params=params, verify=False)
    response.raise_for_status()
    data = response.json()
    if data.get("success"):
        SESSION.cookies.set("id", data["data"]["sid"])  # Set the SID as a cookie
        LOGGER.info(f"INFO    : Authentication Successfully with user/password found in Config file.")
        SID = data["data"]["sid"]
        return SESSION, SID
    else:
        LOGGER.error(f"ERROR   : Unable to authenticate with the provided NAS data: {data}")
        sys.exit(-1)

def logout_synology():
    """
    Logs out from the Synology NAS and clears the active session and SID.
    """
    global SESSION
    global SID
    from GlobalVariables import LOGGER

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
            LOGGER.info("INFO    : Session closed successfully.")
            SESSION = None
            SID = None
        else:
            LOGGER.error("ERROR   : Unable to close session in Synology NAS.")

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
                LOGGER.info("INFO    : This process may take several minutes or even hours to finish depending on the number of files to index. Please be patient...")
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

        with tqdm(total=files_to_index, smoothing=0.8, file=LOGGER.tqdm_stream, desc="INFO    : Reindexing files", unit=" files") as pbar:
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
#                          FOLDERS FUNCTIONS
# -----------------------------------------------------------------------------
def get_photos_root_folder_id():
    """
    Retrieves the folder_id of the root folder in Synology Photos.

    Returns:
        int: The ID of the folder (folder_id).
    """

    from GlobalVariables import LOGGER  # Import the logger inside the function

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
        LOGGER.error("ERROR   : Cannot obtain Photos Root Folder ID due to an error in the API call.")
        sys.exit(-1)
    # Extract the folder_id
    folder_name = data["data"]["folder"]["name"]
    folder_id = str(data["data"]["folder"]["id"])
    if not folder_id or folder_name != "/":
        LOGGER.error("ERROR   : Cannot obtain Photos Root Folder ID.")
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
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.error(f"ERROR   : Cannot obtain name for folder ID '{search_in_folder_id}' due to an error in the API call.")
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
            LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{folder_name}' due to an error in the API call.")
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
# TODO: refactor this function to create_folder
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
    from GlobalVariables import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # Use Synology Photos root folder if no parent folder ID is provided
    if not parent_folder_id:
        photos_root_folder_id = get_photos_root_folder_id()
        parent_folder_id = photos_root_folder_id
        LOGGER.info(f"INFO    : Parent Folder ID not provided, using Synology Photos root folder ID: '{photos_root_folder_id}' as parent folder.")

    # Check if the folder already exists
    folder_id = get_folder_id(search_in_folder_id=parent_folder_id, folder_name=folder_name)
    if folder_id:
        # LOGGER.warning(f"WARNING : The folder '{folder_name}' already exists.")
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
        LOGGER.info(f"INFO    : Folder '{folder_name}' successfully created.")
        return data['data']['folder']['id']
    else:
        LOGGER.error(f"ERROR   : Failed to create the folder: '{folder_name}'")
        return None

# Function to delete a folder
# TODO: Complete this function
def delete_folder(folder_id):
  pass

# Function to return the number of files within a folder
# TODO: Complete this function
def get_folder_items_count(folder_id, folder_name):
  pass

# -----------------------------------------------------------------------------
#                          ALBUMS FUNCTIONS
# -----------------------------------------------------------------------------
def create_album(album_name):
    # Create the album if the folder contains supported files
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.error(f"ERROR   : Unable to create album '{album_name}': {data}")
        return -1
    album_id = data["data"]["album"]["id"]
    LOGGER.info(f"INFO    : Album '{album_name}' created with ID: {album_id}.")
    return album_id


def delete_album(album_id, album_name):
    """
    Deletes an album in Synology Photos.

    Args:
        album_id (str): ID of the album to delete.
        album_name (str): Name of the album to delete.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.warning(f"WARNING : Could not delete album {album_id}: ", data)

def get_albums():
    """
    Lists all albums in Synology Photos.

    Returns:
        dict: A dictionary with album IDs as keys and album names as values.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function

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
            LOGGER.error("ERROR   : Failed to list albums: ", data)
            return -1
        # Check if fewer items than the limit were returned
        if len(data["data"]["list"]) < limit:
            break
        # Increment offset for the next page
        offset += limit
    return albums_dict


def get_albums_own_and_shared():
    """
    Lists both own and shared albums in Synology Photos.

    Returns:
        list: A list of albums.
    """
    from GlobalVariables import LOGGER
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
                LOGGER.error("ERROR   : Failed to list own albums:", data)
                return []
            album_list.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        except Exception as e:
            LOGGER.error("ERROR   : Exception while listing own albums:", e)
            return []
    return album_list[0]


def get_album_items_count(album_id, album_name):
    """
    Gets the number of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.

    Returns:
        int: Number of items in the album.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.warning(f"WARNING : Cannot count files for album: '{album_name}' due to API call error. Skipped!")
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
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
            LOGGER.warning(f"WARNING : Cannot list files for album: '{album_name}' due to API call error. Skipped!")
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

# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS) FUNCTIONS
# -----------------------------------------------------------------------------
def get_all_assets():
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
    offset = 0
    limit = 5000
    all_assets = []
    while True:
        params = {
            'api': 'SYNO.Foto.Browse.Item',
            'version': '4',
            'method': 'list',
            "offset": offset,
            "limit": limit
        }
        try:
            response = SESSION.get(url, params=params, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR   : Failed to list assets")
                return []
            all_assets.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while listing assets", e)
            return []
    return all_assets[0]


def get_assets_from_album(album_name, album_id):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
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
                LOGGER.error(f"ERROR   : Failed to list photos in the album '{album_name}'")
                return []
            album_items.append(data["data"]["list"])
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while listing photos in the album '{album_name}'", e)
            return []
    return album_items[0]


def add_assets_to_album(folder_id, album_name):
    """
    Adds photos from a folder to an album.

    Args:
        folder_id (str): The ID of the folder containing the assets.
        album_name (str): The name of the album to create or add assets to.

    Returns:
        int: The total number of assets added to the album, or -1 in case of an error.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.warning(f"WARNING : Cannot count files in folder: '{album_name}' due to API call error. Skipped!")
        return -1

    # Check if there are assets to add
    num_files = data["data"]["count"]
    if not num_files > 0:
        LOGGER.warning(f"WARNING : No supported assets found in folder: '{album_name}'. Skipped!")
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
            LOGGER.warning(f"WARNING : Cannot list files in folder: '{album_name}' due to API call error. Skipped!")
            return -1
        file_ids.extend([str(item["id"]) for item in data["data"]["list"] if "id" in item])
        # Check if fewer items than the limit were returned
        if len(data["data"]["list"]) < limit:
            break
        # Increment the offset for the next page
        offset += limit

    if not len(file_ids) > 0:
        LOGGER.warning(f"WARNING : No supported assets found in folder: '{album_name}'. Skipped!")
        return -1

    # Create new Album
    album_id = create_album(album_name)

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
            LOGGER.warning(
                f"WARNING : Unable to add assets to album '{album_name}' (Batch {i // batch_size + 1}). Skipped!")
            continue
        total_added += len(batch)
    return total_added


def delete_assets(asset_ids):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    login_synology()
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"


    if not isinstance(asset_ids, list):
        asset_ids = [asset_ids]

    params = {
        'api': 'SYNO.Foto.BackgroundTask.File',
        'version': '1',
        'method': 'delete',
        'item_id': f'{asset_ids}',
        'folder_id': '[]'
    }
    # params = json.dumps(params, indent=2)
    try:
        response = SESSION.get(url, params=params, verify=False)
        data = response.json()
        if not data.get("success"):
            LOGGER.error(f"ERROR   : Failed to list assets")
            return False
    except Exception as e:
        LOGGER.error(f"ERROR   : Exception while listing assets", e)
        return False
    return True

# TODO: Refactor to upload_asset()
def upload_file_to_synology(file_path, album_name=None):
    """
    Uploads a file (photo or video) to a Synology Photos folder.

    Args:
        file_path (str): Path to the file to upload.
        album_name (str, optional): Name of the album associated with the upload.

    Returns:
        int: Status code indicating success or failure.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    stats = os.stat(file_path)
    url = f"{SYNOLOGY_URL}/webapi/entry.cgi"

    # Verifica si el archivo existe antes de continuar
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El archivo '{file_path}' no existe.")

    # Obtiene la información del archivo
    stats = os.stat(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    file = open(file_path, 'rb')
    file.close()
    files = {
        'file': open(file_path, 'rb').close(),
    }

    api_path = 'SYNO.Foto.Upload.Item'
    api_version = '1'
    method = 'upload'
    filename = os.path.basename(file_path)
    # url = f'{url}/{api_path}?api={api_path}&version={api_version}&method={method}&_sid={SID}'


    # Construcción del payload con el formato correcto
    payload = {
        'api': 'SYNO.Foto.Upload.Item',
        'method': 'upload',
        'version': '1',
        'name': os.path.basename(file_path),  # 🔹 Ahora se asegura que `name` esté en los datos
        'uploadDestination': 'timeline',
        'duplicate': 'ignore',
        'mtime': str(int(stats.st_mtime)),
        'folder': '["PhotoLibrary"]'  # 🔹 Se mantiene en formato JSON-string
    }

    # Carga el archivo como binario en una tupla (clave, (nombre, contenido, tipo_mime))
    files = {
        'file': (os.path.basename(file_path), open(file_path, 'rb'), mime_type)
    }

    HEADERS = {'Content-Type': 'application/json; charset="UTF-8"'}

    print(json.dumps(HEADERS, indent=4, ensure_ascii=False))
    print(json.dumps(payload, indent=4, ensure_ascii=False))

    # Envía la solicitud a la API
    response = SESSION.post(url, headers=HEADERS, data=payload, files=files, verify=False)
    response.raise_for_status()
    data = response.json()
    if not data["success"]:
        LOGGER.warning(f"WARNING : Cannot upload asset: '{file_path}' due to API call error. Skipped!")
        return -1

# TODO: Refactor to add_asset_to_folder() and ise the id that returns upload_asset() to associate it to a folder
def upload_file_to_synology_folder(file_path, album_name=None):
    """
    Uploads a file (photo or video) to a Synology Photos folder.

    Args:
        file_path (str): Path to the file to upload.
        album_name (str, optional): Name of the album associated with the upload.

    Returns:
        int: Status code indicating success or failure.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
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
        LOGGER.warning(f"WARNING : Cannot upload assets to folder: '{album_name}' due to API call error. Skipped!")
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
    from GlobalVariables import LOGGER
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
            if not data['success']:
                LOGGER.error(f"ERROR   : Failed to copy batch {i + 1}/{total_batches} of assets: {data}")
                return 0
            # LOGGER.info(f"INFO    : Batch {i + 1}/{total_batches} of assets successfully downloaded to the folder '{folder_name}' (ID:{folder_id}).")
        extracted_photos = len(photos_list)
        return extracted_photos
    except Exception as e:
        LOGGER.error(f"ERROR   : Exception while copying assets batches: {e}")

##############################################################################
#                           END OF AUX FUNCTIONS                             #
##############################################################################


##############################################################################
#           MAIN FUNCTIONS TO CALL FROM OTHER MODULES                        #
##############################################################################
# Function to upload albums to Synology Photos
def synology_upload_albums(input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=None):
    """
    Upload albums into Synology Photos based on folders in the NAS.

    Args:
        input_folder (str): Base path on the NAS where the album folders are located.

    Returns:
        tuple: albums_created, albums_skipped, assets_added
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()

    # Check if albums_folder is inside SYNOLOGY_ROOT_PHOTOS_PATH
    input_folder = Utils.remove_quotes(input_folder)
    if input_folder.endswith(os.path.sep):
        input_folder = input_folder[:-1]
    if not os.path.isdir(input_folder):
        LOGGER.error(f"ERROR   : Cannot find album folder '{input_folder}'. Exiting...")
        sys.exit(-1)
    LOGGER.info(f"INFO    : Albums Folder Path: '{input_folder}'")
    albums_folder_full_path = os.path.realpath(input_folder)
    ROOT_PHOTOS_PATH_full_path = os.path.realpath(SYNOLOGY_ROOT_PHOTOS_PATH)
    ROOT_PHOTOS_PATH_full_path = Utils.remove_server_name(ROOT_PHOTOS_PATH_full_path)
    albums_folder_full_path = Utils.remove_server_name(albums_folder_full_path)
    if ROOT_PHOTOS_PATH_full_path not in albums_folder_full_path:
        LOGGER.error(f"ERROR   : Albums folder: '{albums_folder_full_path}' should be inside SYNOLOGY_ROOT_PHOTOS_PATH: '{ROOT_PHOTOS_PATH_full_path}'")
        sys.exit(-1)

    LOGGER.info("INFO    : Reindexing Synology Photos database before adding content...")

    # Process folders and create albums
    albums_created = 0
    albums_skipped = 0
    assets_added = 0

    if wait_for_reindexing_synology_photos():
        # Step 1: Get the root folder ID of Synology Photos for the authenticated user
        photos_root_folder_id = get_photos_root_folder_id()
        LOGGER.info(f"INFO    : Synology Photos root folder ID: {photos_root_folder_id}")

        # Step 2: Get the folder ID of the directory containing the albums
        albums_folder_relative_path = os.path.relpath(albums_folder_full_path, ROOT_PHOTOS_PATH_full_path)
        albums_folder_relative_path = "/" + os.path.normpath(albums_folder_relative_path).replace("\\", "/")
        albums_folder_id = get_folder_id(search_in_folder_id=photos_root_folder_id, folder_name=os.path.basename(input_folder))
        LOGGER.info(f"INFO    : Albums folder ID: {albums_folder_id}")
        if not albums_folder_id:
            LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{albums_folder_relative_path}/{input_folder}'. The folder may not have been indexed yet. Try forcing indexing and retry.")
            sys.exit(-1)

        # Filter albums_folder to exclude '@eaDir'
        albums_folder_filtered = os.listdir(input_folder)
        albums_folder_filtered[:] = [d for d in albums_folder_filtered if d != '@eaDir']
        LOGGER.info(f"INFO    : Processing all albums in folder '{input_folder}' and creating corresponding albums into Synology Photos...")
        for album_folder in tqdm(albums_folder_filtered, file=LOGGER.tqdm_stream, desc="INFO    : Uploading Albums", unit=" albums"):
            # Step 3: For each album folder, get the folder ID in the directory containing the albums
            individual_album_folder_id = get_folder_id(search_in_folder_id=albums_folder_id, folder_name=os.path.basename(album_folder))
            if not individual_album_folder_id:
                LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{albums_folder_relative_path}/{album_folder}'. The folder may not have been indexed yet. Skipping this album creation.")
                albums_skipped += 1
                continue

            # Step 4: Add all photos or videos in the album folder to the newly created album
            res = add_assets_to_album(folder_id=individual_album_folder_id, album_name=album_folder)
            if res == -1:
                albums_skipped += 1
            else:
                albums_created += 1
                assets_added += res

    LOGGER.info("INFO    : Album creation in Synology Photos completed!")
    logout_synology()
    return albums_created, albums_skipped, assets_added

# Function synology_upload_folder()
# TODO: synology_upload_folder()
def synology_upload_no_albums(input_folder, subfolders_exclusion='Albums', subfolders_inclusion=None):
    """
    Upload folder into Synology Photos.

    Args:
        input_folder (str): Base path on the NAS where the album folders are located.

    Returns:
        tuple: folders_created, folders_skipped, assets_added
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()

    LOGGER.warning("WARNING : This mode is not yet supported. Exiting.")
    sys.exit(-1)

    # Check if albums_folder is inside SYNOLOGY_ROOT_PHOTOS_PATH
    input_folder = Utils.remove_quotes(input_folder)
    if input_folder.endswith(os.path.sep):
        input_folder = input_folder[:-1]
    if not os.path.isdir(input_folder):
        LOGGER.error(f"ERROR   : Cannot find folder '{input_folder}'. Exiting...")
        sys.exit(-1)
    LOGGER.info(f"INFO    : Folder Path: '{input_folder}'")
    folder_full_path = os.path.realpath(input_folder)
    ROOT_PHOTOS_PATH_full_path = os.path.realpath(SYNOLOGY_ROOT_PHOTOS_PATH)
    ROOT_PHOTOS_PATH_full_path = Utils.remove_server_name(ROOT_PHOTOS_PATH_full_path)
    folder_full_path = Utils.remove_server_name(folder_full_path)
    if ROOT_PHOTOS_PATH_full_path not in folder_full_path:
        LOGGER.error(f"ERROR   : Folder: '{folder_full_path}' should be inside SYNOLOGY_ROOT_PHOTOS_PATH: '{ROOT_PHOTOS_PATH_full_path}'")
        sys.exit(-1)

    LOGGER.info("INFO    : Reindexing Synology Photos database before adding content...")
    if wait_for_reindexing_synology_photos():
        # Step 1: Get the root folder ID of Synology Photos for the authenticated user
        photos_root_folder_id = get_photos_root_folder_id()
        LOGGER.info(f"INFO    : Synology Photos root folder ID: {photos_root_folder_id}")

        # Step 2: Get the folder ID of the directory containing the albums
        folder_relative_path = os.path.relpath(folder_full_path, ROOT_PHOTOS_PATH_full_path)
        folder_relative_path = "/" + os.path.normpath(folder_relative_path).replace("\\", "/")
        folder_id = get_folder_id(search_in_folder_id=photos_root_folder_id, folder_name=os.path.basename(input_folder))
        LOGGER.info(f"INFO    : Folder ID: {folder_id}")
        if not folder_id:
            LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{folder_relative_path}/{input_folder}'. The folder may not have been indexed yet. Try forcing indexing and retry.")
            sys.exit(-1)

        # Process folders
        folders_created = 0
        folders_skipped = 0
        assets_added = 0

        # Filter albums_folder to exclude '@eaDir'
        folder_filtered = os.listdir(input_folder)
        folder_filtered[:] = [d for d in folder_filtered if d != '@eaDir']
        LOGGER.info(f"INFO    : Processing all subfolders in folder '{input_folder}' and uploading corresponding assets into Synology Photos...")
        for input_folder in tqdm(folder_filtered, file=LOGGER.tqdm_stream, desc="INFO    : Uploading Folder", unit=" folders"):
            # Step 3: For each album folder, get the folder ID in the directory containing the albums
            individual_folder_id = get_folder_id(search_in_folder_id=folder_id, folder_name=os.path.basename(input_folder))
            if not individual_folder_id:
                LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{folder_relative_path}/{input_folder}'. The folder may not have been indexed yet. Skipping this folder creation.")
                folders_skipped += 1
                continue

            # Step 4: Add all photos or videos in the album folder to the newly created album
            # TODO: ESTA PARTE SOBRA PORQUE NO QUIERO AÑADIR LOS ASSETS A NINGÚN ALBÚM, PERO SI NO HACEMOS ESTO, EN REALIDAD NO ESTAMOS HACIENDO NADA, YA QUE LA CARPETA A AÑADIR YA ESTÁ DENTRO DE SYNOLOGY PHOTOS Y POR TANTO ESTÁ SIENDO INDEXADA
            # TODO: BUSCAR LA FORMA DE AÑADIR UNA CARPETA DESDE EL EXTERIOR DE SYNOOGY FOTOS.
            res = add_assets_to_album(folder_id=individual_folder_id, album_name=input_folder)
            if res == -1:
                folders_skipped += 1
            else:
                folders_created += 1
                assets_added += res

    LOGGER.info("INFO    : Folder Uploaded into Synology Photos!")
    logout_synology()
    return folders_created, folders_skipped, assets_added



# -----------------------------------------------------------------------------
#          COMPLETE UPLOAD OF ALL ASSETS (Albums + No-Albums)
# -----------------------------------------------------------------------------
def synology_upload_ALL(input_folder, albums_folders=None):
    """
    Uploads ALL photos and videos from input_folder into Synology Photos:

    Returns the total number of albums and assets uploaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    login_synology()

    total_assets_uploaded_within_albums = 0
    total_albums_uploaded = 0
    total_albums_skipped = 0

    if albums_folders:
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets and creating Albums into synology Photos from '{albums_folders}' subfolders...")
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums = synology_upload_albums(input_folder=input_folder, subfolders_inclusion=albums_folders)
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")
        total_assets_uploaded_without_albums = synology_upload_no_albums(input_folder=input_folder, subfolders_exclusion=albums_folders)
    else:
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}'...")
        total_assets_uploaded_without_albums = synology_upload_no_albums(input_folder=input_folder)

    total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

    return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums


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
    from GlobalVariables import LOGGER
    login_synology()
    # Variables to return
    albums_downloaded = 0
    assets_downloaded = 0

    # Create or obtain the main folder 'Albums_Synology_Photos'
    main_folder_id = get_folder_id_or_create_folder(output_folder)
    if not main_folder_id:
        LOGGER.error(f"ERROR   : Failed to obtain or create the main folder '{output_folder}'.")
        return albums_downloaded, assets_downloaded

    main_subfolder_id = get_folder_id_or_create_folder("Albums", parent_folder_id=main_folder_id)
    if not main_subfolder_id:
        LOGGER.error(f"ERROR   : Failed to obtain or create the folder 'Albums'.")
        return albums_downloaded, assets_downloaded

    download_folder = os.path.join(output_folder, 'Albums')
    # List own and shared albums
    all_albums = get_albums_own_and_shared()
    # Determine the albums to copy
    if isinstance(albums_name, str) and albums_name.strip().upper() == 'ALL':
        albums_to_download = all_albums
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
            return albums_downloaded, assets_downloaded
        LOGGER.info(f"INFO    : {len(albums_to_download)} albums from Synology Photos will be downloaded to '{download_folder}' within Synology Photos root folder...")

    albums_downloaded = len(albums_to_download)
    # Iterate over each album to copy
    for album in tqdm(albums_to_download, file=LOGGER.tqdm_stream, desc="INFO    : Downloading Albums", unit=" albums"):
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
        target_folder_id = get_folder_id_or_create_folder(target_folder_name, parent_folder_id=main_subfolder_id)
        if not target_folder_id:
            LOGGER.warning(f"WARNING : Failed to obtain or create the destination folder for the album '{album_name}'.")
            continue
        # Download the photos to the destination folder
        assets_downloaded += download_assets(target_folder_id, target_folder_name, photos)

    LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{os.path.join(SYNOLOGY_ROOT_PHOTOS_PATH, download_folder)}'")
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
    from GlobalVariables import LOGGER
    login_synology()
    output_folder = os.path.join(output_folder,"Albums")
    os.makedirs(output_folder, exist_ok=True)
    # Variables to return
    assets_downloaded = 0
    # Create or obtain the main folder 'Albums_Synology_Photos'
    main_folder = output_folder
    main_folder_id = get_folder_id_or_create_folder(main_folder)
    if not main_folder_id:
        LOGGER.error(f"ERROR   : Failed to obtain or create the main folder '{main_folder}'.")
        return  assets_downloaded

    return  assets_downloaded


# Function synology_download_ALL()
def synology_download_ALL(output_folder="Downloads_Synology"):
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()

    LOGGER.warning("WARNING : This mode is not yet supported. Exiting.")
    sys.exit(-1)

    synology_download_albums(albums_name='ALL', output_folder=output_folder)
    synology_download_no_albums(output_folder=output_folder)

# Function to delete empty albums in Synology Photos
def synology_remove_empty_albums():
    """
    Deletes all empty albums in Synology Photos.

    Returns:
        int: The number of empty albums deleted.
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()

    # List albums and identify empty ones
    albums_dict = get_albums()
    albums_deleted = 0
    if albums_dict != -1:
        LOGGER.info("INFO    : Looking for empty albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, file=LOGGER.tqdm_stream, desc="INFO    : Processing Albums", unit=" albums"):
            item_count = get_album_items_count(album_id=album_id, album_name=album_name)
            if item_count == 0:
                LOGGER.info(f"INFO    : Deleting empty album: '{album_name}' (ID: {album_id})")
                delete_album(album_id=album_id, album_name=album_name)
                albums_deleted += 1

    LOGGER.info("INFO    : Deleting empty albums process finished!")
    logout_synology()
    return albums_deleted

# Function to delete duplicate albums in Synology Photos
def synology_remove_duplicates_albums():
    """
    Deletes all duplicate albums in Synology Photos.

    Returns:
        int: The number of duplicate albums deleted.
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    login_synology()

    # List albums and identify duplicates
    albums_dict = get_albums()
    albums_deleted = 0
    albums_data = {}
    if albums_dict != -1:
        LOGGER.info("INFO    : Looking for duplicate albums in Synology Photos...")
        for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, file=LOGGER.tqdm_stream, desc="INFO    : Processing Albums", unit=" albums"):
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
            LOGGER.info(f"INFO    : Deleting duplicate album: '{album_name}' (ID: {album_id})")
            delete_album(album_id=album_id, album_name=album_name)
            albums_deleted += 1

    LOGGER.info("INFO    : Deleting duplicate albums process finished!")
    logout_synology()
    return albums_deleted


# -----------------------------------------------------------------------------
#          DELETE ALL ASSETS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_assets():
    from GlobalVariables import LOGGER  # Import global LOGGER
    login_synology()
    all_assets = get_all_assets()
    total_assets_found = len(all_assets)
    if total_assets_found == 0:
        LOGGER.warning(f"WARNING : No Assets found in Immich Database.")
        return 0,0
    LOGGER.info(f"INFO    : Found {total_assets_found} asset(s) to delete.")
    assets_ids = []
    assets_deleted = len(all_assets)
    for asset in tqdm(all_assets, file=LOGGER.tqdm_stream, desc="INFO    : Deleting assets", unit="assets"):
        asset_id = asset.get("id")
        if not asset_id:
            continue
        assets_ids.append(asset_id)

    ok = delete_assets(assets_ids)
    if ok:
        albums_deleted = synology_remove_empty_albums()
        LOGGER.info(f"INFO    : Total Assets deleted: {assets_deleted}")
        LOGGER.info(f"INFO    : Total Albums deleted: {albums_deleted}")
        return assets_deleted, albums_deleted
    else:
        LOGGER.error(f"ERROR   : Failed to delete assets.")
        return 0, 0

# -----------------------------------------------------------------------------
#          DELETE ALL ALL ALBUMS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_albums(deleteAlbumsAssets=False):
    """
    Deletes all albums and optionally also its associated assets.
    Returns the number of albums deleted and the number of assets deleted.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    login_synology()
    albums = get_albums()
    if not albums:
        LOGGER.info("INFO    : No albums found.")
        return 0, 0
    total_deleted_albums = 0
    total_deleted_assets = 0
    for album in tqdm(albums, file=LOGGER.tqdm_stream, desc=f"INFO    : Searching for Albums to delete", unit=" albums"):
        album_id = album.get("id")
        album_name = album.get("albumName")
        album_assets_ids = []
        # if deleteAlbumsAssets is True, we have to delete also the assets associated to the album, album_id
        if deleteAlbumsAssets:
            album_assets = get_assets_from_album(album_id)
            for asset in album_assets:
                album_assets_ids.append(asset.get("id"))
            delete_assets(album_assets_ids)
            total_deleted_assets += len(album_assets_ids)

        # Now we can delete the album
        if delete_album(album_id, album_name):
            # LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) deleted.")
            total_deleted_albums += 1

    LOGGER.info(f"INFO    : Deleted {total_deleted_albums} albums.")
    if deleteAlbumsAssets:
        LOGGER.info(f"INFO    : Deleted {total_deleted_assets} assets associated to albums.")
    return total_deleted_albums, total_deleted_assets


##############################################################################
#                           END OF MAIN FUNCTIONS                            #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Create initialize LOGGER.
    from GlobalVariables import set_ARGS_PARSER
    set_ARGS_PARSER()

    # 0) Read configuration and log in
    read_synology_config('CONFIG.ini')
    login_synology()

    # # # 1) Example: Delete empty albums
    # print("=== EXAMPLE: synology_delete_empty_albums() ===")
    # deleted = synology_delete_empty_albums()
    # print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # # 2) Example: Delete duplicate albums
    # print("=== EXAMPLE: synology_delete_duplicates_albums() ===")
    # duplicates = synology_delete_duplicates_albums()
    # print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # TODO: Complete this function
    print("\n=== EXAMPLE: upload_file_to_synology() ===")
    file_path = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums\2003.07 - Viaje a Almeria (Julio 2003)\En Almeria (Julio 2003)_17.JPG"                # For Windows
    upload_file_to_synology(file_path)

    # # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur_share\Photos\Upload_folder\No-Albums'
    # # TODO: Complete this function
    # print("\n=== EXAMPLE: synology_upload_folder() ===")
    # input_others_folder = r"r:\jaimetur_share\Photos\Upload_folder_for_testing"                # For Windows
    # input_others_folder = "/volume1/homes/jaimetur_share/Photos/Upload_folder_for_testing"     # For Linux (NAS)
    # synology_upload_no_albums(input_others_folder)

    # # 4) Example: Upload albums from subfolders in 'r:\jaimetur_share\Photos\Upload_folder_for_testing\Albums'
    # # TODO: Permitir subir una carpeta cualquiera sin que tenga que haber una carpeta 'Albums' dentro
    # print("\n=== EXAMPLE: synology_upload_albums() ===")
    # input_albums_folder = "/volume1/homes/jaimetur_share/Photos/Upload_folder_for_testing"     # For Linux (NAS)
    # input_albums_folder = r"r:\jaimetur_share\Photos\Upload_folder_for_testing"                # For Windows
    # synology_upload_albums(input_albums_folder)

    # # 5) Example: Download all photos from ALL albums
    # # TODO: Completar esta función
    # print("\n=== EXAMPLE: synology_download_albums() ===")
    # # total = synology_download_albums('ALL', output_folder="Downloads_Synology")
    # total = synology_download_albums(albums_name='Cadiz', output_folder="Downloads_Synology")
    # print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # # 6) Example: Download everything in the structure /Albums/<albumName>/ + /No-Albums/yyyy/mm
    # # TODO: Completar esta función
    # print("=== EXAMPLE: synology_download_ALL() ===")
    # total_struct = synology_download_ALL(output_folder="Downloads_Synology")
    # # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # 7) Local logout
    logout_synology()


    # # Define albums_folder_path
    # albums_folder_path = "/volume1/homes/jaimetur_share/Photos/Albums"     # For Linux (NAS)
    # albums_folder_path = r"r:\jaimetur_share\Photos\Albums"                 # For Windows
    #
    # # ExtractSynologyPhotosAlbums(album_name='ALL')
    # synology_download_albums(albums_name='Cadiz')

    # result = wait_for_reindexing_synology_photos()
    # LOGGER.info(f"INFO    : Index Result: {result}")

    # if wait_for_reindexing_synology_photos():
    #     delete_synology_photos_duplicates_albums()
    #     delete_synology_phptos_empty_albums()
    #     create_synology_photos_albums(albums_folder_path)