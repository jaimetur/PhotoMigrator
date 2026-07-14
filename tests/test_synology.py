import os
import sys
import tempfile
import types
import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "piexif" not in sys.modules:
    piexif_stub = types.ModuleType("piexif")
    piexif_stub.ExifIFD = types.SimpleNamespace(DateTimeOriginal=36867, DateTimeDigitized=36868)
    piexif_stub.ImageIFD = types.SimpleNamespace(DateTime=306)
    piexif_stub.load = lambda *args, **kwargs: {"0th": {}, "Exif": {}}
    piexif_stub.dump = lambda *args, **kwargs: b""
    piexif_stub.insert = lambda *args, **kwargs: None
    sys.modules["piexif"] = piexif_stub

if "colorama" not in sys.modules:
    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(RED="", GREEN="", YELLOW="", CYAN="", WHITE="", BLUE="", MAGENTA="")
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="", DIM="", NORMAL="")
    sys.modules["colorama"] = colorama_stub

if "dateutil" not in sys.modules:
    dateutil_stub = types.ModuleType("dateutil")
    dateutil_parser_stub = types.ModuleType("dateutil.parser")
    dateutil_parser_stub.parse = lambda value, *args, **kwargs: value
    dateutil_stub.parser = dateutil_parser_stub
    sys.modules["dateutil"] = dateutil_stub
    sys.modules["dateutil.parser"] = dateutil_parser_stub

if "requests_toolbelt" not in sys.modules:
    requests_toolbelt_stub = types.ModuleType("requests_toolbelt")
    requests_toolbelt_multipart_stub = types.ModuleType("requests_toolbelt.multipart")
    requests_toolbelt_encoder_stub = types.ModuleType("requests_toolbelt.multipart.encoder")

    class _DummyMultipartEncoder:
        def __init__(self, *args, **kwargs):
            self.fields = kwargs.get("fields", {})
            self.content_type = "multipart/form-data; boundary=test"

    requests_toolbelt_encoder_stub.MultipartEncoder = _DummyMultipartEncoder
    requests_toolbelt_multipart_stub.encoder = requests_toolbelt_encoder_stub
    requests_toolbelt_stub.multipart = requests_toolbelt_multipart_stub
    sys.modules["requests_toolbelt"] = requests_toolbelt_stub
    sys.modules["requests_toolbelt.multipart"] = requests_toolbelt_multipart_stub
    sys.modules["requests_toolbelt.multipart.encoder"] = requests_toolbelt_encoder_stub

from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos


