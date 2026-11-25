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

        self.web_app.admin_delete_user(user["id"], self._request(), self.admin)

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
            self._request(),
            self.admin,
        )
        settings = self.web_app.mailer.settings()
        self.assertEqual((settings["host"], settings["port"], settings["security"]), ("smtp.example.com", 587, "starttls"))
        self.assertEqual((settings["password"], settings["from_address"]), ("s3cret", "pm@example.com"))
        stored = json.dumps(self.web_app._get_web_setting(self.web_app.WEB_MAIL_SETTINGS_KEY))
        self.assertNotIn("s3cret", stored)

        public = self.web_app.admin_save_mail_settings(
            self.web_app.MailSettingsRequest(host="smtp.example.com", port=587, security="starttls", username="mailer", from_address="pm@example.com"),
            self._request(),
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



class TestWebInterfaceAdminPanel(unittest.TestCase):
    """Administration Panel: users edited in place, bulk changes, password reset, access log, database filters and backups."""

    setUp = TestWebInterfaceAccountsAndEmail.setUp
    tearDown = TestWebInterfaceAccountsAndEmail.tearDown
    _record_mail = TestWebInterfaceAccountsAndEmail._record_mail
    _set_email = TestWebInterfaceAccountsAndEmail._set_email
    _request = TestWebInterfaceAccountsAndEmail._request

    def _create_user(self, username, email, role="user", active=True):
        payload = self.web_app.AdminUserCreateRequest(username=username, email=email, password="long-password", role=role, is_active=active)
        return self.web_app.admin_create_user(payload, self._request(), self.admin)["user_id"]

    def _events(self, event=""):
        logs = self.web_app.admin_access_logs(limit=200, username="", event=event, days=0, current_user=self.admin)["logs"]
        return [(log["event"], log["details"]) for log in logs]

    def test_users_list_reports_last_sign_in_and_online_users(self):
        user_id = self._create_user("marta", "marta@example.com")
        login = self.web_app.api_login(self.web_app.LoginRequest(username="marta", password="long-password"), self.Response(), self._request())
        self.assertTrue(login)
        token = self.web_app._create_session_for_user(user_id)
        self.assertIsNotNone(self.web_app._user_from_session_token(token))
        users = {user["username"]: user for user in self.web_app.admin_list_users(self.admin)["users"]}
        self.assertTrue(users["marta"]["last_login_at"])
        self.assertTrue(users["marta"]["online"])
        self.assertTrue(users["admin"]["is_current_user"])

    def test_failed_sign_in_is_logged(self):
        with self.assertRaises(self.HTTPException):
            self.web_app.api_login(self.web_app.LoginRequest(username="admin", password="wrong"), self.Response(), self._request())
        self.assertIn(("sign_in_failed", "Wrong username or password"), self._events("sign_in_failed"))

    def test_password_set_by_admin_signs_the_user_out_and_is_logged(self):
        user_id = self._create_user("marta", "marta@example.com")
        token = self.web_app._create_session_for_user(user_id)
        self.web_app.admin_update_user(user_id, self.web_app.AdminUserUpdateRequest(password="another-password"), self._request(), self.admin)
        self.assertIsNone(self.web_app._user_from_session_token(token))
        self.assertIn(("user_updated", "marta · password set"), self._events("user_updated"))

    def test_reset_password_shows_a_temporary_password_without_email(self):
        user_id = self._create_user("marta", "marta@example.com")
        result = self.web_app.admin_reset_user_password(user_id, self._request(), self.admin)
        self.assertFalse(result["emailed"])
        self.assertTrue(result["temporary_password"])
        user = self.web_app._fetch_user_by_id(user_id)
        self.assertTrue(bool(user["must_change_password"]))
        self.assertTrue(self.web_app._pbkdf2_verify_password(result["temporary_password"], user["password_hash"]))

    def test_reset_password_emails_the_temporary_password_when_email_works(self):
        user_id = self._create_user("marta", "marta@example.com")
        self.sent.clear()
        with patch.object(self.web_app.mailer, "is_configured", return_value=True):
            result = self.web_app.admin_reset_user_password(user_id, self._request(), self.admin)
        self.assertEqual((result["emailed"], result["temporary_password"]), (True, ""))
        self.assertEqual(self.sent[-1]["to"], ["marta@example.com"])
        self.assertEqual(self.sent[-1]["subject"], "Your password was reset")

    def test_bulk_changes_skip_users_that_cannot_change(self):
        marta = self._create_user("marta", "marta@example.com")
        pedro = self._create_user("pedro", "pedro@example.com")
        result = self.web_app.admin_bulk_users(
            self.web_app.AdminUsersBulkRequest(user_ids=[marta, pedro, self.admin["id"]], action="deactivate"), self._request(), self.admin
        )
        self.assertEqual(sorted(result["updated"]), sorted([marta, pedro]))
        self.assertEqual([item["username"] for item in result["skipped"]], ["admin"])
        self.assertFalse(bool(self.web_app._fetch_user_by_id(marta)["is_active"]))
        result = self.web_app.admin_bulk_users(
            self.web_app.AdminUsersBulkRequest(user_ids=[marta], action="role", value="demo"), self._request(), self.admin
        )
        self.assertEqual(self.web_app._fetch_user_by_id(marta)["role"], "demo")
        with self.assertRaises(self.HTTPException):
            self.web_app.admin_bulk_users(self.web_app.AdminUsersBulkRequest(user_ids=[marta], action="explode"), self._request(), self.admin)

    def test_database_viewer_filters_and_column_values(self):
        self._create_user("marta", "marta@example.com")
        self._create_user("pedro", "pedro@example.com", role="demo")
        rows = self.web_app.admin_db_table_rows("users", limit=100, offset=0, filters=json.dumps({"role": ["demo"]}), current_user=self.admin)
        self.assertEqual([row["username"] for row in rows["rows"]], ["pedro"])
        self.assertEqual(rows["total"], 1)
        self.assertGreaterEqual(rows["total_rows"], 3)
        values = self.web_app.admin_db_column_values("users", column="role", search="", filters="", current_user=self.admin)["values"]
        self.assertIn({"value": "demo", "count": 1}, values)
        with self.assertRaises(self.HTTPException):
            self.web_app.admin_db_column_values("users", column="nope", search="", filters="", current_user=self.admin)

    def test_backups_schedule_status_restore_and_delete(self):
        backup_dir = Path(self.temp_dir.name) / "backups"
        config = self.web_app.BackupConfigRequest(
            enabled=True, backup_dir=str(backup_dir), recurrence="weekly", run_time="03:30", weekday=3, monthday=1, keep_days=14
        )
        saved = self.web_app.admin_save_backup_config(config, self.admin)["config"]
        self.assertEqual((saved["recurrence"], saved["run_time"], saved["weekday"], saved["keep_days"]), ("weekly", "03:30", 3, 14))
        next_run = datetime.fromisoformat(saved["next_run_at"])
        self.assertEqual((next_run.weekday(), next_run.hour, next_run.minute), (3, 3, 30))

        result = self.web_app.admin_run_backup_now(self._request(), self.admin)["result"]
        self.assertEqual(result["status"], "success")
        marta = self._create_user("marta", "marta@example.com")
        status = self.web_app.admin_backup_status(self.admin)
        self.assertEqual([item["origin"] for item in status["files"]], ["manual"])

        restored = self.web_app.admin_restore_backup(self.web_app.BackupFileRequest(name=status["files"][0]["name"]), self._request(), self.admin)
        self.assertIsNone(self.web_app._fetch_user_by_id(marta))
        self.assertTrue(restored["safety_backup"].startswith("web_interface_prerestore_"))

        with self.assertRaises(self.HTTPException):
            self.web_app._resolve_backup_file("../web_interface.db")
        self.web_app.admin_delete_backup(restored["safety_backup"], self._request(), self.admin)
        self.assertNotIn(restored["safety_backup"], [item["name"] for item in self.web_app.admin_backup_status(self.admin)["files"]])

        with self.assertRaises(self.HTTPException):
            self.web_app.admin_save_backup_config(self.web_app.BackupConfigRequest(enabled=True, recurrence="yearly"), self.admin)

    def test_scheduled_retention_keeps_manual_backups_and_the_newest_scheduled(self):
        backup_dir = Path(self.temp_dir.name) / "retention"
        backup_dir.mkdir()
        old_time = (datetime.now() - timedelta(days=40)).timestamp()
        for name in ("web_interface_20250101_020000.db", "web_interface_20250102_020000.db", "web_interface_manual_20250101_120000.db"):
            path = backup_dir / name
            path.write_bytes(b"x")
            os.utime(path, (old_time, old_time))
        newest = backup_dir / "web_interface_20250103_020000.db"
        newest.write_bytes(b"x")
        os.utime(newest, (old_time + 60, old_time + 60))
        self.web_app._prune_scheduled_backups(backup_dir, keep_days=30)
        self.assertEqual(
            sorted(path.name for path in backup_dir.iterdir()),
            ["web_interface_20250103_020000.db", "web_interface_manual_20250101_120000.db"],
        )

    def test_next_scheduled_backup_for_every_recurrence(self):
        base = datetime(2026, 11, 25, 10, 15).astimezone()
        compute = self.web_app._compute_next_scheduled_backup
        self.assertEqual(compute({"recurrence": "hourly", "run_time": "00:30"}, base).strftime("%d %H:%M"), "25 10:30")
        self.assertEqual(compute({"recurrence": "every_4_hours", "run_time": "02:00"}, base).strftime("%d %H:%M"), "25 14:00")
        self.assertEqual(compute({"recurrence": "daily", "run_time": "02:00"}, base).strftime("%d %H:%M"), "26 02:00")
        self.assertEqual(compute({"recurrence": "monthly", "run_time": "02:00", "monthday": 1}, base).strftime("%m-%d %H:%M"), "12-01 02:00")


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
