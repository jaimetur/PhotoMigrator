"""Outgoing email (SMTP) for the PhotoMigrator Web Interface.

Configured with environment variables (SMTP_HOST, SMTP_PORT, SMTP_SECURITY = ssl | starttls | none, SMTP_USERNAME,
SMTP_PASSWORD, SMTP_FROM and SMTP_FROM_NAME). Values saved in the Administration Panel override them. Emails are sent
in the background, so a slow or broken mail server never blocks a web request; failures are only logged.
"""
from __future__ import annotations

import html
import logging
import os
import re
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Callable, Dict, List, Sequence, Tuple

LOGGER = logging.getLogger("PhotoMigrator.web_interface.mail")
TIMEOUT_SECONDS = 60
SUBJECT_PREFIX = "PhotoMigrator - "
BRAND_COLOR = "#2563eb"
SECURITY_CHOICES = ("ssl", "starttls", "none")
DEFAULT_PORTS = {"ssl": 465, "starttls": 587, "none": 25}

# Setting name -> environment variable used when the Administration Panel leaves it empty.
FIELDS = {
    "host": "SMTP_HOST",
    "port": "SMTP_PORT",
    "security": "SMTP_SECURITY",
    "username": "SMTP_USERNAME",
    "password": "SMTP_PASSWORD",
    "from_address": "SMTP_FROM",
    "from_name": "SMTP_FROM_NAME",
}

_stored_settings_loader: Callable[[], Dict[str, str]] = lambda: {}
# Localization hooks: recipients grouped by the language of their account, and translators for subject and body.
_group_by_lang: Callable[[List[str]], Dict[str, List[str]]] = lambda recipients: {"en": list(recipients)}
_translate_text: Callable[[str, str], str] = lambda text, lang: text
_translate_html: Callable[[str, str], str] = lambda markup, lang: markup


def set_localizer(
    group_by_lang: Callable[[List[str]], Dict[str, List[str]]],
    translate_text: Callable[[str, str], str],
    translate_html: Callable[[str, str], str],
) -> None:
    """Register how to send each recipient the email in the language of their account."""
    global _group_by_lang, _translate_text, _translate_html
    _group_by_lang, _translate_text, _translate_html = group_by_lang, translate_text, translate_html


def set_stored_settings_loader(loader: Callable[[], Dict[str, str]]) -> None:
    """Register the function that returns the settings saved in the Administration Panel."""
    global _stored_settings_loader
    _stored_settings_loader = loader


def _raw_values() -> Dict[str, str]:
    try:
        stored = dict(_stored_settings_loader() or {})
    except Exception as exc:  # The database must never break outgoing email.
        LOGGER.warning("Unable to read the stored mail settings: %s", exc)
        stored = {}
    return {
        key: str(stored[key]) if stored.get(key) not in (None, "") else os.environ.get(env_name, "")
        for key, env_name in FIELDS.items()
    }


def settings() -> Dict[str, object]:
    raw = _raw_values()
    security = str(raw.get("security") or "ssl").strip().lower()
    if security not in SECURITY_CHOICES:
        security = "ssl"
    try:
        port = int(raw.get("port") or DEFAULT_PORTS[security])
    except (TypeError, ValueError):
        port = DEFAULT_PORTS[security]
    values: Dict[str, object] = {
        "host": str(raw.get("host") or "").strip(),
        "port": port,
        "security": security,
        "username": str(raw.get("username") or "").strip(),
        "password": str(raw.get("password") or ""),
        "from_address": str(raw.get("from_address") or raw.get("username") or "").strip(),
        "from_name": str(raw.get("from_name") or "PhotoMigrator").strip(),
    }
    values["configured"] = bool(values["host"] and values["from_address"])
    return values


def is_configured() -> bool:
    return bool(settings()["configured"])


def public_settings() -> Dict[str, object]:
    """Settings safe to show in the Administration Panel (the password is never returned)."""
    values = settings()
    out = {key: values[key] for key in ("configured", "host", "port", "security", "username", "from_address", "from_name")}
    out["has_password"] = bool(values["password"])
    return out


