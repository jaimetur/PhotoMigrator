import sys
import types
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if "piexif" not in sys.modules:
    piexif_stub = types.ModuleType("piexif")
    piexif_stub.ExifIFD = types.SimpleNamespace(DateTimeOriginal=36867, DateTimeDigitized=36868)
    piexif_stub.ImageIFD = types.SimpleNamespace(DateTime=306)
    piexif_stub.load = lambda *args, **kwargs: {"0th": {}, "Exif": {}}
    piexif_stub.dump = lambda *args, **kwargs: b""
    piexif_stub.insert = lambda *args, **kwargs: None
    sys.modules["piexif"] = piexif_stub

if "colorama" not in sys.modules:
    colorama_stub = types.ModuleType("colorama")
    colorama_stub.init = lambda *args, **kwargs: None
    colorama_stub.Fore = types.SimpleNamespace(RED="", GREEN="", YELLOW="", CYAN="", WHITE="", BLUE="", MAGENTA="")
    colorama_stub.Style = types.SimpleNamespace(RESET_ALL="", BRIGHT="", DIM="", NORMAL="")
    sys.modules["colorama"] = colorama_stub

try:
    from Utils.GeneralUtils import match_pattern, replace_pattern
    GENERAL_UTILS_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    GENERAL_UTILS_IMPORT_ERROR = exc


class TestGeneralUtilsPatterns(unittest.TestCase):
    def setUp(self):
        if GENERAL_UTILS_IMPORT_ERROR is not None:
            self.skipTest(f"GeneralUtils dependencies are not installed in this environment: {GENERAL_UTILS_IMPORT_ERROR}")

    def test_replace_pattern_supports_literal_replacement(self):
        self.assertEqual(replace_pattern("Trip -- Summer", "--", "-"), "Trip - Summer")

    def test_match_pattern_supports_literal_matching(self):
        self.assertTrue(match_pattern("Temp Album", "Temp"))

    def test_match_pattern_supports_wildcard_matching(self):
        self.assertTrue(match_pattern("Holiday--Draft", "*--*"))

    def test_replace_pattern_supports_wildcard_replacement_in_middle(self):
        self.assertEqual(replace_pattern("Trip--Summer--2026", "*--*", "-"), "Trip-Summer-2026")

    def test_replace_pattern_supports_wildcard_replacement_at_start(self):
        self.assertEqual(replace_pattern("--Trip--Summer", "--*", "-"), "-Trip--Summer")

    def test_replace_pattern_supports_wildcard_replacement_at_end(self):
        self.assertEqual(replace_pattern("Trip--Summer--", "*--", "-"), "Trip--Summer-")

    def test_replace_pattern_keeps_regex_replacement_support(self):
        self.assertEqual(
            replace_pattern("2026.07.06 - Summer", r"\b(\d{4})\.(\d{2})\.(\d{2})\b", r"\1-\2-\3"),
            "2026-07-06 - Summer",
        )


if __name__ == "__main__":
    unittest.main()
