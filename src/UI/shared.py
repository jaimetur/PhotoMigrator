import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import available_timezones

from Core.ArgsParser import parse_arguments

TIMEZONE_DEFAULT = "Europe/Madrid"
TIMEZONE_CHOICES = sorted(list(available_timezones()))
CONFIG_SECTIONS_ORDER = [
    "TimeZone",
    "Google Takeout",
    "iCloud Takeout",
    "Google Photos",
    "Synology Photos",
    "Immich Photos",
    "NextCloud Photos",
]
CONFIG_EDITOR_SECTIONS_ORDER = [
    "TimeZone",
    "Google Photos",
    "Synology Photos",
    "Immich Photos",
    "NextCloud Photos",
]
CONFIG_FEATURES_EXCLUDED_SECTIONS = {"Google Takeout", "iCloud Takeout"}

MODULE_TAB_NAMES = {
    "automatic_migration": "AUTOMATIC MIGRATION",
    "google_takeout": "GOOGLE TAKEOUT",
    "icloud_takeout": "iCLOUD TAKEOUT",
    "google_photos": "GOOGLE PHOTOS",
    "synology_photos": "SYNOLOGY PHOTOS",
    "immich_photos": "IMMICH PHOTOS",
    "nextcloud_photos": "NEXTCLOUD PHOTOS",
    "standalone_features": "OTHER FEATURES",
    "upload_folder": "UPLOAD TO SERVER",
}

GENERAL_TAB_NAMES = {
    "feature": "FEATURE",
    "general": "GENERAL ARGUMENTS",
    "features_config": "FEATURES CONFIG",
    "app_settings": "APP SETTINGS",
}

FEATURE_LABELS = {
    "upload-albums": "Upload Albums",
    "download-albums": "Download Albums",
    "upload-all": "Upload All",
    "download-all": "Download All",
    "rename-albums": "Rename Albums",
    "remove-albums": "Remove Albums",
    "remove-all-albums": "Remove All Albums",
    "remove-all-assets": "Remove All Assets",
    "remove-empty-albums": "Remove Empty Albums",
    "remove-duplicates-albums": "Remove Duplicates Albums",
    "merge-duplicates-albums": "Merge Duplicates Albums",
    "remove-orphan-assets": "Remove Orphan Assets",
    "fix-symlinks-broken": "Fix Broken Symlinks",
    "rename-folders-content-based": "Auto Rename Folders Content Based",
    "find-duplicates": "Find Duplicates",
    "process-duplicates": "Process Duplicates",
}

GENERAL_GROUPS = [
    {"key": "logs", "title": "Logs", "dests": ["no-log-file", "log-level", "log-format", "foldername-logs"]},
    {
        "key": "execution",
        "title": "Execution",
        "dests": ["no-request-user-confirmation", "exec-gpth-tool", "exec-exif-tool", "configuration-file", "remove-albums-assets"],
    },
    {
        "key": "naming",
        "title": "Naming & Folders",
        "dests": [
            "date-separator",
            "range-separator",
            "albums-folders",
            "foldername-albums",
            "foldername-no-albums",
            "foldername-duplicates-output",
            "foldername-extracted-dates",
        ],
    },
    {
        "key": "filters",
        "title": "Filters",
        "dests": [
            "filter-from-date",
            "filter-to-date",
            "filter-by-type",
            "filter-by-country",
            "filter-by-city",
            "filter-by-person",
            "exclude-folders",
            "exclude-files",
        ],
    },
]