def page(title: str, paragraphs: Sequence[str], link: Tuple[str, str] | None = None, preformatted: str = "") -> str:
    """Simple HTML email with the PhotoMigrator colors. Paragraphs must already be HTML-escaped."""
    button = ""
    if link:
        button = (
            f'<p style="margin:22px 0 4px"><a href="{html.escape(link[1], quote=True)}" style="background:{BRAND_COLOR};'
            'color:#fff;text-decoration:none;padding:11px 18px;border-radius:10px;font-weight:600;display:inline-block">'
            f"{html.escape(link[0])}</a></p>"
        )
    body = "".join(f'<p style="margin:0 0 12px">{paragraph}</p>' for paragraph in paragraphs)
    if preformatted:
        body += (
            '<pre style="margin:4px 0 12px;padding:12px;background:#0f172a;color:#e2e8f0;border-radius:10px;'
            'font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word">'
            f"{html.escape(preformatted)}</pre>"
        )
    return (
        '<!doctype html><html lang="en"><body style="margin:0;background:#eef2f7;padding:24px 12px;'
        'font:15px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#0f172a">'
        '<div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #dbe3ee;border-radius:16px;padding:22px">'
        f'<div style="font-weight:700;font-size:18px;color:{BRAND_COLOR};margin-bottom:14px">PhotoMigrator</div>'
        f'<h1 style="font-size:19px;margin:0 0 12px">{html.escape(title)}</h1>{body}{button}</div></body></html>'
    )


def text_of(html_body: str) -> str:
    """Plain-text alternative of an HTML email built with page()."""
    text = re.sub(r"<br\s*/?>|</p>|</h1>|</div>|</pre>", "\n", html_body)
    text = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2: \1", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _clean_recipients(recipients: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(item).strip() for item in recipients if item and str(item).strip()))


def build(values: Dict[str, object], recipients: Sequence[str], subject: str, html_body: str, reply_to: str | None = None) -> EmailMessage:
    message = EmailMessage()
    from_address = str(values["from_address"])
    message["Subject"] = SUBJECT_PREFIX + subject
    message["From"] = formataddr((str(values["from_name"]), from_address))
    message["To"] = ", ".join(recipients)
    if reply_to:
        message["Reply-To"] = reply_to
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=from_address.split("@")[-1] or None)
    message.set_content(text_of(html_body))
    message.add_alternative(html_body, subtype="html")
    return message


def send(recipients: Sequence[str], subject: str, html_body: str, reply_to: str | None = None) -> None:
    """Send an email now. Raises RuntimeError with a readable message when it fails."""
    values = settings()
    to = _clean_recipients(recipients)
    if not values["configured"]:
        raise RuntimeError("Email is not configured (set SMTP_HOST and SMTP_FROM, or use the Administration Panel).")
    if not to:
        raise RuntimeError("The email has no recipients.")
    try:
        groups = _group_by_lang(to) or {"en": to}
    except Exception as exc:  # Localization must never block an email.
        LOGGER.warning("Unable to group email recipients by language: %s", exc)
        groups = {"en": to}
    for lang, group in groups.items():
        _deliver(values, list(group), _translate_text(subject, lang), _translate_html(html_body, lang), reply_to)


def _deliver(values: Dict[str, object], to: List[str], subject: str, html_body: str, reply_to: str | None) -> None:
    message = build(values, to, subject, html_body, reply_to)
    context = ssl.create_default_context()
    host = str(values["host"])
    port = int(values["port"])
    helo = str(values["from_address"]).split("@")[-1] or "localhost"
    try:
        if values["security"] == "ssl":
            server = smtplib.SMTP_SSL(host, port, local_hostname=helo, timeout=TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(host, port, local_hostname=helo, timeout=TIMEOUT_SECONDS)
        with server:
            server.ehlo()
            if values["security"] == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if values["username"]:
                server.login(str(values["username"]), str(values["password"]))
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError("The mail server rejected the username or password.") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(f"Unable to send the email: {type(exc).__name__}.") from exc


def send_later(recipients: Sequence[str], subject: str, html_body: str, reply_to: str | None = None) -> bool:
    """Send an email in the background. Returns False (and sends nothing) when email is not configured."""
    to = _clean_recipients(recipients)
    if not to or not is_configured():
        LOGGER.info("Email not sent (email not configured or no recipients): %s", subject)
        return False

    def _worker() -> None:
        try:
            send(to, subject, html_body, reply_to)
            LOGGER.info("Email sent: %s", subject)
        except RuntimeError as exc:
            LOGGER.warning("Email not sent: %s - %s", subject, exc)

    threading.Thread(target=_worker, name="photomigrator-mail", daemon=True).start()
    return True
