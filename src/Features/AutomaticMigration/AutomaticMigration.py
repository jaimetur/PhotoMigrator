import functools
import heapq
import json
import logging
import os
import re
import shutil
import sys
import threading
import time
import traceback
import unicodedata
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue, Empty, PriorityQueue
from typing import Union, cast

from Core.CustomLogger import set_log_level, CustomInMemoryLogHandler, CustomConsoleFormatter, get_logger_filename
from Core.GlobalVariables import TOOL_NAME_VERSION, TOOL_VERSION, ARGS, HELP_TEXTS, MSG_TAGS, TIMESTAMP, LOGGER, FOLDERNAME_LOGS, TOOL_DATE, FOLDERNAME_EXTRACTED_DATES
from Features.GoogleTakeout.ClassTakeoutFolder import ClassLocalFolder, ClassTakeoutFolder, contains_takeout_structure
from Features.ICloudTakeout.ClassICloudTakeoutFolder import ClassICloudTakeoutFolder, contains_icloud_takeout_structure
from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
from Features.GooglePhotos.ClassGooglePhotos import ClassGooglePhotos
from Features.NextCloudPhotos.ClassNextCloudPhotos import ClassNextCloudPhotos
from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos
from Utils.FileUtils import DEFAULT_FILE_EXCLUSION_PATTERNS, DEFAULT_FOLDER_EXCLUSION_PATTERNS, merge_exclusion_patterns, remove_empty_dirs, contains_zip_files, normalize_path, sanitize_and_unpack_zips
from Utils.GeneralUtils import confirm_continue, TQDM_DASHBOARD_PREFIX, TQDM_DASHBOARD_META_PREFIX, find_reusable_album_candidate, build_reusable_album_group, canonicalize_album_name_for_reuse, prefer_canonical_album_names_enabled, consolidate_similar_albums_enabled
from Utils.StandaloneUtils import change_working_dir, resolve_external_path

terminal_width = shutil.get_terminal_size().columns
BG_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
BG_TQDM_PROGRESS_RE = re.compile(
    r"(?P<pct>\d{1,3})%\|[^|]*\|\s*(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)"
)
BG_CUSTOM_PROGRESS_RE = re.compile(
    r"^(?P<desc>.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+"
    r"(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)\s+\d+(?:\.\d+)?%\s*$"
)
BG_SIMPLE_PROGRESS_RE = re.compile(
    r"^(?P<desc>.+?)\s*:\s*(?P<current>[0-9][0-9,]*)\s*/\s*(?P<total>[0-9][0-9,]*)\b.*$"
)
BG_INDETERMINATE_TQDM_RE = re.compile(
    r"(?P<current>[0-9][0-9,]*)\s+(?P<unit>[A-Za-z][A-Za-z0-9_./-]*)\s+\[[^\]]+\]\s*$"
)
BG_LEVEL_PREFIX_RE = re.compile(
    r"^(?:\[\s*(?:VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\]|(?:VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL))\s*:?\s*",
    flags=re.IGNORECASE,
)
WEB_DASHBOARD_SNAPSHOT_PREFIX = "__PHOTOMIGRATOR_DASHBOARD__\t"


class SharedData:
    def __init__(self, info, counters, logs_queue):
        self.info = info
        self.counters = counters
        self.logs_queue = logs_queue


def _build_web_dashboard_snapshot(shared_data, parallel=None):
    info = dict(getattr(shared_data, "info", {}) or {})
    counters = dict(getattr(shared_data, "counters", {}) or {})
    inferred_queue = max(
        0,
        int(counters.get("total_pulled_assets", 0) or 0)
        - int(counters.get("total_pushed_assets", 0) or 0)
        - int(counters.get("total_push_failed_assets", 0) or 0)
        - int(counters.get("total_push_duplicates_assets", 0) or 0),
    )
    queue_value = max(
        int(info.get("assets_in_queue", 0) or 0),
        inferred_queue,
    )
    snapshot = {
        "migrationMode": "parallel" if bool(parallel) else "sequential",
        "sourceClientName": info.get("source_client_name"),
        "targetClientName": info.get("target_client_name"),
        "totalAssets": int(info.get("total_assets", 0) or 0),
        "totalPhotos": int(info.get("total_photos", 0) or 0),
        "totalVideos": int(info.get("total_videos", 0) or 0),
        "totalAlbums": int(info.get("total_albums", 0) or 0),
        "totalMetadata": int(info.get("total_metadata", 0) or 0),
        "totalSidecar": int(info.get("total_sidecar", 0) or 0),
        "totalInvalid": int(info.get("total_invalid", 0) or 0),
        "blockedAlbums": int(info.get("total_albums_blocked", 0) or 0),
        "blockedAssets": int(counters.get("total_assets_blocked", 0) or 0),
        "assetsInQueue": queue_value,
        "pulledAssets": int(counters.get("total_pulled_assets", 0) or 0),
        "pulledPhotos": int(counters.get("total_pulled_photos", 0) or 0),
        "pulledVideos": int(counters.get("total_pulled_videos", 0) or 0),
        "pulledAlbums": int(counters.get("total_pulled_albums", 0) or 0),
        "pullFailedAssets": int(counters.get("total_pull_failed_assets", 0) or 0),
        "pullFailedPhotos": int(counters.get("total_pull_failed_photos", 0) or 0),
        "pullFailedVideos": int(counters.get("total_pull_failed_videos", 0) or 0),
        "pullFailedAlbums": int(counters.get("total_pull_failed_albums", 0) or 0),
        "pushedAssets": int(counters.get("total_pushed_assets", 0) or 0),
        "pushedPhotos": int(counters.get("total_pushed_photos", 0) or 0),
        "pushedVideos": int(counters.get("total_pushed_videos", 0) or 0),
        "pushedAlbums": int(counters.get("total_pushed_albums", 0) or 0),
        "pushDuplicates": int(counters.get("total_push_duplicates_assets", 0) or 0),
        "pushFailedAssets": int(counters.get("total_push_failed_assets", 0) or 0),
        "pushFailedPhotos": int(counters.get("total_push_failed_photos", 0) or 0),
        "pushFailedVideos": int(counters.get("total_push_failed_videos", 0) or 0),
        "pushFailedAlbums": int(counters.get("total_push_failed_albums", 0) or 0),
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return snapshot


def _debug_perf_log(logger, label, started_at, **fields):
    if not logger.isEnabledFor(logging.DEBUG):
        return
    elapsed_ms = (time.perf_counter() - float(started_at)) * 1000.0
    payload = [f"{key}={value}" for key, value in fields.items() if value is not None]
    suffix = f" | {' '.join(payload)}" if payload else ""
    logger.debug(f"[PERF] {label}: {elapsed_ms:.2f} ms{suffix}")


def _debug_perf_log_elapsed(logger, label, elapsed_ms, **fields):
    if not logger.isEnabledFor(logging.DEBUG):
        return
    payload = [f"{key}={value}" for key, value in fields.items() if value is not None]
    suffix = f" | {' '.join(payload)}" if payload else ""
    logger.debug(f"[PERF] {label}: {float(elapsed_ms):.2f} ms{suffix}")


def _parse_int(value, default=0):
    try:
        return int(str(value or "").replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _format_hms_from_seconds(total_seconds):
    safe_seconds = max(0, int(round(float(total_seconds or 0))))
    return str(timedelta(seconds=safe_seconds))


def _compute_dashboard_estimated_time(elapsed_seconds, processed_assets, pending_assets, total_assets=None):
    total_assets = max(0, _parse_int(total_assets, 0))
    processed_assets = max(0, _parse_int(processed_assets, 0))
    pending_assets = max(0, _parse_int(pending_assets, 0))

    if total_assets <= 0 and (processed_assets > 0 or pending_assets > 0):
        total_assets = processed_assets + pending_assets
    if total_assets <= 0:
        return "-"
    if pending_assets <= 0:
        return "00:00:00"
    if processed_assets <= 0:
        return "Estimating..."

    safe_elapsed_seconds = max(0.0, float(elapsed_seconds or 0.0))
    avg_seconds_per_asset = safe_elapsed_seconds / float(processed_assets)
    estimated_remaining_seconds = avg_seconds_per_asset * float(pending_assets)
    return _format_hms_from_seconds(estimated_remaining_seconds)


def _strip_bg_level_prefix(text):
    value = str(text or "")
    previous = None
    while value != previous:
        previous = value
        value = BG_LEVEL_PREFIX_RE.sub("", value, count=1)
    return value


def _normalize_bg_progress_desc(desc):
    text = re.sub(r"\s+", " ", str(desc or "")).strip()
    text = _strip_bg_level_prefix(text)
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    text = _strip_bg_level_prefix(text.strip())
    text = re.sub(
        r"\s+\b(?:in|at|from)(?:\s+\w+){0,2}\s+[\"']?(?:[A-Za-z]:[\\/]|/)[^\"']*[\"']?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*:\s*$", "", text)
    text = text.strip()
    return text or "Progress"


def _parse_dashboard_progress_line(line):
    raw = str(line or "")
    if not raw:
        return None
    plain = BG_ANSI_ESCAPE_RE.sub("", raw.replace("\r", "")).strip()
    if not plain:
        return None

    if plain.startswith(TQDM_DASHBOARD_META_PREFIX):
        payload = plain[len(TQDM_DASHBOARD_META_PREFIX):]
        parts = payload.split("\t")
        if len(parts) != 3:
            return None
        return {
            "desc": parts[0],
            "current": _parse_int(parts[1], 0),
            "total": _parse_int(parts[2], 0),
            "has_total": _parse_int(parts[2], 0) > 0,
        }

    if plain.startswith(TQDM_DASHBOARD_PREFIX):
        plain = plain[len(TQDM_DASHBOARD_PREFIX):].strip()
    elif plain.upper().startswith("TQDM "):
        plain = plain[5:].strip()
    plain = _strip_bg_level_prefix(plain)

    custom_match = BG_CUSTOM_PROGRESS_RE.match(plain)
    if custom_match:
        total = _parse_int(custom_match.group("total"), 0)
        return {
            "desc": custom_match.group("desc").strip(" :"),
            "current": _parse_int(custom_match.group("current"), 0),
            "total": total,
            "has_total": total > 0,
        }

    simple_match = BG_SIMPLE_PROGRESS_RE.match(plain)
    if simple_match:
        total = _parse_int(simple_match.group("total"), 0)
        return {
            "desc": simple_match.group("desc").strip(" :"),
            "current": _parse_int(simple_match.group("current"), 0),
            "total": total,
            "has_total": total > 0,
        }

    tqdm_match = BG_TQDM_PROGRESS_RE.search(plain)
    if tqdm_match:
        desc = plain[:tqdm_match.start()].strip(" :-")
        if not desc:
            return None
        total = _parse_int(tqdm_match.group("total"), 0)
        return {
            "desc": desc,
            "current": _parse_int(tqdm_match.group("current"), 0),
            "total": total,
            "has_total": total > 0,
        }

    indeterminate_match = BG_INDETERMINATE_TQDM_RE.search(plain)
    if indeterminate_match:
        desc = plain[:indeterminate_match.start()].strip(" :-")
        if not desc:
            return None
        return {
            "desc": desc,
            "current": _parse_int(indeterminate_match.group("current"), 0),
            "total": None,
            "has_total": False,
        }

    return None


def _select_visible_bg_progress_rows(rows, visible_limit):
    ordered = list(rows or [])
    ordered.sort(
        key=lambda info: (
            bool(info.get("completed")),
            -float(info.get("last_update", 0.0)),
            str(info.get("label", "")).lower(),
        )
    )
    return ordered[:max(1, int(visible_limit or 1))]


def _pull_has_content(pulled_result) -> bool:
    if isinstance(pulled_result, bool):
        return pulled_result
    if isinstance(pulled_result, (int, float)):
        return pulled_result > 0
    if isinstance(pulled_result, str):
        return bool(pulled_result.strip())
    if isinstance(pulled_result, (list, tuple, set, dict)):
        return len(pulled_result) > 0
    return bool(pulled_result)


def _is_nextcloud_photo_not_found_error(error: Exception) -> bool:
    return "photo not found for user" in str(error or "").lower()


def _remove_source_asset_after_move(source_client, asset_id, log_level=logging.INFO):
    """
    Delete the source asset after a successful push.

    Local folders are a special case: per-asset analyzer refresh is both noisy and
    expensive during automatic migration, so use a quiet no-refresh deletion path.
    """
    if not asset_id:
        return 0
    if isinstance(source_client, ClassLocalFolder):
        return source_client.remove_assets(
            asset_ids=asset_id,
            log_level=logging.WARNING,
            refresh_analyzer=False,
            log_removed_count=False,
        )
    return source_client.remove_assets(asset_ids=asset_id, log_level=log_level)


def _cleanup_local_source_after_move(source_client, log_level=logging.INFO):
    if not isinstance(source_client, ClassLocalFolder):
        return {}
    try:
        return source_client.cleanup_after_move_assets(log_level=log_level)
    except Exception as error:
        LOGGER.warning(f"Unable to cleanup local source after move-assets migration: {error}")
        return {}


def _is_blocked_synology_shared_album(source_client, album) -> bool:
    if not isinstance(source_client, ClassSynologyPhotos):
        return False
    return bool(source_client.is_blocked_shared_album(album))


def _normalized_asset_path_key(path: str) -> str:
    return os.path.normpath(str(path or "")).replace("\\", "/").lower()


def _queue_contains_asset_path(queue, path: str) -> bool:
    wanted_key = _normalized_asset_path_key(path)
    if not wanted_key:
        return False
    with queue.mutex:
        for queued in list(queue.queue):
            queued_item = queued[2] if isinstance(queued, tuple) and len(queued) == 3 else queued
            if not isinstance(queued_item, dict):
                continue
            queued_key = _normalized_asset_path_key(queued_item.get("asset_file_path", ""))
            if queued_key == wanted_key:
                return True
        return False


def _asset_path_is_reserved(queue, in_flight_paths, in_flight_lock, path: str) -> bool:
    wanted_key = _normalized_asset_path_key(path)
    if not wanted_key:
        return False
    if _queue_contains_asset_path(queue, path):
        return True
    with in_flight_lock:
        return wanted_key in in_flight_paths


def _mark_album_pushed_if_ready(album_name, album_folder_path, processed_albums, processed_albums_lock, counters, logger):
    """
    Count an album as pushed once its temp folder is no longer active and can be removed.
    """
    if not album_name or not album_folder_path or counters is None:
        return False

    with processed_albums_lock:
        if album_name in processed_albums:
            return False
        if not os.path.isdir(album_folder_path):
            return False

        active_file = os.path.join(album_folder_path, ".active")
        if os.path.exists(active_file):
            return False

        try:
            os.rmdir(album_folder_path)
        except OSError:
            return False

        processed_albums.add(album_name)
        counters['total_pushed_albums'] += 1
        logger.info(f"Album Pushed    : '{album_name}'")
        return True


def _album_finalize_wait_reason(album_folder_path, pending_duplicate_keys=None):
    pending_duplicate_keys = pending_duplicate_keys or set()
    if not album_folder_path or not os.path.isdir(album_folder_path):
        return "album folder missing"

    active_file = os.path.join(album_folder_path, ".active")
    if os.path.exists(active_file):
        return "album still active"

    remaining_files = []
    for entry in os.listdir(album_folder_path):
        if entry == ".active" or entry.endswith(".lock"):
            continue
        file_path = os.path.join(album_folder_path, entry)
        if os.path.isfile(file_path) and path_key(file_path) not in pending_duplicate_keys:
            remaining_files.append(file_path)
    if remaining_files:
        return f"{len(remaining_files)} pending file(s) in queue"

    if pending_duplicate_keys:
        return f"{len(pending_duplicate_keys)} pending duplicate resolution item(s)"

    return "album folder not removable yet"


def restore_log_info_on_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # En caso de cualquier excepción, forzamos INFO
            LOGGER.setLevel(logging.INFO)
            LOGGER.exception("Excepción capturada: nivel de log restaurado a INFO")
            # Re-levantamos para no silenciar el error
            raise
    return wrapper


####################################
# FEATURE: AUTOMATIC-MIGRATION: #
####################################
def mode_AUTOMATIC_MIGRATION(source=None, target=None, show_dashboard=None, show_gpth_info=None, show_gpth_errors=None, parallel=None, log_level=None):
    with set_log_level(LOGGER, log_level):
        # ───────────────────────────────────────────────────────────────
        # Declare shared variables to pass as reference to both functions
        # ───────────────────────────────────────────────────────────────

        # Inicializamos start_time para medir el tiempo de procesamiento
        start_time = datetime.now()

        # Cola que contendrá los mensajes de log en memoria
        logs_queue = Queue()

        # Contadores globales
        counters = {
            'total_pulled_assets': 0,
            'total_pulled_photos': 0,
            'total_pulled_videos': 0,
            'total_pulled_albums': 0,
            'total_pull_failed_assets': 0,
            'total_pull_failed_photos': 0,
            'total_pull_failed_videos': 0,
            'total_pull_failed_albums': 0,
            'total_albums_blocked': 0,
            'total_assets_blocked': 0,

            'total_pushed_assets': 0,
            'total_pushed_photos': 0,
            'total_pushed_videos': 0,
            'total_pushed_albums': 0,
            'total_push_failed_assets': 0,
            'total_push_failed_photos': 0,
            'total_push_failed_videos': 0,
            'total_push_failed_albums': 0,
            'total_push_duplicates_assets': 0,
            'total_push_retry_scheduled_assets': 0,
            'total_push_retry_recovered_assets': 0,
            'total_album_assoc_retry_scheduled_assets': 0,
            'total_album_assoc_retry_recovered_assets': 0,
            'total_album_assoc_unconfirmed_assets': 0,
        }

        # Input INFO
        input_info = {
            "source_client_name": "Source Client",
            "target_client_name": "Target Client",
            "total_assets": 0,
            "total_photos": 0,
            "total_videos": 0,
            "total_albums": 0,
            "total_albums_blocked": 0,
            "total_metadata": 0,
            "total_sidecar": 0,
            "total_invalid": 0,
            "assets_in_queue": 0,
            "delayed_assets_pending": 0,
            "elapsed_time": 0,
            "estimated_time": "-",
            "start_time": start_time
        }

        SHARED_DATA = SharedData(input_info, counters, logs_queue)

        # Check if parallel=None, and in that case, get it from ARGS
        if parallel is None: parallel = ARGS['parallel-migration']

        # Detect source and target from the given arguments if have not been provided on the function call
        if not source: source = ARGS['source']
        if not target: target = ARGS['target']

        # Detect show_dashboard from the given arguments if it has not been provided on the function call
        if show_dashboard is None: show_dashboard = ARGS['dashboard']

        # Detect show_gpth_info and show_gpth_errors from the given arguments if it has not been provided on the function call
        if show_gpth_info is None: show_gpth_info = ARGS['show-gpth-info']
        if show_gpth_errors is None: show_gpth_errors = ARGS['show-gpth-errors']

        # Define the INTERMEDIATE_FOLDER
        INTERMEDIATE_FOLDER = resolve_external_path(f'./Automatic_Migration_Push_Failed_{TIMESTAMP}')

        # ---------------------------------------------------------------------------------------------------------
        # 1) Creamos los objetos source_client y target_client en función de los argumentos source y target
        # ---------------------------------------------------------------------------------------------------------
        def _prepare_local_folder_for_detection(client_type, client_label):
            client_path = Path(str(client_type)).expanduser()
            if not client_path.is_dir():
                return client_type
            if not contains_zip_files(str(client_path), log_level=logging.WARNING):
                return str(client_path)

            unzip_folder = Path(f"{client_path}_unzipped_{TIMESTAMP}").resolve()
            LOGGER.info(
                f"📦 {client_label} Folder contains ZIP files. "
                f"Unzipping first into '{unzip_folder}' before Automatic Migration source-type detection..."
            )
            sanitize_and_unpack_zips(
                input_folder=str(client_path),
                unzip_folder=str(unzip_folder),
                step_name=f"[Automatic Migration]-[{client_label} PRE-CHECK]-[Unzip] : ",
                log_level=log_level,
            )
            return str(unzip_folder)

        def get_client_object(client_type, client_label="Local"):
            """Retorna la instancia del cliente en función del tipo de fuente o destino."""

            # Return ClassSynologyPhotos
            if client_type.lower() in ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1'] and not ARGS['account-id'] > 1:
                return ClassSynologyPhotos(account_id=1)
            elif client_type.lower() in ['synology-photos-2', 'synology-photos2', 'synology-2', 'synology2']:
                return ClassSynologyPhotos(account_id=2)
            elif client_type.lower() in ['synology-photos-3', 'synology-photos3', 'synology-3', 'synology3']:
                return ClassSynologyPhotos(account_id=3)
            elif client_type.lower() in ['synology-photos', 'synology'] and ARGS['account-id'] > 1:
                return ClassSynologyPhotos(account_id=ARGS['account-id'])

            # Return ClassImmichPhotos
            elif client_type.lower() in ['immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1'] and not ARGS['account-id'] > 1:
                return ClassImmichPhotos(account_id=1)
            elif client_type.lower() in ['immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']:
                return ClassImmichPhotos(account_id=2)
            elif client_type.lower() in ['immich-photos-3', 'immich-photos3', 'immich-3', 'immich3']:
                return ClassImmichPhotos(account_id=3)
            elif client_type.lower() in ['immich-photos', 'immich'] and ARGS['account-id'] > 1:
                return ClassImmichPhotos(account_id=ARGS['account-id'])

            # Return ClassNextCloudPhotos
            elif client_type.lower() in ['nextcloud-photos', 'nextcloud', 'nextcloud-photos-1', 'nextcloud-photos1', 'nextcloud-1', 'nextcloud1'] and not ARGS['account-id'] > 1:
                return ClassNextCloudPhotos(account_id=1)
            elif client_type.lower() in ['nextcloud-photos-2', 'nextcloud-photos2', 'nextcloud-2', 'nextcloud2']:
                return ClassNextCloudPhotos(account_id=2)
            elif client_type.lower() in ['nextcloud-photos-3', 'nextcloud-photos3', 'nextcloud-3', 'nextcloud3']:
                return ClassNextCloudPhotos(account_id=3)
            elif client_type.lower() in ['nextcloud-photos', 'nextcloud'] and ARGS['account-id'] > 1:
                return ClassNextCloudPhotos(account_id=ARGS['account-id'])

            # Return ClassGooglePhotos
            elif client_type.lower() in ['google-photos', 'googlephotos', 'google-photos-1', 'googlephotos-1', 'google-1', 'google1'] and not ARGS['account-id'] > 1:
                return ClassGooglePhotos(account_id=1)
            elif client_type.lower() in ['google-photos-2', 'googlephotos-2', 'google-2', 'google2']:
                return ClassGooglePhotos(account_id=2)
            elif client_type.lower() in ['google-photos-3', 'googlephotos-3', 'google-3', 'google3']:
                return ClassGooglePhotos(account_id=3)
            elif client_type.lower() in ['google-photos', 'googlephotos'] and ARGS['account-id'] > 1:
                return ClassGooglePhotos(account_id=ARGS['account-id'])

            local_detection_path = _prepare_local_folder_for_detection(client_type, client_label)

            # Return ClassICloudTakeoutFolder
            if Path(local_detection_path).is_dir() and contains_icloud_takeout_structure(local_detection_path, log_level=logging.INFO):
                return ClassICloudTakeoutFolder(local_detection_path)  # In this class, client_type is the path to the iCloud Takeout Folder

            # Return ClassTakeoutFolder
            elif Path(local_detection_path).is_dir() and contains_takeout_structure(local_detection_path, log_level=logging.INFO):
                return ClassTakeoutFolder(local_detection_path)  # In this clase, client_type is the path to the Takeout Folder

            # Return ClassLocalFolder
            elif Path(local_detection_path).is_dir():
                return ClassLocalFolder(base_folder=local_detection_path)  # In this clase, client_type is the path to the base Local Folder
            else:
                raise ValueError(f"{MSG_TAGS['ERROR']}Tipo de cliente no válido: {client_type}")

        # Creamos los objetos source_client y target_client y obtenemos sus nombres para mostrar en el show_dashboard
        source_client = get_client_object(source, client_label="Source")
        source_client_name = source_client.get_client_name()
        SHARED_DATA.info.update({"source_client_name": source_client_name})

        target_client = get_client_object(target, client_label="Target")
        target_client_name = target_client.get_client_name()
        SHARED_DATA.info.update({"target_client_name": target_client_name})

        # Check if source_client support specified filters
        unsupported_text = ""
        if isinstance(source_client, (ClassTakeoutFolder, ClassICloudTakeoutFolder, ClassLocalFolder)):
            unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

        # Check if '-move, --move-assets' have been passed as argument
        move_assets = ARGS.get('move-assets', False)

        # Get the values from the arguments (if exists)
        type = ARGS.get('filter-by-type', None)
        from_date = ARGS.get('filter-from-date', None)
        to_date = ARGS.get('filter-to-date', None)
        country = ARGS.get('filter-by-country', None)
        city = ARGS.get('filter-by-city', None)
        person = ARGS.get('filter-by-person', None)
        exclude_folders = ARGS.get('exclude-folders', []) or []
        exclude_files = ARGS.get('exclude-files', []) or []
        effective_exclude_folders = merge_exclusion_patterns(
            exclude_folders,
            default_patterns=DEFAULT_FOLDER_EXCLUSION_PATTERNS,
        )
        effective_exclude_files = merge_exclusion_patterns(
            exclude_files,
            default_patterns=DEFAULT_FILE_EXCLUSION_PATTERNS,
        )

        LOGGER.info(f"")
        LOGGER.info(f"*** Automatic Migration Mode *** detected")
        LOGGER.info('-' * (terminal_width-10))
        if not isinstance(source_client, (ClassTakeoutFolder, ClassICloudTakeoutFolder)):
            LOGGER.warning(HELP_TEXTS["AUTOMATIC-MIGRATION"].replace('<SOURCE>', f"'{source}'").replace('<TARGET>', f"'{target}'"))
        else:
            LOGGER.warning(HELP_TEXTS["AUTOMATIC-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{source}'").replace('<TARGET>', f"'{target}'").replace('Pulling', 'Analyzing and Fixing'))
        LOGGER.info('-' * (terminal_width-10))
        LOGGER.info(f"Source Client  : {source_client_name}")
        LOGGER.info(f"Target Client  : {target_client_name}")
        LOGGER.info(f"Temp Folder    : {INTERMEDIATE_FOLDER}")

        if parallel:
            LOGGER.info(f"Migration Mode : Parallel")
        else:
            LOGGER.info(f"Migration Mode : Sequential")

        LOGGER.info(f"Move Assets    : {move_assets}")

        if from_date or to_date or type or country or city or person or effective_exclude_folders or effective_exclude_files:
            LOGGER.info(f"Assets Filters :")
        else:
            LOGGER.info(f"Assets Filters : None")
        if from_date:
            date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"     from Date : {date_obj.strftime('%Y-%m-%d')}")
        if to_date:
            date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            LOGGER.info(f"       to Date : {date_obj.strftime('%Y-%m-%d')}")
        if type:
            LOGGER.info(f"       by Type : {type}")
        if country:
            LOGGER.info(f"    by Country : {country} {unsupported_text}")
        if city:
            LOGGER.info(f"       by City : {city} {unsupported_text}")
        if person:
            LOGGER.info(f"     by Person : {person} {unsupported_text}")
        if effective_exclude_folders:
            LOGGER.info(f" Excl. Folders : {effective_exclude_folders}")
        if effective_exclude_files:
            LOGGER.info(f"   Excl. Files : {effective_exclude_files}")

        LOGGER.info(f"")
        if isinstance(source_client, ClassGooglePhotos):
            LOGGER.error(ClassGooglePhotos.get_full_library_read_unsupported_message("Automatic Migration"))
            LOGGER.error("Recommended workaround: export your library with Google Takeout and use the Takeout folder as `--source`.")
            sys.exit(1)

        if not confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
            # Call the parallel_automatic_migration module to do the whole migration process
            # parallel_automatic_migration(source, target, temp_folder, SHARED_DATA.input_info, SHARED_DATA.counters, SHARED_DATA.logs_queue)
            # and if show_dashboard=True, launch start_dashboard function to show a Live Dashboard of the whole process
            # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

            # ---------------------------------------------------------------------------------------------------------
            # 1) Creamos un evento para indicar cuándo termina la migración
            migration_finished = threading.Event()
            web_mode = os.environ.get("PHOTOMIGRATOR_WEB_MODE") == "1"
            embedded_ui_mode = os.environ.get("PHOTOMIGRATOR_EMBEDDED_UI") == "1"
            web_dashboard_snapshot_thread = None
            if show_dashboard and embedded_ui_mode:
                LOGGER.info("Embedded GUI/TUI execution detected. Rich Live Dashboard is disabled in embedded panels because it is full-screen terminal output and degrades rendering/performance there.")
            effective_dashboard = bool(show_dashboard and not web_mode and not embedded_ui_mode)
            # ---------------------------------------------------------------------------------------------------------

            # ------------------------------------------------------------------------------------------------------
            # 2) Lanzamos el start_dashboard en un hilo secundario (o viceversa).
            # ------------------------------------------------------------------------------------------------------
            if effective_dashboard:
                dashboard_thread = threading.Thread(
                    target=start_dashboard,
                    kwargs={
                        "migration_finished": migration_finished,  # Pasamos un evento para indicar cuando ha terminado el proceso de migración
                        "SHARED_DATA": SHARED_DATA,  # Pasamos la instancia de la clase
                        "parallel": parallel,  # Pasamos el modo de migración (parallel=True/False)
                        "log_level": logging.INFO
                    },
                    daemon=True  # El show_dashboard se cierra si el proceso principal termina
                )
                dashboard_thread.start()

                # Pequeña espera para garantizar que el show_dashboard ha arrancado antes de la migración
                time.sleep(2)

            if web_mode:
                def _web_dashboard_snapshot_worker():
                    last_payload = ""
                    while not migration_finished.wait(0.25):
                        snapshot = _build_web_dashboard_snapshot(SHARED_DATA, parallel=parallel)
                        payload = json.dumps(snapshot, separators=(",", ":"), sort_keys=True)
                        if payload == last_payload:
                            continue
                        print(f"{WEB_DASHBOARD_SNAPSHOT_PREFIX}{payload}", flush=True)
                        last_payload = payload
                    final_snapshot = _build_web_dashboard_snapshot(SHARED_DATA, parallel=parallel)
                    final_payload = json.dumps(final_snapshot, separators=(",", ":"), sort_keys=True)
                    if final_payload != last_payload:
                        print(f"{WEB_DASHBOARD_SNAPSHOT_PREFIX}{final_payload}", flush=True)

                web_dashboard_snapshot_thread = threading.Thread(
                    target=_web_dashboard_snapshot_worker,
                    name="web-dashboard-snapshot",
                    daemon=True,
                )
                web_dashboard_snapshot_thread.start()

            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"🚀 AUTOMATIC MIGRATION JOB STARTED - {source_client_name} ➜ {target_client_name}")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")

            # ------------------------------------------------------------------------------------------------------
            # 3) Verifica y procesa source_client y target_client si es una instancia de ClassTakeoutFolder
            print_messages = False if effective_dashboard else True
            if isinstance(source_client, ClassTakeoutFolder):
                if source_client.needs_unzip or source_client.needs_process:
                    LOGGER.info(f"🔢 Source Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")

                    # Process the Takeout if needed
                    source_client.process(capture_output=show_gpth_info, capture_errors=show_gpth_errors, print_messages=print_messages)

                    # Rebuild the analyzer from the processed folder on disk instead of
                    # the extracted-dates JSON. The JSON tracks physical processed assets,
                    # but it does not include album symlinks/shortcuts created under
                    # Albums, so using it would hide shortcut-only albums from the
                    # migration source view.
                    source_client._ensure_analyzer(log_level=log_level)

            if isinstance(source_client, ClassICloudTakeoutFolder):
                LOGGER.info(f"🔢 Source Folder contains an iCloud Takeout Structure and needs to be processed first. Processing it...")
                source_client.ARGS = dict(source_client.ARGS)
                source_client.ARGS["icloud-include-memories"] = True
                if source_client.ARGS.get("output-folder"):
                    source_client.ARGS["output-folder"] = ""
                    source_client.output_folder = source_client._build_output_folder()
                    source_client.no_albums_folder = source_client.output_folder / source_client.no_albums_folder.name
                    source_client.albums_folder = source_client.output_folder / source_client.albums_folder.name
                    source_client.memories_folder = source_client.output_folder / source_client.memories_folder.name
                source_client.process(log_level=log_level)
                source_client = ClassLocalFolder(base_folder=str(source_client.output_folder))
                source_client_name = source_client.get_client_name()
                SHARED_DATA.info.update({"source_client_name": source_client_name})

            if isinstance(target_client, ClassTakeoutFolder):
                if target_client.needs_unzip or target_client.needs_process:
                    LOGGER.info(f"🔢 Target Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")
                    target_client.process(capture_output=show_gpth_info, capture_errors=show_gpth_errors, print_messages=print_messages)

            if isinstance(target_client, ClassICloudTakeoutFolder):
                LOGGER.info(f"🔢 Target Folder contains an iCloud Takeout Structure and needs to be processed first. Processing it...")
                target_client.ARGS = dict(target_client.ARGS)
                target_client.ARGS["icloud-include-memories"] = True
                if target_client.ARGS.get("output-folder"):
                    target_client.ARGS["output-folder"] = ""
                    target_client.output_folder = target_client._build_output_folder()
                    target_client.no_albums_folder = target_client.output_folder / target_client.no_albums_folder.name
                    target_client.albums_folder = target_client.output_folder / target_client.albums_folder.name
                    target_client.memories_folder = target_client.output_folder / target_client.memories_folder.name
                target_client.process(log_level=log_level)
                target_client = ClassLocalFolder(base_folder=str(target_client.output_folder))
                target_client_name = target_client.get_client_name()
                SHARED_DATA.info.update({"target_client_name": target_client_name})

            # ---------------------------------------------------------------------------------------------------------
            # 4) Ejecutamos la migración en el hilo principal (ya sea con descargas y subidas en paralelo o secuencial)
            # ---------------------------------------------------------------------------------------------------------
            try:
                parallel_automatic_migration(source_client=source_client, target_client=target_client, temp_folder=INTERMEDIATE_FOLDER, SHARED_DATA=SHARED_DATA, parallel=parallel, log_level=log_level)
            except Exception:
                # 1) Mostrar el stack trace completo en stderr (o stdout)
                traceback.print_exc()
                # 2) Registrar en el logger con stack trace
                LOGGER.exception("ERROR executing Automatic Migration Feature")
                sys.exit(1)
            finally:
                migration_finished.set()

            # ---------------------------------------------------------------------------------------------------------
            # 5) Cuando la migración termine, notificamos al show_dashboard
            migration_finished.set()
            # ---------------------------------------------------------------------------------------------------------

            # ---------------------------------------------------------------------------------------------------------
            # 6) Esperamos a que el show_dashboard termine (si sigue corriendo después de la migración)
            # ---------------------------------------------------------------------------------------------------------
            if effective_dashboard:
                dashboard_thread.join()
            if web_dashboard_snapshot_thread is not None:
                web_dashboard_snapshot_thread.join(timeout=1.0)


