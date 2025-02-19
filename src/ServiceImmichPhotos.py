# -*- coding: utf-8 -*-

"""
ServiceImmichPhotos.py
---------------
Python module with example functions to interact with Immich Photos, including followfing functions:
  - Configuration (read config)
  - Authentication (login/logout)
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Deleting empty or duplicate albums
  - Main functions for use in other modules:
     - immich_delete_empty_albums()
     - immich_delete_duplicates_albums()
     - immich_upload_folder()
     - immich_upload_albums()
     - immich_download_albums()
     - immich_download_ALL()
"""
import os
import requests
import json
import urllib3
import fnmatch
from tqdm import tqdm
from datetime import datetime
from dateutil import parser
from urllib.parse import urlparse
from halo import Halo
from tabulate import tabulate
from pathlib import Path
import logging
from CustomLogger import set_log_level
from Utils import update_metadata, convert_to_list

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------------------------------------------------------
#                          GLOBAL VARIABLES
# -----------------------------------------------------------------------------
CONFIG                              = None  # Dictionary containing configuration information
IMMICH_URL                          = None  # e.g., "http://192.168.1.100:2283"
IMMICH_ADMIN_API_KEY                = None  # Immich IMMICH_ADMIN_API_KEY
IMMICH_USER_API_KEY                 = None  # Immich IMMICH_USER_API_KEY
IMMICH_USERNAME                     = None  # Immich user (email)
IMMICH_PASSWORD                     = None  # Immich password
SESSION_TOKEN                       = None  # JWT token returned after login
API_KEY_LOGIN                       = False # Variable to determine if we use IMMICH_USER_API_KEY for login
HEADERS_WITH_CREDENTIALS            = {}    # Headers used in each request
ALLOWED_IMMICH_MEDIA_EXTENSIONS     = []    # Allowed Immich Media Extensions
ALLOWED_IMMICH_SIDECAR_EXTENSIONS   = []    # Allowed Immich Sidecar Extensions
ALLOWED_IMMICH_EXTENSIONS           = []    # Allowed Immich Extensions


##############################################################################
#                            AUXILIARY FUNCTIONS                             #
##############################################################################
# -----------------------------------------------------------------------------
#                          CONFIGURATION READING
# -----------------------------------------------------------------------------
def read_immich_config(config_file='Config.ini', log_level=logging.INFO):
    """
    Reads configuration (IMMICH_URL, IMMICH_USERNAME, IMMICH_PASSWORD) from a .config file,
    for example:

        IMMICH_URL = http://192.168.1.100:2283
        IMMICH_USER_API_KEY    = YOUR_API_KEY
        IMMICH_USERNAME   = user@example.com
        IMMICH_PASSWORD   = 1234

    If the file is not found, the data will be requested from the user interactively.
    """
    global CONFIG, IMMICH_URL, IMMICH_ADMIN_API_KEY, IMMICH_USER_API_KEY, IMMICH_USERNAME, IMMICH_PASSWORD, API_KEY_LOGIN, IMMICH_FILTER_ARCHIVE, IMMICH_FILTER_FROM, IMMICH_FILTER_TO, IMMICH_FILTER_COUNTRY, IMMICH_FILTER_CITY, IMMICH_FILTER_PERSON
    from GlobalVariables import LOGGER  # Import global LOGGER
    from ConfigReader import load_config
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if CONFIG:
            return CONFIG  # Configuration already read previously
        # Load CONFIG from config_file
        CONFIG = {}
        CONFIG = load_config(config_file)
        # Extract specific values for Synology from CONFIG.
        IMMICH_URL              = CONFIG.get('IMMICH_URL', None)
        IMMICH_ADMIN_API_KEY    = CONFIG.get('IMMICH_ADMIN_API_KEY', None)
        IMMICH_USER_API_KEY     = CONFIG.get('IMMICH_USER_API_KEY', None)
        IMMICH_USERNAME         = CONFIG.get('IMMICH_USERNAME', None)
        IMMICH_PASSWORD         = CONFIG.get('IMMICH_PASSWORD', None)
        IMMICH_FILTER_ARCHIVE   = CONFIG.get('IMMICH_FILTER_ARCHIVE', None)
        IMMICH_FILTER_FROM      = CONFIG.get('IMMICH_FILTER_FROM', None)
        IMMICH_FILTER_TO        = CONFIG.get('IMMICH_FILTER_TO', None)
        IMMICH_FILTER_COUNTRY   = CONFIG.get('IMMICH_FILTER_COUNTRY', None)
        IMMICH_FILTER_CITY      = CONFIG.get('IMMICH_FILTER_CITY', None)
        IMMICH_FILTER_PERSON    = CONFIG.get('IMMICH_FILTER_PERSON', None)
        # Verify required parameters and prompt on screen if missing
        if not IMMICH_URL or IMMICH_URL.strip()=='':
            LOGGER.warning(f"WARNING : IMMICH_URL not found. It will be requested on screen.")
            CONFIG['IMMICH_URL'] = input("[PROMPT] Enter IMMICH_URL (e.g., http://192.168.1.100:2283): ")
            IMMICH_URL = CONFIG['IMMICH_URL']
        if not IMMICH_USER_API_KEY or IMMICH_USER_API_KEY.strip()=='':
            if not IMMICH_USERNAME or IMMICH_USERNAME.strip()=='':
                LOGGER.warning(f"WARNING : IMMICH_USERNAME not found. It will be requested on screen.")
                CONFIG['IMMICH_USERNAME'] = input("[PROMPT] Enter IMMICH_USERNAME (Immich email): ")
                IMMICH_USERNAME = CONFIG['IMMICH_USERNAME']
            if not IMMICH_PASSWORD or IMMICH_PASSWORD.strip()=='':
                LOGGER.warning(f"WARNING : IMMICH_PASSWORD not found. It will be requested on screen.")
                CONFIG['IMMICH_PASSWORD'] = input("[PROMPT] Enter IMMICH_PASSWORD: ")
                IMMICH_PASSWORD = CONFIG['IMMICH_PASSWORD']
        else:
            API_KEY_LOGIN = True
            LOGGER.info("")
            LOGGER.info(f"INFO    : Immich Config Read:")
            LOGGER.info(f"INFO    : -------------------")
            LOGGER.info(f"INFO    : IMMICH_URL            : {IMMICH_URL}")
            if API_KEY_LOGIN:
                masked_admin_api = '*' * len(IMMICH_ADMIN_API_KEY)
                masked_user_api = '*' * len(IMMICH_USER_API_KEY)
                LOGGER.info(f"INFO    : IMMICH_ADMIN_API_KEY  : {masked_admin_api}")
                LOGGER.info(f"INFO    : IMMICH_USER_API_KEY   : {masked_user_api}")
            else:
                LOGGER.info(f"INFO    : IMMICH_USERNAME       : {IMMICH_USERNAME}")
                masked_password = '*' * len(IMMICH_PASSWORD)
                LOGGER.info(f"INFO    : IMMICH_PASSWORD       : {masked_password}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_ARCHIVE : {IMMICH_FILTER_ARCHIVE}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_FROM    : {IMMICH_FILTER_FROM}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_TO      : {IMMICH_FILTER_TO}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_COUNTRY : {IMMICH_FILTER_COUNTRY}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_CITY    : {IMMICH_FILTER_CITY}")
            LOGGER.info(f"INFO    : IMMICH_FILTER_PERSON  : {IMMICH_FILTER_PERSON}")
        return CONFIG


