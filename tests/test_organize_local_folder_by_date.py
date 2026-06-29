import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import Features.StandAloneFeatures.OrganizeLocalFolderByDate as organize_module
except ModuleNotFoundError as exc:
    organize_module = exc


class TestOrganizeLocalFolderByDate(unittest.TestCase):
    def setUp(self):
        if isinstance(organize_module, ModuleNotFoundError):
            self.skipTest(f"Standalone feature dependencies are not installed in this environment: {organize_module}")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.input_folder = self.base_path / "library"
        self.input_folder.mkdir(parents=True, exist_ok=True)
        (self.input_folder / "IMG_0001.JPG").write_bytes(b"jpeg")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explicit_output_folder_is_used_without_suffix_generation(self):
        output_folder = self.base_path / "custom-output"

        with (
            patch.object(organize_module, "ARGS", {"exclude-folders": []}),
            patch.object(organize_module, "LOGGER", Mock()),
            patch.object(organize_module, "organize_files_by_date", return_value=[]),
        ):
            result = organize_module.organize_local_folder_by_date(
                input_folder=str(self.input_folder),
                output_folder=str(output_folder),
                folder_structure="year/month",
                output_folder_suffix="ignored",
                move_original_files=False,
            )

        self.assertTrue(self.input_folder.exists())
        self.assertTrue(output_folder.exists())
        self.assertEqual(result["output_folder"], str(output_folder.resolve()))

    def test_implicit_output_folder_uses_suffix_and_timestamp_for_move_mode(self):
        with (
            patch.object(organize_module, "ARGS", {"exclude-folders": []}),
            patch.object(organize_module, "LOGGER", Mock()),
            patch.object(organize_module, "TIMESTAMP", "20260630_101010"),
            patch.object(organize_module, "organize_files_by_date", return_value=[]),
        ):
            result = organize_module.organize_local_folder_by_date(
                input_folder=str(self.input_folder),
                output_folder="",
                folder_structure="flatten",
                output_folder_suffix="sorted",
                move_original_files=True,
            )

        expected_output = Path(f"{self.input_folder}_sorted_20260630_101010").resolve()
        self.assertFalse(self.input_folder.exists())
        self.assertTrue(expected_output.exists())
        self.assertEqual(result["output_folder"], str(expected_output))
        self.assertEqual(result["folder_structure"], "flatten")
        self.assertTrue(result["move_original_files"])


if __name__ == "__main__":
    unittest.main()
