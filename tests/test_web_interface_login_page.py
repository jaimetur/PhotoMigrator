import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class TestWebInterfaceLoginWebsiteLink(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base_path = Path(self.temp_dir.name)
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
        os.environ["PHOTOMIGRATOR_WEB_DB_PATH"] = str(base_path / "web_interface.db")
        os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_DATA"] = str(base_path / "data")
        os.environ["PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1"] = str(base_path / "volumes")
        os.environ["PHOTOMIGRATOR_CONFIG_PATH"] = str(base_path / "Config.ini")
        os.environ["PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH"] = str(PROJECT_ROOT / "tests" / "test_data" / "config_test.ini")
        os.environ["PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR"] = str(base_path / "generated")
        os.environ["PHOTOMIGRATOR_STATE_PATH"] = str(base_path / "state.json")

        sys.modules.pop("web_interface.app", None)
        try:
            import web_interface.app as web_app
        except ModuleNotFoundError as exc:
            self.skipTest(f"web interface dependencies are not installed in this environment: {exc}")
        self.web_app = importlib.reload(web_app)

    def tearDown(self):
        sys.modules.pop("web_interface.app", None)
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def _render_login(self, website_url):
        template = self.web_app.templates.get_template("login.html")
        return template.render(
            request=None,
            tool_name="PhotoMigrator",
            tool_version="v5.0.0",
            show_default_admin_hint=False,
            show_demo_hint=False,
            website_url=website_url,
        )

    def test_landing_page_is_served_as_public_static_site(self):
        self.assertTrue((self.web_app.LANDING_ROOT / "index.html").is_file())
        mounts = {getattr(route, "name", None): getattr(route, "path", None) for route in self.web_app.app.routes}
        self.assertEqual(mounts.get("landing"), "/landing/media")
        self.assertEqual(self.web_app._project_website_url(), "/")

    def test_root_serves_the_landing_and_old_landing_urls_redirect(self):
        response = self.web_app.home(None)
        page = response.body.decode("utf-8")
        self.assertIn('src="/landing/media/', page)
        self.assertNotIn('src="media/', page)
        self.assertIn('href="/app/">Sign in</a>', page)
        for redirect in (self.web_app.landing_redirect(),):
            self.assertEqual((redirect.status_code, redirect.headers["location"]), (301, "/"))
        entry = self.web_app.app_entry(None)
        self.assertEqual((entry.status_code, entry.headers["location"]), (302, "/login"))

    def test_website_link_falls_back_to_project_page_without_landing_folder(self):
        with patch.object(self.web_app, "LANDING_ROOT", Path(self.temp_dir.name) / "missing-landing"):
            self.assertEqual(self.web_app._project_website_url(), self.web_app.PROJECT_WEBSITE_FALLBACK_URL)

    def test_login_page_links_logo_and_website_button_to_the_website(self):
        html = self._render_login("/")
        self.assertIn('id="login-website-link"', html)
        self.assertEqual(html.count('href="/"'), 2)
        self.assertIn("Website", html)


if __name__ == "__main__":
    unittest.main()
