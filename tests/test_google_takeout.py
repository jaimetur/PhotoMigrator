import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Features.GoogleTakeout.ClassTakeoutFolder as takeout_module
from Features.GoogleTakeout.ClassTakeoutFolder import (
    _find_forbidden_special_folder_in_path,
    _is_takeout_year_folder,
    contains_takeout_structure,
)


class TestGoogleTakeoutHelpers(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test-google-takeout")
        self.logger.handlers = []
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())

    def test_is_takeout_year_folder_supports_localized_names(self):
        self.assertTrue(_is_takeout_year_folder("Photos from 2024"))
        self.assertTrue(_is_takeout_year_folder("Fotos del 2024"))
        self.assertTrue(_is_takeout_year_folder("Fotos von 2024"))
        self.assertFalse(_is_takeout_year_folder("Holiday Album 2024"))

    def test_find_forbidden_special_folder_in_path_detects_special_components(self):
        offending = _find_forbidden_special_folder_in_path("/tmp/Export/Trash/Takeout")
        self.assertEqual(offending, "Trash")

    def test_contains_takeout_structure_detects_nested_localized_year_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Google Photos" / "Fotos del 2024").mkdir(parents=True)

            with patch.object(takeout_module, "LOGGER", self.logger):
                detected = contains_takeout_structure(str(root), log_level=logging.INFO)

        self.assertTrue(detected)


if __name__ == "__main__":
    unittest.main()
