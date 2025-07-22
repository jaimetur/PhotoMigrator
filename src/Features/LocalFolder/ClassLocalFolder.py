# -*- coding: utf-8 -*-

import logging
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from Core.ClassFolderAnalyzer import FolderAnalyzer
from Core.CustomLogger import set_log_level
from Core.GlobalVariables import LOGGER, ARGS, MSG_TAGS, FOLDERNAME_NO_ALBUMS, CONFIGURATION_FILE, FOLDERNAME_ALBUMS
from Utils.DateUtils import parse_text_datetime_to_epoch
from Utils.StandaloneUtils import change_working_dir
from Utils.GeneralUtils import has_any_filter, confirm_continue, convert_to_list

"""
-------------------
ClassLocalFolder.py
-------------------
Python module with example functions to interact with Local Folder, including following functions:
  - Listing and managing albums
  - Listing, uploading, and downloading assets
  - Deleting empty or duplicate albums
  - Main functions for use in other modules:
     - delete_empty_albums()
     - delete_duplicates_albums()
     - upload_folder()
     - upload_albums()
     - download_albums()
     - pull_ALL()
"""

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassLocalFolder:
    def __init__(self, base_folder):
        """
        Initializes the class and sets up the base folder where albums and assets will be managed.

        Args:
            base_folder (str, Path): Path to the main directory where albums and assets will be stored.
        """
        self.base_folder = Path(base_folder)
        self.albums_folder = self.base_folder / f"{FOLDERNAME_ALBUMS}"
        self.shared_albums_folder = self.base_folder / f"{FOLDERNAME_ALBUMS}-shared"
        self.no_albums_folder = self.base_folder / FOLDERNAME_NO_ALBUMS

        # Ensure all required folders exist
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.albums_folder.mkdir(parents=True, exist_ok=True)
        self.shared_albums_folder.mkdir(parents=True, exist_ok=True)
        self.no_albums_folder.mkdir(parents=True, exist_ok=True)

        # Allowed extensions:
        self.ALLOWED_SIDECAR_EXTENSIONS = [".xmp", ".thm", ".pp3"]
        self.ALLOWED_METADATA_EXTENSIONS = [".json"]
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
        self.ALLOWED_EXTENSIONS = self.ALLOWED_MEDIA_EXTENSIONS + self.ALLOWED_SIDECAR_EXTENSIONS + self.ALLOWED_METADATA_EXTENSIONS

        # Definition of folder exclusion patterns
        self.FOLDER_EXCLUSION_PATTERNS = [
            r"@eaDir",  # Excludes the specific "@eaDir" folder
            r"\..+"  # Excludes any hidden folder (starting with ".")
        ]

        # Definition of file exclusion patterns
        self.FILE_EXCLUSION_PATTERNS = [
            r"SYNOFILE_THUMB.*"  # Excludes any file beginning with "SYNOFILE_THUMB"
        ]

        # Create a cache dictionary of albums_owned_by_user to save in memory all the albums owned by this user to avoid multiple calls to method get_albums_owned_by_user()
        self.albums_owned_by_user = {}

        # Create cache lists for future use
        self.all_assets_filtered = None
        self.assets_without_albums_filtered = None
        self.albums_assets_filtered = None

        # Get the values from the arguments (if exists)
        self.type = ARGS.get('filter-by-type', None)
        self.from_date = ARGS.get('filter-from-date', None)
        self.to_date = ARGS.get('filter-to-date', None)

        # Create the object analyzer from FolderAnalyzer Class
        self.analyzer = None

        self.CLIENT_NAME = f'Local Folder ({self.base_folder.name})'


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def _ensure_analyzer(self, metadata_json_file=None, step_name="", log_level=None):
        # Ensure FolderAnalyzer is initialized lazily
        with set_log_level(LOGGER, log_level):
            if not hasattr(self, 'analyzer') or self.analyzer is None:
                LOGGER.info(f"{step_name}Initializing analyzer for {self.base_folder}…")
                # Create the analyzer with the base folder path
                self.analyzer = FolderAnalyzer(
                    folder_path=str(self.base_folder),
                    logger=LOGGER,
                    step_name=step_name
                )
                if os.path.isfile(metadata_json_file):
                    self.analyzer.load_from_json(input_file=metadata_json_file, step_name=step_name)
                else:
                    self.analyzer.extract_dates(step_name=step_name)
                self.analyzer.save_to_json(output_file=f"automatic_migration_dates_metadata.json", step_name=step_name)

    def _determine_file_type(self, file):
        """
        Determines the type of the file based on its extension.

        Returns:
            str: 'image', 'video', 'metadata', 'sidecar', or 'unknown'.
        """
        ext = file.suffix.lower()
        if ext in self.ALLOWED_PHOTO_EXTENSIONS:
            return "image"
        elif ext in self.ALLOWED_VIDEO_EXTENSIONS:
            return "video"
        elif ext in self.ALLOWED_METADATA_EXTENSIONS:
            return "metadata"
        elif ext in self.ALLOWED_SIDECAR_EXTENSIONS:
            return "sidecar"
        return "unknown"


    def _get_selected_extensions(self, type):
        """
        Returns the allowed extensions based on the specified type.

        Args:
            type (str): Type of assets to filter. Options are 'all', 'photo', 'image', 'video',
                        'media', 'metadata', 'sidecar', 'unsupported'.

        Returns:
            set[str] or str: A set of allowed extensions, or "unsupported" for filtering unsupported files.
        """
        if type in ['photo', 'image']:
            return self.ALLOWED_PHOTO_EXTENSIONS
        elif type == 'video':
            return self.ALLOWED_VIDEO_EXTENSIONS
        elif type == 'media':
            return self.ALLOWED_MEDIA_EXTENSIONS
        elif type == 'metadata':
            return self.ALLOWED_METADATA_EXTENSIONS
        elif type == 'sidecar':
            return self.ALLOWED_SIDECAR_EXTENSIONS
        elif type == 'unsupported':
            return "unsupported"  # Special case for unsupported files
        else:  # 'all' or any other unrecognized value
            return self.ALLOWED_EXTENSIONS


    def _should_exclude(self, file_path):
        """
        Checks if a given file or folder should be excluded based on regex patterns.

        Args:
            file_path (Path): Path to the file or folder.

        Returns:
            bool: True if the file or folder should be excluded, False otherwise.
        """
        file_name = file_path.name
        # Check folder exclusion
        for pattern in self.FOLDER_EXCLUSION_PATTERNS:
            if any(re.fullmatch(pattern, part) for part in file_path.parts):
                return True
        # Check file exclusion
        for pattern in self.FILE_EXCLUSION_PATTERNS:
            if re.fullmatch(pattern, file_name):
                return True
        return False

    def get_takeout_assets_by_filters(self, type='all', log_level=None):
        return []  # Base class has no takeout, returns an empty list

    ###########################################################################
    #                           CLASS PROPERTIES GETS                         #
    ###########################################################################
    def get_client_name(self, log_level=None):
        """
        Returns the name of the client.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            str: The name of the client.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.debug(f"Fetching the client name.")
            return self.CLIENT_NAME


    ###########################################################################
    #                           CONFIGURATION READING                         #
    ###########################################################################
    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        """
        Reads a configuration file (not really used in local storage).

        Args:
            config_file (str): The path to the configuration file. Default is 'Config.ini'.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            dict: An empty dictionary, as config is not used locally.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Reading config file (Not applicable).")
            return {}


    ###########################################################################
    #                         AUTHENTICATION / LOGOUT                         #
    ###########################################################################
    def login(self, log_level=None):
        """
        Simulates a login operation. Always successful in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            bool: Always True for local usage.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Logging in (local storage).")
            return True

    def logout(self, log_level=None):
        """
        Simulates a logout operation. Always successful in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Logging out (local storage).")


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def get_supported_media_types(self, type='media', log_level=None):
        """
        Returns the supported media/sidecar extensions for local usage.

        Args:
            type (str): 'media', 'image', 'video', or 'sidecar' to filter. Default 'media'.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[str]: The list of supported extensions depending on 'type'.
        """
        with set_log_level(LOGGER, log_level):
            if type.lower() == 'image':
                return self.ALLOWED_PHOTO_EXTENSIONS
            elif type.lower() == 'video':
                return self.ALLOWED_VIDEO_EXTENSIONS
            elif type.lower() == 'sidecar':
                return self.ALLOWED_SIDECAR_EXTENSIONS
            else:
                # 'media' or anything else defaults to photo+video
                return self.ALLOWED_PHOTO_EXTENSIONS + self.ALLOWED_VIDEO_EXTENSIONS


    def get_user_id(self, log_level=None):
        """
        Returns a user ID, which is simply the base folder path in local usage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            str: The path of the base folder as the user ID.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Returning the user ID (base folder path).")
            return str(self.base_folder)


    def get_user_mail(self, log_level=None):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            return "no-applicable"


    ###########################################################################
    #                            ALBUMS FUNCTIONS                             #
    ###########################################################################
    def create_album(self, album_name, log_level=None):
        """
        Creates a new album (folder).

        Args:
            album_name (str): Name of the album to be created.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            bool: True if the album was created successfully, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Creating album '{album_name}'.")
            album_path = self.albums_folder / album_name
            album_path.mkdir(parents=True, exist_ok=True)
            return album_path


    def remove_album(self, album_id, album_name=None, log_level=None):
        """
        Removes an album (folder) if it exists.

        Args:
            album_id (str): Path to the album folder.
            album_name (str): (Optional) Name of the album, for logging only.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            bool: True if the album was removed successfully, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            album_path = Path(album_id)
            LOGGER.info(f"Removing album '{album_name or album_id}'.")
            if album_path.exists() and album_path.is_dir():
                shutil.rmtree(album_path)
                return True
            return False

    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        """
        Retrieves the list of owned albums.

        Args:
            filter_assets (bool): If True, only return albums with at least one asset.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Retrieving owned albums.")

            # Check if we already have cached results for this filter_assets value
            cache_key = f"owned_{filter_assets}"
            if cache_key in self.albums_owned_by_user:
                LOGGER.debug("Returning cached owned albums.")
                return self.albums_owned_by_user[cache_key]

            # Initialize the analyzer if needed
            self._ensure_analyzer(log_level=log_level)

            # Discover non-empty album names via analyzer.file_list
            album_names = set()
            base = Path(self.albums_folder.resolve())
            for p in self.analyzer.file_list:
                file = Path(p)
                try:
                    # only process files that live under the Albums folder
                    rel = file.relative_to(base)
                except ValueError:
                    # file is not inside base → skip
                    continue
                # the first component of the relative path is the album folder name
                album_names.add(rel.parts[0])

            # Build the list of albums
            albums = [
                {"id": str((self.albums_folder / name).resolve()), "albumName": name}
                for name in album_names
            ]

            # If not filtering by assets, cache and return immediately
            if not filter_assets:
                self.albums_owned_by_user[cache_key] = albums
                return albums

            # Apply the original asset-presence filter
            albums_filtered = []
            for album in albums:
                album_id = album["id"]
                album_name = album["albumName"]
                album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                if len(album_assets) > 0:
                    albums_filtered.append(album)

            LOGGER.info(f"Found {len(albums_filtered)} owned albums.")

            # Cache the result for future calls
            self.albums_owned_by_user[cache_key] = albums_filtered
            return albums_filtered

    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        """
        Retrieves both owned and shared albums.

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        # TODO: Apply Filters to this method.
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.info(f"Retrieving owned and shared albums.")
                # Initialize the analyzer if needed
                self._ensure_analyzer(log_level=log_level)

                # Discover non-empty album names via analyzer.file_list
                owned_names = set()
                shared_names = set()
                base_owned = Path(self.albums_folder.resolve())
                base_shared = Path(self.shared_albums_folder.resolve())

                for p in self.analyzer.file_list:
                    file_path = Path(p)
                    # owned
                    try:
                        rel = file_path.relative_to(base_owned)
                        # rel.parts[0] es el nombre del álbum
                        owned_names.add(rel.parts[0])
                        continue
                    except ValueError:
                        pass
                    # shared
                    try:
                        rel = file_path.relative_to(base_shared)
                        shared_names.add(rel.parts[0])
                    except ValueError:
                        pass

                albums = [
                    {"id": str((self.albums_folder / name).resolve()), "albumName": name}
                    for name in owned_names
                ]
                shared_albums = [
                    {"id": str((self.shared_albums_folder / name).resolve()), "albumName": name}
                    for name in shared_names
                ]

                all_albums = albums + shared_albums
                albums_filtered = []
                for album in all_albums:
                    album_id = album["id"]
                    album_name = album["albumName"]
                    album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                    if len(album_assets) > 0:
                        albums_filtered.append(album)
                LOGGER.info(f"Found {len(albums_filtered)} albums in total (owned + shared).")
            except Exception as e:
                LOGGER.error(f"Failed to get albums (owned + shared): {str(e)}")

            return albums_filtered

    def get_album_assets_size(self, album_id, type='all', log_level=None):
        """
        Total size (bytes) of assets in an album, with global and local filters.
        """
        with set_log_level(LOGGER, log_level):
            self._ensure_analyzer(log_level=log_level)
            album_path = Path(album_id)
            if not album_path.is_dir():
                LOGGER.warning(f"Album path '{album_id}' is invalid.")
                return 0

            prefix = str(album_path.resolve().as_posix())
            if type == 'all' and not self.type and not self.from_date and not self.to_date:
                return self.analyzer.folder_sizes.get(prefix, 0)

            sel_ext_local = self._get_selected_extensions(type)
            sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
            epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
            epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)

            total = 0
            for p in self.analyzer.file_list:
                file = Path(p)
                try:
                    file.relative_to(prefix)
                except ValueError:
                    continue
                size = self.analyzer.file_sizes.get(p)
                if size is None:
                    continue

                ext = Path(p).suffix.lower()
                # filters same as above…
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue
                if sel_ext_global:
                    if sel_ext_global == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in sel_ext_global:
                        continue

                file_date = self.analyzer.get_date(p)
                if file_date is None:
                    continue
                ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
                if ts < epoch_start or ts > epoch_end:
                    continue

                # accumulate size
                try:
                    total += size
                except (OSError, IOError) as e:
                    LOGGER.warning(f"Error summing size of {p}: {e}")

            return total

    def get_album_assets_count(self, album_id, log_level=None):
        """
        Gets the number of assets in an album.

        Args:
            album_id (str): Path to the album folder.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of assets in the album.
        """
        with set_log_level(LOGGER, log_level):
            return len(self.get_all_assets_from_album(album_id, type='all', log_level=log_level))


    def album_exists(self, album_name, log_level=None):
        """
        Checks if an album with the given name exists in the 'Albums' folder.

        Args:
            album_name (str): Name of the album to check.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            tuple: (bool, str or None) -> (exists, album_path_if_exists)
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Checking if album '{album_name}' exists.")
            for album in self.get_albums_owned_by_user(filter_assets=False, log_level=log_level):
                if album_name == album["albumName"]:
                    return True, album["id"]
            return False, None


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
                    assets_filtered = self.get_assets_by_filters(log_level=log_level) or []
                    self.all_assets_filtered = assets_filtered
                if any(asset.get('id') == asset_id for asset in self.all_assets_filtered):
                    filtered.append(asset)
            return filtered

    def filter_assets_old(self, assets, log_level=None):
        """
        Filters a list of assets based on user-defined criteria such as date range,
        country, city, and asset type. Filter parameters are retrieved from the global ARGS dictionary.

        The filtering steps are applied in the following order:
        1. By date range (from-date, to-date)
        2. By asset_type

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
                return filtered_assets
            except Exception as e:
                LOGGER.error(f"Exception while filtering Assets from Local Folder. {e}")

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


    ###########################################################################
    #                        ASSETS (PHOTOS/VIDEOS)                           #
    ###########################################################################
    def get_assets_by_filters(self, type='all', log_level=logging.WARNING):
        """
        Retrieves all assets from the base_folder, filtering by global date/type
        and by local type (parameter 'type').
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Retrieving {type} assets…")

            if self.all_assets_filtered is not None and not self.from_date and not self.to_date and not self.type:
                return self.all_assets_filtered

            sel_ext_local = self._get_selected_extensions(type)
            sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
            epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
            epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)

            self._ensure_analyzer(log_level=log_level)
            result = []

            for p in self.analyzer.file_list:
                f = Path(p)
                if not f.is_file():
                    continue
                if self._should_exclude(f):
                    continue

                ext = f.suffix.lower()
                # local filter
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue
                # global filter
                if sel_ext_global:
                    if sel_ext_global == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in sel_ext_global:
                        continue

                # global date filter
                file_date = self.analyzer.get_date(p)
                if file_date is None:
                    continue
                ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
                if ts < epoch_start or ts > epoch_end:
                    continue

                # OK: asset metadata
                try:
                    mtime = f.stat().st_mtime
                except (OSError, IOError) as e:
                    LOGGER.warning(f"Could not read mtime of {f}: {e}")
                    continue

                result.append({
                    "id": str(f),
                    "time": mtime,
                    "filename": f.name,
                    "filepath": str(f),
                    "type": self._determine_file_type(f),
                })

            LOGGER.info(f"Found {len(result)} assets of type '{type}'.")
            self.all_assets_filtered = result
            return result

    def get_all_assets_from_album(self, album_id, album_name=None, type='all', log_level=logging.WARNING):
        """
        Lists assets in a specific album, applying both global and local type/date filters.
        """
        with set_log_level(LOGGER, log_level):
            album_path = Path(album_id)
            if not album_path.is_dir():
                LOGGER.warning(f"Album '{album_id}' does not exist.")
                return []

            sel_ext_local = self._get_selected_extensions(type)
            sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
            epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
            epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)
            prefix = album_path.resolve()

            self._ensure_analyzer(log_level=log_level)
            assets = []

            for p in self.analyzer.file_list:
                filepath = Path(p)
                try:
                    filepath.relative_to(prefix)
                except ValueError:
                    continue
                if not (filepath.is_file() or filepath.is_symlink()):
                    continue
                if self._should_exclude(filepath):
                    continue

                ext = filepath.suffix.lower()
                # local filter
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue
                # global filter
                if sel_ext_global:
                    if sel_ext_global == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in sel_ext_global:
                        continue

                # global date filter (resolve symlinks to get real metadata)
                fs_path = Path(p)
                if fs_path.is_symlink():
                    # resolve the link to the real file
                    target = fs_path.resolve()
                    file_date = self.analyzer.get_date(str(target))
                else:
                    file_date = self.analyzer.get_date(p)

                if file_date is None:
                    continue
                ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
                if ts < epoch_start or ts > epoch_end:
                    continue

                try:
                    mtime = filepath.stat().st_mtime
                except (OSError, IOError) as e:
                    LOGGER.warning(f"Unable to read mtime from {filepath}: {e}")
                    continue

                assets.append({
                    "id": str(filepath),
                    "time": mtime,
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "type": self._determine_file_type(filepath),
                })

            LOGGER.debug(f"{len(assets)} assets in album '{album_id}'.")
            return assets

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type='all', album_passphrase=None, log_level=logging.WARNING):
        """
        Lists the assets within a given shared album, with optional filtering by file type.

        Args:
            album_id (str): Path to the shared album folder.
            album_name (str, optional): Name of the album for logging.
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media',
                        'metadata', 'sidecar', 'unsupported'.
            album_passphrase (str): Shared album passphrase (no‐op for local).
            log_level (int): Logging level.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Modification timestamp.
                        - 'filename': File name.
                        - 'filepath': Absolute path.
                        - 'type': 'image', 'video', etc.
        """
        # TODO: This method is just a copy of get_all_assets_from_album. Change to filter only shared albums

        with set_log_level(LOGGER, log_level):
            album_path = Path(album_id)
            if not album_path.is_dir():
                LOGGER.warning(f"Shared album '{album_id}' does not exist.")
                return []

            sel_ext_local  = self._get_selected_extensions(type)
            sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
            epoch_start    = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
            epoch_end      = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)
            prefix         = str(album_path.resolve())

            self._ensure_analyzer(log_level=log_level)
            assets = []

            for p in self.analyzer.file_list:
                filepath = Path(p)
                try:
                    filepath.relative_to(prefix)
                except ValueError:
                    continue
                if not (filepath.is_file() or filepath.is_symlink()):
                    continue
                if self._should_exclude(filepath):
                    continue

                ext = filepath.suffix.lower()
                # local and global filters identical to above…
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue
                if sel_ext_global:
                    if sel_ext_global == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in sel_ext_global:
                        continue

                # global date filter (resolve symlinks to get real metadata)
                fs_path = Path(p)
                if fs_path.is_symlink():
                    # resolve the link to the real file
                    target = fs_path.resolve()
                    file_date = self.analyzer.get_date(str(target))
                else:
                    file_date = self.analyzer.get_date(p)

                if file_date is None:
                    continue
                ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
                if ts < epoch_start or ts > epoch_end:
                    continue

                try:
                    mtime = filepath.stat().st_mtime
                except (OSError, IOError) as e:
                    LOGGER.warning(f"Could not read mtime of {filepath}: {e}")
                    continue

                assets.append({
                    "id": str(filepath),
                    "time": mtime,
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "type": self._determine_file_type(filepath),
                })

            LOGGER.debug(f"{len(assets)} assets in shared album '{album_id}'.")
            return assets

    def get_all_assets_without_albums(self, type='all', log_level=logging.WARNING):
        """
        Lists assets that are in self.base_folder but not in self.albums_folder
        or self.shared_albums_folder, with optional filtering by file type.

        Args:
            type (str): Type of assets to retrieve. Options are 'all', 'photo',
                        'image', 'video', 'media', 'metadata', 'sidecar', 'unsupported'.
            log_level (int): Logging level.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Retrieving {type} assets excluding albums, shared albums, and excluded patterns.")

            # Cache check (same as before)
            if self.assets_without_albums_filtered is not None:
                return self.assets_without_albums_filtered

            albums_folder = self.albums_folder.resolve()
            shared_albums_folder = self.shared_albums_folder.resolve()
            selected_type_extensions = self._get_selected_extensions(type)

            # Initialize the analyzer only once
            self._ensure_analyzer(log_level=log_level)

            assets = []
            for p in self.analyzer.file_list:
                f = Path(p)
                # Only regular files
                if not f.is_file():
                    continue
                # Pattern exclusion
                if self._should_exclude(f):
                    continue
                # Discard anything inside Albums or Shared
                try:
                    f.relative_to(albums_folder)
                    continue
                except ValueError:
                    pass
                try:
                    f.relative_to(shared_albums_folder)
                    continue
                except ValueError:
                    pass

                ext = f.suffix.lower()
                # Local filter by type (param 'type')
                if selected_type_extensions == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif selected_type_extensions is not None and ext not in selected_type_extensions:
                    continue

                assets.append({
                    "id": str(f),
                    "time": f.stat().st_mtime,
                    "filename": f.name,
                    "filepath": str(f),
                    "type": self._determine_file_type(f),
                })

            # Apply global filter (self.type, self.from_date, self.to_date)
            assets_without_albums = self.filter_assets(assets=assets, log_level=log_level)

            # Rest of takeouts as before
            takeout_metadata = self.get_takeout_assets_by_filters(type='metadata', log_level=log_level)
            takeout_sidecar = self.get_takeout_assets_by_filters(type='sidecar', log_level=log_level)
            takeout_unsupported = self.get_takeout_assets_by_filters(type='unsupported', log_level=log_level)

            LOGGER.info(f"Found {len(assets_without_albums)} assets of type '{type}' in No-Album folders.")
            all_assets = assets_without_albums + takeout_metadata + takeout_sidecar + takeout_unsupported

            # Cache for subsequent calls
            self.assets_without_albums_filtered = all_assets
            return all_assets

    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[dict]: Merged assets from all albums.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Gathering all albums' assets.")
            # If albums_assets is already cached, return it
            if self.albums_assets_filtered is not None:
                return self.albums_assets_filtered

            combined_assets = []
            all_albums = self.get_albums_including_shared_with_user(filter_assets=True, log_level=log_level)
            for album in all_albums:
                album_id = album["id"]
                combined_assets.extend(self.get_all_assets_from_album(album_id, log_level))
            self.albums_assets_filtered = combined_assets  # Cache albums_assets for future use
            return combined_assets


    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None):
        """
        Adds (links) assets to an album using relative symbolic links. If symlink creation fails, copies the file instead.

        Args:
            album_id (str): Path to the album folder.
            asset_ids (list[str]): List of asset file paths to add.
            album_name (str): (Optional) name of the album, for logging only.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of assets added to the album.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Adding assets to album: {album_name or album_id}")
            album_path = Path(album_id)
            album_path.mkdir(parents=True, exist_ok=True)
            count_added = 0
            asset_ids = convert_to_list(asset_ids)

            for asset in asset_ids:
                asset_path = Path(asset)
                if asset_path.exists() and asset_path.is_file():
                    symlink_path = album_path / asset_path.name

                    if not symlink_path.exists():
                        try:
                            relative_path = os.path.relpath(asset_path, start=symlink_path.parent)
                            symlink_path.symlink_to(relative_path)
                            LOGGER.info(f"Created relative symlink: {symlink_path} -> {relative_path}")
                        except Exception as e:
                            LOGGER.warning(f"Error: {e}")
                            LOGGER.warning(f"Failed to create symlink {symlink_path}. Copying a duplicated copy of the file into Album folder instead.")
                            try:
                                shutil.copy2(asset_path, symlink_path)
                                LOGGER.info(f"Copied file: {symlink_path}")
                            except Exception as copy_error:
                                LOGGER.error(f"Failed to copy file {asset_path} to {symlink_path}. Error: {copy_error}")
                                continue
                        count_added += 1

            LOGGER.info(f"Added {count_added} asset(s) to album '{album_name or album_id}'.")
            return count_added

    def get_duplicates_assets(self, log_level=None):
        """
        Returns a list of duplicate assets found in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[list[str]]: Each element is a list of file paths considered duplicates.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Searching for duplicate assets in local storage.")
            # Ensure analyzer has built file_sizes cache
            self._ensure_analyzer(log_level=log_level)

            # Use the cached file_sizes from the analyzer to group by size
            size_map = {}
            for file_path, size in self.analyzer.file_sizes.items():
                # file_path is a posix string; keep grouping by its size
                size_map.setdefault(size, []).append(file_path)

            # Build list of groups where more than one file shares the same size
            duplicates = []
            for group in size_map.values():
                if len(group) > 1:
                    duplicates.append(group)

            LOGGER.info(f"Found {len(duplicates)} duplicate group(s).")
            return duplicates

    def remove_assets(self, asset_ids, log_level=None):
        """
        Removes the given asset(s) from local storage.

        Args:
            asset_ids (list[str]): List of absolute file paths to remove.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of assets removed.
        """
        with set_log_level(LOGGER, log_level):
            if isinstance(asset_ids, str):
                asset_ids = [asset_ids]
            count = 0
            for asset in asset_ids:
                asset_path = Path(asset)
                if asset_path.exists():
                    if asset_path.is_file():
                        asset_path.unlink()
                        count += 1
                    else:
                        LOGGER.warning(f"Skipped removing '{asset_path}' because it is not a file.")
                else:
                    LOGGER.warning(f"Asset path does not exist: {asset_path}")
            LOGGER.info(f"Removed {count} asset(s) from local storage.")
            return count

    def remove_duplicates_assets(self, log_level=None):
        """
        Removes duplicate assets in local storage, keeping only the first one found.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of duplicate assets removed.
        """
        with set_log_level(LOGGER, log_level):
            duplicates = self.get_duplicates_assets(log_level)
            to_remove = []
            for dup_group in duplicates:
                # keep the first, remove the rest
                to_remove.extend(dup_group[1:])
            count_removed = self.remove_assets(to_remove, log_level)
            LOGGER.info(f"Removed {count_removed} duplicate asset(s) from local storage.")
            return count_removed


    def push_asset(self, file_path, log_level=None):
        """
        Uploads (copies) a local file to the No-Albums directory following a year/month structure.

        Args:
            file_path (str): Local file path of the asset to upload.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            (str, bool): (asset_full_path, is_duplicated=False).
                         In local storage we do not automatically detect duplicates at this stage.
        """
        with set_log_level(LOGGER, log_level):
            src = Path(file_path)
            if not src.exists() or not src.is_file():
                LOGGER.warning(f"File '{file_path}' does not exist or is not a file.")
                return None, None

            mtime = src.stat().st_mtime
            dt_m = datetime.fromtimestamp(mtime)
            year = str(dt_m.year)
            month = str(dt_m.month).zfill(2)

            target_folder = self.no_albums_folder / year / month
            target_folder.mkdir(parents=True, exist_ok=True)

            dest = target_folder / src.name
            if os.path.isfile(dest):
                return str(dest), True
            else:
                shutil.copy2(src, dest)
                LOGGER.info(f"Uploaded asset '{file_path}' to '{dest}'.")
            return str(dest), False


    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_LocalFolder", album_passphrase=None, log_level=None):
        """
        Downloads (copies) an asset to a specified local folder, preserving the file's timestamp.

        Args:
            asset_id (str): The absolute path of the asset in local storage.
            asset_filename (str): The filename to use for the downloaded file.
            asset_time (float): The file's creation or modification timestamp.
            download_folder (str): Where to copy the file locally.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: 1 if download succeeded, 0 otherwise.
            :param album_passphrase:
        """
        with set_log_level(LOGGER, log_level):
            src = Path(asset_id)
            if not src.exists():
                LOGGER.warning(f"Asset '{asset_id}' does not exist.")
                return 0

            dest_dir = Path(download_folder)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / asset_filename
            shutil.copy2(src, dest)

            if asset_time:
                os.utime(dest, (asset_time, asset_time))

            LOGGER.info(f"Downloaded asset '{src}' to '{dest}'.")
            return 1


    def push_albums(self, input_folder, subfolders_exclusion=FOLDERNAME_NO_ALBUMS,
                    subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        """
        Recursively uploads each subfolder of 'input_folder' as an album,
        simulating local album creation.

        Args:
            input_folder (str): The local folder containing subfolders as albums.
            subfolders_exclusion (str or list[str]): Which subfolders to exclude.
            subfolders_inclusion (str or list[str]): Which subfolders to include, if any.
            remove_duplicates (bool): Whether to remove duplicates after upload.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            tuple: (albums_uploaded, albums_skipped, assets_uploaded, total_duplicates_removed, total_duplicates_skipped=0)
        """
        # (The concrete local-upload logic can be the same as what we defined earlier)
        pass


    def push_no_albums(self, input_folder, subfolders_exclusion=f'{FOLDERNAME_ALBUMS}',
                       subfolders_inclusion=None, remove_duplicates=True,
                       log_level=logging.WARNING):
        """
        Recursively uploads all compatible files from 'input_folder' to <NO_ALBUMS_FOLDER>,
        ignoring any subfolders named in 'subfolders_exclusion'.

        Returns:
            tuple: (total_assets_uploaded, total_duplicates_skipped=0, total_duplicates_removed)
        """
        # (Same as the previous local logic, adapted)
        pass


    def push_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        """
        Uploads all photos/videos from input_folder to local storage,
        dividing them between '<ALBUMS_FOLDER>' and '<NO_ALBUMS_FOLDER>'.

        Returns:
            tuple: (albums_uploaded, albums_skipped, total_assets_uploaded,
                    assets_in_albums, assets_in_no_albums, duplicates_removed, duplicates_skipped=0)
        """
        pass


    def pull_albums(self, albums_name='ALL', output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading albums by copying album folders to output_folder/Albums.

        Returns:
            tuple: (albums_downloaded, assets_downloaded)
        """
        # Check if there is some filter applied
        filters_provided = has_any_filter()
        pass


    def pull_no_albums(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading 'no albums' assets to output_folder/<NO_ALBUMS_FOLDER>, organizing by year/month.

        Returns:
            int: Number of assets downloaded.
        """
        pass


    def pull_ALL(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading all albums and no-albums assets to output_folder.

        Returns:
            tuple: (total_albums_downloaded, total_assets_downloaded,
                    total_assets_in_albums, total_assets_no_albums).
        """
        pass

    def remove_empty_folders(self, log_level=None):
        """
        Recursively removes all empty folders in the entire base folder structure.

        Returns:
            int: The number of empty folders removed.
        """
        with set_log_level(LOGGER, log_level):
            if not self.base_folder.exists():
                LOGGER.warning(f"WARN    : Base folder does not exist: {self.base_folder}")
                return 0

            LOGGER.info(f"Looking for empty folders in '{self.base_folder}'...")
            # Initialize the analyzer if necessary
            self._ensure_analyzer(log_level=log_level)

            # Folder → contains files?
            occupied = set(Path(p).parent.resolve() for p in self.analyzer.file_list)
            removed = 0

            for folder in sorted(self.base_folder.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if folder.is_dir() and folder not in occupied:
                    try:
                        folder.rmdir()
                        removed += 1
                        LOGGER.info(f"Removed empty folder: {folder}")
                    except Exception as e:
                        LOGGER.warning(f"WARN    : Could not remove folder '{folder}': {e}")

            LOGGER.info(f"Removed {removed} empty folders.")
            return removed

    def remove_all_albums(self, log_level=None):
        """
        Removes all album folders. If removeAlbumsAssets=True, also removes files inside them.

        Returns:
            tuple(int, int): (#albums_removed, #assets_removed_if_requested).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Removing all albums.")

            for album in self.albums_folder.iterdir():
                if album.is_dir():
                    shutil.rmtree(album)

            LOGGER.info(f"All albums have been removed.")
            return True


    def remove_empty_albums(self, log_level=None):
        """
        Removes all empty album folders.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Removing empty albums.")

            empty_albums = [p for p in self.albums_folder.iterdir() if p.is_dir() and not any(p.iterdir())]
            for album in empty_albums:
                shutil.rmtree(album)

            LOGGER.info(f"Removed {len(empty_albums)} empty albums.")
            return True

    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        """
        Removes exact duplicate albums in local folders.

        Duplicates are folders with the same name and same total size (sum of all files).
        The function keeps one folder (the first found) and removes the rest.
        If request_user_confirmation is True, displays the folders to be deleted and asks for user confirmation.

        Args:
            request_user_confirmation (bool): Whether to ask for confirmation before deleting duplicates.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            int: The number of duplicate albums removed.
        """
        with set_log_level(LOGGER, log_level):
            from collections import defaultdict

            if not self.albums_folder.exists():
                LOGGER.warning(f"WARN    : Albums folder does not exist: {self.albums_folder}")
                return 0

            LOGGER.info(f"Looking for exact duplicate albums in local folders...")
            # Initialize the analyzer if needed
            self._ensure_analyzer(log_level=log_level)

            duplicates_map = defaultdict(list)
            for folder in self.albums_folder.glob("*"):
                if folder.is_dir():
                    album_name = folder.name
                    key = str(folder.resolve())
                    total_size = self.analyzer.folder_sizes.get(key, 0)
                    duplicates_map[(album_name, total_size)].append(folder)

            folders_to_remove = []
            for (album_name, total_size), group in duplicates_map.items():
                if len(group) > 1:
                    keeper = group[0]
                    LOGGER.info(f"Keeping folder '{keeper}' with size {total_size} bytes.")
                    for dup_folder in group[1:]:
                        folders_to_remove.append((album_name, total_size, dup_folder))

            if not folders_to_remove:
                LOGGER.info(f"No exact duplicate albums found.")
                return 0

            LOGGER.info(f"Folders marked for deletion:")
            for album_name, total_size, dup_folder in folders_to_remove:
                print(f"  '{album_name}' - Size: {total_size} bytes -> {dup_folder}")
            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                return 0

            total_removed = 0
            for album_name, total_size, dup_folder in folders_to_remove:
                try:
                    shutil.rmtree(dup_folder)
                    LOGGER.info(f"Removed duplicate folder: {dup_folder}")
                    total_removed += 1
                except Exception as e:
                    LOGGER.error(f"Failed to remove folder '{dup_folder}': {e}")

            LOGGER.info(f"Removed {total_removed} exact duplicate folders.")
            return total_removed

    def merge_duplicates_albums(self, strategy='count', request_user_confirmation=True, log_level=logging.WARNING):
        """
        Merges all duplicate albums in local folders.

        Duplicates are folders with the same name.
        The function keeps the folder with the most files or the largest total size (depending on strategy),
        moves all files from the duplicates into it, and deletes the duplicate folders.
        Before merging, it displays the planned operations and asks for user confirmation if requested.

        Args:
            strategy (str): 'count' to keep the album with the most files, 'size' to keep the album with the largest size.
            request_user_confirmation (bool): Whether to ask for confirmation before merging.
            log_level (logging.LEVEL): The log level for logging and console output.

        Returns:
            int: The number of duplicate folders deleted.
        """
        with set_log_level(LOGGER, log_level):
            from collections import defaultdict

            if not self.albums_folder.exists():
                LOGGER.warning(f"Albums folder does not exist: {self.albums_folder}")
                return 0

            LOGGER.info(f"Searching for duplicate albums in local folders...")
            # Initialize the analyzer if needed
            self._ensure_analyzer(log_level=log_level)

            # Group albums by name using in-memory data
            albums_by_name = defaultdict(list)
            for folder in self.albums_folder.glob("*"):
                if folder.is_dir():
                    album_name = folder.name
                    prefix = str(folder.resolve())
                    file_count = 0
                    for p in self.analyzer.file_list:
                        file = Path(p)
                        try:
                            file.relative_to(prefix)
                        except ValueError:
                            continue
                        if file.is_file():
                            file_count += 1
                    size = self.analyzer.folder_sizes.get(prefix, 0)
                    albums_by_name[album_name].append({
                        "path": folder,
                        "count": file_count,
                        "size": size
                    })

            merge_plan = []
            for album_name, group in albums_by_name.items():
                if len(group) <= 1:
                    continue
                if strategy == 'size':
                    keeper = sorted(group, key=lambda x: x['size'], reverse=True)[0]
                else:
                    keeper = sorted(group, key=lambda x: x['count'], reverse=True)[0]
                duplicates = [item["path"] for item in group if item["path"] != keeper["path"]]
                merge_plan.append({
                    "album_name": album_name,
                    "keeper_path": keeper["path"],
                    "duplicates": duplicates
                })

            if not merge_plan:
                LOGGER.info(f"No duplicate albums found.")
                return 0

            LOGGER.info(f"Albums to be merged:")
            for item in merge_plan:
                LOGGER.info(f"\nAlbum: '{item['album_name']}'")
                LOGGER.info(f"  Keeper: {item['keeper_path']}")
                for dup in item["duplicates"]:
                    LOGGER.info(f"  Duplicate to merge and remove: {dup}")

            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                return 0

            total_removed = 0
            for item in merge_plan:
                keeper_path = item["keeper_path"]
                for dup_path in item["duplicates"]:
                    for f in self.analyzer.file_list:
                        if f.startswith(str(dup_path.resolve()) + os.sep):
                            file = Path(f)
                            if file.is_file():
                                rel = file.relative_to(dup_path)
                                target = keeper_path / rel
                                target.parent.mkdir(parents=True, exist_ok=True)
                                if not target.exists():
                                    file.rename(target)
                                else:
                                    LOGGER.warning(f"Skipped moving '{file}' as it already exists at destination.")
                    try:
                        dup_path.rmdir()
                        total_removed += 1
                        LOGGER.info(f"Removed duplicate folder: {dup_path}")
                    except OSError:
                        shutil.rmtree(dup_path)
                        total_removed += 1
                        LOGGER.info(f"Removed duplicate folder and its contents: {dup_path}")

            LOGGER.info(f"Removed {total_removed} duplicate folders.")
            return total_removed

    def remove_orphan_assets(self, user_confirmation=True, log_level=logging.WARNING):
        """
        Removes orphan assets in local storage.

        Args:
            user_confirmation (bool): If True, request user confirmation. Not actually implemented locally.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of orphan assets removed (always 0 if not implemented).
        """
        pass


    ###########################################################################
    #                     REMOVE ALL ASSETS / ALL ALBUMS                      #
    ###########################################################################
    def remove_all_assets(self, log_level=logging.WARNING):
        """
        Removes all assets from local storage (both in <ALBUMS_FOLDER> and <NO_ALBUMS_FOLDER>).

        Returns:
            bool: True if success.
        """
        pass

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
    localFolder = ClassLocalFolder()

    # 0) Read configuration and log in
    localFolder.read_config_file(CONFIGURATION_FILE)
    localFolder.login()

    # 1) Example: Remove empty albums
    print("\n=== EXAMPLE: remove_empty_albums() ===")
    removed = localFolder.remove_empty_albums(log_level=logging.DEBUG)
    print(f"[RESULT] Empty albums removed: {removed}")

    # 2) Example: Remove duplicate albums
    print("\n=== EXAMPLE: remove_duplicates_albums() ===")
    duplicates = localFolder.remove_duplicates_albums(log_level=logging.DEBUG)
    print(f"[RESULT] Duplicate albums removed: {duplicates}")

    # 3) Example: Upload files WITHOUT assigning them to an album, from 'r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\No-Albums'
    print("\n=== EXAMPLE: push_no_albums() ===")
    big_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\No-Albums"
    localFolder.push_no_albums(big_folder, log_level=logging.DEBUG)

    # 4) Example: Create albums from subfolders in 'r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\Albums'
    print("\n=== EXAMPLE: push_albums() ===")
    input_albums_folder = r"r:\jaimetur\PhotoMigrator\Upload_folder_for_testing\Albums"
    localFolder.push_albums(input_albums_folder, log_level=logging.DEBUG)

    # 5) Example: Download all photos from ALL albums
    print("\n=== EXAMPLE: pull_albums() ===")
    # total = pull_albums('ALL', output_folder="Downloads_Immich")
    total_albums, total_assets = localFolder.pull_albums("1994 - Recuerdos", output_folder="Downloads_Immich", log_level=logging.DEBUG)
    print(f"[RESULT] A total of {total_assets} assets have been downloaded from {total_albums} different albbums.")

    # 6) Example: Download everything in the structure /Albums/<albumName>/ + /<NO_ALBUMS_FOLDER>/yyyy/mm
    print("\n=== EXAMPLE: pull_ALL() ===")
    # total_struct = pull_ALL(output_folder="Downloads_Immich")
    total_albums_downloaded, total_assets_downloaded = localFolder.pull_ALL(output_folder="Downloads_Immich", log_level=logging.DEBUG)
    print(f"[RESULT] Bulk download completed. \nTotal albums: {total_albums_downloaded}\nTotal assets: {total_assets_downloaded}.")

    # 8) Example: Remove ALL Assets
    localFolder.remove_all_assets(log_level=logging.DEBUG)

    # 9) Example: Remove ALL Assets
    localFolder.remove_all_albums(log_level=logging.DEBUG)

    # 10) Local logout
    localFolder.logout()