import importlib
import json
import os
import sys
import tempfile
import unittest
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SMTP_ENV_KEYS = ["SMTP_HOST", "SMTP_PORT", "SMTP_SECURITY", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_FROM_NAME"]


class TestWebInterfaceAccountsAndEmail(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi import HTTPException, Response
            from starlette.requests import Request
        except ModuleNotFoundError as exc:
            self.skipTest(f"fastapi is not installed in this environment: {exc}")
        self.HTTPException = HTTPException
        self.Response = Response
        self.Request = Request
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
            "PHOTOMIGRATOR_WEB_PUBLIC_URL",
            "PHOTOMIGRATOR_WEB_ACCOUNT_REQUESTS",
            *SMTP_ENV_KEYS,
        ]
        self.env_backup = {key: os.environ.get(key) for key in self.env_keys}
        for key in ["PHOTOMIGRATOR_WEB_PUBLIC_URL", "PHOTOMIGRATOR_WEB_ACCOUNT_REQUESTS", *SMTP_ENV_KEYS]:
            os.environ.pop(key, None)
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
        self.web_app.PARSER_SCHEMA = self.web_app._load_parser_schema()
        self.web_app.CONFIG_TEMPLATE_CONTENT = self.web_app._load_default_config_template()
        self.web_app.CONFIG_FORM_SCHEMA = self.web_app._extend_form_schema_with_web_interface_theme(
            self.web_app._parse_template_to_form_schema(self.web_app.CONFIG_TEMPLATE_CONTENT)
        )
        self.web_app._init_web_db(self.web_app.CONFIG_FORM_SCHEMA)
        self.admin = self.web_app._fetch_user_by_username("admin")
        self._set_email(self.admin["id"], "owner@example.com")
        self.admin = self.web_app._fetch_user_by_id(self.admin["id"])

        self.sent = []
        send_patch = patch.object(self.web_app.mailer, "send_later", side_effect=self._record_mail)
        send_patch.start()
        self.addCleanup(send_patch.stop)

    def tearDown(self):
        sys.modules.pop("web_interface.app", None)
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def _record_mail(self, recipients, subject, html_body, reply_to=None):
        self.sent.append({"to": list(recipients), "subject": subject, "html": html_body, "reply_to": reply_to})
        return True

    def _set_email(self, user_id, email):
        conn = self.web_app._db_connect()
        try:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, int(user_id)))
            conn.commit()
        finally:
            conn.close()

    def _request(self, ip="203.0.113.7"):
        return self.Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": [(b"host", b"photos.example.com")],
                "client": (ip, 5000),
                "scheme": "https",
                "server": ("photos.example.com", 443),
                "query_string": b"",
            }
        )

    def _request_account(self, username="newuser", email="New.User@Example.com", password="long-password", ip="203.0.113.7", **extra):
        payload = self.web_app.AccountRequest(username=username, email=email, password=password, **extra)
        return self.web_app.api_request_account(payload, self._request(ip))

    def test_account_request_creates_pending_account_and_emails_admins_and_requester(self):
        self.assertEqual(self._request_account(note="Family album"), {"requested": True})

        user = self.web_app._fetch_user_by_username("newuser")
        self.assertEqual(user["email"], "new.user@example.com")
        self.assertFalse(bool(user["is_active"]))
        self.assertEqual(user["request_note"], "Family album")
        self.assertTrue(self.web_app._is_pending_account_request(user))
        self.assertEqual([mail["to"] for mail in self.sent], [["owner@example.com"], ["new.user@example.com"]])
        self.assertIn("https://photos.example.com/admin", self.sent[0]["html"])
        self.assertEqual(self.sent[0]["reply_to"], "new.user@example.com")

    def test_account_request_requires_a_valid_and_unique_email(self):
        invalid_cases = (("", 400), ("not-an-email", 400), ("<img/src=x/onerror=alert(1)>@example.com", 400), ("OWNER@example.com", 409))
        for email, expected_status in invalid_cases:
            with self.subTest(email=email):
                with self.assertRaises(self.HTTPException) as context:
                    self._request_account(email=email)
                self.assertEqual(context.exception.status_code, expected_status)
        self.assertIsNone(self.web_app._fetch_user_by_username("newuser"))

    def test_account_request_honeypot_and_throttle(self):
        self.assertEqual(self._request_account(website="https://spam.example", ip="198.51.100.1"), {"requested": True})
        self.assertIsNone(self.web_app._fetch_user_by_username("newuser"))
        for index in range(1, self.web_app.WEB_ACCOUNT_REQUESTS_PER_HOUR):
            self._request_account(username=f"user{index}", email=f"user{index}@example.com", ip="198.51.100.1")
        with self.assertRaises(self.HTTPException) as context:
            self._request_account(username="toomany", email="toomany@example.com", ip="198.51.100.1")
        self.assertEqual(context.exception.status_code, 429)

        # A spoofed IP per request still hits the total limit.
        with self.assertRaises(self.HTTPException) as context:
            for index in range(self.web_app.WEB_ACCOUNT_REQUESTS_PER_HOUR_TOTAL + 1):
                self._request_account(username=f"spoof{index}", email=f"spoof{index}@example.com", ip=f"192.0.2.{index}")
        self.assertEqual(context.exception.status_code, 429)

    def test_login_accepts_username_or_email_of_active_accounts_only(self):
        self._request_account()
        with self.assertRaises(self.HTTPException) as context:
            self.web_app.api_login(self.web_app.LoginRequest(username="new.user@example.com", password="long-password"), self.Response(), self._request())
        self.assertEqual(context.exception.status_code, 401)

        user = self.web_app._fetch_user_by_username("newuser")
        self.web_app.admin_update_user(user["id"], self.web_app.AdminUserUpdateRequest(is_active=True), self._request(), self.admin)
        for identifier in ("newuser", "NEW.USER@example.com"):
            with self.subTest(identifier=identifier):
                result = self.web_app.api_login(self.web_app.LoginRequest(username=identifier, password="long-password"), self.Response(), self._request())
                self.assertEqual(result, {"ok": True})

    def test_activating_a_request_approves_it_and_emails_the_user(self):
        self._request_account()
        user = self.web_app._fetch_user_by_username("newuser")
        self.sent.clear()

        self.web_app.admin_update_user(user["id"], self.web_app.AdminUserUpdateRequest(is_active=True), self._request(), self.admin)

        updated = self.web_app._fetch_user_by_id(user["id"])
        self.assertTrue(bool(updated["is_active"]))
        self.assertFalse(self.web_app._is_pending_account_request(updated))
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["subject"], "Your account is active")
        self.assertEqual(self.sent[0]["to"], ["new.user@example.com"])

        self.web_app.admin_update_user(user["id"], self.web_app.AdminUserUpdateRequest(is_active=False), self._request(), self.admin)
        self.assertEqual(self.sent[-1]["subject"], "Your account has been disabled")

    def test_deleting_a_request_rejects_it_by_email(self):
        self._request_account()
        user = self.web_app._fetch_user_by_username("newuser")
        self.sent.clear()

        self.web_app.admin_delete_user(user["id"], self.admin)

        self.assertIsNone(self.web_app._fetch_user_by_id(user["id"]))
        self.assertEqual([mail["subject"] for mail in self.sent], ["Your account request"])

    def test_admin_created_accounts_require_an_email_and_get_a_welcome_email(self):
        with self.assertRaises(self.HTTPException) as context:
            self.web_app.admin_create_user(self.web_app.AdminUserCreateRequest(username="family", password="secret"), self._request(), self.admin)
        self.assertEqual(context.exception.status_code, 400)

        self.web_app.admin_create_user(
            self.web_app.AdminUserCreateRequest(username="family", email="family@example.com", password="Temp-1234", must_change_password=True),
            self._request(),
            self.admin,
        )
        self.assertEqual(self.web_app._fetch_user_by_username("family")["email"], "family@example.com")
        self.assertEqual(self.sent[-1]["subject"], "Your PhotoMigrator account")
        self.assertIn("Temp-1234", self.sent[-1]["html"])

        with self.assertRaises(self.HTTPException) as context:
            self.web_app.admin_create_user(
                self.web_app.AdminUserCreateRequest(username="other", email="Family@Example.com", password="secret"),
                self._request(),
                self.admin,
            )
        self.assertEqual(context.exception.status_code, 409)

    def test_mail_settings_keep_the_password_encrypted_and_override_the_environment(self):
        os.environ["SMTP_HOST"] = "env.example.com"
        self.assertEqual(self.web_app.mailer.settings()["host"], "env.example.com")
        self.web_app.admin_save_mail_settings(
            self.web_app.MailSettingsRequest(
                host="smtp.example.com", port=587, security="starttls", username="mailer", password="s3cret", from_address="PM@Example.com"
            ),
            self.admin,
        )
        settings = self.web_app.mailer.settings()
        self.assertEqual((settings["host"], settings["port"], settings["security"]), ("smtp.example.com", 587, "starttls"))
        self.assertEqual((settings["password"], settings["from_address"]), ("s3cret", "pm@example.com"))
        stored = json.dumps(self.web_app._get_web_setting(self.web_app.WEB_MAIL_SETTINGS_KEY))
        self.assertNotIn("s3cret", stored)

        public = self.web_app.admin_save_mail_settings(
            self.web_app.MailSettingsRequest(host="smtp.example.com", port=587, security="starttls", username="mailer", from_address="pm@example.com"),
            self.admin,
        )
        self.assertTrue(public["has_password"])
        self.assertNotIn("password", public)
        self.assertEqual(self.web_app.mailer.settings()["password"], "s3cret")

    def test_finished_job_emails_its_owner_with_status_and_log_tail(self):
        started = datetime.now(timezone.utc) - timedelta(minutes=2, seconds=5)
        job = SimpleNamespace(
            notify_email_to="owner@example.com",
            notify_username="admin",
            notify_base_url="https://photos.example.com",
            status="success",
            return_code=0,
            output=deque(self.web_app.OutputLine(text=f"line {index}\n") for index in range(40)),
            tab="immich_photos",
            selected_action_dest="upload-albums",
            started_at=started.isoformat(),
            finished_at=(started + timedelta(minutes=2, seconds=5)).isoformat(),
        )

        self.web_app._send_job_finished_email(job)

        self.assertEqual(len(self.sent), 1)
        mail = self.sent[0]
        self.assertEqual(mail["to"], ["owner@example.com"])
        self.assertEqual(mail["subject"], "Immich Photos · Upload Albums finished")
        self.assertIn("line 39", mail["html"])
        self.assertIn("line 20", mail["html"])
        self.assertNotIn("line 19", mail["html"])
        self.assertIn("0:02:05", mail["html"])
        self.assertIn("https://photos.example.com/output", mail["html"])

        job.notify_email_to = ""
        self.web_app._send_job_finished_email(job)
        self.assertEqual(len(self.sent), 1)


