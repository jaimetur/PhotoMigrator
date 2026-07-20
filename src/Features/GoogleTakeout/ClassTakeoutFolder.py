# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-
import fnmatch
import json
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import zipfile
import unicodedata
from collections import deque
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from os.path import dirname, basename
from pathlib import Path

import piexif
from colorama import init
from dateutil import parser
from packaging.version import Version

from Core.CustomLogger import set_log_level
from Core.CustomLogger import suppress_console_output_temporarily
from Core.FolderAnalyzer import FolderAnalyzer
from Core.GlobalVariables import ARGS, LOG_LEVEL, LOGGER, START_TIME, FOLDERNAME_ALBUMS, FOLDERNAME_NO_ALBUMS, TIMESTAMP, SUPPLEMENTAL_METADATA, MSG_TAGS, SPECIAL_SUFFIXES, EDITTED_SUFFIXES, PHOTO_EXT, VIDEO_EXT, GPTH_VERSION, FOLDERNAME_GPTH, TAKEOUT_SPECIAL_FOLDER_NAMES, \
    PIL_SUPPORTED_EXTENSIONS, FOLDERNAME_EXIFTOOL, GOOGLE_PHOTOS_CONTAINER_NAMES, TAKEOUT_YEAR_FOLDER_PATTERNS
from Features.LocalFolder.ClassLocalFolder import ClassLocalFolder  # Import ClassLocalFolder (Parent Class of this)
from Features.GoogleTakeout.PeopleMetadata import build_people_map, PEOPLE_MAP_FILENAME
from Features.StandAloneFeatures.AutoRenameAlbumsFolders import rename_album_folders
from Features.StandAloneFeatures.Duplicates import find_duplicates
from Features.StandAloneFeatures.FixSymLinks import fix_symlinks_broken
from Utils.DateUtils import normalize_datetime_utc
from Utils.FileUtils import build_generated_output_folder, delete_subfolders, remove_empty_dirs, is_valid_path, sanitize_and_unpack_zips
from Utils.GeneralUtils import print_dict_pretty, tqdm, get_os, get_arch, ensure_executable, print_arguments_pretty, profile_and_print, TQDM_DASHBOARD_PREFIX
from Utils.StandaloneUtils import change_working_dir, get_gpth_tool_path, custom_print, get_exif_tool_path

CREATEFILE_FAILED_RE = re.compile(r'CreateFile failed for "(?P<path>.+?)" \(error=(?P<error>\d+)\)')
VIDEO_XMP_DATE_TAGS = (
    "XMP:DateTimeOriginal",
    "XMP:DateTime",
    "XMP:CreateDate",
    "XMP:ModifyDate",
)
VIDEO_NATIVE_DATE_TAGS = (
    "QuickTime:CreateDate",
    "QuickTime:TrackCreateDate",
    "QuickTime:MediaCreateDate",
    "Track:CreateDate",
    "Media:CreateDate",
    "QuickTime:ModifyDate",
    "QuickTime:TrackModifyDate",
    "QuickTime:MediaModifyDate",
    "Track:ModifyDate",
    "Media:ModifyDate",
)
VIDEO_METADATA_REPAIR_SOURCE_PREFIXES = ("QuickTime:", "Track:", "Media:")
VIDEO_METADATA_REPAIR_EXTENSIONS = {".mp4", ".mov", ".m4v", ".3gp", ".3g2"}

