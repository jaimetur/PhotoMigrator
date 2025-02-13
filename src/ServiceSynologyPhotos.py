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
from tqdm import tqdm
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder
import logging
from CustomLogger import set_log_level

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
ALLOWED_SYNOLOGY_SIDECAR_EXTENSIONS = []
ALLOWED_SYNOLOGY_EXTENSIONS = ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                            AUXILIARY FUNCTIONS                             #
##############################################################################
# -----------------------------------------------------------------------------
#                          CONFIGURATION READING
# -----------------------------------------------------------------------------
def read_synology_config(config_file='Config.ini', log_level=logging.INFO):
    """
    Reads the Synology configuration file and updates global variables.
    If the configuration file is not found, prompts the user to manually input required data.

    Args:
        config_file (str): The path to the Synology configuration file. Default is 'Synology.config'.

    Returns:
        dict: The loaded configuration dictionary.
    """
    global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD, SYNOLOGY_ROOT_PHOTOS_PATH
    from GlobalVariables import LOGGER  # Import the logger inside the function
    from ConfigReader import load_config

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if CONFIG:
            return CONFIG
    
        # Load CONFIG from config_file
        CONFIG = {}
        CONFIG = load_config(config_file)
    
        # Extract specific values for Synology from CONFIG.
        SYNOLOGY_URL                = CONFIG.get('SYNOLOGY_URL', None)
        SYNOLOGY_USERNAME           = CONFIG.get('SYNOLOGY_USERNAME', None)
        SYNOLOGY_PASSWORD           = CONFIG.get('SYNOLOGY_PASSWORD', None)
        # SYNOLOGY_ROOT_PHOTOS_PATH   = CONFIG.get('SYNOLOGY_ROOT_PHOTOS_PATH', None)
        # import Utils
        # SYNOLOGY_ROOT_PHOTOS_PATH   = Utils.fix_paths(SYNOLOGY_ROOT_PHOTOS_PATH)
    
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
        # if not SYNOLOGY_ROOT_PHOTOS_PATH or SYNOLOGY_ROOT_PHOTOS_PATH.strip()=='':
        #     LOGGER.warning(f"WARNING : SYNOLOGY_ROOT_PHOTOS_PATH not found. It will be requested on screen.")
        #     CONFIG['SYNOLOGY_ROOT_PHOTOS_PATH'] = input("\nEnter SYNOLOGY_ROOT_PHOTOS_PATH: ")
        #     SYNOLOGY_ROOT_PHOTOS_PATH = CONFIG['SYNOLOGY_ROOT_PHOTOS_PATH']
    
        LOGGER.info("")
        LOGGER.info(f"INFO    : Synology Config Read:")
        LOGGER.info(f"INFO    : ---------------------")
        masked_password = '*' * len(SYNOLOGY_PASSWORD)
        LOGGER.info(f"INFO    : SYNOLOGY_URL              : {SYNOLOGY_URL}")
        LOGGER.info(f"INFO    : SYNOLOGY_USERNAME         : {SYNOLOGY_USERNAME}")
        LOGGER.info(f"INFO    : SYNOLOGY_PASSWORD         : {masked_password}")
        # LOGGER.info(f"INFO    : SYNOLOGY_ROOT_PHOTOS_PATH : {SYNOLOGY_ROOT_PHOTOS_PATH}")
    
        return CONFIG

# -----------------------------------------------------------------------------
#                          AUTHENTICATION / LOGOUT
# -----------------------------------------------------------------------------
def login_synology(use_syno_token=False, log_level=logging.INFO):
    """
    Logs into the NAS and returns the active session with the SID and Synology DSM URL.
    """
    global SESSION, SID, SYNO_TOKEN_HEADER
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # If a session is already active, return it instead of creating a new one
        if SESSION and SID and SYNO_TOKEN_HEADER:
            return SESSION, SID, SYNO_TOKEN_HEADER
        elif SESSION and SID:
            return SESSION, SID

        # Read server configuration
        read_synology_config(log_level=log_level)

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
        if use_syno_token:
            params.update({"enable_syno_token": "yes"})

        response = SESSION.get(url, params=params, verify=False)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            SID = data["data"]["sid"]
            SESSION.cookies.set("id", SID)  # Set the SID as a cookie
            LOGGER.info(f"INFO    : Authentication Successfully with user/password found in Config file. Cookie properly set with session id.")
            if use_syno_token:
                LOGGER.info(f"INFO    : SYNO_TOKEN_HEADER created as global variable. You must include 'SYNO_TOKEN_HEADER' in your request to work with this session.")
                SYNO_TOKEN_HEADER = {
                    "X-SYNO-TOKEN": data["data"]["synotoken"],
                }
                return SESSION, SID, SYNO_TOKEN_HEADER
            else:
                return SESSION, SID
        else:
            LOGGER.error(f"ERROR   : Unable to authenticate with the provided NAS data: {data}")
            sys.exit(-1)

