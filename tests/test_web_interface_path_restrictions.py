import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class TestWebInterfacePathRestrictions(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi import HTTPException
        except ModuleNotFoundError as exc:
            self.skipTest(f"fastapi is not installed in this environment: {exc}")

        self.HTTPException = HTTPException
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.template_path = PROJECT_ROOT / "tests" / "test_data" / "config_test.ini"
        self.env_keys = [
            "PHOTOMIGRATOR_WEB_DB_PATH",
            "PHOTOMIGRATOR_WEB_USER_ROOT_DATA",
            "PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1",
            "PHOTOMIGRATOR_CONFIG_PATH",
            "PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH",
            "PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR",
            "PHOTOMIGRATOR_STATE_PATH",
        ]
        self.env_backup = {key: os.environ.get(key) for key in self.env_keys}

        os.environ["PHOTOMIGRATOR_WEB_DB_PATH"] = str(self.base_path / "web_interface.db")
        os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_DATA"] = str(self.base_path / "data")
        os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1"] = str(self.base_path / "volumes")
        os.environ["PHOTOMIGRATOR_CONFIG_PATH"] = str(self.base_path / "Config.ini")
        os.environ["PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH"] = str(self.template_path)
        os.environ["PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR"] = str(self.base_path / "generated")
        os.environ["PHOTOMIGRATOR_STATE_PATH"] = str(self.base_path / "state.json")

        sys.modules.pop("web_interface.app", None)
        try:
            import web_interface.app as web_app
        except ModuleNotFoundError as exc:
            self.skipTest(f"web interface dependencies are not installed in this environment: {exc}")

        self.web_app = importlib.reload(web_app)
        self.web_app.PARSER_SCHEMA = self.web_app._load_parser_schema()
        self.current_user = {
            "id": 1,
            "username": "demo",
            "role": "user",
            "data_subpath": "demo",
            "volume1_subpath": "demo",
        }
        self.allowed_roots = self.web_app._ensure_user_roots_exist(self.current_user)

    def tearDown(self):
        sys.modules.pop("web_interface.app", None)
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_google_takeout_rejects_direct_user_root(self):
        values = {"google-takeout": str(self.allowed_roots[0])}
        scope = self.web_app._path_validation_scope_for_payload("google_takeout", None, values)

        with self.assertRaises(self.HTTPException) as context:
            self.web_app._sanitize_payload_paths_for_user(values, self.current_user, path_scope=scope)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("subfolder", str(context.exception.detail))
        self.assertIn(str(self.allowed_roots[0]), str(context.exception.detail))

    def test_optional_output_folder_also_rejects_direct_user_root(self):
        takeout_subfolder = self.allowed_roots[0] / "TakeoutInput"
        takeout_subfolder.mkdir(parents=True, exist_ok=True)
        values = {
            "google-takeout": str(takeout_subfolder),
            "output-folder": str(self.allowed_roots[0]),
        }
        scope = self.web_app._path_validation_scope_for_payload("google_takeout", None, values)

        with self.assertRaises(self.HTTPException) as context:
            self.web_app._sanitize_payload_paths_for_user(values, self.current_user, path_scope=scope)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("--output-folder", str(context.exception.detail))

    def test_subfolders_inside_data_and_volume_roots_are_allowed(self):
        data_subfolder = self.allowed_roots[0] / "input" / "takeout"
        volume_subfolder = self.allowed_roots[1] / "exports" / "output"
        data_subfolder.mkdir(parents=True, exist_ok=True)
        volume_subfolder.mkdir(parents=True, exist_ok=True)
        values = {
            "google-takeout": str(data_subfolder),
            "output-folder": str(volume_subfolder),
        }
        scope = self.web_app._path_validation_scope_for_payload("google_takeout", None, values)

        sanitized = self.web_app._sanitize_payload_paths_for_user(values, self.current_user, path_scope=scope)

        self.assertEqual(sanitized["google-takeout"], str(data_subfolder))
        self.assertEqual(sanitized["output-folder"], str(volume_subfolder))

    def test_config_paths_reject_direct_user_root(self):
        form_schema = [
            {
                "name": "Google Takeout",
                "fields": [
                    {"key": "INPUT_FOLDER"},
                    {"key": "OUTPUT_FOLDER"},
                ],
            }
        ]
        values = {"Google Takeout": {"INPUT_FOLDER": str(self.allowed_roots[0])}}

        with self.assertRaises(self.HTTPException) as context:
            self.web_app._sanitize_config_values_for_user(values, form_schema, self.current_user)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Config path", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