BOOL_VALUE_DESTS = {
    "move-assets",
    "dashboard",
    "parallel-migration",
    "show-gpth-info",
    "show-gpth-errors",
}
AUTOMATION_DESTS = {"source", "target", "move-assets", "dashboard", "parallel-migration"}
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
ICLOUD_DESTS = {
    "icloud-takeout",
    "icloud-output-folder-suffix",
    "icloud-albums-folders-structure",
    "icloud-no-albums-folders-structure",
    "icloud-no-symbolic-albums",
    "icloud-include-memories",
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
    "immich_photos": {
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
STANDALONE_DESTS = {"fix-symlinks-broken", "rename-folders-content-based", "find-duplicates", "process-duplicates"}
GENERAL_CORE_DESTS = {
    "filter-from-date",
    "filter-to-date",
    "filter-by-type",
    "filter-by-country",
    "filter-by-city",
    "filter-by-person",
    "exclude-folders",
    "exclude-files",
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
FEATURE_SCOPED_DESTS = {"input-folder", "output-folder", "account-id"}
MODULE_DEPENDENCIES_REQUIRED = {
    "google_photos": {"download-albums": {"output-folder"}, "rename-albums": {"replacement-pattern"}},
    "synology_photos": {"download-albums": {"output-folder"}, "rename-albums": {"replacement-pattern"}},
    "immich_photos": {"download-albums": {"output-folder"}, "rename-albums": {"replacement-pattern"}},
    "nextcloud_photos": {"download-albums": {"output-folder"}, "rename-albums": {"replacement-pattern"}},
}
TAB_TO_CATEGORY = {
    "google_takeout": "google_takeout",
    "icloud_takeout": "icloud_takeout",
    "google_photos": "google_photos",
    "synology_photos": "synology_photos",
    "immich_photos": "immich_photos",
    "nextcloud_photos": "nextcloud_photos",
    "standalone_features": "standalone_features",
    "automatic_migration": "automatic_migration",
}


def _tab_for_dest(dest: str) -> str:
    if dest in AUTOMATION_DESTS:
        return "automatic_migration"
    if dest in GOOGLE_DESTS:
        return "google_takeout"
    if dest in ICLOUD_DESTS:
        return "icloud_takeout"
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
    if name in {"exclude-folders", "exclude-files"} or name.endswith("-suffix"):
        return ""
    metavar_text = str(metavar or "").lower()
    path_tokens = ("path", "folder", "file", "takeout", "source", "target")
    if any(token in name for token in path_tokens) or any(token in metavar_text for token in path_tokens):
        return "path"
    return ""


def bool_from_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "on"}
    return bool(value)


def to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.replace("\r\n", "\n").replace(",", "\n")
        return [item.strip() for item in normalized.split("\n") if item.strip()]
    return [str(value).strip()]


def parse_folder_list_value(value: Any) -> List[str]:
    return [item for item in to_list(value) if item]


def parse_rename_albums_value(raw_value: Any) -> Dict[str, str]:
    text = str(raw_value or "").replace("\r\n", "\n").strip()
    if not text:
        return {"pattern": "", "replacement": ""}
    comma_index = text.find(",")
    if comma_index >= 0:
        return {
            "pattern": text[:comma_index].strip(),
            "replacement": text[comma_index + 1 :].strip(),
        }
    lines = [item.strip() for item in text.split("\n") if item.strip()]
    return {"pattern": lines[0] if lines else "", "replacement": lines[1] if len(lines) > 1 else ""}


def compose_rename_albums_value(pattern: Any, replacement: Any) -> str:
    pattern_text = str(pattern or "").strip()
    replacement_text = str(replacement or "").strip()
    if not pattern_text and not replacement_text:
        return ""
    if not replacement_text:
        return pattern_text
    return f"{pattern_text}, {replacement_text}"


def parse_migration_endpoint(raw_value: Any, fallback_kind: str = "folder") -> Dict[str, str]:
    text = str(raw_value or "").strip()
    if not text:
        return {"kind": fallback_kind, "account": "1", "path": ""}

    synology_match = re.fullmatch(r"synology(?:-photos)?(?:-([123]))?", text, flags=re.IGNORECASE)
    if synology_match:
        return {"kind": "synology", "account": synology_match.group(1) or "1", "path": ""}

    immich_match = re.fullmatch(r"immich(?:-photos)?(?:-([123]))?", text, flags=re.IGNORECASE)
    if immich_match:
        return {"kind": "immich", "account": immich_match.group(1) or "1", "path": ""}

    nextcloud_match = re.fullmatch(r"nextcloud(?:-photos)?(?:-([123]))?", text, flags=re.IGNORECASE)
    if nextcloud_match:
        return {"kind": "nextcloud", "account": nextcloud_match.group(1) or "1", "path": ""}

    google_match = re.fullmatch(r"google(?:-?photos)?(?:-([123]))?", text, flags=re.IGNORECASE)
    if google_match:
        return {"kind": "google", "account": google_match.group(1) or "1", "path": ""}

    return {"kind": "folder", "account": "1", "path": text}


def compose_migration_endpoint(state: Dict[str, Any] | None) -> str:
    current = state or {}
    kind = str(current.get("kind") or "").strip().lower()
    account = str(current.get("account") or "1").strip() or "1"
    path = str(current.get("path") or "").strip()
    if kind == "folder":
        return path
    if kind == "synology":
        return f"synology-photos-{account}"
    if kind == "immich":
        return f"immich-photos-{account}"
    if kind == "nextcloud":
        return f"nextcloud-photos-{account}"
    if kind == "google":
        return f"google-photos-{account}"
    return path


def parse_find_duplicates_value(raw_value: Any) -> Dict[str, Any]:
    parts = parse_folder_list_value(raw_value)
    action = "list"
    folders: List[str] = []
    for part in parts:
        token = str(part or "").strip().lower()
        if token in {"list", "move", "remove", "delete"}:
            action = "delete" if token in {"remove", "delete"} else token
        else:
            folders.append(str(part))
    return {"action": action, "folders": folders}


def compose_find_duplicates_value(action_ui: Any, folders: List[str]) -> str:
    normalized_folders = [str(item or "").strip() for item in (folders or []) if str(item or "").strip()]
    if not normalized_folders:
        return ""
    action = str(action_ui or "list").strip().lower() or "list"
    action_cli = "remove" if action == "delete" else action
    return ", ".join([action_cli, *normalized_folders])


def ui_option_name(field_or_dest: Any) -> str:
    if isinstance(field_or_dest, dict):
        dest = str(field_or_dest.get("dest") or "")
    else:
        dest = str(field_or_dest or "")
    if dest in FEATURE_LABELS:
        return FEATURE_LABELS[dest]
    return dest.replace("-", " ").strip().title()


def build_parser_schema(
    default_google_takeout_path: str = "",
    default_icloud_takeout_path: str = "",
) -> Dict[str, Any]:
    old_argv = sys.argv[:]
    try:
        sys.argv = ["cli-tui"]
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
        if dest == "google-takeout" and default_google_takeout_path:
            field["default"] = default_google_takeout_path
        if dest == "icloud-takeout" and default_icloud_takeout_path:
            field["default"] = default_icloud_takeout_path
        fields.append(field)
        by_dest[dest] = field

    cloud_common = [field for field in fields if field["tab"] == "cloud_common"]
    merged_general = [field for field in fields if field["dest"] in (GENERAL_CORE_DESTS | GENERAL_OPTIONAL_DESTS)]
    schema = {
        "general_tabs": {"general": merged_general},
        "feature_scoped": [field for field in fields if field["dest"] in FEATURE_SCOPED_DESTS],
        "tabs": {
            "google_takeout": [field for field in fields if field["tab"] == "google_takeout"],
            "icloud_takeout": [field for field in fields if field["tab"] == "icloud_takeout"],
            "google_photos": cloud_common,
            "synology_photos": cloud_common,
            "immich_photos": cloud_common,
            "nextcloud_photos": cloud_common,
            "standalone_features": [field for field in fields if field["tab"] == "standalone_features"],
            "automatic_migration": [field for field in fields if field["tab"] == "automatic_migration"],
        },
        "fields_by_dest": by_dest,
    }
    return schema


def get_all_fields(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        *(schema.get("general_tabs", {}).get("general", []) or []),
        *(schema.get("feature_scoped", []) or []),
        *(schema.get("tabs", {}).get("google_takeout", []) or []),
        *(schema.get("tabs", {}).get("icloud_takeout", []) or []),
        *(schema.get("tabs", {}).get("google_photos", []) or []),
        *(schema.get("tabs", {}).get("synology_photos", []) or []),
        *(schema.get("tabs", {}).get("immich_photos", []) or []),
        *(schema.get("tabs", {}).get("nextcloud_photos", []) or []),
        *(schema.get("tabs", {}).get("standalone_features", []) or []),
        *(schema.get("tabs", {}).get("automatic_migration", []) or []),
    ]


def get_field_by_dest(schema: Dict[str, Any], dest: str) -> Dict[str, Any] | None:
    return (schema.get("fields_by_dest") or {}).get(dest)


def normalize_field_for_context(field: Dict[str, Any] | None, tab_key: str) -> Dict[str, Any] | None:
    if not field:
        return field
    if tab_key in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"} and field.get("dest") == "account-id":
        normalized = dict(field)
        normalized["kind"] = "select"
        normalized["choices"] = [1, 2, 3]
        normalized["help"] = "Select Account ID defined in Configuration file."
        return normalized
    return field


def parse_required_from_help(help_text: str, ignore_dests: set[str] | None = None) -> List[str]:
    ignored = {str(item or "").strip().lower() for item in (ignore_dests or set()) if str(item or "").strip()}
    found: List[str] = []
    seen = set()
    for line in str(help_text or "").replace("\r\n", "\n").split("\n"):
        text = str(line or "").strip()
        if not text:
            continue
        if re.match(r"^Example:", text, flags=re.IGNORECASE):
            continue
        if not re.search(r"\brequired?\b", text, flags=re.IGNORECASE) and not re.search(r"\brequires\b", text, flags=re.IGNORECASE):
            continue
        for match in re.findall(r"--([a-z0-9-]+)", text, flags=re.IGNORECASE):
            dest = str(match or "").strip().lower()
            if not dest or dest == "client" or dest in ignored or dest in seen:
                continue
            seen.add(dest)
            found.append(dest)
    return found


def build_argument_specs(schema: Dict[str, Any], tab_key: str, selected_field: Dict[str, Any] | None, include_selected_value: bool = True) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    seen = set()

    def push_spec(dest: str, required: bool = False, force_include_flag: bool = False) -> None:
        if dest in seen:
            return
        field = get_field_by_dest(schema, dest)
        if not field:
            return
        if field.get("kind") == "flag" and not force_include_flag and not required:
            return
        seen.add(dest)
        specs.append({"field": normalize_field_for_context(field, tab_key), "required": required})

    if include_selected_value and selected_field and selected_field.get("kind") != "flag":
        push_spec(str(selected_field.get("dest") or ""), True)

    for dep in (MODULE_DEPENDENCIES_REQUIRED.get(tab_key, {}) or {}).get(str((selected_field or {}).get("dest") or ""), set()):
        push_spec(dep, True, True)

    for dest in parse_required_from_help(str((selected_field or {}).get("help") or ""), {str((selected_field or {}).get("dest") or "")}):
        push_spec(dest, True, True)
    return specs


def _load_default_config_template(project_root: Path) -> str:
    candidates = [project_root / "Config.ini"]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return ""


def _is_sensitive_config_key(key: str) -> bool:
    return bool(re.search(r"(PASSWORD|SECRET|TOKEN|API_KEY|APIKEY|PASSWD)", str(key or "").upper()))


def _immich_field_sort_key(field: Dict[str, Any], index: int) -> tuple[int, int, int]:
    key = str(field.get("key") or "").strip().upper()
    if key == "IMMICH_URL":
        return 0, 0, index
    if key == "IMMICH_API_KEY_ADMIN":
        return 1, 0, index
    match = re.fullmatch(r"IMMICH_(USERNAME|PASSWORD|API_KEY_USER)_(\d+)", key)
    if not match:
        return 9, 0, index
    field_kind = str(match.group(1))
    account_id = int(match.group(2))
    kind_order = {"USERNAME": 0, "PASSWORD": 1, "API_KEY_USER": 2}
    return 2, account_id * 10 + kind_order.get(field_kind, 9), index


def _sort_section_fields(section_name: str, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ordered = list(fields or [])
    if section_name == "Immich Photos":
        indexed = list(enumerate(ordered))
        indexed.sort(key=lambda item: _immich_field_sort_key(item[1], item[0]))
        return [field for _, field in indexed]
    return ordered


def config_field_account_id(key: str) -> str:
    match = re.search(r"_(\d+)$", str(key or "").strip().upper())
    return str(match.group(1)) if match else ""


def config_section_account_selector(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    account_ids = sorted({str(field.get("account_id") or "") for field in fields if str(field.get("account_id") or "")}, key=lambda value: int(value))
    return {"enabled": len(account_ids) > 1, "accounts": account_ids, "default_account": account_ids[0] if account_ids else ""}


def parse_template_to_form_schema(template_content: str) -> List[Dict[str, Any]]:
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
                    "account_id": config_field_account_id(key),
                }
            )
            pending_comments = []

    order_index = {name: idx for idx, name in enumerate(CONFIG_SECTIONS_ORDER)}
    for section in sections:
        section_name = str(section.get("name") or "")
        section["fields"] = _sort_section_fields(section_name, section.get("fields", []))
    sections.sort(key=lambda item: order_index.get(str(item.get("name") or ""), len(order_index) + 1000))
    return sections


def parse_ini_text_to_values(config_text: str) -> Dict[str, Dict[str, str]]:
    text = str(config_text or "").lstrip("\ufeff")
    values: Dict[str, Dict[str, str]] = {}
    current_section = ""

    def strip_inline_comment(raw: str) -> str:
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

    for raw_line in text.splitlines():
        line = str(raw_line or "").strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            values.setdefault(current_section, {})
            continue
        if not current_section:
            continue
        if "=" in line:
            key_raw, value_raw = line.split("=", 1)
        elif ":" in line:
            key_raw, value_raw = line.split(":", 1)
        else:
            continue
        key = key_raw.strip()
        if not key:
            continue
        values.setdefault(current_section, {})[key] = strip_inline_comment(value_raw.strip())
    return values


def merge_values_with_schema(values: Dict[str, Dict[str, str]], form_schema: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    def norm_token(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").strip().lower())

    input_values = values or {}
    section_lookup = {str(name).strip().lower(): (section_values or {}) for name, section_values in input_values.items() if str(name or "").strip()}
    section_lookup_norm = {norm_token(str(name)): (section_values or {}) for name, section_values in input_values.items() if str(name or "").strip()}
    merged: Dict[str, Dict[str, str]] = {}
    for section in form_schema:
        section_name = str(section.get("name") or "")
        merged[section_name] = {}
        source_values = input_values.get(section_name)
        if source_values is None:
            source_values = section_lookup.get(section_name.strip().lower(), {})
        if not source_values:
            source_values = section_lookup_norm.get(norm_token(section_name), {})
        normalized_source = {str(k): str(v or "") for k, v in (source_values or {}).items()}
        normalized_source_lc = {str(k).strip().lower(): str(v or "") for k, v in (source_values or {}).items()}
        normalized_source_norm = {norm_token(str(k)): str(v or "") for k, v in (source_values or {}).items()}
        for field in section.get("fields", []):
            key = str(field.get("key") or "")
            base_value = normalized_source.get(key)
            if base_value is None:
                base_value = normalized_source_lc.get(key.strip().lower(), str(field.get("default", "")) or "")
            if base_value == str(field.get("default", "")) or base_value is None:
                base_value = normalized_source_norm.get(norm_token(key), base_value)
            if section_name == "TimeZone" and key == "timezone" and not str(base_value).strip():
                base_value = TIMEZONE_DEFAULT
            merged[section_name][key] = str(base_value or "")

    nextcloud_section = merged.get("NextCloud Photos", {})
    if isinstance(nextcloud_section, dict):
        for account_id in ("1", "2", "3"):
            username_key = f"NEXTCLOUD_USERNAME_{account_id}"
            password_key = f"NEXTCLOUD_PASSWORD_{account_id}"
            photos_key = f"NEXTCLOUD_PHOTOS_FOLDER_{account_id}"
            albums_key = f"NEXTCLOUD_ALBUMS_FOLDER_{account_id}"
            if not str(nextcloud_section.get(username_key, "") or "").strip():
                nextcloud_section[password_key] = ""
                nextcloud_section[photos_key] = ""
                nextcloud_section[albums_key] = ""
    return merged


def serialize_values_to_ini_with_comments(values: Dict[str, Dict[str, str]], template_content: str) -> str:
    comment_column = 72

    def aligned_line(left: str, comment_text: str) -> str:
        base = left.rstrip()
        comment = str(comment_text or "").strip()
        if not comment:
            return base
        if not comment.startswith("#"):
            comment = f"# {comment}"
        pad = max(1, comment_column - len(base))
        return f"{base}{' ' * pad}{comment}"

    output_lines: List[str] = []
    current_section = ""
    written = set()
    merged_values = values or {}

    for original_line in str(template_content or "").splitlines():
        line = str(original_line or "")
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            output_lines.append(line)
            continue
        if "=" in line and current_section:
            key_part, rhs = line.split("=", 1)
            key = key_part.strip()
            if key and current_section in merged_values and key in merged_values[current_section]:
                value = str(merged_values[current_section][key] or "")
                comment = ""
                if "#" in rhs:
                    comment = "#" + rhs.split("#", 1)[1]
                output_lines.append(aligned_line(f"{key_part.rstrip()} = {value}", comment))
                written.add((current_section, key))
                continue
        output_lines.append(line)

    if output_lines and output_lines[-1].strip():
        output_lines.append("")

    for section in CONFIG_SECTIONS_ORDER:
        section_values = merged_values.get(section)
        if not section_values:
            continue
        missing_keys = [key for key in section_values if (section, key) not in written]
        if not missing_keys:
            continue
        if f"[{section}]" not in output_lines:
            output_lines.append(f"[{section}]")
        for key in missing_keys:
            output_lines.append(f"{key} = {section_values[key]}")
        output_lines.append("")
    return "\n".join(output_lines).rstrip() + "\n"


def load_config_editor_model(project_root: Path, config_path: Path) -> Dict[str, Any]:
    template_text = _load_default_config_template(project_root)
    schema = parse_template_to_form_schema(template_text)
    current_values: Dict[str, Dict[str, str]] = {}
    if config_path.exists() and config_path.is_file():
        try:
            current_values = parse_ini_text_to_values(config_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            current_values = {}
    merged = merge_values_with_schema(current_values, schema)
    sections = []
    section_order = {name: idx for idx, name in enumerate(CONFIG_EDITOR_SECTIONS_ORDER)}
    for section in schema:
        section_name = str(section.get("name") or "")
        if section_name in CONFIG_FEATURES_EXCLUDED_SECTIONS:
            continue
        if section_name not in CONFIG_EDITOR_SECTIONS_ORDER:
            continue
        fields = []
        for field in section.get("fields", []):
            key = str(field.get("key") or "")
            if not key:
                continue
            choices = TIMEZONE_CHOICES if section_name == "TimeZone" and key == "timezone" else []
            fields.append(
                {
                    "key": key,
                    "value": str(merged.get(section_name, {}).get(key, "")),
                    "default": str(field.get("default") or ""),
                    "help": str(field.get("help") or ""),
                    "sensitive": bool(field.get("sensitive")),
                    "account_id": config_field_account_id(key),
                    "choices": choices,
                }
            )
        sections.append(
            {
                "name": section_name,
                "description": str(section.get("description") or ""),
                "account_selector": config_section_account_selector(fields),
                "fields": fields,
            }
        )
    sections.sort(key=lambda item: section_order.get(str(item.get("name") or ""), 9999))
    return {"template_text": template_text, "schema": schema, "values": merged, "sections": sections}


def save_config_editor_values(config_path: Path, values: Dict[str, Dict[str, str]], template_text: str, schema: List[Dict[str, Any]]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_values_with_schema(values, schema)
    content = serialize_values_to_ini_with_comments(merged, template_text)
    config_path.write_text(content, encoding="utf-8")


def default_state_values(schema: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for field in get_all_fields(schema):
        dest = str(field.get("dest") or "")
        if not dest or dest in values:
            continue
        default = field.get("default")
        kind = field.get("kind")
        if kind == "flag":
            values[dest] = bool_from_value(default)
        elif kind == "bool":
            values[dest] = bool_from_value(default)
        elif kind == "list":
            values[dest] = to_list(default)
        else:
            values[dest] = "" if default is None else str(default)
    values.setdefault("replacement-pattern", "")
    return values


def prepare_values_for_command(values: Dict[str, Any], tab: str, selected_action_dest: str | None) -> Dict[str, Any]:
    prepared = dict(values or {})
    if tab in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"} and selected_action_dest == "rename-albums":
        prepared["rename-albums"] = compose_rename_albums_value(prepared.get("rename-pattern", ""), prepared.get("replacement-pattern", ""))
    if tab == "standalone_features" and selected_action_dest == "find-duplicates":
        folders = parse_folder_list_value(prepared.get("find-duplicates-folders", []))
        prepared["find-duplicates"] = compose_find_duplicates_value(prepared.get("find-duplicates-action", "list"), folders)
    return prepared


def _allowed_dests_for_tab(schema: Dict[str, Any], tab: str, selected_action_dest: str | None = None) -> set[str]:
    if tab not in TAB_TO_CATEGORY:
        raise ValueError(f"Unsupported tab: {tab}")
    allowed_dests = {field["dest"] for field in schema["general_tabs"]["general"]}
    allowed_dests.update(FEATURE_SCOPED_DESTS)
    tab_dests = {field["dest"] for field in schema["tabs"][tab]}
    if tab in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
        cloud_action_dests = {dest for dest in tab_dests if dest != "one-time-password"}
        available_actions = cloud_action_dests.intersection(CLOUD_ACTIONS_AVAILABLE_BY_TAB.get(tab, cloud_action_dests))
        if not available_actions:
            available_actions = cloud_action_dests
        if selected_action_dest:
            if selected_action_dest not in available_actions:
                raise ValueError(f"Invalid selected action for tab {tab}: {selected_action_dest}")
            allowed_dests.add(selected_action_dest)
        else:
            allowed_dests.update(available_actions)
        if "one-time-password" in tab_dests:
            allowed_dests.add("one-time-password")
    elif tab == "standalone_features":
        if selected_action_dest:
            if selected_action_dest not in tab_dests:
                raise ValueError(f"Invalid selected action for tab {tab}: {selected_action_dest}")
            allowed_dests.add(selected_action_dest)
        else:
            allowed_dests.update(tab_dests)
    else:
        allowed_dests.update(tab_dests)
    return allowed_dests


def build_cli_args(schema: Dict[str, Any], tab: str, values: Dict[str, Any], selected_action_dest: str | None = None) -> List[str]:
    prepared = prepare_values_for_command(values, tab, selected_action_dest)
    allowed_dests = _allowed_dests_for_tab(schema, tab, selected_action_dest)
    args: List[str] = []
    for dest in sorted(allowed_dests):
        field = schema["fields_by_dest"][dest]
        raw_value = prepared.get(dest)
        kind = field["kind"]
        long_option = field["long_option"]
        default = field["default"]
        if kind == "flag":
            if bool_from_value(raw_value):
                args.append(long_option)
            continue
        if kind == "bool":
            current = bool_from_value(raw_value)
            default_bool = bool_from_value(default)
            if current != default_bool:
                args.extend([long_option, "true" if current else "false"])
            continue
        if kind == "list":
            if dest == "rename-albums":
                text = str(raw_value or "").strip()
                if text:
                    args.extend([long_option, text])
                continue
            values_list = to_list(raw_value)
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


def build_full_command(cli_entrypoint: Path, schema: Dict[str, Any], tab: str, values: Dict[str, Any], selected_action_dest: str | None = None) -> List[str]:
    return [sys.executable, str(cli_entrypoint), *build_cli_args(schema, tab, values, selected_action_dest)]


def load_json_file(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def command_to_string(command: List[str]) -> str:
    return subprocess.list2cmdline(command)
