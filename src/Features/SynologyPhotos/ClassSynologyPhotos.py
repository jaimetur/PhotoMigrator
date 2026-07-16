# -*- coding: utf-8 -*-

import fnmatch
import json
import logging
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime

import requests
import urllib3
from requests_toolbelt.multipart.encoder import MultipartEncoder

from Core.CustomLogger import set_log_level
from Core.GlobalVariables import ARGS, LOGGER, MSG_TAGS, FOLDERNAME_NO_ALBUMS, CONFIGURATION_FILE, FOLDERNAME_ALBUMS
from Features.BaseMediaClient import BaseMediaClient
from Utils.DateUtils import parse_text_datetime_to_epoch, is_date_outside_range
from Utils.FileUtils import matches_any_pattern, merge_exclusion_patterns
from Utils.GeneralUtils import update_metadata, convert_to_list, get_unique_items, tqdm, match_pattern, replace_pattern, has_any_filter, confirm_continue, sha1_checksum, find_reusable_album_candidate, build_reusable_album_group, canonicalize_album_name_for_reuse, prefer_canonical_album_names_enabled, consolidate_similar_albums_enabled, scan_album_consolidation_groups, print_album_consolidation_preview

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
     - pull_all()
"""

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassSynologyPhotos(BaseMediaClient):
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
        self.CURRENT_OWNER_USER_ID = None

        # Create cache lists for future use
        self.all_assets_filtered = None
        self.assets_without_albums_filtered = None
        self.albums_assets_filtered = None
        self.shared_album_access_cache = {}
        self.album_runtime_details_cache = {}

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

    @staticmethod
    def _extract_album_permissions(album):
        if not isinstance(album, dict):
            return []
        candidates = [
            album.get("permission"),
            (album.get("sharing_info") or {}).get("permission"),
            (album.get("additional") or {}).get("permission"),
            ((album.get("additional") or {}).get("sharing_info") or {}).get("permission"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list) and candidate:
                return candidate
        return []

    @staticmethod
    def _normalize_album_category(album):
        if not isinstance(album, dict):
            return ""
        return str(album.get('category') or album.get('album_type') or album.get('type') or "").strip().lower()

    @staticmethod
    def _normalize_user_id(value):
        text = str(value or "").strip()
        return text or None

    @classmethod
    def _extract_album_owner_user_id(cls, album):
        if not isinstance(album, dict):
            return None
        candidates = [
            album.get("_synology_owner_user_id"),
            album.get("owner_user_id"),
            album.get("user_id"),
            (album.get("sharing_info") or {}).get("owner_user_id"),
            (album.get("sharing_info") or {}).get("user_id"),
            (album.get("additional") or {}).get("owner_user_id"),
            (album.get("additional") or {}).get("user_id"),
            (album.get("additional") or {}).get("sharing_info", {}).get("owner_user_id"),
            (album.get("additional") or {}).get("sharing_info", {}).get("user_id"),
        ]
        for candidate in candidates:
            normalized = cls._normalize_user_id(candidate)
            if normalized is not None:
                return normalized
        return None

    @classmethod
    def _extract_album_primary_permission_role(cls, album):
        permissions = cls._extract_album_permissions(album)
        if not permissions:
            return ""
        return str((permissions[0] or {}).get("role") or "").strip().lower()

    @classmethod
    def is_shared_with_me_album(cls, album):
        if not isinstance(album, dict):
            return False
        explicit_scope = str(album.get("_synology_album_scope") or "").strip().lower()
        if explicit_scope == "shared_with_me":
            return True
        if explicit_scope in {"owned", "owned_personal", "owned_shared_space"}:
            return False
        category = cls._normalize_album_category(album)
        return "share_with_me" in category

    @classmethod
    def is_album_owned_by_user(cls, album):
        if not isinstance(album, dict):
            return False
        explicit_scope = str(album.get("_synology_album_scope") or "").strip().lower()
        if explicit_scope in {"owned", "owned_personal", "owned_shared_space"}:
            return True
        if explicit_scope == "shared_with_me":
            return False
        return not cls.is_shared_with_me_album(album)

    @classmethod
    def is_shared_album(cls, album):
        if not isinstance(album, dict):
            return False
        return cls.is_shared_with_me_album(album)

    @classmethod
    def is_blocked_shared_album(cls, album):
        if not cls.is_shared_album(album):
            return False
        permissions = cls._extract_album_permissions(album)
        if not permissions:
            return False
        role = str((permissions[0] or {}).get("role") or "").strip().lower()
        return role == "view"

    @classmethod
    def normalize_album_payload(cls, album, scope=None):
        if not isinstance(album, dict):
            return album
        normalized_album = dict(album)
        if "name" in normalized_album and "albumName" not in normalized_album:
            normalized_album["albumName"] = normalized_album.pop("name")
        owner_user_id = cls._extract_album_owner_user_id(normalized_album)
        if owner_user_id is not None:
            normalized_album["_synology_owner_user_id"] = owner_user_id
        if scope:
            normalized_album["_synology_album_scope"] = scope
        elif "_synology_album_scope" not in normalized_album:
            normalized_album["_synology_album_scope"] = "shared_with_me" if cls.is_shared_with_me_album(normalized_album) else "owned"
        return normalized_album

    def _remember_current_owner_user_id(self, album):
        owner_user_id = self._extract_album_owner_user_id(album)
        if not owner_user_id or getattr(self, "CURRENT_OWNER_USER_ID", None):
            return
        if self.is_album_owned_by_user(album):
            self.CURRENT_OWNER_USER_ID = owner_user_id
            return

        permission_role = self._extract_album_primary_permission_role(album)
        category = self._normalize_album_category(album)
        if "share_with_me" in category and permission_role == "full":
            # Synology Shared Space albums can be exposed through the
            # `normal_share_with_me` namespace even when they still belong to
            # the current account. We cannot always query the numeric current
            # owner id directly, so we learn it from the first album that the
            # browser exposes in that namespace with `full` permissions. Once
            # discovered, every other album with the same owner_user_id can be
            # classified deterministically as `owned_shared_space`.
            self.CURRENT_OWNER_USER_ID = owner_user_id

    def _infer_album_scope(self, album, fallback_scope=None):
        """
        Infer the Synology album scope as precisely as possible.

        Synology "Shared Space" albums can appear under the
        `normal_share_with_me` namespace even when they are still owned by the
        current user. Issue #1173 showed that those albums must be handled with
        the normal album/item APIs (`album_id` context) instead of the
        passphrase-based "shared with me" flow.

        Scope meanings:
          - owned_personal: regular owned album in Personal Space
          - owned_shared_space: album owned by current user but exposed through
            Synology's Shared Space namespace
          - shared_with_me: album owned by another user and shared to us
        """
        normalized_album = self.normalize_album_payload(album)
        category = self._normalize_album_category(normalized_album)
        owner_user_id = self._extract_album_owner_user_id(normalized_album)
        current_owner_user_id = self._normalize_user_id(getattr(self, "CURRENT_OWNER_USER_ID", None))
        permission_role = self._extract_album_primary_permission_role(normalized_album)

        if owner_user_id and current_owner_user_id and owner_user_id == current_owner_user_id:
            return "owned_shared_space" if "share_with_me" in category else "owned_personal"

        if fallback_scope in {"owned", "owned_personal"}:
            return "owned_personal"
        if fallback_scope == "owned_shared_space":
            return "owned_shared_space"

        # When we do not yet know the numeric owner ID of the current account,
        # use the observed Shared Space heuristic from issue #1173: albums
        # surfaced in `normal_share_with_me` but with "full" permissions behave
        # like owned albums and must use `album_id`-context list/download calls.
        if fallback_scope == "shared_with_me" and permission_role == "full":
            return "owned_shared_space"

        if fallback_scope == "shared_with_me":
            return "shared_with_me"

        if "share_with_me" in category:
            return "shared_with_me"
        return "owned_personal"

    def _hydrate_album_payload(self, album, fallback_scope=None):
        normalized_album = self.normalize_album_payload(album)
        scope = self._infer_album_scope(normalized_album, fallback_scope=fallback_scope)
        normalized_album["_synology_album_scope"] = scope
        owner_user_id = self._extract_album_owner_user_id(normalized_album)
        if owner_user_id is not None:
            normalized_album["_synology_owner_user_id"] = owner_user_id
        self._remember_current_owner_user_id(normalized_album)
        return normalized_album

    def _extract_passphrase_from_album_payload(self, payload):
        candidates = []
        if isinstance(payload, dict):
            candidates.extend([
                payload,
                payload.get("data"),
                (payload.get("data") or {}).get("album") if isinstance(payload.get("data"), dict) else None,
                (payload.get("data") or {}).get("list") if isinstance(payload.get("data"), dict) else None,
            ])
        for candidate in candidates:
            if isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict):
                        value = str(item.get("passphrase") or "").strip()
                        if value:
                            return value
                        value = str(((item.get("sharing_info") or {}).get("passphrase")) or "").strip()
                        if value:
                            return value
                        value = str((((item.get("additional") or {}).get("sharing_info") or {}).get("passphrase")) or "").strip()
                        if value:
                            return value
            elif isinstance(candidate, dict):
                value = str(candidate.get("passphrase") or "").strip()
                if value:
                    return value
                value = str(((candidate.get("sharing_info") or {}).get("passphrase")) or "").strip()
                if value:
                    return value
                value = str((((candidate.get("additional") or {}).get("sharing_info") or {}).get("passphrase")) or "").strip()
                if value:
                    return value
        return ""

    @staticmethod
    def _parse_album_expected_count(value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            return None
        return parsed_value if parsed_value >= 0 else None

    @staticmethod
    def _iter_entry_transport_variants(prefer_post=False):
        if prefer_post:
            yield "post", "data"
        yield "get", "params"
        if not prefer_post:
            yield "post", "data"

    def _request_entry_api(self, url, payload, headers=None, prefer_post=False, stream=False):
        last_error = None
        for method_name, payload_key in self._iter_entry_transport_variants(prefer_post=prefer_post):
            request_method = getattr(self.SESSION, method_name)
            try:
                return request_method(
                    url,
                    headers=headers,
                    verify=False,
                    stream=stream,
                    **{payload_key: payload},
                )
            except Exception as error:
                last_error = error
        if last_error:
            raise last_error
        raise RuntimeError("No valid Synology entry.cgi transport available")

    def _fetch_album_details(self, album_id, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
            headers = {}
            if self.SYNO_TOKEN_HEADER:
                headers.update(self.SYNO_TOKEN_HEADER)

            params = {
                "api": "SYNO.Foto.Browse.Album",
                "method": "get",
                "version": "4",
                "id": album_id,
                "additional": '["sharing_info","flex_section","provider_count","thumbnail"]',
            }
            response = self._request_entry_api(url, params, headers=headers, prefer_post=True)
            response.raise_for_status()
            data = response.json()
            if not data.get("success"):
                return None

            payload_data = data.get("data") or {}
            if isinstance(payload_data, dict):
                if isinstance(payload_data.get("album"), dict):
                    return payload_data.get("album")
                if isinstance(payload_data.get("list"), list) and payload_data.get("list"):
                    if isinstance(payload_data["list"][0], dict):
                        return payload_data["list"][0]
            return None

    def _ensure_album_runtime_details(self, album, log_level=None):
        """
        Enrich album payloads with runtime-only details required by list/download calls.

        Synology's list endpoints do not always include `item_count`, and issue
        #1173 showed that some Shared Space albums exposed through
        `normal_share_with_me` can return an empty success response for one item
        listing variant while another variant returns the real contents. We
        therefore try to learn the authoritative album payload first, so both
        Automatic Migration and the standalone Synology download flows evaluate
        the same album metadata before trying item-list fallbacks.
        """
        with set_log_level(LOGGER, log_level):
            if not isinstance(album, dict):
                return album

            album = self._hydrate_album_payload(album)
            album_id = str(album.get("id") or "").strip()
            if not album_id:
                return album

            album_runtime_details_cache = getattr(self, "album_runtime_details_cache", None)
            if album_runtime_details_cache is None:
                album_runtime_details_cache = {}
                self.album_runtime_details_cache = album_runtime_details_cache

            cached_album = album_runtime_details_cache.get(album_id)
            if isinstance(cached_album, dict):
                merged_album = dict(album)
                merged_album.update(cached_album)
                return self._hydrate_album_payload(merged_album, fallback_scope=album.get("_synology_album_scope"))

            album_scope = album.get("_synology_album_scope")
            expected_count = self._parse_album_expected_count(album.get("item_count"))
            needs_item_count = expected_count is None
            needs_passphrase = self.is_shared_with_me_album(album) and not str(album.get("passphrase") or "").strip()
            if not needs_item_count and not needs_passphrase:
                album_runtime_details_cache[album_id] = dict(album)
                return album

            enriched_album = dict(album)
            try:
                detailed_album = self._fetch_album_details(album_id=album_id, log_level=log_level)
                if isinstance(detailed_album, dict):
                    enriched_album.update(detailed_album)
                    enriched_album = self._hydrate_album_payload(enriched_album, fallback_scope=album_scope)

                resolved_passphrase = self._extract_passphrase_from_album_payload(detailed_album or {})
                if resolved_passphrase and not str(enriched_album.get("passphrase") or "").strip():
                    enriched_album["passphrase"] = resolved_passphrase

                if self._parse_album_expected_count(enriched_album.get("item_count")) is None:
                    counted_assets = self.get_album_assets_count(
                        album_id=album_id,
                        album_name=enriched_album.get("albumName", ""),
                        album_passphrase=enriched_album.get("passphrase"),
                        album_scope=enriched_album.get("_synology_album_scope"),
                        log_level=log_level,
                    )
                    counted_assets = self._parse_album_expected_count(counted_assets)
                    if counted_assets is not None:
                        enriched_album["item_count"] = counted_assets
            except Exception as error:
                LOGGER.debug(f"Could not enrich Synology album runtime details for album ID={album_id}: {error}")

            album_runtime_details_cache[album_id] = dict(enriched_album)
            return enriched_album

    def ensure_shared_album_access(self, album, log_level=None):
        with set_log_level(LOGGER, log_level):
            if not isinstance(album, dict):
                return album
            album = self._hydrate_album_payload(album)
            if not self.is_shared_with_me_album(album):
                return album
            if str(album.get("passphrase") or "").strip():
                return album

            album_id = str(album.get("id") or "").strip()
            if not album_id:
                return album
            shared_album_access_cache = getattr(self, "shared_album_access_cache", None)
            if shared_album_access_cache is None:
                shared_album_access_cache = {}
                self.shared_album_access_cache = shared_album_access_cache
            cached_album = shared_album_access_cache.get(album_id)
            if isinstance(cached_album, dict):
                album.update(cached_album)
                return album

            try:
                candidate_album = self._fetch_album_details(album_id=album_id, log_level=log_level)
                if isinstance(candidate_album, dict):
                    album.update(candidate_album)
                    album = self._hydrate_album_payload(album, fallback_scope="shared_with_me")

                resolved_passphrase = self._extract_passphrase_from_album_payload(candidate_album or {})
                if resolved_passphrase:
                    album["passphrase"] = resolved_passphrase
                    LOGGER.debug(f"Resolved shared album passphrase for album ID={album_id}.")
            except Exception as error:
                LOGGER.debug(f"Could not resolve shared album access details for album ID={album_id}: {error}")
            shared_album_access_cache[album_id] = dict(album)
            return album

    def _list_shared_with_me_albums(self, log_level=None):
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

                    response = self._request_entry_api(url, params, headers=headers, prefer_post=True)
                    data = response.json()
                    if not data.get("success"):
                        LOGGER.error(f"Failed to list shared albums with current user: {data}")
                        return None
                    album_list.extend([
                        self._hydrate_album_payload(album, fallback_scope="shared_with_me")
                        for album in data["data"]["list"]
                    ])
                    if len(data["data"]["list"]) < limit:
                        break
                    offset += limit
                return album_list
            except Exception as e:
                LOGGER.error(f"Exception while listing shared albums with current user. {e}")
                return None


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
    def create_album(self, album_name, shared=False, log_level=None):
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
                    album = self._hydrate_album_payload(album, fallback_scope="owned_personal")
                    album = self._ensure_album_runtime_details(album, log_level=log_level)
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    if filter_assets and has_any_filter():
                        if self.is_shared_with_me_album(album):
                            album_assets = self.get_all_assets_from_album_shared(
                                album_id,
                                album_name,
                                album_passphrase=album.get("passphrase"),
                                album_scope=album.get("_synology_album_scope"),
                                album_expected_count=album.get("item_count"),
                                log_level=log_level,
                            )
                        else:
                            album_assets = self.get_all_assets_from_album(
                                album_id,
                                album_name,
                                album_scope=album.get("_synology_album_scope"),
                                album_expected_count=album.get("item_count"),
                                log_level=log_level,
                            )
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
            owned_albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or []
            shared_with_me_albums = self._list_shared_with_me_albums(log_level=log_level) or []

            deduped_albums = {}
            ordered_ids = []
            for album in owned_albums + shared_with_me_albums:
                album = self._hydrate_album_payload(album)
                album_id = str(album.get("id") or "").strip()
                if not album_id:
                    continue
                existing = deduped_albums.get(album_id)
                if existing is None:
                    deduped_albums[album_id] = album
                    ordered_ids.append(album_id)
                    continue
                if self.is_album_owned_by_user(album) and not self.is_album_owned_by_user(existing):
                    deduped_albums[album_id] = album

            albums_filtered = []
            for album_id in ordered_ids:
                album = deduped_albums[album_id]
                album = self.ensure_shared_album_access(album, log_level=log_level)
                album = self._hydrate_album_payload(album)
                album = self._ensure_album_runtime_details(album, log_level=log_level)
                album_id = album.get('id')
                album_name = album.get("albumName", "")
                if filter_assets and has_any_filter():
                    if self.is_shared_with_me_album(album):
                        album_assets = self.get_all_assets_from_album_shared(
                            album_id,
                            album_name,
                            album_passphrase=album.get("passphrase"),
                            album_scope=album.get("_synology_album_scope"),
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    else:
                        album_assets = self.get_all_assets_from_album(
                            album_id,
                            album_name,
                            album_scope=album.get("_synology_album_scope"),
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    if len(album_assets) > 0:
                        albums_filtered.append(album)
                else:
                    albums_filtered.append(album)
            return albums_filtered


    def get_album_assets_size(self, album_id, album_name=None, type='all', album_passphrase=None, album_scope='owned_personal', log_level=None):
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
            

    def get_album_assets_count(self, album_id, album_name=None, type='all', album_passphrase=None, album_scope="owned_personal", log_level=None):
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

                failure_messages = []
                for variant in self._iter_album_item_request_variants(
                    album_id=album_id,
                    album_scope=album_scope,
                    album_passphrase=album_passphrase,
                ):
                    params = {
                        "api": variant["api"],
                        "method": "count",
                        "version": variant["version"],
                        "album_id": variant["album_id"],
                    }
                    if variant.get("passphrase"):
                        params["passphrase"] = variant["passphrase"]
                    try:
                        prefer_post = album_scope in {"owned_shared_space", "shared_with_me"}
                        response = self._request_entry_api(url, params, headers=headers, prefer_post=prefer_post)
                        response.raise_for_status()
                        data = response.json()
                        if not data.get("success"):
                            failure_messages.append(f"variant={params.get('version')}/count response={data}")
                            continue
                        count = self._parse_album_expected_count((data.get("data") or {}).get("count"))
                        if count is not None:
                            return count
                    except Exception as e:
                        failure_messages.append(f"variant={params.get('version')}/count error={e}")
                        continue

                LOGGER.warning(f"Cannot count files for album: '{album_name}' due to API call error. Skipped!")
                if failure_messages:
                    LOGGER.debug("Album count variants tried: " + " | ".join(failure_messages))
                return -1
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets count from Synology Photos. {e}")


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
    def get_assets_by_filters(self, type='all', is_not_in_album=None, is_archived=None, with_deleted=None, log_level=logging.WARNING):
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
            

    def _iter_album_item_request_variants(self, album_id, album_scope="owned_personal", album_passphrase=None):
        """
        Yield request variants for album item listing.

        Synology's browser and API behavior is not uniform across namespaces:
          - Personal-space owned albums have historically worked with
            `SYNO.Foto.Browse.Item` version 4.
          - Issue #1173 showed that Shared Space albums exposed under the
            `normal_share_with_me` namespace are still listed by the browser
            with `version=7`, `album_id=<id>` and *without* passphrase.
          - True "shared with me" albums may still require the passphrase-based
            flow, so we keep that as a fallback instead of replacing it.
        """
        common_v4 = '["thumbnail","resolution","orientation","video_convert","video_meta","address"]'
        common_v7 = '["thumbnail","resolution","orientation","video_convert","video_meta","provider_user_id"]'
        variants = []

        if album_scope in {"owned_shared_space", "shared_with_me"}:
            variants.append({
                "api": "SYNO.Foto.Browse.Item",
                "version": "7",
                "method": "list",
                "album_id": album_id,
                "sort_by": "takentime",
                "sort_direction": "asc",
                "additional": common_v7,
            })

        variants.append({
            "api": "SYNO.Foto.Browse.Item",
            "version": "4",
            "method": "list",
            "album_id": album_id,
            "additional": common_v4,
        })

        if album_scope == "shared_with_me" and album_passphrase:
            variants.append({
                "api": "SYNO.Foto.Browse.Item",
                "version": "4",
                "method": "list",
                "album_id": album_id,
                "passphrase": album_passphrase,
                "additional": common_v4,
            })
            variants.append({
                "api": "SYNO.Foto.Browse.Item",
                "version": "7",
                "method": "list",
                "album_id": album_id,
                "passphrase": album_passphrase,
                "sort_by": "takentime",
                "sort_direction": "asc",
                "additional": common_v7,
            })

        seen = set()
        for variant in variants:
            key = json.dumps(variant, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            yield variant

    def _get_album_assets_via_variants(self, album_id, album_name=None, album_passphrase=None, album_scope="owned_personal", album_expected_count=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.login(log_level=log_level)
            url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
            headers = {}
            if self.SYNO_TOKEN_HEADER:
                headers.update(self.SYNO_TOKEN_HEADER)

            failure_messages = []
            saw_successful_empty_response = False
            expected_count = self._parse_album_expected_count(album_expected_count)
            variants = list(self._iter_album_item_request_variants(album_id=album_id, album_scope=album_scope, album_passphrase=album_passphrase))
            for index, base_params in enumerate(variants):
                offset = 0
                limit = 5000
                album_assets = []
                while True:
                    params = dict(base_params)
                    params["offset"] = offset
                    params["limit"] = limit
                    try:
                        prefer_post = album_scope in {"owned_shared_space", "shared_with_me"}
                        resp = self._request_entry_api(url, params, headers=headers, prefer_post=prefer_post)
                        data = resp.json()
                        if not data.get("success"):
                            failure_messages.append(f"variant={params.get('version')}/{params.get('method')} response={data}")
                            album_assets = None
                            break
                        page = list((data.get("data") or {}).get("list") or [])
                        if page:
                            album_assets.extend(page)
                        if len(page) < limit:
                            break
                        offset += limit
                    except Exception as e:
                        failure_messages.append(f"variant={params.get('version')}/{params.get('method')} error={e}")
                        album_assets = None
                        break

                if album_assets is None:
                    continue
                if album_assets:
                    return self.filter_assets(assets=album_assets, log_level=log_level)

                saw_successful_empty_response = True

                # Synology may return `success=true` with an empty list for a
                # syntactically valid variant that does not actually match the
                # album namespace. Do not trust that first empty response unless
                # the album is already known to be truly empty.
                if expected_count == 0:
                    return []
                if index == len(variants) - 1:
                    break

                LOGGER.debug(
                    f"Synology album listing variant returned no items for album ID={album_id} "
                    f"(variant {index + 1}/{len(variants)}, scope={album_scope}, expected_count={expected_count}). "
                    "Trying the next variant."
                )

            if saw_successful_empty_response and expected_count is None:
                return []

            if album_name:
                LOGGER.error(f"Failed to list photos in the album '{album_name}'")
            else:
                LOGGER.error(f"Failed to list photos in the album ID={album_id}")
            if failure_messages:
                LOGGER.debug("Album list variants tried: " + " | ".join(failure_messages))
            return []

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", album_scope="owned_personal", album_expected_count=None, log_level=None):
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
                return self._get_album_assets_via_variants(
                    album_id=album_id,
                    album_name=album_name,
                    album_scope=album_scope,
                    album_expected_count=album_expected_count,
                    log_level=log_level,
                )
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets from Synology Photos. {e}")


    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, album_scope="shared_with_me", album_expected_count=None, log_level=None):
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
                return self._get_album_assets_via_variants(
                    album_id=album_id,
                    album_name=album_name,
                    album_passphrase=album_passphrase,
                    album_scope=album_scope,
                    album_expected_count=album_expected_count,
                    log_level=log_level,
                )
            except Exception as e:
                LOGGER.error(f"Exception while getting Album Assets from Synology Photos. {e}")


    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
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

                all_albums = self.get_albums_including_shared_with_user(filter_assets=False, log_level=log_level)
                combined_assets = []
                if not all_albums:
                    self.albums_assets_filtered = combined_assets  # Cache albums_assets for future use
                    return []
                for album in all_albums:
                    album = self.ensure_shared_album_access(album, log_level=log_level)
                    album = self._hydrate_album_payload(album)
                    album = self._ensure_album_runtime_details(album, log_level=log_level)
                    album_id = album.get("id")
                    album_name = album.get("albumName", "")
                    if self.is_shared_with_me_album(album):
                        album_assets = self.get_all_assets_from_album_shared(
                            album_id,
                            album_name,
                            album_passphrase=album.get("passphrase"),
                            album_scope=album.get("_synology_album_scope"),
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    else:
                        album_assets = self.get_all_assets_from_album(
                            album_id,
                            album_name,
                            album_scope=album.get("_synology_album_scope"),
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    combined_assets.extend(album_assets)
                self.albums_assets_filtered = combined_assets # Cache albums_assets for future use
                return combined_assets
            except Exception as e:
                LOGGER.error(f"Exception while getting All Albums Assets from Synology Photos. {e}")
            

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=logging.WARNING, return_details=False):
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
                confirmed_total = 0
                chunk_size = 500
                for start in range(0, len(asset_ids), chunk_size):
                    raw_chunk = asset_ids[start:start + chunk_size]
                    chunk = []
                    for asset_id in raw_chunk:
                        value = str(asset_id).strip()
                        if not value:
                            continue
                        chunk.append(int(value) if value.isdigit() else value)
                    if not chunk:
                        continue

                    params = {
                        "api": "SYNO.Foto.Browse.NormalAlbum",
                        "method": "add_item",
                        "version": "1",
                        "id": album_id,
                        "item": json.dumps(chunk, separators=(",", ":")),
                    }
                    resp = self.SESSION.get(url, params=params, headers=headers, verify=False)
                    resp.raise_for_status()
                    data = resp.json()

                    if not data["success"]:
                        response_text = json.dumps(data, ensure_ascii=False).lower()
                        if "duplicate" in response_text or "already" in response_text:
                            confirmed_total += len(chunk)
                            continue
                        if album_name:
                            LOGGER.warning(f"Cannot add assets to album: '{album_name}' due to API call error. Skipped!")
                        else:
                            LOGGER.warning(f"Cannot add assets to album ID: '{album_id}' due to API call error. Skipped!")
                        return confirmed_total
                    confirmed_total += len(chunk)

                if album_name:
                    LOGGER.info(f"{confirmed_total} Assets successfully added to album: '{album_name}'.")
                else:
                    LOGGER.info(f"{confirmed_total} Assets successfully added to album ID: '{album_id}'.")
                return confirmed_total

            except Exception as e:
                LOGGER.warning(f"Cannot add Assets to album: '{album_name}' due to API call error. Skipped!")
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
                duplicate_assets = self.get_all_assets_from_album(redundant_id, redundant_name, log_level=log_level) or []
                duplicate_asset_ids = [str(asset.get("id", "")).strip() for asset in duplicate_assets if str(asset.get("id", "")).strip()]
                total_redundant_assets = len(duplicate_asset_ids)
                reassigned_count = 0
                should_remove_redundant = False
                if duplicate_asset_ids:
                    added_count = self.add_assets_to_album(keeper_id, duplicate_asset_ids, keeper_name, log_level=log_level)
                    keeper_assets = self.get_all_assets_from_album(keeper_id, keeper_name, log_level=log_level) or []
                    keeper_asset_ids = {str(asset.get("id", "")).strip() for asset in keeper_assets if str(asset.get("id", "")).strip()}
                    reassigned_count = sum(1 for asset_id in duplicate_asset_ids if asset_id in keeper_asset_ids)
                    LOGGER.info(
                        f"Album Reassignment: '{redundant_name}' -> '{keeper_name}'. "
                        f"Requested={total_redundant_assets}, Confirmed={reassigned_count}, "
                        f"AddedNow={added_count if isinstance(added_count, int) else 0}."
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
                date_getter=lambda album: (album or {}).get("create_time"),
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
            url = f"{self.SYNOLOGY_URL}/webapi/entry.cgi"
            headers = {}
            if self.SYNO_TOKEN_HEADER:
                headers.update(self.SYNO_TOKEN_HEADER)

            base_params = {
                'api': 'SYNO.Foto.Browse.Item',
                'version': '2',
                'method': 'list_with_filter',
                'additional': '["thumbnail","resolution","orientation","video_convert","video_meta","address"]',
            }
            offset = 0
            limit = 5000
            all_assets = []
            while True:
                params = base_params.copy()
                params["offset"] = offset
                params["limit"] = limit
                resp = self.SESSION.get(url, headers=headers, params=params, verify=False)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("success"):
                    LOGGER.error("Failed to list assets while resolving Synology duplicate IDs")
                    return []
                batch = data.get("data", {}).get("list", [])
                all_assets.extend(batch)
                if len(batch) < limit:
                    break
                offset += limit
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
                target_time = int(stat.st_mtime)
                target_size = int(stat.st_size)
            except Exception:
                target_time = None
                target_size = None

            best_asset_id = None
            best_score = None
            for item in self._get_all_assets_unfiltered(log_level=log_level):
                candidate_name = str(item.get("filename") or item.get("name") or "")
                candidate_name_casefold = candidate_name.casefold()
                candidate_name_normalized = self._normalize_duplicate_lookup_name(candidate_name)
                exact_name_match = candidate_name_casefold == target_name_casefold
                normalized_name_match = candidate_name_normalized == target_name_normalized
                if not exact_name_match and not normalized_name_match:
                    continue
                candidate_id = str(item.get("id", "")).strip()
                if not candidate_id:
                    continue
                candidate_time = item.get("time")
                try:
                    candidate_time = int(candidate_time) if candidate_time is not None else None
                except Exception:
                    candidate_time = None
                candidate_size = item.get("filesize")
                try:
                    candidate_size = int(candidate_size) if candidate_size is not None else None
                except Exception:
                    candidate_size = None
                time_delta = abs(candidate_time - target_time) if candidate_time is not None and target_time is not None else float("inf")
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
                        if is_duplicated and not asset_id:
                            if not resolve_duplicate_id:
                                LOGGER.debug(
                                    f"Synology duplicate response without asset id for '{os.path.basename(file_path)}'. "
                                    f"Deferring existing asset resolution."
                                )
                                return None, True
                            resolved_asset_id = self._resolve_existing_asset_id(file_path, log_level=log_level)
                            if resolved_asset_id:
                                LOGGER.debug(
                                    f"Synology duplicate response without asset id for '{os.path.basename(file_path)}'. "
                                    f"Resolved existing asset_id={resolved_asset_id}."
                                )
                                return resolved_asset_id, True
                            LOGGER.warning(
                                f"Synology returned duplicate action without existing asset id for '{os.path.basename(file_path)}'. "
                                f"Response payload: {data}"
                            )
                            return None, None
                        if asset_id:
                            self._remember_uploaded_asset_id(file_path, asset_id)
                        if is_duplicated:
                            LOGGER.debug(f"Duplicated Asset: '{os.path.basename(file_path)}'. Existing asset_id={asset_id}")
                        else:
                            LOGGER.debug(f"Uploaded '{os.path.basename(file_path)}' with asset_id={asset_id}")
                        return asset_id, is_duplicated

            except Exception as e:
                LOGGER.warning(f"Cannot upload asset: '{file_path}' due to API call error. Skipped!")
                return None, None
            

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_Synology", album_passphrase=None, album_id=None, album_scope=None, log_level=None):
        """
        Downloads an asset (photo/video) from Synology Photos to a local folder,
        preserving the original timestamp if available.

        For some LIVE assets, Synology can return a ZIP payload that contains both
        image and video components (for example: HEIF + MOV). In that case this
        method extracts the ZIP contents into download_folder.

        Args:
            asset_id (int): ID of the asset to download.
            asset_filename (str): Name of the file to save.
            asset_time (int or str): UNIX epoch or ISO string time of the asset.
            album_passphrase (str): Passphrase for shared albums.
            album_id (str): Album context ID when the asset is being downloaded
                from a specific album.
            album_scope (str): Normalized album scope. For Shared Space albums
                discovered in issue #1173 we must include `album_id` even when
                the album is owned by the current user and no passphrase is used.
            download_folder (str): Path where the file will be saved.
            log_level (logging.LEVEL): log_level for logs and console

        Returns:
            int: 1 if download succeeded, 0 if failed.
        """
        with set_log_level(LOGGER, log_level):
            tmp_dir = None
            download_tmp_path = None
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
                if album_id is not None:
                    params["album_id"] = str(album_id)

                request_variants = [dict(params)]
                if album_passphrase:
                    request_with_passphrase = dict(params)
                    request_with_passphrase['passphrase'] = f'"{album_passphrase}"'
                    request_variants.append(request_with_passphrase)

                # Synology's browser download flow for Shared Space albums uses
                # `album_id` without passphrase. True shared-with-me albums may
                # still require passphrase, so we try the browser-like context
                # first and only then fall back to the passphrase variant.
                resp = None
                for request_params in request_variants:
                    prefer_post = album_scope in {"owned_shared_space", "shared_with_me"}
                    resp = self._request_entry_api(
                        url,
                        request_params,
                        headers=headers,
                        prefer_post=prefer_post,
                        stream=True,
                    )
                    if resp.status_code == 200:
                        break
                if resp.status_code != 200:
                    LOGGER.error(f"")
                    LOGGER.error(f"Failed to download asset '{asset_filename}' with ID [{asset_id}]. Status code: {resp.status_code}")
                    return 0

                content_type = str(resp.headers.get("Content-Type", "")).lower()
                content_disp = str(resp.headers.get("Content-Disposition", "")).lower()
                zip_by_headers = ("zip" in content_type) or (".zip" in content_disp)

                tmp_dir = os.path.join(download_folder, ".photomigrator_tmp")
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_name = f"{asset_id}_{uuid.uuid4().hex}.part"
                download_tmp_path = os.path.join(tmp_dir, tmp_name)

                first_bytes = b""
                bytes_written = 0
                with open(download_tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        if not first_bytes:
                            first_bytes = chunk[:4]
                        f.write(chunk)
                        bytes_written += len(chunk)

                if bytes_written <= 0:
                    LOGGER.error(f"Downloaded empty payload for asset '{asset_filename}' (ID [{asset_id}]).")
                    return 0

                is_zip_payload = zip_by_headers or first_bytes.startswith(b"PK\x03\x04")

                if is_zip_payload:
                    extracted_files = []
                    try:
                        with zipfile.ZipFile(download_tmp_path, "r") as zf:
                            for member in zf.infolist():
                                if member.is_dir():
                                    continue
                                member_name = os.path.basename(member.filename)
                                if not member_name:
                                    continue
                                extracted_path = os.path.join(download_folder, member_name)
                                with zf.open(member, "r") as src, open(extracted_path, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                os.utime(extracted_path, (asset_time, asset_time))
                                extracted_ext = os.path.splitext(member_name)[1].lower()
                                if extracted_ext in self.ALLOWED_MEDIA_EXTENSIONS:
                                    update_metadata(extracted_path, asset_datetime.strftime("%Y-%m-%d %H:%M:%S"), log_level=logging.ERROR)
                                extracted_files.append(extracted_path)

                        if not extracted_files:
                            LOGGER.error(f"ZIP payload detected for '{asset_filename}' but no files were extracted.")
                            return 0

                        # Keep backward compatibility for callers that expect file_path to exist.
                        if not os.path.exists(file_path):
                            requested_ext = os.path.splitext(asset_filename)[1].lower()
                            preferred = next((p for p in extracted_files if os.path.splitext(p)[1].lower() == requested_ext), extracted_files[0])
                            shutil.copy2(preferred, file_path)
                            os.utime(file_path, (asset_time, asset_time))

                        LOGGER.warning(f"Asset '{asset_filename}' downloaded as ZIP payload and extracted to {len(extracted_files)} file(s).")
                        LOGGER.debug(f"")
                        LOGGER.debug(f"Asset '{asset_filename}' downloaded and extracted at {download_folder}")
                        return 1
                    except zipfile.BadZipFile:
                        LOGGER.warning(f"ZIP-like payload detected for '{asset_filename}' but extraction failed. Keeping raw file.")

                os.replace(download_tmp_path, file_path)
                download_tmp_path = None

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
            finally:
                try:
                    if download_tmp_path and os.path.exists(download_tmp_path):
                        os.remove(download_tmp_path)
                except Exception:
                    pass
                try:
                    if tmp_dir and os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
                        os.rmdir(tmp_dir)
                except Exception:
                    pass
            


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
                        has_supported_files = any(
                            os.path.splitext(file)[-1].lower() in self.ALLOWED_EXTENSIONS
                            and not matches_any_pattern(file, effective_file_exclusions)
                            for file in os.listdir(dir_path)
                            if os.path.isfile(os.path.join(dir_path, file))
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

                        album_file_paths = [os.path.join(subpath, file) for file in os.listdir(subpath)]
                        for file_path in tqdm(
                            album_file_paths,
                            desc=f"{MSG_TAGS['INFO']}   Uploading '{album_name}' Assets",
                            unit=" assets",
                        ):
                            if not os.path.isfile(file_path):
                                continue
                            if matches_any_pattern(os.path.basename(file_path), effective_file_exclusions):
                                continue
                            ext = os.path.splitext(file_path)[-1].lower()
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
                            matched_album = None
                            preferred_name = album_name
                            if consolidate_similar_albums:
                                matched_album, reuse_plan = self.consolidate_reusable_album_group(
                                    album_name=album_name,
                                    existing_albums=existing_albums,
                                    log_level=log_level,
                                )
                                matched_name = (matched_album or {}).get("albumName", album_name) if matched_album else album_name
                                if matched_album or reuse_plan.get("similar_albums"):
                                    preferred_name = str(reuse_plan.get("preferred_album_name") or album_name)
                                if matched_album and matched_name != album_name:
                                    LOGGER.info(
                                        f"Reusing consolidated Synology album '{matched_name}' "
                                        f"for source album '{album_name}'. Preferred keeper name: '{preferred_name}'."
                                    )
                            else:
                                matched_album, _, _ = find_reusable_album_candidate(
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
                                            f"Reusing canonical Synology album '{preferred_name}' "
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
            effective_folder_exclusions = merge_exclusion_patterns(
                ARGS.get("exclude-folders", []),
                default_patterns=['@eaDir', '@Recycle', '.*'] + subfolders_exclusion,
            )
            effective_file_exclusions = merge_exclusion_patterns(
                ARGS.get("exclude-files", []),
                default_patterns=["SYNOFILE_THUMB*", "SYNOPHOTO_THUMB*", "SYNOVIDEO_THUMB*", "SYNOPHOTO_FILM*", "Thumbs.db", "ehthumbs.db", ".DS_Store", "._*"],
            )

            def collect_files(base, only_subs):
                files_list = []
                if only_subs:
                    for sub in only_subs:
                        sub_path = os.path.join(base, sub)
                        if not os.path.isdir(sub_path):
                            LOGGER.warning(f"Subfolder '{sub}' does not exist in '{base}'. Skipping.")
                            continue
                        for r, dirs, files in os.walk(sub_path):
                            dirs[:] = [d for d in dirs if not matches_any_pattern(d, effective_folder_exclusions)]
                            for f_ in files:
                                if matches_any_pattern(f_, effective_file_exclusions):
                                    continue
                                files_list.append(os.path.join(r, f_))
                else:
                    for r, dirs, files in os.walk(base):
                        dirs[:] = [d for d in dirs if not matches_any_pattern(d, effective_folder_exclusions)]
                        for f_ in files:
                            if matches_any_pattern(f_, effective_file_exclusions):
                                continue
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
                            LOGGER.debug(f"Duplicated Asset: {file_}. Asset ID: {asset_id} skipped")
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


    def push_all(self, input_folder, album_folders=None, remove_duplicates=False, log_level=None):
        """
        Uploads ALL photos/videos from input_folder into Synology Photos.
        Returns details about how many albums and assets were uploaded.

        Args:
            input_folder (str): Input folder
            album_folders (str): Albums folder
            remove_duplicates (bool): True to remove duplicates assets after upload all assets
            log_level (logging.LEVEL): log_level for logs and console

        Returns: (total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed)
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)

                total_duplicates_assets_removed = 0
                input_folder = os.path.realpath(input_folder)
                album_folders = convert_to_list(album_folders) if album_folders else []

                albums_folder_included = any(subf.lower() == 'albums' for subf in album_folders)
                if not albums_folder_included:
                    album_folders.append(f'{FOLDERNAME_ALBUMS}')

                LOGGER.info(f"")
                LOGGER.info(f"Uploading Assets and creating Albums into synology Photos from '{album_folders}' subfolders...")

                total_albums_uploaded, total_albums_skipped, total_assets_uploaded_within_albums, total_duplicates_assets_removed_1, total_dupplicated_assets_skipped_1 = self.push_albums(input_folder=input_folder, subfolders_inclusion=album_folders, remove_duplicates=False, log_level=logging.WARNING)

                LOGGER.info(f"")
                LOGGER.info(f"Uploading Assets without Albums creation into synology Photos from '{input_folder}' (excluding albums subfolders '{album_folders}')...")

                total_assets_uploaded_without_albums, total_dupplicated_assets_skipped_2, total_duplicates_assets_removed_2 = self.push_no_albums(input_folder=input_folder, subfolders_exclusion=album_folders, log_level=logging.WARNING)

                total_duplicates_assets_removed = total_duplicates_assets_removed_1 + total_duplicates_assets_removed_2
                total_dupplicated_assets_skipped = total_dupplicated_assets_skipped_1 + total_dupplicated_assets_skipped_2
                total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums

                if remove_duplicates:
                    LOGGER.info(f"Removing Duplicates Assets...")
                    total_duplicates_assets_removed += self.remove_duplicates_assets(log_level=logging.WARNING)

            except Exception as e:
                LOGGER.error(f"Exception while uploading ALL assets into Synology Photos. {e}")

            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, total_duplicates_assets_removed, total_dupplicated_assets_skipped


    def pull_albums(self, album_names='ALL', output_folder='Downloads_Synology', log_level=logging.WARNING):
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
            try:
                self.login(log_level=log_level)

                albums_downloaded = 0
                assets_downloaded = 0

                output_folder = os.path.join(output_folder, f'{FOLDERNAME_ALBUMS}')
                os.makedirs(output_folder, exist_ok=True)

                if isinstance(album_names, str):
                    album_names = [album_names]

                # Check if there is some filter applied
                filters_provided = has_any_filter()

                all_albums = self.get_albums_including_shared_with_user(filter_assets=filters_provided, log_level=log_level)

                if not all_albums:
                    return 0, 0

                if 'ALL' in [x.strip().upper() for x in album_names]:
                    albums_to_download = all_albums
                    LOGGER.info(f"ALL albums ({len(all_albums)}) will be downloaded...")
                else:
                    # Flatten user-specified album patterns
                    pattern_list = []
                    for item in album_names:
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
                    album = self.ensure_shared_album_access(album, log_level=log_level)
                    album = self._hydrate_album_payload(album)
                    album = self._ensure_album_runtime_details(album, log_level=log_level)
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    album_passphrase = album.get("passphrase")
                    album_scope = album.get("_synology_album_scope")
                    is_shared = self.is_shared_with_me_album(album)
                    LOGGER.info(f"Processing album: '{album_name}' (ID: {album_id})")
                    if is_shared:
                        album_assets = self.get_all_assets_from_album_shared(
                            album_id,
                            album_name,
                            album_passphrase=album_passphrase,
                            album_scope=album_scope,
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    else:
                        album_assets = self.get_all_assets_from_album(
                            album_id,
                            album_name,
                            album_scope=album_scope,
                            album_expected_count=album.get("item_count"),
                            log_level=log_level,
                        )
                    LOGGER.info(f"Number of album_assets in the album '{album_name}': {len(album_assets)}")
                    if not album_assets:
                        LOGGER.warning(f"No album_assets to download in the album '{album_name}'.")
                        continue

                    album_folder_name = f'{album_name}'
                    album_folder_path = os.path.join(output_folder, album_folder_name)

                    for asset in tqdm(
                        album_assets,
                        desc=f"{MSG_TAGS['INFO']}   Downloading '{album_name}' Assets",
                        unit=" assets",
                    ):
                        asset_id = asset.get('id')
                        asset_time = asset.get('time')
                        asset_filename = asset.get('filename')
                        # Download
                        assets_downloaded += self.pull_asset(
                            asset_id=asset_id,
                            asset_filename=asset_filename,
                            asset_time=asset_time,
                            download_folder=album_folder_path,
                            album_passphrase=album_passphrase if is_shared else None,
                            album_id=album_id,
                            album_scope=album_scope,
                            log_level=logging.INFO,
                        )

                LOGGER.info(f"Album(s) downloaded successfully. You can find them in '{output_folder}'")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while uploading ALL assets into Synology Photos. {e}")
                return 0,0
            
            return albums_downloaded, assets_downloaded


    def pull_no_albums(self, output_folder='Downloads_Synology', log_level=logging.WARNING):
        """
        Downloads assets not associated to any album from Synology Photos into output_folder/<NO_ALBUMS_FOLDER>/.
        Assets are stored directly using year/month subfolders.

        Args:
            output_folder (str): The output folder where the album assets will be downloaded.
            log_level (logging.LEVEL): log_level for logs and console

        Returns total_assets_downloaded or 0 if no assets are downloaded
        """
        with set_log_level(LOGGER, log_level):
            try:
                self.login(log_level=log_level)
                total_assets_downloaded = 0

                assets_without_albums = self.get_all_assets_without_albums(log_level=logging.INFO)
                output_folder = os.path.join(output_folder, FOLDERNAME_NO_ALBUMS)
                os.makedirs(output_folder, exist_ok=True)

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
                    target_folder = os.path.join(output_folder, year_str, month_str)
                    os.makedirs(target_folder, exist_ok=True)


                    total_assets_downloaded += self.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_time, download_folder=target_folder, log_level=logging.INFO)

                LOGGER.info(f"Album(s) downloaded successfully. You can find them in '{output_folder}'")
                # self.logout(log_level=log_level)
            except Exception as e:
                LOGGER.error(f"Exception while downloading No-Albums assets from Synology Photos. {e}")
            
            return total_assets_downloaded


    def pull_all(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
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
                total_albums_downloaded, total_assets_downloaded_within_albums = self.pull_albums(album_names='ALL', output_folder=output_folder, log_level=logging.WARNING)
                total_assets_downloaded_without_albums = self.pull_no_albums(output_folder=output_folder, log_level=logging.WARNING)
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
            matched_album_names = []
            for album in tqdm(albums, desc=f"{MSG_TAGS['INFO']}Searching for albums to rename", unit="albums"):
                album_date = album.get("create_time")
                if is_date_outside_range(album_date):
                    continue
                album_id = album.get("id")
                album_name = album.get("albumName", "")
                if match_pattern(album_name, pattern):
                    matched_album_names.append(album_name)
                    new_name = replace_pattern(album_name, pattern=pattern, pattern_to_replace=pattern_to_replace)
                    if not new_name or new_name == album_name:
                        continue
                    albums_to_rename[album_id] = {
                        "album_name": album_name,
                        "new_name": new_name,
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

    def remove_albums_by_name(self, pattern, remove_album_assets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Synology Photos whose name matches the provided pattern.

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
                        self.remove_assets(album_assets_ids, log_level=logging.WARNING)
                        total_removed_assets += len(album_assets_ids)
                if self.remove_album(album_id, album_name):
                    LOGGER.info(f"Album '{album_name}' (ID={album_id}) removed.")
                    total_removed_albums += 1

            LOGGER.info(f"Removed {total_removed_albums} albums whose names matched the provided pattern.")
            LOGGER.info(f"Removed {total_removed_assets} assets from those removed albums.")
            # self.logout(log_level=log_level)
            return total_removed_albums, total_removed_assets


    def remove_all_albums(self, remove_album_assets=False, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes all albums in Synology Photos, and optionally all their associated assets.

        If request_user_confirmation is True, displays the albums to be deleted and asks for user confirmation before proceeding.

        Args:
            remove_album_assets (bool): Whether to remove all assets inside the albums.
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

                    if remove_album_assets:
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
                if remove_album_assets:
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

    # Example: push_all()
    print("\n=== EXAMPLE: push_all() ===")
    # input_folder = "/volume1/homes/jaimetur/PhotoMigrator/Upload_folder_for_testing"     # For Linux (NAS)
    input_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing"                # For Windows
    syno.push_all(input_folder)

    # Example: pull_albums()
    print("\n=== EXAMPLE: pull_albums() ===")
    download_folder = r"r:\jaimetur\PhotoMigrator\Download_folder_for_testing"
    total_albums, total_assets = syno.pull_albums(album_names='ALL', output_folder=download_folder)
    print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums}.\n")

    # Example: pull_no_albums()
    print("\n=== EXAMPLE: pull_no_albums() ===")
    download_folder = r"r:\jaimetur\PhotoMigrator\Download_folder_for_testing"
    total = syno.pull_no_albums(output_folder=download_folder)
    print(f"[RESULT] A total of {total} assets have been downloaded.\n")

    # Example: pull_all
    print("=== EXAMPLE: pull_all() ===")
    total_struct = syno.pull_all(output_folder="Downloads_Synology")
    # print(f"[RESULT] Bulk download completed. Total assets: {total_struct}\n")

    # Example: remove_empty_folders()
    print("\n=== EXAMPLE: remove_empty_folders() ===")
    total = syno.remove_empty_folders()
    print(f"[RESULT] A total of {total} folders have been removed.\n")

    # logout()
    syno.logout()
