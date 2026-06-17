import unittest
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from UI.shared import (
        build_cli_args,
        build_full_command,
        build_ui_subprocess_env,
        build_parser_schema,
        build_external_terminal_command,
        command_preview_string,
        command_to_string,
        compose_migration_endpoint,
        compose_find_duplicates_value,
        compose_rename_albums_value,
        config_section_account_selector,
        merge_values_with_schema,
        load_config_editor_model,
        parse_find_duplicates_value,
        parse_migration_endpoint,
        parse_rename_albums_value,
        parse_template_to_form_schema,
        resolve_ui_config_path,
        save_config_editor_values,
        ui_runtime_launcher_executable,
    )
    SHARED_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    SHARED_IMPORT_ERROR = exc


class TestCliTuiShared(unittest.TestCase):
    def setUp(self):
        if SHARED_IMPORT_ERROR is not None:
            self.skipTest(f"CLI TUI dependencies are not installed in this environment: {SHARED_IMPORT_ERROR}")

    def test_build_parser_schema_exposes_expected_tabs(self):
        schema = build_parser_schema()

        self.assertIn("google_takeout", schema["tabs"])
        self.assertIn("icloud_takeout", schema["tabs"])
        self.assertIn("automatic_migration", schema["tabs"])
        self.assertIn("google_photos", schema["tabs"])
        self.assertIn("configuration-file", schema["fields_by_dest"])

    def test_build_cli_args_composes_cloud_rename_albums_value(self):
        schema = build_parser_schema()
        values = {
            "account-id": "2",
            "rename-pattern": r"\\b(\\d{4})\\.(\\d{2})\\.(\\d{2})\\b",
            "replacement-pattern": r"\\1-\\2-\\3",
        }

        args = build_cli_args(schema, "synology_photos", values, "rename-albums")
        args_text = command_to_string(["python", *args])

        self.assertIn("--rename-albums", args)
        self.assertIn("--client", args)
        self.assertIn("synology", args)
        self.assertIn("--account-id", args)
        self.assertIn("2", args)
        self.assertIn(r"\\b(\\d{4})\\.(\\d{2})\\.(\\d{2})\\b, \\1-\\2-\\3", args_text)

    def test_build_cli_args_composes_find_duplicates_value(self):
        schema = build_parser_schema()
        values = {
            "find-duplicates-action": "delete",
            "find-duplicates-folders": ["/photos/Albums", "/photos/ALL_PHOTOS"],
        }

        args = build_cli_args(schema, "standalone_features", values, "find-duplicates")

        self.assertEqual(args[0], "--find-duplicates")
        self.assertEqual(args[1], "remove")
        self.assertEqual(args[2:], ["/photos/Albums", "/photos/ALL_PHOTOS"])

    def test_parse_helpers_roundtrip_special_fields(self):
        rename_value = compose_rename_albums_value("old", "new")
        self.assertEqual(parse_rename_albums_value(rename_value), {"pattern": "old", "replacement": "new"})

        duplicates_value = compose_find_duplicates_value("delete", ["/a", "/b"])
        self.assertEqual(parse_find_duplicates_value(duplicates_value), {"action": "delete", "folders": ["/a", "/b"]})

    def test_parse_helpers_roundtrip_migration_endpoints(self):
        self.assertEqual(
            parse_migration_endpoint("synology-photos-2", "synology"),
            {"kind": "synology", "account": "2", "path": ""},
        )
        self.assertEqual(
            parse_migration_endpoint("/mnt/photos", "synology"),
            {"kind": "folder", "account": "1", "path": "/mnt/photos"},
        )
        self.assertEqual(
            compose_migration_endpoint({"kind": "immich", "account": "3", "path": ""}),
            "immich-photos-3",
        )
        self.assertEqual(
            compose_migration_endpoint({"kind": "folder", "account": "1", "path": "/srv/library"}),
            "/srv/library",
        )

    def test_command_preview_string_omits_absolute_python_and_entrypoint_paths(self):
        preview = command_preview_string(
            ["/usr/bin/python3", "/opt/PhotoMigrator/src/PhotoMigrator.py", "--google-takeout", "/tmp/Takeout"]
        )

        self.assertEqual(preview, 'PhotoMigrator --google-takeout /tmp/Takeout')

    def test_command_preview_string_supports_frozen_binary_commands(self):
        preview = command_preview_string(
            ["/opt/PhotoMigrator/PhotoMigrator.exe", "--google-takeout", "D:\\Takeout"]
        )

        self.assertEqual(preview, 'PhotoMigrator --google-takeout D:\\Takeout')

    def test_config_schema_marks_multi_account_sections(self):
        template_text = Path("Config.ini").read_text(encoding="utf-8")
        schema = parse_template_to_form_schema(template_text)
        immich = next(section for section in schema if section["name"] == "Immich Photos")
        selector = config_section_account_selector(immich["fields"])

        self.assertTrue(selector["enabled"])
        self.assertEqual(selector["accounts"], ["1", "2", "3"])

    def test_merge_values_with_schema_preserves_defaults_for_missing_fields(self):
        template_text = Path("Config.ini").read_text(encoding="utf-8")
        schema = parse_template_to_form_schema(template_text)
        merged = merge_values_with_schema({"TimeZone": {"timezone": "UTC"}}, schema)

        self.assertEqual(merged["TimeZone"]["timezone"], "UTC")
        self.assertIn("GOOGLE_PHOTOS_CLIENT_ID_1", merged["Google Photos"])

    def test_resolve_ui_config_path_uses_base_dir_for_default_and_relative_paths(self):
        base_dir = Path("/tmp/photomigrator-ui")
        default_path = resolve_ui_config_path("", base_dir=base_dir)
        relative_path = resolve_ui_config_path("configs/custom.ini", base_dir=base_dir)
        custom_path = resolve_ui_config_path("~/custom-config.ini", base_dir=base_dir)

        self.assertEqual(default_path, base_dir / "Config.ini")
        self.assertEqual(relative_path, base_dir / "configs" / "custom.ini")
        self.assertEqual(custom_path, Path.home() / "custom-config.ini")

    def test_build_full_command_uses_current_executable_only_when_frozen(self):
        schema = build_parser_schema()
        values = {"google-takeout": "/tmp/Takeout"}

        with (
            patch("UI.shared.ui_runtime_is_frozen", return_value=True),
            patch("UI.shared.ui_runtime_launcher_executable", return_value="/Applications/PhotoMigrator"),
        ):
            command = build_full_command(Path("/opt/PhotoMigrator/src/PhotoMigrator.py"), schema, "google_takeout", values)

        self.assertEqual(command[0], "/Applications/PhotoMigrator")
        self.assertNotIn("/opt/PhotoMigrator/src/PhotoMigrator.py", command)
        self.assertIn("--google-takeout", command)

    def test_ui_runtime_launcher_executable_prefers_argv0_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher = Path(temp_dir) / "PhotoMigrator"
            launcher.write_text("", encoding="utf-8")

            with (
                patch("UI.shared.sys.argv", [str(launcher)]),
                patch("UI.shared.sys.executable", "/var/tmp/PhotoMigrator/python3"),
            ):
                resolved = ui_runtime_launcher_executable()

        self.assertEqual(resolved, str(launcher))

    def test_load_config_editor_model_falls_back_to_launch_config_when_project_template_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "bundle-temp"
            launch_cwd = temp_root / "release-folder"
            project_root.mkdir()
            launch_cwd.mkdir()
            template_text = Path("Config.ini").read_text(encoding="utf-8")
            config_path = launch_cwd / "Config.ini"
            config_path.write_text(template_text, encoding="utf-8")

            model = load_config_editor_model(project_root, config_path, launch_cwd=launch_cwd)

        self.assertIn("[TimeZone]", model["template_text"])
        self.assertTrue(model["schema"])
        self.assertTrue(model["sections"])

    def test_save_config_editor_values_preserves_content_when_template_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_root = temp_root / "bundle-temp"
            launch_cwd = temp_root / "release-folder"
            project_root.mkdir()
            launch_cwd.mkdir()
            template_text = Path("Config.ini").read_text(encoding="utf-8")
            config_path = launch_cwd / "Config.ini"
            config_path.write_text(template_text, encoding="utf-8")

            model = load_config_editor_model(project_root, config_path, launch_cwd=launch_cwd)
            model["values"]["TimeZone"]["timezone"] = "UTC"
            save_config_editor_values(config_path, model["values"], model["template_text"], model["schema"])
            saved_text = config_path.read_text(encoding="utf-8")

        self.assertIn("[TimeZone]", saved_text)
        self.assertIn("timezone = UTC", saved_text)

    def test_build_ui_subprocess_env_forces_color_and_removes_no_color(self):
        env = build_ui_subprocess_env({"NO_COLOR": "1", "TERM": "dumb"}, ui_mode="tui")

        self.assertEqual(env["PHOTOMIGRATOR_FORCE_COLOR"], "1")
        self.assertEqual(env["FORCE_COLOR"], "1")
        self.assertEqual(env["PY_COLORS"], "1")
        self.assertEqual(env["CLICOLOR_FORCE"], "1")
        self.assertEqual(env["PHOTOMIGRATOR_EMBEDDED_UI"], "1")
        self.assertEqual(env["PHOTOMIGRATOR_TUI_MODE"], "1")
        self.assertEqual(env["TERM"], "dumb")
        self.assertNotIn("NO_COLOR", env)

    def test_build_external_terminal_command_uses_osascript_on_macos(self):
        env = build_ui_subprocess_env({"TERM": "xterm-256color"}, ui_mode="gui", embedded_ui=False)

        with patch("UI.shared.shutil.which", side_effect=lambda name: "/usr/bin/osascript" if name == "osascript" else None):
            command = build_external_terminal_command(
                ["/usr/bin/python3", "/tmp/PhotoMigrator.py", "--automatic-migration"],
                Path("/tmp/project"),
                env,
                platform_name="darwin",
            )

        self.assertEqual(command[:2], ["osascript", "-e"])
        self.assertIn('tell application "Terminal"', command[2])
        self.assertIn("cd /tmp/project", command[2])
        self.assertIn("/usr/bin/python3", command[2])

    def test_build_external_terminal_command_uses_linux_terminal_emulator(self):
        env = build_ui_subprocess_env({"TERM": "xterm-256color"}, ui_mode="gui", embedded_ui=False)

        with patch("UI.shared.shutil.which", side_effect=lambda name: "/usr/bin/gnome-terminal" if name == "gnome-terminal" else None):
            command = build_external_terminal_command(
                ["/usr/bin/python3", "/tmp/PhotoMigrator.py", "--automatic-migration"],
                Path("/tmp/project"),
                env,
                platform_name="linux",
            )

        self.assertEqual(command[:3], ["gnome-terminal", "--", "bash"])
        self.assertEqual(command[3], "-lc")
        self.assertIn("cd /tmp/project", command[4])
        self.assertIn("/usr/bin/python3", command[4])


if __name__ == "__main__":
    unittest.main()
