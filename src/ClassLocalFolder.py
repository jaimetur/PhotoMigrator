import os
import shutil
import logging
import Utils
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager

# We also keep references to your custom logger context manager and utility functions:
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER


##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassLocalFolder:
    def __init__(self, base_folder):
        """
        Initializes the class and sets up the base folder where albums and assets will be managed.

        Args:
            base_folder (str): Path to the main directory where albums and assets will be stored.
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

        self.CLIENT_NAME = f'Local Folder ({self.base_folder.name})'

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

    def get_client_name(self, log_level=logging.INFO):
        """
        Returns the name of the client.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            str: The name of the client.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.debug("DEBUG   : Fetching the client name.")
            return self.CLIENT_NAME

    def get_albums_owned_by_user(self, log_level=logging.INFO):
        """
        Retrieves the list of owned albums.

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Retrieving owned albums.")

            albums = [
                {"id": str(p.resolve()), "albumName": p.name}
                for p in self.albums_folder.iterdir() if p.is_dir()
            ]

            LOGGER.info(f"INFO    : Found {len(albums)} owned albums.")
            return albums

    def get_albums_including_shared_with_user(self, log_level=logging.INFO):
        """
        Retrieves both owned and shared albums.

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Retrieving owned and shared albums.")

            albums = [
                {"id": str(p.resolve()), "albumName": p.name}
                for p in self.albums_folder.iterdir() if p.is_dir()
            ]
            shared_albums = [
                {"id": str(p.resolve()), "albumName": p.name}
                for p in self.shared_albums_folder.iterdir() if p.is_dir()
            ]

            all_albums = albums + shared_albums

            LOGGER.info(f"INFO    : Found {len(all_albums)} albums in total (owned + shared).")
            return all_albums

    def get_album_assets(self, album_id, log_level=logging.INFO):
        """
        Lists the assets within a given album.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': File name (no path).
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"INFO    : Retrieving assets for album: {album_id}")

            album_path = Path(album_id)
            assets = [
                {
                    "id": str(file.resolve()),
                    "time": file.stat().st_ctime,
                    "filename": file.name,
                    "filepath": str(file.resolve()),
                    "type": self._determine_file_type(file),
                }
                for file in album_path.iterdir() if file.is_file() or file.is_symlink()
            ]

            LOGGER.info(f"INFO    : Found {len(assets)} assets in album {album_id}.")
            return assets

    # def get_no_albums_assets(self, log_level=logging.INFO):
    #     """
    #     Lists assets that are not assigned to any album.
    #
    #     Returns:
    #         list[dict]: A list of asset dictionaries, each containing:
    #                     - 'id': Absolute path to the file.
    #                     - 'time': Creation timestamp of the file.
    #                     - 'filename': File name (no path).
    #                     - 'filepath': Absolute path to the file.
    #                     - 'type': Type of the file (image, video, metadata, sidecar, unknown).
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         LOGGER.info("INFO    : Retrieving assets without albums.")
    #
    #         assets = [
    #             {
    #                 "id": str(file.resolve()),
    #                 "time": file.stat().st_ctime,
    #                 "filename": file.name,
    #                 "filepath": str(file.resolve()),
    #                 "type": self._determine_file_type(file),
    #             }
    #             for file in self.no_albums_folder.rglob("*") if file.is_file()
    #         ]
    #
    #         LOGGER.info(f"INFO    : Found {len(assets)} assets without albums.")
    #         return assets

    def get_no_albums_assets(self, log_level=logging.INFO):
        """
        Lists assets that are in self.base_folder but not in self.albums_folder or self.shared_albums_folder.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Retrieving assets excluding albums and shared albums.")

            # Convert paths to absolute for comparison
            base_folder = self.base_folder.resolve()
            albums_folder = self.albums_folder.resolve() if self.albums_folder else None
            shared_albums_folder = self.shared_albums_folder.resolve() if self.shared_albums_folder else None

            assets = []
            for file in base_folder.rglob("*"):
                if file.is_file():
                    # Check if the file is inside the excluded folders
                    if albums_folder and file.is_relative_to(albums_folder):
                        continue
                    if shared_albums_folder and file.is_relative_to(shared_albums_folder):
                        continue

                    assets.append({
                        "id": str(file.resolve()),
                        "time": file.stat().st_ctime,
                        "filename": file.name,
                        "filepath": str(file.resolve()),
                        "type": self._determine_file_type(file),
                    })

            LOGGER.info(f"INFO    : Found {len(assets)} assets excluding album folders.")
            return assets

    def get_all_assets(self, type='all', log_level=logging.INFO):
        """
        Retrieves assets stored in the base folder, filtering by type.

        Args:
            log_level (int): Logging level.
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media', 'metadata', 'sidecar', 'unsupported'.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"INFO    : Retrieving {type} assets from the base folder.")

            # Determine allowed extensions based on the type
            if type in ['photo', 'image']:
                selected_type_extensions = self.ALLOWED_PHOTO_EXTENSIONS
            elif type == 'video':
                selected_type_extensions = self.ALLOWED_VIDEO_EXTENSIONS
            elif type == 'media':
                selected_type_extensions = self.ALLOWED_MEDIA_EXTENSIONS
            elif type == 'metadata':
                selected_type_extensions = self.ALLOWED_METADATA_EXTENSIONS
            elif type == 'sidecar':
                selected_type_extensions = self.ALLOWED_SIDECAR_EXTENSIONS
            elif type == 'unsupported':
                selected_type_extensions = None  # Special case to filter unsupported files
            else:  # 'all' or unrecognized type defaults to all supported extensions
                selected_type_extensions = self.ALLOWED_EXTENSIONS

            assets = [
                {
                    "id": str(file.resolve()),
                    "time": file.stat().st_ctime,
                    "filename": file.name,
                    "filepath": str(file.resolve()),
                    "type": self._determine_file_type(file),
                }
                for file in self.base_folder.rglob("*")
                if file.is_file() and (
                    (selected_type_extensions is None and file.suffix.lower() not in self.ALLOWED_EXTENSIONS) or
                    (selected_type_extensions is not None and file.suffix.lower() in selected_type_extensions)
                )
            ]

            LOGGER.info(f"INFO    : Found {len(assets)} {type} assets in the base folder.")
            return assets

    def remove_empty_albums(self, log_level=logging.INFO):
        """
        Removes all empty album folders.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Removing empty albums.")

            empty_albums = [p for p in self.albums_folder.iterdir() if p.is_dir() and not any(p.iterdir())]
            for album in empty_albums:
                shutil.rmtree(album)

            LOGGER.info(f"INFO    : Removed {len(empty_albums)} empty albums.")
            return True

    def remove_all_albums(self, log_level=logging.INFO):
        """
        Removes all album folders. If removeAlbumsAssets=True, also removes files inside them.

        Returns:
            tuple(int, int): (#albums_removed, #assets_removed_if_requested).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Removing all albums.")

            for album in self.albums_folder.iterdir():
                if album.is_dir():
                    shutil.rmtree(album)

            LOGGER.info("INFO    : All albums have been removed.")
            return True

    ###########################################################################
    #                    NEW METHODS ADAPTED FROM CLASSIMMICHPHOTOS           #
    ###########################################################################
    def read_config_file(self, config_file='Config.ini', log_level=logging.INFO):
        """
        Reads a configuration file (not really used in local storage).

        Args:
            config_file (str): The path to the configuration file. Default is 'Config.ini'.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            dict: An empty dictionary, as config is not used locally.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Reading config file (Not applicable).")
            return {}

    def login(self, log_level=logging.INFO):
        """
        Simulates a login operation. Always successful in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            bool: Always True for local usage.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Logging in (local storage).")
            return True

    def logout(self, log_level=logging.INFO):
        """
        Simulates a logout operation. Always successful in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Logging out (local storage).")

    def get_supported_media_types(self, type='media', log_level=logging.INFO):
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

    def get_user_id(self, log_level=logging.INFO):
        """
        Returns a user ID, which is simply the base folder path in local usage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            str: The path of the base folder as the user ID.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Returning the user ID (base folder path).")
            return str(self.base_folder)

    def create_album(self, album_name, log_level=logging.INFO):
        """
        Creates a new album (folder).

        Args:
            album_name (str): Name of the album to be created.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            bool: True if the album was created successfully, False otherwise.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"INFO    : Creating album '{album_name}'.")
            album_path = self.albums_folder / album_name
            album_path.mkdir(parents=True, exist_ok=True)
            return album_path

    def remove_album(self, album_id, album_name=None, log_level=logging.INFO):
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
            LOGGER.info(f"INFO    : Removing album '{album_name or album_id}'.")
            if album_path.exists() and album_path.is_dir():
                shutil.rmtree(album_path)
                return True
            return False

    def get_album_assets_size(self, album_id, log_level=logging.INFO):
        """
        Gets the total size (bytes) of all assets in an album.

        Args:
            album_id (str): Path to the album folder.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Total size of assets in the album (in bytes).
        """
        with set_log_level(LOGGER, log_level):
            album_path = Path(album_id)
            total_size = 0
            for file in album_path.iterdir():
                if file.is_file() or file.is_symlink():
                    total_size += file.stat().st_size
            return total_size

    def get_album_assets_count(self, album_id, log_level=logging.INFO):
        """
        Gets the number of assets in an album.

        Args:
            album_id (str): Path to the album folder.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of assets in the album.
        """
        with set_log_level(LOGGER, log_level):
            return len(self.get_album_assets(album_id, log_level))

    def album_exists(self, album_name, log_level=logging.INFO):
        """
        Checks if an album with the given name exists in the 'Albums' folder.

        Args:
            album_name (str): Name of the album to check.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            tuple: (bool, str or None) -> (exists, album_path_if_exists)
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"INFO    : Checking if album '{album_name}' exists.")
            for album in self.get_albums_owned_by_user(log_level):
                if album_name == album["albumName"]:
                    return True, album["id"]
            return False, None

    def get_all_albums_assets(self, log_level=logging.WARNING):
        """
        Gathers assets from all known albums, merges them into a single list.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[dict]: Merged assets from all albums.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Gathering all albums' assets.")
            combined_assets = []
            all_albums = self.get_albums_including_shared_with_user(log_level)
            for album in all_albums:
                album_id = album["id"]
                combined_assets.extend(self.get_album_assets(album_id, log_level))
            return combined_assets

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=logging.INFO):
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
            LOGGER.info(f"INFO    : Adding assets to album: {album_name or album_id}")
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
                            LOGGER.info(f"INFO    : Created relative symlink: {symlink_path} -> {relative_path}")
                        except Exception as e:
                            LOGGER.warning(f"WARNING : Error: {e}")
                            LOGGER.warning(f"WARNING : Failed to create symlink {symlink_path}. Copying a duplicated copy of the file into Album folder instead.")
                            try:
                                shutil.copy2(asset_path, symlink_path)
                                LOGGER.info(f"INFO    : Copied file: {symlink_path}")
                            except Exception as copy_error:
                                LOGGER.error(f"ERROR   : Failed to copy file {asset_path} to {symlink_path}. Error: {copy_error}")
                                continue
                        count_added += 1

            LOGGER.info(f"INFO    : Added {count_added} asset(s) to album '{album_name or album_id}'.")
            return count_added

    def get_duplicates_assets(self, log_level=logging.INFO):
        """
        Returns a list of duplicate assets found in local storage.

        Args:
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[list[str]]: Each element is a list of file paths considered duplicates.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("INFO    : Searching for duplicate assets in local storage.")
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
            LOGGER.info(f"INFO    : Found {len(duplicates)} group(s) of duplicates.")
            return duplicates

    def remove_assets(self, asset_ids, log_level=logging.INFO):
        """
        Removes the given asset(s) from local storage.

        Args:
            asset_ids (list[str]): List of absolute file paths to remove.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of assets removed.
        """
        with set_log_level(LOGGER, log_level):
            count = 0
            for asset in asset_ids:
                asset_path = Path(asset)
                if asset_path.exists():
                    asset_path.unlink()
                    count += 1
            LOGGER.info(f"INFO    : Removed {count} asset(s) from local storage.")
            return count

    def remove_duplicates_assets(self, log_level=logging.INFO):
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
            LOGGER.info(f"INFO    : Removed {count_removed} duplicate asset(s) from local storage.")
            return count_removed

    def upload_asset(self, file_path, log_level=logging.INFO):
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
                LOGGER.warning(f"INFO    : File '{file_path}' does not exist or is not a file.")
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
                LOGGER.info(f"INFO    : Uploaded asset '{file_path}' to '{dest}'.")
            return str(dest), False

    def download_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_LocalFolder", log_level=logging.INFO):
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
                LOGGER.warning(f"WARNING : Asset '{asset_id}' does not exist.")
                return 0

            dest_dir = Path(download_folder)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / asset_filename
            shutil.copy2(src, dest)

            if asset_time:
                os.utime(dest, (asset_time, asset_time))

            LOGGER.info(f"INFO    : Downloaded asset '{src}' to '{dest}'.")
            return 1



    def upload_albums(self, input_folder, subfolders_exclusion='No-Albums',
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

    def upload_no_albums(self, input_folder, subfolders_exclusion='Albums',
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

    def upload_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        """
        Uploads all photos/videos from input_folder to local storage,
        dividing them between 'albums_folders' and 'No-Albums'.

        Returns:
            tuple: (albums_uploaded, albums_skipped, total_assets_uploaded,
                    assets_in_albums, assets_in_no_albums, duplicates_removed, duplicates_skipped=0)
        """
        pass

    def download_albums(self, albums_name='ALL', output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading albums by copying album folders to output_folder/Albums.

        Returns:
            tuple: (albums_downloaded, assets_downloaded)
        """
        pass

    def download_no_albums(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading 'no albums' assets to output_folder/No-Albums, organizing by year/month.

        Returns:
            int: Number of assets downloaded.
        """
        pass

    def download_ALL(self, output_folder="Downloads_Immich", log_level=logging.WARNING):
        """
        Simulates downloading all albums and no-albums assets to output_folder.

        Returns:
            tuple: (total_albums_downloaded, total_assets_downloaded,
                    total_assets_in_albums, total_assets_no_albums).
        """
        pass

    def remove_empty_folders(self, log_level=logging.INFO):
        """
        Recursively removes all empty folders in the entire base folder structure.

        Returns:
            int: The number of empty folders removed.
        """
        pass

    def remove_duplicates_albums(self, log_level=logging.WARNING):
        """
        Removes duplicate albums that contain the exact same set of files.

        Returns:
            int: Number of duplicate albums removed.
        """
        pass

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