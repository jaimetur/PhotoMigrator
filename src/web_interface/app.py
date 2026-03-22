import argparse
import base64
from collections import deque
from configparser import ConfigParser
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, TextIO
from zoneinfo import available_timezones

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
CLI_ENTRYPOINT = SRC_ROOT / "PhotoMigrator.py"
CONFIG_FILE_PATH = Path(os.environ.get("PHOTOMIGRATOR_CONFIG_PATH", "/app/config/Config.ini"))
STATE_FILE_PATH = Path(os.environ.get("PHOTOMIGRATOR_STATE_PATH", "/app/config/web_interface_state.json"))
WEB_HOME_PATH = Path(os.environ.get("PHOTOMIGRATOR_DOCKER_BASE_PATH", "/app/data")).resolve()
WEB_FS_ROOT = WEB_HOME_PATH if WEB_HOME_PATH.exists() else PROJECT_ROOT.resolve()
DELETE_ALLOWED_ROOTS_DEFAULT = [Path("/app/data"), Path("/app/config"), Path("/app/volumes")]
_delete_roots_env = [item.strip() for item in os.environ.get("PHOTOMIGRATOR_WEB_DELETE_ROOTS", "").split(",") if item.strip()]
DELETE_ALLOWED_ROOTS = [Path(item).expanduser().resolve() for item in _delete_roots_env] if _delete_roots_env else [p.resolve() for p in DELETE_ALLOWED_ROOTS_DEFAULT]
WEB_DB_PATH = Path(os.environ.get("PHOTOMIGRATOR_WEB_DB_PATH", "/app/config/web_interface.db"))
WEB_CONFIG_TEMPLATE_PATH = Path(os.environ.get("PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH", "/app/default_config.ini"))
WEB_CONFIG_CACHE_DIR = Path(os.environ.get("PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR", "/app/config/generated"))
WEB_SESSION_COOKIE = "photomigrator_session"
WEB_SESSION_TTL_SECONDS = int(os.environ.get("PHOTOMIGRATOR_WEB_SESSION_TTL_SECONDS", "86400"))
WEB_SECRET = os.environ.get("PHOTOMIGRATOR_WEB_SECRET", "change-me-photomigrator-web-secret")
WEB_BOOTSTRAP_ADMIN_USER = os.environ.get("PHOTOMIGRATOR_BOOTSTRAP_ADMIN_USER", "admin")
WEB_BOOTSTRAP_ADMIN_PASS = os.environ.get("PHOTOMIGRATOR_BOOTSTRAP_ADMIN_PASS", "admin123")
WEB_USER_ROOT_DATA = Path(os.environ.get("PHOTOMIGRATOR_WEB_USER_ROOT_DATA", "/app/data")).resolve()
WEB_USER_ROOT_VOLUME1 = Path(os.environ.get("PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1", "/app/volumes")).resolve()
CONFIG_SECTIONS_ORDER = [
    "TimeZone",
    "Web Interface",
    "Google Takeout",
    "Google Photos",
    "Synology Photos",
    "Immich Photos",
    "NextCloud Photos",
]
TIMEZONE_DEFAULT = "Europe/Madrid"
TIMEZONE_CHOICES = sorted(list(available_timezones()))
WEB_INTERFACE_SECTION_NAME = "Web Interface"
WEB_INTERFACE_THEME_KEY = "THEME"
WEB_INTERFACE_THEME_DEFAULT = "ocean"
WEB_INTERFACE_THEME_CHOICES = ["ocean", "emerald", "dark", "sunset"]
WEB_ALLOWED_ROLES = {"admin", "user", "demo"}
WEB_BACKUP_DEFAULT_DIR = Path(os.environ.get("PHOTOMIGRATOR_WEB_BACKUP_DIR", "/app/config/backups"))
WEB_BACKUP_DEFAULT_INTERVAL_MINUTES = int(os.environ.get("PHOTOMIGRATOR_WEB_BACKUP_INTERVAL_MINUTES", "1440"))
WEB_BACKUP_DEFAULT_KEEP_LAST = int(os.environ.get("PHOTOMIGRATOR_WEB_BACKUP_KEEP_LAST", "14"))
WEB_BACKUP_DEFAULT_MODE = os.environ.get("PHOTOMIGRATOR_WEB_BACKUP_MODE", "daily_2am").strip().lower()
WEB_BACKUP_MODES = {"hourly", "daily_2am", "weekly_monday_2am"}
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Core.ArgsParser import parse_arguments  # noqa: E402
from Core.GlobalVariables import TOOL_DATE, TOOL_NAME, TOOL_VERSION, TAKEOUT_SPECIAL_FOLDER_NAMES  # noqa: E402


BOOL_VALUE_DESTS = {
    "move-assets",
    "dashboard",
    "parallel-migration",
    "show-gpth-info",
    "show-gpth-errors",
}

AUTOMATION_DESTS = {
    "source",
    "target",
    "move-assets",
    "dashboard",
    "parallel-migration",
}

GOOGLE_DESTS = {
    "google-takeout",
    "google-output-folder-suffix",
    "google-albums-folders-structure",
    "google-no-albums-folders-structure",
    "google-ignore-check-structure",
    "google-no-symbolic-albums",
    "google-remove-duplicates-files",
    "google-rename-albums-folders",
    "google-skip-extras-files",
    "google-skip-move-albums",
    "google-skip-gpth-tool",
    "google-skip-preprocess",
    "google-skip-postprocess",
    "google-keep-takeout-folder",
    "show-gpth-info",
    "show-gpth-errors",
    "gpth-no-log",
}

CLOUD_DESTS = {
    "upload-albums",
    "download-albums",
    "upload-all",
    "download-all",
    "rename-albums",
    "remove-albums",
    "remove-all-albums",
    "remove-all-assets",
    "remove-empty-albums",
    "remove-duplicates-albums",
    "merge-duplicates-albums",
    "remove-orphan-assets",
    "one-time-password",
}

CLOUD_ACTIONS_AVAILABLE_BY_TAB = {
    "google_photos": {"upload-albums", "download-albums", "upload-all", "download-all"},
    "synology_photos": {
        "upload-albums",
        "download-albums",
        "upload-all",
        "download-all",
        "rename-albums",
        "remove-albums",
        "remove-all-albums",
        "remove-all-assets",
        "remove-empty-albums",
        "remove-duplicates-albums",
        "merge-duplicates-albums",
    },
    "nextcloud_photos": {
        "upload-albums",
        "download-albums",
        "upload-all",
        "download-all",
        "rename-albums",
        "remove-albums",
        "remove-all-albums",
        "remove-all-assets",
        "remove-empty-albums",
        "remove-duplicates-albums",
        "merge-duplicates-albums",
    },
}

STANDALONE_DESTS = {
    "fix-symlinks-broken",
    "rename-folders-content-based",
    "find-duplicates",
    "process-duplicates",
}

GENERAL_CORE_DESTS = {
    "filter-from-date",
    "filter-to-date",
    "filter-by-type",
    "filter-by-country",
    "filter-by-city",
    "filter-by-person",
    "albums-folders",
    "remove-albums-assets",
}

GENERAL_OPTIONAL_DESTS = {
    "configuration-file",
    "no-request-user-confirmation",
    "no-log-file",
    "log-level",
    "log-format",
    "date-separator",
    "range-separator",
    "foldername-albums",
    "foldername-no-albums",
    "foldername-logs",
    "foldername-duplicates-output",
    "foldername-extracted-dates",
    "exec-gpth-tool",
    "exec-exif-tool",
}

FEATURE_SCOPED_DESTS = {
    "input-folder",
    "output-folder",
    "account-id",
}

MODULE_DEPENDENCIES_REQUIRED = {
    "google_photos": {
        "download-albums": {"output-folder"},
        "rename-albums": {"replacement-pattern"},
    },
    "synology_photos": {
        "download-albums": {"output-folder"},
        "rename-albums": {"replacement-pattern"},
    },
    "immich_photos": {
        "download-albums": {"output-folder"},
        "rename-albums": {"replacement-pattern"},
    },
    "nextcloud_photos": {
        "download-albums": {"output-folder"},
        "rename-albums": {"replacement-pattern"},
    },
}

TAB_TO_CATEGORY = {
    "google_takeout": "google_takeout",
    "google_photos": "google_photos",
    "synology_photos": "synology_photos",
    "immich_photos": "immich_photos",
    "nextcloud_photos": "nextcloud_photos",
    "standalone_features": "standalone_features",
    "automatic_migration": "automatic_migration",
}

class RunRequest(BaseModel):
    tab: str
    values: Dict[str, Any] = Field(default_factory=dict)
    selected_action_dest: str | None = None


class ConfigUpdateRequest(BaseModel):
    content: str = ""
    admin_username: str = ""
    admin_password: str = ""


class StateUpdateRequest(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)
    ui_state: Dict[str, Any] = Field(default_factory=dict)


class FolderCreateRequest(BaseModel):
    path: str = "/app/data"
    name: str = ""


class FolderDeleteRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)
    recursive: bool = True


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = ""
    new_password: str = ""


class AdminUserCreateRequest(BaseModel):
    username: str = ""
    password: str = ""
    role: str = "user"
    is_active: bool = True
    must_change_password: bool = False
    data_subpath: str = ""
    volume1_subpath: str = ""


class AdminUserUpdateRequest(BaseModel):
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None
    data_subpath: str | None = None
    volume1_subpath: str | None = None
    must_change_password: bool | None = None


class ConfigFormSaveRequest(BaseModel):
    values: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    admin_username: str = ""
    admin_password: str = ""


class ConfigAdminOverrideRequest(BaseModel):
    action: str = ""
    admin_username: str = ""
    admin_password: str = ""


class AdminDbInsertRequest(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)


class AdminDbUpdateRequest(BaseModel):
    rowid: int
    values: Dict[str, Any] = Field(default_factory=dict)


class AdminDbDeleteRequest(BaseModel):
    rowid: int


class BackupConfigRequest(BaseModel):
    enabled: bool = False
    schedule_mode: str = WEB_BACKUP_DEFAULT_MODE
    backup_dir: str = str(WEB_BACKUP_DEFAULT_DIR)
    keep_last: int = WEB_BACKUP_DEFAULT_KEEP_LAST


class JobData:
    def __init__(
        self,
        command: List[str],
        process: subprocess.Popen[str],
        tab: str | None = None,
        owner_user_id: int | None = None,
    ) -> None:
        self.command = command
        self.command_string = subprocess.list2cmdline(command)
        self.tab = str(tab or "").strip() or None
        self.owner_user_id = owner_user_id
        self.process = process
        self.stop_requested = False
        self.awaiting_confirmation = False
        self.status = "running"
        self.output: Deque["OutputLine"] = deque()  # last completed logical lines in memory
        self.output_chars = 0
        self.dropped_output_lines = 0
        self.partial_line = ""             # current in-progress line (no trailing \n yet)
        self.pending_cr = False            # track split CRLF across chunk boundaries
        self.progress_lines: Dict[str, "OutputLine"] = {}
        self.total_output_chars = 0        # full execution chars
        self.output_file = _create_job_output_file()
        self.output_fp: TextIO | None = open(self.output_file, "a", encoding="utf-8", errors="replace")
        self.return_code: int | None = None
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: str | None = None


