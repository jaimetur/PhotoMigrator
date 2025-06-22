import unittest
from tests.utils import get_test_file

from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos

class TestSynologyPhotos(unittest.TestCase):
    def setUp(self):
        config_path = get_test_file("config_test.ini")
        self.manager = ClassSynologyPhotos(config=config_path)

    def test_upload_album(self):
        album_path = get_test_file("album1")
        result = self.manager.upload_album(album_path)
        self.assertTrue(result)
