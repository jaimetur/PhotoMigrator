"""
Checks made before a cloud service task is quoted.

* check_target(): signs in to the destination and, where the service allows deleting it again, uploads a tiny test
  image and removes it. Google Photos cannot delete what it receives, so only the permission to upload is checked.
* source_size(): size in bytes of the library of a source service (cloud to cloud migrations).

Only small HTTP calls are made here; the migration itself runs with the PhotoMigrator command line.
"""

from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from xml.etree import ElementTree

import requests

TIMEOUT_SECONDS = 60
SERVICES = ("immich", "synology", "nextcloud", "google-photos")
SOURCE_SERVICES = ("immich", "synology", "nextcloud")
# Small valid JPEG (8x8 pixels), used for the test upload.
TEST_IMAGE = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC"
    "0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAI"
    "AAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhBy"
    "JxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKT"
    "lJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAA"
    "AAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRom"
    "JygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExc"
    "bHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDlKKKK/WT48//Z"
)

# Fields the user gives for each service (the Config.ini keys without the account suffix).
CREDENTIAL_FIELDS: Dict[str, List[Dict[str, Any]]] = {
    "immich": [
        {"key": "URL", "label": "Server address", "required": True},
        {"key": "API_KEY_USER", "label": "API key", "secret": True},
        {"key": "USERNAME", "label": "Email"},
        {"key": "PASSWORD", "label": "Password", "secret": True},
    ],
    "synology": [
        {"key": "URL", "label": "Server address", "required": True},
        {"key": "USERNAME", "label": "Username", "required": True},
        {"key": "PASSWORD", "label": "Password", "secret": True, "required": True},
    ],
    "nextcloud": [
        {"key": "URL", "label": "Server address", "required": True},
        {"key": "USERNAME", "label": "Username", "required": True},
        {"key": "PASSWORD", "label": "App password", "secret": True, "required": True},
        {"key": "PHOTOS_FOLDER", "label": "Photos folder", "default": "/Photos/ALL_Photos"},
        {"key": "ALBUMS_FOLDER", "label": "Albums folder", "default": "/Photos/Albums"},
    ],
    "google-photos": [
        {"key": "CLIENT_ID", "label": "OAuth client ID", "required": True},
        {"key": "CLIENT_SECRET", "label": "OAuth client secret", "secret": True, "required": True},
        {"key": "REFRESH_TOKEN", "label": "Refresh token", "secret": True, "required": True},
    ],
}

# How the user's saved Config.ini keys map to these fields, per service: (section, prefix, url key).
CONFIG_SECTIONS = {
    "immich": ("Immich Photos", "IMMICH_", "IMMICH_URL"),
    "synology": ("Synology Photos", "SYNOLOGY_", "SYNOLOGY_URL"),
    "nextcloud": ("NextCloud Photos", "NEXTCLOUD_", "NEXTCLOUD_URL"),
    "google-photos": ("Google Photos", "GOOGLE_PHOTOS_", ""),
}


class ProbeError(RuntimeError):
    """The check failed; the message is shown to the user (it never contains credentials)."""


def validate_credentials(service: str, values: Dict[str, str]) -> Dict[str, str]:
    if service not in CREDENTIAL_FIELDS:
        raise ProbeError(f"Unknown service '{service}'.")
    clean: Dict[str, str] = {}
    for field in CREDENTIAL_FIELDS[service]:
        value = str(values.get(field["key"]) or field.get("default") or "").strip()
        if field.get("required") and not value:
            raise ProbeError(f"Fill in '{field['label']}'.")
        clean[field["key"]] = value
    if "URL" in clean:
        clean["URL"] = clean["URL"].rstrip("/")
        if not clean["URL"].lower().startswith(("http://", "https://")):
            raise ProbeError("The server address must start with http:// or https://.")
    if service == "immich" and not clean.get("API_KEY_USER") and not (clean.get("USERNAME") and clean.get("PASSWORD")):
        raise ProbeError("Give an API key, or an email and password.")
    return clean


def credentials_from_config(service: str, config_values: Dict[str, Dict[str, str]], account_id: int) -> Dict[str, str]:
    """Credentials of one saved account (Settings > Service credentials) in the format of CREDENTIAL_FIELDS."""
    section, prefix, url_key = CONFIG_SECTIONS[service]
    stored = config_values.get(section, {}) or {}
    out: Dict[str, str] = {}
    for field in CREDENTIAL_FIELDS[service]:
        if field["key"] == "URL":
            out["URL"] = str(stored.get(url_key) or "")
        else:
            out[field["key"]] = str(stored.get(f"{prefix}{field['key']}_{account_id}") or "")
    return out


