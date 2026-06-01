import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Utils.FileUtils import get_all_files_paths, get_subfolders, should_exclude_path


class TestExclusionPatterns(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "keep").mkdir()
        (self.root / "@eaDir").mkdir()
        (self.root / ".@__thumb").mkdir()
        (self.root / "keep" / "photo.jpg").write_text("ok", encoding="utf-8")
        (self.root / "keep" / "SYNOFILE_THUMB_M.jpg").write_text("thumb", encoding="utf-8")
        (self.root / "@eaDir" / "ignored.jpg").write_text("ignored", encoding="utf-8")
        (self.root / ".@__thumb" / "ignored2.jpg").write_text("ignored", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_subfolders_supports_glob_exclusions(self):
        subfolders = get_subfolders(
            input_folder=str(self.root),
            exclusion_subfolders=["@eaDir", ".@__thumb"],
        )
        self.assertEqual([Path(item).name for item in subfolders], ["keep"])

    def test_get_all_files_paths_supports_folder_and_file_exclusions(self):
        files = get_all_files_paths(
            input_folder=str(self.root),
            exclusion_folders=["@eaDir", ".@__thumb"],
            exclusion_files=["SYNOFILE_THUMB*"],
        )
        self.assertEqual([Path(item).name for item in files], ["photo.jpg"])

    def test_should_exclude_path_checks_folder_components_and_filename(self):
        self.assertTrue(
            should_exclude_path(
                self.root / ".@__thumb" / "nested.jpg",
                exclusion_folders=[".@__thumb"],
            )
        )
        self.assertTrue(
            should_exclude_path(
                self.root / "keep" / "SYNOFILE_THUMB_M.jpg",
                exclusion_files=["SYNOFILE_THUMB*"],
            )
        )
        self.assertFalse(
            should_exclude_path(
                self.root / "keep" / "photo.jpg",
                exclusion_folders=["@eaDir"],
                exclusion_files=["Thumbs.db"],
            )
        )


if __name__ == "__main__":
    unittest.main()
