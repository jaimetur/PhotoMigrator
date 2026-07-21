import importlib
import io
import os
import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path
from types import SimpleNamespace
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

    def test_features_redirects_to_output_for_current_users_active_job(self):
        self.web_app.JOBS["active-job"] = SimpleNamespace(status="running", owner_user_id=self.current_user["id"])
        request = self.web_app.Request({
            "type": "http",
            "method": "GET",
            "path": "/features",
            "query_string": b"",
            "headers": [],
        })

        with patch.object(self.web_app, "_user_from_session_token", return_value=self.current_user):
            response = self.web_app.features_page(request, session_token="session-token")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/output")

    def test_features_allows_manual_navigation_for_current_users_active_job(self):
        self.web_app.JOBS["active-job"] = SimpleNamespace(status="running", owner_user_id=self.current_user["id"])
        request = self.web_app.Request({
            "type": "http",
            "method": "GET",
            "path": "/features",
            "query_string": b"manual_navigation=1",
            "headers": [],
        })

        with patch.object(self.web_app, "_user_from_session_token", return_value=self.current_user), patch.object(
            self.web_app.templates,
            "TemplateResponse",
            return_value=self.web_app.HTMLResponse("features"),
        ):
            response = self.web_app.features_page(request, session_token="session-token")

        self.assertEqual(response.status_code, 200)

    def test_icloud_takeout_rejects_direct_user_root(self):
        values = {"icloud-takeout": str(self.allowed_roots[0])}
        scope = self.web_app._path_validation_scope_for_payload("icloud_takeout", None, values)

        with self.assertRaises(self.HTTPException) as context:
            self.web_app._sanitize_payload_paths_for_user(values, self.current_user, path_scope=scope)

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("subfolder", str(context.exception.detail))
        self.assertIn(str(self.allowed_roots[0]), str(context.exception.detail))

    def test_takeout_tabs_do_not_expose_unused_album_name_flags(self):
        general_dests = {
            field["dest"]
            for field in self.web_app.PARSER_SCHEMA["general_tabs"]["general"]
        }
        self.assertNotIn("prefer-canonical-album-names", general_dests)
        self.assertNotIn("consolidate-similar-albums", general_dests)

        for tab in ("google_takeout", "icloud_takeout"):
            with self.subTest(tab=tab):
                tab_dests = {
                    field["dest"]
                    for field in self.web_app.PARSER_SCHEMA["tabs"][tab]
                }
                self.assertNotIn("prefer-canonical-album-names", tab_dests)
                self.assertNotIn("consolidate-similar-albums", tab_dests)

    def test_google_takeout_binary_controls_are_boolean_fields(self):
        fields_by_dest = self.web_app.PARSER_SCHEMA["fields_by_dest"]

        for dest in ("show-gpth-info", "show-gpth-errors", "google-process-people"):
            with self.subTest(dest=dest):
                self.assertEqual(fields_by_dest[dest]["kind"], "bool")

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

    def test_import_config_preserves_paths_outside_user_roots(self):
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
            response = self.web_app.import_config(payload, self.current_user)
        finally:
            self.web_app.CONFIG_FORM_SCHEMA = original_schema

        self.assertTrue(response["saved"])
        imported = self.web_app._get_user_config_values(self.current_user)["Google Takeout"]["INPUT_FOLDER"]
        self.assertEqual(imported, "/etc/passwd")

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

    def test_read_job_output_lines_for_api_omits_non_progress_partial(self):
        job = type("JobStub", (), {})()
        job.output = deque([
            self.web_app.OutputLine(text="INFO: line 1\n"),
            self.web_app.OutputLine(text="INFO: line 2\n"),
        ])
        job.partial_line = "INFO: partial"
        job.dropped_output_lines = 0

        lines = self.web_app._read_job_output_lines_for_api(job)

        self.assertEqual(lines, ["INFO: line 1", "INFO: line 2"])

    def test_read_job_output_lines_for_api_prepends_drop_notice_when_needed(self):
        job = type("JobStub", (), {})()
        job.output = deque([self.web_app.OutputLine(text="INFO: kept\n")])
        job.partial_line = ""
        job.dropped_output_lines = 3

        lines = self.web_app._read_job_output_lines_for_api(job)

        self.assertIn("3 lines were dropped", lines[0])
        self.assertEqual(lines[1:], ["INFO: kept"])

    def test_read_job_output_lines_for_api_returns_full_compact_buffer(self):
        job = type("JobStub", (), {})()
        job.output = deque(
            [self.web_app.OutputLine(text=f"INFO: line {idx}\n") for idx in range(150)]
        )
        job.partial_line = ""
        job.dropped_output_lines = 0

        lines = self.web_app._read_job_output_lines_for_api(job)

        self.assertEqual(len(lines), 150)
        self.assertEqual(lines[0], "INFO: line 0")
        self.assertEqual(lines[-1], "INFO: line 149")

    def test_read_job_output_history_page_helper_is_not_exposed(self):
        self.assertFalse(hasattr(self.web_app, "_read_job_output_history_page"))

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

    def test_synology_download_all_includes_enabled_otp_flag(self):
        synology_dests = {
            str(field.get("dest") or "")
            for field in self.web_app.PARSER_SCHEMA["tabs"]["synology_photos"]
        }
        self.assertIn("one-time-password", synology_dests)

        args = self.web_app._build_cli_args(
            "synology_photos",
            {
                "account-id": 2,
                "download-all": "/tmp/Synology",
                "one-time-password": True,
            },
            "download-all",
        )

        self.assertIn("--one-time-password", args)

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

    def test_immich_duplicate_asset_keeper_default_is_sent_to_the_cli(self):
        args = self.web_app._build_cli_args(
            "immich_photos",
            {
                "account-id": 1,
                "remove-duplicates-assets": True,
                "dup-asset-keeper": "newest",
            },
            "remove-duplicates-assets",
        )

        self.assertIn("--remove-duplicates-assets", args)
        self.assertIn("--dup-asset-keeper", args)
        self.assertIn("newest", args)

    def test_immich_manual_duplicate_flow_forces_native_deletion_false(self):
        args = self.web_app._build_cli_args(
            "immich_photos",
            {
                "account-id": 2,
                "remove-duplicates-assets": True,
                "dup-immich-native-algorithm": False,
                "dup-immich-native-deletion": False,
                "dup-asset-keeper": "newest",
            },
            "remove-duplicates-assets",
        )

        deletion_index = args.index("--dup-immich-native-deletion")
        self.assertEqual(args[deletion_index + 1], "false")

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

    def test_web_job_output_records_incremental_append_ops(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="icloud_takeout", owner_user_id=1)
        try:
            self.web_app._append_job_output(job, "INFO    : Asset Pulled    : 'IMG_0001.jpg'\n")
            ops = self.web_app._read_job_output_ops_after(job, 0)
            snapshot = self.web_app._build_job_output_snapshot_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["op"], "append")
        self.assertEqual(ops[0]["text"], "INFO    : Asset Pulled    : 'IMG_0001.jpg'")
        self.assertEqual(snapshot["entries"][0]["line_id"], ops[0]["line_id"])
        self.assertEqual(snapshot["cursor"], ops[0]["seq"])

    def test_web_job_output_updates_last_updated_timestamp(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="icloud_takeout", owner_user_id=1)
        try:
            job.last_updated_at = "2000-01-01T00:00:00+00:00"
            self.web_app._append_job_output(job, "INFO    : Processing asset\n")
        finally:
            self.web_app._close_job_output_file(job)

        self.assertNotEqual(job.last_updated_at, "2000-01-01T00:00:00+00:00")

    def test_web_job_exposes_otp_prompt_before_a_newline_is_written(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = Mock()
        fake_process.stdin.closed = False
        fake_process.returncode = None
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="synology_photos", owner_user_id=1)
        try:
            self.web_app._append_job_output(job, "INFO    : Enter SYNOLOGY OTP Token: ")
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertTrue(job.awaiting_confirmation)
        self.assertEqual(lines, ["INFO    : Enter SYNOLOGY OTP Token: "])

    def test_web_job_output_records_incremental_replace_ops_for_progress_updates(self):
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
            first_ops = self.web_app._read_job_output_ops_after(job, 0)
            self.web_app._append_job_output(
                job,
                "INFO    : [iCloud PROCESS]-[Stage Media] : Staging iCloud assets: 1289 files [00:34, 38.65 files/s]\n",
            )
            delta_ops = self.web_app._read_job_output_ops_after(job, first_ops[-1]["seq"])
            snapshot = self.web_app._build_job_output_snapshot_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(len(first_ops), 1)
        self.assertEqual(first_ops[0]["op"], "append")
        self.assertEqual(len(delta_ops), 1)
        self.assertEqual(delta_ops[0]["op"], "replace")
        self.assertEqual(delta_ops[0]["line_id"], first_ops[0]["line_id"])
        self.assertEqual(snapshot["entries"][0]["text"], "INFO    : [iCloud PROCESS]-[Stage Media] : Staging iCloud assets: 1289 files [00:34, 38.65 files/s]")

    def test_dashboard_snapshot_events_update_job_snapshot_without_polluting_visible_output(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        snapshot_payload = {
            "pulledAssets": 321,
            "pushedAssets": 123,
            "assetsInQueue": 17,
            "updatedAt": "2026-07-14T18:00:00Z",
        }
        try:
            self.web_app._append_job_output(
                job,
                f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{self.web_app.json.dumps(snapshot_payload)}\n",
            )
            self.web_app._append_job_output(job, "INFO    : Asset Pulled    : 'IMG_0001.jpg'\n")
            output = self.web_app._read_job_output_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertTrue(job.dashboard_snapshot_from_events)
        self.assertEqual(job.dashboard_snapshot["pulledAssets"], 321)
        self.assertEqual(job.dashboard_snapshot["pushedAssets"], 123)
        self.assertEqual(job.dashboard_snapshot["assetsInQueue"], 17)
        self.assertEqual(job.dashboard_snapshot_updated_at, "2026-07-14T18:00:00Z")
        self.assertIn("Asset Pulled", output)
        self.assertNotIn(self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX, output)
        persisted = Path(job.output_file).read_text(encoding="utf-8")
        self.assertIn("Asset Pulled", persisted)
        self.assertNotIn(self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX, persisted)

    def test_dashboard_snapshot_partial_line_is_hidden_from_visible_output(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            job.partial_line = f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{{\"pulledAssets\":321"
            lines = [self.web_app._strip_ansi(line) for line in self.web_app._read_job_output_lines_for_api(job)]
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(lines, [])

    def test_dashboard_snapshot_embedded_after_progress_line_does_not_leak_or_duplicate(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        snapshot_payload = {
            "pulledAssets": 99,
            "updatedAt": "2026-07-15T08:00:00Z",
        }
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : [Pull] : ##### 5/10 50.0%\r"
                f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{self.web_app.json.dumps(snapshot_payload)}\n"
            )
            self.web_app._append_job_output(
                job,
                "INFO    : [Pull] : ########## 10/10 100.0%\n"
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
            persisted = Path(job.output_file).read_text(encoding="utf-8")
        finally:
            self.web_app._close_job_output_file(job)

        self.assertTrue(job.dashboard_snapshot_from_events)
        self.assertEqual(job.dashboard_snapshot["pulledAssets"], 99)
        self.assertEqual(lines, ["INFO    : [Pull] : ########## 10/10 100.0%"])
        self.assertNotIn(self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX, persisted)
        self.assertNotIn("INFO    :\n", persisted)

    def test_dashboard_snapshot_inline_partial_keeps_visible_prefix_only(self):
        job = type("JobStub", (), {})()
        job.output = deque([])
        job.partial_line = (
            "INFO    : [Pull] : ##### 5/10 50.0%\r"
            f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{{\"pulledAssets\":321"
        )
        job.pending_structured_prefix = ""
        job.pending_level_prefix = ""
        job.dropped_output_lines = 0

        lines = self.web_app._read_job_output_lines_for_api(job)

        self.assertEqual(lines, ["INFO    : [Pull] : ##### 5/10 50.0%\r"])

    def test_dashboard_snapshot_with_trailing_info_prefix_is_fully_removed_from_visible_log(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        snapshot_payload = {
            "pulledAssets": 0,
            "updatedAt": "2026-07-15T16:11:32.838768Z",
        }
        try:
            self.web_app._append_job_output(
                job,
                f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{self.web_app.json.dumps(snapshot_payload)}INFO    : \n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
            persisted = Path(job.output_file).read_text(encoding="utf-8")
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(lines, [])
        self.assertEqual(persisted, "")
        self.assertEqual(job.dashboard_snapshot["pulledAssets"], 0)

    def test_dashboard_snapshot_embedded_before_info_line_keeps_only_visible_message(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        snapshot_payload = {
            "pulledAssets": 1,
            "updatedAt": "2026-07-15T16:11:32.838768Z",
        }
        try:
            self.web_app._append_job_output(
                job,
                f"{self.web_app.WEB_DASHBOARD_SNAPSHOT_PREFIX}{self.web_app.json.dumps(snapshot_payload)}INFO    : Asset Pulled    : 'IMG_0001.jpg'\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(lines, ["INFO    : Asset Pulled    : 'IMG_0001.jpg'"])
        self.assertEqual(job.dashboard_snapshot["pulledAssets"], 1)

    def test_orphan_info_prefix_is_reattached_to_following_progress_line(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(job, "INFO    : \nDownloading Albums:  37%|███▋      | 94/254 [00:26<00:33,  4.84 albums/s]\n")
            lines = self.web_app._read_job_output_lines_for_api(job)
            persisted = Path(job.output_file).read_text(encoding="utf-8")
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            ["INFO    : Downloading Albums:  37%|███▋      | 94/254 [00:26<00:33,  4.84 albums/s]"],
        )
        self.assertIn("INFO    : Downloading Albums:", persisted)

    def test_orphan_info_prefix_is_dropped_when_no_progress_line_follows(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(job, "INFO    : \nWARNING : Real warning message\n")
            lines = self.web_app._read_job_output_lines_for_api(job)
            persisted = Path(job.output_file).read_text(encoding="utf-8")
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(lines, ["WARNING : Real warning message"])
        self.assertEqual(persisted, "WARNING : Real warning message\n")

    def test_ansi_colored_orphan_info_prefix_is_dropped(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(job, "\x1b[97mINFO    : \x1b[0m\nINFO    : Downloading Albums: 100%|##########| 1/1\n")
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(lines, ["INFO    : Downloading Albums: 100%|##########| 1/1"])

    def test_ansi_colored_nested_progress_replaces_each_progress_line(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="synology_photos", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : Downloading Albums:   0%|          | 0/2 [00:00<?, ? albums/s]\n"
                "INFO    :    Downloading 'Jaime' Assets:   0%|          | 0/1 [00:00<?, ? assets/s]\n"
                "\x1b[97mINFO    : \x1b[0m\n"
                "\x1b[97mINFO    :    Downloading 'Jaime' Assets: 100%|##########| 1/1 [00:00<00:00, 9.86 assets/s]\x1b[0m\n"
                "\x1b[97mINFO    : \x1b[0m\n"
                "\x1b[97mINFO    : Downloading Albums: 100%|##########| 2/2 [00:01<00:00, 1.73 albums/s]\x1b[0m\n",
            )
            lines = [self.web_app._strip_ansi(line) for line in self.web_app._read_job_output_lines_for_api(job)]
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : Downloading Albums: 100%|##########| 2/2 [00:01<00:00, 1.73 albums/s]",
                "INFO    :    Downloading 'Jaime' Assets: 100%|##########| 1/1 [00:00<00:00, 9.86 assets/s]",
            ],
        )

    def test_progress_line_is_split_before_following_info_prefix(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "Downloading Albums: 100%|██████████| 254/254 [00:33<00:00,  8.77 albums/s]INFO    : Grouping Albums by Name: 100%|██████████| 254/254 [00:31<00:00,  8.38 albums/s]\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "Downloading Albums: 100%|██████████| 254/254 [00:33<00:00,  8.77 albums/s]",
                "INFO    : Grouping Albums by Name: 100%|██████████| 254/254 [00:31<00:00,  8.38 albums/s]",
            ],
        )

    def test_partial_progress_replaces_previous_completed_progress_line(self):
        job = type("JobStub", (), {})()
        job.output = deque([
            self.web_app.OutputLine(text="INFO    : Downloading Albums:  37%|███▋      | 94/254 [00:26<00:33,  4.84 albums/s]\n")
        ])
        job.partial_line = "INFO    : Downloading Albums:  38%|███▊      | 95/254 [00:27<00:33,  4.84 albums/s]"
        job.pending_structured_prefix = ""
        job.pending_level_prefix = ""
        job.dropped_output_lines = 0

        lines = self.web_app._read_job_output_lines_for_api(job)

        self.assertEqual(
            lines,
            ["INFO    : Downloading Albums:  38%|███▊      | 95/254 [00:27<00:33,  4.84 albums/s]"],
        )

    def test_gpth_progress_line_is_split_before_following_inner_info_step_line(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : ██████████████████████████████████████████████████ 170/170 100.0% [ INFO  ] [Step 5/8] Media with album associations: 119\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : ██████████████████████████████████████████████████ 170/170 100.0%",
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Media with album associations: 119",
            ],
        )

    def test_step_information_line_is_not_treated_as_progress_key(self):
        line = "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Media with album associations: 119"
        self.assertIsNone(self.web_app._extract_progress_key(line))

    def test_gpth_inner_step_line_inherits_structured_prefix_across_chunks(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : ██████████████████████████████████████████████████ 170/170 100.0%\n",
            )
            self.web_app._append_job_output(
                job,
                "[ INFO  ] [Step 5/8] Media with album associations: 119\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : ██████████████████████████████████████████████████ 170/170 100.0%",
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Media with album associations: 119",
            ],
        )

    def test_gpth_progress_updates_without_outer_level_replace_previous_progress_line(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : .................................................. 1/170 0.6%\n",
            )
            self.web_app._append_job_output(
                job,
                "🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : █................................................. 4/170 2.4%\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : █................................................. 4/170 2.4%",
            ],
        )

    def test_gpth_progress_line_trailing_info_prefix_is_reattached_to_next_progress_update(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : .................................................. 1/170 0.6%INFO    : \n",
            )
            self.web_app._append_job_output(
                job,
                "🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : .................................................. 2/170 1.2%\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 5/8] Processing album associations : .................................................. 2/170 1.2%",
            ],
        )

    def test_gpth_structured_followup_line_recovers_outer_info_prefix(self):
        fake_process = Mock()
        fake_process.stdout = io.StringIO("")
        fake_process.stdin = None
        fake_process.returncode = 0
        job = self.web_app.JobData(command=["python"], process=fake_process, tab="automatic_migration", owner_user_id=1)
        try:
            self.web_app._append_job_output(
                job,
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Writing EXIF data : ██████████████████████████████████████████████████ 170/170 100.0%\n",
            )
            self.web_app._append_job_output(
                job,
                "🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Pending before final flush → Images: 0, Videos: 0\n",
            )
            lines = self.web_app._read_job_output_lines_for_api(job)
        finally:
            self.web_app._close_job_output_file(job)

        self.assertEqual(
            lines,
            [
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Writing EXIF data : ██████████████████████████████████████████████████ 170/170 100.0%",
                "INFO    : 🧠 [PROCESS]-[Metadata Processing] : [ INFO  ] [Step 7/8] Pending before final flush → Images: 0, Videos: 0",
            ],
        )


if __name__ == "__main__":
    unittest.main()
