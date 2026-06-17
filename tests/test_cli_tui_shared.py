import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from UI.shared import (
        build_cli_args,
        build_parser_schema,
        command_to_string,
        compose_migration_endpoint,
        compose_find_duplicates_value,
        compose_rename_albums_value,
        config_section_account_selector,
        merge_values_with_schema,
        parse_find_duplicates_value,
        parse_migration_endpoint,
        parse_rename_albums_value,
        parse_template_to_form_schema,
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


if __name__ == "__main__":
    unittest.main()
