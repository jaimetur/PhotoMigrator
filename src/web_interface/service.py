"""
PhotoMigrator cloud service: migrations and Takeout processing run on the server for remote users.

A task goes through these states:
    draft -> analyzing -> quoted -> (awaiting_payment) -> queued -> preparing -> running -> completed
    process_takeout: ... -> running -> packaging -> (awaiting_download_payment) -> ready -> expired
    any state -> failed / canceled / rejected

* Data and credentials of a task live only in its own temporary folder (<work dir>/<task id>): the uploaded or
  imported Takeout files, the files the command line creates and an encrypted credentials file whose key is in
  the same folder. The folder is deleted when the task ends or is deleted, so the credentials can no longer be read;
  the folder is outside the database and its backups.
* Billing (Stripe) applies only when the service is enabled with a Stripe key, and never to administrators.
  A self-hosted installation without Stripe runs every task for free.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from html import escape as _esc
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from . import mailer
from . import service_probes as probes
from . import service_remote as remote
from . import service_stripe as stripe

LOGGER = logging.getLogger("PhotoMigrator.web_interface.service")

SETTINGS_KEY = "service"
WORK_DIR_NAME = ".service-work"
DEFAULT_WORK_DIR = Path(os.environ.get("PHOTOMIGRATOR_SERVICE_WORK_DIR", f"/app/data/{WORK_DIR_NAME}"))
SECRETS_DIR = ".secrets"
INPUT_DIR = "input"
DOWNLOADS_DIR = "downloads"
LOGS_DIR = "logs"
PART_MAX_BYTES = 50 * 1000 ** 3
UPLOAD_CHUNK_MAX_BYTES = 128 * 1024 * 1024
BYTES_PER_SECOND_DEFAULT = 15 * 1000 ** 2
WORKER_INTERVAL_SECONDS = 10
DISK_CHECK_INTERVAL_SECONDS = 600
TERMS_VERSION = "2026-11-25"

KINDS = ("takeout_to_cloud", "process_takeout", "cloud_to_cloud")
TAKEOUT_TYPES = ("google", "icloud")
INPUT_MODES = ("upload", "dropbox", "onedrive")
# Space needed on disk for each GB of input (archives + extracted files + processed output).
DISK_FACTORS = {"takeout_to_cloud": 3.0, "process_takeout": 3.0, "cloud_to_cloud": 1.5}
LABELS = {
    "immich": "Immich Photos",
    "synology": "Synology Photos",
    "nextcloud": "NextCloud Photos",
    "google-photos": "Google Photos",
    "google": "Google Takeout",
    "icloud": "iCloud Takeout",
    "download": "Download",
}
ACTIVE_STATES = {"preparing", "running", "packaging"}
PRE_RUN_STATES = {"draft", "analyzing", "quoted", "awaiting_payment", "queued", "rejected"}
FINAL_STATES = {"completed", "failed", "canceled", "expired", "rejected"}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "price_min_cents": 500,
    "price_per_gb_cents": 5,
    "currency": "eur",
    "max_task_bytes": 10 * 1000 ** 4,
    "concurrent_tasks": 1,
    "download_mbps": 100,
    "download_days": 7,
    "quote_days": 7,
    "idle_days": 7,
    "automatic_tax": False,
    "operator_name": "",
    "contact_email": "",
    "stripe_secret_key_encrypted": "",
    "stripe_webhook_secret_encrypted": "",
    "dropbox_app_key": "",
    "dropbox_app_secret_encrypted": "",
    "onedrive_client_id": "",
    "onedrive_client_secret_encrypted": "",
}
ENV_OVERRIDES = {
    "stripe_secret_key": "PHOTOMIGRATOR_STRIPE_SECRET_KEY",
    "stripe_webhook_secret": "PHOTOMIGRATOR_STRIPE_WEBHOOK_SECRET",
    "dropbox_app_key": "PHOTOMIGRATOR_DROPBOX_APP_KEY",
    "dropbox_app_secret": "PHOTOMIGRATOR_DROPBOX_APP_SECRET",
    "onedrive_client_id": "PHOTOMIGRATOR_ONEDRIVE_CLIENT_ID",
    "onedrive_client_secret": "PHOTOMIGRATOR_ONEDRIVE_CLIENT_SECRET",
}

# Texts of the service emails, for the translation catalogs (tools/UpdateTranslationTemplate.py).
EMAIL_TEXTS = [
    "Your PhotoMigrator quote", "Your quote is ready",
    "We checked your task <b>{0}</b>: {1} of photos and videos.",
    "Price: <b>{0}</b> (VAT included).", "Price: <b>{0}</b>. This task is free for your account.",
    "Estimated start: {0}. Estimated duration: {1}.",
    "The quote is valid for {0} days. After that the task and its data are deleted.",
    "Review and pay", "Review the task",
    "Payment received", "Your task is in the queue",
    "We received your payment of <b>{0}</b>. Your task <b>{1}</b> is number {2} in the queue.",
    "Your task <b>{0}</b> is number {1} in the queue.",
    "Your task has started", "Your task <b>{0}</b> has started. You can follow it in Activity.",
    "Your migration is complete",
    "Your task <b>{0}</b> finished successfully: {1} of photos and videos were moved.",
    "The data and credentials of the task have been deleted from our server.",
    "Your processed Takeout is ready",
    "Your task <b>{0}</b> finished successfully. The result takes {1}.",
    "Pay <b>{0}</b> to download it. You have {1} days; after that the result is deleted.",
    "You can download it until {0}. After that it is deleted from our server.",
    "Pay and download", "Download",
    "Your task could not be completed", "Your task <b>{0}</b> failed: {1}",
    "We refunded the full amount of <b>{0}</b>. It reaches your card in 5 to 10 days.",
    "You have not been charged.",
    "Your download expires soon",
    "The result of your task <b>{0}</b> is deleted on {1}. Download it before then.",
    "Your task data has been deleted",
    "The data and credentials of your task <b>{0}</b> were deleted from our server on {1}.",
    "Your task was canceled", "Your task <b>{0}</b> was canceled and its data deleted.",
    "{0} hours", "{0} days",
]


class ServiceDeps:
    """Functions of the Web Interface that the service uses (set by configure())."""

    db_connect: Callable[[], sqlite3.Connection]
    get_setting: Callable[[str, Any], Any]
    set_setting: Callable[[str, Any], None]
    encrypt: Callable[[str], str]
    decrypt: Callable[[str], str]
    secret: str
    public_base_url: Callable[[Optional[Request]], str]
    get_user_config_values: Callable[[Dict[str, Any]], Dict[str, Dict[str, str]]]
    get_user_by_session: Callable[[Optional[str]], Optional[Dict[str, Any]]]
    launch_job: Callable[..., str]
    job_state: Callable[[str], Dict[str, Any]]
    stop_job: Callable[[str], None]
    cli_command: Callable[[], List[str]]


DEPS = ServiceDeps()
STATE_LOCK = threading.RLock()
_WORKER_STARTED = False
_WORKER_STOP = threading.Event()
_THREADS: Dict[str, threading.Thread] = {}
_LAST_DISK_CHECK: Dict[str, float] = {}


def configure(**kwargs: Any) -> None:
    for key, value in kwargs.items():
        setattr(DEPS, key, value)


# ======================================================================================================================
# Settings
# ======================================================================================================================
def load_settings() -> Dict[str, Any]:
    stored = DEPS.get_setting(SETTINGS_KEY, {}) or {}
    values = dict(DEFAULT_SETTINGS)
    if isinstance(stored, dict):
        values.update({key: stored[key] for key in stored if key in DEFAULT_SETTINGS})
    env_enabled = str(os.environ.get("PHOTOMIGRATOR_SERVICE_ENABLED", "")).strip().lower()
    if env_enabled in {"1", "true", "yes", "on"}:
        values["enabled"] = True
    return values


def secret_value(settings: Dict[str, Any], name: str) -> str:
    """A credential of the service: environment variable first, then the value saved in the Administration Panel."""
    env_name = ENV_OVERRIDES.get(name, "")
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    if f"{name}_encrypted" in settings:
        encrypted = str(settings.get(f"{name}_encrypted") or "")
        return DEPS.decrypt(encrypted) if encrypted else ""
    return str(settings.get(name) or "").strip()


def billing_active(settings: Optional[Dict[str, Any]] = None) -> bool:
    settings = settings or load_settings()
    return bool(settings.get("enabled")) and bool(secret_value(settings, "stripe_secret_key"))


def billing_applies(user: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> bool:
    return billing_active(settings) and str(user.get("role") or "").lower() != "admin"


def work_root() -> Path:
    return DEFAULT_WORK_DIR


def compute_price_cents(size_bytes: int, settings: Optional[Dict[str, Any]] = None) -> int:
    settings = settings or load_settings()
    gigabytes = max(0, int(size_bytes)) / 1000 ** 3
    return max(int(settings["price_min_cents"]), int(math.ceil(gigabytes * float(settings["price_per_gb_cents"]))))


# ======================================================================================================================
# Formatting
# ======================================================================================================================
def format_bytes(size: int) -> str:
    value = float(max(0, int(size or 0)))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit in ("B", "KB") else f"{value:.1f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"


def format_price(cents: int, currency: str = "eur") -> str:
    symbol = {"eur": "€", "usd": "$", "gbp": "£"}.get(str(currency).lower(), str(currency).upper())
    return f"{int(cents) / 100:.2f} {symbol}"


def format_duration(seconds: float) -> str:
    hours = max(1, int(math.ceil(float(seconds) / 3600)))
    return f"{hours} hours" if hours < 48 else f"{int(math.ceil(hours / 24))} days"


def format_when(iso_value: str) -> str:
    try:
        moment = datetime.fromisoformat(str(iso_value))
    except ValueError:
        return str(iso_value or "")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: Optional[datetime] = None) -> str:
    return (moment or _now()).isoformat()


def _parse(iso_value: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(iso_value)) if iso_value else None
    except ValueError:
        return None


# ======================================================================================================================
# Database
# ======================================================================================================================
TASK_COLUMNS = {
    "id": "TEXT PRIMARY KEY",
    "user_id": "INTEGER NOT NULL",
    "kind": "TEXT NOT NULL",
    "takeout_type": "TEXT NOT NULL DEFAULT ''",
    "input_mode": "TEXT NOT NULL DEFAULT ''",
    "source_service": "TEXT NOT NULL DEFAULT ''",
    "target_service": "TEXT NOT NULL DEFAULT ''",
    "title": "TEXT NOT NULL DEFAULT ''",
    "status": "TEXT NOT NULL DEFAULT 'draft'",
    "status_detail": "TEXT NOT NULL DEFAULT ''",
    "error": "TEXT NOT NULL DEFAULT ''",
    "input_files_json": "TEXT NOT NULL DEFAULT '[]'",
    "remote_path": "TEXT NOT NULL DEFAULT ''",
    "oauth_nonce": "TEXT NOT NULL DEFAULT ''",
    "size_bytes": "INTEGER NOT NULL DEFAULT 0",
    "disk_bytes": "INTEGER NOT NULL DEFAULT 0",
    "result_bytes": "INTEGER NOT NULL DEFAULT 0",
    "price_cents": "INTEGER NOT NULL DEFAULT 0",
    "currency": "TEXT NOT NULL DEFAULT 'eur'",
    "billable": "INTEGER NOT NULL DEFAULT 0",
    "checkout_session_id": "TEXT NOT NULL DEFAULT ''",
    "payment_intent_id": "TEXT NOT NULL DEFAULT ''",
    "amount_paid_cents": "INTEGER NOT NULL DEFAULT 0",
    "paid_at": "TEXT NOT NULL DEFAULT ''",
    "refund_id": "TEXT NOT NULL DEFAULT ''",
    "refunded_at": "TEXT NOT NULL DEFAULT ''",
    "terms_version": "TEXT NOT NULL DEFAULT ''",
    "terms_accepted_at": "TEXT NOT NULL DEFAULT ''",
    "quoted_at": "TEXT NOT NULL DEFAULT ''",
    "queued_at": "TEXT NOT NULL DEFAULT ''",
    "started_at": "TEXT NOT NULL DEFAULT ''",
    "finished_at": "TEXT NOT NULL DEFAULT ''",
    "eta_start_at": "TEXT NOT NULL DEFAULT ''",
    "eta_seconds": "INTEGER NOT NULL DEFAULT 0",
    "job_id": "TEXT NOT NULL DEFAULT ''",
    "download_expires_at": "TEXT NOT NULL DEFAULT ''",
    "reminder_sent_at": "TEXT NOT NULL DEFAULT ''",
    "purged_at": "TEXT NOT NULL DEFAULT ''",
    "created_at": "TEXT NOT NULL",
    "updated_at": "TEXT NOT NULL",
}
PUBLIC_TASK_FIELDS = [
    "id", "kind", "takeout_type", "input_mode", "source_service", "target_service", "title", "status", "status_detail",
    "error", "remote_path", "size_bytes", "disk_bytes", "result_bytes", "price_cents", "currency", "billable",
    "amount_paid_cents", "paid_at", "refunded_at", "quoted_at", "queued_at", "started_at", "finished_at",
    "eta_start_at", "eta_seconds", "job_id", "download_expires_at", "purged_at", "created_at", "updated_at",
]


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    columns_sql = ",\n".join(f"{name} {sql}" for name, sql in TASK_COLUMNS.items())
    cur.execute(f"CREATE TABLE IF NOT EXISTS service_tasks (\n{columns_sql}\n)")
    existing = {str(row[1]) for row in cur.execute("PRAGMA table_info(service_tasks)").fetchall()}
    for name, sql in TASK_COLUMNS.items():
        if name not in existing:
            default_sql = sql.replace("PRIMARY KEY", "").replace("NOT NULL", "")
            if "DEFAULT" not in default_sql:
                default_sql += " DEFAULT ''"
            cur.execute(f"ALTER TABLE service_tasks ADD COLUMN {name} {default_sql}")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_service_tasks_user ON service_tasks(user_id, created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_service_tasks_status ON service_tasks(status)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS service_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            event TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT ''
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_service_events_task ON service_events(task_id, id)")
    conn.commit()


def _row_to_task(row: sqlite3.Row) -> Dict[str, Any]:
    task = {key: row[key] for key in row.keys()}
    try:
        task["input_files"] = json.loads(task.get("input_files_json") or "[]")
    except ValueError:
        task["input_files"] = []
    return task


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = DEPS.db_connect()
    try:
        row = conn.execute("SELECT * FROM service_tasks WHERE id = ?", (str(task_id),)).fetchone()
    finally:
        conn.close()
    return _row_to_task(row) if row else None


def list_tasks(user_id: Optional[int] = None, statuses: Optional[set] = None, limit: int = 500) -> List[Dict[str, Any]]:
    conn = DEPS.db_connect()
    try:
        query = "SELECT * FROM service_tasks"
        params: List[Any] = []
        where = []
        if user_id is not None:
            where.append("user_id = ?")
            params.append(int(user_id))
        if statuses:
            where.append(f"status IN ({','.join('?' * len(statuses))})")
            params.extend(sorted(statuses))
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [_row_to_task(row) for row in rows]


def update_task(task_id: str, **fields: Any) -> Dict[str, Any]:
    if "input_files" in fields:
        fields["input_files_json"] = json.dumps(fields.pop("input_files"))
    fields["updated_at"] = _iso()
    unknown = [key for key in fields if key not in TASK_COLUMNS]
    if unknown:
        raise ValueError(f"Unknown task fields: {unknown}")
    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn = DEPS.db_connect()
    try:
        conn.execute(f"UPDATE service_tasks SET {assignments} WHERE id = ?", [*fields.values(), str(task_id)])
        conn.commit()
    finally:
        conn.close()
    task = get_task(task_id)
    if task is None:
        raise KeyError(task_id)
    return task


def record_event(task_id: str, event: str, details: str = "") -> None:
    conn = DEPS.db_connect()
    try:
        conn.execute("INSERT INTO service_events (task_id, created_at, event, details) VALUES (?, ?, ?, ?)",
                     (str(task_id), _iso(), str(event), str(details)[:1000]))
        conn.commit()
    finally:
        conn.close()


def task_events(task_id: str) -> List[Dict[str, Any]]:
    conn = DEPS.db_connect()
    try:
        rows = conn.execute("SELECT created_at, event, details FROM service_events WHERE task_id = ? ORDER BY id", (str(task_id),)).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def _user(user_id: int) -> Dict[str, Any]:
    conn = DEPS.db_connect()
    try:
        row = conn.execute("SELECT id, username, email, role, lang FROM users WHERE id = ?", (int(user_id),)).fetchone()
    except sqlite3.OperationalError:
        row = conn.execute("SELECT id, username, email, role FROM users WHERE id = ?", (int(user_id),)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else {"id": user_id, "username": "", "email": "", "role": "user"}


# ======================================================================================================================
# Task folder, encrypted credentials and cleanup
# ======================================================================================================================
def task_dir(task_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", str(task_id)):
        raise ValueError("Invalid task id.")
    return work_root() / str(task_id)


def _private_mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def ensure_task_dir(task_id: str) -> Path:
    root = _private_mkdir(work_root())
    folder = _private_mkdir(root / task_id)
    _private_mkdir(folder / SECRETS_DIR)
    _private_mkdir(folder / INPUT_DIR)
    return folder


def _keystream_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        stream.extend(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(a ^ b for a, b in zip(data, stream))


def save_secrets(task_id: str, payload: Dict[str, Any]) -> None:
    """Encrypt the credentials of a task with a key that exists only in the task folder."""
    folder = ensure_task_dir(task_id) / SECRETS_DIR
    key_file = folder / "task.key"
    if not key_file.exists():
        key_file.write_bytes(secrets.token_bytes(32))
        os.chmod(key_file, 0o600)
    key = key_file.read_bytes()
    nonce = secrets.token_bytes(16)
    cipher = _keystream_xor(key, nonce, json.dumps(payload).encode("utf-8"))
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    target = folder / "credentials.enc"
    target.write_bytes(base64.b64encode(nonce + cipher + tag))
    os.chmod(target, 0o600)


def load_secrets(task_id: str) -> Dict[str, Any]:
    folder = task_dir(task_id) / SECRETS_DIR
    try:
        key = (folder / "task.key").read_bytes()
        blob = base64.b64decode((folder / "credentials.enc").read_bytes())
    except (OSError, ValueError):
        return {}
    nonce, cipher, tag = blob[:16], blob[16:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(key, nonce + cipher, hashlib.sha256).digest()):
        return {}
    return json.loads(_keystream_xor(key, nonce, cipher).decode("utf-8"))


def update_secrets(task_id: str, **values: Any) -> None:
    current = load_secrets(task_id)
    current.update(values)
    save_secrets(task_id, current)


def purge_task(task_id: str, reason: str) -> None:
    """Delete the task folder: data, generated files, logs and the encrypted credentials with their key."""
    folder = task_dir(task_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    if folder.exists():
        LOGGER.warning("Service task %s: the folder could not be deleted completely.", task_id)
        record_event(task_id, "purge_incomplete", reason)
        return
    task = get_task(task_id)
    if task and not task.get("purged_at"):
        update_task(task_id, purged_at=_iso())
        record_event(task_id, "data_deleted", reason)


def folder_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total


def free_disk_bytes() -> int:
    root = work_root()
    probe = root if root.exists() else root.parent
    try:
        return int(shutil.disk_usage(probe).free)
    except OSError:
        return 0


# ======================================================================================================================
# Throughput and queue estimates
# ======================================================================================================================
def throughput_bytes_per_second() -> float:
    finished = [task for task in list_tasks(statuses={"completed", "ready", "expired", "awaiting_download_payment"}, limit=20)
                if task.get("started_at") and task.get("finished_at") and int(task.get("size_bytes") or 0) > 0]
    rates = []
    for task in finished:
        started, ended = _parse(task["started_at"]), _parse(task["finished_at"])
        if started and ended and ended > started:
            rates.append(int(task["size_bytes"]) / (ended - started).total_seconds())
    return sum(rates) / len(rates) if rates else float(BYTES_PER_SECOND_DEFAULT)


def queue_estimate(size_bytes: int, exclude_task_id: str = "") -> Tuple[int, datetime, int]:
    """(position in the queue, estimated start, estimated duration in seconds) for a new task."""
    rate = throughput_bytes_per_second()
    settings = load_settings()
    slots = max(1, int(settings.get("concurrent_tasks") or 1))
    ahead = [task for task in list_tasks(statuses={"queued"} | ACTIVE_STATES) if task["id"] != exclude_task_id]
    pending_seconds = 0.0
    for task in ahead:
        total = int(task.get("size_bytes") or 0) / rate
        started = _parse(task.get("started_at"))
        if task["status"] in ACTIVE_STATES and started:
            total = max(0.0, total - (_now() - started).total_seconds())
        pending_seconds += total
    position = len([task for task in ahead if task["status"] == "queued"]) + 1
    start = _now() + timedelta(seconds=pending_seconds / slots)
    return position, start, int(max(1800, size_bytes / rate))


# ======================================================================================================================
# Emails
# ======================================================================================================================
def _task_label(task: Dict[str, Any]) -> str:
    if task["kind"] == "process_takeout":
        return f"{LABELS.get(task['takeout_type'], 'Takeout')} → {LABELS['download']}"
    source = LABELS.get(task["takeout_type"]) if task["kind"] == "takeout_to_cloud" else LABELS.get(task["source_service"])
    return f"{source} → {LABELS.get(task['target_service'], task['target_service'])}"


def _send(task: Dict[str, Any], subject: str, title: str, paragraphs: List[str], link: Optional[Tuple[str, str]] = None) -> None:
    user = _user(int(task["user_id"]))
    email = str(user.get("email") or "").strip()
    if not email:
        return
    greeting = f"Hi {_esc(str(user.get('username') or 'there'))},"
    mailer.send_later([email], subject, mailer.page(title, [greeting, *paragraphs], link=link))


def _task_link(task: Dict[str, Any], base_url: str = "") -> str:
    base = base_url or DEPS.public_base_url(None)
    return f"{base}/service?task={task['id']}"


def email_quote(task: Dict[str, Any]) -> None:
    settings = load_settings()
    paragraphs = [f"We checked your task <b>{_esc(_task_label(task))}</b>: {format_bytes(task['size_bytes'])} of photos and videos."]
    if int(task.get("billable") or 0):
        paragraphs.append(f"Price: <b>{format_price(task['price_cents'], task['currency'])}</b> (VAT included).")
    else:
        paragraphs.append(f"Price: <b>{format_price(task['price_cents'], task['currency'])}</b>. This task is free for your account.")
    paragraphs.append(f"Estimated start: {format_when(task['eta_start_at'])}. Estimated duration: {format_duration(task['eta_seconds'])}.")
    paragraphs.append(f"The quote is valid for {int(settings['quote_days'])} days. After that the task and its data are deleted.")
    _send(task, "Your PhotoMigrator quote", "Your quote is ready", paragraphs,
          link=("Review and pay" if int(task.get("billable") or 0) else "Review the task", _task_link(task)))


def email_queued(task: Dict[str, Any], position: int) -> None:
    if int(task.get("amount_paid_cents") or 0):
        text = (f"We received your payment of <b>{format_price(task['amount_paid_cents'], task['currency'])}</b>. "
                f"Your task <b>{_esc(_task_label(task))}</b> is number {position} in the queue.")
        subject = "Payment received"
    else:
        text = f"Your task <b>{_esc(_task_label(task))}</b> is number {position} in the queue."
        subject = "Your task is in the queue"
    _send(task, subject, "Your task is in the queue",
          [text, f"Estimated start: {format_when(task['eta_start_at'])}. Estimated duration: {format_duration(task['eta_seconds'])}."],
          link=("Review the task", _task_link(task)))


def email_started(task: Dict[str, Any]) -> None:
    _send(task, "Your task has started", "Your task has started",
          [f"Your task <b>{_esc(_task_label(task))}</b> has started. You can follow it in Activity."],
          link=("Review the task", _task_link(task)))


def email_completed(task: Dict[str, Any]) -> None:
    _send(task, "Your migration is complete", "Your migration is complete", [
        f"Your task <b>{_esc(_task_label(task))}</b> finished successfully: {format_bytes(task['size_bytes'])} of photos and videos were moved.",
        "The data and credentials of the task have been deleted from our server.",
    ])


def email_download_ready(task: Dict[str, Any]) -> None:
    paragraphs = [f"Your task <b>{_esc(_task_label(task))}</b> finished successfully. The result takes {format_bytes(task['result_bytes'])}."]
    if task["status"] == "awaiting_download_payment":
        paragraphs.append(f"Pay <b>{format_price(task['price_cents'], task['currency'])}</b> to download it. "
                          f"You have {int(load_settings()['download_days'])} days; after that the result is deleted.")
        link = ("Pay and download", _task_link(task))
    else:
        paragraphs.append(f"You can download it until {format_when(task['download_expires_at'])}. After that it is deleted from our server.")
        link = ("Download", _task_link(task))
    _send(task, "Your processed Takeout is ready", "Your processed Takeout is ready", paragraphs, link=link)


def email_failed(task: Dict[str, Any]) -> None:
    paragraphs = [f"Your task <b>{_esc(_task_label(task))}</b> failed: {_esc(task.get('error') or 'unknown error')}"]
    if task.get("refunded_at"):
        paragraphs.append(f"We refunded the full amount of <b>{format_price(task['amount_paid_cents'], task['currency'])}</b>. It reaches your card in 5 to 10 days.")
    else:
        paragraphs.append("You have not been charged.")
    paragraphs.append("The data and credentials of the task have been deleted from our server.")
    _send(task, "Your task could not be completed", "Your task could not be completed", paragraphs)


def email_canceled(task: Dict[str, Any]) -> None:
    paragraphs = [f"Your task <b>{_esc(_task_label(task))}</b> was canceled and its data deleted."]
    if task.get("refunded_at"):
        paragraphs.append(f"We refunded the full amount of <b>{format_price(task['amount_paid_cents'], task['currency'])}</b>. It reaches your card in 5 to 10 days.")
    _send(task, "Your task was canceled", "Your task was canceled", paragraphs)


def email_expiry_reminder(task: Dict[str, Any]) -> None:
    _send(task, "Your download expires soon", "Your download expires soon",
          [f"The result of your task <b>{_esc(_task_label(task))}</b> is deleted on {format_when(task['download_expires_at'])}. Download it before then."],
          link=("Download", _task_link(task)))


def email_deleted(task: Dict[str, Any]) -> None:
    _send(task, "Your task data has been deleted", "Your task data has been deleted",
          [f"The data and credentials of your task <b>{_esc(_task_label(task))}</b> were deleted from our server on {format_when(task.get('purged_at') or _iso())}."])


# ======================================================================================================================
# Payments
# ======================================================================================================================
def _stripe_key() -> str:
    return secret_value(load_settings(), "stripe_secret_key")


def start_checkout(task: Dict[str, Any], purpose: str, base_url: str) -> str:
    settings = load_settings()
    user = _user(int(task["user_id"]))
    session = stripe.create_checkout_session(
        secret_value(settings, "stripe_secret_key"),
        task_id=task["id"],
        purpose=purpose,
        amount_cents=int(task["price_cents"]),
        currency=str(task.get("currency") or settings["currency"]),
        description=f"PhotoMigrator · {_task_label(task)} · {format_bytes(task['size_bytes'])}",
        customer_email=str(user.get("email") or ""),
        success_url=f"{base_url}/service?task={task['id']}&checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/service?task={task['id']}&checkout=canceled",
        automatic_tax=bool(settings.get("automatic_tax")),
        locale=str(user.get("lang") or "auto") or "auto",
    )
    update_task(task["id"], checkout_session_id=str(session.get("id") or ""),
                status="awaiting_payment" if purpose == "migration" else task["status"])
    record_event(task["id"], "checkout_created", purpose)
    return str(session.get("url") or "")


def mark_paid(task_id: str, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Apply a paid Checkout Session (from the webhook or the return page). Safe to call more than once."""
    with STATE_LOCK:
        task = get_task(task_id)
        if not task or task.get("paid_at"):
            return task
        if str(session.get("payment_status") or "") != "paid":
            return task
        metadata = session.get("metadata") or {}
        if str(metadata.get("task_id") or session.get("client_reference_id") or "") != task_id:
            return task
        purpose = str(metadata.get("purpose") or "migration")
        task = update_task(
            task_id,
            paid_at=_iso(),
            amount_paid_cents=int(session.get("amount_total") or task["price_cents"]),
            payment_intent_id=str(session.get("payment_intent") or ""),
            checkout_session_id=str(session.get("id") or task.get("checkout_session_id") or ""),
        )
        record_event(task_id, "paid", f"{purpose} · {format_price(task['amount_paid_cents'], task['currency'])}")
        if task.get("purged_at") or task["status"] in {"canceled", "failed", "expired"}:
            # Paid after the task was canceled or expired: give the money back.
            refund(task, "Paid after the task ended")
            return get_task(task_id)
        if purpose == "download":
            days = int(load_settings()["download_days"])
            expires = max(_parse(task.get("download_expires_at")) or _now(), _now() + timedelta(days=days))
            task = update_task(task_id, status="ready", download_expires_at=_iso(expires), reminder_sent_at="")
            email_download_ready(task)
        else:
            enqueue(task)
        return get_task(task_id)


