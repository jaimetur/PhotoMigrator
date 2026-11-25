"""
Import of Takeout files from Dropbox and OneDrive for the cloud service.

Google Takeout can deliver the export to Dropbox or OneDrive. The user signs in to that storage with OAuth (read-only
access) and chooses the folder; the files are listed to measure the size and downloaded when the task starts.
The access tokens are kept only in the encrypted credentials file of the task, which is destroyed with the task.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List
from urllib.parse import urlencode

import requests

TIMEOUT_SECONDS = 60
CHUNK_BYTES = 8 * 1024 * 1024
ARCHIVE_SUFFIXES = (".zip", ".tgz", ".tar.gz", ".tar")
PROVIDERS = ("dropbox", "onedrive")

DROPBOX_AUTHORIZE = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_TOKEN = "https://api.dropboxapi.com/oauth2/token"
DROPBOX_API = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT = "https://content.dropboxapi.com/2"

MS_AUTHORIZE = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_GRAPH = "https://graph.microsoft.com/v1.0"
MS_SCOPES = "offline_access Files.Read User.Read"


class RemoteError(RuntimeError):
    """A Dropbox or OneDrive call failed (the message never contains tokens)."""


def is_archive(name: str) -> bool:
    lowered = str(name or "").lower()
    return lowered.endswith(ARCHIVE_SUFFIXES)


def authorize_url(provider: str, client_id: str, redirect_uri: str, state: str) -> str:
    if provider == "dropbox":
        return DROPBOX_AUTHORIZE + "?" + urlencode({
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "token_access_type": "offline",
        })
    if provider == "onedrive":
        return MS_AUTHORIZE + "?" + urlencode({
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": MS_SCOPES,
            "state": state,
        })
    raise RemoteError(f"Unknown storage provider '{provider}'.")


def _token_request(url: str, data: Dict[str, str]) -> Dict[str, Any]:
    try:
        response = requests.post(url, data=data, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise RemoteError(f"Could not reach the storage provider ({type(exc).__name__}).") from exc
    if response.status_code != 200:
        raise RemoteError(f"The storage provider did not accept the authorization (HTTP {response.status_code}).")
    tokens = response.json()
    tokens["obtained_at"] = int(time.time())
    return tokens


def exchange_code(provider: str, client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict[str, Any]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if provider == "onedrive":
        data["scope"] = MS_SCOPES
    return _token_request(DROPBOX_TOKEN if provider == "dropbox" else MS_TOKEN, data)


def refresh_tokens(provider: str, client_id: str, client_secret: str, tokens: Dict[str, Any]) -> Dict[str, Any]:
    refresh_token = str(tokens.get("refresh_token") or "")
    if not refresh_token:
        raise RemoteError("The storage authorization expired. Connect the storage again.")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if provider == "onedrive":
        data["scope"] = MS_SCOPES
    fresh = _token_request(DROPBOX_TOKEN if provider == "dropbox" else MS_TOKEN, data)
    if not fresh.get("refresh_token"):
        fresh["refresh_token"] = refresh_token
    return fresh


def token_is_fresh(tokens: Dict[str, Any], margin_seconds: int = 300) -> bool:
    expires_in = int(tokens.get("expires_in") or 0)
    obtained_at = int(tokens.get("obtained_at") or 0)
    return bool(tokens.get("access_token")) and (not expires_in or time.time() < obtained_at + expires_in - margin_seconds)


class RemoteStorage:
    """Read-only access to the folders and files of one Dropbox or OneDrive account."""

    def __init__(self, provider: str, client_id: str, client_secret: str, tokens: Dict[str, Any],
                 on_tokens_changed: Callable[[Dict[str, Any]], None] | None = None) -> None:
        if provider not in PROVIDERS:
            raise RemoteError(f"Unknown storage provider '{provider}'.")
        self.provider = provider
        self.client_id = client_id
        self.client_secret = client_secret
        self.tokens = dict(tokens or {})
        self.on_tokens_changed = on_tokens_changed

    def _access_token(self) -> str:
        if not token_is_fresh(self.tokens):
            self.tokens = refresh_tokens(self.provider, self.client_id, self.client_secret, self.tokens)
            if self.on_tokens_changed:
                self.on_tokens_changed(self.tokens)
        return str(self.tokens.get("access_token") or "")

    def _call(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {self._access_token()}"
        try:
            response = requests.request(method, url, headers=headers, timeout=kwargs.pop("timeout", TIMEOUT_SECONDS), **kwargs)
        except requests.RequestException as exc:
            raise RemoteError(f"Could not reach the storage provider ({type(exc).__name__}).") from exc
        if response.status_code >= 400:
            raise RemoteError(f"The storage provider refused the request (HTTP {response.status_code}).")
        return response

    # --- Listing -------------------------------------------------------------------------------------------------
    def list_folder(self, path: str = "") -> List[Dict[str, Any]]:
        """Direct children of a folder: [{"name", "path", "is_folder", "size"}]."""
        entries: List[Dict[str, Any]] = []
        if self.provider == "dropbox":
            body = {"path": "" if path in ("", "/") else path, "recursive": False, "limit": 2000}
            data = self._call("POST", f"{DROPBOX_API}/files/list_folder", json=body).json()
            while True:
                for item in data.get("entries", []):
                    entries.append({
                        "name": item.get("name", ""),
                        "path": item.get("path_display") or item.get("path_lower") or "",
                        "is_folder": item.get(".tag") == "folder",
                        "size": int(item.get("size") or 0),
                    })
                if not data.get("has_more"):
                    break
                data = self._call("POST", f"{DROPBOX_API}/files/list_folder/continue", json={"cursor": data.get("cursor")}).json()
        else:
            clean = str(path or "").strip("/")
            url = f"{MS_GRAPH}/me/drive/root/children" if not clean else f"{MS_GRAPH}/me/drive/root:/{clean}:/children"
            while url:
                data = self._call("GET", url, params={"$top": "999"} if "?" not in url else None).json()
                for item in data.get("value", []):
                    entries.append({
                        "name": item.get("name", ""),
                        "path": f"/{clean}/{item.get('name', '')}" if clean else f"/{item.get('name', '')}",
                        "is_folder": "folder" in item,
                        "size": int(item.get("size") or 0),
                        "id": item.get("id", ""),
                    })
                url = data.get("@odata.nextLink") or ""
        entries.sort(key=lambda entry: (not entry["is_folder"], str(entry["name"]).lower()))
        return entries

    def archives_in(self, path: str) -> List[Dict[str, Any]]:
        """Takeout archives directly inside a folder."""
        return [entry for entry in self.list_folder(path) if not entry["is_folder"] and is_archive(entry["name"])]

    # --- Download ------------------------------------------------------------------------------------------------
    def _stream(self, entry: Dict[str, Any], offset: int) -> Iterator[bytes]:
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        if self.provider == "dropbox":
            headers["Dropbox-API-Arg"] = json.dumps({"path": entry["path"]})
            response = self._call("POST", f"{DROPBOX_CONTENT}/files/download", headers=headers, stream=True, timeout=300)
        else:
            response = self._call("GET", f"{MS_GRAPH}/me/drive/items/{entry['id']}/content", headers=headers, stream=True, timeout=300)
        if offset and response.status_code != 206:
            raise RemoteError("The storage provider does not support resuming this download.")
        yield from response.iter_content(CHUNK_BYTES)

    def download(self, entry: Dict[str, Any], target: Path, should_stop: Callable[[], bool] | None = None,
                 on_progress: Callable[[int], None] | None = None) -> None:
        """Download one file, resuming a partial file when it exists."""
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        expected = int(entry.get("size") or 0)
        if expected and offset > expected:
            partial.unlink()
            offset = 0
        if not expected or offset < expected:
            with open(partial, "ab") as handle:
                for chunk in self._stream(entry, offset):
                    if should_stop and should_stop():
                        raise RemoteError("Download stopped.")
                    handle.write(chunk)
                    if on_progress:
                        on_progress(len(chunk))
        if expected and partial.stat().st_size != expected:
            raise RemoteError(f"The download of '{entry.get('name')}' is incomplete.")
        partial.replace(target)