def config_lines(service: str, values: Dict[str, str], account_id: int) -> Tuple[str, Dict[str, str]]:
    """Config.ini section name and keys for one account of a task."""
    section, prefix, url_key = CONFIG_SECTIONS[service]
    keys: Dict[str, str] = {}
    for key, value in values.items():
        if key == "URL":
            keys[url_key] = value
        else:
            keys[f"{prefix}{key}_{account_id}"] = value
    return section, keys


# --- Immich -------------------------------------------------------------------------------------------------------
def _immich_headers(values: Dict[str, str]) -> Dict[str, str]:
    if values.get("API_KEY_USER"):
        return {"x-api-key": values["API_KEY_USER"], "Accept": "application/json"}
    response = _http("POST", f"{values['URL']}/api/auth/login", json={"email": values.get("USERNAME"), "password": values.get("PASSWORD")})
    token = str(response.json().get("accessToken") or "")
    if not token:
        raise ProbeError("Immich did not accept the email and password.")
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _immich_check(values: Dict[str, str]) -> None:
    headers = _immich_headers(values)
    _http("GET", f"{values['URL']}/api/users/me", headers=headers)
    now = datetime.now(timezone.utc).isoformat()
    response = _http(
        "POST",
        f"{values['URL']}/api/assets",
        headers=headers,
        files={"assetData": ("photomigrator-test.jpg", TEST_IMAGE, "image/jpeg")},
        data={"deviceAssetId": f"photomigrator-test-{uuid.uuid4().hex}", "deviceId": "PhotoMigrator", "fileCreatedAt": now, "fileModifiedAt": now},
    )
    asset_id = str(response.json().get("id") or "")
    if asset_id:
        _http("DELETE", f"{values['URL']}/api/assets", headers=headers, json={"ids": [asset_id], "force": True})


def _immich_size(values: Dict[str, str]) -> int:
    headers = _immich_headers(values)
    me = _http("GET", f"{values['URL']}/api/users/me", headers=headers).json()
    usage = int(me.get("quotaUsageInBytes") or 0)
    if usage:
        return usage
    total, page = 0, 1
    while page:
        data = _http("POST", f"{values['URL']}/api/search/metadata", headers=headers, json={"page": page, "size": 1000, "withExif": True}).json()
        assets = (data.get("assets") or {})
        for item in assets.get("items", []):
            total += int(((item.get("exifInfo") or {}).get("fileSizeInByte")) or 0)
        page = int(assets.get("nextPage") or 0)
    return total


# --- Synology Photos ----------------------------------------------------------------------------------------------
def _synology_login(values: Dict[str, str]) -> str:
    data = _http("GET", f"{values['URL']}/webapi/auth.cgi", params={
        "api": "SYNO.API.Auth", "version": "6", "method": "login",
        "account": values["USERNAME"], "passwd": values["PASSWORD"], "format": "sid",
    }).json()
    if not data.get("success"):
        code = ((data.get("error") or {}).get("code"))
        if code in (403, 406):
            raise ProbeError("Synology asks for a two-step verification code. Use an account without it for this task.")
        raise ProbeError("Synology did not accept the username and password.")
    return str(data["data"]["sid"])


def _synology_items(values: Dict[str, str], sid: str, offset: int, limit: int) -> List[Dict[str, Any]]:
    data = _http("GET", f"{values['URL']}/webapi/entry.cgi", params={
        "api": "SYNO.Foto.Browse.Item", "version": "1", "method": "list",
        "offset": str(offset), "limit": str(limit), "_sid": sid,
    }).json()
    if not data.get("success"):
        raise ProbeError("Synology Photos did not allow reading the library. Check that Synology Photos is installed and the user can use it.")
    return list((data.get("data") or {}).get("list") or [])


def _synology_check(values: Dict[str, str]) -> None:
    sid = _synology_login(values)
    _synology_items(values, sid, 0, 1)


def _synology_size(values: Dict[str, str]) -> int:
    sid = _synology_login(values)
    total, offset, limit = 0, 0, 5000
    while True:
        items = _synology_items(values, sid, offset, limit)
        total += sum(int(item.get("filesize") or 0) for item in items)
        if len(items) < limit:
            return total
        offset += limit


# --- NextCloud ----------------------------------------------------------------------------------------------------
def _nextcloud_url(values: Dict[str, str], folder: str) -> str:
    folder = "/" + str(folder or "").strip("/")
    return f"{values['URL']}/remote.php/dav/files/{values['USERNAME']}{folder.rstrip('/')}"