def refund(task: Dict[str, Any], reason: str) -> Dict[str, Any]:
    if not task.get("payment_intent_id") or task.get("refunded_at"):
        return task
    try:
        result = stripe.refund_payment(_stripe_key(), task["payment_intent_id"], task["id"])
    except stripe.StripeError as exc:
        record_event(task["id"], "refund_failed", str(exc))
        LOGGER.error("Service task %s: refund failed: %s", task["id"], exc)
        return task
    record_event(task["id"], "refunded", reason)
    return update_task(task["id"], refund_id=str(result.get("id") or ""), refunded_at=_iso())


def handle_webhook_event(event: Dict[str, Any]) -> None:
    kind = str(event.get("type") or "")
    obj = ((event.get("data") or {}).get("object")) or {}
    if str((obj.get("metadata") or {}).get("service") or "") != stripe.SERVICE_TAG:
        return  # Event of another business sharing the Stripe account.
    if kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        task_id = str((obj.get("metadata") or {}).get("task_id") or obj.get("client_reference_id") or "")
        if task_id:
            mark_paid(task_id, obj)
    elif kind == "charge.refunded":
        task_id = str((obj.get("metadata") or {}).get("task_id") or "")
        task = get_task(task_id) if task_id else None
        if task and not task.get("refunded_at"):
            update_task(task_id, refunded_at=_iso())
            record_event(task_id, "refunded", "Refund made in Stripe")


