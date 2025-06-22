import unittest
from tests.utils import get_test_file
from ClassImmichPhotos import ClassImmichPhotos

class TestImmichPhotosManager(unittest.TestCase):
    def setUp(self):
        config_path = get_test_file("config_test.ini")
        self.manager = ImmichPhotosManager(config=config_path)

    def test_remove_duplicates(self):
        removed = self.manager.remove_duplicates()
        self.assertGreaterEqual(removed, 0)
