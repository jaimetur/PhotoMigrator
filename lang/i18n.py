"""PhotoMigrator languages, shared by the Web Interface backend and its pages.

The interface is written in English. Each language has a gettext catalog in this folder (``lang/<code>.po``) whose
``msgid`` is the English text and ``msgstr`` its translation. Texts with variable parts use numbered placeholders
(``"{0} users"`` -> ``"{0} usuarios"``). A missing translation falls back to English.

The browser translates the pages with ``lang/i18n.js`` and the catalog returned by :func:`catalog`; the backend uses
:func:`translate` and :func:`translate_html` (for example in emails).
"""
from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

LANG_DIR = Path(__file__).resolve().parent
LANGS: Dict[str, str] = {
    "en": "English",
    "es": "Español",
    "ca": "Català",
    "fr": "Français",
    "it": "Italiano",
    "de": "Deutsch",
    "pt": "Português",
    "nl": "Nederlands",
    "zh": "中文",
    "ja": "日本語",
}
DEFAULT = "en"
COOKIE = "pm_lang"
_EDGE = re.compile(r"^([\s:·—–]*)(.*?)(\s*)$", re.S)
_PLACEHOLDER = re.compile(r"\\\{(\d)\\\}")


def clean(value: str | None) -> str | None:
    """Supported language code of ``value`` ("es-ES" -> "es"), or None."""
    code = str(value or "").strip().lower().replace("_", "-").split("-")[0][:3]
    return code if code in LANGS else None


def from_accept_language(header: str | None) -> str | None:
    """First supported language of an Accept-Language header."""
    for part in str(header or "").split(","):
        code = clean(part.split(";")[0])
        if code:
            return code
    return None


def _unescape(value: str) -> str:
    return re.sub(r'\\(["\\nt])', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), value)


def parse_po(text: str) -> Dict[str, str]:
    """``{msgid: msgstr}`` of a .po file (only translated, non-fuzzy entries)."""
    entries: Dict[str, str] = {}
    msgid: List[str] | None = None
    msgstr: List[str] | None = None
    current: List[str] | None = None
    fuzzy = False

    def commit() -> None:
        if msgid is not None and msgstr is not None and not fuzzy:
            key, value = "".join(msgid), "".join(msgstr)
            if key and value:
                entries[key] = value

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            commit()
            msgid = msgstr = current = None
            fuzzy = False
        elif line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
        elif line.startswith("#"):
            continue
        elif line.startswith("msgid "):
            commit()
            msgid, msgstr = [_unescape(line[6:].strip()[1:-1])], None
            current = msgid
        elif line.startswith("msgstr "):
            msgstr = [_unescape(line[7:].strip()[1:-1])]
            current = msgstr
        elif line.startswith('"') and current is not None:
            current.append(_unescape(line[1:-1]))
    commit()
    return entries


def po_path(lang: str) -> Path:
    return LANG_DIR / f"{lang}.po"


def stamp(lang: str) -> int:
    """Changes when the catalog of ``lang`` changes (cache-busting in URLs)."""
    try:
        return int(po_path(lang).stat().st_mtime)
    except OSError:
        return 0


@lru_cache(maxsize=32)
def _load(lang: str, version: int) -> Tuple[Dict[str, str], Tuple[Tuple[re.Pattern, str], ...]]:
    if lang == DEFAULT or lang not in LANGS:
        return {}, ()
    try:
        entries = parse_po(po_path(lang).read_text(encoding="utf-8"))
    except OSError:
        entries = {}
    patterns = tuple(
        (re.compile("^" + _PLACEHOLDER.sub(r"(.+?)", re.escape(key)) + "$", re.S), value)
        for key, value in entries.items()
        if "{0}" in key
    )
    return entries, patterns


def catalog(lang: str) -> Dict[str, str]:
    """English text -> translation for ``lang`` (empty for English)."""
    return dict(_load(lang, stamp(lang))[0])


def translate(text: str, lang: str | None) -> str:
    """Translate one English text (surrounding spaces are kept); unknown texts are returned unchanged."""
    code = clean(lang) or DEFAULT
    if code == DEFAULT or not text or not text.strip():
        return text
    entries, patterns = _load(code, stamp(code))
    lead, core, tail = _EDGE.match(text).groups()
    if core in entries:
        return lead + entries[core] + tail
    for pattern, value in patterns:
        match = pattern.match(core)
        if match:
            out = value
            for index, part in enumerate(match.groups()):
                out = out.replace("{%d}" % index, translate(part, code))
            return lead + out + tail
    return text


def translate_html(markup: str, lang: str | None) -> str:
    """Translate the text of a small HTML fragment (for example an email), keeping its tags.

    Each run of text between block tags is translated as a whole, with inline tags (<b>, <i>, <code>, <a>) as
    part of the key, so a translator sees and moves them with the sentence.
    """
    code = clean(lang) or DEFAULT
    if code == DEFAULT:
        return markup
    blocks = re.split(r"(</?(?:p|h1|div|pre|html|body|!doctype)[^>]*>)", markup, flags=re.I)
    out = []
    for block in blocks:
        if not block or block.startswith("<"):
            out.append(block)
            continue
        out.append(html.escape(translate(html.unescape(block), code), quote=False) if "<" not in block else translate(block, code))
    return "".join(out)