# ======================================================================================================================
# Lifecycle
# ======================================================================================================================
def create_task(user: Dict[str, Any], kind: str, takeout_type: str, input_mode: str, source_service: str,
                target_service: str, source_credentials: Dict[str, str], target_credentials: Dict[str, str]) -> Dict[str, Any]:
    task_id = uuid.uuid4().hex
    now = _iso()
    settings = load_settings()
    task = {
        "id": task_id, "user_id": int(user["id"]), "kind": kind, "takeout_type": takeout_type, "input_mode": input_mode,
        "source_service": source_service, "target_service": target_service, "status": "draft",
        "currency": str(settings["currency"]), "billable": 1 if billing_applies(user, settings) else 0,
        "terms_version": TERMS_VERSION, "terms_accepted_at": now, "created_at": now, "updated_at": now,
    }
    task["title"] = _task_label(task)
    conn = DEPS.db_connect()
    try:
        columns = ", ".join(task)
        conn.execute(f"INSERT INTO service_tasks ({columns}) VALUES ({', '.join('?' * len(task))})", list(task.values()))
        conn.commit()
    finally:
        conn.close()
    ensure_task_dir(task_id)
    save_secrets(task_id, {"source": source_credentials, "target": target_credentials})
    record_event(task_id, "created", f"{kind} · terms {TERMS_VERSION} accepted")
    return get_task(task_id) or task