#########################################
# parallel_automatic_migration Function #
#########################################
# @restore_log_info_on_exception
def parallel_automatic_migration(source_client, target_client, temp_folder, SHARED_DATA, parallel=None, log_level=logging.INFO):
    """
    Sincroniza fotos y vídeos entre un 'source_client' y un 'destination_client',
    descargando álbumes y assets desde la fuente, y luego subiéndolos a destino,
    de forma concurrente mediante una cola de proceso.

    Parámetros:
    -----------
    source_client: objeto con los métodos:
        - get_client_name()
        - get_albums_including_shared_with_user() -> [ { 'id': ..., 'name': ... }, ... ]
        - get_all_assets_from_all_albums() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_without_albums() -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_from_album(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - get_all_assets_from_album_shared(album_id) -> [ { 'id': ..., 'asset_datetime': ..., 'type': ... }, ... ]
        - pull_asset(asset_id, download_path) -> str (ruta local del archivo descargado)

    target_client: objeto con los métodos:
        - get_client_name()
        - album_exists(album_name) -> (bool, album_id_o_None)
        - create_album(album_name) -> album_id
        - add_asset_to_album(album_id, asset_id) -> None
        - push_asset(asset_file_path, asset_datetime) -> asset_id

    temp_folder: str
        Carpeta temporal donde se descargarán los assets antes de subirse.
    """

    # Protector para que no se pisen las actualizaciones de métricas
    metrics_lock = threading.Lock()
    retry_delay_seconds = max(60, int(ARGS.get("push-failed-asset-retry-delay-seconds", 180) or 180))
    # Keep failed uploads in the temp folder by default instead of re-enqueueing them.
    max_push_retries = max(0, int(ARGS.get("push-failed-asset-retries", 0) or 0))
    retry_backoff_factor = max(1, int(ARGS.get("push-failed-asset-retry-backoff-factor", 1) or 1))
    album_assoc_retry_delays_seconds = [2, 5, 10]
    max_album_assoc_retries = min(
        len(album_assoc_retry_delays_seconds),
        max(0, int(ARGS.get("album-association-retries", 0) or 0)),
    )
    default_album_assoc_batch_size = 10 if isinstance(target_client, ClassImmichPhotos) else 100
    album_assoc_batch_size = max(5, int(ARGS.get("album-association-batch-size", default_album_assoc_batch_size) or default_album_assoc_batch_size))
    album_assoc_flush_interval_seconds = max(0.1, float(ARGS.get("album-association-flush-interval-seconds", 0.75) or 0.75))
    defer_album_association_until_album_end = bool(ARGS.get("defer-album-association-until-album-end", True))
    push_queue_priority_enabled = bool(ARGS.get("push-queue-priority-enabled", True))
    retry_heap = []
    retry_condition = threading.Condition()
    retry_sequence = {"value": 0}
    push_queue_sequence = {"value": 0}
    retry_scheduler_stop = threading.Event()
    retries_enabled = max_push_retries > 0 or max_album_assoc_retries > 0

    def _refresh_queue_depth():
        with metrics_lock:
            delayed_assets = int(SHARED_DATA.info.get('delayed_assets_pending', 0) or 0)
            try:
                queue_size = push_queue.qsize()
            except NameError:
                queue_size = 0
            try:
                album_assoc_queue_size = album_assoc_queue.qsize()
            except NameError:
                album_assoc_queue_size = 0
            SHARED_DATA.info['assets_in_queue'] = queue_size + album_assoc_queue_size + delayed_assets

    class MonitoredQueue(Queue):
        def put(self, item, *args, **kwargs):
            super().put(item, *args, **kwargs)
            _refresh_queue_depth()

        def get(self, *args, **kwargs):
            item = super().get(*args, **kwargs)
            _refresh_queue_depth()
            return item

    # -------------------------------------------------------------------
    # Variables compartidas para controlar la creación de álbumes
    # -------------------------------------------------------------------
    # Creamos un diccionario created_albums (protegido por candado para evitar condiciones de carrera entre workers) para registrar los albums que ya han sido creados y de este modo evitar que un album se cree 2 o más veces por varios workers en paralelo.
    album_creation_lock = threading.Lock()
    created_albums = {}
    consolidated_album_groups = set()
    processed_albums = set()
    processed_albums_lock = threading.Lock()
    target_album_asset_ids_cache = {}
    target_album_asset_ids_lock = threading.Lock()
    album_assoc_locks = {}
    album_assoc_locks_lock = threading.Lock()
    pending_duplicate_resolution_by_album = {}
    pending_duplicate_resolution_lock = threading.Lock()
    album_finalize_wait_log_by_album = {}
    album_finalize_wait_log_lock = threading.Lock()
    album_finalize_locks = {}
    album_finalize_locks_lock = threading.Lock()
    immich_uploaded_records = []
    immich_uploaded_records_lock = threading.Lock()
    in_flight_asset_paths = set()
    in_flight_asset_paths_lock = threading.Lock()
    consumed_live_companion_paths = set()
    consumed_live_companion_paths_lock = threading.Lock()
    prefer_canonical_album_names = prefer_canonical_album_names_enabled(ARGS)
    consolidate_similar_albums = consolidate_similar_albums_enabled(ARGS)
    target_exact_album_match_case_sensitive = isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos))
    target_existing_albums = None
    if isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos, ClassGooglePhotos, ClassNextCloudPhotos)):
        try:
            target_existing_albums = target_client.get_albums_owned_by_user(filter_assets=False, log_level=logging.ERROR) or []
        except Exception as error:
            LOGGER.warning(f"Could not preload existing target albums for album reuse checks. {error}")
            target_existing_albums = []

    def _get_target_album_assets(target_client, album_id, album_name=None, log_level=logging.ERROR):
        if isinstance(target_client, ClassSynologyPhotos):
            return target_client.get_all_assets_from_album(album_id, album_name, log_level=log_level) or []
        return target_client.get_all_assets_from_album(album_id, log_level=log_level) or []

    def _get_target_album_asset_ids(target_client, album_id, album_name=None, log_level=logging.ERROR):
        assets = _get_target_album_assets(target_client, album_id, album_name=album_name, log_level=log_level)
        return [str(asset.get("id", "")).strip() for asset in assets if str(asset.get("id", "")).strip()]

    def _set_cached_target_album_asset_ids(album_id, asset_ids):
        album_id = str(album_id or "").strip()
        if not album_id:
            return
        normalized = {
            str(asset_id).strip()
            for asset_id in (asset_ids or [])
            if str(asset_id).strip()
        }
        with target_album_asset_ids_lock:
            target_album_asset_ids_cache[album_id] = normalized

    def _get_cached_target_album_asset_ids(album_id, album_name=None, log_level=logging.ERROR):
        album_id = str(album_id or "").strip()
        if not album_id:
            return set()
        with target_album_asset_ids_lock:
            cached = target_album_asset_ids_cache.get(album_id)
            if cached is not None:
                return cached
        asset_ids = set(_get_target_album_asset_ids(
            target_client=target_client,
            album_id=album_id,
            album_name=album_name,
            log_level=log_level,
        ))
        with target_album_asset_ids_lock:
            return target_album_asset_ids_cache.setdefault(album_id, asset_ids)

    def _mark_target_album_asset_present(album_id, asset_id):
        album_id = str(album_id or "").strip()
        asset_id = str(asset_id or "").strip()
        if not album_id or not asset_id:
            return
        with target_album_asset_ids_lock:
            target_album_asset_ids_cache.setdefault(album_id, set()).add(asset_id)

    def _mark_target_album_assets_present(album_id, asset_ids):
        album_id = str(album_id or "").strip()
        if not album_id:
            return
        normalized_ids = {
            str(asset_id).strip()
            for asset_id in (asset_ids or [])
            if str(asset_id).strip()
        }
        if not normalized_ids:
            return
        with target_album_asset_ids_lock:
            target_album_asset_ids_cache.setdefault(album_id, set()).update(normalized_ids)

    def _refresh_target_album_asset_ids(album_id, album_name=None, log_level=logging.ERROR):
        album_id = str(album_id or "").strip()
        if not album_id:
            return set()
        refreshed_asset_ids = {
            str(asset_id).strip()
            for asset_id in _get_target_album_asset_ids(
                target_client=target_client,
                album_id=album_id,
                album_name=album_name,
                log_level=log_level,
            )
            if str(asset_id).strip()
        }
        _set_cached_target_album_asset_ids(album_id, refreshed_asset_ids)
        return refreshed_asset_ids

    def _get_album_association_lock(album_key):
        album_key = str(album_key or "").strip() or "__default__"
        with album_assoc_locks_lock:
            lock = album_assoc_locks.get(album_key)
            if lock is None:
                lock = threading.Lock()
                album_assoc_locks[album_key] = lock
            return lock

    def _get_album_finalize_lock(album_key):
        album_key = str(album_key or "").strip() or "__default__"
        with album_finalize_locks_lock:
            lock = album_finalize_locks.get(album_key)
            if lock is None:
                lock = threading.Lock()
                album_finalize_locks[album_key] = lock
            return lock

    def _remove_target_existing_album(existing_albums, album_id):
        if existing_albums is None:
            return
        album_id = str(album_id or "").strip()
        if not album_id:
            return
        existing_albums[:] = [
            album for album in existing_albums
            if str((album or {}).get("id", "")).strip() != album_id
        ]

    def _ensure_target_album_ready(album_name, worker_id=1, album_is_shared=False, log_level=logging.ERROR):
        with album_creation_lock:
            if album_name not in created_albums:
                aid = None
                exists = False
                if isinstance(target_client, ClassLocalFolder):
                    exists, aid = target_client.album_exists(
                        album_name=album_name,
                        shared=album_is_shared,
                        log_level=log_level,
                    )
                else:
                    exists, aid = target_client.album_exists(album_name=album_name, log_level=log_level)
                if not exists and isinstance(target_client, ClassLocalFolder):
                    aid = target_client.create_album(
                        album_name=album_name,
                        shared=album_is_shared,
                        log_level=log_level,
                    )
                elif not exists:
                    aid = target_client.create_album(album_name=album_name, log_level=log_level)
                if not exists and aid:
                    LOGGER.info(f"Album Created   : '{album_name}' by worker={worker_id}")
                    if target_existing_albums is not None:
                        target_existing_albums.append({"id": aid, "albumName": album_name})
                    _set_cached_target_album_asset_ids(aid, set())
                created_albums[album_name] = aid
        album_id_dest = created_albums.get(album_name)
        return album_id_dest, album_name

    def _cleanup_local_artifacts(asset_file_path, live_photo_video_path=None):
        safe_remove_local_file(asset_file_path)
        if live_photo_video_path:
            safe_remove_local_file(live_photo_video_path)

    def _finalize_asset_success(
        source_asset_id,
        asset_file_path,
        live_photo_video_path,
        album_name,
        asset_id,
        retry_attempt,
        association_retry_attempt,
        asset_type,
        count_push_stats,
        move_assets,
        removed_source_asset_ids,
        processed_albums,
        processed_albums_lock,
        worker_id,
        logger,
        cleanup_delay_seconds=0.0,
    ):
        cleanup_started_at = time.perf_counter()
        if cleanup_delay_seconds > 0:
            time.sleep(cleanup_delay_seconds)
        if move_assets and source_asset_id and source_asset_id not in removed_source_asset_ids and asset_id:
            _remove_source_asset_after_move(
                source_client=source_client,
                asset_id=source_asset_id,
                log_level=log_level,
            )
            removed_source_asset_ids.add(source_asset_id)
        _cleanup_local_artifacts(asset_file_path, live_photo_video_path)
        if retry_attempt > 0:
            SHARED_DATA.counters['total_push_retry_recovered_assets'] += 1
        if association_retry_attempt > 0:
            SHARED_DATA.counters['total_album_assoc_retry_recovered_assets'] += 1
        if album_name:
            _maybe_finalize_album(
                album_name=album_name,
                removed_source_asset_ids=removed_source_asset_ids,
                processed_albums=processed_albums,
                processed_albums_lock=processed_albums_lock,
                worker_id=worker_id,
                logger=logger,
                log_level=log_level,
            )
        return (time.perf_counter() - cleanup_started_at) * 1000.0

    def _upsert_target_existing_album(existing_albums, album_id, album_name):
        if existing_albums is None or not album_id:
            return
        _remove_target_existing_album(existing_albums, album_id)
        existing_albums.append({"id": album_id, "albumName": album_name})

    def _consolidate_album_group_for_reuse(album_name, worker_id=1, log_level=logging.ERROR):
        if not consolidate_similar_albums or not isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos, ClassGooglePhotos, ClassNextCloudPhotos)):
            matched_album, match_kind, ambiguous_matches = find_reusable_album_candidate(
                album_name=album_name,
                albums=target_existing_albums,
                allow_similar=False,
                exact_case_sensitive=target_exact_album_match_case_sensitive,
            )
            return matched_album, match_kind, ambiguous_matches

        plan = build_reusable_album_group(
            album_name=album_name,
            albums=target_existing_albums,
            allow_similar=True,
            exact_case_sensitive=target_exact_album_match_case_sensitive,
        )
        group_key = str(plan.get("similarity_key") or "").strip()
        keeper_album = plan.get("keeper_album")
        preferred_album_name = str(plan.get("preferred_album_name") or album_name).strip() or album_name

        if group_key and group_key not in consolidated_album_groups:
            keeper_id = str((keeper_album or {}).get("id", "")).strip() if keeper_album else ""
            keeper_name = str((keeper_album or {}).get("albumName", "")).strip() if keeper_album else ""

            if not keeper_id or str(keeper_name).casefold() != preferred_album_name.casefold():
                keeper_id = target_client.create_album(album_name=preferred_album_name, log_level=log_level)
                if keeper_id:
                    keeper_name = preferred_album_name
                    keeper_album = {"id": keeper_id, "albumName": keeper_name}
                    LOGGER.info(f"Album Created   : '{keeper_name}' by pusher_worker={worker_id}")
                    _upsert_target_existing_album(target_existing_albums, keeper_id, keeper_name)

            if keeper_id:
                keeper_asset_ids = None
                all_redundant = list(plan.get("similar_albums") or [])
                for redundant_album in all_redundant:
                    redundant_id = str((redundant_album or {}).get("id", "")).strip()
                    redundant_name = str((redundant_album or {}).get("albumName", "")).strip()
                    if not redundant_id or redundant_id == keeper_id:
                        continue

                    duplicate_asset_ids = _get_target_album_asset_ids(
                        target_client=target_client,
                        album_id=redundant_id,
                        album_name=redundant_name,
                        log_level=log_level,
                    )
                    total_redundant_assets = len(duplicate_asset_ids)
                    reassigned_count = 0
                    should_remove_redundant = False
                    if duplicate_asset_ids:
                        added_count = target_client.add_assets_to_album(
                            album_id=keeper_id,
                            asset_ids=duplicate_asset_ids,
                            album_name=keeper_name,
                            log_level=log_level,
                        )
                        if isinstance(added_count, int) and added_count >= 1:
                            _set_cached_target_album_asset_ids(
                                keeper_id,
                                _get_cached_target_album_asset_ids(
                                    keeper_id,
                                    album_name=keeper_name,
                                    log_level=log_level,
                                ).union(set(duplicate_asset_ids))
                            )
                        if isinstance(target_client, ClassNextCloudPhotos):
                            keeper_assets = _get_target_album_assets(
                                target_client=target_client,
                                album_id=keeper_id,
                                album_name=keeper_name,
                                log_level=log_level,
                            )
                            redundant_assets = _get_target_album_assets(
                                target_client=target_client,
                                album_id=redundant_id,
                                album_name=redundant_name,
                                log_level=log_level,
                            )
                            keeper_name_counts = Counter(
                                str(asset.get("filename", "")).strip()
                                for asset in keeper_assets
                                if str(asset.get("filename", "")).strip()
                            )
                            redundant_name_counts = Counter(
                                str(asset.get("filename", "")).strip()
                                for asset in redundant_assets
                                if str(asset.get("filename", "")).strip()
                            )
                            reassigned_count = sum(
                                min(count, keeper_name_counts.get(filename, 0))
                                for filename, count in redundant_name_counts.items()
                            )
                        else:
                            keeper_asset_ids = set(_get_target_album_asset_ids(
                                target_client=target_client,
                                album_id=keeper_id,
                                album_name=keeper_name,
                                log_level=log_level,
                            ))
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
                        if target_client.remove_album(redundant_id, redundant_name, log_level=log_level):
                            LOGGER.info(
                                f"Album Consolidated: moved reusable/similar album '{redundant_name}' into '{keeper_name}' "
                                f"and removed the redundant album after consolidating {reassigned_count}/{total_redundant_assets} assets."
                            )
                            _remove_target_existing_album(target_existing_albums, redundant_id)
                        elif isinstance(target_client, ClassGooglePhotos):
                            LOGGER.info(
                                f"Album Consolidated: moved reusable/similar album '{redundant_name}' into '{keeper_name}'. "
                                f"All {reassigned_count}/{total_redundant_assets} assets were confirmed in the keeper album, "
                                f"but the redundant album was kept because Google Photos does not support album deletion."
                            )
                    else:
                        LOGGER.warning(
                            f"Album Consolidation Partial: '{redundant_name}' -> '{keeper_name}'. "
                            f"Only {reassigned_count}/{total_redundant_assets} assets were confirmed in the keeper album. "
                            f"The redundant album was kept."
                        )

                consolidated_album_groups.add(group_key)
                created_albums[preferred_album_name] = keeper_id
                if keeper_id and keeper_asset_ids is not None:
                    _set_cached_target_album_asset_ids(keeper_id, keeper_asset_ids)
                for similar_album in plan.get("similar_albums") or []:
                    similar_name = str((similar_album or {}).get("albumName", "")).strip()
                    if similar_name:
                        created_albums[similar_name] = keeper_id
                created_albums[album_name] = keeper_id
                return keeper_album, plan.get("match_kind") or "similar", []

        matched_album = plan.get("matched_album")
        if keeper_album and str((keeper_album or {}).get("id", "")).strip():
            matched_album = keeper_album
        return matched_album, plan.get("match_kind"), []

    def _resolve_duplicate_target_asset_id(asset_file_path, log_level=logging.ERROR):
        resolver = getattr(target_client, "_resolve_existing_asset_id", None)
        if callable(resolver):
            return resolver(asset_file_path, log_level=log_level)
        media_resolver = getattr(target_client, "_resolve_existing_media_item_id", None)
        if callable(media_resolver):
            return media_resolver(file_path=asset_file_path, file_name=os.path.basename(asset_file_path))
        return None

    def _register_pending_duplicate_resolution(album_name, asset):
        album_name = str(album_name or "").strip()
        asset_file_path = str((asset or {}).get("asset_file_path", "") or "").strip()
        if not album_name or not asset_file_path:
            return
        pending_key = path_key(asset_file_path)
        with pending_duplicate_resolution_lock:
            album_pending = pending_duplicate_resolution_by_album.setdefault(album_name, {})
            album_pending[pending_key] = dict(asset)

    def _get_pending_duplicate_resolution_items(album_name):
        album_name = str(album_name or "").strip()
        with pending_duplicate_resolution_lock:
            album_pending = pending_duplicate_resolution_by_album.get(album_name, {})
            return [dict(item) for item in album_pending.values()]

    def _set_pending_duplicate_resolution_items(album_name, items):
        album_name = str(album_name or "").strip()
        with pending_duplicate_resolution_lock:
            if not items:
                pending_duplicate_resolution_by_album.pop(album_name, None)
                return
            pending_duplicate_resolution_by_album[album_name] = {
                path_key(str((item or {}).get("asset_file_path", "") or "")): dict(item)
                for item in items
                if str((item or {}).get("asset_file_path", "") or "").strip()
            }

    def _get_pending_duplicate_file_keys(album_name):
        album_name = str(album_name or "").strip()
        with pending_duplicate_resolution_lock:
            return set((pending_duplicate_resolution_by_album.get(album_name) or {}).keys())

    def _add_assets_to_target_album(album_id_dest, album_name, asset_ids, log_level=logging.ERROR):
        normalized_asset_ids = [
            str(asset_id).strip()
            for asset_id in dict.fromkeys(asset_ids or [])
            if str(asset_id).strip()
        ]
        if not album_id_dest or not normalized_asset_ids:
            return set()

        album_lock = _get_album_association_lock(album_id_dest or album_name)
        with album_lock:
            target_album_asset_ids = _get_cached_target_album_asset_ids(
                album_id=album_id_dest,
                album_name=album_name,
                log_level=log_level,
            )
            already_present_ids = {
                asset_id for asset_id in normalized_asset_ids
                if asset_id in target_album_asset_ids
            }
            ids_to_add = [
                asset_id for asset_id in normalized_asset_ids
                if asset_id not in already_present_ids
            ]
            confirmed_ids = set(already_present_ids)
            if ids_to_add:
                if isinstance(target_client, ClassImmichPhotos):
                    add_result = target_client.add_assets_to_album(
                        album_id=album_id_dest,
                        asset_ids=ids_to_add,
                        album_name=album_name,
                        log_level=log_level,
                        return_details=True,
                    )
                    if isinstance(add_result, dict):
                        confirmed_ids.update({
                            str(asset_id).strip()
                            for asset_id in add_result.get("confirmed_asset_ids", set())
                            if str(asset_id).strip()
                        })
                else:
                    target_client.add_assets_to_album(
                        album_id=album_id_dest,
                        asset_ids=ids_to_add,
                        album_name=album_name,
                        log_level=log_level,
                    )
                    confirmed_ids.update(ids_to_add)

            if isinstance(target_client, ClassImmichPhotos):
                unresolved_ids = [
                    asset_id for asset_id in normalized_asset_ids
                    if asset_id not in confirmed_ids
                ]
                if unresolved_ids:
                    refreshed_ids = _refresh_target_album_asset_ids(
                        album_id=album_id_dest,
                        album_name=album_name,
                        log_level=log_level,
                    )
                    confirmed_ids.update({
                        asset_id for asset_id in unresolved_ids
                        if asset_id in refreshed_ids
                    })
                    unresolved_ids = [
                        asset_id for asset_id in normalized_asset_ids
                        if asset_id not in confirmed_ids
                    ]
                if unresolved_ids:
                    individually_confirmed = set()
                    for unresolved_asset_id in unresolved_ids:
                        add_result = target_client.add_assets_to_album(
                            album_id=album_id_dest,
                            asset_ids=[unresolved_asset_id],
                            album_name=album_name,
                            log_level=log_level,
                            return_details=True,
                        )
                        if isinstance(add_result, dict):
                            individually_confirmed.update({
                                str(asset_id).strip()
                                for asset_id in add_result.get("confirmed_asset_ids", set())
                                if str(asset_id).strip()
                            })
                    if individually_confirmed:
                        confirmed_ids.update(individually_confirmed)
                    unresolved_ids = [
                        asset_id for asset_id in normalized_asset_ids
                        if asset_id not in confirmed_ids
                    ]
                if unresolved_ids:
                    refreshed_ids = _refresh_target_album_asset_ids(
                        album_id=album_id_dest,
                        album_name=album_name,
                        log_level=log_level,
                    )
                    confirmed_ids.update({
                        asset_id for asset_id in unresolved_ids
                        if asset_id in refreshed_ids
                    })

            if confirmed_ids:
                _mark_target_album_assets_present(album_id_dest, confirmed_ids)
            return confirmed_ids

    def _associate_uploaded_asset_to_album(
        asset,
        asset_id,
        album_name,
        album_is_shared=False,
        worker_id=1,
        removed_source_asset_ids=None,
        processed_albums=None,
        processed_albums_lock=None,
        log_level=logging.INFO,
    ):
        removed_source_asset_ids = removed_source_asset_ids if removed_source_asset_ids is not None else set()
        processed_albums = processed_albums if processed_albums is not None else set()
        processed_albums_lock = processed_albums_lock if processed_albums_lock is not None else threading.Lock()

        assoc_started_at = time.perf_counter()
        asset_id = str(asset_id or "").strip()
        if not asset_id or not album_name:
            return False, 0.0, None, False

        try:
            album_id_dest, album_name_to_query = _ensure_target_album_ready(
                album_name=album_name,
                worker_id=worker_id,
                album_is_shared=album_is_shared,
                log_level=logging.ERROR,
            )
            confirmed_ids = _add_assets_to_target_album(
                album_id_dest=album_id_dest,
                album_name=album_name_to_query,
                asset_ids=[asset_id],
                log_level=logging.ERROR,
            )
            assoc_elapsed_ms = (time.perf_counter() - assoc_started_at) * 1000.0
            if asset_id in confirmed_ids:
                _mark_target_album_asset_present(album_id_dest, asset_id)
                cleanup_elapsed_ms = _finalize_asset_success(
                    source_asset_id=asset.get("asset_id"),
                    asset_file_path=asset.get("asset_file_path"),
                    live_photo_video_path=asset.get("live_photo_video_path"),
                    album_name=album_name,
                    asset_id=asset_id,
                    retry_attempt=int(asset.get("retry_attempt", 0) or 0),
                    association_retry_attempt=int(asset.get("album_assoc_retry_attempt", 0) or 0),
                    asset_type=asset.get("asset_type", "photo"),
                    count_push_stats=asset.get("count_push_stats", True),
                    move_assets=ARGS.get('move-assets', None),
                    removed_source_asset_ids=removed_source_asset_ids,
                    processed_albums=processed_albums,
                    processed_albums_lock=processed_albums_lock,
                    worker_id=worker_id,
                    logger=LOGGER,
                )
                return True, assoc_elapsed_ms, cleanup_elapsed_ms, False

            LOGGER.warning(
                f"Album association was not confirmed by target for asset "
                f"'{os.path.basename(asset.get('asset_file_path', ''))}' into album '{album_name}'. "
                f"The asset may already belong to that album or the target may have rejected it."
            )
            scheduled_retry = False
            if isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos)):
                scheduled_retry = _schedule_album_association_retry(
                    asset=asset,
                    reason=f"album association to '{album_name}' was not confirmed",
                    resolved_target_asset_id=asset_id,
                )
            if not scheduled_retry:
                deferred_asset = dict(asset or {})
                deferred_asset["resolved_target_asset_id"] = asset_id
                _register_pending_duplicate_resolution(album_name=album_name, asset=deferred_asset)
            return False, assoc_elapsed_ms, None, scheduled_retry
        except Exception as e:
            assoc_elapsed_ms = (time.perf_counter() - assoc_started_at) * 1000.0
            scheduled_retry = _schedule_album_association_retry(
                asset=asset,
                reason=f"album association exception for '{album_name}': {str(e)}",
                resolved_target_asset_id=asset_id,
            )
            if not scheduled_retry:
                deferred_asset = dict(asset or {})
                deferred_asset["resolved_target_asset_id"] = asset_id
                _register_pending_duplicate_resolution(album_name=album_name, asset=deferred_asset)
                LOGGER.error(
                    f"Album Association Exception: asset '{os.path.basename(asset.get('asset_file_path', ''))}' "
                    f"into album '{album_name}' - {e}"
                )
            return False, assoc_elapsed_ms, None, scheduled_retry

    def _finalize_canonical_album_name(album_name, worker_id=1, log_level=logging.ERROR):
        if not prefer_canonical_album_names:
            return
        if consolidate_similar_albums:
            return
        if not isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos, ClassGooglePhotos, ClassNextCloudPhotos)):
            return

        preferred_album_name = str(canonicalize_album_name_for_reuse(album_name) or album_name).strip() or album_name
        if preferred_album_name.casefold() == str(album_name or "").strip().casefold():
            return

        source_album_id = str(created_albums.get(album_name) or "").strip()
        if not source_album_id:
            return

        exists, keeper_id = target_client.album_exists(album_name=preferred_album_name, log_level=log_level)
        if not exists:
            keeper_id = target_client.create_album(album_name=preferred_album_name, log_level=log_level)
            if keeper_id:
                LOGGER.info(f"Album Created   : '{preferred_album_name}' by worker={worker_id}")
                if target_existing_albums is not None:
                    _upsert_target_existing_album(target_existing_albums, keeper_id, preferred_album_name)
                _set_cached_target_album_asset_ids(keeper_id, set())
        if not keeper_id or str(keeper_id).strip() == source_album_id:
            created_albums[album_name] = source_album_id
            return

        source_asset_ids = sorted(_get_cached_target_album_asset_ids(
            album_id=source_album_id,
            album_name=album_name,
            log_level=log_level,
        ))
        if source_asset_ids:
            _add_assets_to_target_album(
                album_id_dest=keeper_id,
                album_name=preferred_album_name,
                asset_ids=source_asset_ids,
                log_level=log_level,
            )

        if isinstance(target_client, ClassGooglePhotos):
            LOGGER.info(
                f"Album Canonicalization: copied assets from '{album_name}' into canonical album "
                f"'{preferred_album_name}'. The original album is kept because Google Photos cannot delete albums."
            )
        else:
            removed = target_client.remove_album(source_album_id, album_name, log_level=log_level)
            if removed:
                LOGGER.info(
                    f"Album Canonicalization: moved assets from '{album_name}' into canonical album "
                    f"'{preferred_album_name}' and removed the original album."
                )
                if target_existing_albums is not None:
                    _remove_target_existing_album(target_existing_albums, source_album_id)
            else:
                LOGGER.warning(
                    f"Album Canonicalization Partial: copied assets from '{album_name}' into "
                    f"'{preferred_album_name}', but the original album could not be removed."
                )

        created_albums[preferred_album_name] = keeper_id
        created_albums[album_name] = keeper_id

    def _apply_final_album_naming(album_name, worker_id=1, log_level=logging.ERROR):
        if consolidate_similar_albums:
            _consolidate_album_group_for_reuse(
                album_name=album_name,
                worker_id=worker_id,
                log_level=log_level,
            )
            return
        _finalize_canonical_album_name(
            album_name=album_name,
            worker_id=worker_id,
            log_level=log_level,
        )

    def _list_album_remaining_files(album_folder_path):
        remaining_files = []
        if not os.path.isdir(album_folder_path):
            return remaining_files
        for entry in os.listdir(album_folder_path):
            if entry == ".active" or entry.endswith(".lock"):
                continue
            full_path = os.path.join(album_folder_path, entry)
            if os.path.isfile(full_path):
                remaining_files.append(full_path)
        return remaining_files

    def _format_album_pending_context(album_name, current_asset_file_path=None):
        if not album_name:
            return ""
        album_folder_path = os.path.join(temp_folder, album_name)
        if not os.path.isdir(album_folder_path):
            return f" (Album: '{album_name}')"

        remaining_files = _list_album_remaining_files(album_folder_path)
        pending_duplicate_keys = _get_pending_duplicate_file_keys(album_name)
        current_asset_key = path_key(current_asset_file_path) if current_asset_file_path else None
        pending_count = 0

        for file_path in remaining_files:
            file_key = path_key(file_path)
            if file_key == current_asset_key:
                continue
            if file_key in pending_duplicate_keys:
                continue
            pending_count += 1

        if pending_count > 0:
            return f" (Album: '{album_name}' - {pending_count} pending file(s) in queue)"
        return f" (Album: '{album_name}')"

    def _maybe_finalize_album(album_name, removed_source_asset_ids=None, processed_albums=None, processed_albums_lock=None, worker_id=1, logger=LOGGER, log_level=logging.ERROR):
        if not album_name:
            return False
        removed_source_asset_ids = removed_source_asset_ids if removed_source_asset_ids is not None else set()
        processed_albums = processed_albums if processed_albums is not None else set()
        processed_albums_lock = processed_albums_lock if processed_albums_lock is not None else threading.Lock()
        album_folder_path = os.path.join(temp_folder, album_name)
        finalize_lock = _get_album_finalize_lock(album_name)

        def _log_finalize_wait(reason):
            return

        with finalize_lock:
            with processed_albums_lock:
                if album_name in processed_albums:
                    return False

            if not os.path.isdir(album_folder_path):
                return False

            active_file = os.path.join(album_folder_path, ".active")
            if os.path.exists(active_file):
                _log_finalize_wait("album still active")
                return False

            remaining_files = _list_album_remaining_files(album_folder_path)
            pending_duplicate_items = _get_pending_duplicate_resolution_items(album_name)
            pending_duplicate_keys = _get_pending_duplicate_file_keys(album_name)
            non_pending_files = [
                file_path for file_path in remaining_files
                if path_key(file_path) not in pending_duplicate_keys
            ]
            if non_pending_files:
                _log_finalize_wait(f"{len(non_pending_files)} pending file(s) in queue")
                return False

            if pending_duplicate_items:
                resolved_items = []
                unresolved_items = []
                resolved_asset_ids = []
                for item in pending_duplicate_items:
                    resolved_target_asset_id = str(item.get("resolved_target_asset_id") or "").strip()
                    if not resolved_target_asset_id:
                        resolved_target_asset_id = _resolve_duplicate_target_asset_id(
                            asset_file_path=item.get("asset_file_path"),
                            log_level=log_level,
                        )
                    if resolved_target_asset_id:
                        item["resolved_target_asset_id"] = resolved_target_asset_id
                        resolved_items.append(item)
                        resolved_asset_ids.append(resolved_target_asset_id)
                    else:
                        if not item.get("_final_resolution_counted"):
                            SHARED_DATA.counters['total_album_assoc_unconfirmed_assets'] += 1
                            item["_final_resolution_counted"] = True
                        unresolved_items.append(item)
                        logger.error(
                            f"Album Association Unconfirmed: '{os.path.basename(item.get('asset_file_path', ''))}' "
                            f"could not resolve an existing target asset id during album finalization for '{album_name}'."
                        )

                if unresolved_items:
                    _set_pending_duplicate_resolution_items(album_name, unresolved_items)
                else:
                    _set_pending_duplicate_resolution_items(album_name, [])

                if resolved_items:
                    album_id_dest, album_name_to_query = _ensure_target_album_ready(
                        album_name=album_name,
                        worker_id=worker_id,
                        album_is_shared=any(bool(item.get("album_is_shared")) for item in resolved_items),
                        log_level=log_level,
                    )
                    confirmed_ids = _add_assets_to_target_album(
                        album_id_dest=album_id_dest,
                        album_name=album_name_to_query,
                        asset_ids=resolved_asset_ids,
                        log_level=log_level,
                    )
                    for item in resolved_items:
                        target_asset_id = str(item.get("resolved_target_asset_id") or "").strip()
                        if target_asset_id not in confirmed_ids:
                            unresolved_items.append(item)
                            continue
                        _finalize_asset_success(
                            source_asset_id=item.get("asset_id"),
                            asset_file_path=item.get("asset_file_path"),
                            live_photo_video_path=item.get("live_photo_video_path"),
                            album_name=None,
                            asset_id=target_asset_id,
                            retry_attempt=int(item.get("retry_attempt", 0) or 0),
                            association_retry_attempt=int(item.get("album_assoc_retry_attempt", 0) or 0),
                            asset_type=item.get("asset_type", "photo"),
                            count_push_stats=item.get("count_push_stats", True),
                            move_assets=ARGS.get('move-assets', None),
                            removed_source_asset_ids=removed_source_asset_ids,
                            processed_albums=processed_albums,
                            processed_albums_lock=processed_albums_lock,
                            worker_id=worker_id,
                            logger=logger,
                        )
                    if unresolved_items:
                        _set_pending_duplicate_resolution_items(album_name, unresolved_items)
                        _log_finalize_wait(f"{len(unresolved_items)} pending duplicate resolution item(s)")
                        return False

            if _list_album_remaining_files(album_folder_path):
                _log_finalize_wait(
                    _album_finalize_wait_reason(
                        album_folder_path=album_folder_path,
                        pending_duplicate_keys=_get_pending_duplicate_file_keys(album_name),
                    )
                )
                return False

            _apply_final_album_naming(
                album_name=album_name,
                worker_id=worker_id,
                log_level=log_level,
            )

            return _mark_album_pushed_if_ready(
                album_name=album_name,
                album_folder_path=album_folder_path,
                processed_albums=processed_albums,
                processed_albums_lock=processed_albums_lock,
                counters=SHARED_DATA.counters,
                logger=logger,
            )

    def _record_final_push_failure(asset_type, count_push_stats):
        if count_push_stats:
            SHARED_DATA.counters['total_push_failed_assets'] += 1
            if asset_type.lower() in video_labels:
                SHARED_DATA.counters['total_push_failed_videos'] += 1
            else:
                SHARED_DATA.counters['total_push_failed_photos'] += 1

    NO_RETRY_LARGE_ASSET_BYTES = 50 * 1024 * 1024

    def _compute_push_retry_delay_seconds(retry_attempt):
        exponent = max(0, int(retry_attempt) - 1)
        return int(retry_delay_seconds * (retry_backoff_factor ** exponent))

    def _schedule_asset_retry(asset, reason, resolved_target_asset_id=None, skip_target_push=False):
        if max_push_retries <= 0:
            return False

        asset_file_path = str((asset or {}).get('asset_file_path', '') or '').strip()
        if asset_file_path:
            try:
                asset_size = os.path.getsize(asset_file_path) if os.path.exists(asset_file_path) else 0
            except Exception:
                asset_size = 0
            if asset_size > NO_RETRY_LARGE_ASSET_BYTES:
                LOGGER.warning(
                    f"Asset Retry Skipped: '{os.path.basename(asset_file_path)}' exceeds "
                    f"{NO_RETRY_LARGE_ASSET_BYTES // (1024 * 1024)} MB ({asset_size / (1024 * 1024):.1f} MB). "
                    f"Reason: {reason}"
                )
                return False

        current_attempt = int(asset.get('retry_attempt', 0) or 0)
        next_attempt = current_attempt + 1
        if next_attempt > max_push_retries:
            return False

        retry_asset = dict(asset)
        retry_asset['retry_attempt'] = next_attempt
        if resolved_target_asset_id:
            retry_asset['resolved_target_asset_id'] = resolved_target_asset_id
            retry_asset['skip_target_push'] = bool(skip_target_push)
        else:
            retry_asset.pop('resolved_target_asset_id', None)
            retry_asset.pop('skip_target_push', None)

        delay_seconds = _compute_push_retry_delay_seconds(next_attempt)
        ready_at = time.time() + delay_seconds

        with retry_condition:
            retry_sequence['value'] += 1
            heapq.heappush(retry_heap, (ready_at, retry_sequence['value'], retry_asset))
            SHARED_DATA.info['delayed_assets_pending'] = len(retry_heap)
            retry_condition.notify_all()
        _refresh_queue_depth()

        SHARED_DATA.counters['total_push_retry_scheduled_assets'] += 1
        LOGGER.warning(
            f"Asset Retry Delayed: '{os.path.basename(asset.get('asset_file_path', ''))}' "
            f"attempt {next_attempt}/{max_push_retries} scheduled in {delay_seconds}s. Reason: {reason}"
        )
        return True

    def _schedule_album_association_retry(asset, reason, resolved_target_asset_id):
        if not resolved_target_asset_id or max_album_assoc_retries <= 0:
            return False

        current_attempt = int((asset or {}).get('album_assoc_retry_attempt', 0) or 0)
        next_attempt = current_attempt + 1
        if next_attempt > max_album_assoc_retries:
            SHARED_DATA.counters['total_album_assoc_unconfirmed_assets'] += 1
            LOGGER.error(
                f"Album Association Unconfirmed: '{os.path.basename((asset or {}).get('asset_file_path', ''))}' "
                f"exhausted {max_album_assoc_retries} verification attempt(s). Reason: {reason}"
            )
            return False

        retry_asset = dict(asset or {})
        retry_asset['resolved_target_asset_id'] = resolved_target_asset_id
        retry_asset['skip_target_push'] = True
        retry_asset['album_assoc_retry_attempt'] = next_attempt
        retry_asset['retry_kind'] = 'album_assoc'
        retry_asset.pop('retry_attempt', None)

        delay_seconds = album_assoc_retry_delays_seconds[next_attempt - 1]
        ready_at = time.time() + delay_seconds

        with retry_condition:
            retry_sequence['value'] += 1
            heapq.heappush(retry_heap, (ready_at, retry_sequence['value'], retry_asset))
            SHARED_DATA.info['delayed_assets_pending'] = len(retry_heap)
            retry_condition.notify_all()
        _refresh_queue_depth()

        SHARED_DATA.counters['total_album_assoc_retry_scheduled_assets'] += 1
        LOGGER.warning(
            f"Album Association Retry Delayed: '{os.path.basename((asset or {}).get('asset_file_path', ''))}' "
            f"attempt {next_attempt}/{max_album_assoc_retries} scheduled in {delay_seconds}s. Reason: {reason}"
        )
        return True

    def retry_scheduler_worker(log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):
            while True:
                with retry_condition:
                    while not retry_heap and not retry_scheduler_stop.is_set():
                        retry_condition.wait(timeout=1.0)
                    if retry_scheduler_stop.is_set() and not retry_heap:
                        break
                    if not retry_heap:
                        continue
                    ready_at, _, retry_asset = retry_heap[0]
                    now = time.time()
                    if ready_at > now:
                        retry_condition.wait(timeout=min(1.0, ready_at - now))
                        continue
                    heapq.heappop(retry_heap)
                    SHARED_DATA.info['delayed_assets_pending'] = len(retry_heap)
                _refresh_queue_depth()
                _push_queue_put(retry_asset)
                retry_kind = str(retry_asset.get('retry_kind') or 'push').strip().lower()
                if retry_kind == 'album_assoc':
                    LOGGER.info(
                        f"Album Association Retry Enqueued: '{os.path.basename(retry_asset.get('asset_file_path', ''))}' "
                        f"attempt {retry_asset.get('album_assoc_retry_attempt', 0)}/{max_album_assoc_retries}"
                    )
                else:
                    LOGGER.info(
                        f"Asset Retry Enqueued: '{os.path.basename(retry_asset.get('asset_file_path', ''))}' "
                        f"attempt {retry_asset.get('retry_attempt', 0)}/{max_push_retries}"
                    )

    def _flush_album_association_batch(
        album_name,
        batch_items,
        worker_id=1,
        removed_source_asset_ids=None,
        processed_albums=None,
        processed_albums_lock=None,
        log_level=logging.INFO,
    ):
        if not batch_items:
            return
        removed_source_asset_ids = removed_source_asset_ids if removed_source_asset_ids is not None else set()
        processed_albums = processed_albums if processed_albums is not None else set()
        processed_albums_lock = processed_albums_lock if processed_albums_lock is not None else threading.Lock()

        album_is_shared = any(bool(item.get("album_is_shared")) for item in batch_items)
        album_assoc_started_at = time.perf_counter()
        album_id_dest = None
        album_name_to_query = album_name
        try:
            album_id_dest, album_name_to_query = _ensure_target_album_ready(
                album_name=album_name,
                worker_id=worker_id,
                album_is_shared=album_is_shared,
                log_level=logging.ERROR,
            )

            normalized_items = []
            for item in batch_items:
                target_asset_id = str(item.get("resolved_target_asset_id") or "").strip()
                if not target_asset_id:
                    continue
                normalized_items.append((item, target_asset_id))

            if not normalized_items:
                return
            requested_asset_ids = [asset_id for _, asset_id in normalized_items]
            confirmed_ids = _add_assets_to_target_album(
                album_id_dest=album_id_dest,
                album_name=album_name_to_query,
                asset_ids=requested_asset_ids,
                log_level=logging.ERROR,
            )
            final_missing_ids = [
                asset_id for _, asset_id in normalized_items
                if asset_id not in confirmed_ids
            ]
            LOGGER.debug(
                f"Album Association Batch: album='{album_name}' worker={worker_id} "
                f"requested={len(normalized_items)} confirmed={len(confirmed_ids)} "
                f"missing={len(final_missing_ids)}"
            )

            album_assoc_elapsed_ms = (time.perf_counter() - album_assoc_started_at) * 1000.0
            for item, target_asset_id in normalized_items:
                asset_started_at = item.get("asset_started_at_perf") or time.perf_counter()
                push_elapsed_ms = item.get("push_elapsed_ms")
                queue_wait_ms = item.get("queue_wait_ms")
                assoc_queue_wait_ms = None
                assoc_enqueued_at = item.get("album_assoc_enqueued_at_monotonic")
                if isinstance(assoc_enqueued_at, (int, float)):
                    assoc_queue_wait_ms = max(0.0, (album_assoc_started_at - float(assoc_enqueued_at)) * 1000.0)
                asset_confirmed = target_asset_id in confirmed_ids
                cleanup_elapsed_ms = None
                scheduled_retry = False

                if asset_confirmed:
                    _mark_target_album_asset_present(album_id_dest, target_asset_id)
                    cleanup_elapsed_ms = _finalize_asset_success(
                        source_asset_id=item.get("asset_id"),
                        asset_file_path=item.get("asset_file_path"),
                        live_photo_video_path=item.get("live_photo_video_path"),
                        album_name=album_name,
                        asset_id=target_asset_id,
                        retry_attempt=int(item.get("retry_attempt", 0) or 0),
                        association_retry_attempt=int(item.get("album_assoc_retry_attempt", 0) or 0),
                        asset_type=item.get("asset_type", "photo"),
                        count_push_stats=item.get("count_push_stats", True),
                        move_assets=ARGS.get('move-assets', None),
                        removed_source_asset_ids=removed_source_asset_ids,
                        processed_albums=processed_albums,
                        processed_albums_lock=processed_albums_lock,
                        worker_id=worker_id,
                        logger=LOGGER,
                    )
                else:
                    LOGGER.warning(
                        f"Album association was not confirmed by target for asset '{os.path.basename(item.get('asset_file_path', ''))}' "
                        f"into album '{album_name}'. The asset may already belong to that album or the target may have rejected it."
                    )
                    if isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos)):
                        scheduled_retry = _schedule_album_association_retry(
                            asset=item,
                            reason=f"album association to '{album_name}' was not confirmed",
                            resolved_target_asset_id=target_asset_id,
                        )

                _debug_perf_log(
                    LOGGER,
                    "automatic_migration.asset.pipeline",
                    asset_started_at,
                    worker=item.get("worker_id"),
                    album=album_name or "-",
                    asset=os.path.basename(item.get("asset_file_path", "")),
                    source_asset_id=item.get("asset_id"),
                    queue_wait_ms=f"{queue_wait_ms:.2f}" if isinstance(queue_wait_ms, (int, float)) else None,
                    album_queue_wait_ms=f"{assoc_queue_wait_ms:.2f}" if isinstance(assoc_queue_wait_ms, (int, float)) else None,
                    push_ms=f"{push_elapsed_ms:.2f}" if isinstance(push_elapsed_ms, (int, float)) else None,
                    album_assoc_ms=f"{album_assoc_elapsed_ms:.2f}",
                    cleanup_ms=f"{cleanup_elapsed_ms:.2f}" if isinstance(cleanup_elapsed_ms, (int, float)) else None,
                    duplicated=item.get("isDuplicated", False),
                    asset_pushed=item.get("asset_pushed", False),
                    consumed=item.get("treat_as_consumed", False),
                    album_association_confirmed=asset_confirmed,
                    scheduled_retry=scheduled_retry,
                    batch_size=len(normalized_items),
                )
        except Exception as e:
            for item in batch_items:
                target_asset_id = item.get("resolved_target_asset_id")
                scheduled_retry = _schedule_album_association_retry(
                    asset=item,
                    reason=f"album association exception for '{album_name}': {str(e)}",
                    resolved_target_asset_id=target_asset_id,
                )
                if not scheduled_retry:
                    LOGGER.error(f"Album Push Fail : '{album_name}'")
                    LOGGER.error(f"Caught Exception: {str(e)}\n{traceback.format_exc()}")
                    SHARED_DATA.counters['total_push_failed_albums'] += 1

    def album_association_worker(processed_albums=None, processed_albums_lock=None, worker_id=1, log_level=logging.INFO):
        if processed_albums is None:
            processed_albums = set()
        if processed_albums_lock is None:
            processed_albums_lock = threading.Lock()
        removed_source_asset_ids = set()
        pending_by_album = {}
        pending_order = []
        completed_album_keys = set()
        stop_requested = False

        def flush_ready(force=False):
            nonlocal pending_order
            now = time.perf_counter()
            remaining_order = []
            for album_key in pending_order:
                state = pending_by_album.get(album_key)
                if not state:
                    continue
                if defer_album_association_until_album_end:
                    album_is_complete = bool(state.get("album_complete")) or album_key in completed_album_keys
                    if force:
                        album_is_complete = True
                    if not album_is_complete:
                        remaining_order.append(album_key)
                        continue
                    while state["items"]:
                        batch_items = state["items"][:album_assoc_batch_size]
                        state["items"] = state["items"][album_assoc_batch_size:]
                        _flush_album_association_batch(
                            album_name=album_key,
                            batch_items=batch_items,
                            worker_id=worker_id,
                            removed_source_asset_ids=removed_source_asset_ids,
                            processed_albums=processed_albums,
                            processed_albums_lock=processed_albums_lock,
                            log_level=log_level,
                        )
                        for _ in batch_items:
                            album_assoc_queue.task_done()
                    pending_by_album.pop(album_key, None)
                else:
                    should_flush = force or len(state["items"]) >= album_assoc_batch_size or (now - state["first_enqueued_at"]) >= album_assoc_flush_interval_seconds
                    if should_flush:
                        batch_items = state["items"]
                        pending_by_album.pop(album_key, None)
                        _flush_album_association_batch(
                            album_name=album_key,
                            batch_items=batch_items,
                            worker_id=worker_id,
                            removed_source_asset_ids=removed_source_asset_ids,
                            processed_albums=processed_albums,
                            processed_albums_lock=processed_albums_lock,
                            log_level=log_level,
                        )
                        for _ in batch_items:
                            album_assoc_queue.task_done()
                    else:
                        remaining_order.append(album_key)
            pending_order = remaining_order

        with set_log_level(LOGGER, log_level):
            while True:
                try:
                    item = album_assoc_queue.get(timeout=album_assoc_flush_interval_seconds)
                except Empty:
                    flush_ready(force=False)
                    if stop_requested and not pending_by_album:
                        break
                    continue

                if item is None:
                    album_assoc_queue.task_done()
                    stop_requested = True
                    flush_ready(force=True)
                    if not pending_by_album:
                        break
                    continue

                if item.get("_album_done"):
                    album_key = item.get("album_name") or ""
                    completed_album_keys.add(album_key)
                    state = pending_by_album.get(album_key)
                    if state is None:
                        state = {"items": [], "first_enqueued_at": time.perf_counter(), "album_complete": True}
                        pending_by_album[album_key] = state
                        pending_order.append(album_key)
                    else:
                        state["album_complete"] = True
                    album_assoc_queue.task_done()
                    flush_ready(force=False)
                    if stop_requested and not pending_by_album:
                        break
                    continue

                album_key = item.get("album_name") or ""
                state = pending_by_album.get(album_key)
                if state is None:
                    state = {
                        "items": [],
                        "first_enqueued_at": time.perf_counter(),
                        "album_complete": album_key in completed_album_keys,
                    }
                    pending_by_album[album_key] = state
                    pending_order.append(album_key)
                state["items"].append(item)
                flush_ready(force=False)

            flush_ready(force=True)
            LOGGER.info(f"Album Association Worker {worker_id} - Task Finished!")

    def _wait_until_push_pipeline_drains():
        while True:
            push_queue.join()
            album_assoc_queue.join()
            with retry_condition:
                retries_pending = len(retry_heap)
            if retries_pending == 0 and push_queue.qsize() == 0 and album_assoc_queue.qsize() == 0:
                break
            time.sleep(0.25)

    def _get_push_queue_priority(item):
        if not push_queue_priority_enabled:
            return 0
        if item is None:
            return 99
        asset_type = str((item or {}).get("asset_type", "") or "").strip().lower()
        if asset_type in video_labels:
            return 10
        return 0

    def _push_queue_put(item):
        with retry_condition:
            push_queue_sequence["value"] += 1
            sequence = push_queue_sequence["value"]
        push_queue.put((_get_push_queue_priority(item), sequence, item))

    def _push_queue_get():
        _, _, item = push_queue.get()
        return item

    # ----------------------------------------------------------------------------------------
    # function to ensure that the puller put only 1 asset with the same filepath to the queue
    # ----------------------------------------------------------------------------------------
    def enqueue_unique(push_queue, item_dict, parallel=True):
        """
        Añade item_dict a la cola si su asset_file_path no ha sido añadido previamente.
        Thread-safe gracias al lock global.
        """
        with file_paths_lock:
            asset_file_path = item_dict['asset_file_path']
            asset_file_key = _normalized_asset_path_key(asset_file_path)
            _refresh_queue_depth()

            if asset_file_key in added_file_paths:
                # El item ya fue añadido anteriormente
                return False

            # If parallel mode, then manage waiting time to avoid queue size go beyond 100 elements.
            if parallel:
                # Pausa si la cola tiene más de 100 elementos, pero no bloquea innecesariamente, y reanuda cuando tenga 10.
                while push_queue.qsize() >= 100:
                    while push_queue.qsize() > 25:
                        time.sleep(1)  # Hacemos pausas de 1s hasta que la cola se vacíe (25 elementos)
                        # SHARED_DATA.info['assets_in_queue'] = push_queue.qsize()

                # Si la cola está muy llena (entre 50 y 100), reducir la velocidad en vez de bloquear
                if push_queue.qsize() > 50:
                    time.sleep(0.1)  # Pequeña pausa para no sobrecargar la cola
                    pass

            # Añadir a la cola y al registro global
            _push_queue_put(item_dict)
            added_file_paths.add(asset_file_key)
            return True

    def is_asset_in_queue(queue, path):
        """Comprueba si el path está presente en la cola (sin distinguir mayúsculas/minúsculas)."""
        return _queue_contains_asset_path(queue, path)

    def _mark_asset_path_in_flight(path):
        normalized = _normalized_asset_path_key(path)
        if not normalized:
            return
        with in_flight_asset_paths_lock:
            in_flight_asset_paths.add(normalized)

    def _unmark_asset_path_in_flight(path):
        normalized = _normalized_asset_path_key(path)
        if not normalized:
            return
        with in_flight_asset_paths_lock:
            in_flight_asset_paths.discard(normalized)

    def is_asset_reserved(path):
        return _asset_path_is_reserved(
            queue=push_queue,
            in_flight_paths=in_flight_asset_paths,
            in_flight_lock=in_flight_asset_paths_lock,
            path=path,
        )

    def _remember_added_asset_path(path):
        normalized = _normalized_asset_path_key(path)
        if not normalized:
            return
        with file_paths_lock:
            added_file_paths.add(normalized)

    def _mark_live_companion_consumed(path):
        normalized = _normalized_asset_path_key(path)
        if not normalized:
            return
        with consumed_live_companion_paths_lock:
            consumed_live_companion_paths.add(normalized)
        _remember_added_asset_path(path)

    def _is_live_companion_consumed(path):
        normalized = _normalized_asset_path_key(path)
        if not normalized:
            return False
        with consumed_live_companion_paths_lock:
            return normalized in consumed_live_companion_paths

    def infer_asset_type_from_path(file_path, fallback_type):
        """Infers media type from extension; falls back to source type when unknown."""
        ext = os.path.splitext(file_path)[1].lower()
        source_video_exts = [e.lower() for e in getattr(source_client, "ALLOWED_VIDEO_EXTENSIONS", [])]
        source_photo_exts = [e.lower() for e in getattr(source_client, "ALLOWED_PHOTO_EXTENSIONS", [])]
        if ext in source_video_exts:
            return "video"
        if ext in source_photo_exts:
            return "photo"
        return fallback_type

    def collect_pulled_asset_paths(download_folder, asset_filename):
        """
        Returns pulled file paths for one logical asset.
        For Synology Live Photo ZIP payloads, this includes companion video files sharing the same stem.
        """
        primary_path = os.path.join(download_folder, asset_filename)
        stem = os.path.splitext(asset_filename)[0]
        found = []

        # Resolve actual filename case from directory entries (important on Linux/NAS).
        try:
            entries = os.listdir(download_folder)
        except Exception:
            entries = []
        lower_to_real = {name.lower(): name for name in entries}

        primary_real_name = lower_to_real.get(asset_filename.lower())
        if primary_real_name:
            primary_path = os.path.join(download_folder, primary_real_name)

        if os.path.exists(primary_path):
            found.append(primary_path)

        source_video_exts = [e.lower() for e in getattr(source_client, "ALLOWED_VIDEO_EXTENSIONS", [])]
        stem_lower = stem.lower()
        for entry in entries:
            entry_base, entry_ext = os.path.splitext(entry)
            if entry_base.lower() != stem_lower:
                continue
            if entry_ext.lower() not in source_video_exts:
                continue
            companion = os.path.join(download_folder, entry)
            if companion.lower() != primary_path.lower():
                found.append(companion)

        return found

    def path_key(path):
        """
        OS-agnostic normalized key for case-insensitive path comparisons.
        """
        return os.path.normpath(path).replace("\\", "/").lower()

    def resolve_existing_path_case_insensitive(path):
        """
        Resolve an existing path even if provided filename casing does not match filesystem entry.
        """
        if not path:
            return path
        if os.path.exists(path):
            return path
        folder = os.path.dirname(path) or "."
        wanted_name = os.path.basename(path)
        try:
            for entry in os.listdir(folder):
                if entry.lower() == wanted_name.lower():
                    candidate = os.path.join(folder, entry)
                    if os.path.exists(candidate):
                        return candidate
        except Exception:
            pass
        return path

    def safe_remove_local_file(path, retries=3, delay_s=0.15):
        """
        Try to remove a local file with small retries (Windows/NAS transient locks).
        """
        if not path:
            return True
        resolved = resolve_existing_path_case_insensitive(path)
        if not os.path.exists(resolved):
            return True
        last_exc = None
        for _ in range(max(1, retries)):
            try:
                os.remove(resolved)
                return True
            except Exception as e:
                last_exc = e
                time.sleep(delay_s)
        LOGGER.warning(f"Could not remove file '{resolved}': {last_exc}")
        return False

    def cleanup_temp_folder_markers(folder):
        """
        Remove transient marker files (.active / *.lock) and prune empty dirs,
        including the root temp folder when it becomes empty.
        """
        if not folder or not os.path.exists(folder):
            return
        for path, dirs, files in os.walk(folder, topdown=False):
            for filename in files:
                if filename == ".active" or filename.endswith(".lock"):
                    safe_remove_local_file(os.path.join(path, filename))
            try:
                if not os.listdir(path):
                    os.rmdir(path)
                    LOGGER.info(f"Removed empty directory {path}")
            except OSError:
                pass

    def find_immich_live_video_companion(photo_file_path, pulled_file_paths):
        """
        Finds the companion video path for a given photo path within pulled files when target is Immich.
        """
        if not isinstance(target_client, ClassImmichPhotos):
            return None
        photo_ext = os.path.splitext(photo_file_path)[1].lower()
        if photo_ext not in ['.heic', '.heif', '.jpg', '.jpeg']:
            return None
        photo_stem = os.path.splitext(photo_file_path)[0]
        candidate_paths = {path_key(p): p for p in pulled_file_paths}
        for video_ext in (getattr(target_client, "ALLOWED_IMMICH_VIDEO_EXTENSIONS", []) or []):
            candidate_norm = path_key(f"{photo_stem}{video_ext.lower()}")
            if candidate_norm in candidate_paths:
                return candidate_paths[candidate_norm]
        return None

    def parse_capture_epoch(asset_datetime):
        if isinstance(asset_datetime, (int, float)):
            return float(asset_datetime)
        if isinstance(asset_datetime, str):
            try:
                return datetime.fromisoformat(asset_datetime.replace("Z", "+00:00")).timestamp()
            except Exception:
                return None
        return None

    # ------------------
    # 1) HILO PRINCIPAL
    # ------------------
    def main_thread(parallel=None, log_level=logging.INFO):
        def is_unsupported_source(client) -> bool:
            return isinstance(client, (ClassTakeoutFolder, ClassLocalFolder))

        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            # Get Log_filename
            log_file = get_logger_filename(LOGGER)

            # Get source and target client names
            source_client_name = source_client.get_client_name()
            target_client_name = target_client.get_client_name()

            # Check if source_client support specified filters
            unsupported_text = ""
            if is_unsupported_source(source_client):
                unsupported_text = f"(Unsupported for this source client: {source_client_name}. Filter Ignored)"

            # Check if '-move, --move-assets' have been passed as argument
            move_assets = ARGS.get('move-assets', False)

            # Check if there is some filter applied
            with_filters = False
            if ARGS.get('filter-by-type', None) or ARGS.get('filter-from-date', None) or ARGS.get('filter-to-date', None) or ARGS.get('filter-by-country', None) or ARGS.get('filter-by-city', None) or ARGS.get('filter-by-person', None):
                with_filters = True

            # Get the values from the arguments (if exists)
            type = ARGS.get('filter-by-type', None)
            from_date = ARGS.get('filter-from-date', None)
            to_date = ARGS.get('filter-to-date', None)
            country = ARGS.get('filter-by-country', None)
            city = ARGS.get('filter-by-city', None)
            person = ARGS.get('filter-by-person', None)

            LOGGER.info(f"🚀 Starting Automatic Migration Process: {source_client_name} ➜ {target_client_name}...")
            LOGGER.info(f"Source Client  : {source_client_name}")
            LOGGER.info(f"Target Client  : {target_client_name}")
            LOGGER.info(f"Temp Folder    : {temp_folder}")
            LOGGER.info(f"Log File       : {log_file}")

            if parallel:
                LOGGER.info(f"Migration Mode : Parallel")
            else:
                LOGGER.info(f"Migration Mode : Sequential")

            LOGGER.info(f"Move Assets    : {move_assets}")

            LOGGER.info(f"")
            if from_date or to_date or type or country or city or person:
                LOGGER.info(f"Assets Filters :")
            else:
                LOGGER.info(f"Assets Filters : None")
            if from_date:
                date_obj = datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"     from Date : {date_obj.strftime('%Y-%m-%d')}")
            if to_date:
                date_obj = datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                LOGGER.info(f"       to Date : {date_obj.strftime('%Y-%m-%d')}")
            if type:
                LOGGER.info(f"       by Type : {type}")
            if country:
                LOGGER.info(f"    by Country : {country} {unsupported_text}")
            if city:
                LOGGER.info(f"       by City : {city} {unsupported_text}")
            if person:
                LOGGER.info(f"     by Person : {person} {unsupported_text}")

            LOGGER.info(f"")
            LOGGER.info(f"Starting Pulling/Pushing Workers...")
            LOGGER.info(f"Analyzing Source client and Applying filters. This process may take some time, please be patient...")

            # Get source client statistics:
            blocked_assets = []
            total_albums_blocked_count = 0
            total_assets_blocked_count = 0
            all_albums = []
            try:
                LOGGER.info(f"Retrieving Albums on '{source_client_name}' matching filters criteria (if any). This process may take some time, please be patient...")
                all_albums = source_client.get_albums_including_shared_with_user(filter_assets=with_filters, log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Albums from '{source_client_name}'. - {e}")

            # Defensive dedupe for NextCloud sources:
            # when same logical album exists both as native PhotosDAV album and as folder album,
            # keep only one (prefer native).
            if isinstance(source_client, ClassNextCloudPhotos):
                def _album_key(name: str) -> str:
                    normalized = unicodedata.normalize("NFKC", str(name or "")).casefold().strip()
                    normalized = re.sub(r"^\d+[-_\s]+", "", normalized).strip()
                    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip()
                    normalized = re.sub(r"\s*\((copy|\d+)\)\s*$", "", normalized).strip()
                    normalized = re.sub(r"\s+", " ", normalized).strip()
                    return normalized

                dedup: dict[str, dict] = {}
                for album in all_albums:
                    key = _album_key(album.get("albumName", ""))
                    if not key:
                        continue
                    existing = dedup.get(key)
                    if existing is None:
                        dedup[key] = album
                        continue
                    existing_ns = str(existing.get("source_namespace", "")).strip().lower()
                    current_ns = str(album.get("source_namespace", "")).strip().lower()
                    if current_ns == "photos" and existing_ns != "photos":
                        dedup[key] = album
                if len(dedup) != len(all_albums):
                    LOGGER.info(
                        f"NextCloud albums deduplicated by name: before={len(all_albums)}, after={len(dedup)}"
                    )
                all_albums = sorted(list(dedup.values()), key=lambda a: str(a.get("albumName", "")).lower())

            LOGGER.info(f"{len(all_albums)} Albums found on '{source_client_name}' matching filters criteria")
            for album in all_albums:
                if isinstance(source_client, ClassSynologyPhotos):
                    album = source_client.ensure_shared_album_access(album, log_level=logging.ERROR)
                album_id = album['id']
                album_name = album['albumName']
                album_passphrase = album.get('passphrase')  # Obtiene el valor si existe, si no, devuelve None
                if _is_blocked_synology_shared_album(source_client, album):
                    LOGGER.info(f"Album '{album_name}' cannot be pulled because is a blocked shared album. Skipped!")
                    total_albums_blocked_count += 1
                    total_assets_blocked_count += album.get('item_count')
                    try:
                        blocked_assets.extend(source_client.get_all_assets_from_album_shared(album_id=album_id, album_name=album_name, album_passphrase=album_passphrase, log_level=logging.WARNING))
                    except Exception as e:
                        LOGGER.error(f"Error Retrieving Shared Albums's Assets from '{source_client_name}' - {e}")
            # Get all assets and filter out those blocked assets (from blocked shared albums) if any
            all_no_albums_assets = []
            try:
                all_no_albums_assets = source_client.get_all_assets_without_albums(log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving Assets without albums from '{source_client_name}' - {e}")
            all_albums_assets = []
            try:
                all_albums_assets = source_client.get_all_assets_from_all_albums(log_level=logging.INFO)
            except Exception as e:
                LOGGER.error(f"Error Retrieving Albums's Assets from '{source_client_name}' - {e}")

            all_supported_assets = all_no_albums_assets + all_albums_assets
            blocked_assets_ids = {asset["id"] for asset in blocked_assets}
            filtered_all_supported_assets = [asset for asset in all_supported_assets if asset["id"] not in blocked_assets_ids]

            all_photos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in image_labels]
            all_videos = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in video_labels]
            all_assets = all_photos + all_videos
            all_metadata = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in metadata_labels]
            all_sidecar = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in sidecar_labels]
            all_invalid = [asset for asset in filtered_all_supported_assets if asset['type'].lower() in ['unknown']]

            SHARED_DATA.info.update({
                "total_assets": len(all_assets),
                "total_photos": len(all_photos),
                "total_videos": len(all_videos),
                "total_albums": len(all_albums),
                "total_albums_blocked": total_albums_blocked_count,
                "total_metadata": len(all_metadata),
                "total_sidecar": len(all_sidecar),
                "total_invalid": len(all_invalid),
            })

            SHARED_DATA.counters['total_albums_blocked'] = total_albums_blocked_count
            SHARED_DATA.counters['total_assets_blocked'] = total_assets_blocked_count

            LOGGER.info(f"Input Info Analysis: ")
            for key, value in SHARED_DATA.info.items():
                LOGGER.info(f"   {key}: {value}")

            # Delete unneeded vars to clean memory
            del all_albums
            del all_supported_assets
            del blocked_assets_ids
            del filtered_all_supported_assets
            del all_assets
            del all_photos
            del all_videos
            del all_metadata
            del all_sidecar
            del all_invalid

            # ------------------------------------------------------------------------------------------------------
            # 1) Iniciar uno o varios hilos de pull y push para manejar los pull y push concurrentes
            # ------------------------------------------------------------------------------------------------------
            # Obtain the number of Threads for the CPU and launch as many Push workers as max(1, int(cpu_total_threads*2))
            cpu_total_threads = os.cpu_count()
            LOGGER.info(f"")
            LOGGER.info(f"CPU Total Cores Detected = {cpu_total_threads}")
            num_pull_threads = 1  # no Iniciar más de 1 hilo de descarga, de lo contrario los assets se descargarán multiples veces.
            LOGGER.info(f"Launching {num_pull_threads} Pull worker in parallel...")
            num_push_threads = max(1, int(cpu_total_threads * 2))
            LOGGER.info(f"Launching {num_push_threads} Push workers in parallel...")
            configured_album_assoc_threads = int(ARGS.get("album-association-workers", 0) or 0)
            if configured_album_assoc_threads > 0:
                num_album_assoc_threads = configured_album_assoc_threads
            elif isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos, ClassGooglePhotos, ClassNextCloudPhotos)):
                num_album_assoc_threads = min(max(2, int(cpu_total_threads or 1)), 4)
            else:
                num_album_assoc_threads = 1
            LOGGER.info(f"Launching {num_album_assoc_threads} Album Association worker in parallel...")

            pull_threads = [
                threading.Thread(
                    target=puller_worker,
                    kwargs={"parallel": parallel, "log_level": log_level},
                    daemon=True,
                )
                for _ in range(num_pull_threads)
            ]
            push_threads = [
                threading.Thread(
                    target=pusher_worker,
                    kwargs={
                        "processed_albums": processed_albums,
                        "processed_albums_lock": processed_albums_lock,
                        "worker_id": worker_id + 1,
                        "log_level": log_level,
                    },
                    daemon=True,
                )
                for worker_id in range(num_push_threads)
            ]
            album_assoc_threads = [
                threading.Thread(
                    target=album_association_worker,
                    kwargs={
                        "processed_albums": processed_albums,
                        "processed_albums_lock": processed_albums_lock,
                        "worker_id": worker_id + 1,
                        "log_level": log_level,
                    },
                    daemon=True,
                )
                for worker_id in range(num_album_assoc_threads)
            ]
            retry_thread = None
            if retries_enabled:
                retry_thread = threading.Thread(
                    target=retry_scheduler_worker,
                    kwargs={"log_level": log_level},
                    daemon=True,
                )

            # 1) Arrancar pullers
            for t in pull_threads:
                t.start()
            if retry_thread is not None:
                retry_thread.start()
            for t in album_assoc_threads:
                t.start()

            # 2) Si modo paralelo, arranca ya los pushers
            if parallel:
                for t in push_threads:
                    t.start()

            # 3) Esperar a que terminen los pullers
            for t in pull_threads:
                t.join()

            # 4) Si modo secuencial, ahora sí arranca los pushers
            if not parallel:
                for t in push_threads:
                    t.start()

            # 5) Esperar a que la cola se vacíe (assets reales y todos los re‑enqueues)
            _wait_until_push_pipeline_drains()

            if retry_thread is not None:
                retry_scheduler_stop.set()
                with retry_condition:
                    retry_condition.notify_all()
                retry_thread.join()

            # 6) Inyectar un None por cada pusher para que lean la señal de fin
            for _ in range(num_push_threads):
                _push_queue_put(None)

            # 7) Esperar a que los pushers consuman su None y terminen
            for t in push_threads:
                t.join()

            for _ in range(num_album_assoc_threads):
                album_assoc_queue.put(None)

            for t in album_assoc_threads:
                t.join()

            # En este punto todos los pulls y pushs están listas y la cola está vacía.

            # Auto-stack burst photos in Immich target using uploaded records.
            if isinstance(target_client, ClassImmichPhotos):
                try:
                    target_client.auto_stack_bursts(immich_uploaded_records, context_label="Automatic Migration", log_level=logging.INFO)
                except Exception as e:
                    LOGGER.warning(f"Unable to auto-stack bursts in Immich after migration: {e}")

            if move_assets and isinstance(source_client, ClassLocalFolder):
                _cleanup_local_source_after_move(source_client=source_client, log_level=logging.INFO)

            # Finalmente, borrar carpetas vacías que queden en temp_folder
            remove_empty_dirs(temp_folder)
            cleanup_temp_folder_markers(temp_folder)

            end_time = datetime.now()
            migration_formatted_duration = str(timedelta(seconds=round((end_time - migration_start_time).total_seconds())))
            total_formatted_duration = str(timedelta(seconds=round((end_time - SHARED_DATA.info["start_time"]).total_seconds())))

            # ----------------------------------------------------------------------------
            # 4) Mostrar o retornar contadores
            # ----------------------------------------------------------------------------
            LOGGER.info(f"")
            total_failed_assets = (
                SHARED_DATA.counters['total_pull_failed_assets']
                + SHARED_DATA.counters['total_push_failed_assets']
                + SHARED_DATA.counters['total_album_assoc_unconfirmed_assets']
            )
            if total_failed_assets > 0:
                LOGGER.warning(f"{MSG_TAGS['WARNING']}Migration finished with partial failures.")
            else:
                LOGGER.info(f"🚀 All assets pulled and pushed successfully!")
            LOGGER.info(f"")
            LOGGER.info(f"----- MIGRATION FINISHED  -----")
            LOGGER.info(f"{source_client_name} --> {target_client_name}")
            LOGGER.info(f"Pulled Albums               : {SHARED_DATA.counters['total_pulled_albums']}")
            LOGGER.info(f"Pushed Albums               : {SHARED_DATA.counters['total_pushed_albums']}")
            LOGGER.info(f"Pulled Assets               : {SHARED_DATA.counters['total_pulled_assets']} (Photos: {SHARED_DATA.counters['total_pulled_photos']}, Videos: {SHARED_DATA.counters['total_pulled_videos']})")
            LOGGER.info(f"Pushed Assets               : {SHARED_DATA.counters['total_pushed_assets']} (Photos: {SHARED_DATA.counters['total_pushed_photos']}, Videos: {SHARED_DATA.counters['total_pushed_videos']})")
            LOGGER.info(f"Push Duplicates (skipped)   : {SHARED_DATA.counters['total_push_duplicates_assets']}")
            LOGGER.info(f"Pull Failed Assets          : {SHARED_DATA.counters['total_pull_failed_assets']}")
            LOGGER.info(f"Push Failed Assets          : {SHARED_DATA.counters['total_push_failed_assets']}")
            LOGGER.info(f"Push Retry Scheduled        : {SHARED_DATA.counters['total_push_retry_scheduled_assets']}")
            LOGGER.info(f"Push Retry Recovered        : {SHARED_DATA.counters['total_push_retry_recovered_assets']}")
            LOGGER.info(f"Album Assoc Retry Scheduled : {SHARED_DATA.counters['total_album_assoc_retry_scheduled_assets']}")
            LOGGER.info(f"Album Assoc Retry Recovered : {SHARED_DATA.counters['total_album_assoc_retry_recovered_assets']}")
            LOGGER.info(f"Album Assoc Unconfirmed     : {SHARED_DATA.counters['total_album_assoc_unconfirmed_assets']}")
            LOGGER.info(f"")
            LOGGER.info(f"Migration Job completed in  : {migration_formatted_duration}")
            LOGGER.info(f"Total Elapsed Time          : {total_formatted_duration}")
            LOGGER.info(f"")
            LOGGER.info(f"")
            return SHARED_DATA.counters

    # --------------------------------------------------------------------------------
    # 1) PULLER: Función puller_worker para descargar assets y poner en la cola
    # --------------------------------------------------------------------------------
    def puller_worker(parallel=None, log_level=logging.INFO):
        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"puller-{thread_id}")

        # Check if there is some filter applied
        with_filters = False
        if ARGS.get('filter-by-type', None) or ARGS.get('filter-from-date', None) or ARGS.get('filter-to-date', None) or ARGS.get('filter-by-country', None) or ARGS.get('filter-by-city', None) or ARGS.get('filter-by-person', None):
            with_filters = True

        with set_log_level(LOGGER, log_level):

            # 1.1) Descarga de álbumes
            albums = []
            try:
                albums = source_client.get_albums_including_shared_with_user(filter_assets=with_filters, log_level=logging.ERROR)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Albums - {e} \n{traceback.format_exc()}")
                LOGGER.info(f"Albums Assets Skipped")

            pulled_assets = 0
            for album in albums:
                if isinstance(source_client, ClassSynologyPhotos):
                    album = source_client.ensure_shared_album_access(album, log_level=logging.ERROR)
                    if hasattr(source_client, "_hydrate_album_payload"):
                        album = source_client._hydrate_album_payload(album)
                album_assets = []
                album_id = album['id']
                album_name = album['albumName']
                album_passphrase = album.get('passphrase')  # Obtiene el valor si existe, si no, devuelve None
                album_scope = album.get("_synology_album_scope")
                if isinstance(source_client, ClassSynologyPhotos):
                    is_shared = source_client.is_shared_with_me_album(album)
                else:
                    is_shared = album_passphrase is not None and album_passphrase != ""  # Si tiene passphrase, es compartido

                # Descargar todos los assets de este álbum
                try:
                    if not is_shared:
                        album_assets = source_client.get_all_assets_from_album(
                            album_id=album_id,
                            album_name=album_name,
                            album_scope=album_scope,
                            album_expected_count=album.get("item_count"),
                            log_level=logging.ERROR,
                        )
                    else:
                        if not _is_blocked_synology_shared_album(source_client, album):
                            album_assets = source_client.get_all_assets_from_album_shared(
                                album_id=album_id,
                                album_name=album_name,
                                album_passphrase=album_passphrase,
                                album_scope=album_scope,
                                album_expected_count=album.get("item_count"),
                                log_level=logging.ERROR,
                            )
                    if not album_assets:
                        # SHARED_DATA.counters['total_pull_failed_albums'] += 1     # If we uncomment this line, it will count as failed Empties albums
                        continue
                except Exception as e:
                    LOGGER.error(f"Error Retrieving All Assets from album {album_name} - {e} \n{traceback.format_exc()}")
                    SHARED_DATA.counters['total_pull_failed_albums'] += 1
                    continue

                # Crear carpeta del álbum dentro de temp_folder, y bloquea su eliminación hasta que terminen las descargas del album
                album_folder = os.path.join(temp_folder, album_name)
                os.makedirs(album_folder, exist_ok=True)
                # Crear archivo `.active` para marcar que la carpeta está en uso
                active_file = os.path.join(album_folder, ".active")
                with open(active_file, 'w') as lock_album_folder:
                    lock_album_folder.write("Pulling Album")
                try:
                    for asset in album_assets:
                        asset_perf_started = time.perf_counter()
                        asset_id = asset['id']
                        asset_type = asset['type']
                        asset_datetime = asset.get('asset_datetime') or asset.get('time')
                        asset_filename = asset.get('filename')

                        # Skip pull metadata and sidecar for the time being
                        if asset_type in ['metadata', 'sidecar']:
                            continue

                        # Ruta del archivo descargado
                        local_file_path = os.path.join(album_folder, asset_filename)

                        # Archivo de bloqueo temporal para que el pusher no borre el fichero mientras que el puller lo está creando
                        lock_file = local_file_path + ".lock"
                        # Crear archivo de bloqueo antes de la descarga
                        with open(lock_file, 'w') as lock:
                            lock.write("Pulling Asset")
                        # Descargar el asset (tolerante por-asset para no abortar todo el álbum).
                        skipped_not_found = False
                        pull_started_at = time.perf_counter()
                        try:
                            pulled_assets = source_client.pull_asset(
                                asset_id=asset_id,
                                asset_filename=asset_filename,
                                asset_time=asset_datetime,
                                download_folder=album_folder,
                                album_passphrase=album_passphrase if is_shared else None,
                                album_id=album_id,
                                album_scope=album_scope,
                                log_level=logging.ERROR,
                            )
                        except Exception as e:
                            if _is_nextcloud_photo_not_found_error(e):
                                skipped_not_found = True
                                LOGGER.warning(
                                    f"Asset Pull Skip : '{os.path.basename(asset_filename)}' from Album '{album_name}' - "
                                    f"Photo not found for user"
                                )
                            else:
                                LOGGER.error(
                                    f"Asset Pull Error: '{os.path.basename(asset_filename)}' from Album '{album_name}' - {e}"
                                )
                            pulled_assets = 0
                        finally:
                            # Eliminar archivo de bloqueo después de la descarga
                            if os.path.exists(lock_file):
                                os.remove(lock_file)

                        # Actualizamos Contadores de descargas
                        if _pull_has_content(pulled_assets):
                            pulled_file_paths = collect_pulled_asset_paths(album_folder, asset_filename)
                            if not pulled_file_paths:
                                pulled_file_paths = [local_file_path]
                            collect_finished_at = time.perf_counter()

                            immich_live_companion = find_immich_live_video_companion(local_file_path, pulled_file_paths)
                            for idx, pulled_file_path in enumerate(pulled_file_paths):
                                if immich_live_companion and path_key(pulled_file_path) == path_key(immich_live_companion):
                                    continue
                                if _is_live_companion_consumed(pulled_file_path):
                                    LOGGER.info(f"Asset Live Companion Consumed: '{os.path.basename(pulled_file_path)}' from Album '{album_name}'. Skipped")
                                    if not is_asset_reserved(pulled_file_path) and os.path.exists(pulled_file_path):
                                        safe_remove_local_file(pulled_file_path)
                                    continue
                                normalized_asset_type = infer_asset_type_from_path(pulled_file_path, asset_type)
                                count_push_stats = (idx == 0)
                                LOGGER.info(f"Asset Pulled    : '{os.path.basename(pulled_file_path)}'")
                                SHARED_DATA.counters['total_pulled_assets'] += 1
                                if normalized_asset_type.lower() in video_labels:
                                    SHARED_DATA.counters['total_pulled_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_pulled_photos'] += 1

                                # Enviar a la cola con la información necesaria para la subida
                                asset_dict = {
                                    'asset_id': asset_id,
                                    'asset_file_path': pulled_file_path,
                                    'asset_datetime': asset_datetime,
                                    'asset_type': normalized_asset_type,
                                    'album_name': album_name,
                                    'album_is_shared': is_shared,
                                    'count_push_stats': count_push_stats,
                                    'enqueued_at_monotonic': time.perf_counter(),
                                }
                                if immich_live_companion and path_key(pulled_file_path) == path_key(local_file_path):
                                    asset_dict['live_photo_video_path'] = immich_live_companion
                                # añadimos el asset a la cola solo si no se había añadido ya un asset con el mismo 'asset_file_path'
                                unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)
                                if unique and asset_dict.get('live_photo_video_path'):
                                    _mark_live_companion_consumed(asset_dict.get('live_photo_video_path'))
                                if not unique:
                                    LOGGER.info(f"Asset Duplicated: '{os.path.basename(pulled_file_path)}' from Album '{album_name}'. Skipped")
                                    SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                    # Solo borramos si el fichero ya no está reservado por la cola ni por un pusher en curso.
                                    if not is_asset_reserved(pulled_file_path) and os.path.exists(pulled_file_path):
                                        safe_remove_local_file(pulled_file_path)
                                    companion_to_cleanup = asset_dict.get('live_photo_video_path')
                                    if companion_to_cleanup and os.path.exists(companion_to_cleanup):
                                        companion_lock = companion_to_cleanup + ".lock"
                                        if (not is_asset_reserved(companion_to_cleanup)) and (not os.path.exists(companion_lock)):
                                            safe_remove_local_file(companion_to_cleanup)
                            _debug_perf_log(
                                LOGGER,
                                "automatic_migration.pull.album_asset",
                                asset_perf_started,
                                worker="puller",
                                album=album_name,
                                asset=os.path.basename(local_file_path),
                                asset_id=asset_id,
                                pulled_variants=len(pulled_file_paths),
                                pull_ms=f"{(collect_finished_at - pull_started_at) * 1000.0:.2f}",
                            )
                        else:
                            if skipped_not_found:
                                SHARED_DATA.counters['total_pull_failed_assets'] += 1
                                if asset_type.lower() in video_labels:
                                    SHARED_DATA.counters['total_pull_failed_videos'] += 1
                                else:
                                    SHARED_DATA.counters['total_pull_failed_photos'] += 1
                                continue
                            LOGGER.warning(f"Asset Pull Fail : '{os.path.basename(local_file_path)}' from Album '{album_name}'")
                            SHARED_DATA.counters['total_pull_failed_assets'] += 1
                            if asset_type.lower() in video_labels:
                                SHARED_DATA.counters['total_pull_failed_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pull_failed_photos'] += 1

                except Exception as e:
                    LOGGER.error(f"Album Pull Error: '{album_name}' - {e}")
                    SHARED_DATA.counters['total_pull_failed_albums'] += 1
                    continue
                finally:
                    # Eliminar archivo .active después de la descarga
                    if os.path.exists(active_file):
                        os.remove(active_file)

                # Incrementamos contador de álbumes descargados
                SHARED_DATA.counters['total_pulled_albums'] += 1
                if defer_album_association_until_album_end:
                    album_assoc_queue.put({
                        "album_name": album_name,
                        "_album_done": True,
                    })
                LOGGER.info(f"Album Pulled    : '{album_name}'")

            # 1.2) Descarga de assets sin álbum
            assets_no_album = []
            try:
                assets_no_album = source_client.get_all_assets_without_albums(log_level=logging.ERROR)
            except Exception as e:
                LOGGER.error(f"Error Retrieving All Assets without Albums - {e} \n{traceback.format_exc()}")

            # Crear carpeta temp_folder si no existe, y bloquea su eliminación hasta que terminen las descargas
            os.makedirs(temp_folder, exist_ok=True)
            # Crear archivo `.active` para marcar que la carpeta está en uso
            active_file = os.path.join(temp_folder, ".active")
            with open(active_file, 'w') as lock_temp_folder:
                lock_temp_folder.write("Pulling Asset")
            try:
                pulled_assets = 0
                for asset in assets_no_album:
                    asset_perf_started = time.perf_counter()
                    asset_id = asset['id']
                    asset_type = asset['type']
                    asset_datetime = asset.get('asset_datetime') or asset.get('time')
                    asset_filename = asset.get('filename')
                    lock_file = None

                    # Skip pull metadata and sidecar for the time being
                    if asset_type in ['metadata', 'sidecar']:
                        continue

                    try:
                        # Ruta del archivo descargado
                        local_file_path = os.path.join(temp_folder, asset_filename)

                        # Archivo de bloqueo temporal para que el pusher no borre el fichero mientras que el puller lo está creando
                        lock_file = local_file_path + ".lock"
                        # Crear archivo de bloqueo antes de la descarga
                        with open(lock_file, 'w') as lock:
                            lock.write("Pulling")
                        # Descargar directamente en temp_folder
                        pull_started_at = time.perf_counter()
                        pulled_assets = source_client.pull_asset(asset_id=asset_id, asset_filename=asset_filename, asset_time=asset_datetime, download_folder=temp_folder, log_level=logging.ERROR)
                    except Exception as e:
                        if _is_nextcloud_photo_not_found_error(e):
                            LOGGER.warning(
                                f"Asset Pull Skip : '{os.path.basename(local_file_path)}' - Photo not found for user"
                            )
                        else:
                            LOGGER.error(f"Asset Pull Error: '{os.path.basename(local_file_path)}' - {e}")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() in video_labels:
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
                        continue
                    finally:
                        if lock_file and os.path.exists(lock_file):
                            safe_remove_local_file(lock_file)

                    # Si se ha hecho correctamente el pull del asset, actualizamos contadores y enviamos el asset a la cola de push
                    if _pull_has_content(pulled_assets):
                        pulled_file_paths = collect_pulled_asset_paths(temp_folder, asset_filename)
                        if not pulled_file_paths:
                            pulled_file_paths = [local_file_path]
                        collect_finished_at = time.perf_counter()

                        immich_live_companion = find_immich_live_video_companion(local_file_path, pulled_file_paths)
                        for idx, pulled_file_path in enumerate(pulled_file_paths):
                            if immich_live_companion and path_key(pulled_file_path) == path_key(immich_live_companion):
                                continue
                            if _is_live_companion_consumed(pulled_file_path):
                                LOGGER.info(f"Asset Live Companion Consumed: '{os.path.basename(pulled_file_path)}'. Skipped")
                                if not is_asset_reserved(pulled_file_path) and os.path.exists(pulled_file_path):
                                    safe_remove_local_file(pulled_file_path)
                                continue
                            normalized_asset_type = infer_asset_type_from_path(pulled_file_path, asset_type)
                            count_push_stats = (idx == 0)
                            # Actualizamos Contadores de descargas
                            LOGGER.info(f"Asset Pulled    : '{os.path.basename(pulled_file_path)}'")
                            SHARED_DATA.counters['total_pulled_assets'] += 1
                            if normalized_asset_type.lower() in video_labels:
                                SHARED_DATA.counters['total_pulled_videos'] += 1
                            else:
                                SHARED_DATA.counters['total_pulled_photos'] += 1

                            # Enviar a la cola de push con la información necesaria para la subida (sin album_name)
                            asset_dict = {
                                'asset_id': asset_id,
                                'asset_file_path': pulled_file_path,
                                'asset_datetime': asset_datetime,
                                'asset_type': normalized_asset_type,
                                'album_name': None,
                                'count_push_stats': count_push_stats,
                                'enqueued_at_monotonic': time.perf_counter(),
                            }
                            if immich_live_companion and path_key(pulled_file_path) == path_key(local_file_path):
                                asset_dict['live_photo_video_path'] = immich_live_companion
                            unique = enqueue_unique(push_queue, asset_dict, parallel=parallel)
                            if unique and asset_dict.get('live_photo_video_path'):
                                _mark_live_companion_consumed(asset_dict.get('live_photo_video_path'))
                            if not unique:
                                LOGGER.info(f"Asset Duplicated: '{os.path.basename(pulled_file_path)}'. Skipped")
                                SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                # Solo borramos si el fichero ya no está reservado por la cola ni por un pusher en curso.
                                if not is_asset_reserved(pulled_file_path) and os.path.exists(pulled_file_path):
                                    safe_remove_local_file(pulled_file_path)
                                companion_to_cleanup = asset_dict.get('live_photo_video_path')
                                if companion_to_cleanup and os.path.exists(companion_to_cleanup):
                                    companion_lock = companion_to_cleanup + ".lock"
                                    if (not is_asset_reserved(companion_to_cleanup)) and (not os.path.exists(companion_lock)):
                                        safe_remove_local_file(companion_to_cleanup)
                        _debug_perf_log(
                            LOGGER,
                            "automatic_migration.pull.no_album_asset",
                            asset_perf_started,
                            worker="puller",
                            album="-",
                            asset=os.path.basename(local_file_path),
                            asset_id=asset_id,
                            pulled_variants=len(pulled_file_paths),
                            pull_ms=f"{(collect_finished_at - pull_started_at) * 1000.0:.2f}",
                        )
                    else:
                        LOGGER.warning(f"Asset Pull Fail : '{os.path.basename(local_file_path)}'")
                        SHARED_DATA.counters['total_pull_failed_assets'] += 1
                        if asset_type.lower() in video_labels:
                            SHARED_DATA.counters['total_pull_failed_videos'] += 1
                        else:
                            SHARED_DATA.counters['total_pull_failed_photos'] += 1
            finally:
                # Eliminar archivo .active después de la descarga
                if os.path.exists(active_file):
                    os.remove(active_file)

            LOGGER.info(f"Puller Task Finished!")

    # ----------------------------------------------------------------------------
    # 2) PUSHER: Función pusher_worker para SUBIR (consumir de la cola)
    # ----------------------------------------------------------------------------
    def pusher_worker(processed_albums=None, processed_albums_lock=None, worker_id=1, log_level=logging.INFO):
        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"pusher-{thread_id}")

        if processed_albums is None:
            processed_albums = set()
        if processed_albums_lock is None:
            processed_albums_lock = threading.Lock()
        removed_source_asset_ids = set()

        with set_log_level(LOGGER, log_level):
            move_assets = ARGS.get('move-assets', None)
            while True:
                asset = None
                try:
                    # Extraemos el siguiente asset de la cola
                    # time.sleep(0.7)  # Esto es por si queremos ralentizar el worker de subidas
                    asset = _push_queue_get()

                    if asset is None:
                        # Señal de fin: marcamos la tarea y salimos
                        break

                    # Obtenemos las propiedades del asset extraído de la cola.
                    source_asset_id = asset['asset_id']
                    asset_file_path = asset['asset_file_path']
                    asset_datetime = asset['asset_datetime']
                    asset_type = asset['asset_type']
                    album_name = asset['album_name']
                    album_is_shared = asset.get('album_is_shared', False)
                    count_push_stats = asset.get('count_push_stats', True)
                    live_photo_video_path = asset.get('live_photo_video_path', None)
                    retry_attempt = int(asset.get('retry_attempt', 0) or 0)
                    association_retry_attempt = int(asset.get('album_assoc_retry_attempt', 0) or 0)
                    enqueued_at_monotonic = asset.get('enqueued_at_monotonic')
                    skip_target_push = bool(asset.get('skip_target_push')) and bool(asset.get('resolved_target_asset_id'))
                    asset_id = asset.get('resolved_target_asset_id')
                    asset_pushed = False
                    treat_as_consumed = False
                    album_association_confirmed = not bool(album_name)
                    scheduled_retry = False
                    asset_started_at = time.perf_counter()
                    push_elapsed_ms = None
                    album_assoc_elapsed_ms = None
                    cleanup_elapsed_ms = None
                    _mark_asset_path_in_flight(asset_file_path)
                    if live_photo_video_path:
                        _mark_asset_path_in_flight(live_photo_video_path)

                    # Antes de llamar, guardamos el nivel actual (debería ser INFO)
                    orig_level = LOGGER.level
                    try:
                        isDuplicated = False
                        if (not live_photo_video_path) and _is_live_companion_consumed(asset_file_path):
                            LOGGER.info(
                                f"Asset Live Companion Consumed: '{os.path.basename(asset_file_path)}'. Skipped"
                                f"{_format_album_pending_context(album_name, asset_file_path)}"
                            )
                            treat_as_consumed = True
                            cleanup_elapsed_ms = _finalize_asset_success(
                                source_asset_id=source_asset_id,
                                asset_file_path=asset_file_path,
                                live_photo_video_path=None,
                                album_name=album_name,
                                asset_id=None,
                                retry_attempt=retry_attempt,
                                association_retry_attempt=association_retry_attempt,
                                asset_type=asset_type,
                                count_push_stats=False,
                                move_assets=False,
                                removed_source_asset_ids=removed_source_asset_ids,
                                processed_albums=processed_albums,
                                processed_albums_lock=processed_albums_lock,
                                worker_id=worker_id,
                                logger=LOGGER,
                            )
                            continue
                        # SUBIR el asset salvo que ya tengamos que reintentar solo la asociación al álbum.
                        if skip_target_push and asset_id:
                            treat_as_consumed = True
                        else:
                            push_started_at = time.perf_counter()
                            if isinstance(target_client, ClassImmichPhotos) and live_photo_video_path:
                                asset_id, isDuplicated = target_client.push_live_photo(
                                    photo_file_path=asset_file_path,
                                    live_photo_video_path=live_photo_video_path,
                                    log_level=logging.ERROR,
                                    resolve_duplicate_id=False,
                                )
                            elif isinstance(target_client, (ClassImmichPhotos, ClassSynologyPhotos, ClassGooglePhotos)):
                                asset_id, isDuplicated = target_client.push_asset(
                                    file_path=asset_file_path,
                                    log_level=logging.ERROR,
                                    resolve_duplicate_id=False,
                                )
                            else:
                                asset_id, isDuplicated = target_client.push_asset(file_path=asset_file_path, log_level=logging.ERROR)
                            push_elapsed_ms = (time.perf_counter() - push_started_at) * 1000.0
                            queue_wait_ms = max(0.0, (asset_started_at - float(enqueued_at_monotonic)) * 1000.0) if isinstance(enqueued_at_monotonic, (int, float)) else None
                            _debug_perf_log_elapsed(
                                LOGGER,
                                "automatic_migration.asset.upload",
                                push_elapsed_ms,
                                worker=worker_id,
                                album=album_name or "-",
                                asset=os.path.basename(asset_file_path),
                                source_asset_id=source_asset_id,
                                queue_wait_ms=f"{queue_wait_ms:.2f}" if queue_wait_ms is not None else None,
                                duplicated=isDuplicated,
                                asset_pushed=bool(asset_id),
                                skip_target_push=skip_target_push,
                            )

                            # Actualizamos Contadores de subidas
                            if asset_id:
                                asset_pushed = True
                                treat_as_consumed = True
                                if isDuplicated:
                                    LOGGER.info(
                                        f"Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped"
                                        f"{_format_album_pending_context(album_name, asset_file_path)}"
                                    )
                                    if count_push_stats:
                                        SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                else:
                                    if count_push_stats:
                                        SHARED_DATA.counters['total_pushed_assets'] += 1
                                        if asset_type.lower() in video_labels:
                                            SHARED_DATA.counters['total_pushed_videos'] += 1
                                        else:
                                            SHARED_DATA.counters['total_pushed_photos'] += 1
                                    LOGGER.info(
                                        f"Asset Pushed    : '{os.path.basename(asset_file_path)}'"
                                        f"{_format_album_pending_context(album_name, asset_file_path)}"
                                    )
                                    if isinstance(target_client, ClassImmichPhotos) and asset_type.lower() in image_labels and not str(asset_id).startswith("duplicate::"):
                                        try:
                                            file_size = os.path.getsize(asset_file_path) if os.path.exists(asset_file_path) else 0
                                        except Exception:
                                            file_size = 0
                                        rec = target_client._build_burst_record(
                                            asset_id=asset_id,
                                            file_path=asset_file_path,
                                            capture_epoch=parse_capture_epoch(asset_datetime),
                                            file_size=file_size
                                        )
                                        with immich_uploaded_records_lock:
                                            immich_uploaded_records.append(rec)
                            else:
                                # Si entramos aqui es porque asset_id no existe, probablemente se haya producido una excepción en push_asset, y el LOGGER se haya quedado con el nivel ERROR
                                set_log_level(LOGGER, orig_level)
                                if isDuplicated:
                                    LOGGER.info(
                                        f"Asset Duplicated: '{os.path.basename(asset_file_path)}'. Skipped"
                                        f"{_format_album_pending_context(album_name, asset_file_path)}"
                                    )
                                    treat_as_consumed = True
                                    if count_push_stats:
                                        SHARED_DATA.counters['total_push_duplicates_assets'] += 1
                                    if album_name:
                                        _register_pending_duplicate_resolution(album_name=album_name, asset=asset)
                                        _maybe_finalize_album(
                                            album_name=album_name,
                                            removed_source_asset_ids=removed_source_asset_ids,
                                            processed_albums=processed_albums,
                                            processed_albums_lock=processed_albums_lock,
                                            worker_id=worker_id,
                                            logger=LOGGER,
                                            log_level=log_level,
                                        )
                                else:
                                    scheduled_retry = _schedule_asset_retry(
                                        asset=asset,
                                        reason="upload did not return a reusable target asset id",
                                    )
                                    if not scheduled_retry:
                                        if album_name:
                                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                                        else:
                                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                                        _record_final_push_failure(asset_type=asset_type, count_push_stats=count_push_stats)

                    except Exception as e:
                        # 1) Restaura el nivel a INFO
                        LOGGER.setLevel(logging.INFO)

                        scheduled_retry = _schedule_asset_retry(
                            asset=asset,
                            reason=f"upload exception: {str(e)}",
                        )
                        if not scheduled_retry:
                            if album_name:
                                LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                            else:
                                LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                            LOGGER.error(f"Caught Exception: {str(e)} \n{traceback.format_exc()}")
                            _record_final_push_failure(asset_type=asset_type, count_push_stats=count_push_stats)
                            continue

                    finally:
                        # Pase lo que pase (return o excepción dentro de push_asset),
                        # aquí restauramos siempre el nivel original
                        LOGGER.setLevel(orig_level)

                    if not scheduled_retry and album_name and asset_id:
                        asset['resolved_target_asset_id'] = asset_id
                        album_association_confirmed, album_assoc_elapsed_ms, cleanup_elapsed_ms, scheduled_retry = _associate_uploaded_asset_to_album(
                            asset=asset,
                            asset_id=asset_id,
                            album_name=album_name,
                            album_is_shared=album_is_shared,
                            worker_id=worker_id,
                            removed_source_asset_ids=removed_source_asset_ids,
                            processed_albums=processed_albums,
                            processed_albums_lock=processed_albums_lock,
                            log_level=log_level,
                        )

                    if not scheduled_retry and album_name and isDuplicated and not asset_id:
                        queue_wait_ms = None
                        if isinstance(enqueued_at_monotonic, (int, float)):
                            queue_wait_ms = max(0.0, (asset_started_at - float(enqueued_at_monotonic)) * 1000.0)
                        _debug_perf_log(
                            LOGGER,
                            "automatic_migration.asset.pipeline",
                            asset_started_at,
                            worker=worker_id,
                            album=album_name or "-",
                            asset=os.path.basename(asset_file_path),
                            source_asset_id=source_asset_id,
                            queue_wait_ms=f"{queue_wait_ms:.2f}" if queue_wait_ms is not None else None,
                            push_ms=f"{push_elapsed_ms:.2f}" if push_elapsed_ms is not None else None,
                            album_assoc_ms=f"{album_assoc_elapsed_ms:.2f}" if album_assoc_elapsed_ms is not None else None,
                            duplicated=isDuplicated,
                            asset_pushed=asset_pushed,
                            consumed=treat_as_consumed,
                            album_association_confirmed=False,
                            scheduled_retry=False,
                        )
                        continue

                    if not scheduled_retry and (asset_pushed or treat_as_consumed) and not (album_name and asset_id):
                        cleanup_delay_seconds = 1.0 if skip_target_push and not album_name else 0.0
                        cleanup_elapsed_ms = _finalize_asset_success(
                            source_asset_id=source_asset_id,
                            asset_file_path=asset_file_path,
                            live_photo_video_path=live_photo_video_path,
                            album_name=album_name,
                            asset_id=asset_id,
                            retry_attempt=retry_attempt,
                            association_retry_attempt=association_retry_attempt,
                            asset_type=asset_type,
                            count_push_stats=count_push_stats,
                            move_assets=move_assets,
                            removed_source_asset_ids=removed_source_asset_ids,
                            processed_albums=processed_albums,
                            processed_albums_lock=processed_albums_lock,
                            worker_id=worker_id,
                            logger=LOGGER,
                            cleanup_delay_seconds=cleanup_delay_seconds,
                        )
                        album_association_confirmed = True

                    queue_wait_ms = None
                    if isinstance(enqueued_at_monotonic, (int, float)):
                        queue_wait_ms = max(0.0, (asset_started_at - float(enqueued_at_monotonic)) * 1000.0)
                    _debug_perf_log(
                        LOGGER,
                        "automatic_migration.asset.pipeline",
                        asset_started_at,
                        worker=worker_id,
                        album=album_name or "-",
                        asset=os.path.basename(asset_file_path),
                        source_asset_id=source_asset_id,
                        queue_wait_ms=f"{queue_wait_ms:.2f}" if queue_wait_ms is not None else None,
                        push_ms=f"{push_elapsed_ms:.2f}" if push_elapsed_ms is not None else None,
                        album_assoc_ms=f"{album_assoc_elapsed_ms:.2f}" if album_assoc_elapsed_ms is not None else None,
                        cleanup_ms=f"{cleanup_elapsed_ms:.2f}" if cleanup_elapsed_ms is not None else None,
                        duplicated=isDuplicated,
                        asset_pushed=asset_pushed,
                        consumed=treat_as_consumed,
                        album_association_confirmed=album_association_confirmed,
                        scheduled_retry=scheduled_retry,
                    )

                except Exception as e:
                    asset_file_path = asset.get('asset_file_path') if isinstance(asset, dict) else ""
                    album_name = asset.get('album_name') if isinstance(asset, dict) else None
                    asset_type = asset.get('asset_type', 'photo') if isinstance(asset, dict) else 'photo'
                    count_push_stats = asset.get('count_push_stats', True) if isinstance(asset, dict) else True
                    scheduled_retry = _schedule_asset_retry(
                        asset=asset if isinstance(asset, dict) else {},
                        reason=f"unexpected pusher exception: {str(e)}",
                    ) if isinstance(asset, dict) else False
                    if not scheduled_retry:
                        if album_name:
                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'. Album: '{album_name}'")
                        else:
                            LOGGER.error(f"Asset Push Fail : '{os.path.basename(asset_file_path)}'")
                        LOGGER.error(f"Caught Exception: {str(e)} \n{traceback.format_exc()}")
                        _record_final_push_failure(asset_type=asset_type, count_push_stats=count_push_stats)
                finally:
                    if asset is not None and isinstance(asset, dict):
                        _unmark_asset_path_in_flight(asset.get('asset_file_path'))
                        _unmark_asset_path_in_flight(asset.get('live_photo_video_path'))
                    if asset is not None:
                        push_queue.task_done()

            LOGGER.info(f"Pusher {worker_id} - Task Finished!")

    # ----------------------------
    # 4) LLAMADA AL HILO PRINCIPAL
    # ----------------------------

    # Inicializamos start_time para medir el tiempo de procesamiento
    migration_start_time = datetime.now()

    # Preparar la cola que compartiremos entre descargas y subidas
    # push_queue = Queue()
    class MonitoredPriorityQueue(PriorityQueue):
        def put(self, item, *args, **kwargs):
            super().put(item, *args, **kwargs)
            _refresh_queue_depth()

        def get(self, *args, **kwargs):
            item = super().get(*args, **kwargs)
            _refresh_queue_depth()
            return item

    push_queue = MonitoredPriorityQueue() if push_queue_priority_enabled else MonitoredQueue()
    album_assoc_queue = MonitoredQueue()

    # Set global para almacenar paths ya añadidos
    added_file_paths = set()

    # Lock global para proteger el acceso concurrente
    file_paths_lock = threading.Lock()

    # Normalizamos temp_folder
    temp_folder = normalize_path(temp_folder)

    # Listas de posibles etiquetas para los distintos tipos de archivos en los diferentes clientes
    image_labels = ['photo', 'image']
    video_labels = ['video', 'live']
    metadata_labels = ['metadata']
    sidecar_labels = ['sidecar']

    # Check if parallel=None, and in that case, get it from ARGS
    if parallel is None: parallel = ARGS['parallel-migration']

    # Llamada al hilo principal
    main_thread(parallel=parallel, log_level=log_level)


