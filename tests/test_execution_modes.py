import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "PIL" not in sys.modules:
    pil_stub = types.ModuleType("PIL")
    pil_image_stub = types.ModuleType("PIL.Image")
    pil_exif_stub = types.ModuleType("PIL.ExifTags")
    pil_stub.Image = pil_image_stub
    pil_stub.ExifTags = pil_exif_stub
    sys.modules["PIL"] = pil_stub
    sys.modules["PIL.Image"] = pil_image_stub
    sys.modules["PIL.ExifTags"] = pil_exif_stub

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
    import Features.AutomaticMigration.AutomaticMigration as automatic_module
    import Core.ExecutionModes as execution_modes
    EXECUTION_MODES_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    automatic_module = exc
    execution_modes = exc
    EXECUTION_MODES_IMPORT_ERROR = exc


def _base_args():
    return {
        "source": "",
        "target": "",
        "google-takeout": "",
        "icloud-takeout": "",
        "upload-albums": "",
        "upload-all": "",
        "download-albums": "",
        "download-all": "",
        "remove-albums": "",
        "rename-albums": "",
        "preview-album-actions": False,
        "reuse-similar-existing-albums": False,
        "remove-empty-albums": False,
        "remove-duplicates-albums": False,
        "merge-duplicates-albums": False,
        "remove-all-albums": "",
        "remove-all-assets": "",
        "remove-orphan-assets": "",
        "fix-symlinks-broken": "",
        "find-duplicates": ["list", ""],
        "process-duplicates": "",
        "rename-folders-content-based": "",
        "organize-local-folder-by-date": "",
        "show-gpth-info": False,
        "account-id": 1,
        "client": "immich",
    }


class TestExecutionModes(unittest.TestCase):
    def setUp(self):
        if EXECUTION_MODES_IMPORT_ERROR is not None:
            self.skipTest(f"Execution mode dependencies are not installed in this environment: {EXECUTION_MODES_IMPORT_ERROR}")

    def test_detect_and_run_execution_mode_dispatches_automatic_migration(self):
        args = _base_args()
        args["source"] = "synology"
        args["target"] = "immich"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(automatic_module, "ARGS", args),
            patch.object(execution_modes, "mode_AUTOMATIC_MIGRATION") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_google_takeout(self):
        args = _base_args()
        args["google-takeout"] = "/tmp/Takeout"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_google_takeout") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_icloud_takeout(self):
        args = _base_args()
        args["icloud-takeout"] = "/tmp/iCloudExport"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_icloud_takeout") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_upload_albums(self):
        args = _base_args()
        args["upload-albums"] = "/tmp/albums"
        args["client"] = "nextcloud"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_cloud_upload_albums") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once_with(client="nextcloud")

    def test_detect_and_run_execution_mode_dispatches_organize_local_folder_by_date(self):
        args = _base_args()
        args["organize-local-folder-by-date"] = "/tmp/library"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_organize_local_folder_by_date") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_mode_cloud_rename_albums_passes_preview_flag_to_client(self):
        args = _base_args()
        args["rename-albums"] = ["--", "-"]
        args["preview-album-actions"] = True
        client_mock = unittest.mock.MagicMock()
        client_mock.rename_albums.return_value = 1

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=client_mock),
            patch.object(execution_modes, "LOGGER", unittest.mock.MagicMock()),
            patch.object(execution_modes, "HELP_TEXTS", {"rename-albums": "rename <ALBUMS_NAME_PATTERN> <ALBUMS_NAME_REPLACEMENT_PATTERN>"}),
        ):
            execution_modes.mode_cloud_rename_albums(client="immich", user_confirmation=False)

        client_mock.rename_albums.assert_called_once_with(
            pattern="--",
            pattern_to_replace="-",
            request_user_confirmation=True,
            log_level=unittest.mock.ANY,
        )

    def test_mode_cloud_remove_albums_passes_preview_flag_to_client(self):
        args = _base_args()
        args["remove-albums"] = "*Temp*"
        args["remove-albums-assets"] = True
        args["preview-album-actions"] = True
        client_mock = unittest.mock.MagicMock()
        client_mock.remove_albums_by_name.return_value = (2, 5)

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=client_mock),
            patch.object(execution_modes, "LOGGER", unittest.mock.MagicMock()),
            patch.object(execution_modes, "HELP_TEXTS", {"remove-albums": "remove <ALBUMS_NAME_PATTERN>"}),
        ):
            execution_modes.mode_cloud_remove_albums_by_name_pattern(client="nextcloud", user_confirmation=False)

        client_mock.remove_albums_by_name.assert_called_once_with(
            pattern="*Temp*",
            removeAlbumsAssets=True,
            request_user_confirmation=True,
            log_level=unittest.mock.ANY,
        )


if __name__ == "__main__":
    unittest.main()