# -----------------------------------------------------------------------------
#                          AUTHENTICATION / LOGOUT
# -----------------------------------------------------------------------------
def login_immich(log_level=logging.INFO):
    """
    Logs into Immich and obtains a JWT token (SESSION_TOKEN).
    Returns True if the connection was successful, False otherwise.
    """
    global SESSION_TOKEN, HEADERS_WITH_CREDENTIALS, ALLOWED_IMMICH_MEDIA_EXTENSIONS, ALLOWED_IMMICH_SIDECAR_EXTENSIONS, ALLOWED_IMMICH_EXTENSIONS
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # If there is already a token and headers, assume we are logged in
        if len(HEADERS_WITH_CREDENTIALS.keys())>0 and  (f"Bearer {SESSION_TOKEN}" or IMMICH_USER_API_KEY in HEADERS_WITH_CREDENTIALS.values()):
            return True
        # Ensure the configuration is read
        read_immich_config(log_level=log_level)
        LOGGER.info("")
        LOGGER.info(f"INFO    : Authenticating on Immich Photos and getting Session...")
        # If detected IMMICH_USER_API_KEY in Immich.config
        if API_KEY_LOGIN:
            HEADERS_WITH_CREDENTIALS = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'x-api-key': IMMICH_USER_API_KEY
            }
            LOGGER.info(f"INFO    : Authentication Successfully with IMMICH_USER_API_KEY found in Config file.")
        # If not detected IMMICH_USER_API_KEY in Immich.config
        else:
            url = f"{IMMICH_URL}/api/auth/login"
            payload = json.dumps({
              "email": IMMICH_USERNAME,
              "password": IMMICH_PASSWORD
            })
            headers = {
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            }
            try:
                response = requests.post(url, headers=headers, data=payload)
                response.raise_for_status()  # Raises exception if 4xx or 5xx
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception occurred during Immich login: {str(e)}")
                return False
            data = response.json()
            SESSION_TOKEN = data.get("accessToken", None)
            if not SESSION_TOKEN:
                LOGGER.error(f"ERROR   : 'accessToken' not found in the response: {data}")
                return False
            HEADERS_WITH_CREDENTIALS = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {SESSION_TOKEN}'
            }
            LOGGER.info(f"INFO    : Authentication Successfully with user/password found in Config file.")

        # get List of “compatible” media and sidecar extensions for Immich
        ALLOWED_IMMICH_MEDIA_EXTENSIONS = get_supported_media_types(log_level=logging.WARNING)
        ALLOWED_IMMICH_SIDECAR_EXTENSIONS = get_supported_media_types(type='sidecar', log_level=logging.WARNING)
        ALLOWED_IMMICH_EXTENSIONS = ALLOWED_IMMICH_MEDIA_EXTENSIONS + ALLOWED_IMMICH_SIDECAR_EXTENSIONS
        return True

def logout_immich(log_level=logging.INFO):
    """
    "Logs out" locally by discarding the token.
    (Currently, Immich does not provide an official /logout endpoint).
    """
    global SESSION_TOKEN, HEADERS_WITH_CREDENTIALS
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        SESSION_TOKEN = None
        HEADERS_WITH_CREDENTIALS = {}
        LOGGER.info("INFO    : Session closed locally (Bearer Token discarded).")

# -----------------------------------------------------------------------------
#                          ALBUMS FUNCTIONS
# -----------------------------------------------------------------------------
def create_album(album_name, log_level=logging.INFO):
    """
    Creates an album in Immich with the name 'album_name'.
    Returns the ID of the created album or None if it fails.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/albums"
        payload = json.dumps({
            "albumName": album_name,
        })
        try:
            response = requests.post(url, headers=HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
            response.raise_for_status()
            data = response.json()
            album_id = data.get("id")
            # LOGGER.info(f"INFO    : Album '{album_name}' created with ID={album_id}.")
            return album_id
        except Exception:
            LOGGER.warning(f"WARNING : Cannot create album '{album_name}' due to API call error. Skipped!")
            return None

def delete_album(album_id, album_name, log_level=logging.INFO):
    """
    Deletes an album from Immich by its ID. Returns True if deleted successfully, False otherwise.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/albums/{album_id}"
        try:
            response = requests.delete(url, headers=HEADERS_WITH_CREDENTIALS, verify=False)
            if response.status_code == 200:
                # LOGGER.info(f"INFO    : Album '{album_name}' with ID={album_id} deleted.")
                return True
            else:
                LOGGER.warning(f"WARNING : Failed to delete album: '{album_name}' with ID: {album_id}. Status: {response.status_code}")
                return False
        except Exception as e:
            LOGGER.error(f"ERROR   : Error while deleting album '{album_name}' with ID:  {album_id}: {e}")
            return False

