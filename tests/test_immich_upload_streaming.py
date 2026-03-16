import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from requests_toolbelt.multipart.encoder import MultipartEncoder

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos


class TestImmichStreamingUpload(unittest.TestCase):
    def _build_manager(self):
        manager = ClassImmichPhotos.__new__(ClassImmichPhotos)
        manager.ALLOWED_IMMICH_MEDIA_EXTENSIONS = [".jpg"]
        manager.ALLOWED_IMMICH_SIDECAR_EXTENSIONS = [".xmp"]
        manager.IMMICH_URL = "http://immich.local"
        manager.API_KEY_LOGIN = True
        manager.IMMICH_USER_API_KEY = "test-api-key"
        manager.SESSION_TOKEN = None
        manager.login = lambda log_level=None: True
        return manager

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_uses_streaming_multipart_without_files_arg(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "asset-id", "status": "created"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")

            asset_id, is_duplicated = manager.push_asset(asset_path)

        self.assertEqual(asset_id, "asset-id")
        self.assertFalse(is_duplicated)

        kwargs = mock_post.call_args.kwargs
        self.assertNotIn("files", kwargs)
        self.assertIsInstance(kwargs["data"], MultipartEncoder)
        self.assertIn("multipart/form-data", kwargs["headers"]["Content-Type"])

    @patch("Features.ImmichPhotos.ClassImmichPhotos.LOGGER", new_callable=MagicMock)
    @patch("Features.ImmichPhotos.ClassImmichPhotos.requests.post")
    def test_push_asset_attaches_sidecar_in_multipart_fields(
        self, mock_post, _mock_logger
    ):
        manager = self._build_manager()

        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"id": "asset-id", "status": "created"}
        mock_post.return_value = response

        with tempfile.TemporaryDirectory() as tmpdir:
            asset_path = os.path.join(tmpdir, "photo.jpg")
            sidecar_path = os.path.join(tmpdir, "photo.xmp")
            with open(asset_path, "wb") as f:
                f.write(b"binary-data")
            with open(sidecar_path, "wb") as f:
                f.write(b"sidecar-data")

            manager.push_asset(asset_path)

        encoder = mock_post.call_args.kwargs["data"]
        self.assertIn("sidecarData", encoder.fields)


if __name__ == "__main__":
    unittest.main()
