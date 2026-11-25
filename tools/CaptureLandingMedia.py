#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Capture the screenshots used by the marketing landing page (landing/index.html).

The script drives a running PhotoMigrator Web Interface with Playwright and renders the
Terminal TUI with Textual, then writes WebP images to landing/media/.

    1. Start a local Web Interface with test data (for example `python src/PhotoMigrator_Web.py`).
    2. Run: python tools/CaptureLandingMedia.py --url http://127.0.0.1:6078 --user admin --password <test password>

Requirements (not project dependencies): `pip install playwright pillow textual` and
`python -m playwright install chromium`. Only use a local test instance: the script saves
sample credentials in the Service credentials of the signed-in user so the screenshots
show configured accounts, and runs a list-only Find Duplicates job on a small sample folder
created inside that user's first data root (its CSV report and log are written where that
instance writes job outputs). Local paths shown in the Activity log are replaced by the
Docker paths of the Web Interface before the screenshot is taken.

The Web Interface screenshots are taken once per language of the Web Interface (lang/): English ones are
`<name>.webp` and the others `<name>-<lang>.webp`. The website shows the ones of the language chosen with its
picker (English when a language has none). `--langs es,fr` captures only some languages. The language of the
signed-in test user is restored at the end. The Terminal TUI is not translated, so it has a single image.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT / "landing" / "media"
sys.path.insert(0, str(ROOT))
from lang import i18n  # noqa: E402

SAMPLE_CREDENTIALS = {
    "Synology Photos": {"SYNOLOGY_URL": "http://192.168.1.11:5000", "SYNOLOGY_USERNAME_1": "family", "SYNOLOGY_PASSWORD_1": "sample-password"},
    "Immich Photos": {"IMMICH_URL": "http://192.168.1.11:2283", "IMMICH_API_KEY_USER_1": "sample-api-key", "IMMICH_USERNAME_1": "family"},
}


def save_webp(png_bytes: bytes, name: str, *, width: int | None = None) -> Path:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if width and image.width > width:
        height = round(image.height * width / image.width)
        image = image.resize((width, height), Image.LANCZOS)
    target = MEDIA_DIR / f"{name}.webp"
    image.save(target, "WEBP", quality=86, method=6)
    print(f"  - {target.relative_to(ROOT)} ({image.width}x{image.height})")
    return target


def wait_ready(page: Page) -> None:
    page.wait_for_function("typeof schema !== 'undefined' && schema !== null")
    page.wait_for_timeout(700)


def login(page: Page, base_url: str, user: str, password: str) -> None:
    page.goto(f"{base_url}/login")
    page.fill("#username", user)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_url("**/features**")
    wait_ready(page)


def store_sample_credentials(page: Page) -> None:
    page.evaluate(
        """async (samples) => {
            const response = await fetch('/api/config/form');
            const data = await response.json();
            const values = {};
            (data.sections || []).forEach((section) => {
                values[section.name] = {};
                (section.fields || []).forEach((field) => { values[section.name][field.key] = String(field.value || ''); });
            });
            Object.entries(samples).forEach(([section, entries]) => {
                values[section] = Object.assign(values[section] || {}, entries);
            });
            await fetch('/api/config/form', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({values})});
        }""",
        SAMPLE_CREDENTIALS,
    )


def open_features(page: Page, base_url: str, module: str, action: str | None = None) -> None:
    page.goto(f"{base_url}/features?manual_navigation=1")
    wait_ready(page)
    page.evaluate("(m) => openModuleFromNavigation(m)", module)
    page.wait_for_timeout(400)
    if action:
        page.click(f'[data-action-dest="{action}"]')
        page.wait_for_timeout(400)
    page.evaluate("window.scrollTo(0, 0)")


def set_language(page: Page, lang: str) -> None:
    page.evaluate("async (code) => { await fetch('/api/lang', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lang: code})}); }", lang)


def capture_web(base_url: str, user: str, password: str, langs: list[str]) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        desktop = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = desktop.new_page()
        login(page, base_url, user, password)
        store_sample_credentials(page)
        original_lang = page.evaluate("window.PM_LANG || 'en'")
        try:
            for lang in langs:
                print(f"Language: {lang}")
                set_language(page, lang)
                for attempt in range(1, 4):  # a busy local instance can be slow to load a page
                    try:
                        # The phone screenshot signs in again, which can end the desktop session.
                        if lang != langs[0] or attempt > 1:
                            login(page, base_url, user, password)
                            set_language(page, lang)
                        capture_web_screens(browser, page, base_url, user, password, "" if lang == i18n.DEFAULT else f"-{lang}")
                        break
                    except PlaywrightTimeoutError:
                        if attempt == 3:
                            raise
                        print(f"  timeout on {page.url}, retrying {lang} ({attempt}/3)")
        finally:
            set_language(page, original_lang)
        browser.close()