def get_albums(log_level=logging.INFO):
    """
    Returns the list of albums for the current user in Immich.
    Each item is a dictionary with at least:
        {
          "id": <str>,
          "albumName": <str>,
          "ownerId": <str>,
          "assets": [ ... ],
          ...
        }
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/albums"
        try:
            response = requests.get(url, headers=HEADERS_WITH_CREDENTIALS, verify=False)
            response.raise_for_status()
            albums_data = response.json()  # A list
            return albums_data
        except Exception as e:
            LOGGER.error(f"ERROR   : Error while listing albums: {e}")
            return None

def get_album_items_size(album_id, log_level=logging.INFO):
    """
    Calculates the total size of all assets in an album by summing up exifInfo.fileSizeInByte (if available).
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        try:
            assets = get_assets_from_album(album_id)
            total_size = 0
            for asset in assets:
                exif_info = asset.get("exifInfo", {})
                if "fileSizeInByte" in exif_info:
                    total_size += exif_info["fileSizeInByte"]
            return total_size
        except:
            return 0

# -----------------------------------------------------------------------------
#                          ASSETS (FOTOS/VIDEOS) FUNCTIONS
# -----------------------------------------------------------------------------
def get_duplicates_assets(log_level=logging.INFO):
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/duplicates"
        payload = {}
        response = requests.request("GET", url, headers=HEADERS_WITH_CREDENTIALS, data=payload)
        response.raise_for_status()
        duplicates_assets = response.json()  # List
        return duplicates_assets

def get_all_assets_by_search_filter(type=None, isNotInAlbum=None, isArchived=None, createdAfter=None, createdBefore=None, country=None, city=None, personIds=None, log_level=logging.INFO):
    """
    Returns the list of assets that belong to a specific album (ID).
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/search/metadata"
        payload_data = {
            # "libraryId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "order": "desc",
            # "country": "string",
            # "city": "string",
            # "type": "IMAGE",
            # "isNotInAlbum": False,
            # "isArchived": True,
            # "isEncoded": True,
            # "isFavorite": True,
            # "isMotion": True,
            # "isOffline": True,
            # "isVisible": True,
            # "withArchived": False,
            # "withDeleted": True,
            # "withExif": True,
            # "withPeople": True,
            # "withStacked": True,
            # "createdAfter": "string",
            # "createdBefore": "string",
            # "takenAfter": "string",
            # "takenBefore": "string",
            # "updatedAfter": "string",
            # "updatedBefore": "string",
            # "personIds": [
            #   "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            # ],
        }
        # Agregar isNotInAlbum solo si no es None
        if type: payload_data["type"] = type
        if isNotInAlbum: payload_data["isNotInAlbum"] = isNotInAlbum
        if isArchived: payload_data["isArchived"] = isArchived
        if createdAfter: payload_data["createdAfter"] = createdAfter
        if createdBefore: payload_data["createdBefore"] = createdBefore
        if country: payload_data["country"] = country
        if city: payload_data["city"] = city
        if personIds: payload_data["personIds"] = personIds
        # Convert payload_data dict to JSON
        payload = json.dumps(payload_data, indent=2)
        try:
            response = requests.post(url, headers=HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
            response.raise_for_status()
            data = response.json()  # List
            assets = data.get("assets")
            return assets
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to retrieve assets: {str(e)}")
            return []

def get_assets_from_album(album_id, log_level=logging.INFO):
    """
    Returns the list of assets that belong to a specific album (ID).
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/albums/{album_id}"
        try:
            response = requests.get(url, headers=HEADERS_WITH_CREDENTIALS, verify=False)
            response.raise_for_status()
            data = response.json()  # List
            assets = data.get("assets")
            return assets
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to retrieve assets from album ID={album_id}: {str(e)}")
            return []


def add_assets_to_album(album_id, asset_ids, album_name=None, log_level=logging.INFO):
    """
    Adds the list of asset_ids (photos/videos already uploaded) to the album with album_id.
    Returns the number of assets successfully added.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        if not asset_ids:
            return 0
        url = f"{IMMICH_URL}/api/albums/{album_id}/assets"
        payload = json.dumps({
                  "ids": asset_ids
                })
        try:
            response = requests.put(url, headers=HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
            response.raise_for_status()
            data = response.json()
            total_added = 0
            for item in data:
                if item.get("success"):
                    total_added += 1
            return total_added
        except Exception as e:
            if album_name:
                LOGGER.warning(f"WARNING : Error while adding assets to album '{album_name}' with ID={album_id}: {e}")
            else:
                LOGGER.warning(f"WARNING : Error while adding assets to album with ID={album_id}: {e}")
            return 0

def remove_assets(assets_ids, log_level=logging.INFO):
    """
    Delete the list of assets provide by assets_ids.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/assets"
        payload = json.dumps({
          "force": True,
          "ids": assets_ids
        })
        try:
            response = requests.request("DELETE", url, headers=HEADERS_WITH_CREDENTIALS, data=payload)
            response.raise_for_status()
            if response.ok:
                deleted_assets = len(assets_ids)
                return deleted_assets
            else:
                LOGGER.error(f"ERROR   : Failed to delete assets due to API error")
                return 0
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to delete assets: {str(e)}")
            return 0

