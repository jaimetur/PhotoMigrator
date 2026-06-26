import logging
import tempfile
import threading
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

    def test_remove_source_asset_after_move_uses_quiet_local_delete_path(self):
        local_client = object.__new__(automatic_module.ClassLocalFolder)
        local_client.remove_assets = unittest.mock.Mock(return_value=1)

        removed = automatic_module._remove_source_asset_after_move(
            source_client=local_client,
            asset_id="/tmp/photo.jpg",
            log_level=logging.INFO,
        )

        self.assertEqual(removed, 1)
        local_client.remove_assets.assert_called_once_with(
            asset_ids="/tmp/photo.jpg",
            log_level=logging.WARNING,
            refresh_analyzer=False,
            log_removed_count=False,
        )

    def test_remove_source_asset_after_move_preserves_default_behavior_for_remote_clients(self):
        remote_client = unittest.mock.Mock()
        remote_client.remove_assets.return_value = 1

        removed = automatic_module._remove_source_asset_after_move(
            source_client=remote_client,
            asset_id="abc123",
            log_level=logging.ERROR,
        )

        self.assertEqual(removed, 1)
        remote_client.remove_assets.assert_called_once_with(asset_ids="abc123", log_level=logging.ERROR)

    def test_mark_album_pushed_if_ready_counts_album_once_when_folder_is_drained(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_folder = Path(tmpdir) / "Album A"
            album_folder.mkdir()
            counters = {"total_pushed_albums": 0, "total_pulled_albums": 5}
            processed_albums = set()
            lock = threading.Lock()
            logger = unittest.mock.Mock()

            counted = automatic_module._mark_album_pushed_if_ready(
                album_name="Album A",
                album_folder_path=str(album_folder),
                processed_albums=processed_albums,
                processed_albums_lock=lock,
                counters=counters,
                logger=logger,
            )

        self.assertTrue(counted)
        self.assertEqual(counters["total_pushed_albums"], 1)
        self.assertEqual(processed_albums, {"Album A"})
        logger.info.assert_called_once_with("Album Pushed    : 'Album A'")

    def test_mark_album_pushed_if_ready_waits_until_active_marker_is_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_folder = Path(tmpdir) / "Album B"
            album_folder.mkdir()
            active_file = album_folder / ".active"
            active_file.write_text("busy", encoding="utf-8")
            counters = {"total_pushed_albums": 0, "total_pulled_albums": 3}
            processed_albums = set()
            lock = threading.Lock()
            logger = unittest.mock.Mock()

            first_attempt = automatic_module._mark_album_pushed_if_ready(
                album_name="Album B",
                album_folder_path=str(album_folder),
                processed_albums=processed_albums,
                processed_albums_lock=lock,
                counters=counters,
                logger=logger,
            )

            active_file.unlink()

            second_attempt = automatic_module._mark_album_pushed_if_ready(
                album_name="Album B",
                album_folder_path=str(album_folder),
                processed_albums=processed_albums,
                processed_albums_lock=lock,
                counters=counters,
                logger=logger,
            )

        self.assertFalse(first_attempt)
        self.assertTrue(second_attempt)
        self.assertEqual(counters["total_pushed_albums"], 1)


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
        self.assertIn("Local Folder", kwargs["source_client"].CLIENT_NAME)
        self.assertIn("Local Folder", kwargs["target_client"].CLIENT_NAME)

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
        self.assertNotIn("metadata_json_file", mock_ensure_analyzer.call_args.kwargs)
        self.assertEqual(mock_ensure_analyzer.call_args.kwargs.get("log_level"), logging.INFO)

    def test_mode_automatic_migration_processes_icloud_takeout_source_before_parallel_flow(self):
        (self.source / "PartA").mkdir(parents=True, exist_ok=True)
        (self.source / "PartA" / "Photo Details.csv").write_text(
            "imgName,fileChecksum,originalCreationDate,importDate\n",
            encoding="utf-8",
        )
        process_calls = []

        def capture_process(self, *args, **kwargs):
            process_calls.append(dict(self.ARGS))

        with (
            patch.object(automatic_module, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "HELP_TEXTS", self.help_texts),
            patch.object(automatic_module, "LOGGER", self.logger),
            patch.object(GV, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "confirm_continue", return_value=True),
            patch.object(automatic_module, "contains_zip_files", return_value=False),
            patch.object(automatic_module, "contains_takeout_structure", return_value=False),
            patch.object(
                automatic_module,
                "contains_icloud_takeout_structure",
                side_effect=lambda path, log_level=None: Path(path) == self.source,
            ),
            patch("Features.LocalFolder.ClassLocalFolder.ARGS", dict(self.base_args)),
            patch("Features.ICloudTakeout.ClassICloudTakeoutFolder.ARGS", dict(self.base_args)),
            patch("Features.LocalFolder.ClassLocalFolder.LOGGER", self.logger),
            patch("Features.ICloudTakeout.ClassICloudTakeoutFolder.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.ARGS", dict(self.base_args)),
            patch(
                "Features.ICloudTakeout.ClassICloudTakeoutFolder.ClassICloudTakeoutFolder.process",
                autospec=True,
                side_effect=capture_process,
            ) as mock_process,
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
        self.assertEqual(mock_parallel.call_count, 1)
        self.assertEqual(len(process_calls), 1)
        self.assertTrue(process_calls[0]["icloud-include-memories"])
        kwargs = mock_parallel.call_args.kwargs
        self.assertIn("Local Folder", kwargs["source_client"].CLIENT_NAME)
        self.assertIn("_processed_", str(kwargs["source_client"].base_folder))

    def test_mode_automatic_migration_unzips_local_zip_source_before_detecting_icloud_takeout(self):
        expected_unzip = Path(f"{self.source}_unzipped_{automatic_module.TIMESTAMP}").resolve()
        process_takeout_roots = []

        def fake_unzip(input_folder, unzip_folder, step_name="", log_level=None):
            Path(unzip_folder).mkdir(parents=True, exist_ok=True)

        def capture_process(self, *args, **kwargs):
            process_takeout_roots.append(self.takeout_folder)

        with (
            patch.object(automatic_module, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "HELP_TEXTS", self.help_texts),
            patch.object(automatic_module, "LOGGER", self.logger),
            patch.object(GV, "ARGS", dict(self.base_args)),
            patch.object(automatic_module, "confirm_continue", return_value=True),
            patch.object(
                automatic_module,
                "contains_zip_files",
                side_effect=lambda path, log_level=None: Path(path).resolve() == self.source.resolve(),
            ),
            patch.object(automatic_module, "contains_takeout_structure", return_value=False),
            patch.object(
                automatic_module,
                "contains_icloud_takeout_structure",
                side_effect=lambda path, log_level=None: Path(path).resolve() == expected_unzip,
            ),
            patch.object(automatic_module, "sanitize_and_unpack_zips", side_effect=fake_unzip) as mock_unzip,
            patch("Features.LocalFolder.ClassLocalFolder.ARGS", dict(self.base_args)),
            patch("Features.ICloudTakeout.ClassICloudTakeoutFolder.ARGS", dict(self.base_args)),
            patch("Features.LocalFolder.ClassLocalFolder.LOGGER", self.logger),
            patch("Features.ICloudTakeout.ClassICloudTakeoutFolder.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.LOGGER", self.logger),
            patch("Core.FolderAnalyzer.ARGS", dict(self.base_args)),
            patch(
                "Features.ICloudTakeout.ClassICloudTakeoutFolder.ClassICloudTakeoutFolder.process",
                autospec=True,
                side_effect=capture_process,
            ) as mock_process,
            patch.object(automatic_module, "parallel_automatic_migration") as mock_parallel,
        ):
            automatic_module.mode_AUTOMATIC_MIGRATION(
                source=str(self.source),
                target=str(self.target),
                show_dashboard=False,
                parallel=False,
                log_level=logging.INFO,
            )

        self.assertEqual(mock_unzip.call_count, 1)
        self.assertEqual(mock_process.call_count, 1)
        self.assertEqual(mock_parallel.call_count, 1)
        self.assertEqual(process_takeout_roots, [expected_unzip])


if __name__ == "__main__":
    unittest.main()
