import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import Core.FolderAnalyzer as folder_analyzer_module
import Features.LocalFolder.ClassLocalFolder as local_folder_module
from Features.LocalFolder.ClassLocalFolder import ClassLocalFolder


class TestLocalFolderTakeoutLayouts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.logger = logging.getLogger("test-local-folder-takeout-layouts")
        self.logger.handlers = []
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())
        self.logger.setLevel(logging.INFO)
        self.args = {
            "exclude-folders": [],
            "exclude-files": [],
            "filter-by-type": None,
            "filter-from-date": None,
            "filter-to-date": None,
        }

        self._create_file("Albums/Personal Album/personal.jpg")
        self._create_file("Albums-shared/Shared Album/shared.jpg")
        self._create_file("PARTNER_SHARED/Albums/Partner Album/partner.jpg")
        self._create_file("PARTNER_SHARED/ALL_PHOTOS/2024/partner-no-album.jpg")
        self._create_file("ALL_PHOTOS/2024/root-no-album.jpg")
        self._create_file("Special Folders/Archive/archive.jpg")
        self._create_file("Special Folders/Papelera/trash-es.jpg")
        self._create_file("Special Folders/Trash/trash-en.jpg")

        self.args_patcher_local = patch.object(local_folder_module, "ARGS", self.args)
        self.args_patcher_analyzer = patch.object(folder_analyzer_module, "ARGS", self.args)
        self.logger_patcher_local = patch.object(local_folder_module, "LOGGER", self.logger)
        self.logger_patcher_analyzer = patch.object(folder_analyzer_module, "LOGGER", self.logger)

        self.args_patcher_local.start()
        self.args_patcher_analyzer.start()
        self.logger_patcher_local.start()
        self.logger_patcher_analyzer.start()

    def tearDown(self):
        self.logger_patcher_analyzer.stop()
        self.logger_patcher_local.stop()
        self.args_patcher_analyzer.stop()
        self.args_patcher_local.stop()
        self.temp_dir.cleanup()

    def _create_file(self, relative_path):
        file_path = self.root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("data", encoding="utf-8")

    def test_takeout_partner_shared_and_special_folders_are_classified_correctly(self):
        local_folder = ClassLocalFolder(base_folder=self.root)

        albums = local_folder.get_albums_including_shared_with_user(log_level=logging.INFO)
        album_names = sorted(album["albumName"] for album in albums)
        self.assertEqual(
            album_names,
            ["Archive", "Partner Album", "Personal Album", "Shared Album"],
        )

        no_album_assets = local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        no_album_filenames = sorted(asset["filename"] for asset in no_album_assets)
        self.assertEqual(
            no_album_filenames,
            ["partner-no-album.jpg", "root-no-album.jpg"],
        )

    def test_remove_assets_refreshes_analyzer_with_supported_methods_and_invalidates_caches(self):
        removable = self.root / "ALL_PHOTOS/2024/remove-me.jpg"
        removable.parent.mkdir(parents=True, exist_ok=True)
        removable.write_text("delete", encoding="utf-8")

        local_folder = ClassLocalFolder(base_folder=self.root)
        removed_key = removable.resolve().as_posix()
        keep_key = (self.root / "ALL_PHOTOS/2024/root-no-album.jpg").resolve().as_posix()

        class AnalyzerStub:
            def __init__(self):
                self.extracted_dates = {
                    removed_key: {"TargetFile": removed_key},
                    keep_key: {"TargetFile": keep_key},
                }
                self._build_file_list_from_disk = Mock()
                self._apply_filters = Mock()
                self._compute_folder_sizes = Mock()

        local_folder.analyzer = AnalyzerStub()
        local_folder.all_assets_filtered = ["stale-all-assets"]
        local_folder.assets_without_albums_filtered = ["stale-no-albums"]
        local_folder.albums_assets_filtered = ["stale-album-assets"]

        removed_count = local_folder.remove_assets(str(removable), log_level=logging.INFO)

        self.assertEqual(removed_count, 1)
        self.assertFalse(removable.exists())
        self.assertNotIn(removed_key, local_folder.analyzer.extracted_dates)
        self.assertIn(keep_key, local_folder.analyzer.extracted_dates)
        local_folder.analyzer._build_file_list_from_disk.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.INFO,
        )
        local_folder.analyzer._apply_filters.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.INFO,
        )
        local_folder.analyzer._compute_folder_sizes.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.INFO,
        )
        self.assertIsNone(local_folder.all_assets_filtered)
        self.assertIsNone(local_folder.assets_without_albums_filtered)
        self.assertIsNone(local_folder.albums_assets_filtered)

    def test_remove_assets_initializes_analyzer_before_refresh_when_missing(self):
        removable = self.root / "ALL_PHOTOS/2024/remove-after-init.jpg"
        removable.parent.mkdir(parents=True, exist_ok=True)
        removable.write_text("delete", encoding="utf-8")

        local_folder = ClassLocalFolder(base_folder=self.root)

        class AnalyzerStub:
            def __init__(self):
                self.extracted_dates = {}
                self._build_file_list_from_disk = Mock()
                self._apply_filters = Mock()
                self._compute_folder_sizes = Mock()

        analyzer_stub = AnalyzerStub()

        def fake_ensure_analyzer(log_level=None):
            local_folder.analyzer = analyzer_stub

        with patch.object(local_folder, "_ensure_analyzer", side_effect=fake_ensure_analyzer) as mock_ensure:
            removed_count = local_folder.remove_assets(str(removable), log_level=logging.WARNING)

        self.assertEqual(removed_count, 1)
        self.assertFalse(removable.exists())
        mock_ensure.assert_called_once_with(log_level=logging.WARNING)
        analyzer_stub._build_file_list_from_disk.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.WARNING,
        )
        analyzer_stub._apply_filters.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.WARNING,
        )
        analyzer_stub._compute_folder_sizes.assert_called_once_with(
            step_name="remove_assets: ",
            log_level=logging.WARNING,
        )


if __name__ == "__main__":
    unittest.main()
