# -*- coding: utf-8 -*-

"""
ClassImmichPhotos.py
---------------
Python module with example functions to interact with Immich Photos, including followfing functions:
  - Configuration (read config)
  - Authentication (login/logout)
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Removing empty or duplicate albums
  - Main functions for use in other modules:
     - remove_empty_albums()
     - remove_duplicates_albums()
     - immich_upload_folder()
     - upload_albums()
     - download_albums()
     - download_ALL()
"""
# ClassImmichPhotos.py
# -*- coding: utf-8 -*-

"""
Single class version of ClassImmichPhotos.py:
- All docstrings and comments in English.
- Preserves original LOGGER text (e.g., "INFO    :", "WARNING :", etc.).
- Uses a global LOGGER from GlobalVariables.
"""

import os,sys
import requests
import json
import urllib3
import fnmatch
import logging
from datetime import datetime
from dateutil import parser
from urllib.parse import urlparse
from halo import Halo
from tabulate import tabulate

from Utils import update_metadata, convert_to_list, tqdm, sha1_checksum

# We also keep references to your custom logger context manager and utility functions:
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassImmichPhotos:
    """
    Encapsulates all the functionality from the original ClassImmichPhotos.py
    into a single class that uses a global LOGGER from GlobalVariables.
    """
    def __init__(self, account_id=1):
        """
        Constructor that initializes what used to be global variables.
        Also imports the global LOGGER from GlobalVariables.
        """
        # # Import the global LOGGER from GlobalVariables
        # from GlobalVariables import LOGGER
        # self.logger = LOGGER

        self.ACCOUNT_ID = str(account_id)        # Used to identify wich Account to use from the configuration file
        if account_id not in [1, 2]:
            LOGGER.error(f"ERROR   : Cannot create Immich Photos object with ACCOUNT_ID: {account_id}. Valid valies are [1, 2]. Exiting...")
            sys.exit(-1)

        self.CONFIG = {}

        self.IMMICH_URL = None
        self.IMMICH_API_KEY_ADMIN = None
        self.IMMICH_USER_API_KEY = None
        self.IMMICH_USERNAME = None
        self.IMMICH_PASSWORD = None

        self.SESSION_TOKEN = None
        self.API_KEY_LOGIN = False
        self.HEADERS_WITH_CREDENTIALS = {}

        self.ALLOWED_IMMICH_MEDIA_EXTENSIONS = []
        self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = []
        self.ALLOWED_IMMICH_EXTENSIONS = []

        # Additional filters that might be in your config
        self.IMMICH_FILTER_ARCHIVE = None
        self.IMMICH_FILTER_FROM = None
        self.IMMICH_FILTER_TO = None
        self.IMMICH_FILTER_COUNTRY = None
        self.IMMICH_FILTER_CITY = None
        self.IMMICH_FILTER_PERSON = None

        # Create a dictionary to save in memmory all the albums owned by this user to avoid multiple calls to method get_albums_ownned_by_user()
        self.albums_owned_by_user = {}

        # Read the Config File to get CLIENT_ID
        self.read_config_file()
        self.CLIENT_ID = self.get_user_mail()

        self.CLIENT_NAME = f'Immich Photos ({self.CLIENT_ID})'


    ###########################################################################
    #                           CLASS PROPERTIES GETS                         #
    ###########################################################################
    def get_client_name(self, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return self.CLIENT_NAME


    ###########################################################################
    #                           CONFIGURATION READING                         #
    ###########################################################################
    def read_config_file(self, config_file='Config.ini', log_level=logging.INFO):
        """
        Reads the Configuration file and updates the instance attributes.
        If the config file is not found, prompts the user to manually input required data.

        Args:
            config_file (str): The path to the configuration file. Default is 'Config.ini'.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            dict: The loaded configuration dictionary.
        """
        from ConfigReader import load_config
        
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            if self.CONFIG:
                return self.CONFIG  # Configuration already read previously

            # Load CONFIG for Immich Photos section from config_file
            section_to_load = 'Immich Photos'
            conf = load_config(config_file=config_file, section_to_load=section_to_load)
            self.CONFIG[section_to_load] = conf.get(section_to_load)

            # Extract values for Immich from self.CONFIG
            self.IMMICH_URL = self.CONFIG.get(section_to_load).get('IMMICH_URL', None)
            self.IMMICH_API_KEY_ADMIN = self.CONFIG.get(section_to_load).get('IMMICH_API_KEY_ADMIN', None)

            self.IMMICH_USER_API_KEY = self.CONFIG.get(section_to_load).get(f'IMMICH_API_KEY_USER_{self.ACCOUNT_ID}', None)      # Read the configuration for the user account given by the suffix ACCAUNT_ID
            self.IMMICH_USERNAME = self.CONFIG.get(section_to_load).get(f'IMMICH_USERNAME_{self.ACCOUNT_ID}', None)              # Read the configuration for the user account given by the suffix ACCAUNT_ID
            self.IMMICH_PASSWORD = self.CONFIG.get(section_to_load).get(f'IMMICH_PASSWORD_{self.ACCOUNT_ID}', None)              # Read the configuration for the user account given by the suffix ACCAUNT_ID

            self.IMMICH_FILTER_ARCHIVE = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_ARCHIVE', None)
            self.IMMICH_FILTER_FROM = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_FROM', None)
            self.IMMICH_FILTER_TO = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_TO', None)
            self.IMMICH_FILTER_COUNTRY = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_COUNTRY', None)
            self.IMMICH_FILTER_CITY = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_CITY', None)
            self.IMMICH_FILTER_PERSON = self.CONFIG.get(section_to_load).get('IMMICH_FILTER_PERSON', None)
            # Verify required parameters and prompt on screen if missing
            if not self.IMMICH_URL or self.IMMICH_URL.strip() == '':
                LOGGER.warning(f"WARNING : IMMICH_URL not found. It will be requested on screen.")
                self.CONFIG['IMMICH_URL'] = input("[PROMPT] Enter IMMICH_URL (e.g., http://192.168.1.100:2283): ")
                self.IMMICH_URL = self.CONFIG['IMMICH_URL']
            if not self.IMMICH_USER_API_KEY or self.IMMICH_USER_API_KEY.strip() == '':
                if not self.IMMICH_USERNAME or self.IMMICH_USERNAME.strip() == '':
                    LOGGER.warning(f"WARNING : IMMICH_USERNAME not found. It will be requested on screen.")
                    self.CONFIG['IMMICH_USERNAME'] = input("[PROMPT] Enter IMMICH_USERNAME (Immich email): ")
                    self.IMMICH_USERNAME = self.CONFIG['IMMICH_USERNAME']
                if not self.IMMICH_PASSWORD or self.IMMICH_PASSWORD.strip() == '':
                    LOGGER.warning(f"WARNING : IMMICH_PASSWORD not found. It will be requested on screen.")
                    self.CONFIG['IMMICH_PASSWORD'] = input("[PROMPT] Enter IMMICH_PASSWORD: ")
                    self.IMMICH_PASSWORD = self.CONFIG['IMMICH_PASSWORD']
            else:
                self.API_KEY_LOGIN = True
                LOGGER.info("")
                LOGGER.info(f"INFO    : Immich Config Read:")
                LOGGER.info(f"INFO    : -------------------")
                LOGGER.info(f"INFO    : IMMICH_URL            : {self.IMMICH_URL}")
                if self.API_KEY_LOGIN:
                    masked_admin_api = '*' * len(self.IMMICH_API_KEY_ADMIN)
                    masked_user_api = '*' * len(self.IMMICH_USER_API_KEY)
                    LOGGER.info(f"INFO    : IMMICH_ADMIN_API_KEY  : {masked_admin_api}")
                    LOGGER.info(f"INFO    : IMMICH_USER_API_KEY   : {masked_user_api}")
                else:
                    LOGGER.info(f"INFO    : IMMICH_USERNAME       : {self.IMMICH_USERNAME}")
                    masked_password = '*' * len(self.IMMICH_PASSWORD)
                    LOGGER.info(f"INFO    : IMMICH_PASSWORD       : {masked_password}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_ARCHIVE : {self.IMMICH_FILTER_ARCHIVE}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_FROM    : {self.IMMICH_FILTER_FROM}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_TO      : {self.IMMICH_FILTER_TO}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_COUNTRY : {self.IMMICH_FILTER_COUNTRY}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_CITY    : {self.IMMICH_FILTER_CITY}")
                LOGGER.info(f"INFO    : IMMICH_FILTER_PERSON  : {self.IMMICH_FILTER_PERSON}")

            return self.CONFIG


    ###########################################################################
    #                         AUTHENTICATION / LOGOUT                         #
    ###########################################################################
    def login(self, log_level=logging.INFO):
        """
        Logs into Immich and obtains a JWT token in self.SESSION_TOKEN,
        or sets x-api-key headers if self.API_KEY_LOGIN is True.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns True if successful, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            # If there's already a token/headers, assume logged in
            if (self.HEADERS_WITH_CREDENTIALS and
               (f"Bearer {self.SESSION_TOKEN}" in self.HEADERS_WITH_CREDENTIALS.values() or
                (self.IMMICH_USER_API_KEY and self.IMMICH_USER_API_KEY in self.HEADERS_WITH_CREDENTIALS.values()))):
                return True

            # Ensure config is read
            self.read_config_file(log_level=log_level)
            LOGGER.info("")
            LOGGER.info(f"INFO    : Authenticating on Immich Photos and getting Session...")

            if self.API_KEY_LOGIN:
                # Using user API key from config
                url = f"{self.IMMICH_URL}/api/auth/validateToken"
                headers = {
                    'Accept': 'application/json',
                    'x-api-key': self.IMMICH_USER_API_KEY
                }
                try:
                    response = requests.post(url, headers=headers, data={})
                    response.raise_for_status()
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception occurred during Immich login: {str(e)}")
                    return False
                

                self.HEADERS_WITH_CREDENTIALS = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'x-api-key': self.IMMICH_USER_API_KEY
                }
                LOGGER.info(f"INFO    : Authentication Successfully with IMMICH_USER_API_KEY found in Config file.")
            else:
                # Using user/password
                url = f"{self.IMMICH_URL}/api/auth/login"
                payload = json.dumps({
                    "email": self.IMMICH_USERNAME,
                    "password": self.IMMICH_PASSWORD
                })
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                try:
                    response = requests.post(url, headers=headers, data=payload)
                    response.raise_for_status()
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception occurred during Immich login: {str(e)}")
                    return False
                

                data = response.json()
                self.SESSION_TOKEN = data.get("accessToken", None)
                if not self.SESSION_TOKEN:
                    LOGGER.error(f"ERROR   : 'accessToken' not found in the response: {data}")
                    return False

                self.HEADERS_WITH_CREDENTIALS = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.SESSION_TOKEN}'
                }
                LOGGER.info(f"INFO    : Authentication Successfully with user/password found in Config file.")

            # Now retrieve list of allowed media/sidecar extensions
            self.ALLOWED_IMMICH_MEDIA_EXTENSIONS = self.get_supported_media_types(log_level=logging.WARNING)
            self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = self.get_supported_media_types(type='sidecar', log_level=logging.WARNING)
            self.ALLOWED_IMMICH_EXTENSIONS = self.ALLOWED_IMMICH_MEDIA_EXTENSIONS + self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS

            # Restore log_level of the parent method
            # set_log_level(LOGGER, parent_log_level, manual=True)
            return True


    def logout(self, log_level=logging.INFO):
        """
        Logout locally by discarding the token. (Immich does not provide an official /logout endpoint).

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            self.SESSION_TOKEN = None
            self.HEADERS_WITH_CREDENTIALS = {}
            LOGGER.info("INFO    : Session closed locally (Bearer Token discarded).")


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def get_supported_media_types(self, type='media', log_level=logging.INFO):
        """
        Returns the supported media/sidecar extensions as reported by Immich (via /api/server/media-types).
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/server/media-types"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS)
                resp.raise_for_status()
                data = resp.json()
                image = data.get("image", [])
                video = data.get("video", [])
                sidecar = data.get("sidecar", [])

                if type.lower() == 'media':
                    supported_types = image + video
                    LOGGER.debug(f"DEBUG   : Supported media types: '{supported_types}'.")
                elif type.lower() == 'image':
                    supported_types = image
                    LOGGER.debug(f"DEBUG   : Supported image types: '{supported_types}'.")
                elif type.lower() == 'video':
                    supported_types = video
                    LOGGER.debug(f"DEBUG   : Supported video types: '{supported_types}'.")
                elif type.lower() == 'sidecar':
                    supported_types = sidecar
                    LOGGER.debug(f"DEBUG   : Supported sidecar types: '{supported_types}'.")
                else:
                    LOGGER.error(f"ERROR   : Invalid type '{type}' to get supported media types. Types allowed are 'media', 'image', 'video' or 'sidecar'")
                    return None
                return supported_types
            except Exception as e:
                LOGGER.error(f"ERROR   : Cannot get Supported media types: {e}")
                return None


    def get_user_id(self, log_level=logging.INFO):
        """
        Returns the user_id of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/users/me"
            payload = {}
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload)
                resp.raise_for_status()
                data = resp.json()
                user_id = data.get("id")
                user_mail = data.get("email")
                LOGGER.info(f"INFO    : User ID: '{user_id}' found for user '{user_mail}'.")
                return user_id
            except Exception as e:
                LOGGER.error(f"ERROR   : Cannot find User ID for user '{self.IMMICH_USERNAME}': {e}")
                return None


    def get_user_mail(self, log_level=logging.INFO):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/users/me"
            payload = {}
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload)
                resp.raise_for_status()
                data = resp.json()
                user_id = data.get("id")
                user_mail = data.get("email")
                LOGGER.info(f"INFO    : User ID: '{user_id}' found for user '{user_mail}'.")
                return user_mail
            except Exception as e:
                LOGGER.error(f"ERROR   : Cannot find User ID for user '{self.IMMICH_USERNAME}': {e}")
                return None


    ###########################################################################
    #                           ALBUMS FUNCTIONS                              #
    ###########################################################################
    def create_album(self, album_name, log_level=logging.INFO):
        """
        Creates a new album in Immich Photos with the specified name.

        Args:
            album_name (str): Album name to be created.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: New album ID or None if it fails
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums"
            payload = json.dumps({"albumName": album_name})

            try:
                resp = requests.post(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                album_id = data.get("id")
                LOGGER.debug(f"DEBUG   : Album '{album_name}' created with ID: {album_id}")
                return album_id
            except Exception as e:
                LOGGER.warning(f"WARNING : Cannot create album '{album_name}' due to API call error. Skipped! {e}")
                return None



    def remove_album(self, album_id, album_name, log_level=logging.INFO):
        """
        Removes an album in Immich Photos by its album ID.

        Args:
            album_id (str): ID of the album to delete.
            album_name (str): Name of the album to delete.
            log_level (logging.LEVEL): log_level for logs and console

        Returns True on success, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums/{album_id}"
            try:
                response = requests.delete(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                if response.status_code == 200:
                    LOGGER.info(f"INFO    : Album '{album_name}' with ID={album_id} removed.")
                    return True
                else:
                    LOGGER.warning(f"WARNING : Failed to remove album: '{album_name}' with ID: {album_id}. Status: {response.status_code}")
                    return False
            except Exception as e:
                LOGGER.error(f"ERROR   : Error while removing album '{album_name}' with ID:  {album_id}: {e}")
                return False



    def get_albums_owned_by_user(self, log_level=logging.INFO):
        """
        Get all albums in Immich Photos for the current user.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of dictionaries where each item has below structure:
                    {
                      "id": <str>,
                      "albumName": <str>,
                      "ownerId": <str>,
                      "...",
                    }
            None on error
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                albums = resp.json()
                user_id = self.get_user_id(log_level=logging.WARNING)
                own_albums = []
                for album in albums:
                    if album.get('ownerId') == user_id:
                        own_albums.append(album)
                return own_albums
            except Exception as e:
                LOGGER.error(f"ERROR   : Error while listing albums: {e}")
                return None


    def get_albums_including_shared_with_user(self, log_level=logging.INFO):
        """
        Get both own and shared albums in Immich Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of dictionaries where each item has below structure:
                    {
                      "id": <str>,
                      "albumName": <str>,
                      "ownerId": <str>,
                      ...
                    }
            None on error
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                LOGGER.error(f"ERROR   : Error while listing albums: {e}")
                return None


    def get_album_assets_size(self, album_id, log_level=logging.INFO):
        """
        Gets the total size (bytes) of all assets in an album.

        Args:
            album_id (str): Album ID
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Album Size or -1 on error.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            try:
                assets = self.get_album_assets(album_id, log_level=log_level)
                total_size = 0
                for asset in assets:
                    exif_info = asset.get("exifInfo", {})
                    if "fileSizeInByte" in exif_info:
                        total_size += exif_info["fileSizeInByte"]
                return total_size
            except Exception:
                return -1



    def get_album_assets_count(self, album_id, log_level=logging.INFO):
        """
        Gets the number of assets in an album.

        Args:
            album_id (str): Album ID
            log_level (logging.LEVEL): log_level for logs and console
        Returns:
             int: Album Items Count or -1 on error.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            try:
                assets = self.get_album_assets(album_id, log_level=log_level)
                return len(assets)
            except Exception:
                return -1



    def album_exists(self, album_name, log_level=logging.INFO):
        """
        Gets the number of items in an album.

        Args:
            album_name (str): Album Name
            log_level (logging.LEVEL): log_level for logs and console
        Returns:
             bool: True if Album exists. False if Album does not exists.
             album_id (str): album_id if Album  exists. None if Album does not exists.
        """
        with set_log_level(LOGGER, log_level):
            album_exists = False  # Initialize album existence flag
            album_id = None  # Initialize album ID as None

            # First, check if the album is already in the user's dictionary
            if album_name in self.albums_owned_by_user:
                album_exists = True
                album_id = self.albums_owned_by_user[album_name]
            else:
                # If not found, retrieve the list of owned albums (from an API)
                albums = self.get_albums_owned_by_user(log_level=log_level)
                for album in albums:
                    if album_name == album.get("albumName"):
                        album_exists = True
                        album_id = album.get("id")
                        self.albums_owned_by_user[album_name] = album_id  # Cache it for future use
                        break  # Stop searching once found
            return album_exists, album_id


    ###########################################################################
    #                        ASSETS (PHOTOS/VIDEOS)                           #
    ###########################################################################
    def get_all_assets(self, type=None, isNotInAlbum=None, isArchived=None,
                       createdAfter=None, createdBefore=None, country=None,
                       city=None, personIds=None, withDeleted=None, log_level=logging.INFO):
        """
        Lists all assets in Immich Photos that match with the specified filters.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets (dict) matching the specified filters in the entire library or Empty list on error.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/search/metadata"
            all_assets = []
            try:
                next_page = 1
                while True:
                    payload_data = {
                        "page": next_page,
                        "order": "desc",
                        # "withArchived": False,
                        # "withDeleted": False,
                        # "country": "string",
                        # "city": "string",
                        # "type": "IMAGE",
                        # "isNotInAlbum": False,
                        # "isArchived": True,
                        # "isOffline": isOffline,
                        # "isEncoded": True,
                        # "isFavorite": True,
                        # "isMotion": True,
                        # "isVisible": True,
                        # "withRemoved": True,
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
                    if type: payload_data["type"] = type
                    if isNotInAlbum: payload_data["isNotInAlbum"] = isNotInAlbum
                    if isArchived: payload_data["isArchived"] = isArchived
                    if createdAfter: payload_data["createdAfter"] = createdAfter
                    if createdBefore: payload_data["createdBefore"] = createdBefore
                    if country: payload_data["country"] = country
                    if city: payload_data["city"] = city
                    if personIds: payload_data["personIds"] = personIds
                    if withDeleted: payload_data["withDeleted"] = withDeleted

                    payload = json.dumps(payload_data)
                    resp = requests.post(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("assets", {}).get("items", [])
                    all_assets.extend(items)
                    next_page = data.get("assets", {}).get("nextPage", None)
                    if next_page is None:
                        break
            except Exception as e:
                LOGGER.error(f"ERROR   : Failed to retrieve assets: {str(e)}")

            # Add new fields "time" with the same value as "fileCreatedAt" and "filename" with the same value as "originalFileName" to allign with Synology Photos
            for asset in all_assets:
                asset["time"] = asset["fileCreatedAt"]
                asset["filename"] = asset["originalFileName"]

            return all_assets


    def get_album_assets(self, album_id, album_name=None, log_level=logging.INFO):
        """
        Get assets in a specific album.

        Args:
            album_id (str): ID of the album.
            album_name (str): Name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of photos in the album (dict objects). [] if no assets found.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums/{album_id}"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                data = resp.json()
                all_assets = data.get("assets", [])
                # Add new fields "time" with the same value as "fileCreatedAt" and "filename" with the same value as "originalFileName" to allign with Synology Photos
                for asset in all_assets:
                    asset["time"] = asset["fileCreatedAt"]
                    asset["filename"] = asset["originalFileName"]
                return all_assets
            except Exception as e:
                if album_name:
                    LOGGER.error(f"ERROR   : Failed to retrieve assets from album '{album_name}': {str(e)}")
                else:
                    LOGGER.error(f"ERROR   : Failed to retrieve assets from album ID={album_id}: {str(e)}")
                return []


    def get_no_albums_assets(self, log_level=logging.WARNING):
        """
        Get assets not associated to any album from Immich Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_without_albums
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            assets_without_albums = self.get_all_assets(isNotInAlbum=True, log_level=log_level)
            LOGGER.info(f"INFO    : Number of all_assets without Albums associated: {len(assets_without_albums)}")
            return assets_without_albums


    def get_all_albums_assets(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: Albums Assets
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            all_albums = self.get_albums_including_shared_with_user(log_level=log_level)
            combined_assets = []
            if not all_albums:
                return []
            for album in all_albums:
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                album_assets = self.get_album_assets(album_id, album_name, log_level=log_level)
                combined_assets.extend(album_assets)
            return combined_assets


    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=logging.INFO):
        """
        Adds photos (asset_ids) to an album.

        Args:
            album_id (str): The ID of the album to which we add assets.
            asset_ids (list or str): The IDs of assets to add.
            album_name (str): The name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Number of assets added to the album
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not asset_ids:
                return 0
            asset_ids = convert_to_list(asset_ids)
            url = f"{self.IMMICH_URL}/api/albums/{album_id}/assets"
            payload = json.dumps({"ids": asset_ids})
            try:
                resp = requests.put(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                total_added = sum(1 for item in data if item.get("success"))
                return total_added
            except Exception as e:
                if album_name:
                    LOGGER.warning(f"WARNING : Error while adding assets to album '{album_name}' with ID={album_id}: {e}")
                else:
                    LOGGER.warning(f"WARNING : Error while adding assets to album with ID={album_id}: {e}")
                return 0


    def get_duplicates_assets(self, log_level=logging.INFO):
        """
        Returns the list of duplicate assets from Immich (via /api/duplicates).
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/duplicates"
            resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS)
            resp.raise_for_status()
            return resp.json()


    def remove_assets(self, asset_ids, log_level=logging.INFO):
        """
        Removes the given asset(s) from Synology Photos.

        Args:
            asset_ids (list): list of assets ID to remove
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Number of assets removed
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/assets"
            payload = json.dumps({"force": True, "ids": asset_ids})
            try:
                response = requests.delete(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload)
                response.raise_for_status()
                if response.ok:
                    return len(asset_ids)
                else:
                    LOGGER.error(f"ERROR   : Failed to remove assets due to API error")
                    return 0
            except Exception as e:
                LOGGER.error(f"ERROR   : Failed to remove assets: {str(e)}")
                return 0



    def remove_duplicates_assets(self, log_level=logging.INFO):
        """
        Removes duplicate assets in the Immich database. Returns how many duplicates got removed.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            duplicates_assets = self.get_duplicates_assets(log_level=log_level)
            duplicates_ids = []
            for duplicates_set in duplicates_assets:
                duplicates_assets_in_set = duplicates_set.get('assets', [])
                # Keep the first, remove the rest
                for duplicate_asset_in_set in duplicates_assets_in_set[1:]:
                    duplicates_ids.append(duplicate_asset_in_set.get('id'))

            if len(duplicates_ids) > 0:
                LOGGER.info(f"INFO    : Removing Duplicates Assets...")
                return self.remove_assets(duplicates_ids, log_level=log_level)
            return 0


    def upload_asset(self, file_path, log_level=logging.INFO):
        """
        Uploads a local file (photo/video) to Immich Photos via /api/assets.

        Args:
            file_path (str): file_path of the asset to upload
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: the asset_id if success, or None if it fails or is an unsupported extension.
            bool: is_duplicated = False if success, or None if it fails or is an unsupported extension.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not os.path.isfile(file_path):
                LOGGER.error(f"ERROR   : File not found: {file_path}")
                return None, None

            # Calculate checksum to avoid duplicates
            # hex_checksum, base64_checksum = sha1_checksum(file_path)

            filename, ext = os.path.splitext(file_path)

            # Check extension
            if ext.lower() not in self.ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                if ext.lower() in self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
                    return None, None
                else:
                    LOGGER.warning(f"WARNING : File '{file_path}' has an unsupported extension. Skipped.")
                    return None, None

            url = f"{self.IMMICH_URL}/api/assets"
            files = {
                'assetData': open(file_path, 'rb')
            }

            # Check for sidecar in the same path
            for sidecar_extension in self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
                sidecar_path_1 = f"{file_path}{sidecar_extension}"
                sidecar_path_2 = file_path.replace(ext, sidecar_extension)
                if os.path.isfile(sidecar_path_1):
                    files['sidecarData'] = open(sidecar_path_1, 'rb')
                    break
                elif os.path.isfile(sidecar_path_2):
                    files['sidecarData'] = open(sidecar_path_2, 'rb')
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
                'isVisible': 'true',
            }

            # Determine headers
            if self.API_KEY_LOGIN:
                header = {
                    'Accept': 'application/json',
                    'x-api-key': self.IMMICH_USER_API_KEY
                }
            else:
                header = {
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.SESSION_TOKEN}'
                }

            try:
                response = requests.post(url, headers=header, data=data, files=files)
                response.raise_for_status()
                new_asset = response.json()
                asset_id = new_asset.get("id")
                is_duplicated = (new_asset.get("status") == 'duplicate')
                if asset_id:
                    if is_duplicated:
                        LOGGER.debug(f"DEBUG   : Duplicated Asset: '{os.path.basename(file_path)}'. Skipped!")
                    else:
                        LOGGER.debug(f"DEBUG   : Uploaded '{os.path.basename(file_path)}' with asset_id={asset_id}")
                return asset_id, is_duplicated
            except Exception as e:
                LOGGER.error(f"ERROR   : Failed to upload '{file_path}': {e}")
                return None, None


    def download_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_Immich", log_level=logging.INFO):
        """
        Downloads an asset (photo/video) from Immich Photos to a local folder,
        preserving the original timestamp if available.

        Args:
            asset_id (int): ID of the asset to download.
            asset_filename (str): filename of the asset to download.
            asset_time (int or str): UNIX epoch or ISO string time of the asset.
            download_folder (str): Path where the file will be saved.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: 1 if download succeeded, 0 if failed.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            os.makedirs(download_folder, exist_ok=True)

            if isinstance(asset_time, str):
                asset_time = parser.isoparse(asset_time).timestamp()

            if asset_time > 0:
                asset_datetime = datetime.fromtimestamp(asset_time)
            else:
                asset_datetime = datetime.now()

            file_ext = os.path.splitext(asset_filename)[1].lower()
            url = f"{self.IMMICH_URL}/api/assets/{asset_id}/original"

            try:
                req = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False, stream=True)
                req.raise_for_status()
                file_path = os.path.join(download_folder, asset_filename)
                with open(file_path, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Update timestamps using the asset_time
                os.utime(file_path, (asset_time, asset_time))
                # If extension is recognized, update metadata
                if file_ext in self.ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                    update_metadata(file_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"), log_level=logging.ERROR)

                LOGGER.debug("")
                LOGGER.debug(f"DEBUG   : Asset '{asset_filename}' downloaded and saved at {file_path}")
                return 1
            except Exception as e:
                LOGGER.error(f"ERROR   : Failed to download asset {asset_id}: {e}")
                return 0


    ###########################################################################
    #                  HIGH-LEVEL MAIN FUNCTIONS (UPLOAD/DOWNLOAD)            #
    ###########################################################################
    def upload_albums(self, input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        """
        Traverses the subfolders of 'input_folder', creating an album for each valid subfolder (album name equals
        the subfolder name). Within each subfolder, it uploads all files with allowed extensions (based on
        self.ALLOWED_IMMICH_EXTENSIONS) and associates them with the album.
        
        Example structure:
        input_folder/
            ├─ Album1/   (files for album "Album1")
            └─ Album2/   (files for album "Album2")

        Args:
            input_folder (str): Input folder
            subfolders_exclusion (str or list): Subfolders exclusion
            subfolders_inclusion (str or list): Subfolders inclusion
            remove_duplicates (bool): True to remove duplicates assets after upload
            log_level (logging.LEVEL): log_level for logs and console

        Returns: (albums_uploaded, albums_skipped, assets_uploaded, total_duplicates_assets_removed, total_duplicates_assets_skipped)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not os.path.isdir(input_folder):
                LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
                self.logout(log_level=log_level)
                return 0, 0, 0, 0, 0

            subfolders_exclusion = convert_to_list(subfolders_exclusion)
            subfolders_inclusion = convert_to_list(subfolders_inclusion)

            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_duplicates_assets_removed = 0
            total_duplicates_assets_skipped = 0

            SUBFOLDERS_EXCLUSIONS = ['@eaDir'] + subfolders_exclusion

            # user_id = self.get_user_id(log_level=log_level)
            valid_folders = []

            for root, folders, _ in os.walk(input_folder):
                folders[:] = [d for d in folders if d not in SUBFOLDERS_EXCLUSIONS]
                if subfolders_inclusion:
                    rel_path = os.path.relpath(root, input_folder)
                    if rel_path == ".":
                        folders[:] = [d for d in folders if d in subfolders_inclusion]
                    else:
                        first_dir = rel_path.split(os.sep)[0]
                        if first_dir not in subfolders_inclusion:
                            folders[:] = []

                for folder in folders:
                    dir_path = os.path.join(root, folder)
                    if not os.path.isdir(dir_path):
                        continue
                    # Check if there's at least one supported file
                    has_supported = any(
                        os.path.splitext(f)[-1].lower() in self.ALLOWED_IMMICH_EXTENSIONS
                        for f in os.listdir(dir_path)
                        if os.path.isfile(os.path.join(dir_path, f))
                    )
                    if has_supported:
                        valid_folders.append(dir_path)

            first_level_folders = os.listdir(input_folder)
            if subfolders_inclusion:
                first_level_folders += subfolders_inclusion

            with tqdm(total=len(valid_folders), smoothing=0.1,
                      desc="INFO    : Uploading Albums from Folders", unit=" folders") as pbar:
                for subpath in valid_folders:
                    pbar.update(1)
                    album_assets_ids = []
                    rel_path = os.path.relpath(subpath, input_folder)
                    path_parts = rel_path.split(os.sep)

                    if len(path_parts) == 1:
                        album_name = path_parts[0]
                    else:
                        if path_parts[0] in first_level_folders:
                            album_name = " - ".join(path_parts[1:])
                        else:
                            album_name = " - ".join(path_parts)

                    if not album_name:
                        total_albums_skipped += 1
                        continue

                    for f in os.listdir(subpath):
                        file_path = os.path.join(subpath, f)
                        if not os.path.isfile(file_path):
                            continue
                        ext = os.path.splitext(f)[-1].lower()
                        if ext not in self.ALLOWED_IMMICH_EXTENSIONS:
                            continue

                        asset_id, is_dup = self.upload_asset(file_path, log_level=log_level)
                        if is_dup:
                            total_duplicates_assets_skipped += 1
                            LOGGER.debug(f"DEBUG   : Dupplicated Asset: {file_path}. Asset ID: {asset_id} skipped")
                        elif asset_id:
                            total_assets_uploaded += 1
                            if ext in self.ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                                album_assets_ids.append(asset_id)

                    if album_assets_ids:
                        album_id = self.create_album(album_name, log_level=log_level)
                        if not album_id:
                            LOGGER.warning(f"WARNING : Could not create album for subfolder '{subpath}'.")
                            total_albums_skipped += 1
                        else:
                            self.add_assets_to_album(album_id, album_assets_ids, album_name=album_name, log_level=log_level)
                            LOGGER.debug(f"DEBUG   : Album '{album_name}' created with ID: {album_id}. Total Assets added to Album: {len(album_assets_ids)}.")
                            total_albums_uploaded += 1
                    else:
                        total_albums_skipped += 1

            if remove_duplicates:
                LOGGER.info("INFO    : Removing Duplicates Assets...")
                total_duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

            LOGGER.info(f"INFO    : Uploaded {total_albums_uploaded} album(s) from '{input_folder}'.")
            LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} asset(s) from '{input_folder}' to Albums.")
            LOGGER.info(f"INFO    : Skipped {total_albums_skipped} album(s) from '{input_folder}'.")
            LOGGER.info(f"INFO    : Removed {total_duplicates_assets_removed} duplicates asset(s) from Immich Database.")
            LOGGER.info(f"INFO    : Skipped {total_duplicates_assets_skipped} duplicated asset(s) from '{input_folder}' to Albums.")

            self.logout(log_level=log_level)
            return (total_albums_uploaded,
                    total_albums_skipped,
                    total_assets_uploaded,
                    total_duplicates_assets_removed,
                    total_duplicates_assets_skipped)


    def upload_no_albums(self, input_folder,
                         subfolders_exclusion='Albums',
                         subfolders_inclusion=None,
                         remove_duplicates=True,
                         log_level=logging.WARNING):
        """
        Recursively traverses 'input_folder' and its subfolders_inclusion to upload all
        compatible files (photos/videos) to Immich without associating them to any album.

        If 'subfolders_inclusion' is provided (as a string or list of strings), only those
        direct subfolders_inclusion of 'input_folder' are processed (excluding any in SUBFOLDERS_EXCLUSIONS).
        Otherwise, all subfolders_inclusion except those listed in SUBFOLDERS_EXCLUSIONS are processed.

        Returns total_assets_uploaded, total_duplicated_assets_skipped, duplicates_assets_removed.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not os.path.isdir(input_folder):
                LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
                self.logout(log_level=log_level)
                return 0, 0, 0

            subfolders_exclusion = convert_to_list(subfolders_exclusion)
            subfolders_inclusion = convert_to_list(subfolders_inclusion)

            SUBFOLDERS_EXCLUSIONS = ['@eaDir'] + subfolders_exclusion

            def collect_files(base_folder, only_subfolders):
                flist = []
                if only_subfolders:
                    for sub in only_subfolders:
                        sub_path = os.path.join(base_folder, sub)
                        if not os.path.isdir(sub_path):
                            LOGGER.warning(f"WARNING : Subfolder '{sub}' does not exist in '{base_folder}'. Skipping.")
                            continue
                        for root, dirs, files in os.walk(sub_path):
                            dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                            for file_ in files:
                                flist.append(os.path.join(root, file_))
                else:
                    for root, dirs, files in os.walk(base_folder):
                        dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                        for file_ in files:
                            flist.append(os.path.join(root, file_))
                return flist

            file_paths = collect_files(input_folder, subfolders_inclusion)
            total_files = len(file_paths)
            total_assets_uploaded = 0
            total_duplicated_assets_skipped = 0

            with tqdm(total=total_files, smoothing=0.1,
                      desc="INFO    : Uploading Assets", unit=" asset") as pbar:
                for f_idx, file_path in enumerate(file_paths, start=1):
                    pbar.update(1)
                    _, ext = os.path.splitext(file_path)
                    ext = ext.lower()
                    if ext not in self.ALLOWED_IMMICH_EXTENSIONS:
                        LOGGER.debug(f"DEBUG   : Unsopported Extension: '{ext}'. Skipped")
                        continue

                    asset_id, is_dup = self.upload_asset(file_path, log_level=log_level)
                    if is_dup:
                        total_duplicated_assets_skipped += 1
                        LOGGER.debug(f"DEBUG   : Dupplicated Asset: {file_path}. Asset ID: {asset_id} skipped")
                    elif asset_id:
                        LOGGER.debug(f"DEBUG   : Asset ID: {asset_id} uploaded to Immich Photos")
                        total_assets_uploaded += 1

            duplicates_assets_removed = 0
            if remove_duplicates:
                LOGGER.info("INFO    : Removing Duplicates Assets...")
                duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

            LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")
            LOGGER.info(f"INFO    : Skipped {total_duplicated_assets_skipped} duplicated asset(s) from '{input_folder}'.")
            LOGGER.info(f"INFO    : Removed {duplicates_assets_removed} duplicates asset(s) from Immich Database.")

            self.logout(log_level=log_level)
            return total_assets_uploaded, total_duplicated_assets_skipped, duplicates_assets_removed


    def upload_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        """
        Uploads ALL photos/videos from input_folder into Immich Photos.
        Returns details about how many albums and assets were uploaded.

        Args:
            input_folder (str): Input folder
            albums_folders (str): Albums folder
            remove_duplicates (bool): True to remove duplicates assets after upload all assets
            log_level (logging.LEVEL): log_level for logs and console

        Returns: (albums_uploaded, albums_skipped, assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed, total_dupplicated_assets_skipped)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)

            total_duplicates_assets_removed = 0
            input_folder = os.path.realpath(input_folder)
            albums_folders = convert_to_list(albums_folders)

            # Ensure 'Albums' is included
            albums_folder_included = any((subf.lower() == 'albums') for subf in albums_folders)
            if not albums_folder_included:
                albums_folders.append('Albums')

            LOGGER.info("")
            LOGGER.info(f"INFO    : Uploading Assets and creating Albums into immich Photos from '{albums_folders}' subfolders...")

            (total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, total_duplicates_assets_removed_1, total_dupplicated_assets_skipped_1) = self.upload_albums(
                 input_folder=input_folder,
                 subfolders_inclusion=albums_folders,
                 remove_duplicates=False,
                 log_level=logging.WARNING
            )

            LOGGER.info("")
            LOGGER.info(f"INFO    : Uploading Assets without Albums creation into immich Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")

            (total_assets_uploaded_without_albums, total_dupplicated_assets_skipped_2, total_duplicates_assets_removed_2) = self.upload_no_albums(
                 input_folder=input_folder,
                 subfolders_exclusion=albums_folders,
                 remove_duplicates=False,
                 log_level=logging.WARNING
            )
            total_duplicates_assets_removed = total_duplicates_assets_removed_1 + total_duplicates_assets_removed_2
            total_dupplicated_assets_skipped = total_dupplicated_assets_skipped_1 + total_dupplicated_assets_skipped_2
            total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

            if remove_duplicates:
                LOGGER.info("INFO    : Removing Duplicates Assets...")
                total_duplicates_assets_removed += self.remove_duplicates_assets(log_level=logging.WARNING)

            self.logout(log_level=log_level)
            return (total_albums_uploaded,
                    total_albums_skipped,
                    total_assets_uploaded,
                    total_assets_uploaded_within_albums,
                    total_assets_uploaded_without_albums,
                    total_duplicates_assets_removed,
                    total_dupplicated_assets_skipped
            )


    def download_albums(self, albums_name='ALL', output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads photos/videos from albums by name pattern or ID. 'ALL' downloads all.

        Args:
            albums_name (str or list): The name(s) of the album(s) to download. Use 'ALL' to download all albums.
            output_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            tuple: (albums_downloaded, assets_downloaded)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            output_folder = os.path.join(output_folder, "Albums")
            os.makedirs(output_folder, exist_ok=True)

            all_albums = self.get_albums_including_shared_with_user(log_level=log_level)
            if not all_albums:
                LOGGER.warning("WARNING : No albums available or could not retrieve the list.")
                self.logout(log_level=log_level)
                return 0, 0

            if isinstance(albums_name, str):
                albums_name = [albums_name]

            if 'ALL' in [x.strip().upper() for x in albums_name]:
                albums_to_download = all_albums
                LOGGER.info(f"INFO    : ALL albums ({len(all_albums)}) will be downloaded...")
            else:
                found_albums = []
                for alb in all_albums:
                    alb_id = alb.get("id")
                    alb_name = alb.get("albumName", "")
                    for pattern in albums_name:
                        if alb_id == str(pattern):
                            found_albums.append(alb)
                            break
                        if fnmatch.fnmatch(alb_name.lower(), pattern.lower()):
                            found_albums.append(alb)
                            break

                if found_albums:
                    albums_to_download = found_albums
                    LOGGER.info(f"INFO    : {len(found_albums)} album(s) matched pattern(s) '{albums_name}'.")
                else:
                    LOGGER.warning(f"WARNING : No albums found matching pattern(s) '{albums_name}'.")
                    self.logout(log_level=log_level)
                    return 0, 0

            total_assets_downloaded = 0
            total_albums_downloaded = 0
            total_albums = len(albums_to_download)

            for alb in albums_to_download:
                alb_id = alb.get("id")
                alb_name = alb.get("albumName", f"album_{alb_id}")
                alb_folder = os.path.join(output_folder, alb_name)
                os.makedirs(alb_folder, exist_ok=True)

                assets_in_album = self.get_album_assets(alb_id, log_level=log_level)
                for asset in tqdm(assets_in_album, desc=f"INFO    : Downloading '{alb_name}'", unit=" assets"):
                    asset_id = asset.get("id")
                    asset_filename = os.path.basename(asset.get("originalFileName", "unknown"))
                    if asset_id:
                        asset_time = asset.get('fileCreatedAt')
                        total_assets_downloaded += self.download_asset(asset_id, asset_filename, asset_time, alb_folder, log_level=log_level)

                total_albums_downloaded += 1
                LOGGER.info(f"INFO    : Downloaded Album [{total_albums_downloaded}/{total_albums}] - '{alb_name}'. {len(assets_in_album)} asset(s) have been downloaded.")

            LOGGER.info(f"INFO    : Download of Albums completed.")
            LOGGER.info(f"INFO    : Total Albums downloaded: {total_albums_downloaded}")
            LOGGER.info(f"INFO    : Total Assets downloaded: {total_assets_downloaded}")

            self.logout(log_level=log_level)
            return total_albums_downloaded, total_assets_downloaded


    def download_no_albums(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads assets not associated to any album from Immich Photos into output_folder/No-Albums/.
        Then organizes them by year/month inside that folder.

        Args:
            output_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_downloaded or 0 if no assets are downloaded
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            total_assets_downloaded = 0

            all_assets_without_albums = self.get_no_albums_assets(log_level=log_level)
            no_albums_folder = os.path.join(output_folder, 'No-Albums')
            os.makedirs(no_albums_folder, exist_ok=True)

            LOGGER.info(f"INFO    : Found {len(all_assets_without_albums)} asset(s) without any album associated.")
            for asset in tqdm(all_assets_without_albums, desc="INFO    : Downloading assets without associated albums", unit=" assets"):
                asset_id = asset.get("id")
                asset_filename = os.path.basename(asset.get("originalFileName", "unknown"))
                if not asset_id:
                    continue

                created_at_str = asset.get("fileCreatedAt", "")
                try:
                    dt_created = datetime.fromisoformat(created_at_str.replace("Z", ""))
                except Exception:
                    dt_created = datetime.now()
                

                year_str = dt_created.strftime("%Y")
                month_str = dt_created.strftime("%m")
                target_folder = os.path.join(no_albums_folder, year_str, month_str)
                os.makedirs(target_folder, exist_ok=True)

                asset_time = asset.get('fileCreatedAt')
                total_assets_downloaded += self.download_asset(asset_id, asset_filename, asset_time, target_folder, log_level=log_level)

            LOGGER.info(f"INFO    : Download of assets without associated albums completed.")
            LOGGER.info(f"INFO    : Total Assets downloaded: {total_assets_downloaded}")

            self.logout(log_level=log_level)
            return total_assets_downloaded


    def download_ALL(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
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

        Args:
            output_folder (str): Output folder
            log_level (logging.LEVEL): log_level for logs and console
            
        Returns total_albums_downloaded, total_assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            total_albums_downloaded, total_assets_in_albums = self.download_albums(
                albums_name='ALL',
                output_folder=output_folder,
                log_level=log_level
            )
            total_assets_no_albums = self.download_no_albums(
                output_folder=output_folder,
                log_level=log_level
            )
            total_assets = total_assets_in_albums + total_assets_no_albums

            LOGGER.info(f"INFO    : Download of ALL assets completed.")
            LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
            LOGGER.info(f"Total Assets downloaded                   : {total_assets}")
            LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_in_albums}")
            LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_no_albums}")

            self.logout(log_level=log_level)
            return (total_albums_downloaded,
                    total_assets,
                    total_assets_in_albums,
                    total_assets_no_albums)


    ###########################################################################
    #                   REMOVE EMPTY / DUPLICATES ALBUMS                      #
    ###########################################################################
    # TODO: Complete this method
    def remove_empty_folders(self, log_level=logging.INFO):
        """
        Recursively removes all empty folders and subfolders in Immich Photos,
        considering folders empty if they only contain '@eaDir'.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty folders removed.
        """
        return 0


    def remove_empty_albums(self, log_level=logging.WARNING):
        """
        Removes all empty albums in Immich Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty albums deleted.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            albums = self.get_albums_owned_by_user(log_level=log_level)
            if not albums:
                LOGGER.info("INFO    : No albums found.")
                self.logout(log_level=log_level)
                return 0

            total_removed_empty_albums = 0
            LOGGER.info("INFO    : Looking for empty albums in Immich Photos...")
            for album in tqdm(albums, desc=f"INFO    : Searching for Empty Albums", unit=" albums"):
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                asset_count = album.get("assetCount")
                if asset_count == 0:
                    if self.remove_album(album_id, album_name):
                        LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) removed.")
                        total_removed_empty_albums += 1

            LOGGER.info(f"INFO    : Removed {total_removed_empty_albums} empty albums.")
            self.logout(log_level=log_level)
            return total_removed_empty_albums


    def remove_duplicates_albums(self, log_level=logging.WARNING):
        """
        Remove all duplicate albums in Immich Photos. Duplicates are albums
        that share the same item_count and total item_size. It keeps the first
        album, removes the others from each duplicate group.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of duplicate albums deleted.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            albums = self.get_albums_owned_by_user(log_level=log_level)
            if not albums:
                self.logout(log_level=log_level)
                return 0

            LOGGER.info("INFO    : Looking for duplicate albums in Immich Photos...")
            duplicates_map = {}
            for album in tqdm(albums, desc=f"INFO    : Searching for Duplicates Albums", unit=" albums"):
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                assets_count = album.get("assetCount")
                assets_size = self.get_album_assets_size(album_id, log_level=log_level)
                duplicates_map.setdefault((assets_count, assets_size), []).append((album_id, album_name))

            total_removed_duplicated_albums = 0
            for (assets_count, assets_size), group in duplicates_map.items():
                LOGGER.debug(f"DEBUG   : Assets Count: {assets_count}. Assets Size: {assets_size}.")
                if len(group) > 1:
                    # Keep the first, remove the rest
                    group_sorted = sorted(group, key=lambda x: x[1])  # sort by album_id string
                    to_remove = group_sorted[1:]
                    for (alb_id, alb_name) in to_remove:
                        LOGGER.info(f"INFO    : Removing duplicate album: '{alb_name}' (ID={alb_id})")
                        if self.remove_album(alb_id, alb_name):
                            total_removed_duplicated_albums += 1

            LOGGER.info(f"INFO    : Removed {total_removed_duplicated_albums} duplicate albums.")
            self.logout(log_level=log_level)
            return total_removed_duplicated_albums


    # -----------------------------------------------------------------------------
    #          DELETE ORPHANS ASSETS FROM IMMICH DATABASE
    # -----------------------------------------------------------------------------
    def remove_orphan_assets(self, user_confirmation=True, log_level=logging.WARNING):
        """
        Removes orphan assets in the Immich database. Orphan assets are assets found in Immich database but not found in disk.

        Returns how many orphan got removed.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # login_immich
            self.login(log_level=log_level)

            def filter_entities(response_json, entity_type):
                return [
                    {'pathValue': entity['pathValue'], 'entityId': entity['entityId'], 'entityType': entity['entityType']}
                    for entity in response_json.get('orphans', []) if entity.get('entityType') == entity_type
                ]

            if not self.IMMICH_API_KEY_ADMIN or not self.IMMICH_USER_API_KEY:
                LOGGER.error(f"ERROR   : Both admin and user API keys are required.")
                # logout_immich
                self.logout(log_level=log_level)
                return 0

            immich_parsed_url = urlparse(self.IMMICH_URL)
            base_url = f'{immich_parsed_url.scheme}://{immich_parsed_url.netloc}'
            api_url = f'{base_url}/api'
            file_report_url = api_url + '/reports'
            headers = {'x-api-key': self.IMMICH_API_KEY_ADMIN}

            print()
            spinner = Halo(text='Retrieving list of orphaned media assets...', spinner='dots')
            spinner.start()

            total_removed_assets = 0
            try:
                response = requests.get(file_report_url, headers=headers)
                response.raise_for_status()
                spinner.succeed('Success!')
            except requests.exceptions.RequestException as e:
                spinner.fail(f'Failed to fetch assets: {str(e)}')
                # logout_immich
                self.logout(log_level=log_level)
                return 0


            orphan_media_assets = filter_entities(response.json(), 'asset')
            num_entries = len(orphan_media_assets)

            if num_entries == 0:
                LOGGER.info(f"INFO    : No orphaned media assets found.")
                # logout_immich
                self.logout(log_level=log_level)
                return total_removed_assets

            if user_confirmation:
                table_data = [[asset['pathValue'], asset['entityId']] for asset in orphan_media_assets]
                LOGGER.info(f"INFO    : {tabulate(table_data, headers=['Path Value', 'Entity ID'], tablefmt='pretty')}")
                LOGGER.info("")

                summary = f'There {"is" if num_entries == 1 else "are"} {num_entries} orphaned media asset{"s" if num_entries != 1 else ""}. Would you like to remove {"them" if num_entries != 1 else "it"} from Immich? (yes/no): '
                user_input = input(summary).lower()
                LOGGER.info("")

                if user_input not in ('y', 'yes'):
                    LOGGER.info(f"INFO    : Exiting without making any changes.")
                    # logout_immich
                    self.logout(log_level=log_level)
                    return 0

            headers['x-api-key'] = self.IMMICH_USER_API_KEY  # Use user API key for deletion
            with tqdm(total=num_entries, desc="INFO    : Removing orphaned media assets", unit="asset") as progress_bar:
                for asset in orphan_media_assets:
                    entity_id = asset['entityId']
                    asset_url = f'{api_url}/assets'
                    remove_payload = json.dumps({'force': True, 'ids': [entity_id]})
                    headers = {'Content-Type': 'application/json', 'x-api-key': self.IMMICH_USER_API_KEY}
                    try:
                        response = requests.remove(asset_url, headers=headers, data=remove_payload)
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        if response.status_code == 400:
                            LOGGER.warning(f"WARNING : Failed to remove asset {entity_id} due to potential API key mismatch. Ensure you're using the asset owners API key as the User API key.")
                        else:
                            LOGGER.warning(f"WARNING : Failed to remove asset {entity_id}: {str(e)}")
                        continue
                    
                    progress_bar.update(1)
                    total_removed_assets += 1
            LOGGER.info(f"INFO    : Orphaned media assets removed successfully!")
            # logout_immich
            self.logout(log_level=log_level)
            return total_removed_assets


    ###########################################################################
    #                     REMOVE ALL ASSETS / ALL ALBUMS                      #
    ###########################################################################
    def remove_all_assets(self, log_level=logging.WARNING):
        """
        Removes ALL assets in Immich Photos (in batches of 250 if needed) and then removes empty albums.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns (assets_removed, albums_removed)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.info(f"INFO    : Getting list of asset(s) to remove...")

            # Collect
            all_assets_items = self.get_all_assets(log_level=log_level)
            all_assets_items_withDeleted = self.get_all_assets(withDeleted=True, log_level=log_level)
            all_assets_items.extend(all_assets_items_withDeleted)

            total_assets_found = len(all_assets_items)
            if total_assets_found == 0:
                LOGGER.warning(f"WARNING : No Assets found in Immich Database.")
            LOGGER.info(f"INFO    : Found {total_assets_found} asset(s) to remove.")

            assets_ids = []
            for asset in all_assets_items:
                asset_id = asset.get("id")
                if not asset_id:
                    continue
                assets_ids.append(asset_id)

            total_removed_assets = 0
            BATCH_SIZE = min(250, len(assets_ids))

            # Delete in batches
            if assets_ids:
                with tqdm(total=total_assets_found, desc="INFO    : Removing assets", unit=" assets") as pbar:
                    for i in range(0, len(assets_ids), BATCH_SIZE):
                        batch = assets_ids[i:i + BATCH_SIZE]
                        removed_count = self.remove_assets(batch, log_level=logging.WARNING)
                        total_removed_assets += removed_count
                        pbar.update(len(batch))

            LOGGER.info(f"INFO    : Getting empty albums to remove...")
            total_removed_albums = self.remove_empty_albums(log_level=logging.WARNING)

            self.logout(log_level=log_level)
            LOGGER.info(f"INFO    : Total Assets removed: {total_removed_assets}")
            LOGGER.info(f"INFO    : Total Albums removed: {total_removed_albums}")

            return total_removed_assets, total_removed_albums


    def remove_all_albums(self, removeAlbumsAssets=False, log_level=logging.WARNING):
        """
        Removes all albums and optionally also all their associated assets.

        Args:
            removeAlbumsAssets (bool): If True, removes also all the assets associated to all albums
            log_level (logging.LEVEL): log_level for logs and console

        Returns (#albums_removed, #assets_removed).
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            albums = self.get_albums_owned_by_user(log_level=log_level)
            if not albums:
                LOGGER.info("INFO    : No albums found.")
                self.logout(log_level=log_level)
                return 0, 0

            total_removed_albums = 0
            total_removed_assets = 0

            for album in tqdm(albums, desc=f"INFO    : Searching for Albums to remove", unit=" albums"):
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                album_assets_ids = []

                if removeAlbumsAssets:
                    album_assets = self.get_album_assets(album_id, log_level=log_level)
                    for asset in album_assets:
                        asset_id = asset.get("id")
                        if asset_id:
                            album_assets_ids.append(asset_id)
                    self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                    total_removed_assets += len(album_assets_ids)

                if self.remove_album(album_id, album_name, log_level=logging.WARNING):
                    total_removed_albums += 1

            LOGGER.info(f"INFO    : Getting empty albums to remove...")
            total_removed_albums += self.remove_empty_albums(log_level=logging.WARNING)

            LOGGER.info(f"INFO    : Removed {total_removed_albums} albums.")
            if removeAlbumsAssets:
                LOGGER.info(f"INFO    : Removed {total_removed_assets} assets associated to albums.")

            self.logout(log_level=log_level)
            return total_removed_albums, total_removed_assets

##############################################################################
#                                END OF CLASS                                #
##############################################################################



##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    from Utils import change_workingdir
    change_workingdir()

    # Create the Object
    immich = ClassImmichPhotos()

    # 0) Read configuration and log in
    immich.read_config_file('Config.ini')
    immich.login()

    # # 1) Example: Remove empty albums
    # print("\n=== EXAMPLE: remove_empty_albums() ===")
    # removed = immich.remove_empty_albums(log_level=logging.DEBUG)
    # print(f"[RESULT] Empty albums removed: {removed}")
    #
    # # 2) Example: Remove duplicate albums
    # print("\n=== EXAMPLE: remove_duplicates_albums() ===")
    # duplicates = immich.remove_duplicates_albums(log_level=logging.DEBUG)
    # print(f"[RESULT] Duplicate albums removed: {duplicates}")
    #
    # # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\No-Albums'
    # print("\n=== EXAMPLE: upload_no_albums() ===")
    # big_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\No-Albums"
    # immich.upload_no_albums(big_folder, log_level=logging.DEBUG)
    #
    # # 4) Example: Create albums from subfolders in 'r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums'
    # print("\n=== EXAMPLE: upload_albums() ===")
    # input_albums_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums"
    # immich.upload_albums(input_albums_folder, log_level=logging.DEBUG)
    #
    # # 5) Example: Download all photos from ALL albums
    print("\n=== EXAMPLE: download_albums() ===")
    # total = download_albums('ALL', output_folder="Downloads_Immich")
    total_albums, total_assets = immich.download_albums("1994 - Recuerdos", output_folder="Downloads_Immich", log_level=logging.DEBUG)
    print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums} different albbums.")
    #
    # # 6) Example: Download everything in the structure /Albums/<albumName>/ + /No-Albums/yyyy/mm
    # print("\n=== EXAMPLE: download_ALL() ===")
    # # total_struct = download_ALL(output_folder="Downloads_Immich")
    # total_albums_downloaded, total_assets_downloaded = immich.download_ALL(output_folder="Downloads_Immich", log_level=logging.DEBUG)
    # print(f"[RESULT] Bulk download completed. \nTotal albums: {total_albums_downloaded}\nTotal assets: {total_assets_downloaded}.")
    #
    # # 7) Example: Remove Orphan Assets
    # immich.remove_orphan_assets(user_confirmation=True, log_level=logging.DEBUG)
    #
    # # 8) Example: Remove ALL Assets
    # immich.remove_all_assets(log_level=logging.DEBUG)
    #
    # # 9) Example: Remove ALL Assets
    # immich.remove_all_albums(removeAlbumsAssets=True, log_level=logging.DEBUG)
    #
    # # 10) Local logout
    # immich.logout()