def _nextcloud_folder_size(values: Dict[str, str], folder: str) -> int:
    body = '<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop><oc:size/></d:prop></d:propfind>'
    response = _http("PROPFIND", _nextcloud_url(values, folder), auth=(values["USERNAME"], values["PASSWORD"]),
                     headers={"Depth": "0", "Content-Type": "application/xml"}, data=body, allow_404=True)
    if response.status_code == 404:
        return 0
    tree = ElementTree.fromstring(response.content)
    node = tree.find(".//{http://owncloud.org/ns}size")
    return int(node.text or 0) if node is not None and node.text else 0


def _nextcloud_check(values: Dict[str, str]) -> None:
    folder = values.get("PHOTOS_FOLDER") or "/Photos/ALL_Photos"
    auth = (values["USERNAME"], values["PASSWORD"])
    # Create the folder chain when it does not exist (MKCOL answers 405 when it already exists).
    current = ""
    for part in [p for p in folder.strip("/").split("/") if p]:
        current += f"/{part}"
        _http("MKCOL", _nextcloud_url(values, current), auth=auth, allow_codes=(201, 405))
    target = f"{_nextcloud_url(values, folder)}/photomigrator-test-{uuid.uuid4().hex}.jpg"
    _http("PUT", target, auth=auth, data=TEST_IMAGE, allow_codes=(200, 201, 204))
    _http("DELETE", target, auth=auth, allow_codes=(200, 204, 404))


def _nextcloud_size(values: Dict[str, str]) -> int:
    photos = _nextcloud_folder_size(values, values.get("PHOTOS_FOLDER") or "/Photos/ALL_Photos")
    albums = _nextcloud_folder_size(values, values.get("ALBUMS_FOLDER") or "/Photos/Albums")
    return photos + albums


# --- Google Photos ------------------------------------------------------------------------------------------------
def _google_photos_check(values: Dict[str, str]) -> None:
    from Features.GooglePhotos.GooglePhotosAuthorize import SCOPE_APPEND_ONLY, missing_scopes

    response = _http("POST", "https://oauth2.googleapis.com/token", data={
        "client_id": values["CLIENT_ID"], "client_secret": values["CLIENT_SECRET"],
        "refresh_token": values["REFRESH_TOKEN"], "grant_type": "refresh_token",
    }, allow_codes=(200, 400, 401))
    if response.status_code != 200:
        raise ProbeError("Google did not accept the client ID, client secret and refresh token.")
    if SCOPE_APPEND_ONLY in missing_scopes(str(response.json().get("scope") or "")):
        raise ProbeError("The Google Photos token cannot add photos to the library. Create it again and tick every permission checkbox.")


# --- Common -------------------------------------------------------------------------------------------------------
def _http(method: str, url: str, allow_404: bool = False, allow_codes: Tuple[int, ...] = (), **kwargs: Any) -> requests.Response:
    kwargs.setdefault("timeout", TIMEOUT_SECONDS)
    try:
        response = requests.request(method, url, **kwargs)
    except requests.exceptions.SSLError as exc:
        raise ProbeError("The server certificate is not valid (HTTPS).") from exc
    except requests.RequestException as exc:
        raise ProbeError(f"Could not connect to {url.split('/')[2] if '//' in url else url}. Check the address and that the server is reachable from the internet.") from exc
    if allow_codes and response.status_code in allow_codes:
        return response
    if allow_404 and response.status_code == 404:
        return response
    if response.status_code in (401, 403):
        raise ProbeError("The server did not accept the credentials.")
    if response.status_code >= 400:
        raise ProbeError(f"The server answered with an error (HTTP {response.status_code}).")
    return response


_CHECKS = {"immich": _immich_check, "synology": _synology_check, "nextcloud": _nextcloud_check, "google-photos": _google_photos_check}
_SIZES = {"immich": _immich_size, "synology": _synology_size, "nextcloud": _nextcloud_size}


def check_target(service: str, values: Dict[str, str]) -> Dict[str, Any]:
    started = time.monotonic()
    _CHECKS[service](validate_credentials(service, values))
    return {"ok": True, "seconds": round(time.monotonic() - started, 1)}


def check_source(service: str, values: Dict[str, str]) -> int:
    if service not in _SIZES:
        raise ProbeError(f"'{service}' cannot be used as a source.")
    return int(_SIZES[service](validate_credentials(service, values)))