def max_input_bytes(kind: str) -> int:
    return int(int(load_settings()["max_task_bytes"]) / DISK_FACTORS[kind])


def analyze(task_id: str) -> None:
    """Measure the data, test the destination and send the quote (runs in a background thread)."""
    task = get_task(task_id)
    if not task:
        return
    try:
        secrets_payload = load_secrets(task_id)
        if task["kind"] == "cloud_to_cloud":
            size = probes.check_source(task["source_service"], secrets_payload.get("source") or {})
        elif task["input_mode"] == "upload":
            files = task["input_files"]
            if not files or not all(item.get("complete") for item in files):
                raise probes.ProbeError("Upload every Takeout file before continuing.")
            size = sum(int(item.get("size") or 0) for item in files)
        else:
            if not task.get("remote_path"):
                raise probes.ProbeError("Choose the folder with the Takeout files.")
            storage = _remote_storage(task)
            archives = storage.archives_in(task["remote_path"])
            if not archives:
                raise probes.ProbeError("The chosen folder has no Takeout files (.zip or .tgz).")
            update_task(task_id, input_files=[{"name": a["name"], "path": a["path"], "id": a.get("id", ""), "size": a["size"]} for a in archives])
            size = sum(int(a["size"]) for a in archives)
        if size <= 0:
            raise probes.ProbeError("No photos or videos were found.")
        disk = int(size * DISK_FACTORS[task["kind"]])
        settings = load_settings()
        if disk > int(settings["max_task_bytes"]):
            update_task(task_id, status="rejected", size_bytes=size, disk_bytes=disk,
                        error=f"The task needs {format_bytes(disk)} of space and the limit is {format_bytes(settings['max_task_bytes'])}.")
            record_event(task_id, "rejected", "too large")
            purge_task(task_id, "Task too large")
            return
        if task["target_service"]:
            probes.check_target(task["target_service"], secrets_payload.get("target") or {})
            record_event(task_id, "target_checked", task["target_service"])
        _position, start, duration = queue_estimate(size, task_id)
        task = update_task(task_id, status="quoted", size_bytes=size, disk_bytes=disk, error="", status_detail="",
                           price_cents=compute_price_cents(size, settings), quoted_at=_iso(),
                           eta_start_at=_iso(start), eta_seconds=duration)
        record_event(task_id, "quoted", f"{format_bytes(size)} · {format_price(task['price_cents'], task['currency'])}")
        email_quote(task)
    except (probes.ProbeError, remote.RemoteError) as exc:
        update_task(task_id, status="draft", error=str(exc), status_detail="")
        record_event(task_id, "analysis_failed", str(exc))
    except Exception as exc:  # never leave a task in "analyzing"
        LOGGER.exception("Service task %s: analysis failed", task_id)
        update_task(task_id, status="draft", error=f"The check failed ({type(exc).__name__}). Try again.", status_detail="")


def start_analysis(task: Dict[str, Any]) -> Dict[str, Any]:
    with STATE_LOCK:
        if task["status"] not in {"draft", "quoted"}:
            raise HTTPException(status_code=409, detail="The task cannot be checked in its current state.")
        task = update_task(task["id"], status="analyzing", error="", status_detail="")
    _spawn(f"analyze-{task['id']}", analyze, task["id"])
    return task


def enqueue(task: Dict[str, Any]) -> Dict[str, Any]:
    position, start, duration = queue_estimate(int(task["size_bytes"]), task["id"])
    task = update_task(task["id"], status="queued", queued_at=_iso(), eta_start_at=_iso(start), eta_seconds=duration)
    record_event(task["id"], "queued", f"position {position}")
    email_queued(task, position)
    return task


def accept(task: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """The user accepts the quote: pay now (migrations) or queue it (Takeout processing is paid at the end)."""
    with STATE_LOCK:
        if task["status"] not in {"quoted", "awaiting_payment"}:
            raise HTTPException(status_code=409, detail="This task has no quote to accept.")
        quoted = _parse(task.get("quoted_at"))
        if quoted and _now() - quoted > timedelta(days=int(load_settings()["quote_days"])):
            raise HTTPException(status_code=409, detail="The quote expired. Check the task again.")
        if int(task.get("billable") or 0) and task["kind"] != "process_takeout":
            try:
                return {"checkout_url": start_checkout(task, "migration", base_url)}
            except stripe.StripeError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"task": public_task(enqueue(task))}


def cancel(task: Dict[str, Any], by_admin: bool = False, refund_running: bool = False) -> Dict[str, Any]:
    """Cancel or delete a task. Paid tasks are refunded in full only when they had not started."""
    with STATE_LOCK:
        task = get_task(task["id"]) or task
        status = task["status"]
        if status in ACTIVE_STATES:
            if task.get("job_id"):
                try:
                    DEPS.stop_job(task["job_id"])
                except Exception:
                    pass
            if refund_running:
                task = refund(task, "Canceled by an administrator")
        elif status in PRE_RUN_STATES:
            task = refund(task, "Canceled before it started")
        new_status = status if status in {"completed", "failed", "expired"} else "canceled"
        task = update_task(task["id"], status=new_status, finished_at=task.get("finished_at") or _iso(),
                           status_detail="", download_expires_at="" if new_status == "canceled" else task.get("download_expires_at", ""))
        record_event(task["id"], "canceled", "by an administrator" if by_admin else "by the user")
    purge_task(task["id"], "Task canceled or deleted")
    task = get_task(task["id"]) or task
    email_canceled(task)
    return task


def public_task(task: Dict[str, Any]) -> Dict[str, Any]:
    out = {key: task.get(key) for key in PUBLIC_TASK_FIELDS}
    out["input_files"] = [{"id": f.get("id", ""), "name": f.get("name", ""), "size": int(f.get("size") or 0),
                           "received": int(f.get("received") or 0), "complete": bool(f.get("complete"))}
                          for f in task.get("input_files") or []]
    out["label"] = _task_label(task)
    out["price"] = format_price(int(task.get("price_cents") or 0), str(task.get("currency") or "eur"))
    if task.get("status") == "queued":
        queued = sorted(list_tasks(statuses={"queued"}), key=lambda item: item.get("queued_at") or "")
        out["queue_position"] = next((index + 1 for index, item in enumerate(queued) if item["id"] == task["id"]), 0)
    return out


# ======================================================================================================================
# Running tasks
# ======================================================================================================================
def _spawn(name: str, target: Callable[..., None], *args: Any) -> None:
    thread = threading.Thread(target=target, args=args, name=f"service-{name}", daemon=True)
    _THREADS[name] = thread
    thread.start()


def _remote_storage(task: Dict[str, Any]) -> remote.RemoteStorage:
    settings = load_settings()
    provider = task["input_mode"]
    payload = load_secrets(task["id"]).get("remote") or {}
    if provider == "dropbox":
        client_id, client_secret = secret_value(settings, "dropbox_app_key"), secret_value(settings, "dropbox_app_secret")
    else:
        client_id, client_secret = secret_value(settings, "onedrive_client_id"), secret_value(settings, "onedrive_client_secret")
    if not payload.get("tokens"):
        raise remote.RemoteError("Connect the storage first.")
    return remote.RemoteStorage(provider, client_id, client_secret, payload["tokens"],
                                on_tokens_changed=lambda tokens: update_secrets(task["id"], remote={"provider": provider, "tokens": tokens}))