def logout_synology(log_level=logging.INFO):
    """
    Logs out from the Synology NAS and clears the active session and SID.
    """
    global SESSION, SID, SYNO_TOKEN_HEADER
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
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
                SYNO_TOKEN_HEADER = {}
            else:
                LOGGER.error("ERROR   : Unable to close session in Synology NAS.")


# -----------------------------------------------------------------------------
#                          FOLDERS FUNCTIONS
# -----------------------------------------------------------------------------
def get_photos_root_folder_id(log_level=logging.INFO):
    """
    Retrieves the folder_id of the root folder in Synology Photos.

    Returns:
        int: The ID of the folder (folder_id).
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
        # Define the params for the API request
        params = {
            "api": "SYNO.Foto.Browse.Folder",
            "method": "get",
            "version": "2",
        }
        # Make the request
        response = SESSION.get(url, params=params, headers=headers, verify=False)
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


def get_folder_id(search_in_folder_id, folder_name, log_level=logging.WARNING):
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
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        # First, get folder_name for search_in_folder_id
        params = {
            "api": "SYNO.Foto.Browse.Folder",
            "method": "get",
            "version": "2",
            "id": search_in_folder_id,
        }
        # Make the request
        response = SESSION.get(url, params=params, headers=headers, verify=False)
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
            response = SESSION.get(url, params=params, headers=headers, verify=False)
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
def create_folder(folder_name, parent_folder_id=None, log_level=logging.INFO):
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
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        # Use Synology Photos root folder if no parent folder ID is provided
        if not parent_folder_id:
            photos_root_folder_id = get_photos_root_folder_id()
            parent_folder_id = photos_root_folder_id
            LOGGER.warning(f"WARNING : Parent Folder ID not provided, using Synology Photos root folder ID: '{photos_root_folder_id}' as parent folder.")
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
        response = SESSION.get(url, params=params, headers=headers, verify=False)
        data = response.json()
        logout_synology(log_level=log_level)
        if data.get("success"):
            LOGGER.info(f"INFO    : Folder '{folder_name}' successfully created.")
            return data['data']['folder']['id']
        else:
            LOGGER.error(f"ERROR   : Failed to create the folder: '{folder_name}'")
            return None

def get_folders(parent_folder_id, log_level=logging.INFO):
    """
    Lists all albums in Synology Photos.

    Returns:
        dict: A dictionary with album IDs as keys and album names as values.
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
        offset = 0
        limit = 5000
        folders_dict = []
        while True:
            params = {
                "api": "SYNO.Foto.Browse.Folder",
                "method": "list",
                "version": "2",
                "id": parent_folder_id,
                "sort_by": "filename",
                "sort_direction": "asc",
                "offset": offset,
                "limit": limit
            }
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            response.raise_for_status()
            data = response.json()
            if data["success"]:
                # Add IDs filtered by supported extensions
                # folders_dict = {str(item["id"]): item["name"] for item in data["data"]["list"] if "id" in item}
                folders_dict = {item["id"]: item["name"] for item in data["data"]["list"] if "id" in item}
            else:
                LOGGER.error("ERROR   : Failed to list albums: ", data)
                return -1
            # Check if fewer items than the limit were returned
            if len(data["data"]["list"]) < limit:
                break
            # Increment offset for the next page
            offset += limit
        return folders_dict

# Function to remove a folder
# TODO: Complete and Check this function
def remove_folder(folder_id, folder_name, log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        folder_id (str): ID of the folder.
        folder_name (str): Name of the folder.

    Returns:
        list: Number of removed folders.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)

        if not isinstance(folder_id, list):
            folder_id = [folder_id]

        params = {
            'api': 'SYNO.Foto.BackgroundTask.File',
            'version': '1',
            'method': 'delete',
            'item_id': '[]',
            'folder_id': f'{folder_id}',
        }
        try:
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR   : Failed to remove folder '{folder_name}'")
                return 0
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while removing folder '{folder_name}'", e)
            return 0
        return len(folder_id)

