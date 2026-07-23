import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import Core.FolderAnalyzer as folder_analyzer_module
import Features.LocalPhotosFolder.ClassLocalPhotosFolder as local_folder_module
from Features.LocalPhotosFolder.ClassLocalPhotosFolder import ClassLocalPhotosFolder


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
        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

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

    def test_analyzer_does_not_exclude_source_files_because_an_ancestor_is_hidden(self):
        hidden_source = self.root / ".web-dev" / "data" / "Synology"
        media_file = hidden_source / "No_Albums" / "2025" / "10" / "photo.jpg"
        media_file.parent.mkdir(parents=True)
        media_file.write_text("data", encoding="utf-8")

        analyzer = folder_analyzer_module.FolderAnalyzer(
            folder_path=str(hidden_source),
            force_date_extraction=False,
            logger=self.logger,
        )

        self.assertEqual(analyzer.file_list, [media_file.resolve().as_posix()])
        self.assertEqual(analyzer.filtered_file_list, [media_file.resolve().as_posix()])

    def test_managed_layout_treats_memories_root_as_album_collections(self):
        self._create_file("Memories/Summer Recap/memory-a.jpg")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        albums = local_folder.get_albums_including_shared_with_user(log_level=logging.INFO)
        album_names = sorted(album["albumName"] for album in albums)
        self.assertIn("Summer Recap", album_names)

        no_album_assets = local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        no_album_filenames = sorted(asset["filename"] for asset in no_album_assets)
        self.assertNotIn("memory-a.jpg", no_album_filenames)

    def test_all_album_assets_passes_album_name_to_manifest_aware_lookup(self):
        local_folder = object.__new__(ClassLocalPhotosFolder)
        local_folder.albums_assets_filtered = None
        local_folder.get_albums_including_shared_with_user = Mock(return_value=[{
            "id": "album-id",
            "albumName": "Summer Live Photos",
        }])
        local_folder.get_all_assets_from_album = Mock(return_value=[{"id": "asset-id"}])

        assets = local_folder.get_all_assets_from_all_albums(log_level=logging.INFO)

        self.assertEqual(assets, [{"id": "asset-id"}])
        local_folder.get_albums_including_shared_with_user.assert_called_once_with(
            filter_assets=False,
            log_level=logging.INFO,
        )
        local_folder.get_all_assets_from_album.assert_called_once_with(
            album_id="album-id",
            album_name="Summer Live Photos",
            log_level=logging.INFO,
        )

    def test_manifest_assigned_no_album_asset_is_not_returned_twice(self):
        self._create_file("Albums/Manifest Album/album-info.json")
        (self.root / "automatic_migration_album_manifest.json").write_text(
            json.dumps({"albums": {"Manifest Album": ["root-no-album.jpg"]}}),
            encoding="utf-8",
        )
        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        no_album_filenames = {
            asset["filename"]
            for asset in local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        }

        self.assertNotIn("root-no-album.jpg", no_album_filenames)

    def test_determine_file_type_treats_real_icloud_metadata_csv_as_metadata_but_not_generic_reports(self):
        metadata_csv = self.root / "Albums/Trip/Photo Details.csv"
        metadata_csv.parent.mkdir(parents=True, exist_ok=True)
        metadata_csv.write_text(
            "ImgName,FileChecksum,Original Creation Date,Import Date,Favorite\n"
            "IMG_0001.JPG,abc,2024-01-01,2024-01-02,false\n",
            encoding="utf-8",
        )
        generic_csv = self.root / "No_Date_Assets.csv"
        generic_csv.write_text("filename,path\nIMG_0002.JPG,/tmp/IMG_0002.JPG\n", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        self.assertEqual(local_folder._determine_file_type(metadata_csv), "metadata")
        self.assertEqual(local_folder._determine_file_type(generic_csv), "unknown")

    def test_determine_file_type_treats_webp_as_image(self):
        webp_file = self.root / "ALL_PHOTOS/2024/IMG_20210805_112248_719.webp"
        webp_file.parent.mkdir(parents=True, exist_ok=True)
        webp_file.write_text("img", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        self.assertEqual(local_folder._determine_file_type(webp_file), "image")

    def test_progress_json_is_unknown_and_mp_is_counted_as_unsupported(self):
        progress_json = self.root / "ALL_PHOTOS/2024/progress.json"
        progress_json.parent.mkdir(parents=True, exist_ok=True)
        progress_json.write_text("{}", encoding="utf-8")

        mp_file = self.root / "ALL_PHOTOS/2024/PXL_20230512_222825532.MP"
        mp_file.write_text("img", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        self.assertEqual(local_folder._determine_file_type(progress_json), "unknown")
        self.assertEqual(local_folder._determine_file_type(mp_file), "unknown")

        unsupported_assets = local_folder.get_all_assets_without_albums(type="unsupported", log_level=logging.INFO)
        unsupported_filenames = sorted(asset["filename"] for asset in unsupported_assets)

        self.assertIn("progress.json", unsupported_filenames)
        self.assertIn("PXL_20230512_222825532.MP", unsupported_filenames)

        all_assets = local_folder.get_all_assets_without_albums(type="all", log_level=logging.INFO)
        all_filenames = sorted(asset["filename"] for asset in all_assets)

        self.assertNotIn("progress.json", all_filenames)
        self.assertNotIn("PXL_20230512_222825532.MP", all_filenames)

    def test_remove_assets_refreshes_analyzer_with_supported_methods_and_invalidates_caches(self):
        removable = self.root / "ALL_PHOTOS/2024/remove-me.jpg"
        removable.parent.mkdir(parents=True, exist_ok=True)
        removable.write_text("delete", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)
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

    def test_remove_empty_folders_treats_excluded_synology_artifacts_as_empty(self):
        self.args["exclude-folders"] = ["@eaDir"]
        self.args["exclude-files"] = [".DS_Store", "Thumbs.db"]
        cleanup_root = self.root / "ALL_PHOTOS/2009"
        (cleanup_root / "@eaDir").mkdir(parents=True, exist_ok=True)
        (cleanup_root / "@eaDir" / "SYNOPHOTO_THUMB_XL.jpg").write_text("thumb", encoding="utf-8")
        (cleanup_root / ".DS_Store").write_text("junk", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

        removed = local_folder.remove_empty_folders(log_level=logging.INFO)

        self.assertGreaterEqual(removed, 1)
        self.assertFalse(cleanup_root.exists())

    def test_cleanup_after_move_assets_removes_effectively_empty_source_root(self):
        clean_root = self.root / "CleanupRoot"
        (clean_root / "Albums/OnlyExcluded/@eaDir").mkdir(parents=True, exist_ok=True)
        (clean_root / "Albums/OnlyExcluded/@eaDir/thumb.jpg").write_text("thumb", encoding="utf-8")
        (clean_root / "Albums/OnlyExcluded/.DS_Store").write_text("junk", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=clean_root)
        summary = local_folder.cleanup_after_move_assets(log_level=logging.INFO)

        self.assertTrue(summary["root_removed"])
        self.assertFalse(clean_root.exists())

    def test_cleanup_after_move_assets_ignores_runtime_lock_markers_when_pruning_empty_tree(self):
        clean_root = self.root / "CleanupRootWithLocks"
        (clean_root / "Albums/OnlyRuntimeMarkers").mkdir(parents=True, exist_ok=True)
        (clean_root / "Albums/OnlyRuntimeMarkers/.active").write_text("busy", encoding="utf-8")
        (clean_root / "Albums/OnlyRuntimeMarkers/asset.jpg.lock").write_text("busy", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=clean_root)
        summary = local_folder.cleanup_after_move_assets(log_level=logging.INFO)

        self.assertTrue(summary["root_removed"])
        self.assertFalse(clean_root.exists())

    def test_remove_assets_initializes_analyzer_before_refresh_when_missing(self):
        removable = self.root / "ALL_PHOTOS/2024/remove-after-init.jpg"
        removable.parent.mkdir(parents=True, exist_ok=True)
        removable.write_text("delete", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)

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

    def test_remove_assets_can_skip_analyzer_refresh_for_quiet_bulk_deletes(self):
        removable = self.root / "ALL_PHOTOS/2024/remove-without-refresh.jpg"
        removable.parent.mkdir(parents=True, exist_ok=True)
        removable.write_text("delete", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=self.root)
        removed_key = removable.resolve().as_posix()

        class AnalyzerStub:
            def __init__(self):
                self.extracted_dates = {
                    removed_key: {"TargetFile": removed_key},
                }
                self._build_file_list_from_disk = Mock()
                self._apply_filters = Mock()
                self._compute_folder_sizes = Mock()

        local_folder.analyzer = AnalyzerStub()

        removed_count = local_folder.remove_assets(
            str(removable),
            log_level=logging.WARNING,
            refresh_analyzer=False,
            log_removed_count=False,
        )

        self.assertEqual(removed_count, 1)
        self.assertFalse(removable.exists())
        self.assertNotIn(removed_key, local_folder.analyzer.extracted_dates)
        local_folder.analyzer._build_file_list_from_disk.assert_not_called()
        local_folder.analyzer._apply_filters.assert_not_called()
        local_folder.analyzer._compute_folder_sizes.assert_not_called()

    def test_plain_local_folder_does_not_create_managed_layout_and_detects_top_level_albums(self):
        plain_root = self.root / "plain-source"
        plain_root.mkdir(parents=True, exist_ok=True)
        (plain_root / "root-photo.jpg").write_text("data", encoding="utf-8")
        (plain_root / "root-video.mp4").write_text("data", encoding="utf-8")
        (plain_root / "Trip 2024").mkdir(parents=True, exist_ok=True)
        (plain_root / "Trip 2024" / "trip-a.jpg").write_text("data", encoding="utf-8")
        (plain_root / "Family").mkdir(parents=True, exist_ok=True)
        (plain_root / "Family" / "family-a.jpg").write_text("data", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=plain_root)

        self.assertFalse((plain_root / "Albums").exists())
        self.assertFalse((plain_root / "Albums-shared").exists())
        self.assertFalse((plain_root / "ALL_PHOTOS").exists())

        albums = local_folder.get_albums_including_shared_with_user(log_level=logging.INFO)
        album_names = sorted(album["albumName"] for album in albums)
        self.assertEqual(album_names, ["Family", "Trip 2024"])

        no_album_assets = local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        no_album_filenames = sorted(asset["filename"] for asset in no_album_assets)
        self.assertEqual(no_album_filenames, ["root-photo.jpg", "root-video.mp4"])

    def test_takeout_master_library_without_albums_is_a_managed_non_album_root(self):
        takeout_root = self.root / "takeout-without-albums"
        all_photos_file = takeout_root / "ALL_PHOTOS" / "2024" / "01" / "takeout-only.jpg"
        all_photos_file.parent.mkdir(parents=True, exist_ok=True)
        all_photos_file.write_text("data", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=takeout_root)

        self.assertTrue(local_folder._uses_managed_layout())
        no_album_assets = local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        self.assertEqual([asset["filename"] for asset in no_album_assets], ["takeout-only.jpg"])

    def test_plain_local_folder_treats_memories_subfolders_as_album_collections(self):
        plain_root = self.root / "plain-memories-source"
        plain_root.mkdir(parents=True, exist_ok=True)
        (plain_root / "root-photo.jpg").write_text("data", encoding="utf-8")
        (plain_root / "Family").mkdir(parents=True, exist_ok=True)
        (plain_root / "Family" / "family-a.jpg").write_text("data", encoding="utf-8")
        (plain_root / "Memories" / "Summer Recap").mkdir(parents=True, exist_ok=True)
        (plain_root / "Memories" / "Summer Recap" / "memory-a.jpg").write_text("data", encoding="utf-8")

        local_folder = ClassLocalPhotosFolder(base_folder=plain_root)

        albums = local_folder.get_albums_including_shared_with_user(log_level=logging.INFO)
        album_names = sorted(album["albumName"] for album in albums)
        self.assertEqual(album_names, ["Family", "Summer Recap"])

        no_album_assets = local_folder.get_all_assets_without_albums(log_level=logging.INFO)
        no_album_filenames = sorted(asset["filename"] for asset in no_album_assets)
        self.assertEqual(no_album_filenames, ["root-photo.jpg"])

    def test_shared_albums_folder_is_created_only_when_a_shared_album_is_created(self):
        plain_root = self.root / "plain-target"
        plain_root.mkdir(parents=True, exist_ok=True)

        local_folder = ClassLocalPhotosFolder(base_folder=plain_root)

        self.assertFalse((plain_root / "Albums-shared").exists())

        shared_album_path = local_folder.create_album("Shared Album", shared=True, log_level=logging.INFO)

        self.assertTrue((plain_root / "Albums-shared").is_dir())
        self.assertEqual(shared_album_path.resolve(), (plain_root / "Albums-shared" / "Shared Album").resolve())


if __name__ == "__main__":
    unittest.main()
