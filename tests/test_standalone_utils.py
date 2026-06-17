import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from Utils.StandaloneUtils import get_exif_tool_path
    STANDALONE_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    STANDALONE_IMPORT_ERROR = exc


class TestStandaloneUtils(unittest.TestCase):
    def setUp(self):
        if STANDALONE_IMPORT_ERROR is not None:
            self.skipTest(f"Standalone utils dependencies are not installed in this environment: {STANDALONE_IMPORT_ERROR}")

    def test_get_exif_tool_path_falls_back_to_system_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exiftool_path = Path(temp_dir) / "exiftool"
            exiftool_path.write_text("", encoding="utf-8")

            with (
                patch("Utils.StandaloneUtils.platform.system", return_value="Darwin"),
                patch("Utils.StandaloneUtils.shutil.which", side_effect=lambda name: str(exiftool_path) if name == "exiftool" else None),
            ):
                resolved = get_exif_tool_path("missing_exiftool_folder")

        self.assertEqual(resolved, str(exiftool_path))

    def test_get_exif_tool_path_accepts_command_name_override_from_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exiftool_path = Path(temp_dir) / "exiftool-custom"
            exiftool_path.write_text("", encoding="utf-8")

            with (
                patch("Utils.StandaloneUtils.platform.system", return_value="Darwin"),
                patch("Utils.StandaloneUtils.shutil.which", side_effect=lambda name: str(exiftool_path) if name == "exiftool-custom" else None),
            ):
                resolved = get_exif_tool_path("exiftool-custom")

        self.assertEqual(resolved, str(exiftool_path))


if __name__ == "__main__":
    unittest.main()