# Function to remove empty folder in Synology Photos
def remove_empty_folders(log_level=logging.INFO):
    """
    Recursively removes all empty folders and subfolders in Synology Photos.

    Returns:
        int: The number of empty folders removed.
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Cambia el nivel de registro
        # Iniciar sesión en Synology Photos si no hay una sesión activa
        login_synology(log_level=log_level)
        def delete_empty_folders_recursive(folder_id, folder_name):
            """Recorre y elimina las carpetas vacías de manera recursiva."""
            folders_dict = get_folders(folder_id, log_level=log_level)
            item_count = len(folders_dict)
            deleted_count = 0
            if item_count == 0:
                LOGGER.info("")
                LOGGER.info(f"INFO: Removing empty folder: '{folder_name}' (ID: {folder_id}) within Synology Photos")
                remove_folder(folder_id=folder_id, folder_name=folder_name, log_level=logging.WARNING)
                deleted_count += 1
            for subfolder_id, subfolder_name in tqdm(folders_dict.items(), smoothing=0.1, desc=f"INFO    : Looking for empty subfolders in '{folder_name}'", unit=" folders"):
                # Recursive call to process subfolders first
                deleted_count += delete_empty_folders_recursive(subfolder_id, subfolder_name)
            return deleted_count
        LOGGER.info("INFO    : Starting empty folder removing from Synology Photos...")
        # Obtener el ID de la carpeta raíz
        root_folder_id = get_photos_root_folder_id(log_level=log_level)
        total_removed = delete_empty_folders_recursive(folder_id=root_folder_id, folder_name='/')
        LOGGER.info(f"INFO    : Process Remove empty folders from Synology Photos finished. Total removed folders: {total_removed}")
        logout_synology(log_level=log_level)
        return total_removed


# -----------------------------------------------------------------------------
#                          ALBUMS FUNCTIONS
# -----------------------------------------------------------------------------
def create_album(album_name, log_level=logging.INFO):
    # Create the album if the folder contains supported files
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
        params = {
            "api": "SYNO.Foto.Browse.NormalAlbum",
            "method": "create",
            "version": "3",
            "name": f'"{album_name}"',
        }
        response = SESSION.get(url, params=params, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.error(f"ERROR   : Unable to create album '{album_name}': {data}")
            return -1
        album_id = data["data"]["album"]["id"]
        LOGGER.info(f"INFO    : Album '{album_name}' created with ID: {album_id}.")
        return album_id


def delete_album(album_id, album_name, log_level=logging.INFO):
    """
    Deletes an album in Synology Photos.

    Args:
        album_id (str): ID of the album to delete.
        album_name (str): Name of the album to delete.
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
        params = {
            "api": "SYNO.Foto.Browse.Album",
            "method": "delete",
            "version": "3",
            "id": f"[{album_id}]",
            "name": album_name,
        }
        response = SESSION.get(url, params=params, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING : Could not delete album {album_id}: ", data)

def get_albums(log_level=logging.INFO):
    """
    Lists all albums in Synology Photos.

    Returns:
        dict: A dictionary with album IDs as keys and album names as values.
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
            response = SESSION.get(url, params=params, headers=headers, verify=False)
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


def get_albums_own_and_shared(log_level=logging.INFO):
    """
    Lists both own and shared albums in Synology Photos.

    Returns:
        list: A list of albums.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
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
                response = SESSION.get(url, params=params, headers=headers, verify=False)
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


def get_album_items_count(album_id, album_name, log_level=logging.INFO):
    """
    Gets the number of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.

    Returns:
        int: Number of items in the album.
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
        params = {
            "api": "SYNO.Foto.Browse.Item",
            "method": "count",
            "version": "4",
            "album_id": album_id,
        }
        response = SESSION.get(url, params=params, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING : Cannot count files for album: '{album_name}' due to API call error. Skipped!")
            return -1
        num_files = data["data"]["count"]
        return num_files


def get_album_items_size(album_id, album_name, log_level=logging.INFO):
    """
    Gets the total size of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.

    Returns:
        int: Total size of the items in the album in bytes.
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
            response = SESSION.get(url, params=params, headers=headers, verify=False)
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
def get_all_assets(log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
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
                response = SESSION.get(url, params=params, headers=headers, verify=False)
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


def get_assets_from_album(album_name, album_id, log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
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
                response = SESSION.get(url, params=params, headers=headers, verify=False)
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


def add_assets_to_album(album_id, asset_ids, album_name, log_level=logging.WARNING):
    """
    Adds photos from a folder to an album.

    Args:
        album_id (str): The ID of the folder containing the assets.
        album_name (str): The name of the album to create or add assets to.

    Returns:
        int: The total number of assets added to the album, or -1 in case of an error.
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

        # Check if there are assets to add
        total_added = len(asset_ids)
        if not total_added > 0:
            LOGGER.warning(f"WARNING : No assets found to add to Album: '{album_name}'. Skipped!")
            return -1

        # Define params for the API query
        params = {
            "api": "SYNO.Foto.Browse.NormalAlbum",
            "method": "add_item",
            "version": "1",
            "id": album_id,
            "item": f"{asset_ids}"
        }
        # Make the request
        response = SESSION.get(url, params=params, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING : Cannot add assets to album: '{album_name}' due to API call error. Skipped!")
            return -1
        LOGGER.info(f"INFO    : {total_added} Assets successfully added to album: '{album_name}'.")
        return total_added


def remove_assets(asset_ids, log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)

        if not isinstance(asset_ids, list):
            asset_ids = [asset_ids]

        params = {
            'api': 'SYNO.Foto.BackgroundTask.File',
            'version': '1',
            'method': 'delete',
            'item_id': f'{asset_ids}',
            'folder_id': '[]'
        }
        try:
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR   : Failed to list assets")
                return 0
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while listing assets", e)
            return 0
        return len(asset_ids)


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


def upload_asset(file_path, log_level=logging.INFO):
    """Upload an Asset to Synology Photos."""
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo '{file_path}' no existe.")
        # Check if the file extension is allowed
        filename, ext = os.path.splitext(file_path)
        if ext.lower() not in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS:
            if ext.lower() in ALLOWED_SYNOLOGY_SIDECAR_EXTENSIONS:
                return None
            else:
                LOGGER.warning(f"WARNING : File '{file_path}' has an unsupported extension. Skipped.")
                return None

        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)

        # URL for Synology Photos with api, method and version within the URL (needed when data is sent as MultipartEncoder object.
        api = "SYNO.Foto.Upload.Item"
        method = "upload"
        version = "1"
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi/SYNO.Foto.Upload.Item?api={api}&method={method}&version={version}"

        # Obtain MIME type from file
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        # Force `multipart/form-data`
        with open(file_path, "rb") as file:
            multipart_data = MultipartEncoder(
                fields=[
                    ("api", f'{api}'),
                    ("method", f'{method}'),
                    ("version", f'{version}'),
                    ("file", (os.path.basename(file_path), file, mime_type)),
                    ("uploadDestination", '"timeline"'),
                    ("duplicate", '"ignore"'),
                    ("name", f'"{os.path.basename(file_path)}"'),
                    ("mtime", f'{str(int(os.stat(file_path).st_mtime))}'),
                    # ("folder", f'"{json.dumps(["PhotoLibrary"])}"'),
                    ("folder", f'["PhotoLibrary"]'),
                ],
            )
            # We need to include Content-Type in the header
            headers.update({"Content-Type": multipart_data.content_type})

            # Send request with `multipart/form-data`
            response = SESSION.post(url, data=multipart_data, headers=headers, verify=False)

        response.raise_for_status()
        data = response.json()
        if not data["success"]:
            LOGGER.warning(f"WARNING : Cannot upload asset: '{file_path}' due to API call error. Skipped!")
            return None
        else:
            asset_id = data["data"].get("id")
            return asset_id

def download_assets(folder_id, folder_name, assets_list, log_level=logging.INFO):
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
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
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


##############################################################################
#           MAIN FUNCTIONS TO CALL FROM OTHER MODULES                        #
##############################################################################
# Function to upload albums to Synology Photos
def synology_upload_albums(input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=None, log_level=logging.INFO):
    """
    Traverses the subfolders of 'input_folder', creating an album for each valid subfolder (album name equals the subfolder name). Within each subfolder, it uploads all files with allowed extensions (based on SYNOLOGY_EXTENSIONS) and associates them with the album.
    Example structure:
        input_folder/
            ├─ Album1/   (files for album "Album1")
            └─ Album2/   (files for album "Album2")
    Returns: albums_uploaded, albums_skipped, assets_uploaded
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            return 0

        # Process subfolders_exclusion to obtain a list of inclusion names if provided
        if isinstance(subfolders_exclusion, str):
            subfolders_exclusion = [name.strip() for name in subfolders_exclusion.replace(',', ' ').split() if name.strip()]
        elif isinstance(subfolders_exclusion, list):
            subfolders_exclusion = [name.strip() for item in subfolders_exclusion if isinstance(item, str) for name in item.split(',') if name.strip()]
        else:
            subfolders_exclusion = None

        # Process subfolders_inclusion to obtain a list of inclusion names if provided
        if isinstance(subfolders_inclusion, str):
            subfolders_inclusion = [name.strip() for name in subfolders_inclusion.replace(',', ' ').split() if name.strip()]
        elif isinstance(subfolders_inclusion, list):
            subfolders_inclusion = [name.strip() for item in subfolders_inclusion if isinstance(item, str) for name in item.split(',') if name.strip()]
        else:
            subfolders_inclusion = None

        albums_uploaded = 0
        albums_skipped = 0
        assets_uploaded = 0

        # Directories to exclude
        SUBFOLDERS_EXCLUSIONS = ['@eaDir']
        for subfolder in subfolders_exclusion:
            SUBFOLDERS_EXCLUSIONS.append(subfolder)

        # Search for all valid Albums folders
        valid_folders = []  # List to store valid folder paths
        for root, dirs, _ in os.walk(input_folder):
            dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]  # Exclude directories in the exclusion list
            if subfolders_inclusion:  # Apply SUBFOLDERS_INCLUSION filter if provided
                rel_path = os.path.relpath(root, input_folder)
                if rel_path == ".":
                    dirs[:] = [d for d in dirs if d in subfolders_inclusion]
                else:
                    first_dir = rel_path.split(os.sep)[0]
                    if first_dir not in subfolders_inclusion:
                        dirs[:] = []
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                # Check if there is at least one file with an allowed extension in the subfolder
                has_supported_files = any(os.path.splitext(file)[-1].lower() in ALLOWED_SYNOLOGY_EXTENSIONS for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file)))
                if not has_supported_files:
                    continue
                valid_folders.append(dir_path)

        first_level_folders = os.listdir(input_folder)
        if subfolders_inclusion:
            first_level_folders = first_level_folders + subfolders_inclusion

        # with tqdm(total=len(valid_folders), smoothing=0.1, file=LOGGER.tqdm_stream, desc="INFO    : Uploading Albums from Folders", unit=" folders") as pbar:
        with tqdm(total=len(valid_folders), smoothing=0.1, desc="INFO    : Uploading Albums from Folders", unit=" folders") as pbar:
            for subpath in valid_folders:
                pbar.update(1)
                new_album_assets_ids = []
                if not os.path.isdir(subpath):
                    LOGGER.warning(f"WARNING : Could not create album for subfolder '{subpath}'.")
                    albums_skipped += 1
                    continue
                relative_path = os.path.relpath(subpath, input_folder)
                path_parts = relative_path.split(os.sep)
                # Create album_name
                if len(path_parts) == 1:
                    album_name = path_parts[0]
                else:
                    album_name = " - ".join(path_parts[1:]) if path_parts[0] in first_level_folders else " - ".join(path_parts)
                if album_name != '':
                    album_id = create_album(album_name, log_level=logging.WARNING)
                    if not album_id:
                        LOGGER.warning(f"WARNING : Could not create album for subfolder '{subpath}'.")
                        albums_skipped += 1
                        continue
                    else:
                        albums_uploaded += 1
                    for file in os.listdir(subpath):
                        file_path = os.path.join(subpath, file)
                        if not os.path.isfile(file_path):
                            continue
                        ext = os.path.splitext(file)[-1].lower()
                        if ext not in ALLOWED_SYNOLOGY_EXTENSIONS:
                            continue
                        asset_id = upload_asset(file_path, log_level=logging.WARNING)
                        assets_uploaded += 1
                        # Assign to Album only if extension is in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS
                        if ext in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS:
                            new_album_assets_ids.append(asset_id)
                if new_album_assets_ids:
                    add_assets_to_album(album_id, new_album_assets_ids, album_name=album_name, log_level=logging.WARNING)

        LOGGER.info(f"INFO    : Skipped {albums_skipped} album(s) from '{input_folder}'.")
        LOGGER.info(f"INFO    : Uploaded {albums_uploaded} album(s) from '{input_folder}'.")
        LOGGER.info(f"INFO    : Uploaded {assets_uploaded} asset(s) from '{input_folder}' to Albums.")
        return albums_uploaded, albums_skipped, assets_uploaded