def remove_duplicates_assets(log_level=logging.INFO):
    """
    Remove Duplicates Asset in Immich Database
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        # Check for duplicates assets and remove them if exists.
        # TODO: Check if the duplicate duplicates_set contains some metadata and assign them to the duplicates_set to keep.
        duplicates_assets = get_duplicates_assets(log_level=log_level)
        duplicates_ids = []
        for duplicates_set in duplicates_assets:
            duplicates_assets_in_set = duplicates_set.get('assets')
            for duplicate_asset_in_set in duplicates_assets_in_set[1:]:
                duplicate_id = duplicate_asset_in_set.get('id')
                duplicates_ids.append(duplicate_id)
        LOGGER.info(f"INFO    : Removing Duplicates Assets...")
        duplicates_assets_removed = remove_assets(duplicates_ids)
        return duplicates_assets_removed

def upload_asset(file_path, log_level=logging.INFO):
    """
    Uploads a local file (photo or video) to Immich using /api/duplicates_set/upload-file.
    Returns the 'id' of the created duplicates_set, or None if the upload fails.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        if not os.path.isfile(file_path):
            LOGGER.error(f"ERROR   : File not found: {file_path}")
            return None
        # Check if the file extension is allowed
        filename, ext = os.path.splitext(file_path)
        if ext.lower() not in ALLOWED_IMMICH_MEDIA_EXTENSIONS:
            if ext.lower() in ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
                return None
            else:
                LOGGER.warning(f"WARNING : File '{file_path}' has an unsupported extension. Skipped.")
                return None
        # This API requires special headers without 'Content-Type': 'application/json'
        if API_KEY_LOGIN:
            header = {
                'Accept': 'application/json',
                'x-api-key': IMMICH_USER_API_KEY
            }
        else:
            header = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {SESSION_TOKEN}'
            }
        url = f"{IMMICH_URL}/api/assets"

        files = {
            'assetData': open(file_path, 'rb')
        }
        # Check if a sidecar file is found on the same path, if so, then add it to files dict.
        for sidecar_extension in ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
            # Check with file_path/filename.ext.sidecar_extension
            sidecar_path = f"{file_path}{sidecar_extension}"
            if os.path.isfile(sidecar_path):
                # LOGGER.info(f"INFO    : Uploaded Sidecar: '{os.path.basename(sidecar_path)}' for file: '{os.path.basename(file_path)}'")
                files['sidecarData'] = open(sidecar_path, 'rb')
                break
            # Check with file_path/filename.sidecar_extension
            sidecar_path = f"{file_path.replace(ext, sidecar_extension)}"
            if os.path.isfile(sidecar_path):
                # LOGGER.info(f"INFO    : Uploaded Sidecar: '{os.path.basename(sidecar_path)}' for file: '{os.path.basename(file_path)}'")
                files['sidecarData'] = open(sidecar_path, 'rb')
                break
        stats = os.stat(file_path)
        date_time_for_filename = datetime.fromtimestamp(stats.st_mtime).strftime("%Y%m%d_%H%M%S")
        date_time_for_attributes = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        data = {
            'deviceAssetId': f'{date_time_for_filename}_{os.path.basename(file_path)}',
            'deviceId': 'CloudPhotoMigrator',
            'fileCreatedAt': date_time_for_attributes,
            'fileModifiedAt': date_time_for_attributes,
            'fileSize': str(stats.st_size),
            'isFavorite': 'false',
            # You can add other optional fields if needed, such as:
            # "isArchived": "false",
            # "isVisible": "true",
            # ...
        }
        try:
            # On upload, 'Content-Type' is automatically generated with multipart
            response = requests.post(url, headers=header, data=data, files=files)
            response.raise_for_status()
            new_asset = response.json()
            asset_id = new_asset.get("id")
            if asset_id:
                LOGGER.debug(f"DEBUG   : Uploaded '{os.path.basename(file_path)}' with asset_id={asset_id}")
                pass
            return asset_id
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to upload '{file_path}': {e}")
            return None

def download_asset(asset_id, asset_filename, asset_time, download_folder="Downloaded_Immich", log_level=logging.INFO):
    """
    Downloads an asset (photo/video) from Immich and saves it to local disk.
    Uses GET /api/asset/:assetId/serve
    Returns True if the download was successful, False otherwise.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        # Ensure the destination folder exists
        os.makedirs(download_folder, exist_ok=True)
        # If asset_time is str, convert to UNIX timestamp
        if isinstance(asset_time, str):
            asset_time = parser.isoparse(asset_time).timestamp()
        # Convert UNIX timestamp to datetime
        if asset_time > 0:
            asset_datetime = datetime.fromtimestamp(asset_time)
        else:
            asset_datetime = datetime.now()
        # Get file extension
        file_ext = os.path.splitext(asset_filename)[1].lower()
        url = f"{IMMICH_URL}/api/assets/{asset_id}/original"
        try:
            with requests.get(url, headers=HEADERS_WITH_CREDENTIALS, verify=False, stream=True) as request:
                request.raise_for_status()
                # # Attempt to deduce filename from the header
                # content_disp = request.headers.get('Content-Disposition', '')
                # if 'filename=' in content_disp:
                #     # attachment; filename="name.jpg"
                #     asset_filename = content_disp.split("filename=")[-1].strip('"; ')
                file_path = os.path.join(download_folder, asset_filename)
                with open(file_path, 'wb') as f:
                    for chunk in request.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Update file timestamps using UNIX timestamp
                os.utime(file_path, (asset_time, asset_time))
                # Check if file extension is in ALLOWED_IMMICH_MEDIA_EXTENSIONS
                if file_ext in ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                    update_metadata(file_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"))
                LOGGER.debug("")
                LOGGER.debug(f"DEBUG   : Asset '{asset_filename}' downloaded and saved at {file_path}")
                return True
        except Exception as e:
            LOGGER.error(f"ERROR   : Failed to download asset {asset_id}: {e}")
            return False


# -----------------------------------------------------------------------------
#                          GENERAL FUNCTIONS
# -----------------------------------------------------------------------------
def get_user_id(log_level=logging.INFO):
    """
    Return the user_id for the logged user
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/users/me"
        payload = {}
        try:
            response = requests.request("GET", url, headers=HEADERS_WITH_CREDENTIALS, data=payload)
            response.raise_for_status()
            data = response.json()
            user_id = data.get("id")
            user_mail = data.get("email")
            LOGGER.info(f"INFO    : User ID: '{user_id}' found for user '{user_mail}'.")
            return user_id
        except Exception as e:
            LOGGER.error(f"ERROR   : Cannot find User ID for user '{user_mail}': {e}")
            return None


