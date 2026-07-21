import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Features.GoogleTakeout.PeopleMetadata import build_people_map, load_people_map

try:
    from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
    IMMICH_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    ClassImmichPhotos = None
    IMMICH_IMPORT_ERROR = exc


class TestPeopleMetadata(unittest.TestCase):
    def test_same_filename_keeps_people_entries_separate_by_capture_time(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for folder, timestamp, person in (("one", "100", "Ana"), ("two", "200", "Luis")):
                sidecar = root / folder / "IMG_0001.jpg.json"
                sidecar.parent.mkdir()
                sidecar.write_text(json.dumps({
                    "title": "IMG_0001.jpg",
                    "photoTakenTime": {"timestamp": timestamp},
                    "people": [{"name": person}],
                }), encoding="utf-8")

            people_map = build_people_map(root)

        entries = people_map["img_0001.jpg"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["people"], ["Ana"])
        self.assertEqual(entries[1]["people"], ["Luis"])

    def test_load_people_map_collapses_album_copies_with_same_capture_time(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "takeout_people_metadata.json").write_text(json.dumps({
                "version": 2,
                "assets": {
                    "IMG_0001.jpg": [
                        {"people": ["Ana"], "taken_at": "100", "created_at": "110"},
                        {"people": ["Luis"], "taken_at": "100", "created_at": "120"},
                    ]
                },
            }), encoding="utf-8")

            people_map = load_people_map(temp_dir)

        self.assertEqual(people_map["img_0001.jpg"], [{
            "people": ["Ana", "Luis"], "taken_at": "100", "created_at": "110", "modified_at": ""
        }])

    def test_resolves_same_filename_using_media_capture_time(self):
        if IMMICH_IMPORT_ERROR is not None:
            self.skipTest(f"Immich dependencies are not installed: {IMMICH_IMPORT_ERROR}")
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = Path(temp_dir) / "IMG_0001.jpg"
            asset_path.touch()
            taken_at = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
            os.utime(asset_path, (taken_at.timestamp(), taken_at.timestamp()))
            client = ClassImmichPhotos.__new__(ClassImmichPhotos)
            client._takeout_people_map = {
                "IMG_0001.jpg": [
                    {"people": ["Ana"], "taken_at": "1577836800"},
                    {"people": ["Luis"], "modified_at": "1704164645"},
                ]
            }

            with patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock):
                entry = client._get_takeout_people_entry_for_asset(str(asset_path))

        self.assertEqual(entry["people"], ["Luis"])
