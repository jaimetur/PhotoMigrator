# -*- coding: utf-8 -*-

import fnmatch
import json
import logging
import os
import re
import sys
import threading
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from urllib.parse import urlparse

import mimetypes
import requests
import urllib3
from dateutil import parser
from halo import Halo
from requests_toolbelt.multipart.encoder import MultipartEncoder
from tabulate import tabulate

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import LOGGER, ARGS, MSG_TAGS, FOLDERNAME_NO_ALBUMS, CONFIGURATION_FILE, FOLDERNAME_ALBUMS
from Features.BaseMediaClient import BaseMediaClient
from Utils.DateUtils import parse_text_datetime_to_epoch, is_date_outside_range
from Utils.FileUtils import matches_any_pattern, merge_exclusion_patterns
from Utils.GeneralUtils import update_metadata, convert_to_list, tqdm, match_pattern, replace_pattern, has_any_filter, confirm_continue, sha1_checksum, find_reusable_album_candidate, build_reusable_album_group, canonicalize_album_name_for_reuse, prefer_canonical_album_names_enabled, consolidate_similar_albums_enabled, scan_album_consolidation_groups, print_album_consolidation_preview
from Utils.StandaloneUtils import change_working_dir

"""
--------------------
ClassImmichPhotos.py
--------------------
Python module with example functions to interact with Immich Photos, including following functions:
  - Configuration (read config)
  - Authentication (login/logout)
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Removing empty or duplicate albums
  - Main functions for use in other modules:
     - remove_empty_albums()
     - remove_duplicates_albums()
     - immich_upload_folder()
     - push_albums()
     - pull_albums()
     - pull_all()
"""

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassImmichPhotos(BaseMediaClient):
    """
    Encapsulates all the functionality from the original ClassImmichPhotos.py
    into a single class that uses a global LOGGER from GlobalVariables.
    """
    def __init__(self, account_id=1):
        """
        Constructor that initializes what used to be global variables.
        Also imports the global LOGGER from GlobalVariables.
        """
        self.ACCOUNT_ID = str(account_id)        # Used to identify wich Account to use from the configuration file
        if account_id not in [1, 2, 3]:
            LOGGER.error(f"Cannot create Immich Photos object with ACCOUNT_ID: {account_id}. Valid valies are [1, 2]. Exiting...")
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
        self.ALLOWED_IMMICH_PHOTO_EXTENSIONS = []
        self.ALLOWED_IMMICH_VIDEO_EXTENSIONS = []
        self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = []
        self.ALLOWED_IMMICH_EXTENSIONS = []
        self.IMMICH_MEDIA_TYPES_CACHE = None
        self.CURRENT_USER_PROFILE = None

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
        self.person_ids_list = None

        # login to get CLIENT_ID
        self.login()
        self.CLIENT_ID = self.get_user_mail()

        self.CLIENT_NAME = f'Immich Photos ({self.CLIENT_ID})'


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

            # Verify required parameters and prompt on screen if missing
            if not self.IMMICH_URL or self.IMMICH_URL.strip() == '':
                LOGGER.warning(f"IMMICH_URL not found. It will be requested on screen.")
                self.CONFIG['IMMICH_URL'] = input("[PROMPT] Enter IMMICH_URL (e.g., http://192.168.1.100:2283): ")
                self.IMMICH_URL = self.CONFIG['IMMICH_URL']
            if not self.IMMICH_USER_API_KEY or self.IMMICH_USER_API_KEY.strip() == '':
                if not self.IMMICH_USERNAME or self.IMMICH_USERNAME.strip() == '':
                    LOGGER.warning(f"IMMICH_USERNAME not found. It will be requested on screen.")
                    self.CONFIG['IMMICH_USERNAME'] = input("[PROMPT] Enter IMMICH_USERNAME (Immich email): ")
                    self.IMMICH_USERNAME = self.CONFIG['IMMICH_USERNAME']
                if not self.IMMICH_PASSWORD or self.IMMICH_PASSWORD.strip() == '':
                    LOGGER.warning(f"IMMICH_PASSWORD not found. It will be requested on screen.")
                    self.CONFIG['IMMICH_PASSWORD'] = input("[PROMPT] Enter IMMICH_PASSWORD: ")
                    self.IMMICH_PASSWORD = self.CONFIG['IMMICH_PASSWORD']
            else:
                self.API_KEY_LOGIN = True
                LOGGER.info(f"")
                LOGGER.info(f"Immich Config Read:")
                LOGGER.info(f"-------------------")
                LOGGER.info(f"IMMICH_URL            : {self.IMMICH_URL}")
                if self.API_KEY_LOGIN:
                    masked_admin_api = '*' * len(self.IMMICH_API_KEY_ADMIN)
                    masked_user_api = '*' * len(self.IMMICH_USER_API_KEY)
                    LOGGER.info(f"IMMICH_ADMIN_API_KEY  : {masked_admin_api}")
                    LOGGER.info(f"IMMICH_USER_API_KEY   : {masked_user_api}")
                else:
                    LOGGER.info(f"IMMICH_USERNAME       : {self.IMMICH_USERNAME}")
                    masked_password = '*' * len(self.IMMICH_PASSWORD)
                    LOGGER.info(f"IMMICH_PASSWORD       : {masked_password}")

            return self.CONFIG


    ###########################################################################
    #                         AUTHENTICATION / LOGOUT                         #
    ###########################################################################
    def login(self, log_level=None):
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
            LOGGER.info(f"")
            LOGGER.info(f"Authenticating on Immich Photos and getting Session...")

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
                    LOGGER.error(f"Exception occurred during Immich login: {str(e)}")
                    return False
                

                self.HEADERS_WITH_CREDENTIALS = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'x-api-key': self.IMMICH_USER_API_KEY
                }
                LOGGER.info(f"Authentication Successfully with IMMICH_USER_API_KEY found in Config file.")
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
                    LOGGER.error(f"Exception occurred during Immich login: {str(e)}")
                    return False
                

                data = response.json()
                self.SESSION_TOKEN = data.get("accessToken", None)
                if not self.SESSION_TOKEN:
                    LOGGER.error(f"'accessToken' not found in the response: {data}")
                    return False

                self.HEADERS_WITH_CREDENTIALS = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.SESSION_TOKEN}'
                }
                LOGGER.info(f"Authentication Successfully with user/password found in Config file.")

            # Now retrieve list of allowed media/sidecar extensions
            media_types = self._get_media_types_payload(log_level=logging.WARNING) or {}
            self.ALLOWED_IMMICH_PHOTO_EXTENSIONS = media_types.get("image", []) or []
            self.ALLOWED_IMMICH_VIDEO_EXTENSIONS = media_types.get("video", []) or []
            self.ALLOWED_IMMICH_MEDIA_EXTENSIONS = (self.ALLOWED_IMMICH_PHOTO_EXTENSIONS or []) + (self.ALLOWED_IMMICH_VIDEO_EXTENSIONS or [])
            self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = media_types.get("sidecar", []) or []
            self.ALLOWED_IMMICH_EXTENSIONS = self.ALLOWED_IMMICH_MEDIA_EXTENSIONS + self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS
            return True


    def logout(self, log_level=None):
        """
        Logout locally by discarding the token. (Immich does not provide an official /logout endpoint).

        Args:
            log_level (logging.LEVEL): log_level for logs and console
        """
        with set_log_level(LOGGER, log_level):
            self.SESSION_TOKEN = None
            self.HEADERS_WITH_CREDENTIALS = {}
            LOGGER.info(f"Session closed locally (Bearer Token discarded).")


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def get_supported_media_types(self, type='media', log_level=None):
        """
        Returns the supported media/sidecar extensions as reported by Immich (via /api/server/media-types).
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            try:
                data = self._get_media_types_payload(log_level=log_level) or {}
                image = data.get("image", []) or []
                video = data.get("video", []) or []
                sidecar = data.get("sidecar", []) or []

                if type.lower() == 'media':
                    supported_types = image + video
                    LOGGER.debug(f"Supported media types: '{supported_types}'.")
                elif type.lower() == 'image':
                    supported_types = image
                    LOGGER.debug(f"Supported image types: '{supported_types}'.")
                elif type.lower() == 'video':
                    supported_types = video
                    LOGGER.debug(f"Supported video types: '{supported_types}'.")
                elif type.lower() == 'sidecar':
                    supported_types = sidecar
                    LOGGER.debug(f"Supported sidecar types: '{supported_types}'.")
                else:
                    LOGGER.error(f"Invalid type '{type}' to get supported media types. Types allowed are 'media', 'image', 'video' or 'sidecar'")
                    return None
                return supported_types
            except Exception as e:
                LOGGER.error(f"Cannot get Supported media types: {e}")
                return None

    def _get_media_types_payload(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if isinstance(self.IMMICH_MEDIA_TYPES_CACHE, dict):
                return self.IMMICH_MEDIA_TYPES_CACHE
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/server/media-types"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS)
                resp.raise_for_status()
                data = resp.json() or {}
                self.IMMICH_MEDIA_TYPES_CACHE = data if isinstance(data, dict) else {}
                return self.IMMICH_MEDIA_TYPES_CACHE
            except Exception as e:
                LOGGER.error(f"Cannot get Supported media types: {e}")
                return None

    def _get_current_user_profile(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if isinstance(self.CURRENT_USER_PROFILE, dict) and self.CURRENT_USER_PROFILE.get("id"):
                return self.CURRENT_USER_PROFILE
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/users/me"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, data={})
                resp.raise_for_status()
                data = resp.json() or {}
                if isinstance(data, dict):
                    self.CURRENT_USER_PROFILE = data
                    return data
                return None
            except Exception as e:
                LOGGER.error(f"Cannot retrieve current Immich user profile for '{self.IMMICH_USERNAME}': {e}")
                return None


    def get_user_id(self, log_level=None):
        """
        Returns the user_id of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            try:
                data = self._get_current_user_profile(log_level=log_level) or {}
                user_id = data.get("id")
                user_mail = data.get("email")
                LOGGER.info(f"User ID: '{user_id}' found for user '{user_mail}'.")
                LOGGER.info(f"")
                return user_id
            except Exception as e:
                LOGGER.error(f"Cannot find User ID for user '{self.IMMICH_USERNAME}': {e}")
                return None


    def get_user_mail(self, log_level=None):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            try:
                data = self._get_current_user_profile(log_level=log_level) or {}
                user_id = data.get("id")
                user_mail = data.get("email")
                LOGGER.info(f"User ID: '{user_id}' found for user '{user_mail}'.")
                LOGGER.info(f"")
                return user_mail
            except Exception as e:
                LOGGER.error(f"Cannot find User ID for user '{self.IMMICH_USERNAME}': {e}")
                return None

    def get_person_id(self, name, log_level=None):
        """
        Returns the ID of the first person matching the given name.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/search/person"
            params = {"name": name}
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, params=params)
                resp.raise_for_status()
                data = resp.json()
                if data:
                    person_id = data[0].get("id")
                    LOGGER.info(f"ID '{person_id}' found for person '{name}'.")
                    return person_id
                else:
                    LOGGER.info(f"No person found with name '{name}'.")
                    return None
            except Exception as e:
                LOGGER.error(f"Cannot find ID for person '{name}': {e}")
                return None

    ###########################################################################
    #                           ALBUMS FUNCTIONS                              #
    ###########################################################################
    def create_album(self, album_name, shared=False, log_level=None):
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
                LOGGER.debug(f"Album '{album_name}' created with ID: {album_id}")
                return album_id
            except Exception as e:
                LOGGER.warning(f"Cannot create album '{album_name}' due to API call error. Skipped! {e}")
                return None



    def remove_album(self, album_id, album_name, log_level=None):
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
                if 200 <= response.status_code < 300:
                    LOGGER.info(f"Album '{album_name}' with ID={album_id} removed (status: {response.status_code}).")
                    return True
                else:
                    LOGGER.warning(f"Failed to remove album: '{album_name}' with ID: {album_id}. Status: {response.status_code}")
                    return False
            except Exception as e:
                LOGGER.error(f"Error while removing album '{album_name}' with ID:  {album_id}: {e}")
                return False


    @staticmethod
    def _get_album_owner_id(album):
        """
        Return the owner user id of an album, compatible with all Immich versions.

        Immich <= v2 exposes 'ownerId' directly on the album object. Immich v3 removed
        'ownerId' (and the 'owner' object) from AlbumResponseDto and moved that information
        into 'albumUsers' as the entry whose role is 'owner'.

        Args:
            album (dict): Album object as returned by the Immich API.

        Returns:
            str: The owner user id, or None if it cannot be determined.
        """
        owner_id = album.get('ownerId')
        if owner_id:
            return owner_id
        for album_user in album.get('albumUsers', []) or []:
            if album_user.get('role') == 'owner':
                return (album_user.get('user') or {}).get('id')
        return None


    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
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
            :param filter_assets:
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums"
            try:
                LOGGER.info("Retrieving owned albums from Immich Photos. This may take some time, please be patient...")
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                albums = resp.json()
                user_id = self.get_user_id(log_level=logging.WARNING)
                albums_filtered = []
                for album in albums:
                    owner_id = self._get_album_owner_id(album)
                    # Guard against None == None: if neither the album owner nor the current
                    # user id can be determined, do not treat the album as owned by the user.
                    if owner_id is not None and owner_id == user_id:
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
                LOGGER.error(f"Error while listing albums: {e}")
                return None


    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
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
            :param filter_assets:
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums"
            try:
                LOGGER.info("Retrieving owned and shared albums from Immich Photos. This may take some time, please be patient...")
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                albums = resp.json()
                albums_filtered = []
                for album in albums:
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
                LOGGER.error(f"Error while listing albums: {e}")
                return None


    def get_album_assets_size(self, album_id, album_name=None, type='all', album_passphrase=None, album_scope=None, log_level=None):
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
                assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                total_size = 0
                for asset in assets:
                    exif_info = asset.get("exifInfo", {})
                    if "fileSizeInByte" in exif_info:
                        total_size += exif_info["fileSizeInByte"]
                return total_size
            except Exception:
                return -1



    def get_album_assets_count(self, album_id, album_name=None, type='all', album_passphrase=None, album_scope=None, log_level=None):
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
                assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                return len(assets)
            except Exception:
                return -1



    def album_exists(self, album_name, shared=False, log_level=None):
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
                albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
                if not albums:
                    return False, None
                for album in albums:
                    if album_name == album.get("albumName"):
                        album_exists = True
                        album_id = album.get("id")
                        self.albums_owned_by_user[album_name] = album_id  # Cache it for future use
                        break  # Stop searching once found
            return album_exists, album_id


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
                LOGGER.error(f"Exception while filtering Assets from Immich Photos. {e}")

    def filter_assets_by_type(self, assets, type):
        """
        Filters a list of assets by their type, supporting flexible type aliases.

        Accepted values for 'type':
        - 'image', 'images', 'photo', 'photos' → treated as 'IMAGE'
        - 'video', 'videos' → treated as 'VIDEO'
        - 'all' → returns all assets (no filtering)

        Matching is case-insensitive.

        Args:
            assets (list): List of asset dictionaries to be filtered.
            type (str): The asset type to match.

        Returns:
            list: A filtered list of assets with the specified type.
        """
        if not type or type.lower() == "all":
            return assets
        type_lower = type.lower()
        image_aliases = {"image", "images", "photo", "photos"}
        video_aliases = {"video", "videos"}
        if type_lower in image_aliases:
            target_type = "IMAGE"
        elif type_lower in video_aliases:
            target_type = "VIDEO"
        else:
            return []  # Unknown type alias
        return [asset for asset in assets if asset.get("type", "").upper() == target_type]

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
        Filters a list of assets by matching the given place name against the 'city', 'state',
        or 'country' fields in the 'exifInfo' dictionary of each asset.

        Matching is case-insensitive and partial (substring match). Assets without 'exifInfo'
        or with none of the fields present will be ignored.

        Args:
            assets (list): List of asset dictionaries.
            place (str): Name of the place to match (case-insensitive).

        Returns:
            list: A filtered list of assets that match the given place in 'city', 'state', or 'country'.
        """
        filtered = []
        place_lower = place.lower()
        for asset in assets:
            exif = asset.get("exifInfo", {})
            if not exif:
                continue
            for key in ("city", "state", "country"):
                value = exif.get(key)
                if isinstance(value, str) and place_lower in value.lower():
                    filtered.append(asset)
                    break  # Match found, no need to check other fields
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
        if not person_name:
            return assets
        name_lower = person_name.lower()
        filtered = []
        for asset in assets:
            asset_id = asset.get("id")
            # people = asset.get("people", [])
            people = self.get_asset_people(asset_id)
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
    def get_asset_people(self, asset_id, log_level=None):
        """
        Get assets iinfo.

        Args:
            asset_id (str): ID of the asset.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of asset info (dict objects). [] if no assets found.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/assets/{asset_id}"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                data = resp.json()
                people_list = data.get("people", [])
                return people_list
            except Exception as e:
                LOGGER.error(f"Failed to retrieve assets info for '{asset_id}': {str(e)}")
                return []

    def get_assets_by_filters(self, type='all', is_not_in_album=None, is_archived=None, with_deleted=None, log_level=logging.WARNING):
        """
        Lists all assets in Immich Photos that match with the specified filters.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of assets (dict) matching the specified filters in the entire library or Empty list on error.
            :param is_not_in_album:
            :param is_archived:
            :param with_deleted:
        """
        with set_log_level(LOGGER, log_level):
            try:
                # Reuse global cache only for the default "global search" shape.
                # Queries with is_not_in_album/is_archived/with_deleted are different datasets
                # and must not poison the global cache.
                use_global_cache = (is_not_in_album is None and is_archived is None and with_deleted is None)

                if use_global_cache and self.all_assets_filtered is not None:
                    return self.all_assets_filtered

                # Obtain the correct type for the API call
                if self.type:
                    image_aliases = {"image", "images", "photo", "photos"}
                    video_aliases = {"video", "videos"}
                    type_lower = self.type.lower()
                    if type_lower in image_aliases:
                        self.type = "IMAGE"
                    elif type_lower in video_aliases:
                        self.type = "VIDEO"
                    elif type_lower == "all":
                        self.type = None  # No filtering needed
                    else:
                        self.type = None  # Unknown alias, treat as no filtering

                # Obtain the person_ids_list to include in the API call
                self.person_ids_list = []
                if self.person:
                    self.person_ids_list = self.get_person_id(name=self.person, log_level=log_level)
                    # If person was provided but person_ids_list is empty means that the person does not exists, so return []
                    if not self.person_ids_list:
                        if use_global_cache:
                            self.all_assets_filtered = []
                        return []


                self.login(log_level=log_level)
                url = f"{self.IMMICH_URL}/api/search/metadata"
                all_filtered_assets = []

                next_page = 1
                while True:
                    payload_data = {
                        "page": next_page,
                        "order": "desc",
                        # "withArchived": False,
                        # "with_deleted": False,
                        # "country": "string",
                        # "city": "string",
                        # "type": "IMAGE",
                        # "is_not_in_album": False,
                        # "is_archived": True,
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
                    if with_deleted:
                        payload_data["withDeleted"] = with_deleted
                    if is_not_in_album:
                        payload_data["isNotInAlbum"] = is_not_in_album
                    if is_archived:
                        payload_data["isArchived"] = is_archived

                    if self.from_date: payload_data["takenAfter"] = self.from_date
                    if self.to_date: payload_data["takenBefore"] = self.to_date
                    if self.country: payload_data["country"] = self.country
                    if self.city: payload_data["city"] = self.city
                    if self.person_ids_list: payload_data["personIds"] = [self.person_ids_list]
                    if self.type: payload_data["type"] = self.type

                    payload = json.dumps(payload_data)
                    resp = requests.post(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("assets", {}).get("items", [])
                    all_filtered_assets.extend(items)
                    next_page = data.get("assets", {}).get("nextPage", None)
                    if next_page is None:
                        break
            except Exception as e:
                LOGGER.error(f"Failed to retrieve assets: {str(e)}")

            # Add new fields "time" with the same value as "fileCreatedAt" and "filename" with the same value as "originalFileName" to allign with Synology Photos
            for asset in all_filtered_assets:
                asset["time"] = asset["fileCreatedAt"]
                asset["filename"] = asset["originalFileName"]

            if use_global_cache:
                self.all_assets_filtered = all_filtered_assets  # Cache global filtered assets for future use
            return all_filtered_assets


    def _get_album_assets_via_search(self, album_id, log_level=None):
        """
        Retrieve all assets of an album using 'POST /api/search/metadata' filtered by
        'albumIds', paginating through the results.

        This is required for Immich v3+, where the 'assets' property was removed from
        AlbumResponseDto (i.e. 'GET /api/albums/{id}' no longer returns the album's assets).
        It also works on older Immich versions, so it is safe to use as a fallback.

        Args:
            album_id (str): ID of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: Raw asset dicts belonging to the album ([] if the album is empty).

        Raises:
            Exception: Request/HTTP errors are intentionally propagated (not swallowed)
                so the caller treats a partially-paginated album as a failure and returns
                [] with an error, rather than silently returning a truncated list that
                looks complete.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/search/metadata"
            album_assets = []
            next_page = 1
            while True:
                # Immich returns 'nextPage' as a string, but 'page' is validated as an
                # integer (strictly, under v3's Zod validation), so coerce before sending.
                payload = json.dumps({"albumIds": [album_id], "page": int(next_page), "order": "desc"})
                resp = requests.post(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                album_assets.extend(data.get("assets", {}).get("items", []))
                next_page = data.get("assets", {}).get("nextPage", None)
                if next_page is None:
                    break
            return album_assets

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", album_scope=None, album_expected_count=None, log_level=None):
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
                # Immich <= v2 returns the album's assets inline in AlbumResponseDto.
                # Immich v3 removed the 'assets' property from GET /api/albums/{id}, so fall
                # back to POST /api/search/metadata (filtered by albumIds) to fetch them. The
                # inline path is kept for backward compatibility with older Immich servers.
                if isinstance(data.get("assets"), list):
                    album_assets = data.get("assets", [])
                else:
                    album_assets = self._get_album_assets_via_search(album_id, log_level=log_level)
                # Add new fields "time" with the same value as "fileCreatedAt" and "filename" with the same value as "originalFileName" to allign with Synology Photos
                for asset in album_assets:
                    asset["time"] = asset["fileCreatedAt"]
                    asset["filename"] = asset["originalFileName"]

                if has_any_filter():
                    return self.filter_assets(assets=album_assets, log_level=log_level)
                return album_assets
            except Exception as e:
                if album_name:
                    LOGGER.error(f"Failed to retrieve assets from album '{album_name}': {str(e)}")
                else:
                    LOGGER.error(f"Failed to retrieve assets from album ID={album_id}: {str(e)}")
                return []

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, album_scope=None, album_expected_count=None, log_level=None):
        """
        Get assets in a specific album.

        Args:
            album_id (str): ID of the album.
            album_name (str): Name of the album.
            album_passphrase (str): Shared album passphrase
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: A list of photos in the album (dict objects). [] if no assets found.
        """
        # TODO: This method is just a copy of get_all_assets_from_album. Change to filter only shared albums
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/albums/{album_id}"
            try:
                resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS, verify=False)
                resp.raise_for_status()
                data = resp.json()
                # Immich <= v2 returns the album's assets inline in AlbumResponseDto.
                # Immich v3 removed the 'assets' property from GET /api/albums/{id}, so fall
                # back to POST /api/search/metadata (filtered by albumIds) to fetch them. The
                # inline path is kept for backward compatibility with older Immich servers.
                if isinstance(data.get("assets"), list):
                    album_assets = data.get("assets", [])
                else:
                    album_assets = self._get_album_assets_via_search(album_id, log_level=log_level)
                # Add new fields "time" with the same value as "fileCreatedAt" and "filename" with the same value as "originalFileName" to allign with Synology Photos
                for asset in album_assets:
                    asset["time"] = asset["fileCreatedAt"]
                    asset["filename"] = asset["originalFileName"]

                if has_any_filter():
                    return self.filter_assets(assets=album_assets, log_level=log_level)
                return album_assets
            except Exception as e:
                if album_name:
                    LOGGER.error(f"Failed to retrieve assets from album '{album_name}': {str(e)}")
                else:
                    LOGGER.error(f"Failed to retrieve assets from album ID={album_id}: {str(e)}")
                return []

    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        """
        Get assets not associated to any album from Immich Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_without_albums
        """
        with set_log_level(LOGGER, log_level):
            # If assets_without_albums is already cached, return it.
            if self.assets_without_albums_filtered is not None:
                return self.assets_without_albums_filtered

            self.login(log_level=log_level)
            LOGGER.info("Retrieving assets without associated albums from Immich Photos. This may take some time, please be patient...")
            assets_without_albums = self.get_assets_by_filters(is_not_in_album=True, log_level=log_level)
            LOGGER.info(f"Number of all_assets without Albums associated: {len(assets_without_albums)}")
            self.assets_without_albums_filtered = assets_without_albums  # Cache assets_without_albums for future use
            return assets_without_albums


    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            list: Albums Assets
        """
        with set_log_level(LOGGER, log_level):
            # If albums_assets is already cached, return it
            if self.albums_assets_filtered is not None:
                return self.albums_assets_filtered

            self.login(log_level=log_level)
            LOGGER.info("Gathering all albums' assets from Immich Photos. This may take some time, please be patient...")
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
            self.albums_assets_filtered = combined_assets  # Cache albums_assets for future use
            return combined_assets


    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None, return_details=False):
        """
        Adds photos (asset_ids) to an album.

        Args:
            album_id (str): The ID of the album to which we add assets.
            asset_ids (list or str): The IDs of assets to add.
            album_name (str): The name of the album.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int | dict: Number of assets confirmed in the album, or a details dict when
                        `return_details=True`.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not asset_ids:
                if return_details:
                    return {
                        "requested_count": 0,
                        "confirmed_count": 0,
                        "confirmed_asset_ids": set(),
                        "failed_asset_ids": set(),
                        "real_failures": [],
                    }
                return 0
            asset_ids = convert_to_list(asset_ids)
            url = f"{self.IMMICH_URL}/api/albums/{album_id}/assets"
            payload = json.dumps({"ids": asset_ids})
            try:
                resp = requests.put(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                total_added = sum(1 for item in data if item.get("success"))
                confirmed_asset_ids = set()
                failed_asset_ids = set()
                duplicate_like_failures = []
                real_failures = []
                for index, item in enumerate(data):
                    item_asset_id = str(
                        item.get("id")
                        or item.get("assetId")
                        or item.get("asset_id")
                        or ""
                    ).strip()
                    if not item_asset_id and index < len(asset_ids):
                        item_asset_id = str(asset_ids[index]).strip()
                    if item.get("success"):
                        if item_asset_id:
                            confirmed_asset_ids.add(item_asset_id)
                        continue
                    error_text = " ".join([
                        str(item.get("error") or ""),
                        str(item.get("message") or ""),
                        str(item.get("reason") or ""),
                    ]).strip().lower()
                    if "duplicate" in error_text or "already" in error_text:
                        if item_asset_id:
                            confirmed_asset_ids.add(item_asset_id)
                        duplicate_like_failures.append(item)
                    else:
                        if item_asset_id:
                            failed_asset_ids.add(item_asset_id)
                        real_failures.append(item)

                confirmed_count = total_added + len(duplicate_like_failures)
                if real_failures:
                    LOGGER.warning(
                        f"Immich album association confirmed {confirmed_count}/{len(asset_ids)} asset(s) "
                        f"for album '{album_name or album_id}'. Failed items: {real_failures[:3]}"
                    )
                if return_details:
                    return {
                        "requested_count": len(asset_ids),
                        "confirmed_count": confirmed_count,
                        "confirmed_asset_ids": confirmed_asset_ids,
                        "failed_asset_ids": failed_asset_ids,
                        "real_failures": real_failures,
                    }
                return confirmed_count
            except Exception as e:
                if album_name:
                    LOGGER.error(f"Error while adding assets to album '{album_name}' with ID={album_id}: {e}")
                else:
                    LOGGER.error(f"Error while adding assets to album with ID={album_id}: {e}")
                if return_details:
                    return {
                        "requested_count": len(asset_ids),
                        "confirmed_count": 0,
                        "confirmed_asset_ids": set(),
                        "failed_asset_ids": {str(asset_id).strip() for asset_id in asset_ids if str(asset_id).strip()},
                        "real_failures": [str(e)],
                    }
                return 0

    @staticmethod
    def _upsert_existing_album(existing_albums, album_id, album_name):
        if existing_albums is None or not album_id:
            return
        album_id = str(album_id).strip()
        existing_albums[:] = [
            album for album in existing_albums
            if str((album or {}).get("id", "")).strip() != album_id
        ]
        existing_albums.append({"id": album_id, "albumName": album_name})

    def consolidate_reusable_album_group(self, album_name, existing_albums=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            existing_albums = existing_albums if existing_albums is not None else (self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or [])
            plan = build_reusable_album_group(
                album_name=album_name,
                albums=existing_albums,
                allow_similar=True,
                exact_case_sensitive=True,
            )
            if not plan.get("matched_album") and not plan.get("similar_albums"):
                return None, plan
            preferred_album_name = str(plan.get("preferred_album_name") or album_name).strip() or album_name
            keeper_album = plan.get("keeper_album")
            keeper_id = str((keeper_album or {}).get("id", "")).strip() if keeper_album else ""
            keeper_name = str((keeper_album or {}).get("albumName", "")).strip() if keeper_album else ""

            if not keeper_id or keeper_name.casefold() != preferred_album_name.casefold():
                keeper_id = self.create_album(preferred_album_name, log_level=log_level)
                if not keeper_id:
                    return None, plan
                keeper_name = preferred_album_name
                keeper_album = {"id": keeper_id, "albumName": keeper_name}
                self._upsert_existing_album(existing_albums, keeper_id, keeper_name)

            keeper_asset_ids = None
            for redundant_album in plan.get("similar_albums") or []:
                redundant_id = str((redundant_album or {}).get("id", "")).strip()
                redundant_name = str((redundant_album or {}).get("albumName", "")).strip()
                if not redundant_id or redundant_id == keeper_id:
                    continue
                duplicate_assets = self.get_all_assets_from_album(redundant_id, log_level=log_level) or []
                duplicate_asset_ids = [str(asset.get("id", "")).strip() for asset in duplicate_assets if str(asset.get("id", "")).strip()]
                total_redundant_assets = len(duplicate_asset_ids)
                reassigned_count = 0
                should_remove_redundant = False
                if duplicate_asset_ids:
                    added_count = self.add_assets_to_album(keeper_id, duplicate_asset_ids, keeper_name, log_level=log_level)
                    keeper_assets = self.get_all_assets_from_album(keeper_id, log_level=log_level) or []
                    keeper_asset_ids = {str(asset.get("id", "")).strip() for asset in keeper_assets if str(asset.get("id", "")).strip()}
                    reassigned_count = sum(1 for asset_id in duplicate_asset_ids if asset_id in keeper_asset_ids)
                    missing_asset_ids = [asset_id for asset_id in duplicate_asset_ids if asset_id not in keeper_asset_ids]
                    if missing_asset_ids:
                        time.sleep(1.0)
                        keeper_assets = self.get_all_assets_from_album(keeper_id, log_level=log_level) or []
                        keeper_asset_ids = {str(asset.get("id", "")).strip() for asset in keeper_assets if str(asset.get("id", "")).strip()}
                        reassigned_count = sum(1 for asset_id in duplicate_asset_ids if asset_id in keeper_asset_ids)
                        missing_asset_ids = [asset_id for asset_id in duplicate_asset_ids if asset_id not in keeper_asset_ids]
                    if missing_asset_ids:
                        retry_added_count = self.add_assets_to_album(keeper_id, missing_asset_ids, keeper_name, log_level=log_level)
                        time.sleep(1.0)
                        keeper_assets = self.get_all_assets_from_album(keeper_id, log_level=log_level) or []
                        keeper_asset_ids = {str(asset.get("id", "")).strip() for asset in keeper_assets if str(asset.get("id", "")).strip()}
                        reassigned_count = sum(1 for asset_id in duplicate_asset_ids if asset_id in keeper_asset_ids)
                        missing_asset_ids = [asset_id for asset_id in duplicate_asset_ids if asset_id not in keeper_asset_ids]
                    else:
                        retry_added_count = 0
                    LOGGER.info(
                        f"Album Reassignment: '{redundant_name}' -> '{keeper_name}'. "
                        f"Requested={total_redundant_assets}, Confirmed={reassigned_count}, "
                        f"AddedNow={added_count if isinstance(added_count, int) else 0}, "
                        f"RetriedMissing={retry_added_count if isinstance(retry_added_count, int) else 0}, "
                        f"MissingAfterRetry={len(missing_asset_ids)}."
                    )
                    should_remove_redundant = reassigned_count == total_redundant_assets
                else:
                    LOGGER.info(
                        f"Album Reassignment: '{redundant_name}' -> '{keeper_name}'. "
                        f"Requested=0, Confirmed=0, AddedNow=0."
                    )
                    should_remove_redundant = True

                if should_remove_redundant:
                    if self.remove_album(redundant_id, redundant_name, log_level=log_level):
                        LOGGER.info(
                            f"Album Consolidated: '{redundant_name}' -> '{keeper_name}'. "
                            f"Redundant album removed after consolidating {reassigned_count}/{total_redundant_assets} assets."
                        )
                        existing_albums[:] = [
                            album for album in existing_albums
                            if str((album or {}).get("id", "")).strip() != redundant_id
                        ]
                else:
                    LOGGER.warning(
                        f"Album Consolidation Partial: '{redundant_name}' -> '{keeper_name}'. "
                        f"Only {reassigned_count}/{total_redundant_assets} assets were confirmed in the keeper album. "
                        f"The redundant album was kept."
                    )

            self._upsert_existing_album(existing_albums, keeper_id, keeper_name)
            return {"id": keeper_id, "albumName": keeper_name}, plan

    def consolidate_album_namess(self, request_user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.warning("Searching for equivalent album-name families to consolidate. This process may take some time. Please be patient...")
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or []
            if not albums:
                LOGGER.info("No albums found.")
                return 0, 0

            consolidation_groups = scan_album_consolidation_groups(
                albums=albums,
                exact_case_sensitive=True,
                date_getter=lambda album: (album or {}).get("createdAt"),
                progress_desc=f"{MSG_TAGS['INFO']}Scanning albums families to consolidate",
                progress_unit="albums",
            )

            if not consolidation_groups:
                LOGGER.info("No equivalent album families found to consolidate.")
                return 0, 0

            if request_user_confirmation:
                LOGGER.info("Album families to be consolidated:")
                print_album_consolidation_preview(consolidation_groups)
                if not confirm_continue(force_prompt=True):
                    LOGGER.info("Exiting program.")
                    return 0, 0

            families_consolidated = 0
            redundant_albums_detected = 0
            for group in consolidation_groups:
                keeper_album, _ = self.consolidate_reusable_album_group(
                    album_name=group["seed_album_name"],
                    existing_albums=albums,
                    log_level=log_level,
                )
                if keeper_album:
                    families_consolidated += 1
                    redundant_albums_detected += len(group.get("redundant_albums") or [])

            LOGGER.info(
                f"Consolidated {families_consolidated} album family(ies). "
                f"Detected {redundant_albums_detected} redundant album variant(s)."
            )
            return families_consolidated, redundant_albums_detected


    def get_duplicates_assets(self, log_level=None):
        """
        Returns the list of duplicate assets from Immich (via /api/duplicates).
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/duplicates"
            resp = requests.get(url, headers=self.HEADERS_WITH_CREDENTIALS)
            resp.raise_for_status()
            return resp.json()


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
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/assets"
            payload = json.dumps({"force": True, "ids": asset_ids})
            try:
                response = requests.delete(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload)
                response.raise_for_status()
                if response.ok:
                    return len(asset_ids)
                else:
                    LOGGER.error(f"Failed to remove assets due to API error")
                    return 0
            except Exception as e:
                LOGGER.error(f"Failed to remove assets: {str(e)}")
                return 0



    def remove_duplicates_assets(self, log_level=None):
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
                LOGGER.info(f"Removing Duplicates Assets...")
                return self.remove_assets(duplicates_ids, log_level=log_level)
            return 0

    def _ensure_uploaded_asset_cache(self):
        if not hasattr(self, "_uploaded_asset_cache"):
            self._uploaded_asset_cache = {}
        if not hasattr(self, "_uploaded_asset_cache_lock"):
            self._uploaded_asset_cache_lock = threading.Lock()

    def _build_uploaded_asset_cache_key(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            return None
        try:
            checksum_hex, _ = sha1_checksum(file_path)
            return checksum_hex
        except Exception as error:
            LOGGER.debug(f"Unable to compute upload cache key for '{file_path}': {error}")
            return None

    def _remember_uploaded_asset_id(self, file_path, asset_id):
        cache_key = self._build_uploaded_asset_cache_key(file_path)
        if not cache_key or not asset_id:
            return
        self._ensure_uploaded_asset_cache()
        with self._uploaded_asset_cache_lock:
            self._uploaded_asset_cache[cache_key] = str(asset_id)

    def _lookup_uploaded_asset_id(self, file_path):
        cache_key = self._build_uploaded_asset_cache_key(file_path)
        if not cache_key:
            return None
        self._ensure_uploaded_asset_cache()
        with self._uploaded_asset_cache_lock:
            return self._uploaded_asset_cache.get(cache_key)

    def _get_all_assets_unfiltered(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if hasattr(self, "_all_assets_unfiltered_cache") and self._all_assets_unfiltered_cache is not None:
                return self._all_assets_unfiltered_cache
            self.login(log_level=log_level)
            url = f"{self.IMMICH_URL}/api/search/metadata"
            all_assets = []
            next_page = 1
            while True:
                payload = json.dumps({"page": int(next_page), "order": "desc"})
                resp = requests.post(url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("assets", {}).get("items", [])
                all_assets.extend(items)
                next_page = data.get("assets", {}).get("nextPage", None)
                if next_page is None:
                    break
            self._all_assets_unfiltered_cache = all_assets
            return all_assets

    def _resolve_existing_asset_id(self, file_path, log_level=None):
        with set_log_level(LOGGER, log_level):
            cached_asset_id = self._lookup_uploaded_asset_id(file_path)
            if cached_asset_id:
                return cached_asset_id

            target_name = os.path.basename(file_path)
            target_name_casefold = target_name.casefold()
            target_name_normalized = self._normalize_duplicate_lookup_name(target_name)
            try:
                stat = os.stat(file_path)
                target_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                target_size = int(stat.st_size)
            except Exception:
                target_time = None
                target_size = None

            best_asset_id = None
            best_score = None
            for item in self._get_all_assets_unfiltered(log_level=log_level):
                candidate_name = str(item.get("originalFileName", ""))
                candidate_name_casefold = candidate_name.casefold()
                candidate_name_normalized = self._normalize_duplicate_lookup_name(candidate_name)
                exact_name_match = candidate_name_casefold == target_name_casefold
                normalized_name_match = candidate_name_normalized == target_name_normalized
                if not exact_name_match and not normalized_name_match:
                    continue
                candidate_id = str(item.get("id", "")).strip()
                if not candidate_id:
                    continue
                candidate_time = None
                try:
                    candidate_time = datetime.fromisoformat(str(item.get("fileCreatedAt", "")).replace("Z", "+00:00")).astimezone(timezone.utc)
                except Exception:
                    candidate_time = None
                candidate_size = item.get("exifInfo", {}).get("fileSize")
                try:
                    candidate_size = int(candidate_size) if candidate_size is not None else None
                except Exception:
                    candidate_size = None
                time_delta = abs((candidate_time - target_time).total_seconds()) if candidate_time and target_time else float("inf")
                size_delta = abs(candidate_size - target_size) if candidate_size is not None and target_size is not None else float("inf")
                score = (
                    0 if exact_name_match else 1,
                    0 if normalized_name_match else 1,
                    time_delta,
                    size_delta,
                    len(candidate_name),
                )
                if best_score is None or score < best_score:
                    best_score = score
                    best_asset_id = candidate_id
                    if exact_name_match and time_delta <= 1 and (size_delta == 0 or size_delta == float("inf")):
                        break

            if best_asset_id:
                self._remember_uploaded_asset_id(file_path, best_asset_id)
            return best_asset_id

    @staticmethod
    def _normalize_duplicate_lookup_name(filename):
        name = os.path.basename(str(filename or ""))
        stem, ext = os.path.splitext(name)
        stem = re.sub(r"\(\d+\)$", "", stem)
        return f"{stem.casefold()}{ext.casefold()}"


    def push_asset(self, file_path, log_level=None, resolve_duplicate_id=True):
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
                LOGGER.error(f"File not found: {file_path}")
                return None, None

            # Calculate checksum to avoid duplicates
            # hex_checksum, base64_checksum = sha1_checksum(file_path)

            filename, ext = os.path.splitext(file_path)

            # Check extension
            if ext.lower() not in self.ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                if ext.lower() in self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
                    return None, None
                else:
                    LOGGER.warning(f"File '{file_path}' has an unsupported extension. Skipped.")
                    return None, None

            url = f"{self.IMMICH_URL}/api/assets"

            stats = os.stat(file_path)
            try:
                date_time_for_filename = datetime.fromtimestamp(stats.st_mtime).strftime("%Y%m%d_%H%M%S")
                date_time_for_attributes = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            except ValueError:
                # El timestamp stats.st_mtime está fuera de rango, usamos epoch (0)
                LOGGER.warning(f"Timestamp {stats.st_mtime} fuera de rango, usando valor por defecto")
                date_time_for_filename = datetime.fromtimestamp(0).strftime("%Y%m%d_%H%M%S")
                date_time_for_attributes = datetime.fromtimestamp(0).strftime("%Y-%m-%dT%H:%M:%S.000Z")

            data = {
                'deviceAssetId': f'{date_time_for_filename}_{os.path.basename(file_path)}',
                'deviceId': 'PhotoMigrator',
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
                with ExitStack() as stack:
                    file_obj = stack.enter_context(open(file_path, "rb"))
                    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

                    fields = {
                        "deviceAssetId": data["deviceAssetId"],
                        "deviceId": data["deviceId"],
                        "fileCreatedAt": data["fileCreatedAt"],
                        "fileModifiedAt": data["fileModifiedAt"],
                        "fileSize": data["fileSize"],
                        "isFavorite": data["isFavorite"],
                        "isVisible": data["isVisible"],
                        "assetData": (os.path.basename(file_path), file_obj, mime_type),
                    }

                    for sidecar_extension in self.ALLOWED_IMMICH_SIDECAR_EXTENSIONS:
                        sidecar_path_1 = f"{file_path}{sidecar_extension}"
                        sidecar_path_2 = file_path.replace(ext, sidecar_extension)
                        if os.path.isfile(sidecar_path_1):
                            sidecar_obj = stack.enter_context(open(sidecar_path_1, "rb"))
                            sidecar_mime = mimetypes.guess_type(sidecar_path_1)[0] or "application/octet-stream"
                            fields["sidecarData"] = (os.path.basename(sidecar_path_1), sidecar_obj, sidecar_mime)
                            break
                        elif os.path.isfile(sidecar_path_2):
                            sidecar_obj = stack.enter_context(open(sidecar_path_2, "rb"))
                            sidecar_mime = mimetypes.guess_type(sidecar_path_2)[0] or "application/octet-stream"
                            fields["sidecarData"] = (os.path.basename(sidecar_path_2), sidecar_obj, sidecar_mime)
                            break

                    multipart_data = MultipartEncoder(fields=fields)
                    header["Content-Type"] = multipart_data.content_type
                    response = requests.post(url, headers=header, data=multipart_data)
                    response.raise_for_status()
                    new_asset = response.json()
                asset_id = new_asset.get("id")
                status = str(new_asset.get("status") or "").lower()
                is_duplicated = (status == 'duplicate')
                if is_duplicated and not asset_id:
                    if not resolve_duplicate_id:
                        LOGGER.debug(
                            f"Immich duplicate response without asset id for '{os.path.basename(file_path)}'. "
                            f"Deferring existing asset resolution."
                        )
                        return None, True
                    resolved_asset_id = self._resolve_existing_asset_id(file_path, log_level=log_level)
                    if resolved_asset_id:
                        LOGGER.debug(
                            f"Immich duplicate response without asset id for '{os.path.basename(file_path)}'. "
                            f"Resolved existing asset_id={resolved_asset_id}."
                        )
                        return resolved_asset_id, True
                    LOGGER.error(
                        f"Immich returned duplicate status without existing asset id for '{os.path.basename(file_path)}'. "
                        f"Response payload: {new_asset}"
                    )
                    return None, None
                if asset_id:
                    self._remember_uploaded_asset_id(file_path, asset_id)
                    if is_duplicated:
                        LOGGER.debug(f"Duplicated Asset: '{os.path.basename(file_path)}'. Existing asset_id={asset_id}")
                    else:
                        LOGGER.debug(f"Pushed '{os.path.basename(file_path)}' with asset_id={asset_id}")
                return asset_id, is_duplicated
            except Exception as e:
                LOGGER.error(f"Failed to push '{file_path}': {e}")
                return None, None

    def _find_live_photo_video_companion(self, photo_file_path):
        """
        Find a companion video for a photo using same basename in the same folder.
        """
        photo_ext = os.path.splitext(photo_file_path)[1].lower()
        if photo_ext not in ['.heic', '.heif', '.jpg', '.jpeg']:
            return None
        folder = os.path.dirname(photo_file_path) or "."
        photo_base = os.path.splitext(os.path.basename(photo_file_path))[0]
        try:
            entries = os.listdir(folder)
        except Exception:
            return None

        lower_to_real = {name.lower(): name for name in entries}
        for video_ext in (self.ALLOWED_IMMICH_VIDEO_EXTENSIONS or []):
            expected_name_lower = f"{photo_base}{video_ext}".lower()
            real_name = lower_to_real.get(expected_name_lower)
            if real_name:
                candidate = os.path.join(folder, real_name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _link_live_photo_assets(self, photo_asset_id, video_asset_id, log_level=None):
        """
        Link an uploaded photo asset with its uploaded companion video using livePhotoVideoId.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not photo_asset_id or not video_asset_id:
                return False
            try:
                url = f"{self.IMMICH_URL}/api/assets/{photo_asset_id}"
                payload = json.dumps({"livePhotoVideoId": str(video_asset_id)})
                headers = dict(self.HEADERS_WITH_CREDENTIALS)
                headers["Content-Type"] = "application/json"
                # Immich may expose eventual consistency just after upload; retry transient 404s.
                retry_delays = [0.2, 0.5, 1.0, 2.0]
                attempts = len(retry_delays) + 1
                for attempt in range(attempts):
                    try:
                        resp = requests.patch(url, headers=headers, data=payload, verify=False)
                        resp.raise_for_status()
                        return True
                    except requests.HTTPError as e:
                        status_code = e.response.status_code if e.response is not None else None
                        if status_code == 404 and attempt < len(retry_delays):
                            time.sleep(retry_delays[attempt])
                            continue
                        raise
            except Exception as e:
                LOGGER.warning(f"Unable to link live photo assets (photo={photo_asset_id}, video={video_asset_id}): {e}")
                return False

    def push_live_photo(self, photo_file_path, live_photo_video_path=None, log_level=None, resolve_duplicate_id=True):
        """
        Uploads Live Photo components (video + photo) and links them in Immich.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            companion_video = live_photo_video_path or self._find_live_photo_video_companion(photo_file_path)
            if not companion_video or not os.path.isfile(companion_video):
                return self.push_asset(photo_file_path, log_level=log_level, resolve_duplicate_id=resolve_duplicate_id)

            video_asset_id, video_is_dup = self.push_asset(companion_video, log_level=log_level, resolve_duplicate_id=resolve_duplicate_id)
            photo_asset_id, photo_is_dup = self.push_asset(photo_file_path, log_level=log_level, resolve_duplicate_id=resolve_duplicate_id)

            # Linking duplicated assets is unreliable and can produce 404s depending on Immich duplicate policy.
            if photo_asset_id and video_asset_id and not photo_is_dup and not video_is_dup:
                self._link_live_photo_assets(photo_asset_id=photo_asset_id, video_asset_id=video_asset_id, log_level=log_level)

            return photo_asset_id, photo_is_dup

    def _normalize_burst_stem(self, filename):
        """
        Normalize filename stem to reduce burst variants into a common key.
        """
        stem = os.path.splitext(os.path.basename(filename))[0].lower()
        stem = re.sub(r'\(\d+\)$', '', stem)
        stem = re.sub(r'([._-])(edited|edit|hdr|enhanced)$', '', stem)
        stem = re.sub(r'([._-])burst\d+$', '', stem)
        stem = re.sub(r'([._-])(raw|dng|jpg|jpeg|heic|heif)$', '', stem)
        stem = re.sub(r'[\s._-]+$', '', stem)
        return stem

    def _build_burst_record(self, asset_id, file_path, capture_epoch=None, file_size=None):
        """
        Build a normalized record used by burst auto-stacking heuristics.
        """
        ext = os.path.splitext(file_path)[1].lower()
        folder = os.path.normcase(os.path.normpath(os.path.dirname(file_path)))
        normalized_stem = self._normalize_burst_stem(file_path)
        if capture_epoch is None:
            try:
                capture_epoch = os.path.getmtime(file_path)
            except Exception:
                capture_epoch = None
        if file_size is None:
            try:
                file_size = os.path.getsize(file_path)
            except Exception:
                file_size = 0
        return {
            "asset_id": asset_id,
            "file_path": file_path,
            "folder": folder,
            "ext": ext,
            "normalized_stem": normalized_stem,
            "capture_epoch": capture_epoch,
            "file_size": file_size or 0,
        }

    def _burst_primary_sort_key(self, record):
        """
        Lower tuple means higher priority for stack primary.
        """
        ext = record.get("ext", "").lower()
        if ext in ['.jpg', '.jpeg', '.heic', '.heif']:
            ext_rank = 0
        elif ext in ['.dng', '.raw', '.arw', '.cr2', '.cr3', '.nef', '.orf', '.raf', '.rw2']:
            ext_rank = 1
        else:
            ext_rank = 2
        size = record.get("file_size", 0) or 0
        capture = record.get("capture_epoch")
        capture_rank = capture if isinstance(capture, (int, float)) else float("inf")
        return (ext_rank, -size, capture_rank)

    def _create_stack(self, asset_ids, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            if not asset_ids or len(asset_ids) < 2:
                return None
            try:
                url = f"{self.IMMICH_URL}/api/stacks"
                payload = json.dumps({"assetIds": asset_ids})
                headers = dict(self.HEADERS_WITH_CREDENTIALS)
                headers["Content-Type"] = "application/json"
                resp = requests.post(url, headers=headers, data=payload, verify=False)
                resp.raise_for_status()
                data = resp.json()
                return data.get("id")
            except Exception as e:
                LOGGER.warning(f"Unable to create burst stack ({len(asset_ids)} assets): {e}")
                return None

    def auto_stack_bursts(self, uploaded_records, context_label="", log_level=None):
        """
        Auto-stack burst-like photo groups in Immich using conservative heuristics.
        """
        with set_log_level(LOGGER, log_level):
            if not uploaded_records:
                return 0

            # Keep only photo assets and valid IDs
            photo_exts = {e.lower() for e in (self.ALLOWED_IMMICH_PHOTO_EXTENSIONS or [])}
            records = []
            for rec in uploaded_records:
                if not rec:
                    continue
                asset_id = rec.get("asset_id")
                ext = str(rec.get("ext", "")).lower()
                if not asset_id or ext not in photo_exts:
                    continue
                records.append(rec)

            if not records:
                return 0

            groups = {}
            for rec in records:
                key = (rec.get("folder"), rec.get("normalized_stem"))
                groups.setdefault(key, []).append(rec)

            stacks_created = 0
            for _, items in groups.items():
                if len(items) < 2:
                    continue
                items_sorted = sorted(items, key=lambda r: (r.get("capture_epoch") if isinstance(r.get("capture_epoch"), (int, float)) else float("inf")))

                # Split by capture-time windows (<=2s)
                current_cluster = []
                clusters = []
                for rec in items_sorted:
                    if not current_cluster:
                        current_cluster.append(rec)
                        continue
                    prev = current_cluster[-1]
                    prev_t = prev.get("capture_epoch")
                    cur_t = rec.get("capture_epoch")
                    if isinstance(prev_t, (int, float)) and isinstance(cur_t, (int, float)) and abs(cur_t - prev_t) <= 2:
                        current_cluster.append(rec)
                    else:
                        if len(current_cluster) >= 2:
                            clusters.append(current_cluster)
                        current_cluster = [rec]
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)

                for cluster in clusters:
                    # Size ratio guard
                    sizes = [max(1, int(c.get("file_size") or 1)) for c in cluster]
                    min_size = min(sizes)
                    max_size = max(sizes)
                    if max_size / min_size > 1.8:
                        continue

                    cluster_sorted = sorted(cluster, key=self._burst_primary_sort_key)
                    ordered_asset_ids = []
                    seen_ids = set()
                    for c in cluster_sorted:
                        aid = c.get("asset_id")
                        if aid and aid not in seen_ids:
                            ordered_asset_ids.append(aid)
                            seen_ids.add(aid)
                    if len(ordered_asset_ids) < 2:
                        continue
                    stack_id = self._create_stack(ordered_asset_ids, log_level=log_level)
                    if stack_id:
                        stacks_created += 1

            if stacks_created > 0:
                prefix = f"{context_label}: " if context_label else ""
                LOGGER.info(f"{prefix}Auto-stacked {stacks_created} burst group(s) in Immich.")
            return stacks_created


    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_Immich", album_passphrase=None, album_id=None, album_scope=None, log_level=None):
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
            :param album_passphrase:
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

                LOGGER.debug(f"")
                LOGGER.debug(f"Asset '{asset_filename}' downloaded and saved at {file_path}")
                return 1
            except Exception as e:
                LOGGER.error(f"Failed to download asset {asset_id}: {e}")
                return 0


    ###########################################################################
    #                  HIGH-LEVEL MAIN FUNCTIONS (UPLOAD/DOWNLOAD)            #
    ###########################################################################
    def push_albums(self, input_folder, subfolders_exclusion=FOLDERNAME_NO_ALBUMS, subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        """
        Traverses the subfolders of 'input_folder', creating an album for each valid subfolder (album name equals the subfolder name).
        Within each subfolder, it uploads all files with allowed extensions (based on self.ALLOWED_IMMICH_EXTENSIONS) and associates them with the album.
        
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
            try:
                self.login(log_level=log_level)
                if not os.path.isdir(input_folder):
                    LOGGER.error(f"The folder '{input_folder}' does not exist.")
                    # self.logout(log_level=log_level)
                    return 0, 0, 0, 0, 0

                subfolders_exclusion = convert_to_list(subfolders_exclusion)
                subfolders_inclusion = convert_to_list(subfolders_inclusion)
                effective_folder_exclusions = merge_exclusion_patterns(
                    ARGS.get("exclude-folders", []),
                    default_patterns=['@eaDir', '@Recycle', '.*'] + subfolders_exclusion,
                )
                effective_file_exclusions = merge_exclusion_patterns(
                    ARGS.get("exclude-files", []),
                    default_patterns=["SYNOFILE_THUMB*", "SYNOPHOTO_THUMB*", "SYNOVIDEO_THUMB*", "SYNOPHOTO_FILM*", "Thumbs.db", "ehthumbs.db", ".DS_Store", "._*"],
                )

                total_albums_uploaded = 0
                total_albums_skipped = 0
                total_assets_uploaded = 0
                total_duplicates_assets_removed = 0
                total_duplicates_assets_skipped = 0
                prefer_canonical_album_names = prefer_canonical_album_names_enabled(ARGS)
                consolidate_similar_albums = consolidate_similar_albums_enabled(ARGS)
                LOGGER.info("Retrieving existing albums from Immich Photos and scanning local album folders. This may take some time, please be patient...")
                existing_albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or []

                # # If 'Albums' is not in subfolders_inclusion, add it (like original code).
                # first_level_folders = [name.lower() for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
                # albums_folder_included = any(rel.lower() == 'albums' for rel in subfolders_inclusion)
                # if not albums_folder_included and 'albums' in first_level_folders:
                #     subfolders_inclusion.append('Albums')

                valid_folders = []

                for root, folders, _ in os.walk(input_folder):
                    # Filter out excluded folders
                    folders[:] = [d for d in folders if not matches_any_pattern(d, effective_folder_exclusions)]
                    if subfolders_inclusion:
                        relative_path = os.path.relpath(root, input_folder)
                        if relative_path == ".":
                            folders[:] = [d for d in folders if d in subfolders_inclusion]
                        else:
                            first_dir = relative_path.split(os.sep)[0]
                            if first_dir not in subfolders_inclusion:
                                folders[:] = []

                    for folder in folders:
                        dir_path = os.path.join(root, folder)
                        if not os.path.isdir(dir_path):
                            continue
                        # Check if there's at least one supported file
                        has_supported_files = any(
                            os.path.splitext(f)[-1].lower() in self.ALLOWED_IMMICH_EXTENSIONS
                            and not matches_any_pattern(f, effective_file_exclusions)
                            for f in os.listdir(dir_path)
                            if os.path.isfile(os.path.join(dir_path, f))
                        )
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
                        album_uploaded_records = []
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

                        consumed_live_companions = set()
                        album_file_paths = [os.path.join(subpath, file) for file in os.listdir(subpath)]
                        for file_path in tqdm(
                            album_file_paths,
                            desc=f"{MSG_TAGS['INFO']}   Uploading '{album_name}' Assets",
                            unit=" assets",
                        ):
                            if not os.path.isfile(file_path):
                                continue
                            norm_file_path = os.path.normcase(os.path.normpath(file_path))
                            if norm_file_path in consumed_live_companions:
                                continue
                            if matches_any_pattern(os.path.basename(file_path), effective_file_exclusions):
                                continue
                            ext = os.path.splitext(file_path)[-1].lower()
                            if ext not in self.ALLOWED_IMMICH_EXTENSIONS:
                                continue

                            live_photo_video_path = None
                            if ext in self.ALLOWED_IMMICH_PHOTO_EXTENSIONS:
                                live_photo_video_path = self._find_live_photo_video_companion(file_path)
                                if live_photo_video_path:
                                    consumed_live_companions.add(os.path.normcase(os.path.normpath(live_photo_video_path)))
                                    asset_id, is_dup = self.push_live_photo(file_path, live_photo_video_path=live_photo_video_path, log_level=log_level)
                                else:
                                    asset_id, is_dup = self.push_asset(file_path, log_level=log_level)
                            else:
                                asset_id, is_dup = self.push_asset(file_path, log_level=log_level)
                            if is_dup:
                                total_duplicates_assets_skipped += 1
                                LOGGER.debug(f"Dupplicated Asset: {file_path}. Asset ID: {asset_id} upload skipped")
                            else:
                                total_assets_uploaded += 1

                            if asset_id:
                                album_uploaded_records.append(self._build_burst_record(asset_id=asset_id, file_path=file_path))
                                # Associate only if ext is photo/video
                                if ext in self.ALLOWED_IMMICH_MEDIA_EXTENSIONS:
                                    album_assets_ids.append(asset_id)

                        self.auto_stack_bursts(album_uploaded_records, context_label=f"Album '{album_name}'", log_level=log_level)

                        if album_assets_ids:
                            matched_album = None
                            match_kind = None
                            preferred_name = album_name
                            if consolidate_similar_albums:
                                matched_album, reuse_plan = self.consolidate_reusable_album_group(
                                    album_name=album_name,
                                    existing_albums=existing_albums,
                                    log_level=log_level,
                                )
                                match_kind = reuse_plan.get("match_kind")
                                matched_name = (matched_album or {}).get("albumName", album_name) if matched_album else album_name
                                if matched_album or reuse_plan.get("similar_albums"):
                                    preferred_name = str(reuse_plan.get("preferred_album_name") or album_name)
                                if matched_album and matched_name != album_name:
                                    LOGGER.info(
                                        f"Reusing consolidated Immich album '{matched_name}' "
                                        f"for source album '{album_name}'. Preferred keeper name: '{preferred_name}'."
                                    )
                            else:
                                matched_album, match_kind, _ = find_reusable_album_candidate(
                                    album_name=album_name,
                                    albums=existing_albums,
                                    allow_similar=False,
                                    exact_case_sensitive=True,
                                )
                            if not matched_album and prefer_canonical_album_names:
                                preferred_name = str(canonicalize_album_name_for_reuse(album_name) or album_name).strip() or album_name
                                if preferred_name.casefold() != album_name.casefold():
                                    matched_album, _, _ = find_reusable_album_candidate(
                                        album_name=preferred_name,
                                        albums=existing_albums,
                                        allow_similar=False,
                                        exact_case_sensitive=True,
                                    )
                                    if matched_album:
                                        LOGGER.info(
                                            f"Reusing canonical Immich album '{preferred_name}' "
                                            f"for source album '{album_name}'."
                                        )
                            if matched_album:
                                album_id = matched_album.get("id")
                            else:
                                album_name_to_create = preferred_name if prefer_canonical_album_names else album_name
                                if album_name_to_create != album_name:
                                    LOGGER.info(
                                        f"Normalizing source album name '{album_name}' to preferred keeper name "
                                        f"'{album_name_to_create}' before creating the destination album."
                                    )
                                album_id = self.create_album(album_name_to_create, log_level=log_level)
                                if album_id:
                                    existing_albums.append({"id": album_id, "albumName": album_name_to_create})
                            if not album_id:
                                LOGGER.warning(f"Could not create album for subfolder '{subpath}'.")
                                total_albums_skipped += 1
                            else:
                                self.add_assets_to_album(album_id, album_assets_ids, album_name=album_name, log_level=log_level)
                                LOGGER.debug(f"Album '{album_name}' ready with ID: {album_id}. Total Assets added to Album: {len(album_assets_ids)}.")
                                if not matched_album:
                                    total_albums_uploaded += 1
                        else:
                            total_albums_skipped += 1

                if remove_duplicates:
                    LOGGER.info(f"Removing Duplicates Assets...")
                    total_duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

                LOGGER.info(f"Uploaded {total_albums_uploaded} album(s) from '{input_folder}'.")
                LOGGER.info(f"Uploaded {total_assets_uploaded} asset(s) from '{input_folder}' to Albums.")
                LOGGER.info(f"Skipped {total_albums_skipped} album(s) from '{input_folder}'.")
                LOGGER.info(f"Removed {total_duplicates_assets_removed} duplicates asset(s) from Immich Database.")
                LOGGER.info(f"Skipped {total_duplicates_assets_skipped} duplicated asset(s) from '{input_folder}' to Albums.")

            except Exception as e:
                LOGGER.error(f"Exception while uploading Albums assets into Immich Photos. {e}")
                return 0,0,0,0,0

            # self.logout(log_level=log_level)
            return (total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_duplicates_assets_removed, total_duplicates_assets_skipped)


    def push_no_albums(self, input_folder, subfolders_exclusion=f'{FOLDERNAME_ALBUMS}', subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
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
                LOGGER.error(f"The folder '{input_folder}' does not exist.")
                # self.logout(log_level=log_level)
                return 0, 0, 0

            subfolders_exclusion = convert_to_list(subfolders_exclusion)
            subfolders_inclusion = convert_to_list(subfolders_inclusion)
            effective_folder_exclusions = merge_exclusion_patterns(
                ARGS.get("exclude-folders", []),
                default_patterns=['@eaDir', '@Recycle', '.*'] + subfolders_exclusion,
            )
            effective_file_exclusions = merge_exclusion_patterns(
                ARGS.get("exclude-files", []),
                default_patterns=["SYNOFILE_THUMB*", "SYNOPHOTO_THUMB*", "SYNOVIDEO_THUMB*", "SYNOPHOTO_FILM*", "Thumbs.db", "ehthumbs.db", ".DS_Store", "._*"],
            )
            LOGGER.info("Scanning local files to upload into Immich Photos. This may take some time, please be patient...")

            def collect_files(base_folder, only_subfolders):
                flist = []
                if only_subfolders:
                    for sub in only_subfolders:
                        sub_path = os.path.join(base_folder, sub)
                        if not os.path.isdir(sub_path):
                            LOGGER.warning(f"Subfolder '{sub}' does not exist in '{base_folder}'. Skipping.")
                            continue
                        for root, dirs, files in os.walk(sub_path):
                            dirs[:] = [d for d in dirs if not matches_any_pattern(d, effective_folder_exclusions)]
                            for file_ in files:
                                if matches_any_pattern(file_, effective_file_exclusions):
                                    continue
                                flist.append(os.path.join(root, file_))
                else:
                    for root, dirs, files in os.walk(base_folder):
                        dirs[:] = [d for d in dirs if not matches_any_pattern(d, effective_folder_exclusions)]
                        for file_ in files:
                            if matches_any_pattern(file_, effective_file_exclusions):
                                continue
                            flist.append(os.path.join(root, file_))
                return flist

            file_paths = collect_files(input_folder, subfolders_inclusion)
            total_files = len(file_paths)
            total_assets_uploaded = 0
            total_duplicated_assets_skipped = 0
            consumed_live_companions = set()
            uploaded_records = []

            with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}Uploading Assets", unit=" asset") as pbar:
                for f_idx, file_path in enumerate(file_paths, start=1):
                    pbar.update(1)
                    norm_file_path = os.path.normcase(os.path.normpath(file_path))
                    if norm_file_path in consumed_live_companions:
                        continue
                    _, ext = os.path.splitext(file_path)
                    ext = ext.lower()
                    if ext not in self.ALLOWED_IMMICH_EXTENSIONS:
                        LOGGER.debug(f"Unsopported Extension: '{ext}'. Skipped")
                        continue

                    if ext in self.ALLOWED_IMMICH_PHOTO_EXTENSIONS:
                        live_photo_video_path = self._find_live_photo_video_companion(file_path)
                        if live_photo_video_path:
                            consumed_live_companions.add(os.path.normcase(os.path.normpath(live_photo_video_path)))
                            asset_id, is_dup = self.push_live_photo(file_path, live_photo_video_path=live_photo_video_path, log_level=log_level)
                        else:
                            asset_id, is_dup = self.push_asset(file_path, log_level=log_level)
                    else:
                        asset_id, is_dup = self.push_asset(file_path, log_level=log_level)
                    if is_dup:
                        total_duplicated_assets_skipped += 1
                        LOGGER.debug(f"Dupplicated Asset: {file_path}. Asset ID: {asset_id} skipped")
                    elif asset_id:
                        LOGGER.debug(f"Asset ID: {asset_id} uploaded to Immich Photos")
                        total_assets_uploaded += 1
                        uploaded_records.append(self._build_burst_record(asset_id=asset_id, file_path=file_path))

            self.auto_stack_bursts(uploaded_records, context_label="No-Album Upload", log_level=log_level)

            duplicates_assets_removed = 0
            if remove_duplicates:
                LOGGER.info(f"Removing Duplicates Assets...")
                duplicates_assets_removed = self.remove_duplicates_assets(log_level=log_level)

            LOGGER.info(f"Uploaded {total_assets_uploaded} files (without album) from '{input_folder}'.")
            LOGGER.info(f"Skipped {total_duplicated_assets_skipped} duplicated asset(s) from '{input_folder}'.")
            LOGGER.info(f"Removed {duplicates_assets_removed} duplicates asset(s) from Immich Database.")

            # self.logout(log_level=log_level)
            return total_assets_uploaded, total_duplicated_assets_skipped, duplicates_assets_removed


    def push_all(self, input_folder, album_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        """
        Uploads ALL photos/videos from input_folder into Immich Photos.
        Returns details about how many albums and assets were uploaded.

        Args:
            input_folder (str): Input folder
            album_folders (str): Albums folder
            remove_duplicates (bool): True to remove duplicates assets after upload all assets
            log_level (logging.LEVEL): log_level for logs and console

        Returns: (albums_uploaded, albums_skipped, assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed, total_dupplicated_assets_skipped)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)

            total_duplicates_assets_removed = 0
            input_folder = os.path.realpath(input_folder)
            album_folders = convert_to_list(album_folders)

            # Ensure 'Albums' is included
            albums_folder_included = any((subf.lower() == 'albums') for subf in album_folders)
            if not albums_folder_included:
                album_folders.append(f'{FOLDERNAME_ALBUMS}')

            LOGGER.info(f"")
            LOGGER.info(f"Uploading Assets and creating Albums into immich Photos from '{album_folders}' subfolders...")

            total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, total_duplicates_assets_removed_1, total_dupplicated_assets_skipped_1 = self.push_albums(input_folder=input_folder, subfolders_inclusion=album_folders, remove_duplicates=False, log_level=logging.WARNING)

            LOGGER.info(f"")
            LOGGER.info(f"Uploading Assets without Albums creation into immich Photos from '{input_folder}' (excluding albums subfolders '{album_folders}')...")

            total_assets_uploaded_without_albums, total_dupplicated_assets_skipped_2, total_duplicates_assets_removed_2 = self.push_no_albums(input_folder=input_folder, subfolders_exclusion=album_folders, remove_duplicates=False, log_level=logging.WARNING)

            total_duplicates_assets_removed = total_duplicates_assets_removed_1 + total_duplicates_assets_removed_2
            total_dupplicated_assets_skipped = total_dupplicated_assets_skipped_1 + total_dupplicated_assets_skipped_2
            total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

            if remove_duplicates:
                LOGGER.info(f"Removing Duplicates Assets...")
                total_duplicates_assets_removed += self.remove_duplicates_assets(log_level=logging.WARNING)

            # self.logout(log_level=log_level)

            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed, total_dupplicated_assets_skipped


    def pull_albums(self, album_names='ALL', output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads photos/videos from albums by name pattern or ID. 'ALL' downloads all.

        Args:
            album_names (str or list): The name(s) of the album(s) to download. Use 'ALL' to download all albums.
            output_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            tuple: (albums_downloaded, assets_downloaded)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            output_folder = os.path.join(output_folder, f"{FOLDERNAME_ALBUMS}")
            os.makedirs(output_folder, exist_ok=True)

            # Check if there is some filter applied
            filters_provided = has_any_filter()

            all_albums = self.get_albums_including_shared_with_user(filter_assets=filters_provided, log_level=log_level)
            if not all_albums:
                LOGGER.warning(f"No albums available or could not retrieve the list.")
                # self.logout(log_level=log_level)
                return 0, 0

            if isinstance(album_names, str):
                album_names = [album_names]

            if 'ALL' in [x.strip().upper() for x in album_names]:
                albums_to_download = all_albums
                LOGGER.info(f"ALL albums ({len(all_albums)}) will be downloaded...")
            else:
                found_albums = []
                for album in all_albums:
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    for pattern in album_names:
                        if album_id == str(pattern):
                            found_albums.append(album)
                            break
                        if fnmatch.fnmatch(album_name.lower(), pattern.lower()):
                            found_albums.append(album)
                            break

                if found_albums:
                    albums_to_download = found_albums
                    LOGGER.info(f"{len(found_albums)} album(s) matched pattern(s) '{album_names}'.")
                else:
                    LOGGER.warning(f"No albums found matching pattern(s) '{album_names}'.")
                    # self.logout(log_level=log_level)
                    return 0, 0

            total_assets_downloaded = 0
            total_albums_downloaded = 0
            total_albums = len(albums_to_download)

            for album in tqdm(albums_to_download, desc=f"{MSG_TAGS['INFO']}Downloading Albums", unit=" albums"):
                album_id = album.get("id")
                album_name = album.get("albumName", f"album_{album_id}")
                album_folder = os.path.join(output_folder, album_name)
                os.makedirs(album_folder, exist_ok=True)

                album_assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                for asset in tqdm(
                    album_assets,
                    desc=f"{MSG_TAGS['INFO']}   Downloading '{album_name}' Assets",
                    unit=" assets",
                ):
                    asset_id = asset.get("id")
                    asset_filename = os.path.basename(asset.get("originalFileName", "unknown"))
                    if asset_id:
                        asset_time = asset.get('fileCreatedAt')
                        total_assets_downloaded += self.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=album_folder, log_level=log_level)

                total_albums_downloaded += 1
                LOGGER.info(f"Downloaded Album [{total_albums_downloaded}/{total_albums}] - '{album_name}'. {len(album_assets)} asset(s) have been downloaded.")

            LOGGER.info(f"Download of Albums completed.")
            LOGGER.info(f"Total Albums downloaded: {total_albums_downloaded}")
            LOGGER.info(f"Total Assets downloaded: {total_assets_downloaded}")

            # self.logout(log_level=log_level)
            return total_albums_downloaded, total_assets_downloaded


    def pull_no_albums(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads assets not associated to any album from Immich Photos into output_folder/<NO_ALBUMS_FOLDER>/.
        Assets are stored directly using year/month subfolders.

        Args:
            output_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns assets_downloaded or 0 if no assets are downloaded
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            total_assets_downloaded = 0

            all_assets_without_albums = self.get_all_assets_without_albums(log_level=log_level)
            no_albums_folder = os.path.join(output_folder, FOLDERNAME_NO_ALBUMS)
            os.makedirs(no_albums_folder, exist_ok=True)

            LOGGER.info(f"Found {len(all_assets_without_albums)} asset(s) without any album associated.")
            for asset in tqdm(all_assets_without_albums, desc=f"{MSG_TAGS['INFO']}Downloading assets without associated albums", unit=" assets"):
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
                total_assets_downloaded += self.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=target_folder, log_level=log_level)

            LOGGER.info(f"Download of assets without associated albums completed.")
            LOGGER.info(f"Total Assets downloaded: {total_assets_downloaded}")

            # self.logout(log_level=log_level)
            return total_assets_downloaded


    def pull_all(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Downloads ALL photos and videos from Immich Photos into output_folder creating a Folder Structure like this:
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
            
        Returns total_albums_downloaded, total_assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            total_albums_downloaded, total_assets_in_albums = self.pull_albums(album_names='ALL', output_folder=output_folder, log_level=log_level)
            total_assets_no_albums = self.pull_no_albums(output_folder=output_folder, log_level=log_level)
            total_assets = total_assets_in_albums + total_assets_no_albums

            LOGGER.info(f"Download of ALL assets completed.")
            LOGGER.info(f"Total Albums downloaded                   : {total_albums_downloaded}")
            LOGGER.info(f"Total Assets downloaded                   : {total_assets}")
            LOGGER.info(f"Total Assets downloaded within albums     : {total_assets_in_albums}")
            LOGGER.info(f"Total Assets downloaded without albums    : {total_assets_no_albums}")

            # self.logout(log_level=log_level)
            return (total_albums_downloaded, total_assets, total_assets_in_albums, total_assets_no_albums)


    ###########################################################################
    #                   REMOVE EMPTY / DUPLICATES ALBUMS                      #
    ###########################################################################
    # TODO: Complete this method
    def remove_empty_folders(self, log_level=None):
        """
        Recursively removes all empty folders and subfolders in Immich Photos,
        considering folders empty if they only contain '@eaDir'.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty folders removed.
        """
        return 0


    def rename_albums(self, pattern, pattern_to_replace, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Renames all albums in Immich Photos whose name matches the provided pattern.

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
            matched_album_names = []
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to rename", unit="albums"):
                album_date = album.get("createdAt")
                if is_date_outside_range(album_date):
                    continue

                album_id = album.get("id")
                album_name = album.get("albumName", "")
                album_description = album.get("description", "")
                album_thumbnail = album.get("albumThumbnailAssetId", "")
                if match_pattern(album_name, pattern):
                    matched_album_names.append(album_name)
                    new_name = replace_pattern(album_name, pattern=pattern, pattern_to_replace=pattern_to_replace)
                    if not new_name or new_name == album_name:
                        continue
                    albums_to_rename[album_id] = {
                        "album_name": album_name,
                        "new_name": new_name,
                        "album_thumbnail": album_thumbnail,
                        "album_description": album_description
                    }

            if not albums_to_rename:
                if matched_album_names:
                    LOGGER.info(
                        f"Pattern matched {len(matched_album_names)} album(s), but the replacement pattern did not change any album name. "
                        f"Nothing to rename."
                    )
                else:
                    LOGGER.info(f"No albums matched the pattern.")
                # self.logout(log_level=log_level)
                return 0

            # Display the albums that will be renamed
            LOGGER.info(f"Albums to be renamed:")
            for album_info in albums_to_rename.values():
                print(f"  '{album_info['album_name']}' --> '{album_info['new_name']}'")

            # Ask for confirmation only if requested
            if request_user_confirmation and not confirm_continue(force_prompt=True):
                LOGGER.info(f"Exiting program.")
                return 0

            total_renamed_albums = 0
            for album_id, album_info in albums_to_rename.items():
                url = f"{self.IMMICH_URL}/api/albums/{album_id}"
                payload = json.dumps({
                    "albumName": album_info["new_name"],
                    "albumThumbnailAssetId": album_info["album_thumbnail"],
                    "description": album_info["album_description"],
                    "isActivityEnabled": True,
                    "order": "asc"
                })
                response = requests.request("PATCH", url, headers=self.HEADERS_WITH_CREDENTIALS, data=payload)
                response.raise_for_status()
                if response.ok:
                    LOGGER.info(f"Album '{album_info['album_name']}' (ID={album_id}) renamed to '{album_info['new_name']}'.")
                    total_renamed_albums += 1

            LOGGER.info(f"Renamed {total_renamed_albums} albums whose names matched the provided pattern.")
            # self.logout(log_level=log_level)
            return total_renamed_albums

    def remove_albums_by_name(self, pattern, remove_album_assets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Immich Photos whose name matches the provided pattern.

        If remove_album_assets is True, it also deletes all assets inside the matching albums.
        If request_user_confirmation is True, displays the albums to be deleted and asks for user confirmation before proceeding.

        Args:
            pattern (str): The regex pattern to match album names.
            remove_album_assets (bool): Whether to delete all assets contained in the albums.
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
                album_date = album.get("createdAt")
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
            if request_user_confirmation and not confirm_continue(force_prompt=True):
                LOGGER.info(f"Exiting program.")
                # self.logout(log_level=log_level)
                return 0, 0

            total_removed_albums = 0
            total_removed_assets = 0
            for album_info in albums_to_remove:
                album_id = album_info["album_id"]
                album_name = album_info["album_name"]

                if remove_album_assets:
                    album_assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                    album_assets_ids = [asset.get("id") for asset in album_assets if asset.get("id")]
                    if album_assets_ids:
                        assets_removed = self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                        total_removed_assets += assets_removed

                if self.remove_album(album_id, album_name):
                    LOGGER.info(f"Album '{album_name}' (ID={album_id}) removed.")
                    total_removed_albums += 1

            LOGGER.info(f"Removed {total_removed_albums} albums whose names matched the provided pattern.")
            LOGGER.info(f"Removed {total_removed_assets} assets from those removed albums.")
            # self.logout(log_level=log_level)
            return total_removed_albums, total_removed_assets

    def remove_all_albums(self, remove_album_assets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Immich Photos, and optionally all their associated assets.

        If request_user_confirmation is True, displays the albums to be deleted and asks for user confirmation before proceeding.

        Args:
            remove_album_assets (bool): Whether to remove all assets inside the albums.
            request_user_confirmation (bool): Whether to ask for confirmation before deleting.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            tuple: (number of albums removed, number of assets removed)
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.info("Retrieving albums from Immich Photos to remove. This may take some time, please be patient...")
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                LOGGER.info(f"No albums found.")
                return 0, 0

            albums_to_remove = []
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to remove", unit="albums"):
                album_date = album.get("createdAt")
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
            LOGGER.warning(f"{len(albums_to_remove)} albums marked for deletion:")
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

                if remove_album_assets:
                    album_assets = self.get_all_assets_from_album(album_id, log_level=log_level)
                    album_assets_ids = [asset.get("id") for asset in album_assets if asset.get("id")]
                    if album_assets_ids:
                        self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                        total_removed_assets += len(album_assets_ids)

                if self.remove_album(album_id, album_name, log_level=logging.WARNING):
                    LOGGER.info(f"Album '{album_name}' (ID={album_id}) removed.")
                    total_removed_albums += 1

            # Remove any remaining empty albums
            LOGGER.info(f"Getting empty albums to remove...")
            empty_albums_removed = self.remove_empty_albums(log_level=logging.WARNING)
            total_removed_albums += empty_albums_removed

            LOGGER.info(f"Removed {total_removed_albums} albums.")
            if remove_album_assets:
                LOGGER.info(f"Removed {total_removed_assets} assets associated with those albums.")

            return total_removed_albums, total_removed_assets


            # self.logout(log_level=log_level)
            return total_removed_albums, total_removed_assets


    def remove_empty_albums(self, log_level=logging.WARNING):
        """
        Removes all empty albums in Immich Photos.

        Args:
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of empty albums removed.
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                LOGGER.info(f"No albums found.")
                # self.logout(log_level=log_level)
                return 0

            total_removed_empty_albums = 0
            LOGGER.info(f"Looking for empty albums in Immich Photos...")
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for Empty Albums", unit=" albums"):
                # Check if Album Creation date is outside filters date range (if provided), in that case, skip this album
                album_date = album.get("createdAt")
                if is_date_outside_range(album_date):
                    continue

                album_id = album.get("id")
                album_name = album.get("albumName", "")
                asset_count = album.get("assetCount")
                if asset_count == 0:
                    if self.remove_album(album_id, album_name):
                        LOGGER.info(f"Empty album '{album_name}' (ID={album_id}) removed.")
                        total_removed_empty_albums += 1

            LOGGER.info(f"Removed {total_removed_empty_albums} empty albums.")
            # self.logout(log_level=log_level)
            return total_removed_empty_albums

    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all duplicate albums in Immich Photos.

        Duplicates are albums that share the same item count and total item size.
        The function keeps the first album (sorted by album name) and removes the rest.
        Before deleting, it displays the list of albums to be removed and asks for user confirmation.

        Args:
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            int: The number of duplicate albums deleted.
            :param request_user_confirmation:
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            LOGGER.info("Retrieving albums from Immich Photos to detect duplicates. This may take some time, please be patient...")
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                # self.logout(log_level=log_level)
                return 0

            LOGGER.info(f"Searching for duplicate albums in Immich Photos...")
            duplicates_map = {}
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for duplicate albums", unit="albums"):
                album_date = album.get("createdAt")
                if is_date_outside_range(album_date):
                    continue
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                assets_count = album.get("assetCount")
                assets_size = self.get_album_assets_size(album_id, log_level=log_level)
                duplicates_map.setdefault((assets_count, assets_size), []).append((album_id, album_name))

            albums_to_remove = []
            for (assets_count, assets_size), group in duplicates_map.items():
                LOGGER.debug(f"Assets Count: {assets_count}. Assets Size: {assets_size}.")
                if len(group) > 1:
                    group_sorted = sorted(group, key=lambda x: x[1])  # Sort by album name
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

            # Ask for confirmation only if requested
            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                return 0

            total_removed_duplicated_albums = 0
            for alb_id, alb_name in albums_to_remove:
                LOGGER.info(f"Removing duplicate album: '{alb_name}' (ID={alb_id})")
                if self.remove_album(alb_id, alb_name):
                    total_removed_duplicated_albums += 1

            LOGGER.info(f"Removed {total_removed_duplicated_albums} duplicate albums.")
            # self.logout(log_level=log_level)
            return total_removed_duplicated_albums


    def merge_duplicates_albums(self, strategy='count', request_user_confirmation=True, log_level=logging.WARNING):
        """
        Merge all duplicate albums in Immich Photos. Duplicates are albums
        with the same name but different assets. Keeps the album with the highest
        number of assets or largest size (based on strategy), moves the assets from the
        others into it, then deletes the others.

        Args:
            strategy (str): 'count' to keep album with most assets, 'size' to keep album with largest size
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: The number of duplicate albums deleted.
            :param request_user_confirmation:
        """
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level)
            if not albums:
                # self.logout(log_level=log_level)
                return 0

            LOGGER.info(f"Looking for duplicate albums in Immich Photos...")
            albums_by_name = {}
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Grouping Albums by Name", unit=" albums"):
                # Check if Album Creation date is outside filters date range (if provided), in that case, skip this album
                album_date = album.get("create_time")
                if is_date_outside_range(album_date):
                    continue

                album_id = album.get("id")
                album_name = album.get("albumName", "")
                asset_count = album.get("assetCount", 0)
                if strategy=='size':
                    assets_size = self.get_album_assets_size(album_id, log_level=log_level)
                else:
                    assets_size = 'Undefined'

                albums_by_name.setdefault(album_name, []).append({
                    "id": album_id,
                    "name": album_name,
                    "count": asset_count,
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
            for album_name, album_group in albums_by_name.items():
                if len(album_group) <= 1:
                    continue  # No duplicates

                if strategy == 'size':
                    sorted_group = sorted(album_group, key=lambda x: x["size"], reverse=True)
                else:  # Default to 'count'
                    sorted_group = sorted(album_group, key=lambda x: x["count"], reverse=True)

                keeper = sorted_group[0]
                keeper_id = keeper["id"]
                keeper_name = keeper["name"]

                LOGGER.info(f"Merging duplicates of album '{album_name}' into ID={keeper_id} with {keeper['count']} assets and {keeper['size']} bytes.")

                for duplicate in sorted_group[1:]:
                    dup_id = duplicate["id"]
                    dup_name = duplicate["name"]
                    dup_size = duplicate["size"]

                    LOGGER.debug(f"Transferring assets from duplicate album '{dup_name}' (ID={dup_id}, Size={dup_size} bytes)")
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
            return total_merged_albums, total_removed_duplicated_albums

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
                LOGGER.error(f"Both admin and user API keys are required.")
                # logout_immich
                # self.logout(log_level=log_level)
                return 0

            immich_parsed_url = urlparse(self.IMMICH_URL)
            base_url = f'{immich_parsed_url.scheme}://{immich_parsed_url.netloc}'
            api_url = f'{base_url}/api'
            server_info_url = f'{api_url}/server-info'
            file_report_url = api_url + '/reports'
            headers = {'x-api-key': self.IMMICH_API_KEY_ADMIN}

            def parse_version_tuple(version_text):
                """
                Parse version text like 'v1.133.0' into tuple (1, 133, 0).
                """
                match = re.search(r'(\d+)\.(\d+)\.(\d+)', str(version_text or ''))
                if not match:
                    return None
                return int(match.group(1)), int(match.group(2)), int(match.group(3))

            # Immich removed /api/reports in newer versions (from v1.133.0).
            # Detect version first to avoid noisy 404 errors and abort gracefully.
            try:
                server_info_response = requests.get(server_info_url, headers=headers, timeout=15)
                if server_info_response.ok:
                    server_info = server_info_response.json() or {}
                    detected_version = (
                        server_info.get('serverVersion')
                        or server_info.get('version')
                        or server_info.get('appVersion')
                        or server_info.get('build')
                        or ''
                    )
                    parsed_version = parse_version_tuple(detected_version)
                    if parsed_version and parsed_version >= (1, 133, 0):
                        LOGGER.warning(
                            f"'Remove Orphan Assets' is not supported on Immich {detected_version}: "
                            f"endpoint '/api/reports' was removed in newer Immich versions. "
                            f"Module aborted without changes."
                        )
                        return 0
            except Exception:
                # If version can't be detected, continue and fallback to endpoint probing below.
                pass

            print()
            spinner = Halo(text='Retrieving list of orphaned media assets...', spinner='dots')
            spinner.start()

            total_removed_assets = 0
            try:
                response = requests.get(file_report_url, headers=headers)
                response.raise_for_status()
                spinner.succeed('Success!')
            except requests.exceptions.RequestException as e:
                status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                if status_code == 404:
                    spinner.fail("Not supported by current Immich API (404).")
                    LOGGER.warning(
                        f"'Remove Orphan Assets' endpoint '/api/reports' is not available on this Immich server. "
                        f"Your version likely removed this API. Module aborted without changes."
                    )
                else:
                    spinner.fail(f'Failed to fetch assets: {str(e)}')
                # logout_immich
                # self.logout(log_level=log_level)
                return 0


            orphan_media_assets = filter_entities(response.json(), 'asset')
            num_entries = len(orphan_media_assets)

            if num_entries == 0:
                LOGGER.info(f"No orphaned media assets found.")
                # logout_immich
                # self.logout(log_level=log_level)
                return total_removed_assets

            if user_confirmation:
                table_data = [[asset['pathValue'], asset['entityId']] for asset in orphan_media_assets]
                LOGGER.info(f"{tabulate(table_data, headers=['Path Value', 'Entity ID'], tablefmt='pretty')}")
                LOGGER.info(f"")

                summary = f'There {"is" if num_entries == 1 else "are"} {num_entries} orphaned media asset{"s" if num_entries != 1 else ""}. Would you like to remove {"them" if num_entries != 1 else "it"} from Immich? (yes/no): '
                user_input = input(summary).lower()
                LOGGER.info(f"")

                if user_input not in ('y', 'yes'):
                    LOGGER.info(f"Exiting without making any changes.")
                    # logout_immich
                    # self.logout(log_level=log_level)
                    return 0

            headers['x-api-key'] = self.IMMICH_USER_API_KEY  # Use user API key for deletion
            with tqdm(total=num_entries, desc=f"{MSG_TAGS['INFO']}Removing orphaned media assets", unit="asset") as progress_bar:
                for asset in orphan_media_assets:
                    entity_id = asset['entityId']
                    asset_url = f'{api_url}/assets'
                    remove_payload = json.dumps({'force': True, 'ids': [entity_id]})
                    headers = {'Content-Type': 'application/json', 'x-api-key': self.IMMICH_USER_API_KEY}
                    try:
                        response = requests.delete(asset_url, headers=headers, data=remove_payload)
                        response.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        if response.status_code == 400:
                            LOGGER.warning(f"Failed to remove asset {entity_id} due to potential API key mismatch. Ensure you're using the asset owners API key as the User API key.")
                        else:
                            LOGGER.warning(f"Failed to remove asset {entity_id}: {str(e)}")
                        continue
                    
                    progress_bar.update(1)
                    total_removed_assets += 1
            LOGGER.info(f"Orphaned media assets removed successfully!")
            # logout_immich
            # self.logout(log_level=log_level)
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
            LOGGER.info(f"Getting list of asset(s) to remove...")

            # Collect
            all_assets_items = self.get_assets_by_filters(log_level=log_level)
            all_assets_items_with_deleted = self.get_assets_by_filters(with_deleted=True, log_level=log_level)
            all_assets_items.extend(all_assets_items_with_deleted)

            total_assets_found = len(all_assets_items)
            if total_assets_found == 0:
                LOGGER.warning(f"No Assets found that matches filters criteria in Immich Database.")
            LOGGER.info(f"Found {total_assets_found} asset(s) to remove.")

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
                with tqdm(total=total_assets_found, desc=f"{MSG_TAGS['INFO']}Removing assets", unit=" assets") as pbar:
                    for i in range(0, len(assets_ids), BATCH_SIZE):
                        batch = assets_ids[i:i + BATCH_SIZE]
                        removed_count = self.remove_assets(batch, log_level=logging.WARNING)
                        total_removed_assets += removed_count
                        pbar.update(len(batch))

            LOGGER.info(f"Getting empty albums to remove...")
            total_removed_albums = self.remove_empty_albums(log_level=logging.WARNING)

            # self.logout(log_level=log_level)
            LOGGER.info(f"Total Assets removed: {total_removed_assets}")
            LOGGER.info(f"Total Albums removed: {total_removed_albums}")

            return total_removed_assets, total_removed_albums

##############################################################################
#                                END OF CLASS                                #
##############################################################################


##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.

    change_working_dir(change_dir=False)

    # Create the Object
    immich = ClassImmichPhotos()

    # 0) Read configuration and log in
    immich.read_config_file(CONFIGURATION_FILE)
    immich.login()

    # 1) Example: Remove empty albums
    print("\n=== EXAMPLE: remove_empty_albums() ===")
    removed = immich.remove_empty_albums(log_level=logging.DEBUG)
    print(f"[RESULT] Empty albums removed: {removed}")

    # 2) Example: Remove duplicate albums
    print("\n=== EXAMPLE: remove_duplicates_albums() ===")
    duplicates = immich.remove_duplicates_albums(log_level=logging.DEBUG)
    print(f"[RESULT] Duplicate albums removed: {duplicates}")

    # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\No-Albums'
    print("\n=== EXAMPLE: push_no_albums() ===")
    big_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\No-Albums"
    immich.push_no_albums(big_folder, log_level=logging.DEBUG)

    # 4) Example: Create albums from subfolders in 'r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\Albums'
    print("\n=== EXAMPLE: push_albums() ===")
    input_albums_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\Albums"
    immich.push_albums(input_albums_folder, log_level=logging.DEBUG)

    # 5) Example: Download all photos from ALL albums
    print("\n=== EXAMPLE: pull_albums() ===")
    # total = pull_albums('ALL', output_folder="Downloads_Immich")
    total_albums, total_assets = immich.pull_albums("1994 - Recuerdos", output_folder="Downloads_Immich", log_level=logging.DEBUG)
    print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums} different albbums.")

    # 6) Example: Download everything in the structure /Albums/<albumName>/ + /<NO_ALBUMS_FOLDER>/yyyy/mm
    print("\n=== EXAMPLE: pull_all() ===")
    # total_struct = pull_all(output_folder="Downloads_Immich")
    total_albums_downloaded, total_assets_downloaded = immich.pull_all(output_folder="Downloads_Immich", log_level=logging.DEBUG)
    print(f"[RESULT] Bulk download completed. \nTotal albums: {total_albums_downloaded}\nTotal assets: {total_assets_downloaded}.")

    # 7) Example: Remove Orphan Assets
    immich.remove_orphan_assets(user_confirmation=True, log_level=logging.DEBUG)

    # 8) Example: Remove ALL Assets
    immich.remove_all_assets(log_level=logging.DEBUG)

    # 9) Example: Remove ALL Assets
    immich.remove_all_albums(remove_album_assets=True, log_level=logging.DEBUG)

    # 10) Local logout
    immich.logout()