def get_supported_media_types(type='media', log_level=logging.INFO):
    """
    Return the user_id for the logged user
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        url = f"{IMMICH_URL}/api/server/media-types"
        payload = {}
        try:
            response = requests.request("GET", url, headers=HEADERS_WITH_CREDENTIALS, data=payload)
            response.raise_for_status()
            data = response.json()
            image = data.get("image")
            video = data.get("video")
            sidecar = data.get("sidecar")
            if type.lower() == 'media':
                supported_types = image + video
                LOGGER.info(f"INFO    : Supported media types: '{supported_types}'.")
            elif type.lower() == 'image':
                supported_types = image
                LOGGER.info(f"INFO    : Supported image types: '{supported_types}'.")
            elif type.lower() == 'video':
                supported_types = video
                LOGGER.info(f"INFO    : Supported video types: '{supported_types}'.")
            elif type.lower() == 'sidecar':
                supported_types = sidecar
                LOGGER.info(f"INFO    : Supported sidecar types: '{supported_types}'.")
            else:
                LOGGER.error(f"ERROR   : Invalid type '{type}' to get supported media types. Types allowed are 'media', 'image', 'video' or 'sidecar'")
                return None
            return supported_types
        except Exception as e:
            LOGGER.error(f"ERROR   : Cannot get Supported media types: {e}")
            return None


##############################################################################
#                           END OF AUX FUNCTIONS                             #
##############################################################################

##############################################################################
#           MAIN FUNCTIONS TO CALL FROM OTHER MODULES                        #
##############################################################################
def immich_upload_albums(input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
    """
    Traverses the subfolders of 'input_folder', creating an album for each valid subfolder (album name equals the subfolder name). Within each subfolder, it uploads all files with allowed extensions (based on ALLOWED_IMMICH_EXTENSIONS) and associates them with the album.
    Example structure:
        input_folder/
            ├─ Album1/   (files for album "Album1")
            └─ Album2/   (files for album "Album2")
    Returns: albums_uploaded, albums_skipped, assets_uploaded
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            # logout_immich
            logout_immich(log_level=log_level)
            return 0, 0, 0, 0
        # Process subfolders_exclusion and subfolders_inclusion to convert into list
        subfolders_exclusion = convert_to_list(subfolders_exclusion)
        subfolders_inclusion = convert_to_list(subfolders_inclusion)
        albums_uploaded = 0
        albums_skipped = 0
        assets_uploaded = 0
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
                # Check if there is at least one file with an allowed extension in the subfolder
                if isinstance(dir_path, bytes):
                    dir_path = dir_path.decode()  # Convertir bytes a str
                dir_path = Path(dir_path)  # Asegurarnos de que es un Path
                has_supported_files = any(os.path.splitext(file)[-1].lower() in ALLOWED_IMMICH_EXTENSIONS for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file)))
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
                    album_id = create_album(album_name)
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
                        if ext not in ALLOWED_IMMICH_EXTENSIONS:
                            continue
                        asset_id = upload_asset(file_path)
                        assets_uploaded += 1
                        # Assign to Album only if extension is in ALLOWED_IMMICH_MEDIA_EXTENSIONS
                        if ext in ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                            new_album_assets_ids.append(asset_id)
                    if new_album_assets_ids:
                        add_assets_to_album(album_id, new_album_assets_ids, album_name=album_name)
        # Finally remove duplicates_asset in Immich Database
        duplicates_assets_removed = 0
        if remove_duplicates:
            LOGGER.info("INFO    : Removing Duplicates Assets...")
            duplicates_assets_removed = remove_duplicates_assets(log_level=log_level)
        LOGGER.info(f"INFO    : Skipped {albums_skipped} album(s) from '{input_folder}'.")
        LOGGER.info(f"INFO    : Uploaded {albums_uploaded} album(s) from '{input_folder}'.")
        LOGGER.info(f"INFO    : Uploaded {assets_uploaded} asset(s) from '{input_folder}' to Albums.")
        LOGGER.info(f"INFO    : Removed {duplicates_assets_removed} duplicates asset(s) from Immich Database.")
        # logout_immich
        logout_immich(log_level=log_level)
        return albums_uploaded, albums_skipped, assets_uploaded, duplicates_assets_removed

