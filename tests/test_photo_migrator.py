import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
