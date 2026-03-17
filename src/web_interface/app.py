import argparse
import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Core.ArgsParser import parse_arguments  # noqa: E402
from Core.GlobalVariables import TOOL_DATE, TOOL_NAME, TOOL_VERSION  # noqa: E402


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

TAB_TO_CATEGORY = {
    "google_takeout": "google_takeout",
    "synology_photos": "synology_photos",
    "immich_photos": "immich_photos",
    "standalone_features": "standalone_features",
    "automatic_migration": "automatic_migration",
}


class RunRequest(BaseModel):
    tab: str
    values: Dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    content: str = ""


class StateUpdateRequest(BaseModel):
    values: Dict[str, Any] = Field(default_factory=dict)
    ui_state: Dict[str, Any] = Field(default_factory=dict)


class JobData:
    def __init__(self, command: List[str], process: subprocess.Popen[str]) -> None:
        self.command = command
        self.command_string = subprocess.list2cmdline(command)
        self.process = process
        self.awaiting_confirmation = False
        self.status = "running"
        self.output: List[str] = []
        self.return_code: int | None = None
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: str | None = None


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
            "synology_photos": cloud_common,
            "immich_photos": cloud_common,
            "standalone_features": [field for field in fields if field["tab"] == "standalone_features"],
            "automatic_migration": [field for field in fields if field["tab"] == "automatic_migration"],
        },
    }
    global PARSER_FIELDS_BY_DEST
    PARSER_FIELDS_BY_DEST = by_dest
    return schema


def _build_cli_args(tab: str, values: Dict[str, Any]) -> List[str]:
    if tab not in TAB_TO_CATEGORY:
        raise HTTPException(status_code=400, detail=f"Unsupported tab: {tab}")

    allowed_dests = {field["dest"] for field in PARSER_SCHEMA["general_tabs"]["general"]}
    allowed_dests.update(FEATURE_SCOPED_DESTS)
    allowed_dests.update(field["dest"] for field in PARSER_SCHEMA["tabs"][tab])

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

    if tab == "synology_photos":
        args.extend(["--client", "synology"])
    elif tab == "immich_photos":
        args.extend(["--client", "immich"])
    elif tab == "google_takeout":
        args.extend(["--client", "google-takeout"])

    return args


def _run_job(job_id: str, process: subprocess.Popen[str]) -> None:
    job = JOBS[job_id]
    try:
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(1)
            if chunk == "":
                break
            with JOBS_LOCK:
                job.output.append(chunk)
                lowered_tail = "".join(job.output[-2000:]).lower()
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
            job.status = "success" if rc == 0 else "failed"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.awaiting_confirmation = False
            job.process = None
    except Exception as exc:
        with JOBS_LOCK:
            job.output.append(f"\n[web-interface] Internal error: {exc}\n")
            job.return_code = -1
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc).isoformat()
            job.awaiting_confirmation = False
            job.process = None


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


@app.get("/api/fs/list")
def list_directories(path: str = Query("/app/data")) -> Dict[str, Any]:
    current = Path(path).expanduser()
    if not current.is_absolute():
        current = (Path("/app") / current).resolve()
    if not current.exists():
        fallback_candidates = [Path("/app/data"), Path("/app"), PROJECT_ROOT]
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


@app.post("/api/run")
def run_cli(payload: RunRequest) -> Dict[str, Any]:
    incoming_values = dict(payload.values or {})
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
    cli_args = _build_cli_args(payload.tab, incoming_values)
    command = [sys.executable, str(CLI_ENTRYPOINT), *cli_args]
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
        JOBS[job_id] = JobData(command=command, process=process)

    thread = threading.Thread(target=_run_job, args=(job_id, process), daemon=True)
    thread.start()

    return {"job_id": job_id, "command": subprocess.list2cmdline(command)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        job = JOBS[job_id]
        output = "".join(job.output[-200000:])
        can_send_input = bool(
            job.status == "running"
            and job.process is not None
            and job.process.stdin is not None
            and not job.process.stdin.closed
        )
        return {
            "job_id": job_id,
            "status": job.status,
            "return_code": job.return_code,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "command": job.command_string,
            "can_send_input": can_send_input,
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


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}