def immich_upload_no_albums(input_folder, subfolders_exclusion='Albums', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
    """
    Recursively traverses 'input_folder' and its subfolders_inclusion to upload all
    compatible files (photos/videos) to Immich without associating them to any album.

    If 'subfolders_inclusion' is provided (as a string or list of strings), only those
    direct subfolders_inclusion of 'input_folder' are processed (excluding any in SUBFOLDERS_EXCLUSIONS).
    Otherwise, all subfolders_inclusion except those listed in SUBFOLDERS_EXCLUSIONS are processed.

    Returns the number of files uploaded.
    """
    from GlobalVariables import LOGGER  # Global logger
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        # Verify that the input folder exists
        if not os.path.isdir(input_folder):
            LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
            # logout_immich
            logout_immich(log_level=log_level)
            return 0, 0
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
        def collect_files(input_folders, only_subfolders):
            files_list = []
            if only_subfolders:
                # Process only the specified direct subfolders_inclusion (if they exist)
                for sub in only_subfolders:
                    sub_path = os.path.join(str(input_folders), sub)
                    if not os.path.isdir(sub_path):
                        LOGGER.warning(f"WARNING : Subfolder '{sub}' does not exist in '{input_folders}'. Skipping.")
                        continue
                    for root, dirs, files in os.walk(sub_path):
                        # Exclude any directories matching the exclusions
                        dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                        files_list.extend(os.path.join(root, f) for f in files)
            else:
                # Process all subfolders_inclusion except those in SUBFOLDERS_EXCLUSIONS (filtering at all levels)
                for root, dirs, files in os.walk(input_folders):
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
                if upload_asset(file_path):
                    total_assets_uploaded += 1
                pbar.update(1)
        # Finally remove duplicates_asset in Immich Database
        duplicates_assets_removed = 0
        if remove_duplicates:
            LOGGER.info("INFO    : Removing Duplicates Assets...")
            duplicates_assets_removed = remove_duplicates_assets(log_level=log_level)
        LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")
        LOGGER.info(f"INFO    : Removed {duplicates_assets_removed} duplicates asset(s) from Immich Database.")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_assets_uploaded, duplicates_assets_removed

# -----------------------------------------------------------------------------
#          COMPLETE UPLOAD OF ALL ASSETS (Albums + No-Albums)
# -----------------------------------------------------------------------------
def immich_upload_ALL(input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
    """
    Uploads ALL photos and videos from input_folder into Immich Photos:

    Returns the total number of albums and assets uploaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
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
        LOGGER.info(f"INFO    : Uploading Assets and creating Albums into immich Photos from '{albums_folders}' subfolders...")
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, duplicates_assets_removed_1 = immich_upload_albums(input_folder=input_folder, subfolders_inclusion=albums_folders, remove_duplicates=False, log_level=logging.WARNING)
        LOGGER.info("")
        LOGGER.info(f"INFO    : Uploading Assets without Albums creation into immich Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")
        total_assets_uploaded_without_albums, duplicates_assets_removed_2 = immich_upload_no_albums(input_folder=input_folder, subfolders_exclusion=albums_folders, remove_duplicates=False, log_level=logging.WARNING)
        total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums
        # Finally remove duplicates assets from Immich Database
        duplicates_assets_removed = 0
        if remove_duplicates:
            LOGGER.info("INFO    : Removing Duplicates Assets...")
            duplicates_assets_removed = remove_duplicates_assets(log_level=logging.WARNING)
        # logout_immich
        logout_immich(log_level=log_level)
        return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, duplicates_assets_removed


def immich_download_albums(albums_name='ALL', output_folder="Downloads_Immich", log_level=logging.WARNING):
    """
    Downloads (extracts) all photos/videos from one or multiple albums using name patterns:

      - If album_name_or_id == 'ALL', all albums will be downloaded.
      - If it matches an 'id' or 'albumName', only that album will be downloaded.
      - If it contains wildcard patterns (e.g., "*jaime*", "jaime*"), it will download matching albums.
      - If it is a list, it will check each item as an ID, exact name, or pattern.

    Returns the total number of albums and assets downloaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        output_folder = os.path.join(output_folder, "Albums")
        os.makedirs(output_folder, exist_ok=True)
        all_albums = get_albums()
        if not all_albums:
            LOGGER.warning("WARNING : No albums available or could not retrieve the list.")
            # logout_immich
            logout_immich(log_level=log_level)
            return 0, 0
        # Normalize album_name_or_id to a list if it's a string
        if isinstance(albums_name, str):
            albums_name = [albums_name]
        found_albums = []
        if 'ALL' in [x.strip().upper() for x in albums_name]:
            albums_to_download = all_albums
            LOGGER.info(f"INFO    : ALL albums ({len(all_albums)}) will be downloaded...")
        else:
            for album in all_albums:
                album_id = album.get("id")
                album_name = album.get("albumName", "")

                for pattern in albums_name:
                    if album_id == str(pattern):
                        found_albums.append(album)
                        break
                    if fnmatch.fnmatch(album_name.lower(), pattern.lower()):
                        found_albums.append(album)
                        break
            if found_albums:
                albums_to_download = found_albums
                LOGGER.info(f"INFO    : {len(found_albums)} album(s) matched pattern(s) '{albums_name}'.")
            else:
                LOGGER.warning(f"WARNING : No albums found matching pattern(s) '{albums_name}'.")
                # logout_immich
                logout_immich(log_level=log_level)
                return 0, 0
        total_assets_downloaded = 0
        total_albums_downloaded = 0
        total_albums = len(albums_to_download)
        for album in albums_to_download:
            album_id = album.get("id")
            album_name = album.get("albumName", f"album_{album_id}")
            album_folder = os.path.join(output_folder, f"{album_name}")
            os.makedirs(album_folder, exist_ok=True)
            assets_in_album = get_assets_from_album(album_id)
            for asset in tqdm(assets_in_album, desc=f"INFO    : Downloading '{album_name}'", unit=" assets"):
                asset_id = asset.get("id")
                asset_filename = os.path.basename(asset.get("originalPath"))
                if asset_id:
                    asset_time = asset.get('fileCreatedAt')
                    ok = download_asset(asset_id, asset_filename, asset_time, album_folder)
                    if ok:
                        total_assets_downloaded += 1
            total_albums_downloaded += 1
            LOGGER.info(f"INFO    : Downloaded Album [{total_albums_downloaded}/{total_albums}] - '{album_name}'. {len(assets_in_album)} asset(s) have been downloaded.")
        LOGGER.info(f"INFO    : Download of Albums completed.")
        LOGGER.info(f"INFO    : Total Albums downloaded: {total_albums_downloaded}")
        LOGGER.info(f"INFO    : Total Assets downloaded: {total_assets_downloaded}")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_albums_downloaded, total_assets_downloaded

def immich_download_no_albums(output_folder="Downloads_Immich", log_level=logging.WARNING):
    """
    (Previously extract_photos_from_album)
    Downloads (extracts) all photos/videos from one or multiple albums:

      - If album_name_or_id == 'ALL', all albums will be downloaded.
      - If it matches an 'id' or 'albumName', only that album will be downloaded.

    Returns the total number of assets downloaded.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        total_assets_downloaded = 0
        # 2) Assets without album -> output_folder/No-Albums/yyyy/mm
        all_assets = get_all_assets_by_search_filter(isNotInAlbum=True)
        # all_assets = get_assets_by_search_filter()
        all_assets_items = all_assets.get("items")
        all_photos_path = os.path.join(output_folder, 'No-Albums')
        os.makedirs(all_photos_path, exist_ok=True)
        LOGGER.info(f"INFO    : Found {len(all_assets_items)} asset(s) without any album associated.")
        for asset in tqdm(all_assets_items, desc="INFO    : Downloading assets without associated albums", unit=" photos"):
            asset_id = asset.get("id")
            asset_filename = os.path.basename(asset.get("originalPath"))
            if not asset_id:
                continue
            created_at_str = asset.get("fileCreatedAt", "")
            try:
                dt_created = datetime.fromisoformat(created_at_str.replace("Z", ""))
            except:
                dt_created = datetime.now()
            year_str = dt_created.strftime("%Y")
            month_str = dt_created.strftime("%m")
            target_folder = os.path.join(all_photos_path, year_str, month_str)
            os.makedirs(target_folder, exist_ok=True)
            asset_time = asset.get('fileCreatedAt')
            ok = download_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=target_folder)
            if ok:
                total_assets_downloaded += 1
        LOGGER.info(f"INFO    : Download of assets without associated albums completed.")
        LOGGER.info(f"INFO    : Total Assets downloaded: {total_assets_downloaded}")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_assets_downloaded


# -----------------------------------------------------------------------------
#          COMPLETE DOWNLOAD OF ALL ASSETS (Albums + No-Albums)
# -----------------------------------------------------------------------------
def immich_download_ALL(output_folder="Downloads_Immich", log_level=logging.WARNING):
    """
    Downloads ALL photos and videos from Immich Photos into output_folder creating a Folder Structure like this:
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
        # login_immich
        login_immich(log_level=log_level)
        total_albums_downloaded, total_assets_downloaded_within_albums = immich_download_albums(albums_name='ALL', output_folder=output_folder, log_level=logging.WARNING)
        total_assets_downloaded_without_albums = immich_download_no_albums(output_folder=output_folder, log_level=logging.WARNING)
        total_assets_downloaded = total_assets_downloaded_within_albums + total_assets_downloaded_without_albums
        LOGGER.info(f"INFO    : Download of ALL assets completed.")
        LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
        LOGGER.info(f"Total Assets downloaded                   : {total_assets_downloaded}")
        LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_downloaded_within_albums}")
        LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_downloaded_without_albums}")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_albums_downloaded, total_assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums


