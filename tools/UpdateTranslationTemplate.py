#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build lang/messages.pot (the English source catalog of the Web Interface) and add the new texts to every lang/<code>.po.

The Web Interface is written in English; translators copy lang/messages.pot to lang/<code>.po and fill each msgstr.
Texts come from three places:
  1. a JSON list of the visible texts of a running local Web Interface (collected with --ui-texts, see
     tools/CollectUiTexts.py),
  2. the literal UI strings of the page scripts (statuses, dialogs and notices),
  3. the email texts of src/web_interface/app.py (EMAIL_TEXTS below).
Numbers inside texts become placeholders ("3 accounts" -> "{0} accounts").

    python tools/UpdateTranslationTemplate.py --ui-texts ui_texts.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import zoneinfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANG_DIR = ROOT / "lang"
sys.path.insert(0, str(ROOT))
from lang import i18n  # noqa: E402

TEMPLATES = ["_main_app_page.html", "admin.html", "login.html", "doc_view.html"]
EMAIL_TEXTS = [
    "Account request from {0}", "New account request",
    "<b>{0}</b> ({1}) asked for a PhotoMigrator account.<br>Message: <i>{2}</i>",
    "<b>{0}</b> ({1}) asked for a PhotoMigrator account.",
    "Approve it by activating the account in the Administration Panel, or reject it from the same list.", "Review the request",
    "We received your account request", "Hi {0},",
    "your request for a PhotoMigrator account with the username <b>{0}</b> is waiting for approval. We will email you as soon as it is active.",
    "Your PhotoMigrator account",
    "{0} created a PhotoMigrator account for you. Sign in with the username <b>{1}</b> or with this email address.",
    "Your temporary password is <b>{0}</b>. You will choose your own password the first time you sign in.",
    "Use the password your administrator gave you.", "The account is not active yet. We will email you when it is.",
    "Sign in to PhotoMigrator", "Your account is active",
    "your PhotoMigrator account is now active. Sign in with the username <b>{0}</b> or your email address and {1}.",
    "the password you chose", "your password", "Your account has been disabled",
    "an administrator disabled your PhotoMigrator account <b>{0}</b>. If you think this is a mistake, reply to this email.",
    "Your account request",
    "your request for a PhotoMigrator account was not approved. If you think this is a mistake, reply to this email.",
    "Your password was changed",
    "an administrator changed the password of your PhotoMigrator account <b>{0}</b>. Ask them for the new password if you did not get it. If you did not expect this change, contact them.",
    "the password of your PhotoMigrator account <b>{0}</b> was changed. If it was not you, contact your administrator right away.",
    "Email check",
    "this is the test email you asked for from the Administration Panel. If you got it, PhotoMigrator can send account notices (requests, activations and password changes) and the emails of finished tasks.",
    "Open PhotoMigrator", "{0} finished", "{0} stopped", "{0} failed", "your task <b>{0}</b> finished successfully.",
    "your task <b>{0}</b> was stopped before it finished.", "your task <b>{0}</b> ended with errors (exit code {1}).",
    "Duration: <b>{0}</b>. Last lines of the log:", "Open Activity", "(no output)",
]


def numbered(text: str) -> str:
    if "{0}" in text or re.search(r"\d+[.:/_-]\d+|\bv\d|Example", text):
        return text
    counter = itertools.count()
    return re.sub(r"(?<![\w-])\d+(?![\w-])", lambda _: "{%d}" % next(counter), text)


def is_ui_text(text: str, timezones: set) -> bool:
    if not re.search(r"[A-Za-z]", text) or text in timezones or text.startswith("-"):
        return False
    if re.fullmatch(r"[a-z0-9_\-]+", text):
        return False
    if re.fullmatch(r"[\w./@<>:\-]+", text) and ("/" in text or "_" in text or "." in text or text.isupper()):
        return False
    return True


def script_literals() -> set:
    found = set()
    for name in TEMPLATES:
        source = (ROOT / "src" / "web_interface" / "html" / name).read_text(encoding="utf-8")
        for match in re.finditer(r'"([A-Z][^"\\$<>{}]*?\s[^"\\$<>{}]*?)"', source):
            text = match.group(1).strip()
            if re.search(r"[a-z]{2}", text) and not re.search(r"[#=;]|\.(js|css|html)\b|/api/", text):
                found.add(text)
        for match in re.finditer(r"`([A-Z][^`]*?)`", source):
            text = match.group(1)
            if "${" in text and not re.search(r"[<>#=;]|/api/", text):
                counter = itertools.count()
                text = re.sub(r"\$\{[^}]*\}", lambda _: "{%d}" % next(counter), text).strip()
                if re.search(r"[a-z]{3}", text):
                    found.add(text)
    return found


def po_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def write_po(path: Path, keys: list, translations: dict, lang: str | None) -> None:
    header = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"']
    if lang:
        header.append(f'"Language: {lang}\\n"')
    lines = ["# PhotoMigrator Web Interface - " + (f"{i18n.LANGS[lang]} ({lang})" if lang else "English source template"),
             "# msgid: English text. msgstr: translation. Keep {0}, {1}... and HTML tags such as <b> in the translation.", ""]
    lines += header + [""]
    for key in keys:
        lines += [f"msgid {po_quote(key)}", f"msgstr {po_quote(translations.get(key, '') if lang else '')}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ui-texts", required=True, help="JSON list of visible texts collected from a running Web Interface")
    args = parser.parse_args()
    timezones = set(zoneinfo.available_timezones())
    texts = set()
    for raw in json.loads(Path(args.ui_texts).read_text(encoding="utf-8")):
        text = re.sub(r"^[\s:·—–-]+", "", str(raw)).strip()
        if is_ui_text(text, timezones):
            texts.add(text)
    texts |= script_literals()
    keys = sorted({numbered(text) for text in texts} | set(EMAIL_TEXTS))
    write_po(LANG_DIR / "messages.pot", keys, {}, None)
    for code in i18n.LANGS:
        if code == i18n.DEFAULT:
            continue
        path = LANG_DIR / f"{code}.po"
        existing = i18n.parse_po(path.read_text(encoding="utf-8")) if path.exists() else {}
        write_po(path, sorted(set(keys) | set(existing)), existing, code)
    print(f"{len(keys)} texts in lang/messages.pot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
