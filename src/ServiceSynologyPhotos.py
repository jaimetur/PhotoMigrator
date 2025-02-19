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
import fnmatch
from tqdm import tqdm
from datetime import datetime
import requests
import urllib3
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder
import time
import logging
from CustomLogger import set_log_level
from Utils import update_metadata, convert_to_list, get_unique_items, organize_files_by_date

# -----------------------------------------------------------------------------
#                          GLOBAL VARIABLES
# -----------------------------------------------------------------------------
global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD
global SESSION, SID

# Initialize global variables
CONFIG = None
SESSION = None
SID = None
SYNO_TOKEN_HEADER = {}
ALLOWED_SYNOLOGY_SIDECAR_EXTENSIONS = []
ALLOWED_SYNOLOGY_PHOTO_EXTENSIONS   = ['.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.3fr', '.arw', '.cr2', '.cr3', '.crw', '.dcr', '.dng', '.erf', '.k25', '.kdc', '.mef', '.mos', '.mrw', '.nef', '.orf', '.ptx', '.pef', '.raf', '.raw', '.rw2', '.sr2', '.srf', '.TIFF', '.HEIC']
ALLOWED_SYNOLOGY_VIDEO_EXTENSIONS   = ['.3G2', '.3GP', '.ASF', '.AVI', '.DivX', '.FLV', '.M4V', '.MOV', '.MP4', '.MPEG', '.MPG', '.MTS', '.M2TS', '.M2T', '.QT', '.WMV', '.XviD']
ALLOWED_SYNOLOGY_PHOTO_EXTENSIONS   = [ext.lower() for ext in ALLOWED_SYNOLOGY_PHOTO_EXTENSIONS]
ALLOWED_SYNOLOGY_VIDEO_EXTENSIONS   = [ext.lower() for ext in ALLOWED_SYNOLOGY_VIDEO_EXTENSIONS]
ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS   = ALLOWED_SYNOLOGY_PHOTO_EXTENSIONS + ALLOWED_SYNOLOGY_VIDEO_EXTENSIONS
ALLOWED_SYNOLOGY_EXTENSIONS         = ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS

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
        config_file (str): The path to the configuration file. Default is 'Config.ini'.
        log_level (logging,level): log_level for function messages.

    Returns:
        dict: The loaded configuration dictionary.
    """
    global CONFIG, SYNOLOGY_URL, SYNOLOGY_USERNAME, SYNOLOGY_PASSWORD
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
        LOGGER.info("")
        LOGGER.info(f"INFO    : Synology Config Read:")
        LOGGER.info(f"INFO    : ---------------------")
        masked_password = '*' * len(SYNOLOGY_PASSWORD)
        LOGGER.info(f"INFO    : SYNOLOGY_URL              : {SYNOLOGY_URL}")
        LOGGER.info(f"INFO    : SYNOLOGY_USERNAME         : {SYNOLOGY_USERNAME}")
        LOGGER.info(f"INFO    : SYNOLOGY_PASSWORD         : {masked_password}")
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
        # login into Synology Photos if the session is not yet started
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
        log_level (logging,level): log_level for function messages.

    Returns:
        int: The ID of the folder (folder_id), or None if not found.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
        log_level (logging,level): log_level for function messages.

    Returns:
        str: The folder ID if found or successfully created, otherwise None.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        offset = 0
        limit = 5000
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
        log_level (logging,level): log_level for function messages.

    Returns:
        list: Number of removed folders.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
import logging


# -----------------------------------------------------------------------------
#                          ALBUMS FUNCTIONS
# -----------------------------------------------------------------------------
def remove_album(album_id, album_name, log_level=logging.INFO):
    """
    Deletes an album in Synology Photos.

    Args:
        album_id (str): ID of the album to delete.
        album_name (str): Name of the album to delete.
        log_level (logging,level): log_level for function messages.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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


def create_album(album_name, log_level=logging.INFO):
    # Create the album if the folder contains supported files
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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