# -----------------------------------------------------------------------------
#          DELETE EMPTY ALBUMS FROM IMMICH DATABASE
# -----------------------------------------------------------------------------
def immich_remove_empty_albums(log_level=logging.WARNING):
    """
    Deletes all albums that have no assets (are empty).
    Returns the number of albums deleted.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        albums = get_albums()
        if not albums:
            LOGGER.info("INFO    : No albums found.")
            # logout_immich
            logout_immich(log_level=log_level)
            return 0
        total_deleted_empty_albums = 0
        for album in tqdm(albums, desc=f"INFO    : Searching for Empty Albums", unit=" albums"):
            album_id = album.get("id")
            album_name = album.get("albumName")
            assets_count = album.get("assetCount")
            if assets_count == 0:
                if delete_album(album_id, album_name):
                    # LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) deleted.")
                    total_deleted_empty_albums += 1
        LOGGER.info(f"INFO    : Deleted {total_deleted_empty_albums} empty albums.")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_deleted_empty_albums

# -----------------------------------------------------------------------------
#          DELETE DUPLICATES ALBUMS FROM IMMICH DATABASE
# -----------------------------------------------------------------------------
def immich_remove_duplicates_albums(log_level=logging.WARNING):
    """
    Deletes albums that have the same number of assets and the same total size.
    From each duplicate group, keeps the first one (smallest ID) and deletes the rest.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        albums = get_albums()
        if not albums:
            # logout_immich
            logout_immich(log_level=log_level)
            return 0
        duplicates_map = {}
        for album in tqdm(albums, desc=f"INFO    : Searching for Duplicates Albums", unit=" albums"):
            album_id = album.get("id")
            album_name = album.get("albumName")
            assets_count = album.get("assetCount")
            size = get_album_items_size(album_id)
            duplicates_map.setdefault((assets_count, size), []).append((album_id, album_name))
        total_deleted_duplicated_albums = 0
        for (item_assets_count, size), group in tqdm(duplicates_map.items(), desc=f"INFO    : Deleting Duplicates Albums", unit=" albums"):
            LOGGER.debug(f'DEBUG   : Assets Count: {item_assets_count}. Size: {size}.')
            if len(group) > 1:
                group_sorted = sorted(group, key=lambda x: x[1])
                # The first album in the group is kept
                to_delete = group_sorted[1:]
                for album_id, album_name in to_delete:
                    if delete_album(album_id, album_name):
                        total_deleted_duplicated_albums += 1
        LOGGER.info(f"INFO    : Deleted {total_deleted_duplicated_albums} duplicate albums.")
        # logout_immich
        logout_immich(log_level=log_level)
        return total_deleted_duplicated_albums

# -----------------------------------------------------------------------------
#          DELETE ORPHANS ASSETS FROM IMMICH DATABASE
# -----------------------------------------------------------------------------
def immich_remove_orphan_assets(user_confirmation=True, log_level=logging.WARNING):
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        def filter_entities(response_json, entity_type):
            return [
                {'pathValue': entity['pathValue'], 'entityId': entity['entityId'], 'entityType': entity['entityType']}
                for entity in response_json.get('orphans', []) if entity.get('entityType') == entity_type
            ]

        if not IMMICH_ADMIN_API_KEY or not IMMICH_USER_API_KEY:
            LOGGER.error(f"ERROR   : Both admin and user API keys are required.")
            # logout_immich
            logout_immich(log_level=log_level)
            return 0

        immich_parsed_url = urlparse(IMMICH_URL)
        base_url = f'{immich_parsed_url.scheme}://{immich_parsed_url.netloc}'
        api_url = f'{base_url}/api'
        file_report_url = api_url + '/reports'
        headers = {'x-api-key': IMMICH_ADMIN_API_KEY}

        print()
        spinner = Halo(text='Retrieving list of orphaned media assets...', spinner='dots')
        spinner.start()

        deleted_assets = 0
        try:
            response = requests.get(file_report_url, headers=headers)
            response.raise_for_status()
            spinner.succeed('Success!')
        except requests.exceptions.RequestException as e:
            spinner.fail(f'Failed to fetch assets: {str(e)}')
            # logout_immich
            logout_immich(log_level=log_level)
            return 0

        orphan_media_assets = filter_entities(response.json(), 'asset')
        num_entries = len(orphan_media_assets)

        if num_entries == 0:
            LOGGER.info(f"INFO    : No orphaned media assets found.")
            # logout_immich
            logout_immich(log_level=log_level)
            return deleted_assets

        if user_confirmation:
            table_data = [[asset['pathValue'], asset['entityId']] for asset in orphan_media_assets]
            LOGGER.info(f"INFO    : {tabulate(table_data, headers=['Path Value', 'Entity ID'], tablefmt='pretty')}")
            LOGGER.info("")

            summary = f'There {"is" if num_entries == 1 else "are"} {num_entries} orphaned media asset{"s" if num_entries != 1 else ""}. Would you like to delete {"them" if num_entries != 1 else "it"} from Immich? (yes/no): '
            user_input = input(summary).lower()
            LOGGER.info("")

            if user_input not in ('y', 'yes'):
                LOGGER.info(f"INFO    : Exiting without making any changes.")
                # logout_immich
                logout_immich(log_level=log_level)
                return 0

        headers['x-api-key'] = IMMICH_USER_API_KEY  # Use user API key for deletion
        with tqdm(total=num_entries, desc="INFO    : Deleting orphaned media assets", unit="asset") as progress_bar:
            for asset in orphan_media_assets:
                entity_id = asset['entityId']
                asset_url = f'{api_url}/assets'
                delete_payload = json.dumps({'force': True, 'ids': [entity_id]})
                headers = {'Content-Type': 'application/json', 'x-api-key': IMMICH_USER_API_KEY}
                try:
                    response = requests.delete(asset_url, headers=headers, data=delete_payload)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 400:
                        LOGGER.warning(f"WARNING : Failed to delete asset {entity_id} due to potential API key mismatch. Ensure you're using the asset owners API key as the User API key.")
                    else:
                        LOGGER.warning(f"WARNING : Failed to delete asset {entity_id}: {str(e)}")
                    continue
                progress_bar.update(1)
                deleted_assets += 1
        LOGGER.info(f"INFO    : Orphaned media assets deleted successfully!")
        # logout_immich
        logout_immich(log_level=log_level)
        return deleted_assets