def capture_web_screens(browser, page: Page, base_url: str, user: str, password: str, suffix: str) -> None:
    """The Web Interface screenshots in the current language of the signed-in user, saved as <name><suffix>.webp."""
    page.goto(f"{base_url}/features?view=home&manual_navigation=1")
    wait_ready(page)
    save_webp(page.screenshot(), "web-home" + suffix, width=2400)

    open_features(page, base_url, "automatic_migration")
    page.evaluate("""() => {
        uiState.migration_endpoints = {source: {kind: 'synology', account: '1', path: ''}, target: {kind: 'immich', account: '1', path: ''}};
        renderAll();
    }""")
    page.wait_for_timeout(500)
    save_webp(page.screenshot(), "web-migration" + suffix, width=2400)

    open_features(page, base_url, "immich_photos", "remove-duplicates-assets")
    save_webp(page.screenshot(), "web-immich" + suffix, width=2400)

    open_features(page, base_url, "google_takeout")
    save_webp(page.screenshot(), "web-takeout" + suffix, width=2400)

    page.evaluate("() => { document.body.setAttribute('data-theme', 'dark'); }")
    open_features(page, base_url, "immich_photos", "upload-albums")
    page.evaluate("() => { document.body.setAttribute('data-theme', 'dark'); }")
    page.wait_for_timeout(300)
    save_webp(page.screenshot(), "web-dark" + suffix, width=2400)

    page.goto(f"{base_url}/configuration?manual_navigation=1")
    wait_ready(page)
    page.evaluate("() => { uiState.config_active_section = 'Immich Photos'; activeConfigSection = 'Immich Photos'; renderConfigSectionTabs(); renderActiveConfigSection(); }")
    page.wait_for_timeout(400)
    save_webp(page.screenshot(), "web-settings" + suffix, width=2400)

    # A short real job so that Activity shows a finished run with its log. The sample folders
    # live inside the first data root of the signed-in test user, as the Web Interface requires.
    scratch_folder = Path(page.evaluate("allowedRoots[0]")) / "landing-sample"
    first = scratch_folder / "a"
    second = scratch_folder / "b"
    first.mkdir(parents=True, exist_ok=True)
    second.mkdir(parents=True, exist_ok=True)
    (first / "IMG_0001.jpg").write_text("sample", encoding="utf-8")
    (second / "IMG_0001.jpg").write_text("sample", encoding="utf-8")
    (second / "IMG_0002.jpg").write_text("other", encoding="utf-8")
    open_features(page, base_url, "standalone_features", "find-duplicates")
    page.fill('input[data-folder-multi="1"]', f"{first}, {second}")
    page.wait_for_timeout(400)
    page.click("#run-btn")
    page.wait_for_url("**/output**")
    page.wait_for_selector("#job-input-yes:not([disabled])", timeout=30000)
    page.click("#job-input-yes")
    # Wait for the job through the API (the status text is translated): a running job would redirect the next
    # screenshots of the following language to Activity.
    deadline = time.time() + 60
    while time.time() < deadline and page.evaluate("fetch('/api/jobs/_active').then((r) => r.json()).then((d) => d.job_id)"):
        page.wait_for_timeout(500)
    page.wait_for_timeout(800)
    # Local machine paths must not be published: show them as the Docker paths of the Web Interface.
    replacements = [[str(scratch_folder.parent), "/app/data"], [str(ROOT), "/app"]]
    page.evaluate(
        """(pairs) => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                let text = node.nodeValue;
                pairs.forEach(([from, to]) => { text = text.split(from).join(to); });
                if (text !== node.nodeValue) node.nodeValue = text;
            }
        }""",
        replacements,
    )
    save_webp(page.screenshot(), "web-activity" + suffix, width=2400)

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    phone = mobile.new_page()
    login(phone, base_url, user, password)
    phone.goto(f"{base_url}/features?view=home&manual_navigation=1")
    wait_ready(phone)
    save_webp(phone.screenshot(), "web-phone" + suffix, width=1170)
    mobile.close()


def capture_tui() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from UI.cli_tui import PhotoMigratorTUI

    async def render_svg() -> str:
        app = PhotoMigratorTUI(project_root=ROOT, cli_entrypoint=ROOT / "src" / "PhotoMigrator.py", initial_values={})
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(1.0)
            return app.export_screenshot()

    svg = asyncio.run(render_svg())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page.set_content(f"<html><body style='margin:0;background:#0b1120'>{svg}</body></html>")
        page.wait_for_timeout(300)
        element = page.query_selector("svg")
        png = element.screenshot() if element else page.screenshot()
        browser.close()
    save_webp(png, "tui", width=2400)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the landing page screenshots.")
    parser.add_argument("--url", default="http://127.0.0.1:6078", help="Base URL of a local test Web Interface")
    parser.add_argument("--user", default="admin", help="Test user of that instance")
    parser.add_argument("--password", required=True, help="Password of the test user")
    parser.add_argument("--only", choices=["web", "tui"], help="Capture only one group")
    parser.add_argument("--langs", default=",".join(i18n.LANGS),
                        help="Comma-separated languages of the Web Interface screenshots (default: all)")
    args = parser.parse_args()
    print(f"Writing landing media to {MEDIA_DIR}")
    if args.only in (None, "web"):
        langs = [code for code in (item.strip() for item in args.langs.split(",")) if code in i18n.LANGS]
        capture_web(args.url.rstrip("/"), args.user, args.password, langs)
    if args.only in (None, "tui"):
        capture_tui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
