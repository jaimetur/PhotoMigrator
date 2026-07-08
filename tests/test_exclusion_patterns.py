import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import types


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "colorama" not in sys.modules:
    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(
        RED="",
        GREEN="",
        YELLOW="",
        CYAN="",
        WHITE="",
        BLUE="",
        MAGENTA="",
    )
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="", DIM="", NORMAL="")
    sys.modules["colorama"] = colorama_stub

if "piexif" not in sys.modules:
    piexif_stub = types.ModuleType("piexif")
    piexif_stub.ExifIFD = types.SimpleNamespace(DateTimeOriginal=36867, DateTimeDigitized=36868)
    piexif_stub.ImageIFD = types.SimpleNamespace(DateTime=306)
    piexif_stub.load = lambda *args, **kwargs: {"0th": {}, "Exif": {}}
    piexif_stub.dump = lambda *args, **kwargs: b""
    piexif_stub.insert = lambda *args, **kwargs: None
    sys.modules["piexif"] = piexif_stub

from Utils import FileUtils
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

    def test_sanitize_and_unpack_zips_uses_runtime_global_logger_when_module_logger_is_none(self):
        zip_path = self.root / "sample.zip"
        with zipfile.ZipFile(zip_path, "w") as zip_ref:
            zip_ref.writestr("Album/Test File.jpg", b"ok")

        unzip_root = self.root / "unzipped"
        runtime_logger = MagicMock()

        with (
            patch.object(FileUtils, "LOGGER", None),
            patch.object(FileUtils.GV, "LOGGER", runtime_logger),
        ):
            FileUtils.sanitize_and_unpack_zips(
                input_folder=str(self.root),
                unzip_folder=str(unzip_root),
                step_name="[test] ",
            )

        self.assertTrue((unzip_root / "Album" / "Test File.jpg").exists())
        runtime_logger.info.assert_any_call("[test] Unzipping: sample.zip")


if __name__ == "__main__":
    unittest.main()
