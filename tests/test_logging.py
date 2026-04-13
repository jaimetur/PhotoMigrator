import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from Core import GlobalVariables as GV
from Core.CustomLogger import log_setup


class TestLoggingConfiguration(unittest.TestCase):
    def setUp(self):
        self.original_logger = GV.LOGGER

    def tearDown(self):
        if GV.LOGGER:
            for handler in GV.LOGGER.handlers[:]:
                handler.close()
                GV.LOGGER.removeHandler(handler)

        GV.LOGGER = self.original_logger

    def test_log_setup_skips_log_folder_and_file_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "LogsShouldNotExist")
            logger = log_setup(
                log_folder=log_dir,
                log_filename="test-no-log-file",
                log_level=logging.INFO,
                skip_logfile=True,
                skip_console=False,
                format="log",
            )
            logger.info("This message should only go to console handlers.")

            self.assertFalse(os.path.exists(log_dir))
            self.assertFalse(os.path.exists(os.path.join(log_dir, "test-no-log-file.log")))
            self.assertFalse(any(isinstance(handler, logging.FileHandler) for handler in logger.handlers))