# Function synology_upload_no_albums()
def synology_upload_no_albums(input_folder, subfolders_exclusion='Albums', subfolders_inclusion=None, log_level=logging.INFO):
    """
    Recursively traverses 'input_folder' and its subfolders_inclusion to upload all
    compatible files (photos/videos) to Synology without associating them to any album.

    If 'subfolders_inclusion' is provided (as a string or list of strings), only those
    direct subfolders_inclusion of 'input_folder' are processed (excluding any in SUBFOLDERS_EXCLUSIONS).
    Otherwise, all subfolders_inclusion except those listed in SUBFOLDERS_EXCLUSIONS are processed.

    Returns the number of files uploaded.
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        # Verify that the input folder exists
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            return 0

        # Process subfolders_exclusion to obtain a list of subfolders_exclusion names (if provided)
        if isinstance(subfolders_exclusion, str):
            subfolders_exclusion = [name.strip() for name in subfolders_exclusion.replace(',', ' ').split() if name.strip()]
        elif isinstance(subfolders_exclusion, list):
            subfolders_exclusion = [name.strip() for item in subfolders_exclusion if isinstance(item, str) for name in item.split(',') if name.strip()]
        else:
            subfolders_exclusion = None

        # Process subfolders_inclusion to obtain a list of subfolders_inclusion names (if provided)
        if isinstance(subfolders_inclusion, str):
            subfolders_inclusion = [name.strip() for name in subfolders_inclusion.replace(',', ' ').split() if name.strip()]
        elif isinstance(subfolders_inclusion, list):
            subfolders_inclusion = [name.strip() for item in subfolders_inclusion if isinstance(item, str) for name in item.split(',') if name.strip()]
        else:
            subfolders_inclusion = None

        # List of Subfolders to exclude
        SUBFOLDERS_EXCLUSIONS = ['@eaDir']
        for subfolder in subfolders_exclusion:
            SUBFOLDERS_EXCLUSIONS.append(subfolder)

        # Exclude any SUBFOLDERS_EXCLUSIONS that match exclusions
        if subfolders_inclusion:
            subfolders_inclusion = [s for s in subfolders_inclusion if s not in SUBFOLDERS_EXCLUSIONS]

        # Collect all file paths based on subfolder criteria
        def collect_files(input_folder, only_subfolders):
            files_list = []
            if only_subfolders:
                # Process only the specified direct subfolders_inclusion (if they exist)
                for sub in only_subfolders:
                    sub_path = os.path.join(input_folder, sub)
                    if not os.path.isdir(sub_path):
                        LOGGER.warning(f"WARNING : Subfolder '{sub}' does not exist in '{input_folder}'. Skipping.")
                        continue
                    for root, dirs, files in os.walk(sub_path):
                        # Exclude any directories matching the exclusions
                        dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                        files_list.extend(os.path.join(root, f) for f in files)
            else:
                # Process all subfolders_inclusion except those in SUBFOLDERS_EXCLUSIONS (filtering at all levels)
                for root, dirs, files in os.walk(input_folder):
                    dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                    files_list.extend(os.path.join(root, f) for f in files)
            return files_list

        # Collect all file paths to be processed
        file_paths = collect_files(input_folder, subfolders_inclusion)
        total_files = len(file_paths)
        total_assets_uploaded = 0

        # Process each file with a progress bar
        with tqdm(total=total_files, smoothing=0.1, desc="INFO    : Uploading Assets", unit=" asset") as pbar:
            for file_path in file_paths:
                if upload_asset(file_path, log_level=logging.WARNING):
                    total_assets_uploaded += 1
                pbar.update(1)
        LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")
        return total_assets_uploaded


# -----------------------------------------------------------------------------
#          COMPLETE UPLOAD OF ALL ASSETS (Albums + No-Albums)
# -----------------------------------------------------------------------------
def synology_upload_ALL(input_folder, albums_folders=None, log_level=logging.INFO):
    """
    Uploads ALL photos and videos from input_folder into Synology Photos:

    Returns the total number of albums and assets uploaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        total_assets_uploaded_within_albums = 0
        total_albums_uploaded = 0
        total_albums_skipped = 0

        if albums_folders:
            LOGGER.info("")
            LOGGER.info(f"INFO    : Uploading Assets and creating Albums into synology Photos from '{albums_folders}' subfolders...")
            total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums = synology_upload_albums(input_folder=input_folder, subfolders_inclusion=albums_folders, log_level=logging.WARNING)
            LOGGER.info("")
            LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")
            total_assets_uploaded_without_albums = synology_upload_no_albums(input_folder=input_folder, subfolders_exclusion=albums_folders, log_level=logging.WARNING)
        else:
            LOGGER.info("")
            LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}'...")
            total_assets_uploaded_without_albums = synology_upload_no_albums(input_folder=input_folder, log_level=logging.WARNING)

        total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums
        return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums


