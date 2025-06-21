import os
import unittest
from tests.utils import get_test_file


class TestGoogleTakeoutProcessor(unittest.TestCase):
    def setUp(self):
        self.zip_path = get_test_file("takeout.zip")
        self.processor = GoogleTakeoutProcessor(self.zip_path)

    def test_unpack_zip(self):
        self.processor.unpack_zip()
        output_path = os.path.join(os.path.dirname(self.zip_path), "unpacked")
        self.assertTrue(os.path.exists(output_path))
