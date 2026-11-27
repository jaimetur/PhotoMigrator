import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import Core.ConfigReader as config_reader_module
from Core.ConfigReader import account_config_value

CONFIG_TEXT = """
[Synology Photos]
SYNOLOGY_URL = http://nas-shared:5000
SYNOLOGY_URL_2 = http://nas-two:5000
SYNOLOGY_USERNAME_1 = syno1
SYNOLOGY_PASSWORD_1 = pass1
SYNOLOGY_USERNAME_2 = syno2
SYNOLOGY_PASSWORD_2 = pass2

[Immich Photos]
IMMICH_URL = http://immich-shared:2283
IMMICH_API_KEY_ADMIN = admin-key
IMMICH_URL_2 = http://immich-two:2283
IMMICH_AUTH_METHOD_1 = password
IMMICH_API_KEY_USER_1 = API_KEY_USER_1
IMMICH_USERNAME_1 = one@example.test
IMMICH_PASSWORD_1 = secret1
IMMICH_API_KEY_USER_2 = user-two-key

[NextCloud Photos]
NEXTCLOUD_URL = http://cloud-shared
NEXTCLOUD_URL_2 = http://cloud-two/
NEXTCLOUD_USERNAME_1 = nc1
NEXTCLOUD_PASSWORD_1 = ncpass1
NEXTCLOUD_USERNAME_2 = nc2
NEXTCLOUD_PASSWORD_2 = ncpass2
"""


