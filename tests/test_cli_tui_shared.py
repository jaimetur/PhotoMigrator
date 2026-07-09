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
    from UI.ui_shared import (
        MIGRATION_FILTER_DESTS,
        build_automatic_migration_filter_fields,
        build_cli_args,
        build_full_command,
        build_ui_subprocess_env,
        build_parser_schema,
        build_external_terminal_command,
        build_windows_external_terminal_script,
        command_preview_string,
        command_to_string,
        compose_migration_endpoint,
        compose_find_duplicates_value,
        compose_rename_albums_value,
        config_section_account_selector,
        effective_interactive_field_value,
        merge_values_with_schema,
        load_config_editor_model,
        normalize_organize_local_folder_ui_state,
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

try:
    from UI.cli_tui import preferred_tui_panel_widget_ids
    CLI_TUI_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    preferred_tui_panel_widget_ids = None
    CLI_TUI_IMPORT_ERROR = exc


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

    def test_build_parser_schema_exposes_album_name_flags_in_automatic_migration(self):
        schema = build_parser_schema()

        automatic_dests = {field["dest"] for field in schema["tabs"]["automatic_migration"]}

        self.assertIn("prefer-canonical-album-names", automatic_dests)
        self.assertIn("consolidate-similar-albums", automatic_dests)

    def test_build_parser_schema_standalone_actions_exclude_auxiliary_organize_fields(self):
        schema = build_parser_schema()

        standalone_dests = {field["dest"] for field in schema["tabs"]["standalone_features"]}

        self.assertIn("organize-local-folder-by-date", standalone_dests)
        self.assertNotIn("organize-output-folder-suffix", standalone_dests)
        self.assertNotIn("organize-folder-structure", standalone_dests)
        self.assertNotIn("move-original-files", standalone_dests)

    def test_build_parser_schema_defaults_native_icloud_writer_to_true_for_ui(self):
        schema = build_parser_schema()

        self.assertTrue(bool(schema["fields_by_dest"]["icloud-prefer-native-exif-writer"]["default"]))

    def test_build_parser_schema_defaults_organize_suffix_to_interactive_processed_value(self):
        schema = build_parser_schema()

        self.assertEqual(schema["fields_by_dest"]["organize-output-folder-suffix"]["default"], "processed")

    def test_effective_interactive_field_value_shows_processed_suffix_when_output_folder_is_empty(self):
        schema = build_parser_schema()
        field = schema["fields_by_dest"]["organize-output-folder-suffix"]

        shown_value = effective_interactive_field_value(
            field,
            {
                "output-folder": "",
                "organize-output-folder-suffix": "",
            },
        )

        self.assertEqual(shown_value, "processed")

    def test_normalize_organize_local_folder_ui_state_clears_suffix_when_output_folder_is_selected(self):
        schema = build_parser_schema()
        values = {
            "output-folder": "/photos/organized",
            "organize-output-folder-suffix": "processed",
        }

        changed = normalize_organize_local_folder_ui_state(values, schema)

        self.assertTrue(changed)
        self.assertEqual(values["organize-output-folder-suffix"], "")

    def test_normalize_organize_local_folder_ui_state_restores_default_suffix_when_output_folder_is_empty(self):
        schema = build_parser_schema()
        values = {
            "output-folder": "",
            "organize-output-folder-suffix": "",
        }

        changed = normalize_organize_local_folder_ui_state(values, schema)

        self.assertTrue(changed)
        self.assertEqual(values["organize-output-folder-suffix"], "processed")

    def test_build_cli_args_appends_native_icloud_writer_flag_only_when_enabled(self):
        schema = build_parser_schema()

        enabled_args = build_cli_args(schema, "icloud_takeout", {"icloud-prefer-native-exif-writer": True})
        disabled_args = build_cli_args(schema, "icloud_takeout", {"icloud-prefer-native-exif-writer": False})

        self.assertIn("--icloud-prefer-native-exif-writer", enabled_args)
        self.assertNotIn("--icloud-prefer-native-exif-writer", disabled_args)

    def test_build_cli_args_appends_google_keep_takeout_flag_only_when_enabled(self):
        schema = build_parser_schema()

        enabled_args = build_cli_args(
            schema,
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "google-keep-takeout-folder": True},
        )
        disabled_args = build_cli_args(
            schema,
            "google_takeout",
            {"google-takeout": "/tmp/Takeout", "google-keep-takeout-folder": False},
        )

        self.assertIn("--google-keep-takeout-folder", enabled_args)
        self.assertNotIn("--google-keep-takeout-folder", disabled_args)

    def test_build_cli_args_appends_google_takeout_processing_flags_only_when_enabled(self):
        schema = build_parser_schema()

        enabled_args = build_cli_args(
            schema,
            "google_takeout",
            {
                "google-takeout": "/tmp/Takeout",
                "google-remove-duplicates-files": True,
                "google-rename-albums-folders": True,
                "google-skip-extras-files": True,
            },
        )
        disabled_args = build_cli_args(
            schema,
            "google_takeout",
            {
                "google-takeout": "/tmp/Takeout",
                "google-remove-duplicates-files": False,
                "google-rename-albums-folders": False,
                "google-skip-extras-files": False,
            },
        )

        self.assertIn("--google-remove-duplicates-files", enabled_args)
        self.assertIn("--google-rename-albums-folders", enabled_args)
        self.assertIn("--google-skip-extras-files", enabled_args)
        self.assertNotIn("--google-remove-duplicates-files", disabled_args)
        self.assertNotIn("--google-rename-albums-folders", disabled_args)
        self.assertNotIn("--google-skip-extras-files", disabled_args)

    def test_build_cli_args_appends_no_log_file_flag_only_when_enabled(self):
        schema = build_parser_schema()

        enabled_args = build_cli_args(schema, "google_takeout", {"google-takeout": "/tmp/Takeout", "no-log-file": True})
        disabled_args = build_cli_args(schema, "google_takeout", {"google-takeout": "/tmp/Takeout", "no-log-file": False})

        self.assertIn("--no-log-file", enabled_args)
        self.assertNotIn("--no-log-file", disabled_args)

    def test_build_automatic_migration_filter_fields_create_am_overrides(self):
        schema = build_parser_schema()

        fields = build_automatic_migration_filter_fields(schema)

        self.assertEqual(len(fields), len(MIGRATION_FILTER_DESTS))
        self.assertTrue(all(str(field["dest"]).startswith("am-") for field in fields))
        self.assertEqual(fields[0]["label"], "Filter By Type")
        self.assertEqual(fields[0]["default"], "")

    def test_build_cli_args_automatic_migration_promotes_am_filter_overrides(self):
        schema = build_parser_schema()
        values = {
            "source": "/tmp/source",
            "target": "/tmp/target",
            "filter-by-type": "image",
            "am-filter-by-type": "video",
            "exclude-files": ["Thumbs.db"],
            "am-exclude-files": [".DS_Store", "Thumbs.db"],
        }

        args = build_cli_args(schema, "automatic_migration", values)

        self.assertIn("--filter-by-type", args)
        self.assertIn("video", args)
        self.assertIn("--exclude-files", args)
        exclude_index = args.index("--exclude-files")
        self.assertEqual(args[exclude_index + 1 : exclude_index + 3], [".DS_Store", "Thumbs.db"])

    def test_build_cli_args_composes_cloud_rename_albums_value(self):
        schema = build_parser_schema()
        values = {
            "account-id": "2",
            "rename-pattern": r"\\b(\\d{4})\\.(\\d{2})\\.(\\d{2})\\b",
            "replacement-pattern": r"\\1-\\2-\\3",
            "preview-album-actions": True,
        }

        args = build_cli_args(schema, "synology_photos", values, "rename-albums")
        args_text = command_to_string(["python", *args])

        self.assertIn("--rename-albums", args)
        self.assertIn("--client", args)
        self.assertIn("synology", args)
        self.assertIn("--account-id", args)
        self.assertIn("--preview-album-actions", args)
        self.assertIn("2", args)
        self.assertIn(r"\\b(\\d{4})\\.(\\d{2})\\.(\\d{2})\\b, \\1-\\2-\\3", args_text)

    def test_build_cli_args_includes_preview_flag_for_remove_albums(self):
        schema = build_parser_schema()
        values = {
            "account-id": "1",
            "remove-albums": "*Temp*",
            "preview-album-actions": True,
            "remove-albums-assets": True,
        }

        args = build_cli_args(schema, "immich_photos", values, "remove-albums")

        self.assertIn("--remove-albums", args)
        self.assertIn("*Temp*", args)
        self.assertIn("--preview-album-actions", args)
        self.assertIn("--remove-albums-assets", args)

    def test_build_cli_args_includes_album_name_flags_for_cloud_upload(self):
        schema = build_parser_schema()
        values = {
            "account-id": "2",
            "upload-all": "/photos/library",
            "albums-folders": ["Albums"],
            "prefer-canonical-album-names": True,
            "consolidate-similar-albums": True,
        }

        args = build_cli_args(schema, "immich_photos", values, "upload-all")

        self.assertIn("--upload-all", args)
        self.assertIn("/photos/library", args)
        self.assertIn("--prefer-canonical-album-names", args)
        self.assertIn("--consolidate-similar-albums", args)

    def test_build_cli_args_includes_album_name_flags_for_automatic_migration(self):
        schema = build_parser_schema()
        values = {
            "source": "synology-photos-1",
            "target": "immich-photos-2",
            "prefer-canonical-album-names": True,
            "consolidate-similar-albums": True,
        }

        args = build_cli_args(schema, "automatic_migration", values)

        self.assertIn("--source", args)
        self.assertIn("--target", args)
        self.assertIn("--prefer-canonical-album-names", args)
        self.assertIn("--consolidate-similar-albums", args)

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

    def test_build_cli_args_includes_optional_fields_for_organize_local_folder_by_date(self):
        schema = build_parser_schema()
        values = {
            "organize-local-folder-by-date": "/photos/raw",
            "output-folder": "/photos/processed",
            "organize-output-folder-suffix": "sorted",
            "organize-folder-structure": "year",
            "move-original-files": True,
        }

        args = build_cli_args(schema, "standalone_features", values, "organize-local-folder-by-date")

        self.assertIn("--organize-local-folder-by-date", args)
        self.assertIn("/photos/raw", args)
        self.assertIn("--output-folder", args)
        self.assertIn("/photos/processed", args)
        self.assertIn("--organize-output-folder-suffix", args)
        self.assertIn("sorted", args)
        self.assertIn("--organize-folder-structure", args)
        self.assertIn("year", args)
        self.assertIn("--move-original-files", args)

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
            patch("UI.ui_shared.ui_runtime_is_frozen", return_value=True),
            patch("UI.ui_shared.ui_runtime_launcher_executable", return_value="/Applications/PhotoMigrator"),
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
                patch.dict("UI.ui_shared.os.environ", {"PHOTOMIGRATOR_LAUNCHER_PATH": "", "PHOTOMIGRATOR_ORIGINAL_CWD": ""}, clear=False),
                patch("UI.ui_shared.sys.argv", [str(launcher)]),
                patch("UI.ui_shared.sys.executable", "/var/tmp/PhotoMigrator/python3"),
            ):
                resolved = ui_runtime_launcher_executable()

        self.assertEqual(resolved, str(launcher))

    def test_ui_runtime_launcher_executable_prefers_explicit_launcher_env(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launcher = Path(temp_dir) / "PhotoMigrator_v4.3.0_windows_x64.exe"
            launcher.write_text("", encoding="utf-8")

            with (
                patch.dict("UI.ui_shared.os.environ", {"PHOTOMIGRATOR_LAUNCHER_PATH": str(launcher)}, clear=False),
                patch("UI.ui_shared.sys.argv", ["/var/tmp/PhotoMigrator/python3.exe"]),
                patch("UI.ui_shared.sys.executable", "/var/tmp/PhotoMigrator/python3.exe"),
            ):
                resolved = ui_runtime_launcher_executable()

        self.assertEqual(resolved, str(launcher))

    def test_ui_runtime_launcher_executable_recovers_versioned_binary_from_original_cwd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            launch_dir = Path(temp_dir)
            launcher = launch_dir / "PhotoMigrator_v4.3.0_windows_x64.exe"
            launcher.write_text("", encoding="utf-8")

            with (
                patch.dict(
                    "UI.ui_shared.os.environ",
                    {"PHOTOMIGRATOR_LAUNCHER_PATH": "", "PHOTOMIGRATOR_ORIGINAL_CWD": str(launch_dir)},
                    clear=False,
                ),
                patch("UI.ui_shared.sys.argv", ["/var/tmp/PhotoMigrator/python3.exe"]),
                patch("UI.ui_shared.sys.executable", "/var/tmp/PhotoMigrator/python3.exe"),
                patch("UI.ui_shared.sys.platform", "win32"),
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

        with patch("UI.ui_shared.shutil.which", side_effect=lambda name: "/usr/bin/osascript" if name == "osascript" else None):
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

        with patch("UI.ui_shared.shutil.which", side_effect=lambda name: "/usr/bin/gnome-terminal" if name == "gnome-terminal" else None):
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

    def test_build_windows_external_terminal_script_writes_title_env_and_completion_file(self):
        env = build_ui_subprocess_env({"TERM": "xterm-256color"}, ui_mode="gui", embedded_ui=False)

        script = build_windows_external_terminal_script(
            [r"C:\Python311\python.exe", r"C:\PhotoMigrator\PhotoMigrator.py", "--automatic-migration"],
            Path(r"C:\Users\Test User\PhotoMigrator"),
            env,
            completion_file=Path(r"C:\Temp\dashboard_status.txt"),
        )

        self.assertIn("@echo off", script)
        self.assertIn("title PhotoMigrator Live Dashboard", script)
        self.assertIn('set "PHOTOMIGRATOR_GUI_MODE=1"', script)
        self.assertIn('cd /d "C:\\Users\\Test User\\PhotoMigrator"', script)
        self.assertIn(r"C:\Python311\python.exe", script)
        self.assertIn(r"C:\PhotoMigrator\PhotoMigrator.py --automatic-migration", script)
        self.assertIn('> "C:\\Temp\\dashboard_status.txt" echo(%PHOTOMIGRATOR_EXIT_CODE%', script)
        self.assertIn("exit /b %PHOTOMIGRATOR_EXIT_CODE%", script)

    def test_preferred_tui_panel_widget_ids_prioritize_primary_controls(self):
        if CLI_TUI_IMPORT_ERROR is not None:
            self.skipTest(f"CLI TUI dependencies are not installed in this environment: {CLI_TUI_IMPORT_ERROR}")

        self.assertEqual(
            preferred_tui_panel_widget_ids("sidebar-features", active_general_tab="feature", active_module="automatic_migration")[:2],
            ["module-tab-automatic_migration", "run-btn"],
        )
        self.assertEqual(
            preferred_tui_panel_widget_ids("general-tabs", active_general_tab="feature", active_module="automatic_migration")[:2],
            ["general-tab-feature", "load-config-btn"],
        )


if __name__ == "__main__":
    unittest.main()
