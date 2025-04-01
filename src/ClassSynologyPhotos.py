# -*- coding: utf-8 -*-

"""
----------------------
ClassSynologyPhotos.py
----------------------
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
     - download_ALL()
"""

# ClassSynologyPhotos.py
# -*- coding: utf-8 -*-

"""
Single-class version of ClassSynologyPhotos.py:
 - Preserves original log messages without modifying their text.
 - All docstrings/comments in English.
 - Imports CustomLogger.set_log_level, Utils.update_metadata, etc. remain outside the class.
 - Uses a global LOGGER from GlobalVariables inside the class constructor.
"""

import os
import sys
import fnmatch
import requests
import json
import urllib3
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime
import time
import logging
import inspect

from Utils import update_metadata, convert_to_list, convert_asset_ids_to_str, get_unique_items, organize_files_by_date, tqdm, iso8601_to_epoch

# We also keep references to your custom logger context manager and utility functions:
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER, ARGS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassSynologyPhotos:
    """
    Encapsulates all functionality from ClassSynologyPhotos.py into a single class
    that uses a global LOGGER from GlobalVariables. It maintains original log messages
    and docstrings are now in English.
    """

    def __init__(self, account_id=1):
        """
        Constructor that initializes what were previously global variables.
        Also imports the global LOGGER from GlobalVariables.
        """
        self.ACCOUNT_ID = str(account_id)  # Used to identify wich Account to use from the configuration file
        if account_id not in [1, 2]:
            LOGGER.error(f"ERROR   : Cannot create Immich Photos object with ACCOUNT_ID: {account_id}. Valid valies are [1, 2]. Exiting...")
            sys.exit(-1)

        # Variables that were previously global:
        self.CONFIG = {}
        self.SYNOLOGY_URL = None
        self.SYNOLOGY_USERNAME = None
        self.SYNOLOGY_PASSWORD = None

        self.SESSION = None
        self.SID = None
        self.SYNO_TOKEN_HEADER = {}

        # Allowed extensions:
        self.ALLOWED_SIDECAR_EXTENSIONS = []
        self.ALLOWED_PHOTO_EXTENSIONS = [
            '.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.3fr', '.arw', '.cr2', '.cr3', '.crw', '.dcr',
            '.dng', '.erf', '.k25', '.kdc', '.mef', '.mos', '.mrw', '.nef', '.orf', '.ptx', '.pef',
            '.raf', '.raw', '.rw2', '.sr2', '.srf', '.TIFF', '.HEIC'
        ]
        self.ALLOWED_VIDEO_EXTENSIONS = [
            '.3G2', '.3GP', '.ASF', '.AVI', '.DivX', '.FLV', '.M4V',
            '.MOV', '.MP4', '.MPEG', '.MPG', '.MTS', '.M2TS', '.M2T',
            '.QT', '.WMV', '.XviD'
        ]
        # Lowercase them:
        self.ALLOWED_PHOTO_EXTENSIONS = [ext.lower() for ext in self.ALLOWED_PHOTO_EXTENSIONS]
        self.ALLOWED_VIDEO_EXTENSIONS = [ext.lower() for ext in self.ALLOWED_VIDEO_EXTENSIONS]
        self.ALLOWED_MEDIA_EXTENSIONS = self.ALLOWED_PHOTO_EXTENSIONS + self.ALLOWED_VIDEO_EXTENSIONS
        self.ALLOWED_EXTENSIONS = self.ALLOWED_MEDIA_EXTENSIONS

        # Create a cache dictionary of albums_owned_by_user to save in memmory all the albums owned by this user to avoid multiple calls to method get_albums_ownned_by_user()
        self.albums_owned_by_user = {}

        # Read the Config File to get CLIENT_ID
        self.read_config_file()
        self.CLIENT_ID = self.get_user_mail()

        self.CLIENT_NAME = f'Synology Photos ({self.CLIENT_ID})'


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

            # Load CONFIG for Synology Photos section from config_file
            section_to_load = 'Synology Photos'
            conf = load_config(config_file=config_file, section_to_load=section_to_load)
            self.CONFIG[section_to_load] = conf.get(section_to_load)

            # Extract values for Synology from self.CONFIG
            self.SYNOLOGY_URL = self.CONFIG.get(section_to_load).get('SYNOLOGY_URL', None)
            self.SYNOLOGY_USERNAME = self.CONFIG.get(section_to_load).get(f'SYNOLOGY_USERNAME_{self.ACCOUNT_ID}', None)      # Read the configuration for the user account given by the suffix ACCAUNT_ID
            self.SYNOLOGY_PASSWORD = self.CONFIG.get(section_to_load).get(f'SYNOLOGY_PASSWORD_{self.ACCOUNT_ID}', None)      # Read the configuration for the user account given by the suffix ACCAUNT_ID

            if not self.SYNOLOGY_URL or self.SYNOLOGY_URL.strip() == '':
                LOGGER.warning(f"WARNING : SYNOLOGY_URL not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_URL'] = input("\nEnter SYNOLOGY_URL: ")
                self.SYNOLOGY_URL = self.CONFIG['SYNOLOGY_URL']

            if not self.SYNOLOGY_USERNAME or self.SYNOLOGY_USERNAME.strip() == '':
                LOGGER.warning(f"WARNING : SYNOLOGY_USERNAME not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_USERNAME'] = input("\nEnter SYNOLOGY_USERNAME: ")
                self.SYNOLOGY_USERNAME = self.CONFIG['SYNOLOGY_USERNAME']

            if not self.SYNOLOGY_PASSWORD or self.SYNOLOGY_PASSWORD.strip() == '':
                LOGGER.warning(f"WARNING : SYNOLOGY_PASSWORD not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_PASSWORD'] = input("\nEnter SYNOLOGY_PASSWORD: ")
                self.SYNOLOGY_PASSWORD = self.CONFIG['SYNOLOGY_PASSWORD']

            LOGGER.info("")
            LOGGER.info(f"INFO    : Synology Config Read:")
            LOGGER.info(f"INFO    : ---------------------")
            masked_password = '*' * len(self.SYNOLOGY_PASSWORD)
            LOGGER.info(f"INFO    : SYNOLOGY_URL              : {self.SYNOLOGY_URL}")
            LOGGER.info(f"INFO    : SYNOLOGY_USERNAME         : {self.SYNOLOGY_USERNAME}")
            LOGGER.info(f"INFO    : SYNOLOGY_PASSWORD         : {masked_password}")

            return self.CONFIG


    ###########################################################################
    #                         AUTHENTICATION / LOGOUT                         #
    ###########################################################################
    def login(self, use_syno_token=False, log_level=logging.INFO):
        """
        Logs into the NAS and returns the active session with the SID and Synology DSM URL.

        If already logged in, reuses the existing session.

        Args:
            use_syno_token (bool): Define if you want to use X-SYNO-TOKEN in the header to maintain the session
            log_level (logging.LEVEL): log_level for logs and console

        Returns (self.SESSION, self.SID) or (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
        """
        with set_log_level(LOGGER, log_level):
            try:
                if self.SESSION and self.SID and self.SYNO_TOKEN_HEADER:
                    return (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
                elif self.SESSION and self.SID:
                    return (self.SESSION, self.SID)

                self.read_config_file(log_level=log_level)
                LOGGER.info("")
                LOGGER.info(f"INFO    : Authenticating on Synology Photos and getting Session...")

                self.SESSION = requests.Session()
                url = f"{self.SYNOLOGY_URL}/webapi/auth.cgi"

                params = {
                    "api": "SYNO.API.Auth",
                    "version": "6",
                    "method": "login",
                    "account": self.SYNOLOGY_USERNAME,
                    "passwd": self.SYNOLOGY_PASSWORD,
                    "format": "sid",
                }
                if use_syno_token:
                    params.update({"enable_syno_token": "yes"})

                response = self.SESSION.get(url, params=params, verify=False)
                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    self.SID = data["data"]["sid"]
                    self.SESSION.cookies.set("id", self.SID)
                    LOGGER.info(f"INFO    : Authentication Successfully with user/password found in Config file. Cookie properly set with session id.")
                    if use_syno_token:
                        LOGGER.info(f"INFO    : SYNO_TOKEN_HEADER created as global variable. You must include 'SYNO_TOKEN_HEADER' in your request to work with this session.")
                        self.SYNO_TOKEN_HEADER = {
                            "X-SYNO-TOKEN": data["data"]["synotoken"],
                        }
                        return (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
                    else:
                        return (self.SESSION, self.SID)
                else:
                    LOGGER.error(f"ERROR   : Unable to authenticate with the provided Synology Photos data: {data}")
                    sys.exit(-1)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while login into Synology Photos!. {e}")
            

    def logout(self, log_level=logging.INFO):
        """
        Logout from the Synology NAS and clears the active session and SID.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            try:
                if self.SESSION and self.SID:
                    url = f"{self.SYNOLOGY_URL}/webapi/auth.cgi"
                    params = {
                        "api": "SYNO.API.Auth",
                        "version": "3",
                        "method": "logout",
                    }
                    response = self.SESSION.get(url, params=params, verify=False)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("success"):
                        LOGGER.info("INFO    : Session closed successfully.")
                        self.SESSION = None
                        self.SID = None
                        self.SYNO_TOKEN_HEADER = {}
                    else:
                        LOGGER.error("ERROR   : Unable to close session in Synology NAS.")
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while logout from Synology Photos!. {e}")
            

    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def get_supported_media_types(self, type='media', log_level=logging.INFO):
        """
        Returns the supported media/sidecar extensions as for Synology Photos
        """
        with set_log_level(LOGGER, log_level):
            try:
                if type.lower() == 'media':
                    supported_types = self.ALLOWED_MEDIA_EXTENSIONS
                    LOGGER.debug(f"DEBUG   : Supported media types: '{supported_types}'.")
                elif type.lower() == 'image':
                    supported_types = self.ALLOWED_PHOTO_EXTENSIONS
                    LOGGER.debug(f"DEBUG   : Supported image types: '{supported_types}'.")
                elif type.lower() == 'video':
                    supported_types = self.ALLOWED_VIDEO_EXTENSIONS
                    LOGGER.debug(f"DEBUG   : Supported video types: '{supported_types}'.")
                elif type.lower() == 'sidecar':
                    supported_types = self.ALLOWED_SIDECAR_EXTENSIONS
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
            try:
                return self.SYNOLOGY_USERNAME
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting user id. {e}")

    def get_user_mail(self, log_level=logging.INFO):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            try:
                return self.SYNOLOGY_USERNAME
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting user mail. {e}")
            

    def get_geocoding(self, log_level=logging.INFO):
        """
        Gets the Geocoding list.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        Returns:
             int: List of Geocoding used in the database.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)
                offset = 0
                limit = 5000
                geocoding_list = []
                while True:
                    params = {
                        "api": "SYNO.Foto.Browse.Geocoding",
                        "method": "list",
                        "version": "1",
                        "offset": offset,
                        "limit": limit
                    }
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    resp.raise_for_status()
                    data = resp.json()
                    if data["success"]:
                        geocoding_list.extend(data["data"]["list"])
                    else:
                        LOGGER.error("ERROR   : Failed to get Geocoding list: ", data)
                        return None
                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit
                return geocoding_list
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Geocoding List from Synology Photos. {e}")

    def get_ids_for_place(self, place, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):
            geocoding_list = self.get_geocoding(log_level=log_level)
            result_ids = set()

            for item in geocoding_list:
                # Coincidencia con el país
                if item.get("country") == place:
                    result_ids.add(item.get("country_id"))
                    result_ids.add(item.get("id"))

                # Coincidencia con primer nivel (por ejemplo, ciudad o región)
                if item.get("first_level") == place:
                    result_ids.add(item.get("id"))

                # Coincidencia con el nombre del lugar
                if item.get("name") == place:
                    result_ids.add(item.get("id"))

                # Coincidencia con segundo nivel si aplica
                if item.get("second_level") == place:
                    result_ids.add(item.get("id"))

            return list(result_ids)

    ###########################################################################
    #                            ALBUMS FUNCTIONS                             #
    ###########################################################################
    def create_album(self, album_name, log_level=logging.INFO):
        """
        Creates a new album in Synology Photos with the specified name.

        Args:
            album_name (str): Album name to be created.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: New album ID or None if it fails
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    "api": "SYNO.Foto.Browse.NormalAlbum",
                    "method": "create",
                    "version": "3",
                    "name": f'"{album_name}"',
                }
                resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                resp.raise_for_status()
                data = resp.json()

                if not data["success"]:
                    LOGGER.error(f"ERROR   : Unable to create album '{album_name}': {data}")
                    return None

                album_id = data["data"]["album"]["id"]
                LOGGER.info(f"INFO    : Album '{album_name}' created with ID: {album_id}.")
                return album_id
            except Exception as e:
                LOGGER.warning(f"WARNING : Cannot create album: '{album_name}' due to API call error. Skipped! {e}")


    def remove_album(self, album_id, album_name, log_level=logging.INFO):
        """
        Removes an album in Synology Photos by its album ID.

        Args:
            album_id (str): ID of the album to delete.
            album_name (str): Name of the album to delete.
            log_level (logging.LEVEL): log_level for logs and console

        Returns True on success, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    "api": "SYNO.Foto.Browse.Album",
                    "method": "delete",
                    "version": "3",
                    "id": f"[{album_id}]",
                    "name": album_name,
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                response.raise_for_status()
                data = response.json()
                success = True
                if not data["success"]:
                    LOGGER.warning(f"WARNING : Could not delete album {album_id}: {data}")
                    success = False
                return success
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing Album from Synology Photos. {e}")


    def get_albums_owned_by_user(self, log_level=logging.INFO):
        """
        Get all albums in Synology Photos for the current user.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of dictionaries where each item has below structure:
                    {
                      "id": <str>,
                      "albumName": <str>,
                      "...",
                    }
            None on error
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                album_list = []
                while True:
                    params = {
                        "api": "SYNO.Foto.Browse.NormalAlbum",
                        "method": "list",
                        "version": "3",
                        "offset": offset,
                        "limit": limit
                    }
                    r = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    r.raise_for_status()
                    data = r.json()

                    if data["success"]:
                        album_list.extend(data["data"]["list"])
                    else:
                        LOGGER.error("ERROR   : Failed to list albums: ", data)
                        return None

                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit

                # Replace the key "name" by "albumName" to make it equal to Immich Photos
                for item in album_list:
                    if "name" in item:
                        item["albumName"] = item.pop("name")

                albums_filtered = []
                for album in album_list:
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    album_assets = self.get_album_assets(album_id, album_name, log_level=log_level)
                    if len(album_assets) > 0:
                        albums_filtered.append(album)
                return albums_filtered
            except Exception as e:
                LOGGER.warning(f"WARNING : Cannot get albums due to API call error. Skipped! {e}")


    def get_albums_including_shared_with_user(self, log_level=logging.INFO):
        """
        Get both own and shared albums in Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of dictionaries where each item has below structure:
                    {
                      "id": <str>,
                      "albumName": <str>,
                      "...",
                    }
            None on error
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

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

                    r = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    data = r.json()
                    if not data.get("success"):
                        LOGGER.error("ERROR   : Failed to list own albums:", data)
                        return None
                    album_list.extend(data["data"]["list"])
                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit
            except Exception as e:
                LOGGER.error("ERROR   : Exception while listing own albums. {e}")
                return None
            

            # Replace the key "name" by "albumName" to make it equal to Immich Photos
            for album in album_list:
                if "name" in album:
                    album["albumName"] = album.pop("name")

            albums_filtered = []
            for album in album_list:
                album_id = album.get('id')
                album_name = album.get("albumName", "")
                album_assets = self.get_album_assets(album_id, album_name, log_level=log_level)
                if len(album_assets) > 0:
                    albums_filtered.append(album)
            return albums_filtered


    def get_album_assets_size(self, album_id, album_name, log_level=logging.INFO):
        """
        Gets the total size (bytes) of all assets in an album.

        Args:
            album_id (str): Album ID
            album_name (str): Album Name
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Album Size or -1 on error.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

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
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    resp.raise_for_status()
                    data = resp.json()

                    if not data["success"]:
                        LOGGER.warning(f"WARNING : Cannot list files for album: '{album_name}' due to API call error. Skipped!")
                        return -1

                    album_items.append(data["data"]["list"])
                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit

                for sets in album_items:
                    for item in sets:
                        album_size += item.get("filesize", 0)

                return album_size
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Album Assets from Synology Photos. {e}")
            

    def get_album_assets_count(self, album_id, album_name, log_level=logging.INFO):
        """
        Gets the number of assets in an album.

        Args:
            album_id (str): Album ID
            album_name (str): Album Name
            log_level (logging.LEVEL): log_level for logs and console
        Returns:
             int: Album Items Count or -1 on error.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    "api": "SYNO.Foto.Browse.Item",
                    "method": "count",
                    "version": "4",
                    "album_id": album_id,
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                response.raise_for_status()
                data = response.json()

                if not data["success"]:
                    LOGGER.warning(f"WARNING : Cannot count files for album: '{album_name}' due to API call error. Skipped!")
                    return -1
                return data["data"]["count"]
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Album Assets count from Synology Photos. {e}")


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
            try:
                # First, check if the album is already in the user's dictionary
                if album_name in self.albums_owned_by_user:
                    album_exists = True
                    album_id = self.albums_owned_by_user[album_name]
                else:
                    album_exists = False
                    album_id = None
                    albums = self.get_albums_owned_by_user(log_level=log_level)
                    for album in albums:
                        if album_name == album.get("albumName"):
                            album_exists = True
                            album_id = album.get("id")
                            self.albums_owned_by_user[album_name] = album_id  # Cache it for future use
                            break
                return album_exists, album_id
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while checking if Album exists on Synology Photos. {e}")


    ###########################################################################
    #                            ASSETS FILTERING                             #
    ###########################################################################
    def filter_assets(self, assets, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):
            # Get the values from the arguments (if exists)
            # type = ARGS.get('asset-type', None)
            # country = ARGS.get('country', None)
            # city = ARGS.get('city', None)
            # people = ARGS.get('people', None)
            takenAfter = ARGS.get('from-date', None)
            takenBefore = ARGS.get('to-date', None)

            # Convert dates from iso to epoch
            takenAfter = iso8601_to_epoch(takenAfter)
            takenBefore = iso8601_to_epoch(takenBefore)

            if not takenAfter: takenAfter = 0                   # Fecha más antigua aceptada por muchas APIs: 1970-01-01
            if not takenBefore: takenBefore = int(time.time())  # Fecha actual

            filtered_assets = []
            for asset in assets:
                time_value = asset.get('time', -1)
                if takenAfter <= time_value <= takenBefore:
                    filtered_assets.append(asset)
            return filtered_assets


    ###########################################################################
    #                        ASSETS (PHOTOS/VIDEOS)                           #
    ###########################################################################
    def get_all_assets(self, log_level=logging.INFO):
        """
        Lists all assets in Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets (dict) in the entire library or Empty list on error.
        """
        with set_log_level(LOGGER, log_level):
            try:
                # Get the values from the arguments (if exists)
                takenAfter = ARGS.get('from-date', None)
                takenBefore = ARGS.get('to-date', None)
                type = ARGS.get('asset-type', None)
                country = ARGS.get('country', None)
                city = ARGS.get('city', None)
                people = ARGS.get('people', None)

                # Convert the values from iso to epoch
                takenAfter = iso8601_to_epoch(takenAfter)
                takenBefore = iso8601_to_epoch(takenBefore)

                geocoding_country_list = []
                geocoding_city_list = []
                if country: geocoding_country_list = self.get_ids_for_place(country)
                if city: geocoding_city_list = self.get_ids_for_place(city)

                geocoding_list = geocoding_country_list + geocoding_city_list

                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                all_assets = []
                while True:
                    params = {
                        'api': 'SYNO.Foto.Browse.Item',
                        # 'version': '4',
                        # 'method': 'list',
                        'version': '2',
                        'method': 'list_with_filter',
                        'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                        'offset': offset,
                        'limit': limit,
                    }

                    # Add time to params only if takenAfter or takenBefore has some values
                    time_dic = {}
                    if takenAfter:  time_dic["start_time"] = takenAfter
                    if takenBefore: time_dic["end_time"] = takenBefore
                    if time_dic: params["time"] = json.dumps([time_dic])

                    # Add geocoding key if geocoding_list has some value
                    if geocoding_list: params["geocoding"] = json.dumps(geocoding_list)

                    # Add types to params if have been providen
                    types = []
                    if type:
                        if type.lower() in ['photo', 'photos']:
                            types.append(0)
                        if type.lower() in ['video', 'videos']:
                            types.append(1)
                    if types: params["item_type"] = types

                    try:
                        resp = self.SESSION.get(url, headers=headers, params=params, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            LOGGER.error(f"ERROR   : Failed to list assets")
                            return []
                        all_assets.extend(data["data"]["list"])
                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        LOGGER.error(f"ERROR   : Exception while listing assets {e}")
                        return []

                return all_assets
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting all Assets from Synology Photos. {e}")
            

    def get_album_assets(self, album_id, album_name=None, log_level=logging.INFO):
        """
        Get assets in a specific album.

        Args:
            album_id (str): ID of the album.
            album_name (str): Name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets in the album (dict objects). [] if no assets found.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                album_assets = []

                while True:
                    params = {
                        'api': 'SYNO.Foto.Browse.Item',
                        'version': '4',
                        'method': 'list',
                        'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                        'album_id': album_id,
                        'offset': offset,
                        'limit': limit,
                    }

                    try:
                        resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            if album_name:
                                LOGGER.error(f"ERROR   : Failed to list photos in the album '{album_name}'")
                            else:
                                LOGGER.error(f"ERROR   : Failed to list photos in the album ID={album_id}")
                            return []
                        album_assets.extend(data["data"]["list"])

                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        if album_name:
                            LOGGER.error(f"ERROR   : Exception while listing photos in the album '{album_name}' {e}")
                        else:
                            LOGGER.error(f"ERROR   : Exception while listing photos in the album ID={album_id} {e}")
                        return []

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                return filtered_album_assets
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Album Assets from Synology Photos. {e}")


    def get_album_shared_assets(self, album_passphrase, album_id, album_name=None, log_level=logging.INFO):
        """
        Get assets in a specific shared album.

        Args:
            album_passphrase (str): Shared album passphrase
            album_id (str): ID of the album.
            album_name (str): Name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets in the album (dict objects). [] if no assets found.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                album_assets = []

                while True:
                    params = {
                        'api': 'SYNO.Foto.Browse.Item',
                        'version': '4',
                        'method': 'list',
                        'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                        'passphrase': album_passphrase,
                        "offset": offset,
                        "limit": limit
                    }
                    try:
                        resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            if album_name:
                                LOGGER.error(f"ERROR   : Failed to list photos in the album '{album_name}'")
                            else:
                                LOGGER.error(f"ERROR   : Failed to list photos in the album ID={album_id}")
                            return []
                        album_assets.extend(data["data"]["list"])

                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        if album_name:
                            LOGGER.error(f"ERROR   : Exception while listing photos in the album '{album_name}' {e}")
                        else:
                            LOGGER.error(f"ERROR   : Exception while listing photos in the album ID={album_id} {e}")
                        return []

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                return filtered_album_assets
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Album Assets from Synology Photos. {e}")


    def get_no_albums_assets(self, log_level=logging.WARNING):
        """
        Get assets not associated to any album from Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_without_albums
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                all_assets = self.get_all_assets(log_level=logging.INFO)
                album_asset = self.get_all_albums_assets(log_level=logging.INFO)
                # Use get_unique_items from your Utils to find items that are in all_assets but not in album_asset
                assets_without_albums = get_unique_items(all_assets, album_asset, key='filename')
                LOGGER.info(f"INFO    : Number of all_assets without Albums associated: {len(assets_without_albums)}")
                return assets_without_albums
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting No-Albums Assets from Synology Photos. {e}")


    def get_all_albums_assets(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: Albums Assets
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

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
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting All Albums Assets from Synology Photos. {e}")
            

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=logging.WARNING):
        """
        Adds assets (asset_ids) to an album.

        Args:
            album_id (str): The ID of the album to which we add assets.
            asset_ids (list or str): The IDs of assets to add.
            album_name (str): The name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Number of assets added to the album
        """
        with set_log_level(LOGGER, log_level):
            try:
                if not asset_ids:
                    LOGGER.warning(f"WARNING : No assets found to add to Album ID: '{album_id}'. Skipped!")
                    return -1
                # asset_ids = convert_asset_ids_to_str(asset_ids)
                asset_ids = convert_to_list(asset_ids)

                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                total_added = len(asset_ids) if isinstance(asset_ids, list) else 1
                if not total_added > 0:
                    if album_name:
                        LOGGER.warning(f"WARNING : No assets found to add to Album: '{album_name}'. Skipped!")
                    else:
                        LOGGER.warning(f"WARNING : No assets found to add to Album ID: '{album_id}'. Skipped!")
                    return -1

                params = {
                    "api": "SYNO.Foto.Browse.NormalAlbum",
                    "method": "add_item",
                    "version": "1",
                    "id": album_id,
                    "item": f"{asset_ids}"
                }
                resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                resp.raise_for_status()
                data = resp.json()

                if not data["success"]:
                    if album_name:
                        LOGGER.warning(f"WARNING : Cannot add assets to album: '{album_name}' due to API call error. Skipped!")
                    else:
                        LOGGER.warning(f"WARNING : Cannot add assets to album ID: '{album_id}' due to API call error. Skipped!")
                    return -1
                if album_name:
                    LOGGER.info(f"INFO    : {total_added} Assets successfully added to album: '{album_name}'.")
                else:
                    LOGGER.info(f"INFO    : {total_added} Assets successfully added to album ID: '{album_id}'.")
                return total_added

            except Exception as e:
                LOGGER.warning(f"WARNING : Cannot add Assets to album: '{album_name}' due to API call error. Skipped!")
            

    # TODO: Complete this method
    def get_duplicates_assets(self, log_level=logging.INFO):
        """
        Returns the list of duplicate assets from Synology
        """
        with set_log_level(LOGGER, log_level):
            try:
                return []
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting duplicates Assets from Synology Photos. {e}")


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
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

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
                    response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    data = response.json()
                    if not data.get("success"):
                        LOGGER.error(f"ERROR   : Failed to remove assets")
                        return 0
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception while removing assets {e}")
                    return 0
                

                task_id = data.get('data', {}).get('task_info', {}).get('id')
                removed_count = len(asset_ids)

                # Wait for background remove task to finish
                self.wait_for_remove_task(task_id, log_level=log_level)
                return removed_count
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing Assets from Synology Photos. {e}")
            

    # TODO: Complete this method
    def remove_duplicates_assets(self, log_level=logging.INFO):
        """
        Removes duplicate assets in the Synology database. Returns how many duplicates got removed.
        """
        with set_log_level(LOGGER, log_level):
            try:
                return 0
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing duplicates assets from Synology Photos. {e}")
            

    def upload_asset(self, file_path, log_level=logging.INFO):
        """
        Uploads a local file (photo/video) to Synology Photos.

        Args:
            file_path (str): file_path of the asset to upload
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: the asset_id if success, or None if it fails or is an unsupported extension.
            bool: is_duplicated = False if success, or None if it fails or is an unsupported extension.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"El archivo '{file_path}' no existe.")

                filename, ext = os.path.splitext(file_path)
                ext = ext.lower()
                if ext not in self.ALLOWED_MEDIA_EXTENSIONS:
                    if ext in self.ALLOWED_SIDECAR_EXTENSIONS:
                        return None, None
                    else:
                        LOGGER.warning(f"")
                        LOGGER.warning(f"WARNING : File '{file_path}' has an unsupported extension. Skipped.")
                        LOGGER.warning(f"")
                        return None, None

                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                api = "SYNO.Foto.Upload.Item"
                method = "upload"
                version = "1"
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi/SYNO.Foto.Upload.Item?api={api}&method={method}&version={version}"

                mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

                with open(file_path, "rb") as file_:
                    multipart_data = MultipartEncoder(
                        fields=[
                            ("api", f'{api}'),
                            ("method", f'{method}'),
                            ("version", f'{version}'),
                            ("file", (os.path.basename(file_path), file_, mime_type)),
                            ("uploadDestination", '"timeline"'),
                            ("duplicate", '"ignore"'),
                            ("name", f'"{os.path.basename(file_path)}"'),
                            ("mtime", f'{str(int(os.stat(file_path).st_mtime))}'),
                            ("folder", f'["PhotoLibrary"]'),
                        ],
                    )
                    headers.update({"Content-Type": multipart_data.content_type})

                    response = self.SESSION.post(url, data=multipart_data, headers=headers, verify=False)
                    response.raise_for_status()
                    data = response.json()
                    if not data["success"]:
                        LOGGER.warning(f"WARNING : Cannot upload asset: '{file_path}' due to API call error. Skipped!")
                        return None, None
                    else:
                        asset_id = data["data"].get("id")
                        return asset_id, False

            except Exception as e:
                LOGGER.warning(f"WARNING : Cannot upload asset: '{file_path}' due to API call error. Skipped!")
            

    def download_asset(self, asset_id, asset_filename, asset_time, album_passphrase=None, download_folder="Downloaded_Synology", log_level=logging.INFO):
        """
        Downloads an asset (photo/video) from Synology Photos to a local folder,
        preserving the original timestamp if available.

        Args:
            asset_id (int): ID of the asset to download.
            asset_filename (str): Name of the file to save.
            asset_time (int or str): UNIX epoch or ISO string time of the asset.
            album_passphrase (str): Passphrase for shared albums.
            download_folder (str): Path where the file will be saved.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: 1 if download succeeded, 0 if failed.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                os.makedirs(download_folder, exist_ok=True)

                if isinstance(asset_time, str):
                    asset_time = datetime.fromisoformat(asset_time).timestamp()

                if asset_time and asset_time > 0:
                    asset_datetime = datetime.fromtimestamp(asset_time)
                else:
                    asset_datetime = datetime.now()

                file_ext = os.path.splitext(asset_filename)[1].lower()
                file_path = os.path.join(download_folder, asset_filename)

                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    'api': 'SYNO.Foto.Download',
                    'version': '2',
                    'method': 'download',
                    'force_download': 'true',
                    'download_type': 'source',
                    "item_id": f"[{asset_id}]",
                }
                # If is a shared album, we append the passphrase to params
                if album_passphrase:
                    params['passphrase'] = f'"{album_passphrase}"'

                resp = self.SESSION.get(url, params=params, headers=headers, verify=False, stream=True)
                if resp.status_code != 200:
                    LOGGER.error("")
                    LOGGER.error(f"ERROR   : Failed to download asset '{asset_filename}' with ID [{asset_id}]. Status code: {resp.status_code}")
                    return 0

                with open(file_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)

                os.utime(file_path, (asset_time, asset_time))

                if file_ext in self.ALLOWED_MEDIA_EXTENSIONS:
                    update_metadata(file_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"), log_level=logging.ERROR)

                LOGGER.debug("")
                LOGGER.debug(f"DEBUG   : Asset '{asset_filename}' downloaded and saved at {file_path}")
                return 1
            except Exception as e:
                LOGGER.error("")
                LOGGER.error(f"ERROR   : Exception occurred while downloading asset '{asset_filename}' with ID [{asset_id}]. {e}")
                return 0
            


    ###########################################################################
    #                             FOLDERS FUNCTIONS                           #
    #             (This block is exclusive for ClassSynologyPhotos)           #
    ###########################################################################
    def get_root_folder_id(self, log_level=logging.INFO):
        """
        Retrieves the folder_id of the root folder in Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: The ID of the folder (folder_id).
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    "api": "SYNO.Foto.Browse.Folder",
                    "method": "get",
                    "version": "2",
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    LOGGER.error("ERROR   : Cannot obtain Photos Root Folder ID due to an error in the API call.")
                    sys.exit(-1)

                folder_name = data["data"]["folder"]["name"]
                folder_id = str(data["data"]["folder"]["id"])
                if not folder_id or folder_name != "/":
                    LOGGER.error("ERROR   : Cannot obtain Photos Root Folder ID.")
                    sys.exit(-1)
                return folder_id
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while geting root folder ID from Synology Photos. {e}")
            

    def get_folder_id(self, search_in_folder_id, folder_name, log_level=logging.WARNING):
        """
        Retrieves the folder_id of a folder in Synology Photos given the parent folder ID
        and the name of the folder to search for.

        Args:
            search_in_folder_id (str): ID of the Synology Photos folder where the subfolder is located.
            folder_name (str): Name of the folder to search for in the folder structure.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: The ID of the folder (folder_id), or None if not found.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                # 1) get the name of search_in_folder_id
                params = {
                    "api": "SYNO.Foto.Browse.Folder",
                    "method": "get",
                    "version": "2",
                    "id": search_in_folder_id,
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                data = response.json()
                if not data.get("success"):
                    LOGGER.error(f"ERROR   : Cannot obtain name for folder ID '{search_in_folder_id}' due to an error in the API call.")
                    sys.exit(-1)
                search_in_folder_name = data["data"]["folder"]["name"]

                offset = 0
                limit = 5000
                found_id = None
                while True:
                    params_list = {
                        "api": "SYNO.Foto.Browse.Folder",
                        "method": "list",
                        "version": "2",
                        "id": search_in_folder_id,
                        "offset": offset,
                        "limit": limit
                    }
                    resp = self.SESSION.get(url, params=params_list, headers=headers, verify=False)
                    resp.raise_for_status()
                    data_list = resp.json()

                    if not data_list.get("success"):
                        LOGGER.error(f"ERROR   : Cannot obtain ID for folder '{folder_name}' due to an error in the API call.")
                        sys.exit(-1)

                    subfolders_dict = {
                        item["name"].replace(search_in_folder_name, '').replace('/', ''): str(item["id"])
                        for item in data_list["data"]["list"] if "id" in item
                    }

                    if len(data_list["data"]["list"]) < limit or folder_name in subfolders_dict.keys():
                        # might have found it or we are at last chunk
                        found_id = subfolders_dict.get(folder_name)
                        break
                    offset += limit

                if found_id:
                    return found_id
                else:
                    # recursively check subfolders
                    for sf_id in subfolders_dict.values():
                        sub_found = self.get_folder_id(sf_id, folder_name, log_level=log_level)
                        if sub_found:
                            return sub_found
                    return None
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting folder ID from Synology Photos. {e}")
            

    def create_folder(self, folder_name, parent_folder_id=None, log_level=logging.INFO):
        """
        Retrieves the folder ID of a given folder name within a parent folder in Synology Photos.
        If the folder does not exist, it will be created.

        Args:
            folder_name (str): The name of the folder to find or create.
            parent_folder_id (str, optional): The ID of the parent folder.
                If not provided, the root folder of Synology Photos is used.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            str: The folder ID if found or successfully created, otherwise None.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                if not parent_folder_id:
                    photos_root_folder_id = self.get_root_folder_id()
                    parent_folder_id = photos_root_folder_id
                    LOGGER.warning(f"WARNING : Parent Folder ID not provided, using Synology Photos root folder ID: '{photos_root_folder_id}' as parent folder.")

                # Check if the folder already exists
                folder_id = self.get_folder_id(parent_folder_id, folder_name, log_level=log_level)
                if folder_id:
                    # Already exists
                    return folder_id

                # If the folder does not exist, create it
                params = {
                    'api': 'SYNO.Foto.Browse.Folder',
                    'version': '1',
                    'method': 'create',
                    'target_id': parent_folder_id,
                    'name': folder_name
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                data = response.json()

                self.logout(log_level=log_level)
                if data.get("success"):
                    LOGGER.info(f"INFO    : Folder '{folder_name}' successfully created.")
                    return data['data']['folder']['id']
                else:
                    LOGGER.error(f"ERROR   : Failed to create the folder: '{folder_name}'")
                    return None
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while creating folder into Synology Photos. {e}")
            

    def get_folders(self, parent_folder_id, log_level=logging.INFO):
        """
        Lists all subfolders under a specified parent_folder_id in Synology Photos.

        Args:
            parent_folder_id (str): Parent folder ID to get all its subfolders
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            dict: A dictionary with folder IDs as keys and folder names as values.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                folders_dict = {}
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
                    response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    response.raise_for_status()
                    data = response.json()

                    if data["success"]:
                        for item in data["data"]["list"]:
                            if "id" in item:
                                folders_dict[item["id"]] = item["name"]
                    else:
                        LOGGER.error("ERROR   : Failed to list albums: ", data)
                        return {}

                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit

                return folders_dict
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting folders from Synology Photos. {e}")
            

    def remove_folder(self, folder_id, folder_name, log_level=logging.INFO):
        """
        Removes a folder by its ID in Synology Photos.

        Args:
            folder_id (str or list): ID(s) of the folder(s).
            folder_name (str): Name of the folder.
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

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
                    response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    data = response.json()
                    if not data.get("success"):
                        LOGGER.error(f"ERROR   : Failed to remove folder '{folder_name}'")
                        return 0
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception while removing folder '{folder_name}' {e}")
                    return 0
                return len(folder_id)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing Folder from Synology Photos. {e}")
            

    def get_folder_items_count(self, folder_id, folder_name, log_level=logging.INFO):
        """
        Returns the assets count for a specific Synology Photos folder.

        Args:
            folder_id (str): Folder ID
            folder_name (str): Folder Name
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: Folder Items Count or -1 on error.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    'api': 'SYNO.Foto.Browse.Item',
                    'method': 'count',
                    'version': '4',
                    "folder_id": folder_id,
                }
                try:
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    data = resp.json()
                    if not data.get("success"):
                        LOGGER.error(f"ERROR   : Failed to count assets for folder '{folder_name}'.")
                        return -1
                    asset_count = data["data"]["count"]
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception while retrieving assets count for folder '{folder_name}'. {e}")
                    return -1
                return asset_count
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while getting Folder items count from Synology Photos. {e}")
            


    ###########################################################################
    #                         BACKGROUND TASKS MANAGEMENT                     #
    #             (This block is exclusive for ClassSynologyPhotos)           #
    ###########################################################################
    def wait_for_remove_task(self, task_id, log_level=logging.INFO):
        """
        Internal helper to poll a background remove task until done.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            try:
                while True:
                    status = self.check_background_remove_task_finished(task_id, log_level=log_level)
                    if status == 'done' or status is True:
                        LOGGER.info(f'INFO    : Waiting for removing assets to finish...')
                        time.sleep(5)
                        break
                    else:
                        LOGGER.debug(f"DEBUG   : Task not finished yet. Waiting 5 seconds more.")
                        time.sleep(5)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while waitting for remove task to finish in Synology Photos. {e}")


    def check_background_remove_task_finished(self, task_id, log_level=logging.INFO):
        """
        Checks whether a background removal task is finished.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                params = {
                    'api': 'SYNO.Foto.BackgroundTask.Info',
                    'version': '1',
                    'method': 'get_status',
                    'id': f'[{task_id}]'
                }
                try:
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    data = resp.json()
                    if not data.get("success"):
                        LOGGER.error(f"ERROR   : Failed to get removing assets status")
                        return False
                    lst = data['data'].get('list', [])
                    if len(lst) > 0:
                        return lst[0].get('status')
                    else:
                        return True
                except Exception as e:
                    LOGGER.error(f"ERROR   : Exception while checking removing assets status {e}")
                    return False
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while checking if background task has finished in Synology Photos. {e}")
            

    ###########################################################################
    #             MAIN FUNCTIONS TO CALL FROM OTHER MODULES (API)            #
    ###########################################################################
    def upload_albums(self, input_folder, subfolders_exclusion='No-Albums', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        """
        Traverses the subfolders of 'input_folder', creating an album for each valid subfolder (album name equals
        the subfolder name). Within each subfolder, it uploads all files with allowed extensions (based on
        self.ALLOWED_SYNOLOGY_EXTENSIONS) and associates them with the album.
        
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

        Returns: (total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_duplicates_assets_removed)
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                if not os.path.isdir(input_folder):
                    LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
                    return 0, 0, 0, 0

                subfolders_exclusion = convert_to_list(subfolders_exclusion)
                subfolders_inclusion = convert_to_list(subfolders_inclusion) if subfolders_inclusion else []
                total_albums_uploaded = 0
                total_albums_skipped = 0
                total_assets_uploaded = 0
                total_duplicates_assets_removed = 0

                # If 'Albums' is not in subfolders_inclusion, add it (like original code).
                albums_folder_included = any(rel.lower() == 'albums' for rel in subfolders_inclusion)
                if not albums_folder_included:
                    subfolders_inclusion.append('Albums')

                SUBFOLDERS_EXCLUSIONS = ['@eaDir'] + subfolders_exclusion
                valid_folders = []

                for root, folders, _ in os.walk(input_folder):
                    # Filter out excluded folders
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
                        if isinstance(dir_path, bytes):
                            dir_path = dir_path.decode()

                        has_supported_files = any(
                            os.path.splitext(file)[-1].lower() in self.ALLOWED_EXTENSIONS
                            for file in os.listdir(dir_path)
                            if os.path.isfile(os.path.join(dir_path, file))
                        )
                        if not has_supported_files:
                            continue
                        valid_folders.append(dir_path)

                first_level_folders = os.listdir(input_folder)
                if subfolders_inclusion:
                    first_level_folders += subfolders_inclusion

                with tqdm(total=len(valid_folders), smoothing=0.1, desc="INFO    : Uploading Albums from Folders", unit=" folders") as pbar:
                    for subpath in valid_folders:
                        pbar.update(1)
                        new_album_assets_ids = []
                        if not os.path.isdir(subpath):
                            LOGGER.warning(f"WARNING : Could not create album for subfolder '{subpath}'.")
                            total_albums_skipped += 1
                            continue

                        relative_path = os.path.relpath(subpath, input_folder)
                        path_parts = relative_path.split(os.sep)
                        if len(path_parts) == 1:
                            album_name = path_parts[0]
                        else:
                            if path_parts[0] in first_level_folders:
                                album_name = " - ".join(path_parts[1:])
                            else:
                                album_name = " - ".join(path_parts)

                        if album_name:
                            album_id = self.create_album(album_name, log_level=logging.WARNING)
                            if not album_id:
                                LOGGER.warning(f"WARNING : Could not create album for subfolder '{subpath}'.")
                                total_albums_skipped += 1
                                continue
                            else:
                                total_albums_uploaded += 1

                            for file_ in os.listdir(subpath):
                                file_path = os.path.join(subpath, file_)
                                if not os.path.isfile(file_path):
                                    continue
                                ext = os.path.splitext(file_)[-1].lower()
                                if ext not in self.ALLOWED_EXTENSIONS:
                                    continue

                                asset_id = self.upload_asset(file_path, log_level=logging.WARNING)
                                if asset_id:
                                    total_assets_uploaded += 1
                                    # Associate only if ext is photo/video
                                    if ext in self.ALLOWED_MEDIA_EXTENSIONS:
                                        new_album_assets_ids.append(asset_id)
                            if new_album_assets_ids:
                                self.add_assets_to_album(album_id, new_album_assets_ids, album_name=album_name, log_level=logging.WARNING)
                        else:
                            total_albums_skipped += 1

                if remove_duplicates:
                    LOGGER.info("INFO    : Removing Duplicates Assets...")
                    total_duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

                LOGGER.info(f"INFO    : Uploaded {total_albums_uploaded} album(s) from '{input_folder}'.")
                LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} asset(s) from '{input_folder}' to Albums.")
                LOGGER.info(f"INFO    : Skipped {total_albums_skipped} album(s) from '{input_folder}'.")
                LOGGER.info(f"INFO    : Removed {total_duplicates_assets_removed} duplicates asset(s) from Synology Database.")

            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while uploading Albums assets into Synology Photos. {e}")
                return 0,0,0,0
            
        return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_duplicates_assets_removed


    def upload_no_albums(self, input_folder, subfolders_exclusion='Albums', subfolders_inclusion=None, log_level=logging.WARNING):
        """
        Recursively traverses 'input_folder' and its subfolders_inclusion to upload all
        compatible files (photos/videos) to Synology without associating them to any album.

        Args:
            input_folder (str): Input folder
            subfolders_exclusion (str or list): Subfolders exclusion
            subfolders_inclusion (str or list): Subfolders inclusion
            log_level (logging.LEVEL): log_level for logs and console

        Returns: assets_uploaded
        """
        with set_log_level(LOGGER, log_level):

            self.login(log_level=log_level)
            if not os.path.isdir(input_folder):
                LOGGER.error(f"ERROR   : The folder '{input_folder}' does not exist.")
                return 0

            subfolders_exclusion = convert_to_list(subfolders_exclusion)
            subfolders_inclusion = convert_to_list(subfolders_inclusion) if subfolders_inclusion else []
            SUBFOLDERS_EXCLUSIONS = ['@eaDir'] + subfolders_exclusion

            def collect_files(base, only_subs):
                files_list = []
                if only_subs:
                    for sub in only_subs:
                        sub_path = os.path.join(base, sub)
                        if not os.path.isdir(sub_path):
                            LOGGER.warning(f"WARNING : Subfolder '{sub}' does not exist in '{base}'. Skipping.")
                            continue
                        for r, dirs, files in os.walk(sub_path):
                            dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                            for f_ in files:
                                files_list.append(os.path.join(r, f_))
                else:
                    for r, dirs, files in os.walk(base):
                        dirs[:] = [d for d in dirs if d not in SUBFOLDERS_EXCLUSIONS]
                        for f_ in files:
                            files_list.append(os.path.join(r, f_))
                return files_list

            try:
                file_paths = collect_files(input_folder, subfolders_inclusion)
                total_files = len(file_paths)
                total_assets_uploaded = 0

                with tqdm(total=total_files, smoothing=0.1, desc="INFO    : Uploading Assets", unit=" asset") as pbar:
                    for file_ in file_paths:
                        asset_id = self.upload_asset(file_, log_level=logging.WARNING)
                        if asset_id:
                            total_assets_uploaded += 1
                        pbar.update(1)

                LOGGER.info(f"INFO    : Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")

            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while uploading No-Albums assets into Synology Photos. {e}")
                return 0
            
        return total_assets_uploaded


    def upload_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.INFO):
        """
        Uploads ALL photos/videos from input_folder into Synology Photos.
        Returns details about how many albums and assets were uploaded.

        Args:
            input_folder (str): Input folder
            albums_folders (str): Albums folder
            remove_duplicates (bool): True to remove duplicates assets after upload all assets
            log_level (logging.LEVEL): log_level for logs and console

        Returns: (total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed)
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                total_duplicates_assets_removed = 0
                input_folder = os.path.realpath(input_folder)
                albums_folders = convert_to_list(albums_folders) if albums_folders else []

                albums_folder_included = any(subf.lower() == 'albums' for subf in albums_folders)
                if not albums_folder_included:
                    albums_folders.append('Albums')

                LOGGER.info("")
                LOGGER.info(f"INFO    : Uploading Assets and creating Albums into synology Photos from '{albums_folders}' subfolders...")

                total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, total_duplicates_assets_removed = self.upload_albums(
                    input_folder=input_folder,
                    subfolders_inclusion=albums_folders,
                    remove_duplicates=False,
                    log_level=logging.WARNING
                )

                LOGGER.info("")
                LOGGER.info(f"INFO    : Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")

                total_assets_uploaded_without_albums = self.upload_no_albums(
                    input_folder=input_folder,
                    subfolders_exclusion=albums_folders,
                    log_level=logging.WARNING
                )

                total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

                if remove_duplicates:
                    LOGGER.info("INFO    : Removing Duplicates Assets...")
                    total_duplicates_assets_removed += self.remove_duplicates_assets(log_level=logging.WARNING)

            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while uploading ALL assets into Synology Photos. {e}")
            

            return (
                total_albums_uploaded,
                total_albums_skipped,
                total_assets_uploaded,
                total_assets_uploaded_within_albums,
                total_assets_uploaded_without_albums,
                total_duplicates_assets_removed
            )


    def download_albums(self, albums_name='ALL', output_folder='Downloads_Synology', log_level=logging.WARNING):
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
            try:
                self.login(log_level=log_level)

                albums_downloaded = 0
                assets_downloaded = 0

                output_folder = os.path.join(output_folder, 'Albums')
                os.makedirs(output_folder, exist_ok=True)

                if isinstance(albums_name, str):
                    albums_name = [albums_name]

                all_albums = self.get_albums_including_shared_with_user(log_level=log_level)

                if not all_albums:
                    return (0, 0)

                if 'ALL' in [x.strip().upper() for x in albums_name]:
                    albums_to_download = all_albums
                    LOGGER.info(f"INFO    : ALL albums ({len(all_albums)}) will be downloaded...")
                else:
                    # Flatten user-specified album patterns
                    pattern_list = []
                    for item in albums_name:
                        if isinstance(item, str):
                            pattern_list.extend([pt.strip() for pt in item.replace(',', ' ').split() if pt.strip()])
                    albums_to_download = []

                    for album in all_albums:
                        alb_name = album.get("albumName", "")
                        for pattern in pattern_list:
                            if fnmatch.fnmatch(alb_name.strip().lower(), pattern.lower()):
                                albums_to_download.append(album)
                                break

                    if not albums_to_download:
                        LOGGER.error("ERROR   : No albums found matching the provided patterns.")
                        self.logout(log_level=log_level)
                        return (0, 0)
                    LOGGER.info(f"INFO    : {len(albums_to_download)} albums from Synology Photos will be downloaded to '{output_folder}'...")

                albums_downloaded = len(albums_to_download)

                for album in tqdm(albums_to_download, desc="INFO    : Downloading Albums", unit=" albums"):
                    album_name = album.get("albumName", "")
                    album_id = album.get('id')
                    LOGGER.info(f"INFO    : Processing album: '{album_name}' (ID: {album_id})")
                    album_assets = self.get_album_assets(album_id, album_name, log_level=log_level)
                    LOGGER.info(f"INFO    : Number of album_assets in the album '{album_name}': {len(album_assets)}")
                    if not album_assets:
                        LOGGER.warning(f"WARNING : No album_assets to download in the album '{album_name}'.")
                        continue

                    album_folder_name = f'{album_name}'
                    album_folder_path = os.path.join(output_folder, album_folder_name)

                    for asset in album_assets:
                        asset_id = asset.get('id')
                        asset_time = asset.get('time')
                        asset_filename = asset.get('filename')
                        # Download
                        assets_downloaded += self.download_asset(asset_id, asset_filename, asset_time, album_folder_path, log_level=logging.INFO)

                LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{output_folder}'")
                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while uploading ALL assets into Synology Photos. {e}")
                return 0,0
            
            return albums_downloaded, assets_downloaded


    def download_no_albums(self, no_albums_folder='Downloads_Synology', log_level=logging.WARNING):
        """
        Downloads assets not associated to any album from Synology Photos into output_folder/No-Albums/.
        Then organizes them by year/month inside that folder.

        Args:
            no_albums_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns total_assets_downloaded or 0 if no assets are downloaded
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                total_assets_downloaded = 0

                assets_without_albums = self.get_no_albums_assets(log_level=logging.INFO)
                no_albums_folder = os.path.join(no_albums_folder, 'No-Albums')
                os.makedirs(no_albums_folder, exist_ok=True)

                LOGGER.info(f"INFO    : Number of assets without Albums associated to download: {len(assets_without_albums)}")
                if not assets_without_albums:
                    LOGGER.warning(f"WARNING : No assets without Albums associated to download.")
                    return 0

                for asset in tqdm(assets_without_albums, desc="INFO    : Downloading Assets without associated Albums", unit=" assets"):
                    asset_id = asset.get('id')
                    asset_name = asset.get('filename')
                    asset_time = asset.get('time')
                    total_assets_downloaded += self.download_asset(asset_id, asset_name, asset_time, no_albums_folder, log_level=logging.INFO)

                # Now organize them by date (year/month)
                organize_files_by_date(input_folder=no_albums_folder, type='year/month')

                LOGGER.info(f"INFO    : Album(s) downloaded successfully. You can find them in '{no_albums_folder}'")
                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while downloading No-Albums assets from Synology Photos. {e}")
            
            return total_assets_downloaded


    def download_ALL(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
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

        Args:
            output_folder (str): Output folder
            log_level (logging.LEVEL): log_level for logs and console
        """
        
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                (total_albums_downloaded, total_assets_downloaded_within_albums) = self.download_albums(
                    albums_name='ALL',
                    output_folder=output_folder,
                    log_level=logging.WARNING
                )
                total_assets_downloaded_without_albums = self.download_no_albums(
                    no_albums_folder=output_folder,
                    log_level=logging.WARNING
                )
                total_assets_downloaded = total_assets_downloaded_within_albums + total_assets_downloaded_without_albums
                LOGGER.info(f"INFO    : Download of ALL assets completed.")
                LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
                LOGGER.info(f"Total Assets downloaded                   : {total_assets_downloaded}")
                LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_downloaded_within_albums}")
                LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_downloaded_without_albums}")
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while downloading ALL assets from Synology Photos. {e}")
            
            return (
                total_albums_downloaded,
                total_assets_downloaded,
                total_assets_downloaded_within_albums,
                total_assets_downloaded_without_albums
            )


    ###########################################################################
    #                REMOVE EMPTY / DUPLICATES (FOLDERS & ALBUMS)            #
    ###########################################################################
    def remove_empty_folders(self, log_level=logging.INFO):
        """
        Recursively removes all empty folders and subfolders in Synology Photos,
        considering folders empty if they only contain '@eaDir'.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty folders removed.
        """
        def remove_empty_folders_recursive(folder_id, folder_name):
            try:
                folders_dict = self.get_folders(folder_id, log_level=log_level)
                removed_count = 0
                # Recurse subfolders first
                for subfolder_id, subfolder_name in folders_dict.items():
                    removed_count += remove_empty_folders_recursive(subfolder_id, subfolder_name)

                folders_dict = self.get_folders(folder_id, log_level=log_level)
                folders_count = len(folders_dict)
                assets_count = self.get_folder_items_count(folder_id, folder_name, log_level=log_level)
                only_eaDir_present = (folders_count == 1 and "@eaDir" in folders_dict.values())
                is_truly_empty = (folders_count == 0 and assets_count == 0)

                if (is_truly_empty or only_eaDir_present) and folder_name != '/':
                    LOGGER.debug("")
                    LOGGER.debug(f"DEBUG    : Removing empty folder: '{folder_name}' (ID: {folder_id}) within Synology Photos")
                    self.remove_folder(folder_id, folder_name, log_level=log_level)
                    removed_count += 1
                else:
                    LOGGER.debug(f"DEBUG   : The folder '{folder_name}' cannot be removed because is not empty.")
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing empty folders from Synology Photos. {e}")
            
            return removed_count

        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                LOGGER.info("INFO    : Starting empty folder removal from Synology Photos...")

                root_folder_id = self.get_root_folder_id(log_level=log_level)
                total_removed = remove_empty_folders_recursive(root_folder_id, '/')

                LOGGER.info(f"INFO    : Process Remove empty folders from Synology Photos finished. Total removed folders: {total_removed}")
                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing empty folders from Synology Photos. {e}")
            
            return total_removed


    def remove_empty_albums(self, log_level=logging.WARNING):
        """
        Removes all empty albums in Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty albums deleted.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                albums = self.get_albums_owned_by_user(log_level=log_level)
                if not albums:
                    LOGGER.info("INFO    : No albums found.")
                    self.logout(log_level=log_level)
                    return 0

                total_removed_empty_albums = 0
                LOGGER.info("INFO    : Looking for empty albums in Synology Photos...")
                for album in tqdm(albums, desc=f"INFO    : Searching for Empty Albums", unit=" albums"):
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    asset_count = self.get_album_assets_count(album_id, album_name, log_level=logging.WARNING)
                    if asset_count == 0:
                        if self.remove_album(album_id, album_name):
                            LOGGER.info(f"INFO    : Empty album '{album_name}' (ID={album_id}) removed.")
                            total_removed_empty_albums += 1

                LOGGER.info(f"INFO    : Removed {total_removed_empty_albums} empty albums.")
                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing empties albums from Synology Photos. {e}")
            
            return total_removed_empty_albums


    def remove_duplicates_albums(self, log_level=logging.WARNING):
        """
        Remove all duplicate albums in Synology Photos. Duplicates are albums
        that share the same assets_count and total assets_size. It keeps the first
        album, removes the others from each duplicate group.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of duplicate albums deleted.
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                albums = self.get_albums_owned_by_user(log_level=log_level)

                if not albums:
                    return 0

                LOGGER.info("INFO    : Looking for duplicate albums in Synology Photos...")
                duplicates_map = {}
                for album in tqdm(albums, smoothing=0.1, desc="INFO    : Removing Duplicates Albums", unit=" albums"):
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    assets_count = self.get_album_assets_count(album_id, album_name, log_level=log_level)
                    assets_size = self.get_album_assets_size(album_id, album_name, log_level=log_level)
                    duplicates_map.setdefault((assets_count, assets_size), []).append((album_id, album_name))

                # for (assets_count, assets_size), group in duplicates_map.items():
                total_removed_duplicated_albums = 0
                for (assets_count, assets_size), group in duplicates_map.items():
                    LOGGER.debug(f'DEBUG:   : Assets Count: {assets_count}. Assets Size: {assets_size}.')
                    if len(group) > 1:
                        # keep the first, remove the rest
                        group_sorted = sorted(group, key=lambda x: x[0])  # sort by album_id string
                        to_remove = group_sorted[1:]
                        for (alb_id, alb_name) in to_remove:
                            LOGGER.info(f"INFO    : Removing duplicate album: '{alb_name}' (ID={alb_id})")
                            if self.remove_album(alb_id, alb_name, log_level=log_level):
                                total_removed_duplicated_albums += 1

                LOGGER.info(f"INFO    : Removed {total_removed_duplicated_albums} duplicate albums.")
                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing duplicates albums from Synology Photos. {e}")
            
            return total_removed_duplicated_albums


    # -----------------------------------------------------------------------------
    #          DELETE ORPHANS ASSETS FROM IMMICH DATABASE
    # -----------------------------------------------------------------------------
    # TODO: Complete this method
    def remove_orphan_assets(user_confirmation=True, log_level=logging.WARNING):
        """
        Removes orphan assets in the Synology database. Orphan assets are assets found in Synology database but not found in disk.

        Returns how many orphan got removed.
        """
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return 0


    ###########################################################################
    #                   MISC: REMOVE ALL ASSETS, ETC.                         #
    ###########################################################################
    def remove_all_assets(self, log_level=logging.WARNING):
        """
        Removes ALL assets in Synology Photos (in batches of 250 if needed). Then removes empty folders/albums if any remain.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns (assets_removed, albums_removed, folders_removed)
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                LOGGER.info(f"INFO    : Getting list of asset(s) to remove...")

                all_assets = self.get_all_assets(log_level=log_level)
                combined_ids = [a.get("id") for a in all_assets if a.get("id")]

                total_assets_found = len(combined_ids)
                if total_assets_found == 0:
                    LOGGER.warning(f"WARNING : No Assets found in Synology Photos.")
                LOGGER.info(f"INFO    : Found {total_assets_found} asset(s) to remove.")

                removed_assets = 0
                BATCH_SIZE = 250
                i = 0
                while i < len(combined_ids):
                    batch = combined_ids[i:i + BATCH_SIZE]
                    removed_assets += self.remove_assets(batch, log_level=log_level)
                    i += BATCH_SIZE

                LOGGER.info(f"INFO    : Removing empty folders if remain...")
                removed_folders = self.remove_empty_folders(log_level=log_level)

                LOGGER.info(f"INFO    : Removing empty albums if remain...")
                removed_albums = self.remove_empty_albums(log_level=log_level)

                self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing ALL assets from Synology Photos. {e}")
            
            return (removed_assets, removed_albums, removed_folders)


    def remove_all_albums(self, removeAlbumsAssets=False, log_level=logging.WARNING):
        """
        Removes all albums and optionally also all their associated assets.

        Args:
            removeAlbumsAssets (bool): If True, removes also all the assets associated to all albums
            log_level (logging.LEVEL): log_level for logs and console

        Returns (#albums_removed, #assets_removed).
        """
        with set_log_level(LOGGER, log_level):
            try:
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
            except Exception as e:
                LOGGER.error(f"ERROR   : Exception while removing All albums from Synology Photos. {e}")
            
            return total_removed_albums, total_removed_assets

##############################################################################
#                                END OF CLASS                                #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    from ChangeWorkingDir import change_working_dir
    change_working_dir()

    # Create the Object
    syno = ClassSynologyPhotos()

    # Read configuration and log in
    syno.read_config_file('Config.ini')
    syno.login(use_syno_token=True)
    # login(use_syno_token=False)

    # # Example: remove_empty_albums()
    # print("=== EXAMPLE: remove_empty_albums() ===")
    # syno.deleted = synology_remove_empty_albums()
    # print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # # Example: remove_duplicates_albums()
    # print("=== EXAMPLE: remove_duplicates_albums() ===")
    # syno.duplicates = synology_remove_duplicates_albums()
    # print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # # Example: Upload_asset()
    # print("\n=== EXAMPLE: upload_asset() ===")
    # file_path = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing\Albums\1994 - Recuerdos\169859_10150125237566327_578986326_8330690_6545.jpg"                # For Windows
    # asset_id = syno.upload_asset(file_path)
    # if not asset_id:
    #     print(f"Error uploading asset '{file_path}'.")
    # else:
    #     print(f"New Asset uploaded successfully with id: {asset_id}")

    # # Example: synology_upload_no_albums()
    # print("\n=== EXAMPLE: synology_upload_no_albums() ===")
    # # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # syno.upload_no_albums(input_folder)

    # # Example: synology_upload_albums()
    # print("\n=== EXAMPLE: synology_upload_albums() ===")
    # # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # syno.upload_albums(input_folder)

    # # Example: synology_upload_ALL()
    # print("\n=== EXAMPLE: synology_upload_ALL() ===")
    # # input_folder = "/volume1/homes/jaimetur/CloudPhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    # input_folder = r"r:\jaimetur\CloudPhotoMigrator\Upload_folder_for_testing"                # For Windows
    # syno.upload_ALL(input_folder)

    # Example: synology_download_albums()
    print("\n=== EXAMPLE: synology_download_albums() ===")
    download_folder = r"r:\jaimetur\CloudPhotoMigrator\Download_folder_for_testing"
    total = syno.download_albums(albums_name='ALL', output_folder=download_folder)
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # # Example: synology_download_no_albums()
    # print("\n=== EXAMPLE: synology_download_albums() ===")
    # download_folder = r"r:\jaimetur\CloudPhotoMigrator\Download_folder_for_testing"
    # total = syno.download_no_albums(no_albums_folder=download_folder)
    # print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # # Example: download_ALL
    # print("=== EXAMPLE: download_ALL() ===")
    # total_struct = syno.download_ALL(output_folder="Downloads_Synology")
    # # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # # Test: get_photos_root_folder_id()
    # print("=== EXAMPLE: get_photos_root_folder_id() ===")
    # root_folder_id = syno.get_photos_root_folder_id()
    # print (root_folder_id)

    # # Example: remove_empty_folders()
    # print("\n=== EXAMPLE: remove_empty_folders() ===")
    # total = syno.remove_empty_folders()
    # print(f"[RESULT] A total of {total} folders have been removed.\n")

    # logout()
    syno.logout()