def _normalize_special_folder_token(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    return re.sub(r"[\s_-]+", "", text)


TAKEOUT_SPECIAL_FOLDER_ALIASES = {
    "archive": {
        "archive",
        "archivo",
        "arquivo",
        "archives",
        "archiv",
        "archivio",
        "archief",
        "archiwum",
        "архив",
        "归档",
        "已归档",
        "アーカイブ",
        "보관처리됨",
    },
    "trash": {
        "trash",
        "bin",
        "recycle bin",
        "papelera",
        "papelera de reciclaje",
        "lixeira",
        "lixo",
        "corbeille",
        "papierkorb",
        "cestino",
        "cestino eliminati",
        "prullenbak",
        "kosz",
        "kosz na smieci",
        "korzina",
        "корзина",
        "垃圾桶",
        "回收站",
        "ゴミ箱",
        "휴지통",
    },
    "locked": {
        "locked folder",
        "carpeta privada",
        "carpeta bloqueada",
        "pasta trancada",
        "dossier verrouille",
        "dossier verrouillé",
        "gesperrter ordner",
        "cartella bloccata",
        "vergrendelde map",
        "folder zablokowany",
        "заблокированная папка",
        "锁定文件夹",
        "私密文件夹",
        "已上锁的文件夹",
        "ロックされたフォルダ",
        "잠긴 폴더",
    },
}
TAKEOUT_SPECIAL_FOLDER_ALIAS_LOOKUP = {
    _normalize_special_folder_token(alias): category
    for category, aliases in TAKEOUT_SPECIAL_FOLDER_ALIASES.items()
    for alias in aliases
}


def _classify_takeout_special_folder(folder_name):
    return TAKEOUT_SPECIAL_FOLDER_ALIAS_LOOKUP.get(_normalize_special_folder_token(folder_name))


def _find_forbidden_special_folder_in_path(path_value):
    """
    Returns the offending path component if any folder in path_value matches one
    of the special Google folders (Archive/Trash/Locked folder), else None.
    """
    parts = [part for part in re.split(r"[\\/]+", str(path_value or "")) if part and part not in (".", "..")]
    for part in parts:
        if _classify_takeout_special_folder(part):
            return part
    return None


def _get_takeout_special_folders_root(base_root):
    base_root = Path(base_root)
    special_root = base_root / "Special Folders"
    if special_root.exists() or not (base_root / "Special_Folders").exists():
        return special_root
    return base_root / "Special_Folders"


def _relocate_misclassified_special_folders(base_root, step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):
        base_root = Path(base_root).resolve()
        candidate_roots = [
            base_root / FOLDERNAME_ALBUMS,
            base_root / f"{FOLDERNAME_ALBUMS}-shared",
            base_root,
        ]
        special_root = _get_takeout_special_folders_root(base_root)
        moved_any = False

        for candidate_root in candidate_roots:
            if not candidate_root.exists() or not candidate_root.is_dir():
                continue
            if candidate_root.resolve() == special_root.resolve():
                continue

            for child in sorted(candidate_root.iterdir(), key=lambda p: p.name.casefold()):
                if not child.is_dir():
                    continue
                if child.name in {
                    FOLDERNAME_NO_ALBUMS,
                    FOLDERNAME_ALBUMS,
                    f"{FOLDERNAME_ALBUMS}-shared",
                    "Special Folders",
                    "Special_Folders",
                    "PARTNER_SHARED",
                }:
                    continue
                if candidate_root == base_root and child.name.casefold() in {
                    "albums",
                    "albums-shared",
                    "all_photos",
                    "partner_shared",
                    "memories",
                }:
                    continue

                category = _classify_takeout_special_folder(child.name)
                if not category:
                    continue

                destination_path = special_root / child.name
                special_root.mkdir(parents=True, exist_ok=True)
                LOGGER.info(
                    f"{step_name}Relocating misclassified special folder '{child}' -> '{destination_path}' "
                    f"(detected as {category})."
                )
                if destination_path.exists():
                    ok = copy_move_folder(
                        str(child),
                        str(destination_path),
                        move=True,
                        step_name=step_name,
                        log_level=log_level,
                    )
                    if not ok:
                        LOGGER.error(f"{step_name}Failed to merge special folder '{child}' into '{destination_path}'")
                        return False
                    remove_empty_dirs(input_folder=str(child), log_level=log_level)
                    with suppress(Exception):
                        child.rmdir()
                else:
                    shutil.move(str(child), str(destination_path))
                moved_any = True

        return True

def _normalize_folder_name(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _normalize_recoverable_asset_name(filename):
    name = unicodedata.normalize("NFC", os.path.basename(str(filename or "")))
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"\(\d+\)$", "", stem)
    return f"{stem.casefold()}{ext.casefold()}"


def _extract_orphan_album_json_descriptor(json_path):
    try:
        payload = json.loads(Path(json_path).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    title = str(payload.get("title") or "").strip()
    if not title:
        return None

    photo_taken = payload.get("photoTakenTime") or {}
    creation_time = payload.get("creationTime") or {}
    if not isinstance(photo_taken, dict):
        photo_taken = {}
    if not isinstance(creation_time, dict):
        creation_time = {}

    timestamp_raw = photo_taken.get("timestamp") or creation_time.get("timestamp")
    # Album-level metadata JSONs contain "title" but describe the album itself
    # (usually via a "date" field) instead of an individual asset sidecar.
    if timestamp_raw in (None, ""):
        return None

    asset_dt = None
    year = None
    try:
        asset_dt = datetime.fromtimestamp(int(str(timestamp_raw)), timezone.utc)
        year = asset_dt.year
    except Exception:
        asset_dt = None
        year = None

    return {
        "title": title,
        "year": year,
        "datetime": asset_dt,
    }


def _iter_google_takeout_album_dirs(input_folder):
    root = Path(input_folder)
    container_dirs = []
    if _looks_like_google_photos_container(root.name):
        container_dirs.append(root)
    elif root.name.casefold() == "takeout":
        container_dirs.extend(
            child for child in sorted(root.iterdir(), key=lambda p: p.name.casefold())
            if child.is_dir() and _looks_like_google_photos_container(child.name)
        )
    else:
        seen = set()
        for candidate in sorted(root.rglob("*"), key=lambda p: p.as_posix().casefold()):
            if not candidate.is_dir() or not _looks_like_google_photos_container(candidate.name):
                continue
            candidate_key = candidate.resolve().as_posix()
            if candidate_key in seen:
                continue
            seen.add(candidate_key)
            container_dirs.append(candidate)

    album_occurrences = {}
    for container_dir in container_dirs:
        for album_dir in sorted(container_dir.iterdir(), key=lambda p: p.name.casefold()):
            if not album_dir.is_dir():
                continue
            if album_dir.name in {"@eaDir", FOLDERNAME_NO_ALBUMS, FOLDERNAME_ALBUMS, "Takeout"}:
                continue
            if _is_takeout_year_folder(album_dir.name):
                continue
            if _find_forbidden_special_folder_in_path(album_dir.name):
                continue
            occurrence_index = album_occurrences.get(album_dir.name, 0)
            album_occurrences[album_dir.name] = occurrence_index + 1
            yield album_dir, ClassLocalFolder._manifest_album_key(album_dir.name, occurrence_index)


def _build_non_album_candidate_index(no_albums_root):
    exact = {}
    normalized = {}
    if not no_albums_root.exists() or not no_albums_root.is_dir():
        return {"exact": exact, "normalized": normalized}

    for path_obj in sorted(no_albums_root.rglob("*"), key=lambda p: p.as_posix().casefold()):
        if not (path_obj.is_file() or path_obj.is_symlink()):
            continue
        if path_obj.suffix.lower() == ".json":
            continue
        exact.setdefault(path_obj.name.casefold(), []).append(path_obj)
        normalized.setdefault(_normalize_recoverable_asset_name(path_obj.name), []).append(path_obj)
    return {"exact": exact, "normalized": normalized}


def _extract_year_from_candidate_path(path_obj):
    for part in reversed(path_obj.parts):
        part = str(part)
        if re.fullmatch(r"(19|20)\d{2}", part):
            try:
                return int(part)
            except ValueError:
                return None
        match = re.match(r"^((19|20)\d{2})[-_]", part)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None


def _select_recoverable_asset_path(candidate_index, expected_filename, expected_year=None):
    casefold_name = str(expected_filename or "").casefold()
    normalized_name = _normalize_recoverable_asset_name(expected_filename)
    candidates = list(candidate_index["exact"].get(casefold_name, []))
    if not candidates:
        candidates = list(candidate_index["normalized"].get(normalized_name, []))
    if not candidates:
        return None

    def score(path_obj):
        exact_penalty = 0 if path_obj.name.casefold() == casefold_name else 1
        candidate_year = _extract_year_from_candidate_path(path_obj)
        year_penalty = 10_000
        if expected_year:
            if candidate_year is not None:
                year_penalty = abs(int(candidate_year) - int(expected_year))
        elif candidate_year is not None:
            year_penalty = 0
        depth_penalty = len(path_obj.parts)
        return (exact_penalty, year_penalty, depth_penalty, path_obj.as_posix().casefold())

    return sorted(candidates, key=score)[0]


def _build_album_asset_presence_index(album_root):
    exact = set()
    normalized = set()
    album_root = Path(album_root)
    if not album_root.exists() or not album_root.is_dir():
        return {"exact": exact, "normalized": normalized}

    for path_obj in album_root.rglob("*"):
        if not (path_obj.is_file() or path_obj.is_symlink()):
            continue
        if path_obj.suffix.lower() == ".json":
            continue
        exact.add(path_obj.name.casefold())
        normalized.add(_normalize_recoverable_asset_name(path_obj.name))
    return {"exact": exact, "normalized": normalized}


def _album_contains_expected_asset(album_root, expected_filename, album_presence_index=None):
    if not album_root.exists() or not album_root.is_dir():
        return False

    expected_casefold = str(expected_filename or "").casefold()
    expected_normalized = _normalize_recoverable_asset_name(expected_filename)
    if album_presence_index is None:
        album_presence_index = _build_album_asset_presence_index(album_root)
    return (
        expected_casefold in album_presence_index["exact"]
        or expected_normalized in album_presence_index["normalized"]
    )


def _build_album_output_target_path(album_root, filename, asset_dt=None, albums_structure="flatten"):
    target_dir = Path(album_root)
    normalized_structure = str(albums_structure or "flatten").strip().lower()
    if normalized_structure == "year" and asset_dt:
        target_dir = target_dir / asset_dt.strftime("%Y")
    elif normalized_structure == "year/month" and asset_dt:
        target_dir = target_dir / asset_dt.strftime("%Y") / asset_dt.strftime("%m")
    elif normalized_structure == "year-month" and asset_dt:
        target_dir = target_dir / asset_dt.strftime("%Y-%m")
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / str(filename)


def _create_symbolic_or_copied_album_entry(source_path, target_path, no_symbolic_albums, step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):
        target_path = Path(target_path)
        source_path = Path(source_path)
        if target_path.exists() or target_path.is_symlink():
            return False
        try:
            if no_symbolic_albums:
                shutil.copy2(source_path, target_path)
            elif os.name == "nt":
                os.link(source_path, target_path)
            else:
                relative_path = os.path.relpath(source_path, start=target_path.parent)
                target_path.symlink_to(relative_path)
            return True
        except Exception as error:
            LOGGER.warning(f"{step_name}Failed to create recovered album entry '{target_path.name}' from '{source_path}': {error}. Copying instead.")
            try:
                shutil.copy2(source_path, target_path)
                return True
            except Exception as copy_error:
                LOGGER.warning(f"{step_name}Failed to copy recovered album entry '{target_path.name}': {copy_error}")
                return False


def recover_orphan_album_assets_from_json_sidecars(input_folder, output_folder, albums_folder, no_symbolic_albums=False, albums_structure="flatten", step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):
        input_root = Path(input_folder)
        albums_root = Path(albums_folder)
        no_albums_root = Path(output_folder) / FOLDERNAME_NO_ALBUMS

        summary = {
            "orphan_json_detected": 0,
            "recovered_assets": 0,
            "unresolved_assets": 0,
            "albums_touched": 0,
            "already_present_assets": 0,
        }

        if not input_root.exists() or not input_root.is_dir():
            LOGGER.warning(f"{step_name}Skipping orphan album JSON recovery because input folder does not exist: '{input_root}'")
            return summary
        if not no_albums_root.exists() or not no_albums_root.is_dir():
            LOGGER.warning(f"{step_name}Skipping orphan album JSON recovery because '{FOLDERNAME_NO_ALBUMS}' folder does not exist in output: '{no_albums_root}'")
            return summary

        candidate_index = _build_non_album_candidate_index(no_albums_root)
        per_album_stats = {}

        for source_album_dir, output_album_name in _iter_google_takeout_album_dirs(input_root):
            json_candidates = sorted(source_album_dir.rglob("*.json"), key=lambda p: p.as_posix().casefold())
            if not json_candidates:
                continue

            output_album_dir = albums_root / output_album_name
            album_presence_index = _build_album_asset_presence_index(output_album_dir)
            album_stat = per_album_stats.setdefault(output_album_name, {"recovered": 0, "unresolved": 0, "already_present": 0})

            for json_path in json_candidates:
                descriptor = _extract_orphan_album_json_descriptor(json_path)
                if not descriptor:
                    continue

                expected_title = descriptor["title"]
                expected_year = descriptor["year"]
                summary["orphan_json_detected"] += 1

                if _album_contains_expected_asset(output_album_dir, expected_title, album_presence_index):
                    summary["already_present_assets"] += 1
                    album_stat["already_present"] += 1
                    continue

                source_candidate = _select_recoverable_asset_path(candidate_index, expected_title, expected_year)
                if source_candidate is None:
                    summary["unresolved_assets"] += 1
                    album_stat["unresolved"] += 1
                    continue

                target_path = _build_album_output_target_path(
                    output_album_dir,
                    source_candidate.name,
                    asset_dt=descriptor.get("datetime"),
                    albums_structure=albums_structure,
                )

                if _album_contains_expected_asset(output_album_dir, expected_title, album_presence_index):
                    summary["already_present_assets"] += 1
                    album_stat["already_present"] += 1
                    continue

                if _create_symbolic_or_copied_album_entry(
                    source_candidate,
                    target_path,
                    no_symbolic_albums=no_symbolic_albums,
                    step_name=step_name,
                    log_level=log_level,
                ):
                    summary["recovered_assets"] += 1
                    album_stat["recovered"] += 1
                    album_presence_index["exact"].add(source_candidate.name.casefold())
                    album_presence_index["normalized"].add(_normalize_recoverable_asset_name(source_candidate.name))
                else:
                    summary["unresolved_assets"] += 1
                    album_stat["unresolved"] += 1

        for album_name, album_stat in per_album_stats.items():
            if album_stat["recovered"] or album_stat["unresolved"]:
                summary["albums_touched"] += 1
                total_assets = album_stat["already_present"] + album_stat["recovered"]
                LOGGER.info(
                    f"{step_name}Album JSON Recovery: '{album_name}' already had {album_stat['already_present']} assets, "
                    f"recovered {album_stat['recovered']} assets, and left {album_stat['unresolved']} unresolved. "
                    f"Total assets: {total_assets}"
                )

        LOGGER.info(
            f"{step_name}Orphan album JSON sidecars detected: {summary['orphan_json_detected']}. "
            f"Already present: {summary['already_present_assets']}. "
            f"Recovered: {summary['recovered_assets']}. Unresolved: {summary['unresolved_assets']}."
        )
        return summary


def preserve_archive_browser_artifacts(output_folder, step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):
        try:
            output_root = Path(output_folder).resolve()
        except Exception:
            return False

        if not output_root.exists() or not output_root.is_dir():
            return False

        try:
            archive_candidates = list(output_root.rglob("archive_browser.html"))
        except Exception as error:
            LOGGER.warning(f"{step_name}Unable to search archive_browser.html inside '{output_root}': {error}")
            return False

        if not archive_candidates:
            return False

        source_path = None
        for candidate in archive_candidates:
            if candidate.resolve() == (output_root / "archive_browser.html").resolve():
                source_path = candidate
                break
        if source_path is None:
            source_path = archive_candidates[0]

        destination_html = output_root / "archive_browser.html"
        destination_manifest = output_root / "automatic_migration_album_manifest.json"

        try:
            if source_path.resolve() != destination_html.resolve():
                shutil.copy2(source_path, destination_html)
                LOGGER.info(f"{step_name}Copied archive_browser.html to processed output root.")
        except Exception as error:
            LOGGER.warning(f"{step_name}Unable to copy archive_browser.html into '{output_root}': {error}")
            return False

        try:
            html_text = destination_html.read_text(encoding="utf-8", errors="replace")
            albums_manifest = ClassLocalFolder._parse_archive_browser_manifest(html_text)
            payload = {
                "source_file": destination_html.name,
                "generated_at": datetime.now().isoformat(),
                "albums": albums_manifest,
            }
            destination_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            LOGGER.info(f"{step_name}Generated compact album manifest for Automatic Migration from archive_browser.html.")
            return True
        except Exception as error:
            LOGGER.warning(f"{step_name}Unable to generate album manifest from archive_browser.html: {error}")
            return False


def _looks_like_google_photos_container(folder_name):
    return _normalize_folder_name(folder_name) in GOOGLE_PHOTOS_CONTAINER_NAMES


def _is_takeout_year_folder(folder_name):
    normalized = _normalize_folder_name(folder_name)
    return any(pattern.match(normalized) for pattern in TAKEOUT_YEAR_FOLDER_PATTERNS)


def inspect_takeout_structure(input_folder, step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"{step_name}Looking for Google Takeout structure in folder: {input_folder}. This may take long time. Please be patient...")
        root = Path(input_folder).expanduser()
        result = {
            "is_takeout": False,
            "has_year_folders": False,
            "has_google_photos_container": False,
            "has_archive_browser": False,
            "has_album_json_sidecars": False,
            "mode": "none",
            "matched_path": "",
            "container_path": "",
        }

        if not root.exists() or not root.is_dir():
            LOGGER.info(f"{step_name}No Google Takeout structure found in folder   : {input_folder}")
            return result

        queue = deque([str(root)])
        container_candidates = []
        while queue:
            current = queue.popleft()
            try:
                with os.scandir(current) as entries:
                    subdirs = [e for e in entries if e.is_dir(follow_symlinks=False)]
                    for entry in subdirs:
                        if _is_takeout_year_folder(entry.name):
                            result.update({
                                "is_takeout": True,
                                "has_year_folders": True,
                                "mode": "standard",
                                "matched_path": current,
                            })
                            LOGGER.info(f"{step_name}Found Google Takeout structure in folder      : {current}")
                            return result
                        if _looks_like_google_photos_container(entry.name):
                            container_candidates.append(Path(entry.path))
                    if len(subdirs) > 5:
                        LOGGER.debug(f"{step_name}Skipping {current} because it has {len(subdirs)} subdirectories")
                        continue
                    for entry in subdirs:
                        queue.append(entry.path)
            except PermissionError:
                LOGGER.warning(f"{step_name}Permission denied accessing: {current}")
            except Exception as e:
                LOGGER.warning(f"{step_name}Error scanning {current}: {e}")

        if _looks_like_google_photos_container(root.name):
            container_candidates.insert(0, root)

        seen_containers = set()
        for container_path in container_candidates:
            try:
                resolved_key = container_path.resolve().as_posix()
            except Exception:
                resolved_key = container_path.as_posix()
            if resolved_key in seen_containers:
                continue
            seen_containers.add(resolved_key)

            result["has_google_photos_container"] = True
            result["container_path"] = str(container_path)

            archive_browser_path = container_path.parent / "archive_browser.html"
            if not archive_browser_path.exists():
                continue
            result["has_archive_browser"] = True

            try:
                album_dirs = [child for child in container_path.iterdir() if child.is_dir()]
            except Exception:
                continue

            for album_dir in sorted(album_dirs, key=lambda p: p.name.casefold()):
                if _is_takeout_year_folder(album_dir.name):
                    continue
                if album_dir.name in {"@eaDir", FOLDERNAME_ALBUMS, FOLDERNAME_NO_ALBUMS, "Takeout"}:
                    continue
                try:
                    has_json = any(
                        item.is_file() and item.suffix.lower() == ".json"
                        for item in album_dir.rglob("*.json")
                    )
                except Exception:
                    has_json = False
                if has_json:
                    result.update({
                        "is_takeout": True,
                        "has_album_json_sidecars": True,
                        "mode": "album-only",
                        "matched_path": str(album_dir),
                    })
                    LOGGER.info(f"{step_name}Found Google Takeout album-only structure in folder: {album_dir}")
                    return result

        LOGGER.info(f"{step_name}No Google Takeout structure found in folder   : {input_folder}")
        return result


def _parse_createfile_failed_warning(line):
    if "CreateFile failed for" not in str(line):
        return None
    match = CREATEFILE_FAILED_RE.search(str(line))
    if not match:
        return None
    return {
        "line": str(line),
        "path": match.group("path"),
        "error": match.group("error"),
    }


def _normalize_dt_for_metadata_compare(dt_value):
    if dt_value is None:
        return None
    if isinstance(dt_value, str):
        dt_value = _parse_metadata_datetime(dt_value)
        if dt_value is None:
            return None
    return dt_value.replace(microsecond=0, tzinfo=None) if dt_value.tzinfo else dt_value.replace(microsecond=0)


def _parse_metadata_datetime(raw_value):
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    text = raw_value.strip()
    try:
        parsed = parser.parse(text)
        if isinstance(parsed, datetime):
            return parsed
    except Exception:
        parsed = None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _build_video_metadata_repair_args(file_path, dt_value):
    date_text = _normalize_dt_for_metadata_compare(dt_value).strftime("%Y:%m:%d %H:%M:%S")
    args = [
        "-overwrite_original",
        "-m",
        f"-QuickTime:CreateDate={date_text}",
        f"-QuickTime:ModifyDate={date_text}",
        f"-QuickTime:TrackCreateDate={date_text}",
        f"-QuickTime:TrackModifyDate={date_text}",
        f"-QuickTime:MediaCreateDate={date_text}",
        f"-QuickTime:MediaModifyDate={date_text}",
        f"-Keys:CreationDate={date_text}",
        f"-XMP:DateTimeOriginal={date_text}",
        f"-XMP:DateTime={date_text}",
        f"-XMP:CreateDate={date_text}",
        f"-XMP:ModifyDate={date_text}",
        f"-FileModifyDate={date_text}",
    ]
    if sys.platform.startswith("win") or sys.platform == "darwin":
        args.append(f"-FileCreateDate={date_text}")
    args.append(str(file_path))
    return args


def _select_video_native_metadata_date(entry):
    native_candidates = []
    for tag_name in VIDEO_NATIVE_DATE_TAGS:
        parsed = _parse_metadata_datetime(entry.get(tag_name))
        if parsed is None:
            continue
        native_candidates.append((parsed, tag_name))
    if not native_candidates:
        return None, None
    native_candidates.sort(key=lambda item: _normalize_dt_for_metadata_compare(item[0]))
    return native_candidates[0]


def _video_entry_needs_metadata_repair(file_path, entry):
    suffix = Path(file_path).suffix.lower()
    desired_dt, desired_source = _select_video_native_metadata_date(entry)
    if suffix not in VIDEO_EXT:
        return False, desired_dt, desired_source, []
    if desired_dt is None:
        fallback_source = str(entry.get("Source") or "")
        fallback_dt = _parse_metadata_datetime(entry.get("OldestDate"))
        if fallback_dt is None:
            return False, None, None, []
        if suffix not in VIDEO_METADATA_REPAIR_EXTENSIONS and not fallback_source.startswith(VIDEO_METADATA_REPAIR_SOURCE_PREFIXES):
            return False, fallback_dt, fallback_source or None, []
        if not fallback_source.startswith(VIDEO_METADATA_REPAIR_SOURCE_PREFIXES):
            return False, fallback_dt, fallback_source or None, []
        desired_dt = fallback_dt
        desired_source = fallback_source

    desired_cmp = _normalize_dt_for_metadata_compare(desired_dt)
    conflicting_tags = []
    for tag_name in VIDEO_XMP_DATE_TAGS:
        parsed = _parse_metadata_datetime(entry.get(tag_name))
        if parsed is None:
            continue
        if _normalize_dt_for_metadata_compare(parsed) != desired_cmp:
            conflicting_tags.append(tag_name)

    return bool(conflicting_tags), desired_dt, desired_source, conflicting_tags


def _update_video_entry_after_metadata_repair(entry, dt_value, source_tag):
    iso_value = dt_value.isoformat()
    entry["OldestDate"] = iso_value
    if source_tag:
        entry["Source"] = source_tag
    for tag_name in (
        "QuickTime:CreateDate",
        "QuickTime:ModifyDate",
        "QuickTime:TrackCreateDate",
        "QuickTime:TrackModifyDate",
        "QuickTime:MediaCreateDate",
        "QuickTime:MediaModifyDate",
        "Keys:CreationDate",
        "XMP:DateTimeOriginal",
        "XMP:DateTime",
        "XMP:CreateDate",
        "XMP:ModifyDate",
        "File:FileModifyDate",
    ):
        entry[tag_name] = iso_value


def _start_exiftool_stay_open(exif_tool_path):
    return subprocess.Popen(
        [exif_tool_path, "-stay_open", "True", "-@", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )


def _execute_exiftool_stay_open(process, args, execute_id):
    if process.poll() is not None:
        raise RuntimeError("ExifTool stay_open process is no longer running.")
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("ExifTool stay_open pipes are not available.")

    ready_token = f"{{ready{execute_id}}}"
    payload = "\n".join([*args, f"-execute{execute_id}"]) + "\n"
    process.stdin.write(payload)
    process.stdin.flush()

    output_lines = []
    while True:
        line = process.stdout.readline()
        if line == "":
            if process.poll() is not None:
                raise RuntimeError("ExifTool stay_open process terminated before signaling completion.")
            continue
        if line.strip() == ready_token:
            break
        output_lines.append(line.rstrip("\r\n"))

    return output_lines


def _stop_exiftool_stay_open(process):
    if process is None:
        return
    try:
        if process.poll() is None and process.stdin is not None:
            process.stdin.write("-stay_open\nFalse\n")
            process.stdin.flush()
            process.stdin.close()
        process.wait(timeout=10)
    except Exception:
        process.kill()
        process.wait(timeout=5)


def repair_conflicting_video_xmp_dates(folder_analyzer=None, step_name="", log_level=None):
    """
    Normalize processed video metadata when GPTH leaves conflicting XMP dates
    after writing a valid native container date.
    """
    with set_log_level(LOGGER, log_level):
        extracted_dates = folder_analyzer.get_extracted_dates() if folder_analyzer else {}
        if not extracted_dates:
            LOGGER.info(f"{step_name}No extracted dates available. Skipping processed video metadata repair.")
            return 0

        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        if not Path(exif_tool_path).exists():
            LOGGER.warning(f"{step_name}ExifTool not found at '{exif_tool_path}'. Skipping processed video metadata repair.")
            return 0
        ensure_executable(exif_tool_path)

        repair_jobs = []
        skipped_missing_files = 0
        for file_path, entry in extracted_dates.items():
            needs_fix, desired_dt, desired_source, conflicting_tags = _video_entry_needs_metadata_repair(file_path, entry)
            if not needs_fix:
                continue

            resolved_path = Path(entry.get("TargetFile") or file_path)
            if not resolved_path.exists():
                skipped_missing_files += 1
                continue

            repair_jobs.append(
                {
                    "path": resolved_path,
                    "entry": entry,
                    "desired_dt": desired_dt,
                    "desired_source": desired_source,
                    "conflicting_tags": conflicting_tags,
                }
            )

        total_conflicts = len(repair_jobs)
        if not total_conflicts:
            LOGGER.info(f"{step_name}No conflicting video XMP dates detected. Skipping processed video metadata repair.")
            if skipped_missing_files:
                LOGGER.warning(f"{step_name}Skipped {skipped_missing_files} conflicting video files that no longer exist before metadata repair.")
            return 0

        LOGGER.info(
            f"{step_name}Detected {total_conflicts} video files with conflicting XMP dates. "
            f"Starting normalization with persistent ExifTool session..."
        )

        repaired_count = 0
        failed_count = 0
        process = None
        use_stay_open = True
        try:
            process = _start_exiftool_stay_open(exif_tool_path)
        except (OSError, ValueError) as e:
            use_stay_open = False
            LOGGER.warning(
                f"{step_name}Could not start persistent ExifTool session "
                f"('{e}'). Falling back to per-file execution."
            )

        try:
            with tqdm(
                total=total_conflicts,
                smoothing=0.1,
                desc=f"{MSG_TAGS['INFO']}{step_name}Normalizing conflicting video XMP dates",
                unit=" files",
            ) as pbar:
                for execute_id, job in enumerate(repair_jobs, start=1):
                    if use_stay_open:
                        try:
                            output_lines = _execute_exiftool_stay_open(
                                process,
                                _build_video_metadata_repair_args(job["path"], job["desired_dt"]),
                                execute_id,
                            )
                            details = " | ".join(line.strip() for line in output_lines if line.strip())
                            error_detected = any("error" in line.lower() for line in output_lines)
                            if error_detected:
                                failed_count += 1
                                LOGGER.warning(
                                    f"{step_name}Failed to normalize video metadata for '{job['path']}': "
                                    f"{details[:400] or 'ExifTool reported an error.'}"
                                )
                                pbar.update(1)
                                continue
                        except Exception as e:
                            failed_count += 1
                            LOGGER.warning(f"{step_name}Failed to normalize video metadata for '{job['path']}': {e}")
                            pbar.update(1)
                            continue
                    else:
                        command = [exif_tool_path, *_build_video_metadata_repair_args(job["path"], job["desired_dt"])]
                        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
                        if result.returncode != 0:
                            failed_count += 1
                            details = (result.stderr or result.stdout or "").strip()
                            LOGGER.warning(
                                f"{step_name}Failed to normalize video metadata for '{job['path']}': "
                                f"{details[:400] or f'ExifTool exit code {result.returncode}'}"
                            )
                            pbar.update(1)
                            continue

                    _update_video_entry_after_metadata_repair(job["entry"], job["desired_dt"], job["desired_source"])
                    repaired_count += 1
                    LOGGER.debug(
                        f"{step_name}Normalized conflicting video XMP dates for '{job['path']}' "
                        f"(tags: {', '.join(job['conflicting_tags'])})."
                    )
                    pbar.update(1)
        finally:
            _stop_exiftool_stay_open(process)

        LOGGER.info(f"{step_name}Processed video metadata normalized for {repaired_count} of {total_conflicts} conflicting files.")
        if failed_count:
            LOGGER.warning(f"{step_name}Failed to normalize metadata for {failed_count} conflicting video files.")
        if skipped_missing_files:
            LOGGER.warning(f"{step_name}Skipped {skipped_missing_files} conflicting video files that no longer exist before metadata repair.")
        return repaired_count


def remap_extracted_dates_json_for_new_root(filedates_json, source_root, target_root, step_name="", log_level=None):
    """
    Clone the extracted-dates JSON replacing path keys under source_root
    with equivalent paths under target_root.
    """
    with set_log_level(LOGGER, log_level):
        if not filedates_json or not os.path.exists(filedates_json):
            return filedates_json

        source_root = Path(source_root).resolve()
        target_root = Path(target_root).resolve()

        try:
            with open(filedates_json, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as e:
            LOGGER.warning(f"{step_name}Could not read Extracted Dates JSON '{filedates_json}' to remap paths for GPTH fix mode: {e}")
            return filedates_json

        if not isinstance(payload, dict):
            LOGGER.warning(f"{step_name}Extracted Dates JSON '{filedates_json}' has unexpected format. Reusing original file without path remap.")
            return filedates_json

        remapped_payload = {}
        remapped_count = 0
        for raw_path, metadata in payload.items():
            new_key = str(raw_path)
            try:
                rel_path = Path(raw_path).resolve().relative_to(source_root)
                new_key = (target_root / rel_path).resolve().as_posix()
                remapped_count += 1
            except Exception:
                pass
            remapped_payload[new_key] = metadata

        if remapped_count == 0:
            LOGGER.warning(f"{step_name}No paths from '{filedates_json}' matched source root '{source_root}'. Reusing original file without path remap.")
            return filedates_json

        source_json_path = Path(filedates_json)
        remapped_json_path = source_json_path.with_name(f"{source_json_path.stem}_gpth_fix{source_json_path.suffix}")
        with open(remapped_json_path, "w", encoding="utf-8") as fh:
            json.dump(remapped_payload, fh, ensure_ascii=False, indent=2)

        LOGGER.info(f"{step_name}Prepared remapped Extracted Dates JSON for GPTH fix mode: '{remapped_json_path}'")
        return str(remapped_json_path)


def prepare_output_folder_for_gpth_fix(input_folder, output_folder, filedates_json=None, step_name="", log_level=None):
    """
    Ensure GPTH fix mode works on a staged copy inside output_folder so later
    output-dependent steps (symlink fixing, post-process, final cleanup) operate
    on the same files GPTH actually modified.
    """
    with set_log_level(LOGGER, log_level):
        input_folder = os.path.abspath(input_folder)
        output_folder = os.path.abspath(output_folder)

        if not os.path.isdir(input_folder):
            LOGGER.error(f"{step_name}Cannot prepare GPTH fix mode because input folder does not exist: '{input_folder}'")
            return None, None, False

        output_has_content = False
        if os.path.isdir(output_folder):
            try:
                with os.scandir(output_folder) as entries:
                    output_has_content = any(True for _ in entries)
            except Exception:
                output_has_content = False

        staged = output_has_content
        if not output_has_content:
            LOGGER.warning(f"{step_name}Takeout structure checks are being ignored. Staging files into output folder before running GPTH fix mode...")
            staged = copy_move_folder(
                src=input_folder,
                dst=output_folder,
                ignore_patterns=None,
                move=False,
                step_name=step_name,
                log_level=log_level
            )
            if not staged:
                LOGGER.error(f"{step_name}Could not stage files into output folder for GPTH fix mode.")
                return None, None, False
        else:
            LOGGER.warning(f"{step_name}Reusing existing non-empty output folder for GPTH fix mode: '{output_folder}'")

        remapped_json = remap_extracted_dates_json_for_new_root(
            filedates_json=filedates_json,
            source_root=input_folder,
            target_root=output_folder,
            step_name=step_name,
            log_level=log_level
        )

        return output_folder, remapped_json, True


def select_gpth_fix_target_folder(input_folder, takeout_detection_info=None):
    """
    Select the folder that should be passed to `gpth --fix`.

    GPTH fix mode only scans one level of subfolders, so the target must be the
    direct parent of the album folders to process.
    """
    detection_info = takeout_detection_info or {}
    container_path = str(detection_info.get("container_path") or "").strip()
    if container_path:
        return os.path.abspath(container_path)
    return os.path.abspath(input_folder)


def should_auto_force_gpth_fix(takeout_detection_info=None):
    detection_info = takeout_detection_info or {}
    return str(detection_info.get("mode") or "").strip().lower() == "album-only"


def should_recover_orphan_album_assets(takeout_detection_info=None):
    detection_info = takeout_detection_info or {}
    return bool(detection_info.get("has_year_folders"))


def remap_takeout_detection_info_root(takeout_detection_info=None, source_root=None, target_root=None):
    """
    Remap path-like entries from a previously detected Takeout root into a new root.
    """
    details = dict(takeout_detection_info or {})
    source_text = str(source_root or "").strip()
    target_text = str(target_root or "").strip()
    if not source_text or not target_text:
        return details

    try:
        source_path = Path(source_text).resolve()
        target_path = Path(target_text).resolve()
    except Exception:
        return details

    for key in ("matched_path", "container_path"):
        raw_value = str(details.get(key) or "").strip()
        if not raw_value:
            continue
        try:
            relative_path = Path(raw_value).resolve().relative_to(source_path)
        except Exception:
            continue
        details[key] = str((target_path / relative_path).resolve())
    return details


def prepare_gpth_fix_working_input(input_folder, takeout_detection_info=None, keep_takeout_folder=False, filedates_json=None, timestamp=None, input_is_disposable=False, step_name="", log_level=None):
    """
    Prepare the working root for GPTH fix mode.

    When keep_takeout_folder is enabled, GPTH fix must not modify the original
    Takeout tree in place, so a temporary working clone is created first.
    """
    with set_log_level(LOGGER, log_level):
        working_input_root = os.path.abspath(input_folder)
        remapped_json = filedates_json
        cloned_from = None
        effective_detection_info = dict(takeout_detection_info or {})

        if keep_takeout_folder and not input_is_disposable:
            source_root = Path(working_input_root).resolve()
            clone_suffix = timestamp or TIMESTAMP
            cloned_root = source_root.parent / f"{source_root.name}_gpth_fix_tmp_{clone_suffix}"
            LOGGER.warning(
                f"{step_name}GPTH fix mode would modify files in place. "
                f"Because '--google-keep-takeout-folder' is active, a temporary working copy will be created first."
            )
            cloned_path = clone_folder_fast(
                input_folder=str(source_root),
                cloned_folder=str(cloned_root),
                step_name=step_name,
                log_level=log_level,
            )
            if os.path.abspath(cloned_path) == os.path.abspath(str(source_root)):
                LOGGER.error(f"{step_name}Could not create a temporary working copy for GPTH fix mode.")
                return None, None, None, None
            working_input_root = os.path.abspath(cloned_path)
            cloned_from = str(source_root)
            remapped_json = remap_extracted_dates_json_for_new_root(
                filedates_json=filedates_json,
                source_root=str(source_root),
                target_root=working_input_root,
                step_name=step_name,
                log_level=log_level,
            )
            effective_detection_info = remap_takeout_detection_info_root(
                takeout_detection_info=effective_detection_info,
                source_root=str(source_root),
                target_root=working_input_root,
            )
        elif keep_takeout_folder and input_is_disposable:
            LOGGER.info(
                f"{step_name}Skipping extra GPTH fix clone because the current working input is already disposable "
                f"(for example an unzipped staging folder or a previous temporary clone)."
            )

        fix_target_folder = select_gpth_fix_target_folder(
            input_folder=working_input_root,
            takeout_detection_info=effective_detection_info,
        )
        return working_input_root, fix_target_folder, remapped_json, cloned_from


def relocate_gpth_fix_outputs(fix_root, output_folder, step_name="", log_level=None):
    """
    Move the folders/files generated by GPTH `--fix` from the in-place working
    root into PhotoMigrator's configured output folder.
    """
    with set_log_level(LOGGER, log_level):
        fix_root = Path(fix_root).resolve()
        output_root = Path(output_folder).resolve()

        if fix_root == output_root:
            LOGGER.info(f"{step_name}GPTH fix output root already matches PhotoMigrator output folder. No relocation needed.")
            _relocate_misclassified_special_folders(base_root=output_root, step_name=step_name, log_level=log_level)
            preserve_archive_browser_artifacts(output_folder=str(output_root), step_name=step_name, log_level=log_level)
            return True

        output_root.mkdir(parents=True, exist_ok=True)
        artifact_names = [
            FOLDERNAME_NO_ALBUMS,
            FOLDERNAME_ALBUMS,
            "Special Folders",
            "Special_Folders",
            "PARTNER_SHARED",
            f"{FOLDERNAME_ALBUMS}-shared",
        ]
        moved_any = False

        for artifact_name in artifact_names:
            source_path = fix_root / artifact_name
            if not source_path.exists() and not source_path.is_symlink():
                continue

            destination_path = output_root / artifact_name
            LOGGER.info(f"{step_name}Relocating GPTH fix artifact '{source_path}' -> '{destination_path}'")
            if source_path.is_dir() and destination_path.exists():
                ok = copy_move_folder(
                    str(source_path),
                    str(destination_path),
                    move=True,
                    step_name=step_name,
                    log_level=log_level,
                )
                if not ok:
                    LOGGER.error(f"{step_name}Failed to merge GPTH fix artifact '{source_path}' into '{destination_path}'")
                    return False
                remove_empty_dirs(input_folder=str(source_path), log_level=log_level)
                with suppress(Exception):
                    source_path.rmdir()
            else:
                if destination_path.exists() or destination_path.is_symlink():
                    if destination_path.is_dir() and not source_path.is_dir():
                        LOGGER.error(
                            f"{step_name}Cannot relocate GPTH fix artifact '{source_path}' because destination directory already exists: '{destination_path}'"
                        )
                        return False
                    if destination_path.is_dir():
                        shutil.rmtree(destination_path)
                    else:
                        destination_path.unlink()
                shutil.move(str(source_path), str(destination_path))
            moved_any = True

        for source_path in sorted(fix_root.iterdir(), key=lambda p: p.name.casefold()):
            if not source_path.is_file():
                continue
            lower_name = source_path.name.casefold()
            lower_suffix = source_path.suffix.casefold()
            if "gpth" not in lower_name or lower_suffix not in {".log", ".txt"}:
                continue
            destination_path = output_root / source_path.name
            if destination_path.exists() or destination_path.is_symlink():
                destination_path = output_root / f"{source_path.stem}_relocated{source_path.suffix}"
            LOGGER.info(f"{step_name}Relocating GPTH log '{source_path}' -> '{destination_path}'")
            shutil.move(str(source_path), str(destination_path))
            moved_any = True

        for archive_candidate in (fix_root / "archive_browser.html", fix_root.parent / "archive_browser.html"):
            if not archive_candidate.exists():
                continue
            destination_html = output_root / "archive_browser.html"
            if archive_candidate.resolve() != destination_html.resolve():
                shutil.copy2(archive_candidate, destination_html)
            break

        _relocate_misclassified_special_folders(base_root=output_root, step_name=step_name, log_level=log_level)
        preserve_archive_browser_artifacts(output_folder=str(output_root), step_name=step_name, log_level=log_level)

        if not moved_any:
            LOGGER.warning(
                f"{step_name}GPTH fix mode finished but none of the expected output artifacts were found under '{fix_root}'."
            )
        return True


##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassTakeoutFolder(ClassLocalFolder):
    def _sync_local_folder_view(self):
        self.base_folder = Path(self.output_folder)
        if not self.ARGS['google-skip-move-albums']:
            self.albums_folder = self.base_folder / FOLDERNAME_ALBUMS
        else:
            self.albums_folder = self.base_folder
        self.shared_albums_folder = self.base_folder / f"{FOLDERNAME_ALBUMS}-shared"
        self.no_albums_folder = self.base_folder / FOLDERNAME_NO_ALBUMS

    def __init__(self, takeout_folder):
        """
        Inicializa la clase con la carpeta base (donde se guardan los archivos ya procesados)
        y la carpeta de entrada (donde se encuentran los archivos sin procesar).
        """
        from Core.GlobalVariables import ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS
        from Core.DataModels import init_process_results

        self.ARGS = ARGS
        self.TIMESTAMP = TIMESTAMP
        self.DEPRIORITIZE_FOLDERS_PATTERNS = DEPRIORITIZE_FOLDERS_PATTERNS
        self.log_level = logging.INFO

        # # Create atributes from the ARGS given:
        # self.skip_gpth                      = self.ARGS['google-skip-gpth-tool']
        # self.ignore_takeout_structure       = self.ARGS['google-ignore-check-structure']

        # Assign takeout_folder from the given argument when create the object
        self.takeout_folder = Path(takeout_folder).expanduser()  # Folder given when create the object
        offending_component = _find_forbidden_special_folder_in_path(self.takeout_folder)
        if offending_component:
            blocked_folders = ", ".join([f"'{name}'" for name in TAKEOUT_SPECIAL_FOLDER_NAMES])
            LOGGER.error(f"Invalid --google-takeout path: '{self.takeout_folder}'")
            LOGGER.error(
                f"The input path contains forbidden folder '{offending_component}', which conflicts with Google special folders."
            )
            LOGGER.error(
                f"Please move/rename the Takeout path so it does not contain any of: {blocked_folders}"
            )
            sys.exit(1)
        self.takeout_folder.mkdir(parents=True, exist_ok=True)  # Asegurar que takeout_folder existe

        self.takeout_detection_info = {
            "is_takeout": False,
            "has_year_folders": False,
            "has_google_photos_container": False,
            "has_archive_browser": False,
            "has_album_json_sidecars": False,
            "mode": "none",
            "matched_path": "",
            "container_path": "",
        }

        # Verificar si la carpeta necesita ser descomprimida
        self.needs_unzip = self.check_if_needs_unzip(log_level=logging.WARNING)
        self.unzipped_folder = None # Only will have value if the Takeout have been already unzipped

        # Backup_folder in case of needed
        self.backup_takeout_folder = None

        # Verificar si la carpeta necesita ser procesada
        self.needs_process = self.check_if_needs_process(log_level=logging.WARNING)

        # Set input_folder as the input for the Preprocessing and Processing Phases
        self.input_folder = self.get_input_folder()

        # Initiate the output_folder
        self.output_folder = self.get_output_folder()

        # Set Albums Folder
        self.albums_folder = self.get_albums_folder()
        self._sync_local_folder_view()

        # Define the Folder Analyzers
        self.initial_takeout_folder_analyzer = FolderAnalyzer()
        self.output_folder_analyzer = FolderAnalyzer()
        self.initial_filedates_json = ""
        self.final_filedates_json = ""

        # Contador de pasos durante el procesamiento
        self.step = 0
        self.substep = 0

        # Create steps_duration list
        self.steps_duration = []

        # Create and init self.result dict
        self.result = init_process_results()

        self.CLIENT_NAME = f'Google Takeout Folder ({self.takeout_folder.name})'

#---------------------------------------------- CLASS METHODS ----------------------------------------------
    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_process(self, log_level=None):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            self.takeout_detection_info = inspect_takeout_structure(input_folder=self.takeout_folder, log_level=log_level)
            return bool(self.takeout_detection_info.get("is_takeout"))

    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_unzip(self, log_level=None):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            for file in os.listdir(self.takeout_folder):
                if file.endswith('.zip'):
                    return True
            return False

    def get_input_folder(self):
        if self.unzipped_folder:
            self.input_folder = self.unzipped_folder
        else:
            self.input_folder = self.takeout_folder
        return self.input_folder

    def get_albums_folder(self):
        if not self.ARGS['google-skip-move-albums']:
            self.albums_folder = Path(self.output_folder) / FOLDERNAME_ALBUMS
        else:
            self.albums_folder = Path(self.output_folder)
        return self.albums_folder

    def get_output_folder(self):
        if self.needs_process or self.ARGS['google-ignore-check-structure']:
            if self.ARGS['output-folder']:
                self.output_folder = Path(self.ARGS['output-folder'])
            else:
                self.output_folder = build_generated_output_folder(
                    self.takeout_folder,
                    self.ARGS['google-output-folder-suffix'],
                    self.TIMESTAMP,
                    strip_stage_names={"unzipped"},
                )
        else:
            self.output_folder = self.takeout_folder
        # Call get_albums_folder to update it with the new output_folder
        self.get_albums_folder()
        self._sync_local_folder_view()
        return self.output_folder

    def normalize_input_root_for_gpth(self, step_name="", log_level=None):
        """
        Normalize input root so GPTH always receives a Takeout-compatible root.

        Rules:
          - If input already points to <...>/Takeout (or any non localized "Google Photos" folder), do nothing.
          - If input points to <...>/Takeout/<Google Photos localized folder>, switch root to parent <...>/Takeout.
          - If input points to <...>/<Google Photos localized folder> and parent is not "Takeout",
            create sibling wrapper <...>/_gpth_wrap_<TIMESTAMP>/Takeout/Google Photos
            and move the folder there (no copy fallback).
        """
        with set_log_level(LOGGER, log_level):
            current_input = Path(self.get_input_folder())
            if not _looks_like_google_photos_container(current_input.name):
                return False

            parent = current_input.parent

            # Case 1: direct Google Photos under Takeout -> just use Takeout root.
            if parent.name.lower() == "takeout":
                LOGGER.info(f"{step_name}Detected input folder as Google Photos subfolder. Using parent Takeout folder for GPTH input.")
                self.takeout_folder = parent
                if self.unzipped_folder:
                    self.unzipped_folder = parent
                self.input_folder = parent
                self.needs_unzip = self.check_if_needs_unzip(log_level=logging.WARNING)
                self.needs_process = self.check_if_needs_process(log_level=logging.WARNING)
                self.output_folder = self.get_output_folder()
                self.get_albums_folder()
                return True

            # Case 2: Google Photos folder without Takeout parent -> build wrapper and move.
            wrapper_root = parent / f"_gpth_wrap_{self.TIMESTAMP}"
            wrapper_takeout = wrapper_root / "Takeout"
            target_google_photos = wrapper_takeout / current_input.name

            if wrapper_root.exists():
                LOGGER.error(f"{step_name}Cannot normalize Takeout structure because wrapper folder already exists: '{wrapper_root}'")
                raise RuntimeError(f"Wrapper folder already exists: {wrapper_root}")

            LOGGER.warning(f"{step_name}Input folder points directly to localized 'Google Photos' folder without 'Takeout' parent.")
            LOGGER.warning(f"{step_name}Normalizing structure for GPTH by moving folder (no copy fallback):")
            LOGGER.warning(f"{step_name}  Source: '{current_input}'")
            LOGGER.warning(f"{step_name}  Target: '{target_google_photos}'")

            try:
                wrapper_takeout.mkdir(parents=True, exist_ok=False)
                current_input.rename(target_google_photos)
            except Exception as e:
                LOGGER.error(f"{step_name}Failed to normalize Takeout structure using move/rename: {e}")
                LOGGER.error(f"{step_name}Aborting to avoid dangerous copy fallback for large Takeout datasets.")
                raise RuntimeError("Could not normalize Takeout structure with move/rename.") from e

            self.takeout_folder = wrapper_takeout
            if self.unzipped_folder:
                self.unzipped_folder = wrapper_takeout
            self.input_folder = wrapper_takeout
            self.needs_unzip = self.check_if_needs_unzip(log_level=logging.WARNING)
            self.needs_process = self.check_if_needs_process(log_level=logging.WARNING)
            self.output_folder = self.get_output_folder()
            self.get_albums_folder()
            LOGGER.info(f"{step_name}Takeout structure normalized successfully for GPTH.")
            return True

    def analyze_folder(self, folder_to_analyze, folder_type='output', step_name='', save_json=True, json_filename=None):
        # Analyze Folder using the New Class FolderAnalyzer to extract files dates and to count all file types from a given folder
        # ----------------------------------------------------------------------------------------------------------------------
        step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
        sub_step_start_time = datetime.now()
        if folder_type.lower() == 'input':
            self.initial_takeout_folder_analyzer = FolderAnalyzer(folder_path=folder_to_analyze, force_date_extraction=False, logger=LOGGER, step_name=step_name)
            # self.initial_takeout_folder_analyzer.extract_dates(use_fallback_to_filename=False, step_name=step_name) # Avoid to use filename to guess dates from filename to do a fair comparison between pre/post
            self.initial_takeout_folder_analyzer.extract_dates(step_name=step_name) # Use filename to guess dates and save them in the JSON, but does not count GUESS dates in the count_files function
            counters = self.initial_takeout_folder_analyzer.count_files(exclude_fallbacks=True, step_name=step_name) # Avoid to use filename to guess dates from filename to do a fair comparison between pre/post
            if save_json:
                if json_filename is None:
                    json_filename = f"takeout_input_dates_metadata.json"
                self.initial_filedates_json = self.initial_takeout_folder_analyzer.save_to_json(output_file=json_filename, step_name=step_name)
            # Define folder and sub_dict counters
            folder = 'Takeout folder'
            sub_dict = 'input_counters'
        elif folder_type.lower() == 'output':
            self.output_folder_analyzer = FolderAnalyzer(folder_path=folder_to_analyze, force_date_extraction=True, logger=LOGGER, step_name=step_name)
            # self.output_folder_analyzer.extract_dates(step_name=step_name)
            counters = self.output_folder_analyzer.count_files(exclude_fallbacks=False, step_name=step_name)
            if save_json:
                if json_filename is None:
                    json_filename = f"takeout_output_dates_metadata.json"
                self.final_filedates_json = self.output_folder_analyzer.save_to_json(output_file=json_filename, step_name=step_name)
            # Define folder and sub_dict counters
            folder = 'Output folder'
            sub_dict = 'output_counters'

        # Clean input/output dict
        self.result[sub_dict].clear()
        # Assign all pairs key-value from output_counters to counter['output_counters'] dict
        self.result[sub_dict].update(counters)
        result = self.result

        # Present Results
        # ----------------------------------------------------------------------------------------------------------------------
        COL1_WIDTH = 44  # Description
        COL2_WIDTH = 7   # Counters
        COL3_WIDTH = 40  # "(Physical: xxxx | Symlinks: yyyyyy)"
        TOTAL_WIDTH = COL1_WIDTH + COL2_WIDTH + COL3_WIDTH

        inp = result[sub_dict]

        phys_total_files = inp['total_files'] - inp['total_symlinks']
        phys_supported   = inp['supported_files'] - inp['supported_symlinks']
        phys_media       = inp['media_files'] - inp['media_symlinks']
        phys_photos      = inp['photo_files'] - inp['photo_symlinks']
        phys_videos      = inp['video_files'] - inp['video_symlinks']

        PHYS_DIGITS    = max(6, len(str(max(phys_total_files, phys_supported, phys_media, phys_photos, phys_videos))))
        SYMLINK_DIGITS = max(6, len(str(max(inp['total_symlinks'], inp['supported_symlinks'], inp['media_symlinks'], inp['photo_symlinks'], inp['video_symlinks']))))

        def fmt_phys_syml(total, syms):
            phys = total - syms
            return f"(Physical: {phys:>{PHYS_DIGITS}} | Symlinks: {syms:>{SYMLINK_DIGITS}})"

        PCT_DIGITS = max(
            3,
            len(str(int(inp['photos']['pct_with_date']))),
            len(str(int(inp['photos']['pct_without_date']))),
            len(str(int(inp['videos']['pct_with_date']))),
            len(str(int(inp['videos']['pct_without_date'])))
        ) + 2

        LOGGER.info(f"{step_name}Analyzing {folder} completed!")
        LOGGER.info(f"{step_name}{'-' * TOTAL_WIDTH}")
        LOGGER.info(f"{step_name}{'Total Size of ' + folder:<{COL1_WIDTH}}: {inp['total_size_mb'] / 1024:>{COL2_WIDTH}.2f} (GB)")
        LOGGER.info(f"{step_name}{'Total Files in ' + folder:<{COL1_WIDTH}}: {inp['total_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['total_files'], inp['total_symlinks']):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'Total Non-Supported files in ' + folder:<{COL1_WIDTH}}: {inp['unsupported_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['unsupported_files'], 0):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'Total Supported files in ' + folder:<{COL1_WIDTH}}: {inp['supported_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['supported_files'], inp['supported_symlinks']):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'  - Total Non-Media files in ' + folder:<{COL1_WIDTH}}: {inp['non_media_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['non_media_files'], 0):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'    - Total Metadata in ' + folder:<{COL1_WIDTH}}: {inp['metadata_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['metadata_files'], 0):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'    - Total Sidecars in ' + folder:<{COL1_WIDTH}}: {inp['sidecar_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['sidecar_files'], 0):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'-' * TOTAL_WIDTH}")
        LOGGER.info(f"{step_name}{'  - Total Media files in ' + folder:<{COL1_WIDTH}}: {inp['media_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['media_files'], inp['media_symlinks']):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'    - Total Photos in ' + folder:<{COL1_WIDTH}}: {inp['photo_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['photo_files'], inp['photo_symlinks']):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'      - With Date':<{COL1_WIDTH}}: {inp['photos']['with_date']:>{COL2_WIDTH}} ({inp['photos']['pct_with_date']:>{PCT_DIGITS}.1f}%)")
        LOGGER.info(f"{step_name}{'      - Without Date':<{COL1_WIDTH}}: {inp['photos']['without_date']:>{COL2_WIDTH}} ({inp['photos']['pct_without_date']:>{PCT_DIGITS}.1f}%)")
        LOGGER.info(f"{step_name}{'    - Total Videos in ' + folder:<{COL1_WIDTH}}: {inp['video_files']:>{COL2_WIDTH}} {fmt_phys_syml(inp['video_files'], inp['video_symlinks']):<{COL3_WIDTH}}")
        LOGGER.info(f"{step_name}{'      - With Date':<{COL1_WIDTH}}: {inp['videos']['with_date']:>{COL2_WIDTH}} ({inp['videos']['pct_with_date']:>{PCT_DIGITS}.1f}%)")
        LOGGER.info(f"{step_name}{'      - Without Date':<{COL1_WIDTH}}: {inp['videos']['without_date']:>{COL2_WIDTH}} ({inp['videos']['pct_without_date']:>{PCT_DIGITS}.1f}%)")
        LOGGER.info(f"{step_name}{'-' * TOTAL_WIDTH}")


        sub_step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Step {self.step}: {step_name_cleaned} completed in {formatted_duration}.")
        self.steps_duration.append({'step_id': f"{self.step}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

    def pre_checks(self, log_level=None):
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            # Start Pre-Checking
            self.step += 1
            self.substep = 0
            step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. PRE-CHECKING TAKEOUT FOLDER...  ")
            LOGGER.info(f"================================================================================================================================================")

            # Sub-Step 1: Extraction Process
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🔍 [PRE-CHECKS]-[Unzip Takeout  ] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. UNZIP TAKEOUT (IF NEEDED)... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if self.needs_unzip:
                LOGGER.info(f"{step_name}📦 Input Folder contains ZIP files and needs to be unzipped first.")
                LOGGER.info(f"{step_name}📦 This process might take long time, depending on how big is your Takeout.")
                LOGGER.info(f"{step_name}📦 Unzipping Takeout Folder...Be patient... 🙂")
                # Make the 'Unzipped' folder as the new takeout_folder for the object
                self.unzipped_folder= Path(f"{self.takeout_folder}_unzipped_{self.TIMESTAMP}")
                # Unzip the files into unzip_folder
                sanitize_and_unpack_zips(input_folder=self.takeout_folder, unzip_folder=self.unzipped_folder, step_name=step_name, log_level=self.log_level)
                # Update input_folder to take the new unzipped folder as reference
                self.input_folder = self.unzipped_folder
                # Change flag self.check_if_needs_unzip to False
                self.needs_unzip = False
                self.takeout_detection_info = inspect_takeout_structure(input_folder=self.input_folder, step_name=step_name)
                self.needs_process = bool(self.takeout_detection_info.get("is_takeout"))
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Sub-Step 2: create_backup_if_needed
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🔍 [PRE-CHECKS]-[Clone Takeout  ] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. CLONE ORIGINAL TAKEOUT TO KEEP A BACKUP (IF ADDED '-gKeepTakeout' OPTION)... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if self.ARGS.get('google-keep-takeout-folder'):
                if not self.unzipped_folder:
                    # Determine the input_folder depending if the Takeout have been unzipped or not
                    input_folder = self.get_input_folder()
                    LOGGER.info(f"")
                    LOGGER.warning(f"{step_name}Flag '-gKeepTakeout, --google-keep-takeout-folder' detected. Cloning Takeout Folder...")
                    # Generate the target temporary folder path
                    parent_dir = dirname(self.takeout_folder)
                    folder_name = basename(self.takeout_folder)
                    cloned_folder = os.path.join(parent_dir, f"{folder_name}_tmp_{TIMESTAMP}")
                    # Call the cloning function
                    tmp_folder = clone_folder_fast (input_folder=self.input_folder, cloned_folder=cloned_folder, step_name=step_name, log_level=log_level)
                    if tmp_folder != self.input_folder:
                        ARGS['google-takeout'] = tmp_folder
                        self.input_folder = Path(tmp_folder)
                        self.unzipped_folder = Path(tmp_folder)
                        self.backup_takeout_folder = input_folder
                        self.takeout_detection_info = remap_takeout_detection_info_root(
                            takeout_detection_info=self.takeout_detection_info,
                            source_root=input_folder,
                            target_root=tmp_folder,
                        )
                        LOGGER.info(f"{step_name}Takeout folder cloned successfully and will be used as working folder for next steps. ")
                        LOGGER.info(f"{step_name}Your original Takeout files have been safely preserved in the folder: '{self.backup_takeout_folder}' ")
                    sub_step_end_time = datetime.now()
                    formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
                else:
                    LOGGER.warning(f"{step_name}Flag '-gKeepTakeout, --google-keep-takeout-folder' detected, but Takeout have been unzipped. No need to clone Input folder")
                    formatted_duration = f"Skipped"
                    LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[') + 1: step_name.rfind(']')].strip()}'")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Finally show TOTAL DURATION OF PRE-CHECKS PHASE
            step_name = '🔍 [PRE-CHECKS] : '
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})

            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '-[TOTAL DURATION]', 'duration': formatted_duration})


    def pre_process(self, log_level=None):
        # Start Pre-Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            self.substep = 0
            step_start_time = datetime.now()

            # Determine the input_folder deppending if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()

            # Sub-Step 1: Delete hidden subfolders '@eaDir'
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[Sanitize Takeout Folder]   : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. CLEAN AND SANITIZE TAKEOUT FOLDER... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Sanitizing input folder (fix folders/files ending with spaces or dosts to avoid SMB mingling names)...")
            sanitize_names(input_folder=input_folder, step_name=step_name, log_level=log_level)
            LOGGER.info(f"{step_name}Cleaning hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
            delete_subfolders(input_folder=input_folder, folder_name_to_delete="@eaDir", step_name=step_name, log_level=LOG_LEVEL)
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 2: Fix .MP4 JSON
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[MP4/Live Pics. Fixer] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. FIX LIVE/MOTION PICTURES WITH ASSOCIATED MP4 FILES... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
            total_mp4_files_fixed = fix_mp4_files(input_folder=input_folder, step_name=step_name, log_level=LOG_LEVEL)
            LOGGER.info(f"{step_name}Fixing MP4 from live pictures metadata finished!")
            LOGGER.info(f"{step_name}Total MP4 from live pictures Files fixed         : {total_mp4_files_fixed}")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 3: Fix truncated suffixes (such as '-ha edit.jpg' or '-ha e.jpg', or '-effec', or '-supplemen',...)
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[Truncations Fixer   ] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. FIX TRUNCATIONS ON MEDIA EXTENSIONS OR JSON SPECIAL SUFFIXES (like '.supplemental-metadata', '-editted', '-effects', etc)... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Fixing Truncated Special Suffixes from Google Photos and rename files to include complete special suffix...")
            fix_truncations_output = fix_truncations(input_folder=input_folder, step_name=step_name, log_level=LOG_LEVEL)

            # Clean input dict
            self.result['fix_truncations'].clear()
            # Assign all pairs key-value from output_counters to counter['output_counters'] dict
            self.result['fix_truncations'].update(fix_truncations_output)

            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Fixing Truncated Files finished!")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"{step_name}Total Files files in Takeout folder              : {fix_truncations_output['total_files']}")
            LOGGER.info(f"{step_name}  - Total Fixed Files files in Takeout folder    : {total_mp4_files_fixed + fix_truncations_output['total_files_fixed']:<7}")
            LOGGER.info(f"{step_name}    - Total MP4 from live pictures Files fixed   : {total_mp4_files_fixed:<7}")
            LOGGER.info(f"{step_name}    - Total Truncated files fixed                : {fix_truncations_output['total_files_fixed']:<7}")
            LOGGER.info(f"{step_name}      - Total JSON files fixed                   : {fix_truncations_output['json_files_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Supplemental-metadata changes          : {fix_truncations_output['supplemental_metadata_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Extensions changes                     : {fix_truncations_output['extensions_fixed']:<7}")
            LOGGER.info(f"{step_name}      - Total Images/Videos files fixed          : {fix_truncations_output['non_json_files_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Special Suffixes changes               : {fix_truncations_output['special_suffixes_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Edited Suffixes changes                : {fix_truncations_output['edited_suffixes_fixed']:<7}")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Finally show TOTAL DURATION OF PRE-PROCESS PHASE
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            step_name = '🪛 [PRE-PROCESS] : '
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '-[TOTAL DURATION]', 'duration': formatted_duration})


    def process(self, output_folder=None, capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=True, log_level=None):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        process() function, but uses LOGGER and self.ARGS instead of global.
        """
        # Start the Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"🔢 TAKEOUT PROCESSING STARTED...")
            LOGGER.info(f"================================================================================================================================================")
            processing_start_time = datetime.now()

            if capture_output is None: capture_output=self.ARGS['show-gpth-info']
            if capture_errors is None: capture_errors=self.ARGS['show-gpth-errors']

            # STEP 1: Pre-check the object with skip_process=True to just unzip files in case they are zipped
            # ----------------------------------------------------------------------------------------------------------------------
            self.pre_checks(log_level=log_level)

            # Normalize input root for GPTH before any pre-process/analyze step.
            # This ensures extracted dates JSON paths match GPTH input paths.
            step_name = '🔧 [PRE-CHECKS]-[Normalize GPTH Input] : '
            self.normalize_input_root_for_gpth(step_name=step_name, log_level=log_level)


            # STEP 2: Pre-Process Takeout folder
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. PRE-PROCESSING TAKEOUT FOLDER...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if not self.ARGS['google-skip-preprocess']:
                # Call pre_process() with the same log_level as process()
                self.pre_process(log_level=log_level)
            else:
                step_name = '🪛 [PRE-PROCESS] : '
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # STEP 3: Analyze initial files in Takeout Folder before to process with GPTH and modify any original file
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            # Determine the input_folder depending on if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()
            step_name = '🔢 [PRE]-[Analyze Takeout] : '
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. ANALYZING INITIAL TAKEOUT FILES... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            self.analyze_folder(folder_to_analyze=input_folder, folder_type='input', step_name=step_name)
            # ----------------------------------------------------------------------------------------------------------------------


            # STEP 4: Process Input Takeout folder
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            self.substep = 0
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. PROCESS INPUT TAKEOUT FOLDER...")
            LOGGER.info(f"================================================================================================================================================")
            # --------------------------------------------------------------------------------------------------------------------------------------------------------
            # DETERMINE BASIC FOLDERS AND INIT SUPER CLASS
            # This need to be done after Pre-checks because if takeout folders have been unzipped, the input_folder, output_folder and albums_folder need to be updated
            # --------------------------------------------------------------------------------------------------------------------------------------------------------
            # If the user have passed an output_folder directly to the process() method, then update the object with this output_folder
            if output_folder:
                self.output_folder = output_folder
            # Determine the output_folder if it has not been given in the call to process() method
            # Determine the input_folder depending on if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()
            output_folder = self.get_output_folder()
            # Sub-Step 4.1: Capture person labels before GPTH removes JSON sidecars.
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '👥 [PROCESS]-[People Metadata Capture] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            step_start_time = datetime.now()
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. CAPTURING PEOPLE METADATA FROM GOOGLE TAKEOUT JSON SIDECARS...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if self.ARGS.get("google-process-people", True):
                LOGGER.info(f"{step_name}Capturing Google Takeout person labels before GPTH processing.")
                self.takeout_people_map = build_people_map(input_folder)
                unique_people = {
                    str(person).strip().casefold()
                    for entries in self.takeout_people_map.values()
                    for entry in (entries if isinstance(entries, list) else [entries])
                    if isinstance(entry, dict)
                    for person in entry.get("people", [])
                    if str(person).strip()
                }
                try:
                    Path(output_folder).mkdir(parents=True, exist_ok=True)
                    people_map_path = Path(output_folder) / PEOPLE_MAP_FILENAME
                    people_map_path.write_text(
                        json.dumps({"version": 2, "assets": self.takeout_people_map}, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    LOGGER.info(f"{step_name}Google Takeout people map saved: '{people_map_path}' ({len(self.takeout_people_map)} assets).")
                except Exception as error:
                    LOGGER.warning(f"{step_name}Unable to save Google Takeout people map before GPTH: {error}")
                LOGGER.info(f"{step_name}Detected {len(unique_people)} unique people labels.")
                LOGGER.info(f"{step_name}Captured person labels for {len(self.takeout_people_map)} assets; the map ({PEOPLE_MAP_FILENAME}) will be written during Final Cleaning in output folder.")
                formatted_duration = str(timedelta(seconds=round((datetime.now() - sub_step_start_time).total_seconds())))
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                self.takeout_people_map = None
                formatted_duration = "Skipped"
                LOGGER.info(f"{step_name}Step Skipped: people metadata capture disabled by --google-process-people=false.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})
            # Determine where the Albums will be located
            albums_folder = self.get_albums_folder()
            gpth_input_folder = input_folder
            gpth_filedates_json = self.initial_filedates_json

            # Sub-Step 4.2: Process photos with GPTH tool
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🧠 [PROCESS]-[Metadata Processing] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if not self.ARGS['google-skip-gpth-tool']:
                LOGGER.info(f"{step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")
                auto_fix_album_only_takeout = should_auto_force_gpth_fix(self.takeout_detection_info)
                if auto_fix_album_only_takeout and not self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(
                        f"{step_name}Google Takeout album-only structure detected (album folders with JSON sidecars and archive_browser.html, but no year folders). "
                        f"GPTH will be executed in fix mode automatically."
                    )
                    self.ARGS['google-ignore-check-structure'] = True

                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"{step_name}Ignore Google Takeout Structure flag detected ('-gics, --google-ignore-check-structure').")
                else:
                    if not self.needs_process:
                        LOGGER.warning(f"{step_name}No Takeout structure detected in input folder. The tool will process the folder ignoring Takeout structure.")
                        self.ARGS['google-ignore-check-structure'] = True
                        # Determine the output_folder again because when elf.ARGS['google-ignore-check-structure'] = True, the output_folder is different
                        output_folder = self.get_output_folder()
                if self.ARGS['google-ignore-check-structure']:
                    input_is_disposable_for_fix = bool(self.ARGS.get('google-input-zip-folder'))
                    if not input_is_disposable_for_fix and self.backup_takeout_folder:
                        try:
                            input_is_disposable_for_fix = (
                                os.path.abspath(str(self.backup_takeout_folder)) != os.path.abspath(str(input_folder))
                            )
                        except Exception:
                            input_is_disposable_for_fix = True
                    working_input_root, gpth_input_folder, gpth_filedates_json, cloned_from = prepare_gpth_fix_working_input(
                        input_folder=input_folder,
                        takeout_detection_info=self.takeout_detection_info,
                        keep_takeout_folder=self.ARGS['google-keep-takeout-folder'],
                        filedates_json=self.initial_filedates_json,
                        timestamp=self.TIMESTAMP,
                        input_is_disposable=input_is_disposable_for_fix,
                        step_name=step_name,
                        log_level=LOG_LEVEL,
                    )
                    if not working_input_root or not gpth_input_folder:
                        LOGGER.error(f"{step_name}Metadata fixing aborted because GPTH fix working input could not be prepared.")
                        return self.result
                    input_folder = working_input_root
                    self.input_folder = working_input_root
                    if self.unzipped_folder:
                        self.unzipped_folder = working_input_root
                    else:
                        self.takeout_folder = Path(working_input_root)
                    if cloned_from and not self.backup_takeout_folder:
                        self.backup_takeout_folder = cloned_from
                    LOGGER.info(f"{step_name}GPTH fix mode will process in place the folder: '{gpth_input_folder}'")

                # Now Call GPTH Tool
                ok = fix_metadata_with_gpth_tool(
                    input_folder=gpth_input_folder,
                    output_folder=output_folder,
                    capture_output=capture_output,
                    capture_errors=capture_errors,
                    print_messages=print_messages,
                    no_symbolic_albums=self.ARGS['google-no-symbolic-albums'],
                    skip_extras=self.ARGS['google-skip-extras-files'],
                    keep_takeout_folder=self.ARGS['google-keep-takeout-folder'],
                    ignore_takeout_structure=self.ARGS['google-ignore-check-structure'],
                    filedates_json=gpth_filedates_json,
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                if not ok:
                    LOGGER.warning(f"{step_name}Metadata fixing didn't finish properly due to GPTH error.")
                    LOGGER.warning(f"{step_name}If your Takeout does not contain Year/Month folder structure, you can use '-gics, --google-ignore-check-structure' flag.")
                    return self.result

                # [OPTIONAL] [Enabled by Default] - Fix Broken Symbolic Links
                # ----------------------------------------------------------------------------------------------------------------------
                if not self.ARGS['google-no-symbolic-albums']:
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Fixing broken symbolic links. This step is needed after Metadata processing with GPTH...")
                    self.result['symlink_fixed'], self.result['symlink_not_fixed'] = fix_symlinks_broken(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
                    LOGGER.info(f"{step_name}Fixed symbolic links after Metadata processing with GPTH")

                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
                self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 4.3: [OPTIONAL] [Disabled by Default] - Copy/Move files to output folder manually
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '📁 [PROCESS]-[Copy/Move] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. COPYING/MOVING FILES TO OUTPUT FOLDER...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            # Determine if manual copy/move is needed (for step 4)
            manual_copy_move_needed = (
                self.ARGS['google-skip-gpth-tool']
            ) and input_folder != output_folder
            if manual_copy_move_needed:
                if self.ARGS['google-skip-gpth-tool']:
                    LOGGER.warning(f"{step_name}Metadata fixing with GPTH tool skipped ('-gSkipGpth, --google-skip-gpth-tool' flag). step {self.step}.{self.substep} is needed to copy files manually to output folder.")
                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"{step_name}Flag to Ignore Google Takeout Structure detected. step {self.step}.{self.substep} is needed to copy/move files manually to output folder.")
                if not self.ARGS['google-keep-takeout-folder']:
                    LOGGER.info(f"{step_name}Moving files from Takeout folder to Output folder...")
                else:
                    LOGGER.info(f"{step_name}Copying files from Takeout folder to Output folder...")
                copy_move_folder(input_folder, output_folder, ignore_patterns=['*.json', '*.j'], move=not self.ARGS['google-keep-takeout-folder'], step_name=step_name, log_level=LOG_LEVEL)
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[') + 1: step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 4.4: Recover orphan album assets from JSON-only source entries
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🧩 [PROCESS]-[Recover Orphan Album Assets] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. RECOVERING ORPHAN ALBUM ASSETS FROM SOURCE JSON SIDECARS...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if should_recover_orphan_album_assets(self.takeout_detection_info):
                recovery_summary = recover_orphan_album_assets_from_json_sidecars(
                    input_folder=input_folder,
                    output_folder=output_folder,
                    albums_folder=albums_folder,
                    no_symbolic_albums=self.ARGS['google-no-symbolic-albums'],
                    albums_structure=self.ARGS['google-albums-folders-structure'],
                    step_name=step_name,
                    log_level=LOG_LEVEL,
                )
                self.result['orphan_album_json_detected'] = recovery_summary['orphan_json_detected']
                self.result['orphan_album_assets_recovered'] = recovery_summary['recovered_assets']
                self.result['orphan_album_assets_unresolved'] = recovery_summary['unresolved_assets']
                self.result['orphan_album_recovery_albums_touched'] = recovery_summary['albums_touched']
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = "Skipped"
                LOGGER.info(f"{step_name}Step Skipped: orphan album JSON recovery only applies to Takeouts with year folders.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Finally show TOTAL DURATION OF PROCESSING PHASE
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            step_name = '🧠 [PROCESS] : '
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '-[TOTAL DURATION]', 'duration': formatted_duration})


            # STEP 5: Analyze final files in Output Folder after processed with GPTH
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            # Determine the input_folder depending on if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()
            step_name = '🔢 [POST]-[Analyze Output] : '
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. ANALYZING OUTPUT FILES... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            # Call analyze_folder to invoke FolderAnalyzer class with the selected folder_to_analyze
            self.analyze_folder(folder_to_analyze=output_folder, folder_type='output', step_name=step_name, save_json=False)
            # ----------------------------------------------------------------------------------------------------------------------


            # STEP 6: Post Process Output folder
            # ----------------------------------------------------------------------------------------------------------------------
            # Increment self.step for the Post Process Steps
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. POST-PROCESSING OUTPUT FOLDER...")
            LOGGER.info(f"================================================================================================================================================")
            if not self.ARGS['google-skip-postprocess']:
                # Now call the post_process() function
                self.post_process(input_folder=input_folder, output_folder=output_folder, albums_folder=albums_folder, log_level=log_level)
            else:
                LOGGER.info(f"")
                step_name = '✅ [POST-PROCESS] : '
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # STEP 7: Final Steps
            # ----------------------------------------------------------------------------------------------------------------------
            # Increment self.step for the Post Process Steps
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}. FINAL STEPS...")
            LOGGER.info(f"================================================================================================================================================")
            self.final_steps(input_folder=input_folder, output_folder=output_folder)


            # FINISH & PRINT RESULTS
            # ----------------------------------------------------------------------------------------------------------------------
            processing_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((processing_end_time - processing_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"✅ TAKEOUT PROCESSING FINISHED!!!")
            LOGGER.info(f"")
            LOGGER.info(f"{'Takeout Precessed Folder'.ljust(55)}  : '{output_folder}'.")
            LOGGER.info(f"")
            LOGGER.info(f"Processing Time per Step:")
            LOGGER.info(f"-" * 67)
            for entry in self.steps_duration:
                label_cleaned = ' '.join(entry['step_name'].replace(' : ', '').split()).replace(' ]', ']')
                # If it is a principal Step, add new line
                if '.' not in str(entry['step_id']):
                    LOGGER.info("")
                    step_id_and_label = f"{('STEP ' + str(entry['step_id'])).ljust(9)} : {label_cleaned}"
                else:
                    step_id_and_label = f"{('Step ' + str(entry['step_id'])).ljust(9)} : {label_cleaned}"

                LOGGER.info(f"{step_id_and_label.ljust(55)} : {entry['duration'].rjust(8)}")
            LOGGER.info(f"")
            LOGGER.info(f"{'TOTAL PROCESSING TIME'.ljust(55)}  : {formatted_duration.rjust(8)}")
            LOGGER.info(f"================================================================================================================================================")

            # PRINT RESULTS
            # ----------------------------------------------------------------------------------------------------------------------
            result = self.result
            if LOG_LEVEL == logging.VERBOSE:
                LOGGER.verbose (f"Process Output:")
                print_dict_pretty(result, log_level=logging.VERBOSE)

            # Extract percentages of totals
            output_perc_photos_with_date = result['output_counters']['photos']['pct_with_date']
            output_perc_photos_without_date = result['output_counters']['photos']['pct_without_date']
            output_perc_videos_with_date = result['output_counters']['videos']['pct_with_date']
            output_perc_videos_without_date = result['output_counters']['videos']['pct_without_date']

            # Calculate percentages from output vs input
            perc_of_input_total_files               = 100 * result['output_counters']['total_files']           / result['input_counters']['total_files']             if result['input_counters']['total_files']           != 0 else 100
            perc_of_input_total_unsupported_files   = 100 * result['output_counters']['unsupported_files']     / result['input_counters']['unsupported_files']       if result['input_counters']['unsupported_files']     != 0 else 100
            perc_of_input_total_supported_files     = 100 * result['output_counters']['supported_files']       / result['input_counters']['supported_files']         if result['input_counters']['supported_files']       != 0 else 100
            perc_of_input_total_media               = 100 * result['output_counters']['media_files']           / result['input_counters']['media_files']             if result['input_counters']['media_files']           != 0 else 100
            perc_of_input_total_images              = 100 * result['output_counters']['photo_files']           / result['input_counters']['photo_files']             if result['input_counters']['photo_files']           != 0 else 100
            perc_of_input_total_photos_with_date    = 100 * result['output_counters']['photos']['with_date']   / result['input_counters']['photos']['with_date']     if result['input_counters']['photos']['with_date']   != 0 else 100
            perc_of_input_total_photos_without_date = 100 * result['output_counters']['photos']['without_date']/ result['input_counters']['photos']['without_date']  if result['input_counters']['photos']['without_date']!= 0 else 100
            perc_of_input_total_videos              = 100 * result['output_counters']['video_files']           / result['input_counters']['video_files']             if result['input_counters']['video_files']           != 0 else 100
            perc_of_input_total_videos_with_date    = 100 * result['output_counters']['videos']['with_date']   / result['input_counters']['videos']['with_date']     if result['input_counters']['videos']['with_date']   != 0 else 100
            perc_of_input_total_videos_without_date = 100 * result['output_counters']['videos']['without_date']/ result['input_counters']['videos']['without_date']  if result['input_counters']['videos']['without_date']!= 0 else 100
            perc_of_input_total_non_media           = 100 * result['output_counters']['non_media_files']       / result['input_counters']['non_media_files']         if result['input_counters']['non_media_files']       != 0 else 100
            perc_of_input_total_metadata            = 100 * result['output_counters']['metadata_files']        / result['input_counters']['metadata_files']          if result['input_counters']['metadata_files']        != 0 else 100
            perc_of_input_total_sidecars            = 100 * result['output_counters']['sidecar_files']         / result['input_counters']['sidecar_files']           if result['input_counters']['sidecar_files']         != 0 else 100

            # Calculate differences from output vs input
            diff_output_input_total_files               = result['output_counters']['total_files']           - result['input_counters']['total_files']
            diff_output_input_total_unsupported_files   = result['output_counters']['unsupported_files']     - result['input_counters']['unsupported_files']
            diff_output_input_total_supported_files     = result['output_counters']['supported_files']       - result['input_counters']['supported_files']
            diff_output_input_total_media               = result['output_counters']['media_files']           - result['input_counters']['media_files']
            diff_output_input_total_images              = result['output_counters']['photo_files']           - result['input_counters']['photo_files']
            diff_output_input_total_photos_with_date    = result['output_counters']['photos']['with_date']   - result['input_counters']['photos']['with_date']
            diff_output_input_total_photos_without_date = result['output_counters']['photos']['without_date']- result['input_counters']['photos']['without_date']
            diff_output_input_total_videos              = result['output_counters']['video_files']           - result['input_counters']['video_files']
            diff_output_input_total_videos_with_date    = result['output_counters']['videos']['with_date']   - result['input_counters']['videos']['with_date']
            diff_output_input_total_videos_without_date = result['output_counters']['videos']['without_date']- result['input_counters']['videos']['without_date']
            diff_output_input_total_non_media           = result['output_counters']['non_media_files']       - result['input_counters']['non_media_files']
            diff_output_input_total_metadata            = result['output_counters']['metadata_files']        - result['input_counters']['metadata_files']
            diff_output_input_total_sidecars            = result['output_counters']['sidecar_files']         - result['input_counters']['sidecar_files']

            end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
            if result['output_counters']['total_files'] == 0:
                # FINAL SUMMARY
                LOGGER.info(f"")
                LOGGER.error(f"================================================================================================================================================")
                LOGGER.error(f"❌ PROCESS COMPLETED WITH ERRORS!           ")
                LOGGER.error(f"================================================================================================================================================")
                LOGGER.info(f"")
                LOGGER.error(f"No files found in Output Folder  : '{output_folder}'")
                LOGGER.info(f"")
                LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
                LOGGER.info(f"================================================================================================================================================")
                LOGGER.info(f"")
            else:
                # FINAL SUMMARY
                LOGGER.info(f"")
                LOGGER.info(f"================================================================================================================================================")
                LOGGER.info(f"✅ PROCESS COMPLETED SUCCESSFULLY!")
                LOGGER.info(f"")
                LOGGER.info(f"Processed Takeout have been saved to folder : '{output_folder}'")
                if self.ARGS.get('google-keep-takeout-folder'):
                    LOGGER.info(f"Original Takeout is safely preserved in     : '{self.backup_takeout_folder}' ")
                else:
                    LOGGER.info(f"")

                LOGGER.info(f"")
                LOGGER.info(f"📊 FINAL SUMMARY & STATISTICS:")
                # ---------------------- Column widths ----------------------
                COL1_WIDTH = 44  # Description
                COL2_WIDTH = 7   # Counters
                COL3_WIDTH = 38  # "(Physical: xxxx | Symlinks: yyyyyy)"
                COL4_WIDTH = 18  # diff
                COL5_WIDTH = 20  # % of input
                TOTAL_WIDTH = COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH + COL5_WIDTH + 2

                # ---------------------- Helpers & digit widths ----------------------
                def _safe_get(d, *keys, default=0):
                    cur = d
                    for k in keys:
                        if not isinstance(cur, dict) or k not in cur:
                            return default
                        cur = cur[k]
                    return cur

                inp = result.get('input_counters', {})
                out = result.get('output_counters', {})

                pairs = []
                pairs.append((_safe_get(inp, 'total_files'), _safe_get(inp, 'total_symlinks')))
                pairs.append((_safe_get(inp, 'unsupported_files'), 0))
                pairs.append((_safe_get(inp, 'supported_files'), _safe_get(inp, 'supported_symlinks')))
                pairs.append((_safe_get(inp, 'non_media_files'), 0))
                pairs.append((_safe_get(inp, 'metadata_files'), 0))
                pairs.append((_safe_get(inp, 'sidecar_files'), 0))
                pairs.append((_safe_get(inp, 'media_files'), _safe_get(inp, 'media_symlinks')))
                pairs.append((_safe_get(inp, 'photo_files'), _safe_get(inp, 'photo_symlinks')))
                pairs.append((_safe_get(inp, 'video_files'), _safe_get(inp, 'video_symlinks')))
                pairs.append((_safe_get(out, 'total_files'), _safe_get(out, 'total_symlinks')))
                pairs.append((_safe_get(out, 'unsupported_files'), 0))
                pairs.append((_safe_get(out, 'supported_files'), _safe_get(out, 'supported_symlinks')))
                pairs.append((_safe_get(out, 'non_media_files'), 0))
                pairs.append((_safe_get(out, 'metadata_files'), 0))
                pairs.append((_safe_get(out, 'sidecar_files'), 0))
                pairs.append((_safe_get(out, 'media_files'), _safe_get(out, 'media_symlinks')))
                pairs.append((_safe_get(out, 'photo_files'), _safe_get(out, 'photo_symlinks')))
                pairs.append((_safe_get(out, 'video_files'), _safe_get(out, 'video_symlinks')))

                phys_vals = [max(0, (t or 0) - (s or 0)) for (t, s) in pairs]
                sym_vals  = [s or 0 for (_, s) in pairs]
                PHYS_DIGITS = max(6, *(len(str(v)) for v in phys_vals))
                SYMLINK_DIGITS = max(6, *(len(str(v)) for v in sym_vals))

                def fmt_phys_syml(total, syms):
                    # single-line formatter "(Physical: ### | Symlinks: ######)"
                    phys = max(0, (total or 0) - (syms or 0))
                    return f"(Physical: {phys:>{PHYS_DIGITS}} | Symlinks: {syms:>{SYMLINK_DIGITS}})"

                PCT_DIGITS = max(
                    3,
                    len(str(int(_safe_get(inp, 'photos', 'pct_with_date', default=0)))),
                    len(str(int(_safe_get(inp, 'photos', 'pct_without_date', default=0)))),
                    len(str(int(_safe_get(inp, 'videos', 'pct_with_date', default=0)))),
                    len(str(int(_safe_get(inp, 'videos', 'pct_without_date', default=0)))),
                    len(str(int(_safe_get(out, 'photos', 'pct_with_date', default=0)))),
                    len(str(int(_safe_get(out, 'photos', 'pct_without_date', default=0)))),
                    len(str(int(_safe_get(out, 'videos', 'pct_with_date', default=0)))),
                    len(str(int(_safe_get(out, 'videos', 'pct_without_date', default=0))))
                ) + 2

                # ---------------------- INPUT SUMMARY ----------------------
                folder = 'Takeout folder'
                sub_dict = 'input_counters'
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"{'Total Size of ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['total_size_mb']/1024:>{COL2_WIDTH}.2f} (GB)")
                LOGGER.info(f"{'Total Files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['total_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['total_files'], result[sub_dict]['total_symlinks']):<{COL3_WIDTH}}")
                LOGGER.info(f"{'Total Non-Supported files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['unsupported_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['unsupported_files'], 0):<{COL3_WIDTH}}")
                LOGGER.info(f"{'Total Supported files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['supported_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['supported_files'], result[sub_dict]['supported_symlinks']):<{COL3_WIDTH}}")
                LOGGER.info(f"{'  - Total Non-Media files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['non_media_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['non_media_files'], 0):<{COL3_WIDTH}}")
                LOGGER.info(f"{'    - Total Metadata in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['metadata_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['metadata_files'], 0):<{COL3_WIDTH}}")
                LOGGER.info(f"{'    - Total Sidecars in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['sidecar_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['sidecar_files'], 0):<{COL3_WIDTH}}")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"{'  - Total Media files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['media_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['media_files'], result[sub_dict]['media_symlinks']):<{COL3_WIDTH}}")
                LOGGER.info(f"{'    - Total Photos in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['photo_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['photo_files'], result[sub_dict]['photo_symlinks']):<{COL3_WIDTH}}")
                LOGGER.info(f"{'      - With Date':<{COL1_WIDTH}}: {result[sub_dict]['photos']['with_date']:>{COL2_WIDTH}} ({result[sub_dict]['photos']['pct_with_date']:>{PCT_DIGITS}.1f}%)")
                LOGGER.info(f"{'      - Without Date':<{COL1_WIDTH}}: {result[sub_dict]['photos']['without_date']:>{COL2_WIDTH}} ({result[sub_dict]['photos']['pct_without_date']:>{PCT_DIGITS}.1f}%)")
                LOGGER.info(f"{'    - Total Videos in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['video_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['video_files'], result[sub_dict]['video_symlinks']):<{COL3_WIDTH}}")
                LOGGER.info(f"{'      - With Date':<{COL1_WIDTH}}: {result[sub_dict]['videos']['with_date']:>{COL2_WIDTH}} ({result[sub_dict]['videos']['pct_with_date']:>{PCT_DIGITS}.1f}%)")
                LOGGER.info(f"{'      - Without Date':<{COL1_WIDTH}}: {result[sub_dict]['videos']['without_date']:>{COL2_WIDTH}} ({result[sub_dict]['videos']['pct_without_date']:>{PCT_DIGITS}.1f}%)")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")

                # ---------------------- OUTPUT SUMMARY (with diffs) ----------------------
                folder = 'Output folder'
                sub_dict = 'output_counters'
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"{'Total Size of ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['total_size_mb']/1024:>{COL2_WIDTH}.2f} (GB)")
                LOGGER.info(f"{'Total Files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['total_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['total_files'], result[sub_dict]['total_symlinks']):<{COL3_WIDTH}}| (diff: {diff_output_input_total_files:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_files:>5.1f}% of input)")
                LOGGER.info(f"{'Total Non-Supported files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['unsupported_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['unsupported_files'], 0):<{COL3_WIDTH}}| (diff: {diff_output_input_total_unsupported_files:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_unsupported_files:>5.1f}% of input)")
                LOGGER.info(f"{'Total Supported files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['supported_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['supported_files'], result[sub_dict]['supported_symlinks']):<{COL3_WIDTH}}| (diff: {diff_output_input_total_supported_files:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_supported_files:>5.1f}% of input)")
                LOGGER.info(f"{'  - Total Non-Media files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['non_media_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['non_media_files'], 0):<{COL3_WIDTH}}| (diff: {diff_output_input_total_non_media:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_non_media:>5.1f}% of input)")
                LOGGER.info(f"{'    - Total Metadata in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['metadata_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['metadata_files'], 0):<{COL3_WIDTH}}| (diff: {diff_output_input_total_metadata:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_metadata:>5.1f}% of input)")
                LOGGER.info(f"{'    - Total Sidecars in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['sidecar_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['sidecar_files'], 0):<{COL3_WIDTH}}| (diff: {diff_output_input_total_sidecars:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_sidecars:>5.1f}% of input)")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"{'  - Total Media files in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['media_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['media_files'], result[sub_dict]['media_symlinks']):<{COL3_WIDTH}}| (diff: {diff_output_input_total_media:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_media:>5.1f}% of input)")
                LOGGER.info(f"{'    - Total Photos in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['photo_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['photo_files'], result[sub_dict]['photo_symlinks']):<{COL3_WIDTH}}| (diff: {diff_output_input_total_images:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_images:>5.1f}% of input)")
                LOGGER.info(f"{'      - With Date':<{COL1_WIDTH}}: {result[sub_dict]['photos']['with_date']:>{COL2_WIDTH}} ({output_perc_photos_with_date:>{PCT_DIGITS}.1f}%)".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH) + f"   | (diff: {diff_output_input_total_photos_with_date:>7})".ljust(COL4_WIDTH) + f" | ({perc_of_input_total_photos_with_date:>5.1f}% of input)")
                LOGGER.info(f"{'      - Without Date':<{COL1_WIDTH}}: {result[sub_dict]['photos']['without_date']:>{COL2_WIDTH}} ({output_perc_photos_without_date:>{PCT_DIGITS}.1f}%)".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH) + f"   | (diff: {diff_output_input_total_photos_without_date:>7})".ljust(COL4_WIDTH) + f" | ({perc_of_input_total_photos_without_date:>5.1f}% of input)")
                LOGGER.info(f"{'    - Total Videos in ' + folder:<{COL1_WIDTH}}: {result[sub_dict]['video_files']:>{COL2_WIDTH}} {fmt_phys_syml(result[sub_dict]['video_files'], result[sub_dict]['video_symlinks']):<{COL3_WIDTH}}| (diff: {diff_output_input_total_videos:>7})".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH + COL4_WIDTH) + f" | ({perc_of_input_total_videos:>5.1f}% of input)")
                LOGGER.info(f"{'      - With Date':<{COL1_WIDTH}}: {result[sub_dict]['videos']['with_date']:>{COL2_WIDTH}} ({output_perc_videos_with_date:>{PCT_DIGITS}.1f}%)".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH) + f"   | (diff: {diff_output_input_total_videos_with_date:>7})".ljust(COL4_WIDTH) + f" | ({perc_of_input_total_videos_with_date:>5.1f}% of input)")
                LOGGER.info(f"{'      - Without Date':<{COL1_WIDTH}}: {result[sub_dict]['videos']['without_date']:>{COL2_WIDTH}} ({output_perc_videos_without_date:>{PCT_DIGITS}.1f}%)".ljust(COL1_WIDTH + COL2_WIDTH + COL3_WIDTH) + f"   | (diff: {diff_output_input_total_videos_without_date:>7})".ljust(COL4_WIDTH) + f" | ({perc_of_input_total_videos_without_date:>5.1f}% of input)")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")

                LOGGER.info(f"")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"Total Albums folders found in Output folder : {result['valid_albums_found']}")
                if result.get('orphan_album_json_detected', 0) or result.get('orphan_album_assets_recovered', 0) or result.get('orphan_album_assets_unresolved', 0):
                    LOGGER.info(f"Orphan Album JSON Sidecars Detected         : {result.get('orphan_album_json_detected', 0)}")
                    LOGGER.info(f"Orphan Album Assets Recovered               : {result.get('orphan_album_assets_recovered', 0)}")
                    LOGGER.info(f"Orphan Album Assets Unresolved              : {result.get('orphan_album_assets_unresolved', 0)}")
                if ARGS['google-rename-albums-folders']:
                    LOGGER.info(f"Total Albums Renamed                        : {result['renamed_album_folders']}")
                    LOGGER.info(f"Total Albums Duplicated                     : {result['duplicates_album_folders']}")
                    LOGGER.info(f"   - Total Albums Fully Merged              : {result['duplicates_albums_fully_merged']}")
                    LOGGER.info(f"   - Total Albums Not Fully Merged          : {result['duplicates_albums_not_fully_merged']}")
                if not ARGS['google-no-symbolic-albums']:
                    LOGGER.info(f"")
                    LOGGER.info(f"Total Symlinks Fixed                        : {result['symlink_fixed']}")
                    LOGGER.info(f"Total Symlinks Not Fixed                    : {result['symlink_not_fixed']}")
                if ARGS['google-remove-duplicates-files']:
                    LOGGER.info(f"")
                    LOGGER.info(f"Total Duplicates Removed                    : {result['duplicates_found']}")
                    LOGGER.info(f"Total Empty Folders Removed                 : {result['removed_empty_folders']}")
                LOGGER.info(f"")
                LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
                LOGGER.info(f"{'-' * TOTAL_WIDTH}")
                LOGGER.info(f"================================================================================================================================================")
                LOGGER.info(f"")

            # At the end of the process, we call the super() to make this objet a sub-instance of the class ClassLocalFolder to create the same folder structure
            if create_localfolder_object:
                super().__init__(output_folder)

            return self.result


    def post_process(self, input_folder=None, output_folder=None, albums_folder=None, log_level=None):
        # Start the Post Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            # --------------------------------------------- POST PROCESS -----------------------------------------------------------
            # Initialize Step timer
            step_start_time = datetime.now()

            # Initialize self.substep counter for the Post Process Steps
            self.substep = 0

            # Step 4.1: Sync .MP4 live pictures timestamp
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🕒 [POST-PROCESS]-[MP4 Timestamp Synch] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
            sync_mp4_timestamps_with_images(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Step 4.2: Normalize conflicting video XMP dates left by GPTH
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🎞️ [POST-PROCESS]-[Repair Video XMP Dates]   : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. NORMALIZING CONFLICTING VIDEO XMP DATES...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            repair_conflicting_video_xmp_dates(
                folder_analyzer=self.output_folder_analyzer,
                step_name=step_name,
                log_level=LOG_LEVEL,
            )
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Step 4.2.1: [OPTIONAL] [Enabled by Default] - Move albums
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '📚 [POST-PROCESS]-[Albums Moving] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. MOVING ALBUMS FOLDER...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")

            if Version(GPTH_VERSION) >= Version("4.3.0"):
                albums_input_folder = os.path.join(output_folder, FOLDERNAME_ALBUMS)
            else:
                albums_input_folder = output_folder

            need_to_move_albums = os.path.abspath(albums_input_folder) != os.path.abspath(os.path.join(output_folder, FOLDERNAME_ALBUMS))

            if not self.ARGS['google-skip-move-albums'] and need_to_move_albums:
                LOGGER.info(f"{step_name}Moving All your albums into '{FOLDERNAME_ALBUMS}' subfolder for a better organization...")

                replacements1 = move_albums(input_folder=albums_input_folder, albums_subfolder=FOLDERNAME_ALBUMS, exclude_subfolder=[FOLDERNAME_NO_ALBUMS, '@eaDir'], step_name=step_name, log_level=LOG_LEVEL)
                # Now modify the object analyzer with all the files changed during this step
                self.output_folder_analyzer.update_folders_bulk(replacements=replacements1, step_name=step_name)
                # Finally Move Albums to Albums root folder
                albums_path = os.path.join(output_folder, f"{FOLDERNAME_ALBUMS}")
                replacements2 = move_albums_to_root(albums_root=albums_path, step_name=step_name, log_level=log_level)
                self.output_folder_analyzer.update_folders_bulk(replacements=replacements2, step_name=step_name)
                LOGGER.info(f"{step_name}All your albums have been moved successfully!")
                # Step 4.2.2: [OPTIONAL] [Enabled by Default] - Fix Broken Symbolic Links
                # ----------------------------------------------------------------------------------------------------------------------
                if not self.ARGS['google-no-symbolic-albums']:
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                    self.result['symlink_fixed'], self.result['symlink_not_fixed'] = fix_symlinks_broken(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
                    LOGGER.info(f"{step_name}Fixed symbolic links after moving Albums folders!")
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Step 4.3: [OPTIONAL] [Enabled by Default] - Create Folders Year/Month or Year only structure
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '📁 [POST-PROCESS]-[Create year/month struct] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
            LOGGER.info(f"================================================================================================================================================")
            albums_structure = self.ARGS['google-albums-folders-structure'].lower()
            no_albums_structure = self.ARGS['google-no-albums-folders-structure'].lower()
            if albums_structure != 'flatten' or no_albums_structure != 'flatten' or (albums_structure == 'flatten' and no_albums_structure == 'flatten'):
                # For Albums
                if albums_structure != 'flatten':
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Creating Folder structure '{albums_structure}' for each Album folder...")
                    if self.ARGS['google-skip-move-albums']:
                        basedir = output_folder
                    else:
                        basedir = os.path.join(output_folder, FOLDERNAME_ALBUMS)

                    exclude_subfolders = [FOLDERNAME_NO_ALBUMS]
                    # replacements = profile_and_print(organize_files_by_date, input_folder=basedir, type=albums_structure, exclude_subfolders=exclude_subfolders, folder_analyzer=self.output_folder_analyzer, step_name=step_name, log_level=LOG_LEVEL)
                    replacements = organize_files_by_date(input_folder=basedir, type=albums_structure, exclude_subfolders=exclude_subfolders, folder_analyzer=self.output_folder_analyzer, step_name=step_name, log_level=LOG_LEVEL)
                    # Now modify the object analyzer with all the files changed during this step
                    self.output_folder_analyzer.apply_replacements(replacements=replacements, step_name=step_name)
                # For No-Albums
                if no_albums_structure != 'flatten':
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Creating Folder structure '{no_albums_structure}' for '{FOLDERNAME_NO_ALBUMS}' folder...")
                    basedir = os.path.join(output_folder, FOLDERNAME_NO_ALBUMS)

                    exclude_subfolders = []
                    # replacements = profile_and_print(organize_files_by_date, input_folder=basedir, type=no_albums_structure, exclude_subfolders=exclude_subfolders, folder_analyzer=self.output_folder_analyzer, step_name=step_name, log_level=LOG_LEVEL)
                    replacements = organize_files_by_date(input_folder=basedir, type=no_albums_structure, exclude_subfolders=exclude_subfolders, folder_analyzer=self.output_folder_analyzer, step_name=step_name, log_level=LOG_LEVEL)
                    # Now modify the object analyzer with all the files changed during this step
                    self.output_folder_analyzer.apply_replacements(replacements=replacements, step_name=step_name)
                # If flatten
                if albums_structure == 'flatten' and no_albums_structure == 'flatten':
                    LOGGER.info(f"")
                    LOGGER.warning(f"{step_name}No argument '-gafs, --google-albums-folders-structure' and '-gnas, --google-no-albums-folders-structure' detected. All photos and videos will be flattened in their folders.")

                if albums_structure != 'flatten' or no_albums_structure != 'flatten':
                    # Step 4.6.2: [OPTIONAL] [Enabled by Default] - Fix Broken Symbolic Links
                    # ----------------------------------------------------------------------------------------------------------------------
                    if not self.ARGS['google-no-symbolic-albums']:
                        LOGGER.info(f"")
                        LOGGER.info(f"{step_name}Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                        self.result['symlink_fixed'], self.result['symlink_not_fixed'] = fix_symlinks_broken(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
                        LOGGER.info(f"{step_name}Fixed symbolic links after Created Year/Month structure in output folders!!")

                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Step 4.4.1: [OPTIONAL] [Disabled by Default] - Rename Albums Folders based on content date
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '📝 [POST-PROCESS]-[Albums Renaming] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. RENAMING ALBUMS FOLDERS BASED ON THEIR DATES...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if self.ARGS['google-rename-albums-folders']:
                LOGGER.info(f"{step_name}Renaming albums folders in <OUTPUT_TAKEOUT_FOLDER> based on their dates...")
                rename_output = rename_album_folders(input_folder=albums_folder, exclude_subfolder=[FOLDERNAME_NO_ALBUMS, '@eaDir'], date_dict=self.output_folder_analyzer.extracted_dates, step_name=step_name, log_level=LOG_LEVEL)
                # Extrae la lista de tuplas (old_path, new_path)
                replacements = rename_output['replacements']
                # Now modify the object analyzer with all the files changed during this step
                self.output_folder_analyzer.update_folders_bulk(replacements=replacements, step_name=step_name)
                # Merge all counts from rename_output into self.result in one go
                self.result.update(rename_output)
                # Step 4.4.2: [OPTIONAL] [Enabled by Default] - Fix Broken Symbolic Links
                # ----------------------------------------------------------------------------------------------------------------------
                if not self.ARGS['google-no-symbolic-albums']:
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                    self.result['symlink_fixed'], self.result['symlink_not_fixed'] = fix_symlinks_broken(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
                    LOGGER.info(f"{step_name}Fixed symbolic links after moving Albums renaming!")
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Step 4.5: [OPTIONAL] [Disabled by Default] - Remove Duplicates
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '👥 [POST-PROCESS]-[Remove Duplicates] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. REMOVING DUPLICATES IN <OUTPUT_TAKEOUT_FOLDER>...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            if self.ARGS['google-remove-duplicates-files']:
                # 1) Remove Duplicates from OUTPUT_TAKEOUT_FOLDER (excluding '<NO_ALBUMS_FOLDER>' folder)
                LOGGER.info(f"{step_name}1. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>', excluding '<NO_ALBUMS_FOLDER>' folder...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=output_folder,
                    exclusion_folders=[FOLDERNAME_NO_ALBUMS],    # Exclude '<NO_ALBUMS_FOLDER>' folder since it will contain duplicates of all the assets within 'Albums' subfolders.
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                self.result['duplicates_found'] += duplicates_found
                self.result['removed_empty_folders'] += removed_empty_folders

                # 2) Remove Duplicates from <OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER> (excluding any other folder outside it).
                LOGGER.info(f"{step_name}2. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER>', excluding any other folders outside it...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=os.path.join(output_folder, FOLDERNAME_NO_ALBUMS),
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                self.result['duplicates_found'] += duplicates_found
                self.result['removed_empty_folders'] += removed_empty_folders
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            else:
                formatted_duration = f"Skipped"
                LOGGER.info(f"{step_name}Step Skipped: '{step_name[step_name.rfind('[')+1 : step_name.rfind(']')].strip()}'")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Step 4.6: Count Albums
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🔢 [POST-PROCESS]-[Count Albums] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. COUNTING ALBUMS... ")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            # Count the Albums in output Folder
            if os.path.isdir(albums_folder):
                excluded_folders = [FOLDERNAME_NO_ALBUMS, "ALL_PHOTOS"]
                # self.result['valid_albums_found'] = count_valid_albums(albums_folder, excluded_folders=excluded_folders, step_name=step_name, log_level=LOG_LEVEL)
                self.result['valid_albums_found'] = count_valid_albums_in_first_level(albums_folder, excluded_folders=excluded_folders, step_name=step_name, log_level=LOG_LEVEL)
            LOGGER.info(f"{step_name}Valid Albums Found {self.result['valid_albums_found']}.")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Step 4.8: Remove Empty Folders
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🧹 [POST-PROCESS]-[Remove Empty Folders] : '
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            sub_step_start_time = datetime.now()
            self.substep += 1
            LOGGER.info(f"")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"{self.step}.{self.substep}. REMOVING EMPTY FOLDERS...")
            LOGGER.info(f"================================================================================================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Removing empty folders in <OUTPUT_TAKEOUT_FOLDER>...")
            remove_empty_dirs(input_folder=output_folder, log_level=LOG_LEVEL)
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Finally show TOTAL DURATION OF POST-PROCESS PHASE
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            step_name = '✅ [POST-PROCESS] : '
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '-[TOTAL DURATION]', 'duration': formatted_duration})


    def final_steps(self, input_folder=None, output_folder=None):
        # ---------------------------------------------- FINAL STEPS ------------------------------------------------------------
        # Initialize Step timer
        step_start_time = datetime.now()

        # Initialize self.substep counter for the Post Process Steps
        self.substep = 0

        # Step 5.1: FINAL CLEANING
        # ----------------------------------------------------------------------------------------------------------------------
        step_name = '🧹 [FINAL-STEPS]-[Final Cleaning] : '
        step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
        sub_step_start_time = datetime.now()
        self.substep += 1
        LOGGER.info(f"")
        LOGGER.info(f"================================================================================================================================================")
        LOGGER.info(f"{self.step}.{self.substep}. FINAL CLEANING... ")
        LOGGER.info(f"================================================================================================================================================")
        LOGGER.info(f"")
        # Persist the map captured before GPTH after all output-folder processing finishes.
        if self.ARGS.get("google-process-people", True):
            try:
                people_map_path = Path(output_folder) / PEOPLE_MAP_FILENAME
                people_map_path.write_text(
                    json.dumps({"version": 2, "assets": getattr(self, "takeout_people_map", {}) or {}}, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                LOGGER.info(f"{step_name}Google Takeout people map saved: '{people_map_path}' ({len(getattr(self, 'takeout_people_map', {}) or {})} assets).")
            except Exception as error:
                LOGGER.warning(f"{step_name}Unable to save Google Takeout people map: {error}")
        else:
            LOGGER.info(f"{step_name}Google Takeout people processing disabled; no people map was generated.")
        # Save the final output_dates_metadata.json
        self.final_filedates_json = self.output_folder_analyzer.save_to_json(f"takeout_output_dates_metadata_final.json", step_name=step_name)
        # Removes completely the input_folder because all the files (except JSON) have been already moved to output folder
        removed = force_remove_directory_faster(folder=input_folder, step_name=step_name, log_level=logging.ERROR)
        if removed:
            LOGGER.info(f"{step_name}The folder '{input_folder}' have been successfully deleted.")
        else:
            LOGGER.info(f"{step_name}Nothing to Clean. The folder '{input_folder}' have been already deleted by a previous step.")
        sub_step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
        self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


        # Step 5.2: SHOW FILES WITHOUT DATES
        # ----------------------------------------------------------------------------------------------------------------------
        step_name = '❔ [FINAL-STEPS]-[Files without dates] : '
        step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
        sub_step_start_time = datetime.now()
        self.substep += 1
        LOGGER.info(f"")
        LOGGER.info(f"================================================================================================================================================")
        LOGGER.info(f"{self.step}.{self.substep}. FILES WITHOUT DATES... ")
        LOGGER.info(f"================================================================================================================================================")
        LOGGER.info(f"")
        # Now, after Post-Processing (if have been executed), show the files without dates
        self.output_folder_analyzer.show_files_without_dates(relative_folder=output_folder, step_name=step_name)
        sub_step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
        self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

        # Finally show TOTAL DURATION OF FINAL-STEPS PHASE
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
        step_name = '🏁 [FINAL-STEPS] : '
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
        # Índice self.substep posiciones antes del final
        idx = len(self.steps_duration) - self.substep
        if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
        # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
        self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '-[TOTAL DURATION]', 'duration': formatted_duration})

##############################################################################
#                                END OF CLASS                                #
##############################################################################


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-CHECKS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def unpack_zips(input_folder, unzip_folder, step_name="", log_level=None):
    """ Unzips all ZIP files from a folder into another """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if not os.path.exists(input_folder):
            LOGGER.error(f"{step_name}ZIP folder '{input_folder}' does not exist.")
            return
        os.makedirs(unzip_folder, exist_ok=True)
        for zip_file in os.listdir(input_folder):
            if zip_file.endswith(".zip"):
                zip_path = os.path.join(input_folder, zip_file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        LOGGER.info(f"{step_name}Unzipping: {zip_file}")
                        zip_ref.extractall(unzip_folder)
                except zipfile.BadZipFile:
                    LOGGER.error(f"{step_name}Could not unzip file: {zip_file}")



def contains_takeout_structure(input_folder, step_name="", log_level=None):
    result = inspect_takeout_structure(input_folder=input_folder, step_name=step_name, log_level=log_level)
    return bool(result.get("is_takeout"))


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sanitize_names(input_folder, dry_run=False, step_name="", log_level=None):
    """
    Sanitize file and directory names to be SMB/Windows-friendly while keeping visible characters (including accents).
    Operations performed (in this order), component-wise (never across directories):
      1) Unicode normalization to NFC (no visual loss; 'a' + acute -> 'á').
      2) Strip trailing spaces and dots (Windows/SMB-incompatible).
      3) Replace control chars and SMB-reserved chars [: * ? " < > |] with '_'.
      4) Avoid reserved DOS names for files/dirs (CON, PRN, AUX, NUL, COM1..COM9, LPT1..LPT9) by prefixing '_'.
      5) Resolve collisions safely by appending ' (n)' before the extension (or at end for directories).
      6) Case-only renames handled via a temporary hop name to satisfy case-insensitive filesystems.
    Notes:
      - Does not create or delete folders; only renames entries in-place.
      - Processes directories depth-first (post-order) to avoid breaking traversal.
      - Returns counters with detailed stats.
    Args:
      input_folder: Root path to sanitize recursively.
      dry_run: If True, only logs intended changes (no rename on disk).
      step_name: Prefix to prepend to all log lines.
      log_level: Log level context to apply within set_log_level.
    Returns:
      dict with counters:
        - total_entries_scanned
        - dirs_renamed
        - files_renamed
        - collisions_resolved
        - nfc_normalized
        - trailing_fixed
        - illegal_chars_replaced
        - reserved_names_fixed
        - errors
    """
    # ------------------------------- helpers (pure functions) --------------------------------
    # Precompile patterns and constants once
    control_re = re.compile(r'[\x00-\x1F\x7F]')
    illegal_re = re.compile(r'[:*?"<>|]')  # SMB/Windows disallowed
    trailing_re = re.compile(r'[ .]+$')    # trailing spaces/dots
    reserved_names = {
        'CON','PRN','AUX','NUL',
        *(f'COM{i}' for i in range(1,10)),
        *(f'LPT{i}' for i in range(1,10)),
    }

    def nfc(s):
        # Normalize to NFC (no character loss; only composes combining sequences)
        return unicodedata.normalize('NFC', s)

    def split_name_ext(name, is_dir):
        # For files: separate base and extension; for dirs: ext is ''
        if is_dir:
            return name, ''
        base, ext = os.path.splitext(name)
        return base, ext

    def join_name_ext(base, ext):
        return f"{base}{ext}"

    def sanitize_component(name, is_dir):
        """Return (clean_name, flags_dict) for a single path component."""
        flags = {'nfc': False, 'trailing': False, 'illegal': False, 'reserved': False}

        original = name
        # 1) Unicode NFC
        s = nfc(name)
        if s != name:
            flags['nfc'] = True
        name = s

        # 2) Strip trailing spaces/dots
        s = trailing_re.sub('', name)
        if s != name:
            flags['trailing'] = True
        name = s

        # 3) Replace control and illegal chars
        s = control_re.sub('_', name)
        s = illegal_re.sub('_', s)
        if s != name:
            flags['illegal'] = True
        name = s

        # 4) Reserved DOS names (case-insensitive)
        test = name.upper()
        if test in reserved_names or (not is_dir and split_name_ext(name, False)[0].upper() in reserved_names):
            name = f"_{name}"
            flags['reserved'] = True

        return name, flags

    def unique_target_path(dir_path, target_name, is_dir):
        """Generate a collision-free path by appending ' (n)'. Preserve file extension."""
        base, ext = split_name_ext(target_name, is_dir)
        candidate = target_name
        n = 1
        while (dir_path / candidate).exists():
            n += 1
            candidate = join_name_ext(f"{base} ({n})", ext)
        return candidate, (n > 1)

    def safe_rename(src_path, dst_path):
        """Perform a safe rename, handling case-only changes via a temp hop."""
        if str(src_path) == str(dst_path):
            return True
        # Case-only rename on case-insensitive FS needs a temp hop
        same_dir = src_path.parent == dst_path.parent
        hop_ok = True
        try:
            if same_dir and src_path.name.lower() == dst_path.name.lower() and src_path.name != dst_path.name:
                temp_name = f".__rename_tmp__{os.getpid()}__"
                temp_path = src_path.parent / temp_name
                os.replace(src_path, temp_path)
                os.replace(temp_path, dst_path)
            else:
                os.replace(src_path, dst_path)
            return True
        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ Rename failed: {src_path} → {dst_path} | {e}")
            return False
    # -----------------------------------------------------------------------------------------

    counters = {
        'total_entries_scanned': 0,
        'dirs_renamed': 0,
        'files_renamed': 0,
        'collisions_resolved': 0,
        'nfc_normalized': 0,
        'trailing_fixed': 0,
        'illegal_chars_replaced': 0,
        'reserved_names_fixed': 0,
        'errors': 0,
    }

    with set_log_level(LOGGER, log_level):
        root = Path(input_folder)
        if not root.exists():
            LOGGER.warning(f"{step_name}❌ Folder does not exist: {input_folder}")
            counters['errors'] += 1
            return counters

        # -------------------- 1) Directories first (post-order) --------------------
        # Walk once to collect all directories with depth, then rename deepest first
        dir_entries = []
        for current_root, dirnames, _ in os.walk(root, topdown=True, followlinks=False):
            base_depth = Path(current_root).relative_to(root).parts
            for d in dirnames:
                p = Path(current_root) / d
                depth = len(Path(current_root).relative_to(root).parts) + 1
                dir_entries.append((depth, p))

        # Process deeper directories first
        for _, dir_path in sorted(dir_entries, key=lambda t: t[0], reverse=True):
            counters['total_entries_scanned'] += 1
            parent = dir_path.parent
            clean_name, flags = sanitize_component(dir_path.name, is_dir=True)
            if clean_name == dir_path.name:
                continue  # nothing to do

            target_name, collided = unique_target_path(parent, clean_name, is_dir=True)
            dst_path = parent / target_name

            if collided:
                counters['collisions_resolved'] += 1

            LOGGER.debug(f"{step_name}DIR  : {dir_path.name} → {target_name}")
            if not dry_run:
                ok = safe_rename(dir_path, dst_path)
                if not ok:
                    counters['errors'] += 1
                    continue
            counters['dirs_renamed'] += 1
            counters['nfc_normalized'] += int(flags['nfc'])
            counters['trailing_fixed'] += int(flags['trailing'])
            counters['illegal_chars_replaced'] += int(flags['illegal'])
            counters['reserved_names_fixed'] += int(flags['reserved'])

        # -------------------- 2) Files inside all directories --------------------
        for current_root, _, filenames in os.walk(root, topdown=True, followlinks=False):
            for fname in filenames:
                counters['total_entries_scanned'] += 1
                file_path = Path(current_root) / fname
                parent = file_path.parent

                clean_name, flags = sanitize_component(fname, is_dir=False)
                if clean_name == fname:
                    continue  # nothing to do

                target_name, collided = unique_target_path(parent, clean_name, is_dir=False)
                dst_path = parent / target_name

                if collided:
                    counters['collisions_resolved'] += 1

                LOGGER.debug(f"{step_name}FILE : {fname} → {target_name}")
                if not dry_run:
                    try:
                        ok = safe_rename(file_path, dst_path)
                        if not ok:
                            counters['errors'] += 1
                            continue
                    except Exception as e:
                        counters['errors'] += 1
                        LOGGER.warning(f"{step_name}⚠️ Rename failed: {file_path} → {dst_path} | {e}")
                        continue

                counters['files_renamed'] += 1
                counters['nfc_normalized'] += int(flags['nfc'])
                counters['trailing_fixed'] += int(flags['trailing'])
                counters['illegal_chars_replaced'] += int(flags['illegal'])
                counters['reserved_names_fixed'] += int(flags['reserved'])

        LOGGER.debug(f"{step_name}Sanitize completed. Dirs: {counters['dirs_renamed']}, Files: {counters['files_renamed']}, Collisions: {counters['collisions_resolved']}, Errors: {counters['errors']}")
        return counters

def fix_mp4_files(input_folder, step_name="", log_level=None):
    """
    Busca archivos .MP4/.MOV/.AVI sin su JSON correspondiente. Si existe un archivo .HEIC/.JPG/.JPEG
    con el mismo nombre base y sí tiene JSON (posiblemente truncado con .supplemental-metadata),
    copia ese JSON renombrándolo con el nombre del vídeo, completando el sufijo si es necesario.

    Args:
        input_folder: Carpeta raíz donde buscar.
        step_name: Prefijo de mensajes de log.
        log_level: Nivel de log.
    """
    with set_log_level(LOGGER, log_level):
        counter_mp4_files_changed = 0
        video_exts = ['.mp4', '.mov', '.avi']
        image_exts = ['.heic', '.jpg', '.jpeg']
        supplemental = SUPPLEMENTAL_METADATA  # ya definido globalmente como 'supplemental-metadata'
        disable_tqdm = log_level < logging.WARNING

        all_video_files = []
        for _, _, files in os.walk(input_folder):
            all_video_files += [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

        if not all_video_files:
            return 0

        with tqdm(total=len(all_video_files), smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Fixing video JSONs", unit=" files", disable=disable_tqdm) as pbar:
            for root, _, files in os.walk(input_folder):
                file_set = set(files)

                video_files = [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

                for video_file in video_files:
                    pbar.update(1)
                    base_name, ext = os.path.splitext(video_file)
                    target_json = f"{video_file}.json"

                    if target_json in file_set:
                        continue

                    # Buscar posibles imágenes con el mismo nombre base
                    matched_candidate = None
                    for image_ext in image_exts:
                        candidate_base = f"{base_name}{image_ext}"

                        # Buscar json exacto o con posible truncación del supplemental
                        for f in files:
                            if not f.lower().endswith('.json'):
                                continue

                            json_base = f[:-5]  # sin el .json
                            if not json_base.lower().startswith(candidate_base.lower()):
                                continue

                            # ¿Tiene .supplemental-metadata (truncado o completo)?
                            suffix = json_base[len(candidate_base):]
                            if suffix == '':
                                matched_candidate = f
                                break
                            elif supplemental.startswith(suffix.lstrip('.')):
                                matched_candidate = f
                                break

                        if matched_candidate:
                            break  # no seguir buscando si ya tenemos uno

                    if matched_candidate:
                        src_path = os.path.join(root, matched_candidate)
                        dst_path = os.path.join(root, target_json)
                        shutil.copy(src_path, dst_path)
                        LOGGER.debug(f"{step_name}Copied: {matched_candidate} → {target_json}")
                        counter_mp4_files_changed += 1

        return counter_mp4_files_changed


def fix_truncations(input_folder, step_name="", log_level=logging.INFO, name_length_threshold=46):
    """
    Recursively traverses `input_folder` and fixes:
      1) .json files with a truncated '.supplemental-metadata' suffix.
      2) .json files whose original extension is truncated (e.g. .jp.json → .jpg.json),
         by finding the real asset file in the same directory.
      3) Non-.json files with truncated special suffixes (based on SPECIAL_SUFFIXES).
      4) Non-.json files with truncated edited suffixes in multiple languages (based on EDITTED).

    Only processes files whose base name (without extension) exceeds `name_length_threshold` characters.

    Args:
        input_folder (str): Path to the root folder to scan.
        step_name (str): Prefix for log messages (e.g. "DEBUG   : ").
        log_level (int): Logging level for this operation.
        name_length_threshold (int): Minimum length of the base filename (sans extension) to consider.

    Returns:
        dict: Counters of changes made, with keys:
          - total_files: total number of files found
          - total_files_fixed: number of files that were renamed at least once
          - json_files_fixed: number of .json files modified
          - non_json_files_fixed: number of non-.json files modified
          - supplemental_metadata_fixed: count of '.supplemental-metadata' fixes
          - extensions_fixed: count of JSON extension corrections
          - special_suffixes_fixed: count of special-suffix completions
          - edited_suffixes_fixed: count of edited-suffix completions
    """
    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def repl(m):
        tail = m.group(0)[len(sub):-len(ext)]
        return suf + tail + ext

    # Build a combined regex for ANY truncated prefix of any special or edited suffix
    def make_variant_pattern(suffix_list):
        variants = set(suffix_list)
        for s in suffix_list:
            for i in range(2, len(s)):
                variants.add(s[:i])
        # sort longest first so regex matches the largest truncation before smaller ones
        return '|'.join(sorted(map(re.escape, variants), key=len, reverse=True))
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------

    # Pre-count all files for reporting
    total_files = sum(len(files) for _, _, files in os.walk(input_folder))
    variants_specials_pattern = make_variant_pattern(SPECIAL_SUFFIXES)
    variants_editted_pattern = make_variant_pattern(EDITTED_SUFFIXES)
    optional_counter = r'(?:\(\d+\))?'  # allow "(n)" counters
    counters = {
        "total_files": total_files,
        "total_files_fixed": 0,
        "json_files_fixed": 0,
        "non_json_files_fixed": 0,
        "supplemental_metadata_fixed": 0,
        "extensions_fixed": 0,
        "special_suffixes_fixed": 0,
        "edited_suffixes_fixed": 0,
    }
    with set_log_level(LOGGER, log_level):
        # --------------------------
        # --- Case A: JSON files ---
        # --------------------------
        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + SUPPLEMENTAL_METADATA
        # Calculate max allowed truncation length (excluding the initial '.su')
        MAX_TRUNC = len(SUPPLEMENTAL_METADATA_WITH_DOT) - len('.su')
        # Compile pattern to capture truncated stub and optional counter like '(1)'
        pattern = re.compile(
            rf'(?P<base>.*?)(?P<stub>\.su[\w-]{{0,{MAX_TRUNC}}})(?P<counter>\(\d+\))?$',
            re.IGNORECASE
        )

        # Walk through all subdirectories to process only JSON files
        for root, _, files in os.walk(input_folder):
            files_set = set(files)  # for matching JSON sidecars
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() == '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # A.1) Fix truncated '.supplemental-metadata' suffix
                    match = pattern.match(name)
                    if match and '.su' in name.lower():  # quick sanity check before applying the pattern
                        base = match.group('base')
                        counter = match.group('counter') or ''  # preserve any '(n)' counter
                        new_name = f"{base}{SUPPLEMENTAL_METADATA_WITH_DOT}{counter}{ext}"
                        new_path = Path(root) / new_name
                        if str(old_path).lower() != str(new_path).lower():
                            os.rename(old_path, new_path)
                            LOGGER.verbose(f"{step_name}Fixed JSON Supplemental Ext: {file} → {new_name}")
                            counters["supplemental_metadata_fixed"] += 1
                            # We need to medify file and old_path for next steps
                            file = new_name
                            old_path = new_path
                            name, ext = os.path.splitext(file)  # Refresh name and ext
                            files_set = set(os.listdir(root))   # Refresh to include any renamed files
                            if not file_modified:
                                counters["json_files_fixed"] += 1
                                counters["total_files_fixed"] += 1
                                file_modified = True
                    # end A.1

                    # A.2) Fix truncated original extension by locating the real asset file
                    parts = name.split('.')
                    if len(parts) >= 2:
                        # determine base_name and raw truncated ext (with possible "(n)")
                        if len(parts) == 2:
                            base_name, raw_trunc = parts
                        else:
                            base_name = '.'.join(parts[:-2])
                            raw_trunc = parts[-2]

                        # strip counter from raw_trunc, but save it
                        m_cnt = re.match(r'^(?P<ext>.*?)(\((?P<num>\d+)\))?$', raw_trunc)
                        trunc_ext = m_cnt.group('ext')
                        counter = f"({m_cnt.group('num')})" if m_cnt.group('num') else ''

                        # look for a matching asset: stem starts with base_name, ext starts with trunc_ext
                        full_ext = None
                        for cand in files_set:
                            if cand.lower().endswith('.json'):
                                continue
                            cand_stem = Path(cand).stem
                            if not cand_stem.lower().startswith(base_name.lower()):
                                continue
                            ext_cand = Path(cand).suffix.lstrip('.')
                            if ext_cand.lower().startswith(trunc_ext.lower()):
                                full_ext = Path(cand).suffix  # e.g. ".JPG"
                                break # Once a candidate has matched, skipp looping other candidates

                        if full_ext:
                            # replace the first ".trunc_ext" in the JSON name with the full_ext, leaving any "(n)" counter at the end untouched, then append ".json"
                            new_core = name.replace(f'.{trunc_ext}', full_ext, 1)
                            if counter and new_core.endswith(counter):
                                # If the counter is already present in `name`, don't re-append it
                                new_name = f"{new_core}{ext}"
                            else:
                                # re-attach the counter just before the ".json"
                                new_name = f"{new_core}{counter}{ext}"
                            new_path = Path(root) / new_name
                            if not new_path.exists() and str(old_path).lower() != str(new_path).lower():
                                os.rename(old_path, new_path)
                                LOGGER.verbose(f"{step_name}Fixed JSON Origin File Ext : {file} → {new_name}")
                                counters["extensions_fixed"] += 1
                                if not file_modified:
                                    counters["json_files_fixed"] += 1
                                    counters["total_files_fixed"] += 1
                                    file_modified = True
                    # end A.2

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed JSON File  : {original_file} → {new_name}")

        # ------------------------------------------------------------
        # --- Case B: Non-JSON files (special suffixes or editted) ---
        # ------------------------------------------------------------
        # Walk through all subdirectories to process only Non-JSON files
        for root, _, files in os.walk(input_folder):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # B.1) Fix Special Suffixes: '-effects', '-smile', '-mix', 'collage'
                    for suf in SPECIAL_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}(?=(-|_|\.|{variants_editted_pattern}|{SUPPLEMENTAL_METADATA})?(?:\(\d+\))?{re.escape(ext)}$)",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                match = pattern.search(file)
                                if match:
                                    start = match.start()
                                    end = match.end()
                                    tail = file[end:]  # everything after the matched truncation
                                    new_name = file[:start] + suf + tail
                                    new_path = Path(root) / new_name
                                    if str(old_path).lower() != str(new_path).lower():
                                        os.rename(old_path, new_path)
                                        LOGGER.verbose(f"{step_name}Fixed ORIGIN Special Suffix: {file} → {new_name}")
                                        counters["special_suffixes_fixed"] += 1
                                        # We need to modify file and old_path for next steps and to keep changes if other suffixes are found
                                        file = new_name
                                        old_path = new_path
                                        if not file_modified:
                                            counters["non_json_files_fixed"] += 1
                                            counters["total_files_fixed"] += 1
                                            file_modified = True
                                    break # Once one truncation of the current suf is applied, stop trying shorter ones

                    # B.2) Fix Edited Suffixes (multi-language): '-edited', '-edytowane', '-bearbeitet', '-bewerkt', '-編集済み', '-modificato', '-modifié', '-ha editado', '-editat'
                    for suf in EDITTED_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}"
                                rf"(?:(?:{variants_editted_pattern}){optional_counter})*"
                                rf"{optional_counter}"
                                rf"{re.escape(ext)}$",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                new_name = pattern.sub(repl, file)
                                new_path = Path(root) / new_name
                                if str(old_path).lower() != str(new_path).lower():
                                    os.rename(old_path, new_path)
                                    LOGGER.verbose(f"{step_name}Fixed ORIGIN Edited Suffix : {file} → {new_name}")
                                    counters["edited_suffixes_fixed"] += 1
                                    # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                    file = new_name
                                    old_path = new_path
                                    if not file_modified:
                                        counters["non_json_files_fixed"] += 1
                                        counters["total_files_fixed"] += 1
                                        file_modified = True
                                break # Once one truncation of the current suf is applied, stop trying shorter ones

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed MEDIA File : {original_file} → {new_name}")
    return counters


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def run_command(command, capture_output=False, capture_errors=True, print_messages=True, step_name=""):
    """
    Ejecuta un comando. Muestra en consola actualizaciones de progreso sin loguearlas.
    Loguea solo líneas distintas a las de progreso. Corrige pegado de líneas en consola.
    """
    buffered_createfile_failures = []
    warning_keywords = [
        "WARNING",
        "ExifTool command failed with exit code",
        "Error output",
    ]

    def emit_line(line, is_error=False):
        if print_messages:
            if is_error:
                custom_print(f"{step_name}{line}", log_level=logging.ERROR)
            else:
                if "VERBOSE" in line:
                    custom_print(f"{step_name}{line}", log_level=logging.VERBOSE)
                elif "DEBUG" in line:
                    custom_print(f"{step_name}{line}", log_level=logging.DEBUG)
                elif "WARNING" in line or any(kw in line for kw in warning_keywords):
                    custom_print(f"{step_name}{line}", log_level=logging.WARNING)
                elif "ERROR" in line:
                    custom_print(f"{step_name}{line}", log_level=logging.ERROR)
                else:
                    custom_print(f"{step_name}{line}", log_level=logging.INFO)

        if is_error:
            LOGGER.error(f"{step_name}{line}")
        else:
            if "ERROR" in line:
                LOGGER.error(f"{step_name}{line}")
            elif "WARNING" in line:
                LOGGER.warning(f"{step_name}{line}")
            elif "DEBUG" in line:
                LOGGER.debug(f"{step_name}{line}")
            elif "VERBOSE" in line:
                LOGGER.verbose(f"{step_name}{line}")
            elif any(kw in line for kw in warning_keywords):
                LOGGER.warning(f"{step_name}{line}")
            else:
                LOGGER.info(f"{step_name}{line}")

    def emit_dashboard_progress(line):
        payload = f"{TQDM_DASHBOARD_PREFIX}{line}"
        for handler in getattr(LOGGER, "handlers", []) or []:
            if not getattr(handler, "accept_tqdm", False):
                continue
            try:
                record = logging.LogRecord(
                    name=getattr(LOGGER, "name", "PhotoMigrator"),
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=payload,
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)
            except Exception:
                continue

    def emit_progress_console_line(line, final=False):
        if not print_messages:
            return
        custom_print(f"\r{step_name}{line}", end="", flush=True, log_level=logging.INFO)
        if final:
            print()

    def flush_createfile_failed_warnings():
        if not buffered_createfile_failures:
            return

        if len(buffered_createfile_failures) == 1:
            emit_line(buffered_createfile_failures[0]["line"], is_error=False)
            return

        first = buffered_createfile_failures[0]
        error_codes = ", ".join(sorted({entry["error"] for entry in buffered_createfile_failures}))
        summary = (
            f'[WARNING] Collapsed {len(buffered_createfile_failures)} repeated GPTH "CreateFile failed" warnings '
            f'during the Windows creation-time update step (error codes: {error_codes}). '
            f'First example: "{first["path"]}".'
        )
        emit_line(summary, is_error=False)

    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def handle_stream(stream, is_error=False):
        init(autoreset=True)

        # progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)$')                            # Patron que solo detecta barras que terminen en contadores 11/100 etc...
        # progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)(?:\s+\d+(\.\d+)?%)?\s*$')     # Patron que detecta barras que terminen en contadores 11/100 etc.. aunque vengan porcentajes detrás (1063/1063 100.0%)
        progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)\b.*$')                        # Patron que detecta barras que terminen en contadores 11/100 aunque vengan más cosas detrás como porcentajes o ETAS

        last_was_progress = False
        printed_final = set()

        def iter_stream_frames(input_stream):
            buffer = []
            while True:
                char = input_stream.read(1)
                if char == "":
                    break
                if char in ("\r", "\n"):
                    if buffer:
                        yield "".join(buffer)
                        buffer = []
                    continue
                buffer.append(char)
            if buffer:
                yield "".join(buffer)

        for raw in iter_stream_frames(stream):

            # Limpiar ANSI y espacios finales
            ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', raw).rstrip()
            if not line.strip():
                if last_was_progress and print_messages:
                    print()
                last_was_progress = False
                continue

            createfile_failed = None if is_error else _parse_createfile_failed_warning(line)
            if createfile_failed:
                buffered_createfile_failures.append(createfile_failed)
                continue

            # Prefijo para agrupar barras
            common_part = line.split(' : ')[0] if ' : ' in line else line

            # 1) ¿Es barra de progreso?
            m = progress_re.search(line)
            if m:
                n, total = int(m.group(1)), int(m.group(2))

                # 1.a) Barra vacía (0/x)
                if n == 0:
                    if not print_messages:
                        emit_dashboard_progress(line)
                    if not print_messages:
                        # Log inicial
                        log_msg = f"{step_name}{line}"
                        if is_error:
                            LOGGER.error(log_msg)
                        else:
                            LOGGER.info(log_msg)
                    # nunca imprimo 0/x en pantalla
                    last_was_progress = True
                    continue

                # 1.b) Progreso intermedio (1 <= n < total)
                if n < total:
                    if print_messages:
                        emit_progress_console_line(line, final=False)
                    else:
                        emit_dashboard_progress(line)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    if not print_messages:
                        emit_dashboard_progress(line)
                    # impresión en pantalla
                    if print_messages:
                        emit_progress_console_line(line, final=True)
                    # log final
                    log_msg = f"{step_name}{line}"
                    if is_error:
                        LOGGER.error(log_msg)
                    else:
                        LOGGER.info(log_msg)

                    printed_final.add(common_part)

                last_was_progress = False
                continue

            # 2) Mensaje normal: si venía de progreso vivo, forzamos salto
            if last_was_progress and print_messages:
                print()
            last_was_progress = False

            # 3) Impresión/logging normal
            emit_line(line, is_error=is_error)

        # 5) Al cerrar stream, si quedó un progreso vivo, cerramos línea
        if last_was_progress and print_messages:
            print()
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------

    with suppress_console_output_temporarily(LOGGER):
        if not capture_output and not capture_errors:
            return subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace").returncode
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True, encoding = "utf-8", errors = "replace"
            )
            if capture_output:
                handle_stream(process.stdout, is_error=False)
            if capture_errors:
                handle_stream(process.stderr, is_error=True)

            process.wait()  # Esperar a que el proceso termine
            flush_createfile_failed_warnings()
            return process.returncode


def fix_metadata_with_gpth_tool(input_folder, output_folder, capture_output=False, capture_errors=True, print_messages=True, skip_extras=False, no_symbolic_albums=False, keep_takeout_folder=False, ignore_takeout_structure=False, filedates_json=None, step_name="", log_level=None):
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        """Runs the GPTH Tool command to process photos."""
        input_folder = os.path.abspath(input_folder)
        output_folder = os.path.abspath(output_folder)
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Running GPTH Tool...")
        LOGGER.info(f"{step_name}GPTH Version : '{GPTH_VERSION}'")
        LOGGER.info(f"{step_name}Input Folder : '{input_folder}'")
        LOGGER.info(f"{step_name}Output Folder: '{output_folder}'")

        # Detect the operating system
        current_os = get_os(step_name=step_name)
        current_arch = get_arch(step_name=step_name)

        # Determine the Tool name based on the OS
        tool_name = f"gpth-{GPTH_VERSION}-{current_os}-{current_arch}"
        if current_os in ("linux", "macos"):
            tool_name  +=".bin"
        elif current_os == "windows":
            tool_name += ".exe"
        else:
            LOGGER.error(f"{step_name}Invalid OS: {current_os}. Exiting...")
            sys.exit(-1)

        # Get gpth_tool_path
        gpth_tool_path = get_gpth_tool_path(base_path=FOLDERNAME_GPTH, exec_name=tool_name, step_name=step_name)
        LOGGER.info(f"{step_name}Using GPTH Tool file: '{gpth_tool_path}'...")

        # Check if the file exists
        if not os.path.exists(gpth_tool_path):
            LOGGER.error(f"{step_name}❌ GPTH was not found at: {gpth_tool_path}")
            return False
        else:
            LOGGER.info(f"{step_name}✅ GPTH found at: {gpth_tool_path}")

        # Ensure exec permissions for the binary file
        ensure_executable(gpth_tool_path)

        # Basic GPTH Command
        if ignore_takeout_structure:
            gpth_command = [gpth_tool_path, "--fix", input_folder, "--no-interactive"]
        else:
            gpth_command = [gpth_tool_path, "--input", input_folder, "--output", output_folder, "--no-interactive"]

        # Add verbosity depending on log-level
        if ARGS['log-level'].lower() in ['verbose']:
            gpth_command.append("--verbose")

        # By default, force --no-divide-to-dates and the Tool will create date structure if needed
        if Version(GPTH_VERSION) >= Version("3.6.0"):
            # The new version of GPTH have changed this argument:
            gpth_command.append("--divide-to-dates=0")  # 0: No divide, 1: year, 2: year/month, 3: year/month/day
        else:
            # For previous versions of the original GPTH tool
            gpth_command.append("--no-divide-to-dates")

        # Append --albums shortcut / duplicate-copy based on value of flag -sa, --symbolic-albums
        gpth_command.append("--albums")
        if no_symbolic_albums:
            gpth_command.append("duplicate-copy")
        else:
            LOGGER.info(f"{step_name}Symbolic Albums will be created with links to the original files...")
            gpth_command.append("shortcut")
            if current_os == "windows":
                LOGGER.info(f"{step_name}Windows GPTH shortcut mode will force --hardlink so album entries remain real filesystem links instead of .lnk shortcut files.")
                gpth_command.append("--hardlink")

        # Append --skip-extras to the gpth tool call based on the value of flag -se, --skip-extras
        if skip_extras:
            gpth_command.append("--skip-extras")

        # This feature have been removed in v4.0.9
        if Version(GPTH_VERSION) < Version("4.0.9"):
            # Append --copy/--no-copy to the gpth tool call based on the values of move_takeout_folder
            if keep_takeout_folder:
                gpth_command.append("--copy")
            else:
                gpth_command.append("--no-copy")

        if Version(GPTH_VERSION) >= Version("3.6.0"):
            # Use the new feature to Set creation time equal to the last modification date at the end of the program. (Only Windows supported)
            gpth_command.append("--update-creation-time")
            if Version(GPTH_VERSION) < Version("6.0.0"):
                # Use the new feature to Transform Pixel .MP or .MV extensions to ".mp4"
                gpth_command.append("--transform-pixel-mp")
            elif Version(GPTH_VERSION) >= Version("6.0.0"):
                # Use the new feature to Transform Pixel .MP or .MV motion photos into motion .jpg files
                gpth_command.append("--transform-pixel-mp jpg") # gpth 6.1.1 has a bug in --transform-pixel-mp flag. Disabling it until it is solved
                pass

        if Version(GPTH_VERSION) >= Version("4.0.0"):
            gpth_command.append("--write-exif")

        # From version 4.0.8 onwards a new flag --fix-extensions was added to fix those files whose extensions does not match with its mime type.
        elif Version(GPTH_VERSION) == Version("4.0.8"):
            gpth_command.append("--fix-extensions")

        # From version 4.0.9 the flag --fix-extensions needs a modifier
        if Version(GPTH_VERSION) >= Version("4.0.9"):
            gpth_command.append("--fix-extensions=standard")
            # gpth_command.append("--fix-extensions=conservative")
            # gpth_command.append("--fix-extensions=solo")
            # gpth_command.append("--fix-extensions=none")

        if Version(GPTH_VERSION) >= Version("4.1.0"):
            gpth_command.append("--guess-from-name")
            if not Version(GPTH_VERSION) == Version("4.2.0"):
                gpth_command.append("--divide-partner-shared")  # This flag was temporarilly removed in 4.2.0 but restored again in 4.2.1 and onwards

        # From version 4.3.0 onwards a new flag --fileDates has been introduced to provide a JSON file with a dictionary of Dates per file (this will speed-up GPTH date extraction a lot).
        if Version(GPTH_VERSION) >= Version("4.3.0") and Version(GPTH_VERSION) < Version("5.0.2"):
            if filedates_json and os.path.exists(filedates_json):
                gpth_command.extend(["--fileDates", filedates_json])

        # From version 5.0.2 onwards flag --fileDates has been renamed to --json-dates
        if Version(GPTH_VERSION) >= Version("5.0.2"):
            if filedates_json and os.path.exists(filedates_json):
                gpth_command.extend(["--json-dates", filedates_json])

        # From version 5.0.2 onwards flag --save-log have been added to save messages log into a file.
        if Version(GPTH_VERSION) >= Version("5.0.2") and ARGS['gpth-no-log']:
                gpth_command.extend(["--no-save-log"])

        try:
            command = ' '.join(gpth_command)
            LOGGER.info(f"{step_name}🪛 Fixing and 🧩 organizing all your Takeout photos and videos.")
            LOGGER.info(f"{step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂.")
            LOGGER.verbose(f"{step_name}Running GPTH with following command: {command}")
            print_arguments_pretty(gpth_command, title='GPTH Command', step_name=step_name, use_logger=True)

            # Run GPTH Tool
            ok = run_command(gpth_command, capture_output=capture_output, capture_errors=capture_errors, print_messages=print_messages, step_name=step_name)      # Shows the output in real time and capture it to the LOGGER.
            LOGGER.info(f"{step_name}GPTH Return Code: {ok}")

            # Check the result of GPTH process
            if ok == 0:
                if ignore_takeout_structure:
                    relocated = relocate_gpth_fix_outputs(
                        fix_root=input_folder,
                        output_folder=output_folder,
                        step_name=step_name,
                        log_level=log_level,
                    )
                    if not relocated:
                        LOGGER.error(f"{step_name}❌ GPTH fix completed but PhotoMigrator could not relocate the generated output folders.")
                        return False
                else:
                    preserve_archive_browser_artifacts(output_folder=output_folder, step_name=step_name, log_level=log_level)
                    relocated_special_folders = _relocate_misclassified_special_folders(
                        base_root=output_folder,
                        step_name=step_name,
                        log_level=log_level,
                    )
                    if relocated_special_folders is False:
                        LOGGER.error(
                            f"{step_name}❌ GPTH completed but PhotoMigrator could not relocate misclassified special folders from the normal output."
                        )
                        return False
                LOGGER.info(f"{step_name}✅ GPTH Tool fixing completed successfully.")
                return True
            else:
                LOGGER.error(f"{step_name}❌ GPTH Tool fixing failed with exit code {ok}.")
                return False
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"{step_name}❌ GPTH Tool fixing failed:\n{e.stderr}")
            return False


def fix_metadata_with_exif_tool(output_folder, step_name='', log_level=None):
    """Runs the EXIF Tool command to fix photo metadata."""
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Fixing EXIF metadata in '{output_folder}'...")
        # Detect the operating system
        current_os = platform.system()
        # Determine the Tool name based on the OS
        tool_name = ""
        if current_os == "Linux":
            tool_name = "exiftool"
        elif current_os == "Darwin":
            tool_name = "exiftool"
        elif current_os == "Windows":
            tool_name = "exiftool.exe"
        # Usar resolve_internal_path para acceder a archivos o directorios:
        # exif_tool_path = resolve_internal_path(os.path.join("exif_tool", tool_name))
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)

        # Ensure exec permissions for the binary file
        ensure_executable(exif_tool_path)

        exif_command = [
            exif_tool_path,
            "-overwrite_original",
            "-ExtractEmbedded",
            "-r",
            '-datetimeoriginal<filemodifydate',
            "-if", "(not $datetimeoriginal or ($datetimeoriginal eq '0000:00:00 00:00:00'))",
            output_folder
        ]
        try:
            print_arguments_pretty(exif_command, title='EXIFTOOL Command', step_name="", use_logger=True)
            result = subprocess.run(exif_command, check=False)
            LOGGER.info(f"EXIF Tool fixing completed successfully.")
        except subprocess.CalledProcessError as e:
            LOGGER.error(f"EXIF Tool fixing failed:\n{e.stderr}")

# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT POST-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sync_mp4_timestamps_with_images(input_folder, step_name="", log_level=None):
    """
    Look for .MP4 files with the same base name as any Live Picture file (.HEIC, .JPG, .JPEG)
    in the same folder. If found, set the date and time of the .MP4 file (or the symlink itself)
    to match the original Live Picture.
    """
    # Set logging level for this operation
    with set_log_level(LOGGER, log_level):
        # Count total files for progress bar
        total_files = sum(len(files) for _, _, files in os.walk(input_folder))
        with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'", unit=" files"
                  ) as pbar:
            # Walk through all directories and files
            for path, _, files in os.walk(input_folder):
                # Build a mapping from base filename to its extensions
                file_dict = {}
                for filename in files:
                    pbar.update(1)
                    name, ext = os.path.splitext(filename)
                    base_name = name.lower()
                    ext = ext.lower()
                    file_dict.setdefault(base_name, {})[ext] = filename
                # For each group of files sharing the same base name
                for base_name, ext_file_map in file_dict.items():
                    if '.mp4' not in ext_file_map:
                        continue
                    mp4_filename = ext_file_map['.mp4']
                    mp4_file_path = os.path.join(path, mp4_filename)
                    # Detect if the .mp4 is a symlink
                    is_mp4_link = os.path.islink(mp4_file_path)
                    # Look for a matching Live Picture image
                    image_exts = ['.heic', '.jpg', '.jpeg']
                    for image_ext in image_exts:
                        if image_ext not in ext_file_map:
                            continue
                        image_filename = ext_file_map[image_ext]
                        image_file_path = os.path.join(path, image_filename)
                        try:
                            # Get the image's atime and mtime
                            image_stats = os.stat(image_file_path)
                            atime, mtime = image_stats.st_atime, image_stats.st_mtime
                            if is_mp4_link:
                                # Apply timestamps to the symlink itself
                                os.utime(mp4_file_path, (atime, mtime), follow_symlinks=False)
                                LOGGER.debug(f"{step_name}Timestamps applied to symlink: {os.path.relpath(mp4_file_path, input_folder)}")
                            else:
                                # Apply timestamps to the regular .mp4 file
                                os.utime(mp4_file_path, (atime, mtime))
                                LOGGER.debug(f"{step_name}Timestamps applied to file: {os.path.relpath(mp4_file_path, input_folder)}")
                        except FileNotFoundError:
                            # Warn if either the .mp4 or the image file is missing
                            LOGGER.warning(f"{step_name}File not found. MP4: {mp4_file_path} | Image: {image_file_path}")
                        except Exception as e:
                            # Log any other errors encountered
                            LOGGER.error(f"{step_name}Error syncing {mp4_file_path}: {e}")
                        # Only sync with the first matching image
                        break


def force_remove_directory(folder, step_name='', log_level=None):
    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(folder):
            shutil.rmtree(folder, onerror=onerror)
            LOGGER.info(f"{step_name}The folder '{folder}' and all its content have been deleted.")
            return True
        else:
            LOGGER.info(f"{step_name}Cannot delete the folder '{folder}'.")
            return False


def force_remove_directory_faster(folder, step_name='', log_level=None):
    def onerror(func, path, exc_info):
        with suppress(Exception):
            os.chmod(path, stat.S_IWRITE)
            func(path)
    def delete_contents(path):
        for entry in os.scandir(path):
            try:
                full_path = entry.path
                if entry.is_dir(follow_symlinks=False):
                    delete_contents(full_path)
                    os.rmdir(full_path)
                else:
                    os.chmod(full_path, stat.S_IWRITE)
                    os.remove(full_path)
            except Exception:
                onerror(os.remove if entry.is_file() else os.rmdir, full_path, None)
    with set_log_level(LOGGER, log_level):
        if os.path.exists(folder):
            try:
                delete_contents(folder)
                os.rmdir(folder)
                LOGGER.info(f"{step_name}The folder '{folder}' and all its content have been deleted.")
                return True
            except Exception as e:
                LOGGER.warning(f"{step_name}Failed to delete folder '{folder}' completely: {e}")
                return False
        else:
            LOGGER.info(f"{step_name}The folder '{folder}' does not exist.")
            return False

def copy_move_folder(src, dst, ignore_patterns=None, move=False, step_name="", log_level=None):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param step_name:
    :param log_level:
    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def ignore_function(files, ignore_patterns):
        if ignore_patterns:
            # Convert to a list if a single pattern is provided
            patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
            ignored = []
            for pattern in patterns:
                ignored.extend(fnmatch.filter(files, pattern))
            return set(ignored)
        return set()
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Ignore function
        action = 'Moving' if move else 'Copying'
        try:
            if not is_valid_path(src):
                LOGGER.error(f"{step_name}The path '{src}' is not valid for the execution platform. Cannot copy/move folders from it.")
                return False
            if not is_valid_path(dst):
                LOGGER.error(f"{step_name}The path '{dst}' is not valid for the execution platform. Cannot copy/move folders to it.")
                return False

            # Ensure source != destination
            if src == dst:
                LOGGER.warning(f"{step_name}The source path '{src}' is the same as destination path '{dst}' Skipping copy/move folders to it...")
                return False

            # Ensure the source folder exists
            if not os.path.exists(src):
                raise FileNotFoundError(f"{step_name}Source folder does not exist: '{src}'")
            # Create the destination folder if it doesn't exist
            os.makedirs(dst, exist_ok=True)

            if move:
                # Contar el total de carpetas
                total_files = sum([len(files) for _, _, files in os.walk(src)])
                # Mostrar la barra de progreso basada en carpetas
                with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                    for path, dirs, files in os.walk(src, topdown=True):
                        pbar.update(1)
                        # Compute relative path
                        rel_path = os.path.relpath(path, src)
                        # Destination path
                        dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        # Apply ignore function to files and dirs
                        ignore = ignore_function(files + dirs, ignore_patterns=ignore_patterns)
                        # Filter dirs in-place to skip ignored directories
                        dirs[:] = [d for d in dirs if d not in ignore]
                        # Create destination directory
                        os.makedirs(dest_path, exist_ok=True)
                        # Move files
                        for file in files:
                            if file not in ignore:
                                src_file = os.path.join(path, file)
                                dst_file = os.path.join(dest_path, file)
                                shutil.move(src_file, dst_file)
                    print(f"")
                    LOGGER.info(f"{step_name}Folder moved successfully from {src} to {dst}")
            else:
                system = platform.system()
                try:
                    if system in ("Linux", "Darwin"):
                        LOGGER.info(f"{step_name}Trying fast copy with cp --reflink=auto...")
                        subprocess.run([
                            "cp", "-a", "--reflink=auto", os.path.join(src, "."), dst
                        ], check=True)
                        LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using cp --reflink.")
                        return True
                except Exception as e:
                    LOGGER.warning(f"{step_name}cp --reflink failed: {e}")

                try:
                    if system == "Windows":
                        LOGGER.info(f"{step_name}Trying fast copy with robocopy...")
                        result = subprocess.run([
                            "robocopy", src, dst, "/MIR", "/R:0", "/W:0", "/NFL", "/NDL", "/NJH", "/NJS"
                        ], capture_output=True, text=True)
                        if result.returncode <= 7:
                            LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using robocopy.")
                            return True
                        else:
                            raise Exception(f"robocopy error code {result.returncode}: {result.stderr}")
                    elif system in ("Linux", "Darwin"):
                        LOGGER.info(f"{step_name}Trying fast copy with rsync...")
                        subprocess.run([
                            "rsync", "-a", "--info=progress2", src + "/", dst
                        ], check=True)
                        LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using rsync.")
                        return True
                except Exception as e:
                    LOGGER.warning(f"{step_name}Fast copy methods failed: {e}, falling back to copytree.")

                # Copy the folder contents with fallback
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
                LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using shutil.copytree.")
                return True

        except Exception as e:
            LOGGER.error(f"{step_name}Error {action} folder: {e}")
            return False


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[], folder_analyzer: FolderAnalyzer = None, step_name="", log_level=None):
    """
    Organizes files into subfolders based on their EXIF date or, if unavailable, their modification date.

    The organization structure can be by year, by nested year/month folders, or by flat year-month folders.

    Args:
        input_folder (str or Path): The root directory containing the files to organize.
        type (str): The structure used to organize files. Must be one of:
            - 'year' → creates folders like '2024'
            - 'year/month' → creates nested folders like '2024/07'
            - 'year-month' → creates folders like '2024-07'
        exclude_subfolders (list): A list of folder names (not paths) to exclude from processing.
        folder_analyzer (FolderAnalyzer): Optional object FolderAnalyzer which contains method get_extracted_dates() to obtain the EXIF dates of all files within folder.
                           Used to avoid reprocessing EXIF metadata.
        update_json (str or Path): Path to a JSON file whose "source_file" entries will be updated with new paths.
        step_name (str): Optional prefix to include in all log messages for context tracking.
        log_level (int or None): Optional logging level to use during execution.

    Returns:
        list: A list of tuples (original_path, new_path) representing all moved files.

    Raises:
        ValueError: If `type` is not one of 'year', 'year/month', or 'year-month'.
    """

    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def get_date(file_path, extracted_dates, step_name):
        norm_path = Path(file_path).resolve().as_posix()

        # 1. Try to get OldestDate from extracted_dates if available
        date_entry = extracted_dates.get(norm_path) if extracted_dates else None
        if isinstance(date_entry, dict):
            oldest_date = date_entry.get("OldestDate")
            if isinstance(oldest_date, datetime):
                return oldest_date
            elif isinstance(oldest_date, str) and oldest_date.strip():
                try:
                    return parser.parse(oldest_date.strip())
                except Exception as e:
                    if LOGGER.isEnabledFor(logging.VERBOSE):
                        LOGGER.verbose(f"{step_name}❌ Error parsing OldestDate '{oldest_date}' for {norm_path}: {e}")

            # # If no OldestDate, try to use the minimum date among all EXIF tags found in the extracted_dates dictionary
            # all_dates = []
            # for k, v in date_entry.items():
            #     if k in ["OldestDate", "Source"] or not v:
            #         continue
            #     try:
            #         dt = v if isinstance(v, datetime) else parser.parse(str(v).strip())
            #         dt = normalize_datetime_utc(dt) # Converts datetime to datetime UTC aware if it is datetime naive
            #         all_dates.append(dt)
            #     except Exception:
            #         continue
            # if all_dates:
            #     return min(all_dates)

        # 2. Try to extract EXIF date directly if it's a photo
        ext = Path(file_path).suffix.lower()
        if ext in {".jpg", ".jpeg", ".tif", ".tiff"}:
            try:
                if LOGGER.isEnabledFor(logging.VERBOSE):
                    LOGGER.verbose(f"{step_name}Falling back to read EXIF with piexif for: {file_path}")
                exif_dict = piexif.load(file_path)
                for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                # for tag in ["DateTimeOriginal", "DateTime"]:
                    tag_id = piexif.ExifIFD.__dict__.get(tag)
                    value = exif_dict["Exif"].get(tag_id)
                    if value:
                        return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
            except Exception as e:
                LOGGER.warning(f"{step_name}Error reading EXIF for {file_path}: {e}")

        # 3. Fallback to mtime
        try:
            if LOGGER.isEnabledFor(logging.VERBOSE):
                LOGGER.verbose(f"{step_name}Falling back to mtime for: {file_path}")
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime if mtime > 0 else 0)
        except Exception as e:
            LOGGER.warning(f"{step_name}Error reading mtime for {file_path}: {e}")
            return datetime(1970, 1, 1)
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------

    with set_log_level(LOGGER, log_level):
        if type not in ['year', 'year/month', 'year-month']:
            raise ValueError(f"{step_name}The 'type' parameter must be 'year', 'year/month' or 'year-month'.")

        # ⏩ Extract extracted_dates dict from folder_analyzer object
        extracted_dates = folder_analyzer.get_extracted_dates() if folder_analyzer else {}

        replacements = []
        with tqdm(smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files", dynamic_ncols=True) as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_subfolders]
                for file in files:
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path) or file_path.lower().endswith(".json"):
                        continue
                    pbar.update(1)
                    # Get file date
                    mod_time = get_date(file_path, extracted_dates, step_name)
                    if LOGGER.isEnabledFor(logging.DEBUG):
                        LOGGER.debug(f"{step_name}Using date {mod_time} for file {file_path}")

                    # Skip files already placed in the expected date structure to avoid re-nesting
                    # (e.g. year/month/year/month).
                    current_dir_name = Path(path).name
                    parent_dir_name = Path(path).parent.name
                    if type == 'year':
                        if current_dir_name == mod_time.strftime('%Y'):
                            continue
                    elif type == 'year/month':
                        if (
                            current_dir_name == mod_time.strftime('%m')
                            and parent_dir_name == mod_time.strftime('%Y')
                        ):
                            continue
                    elif type == 'year-month':
                        if current_dir_name == mod_time.strftime('%Y-%m'):
                            continue

                    # Determine target folder
                    if type == 'year':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'))
                    elif type == 'year/month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'), mod_time.strftime('%m'))
                    elif type == 'year-month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y-%m'))
                    os.makedirs(target_dir, exist_ok=True)
                    dest_path = os.path.join(target_dir, file)
                    # Moves file_path to new dest_path
                    if os.path.abspath(file_path) != os.path.abspath(dest_path):
                        # shutil.move(file_path, dest_path)     # Safer but slower. Can be used to move files between different disks.
                        Path(file_path).rename(dest_path)       # Faster but only valid if src and dst are in the same disk,
                        # Update replacements list only when a move actually happened
                        replacements.append((str(file_path), str(dest_path)))
        LOGGER.info(f"{step_name}Organization completed. Folder structure per '{type}' created in '{input_folder}'.")
        return replacements



def move_albums(input_folder, albums_subfolder=f"{FOLDERNAME_ALBUMS}", exclude_subfolder=None, step_name="", log_level=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).
    Returns:
        list of (old_path, new_path) tuples for each moved folder.
    """
    # ----------------------------------------------------------------- AUXILIARY FUNCTIONS -------------------------------------------------------------------
    def safe_move(folder_path, albums_path):
        destination = os.path.join(albums_path, os.path.basename(folder_path))
        if os.path.exists(destination):
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            else:
                os.remove(destination)
        shutil.move(folder_path, albums_path)
    # -------------------------------------------------------------- END OF AUXILIARY FUNCTIONS ---------------------------------------------------------------

    with set_log_level(LOGGER, log_level):
        replacements = []

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]
        albums_path = os.path.join(input_folder, albums_subfolder)

        # English comment: safeguard → if albums_path is the same as input_folder, do nothing
        if os.path.abspath(input_folder) == os.path.abspath(albums_path):
            LOGGER.debug(f"{step_name}Skipping move: input_folder and albums_subfolder point to the same directory")
            return []

        exclude_subfolder_paths = [
            os.path.abspath(os.path.join(input_folder, sub))
            for sub in (exclude_subfolder or [])
        ]

        subfolders = [
            sub for sub in os.listdir(input_folder)
            if sub not in ('@eaDir', FOLDERNAME_NO_ALBUMS)
        ]

        for subfolder in tqdm(
            subfolders,
            smoothing=0.1,
            desc=f"{MSG_TAGS['INFO']}{step_name}Moving Albums in '{os.path.basename(input_folder)}' to Subfolder '{os.path.basename(albums_subfolder)}'",
            unit=" albums"
        ):
            folder_path = os.path.join(input_folder, subfolder)
            if (
                os.path.isdir(folder_path)
                and subfolder != albums_subfolder
                and os.path.abspath(folder_path) != os.path.abspath(input_folder)
                and os.path.abspath(folder_path) not in exclude_subfolder_paths
            ):
                destination = os.path.join(albums_path, subfolder)
                LOGGER.debug(f"{step_name}Moving folder '{subfolder}' → '{os.path.basename(albums_subfolder)}'")
                os.makedirs(albums_path, exist_ok=True)

                safe_move(folder_path, albums_path)

                # record the actual old and new paths, both as posix strings
                old_posix = Path(folder_path).resolve().as_posix()
                new_posix = Path(destination).resolve().as_posix()
                replacements.append((old_posix, new_posix))

        return replacements




