import os
import unittest
from tests.utils import get_test_file
from Features.GoogleTakeout.ClassTakeoutFolder import ClassTakeoutFolder

class TestGoogleTakeoutProcessor(unittest.TestCase):
    def setUp(self):
        self.zip_path = get_test_file("takeout.zip")
        self.processor = ClassTakeoutFolder(self.zip_path)

    def test_precheck_takeout_and_calculate_initial_counters(self):
        self.processor.precheck_takeout_and_calculate_initial_counters()
        output_path = os.path.join(os.path.dirname(self.zip_path), "unpacked")
        self.assertTrue(os.path.exists(output_path))
