import unittest
from tests.utils import get_test_file
from AutomaticMode import mode_AUTOMATIC_MIGRATION

class AutomaticMode(unittest.TestCase):
    def test_automatic_mode(self):
        result = mode_AUTOMATIC_MIGRATION(source='synology-photos', target='immich-photos', show_dashboard=False, parallel=True)
        self.assertTrue(result)