@dataclass
class OutputLine:
    text: str
    progress_key: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_connect() -> sqlite3.Connection:
    WEB_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(WEB_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _extract_client_ip(request: Request) -> str:
    forwarded_for = str(request.headers.get("x-forwarded-for") or "").strip()
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    real_ip = str(request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


def _record_access_log(user_id: int, username: str, ip_address: str) -> None:
    _ensure_access_logs_table()
    conn = _db_connect()
    try:
        conn.execute(
            """
            INSERT INTO access_logs (user_id, username, ip_address, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (int(user_id), str(username or ""), str(ip_address or "unknown"), _utc_now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def _ensure_access_logs_table() -> None:
    conn = _db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_username ON access_logs(username)")
        conn.commit()
    finally:
        conn.close()


def _pbkdf2_hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 240_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _pbkdf2_verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = str(hashed_password or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(current, expected)
    except Exception:
        return False


def _session_token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _normalize_subpath(value: str | None, username: str) -> str:
    raw = str(value or "").strip().replace("\\", "/").strip("/")
    if not raw:
        raw = str(username or "").strip().lower()
    if raw in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid subpath.")
    if ".." in raw.split("/"):
        raise HTTPException(status_code=400, detail="Subpath cannot contain '..'.")
    if not re.fullmatch(r"[A-Za-z0-9._/\-]+", raw):
        raise HTTPException(status_code=400, detail="Subpath contains invalid characters.")
    return raw


def _load_default_config_template() -> str:
    candidates = [WEB_CONFIG_TEMPLATE_PATH, Path("/app/default_config.ini"), PROJECT_ROOT / "Config.ini"]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return ""


def _is_sensitive_config_key(key: str) -> bool:
    return bool(re.search(r"(PASSWORD|SECRET|TOKEN|API_KEY|APIKEY|PASSWD)", str(key or "").upper()))


def _looks_like_template_placeholder(key: str, value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    if re.fullmatch(r"\*+", raw):
        return True
    upper = raw.upper()
    if upper in {
        "YOUR_ADMIN_API_KEY",
        "YOUR_API_KEY",
        "API_KEY_USER_1",
        "API_KEY_USER_2",
        "API_KEY_USER_3",
        "USERNAME_1",
        "USERNAME_2",
        "USERNAME_3",
        "PASSWORD_1",
        "PASSWORD_2",
        "PASSWORD_3",
        "APP_PASSWORD_1",
        "APP_PASSWORD_2",
        "APP_PASSWORD_3",
    }:
        return True
    key_upper = str(key or "").upper()
    if "API_KEY" in key_upper and "API_KEY" in upper:
        return True
    if "USERNAME" in key_upper and re.fullmatch(r"USERNAME(?:[_-]?\d+)?", upper):
        return True
    if "PASSWORD" in key_upper and re.fullmatch(r"(?:APP_)?PASSWORD(?:[_-]?\d+)?", upper):
        return True
    return False


def _sanitize_config_form_value(section_name: str, key: str, value: str, default_value: str, sensitive: bool) -> str:
    raw = str(value or "")
    stripped = raw.strip()
    if not stripped:
        return ""
    if sensitive and re.fullmatch(r"\*+", stripped):
        return ""
    if stripped == str(default_value or "").strip() and _looks_like_template_placeholder(key, stripped):
        return ""
    return raw


def _immich_field_sort_key(field: Dict[str, Any], index: int) -> tuple[int, int, int]:
    key = str(field.get("key") or "").strip()
    normalized = key.upper()
    if normalized == "IMMICH_URL":
        return 0, 0, index
    if normalized == "IMMICH_API_KEY_ADMIN":
        return 1, 0, index
    match = re.fullmatch(r"IMMICH_(USERNAME|PASSWORD|API_KEY_USER)_(\d+)", normalized)
    if not match:
        return 9, 0, index
    field_kind = str(match.group(1))
    account_id = int(match.group(2))
    kind_order = {"USERNAME": 0, "PASSWORD": 1, "API_KEY_USER": 2}
    return 2, account_id * 10 + kind_order.get(field_kind, 9), index


def _sort_section_fields(section_name: str, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = list(fields or [])
    if section_name == "Immich Photos":
        indexed_fields = list(enumerate(ordered))
        indexed_fields.sort(key=lambda item: _immich_field_sort_key(item[1], item[0]))
        return [field_item for _, field_item in indexed_fields]
    return ordered


def _sort_form_schema_sections(form_schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    schema = list(form_schema or [])
    order_index = {name: idx for idx, name in enumerate(CONFIG_SECTIONS_ORDER)}
    schema.sort(key=lambda item: order_index.get(str(item.get("name") or ""), len(order_index) + 1000))
    return schema


def _encrypt_value(value: str) -> str:
    plain = str(value or "").encode("utf-8")
    nonce = secrets.token_bytes(16)
    key = hashlib.sha256(WEB_SECRET.encode("utf-8")).digest()
    stream = bytearray()
    counter = 0
    while len(stream) < len(plain):
        block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    cipher = bytes([a ^ b for a, b in zip(plain, stream[: len(plain)])])
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(nonce + cipher + tag).decode("ascii")


def _decrypt_value(token: str) -> str:
    try:
        blob = base64.urlsafe_b64decode(str(token or "").encode("ascii"))
        if len(blob) < 32:
            return ""
        nonce = blob[:16]
        tag = blob[-16:]
        cipher = blob[16:-16]
        key = hashlib.sha256(WEB_SECRET.encode("utf-8")).digest()
        expected_tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            return ""
        stream = bytearray()
        counter = 0
        while len(stream) < len(cipher):
            block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            stream.extend(block)
            counter += 1
        plain = bytes([a ^ b for a, b in zip(cipher, stream[: len(cipher)])])
        return plain.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _parse_template_to_form_schema(template_content: str) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    section_map: Dict[str, Dict[str, Any]] = {}
    current_section: Dict[str, Any] | None = None
    pending_comments: List[str] = []
    pending_section_comment: List[str] = []

    for raw_line in str(template_content or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            pending_comments = []
            pending_section_comment = []
            continue
        if stripped.startswith("#"):
            comment = stripped.lstrip("#").strip()
            if comment:
                pending_comments.append(comment)
                pending_section_comment.append(comment)
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section_name = stripped[1:-1].strip()
            description = " ".join(pending_section_comment).strip()
            pending_section_comment = []
            pending_comments = []
            if section_name not in section_map:
                entry = {"name": section_name, "description": description, "fields": []}
                section_map[section_name] = entry
                sections.append(entry)
            current_section = section_map[section_name]
            if description and not current_section.get("description"):
                current_section["description"] = description
            continue
        if "=" in line and current_section is not None:
            key_raw, value_raw = line.split("=", 1)
            key = key_raw.strip()
            if not key:
                pending_comments = []
                continue
            value_part = value_raw.strip()
            inline_help = ""
            if "#" in value_part:
                value_value, comment = value_part.split("#", 1)
                value = value_value.rstrip()
                inline_help = comment.strip()
            else:
                value = value_part
            help_text = inline_help or " ".join(pending_comments).strip()
            current_section["fields"].append(
                {
                    "key": key,
                    "default": value,
                    "help": help_text,
                    "sensitive": _is_sensitive_config_key(key),
                }
            )
            pending_comments = []

    if not sections:
        return []
    for section in sections:
        section_name = str(section.get("name") or "")
        section["fields"] = _sort_section_fields(section_name, section.get("fields", []))
    return _sort_form_schema_sections(sections)


def _extend_form_schema_with_web_interface_theme(form_schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    schema = list(form_schema or [])
    for section in schema:
        if str(section.get("name") or "") == WEB_INTERFACE_SECTION_NAME:
            return _sort_form_schema_sections(schema)
    schema.append(
        {
            "name": WEB_INTERFACE_SECTION_NAME,
            "description": "Web interface preferences stored per user.",
            "fields": [
                {
                    "key": WEB_INTERFACE_THEME_KEY,
                    "default": WEB_INTERFACE_THEME_DEFAULT,
                    "help": "Theme used by the PhotoMigrator web interface.",
                    "sensitive": False,
                }
            ],
        }
    )
    return _sort_form_schema_sections(schema)


def _parse_ini_text_to_values(config_text: str, *, strict: bool = False) -> Dict[str, Dict[str, str]]:
    text = str(config_text or "").lstrip("\ufeff")
    values: Dict[str, Dict[str, str]] = {}
    current_section = ""
    parsed_pairs = 0

    def _strip_inline_comment(raw: str) -> str:
        in_single = False
        in_double = False
        for idx, ch in enumerate(raw):
            if ch == "'" and not in_double:
                in_single = not in_single
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                continue
            if (ch == "#" or ch == ";") and not in_single and not in_double:
                if idx == 0 or raw[idx - 1].isspace():
                    return raw[:idx].rstrip()
        return raw.rstrip()

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = str(raw_line or "").strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            if not section_name:
                if strict:
                    raise HTTPException(status_code=400, detail=f"Invalid Config.ini format: empty section at line {line_no}.")
                continue
            current_section = section_name
            values.setdefault(current_section, {})
            continue
        if not current_section:
            if strict:
                raise HTTPException(status_code=400, detail=f"Invalid Config.ini format: key/value outside section at line {line_no}.")
            continue
        if "=" in line:
            key_raw, value_raw = line.split("=", 1)
        elif ":" in line:
            key_raw, value_raw = line.split(":", 1)
        else:
            if strict:
                raise HTTPException(status_code=400, detail=f"Invalid Config.ini format: expected key=value at line {line_no}.")
            continue
        key = key_raw.strip()
        if not key:
            if strict:
                raise HTTPException(status_code=400, detail=f"Invalid Config.ini format: empty key at line {line_no}.")
            continue
        value = _strip_inline_comment(value_raw.strip())
        values.setdefault(current_section, {})[key] = value
        parsed_pairs += 1

    if strict:
        if not values:
            raise HTTPException(status_code=400, detail="Invalid Config.ini format: no sections found.")
        if parsed_pairs <= 0:
            raise HTTPException(status_code=400, detail="Invalid Config.ini format: no key/value pairs found.")
    return values


def _serialize_values_to_ini(values: Dict[str, Dict[str, str]], form_schema: List[Dict[str, Any]]) -> str:
    lines: List[str] = ["# Config.ini File", ""]
    for section in form_schema:
        section_name = str(section.get("name") or "").strip()
        if not section_name:
            continue
        lines.append(f"[{section_name}]")
        field_values = values.get(section_name, {})
        for field in section.get("fields", []):
            key = str(field.get("key") or "").strip()
            if not key:
                continue
            value = str(field_values.get(key, field.get("default", "")) or "")
            lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _serialize_values_to_ini_with_comments(values: Dict[str, Dict[str, str]], template_content: str) -> str:
    comment_column = 72

    def _aligned_line(left: str, comment_text: str) -> str:
        base = left.rstrip()
        comment = str(comment_text or "").strip()
        if not comment:
            return base
        if not comment.startswith("#"):
            comment = f"# {comment}"
        pad = max(1, comment_column - len(base))
        return f"{base}{' ' * pad}{comment}"

    output_lines: List[str] = ["# Config.ini File"]
    timezone_value = str(values.get("TimeZone", {}).get("timezone", TIMEZONE_DEFAULT) or TIMEZONE_DEFAULT)
    output_lines.append("[TimeZone]")
    output_lines.append(f"timezone = {timezone_value}")
    output_lines.append("")
    output_lines.append("# Web Interface user preferences")
    output_lines.append(f"[{WEB_INTERFACE_SECTION_NAME}]")
    theme_value = str(
        values.get(WEB_INTERFACE_SECTION_NAME, {}).get(WEB_INTERFACE_THEME_KEY, WEB_INTERFACE_THEME_DEFAULT)
        or WEB_INTERFACE_THEME_DEFAULT
    )
    output_lines.append(_aligned_line(
        f"{WEB_INTERFACE_THEME_KEY} = {theme_value}",
        f"# Theme for Web UI ({', '.join(WEB_INTERFACE_THEME_CHOICES)})",
    ))
    output_lines.append("")

    current_section = ""
    skipped_sections = {"TimeZone", WEB_INTERFACE_SECTION_NAME}
    for original_line in str(template_content or "").splitlines():
        line = str(original_line or "")
        stripped = line.strip()
        if stripped == "# Config.ini File":
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            if current_section in skipped_sections:
                continue
            output_lines.append(line)
            continue
        if current_section in skipped_sections:
            continue
        if "=" in line and current_section:
            key_part, rhs = line.split("=", 1)
            key = key_part.strip()
            if key and current_section in values and key in values[current_section]:
                value = str(values[current_section][key] or "")
                comment = ""
                if "#" in rhs:
                    comment = "#" + rhs.split("#", 1)[1]
                new_line = _aligned_line(f"{key_part.rstrip()} = {value}", comment)
                output_lines.append(new_line)
                continue
        if stripped == "" and output_lines and output_lines[-1].strip() == "":
            continue
        output_lines.append(line)
    return "\n".join(output_lines).rstrip() + "\n"


def _encrypt_config_values(values: Dict[str, Dict[str, str]], form_schema: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    encrypted: Dict[str, Dict[str, Dict[str, Any]]] = {}
    schema_lookup: Dict[str, Dict[str, bool]] = {}
    for section in form_schema:
        section_name = str(section.get("name") or "")
        schema_lookup[section_name] = {}
        for field in section.get("fields", []):
            schema_lookup[section_name][str(field.get("key") or "")] = bool(field.get("sensitive"))
    for section_name, section_values in (values or {}).items():
        target: Dict[str, Dict[str, Any]] = {}
        sensitive_lookup = schema_lookup.get(section_name, {})
        for key, raw_value in (section_values or {}).items():
            value = str(raw_value or "")
            is_sensitive = bool(sensitive_lookup.get(key, _is_sensitive_config_key(key)))
            if is_sensitive and value.strip():
                target[key] = {"value": _encrypt_value(value), "encrypted": True}
            else:
                target[key] = {"value": value, "encrypted": False}
        encrypted[section_name] = target
    return encrypted


def _decrypt_config_values(encrypted_values: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, str]]:
    plain: Dict[str, Dict[str, str]] = {}
    for section_name, section_values in (encrypted_values or {}).items():
        out_section: Dict[str, str] = {}
        for key, item in (section_values or {}).items():
            if isinstance(item, dict) and bool(item.get("encrypted")):
                out_section[key] = _decrypt_value(str(item.get("value") or ""))
            elif isinstance(item, dict):
                out_section[key] = str(item.get("value") or "")
            else:
                out_section[key] = str(item or "")
        plain[section_name] = out_section
    return plain


def _init_web_db(template_schema: List[Dict[str, Any]]) -> None:
    conn = _db_connect()
    now = _utc_now_iso()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                data_subpath TEXT NOT NULL DEFAULT '',
                volume1_subpath TEXT NOT NULL DEFAULT '',
                state_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_configs (
                user_id INTEGER PRIMARY KEY,
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_username ON access_logs(username)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_schedules (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled INTEGER NOT NULL DEFAULT 0,
                schedule_mode TEXT NOT NULL DEFAULT 'daily_2am',
                interval_minutes INTEGER NOT NULL DEFAULT 1440,
                backup_dir TEXT NOT NULL DEFAULT '/app/config/backups',
                keep_last INTEGER NOT NULL DEFAULT 14,
                next_run_at TEXT,
                last_run_at TEXT,
                last_status TEXT NOT NULL DEFAULT 'idle',
                last_error TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        cur.execute("UPDATE users SET role = LOWER(TRIM(role)) WHERE role IS NOT NULL")
        conn.commit()
        backup_cols = {str(row["name"]) for row in cur.execute("PRAGMA table_info(backup_schedules)").fetchall()}
        if "schedule_mode" not in backup_cols:
            cur.execute("ALTER TABLE backup_schedules ADD COLUMN schedule_mode TEXT NOT NULL DEFAULT 'daily_2am'")
            conn.commit()

        # Safety net: never allow the system to remain without at least one active admin.
        admin_count = int(
            cur.execute(
                "SELECT COUNT(*) AS count FROM users WHERE LOWER(TRIM(role)) = 'admin' AND is_active = 1"
            ).fetchone()["count"]
        )
        if admin_count == 0:
            bootstrap_username = str(WEB_BOOTSTRAP_ADMIN_USER or "admin").strip()
            candidate = cur.execute(
                "SELECT id FROM users WHERE LOWER(TRIM(username)) = LOWER(TRIM(?)) LIMIT 1",
                (bootstrap_username,),
            ).fetchone()
            if candidate is None:
                candidate = cur.execute(
                    "SELECT id FROM users WHERE is_active = 1 ORDER BY id ASC LIMIT 1"
                ).fetchone()
            if candidate is None:
                candidate = cur.execute(
                    "SELECT id FROM users ORDER BY id ASC LIMIT 1"
                ).fetchone()
            if candidate is not None:
                cur.execute(
                    "UPDATE users SET role = 'admin', is_active = 1, updated_at = ? WHERE id = ?",
                    (now, int(candidate["id"])),
                )
                conn.commit()

        user_count = int(cur.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"])
        if user_count == 0:
            admin_username = str(WEB_BOOTSTRAP_ADMIN_USER or "admin").strip() or "admin"
            admin_data_subpath = _normalize_subpath(admin_username, admin_username)
            cur.execute(
                """
                INSERT INTO users (
                    username, password_hash, role, is_active, must_change_password,
                    data_subpath, volume1_subpath, state_json, created_at, updated_at
                ) VALUES (?, ?, 'admin', 1, 1, ?, ?, '{}', ?, ?)
                """,
                (
                    admin_username,
                    _pbkdf2_hash_password(str(WEB_BOOTSTRAP_ADMIN_PASS or "admin123")),
                    admin_data_subpath,
                    admin_data_subpath,
                    now,
                    now,
                ),
            )
            conn.commit()

        template_defaults = {}
        for section in template_schema:
            section_name = str(section.get("name") or "")
            template_defaults[section_name] = {}
            for field in section.get("fields", []):
                key = str(field.get("key") or "")
                value = str(field.get("default") or "")
                if section_name == "TimeZone" and key == "timezone":
                    value = TIMEZONE_DEFAULT
                template_defaults[section_name][key] = value
        encrypted_defaults = _encrypt_config_values(template_defaults, template_schema)
        all_users = cur.execute("SELECT id FROM users").fetchall()
        for user_row in all_users:
            user_id = int(user_row["id"])
            existing = cur.execute("SELECT user_id FROM user_configs WHERE user_id = ?", (user_id,)).fetchone()
            if existing:
                continue
            cur.execute(
                "INSERT INTO user_configs (user_id, config_json, updated_at) VALUES (?, ?, ?)",
                (user_id, json.dumps(encrypted_defaults, ensure_ascii=False), now),
            )
        config_rows = cur.execute("SELECT user_id, config_json FROM user_configs").fetchall()
        for row in config_rows:
            user_id = int(row["user_id"])
            raw_json = str(row["config_json"] or "{}")
            try:
                encrypted_payload = json.loads(raw_json)
            except Exception:
                encrypted_payload = {}
            plain_values = _decrypt_config_values(encrypted_payload if isinstance(encrypted_payload, dict) else {})
            reordered_values = _merge_values_with_schema(plain_values, template_schema)
            reordered_encrypted = _encrypt_config_values(reordered_values, template_schema)
            reordered_json = json.dumps(reordered_encrypted, ensure_ascii=False)
            if reordered_json == raw_json:
                continue
            cur.execute(
                "UPDATE user_configs SET config_json = ?, updated_at = ? WHERE user_id = ?",
                (reordered_json, now, user_id),
            )
        for user_row in all_users:
            user_id = int(user_row["id"])
            existing_state = cur.execute("SELECT user_id FROM user_states WHERE user_id = ?", (user_id,)).fetchone()
            if existing_state:
                continue
            legacy_state_row = cur.execute("SELECT state_json FROM users WHERE id = ?", (user_id,)).fetchone()
            legacy_state = "{}"
            if legacy_state_row:
                legacy_state = str(legacy_state_row["state_json"] or "{}")
            cur.execute(
                "INSERT INTO user_states (user_id, state_json, updated_at) VALUES (?, ?, ?)",
                (user_id, legacy_state, now),
            )
        schedule_row = cur.execute("SELECT id FROM backup_schedules WHERE id = 1").fetchone()
        if not schedule_row:
            cur.execute(
                """
                INSERT INTO backup_schedules (id, enabled, schedule_mode, interval_minutes, backup_dir, keep_last, next_run_at, last_run_at, last_status, last_error, updated_at)
                VALUES (1, 0, ?, ?, ?, ?, NULL, NULL, 'idle', '', ?)
                """,
                (
                    _normalize_backup_mode(WEB_BACKUP_DEFAULT_MODE),
                    WEB_BACKUP_DEFAULT_INTERVAL_MINUTES,
                    str(WEB_BACKUP_DEFAULT_DIR),
                    WEB_BACKUP_DEFAULT_KEEP_LAST,
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    _ensure_access_logs_table()


def _fetch_user_by_id(user_id: int) -> Dict[str, Any] | None:
    conn = _db_connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _fetch_user_by_username(username: str) -> Dict[str, Any] | None:
    conn = _db_connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (str(username or "").strip(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _create_session_for_user(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = _session_token_hash(token)
    created_at = _utc_now_iso()
    expires_at = datetime.fromtimestamp(time.time() + WEB_SESSION_TTL_SECONDS, timezone.utc).isoformat()
    conn = _db_connect()
    try:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token_hash, int(user_id), expires_at, created_at),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def _delete_session(token: str | None) -> None:
    token = str(token or "").strip()
    if not token:
        return
    token_hash = _session_token_hash(token)
    conn = _db_connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
    finally:
        conn.close()


def _user_from_session_token(token: str | None) -> Dict[str, Any] | None:
    token = str(token or "").strip()
    if not token:
        return None
    token_hash = _session_token_hash(token)
    now = _utc_now_iso()
    conn = _db_connect()
    try:
        row = conn.execute(
            """
            SELECT u.*
            FROM sessions s
            INNER JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ? AND u.is_active = 1
            """,
            (token_hash, now),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _require_user(session_token: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)) -> Dict[str, Any]:
    user = _user_from_session_token(session_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def _require_admin(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    if str(current_user.get("role") or "").strip().lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")
    return current_user


def _ensure_export_allowed(current_user: Dict[str, Any]) -> None:
    if str(current_user.get("role") or "").strip().lower() == "demo":
        raise HTTPException(status_code=403, detail="Demo accounts cannot export configuration.")


DEMO_CONFIG_ALLOWED_FIELDS = {
    ("TimeZone", "timezone"),
    (WEB_INTERFACE_SECTION_NAME, WEB_INTERFACE_THEME_KEY),
}


def _is_demo_user(current_user: Dict[str, Any]) -> bool:
    return str(current_user.get("role") or "").strip().lower() == "demo"


def _validate_admin_override_credentials(admin_username: str, admin_password: str) -> Dict[str, Any]:
    username = str(admin_username or "").strip()
    password = str(admin_password or "")
    if not username or not password:
        raise HTTPException(status_code=403, detail="Admin credentials are required.")
    user = _fetch_user_by_username(username)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid admin credentials.")
    if str(user.get("role") or "").strip().lower() != "admin" or not bool(user.get("is_active")):
        raise HTTPException(status_code=403, detail="Invalid admin credentials.")
    if not _pbkdf2_verify_password(password, str(user.get("password_hash") or "")):
        raise HTTPException(status_code=403, detail="Invalid admin credentials.")
    return user


def _demo_config_has_disallowed_changes(
    current_user: Dict[str, Any],
    incoming_values: Dict[str, Dict[str, str]],
    form_schema: List[Dict[str, Any]],
) -> bool:
    current_values = _merge_values_with_schema(_get_user_config_values(current_user), form_schema)
    new_values = _merge_values_with_schema(incoming_values or {}, form_schema)
    for section in form_schema:
        section_name = str(section.get("name") or "")
        if not section_name:
            continue
        for field in section.get("fields", []):
            key = str(field.get("key") or "")
            if not key:
                continue
            before = str(current_values.get(section_name, {}).get(key, "") or "").strip()
            after = str(new_values.get(section_name, {}).get(key, "") or "").strip()
            if before == after:
                continue
            if (section_name, key) in DEMO_CONFIG_ALLOWED_FIELDS:
                continue
            return True
    return False


def _require_demo_admin_override(
    current_user: Dict[str, Any],
    *,
    action: str,
    admin_username: str = "",
    admin_password: str = "",
) -> None:
    if not _is_demo_user(current_user):
        return
    _validate_admin_override_credentials(admin_username, admin_password)


def _enforce_demo_save_policy(
    current_user: Dict[str, Any],
    merged_values: Dict[str, Dict[str, str]],
    *,
    admin_username: str = "",
    admin_password: str = "",
) -> None:
    if not _is_demo_user(current_user):
        return
    if not _demo_config_has_disallowed_changes(current_user, merged_values, CONFIG_FORM_SCHEMA):
        return
    _validate_admin_override_credentials(admin_username, admin_password)


def _get_user_allowed_roots(current_user: Dict[str, Any]) -> List[Path]:
    username = str(current_user.get("username") or "").strip().lower()
    data_subpath = _normalize_subpath(str(current_user.get("data_subpath") or ""), username)
    volume1_subpath = _normalize_subpath(str(current_user.get("volume1_subpath") or ""), username)
    roots = [
        (WEB_USER_ROOT_DATA / data_subpath).resolve(),
        (WEB_USER_ROOT_VOLUME1 / volume1_subpath).resolve(),
    ]
    return roots


def _ensure_user_roots_exist(current_user: Dict[str, Any]) -> List[Path]:
    roots = _get_user_allowed_roots(current_user)
    for root in roots:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
    return roots


def _resolve_user_path(raw_path: str | None, current_user: Dict[str, Any]) -> Path:
    roots = _ensure_user_roots_exist(current_user)
    fallback = roots[0]
    incoming = str(raw_path or "").strip()
    if not incoming:
        incoming_path = fallback
    else:
        incoming_path = Path(incoming).expanduser()
        if not incoming_path.is_absolute():
            incoming_path = (fallback / incoming_path).resolve()
        else:
            incoming_path = incoming_path.resolve()
    for root in roots:
        try:
            incoming_path.relative_to(root)
            return incoming_path
        except ValueError:
            continue
    # Compatibility remap: legacy/global paths under shared roots are mapped
    # into the active user's own roots to avoid cross-user access.
    username = str(current_user.get("username") or "").strip().lower()
    data_subpath = _normalize_subpath(str(current_user.get("data_subpath") or ""), username)
    volume1_subpath = _normalize_subpath(str(current_user.get("volume1_subpath") or ""), username)
    remap_pairs = [
        (WEB_USER_ROOT_DATA, (WEB_USER_ROOT_DATA / data_subpath).resolve()),
        (WEB_USER_ROOT_VOLUME1, (WEB_USER_ROOT_VOLUME1 / volume1_subpath).resolve()),
    ]
    for base_root, user_root in remap_pairs:
        try:
            rel = incoming_path.relative_to(base_root)
        except ValueError:
            continue
        mapped = (user_root / rel).resolve()
        try:
            mapped.relative_to(user_root)
            return mapped
        except ValueError:
            continue
    allowed = ", ".join(str(root) for root in roots)
    raise HTTPException(status_code=403, detail=f"Path outside allowed user roots. Allowed roots: {allowed}")


def _get_user_config_values(current_user: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    user_id = int(current_user["id"])
    conn = _db_connect()
    try:
        row = conn.execute("SELECT config_json FROM user_configs WHERE user_id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    try:
        encrypted = json.loads(str(row["config_json"] or "{}"))
    except Exception:
        encrypted = {}
    return _decrypt_config_values(encrypted)


def _save_user_config_values(current_user: Dict[str, Any], values: Dict[str, Dict[str, str]], form_schema: List[Dict[str, Any]]) -> None:
    encrypted = _encrypt_config_values(values, form_schema)
    user_id = int(current_user["id"])
    now = _utc_now_iso()
    conn = _db_connect()
    try:
        conn.execute(
            """
            INSERT INTO user_configs (user_id, config_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(encrypted, ensure_ascii=False), now),
        )
        conn.commit()
    finally:
        conn.close()


def _merge_values_with_schema(values: Dict[str, Dict[str, str]], form_schema: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    def _norm_token(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").strip().lower())

    input_values = values or {}
    section_lookup: Dict[str, Dict[str, str]] = {
        str(name).strip().lower(): (section_values or {})
        for name, section_values in input_values.items()
        if str(name or "").strip()
    }
    section_lookup_norm: Dict[str, Dict[str, str]] = {
        _norm_token(str(name)): (section_values or {})
        for name, section_values in input_values.items()
        if str(name or "").strip()
    }
    merged: Dict[str, Dict[str, str]] = {}
    for section in form_schema:
        section_name = str(section.get("name") or "")
        merged[section_name] = {}
        source_values = input_values.get(section_name)
        if source_values is None:
            source_values = section_lookup.get(section_name.strip().lower(), {})
        if not source_values:
            source_values = section_lookup_norm.get(_norm_token(section_name), {})
        normalized_source = {str(k): str(v or "") for k, v in (source_values or {}).items()}
        normalized_source_lc = {str(k).strip().lower(): str(v or "") for k, v in (source_values or {}).items()}
        normalized_source_norm = {_norm_token(str(k)): str(v or "") for k, v in (source_values or {}).items()}
        for field in section.get("fields", []):
            key = str(field.get("key") or "")
            base_value = normalized_source.get(key)
            if base_value is None:
                base_value = normalized_source_lc.get(key.strip().lower(), str(field.get("default", "")) or "")
            if base_value == str(field.get("default", "")) or base_value is None:
                base_value = normalized_source_norm.get(_norm_token(key), base_value)
            if section_name == "TimeZone" and key == "timezone" and not base_value.strip():
                base_value = TIMEZONE_DEFAULT
            if section_name == WEB_INTERFACE_SECTION_NAME and key == WEB_INTERFACE_THEME_KEY:
                if base_value.strip() not in WEB_INTERFACE_THEME_CHOICES:
                    base_value = WEB_INTERFACE_THEME_DEFAULT
            merged[section_name][key] = base_value
    return merged


def _materialize_user_config_to_file(current_user: Dict[str, Any], form_schema: List[Dict[str, Any]]) -> Path:
    values = _merge_values_with_schema(_get_user_config_values(current_user), form_schema)
    content = _serialize_values_to_ini(values, form_schema)
    WEB_CONFIG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_username = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(current_user.get("username") or "user"))
    file_path = WEB_CONFIG_CACHE_DIR / f"Config_{safe_username}_{int(current_user['id'])}.ini"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _user_config_db_path(current_user: Dict[str, Any]) -> str:
    username = str(current_user.get("username") or "").strip() or "user"
    return f"db://users/{username}/Config.ini"


def _build_config_form_response(current_user: Dict[str, Any], merged: Dict[str, Dict[str, str]] | None = None) -> Dict[str, Any]:
    effective = merged if merged is not None else _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
    sections: List[Dict[str, Any]] = []
    section_order = {name: idx for idx, name in enumerate(CONFIG_SECTIONS_ORDER + [WEB_INTERFACE_SECTION_NAME])}
    for section in CONFIG_FORM_SCHEMA:
        section_name = str(section.get("name") or "")
        if not section_name:
            continue
        if section_name not in CONFIG_SECTIONS_ORDER and section_name != WEB_INTERFACE_SECTION_NAME:
            continue
        fields: List[Dict[str, Any]] = []
        source_fields = list(section.get("fields", []))
        if section_name == "Immich Photos":
            indexed_fields = list(enumerate(source_fields))
            indexed_fields.sort(key=lambda item: _immich_field_sort_key(item[1], item[0]))
            source_fields = [field_item for _, field_item in indexed_fields]
        for field in source_fields:
            key = str(field.get("key") or "")
            if not key:
                continue
            raw_value = str(effective.get(section_name, {}).get(key, ""))
            default_value = str(field.get("default") or "")
            sensitive = bool(field.get("sensitive"))
            display_value = _sanitize_config_form_value(section_name, key, raw_value, default_value, sensitive)
            fields.append(
                {
                    "key": key,
                    "value": display_value,
                    "help": (
                        "Select the time zone used by PhotoMigrator to display timestamps and process date/time-based operations."
                        if section_name == "TimeZone" and key == "timezone"
                        else str(field.get("help") or "")
                    ),
                    "sensitive": sensitive,
                    "choices": (
                        TIMEZONE_CHOICES
                        if section_name == "TimeZone" and key == "timezone"
                        else WEB_INTERFACE_THEME_CHOICES
                        if section_name == WEB_INTERFACE_SECTION_NAME and key == WEB_INTERFACE_THEME_KEY
                        else []
                    ),
                }
            )
        sections.append(
            {
                "name": section_name,
                "display_name": "Theme" if section_name == WEB_INTERFACE_SECTION_NAME else section_name,
                "description": (
                    "Configuration for google takeout. Configure execution options for this module from Feature Selector > Google Takeout tab."
                    if section_name == "Google Takeout"
                    else
                    "Time zone used by PhotoMigrator to interpret and display date/time values in logs and date-based operations."
                    if section_name == "TimeZone"
                    else "Select the visual theme used by your web interface."
                    if section_name == WEB_INTERFACE_SECTION_NAME
                    else str(section.get("description") or "")
                ),
                "fields": fields,
            }
        )
    sections.sort(key=lambda item: section_order.get(str(item.get("name") or ""), 9999))
    return {"path": _user_config_db_path(current_user), "sections": sections, "updated_at": _utc_now_iso()}


def _read_user_state_payload(current_user: Dict[str, Any]) -> Dict[str, Any]:
    user_id = int(current_user["id"])
    conn = _db_connect()
    try:
        row = conn.execute("SELECT state_json FROM user_states WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            raw = str(row["state_json"] or "{}")
        else:
            # Backward compatibility with legacy users.state_json
            raw = str(current_user.get("state_json") or "{}")
            conn.execute(
                "INSERT INTO user_states (user_id, state_json, updated_at) VALUES (?, ?, ?)",
                (user_id, raw, _utc_now_iso()),
            )
            conn.commit()
    finally:
        conn.close()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    values = data.get("values", {}) if isinstance(data, dict) else {}
    ui_state = data.get("ui_state", {}) if isinstance(data, dict) else {}
    if not isinstance(values, dict):
        values = {}
    if not isinstance(ui_state, dict):
        ui_state = {}
    return {"values": values, "ui_state": ui_state}


def _save_user_state_payload(current_user: Dict[str, Any], values: Dict[str, Any], ui_state: Dict[str, Any]) -> None:
    payload = {"values": values or {}, "ui_state": ui_state or {}, "updated_at": _utc_now_iso()}
    conn = _db_connect()
    try:
        conn.execute(
            """
            INSERT INTO user_states (user_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (int(current_user["id"]), json.dumps(payload, ensure_ascii=False), _utc_now_iso()),
        )
        # Keep legacy column synced for compatibility/debugging
        conn.execute(
            "UPDATE users SET state_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), _utc_now_iso(), int(current_user["id"])),
        )
        conn.commit()
    finally:
        conn.close()


def _list_admin_db_tables() -> List[str]:
    conn = _db_connect()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [str(row["name"]) for row in rows]
    finally:
        conn.close()


def _validate_admin_table_name(table_name: str) -> str:
    name = str(table_name or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise HTTPException(status_code=400, detail="Invalid table name.")
    allowed = set(_list_admin_db_tables())
    if name not in allowed:
        raise HTTPException(status_code=404, detail="Table not found.")
    return name


def _table_columns(table_name: str) -> List[Dict[str, Any]]:
    conn = _db_connect()
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [
            {
                "cid": int(row["cid"]),
                "name": str(row["name"]),
                "type": str(row["type"] or ""),
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": int(row["pk"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def _read_backup_schedule() -> Dict[str, Any]:
    conn = _db_connect()
    try:
        row = conn.execute("SELECT * FROM backup_schedules WHERE id = 1").fetchone()
        if not row:
            now = _utc_now_iso()
            conn.execute(
                """
                INSERT INTO backup_schedules (id, enabled, schedule_mode, interval_minutes, backup_dir, keep_last, next_run_at, last_run_at, last_status, last_error, updated_at)
                VALUES (1, 0, ?, ?, ?, ?, NULL, NULL, 'idle', '', ?)
                """,
                (
                    _normalize_backup_mode(WEB_BACKUP_DEFAULT_MODE),
                    WEB_BACKUP_DEFAULT_INTERVAL_MINUTES,
                    str(WEB_BACKUP_DEFAULT_DIR),
                    WEB_BACKUP_DEFAULT_KEEP_LAST,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM backup_schedules WHERE id = 1").fetchone()
        payload = dict(row)
        payload["enabled"] = bool(payload.get("enabled"))
        payload["schedule_mode"] = _normalize_backup_mode(payload.get("schedule_mode"))
        payload["interval_minutes"] = max(1, int(payload.get("interval_minutes") or WEB_BACKUP_DEFAULT_INTERVAL_MINUTES))
        payload["keep_last"] = max(1, int(payload.get("keep_last") or WEB_BACKUP_DEFAULT_KEEP_LAST))
        payload["backup_dir"] = str(payload.get("backup_dir") or str(WEB_BACKUP_DEFAULT_DIR)).strip() or str(WEB_BACKUP_DEFAULT_DIR)
        return payload
    finally:
        conn.close()


def _save_backup_schedule(config: BackupConfigRequest) -> Dict[str, Any]:
    schedule_mode = _normalize_backup_mode(config.schedule_mode)
    interval = (
        60 if schedule_mode == "hourly"
        else 24 * 60 if schedule_mode == "daily_2am"
        else 7 * 24 * 60
    )
    keep_last = max(1, int(config.keep_last or WEB_BACKUP_DEFAULT_KEEP_LAST))
    backup_dir = str(config.backup_dir or str(WEB_BACKUP_DEFAULT_DIR)).strip() or str(WEB_BACKUP_DEFAULT_DIR)
    now = _utc_now_iso()
    next_run = _compute_next_backup_run(schedule_mode).isoformat() if config.enabled else None
    conn = _db_connect()
    try:
        conn.execute(
            """
            INSERT INTO backup_schedules (id, enabled, schedule_mode, interval_minutes, backup_dir, keep_last, next_run_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enabled = excluded.enabled,
                schedule_mode = excluded.schedule_mode,
                interval_minutes = excluded.interval_minutes,
                backup_dir = excluded.backup_dir,
                keep_last = excluded.keep_last,
                next_run_at = excluded.next_run_at,
                updated_at = excluded.updated_at
            """,
            (
                1 if config.enabled else 0,
                schedule_mode,
                interval,
                backup_dir,
                keep_last,
                next_run,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return _read_backup_schedule()


def _run_backup_now(manual: bool = False) -> Dict[str, Any]:
    with BACKUP_LOCK:
        cfg = _read_backup_schedule()
        backup_dir = Path(str(cfg.get("backup_dir") or str(WEB_BACKUP_DEFAULT_DIR))).expanduser()
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"web_interface_{timestamp}.db"
        status = "success"
        error = ""
        try:
            shutil.copy2(str(WEB_DB_PATH), str(backup_file))
            keep_last = max(1, int(cfg.get("keep_last") or WEB_BACKUP_DEFAULT_KEEP_LAST))
            files = sorted(backup_dir.glob("web_interface_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
            for stale in files[keep_last:]:
                try:
                    stale.unlink()
                except Exception:
                    pass
        except Exception as exc:
            status = "failed"
            error = str(exc)

        now_iso = _utc_now_iso()
        next_run_at = None
        if bool(cfg.get("enabled")):
            next_run_at = _compute_next_backup_run(str(cfg.get("schedule_mode") or WEB_BACKUP_DEFAULT_MODE)).isoformat()
        conn = _db_connect()
        try:
            conn.execute(
                """
                UPDATE backup_schedules
                SET last_run_at = ?, last_status = ?, last_error = ?, next_run_at = ?, updated_at = ?
                WHERE id = 1
                """,
                (now_iso, status, error, next_run_at, now_iso),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "status": status,
            "error": error,
            "backup_file": str(backup_file),
            "manual": bool(manual),
        }


def _backup_scheduler_loop() -> None:
    while not BACKUP_THREAD_STOP.is_set():
        try:
            cfg = _read_backup_schedule()
            if bool(cfg.get("enabled")):
                next_run_raw = str(cfg.get("next_run_at") or "").strip()
                due = False
                if not next_run_raw:
                    due = True
                else:
                    try:
                        due = datetime.now(timezone.utc) >= datetime.fromisoformat(next_run_raw)
                    except Exception:
                        due = True
                if due:
                    _run_backup_now(manual=False)
        except Exception:
            pass
        BACKUP_THREAD_STOP.wait(30)


def _start_backup_scheduler() -> None:
    global BACKUP_THREAD
    if BACKUP_THREAD is not None and BACKUP_THREAD.is_alive():
        return
    BACKUP_THREAD_STOP.clear()
    BACKUP_THREAD = threading.Thread(target=_backup_scheduler_loop, daemon=True)
    BACKUP_THREAD.start()


def _sync_user_theme_to_state(current_user: Dict[str, Any], config_values: Dict[str, Dict[str, str]]) -> None:
    theme = str(
        (config_values or {}).get(WEB_INTERFACE_SECTION_NAME, {}).get(WEB_INTERFACE_THEME_KEY, WEB_INTERFACE_THEME_DEFAULT)
        or WEB_INTERFACE_THEME_DEFAULT
    ).strip().lower()
    if theme not in WEB_INTERFACE_THEME_CHOICES:
        theme = WEB_INTERFACE_THEME_DEFAULT
    fresh_user = _fetch_user_by_id(int(current_user["id"])) or current_user
    payload = _read_user_state_payload(fresh_user)
    ui_state = dict(payload.get("ui_state") or {})
    ui_state["theme"] = theme
    _save_user_state_payload(fresh_user, payload.get("values") or {}, ui_state)

def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


WEB_JOB_LOG_DIR = Path(os.environ.get("PHOTOMIGRATOR_WEB_JOB_LOG_DIR", "/tmp/photomigrator-web-jobs"))
MAX_JOB_OUTPUT_LINES = _env_int("PHOTOMIGRATOR_WEB_MAX_JOB_OUTPUT_LINES", 100_000)
TAIL_CONFIRM_CHARS = 4_000
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
PROGRESS_CUSTOM_FULL_RE = re.compile(r"^(.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+\d+/\d+\s+\d+(?:\.\d+)?%\s*$")
PROGRESS_TQDM_RE = re.compile(r"(\d{1,3}%\|[^|]*\|\s*\d+/\d+)")
PROGRESS_CUSTOM_PARTIAL_RE = re.compile(r"^(.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]{8,}\s*$")
PROGRESS_TQDM_PARTIAL_RE = re.compile(r"(\d{1,3}%\|[^|]*)")
PROGRESS_STEP_PREFIX_RE = re.compile(r"^(.*?\[\s*step\s+\d+/\d+\][^:]*:)", re.IGNORECASE)
PROGRESS_SEPARATOR_RE = re.compile(r"^[=\-_\s]{6,}$")


def _create_job_output_file() -> Path:
    WEB_JOB_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return WEB_JOB_LOG_DIR / f"job_{uuid.uuid4().hex}.log"


def _close_job_output_file(job: JobData) -> None:
    fp = getattr(job, "output_fp", None)
    if fp is not None:
        try:
            fp.flush()
            fp.close()
        except Exception:
            pass
        finally:
            job.output_fp = None


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", str(text or ""))


def _extract_progress_key(line: str) -> str | None:
    clean = _strip_ansi(line).replace("\r", "").strip()
    if not clean:
        return None
    without_level = re.sub(r"^[A-Z]+\s*:?\s*", "", clean).strip()
    if without_level and PROGRESS_SEPARATOR_RE.match(without_level):
        return None

    m = PROGRESS_CUSTOM_FULL_RE.match(clean)
    if m:
        return str(m.group(1) or "").strip().lower() or None

    m = PROGRESS_TQDM_RE.search(clean)
    if m and m.start() >= 0:
        return clean[:m.start()].strip().lower() or None

    m = PROGRESS_CUSTOM_PARTIAL_RE.match(clean)
    if m:
        return str(m.group(1) or "").strip().lower() or None

    m = PROGRESS_TQDM_PARTIAL_RE.search(clean)
    if m and m.start() >= 0:
        return clean[:m.start()].strip().lower() or None

    m = PROGRESS_STEP_PREFIX_RE.match(clean)
    if m:
        return str(m.group(1) or "").strip().lower() or None

    return None


def _append_job_output(job: JobData, text: str) -> None:
    if not text:
        return
    if job.output_fp is not None:
        try:
            job.output_fp.write(text)
            job.output_fp.flush()
        except Exception:
            pass
    job.total_output_chars += len(text)

    # Keep last completed logical lines in memory (line-based, not char-based).
    # '\r' rewrites the same line and does not create a new history line.
    current = job.partial_line
    completed: List[str] = []
    for ch in text:
        if job.pending_cr:
            if ch == "\n":
                completed.append(current)
                current = ""
                job.pending_cr = False
                continue
            current = ""
            job.pending_cr = False

        if ch == "\n":
            completed.append(current)
            current = ""
        elif ch == "\r":
            job.pending_cr = True
        else:
            current += ch
    job.partial_line = current

    for line in completed:
        line_with_nl = f"{line}\n"
        progress_key = _extract_progress_key(line_with_nl)
        if progress_key and progress_key in job.progress_lines:
            prev_entry = job.progress_lines[progress_key]
            prev_len = len(prev_entry.text)
            prev_entry.text = line_with_nl
            job.output_chars += len(line_with_nl) - prev_len
            continue

        entry = OutputLine(text=line_with_nl, progress_key=progress_key)
        job.output.append(entry)
        job.output_chars += len(line_with_nl)
        if progress_key:
            job.progress_lines[progress_key] = entry

    while len(job.output) > MAX_JOB_OUTPUT_LINES:
        removed = job.output.popleft()
        job.output_chars -= len(removed.text)
        job.dropped_output_lines += 1
        if removed.progress_key and job.progress_lines.get(removed.progress_key) is removed:
            del job.progress_lines[removed.progress_key]


def _get_job_output_tail(job: JobData, max_chars: int) -> str:
    if max_chars <= 0 or not job.output:
        return ""
    total = 0
    chunks: List[str] = []
    partial = job.partial_line or ""
    if partial:
        chunks.append(partial)
        total += len(partial)
    for entry in reversed(job.output):
        chunk = entry.text
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "".join(reversed(chunks))[-max_chars:]


def _read_job_output_for_api(job: JobData) -> str:
    # Always serve compact in-memory output so progress refreshes don't consume history.
    base = "".join(entry.text for entry in job.output)
    if job.partial_line:
        base += job.partial_line

    if job.dropped_output_lines <= 0:
        return base

    notice = (
        f"[web-interface] Output too large ({job.dropped_output_lines} lines were dropped). "
        f"Showing compact log buffer (max {MAX_JOB_OUTPUT_LINES} lines).\n"
    )
    return notice + base


PARSER_SCHEMA: Dict[str, Any] = {}
PARSER_FIELDS_BY_DEST: Dict[str, Dict[str, Any]] = {}
CONFIG_TEMPLATE_CONTENT = ""
CONFIG_FORM_SCHEMA: List[Dict[str, Any]] = []
JOBS: Dict[str, JobData] = {}
JOBS_LOCK = threading.Lock()
BACKUP_LOCK = threading.Lock()
BACKUP_THREAD: threading.Thread | None = None
BACKUP_THREAD_STOP = threading.Event()

app = FastAPI(title="PhotoMigrator Web Interface")
app.mount("/static", StaticFiles(directory=str(SRC_ROOT / "web_interface" / "static")), name="static")
app.mount("/assets", StaticFiles(directory=str(PROJECT_ROOT / "assets")), name="assets")
templates = Jinja2Templates(directory=str(SRC_ROOT / "web_interface" / "html"))


def _tab_for_dest(dest: str) -> str:
    if dest in AUTOMATION_DESTS:
        return "automatic_migration"
    if dest in GOOGLE_DESTS:
        return "google_takeout"
    if dest in CLOUD_DESTS:
        return "cloud_common"
    if dest in STANDALONE_DESTS:
        return "standalone_features"
    return "general"


def _field_kind(action: argparse.Action, dest: str) -> str:
    if isinstance(action, argparse._StoreTrueAction):
        return "flag"
    if dest in BOOL_VALUE_DESTS:
        return "bool"
    if action.nargs in ("*", "+") or isinstance(action.nargs, int):
        return "list"
    if action.choices:
        return "select"
    return "text"


def _path_hint(dest: str, metavar: Any) -> str:
    name = dest.lower()
    mv = str(metavar or "").lower()
    path_tokens = ("path", "folder", "file", "takeout", "source", "target")
    if any(token in name for token in path_tokens) or any(token in mv for token in path_tokens):
        return "path"
    return ""


def _to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace(",", "\n")
        return [item.strip() for item in normalized.split("\n") if item.strip()]
    return [str(value).strip()]


def _normalize_special_folder_token(value: Any) -> str:
    return re.sub(r"[\s_-]+", "", str(value or "").strip().lower())


def _find_forbidden_special_folder_in_path(path_value: Any) -> str | None:
    blocked = {_normalize_special_folder_token(item) for item in TAKEOUT_SPECIAL_FOLDER_NAMES}
    parts = [part for part in re.split(r"[\\/]+", str(path_value or "")) if part and part not in (".", "..")]
    for part in parts:
        if _normalize_special_folder_token(part) in blocked:
            return part
    return None


def _is_automatic_migration_cloud_endpoint(value: str) -> bool:
    return bool(re.fullmatch(r"(?:synology|immich|nextcloud|google)(?:-?photos)?(?:-[123])?", value.strip().lower()))


def _bool_from_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "on"}
    return bool(value)


def _load_parser_schema() -> Dict[str, Any]:
    old_argv = sys.argv[:]
    try:
        sys.argv = ["web-interface"]
        _, parser = parse_arguments()
    finally:
        sys.argv = old_argv

    fields: List[Dict[str, Any]] = []
    by_dest: Dict[str, Dict[str, Any]] = {}
    for action in parser._actions:
        if not action.option_strings:
            continue
        if action.dest in {"help", "version", "client"}:
            continue

        long_options = [opt for opt in action.option_strings if opt.startswith("--")]
        long_option = long_options[0] if long_options else action.option_strings[-1]
        dest = action.dest.replace("_", "-")
        field = {
            "dest": dest,
            "long_option": long_option,
            "help": (action.help or "").replace("%(default)s", str(action.default)),
            "default": action.default,
            "choices": list(action.choices) if action.choices else [],
            "nargs": action.nargs,
            "tab": _tab_for_dest(dest),
            "kind": _field_kind(action, dest),
            "path_hint": _path_hint(dest, getattr(action, "metavar", None)),
        }
        fields.append(field)
        by_dest[dest] = field

    cloud_common = [field for field in fields if field["tab"] == "cloud_common"]
    merged_general = [field for field in fields if field["dest"] in (GENERAL_CORE_DESTS | GENERAL_OPTIONAL_DESTS)]
    schema = {
        "general_tabs": {
            "general": merged_general,
            "config_editor": [],
        },
        "feature_scoped": [field for field in fields if field["dest"] in FEATURE_SCOPED_DESTS],
        "tabs": {
            "google_takeout": [field for field in fields if field["tab"] == "google_takeout"],
            "google_photos": cloud_common,
            "synology_photos": cloud_common,
            "immich_photos": cloud_common,
            "nextcloud_photos": cloud_common,
            "standalone_features": [field for field in fields if field["tab"] == "standalone_features"],
            "automatic_migration": [field for field in fields if field["tab"] == "automatic_migration"],
        },
    }
    global PARSER_FIELDS_BY_DEST
    PARSER_FIELDS_BY_DEST = by_dest
    return schema


def _allowed_dests_for_tab(tab: str, selected_action_dest: str | None = None) -> set[str]:
    if tab not in TAB_TO_CATEGORY:
        raise HTTPException(status_code=400, detail=f"Unsupported tab: {tab}")

    allowed_dests = {field["dest"] for field in PARSER_SCHEMA["general_tabs"]["general"]}
    allowed_dests.update(FEATURE_SCOPED_DESTS)
    tab_dests = {field["dest"] for field in PARSER_SCHEMA["tabs"][tab]}

    if tab in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
        cloud_action_dests = {dest for dest in tab_dests if dest != "one-time-password"}
        available_actions = cloud_action_dests.intersection(
            CLOUD_ACTIONS_AVAILABLE_BY_TAB.get(tab, cloud_action_dests)
        )
        if not available_actions:
            available_actions = cloud_action_dests
        if selected_action_dest:
            if selected_action_dest not in available_actions:
                raise HTTPException(status_code=400, detail=f"Invalid selected action for tab {tab}: {selected_action_dest}")
            allowed_dests.add(selected_action_dest)
        else:
            # Backward-compatible fallback for older UI payloads.
            allowed_dests.update(available_actions)
        if "one-time-password" in tab_dests:
            allowed_dests.add("one-time-password")
    elif tab == "standalone_features":
        if selected_action_dest:
            if selected_action_dest not in tab_dests:
                raise HTTPException(status_code=400, detail=f"Invalid selected action for tab {tab}: {selected_action_dest}")
            allowed_dests.add(selected_action_dest)
        else:
            # Backward-compatible fallback for older UI payloads.
            allowed_dests.update(tab_dests)
    else:
        allowed_dests.update(tab_dests)
    return allowed_dests


def _dest_is_active_for_values(dest: str, field: Dict[str, Any], values: Dict[str, Any]) -> bool:
    raw_value = values.get(dest)
    kind = field["kind"]
    default = field["default"]
    if kind == "flag":
        return _bool_from_value(raw_value)
    if kind == "bool":
        return _bool_from_value(raw_value) != _bool_from_value(default)
    if kind == "list":
        return len(_to_list(raw_value)) > 0
    if raw_value is None:
        return False
    text = str(raw_value).strip()
    return text != "" and text != str(default)


def _build_cli_args(tab: str, values: Dict[str, Any], selected_action_dest: str | None = None) -> List[str]:
    allowed_dests = _allowed_dests_for_tab(tab, selected_action_dest)

    args: List[str] = []
    for dest in sorted(allowed_dests):
        field = PARSER_FIELDS_BY_DEST[dest]
        raw_value = values.get(dest)
        kind = field["kind"]
        long_option = field["long_option"]
        default = field["default"]

        if kind == "flag":
            if _bool_from_value(raw_value):
                args.append(long_option)
            continue

        if kind == "bool":
            current = _bool_from_value(raw_value)
            default_bool = _bool_from_value(default)
            if current != default_bool:
                args.extend([long_option, "true" if current else "false"])
            continue

        if kind == "list":
            values_list = _to_list(raw_value)
            if values_list:
                args.append(long_option)
                args.extend(values_list)
            continue

        if raw_value is None:
            continue

        text = str(raw_value).strip()
        if text == "" or text == str(default):
            continue
        args.extend([long_option, text])

    if tab == "google_photos":
        args.extend(["--client", "google-photos"])
    elif tab == "synology_photos":
        args.extend(["--client", "synology"])
    elif tab == "immich_photos":
        args.extend(["--client", "immich"])
    elif tab == "nextcloud_photos":
        args.extend(["--client", "nextcloud"])
    elif tab == "google_takeout":
        args.extend(["--client", "google-takeout"])

    return args


def _normalize_incoming_values(values: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    incoming_values = dict(values or {})
    for key, value in list(incoming_values.items()):
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if not trimmed.startswith("/docker"):
            continue
        if key == "configuration-file":
            incoming_values[key] = str(config_path)
        else:
            incoming_values[key] = trimmed.replace("/docker", "/app/data", 1)

    if not str(incoming_values.get("configuration-file", "")).strip():
        incoming_values["configuration-file"] = str(config_path)
    return incoming_values


def _build_command_from_payload(payload: RunRequest, config_path: Path) -> List[str]:
    normalized_values = _normalize_incoming_values(payload.values or {}, config_path=config_path)
    blocked_folders = ", ".join([f"'{name}'" for name in TAKEOUT_SPECIAL_FOLDER_NAMES])
    if payload.tab == "google_takeout":
        takeout_value = str(normalized_values.get("google-takeout", "")).strip()
        if takeout_value:
            offending_component = _find_forbidden_special_folder_in_path(takeout_value)
            if offending_component:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid --google-takeout path '{takeout_value}'. "
                        f"It contains forbidden folder '{offending_component}' "
                        f"(special folders: {blocked_folders})."
                    ),
                )
    elif payload.tab == "automatic_migration":
        source_value = str(normalized_values.get("source", "")).strip()
        if source_value and not _is_automatic_migration_cloud_endpoint(source_value):
            offending_component = _find_forbidden_special_folder_in_path(source_value)
            if offending_component:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid --source path '{source_value}'. "
                        f"It contains forbidden folder '{offending_component}' "
                        f"(special folders: {blocked_folders})."
                    ),
                )
    cli_args = _build_cli_args(payload.tab, normalized_values, payload.selected_action_dest)
    return [sys.executable, str(CLI_ENTRYPOINT), *cli_args]


def _value_is_provided(dest: str, values: Dict[str, Any]) -> bool:
    field = PARSER_FIELDS_BY_DEST.get(dest)
    raw_value = values.get(dest)
    if not field:
        return str(raw_value or "").strip() != ""
    kind = field.get("kind")
    if kind == "flag":
        return _bool_from_value(raw_value)
    if kind == "list":
        return len(_to_list(raw_value)) > 0
    return str(raw_value or "").strip() != ""


def _parse_required_dests_from_help(help_text: str, ignore_dests: set[str] | None = None) -> set[str]:
    if not help_text:
        return set()
    ignored = {str(item or "").strip().lower() for item in (ignore_dests or set()) if str(item or "").strip()}
    required: set[str] = set()
    lines = str(help_text).replace("\r\n", "\n").split("\n")
    for line in lines:
        text = str(line or "").strip()
        if not text:
            continue
        if re.match(r"^Example:", text, flags=re.IGNORECASE):
            continue
        if not re.search(r"\brequired?\b", text, flags=re.IGNORECASE) and not re.search(r"\brequires\b", text, flags=re.IGNORECASE):
            continue
        for match in re.findall(r"--([a-z0-9-]+)", text, flags=re.IGNORECASE):
            dest = str(match or "").strip().lower()
            if not dest or dest == "client" or dest in ignored:
                continue
            if dest in PARSER_FIELDS_BY_DEST:
                required.add(dest)
    return required


def _required_dests_for_payload(tab: str, selected_action_dest: str | None) -> set[str]:
    required: set[str] = set()
    if tab == "google_takeout":
        required.add("google-takeout")
        return required

    if tab == "automatic_migration":
        required.update({"source", "target"})
        return required

    if tab in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos", "standalone_features"} and selected_action_dest:
        tab_fields = {field["dest"]: field for field in PARSER_SCHEMA["tabs"].get(tab, [])}
        selected_field = tab_fields.get(selected_action_dest)
        if selected_field and selected_field.get("kind") != "flag":
            required.add(selected_action_dest)
        for dep in MODULE_DEPENDENCIES_REQUIRED.get(tab, {}).get(selected_action_dest, set()):
            required.add(dep)
        if selected_field:
            required.update(
                _parse_required_dests_from_help(
                    selected_field.get("help", "") or "",
                    ignore_dests={selected_field.get("dest", "")},
                )
            )
    return required


def _path_validation_scope_for_payload(
    tab: str,
    selected_action_dest: str | None,
    values: Dict[str, Any],
) -> set[str]:
    required = _required_dests_for_payload(tab, selected_action_dest)
    scoped: set[str] = set()
    for dest in required:
        field = PARSER_FIELDS_BY_DEST.get(dest)
        if field and field.get("path_hint") == "path":
            scoped.add(dest)
    return scoped


def _allowed_delete_root_for_path(target: Path, allowed_roots: List[Path]) -> Path | None:
    for root in allowed_roots:
        try:
            target.relative_to(root)
            return root
        except ValueError:
            continue
    return None


def _validate_payload_paths_for_user(
    values: Dict[str, Any],
    current_user: Dict[str, Any],
    path_scope: set[str] | None = None,
) -> None:
    _sanitize_payload_paths_for_user(values, current_user, path_scope=path_scope)


def _sanitize_payload_paths_for_user(
    values: Dict[str, Any],
    current_user: Dict[str, Any],
    path_scope: set[str] | None = None,
) -> Dict[str, Any]:
    normalized_values = dict(values or {})
    primary_root = _ensure_user_roots_exist(current_user)[0]
    for dest, field in PARSER_FIELDS_BY_DEST.items():
        if path_scope is not None and dest not in path_scope:
            continue
        if dest == "configuration-file":
            continue
        if field.get("path_hint") != "path":
            continue
        raw_value = normalized_values.get(dest)
        if raw_value is None:
            continue
        candidates = _to_list(raw_value) if field.get("kind") == "list" else [str(raw_value)]
        sanitized_candidates: List[str] = []
        for candidate in candidates:
            text = str(candidate or "").strip()
            if not text:
                continue
            if dest in {"source", "target"} and _is_automatic_migration_cloud_endpoint(text):
                sanitized_candidates.append(text)
                continue
            if text.startswith("/"):
                sanitized_candidates.append(str(_resolve_user_path(text, current_user)))
                continue
            # Relative paths are forced under user's data home to avoid escaping outside allowed roots.
            sanitized_candidates.append(str(_resolve_user_path(str((primary_root / text).resolve()), current_user)))
        if field.get("kind") == "list":
            normalized_values[dest] = sanitized_candidates
        elif sanitized_candidates:
            normalized_values[dest] = sanitized_candidates[0]
    return normalized_values


def _is_config_path_key(key: str) -> bool:
    lowered = str(key or "").strip().lower()
    if not lowered:
        return False
    tokens = ("path", "folder", "file", "directory", "takeout", "source", "target", "input", "output")
    return any(token in lowered for token in tokens)


def _sanitize_config_values_for_user(
    values: Dict[str, Dict[str, str]],
    form_schema: List[Dict[str, Any]],
    current_user: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    merged = _merge_values_with_schema(values or {}, form_schema)
    sanitized: Dict[str, Dict[str, str]] = {}
    primary_root = _ensure_user_roots_exist(current_user)[0]
    for section in form_schema:
        section_name = str(section.get("name") or "")
        section_values = merged.get(section_name, {})
        sanitized[section_name] = {}
        for field in section.get("fields", []):
            key = str(field.get("key") or "")
            raw_value = str(section_values.get(key, "") or "")
            text = raw_value.strip()
            if not text or not _is_config_path_key(key):
                sanitized[section_name][key] = raw_value
                continue
            if key in {"source", "target"} and _is_automatic_migration_cloud_endpoint(text):
                sanitized[section_name][key] = text
                continue
            if text.startswith("/"):
                sanitized[section_name][key] = str(_resolve_user_path(text, current_user))
                continue
            candidate = str((primary_root / text).resolve())
            sanitized[section_name][key] = str(_resolve_user_path(candidate, current_user))
    return sanitized


def _normalize_backup_mode(mode: str | None) -> str:
    raw = str(mode or "").strip().lower()
    if raw in WEB_BACKUP_MODES:
        return raw
    return WEB_BACKUP_DEFAULT_MODE if WEB_BACKUP_DEFAULT_MODE in WEB_BACKUP_MODES else "daily_2am"


def _compute_next_backup_run(schedule_mode: str, base_dt: datetime | None = None) -> datetime:
    now_local = base_dt if base_dt is not None else datetime.now().astimezone()
    mode = _normalize_backup_mode(schedule_mode)
    if mode == "hourly":
        return (now_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    if mode == "weekly_monday_2am":
        candidate = now_local.replace(hour=2, minute=0, second=0, microsecond=0)
        days_ahead = (0 - candidate.weekday()) % 7
        if days_ahead == 0 and candidate <= now_local:
            days_ahead = 7
        return candidate + timedelta(days=days_ahead)
    # daily_2am
    candidate = now_local.replace(hour=2, minute=0, second=0, microsecond=0)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate


def _run_job(job_id: str, process: subprocess.Popen[str]) -> None:
    job = JOBS[job_id]
    try:
        assert process.stdout is not None
        while True:
            # Read per-character to preserve immediate updates and avoid waiting
            # for large chunks/new lines in long-running tasks.
            chunk = process.stdout.read(1)
            if chunk == "":
                break
            with JOBS_LOCK:
                _append_job_output(job, chunk)
                lowered_tail = _get_job_output_tail(job, TAIL_CONFIRM_CHARS).lower()
                if (
                    "awaiting user confirmation (yes/no)" in lowered_tail
                    or "do you want to continue? (yes/no):" in lowered_tail
                ):
                    job.awaiting_confirmation = True
                elif "continuing..." in lowered_tail or "operation canceled." in lowered_tail:
                    job.awaiting_confirmation = False
        rc = process.wait()
        with JOBS_LOCK:
            job.return_code = rc
            if job.stop_requested:
                job.status = "stopped"
            else:
                job.status = "success" if rc == 0 else "failed"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.awaiting_confirmation = False
            job.process = None
            _close_job_output_file(job)
    except Exception as exc:
        with JOBS_LOCK:
            _append_job_output(job, f"\n[web-interface] Internal error: {exc}\n")
            job.return_code = -1
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.awaiting_confirmation = False
            job.process = None
            _close_job_output_file(job)


def _force_kill_job_process(job_id: str, process: subprocess.Popen[str], delay_seconds: float = 3.0) -> None:
    time.sleep(delay_seconds)
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        same_process = job.process is process
        still_running = process.poll() is None
        if same_process and still_running and job.stop_requested:
            try:
                process.kill()
            except Exception:
                pass


def _resolve_doc_path(doc_name: str) -> Path:
    normalized = str(doc_name or "").strip().lower()
    allowed = {
        "readme": "README.md",
        "changelog": "CHANGELOG.md",
        "roadmap": "ROADMAP.md",
        "config": "Config.ini",
        "help": "help/help.md",
    }
    filename = allowed.get(normalized)
    if not filename:
        raise HTTPException(status_code=400, detail="Unsupported document. Use 'readme', 'changelog', 'roadmap', 'config' or 'help'.")

    candidates = [
        Path("/app") / filename,
        PROJECT_ROOT / filename,
    ]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except Exception:
            continue
    raise HTTPException(status_code=404, detail=f"Document not found: {filename}")


def _resolve_help_doc_path(doc_file: str) -> Path:
    requested = str(doc_file or "").strip().replace("\\", "/")
    if not requested.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only markdown files are allowed.")

    target = (PROJECT_ROOT / "help" / requested).resolve()
    help_root = (PROJECT_ROOT / "help").resolve()
    try:
        target.relative_to(help_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid help document path.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Help document not found: {requested}")
    return target


@app.on_event("startup")
def _startup() -> None:
    global PARSER_SCHEMA, CONFIG_TEMPLATE_CONTENT, CONFIG_FORM_SCHEMA
    PARSER_SCHEMA = _load_parser_schema()
    CONFIG_TEMPLATE_CONTENT = _load_default_config_template()
    CONFIG_FORM_SCHEMA = _extend_form_schema_with_web_interface_theme(
        _parse_template_to_form_schema(CONFIG_TEMPLATE_CONTENT)
    )
    _init_web_db(CONFIG_FORM_SCHEMA)
    _start_backup_scheduler()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session_token: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)) -> HTMLResponse:
    if _user_from_session_token(session_token):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
        },
    )


@app.post("/api/auth/login")
def api_login(payload: LoginRequest, response: Response, request: Request) -> Dict[str, Any]:
    username = str(payload.username or "").strip()
    password = str(payload.password or "")
    user = _fetch_user_by_username(username)
    if not user or not bool(user.get("is_active")) or not _pbkdf2_verify_password(password, str(user.get("password_hash") or "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_session_for_user(int(user["id"]))
    _record_access_log(int(user["id"]), str(user.get("username") or username), _extract_client_ip(request))
    response.set_cookie(
        key=WEB_SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=WEB_SESSION_TTL_SECONDS,
        path="/",
    )
    return {"ok": True}


@app.post("/api/auth/logout")
def api_logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE),
) -> Dict[str, Any]:
    _delete_session(session_token)
    response.delete_cookie(WEB_SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def api_me(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    roots = [str(path) for path in _ensure_user_roots_exist(current_user)]
    return {
        "id": int(current_user["id"]),
        "username": str(current_user["username"]),
        "role": str(current_user.get("role") or "user"),
        "is_admin": str(current_user.get("role") or "").strip().lower() == "admin",
        "must_change_password": bool(current_user.get("must_change_password")),
        "allowed_roots": roots,
        "data_subpath": str(current_user.get("data_subpath") or ""),
        "volume1_subpath": str(current_user.get("volume1_subpath") or ""),
    }


@app.post("/api/me/change-password")
def api_change_password(payload: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    current_password = str(payload.current_password or "")
    new_password = str(payload.new_password or "")
    if not _pbkdf2_verify_password(current_password, str(current_user.get("password_hash") or "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    conn = _db_connect()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0, updated_at = ? WHERE id = ?",
            (_pbkdf2_hash_password(new_password), _utc_now_iso(), int(current_user["id"])),
        )
        conn.commit()
    finally:
        conn.close()
    return {"saved": True}


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session_token: str | None = Cookie(default=None, alias=WEB_SESSION_COOKIE)) -> HTMLResponse:
    current_user = _user_from_session_token(session_token)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "tool_date": TOOL_DATE,
            "takeout_special_folders": list(TAKEOUT_SPECIAL_FOLDER_NAMES),
            "username": str(current_user.get("username") or ""),
            "role": str(current_user.get("role") or "user"),
            "is_admin": str(current_user.get("role") or "").strip().lower() == "admin",
        },
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, current_user: Dict[str, Any] = Depends(_require_admin)) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "username": str(current_user.get("username") or ""),
        },
    )


@app.get("/docs/view/{doc_name}", response_class=HTMLResponse)
def docs_view(request: Request, doc_name: str, current_user: Dict[str, Any] = Depends(_require_user)) -> HTMLResponse:
    normalized = str(doc_name or "").strip().lower()
    if normalized not in {"readme", "changelog", "roadmap", "config", "help"}:
        raise HTTPException(status_code=404, detail="Document not found")
    pretty_title = "README.md"
    if normalized == "changelog":
        pretty_title = "CHANGELOG.md"
    elif normalized == "roadmap":
        pretty_title = "ROADMAP.md"
    elif normalized == "config":
        pretty_title = "Config.ini"
    elif normalized == "help":
        pretty_title = "HELP.md"
    return templates.TemplateResponse(
        "doc_view.html",
        {
            "request": request,
            "doc_name": pretty_title,
            "doc_api_url": f"/api/docs/{normalized}",
            "tool_name": TOOL_NAME,
        },
    )


@app.get("/docs/view/help/{doc_file:path}", response_class=HTMLResponse)
def docs_view_help_file(request: Request, doc_file: str, current_user: Dict[str, Any] = Depends(_require_user)) -> HTMLResponse:
    path = _resolve_help_doc_path(doc_file)
    return templates.TemplateResponse(
        "doc_view.html",
        {
            "request": request,
            "doc_name": path.name,
            "doc_api_url": f"/api/docs/help/{doc_file}",
            "tool_name": TOOL_NAME,
        },
    )


@app.get("/api/schema")
def get_schema(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    return PARSER_SCHEMA


@app.get("/api/config")
def get_config(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    merged = _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
    content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
    return {"path": _user_config_db_path(current_user), "content": content}


@app.get("/api/config/form")
def get_config_form(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    return _build_config_form_response(current_user)


@app.post("/api/config/admin-override")
def config_admin_override(
    payload: ConfigAdminOverrideRequest,
    current_user: Dict[str, Any] = Depends(_require_user),
) -> Dict[str, Any]:
    if not _is_demo_user(current_user):
        return {"authorized": True, "required": False}
    admin_user = _validate_admin_override_credentials(payload.admin_username, payload.admin_password)
    return {
        "authorized": True,
        "required": True,
        "action": str(payload.action or "").strip().lower(),
        "admin_username": str(admin_user.get("username") or ""),
    }


@app.post("/api/config/form")
def save_config_form(payload: ConfigFormSaveRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    incoming = payload.values or {}
    merged = _merge_values_with_schema(incoming, CONFIG_FORM_SCHEMA)
    merged = _sanitize_config_values_for_user(merged, CONFIG_FORM_SCHEMA, current_user)
    _enforce_demo_save_policy(
        current_user,
        merged,
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
    )
    _save_user_config_values(current_user, merged, CONFIG_FORM_SCHEMA)
    _sync_user_theme_to_state(current_user, merged)
    return {"saved": True, "path": _user_config_db_path(current_user)}


@app.post("/api/config/import")
def import_config(payload: ConfigUpdateRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    _require_demo_admin_override(
        current_user,
        action="import",
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
    )
    parsed_values = _parse_ini_text_to_values(payload.content or "", strict=True)
    merged = _merge_values_with_schema(parsed_values, CONFIG_FORM_SCHEMA)
    _save_user_config_values(current_user, merged, CONFIG_FORM_SCHEMA)
    _sync_user_theme_to_state(current_user, merged)
    response = _build_config_form_response(current_user, merged=merged)
    response.update({"saved": True, "imported": True})
    return response


@app.get("/api/config/export")
def export_config(current_user: Dict[str, Any] = Depends(_require_user)) -> Response:
    _ensure_export_allowed(current_user)
    merged = _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
    content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
    filename = f"Config_{str(current_user.get('username') or 'user')}.ini"
    payload = content.encode("utf-8")
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",
        "Content-Length": str(len(payload)),
    }
    return Response(content=payload, media_type="application/octet-stream", headers=headers)


@app.get("/api/config/export-content")
def export_config_content(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    _ensure_export_allowed(current_user)
    merged = _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
    content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
    filename = f"Config_{str(current_user.get('username') or 'user')}.ini"
    return {"filename": filename, "content": content}


@app.post("/api/config/export-content")
def export_config_content_from_values(
    payload: ConfigFormSaveRequest,
    current_user: Dict[str, Any] = Depends(_require_user),
) -> Dict[str, Any]:
    _require_demo_admin_override(
        current_user,
        action="export",
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
    )
    merged = _merge_values_with_schema(payload.values or {}, CONFIG_FORM_SCHEMA)
    content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
    filename = f"Config_{str(current_user.get('username') or 'user')}.ini"
    return {"filename": filename, "content": content}


@app.post("/api/config/export-to-storage")
def export_config_to_storage(
    payload: ConfigFormSaveRequest,
    current_user: Dict[str, Any] = Depends(_require_user),
) -> Dict[str, Any]:
    _require_demo_admin_override(
        current_user,
        action="export",
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
    )
    merged = _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
    content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
    primary_root = _ensure_user_roots_exist(current_user)[0]
    export_dir = (primary_root / "exports").resolve()
    try:
        export_dir.relative_to(primary_root)
    except ValueError:
        raise HTTPException(status_code=500, detail="Export directory resolution failed.")
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Config_{str(current_user.get('username') or 'user')}_{timestamp}.ini"
    target = (export_dir / filename).resolve()
    try:
        target.relative_to(primary_root)
    except ValueError:
        raise HTTPException(status_code=500, detail="Export file path resolution failed.")
    target.write_text(content, encoding="utf-8")
    return {"saved": True, "path": str(target), "filename": filename}


@app.get("/api/state")
def get_state(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    fresh_user = _fetch_user_by_id(int(current_user["id"])) or current_user
    payload = _read_user_state_payload(fresh_user)
    return {"path": f"db://users/{current_user['id']}/state.json", "values": payload["values"], "ui_state": payload["ui_state"]}


@app.post("/api/state")
def save_state(payload: StateUpdateRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    _save_user_state_payload(current_user, payload.values or {}, payload.ui_state or {})
    return {"saved": True, "path": f"db://users/{current_user['id']}/state.json"}


@app.post("/api/config")
def save_config(payload: ConfigUpdateRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    parsed_values = _parse_ini_text_to_values(payload.content or "")
    merged = _merge_values_with_schema(parsed_values, CONFIG_FORM_SCHEMA)
    merged = _sanitize_config_values_for_user(merged, CONFIG_FORM_SCHEMA, current_user)
    _enforce_demo_save_policy(
        current_user,
        merged,
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
    )
    _save_user_config_values(current_user, merged, CONFIG_FORM_SCHEMA)
    _sync_user_theme_to_state(current_user, merged)
    return {"saved": True, "path": _user_config_db_path(current_user)}


@app.get("/api/docs/{doc_name}")
def get_markdown_doc(doc_name: str, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    if str(doc_name or "").strip().lower() == "config":
        merged = _merge_values_with_schema(_get_user_config_values(current_user), CONFIG_FORM_SCHEMA)
        content = _serialize_values_to_ini_with_comments(merged, CONFIG_TEMPLATE_CONTENT)
        return {
            "name": "config",
            "path": _user_config_db_path(current_user),
            "content": content,
        }
    path = _resolve_doc_path(doc_name)
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "name": doc_name,
        "path": str(path),
        "content": content,
    }


@app.get("/api/docs/help/{doc_file:path}")
def get_help_markdown_doc(doc_file: str, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    path = _resolve_help_doc_path(doc_file)
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "name": path.name,
        "path": str(path),
        "content": content,
    }


@app.get("/api/docs/help-index")
def get_help_docs_index(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    help_root = (PROJECT_ROOT / "help").resolve()
    docs: List[Dict[str, str]] = []
    if help_root.exists() and help_root.is_dir():
        for file_path in sorted(help_root.rglob("*.md"), key=lambda p: str(p).lower()):
            try:
                rel = file_path.resolve().relative_to(help_root).as_posix()
            except Exception:
                continue
            docs.append(
                {
                    "name": file_path.name,
                    "relative_path": rel,
                    "url": f"/docs/view/help/{rel}",
                }
            )
    return {"root": str(help_root), "documents": docs}


@app.get("/api/fs/list")
def list_directories(
    path: str | None = Query(None),
    current_user: Dict[str, Any] = Depends(_require_user),
) -> Dict[str, Any]:
    roots = _ensure_user_roots_exist(current_user)
    fallback_root = roots[0]
    current = _resolve_user_path(path or str(fallback_root), current_user)
    if not current.exists():
        current = fallback_root
    if not current.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {current}")

    dirs = []
    for item in sorted(current.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir():
            dirs.append({"name": item.name, "path": str(item)})
    parent = None
    if current.parent != current:
        for root in roots:
            try:
                current.relative_to(root)
                if current != root:
                    parent = str(current.parent)
                break
            except ValueError:
                continue
    return {"path": str(current), "parent": parent, "directories": dirs, "allowed_roots": [str(root) for root in roots]}


@app.get("/api/fs/list-files")
def list_csv_files(
    path: str | None = Query(None),
    current_user: Dict[str, Any] = Depends(_require_user),
) -> Dict[str, Any]:
    roots = _ensure_user_roots_exist(current_user)
    fallback_root = roots[0]
    current = _resolve_user_path(path or str(fallback_root), current_user)
    if not current.exists():
        current = fallback_root
    if not current.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {current}")

    dirs: List[Dict[str, str]] = []
    files: List[Dict[str, str]] = []
    for item in sorted(current.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir():
            dirs.append({"name": item.name, "path": str(item)})
        elif item.is_file() and item.suffix.lower() == ".csv":
            files.append({"name": item.name, "path": str(item)})
    parent = None
    if current.parent != current:
        for root in roots:
            try:
                current.relative_to(root)
                if current != root:
                    parent = str(current.parent)
                break
            except ValueError:
                continue
    return {"path": str(current), "parent": parent, "directories": dirs, "files": files, "allowed_roots": [str(root) for root in roots]}


@app.post("/api/fs/mkdir")
def make_directory(payload: FolderCreateRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    roots = _ensure_user_roots_exist(current_user)
    parent = _resolve_user_path(payload.path or str(roots[0]), current_user)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid parent directory: {parent}")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required.")
    if name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Folder name is invalid.")

    name_path = Path(name).expanduser()
    if name_path.is_absolute():
        target = _resolve_user_path(str(name_path), current_user)
    else:
        if "/" in name or "\\" in name:
            raise HTTPException(status_code=400, detail="Folder name cannot contain path separators.")
        target = (parent / name).resolve()
        _resolve_user_path(str(target), current_user)

    if target.exists():
        raise HTTPException(status_code=409, detail=f"Folder already exists: {target}")
    target.mkdir(parents=True, exist_ok=False)
    return {"created": True, "path": str(target), "parent": str(parent)}


@app.post("/api/fs/rmdir")
def remove_directories(payload: FolderDeleteRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    roots = _ensure_user_roots_exist(current_user)
    requested_paths = [str(item or "").strip() for item in (payload.paths or []) if str(item or "").strip()]
    if not requested_paths:
        raise HTTPException(status_code=400, detail="At least one folder path is required.")

    removed: List[str] = []
    failed: List[Dict[str, str]] = []

    for raw_path in requested_paths:
        try:
            target = _resolve_user_path(raw_path, current_user)
        except HTTPException as ex:
            failed.append({"path": str(raw_path), "detail": str(ex.detail)})
            continue

        allowed_root = _allowed_delete_root_for_path(target, roots)
        if allowed_root is None:
            allowed = ", ".join(str(root) for root in roots)
            failed.append({"path": str(target), "detail": f"Folder must be inside one of: {allowed}"})
            continue
        if target == allowed_root:
            failed.append({"path": str(target), "detail": f"Base folder cannot be removed: {allowed_root}"})
            continue
        if not target.exists():
            failed.append({"path": str(target), "detail": "Folder does not exist."})
            continue
        if not target.is_dir():
            failed.append({"path": str(target), "detail": "Path is not a folder."})
            continue

        try:
            if payload.recursive:
                shutil.rmtree(target)
            else:
                target.rmdir()
            removed.append(str(target))
        except Exception as error:
            failed.append({"path": str(target), "detail": str(error)})

    if not removed:
        raise HTTPException(status_code=400, detail={"removed": removed, "failed": failed})
    return {"removed": removed, "failed": failed}


@app.post("/api/preview")
def preview_cli(payload: RunRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    config_path = _materialize_user_config_to_file(current_user, CONFIG_FORM_SCHEMA)
    normalized_values = _normalize_incoming_values(payload.values or {}, config_path=config_path)
    scope = _path_validation_scope_for_payload(payload.tab, payload.selected_action_dest, normalized_values)
    normalized_values = _sanitize_payload_paths_for_user(normalized_values, current_user, path_scope=scope)
    command = _build_command_from_payload(RunRequest(tab=payload.tab, values=normalized_values, selected_action_dest=payload.selected_action_dest), config_path=config_path)
    return {"command": subprocess.list2cmdline(command)}


@app.post("/api/run")
def run_cli(payload: RunRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    config_path = _materialize_user_config_to_file(current_user, CONFIG_FORM_SCHEMA)
    normalized_values = _normalize_incoming_values(payload.values or {}, config_path=config_path)
    scope = _path_validation_scope_for_payload(payload.tab, payload.selected_action_dest, normalized_values)
    normalized_values = _sanitize_payload_paths_for_user(normalized_values, current_user, path_scope=scope)
    required_dests = _required_dests_for_payload(payload.tab, payload.selected_action_dest)
    missing = [dest for dest in sorted(required_dests) if not _value_is_provided(dest, normalized_values)]
    if missing:
        joined = ", ".join(f"'--{dest}'" for dest in missing)
        raise HTTPException(status_code=400, detail=f"Missing required argument(s): {joined}")
    payload = RunRequest(tab=payload.tab, values=normalized_values, selected_action_dest=payload.selected_action_dest)
    command = _build_command_from_payload(payload, config_path=config_path)
    child_env = os.environ.copy()
    child_env["PHOTOMIGRATOR_ALLOW_STDIN_PIPE"] = "1"
    child_env["PHOTOMIGRATOR_WEB_MODE"] = "1"
    child_env["PHOTOMIGRATOR_DOCKER_BASE_PATH"] = str(_ensure_user_roots_exist(current_user)[0])
    child_env["PHOTOMIGRATOR_CONFIG_PATH"] = str(config_path)

    job_id = uuid.uuid4().hex
    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=child_env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    with JOBS_LOCK:
        JOBS[job_id] = JobData(command=command, process=process, tab=payload.tab, owner_user_id=int(current_user["id"]))

    thread = threading.Thread(target=_run_job, args=(job_id, process), daemon=True)
    thread.start()

    return {"job_id": job_id, "command": subprocess.list2cmdline(command)}


@app.get("/api/jobs/_active")
def get_active_job(current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    with JOBS_LOCK:
        active_jobs = [
            (job_id, job)
            for job_id, job in JOBS.items()
            if job.status in {"running", "stopping"} and int(job.owner_user_id or -1) == int(current_user["id"])
        ]
        if not active_jobs:
            return {"job_id": None}
        job_id, job = max(active_jobs, key=lambda item: item[1].started_at or "")
        return {
            "job_id": job_id,
            "tab": job.tab,
            "status": job.status,
            "started_at": job.started_at,
            "command": job.command_string,
        }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
        if int(job.owner_user_id or -1) != int(current_user["id"]):
            raise HTTPException(status_code=404, detail="Job not found")
        output = _read_job_output_for_api(job)
        can_send_input = bool(
            job.status == "running"
            and job.process is not None
            and job.process.stdin is not None
            and not job.process.stdin.closed
        )
        can_stop = bool(job.status in {"running", "stopping"} and job.process is not None)
        return {
            "job_id": job_id,
            "tab": job.tab,
            "status": job.status,
            "return_code": job.return_code,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "command": job.command_string,
            "can_send_input": can_send_input,
            "can_stop": can_stop,
            "awaiting_confirmation": bool(can_send_input and job.awaiting_confirmation),
            "output": output,
        }


class JobInputRequest(BaseModel):
    text: str = ""


@app.post("/api/jobs/{job_id}/input")
def send_job_input(job_id: str, payload: JobInputRequest, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
        if int(job.owner_user_id or -1) != int(current_user["id"]):
            raise HTTPException(status_code=404, detail="Job not found")
        process = job.process
        if job.status != "running" or process is None or process.stdin is None or process.stdin.closed:
            raise HTTPException(status_code=409, detail="Job is not accepting input")
        text = (payload.text or "").rstrip("\r\n")
        try:
            process.stdin.write(text + "\n")
            process.stdin.flush()
            job.awaiting_confirmation = False
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Unable to send input: {exc}")
    return {"sent": True}


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str, current_user: Dict[str, Any] = Depends(_require_user)) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
        if int(job.owner_user_id or -1) != int(current_user["id"]):
            raise HTTPException(status_code=404, detail="Job not found")
        process = job.process
        if process is None or job.status not in {"running", "stopping"}:
            raise HTTPException(status_code=409, detail="Job is not running")
        job.stop_requested = True
        job.status = "stopping"
        job.awaiting_confirmation = False

    try:
        process.terminate()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unable to stop job: {exc}")

    threading.Thread(target=_force_kill_job_process, args=(job_id, process), daemon=True).start()
    return {"stopping": True}


@app.get("/api/admin/users")
def admin_list_users(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    conn = _db_connect()
    try:
        rows = conn.execute(
            """
            SELECT id, username, role, is_active, must_change_password, data_subpath, volume1_subpath, created_at, updated_at
            FROM users
            ORDER BY username COLLATE NOCASE ASC
            """
        ).fetchall()
    finally:
        conn.close()
    users = []
    for row in rows:
        user = dict(row)
        user["is_active"] = bool(user.get("is_active"))
        user["must_change_password"] = bool(user.get("must_change_password"))
        users.append(user)
    return {"users": users}


@app.post("/api/admin/users")
def admin_create_user(payload: AdminUserCreateRequest, current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    username = str(payload.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    role = str(payload.role or "user").strip().lower()
    if role not in WEB_ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Role must be one of: admin, user, demo.")
    data_subpath = _normalize_subpath(payload.data_subpath, username)
    volume1_subpath = _normalize_subpath(payload.volume1_subpath, username)

    now = _utc_now_iso()
    conn = _db_connect()
    try:
        existing = conn.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists.")
        cursor = conn.execute(
            """
            INSERT INTO users (
                username, password_hash, role, is_active, must_change_password,
                data_subpath, volume1_subpath, state_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)
            """,
            (
                username,
                _pbkdf2_hash_password(payload.password),
                role,
                1 if payload.is_active else 0,
                1 if payload.must_change_password else 0,
                data_subpath,
                volume1_subpath,
                now,
                now,
            ),
        )
        user_id = int(cursor.lastrowid)
        template_defaults = _merge_values_with_schema({}, CONFIG_FORM_SCHEMA)
        encrypted_defaults = _encrypt_config_values(template_defaults, CONFIG_FORM_SCHEMA)
        conn.execute(
            "INSERT INTO user_configs (user_id, config_json, updated_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(encrypted_defaults, ensure_ascii=False), now),
        )
        conn.execute(
            "INSERT INTO user_states (user_id, state_json, updated_at) VALUES (?, '{}', ?)",
            (user_id, now),
        )
        conn.commit()
    finally:
        conn.close()
    created_user = _fetch_user_by_id(user_id)
    if created_user:
        _ensure_user_roots_exist(created_user)
    return {"created": True, "user_id": user_id}


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, payload: AdminUserUpdateRequest, current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    target = _fetch_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    updates: Dict[str, Any] = {}
    if payload.role is not None:
        role = str(payload.role or "").strip().lower()
        if role not in WEB_ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Role must be one of: admin, user, demo.")
        updates["role"] = role
    if payload.is_active is not None:
        updates["is_active"] = 1 if payload.is_active else 0
    if payload.must_change_password is not None:
        updates["must_change_password"] = 1 if payload.must_change_password else 0
    if payload.data_subpath is not None:
        updates["data_subpath"] = _normalize_subpath(payload.data_subpath, str(target.get("username") or "user"))
    if payload.volume1_subpath is not None:
        updates["volume1_subpath"] = _normalize_subpath(payload.volume1_subpath, str(target.get("username") or "user"))
    if payload.password is not None:
        updates["password_hash"] = _pbkdf2_hash_password(str(payload.password))
        updates["must_change_password"] = 0
    if not updates:
        return {"updated": True}

    current_role = str(target.get("role") or "").strip().lower()
    current_active = bool(target.get("is_active"))
    next_role = str(updates.get("role", current_role)).strip().lower()
    next_active = bool(updates.get("is_active", 1 if current_active else 0))

    if current_role == "admin" and current_active and (next_role != "admin" or not next_active):
        conn = _db_connect()
        try:
            admins = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE LOWER(TRIM(role)) = 'admin' AND is_active = 1"
            ).fetchone()
        finally:
            conn.close()
        if int(admins["count"]) <= 1:
            if next_role != "admin":
                raise HTTPException(status_code=400, detail="Cannot change role of the last active admin.")
            raise HTTPException(status_code=400, detail="Cannot deactivate the last active admin.")

    set_clause = ", ".join(f"{column} = ?" for column in updates.keys())
    params = list(updates.values()) + [_utc_now_iso(), int(user_id)]
    conn = _db_connect()
    try:
        conn.execute(f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()
    updated = _fetch_user_by_id(user_id)
    if updated:
        _ensure_user_roots_exist(updated)
    return {"updated": True}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    if int(current_user["id"]) == int(user_id):
        raise HTTPException(status_code=400, detail="You cannot delete your own user.")
    conn = _db_connect()
    try:
        row = conn.execute("SELECT id, role FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        if str(row["role"] or "").strip().lower() == "admin":
            admins = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE LOWER(TRIM(role)) = 'admin' AND is_active = 1"
            ).fetchone()
            if int(admins["count"]) <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last active admin.")
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (int(user_id),))
        conn.execute("DELETE FROM user_configs WHERE user_id = ?", (int(user_id),))
        conn.execute("DELETE FROM user_states WHERE user_id = ?", (int(user_id),))
        conn.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        conn.commit()
    finally:
        conn.close()
    return {"deleted": True}


@app.get("/api/admin/db/tables")
def admin_db_tables(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    tables = _list_admin_db_tables()
    conn = _db_connect()
    try:
        out: List[Dict[str, Any]] = []
        for table in tables:
            cols = _table_columns(table)
            count = int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
            out.append({"name": table, "columns": cols, "row_count": count})
    finally:
        conn.close()
    return {"tables": out}


@app.get("/api/admin/access-logs")
def admin_access_logs(
    limit: int = Query(200, ge=1, le=2000),
    username: str = Query("", max_length=256),
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    _ensure_access_logs_table()
    username_filter = str(username or "").strip()
    conn = _db_connect()
    try:
        if username_filter:
            rows = conn.execute(
                """
                SELECT id, user_id, username, ip_address, created_at
                FROM access_logs
                WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (username_filter, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, username, ip_address, created_at
                FROM access_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
    finally:
        conn.close()
    return {"logs": [dict(row) for row in rows], "limit": int(limit), "username": username_filter}


@app.get("/api/admin/access_logs")
def admin_access_logs_legacy(
    limit: int = Query(200, ge=1, le=2000),
    username: str = Query("", max_length=256),
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    return admin_access_logs(limit=limit, username=username, current_user=current_user)


@app.get("/api/admin/db/table/{table_name}")
def admin_db_table_rows(
    table_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    table = _validate_admin_table_name(table_name)
    columns = _table_columns(table)
    conn = _db_connect()
    try:
        has_rowid = True
        try:
            rows = conn.execute(f"SELECT rowid AS _rowid, * FROM {table} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        except Exception:
            has_rowid = False
            rows = conn.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        total = int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
        serialized = [dict(row) for row in rows]
    finally:
        conn.close()
    return {"table": table, "columns": columns, "rows": serialized, "total": total, "limit": limit, "offset": offset, "has_rowid": has_rowid}


@app.post("/api/admin/db/table/{table_name}/insert")
def admin_db_insert_row(
    table_name: str,
    payload: AdminDbInsertRequest,
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    table = _validate_admin_table_name(table_name)
    values = dict(payload.values or {})
    values.pop("_rowid", None)
    if not values:
        raise HTTPException(status_code=400, detail="No values to insert.")
    valid_columns = {col["name"] for col in _table_columns(table)}
    columns = [str(k) for k in values.keys() if str(k) in valid_columns and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(k))]
    placeholders = ", ".join(["?"] * len(columns))
    cols_sql = ", ".join(columns)
    params = [values[col] for col in columns]
    if not columns:
        raise HTTPException(status_code=400, detail="No valid columns to insert.")
    conn = _db_connect()
    try:
        cursor = conn.execute(f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})", params)
        conn.commit()
        return {"inserted": True, "rowid": int(cursor.lastrowid)}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@app.put("/api/admin/db/table/{table_name}/update")
def admin_db_update_row(
    table_name: str,
    payload: AdminDbUpdateRequest,
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    table = _validate_admin_table_name(table_name)
    values = dict(payload.values or {})
    values.pop("_rowid", None)
    if not values:
        raise HTTPException(status_code=400, detail="No values to update.")
    valid_columns = {col["name"] for col in _table_columns(table)}
    safe_items = [(str(col), values[col]) for col in values.keys() if str(col) in valid_columns and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(col))]
    if not safe_items:
        raise HTTPException(status_code=400, detail="No valid columns to update.")
    assignments = ", ".join([f"{col} = ?" for col, _ in safe_items])
    params = [val for _, val in safe_items] + [int(payload.rowid)]
    conn = _db_connect()
    try:
        cursor = conn.execute(f"UPDATE {table} SET {assignments} WHERE rowid = ?", params)
        conn.commit()
        if cursor.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Row not found.")
        return {"updated": True, "rowcount": int(cursor.rowcount)}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@app.delete("/api/admin/db/table/{table_name}/delete")
def admin_db_delete_row(
    table_name: str,
    payload: AdminDbDeleteRequest,
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    table = _validate_admin_table_name(table_name)
    conn = _db_connect()
    try:
        cursor = conn.execute(f"DELETE FROM {table} WHERE rowid = ?", (int(payload.rowid),))
        conn.commit()
        if cursor.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Row not found.")
        return {"deleted": True, "rowcount": int(cursor.rowcount)}
    except sqlite3.Error as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        conn.close()


@app.get("/api/admin/backups/config")
def admin_get_backup_config(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    return _read_backup_schedule()


@app.get("/api/admin/backup/config")
def admin_get_backup_config_legacy(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    return _read_backup_schedule()


@app.post("/api/admin/backups/config")
def admin_save_backup_config(
    payload: BackupConfigRequest,
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    saved = _save_backup_schedule(payload)
    return {"saved": True, "config": saved}


@app.post("/api/admin/backup/config")
def admin_save_backup_config_legacy(
    payload: BackupConfigRequest,
    current_user: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    saved = _save_backup_schedule(payload)
    return {"saved": True, "config": saved}


@app.post("/api/admin/backups/run-now")
def admin_run_backup_now(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    result = _run_backup_now(manual=True)
    return {"ok": True, "result": result}


@app.post("/api/admin/backup/run-now")
def admin_run_backup_now_legacy(current_user: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    result = _run_backup_now(manual=True)
    return {"ok": True, "result": result}


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}
