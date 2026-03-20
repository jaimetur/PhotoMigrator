import argparse
from collections import deque
from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, TextIO

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
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


class StateUpdateRequest(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)
    ui_state: Dict[str, Any] = Field(default_factory=dict)


class FolderCreateRequest(BaseModel):
    path: str = "/app/data"
    name: str = ""


class FolderDeleteRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)
    recursive: bool = True


class JobData:
    def __init__(self, command: List[str], process: subprocess.Popen[str], tab: str | None = None) -> None:
        self.command = command
        self.command_string = subprocess.list2cmdline(command)
        self.tab = str(tab or "").strip() or None
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
JOBS: Dict[str, JobData] = {}
JOBS_LOCK = threading.Lock()

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


def _build_cli_args(tab: str, values: Dict[str, Any], selected_action_dest: str | None = None) -> List[str]:
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


def _normalize_incoming_values(values: Dict[str, Any]) -> Dict[str, Any]:
    incoming_values = dict(values or {})
    for key, value in list(incoming_values.items()):
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if not trimmed.startswith("/docker"):
            continue
        if key == "configuration-file":
            incoming_values[key] = str(CONFIG_FILE_PATH)
        else:
            incoming_values[key] = trimmed.replace("/docker", "/app/data", 1)

    if not str(incoming_values.get("configuration-file", "")).strip():
        incoming_values["configuration-file"] = str(CONFIG_FILE_PATH)
    return incoming_values


def _build_command_from_payload(payload: RunRequest) -> List[str]:
    normalized_values = _normalize_incoming_values(payload.values or {})
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


def _allowed_delete_root_for_path(target: Path) -> Path | None:
    for root in DELETE_ALLOWED_ROOTS:
        try:
            target.relative_to(root)
            return root
        except ValueError:
            continue
    return None


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


def _read_config_content() -> str:
    if CONFIG_FILE_PATH.exists():
        return CONFIG_FILE_PATH.read_text(encoding="utf-8", errors="replace")
    fallback = PROJECT_ROOT / "Config.ini"
    if fallback.exists():
        return fallback.read_text(encoding="utf-8", errors="replace")
    return ""


def _read_state_payload() -> Dict[str, Any]:
    if not STATE_FILE_PATH.exists():
        return {"values": {}, "ui_state": {}}
    try:
        data = json.loads(STATE_FILE_PATH.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            values = data.get("values", {})
            ui_state = data.get("ui_state", {})
            if not isinstance(values, dict):
                values = {}
            if not isinstance(ui_state, dict):
                ui_state = {}
            return {"values": values, "ui_state": ui_state}
    except Exception:
        return {"values": {}, "ui_state": {}}
    return {"values": {}, "ui_state": {}}


def _save_state_payload(values: Dict[str, Any], ui_state: Dict[str, Any]) -> None:
    STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "values": values,
        "ui_state": ui_state,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    STATE_FILE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


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
    global PARSER_SCHEMA
    PARSER_SCHEMA = _load_parser_schema()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "tool_date": TOOL_DATE,
            "takeout_special_folders": list(TAKEOUT_SPECIAL_FOLDER_NAMES),
        },
    )


@app.get("/docs/view/{doc_name}", response_class=HTMLResponse)
def docs_view(request: Request, doc_name: str) -> HTMLResponse:
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
def docs_view_help_file(request: Request, doc_file: str) -> HTMLResponse:
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
def get_schema() -> Dict[str, Any]:
    return PARSER_SCHEMA


@app.get("/api/config")
def get_config() -> Dict[str, Any]:
    return {"path": str(CONFIG_FILE_PATH), "content": _read_config_content()}


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    payload = _read_state_payload()
    return {"path": str(STATE_FILE_PATH), "values": payload["values"], "ui_state": payload["ui_state"]}


@app.post("/api/state")
def save_state(payload: StateUpdateRequest) -> Dict[str, Any]:
    _save_state_payload(payload.values or {}, payload.ui_state or {})
    return {"saved": True, "path": str(STATE_FILE_PATH)}


@app.post("/api/config")
def save_config(payload: ConfigUpdateRequest) -> Dict[str, Any]:
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE_PATH.write_text(payload.content or "", encoding="utf-8")
    return {"saved": True, "path": str(CONFIG_FILE_PATH)}


@app.get("/api/docs/{doc_name}")
def get_markdown_doc(doc_name: str) -> Dict[str, Any]:
    path = _resolve_doc_path(doc_name)
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "name": doc_name,
        "path": str(path),
        "content": content,
    }


@app.get("/api/docs/help/{doc_file:path}")
def get_help_markdown_doc(doc_file: str) -> Dict[str, Any]:
    path = _resolve_help_doc_path(doc_file)
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "name": path.name,
        "path": str(path),
        "content": content,
    }