def move_albums_to_root(albums_root, step_name="", log_level=None):
    """
    Moves all albums from nested subdirectories ('Takeout/Google Fotos' or 'Takeout/Google Photos')
    directly into the 'Albums' folder, removing unnecessary intermediate folders.
    Returns:
        list of (old_path, new_path) tuples for each moved album.
    """
    with set_log_level(LOGGER, log_level):
        replacements = []

        possible_google_folders = ["Google Fotos", "Google Photos"]
        takeout_path = os.path.join(albums_root, "Takeout")
        if not os.path.exists(takeout_path):
            LOGGER.debug(f"{step_name}'Takeout' folder not found at {takeout_path}. Exiting.")
            return replacements

        # find the actual Google Photos folder
        google_photos_path = None
        for folder in possible_google_folders:
            path = os.path.join(takeout_path, folder)
            if os.path.exists(path):
                google_photos_path = path
                break
        if not google_photos_path:
            LOGGER.debug(f"{step_name}No valid 'Google Fotos' or 'Google Photos' folder found inside 'Takeout'. Exiting.")
            return replacements

        LOGGER.debug(f"{step_name}Found Google Photos folder: {google_photos_path}")
        LOGGER.info(f"{step_name}Moving Albums to Albums root folder...")

        # move each album and record replacement
        for album in os.listdir(google_photos_path):
            album_path = os.path.join(google_photos_path, album)
            if not os.path.isdir(album_path):
                continue

            target_path = os.path.join(albums_root, album)
            new_target_path = target_path
            count = 1
            while os.path.exists(new_target_path):
                new_target_path = f"{target_path}_{count}"
                count += 1

            shutil.move(album_path, new_target_path)
            LOGGER.debug(f"{step_name}Moved: {album_path} → {new_target_path}")

            # record posix paths for analyzer
            old_posix = Path(album_path).resolve().as_posix()
            new_posix = Path(new_target_path).resolve().as_posix()
            replacements.append((old_posix, new_posix))

        # remove the empty 'Takeout' tree
        try:
            shutil.rmtree(takeout_path)
            LOGGER.debug(f"{step_name}'Takeout' folder successfully removed.")
        except Exception as e:
            LOGGER.error(f"{step_name}Failed to remove 'Takeout': {e}")

        return replacements


