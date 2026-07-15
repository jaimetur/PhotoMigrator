import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

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
from Features.BaseMediaClient import BaseMediaClient
from Utils.FileUtils import get_all_files_paths, get_subfolders, merge_exclusion_patterns
from Utils.GeneralUtils import confirm_continue, convert_to_list, match_pattern, replace_pattern, tqdm, update_metadata, sha1_checksum, find_reusable_album_candidate, build_reusable_album_group, canonicalize_album_name_for_reuse, prefer_canonical_album_names_enabled, consolidate_similar_albums_enabled, scan_album_consolidation_groups, print_album_consolidation_preview


class ClassGooglePhotos(BaseMediaClient):
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://photoslibrary.googleapis.com/v1"
    UPLOADS_URL = f"{API_BASE}/uploads"
    FULL_LIBRARY_READ_REMOVAL_DATE = "2025-04-01"

    def __init__(self, account_id: int = 1):
        self.account_id = int(account_id or 1)
        self.client_name = "Google Photos"
        self.session: Optional[requests.Session] = None
        self.timeout_seconds = 60

        self.account_name = ""
        self.client_id = ""
        self.client_secret = ""
        self.refresh_token = ""
        self.access_token = ""
        self._session_lock = threading.Lock()

        self.albums_root_name = FOLDERNAME_ALBUMS
        self.no_albums_root_name = FOLDERNAME_NO_ALBUMS
        self.ALLOWED_PHOTO_EXTENSIONS = [ext.lower() for ext in PHOTO_EXT]
        self.ALLOWED_VIDEO_EXTENSIONS = [ext.lower() for ext in VIDEO_EXT]
        self.type = ARGS.get("filter-by-type", None)
        self.from_date = ARGS.get("filter-from-date", None)
        self.to_date = ARGS.get("filter-to-date", None)
        self.country = ARGS.get("filter-by-country", None)
        self.city = ARGS.get("filter-by-city", None)
        self.person = ARGS.get("filter-by-person", None)
        self.exclude_folder_patterns = merge_exclusion_patterns(
            ARGS.get("exclude-folders", []),
            default_patterns=[".*", "@eaDir", "@Recycle"],
        )
        self.exclude_file_patterns = merge_exclusion_patterns(
            ARGS.get("exclude-files", []),
            default_patterns=["SYNOFILE_THUMB*", "SYNOPHOTO_THUMB*", "SYNOVIDEO_THUMB*", "SYNOPHOTO_FILM*", "Thumbs.db", "ehthumbs.db", ".DS_Store", "._*"],
        )
        self._warned_unsupported_filters = False

    def get_client_name(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            label = str(self.account_name or "").strip()
            if not label:
                try:
                    config = load_config(config_file=CONFIGURATION_FILE, section_to_load="Google Photos")
                    section = config.get("Google Photos", {})
                    label = str(section.get(f"GOOGLE_PHOTOS_ACCOUNT_NAME_{self.account_id}", "") or "").strip()
                except Exception:
                    label = ""
            if not label:
                label = str(self.account_id)
            return f"{self.client_name} ({label})"

    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            config = load_config(config_file=config_file, section_to_load="Google Photos")
            section = config.get("Google Photos", {})
            suffix = str(self.account_id)

            self.account_name = section.get(f"GOOGLE_PHOTOS_ACCOUNT_NAME_{suffix}", "").strip()
            self.client_id = section.get(f"GOOGLE_PHOTOS_CLIENT_ID_{suffix}", "").strip()
            self.client_secret = section.get(f"GOOGLE_PHOTOS_CLIENT_SECRET_{suffix}", "").strip()
            self.refresh_token = section.get(f"GOOGLE_PHOTOS_REFRESH_TOKEN_{suffix}", "").strip()

            if not self.client_id:
                raise ValueError(f"Missing GOOGLE_PHOTOS_CLIENT_ID_{suffix} in [Google Photos]")
            if not self.client_secret:
                raise ValueError(f"Missing GOOGLE_PHOTOS_CLIENT_SECRET_{suffix} in [Google Photos]")
            if not self.refresh_token:
                raise ValueError(f"Missing GOOGLE_PHOTOS_REFRESH_TOKEN_{suffix} in [Google Photos]")

            LOGGER.info("Google Photos Config Read:")
            LOGGER.info("--------------------------")
            LOGGER.info(f"GOOGLE_PHOTOS_CLIENT_ID        : {self.client_id}")
            LOGGER.info(f"GOOGLE_PHOTOS_CLIENT_SECRET    : {'*' * len(self.client_secret)}")
            LOGGER.info(f"GOOGLE_PHOTOS_REFRESH_TOKEN    : {'*' * len(self.refresh_token)}")
            LOGGER.info("")

    def _refresh_access_token(self):
        response = requests.post(
            self.TOKEN_URL,
            timeout=self.timeout_seconds,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to refresh Google Photos access token (status={response.status_code}, body={response.text[:350]})")
        data = response.json()
        token = str(data.get("access_token", "")).strip()
        if not token:
            raise RuntimeError("Google OAuth token response does not include access_token.")
        self.access_token = token

    def login(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            self.read_config_file(config_file=config_file, log_level=log_level)
            LOGGER.info("Authenticating on Google Photos and getting Session...")
            self._refresh_access_token()
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                }
            )
            # Do not probe read endpoints during login. Since Google's April 1, 2025
            # Library API changes, upload-only tokens may still be valid while
            # full-library read calls fail with 403.
            LOGGER.info("Authentication Successfully with refresh token found in Config file. Access token properly set.")
            LOGGER.info(f"User ID: 'google-account-{self.account_id}' found.")
            LOGGER.info("")
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged in to Google Photos account {self.account_id}.")
            return True

    @classmethod
    def get_full_library_read_unsupported_message(cls, operation: str = "This operation") -> str:
        return (
            f"{operation} is not supported with Google Photos as source. "
            f"Since {cls.FULL_LIBRARY_READ_REMOVAL_DATE}, Google Photos Library API no longer allows third-party apps "
            "to read a user's full library. Google removed the legacy scopes "
            "`photoslibrary`, `photoslibrary.readonly`, and `photoslibrary.sharing`, so full-library reads now fail "
            "with `403 PERMISSION_DENIED`. Use Google Takeout as source instead, or use Google Photos only as an "
            "upload target / app-created-data workflow."
        )

    def logout(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            if self.session is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
            self.session = None
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged out from Google Photos account {self.account_id}.")
            return True

    def _require_session(self):
        if self.session is not None:
            return
        with self._session_lock:
            if self.session is None:
                # Keep the same behavior as Synology/Immich/NextCloud clients: lazy login on first API call.
                self.login(log_level=logging.ERROR)
        if self.session is None:
            raise RuntimeError("Google Photos session could not be initialized.")

    def _request(self, method: str, url: str, expected=(200,), **kwargs):
        self._require_session()
        response = self.session.request(method=method, url=url, timeout=self.timeout_seconds, **kwargs)
        if response.status_code not in expected:
            raise RuntimeError(
                f"Google Photos API {method} failed for '{url}' "
                f"(status={response.status_code}, body={response.text[:350]})"
            )
        return response

    def _is_photo(self, filename: str, mime_type: str = "") -> bool:
        mime = str(mime_type or "").lower()
        if mime.startswith("image/"):
            return True
        return Path(filename).suffix.lower() in self.ALLOWED_PHOTO_EXTENSIONS

    def _is_video(self, filename: str, mime_type: str = "") -> bool:
        mime = str(mime_type or "").lower()
        if mime.startswith("video/"):
            return True
        return Path(filename).suffix.lower() in self.ALLOWED_VIDEO_EXTENSIONS

    def _is_supported_media(self, filename: str, mime_type: str = "") -> bool:
        return self._is_photo(filename, mime_type) or self._is_video(filename, mime_type)

    def _normalize_asset_type(self, filename: str, mime_type: str = "") -> str:
        return "video" if self._is_video(filename, mime_type) else "photo"

    def _build_asset_payload(self, media_item: Dict, album_name: str = "") -> Dict[str, str]:
        media_metadata = media_item.get("mediaMetadata", {}) or {}
        creation = str(media_metadata.get("creationTime", "")).strip() or datetime.now(timezone.utc).isoformat()
        payload = {
            "id": str(media_item.get("id", "")),
            "filename": str(media_item.get("filename", "")),
            "asset_datetime": creation,
            "type": self._normalize_asset_type(str(media_item.get("filename", "")), str(media_item.get("mimeType", ""))),
        }
        if album_name:
            payload["album_name"] = album_name
        return payload

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
                f"{MSG_TAGS['WARNING']}Google Photos public API does not provide country/city/person indexed filters in this integration. "
                f"Those filters are ignored for Google Photos."
            )
        return True

    def _list_albums(self) -> List[Dict[str, str]]:
        albums: List[Dict[str, str]] = []
        page_token = ""
        while True:
            params = {"pageSize": 50}
            if page_token:
                params["pageToken"] = page_token
            response = self._request("GET", f"{self.API_BASE}/albums", expected=(200,), params=params)
            data = response.json() or {}
            for album in data.get("albums", []) or []:
                albums.append({"id": str(album.get("id", "")), "albumName": str(album.get("title", ""))})
            page_token = str(data.get("nextPageToken", "")).strip()
            if not page_token:
                break
        albums.sort(key=lambda a: a["albumName"].lower())
        return albums

    def _list_shared_albums(self) -> List[Dict[str, str]]:
        albums: List[Dict[str, str]] = []
        page_token = ""
        while True:
            params = {"pageSize": 50}
            if page_token:
                params["pageToken"] = page_token
            response = self._request("GET", f"{self.API_BASE}/sharedAlbums", expected=(200,), params=params)
            data = response.json() or {}
            for album in data.get("sharedAlbums", []) or []:
                albums.append({"id": str(album.get("id", "")), "albumName": str(album.get("title", ""))})
            page_token = str(data.get("nextPageToken", "")).strip()
            if not page_token:
                break
        albums.sort(key=lambda a: a["albumName"].lower())
        return albums

    def _search_media_items(self, album_id: str = "", page_size: int = 100) -> Iterable[Dict]:
        page_token = ""
        while True:
            body = {"pageSize": page_size}
            if album_id:
                body["albumId"] = album_id
            if page_token:
                body["pageToken"] = page_token
            response = self._request("POST", f"{self.API_BASE}/mediaItems:search", expected=(200,), json=body)
            data = response.json() or {}
            for item in data.get("mediaItems", []) or []:
                yield item
            page_token = str(data.get("nextPageToken", "")).strip()
            if not page_token:
                break

    def _create_upload_token(self, file_path: str) -> str:
        self._require_session()
        with open(file_path, "rb") as fp:
            file_bytes = fp.read()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-File-Name": os.path.basename(file_path),
            "X-Goog-Upload-Protocol": "raw",
        }
        response = requests.post(self.UPLOADS_URL, headers=headers, data=file_bytes, timeout=self.timeout_seconds)
        if response.status_code != 200:
            raise RuntimeError(f"Google Photos upload token creation failed (status={response.status_code}, body={response.text[:350]})")
        token = response.text.strip()
        if not token:
            raise RuntimeError("Google Photos uploads endpoint returned empty upload token.")
        return token

    def _ensure_uploaded_media_item_cache(self):
        if not hasattr(self, "_uploaded_media_item_cache"):
            self._uploaded_media_item_cache = {}
        if not hasattr(self, "_uploaded_media_item_cache_lock"):
            self._uploaded_media_item_cache_lock = threading.Lock()

    def _build_uploaded_media_item_cache_key(self, file_path: str) -> Optional[str]:
        if not file_path or not os.path.isfile(file_path):
            return None
        try:
            checksum_hex, _ = sha1_checksum(file_path)
            return checksum_hex
        except Exception as error:
            LOGGER.debug(f"Unable to compute Google Photos upload cache key for '{file_path}': {error}")
            return None

    def _remember_uploaded_media_item_id(self, file_path: str, media_item_id: str):
        cache_key = self._build_uploaded_media_item_cache_key(file_path)
        if not cache_key or not media_item_id:
            return
        self._ensure_uploaded_media_item_cache()
        with self._uploaded_media_item_cache_lock:
            self._uploaded_media_item_cache[cache_key] = str(media_item_id)

    def _lookup_uploaded_media_item_id(self, file_path: str) -> Optional[str]:
        cache_key = self._build_uploaded_media_item_cache_key(file_path)
        if not cache_key:
            return None
        self._ensure_uploaded_media_item_cache()
        with self._uploaded_media_item_cache_lock:
            return self._uploaded_media_item_cache.get(cache_key)

    def _resolve_existing_media_item_id(self, file_path: str, file_name: str) -> Optional[str]:
        cached_media_id = self._lookup_uploaded_media_item_id(file_path)
        if cached_media_id:
            return cached_media_id

        target_name = str(file_name or os.path.basename(file_path)).casefold()
        target_dt = None
        try:
            target_dt = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc)
        except Exception:
            target_dt = None

        best_media_id = None
        best_delta = None
        for item in self._search_media_items(album_id=""):
            candidate_name = str(item.get("filename", "")).casefold()
            if candidate_name != target_name:
                continue
            candidate_id = str(item.get("id", "")).strip()
            if not candidate_id:
                continue
            if target_dt is None:
                self._remember_uploaded_media_item_id(file_path, candidate_id)
                return candidate_id
            candidate_dt = self._to_datetime_utc(str((item.get("mediaMetadata", {}) or {}).get("creationTime", "")))
            if candidate_dt is None:
                delta = float("inf")
            else:
                delta = abs((candidate_dt - target_dt).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_media_id = candidate_id
                if delta <= 1:
                    break

        if best_media_id:
            self._remember_uploaded_media_item_id(file_path, best_media_id)
        return best_media_id

    def _batch_create_media_item(self, upload_token: str, file_name: str, album_id: str = "", file_path: str = "", resolve_duplicate_id: bool = True) -> Tuple[Optional[str], bool]:
        payload = {
            "newMediaItems": [
                {
                    "description": "",
                    "simpleMediaItem": {
                        "uploadToken": upload_token,
                        "fileName": file_name,
                    },
                }
            ]
        }
        if album_id:
            payload["albumId"] = album_id
        response = self._request("POST", f"{self.API_BASE}/mediaItems:batchCreate", expected=(200,), json=payload)
        data = response.json() or {}
        results = data.get("newMediaItemResults", []) or []
        if not results:
            raise RuntimeError("Google Photos batchCreate returned no results.")
        result = results[0] or {}
        status = result.get("status", {}) or {}
        code = int(status.get("code", 0) or 0)
        if code and code != 0:
            message = str(status.get("message", "Unknown error")).strip()
            lower = message.lower()
            is_dup = "already exists" in lower or "duplicate" in lower
            if is_dup:
                if not resolve_duplicate_id:
                    return None, True
                existing_media_id = self._resolve_existing_media_item_id(file_path=file_path, file_name=file_name) if file_path else None
                if existing_media_id:
                    return existing_media_id, True
                return None, True
            raise RuntimeError(f"Google Photos batchCreate failed: {message}")
        media_item = result.get("mediaItem", {}) or {}
        media_item_id = str(media_item.get("id", "")).strip()
        if not media_item_id:
            raise RuntimeError("Google Photos batchCreate did not return mediaItem id.")
        if file_path:
            self._remember_uploaded_media_item_id(file_path, media_item_id)
        return media_item_id, False

    def _download_media_item(self, media_item: Dict, output_file: str) -> str:
        base_url = str(media_item.get("baseUrl", "")).strip()
        if not base_url:
            raise RuntimeError(f"Missing baseUrl for media item '{media_item.get('id', '')}'.")
        mime = str(media_item.get("mimeType", "")).lower()
        download_url = f"{base_url}=dv" if mime.startswith("video/") else f"{base_url}=d"
        response = self._request("GET", download_url, expected=(200,))
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "wb") as fp:
            fp.write(response.content)
        return output_file

    def create_album(self, album_name: str, shared: bool = False, log_level=None):
        with set_log_level(LOGGER, log_level):
            response = self._request("POST", f"{self.API_BASE}/albums", expected=(200,), json={"album": {"title": str(album_name)}})
            data = response.json() or {}
            album = data.get("album", {}) or {}
            album_id = str(album.get("id", "")).strip()
            if not album_id:
                raise RuntimeError("Google Photos create album returned empty id.")
            return album_id

    def remove_album(self, album_id, album_name=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting albums via public Library API. No action applied.")
            return False

    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        with set_log_level(LOGGER, log_level):
            return self._list_albums()

    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        with set_log_level(LOGGER, log_level):
            albums = self._list_albums()
            shared = self._list_shared_albums()
            seen_ids = {a.get("id") for a in albums}
            for item in shared:
                if item.get("id") not in seen_ids:
                    albums.append(item)
            albums.sort(key=lambda a: a["albumName"].lower())
            return albums

    def get_album_assets_size(self, album_id, album_name=None, type="all", album_passphrase=None, album_scope=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            return len(self.get_all_assets_from_album(album_id=album_id, type=type, log_level=log_level))

    def get_album_assets_count(self, album_id, album_name=None, type="all", album_passphrase=None, album_scope=None, log_level=None):
        return self.get_album_assets_size(album_id=album_id, type="all", log_level=log_level)

    def album_exists(self, album_name, shared=False, log_level=None):
        with set_log_level(LOGGER, log_level):
            for album in self._list_albums():
                if album["albumName"].lower() == str(album_name).lower():
                    return True, album["id"]
            return False, None

    def get_assets_by_filters(self, type="all", is_not_in_album=None, is_archived=None, with_deleted=None, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or self.type or "all").lower()
            assets = []
            for item in self._search_media_items(album_id=""):
                filename = str(item.get("filename", ""))
                mime = str(item.get("mimeType", ""))
                if not self._is_supported_media(filename, mime):
                    continue
                payload = self._build_asset_payload(item)
                if not self._asset_matches_filters(
                    asset_datetime=payload.get("asset_datetime", ""),
                    asset_type=payload.get("type", ""),
                    selected_type=selected,
                ):
                    continue
                assets.append(payload)
            return assets

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", album_scope=None, album_expected_count=None, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or self.type or "all").lower()
            assets = []
            for item in self._search_media_items(album_id=str(album_id)):
                filename = str(item.get("filename", ""))
                mime = str(item.get("mimeType", ""))
                if not self._is_supported_media(filename, mime):
                    continue
                payload = self._build_asset_payload(item, album_name=album_name or "")
                if not self._asset_matches_filters(
                    asset_datetime=payload.get("asset_datetime", ""),
                    asset_type=payload.get("type", ""),
                    selected_type=selected,
                ):
                    continue
                assets.append(payload)
            return assets

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, album_scope=None, album_expected_count=None, log_level=logging.WARNING):
        return self.get_all_assets_from_album(
            album_id=album_id,
            album_name=album_name,
            type=type,
            album_scope=album_scope,
            album_expected_count=album_expected_count,
            log_level=log_level,
        )

    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or self.type or "all").lower()
            all_items: Dict[str, Dict] = {}
            for item in self._search_media_items(album_id=""):
                item_id = str(item.get("id", "")).strip()
                if item_id:
                    all_items[item_id] = item

            album_item_ids = set()
            for album in self._list_albums():
                for item in self._search_media_items(album_id=album["id"]):
                    item_id = str(item.get("id", "")).strip()
                    if item_id:
                        album_item_ids.add(item_id)

            assets = []
            for item_id, item in all_items.items():
                if item_id in album_item_ids:
                    continue
                filename = str(item.get("filename", ""))
                mime = str(item.get("mimeType", ""))
                if not self._is_supported_media(filename, mime):
                    continue
                payload = self._build_asset_payload(item)
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
            for album in self._list_albums():
                all_assets.extend(self.get_all_assets_from_album(album_id=album["id"], album_name=album["albumName"], log_level=log_level))
            return all_assets

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None, return_details=False):
        with set_log_level(LOGGER, log_level):
            media_ids = [str(item).strip() for item in (asset_ids or []) if str(item).strip()]
            if not media_ids:
                return 0
            added = 0
            chunk_size = 50
            for i in range(0, len(media_ids), chunk_size):
                chunk = media_ids[i:i + chunk_size]
                self._request(
                    "POST",
                    f"{self.API_BASE}/albums/{album_id}:batchAddMediaItems",
                    expected=(200,),
                    json={"mediaItemIds": chunk},
                )
                added += len(chunk)
            return added

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
            existing_albums = existing_albums if existing_albums is not None else (self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or [])
            plan = build_reusable_album_group(
                album_name=album_name,
                albums=existing_albums,
                allow_similar=True,
                exact_case_sensitive=False,
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
                        LOGGER.info(
                            f"Album Consolidated: '{redundant_name}' -> '{keeper_name}'. "
                            f"All {reassigned_count}/{total_redundant_assets} assets were confirmed in the keeper album, "
                            f"but the redundant album was kept because Google Photos does not support album deletion."
                        )
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
            albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or []
            if not albums:
                LOGGER.info("No albums found.")
                return 0, 0

            consolidation_groups = scan_album_consolidation_groups(
                albums=albums,
                exact_case_sensitive=False,
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
                f"Detected {redundant_albums_detected} redundant album variant(s). "
                f"Google Photos keeps redundant album containers because the public API does not support album deletion."
            )
            return families_consolidated, redundant_albums_detected

    def get_duplicates_assets(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return []

    def remove_assets(self, asset_ids, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting media items via public Library API. No action applied.")
            return 0

    def remove_duplicates_assets(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return 0

    def push_asset(self, file_path, log_level=None, resolve_duplicate_id=True):
        with set_log_level(LOGGER, log_level):
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            upload_token = self._create_upload_token(file_path)
            return self._batch_create_media_item(
                upload_token=upload_token,
                file_name=os.path.basename(file_path),
                album_id="",
                file_path=file_path,
                resolve_duplicate_id=resolve_duplicate_id,
            )

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_GooglePhotos", album_passphrase=None, album_id=None, album_scope=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            media_resp = self._request("GET", f"{self.API_BASE}/mediaItems/{asset_id}", expected=(200,))
            media_item = media_resp.json() or {}
            os.makedirs(download_folder, exist_ok=True)
            output_file = os.path.join(download_folder, str(asset_filename))
            output_file = self._download_media_item(media_item=media_item, output_file=output_file)
            update_metadata(file_path=output_file, date_time=asset_time, log_level=log_level)
            return output_file

    def push_albums(self, input_folder, subfolders_exclusion=FOLDERNAME_NO_ALBUMS, subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            if not os.path.isdir(input_folder):
                raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

            effective_folder_exclusions = merge_exclusion_patterns(
                self.exclude_folder_patterns,
                default_patterns=["@eaDir"] + convert_to_list(subfolders_exclusion, log_level=log_level),
            )
            subfolders = get_subfolders(
                input_folder=input_folder,
                exclusion_subfolders=effective_folder_exclusions,
                log_level=log_level,
            )
            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_duplicates_skipped = 0
            prefer_canonical_album_names = prefer_canonical_album_names_enabled(ARGS)
            consolidate_similar_albums = consolidate_similar_albums_enabled(ARGS)
            existing_albums = self.get_albums_owned_by_user(filter_assets=False, log_level=log_level) or []
            for folder in tqdm(subfolders, desc=f"{MSG_TAGS['INFO']}Uploading Albums to Google Photos", unit=" album"):
                album_name = os.path.basename(folder)
                media_files = [
                    f for f in get_all_files_paths(
                        folder,
                        exclusion_folders=effective_folder_exclusions,
                        exclusion_files=self.exclude_file_patterns,
                    )
                    if self._is_supported_media(os.path.basename(f))
                ]
                if not media_files:
                    total_albums_skipped += 1
                    continue
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
                            f"Reusing consolidated Google Photos album '{matched_name}' "
                            f"for source album '{album_name}'. Preferred keeper name: '{preferred_name}'."
                        )
                else:
                    matched_album, _, _ = find_reusable_album_candidate(
                        album_name=album_name,
                        albums=existing_albums,
                        allow_similar=False,
                        exact_case_sensitive=False,
                    )
                if not matched_album and prefer_canonical_album_names:
                    preferred_name = str(canonicalize_album_name_for_reuse(album_name) or album_name).strip() or album_name
                    if preferred_name.casefold() != album_name.casefold():
                        matched_album, _, _ = find_reusable_album_candidate(
                            album_name=preferred_name,
                            albums=existing_albums,
                            allow_similar=False,
                            exact_case_sensitive=False,
                        )
                        if matched_album:
                            LOGGER.info(
                                f"Reusing canonical Google Photos album '{preferred_name}' "
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
                    album_id = self.create_album(album_name=album_name_to_create, log_level=log_level)
                    if album_id:
                        existing_albums.append({"id": album_id, "albumName": album_name_to_create})
                        total_albums_uploaded += 1
                album_media_ids = []
                for file_path in tqdm(
                    media_files,
                    desc=f"{MSG_TAGS['INFO']}   Uploading '{album_name}' Assets",
                    unit=" assets",
                ):
                    media_id, is_dup = self.push_asset(file_path, log_level=log_level)
                    if is_dup:
                        total_duplicates_skipped += 1
                    elif media_id:
                        total_assets_uploaded += 1
                    if media_id:
                        album_media_ids.append(media_id)
                if album_media_ids:
                    self.add_assets_to_album(album_id=album_id, asset_ids=album_media_ids, album_name=album_name, log_level=log_level)
            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, 0, total_duplicates_skipped

    def push_no_albums(self, input_folder, subfolders_exclusion=f"{FOLDERNAME_ALBUMS}", subfolders_inclusion=None, remove_duplicates=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            effective_folder_exclusions = merge_exclusion_patterns(
                self.exclude_folder_patterns,
                default_patterns=["@eaDir"] + convert_to_list(subfolders_exclusion, log_level=log_level),
            )
            files = [
                f for f in get_all_files_paths(
                    input_folder=input_folder,
                    exclusion_folders=effective_folder_exclusions,
                    exclusion_files=self.exclude_file_patterns,
                )
                if self._is_supported_media(os.path.basename(f))
            ]
            uploaded = 0
            duplicates = 0
            for file_path in tqdm(files, desc=f"{MSG_TAGS['INFO']}Uploading Assets without Albums to Google Photos", unit=" asset"):
                media_id, is_dup = self.push_asset(file_path, log_level=log_level)
                if is_dup:
                    duplicates += 1
                elif media_id:
                    uploaded += 1
            return uploaded, duplicates

    def push_all(self, input_folder, album_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            album_folders = convert_to_list(album_folders, log_level=log_level)
            albums_folder_included = any(str(folder or "").strip().lower() == self.albums_root_name.lower() for folder in album_folders)
            if not albums_folder_included:
                album_folders.append(self.albums_root_name)
            total_albums_uploaded = 0
            total_albums_skipped = 0
            total_assets_uploaded = 0
            total_assets_uploaded_within_albums = 0
            total_assets_uploaded_without_albums = 0
            total_duplicates_assets_skipped = 0

            for albums_folder in album_folders:
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

    def pull_albums(self, album_names="ALL", output_folder="Downloads_GooglePhotos", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target_names = [n.lower() for n in convert_to_list(album_names, log_level=log_level)] if album_names != "ALL" else ["all"]
            albums = self._list_albums()
            selected_albums = []
            for album in albums:
                name = album["albumName"]
                if "all" not in target_names and not any(match_pattern(name, pattern) for pattern in target_names):
                    continue
                selected_albums.append(album)
            downloaded_albums = 0
            downloaded_assets = 0
            root = os.path.join(output_folder, self.albums_root_name)
            os.makedirs(root, exist_ok=True)
            for album in tqdm(
                selected_albums,
                desc=f"{MSG_TAGS['INFO']}Downloading Albums from Google Photos",
                unit=" albums",
            ):
                name = album["albumName"]
                local_album = os.path.join(root, name)
                os.makedirs(local_album, exist_ok=True)
                album_assets = self.get_all_assets_from_album(album_id=album["id"], album_name=name, log_level=log_level)
                for asset in tqdm(
                    album_assets,
                    desc=f"{MSG_TAGS['INFO']}   Downloading '{name}' Assets",
                    unit=" assets",
                ):
                    self.pull_asset(
                        asset_id=asset["id"],
                        asset_filename=asset["filename"],
                        asset_time=asset["asset_datetime"],
                        download_folder=local_album,
                        log_level=log_level,
                    )
                    downloaded_assets += 1
                downloaded_albums += 1
            return downloaded_albums, downloaded_assets

    def pull_no_albums(self, output_folder="Downloads_GooglePhotos", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target = os.path.join(output_folder, self.no_albums_root_name)
            os.makedirs(target, exist_ok=True)
            downloaded = 0
            for asset in self.get_all_assets_without_albums(log_level=log_level):
                created_dt = self._to_datetime_utc(asset.get("asset_datetime", "")) or datetime.now(timezone.utc)
                year_str = created_dt.strftime("%Y")
                month_str = created_dt.strftime("%m")
                target_folder = os.path.join(target, year_str, month_str)
                os.makedirs(target_folder, exist_ok=True)
                self.pull_asset(
                    asset_id=asset["id"],
                    asset_filename=asset["filename"],
                    asset_time=asset["asset_datetime"],
                    download_folder=target_folder,
                    log_level=log_level,
                )
                downloaded += 1
            return downloaded

    def pull_all(self, output_folder="Downloads_GooglePhotos", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            albums_downloaded, assets_in_albums = self.pull_albums(album_names="ALL", output_folder=output_folder, log_level=log_level)
            assets_without_albums = self.pull_no_albums(output_folder=output_folder, log_level=log_level)
            total_assets = assets_in_albums + assets_without_albums
            return albums_downloaded, total_assets, assets_in_albums, assets_without_albums

    def remove_empty_folders(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return 0

    def remove_all_albums(self, remove_album_assets=False, request_user_confirmation=True, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting albums via public Library API. No action applied.")
            return 0, 0

    def remove_empty_albums(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting albums via public Library API. No action applied.")
            return 0

    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            return 0

    def merge_duplicates_albums(self, strategy="count", request_user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            return 0, 0

    def remove_orphan_assets(self, user_confirmation=True, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not expose orphan-assets semantics. No action applied.")
            return 0

    def remove_all_assets(self, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting media items via public Library API. No action applied.")
            return 0, 0

    def rename_albums(self, pattern, pattern_to_replace, request_user_confirmation=True, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support renaming albums via public Library API. No action applied.")
            return 0

    def remove_albums_by_name(self, pattern, remove_album_assets=False, request_user_confirmation=True, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting albums via public Library API. No action applied.")
            return 0, 0
