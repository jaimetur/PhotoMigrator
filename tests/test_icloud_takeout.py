import csv
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import Features.ICloudTakeout.ClassICloudTakeoutFolder as icloud_module
except ModuleNotFoundError as exc:
    icloud_module = exc

try:
    import Features.GoogleTakeout.ClassTakeoutFolder as google_takeout_module
except ModuleNotFoundError as exc:
    google_takeout_module = exc


def _args(output_folder):
    return {
        "output-folder": str(output_folder),
        "icloud-output-folder-suffix": "processed",
        "icloud-albums-folders-structure": "flatten",
        "icloud-no-albums-folders-structure": "flatten",
        "icloud-no-symbolic-albums": True,
        "icloud-include-memories": True,
        "icloud-prefer-native-exif-writer": False,
    }


class TestICloudTakeout(unittest.TestCase):
    def setUp(self):
        if isinstance(icloud_module, ModuleNotFoundError):
            self.skipTest(f"iCloud Takeout dependencies are not installed in this environment: {icloud_module}")
        if isinstance(google_takeout_module, ModuleNotFoundError):
            self.skipTest(f"Google Takeout dependencies are not installed in this environment: {google_takeout_module}")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.takeout_root = self.base_path / "iCloudExport"
        self.takeout_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_photo_details(self, csv_path: Path, rows):
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "imgName",
                    "fileChecksum",
                    "favorite",
                    "hidden",
                    "deleted",
                    "originalCreationDate",
                    "viewCount",
                    "importDate",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _write_membership_csv(self, csv_path: Path, member_names):
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["imgName"])
            writer.writeheader()
            for member_name in member_names:
                writer.writerow({"imgName": member_name})

    def test_photo_details_rows_match_only_inside_their_own_export_folder(self):
        scope_a_photos = self.takeout_root / "PartA" / "Photos"
        scope_b_photos = self.takeout_root / "PartB" / "Photos"
        scope_a_photos.mkdir(parents=True, exist_ok=True)
        scope_b_photos.mkdir(parents=True, exist_ok=True)

        (scope_a_photos / "IMG_0001.JPG").write_bytes(b"scope-a")
        (scope_b_photos / "IMG_0001.JPG").write_bytes(b"scope-b")

        self._write_photo_details(
            scope_a_photos / "Photo Details.csv",
            [
                {
                    "imgName": "IMG_0001.JPG",
                    "fileChecksum": "",
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Sunday May 14,2023 3:36 AM GMT",
                    "viewCount": 0,
                    "importDate": "Sunday May 14,2023 3:37 AM GMT",
                }
            ],
        )
        self._write_photo_details(
            scope_b_photos / "Photo Details.csv",
            [
                {
                    "imgName": "IMG_0001.JPG",
                    "fileChecksum": "",
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Monday May 15,2023 3:36 AM GMT",
                    "viewCount": 0,
                    "importDate": "Monday May 15,2023 3:37 AM GMT",
                }
            ],
        )

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            source_records, source_index = processor._stage_original_assets(self.takeout_root)
            csv_files, _, _ = processor._collect_csv_inputs(self.takeout_root)
            photo_rows = processor._load_photo_details_rows(csv_files)
            matched_rows = [(row, processor._match_row_to_records(row, source_index)) for row in photo_rows]

        self.assertEqual(len(source_records), 2)
        self.assertEqual(len(matched_rows), 2)

        matches_by_scope = {
            row["scope_key"]: records
            for row, records in matched_rows
        }
        self.assertEqual(len(matches_by_scope), 2)
        for scope_key, records in matches_by_scope.items():
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["scope_key"], scope_key)

    def test_photo_details_rows_can_fallback_to_unique_global_name_when_local_scope_match_fails(self):
        source_photos = self.takeout_root / "PartA" / "Photos"
        metadata_photos = self.takeout_root / "PartB" / "Photos"
        source_photos.mkdir(parents=True, exist_ok=True)
        metadata_photos.mkdir(parents=True, exist_ok=True)

        (source_photos / "IMG_0099.JPG").write_bytes(b"only-copy")
        self._write_photo_details(
            metadata_photos / "Photo Details.csv",
            [
                {
                    "imgName": "IMG_0099.JPG",
                    "fileChecksum": "",
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Sunday May 14,2023 3:36 AM GMT",
                    "viewCount": 0,
                    "importDate": "Sunday May 14,2023 3:37 AM GMT",
                }
            ],
        )

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            csv_files, _, _ = processor._collect_csv_inputs(self.takeout_root)
            row = processor._load_photo_details_rows(csv_files)[0]
            matches = processor._match_row_to_records(row, source_index)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["source"].resolve(), (source_photos / "IMG_0099.JPG").resolve())

    def test_photo_details_rows_can_fallback_globally_by_checksum_when_name_is_not_unique(self):
        source_a = self.takeout_root / "PartA" / "Photos"
        source_b = self.takeout_root / "PartB" / "Photos"
        metadata_scope = self.takeout_root / "PartC" / "Photos"
        source_a.mkdir(parents=True, exist_ok=True)
        source_b.mkdir(parents=True, exist_ok=True)
        metadata_scope.mkdir(parents=True, exist_ok=True)

        file_a = source_a / "IMG_0100.JPG"
        file_b = source_b / "IMG_0100.JPG"
        file_a.write_bytes(b"same-name-a")
        file_b.write_bytes(b"same-name-b")

        checksum_hex, _ = icloud_module.sha1_checksum(str(file_b))
        self._write_photo_details(
            metadata_scope / "Photo Details.csv",
            [
                {
                    "imgName": "IMG_0100.JPG",
                    "fileChecksum": checksum_hex,
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Sunday May 14,2023 3:36 AM GMT",
                    "viewCount": 0,
                    "importDate": "Sunday May 14,2023 3:37 AM GMT",
                }
            ],
        )

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            csv_files, _, _ = processor._collect_csv_inputs(self.takeout_root)
            row = processor._load_photo_details_rows(csv_files)[0]
            matches = processor._match_row_to_records(row, source_index)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["source"].resolve(), file_b.resolve())

    def test_contains_icloud_takeout_structure_detects_renamed_metadata_csv_by_header(self):
        photos_folder = self.takeout_root / "RenamedExport" / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        self._write_photo_details(
            photos_folder / "metadata.csv",
            [
                {
                    "imgName": "IMG_0001.JPG",
                    "fileChecksum": "",
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Sunday May 14,2023 3:36 AM GMT",
                    "viewCount": 0,
                    "importDate": "Sunday May 14,2023 3:37 AM GMT",
                }
            ],
        )

        with patch.object(icloud_module, "LOGGER", Mock()):
            detected = icloud_module.contains_icloud_takeout_structure(self.takeout_root)

        self.assertTrue(detected)

    def test_contains_icloud_takeout_structure_detects_renamed_metadata_csv_inside_zip_by_header(self):
        zip_path = self.takeout_root / "renamed-export.zip"
        with zipfile.ZipFile(zip_path, "w") as handle:
            handle.writestr(
                "RenamedBundle/Photos/metadata.csv",
                (
                    "imgName,fileChecksum,favorite,hidden,deleted,originalCreationDate,viewCount,importDate\n"
                    "IMG_0001.JPG,,no,no,no,\"Sunday May 14,2023 3:36 AM GMT\",0,\"Sunday May 14,2023 3:37 AM GMT\"\n"
                ),
            )

        with patch.object(icloud_module, "LOGGER", Mock()):
            detected = icloud_module.contains_icloud_takeout_structure(self.takeout_root)

        self.assertTrue(detected)

    def test_album_membership_uses_only_assets_from_the_same_scope(self):
        scope_a_photos = self.takeout_root / "PartA" / "Photos"
        scope_a_albums = self.takeout_root / "PartA" / "Albums"
        scope_b_photos = self.takeout_root / "PartB" / "Photos"
        scope_b_albums = self.takeout_root / "PartB" / "Albums"
        scope_a_photos.mkdir(parents=True, exist_ok=True)
        scope_a_albums.mkdir(parents=True, exist_ok=True)
        scope_b_photos.mkdir(parents=True, exist_ok=True)
        scope_b_albums.mkdir(parents=True, exist_ok=True)

        (scope_a_photos / "IMG_0001.JPG").write_bytes(b"scope-a")
        (scope_b_photos / "IMG_0001.JPG").write_bytes(b"scope-b")

        self._write_membership_csv(scope_a_albums / "Trip A.csv", ["IMG_0001.JPG"])
        self._write_membership_csv(scope_b_albums / "Trip B.csv", ["IMG_0001.JPG"])

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            _, album_csvs, _ = processor._collect_csv_inputs(self.takeout_root)
            stats = processor._build_collection_from_csvs(
                csv_files=album_csvs,
                source_index=source_index,
                root_folder=processor.albums_folder,
                structure="flatten",
            )

        self.assertEqual(stats["collections_created"], 2)
        self.assertEqual(stats["collections_fully_resolved"], 2)
        trip_a_files = sorted(path.read_bytes() for path in (self.base_path / "output" / "Albums" / "Trip A").iterdir())
        trip_b_files = sorted(path.read_bytes() for path in (self.base_path / "output" / "Albums" / "Trip B").iterdir())
        self.assertEqual(trip_a_files, [b"scope-a"])
        self.assertEqual(trip_b_files, [b"scope-b"])

    def test_album_symlinks_use_relative_targets(self):
        photos_folder = self.takeout_root / "Photos"
        albums_folder = self.takeout_root / "Albums"
        photos_folder.mkdir(parents=True, exist_ok=True)
        albums_folder.mkdir(parents=True, exist_ok=True)

        (photos_folder / "IMG_0001.JPG").write_bytes(b"scope-a")
        self._write_membership_csv(albums_folder / "Favorites.csv", ["IMG_0001.JPG"])

        args = _args(self.base_path / "output")
        args["icloud-no-symbolic-albums"] = False

        with patch.object(icloud_module, "ARGS", args):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            _, album_csvs, _ = processor._collect_csv_inputs(self.takeout_root)
            processor._build_collection_from_csvs(
                csv_files=album_csvs,
                source_index=source_index,
                root_folder=processor.albums_folder,
                structure="flatten",
            )

        link_path = self.base_path / "output" / "Albums" / "Favorites" / "IMG_0001.JPG"
        self.assertTrue(link_path.is_symlink())
        link_target = os.readlink(link_path)
        self.assertFalse(Path(link_target).is_absolute())
        self.assertEqual(link_path.resolve().read_bytes(), b"scope-a")

    def test_album_folder_is_created_empty_when_no_members_resolve(self):
        photos_folder = self.takeout_root / "Photos"
        albums_folder = self.takeout_root / "Albums"
        photos_folder.mkdir(parents=True, exist_ok=True)
        albums_folder.mkdir(parents=True, exist_ok=True)

        (photos_folder / "IMG_0001.JPG").write_bytes(b"scope-a")
        self._write_membership_csv(albums_folder / "Missing.csv", ["IMG_9999.JPG"])

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            _, album_csvs, _ = processor._collect_csv_inputs(self.takeout_root)
            stats = processor._build_collection_from_csvs(
                csv_files=album_csvs,
                source_index=source_index,
                root_folder=processor.albums_folder,
                structure="flatten",
            )

        empty_album = self.base_path / "output" / "Albums" / "Missing"
        self.assertTrue(empty_album.exists())
        self.assertEqual(list(empty_album.iterdir()), [])
        self.assertEqual(stats["collections_created"], 1)
        self.assertEqual(stats["collections_empty"], 1)
        self.assertEqual(stats["members_unresolved"], 1)

    def test_album_stats_track_partial_resolution(self):
        photos_folder = self.takeout_root / "Photos"
        albums_folder = self.takeout_root / "Albums"
        photos_folder.mkdir(parents=True, exist_ok=True)
        albums_folder.mkdir(parents=True, exist_ok=True)

        (photos_folder / "IMG_0001.JPG").write_bytes(b"scope-a")
        self._write_membership_csv(albums_folder / "Mixed.csv", ["IMG_0001.JPG", "IMG_9999.JPG"])

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            _, source_index = processor._stage_original_assets(self.takeout_root)
            _, album_csvs, _ = processor._collect_csv_inputs(self.takeout_root)
            stats = processor._build_collection_from_csvs(
                csv_files=album_csvs,
                source_index=source_index,
                root_folder=processor.albums_folder,
                structure="flatten",
            )

        mixed_album = self.base_path / "output" / "Albums" / "Mixed"
        self.assertTrue(mixed_album.exists())
        self.assertEqual(sorted(path.name for path in mixed_album.iterdir()), ["IMG_0001.JPG"])
        self.assertEqual(stats["collections_created"], 1)
        self.assertEqual(stats["collections_partially_resolved"], 1)
        self.assertEqual(stats["members_resolved"], 1)
        self.assertEqual(stats["members_unresolved"], 1)

    def test_build_exiftool_args_include_filesystem_dates(self):
        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            dt_value = datetime(2023, 5, 14, 3, 36, 0)

            with patch.object(icloud_module.sys, "platform", "win32"):
                args = processor._build_exiftool_args(Path("/tmp/example.jpg"), dt_value)

        self.assertIn("-DateTimeOriginal=2023:05:14 03:36:00", args)
        self.assertIn("-FileModifyDate=2023:05:14 03:36:00", args)
        self.assertIn("-FileCreateDate=2023:05:14 03:36:00", args)

    def test_parse_icloud_datetime_preserves_explicit_year_from_photo_details_format(self):
        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            parsed = processor._parse_icloud_datetime("Wednesday December 27,2023 3:42 AM GMT")

        self.assertEqual(parsed, datetime(2023, 12, 27, 3, 42, 0))

    def test_load_photo_details_rows_keeps_csv_year_in_chosen_dt(self):
        photos_folder = self.takeout_root / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        self._write_photo_details(
            photos_folder / "Photo Details.csv",
            [
                {
                    "imgName": "IMG_72671.JPG",
                    "fileChecksum": "",
                    "favorite": "no",
                    "hidden": "no",
                    "deleted": "no",
                    "originalCreationDate": "Wednesday December 27,2023 3:42 AM GMT",
                    "viewCount": 0,
                    "importDate": "Wednesday December 27,2023 3:43 AM GMT",
                }
            ],
        )

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            csv_files, _, _ = processor._collect_csv_inputs(self.takeout_root)
            rows = processor._load_photo_details_rows(csv_files)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["chosen_dt"], datetime(2023, 12, 27, 3, 42, 0))

    def test_parse_exiftool_datetime_keeps_explicit_year(self):
        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            parsed = processor._parse_exiftool_datetime("2023:12:27 03:42:00")

        self.assertEqual(parsed, datetime(2023, 12, 27, 3, 42, 0))

    def test_organize_files_by_date_does_not_log_exif_warning_for_png_files(self):
        png_folder = self.base_path / "pngs"
        png_folder.mkdir(parents=True, exist_ok=True)
        png_path = png_folder / "IMG_0001.PNG"
        png_path.write_bytes(b"not-a-real-png-but-good-enough-for-mtime")

        with patch.object(google_takeout_module, "LOGGER", Mock()) as logger_mock:
            google_takeout_module.organize_files_by_date(str(png_folder), type="year")

        warning_messages = " ".join(str(call.args[0]) for call in logger_mock.warning.call_args_list if call.args)
        self.assertNotIn("Error reading EXIF", warning_messages)

    def test_apply_dates_does_not_pre_read_embedded_exif_dates(self):
        photos_folder = self.takeout_root / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        source_file = photos_folder / "IMG_0001.JPG"
        source_file.write_bytes(b"jpeg-bytes")
        output_folder = self.base_path / "output"
        output_folder.mkdir(parents=True, exist_ok=True)
        dest_file = output_folder / "IMG_0001.JPG"
        dest_file.write_bytes(b"jpeg-bytes")

        row = {
            "chosen_dt": datetime(2023, 5, 14, 3, 36, 0),
            "source_csv": str(photos_folder / "Photo Details.csv"),
            "checksum": "",
            "favorite": "no",
            "hidden": "no",
            "deleted": "no",
        }
        records = [{"source": source_file, "dest": dest_file}]

        with (
            patch.object(icloud_module, "ARGS", _args(self.base_path / "output")),
            patch.object(icloud_module, "LOGGER", Mock()),
        ):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            with (
                patch.object(processor, "_exiftool_embedded_dates_match", side_effect=AssertionError("pre-read should be disabled")),
                patch.object(processor, "_write_exif_with_exiftool", return_value=True),
                patch.object(processor, "_filesystem_dates_match", return_value=False),
                patch.object(icloud_module, "update_file_timestamps", return_value=None),
            ):
                extracted = processor._apply_dates([(row, records)])

        self.assertIn(dest_file.resolve().as_posix(), extracted)

    def test_apply_dates_uses_only_exiftool_when_native_preference_is_disabled(self):
        photos_folder = self.takeout_root / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        source_file = photos_folder / "IMG_0001.JPG"
        source_file.write_bytes(b"jpeg-bytes")
        output_folder = self.base_path / "output"
        output_folder.mkdir(parents=True, exist_ok=True)
        dest_file = output_folder / "IMG_0001.JPG"
        dest_file.write_bytes(b"jpeg-bytes")

        row = {
            "chosen_dt": datetime(2023, 5, 14, 3, 36, 0),
            "source_csv": str(photos_folder / "Photo Details.csv"),
            "checksum": "",
            "favorite": "no",
            "hidden": "no",
            "deleted": "no",
        }
        records = [{"source": source_file, "dest": dest_file}]

        args = _args(self.base_path / "output")
        args["icloud-prefer-native-exif-writer"] = False
        with (
            patch.object(icloud_module, "ARGS", args),
            patch.object(icloud_module, "LOGGER", Mock()),
        ):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            with (
                patch.object(processor, "_write_photo_exif_natively", side_effect=AssertionError("native writer should not be used")),
                patch.object(processor, "_write_exif_with_exiftool", return_value=True) as exiftool_mock,
                patch.object(processor, "_filesystem_dates_match", return_value=True),
            ):
                processor._apply_dates([(row, records)])

        exiftool_mock.assert_called_once()

    def test_apply_dates_prefers_native_writer_when_enabled(self):
        photos_folder = self.takeout_root / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        source_file = photos_folder / "IMG_0001.JPG"
        source_file.write_bytes(b"jpeg-bytes")
        output_folder = self.base_path / "output"
        output_folder.mkdir(parents=True, exist_ok=True)
        dest_file = output_folder / "IMG_0001.JPG"
        dest_file.write_bytes(b"jpeg-bytes")

        row = {
            "chosen_dt": datetime(2023, 5, 14, 3, 36, 0),
            "source_csv": str(photos_folder / "Photo Details.csv"),
            "checksum": "",
            "favorite": "no",
            "hidden": "no",
            "deleted": "no",
        }
        records = [{"source": source_file, "dest": dest_file}]

        args = _args(self.base_path / "output")
        args["icloud-prefer-native-exif-writer"] = True
        with (
            patch.object(icloud_module, "ARGS", args),
            patch.object(icloud_module, "LOGGER", Mock()),
        ):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            with (
                patch.object(processor, "_write_photo_exif_natively", return_value=True) as native_mock,
                patch.object(processor, "_write_exif_with_exiftool", return_value=True) as exiftool_mock,
                patch.object(processor, "_filesystem_dates_match", return_value=True),
            ):
                processor._apply_dates([(row, records)])

        native_mock.assert_called_once()
        exiftool_mock.assert_not_called()

    def test_apply_dates_marks_multi_match_rows_as_ambiguous_without_writing_dates(self):
        photos_a = self.takeout_root / "PartA" / "Photos"
        photos_b = self.takeout_root / "PartB" / "Photos"
        photos_a.mkdir(parents=True, exist_ok=True)
        photos_b.mkdir(parents=True, exist_ok=True)
        source_a = photos_a / "IMG_0001.JPG"
        source_b = photos_b / "IMG_0001.JPG"
        source_a.write_bytes(b"a")
        source_b.write_bytes(b"b")

        output_folder = self.base_path / "output"
        output_folder.mkdir(parents=True, exist_ok=True)
        dest_a = output_folder / "IMG_0001.JPG"
        dest_b = output_folder / "IMG_0001 (2).JPG"
        dest_a.write_bytes(b"a")
        dest_b.write_bytes(b"b")

        row = {
            "chosen_dt": datetime(2023, 5, 14, 3, 36, 0),
            "source_csv": str(photos_a / "Photo Details.csv"),
            "checksum": "",
            "favorite": "no",
            "hidden": "no",
            "deleted": "no",
        }
        records = [{"source": source_a, "dest": dest_a}, {"source": source_b, "dest": dest_b}]

        with (
            patch.object(icloud_module, "ARGS", _args(self.base_path / "output")),
            patch.object(icloud_module, "LOGGER", Mock()),
        ):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            with (
                patch.object(processor, "_write_photo_exif_natively", side_effect=AssertionError("should not write ambiguous rows")),
                patch.object(processor, "_write_exif_with_exiftool", side_effect=AssertionError("should not write ambiguous rows")),
            ):
                extracted = processor._apply_dates([(row, records)])

        self.assertEqual(extracted, {})
        self.assertEqual(processor._last_date_application_report["rows_matched_to_multiple_media_files"], 1)
        self.assertEqual(
            processor._last_date_application_report["ambiguous_destinations"],
            {dest_a.resolve().as_posix(), dest_b.resolve().as_posix()},
        )

    def test_unknown_date_assets_are_bucketed_into_no_csv_and_ambiguous_folders(self):
        photos_folder = self.takeout_root / "Photos"
        photos_folder.mkdir(parents=True, exist_ok=True)
        dated_source = photos_folder / "IMG_0001.JPG"
        unmatched_source = photos_folder / "IMG_0002.JPG"
        ambiguous_source = photos_folder / "IMG_0003.JPG"
        dated_source.write_bytes(b"dated")
        unmatched_source.write_bytes(b"unmatched")
        ambiguous_source.write_bytes(b"ambiguous")

        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            source_records, source_index = processor._stage_original_assets(self.takeout_root)
            dated_record = source_index["by_name"][processor._normalized_name("IMG_0001.JPG")][0]
            ambiguous_record = source_index["by_name"][processor._normalized_name("IMG_0003.JPG")][0]
            extracted_dates = {
                Path(dated_record["dest"]).resolve().as_posix(): {
                    "SourceFile": str(dated_source),
                    "TargetFile": Path(dated_record["dest"]).resolve().as_posix(),
                    "OldestDate": "2023-05-14 03:36:00",
                    "Source": "test",
                }
            }
            processor._last_date_application_report = {
                "rows_without_matching_media": 0,
                "rows_matched_to_multiple_media_files": 1,
                "ambiguous_destinations": {Path(ambiguous_record["dest"]).resolve().as_posix()},
            }
            updated_index = processor._move_unknown_date_assets(source_records, extracted_dates)

        no_csv_path = (
            self.base_path / "output" / "ALL_PHOTOS" / "Unknown Date" / "No CSV Match" / "IMG_0002.JPG"
        )
        ambiguous_path = (
            self.base_path / "output" / "ALL_PHOTOS" / "Unknown Date" / "Ambiguous Match" / "IMG_0003.JPG"
        )
        dated_path = self.base_path / "output" / "ALL_PHOTOS" / "IMG_0001.JPG"

        self.assertTrue(no_csv_path.exists())
        self.assertTrue(ambiguous_path.exists())
        self.assertTrue(dated_path.exists())
        self.assertEqual(no_csv_path.read_bytes(), b"unmatched")
        self.assertEqual(ambiguous_path.read_bytes(), b"ambiguous")
        self.assertEqual(
            Path(updated_index["by_name"][processor._normalized_name("IMG_0002.JPG")][0]["dest"]).resolve(),
            no_csv_path.resolve(),
        )
        self.assertEqual(
            Path(updated_index["by_name"][processor._normalized_name("IMG_0003.JPG")][0]["dest"]).resolve(),
            ambiguous_path.resolve(),
        )


if __name__ == "__main__":
    unittest.main()