def _write_task_config(task: Dict[str, Any]) -> Path:
    """Config.ini with only the accounts of this task (account 1 = source or target, 2 = target of the same service)."""
    payload = load_secrets(task["id"])
    sections: Dict[str, Dict[str, str]] = {}
    endpoints = {}
    if task["kind"] == "cloud_to_cloud":
        endpoints["source"] = (task["source_service"], payload.get("source") or {}, 1)
    if task["target_service"]:
        same = task["kind"] == "cloud_to_cloud" and task["source_service"] == task["target_service"]
        endpoints["target"] = (task["target_service"], payload.get("target") or {}, 2 if same else 1)
    for _role, (service, values, account_id) in endpoints.items():
        section, keys = probes.config_lines(service, probes.validate_credentials(service, values), account_id)
        sections.setdefault(section, {}).update(keys)
    lines = ["# Temporary configuration of a PhotoMigrator service task. Deleted when the task ends."]
    for section, keys in sections.items():
        lines.append(f"\n[{section}]")
        lines.extend(f"{key} = {value}" for key, value in keys.items())
    path = task_dir(task["id"]) / SECRETS_DIR / "Config.ini"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def build_command(task: Dict[str, Any], config_path: Path) -> Tuple[List[str], str, Dict[str, Any]]:
    folder = task_dir(task["id"])
    input_dir = folder / INPUT_DIR
    common = [f"--configuration-file={config_path}", "--request-user-confirmation=false",
              f"--foldername-logs={folder / LOGS_DIR}"]
    if task["kind"] == "process_takeout":
        flag = "--google-takeout" if task["takeout_type"] == "google" else "--icloud-takeout"
        return [*DEPS.cli_command(), f"{flag}={input_dir}", *common], f"{task['takeout_type']}_takeout", {}
    same = task["kind"] == "cloud_to_cloud" and task["source_service"] == task["target_service"]
    source = f"{task['source_service']}-1" if task["kind"] == "cloud_to_cloud" else str(input_dir)
    target = f"{task['target_service']}-{2 if same else 1}"
    command = [*DEPS.cli_command(), f"--source={source}", f"--target={target}", "--dashboard=true", *common]
    return command, "automatic_migration", {"source": source, "target": target, "parallel_migration": True}


def run_task(task_id: str) -> None:
    """Download the remote files when needed and start the command line job."""
    task = get_task(task_id)
    if not task:
        return
    try:
        if task["input_mode"] in remote.PROVIDERS and task["kind"] != "cloud_to_cloud":
            storage = _remote_storage(task)
            input_dir = task_dir(task_id) / INPUT_DIR
            done = 0
            for index, entry in enumerate(task["input_files"], start=1):
                update_task(task_id, status_detail=f"Downloading {index}/{len(task['input_files'])}: {entry['name']}")
                storage.download(entry, input_dir / Path(entry["name"]).name,
                                 should_stop=lambda: (get_task(task_id) or {}).get("status") != "preparing")
                done += int(entry.get("size") or 0)
            update_secrets(task_id, remote={})  # the storage access is no longer needed
            record_event(task_id, "input_downloaded", format_bytes(done))
        config_path = _write_task_config(task)
        command, tab, dashboard = build_command(task, config_path)
        user = _user(int(task["user_id"]))
        env = {"PHOTOMIGRATOR_DOCKER_BASE_PATH": str(task_dir(task_id)), "PHOTOMIGRATOR_CONFIG_PATH": str(config_path)}
        display = " ".join(part if "configuration-file" not in part else "--configuration-file=<task configuration>" for part in command[1:])
        display = display.replace(str(task_dir(task_id)), "<task folder>")
        job_id = DEPS.launch_job(user=user, command=command, env=env, cwd=task_dir(task_id), tab=tab,
                                 dashboard_context=dashboard, display_command=display)
        with STATE_LOCK:
            current = get_task(task_id) or {}
            if current.get("status") != "preparing":
                DEPS.stop_job(job_id)
                return
            task = update_task(task_id, status="running", job_id=job_id, status_detail="")
        record_event(task_id, "started", tab)
        email_started(task)
    except Exception as exc:
        LOGGER.exception("Service task %s: start failed", task_id)
        fail_task(task_id, str(exc) if isinstance(exc, (remote.RemoteError, probes.ProbeError)) else f"The task could not start ({type(exc).__name__}).")


def fail_task(task_id: str, error: str) -> None:
    with STATE_LOCK:
        task = get_task(task_id)
        if not task or task["status"] in FINAL_STATES:
            return
        task = update_task(task_id, status="failed", error=error, finished_at=_iso(), status_detail="")
        record_event(task_id, "failed", error)
        task = refund(task, "The task failed")
    purge_task(task_id, "Task failed")
    email_failed(get_task(task_id) or task)


def _processed_folder(task_id: str) -> Optional[Path]:
    folder = task_dir(task_id)
    candidates = sorted(path for path in folder.glob(f"{INPUT_DIR}_processed_*") if path.is_dir())
    return candidates[-1] if candidates else None


def package_result(task_id: str) -> None:
    """Split the processed Takeout into ZIP parts of up to 50 GB, deleting each file once it is in a part."""
    folder = task_dir(task_id)
    try:
        processed = _processed_folder(task_id)
        if processed is None:
            raise RuntimeError("The processed folder was not found.")
        for path in folder.iterdir():
            if path.name not in {SECRETS_DIR, DOWNLOADS_DIR, LOGS_DIR} and path != processed:
                shutil.rmtree(path, ignore_errors=True) if path.is_dir() else path.unlink(missing_ok=True)
        downloads = _private_mkdir(folder / DOWNLOADS_DIR)
        files = sorted(p for p in processed.rglob("*") if p.is_file())
        part_index, part_size, archive = 0, 0, None
        for file_path in files:
            size = file_path.stat().st_size
            if archive is None or (part_size and part_size + size > PART_MAX_BYTES):
                if archive is not None:
                    archive.close()
                part_index += 1
                part_size = 0
                archive = zipfile.ZipFile(downloads / f"PhotoMigrator-{task_id[:8]}-part{part_index:03d}.zip", "w",
                                          compression=zipfile.ZIP_STORED, allowZip64=True)
            archive.write(file_path, arcname=str(file_path.relative_to(processed)))
            part_size += size
            file_path.unlink()
        if archive is not None:
            archive.close()
        shutil.rmtree(processed, ignore_errors=True)
        (folder / SECRETS_DIR / "Config.ini").unlink(missing_ok=True)
        result_bytes = folder_size(downloads)
        settings = load_settings()
        with STATE_LOCK:
            task = get_task(task_id) or {}
            if task.get("status") != "packaging":
                return
            expires = _now() + timedelta(days=int(settings["download_days"]))
            status = "awaiting_download_payment" if int(task.get("billable") or 0) and not task.get("paid_at") else "ready"
            task = update_task(task_id, status=status, result_bytes=result_bytes, finished_at=_iso(),
                               download_expires_at=_iso(expires), status_detail="")
        record_event(task_id, "result_ready", f"{part_index} part(s) · {format_bytes(result_bytes)}")
        email_download_ready(task)
    except Exception as exc:
        LOGGER.exception("Service task %s: packaging failed", task_id)
        fail_task(task_id, f"The result could not be prepared for download ({type(exc).__name__}).")


def _finish_running(task: Dict[str, Any]) -> None:
    state = DEPS.job_state(task["job_id"]) if task.get("job_id") else {"status": "missing"}
    status = str(state.get("status") or "missing")
    if status in {"running", "stopping"}:
        last = _LAST_DISK_CHECK.get(task["id"], 0.0)
        if time.monotonic() - last > DISK_CHECK_INTERVAL_SECONDS:
            _LAST_DISK_CHECK[task["id"]] = time.monotonic()
            used = folder_size(task_dir(task["id"]))
            limit = int(load_settings()["max_task_bytes"])
            if used > limit:
                DEPS.stop_job(task["job_id"])
                fail_task(task["id"], f"The task used more than {format_bytes(limit)} of space.")
        return
    (task_dir(task["id"]) / SECRETS_DIR / "Config.ini").unlink(missing_ok=True)
    if status == "success":
        if task["kind"] == "process_takeout":
            update_task(task["id"], status="packaging", status_detail="Preparing the download")
            _spawn(f"package-{task['id']}", package_result, task["id"])
        else:
            task = update_task(task["id"], status="completed", finished_at=_iso(), status_detail="")
            record_event(task["id"], "completed", format_bytes(task["size_bytes"]))
            purge_task(task["id"], "Task completed")
            email_completed(get_task(task["id"]) or task)
    elif status == "stopped":
        # Stopped from Activity by its owner: canceled once started, so it is not refunded.
        current = get_task(task["id"]) or {}
        if current.get("status") in ACTIVE_STATES:
            cancel(current)
    else:
        rc = state.get("return_code")
        fail_task(task["id"], "The server restarted while the task was running." if status == "missing"
                  else f"PhotoMigrator ended with an error (code {rc}). Check the log in Activity.")


def worker_tick() -> None:
    settings = load_settings()
    now = _now()
    # Running tasks: finished jobs and disk limit.
    for task in list_tasks(statuses={"running"}):
        try:
            _finish_running(task)
        except Exception:
            LOGGER.exception("Service task %s: check failed", task["id"])
    # Start queued tasks while there are free slots and enough disk.
    active = list_tasks(statuses=ACTIVE_STATES)
    slots = max(1, int(settings.get("concurrent_tasks") or 1)) - len(active)
    if slots > 0:
        reserved = sum(max(0, int(t.get("disk_bytes") or 0) - folder_size(task_dir(t["id"]))) for t in active)
        for task in sorted(list_tasks(statuses={"queued"}), key=lambda item: item.get("queued_at") or ""):
            if slots <= 0:
                break
            if free_disk_bytes() - reserved < int(task.get("disk_bytes") or 0):
                if task.get("status_detail") != "Waiting for disk space":
                    update_task(task["id"], status_detail="Waiting for disk space")
                break
            with STATE_LOCK:
                current = get_task(task["id"])
                if not current or current["status"] != "queued":
                    continue
                update_task(task["id"], status="preparing", started_at=_iso(), status_detail="Preparing")
            _spawn(f"run-{task['id']}", run_task, task["id"])
            reserved += int(task.get("disk_bytes") or 0)
            slots -= 1
    # Expirations and reminders.
    for task in list_tasks(statuses={"ready", "awaiting_download_payment"}):
        expires = _parse(task.get("download_expires_at"))
        if not expires:
            continue
        if now >= expires:
            update_task(task["id"], status="expired")
            record_event(task["id"], "expired", "download period ended")
            purge_task(task["id"], "Download period ended")
            email_deleted(get_task(task["id"]) or task)
        elif task["status"] == "ready" and not task.get("reminder_sent_at") and expires - now <= timedelta(days=2):
            update_task(task["id"], reminder_sent_at=_iso())
            email_expiry_reminder(task)
    quote_limit = timedelta(days=int(settings["quote_days"]))
    idle_limit = timedelta(days=int(settings["idle_days"]))
    for task in list_tasks(statuses={"quoted", "awaiting_payment", "draft"}):
        reference = _parse(task.get("quoted_at")) if task["status"] != "draft" else _parse(task.get("updated_at"))
        limit = quote_limit if task["status"] != "draft" else idle_limit
        if reference and now - reference > limit and not task.get("paid_at"):
            update_task(task["id"], status="expired", status_detail="")
            record_event(task["id"], "expired", "not accepted in time")
            purge_task(task["id"], "Quote or draft expired")


