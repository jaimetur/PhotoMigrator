# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import os
import re
import shutil
import time
import unicodedata
from datetime import datetime
from html import unescape
from pathlib import Path

from Core.CustomLogger import set_log_level
from Core.FolderAnalyzer import FolderAnalyzer
from Core.GlobalVariables import LOGGER, ARGS, FOLDERNAME_NO_ALBUMS, CONFIGURATION_FILE, FOLDERNAME_ALBUMS
from Utils.DateUtils import parse_text_datetime_to_epoch
from Utils.GeneralUtils import has_any_filter, confirm_continue, convert_to_list, tqdm
from Utils.FileUtils import DEFAULT_FILE_EXCLUSION_PATTERNS, DEFAULT_FOLDER_EXCLUSION_PATTERNS, merge_exclusion_patterns, should_exclude_path
from Utils.StandaloneUtils import change_working_dir

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
        self.memories_folder = self.base_folder / "Memories"
        self.shared_albums_folder = self.base_folder / f"{FOLDERNAME_ALBUMS}-shared"
        self.no_albums_folder = self.base_folder / FOLDERNAME_NO_ALBUMS

        # Ensure the base folder exists, but do not eagerly create managed-layout
        # folders when reading a plain local source for automatic migration.
        self.base_folder.mkdir(parents=True, exist_ok=True)

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
        self.FOLDER_EXCLUSION_PATTERNS = merge_exclusion_patterns(
            ARGS.get('exclude-folders', []),
            default_patterns=["_Duplicates"] + DEFAULT_FOLDER_EXCLUSION_PATTERNS,
        )

        # Definition of file exclusion patterns
        self.FILE_EXCLUSION_PATTERNS = merge_exclusion_patterns(
            ARGS.get('exclude-files', []),
            default_patterns=DEFAULT_FILE_EXCLUSION_PATTERNS,
        )

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

    @staticmethod
    def _normalize_folder_token(name):
        text = unicodedata.normalize("NFKD", str(name or ""))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.casefold().strip()
        text = re.sub(r"[_\-]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_special_trash_folder(self, folder_name):
        trash_aliases = {
            "trash",
            "bin",
            "recycle bin",
            "papelera",
            "papelera de reciclaje",
            "lixeira",
            "lixo",
            "corbeille",
            "papierkorb",
            "cestino",
            "cestino eliminati",
            "prullenbak",
            "kosz",
            "kosz na smieci",
            "korzina",
            "корзина",
            "垃圾桶",
            "回收站",
            "ゴミ箱",
            "휴지통",
        }
        return self._normalize_folder_token(folder_name) in trash_aliases

    def _get_partner_shared_root(self):
        return self.base_folder / "PARTNER_SHARED"

    def _get_partner_shared_albums_folder(self):
        return self._get_partner_shared_root() / FOLDERNAME_ALBUMS

    def _get_partner_shared_no_albums_folder(self):
        return self._get_partner_shared_root() / FOLDERNAME_NO_ALBUMS

    def _get_special_folders_root(self):
        return self.base_folder / "Special Folders"

    def _get_album_path(self, album_name, shared=False):
        album_root = self.shared_albums_folder if shared else self.albums_folder
        return album_root / str(album_name)

    def _uses_managed_layout(self):
        managed_roots = (
            self.albums_folder,
            self.shared_albums_folder,
            self.no_albums_folder,
            self._get_partner_shared_root(),
            self._get_special_folders_root(),
        )
        return any(path.exists() and path.is_dir() for path in managed_roots)

    def _iter_album_roots(self):
        if self._uses_managed_layout():
            yield self.albums_folder, "owned"
            if self.memories_folder.exists() and self.memories_folder.is_dir():
                yield self.memories_folder, "owned"
            yield self.shared_albums_folder, "shared"
            yield self._get_partner_shared_albums_folder(), "partner_shared"
            yield self._get_special_folders_root(), "special"

    def _get_plain_layout_album_info(self, file_path):
        try:
            rel = Path(file_path).resolve().relative_to(self.base_folder.resolve())
        except ValueError:
            return None, None
        if len(rel.parts) < 2:
            return None, None
        if self._normalize_folder_token(rel.parts[0]) == "memories":
            if len(rel.parts) < 3:
                return None, None
            album_name = rel.parts[1]
            album_path = (self.base_folder / rel.parts[0] / rel.parts[1]).resolve()
            return album_name, album_path
        album_name = rel.parts[0]
        album_path = (self.base_folder / rel.parts[0]).resolve()
        return album_name, album_path

    def _get_plain_album_name_from_file(self, file_path):
        album_name, _ = self._get_plain_layout_album_info(file_path)
        return album_name

    @staticmethod
    def _get_top_level_folder_name(folder_path, root_path):
        try:
            rel = folder_path.relative_to(root_path)
        except ValueError:
            return None
        if not rel.parts:
            return None
        return rel.parts[0]

    @staticmethod
    def _effective_analyzer_log_level(log_level=None):
        """
        Ensure analyzer bootstrap has at least INFO visibility so tqdm progress is
        not hidden when callers pass WARNING/ERROR.
        """
        if log_level is None:
            return logging.INFO
        try:
            value = int(log_level)
        except (TypeError, ValueError):
            return logging.INFO
        return value if value <= logging.INFO else logging.INFO

    def _invalidate_asset_caches(self):
        self.all_assets_filtered = None
        self.assets_without_albums_filtered = None
        self.albums_assets_filtered = None

    @staticmethod
    def _normalize_manifest_asset_name(filename):
        name = os.path.basename(str(filename or ""))
        stem, ext = os.path.splitext(name)
        stem = re.sub(r"\(\d+\)$", "", stem)
        return f"{stem.casefold()}{ext.casefold()}"

    @staticmethod
    def _manifest_album_key(album_name, occurrence_index=0):
        if occurrence_index <= 0:
            return str(album_name)
        return f"{album_name}_{occurrence_index}"

    def _get_archive_browser_path(self):
        return self.base_folder / "archive_browser.html"

    def _get_album_manifest_path(self):
        return self.base_folder / "automatic_migration_album_manifest.json"

    def _load_album_membership_manifest(self, log_level=None):
        if hasattr(self, "_album_membership_manifest"):
            return self._album_membership_manifest

        manifest = {}
        manifest_path = self._get_album_manifest_path()
        archive_browser_path = self._get_archive_browser_path()

        try:
            if manifest_path.exists() and manifest_path.is_file():
                data = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
                manifest = dict(data.get("albums") or data)
            elif archive_browser_path.exists() and archive_browser_path.is_file():
                html_text = archive_browser_path.read_text(encoding="utf-8", errors="replace")
                manifest = self._parse_archive_browser_manifest(html_text)
        except Exception as error:
            LOGGER.warning(f"Unable to load album membership manifest from '{self.base_folder}': {error}")
            manifest = {}

        self._album_membership_manifest = manifest
        return manifest

    @classmethod
    def _parse_archive_browser_manifest(cls, html_text):
        text = str(html_text or "")
        title_re = re.compile(r'<div class="extracted-folder-name">\s*([^<]+?)\s*</div>', re.IGNORECASE)
        file_re = re.compile(r'<div class="extracted-file-name">\s*([^<]+?)\s*</div>', re.IGNORECASE)

        matches = list(title_re.finditer(text))
        manifest = {}
        occurrences = {}
        for idx, match in enumerate(matches):
            album_name = unescape(str(match.group(1) or "")).strip()
            if not album_name:
                continue
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[start:end]
            files = []
            seen_files = set()
            for file_match in file_re.finditer(block):
                filename = unescape(str(file_match.group(1) or "")).strip()
                if not filename or filename == album_name:
                    continue
                if filename in seen_files:
                    continue
                seen_files.add(filename)
                files.append(filename)

            occurrence_index = occurrences.get(album_name, 0)
            manifest_key = cls._manifest_album_key(album_name, occurrence_index)
            manifest[manifest_key] = files
            occurrences[album_name] = occurrence_index + 1

        return manifest

    def _build_manifest_candidate_index(self):
        if hasattr(self, "_manifest_candidate_index") and self._manifest_candidate_index is not None:
            return self._manifest_candidate_index

        self._ensure_analyzer(log_level=logging.WARNING)
        exact = {}
        normalized = {}
        for path_str in getattr(self.analyzer, "filtered_file_list", []) or []:
            path_obj = Path(path_str)
            if not (path_obj.is_file() or path_obj.is_symlink()):
                continue
            exact.setdefault(path_obj.name.casefold(), []).append(path_str)
            normalized.setdefault(self._normalize_manifest_asset_name(path_obj.name), []).append(path_str)

        self._manifest_candidate_index = {
            "exact": exact,
            "normalized": normalized,
        }
        return self._manifest_candidate_index

    def _iter_non_album_roots(self):
        roots = []
        if self.no_albums_folder.exists() and self.no_albums_folder.is_dir():
            roots.append(self.no_albums_folder.resolve())
        partner_shared_no_albums = self._get_partner_shared_no_albums_folder()
        if partner_shared_no_albums.exists() and partner_shared_no_albums.is_dir():
            roots.append(partner_shared_no_albums.resolve())
        return roots

    def _select_manifest_backed_asset_path(self, expected_filename, sel_ext_local=None):
        candidate_index = self._build_manifest_candidate_index()
        expected_casefold = str(expected_filename or "").casefold()
        expected_normalized = self._normalize_manifest_asset_name(expected_filename)
        candidate_paths = list(candidate_index["exact"].get(expected_casefold, []))
        if not candidate_paths:
            candidate_paths = list(candidate_index["normalized"].get(expected_normalized, []))
        if not candidate_paths:
            return None

        non_album_roots = self._iter_non_album_roots()

        def is_allowed_extension(path_obj):
            if not sel_ext_local:
                return True
            if sel_ext_local == "unsupported":
                return path_obj.suffix.lower() not in self.ALLOWED_EXTENSIONS
            return path_obj.suffix.lower() in sel_ext_local

        def score(path_str):
            path_obj = Path(path_str)
            exact_name_penalty = 0 if path_obj.name.casefold() == expected_casefold else 1
            non_album_penalty = 1
            resolved_parent = path_obj.parent.resolve()
            for root in non_album_roots:
                try:
                    resolved_parent.relative_to(root)
                    non_album_penalty = 0
                    break
                except ValueError:
                    continue
            numbered_match = re.search(r"\((\d+)\)(?=\.[^.]+$)", path_obj.name)
            numbered_penalty = int(numbered_match.group(1)) if numbered_match else 0
            return (non_album_penalty, exact_name_penalty, numbered_penalty, len(path_obj.name))

        filtered_candidates = []
        for path_str in candidate_paths:
            path_obj = Path(path_str)
            if not path_obj.exists():
                continue
            if not is_allowed_extension(path_obj):
                continue
            filtered_candidates.append(path_str)

        if not filtered_candidates:
            return None

        filtered_candidates.sort(key=score)
        return Path(filtered_candidates[0])

    @staticmethod
    def _is_media_request(asset_type):
        return str(asset_type or "all").lower() in {"all", "photo", "photos", "image", "images", "video", "videos", "media"}

    def _supplement_album_assets_from_manifest(self, album_name, sel_ext_local, requested_type, current_assets, log_level=None):
        if not album_name or not self._uses_managed_layout() or not self._is_media_request(requested_type):
            return current_assets

        manifest = self._load_album_membership_manifest(log_level=log_level)
        expected_files = manifest.get(str(album_name), [])
        if not expected_files:
            return current_assets

        existing_names = {str(item.get("filename", "")).casefold() for item in current_assets}
        existing_paths = {str(item.get("filepath", "")) for item in current_assets}
        supplemented = 0

        for expected_filename in expected_files:
            filename = str(expected_filename or "").strip()
            if not filename or filename.casefold() in existing_names:
                continue
            candidate_path = self._select_manifest_backed_asset_path(filename, sel_ext_local=sel_ext_local)
            if candidate_path is None:
                continue
            if str(candidate_path) in existing_paths:
                continue
            try:
                mtime = candidate_path.stat().st_mtime
            except (OSError, IOError) as error:
                LOGGER.warning(f"Unable to read mtime from manifest-backed asset {candidate_path}: {error}")
                continue

            current_assets.append({
                "id": str(candidate_path),
                "time": mtime,
                "filename": filename,
                "filepath": str(candidate_path),
                "type": self._determine_file_type(candidate_path),
            })
            existing_names.add(filename.casefold())
            existing_paths.add(str(candidate_path))
            supplemented += 1

        if supplemented > 0:
            LOGGER.info(f"Supplemented {supplemented} album asset(s) for '{album_name}' using archive_browser manifest fallback.")
        return current_assets

    def _refresh_analyzer_from_disk(self, step_name="", log_level=None):
        self._ensure_analyzer(log_level=log_level)
        self.analyzer._build_file_list_from_disk(step_name=step_name, log_level=log_level)
        self.analyzer._apply_filters(step_name=step_name, log_level=log_level)
        self.analyzer._compute_folder_sizes(step_name=step_name, log_level=log_level)
        self._invalidate_asset_caches()
        if hasattr(self, "_manifest_candidate_index"):
            self._manifest_candidate_index = None

    def _is_cleanup_auxiliary_file(self, file_path):
        path_obj = Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return False

        lower_name = path_obj.name.casefold()
        lower_suffix = path_obj.suffix.lower()
        if lower_suffix in self.ALLOWED_METADATA_EXTENSIONS or lower_suffix in self.ALLOWED_SIDECAR_EXTENSIONS:
            return True
        if lower_name in {
            "archive_browser.html",
            "automatic_migration_album_manifest.json",
            "automatic_migration_dates_metadata.json",
            "remember-list.json",
            "shared_album_comments.json",
            "user-generated-memory-titles.json",
        }:
            return True
        return False

    def remove_metadata_only_folders(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if not self.base_folder.exists():
                return {"folders_removed": 0, "files_removed": 0}

            files_removed = 0
            folders_removed = 0

            for root, dirs, files in os.walk(self.base_folder, topdown=False):
                root_path = Path(root)
                removable_files = []
                blocked = False

                for file_name in files:
                    file_path = root_path / file_name
                    if self._is_cleanup_auxiliary_file(file_path):
                        removable_files.append(file_path)
                    else:
                        blocked = True
                        break

                if blocked:
                    continue

                for file_path in removable_files:
                    try:
                        file_path.unlink()
                        files_removed += 1
                    except Exception as error:
                        LOGGER.warning(f"Failed to remove metadata-only file '{file_path}': {error}")
                        blocked = True
                        break

                if blocked:
                    continue

                if any(Path(root_path / directory).exists() for directory in dirs):
                    continue

                if root_path == self.base_folder:
                    continue

                try:
                    root_path.rmdir()
                    folders_removed += 1
                except Exception:
                    continue

            if files_removed or folders_removed:
                self._refresh_analyzer_from_disk(step_name="remove_metadata_only_folders: ", log_level=log_level)

            LOGGER.info(f"Removed {files_removed} metadata/auxiliary file(s) and {folders_removed} metadata-only folder(s).")
            return {"folders_removed": folders_removed, "files_removed": files_removed}

    def cleanup_after_move_assets(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            summary = {
                "metadata_files_removed": 0,
                "metadata_folders_removed": 0,
                "empty_folders_removed": 0,
                "empty_albums_removed": 0,
                "root_removed": False,
            }

            self._refresh_analyzer_from_disk(step_name="cleanup_after_move_assets: ", log_level=log_level)

            metadata_cleanup = self.remove_metadata_only_folders(log_level=log_level)
            summary["metadata_files_removed"] = int(metadata_cleanup.get("files_removed", 0))
            summary["metadata_folders_removed"] = int(metadata_cleanup.get("folders_removed", 0))

            empty_albums_before = len([p for p in self.albums_folder.iterdir() if p.is_dir() and not any(p.iterdir())]) if self.albums_folder.exists() else 0
            if empty_albums_before > 0:
                self.remove_empty_albums(log_level=log_level)
            summary["empty_albums_removed"] = empty_albums_before

            empty_folders_removed = self.remove_empty_folders(log_level=log_level)
            summary["empty_folders_removed"] = int(empty_folders_removed or 0)

            root_children = list(self.base_folder.iterdir()) if self.base_folder.exists() else []
            if self.base_folder.exists() and not root_children:
                try:
                    self.base_folder.rmdir()
                    summary["root_removed"] = True
                except Exception as error:
                    LOGGER.warning(f"Unable to remove empty source root '{self.base_folder}': {error}")

            LOGGER.info(
                "Source cleanup summary: "
                f"metadata_files_removed={summary['metadata_files_removed']}, "
                f"metadata_folders_removed={summary['metadata_folders_removed']}, "
                f"empty_albums_removed={summary['empty_albums_removed']}, "
                f"empty_folders_removed={summary['empty_folders_removed']}, "
                f"root_removed={summary['root_removed']}"
            )
            return summary


    ###########################################################################
    #                           GENERAL UTILITY                               #
    ###########################################################################
    def _ensure_analyzer(self, metadata_json_file=None, step_name="", log_level=None):
        """
        Ensure FolderAnalyzer is initialized lazily, reading filters from ARGS.
        """
        effective_log_level = self._effective_analyzer_log_level(log_level)
        with set_log_level(LOGGER, effective_log_level):
            if not hasattr(self, 'analyzer') or self.analyzer is None:
                LOGGER.info(f"{step_name}Initializing analyzer for {self.base_folder}. This process may take long time. Please be patient…")

                # Read filter parameters from ARGS
                selected_ext = None
                if ARGS.get('filter-by-type'):
                    selected_ext = self._get_selected_extensions(ARGS['filter-by-type'])
                epoch_start = 0 if not ARGS.get('filter-from-date') else parse_text_datetime_to_epoch(ARGS['filter-from-date'])
                epoch_end = float('inf') if not ARGS.get('filter-to-date') else parse_text_datetime_to_epoch(ARGS['filter-to-date'])
                needs_date_extraction = not (epoch_start == 0 and epoch_end == float('inf'))

                # Initialize analyzer with metadata_json_file or with folder_path
                if metadata_json_file and os.path.isfile(metadata_json_file):
                    self.analyzer = FolderAnalyzer(folder_path=None, metadata_json_file=metadata_json_file, extracted_dates=None, logger=LOGGER, step_name=step_name, filter_ext=selected_ext, filter_from_epoch=epoch_start, filter_to_epoch=epoch_end)
                    # self.analyzer = FolderAnalyzer(folder_path=str(self.base_folder), metadata_json_file=None, extracted_dates=None, logger=LOGGER, step_name=step_name, filter_ext=selected_ext, filter_from_epoch=epoch_start, filter_to_epoch=epoch_end)

                else:
                    self.analyzer = FolderAnalyzer(
                        folder_path=str(self.base_folder),
                        metadata_json_file=None,
                        extracted_dates=None,
                        force_date_extraction=needs_date_extraction,
                        logger=LOGGER,
                        step_name=step_name,
                        filter_ext=selected_ext,
                        filter_from_epoch=epoch_start,
                        filter_to_epoch=epoch_end,
                    )

                # Optional: save date metadata for reuse
                if self.analyzer.extracted_dates:
                    self.analyzer.save_to_json(output_file="automatic_migration_dates_metadata.json", step_name=step_name)

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
        if type in ['photo', 'photos', 'image', 'images']:
            return self.ALLOWED_PHOTO_EXTENSIONS
        elif type in ['video', 'videos']:
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
        return should_exclude_path(
            file_path,
            exclusion_folders=self.FOLDER_EXCLUSION_PATTERNS,
            exclusion_files=self.FILE_EXCLUSION_PATTERNS,
        )

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
    def _get_supported_media_types(self, type='media', log_level=None):
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


    def _get_user_id(self, log_level=None):
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


    def _get_user_mail(self, log_level=None):
        """
        Returns the user_mail of the currently logged-in user.
        """
        with set_log_level(LOGGER, log_level):
            return "no-applicable"


    ###########################################################################
    #                            ALBUMS FUNCTIONS                             #
    ###########################################################################
    def create_album(self, album_name: str, shared=False, log_level=None) -> Path:
        """
        Creates a new album (folder), and updates the analyzer caches.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Creating album '{album_name}'.")
            album_path = self._get_album_path(album_name=album_name, shared=shared)
            album_path.mkdir(parents=True, exist_ok=True)

            # --- Update analyzer, if already initialized
            if hasattr(self, 'analyzer') and self.analyzer is not None:
                key = album_path.resolve().as_posix()
                # Initialize its counters to zero
                self.analyzer.folder_assets[key] = 0
                self.analyzer.folder_sizes[key] = 0
                # Also include it in filtered_file_list if appropriate (empty for now)
                # self.analyzer.filtered_file_list.extend([])

            return album_path

    def remove_album(self, album_id, album_name=None, log_level=None):
        """
        Removes an album (folder) if it exists and refreshes the analyzer.

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
                # Refresh the analyzer so it reflects the deletion
                # Rebuild file_list and recompute folder sizes/assets
                self.analyzer._build_file_list_from_disk(step_name="remove_album: ")
                self.analyzer._compute_folder_sizes(step_name="remove_album: ")
                return True
            else:
                LOGGER.warning(f"Album '{album_id}' not found or is not a directory.")
                return False

    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        """
        Retrieves the list of owned albums.

        Args:
            filter_assets (bool): If True, only return albums with at least one filtered asset.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            list[dict]: A list of dictionaries containing album details.
                        Each dictionary contains:
                        - 'id': Full path of the album folder.
                        - 'albumName': Name of the album folder.
        """
        effective_log_level = self._effective_analyzer_log_level(log_level)
        with set_log_level(LOGGER, effective_log_level):
            LOGGER.info("Retrieving owned albums.")

            cache_key = f"owned_{filter_assets}"
            if cache_key in self.albums_owned_by_user:
                LOGGER.debug("Returning cached owned albums.")
                return self.albums_owned_by_user[cache_key]

            self._ensure_analyzer(log_level=effective_log_level)

            source_files = self.analyzer.filtered_file_list if filter_assets else self.analyzer.file_list
            owned = []
            if self._uses_managed_layout():
                managed_roots = []
                if self.albums_folder.exists() and self.albums_folder.is_dir():
                    managed_roots.append(self.albums_folder.resolve())
                if self.memories_folder.exists() and self.memories_folder.is_dir():
                    managed_roots.append(self.memories_folder.resolve())
                for p in source_files:
                    for album_root in managed_roots:
                        try:
                            rel = Path(p).resolve().relative_to(album_root)
                        except ValueError:
                            continue
                        if not rel.parts:
                            continue
                        album_name = rel.parts[0]
                        album_id = str((album_root / album_name).resolve())
                        owned.append((album_id, album_name))
                        break
            else:
                for p in source_files:
                    album_name, album_path = self._get_plain_layout_album_info(p)
                    if not album_name or album_path is None:
                        continue
                    album_id = str(album_path)
                    owned.append((album_id, album_name))

            # dedupe
            seen = set()
            albums = []
            for album_id, album_name in owned:
                if album_id in seen:
                    continue
                seen.add(album_id)
                albums.append({"id": album_id, "albumName": album_name})

            LOGGER.info(f"Found {len(albums)} owned albums.")
            # Cache the result for future calls
            self.albums_owned_by_user[cache_key] = albums
            return albums

    # def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
    #     """
    #     Retrieves the list of owned albums.
    #
    #     Args:
    #         filter_assets (bool): If True, only return albums with at least one asset.
    #         log_level (logging.LEVEL): log level for logs and console.
    #
    #     Returns:
    #         list[dict]: A list of dictionaries containing album details.
    #                     Each dictionary contains:
    #                     - 'id': Full path of the album folder.
    #                     - 'albumName': Name of the album folder.
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         LOGGER.info("Retrieving owned albums.")
    #
    #         # Check if we already have cached results for this filter_assets value
    #         cache_key = f"owned_{filter_assets}"
    #         if cache_key in self.albums_owned_by_user:
    #             LOGGER.debug("Returning cached owned albums.")
    #             return self.albums_owned_by_user[cache_key]
    #
    #         # Initialize the analyzer if needed
    #         self._ensure_analyzer(log_level=log_level)
    #
    #         # Discover non-empty album names via analyzer.file_list
    #         album_names = set()
    #         base = Path(self.albums_folder.resolve())
    #         for p in self.analyzer.file_list:
    #             file = Path(p)
    #             try:
    #                 # only process files that live under the Albums folder
    #                 rel = file.relative_to(base)
    #             except ValueError:
    #                 # file is not inside base → skip
    #                 continue
    #             # the first component of the relative path is the album folder name
    #             album_names.add(rel.parts[0])
    #
    #         # Build the list of albums
    #         albums = [
    #             {"id": str((self.albums_folder / name).resolve()), "albumName": name}
    #             for name in album_names
    #         ]
    #
    #         # If not filtering by assets, cache and return immediately
    #         if not filter_assets:
    #             self.albums_owned_by_user[cache_key] = albums
    #             return albums
    #
    #         # Apply the original asset-presence filter
    #         albums_filtered = []
    #         for album in albums:
    #             album_id = album["id"]
    #             album_name = album["albumName"]
    #             album_assets = self.get_all_assets_from_album(album_id, album_name, log_level=log_level)
    #             if len(album_assets) > 0:
    #                 albums_filtered.append(album)
    #
    #         LOGGER.info(f"Found {len(albums_filtered)} owned albums.")
    #
    #         # Cache the result for future calls
    #         self.albums_owned_by_user[cache_key] = albums_filtered
    #         return albums_filtered

    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        """
        Retrieves both owned and shared albums that contain at least one asset
        passing the current filters.
        """
        effective_log_level = self._effective_analyzer_log_level(log_level)
        with set_log_level(LOGGER, effective_log_level):
            try:
                LOGGER.info("Retrieving owned and shared albums.")
                if not self._uses_managed_layout():
                    albums = self.get_albums_owned_by_user(filter_assets=filter_assets, log_level=effective_log_level)
                    LOGGER.info(f"Found {len(albums)} albums in total (owned + shared).")
                    return albums

                # Inicializa el analyzer y sus folder_assets
                self._ensure_analyzer(log_level=effective_log_level)

                album_roots = [
                    (Path(album_root.resolve()), root_kind)
                    for album_root, root_kind in self._iter_album_roots()
                ]
                discovered_albums = {}

                if filter_assets:
                    # Solo iteramos las carpetas que tienen >=1 fichero filtrado
                    candidate_folders = [Path(folder_str) for folder_str, count in self.analyzer.folder_assets.items() if count > 0]
                else:
                    candidate_folders = []
                    seen_folders = set()
                    for file_path in self.analyzer.file_list:
                        file_parent = Path(file_path).parent
                        key = file_parent.resolve().as_posix()
                        if key not in seen_folders:
                            seen_folders.add(key)
                            candidate_folders.append(file_parent)
                with tqdm(
                    total=len(candidate_folders),
                    desc="📚 Scanning Owned/Shared Albums",
                    unit="folder",
                    smoothing=0.1,
                    dynamic_ncols=True,
                    leave=True,
                ) as pbar:
                    for folder in candidate_folders:
                        for album_root, root_kind in album_roots:
                            album_name = self._get_top_level_folder_name(folder, album_root)
                            if not album_name:
                                continue
                            if root_kind == "special" and self._is_special_trash_folder(album_name):
                                continue
                            album_id = str((album_root / album_name).resolve())
                            discovered_albums.setdefault(album_id, {"id": album_id, "albumName": album_name})
                        pbar.update(1)

                result = list(discovered_albums.values())
                LOGGER.info(f"Found {len(result)} albums in total (owned + shared).")
                return result

            except Exception as e:
                LOGGER.error(f"Failed to get albums (owned + shared): {e}")
                return []

    def get_album_assets_size(self, album_id, type='all', log_level=None):
        """
        Total size (bytes) of assets in an album, with global and local filters.
        """
        with set_log_level(LOGGER, log_level):
            # Ensure the analyzer (with filters applied) is ready
            self._ensure_analyzer(log_level=log_level)

            album_path = Path(album_id)
            if not album_path.is_dir():
                LOGGER.warning(f"Album path '{album_id}' is invalid.")
                return 0

            prefix = album_path.resolve()

            # If there are no active filters and asking for all, return cached folder size
            if type == 'all' and not self.type and not self.from_date and not self.to_date:
                return self.analyzer.folder_sizes.get(prefix.as_posix(), 0)

            # Determine local and global extension filters
            sel_ext_local = self._get_selected_extensions(type)
            sel_ext_global = self._get_selected_extensions(self.type) if self.type else None

            # Compute epoch bounds
            epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
            epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)

            total = 0

            # Iterate only over files that passed the global filtering
            for p in self.analyzer.filtered_file_list:
                file = Path(p)
                # Skip files outside this album
                try:
                    file.relative_to(prefix)
                except ValueError:
                    continue

                size = self.analyzer.file_sizes.get(p)
                if size is None:
                    continue

                ext = file.suffix.lower()

                # Apply local type filter
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue

                # Apply global type filter
                if sel_ext_global:
                    if sel_ext_global == "unsupported":
                        if ext in self.ALLOWED_EXTENSIONS:
                            continue
                    elif ext not in sel_ext_global:
                        continue

                # Apply date filter using pre-extracted dates
                file_date = self.analyzer.extracted_dates.get(p)
                if file_date is None:
                    continue
                ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
                if ts < epoch_start or ts > epoch_end:
                    continue

                # Accumulate size
                total += size

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


    def album_exists(self, album_name, shared=False, log_level=None):
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
            target_path = self._get_album_path(album_name=album_name, shared=shared).resolve().as_posix()
            if Path(target_path).is_dir():
                return True, target_path
            return False, None

    ###########################################################################
    #                        ASSETS (PHOTOS/VIDEOS)                           #
    ###########################################################################
    def get_assets_by_filters(self, type='all', log_level=logging.WARNING):
        """
        Retrieves all assets from the base_folder, filtering first by global date/type
        (already applied in analyzer.filtered_file_list) and then by local type (parameter 'type').
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"Retrieving {type} assets…")

            # Return cached result if no filtering parameters are active
            if self.all_assets_filtered is not None and not self.from_date and not self.to_date and not self.type and type == 'all':
                return self.all_assets_filtered

            # Determine which extensions to keep for this local type filter
            sel_ext_local = self._get_selected_extensions(type)

            # Ensure analyzer has been initialized and global filters applied
            self._ensure_analyzer(log_level=log_level)

            result = []
            # Iterate only over files that already passed global filtering
            for p in self.analyzer.filtered_file_list:
                f = Path(p)
                # Skip anything that's not a file or symlink
                if not (f.is_file() or f.is_symlink()):
                    continue
                # Exclude by pattern if needed
                if self._should_exclude(f):
                    continue

                ext = f.suffix.lower()
                # Apply local type filter
                if sel_ext_local == "unsupported":
                    if ext in self.ALLOWED_EXTENSIONS:
                        continue
                elif sel_ext_local and ext not in sel_ext_local:
                    continue

                # Gather file metadata
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
            # Cache for future calls
            self.all_assets_filtered = result
            return result

    # def get_assets_by_filters(self, type='all', log_level=logging.WARNING):
    #     """
    #     Retrieves all assets from the base_folder, filtering by global date/type
    #     and by local type (parameter 'type').
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         LOGGER.info(f"Retrieving {type} assets…")
    #
    #         if self.all_assets_filtered is not None and not self.from_date and not self.to_date and not self.type:
    #             return self.all_assets_filtered
    #
    #         sel_ext_local = self._get_selected_extensions(type)
    #         sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
    #         epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
    #         epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)
    #
    #         self._ensure_analyzer(log_level=log_level)
    #         result = []
    #
    #         for p in self.analyzer.file_list:
    #             f = Path(p)
    #             if not f.is_file():
    #                 continue
    #             if self._should_exclude(f):
    #                 continue
    #
    #             ext = f.suffix.lower()
    #             # local filter
    #             if sel_ext_local == "unsupported":
    #                 if ext in self.ALLOWED_EXTENSIONS:
    #                     continue
    #             elif sel_ext_local and ext not in sel_ext_local:
    #                 continue
    #             # global filter
    #             if sel_ext_global:
    #                 if sel_ext_global == "unsupported":
    #                     if ext in self.ALLOWED_EXTENSIONS:
    #                         continue
    #                 elif ext not in sel_ext_global:
    #                     continue
    #
    #             # global date filter
    #             file_date = self.analyzer.get_date(p)
    #             if file_date is None:
    #                 continue
    #             ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
    #             if ts < epoch_start or ts > epoch_end:
    #                 continue
    #
    #             # OK: asset metadata
    #             try:
    #                 mtime = f.stat().st_mtime
    #             except (OSError, IOError) as e:
    #                 LOGGER.warning(f"Could not read mtime of {f}: {e}")
    #                 continue
    #
    #             result.append({
    #                 "id": str(f),
    #                 "time": mtime,
    #                 "filename": f.name,
    #                 "filepath": str(f),
    #                 "type": self._determine_file_type(f),
    #             })
    #
    #         LOGGER.info(f"Found {len(result)} assets of type '{type}'.")
    #         self.all_assets_filtered = result
    #         return result

    def get_all_assets_from_album(self, album_id, album_name=None, type='all', log_level=logging.WARNING):
        """
        Lists the assets within a given  album, with optional filtering by file type.

        Args:
            album_id (str): Path to the  album folder.
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
        with set_log_level(LOGGER, log_level):
            album_path = Path(album_id)
            if not album_path.is_dir():
                LOGGER.warning(f"Album '{album_id}' does not exist.")
                return []

            # prepare local extension filter
            sel_ext_local = self._get_selected_extensions(type)

            # ensure analyzer has already built filtered_file_list
            self._ensure_analyzer(log_level=log_level)

            assets = []
            prefix = album_path.resolve().as_posix().rstrip('/') + '/'

            # iterate only prefiltered assets (global filters already applied)
            for p in self.analyzer.filtered_file_list:
                # skip any file outside this album folder
                if not p.startswith(prefix):
                    continue

                filepath = Path(p)
                # skip non-file (but include valid symlinks)
                if not (filepath.is_file() or filepath.is_symlink()):
                    continue

                # -- local type filter (if requested) --
                if sel_ext_local:
                    if sel_ext_local == "unsupported":
                        if filepath.suffix.lower() in self.ALLOWED_EXTENSIONS:
                            continue
                    elif filepath.suffix.lower() not in sel_ext_local:
                        continue

                # -- get modification time (for ordering or metadata) --
                try:
                    mtime = filepath.stat().st_mtime
                except (OSError, IOError) as e:
                    LOGGER.warning(f"Unable to read mtime from {filepath}: {e}")
                    continue

                # build the asset dict
                assets.append({
                    "id": str(filepath),
                    "time": mtime,
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "type": self._determine_file_type(filepath),
                })

            assets = self._supplement_album_assets_from_manifest(
                album_name=album_name or album_path.name,
                sel_ext_local=sel_ext_local,
                requested_type=type,
                current_assets=assets,
                log_level=log_level,
            )

            LOGGER.debug(f"{len(assets)} assets in album '{album_id}'.")
            return assets

    # def get_all_assets_from_album(self, album_id, album_name=None, type='all', filter_assets=True, log_level=logging.WARNING):
    #     """
    #     Lists assets in a specific album, applying both global and local type/date filters.
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         album_path = Path(album_id)
    #         if not album_path.is_dir():
    #             LOGGER.warning(f"Album '{album_id}' does not exist.")
    #             return []
    #
    #         sel_ext_local = self._get_selected_extensions(type)
    #         sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
    #         epoch_start = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
    #         epoch_end = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)
    #         prefix = album_path.resolve()
    #
    #         self._ensure_analyzer(log_level=log_level)
    #         assets = []
    #
    #         for p in self.analyzer.file_list:
    #             filepath = Path(p)
    #             try:
    #                 filepath.relative_to(prefix)
    #             except ValueError:
    #                 continue
    #             if not (filepath.is_file() or filepath.is_symlink()):
    #                 continue
    #             if self._should_exclude(filepath):
    #                 continue
    #
    #             ext = filepath.suffix.lower()
    #             # local filter
    #             if sel_ext_local == "unsupported":
    #                 if ext in self.ALLOWED_EXTENSIONS:
    #                     continue
    #             elif sel_ext_local and ext not in sel_ext_local:
    #                 continue
    #             # global filter
    #             if sel_ext_global:
    #                 if sel_ext_global == "unsupported":
    #                     if ext in self.ALLOWED_EXTENSIONS:
    #                         continue
    #                 elif ext not in sel_ext_global:
    #                     continue
    #
    #             # global date filter (resolve symlinks to get real metadata)
    #             fs_path = Path(p)
    #             if fs_path.is_symlink():
    #                 # resolve the link to the real file
    #                 target = fs_path.resolve()
    #                 file_date = self.analyzer.get_date(str(target))
    #             else:
    #                 file_date = self.analyzer.get_date(p)
    #
    #             if file_date is None:
    #                 continue
    #             ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
    #             if ts < epoch_start or ts > epoch_end:
    #                 continue
    #
    #             try:
    #                 mtime = filepath.stat().st_mtime
    #             except (OSError, IOError) as e:
    #                 LOGGER.warning(f"Unable to read mtime from {filepath}: {e}")
    #                 continue
    #
    #             assets.append({
    #                 "id": str(filepath),
    #                 "time": mtime,
    #                 "filename": filepath.name,
    #                 "filepath": str(filepath),
    #                 "type": self._determine_file_type(filepath),
    #             })
    #
    #         LOGGER.debug(f"{len(assets)} assets in album '{album_id}'.")
    #         return assets

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

            # Si no hay nada filtrado en esa carpeta, devolvemos ya []
            count = self.analyzer.folder_assets.get(str(album_path.resolve()), 0)
            if count == 0:
                LOGGER.debug(f"0 assets in shared album '{album_id}'.")
                return []

            # Si solo quieres IDs y nombres de fichero, sin reconstruir dicts…
            assets = []
            for p in self.analyzer.filtered_file_list:
                fp = Path(p)
                try:
                    fp.relative_to(album_path.resolve())
                except ValueError:
                    continue
                # Solo añades el bloque de lectura de stat y tipo si realmente necesitas mtime/tipo
                try:
                    mtime = fp.stat().st_mtime
                except OSError:
                    continue
                assets.append({
                    "id": str(fp),
                    "time": mtime,
                    "filename": fp.name,
                    "filepath": str(fp),
                    "type": self._determine_file_type(fp),
                })

            LOGGER.debug(f"{len(assets)} assets in shared album '{album_id}'.")
            return assets

    # def get_all_assets_from_album_shared(self, album_id, album_name=None, type='all', album_passphrase=None, log_level=logging.WARNING):
    #     """
    #     Lists the assets within a given shared album, with optional filtering by file type.
    #
    #     Args:
    #         album_id (str): Path to the shared album folder.
    #         album_name (str, optional): Name of the album for logging.
    #         type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media',
    #                     'metadata', 'sidecar', 'unsupported'.
    #         album_passphrase (str): Shared album passphrase (no‐op for local).
    #         log_level (int): Logging level.
    #
    #     Returns:
    #         list[dict]: A list of asset dictionaries, each containing:
    #                     - 'id': Absolute path to the file.
    #                     - 'time': Modification timestamp.
    #                     - 'filename': File name.
    #                     - 'filepath': Absolute path.
    #                     - 'type': 'image', 'video', etc.
    #     """
    #     # TODO: This method is just a copy of get_all_assets_from_album. Change to filter only shared albums
    #
    #     with set_log_level(LOGGER, log_level):
    #         album_path = Path(album_id)
    #         if not album_path.is_dir():
    #             LOGGER.warning(f"Shared album '{album_id}' does not exist.")
    #             return []
    #
    #         sel_ext_local  = self._get_selected_extensions(type)
    #         sel_ext_global = self._get_selected_extensions(self.type) if self.type else None
    #         epoch_start    = 0 if not self.from_date else parse_text_datetime_to_epoch(self.from_date)
    #         epoch_end      = float('inf') if not self.to_date else parse_text_datetime_to_epoch(self.to_date)
    #         prefix         = str(album_path.resolve())
    #
    #         self._ensure_analyzer(log_level=log_level)
    #         assets = []
    #
    #         for p in self.analyzer.file_list:
    #             filepath = Path(p)
    #             try:
    #                 filepath.relative_to(prefix)
    #             except ValueError:
    #                 continue
    #             if not (filepath.is_file() or filepath.is_symlink()):
    #                 continue
    #             if self._should_exclude(filepath):
    #                 continue
    #
    #             ext = filepath.suffix.lower()
    #             # local and global filters identical to above…
    #             if sel_ext_local == "unsupported":
    #                 if ext in self.ALLOWED_EXTENSIONS:
    #                     continue
    #             elif sel_ext_local and ext not in sel_ext_local:
    #                 continue
    #             if sel_ext_global:
    #                 if sel_ext_global == "unsupported":
    #                     if ext in self.ALLOWED_EXTENSIONS:
    #                         continue
    #                 elif ext not in sel_ext_global:
    #                     continue
    #
    #             # global date filter (resolve symlinks to get real metadata)
    #             fs_path = Path(p)
    #             if fs_path.is_symlink():
    #                 # resolve the link to the real file
    #                 target = fs_path.resolve()
    #                 file_date = self.analyzer.get_date(str(target))
    #             else:
    #                 file_date = self.analyzer.get_date(p)
    #
    #             if file_date is None:
    #                 continue
    #             ts = file_date if isinstance(file_date, (int, float)) else int(file_date.timestamp())
    #             if ts < epoch_start or ts > epoch_end:
    #                 continue
    #
    #             try:
    #                 mtime = filepath.stat().st_mtime
    #             except (OSError, IOError) as e:
    #                 LOGGER.warning(f"Could not read mtime of {filepath}: {e}")
    #                 continue
    #
    #             assets.append({
    #                 "id": str(filepath),
    #                 "time": mtime,
    #                 "filename": filepath.name,
    #                 "filepath": str(filepath),
    #                 "type": self._determine_file_type(filepath),
    #             })
    #
    #         LOGGER.debug(f"{len(assets)} assets in shared album '{album_id}'.")
    #         return assets

    def get_all_assets_without_albums(self, type='all', log_level=logging.WARNING):
        """
        Lists assets that are in self.base_folder but not in self.albums_folder,
        self.shared_albums_folder, or '_Duplicates' folder, with optional filtering by file type.

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
            LOGGER.info(f"Retrieving {type} assets excluding albums, shared albums, _Duplicates, and excluded patterns.")

            # Return cached if already computed
            if self.assets_without_albums_filtered is not None:
                return self.assets_without_albums_filtered

            # Ensure analyzer is initialized (with global filters applied)
            self._ensure_analyzer(log_level=log_level)

            managed_layout = self._uses_managed_layout()
            non_album_roots = [Path(album_root.resolve()) for album_root, _ in self._iter_album_roots()] if managed_layout else []
            duplicates_folder = self.base_folder / "_Duplicates"
            sel_ext = self._get_selected_extensions(type)

            assets = []
            with tqdm(
                total=len(self.analyzer.filtered_file_list),
                desc="🔎 Scanning No-Album Assets",
                unit="file",
                smoothing=0.1,
                dynamic_ncols=True,
                leave=True,
            ) as pbar:
                for p in self.analyzer.filtered_file_list:
                    f = Path(p)
                    # only real files and symlinks should be considered
                    if not (f.is_file() or f.is_symlink()):
                        pbar.update(1)
                        continue

                    if managed_layout:
                        # skip any path under roots that are treated as albums
                        is_album_asset = False
                        for album_root in non_album_roots:
                            try:
                                f.relative_to(album_root)
                                is_album_asset = True
                                break
                            except ValueError:
                                continue
                        if is_album_asset:
                            pbar.update(1)
                            continue
                    else:
                        try:
                            rel = f.resolve().relative_to(self.base_folder.resolve())
                        except ValueError:
                            pbar.update(1)
                            continue
                        # In a plain local folder layout, only files placed directly
                        # under the root are treated as non-album assets.
                        if len(rel.parts) != 1:
                            pbar.update(1)
                            continue
                    # skip any path under _Duplicates
                    try:
                        f.relative_to(duplicates_folder)
                        pbar.update(1)
                        continue
                    except ValueError:
                        pass

                    ext = f.suffix.lower()
                    # local filter by requested type
                    if sel_ext == 'unsupported':
                        if ext in self.ALLOWED_EXTENSIONS:
                            pbar.update(1)
                            continue
                    elif sel_ext is not None and ext not in sel_ext:
                        pbar.update(1)
                        continue

                    # record asset
                    assets.append({
                        'id': str(f),
                        'time': f.stat().st_mtime,
                        'filename': f.name,
                        'filepath': str(f),
                        'type': self._determine_file_type(f),
                    })
                    pbar.update(1)

            # include takeout metadata, sidecar, unsupported files also outside albums
            metadata = [{'id': a['id'], **a} for a in self.get_takeout_assets_by_filters('metadata')]
            sidecar = [{'id': a['id'], **a} for a in self.get_takeout_assets_by_filters('sidecar')]
            unsupported = [{'id': a['id'], **a} for a in self.get_takeout_assets_by_filters('unsupported')]

            all_assets = assets + metadata + sidecar + unsupported

            LOGGER.info(f"Found {len(all_assets)} assets of type '{type}' in No-Album folders (excluding _Duplicates).")
            # cache result for next calls
            self.assets_without_albums_filtered = all_assets
            return all_assets

    # def get_all_assets_without_albums(self, type='all', log_level=logging.WARNING):
    #     """
    #     Lists assets that are in self.base_folder but not in self.albums_folder
    #     or self.shared_albums_folder, with optional filtering by file type.
    #
    #     Args:
    #         type (str): Type of assets to retrieve. Options are 'all', 'photo',
    #                     'image', 'video', 'media', 'metadata', 'sidecar', 'unsupported'.
    #         log_level (int): Logging level.
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
    #         LOGGER.info(f"Retrieving {type} assets excluding albums, shared albums, and excluded patterns.")
    #
    #         # Cache check (same as before)
    #         if self.assets_without_albums_filtered is not None:
    #             return self.assets_without_albums_filtered
    #
    #         albums_folder = self.albums_folder.resolve()
    #         shared_albums_folder = self.shared_albums_folder.resolve()
    #         selected_type_extensions = self._get_selected_extensions(type)
    #
    #         # Initialize the analyzer only once
    #         self._ensure_analyzer(log_level=log_level)
    #
    #         assets = []
    #         for p in self.analyzer.file_list:
    #             f = Path(p)
    #             # Only regular files
    #             if not f.is_file():
    #                 continue
    #             # Pattern exclusion
    #             if self._should_exclude(f):
    #                 continue
    #             # Discard anything inside Albums or Shared
    #             try:
    #                 f.relative_to(albums_folder)
    #                 continue
    #             except ValueError:
    #                 pass
    #             try:
    #                 f.relative_to(shared_albums_folder)
    #                 continue
    #             except ValueError:
    #                 pass
    #
    #             ext = f.suffix.lower()
    #             # Local filter by type (param 'type')
    #             if selected_type_extensions == "unsupported":
    #                 if ext in self.ALLOWED_EXTENSIONS:
    #                     continue
    #             elif selected_type_extensions is not None and ext not in selected_type_extensions:
    #                 continue
    #
    #             assets.append({
    #                 "id": str(f),
    #                 "time": f.stat().st_mtime,
    #                 "filename": f.name,
    #                 "filepath": str(f),
    #                 "type": self._determine_file_type(f),
    #             })
    #
    #         # Apply global filter (self.type, self.from_date, self.to_date)
    #         assets_without_albums = self.filter_assets(assets=assets, log_level=log_level)
    #
    #         # Rest of takeouts as before
    #         takeout_metadata = self.get_takeout_assets_by_filters(type='metadata', log_level=log_level)
    #         takeout_sidecar = self.get_takeout_assets_by_filters(type='sidecar', log_level=log_level)
    #         takeout_unsupported = self.get_takeout_assets_by_filters(type='unsupported', log_level=log_level)
    #
    #         LOGGER.info(f"Found {len(assets_without_albums)} assets of type '{type}' in No-Album folders.")
    #         all_assets = assets_without_albums + takeout_metadata + takeout_sidecar + takeout_unsupported
    #
    #         # Cache for subsequent calls
    #         self.assets_without_albums_filtered = all_assets
    #         return all_assets

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
            all_albums = self.get_albums_including_shared_with_user(log_level=log_level)
            with tqdm(
                total=len(all_albums),
                desc="📚 Gathering Albums Assets",
                unit="album",
                smoothing=0.1,
                dynamic_ncols=True,
                leave=True,
            ) as pbar:
                for album in all_albums:
                    album_id = album["id"]
                    combined_assets.extend(self.get_all_assets_from_album(album_id, log_level))
                    pbar.update(1)
            self.albums_assets_filtered = combined_assets  # Cache albums_assets for future use
            return combined_assets

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None):
        """
        Adds (links) assets to an album using relative symbolic links.
        If symlink creation fails, copies the file instead.
        Updates the FolderAnalyzer caches so no full rescan is needed.
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
                            LOGGER.warning(f"Failed to create symlink {symlink_path}: {e}; copying instead.")
                            try:
                                shutil.copy2(asset_path, symlink_path)
                                LOGGER.info(f"Copied file: {symlink_path}")
                            except Exception as copy_error:
                                LOGGER.error(f"Failed to copy {asset_path} to {symlink_path}: {copy_error}")
                                continue

                        # --- Update analyzer caches (if ya está inicializado)
                        if hasattr(self, 'analyzer') and self.analyzer is not None:
                            new_file = symlink_path.as_posix()
                            # 1) add to raw file_list
                            self.analyzer.file_list.append(new_file)
                            # 2) if pasa filtros globales y locales, añade a filtered_file_list
                            if not self._should_exclude(Path(new_file)):
                                self.analyzer.filtered_file_list.append(new_file)
                                # 3) incrementa el contador de assets para esta carpeta
                                key = Path(album_path.resolve()).as_posix()
                                self.analyzer.folder_assets[key] = self.analyzer.folder_assets.get(key, 0) + 1
                                # 4) incrementa el tamaño
                                size = Path(new_file).stat().st_size
                                self.analyzer.folder_sizes[key] = self.analyzer.folder_sizes.get(key, 0) + size

                        count_added += 1

            LOGGER.info(f"Added {count_added} asset(s) to album '{album_name or album_id}'.")
            return count_added

    # def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None):
    #     """
    #     Adds (links) assets to an album using relative symbolic links. If symlink creation fails, copies the file instead.
    #
    #     Args:
    #         album_id (str): Path to the album folder.
    #         asset_ids (list[str]): List of asset file paths to add.
    #         album_name (str): (Optional) name of the album, for logging only.
    #         log_level (logging.LEVEL): log level for logs and console.
    #
    #     Returns:
    #         int: Number of assets added to the album.
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         LOGGER.info(f"Adding assets to album: {album_name or album_id}")
    #         album_path = Path(album_id)
    #         album_path.mkdir(parents=True, exist_ok=True)
    #         count_added = 0
    #         asset_ids = convert_to_list(asset_ids)
    #
    #         for asset in asset_ids:
    #             asset_path = Path(asset)
    #             if asset_path.exists() and asset_path.is_file():
    #                 symlink_path = album_path / asset_path.name
    #
    #                 if not symlink_path.exists():
    #                     try:
    #                         relative_path = os.path.relpath(asset_path, start=symlink_path.parent)
    #                         symlink_path.symlink_to(relative_path)
    #                         LOGGER.info(f"Created relative symlink: {symlink_path} -> {relative_path}")
    #                     except Exception as e:
    #                         LOGGER.warning(f"Error: {e}")
    #                         LOGGER.warning(f"Failed to create symlink {symlink_path}. Copying a duplicated copy of the file into Album folder instead.")
    #                         try:
    #                             shutil.copy2(asset_path, symlink_path)
    #                             LOGGER.info(f"Copied file: {symlink_path}")
    #                         except Exception as copy_error:
    #                             LOGGER.error(f"Failed to copy file {asset_path} to {symlink_path}. Error: {copy_error}")
    #                             continue
    #                     count_added += 1
    #
    #         LOGGER.info(f"Added {count_added} asset(s) to album '{album_name or album_id}'.")
    #         return count_added

    def get_duplicates_assets(self, log_level=None):
        """
        Returns a list of duplicate assets found in local storage,
        first grouping by size, then confirming by hash.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Searching for duplicate assets in local storage.")
            # Ensure analyzer has built file_sizes cache
            self._ensure_analyzer(log_level=log_level)

            # 1) Group by file size
            size_map = {}
            for file_path, size in self.analyzer.file_sizes.items():
                size_map.setdefault(size, []).append(file_path)

            duplicates = []
            # 2) For each size-group >1, compute hash to confirm duplicates
            for size, group in size_map.items():
                if len(group) < 2:
                    continue

                # secondary grouping by hash
                hash_map = {}
                for path in group:
                    try:
                        # Compute a quick hash (e.g. MD5); you can switch to SHA256 if preferred
                        hasher = hashlib.md5()
                        with open(path, 'rb') as f:
                            # read in chunks to avoid big RAM usage
                            for chunk in iter(lambda: f.read(8192), b''):
                                hasher.update(chunk)
                        digest = hasher.hexdigest()
                    except Exception as e:
                        LOGGER.warning(f"Failed to hash {path}: {e}")
                        continue

                    hash_map.setdefault(digest, []).append(path)

                # collect only real duplicates
                for dup_group in hash_map.values():
                    if len(dup_group) > 1:
                        duplicates.append(dup_group)

            LOGGER.info(f"Found {len(duplicates)} duplicate group(s).")
            return duplicates

    # def get_duplicates_assets(self, log_level=None):
    #     """
    #     Returns a list of duplicate assets found in local storage.
    #
    #     Args:
    #         log_level (logging.LEVEL): log level for logs and console.
    #
    #     Returns:
    #         list[list[str]]: Each element is a list of file paths considered duplicates.
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         LOGGER.info("Searching for duplicate assets in local storage.")
    #         # Ensure analyzer has built file_sizes cache
    #         self._ensure_analyzer(log_level=log_level)
    #
    #         # Use the cached file_sizes from the analyzer to group by size
    #         size_map = {}
    #         for file_path, size in self.analyzer.file_sizes.items():
    #             # file_path is a posix string; keep grouping by its size
    #             size_map.setdefault(size, []).append(file_path)
    #
    #         # Build list of groups where more than one file shares the same size
    #         duplicates = []
    #         for group in size_map.values():
    #             if len(group) > 1:
    #                 duplicates.append(group)
    #
    #         LOGGER.info(f"Found {len(duplicates)} duplicate group(s).")
    #         return duplicates

    def remove_assets(self, asset_ids, log_level=None, refresh_analyzer=True, log_removed_count=True):
        """
        Removes the given asset(s) from local storage.

        Args:
            asset_ids (list[str]): List of absolute file paths to remove.
            log_level (logging.LEVEL): log level for logs and console.
            refresh_analyzer (bool): Rebuild analyzer state after deletion.
            log_removed_count (bool): Emit summary info log with removed count.

        Returns:
            int: Number of assets removed.
        """
        with set_log_level(LOGGER, log_level):
            if isinstance(asset_ids, str):
                asset_ids = [asset_ids]
            count = 0
            removed_paths = []

            # If analyzer isn’t initialized yet, create it so we can rebuild later
            if not hasattr(self, 'analyzer') or self.analyzer is None:
                self._ensure_analyzer(log_level=log_level)

            for asset in asset_ids:
                asset_path = Path(asset)
                if asset_path.exists():
                    if asset_path.is_file() or asset_path.is_symlink():
                        try:
                            asset_path.unlink()
                            count += 1
                            removed_paths.append(asset_path.resolve().as_posix())
                            LOGGER.debug(f"Removed asset: {asset_path}")
                        except Exception as e:
                            LOGGER.warning(f"Failed to remove '{asset_path}': {e}")
                    else:
                        LOGGER.warning(f"Skipped removing '{asset_path}' because it is not a file or symlink.")
                else:
                    LOGGER.warning(f"Asset path does not exist: {asset_path}")

            if log_removed_count:
                LOGGER.info(f"Removed {count} asset(s) from local storage.")

            self._invalidate_asset_caches()

            # Keep extracted_dates consistent even when a full analyzer refresh is skipped.
            if hasattr(self, 'analyzer') and self.analyzer is not None:
                if getattr(self.analyzer, 'extracted_dates', None):
                    for removed_path in removed_paths:
                        self.analyzer.extracted_dates.pop(removed_path, None)

            # Refresh analyzer state from disk so filtered views and sizes
            # reflect the current filesystem after deletions.
            if refresh_analyzer and hasattr(self, 'analyzer') and self.analyzer is not None:
                self.analyzer._build_file_list_from_disk(step_name="remove_assets: ", log_level=log_level)
                self.analyzer._apply_filters(step_name="remove_assets: ", log_level=log_level)
                self.analyzer._compute_folder_sizes(step_name="remove_assets: ", log_level=log_level)

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

            # Determine destination based on file mtime
            mtime = src.stat().st_mtime
            dt_m = datetime.fromtimestamp(mtime)
            year = str(dt_m.year)
            month = str(dt_m.month).zfill(2)

            target_folder = self.no_albums_folder / year / month
            target_folder.mkdir(parents=True, exist_ok=True)

            dest = target_folder / src.name
            if dest.exists():
                # File already there → duplicated
                return str(dest), True
            else:
                # Copy file
                shutil.copy2(src, dest)
                LOGGER.info(f"Uploaded asset '{file_path}' to '{dest}'.")

                # ─── Update analyzer caches ────────────────────────────────────────────
                if hasattr(self, 'analyzer') and self.analyzer:
                    new_path = dest.resolve().as_posix()

                    # 1) file_list
                    self.analyzer.file_list.append(new_path)

                    # 2) filtered_file_list (if exists)
                    if hasattr(self.analyzer, 'filtered_file_list'):
                        self.analyzer.filtered_file_list.append(new_path)

                    # 3) file_sizes
                    size = dest.stat().st_size
                    self.analyzer.file_sizes[new_path] = size

                    # 4) folder_sizes
                    parent = dest.parent.resolve().as_posix()
                    prev = self.analyzer.folder_sizes.get(parent, 0)
                    self.analyzer.folder_sizes[parent] = prev + size

                    # 5) folder_assets (if exists)
                    if hasattr(self.analyzer, 'folder_assets'):
                        prev_count = self.analyzer.folder_assets.get(parent, 0)
                        self.analyzer.folder_assets[parent] = prev_count + 1
                # ────────────────────────────────────────────────────────────────────────

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
        Recursively removes all empty folders in the entire base folder structure
        without rebuilding the entire analyzer.

        Returns:
            int: The number of empty folders removed.
        """
        with set_log_level(LOGGER, log_level):
            if not self.base_folder.exists():
                LOGGER.warning(f"WARN    : Base folder does not exist: {self.base_folder}")
                return 0

            LOGGER.info(f"Looking for empty folders in '{self.base_folder}'...")
            # Ensure analyzer is initialized
            self._ensure_analyzer(log_level=log_level)

            # Build set of all folders that contain at least one file
            occupied = set(Path(p).parent.resolve().as_posix() for p in self.analyzer.file_list)
            removed = 0
            prefixes = []

            # Walk from deepest to root so children are removed before parents
            for folder in sorted(self.base_folder.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if folder.is_dir():
                    folder_str = folder.resolve().as_posix()
                    if folder_str not in occupied:
                        try:
                            folder.rmdir()
                            removed += 1
                            prefixes.append(folder_str)
                            LOGGER.info(f"Removed empty folder: {folder}")
                        except Exception as e:
                            LOGGER.warning(f"WARN    : Could not remove folder '{folder}': {e}")

            # Purge any references under removed folders from analyzer caches
            if removed > 0:
                def keep(path):
                    return not any(path.startswith(pref + "/") for pref in prefixes)

                # file_list
                self.analyzer.file_list = [p for p in self.analyzer.file_list if keep(p)]
                # filtered_file_list
                if hasattr(self.analyzer, 'filtered_file_list'):
                    self.analyzer.filtered_file_list = [p for p in self.analyzer.filtered_file_list if keep(p)]
                # file_sizes
                for pref in prefixes:
                    for p in list(self.analyzer.file_sizes):
                        if p.startswith(pref + "/") or p == pref:
                            del self.analyzer.file_sizes[p]
                # folder_sizes
                for pref in prefixes:
                    for folder in list(self.analyzer.folder_sizes):
                        if folder.startswith(pref + "/") or folder == pref:
                            del self.analyzer.folder_sizes[folder]
                # folder_assets
                if hasattr(self.analyzer, 'folder_assets'):
                    for pref in prefixes:
                        for folder in list(self.analyzer.folder_assets):
                            if folder.startswith(pref + "/") or folder == pref:
                                del self.analyzer.folder_assets[folder]

            LOGGER.info(f"Removed {removed} empty folders.")
            return removed

    def remove_all_albums(self, remove_album_assets=False, log_level=None):
        """
        Removes all album folders. Optionally removes the assets inside them.

        Args:
            remove_album_assets (bool): If True, also delete the files inside each album folder.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            tuple(int, int): (#albums_removed, #assets_removed_if_requested).
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Removing all albums.")

            albums_removed = 0
            assets_removed = 0

            for album in self.albums_folder.iterdir():
                if album.is_dir():
                    # Count assets before removal if requested
                    if remove_album_assets:
                        for file in album.rglob("*"):
                            if file.is_file() or file.is_symlink():
                                try:
                                    file.unlink()
                                    assets_removed += 1
                                except Exception as e:
                                    LOGGER.warning(f"Failed to remove asset {file}: {e}")
                    # Remove the album folder itself
                    try:
                        shutil.rmtree(album)
                        albums_removed += 1
                        LOGGER.info(f"Removed album folder: {album}")
                    except Exception as e:
                        LOGGER.error(f"Failed to remove album folder {album}: {e}")

            # Refresh analyzer so it no longer lists removed albums
            self.analyzer._build_file_list_from_disk(step_name="remove_all_albums: ")
            self.analyzer._compute_folder_sizes(step_name="remove_all_albums: ")

            LOGGER.info(f"Removed {albums_removed} album(s) and {assets_removed} asset(s).")
            return albums_removed, assets_removed

    def remove_empty_albums(self, log_level=None):
        """
        Removes all empty album folders without rebuilding the entire analyzer.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Removing empty albums.")

            # 1) Detect empty albums
            empty_albums = [p for p in self.albums_folder.iterdir() if p.is_dir() and not any(p.iterdir())]
            prefixes = [str(p.resolve().as_posix()) for p in empty_albums]

            # 2) Delete them from disk
            for album in empty_albums:
                shutil.rmtree(album)

            # 3) Purge analyzer caches _in place_ to avoid full rebuild:

            # Remove any file paths under those prefixes
            def keep_path(path):
                return not any(path.startswith(pref + "/") for pref in prefixes)

            # file_list
            self.analyzer.file_list = [p for p in self.analyzer.file_list if keep_path(p)]
            # filtered_file_list (if used)
            if hasattr(self.analyzer, 'filtered_file_list'):
                self.analyzer.filtered_file_list = [p for p in self.analyzer.filtered_file_list if keep_path(p)]
            # file_sizes: drop entries under removed albums
            for pref in prefixes:
                for p in list(self.analyzer.file_sizes):
                    if p.startswith(pref + "/"):
                        del self.analyzer.file_sizes[p]
            # folder_sizes: drop folders under removed albums
            for pref in prefixes:
                for folder in list(self.analyzer.folder_sizes):
                    if folder.startswith(pref + "/") or folder == pref:
                        del self.analyzer.folder_sizes[folder]
            # folder_assets: same as folder_sizes
            if hasattr(self.analyzer, 'folder_assets'):
                for pref in prefixes:
                    for folder in list(self.analyzer.folder_assets):
                        if folder.startswith(pref + "/") or folder == pref:
                            del self.analyzer.folder_assets[folder]

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

            LOGGER.info("Looking for exact duplicate albums in local folders...")
            # Ensure analyzer is ready so we can use its folder_sizes map
            self._ensure_analyzer(log_level=log_level)

            # Group folders by (name, size)
            duplicates_map = defaultdict(list)
            for folder in self.albums_folder.glob("*"):
                if folder.is_dir():
                    album_name = folder.name
                    key = str(folder.resolve())
                    total_size = self.analyzer.folder_sizes.get(key, 0)
                    duplicates_map[(album_name, total_size)].append(folder)

            # Build list of duplicates to remove
            folders_to_remove = []
            for (album_name, total_size), group in duplicates_map.items():
                if len(group) > 1:
                    keeper = group[0]
                    LOGGER.info(f"Keeping folder '{keeper}' with size {total_size} bytes.")
                    for dup_folder in group[1:]:
                        folders_to_remove.append((album_name, total_size, dup_folder))

            if not folders_to_remove:
                LOGGER.info("No exact duplicate albums found.")
                return 0

            LOGGER.info("Folders marked for deletion:")
            for album_name, total_size, dup_folder in folders_to_remove:
                LOGGER.info(f"  '{album_name}' - Size: {total_size} bytes -> {dup_folder}")

            if request_user_confirmation and not confirm_continue():
                LOGGER.info("Exiting program.")
                return 0

            # Remove duplicates
            total_removed = 0
            for album_name, total_size, dup_folder in folders_to_remove:
                try:
                    shutil.rmtree(dup_folder)
                    LOGGER.info(f"Removed duplicate folder: {dup_folder}")
                    total_removed += 1
                except Exception as e:
                    LOGGER.error(f"Failed to remove folder '{dup_folder}': {e}")

            LOGGER.info(f"Removed {total_removed} exact duplicate folders.")

            # --- Update analyzer to reflect folder removals ---
            # Rebuild the in-memory file list and recompute sizes
            self.analyzer._build_file_list_from_disk(step_name="remove_duplicates_albums: ")
            self.analyzer._compute_folder_sizes(step_name="remove_duplicates_albums: ")

            return total_removed

    def merge_duplicates_albums(self, strategy='count', request_user_confirmation=True, log_level=logging.WARNING):
        """
        Merges all duplicate albums in local folders.

        Duplicates are folders with the same name.
        Keeps the folder with the most files or the largest total size (depending on strategy),
        moves all files from the duplicates into it, and deletes the duplicate folders.
        Before merging, displays the planned operations and asks for user confirmation if requested.

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

            LOGGER.info("Searching for duplicate albums in local folders...")
            # Ensure the analyzer has run to populate folder_assets and folder_sizes
            self._ensure_analyzer(log_level=log_level)

            # Group albums by name using in-memory data
            albums_by_name = defaultdict(list)
            for folder in self.albums_folder.iterdir():
                if not folder.is_dir():
                    continue
                album_name = folder.name
                prefix = folder.resolve().as_posix()
                # Retrieve counts and sizes from analyzer caches (filtered list)
                file_count = self.analyzer.folder_assets.get(prefix, 0)
                size = self.analyzer.folder_sizes.get(prefix, 0)
                albums_by_name[album_name].append({
                    "path": folder,
                    "count": file_count,
                    "size": size
                })

            # Plan merges: select keeper and duplicates
            merge_plan = []
            for album_name, group in albums_by_name.items():
                if len(group) <= 1:
                    continue
                # Choose keeper by strategy
                if strategy == 'size':
                    keeper = max(group, key=lambda x: x['size'])
                else:
                    keeper = max(group, key=lambda x: x['count'])
                duplicates = [item['path'] for item in group if item['path'] != keeper['path']]
                merge_plan.append({
                    "album_name": album_name,
                    "keeper_path": keeper['path'],
                    "duplicates": duplicates
                })

            if not merge_plan:
                LOGGER.info("No duplicate albums found.")
                return 0

            # Display plan
            LOGGER.info("Albums to be merged:")
            for item in merge_plan:
                LOGGER.info(f"\nAlbum: '{item['album_name']}'")
                LOGGER.info(f"  Keeper: {item['keeper_path']}")
                for dup in item['duplicates']:
                    LOGGER.info(f"  Duplicate to merge and remove: {dup}")

            # Confirm with user
            if request_user_confirmation and not confirm_continue():
                LOGGER.info("Exiting program.")
                return 0

            total_removed = 0
            # Execute merges
            for item in merge_plan:
                keeper_path = item['keeper_path']
                for dup_path in item['duplicates']:
                    # Move files using analyzer.file_list for faster access
                    prefix = dup_path.resolve().as_posix()
                    for p in self.analyzer.file_list:
                        # Only paths under the duplicate folder
                        if not p.startswith(prefix + '/'):  # ensure trailing slash
                            continue
                        src = Path(p)
                        # Only files and symlinks
                        if not (src.is_file() or src.is_symlink()):
                            continue
                        # Compute relative path within album
                        rel = src.relative_to(dup_path)
                        dst = keeper_path / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if not dst.exists():
                            try:
                                src.rename(dst)
                            except Exception:
                                # fallback: copy and remove
                                shutil.copy2(src, dst)
                                src.unlink()
                        else:
                            LOGGER.warning(f"Skipped moving '{src}' as it already exists at destination.")
                    # Remove the now-empty duplicate folder
                    try:
                        dup_path.rmdir()
                        LOGGER.info(f"Removed duplicate folder: {dup_path}")
                    except Exception:
                        shutil.rmtree(dup_path)
                        LOGGER.info(f"Removed duplicate folder and its contents: {dup_path}")
                    total_removed += 1

            # after merging and deleting folders…
            # Refresh the analyzer so it rescans y recompute los índices
            self.analyzer._build_file_list_from_disk(step_name="merge_duplicates_albums: ")
            self.analyzer._compute_folder_sizes(step_name="merge_duplicates_albums: ")

            LOGGER.info(f"Removed {total_removed} duplicate folders.")
            return total_removed

    # def merge_duplicates_albums(self, strategy='count', request_user_confirmation=True, log_level=logging.WARNING):
    #     """
    #     Merges all duplicate albums in local folders.
    #
    #     Duplicates are folders with the same name.
    #     The function keeps the folder with the most files or the largest total size (depending on strategy),
    #     moves all files from the duplicates into it, and deletes the duplicate folders.
    #     Before merging, it displays the planned operations and asks for user confirmation if requested.
    #
    #     Args:
    #         strategy (str): 'count' to keep the album with the most files, 'size' to keep the album with the largest size.
    #         request_user_confirmation (bool): Whether to ask for confirmation before merging.
    #         log_level (logging.LEVEL): The log level for logging and console output.
    #
    #     Returns:
    #         int: The number of duplicate folders deleted.
    #     """
    #     with set_log_level(LOGGER, log_level):
    #         from collections import defaultdict
    #
    #         if not self.albums_folder.exists():
    #             LOGGER.warning(f"Albums folder does not exist: {self.albums_folder}")
    #             return 0
    #
    #         LOGGER.info(f"Searching for duplicate albums in local folders...")
    #         # Initialize the analyzer if needed
    #         self._ensure_analyzer(log_level=log_level)
    #
    #         # Group albums by name using in-memory data
    #         albums_by_name = defaultdict(list)
    #         for folder in self.albums_folder.glob("*"):
    #             if folder.is_dir():
    #                 album_name = folder.name
    #                 prefix = str(folder.resolve())
    #                 file_count = 0
    #                 for p in self.analyzer.file_list:
    #                     file = Path(p)
    #                     try:
    #                         file.relative_to(prefix)
    #                     except ValueError:
    #                         continue
    #                     if file.is_file():
    #                         file_count += 1
    #                 size = self.analyzer.folder_sizes.get(prefix, 0)
    #                 albums_by_name[album_name].append({
    #                     "path": folder,
    #                     "count": file_count,
    #                     "size": size
    #                 })
    #
    #         merge_plan = []
    #         for album_name, group in albums_by_name.items():
    #             if len(group) <= 1:
    #                 continue
    #             if strategy == 'size':
    #                 keeper = sorted(group, key=lambda x: x['size'], reverse=True)[0]
    #             else:
    #                 keeper = sorted(group, key=lambda x: x['count'], reverse=True)[0]
    #             duplicates = [item["path"] for item in group if item["path"] != keeper["path"]]
    #             merge_plan.append({
    #                 "album_name": album_name,
    #                 "keeper_path": keeper["path"],
    #                 "duplicates": duplicates
    #             })
    #
    #         if not merge_plan:
    #             LOGGER.info(f"No duplicate albums found.")
    #             return 0
    #
    #         LOGGER.info(f"Albums to be merged:")
    #         for item in merge_plan:
    #             LOGGER.info(f"\nAlbum: '{item['album_name']}'")
    #             LOGGER.info(f"  Keeper: {item['keeper_path']}")
    #             for dup in item["duplicates"]:
    #                 LOGGER.info(f"  Duplicate to merge and remove: {dup}")
    #
    #         if request_user_confirmation and not confirm_continue():
    #             LOGGER.info(f"Exiting program.")
    #             return 0
    #
    #         total_removed = 0
    #         for item in merge_plan:
    #             keeper_path = item["keeper_path"]
    #             for dup_path in item["duplicates"]:
    #                 for f in self.analyzer.file_list:
    #                     if f.startswith(str(dup_path.resolve()) + os.sep):
    #                         file = Path(f)
    #                         if file.is_file():
    #                             rel = file.relative_to(dup_path)
    #                             target = keeper_path / rel
    #                             target.parent.mkdir(parents=True, exist_ok=True)
    #                             if not target.exists():
    #                                 file.rename(target)
    #                             else:
    #                                 LOGGER.warning(f"Skipped moving '{file}' as it already exists at destination.")
    #                 try:
    #                     dup_path.rmdir()
    #                     total_removed += 1
    #                     LOGGER.info(f"Removed duplicate folder: {dup_path}")
    #                 except OSError:
    #                     shutil.rmtree(dup_path)
    #                     total_removed += 1
    #                     LOGGER.info(f"Removed duplicate folder and its contents: {dup_path}")
    #
    #         LOGGER.info(f"Removed {total_removed} duplicate folders.")
    #         return total_removed

    def remove_orphan_assets(self, user_confirmation=True, log_level=logging.WARNING):
        """
        Removes orphan assets in local storage (broken symlinks in album folders).

        Args:
            user_confirmation (bool): If True, request user confirmation before deletion.
            log_level (logging.LEVEL): log level for logs and console.

        Returns:
            int: Number of orphan assets removed.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Removing orphan assets (broken symlinks) in albums.")

            # 1) Find broken symlinks under albums_folder
            orphans = []
            for dirpath, _, files in os.walk(self.albums_folder, followlinks=False):
                for name in files:
                    link = Path(dirpath) / name
                    if link.is_symlink():
                        target = link.resolve(strict=False)
                        if not target.exists():
                            orphans.append(link.as_posix())

            if not orphans:
                LOGGER.info("No orphan assets found.")
                return 0

            LOGGER.info(f"Found {len(orphans)} orphan assets:")
            for p in orphans:
                LOGGER.info(f"  {p}")

            # 2) Confirm
            if user_confirmation and not confirm_continue():
                LOGGER.info("Exiting without removing orphan assets.")
                return 0

            # 3) Remove them
            removed = 0
            for p in orphans:
                try:
                    Path(p).unlink()
                    LOGGER.info(f"Removed orphan asset: {p}")
                    removed += 1
                except Exception as e:
                    LOGGER.error(f"Failed to remove orphan asset {p}: {e}")

            # 4) Cleanup analyzer caches (no full rebuild)
            if hasattr(self, 'analyzer'):
                # Helper to filter out any path under a removed link
                prefixes = set(Path(p).parent.resolve().as_posix() for p in orphans)

                def keep_fp(fp):
                    return fp not in orphans and not any(fp.startswith(pref + "/") for pref in prefixes)

                # file_list and filtered_file_list
                self.analyzer.file_list = [fp for fp in self.analyzer.file_list if keep_fp(fp)]
                if hasattr(self.analyzer, 'filtered_file_list'):
                    self.analyzer.filtered_file_list = [fp for fp in self.analyzer.filtered_file_list if keep_fp(fp)]

                # file_sizes
                for fp in list(self.analyzer.file_sizes):
                    if not keep_fp(fp):
                        del self.analyzer.file_sizes[fp]

                # folder_sizes
                for folder in list(self.analyzer.folder_sizes):
                    if any(folder == pref or folder.startswith(pref + "/") for pref in prefixes):
                        del self.analyzer.folder_sizes[folder]

                # folder_assets
                if hasattr(self.analyzer, 'folder_assets'):
                    for folder in list(self.analyzer.folder_assets):
                        if any(folder == pref or folder.startswith(pref + "/") for pref in prefixes):
                            del self.analyzer.folder_assets[folder]

            LOGGER.info(f"Removed {removed} orphan asset(s).")
            return removed

    ###########################################################################
    #                     REMOVE ALL ASSETS / ALL ALBUMS                      #
    ###########################################################################
    def remove_all_assets(self, log_level=logging.WARNING):
        """
        Removes all assets from local storage (both in <ALBUMS_FOLDER> and <NO_ALBUMS_FOLDER>).

        Returns:
            int: Number of assets removed.
        """
        with set_log_level(LOGGER, log_level):
            LOGGER.info("Removing all assets (symlinks in albums + files in no-albums).")

            assets_removed = 0

            # 1) Remove all symlinks inside each album folder
            for album_folder in (self.albums_folder, self.shared_albums_folder):
                for entry in album_folder.iterdir():
                    # only files or symlinks (ignore subfolders)
                    if entry.is_symlink() or entry.is_file():
                        try:
                            entry.unlink()
                            assets_removed += 1
                            LOGGER.debug(f"Removed album asset: {entry}")
                        except Exception as e:
                            LOGGER.warning(f"Failed to remove {entry}: {e}")

            # 2) Remove all real files that are not in any album
            #    We use get_all_assets_without_albums to respect filters
            no_album_assets = self.get_all_assets_without_albums(type='all', log_level=log_level)
            for asset in no_album_assets:
                fp = Path(asset['filepath'])
                if fp.exists():
                    try:
                        fp.unlink()
                        assets_removed += 1
                        LOGGER.debug(f"Removed no-album asset: {fp}")
                    except Exception as e:
                        LOGGER.warning(f"Failed to remove {fp}: {e}")

            # 3) Refresh analyzer state
            #    Rebuild file list and recompute sizes so it no longer sees removed assets
            self.analyzer._build_file_list_from_disk(step_name="remove_all_assets: ")
            self.analyzer._compute_folder_sizes(step_name="remove_all_assets: ")

            LOGGER.info(f"Removed {assets_removed} asset(s) in total.")
            return assets_removed


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
