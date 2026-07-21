import logging
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue
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

import Core.GlobalVariables as GV
import Features.AutomaticMigration.AutomaticMigration as automatic_module


class TestAutomaticMigrationHelpers(unittest.TestCase):
    def test_build_web_dashboard_snapshot_uses_structured_counters(self):
        shared_data = automatic_module.SharedData(
            info={
                "source_client_name": "Local Folder",
                "target_client_name": "Immich Photos",
                "asset_transfer_start_time": "2026-07-16T10:00:00Z",
                "total_assets": 500,
                "total_photos": 420,
                "total_videos": 80,
                "total_albums": 12,
                "total_metadata": 30,
                "total_sidecar": 10,
                "total_invalid": 2,
                "total_albums_blocked": 1,
                "assets_in_queue": 7,
                "album_assoc_queue_size": 4,
                "delayed_assets_pending": 3,
            },
            counters={
                "total_assets_blocked": 9,
                "total_pulled_assets": 240,
                "total_pulled_photos": 200,
                "total_pulled_videos": 40,
                "total_pulled_albums": 11,
                "total_pull_failed_assets": 3,
                "total_pull_failed_photos": 2,
                "total_pull_failed_videos": 1,
                "total_pull_failed_albums": 0,
                "total_pushed_assets": 210,
                "total_pushed_photos": 180,
                "total_pushed_videos": 30,
                "total_pushed_albums": 9,
                "total_push_queued_assets": 219,
                "total_push_queued_photos": 187,
                "total_push_queued_videos": 32,
                "total_push_duplicates_assets": 5,
                "total_push_duplicates_photos": 4,
                "total_push_duplicates_videos": 1,
                "total_push_failed_assets": 4,
                "total_push_failed_photos": 3,
                "total_push_failed_videos": 1,
                "total_push_failed_albums": 0,
                "total_push_retry_recovered_assets": 8,
                "total_push_retry_failed_assets": 2,
                "total_push_retry_scheduled_assets": 10,
                "total_delayed_queue_assets": 9,
                "total_album_assoc_queue_assets": 6,
                "total_consolidated_albums": 6,
                "total_canonicalized_albums": 4,
                "total_target_empty_albums_removed": 2,
                "total_album_assoc_retry_scheduled_assets": 7,
                "total_album_assoc_retry_recovered_assets": 5,
                "total_album_assoc_failed_assets": 1,
            },
            logs_queue=None,
        )

        snapshot = automatic_module._build_web_dashboard_snapshot(shared_data, parallel=True)

        self.assertEqual(snapshot["migrationMode"], "parallel")
        self.assertEqual(snapshot["sourceClientName"], "Local Folder")
        self.assertEqual(snapshot["targetClientName"], "Immich Photos")
        self.assertEqual(snapshot["assetTransferStartedAt"], "2026-07-16T10:00:00Z")
        self.assertEqual(snapshot["pulledAssets"], 240)
        self.assertEqual(snapshot["pushedAssets"], 210)
        self.assertEqual(snapshot["pushQueuedAssets"], 219)
        self.assertEqual(snapshot["pushDuplicatePhotos"], 4)
        self.assertEqual(snapshot["pushRetryScheduled"], 10)
        self.assertEqual(snapshot["delayedRetriesQueueTotal"], 9)
        self.assertEqual(snapshot["albumAssocQueueTotal"], 6)
        self.assertEqual(snapshot["assetsInQueue"], 7)
        self.assertEqual(snapshot["albumAssocQueue"], 4)
        self.assertEqual(snapshot["delayedRetriesQueue"], 3)
        self.assertEqual(snapshot["blockedAssets"], 9)
        self.assertEqual(snapshot["pushRetryRecovered"], 8)
        self.assertEqual(snapshot["pushRetryFailed"], 2)
        self.assertEqual(snapshot["consolidatedAlbums"], 6)
        self.assertEqual(snapshot["canonicalizedAlbums"], 4)
        self.assertEqual(snapshot["targetEmptyAlbumsRemoved"], 2)
        self.assertEqual(snapshot["albumAssocRetryScheduled"], 7)
        self.assertEqual(snapshot["albumAssocRetryRecovered"], 5)
        self.assertEqual(snapshot["albumAssocUnconfirmed"], 1)

    def test_web_dashboard_snapshot_uses_the_same_physical_totals_for_pull_and_push(self):
        shared_data = automatic_module.SharedData(
            info={
                "total_assets": 10,
                "total_photos": 7,
                "total_videos": 3,
            },
            counters={
                # A Live Photo companion raises the transferred video count
                # above the source's logical video-record count.
                "total_pulled_assets": 12,
                "total_pulled_photos": 7,
                "total_pulled_videos": 5,
                "total_pull_failed_assets": 1,
                "total_pull_failed_photos": 1,
                "total_pull_failed_videos": 0,
                "total_push_queued_assets": 12,
                "total_push_queued_photos": 7,
                "total_push_queued_videos": 5,
            },
            logs_queue=None,
        )

        snapshot = automatic_module._build_web_dashboard_snapshot(shared_data, parallel=True)

        self.assertEqual(snapshot["totalAssets"], 13)
        self.assertEqual(snapshot["totalPhotos"], 8)
        self.assertEqual(snapshot["totalVideos"], 5)
        self.assertEqual(snapshot["pushTotalAssets"], 13)
        self.assertEqual(snapshot["pushTotalPhotos"], 8)
        self.assertEqual(snapshot["pushTotalVideos"], 5)

    def test_compute_dashboard_estimated_time_returns_estimate_from_processed_and_pending_assets(self):
        estimated = automatic_module._compute_dashboard_estimated_time(
            elapsed_seconds=120,
            total_assets=100,
            processed_assets=20,
            pending_assets=80,
        )

        self.assertEqual(estimated, "0:08:00")

    def test_compute_dashboard_estimated_time_handles_zero_processed_assets(self):
        estimated = automatic_module._compute_dashboard_estimated_time(
            elapsed_seconds=120,
            total_assets=100,
            processed_assets=0,
            pending_assets=100,
        )

        self.assertEqual(estimated, "Estimating...")

    def test_compute_dashboard_estimated_end_uses_local_time_for_valid_duration(self):
        estimated_end = automatic_module._compute_dashboard_estimated_end(
            "01:02:03",
            now=datetime(2026, 7, 19, 10, 30, 0),
        )

        self.assertEqual(estimated_end, "2026-07-19 11:32:03")
        self.assertEqual(automatic_module._compute_dashboard_estimated_end("Estimating..."), "-")

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

    def test_record_unique_counter_counts_each_key_once(self):
        counters = {}
        seen = set()

        first = automatic_module._record_unique_counter(counters, "total_consolidated_albums", seen, "album-1")
        second = automatic_module._record_unique_counter(counters, "total_consolidated_albums", seen, "album-1")
        third = automatic_module._record_unique_counter(counters, "total_consolidated_albums", seen, "album-2")

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(third)
        self.assertEqual(counters["total_consolidated_albums"], 2)

    def test_remove_target_empty_albums_if_supported_returns_removed_count(self):
        target = unittest.mock.Mock()
        target.remove_empty_albums.return_value = 3

        removed = automatic_module._remove_target_empty_albums_if_supported(target, log_level=logging.INFO)

        self.assertEqual(removed, 3)
        target.remove_empty_albums.assert_called_once_with(log_level=logging.INFO)

    def test_remove_target_empty_albums_if_supported_ignores_unsupported_targets(self):
        target = unittest.mock.Mock(spec=[])

        removed = automatic_module._remove_target_empty_albums_if_supported(target, log_level=logging.INFO)

        self.assertEqual(removed, 0)

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

    def test_build_physical_transfer_stats_counts_live_photo_as_two_physical_assets(self):
        self.assertEqual(
            automatic_module._build_physical_transfer_stats("photo", include_live_companion=True),
            {"assets": 2, "photos": 1, "videos": 1},
        )
        self.assertEqual(
            automatic_module._build_physical_transfer_stats("video"),
            {"assets": 1, "photos": 0, "videos": 1},
        )

    def test_increment_pull_counters_uses_physical_stats_bundle(self):
        counters = {
            "total_pulled_assets": 0,
            "total_pulled_photos": 0,
            "total_pulled_videos": 0,
        }

        automatic_module._increment_pull_counters(
            counters,
            asset_type="photo",
            asset_stats={"assets": 2, "photos": 1, "videos": 1},
        )

        self.assertEqual(counters["total_pulled_assets"], 2)
        self.assertEqual(counters["total_pulled_photos"], 1)
        self.assertEqual(counters["total_pulled_videos"], 1)

    def test_increment_push_duplicate_counters_uses_physical_stats_bundle(self):
        counters = {
            "total_push_duplicates_assets": 0,
            "total_push_duplicates_photos": 0,
            "total_push_duplicates_videos": 0,
        }

        automatic_module._increment_push_duplicate_counters(
            counters,
            asset_type="photo",
            asset_stats={"assets": 2, "photos": 1, "videos": 1},
        )

        self.assertEqual(counters["total_push_duplicates_assets"], 2)
        self.assertEqual(counters["total_push_duplicates_photos"], 1)
        self.assertEqual(counters["total_push_duplicates_videos"], 1)

    def test_move_to_album_association_failed_preserves_relative_folder_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            album_folder = temp_root / automatic_module.AUTOMATIC_MIGRATION_PUSH_QUEUE_FOLDER / "Albums" / "Fotos Javi"
            album_folder.mkdir(parents=True)
            photo = album_folder / "IMG_0001.JPG"
            video = album_folder / "IMG_0001.MP4"
            photo.write_text("photo", encoding="utf-8")
            video.write_text("video", encoding="utf-8")

            moved = automatic_module._move_to_album_association_failed_folder(
                temp_folder=str(temp_root),
                album_name="Fotos Javi",
                asset_file_path=str(photo),
                live_photo_video_path=str(video),
                log_level=logging.INFO,
            )

            failed_album_folder = temp_root / automatic_module.AUTOMATIC_MIGRATION_ALBUM_ASSOC_FAILED_FOLDER / "Albums" / "Fotos Javi"
            self.assertEqual(
                moved,
                {
                    "asset_file_path": str(failed_album_folder / "IMG_0001.JPG"),
                    "live_photo_video_path": str(failed_album_folder / "IMG_0001.MP4"),
                },
            )
            self.assertFalse(photo.exists())
            self.assertFalse(video.exists())
            self.assertTrue((failed_album_folder / "IMG_0001.JPG").exists())
            self.assertTrue((failed_album_folder / "IMG_0001.MP4").exists())

    def test_move_staged_asset_between_queues_preserves_relative_folder_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            queued_photo = temp_root / "Push_Queue" / "Albums" / "MiAlbum" / "IMG_0001.JPG"
            queued_photo.parent.mkdir(parents=True)
            queued_photo.write_text("photo", encoding="utf-8")

            delayed_asset = automatic_module._move_staged_asset_to_queue_folder(
                str(temp_root),
                {"asset_file_path": str(queued_photo)},
                automatic_module.AUTOMATIC_MIGRATION_DELAYED_QUEUE_FOLDER,
            )
            expected_delayed = temp_root / "Push_Delayed_Queue" / "Albums" / "MiAlbum" / "IMG_0001.JPG"

            self.assertEqual(delayed_asset["asset_file_path"], str(expected_delayed))
            self.assertFalse(queued_photo.exists())
            self.assertTrue(expected_delayed.exists())
            self.assertFalse((temp_root / "Push_Queue" / "Albums").exists())
            self.assertTrue((temp_root / "Push_Queue").exists())

    def test_count_staged_queue_files_ignores_runtime_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_folder = Path(tmpdir) / automatic_module.AUTOMATIC_MIGRATION_ALBUM_ASSOC_QUEUE_FOLDER / "Albums" / "MiAlbum"
            queue_folder.mkdir(parents=True)
            (queue_folder / "IMG_0001.JPG").write_text("photo", encoding="utf-8")
            (queue_folder / "IMG_0001.MP4").write_text("video", encoding="utf-8")
            (queue_folder / ".active").write_text("active", encoding="utf-8")
            (queue_folder / "IMG_0002.JPG.lock").write_text("lock", encoding="utf-8")
            synology_metadata = queue_folder / "@eaDir" / "IMG_0001.JPG"
            synology_metadata.parent.mkdir()
            synology_metadata.write_text("thumbnail", encoding="utf-8")

            count = automatic_module._count_staged_queue_files(
                tmpdir,
                automatic_module.AUTOMATIC_MIGRATION_ALBUM_ASSOC_QUEUE_FOLDER,
            )

            self.assertEqual(count, 2)

    def test_stage_local_asset_moves_and_preserves_source_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = Path(tmpdir) / "source"
            source_photo = source_root / "Albums" / "MiAlbum" / "IMG_0001.JPG"
            source_photo.parent.mkdir(parents=True)
            source_photo.write_text("photo", encoding="utf-8")
            local_client = object.__new__(automatic_module.ClassLocalFolder)
            local_client.base_folder = source_root
            queue_root = Path(tmpdir) / "Automatic_Migration" / "Push_Queue"

            staged_path = automatic_module._stage_local_asset_for_automatic_migration(
                source_client=local_client,
                source_asset_id=str(source_photo),
                asset_filename=source_photo.name,
                asset_time=None,
                queue_root=str(queue_root),
                move_assets=True,
            )

            expected_path = queue_root / "Albums" / "MiAlbum" / "IMG_0001.JPG"
            self.assertEqual(staged_path, str(expected_path))
            self.assertFalse(source_photo.exists())
            self.assertTrue(expected_path.exists())

    def test_stage_local_symlink_copies_target_into_album_path_and_removes_only_link_on_move(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = Path(tmpdir) / "source"
            physical_photo = source_root / "ALL_PHOTOS" / "2020" / "01" / "IMG_0001.JPG"
            album_link = source_root / "Albums" / "Album1" / "IMG_0001.JPG"
            physical_photo.parent.mkdir(parents=True)
            album_link.parent.mkdir(parents=True)
            physical_photo.write_text("photo", encoding="utf-8")
            album_link.symlink_to(physical_photo)
            local_client = object.__new__(automatic_module.ClassLocalFolder)
            local_client.base_folder = source_root
            queue_root = Path(tmpdir) / "Automatic_Migration" / "Push_Queue"

            physical_staged = automatic_module._stage_local_asset_for_automatic_migration(
                local_client, str(physical_photo), physical_photo.name, None, str(queue_root), move_assets=True,
            )
            album_staged = automatic_module._stage_local_asset_for_automatic_migration(
                local_client, str(album_link), album_link.name, None, str(queue_root), move_assets=True,
            )

            self.assertEqual(physical_staged, str(queue_root / "ALL_PHOTOS" / "2020" / "01" / "IMG_0001.JPG"))
            self.assertEqual(album_staged, str(queue_root / "Albums" / "Album1" / "IMG_0001.JPG"))
            self.assertFalse(physical_photo.exists())
            self.assertFalse(album_link.exists())
            self.assertTrue((queue_root / "ALL_PHOTOS" / "2020" / "01" / "IMG_0001.JPG").is_file())
            self.assertTrue((queue_root / "Albums" / "Album1" / "IMG_0001.JPG").is_file())
            self.assertFalse((queue_root / "Albums" / "Album1" / "IMG_0001.JPG").is_symlink())

    def test_finalize_album_assoc_failed_asset_safely_returns_none_when_cleanup_raises(self):
        logger = unittest.mock.Mock()

        def failing_finalizer(**_kwargs):
            raise RuntimeError("cleanup failed")

        result = automatic_module._finalize_album_assoc_failed_asset_safely(
            failing_finalizer,
            report_logger=logger,
            log_asset_file_path="/tmp/Carpeta privada/VID_20170914_005330.mp4",
            log_album_name="Carpeta privada",
            asset_id="asset-1",
        )

        self.assertIsNone(result)
        logger.error.assert_called_once()

    def test_finalize_album_assoc_failed_asset_safely_returns_finalizer_result(self):
        logger = unittest.mock.Mock()

        def ok_finalizer(**_kwargs):
            return 12.5

        result = automatic_module._finalize_album_assoc_failed_asset_safely(
            ok_finalizer,
            report_logger=logger,
            log_asset_file_path="/tmp/Album/IMG_0001.JPG",
            log_album_name="Album",
            asset_id="asset-1",
        )

        self.assertEqual(result, 12.5)
        logger.error.assert_not_called()

    def test_is_blocked_synology_shared_album_returns_false_for_non_synology_sources(self):
        local_client = object.__new__(automatic_module.ClassLocalFolder)
        album = {"id": "album-1", "albumName": "Album"}

        blocked = automatic_module._is_blocked_synology_shared_album(local_client, album)

        self.assertFalse(blocked)

    def test_is_blocked_synology_shared_album_delegates_for_synology_sources(self):
        synology_client = object.__new__(automatic_module.ClassSynologyPhotos)
        synology_client.is_blocked_shared_album = unittest.mock.Mock(return_value=True)
        album = {"id": "album-1", "albumName": "Album"}

        blocked = automatic_module._is_blocked_synology_shared_album(synology_client, album)

        self.assertTrue(blocked)
        synology_client.is_blocked_shared_album.assert_called_once_with(album)

    def test_asset_path_is_reserved_detects_in_flight_paths(self):
        queue = PriorityQueue()
        in_flight = {automatic_module._normalized_asset_path_key("/tmp/Album/IMG_2088.MP4")}
        lock = threading.Lock()

        reserved = automatic_module._asset_path_is_reserved(
            queue=queue,
            in_flight_paths=in_flight,
            in_flight_lock=lock,
            path="/tmp/Album/IMG_2088.MP4",
        )

        self.assertTrue(reserved)

    def test_asset_path_is_reserved_detects_paths_still_in_queue(self):
        queue = PriorityQueue()
        queue.put((0, 1, {"asset_file_path": "/tmp/Album/IMG_2088.MP4"}))
        lock = threading.Lock()

        reserved = automatic_module._asset_path_is_reserved(
            queue=queue,
            in_flight_paths=set(),
            in_flight_lock=lock,
            path="/tmp/Album/IMG_2088.MP4",
        )

        self.assertTrue(reserved)

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

    def test_mark_album_pushed_if_ready_ignores_excluded_housekeeping_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_folder = Path(tmpdir) / "Album A"
            (album_folder / "@eaDir").mkdir(parents=True)
            (album_folder / "@eaDir" / "thumb.jpg").write_text("thumb", encoding="utf-8")
            (album_folder / ".DS_Store").write_text("junk", encoding="utf-8")
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
        self.assertFalse(album_folder.exists())
        self.assertEqual(counters["total_pushed_albums"], 1)

    def test_mark_album_pushed_if_ready_counts_pruned_folder_as_drained(self):
        counters = {"total_pushed_albums": 0}
        processed_albums = set()
        lock = threading.Lock()
        logger = unittest.mock.Mock()

        counted = automatic_module._mark_album_pushed_if_ready(
            album_name="Album A",
            album_folder_path="/nonexistent/Album A",
            processed_albums=processed_albums,
            processed_albums_lock=lock,
            counters=counters,
            logger=logger,
        )

        self.assertTrue(counted)
        self.assertEqual(counters["total_pushed_albums"], 1)
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

    def test_cleanup_local_source_album_folders_after_push_removes_effectively_empty_local_album(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            album_folder = root / "Albums/Album A"
            (album_folder / "@eaDir").mkdir(parents=True)
            (album_folder / "@eaDir" / "thumb.jpg").write_text("thumb", encoding="utf-8")
            (album_folder / ".DS_Store").write_text("junk", encoding="utf-8")
            (album_folder / ".active").write_text("busy", encoding="utf-8")

            local_client = object.__new__(automatic_module.ClassLocalFolder)
            local_client.FOLDER_EXCLUSION_PATTERNS = ["@eaDir", "@Recycle", ".*"]
            local_client.FILE_EXCLUSION_PATTERNS = [".DS_Store", "Thumbs.db", "._*"]

            removed = automatic_module._cleanup_local_source_album_folders_after_push(
                source_client=local_client,
                album_name="Album A",
                source_album_paths_by_name={"Album A": {str(album_folder)}},
                log_level=logging.INFO,
            )

        self.assertEqual(removed, 1)
        self.assertFalse(album_folder.exists())

    def test_parse_dashboard_progress_line_supports_simple_gpth_counter_frames(self):
        parsed = automatic_module._parse_dashboard_progress_line(
            "__TQDM__ [INFO] [Step 8/8] Updating creation times : 42/100"
        )

        self.assertEqual(
            parsed,
            {
                "desc": "[Step 8/8] Updating creation times",
                "current": 42,
                "total": 100,
                "has_total": True,
            },
        )

    def test_parse_dashboard_progress_line_strips_spaced_info_prefixes(self):
        parsed = automatic_module._parse_dashboard_progress_line(
            "__TQDM__ [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Writing EXIF data : 100/100"
        )

        self.assertEqual(
            parsed,
            {
                "desc": "[PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Writing EXIF data",
                "current": 100,
                "total": 100,
                "has_total": True,
            },
        )
        self.assertEqual(
            automatic_module._normalize_bg_progress_desc(parsed["desc"]),
            "[Step 7/8] Writing EXIF data",
        )

    def test_select_visible_bg_progress_rows_prioritizes_recent_active_rows(self):
        rows = [
            {"label": "Step 5", "completed": True, "last_update": 10.0},
            {"label": "Step 6", "completed": False, "last_update": 20.0},
            {"label": "Step 7", "completed": True, "last_update": 30.0},
            {"label": "Step 8", "completed": False, "last_update": 40.0},
            {"label": "Step 4", "completed": True, "last_update": 50.0},
            {"label": "Step 3", "completed": False, "last_update": 5.0},
        ]

        visible = automatic_module._select_visible_bg_progress_rows(rows, 5)

        self.assertEqual(
            [item["label"] for item in visible],
            ["Step 8", "Step 6", "Step 3", "Step 4", "Step 7"],
        )


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
            "prefer-canonical-album-names": False,
            "consolidate-similar-albums": False,
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