def recover_after_restart() -> None:
    """Jobs do not survive a restart: queue interrupted tasks again (their generated files are removed first)."""
    for task in list_tasks(statuses={"analyzing"}):
        update_task(task["id"], status="draft", error="The check was interrupted. Try again.")
    for task in list_tasks(statuses={"preparing", "running"}):
        if task.get("job_id") and DEPS.job_state(task["job_id"]).get("status") in {"running", "stopping"}:
            continue
        folder = task_dir(task["id"])
        if folder.exists():
            for path in folder.iterdir():
                if path.name not in {SECRETS_DIR, INPUT_DIR}:
                    shutil.rmtree(path, ignore_errors=True) if path.is_dir() else path.unlink(missing_ok=True)
        update_task(task["id"], status="queued", job_id="", status_detail="Restarting after a server restart")
        record_event(task["id"], "requeued", "server restart")
    for task in list_tasks(statuses={"packaging"}):
        fail_task(task["id"], "The server restarted while the download was being prepared.")


def _worker_loop() -> None:
    try:
        recover_after_restart()
    except Exception:
        LOGGER.exception("Service: recovery after restart failed")
    while not _WORKER_STOP.wait(WORKER_INTERVAL_SECONDS):
        try:
            if load_settings().get("enabled") or list_tasks(statuses={"queued"} | ACTIVE_STATES, limit=1):
                worker_tick()
        except Exception:
            LOGGER.exception("Service worker tick failed")


def start_worker() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    _WORKER_STARTED = True
    threading.Thread(target=_worker_loop, name="service-worker", daemon=True).start()


# ======================================================================================================================
# Uploads and downloads
# ======================================================================================================================
SAFE_NAME = re.compile(r"[^A-Za-z0-9._ ()+-]+")


def _clean_file_name(name: str) -> str:
    clean = SAFE_NAME.sub("_", Path(str(name or "")).name).strip(" .")
    if not clean or not remote.is_archive(clean):
        raise HTTPException(status_code=400, detail="Only Takeout archives can be uploaded (.zip, .tgz, .tar.gz or .tar).")
    return clean[:200]


