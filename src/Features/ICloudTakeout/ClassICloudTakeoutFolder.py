# -*- coding: utf-8 -*-
import csv
import logging
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from dateutil import parser

from Core.CustomLogger import set_log_level
from Core.DataModels import init_process_results
from Core.FolderAnalyzer import FolderAnalyzer
from Core.GlobalVariables import (
    ARGS,
    FOLDERNAME_ALBUMS,
    FOLDERNAME_EXIFTOOL,
    FOLDERNAME_NO_ALBUMS,
    LOGGER,
    LOG_LEVEL,
    PHOTO_EXT,
    TIMESTAMP,
    VIDEO_EXT,
)
from Features.GoogleTakeout.ClassTakeoutFolder import organize_files_by_date
from Utils.FileUtils import contains_zip_files, remove_empty_dirs, sanitize_and_unpack_zips
from Utils.GeneralUtils import ensure_executable, sha1_checksum, tqdm, update_file_timestamps, update_metadata
from Utils.StandaloneUtils import get_exif_tool_path


class _ExifToolSession:
    def __init__(self, exiftool_path: str):
        self.exiftool_path = str(exiftool_path)
        self.process = subprocess.Popen(
            [self.exiftool_path, "-stay_open", "True", "-@", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def execute(self, args):
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("ExifTool persistent session streams are not available.")
        for arg in args:
            self.process.stdin.write(f"{arg}\n")
        self.process.stdin.write("-execute\n")
        self.process.stdin.flush()
        output_lines = []
        while True:
            line = self.process.stdout.readline()
            if line == "":
                break
            if line.strip() == "{ready}":
                break
            output_lines.append(line)
        return "".join(output_lines).strip()

    def close(self):
        if self.process.stdin is not None:
            try:
                self.process.stdin.write("-stay_open\nFalse\n")
                self.process.stdin.flush()
            except Exception:
                pass
        try:
            self.process.wait(timeout=5)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


class ClassICloudTakeoutFolder:
    def __init__(self, takeout_folder):
        self.ARGS = ARGS
        self.takeout_folder = Path(takeout_folder).expanduser().resolve()
        self.unzipped_folder = None
        self.needs_unzip = self.takeout_folder.is_dir() and contains_zip_files(self.takeout_folder, log_level=logging.WARNING)
        self.input_folder = self.takeout_folder
        self.output_folder = self._build_output_folder()
        self.no_albums_folder = self.output_folder / FOLDERNAME_NO_ALBUMS
        self.albums_folder = self.output_folder / FOLDERNAME_ALBUMS
        self.memories_folder = self.output_folder / "Memories"
        self.result = init_process_results()
        self.steps_duration = []
        self.step = 0
        self.substep = 0
        self.local_analyzer = FolderAnalyzer(logger=LOGGER)
        self.initial_filedates_json = ""
        self.final_filedates_json = ""
        self.CLIENT_NAME = f"iCloud Takeout Folder ({self.takeout_folder.name})"
        self._exiftool_path = None
        self._exiftool_session = None

    def _build_output_folder(self):
        if self.ARGS.get("output-folder"):
            return Path(self.ARGS["output-folder"]).expanduser().resolve()
        suffix = self.ARGS.get("icloud-output-folder-suffix", "processed")
        return Path(f"{self.takeout_folder}_{suffix}_{TIMESTAMP}").resolve()

    def _refresh_input_folder(self):
        self.input_folder = self.unzipped_folder or self.takeout_folder
        return self.input_folder

    @staticmethod
    def _path_key(path_obj: Path) -> str:
        return Path(path_obj).resolve().as_posix()

    @classmethod
    def _scope_root_for_path(cls, path_obj: Path) -> Path:
        path_obj = Path(path_obj).resolve()
        anchor = path_obj.parent if path_obj.is_file() else path_obj
        parts = list(anchor.parts)
        parts_norm = [cls._normalized_name(part) for part in parts]
        for marker in ("photos", "albums", "memories"):
            if marker in parts_norm:
                idx = parts_norm.index(marker)
                if idx > 0:
                    return Path(*parts[:idx]).resolve()
        return anchor

    @staticmethod
    def _normalized_name(value):
        return str(value or "").strip().casefold()

    @staticmethod
    def _normalized_checksum(value):
        return str(value or "").strip().replace("=", "").casefold()

    @staticmethod
    def _is_photo_details_csv(path_obj: Path) -> bool:
        stem = path_obj.stem.casefold().replace("_", " ").replace("-", " ")
        return stem.startswith("photo details")

    @staticmethod
    def _iter_media_files(root_folder: Path):
        for path in root_folder.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in PHOTO_EXT or suffix in VIDEO_EXT:
                yield path

    @staticmethod
    def _parse_icloud_datetime(raw_value):
        text = str(raw_value or "").strip()
        if not text:
            return None
        try:
            dt = parser.parse(text)
        except Exception:
            return None
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt

    @staticmethod
    def _unique_file_path(folder: Path, filename: str) -> Path:
        candidate = folder / filename
        if not candidate.exists():
            return candidate
        stem = candidate.stem
        suffix = candidate.suffix
        counter = 2
        while True:
            alt = folder / f"{stem} ({counter}){suffix}"
            if not alt.exists():
                return alt
            counter += 1

    @staticmethod
    def _safe_collection_name(path_obj: Path) -> str:
        return path_obj.stem.strip() or path_obj.name.strip() or "Unnamed"

    def _parse_membership_csv(self, csv_path: Path):
        members = []
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    return members
                key_map = {self._normalized_name(name): name for name in reader.fieldnames if name}
                member_key = None
                for candidate in ("imgname", "imagename", "images"):
                    if candidate in key_map:
                        member_key = key_map[candidate]
                        break
                if not member_key and reader.fieldnames:
                    member_key = reader.fieldnames[0]
                for row in reader:
                    raw_name = str((row or {}).get(member_key, "") or "").strip()
                    if raw_name:
                        members.append(raw_name)
        except Exception as exc:
            LOGGER.warning(f"Could not parse iCloud membership CSV '{csv_path}': {exc}")
        return members

    def _collect_csv_inputs(self, input_folder: Path):
        photo_details_csvs = []
        album_csvs = []
        memory_csvs = []
        for csv_path in input_folder.rglob("*.csv"):
            parts_norm = [self._normalized_name(part) for part in csv_path.parts]
            if self._is_photo_details_csv(csv_path):
                photo_details_csvs.append(csv_path)
                continue
            if "albums" in parts_norm:
                album_csvs.append(csv_path)
                continue
            if "memories" in parts_norm:
                memory_csvs.append(csv_path)
                continue
        return photo_details_csvs, album_csvs, memory_csvs

    def _load_photo_details_rows(self, csv_files):
        rows = []
        for csv_path in csv_files:
            try:
                csv_folder = csv_path.parent.resolve()
                scope_root = self._scope_root_for_path(csv_path)
                with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        img_name = str((row or {}).get("imgName", "") or "").strip()
                        if not img_name:
                            continue
                        original_dt = self._parse_icloud_datetime(row.get("originalCreationDate"))
                        import_dt = self._parse_icloud_datetime(row.get("importDate"))
                        chosen_dt = original_dt or import_dt
                        rows.append(
                            {
                                "img_name": img_name,
                                "checksum": str((row or {}).get("fileChecksum", "") or "").strip(),
                                "original_dt": original_dt,
                                "import_dt": import_dt,
                                "chosen_dt": chosen_dt,
                                "favorite": str((row or {}).get("favorite", "") or "").strip(),
                                "hidden": str((row or {}).get("hidden", "") or "").strip(),
                                "deleted": str((row or {}).get("deleted", "") or "").strip(),
                                "source_csv": str(csv_path),
                                "csv_folder_key": self._path_key(csv_folder),
                                "scope_key": self._path_key(scope_root),
                            }
                        )
            except Exception as exc:
                LOGGER.warning(f"Could not parse iCloud Photo Details CSV '{csv_path}': {exc}")
        return rows

    def _build_source_indexes(self, source_records):
        by_name = defaultdict(list)
        by_folder_name = defaultdict(lambda: defaultdict(list))
        by_scope_name = defaultdict(lambda: defaultdict(list))
        for record in source_records:
            basename_key = record["basename_key"]
            by_name[basename_key].append(record)
            by_folder_name[record["source_folder_key"]][basename_key].append(record)
            by_scope_name[record["scope_key"]][basename_key].append(record)
        return {
            "by_name": by_name,
            "by_folder_name": by_folder_name,
            "by_scope_name": by_scope_name,
        }

    def _stage_original_assets(self, input_folder: Path, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            self.no_albums_folder.mkdir(parents=True, exist_ok=True)
            source_records = []
            for source_path in tqdm(
                self._iter_media_files(input_folder),
                desc=f"[INFO] {step_name}Staging iCloud assets",
                unit=" files",
                smoothing=0.1,
                dynamic_ncols=True,
            ):
                dest_path = self._unique_file_path(self.no_albums_folder, source_path.name)
                shutil.copy2(source_path, dest_path)
                record = {
                    "source": source_path.resolve(),
                    "dest": dest_path.resolve(),
                    "basename": source_path.name,
                    "basename_key": self._normalized_name(source_path.name),
                    "source_folder_key": self._path_key(source_path.parent),
                    "scope_key": self._path_key(self._scope_root_for_path(source_path)),
                    "suffix": source_path.suffix.lower(),
                    "checksum_cache": None,
                }
                source_records.append(record)
            return source_records, self._build_source_indexes(source_records)

    def _record_checksum_variants(self, record):
        if record.get("checksum_cache") is not None:
            return record["checksum_cache"]
        try:
            hex_checksum, base64_checksum = sha1_checksum(str(record["source"]))
            variants = {
                self._normalized_checksum(hex_checksum),
                self._normalized_checksum(base64_checksum),
                self._normalized_checksum(str(base64_checksum).rstrip("=")),
            }
            record["checksum_cache"] = variants
        except Exception as exc:
            LOGGER.warning(f"Could not calculate checksum for '{record['source']}': {exc}")
            record["checksum_cache"] = set()
        return record["checksum_cache"]

    def _match_row_to_records(self, row, source_index):
        basename_key = self._normalized_name(row.get("img_name"))
        candidates = list(
            source_index["by_folder_name"].get(row.get("csv_folder_key", ""), {}).get(basename_key, [])
        )
        if not candidates:
            candidates = list(
                source_index["by_scope_name"].get(row.get("scope_key", ""), {}).get(basename_key, [])
            )
        if not candidates:
            return []
        checksum = self._normalized_checksum(row.get("checksum"))
        if len(candidates) > 1 and checksum:
            checksum_matches = [
                record for record in candidates
                if checksum in self._record_checksum_variants(record)
            ]
            if checksum_matches:
                candidates = checksum_matches
        return candidates

    def _date_to_exif_string(self, dt_value):
        return dt_value.strftime("%Y:%m:%d %H:%M:%S")

    def _date_to_general_string(self, dt_value):
        return dt_value.strftime("%Y-%m-%d %H:%M:%S")

    def _get_exiftool_path(self, step_name=""):
        if self._exiftool_path is not None:
            return self._exiftool_path
        exif_tool_path = get_exif_tool_path(base_path=FOLDERNAME_EXIFTOOL, step_name=step_name)
        if not os.path.exists(exif_tool_path):
            self._exiftool_path = ""
            return ""
        ensure_executable(exif_tool_path)
        self._exiftool_path = exif_tool_path
        return self._exiftool_path

    def _get_exiftool_session(self, step_name=""):
        if self._exiftool_session is not None:
            return self._exiftool_session
        exif_tool_path = self._get_exiftool_path(step_name=step_name)
        if not exif_tool_path:
            return None
        self._exiftool_session = _ExifToolSession(exif_tool_path)
        return self._exiftool_session

    def _close_exiftool_session(self):
        if self._exiftool_session is None:
            return
        try:
            self._exiftool_session.close()
        finally:
            self._exiftool_session = None

    def _build_exiftool_args(self, file_path: Path, dt_value: datetime):
        date_text = self._date_to_exif_string(dt_value)
        args = ["-overwrite_original"]
        suffix = file_path.suffix.lower()
        if suffix in PHOTO_EXT:
            args.extend(
                [
                    f"-DateTimeOriginal={date_text}",
                    f"-CreateDate={date_text}",
                    f"-ModifyDate={date_text}",
                    f"-DateTimeDigitized={date_text}",
                ]
            )
        else:
            args.extend(
                [
                    f"-QuickTime:CreateDate={date_text}",
                    f"-QuickTime:ModifyDate={date_text}",
                    f"-QuickTime:TrackCreateDate={date_text}",
                    f"-QuickTime:TrackModifyDate={date_text}",
                    f"-QuickTime:MediaCreateDate={date_text}",
                    f"-QuickTime:MediaModifyDate={date_text}",
                    f"-Keys:CreationDate={date_text}",
                ]
            )
        args.append(f"-FileModifyDate={date_text}")
        if sys.platform.startswith("win") or sys.platform == "darwin":
            args.append(f"-FileCreateDate={date_text}")
        args.append(str(file_path))
        return args

    def _write_exif_with_exiftool(self, file_path: Path, dt_value: datetime, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            session = self._get_exiftool_session(step_name=step_name)
            if session is None:
                return False
            try:
                output = session.execute(self._build_exiftool_args(file_path, dt_value))
            except Exception as exc:
                LOGGER.warning(
                    f"{step_name}ExifTool persistent session failed for '{file_path}'. "
                    f"Falling back to native metadata update. Details: {str(exc)[:400]}"
                )
                return False
            if "Error:" not in output:
                return True
            LOGGER.warning(
                f"{step_name}ExifTool could not update '{file_path}'. "
                f"Falling back to native metadata update. Details: {output[:400]}"
            )
            return False

    def _apply_dates(self, matched_rows, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            extracted_dates = {}
            updated_files = 0
            unmatched_rows = 0
            ambiguous_rows = 0
            processed_paths = set()
            for row, records in tqdm(
                matched_rows,
                desc=f"[INFO] {step_name}Applying iCloud dates",
                unit=" rows",
                smoothing=0.1,
                dynamic_ncols=True,
            ):
                dt_value = row.get("chosen_dt")
                if not dt_value:
                    unmatched_rows += 1
                    continue
                if not records:
                    unmatched_rows += 1
                    continue
                if len(records) > 1:
                    ambiguous_rows += 1
                for record in records:
                    dest_path = Path(record["dest"]).resolve()
                    dest_key = dest_path.as_posix()
                    if dest_key in processed_paths:
                        entry = extracted_dates.get(dest_key)
                        if entry and not entry.get("OldestDate"):
                            entry["OldestDate"] = dt_value.isoformat(sep=" ")
                        continue
                    if not self._write_exif_with_exiftool(dest_path, dt_value, step_name=step_name, log_level=log_level):
                        update_metadata(str(dest_path), self._date_to_general_string(dt_value), log_level=log_level)
                        update_file_timestamps(str(dest_path), self._date_to_general_string(dt_value), log_level=log_level)
                    processed_paths.add(dest_key)
                    extracted_dates[dest_key] = {
                        "SourceFile": str(record["source"]),
                        "TargetFile": dest_key,
                        "OldestDate": dt_value.isoformat(sep=" "),
                        "Source": f"iCloud Photo Details CSV ({Path(row['source_csv']).name})",
                        "ICloudChecksum": row.get("checksum", ""),
                        "ICloudFavorite": row.get("favorite", ""),
                        "ICloudHidden": row.get("hidden", ""),
                        "ICloudDeleted": row.get("deleted", ""),
                    }
                    updated_files += 1
            LOGGER.info(f"{step_name}iCloud dates applied to {updated_files} assets.")
            LOGGER.info(f"{step_name}Rows without matching media: {unmatched_rows}")
            LOGGER.info(f"{step_name}Rows matched to multiple media files: {ambiguous_rows}")
            return extracted_dates

    def _update_source_record_destinations(self, source_records, replacements):
        replacement_map = {
            Path(old_path).resolve().as_posix(): Path(new_path).resolve()
            for old_path, new_path in replacements
        }
        for record in source_records:
            current_dest = Path(record["dest"]).resolve()
            replacement = replacement_map.get(current_dest.as_posix())
            if replacement is not None:
                record["dest"] = replacement
        return self._build_source_indexes(source_records)

    def _organize_originals(self, source_records, extracted_dates, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            self.local_analyzer = FolderAnalyzer(extracted_dates=extracted_dates, logger=LOGGER)
            structure = self.ARGS.get("icloud-no-albums-folders-structure", "year/month")
            replacements = organize_files_by_date(
                input_folder=str(self.no_albums_folder),
                type=structure,
                exclude_subfolders=["@eaDir"],
                folder_analyzer=self.local_analyzer,
                step_name=step_name,
                log_level=log_level,
            )
            if replacements:
                self.local_analyzer.apply_replacements(replacements, step_name=step_name, log_level=log_level)
            return self._update_source_record_destinations(source_records, replacements)

    def _create_link_or_copy(self, source_path: Path, destination_path: Path, use_copy: bool):
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        final_path = destination_path
        if final_path.exists() or final_path.is_symlink():
            final_path = self._unique_file_path(destination_path.parent, destination_path.name)
        if use_copy:
            shutil.copy2(source_path, final_path)
        else:
            os.symlink(source_path, final_path)
        return final_path

    def _build_collection_from_csvs(self, csv_files, source_index, root_folder: Path, structure: str, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            use_copy = self.ARGS.get("icloud-no-symbolic-albums", False)
            created_collections = 0
            for csv_path in csv_files:
                collection_name = self._safe_collection_name(csv_path)
                members = self._parse_membership_csv(csv_path)
                if not members:
                    continue
                collection_folder = root_folder / collection_name
                scope_key = self._path_key(self._scope_root_for_path(csv_path))
                seen_sources = set()
                for member_name in members:
                    member_key = self._normalized_name(member_name)
                    scope_matches = source_index["by_scope_name"].get(scope_key, {}).get(member_key, [])
                    for record in scope_matches:
                        source_dest = Path(record["dest"]).resolve()
                        source_key = source_dest.as_posix()
                        if source_key in seen_sources:
                            continue
                        seen_sources.add(source_key)
                        self._create_link_or_copy(source_dest, collection_folder / source_dest.name, use_copy=use_copy)
                if not collection_folder.exists():
                    continue
                created_collections += 1
                if structure != "flatten":
                    organize_files_by_date(
                        input_folder=str(collection_folder),
                        type=structure,
                        exclude_subfolders=["@eaDir"],
                        folder_analyzer=self.local_analyzer,
                        step_name=step_name,
                        log_level=log_level,
                    )
            return created_collections

    def _save_dates_json(self, step_name="", log_level=None):
        with set_log_level(LOGGER, log_level):
            if not getattr(self.local_analyzer, "extracted_dates", None):
                return ""
            return self.local_analyzer.save_to_json("icloud_takeout_dates_metadata.json", step_name=step_name)

    def process(self, log_level=None):
        with set_log_level(LOGGER, log_level):
            try:
                if not self.takeout_folder.exists() or not self.takeout_folder.is_dir():
                    LOGGER.error(f"The iCloud Takeout folder does not exist: '{self.takeout_folder}'")
                    sys.exit(1)

                processing_start = datetime.now()
                LOGGER.info("=============================================================")
                LOGGER.info("Starting iCloud Takeout Processor Feature...")
                LOGGER.info("=============================================================")
                LOGGER.info("")

                if self.needs_unzip:
                    self.unzipped_folder = Path(f"{self.takeout_folder}_unzipped_{TIMESTAMP}").resolve()
                    step_name = "[iCloud PRE-CHECK]-[Unzip Takeout] : "
                    LOGGER.info(f"{step_name}ZIP files detected. Extracting to '{self.unzipped_folder}'...")
                    sanitize_and_unpack_zips(
                        input_folder=str(self.takeout_folder),
                        unzip_folder=str(self.unzipped_folder),
                        step_name=step_name,
                        log_level=LOG_LEVEL,
                    )
                self._refresh_input_folder()

                LOGGER.info(f"Input iCloud Takeout folder  : '{self.input_folder}'")
                LOGGER.info(f"Output processed folder      : '{self.output_folder}'")
                LOGGER.info(f"Albums structure             : '{self.ARGS.get('icloud-albums-folders-structure', 'flatten')}'")
                LOGGER.info(f"ALL_PHOTOS structure         : '{self.ARGS.get('icloud-no-albums-folders-structure', 'year/month')}'")
                LOGGER.info(f"Use copies for albums        : '{self.ARGS.get('icloud-no-symbolic-albums', False)}'")
                LOGGER.info(f"Include Memories             : '{self.ARGS.get('icloud-include-memories', False)}'")
                LOGGER.info("")

                self.output_folder.mkdir(parents=True, exist_ok=True)

                step_name = "[iCloud PREP]-[Scan CSVs] : "
                photo_details_csvs, album_csvs, memory_csvs = self._collect_csv_inputs(self.input_folder)
                LOGGER.info(f"{step_name}Photo Details CSV files found : {len(photo_details_csvs)}")
                LOGGER.info(f"{step_name}Album CSV files found         : {len(album_csvs)}")
                LOGGER.info(f"{step_name}Memory CSV files found        : {len(memory_csvs)}")

                step_name = "[iCloud PROCESS]-[Stage Media] : "
                source_records, source_index = self._stage_original_assets(self.input_folder, step_name=step_name, log_level=LOG_LEVEL)
                LOGGER.info(f"{step_name}Media assets staged into '{self.no_albums_folder}': {len(source_records)}")

                step_name = "[iCloud PROCESS]-[Read Photo Details] : "
                photo_rows = self._load_photo_details_rows(photo_details_csvs)
                LOGGER.info(f"{step_name}Rows loaded from Photo Details CSV files: {len(photo_rows)}")
                matched_rows = [(row, self._match_row_to_records(row, source_index)) for row in photo_rows]

                step_name = "[iCloud PROCESS]-[Write Dates] : "
                extracted_dates = self._apply_dates(matched_rows, step_name=step_name, log_level=LOG_LEVEL)

                step_name = "[iCloud POST]-[Organize ALL_PHOTOS] : "
                source_index = self._organize_originals(source_records, extracted_dates, step_name=step_name, log_level=LOG_LEVEL)

                step_name = "[iCloud POST]-[Build Albums] : "
                album_count = self._build_collection_from_csvs(
                    csv_files=album_csvs,
                    source_index=source_index,
                    root_folder=self.albums_folder,
                    structure=self.ARGS.get("icloud-albums-folders-structure", "flatten"),
                    step_name=step_name,
                    log_level=LOG_LEVEL,
                )
                LOGGER.info(f"{step_name}Album folders created: {album_count}")
                self.result["valid_albums_found"] = album_count

                if self.ARGS.get("icloud-include-memories", False):
                    step_name = "[iCloud POST]-[Build Memories] : "
                    memories_count = self._build_collection_from_csvs(
                        csv_files=memory_csvs,
                        source_index=source_index,
                        root_folder=self.memories_folder,
                        structure=self.ARGS.get("icloud-albums-folders-structure", "flatten"),
                        step_name=step_name,
                        log_level=LOG_LEVEL,
                    )
                    LOGGER.info(f"{step_name}Memories folders created: {memories_count}")

                step_name = "[iCloud FINAL]-[Cleanup] : "
                remove_empty_dirs(str(self.output_folder), log_level=LOG_LEVEL)
                self.final_filedates_json = self._save_dates_json(step_name=step_name, log_level=LOG_LEVEL)
                if getattr(self.local_analyzer, "extracted_dates", None):
                    self.local_analyzer.show_files_without_dates(relative_folder=str(self.output_folder), step_name=step_name)

                processing_end = datetime.now()
                LOGGER.info("")
                LOGGER.info("=============================================================")
                LOGGER.info("iCloud Takeout Processing finished")
                LOGGER.info("=============================================================")
                LOGGER.info(f"Processed folder : '{self.output_folder}'")
                LOGGER.info(f"Duration         : {str(timedelta(seconds=round((processing_end - processing_start).total_seconds())))}")
                if self.final_filedates_json:
                    LOGGER.info(f"Dates JSON       : '{self.final_filedates_json}'")
                LOGGER.info("")
                return self.result
            finally:
                self._close_exiftool_session()