def get_albums(log_level=logging.INFO):
    """
    Lists all albums in Synology Photos.

    Returns:
        dict: A dictionary with album IDs as keys and album names as values.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        offset = 0
        limit = 5000
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
        # login into Synology Photos if the session is not yet started
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


def get_album_items_size(album_id, album_name, log_level=logging.INFO):
    """
    Gets the total size of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.
        log_level (logging,level): log_level for function messages.

    Returns:
        int: Total size of the items in the album in bytes.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
        for sets in album_items:
            for item in sets:
                album_size += item.get("filesize")
        return album_size


def get_album_items_count(album_id, album_name, log_level=logging.INFO):
    """
    Gets the number of items in an album.

    Args:
        album_id (str): ID of the album.
        album_name (str): Name of the album.
        log_level (logging,level): log_level for function messages.

    Returns:
        int: Number of items in the album.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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


# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS) FUNCTIONS
# -----------------------------------------------------------------------------
def get_folder_items_count(folder_id, folder_name, log_level=logging.INFO):
    """
    Return the assets count for a specific Synology Photos folder

    Args:
        folder_id (str): Name of the album.
        folder_name (str): ID of the album.
        log_level (logging,level): log_level for function messages.

    Returns:
        asset_count: the assets count for a specific Synology Photos folder
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        params = {
            'api': 'SYNO.Foto.Browse.Item',
            'method': 'count',
            'version': '4',
            "folder_id": folder_id,
        }
        try:
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR   : Failed to count assets for folder '{folder_name}'.")
                return -1
            asset_count = data["data"]["count"]
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while retrieving assets count for folder '{folder_name}'.", e)
            return -1
        return asset_count


