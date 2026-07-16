import contextlib
import builtins
import io
import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "colorama" not in sys.modules:
    colorama_stub = MagicMock()
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = MagicMock()
    colorama_stub.Style = MagicMock()
    sys.modules["colorama"] = colorama_stub

sys.modules.setdefault("piexif", MagicMock())
import Utils.StandaloneUtils as standalone_utils

try:
    import Features.GoogleTakeout.ClassTakeoutFolder as takeout_module
    from Features.GoogleTakeout.ClassTakeoutFolder import (
        _extract_orphan_album_json_descriptor,
        _find_forbidden_special_folder_in_path,
        _is_takeout_year_folder,
        contains_takeout_structure,
        inspect_takeout_structure,
        prepare_gpth_fix_working_input,
        recover_orphan_album_assets_from_json_sidecars,
        remap_takeout_detection_info_root,
        relocate_gpth_fix_outputs,
        select_gpth_fix_target_folder,
        should_auto_force_gpth_fix,
        should_recover_orphan_album_assets,
    )
    TAKEOUT_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    TAKEOUT_IMPORT_ERROR = exc


class TestGoogleTakeoutHelpers(unittest.TestCase):
    def setUp(self):
        if TAKEOUT_IMPORT_ERROR is not None:
            self.skipTest(f"Google Takeout dependencies are not installed in this environment: {TAKEOUT_IMPORT_ERROR}")
        self.logger = logging.getLogger("test-google-takeout")
        self.logger.handlers = []
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())

    def test_is_takeout_year_folder_supports_localized_names(self):
        self.assertTrue(_is_takeout_year_folder("Photos from 2024"))
        self.assertTrue(_is_takeout_year_folder("Fotos del 2024"))
        self.assertTrue(_is_takeout_year_folder("Fotos von 2024"))
        self.assertFalse(_is_takeout_year_folder("Holiday Album 2024"))

    def test_find_forbidden_special_folder_in_path_detects_special_components(self):
        offending = _find_forbidden_special_folder_in_path("/tmp/Export/Trash/Takeout")
        self.assertEqual(offending, "Trash")

    def test_find_forbidden_special_folder_in_path_detects_localized_special_components(self):
        offending = _find_forbidden_special_folder_in_path("/tmp/Export/Carpeta privada/Takeout")
        self.assertEqual(offending, "Carpeta privada")

    def test_contains_takeout_structure_detects_nested_localized_year_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Google Photos" / "Fotos del 2024").mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                detected = contains_takeout_structure(str(root), log_level=logging.INFO)

        self.assertTrue(detected)

    def test_contains_takeout_structure_detects_album_only_takeout_with_archive_browser_and_json_sidecars(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            takeout_root = root / "Takeout"
            photos_root = takeout_root / "Google Photos"
            album_dir = photos_root / "Album 1"
            album_dir.mkdir(parents=True)
            (takeout_root / "archive_browser.html").write_text("<html></html>", encoding="utf-8")
            (album_dir / "photo.jpg.json").write_text('{"title":"photo.jpg"}', encoding="utf-8")

            with patch.object(takeout_module, "LOGGER", self.logger):
                detected = contains_takeout_structure(str(takeout_root), log_level=logging.INFO)
                details = inspect_takeout_structure(str(takeout_root), log_level=logging.INFO)

        self.assertTrue(detected)
        self.assertTrue(details["is_takeout"])
        self.assertEqual(details["mode"], "album-only")
        self.assertTrue(details["has_archive_browser"])
        self.assertTrue(details["has_album_json_sidecars"])

    def test_contains_takeout_structure_does_not_detect_album_only_layout_without_archive_browser(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            photos_root = root / "Google Photos"
            album_dir = photos_root / "Album 1"
            album_dir.mkdir(parents=True)
            (album_dir / "photo.jpg.json").write_text('{"title":"photo.jpg"}', encoding="utf-8")

            with patch.object(takeout_module, "LOGGER", self.logger):
                detected = contains_takeout_structure(str(root), log_level=logging.INFO)
                details = inspect_takeout_structure(str(root), log_level=logging.INFO)

        self.assertFalse(detected)
        self.assertFalse(details["is_takeout"])

    def test_get_output_folder_strips_generated_unzipped_suffix_from_takeout_root(self):
        takeout = takeout_module.ClassTakeoutFolder.__new__(takeout_module.ClassTakeoutFolder)
        takeout.ARGS = {
            "google-ignore-check-structure": False,
            "google-output-folder-suffix": "processed",
            "google-skip-move-albums": False,
            "output-folder": "",
        }
        takeout.TIMESTAMP = "20260707-012602"
        takeout.needs_process = True
        takeout.takeout_folder = Path("/tmp/Takeout_unzipped_20260707-012602")
        takeout.get_albums_folder = lambda: None
        takeout._sync_local_folder_view = lambda: None

        output_folder = takeout_module.ClassTakeoutFolder.get_output_folder(takeout)

        self.assertEqual(output_folder, Path("/tmp/Takeout_processed_20260707-012602"))

    def test_select_gpth_fix_target_folder_uses_detected_google_photos_container(self):
        selected = select_gpth_fix_target_folder(
            input_folder="/tmp/Takeout",
            takeout_detection_info={
                "mode": "album-only",
                "container_path": "/tmp/Takeout/Google Photos",
            },
        )

        self.assertEqual(selected, str(Path("/tmp/Takeout/Google Photos")))

    def test_should_auto_force_gpth_fix_only_for_album_only_layout(self):
        self.assertTrue(should_auto_force_gpth_fix({"mode": "album-only"}))
        self.assertFalse(should_auto_force_gpth_fix({"mode": "standard"}))
        self.assertFalse(should_auto_force_gpth_fix({}))

    def test_should_recover_orphan_album_assets_only_when_year_folders_exist(self):
        self.assertTrue(should_recover_orphan_album_assets({"has_year_folders": True, "mode": "standard"}))
        self.assertFalse(should_recover_orphan_album_assets({"has_year_folders": False, "mode": "album-only"}))
        self.assertFalse(should_recover_orphan_album_assets({}))

    def test_prepare_gpth_fix_working_input_clones_and_remaps_when_keep_takeout_is_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_root = root / "Takeout"
            photos_root = source_root / "Google Photos"
            album_dir = photos_root / "Album 1"
            album_dir.mkdir(parents=True)
            (album_dir / "photo.jpg").write_bytes(b"x")
            filedates_json = root / "dates.json"
            source_file = album_dir / "photo.jpg"
            filedates_json.write_text(
                json.dumps({source_file.resolve().as_posix(): {"OldestDate": "2024-01-01T00:00:00"}}),
                encoding="utf-8",
            )

            with patch.object(takeout_module, "LOGGER", self.logger):
                working_root, fix_target, remapped_json, cloned_from = prepare_gpth_fix_working_input(
                    input_folder=str(source_root),
                    takeout_detection_info={"container_path": str(photos_root)},
                    keep_takeout_folder=True,
                    filedates_json=str(filedates_json),
                    timestamp="20260709-120000",
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertNotEqual(Path(working_root), source_root)
            self.assertEqual(cloned_from, str(source_root.resolve()))
            self.assertEqual(Path(fix_target).resolve(), (Path(working_root) / "Google Photos").resolve())
            self.assertNotEqual(remapped_json, str(filedates_json))
            remapped_payload = json.loads(Path(remapped_json).read_text(encoding="utf-8"))
            self.assertIn(str((Path(working_root) / "Google Photos" / "Album 1" / "photo.jpg").resolve()), remapped_payload)

    def test_prepare_gpth_fix_working_input_does_not_clone_disposable_unzipped_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            unzipped_root = root / "Takeout_unzipped_20260709-120000"
            photos_root = unzipped_root / "Google Photos"
            (photos_root / "Album 1").mkdir(parents=True)
            filedates_json = root / "dates.json"
            filedates_json.write_text(json.dumps({}), encoding="utf-8")

            with patch.object(takeout_module, "LOGGER", self.logger):
                working_root, fix_target, remapped_json, cloned_from = prepare_gpth_fix_working_input(
                    input_folder=str(unzipped_root),
                    takeout_detection_info={"container_path": str(photos_root)},
                    keep_takeout_folder=True,
                    filedates_json=str(filedates_json),
                    timestamp="20260709-120000",
                    input_is_disposable=True,
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertEqual(Path(working_root).resolve(), unzipped_root.resolve())
            self.assertEqual(Path(fix_target).resolve(), photos_root.resolve())
            self.assertEqual(remapped_json, str(filedates_json))
            self.assertIsNone(cloned_from)

    def test_remap_takeout_detection_info_root_updates_container_and_match_paths(self):
        source_root = Path("/tmp/Takeout")
        target_root = Path("/tmp/Takeout_tmp_20260709")
        original = {
            "mode": "album-only",
            "matched_path": str(source_root / "Google Photos" / "Album 1"),
            "container_path": str(source_root / "Google Photos"),
        }

        remapped = remap_takeout_detection_info_root(
            takeout_detection_info=original,
            source_root=str(source_root),
            target_root=str(target_root),
        )

        self.assertEqual(remapped["mode"], "album-only")
        self.assertEqual(Path(remapped["matched_path"]).resolve(), (target_root / "Google Photos" / "Album 1").resolve())
        self.assertEqual(Path(remapped["container_path"]).resolve(), (target_root / "Google Photos").resolve())

    def test_run_command_compacts_repeated_createfile_failed_warnings(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    '[WARNING] [Step 8/8] CreateFile failed for "\\\\?\\D:\\\\Albums\\\\a.jpg" (error=2)\n'
                    '[WARNING] [Step 8/8] CreateFile failed for "\\\\?\\D:\\\\Albums\\\\b.jpg" (error=2)\n'
                    'INFO  processing completed\n'
                )
                self.stderr = io.StringIO("")
                self.returncode = 0

            def wait(self):
                return self.returncode

        fake_logger = MagicMock()

        with (
            patch.object(takeout_module, "LOGGER", fake_logger),
            patch.object(takeout_module, "custom_print"),
            patch.object(takeout_module, "suppress_console_output_temporarily", new=lambda *_args, **_kwargs: contextlib.nullcontext()),
            patch.object(takeout_module.subprocess, "Popen", return_value=FakeProcess()),
        ):
            returncode = takeout_module.run_command(
                ["dummy-gpth"],
                capture_output=True,
                capture_errors=True,
                print_messages=True,
                step_name="STEP : ",
            )

        self.assertEqual(returncode, 0)
        warning_messages = [call.args[0] for call in fake_logger.warning.call_args_list]
        self.assertEqual(len(warning_messages), 1)
        self.assertIn('Collapsed 2 repeated GPTH "CreateFile failed" warnings', warning_messages[0])
        self.assertIn('First example: "\\\\?\\D:\\\\Albums\\\\a.jpg"', warning_messages[0])
        info_messages = [call.args[0] for call in fake_logger.info.call_args_list]
        self.assertIn("STEP : INFO  processing completed", info_messages)

    def test_run_command_compacts_createfile_warnings_even_when_they_include_progress_counters(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    '[WARNING] [Step 8/8] Updating creation times : 1062/1063 CreateFile failed for "\\\\?\\D:\\\\Albums\\\\a.jpg" (error=2)\n'
                    '[WARNING] [Step 8/8] Updating creation times : 1063/1063 CreateFile failed for "\\\\?\\D:\\\\Albums\\\\b.jpg" (error=2)\n'
                )
                self.stderr = io.StringIO("")
                self.returncode = 0

            def wait(self):
                return self.returncode

        fake_logger = MagicMock()

        with (
            patch.object(takeout_module, "LOGGER", fake_logger),
            patch.object(takeout_module, "custom_print") as mock_custom_print,
            patch.object(takeout_module, "suppress_console_output_temporarily", new=lambda *_args, **_kwargs: contextlib.nullcontext()),
            patch.object(takeout_module.subprocess, "Popen", return_value=FakeProcess()),
        ):
            returncode = takeout_module.run_command(
                ["dummy-gpth"],
                capture_output=True,
                capture_errors=True,
                print_messages=True,
                step_name="STEP : ",
            )

        self.assertEqual(returncode, 0)
        warning_messages = [call.args[0] for call in fake_logger.warning.call_args_list]
        self.assertEqual(len(warning_messages), 1)
        self.assertIn('Collapsed 2 repeated GPTH "CreateFile failed" warnings', warning_messages[0])
        console_lines = [call.args[0] for call in mock_custom_print.call_args_list]
        self.assertEqual(len(console_lines), 1)
        self.assertIn('Collapsed 2 repeated GPTH "CreateFile failed" warnings', console_lines[0])
        self.assertFalse(any('CreateFile failed for "\\\\?\\D:\\\\Albums\\\\a.jpg"' in line for line in console_lines))

    def test_run_command_emits_carriage_return_progress_frames_to_dashboard_handlers(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "[INFO] [Step 6/8] Moving entities : 0/10\r"
                    "[INFO] [Step 6/8] Moving entities : 5/10\r"
                    "\n"
                    "[INFO] [Step 6/8] Moving entities : 10/10"
                )
                self.stderr = io.StringIO("")
                self.returncode = 0

            def wait(self):
                return self.returncode

        class DashboardHandler:
            accept_tqdm = True

            def __init__(self):
                self.messages = []

            def emit(self, record):
                self.messages.append(record.msg)

        fake_logger = MagicMock()
        dashboard_handler = DashboardHandler()
        fake_logger.handlers = [dashboard_handler]
        fake_logger.name = "PhotoMigrator"

        with (
            patch.object(takeout_module, "LOGGER", fake_logger),
            patch.object(takeout_module, "custom_print"),
            patch.object(takeout_module, "suppress_console_output_temporarily", new=lambda *_args, **_kwargs: contextlib.nullcontext()),
            patch.object(takeout_module.subprocess, "Popen", return_value=FakeProcess()),
        ):
            returncode = takeout_module.run_command(
                ["dummy-gpth"],
                capture_output=True,
                capture_errors=True,
                print_messages=False,
                step_name="STEP : ",
            )

        self.assertEqual(returncode, 0)
        self.assertEqual(
            dashboard_handler.messages,
            [
                "__TQDM__ [INFO] [Step 6/8] Moving entities : 0/10",
                "__TQDM__ [INFO] [Step 6/8] Moving entities : 5/10",
                "__TQDM__ [INFO] [Step 6/8] Moving entities : 10/10",
            ],
        )
        info_messages = [call.args[0] for call in fake_logger.info.call_args_list]
        self.assertIn("STEP : [INFO] [Step 6/8] Moving entities : 0/10", info_messages)
        self.assertIn("STEP : [INFO] [Step 6/8] Moving entities : 10/10", info_messages)
        self.assertNotIn("STEP : ", [msg for msg in info_messages if msg.strip() == "STEP :"])

    def test_run_command_progress_output_uses_safe_console_printing_for_unicode_lines(self):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(
                    "[INFO] [Step 1/8] 🧠 Fixing file extensions : 1/2\r"
                    "[INFO] [Step 1/8] 🧠 Fixing file extensions : 2/2\n"
                )
                self.stderr = io.StringIO("")
                self.returncode = 0

            def wait(self):
                return self.returncode

        fake_logger = MagicMock()
        printed_messages = []
        fake_cp1252_stdout = MagicMock()
        fake_cp1252_stdout.encoding = "cp1252"

        def fake_print(*args, **kwargs):
            text = "".join(str(arg) for arg in args)
            if "🧠" in text:
                raise UnicodeEncodeError("cp1252", text, 0, 1, "character maps to <undefined>")
            printed_messages.append(text)

        with (
            patch.object(takeout_module, "LOGGER", fake_logger),
            patch.object(takeout_module, "suppress_console_output_temporarily", new=lambda *_args, **_kwargs: contextlib.nullcontext()),
            patch.object(takeout_module.subprocess, "Popen", return_value=FakeProcess()),
            patch.object(builtins, "print", side_effect=fake_print),
            patch.object(standalone_utils.sys, "stdout", fake_cp1252_stdout),
        ):
            returncode = takeout_module.run_command(
                ["dummy-gpth"],
                capture_output=True,
                capture_errors=True,
                print_messages=True,
                step_name="STEP : ",
            )

        self.assertEqual(returncode, 0)
        self.assertTrue(any("[INFO]" in message for message in printed_messages))
        self.assertTrue(any("?" in message for message in printed_messages))
        self.assertIn("STEP : [INFO] [Step 1/8] 🧠 Fixing file extensions : 2/2", [call.args[0] for call in fake_logger.info.call_args_list])

    def test_recover_orphan_album_assets_from_json_sidecars_creates_album_entry_from_all_photos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "Takeout"
            album_dir = input_root / "Google Photos" / "Album_1"
            album_dir.mkdir(parents=True)
            json_path = album_dir / "mi cocina.JPG.json"
            json_path.write_text(
                json.dumps(
                    {
                        "title": "mi cocina.JPG",
                        "photoTakenTime": {"timestamp": "1024570414"},
                        "creationTime": {"timestamp": "1415843421"},
                    }
                ),
                encoding="utf-8",
            )

            output_root = root / "Processed"
            all_photos_asset = output_root / "ALL_PHOTOS" / "2002" / "06" / "mi cocina.JPG"
            all_photos_asset.parent.mkdir(parents=True)
            all_photos_asset.write_bytes(b"fake-jpg")
            albums_root = output_root / "Albums"
            albums_root.mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                summary = recover_orphan_album_assets_from_json_sidecars(
                    input_folder=input_root,
                    output_folder=output_root,
                    albums_folder=albums_root,
                    no_symbolic_albums=False,
                    albums_structure="flatten",
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            recovered_entry = albums_root / "Album_1" / "mi cocina.JPG"
            self.assertEqual(summary["orphan_json_detected"], 1)
            self.assertEqual(summary["recovered_assets"], 1)
            self.assertEqual(summary["unresolved_assets"], 0)
            self.assertTrue(recovered_entry.exists() or recovered_entry.is_symlink())
            self.assertTrue(recovered_entry.is_symlink() or recovered_entry.read_bytes() == b"fake-jpg")

    def test_recover_orphan_album_assets_from_json_sidecars_respects_copy_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "Takeout"
            album_dir = input_root / "Google Photos" / "Album_1"
            album_dir.mkdir(parents=True)
            (album_dir / "New Album 1.jpg.json").write_text(
                json.dumps({"title": "New Album 1.jpg", "photoTakenTime": {"timestamp": "1024570414"}}),
                encoding="utf-8",
            )

            output_root = root / "Processed"
            all_photos_asset = output_root / "ALL_PHOTOS" / "2002" / "New Album 1.jpg"
            all_photos_asset.parent.mkdir(parents=True)
            all_photos_asset.write_bytes(b"asset")
            albums_root = output_root / "Albums"
            albums_root.mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                summary = recover_orphan_album_assets_from_json_sidecars(
                    input_folder=input_root,
                    output_folder=output_root,
                    albums_folder=albums_root,
                    no_symbolic_albums=True,
                    albums_structure="year/month",
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            recovered_entry = albums_root / "Album_1" / "2002" / "06" / "New Album 1.jpg"
            self.assertEqual(summary["recovered_assets"], 1)
            self.assertTrue(recovered_entry.is_file())
            self.assertFalse(recovered_entry.is_symlink())

    def test_extract_orphan_album_json_descriptor_ignores_album_metadata_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = Path(temp_dir) / "metadatos.json"
            json_path.write_text(
                json.dumps(
                    {
                        "title": "2002 - Casa de Quini (Alicante)",
                        "description": "",
                        "access": "protected",
                        "date": {
                            "timestamp": "1024570187",
                            "formatted": "20 jun 2002, 10:49:47 UTC",
                        },
                    }
                ),
                encoding="utf-8",
            )

            descriptor = _extract_orphan_album_json_descriptor(json_path)

        self.assertIsNone(descriptor)

    def test_recover_orphan_album_assets_from_json_sidecars_prefers_nearest_year_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_root = root / "Takeout"
            album_dir = input_root / "Google Photos" / "Album_1"
            album_dir.mkdir(parents=True)
            (album_dir / "mi cocina.JPG.json").write_text(
                json.dumps({"title": "mi cocina.JPG", "photoTakenTime": {"timestamp": "1009843200"}}),
                encoding="utf-8",
            )

            output_root = root / "Processed"
            farther_asset = output_root / "ALL_PHOTOS" / "1999" / "mi cocina.JPG"
            nearer_asset = output_root / "ALL_PHOTOS" / "2000" / "mi cocina.JPG"
            farther_asset.parent.mkdir(parents=True, exist_ok=True)
            nearer_asset.parent.mkdir(parents=True, exist_ok=True)
            farther_asset.write_bytes(b"farther-year")
            nearer_asset.write_bytes(b"nearer-year")

            albums_root = output_root / "Albums"
            albums_root.mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                summary = recover_orphan_album_assets_from_json_sidecars(
                    input_folder=input_root,
                    output_folder=output_root,
                    albums_folder=albums_root,
                    no_symbolic_albums=True,
                    albums_structure="flatten",
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            recovered_entry = albums_root / "Album_1" / "mi cocina.JPG"
            self.assertEqual(summary["recovered_assets"], 1)
            self.assertTrue(recovered_entry.is_file())
            self.assertEqual(recovered_entry.read_bytes(), b"nearer-year")

    def test_fix_metadata_with_gpth_tool_forces_hardlinks_for_windows_shortcut_albums(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_folder = root / "input"
            output_folder = root / "output"
            gpth_path = root / "gpth.exe"
            input_folder.mkdir()
            output_folder.mkdir()
            gpth_path.write_text("", encoding="utf-8")

            fake_logger = MagicMock()
            fake_logger.handlers = []

            with (
                patch.object(takeout_module, "LOGGER", fake_logger),
                patch.object(takeout_module, "ARGS", {"log-level": "info", "gpth-no-log": False}),
                patch.object(takeout_module, "get_os", return_value="windows"),
                patch.object(takeout_module, "get_arch", return_value="amd64"),
                patch.object(takeout_module, "get_gpth_tool_path", return_value=str(gpth_path)),
                patch.object(takeout_module, "ensure_executable"),
                patch.object(takeout_module, "print_arguments_pretty"),
                patch.object(takeout_module, "run_command", return_value=0) as mock_run_command,
            ):
                ok = takeout_module.fix_metadata_with_gpth_tool(
                    input_folder=str(input_folder),
                    output_folder=str(output_folder),
                    capture_output=True,
                    capture_errors=True,
                    print_messages=False,
                    no_symbolic_albums=False,
                    step_name="STEP : ",
                )

        self.assertTrue(ok)
        command = mock_run_command.call_args.args[0]
        self.assertIn("--albums", command)
        self.assertIn("shortcut", command)
        self.assertIn("--hardlink", command)

    def test_relocate_gpth_fix_outputs_moves_generated_artifacts_to_output_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fix_root = root / "Google Photos"
            output_root = root / "Processed"
            (fix_root / "ALL_PHOTOS" / "2002").mkdir(parents=True)
            (fix_root / "ALL_PHOTOS" / "2002" / "a.jpg").write_bytes(b"a")
            (fix_root / "Albums" / "Trip").mkdir(parents=True)
            (fix_root / "Albums" / "Trip" / "b.jpg").write_bytes(b"b")
            (fix_root / "Special_Folders" / "Locked").mkdir(parents=True)
            (fix_root / "Special_Folders" / "Locked" / "c.jpg").write_bytes(b"c")
            (fix_root.parent / "archive_browser.html").write_text("<html></html>", encoding="utf-8")

            with patch.object(takeout_module, "LOGGER", self.logger):
                ok = relocate_gpth_fix_outputs(
                    fix_root=str(fix_root),
                    output_folder=str(output_root),
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertTrue(ok)
            self.assertTrue((output_root / "ALL_PHOTOS" / "2002" / "a.jpg").is_file())
            self.assertTrue((output_root / "Albums" / "Trip" / "b.jpg").is_file())
            self.assertTrue((output_root / "Special_Folders" / "Locked" / "c.jpg").is_file())
            self.assertTrue((output_root / "archive_browser.html").is_file())
            self.assertFalse((fix_root / "ALL_PHOTOS").exists())
            self.assertFalse((fix_root / "Albums").exists())

    def test_relocate_gpth_fix_outputs_reclassifies_localized_special_folders_left_in_albums(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fix_root = root / "Google Photos"
            output_root = root / "Processed"
            (fix_root / "Albums" / "Archivo").mkdir(parents=True)
            (fix_root / "Albums" / "Archivo" / "a.jpg").write_bytes(b"a")
            (fix_root / "Albums" / "Papelera").mkdir(parents=True)
            (fix_root / "Albums" / "Papelera" / "b.jpg").write_bytes(b"b")
            (fix_root / "Albums" / "Carpeta privada").mkdir(parents=True)
            (fix_root / "Albums" / "Carpeta privada" / "c.jpg").write_bytes(b"c")

            with patch.object(takeout_module, "LOGGER", self.logger):
                ok = relocate_gpth_fix_outputs(
                    fix_root=str(fix_root),
                    output_folder=str(output_root),
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertTrue(ok)
            self.assertTrue((output_root / "Special Folders" / "Archivo" / "a.jpg").is_file())
            self.assertTrue((output_root / "Special Folders" / "Papelera" / "b.jpg").is_file())
            self.assertTrue((output_root / "Special Folders" / "Carpeta privada" / "c.jpg").is_file())
            self.assertFalse((output_root / "Albums" / "Archivo").exists())
            self.assertFalse((output_root / "Albums" / "Papelera").exists())
            self.assertFalse((output_root / "Albums" / "Carpeta privada").exists())

    def test_relocate_gpth_fix_outputs_reclassifies_special_folders_even_when_output_matches_fix_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Albums" / "Archive").mkdir(parents=True)
            (root / "Albums" / "Archive" / "a.jpg").write_bytes(b"a")
            (root / "Albums" / "Trash").mkdir(parents=True)
            (root / "Albums" / "Trash" / "b.jpg").write_bytes(b"b")
            (root / "Albums" / "Locked Folder").mkdir(parents=True)
            (root / "Albums" / "Locked Folder" / "c.jpg").write_bytes(b"c")

            with patch.object(takeout_module, "LOGGER", self.logger):
                ok = relocate_gpth_fix_outputs(
                    fix_root=str(root),
                    output_folder=str(root),
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertTrue(ok)
            self.assertTrue((root / "Special Folders" / "Archive" / "a.jpg").is_file())
            self.assertTrue((root / "Special Folders" / "Trash" / "b.jpg").is_file())
            self.assertTrue((root / "Special Folders" / "Locked Folder" / "c.jpg").is_file())
            self.assertFalse((root / "Albums" / "Archive").exists())
            self.assertFalse((root / "Albums" / "Trash").exists())
            self.assertFalse((root / "Albums" / "Locked Folder").exists())

    def test_relocate_gpth_fix_outputs_preserves_gpth_log_from_temporary_fix_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fix_root = root / "Google Photos"
            output_root = root / "Processed"
            (fix_root / "ALL_PHOTOS").mkdir(parents=True)
            (fix_root / "Albums").mkdir(parents=True)
            (fix_root / "gpth.log").write_text("gpth log", encoding="utf-8")

            with patch.object(takeout_module, "LOGGER", self.logger):
                ok = relocate_gpth_fix_outputs(
                    fix_root=str(fix_root),
                    output_folder=str(output_root),
                    step_name="TEST : ",
                    log_level=logging.INFO,
                )

            self.assertTrue(ok)
            self.assertTrue((output_root / "gpth.log").is_file())
            self.assertEqual((output_root / "gpth.log").read_text(encoding="utf-8"), "gpth log")
            self.assertFalse((fix_root / "gpth.log").exists())

    def test_fix_metadata_with_gpth_tool_uses_fix_mode_without_input_output_arguments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fix_root = root / "Google Photos"
            output_folder = root / "Processed"
            gpth_path = root / "gpth"
            fix_root.mkdir()
            output_folder.mkdir()
            gpth_path.write_text("", encoding="utf-8")
            (fix_root / "ALL_PHOTOS").mkdir()
            (fix_root / "Albums").mkdir()

            fake_logger = MagicMock()
            fake_logger.handlers = []

            with (
                patch.object(takeout_module, "LOGGER", fake_logger),
                patch.object(takeout_module, "ARGS", {"log-level": "info", "gpth-no-log": False}),
                patch.object(takeout_module, "get_os", return_value="linux"),
                patch.object(takeout_module, "get_arch", return_value="x64"),
                patch.object(takeout_module, "get_gpth_tool_path", return_value=str(gpth_path)),
                patch.object(takeout_module, "ensure_executable"),
                patch.object(takeout_module, "print_arguments_pretty"),
                patch.object(takeout_module, "run_command", return_value=0) as mock_run_command,
            ):
                ok = takeout_module.fix_metadata_with_gpth_tool(
                    input_folder=str(fix_root),
                    output_folder=str(output_folder),
                    capture_output=True,
                    capture_errors=True,
                    print_messages=False,
                    no_symbolic_albums=False,
                    ignore_takeout_structure=True,
                    step_name="STEP : ",
                )

            self.assertTrue(ok)
            command = mock_run_command.call_args.args[0]
            self.assertIn("--fix", command)
            self.assertIn(str(fix_root), command)
            self.assertNotIn("--input", command)
            self.assertNotIn("--output", command)
            self.assertTrue((output_folder / "ALL_PHOTOS").is_dir())
            self.assertTrue((output_folder / "Albums").is_dir())

    def test_fix_metadata_with_gpth_tool_relocates_special_folders_after_normal_gpth_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_folder = root / "Google Photos"
            output_folder = root / "Processed"
            gpth_path = root / "gpth"
            input_folder.mkdir()
            (output_folder / "Albums" / "Carpeta privada").mkdir(parents=True)
            (output_folder / "Albums" / "Carpeta privada" / "locked.jpg").write_bytes(b"x")
            gpth_path.write_text("", encoding="utf-8")

            fake_logger = MagicMock()
            fake_logger.handlers = []

            with (
                patch.object(takeout_module, "LOGGER", fake_logger),
                patch.object(takeout_module, "ARGS", {"log-level": "info", "gpth-no-log": False}),
                patch.object(takeout_module, "get_os", return_value="linux"),
                patch.object(takeout_module, "get_arch", return_value="x64"),
                patch.object(takeout_module, "get_gpth_tool_path", return_value=str(gpth_path)),
                patch.object(takeout_module, "ensure_executable"),
                patch.object(takeout_module, "print_arguments_pretty"),
                patch.object(takeout_module, "run_command", return_value=0) as mock_run_command,
                patch.object(takeout_module, "preserve_archive_browser_artifacts"),
            ):
                ok = takeout_module.fix_metadata_with_gpth_tool(
                    input_folder=str(input_folder),
                    output_folder=str(output_folder),
                    capture_output=True,
                    capture_errors=True,
                    print_messages=False,
                    no_symbolic_albums=False,
                    ignore_takeout_structure=False,
                    step_name="STEP : ",
                )

            self.assertTrue(ok)
            command = mock_run_command.call_args.args[0]
            self.assertIn("--input", command)
            self.assertIn("--output", command)
            self.assertTrue((output_folder / "Special Folders" / "Carpeta privada" / "locked.jpg").is_file())
            self.assertFalse((output_folder / "Albums" / "Carpeta privada").exists())

    def test_repair_conflicting_video_xmp_dates_rewrites_conflicting_video_tags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = root / "clip.mp4"
            exiftool_path = root / "exiftool"
            video_path.write_bytes(b"video")
            exiftool_path.write_text("", encoding="utf-8")
            entry = {
                "TargetFile": video_path.as_posix(),
                "OldestDate": "2025-10-19T08:02:06-04:00",
                "Source": "QuickTime:CreateDate",
                "QuickTime:CreateDate": "2025-10-19T08:02:06-04:00",
                "XMP:DateTimeOriginal": "2025-11-26T18:19:48-04:00",
                "XMP:DateTime": "2025-11-26T18:19:48-04:00",
                "XMP:ModifyDate": "2025-11-26T18:19:48-04:00",
            }
            analyzer = MagicMock()
            analyzer.get_extracted_dates.return_value = {video_path.as_posix(): entry}

            with (
                patch.object(takeout_module, "LOGGER", self.logger),
                patch.object(takeout_module, "get_exif_tool_path", return_value=str(exiftool_path)),
                patch.object(takeout_module, "ensure_executable"),
                patch.object(
                    takeout_module.subprocess,
                    "run",
                    return_value=MagicMock(returncode=0, stdout="", stderr=""),
                ) as mock_run,
            ):
                repaired = takeout_module.repair_conflicting_video_xmp_dates(
                    folder_analyzer=analyzer,
                    step_name="STEP : ",
                    log_level=logging.INFO,
                )

        self.assertEqual(repaired, 1)
        command = mock_run.call_args.args[0]
        self.assertEqual(command[0], str(exiftool_path))
        self.assertIn("-QuickTime:CreateDate=2025:10:19 08:02:06", command)
        self.assertIn("-XMP:DateTimeOriginal=2025:10:19 08:02:06", command)
        self.assertEqual(entry["XMP:DateTimeOriginal"], "2025-10-19T08:02:06-04:00")
        self.assertEqual(entry["XMP:DateTime"], "2025-10-19T08:02:06-04:00")
        self.assertEqual(entry["XMP:ModifyDate"], "2025-10-19T08:02:06-04:00")

    def test_repair_conflicting_video_xmp_dates_skips_already_aligned_video_tags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = root / "clip.mp4"
            exiftool_path = root / "exiftool"
            video_path.write_bytes(b"video")
            exiftool_path.write_text("", encoding="utf-8")
            entry = {
                "TargetFile": video_path.as_posix(),
                "OldestDate": "2025-10-19T08:02:06-04:00",
                "Source": "QuickTime:CreateDate",
                "QuickTime:CreateDate": "2025-10-19T08:02:06-04:00",
                "XMP:DateTimeOriginal": "2025-10-19T08:02:06-04:00",
                "XMP:DateTime": "2025-10-19T08:02:06-04:00",
                "XMP:ModifyDate": "2025-10-19T08:02:06-04:00",
            }
            analyzer = MagicMock()
            analyzer.get_extracted_dates.return_value = {video_path.as_posix(): entry}

            with (
                patch.object(takeout_module, "LOGGER", self.logger),
                patch.object(takeout_module, "get_exif_tool_path", return_value=str(exiftool_path)),
                patch.object(takeout_module, "ensure_executable"),
                patch.object(takeout_module.subprocess, "run") as mock_run,
            ):
                repaired = takeout_module.repair_conflicting_video_xmp_dates(
                    folder_analyzer=analyzer,
                    step_name="STEP : ",
                    log_level=logging.INFO,
                )

        self.assertEqual(repaired, 0)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
