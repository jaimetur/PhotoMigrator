"""
Create the Google Photos refresh token of one account and save it in Config.ini.

PhotoMigrator talks to Google Photos with GOOGLE_PHOTOS_CLIENT_ID_<N>, GOOGLE_PHOTOS_CLIENT_SECRET_<N> and
GOOGLE_PHOTOS_REFRESH_TOKEN_<N>. This module runs the OAuth "installed app" flow for an OAuth client of type
"Desktop app": it opens the Google consent page, receives the authorization code on a temporary local address
(http://127.0.0.1:<port>/) and exchanges it, with PKCE, for a refresh token that has the scopes PhotoMigrator needs.

When the browser runs on another machine (Docker, NAS, SSH), the consent page redirects to an address that does
not load: the user copies that address from the browser and pastes it in the terminal instead.
"""

from __future__ import annotations

import base64
import hashlib
import re
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE_APPEND_ONLY = "https://www.googleapis.com/auth/photoslibrary.appendonly"
SCOPE_APP_CREATED_DATA = "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata"
REQUIRED_SCOPES = (SCOPE_APPEND_ONLY, SCOPE_APP_CREATED_DATA)
SECTION = "Google Photos"
WAIT_SECONDS = 300


def missing_scopes(granted_scope: str, required=REQUIRED_SCOPES) -> list[str]:
    """Required scopes that are not in the space-separated scope string returned by Google."""
    granted = set(str(granted_scope or "").split())
    return [scope for scope in required if scope not in granted]


def scope_help_text(account_id: int | str) -> str:
    return (
        f"Create a new refresh token with the scopes '{SCOPE_APPEND_ONLY}' and '{SCOPE_APP_CREATED_DATA}' "
        f"(run PhotoMigrator with '--google-photos-authorize --account-id {account_id}', or follow "
        f"'help/06-google-photos.md') and put it in GOOGLE_PHOTOS_REFRESH_TOKEN_{account_id}. "
        "In Google's consent screen, tick every permission checkbox."
    )


