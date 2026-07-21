import os
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

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

if "halo" not in sys.modules:
    halo_stub = types.ModuleType("halo")
    halo_stub.Halo = object
    sys.modules["halo"] = halo_stub

if "tabulate" not in sys.modules:
    tabulate_stub = types.ModuleType("tabulate")
    tabulate_stub.tabulate = lambda *args, **kwargs: ""
    sys.modules["tabulate"] = tabulate_stub

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

if "tzlocal" not in sys.modules:
    tzlocal_stub = types.ModuleType("tzlocal")
    tzlocal_stub.get_localzone = lambda: None
    sys.modules["tzlocal"] = tzlocal_stub

from requests_toolbelt.multipart.encoder import MultipartEncoder

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos


class TestImmichStreamingUpload(unittest.TestCase):
    def _build_manager(self):
        manager = ClassImmichPhotos.__new__(ClassImmichPhotos)
        manager.ALLOWED_IMMICH_MEDIA_EXTENSIONS = [".jpg"]
        manager.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = [".xmp"]
        manager.IMMICH_URL = "http://immich.local"
        manager.API_KEY_LOGIN = True
        manager.IMMICH_USER_API_KEY = "test-api-key"
        manager.SESSION_TOKEN = None
        manager.HEADERS_WITH_CREDENTIALS = {"x-api-key": "test-api-key"}
        manager.login = lambda log_level=None: True
        return manager

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.tqdm", side_effect=lambda iterable, **kwargs: iterable)
    def test_remove_duplicates_by_name_and_size_keeps_oldest_upload(self, _mock_tqdm, _mock_logger):
        manager = self._build_manager()
        manager._get_all_assets_unfiltered = MagicMock(return_value=[
            {
                "id": "old", "originalFileName": "IMG_0001.JPG",
                "createdAt": "2020-01-01T00:00:00.000Z", "exifInfo": {"fileSize": 42},
            },
            {
                "id": "new", "originalFileName": "IMG_0001.JPG",
                "createdAt": "2021-01-01T00:00:00.000Z", "exifInfo": {"fileSize": 42},
            },
            {
                "id": "other", "originalFileName": "IMG_0001.JPG",
                "createdAt": "2022-01-01T00:00:00.000Z", "exifInfo": {"fileSize": 99},
            },
        ])
        manager._hydrate_duplicate_group_metadata = MagicMock(side_effect=lambda group, log_level=None: group)
        manager._merge_duplicate_asset_metadata = MagicMock(return_value=True)
        manager.remove_assets = MagicMock(side_effect=lambda ids, log_level=None: len(ids))

        removed, groups_found, groups_skipped = manager.remove_duplicates_assets_by_name_and_size("oldest")

        self.assertEqual((removed, groups_found, groups_skipped), (1, 1, 0))
        keeper, redundant = manager._merge_duplicate_asset_metadata.call_args.args[:2]
        self.assertEqual(keeper["id"], "old")
        self.assertEqual([asset["id"] for asset in redundant], ["new"])
        manager.remove_assets.assert_called_once_with(["new"], log_level=None)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_group_metadata_is_loaded_only_for_candidates(self, mock_get, _mock_logger):
        manager = self._build_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "asset-1", "people": []}
        mock_get.return_value = response

        metadata = manager._get_duplicate_asset_metadata("asset-1")

        self.assertEqual(metadata, {"id": "asset-1", "people": []})
        mock_get.assert_called_once_with(
            "http://immich.local/api/assets/asset-1",
            headers=manager.HEADERS_WITH_CREDENTIALS,
            verify=False,
        )

    def test_duplicate_asset_size_prefers_immich_file_size_in_byte(self):
        manager = self._build_manager()

        self.assertEqual(
            manager._duplicate_asset_size({"exifInfo": {"fileSizeInByte": "12345"}}),
            12345,
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.tqdm")
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    def test_unfiltered_inventory_fetches_known_pages_in_parallel(self, _mock_logger, mock_post, mock_tqdm):
        manager = self._build_manager()
        manager._get_unfiltered_asset_inventory_total = MagicMock(return_value=2500)
        progress_bar = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = progress_bar

        def metadata_page_response(_url, headers, data, verify):
            self.assertEqual(headers, manager.HEADERS_WITH_CREDENTIALS)
            self.assertFalse(verify)
            page_number = json.loads(data)["page"]
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "assets": {"items": [{"id": f"asset-{page_number}"}]},
            }
            return response

        mock_post.side_effect = metadata_page_response

        assets = manager._get_all_assets_unfiltered(show_progress=True)

        self.assertEqual([asset["id"] for asset in assets], ["asset-1", "asset-2", "asset-3"])
        self.assertEqual(mock_post.call_count, 3)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_native_duplicate_detection_preserves_immich_quality_suggestion(self, mock_get, _mock_logger):
        manager = self._build_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [{
            "duplicateId": "duplicate-group-1",
            "suggestedKeepAssetIds": ["large"],
            "assets": [
                {"id": "small", "originalFileName": "IMG.JPG", "exifInfo": {"fileSizeInByte": 10}},
                {"id": "large", "originalFileName": "IMG-copy.JPG", "exifInfo": {"fileSizeInByte": 20}},
            ],
        }]
        mock_get.return_value = response

        groups = manager.find_duplicate_assets_by_immich_detection()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0]["_immich_duplicate_id"], "duplicate-group-1")
        self.assertEqual(groups[0][0]["_immich_suggested_keep_asset_ids"], ["large"])
        self.assertEqual(manager._select_duplicate_asset_keeper(groups[0], "better-quality")["id"], "large")
        mock_get.assert_called_once_with(
            "http://immich.local/api/duplicates",
            headers=manager.HEADERS_WITH_CREDENTIALS,
            verify=False,
            timeout=manager.IMMICH_DUPLICATES_TIMEOUT,
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    def test_merge_duplicate_metadata_proceeds_when_unassigned_faces_cannot_be_transferred(self, _mock_logger):
        manager = self._build_manager()
        keeper = {"id": "keeper", "originalFileName": "IMG.JPG", "unassignedFaces": [{"id": "face-1"}]}
        duplicate = {"id": "duplicate", "originalFileName": "IMG.JPG"}

        self.assertTrue(manager._merge_duplicate_asset_metadata(keeper, [duplicate]))

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_merge_duplicate_metadata_copies_only_missing_assigned_faces(
        self, mock_get, mock_post, _mock_logger
    ):
        manager = self._build_manager()
        keeper = {
            "id": "keeper", "originalFileName": "IMG.JPG", "width": 1000, "height": 500,
            "checksum": "same-content", "people": [{"id": "person-1"}],
        }
        duplicate = {
            "id": "duplicate", "originalFileName": "IMG.JPG", "width": 1000, "height": 500,
            "checksum": "same-content", "people": [{"id": "person-1"}, {"id": "person-2"}],
        }

        def face_response(faces):
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = faces
            return response

        mock_get.side_effect = [
            face_response([{
                "person": {"id": "person-1"}, "imageWidth": 1000, "imageHeight": 500,
                "boundingBoxX1": 0, "boundingBoxY1": 0,
                "boundingBoxX2": 100, "boundingBoxY2": 100,
            }]),
            face_response([
                {
                    "person": {"id": "person-1"}, "imageWidth": 1000, "imageHeight": 500,
                    "boundingBoxX1": 1, "boundingBoxY1": 1,
                    "boundingBoxX2": 101, "boundingBoxY2": 101,
                },
                {
                    "person": {"id": "person-2"}, "imageWidth": 1000, "imageHeight": 500,
                    "boundingBoxX1": 500, "boundingBoxY1": 100,
                    "boundingBoxX2": 700, "boundingBoxY2": 400,
                },
            ]),
        ]
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        self.assertTrue(manager._merge_duplicate_asset_metadata(keeper, [duplicate]))

        self.assertEqual(
            [call.kwargs["params"] for call in mock_get.call_args_list],
            [{"id": "keeper"}, {"id": "duplicate"}],
        )
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.args[0], "http://immich.local/api/faces")
        self.assertEqual(
            json.loads(mock_post.call_args.kwargs["data"]),
            {
                "assetId": "keeper", "personId": "person-2", "imageWidth": 1000,
                "imageHeight": 500, "x": 500, "y": 100,
                "width": 200, "height": 300,
            },
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.put")
    def test_merge_duplicate_metadata_preserves_visibility_date_and_location(
        self, mock_put, _mock_logger
    ):
        manager = self._build_manager()
        manager._merge_duplicate_asset_faces = MagicMock(return_value=True)
        manager._merge_duplicate_asset_stacks = MagicMock(return_value=True)
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_put.return_value = response
        keeper = {
            "id": "keeper", "originalFileName": "IMG.JPG", "visibility": "TIMELINE",
        }
        duplicate = {
            "id": "duplicate", "originalFileName": "IMG.JPG", "isArchived": True,
            "visibility": "ARCHIVE",
            "exifInfo": {
                "dateTimeOriginal": "2020-01-02T03:04:05.000Z",
                "latitude": 40.4168, "longitude": -3.7038,
            },
        }

        self.assertTrue(manager._merge_duplicate_asset_metadata(keeper, [duplicate]))

        self.assertEqual(mock_put.call_args.args[0], "http://immich.local/api/assets")
        self.assertEqual(
            json.loads(mock_put.call_args.kwargs["data"]),
            {
                "ids": ["keeper"], "visibility": "ARCHIVE",
                "dateTimeOriginal": "2020-01-02T03:04:05.000Z",
                "latitude": 40.4168, "longitude": -3.7038,
            },
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.put")
    def test_merge_duplicate_metadata_does_not_copy_conflicting_location(
        self, mock_put, _mock_logger
    ):
        manager = self._build_manager()
        manager._merge_duplicate_asset_faces = MagicMock(return_value=True)
        manager._merge_duplicate_asset_stacks = MagicMock(return_value=True)
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_put.return_value = response
        keeper = {"id": "keeper", "originalFileName": "IMG.JPG"}
        duplicates = [
            {"id": "duplicate-1", "exifInfo": {"latitude": 40.4168, "longitude": -3.7038}},
            {"id": "duplicate-2", "exifInfo": {"latitude": 41.3874, "longitude": 2.1686}},
        ]

        self.assertTrue(manager._merge_duplicate_asset_metadata(keeper, duplicates))

        self.assertFalse(mock_put.called)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_merge_duplicate_stacks_recreates_stack_with_keeper_and_survivors(
        self, mock_get, mock_post, _mock_logger
    ):
        manager = self._build_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"assets": [{"id": "duplicate"}, {"id": "other"}]}
        mock_get.return_value = response
        mock_post.return_value = response
        keeper = {"id": "keeper", "stack": None}
        duplicate = {"id": "duplicate", "stack": {"id": "stack-1"}}

        self.assertTrue(manager._merge_duplicate_asset_stacks(keeper, [duplicate]))

        mock_get.assert_called_once_with(
            "http://immich.local/api/stacks/stack-1",
            headers=manager.HEADERS_WITH_CREDENTIALS,
            verify=False,
        )
        mock_post.assert_called_once_with(
            "http://immich.local/api/stacks",
            headers=manager.HEADERS_WITH_CREDENTIALS,
            data=json.dumps({"assetIds": ["keeper", "other"]}),
            verify=False,
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_display_names_resolves_album_tag_and_person_names(self, mock_get, _mock_logger):
        manager = self._build_manager()

        def response(records):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = records
            return result

        mock_get.side_effect = [
            response([{"id": "album-1", "albumName": "Summer 2003"}]),
            response([{"id": "tag-1", "value": "family/yoli"}]),
            response({"people": [{"id": "person-1", "name": "Yoli"}], "hasNextPage": False}),
        ]
        names = manager.get_duplicate_metadata_display_names([[
            {
                "albums": [{"id": "album-1"}], "tags": [{"id": "tag-1"}],
                "people": [{"id": "face-1", "person": {"id": "person-1"}}],
            },
        ]])

        self.assertEqual(
            names,
            {"albums": {"album-1": "Summer 2003"}, "tags": {"tag-1": "family/yoli"}, "people": {"person-1": "Yoli"}},
        )
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(
            mock_get.call_args_list[2].kwargs["params"],
            {"page": 1, "size": 1000, "withHidden": True},
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_display_names_falls_back_to_candidate_person_lookup(self, mock_get, _mock_logger):
        manager = self._build_manager()

        def response(records):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = records
            return result

        mock_get.side_effect = [
            response([]),
            response([]),
            response({"people": [], "hasNextPage": False}),
            response({"id": "person-1", "name": "Yoli"}),
        ]
        names = manager.get_duplicate_metadata_display_names([[
            {"people": [{"personId": "person-1"}]},
        ]])

        self.assertEqual(names["people"], {"person-1": "Yoli"})
        self.assertEqual(mock_get.call_args_list[3].args[0], "http://immich.local/api/people/person-1")

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_display_names_retries_legacy_people_pagination(self, mock_get, _mock_logger):
        manager = self._build_manager()

        rejected = MagicMock()
        rejected.raise_for_status.side_effect = requests.HTTPError("400 bad request")

        def response(records):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = records
            return result

        mock_get.side_effect = [
            response([]),
            response([]),
            rejected,
            response({"people": [{"id": "person-1", "name": "Yoli"}], "hasNextPage": False}),
        ]
        names = manager.get_duplicate_metadata_display_names()

        self.assertEqual(names["people"], {"person-1": "Yoli"})
        self.assertEqual(mock_get.call_args_list[3].kwargs["params"], {"page": 1})

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_hydration_loads_album_memberships(self, mock_get, _mock_logger):
        manager = self._build_manager()

        def response(data):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = data
            return result

        mock_get.side_effect = [
            response({"id": "asset-1", "originalFileName": "IMG.JPG"}),
            response([{"id": "album-1", "albumName": "Summer 2003"}]),
        ]

        hydrated = manager._hydrate_duplicate_group_metadata([{"id": "asset-1"}])

        self.assertEqual(hydrated[0]["albums"], [{"id": "album-1", "albumName": "Summer 2003"}])
        self.assertEqual(
            mock_get.call_args_list[1].kwargs["params"], {"assetId": "asset-1"},
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_hydration_resolves_people_through_faces(self, mock_get, _mock_logger):
        manager = self._build_manager()

        def response(data):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = data
            return result

        mock_get.side_effect = [
            response({"id": "asset-1", "people": [{"id": "person-1"}]}),
            response([{"id": "face-1", "person": {"id": "person-1", "name": "Yoli"}}]),
            response([]),
        ]

        hydrated = manager._hydrate_duplicate_asset_metadata({"id": "asset-1"})

        self.assertEqual(hydrated["people"], [{"id": "person-1", "name": "Yoli"}])
        self.assertEqual(mock_get.call_args_list[1].args[0], "http://immich.local/api/faces")
        self.assertEqual(mock_get.call_args_list[1].kwargs["params"], {"id": "asset-1"})

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_duplicate_metadata_hydration_resolves_scalar_people_ids_through_faces(self, mock_get, _mock_logger):
        manager = self._build_manager()

        def response(data):
            result = MagicMock()
            result.raise_for_status.return_value = None
            result.json.return_value = data
            return result

        mock_get.side_effect = [
            response({"id": "asset-1", "people": ["person-1"]}),
            response([{"id": "face-1", "person": {"id": "person-1", "name": "Yoli"}}]),
            response([]),
        ]

        hydrated = manager._hydrate_duplicate_asset_metadata({"id": "asset-1"})

        self.assertEqual(hydrated["people"], [{"id": "person-1", "name": "Yoli"}])

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_immich_native_duplicate_resolution_uses_selected_keeper(self, mock_post, _mock_logger):
        manager = self._build_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        mock_post.return_value = response
        duplicate_groups = [[
            {"id": "small", "_immich_duplicate_id": "group-1", "exifInfo": {"fileSize": 1}},
            {"id": "large", "_immich_duplicate_id": "group-1", "exifInfo": {"fileSize": 2}},
        ]]

        removed, found, skipped = manager.resolve_duplicate_asset_groups_with_immich(
            duplicate_groups, keeper_strategy="better-quality",
        )

        self.assertEqual((removed, found, skipped), (1, 1, 0))
        mock_post.assert_called_once_with(
            "http://immich.local/api/duplicates/resolve",
            headers=manager.HEADERS_WITH_CREDENTIALS,
            data=json.dumps({"groups": [{
                "duplicateId": "group-1", "keepAssetIds": ["large"], "trashAssetIds": ["small"],
            }]}),
            verify=False,
            timeout=manager.IMMICH_DUPLICATES_TIMEOUT,
        )

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_uses_streaming_multipart_without_files_arg(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "asset-id", "status": "created"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "asset-id")
        self.assertFalse(is_duplicated)

        kwargs = mock_post.call_args.kwargs
        self.assertNotIn("files", kwargs)
        self.assertIsInstance(kwargs["data"], MultipartEncoder)
        self.assertIn("multipart/form-data", kwargs["headers"]["Content-Type"])

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_attaches_sidecar_in_multipart_fields(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "asset-id", "status": "created"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            sidecar_path = os.path.join(tmpdir, "photo.xmp")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")
            with open(sidecar_path, "wb") as f:
                f.write(b"sidecar-data")

            manager.push_asset(asset_path)

        encoder = mock_post.call_args.kwargs["data"]
        self.assertIn("sidecarData", encoder.fields)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_returns_existing_id_for_duplicate_response(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "existing-asset-id", "status": "duplicate"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "existing-asset-id")
        self.assertTrue(is_duplicated)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_rejects_duplicate_response_without_existing_id(
        self, mock_post, mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "duplicate"}
        search_response = MagicMock()
        search_response.raise_for_status.return_value = None
        search_response.json.return_value = {"assets": {"items": [], "nextPage": None}}
        mock_post.side_effect = [response, search_response]

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertIsNone(asset_id)
        self.assertIsNone(is_duplicated)
        mock_logger.error.assert_called()

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_resolves_existing_id_from_remote_search_for_preexisting_duplicate(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        duplicate_response = MagicMock()
        duplicate_response.raise_for_status.return_value = None
        duplicate_response.json.return_value = {"status": "duplicate"}

        search_response = MagicMock()
        search_response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")
            mtime_iso = datetime.fromtimestamp(
                os.path.getmtime(asset_path),
                tz=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            search_response.json.return_value = {
                "assets": {
                    "items": [
                        {
                            "id": "remote-existing-id",
                            "originalFileName": "photo.jpg",
                            "fileCreatedAt": mtime_iso,
                            "exifInfo": {"fileSize": len(b"binary-data")},
                        }
                    ],
                    "nextPage": None,
                }
            }
            mock_post.side_effect = [duplicate_response, search_response]

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "remote-existing-id")
        self.assertTrue(is_duplicated)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_reuses_cached_existing_id_for_duplicate_response_without_id(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"status": "duplicate"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")
            manager._remember_uploaded_asset_id(asset_path, "cached-asset-id")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "cached-asset-id")
        self.assertTrue(is_duplicated)


if __name__ == "__main__":
    unittest.main()