# Function to download albums from Synology Photos
def synology_download_albums(albums_name='ALL', output_folder='Downloads_Synology', log_level=logging.INFO):
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
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
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
                logout_synology(log_level=log_level)
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
                logout_synology(log_level=log_level)
                return albums_downloaded, assets_downloaded
            LOGGER.info(f"INFO    : {len(albums_to_download)} albums from Synology Photos will be downloaded to '{download_folder}' within Synology Photos root folder...")

        albums_downloaded = len(albums_to_download)
        # Iterate over each album to copy
        for album in tqdm(albums_to_download, desc="INFO    : Downloading Albums", unit=" albums"):
            album_name = album['name']
            album_id = album['id']
            # LOGGER.info(f"INFO    : Processing album: '{album_name}' (ID: {album_id})")
            # List assets in the album
            assets = get_assets_from_album(album_name, album_id)
            # LOGGER.info(f"INFO    : Number of assets in the album '{album_name}': {len(assets)}")
            if not assets:
                LOGGER.warning(f"WARNING : No assets to download in the album '{album_name}'.")
                continue
            # Create or obtain the destination folder for the album within output_folder/Albums
            target_folder_name = f'{album_name}'
            target_folder_id = create_folder(folder_name=target_folder_name, parent_folder_id=main_subfolder_id, log_level=logging.WARNING)
            if not target_folder_id:
                LOGGER.warning(f"WARNING : Failed to obtain or create the destination folder for the album '{album_name}'.")
                continue
            # Download the assets to the destination folder
            assets_downloaded += download_assets(folder_id=target_folder_id, folder_name=target_folder_name, assets_list=assets, log_level=logging.WARNING)

        LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{os.path.join(SYNOLOGY_ROOT_PHOTOS_PATH, download_folder)}'")
        logout_synology(log_level=log_level)
        return albums_downloaded, assets_downloaded