def get_all_assets(log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        log_level (logging,level): log_level for function messages

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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


def get_assets_from_album(album_id, album_name, log_level=logging.INFO):
    """
    Lists photos in a specific album.

    Args:
        album_name (str): Name of the album.
        album_id (str): ID of the album.
        log_level (logging,level): log_level for function messages.

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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

def get_all_asset_from_all_albums(log_level=logging.WARNING):
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        all_assets = []
        all_albums = get_albums(log_level=log_level)
        for album_id, album_name in all_albums.items():
            album_assets = get_assets_from_album(album_id=album_id, album_name=album_name)
            all_assets.extend(album_assets)
        return all_assets

def add_assets_to_album(album_id, asset_ids, album_name, log_level=logging.WARNING):
    """
    Adds photos from a folder to an album.

    Args:
        album_id (str): The ID of the folder containing the assets.
        asset_ids (str, list): The IDs to add to the Album.
        album_name (str): The name of the album to create or add assets to.
        log_level (logging,level): log_level for function messages.

    Returns:
        int: The total number of assets added to the album, or -1 in case of an error.
    """
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
        asset_ids (list, str): ID of the assets to remove.
        log_level (logging,level): log_level for function messages

    Returns:
        list: A list of photos in the album.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
                LOGGER.error(f"ERROR   : Failed to remove assets")
                return 0
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while removing assets", e)
            return 0
        task_id = data.get('data').get('task_info').get('id')
        # Check if delete BackgroundTask has finished
        remove_status = check_background_remove_task_finished(task_id, log_level=log_level)
        waiting_time = 5
        while not remove_status == 'done' or remove_status == True:
            LOGGER.debug(f"DEBUG   : Waiting {waiting_time} seconds to check again if remove_assets() has finished.")
            time.sleep(waiting_time)
            remove_status = check_background_remove_task_finished(task_id, log_level=log_level)
        LOGGER.info(f'INFO    : Waiting for removing assets to finish...')
        time.sleep(waiting_time)
        return len(asset_ids)

def check_background_remove_task_finished(task_id, log_level=logging.INFO):
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Define the url for the request
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        params = {
            'api': 'SYNO.Foto.BackgroundTask.Info',
            'version': '1',
            'method': 'get_status',
            'id': f'[{task_id}]'
        }
        try:
            response = SESSION.get(url, params=params, headers=headers, verify=False)
            data = response.json()
            if not data.get("success"):
                LOGGER.error(f"ERROR   : Failed to get removing assets status")
                status = False
            else:
                if len(data['data']['list']) >0:
                    status = data["data"]["list"][0]['status']
                else:
                    status = True
        except Exception as e:
            LOGGER.error(f"ERROR   : Exception while checking removing assets status", e)
            status = False
        return status

def upload_asset(file_path, log_level=logging.INFO):
    """Upload an Asset to Synology Photos."""
    from GlobalVariables import LOGGER  # Import the logger inside the function
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
                LOGGER.warning(f"")
                LOGGER.warning(f"WARNING : File '{file_path}' has an unsupported extension. Skipped.")
                LOGGER.warning(f"")
                return None
        # Define the headers and add SYNO_TOKEN to it if session was initiated with SYNO_TOKEN
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        # URL for Synology Photos with api, method and version within the URL (needed when data is sent as MultipartEncoder object).
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


def download_asset(asset_id, asset_name, asset_time, destination_folder, log_level=logging.INFO):
    """
    Downloads an asset from Synology Photos and saves it to a local folder with the given timestamp.

    Args:
        asset_id (int): ID of the asset to download.
        asset_name (str): Name of the file to save.
        asset_time (int): Timestamp of the asset in UNIX Epoch format or 0 for current time.
        destination_folder (str): Path to the folder where the file will be saved.
        log_level (int, optional): Logging level. Default is logging.INFO.

    Returns:
        str: Path of the downloaded file if successful, None if it fails.
    """
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Temporarily change log level
        login_synology(log_level=log_level)  # Log in if necessary
        # Ensure the destination folder exists
        os.makedirs(destination_folder, exist_ok=True)
        # If asset_time is str, convert to UNIX timestamp
        if isinstance(asset_time, str):
            asset_time = datetime.fromisoformat(asset_time).timestamp()
        # Convert UNIX timestamp to datetime
        if asset_time > 0:
            asset_datetime = datetime.fromtimestamp(asset_time)
        else:
            asset_datetime = datetime.now()
        # Format timestamp for filename (YYYYMMDD_HHMMSS)
        timestamp_str = asset_datetime.strftime("%Y%m%d_%H%M%S")
        # Get file extension
        file_ext = os.path.splitext(asset_name)[1].lower()
        # new_asset_name = f"{timestamp_str}_{asset_name}" # Use this if you want to append the original asset name to the downloaded filename
        new_asset_name = f"{timestamp_str}"
        # Define the file path to save
        file_path = os.path.join(destination_folder, new_asset_name)
        # Define the request URL
        url = f"{SYNOLOGY_URL}/webapi/entry.cgi"
        # Define headers and add SYNO_TOKEN if required
        headers = {}
        if SYNO_TOKEN_HEADER:
            headers.update(SYNO_TOKEN_HEADER)
        try:
            params = {
                'api': 'SYNO.Foto.Download',
                'version': '2',
                'method': 'download',
                'force_download': 'true',
                'download_type': 'source',
                "item_id": f"[{asset_id}]",
            }
            response = SESSION.get(url, params=params, headers=headers, verify=False, stream=True)
            # Check if the download was successful
            if response.status_code != 200:
                LOGGER.error("")
                LOGGER.error(f"ERROR   : Failed to download asset '{asset_name}' with ID [{asset_id}]. Status code: {response.status_code}")
                return 0
            # Save the file content to the destination folder
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            # Update file timestamps using UNIX timestamp
            os.utime(file_path, (asset_time, asset_time))
            # Check if file extension is in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS
            if file_ext in ALLOWED_SYNOLOGY_MEDIA_EXTENSIONS:
                update_metadata(file_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"))
            LOGGER.debug("")
            LOGGER.debug(f"DEBUG   : Asset '{new_asset_name}' downloaded and saved at {file_path}")
            return 1
        except Exception as e:
            LOGGER.error("")
            LOGGER.error(f"ERROR   : Exception occurred while downloading asset '{asset_name}' with ID [{asset_id}]. {e}")
            return 0


##############################################################################
#                           END OF AUX FUNCTIONS                             #
##############################################################################


##############################################################################
#           MAIN FUNCTIONS TO CALL FROM OTHER MODULES                        #
##############################################################################
# Function to upload albums to Synology Photos
def synology_upload_albums(input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=[], log_level=logging.WARNING):
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
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            return 0
        # Process subfolders_exclusion and subfolders_inclusion to convert into list
        subfolders_exclusion = convert_to_list(subfolders_exclusion)
        subfolders_inclusion = convert_to_list(subfolders_inclusion)
        # Initialize output variables
        albums_uploaded = 0
        albums_skipped = 0
        assets_uploaded = 0
        # If 'Albums' is not part of the albums_folders, add it.
        albums_folder_included = False
        for subfolder in subfolders_inclusion:
            subfolder_real_path = os.path.realpath(os.path.join(input_folder,subfolder))
            relative_path = os.path.relpath(subfolder_real_path, input_folder)
            if relative_path.lower() == 'albums':
                albums_folder_included = True
                break
        if not albums_folder_included:
            subfolders_inclusion.append('Albums')
        # Directories to exclude
        SUBFOLDERS_EXCLUSIONS = ['@eaDir']
        for subfolder in subfolders_exclusion:
            SUBFOLDERS_EXCLUSIONS.append(subfolder)
        # Search for all valid Albums folders
        valid_folders = []  # List to store valid folder paths
        for root, folders, _ in os.walk(input_folder):
            folders[:] = [d for d in folders if d not in SUBFOLDERS_EXCLUSIONS]  # Exclude directories in the exclusion list
            if subfolders_inclusion:  # Apply SUBFOLDERS_INCLUSION filter if provided
                rel_path = os.path.relpath(root, input_folder)
                if rel_path == ".":
                    folders[:] = [d for d in folders if d in subfolders_inclusion]
                else:
                    first_dir = rel_path.split(os.sep)[0]
                    if first_dir not in subfolders_inclusion:
                        folders[:] = []
            for folder in folders:
                dir_path = os.path.join(root, folder)
                if isinstance(dir_path, bytes):
                    dir_path = dir_path.decode()  # Convertir bytes a str
                # Check if there is at least one file with an allowed extension in the subfolder
                has_supported_files = any(os.path.splitext(file)[-1].lower() in ALLOWED_SYNOLOGY_EXTENSIONS for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file)))
                if not has_supported_files:
                    continue
                valid_folders.append(dir_path)
        first_level_folders = os.listdir(input_folder)
        if subfolders_inclusion:
            first_level_folders = first_level_folders + subfolders_inclusion
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
def synology_upload_no_albums(input_folder, subfolders_exclusion='Albums', subfolders_inclusion=[], log_level=logging.WARNING):
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
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Verify that the input folder exists
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            return 0
        # Process subfolders_exclusion and subfolders_inclusion to convert into list
        subfolders_exclusion = convert_to_list(subfolders_exclusion)
        subfolders_inclusion = convert_to_list(subfolders_inclusion)
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
                    if isinstance(input_folder, bytes):
                        input_folder = input_folder.decode()
                    if isinstance(sub, bytes):
                        sub = sub.decode()
                    sub_path = os.path.join(str(input_folder), str(sub))
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
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Convert input_folder to realpath
        input_folder = os.path.realpath(input_folder)
        # Process albums_folders to convert into list
        albums_folders = convert_to_list(albums_folders)
        # If 'Albums' is not part of the albums_folders, add it.
        albums_folder_included = False
        for subfolder in albums_folders:
            subfolder_real_path = os.path.realpath(os.path.join(input_folder,subfolder))
            relative_path = os.path.relpath(subfolder_real_path, input_folder)
            if relative_path.lower() == 'albums':
                albums_folder_included = True
        if not albums_folder_included:
            albums_folders.append('Albums')
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets and creating Albums into synology Photos from '{albums_folders}' subfolders...")
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums = synology_upload_albums(input_folder=input_folder, subfolders_inclusion=albums_folders, log_level=logging.WARNING)
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")
        total_assets_uploaded_without_albums = synology_upload_no_albums(input_folder=input_folder, subfolders_exclusion=albums_folders, log_level=logging.WARNING)
        total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums
        return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums


# Function to download albums from Synology Photos
def synology_download_albums(albums_name='ALL', output_folder='Downloads_Synology', log_level=logging.WARNING):
    """
    Downloads albums from Synology Photos to a specified folder, supporting wildcard patterns.

    Args:
        albums_name (str or list): The name(s) of the album(s) to download. Use 'ALL' to download all albums.
        output_folder (str): The output folder where download the album_assets.
        log_level (logging,level): log_level for function messages.

    Returns:
        tuple: albums_downloaded, assets_downloaded
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Variables to return
        albums_downloaded = 0
        assets_downloaded = 0
        # Create download_folder for Albums
        output_folder = os.path.join(output_folder, 'Albums')
        os.makedirs(output_folder, exist_ok=True)
        # Normalize album_name_or_id to a list if it's a string
        if isinstance(albums_name, str):
            albums_name = [albums_name]
        # List own and shared albums
        all_albums = get_albums_own_and_shared()
        # Determine the albums to copy
        if 'ALL' in [x.strip().upper() for x in albums_name]:
            albums_to_download = all_albums
            LOGGER.info(f"INFO    : ALL albums ({len(all_albums)}) will be downloaded...")
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
            LOGGER.info(f"INFO    : {len(albums_to_download)} albums from Synology Photos will be downloaded to '{output_folder}' within Synology Photos root folder...")
        albums_downloaded = len(albums_to_download)
        # Iterate over each album to copy
        for album in tqdm(albums_to_download, desc="INFO    : Downloading Albums", unit=" albums"):
            album_name = album['name']
            album_id = album['id']
            LOGGER.info(f"INFO    : Processing album: '{album_name}' (ID: {album_id})")
            # List album_assets in the album
            album_assets = get_assets_from_album(album_id, album_name)
            LOGGER.info(f"INFO    : Number of album_assets in the album '{album_name}': {len(album_assets)}")
            if not album_assets:
                LOGGER.warning(f"WARNING : No album_assets to download in the album '{album_name}'.")
                continue
            # Create or obtain the destination folder for the album within output_folder/Albums
            album_folder_name = f'{album_name}'
            album_folder_path = os.path.join(output_folder, album_folder_name)
            for asset in album_assets:
                asset_id = asset.get('id')
                asset_name = asset.get('filename')
                asset_time = asset.get('time')
                assets_downloaded += download_asset(asset_id=asset_id, asset_name=asset_name, asset_time=asset_time, destination_folder=album_folder_path, log_level=logging.INFO)
        LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{output_folder}'")
        logout_synology(log_level=log_level)
        return albums_downloaded, assets_downloaded


# Function to download Assets without Albums from Synology Photos
def synology_download_no_albums(output_folder='Downloads_Synology', log_level=logging.WARNING):
    """
    Downloads assets no associated to any albums from Synology Photos to a specified folder, supporting wildcard patterns.

    Args:
        output_folder (str): The output folder where download the all_assets.
        log_level (logging,level): log_level for function messages.

    Returns:
        tuple: assets_downloaded
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # Variables to return
        assets_downloaded = 0
        # Create download_folder for Albums
        output_folder = os.path.join(output_folder, 'No-Albums')
        os.makedirs(output_folder, exist_ok=True)
        all_assets = get_all_assets(log_level=logging.INFO)
        album_asset = get_all_asset_from_all_albums(log_level=logging.INFO)
        assets_without_albums = get_unique_items(all_assets, album_asset, key='filename')
        LOGGER.info(f"INFO    : Number of all_assets without Albums associated to download: {len(all_assets)}")
        if not all_assets:
            LOGGER.warning(f"WARNING : No all_assets without Albums associated to download.")
            return 0, 0
        for asset in assets_without_albums:
            asset_id = asset.get('id')
            asset_name = asset.get('filename')
            asset_time = asset.get('time')
            assets_downloaded += download_asset(asset_id=asset_id, asset_name=asset_name, asset_time=asset_time, destination_folder=output_folder, log_level=logging.INFO)
        organize_files_by_date(input_folder=output_folder, type='year/month')
        LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{output_folder}'")
        logout_synology(log_level=log_level)
        return assets_downloaded


# Function synology_download_ALL()
def synology_download_ALL(output_folder="Downloads_Immich", show_info_messages=False, log_level=logging.WARNING):
    """
    Downloads ALL photos and videos from Synology Photos into output_folder creating a Folder Structure like this:
        output_folder/
          ├─ Albums/
          │    ├─ albumName1/ (assets in the album)
          │    ├─ albumName2/ (assets in the album)
          │    ...
          └─ No-Albums/
               └─ yyyy/
                   └─ mm/ (assets not in any album for that year/month)

    Returns the total number of albums and assets downloaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        login_synology(log_level=log_level)
        total_albums_downloaded, total_assets_downloaded_within_albums = synology_download_albums(albums_name='ALL', output_folder=output_folder, log_level=logging.WARNING)
        total_assets_downloaded_without_albums = synology_download_no_albums(output_folder=output_folder, log_level=logging.WARNING)
        total_assets_downloaded = total_assets_downloaded_within_albums + total_assets_downloaded_without_albums
        if show_info_messages:
            LOGGER.info(f"INFO    : Download of ALL assets completed.")
            LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
            LOGGER.info(f"Total Assets downloaded                   : {total_assets_downloaded}")
            LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_downloaded_within_albums}")
            LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_downloaded_without_albums}")
        return total_albums_downloaded, total_assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums

