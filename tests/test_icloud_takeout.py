import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import Features.ICloudTakeout.ClassICloudTakeoutFolder as icloud_module
except ModuleNotFoundError as exc:
    icloud_module = exc


def _args(output_folder):
    return {
        "output-folder": str(output_folder),
        "icloud-output-folder-suffix": "processed",
        "icloud-albums-folders-structure": "flatten",
        "icloud-no-albums-folders-structure": "flatten",
        "icloud-no-symbolic-albums": True,
        "icloud-include-memories": False,
    }


class TestICloudTakeout(unittest.TestCase):
    def setUp(self):
        if isinstance(icloud_module, ModuleNotFoundError):
            self.skipTest(f"iCloud Takeout dependencies are not installed in this environment: {icloud_module}")
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
            created = processor._build_collection_from_csvs(
                csv_files=album_csvs,
                source_index=source_index,
                root_folder=processor.albums_folder,
                structure="flatten",
            )

        self.assertEqual(created, 2)
        trip_a_files = sorted(path.read_bytes() for path in (self.base_path / "output" / "Albums" / "Trip A").iterdir())
        trip_b_files = sorted(path.read_bytes() for path in (self.base_path / "output" / "Albums" / "Trip B").iterdir())
        self.assertEqual(trip_a_files, [b"scope-a"])
        self.assertEqual(trip_b_files, [b"scope-b"])

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

    def test_photo_native_exif_state_detects_matching_dates(self):
        with patch.object(icloud_module, "ARGS", _args(self.base_path / "output")):
            processor = icloud_module.ClassICloudTakeoutFolder(str(self.takeout_root))
            dt_value = datetime(2023, 5, 14, 3, 36, 0)
            exif_bytes = b"2023:05:14 03:36:00"

            fake_exif = {
                "0th": {icloud_module.piexif.ImageIFD.DateTime: exif_bytes},
                "Exif": {
                    icloud_module.piexif.ExifIFD.DateTimeOriginal: exif_bytes,
                    icloud_module.piexif.ExifIFD.DateTimeDigitized: exif_bytes,
                },
            }

            with patch.object(icloud_module.piexif, "load", return_value=fake_exif):
                state = processor._photo_native_exif_state(Path("/tmp/example.jpg"), dt_value)

        self.assertIsNotNone(state)
        self.assertTrue(state["supported"])
        self.assertTrue(state["matches"])


if __name__ == "__main__":
    unittest.main()