# Function to download albums from Synology Photos
# TODO: CREAR LA FUNCIÓN synology_download_no_albums()
def synology_download_no_albums(output_folder='Downloads_Synology', log_level=logging.INFO):
    """
    Downloads assets no associated to any albums from Synology Photos to a specified folder.

    Args:
        output_folder (str): The output folder where download the assets.

    Returns:
        downloaded_assets
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        output_folder = os.path.join(output_folder,"Albums")
        os.makedirs(output_folder, exist_ok=True)
        # Variables to return
        assets_downloaded = 0
        # Create or obtain the main folder 'Albums_Synology_Photos'
        main_folder = output_folder
        main_folder_id = create_folder(folder_name=main_folder, log_level=logging.WARNING)
        logout_synology(log_level=log_level)
        if not main_folder_id:
            LOGGER.error(f"ERROR   : Failed to obtain or create the main folder '{main_folder}'.")
        return  assets_downloaded


# Function synology_download_ALL()
def synology_download_ALL(output_folder="Downloads_Synology", log_level=logging.INFO):
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        # Call the functions
        synology_download_albums(albums_name='ALL', output_folder=output_folder, log_level=logging.WARNING)
        synology_download_no_albums(output_folder=output_folder, log_level=logging.WARNING)
        logout_synology(log_level=log_level)

# Function to delete empty albums in Synology Photos
def synology_remove_empty_albums(log_level=logging.INFO):
    """
    Deletes all empty albums in Synology Photos.

    Returns:
        int: The number of empty albums deleted.
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        # List albums and identify empty ones
        albums_dict = get_albums()
        albums_deleted = 0
        if albums_dict != -1:
            LOGGER.info("INFO    : Looking for empty albums in Synology Photos...")
            for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc="INFO    : Removing Empty Albums", unit=" albums"):
                item_count = get_album_items_count(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                if item_count == 0:
                    LOGGER.info(f"INFO    : Deleting empty album: '{album_name}' (ID: {album_id})")
                    delete_album(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                    albums_deleted += 1
        LOGGER.info("INFO    : Deleting empty albums process finished!")
        logout_synology(log_level=log_level)
        return albums_deleted

# Function to delete duplicate albums in Synology Photos
def synology_remove_duplicates_albums(log_level=logging.INFO):
    """
    Deletes all duplicate albums in Synology Photos.

    Returns:
        int: The number of duplicate albums deleted.
    """

    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)

        # List albums and identify duplicates
        albums_dict = get_albums()
        albums_deleted = 0
        albums_data = {}
        if albums_dict != -1:
            LOGGER.info("INFO    : Looking for duplicate albums in Synology Photos...")
            for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc="INFO    : Removing Duplicates Albums", unit=" albums"):
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
                delete_album(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                albums_deleted += 1
        LOGGER.info("INFO    : Deleting duplicate albums process finished!")
        logout_synology(log_level=log_level)
        return albums_deleted


# -----------------------------------------------------------------------------
#          DELETE ALL ASSETS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_assets(log_level=logging.INFO):
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        all_assets = get_all_assets()
        total_assets_found = len(all_assets)
        if total_assets_found == 0:
            LOGGER.warning(f"WARNING : No Assets found in Synology Database.")
        LOGGER.info(f"INFO    : Found {total_assets_found} asset(s) to delete.")
        assets_ids = []
        for asset in tqdm(all_assets, desc="INFO    : Deleting assets", unit=" assets"):
            asset_id = asset.get("id")
            if not asset_id:
                continue
            assets_ids.append(asset_id)

        assets_removed = 0
        albums_removed = 0
        if assets_ids:
            assets_removed = remove_assets(assets_ids, log_level=logging.WARNING)
            albums_removed = synology_remove_empty_albums(log_level=logging.WARNING)
            folders_removed = remove_empty_folders(log_level==logging.WARNING)
        logout_synology(log_level=logging.WARNING)
        LOGGER.info(f"INFO    : Total Assets removed : {assets_removed}")
        LOGGER.info(f"INFO    : Total Albums removed : {albums_removed}")
        LOGGER.info(f"INFO    : Total Folders removed: {folders_removed}")
        return assets_removed, albums_removed


# -----------------------------------------------------------------------------
#          DELETE ALL ALL ALBUMS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_albums(deleteAlbumsAssets=False, log_level=logging.INFO):
    """
    Deletes all albums and optionally also its associated assets.
    Returns the number of albums deleted and the number of assets deleted.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session if not yet started
        login_synology(log_level=log_level)
        albums = get_albums()
        if not albums:
            LOGGER.info("INFO    : No albums found.")
            logout_synology(log_level=log_level)
            return 0, 0
        total_deleted_albums = 0
        total_deleted_assets = 0
        for album in tqdm(albums, desc=f"INFO    : Searching for Albums to delete", unit=" albums"):
            album_id = album.get("id")
            album_name = album.get("albumName")
            album_assets_ids = []
            # if deleteAlbumsAssets is True, we have to delete also the assets associated to the album, album_id
            if deleteAlbumsAssets:
                album_assets = get_assets_from_album(album_id)
                for asset in album_assets:
                    album_assets_ids.append(asset.get("id"))
                remove_assets(album_assets_ids)
                total_deleted_assets += len(album_assets_ids)

            # Now we can delete the album
            if delete_album(album_id, album_name, log_level=logging.WARNING):
                # LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) deleted.")
                total_deleted_albums += 1

        LOGGER.info(f"INFO    : Deleted {total_deleted_albums} albums.")
        if deleteAlbumsAssets:
            LOGGER.info(f"INFO    : Deleted {total_deleted_assets} assets associated to albums.")
        logout_synology(log_level=log_level)
        return total_deleted_albums, total_deleted_assets


##############################################################################
#                           END OF MAIN FUNCTIONS                            #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    import Utils
    Utils.change_workingdir()

    # Create initialize LOGGER.
    from GlobalVariables import set_ARGS_PARSER
    set_ARGS_PARSER()

    # Read configuration and log in
    read_synology_config('Config.ini')
    login_synology(use_syno_token=True)
    # login_synology(use_syno_token=False)

    # # Example: synology_delete_empty_albums()
    # print("=== EXAMPLE: synology_delete_empty_albums() ===")
    # deleted = synology_delete_empty_albums()
    # print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # # Example: synology_delete_duplicates_albums()
    # print("=== EXAMPLE: synology_delete_duplicates_albums() ===")
    # duplicates = synology_delete_duplicates_albums()
    # print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # # Example: Upload_asset()
    # print("\n=== EXAMPLE: upload_asset() ===")
    # file_path = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums\2003.07 - Viaje a Almeria (Julio 2003)\En Almeria (Julio 2003)_17.JPG"                # For Windows
    # file_path = r"g:\My Drive\Google Drive\_PERSONAL\DOCUMENTS\MIS PÁGINAS WEBS\jtg.webservices.com\logo\30-01-2023_17-53-05.png"                # For Windows
    # asset_id = upload_asset(file_path)
    # if not asset_id:
    #     print(f"Error uploading asset '{file_path}'.")
    # else:
    #     print(f"New Asset uploaded successfully with id: {asset_id}")

    # # Example: synology_upload_no_albums()
    # print("\n=== EXAMPLE: synology_upload_no_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # synology_upload_no_albums(input_folder)

    # # Example: synology_upload_albums()
    # print("\n=== EXAMPLE: synology_upload_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # synology_upload_albums(input_folder)

    # # Example: synology_upload_ALL()
    # print("\n=== EXAMPLE: synology_upload_ALL() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # synology_upload_ALL(input_folder)

    # # Example: synology_download_albums
    # # TODO: Completar esta función
    # print("\n=== EXAMPLE: synology_download_albums() ===")
    # # total = synology_download_albums('ALL', output_folder="Downloads_Synology")
    # total = synology_download_albums(albums_name='Cadiz', output_folder="Downloads_Synology")
    # print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # # Example: synology_download_ALL
    # # TODO: Completar esta función
    # print("=== EXAMPLE: synology_download_ALL() ===")
    # total_struct = synology_download_ALL(output_folder="Downloads_Synology")
    # # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # # Test: get_photos_root_folder_id()
    # print("=== EXAMPLE: get_photos_root_folder_id() ===")
    # root_folder_id = get_photos_root_folder_id()
    # print (root_folder_id)

    # Example: remove_empty_folders_recursive()
    # TODO: Completar esta función
    print("\n=== EXAMPLE: remove_empty_folders_recursive() ===")
    total = remove_empty_folders()
    print(f"[RESULT] A total of {total} folders have been removed.\n")

    # logout_synology()
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