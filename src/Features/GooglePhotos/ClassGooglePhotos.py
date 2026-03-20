import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

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
from Utils.GeneralUtils import convert_to_list, match_pattern, replace_pattern, tqdm, update_metadata


class ClassGooglePhotos:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://photoslibrary.googleapis.com/v1"
    UPLOADS_URL = f"{API_BASE}/uploads"

    def __init__(self, account_id: int = 1):
        self.account_id = int(account_id or 1)
        self.client_name = "Google Photos"
        self.session: Optional[requests.Session] = None
        self.timeout_seconds = 60

        self.client_id = ""
        self.client_secret = ""
        self.refresh_token = ""
        self.access_token = ""

        self.albums_root_name = FOLDERNAME_ALBUMS
        self.no_albums_root_name = FOLDERNAME_NO_ALBUMS
        self.ALLOWED_PHOTO_EXTENSIONS = [ext.lower() for ext in PHOTO_EXT]
        self.ALLOWED_VIDEO_EXTENSIONS = [ext.lower() for ext in VIDEO_EXT]

    def get_client_name(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            return self.client_name

    def read_config_file(self, config_file=CONFIGURATION_FILE, log_level=None):
        with set_log_level(LOGGER, log_level):
            config = load_config(config_file=config_file, section_to_load="Google Photos")
            section = config.get("Google Photos", {})
            suffix = str(self.account_id)

            self.client_id = section.get(f"GOOGLE_PHOTOS_CLIENT_ID_{suffix}", "").strip()
            self.client_secret = section.get(f"GOOGLE_PHOTOS_CLIENT_SECRET_{suffix}", "").strip()
            self.refresh_token = section.get(f"GOOGLE_PHOTOS_REFRESH_TOKEN_{suffix}", "").strip()

            if not self.client_id:
                raise ValueError(f"Missing GOOGLE_PHOTOS_CLIENT_ID_{suffix} in [Google Photos]")
            if not self.client_secret:
                raise ValueError(f"Missing GOOGLE_PHOTOS_CLIENT_SECRET_{suffix} in [Google Photos]")
            if not self.refresh_token:
                raise ValueError(f"Missing GOOGLE_PHOTOS_REFRESH_TOKEN_{suffix} in [Google Photos]")

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
            self._refresh_access_token()
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                }
            )
            self._list_albums()
            LOGGER.info(f"{MSG_TAGS['INFO']}Logged in to Google Photos account {self.account_id}.")
            return True

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
        if self.session is None:
            raise RuntimeError("Google Photos session is not initialized. Call login() first.")

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

    def _batch_create_media_item(self, upload_token: str, file_name: str, album_id: str = "") -> Tuple[str, bool]:
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
                return f"duplicate::{file_name}", True
            raise RuntimeError(f"Google Photos batchCreate failed: {message}")
        media_item = result.get("mediaItem", {}) or {}
        media_item_id = str(media_item.get("id", "")).strip()
        if not media_item_id:
            raise RuntimeError("Google Photos batchCreate did not return mediaItem id.")
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

    def create_album(self, album_name: str, log_level=None):
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

    def get_album_assets_size(self, album_id, type="all", log_level=None):
        with set_log_level(LOGGER, log_level):
            return len(self.get_all_assets_from_album(album_id=album_id, type=type, log_level=log_level))

    def get_album_assets_count(self, album_id, log_level=None):
        return self.get_album_assets_size(album_id=album_id, type="all", log_level=log_level)

    def album_exists(self, album_name, log_level=None):
        with set_log_level(LOGGER, log_level):
            for album in self._list_albums():
                if album["albumName"].lower() == str(album_name).lower():
                    return True, album["id"]
            return False, None

    def get_assets_by_filters(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
            assets = []
            for item in self._search_media_items(album_id=""):
                filename = str(item.get("filename", ""))
                mime = str(item.get("mimeType", ""))
                if not self._is_supported_media(filename, mime):
                    continue
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename, mime):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename, mime):
                    continue
                assets.append(self._build_asset_payload(item))
            return assets

    def get_all_assets_from_album(self, album_id, album_name=None, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
            assets = []
            for item in self._search_media_items(album_id=str(album_id)):
                filename = str(item.get("filename", ""))
                mime = str(item.get("mimeType", ""))
                if not self._is_supported_media(filename, mime):
                    continue
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename, mime):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename, mime):
                    continue
                assets.append(self._build_asset_payload(item, album_name=album_name or ""))
            return assets

    def get_all_assets_from_album_shared(self, album_id, album_name=None, type="all", album_passphrase=None, log_level=logging.WARNING):
        return self.get_all_assets_from_album(album_id=album_id, album_name=album_name, type=type, log_level=log_level)

    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            selected = str(type or "all").lower()
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
                if selected in ("image", "images", "photo", "photos") and not self._is_photo(filename, mime):
                    continue
                if selected in ("video", "videos") and not self._is_video(filename, mime):
                    continue
                assets.append(self._build_asset_payload(item))
            return assets

    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            all_assets: List[Dict[str, str]] = []
            for album in self._list_albums():
                all_assets.extend(self.get_all_assets_from_album(album_id=album["id"], album_name=album["albumName"], log_level=log_level))
            return all_assets

    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            media_ids = [str(item).strip() for item in (asset_ids or []) if str(item).strip() and not str(item).startswith("duplicate::")]
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

    def push_asset(self, file_path, log_level=None):
        with set_log_level(LOGGER, log_level):
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            upload_token = self._create_upload_token(file_path)
            return self._batch_create_media_item(upload_token=upload_token, file_name=os.path.basename(file_path), album_id="")

    def pull_asset(self, asset_id, asset_filename, asset_time, download_folder="Downloaded_GooglePhotos", album_passphrase=None, log_level=None):
        with set_log_level(LOGGER, log_level):
            media_resp = self._request("GET", f"{self.API_BASE}/mediaItems/{asset_id}", expected=(200,))
            media_item = media_resp.json() or {}
            os.makedirs(download_folder, exist_ok=True)
            output_file = os.path.join(download_folder, str(asset_filename))
            output_file = self._download_media_item(media_item=media_item, output_file=output_file)
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
            for folder in tqdm(subfolders, desc=f"{MSG_TAGS['INFO']}Uploading Albums to Google Photos", unit=" album"):
                album_name = os.path.basename(folder)
                media_files = [f for f in get_all_files_paths(folder) if self._is_supported_media(os.path.basename(f))]
                if not media_files:
                    total_albums_skipped += 1
                    continue
                exists, album_id = self.album_exists(album_name=album_name, log_level=log_level)
                if not exists or not album_id:
                    album_id = self.create_album(album_name=album_name, log_level=log_level)
                    total_albums_uploaded += 1
                for file_path in media_files:
                    upload_token = self._create_upload_token(file_path)
                    media_id, is_dup = self._batch_create_media_item(upload_token, os.path.basename(file_path), album_id=album_id)
                    if is_dup or str(media_id).startswith("duplicate::"):
                        total_duplicates_skipped += 1
                    else:
                        total_assets_uploaded += 1
            return total_albums_uploaded, total_albums_skipped, total_assets_uploaded, 0, total_duplicates_skipped

    def push_no_albums(self, input_folder, subfolders_exclusion=f"{FOLDERNAME_ALBUMS}", remove_duplicates=False, log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            files = [f for f in get_all_files_paths(input_folder=input_folder, exclusion_folders=subfolders_exclusion) if self._is_supported_media(os.path.basename(f))]
            uploaded = 0
            duplicates = 0
            for file_path in tqdm(files, desc=f"{MSG_TAGS['INFO']}Uploading Assets without Albums to Google Photos", unit=" asset"):
                upload_token = self._create_upload_token(file_path)
                media_id, is_dup = self._batch_create_media_item(upload_token, os.path.basename(file_path), album_id="")
                if is_dup or str(media_id).startswith("duplicate::"):
                    duplicates += 1
                else:
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

    def pull_albums(self, albums_name="ALL", output_folder="Downloads_GooglePhotos", log_level=logging.WARNING):
        with set_log_level(LOGGER, log_level):
            target_names = [n.lower() for n in convert_to_list(albums_name, log_level=log_level)] if albums_name != "ALL" else ["all"]
            albums = self._list_albums()
            downloaded_albums = 0
            downloaded_assets = 0
            root = os.path.join(output_folder, self.albums_root_name)
            os.makedirs(root, exist_ok=True)
            for album in albums:
                name = album["albumName"]
                if "all" not in target_names and not any(match_pattern(name, pattern) for pattern in target_names):
                    continue
                local_album = os.path.join(root, name)
                os.makedirs(local_album, exist_ok=True)
                for asset in self.get_all_assets_from_album(album_id=album["id"], album_name=name, log_level=log_level):
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
                self.pull_asset(
                    asset_id=asset["id"],
                    asset_filename=asset["filename"],
                    asset_time=asset["asset_datetime"],
                    download_folder=target,
                    log_level=log_level,
                )
                downloaded += 1
            return downloaded

    def pull_ALL(self, output_folder="Downloads_GooglePhotos", log_level=logging.WARNING):
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

    def rename_albums(self, pattern, pattern_to_replace, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support renaming albums via public Library API. No action applied.")
            return 0

    def remove_albums_by_name(self, pattern, removeAlbumsAssets=False, log_level=None):
        with set_log_level(LOGGER, log_level):
            LOGGER.info(f"{MSG_TAGS['WARNING']}Google Photos API does not support deleting albums via public Library API. No action applied.")
            return 0, 0