def count_valid_albums(folder_path, excluded_folders=None, step_name="", log_level=None):
    """
    Walk every sub-folder in *folder_path* and count how many of them contain at
    least one photo or video (direct file, POSIX symlink, or Windows .lnk).
    """
    if excluded_folders is None:
        excluded_folders = ()
    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    MEDIA_EXT = set(PHOTO_EXT) | set(VIDEO_EXT)         # union once → O(1) lookup
    valid_albums = 0
    visited_dirs = set()
    with set_log_level(LOGGER, log_level):
        for root, dirs, files in os.walk(folder_path, followlinks=True):
            real_root = os.path.realpath(root)
            if real_root in visited_dirs:               # avoid loops with symlinked dirs
                continue
            visited_dirs.add(real_root)
            folder_name = os.path.basename(root)
            # ── skip folders by name ────────────────────────────────────────────
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()
                continue
            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]
            # ── inspect files inside this folder ───────────────────────────────
            for fname in files:
                fpath = Path(root) / fname
                link_ext = fpath.suffix.lower()                 # ext of the file itself
                target_ext = ''                                 # will be filled below
                try:
                    if fpath.is_symlink():                      # POSIX / NTFS symlink
                        target_ext = fpath.resolve(strict=False).suffix.lower()
                    elif os.name == 'nt' and link_ext == '.lnk':
                        # Windows shortcut (.lnk): try to infer inner extension from its stem
                        target_ext = Path(fpath.stem).suffix.lower()
                        # NOTE: we don't parse the .lnk binary; good enough if names keep the ext.
                    else:
                        target_ext = link_ext                   # normal file (no link)
                    if link_ext in MEDIA_EXT or target_ext in MEDIA_EXT:
                        valid_albums += 1
                        LOGGER.debug(f"{step_name}✅ Valid album at: {root}")
                        break                                   # next folder
                except Exception as exc:
                    LOGGER.warning(f"{step_name}⚠️ Cannot inspect {fpath}: {exc}")
    return valid_albums


