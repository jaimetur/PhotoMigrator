import contextlib
import builtins
import io
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

sys.modules.setdefault("piexif", MagicMock())

try:
    import Features.GoogleTakeout.ClassTakeoutFolder as takeout_module
    from Features.GoogleTakeout.ClassTakeoutFolder import (
        _find_forbidden_special_folder_in_path,
        _is_takeout_year_folder,
        contains_takeout_structure,
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

    def test_contains_takeout_structure_detects_nested_localized_year_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Google Photos" / "Fotos del 2024").mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                detected = contains_takeout_structure(str(root), log_level=logging.INFO)

        self.assertTrue(detected)

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
