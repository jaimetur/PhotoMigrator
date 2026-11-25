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
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"prefer-canonical-album-names": False, "consolidate-similar-albums": False}),
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
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"prefer-canonical-album-names": False, "consolidate-similar-albums": True}),
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

    @patch("Features.GooglePhotos.ClassGooglePhotos.tqdm", side_effect=lambda iterable, **kwargs: iterable)
    def test_push_albums_normalizes_new_album_name_when_flag_enabled_even_without_existing_redundancy(self, _mock_tqdm):
        manager = self._build_manager()
        manager.get_albums_owned_by_user = MagicMock(return_value=[])
        manager.create_album = MagicMock(return_value="album-new")
        manager.push_asset = MagicMock(return_value=("media-1", False))
        manager.add_assets_to_album = MagicMock(return_value=1)

        with (
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"prefer-canonical-album-names": True, "consolidate-similar-albums": False}),
            patch("Features.GooglePhotos.ClassGooglePhotos.LOGGER", MagicMock()),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            album_folder = os.path.join(tmpdir, "Huelva_1")
            os.makedirs(album_folder, exist_ok=True)
            with open(os.path.join(album_folder, "photo.jpg"), "wb") as handle:
                handle.write(b"binary-data")

            manager.push_albums(
                input_folder=tmpdir,
                remove_duplicates=False,
            )

        manager.create_album.assert_called_once_with(album_name="Huelva", log_level=unittest.mock.ANY)

    @patch("Features.GooglePhotos.ClassGooglePhotos.tqdm", side_effect=lambda iterable, **kwargs: iterable)
    def test_push_albums_does_not_normalize_new_album_name_with_consolidate_only_and_no_existing_family(self, _mock_tqdm):
        manager = self._build_manager()
        manager.get_albums_owned_by_user = MagicMock(return_value=[])
        manager.create_album = MagicMock(return_value="album-new")
        manager.push_asset = MagicMock(return_value=("media-1", False))
        manager.add_assets_to_album = MagicMock(return_value=1)

        with (
            patch("Features.GooglePhotos.ClassGooglePhotos.ARGS", {"prefer-canonical-album-names": False, "consolidate-similar-albums": True}),
            patch("Features.GooglePhotos.ClassGooglePhotos.LOGGER", MagicMock()),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            album_folder = os.path.join(tmpdir, "Huelva_1")
            os.makedirs(album_folder, exist_ok=True)
            with open(os.path.join(album_folder, "photo.jpg"), "wb") as handle:
                handle.write(b"binary-data")

            manager.push_albums(
                input_folder=tmpdir,
                remove_duplicates=False,
            )

        manager.create_album.assert_called_once_with(album_name="Huelva_1", log_level=unittest.mock.ANY)



class TestGooglePhotosTokenScopes(unittest.TestCase):
    """Issue #1241: tokens without photoslibrary.appendonly and the --google-photos-authorize helper."""

    def setUp(self):
        if GOOGLE_IMPORT_ERROR is not None:
            self.skipTest(f"Google Photos dependencies are not installed in this environment: {GOOGLE_IMPORT_ERROR}")
        from Features.GooglePhotos import GooglePhotosAuthorize
        self.auth = GooglePhotosAuthorize

    def _manager(self):
        manager = ClassGooglePhotos.__new__(ClassGooglePhotos)
        manager.account_id = 2
        manager.client_id, manager.client_secret, manager.refresh_token = "id", "secret", "refresh"
        manager.timeout_seconds = 5
        manager.granted_scopes = ""
        return manager

    def _token_response(self, scope):
        response = MagicMock(status_code=200)
        response.json.return_value = {"access_token": "token", "scope": scope}
        return response

    def test_refresh_keeps_the_granted_scopes_and_detects_missing_upload_permission(self):
        manager = self._manager()
        with patch("Features.GooglePhotos.ClassGooglePhotos.requests.post", return_value=self._token_response(
                "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata")):
            manager._refresh_access_token()
        self.assertFalse(manager.can_upload())
        with patch("Features.GooglePhotos.ClassGooglePhotos.requests.post", return_value=self._token_response(
                " ".join(self.auth.REQUIRED_SCOPES))):
            manager._refresh_access_token()
        self.assertTrue(manager.can_upload())

    def test_token_without_scope_field_is_not_blocked(self):
        manager = self._manager()
        response = MagicMock(status_code=200)
        response.json.return_value = {"access_token": "token"}
        with patch("Features.GooglePhotos.ClassGooglePhotos.requests.post", return_value=response):
            manager._refresh_access_token()
        self.assertTrue(manager.can_upload())

    def test_insufficient_scopes_403_is_explained(self):
        manager = self._manager()
        response = MagicMock(status_code=403, text='{"error": {"code": 403, "message": "Request had insufficient authentication scopes."}}')
        with self.assertRaises(RuntimeError) as ctx:
            manager._raise_api_error("Google Photos API POST", response)
        message = str(ctx.exception)
        self.assertIn("photoslibrary.appendonly", message)
        self.assertIn("--google-photos-authorize --account-id 2", message)
        other = MagicMock(status_code=500, text="boom")
        with self.assertRaises(RuntimeError) as ctx:
            manager._raise_api_error("Google Photos API POST", other)
        self.assertIn("status=500", str(ctx.exception))

    def test_authorization_url_and_redirect_parsing(self):
        url = self.auth.build_authorization_url("client", "http://127.0.0.1:5000/", "state123", "challenge")
        from urllib.parse import parse_qs, urlparse
        params = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}
        self.assertEqual(params["access_type"], "offline")
        self.assertEqual(params["prompt"], "consent")
        self.assertEqual(params["code_challenge_method"], "S256")
        self.assertEqual(params["scope"].split(), list(self.auth.REQUIRED_SCOPES))
        self.assertEqual(self.auth.parse_redirect("http://127.0.0.1:5000/?state=state123&code=abc", "state123"), "abc")
        self.assertEqual(self.auth.parse_redirect("?code=xyz&state=state123", "state123"), "xyz")
        with self.assertRaises(ValueError):
            self.auth.parse_redirect("http://127.0.0.1:5000/?state=other&code=abc", "state123")
        with self.assertRaises(ValueError):
            self.auth.parse_redirect("http://127.0.0.1:5000/?error=access_denied&state=state123", "state123")

    def test_save_refresh_token_keeps_the_rest_of_the_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "Config.ini"
            config.write_text(
                "[Synology Photos]\nSYNOLOGY_URL = http://nas  # url\n\n"
                "[Google Photos]\nGOOGLE_PHOTOS_CLIENT_ID_1 = id   # client\n"
                "GOOGLE_PHOTOS_REFRESH_TOKEN_1   = old_token        # OAuth Refresh Token\n\n"
                "[Immich Photos]\nIMMICH_URL = http://immich\n",
                encoding="utf-8",
            )
            self.auth.save_refresh_token(config, 1, "1//new")
            self.auth.save_refresh_token(config, 2, "1//second")
            text = config.read_text(encoding="utf-8")
            self.assertIn("GOOGLE_PHOTOS_REFRESH_TOKEN_1   = 1//new        # OAuth Refresh Token", text)
            google = text.split("[Google Photos]")[1].split("[Immich Photos]")[0]
            self.assertIn("GOOGLE_PHOTOS_REFRESH_TOKEN_2 = 1//second", google)
            self.assertIn("SYNOLOGY_URL = http://nas  # url", text)
            self.assertIn("IMMICH_URL = http://immich", text)

    def test_authorize_exchanges_the_pasted_address_and_rejects_tokens_without_upload_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "Config.ini"
            config.write_text("[Google Photos]\nGOOGLE_PHOTOS_CLIENT_ID_1 = cid\nGOOGLE_PHOTOS_CLIENT_SECRET_1 = csecret\n", encoding="utf-8")
            captured = {}

            def fake_open(url):
                from urllib.parse import parse_qs, urlparse
                captured["state"] = parse_qs(urlparse(url).query)["state"][0]
                return True

            lines = iter([])

            def read_line():
                import time
                while "state" not in captured:
                    time.sleep(0.01)
                return next(lines, f"http://127.0.0.1:1/?state={captured['state']}&code=thecode")

            token = MagicMock(status_code=200)
            token.json.return_value = {"refresh_token": "1//saved", "scope": " ".join(self.auth.REQUIRED_SCOPES)}
            with patch.object(self.auth.webbrowser, "open", side_effect=fake_open), \
                    patch.object(self.auth.requests, "post", return_value=token) as post, \
                    patch("Core.ConfigReader.load_config", return_value={"Google Photos": {
                        "GOOGLE_PHOTOS_CLIENT_ID_1": "cid", "GOOGLE_PHOTOS_CLIENT_SECRET_1": "csecret"}}):
                self.auth.authorize(config, 1, log=lambda _msg: None, read_line=read_line)
            self.assertEqual(post.call_args.kwargs["data"]["code"], "thecode")
            self.assertIn("GOOGLE_PHOTOS_REFRESH_TOKEN_1 = 1//saved", config.read_text(encoding="utf-8"))

            captured.clear()
            token.json.return_value = {"refresh_token": "1//bad", "scope": self.auth.SCOPE_APP_CREATED_DATA}
            with patch.object(self.auth.webbrowser, "open", side_effect=fake_open), \
                    patch.object(self.auth.requests, "post", return_value=token), \
                    patch("Core.ConfigReader.load_config", return_value={"Google Photos": {
                        "GOOGLE_PHOTOS_CLIENT_ID_1": "cid", "GOOGLE_PHOTOS_CLIENT_SECRET_1": "csecret"}}):
                with self.assertRaises(RuntimeError):
                    self.auth.authorize(config, 1, log=lambda _msg: None, read_line=read_line)
            self.assertNotIn("1//bad", config.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