def count_valid_albums_in_first_level(folder_path, excluded_folders=None, step_name="", log_level=None):
    """
    Count subfolders directly under `folder_path` that contain at least one media file (including via symlink),
    either in the folder itself or any of its nested subfolders.

    Args:
        folder_path: Root folder where direct subfolders are scanned.
        excluded_folders: Set of folder names to skip.
        step_name: Optional step name to prefix log messages.
        log_level: Optional logging level override.
    """
    with set_log_level(LOGGER, log_level):
        if excluded_folders is None:
            excluded_folders = ()
        YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
        MEDIA_EXT = set(PHOTO_EXT) | set(VIDEO_EXT)  # union once → O(1) lookup
        valid_albums = 0
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            LOGGER.warning(f"{step_name}⚠️ Provided path is not a folder: {folder_path}")
            return valid_albums

        for subfolder in folder_path.iterdir():
            if not subfolder.is_dir():
                continue
            folder_name = subfolder.name
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                continue

            visited_dirs = set()
            found = False  # flag to break both loops
            for root, dirs, files in os.walk(subfolder, followlinks=True):
                real_root = os.path.realpath(root)
                if real_root in visited_dirs:
                    continue
                visited_dirs.add(real_root)
                for fname in files:
                    fpath = Path(root) / fname
                    link_ext = fpath.suffix.lower()
                    target_ext = ''
                    try:
                        if fpath.is_symlink():
                            target_ext = fpath.resolve(strict=False).suffix.lower()
                        elif os.name == 'nt' and link_ext == '.lnk':
                            target_ext = Path(fpath.stem).suffix.lower()
                        else:
                            target_ext = link_ext
                        if link_ext in MEDIA_EXT or target_ext in MEDIA_EXT:
                            valid_albums += 1
                            LOGGER.debug(f"{step_name}✅ Valid album at: {subfolder}")
                            found = True
                            break
                    except Exception as exc:
                        LOGGER.warning(f"{step_name}⚠️ Cannot inspect {fpath}: {repr(exc)}")
                if found:
                    break
        return valid_albums