class TestWebInterfaceLanguages(unittest.TestCase):
    """Language of the pages and emails (same setup as the account tests)."""

    setUp = TestWebInterfaceAccountsAndEmail.setUp
    tearDown = TestWebInterfaceAccountsAndEmail.tearDown
    _record_mail = TestWebInterfaceAccountsAndEmail._record_mail
    _set_email = TestWebInterfaceAccountsAndEmail._set_email
    _request = TestWebInterfaceAccountsAndEmail._request
    _request_account = TestWebInterfaceAccountsAndEmail._request_account

    def test_account_requests_and_email_groups_follow_the_language(self):
        self._request_account(username="maria", email="maria@example.com", ip="203.0.113.50")
        conn = self.web_app._db_connect()
        try:
            conn.execute("UPDATE users SET lang = 'es' WHERE username = 'maria'")
            conn.commit()
        finally:
            conn.close()
        groups = self.web_app._group_recipients_by_lang(["MARIA@example.com", "owner@example.com", "nobody@example.com"])
        self.assertEqual(groups, {"es": ["MARIA@example.com"], "en": ["owner@example.com", "nobody@example.com"]})

    def test_language_endpoints(self):
        response = self.Response()
        self.assertEqual(self.web_app.set_ui_language(self.web_app.LanguageRequest(lang="de-DE"), self._request(), response), {"lang": "de"})
        self.assertIn("pm_lang=de", response.headers.get("set-cookie", ""))
        with self.assertRaises(self.HTTPException):
            self.web_app.set_ui_language(self.web_app.LanguageRequest(lang="xx"), self._request(), self.Response())
        script = self.web_app.get_i18n_catalog("es.js").body.decode("utf-8")
        self.assertTrue(script.startswith("window.PM_I18N = {"))
        head = str(self.web_app._i18n_head(self._request()))
        self.assertIn('window.PM_LANG = "en"', head)
        self.assertIn("/lang/i18n.js", head)



