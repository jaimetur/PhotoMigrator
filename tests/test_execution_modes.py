import contextlib
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        "created-from": "",
        "created-to": "",
        "rename-albums": "",
        "preview-album-actions": False,
        "prefer-canonical-album-names": False,
        "consolidate-similar-albums": False,
        "remove-empty-albums": False,
        "remove-duplicates-albums": False,
        "remove-duplicates-assets": False,
        "dup-immich-native-algorithm": False,
        "dup-immich-native-deletion": False,
        "dup-asset-keeper": "newest",
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

    def test_remove_duplicate_assets_previews_groups_before_confirming_deletion(self):
        args = _base_args()
        duplicate_groups = [[
            {
                "id": "older",
                "originalFileName": "IMG_0001.JPG",
                "createdAt": "2020-01-01T00:00:00Z",
                "exifInfo": {"fileSize": 42, "description": "Older description", "rating": 3},
                "albums": [{"id": "album-1"}],
            },
            {
                "id": "newer",
                "originalFileName": "IMG_0001.JPG",
                "createdAt": "2021-01-01T00:00:00Z",
                "exifInfo": {"fileSize": 42},
                "tags": [{"id": "tag-1"}],
                "isFavorite": True,
            },
        ]]
        cloud_client = MagicMock()
        cloud_client.find_duplicate_assets_by_name_and_size.return_value = duplicate_groups
        cloud_client.hydrate_duplicate_groups_metadata.return_value = duplicate_groups
        cloud_client.get_duplicate_metadata_display_names.return_value = {"albums": {}, "tags": {}, "people": {}}
        cloud_client._duplicate_asset_timestamp.side_effect = lambda asset: asset["createdAt"]
        cloud_client._duplicate_asset_size.side_effect = lambda asset: asset["exifInfo"]["fileSize"]
        cloud_client.remove_duplicates_assets_by_name_and_size.return_value = (1, 1, 0)

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=cloud_client),
            patch.object(execution_modes, "confirm_continue", return_value=True) as mock_confirm,
            patch.object(execution_modes, "LOGGER", MagicMock()) as mock_logger,
        ):
            execution_modes.mode_cloud_remove_duplicates_assets(client="immich")

        mock_confirm.assert_called_once_with()
        cloud_client.remove_duplicates_assets_by_name_and_size.assert_called_once_with(
            keeper_strategy="newest",
            duplicate_groups=duplicate_groups,
            log_level=execution_modes.logging.INFO,
        )
        cloud_client.logout.assert_called_once_with(log_level=execution_modes.logging.WARNING)
        preview_lines = [str(call.args[0]) for call in mock_logger.info.call_args_list]
        self.assertIn("  [1] IMG_0001.JPG (42 bytes, 2 candidate asset(s))", preview_lines)
        self.assertTrue(any("Field" in line and "Keeper (newest)" in line and "Remove 1" in line for line in preview_lines))
        self.assertTrue(any("ID" in line and "newer" in line and "older" in line for line in preview_lines))
        self.assertTrue(any("Size" in line and "42 bytes" in line for line in preview_lines))
        self.assertTrue(any("Tags" in line for line in preview_lines))
        self.assertTrue(any("tag-1" in line for line in preview_lines))
        self.assertTrue(any("Favorite" in line for line in preview_lines))
        self.assertTrue(any("Albums" in line for line in preview_lines))
        self.assertTrue(any("album-1" in line for line in preview_lines))
        self.assertTrue(any("Description" in line for line in preview_lines))
        self.assertTrue(any("Older description" in line for line in preview_lines))
        self.assertTrue(any("Rating" in line for line in preview_lines))

    def test_remove_duplicate_assets_uses_immich_native_groups_by_default(self):
        args = _base_args()
        args.update({
            "remove-duplicates-assets": True,
            "dup-immich-native-algorithm": True,
            "dup-asset-keeper": "better-quality",
        })
        duplicate_groups = [[
            {"id": "small", "originalFileName": "IMG.JPG", "createdAt": "2020-01-01T00:00:00Z", "exifInfo": {"fileSize": 42}},
            {"id": "large", "originalFileName": "IMG-copy.JPG", "createdAt": "2021-01-01T00:00:00Z", "exifInfo": {"fileSize": 84}},
        ]]
        cloud_client = MagicMock()
        cloud_client.find_duplicate_assets_by_immich_detection.return_value = duplicate_groups
        cloud_client.hydrate_duplicate_groups_metadata.return_value = duplicate_groups
        cloud_client.get_duplicate_metadata_display_names.return_value = {"albums": {}, "tags": {}, "people": {}}
        cloud_client._select_duplicate_asset_keeper.return_value = duplicate_groups[0][1]
        cloud_client._duplicate_asset_size.side_effect = lambda asset: asset["exifInfo"]["fileSize"]
        cloud_client.remove_duplicates_assets_by_name_and_size.return_value = (1, 1, 0)

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=cloud_client),
            patch.object(execution_modes, "confirm_continue", return_value=True),
            patch.object(execution_modes, "LOGGER", MagicMock()),
        ):
            execution_modes.mode_cloud_remove_duplicates_assets(client="immich")

        cloud_client.find_duplicate_assets_by_immich_detection.assert_called_once_with(log_level=execution_modes.logging.INFO)
        cloud_client.find_duplicate_assets_by_name_and_size.assert_not_called()
        cloud_client.remove_duplicates_assets_by_name_and_size.assert_called_once_with(
            keeper_strategy="better-quality",
            duplicate_groups=duplicate_groups,
            log_level=execution_modes.logging.INFO,
        )
        cloud_client.resolve_duplicate_asset_groups_with_immich.assert_not_called()

    def test_remove_duplicate_assets_can_delegate_resolution_to_immich(self):
        args = _base_args()
        args.update({
            "remove-duplicates-assets": True,
            "dup-immich-native-algorithm": True,
            "dup-immich-native-deletion": True,
            "dup-asset-keeper": "better-quality",
        })
        duplicate_groups = [[
            {"id": "small", "originalFileName": "IMG.JPG", "createdAt": "2020-01-01T00:00:00Z", "exifInfo": {"fileSize": 42}},
            {"id": "large", "originalFileName": "IMG-copy.JPG", "createdAt": "2021-01-01T00:00:00Z", "exifInfo": {"fileSize": 84}},
        ]]
        cloud_client = MagicMock()
        cloud_client.find_duplicate_assets_by_immich_detection.return_value = duplicate_groups
        cloud_client.hydrate_duplicate_groups_metadata.return_value = duplicate_groups
        cloud_client.get_duplicate_metadata_display_names.return_value = {"albums": {}, "tags": {}, "people": {}}
        cloud_client._select_duplicate_asset_keeper.return_value = duplicate_groups[0][1]
        cloud_client._duplicate_asset_size.side_effect = lambda asset: asset["exifInfo"]["fileSize"]
        cloud_client.resolve_duplicate_asset_groups_with_immich.return_value = (1, 1, 0)

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=cloud_client),
            patch.object(execution_modes, "confirm_continue", return_value=True),
            patch.object(execution_modes, "LOGGER", MagicMock()),
        ):
            execution_modes.mode_cloud_remove_duplicates_assets(client="immich")

        cloud_client.find_duplicate_assets_by_immich_detection.assert_called_once_with(log_level=execution_modes.logging.INFO)
        cloud_client.get_duplicate_metadata_display_names.assert_called_once_with(
            duplicate_groups,
            log_level=execution_modes.logging.INFO,
        )
        cloud_client.hydrate_duplicate_groups_metadata.assert_called_once_with(
            duplicate_groups,
            log_level=execution_modes.logging.INFO,
            include_albums=False,
        )
        cloud_client.resolve_duplicate_asset_groups_with_immich.assert_called_once_with(
            duplicate_groups=duplicate_groups,
            keeper_strategy="better-quality",
            log_level=execution_modes.logging.INFO,
        )
        cloud_client.remove_duplicates_assets_by_name_and_size.assert_not_called()

    def test_native_deletion_is_disabled_when_native_detection_is_disabled(self):
        args = _base_args()
        args.update({
            "remove-duplicates-assets": True,
            "dup-immich-native-algorithm": False,
            "dup-immich-native-deletion": True,
            "dup-asset-keeper": "newest",
        })
        duplicate_groups = [[
            {"id": "older", "originalFileName": "IMG.JPG", "createdAt": "2020-01-01T00:00:00Z", "exifInfo": {"fileSize": 42}},
            {"id": "newer", "originalFileName": "IMG.JPG", "createdAt": "2021-01-01T00:00:00Z", "exifInfo": {"fileSize": 42}},
        ]]
        cloud_client = MagicMock()
        cloud_client.find_duplicate_assets_by_name_and_size.return_value = duplicate_groups
        cloud_client.hydrate_duplicate_groups_metadata.return_value = duplicate_groups
        cloud_client.get_duplicate_metadata_display_names.return_value = {"albums": {}, "tags": {}, "people": {}}
        cloud_client._duplicate_asset_timestamp.side_effect = lambda asset: asset["createdAt"]
        cloud_client._duplicate_asset_size.side_effect = lambda asset: asset["exifInfo"]["fileSize"]
        cloud_client.remove_duplicates_assets_by_name_and_size.return_value = (1, 1, 0)

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "_build_cloud_client_obj", return_value=cloud_client),
            patch.object(execution_modes, "confirm_continue", return_value=True),
            patch.object(execution_modes, "LOGGER", MagicMock()),
        ):
            execution_modes.mode_cloud_remove_duplicates_assets(client="immich")

        cloud_client.find_duplicate_assets_by_name_and_size.assert_called_once_with(log_level=execution_modes.logging.INFO)
        cloud_client.find_duplicate_assets_by_immich_detection.assert_not_called()
        cloud_client.resolve_duplicate_asset_groups_with_immich.assert_not_called()

    def test_duplicate_metadata_preview_uses_resolved_names(self):
        preview = execution_modes._duplicate_asset_merge_metadata_preview(
            {
                "albums": [{"id": "album-1"}],
                "tags": [{"id": "tag-1"}],
                "people": [{"id": "person-1"}],
            },
            {
                "albums": {"album-1": "Summer 2003"},
                "tags": {"tag-1": "family/yoli"},
                "people": {"person-1": "Yoli"},
            },
        )

        self.assertEqual(
            preview,
            {"albums": ["Summer 2003"], "tags": ["family/yoli"], "people": ["Yoli"]},
        )

    def test_duplicate_metadata_preview_uses_names_embedded_in_immich_assets(self):
        preview = execution_modes._duplicate_asset_merge_metadata_preview(
            {
                "tags": [{"id": "tag-1", "value": "family/yoli"}],
                "people": [{"id": "person-1", "name": "Yoli"}],
            },
        )

        self.assertEqual(preview, {"tags": ["family/yoli"], "people": ["Yoli"]})

    def test_detect_and_run_execution_mode_dispatches_organize_local_folder_by_date(self):
        args = _base_args()
        args["organize-local-folder-by-date"] = "/tmp/library"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_organize_local_folder_by_date") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_mode_google_takeout_normalizes_pre_unzipped_input_output_folder_name(self):
        args = _base_args()
        args.update({
            "google-takeout": "/tmp/Takeout_unzipped_20260707-012602",
            "output-folder": "",
            "google-output-folder-suffix": "processed",
            "google-input-zip-folder": "",
            "google-albums-folders-structure": "flatten",
            "google-all-photos-folders-structure": "year/month",
            "google-skip-gpth-tool": False,
            "google-skip-extras-files": False,
            "google-skip-move-albums": False,
            "google-no-symbolic-albums": False,
            "google-ignore-check-structure": False,
            "google-keep-takeout-folder": False,
            "google-remove-duplicates-files": False,
            "google-rename-albums-folders": False,
            "google-skip-preprocess": False,
            "google-skip-postprocess": False,
            "show-gpth-info": False,
            "show-gpth-errors": False,
            "no-log-file": False,
        })
        takeout_mock = unittest.mock.MagicMock()
        takeout_mock.process.return_value = {}

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "TIMESTAMP", "20260707-012602"),
            patch.object(execution_modes, "ClassTakeoutFolder", return_value=takeout_mock),
            patch.object(execution_modes, "dir_exists", return_value=True),
            patch.object(execution_modes, "contains_zip_files", return_value=False),
            patch.object(execution_modes, "LOGGER", unittest.mock.MagicMock()),
            patch.object(execution_modes, "set_log_level", return_value=contextlib.nullcontext()),
        ):
            execution_modes.mode_google_takeout(user_confirmation=False)

        takeout_mock.process.assert_called_once_with(
            output_folder="/tmp/Takeout_processed_20260707-012602",
            capture_output=False,
            capture_errors=False,
            print_messages=True,
            create_localfolder_object=False,
            log_level=None,
        )

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
        args["created-from"] = "2024-01-01T00:00:00.000Z"
        args["created-to"] = "2024-12-31T00:00:00.000Z"
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
            remove_album_assets=True,
            created_from="2024-01-01T00:00:00.000Z",
            created_to="2024-12-31T00:00:00.000Z",
            request_user_confirmation=True,
            log_level=unittest.mock.ANY,
        )


if __name__ == "__main__":
    unittest.main()
