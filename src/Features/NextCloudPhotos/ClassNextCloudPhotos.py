import logging
import os
import re
import shutil
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urljoin

import requests
from requests.adapters import HTTPAdapter

from Core import GlobalVariables as GV
from Core.ConfigReader import load_config
from Core.CustomLogger import set_log_level
from Core.GlobalVariables import (
    ARGS,
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
        self.max_parallel_uploads = 12
        self.use_system_proxy = False
        self._worker_local = threading.local()
        self.ALLOWED_PHOTO_EXTENSIONS = [ext.lower() for ext in PHOTO_EXT]
        self.ALLOWED_VIDEO_EXTENSIONS = [ext.lower() for ext in VIDEO_EXT]
        self.type = ARGS.get("filter-by-type", None)
        self.from_date = ARGS.get("filter-from-date", None)
        self.to_date = ARGS.get("filter-to-date", None)
        self.country = ARGS.get("filter-by-country", None)
        self.city = ARGS.get("filter-by-city", None)
        self.person = ARGS.get("filter-by-person", None)
        self._warned_unsupported_filters = False

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
            raw_parallel = section.get(
                f"NEXTCLOUD_MAX_PARALLEL_UPLOADS_{suffix}",
                section.get("NEXTCLOUD_MAX_PARALLEL_UPLOADS", str(self.max_parallel_uploads)),
            )
            raw_use_proxy = section.get(
                f"NEXTCLOUD_USE_SYSTEM_PROXY_{suffix}",
                section.get("NEXTCLOUD_USE_SYSTEM_PROXY", str(self.use_system_proxy)),
            )
            try:
                self.max_parallel_uploads = max(1, min(32, int(str(raw_parallel).strip())))
            except Exception:
                self.max_parallel_uploads = 12
            self.use_system_proxy = str(raw_use_proxy).strip().lower() in {"1", "true", "yes", "y", "on"}
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
            self.session = self._build_session()
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
        # Normalize to a decoded path first to avoid double-encoding (%2520, etc.)
        clean = unquote(str(remote_path or "").replace("\\", "/"))
        clean = re.sub(r"/+", "/", clean).strip()
        if not clean.startswith("/"):
            clean = f"/{clean}"
        root = f"/remote.php/dav/files/{quote(self.username, safe='')}"
        full = f"{root}{quote(clean, safe='/._-() ')}"
        full = full.replace(" ", "%20")
        return urljoin(f"{self.base_url}/", full.lstrip("/"))

    def _photos_dav_url(self, remote_path: str) -> str:
        # Normalize to a decoded path first to avoid double-encoding (%2520, etc.)
        clean = unquote(str(remote_path or "").replace("\\", "/"))
        clean = re.sub(r"/+", "/", clean).strip()
        if not clean.startswith("/"):
            clean = f"/{clean}"
        root = f"/remote.php/dav/photos/{quote(self.username, safe='')}"
        full = f"{root}{quote(clean, safe='/._-() ')}"
        full = full.replace(" ", "%20")
        return urljoin(f"{self.base_url}/", full.lstrip("/"))

    def _request_url(self, method: str, url: str, expected=(200, 201, 204, 207), **kwargs):
        self._require_session()
        response = self.session.request(method=method, url=url, timeout=self.timeout_seconds, **kwargs)
        if response.status_code not in expected:
            if int(response.status_code) == 401:
                raise RuntimeError(
                    "NextCloud authentication failed (401 Unauthorized). "
                    "Check NEXTCLOUD_URL, username/password (or app password), and WebDAV permissions."
                )
            raise RuntimeError(
                f"NextCloud WebDAV {method} failed for '{url}' "
                f"(status={response.status_code}, body={response.text[:350]})"
            )
        return response

    def _request(self, method: str, remote_path: str, expected=(200, 201, 204, 207), **kwargs):
        return self._request_url(method=method, url=self._dav_url(remote_path), expected=expected, **kwargs)

    def _request_photos(self, method: str, remote_path: str, expected=(200, 201, 204, 207), **kwargs):
        return self._request_url(method=method, url=self._photos_dav_url(remote_path), expected=expected, **kwargs)

    def _get_worker_session(self) -> requests.Session:
        session = getattr(self._worker_local, "session", None)
        if session is None:
            session = self._build_session()
            self._worker_local.session = session
        return session

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        # Avoid accidental proxy routing from container env vars unless explicitly enabled.
        session.trust_env = bool(self.use_system_proxy)
        session.auth = (self.username, self.password)
        session.headers.update({"User-Agent": f"{GV.TOOL_NAME}/{GV.TOOL_VERSION_WITHOUT_V}"})
        pool_size = max(8, self.max_parallel_uploads * 2)
        adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _request_url_with_session(self, session: requests.Session, method: str, url: str, expected=(200, 201, 204, 207), **kwargs):
        response = session.request(method=method, url=url, timeout=self.timeout_seconds, **kwargs)
        if response.status_code not in expected:
            if int(response.status_code) == 401:
                raise RuntimeError(
                    "NextCloud authentication failed (401 Unauthorized). "
                    "Check NEXTCLOUD_URL, username/password (or app password), and WebDAV permissions."
                )
            raise RuntimeError(
                f"NextCloud WebDAV {method} failed for '{url}' "
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

    def _to_datetime_utc(self, text: str) -> Optional[datetime]:
        value = str(text or "").strip()
        if not value:
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def _asset_matches_filters(self, asset_datetime: str, asset_type: str, selected_type: str = "all") -> bool:
        selected = str(selected_type or "all").lower()
        a_type = str(asset_type or "").lower()
        if selected in ("image", "images", "photo", "photos") and a_type not in ("photo", "image"):
            return False
        if selected in ("video", "videos") and a_type != "video":
            return False

        asset_dt = self._to_datetime_utc(asset_datetime)
        from_dt = self._to_datetime_utc(self.from_date)
        to_dt = self._to_datetime_utc(self.to_date)
        if from_dt and asset_dt and asset_dt < from_dt:
            return False
        if to_dt and asset_dt and asset_dt > to_dt:
            return False

        if not self._warned_unsupported_filters and (self.country or self.city or self.person):
            self._warned_unsupported_filters = True
            LOGGER.warning(
                f"{MSG_TAGS['WARNING']}NextCloud WebDAV integration does not expose country/city/person indexed filters. "
                f"Those filters are ignored for NextCloud."
            )
        return True

    def _split_relative_from_href(self, href: str) -> str:
        marker = f"/remote.php/dav/files/{self.username}"
        idx = href.find(marker)
        if idx < 0:
            return "/"
        rel = href[idx + len(marker):]
        rel = rel or "/"
        return unquote(rel)

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

    def _upload_file_fast(self, local_path: str, remote_path: str) -> str:
        # Same as _upload_file but assumes parent folder already exists.
        with open(local_path, "rb") as fp:
            self._request("PUT", remote_path, expected=(200, 201, 204), data=fp)
        return remote_path

    def _upload_file_fast_with_session(self, session: requests.Session, local_path: str, remote_path: str) -> str:
        with open(local_path, "rb") as fp:
            self._request_url_with_session(
                session=session,
                method="PUT",
                url=self._dav_url(remote_path),
                expected=(200, 201, 204),
                data=fp,
            )
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

    def _native_albums_home(self) -> str:
        return "/albums"

    def _native_album_path(self, album_name: str) -> str:
        return f"{self._native_albums_home().rstrip('/')}/{album_name}"

    def _ensure_native_album(self, album_name: str) -> str:
        album_path = self._native_album_path(album_name)
        self._request_photos("MKCOL", album_path, expected=(201, 405, 409))
        return album_path

    def _native_album_existing_file_names(self, album_path: str) -> set[str]:
        xml_body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>'
        )
        response = self._request_photos(
            "PROPFIND",
            album_path,
            expected=(207,),
            headers={"Depth": "1", "Content-Type": "application/xml"},
            data=xml_body,
        )
        root = ET.fromstring(response.text)
        ns = {"d": "DAV:"}
        names: set[str] = set()
        for item in root.findall("d:response", ns):
            href_node = item.find("d:href", ns)
            if href_node is None:
                continue
            href = href_node.text or ""
            name = Path(href.rstrip("/")).name
            if name and name != Path(album_path).name:
                names.add(name)
        return names

    def _copy_file_to_native_album(self, source_remote_path: str, album_path: str, destination_name: str):
        destination_url = self._photos_dav_url(f"{album_path.rstrip('/')}/{destination_name}")
        self._request(
            "COPY",
            source_remote_path,
            expected=(201, 204, 412),
            headers={"Destination": destination_url, "Overwrite": "F"},
        )

    def _copy_file_to_native_album_with_session(self, session: requests.Session, source_remote_path: str, album_path: str, destination_name: str):
        destination_url = self._photos_dav_url(f"{album_path.rstrip('/')}/{destination_name}")
        self._request_url_with_session(
            session=session,
            method="COPY",
            url=self._dav_url(source_remote_path),
            expected=(201, 204, 412),
            headers={"Destination": destination_url, "Overwrite": "F"},
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
            selected = str(type or self.type or "all").lower()
            entries = list(self._iter_files_recursive(self.webdav_root))
            assets = []
            for entry in entries:
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                payload = self._build_asset_payload(entry["path"], filename, entry.get("last_modified", ""))
                if not self._asset_matches_filters(
                    asset_datetime=payload.get("asset_datetime", ""),
                    asset_type=payload.get("type", ""),
                    selected_type=selected,
                ):
                    continue
                assets.append(payload)
            return assets

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or self.type or "all").lower()
            assets = []
            for entry in self._iter_files_recursive(str(album_id)):
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                payload = self._build_asset_payload(entry["path"], filename, entry.get("last_modified", ""))
                if not self._asset_matches_filters(
                    asset_datetime=payload.get("asset_datetime", ""),
                    asset_type=payload.get("type", ""),
                    selected_type=selected,
                ):
                    continue
                payload["album_name"] = album_name or Path(str(album_id).rstrip("/")).name
                assets.append(payload)
            return assets

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, log_level=logging.WARNING):
        return self.get_all_assets_from_album(album_id=album_id, album_name=album_name, type=type, log_level=log_level)

    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or self.type or "all").lower()
            assets = []
            for entry in self._iter_files_recursive(self._no_albums_root()):
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                payload = self._build_asset_payload(entry["path"], filename, entry.get("last_modified", ""))
                if not self._asset_matches_filters(
                    asset_datetime=payload.get("asset_datetime", ""),
                    asset_type=payload.get("type", ""),
                    selected_type=selected,
                ):
                    continue
                assets.append(payload)
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
            for index, folder in enumerate(
                tqdm(subfolders, desc=f"{MSG_TAGS['INFO']}Uploading Albums to NextCloud", unit=" album"),
                start=1,
            ):
                album_name = os.path.basename(folder)
                media_files = [f for f in get_all_files_paths(folder) if self._is_supported_media(f)]
                LOGGER.info(
                    f"{MSG_TAGS['INFO']}Processing album {index}/{len(subfolders)}: "
                    f"'{album_name}' ({len(media_files)} supported assets)"
                )
                if not media_files:
                    total_albums_skipped += 1
                    continue
                exists, album_id = self.album_exists(album_name=album_name, log_level=log_level)
                if not exists or not album_id:
                    album_id = self.create_album(album_name=album_name, log_level=log_level)
                    total_albums_uploaded += 1
                # Native Nextcloud Photos album (separate from files WebDAV folder tree)
                native_enabled = True
                native_album_path = ""
                existing_album_files = {
                    Path(item.get("path", "")).name
                    for item in self._propfind(str(album_id), depth=1)
                    if item.get("is_dir") != "true"
                }
                existing_native_files = set()
                try:
                    native_album_path = self._ensure_native_album(album_name=album_name)
                    existing_native_files = self._native_album_existing_file_names(native_album_path)
                except Exception as error:
                    native_enabled = False
                    LOGGER.warning(
                        f"{MSG_TAGS['WARNING']}Native album sync disabled for '{album_name}': {error}. "
                        f"Continuing with folder-only upload."
                    )
                native_added = 0
                album_uploaded = 0
                planned_uploads: List[Tuple[str, str, str, bool]] = []
                seen_names = set(existing_album_files)
                for file_path in media_files:
                    file_name = os.path.basename(file_path)
                    remote_file = f"{str(album_id).rstrip('/')}/{file_name}"
                    if file_name in seen_names:
                        total_duplicates_skipped += 1
                        continue
                    seen_names.add(file_name)
                    should_copy_native = native_enabled and file_name not in existing_native_files
                    planned_uploads.append((file_path, file_name, remote_file, should_copy_native))

                if planned_uploads:
                    workers = max(1, min(self.max_parallel_uploads, len(planned_uploads)))

                    def _upload_worker(item: Tuple[str, str, str, bool]):
                        local_file, local_name, remote_target, copy_native = item
                        session = self._get_worker_session()
                        self._upload_file_fast_with_session(session, local_file, remote_target)
                        native_added_local = 0
                        if copy_native:
                            self._copy_file_to_native_album_with_session(
                                session=session,
                                source_remote_path=remote_target,
                                album_path=native_album_path,
                                destination_name=local_name,
                            )
                            native_added_local = 1
                        return local_name, native_added_local

                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        futures = [executor.submit(_upload_worker, item) for item in planned_uploads]
                        for future in as_completed(futures):
                            try:
                                uploaded_name, native_inc = future.result()
                            except Exception as error:
                                LOGGER.warning(
                                    f"{MSG_TAGS['WARNING']}Failed upload in album '{album_name}': {error}"
                                )
                                continue
                            total_assets_uploaded += 1
                            album_uploaded += 1
                            existing_album_files.add(uploaded_name)
                            if native_inc:
                                native_added += native_inc
                                existing_native_files.add(uploaded_name)
                LOGGER.info(
                    f"{MSG_TAGS['INFO']}Album '{album_name}': "
                    f"uploaded={album_uploaded}, native-album adds={native_added}, duplicates-skipped={total_duplicates_skipped}"
                )
            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, 0, total_duplicates_skipped

    def push_no_albums(self, input_folder, subfolders_exclusion=f"{FOLDERNAME_ALBUMS}", remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            files = [f for f in get_all_files_paths(input_folder=input_folder, exclusion_folders=subfolders_exclusion) if self._is_supported_media(f)]
            uploaded = 0
            duplicates = 0
            no_albums_root = self._no_albums_root()
            self._ensure_dir(no_albums_root)

            existing_names = {
                Path(item.get("path", "")).name
                for item in self._propfind(no_albums_root, depth=1)
                if item.get("is_dir") != "true"
            }

            planned_uploads: List[Tuple[str, str, str]] = []
            seen_names = set(existing_names)
            for file_path in files:
                file_name = os.path.basename(file_path)
                if file_name in seen_names:
                    duplicates += 1
                    continue
                seen_names.add(file_name)
                remote_file = f"{no_albums_root.rstrip('/')}/{file_name}"
                planned_uploads.append((file_path, file_name, remote_file))

            if planned_uploads:
                workers = max(1, min(self.max_parallel_uploads, len(planned_uploads)))

                def _upload_worker(item: Tuple[str, str, str]):
                    local_file, local_name, remote_target = item
                    session = self._get_worker_session()
                    self._upload_file_fast_with_session(session, local_file, remote_target)
                    return local_name

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [executor.submit(_upload_worker, item) for item in planned_uploads]
                    for future in tqdm(
                        as_completed(futures),
                        total=len(planned_uploads),
                        desc=f"{MSG_TAGS['INFO']}Uploading Assets without Albums to NextCloud",
                        unit=" asset",
                    ):
                        try:
                            uploaded_name = future.result()
                        except Exception as error:
                            LOGGER.warning(f"{MSG_TAGS['WARNING']}Failed upload without album: {error}")
                            continue
                        uploaded += 1
                        existing_names.add(uploaded_name)

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
            downloaded = 0
            for asset in self.get_all_assets_without_albums(log_level=log_level):
                asset_id = asset.get("id", "")
                asset_filename = asset.get("filename", "")
                asset_time = asset.get("asset_datetime", "")
                created_dt = self._to_datetime_utc(asset_time) or datetime.now(timezone.utc)
                year_str = created_dt.strftime("%Y")
                month_str = created_dt.strftime("%m")
                target_folder = os.path.join(target, year_str, month_str)
                os.makedirs(target_folder, exist_ok=True)
                self.pull_asset(
                    asset_id=asset_id,
                    asset_filename=asset_filename,
                    asset_time=asset_time,
                    download_folder=target_folder,
                    log_level=log_level,
                )
                downloaded += 1
            return downloaded

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

                    # Try to rename native Nextcloud Photos album too (if it exists).
                    # Keep the main rename successful even if native album MOVE is not supported/fails.
                    try:
                        native_src = self._native_album_path(old_name)
                        native_dst = self._native_album_path(new_name)
                        native_destination_url = self._photos_dav_url(native_dst)
                        self._request_photos(
                            "MOVE",
                            native_src,
                            expected=(201, 204),
                            headers={"Destination": native_destination_url, "Overwrite": "F"},
                        )
                    except Exception as native_error:
                        LOGGER.warning(
                            f"{MSG_TAGS['WARNING']}Folder renamed but native Nextcloud album rename failed "
                            f"('{old_name}' -> '{new_name}'): {native_error}"
                        )

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