@app.get("/api/docs/help-index")
def get_help_docs_index() -> Dict[str, Any]:
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
def list_directories(path: str = Query(str(WEB_FS_ROOT))) -> Dict[str, Any]:
    current = Path(path).expanduser()
    if not current.is_absolute():
        current = (Path("/app") / current).resolve()
    if not current.exists():
        fallback_candidates = [WEB_FS_ROOT, WEB_HOME_PATH, Path("/app"), PROJECT_ROOT]
        fallback = next((candidate for candidate in fallback_candidates if candidate.exists() and candidate.is_dir()), None)
        if fallback is None:
            raise HTTPException(status_code=404, detail=f"Path not found: {current}")
        current = fallback
    if not current.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {current}")

    dirs = []
    for item in sorted(current.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir():
            dirs.append({"name": item.name, "path": str(item)})
    parent = str(current.parent) if current.parent != current else None
    return {"path": str(current), "parent": parent, "directories": dirs}


@app.get("/api/fs/list-files")
def list_csv_files(path: str = Query(str(WEB_FS_ROOT))) -> Dict[str, Any]:
    current = Path(path).expanduser()
    if not current.is_absolute():
        current = (Path("/app") / current).resolve()
    if not current.exists():
        fallback_candidates = [WEB_FS_ROOT, WEB_HOME_PATH, Path("/app"), PROJECT_ROOT]
        fallback = next((candidate for candidate in fallback_candidates if candidate.exists() and candidate.is_dir()), None)
        if fallback is None:
            raise HTTPException(status_code=404, detail=f"Path not found: {current}")
        current = fallback
    if not current.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {current}")

    dirs: List[Dict[str, str]] = []
    files: List[Dict[str, str]] = []
    for item in sorted(current.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir():
            dirs.append({"name": item.name, "path": str(item)})
        elif item.is_file() and item.suffix.lower() == ".csv":
            files.append({"name": item.name, "path": str(item)})
    parent = str(current.parent) if current.parent != current else None
    return {"path": str(current), "parent": parent, "directories": dirs, "files": files}


@app.post("/api/fs/mkdir")
def make_directory(payload: FolderCreateRequest) -> Dict[str, Any]:
    parent = Path(payload.path or "/app/data").expanduser()
    if not parent.is_absolute():
        parent = (Path("/app") / parent).resolve()
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid parent directory: {parent}")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name is required.")
    if name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Folder name is invalid.")

    name_path = Path(name).expanduser()
    if name_path.is_absolute():
        target = name_path.resolve()
        try:
            target.relative_to(WEB_FS_ROOT)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Absolute path must be inside home folder: {WEB_FS_ROOT}",
            )
    else:
        if "/" in name or "\\" in name:
            raise HTTPException(status_code=400, detail="Folder name cannot contain path separators.")
        target = (parent / name).resolve()

    if target.exists():
        raise HTTPException(status_code=409, detail=f"Folder already exists: {target}")
    target.mkdir(parents=True, exist_ok=False)
    return {"created": True, "path": str(target), "parent": str(parent)}


@app.post("/api/fs/rmdir")
def remove_directories(payload: FolderDeleteRequest) -> Dict[str, Any]:
    requested_paths = [str(item or "").strip() for item in (payload.paths or []) if str(item or "").strip()]
    if not requested_paths:
        raise HTTPException(status_code=400, detail="At least one folder path is required.")

    removed: List[str] = []
    failed: List[Dict[str, str]] = []

    for raw_path in requested_paths:
        target = Path(raw_path).expanduser()
        if not target.is_absolute():
            target = (Path("/app") / target).resolve()
        else:
            target = target.resolve()

        allowed_root = _allowed_delete_root_for_path(target)
        if allowed_root is None:
            allowed = ", ".join(str(root) for root in DELETE_ALLOWED_ROOTS)
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
def preview_cli(payload: RunRequest) -> Dict[str, Any]:
    command = _build_command_from_payload(payload)
    return {"command": subprocess.list2cmdline(command)}


@app.post("/api/run")
def run_cli(payload: RunRequest) -> Dict[str, Any]:
    normalized_values = _normalize_incoming_values(payload.values or {})
    required_dests = _required_dests_for_payload(payload.tab, payload.selected_action_dest)
    missing = [dest for dest in sorted(required_dests) if not _value_is_provided(dest, normalized_values)]
    if missing:
        joined = ", ".join(f"'--{dest}'" for dest in missing)
        raise HTTPException(status_code=400, detail=f"Missing required argument(s): {joined}")
    command = _build_command_from_payload(payload)
    child_env = os.environ.copy()
    child_env["PHOTOMIGRATOR_ALLOW_STDIN_PIPE"] = "1"
    child_env["PHOTOMIGRATOR_WEB_MODE"] = "1"
    child_env["PHOTOMIGRATOR_DOCKER_BASE_PATH"] = "/app/data"

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
        JOBS[job_id] = JobData(command=command, process=process, tab=payload.tab)

    thread = threading.Thread(target=_run_job, args=(job_id, process), daemon=True)
    thread.start()

    return {"job_id": job_id, "command": subprocess.list2cmdline(command)}


@app.get("/api/jobs/_active")
def get_active_job() -> Dict[str, Any]:
    with JOBS_LOCK:
        active_jobs = [
            (job_id, job)
            for job_id, job in JOBS.items()
            if job.status in {"running", "stopping"}
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
def get_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
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
def send_job_input(job_id: str, payload: JobInputRequest) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
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
def stop_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
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


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}
