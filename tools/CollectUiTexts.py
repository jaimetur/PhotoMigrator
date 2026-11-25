#!/usr/bin/env python3
"""
Collect every visible text of a running local PhotoMigrator Web Interface (input for tools/UpdateTranslationTemplate.py).

Requirements (not project dependencies): pip install playwright && python -m playwright install chromium.
Use a local test instance only: it signs in, opens every feature, action, settings section, Activity and Admin.

    python tools/CollectUiTexts.py http://127.0.0.1:6078 ui_texts.json <admin user> <password>
"""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1]
OUT = sys.argv[2]
USER, PASSWORD = sys.argv[3], sys.argv[4]

COLLECT = r"""() => {
  const SKIP = "code, pre, kbd, samp, script, style, textarea, .command, [data-no-i18n], [contenteditable=true], noscript";
  const out = new Set();
  const add = (s) => { s = String(s || "").replace(/[\s ]+/g, " ").trim(); if (/[A-Za-z]/.test(s)) out.add(s); };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
    acceptNode: (n) => n.nodeType === 1 && n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  let n;
  while ((n = walker.nextNode())) {
    if (n.nodeType === 3) add(n.nodeValue);
    else ["title", "placeholder", "aria-label", "alt"].forEach((a) => { if (n.getAttribute(a)) add(n.getAttribute(a)); });
  }
  add(document.title);
  return [...out];
}"""

texts = set()


def grab(page):
    page.wait_for_timeout(250)
    texts.update(page.evaluate(COLLECT))


def open_all(page):
    page.evaluate("""() => { document.querySelectorAll('details').forEach(d => d.open = true);
      document.querySelectorAll('[aria-expanded="false"]').forEach(b => { try { b.click(); } catch (e) {} }); }""")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(f"{BASE}/login")
    grab(page)
    page.click("#show-request-form")
    grab(page)
    page.click("#show-login-form")
    page.fill("#username", USER)
    page.fill("#password", PASSWORD)
    page.click("#login-form button[type=submit]")
    page.wait_for_url("**/features**")
    page.wait_for_function("typeof schema !== 'undefined' && schema !== null")
    page.goto(f"{BASE}/features?view=home&manual_navigation=1")
    page.wait_for_function("typeof schema !== 'undefined' && schema !== null")
    grab(page)
    modules = page.evaluate("Object.keys(MODULE_TAB_NAMES)")
    for module in modules:
        page.goto(f"{BASE}/features?manual_navigation=1")
        page.wait_for_function("typeof schema !== 'undefined' && schema !== null")
        page.evaluate("(m) => openModuleFromNavigation(m)", module)
        page.wait_for_timeout(400)
        open_all(page)
        grab(page)
        count = page.locator("[data-action-dest]").count()
        for index in range(count):
            try:
                page.locator("[data-action-dest]").nth(index).click(timeout=2000)
                open_all(page)
                grab(page)
            except Exception as exc:
                print("skip action", module, index, exc)
        if module == "automatic_migration":
            for kind in ["synology", "immich", "google_photos", "nextcloud", "local", "google_takeout", "icloud_takeout"]:
                try:
                    page.evaluate("""(k) => { uiState.migration_endpoints = {source: {kind: k, account: '1', path: ''}, target: {kind: k, account: '1', path: ''}}; renderAll(); }""", kind)
                    open_all(page)
                    grab(page)
                except Exception as exc:
                    print("skip endpoint", kind, exc)
    page.goto(f"{BASE}/configuration?manual_navigation=1")
    page.wait_for_function("typeof schema !== 'undefined' && schema !== null")
    grab(page)
    for selector in ["#general-tabs button", ".section-item"]:
        for index in range(page.locator(selector).count()):
            try:
                page.locator(selector).nth(index).click(timeout=2000)
                open_all(page)
                grab(page)
            except Exception as exc:
                print("skip", selector, index, exc)
    page.goto(f"{BASE}/output")
    page.wait_for_timeout(800)
    grab(page)
    page.goto(f"{BASE}/admin")
    page.wait_for_timeout(1500)
    grab(page)
    browser.close()

json.dump(sorted(texts), open(OUT, "w"), ensure_ascii=False, indent=0)
print(len(texts), "texts")