def _pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorization_url(client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(REQUIRED_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def parse_redirect(value: str, expected_state: str) -> str:
    """Authorization code from a redirect address (or its query string). Raises ValueError with the reason."""
    text = str(value or "").strip()
    query = urlparse(text).query if "://" in text else text.lstrip("?/")
    params = parse_qs(query)
    if params.get("error"):
        raise ValueError(f"Google returned an error: {params['error'][0]}")
    if params.get("state", [""])[0] != expected_state:
        raise ValueError("The address does not belong to this authorization (state mismatch). Start again.")
    code = params.get("code", [""])[0]
    if not code:
        raise ValueError("The address does not include an authorization code.")
    return code


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str, code_verifier: str, timeout: int = 60) -> Dict[str, str]:
    response = requests.post(
        TOKEN_URL,
        timeout=timeout,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Google did not accept the authorization code (status={response.status_code}, body={response.text[:350]})")
    data = response.json()
    if not str(data.get("refresh_token") or "").strip():
        raise RuntimeError(
            "Google did not return a refresh token. Remove PhotoMigrator from https://myaccount.google.com/permissions "
            "and run the authorization again."
        )
    return data


def read_client_credentials(config_file: str | Path, account_id: int) -> Tuple[str, str]:
    from Core.ConfigReader import load_config

    config = load_config(config_file=str(config_file), section_to_load=SECTION)
    section = config.get(SECTION, {}) or {}
    client_id = str(section.get(f"GOOGLE_PHOTOS_CLIENT_ID_{account_id}", "") or "").strip()
    client_secret = str(section.get(f"GOOGLE_PHOTOS_CLIENT_SECRET_{account_id}", "") or "").strip()
    if not client_id or not client_secret:
        raise ValueError(
            f"Add GOOGLE_PHOTOS_CLIENT_ID_{account_id} and GOOGLE_PHOTOS_CLIENT_SECRET_{account_id} of an OAuth client of type "
            f"'Desktop app' to the [{SECTION}] section of '{config_file}' first."
        )
    return client_id, client_secret


def save_refresh_token(config_file: str | Path, account_id: int, refresh_token: str) -> None:
    """Write GOOGLE_PHOTOS_REFRESH_TOKEN_<N> in the [Google Photos] section, keeping the rest of the file (and comments)."""
    path = Path(config_file)
    key = f"GOOGLE_PHOTOS_REFRESH_TOKEN_{account_id}"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    section_start = next((i for i, line in enumerate(lines) if line.strip().lower() == f"[{SECTION.lower()}]"), None)
    if section_start is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += ["\n", f"[{SECTION}]\n", f"{key} = {refresh_token}\n"]
        path.write_text("".join(lines), encoding="utf-8")
        return
    section_end = next((i for i in range(section_start + 1, len(lines)) if lines[i].lstrip().startswith("[")), len(lines))
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)([^#\r\n]*?)(\s*#.*)?(\r?\n)?$")
    for index in range(section_start + 1, section_end):
        match = pattern.match(lines[index])
        if match:
            comment = match.group(3) or ""
            lines[index] = f"{match.group(1)}{refresh_token}{comment}{match.group(4) or ''}"
            break
    else:
        insert_at = section_end
        while insert_at > section_start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, f"{key} = {refresh_token}\n")
    path.write_text("".join(lines), encoding="utf-8")


class _RedirectHandler(BaseHTTPRequestHandler):
    on_query: Callable[[str], None] = staticmethod(lambda _query: None)

    def do_GET(self):  # noqa: N802 - name required by BaseHTTPRequestHandler
        query = urlparse(self.path).query
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body style='font-family:sans-serif;padding:40px'><h2>PhotoMigrator</h2>"
            b"<p>Authorization received. You can close this tab and go back to the terminal.</p></body></html>"
        )
        if query:
            type(self).on_query(query)

    def log_message(self, *_args):  # Keep the terminal clean.
        return


def authorize(config_file: str | Path, account_id: int = 1, open_browser: bool = True, log: Callable[[str], None] = print,
              read_line: Optional[Callable[[], str]] = None) -> Dict[str, str]:
    """Run the whole flow and save the refresh token. Returns the token response (without printing secrets)."""
    account_id = int(account_id or 1)
    client_id, client_secret = read_client_credentials(config_file, account_id)
    state = secrets.token_urlsafe(24)
    verifier, challenge = _pkce_pair()

    received: Dict[str, str] = {}
    done = threading.Event()

    def accept(value: str) -> None:
        if done.is_set():
            return
        try:
            received["code"] = parse_redirect(value, state)
            done.set()
        except ValueError as exc:
            log(f"WARNING: {exc}")

    handler = type("PhotoMigratorRedirectHandler", (_RedirectHandler,), {"on_query": staticmethod(accept)})
    server = HTTPServer(("127.0.0.1", 0), handler)
    redirect_uri = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = build_authorization_url(client_id, redirect_uri, state, challenge)

    log(f"Google Photos authorization for account {account_id}.")
    log("1. Open this address in a browser and sign in with the Google account to use (tick every permission checkbox):")
    log(url)
    log("2. If the browser runs on this machine, PhotoMigrator receives the authorization by itself.")
    log("   Otherwise the last page will not load: copy its full address from the browser and paste it here, then press Enter.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if read_line is None and sys.stdin is not None and sys.stdin.isatty():
        read_line = sys.stdin.readline
    if read_line is not None:
        def read_pasted() -> None:
            while not done.is_set():
                line = read_line()
                if not line:
                    return
                if line.strip():
                    accept(line.strip())
        threading.Thread(target=read_pasted, daemon=True).start()

    try:
        if not done.wait(WAIT_SECONDS):
            raise TimeoutError(f"No authorization received in {WAIT_SECONDS // 60} minutes. Run it again.")
    finally:
        server.shutdown()
        server.server_close()

    tokens = exchange_code(client_id, client_secret, received["code"], redirect_uri, verifier)
    missing = missing_scopes(str(tokens.get("scope") or ""))
    if SCOPE_APPEND_ONLY in missing:
        raise RuntimeError(
            "Google granted the token without permission to add photos to your library "
            f"('{SCOPE_APPEND_ONLY}'). Run the authorization again and tick every permission checkbox."
        )
    save_refresh_token(config_file, account_id, str(tokens["refresh_token"]).strip())
    log(f"Saved GOOGLE_PHOTOS_REFRESH_TOKEN_{account_id} in '{config_file}'.")
    if missing:
        log(f"WARNING: the token cannot list or download the photos created by PhotoMigrator (missing '{missing[0]}'). Uploads work.")
    return tokens
