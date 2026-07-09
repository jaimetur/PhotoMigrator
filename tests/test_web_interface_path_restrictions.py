import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


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
        self.web_app.CONFIG_TEMPLATE_CONTENT = self.web_app._load_default_config_template()
        self.web_app.CONFIG_FORM_SCHEMA = self.web_app._extend_form_schema_with_web_interface_theme(
            self.web_app._parse_template_to_form_schema(self.web_app.CONFIG_TEMPLATE_CONTENT)
        )
        self.web_app._init_web_db(self.web_app.CONFIG_FORM_SCHEMA)
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

    def test_icloud_takeout_rejects_direct_user_root(self):
        values = {"icloud-takeout": str(self.allowed_roots[0])}
        scope = self.web_app._path_validation_scope_for_payload("icloud_takeout", None, values)

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

    def test_web_normalize_incoming_values_forces_authenticated_user_config_path(self):
        own_config_path = self.web_app._materialize_user_config_to_file(self.current_user, self.web_app.CONFIG_FORM_SCHEMA)
        normalized = self.web_app._normalize_incoming_values(
            {"configuration-file": "/app/config/generated/Config_admin_999.ini"},
            config_path=own_config_path,
        )

        self.assertEqual(normalized["configuration-file"], str(own_config_path))

    def test_build_command_ignores_user_supplied_configuration_file(self):
        own_config_path = self.web_app._materialize_user_config_to_file(self.current_user, self.web_app.CONFIG_FORM_SCHEMA)
        takeout_subfolder = self.allowed_roots[0] / "TakeoutInput"
        takeout_subfolder.mkdir(parents=True, exist_ok=True)
        payload = self.web_app.RunRequest(
            tab="google_takeout",
            values={
                "google-takeout": str(takeout_subfolder),
                "configuration-file": "/app/config/generated/Config_admin_999.ini",
            },
        )

        command = self.web_app._build_command_from_payload(payload, own_config_path)

        self.assertIn("--configuration-file", command)
        self.assertIn(str(own_config_path), command)
        self.assertNotIn("/app/config/generated/Config_admin_999.ini", command)

    def test_display_command_hides_materialized_config_path(self):
        own_config_path = self.web_app._materialize_user_config_to_file(self.current_user, self.web_app.CONFIG_FORM_SCHEMA)
        command = [
            "python",
            "PhotoMigrator.py",
            "--google-takeout",
            str(self.allowed_roots[0] / "TakeoutInput"),
            "--configuration-file",
            str(own_config_path),
        ]

        rendered = self.web_app._display_command_for_user(command, own_config_path, self.current_user)

        self.assertIn(self.web_app._user_config_db_path(self.current_user), rendered)
        self.assertNotIn(str(own_config_path), rendered)

    def test_import_config_rejects_paths_outside_user_roots(self):
        original_schema = self.web_app.CONFIG_FORM_SCHEMA
        self.web_app.CONFIG_FORM_SCHEMA = [
            {
                "name": "Google Takeout",
                "fields": [
                    {"key": "INPUT_FOLDER", "default": "", "help": "", "sensitive": False},
                ],
            }
        ]
        payload = self.web_app.ConfigUpdateRequest(
            content="[Google Takeout]\nINPUT_FOLDER = /etc/passwd\n",
        )

        try:
            with self.assertRaises(self.HTTPException) as context:
                self.web_app.import_config(payload, self.current_user)
        finally:
            self.web_app.CONFIG_FORM_SCHEMA = original_schema

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("allowed user roots", str(context.exception.detail))

    def test_exclusion_pattern_fields_are_not_treated_as_paths(self):
        self.assertEqual(self.web_app._path_hint("exclude-folders", "<FOLDER_PATTERN>"), "")
        self.assertEqual(self.web_app._path_hint("exclude-files", "<FILE_PATTERN>"), "")

        values = {
            "exclude-folders": "@eaDir,.@__thumb",
            "exclude-files": "SYNOFILE_THUMB*,Thumbs.db",
        }
        scope = self.web_app._path_validation_scope_for_payload("automatic_migration", None, values)
        self.assertNotIn("exclude-folders", scope)
        self.assertNotIn("exclude-files", scope)

    def test_google_output_folder_suffix_is_not_treated_as_path(self):
        takeout_subfolder = self.allowed_roots[0] / "TakeoutInput"
        takeout_subfolder.mkdir(parents=True, exist_ok=True)
        values = {
            "google-takeout": str(takeout_subfolder),
            "google-output-folder-suffix": "processed",
        }

        self.assertEqual(self.web_app._path_hint("google-output-folder-suffix", "<SUFFIX>"), "")

        scope = self.web_app._path_validation_scope_for_payload("google_takeout", None, values)
        self.assertIn("google-takeout", scope)
        self.assertNotIn("google-output-folder-suffix", scope)

    def test_boolean_flags_with_path_like_names_are_not_treated_as_paths(self):
        takeout_subfolder = self.allowed_roots[0] / "TakeoutInput"
        takeout_subfolder.mkdir(parents=True, exist_ok=True)
        values = {
            "google-takeout": str(takeout_subfolder),
            "google-remove-duplicates-files": True,
            "google-rename-albums-folders": True,
            "google-skip-extras-files": True,
            "google-keep-takeout-folder": True,
            "no-log-file": True,
        }

        scope = self.web_app._path_validation_scope_for_payload("google_takeout", None, values)

        self.assertIn("google-takeout", scope)
        self.assertNotIn("google-remove-duplicates-files", scope)
        self.assertNotIn("google-rename-albums-folders", scope)
        self.assertNotIn("google-skip-extras-files", scope)
        self.assertNotIn("google-keep-takeout-folder", scope)
        self.assertNotIn("no-log-file", scope)

        sanitized = self.web_app._sanitize_payload_paths_for_user(values, self.current_user, path_scope=scope)

        self.assertIs(sanitized["google-remove-duplicates-files"], True)
        self.assertIs(sanitized["google-rename-albums-folders"], True)
        self.assertIs(sanitized["google-skip-extras-files"], True)
        self.assertIs(sanitized["google-keep-takeout-folder"], True)
        self.assertIs(sanitized["no-log-file"], True)

    def test_web_parser_schema_exposes_auxiliary_organize_fields_by_dest(self):
        fields_by_dest = self.web_app.PARSER_SCHEMA.get("fields_by_dest", {})

        self.assertIn("organize-output-folder-suffix", fields_by_dest)
        self.assertIn("organize-folder-structure", fields_by_dest)
        self.assertIn("move-original-files", fields_by_dest)

    def test_config_form_response_exposes_account_selector_for_multi_account_sections(self):
        response = self.web_app._build_config_form_response(self.current_user)
        sections = {str(section.get("name") or ""): section for section in response.get("sections", [])}

        immich = sections["Immich Photos"]
        self.assertTrue(immich["account_selector"]["enabled"])
        self.assertEqual(immich["account_selector"]["accounts"], ["1", "2", "3"])
        self.assertEqual(immich["account_selector"]["default_account"], "1")

        field_map = {str(field.get("key") or ""): field for field in immich.get("fields", [])}
        self.assertEqual(field_map["IMMICH_URL"]["account_id"], "")
        self.assertEqual(field_map["IMMICH_API_KEY_ADMIN"]["account_id"], "")
        self.assertEqual(field_map["IMMICH_USERNAME_2"]["account_id"], "2")
        self.assertEqual(field_map["IMMICH_PASSWORD_3"]["account_id"], "3")

    def test_config_form_response_does_not_enable_account_selector_for_single_account_sections(self):
        response = self.web_app._build_config_form_response(self.current_user)
        sections = {str(section.get("name") or ""): section for section in response.get("sections", [])}

        web_interface = sections["Web Interface"]
        self.assertFalse(web_interface["account_selector"]["enabled"])
        self.assertEqual(web_interface["account_selector"]["accounts"], [])
        self.assertEqual(web_interface["account_selector"]["default_account"], "")

    def test_web_schema_hides_configuration_file_argument(self):
        general_dests = {str(field.get("dest") or "") for field in self.web_app.PARSER_SCHEMA["general_tabs"]["general"]}
        self.assertNotIn("configuration-file", general_dests)

    def test_icloud_include_memories_defaults_to_true_in_ui_and_appends_existing_flag(self):
        field = self.web_app.PARSER_FIELDS_BY_DEST["icloud-include-memories"]

        self.assertTrue(bool(field["default"]))
        self.assertEqual(field["long_option"], "--icloud-include-memories")

        enabled_args = self.web_app._build_cli_args("icloud_takeout", {"icloud-include-memories": True}, None)
        disabled_args = self.web_app._build_cli_args("icloud_takeout", {"icloud-include-memories": False}, None)

        self.assertIn("--icloud-include-memories", enabled_args)
        self.assertNotIn("--icloud-include-memories", disabled_args)

    def test_icloud_native_writer_defaults_to_true_in_web_ui_but_remains_optional_in_cli_args(self):
        field = self.web_app.PARSER_FIELDS_BY_DEST["icloud-prefer-native-exif-writer"]

        self.assertTrue(bool(field["default"]))
        self.assertEqual(field["long_option"], "--icloud-prefer-native-exif-writer")

        enabled_args = self.web_app._build_cli_args("icloud_takeout", {"icloud-prefer-native-exif-writer": True}, None)
        disabled_args = self.web_app._build_cli_args("icloud_takeout", {"icloud-prefer-native-exif-writer": False}, None)

        self.assertIn("--icloud-prefer-native-exif-writer", enabled_args)
        self.assertNotIn("--icloud-prefer-native-exif-writer", disabled_args)

    def test_google_keep_takeout_folder_flag_is_optional_and_only_emitted_when_enabled(self):
        field = self.web_app.PARSER_FIELDS_BY_DEST["google-keep-takeout-folder"]

        self.assertFalse(bool(field["default"]))
        self.assertEqual(field["long_option"], "--google-keep-takeout-folder")

        enabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "google-keep-takeout-folder": True},
            None,
        )
        disabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "google-keep-takeout-folder": False},
            None,
        )

        self.assertIn("--google-keep-takeout-folder", enabled_args)
        self.assertNotIn("--google-keep-takeout-folder", disabled_args)

    def test_google_takeout_processing_flags_are_only_emitted_when_enabled(self):
        enabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {
                "google-takeout": "/tmp/Takeout",
                "google-remove-duplicates-files": True,
                "google-rename-albums-folders": True,
                "google-skip-extras-files": True,
            },
            None,
        )
        disabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {
                "google-takeout": "/tmp/Takeout",
                "google-remove-duplicates-files": False,
                "google-rename-albums-folders": False,
                "google-skip-extras-files": False,
            },
            None,
        )

        self.assertIn("--google-remove-duplicates-files", enabled_args)
        self.assertIn("--google-rename-albums-folders", enabled_args)
        self.assertIn("--google-skip-extras-files", enabled_args)
        self.assertNotIn("--google-remove-duplicates-files", disabled_args)
        self.assertNotIn("--google-rename-albums-folders", disabled_args)
        self.assertNotIn("--google-skip-extras-files", disabled_args)

    def test_no_log_file_flag_is_only_emitted_when_enabled(self):
        enabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "no-log-file": True},
            None,
        )
        disabled_args = self.web_app._build_cli_args(
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "no-log-file": False},
            None,
        )

        self.assertIn("--no-log-file", enabled_args)
        self.assertNotIn("--no-log-file", disabled_args)

    def test_state_value_normalization_converts_string_booleans_for_checkbox_fields(self):
        normalized = self.web_app._normalize_state_values_for_schema(
            {
                "google-keep-takeout-folder": "true",
                "google-remove-duplicates-files": "false",
                "google-rename-albums-folders": "1",
                "google-skip-extras-files": "0",
                "no-log-file": "yes",
                "google-takeout": "/tmp/Takeout",
            }
        )

        self.assertIs(normalized["google-keep-takeout-folder"], True)
        self.assertIs(normalized["google-remove-duplicates-files"], False)
        self.assertIs(normalized["google-rename-albums-folders"], True)
        self.assertIs(normalized["google-skip-extras-files"], False)
        self.assertIs(normalized["no-log-file"], True)
        self.assertEqual(normalized["google-takeout"], "/tmp/Takeout")

    def test_web_build_id_is_generated(self):
        self.assertTrue(str(self.web_app.WEB_BUILD_ID).strip())

    def test_web_job_output_compacts_indeterminate_tqdm_lines(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="icloud_takeout", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : [iCloud PROCESS]-[Stage Media] : Staging iCloud assets: 1262 files [00:33, 29.74 files/s]\n",
            )
            self.web_app._append_job_output(
                job,
                "INFO    : [iCloud PROCESS]-[Stage Media] : Staging iCloud assets: 1289 files [00:34, 38.65 files/s]\n",
            )
            output = self.web_app._read_job_output_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertIn("1289 files", output)
        self.assertNotIn("1262 files", output)


if __name__ == "__main__":
    unittest.main()
