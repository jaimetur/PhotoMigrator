import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from Core.ArgsParser import checkArgs, create_global_variable_from_args, parse_arguments


class TestPhotoMigratorCLIParsing(unittest.TestCase):
    def test_create_global_variable_from_args_replaces_underscores(self):
        namespace = argparse.Namespace(input_folder="/tmp/input", output_folder="/tmp/output")
        args = create_global_variable_from_args(namespace)

        self.assertEqual(args["input-folder"], "/tmp/input")
        self.assertEqual(args["output-folder"], "/tmp/output")

    def test_check_args_parses_local_migration_and_exclusion_patterns(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            argv = [
                "photomigrator",
                f"--source={source_dir}",
                f"--target={target_dir}",
                "--exclude-folders=@eaDir,.@__thumb",
                "--exclude-files=SYNOFILE_THUMB*,Thumbs.db",
            ]
            with patch.object(sys, "argv", argv):
                args, parser = parse_arguments()
                checked = checkArgs(args, parser)

        self.assertEqual(checked["AUTOMATIC-MIGRATION"], [source_dir, target_dir])
        self.assertEqual(checked["exclude-folders"], ["@eaDir", ".@__thumb"])
        self.assertEqual(checked["exclude-files"], ["SYNOFILE_THUMB*", "Thumbs.db"])

    def test_check_args_rejects_dashboard_without_automatic_migration(self):
        argv = ["photomigrator", "--dashboard=true"]
        with patch.object(sys, "argv", argv):
            args, parser = parse_arguments()
            with self.assertRaises(SystemExit):
                checkArgs(args, parser)

    def test_check_args_allows_disabled_native_deletion_with_disabled_detection(self):
        argv = [
            "photomigrator",
            "--dup-immich-native-algorithm=false",
            "--dup-immich-native-deletion=false",
        ]
        with patch.object(sys, "argv", argv):
            args, parser = parse_arguments()
            checked = checkArgs(args, parser)

        self.assertFalse(checked["dup-immich-native-algorithm"])
        self.assertFalse(checked["dup-immich-native-deletion"])

    def test_people_and_stack_controls_default_to_enabled_and_accept_false(self):
        with patch.object(sys, "argv", ["photomigrator"]):
            args, parser = parse_arguments()

        self.assertTrue(args["import-people"])
        self.assertTrue(args["create-stacks"])
        self.assertTrue(args["google-process-people"])

        with patch.object(
            sys,
            "argv",
            [
                "photomigrator",
                "--import-people=false",
                "--create-stacks=false",
                "--google-process-people=false",
            ],
        ):
            args, _ = parse_arguments()

        self.assertFalse(args["import-people"])
        self.assertFalse(args["create-stacks"])
        self.assertFalse(args["google-process-people"])

    def test_large_push_retry_and_immich_upload_timeout_controls(self):
        with patch.object(sys, "argv", ["photomigrator"]):
            args, _ = parse_arguments()

        self.assertEqual(args["push-asset-max-size-mb"], 0)
        self.assertEqual(args["immich-upload-timeout-seconds"], 900)

        with patch.object(
            sys,
            "argv",
            [
                "photomigrator",
                "--push-asset-max-size-mb=1024",
                "--immich-upload-timeout-seconds=1800",
            ],
        ):
            args, _ = parse_arguments()

        self.assertEqual(args["push-asset-max-size-mb"], 1024)
        self.assertEqual(args["immich-upload-timeout-seconds"], 1800)

        with patch.object(sys, "argv", [
            "photomigrator",
            "--client=immich",
            "--upload-all=/photos",
            "--immich-upload-timeout-seconds=1200",
        ]):
            args, _ = parse_arguments()
        self.assertEqual(args["immich-upload-timeout-seconds"], 1200)

        with patch.object(sys, "argv", ["photomigrator", "--push-asset-max-size-mb=-1"]):
            with self.assertRaises(SystemExit):
                parse_arguments()

        with patch.object(sys, "argv", ["photomigrator", "--immich-upload-timeout-seconds=0"]):
            with self.assertRaises(SystemExit):
                parse_arguments()

    def test_immich_native_duplicate_detection_defaults_to_people_tags_then_quality(self):
        with patch.object(sys, "argv", ["photomigrator"]):
            args, parser = parse_arguments()

        self.assertTrue(args["dup-immich-native-algorithm"])
        self.assertEqual(args["dup-asset-keeper"], "more-people/tags-then-better-quality")
        checked = checkArgs(args, parser)
        self.assertFalse(checked["dup-immich-native-deletion"])

    def test_native_duplicate_deletion_requires_native_better_quality_strategy(self):
        with patch.object(
            sys,
            "argv",
            [
                "photomigrator",
                "--dup-immich-native-deletion=true",
                "--dup-asset-keeper=oldest",
            ],
        ):
            args, parser = parse_arguments()
            with self.assertRaises(SystemExit):
                checkArgs(args, parser)

    def test_native_duplicate_deletion_is_enabled_for_native_better_quality_strategy(self):
        with patch.object(
            sys,
            "argv",
            ["photomigrator", "--dup-asset-keeper=better-quality"],
        ):
            args, parser = parse_arguments()
            checked = checkArgs(args, parser)

        self.assertTrue(checked["dup-immich-native-deletion"])

    def test_small_album_max_assets_defaults_to_three_and_rejects_non_positive_values(self):
        with patch.object(sys, "argv", ["photomigrator"]):
            args, _ = parse_arguments()
        self.assertEqual(args["small-album-max-assets"], 3)

        with patch.object(sys, "argv", ["photomigrator", "--small-album-max-assets", "4"]):
            args, _ = parse_arguments()
        self.assertEqual(args["small-album-max-assets"], 4)

        with patch.object(sys, "argv", ["photomigrator", "--small-album-max-assets", "0"]):
            with self.assertRaises(SystemExit):
                parse_arguments()

        with patch.object(
            sys,
            "argv",
            ["photomigrator", "--no-try-small-albums-grouping", "--small-album-max-assets", "4"],
        ):
            with self.assertRaises(SystemExit):
                parse_arguments()

    def test_check_args_parses_single_comma_separated_rename_albums_value_for_dashdash_replacement(self):
        argv = [
            "photomigrator",
            "--rename-albums",
            "*-*, --",
            "--client=immich",
        ]
        with patch.object(sys, "argv", argv):
            args, parser = parse_arguments()
            checked = checkArgs(args, parser)

        self.assertEqual(checked["rename-albums"], ["*-*", "--"])

    def test_check_args_normalizes_remove_album_creation_date_filters(self):
        argv = [
            "photomigrator",
            "--client=immich",
            "--remove-albums=*Temp*",
            "--created-from=2024-01-01",
            "--created-to=2024-12-31",
        ]
        with patch.object(sys, "argv", argv):
            args, parser = parse_arguments()
            checked = checkArgs(args, parser)

        self.assertEqual(checked["created-from"], "2024-01-01T00:00:00.000Z")
        self.assertEqual(checked["created-to"], "2024-12-31T00:00:00.000Z")


if __name__ == "__main__":
    unittest.main()
