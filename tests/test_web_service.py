import hashlib
import hmac
import importlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

ENV_KEYS = [
    "PHOTOMIGRATOR_WEB_DB_PATH", "PHOTOMIGRATOR_WEB_USER_ROOT_DATA", "PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1",
    "PHOTOMIGRATOR_CONFIG_PATH", "PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH", "PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR",
    "PHOTOMIGRATOR_STATE_PATH", "PHOTOMIGRATOR_WEB_PUBLIC_URL", "PHOTOMIGRATOR_STRIPE_SECRET_KEY",
    "PHOTOMIGRATOR_STRIPE_WEBHOOK_SECRET", "PHOTOMIGRATOR_SERVICE_ENABLED",
]
IMMICH = {"URL": "https://immich.example.com", "API_KEY_USER": "key"}


class TestCloudService(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
        except (ModuleNotFoundError, RuntimeError) as exc:
            self.skipTest(f"fastapi test client is not available: {exc}")
        self.TestClient = TestClient
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.env_backup = {key: os.environ.get(key) for key in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        os.environ.update({
            "PHOTOMIGRATOR_WEB_DB_PATH": str(base / "web.db"),
            "PHOTOMIGRATOR_WEB_USER_ROOT_DATA": str(base / "data"),
            "PHOTOMIGRATOR_WEB_USER_ROOT_VOLUME1": str(base / "volumes"),
            "PHOTOMIGRATOR_CONFIG_PATH": str(base / "Config.ini"),
            "PHOTOMIGRATOR_WEB_CONFIG_TEMPLATE_PATH": str(PROJECT_ROOT / "tests" / "test_data" / "config_test.ini"),
            "PHOTOMIGRATOR_WEB_CONFIG_CACHE_DIR": str(base / "generated"),
            "PHOTOMIGRATOR_STATE_PATH": str(base / "state.json"),
            "PHOTOMIGRATOR_WEB_PUBLIC_URL": "https://pm.example.com",
        })
        sys.modules.pop("web_interface.app", None)
        import web_interface.app as web_app
        self.app = importlib.reload(web_app)
        self.svc = self.app.cloud_service
        self.app.PARSER_SCHEMA = self.app._load_parser_schema()
        self.app.CONFIG_TEMPLATE_CONTENT = self.app._load_default_config_template()
        self.app.CONFIG_FORM_SCHEMA = self.app._extend_form_schema_with_web_interface_theme(
            self.app._parse_template_to_form_schema(self.app.CONFIG_TEMPLATE_CONTENT))
        self.app._init_web_db(self.app.CONFIG_FORM_SCHEMA)
        self.work = base / "data" / ".service-work"
        work_patch = patch.object(self.svc, "DEFAULT_WORK_DIR", self.work)
        work_patch.start()
        self.addCleanup(work_patch.stop)
        self.mails = []
        mail_patch = patch.object(self.svc.mailer, "send_later", side_effect=lambda *a, **k: self.mails.append(a[1]) or True)
        mail_patch.start()
        self.addCleanup(mail_patch.stop)
        self.admin = self.app._fetch_user_by_username("admin")
        conn = self.app._db_connect()
        now = self.app._utc_now_iso()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, is_active, created_at, updated_at, email) VALUES (?, ?, 'user', 1, ?, ?, ?)",
            ("alice", self.app._pbkdf2_hash_password("alice-pass-123"), now, now, "alice@example.com"),
        )
        conn.commit()
        conn.close()
        self.alice = self.app._fetch_user_by_username("alice")
        self.client = self.TestClient(self.app.app)

    def tearDown(self):
        self.client.close()
        sys.modules.pop("web_interface.app", None)
        for key, value in self.env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    # --- helpers ------------------------------------------------------------------------------------------------
    def _enable(self, **extra):
        values = dict(self.svc.DEFAULT_SETTINGS)
        values.update({"enabled": True, **extra})
        self.app._set_web_setting(self.svc.SETTINGS_KEY, values)

    def _enable_billing(self):
        self._enable(stripe_secret_key_encrypted=self.app._encrypt_value("rk_test_abc"),
                     stripe_webhook_secret_encrypted=self.app._encrypt_value("whsec_test"))

    def _login(self, username, password):
        response = self.client.post("/api/auth/login", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)

    def _create(self, kind="takeout_to_cloud", **extra):
        body = {"kind": kind, "takeout_type": "google", "input_mode": "upload", "target_service": "immich",
                "target": {"mode": "custom", "values": IMMICH}, "accept_terms": True}
        body.update(extra)
        response = self.client.post("/api/service/tasks", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["task"]

    @staticmethod
    def _zip(files):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    def _upload(self, task_id, name, data):
        started = self.client.post(f"/api/service/tasks/{task_id}/uploads", json={"name": name, "size": len(data)}).json()["upload"]
        half = len(data) // 2
        first = self.client.put(f"/api/service/tasks/{task_id}/uploads/{started['id']}?offset=0", content=data[:half])
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.put(f"/api/service/tasks/{task_id}/uploads/{started['id']}?offset={half}", content=data[half:])
        self.assertEqual(second.status_code, 200, second.text)
        return second.json()["upload"]

    # --- tests --------------------------------------------------------------------------------------------------
    def test_price_has_a_minimum_and_a_price_per_gb(self):
        settings = dict(self.svc.DEFAULT_SETTINGS)
        self.assertEqual(self.svc.compute_price_cents(50 * 1000 ** 3, settings), 500)
        self.assertEqual(self.svc.compute_price_cents(100 * 1000 ** 3, settings), 500)
        self.assertEqual(self.svc.compute_price_cents(200 * 1000 ** 3, settings), 1000)
        self.assertEqual(self.svc.compute_price_cents(1000 ** 4, settings), 5000)

    def test_billing_needs_stripe_and_never_applies_to_admins(self):
        self._enable()
        self.assertFalse(self.svc.billing_active())
        self._enable_billing()
        self.assertTrue(self.svc.billing_applies(self.alice))
        self.assertFalse(self.svc.billing_applies(self.admin))

    def test_service_disabled_by_default(self):
        self._login("alice", "alice-pass-123")
        response = self.client.post("/api/service/tasks", json={"kind": "process_takeout", "accept_terms": True})
        self.assertEqual(response.status_code, 404)

    def test_terms_must_be_accepted(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        response = self.client.post("/api/service/tasks", json={"kind": "process_takeout", "takeout_type": "google"})
        self.assertEqual(response.status_code, 400)

    def test_credentials_are_encrypted_in_the_task_folder_and_deleted_with_it(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create()
        folder = self.work / task["id"]
        stored = (folder / ".secrets" / "credentials.enc").read_bytes()
        self.assertNotIn(b"immich.example.com", stored)
        self.assertEqual(self.svc.load_secrets(task["id"])["target"]["URL"], IMMICH["URL"])
        conn = self.app._db_connect()
        dump = "\n".join(conn.iterdump())
        conn.close()
        self.assertNotIn("immich.example.com", dump)
        self.client.post(f"/api/service/tasks/{task['id']}/cancel")
        self.assertFalse(folder.exists())
        events = [event["event"] for event in self.svc.task_events(task["id"])]
        self.assertIn("data_deleted", events)

    def test_resumable_upload_and_quote_for_free_task(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create()
        data = self._zip({"Takeout/Google Photos/Photos from 2024/a.jpg": os.urandom(2048),
                          "Takeout/Google Photos/Photos from 2024/a.jpg.json": "{}"})
        upload = self._upload(task["id"], "takeout-001.zip", data)
        self.assertTrue(upload["complete"])
        self.assertEqual((self.work / task["id"] / "input" / "takeout-001.zip").read_bytes(), data)
        wrong = self.client.put(f"/api/service/tasks/{task['id']}/uploads/{upload['id']}?offset=5", content=b"x")
        self.assertEqual(wrong.status_code, 200)  # already complete: ignored
        with patch.object(self.svc.probes, "check_target", return_value={"ok": True}):
            self.svc.analyze(task["id"])
        quoted = self.svc.get_task(task["id"])
        self.assertEqual(quoted["status"], "quoted")
        self.assertEqual(quoted["media_count"], 1)
        self.assertEqual(quoted["price_cents"], 500)
        self.assertEqual(quoted["billable"], 0)
        self.assertIn("Your PhotoMigrator quote", self.mails)
        accepted = self.client.post(f"/api/service/tasks/{task['id']}/accept").json()
        self.assertEqual(accepted["task"]["status"], "queued")

    def test_only_archives_can_be_uploaded(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create()
        response = self.client.post(f"/api/service/tasks/{task['id']}/uploads", json={"name": "photo.jpg", "size": 10})
        self.assertEqual(response.status_code, 400)

    def test_admin_is_emailed_when_a_task_is_created(self):
        self._enable(contact_email="ops@example.com")
        self._login("alice", "alice-pass-123")
        with patch.object(self.svc.mailer, "send_later") as send:
            task = self._create()
        recipients, subject, body = send.call_args_list[-1].args[:3]
        self.assertEqual(recipients, ["ops@example.com"])
        self.assertTrue(subject.startswith("New cloud service task"))
        self.assertIn(f"tab=service&amp;task={task['id']}", body.replace("&amp;", "&").replace("&", "&amp;"))
        self.assertIn("alice", body)

    def test_admin_link_signs_in_first_and_comes_back(self):
        link = "/admin?tab=service&task=abc123"
        response = self.client.get(link, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "/login?next=%2Fadmin%3Ftab%3Dservice%26task%3Dabc123")
        self.assertEqual(self.app._safe_next_path("https://evil.example.com"), "")
        self.assertEqual(self.app._safe_next_path("//evil.example.com"), "")
        self.assertEqual(self.app._safe_next_path(link), link)
        self._login("alice", "alice-pass-123")
        self.assertEqual(self.client.get("/admin", follow_redirects=False).status_code, 403)
        self.assertEqual(self.client.get(f"/login?next=%2Fservice", follow_redirects=False).headers["location"], "/service")

    def test_documentation_is_public_except_the_user_config(self):
        for path in ("/docs/view/help", "/docs/view/readme", "/docs/view/changelog", "/docs/view/help/13-cloud-service.md"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        page = self.client.get("/docs/view/help", headers={"accept-language": "es-ES"}).text
        self.assertIn('<html lang="en">', page)  # the browser offers to translate it
        self.assertNotIn("/lang/i18n.js", page)
        help_doc = self.client.get("/api/docs/help").json()
        self.assertIn("PhotoMigrator", help_doc["content"])
        self.assertEqual(help_doc["path"], "help.md")
        self.assertTrue(self.client.get("/api/docs/help-index").json()["documents"])
        self.assertEqual(self.client.get("/api/docs/help/13-cloud-service.md").status_code, 200)
        self.assertEqual(self.client.get("/api/docs/config").status_code, 401)
        config_view = self.client.get("/docs/view/config", follow_redirects=False)
        self.assertEqual(config_view.status_code, 302)
        self.assertTrue(config_view.headers["location"].startswith("/login?next="))
        self._login("alice", "alice-pass-123")
        self.assertEqual(self.client.get("/api/docs/config").status_code, 200)

    def test_website_is_english_by_default_and_follows_the_chosen_language(self):
        page = self.client.get("/", headers={"accept-language": "es-ES,es;q=0.9"}).text
        self.assertIn('<html lang="en">', page)
        self.assertIn('window.PM_LANG = "en"', page)
        self.assertIn('class="lang"', page)
        self.client.post("/api/lang", json={"lang": "es"})
        page = self.client.get("/").text
        self.assertIn('<html lang="es">', page)
        self.assertIn("/api/i18n/es.js", page)
        catalog = self.client.get("/api/i18n/es.js").text
        self.assertIn("Read the documentation", catalog)

    def test_sign_in_keeps_the_language_of_accounts_without_one(self):
        self.client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass-123"},
                         headers={"accept-language": "es-ES,es;q=0.9"})
        self.assertEqual(self.app._fetch_user_by_username("alice")["lang"], "es")
        self.client.cookies.clear()
        self.client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass-123"},
                         headers={"accept-language": "fr-FR"})
        self.assertEqual(self.app._fetch_user_by_username("alice")["lang"], "es")

    def test_quote_checks_the_uploaded_zip_files(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        inner = self._zip({"Takeout/Google Photos/Album/b.heic": b"x" * 100, "Takeout/Google Photos/Album/c.mp4": b"y" * 100})
        cases = [
            ("nested.zip", self._zip({"Takeout-short/Takeout-short.zip": inner}), "quoted", 2),
            ("no-media.zip", self._zip({"Takeout/archive_browser.html": "<html></html>", "Takeout/a.json": "{}"}), "draft", 0),
            ("damaged.zip", b"PK" + os.urandom(500), "draft", 0),
        ]
        for name, data, expected, media in cases:
            with self.subTest(name=name):
                task = self._create(kind="process_takeout", target_service="", target=None)
                self._upload(task["id"], name, data)
                self.svc.analyze(task["id"])
                checked = self.svc.get_task(task["id"])
                self.assertEqual(checked["status"], expected)
                self.assertEqual(checked["media_count"], media)
                if expected == "draft":
                    self.assertTrue(checked["error"])

    def test_tgz_takeouts_are_not_accepted(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create()
        response = self.client.post(f"/api/service/tasks/{task['id']}/uploads", json={"name": "takeout-001.tgz", "size": 10})
        self.assertEqual(response.status_code, 400)

    def test_run_without_media_fails_and_is_not_charged(self):
        self._enable_billing()
        self._login("alice", "alice-pass-123")
        task = self._create(kind="process_takeout", target_service="", target=None)
        self.svc.update_task(task["id"], status="running", job_id="job-9", size_bytes=10, price_cents=500)
        processed = self.work / task["id"] / "input_processed_20261125"
        processed.mkdir(parents=True)
        (processed / "takeout_people_metadata.json").write_text("{}")
        logs = self.work / task["id"] / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "run.log").write_text("Discovered 0 media files (0 from year folders, 0 from albums)")
        self.svc.DEPS.job_state = lambda job_id: {"status": "success", "return_code": 0}
        with patch.object(self.svc.stripe, "refund_payment") as refund:
            self.svc._finish_running(self.svc.get_task(task["id"]))
        refund.assert_not_called()
        failed = self.svc.get_task(task["id"])
        self.assertEqual(failed["status"], "failed")
        self.assertIn("no photos or videos", failed["error"])
        self.assertFalse(failed["paid_at"])
        self.assertIn("Your task could not be completed", self.mails)
        self.assertFalse((self.work / task["id"]).exists())

    def test_task_too_large_is_rejected_and_deleted(self):
        self._enable(max_task_bytes=1000 ** 3)
        self._login("alice", "alice-pass-123")
        task = self._create(kind="cloud_to_cloud", source_service="nextcloud",
                            source={"mode": "custom", "values": {"URL": "https://nc.example.com", "USERNAME": "a", "PASSWORD": "b"}})
        with patch.object(self.svc.probes, "check_source", return_value=900 * 1000 ** 3):
            self.svc.analyze(task["id"])
        rejected = self.svc.get_task(task["id"])
        self.assertEqual(rejected["status"], "rejected")
        self.assertFalse((self.work / task["id"]).exists())

    def test_paid_migration_flow_with_webhook_and_refund_on_failure(self):
        self._enable_billing()
        self._login("alice", "alice-pass-123")
        task = self._create(kind="cloud_to_cloud", source_service="synology",
                            source={"mode": "custom", "values": {"URL": "https://syno.example.com", "USERNAME": "a", "PASSWORD": "b"}})
        with patch.object(self.svc.probes, "check_source", return_value=300 * 1000 ** 3), \
                patch.object(self.svc.probes, "check_target", return_value={"ok": True}):
            self.svc.analyze(task["id"])
        self.assertEqual(self.svc.get_task(task["id"])["price_cents"], 1500)
        with patch.object(self.svc.stripe, "create_checkout_session", return_value={"id": "cs_1", "url": "https://checkout.stripe.com/c/1"}) as checkout:
            response = self.client.post(f"/api/service/tasks/{task['id']}/accept").json()
        self.assertEqual(response["checkout_url"], "https://checkout.stripe.com/c/1")
        self.assertEqual(checkout.call_args.kwargs["amount_cents"], 1500)
        event = {"type": "checkout.session.completed", "data": {"object": {
            "id": "cs_1", "payment_status": "paid", "amount_total": 1500, "payment_intent": "pi_1",
            "metadata": {"service": "photomigrator", "task_id": task["id"], "purpose": "migration"}}}}
        payload = json.dumps(event).encode()
        stamp = str(int(time.time()))
        signature = hmac.new(b"whsec_test", f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
        bad = self.client.post("/api/service/stripe/webhook", content=payload, headers={"stripe-signature": f"t={stamp},v1=00"})
        self.assertEqual(bad.status_code, 400)
        good = self.client.post("/api/service/stripe/webhook", content=payload, headers={"stripe-signature": f"t={stamp},v1={signature}"})
        self.assertEqual(good.status_code, 200)
        paid = self.svc.get_task(task["id"])
        self.assertEqual(paid["status"], "queued")
        self.assertEqual(paid["amount_paid_cents"], 1500)
        self.svc.update_task(task["id"], status="running", job_id="job-1")
        with patch.object(self.svc.stripe, "refund_payment", return_value={"id": "re_1"}) as refund:
            self.svc.DEPS.job_state = lambda job_id: {"status": "failed", "return_code": 1}
            self.svc._finish_running(self.svc.get_task(task["id"]))
        refund.assert_called_once()
        failed = self.svc.get_task(task["id"])
        self.assertEqual(failed["status"], "failed")
        self.assertTrue(failed["refunded_at"])
        self.assertIn("Your task could not be completed", self.mails)

    def test_cancel_before_start_refunds_but_not_while_running(self):
        self._enable_billing()
        self._login("alice", "alice-pass-123")
        first = self._create()
        self.svc.update_task(first["id"], status="queued", payment_intent_id="pi_a", paid_at="x", amount_paid_cents=500)
        second = self._create()
        self.svc.update_task(second["id"], status="running", job_id="job-2", payment_intent_id="pi_b", paid_at="x", amount_paid_cents=500)
        self.svc.DEPS.stop_job = lambda job_id: None
        with patch.object(self.svc.stripe, "refund_payment", return_value={"id": "re"}) as refund:
            self.client.post(f"/api/service/tasks/{first['id']}/cancel")
            self.client.post(f"/api/service/tasks/{second['id']}/cancel")
        self.assertEqual(refund.call_count, 1)
        self.assertTrue(self.svc.get_task(first["id"])["refunded_at"])
        self.assertFalse(self.svc.get_task(second["id"])["refunded_at"])

    def test_processed_takeout_is_paid_before_download_and_downloads_resume(self):
        self._enable_billing()
        self._login("alice", "alice-pass-123")
        task = self._create(kind="process_takeout", target_service="", target=None)
        self.svc.update_task(task["id"], status="packaging", size_bytes=10, price_cents=500)
        processed = self.work / task["id"] / "input_processed_20261125"
        (processed / "2024").mkdir(parents=True)
        (processed / "2024" / "a.jpg").write_bytes(b"A" * 1000)
        (processed / "Albums" / "Trip").mkdir(parents=True)
        (processed / "Albums" / "Trip" / "a.jpg").symlink_to(Path("..") / ".." / "2024" / "a.jpg")
        (processed / "Albums" / "Trip" / "gone.jpg").symlink_to(Path("..") / ".." / "2024" / "missing.jpg")
        (self.work / task["id"] / "input" / "takeout.zip").write_bytes(b"zip")
        self.svc.package_result(task["id"])
        ready = self.svc.get_task(task["id"])
        self.assertEqual(ready["status"], "awaiting_download_payment")
        part_file = next((self.work / task["id"] / "downloads").glob("*.zip"))
        with zipfile.ZipFile(part_file) as archive:
            self.assertEqual(sorted(archive.namelist()), ["2024/a.jpg", "Albums/Trip/a.jpg"])
            self.assertEqual(archive.read("Albums/Trip/a.jpg"), b"A" * 1000)
        self.assertFalse((self.work / task["id"] / "input").exists())
        self.assertFalse(processed.exists())
        details = self.client.get(f"/api/service/tasks/{task['id']}").json()["task"]
        self.assertNotIn("downloads", details)
        self.svc.mark_paid(task["id"], {"id": "cs_2", "payment_status": "paid", "amount_total": 500, "payment_intent": "pi_2",
                                         "metadata": {"task_id": task["id"], "purpose": "download"}})
        details = self.client.get(f"/api/service/tasks/{task['id']}").json()["task"]
        self.assertEqual(details["status"], "ready")
        part = details["downloads"][0]
        whole = self.client.get(part["url"])
        self.assertEqual(whole.status_code, 200)
        partial = self.client.get(part["url"], headers={"Range": "bytes=10-19"})
        self.assertEqual(partial.status_code, 206)
        self.assertEqual(partial.content, whole.content[10:20])
        forged = self.client.get(part["url"].replace("token=", "token=0"))
        self.assertEqual(forged.status_code, 403)

    def test_expired_downloads_are_deleted(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create(kind="process_takeout", target_service="", target=None)
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.svc.update_task(task["id"], status="ready", download_expires_at=past)
        self.svc.worker_tick()
        self.assertEqual(self.svc.get_task(task["id"])["status"], "expired")
        self.assertFalse((self.work / task["id"]).exists())
        self.assertIn("Your task data has been deleted", self.mails)

    def test_other_users_cannot_see_a_task(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create()
        self.client.post("/api/auth/logout")
        self._login("admin", "admin123")
        self.assertEqual(self.client.get(f"/api/service/tasks/{task['id']}").status_code, 404)

    def test_work_folder_name_is_reserved(self):
        with self.assertRaises(self.app.HTTPException):
            self.app._normalize_subpath(".service-work", "x")
        with self.assertRaises(self.app.HTTPException):
            self.app._normalize_subpath("", ".service-work")

    def test_task_config_only_contains_task_accounts(self):
        self._enable()
        self._login("alice", "alice-pass-123")
        task = self._create(kind="cloud_to_cloud", source_service="immich", source={"mode": "custom", "values": IMMICH})
        path = self.svc._write_task_config(self.svc.get_task(task["id"]))
        text = path.read_text()
        self.assertIn("IMMICH_API_KEY_USER_1 = key", text)
        self.assertIn("IMMICH_API_KEY_USER_2 = key", text)
        command, tab, _ = self.svc.build_command(self.svc.get_task(task["id"]), path)
        self.assertEqual(tab, "automatic_migration")
        self.assertIn("--source=immich-1", command)
        self.assertIn("--target=immich-2", command)

    def test_stripe_signature_check(self):
        payload = b'{"type":"x"}'
        stamp = int(time.time())
        signature = hmac.new(b"whsec_x", f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
        self.assertEqual(self.svc.stripe.verify_webhook(payload, f"t={stamp},v1={signature}", "whsec_x")["type"], "x")
        with self.assertRaises(ValueError):
            self.svc.stripe.verify_webhook(payload, f"t={stamp - 1000},v1={signature}", "whsec_x")

    def test_checkout_session_is_card_only_and_tagged(self):
        with patch.object(self.svc.stripe.requests, "request") as request:
            request.return_value.status_code = 200
            request.return_value.json.return_value = {"id": "cs_1", "url": "https://checkout.stripe.com/c/1"}
            self.svc.stripe.create_checkout_session(
                "rk_test_x", task_id="t1", purpose="migration", amount_cents=500, currency="eur", description="Task",
                customer_email="", success_url="https://example.com/ok", cancel_url="https://example.com/ko")
        data = request.call_args.kwargs["data"]
        self.assertEqual(data["payment_method_types[0]"], "card")
        self.assertNotIn("payment_method_types[1]", data)
        self.assertEqual(data["metadata[service]"], "photomigrator")
        self.assertEqual(data["payment_intent_data[metadata][service]"], "photomigrator")
        self.assertEqual(data["payment_intent_data[statement_descriptor_suffix]"], "PHOTOMIGRATOR")

    def test_webhook_ignores_events_of_other_businesses(self):
        self._enable_billing()
        self._login("alice", "alice-pass-123")
        task = self._create()
        self.svc.update_task(task["id"], status="awaiting_payment", price_cents=500)
        foreign = {"type": "checkout.session.completed", "data": {"object": {
            "id": "cs_other", "payment_status": "paid", "amount_total": 500, "payment_intent": "pi_other",
            "client_reference_id": task["id"], "metadata": {"task_id": task["id"], "purpose": "migration"}}}}
        payload = json.dumps(foreign).encode()
        stamp = str(int(time.time()))
        signature = hmac.new(b"whsec_test", f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
        response = self.client.post("/api/service/stripe/webhook", content=payload, headers={"stripe-signature": f"t={stamp},v1={signature}"})
        self.assertEqual(response.status_code, 200)
        unpaid = self.svc.get_task(task["id"])
        self.assertEqual(unpaid["status"], "awaiting_payment")
        self.assertFalse(unpaid.get("amount_paid_cents"))
        self.svc.handle_webhook_event({"type": "charge.refunded", "data": {"object": {"metadata": {"task_id": task["id"]}}}})
        self.assertFalse(self.svc.get_task(task["id"])["refunded_at"])

    def test_admin_settings_keep_secrets_hidden(self):
        self._login("admin", "admin123")
        response = self.client.put("/api/admin/service/settings", json={"enabled": True, "stripe_secret_key": "rk_test_123", "stripe_webhook_secret": "whsec_1"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["has_stripe_secret_key"])
        self.assertEqual(body["stripe_mode"], "test")
        self.assertNotIn("rk_test_123", json.dumps(body))
        self.assertTrue(body["urls"]["stripe_webhook"].endswith("/api/service/stripe/webhook"))

    def test_pages_and_legal_texts(self):
        self.assertEqual(self.client.get("/terms").status_code, 200)
        privacy = self.client.get("/privacy")
        self.assertEqual(privacy.status_code, 200)
        self.assertIn("Privacy policy", privacy.text)
        self._login("alice", "alice-pass-123")
        disabled = self.client.get("/service", follow_redirects=False)
        self.assertEqual(disabled.status_code, 302)
        self._enable(operator_name="Example Photos SL", contact_email="help@example.com")
        page = self.client.get("/service")
        self.assertEqual(page.status_code, 200)
        self.assertIn("service.js", page.text)
        terms = self.client.get("/terms").text
        self.assertIn("Example Photos SL", terms)
        self.assertIn("help@example.com", terms)
        self.assertIn("5.00 €", terms)

    def test_sidebar_shows_cloud_service_only_when_enabled(self):
        self._login("alice", "alice-pass-123")
        self.assertNotIn("/service?manual_navigation=1", self.client.get("/configuration").text)
        self._enable()
        self.assertIn("/service?manual_navigation=1", self.client.get("/configuration").text)


if __name__ == "__main__":
    unittest.main()
