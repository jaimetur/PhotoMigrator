import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Core.GlobalVariables as GV
import Features.AutomaticMigration.AutomaticMigration as automatic_module


class TestAutomaticMigrationHelpers(unittest.TestCase):
    def test_pull_has_content_handles_common_types(self):
        self.assertTrue(automatic_module._pull_has_content(True))
        self.assertTrue(automatic_module._pull_has_content(2))
        self.assertTrue(automatic_module._pull_has_content(" file "))
        self.assertTrue(automatic_module._pull_has_content([1]))
        self.assertFalse(automatic_module._pull_has_content(0))
        self.assertFalse(automatic_module._pull_has_content(""))
        self.assertFalse(automatic_module._pull_has_content([]))

    def test_nextcloud_not_found_error_detection_is_case_insensitive(self):
        error = RuntimeError("Photo not found for user: abc")
        self.assertTrue(automatic_module._is_nextcloud_photo_not_found_error(error))
        self.assertFalse(automatic_module._is_nextcloud_photo_not_found_error(RuntimeError("other error")))


class TestAutomaticMigrationMode(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()

        self.logger = logging.getLogger("test-automatic-migration")
        self.logger.handlers = []
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())
        self.logger.setLevel(logging.INFO)

        self.base_args = {
            "parallel-migration": False,
            "source": "",
            "target": "",
            "dashboard": False,
            "show-gpth-info": False,
            "show-gpth-errors": True,
            "account-id": 1,
            "filter-by-type": None,
            "filter-from-date": None,
            "filter-to-date": None,
            "filter-by-country": None,
            "filter-by-city": None,
            "filter-by-person": None,
            "exclude-folders": [],
            "exclude-files": [],
            "move-assets": False,
            "google-takeout": "",
            "google-ignore-check-structure": False,
            "google-output-folder-suffix": "processed",
            "google-skip-move-albums": False,
            "google-skip-gpth-tool": False,
            "google-skip-extras-files": False,
            "google-keep-takeout-folder": False,
            "output-folder": "",
            "foldername-extracted-dates": "",
            "foldername-duplicates-output": "",
            "foldername-logs": "",
            "foldername-albums": "",
            "foldername-no-albums": "",
            "configuration-file": "",
            "exec-gpth-tool": "",
            "exec-exif-tool": "",
            "gpth-no-log": False,
        }
        self.help_texts = {
            "AUTOMATIC-MIGRATION": "Migrate from <SOURCE> Cloud Service to <TARGET>."
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mode_automatic_migration_uses_local_folder_clients(self):
        with (
            patch.object(automatic_module, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "HELP_TEXTS", self.help_texts),
            patch.object(automatic_module, "LOGGER", self.logger),
            patch.object(GV, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "confirm_continue", return_value=True),
            patch.object(automatic_module, "contains_zip_files", return_value=False),
            patch.object(automatic_module, "contains_takeout_structure", return_value=False),
            patch("Features.LocalFolder.ClassLocalFolder.ARGS", dict(self.base_args)),
            patch("Features.LocalFolder.ClassLocalFolder.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.ARGS", dict(self.base_args)),
            patch("Core.FolderAnalyzer.LOGGER", self.logger),
            patch.object(automatic_module, "parallel_automatic_migration") as mock_parallel,
        ):
            automatic_module.mode_AUTOMATIC_MIGRATION(
                source=str(self.source),
                target=str(self.target),
                show_dashboard=False,
                parallel=False,
                log_level=logging.INFO,
            )

        self.assertEqual(mock_parallel.call_count, 1)
        kwargs = mock_parallel.call_args.kwargs
        self.assertIn("Local Folder", kwargs["source_client"].get_client_name())
        self.assertIn("Local Folder", kwargs["target_client"].get_client_name())

    def test_mode_automatic_migration_processes_takeout_source_before_parallel_flow(self):
        takeout_google_photos = self.source / "Google Photos"
        (takeout_google_photos / "Photos from 2024").mkdir(parents=True)

        with (
            patch.object(automatic_module, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "HELP_TEXTS", self.help_texts),
            patch.object(automatic_module, "LOGGER", self.logger),
            patch.object(GV, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "confirm_continue", return_value=True),
            patch.object(automatic_module, "contains_zip_files", return_value=False),
            patch.object(
                automatic_module,
                "contains_takeout_structure",
                side_effect=lambda path, log_level=None: Path(path) == self.source,
            ),
            patch("Features.LocalFolder.ClassLocalFolder.ARGS", dict(self.base_args)),
            patch("Features.GoogleTakeout.ClassTakeoutFolder.LOGGER", self.logger),
            patch("Features.LocalFolder.ClassLocalFolder.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.ARGS", dict(self.base_args)),
            patch("Features.GoogleTakeout.ClassTakeoutFolder.ClassTakeoutFolder.process") as mock_process,
            patch("Features.GoogleTakeout.ClassTakeoutFolder.ClassTakeoutFolder._ensure_analyzer") as mock_ensure_analyzer,
            patch.object(automatic_module, "parallel_automatic_migration") as mock_parallel,
        ):
            automatic_module.mode_AUTOMATIC_MIGRATION(
                source=str(self.source),
                target=str(self.target),
                show_dashboard=False,
                parallel=False,
                log_level=logging.INFO,
            )

        self.assertEqual(mock_process.call_count, 1)
        self.assertEqual(mock_ensure_analyzer.call_count, 1)
        self.assertEqual(mock_parallel.call_count, 1)


if __name__ == "__main__":
    unittest.main()
