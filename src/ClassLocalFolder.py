# -*- coding: utf-8 -*-

import os
import shutil
import logging
import re
import Utils
from Utils import parse_text_datetime_to_epoch, match_pattern, replace_pattern, has_any_filter, is_date_outside_range
from datetime import datetime
import time
from pathlib import Path

# We also keep references to your custom logger context manager and utility functions:
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER, ARGS
import GlobalVariables as GV

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
        self.albums_folder = self.base_folder / "Albums"
        self.shared_albums_folder = self.base_folder / "Albums-shared"
        self.no_albums_folder = self.base_folder / "No-Albums"

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

        # Definición de patrones de exclusión de carpetas
        self.FOLDER_EXCLUSION_PATTERNS = [
            r"@eaDir",  # Excluye la carpeta específica "@eaDir"
            r"\..*"  # Excluye cualquier carpeta oculta (cuyo nombre comience con ".")
        ]

        # Definición de patrones de exclusión de ficheros
        self.FILE_EXCLUSION_PATTERNS = [
            r"SYNOFILE_THUMB.*"  # Excluye cualquier archivo que empiece por "SYNOFILE_THUMB"
        ]

        # Create a cache dictionary of albums_owned_by_user to save in memmory all the albums owned by this user to avoid multiple calls to method get_albums_ownned_by_user()
        self.albums_owned_by_user = {}

        # Create cache lists for future use
        self.all_assets_filtered = None
        self.assets_without_albums_filtered = None
        self.albums_assets_filtered = None

        # Get the values from the arguments (if exists)
        self.type = ARGS.get('filter-by-type', None)
        self.from_date = ARGS.get('filter-from-date', None)
        self.to_date = ARGS.get('filter-to-date', None)

        self.CLIENT_NAME = f'Local Folder ({self.base_folder.name})'


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
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
            return "unsupported"  # Caso especial para archivos no soportados
        else:  # 'all' o cualquier otro valor no reconocido
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
        # Verificar exclusión de carpetas
        for pattern in self.FOLDER_EXCLUSION_PATTERNS:
            if any(re.fullmatch(pattern, part) for part in file_path.parts):
                return True
        # Verificar exclusión de archivos
        for pattern in self.FILE_EXCLUSION_PATTERNS:
            if re.fullmatch(pattern, file_name):
                return True
        return False

    def get_takeout_assets_by_filters(self, type='all', log_level=None):
        return []  # Clase base no tiene takeout, devuelve lista vacía

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
    def read_config_file(self, config_file='Config.ini', log_level=None):
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

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Retrieving owned albums.")

            albums = [
                {"id": str(p.resolve()), "albumName": p.name}
                for p in self.albums_folder.iterdir() if p.is_dir()
            ]

            albums_filtered = []
            for album in albums:
                album_id = album.get('id')
                album_name = album.get("albumName", "")
                album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                if len(album_assets) > 0:
                    albums_filtered.append(album)
            LOGGER.info(f"Found {len(albums_filtered)} owned albums.")
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

                albums = [
                    {"id": str(p.resolve()), "albumName": p.name}
                    for p in self.albums_folder.iterdir() if p.is_dir()
                ]
                shared_albums = [
                    {"id": str(p.resolve()), "albumName": p.name}
                    for p in self.shared_albums_folder.iterdir() if p.is_dir()
                ]

                all_albums = albums + shared_albums

                albums_filtered = []
                for album in all_albums:
                    album_id = album.get('id')
                    album_name = album.get("albumName", "")
                    album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
                    if len(album_assets) > 0:
                        albums_filtered.append(album)
                LOGGER.info(f"Found {len(albums_filtered)} albums in total (owned + shared).")
            except Exception as e:
                LOGGER.error(f"Failed to get albums (owned + shared): {str(e)}")

            return albums_filtered

    def get_album_assets_size(self, album_id, type='all', log_level=None):
        """
        Gets the total size (bytes) of all assets in an album, with optional filtering by file type.

        Args:
            album_id (str): Path to the album folder.
            type (str): Type of assets to consider for size calculation. Options are 'all', 'photo', 'image', 'video',
                        'media', 'metadata', 'sidecar', 'unsupported'.
            log_level (logging.LEVEL): Log level for logs and console.

        Returns:
            int: Total size of assets in the album (in bytes).
        """
        with set_log_level(LOGGER, log_level):
            try:
                album_path = Path(album_id)
                if not album_path.exists() or not album_path.is_dir():
                    LOGGER.warning(f"Album path '{album_id}' does not exist or is not a directory.")
                    return 0

                selected_type_extensions = self._get_selected_extensions(type)

                total_size = 0
                for file in album_path.iterdir():
                    if file.is_file() or file.is_symlink():
                        # Aplicar exclusiones de carpetas y archivos
                        if self._should_exclude(file):
                            continue

                        file_extension = file.suffix.lower()

                        # Filtrado por tipo de archivo
                        if selected_type_extensions == "unsupported":
                            if file_extension in self.ALLOWED_EXTENSIONS:
                                continue
                        elif selected_type_extensions is not None and file_extension not in selected_type_extensions:
                            continue

                        total_size += file.stat().st_size

                LOGGER.info(f"Total size of {type} assets in album {album_id}: {total_size} bytes.")
                return total_size

            except Exception as e:
                LOGGER.error(f"Failed to calculate size of {type} assets in album '{album_id}': {str(e)}")
                return 0


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
            return len(self.get_all_assets_from_album(album_id, log_level))


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
        Retrieves assets stored in the base folder, filtering by type and applying folder and file exclusions.

        Args:
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media',
                        'metadata', 'sidecar', 'unsupported'.
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
            LOGGER.info(f"Retrieving {type} assets from the base folder, excluding system folders and unwanted files.")
            # If all_assets is already cached, return it
            if self.all_assets_filtered is not None:
                return self.all_assets_filtered

            base_folder = self.base_folder.resolve()
            selected_type_extensions = self._get_selected_extensions(type)

            all_assets = []
            for file in base_folder.rglob("*"):
                if file.is_file():
                    # Aplicar exclusión de carpetas y archivos
                    if self._should_exclude(file):
                        continue

                    file_extension = file.suffix.lower()

                    # Caso especial: archivos no soportados
                    if selected_type_extensions == "unsupported":
                        if file_extension in self.ALLOWED_EXTENSIONS:
                            continue  # Omitir archivos que sí están en las extensiones permitidas
                    elif selected_type_extensions is not None and file_extension not in selected_type_extensions:
                        continue  # Omitir archivos que no están en el tipo solicitado

                    all_assets.append({
                        "id": str(file.resolve()),
                        # "time": file.stat().st_ctime,
                        "time": file.stat().st_mtime,
                        "filename": file.name,
                        "filepath": str(file.resolve()),
                        "type": self._determine_file_type(file),
                    })
            # Here we have to use the old filter_assets method in order to apply the filter to all_assets_filtered. Then the other methods can use the new filter_assets based in this pre-filtered list.
            all_filtered_assets = self.filter_assets_old(assets=all_assets, log_level=log_level)
            LOGGER.info(f"Found {len(all_filtered_assets)} assets of type '{type}' in the base folder.")
            self.all_assets_filtered = all_filtered_assets  # Cache all_assets for future use
            return all_filtered_assets

    def get_all_assets_from_album(self, album_id, album_name=None, type='all', log_level=logging.WARNING):
        """
        Lists the assets within a given album, with optional filtering by file type.

        Args:
            album_id (str): Path to the album folder.
            album_name (str, optional): Name of the album for logging.
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media', 'metadata',
                        'sidecar', 'unsupported'.
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
            try:
                LOGGER.debug(f"Retrieving '{type}' assets for album: {album_id}")

                album_path = Path(album_id)
                if not album_path.exists() or not album_path.is_dir():
                    LOGGER.warning(f"Album path '{album_id}' does not exist or is not a directory.")
                    return []

                selected_type_extensions = self._get_selected_extensions(type)

                album_assets = []
                for file in album_path.iterdir():
                    if file.is_file() or file.is_symlink():
                        # Aplicar exclusiones de carpetas y archivos
                        if self._should_exclude(file):
                            continue

                        file_extension = file.suffix.lower()

                        # Filtrado por tipo de archivo
                        if selected_type_extensions == "unsupported":
                            if file_extension in self.ALLOWED_EXTENSIONS:
                                continue
                        elif selected_type_extensions is not None and file_extension not in selected_type_extensions:
                            continue

                        album_assets.append({
                            "id": str(file.resolve()),
                            # "time": file.stat().st_ctime,
                            "time": file.stat().st_mtime,
                            "filename": file.name,
                            "filepath": str(file.resolve()),
                            "type": self._determine_file_type(file),
                        })

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                LOGGER.debug(f"Found {len(filtered_album_assets)} assets of type '{type}' in album {album_id}.")
                return filtered_album_assets

            except Exception as e:
                error_message = f"Failed to retrieve {type} assets from album '{album_name}'" if album_name else f"Failed to retrieve {type} assets from album ID={album_id}"
                LOGGER.error(f"{error_message}: {str(e)}")
                return []


    def get_all_assets_from_album_shared(self, album_id, album_name=None, album_passphrase=None, log_level=logging.WARNING):
        """
        Lists the assets within a given album, with optional filtering by file type.

        Args:
            album_id (str): Path to the album folder.
            album_name (str, optional): Name of the album for logging.
            album_passphrase (str): Shared album passphrase
            log_level (int): Logging level.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        # TODO: This method is just a copy of get_all_assets_from_album. Change to filter only shared albums
        with set_log_level(LOGGER, log_level):
            try:
                LOGGER.debug(f"Retrieving '{type}' assets for album: {album_id}")

                album_path = Path(album_id)
                if not album_path.exists() or not album_path.is_dir():
                    LOGGER.warning(f"Album path '{album_id}' does not exist or is not a directory.")
                    return []

                selected_type_extensions = self._get_selected_extensions(type)

                album_assets = []
                for file in album_path.iterdir():
                    if file.is_file() or file.is_symlink():
                        # Aplicar exclusiones de carpetas y archivos
                        if self._should_exclude(file):
                            continue

                        file_extension = file.suffix.lower()

                        # Filtrado por tipo de archivo
                        if selected_type_extensions == "unsupported":
                            if file_extension in self.ALLOWED_EXTENSIONS:
                                continue
                        elif selected_type_extensions is not None and file_extension not in selected_type_extensions:
                            continue

                        album_assets.append({
                            "id": str(file.resolve()),
                            # "time": file.stat().st_ctime,
                            "time": file.stat().st_mtime,
                            "filename": file.name,
                            "filepath": str(file.resolve()),
                            "type": self._determine_file_type(file),
                        })

                filtered_album_assets = self.filter_assets(assets=album_assets, log_level=log_level)
                LOGGER.debug(f"Found {len(filtered_album_assets)} assets of type '{type}' in album {album_id}.")
                return filtered_album_assets

            except Exception as e:
                error_message = f"Failed to retrieve {type} assets from album '{album_name}'" if album_name else f"Failed to retrieve {type} assets from album ID={album_id}"
                LOGGER.error(f"{error_message}: {str(e)}")
                return []


    def get_all_assets_without_albums(self, type='all', log_level=logging.WARNING):
        """
        Lists assets that are in self.base_folder but not in self.albums_folder or self.shared_albums_folder,
        with optional filtering by file type.

        Args:
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media', 'metadata',
                        'sidecar', 'unsupported'.
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
            # If assets_without_albums is already cached, return it.
            if self.assets_without_albums_filtered is not None:
                return self.assets_without_albums_filtered

            base_folder = self.base_folder.resolve()
            albums_folder = self.albums_folder.resolve() if self.albums_folder else None
            shared_albums_folder = self.shared_albums_folder.resolve() if self.shared_albums_folder else None

            selected_type_extensions = self._get_selected_extensions(type)

            assets = []
            for file in base_folder.rglob("*"):
                if file.is_file():
                    # Aplicar exclusiones de carpetas y archivos
                    if self._should_exclude(file):
                        continue

                    # Excluir archivos dentro de albums_folder y shared_albums_folder
                    try:
                        if albums_folder and file.relative_to(albums_folder):
                            continue
                    except ValueError:
                        pass

                    try:
                        if shared_albums_folder and file.relative_to(shared_albums_folder):
                            continue
                    except ValueError:
                        pass

                    # Filtrado por tipo de archivo
                    if selected_type_extensions == "unsupported":
                        if file.suffix.lower() in self.ALLOWED_EXTENSIONS:
                            continue
                    elif selected_type_extensions is not None and file.suffix.lower() not in selected_type_extensions:
                        continue

                    assets.append({
                        "id": str(file.resolve()),
                        # "time": file.stat().st_ctime,
                        "time": file.stat().st_mtime,
                        "filename": file.name,
                        "filepath": str(file.resolve()),
                        "type": self._determine_file_type(file),
                    })

            assets_without_albums = self.filter_assets(assets=assets, log_level=log_level)
            takeout_metadata = self.get_takeout_assets_by_filters(type='metadata', log_level=log_level)
            takeout_sidecar = self.get_takeout_assets_by_filters(type='sidecar', log_level=log_level)
            takeout_unsupported = self.get_takeout_assets_by_filters(type='unsupported', log_level=log_level)
            LOGGER.info(f"Found {len(assets_without_albums)} assets of type '{type}' in No-Album folders.")
            all_assets = assets_without_albums + takeout_metadata + takeout_sidecar + takeout_unsupported
            self.assets_without_albums_filtered = all_assets  # Cache assets_without_albums for future use
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
            asset_ids = Utils.convert_to_list(asset_ids)

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
            LOGGER.info(f"Searching for duplicate assets in local storage.")
            size_map = {}
            duplicates = []
            for file in self.base_folder.rglob("*"):
                if file.is_file():
                    fsize = file.stat().st_size
                    if fsize not in size_map:
                        size_map[fsize] = [file]
                    else:
                        size_map[fsize].append(file)

            for fsize, group in size_map.items():
                if len(group) > 1:
                    duplicates.append([str(x.resolve()) for x in group])
            LOGGER.info(f"Found {len(duplicates)} group(s) of duplicates.")
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
                LOGGER.warning(f"{GV.TAG_INFO}File '{file_path}' does not exist or is not a file.")
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


    def push_albums(self, input_folder, subfolders_exclusion='No-Albums',
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
        # (La lógica concreta de la subida local puede ser idéntica a la previa que definimos)
        pass


    def push_no_albums(self, input_folder, subfolders_exclusion='Albums',
                       subfolders_inclusion=None, remove_duplicates=True,
                       log_level=logging.WARNING):
        """
        Recursively uploads all compatible files from 'input_folder' to the No-Albums folder,
        ignoring any subfolders named in 'subfolders_exclusion'.

        Returns:
            tuple: (total_assets_uploaded, total_duplicates_skipped=0, total_duplicates_removed)
        """
        # (Igual a la lógica local previa, adaptada)
        pass


    def push_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        """
        Uploads all photos/videos from input_folder to local storage,
        dividing them between 'albums_folders' and 'No-Albums'.

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
        Simulates downloading 'no albums' assets to output_folder/No-Albums, organizing by year/month.

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

            empty_folders_removed = 0

            # Recorremos en orden inverso para asegurar que primero se limpien las subcarpetas
            for folder in sorted(self.base_folder.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if folder.is_dir():
                    try:
                        # Solo la eliminamos si no tiene archivos ni subdirectorios
                        if not any(folder.iterdir()):
                            folder.rmdir()
                            empty_folders_removed += 1
                            LOGGER.info(f"Removed empty folder: {folder}")
                    except Exception as e:
                        LOGGER.warning(f"WARN    : Could not remove folder '{folder}': {e}")

            LOGGER.info(f"Removed {empty_folders_removed} empty folders.")
            return empty_folders_removed


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

            duplicates_map = defaultdict(list)

            for folder in self.albums_folder.glob("*"):
                if folder.is_dir():
                    album_name = folder.name
                    total_size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                    duplicates_map[(album_name, total_size)].append(folder)

            folders_to_remove = []
            for (album_name, total_size), folders in duplicates_map.items():
                if len(folders) > 1:
                    keeper = folders[0]
                    LOGGER.info(f"Keeping folder '{keeper}' with size {total_size} bytes.")
                    duplicates = folders[1:]
                    for dup_folder in duplicates:
                        folders_to_remove.append((album_name, total_size, dup_folder))

            if not folders_to_remove:
                LOGGER.info(f"No exact duplicate albums found.")
                return 0

            # Display the folders to be removed
            LOGGER.info(f"Folders marked for deletion:")
            for album_name, total_size, dup_folder in folders_to_remove:
                print(f"  '{album_name}' - Size: {total_size} bytes -> {dup_folder}")

            # Ask for confirmation only if requested
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

            # Map from album name to list of folders
            albums_by_name = defaultdict(list)
            for folder in self.albums_folder.glob("*"):
                if folder.is_dir():
                    album_name = folder.name
                    file_count = sum(1 for f in folder.rglob("*") if f.is_file())
                    total_size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                    albums_by_name[album_name].append({
                        "path": folder,
                        "count": file_count,
                        "size": total_size
                    })

            merge_plan = []
            for album_name, folder_group in albums_by_name.items():
                if len(folder_group) <= 1:
                    continue  # No duplicates

                if strategy == 'size':
                    sorted_group = sorted(folder_group, key=lambda x: x['size'], reverse=True)
                else:  # Default to 'count'
                    sorted_group = sorted(folder_group, key=lambda x: x['count'], reverse=True)

                keeper = sorted_group[0]
                duplicates = sorted_group[1:]

                merge_plan.append({
                    "album_name": album_name,
                    "keeper_path": keeper["path"],
                    "duplicates": [dup["path"] for dup in duplicates]
                })

            if not merge_plan:
                LOGGER.info(f"No duplicate albums found.")
                return 0

            # Display the merge plan
            LOGGER.info(f"Albums to be merged:")
            for item in merge_plan:
                LOGGER.info(f"\nAlbum: '{item['album_name']}'")
                LOGGER.info(f"  Keeper: {item['keeper_path']}")
                for dup_path in item["duplicates"]:
                    LOGGER.info(f"  Duplicate to merge and remove: {dup_path}")

            # Ask for confirmation
            if request_user_confirmation and not confirm_continue():
                LOGGER.info(f"Exiting program.")
                return 0

            total_removed_duplicated_albums = 0

            # Proceed with merging
            for item in merge_plan:
                keeper_path = item["keeper_path"]
                for dup_path in item["duplicates"]:
                    LOGGER.debug(f"Moving files from duplicate folder: {dup_path}")

                    for file in dup_path.rglob("*"):
                        if file.is_file():
                            relative_path = file.relative_to(dup_path)
                            target_file = keeper_path / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            if not target_file.exists():
                                file.rename(target_file)
                            else:
                                LOGGER.warning(f"Skipped moving '{file}' as it already exists at destination.")

                    try:
                        dup_path.rmdir()  # Only works if the folder is empty
                        total_removed_duplicated_albums += 1
                        LOGGER.info(f"Removed duplicate folder: {dup_path}")
                    except OSError:
                        shutil.rmtree(dup_path)
                        total_removed_duplicated_albums += 1
                        LOGGER.info(f"Removed duplicate folder and its contents: {dup_path}")

            LOGGER.info(f"Removed {total_removed_duplicated_albums} duplicate folders.")
            return total_removed_duplicated_albums

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
        Removes all assets from local storage (both in albums and No-Albums).

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
    import ChangeWorkingDir
    ChangeWorkingDir.change_working_dir(change_dir=False)

    # Create the Object
    localFolder = ClassLocalFolder()

    # 0) Read configuration and log in
    localFolder.read_config_file('Config.ini')
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

    # 6) Example: Download everything in the structure /Albums/<albumName>/ + /No-Albums/yyyy/mm
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