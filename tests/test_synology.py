import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos


class TestSynologyPhotosUnit(unittest.TestCase):
    def setUp(self):
        self.manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)

    def test_filter_assets_by_type_supports_photo_aliases_and_live_assets(self):
        assets = [
            {"id": "1", "type": "PHOTO"},
            {"id": "2", "type": "LIVE"},
            {"id": "3", "type": "VIDEO"},
        ]

        filtered = self.manager.filter_assets_by_type(assets, "photos")

        self.assertEqual([asset["id"] for asset in filtered], ["1", "2"])

    def test_filter_assets_by_date_respects_epoch_range(self):
        assets = [
            {"id": "old", "time": 100},
            {"id": "inside", "time": 200},
            {"id": "new", "time": 300},
        ]

        filtered = self.manager.filter_assets_by_date(assets, from_date=150, to_date=250)

        self.assertEqual([asset["id"] for asset in filtered], ["inside"])

    def test_filter_assets_by_place_matches_nested_address_values(self):
        assets = [
            {"id": "1", "additional": {"address": {"city": "Madrid"}}},
            {"id": "2", "additional": {"address": {"country": "Spain"}}},
            {"id": "3", "additional": {"address": {"city": "Berlin"}}},
        ]

        filtered = self.manager.filter_assets_by_place(assets, "spa")

        self.assertEqual([asset["id"] for asset in filtered], ["2"])

    def _prepare_push_manager(self):
        manager = ClassSynologyPhotos.__new__(ClassSynologyPhotos)
        manager.ALLOWED_MEDIA_EXTENSIONS = [".jpg"]
        manager.ALLOWED_SIDECAR_EXTENSIONS = [".xmp"]
        manager.SYNOLOGY_URL = "http://synology.local"
        manager.SYNO_TOKEN_HEADER = {}
        manager.SESSION = MagicMock()
        manager.login = lambda log_level=None: True
        return manager

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_returns_existing_id_for_duplicate_response(self, _mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"id": "existing-asset-id", "action": "ignore"},
        }
        manager.SESSION.post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "existing-asset-id")
        self.assertTrue(is_duplicated)

    @patch("Features.SynologyPhotos.ClassSynologyPhotos.LOGGER", new_callable=MagicMock)
    def test_push_asset_rejects_duplicate_response_without_existing_id(self, mock_logger):
        manager = self._prepare_push_manager()
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "success": True,
            "data": {"action": "ignore"},
        }
        manager.SESSION.post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as handle:
                handle.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertIsNone(asset_id)
        self.assertIsNone(is_duplicated)
        mock_logger.warning.assert_called()


if __name__ == "__main__":
    unittest.main()