class TestSynologyPhotosUnit(unittest.TestCase):
    def setUp(self):
        self.manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)

    def test_filter_assets_by_type_supports_photo_aliases_and_live_assets(self):
        assets = [
            {"id": "1", "type": "PHOTO"},
            {"id": "2", "type": "LIVE"},
            {"id": "3", "type": "VIDEO"},
        ]

        filtered = self.manager.filter_assets_by_type(assets, "photos")

        self.assertEqual([asset["id"] for asset in filtered], ["1", "2"])

    def test_filter_assets_by_date_respects_epoch_range(self):
        assets = [
            {"id": "old", "time": 100},
            {"id": "inside", "time": 200},
            {"id": "new", "time": 300},
        ]

        filtered = self.manager.filter_assets_by_date(assets, from_date=150, to_date=250)

        self.assertEqual([asset["id"] for asset in filtered], ["inside"])

    def test_filter_assets_by_place_matches_nested_address_values(self):
        assets = [
            {"id": "1", "additional": {"address": {"city": "Madrid"}}},
            {"id": "2", "additional": {"address": {"country": "Spain"}}},
            {"id": "3", "additional": {"address": {"city": "Berlin"}}},
        ]

        filtered = self.manager.filter_assets_by_place(assets, "spa")

        self.assertEqual([asset["id"] for asset in filtered], ["2"])

    def _prepare_push_manager(self):
        manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)
        manager.ALLOWED_MEDIA_EXTENSIONS = [".jpg"]
        manager.ALLOWED_SIDECAR_EXTENSIONS = [".xmp"]
        manager.SYNOLOGY_URL = "http://synology.local"
        manager.SYNO_TOKEN_HEADER = {}
        manager.SESSION = MagicMock()
        manager.login = lambda log_level=None: True
        return manager

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_returns_existing_id_for_duplicate_response(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"id": "existing-asset-id", "action": "ignore"},
        }
        manager.SESSION.post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "existing-asset-id")
        self.assertTrue(is_duplicated)

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_rejects_duplicate_response_without_existing_id(self, mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"action": "ignore"},
        }
        manager.SESSION.post.return_value = response
        search_response = MagicMock()
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {"success": True, "data": {"list": []}}
        manager.SESSION.get.return_value = search_response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertIsNone(asset_id)
        self.assertIsNone(is_duplicated)
        mock_logger.warning.assert_called()

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_resolves_existing_id_from_remote_search_for_preexisting_duplicate(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"action": "ignore"},
        }
        manager.SESSION.post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")

            search_response = MagicMock()
            search_response.raise_for_status.return_value = None
            search_response.json.return_value = {
                "success": True,
                "data": {
                    "list": [
                        {
                            "id": "remote-existing-id",
                            "filename": "photo.jpg",
                            "time": int(os.path.getmtime(asset_path)),
                            "filesize": len(b"binary-data"),
                        }
                    ]
                },
            }
            manager.SESSION.get.return_value = search_response

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "remote-existing-id")
        self.assertTrue(is_duplicated)

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_reuses_cached_existing_id_for_duplicate_response_without_id(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"action": "ignore"},
        }
        manager.SESSION.post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")
            manager._remember_uploaded_asset_id(asset_path, "cached-asset-id")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "cached-asset-id")
        self.assertTrue(is_duplicated)

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_add_assets_to_album_treats_duplicate_failure_as_already_associated(self, mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": False,
            "error": {"code": 123, "message": "Asset already exists in album"},
        }
        manager.SESSION.get.return_value = response

        added = manager.add_assets_to_album("album-1", "asset-1", album_name="Album")

        self.assertEqual(added, 1)
        mock_logger.warning.assert_not_called()

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_add_assets_to_album_serializes_item_as_json_array(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"success": True}
        manager.SESSION.get.return_value = response

        added = manager.add_assets_to_album("album-1", ["123", "456"], album_name="Album")

        self.assertEqual(added, 2)
        params = manager.SESSION.get.call_args.kwargs["params"]
        self.assertEqual(json.loads(params["item"]), [123, 456])

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_add_assets_to_album_splits_large_requests_into_chunks(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"success": True}
        manager.SESSION.get.return_value = response

        asset_ids = [str(i) for i in range(1, 1003)]
        added = manager.add_assets_to_album("album-1", asset_ids, album_name="Album")

        self.assertEqual(added, 1002)
        self.assertEqual(manager.SESSION.get.call_count, 3)
        first_params = manager.SESSION.get.call_args_list[0].kwargs["params"]
        second_params = manager.SESSION.get.call_args_list[1].kwargs["params"]
        third_params = manager.SESSION.get.call_args_list[2].kwargs["params"]
        self.assertEqual(len(json.loads(first_params["item"])), 500)
        self.assertEqual(len(json.loads(second_params["item"])), 500)
        self.assertEqual(len(json.loads(third_params["item"])), 2)

    def test_is_shared_album_detects_sharing_info_without_passphrase(self):
        album = {
            "id": "shared-1",
            "albumName": "Album Shared",
            "additional": {
                "sharing_info": {
                    "permission": [{"role": "editor"}]
                }
            },
        }

        self.assertTrue(ClassSynologyPhotos.is_shared_album(album))

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_ensure_shared_album_access_populates_missing_passphrase_from_album_get(self, _mock_logger):
        manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)
        manager.SYNOLOGY_URL = "http://synology.local"
        manager.SYNO_TOKEN_HEADER = {}
        manager.SESSION = MagicMock()
        manager.login = lambda log_level=None: True

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {
                "album": {
                    "id": "shared-1",
                    "passphrase": "shared-passphrase",
                    "sharing_info": {"permission": [{"role": "editor"}]},
                }
            },
        }
        manager.SESSION.get.return_value = response

        album = {
            "id": "shared-1",
            "albumName": "Album Shared",
            "additional": {"sharing_info": {"permission": [{"role": "editor"}]}},
        }

        enriched = manager.ensure_shared_album_access(album, log_level=logging.INFO)

        self.assertEqual(enriched.get("passphrase"), "shared-passphrase")

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_get_all_assets_from_album_shared_scopes_listing_by_album_id(self, _mock_logger):
        manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)
        manager.SYNOLOGY_URL = "http://synology.local"
        manager.SYNO_TOKEN_HEADER = {}
        manager.SESSION = MagicMock()
        manager.login = lambda log_level=None: True
        manager.filter_assets = lambda assets, log_level=None: assets

        response = MagicMock()
        response.json.return_value = {
            "success": True,
            "data": {
                "list": [
                    {"id": "asset-1", "filename": "shared-1.jpg", "type": "PHOTO"},
                ]
            },
        }
        manager.SESSION.get.return_value = response

        assets = manager.get_all_assets_from_album_shared(
            album_id="album-shared-1",
            album_name="Shared Album",
            album_passphrase="shared-passphrase",
            log_level=logging.INFO,
        )

        self.assertEqual([asset["id"] for asset in assets], ["asset-1"])
        params = manager.SESSION.get.call_args.kwargs["params"]
        self.assertEqual(params["album_id"], "album-shared-1")
        self.assertEqual(params["passphrase"], "shared-passphrase")


if __name__ == "__main__":
    unittest.main()
