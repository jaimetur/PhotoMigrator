import inspect
import unittest

from Features.GooglePhotos.ClassGooglePhotos import ClassGooglePhotos
from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
from Features.LocalFolder.ClassLocalFolder import ClassLocalFolder
from Features.NextCloudPhotos.ClassNextCloudPhotos import ClassNextCloudPhotos
from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos


CLIENT_CLASSES = [
    ClassLocalFolder,
    ClassSynologyPhotos,
    ClassImmichPhotos,
    ClassNextCloudPhotos,
    ClassGooglePhotos,
]


EXPECTED_SIGNATURES = {
    "get_client_name": ["self", "log_level"],
    "create_album": ["self", "album_name", "shared", "log_level"],
    "get_albums_owned_by_user": ["self", "filter_assets", "log_level"],
    "get_albums_including_shared_with_user": ["self", "filter_assets", "log_level"],
    "get_all_assets_from_album": ["self", "album_id", "album_name", "type", "album_scope", "album_expected_count", "log_level"],
    "get_all_assets_from_album_shared": ["self", "album_id", "album_name", "type", "album_passphrase", "album_scope", "album_expected_count", "log_level"],
    "get_all_assets_without_albums": ["self", "type", "log_level"],
    "get_all_assets_from_all_albums": ["self", "log_level"],
    "add_assets_to_album": ["self", "album_id", "asset_ids", "album_name", "log_level", "return_details"],
    "push_asset": ["self", "file_path", "log_level", "resolve_duplicate_id"],
    "pull_asset": ["self", "asset_id", "asset_filename", "asset_time", "download_folder", "album_passphrase", "album_id", "album_scope", "log_level"],
}


class TestClientPublicContracts(unittest.TestCase):
    def test_client_public_method_parameter_names_are_aligned(self):
        for method_name, expected_parameters in EXPECTED_SIGNATURES.items():
            for client_cls in CLIENT_CLASSES:
                with self.subTest(client=client_cls.__name__, method=method_name):
                    signature = inspect.signature(getattr(client_cls, method_name))
                    self.assertEqual(list(signature.parameters.keys()), expected_parameters)


if __name__ == "__main__":
    unittest.main()