def clone_folder_fast(input_folder, cloned_folder, step_name="", log_level=None):
    """
    Clones input_folder into cloned_folder using the fastest method available:
    - Tries CoW (cp --reflink=auto) on Linux/macOS.
    - Uses robocopy on Windows.
    - Uses rsync on Unix-like systems if reflink is not available.
    - Falls back to shutil.copytree.

    Returns:
        str: Path to the cloned folder (or input_folder if all methods fail).
    """
    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"{step_name}Creating temporary working folder at: {cloned_folder}")

        system = platform.system()

        try:
            # 1. Attempt cp --reflink (Linux/macOS with Btrfs, APFS, etc.)
            if system in ("Linux", "Darwin"):
                LOGGER.info(f"{step_name}Trying fast clone with cp --reflink=auto...")
                subprocess.run([
                    "cp", "-a", "--reflink=auto", input_folder, cloned_folder
                ], check=True)
                LOGGER.info(f"{step_name}✅ CoW clone succeeded with cp --reflink.")
                return cloned_folder

        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ cp --reflink failed: {e}")

        try:
            if system == "Windows":
                LOGGER.info(f"{step_name}Trying fast clone with robocopy...")
                result = subprocess.run([
                    "robocopy", input_folder, cloned_folder, "/MIR", "/R:0", "/W:0", "/NFL", "/NDL", "/NJH", "/NJS"
                ], capture_output=True, text=True)
                if result.returncode <= 7:
                    LOGGER.info(f"{step_name}✅ Clone succeeded with robocopy.")
                    return cloned_folder
                else:
                    raise Exception(f"robocopy error code {result.returncode}: {result.stderr}")

            elif system in ("Linux", "Darwin"):
                LOGGER.info(f"{step_name}Trying fast clone with rsync...")
                subprocess.run([
                    "rsync", "-a", "--info=progress2", input_folder + "/", cloned_folder
                ], check=True)
                LOGGER.info(f"{step_name}✅ Clone succeeded with rsync.")
                return cloned_folder

        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ Fast method failed, falling back to copytree: {e}")

        try:
            shutil.copytree(input_folder, cloned_folder)
            LOGGER.info(f"{step_name}✅ Clone succeeded with shutil.copytree.")
            return cloned_folder
        except Exception as e:
            LOGGER.warning(f"{step_name}❌ All cloning methods failed: {e}")
            return input_folder




##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
# Example main usage
if __name__ == "__main__":
    change_working_dir()

    input_folder = Path(r"r:\jaimetur\PhotoMigrator\Takeout")
    # timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # base_folder = input_folder.parent / f"Takeout_processed_{timestamp}"

    takeout = ClassTakeoutFolder(input_folder)
    res = takeout.process("Output_Takeout_Folder", capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=False, log_level=logging.DEBUG)
    print(res)