class _Throttle:
    """Shared limit for every download (bytes per second)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.next_free = time.monotonic()

    def wait(self, size: int) -> None:
        mbps = int(load_settings().get("download_mbps") or 0)
        if mbps <= 0:
            return
        rate = mbps * 1000 * 1000 / 8
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_free)
            self.next_free = start + size / rate
            delay = start - now
        if delay > 0:
            time.sleep(delay)


THROTTLE = _Throttle()


def download_parts(task_id: str) -> List[Dict[str, Any]]:
    folder = task_dir(task_id) / DOWNLOADS_DIR
    if not folder.exists():
        return []
    return [{"name": path.name, "size": path.stat().st_size} for path in sorted(folder.glob("*.zip"))]


def download_token(task_id: str, name: str, expires_at: int) -> str:
    message = f"{task_id}:{name}:{expires_at}".encode("utf-8")
    return hmac.new(DEPS.secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _range(header: str, size: int) -> Tuple[int, int]:
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", str(header or "").strip())
    if not match:
        return 0, size - 1
    start_text, end_text = match.groups()
    if not start_text:
        length = int(end_text or 0)
        return max(0, size - length), size - 1
    start = int(start_text)
    end = min(int(end_text), size - 1) if end_text else size - 1
    if start > end or start >= size:
        raise HTTPException(status_code=416, detail="Invalid range.")
    return start, end


def _file_stream(path: Path, start: int, end: int) -> Iterator[bytes]:
    remaining = end - start + 1
    with open(path, "rb") as handle:
        handle.seek(start)
        while remaining > 0:
            chunk = handle.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            THROTTLE.wait(len(chunk))
            remaining -= len(chunk)
            yield chunk


# ======================================================================================================================
# API
# ======================================================================================================================
class CredentialsChoice(BaseModel):
    mode: str = "custom"  # "saved" (an account of Settings > Service credentials) or "custom"
    account_id: int = 1
    values: Dict[str, str] = Field(default_factory=dict)


class TaskCreateRequest(BaseModel):
    kind: str
    takeout_type: str = "google"
    input_mode: str = "upload"
    source_service: str = ""
    target_service: str = ""
    source: CredentialsChoice | None = None
    target: CredentialsChoice | None = None
    accept_terms: bool = False


class UploadStartRequest(BaseModel):
    name: str
    size: int


class RemoteSelectRequest(BaseModel):
    path: str


class AdminCancelRequest(BaseModel):
    refund: bool = False


class ServiceSettingsRequest(BaseModel):
    enabled: bool = False
    price_min_cents: int = 500
    price_per_gb_cents: int = 5
    max_task_bytes: int = 10 * 1000 ** 4
    concurrent_tasks: int = 1
    download_mbps: int = 100
    download_days: int = 7
    quote_days: int = 7
    automatic_tax: bool = False
    operator_name: str = ""
    contact_email: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    dropbox_app_key: str = ""
    dropbox_app_secret: str = ""
    onedrive_client_id: str = ""
    onedrive_client_secret: str = ""
    clear: List[str] = Field(default_factory=list)


def _resolve_credentials(user: Dict[str, Any], service: str, choice: Optional[CredentialsChoice]) -> Dict[str, str]:
    if not service:
        return {}
    if choice is None:
        raise HTTPException(status_code=400, detail=f"Give the credentials of {LABELS.get(service, service)}.")
    if choice.mode == "saved":
        values = probes.credentials_from_config(service, DEPS.get_user_config_values(user), int(choice.account_id or 1))
    else:
        values = dict(choice.values or {})
    try:
        return probes.validate_credentials(service, values)
    except probes.ProbeError as exc:
        raise HTTPException(status_code=400, detail=f"{LABELS.get(service, service)}: {exc}") from exc


def _owned_task(task_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    task = get_task(task_id)
    if not task or int(task["user_id"]) != int(user["id"]):
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def _redirect_uri(request: Request, provider: str) -> str:
    return f"{DEPS.public_base_url(request)}/api/service/oauth/{provider}/callback"


def _oauth_state(task_id: str, nonce: str) -> str:
    signature = hmac.new(DEPS.secret.encode("utf-8"), f"{task_id}.{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"{task_id}.{nonce}.{signature}"


def public_info(user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = load_settings()
    return {
        "enabled": bool(settings["enabled"]),
        "billing": billing_active(settings),
        "billing_applies": bool(user and billing_applies(user, settings)),
        "price_min_cents": int(settings["price_min_cents"]),
        "price_per_gb_cents": int(settings["price_per_gb_cents"]),
        "currency": settings["currency"],
        "max_task_bytes": int(settings["max_task_bytes"]),
        "max_input_bytes": {kind: max_input_bytes(kind) for kind in KINDS},
        "download_days": int(settings["download_days"]),
        "quote_days": int(settings["quote_days"]),
        "importers": {
            "dropbox": bool(secret_value(settings, "dropbox_app_key") and secret_value(settings, "dropbox_app_secret")),
            "onedrive": bool(secret_value(settings, "onedrive_client_id") and secret_value(settings, "onedrive_client_secret")),
        },
        "terms_version": TERMS_VERSION,
        "credential_fields": probes.CREDENTIAL_FIELDS,
        "source_services": list(probes.SOURCE_SERVICES),
        "target_services": list(probes.SERVICES),
        "labels": LABELS,
    }


def admin_settings_view(request: Optional[Request] = None) -> Dict[str, Any]:
    settings = load_settings()
    base = DEPS.public_base_url(request)
    out = {key: settings[key] for key in DEFAULT_SETTINGS if not key.endswith("_encrypted")}
    for name in ("stripe_secret_key", "stripe_webhook_secret", "dropbox_app_secret", "onedrive_client_secret"):
        value = secret_value(settings, name)
        out[f"has_{name}"] = bool(value)
        out[f"{name}_from_env"] = bool(os.environ.get(ENV_OVERRIDES[name], "").strip())
    for name in ("dropbox_app_key", "onedrive_client_id"):
        out[name] = secret_value(settings, name)
        out[f"{name}_from_env"] = bool(os.environ.get(ENV_OVERRIDES[name], "").strip())
    out["stripe_mode"] = stripe.key_mode(secret_value(settings, "stripe_secret_key")) if out["has_stripe_secret_key"] else ""
    out["billing_active"] = billing_active(settings)
    out["work_dir"] = str(work_root())
    out["free_disk_bytes"] = free_disk_bytes()
    out["urls"] = {
        "stripe_webhook": f"{base}/api/service/stripe/webhook",
        "dropbox_redirect": f"{base}/api/service/oauth/dropbox/callback",
        "onedrive_redirect": f"{base}/api/service/oauth/onedrive/callback",
    }
    return out


def build_router(require_user: Callable[..., Dict[str, Any]], require_admin: Callable[..., Dict[str, Any]],
                 session_cookie: str) -> APIRouter:
    router = APIRouter()

    def _require_enabled(user: Dict[str, Any]) -> None:
        if not load_settings().get("enabled"):
            raise HTTPException(status_code=404, detail="The cloud service is not enabled on this server.")
        if str(user.get("role") or "").lower() == "demo":
            raise HTTPException(status_code=403, detail="Demo accounts cannot use the cloud service.")

    # --- Information and tasks ----------------------------------------------------------------------------------
    @router.get("/api/service/info")
    def service_info(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        return public_info(user)

    @router.get("/api/service/public-info")
    def service_public_info() -> Dict[str, Any]:
        info = public_info(None)
        return {key: info[key] for key in ("enabled", "billing", "price_min_cents", "price_per_gb_cents", "currency",
                                           "max_task_bytes", "download_days")}

    @router.get("/api/service/tasks")
    def service_tasks(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        return {"tasks": [public_task(task) for task in list_tasks(user_id=int(user["id"]), limit=100)]}

    @router.post("/api/service/tasks", status_code=201)
    def service_create(payload: TaskCreateRequest, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        _require_enabled(user)
        if not payload.accept_terms:
            raise HTTPException(status_code=400, detail="Accept the terms of service and the privacy policy to continue.")
        kind = payload.kind
        if kind not in KINDS:
            raise HTTPException(status_code=400, detail="Unknown task type.")
        takeout_type = payload.takeout_type if kind != "cloud_to_cloud" else ""
        if kind != "cloud_to_cloud" and takeout_type not in TAKEOUT_TYPES:
            raise HTTPException(status_code=400, detail="Choose Google Takeout or iCloud Takeout.")
        input_mode = payload.input_mode if kind != "cloud_to_cloud" else "cloud"
        if kind != "cloud_to_cloud":
            if input_mode not in INPUT_MODES:
                raise HTTPException(status_code=400, detail="Choose how to send the Takeout files.")
            if input_mode != "upload" and not public_info(user)["importers"].get(input_mode):
                raise HTTPException(status_code=400, detail="This storage is not available on this server.")
        source_service = payload.source_service if kind == "cloud_to_cloud" else ""
        target_service = payload.target_service if kind != "process_takeout" else ""
        if kind == "cloud_to_cloud" and source_service not in probes.SOURCE_SERVICES:
            raise HTTPException(status_code=400, detail="Choose Immich Photos, Synology Photos or NextCloud Photos as the source.")
        if kind != "process_takeout" and target_service not in probes.SERVICES:
            raise HTTPException(status_code=400, detail="Choose the destination service.")
        source_credentials = _resolve_credentials(user, source_service, payload.source)
        target_credentials = _resolve_credentials(user, target_service, payload.target)
        if (kind == "cloud_to_cloud" and source_service == target_service and source_service != "google-photos"
                and source_credentials.get("URL") != target_credentials.get("URL")):
            raise HTTPException(status_code=400, detail="Both accounts of the same service must be on the same server.")
        task = create_task(user, kind, takeout_type, input_mode, source_service, target_service, source_credentials, target_credentials)
        return {"task": public_task(task)}

    @router.get("/api/service/tasks/{task_id}")
    def service_task(task_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        out = public_task(task)
        out["events"] = task_events(task_id)
        if task["status"] == "ready":
            out["downloads"] = _signed_parts(task)
        return {"task": out}

    @router.post("/api/service/tasks/{task_id}/analyze")
    def service_analyze(task_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        _require_enabled(user)
        return {"task": public_task(start_analysis(_owned_task(task_id, user)))}

    @router.post("/api/service/tasks/{task_id}/accept")
    def service_accept(task_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        _require_enabled(user)
        return accept(_owned_task(task_id, user), DEPS.public_base_url(request))

    @router.post("/api/service/tasks/{task_id}/pay")
    def service_pay_download(task_id: str, request: Request, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        if task["status"] != "awaiting_download_payment":
            raise HTTPException(status_code=409, detail="This task has nothing to pay.")
        try:
            return {"checkout_url": start_checkout(task, "download", DEPS.public_base_url(request))}
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.get("/api/service/tasks/{task_id}/checkout/confirm")
    def service_checkout_confirm(task_id: str, session_id: str = Query(...), user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        if session_id != task.get("checkout_session_id"):
            raise HTTPException(status_code=400, detail="This payment does not belong to the task.")
        try:
            session = stripe.get_checkout_session(_stripe_key(), session_id)
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"task": public_task(mark_paid(task_id, session) or task)}

    @router.post("/api/service/tasks/{task_id}/cancel")
    def service_cancel(task_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        return {"task": public_task(cancel(_owned_task(task_id, user)))}

    # --- Uploads --------------------------------------------------------------------------------------------------
    @router.post("/api/service/tasks/{task_id}/uploads")
    def service_upload_start(task_id: str, payload: UploadStartRequest, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        if task["input_mode"] != "upload" or task["status"] not in {"draft", "quoted"}:
            raise HTTPException(status_code=409, detail="Files can no longer be added to this task.")
        name = _clean_file_name(payload.name)
        size = int(payload.size)
        if size <= 0:
            raise HTTPException(status_code=400, detail="The file is empty.")
        files = [item for item in task["input_files"] if item.get("name") != name]
        existing = next((item for item in task["input_files"] if item.get("name") == name and int(item.get("size") or 0) == size), None)
        if sum(int(item.get("size") or 0) for item in files) + size > max_input_bytes(task["kind"]):
            raise HTTPException(status_code=400, detail=f"The Takeout files can take up to {format_bytes(max_input_bytes(task['kind']))} in total.")
        if existing is None:
            existing = {"id": hashlib.sha256(name.encode("utf-8")).hexdigest()[:16], "name": name, "size": size, "received": 0, "complete": False}
            (task_dir(task_id) / INPUT_DIR / f"{name}.part").unlink(missing_ok=True)
        partial = task_dir(task_id) / INPUT_DIR / f"{name}.part"
        existing["received"] = partial.stat().st_size if partial.exists() else (size if existing.get("complete") else 0)
        files.append(existing)
        update_task(task_id, input_files=files, status="draft", error="")
        return {"upload": existing, "chunk_max_bytes": UPLOAD_CHUNK_MAX_BYTES}

    @router.put("/api/service/tasks/{task_id}/uploads/{upload_id}")
    async def service_upload_chunk(task_id: str, upload_id: str, request: Request, offset: int = Query(..., ge=0),
                                   user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        entry = next((item for item in task["input_files"] if item.get("id") == upload_id), None)
        if entry is None or task["status"] not in {"draft", "quoted"}:
            raise HTTPException(status_code=404, detail="Upload not found.")
        if entry.get("complete"):
            return {"upload": entry}
        partial = task_dir(task_id) / INPUT_DIR / f"{entry['name']}.part"
        current = partial.stat().st_size if partial.exists() else 0
        if offset != current:
            raise HTTPException(status_code=409, detail=json.dumps({"offset": current}))
        written = 0
        with open(partial, "ab") as handle:
            async for chunk in request.stream():
                written += len(chunk)
                if written > UPLOAD_CHUNK_MAX_BYTES or current + written > int(entry["size"]):
                    handle.truncate(current)
                    raise HTTPException(status_code=413, detail="The chunk is too large.")
                handle.write(chunk)
        received = current + written
        complete = received == int(entry["size"])
        if complete:
            partial.replace(task_dir(task_id) / INPUT_DIR / entry["name"])
        with STATE_LOCK:
            task = get_task(task_id) or task
            files = task["input_files"]
            for item in files:
                if item.get("id") == upload_id:
                    item["received"] = received
                    item["complete"] = complete
                    entry = item
            update_task(task_id, input_files=files, status="draft" if task["status"] == "quoted" else task["status"])
        return {"upload": entry}

    @router.delete("/api/service/tasks/{task_id}/uploads/{upload_id}")
    def service_upload_delete(task_id: str, upload_id: str, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        if task["status"] not in {"draft", "quoted"}:
            raise HTTPException(status_code=409, detail="Files can no longer be removed from this task.")
        files = []
        for item in task["input_files"]:
            if item.get("id") == upload_id:
                for name in (item["name"], f"{item['name']}.part"):
                    (task_dir(task_id) / INPUT_DIR / name).unlink(missing_ok=True)
            else:
                files.append(item)
        return {"task": public_task(update_task(task_id, input_files=files, status="draft"))}

    # --- Dropbox / OneDrive ---------------------------------------------------------------------------------------
    @router.get("/api/service/oauth/{provider}/start")
    def service_oauth_start(provider: str, request: Request, task: str = Query(...), user: Dict[str, Any] = Depends(require_user)):
        current = _owned_task(task, user)
        if provider not in remote.PROVIDERS or current["input_mode"] != provider:
            raise HTTPException(status_code=400, detail="Unknown storage.")
        settings = load_settings()
        client_id = secret_value(settings, "dropbox_app_key" if provider == "dropbox" else "onedrive_client_id")
        if not client_id:
            raise HTTPException(status_code=400, detail="This storage is not available on this server.")
        nonce = secrets.token_urlsafe(16)
        update_task(task, oauth_nonce=nonce)
        return RedirectResponse(remote.authorize_url(provider, client_id, _redirect_uri(request, provider), _oauth_state(task, nonce)), status_code=302)

    @router.get("/api/service/oauth/{provider}/callback")
    def service_oauth_callback(provider: str, request: Request, state: str = Query(""), code: str = Query(""),
                               error: str = Query(""), session_token: str | None = Cookie(default=None, alias=session_cookie)):
        parts = str(state).split(".")
        if len(parts) != 3 or not hmac.compare_digest(_oauth_state(parts[0], parts[1]), state):
            raise HTTPException(status_code=400, detail="Invalid authorization.")
        task_id = parts[0]
        user = DEPS.get_user_by_session(session_token)
        task = get_task(task_id)
        if not user or not task or int(task["user_id"]) != int(user["id"]) or task.get("oauth_nonce") != parts[1]:
            raise HTTPException(status_code=403, detail="Sign in with the account that created the task and try again.")
        update_task(task_id, oauth_nonce="")
        if error or not code:
            return RedirectResponse(f"/service?task={task_id}&connected=0", status_code=302)
        settings = load_settings()
        if provider == "dropbox":
            client_id, client_secret = secret_value(settings, "dropbox_app_key"), secret_value(settings, "dropbox_app_secret")
        else:
            client_id, client_secret = secret_value(settings, "onedrive_client_id"), secret_value(settings, "onedrive_client_secret")
        try:
            tokens = remote.exchange_code(provider, client_id, client_secret, code, _redirect_uri(request, provider))
        except remote.RemoteError as exc:
            update_task(task_id, error=str(exc))
            return RedirectResponse(f"/service?task={task_id}&connected=0", status_code=302)
        update_secrets(task_id, remote={"provider": provider, "tokens": tokens})
        record_event(task_id, "storage_connected", provider)
        return RedirectResponse(f"/service?task={task_id}&connected=1", status_code=302)

    @router.get("/api/service/tasks/{task_id}/remote")
    def service_remote_list(task_id: str, path: str = Query(""), user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        try:
            entries = _remote_storage(task).list_folder(path)
        except remote.RemoteError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"path": path, "entries": [{k: e[k] for k in ("name", "path", "is_folder", "size")} | {"archive": remote.is_archive(e["name"])} for e in entries]}

    @router.post("/api/service/tasks/{task_id}/remote/select")
    def service_remote_select(task_id: str, payload: RemoteSelectRequest, user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        task = _owned_task(task_id, user)
        if task["status"] not in {"draft", "quoted"}:
            raise HTTPException(status_code=409, detail="The folder can no longer be changed.")
        return {"task": public_task(update_task(task_id, remote_path=str(payload.path or "/"), status="draft", error=""))}

    # --- Downloads ------------------------------------------------------------------------------------------------
    def _signed_parts(task: Dict[str, Any]) -> List[Dict[str, Any]]:
        expires = _parse(task.get("download_expires_at"))
        expires_at = int(expires.timestamp()) if expires else int(time.time()) + 3600
        parts = []
        for part in download_parts(task["id"]):
            token = download_token(task["id"], part["name"], expires_at)
            part["url"] = f"/api/service/download/{task['id']}/{part['name']}?expires={expires_at}&token={token}"
            parts.append(part)
        return parts

    @router.get("/api/service/download/{task_id}/{name}")
    def service_download(task_id: str, name: str, request: Request, expires: int = Query(0), token: str = Query("")):
        task = get_task(task_id)
        if not task or task["status"] != "ready":
            raise HTTPException(status_code=404, detail="This download is not available.")
        if expires < time.time() or not hmac.compare_digest(download_token(task_id, name, expires), str(token)):
            raise HTTPException(status_code=403, detail="The download link expired. Open the task again to get a new one.")
        if not re.fullmatch(r"PhotoMigrator-[0-9a-f]{8}-part\d{3}\.zip", name):
            raise HTTPException(status_code=404, detail="File not found.")
        path = task_dir(task_id) / DOWNLOADS_DIR / name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")
        size = path.stat().st_size
        start, end = _range(request.headers.get("range", ""), size)
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        }
        status_code = 200
        if request.headers.get("range"):
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            status_code = 206
        return StreamingResponse(_file_stream(path, start, end), status_code=status_code, media_type="application/zip", headers=headers)

    # --- Stripe webhook -------------------------------------------------------------------------------------------
    @router.post("/api/service/stripe/webhook")
    async def service_stripe_webhook(request: Request) -> Response:
        payload = await request.body()
        try:
            event = stripe.verify_webhook(payload, request.headers.get("stripe-signature", ""),
                                          secret_value(load_settings(), "stripe_webhook_secret"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        handle_webhook_event(event)
        return Response(status_code=200)

    # --- Administration -------------------------------------------------------------------------------------------
    @router.get("/api/admin/service/settings")
    def admin_service_settings(request: Request, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        return admin_settings_view(request)

    @router.put("/api/admin/service/settings")
    def admin_service_save(payload: ServiceSettingsRequest, request: Request, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        if payload.price_min_cents < 0 or payload.price_per_gb_cents < 0:
            raise HTTPException(status_code=400, detail="Prices cannot be negative.")
        if not 1 <= payload.concurrent_tasks <= 8:
            raise HTTPException(status_code=400, detail="Run between 1 and 8 tasks at a time.")
        if payload.max_task_bytes < 1000 ** 3:
            raise HTTPException(status_code=400, detail="The space per task must be at least 1 GB.")
        if not 1 <= payload.download_days <= 60 or not 1 <= payload.quote_days <= 60:
            raise HTTPException(status_code=400, detail="Use between 1 and 60 days.")
        stored = DEPS.get_setting(SETTINGS_KEY, {}) or {}
        values = dict(DEFAULT_SETTINGS)
        values.update({k: v for k, v in stored.items() if k in DEFAULT_SETTINGS})
        values.update({
            "enabled": bool(payload.enabled), "price_min_cents": int(payload.price_min_cents),
            "price_per_gb_cents": int(payload.price_per_gb_cents), "max_task_bytes": int(payload.max_task_bytes),
            "concurrent_tasks": int(payload.concurrent_tasks), "download_mbps": max(0, int(payload.download_mbps)),
            "download_days": int(payload.download_days), "quote_days": int(payload.quote_days),
            "automatic_tax": bool(payload.automatic_tax),
            "operator_name": str(payload.operator_name or "").strip()[:200],
            "contact_email": str(payload.contact_email or "").strip()[:254],
            "dropbox_app_key": str(payload.dropbox_app_key or "").strip(),
            "onedrive_client_id": str(payload.onedrive_client_id or "").strip(),
        })
        for name in ("stripe_secret_key", "stripe_webhook_secret", "dropbox_app_secret", "onedrive_client_secret"):
            new_value = str(getattr(payload, name) or "").strip()
            if new_value:
                values[f"{name}_encrypted"] = DEPS.encrypt(new_value)
            elif name in payload.clear:
                values[f"{name}_encrypted"] = ""
        key = str(payload.stripe_secret_key or "").strip()
        if key and not re.match(r"^(sk|rk)_(test|live)_", key):
            raise HTTPException(status_code=400, detail="The Stripe key must start with rk_test_, rk_live_, sk_test_ or sk_live_.")
        if str(payload.stripe_webhook_secret or "").strip() and not str(payload.stripe_webhook_secret).strip().startswith("whsec_"):
            raise HTTPException(status_code=400, detail="The webhook signing secret must start with whsec_.")
        DEPS.set_setting(SETTINGS_KEY, values)
        if values["enabled"]:
            ensure_work_root()
        return admin_settings_view(request)

    @router.post("/api/admin/service/stripe/test")
    def admin_service_stripe_test(admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        try:
            return stripe.check_connection(_stripe_key())
        except stripe.StripeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/api/admin/service/tasks")
    def admin_service_tasks(admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        tasks = list_tasks(limit=500)
        users: Dict[int, Dict[str, Any]] = {}
        out = []
        for task in tasks:
            uid = int(task["user_id"])
            if uid not in users:
                users[uid] = _user(uid)
            item = public_task(task)
            item["username"] = users[uid].get("username", "")
            item["email"] = users[uid].get("email", "")
            item["refund_id"] = task.get("refund_id", "")
            item["payment_intent_id"] = task.get("payment_intent_id", "")
            out.append(item)
        paid = [t for t in tasks if int(t.get("amount_paid_cents") or 0)]
        return {
            "tasks": out,
            "summary": {
                "queued": len([t for t in tasks if t["status"] == "queued"]),
                "active": len([t for t in tasks if t["status"] in ACTIVE_STATES]),
                "revenue_cents": sum(int(t["amount_paid_cents"]) for t in paid if not t.get("refunded_at")),
                "refunded_cents": sum(int(t["amount_paid_cents"]) for t in paid if t.get("refunded_at")),
                "free_disk_bytes": free_disk_bytes(),
                "currency": load_settings()["currency"],
            },
        }

    @router.get("/api/admin/service/tasks/{task_id}")
    def admin_service_task(task_id: str, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        task = get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        out = public_task(task)
        out["events"] = task_events(task_id)
        return {"task": out}

    @router.post("/api/admin/service/tasks/{task_id}/cancel")
    def admin_service_cancel(task_id: str, payload: AdminCancelRequest, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        task = get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found.")
        return {"task": public_task(cancel(task, by_admin=True, refund_running=bool(payload.refund)))}

    @router.post("/api/admin/service/tasks/{task_id}/refund")
    def admin_service_refund(task_id: str, admin: Dict[str, Any] = Depends(require_admin)) -> Dict[str, Any]:
        task = get_task(task_id)
        if not task or not task.get("payment_intent_id"):
            raise HTTPException(status_code=404, detail="This task has no payment.")
        if task.get("refunded_at"):
            raise HTTPException(status_code=409, detail="This payment was already refunded.")
        task = refund(task, "Refunded by an administrator")
        if not task.get("refunded_at"):
            raise HTTPException(status_code=502, detail="Stripe did not make the refund. Check the Access logs and Stripe.")
        return {"task": public_task(task)}

    return router


def legal_context() -> Dict[str, Any]:
    """Values shown in the terms of service and the privacy policy."""
    settings = load_settings()
    contact = str(settings.get("contact_email") or "").strip() or str(mailer.settings().get("from_address") or "")
    return {
        "operator": str(settings.get("operator_name") or "").strip() or "the operator of this server",
        "contact": contact or "-",
        "price_min": format_price(int(settings["price_min_cents"]), settings["currency"]),
        "price_gb": format_price(int(settings["price_per_gb_cents"]), settings["currency"]),
        "quote_days": int(settings["quote_days"]),
        "download_days": int(settings["download_days"]),
        "max_space": format_bytes(int(settings["max_task_bytes"])),
        "terms_version": TERMS_VERSION,
    }


def ensure_work_root() -> Path:
    return _private_mkdir(work_root())
