# -*- coding: utf-8 -*-

import fnmatch
import json
import logging
import mimetypes
import os
import sys
import time
from datetime import datetime

import requests
import urllib3
from requests_toolbelt.multipart.encoder import MultipartEncoder

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import ARGS, LOGGER, MSG_TAGS, FOLDERNAME_NO_ALBUMS, CONFIGURATION_FILE, FOLDERNAME_ALBUMS
from Features.GoogleTakeout.ClassTakeoutFolder import organize_files_by_date
from Utils.DateUtils import parse_text_datetime_to_epoch, is_date_outside_range
from Utils.GeneralUtils import update_metadata, convert_to_list, get_unique_items, tqdm, match_pattern, replace_pattern, has_any_filter, confirm_continue

"""
----------------------
ClassSynologyPhotos.py
----------------------
Python module with example functions to interact with Synology Photos, including following functions:
  - Configuration (read config)
  - Authentication (login/logout)
  - Indexing and Reindexing functions
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Deleting empty or duplicate albums
  - Main functions for use in other modules:
     - synology_delete_empty_albums()
     - delete_duplicates_albums()
     - upload_folder()
     - upload_albums()
     - pull_albums()
     - pull_ALL()
"""

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
        if account_id not in [1, 2, 3]:
            LOGGER.error(f"Cannot create Immich Photos object with ACCOUNT_ID: {account_id}. Valid valies are [1, 2]. Exiting...")
            sys.exit(-1)

        # Variables that were previously global:
        self.CONFIG = {}
        self.SYNOLOGY_URL = None
        self.SYNOLOGY_USERNAME = None
        self.SYNOLOGY_PASSWORD = None

        self.SESSION = None
        self.SID = None
        self.SYNO_TOKEN_HEADER = {}

        self.use_OTP = ARGS.get('one-time-password', None)

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

        # Create a cache dictionary of albums_owned_by_user to save in memmory all the albums owned by this user to avoid multiple calls to method get_albums_owned_by_user()
        self.albums_owned_by_user = {}

        # Create cache lists for future use
        self.all_assets_filtered = None
        self.assets_without_albums_filtered = None
        self.albums_assets_filtered = None

        # Get the values from the arguments (if exists)
        self.type = ARGS.get('filter-by-type', None)
        self.from_date = ARGS.get('filter-from-date', None)
        self.to_date = ARGS.get('filter-to-date', None)
        self.country = ARGS.get('filter-by-country', None)
        self.city = ARGS.get('filter-by-city', None)
        self.person = ARGS.get('filter-by-person', None)
        self.person_ids_list = []
        self.geocoding_ids_list = []
        self.geocoding_country_ids_list = []
        self.geocoding_city_ids_list = []

        # login to get CLIENT_ID
        self.login()
        self.CLIENT_ID = self.get_user_mail()

        self.CLIENT_NAME = f'Synology Photos ({self.CLIENT_ID})'


    ###########################################################################
    #                           CLASS PROPERTIES GETS                         #
    ###########################################################################
    def get_client_name(self, log_level=None):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return self.CLIENT_NAME

    ###########################################################################
    #                           CONFIGURATION READING                         #
    ###########################################################################
    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        """
        Reads the Configuration file and updates the instance attributes.
        If the config file is not found, prompts the user to manually input required data.

        Args:
            config_file (str): The path to the configuration file. Default is 'Config.ini'.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            dict: The loaded configuration dictionary.
        """
        from Core.ConfigReader import load_config

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
                LOGGER.warning(f"SYNOLOGY_URL not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_URL'] = input("\nEnter SYNOLOGY_URL: ")
                self.SYNOLOGY_URL = self.CONFIG['SYNOLOGY_URL']

            if not self.SYNOLOGY_USERNAME or self.SYNOLOGY_USERNAME.strip() == '':
                LOGGER.warning(f"SYNOLOGY_USERNAME not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_USERNAME'] = input("\nEnter SYNOLOGY_USERNAME: ")
                self.SYNOLOGY_USERNAME = self.CONFIG['SYNOLOGY_USERNAME']

            if not self.SYNOLOGY_PASSWORD or self.SYNOLOGY_PASSWORD.strip() == '':
                LOGGER.warning(f"SYNOLOGY_PASSWORD not found. It will be requested on screen.")
                self.CONFIG['SYNOLOGY_PASSWORD'] = input("\nEnter SYNOLOGY_PASSWORD: ")
                self.SYNOLOGY_PASSWORD = self.CONFIG['SYNOLOGY_PASSWORD']

            LOGGER.info(f"")
            LOGGER.info(f"Synology Config Read:")
            LOGGER.info(f"---------------------")
            masked_password = '*' * len(self.SYNOLOGY_PASSWORD)
            LOGGER.info(f"SYNOLOGY_URL              : {self.SYNOLOGY_URL}")
            LOGGER.info(f"SYNOLOGY_USERNAME         : {self.SYNOLOGY_USERNAME}")
            LOGGER.info(f"SYNOLOGY_PASSWORD         : {masked_password}")

            return self.CONFIG


    ###########################################################################
    #                         AUTHENTICATION / LOGOUT                         #
    ###########################################################################
    def login(self, use_syno_token=False, use_OTP=None, log_level=None):
        """
        Logs into the NAS and returns the active session with the SID and Synology DSM URL.

        If already logged in, reuses the existing session.

        Args:
            use_syno_token (bool): Define if you want to use X-SYNO-TOKEN in the header to maintain the session
            log_level (logging.LEVEL): log_level for logs and console

        Returns (self.SESSION, self.SID) or (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
        :param use_OTP:
        """
        if use_OTP is None:
            use_OTP = self.use_OTP
        with set_log_level(LOGGER, log_level):
            try:
                if self.SESSION and self.SID and self.SYNO_TOKEN_HEADER:
                    return (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
                elif self.SESSION and self.SID:
                    return (self.SESSION, self.SID)

                self.read_config_file(log_level=log_level)
                LOGGER.info(f"")
                LOGGER.info(f"Authenticating on Synology Photos and getting Session...")

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

                if use_OTP:
                    LOGGER.warning(f"SYNOLOGY OTP TOKEN required (flag -OTP, --one-time-password detected). OTP Token will be requested on screen...")
                    OTP = input(f"{MSG_TAGS['INFO']}Enter SYNOLOGY OTP Token: ")
                    params.update({"otp_code": {OTP}})
                    params.update({"enable_device_token": "yes"})
                    params.update({"device_name": "PhotoMigrator"})

                response = self.SESSION.get(url, params=params, verify=False)
                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    self.SID = data["data"]["sid"]
                    self.SESSION.cookies.set("id", self.SID)
                    LOGGER.info(f"Authentication Successfully with user/password found in Config file. Cookie properly set with session id.")
                    if use_syno_token:
                        LOGGER.info(f"SYNO_TOKEN_HEADER created as global variable. You must include 'SYNO_TOKEN_HEADER' in your request to work with this session.")
                        self.SYNO_TOKEN_HEADER = {"X-SYNO-TOKEN": data["data"]["synotoken"],}
                        return (self.SESSION, self.SID, self.SYNO_TOKEN_HEADER)
                    else:
                        return (self.SESSION, self.SID)
                else:
                    LOGGER.error(f"Unable to authenticate with the provided Synology Photos data: {data}")
                    sys.exit(-1)
            except Exception as e:
                LOGGER.error(f"Exception while login into Synology Photos!. {e}")
            

    def logout(self, log_level=None):
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
                        LOGGER.info(f"Session closed successfully.")
                        self.SESSION = None
                        self.SID = None
                        self.SYNO_TOKEN_HEADER = {}
                    else:
                        LOGGER.error(f"Unable to close session in Synology NAS.")
            except Exception as e:
                LOGGER.error(f"Exception while logout from Synology Photos!. {e}")
            

    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def get_supported_media_types(self, type='media', log_level=None):
        """
        Returns the supported media/sidecar extensions as for Synology Photos
        """
        with set_log_level(LOGGER, log_level):
            try:
                if type.lower() == 'media':
                    supported_types = self.ALLOWED_MEDIA_EXTENSIONS
                    LOGGER.debug(f"Supported media types: '{supported_types}'.")
                elif type.lower() == 'image':
                    supported_types = self.ALLOWED_PHOTO_EXTENSIONS
                    LOGGER.debug(f"Supported image types: '{supported_types}'.")
                elif type.lower() == 'video':
                    supported_types = self.ALLOWED_VIDEO_EXTENSIONS
                    LOGGER.debug(f"Supported video types: '{supported_types}'.")
                elif type.lower() == 'sidecar':
                    supported_types = self.ALLOWED_SIDECAR_EXTENSIONS
                    LOGGER.debug(f"Supported sidecar types: '{supported_types}'.")
                else:
                    LOGGER.error(f"Invalid type '{type}' to get supported media types. Types allowed are 'media', 'image', 'video' or 'sidecar'")
                    return None
                return supported_types
            except Exception as e:
                LOGGER.error(f"Cannot get Supported media types: {e}")
                return None
            

    def get_user_id(self, log_level=None):
        """
        Returns the user_id of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.info(f"User ID: '{self.SYNOLOGY_USERNAME}' found.")
                LOGGER.info(f"")
                return self.SYNOLOGY_USERNAME
            except Exception as e:
                LOGGER.error(f"Exception while getting user id. {e}")

    def get_user_mail(self, log_level=None):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.info(f"User ID: '{self.SYNOLOGY_USERNAME}' found.")
                LOGGER.info(f"")
                return self.SYNOLOGY_USERNAME
            except Exception as e:
                LOGGER.error(f"Exception while getting user mail. {e}")

    def get_geocoding_person_lists(self, log_level=None):
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
                geocoding_list = []
                person_list = []
                params = {
                    "api": "SYNO.Foto.Search.Filter",
                    "method": "list",
                    "version": "2",
                    "setting": '{"geocoding":true,"person":true}'
                }
                resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                resp.raise_for_status()
                data = resp.json()
                if data["success"]:
                    geocoding_list.extend(data["data"]["geocoding"])
                    person_list.extend(data["data"]["person"])
                else:
                    LOGGER.error(f"Failed to get Geocoding/Person list: ", data)
                    return None, None
                return geocoding_list, person_list
            except Exception as e:
                LOGGER.error(f"Exception while getting Geocoding List from Synology Photos. {e}")

    def get_person_ids(self, person, log_level=None):
        """
        Retrieves the ID(s) of the person matching the provided name.

        Args:
            person (str): The name of the person to look for.
            log_level (int, optional): Logging level. Defaults to logging.INFO.

        Returns:
            list: A list with the matching person ID(s). Empty if no match is found.
        """
        with set_log_level(LOGGER, log_level):
            geocoding_list, person_list = self.get_geocoding_person_lists(log_level=log_level)
            person_ids_list = []
            for item in person_list:
                if item.get("name").lower() == person.lower():
                    person_ids_list.append(item.get("id"))
            return person_ids_list

    def get_geocoding_ids(self, place, log_level=None):
        def collect_ids(node):
            """Recorre recursivamente un nodo y extrae su id y el de todos sus hijos"""
            ids = [node.get("id")]
            for child in node.get("children", []):
                ids.extend(collect_ids(child))
            return ids
        with set_log_level(LOGGER, log_level):
            geocoding_list, person_list = self.get_geocoding_person_lists(log_level=log_level)
            for item in geocoding_list:
                stack = [item]
                while stack:
                    current = stack.pop()
                    if place.lower() in current.get("name").lower():
                        return collect_ids(current)
                    stack.extend(current.get("children", []))
            return []  # Si no se encuentra el lugar


    ###########################################################################
    #                            ALBUMS FUNCTIONS                             #
    ###########################################################################
    def create_album(self, album_name, log_level=None):
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
                    LOGGER.error(f"Unable to create album '{album_name}': {data}")
                    return None

                album_id = data["data"]["album"]["id"]
                LOGGER.info(f"Album '{album_name}' created with ID: {album_id}.")
                return album_id
            except Exception as e:
                LOGGER.warning(f"Cannot create album: '{album_name}' due to API call error. Skipped! {e}")


    def remove_album(self, album_id, album_name, log_level=None):
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
                    LOGGER.warning(f"Could not delete album {album_id}: {data}")
                    success = False
                return success
            except Exception as e:
                LOGGER.error(f"Exception while removing Album from Synology Photos. {e}")


    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
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
            :param filter_assets:
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
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    resp.raise_for_status()
                    data = resp.json()

                    if data["success"]:
                        album_list.extend(data["data"]["list"])
                    else:
                        LOGGER.error(f"Failed to list albums: ", data)
                        return None

                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit

                albums_filtered = []
                for album in album_list:
                    if "name" in album:  # Replace the key "name" by "albumName" to make it equal to Immich Photos
                        album["albumName"] = album.pop("name")
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    if filter_assets and has_any_filter():
                        album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                        if len(album_assets) > 0:
                            albums_filtered.append(album)
                    else:
                        albums_filtered.append(album)
                return albums_filtered
            except Exception as e:
                LOGGER.warning(f"Cannot get albums due to API call error. Skipped! {e}")


    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
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
            :param filter_assets:
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
                        LOGGER.error(f"Failed to list own albums:", data)
                        return None
                    album_list.extend(data["data"]["list"])
                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit
            except Exception as e:
                LOGGER.error(f"Exception while listing own albums. {e}")
                return None
            
            albums_filtered = []
            for album in album_list:
                if "name" in album:  # Replace the key "name" by "albumName" to make it equal to Immich Photos
                    album["albumName"] = album.pop("name")
                album_id = album.get('id')
                album_name = album.get("albumName", "")
                if filter_assets and has_any_filter():
                    album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                    if len(album_assets) > 0:
                        albums_filtered.append(album)
                else:
                    albums_filtered.append(album)
            return albums_filtered


    def get_album_assets_size(self, album_id, album_name, log_level=None):
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
                        LOGGER.warning(f"Cannot list files for album: '{album_name}' due to API call error. Skipped!")
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
                LOGGER.error(f"Exception while getting Album Assets from Synology Photos. {e}")
            

    def get_album_assets_count(self, album_id, album_name, log_level=None):
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
                    LOGGER.warning(f"Cannot count files for album: '{album_name}' due to API call error. Skipped!")
                    return -1
                return data["data"]["count"]
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets count from Synology Photos. {e}")


    def album_exists(self, album_name, log_level=None):
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
                    albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
                    for album in albums:
                        if album_name == album.get("albumName"):
                            album_exists = True
                            album_id = album.get("id")
                            self.albums_owned_by_user[album_name] = album_id  # Cache it for future use
                            break
                return album_exists, album_id
            except Exception as e:
                LOGGER.error(f"Exception while checking if Album exists on Synology Photos. {e}")


    ###########################################################################
    #                            ASSETS FILTERING                             #
    ###########################################################################
    def filter_assets(self, assets, log_level=None):
        """
        Filters a list of assets by person name.

        The method looks for a match in the 'name' field of each person listed in the
        'people' key of each asset. Matching is case-insensitive and allows partial matches.

        Args:
            assets (list): List of asset dictionaries.

        Returns:
            list: A filtered list of assets that include the specified person.
            :param log_level:
        """
        with set_log_level(LOGGER, log_level):
            filtered = []
            for asset in assets:
                asset_id = asset.get('id')
                # if assets exists in all_assets_filtered is because match all filters criteria, so will include in the filtered list to return
                if self.all_assets_filtered is None:
                    self.all_assets_filtered = self.get_assets_by_filters(log_level=log_level)
                if any(asset.get('id') == asset_id for asset in self.all_assets_filtered):
                    filtered.append(asset)
            return filtered

    def filter_assets_old(self, assets, log_level=None):
        """
        Filters a list of assets based on user-defined criteria such as date range,
        country, city, and asset type. Filter parameters are retrieved from the global ARGS dictionary.

        The filtering steps are applied in the following order:
        1. By date range (from-date, to-date)
        2. By country (matched in address or exifInfo)
        3. By city (matched in address or exifInfo)
        4. By person
        5. By asset_type

        Args:
            assets (list): List of asset dictionaries to be filtered.
            log_level (int, optional): Logging level to apply during filtering. Defaults to logging.INFO.

        Returns:
            list: A filtered list of assets that match the specified criteria.
        """
        with set_log_level(LOGGER, log_level):
            # Now Filter the assets list based on the filters given by ARGS
            try:
                filtered_assets = assets
                if self.type:
                    filtered_assets = self.filter_assets_by_type(filtered_assets, self.type)
                if self.from_date or self.to_date:
                    filtered_assets = self.filter_assets_by_date(filtered_assets, self.from_date, self.to_date)
                if self.country:
                    filtered_assets = self.filter_assets_by_place(filtered_assets, self.country)
                if self.city:
                    filtered_assets = self.filter_assets_by_place(filtered_assets, self.city)
                if self.person:
                    filtered_assets = self.filter_assets_by_person(filtered_assets, self.person)
                return filtered_assets
            except Exception as e:
                LOGGER.error(f"Exception while filtering Assets from Synology Photos. {e}")

    def filter_assets_by_type(self, assets, type):
        """
        Filters a list of assets by their type, supporting flexible type aliases.

        Accepted values for 'type':
        - 'image', 'images', 'photo', 'photos' → treated as ['PHOTO', 'LIVE']
        - 'video', 'videos' → treated as ['VIDEO']
        - 'all' → returns all assets (no filtering)

        Matching is case-insensitive.

        Args:
            assets (list): List of asset dictionaries to be filtered.
            type (str): The asset type to match.

        Returns:
            list: A filtered list of assets with the specified type(s).
        """
        if not type or type.lower() == "all":
            return assets

        type_lower = type.lower()
        image_aliases = {"image", "images", "photo", "photos"}
        video_aliases = {"video", "videos"}

        if type_lower in image_aliases:
            target_types = {"PHOTO", "LIVE"}
        elif type_lower in video_aliases:
            target_types = {"VIDEO"}
        else:
            return []  # Unknown type alias

        return [
            asset for asset in assets
            if asset.get("type", "").upper() in target_types
        ]

    def filter_assets_by_date(self, assets, from_date=None, to_date=None):
        """
        Filters a list of assets by their 'time' field using a date range.

        If any of the date inputs (from_date, to_date, or asset['time']) are not in epoch format,
        they will be converted using `parse_text_datetime_to_epoch()`.

        Args:
            assets (list): List of asset dictionaries.
            from_date (str | int | float | datetime, optional): Start date (inclusive). Defaults to epoch 0.
            to_date (str | int | float | datetime, optional): End date (inclusive). Defaults to current time.

        Returns:
            list: A filtered list of assets whose 'time' field is within the specified range.
        """
        epoch_start = 0 if from_date is None else parse_text_datetime_to_epoch(from_date)
        epoch_end = int(time.time()) if to_date is None else parse_text_datetime_to_epoch(to_date)
        filtered = []
        for asset in assets:
            asset_time = parse_text_datetime_to_epoch(asset.get("time"))
            if asset_time is None:
                continue
            if epoch_start <= asset_time <= epoch_end:
                filtered.append(asset)
        return filtered

    def filter_assets_by_place(self, assets, place):
        """
        Filters a list of assets by checking if the given place name appears in any of the
        string fields inside the 'address' dictionary (under 'additional') of each asset.

        Matching is case-insensitive and partial (substring match). Assets without an
        'address' dictionary will be skipped.

        Args:
            assets (list): List of asset dictionaries.
            place (str): Name of the place to match (case-insensitive).

        Returns:
            list: A filtered list of assets where the given place appears in any address field.
        """
        filtered = []
        place_lower = place.lower()
        for asset in assets:
            address = asset.get("additional", {}).get("address", {})
            if not address:
                continue
            for value in address.values():
                if isinstance(value, str) and place_lower in value.lower():
                    filtered.append(asset)
                    break  # Basta con un match para incluirlo
        return filtered

    def filter_assets_by_person(self, assets, person_name):
        """
        Filters a list of assets by person name.

        The method looks for a match in the 'name' field of each person listed in the
        'people' key of each asset. Matching is case-insensitive and allows partial matches.

        Args:
            assets (list): List of asset dictionaries.
            person_name (str): Name (or partial name) of the person to search for.

        Returns:
            list: A filtered list of assets that include the specified person.
        """
        # TODO: Adapt this method to Synology because have been copied from Immich Class
        if not person_name:
            return assets
        name_lower = person_name.lower()
        filtered = []
        filtered = assets # TODO: Remove this line if you want to apply person filter with this function. Right now Synology does not support this kind of filtering because there is no Person/People list in the assset info.
        for asset in assets:
            people = asset.get("people", [])
            for person in people:
                if isinstance(person, dict):
                    person_name_field = person.get("name", "")
                    if isinstance(person_name_field, str) and name_lower in person_name_field.lower():
                        filtered.append(asset)
                        break  # One match is enough
        return filtered

    ###########################################################################
    #                        ASSETS (PHOTOS/VIDEOS)                           #
    ###########################################################################
    def get_assets_by_filters(self, log_level=None):
        """
        Lists all assets in Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets (dict) in the entire library or Empty list on error.
        """
        with set_log_level(LOGGER, log_level):
            try:
                # If all_filtered_assets is already cached, return it
                if self.all_assets_filtered is not None:
                    return self.all_assets_filtered

                # Convert the values from iso to epoch
                self.from_date = parse_text_datetime_to_epoch(self.from_date)
                self.to_date = parse_text_datetime_to_epoch(self.to_date)

                # Obtain the place_ids for country and city
                self.geocoding_country_ids_list = []
                self.geocoding_city_ids_list = []
                if self.country: self.geocoding_country_ids_list = self.get_geocoding_ids(place=self.country, log_level=log_level)
                if self.city: self.geocoding_city_ids_list = self.get_geocoding_ids(place=self.city, log_level=log_level)
                self.geocoding_ids_list = self.geocoding_country_ids_list + self.geocoding_city_ids_list

                # If city or country filter was provided but geocoding_ids_list is empty means that the place does not exists, so return []
                if (self.city or self.country) and not self.geocoding_ids_list:
                    self.all_assets_filtered = []
                    return []

                # Obtain the person_ids_list for person
                self.person_ids_list = []
                if self.person:
                    self.person_ids_list = self.get_person_ids(self.person, log_level=log_level)
                    # If person was provided but person_ids_list is empty means that the person does not exists, so return []
                    if not self.person_ids_list:
                        self.all_assets_filtered = []
                        return []

                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                base_params = {
                    'api': 'SYNO.Foto.Browse.Item',
                    # 'version': '4',
                    # 'method': 'list',
                    'version': '2',
                    'method': 'list_with_filter',
                    'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                }

                # Add time to params only if from_date or to_date have some values
                time_dic = {}
                if self.from_date:  time_dic["start_time"] = self.from_date
                if self.to_date: time_dic["end_time"] = self.to_date
                if time_dic: base_params["time"] = json.dumps([time_dic])

                # Add geocoding key if geocoding_ids_list has some value
                if self.geocoding_ids_list: base_params["geocoding"] = json.dumps(self.geocoding_ids_list)

                # Add person key if person_ids_list has some value
                if self.person_ids_list:
                    base_params["person"] = json.dumps(self.person_ids_list)
                    base_params["person_policy"] = '"or"'

                # Add types to params if have been providen
                types = []
                if self.type:
                    if self.type.lower() in ['photo', 'photos', 'image', 'images']:
                        types.append(0)
                    if self.type.lower() in ['video', 'videos']:
                        types.append(1)
                if types: base_params["item_type"] = json.dumps(types)
                LOGGER.debug(f"base_params: {json.dumps(base_params, indent=4)}")

                offset = 0
                limit = 5000
                all_filtered_assets = []
                while True:
                    params = base_params.copy()  # Hacemos una copia para no modificar el original
                    params['offset'] = offset
                    params['limit'] = limit
                    try:
                        resp = self.SESSION.get(url, headers=headers, params=params, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            LOGGER.error(f"Failed to list assets")
                            return []
                        all_filtered_assets.extend(data["data"]["list"])
                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        LOGGER.error(f"Exception while listing assets {e}")
                        return []

                self.all_assets_filtered = all_filtered_assets # Cache all_filtered_assets for future use
                return all_filtered_assets
            except Exception as e:
                LOGGER.error(f"Exception while getting all Assets from Synology Photos. {e}")
            

    def get_all_assets_from_album(self, album_id, album_name=None, log_level=None):
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
                # base_params settings
                base_params = {
                    'api': 'SYNO.Foto.Browse.Item',
                    'version': '4',
                    'method': 'list',
                    'album_id': album_id,
                    # 'version': '2',
                    # 'method': 'list_with_filter',
                    # 'album_id': f"[{album_id}]",
                    'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                }

                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                album_assets = []
                while True:
                    params = base_params.copy()  # Hacemos una copia para no modificar el original
                    params['offset'] = offset
                    params['limit'] = limit
                    try:
                        resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            if album_name:
                                LOGGER.error(f"Failed to list photos in the album '{album_name}'")
                            else:
                                LOGGER.error(f"Failed to list photos in the album ID={album_id}")
                            return []
                        if len(data["data"]["list"])>0:
                            album_assets.extend(data["data"]["list"])

                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        if album_name:
                            LOGGER.error(f"Exception while listing photos in the album '{album_name}' {e}")
                        else:
                            LOGGER.error(f"Exception while listing photos in the album ID={album_id} {e}")
                        return []

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                return filtered_album_assets
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets from Synology Photos. {e}")


    def get_all_assets_from_album_shared(self, album_id, album_name=None, album_passphrase=None, log_level=None):
        """
        Get assets in a specific shared album.

        Args:
            album_id (str): ID of the album.
            album_name (str): Name of the album.
            album_passphrase (str): Shared album passphrase
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets in the album (dict objects). [] if no assets found.
        """
        with set_log_level(LOGGER, log_level):
            try:
                # base_params settings
                base_params = {
                    'api': 'SYNO.Foto.Browse.Item',
                    'version': '4',
                    'method': 'list',
                    'passphrase': album_passphrase,
                    # 'version': '2',
                    # 'method': 'list_with_filter',
                    # 'passphrase': album_passphrase,
                    'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
                }

                self.login(log_level=log_level)
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                offset = 0
                limit = 5000
                album_assets = []
                while True:
                    params = base_params.copy()  # Hacemos una copia para no modificar el original
                    params['offset'] = offset
                    params['limit'] = limit
                    try:
                        resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                        data = resp.json()
                        if not data.get("success"):
                            if album_name:
                                LOGGER.error(f"Failed to list photos in the album '{album_name}'")
                            else:
                                LOGGER.error(f"Failed to list photos in the album ID={album_id}")
                            return []
                        if len(data["data"]["list"]) > 0:
                            album_assets.extend(data["data"]["list"])

                        if len(data["data"]["list"]) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        if album_name:
                            LOGGER.error(f"Exception while listing photos in the album '{album_name}' {e}")
                        else:
                            LOGGER.error(f"Exception while listing photos in the album ID={album_id} {e}")
                        return []

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                return filtered_album_assets
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets from Synology Photos. {e}")


    def get_all_assets_without_albums(self, log_level=logging.WARNING):
        """
        Get assets not associated to any album from Synology Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_without_albums
        """
        with set_log_level(LOGGER, log_level):
            try:
                # If assets_without_albums is already cached, return it.
                if self.assets_without_albums_filtered is not None:
                    return self.assets_without_albums_filtered
                self.login(log_level=log_level)
                all_assets = self.get_assets_by_filters(log_level=logging.INFO)
                album_assets = self.get_all_assets_from_all_albums(log_level=logging.INFO)
                # Use get_unique_items from your Utils to find items that are in all_assets but not in album_asset
                assets_without_albums = get_unique_items(all_assets, album_assets, key='filename')
                LOGGER.info(f"Number of all_assets without Albums associated: {len(assets_without_albums)}")
                self.assets_without_albums_filtered = assets_without_albums # Cache assets_without_albums for future use
                return assets_without_albums
            except Exception as e:
                LOGGER.error(f"Exception while getting No-Albums Assets from Synology Photos. {e}")


    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: Albums Assets
        """
        with set_log_level(LOGGER, log_level):
            try:
                # If albums_assets is already cached, return it
                if self.albums_assets_filtered is not None:
                    return self.albums_assets_filtered

                self.login(log_level=log_level)
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)

                all_albums = self.get_albums_including_shared_with_user(filter_assets=True, log_level=log_level)
                combined_assets = []
                if not all_albums:
                    self.albums_assets_filtered = combined_assets  # Cache albums_assets for future use
                    return []
                for album in all_albums:
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                    combined_assets.extend(album_assets)
                self.albums_assets_filtered = combined_assets # Cache albums_assets for future use
                return combined_assets
            except Exception as e:
                LOGGER.error(f"Exception while getting All Albums Assets from Synology Photos. {e}")
            

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
                    LOGGER.warning(f"No assets found to add to Album ID: '{album_id}'. Skipped!")
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
                        LOGGER.warning(f"No assets found to add to Album: '{album_name}'. Skipped!")
                    else:
                        LOGGER.warning(f"No assets found to add to Album ID: '{album_id}'. Skipped!")
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
                        LOGGER.warning(f"Cannot add assets to album: '{album_name}' due to API call error. Skipped!")
                    else:
                        LOGGER.warning(f"Cannot add assets to album ID: '{album_id}' due to API call error. Skipped!")
                    return -1
                if album_name:
                    LOGGER.info(f"{total_added} Assets successfully added to album: '{album_name}'.")
                else:
                    LOGGER.info(f"{total_added} Assets successfully added to album ID: '{album_id}'.")
                return total_added

            except Exception as e:
                LOGGER.warning(f"Cannot add Assets to album: '{album_name}' due to API call error. Skipped!")
            

    # TODO: Complete this method
    def get_duplicates_assets(self, log_level=None):
        """
        Returns the list of duplicate assets from Synology
        """
        with set_log_level(LOGGER, log_level):
            try:
                return []
            except Exception as e:
                LOGGER.error(f"Exception while getting duplicates Assets from Synology Photos. {e}")


    def remove_assets(self, asset_ids, log_level=None):
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
                        LOGGER.error(f"Failed to remove assets")
                        return 0
                except Exception as e:
                    LOGGER.error(f"Exception while removing assets {e}")
                    return 0
                

                task_id = data.get('data', {}).get('task_info', {}).get('id')
                removed_count = len(asset_ids)

                # Wait for background remove task to finish
                self.wait_for_background_remove_task(task_id, log_level=log_level)
                return removed_count
            except Exception as e:
                LOGGER.error(f"Exception while removing Assets from Synology Photos. {e}")
            

    # TODO: Complete this method
    def remove_duplicates_assets(self, log_level=None):
        """
        Removes duplicate assets in the Synology database. Returns how many duplicates got removed.
        """
        with set_log_level(LOGGER, log_level):
            try:
                return 0
            except Exception as e:
                LOGGER.error(f"Exception while removing duplicates assets from Synology Photos. {e}")
            

    def push_asset(self, file_path, log_level=None):
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
                    raise FileNotFoundError(f"{MSG_TAGS['ERROR']}The file '{file_path}' does not exists.")

                filename, ext = os.path.splitext(file_path)
                ext = ext.lower()
                if ext not in self.ALLOWED_MEDIA_EXTENSIONS:
                    if ext in self.ALLOWED_SIDECAR_EXTENSIONS:
                        return None, None
                    else:
                        LOGGER.warning(f"File '{file_path}' has an unsupported extension. Skipped.")
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
                        LOGGER.warning(f"Cannot upload asset: '{file_path}' due to API call error. Skipped!")
                        return None, None
                    else:
                        asset_id = data["data"].get("id")
                        is_duplicated = data["data"].get("action") == "ignore"
                        if is_duplicated:
                            LOGGER.debug(f"Duplicated Asset: '{os.path.basename(file_path)}'. Skipped!")
                        else:
                            LOGGER.debug(f"Uploaded '{os.path.basename(file_path)}' with asset_id={asset_id}")
                        return asset_id, is_duplicated

            except Exception as e:
                LOGGER.warning(f"Cannot upload asset: '{file_path}' due to API call error. Skipped!")
                return None, None
            

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_Synology", album_passphrase=None, log_level=None):
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
                    LOGGER.error(f"")
                    LOGGER.error(f"Failed to download asset '{asset_filename}' with ID [{asset_id}]. Status code: {resp.status_code}")
                    return 0

                with open(file_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)

                os.utime(file_path, (asset_time, asset_time))

                if file_ext in self.ALLOWED_MEDIA_EXTENSIONS:
                    update_metadata(file_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"), log_level=logging.ERROR)

                LOGGER.debug(f"")
                LOGGER.debug(f"Asset '{asset_filename}' downloaded and saved at {file_path}")
                return 1
            except Exception as e:
                LOGGER.error(f"")
                LOGGER.error(f"Exception occurred while downloading asset '{asset_filename}' with ID [{asset_id}]. {e}")
                return 0
            


    ###########################################################################
    #                             FOLDERS FUNCTIONS                           #
    #             (This block is exclusive for ClassSynologyPhotos)           #
    ###########################################################################
    def get_root_folder_id(self, log_level=None):
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
                    LOGGER.error(f"Cannot obtain Photos Root Folder ID due to an error in the API call.")
                    sys.exit(-1)

                folder_name = data["data"]["folder"]["name"]
                folder_id = str(data["data"]["folder"]["id"])
                if not folder_id or folder_name != "/":
                    LOGGER.error(f"Cannot obtain Photos Root Folder ID.")
                    sys.exit(-1)
                return folder_id
            except Exception as e:
                LOGGER.error(f"Exception while geting root folder ID from Synology Photos. {e}")
            

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
                    LOGGER.error(f"Cannot obtain name for folder ID '{search_in_folder_id}' due to an error in the API call.")
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
                        LOGGER.error(f"Cannot obtain ID for folder '{folder_name}' due to an error in the API call.")
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
                LOGGER.error(f"Exception while getting folder ID from Synology Photos. {e}")
            
    def get_folders(self, parent_folder_id, log_level=None):
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
                        LOGGER.error(f"Failed to list albums: ", data)
                        return {}

                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit

                return folders_dict
            except Exception as e:
                LOGGER.error(f"Exception while getting folders from Synology Photos. {e}")
            

    def remove_folder(self, folder_id, folder_name, log_level=None):
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
                        LOGGER.error(f"Failed to remove folder '{folder_name}'")
                        return 0
                except Exception as e:
                    LOGGER.error(f"Exception while removing folder '{folder_name}' {e}")
                    return 0
                return len(folder_id)
            except Exception as e:
                LOGGER.error(f"Exception while removing Folder from Synology Photos. {e}")
            

    def get_folder_items_count(self, folder_id, folder_name, log_level=None):
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
                        LOGGER.error(f"Failed to count assets for folder '{folder_name}'.")
                        return -1
                    asset_count = data["data"]["count"]
                except Exception as e:
                    LOGGER.error(f"Exception while retrieving assets count for folder '{folder_name}'. {e}")
                    return -1
                return asset_count
            except Exception as e:
                LOGGER.error(f"Exception while getting Folder items count from Synology Photos. {e}")
            


    ###########################################################################
    #                         BACKGROUND TASKS MANAGEMENT                     #
    #             (This block is exclusive for ClassSynologyPhotos)           #
    ###########################################################################
    def wait_for_background_remove_task(self, task_id, log_level=None):
        """
        Internal helper to poll a background remove task until done.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
            :param task_id:
        """
        with set_log_level(LOGGER, log_level):
            try:
                while True:
                    status = self.wait_for_background_remove_task_finished_check(task_id, log_level=log_level)
                    if status == 'done' or status is True:
                        break
                    else:
                        LOGGER.debug(f"Task not finished yet. Waiting 5 seconds more.")
                        time.sleep(5)
            except Exception as e:
                LOGGER.error(f"Exception while waitting for remove task to finish in Synology Photos. {e}")


    def wait_for_background_remove_task_finished_check(self, task_id, log_level=None):
        """
        Checks whether a background removal task is finished.

        Args:
            log_level (logging.LEVEL): log_level for logs and console
            :param task_id:
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
                        LOGGER.error(f"Failed to get removing assets status")
                        return False
                    lst = data['data'].get('list', [])
                    if len(lst) > 0:
                        return lst[0].get('status')
                    else:
                        return True
                except Exception as e:
                    LOGGER.error(f"Exception while checking removing assets status {e}")
                    return False
            except Exception as e:
                LOGGER.error(f"Exception while checking if background task has finished in Synology Photos. {e}")
            

    ###########################################################################
    #             MAIN FUNCTIONS TO CALL FROM OTHER MODULES (API)            #
    ###########################################################################
    def push_albums(self, input_folder, subfolders_exclusion=FOLDERNAME_NO_ALBUMS, subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
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
                    LOGGER.error(f"The folder '{input_folder}' does not exist.")
                    return 0, 0, 0, 0, 0

                subfolders_exclusion = convert_to_list(subfolders_exclusion)
                subfolders_inclusion = convert_to_list(subfolders_inclusion)

                total_albums_uploaded = 0
                total_albums_skipped = 0
                total_assets_uploaded = 0
                total_duplicates_assets_removed = 0
                total_duplicates_assets_skipped = 0


                # # If 'Albums' is not in subfolders_inclusion, add it (like original code).
                # first_level_folders = [name.lower() for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
                # albums_folder_included = any(rel.lower() == 'albums' for rel in subfolders_inclusion)
                # if not albums_folder_included and 'albums' in first_level_folders:
                #     subfolders_inclusion.append('Albums')

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
                        # Check if there's at least one supported file
                        has_supported_files = any(os.path.splitext(file)[-1].lower() in self.ALLOWED_EXTENSIONS for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file)))
                        if has_supported_files:
                            valid_folders.append(dir_path)

                first_level_folders = os.listdir(input_folder)
                if subfolders_inclusion:
                    first_level_folders += subfolders_inclusion
                    first_level_folders = list(dict.fromkeys(first_level_folders))

                with tqdm(total=len(valid_folders), smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Uploading Albums from '{os.path.basename(input_folder)}' sub-folders", unit=" sub-folder") as pbar:
                    for subpath in valid_folders:
                        pbar.update(1)
                        album_assets_ids = []
                        if not os.path.isdir(subpath):
                            LOGGER.warning(f"Could not create album for subfolder '{subpath}'.")
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

                        if not album_name:
                            total_albums_skipped += 1
                            continue

                        for file in os.listdir(subpath):
                            file_path = os.path.join(subpath, file)
                            if not os.path.isfile(file_path):
                                continue
                            ext = os.path.splitext(file)[-1].lower()
                            if ext not in self.ALLOWED_EXTENSIONS:
                                continue

                            asset_id, is_dup = self.push_asset(file_path, log_level=logging.WARNING)
                            if is_dup:
                                total_duplicates_assets_skipped += 1
                                LOGGER.debug(f"Dupplicated Asset: {file_path}. Asset ID: {asset_id} upload skipped")
                            else:
                                total_assets_uploaded += 1

                            if asset_id:
                                # Associate only if ext is photo/video
                                if ext in self.ALLOWED_MEDIA_EXTENSIONS:
                                    album_assets_ids.append(asset_id)

                        if album_assets_ids:
                            album_id = self.create_album(album_name, log_level=log_level)
                            if not album_id:
                                LOGGER.warning(f"Could not create album for subfolder '{subpath}'.")
                                total_albums_skipped += 1
                            else:
                                self.add_assets_to_album(album_id, album_assets_ids, album_name=album_name, log_level=log_level)
                                LOGGER.debug(f"Album '{album_name}' created with ID: {album_id}. Total Assets added to Album: {len(album_assets_ids)}.")
                                total_albums_uploaded += 1
                        else:
                            total_albums_skipped += 1

                if remove_duplicates:
                    LOGGER.info(f"Removing Duplicates Assets...")
                    total_duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

                LOGGER.info(f"Uploaded {total_albums_uploaded} album(s) from '{input_folder}'.")
                LOGGER.info(f"Uploaded {total_assets_uploaded} asset(s) from '{input_folder}' to Albums.")
                LOGGER.info(f"Skipped {total_albums_skipped} album(s) from '{input_folder}'.")
                LOGGER.info(f"Removed {total_duplicates_assets_removed} duplicates asset(s) from Synology Database.")
                LOGGER.info(f"Skipped {total_duplicates_assets_skipped} duplicated asset(s) from '{input_folder}' to Albums.")

            except Exception as e:
                LOGGER.error(f"Exception while uploading Albums assets into Synology Photos. {e}")
                return 0,0,0,0,0

            # self.logout(log_level=log_level)
            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_duplicates_assets_removed, total_duplicates_assets_skipped


    def push_no_albums(self, input_folder, subfolders_exclusion=f'{FOLDERNAME_ALBUMS}', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        """
        Recursively traverses 'input_folder' and its subfolders_inclusion to upload all
        compatible files (photos/videos) to Synology without associating them to any album.

        Args:
            input_folder (str): Input folder
            subfolders_exclusion (str or list): Subfolders exclusion
            subfolders_inclusion (str or list): Subfolders inclusion
            log_level (logging.LEVEL): log_level for logs and console

        Returns: assets_uploaded
        :param remove_duplicates:
        """
        with set_log_level(LOGGER, log_level):

            self.login(log_level=log_level)
            if not os.path.isdir(input_folder):
                LOGGER.error(f"The folder '{input_folder}' does not exist.")
                return 0,0,0

            subfolders_exclusion = convert_to_list(subfolders_exclusion)
            subfolders_inclusion = convert_to_list(subfolders_inclusion) if subfolders_inclusion else []
            SUBFOLDERS_EXCLUSIONS = ['@eaDir'] + subfolders_exclusion

            def collect_files(base, only_subs):
                files_list = []
                if only_subs:
                    for sub in only_subs:
                        sub_path = os.path.join(base, sub)
                        if not os.path.isdir(sub_path):
                            LOGGER.warning(f"Subfolder '{sub}' does not exist in '{base}'. Skipping.")
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
                total_duplicated_assets_skipped = 0

                with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Uploading Assets", unit=" asset") as pbar:
                    for file_ in file_paths:
                        asset_id, is_dup = self.push_asset(file_, log_level=logging.WARNING)
                        if is_dup:
                            total_duplicated_assets_skipped += 1
                            LOGGER.debug(f"Dupplicated Asset: {file_path}. Asset ID: {asset_id} skipped")
                        elif asset_id:
                            LOGGER.debug(f"Asset ID: {asset_id} uploaded to Immich Photos")
                            total_assets_uploaded += 1
                        pbar.update(1)

                duplicates_assets_removed = 0
                if remove_duplicates:
                    LOGGER.info(f"Removing Duplicates Assets...")
                    duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

                LOGGER.info(f"Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")
                LOGGER.info(f"Skipped {total_duplicated_assets_skipped} duplicated asset(s) from '{input_folder}'.")
                LOGGER.info(f"Removed {duplicates_assets_removed} duplicates asset(s) from Synology Database.")

            except Exception as e:
                LOGGER.error(f"Exception while uploading No-Albums assets into Synology Photos. {e}")
                return 0,0,0
            
        return total_assets_uploaded, total_duplicated_assets_skipped, duplicates_assets_removed


    def push_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=None):
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
                    albums_folders.append(f'{FOLDERNAME_ALBUMS}')

                LOGGER.info(f"")
                LOGGER.info(f"Uploading Assets and creating Albums into synology Photos from '{albums_folders}' subfolders...")

                total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, total_duplicates_assets_removed_1, total_dupplicated_assets_skipped_1 = self.push_albums(input_folder=input_folder, subfolders_inclusion=albums_folders, remove_duplicates=False, log_level=logging.WARNING)

                LOGGER.info(f"")
                LOGGER.info(f"Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{albums_folders}')...")

                total_assets_uploaded_without_albums, total_dupplicated_assets_skipped_2, total_duplicates_assets_removed_2 = self.push_no_albums(input_folder=input_folder, subfolders_exclusion=albums_folders, log_level=logging.WARNING)

                total_duplicates_assets_removed = total_duplicates_assets_removed_1 + total_duplicates_assets_removed_2
                total_dupplicated_assets_skipped = total_dupplicated_assets_skipped_1 + total_dupplicated_assets_skipped_2
                total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

                if remove_duplicates:
                    LOGGER.info(f"Removing Duplicates Assets...")
                    total_duplicates_assets_removed += self.remove_duplicates_assets(log_level=logging.WARNING)

            except Exception as e:
                LOGGER.error(f"Exception while uploading ALL assets into Synology Photos. {e}")

            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed, total_dupplicated_assets_skipped


    def pull_albums(self, albums_name='ALL', output_folder='Downloads_Synology', log_level=logging.WARNING):
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

                output_folder = os.path.join(output_folder, f'{FOLDERNAME_ALBUMS}')
                os.makedirs(output_folder, exist_ok=True)

                if isinstance(albums_name, str):
                    albums_name = [albums_name]

                # Check if there is some filter applied
                filters_provided = has_any_filter()

                all_albums = self.get_albums_including_shared_with_user(filter_assets=filters_provided, log_level=log_level)

                if not all_albums:
                    return 0, 0

                if 'ALL' in [x.strip().upper() for x in albums_name]:
                    albums_to_download = all_albums
                    LOGGER.info(f"ALL albums ({len(all_albums)}) will be downloaded...")
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
                        LOGGER.error(f"No albums found matching the provided patterns.")
                        # self.logout(log_level=log_level)
                        return 0, 0
                    LOGGER.info(f"{len(albums_to_download)} albums from Synology Photos will be downloaded to '{output_folder}'...")

                albums_downloaded = len(albums_to_download)

                for album in tqdm(albums_to_download, desc=f"{MSG_TAGS['INFO']}Downloading Albums", unit=" albums"):
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    LOGGER.info(f"Processing album: '{album_name}' (ID: {album_id})")
                    album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                    LOGGER.info(f"Number of album_assets in the album '{album_name}': {len(album_assets)}")
                    if not album_assets:
                        LOGGER.warning(f"No album_assets to download in the album '{album_name}'.")
                        continue

                    album_folder_name = f'{album_name}'
                    album_folder_path = os.path.join(output_folder, album_folder_name)

                    for asset in album_assets:
                        asset_id = asset.get('id')
                        asset_time = asset.get('time')
                        asset_filename = asset.get('filename')
                        # Download
                        assets_downloaded += self.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=album_folder_path, log_level=logging.INFO)

                LOGGER.info(f"Album(s) downloaded successfully. You can find them in '{output_folder}'")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while uploading ALL assets into Synology Photos. {e}")
                return 0,0
            
            return albums_downloaded, assets_downloaded


    def pull_no_albums(self, no_albums_folder='Downloads_Synology', log_level=logging.WARNING):
        """
        Downloads assets not associated to any album from Synology Photos into output_folder/<NO_ALBUMS_FOLDER>/.
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

                assets_without_albums = self.get_all_assets_without_albums(log_level=logging.INFO)
                no_albums_folder = os.path.join(no_albums_folder, FOLDERNAME_NO_ALBUMS)
                os.makedirs(no_albums_folder, exist_ok=True)

                LOGGER.info(f"Number of assets without Albums associated to download: {len(assets_without_albums)}")
                if not assets_without_albums:
                    LOGGER.warning(f"No assets without Albums associated to download.")
                    return 0

                for asset in tqdm(assets_without_albums, desc=f"{MSG_TAGS['INFO']}Downloading Assets without associated Albums", unit=" assets"):
                    asset_id = asset.get('id')
                    asset_filename = asset.get('filename')
                    asset_time = asset.get('time')

                    if not asset_id:
                        continue

                    created_at_str = asset.get("time", "")
                    try:
                        dt_created = datetime.fromtimestamp(int(created_at_str))
                    except Exception:
                        dt_created = datetime.now()

                    year_str = dt_created.strftime("%Y")
                    month_str = dt_created.strftime("%m")
                    target_folder = os.path.join(no_albums_folder, year_str, month_str)
                    os.makedirs(target_folder, exist_ok=True)


                    total_assets_downloaded += self.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=target_folder, log_level=logging.INFO)

                # Now organize them by date (year/month)
                organize_files_by_date(input_folder=no_albums_folder, type='year/month')

                LOGGER.info(f"Album(s) downloaded successfully. You can find them in '{no_albums_folder}'")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while downloading No-Albums assets from Synology Photos. {e}")
            
            return total_assets_downloaded


    def pull_ALL(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads ALL photos and videos from Synology Photos into output_folder creating a Folder Structure like this:
        output_folder/
          ├─ Albums/
          │    ├─ albumName1/ (assets in the album)
          │    ├─ albumName2/ (assets in the album)
          │    ...
          └─ <NO_ALBUMS_FOLDER>/
               └─ yyyy/
                   └─ mm/ (assets not in any album for that year/month)

        Args:
            output_folder (str): Output folder
            log_level (logging.LEVEL): log_level for logs and console
        """
        
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                total_albums_downloaded, total_assets_downloaded_within_albums = self.pull_albums(albums_name='ALL', output_folder=output_folder, log_level=logging.WARNING)
                total_assets_downloaded_without_albums = self.pull_no_albums(no_albums_folder=output_folder, log_level=logging.WARNING)
                total_assets_downloaded = total_assets_downloaded_within_albums + total_assets_downloaded_without_albums
                LOGGER.info(f"Download of ALL assets completed.")
                LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
                LOGGER.info(f"Total Assets downloaded                   : {total_assets_downloaded}")
                LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_downloaded_within_albums}")
                LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_downloaded_without_albums}")
            except Exception as e:
                LOGGER.error(f"Exception while downloading ALL assets from Synology Photos. {e}")
            
            return (total_albums_downloaded, total_assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums)


    ###########################################################################
    #                REMOVE EMPTY / DUPLICATES (FOLDERS & ALBUMS)            #
    ###########################################################################
    def remove_empty_folders(self, log_level=None):
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
                    LOGGER.debug(f"")
                    LOGGER.debug(f"Removing empty folder: '{folder_name}' (ID: {folder_id}) within Synology Photos")
                    self.remove_folder(folder_id, folder_name, log_level=log_level)
                    removed_count += 1
                else:
                    LOGGER.debug(f"The folder '{folder_name}' cannot be removed because is not empty.")
            except Exception as e:
                LOGGER.error(f"Exception while removing empty folders from Synology Photos. {e}")
            
            return removed_count

        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                LOGGER.info(f"Starting empty folder removal from Synology Photos...")

                root_folder_id = self.get_root_folder_id(log_level=log_level)
                total_removed = remove_empty_folders_recursive(root_folder_id, '/')

                LOGGER.info(f"Process Remove empty folders from Synology Photos finished. Total removed folders: {total_removed}")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while removing empty folders from Synology Photos. {e}")
            
            return total_removed

    def rename_albums(self, pattern, pattern_to_replace, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Renames all albums in Synology Photos whose name matches the provided pattern.

        First, collects all albums that match the pattern and prepares the new names.
        Then, displays the list of albums to rename and asks the user for confirmation.
        If the user confirms, performs the renaming through the API.

        Args:
            pattern (str): The regex pattern to match album names.
            pattern_to_replace (str): The pattern to replace matches with.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            int: The number of albums renamed.
            :param request_user_confirmation:
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.warning(f"Searching for albums that match the provided pattern. This process may take some time. Please be patient...")
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                LOGGER.info(f"No albums found.")
                # self.logout(log_level=log_level)
                return 0

            albums_to_rename = {}
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to rename", unit="albums"):
                album_date = album.get("create_time")
                if is_date_outside_range(album_date):
                    continue
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                if match_pattern(album_name, pattern):
                    new_name = replace_pattern(album_name, pattern=pattern, pattern_to_replace=pattern_to_replace)
                    albums_to_rename[album_id] = {
                        "album_name": album_name,
                        "new_name": new_name,
                    }

            if not albums_to_rename:
                LOGGER.info(f"No albums matched the pattern.")
                # self.logout(log_level=log_level)
                return 0

            # Display the albums that will be renamed
            LOGGER.info(f"Albums to be renamed:")
            for album_info in albums_to_rename.values():
                print(f"  '{album_info['album_name']}' --> '{album_info['new_name']}'")

            # Ask for confirmation only if requested
            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                return 0

            total_renamed_albums = 0
            for album_id, album_info in albums_to_rename.items():
                url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
                headers = {}
                if self.SYNO_TOKEN_HEADER:
                    headers.update(self.SYNO_TOKEN_HEADER)
                params = {
                    'api': 'SYNO.Foto.Browse.Album',
                    'version': '1',
                    'method': 'set_name',
                    'id': album_id,
                    'name': album_info["new_name"],
                }
                response = self.SESSION.get(url, params=params, headers=headers, verify=False)
                if response.ok:
                    LOGGER.info(f"Album '{album_info['album_name']}' (ID={album_id}) renamed to '{album_info['new_name']}'.")
                    total_renamed_albums += 1

            LOGGER.info(f"Renamed {total_renamed_albums} albums whose names matched the provided pattern.")
            # self.logout(log_level=log_level)
            return total_renamed_albums

    def remove_albums_by_name(self, pattern, removeAlbumsAssets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Synology Photos whose name matches the provided pattern.

        If removeAlbumsAssets is True, it also deletes all assets inside the matching albums.
        If request_user_confirmation is True, displays the albums to be deleted and asks for user confirmation before proceeding.

        Args:
            pattern (str): The regex pattern to match album names.
            removeAlbumsAssets (bool): Whether to delete all assets contained in the albums.
            request_user_confirmation (bool): Whether to ask for confirmation before deleting.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            tuple: (number of albums removed, number of assets removed)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.warning(f"Searching for albums that match the provided pattern. This process may take some time. Please be patient...")
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                LOGGER.info(f"No albums found.")
                # self.logout(log_level=log_level)
                return 0, 0

            albums_to_remove = []
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to remove", unit="albums"):
                album_date = album.get("create_time")
                if is_date_outside_range(album_date):
                    continue
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                if match_pattern(album_name, pattern):
                    albums_to_remove.append({
                        "album_id": album_id,
                        "album_name": album_name
                    })

            if not albums_to_remove:
                LOGGER.info(f"No albums matched the pattern.")
                # self.logout(log_level=log_level)
                return 0, 0

            # Display the albums that will be removed
            LOGGER.warning(f"Albums marked for deletion:")
            for album_info in albums_to_remove:
                LOGGER.warning(f"{album_info['album_name']}' (ID={album_info['album_id']})")

            # Ask for confirmation only if requested
            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                # self.logout(log_level=log_level)
                return 0, 0

            total_removed_albums = 0
            total_removed_assets = 0
            for album_info in albums_to_remove:
                album_id = album_info["album_id"]
                album_name = album_info["album_name"]
                if removeAlbumsAssets:
                    album_assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                    album_assets_ids = [asset.get("id") for asset in album_assets if asset.get("id")]
                    if album_assets_ids:
                        self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                        total_removed_assets += len(album_assets_ids)
                if self.remove_album(album_id, album_name):
                    LOGGER.info(f"Album '{album_name}' (ID={album_id}) removed.")
                    total_removed_albums += 1

            LOGGER.info(f"Removed {total_removed_albums} albums whose names matched the provided pattern.")
            LOGGER.info(f"Removed {total_removed_assets} assets from those removed albums.")
            # self.logout(log_level=log_level)
            return total_removed_albums, total_removed_assets


    def remove_all_albums(self, removeAlbumsAssets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Synology Photos, and optionally all their associated assets.

        If request_user_confirmation is True, displays the albums to be deleted and asks for user confirmation before proceeding.

        Args:
            removeAlbumsAssets (bool): Whether to remove all assets inside the albums.
            request_user_confirmation (bool): Whether to ask for confirmation before deleting.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            tuple: (number of albums removed, number of assets removed)
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
                if not albums:
                    LOGGER.info(f"No albums found.")
                    return 0, 0

                albums_to_remove = []
                for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to remove", unit="albums"):
                    album_date = album.get("create_time")
                    if is_date_outside_range(album_date):
                        continue

                    album_id = album.get("id")
                    album_name = album.get("albumName", "")

                    albums_to_remove.append({
                        "album_id": album_id,
                        "album_name": album_name
                    })

                if not albums_to_remove:
                    LOGGER.info(f"No albums found to remove after date filtering.")
                    return 0, 0

                # Display albums that will be removed
                LOGGER.warning(f"Albums marked for deletion:")
                for album_info in albums_to_remove:
                    LOGGER.warning(f"'{album_info['album_name']}' (ID={album_info['album_id']})")

                # Ask for confirmation only if requested
                if request_user_confirmation and not confirm_continue():
                    LOGGER.info(f"Exiting program.")
                    return 0, 0

                total_removed_albums = 0
                total_removed_assets = 0

                for album_info in albums_to_remove:
                    album_id = album_info["album_id"]
                    album_name = album_info["album_name"]

                    if removeAlbumsAssets:
                        album_assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                        album_assets_ids = [asset.get("id") for asset in album_assets if asset.get("id")]
                        if album_assets_ids:
                            assets_removed = self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                            total_removed_assets += assets_removed

                    if self.remove_album(album_id, album_name, log_level=logging.WARNING):
                        LOGGER.info(f"Album '{album_name}' (ID={album_id}) removed.")
                        total_removed_albums += 1

                # Try to remove empty albums if any remain
                LOGGER.info(f"Getting empty albums to remove...")
                empty_albums_removed = self.remove_empty_albums(log_level=logging.WARNING)
                total_removed_albums += empty_albums_removed

                LOGGER.info(f"Removed {total_removed_albums} albums.")
                if removeAlbumsAssets:
                    LOGGER.info(f"Removed {total_removed_assets} assets associated with those albums.")

            except Exception as e:
                LOGGER.error(f"Exception while removing all albums from Synology Photos: {e}")

            return total_removed_albums, total_removed_assets


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
                albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
                if not albums:
                    LOGGER.info(f"No albums found.")
                    # self.logout(log_level=log_level)
                    return 0

                total_removed_empty_albums = 0
                LOGGER.info(f"Looking for empty albums in Synology Photos...")
                for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for Empty Albums", unit=" albums"):
                    # Check if Album Creation date is outside filters date range (if provided), in that case, skip this album
                    album_date = album.get("create_time")
                    if is_date_outside_range(album_date):
                        continue

                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    asset_count = self.get_album_assets_count(album_id, album_name, log_level=logging.WARNING)
                    if asset_count == 0:
                        if self.remove_album(album_id, album_name):
                            LOGGER.info(f"Empty album '{album_name}' (ID={album_id}) removed.")
                            total_removed_empty_albums += 1

                LOGGER.info(f"Removed {total_removed_empty_albums} empty albums.")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while removing empties albums from Synology Photos. {e}")
            
            return total_removed_empty_albums

    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all duplicate albums in Synology Photos.

        Duplicates are albums that share the same asset count and total asset size.
        The function keeps the first album (sorted by album ID) and removes the rest.
        Before deleting, it displays the list of albums to be removed and asks for user confirmation.

        Args:
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            int: The number of duplicate albums deleted.
            :param request_user_confirmation:
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)

                if not albums:
                    # self.logout(log_level=log_level)
                    return 0

                LOGGER.info(f"Searching for duplicate albums in Synology Photos...")
                duplicates_map = {}
                for album in tqdm(albums, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Searching for duplicate albums", unit="albums"):
                    album_date = album.get("create_time")
                    if is_date_outside_range(album_date):
                        continue
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    assets_count = self.get_album_assets_count(album_id, album_name, log_level=log_level)
                    assets_size = self.get_album_assets_size(album_id, album_name, log_level=log_level)
                    duplicates_map.setdefault((assets_count, assets_size), []).append((album_id, album_name))

                albums_to_remove = []
                for (assets_count, assets_size), group in duplicates_map.items():
                    LOGGER.debug(f"Assets Count: {assets_count}. Assets Size: {assets_size}.")
                    if len(group) > 1:
                        group_sorted = sorted(group, key=lambda x: x[0])  # Sort by album ID
                        to_remove = group_sorted[1:]  # Keep the first, remove the rest
                        albums_to_remove.extend(to_remove)

                if not albums_to_remove:
                    LOGGER.info(f"No duplicate albums found.")
                    # self.logout(log_level=log_level)
                    return 0

                # Display the albums that will be removed
                LOGGER.info(f"Albums marked for deletion:")
                for alb_id, alb_name in albums_to_remove:
                    print(f"  '{alb_name}' (ID={alb_id})")

                # Ask for confirmation
                if not confirm_continue():
                    LOGGER.info(f"Exiting program.")
                    # self.logout(log_level=log_level)
                    return 0

                total_removed_duplicated_albums = 0
                for alb_id, alb_name in albums_to_remove:
                    LOGGER.info(f"Removing duplicate album: '{alb_name}' (ID={alb_id})")
                    if self.remove_album(alb_id, alb_name, log_level=log_level):
                        total_removed_duplicated_albums += 1

                LOGGER.info(f"Removed {total_removed_duplicated_albums} duplicate albums.")

            except Exception as e:
                LOGGER.error(f"Exception while removing duplicate albums from Synology Photos: {e}")

            # self.logout(log_level=log_level)
            return total_removed_duplicated_albums


    def merge_duplicates_albums(self, strategy='count', request_user_confirmation=True, log_level=logging.WARNING):
        """
        Remove all duplicate albums in Synology Photos. Duplicates are albums
        that share the same album name. Keeps the one with the most assets or largest size
        (depending on strategy), merges the rest into it, and removes the duplicates.

        Args:
            strategy (str): 'count' to keep album with most assets, 'size' to keep album with largest size
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of duplicate albums deleted.
            :param request_user_confirmation:
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)

                if not albums:
                    return 0

                LOGGER.info(f"Looking for duplicate albums in Synology Photos...")
                albums_by_name = {}
                for album in tqdm(albums, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Grouping Albums by Name", unit=" albums"):
                    # Check if Album Creation date is outside filters date range (if provided), in that case, skip this album
                    album_date = album.get("create_time")
                    if is_date_outside_range(album_date):
                        continue

                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    assets_count = self.get_album_assets_count(album_id, album_name, log_level=log_level)
                    if strategy == 'size':
                        assets_size = self.get_album_assets_size(album_id, album_name, log_level=log_level)
                    else:
                        assets_size = 'Undefined'
                    albums_by_name.setdefault(album_name, []).append({
                        "id": album_id,
                        "name": album_name,
                        "count": assets_count,
                        "size": assets_size
                    })

                # Comprobar si hay algún grupo con más de un álbum
                if any(len(album_group) > 1 for album_group in albums_by_name.values()):
                    # Contar cuántos álbumes duplicados se van a unir
                    duplicate_albums = sum(len(group) - 1 for group in albums_by_name.values() if len(group) > 1)
                    LOGGER.info(f"A total of {duplicate_albums} duplicate albums will be merged (keeping only one per name).")
                    # Loop through each album name and its group to show all Duplicates Albums and request User Confirmation to continue
                    LOGGER.info(f"The following Albums are duplicates (by Name) and will be merged into the first album:")
                    for album_name, album_group in albums_by_name.items():
                        if len(album_group) > 1:
                            # Ordenar el grupo según la estrategia
                            if strategy == 'size':
                                sorted_group = sorted(album_group, key=lambda x: x["size"], reverse=True)
                            else:  # Default to 'count'
                                sorted_group = sorted(album_group, key=lambda x: x["count"], reverse=True)

                            # El primero es el que se queda
                            main_album = sorted_group[0]
                            albums_to_delete = sorted_group[1:]

                            # Mostrarlo en el log
                            LOGGER.info(f"{album_name}:")
                            LOGGER.info(f"          [KEEP ] {main_album}")
                            for album in albums_to_delete:
                                LOGGER.info(f"          [MERGE] {album}")
                    LOGGER.info(f"")

                    # Ask for confirmation only if requested
                    if request_user_confirmation and not confirm_continue():
                        LOGGER.info(f"Exiting program.")
                        return 0


                total_merged_albums = 0
                total_removed_duplicated_albums = 0
                for album_name, group in albums_by_name.items():
                    if len(group) <= 1:
                        continue  # no duplicates

                    # Select strategy
                    if strategy == 'size':
                        sorted_group = sorted(group, key=lambda x: x['size'], reverse=True)
                    else:
                        sorted_group = sorted(group, key=lambda x: x['count'], reverse=True)

                    keeper = sorted_group[0]
                    keeper_id = keeper["id"]
                    keeper_name = keeper["name"]

                    LOGGER.info(f"Keeping album '{keeper_name}' (ID={keeper_id}) with {keeper['count']} assets and {keeper['size']} bytes.")

                    for duplicate in sorted_group[1:]:
                        dup_id = duplicate["id"]
                        dup_name = duplicate["name"]

                        LOGGER.debug(f"Transferring assets from duplicate album '{dup_name}' (ID={dup_id})")
                        assets = self.get_all_assets_from_album(dup_id, dup_name, log_level=log_level)
                        asset_ids = [asset["id"] for asset in assets] if assets else []
                        if asset_ids:
                            self.add_assets_to_album(keeper_id, asset_ids, keeper_name, log_level=log_level)

                        LOGGER.info(f"Removing duplicate album: '{dup_name}' (ID={dup_id})")
                        if self.remove_album(dup_id, dup_name, log_level=log_level):
                            total_removed_duplicated_albums += 1
                    total_merged_albums += 1

                LOGGER.info(f"Removed {total_removed_duplicated_albums} duplicate albums belonging to {total_merged_albums} different Albums groups.")
                # self.logout(log_level=log_level)

            except Exception as e:
                LOGGER.error(f"Exception while removing duplicates albums from Synology Photos. {e}")

            return total_merged_albums, total_removed_duplicated_albums

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
                LOGGER.info(f"Getting list of asset(s) to remove...")

                all_assets = self.get_assets_by_filters(log_level=log_level)
                combined_ids = [a.get("id") for a in all_assets if a.get("id")]

                total_assets_found = len(combined_ids)
                if total_assets_found == 0:
                    LOGGER.warning(f"No Assets found that matches filters criteria in Synology Photos.")
                LOGGER.info(f"Found {total_assets_found} asset(s) to remove.")

                removed_assets = 0
                BATCH_SIZE = 250
                i = 0
                while i < len(combined_ids):
                    batch = combined_ids[i:i + BATCH_SIZE]
                    removed_assets += self.remove_assets(batch, log_level=log_level)
                    i += BATCH_SIZE

                LOGGER.info(f"Removing empty folders if remain...")
                removed_folders = self.remove_empty_folders(log_level=log_level)

                LOGGER.info(f"Removing empty albums if remain...")
                removed_albums = self.remove_empty_albums(log_level=log_level)

                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while removing ALL assets from Synology Photos. {e}")
            
            return (removed_assets, removed_albums, removed_folders)


##############################################################################
#                                END OF CLASS                                #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.
    from Utils.StandaloneUtils import change_working_dir
    change_working_dir()

    # Create the Object
    syno = ClassSynologyPhotos()

    # Read configuration and log in
    syno.read_config_file(CONFIGURATION_FILE)
    syno.login(use_syno_token=True)
    # login(use_syno_token=False)

    # Example: remove_empty_albums()
    print("=== EXAMPLE: remove_empty_albums() ===")
    deleted = syno.remove_empty_albums()
    print(f"[RESULT] Empty albums deleted: {deleted}\n")

    # Example: remove_duplicates_albums()
    print("=== EXAMPLE: remove_duplicates_albums() ===")
    duplicates = syno.remove_duplicates_albums()
    print(f"[RESULT] Duplicate albums deleted: {duplicates}\n")

    # Example: push_asset()
    print("\n=== EXAMPLE: push_asset() ===")
    file_path = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\Albums\1994 - Recuerdos\169859_10150125237566327_578986326_8330690_6545.jpg"                # For Windows
    asset_id = syno.push_asset(file_path)
    if not asset_id:
        print(f"Error uploading asset '{file_path}'.")
    else:
        print(f"New Asset uploaded successfully with id: {asset_id}")

    # Example: push_no_albums()
    print("\n=== EXAMPLE: push_no_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/PhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing"                # For Windows
    syno.push_no_albums(input_folder)

    # Example: push_albums()
    print("\n=== EXAMPLE: push_albums() ===")
    # input_folder = "/volume1/homes/jaimetur/PhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing"                # For Windows
    syno.push_albums(input_folder)

    # Example: push_ALL()
    print("\n=== EXAMPLE: push_ALL() ===")
    # input_folder = "/volume1/homes/jaimetur/PhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing"                # For Windows
    syno.push_ALL(input_folder)

    # Example: pull_albums()
    print("\n=== EXAMPLE: pull_albums() ===")
    download_folder = r"r:\jaimetur\PhotoMigrator\Download_folder_for_testing"
    total_albums, total_assets = syno.pull_albums(albums_name='ALL', output_folder=download_folder)
    print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums}.\n")

    # Example: pull_no_albums()
    print("\n=== EXAMPLE: pull_no_albums() ===")
    download_folder = r"r:\jaimetur\PhotoMigrator\Download_folder_for_testing"
    total = syno.pull_no_albums(no_albums_folder=download_folder)
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # Example: pull_ALL
    print("=== EXAMPLE: pull_ALL() ===")
    total_struct = syno.pull_ALL(output_folder="Downloads_Synology")
    # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # Example: remove_empty_folders()
    print("\n=== EXAMPLE: remove_empty_folders() ===")
    total = syno.remove_empty_folders()
    print(f"[RESULT] A total of {total} folders have been removed.\n")

    # logout()
    syno.logout()

