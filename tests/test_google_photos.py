import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "colorama" not in sys.modules:
    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(RED="", GREEN="", YELLOW="", CYAN="", WHITE="", BLUE="", MAGENTA="")
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="", DIM="", NORMAL="")
    sys.modules["colorama"] = colorama_stub

if "piexif" not in sys.modules:
    piexif_stub = types.ModuleType("piexif")
    piexif_stub.ExifIFD = types.SimpleNamespace(DateTimeOriginal=36867, DateTimeDigitized=36868)
    piexif_stub.ImageIFD = types.SimpleNamespace(DateTime=306)
    piexif_stub.load = lambda *args, **kwargs: {"0th": {}, "Exif": {}}
    piexif_stub.dump = lambda *args, **kwargs: b""
    piexif_stub.insert = lambda *args, **kwargs: None
    sys.modules["piexif"] = piexif_stub

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

if "tzlocal" not in sys.modules:
    tzlocal_stub = types.ModuleType("tzlocal")
    tzlocal_stub.get_localzone = lambda: None
    sys.modules["tzlocal"] = tzlocal_stub

try:
    from Features.GooglePhotos.ClassGooglePhotos import ClassGooglePhotos
    GOOGLE_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    ClassGooglePhotos = None
    GOOGLE_IMPORT_ERROR = exc


class TestGooglePhotosUnit(unittest.TestCase):
    def setUp(self):
        if GOOGLE_IMPORT_ERROR is not None:
            self.skipTest(f"Google Photos dependencies are not installed in this environment: {GOOGLE_IMPORT_ERROR}")

    def _build_manager(self):
        manager = ClassGooglePhotos.__new__(ClassGooglePhotos)
        manager.albums_root_name = "Albums"
        manager.no_albums_root_name = "No-Albums"
        manager.exclude_folder_patterns = []
        manager.exclude_file_patterns = []
        manager._is_supported_media = lambda filename, mime_type="": str(filename).lower().endswith(".jpg")
        return manager

    def test_batch_create_media_item_reuses_resolved_existing_id_for_duplicate(self):
        manager = self._build_manager()
        response = MagicMock()
        response.json.return_value = {
            "newMediaItemResults": [
                {
                    "status": {
                        "code": 6,
                        "message": "Media item already exists.",
                    }
                }
            ]
        }
        manager._request = MagicMock(return_value=response)
        manager._resolve_existing_media_item_id = MagicMock(return_value="existing-media-id")

        media_id, is_duplicated = manager._batch_create_media_item(
            upload_token="upload-token",
            file_name="photo.jpg",
            album_id="album-1",
            file_path="/tmp/photo.jpg",
        )

        self.assertEqual(media_id, "existing-media-id")
        self.assertTrue(is_duplicated)
        manager._resolve_existing_media_item_id.assert_called_once_with(
            file_path="/tmp/photo.jpg",
            file_name="photo.jpg",
        )

    @patch("Features.GooglePhotos.ClassGooglePhotos.tqdm", side_effect=lambda iterable, **kwargs: iterable)
    def test_push_albums_adds_duplicate_assets_to_each_album_when_id_is_resolved(self, _mock_tqdm):
        manager = self._build_manager()
        manager.get_albums_owned_by_user = MagicMock(return_value=[])
        manager.create_album = MagicMock(side_effect=["album-1", "album-2"])
        manager.push_asset = MagicMock(side_effect=[("media-1", False), ("media-1", True)])
        manager.add_assets_to_album = MagicMock(return_value=1)

        with (
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"reuse-similar-existing-albums": False}),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            album_a = os.path.join(tmpdir, "Album A")
            album_b = os.path.join(tmpdir, "Album B")
            os.makedirs(album_a, exist_ok=True)
            os.makedirs(album_b, exist_ok=True)
            for folder in (album_a, album_b):
                with open(os.path.join(folder, "photo.jpg"), "wb") as handle:
                    handle.write(b"binary-data")

            uploaded_albums, skipped_albums, uploaded_assets, _removed_dups, duplicate_assets = manager.push_albums(
                input_folder=tmpdir,
                remove_duplicates=False,
            )

        self.assertEqual(uploaded_albums, 2)
        self.assertEqual(skipped_albums, 0)
        self.assertEqual(uploaded_assets, 1)
        self.assertEqual(duplicate_assets, 1)
        self.assertEqual(manager.add_assets_to_album.call_count, 2)
        first_call = manager.add_assets_to_album.call_args_list[0].kwargs
        second_call = manager.add_assets_to_album.call_args_list[1].kwargs
        self.assertEqual(first_call["album_id"], "album-1")
        self.assertEqual(first_call["asset_ids"], ["media-1"])
        self.assertEqual(second_call["album_id"], "album-2")
        self.assertEqual(second_call["asset_ids"], ["media-1"])

    @patch("Features.GooglePhotos.ClassGooglePhotos.tqdm", side_effect=lambda iterable, **kwargs: iterable)
    def test_push_albums_reuses_similar_existing_album_when_flag_enabled(self, _mock_tqdm):
        manager = self._build_manager()
        manager.get_albums_owned_by_user = MagicMock(
            return_value=[{"id": "album-existing", "albumName": "2026-07-06 - Viaje a Roma"}]
        )
        manager.create_album = MagicMock()
        manager.push_asset = MagicMock(return_value=("media-1", False))
        manager.add_assets_to_album = MagicMock(return_value=1)

        with (
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"reuse-similar-existing-albums": True}),
            patch("Features.GooglePhotos.ClassGooglePhotos.LOGGER", MagicMock()),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            album_folder = os.path.join(tmpdir, "2026.07.06 -- Viaje a Roma")
            os.makedirs(album_folder, exist_ok=True)
            with open(os.path.join(album_folder, "photo.jpg"), "wb") as handle:
                handle.write(b"binary-data")

            uploaded_albums, skipped_albums, uploaded_assets, _removed_dups, duplicate_assets = manager.push_albums(
                input_folder=tmpdir,
                remove_duplicates=False,
            )

        self.assertEqual(uploaded_albums, 0)
        self.assertEqual(skipped_albums, 0)
        self.assertEqual(uploaded_assets, 1)
        self.assertEqual(duplicate_assets, 0)
        manager.create_album.assert_not_called()
        manager.add_assets_to_album.assert_called_once()
        self.assertEqual(manager.add_assets_to_album.call_args.kwargs["album_id"], "album-existing")


if __name__ == "__main__":
    unittest.main()
