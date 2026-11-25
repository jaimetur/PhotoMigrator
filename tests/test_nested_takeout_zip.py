import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from Utils.FileUtils import sanitize_and_unpack_zips


class TestNestedTakeoutZip(unittest.TestCase):
    def test_zip_inside_a_zip_is_unpacked_into_the_unzip_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inner = root / "inner.zip"
            with zipfile.ZipFile(inner, "w") as archive:
                archive.writestr("Takeout/Google Photos/Photos from 2024/a.jpg", b"jpg")
                archive.writestr("Takeout/Google Photos/Photos from 2024/a.jpg.json", "{}")
            input_folder = root / "input"
            input_folder.mkdir()
            with zipfile.ZipFile(input_folder / "Takeout-short.zip", "w") as archive:
                archive.write(inner, "Takeout-short/Takeout-short.zip")
            unzip_folder = root / "unzipped"

            sanitize_and_unpack_zips(str(input_folder), str(unzip_folder))

            self.assertTrue((unzip_folder / "Takeout" / "Google Photos" / "Photos from 2024" / "a.jpg").is_file())
            self.assertEqual(list(unzip_folder.rglob("*.zip")), [])
            self.assertFalse((unzip_folder / "Takeout-short").exists())


if __name__ == "__main__":
    unittest.main()