class TestAccountServers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "Config.ini"
        self.config_file.write_text(CONFIG_TEXT, encoding="utf-8")
        self.original_config = config_reader_module.CONFIG
        config_reader_module.CONFIG = None
        for target in (
            "Core.ConfigReader.LOGGER",
            "Features.ImmichPhotos.ClassImmichPhotos.LOGGER",
            "Features.SynologyPhotos.ClassSynologyPhotos.LOGGER",
            "Features.NextCloudPhotos.ClassNextCloudPhotos.LOGGER",
        ):
            patcher = patch(target, new_callable=MagicMock)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        config_reader_module.CONFIG = self.original_config
        self.temp_dir.cleanup()

    @staticmethod
    def _client(client_class, account_id):
        # The constructors sign in right away; only the config reading is tested here.
        client = client_class.__new__(client_class)
        client.ACCOUNT_ID = str(account_id)
        client.CONFIG = {}
        client.API_KEY_LOGIN = False
        return client

    def test_account_value_falls_back_to_the_shared_key(self):
        section = {"IMMICH_URL": "http://shared", "IMMICH_URL_2": "http://two", "IMMICH_URL_3": ""}
        self.assertEqual(account_config_value(section, "IMMICH_URL", 1), "http://shared")
        self.assertEqual(account_config_value(section, "IMMICH_URL", "2"), "http://two")
        self.assertEqual(account_config_value(section, "IMMICH_URL", 3), "http://shared")

    def test_missing_per_account_server_keys_are_not_reported(self):
        logger = logging.getLogger("test-account-servers")
        with patch.object(config_reader_module, "LOGGER", logger), self.assertLogs(logger, level="WARNING") as logs:
            logger.warning("start")
            config_reader_module.load_config(config_file=str(self.config_file), section_to_load="Immich Photos")
        self.assertFalse([line for line in logs.output if "IMMICH_URL_3" in line or "IMMICH_AUTH_METHOD_3" in line])

    def test_immich_accounts_use_their_server_and_sign_in_method(self):
        from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos

        first = self._client(ClassImmichPhotos, 1)
        first.read_config_file(config_file=str(self.config_file))
        self.assertEqual(first.IMMICH_URL, "http://immich-shared:2283")
        self.assertEqual(first.IMMICH_USER_API_KEY, "")  # 'password' ignores the API key placeholder
        self.assertFalse(first.API_KEY_LOGIN)
        self.assertEqual(first.IMMICH_API_KEY_ADMIN, "admin-key")

        second = self._client(ClassImmichPhotos, 2)
        second.read_config_file(config_file=str(self.config_file))
        self.assertEqual(second.IMMICH_URL, "http://immich-two:2283")
        self.assertEqual(second.IMMICH_USER_API_KEY, "user-two-key")
        self.assertTrue(second.API_KEY_LOGIN)
        self.assertEqual(second.IMMICH_API_KEY_ADMIN, "admin-key")

    def test_synology_and_nextcloud_accounts_use_their_server(self):
        from Features.NextCloudPhotos.ClassNextCloudPhotos import ClassNextCloudPhotos
        from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos

        synology = self._client(ClassSynologyPhotos, 2)
        synology.read_config_file(config_file=str(self.config_file))
        self.assertEqual(synology.SYNOLOGY_URL, "http://nas-two:5000")
        shared = self._client(ClassSynologyPhotos, 1)
        shared.read_config_file(config_file=str(self.config_file))
        self.assertEqual(shared.SYNOLOGY_URL, "http://nas-shared:5000")

        nextcloud = ClassNextCloudPhotos.__new__(ClassNextCloudPhotos)
        nextcloud.__dict__.update(account_id=2, max_parallel_uploads=12, max_parallel_downloads=12, use_system_proxy=False)
        nextcloud.read_config_file(config_file=str(self.config_file))
        self.assertEqual(nextcloud.base_url, "http://cloud-two")
        nextcloud_shared = ClassNextCloudPhotos.__new__(ClassNextCloudPhotos)
        nextcloud_shared.__dict__.update(account_id=1, max_parallel_uploads=12, max_parallel_downloads=12, use_system_proxy=False)
        nextcloud_shared.read_config_file(config_file=str(self.config_file))
        self.assertEqual(nextcloud_shared.base_url, "http://cloud-shared")

    def test_sign_in_method_decides_which_immich_fields_are_shown(self):
        from UI.ui_shared import immich_auth_method, immich_field_hidden_by_auth_method

        values = {"IMMICH_API_KEY_USER_1": "key", "IMMICH_USERNAME_2": "user", "IMMICH_AUTH_METHOD_3": "password", "IMMICH_API_KEY_USER_3": "key"}
        self.assertEqual(immich_auth_method(values, "1"), "api_key")
        self.assertEqual(immich_auth_method(values, "2"), "password")
        self.assertEqual(immich_auth_method(values, "3"), "password")
        self.assertEqual(immich_auth_method({}, "1"), "api_key")
        hidden = lambda key: immich_field_hidden_by_auth_method("Immich Photos", key, values)
        self.assertEqual([hidden(k) for k in ("IMMICH_API_KEY_USER_1", "IMMICH_USERNAME_1", "IMMICH_PASSWORD_1")], [False, True, True])
        self.assertEqual([hidden(k) for k in ("IMMICH_API_KEY_USER_3", "IMMICH_USERNAME_3", "IMMICH_PASSWORD_3")], [True, False, False])
        self.assertFalse(hidden("IMMICH_URL_1"))
        self.assertFalse(immich_field_hidden_by_auth_method("Synology Photos", "IMMICH_USERNAME_1", values))

    def test_settings_list_the_immich_account_fields_in_sign_in_order(self):
        from UI.ui_shared import parse_template_to_form_schema

        template = (Path(__file__).resolve().parents[1] / "Config.ini").read_text(encoding="utf-8")
        immich = next(section for section in parse_template_to_form_schema(template) if section["name"] == "Immich Photos")
        keys = [field["key"] for field in immich["fields"]]
        self.assertEqual(keys[:2], ["IMMICH_URL", "IMMICH_API_KEY_ADMIN"])
        self.assertEqual(
            keys[2:8],
            ["IMMICH_URL_1", "IMMICH_AUTH_METHOD_1", "IMMICH_API_KEY_USER_1", "IMMICH_USERNAME_1", "IMMICH_PASSWORD_1", "IMMICH_URL_2"],
        )
        self.assertFalse([key for key in keys if key.startswith("IMMICH_API_KEY_ADMIN_")])


if __name__ == "__main__":
    unittest.main()
