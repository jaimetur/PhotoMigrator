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
    "Your password was reset", "an administrator reset the password of your PhotoMigrator account <b>{0}</b>.",
]
# Server texts shown in the Administration Panel (event names of the access log and reasons of skipped bulk changes).
ADMIN_TEXTS = [
    "Sign in", "Failed sign in", "User created", "User updated", "User deleted", "Password reset", "Email settings",
    "Test email", "Backup", "Backup restored", "Backup deleted", "Database edit",
    "You cannot deactivate your own account.", "You cannot delete your own user.", "Cannot deactivate the last active admin.",
    "Cannot change role of the last active admin.", "Cannot delete the last active admin.", "User not found.",
    # Labels and texts of the help card of the side panel.
    "Example", "Examples", "You need", "Optional",
    "Upload a folder or a ZIP file from this computer to a folder on the server, so the other features can use it.",
    "Extract ZIPs on upload on: ZIP files are extracted on the server and the ZIP file is removed.",
    "Extract ZIPs on upload off: ZIP files are kept as uploaded.",
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
        # Texts passed to the page translators: T("...") and fmt("... {0} ...").
        for match in re.finditer(r'\b(?:T|fmt|pmT)\("([^"\\]+)"', source):
            text = match.group(1).strip()
            if re.search(r"[A-Za-z]{2}", text):
                found.add(text)
        for match in re.finditer(r"`([A-Z][^`]*?)`", source):
            text = match.group(1)
            if "${" in text and not re.search(r"[<>#=;]|/api/", text):
                counter = itertools.count()
                text = re.sub(r"\$\{[^}]*\}", lambda _: "{%d}" % next(counter), text).strip()
                if re.search(r"[a-z]{3}", text):
                    found.add(text)
    return found


def _clean_help_line(line: str) -> str:
    """Same cleaning as uiHelpText() in the Web Interface."""
    text = re.sub(r"^CAUTION!!!\s*", "", line.strip(), flags=re.I)
    text = re.sub(r"^ATTENTION!!!:?\s*", "", text, flags=re.I)
    text = re.sub(r"Requires\s+'--client'\.?\s*", "", text, flags=re.I).strip()
    return re.sub(r"You must provide the photo client using '--client'\.?\s*", "", text, flags=re.I).strip()


def help_texts() -> set:
    """Lines of the option help as the Web Interface help card translates them (see formatDescriptionHtml)."""
    sys.path.insert(0, str(ROOT / "src"))
    old_argv = sys.argv[:]
    try:
        sys.argv = ["web-interface"]
        from Core.ArgsParser import parse_arguments
        _, parser = parse_arguments()
    finally:
        sys.argv = old_argv
    found = set()
    for action in parser._actions:
        if not action.option_strings or not action.help or action.help == "==SUPPRESS==":
            continue
        lines = [_clean_help_line(line) for line in str(action.help).split("\n")]
        lines = [line for line in lines if line]
        bullets, examples = [], []
        seen_bullet = False
        for line in lines:
            if re.match(r"^Examples?:", line, re.I):
                examples.append(line)
                continue
            important = re.match(r"^(IMPORTANT|NOTE)(?:!+)?\s*:\s*(.*)$", line, re.I)
            if important:
                found.add(important.group(2))
                continue
            if re.match(r"^[-•·]\s+", line) or re.match(r"^\d+\)\s+", line):
                bullets.append(re.sub(r"^[-•·]\s+", "", line))
                seen_bullet = True
                continue
            if seen_bullet or examples:
                if bullets and not re.match(r"^[A-Z]", line):
                    bullets[-1] += f" {line}"
                elif re.match(r"^--?\w", line) or re.match(r"^\.?/", line):
                    continue
                else:
                    bullets.append(line)
                continue
            found.add(line)
        found.update(bullets)
    return {text for text in found if re.search(r"[A-Za-z]{3}", text)}


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
    help_keys = help_texts()
    # Help lines are translated verbatim (numbers included), so they are not turned into {0} patterns.
    keys = sorted({numbered(text) for text in texts} | set(EMAIL_TEXTS) | set(ADMIN_TEXTS) | help_keys)
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
