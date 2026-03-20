import logging
import os
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests

from Core import GlobalVariables as GV
from Core.ConfigReader import load_config
from Core.CustomLogger import set_log_level
from Core.GlobalVariables import (
    CONFIGURATION_FILE,
    FOLDERNAME_ALBUMS,
    FOLDERNAME_NO_ALBUMS,
    LOGGER,
    MSG_TAGS,
    PHOTO_EXT,
    VIDEO_EXT,
)
from Utils.FileUtils import get_all_files_paths, get_subfolders
from Utils.GeneralUtils import confirm_continue, convert_to_list, match_pattern, replace_pattern, tqdm, update_metadata


class ClassNextCloudPhotos:
    def __init__(self, account_id: int = 1):
        self.account_id = int(account_id or 1)
        self.base_url = ""
        self.username = ""
        self.password = ""
        self.webdav_root = ""
        self.client_name = "NextCloud Photos"
        self.albums_root_name = FOLDERNAME_ALBUMS
        self.no_albums_root_name = FOLDERNAME_NO_ALBUMS
        self.session: Optional[requests.Session] = None
        self.timeout_seconds = 60
        self.ALLOWED_PHOTO_EXTENSIONS = [ext.lower() for ext in PHOTO_EXT]
        self.ALLOWED_VIDEO_EXTENSIONS = [ext.lower() for ext in VIDEO_EXT]

    def get_client_name(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return self.client_name

    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            config = load_config(config_file=config_file, section_to_load="NextCloud Photos")
            section = config.get("NextCloud Photos", {})
            suffix = str(self.account_id)
            self.base_url = section.get("NEXTCLOUD_URL", "").strip().rstrip("/")
            self.username = section.get(f"NEXTCLOUD_USERNAME_{suffix}", "").strip()
            self.password = section.get(f"NEXTCLOUD_PASSWORD_{suffix}", "").strip()
            self.webdav_root = section.get(f"NEXTCLOUD_WEBDAV_ROOT_{suffix}", "/Photos").strip() or "/Photos"
            if not self.webdav_root.startswith("/"):
                self.webdav_root = f"/{self.webdav_root}"
            self.webdav_root = re.sub(r"/+", "/", self.webdav_root.rstrip("/"))

            if not self.base_url:
                raise ValueError("Missing NEXTCLOUD_URL in [NextCloud Photos]")
            if not self.username:
                raise ValueError(f"Missing NEXTCLOUD_USERNAME_{suffix} in [NextCloud Photos]")
            if not self.password:
                raise ValueError(f"Missing NEXTCLOUD_PASSWORD_{suffix} in [NextCloud Photos]")

    def login(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.read_config_file(config_file=config_file, log_level=log_level)
            self.session = requests.Session()
            self.session.auth = (self.username, self.password)
            self.session.headers.update({"User-Agent": f"{GV.TOOL_NAME}/{GV.TOOL_VERSION_WITHOUT_V}"})
            self._ensure_dir("/")
            self._ensure_dir(self._albums_root())
            self._ensure_dir(self._no_albums_root())
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged in to NextCloud account {self.account_id}.")
            return True

    def logout(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if self.session is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
            self.session = None
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged out from NextCloud account {self.account_id}.")
            return True

    def _require_session(self):
        if self.session is None:
            raise RuntimeError("NextCloud session is not initialized. Call login() first.")

    def _dav_url(self, remote_path: str) -> str:
        clean = str(remote_path or "").replace("\\", "/")
        clean = re.sub(r"/+", "/", clean).strip()
        if not clean.startswith("/"):
            clean = f"/{clean}"
        root = f"/remote.php/dav/files/{quote(self.username, safe='')}"
        full = f"{root}{quote(clean, safe='/._-() ')}"
        full = full.replace(" ", "%20")
        return urljoin(f"{self.base_url}/", full.lstrip("/"))

    def _request(self, method: str, remote_path: str, expected=(200, 201, 204, 207), **kwargs):
        self._require_session()
        url = self._dav_url(remote_path)
        response = self.session.request(method=method, url=url, timeout=self.timeout_seconds, **kwargs)
        if response.status_code not in expected:
            raise RuntimeError(
                f"NextCloud WebDAV {method} failed for '{remote_path}' "
                f"(status={response.status_code}, body={response.text[:350]})"
            )
        return response

    def _albums_root(self) -> str:
        return f"{self.webdav_root}/{self.albums_root_name}"

    def _no_albums_root(self) -> str:
        return f"{self.webdav_root}/{self.no_albums_root_name}"

    def _is_photo(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.ALLOWED_PHOTO_EXTENSIONS

    def _is_video(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in self.ALLOWED_VIDEO_EXTENSIONS

    def _is_supported_media(self, filename: str) -> bool:
        return self._is_photo(filename) or self._is_video(filename)

    def _parse_iso_datetime(self, text: str) -> str:
        try:
            dt = datetime.strptime(text, "%a, %d %b %Y %H:%M:%S %Z")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def _split_relative_from_href(self, href: str) -> str:
        marker = f"/remote.php/dav/files/{self.username}"
        idx = href.find(marker)
        if idx < 0:
            return "/"
        rel = href[idx + len(marker):]
        rel = rel or "/"
        return rel

    def _propfind(self, remote_path: str, depth: int = 1) -> List[Dict[str, str]]:
        xml_body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop>'
            "<d:resourcetype/><d:getcontentlength/><d:getlastmodified/>"
            "</d:prop></d:propfind>"
        )
        response = self._request(
            "PROPFIND",
            remote_path,
            expected=(207,),
            headers={"Depth": str(depth), "Content-Type": "application/xml"},
            data=xml_body,
        )
        root = ET.fromstring(response.text)
        ns = {"d": "DAV:"}
        items: List[Dict[str, str]] = []
        for item in root.findall("d:response", ns):
            href_node = item.find("d:href", ns)
            propstat = item.find("d:propstat", ns)
            if href_node is None or propstat is None:
                continue
            prop = propstat.find("d:prop", ns)
            if prop is None:
                continue
            resource_type = prop.find("d:resourcetype", ns)
            collection = resource_type.find("d:collection", ns) if resource_type is not None else None
            content_length = prop.find("d:getcontentlength", ns)
            last_modified = prop.find("d:getlastmodified", ns)
            href = href_node.text or ""
            rel_path = self._split_relative_from_href(href)
            name = Path(rel_path.rstrip("/")).name
            items.append(
                {
                    "href": href,
                    "path": rel_path,
                    "name": name,
                    "is_dir": "true" if collection is not None else "false",
                    "size": (content_length.text or "0") if content_length is not None else "0",
                    "last_modified": (last_modified.text or "") if last_modified is not None else "",
                }
            )
        return items

    def _exists(self, remote_path: str) -> bool:
        self._require_session()
        url = self._dav_url(remote_path)
        response = self.session.request("HEAD", url, timeout=self.timeout_seconds)
        return response.status_code in (200, 204)

    def _ensure_dir(self, remote_path: str):
        normalized = re.sub(r"/+", "/", str(remote_path or "/")).rstrip("/")
        if normalized == "":
            normalized = "/"
        current = ""
        for part in normalized.split("/"):
            if part == "":
                continue
            current = f"{current}/{part}"
            if not self._exists(current):
                self._request("MKCOL", current, expected=(201, 405))

    def _iter_files_recursive(self, remote_path: str) -> Iterable[Dict[str, str]]:
        stack = [remote_path]
        while stack:
            current = stack.pop()
            entries = self._propfind(current, depth=1)
            for entry in entries:
                p = entry["path"]
                if p.rstrip("/") == current.rstrip("/"):
                    continue
                if entry["is_dir"] == "true":
                    stack.append(p)
                else:
                    yield entry

    def _asset_type_from_name(self, name: str) -> str:
        if self._is_video(name):
            return "video"
        return "photo"

    def _remote_parent(self, remote_path: str) -> str:
        p = Path(str(remote_path).replace("\\", "/"))
        parent = str(p.parent).replace("\\", "/")
        if not parent.startswith("/"):
            parent = f"/{parent}"
        return parent

    def _upload_file(self, local_path: str, remote_path: str) -> str:
        self._ensure_dir(self._remote_parent(remote_path))
        with open(local_path, "rb") as fp:
            self._request("PUT", remote_path, expected=(200, 201, 204), data=fp)
        return remote_path

    def _download_file(self, remote_path: str, local_path: str) -> str:
        self._ensure_local_parent(local_path)
        response = self._request("GET", remote_path, expected=(200, 206), stream=True)
        with open(local_path, "wb") as fp:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fp.write(chunk)
        return local_path

    def _ensure_local_parent(self, local_path: str):
        parent = os.path.dirname(local_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _remove_remote(self, remote_path: str) -> bool:
        if not self._exists(remote_path):
            return False
        self._request("DELETE", remote_path, expected=(200, 204))
        return True

    def _copy_remote(self, source_remote_path: str, destination_remote_path: str):
        self._ensure_dir(self._remote_parent(destination_remote_path))
        destination_url = self._dav_url(destination_remote_path)
        self._request(
            "COPY",
            source_remote_path,
            expected=(201, 204),
            headers={"Destination": destination_url, "Overwrite": "T"},
        )

    def _list_album_directories(self, log_level=None) -> List[Dict[str, str]]:
        with set_log_level(LOGGER, log_level):
            albums_root = self._albums_root()
            entries = self._propfind(albums_root, depth=1)
            albums = []
            for entry in entries:
                if entry["path"].rstrip("/") == albums_root.rstrip("/"):
                    continue
                if entry["is_dir"] != "true":
                    continue
                albums.append({"id": entry["path"], "albumName": entry["name"]})
            albums.sort(key=lambda a: a["albumName"].lower())
            return albums

    def _build_asset_payload(self, remote_path: str, name: str, last_modified: str) -> Dict[str, str]:
        return {
            "id": remote_path,
            "filename": name,
            "asset_datetime": self._parse_iso_datetime(last_modified),
            "type": self._asset_type_from_name(name),
        }

    def create_album(self, album_name: str, log_level=None):
        with set_log_level(LOGGER, log_level):
            target = f"{self._albums_root()}/{album_name}".replace("//", "/")
            self._ensure_dir(target)
            return target

    def remove_album(self, album_id, album_name=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            return self._remove_remote(str(album_id))

    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        return self._list_album_directories(log_level=log_level)

    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        return self._list_album_directories(log_level=log_level)

    def get_album_assets_size(self, album_id, type="all", log_level=None):
        with set_log_level(LOGGER, log_level):
            assets = self.get_all_assets_from_album(album_id=album_id, type=type, log_level=log_level)
            return len(assets)

    def get_album_assets_count(self, album_id, log_level=None):
        return self.get_album_assets_size(album_id=album_id, type="all", log_level=log_level)

    def album_exists(self, album_name, log_level=None):
        with set_log_level(LOGGER, log_level):
            albums = self._list_album_directories(log_level=log_level)
            for album in albums:
                if album["albumName"].lower() == str(album_name).lower():
                    return True, album["id"]
            return False, None

    def get_assets_by_filters(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
            entries = list(self._iter_files_recursive(self.webdav_root))
            assets = []
            for entry in entries:
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename):
                    continue
                assets.append(self._build_asset_payload(entry["path"], filename, entry.get("last_modified", "")))
            return assets

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
            assets = []
            for entry in self._iter_files_recursive(str(album_id)):
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename):
                    continue
                payload = self._build_asset_payload(entry["path"], filename, entry.get("last_modified", ""))
                payload["album_name"] = album_name or Path(str(album_id).rstrip("/")).name
                assets.append(payload)
            return assets

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, log_level=logging.WARNING):
        return self.get_all_assets_from_album(album_id=album_id, album_name=album_name, type=type, log_level=log_level)

    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
            assets = []
            for entry in self._iter_files_recursive(self._no_albums_root()):
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename):
                    continue
                assets.append(self._build_asset_payload(entry["path"], filename, entry.get("last_modified", "")))
            return assets

    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            all_assets: List[Dict[str, str]] = []
            for album in self._list_album_directories(log_level=log_level):
                all_assets.extend(self.get_all_assets_from_album(album_id=album["id"], album_name=album["albumName"], log_level=log_level))
            return all_assets

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            if isinstance(asset_ids, str):
                assets = [asset_ids]
            else:
                assets = list(asset_ids or [])
            added = 0
            for asset_id in assets:
                src = str(asset_id)
                name = Path(src).name
                dst = f"{str(album_id).rstrip('/')}/{name}"
                try:
                    self._copy_remote(src, dst)
                    added += 1
                except Exception as error:
                    LOGGER.warning(f"{MSG_TAGS['WARNING']}Unable to add asset '{src}' to album '{album_id}': {error}")
            return added

    def get_duplicates_assets(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return []

    def remove_assets(self, asset_ids, log_level=None):
        with set_log_level(LOGGER, log_level):
            if isinstance(asset_ids, str):
                asset_ids = [asset_ids]
            removed = 0
            for asset_id in asset_ids or []:
                if self._remove_remote(str(asset_id)):
                    removed += 1
            return removed

    def remove_duplicates_assets(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return 0

    def push_asset(self, file_path, log_level=None):
        with set_log_level(LOGGER, log_level):
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            remote_path = f"{self._no_albums_root().rstrip('/')}/{os.path.basename(file_path)}"
            remote_path = self._upload_file(file_path, remote_path)
            return remote_path, False

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_NextCloud", album_passphrase=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            os.makedirs(download_folder, exist_ok=True)
            output_file = os.path.join(download_folder, str(asset_filename))
            output_file = self._download_file(str(asset_id), output_file)
            update_metadata(file_path=output_file, date_time=asset_time, log_level=log_level)
            return output_file

    def push_albums(self, input_folder, subfolders_exclusion=FOLDERNAME_NO_ALBUMS, remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            if not os.path.isdir(input_folder):
                raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

            subfolders = get_subfolders(input_folder=input_folder, exclusion_subfolders=[subfolders_exclusion], log_level=log_level)
            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_duplicates_skipped = 0
            for folder in tqdm(subfolders, desc=f"{MSG_TAGS['INFO']}Uploading Albums to NextCloud", unit=" album"):
                album_name = os.path.basename(folder)
                media_files = [f for f in get_all_files_paths(folder) if self._is_supported_media(f)]
                if not media_files:
                    total_albums_skipped += 1
                    continue
                exists, album_id = self.album_exists(album_name=album_name, log_level=log_level)
                if not exists or not album_id:
                    album_id = self.create_album(album_name=album_name, log_level=log_level)
                    total_albums_uploaded += 1
                for file_path in media_files:
                    remote_file = f"{str(album_id).rstrip('/')}/{os.path.basename(file_path)}"
                    if self._exists(remote_file):
                        total_duplicates_skipped += 1
                        continue
                    self._upload_file(file_path, remote_file)
                    total_assets_uploaded += 1
            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, 0, total_duplicates_skipped

    def push_no_albums(self, input_folder, subfolders_exclusion=f"{FOLDERNAME_ALBUMS}", remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            files = [f for f in get_all_files_paths(input_folder=input_folder, exclusion_folders=subfolders_exclusion) if self._is_supported_media(f)]
            uploaded = 0
            duplicates = 0
            for file_path in tqdm(files, desc=f"{MSG_TAGS['INFO']}Uploading Assets without Albums to NextCloud", unit=" asset"):
                remote_file = f"{self._no_albums_root().rstrip('/')}/{os.path.basename(file_path)}"
                if self._exists(remote_file):
                    duplicates += 1
                    continue
                self._upload_file(file_path, remote_file)
                uploaded += 1
            return uploaded, duplicates

    def push_ALL(self, input_folder, albums_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            albums_folders = convert_to_list(albums_folders, log_level=log_level)
            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_assets_uploaded_within_albums = 0
            total_assets_uploaded_without_albums = 0
            total_duplicates_assets_skipped = 0

            if albums_folders:
                for albums_folder in albums_folders:
                    if not albums_folder:
                        continue
                    abs_folder = albums_folder if os.path.isabs(albums_folder) else os.path.join(input_folder, albums_folder)
                    if not os.path.isdir(abs_folder):
                        continue
                    a_up, a_skip, assets_up, _, dup_skip = self.push_albums(abs_folder, subfolders_exclusion="", remove_duplicates=remove_duplicates, log_level=log_level)
                    total_albums_uploaded += a_up
                    total_albums_skipped += a_skip
                    total_assets_uploaded_within_albums += assets_up
                    total_duplicates_assets_skipped += dup_skip
            else:
                default_albums = os.path.join(input_folder, self.albums_root_name)
                if os.path.isdir(default_albums):
                    a_up, a_skip, assets_up, _, dup_skip = self.push_albums(default_albums, subfolders_exclusion="", remove_duplicates=remove_duplicates, log_level=log_level)
                    total_albums_uploaded += a_up
                    total_albums_skipped += a_skip
                    total_assets_uploaded_within_albums += assets_up
                    total_duplicates_assets_skipped += dup_skip

            uploaded_no_albums, duplicates_no_albums = self.push_no_albums(
                input_folder=input_folder,
                subfolders_exclusion=self.albums_root_name,
                remove_duplicates=remove_duplicates,
                log_level=log_level,
            )
            total_assets_uploaded_without_albums += uploaded_no_albums
            total_duplicates_assets_skipped += duplicates_no_albums
            total_assets_uploaded = total_assets_uploaded_within_albums + total_assets_uploaded_without_albums
            return (
                total_albums_uploaded,
                total_albums_skipped,
                total_assets_uploaded,
                total_assets_uploaded_within_albums,
                total_assets_uploaded_without_albums,
                0,
                total_duplicates_assets_skipped,
            )

    def _download_remote_folder(self, remote_folder: str, local_folder: str, log_level=None) -> int:
        downloaded = 0
        for entry in self._iter_files_recursive(remote_folder):
            rel = str(entry["path"]).replace(str(remote_folder).rstrip("/") + "/", "")
            target = os.path.join(local_folder, rel.replace("/", os.sep))
            self._download_file(entry["path"], target)
            downloaded += 1
        return downloaded

    def pull_albums(self, albums_name="ALL", output_folder="Downloads_NextCloud", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target_names = [n.lower() for n in convert_to_list(albums_name, log_level=log_level)] if albums_name != "ALL" else ["all"]
            albums = self._list_album_directories(log_level=log_level)
            downloaded_albums = 0
            downloaded_assets = 0
            root = os.path.join(output_folder, self.albums_root_name)
            os.makedirs(root, exist_ok=True)
            for album in albums:
                name = album["albumName"]
                if "all" not in target_names:
                    if not any(match_pattern(name, pattern) for pattern in target_names):
                        continue
                local_album = os.path.join(root, name)
                downloaded_assets += self._download_remote_folder(album["id"], local_album, log_level=log_level)
                downloaded_albums += 1
            return downloaded_albums, downloaded_assets

    def pull_no_albums(self, output_folder="Downloads_NextCloud", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target = os.path.join(output_folder, self.no_albums_root_name)
            os.makedirs(target, exist_ok=True)
            return self._download_remote_folder(self._no_albums_root(), target, log_level=log_level)

    def pull_ALL(self, output_folder="Downloads_NextCloud", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            albums_downloaded, assets_in_albums = self.pull_albums(albums_name="ALL", output_folder=output_folder, log_level=log_level)
            assets_without_albums = self.pull_no_albums(output_folder=output_folder, log_level=log_level)
            total_assets = assets_in_albums + assets_without_albums
            return albums_downloaded, total_assets, assets_in_albums, assets_without_albums

    def remove_empty_folders(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return 0

    def remove_all_albums(self, removeAlbumsAssets=False, log_level=None):
        with set_log_level(LOGGER, log_level):
            albums = self._list_album_directories(log_level=log_level)
            removed_albums = 0
            removed_assets = 0
            for album in albums:
                if removeAlbumsAssets:
                    removed_assets += len(self.get_all_assets_from_album(album["id"], log_level=log_level))
                if self._remove_remote(album["id"]):
                    removed_albums += 1
            return removed_albums, removed_assets

    def remove_empty_albums(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            removed = 0
            for album in self._list_album_directories(log_level=log_level):
                assets = self.get_all_assets_from_album(album["id"], log_level=log_level)
                if not assets and self._remove_remote(album["id"]):
                    removed += 1
            return removed

    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            return 0

    def merge_duplicates_albums(self, strategy="count", request_user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            return 0, 0

    def remove_orphan_assets(self, user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['INFO']}NextCloud does not expose orphan-assets semantics like Immich. No action applied.")
            return 0

    def remove_all_assets(self, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            assets_in_albums = self.get_all_assets_from_all_albums(log_level=log_level)
            assets_no_albums = self.get_all_assets_without_albums(log_level=log_level)
            total_assets = 0
            for asset in assets_in_albums + assets_no_albums:
                if self._remove_remote(asset["id"]):
                    total_assets += 1
            albums_removed, _ = self.remove_all_albums(removeAlbumsAssets=False, log_level=log_level)
            return total_assets, albums_removed

    def rename_albums(self, pattern, pattern_to_replace, log_level=None):
        with set_log_level(LOGGER, log_level):
            renamed = 0
            for album in self._list_album_directories(log_level=log_level):
                old_name = album["albumName"]
                if not match_pattern(old_name, pattern):
                    continue
                new_name = replace_pattern(old_name, pattern, pattern_to_replace)
                if not new_name or new_name == old_name:
                    continue
                src = album["id"]
                dst = f"{self._albums_root().rstrip('/')}/{new_name}"
                try:
                    destination_url = self._dav_url(dst)
                    self._request("MOVE", src, expected=(201, 204), headers={"Destination": destination_url, "Overwrite": "F"})
                    renamed += 1
                except Exception as error:
                    LOGGER.warning(f"{MSG_TAGS['WARNING']}Failed to rename album '{old_name}' -> '{new_name}': {error}")
            return renamed

    def remove_albums_by_name(self, pattern, removeAlbumsAssets=False, log_level=None):
        with set_log_level(LOGGER, log_level):
            removed_albums = 0
            removed_assets = 0
            for album in self._list_album_directories(log_level=log_level):
                if not match_pattern(album["albumName"], pattern):
                    continue
                if removeAlbumsAssets:
                    removed_assets += len(self.get_all_assets_from_album(album["id"], log_level=log_level))
                if self._remove_remote(album["id"]):
                    removed_albums += 1
            return removed_albums, removed_assets