# -----------------------------------------------------------------------------
#          DELETE ALL ASSETS FROM IMMICH DATABASE
# -----------------------------------------------------------------------------
def immich_remove_all_assets(log_level=logging.WARNING):
    from GlobalVariables import LOGGER  # Import global LOGGER
    # login_immich
    login_immich(log_level=log_level)
    all_assets = get_all_assets_by_search_filter()
    all_assets_items = all_assets.get("items")
    total_assets_found = len(all_assets_items)
    if total_assets_found == 0:
        LOGGER.warning(f"WARNING : No Assets found in Immich Database.")
    LOGGER.info(f"INFO    : Found {total_assets_found} asset(s) to delete.")
    assets_ids = []
    for asset in tqdm(all_assets_items, desc="INFO    : Deleting assets", unit=" assets"):
        asset_id = asset.get("id")
        if not asset_id:
            continue
        assets_ids.append(asset_id)

    assets_deleted = 0
    albums_deleted = 0
    if assets_ids:
        assets_deleted = remove_assets(assets_ids, log_level=logging.WARNING)
        albums_deleted = immich_remove_empty_albums(log_level=logging.WARNING)
    logout_immich()
    LOGGER.info(f"INFO    : Total Assets deleted: {assets_deleted}")
    LOGGER.info(f"INFO    : Total Albums deleted: {albums_deleted}")
    return assets_deleted, albums_deleted


# -----------------------------------------------------------------------------
#          DELETE ALL ALL ALBUMS FROM IMMICH DATABASE
# -----------------------------------------------------------------------------
def immich_remove_all_albums(deleteAlbumsAssets=False, log_level=logging.WARNING):
    """
    Deletes all albums and optionally also its associated assets.
    Returns the number of albums deleted and the number of assets deleted.
    """
    from GlobalVariables import LOGGER  # Import global LOGGER
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # login_immich
        login_immich(log_level=log_level)
        albums = get_albums()
        if not albums:
            LOGGER.info("INFO    : No albums found.")
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
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    import Utils
    Utils.change_workingdir()

    # Create initialize LOGGER.
    from GlobalVariables import set_ARGS_PARSER
    set_ARGS_PARSER()

    # # 0) Read configuration and log in
    # read_immich_config('Config.ini')
    # login_immich()

    # # 1) Example: Delete empty albums
    # print("\n=== EXAMPLE: immich_delete_empty_albums() ===")
    # deleted = immich_delete_empty_albums()
    # print(f"[RESULT] Empty albums deleted: {deleted}")

    # # 2) Example: Delete duplicate albums
    # print("\n=== EXAMPLE: immich_delete_duplicates_albums() ===")
    # duplicates = immich_delete_duplicates_albums()
    # print(f"[RESULT] Duplicate albums deleted: {duplicates}")

    # # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\No-Albums'
    # print("\n=== EXAMPLE: immich_upload_no_albums() ===")
    # big_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\No-Albums"
    # immich_upload_no_albums(big_folder)

    # # 4) Example: Create albums from subfolders in 'r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums'
    # print("\n=== EXAMPLE: immich_upload_albums() ===")
    # input_albums_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums"
    # immich_upload_albums(input_albums_folder)

    # # # 5) Example: Download all photos from ALL albums
    # print("\n=== EXAMPLE: immich_download_albums() ===")
    # # total = immich_download_albums('ALL', output_folder="Downloads_Immich")
    # total_albums, total_assets = immich_download_albums("1994 - Recuerdos", output_folder="Downloads_Immich")
    # print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums} different albbums.")

    # # 6) Example: Download everything in the structure /Albums/<albumName>/ + /No-Albums/yyyy/mm
    # print("\n=== EXAMPLE: immich_download_ALL() ===")
    # # total_struct = immich_download_ALL(output_folder="Downloads_Immich")
    # total_albums_downloaded, total_assets_downloaded = immich_download_ALL(output_folder="Downloads_Immich")
    # print(f"[RESULT] Bulk download completed. \nTotal albums: {total_albums_downloaded}\nTotal assets: {total_assets_downloaded}.")

    # # 7) Example: Delete Orphan Assets
    # immich_delete_orphan_assets(user_confirmation=True)

    # # 8) Example: Delete ALL Assets
    # immich_delete_all_assets()

    # # 9) Example: Delete ALL Assets
    # immich_delete_all_albums(deleteAlbumsAssets=True)

    # # 10) Local logout
    # logout_immich()
