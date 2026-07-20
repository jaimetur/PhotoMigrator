"""Google Takeout person-label metadata preserved across GPTH processing."""

import json
from datetime import datetime, timezone
from pathlib import Path


PEOPLE_MAP_FILENAME = "takeout_people_metadata.json"


def _people_from_sidecar(payload):
    people = payload.get("people") or payload.get("peopleInPhoto") or []
    names = []
    for person in people:
        name = person.get("name") if isinstance(person, dict) else person
        name = str(name or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _timestamp_from_sidecar(payload, field_name):
    value = payload.get(field_name) or {}
    if isinstance(value, dict):
        value = value.get("timestamp") or value.get("formatted")
    text = str(value or "").strip()
    if text.isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return text


def _asset_name_from_sidecar(payload, json_path):
    asset_name = str(payload.get("title") or json_path.stem).strip()
    # Google commonly emits IMG.jpg.json; the title is authoritative when present.
    if asset_name.lower().endswith(".json"):
        asset_name = asset_name[:-5]
    return asset_name.casefold()


def build_people_map(takeout_root):
    """Collect Google sidecars by filename, retaining distinct capture-date entries.

    Google Takeout can contain different assets with the same filename.  Their
    labels must not be merged: consumers use ``taken_at`` to select the one
    belonging to the physical file being uploaded.
    """
    entries = {}
    for json_path in sorted(Path(takeout_root).rglob("*.json"), key=lambda path: str(path).casefold()):
        if json_path.name == PEOPLE_MAP_FILENAME:
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        names = _people_from_sidecar(payload) if isinstance(payload, dict) else []
        if not names:
            continue
        asset_name = _asset_name_from_sidecar(payload, json_path)
        if not asset_name:
            continue
        entry = {
            "people": names,
            "taken_at": _timestamp_from_sidecar(payload, "photoTakenTime"),
            "created_at": _timestamp_from_sidecar(payload, "creationTime"),
            "modified_at": _timestamp_from_sidecar(payload, "modificationTime"),
        }
        candidates = entries.setdefault(asset_name, [])
        # The same asset may have one sidecar in an album and another in a
        # year folder. Merge only entries that identify that exact capture.
        existing = next(
            (
                item for item in candidates
                if all(item.get(key, "") == entry[key] for key in ("taken_at", "created_at", "modified_at"))
            ),
            None,
        )
        if existing:
            existing["people"] = list(dict.fromkeys(existing.get("people", []) + names))
        else:
            candidates.append(entry)
    return entries


def save_people_map(takeout_root, output_folder):
    entries = build_people_map(takeout_root)
    output_path = Path(output_folder) / PEOPLE_MAP_FILENAME
    payload = {"version": 2, "assets": entries}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return output_path, len(entries)


def load_people_map(input_folder):
    """Find the map in the input folder or one of its parents."""
    current = Path(input_folder).expanduser().resolve()
    for folder in (current, *current.parents):
        candidate = folder / PEOPLE_MAP_FILENAME
        if candidate.is_file():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                return payload.get("assets", {}) if isinstance(payload, dict) else {}
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return {}
    return {}