###########################
# start_dashboard Function #
###########################
def start_dashboard(migration_finished, SHARED_DATA, parallel=True, step_name='', log_level=None):
    with set_log_level(LOGGER, log_level):
        import time
        from datetime import datetime
        from rich.console import Console
        from rich.layout import Layout
        from rich.progress import Progress, BarColumn, TextColumn
        from rich.table import Table
        from rich.panel import Panel
        from rich.live import Live
        from rich.text import Text
        from rich.markup import escape
        import textwrap
        import traceback

        # # 1) Creamos un logger hijo para este hilo y lo asignamos a la variable LOGGER local
        # from Core.GlobalVariables import LOGGER as GV_LOGGER
        # thread_id = threading.get_ident()
        # LOGGER = GV_LOGGER.getChild(f"dashboard-{thread_id}")

        # 🚀 Guardar stdout y stderr originales
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        # Creamos la consola antes de enganchar excepciones
        console = Console()

        # Install a global exception hook for this thread
        def exception_hook(exctype, value, tb):
            """Catch uncaught exceptions and log + print them, then restore cursor."""
            error_msg = "".join(traceback.format_exception(exctype, value, tb))
            LOGGER.warning(f"{step_name}Unhandled exception in Live Dashboard:\n{error_msg}")
            try:
                console.show_cursor()
            except:
                pass
            original_stdout.write(error_msg)

        # 🚀 Capturar e interceptar manualmente cualquier error antes de que `rich` lo maneje
        sys.excepthook = exception_hook

        try:
            # Min Terminal Height and Width to display the Live Dashboard
            MIN_TERMINAL_HEIGHT = 30
            MIN_TERMINAL_WIDTH = 100

            # Background Progress Bar Tittle
            BG_PROGRESS_BAR_TITTLE_WIDTH = 60

            # Calculate terminal_height and terminal_width
            forced_height = int(str(os.environ.get("PHOTOMIGRATOR_TUI_LOG_HEIGHT") or "0").strip() or 0)
            forced_width = int(str(os.environ.get("PHOTOMIGRATOR_TUI_LOG_WIDTH") or "0").strip() or 0)
            terminal_height = forced_height if forced_height > 0 else console.size.height
            terminal_width = forced_width if forced_width > 0 else console.size.width

            LOGGER.info(f"Detected terminal height = {terminal_height}")
            LOGGER.info(f"Detected terminal width  = {terminal_width}")

            # In web-interface mode, the browser dashboard is the canonical live renderer.
            if os.environ.get("PHOTOMIGRATOR_WEB_MODE") == "1":
                LOGGER.info("Using Web Interface Live Dashboard...")
                ARGS['dashboard'] = False
                return

            if terminal_height < MIN_TERMINAL_HEIGHT:
                LOGGER.info(f"Cannot display Live Dashboard because the detected terminal height = {terminal_height} and the minumum needed height = {MIN_TERMINAL_HEIGHT}. Continuing without Live Dashboard...")
                ARGS['dashboard'] = False  # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
                return

            if terminal_width < MIN_TERMINAL_WIDTH:
                LOGGER.info(f"Cannot display Live Dashboard because the detected terminal width = {terminal_width} and the minumum needed width = {MIN_TERMINAL_WIDTH}. Continuing without Live Dashboard...")
                ARGS['dashboard'] = False  # Set this argument to False to avoid use TQDM outputs as if a Interactive Terminal (isatty() = True)
                return

            # Iniciamos el contador de tiempo transcurrido
            step_start_time = datetime.now()

            layout = Layout()
            layout.size = terminal_height

            # # 🚀 Forzar la redirección de sys.stderr globalmente para asegurar que no se imprima en pantalla
            # sys.stderr = sys.__stderr__ = LoggerCapture(LOGGER, logging.ERROR)
            #
            # # 🚀 Capturar e interceptar manualmente cualquier error antes de que `rich` lo maneje
            # def log_exceptions(exctype, value, tb):
            #     """Captura todas las excepciones no manejadas y las guarda en el LOGGER sin imprimir en pantalla"""
            #     error_message = "".join(traceback.format_exception(exctype, value, tb))
            #     LOGGER.error(f"Excepción no manejada:\n" + error_message)  # Guardar en logs sin imprimir en consola
            #
            # sys.excepthook = log_exceptions

            # Eliminar solo los StreamHandler sin afectar los FileHandler
            for handler in list(LOGGER.handlers):  # Hacer una copia de la lista para evitar problemas al modificarla
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    LOGGER.removeHandler(handler)

            # Crea el handler y configúralo con un formatter
            memory_handler = CustomInMemoryLogHandler(SHARED_DATA.logs_queue)
            memory_handler.setFormatter(CustomConsoleFormatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
            memory_handler.setLevel(log_level if log_level is not None else logging.INFO)
            memory_handler.accept_tqdm = True

            # Agrega el handler al LOGGER
            LOGGER.addHandler(memory_handler)

            # Opcional: si NO quieres imprimir por consola, puedes quitar el StreamHandler que tenga el logger por defecto (así solo se registran en la lista).
            # Por ejemplo:
            LOGGER.propagate = False
            log_file = get_logger_filename(LOGGER)

            # Split layout: header_panel (8 lines), title_panel (3 lines), content_panel (12 lines),
            # logs fill remainder, background_progress_panel (7 lines) at the bottom.
            layout.split_column(
                Layout(name="empty_line_1", size=1),  # Línea vacía
                Layout(name="header_panel", size=8),
                Layout(name="title_panel", size=3),
                Layout(name="content_panel", size=12),
                Layout(name="logs_panel", ratio=1),
                Layout(name="background_progress_panel", size=7),
                Layout(name="empty_line_2", size=1),  # Línea vacía
            )

            # Obtener el height de cada panel
            empty_line_1_height = layout["empty_line_1"].size
            header_panel_height = layout["header_panel"].size
            title_panel_height = layout["title_panel"].size
            content_panel_height = layout["content_panel"].size
            background_progress_panel_height = layout["background_progress_panel"].size
            empty_line_2_height = layout["empty_line_2"].size

            # Calcular logs_panel en función del espacio restante
            fixed_heights = sum([empty_line_1_height, header_panel_height, title_panel_height, content_panel_height, background_progress_panel_height, empty_line_2_height])

            # Asegurar que la línea vacía no tenga bordes ni contenido visible
            layout["empty_line_1"].update("")
            layout["empty_line_2"].update("")

            # Split content_panel horizontally into 3 panels
            layout["content_panel"].split_row(
                Layout(name="info_panel", ratio=3),
                Layout(name="pulls_panel", ratio=4),
                Layout(name="pushs_panel", ratio=4),
            )

            # ─────────────────────────────────────────────────────────────────────────
            # 0) Header Panel
            # ─────────────────────────────────────────────────────────────────────────
            header = textwrap.dedent(rf"""
             ____  _           _        __  __ _                 _
            |  _ \| |__   ___ | |_ ___ |  \/  (_) __ _ _ __ __ _| |_ ___  _ __
            | |_) | '_ \ / _ \| __/ _ \| |\/| | |/ _` | '__/ _` | __/ _ \| '__|
            |  __/| | | | (_) | || (_) | |  | | | (_| | | | (_| | || (_) | |
            |_|   |_| |_|\___/ \__\___/|_|  |_|_|\__, |_|  \__,_|\__\___/|_|
                                                 |___/ {TOOL_VERSION} ({TOOL_DATE})
            """).lstrip("\n")  # Elimina solo la primera línea en blanco

            layout["header_panel"].update(Panel(f"[gold1]{header}[/gold1]", border_style="gold1", expand=True))

            # ─────────────────────────────────────────────────────────────────────────
            # 1) Title Panel
            # ─────────────────────────────────────────────────────────────────────────
            title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automatic Migration - {TOOL_NAME_VERSION}"

            layout["title_panel"].update(Panel(f"🚀 {title}", border_style="bright_blue", expand=True))

            def update_title_panel():
                title = f"[bold cyan]{SHARED_DATA.info.get('source_client_name')}[/bold cyan] 🡆 [green]{SHARED_DATA.info.get('target_client_name')}[/green] - Automatic Migration - {TOOL_NAME_VERSION}"
                layout["title_panel"].update(Panel(f"🚀 {title}", border_style="bright_blue", expand=True))

            # ─────────────────────────────────────────────────────────────────────────
            # 2) Info Panel
            # ─────────────────────────────────────────────────────────────────────────

            def build_info_panel(clean_queue_history=False):
                """Construye el panel de información con historial de la cola."""
                # 🔹 Calcular el ancho real de "info_panel"

                total_ratio = 3 + 4 + 4  # Suma de los ratios en split_row()
                info_panel_ratio = 3  # Ratio de "info_panel"

                # Recompute with current terminal width on each render (supports resize).
                current_terminal_width = max(40, int(getattr(console.size, "width", terminal_width) or terminal_width))
                info_panel_width = max(30, (current_terminal_width * info_panel_ratio) // total_ratio)

                # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # # Histograma temporal de la cola con barras como estas "  ▁▂▃▄▅▆▇█"  o estas "▁▂▄▆█"
                # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # # 🔹 Unicode para representar la barra de progreso vertical (10 niveles)
                # BARS = "  ▁▂▃▄▅▆▇█"     # Se agregan 10 barras
                # BARS = "▁▂▄▆█"          # # Se agregan 5 barras
                #
                # # 🔹 Inicializar el historial de la cola dentro de la función
                # if not hasattr(build_info_panel, "queue_history"):
                #     build_info_panel.queue_history = collections.deque(maxlen=info_panel_width-31)
                # queue_history = build_info_panel.queue_history
                #
                # # 🔹 Obtener el tamaño actual de la cola
                # current_queue_size = SHARED_DATA.info.get('assets_in_queue', 0)
                #
                # # 🔹 Actualizar historial de la cola
                # queue_history.append(current_queue_size)
                #
                # # 🔹 Definir los rangos de normalización (10 bloques de tamaño 10 cada uno)
                # num_blocks = len(BARS)
                # block_size = 100 / num_blocks  # Cada bloque cubre 10 unidades
                #
                # # 🔹 Asignar la barra correspondiente a cada valor de la cola
                # progress_bars = [BARS[min(int(val // block_size), num_blocks - 1)] for val in queue_history]
                #
                # # 🔹 Unimos todas las barras
                # queue_display = "".join(progress_bars)

                # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # Barra de cola actual. Muestre una barra horizontal rellenable "███████████████████", cuando esté llena "██████████" cuando esté a la mitad, "██" cuando esté casi vacía
                # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                # 🔹 Definir el ancho de la barra de progreso dinámicamente
                label_col_width = 20
                panel_overhead = 8  # panel borders + paddings + table separators (approx)
                counter_width = 8 if parallel else 7
                BAR_WIDTH = max(3, info_panel_width - label_col_width - panel_overhead - counter_width)
                # 🔹 Obtener backlog real (queued + in-flight) para evitar que qsize() aparente 0
                #     cuando los push workers hacen get() pero aún están procesando.
                raw_queue_size = int(SHARED_DATA.info.get('assets_in_queue', 0) or 0)
                inferred_queue_size = max(
                    0,
                    int(SHARED_DATA.counters.get('total_pulled_assets', 0) or 0)
                    - int(SHARED_DATA.counters.get('total_pushed_assets', 0) or 0)
                    - int(SHARED_DATA.counters.get('total_push_failed_assets', 0) or 0)
                    - int(SHARED_DATA.counters.get('total_push_duplicates_assets', 0) or 0)
                )
                current_queue_size = max(raw_queue_size, inferred_queue_size)
                total_assets = int(SHARED_DATA.info.get('total_assets', 0) or 0)
                processed_assets = min(
                    total_assets,
                    max(0, int(SHARED_DATA.counters.get('total_pulled_assets', 0) or 0))
                )
                pending_assets = max(0, total_assets - processed_assets)
                elapsed_seconds = max(0.0, (datetime.now() - step_start_time).total_seconds())
                SHARED_DATA.info["estimated_time"] = _compute_dashboard_estimated_time(
                    elapsed_seconds=elapsed_seconds,
                    processed_assets=processed_assets,
                    pending_assets=pending_assets,
                    total_assets=total_assets,
                )
                # 🔹 Normalizar el tamaño de la cola dentro del rango de la barra
                filled_blocks = min(int((current_queue_size / 100) * BAR_WIDTH), BAR_WIDTH)
                empty_blocks = BAR_WIDTH - filled_blocks
                # 🔹 Crear la barra de progreso con "█" y espacios
                queue_bar = "█" * filled_blocks + " " * empty_blocks
                if parallel:
                    # 🔹 Mostrar la barra con la cantidad actual de elementos en la cola y el máximo de 100 al final
                    queue_bar = f"[{queue_bar}] {current_queue_size:>3}/100"
                else:
                    # 🔹 Mostrar la barra con la cantidad actual de elementos en la cola aquí sin máximo, y dando espacio para 7 dígitos
                    queue_bar = f"[{queue_bar}] {current_queue_size:>7}"
                # 🔹 borra la barra al final
                if clean_queue_history:
                    queue_bar = 0

                # 🔹 Datos a mostrar
                info_data = [
                    ("🎯 Total Assets", SHARED_DATA.info.get('total_assets', 0)),
                    ("📷 Total Photos", SHARED_DATA.info.get('total_photos', 0)),
                    ("🎬 Total Videos", SHARED_DATA.info.get('total_videos', 0)),
                    ("📂 Total Albums", SHARED_DATA.info.get('total_albums', 0)),
                    ("🔒 Blocked Albums", SHARED_DATA.info.get('total_albums_blocked', 0)),
                    ("📜 Total Metadata", SHARED_DATA.info.get('total_metadata', 0)),
                    ("🔗 Total Sidecar", SHARED_DATA.info.get('total_sidecar', 0)),
                    ("🔍 Invalid Files", SHARED_DATA.info.get('total_invalid', 0)),
                    ("📊 Assets in Queue", f"{queue_bar}"),
                    ("🕒 Elapsed Time", SHARED_DATA.info.get('elapsed_time', 0)),
                    ("⏳ Estimated Time", SHARED_DATA.info.get('estimated_time', "-")),
                ]

                # 🔹 Crear la tabla
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=20, no_wrap=True)
                table.add_column(justify="right", ratio=1, no_wrap=True, overflow="crop")
                for label, value in info_data:
                    table.add_row(f"[bright_magenta]{label:<17}: [/bright_magenta]", f"[bright_magenta]{value}[/bright_magenta]")

                # 🔹 Devolver el panel
                return Panel(table, title="📊 Info Panel", border_style="bright_magenta", expand=True, padding=(0, 1))


            # ─────────────────────────────────────────────────────────────────────────
            # 3) Progress Bars for pulls / pushs
            #    Show "X / total" with a bar, no custom chars
            # ─────────────────────────────────────────────────────────────────────────
            def create_progress_bar(color: str) -> Progress:
                """
                Creates a bar with a longer width and displays 'X / total items' in color.
                """
                counter = f"{{task.completed}}/{{task.total}}"
                return Progress(
                    BarColumn(
                        bar_width=100,  # longer bar for better visuals
                        style=f"{color} dim",
                        complete_style=f"{color} bold",
                        finished_style=f"{color} bold",
                        pulse_style="bar.pulse"
                        # pulse_style=f"{color} bold"
                    ),
                    TextColumn(f"[{color}]{counter:>15}[/{color}]"),
                    console=console,
                    expand=True
                )


            # PULLS (Cyan)
            pull_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
                "🎯 Pulled Assets": (create_progress_bar("cyan"), 'total_pulled_assets', "total_assets"),
                "📷 Pulled Photos": (create_progress_bar("cyan"), 'total_pulled_photos', "total_photos"),
                "🎬 Pulled Videos": (create_progress_bar("cyan"), 'total_pulled_videos', "total_videos"),
                "📂 Pulled Albums": (create_progress_bar("cyan"), 'total_pulled_albums', "total_albums"),
            }
            failed_pulls = {
                "🔒 Blocked Albums": 'total_albums_blocked',
                "🔒 Blocked Assets": 'total_assets_blocked',
                "🚩 Failed Assets": 'total_pull_failed_assets',
                "🚩 Failed Photos": 'total_pull_failed_photos',
                "🚩 Failed Videos": 'total_pull_failed_videos',
                "🚩 Failed Albums": 'total_pull_failed_albums',
            }
            pull_tasks = {}
            for label, (bar, completed_label, total_label) in pull_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                pull_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))

            # PUSHS (Green)
            push_bars = {  # Dicccionario de Tuplas (bar, etiqueta_contador_completados, etiqueta_contador_totales)
                "🎯 Pushed Assets": (create_progress_bar("green"), 'total_pushed_assets', "total_assets"),
                "📷 Pushed Photos": (create_progress_bar("green"), 'total_pushed_photos', "total_photos"),
                "🎬 Pushed Videos": (create_progress_bar("green"), 'total_pushed_videos', "total_videos"),
                "📂 Pushed Albums": (create_progress_bar("green"), 'total_pushed_albums', "total_albums"),
            }
            failed_pushs = {
                "🧩 Duplicates": 'total_push_duplicates_assets',
                "🚩 Failed Assets": 'total_push_failed_assets',
                "🚩 Failed Photos": 'total_push_failed_photos',
                "🚩 Failed Videos": 'total_push_failed_videos',
                "🚩 Failed Albums": 'total_push_failed_albums',
            }
            push_tasks = {}
            for label, (bar, completed_label, total_label) in push_bars.items():
                # bar.add_task retturns the task_id and we create a dictionary {task_label: task_id}
                push_tasks[label] = bar.add_task(label, completed=SHARED_DATA.counters.get(completed_label), total=SHARED_DATA.info.get(total_label, 0))


            # ─────────────────────────────────────────────────────────────────────────
            # 4) Build the Pull/Push Panels
            # ─────────────────────────────────────────────────────────────────────────
            def build_pull_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=20)
                table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in pull_bars.items():
                    table.add_row(f"[cyan]{label:<17}:[/cyan]", bar)
                    bar.update(pull_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                for label, counter_label in failed_pulls.items():
                    value = SHARED_DATA.counters[counter_label]
                    table.add_row(f"[cyan]{label:<17}:[/cyan]", f"[cyan]{value}[/cyan]")
                return Panel(table, title=f'📥 From: {SHARED_DATA.info.get("source_client_name", "Source Client")}', border_style="cyan", expand=True)


            def build_push_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=19)
                table.add_column(justify="right")
                for label, (bar, completed_labeld, total_label) in push_bars.items():
                    table.add_row(f"[green]{label:<16}:[/green]", bar)
                    bar.update(push_tasks[label], completed=SHARED_DATA.counters.get(completed_labeld), total=SHARED_DATA.info.get(total_label, 0))
                for label, counter_label in failed_pushs.items():
                    value = SHARED_DATA.counters[counter_label]
                    table.add_row(f"[green]{label:<16}:[/green]", f"[green]{value}[/green]")
                return Panel(table, title=f'📤 To: {SHARED_DATA.info.get("target_client_name", "Source Client")}', border_style="green", expand=True)

            # -------------------------------------------------------------------------
            # 5) Background Progress Panel (capture any tqdm emitted in background)
            # -------------------------------------------------------------------------
            bg_progress_rows = {}
            bg_progress_colors = ["bright_yellow", "bright_blue", "bright_magenta", "bright_green"]
            bg_completed_retention_sec = 5.0
            bg_indeterminate_idle_retention_sec = 2.0
            bg_progress_next_color_idx = 0
            bg_progress_version = 0

            def _create_bg_bar(color, has_total=True):
                counter = "{task.completed}/{task.total}" if has_total else "{task.completed}"
                pulse_style = "bar.pulse" if has_total else f"{color} bold"
                return Progress(
                    BarColumn(
                        bar_width=None,
                        style=f"{color} dim",
                        complete_style=f"{color} bold",
                        finished_style=f"{color} bold",
                        # pulse_style="bar.pulse",
                        pulse_style=pulse_style,
                    ),
                    TextColumn(f"[{color}]{counter:>15}[/{color}]"),
                    console=console,
                    expand=True,
                )

            def _upsert_bg_progress(desc, current, total=None):
                nonlocal bg_progress_next_color_idx, bg_progress_version
                label = _normalize_bg_progress_desc(desc)
                current_value = max(0, int(current))
                has_total = total is not None and int(total) > 0
                total_value = max(1, int(total)) if has_total else None
                key = f"{label.lower()}::{'determinate' if has_total else 'indeterminate'}::{total_value if has_total else 0}"
                if key not in bg_progress_rows:
                    color = bg_progress_colors[bg_progress_next_color_idx % len(bg_progress_colors)]
                    bg_progress_next_color_idx += 1
                    bar = _create_bg_bar(color, has_total=has_total)
                    task_id = bar.add_task(label, completed=0, total=total_value)
                    bg_progress_rows[key] = {
                        "label": label,
                        "color": color,
                        "bar": bar,
                        "task_id": task_id,
                        "last_update": time.time(),
                        "completed": False,
                        "has_total": has_total,
                    }

                info = bg_progress_rows[key]
                if info.get("has_total"):
                    done = max(0, min(current_value, total_value))
                    info["bar"].update(info["task_id"], completed=done, total=total_value)
                    info["completed"] = done >= total_value
                else:
                    info["bar"].update(info["task_id"], completed=current_value, total=None)
                    info["completed"] = False
                info["last_update"] = time.time()
                bg_progress_version += 1
                return True

            def _prune_bg_progress_rows(now=None):
                nonlocal bg_progress_version
                if now is None:
                    now = time.time()
                to_delete = []
                for key, info in bg_progress_rows.items():
                    age = now - float(info.get("last_update", now))
                    if info.get("completed") and age > bg_completed_retention_sec:
                        to_delete.append(key)
                        continue
                    if not info.get("has_total") and age > bg_indeterminate_idle_retention_sec:
                        to_delete.append(key)
                if not to_delete:
                    return False
                for key in to_delete:
                    bg_progress_rows.pop(key, None)
                bg_progress_version += 1
                return True

            def _consume_progress_line(line):
                parsed = _parse_dashboard_progress_line(line)
                if not parsed:
                    return False
                return _upsert_bg_progress(
                    parsed["desc"],
                    parsed["current"],
                    parsed["total"] if parsed.get("has_total") else None,
                )

            def build_background_progress_panel():
                table = Table.grid(expand=True)
                table.add_column(justify="left", width=BG_PROGRESS_BAR_TITTLE_WIDTH, no_wrap=True, overflow="ellipsis")
                table.add_column(justify="left", ratio=1, no_wrap=True)

                if bg_progress_rows:
                    panel_height = int(getattr(layout["background_progress_panel"], "size", background_progress_panel_height) or background_progress_panel_height)
                    visible_limit = max(1, panel_height - 2)
                    ordered = _select_visible_bg_progress_rows(bg_progress_rows.values(), visible_limit)
                    for info in ordered:
                        label = escape(str(info.get("label", "Progress")))
                        table.add_row(f"[{info['color']}]{label}[/{info['color']}]", info["bar"])
                else:
                    table.add_row("", "")

                return Panel(table, title="⏳ Background Progress", border_style="bright_cyan", expand=True, padding=(0, 1))

            # ─────────────────────────────────────────────────────────────────────────
            # 6) Logging Panel from Memmory Handler
            # ─────────────────────────────────────────────────────────────────────────
            # Lista (o deque) para mantener todo el historial de logs ya mostrados
            ACCU_LOGS = deque(maxlen=2000)
            logs_version = 0

            def _current_logs_panel_height():
                panel_size = getattr(layout["logs_panel"], "size", None)
                if isinstance(panel_size, int) and panel_size > 0:
                    return max(1, panel_size - 2)
                return max(1, terminal_height - fixed_heights - 2)

            def _drain_logs_queue():
                """
                Consume queued logs/events and updates in-memory states.
                Returns True when log panel content changed.
                """
                nonlocal logs_version
                changed = False
                while True:
                    try:
                        line = SHARED_DATA.logs_queue.get_nowait()
                    except Empty:
                        break

                    # Route tqdm/progress lines to Background Progress panel.
                    if _consume_progress_line(line):
                        continue

                    clean_line = BG_ANSI_ESCAPE_RE.sub("", str(line or "").replace("\r", "")).rstrip()
                    if not clean_line:
                        continue
                    safe_line = clean_line

                    line_lower = clean_line.lower()
                    event_line = re.sub(r"^(VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*:\s*", "", clean_line, flags=re.IGNORECASE).strip()
                    event_lower = event_line.lower()
                    if "warning :" in line_lower:
                        line_style = "yellow"
                    elif "error   :" in line_lower:
                        line_style = "red"
                    elif "debug   :" in line_lower:
                        line_style = "#EEEEEE"
                    elif "delayed" in line_lower:
                        line_style = "bright_black"
                    elif event_lower.startswith("asset pulled"):
                        line_style = "cyan"
                    elif event_lower.startswith("asset pushed"):
                        line_style = "green"
                    elif event_lower.startswith("album created"):
                        line_style = "bright_white"
                    elif event_lower.startswith("album pulled"):
                        line_style = "bright_cyan"
                    elif event_lower.startswith("album pushed"):
                        line_style = "bright_green"
                    elif event_lower.startswith("asset duplicated"):
                        line_style = "#9da7ad"
                    elif event_lower.startswith("asset fail") or event_lower.startswith("asset failed"):
                        line_style = "yellow"
                    else:
                        line_style = "bright_white"

                    for visual_line in str(safe_line).splitlines():
                        if visual_line.strip():
                            ACCU_LOGS.append((visual_line, line_style))
                            changed = True

                if changed:
                    logs_version += 1
                return changed

            def build_log_panel():
                logs_panel_height = _current_logs_panel_height()
                title_logs_panel = f"📜 Logs Panel (Only last {logs_panel_height} rows shown. Complete log file at: '{FOLDERNAME_LOGS}/{os.path.basename(log_file)}')"
                try:
                    if ACCU_LOGS:
                        logs_text = Text(no_wrap=True, overflow="crop")
                        visible_logs = list(ACCU_LOGS)[-max(1, logs_panel_height):]
                        logs_count = len(visible_logs)
                        for idx, entry in enumerate(visible_logs):
                            visual_line, visual_style = entry
                            logs_text.append(visual_line, style=visual_style)
                            if idx < logs_count - 1:
                                logs_text.append("\n")
                    else:
                        logs_text = Text("Initializing...", no_wrap=True, overflow="crop")
                    return Panel(logs_text, title=title_logs_panel, border_style="bright_red", expand=True, title_align="left")
                except Exception as e:
                    LOGGER.error(f"Building Log Panel: {e}")
                    return Panel("Error building log panel", title="📜 Logs Panel", border_style="bright_red", expand=True, title_align="left")

            def _build_info_signature():
                keys = (
                    "total_assets", "total_photos", "total_videos", "total_albums", "total_albums_blocked",
                    "total_metadata", "total_sidecar", "total_invalid", "assets_in_queue", "estimated_time",
                )
                return tuple(SHARED_DATA.info.get(k) for k in keys)

            def _build_pull_signature():
                completed_keys = [cfg[1] for cfg in pull_bars.values()]
                total_keys = [cfg[2] for cfg in pull_bars.values()]
                failed_keys = list(failed_pulls.values())
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                )

            def _build_push_signature():
                completed_keys = [cfg[1] for cfg in push_bars.values()]
                total_keys = [cfg[2] for cfg in push_bars.values()]
                failed_keys = list(failed_pushs.values())
                return (
                    tuple(SHARED_DATA.counters.get(k, 0) for k in completed_keys + failed_keys),
                    tuple(SHARED_DATA.info.get(k, 0) for k in total_keys),
                )

            def _sync_terminal_size():
                nonlocal terminal_height, terminal_width
                new_height = max(1, int(getattr(console.size, "height", terminal_height) or terminal_height))
                new_width = max(1, int(getattr(console.size, "width", terminal_width) or terminal_width))
                if new_height == terminal_height and new_width == terminal_width:
                    return False
                terminal_height = new_height
                terminal_width = new_width
                layout.size = terminal_height
                return True

            def _wait_for_any_key_to_close_dashboard():
                """
                Keep final dashboard visible until user confirms close (interactive CLI only).
                """
                stdin_is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
                stdout_is_tty = bool(getattr(original_stdout, "isatty", lambda: False)())
                if not (stdin_is_tty and stdout_is_tty):
                    return
                try:
                    if os.name == "nt":
                        import msvcrt
                        # Flush pending keypresses (e.g., buffered Enter) to avoid instant close.
                        while msvcrt.kbhit():
                            msvcrt.getch()
                        msvcrt.getch()
                    else:
                        import termios
                        import tty
                        fd = sys.stdin.fileno()
                        old_settings = termios.tcgetattr(fd)
                        try:
                            termios.tcflush(fd, termios.TCIFLUSH)
                            tty.setraw(fd)
                            os.read(fd, 1)
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except KeyboardInterrupt:
                    pass
                except Exception:
                    # Never fail dashboard shutdown due to input handling issues.
                    pass


            # ─────────────────────────────────────────────────────────────────────────
            # 6) Main Live Loop
            # ─────────────────────────────────────────────────────────────────────────
            LOGGER.debug(f"{step_name}Dashboard initialized (parallel={parallel})")
            with Live(layout, refresh_per_second=4, auto_refresh=False, screen=True, console=console, vertical_overflow="crop") as live:
                try:
                    min_refresh_interval_sec = 1.0 / 60.0
                    elapsed_refresh_interval_sec = 1.0
                    last_render_ts = 0.0
                    last_elapsed_update_ts = 0.0
                    last_info_signature = None
                    last_pull_signature = None
                    last_push_signature = None
                    last_bg_version = -1
                    last_logs_version = -1

                    update_title_panel()
                    _drain_logs_queue()
                    _prune_bg_progress_rows()
                    SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                    layout["info_panel"].update(build_info_panel())
                    layout["pulls_panel"].update(build_pull_panel())
                    layout["pushs_panel"].update(build_push_panel())
                    layout["background_progress_panel"].update(build_background_progress_panel())
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()
                    last_render_ts = time.time()
                    last_elapsed_update_ts = last_render_ts
                    last_info_signature = _build_info_signature()
                    last_pull_signature = _build_pull_signature()
                    last_push_signature = _build_push_signature()
                    last_bg_version = bg_progress_version
                    last_logs_version = logs_version

                    # Continue the loop until migration_finished.is_set()
                    LOGGER.debug(f"{step_name}Starting Live loop")
                    while not migration_finished.is_set():
                        dirty = False

                        if _sync_terminal_size():
                            layout["info_panel"].update(build_info_panel())
                            layout["pulls_panel"].update(build_pull_panel())
                            layout["pushs_panel"].update(build_push_panel())
                            layout["background_progress_panel"].update(build_background_progress_panel())
                            layout["logs_panel"].update(build_log_panel())
                            last_info_signature = _build_info_signature()
                            last_pull_signature = _build_pull_signature()
                            last_push_signature = _build_push_signature()
                            last_bg_version = bg_progress_version
                            last_logs_version = logs_version
                            dirty = True

                        if _drain_logs_queue():
                            dirty = True
                        if _prune_bg_progress_rows():
                            dirty = True

                        info_signature = _build_info_signature()
                        if info_signature != last_info_signature:
                            layout["info_panel"].update(build_info_panel())
                            last_info_signature = info_signature
                            dirty = True

                        pull_signature = _build_pull_signature()
                        if pull_signature != last_pull_signature:
                            layout["pulls_panel"].update(build_pull_panel())
                            last_pull_signature = pull_signature
                            dirty = True

                        push_signature = _build_push_signature()
                        if push_signature != last_push_signature:
                            layout["pushs_panel"].update(build_push_panel())
                            last_push_signature = push_signature
                            dirty = True

                        if bg_progress_version != last_bg_version:
                            layout["background_progress_panel"].update(build_background_progress_panel())
                            last_bg_version = bg_progress_version
                            dirty = True

                        if logs_version != last_logs_version:
                            layout["logs_panel"].update(build_log_panel())
                            last_logs_version = logs_version
                            dirty = True

                        now_ts = time.time()
                        if now_ts - last_elapsed_update_ts >= elapsed_refresh_interval_sec:
                            SHARED_DATA.info["elapsed_time"] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                            layout["info_panel"].update(build_info_panel())
                            last_info_signature = _build_info_signature()
                            last_elapsed_update_ts = now_ts
                            dirty = True

                        if dirty and (now_ts - last_render_ts >= min_refresh_interval_sec):
                            live.refresh()
                            last_render_ts = now_ts
                        time.sleep(0.01)

                    # Pequeña pausa adicional para asegurar el dibujado final
                    time.sleep(1)

                    # Al terminar, asegurarse que todos los paneles finales se muestren
                    _drain_logs_queue()
                    _prune_bg_progress_rows()
                    SHARED_DATA.info['elapsed_time'] = str(timedelta(seconds=round((datetime.now() - step_start_time).total_seconds())))
                    layout["info_panel"].update(build_info_panel(clean_queue_history=True))  # Limpiamos el histórico de la cola
                    layout["pulls_panel"].update(build_pull_panel())
                    layout["pushs_panel"].update(build_push_panel())
                    layout["background_progress_panel"].update(build_background_progress_panel())
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()

                    # Keep final result visible in CLI until the user closes it.
                    LOGGER.info("Automatic Migration completed. Press any key to close the dashboard...")
                    _drain_logs_queue()
                    layout["logs_panel"].update(build_log_panel())
                    live.refresh()
                    _wait_for_any_key_to_close_dashboard()

                except ModuleNotFoundError as error:
                    missing = str(getattr(error, "name", "") or "")
                    if "rich._unicode_data.unicode" in missing:
                        LOGGER.warning(
                            f"{step_name}Live Dashboard disabled because bundled binary is missing Rich unicode tables "
                            f"({missing}). Continuing without dashboard."
                        )
                        ARGS['dashboard'] = False
                        return
                    err = traceback.format_exc()
                    LOGGER.warning(f"{step_name}Exception during Live Dashboard execution:\n{err}")
                    try:
                        console.show_cursor()
                    except:
                        pass
                    original_stdout.write(err)
                    raise
                except Exception:
                    # Catch any exception from Live Dashboard
                    err = traceback.format_exc()
                    LOGGER.warning(f"{step_name}Exception during Live Dashboard execution:\n{err}")
                    try:
                        console.show_cursor()
                    except:
                        pass
                    original_stdout.write(err)
                    raise

                finally:
                    # Always restore cursor and stdout/stderr
                    try:
                        console.show_cursor()
                    except:
                        pass
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr

        except Exception:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            traceback.print_exc()
            LOGGER.exception(f"ERROR during Automatic Migration Feature")
            raise
        finally:
            # Restaurar stdout y stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
######################
# CALL FROM __MAIN__ #
######################
if __name__ == "__main__":
    # Change Working Dir before to import GlobalVariables or other Modules that depends on it.

    change_working_dir(change_dir=False)

    # # Paths para Windows
    local_folder = r'r:\jaimetur\PhotoMigrator\LocalFolderClient'
    takeout_folder = r'r:\jaimetur\PhotoMigrator\Takeout'
    takeout_folder_zipped = r'r:\jaimetur\PhotoMigrator\Zip_files_prueba_rapida'

    # Paths para Linux
    # local_folder = r'/mnt/homes/jaimetur/PhotoMigrator/LocalFolderClient'
    # takeout_folder = r'/mnt/homes/jaimetur/PhotoMigrator/Takeout'
    # takeout_folder_zipped = r'/mnt/homes/jaimetur/PhotoMigrator/Zip_files_prueba_rapida'

    # Define source and target
    source = takeout_folder_zipped
    target = 'synology-photos'

    mode_AUTOMATIC_MIGRATION(source=source, target=target, show_dashboard=True, parallel=True, show_gpth_info=True)
