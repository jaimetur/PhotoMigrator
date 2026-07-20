import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


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

try:
    from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
    IMMICH_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    ClassImmichPhotos = None
    IMMICH_IMPORT_ERROR = exc


class TestImmichPhotosUnit(unittest.TestCase):
    def setUp(self):
        if IMMICH_IMPORT_ERROR is not None:
            self.skipTest(f"Immich dependencies are not installed in this environment: {IMMICH_IMPORT_ERROR}")
        self.manager = ClassImmichPhotos.__new__(ClassImmichPhotos)
        self.manager.IMMICH_URL = "http://immich.local"
        self.manager.HEADERS_WITH_CREDENTIALS = {"x-api-key": "test-key"}
        self.manager.login = lambda log_level=None: True

    def test_filter_assets_by_type_supports_aliases(self):
        assets = [
            {"id": "1", "type": "IMAGE"},
            {"id": "2", "type": "VIDEO"},
            {"id": "3", "type": "image"},
        ]

        filtered = self.manager.filter_assets_by_type(assets, "photos")

        self.assertEqual([asset["id"] for asset in filtered], ["1", "3"])

    def test_normalize_burst_stem_removes_common_suffixes(self):
        normalized = self.manager._normalize_burst_stem("IMG_1234-edited.BURST0001.jpg")
        self.assertEqual(normalized, "img_1234-edited")

    def test_resolve_existing_asset_id_indexes_cached_library_by_filename(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as asset_file:
            filename = Path(asset_file.name).name
            modified_at = datetime.fromtimestamp(Path(asset_file.name).stat().st_mtime, tz=timezone.utc)
            self.manager._lookup_uploaded_asset_id = lambda _: None
            self.manager._remember_uploaded_asset_id = lambda *_: None
            self.manager._get_all_assets_unfiltered = MagicMock(return_value=[
                {
                    "id": "remote-match",
                    "originalFileName": filename,
                    "fileCreatedAt": modified_at.isoformat().replace("+00:00", "Z"),
                    "exifInfo": {"fileSize": 0},
                },
                {
                    "id": "remote-other",
                    "originalFileName": "other.jpg",
                    "fileCreatedAt": modified_at.isoformat().replace("+00:00", "Z"),
                    "exifInfo": {"fileSize": 0},
                },
            ])

            resolved_id = self.manager._resolve_existing_asset_id(asset_file.name)

        self.assertEqual(resolved_id, "remote-match")
        self.assertIn(filename.casefold(), self.manager._existing_asset_name_index)

    def test_burst_primary_sort_key_prefers_image_then_larger_file(self):
        image_record = {"ext": ".jpg", "file_size": 300, "capture_epoch": 100}
        raw_record = {"ext": ".dng", "file_size": 500, "capture_epoch": 90}
        smaller_image = {"ext": ".jpg", "file_size": 200, "capture_epoch": 80}

        self.assertLess(
            self.manager._burst_primary_sort_key(image_record),
            self.manager._burst_primary_sort_key(raw_record),
        )
        self.assertLess(
            self.manager._burst_primary_sort_key(image_record),
            self.manager._burst_primary_sort_key(smaller_image),
        )

    def test_get_album_owner_id_prefers_owner_id_when_present(self):
        album = {
            "ownerId": "legacy-owner",
            "albumUsers": [{"role": "owner", "user": {"id": "new-owner"}}],
        }

        self.assertEqual(self.manager._get_album_owner_id(album), "legacy-owner")

    def test_get_album_owner_id_falls_back_to_album_users_owner(self):
        album = {
            "albumUsers": [
                {"role": "viewer", "user": {"id": "viewer"}},
                {"role": "owner", "user": {"id": "owner-from-v3"}},
            ]
        }

        self.assertEqual(self.manager._get_album_owner_id(album), "owner-from-v3")

    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_get_album_assets_via_search_paginates_and_coerces_page_to_int(self, mock_post):
        first_response = MagicMock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = {
            "assets": {
                "items": [{"id": "a1"}],
                "nextPage": "2",
            }
        }
        second_response = MagicMock()
        second_response.raise_for_status.return_value = None
        second_response.json.return_value = {
            "assets": {
                "items": [{"id": "a2"}],
                "nextPage": None,
            }
        }
        mock_post.side_effect = [first_response, second_response]

        assets = self.manager._get_album_assets_via_search("album-1")

        self.assertEqual([asset["id"] for asset in assets], ["a1", "a2"])
        first_payload = mock_post.call_args_list[0].kwargs["data"]
        second_payload = mock_post.call_args_list[1].kwargs["data"]
        self.assertIn('"page": 1', first_payload)
        self.assertIn('"page": 2', second_payload)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.has_any_filter", return_value=False)
    @patch.object(ClassImmichPhotos, "_get_album_assets_via_search")
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_get_all_assets_from_album_falls_back_to_search_when_inline_assets_missing(
        self, mock_get, mock_search, _mock_filters
    ):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "album-1", "albumName": "Trip"}
        mock_get.return_value = response
        mock_search.return_value = [{"id": "asset-1", "fileCreatedAt": "2026-07-06T12:00:00Z", "originalFileName": "photo.jpg"}]

        assets = self.manager.get_all_assets_from_album("album-1", "Trip")

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["time"], "2026-07-06T12:00:00Z")
        self.assertEqual(assets[0]["filename"], "photo.jpg")
        mock_search.assert_called_once_with("album-1", log_level=None)

    @patch("Features.ImmichPhotos.ClassImmichPhotos.has_any_filter", return_value=False)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_get_albums_owned_by_user_uses_v3_owner_resolution(self, mock_get, _mock_filters):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {
                "id": "owned",
                "albumName": "Owned album",
                "albumUsers": [{"role": "owner", "user": {"id": "me"}}],
            },
            {
                "id": "shared",
                "albumName": "Shared album",
                "albumUsers": [{"role": "owner", "user": {"id": "someone-else"}}],
            },
        ]
        mock_get.return_value = response
        self.manager.get_user_id = lambda log_level=None: "me"

        albums = self.manager.get_albums_owned_by_user(filter_assets=False)

        self.assertEqual([album["id"] for album in albums], ["owned"])

    @patch("Features.ImmichPhotos.ClassImmichPhotos.has_any_filter", return_value=False)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.get")
    def test_get_albums_owned_by_user_ignores_unknown_owner_when_user_id_missing(self, mock_get, _mock_filters):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {
                "id": "ambiguous",
                "albumName": "Ambiguous album",
                "albumUsers": [],
            }
        ]
        mock_get.return_value = response
        self.manager.get_user_id = lambda log_level=None: None

        albums = self.manager.get_albums_owned_by_user(filter_assets=False)

        self.assertEqual(albums, [])

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.put")
    def test_add_assets_to_album_treats_duplicate_failures_as_already_associated(self, mock_put, mock_logger):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": "asset-1", "success": False, "error": "duplicate"},
        ]
        mock_put.return_value = response

        added = self.manager.add_assets_to_album("album-1", "asset-1", album_name="Album")

        self.assertEqual(added, 1)
        mock_logger.warning.assert_not_called()

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.put")
    def test_add_assets_to_album_warns_only_for_non_duplicate_failures(self, mock_put, mock_logger):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {"id": "asset-1", "success": True},
            {"id": "asset-2", "success": False, "error": "duplicate"},
            {"id": "asset-3", "success": False, "error": "permission denied"},
        ]
        mock_put.return_value = response

        added = self.manager.add_assets_to_album("album-1", ["asset-1", "asset-2", "asset-3"], album_name="Album")

        self.assertEqual(added, 2)
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args.args[0]
        self.assertIn("confirmed 2/3", warning_message)
        self.assertIn("permission denied", warning_message)


if __name__ == "__main__":
    unittest.main()
