import logging
import os
import re
import shutil
import threading
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urljoin

import piexif
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
from Utils.DateUtils import guess_date_from_filename
from Utils.GeneralUtils import confirm_continue, convert_to_list, match_pattern, replace_pattern, tqdm


class ClassNextCloudPhotos:
    def __init__(self, account_id: int = 1):
        self.account_id = int(account_id or 1)
        self.base_url = ""
        self.username = ""
        self.password = ""
        self.photos_folder = ""
        self.albums_folder = ""
        self.client_name = "NextCloud Photos"
        self.local_albums_root_name = FOLDERNAME_ALBUMS
        self.local_no_albums_root_name = FOLDERNAME_NO_ALBUMS
        self.session: Optional[requests.Session] = None
        self.timeout_seconds = 60
        self.max_parallel_uploads = 12
        self.max_parallel_downloads = 12
        self.use_system_proxy = False
        self._worker_local = threading.local()
        self._session_lock = threading.Lock()
        self._ensured_dirs_lock = threading.Lock()
        self._ensured_dirs = {"/"}
        self._native_album_lock = threading.Lock()
        self._native_album_cache: Dict[str, str] = {}
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
            label = str(self.username or "").strip()
            if not label:
                try:
                    config = load_config(config_file=CONFIGURATION_FILE, section_to_load="NextCloud Photos")
                    section = config.get("NextCloud Photos", {})
                    label = str(section.get(f"NEXTCLOUD_USERNAME_{self.account_id}", "") or "").strip()
                except Exception:
                    label = ""
            if not label:
                label = str(self.account_id)
            return f"{self.client_name} ({label})"

    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            config = load_config(config_file=config_file, section_to_load="NextCloud Photos")
            section = config.get("NextCloud Photos", {})
            suffix = str(self.account_id)
            self.base_url = section.get("NEXTCLOUD_URL", "").strip().rstrip("/")
            self.username = section.get(f"NEXTCLOUD_USERNAME_{suffix}", "").strip()
            self.password = section.get(f"NEXTCLOUD_PASSWORD_{suffix}", "").strip()
            default_photos_folder = "/Photos/ALL_Photos"
            default_albums_folder = "/Photos/Albums"
            configured_photos_folder = section.get(f"NEXTCLOUD_PHOTOS_FOLDER_{suffix}", "").strip()
            configured_albums_folder = section.get(f"NEXTCLOUD_ALBUMS_FOLDER_{suffix}", "").strip()
            if self.username:
                self.photos_folder = configured_photos_folder or default_photos_folder
                self.albums_folder = configured_albums_folder or default_albums_folder
            else:
                self.photos_folder = configured_photos_folder
                self.albums_folder = configured_albums_folder
            raw_parallel = section.get(
                f"NEXTCLOUD_MAX_PARALLEL_UPLOADS_{suffix}",
                section.get("NEXTCLOUD_MAX_PARALLEL_UPLOADS", str(self.max_parallel_uploads)),
            )
            raw_use_proxy = section.get(
                f"NEXTCLOUD_USE_SYSTEM_PROXY_{suffix}",
                section.get("NEXTCLOUD_USE_SYSTEM_PROXY", str(self.use_system_proxy)),
            )
            raw_parallel_downloads = section.get(
                f"NEXTCLOUD_MAX_PARALLEL_DOWNLOADS_{suffix}",
                section.get("NEXTCLOUD_MAX_PARALLEL_DOWNLOADS", str(self.max_parallel_downloads)),
            )
            try:
                self.max_parallel_uploads = max(1, min(32, int(str(raw_parallel).strip())))
            except Exception:
                self.max_parallel_uploads = 12
            try:
                self.max_parallel_downloads = max(1, min(32, int(str(raw_parallel_downloads).strip())))
            except Exception:
                self.max_parallel_downloads = 12
            self.use_system_proxy = str(raw_use_proxy).strip().lower() in {"1", "true", "yes", "y", "on"}
            # Accept host-only values in config and normalize to absolute URL.
            if self.base_url and not re.match(r"^https?://", self.base_url, flags=re.IGNORECASE):
                LOGGER.warning(
                    f"{MSG_TAGS['WARNING']}NEXTCLOUD_URL has no scheme. Auto-prefixing with 'http://'. "
                    f"Current value: '{self.base_url}'"
                )
                self.base_url = f"http://{self.base_url}"
            if self.username:
                self.photos_folder = self._normalize_remote_folder(self.photos_folder, default=default_photos_folder)
                self.albums_folder = self._normalize_remote_folder(self.albums_folder, default=default_albums_folder)

            if not self.base_url:
                raise ValueError("Missing NEXTCLOUD_URL in [NextCloud Photos]")
            if not self.username:
                raise ValueError(f"Missing NEXTCLOUD_USERNAME_{suffix} in [NextCloud Photos]")
            if not self.password:
                raise ValueError(f"Missing NEXTCLOUD_PASSWORD_{suffix} in [NextCloud Photos]")

            LOGGER.info("NextCloud Config Read:")
            LOGGER.info("----------------------")
            LOGGER.info(f"NEXTCLOUD_URL              : {self.base_url}")
            LOGGER.info(f"NEXTCLOUD_USERNAME         : {self.username}")
            LOGGER.info(f"NEXTCLOUD_PASSWORD         : {'*' * len(self.password)}")
            LOGGER.info(f"NEXTCLOUD_PHOTOS_FOLDER    : {self.photos_folder}")
            LOGGER.info(f"NEXTCLOUD_ALBUMS_FOLDER    : {self.albums_folder}")
            LOGGER.info(f"NEXTCLOUD_MAX_PAR_UPLOADS  : {self.max_parallel_uploads}")
            LOGGER.info(f"NEXTCLOUD_MAX_PAR_DOWNLOADS: {self.max_parallel_downloads}")
            LOGGER.info("")

    def login(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.read_config_file(config_file=config_file, log_level=log_level)
            LOGGER.info("Authenticating on NextCloud Photos and getting Session...")
            self.session = self._build_session()
            self._worker_local = threading.local()
            with self._ensured_dirs_lock:
                self._ensured_dirs = {"/"}
            with self._native_album_lock:
                self._native_album_cache = {}
            self._ensure_dir("/")
            self._ensure_dir(self._albums_root())
            self._ensure_dir(self._no_albums_root())
            LOGGER.info("Authentication Successfully with user/password found in Config file. Session initialized.")
            LOGGER.info(f"User ID: '{self.username}' found.")
            LOGGER.info("")
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
            self._worker_local = threading.local()
            with self._ensured_dirs_lock:
                self._ensured_dirs = {"/"}
            with self._native_album_lock:
                self._native_album_cache = {}
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged out from NextCloud account {self.account_id}.")
            return True

    def _require_session(self):
        has_runtime_config = bool(self.base_url and self.username and re.match(r"^https?://", self.base_url, flags=re.IGNORECASE))
        if self.session is not None and has_runtime_config:
            return
        with self._session_lock:
            has_runtime_config = bool(self.base_url and self.username and re.match(r"^https?://", self.base_url, flags=re.IGNORECASE))
            if self.session is None or not has_runtime_config:
                # Keep the same behavior as Synology/Immich clients: lazy login on first API call.
                self.login(log_level=logging.ERROR)
        has_runtime_config = bool(self.base_url and self.username and re.match(r"^https?://", self.base_url, flags=re.IGNORECASE))
        if self.session is None or not has_runtime_config:
            raise RuntimeError("NextCloud session could not be initialized.")

    def _dav_url(self, remote_path: str) -> str:
        return self._dav_namespace_url(remote_path=remote_path, namespace="files")

    def _dav_namespace_url(self, remote_path: str, namespace: str = "files") -> str:
        # Normalize to a decoded path first to avoid double-encoding (%2520, etc.)
        clean = unquote(str(remote_path or "").replace("\\", "/"))
        clean = re.sub(r"/+", "/", clean).strip()
        if not clean.startswith("/"):
            clean = f"/{clean}"
        namespace_value = "photos" if str(namespace or "").lower() == "photos" else "files"
        root = f"/remote.php/dav/{namespace_value}/{quote(self.username, safe='')}"
        full = f"{root}{quote(clean, safe='/._-() ')}"
        full = full.replace(" ", "%20")
        return urljoin(f"{self.base_url}/", full.lstrip("/"))

    def _photos_dav_url(self, remote_path: str) -> str:
        return self._dav_namespace_url(remote_path=remote_path, namespace="photos")

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
                f"(status={response.status_code}, body={self._compact_response_body(response.text)})"
            )
        return response

    @staticmethod
    def _is_not_found_runtime_error(error: Exception) -> bool:
        text = str(error or "")
        lowered = text.lower()
        if "status=404" in lowered:
            return True
        if "exception:notfound" in lowered or "exception\\notfound" in lowered:
            return True
        if "could not be located" in lowered:
            return True
        return False

    @staticmethod
    def _compact_response_body(body: str, limit: int = 220) -> str:
        clean = re.sub(r"\s+", " ", str(body or "")).strip()
        return clean[:limit]

    @staticmethod
    def _compact_runtime_error(error: Exception, limit: int = 240) -> str:
        text = re.sub(r"\s+", " ", str(error or "")).strip()
        if "photo not found for user" in text.lower():
            return "Photo not found for user"
        status_match = re.search(r"status\s*=\s*(\d+)", text, flags=re.IGNORECASE)
        if status_match:
            return f"HTTP {status_match.group(1)}"
        return text[:limit]

    def _request(self, method: str, remote_path: str, expected=(200, 201, 204, 207), **kwargs):
        # Ensure config/session is initialized before building absolute DAV URLs.
        self._require_session()
        return self._request_url(method=method, url=self._dav_url(remote_path), expected=expected, **kwargs)

    def _request_photos(self, method: str, remote_path: str, expected=(200, 201, 204, 207), **kwargs):
        # Ensure config/session is initialized before building absolute Photos DAV URLs.
        self._require_session()
        return self._request_url(method=method, url=self._photos_dav_url(remote_path), expected=expected, **kwargs)

    def _get_worker_session(self) -> requests.Session:
        # Ensure config/session has been initialized before creating worker sessions.
        self._require_session()
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
                f"(status={response.status_code}, body={self._compact_response_body(response.text)})"
            )
        return response

    @staticmethod
    def _normalize_dir_path(remote_path: str) -> str:
        normalized = re.sub(r"/+", "/", str(remote_path or "/")).rstrip("/")
        return normalized or "/"

    @staticmethod
    def _normalize_remote_folder(remote_path: str, default: str) -> str:
        clean = re.sub(r"/+", "/", str(remote_path or "").replace("\\", "/")).strip()
        if not clean:
            clean = str(default or "/")
        if not clean.startswith("/"):
            clean = f"/{clean}"
        clean = re.sub(r"/+", "/", clean).rstrip("/")
        return clean or "/"

    @staticmethod
    def _is_path_under(remote_path: str, base_path: str) -> bool:
        path_clean = re.sub(r"/+", "/", str(remote_path or "").replace("\\", "/")).rstrip("/")
        base_clean = re.sub(r"/+", "/", str(base_path or "").replace("\\", "/")).rstrip("/")
        if not path_clean or not base_clean:
            return False
        return path_clean == base_clean or path_clean.startswith(f"{base_clean}/")

    @staticmethod
    def _album_name_dedupe_key(album_name: str) -> str:
        raw = str(album_name or "")
        if not raw:
            return ""
        normalized = unicodedata.normalize("NFKC", raw).casefold().strip()
        # Strip typical Nextcloud synthetic prefixes.
        normalized = re.sub(r"^\d+[-_\s]+", "", normalized).strip()
        # Treat common separators as equivalent and normalize noisy suffixes from duplicate copies.
        normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
        normalized = re.sub(r"\s*\((copy|\d+)\)\s*$", "", normalized).strip()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _albums_root(self) -> str:
        return self.albums_folder

    def _no_albums_root(self) -> str:
        return self.photos_folder

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

    def _split_relative_from_href(self, href: str, namespace: str = "files") -> str:
        namespace_value = "photos" if str(namespace or "").lower() == "photos" else "files"
        marker = f"/remote.php/dav/{namespace_value}/{quote(self.username, safe='')}"
        idx = href.find(marker)
        if idx < 0:
            return "/"
        rel = href[idx + len(marker):]
        rel = rel or "/"
        return unquote(rel)

    def _propfind(self, remote_path: str, depth: int = 1, namespace: str = "files") -> List[Dict[str, str]]:
        xml_body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop>'
            "<d:resourcetype/><d:getcontentlength/><d:getlastmodified/>"
            "</d:prop></d:propfind>"
        )
        namespace_value = "photos" if str(namespace or "").lower() == "photos" else "files"
        if namespace_value == "photos":
            response = self._request_photos(
                "PROPFIND",
                remote_path,
                expected=(207,),
                headers={"Depth": str(depth), "Content-Type": "application/xml"},
                data=xml_body,
            )
        else:
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
            rel_path = self._split_relative_from_href(href, namespace=namespace_value)
            name = Path(rel_path.rstrip("/")).name
            items.append(
                {
                    "href": href,
                    "path": rel_path,
                    "name": name,
                    "is_dir": "true" if collection is not None else "false",
                    "size": (content_length.text or "0") if content_length is not None else "0",
                    "last_modified": (last_modified.text or "") if last_modified is not None else "",
                    "source_namespace": namespace_value,
                }
            )
        return items

    def _exists(self, remote_path: str) -> bool:
        self._require_session()
        url = self._dav_url(remote_path)
        response = self.session.request("HEAD", url, timeout=self.timeout_seconds)
        return response.status_code in (200, 204)

    def _ensure_dir(self, remote_path: str):
        normalized = self._normalize_dir_path(remote_path)
        with self._ensured_dirs_lock:
            if normalized in self._ensured_dirs:
                return
        current = ""
        for part in normalized.split("/"):
            if part == "":
                continue
            current = f"{current}/{part}"
            with self._ensured_dirs_lock:
                if current in self._ensured_dirs:
                    continue
            # Optimistic create is faster than HEAD+MKCOL for every upload.
            self._request("MKCOL", current, expected=(201, 405, 409))
            with self._ensured_dirs_lock:
                self._ensured_dirs.add(current)

    def _iter_files_recursive(self, remote_path: str, namespace: str = "files") -> Iterable[Dict[str, str]]:
        stack = [remote_path]
        namespace_value = "photos" if str(namespace or "").lower() == "photos" else "files"
        while stack:
            current = stack.pop()
            try:
                entries = self._propfind(current, depth=1, namespace=namespace_value)
            except Exception as error:
                if self._is_not_found_runtime_error(error):
                    LOGGER.warning(
                        f"{MSG_TAGS['WARNING']}NextCloud folder not found while listing '{current}' "
                        f"(namespace={namespace_value}). Skipping. {error}"
                    )
                    continue
                raise
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

    def _download_file_with_session(
        self,
        session: requests.Session,
        remote_path: str,
        local_path: str,
        namespace: str = "files",
    ) -> str:
        self._ensure_local_parent(local_path)
        namespace_value = "photos" if str(namespace or "").lower() == "photos" else "files"
        response = self._request_url_with_session(
            session=session,
            method="GET",
            url=self._dav_namespace_url(remote_path=remote_path, namespace=namespace_value),
            expected=(200, 206),
            stream=True,
        )
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

    def _copy_remote_with_session(self, session: requests.Session, source_remote_path: str, destination_remote_path: str):
        self._ensure_dir(self._remote_parent(destination_remote_path))
        destination_url = self._dav_url(destination_remote_path)
        self._request_url_with_session(
            session=session,
            method="COPY",
            url=self._dav_url(source_remote_path),
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

    def _get_or_create_native_album(self, album_name: str) -> str:
        key = str(album_name or "").strip()
        if not key:
            return ""
        with self._native_album_lock:
            cached = self._native_album_cache.get(key.lower())
            if cached:
                return cached
        album_path = self._ensure_native_album(key)
        with self._native_album_lock:
            self._native_album_cache[key.lower()] = album_path
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
            name = unquote(Path(href.rstrip("/")).name)
            if name and name != Path(album_path).name:
                # Nextcloud PhotosDAV may expose entries as "<numeric-id>-<original-name>".
                # Store both raw and normalized names to avoid duplicate uploads on re-runs.
                lowered = str(name).casefold()
                names.add(lowered)
                names.add(re.sub(r"^\d+-", "", lowered))
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
            try:
                entries = self._propfind(albums_root, depth=1)
            except Exception as error:
                if self._is_not_found_runtime_error(error):
                    LOGGER.warning(
                        f"{MSG_TAGS['WARNING']}NextCloud albums folder '{albums_root}' was not found. "
                        f"Continuing with empty albums list. {error}"
                    )
                    return []
                raise
            albums = []
            for entry in entries:
                if entry["path"].rstrip("/") == albums_root.rstrip("/"):
                    continue
                if entry["is_dir"] != "true":
                    continue
                albums.append({"id": entry["path"], "albumName": entry["name"], "source_namespace": "files"})
            albums.sort(key=lambda a: a["albumName"].lower())
            return albums

    def _list_native_album_directories(self, log_level=None) -> List[Dict[str, str]]:
        with set_log_level(LOGGER, log_level):
            albums_root = self._native_albums_home()
            try:
                entries = self._propfind(albums_root, depth=1, namespace="photos")
            except Exception as error:
                LOGGER.warning(
                    f"{MSG_TAGS['WARNING']}Unable to list native Nextcloud albums from '{albums_root}'. "
                    f"Continuing with folder-based albums only. {error}"
                )
                return []
            albums = []
            for entry in entries:
                if entry["path"].rstrip("/") == albums_root.rstrip("/"):
                    continue
                if entry["is_dir"] != "true":
                    continue
                albums.append({"id": entry["path"], "albumName": entry["name"], "source_namespace": "photos"})
            albums.sort(key=lambda a: a["albumName"].lower())
            return albums

    def _list_download_album_directories(self, log_level=None) -> List[Dict[str, str]]:
        with set_log_level(LOGGER, log_level):
            merged: Dict[str, Dict[str, str]] = {}
            for album in self._list_album_directories(log_level=log_level):
                key = self._album_name_dedupe_key(album.get("albumName", ""))
                if not key:
                    continue
                merged[key] = album
            for album in self._list_native_album_directories(log_level=log_level):
                key = self._album_name_dedupe_key(album.get("albumName", ""))
                if not key:
                    continue
                # Native album wins when names collide.
                merged[key] = album
            albums = list(merged.values())
            albums.sort(key=lambda a: str(a.get("albumName", "")).lower())
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
            try:
                self._get_or_create_native_album(album_name)
            except Exception as error:
                LOGGER.warning(
                    f"{MSG_TAGS['WARNING']}Unable to create native Nextcloud album '{album_name}'. "
                    f"Folder album was created successfully. {error}"
                )
            return target

    def remove_album(self, album_id, album_name=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            return self._remove_remote(str(album_id))

    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        return self._list_download_album_directories(log_level=log_level)

    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        return self._list_download_album_directories(log_level=log_level)

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
            entries = list(self._iter_files_recursive(self._no_albums_root()))
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
            album_path = str(album_id)
            source_namespace = "photos" if album_path.startswith("/albums/") else "files"
            for entry in self._iter_files_recursive(album_path, namespace=source_namespace):
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
            albums_root = self._albums_root().rstrip("/")
            for entry in self._iter_files_recursive(self._no_albums_root()):
                filename = entry.get("name", "")
                if not self._is_supported_media(filename):
                    continue
                asset_path = str(entry.get("path", ""))
                if albums_root and self._is_path_under(asset_path, albums_root):
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
            session = self._get_worker_session()
            resolved_album_name = str(album_name or Path(str(album_id).rstrip("/")).name)
            native_album_path = ""
            if resolved_album_name:
                try:
                    native_album_path = self._get_or_create_native_album(resolved_album_name)
                except Exception as error:
                    LOGGER.warning(
                        f"{MSG_TAGS['WARNING']}Unable to prepare native Nextcloud album '{resolved_album_name}'. "
                        f"Continuing with folder album only. {error}"
                    )
            for asset_id in assets:
                src = str(asset_id)
                name = Path(src).name
                dst = f"{str(album_id).rstrip('/')}/{name}"
                try:
                    self._copy_remote_with_session(session=session, source_remote_path=src, destination_remote_path=dst)
                    if native_album_path:
                        self._copy_file_to_native_album_with_session(
                            session=session,
                            source_remote_path=dst,
                            album_path=native_album_path,
                            destination_name=name,
                        )
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
            self._ensure_dir(self._remote_parent(remote_path))
            session = self._get_worker_session()
            remote_path = self._upload_file_fast_with_session(session=session, local_path=file_path, remote_path=remote_path)
            return remote_path, False

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_NextCloud", album_passphrase=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            os.makedirs(download_folder, exist_ok=True)
            output_file = os.path.join(download_folder, str(asset_filename))
            session = self._get_worker_session()
            remote_path = str(asset_id)
            source_namespace = "photos" if remote_path.startswith("/albums/") else "files"
            output_file = self._download_file_with_session(
                session=session,
                remote_path=remote_path,
                local_path=output_file,
                namespace=source_namespace,
            )
            return output_file

    def _normalize_asset_time_for_metadata(self, asset_time) -> str:
        if isinstance(asset_time, (int, float)):
            return datetime.fromtimestamp(asset_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        value = str(asset_time or "").strip()
        if not value:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value
        except Exception:
            pass
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        try:
            parsed = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z")
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _extract_exif_datetime(self, file_path: str) -> Optional[datetime]:
        try:
            exif_dict = piexif.load(file_path)
        except Exception:
            return None

        candidates = [
            exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal),
            exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeDigitized),
            exif_dict.get("0th", {}).get(piexif.ImageIFD.DateTime),
        ]
        for value in candidates:
            if not value:
                continue
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="ignore")
            text = str(value).strip()
            if not text:
                continue
            try:
                parsed = datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
                return parsed.replace(tzinfo=timezone.utc)
            except Exception:
                continue
        return None

    def _resolve_download_datetime(self, downloaded_file: str, fallback_asset_time) -> datetime:
        try:
            if self._is_photo(downloaded_file):
                exif_dt = self._extract_exif_datetime(downloaded_file)
                if exif_dt is not None:
                    return exif_dt
        except Exception:
            pass

        try:
            guessed = guess_date_from_filename(downloaded_file, step_name="", log_level=logging.ERROR)
            if guessed is not None:
                if guessed.tzinfo is None:
                    guessed = guessed.replace(tzinfo=timezone.utc)
                else:
                    guessed = guessed.astimezone(timezone.utc)
                return guessed
        except Exception:
            pass

        fallback_dt = self._to_datetime_utc(fallback_asset_time)
        if fallback_dt is not None:
            return fallback_dt
        return datetime.now(timezone.utc)

    @staticmethod
    def _unique_local_path(folder: str, filename: str) -> str:
        base = Path(filename).stem
        ext = Path(filename).suffix
        candidate = os.path.join(folder, filename)
        if not os.path.exists(candidate):
            return candidate
        counter = 1
        while True:
            candidate = os.path.join(folder, f"{base} ({counter}){ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

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
                    normalized_name = str(file_name).casefold()
                    should_copy_native = native_enabled and normalized_name not in existing_native_files
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
                        for future in tqdm(
                            as_completed(futures),
                            total=len(futures),
                            desc=f"{MSG_TAGS['INFO']}   Uploading '{album_name}' Assets",
                            unit=" assets",
                        ):
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
                                uploaded_normalized = str(uploaded_name).casefold()
                                existing_native_files.add(uploaded_normalized)
                                existing_native_files.add(re.sub(r"^\d+-", "", uploaded_normalized))
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
            albums_folder_included = any(
                str(folder or "").strip().lower() == self.local_albums_root_name.lower()
                for folder in albums_folders
            )
            if not albums_folder_included:
                albums_folders.append(self.local_albums_root_name)
            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_assets_uploaded_within_albums = 0
            total_assets_uploaded_without_albums = 0
            total_duplicates_assets_skipped = 0

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

            uploaded_no_albums, duplicates_no_albums = self.push_no_albums(
                input_folder=input_folder,
                subfolders_exclusion=self.local_albums_root_name,
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

    def _download_remote_folder(
        self,
        remote_folder: str,
        local_folder: str,
        progress_desc: str = "",
        log_level=None,
        source_namespace: str = "files",
    ) -> int:
        namespace_value = "photos" if str(source_namespace or "").lower() == "photos" else "files"
        entries = list(self._iter_files_recursive(remote_folder, namespace=namespace_value))
        if not entries:
            return 0

        workers = max(1, min(self.max_parallel_downloads, len(entries)))

        def _download_worker(entry: Dict[str, str]) -> str:
            rel = str(entry["path"]).replace(str(remote_folder).rstrip("/") + "/", "")
            target = os.path.join(local_folder, rel.replace("/", os.sep))
            session = self._get_worker_session()
            entry_namespace = str(entry.get("source_namespace") or namespace_value).lower()
            return self._download_file_with_session(
                session=session,
                remote_path=entry["path"],
                local_path=target,
                namespace=entry_namespace,
            )

        downloaded = 0
        failed = 0
        failure_reasons: Dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_download_worker, entry) for entry in entries]
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc=progress_desc or f"{MSG_TAGS['INFO']}Downloading Assets from NextCloud",
                unit=" asset",
            ):
                try:
                    future.result()
                    downloaded += 1
                except Exception as error:
                    failed += 1
                    reason = self._compact_runtime_error(error)
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                    continue
        if failed > 0:
            reasons_text = ", ".join([f"{reason}={count}" for reason, count in sorted(failure_reasons.items(), key=lambda item: item[1], reverse=True)])
            LOGGER.warning(
                f"{MSG_TAGS['WARNING']}Completed with partial failures for folder '{remote_folder}': "
                f"downloaded={downloaded}, failed={failed}, reasons=[{reasons_text}]"
            )
        return downloaded

    def pull_albums(self, albums_name="ALL", output_folder="Downloads_NextCloud", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target_names = [n.lower() for n in convert_to_list(albums_name, log_level=log_level)] if albums_name != "ALL" else ["all"]
            albums = self._list_download_album_directories(log_level=log_level)
            selected_albums = []
            for album in albums:
                name = album["albumName"]
                if "all" not in target_names and not any(match_pattern(name, pattern) for pattern in target_names):
                    continue
                selected_albums.append(album)
            downloaded_albums = 0
            downloaded_assets = 0
            root = os.path.join(output_folder, self.local_albums_root_name)
            os.makedirs(root, exist_ok=True)
            for album in tqdm(
                selected_albums,
                desc=f"{MSG_TAGS['INFO']}Downloading Albums from NextCloud",
                unit=" album",
            ):
                name = album["albumName"]
                local_album = os.path.join(root, name)
                downloaded_assets += self._download_remote_folder(
                    album["id"],
                    local_album,
                    progress_desc=f"{MSG_TAGS['INFO']}   Downloading '{name}' Assets",
                    log_level=log_level,
                    source_namespace=album.get("source_namespace", "files"),
                )
                downloaded_albums += 1
            return downloaded_albums, downloaded_assets

    def pull_no_albums(self, output_folder="Downloads_NextCloud", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target = os.path.join(output_folder, self.local_no_albums_root_name)
            os.makedirs(target, exist_ok=True)
            assets = self.get_all_assets_without_albums(log_level=log_level)
            if not assets:
                return 0

            temp_download_root = os.path.join(target, "_TMP_DOWNLOAD")
            os.makedirs(temp_download_root, exist_ok=True)

            tasks = []
            for asset in assets:
                asset_id = asset.get("id", "")
                asset_filename = asset.get("filename", "")
                asset_time = asset.get("asset_datetime", "")
                tasks.append((asset_id, asset_filename, asset_time))

            workers = max(1, min(self.max_parallel_downloads, len(tasks)))

            def _pull_worker(task: Tuple[str, str, str]) -> str:
                aid, name, time_value = task
                downloaded_file = self.pull_asset(
                    asset_id=aid,
                    asset_filename=name,
                    asset_time=time_value,
                    download_folder=temp_download_root,
                    log_level=log_level,
                )
                resolved_dt = self._resolve_download_datetime(downloaded_file, fallback_asset_time=time_value)
                year_str = resolved_dt.strftime("%Y")
                month_str = resolved_dt.strftime("%m")
                target_folder = os.path.join(target, year_str, month_str)
                os.makedirs(target_folder, exist_ok=True)
                target_file = self._unique_local_path(target_folder, os.path.basename(downloaded_file))
                os.replace(downloaded_file, target_file)
                return target_file

            downloaded = 0
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(_pull_worker, task) for task in tasks]
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc=f"{MSG_TAGS['INFO']}Downloading Assets without Albums from NextCloud",
                    unit=" asset",
                ):
                    future.result()
                    downloaded += 1
            try:
                shutil.rmtree(temp_download_root)
            except Exception:
                pass
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