class TestMailer(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SRC_ROOT))
        from web_interface import mailer
        self.mailer = mailer
        self.env_backup = {key: os.environ.get(key) for key in SMTP_ENV_KEYS}
        for key in SMTP_ENV_KEYS:
            os.environ.pop(key, None)
        self.loader_backup = mailer._stored_settings_loader
        mailer.set_stored_settings_loader(lambda: {})

    def tearDown(self):
        self.mailer.set_stored_settings_loader(self.loader_backup)
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_send_later_does_nothing_without_configuration(self):
        self.assertFalse(self.mailer.is_configured())
        self.assertFalse(self.mailer.send_later(["someone@example.com"], "Subject", "<p>Body</p>"))

    def test_build_creates_html_and_text_alternatives(self):
        os.environ["SMTP_HOST"] = "smtp.example.com"
        os.environ["SMTP_FROM"] = "photomigrator@example.com"
        settings = self.mailer.settings()
        self.assertTrue(settings["configured"])
        self.assertEqual((settings["security"], settings["port"]), ("ssl", 465))
        html_body = self.mailer.page("Title", ["Hello &amp; welcome"], link=("Open", "https://photos.example.com/login"), preformatted="<log>")
        message = self.mailer.build(settings, ["user@example.com"], "Subject", html_body)
        self.assertEqual(message["Subject"], "PhotoMigrator - Subject")
        self.assertIn("PhotoMigrator <photomigrator@example.com>", message["From"])
        text = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("Hello & welcome", text)
        self.assertIn("Open: https://photos.example.com/login", text)
        self.assertIn("&lt;log&gt;", message.get_body(preferencelist=("html",)).get_content())


if __name__ == "__main__":
    unittest.main()