# Function to delete empty folders in Synology Photos
def synology_remove_empty_folders(log_level=logging.INFO):
    """
    Recursively removes all empty folders and subfolders in Synology Photos,
    considering folders empty even if they only contain a hidden '@eaDir' folder.

    Returns:
        int: The number of empty folders removed.
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Cambia el nivel de registro
        # Iniciar sesión en Synology Photos si no hay una sesión activa
        login_synology(log_level=log_level)
        def remove_empty_folders_recursive(folder_id, folder_name):
            """Recorre y elimina las carpetas vacías de manera recursiva."""
            with set_log_level(LOGGER, log_level):  # Cambia el nivel de registro
                folders_dict = get_folders(folder_id, log_level=log_level)
                removed_count = 0
                for subfolder_id, subfolder_name in folders_dict.items():
                    # Recursive call to process subfolders first
                    LOGGER.debug(f"DEBUG    : Looking for empty subfolders in '{folder_name}'")
                    removed_count += remove_empty_folders_recursive(subfolder_id, subfolder_name)
                # Verificar nuevamente el contenido de la carpeta
                folders_dict = get_folders(folder_id, log_level=log_level)
                # Obtain number of folders and number of assets
                folders_count = len(folders_dict)
                assets_count = get_folder_items_count(folder_id=folder_id, folder_name=folder_name, log_level=log_level)
                # Comprobar si la única carpeta existente es '@eaDir'
                only_eaDir_present = (len(folders_dict) == 1 and "@eaDir" in folders_dict.values())
                is_truly_empty = (folders_count == 0 and assets_count == 0)
                if (is_truly_empty or only_eaDir_present) and folder_name != '/':
                    LOGGER.debug("")
                    LOGGER.debug(f"DEBUG    : Removing empty folder: '{folder_name}' (ID: {folder_id}) within Synology Photos")
                    remove_folder(folder_id=folder_id, folder_name=folder_name, log_level=log_level)
                    removed_count += 1
                else:
                    LOGGER.debug(f"DEBUG   : The folder '{folder_name}' cannot be removed because is not empty.")
                return removed_count
        LOGGER.info("INFO    : Starting empty folder removal from Synology Photos...")
        # Obtener el ID de la carpeta raíz
        root_folder_id = get_photos_root_folder_id(log_level=log_level)
        total_removed = remove_empty_folders_recursive(folder_id=root_folder_id, folder_name='/')
        LOGGER.info(f"INFO    : Process Remove empty folders from Synology Photos finished. Total removed folders: {total_removed}")
        logout_synology(log_level=log_level)
        return total_removed


# Function to delete empty albums in Synology Photos
def synology_remove_empty_albums(log_level=logging.WARNING):
    """
    Deletes all empty albums in Synology Photos.

    Returns:
        int: The number of empty albums deleted.
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        # List albums and identify empty ones
        albums_dict = get_albums()
        albums_removed = 0
        if albums_dict != -1:
            LOGGER.info("INFO    : Looking for empty albums in Synology Photos...")
            for album_id, album_name in tqdm(albums_dict.items(), smoothing=0.1, desc="INFO    : Removing Empty Albums", unit=" albums"):
                item_count = get_album_items_count(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                if item_count == 0:
                    LOGGER.info(f"INFO    : Removing empty album: '{album_name}' (ID: {album_id})")
                    remove_album(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                    albums_removed += 1
        LOGGER.info("INFO    : Removing empty albums process finished!")
        logout_synology(log_level=log_level)
        return albums_removed

# Function to delete duplicate albums in Synology Photos
def synology_remove_duplicates_albums(log_level=logging.WARNING):
    """
    Deletes all duplicate albums in Synology Photos.

    Returns:
        int: The number of duplicate albums deleted.
    """
    # Import logger and log in to the NAS
    from GlobalVariables import LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
                LOGGER.debug(f'DEBUG:   : Item Count: {item_count}. Item Size: {item_size}. ')
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
                remove_album(album_id=album_id, album_name=album_name, log_level=logging.WARNING)
                albums_deleted += 1
        LOGGER.info("INFO    : Deleting duplicate albums process finished!")
        logout_synology(log_level=log_level)
        return albums_deleted


# -----------------------------------------------------------------------------
#          DELETE ALL ASSETS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_assets(log_level=logging.WARNING):
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
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
        if assets_ids:
            assets_removed = remove_assets(assets_ids, log_level=logging.WARNING)
        albums_removed  = synology_remove_empty_albums (log_level=logging.WARNING)
        folders_removed = synology_remove_empty_folders(log_level=logging.WARNING)
        LOGGER.info(f"INFO    : Total Assets removed : {assets_removed}")
        LOGGER.info(f"INFO    : Total Albums removed : {albums_removed}")
        LOGGER.info(f"INFO    : Total Folders removed: {folders_removed}")
        logout_synology(log_level=logging.WARNING)
        return assets_removed, albums_removed, folders_removed


# -----------------------------------------------------------------------------
#          DELETE ALL ALL ALBUMS FROM SYNOLOGY DATABASE
# -----------------------------------------------------------------------------
def synology_remove_all_albums(removeAlbumsAssets=False, log_level=logging.WARNING):
    """
    Removes all albums and optionally also its associated assets.
    Returns the number of albums deleted and the number of assets deleted.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login into Synology Photos if the session is not yet started
        login_synology(log_level=log_level)
        albums = get_albums()
        if not albums:
            LOGGER.info("INFO    : No albums found.")
            logout_synology(log_level=log_level)
            return 0, 0
        total_assets_removed = 0
        total_albums_removed = 0
        for album in tqdm(albums, desc=f"INFO    : Searching for Albums to remove", unit=" albums"):
            album_id = album.get("id")
            album_name = album.get("albumName")
            album_assets_ids = []
            # if deleteAlbumsAssets is True, we have to delete also the assets associated to the album, album_id
            if removeAlbumsAssets:
                album_assets = get_assets_from_album(album_id, album_name)
                for asset in album_assets:
                    album_assets_ids.append(asset.get("id"))
                remove_assets(album_assets_ids)
                total_assets_removed += len(album_assets_ids)
            # Now we can delete the album
            if remove_album(album_id, album_name, log_level=logging.WARNING):
                # LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) deleted.")
                total_albums_removed += 1
        total_folders_removed = synology_remove_empty_folders(log_level == logging.WARNING)
        LOGGER.info(f"INFO    : Removed {total_assets_removed} assets associated to albums.")
        LOGGER.info(f"INFO    : Removed {total_albums_removed} albums.")
        LOGGER.info(f"INFO    : Removed {total_folders_removed} empty folders.")
        logout_synology(log_level=log_level)
        return total_assets_removed, total_albums_removed, total_folders_removed


##############################################################################
#                           END OF MAIN FUNCTIONS                            #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    from Utils import change_workingdir
    change_workingdir()

    # Create initialize LOGGER.
    from GlobalVariables import set_ARGS_PARSER
    set_ARGS_PARSER()

    # Read configuration and log in
    read_synology_config('../Config.ini')
    login_synology(use_syno_token=True)
    # login_synology(use_syno_token=False)

    # Example: synology_remove_empty_albums()
    print("=== EXAMPLE: synology_remove_empty_albums() ===")
    deleted = synology_remove_empty_albums()
    print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # Example: synology_remove_duplicates_albums()
    print("=== EXAMPLE: synology_remove_duplicates_albums() ===")
    duplicates = synology_remove_duplicates_albums()
    print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # Example: Upload_asset()
    print("\n=== EXAMPLE: upload_asset() ===")
    file_path = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums\1994 - Recuerdos\169859_10150125237566327_578986326_8330690_6545.jpg"                # For Windows
    asset_id = upload_asset(file_path)
    if not asset_id:
        print(f"Error uploading asset '{file_path}'.")
    else:
        print(f"New Asset uploaded successfully with id: {asset_id}")

    # Example: synology_upload_no_albums()
    print("\n=== EXAMPLE: synology_upload_no_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    synology_upload_no_albums(input_folder)

    # Example: synology_upload_albums()
    print("\n=== EXAMPLE: synology_upload_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    synology_upload_albums(input_folder)

    # Example: synology_upload_ALL()
    print("\n=== EXAMPLE: synology_upload_ALL() ===")
    # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    synology_upload_ALL(input_folder)

    # Example: synology_download_albums()
    print("\n=== EXAMPLE: synology_download_albums() ===")
    download_folder = r"r:\jaimetur\CloudPhotoMigrator\Download_folder_for_testing"
    total = synology_download_albums(albums_name='ALL', output_folder=download_folder)
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # Example: synology_download_no_albums()
    print("\n=== EXAMPLE: synology_download_albums() ===")
    download_folder = r"r:\jaimetur\CloudPhotoMigrator\Download_folder_for_testing"
    total = synology_download_no_albums(output_folder=download_folder)
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # Example: synology_download_ALL
    print("=== EXAMPLE: synology_download_ALL() ===")
    total_struct = synology_download_ALL(output_folder="Downloads_Synology")
    # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # Test: get_photos_root_folder_id()
    print("=== EXAMPLE: get_photos_root_folder_id() ===")
    root_folder_id = get_photos_root_folder_id()
    print (root_folder_id)

    # Example: synology_remove_empty_folders()
    print("\n=== EXAMPLE: synology_remove_empty_folders() ===")
    total = synology_remove_empty_folders()
    print(f"[RESULT] A total of {total} folders have been removed.\n")

    # logout_synology()
    logout_synology()

