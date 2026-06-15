import unittest
from unittest.mock import patch

import Features.AutomaticMigration.AutomaticMigration as automatic_module
import Core.ExecutionModes as execution_modes


def _base_args():
    return {
        "source": "",
        "target": "",
        "google-takeout": "",
        "icloud-takeout": "",
        "upload-albums": "",
        "upload-all": "",
        "download-albums": "",
        "download-all": "",
        "remove-albums": "",
        "rename-albums": "",
        "remove-empty-albums": False,
        "remove-duplicates-albums": False,
        "merge-duplicates-albums": False,
        "remove-all-albums": "",
        "remove-all-assets": "",
        "remove-orphan-assets": "",
        "fix-symlinks-broken": "",
        "find-duplicates": ["list", ""],
        "process-duplicates": "",
        "rename-folders-content-based": "",
        "show-gpth-info": False,
        "account-id": 1,
        "client": "immich",
    }


class TestExecutionModes(unittest.TestCase):
    def test_detect_and_run_execution_mode_dispatches_automatic_migration(self):
        args = _base_args()
        args["source"] = "synology"
        args["target"] = "immich"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(automatic_module, "ARGS", args),
            patch.object(execution_modes, "mode_AUTOMATIC_MIGRATION") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_google_takeout(self):
        args = _base_args()
        args["google-takeout"] = "/tmp/Takeout"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_google_takeout") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_icloud_takeout(self):
        args = _base_args()
        args["icloud-takeout"] = "/tmp/iCloudExport"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_icloud_takeout") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once()

    def test_detect_and_run_execution_mode_dispatches_upload_albums(self):
        args = _base_args()
        args["upload-albums"] = "/tmp/albums"
        args["client"] = "nextcloud"

        with (
            patch.object(execution_modes, "ARGS", args),
            patch.object(execution_modes, "mode_cloud_upload_albums") as mock_mode,
        ):
            execution_modes.detect_and_run_execution_mode()

        mock_mode.assert_called_once_with(client="nextcloud")


if __name__ == "__main__":
    unittest.main()
