import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import Core.ConfigReader as config_reader_module


class TestConfigReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config_file = self.root / "Config.ini"
        self.logger = logging.getLogger("test-config-reader")
        self.logger.handlers = []
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())
        self.logger.setLevel(logging.INFO)
        self.original_config = config_reader_module.CONFIG
        config_reader_module.CONFIG = None

    def tearDown(self):
        config_reader_module.CONFIG = self.original_config
        self.temp_dir.cleanup()

    def _write_config(self, text):
        self.config_file.write_text(text, encoding="utf-8")

    def test_load_config_reads_requested_section(self):
        self._write_config(
            """
[Synology Photos]
SYNOLOGY_URL = https://example.test
SYNOLOGY_USERNAME_1 = user1
SYNOLOGY_PASSWORD_1 = pass1
"""
        )

        with patch.object(config_reader_module, "LOGGER", self.logger):
            loaded = config_reader_module.load_config(
                config_file=str(self.config_file),
                section_to_load="Synology Photos",
            )

        self.assertEqual(loaded["Synology Photos"]["SYNOLOGY_URL"], "https://example.test")
        self.assertEqual(loaded["Synology Photos"]["SYNOLOGY_USERNAME_1"], "user1")

    def test_load_config_applies_environment_variable_override(self):
        self._write_config(
            """
[Synology Photos]
SYNOLOGY_URL = https://config-value.test
SYNOLOGY_USERNAME_1 = user1
SYNOLOGY_PASSWORD_1 = pass1
"""
        )

        with (
            patch.object(config_reader_module, "LOGGER", self.logger),
            patch.dict(os.environ, {"SYNOLOGY_URL": "https://env-value.test"}, clear=False),
        ):
            loaded = config_reader_module.load_config(
                config_file=str(self.config_file),
                section_to_load="Synology Photos",
            )
            source = config_reader_module.get_env_override_source("SYNOLOGY_URL")

        self.assertEqual(loaded["Synology Photos"]["SYNOLOGY_URL"], "https://env-value.test")
        self.assertEqual(source, "SYNOLOGY_URL")

    def test_load_config_uses_runtime_global_logger_proxy(self):
        self._write_config(
            """
[Synology Photos]
SYNOLOGY_URL = https://example.test
SYNOLOGY_USERNAME_1 = user1
SYNOLOGY_PASSWORD_1 = pass1
"""
        )

        with patch.object(config_reader_module.GV, "LOGGER", self.logger):
            loaded = config_reader_module.load_config(
                config_file=str(self.config_file),
                section_to_load="Synology Photos",
            )

        self.assertEqual(loaded["Synology Photos"]["SYNOLOGY_URL"], "https://example.test")


if __name__ == "__main__":
    unittest.main()
