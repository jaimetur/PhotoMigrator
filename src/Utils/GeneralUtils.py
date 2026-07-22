import base64
import ctypes
import fnmatch
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import unicodedata
from dataclasses import is_dataclass, asdict
from datetime import datetime

import piexif
from tabulate import tabulate
from tqdm import tqdm as original_tqdm

import Core.GlobalVariables as GV
from Core.CustomLogger import set_log_level
from Core.GlobalVariables import VIDEO_EXT, PHOTO_EXT, MSG_TAGS, VERBOSE_LEVEL_NUM
from Utils.DateUtils import is_date_outside_range

TQDM_DASHBOARD_PREFIX = "__TQDM__ "
TQDM_DASHBOARD_META_PREFIX = "__TQDM_META__ "
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")
TQDM_PROGRESS_RE = re.compile(
    r"(?P<pct>\d{1,3})%\|[^|]*\|\s*(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)"
)
CUSTOM_PROGRESS_RE = re.compile(
    r"^(?P<desc>.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+"
    r"(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)\s+(?P<pct>\d+(?:\.\d+)?)%\s*$"
)
INDETERMINATE_TQDM_RE = re.compile(
    r"^(?P<desc>.*?:)\s*(?P<current>[0-9][0-9,]*)\s+\w+\s+\[\d{2}:\d{2}(?::\d{2})?,\s*(?P<rate>[^\]]+)\]\s*$"
)


# ------------------------------------------------------------------
# Integrate tqdm with the logger
class TqdmLoggerConsole:
    """Redirects tqdm output only to the console handlers of GV.LOGGER."""

    def __init__(self, logger, level=logging.INFO):
        self.logger = logger
        self.level = level
        self.levelname = logging.getLevelName(level)
        self._buffer = ""
        self._console_state = {}
        self._progress_snapshots = {}
        self._completed_progress = {}

    def _normalize_message(self, message: str) -> str:
        text = str(message or "")
        if self.levelname == "VERBOSE":
            return text.replace("VERBOSE : ", "")
        if self.levelname == "DEBUG":
            return text.replace("DEBUG   : ", "")
        if self.levelname == "INFO":
            return text.replace("INFO    : ", "")
        if self.levelname == "WARNING":
            return text.replace("WARNING : ", "")
        if self.levelname == "ERROR":
            return text.replace("ERROR   : ", "")
        if self.levelname == "CRITICAL":
            return text.replace("CRITICAL: ", "")
        return text

    def _build_meta_payload(self, message: str):
        """
        Build a structured tqdm frame for dashboard consumers.
        Format: "__TQDM_META__ <desc>\\t<current>\\t<total>"
        """
        text = str(message or "").replace("\r", "").strip()
        if not text:
            return None

        tqdm_match = re.search(
            r"(?P<pct>\d{1,3})%\|[^|]*\|\s*(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)",
            text,
        )
        if tqdm_match:
            desc = text[:tqdm_match.start()].strip(" :-") or "Progress"
            current = str(tqdm_match.group("current") or "0").replace(",", "")
            total = str(tqdm_match.group("total") or "0").replace(",", "")
            return f"{TQDM_DASHBOARD_META_PREFIX}{desc}\t{current}\t{total}"

        custom_match = re.match(
            r"^(?P<desc>.*?:)\s*[#=>.\s\u2588\u2593\u2592\u2591]+\s+"
            r"(?P<current>[0-9][0-9,]*)/(?P<total>[0-9][0-9,]*)\s+\d+(?:\.\d+)?%\s*$",
            text,
        )
        if custom_match:
            desc = str(custom_match.group("desc") or "").strip(" :-") or "Progress"
            current = str(custom_match.group("current") or "0").replace(",", "")
            total = str(custom_match.group("total") or "0").replace(",", "")
            return f"{TQDM_DASHBOARD_META_PREFIX}{desc}\t{current}\t{total}"

        indeterminate_match = INDETERMINATE_TQDM_RE.match(text)
        if indeterminate_match:
            desc = str(indeterminate_match.group("desc") or "").strip(" :-") or "Progress"
            current = str(indeterminate_match.group("current") or "0").replace(",", "")
            return f"{TQDM_DASHBOARD_META_PREFIX}{desc}\t{current}\t0"

        return None

    def _build_log_record(self, payload: str):
        return logging.LogRecord(
            name=self.logger.name,
            level=self.level,
            pathname="",
            lineno=0,
            msg=payload,
            args=(),
            exc_info=None
        )

    def _emit_record(self, handler, payload: str):
        stream = getattr(handler, "stream", None)
        encoding = getattr(stream, "encoding", None) if stream is not None else None
        safe_payload = payload
        if encoding:
            try:
                str(payload).encode(encoding)
            except UnicodeEncodeError:
                safe_payload = str(payload).encode(encoding, errors="replace").decode(encoding, errors="replace")
        handler.emit(self._build_log_record(safe_payload))

    def _strip_ansi(self, text: str) -> str:
        return ANSI_ESCAPE_RE.sub("", str(text or ""))

    def _parse_int(self, value, default=0):
        try:
            return int(str(value or "").replace(",", "").strip())
        except (TypeError, ValueError):
            return default

    def _extract_progress_state(self, message: str):
        """
        Parse tqdm/custom progress lines and return:
          (key, current, total, pct)
        """
        text = self._strip_ansi(str(message or "")).replace("\r", "").strip()
        if not text:
            return None

        custom_match = CUSTOM_PROGRESS_RE.match(text)
        if custom_match:
            desc = str(custom_match.group("desc") or "").strip(" :-") or "Progress"
            current = self._parse_int(custom_match.group("current"), 0)
            total = self._parse_int(custom_match.group("total"), 0)
            try:
                pct = float(str(custom_match.group("pct") or "0").strip())
            except ValueError:
                pct = 0.0
            return desc.lower(), current, total, pct

        tqdm_match = TQDM_PROGRESS_RE.search(text)
        if tqdm_match:
            desc = text[:tqdm_match.start()].strip(" :-") or "Progress"
            current = self._parse_int(tqdm_match.group("current"), 0)
            total = self._parse_int(tqdm_match.group("total"), 0)
            pct = float(self._parse_int(tqdm_match.group("pct"), 0))
            return desc.lower(), current, total, pct

        indeterminate_match = INDETERMINATE_TQDM_RE.match(text)
        if indeterminate_match:
            desc = str(indeterminate_match.group("desc") or "").strip(" :-") or "Progress"
            current = self._parse_int(indeterminate_match.group("current"), 0)
            return desc.lower(), current, 0, 0.0

        return None

    def _is_tty_console_handler(self, handler) -> bool:
        if not isinstance(handler, logging.StreamHandler) or isinstance(handler, logging.FileHandler):
            return False
        stream = getattr(handler, "stream", None)
        if stream is None:
            return False
        isatty = getattr(stream, "isatty", None)
        if not callable(isatty):
            return False
        try:
            return bool(isatty())
        except Exception:
            return False

    def _close_active_progress_line(self, handler):
        state = self._console_state.get(id(handler))
        if not state or not state.get("active"):
            return
        stream = getattr(handler, "stream", None)
        if stream is None:
            state["active"] = False
            state["key"] = None
            state["last_len"] = 0
            return
        try:
            stream.write("\n")
            stream.flush()
        except Exception:
            pass
        state["active"] = False
        state["key"] = None
        state["last_len"] = 0

    def _close_all_console_progress_lines(self):
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                self._close_active_progress_line(handler)

    def _emit_live_progress(self, handler, message: str, progress_state):
        key, current, total, pct = progress_state
        handler_id = id(handler)
        completed_by_key = self._completed_progress.setdefault(handler_id, {})

        # tqdm usually emits one final frame in refresh and another on close.
        # Keep only the first completed frame per progress key.
        done = (total > 0 and current >= total) or (total <= 0 and pct >= 100.0)
        completed_state = (int(current), int(total))
        if done:
            if completed_by_key.get(key) == completed_state:
                return
            completed_by_key[key] = completed_state
        else:
            completed_by_key.pop(key, None)

        stream = getattr(handler, "stream", None)
        if stream is None:
            self._emit_record(handler, message)
            return

        state = self._console_state.setdefault(
            id(handler), {"active": False, "key": None, "last_len": 0}
        )

        if state["active"] and state.get("key") != key:
            self._close_active_progress_line(handler)

        record = self._build_log_record(message)
        formatted = handler.format(record)
        visible_len = len(self._strip_ansi(formatted))

        try:
            if state["active"]:
                stream.write("\r")
            stream.write(formatted)
            if state["last_len"] > visible_len:
                stream.write(" " * (state["last_len"] - visible_len))
            stream.flush()
        except Exception:
            self._emit_record(handler, message)
            return

        # tqdm shows integer percentages and may display 100% before the true end.
        # Treat completion by counters, not by rounded percentage.
        if done:
            try:
                stream.write("\n")
                stream.flush()
            except Exception:
                pass
            state["active"] = False
            state["key"] = None
            state["last_len"] = 0
            return

        state["active"] = True
        state["key"] = key
        state["last_len"] = visible_len

    def _should_emit_progress_snapshot(self, handler, progress_state) -> bool:
        """
        In non-live mode, collapse repeated updates that keep the same current/total
        for the same logical progress key.
        """
        key, current, total, pct = progress_state
        handler_id = id(handler)
        by_key = self._progress_snapshots.setdefault(handler_id, {})
        prev = by_key.get(key)
        now = (int(current), int(total))
        by_key[key] = now
        if prev is None:
            return True
        return prev != now

    def _emit_to_handlers(self, message: str):
        if not message:
            return
        message = self._normalize_message(message)
        progress_state = self._extract_progress_state(message)

        for handler in self.logger.handlers:
            if getattr(handler, "accept_tqdm", False):
                payload = self._build_meta_payload(message)
                if payload is None:
                    payload = f"{TQDM_DASHBOARD_PREFIX}{message}"
                self._emit_record(handler, payload)
                continue

            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                env_live_tqdm = os.environ.get("PHOTOMIGRATOR_CLI_LIVE_TQDM")
                if env_live_tqdm is None:
                    live_tqdm_cli = self._is_tty_console_handler(handler)
                else:
                    live_tqdm_cli = env_live_tqdm == "1"
                if progress_state and self._is_tty_console_handler(handler) and live_tqdm_cli:
                    self._emit_live_progress(handler, message, progress_state)
                    continue

                if progress_state and not self._should_emit_progress_snapshot(handler, progress_state):
                    continue

                self._close_active_progress_line(handler)
                self._emit_record(handler, message)

    def write(self, message):
        if message is None:
            return

        self._buffer += str(message)
        while True:
            split_idx = None
            split_sep = None
            for candidate_sep in ("\r", "\n"):
                idx = self._buffer.find(candidate_sep)
                if idx != -1 and (split_idx is None or idx < split_idx):
                    split_idx = idx
                    split_sep = candidate_sep
            if split_idx is None:
                break

            chunk = self._buffer[:split_idx].strip()
            self._buffer = self._buffer[split_idx + 1:]
            if chunk:
                self._emit_to_handlers(chunk)
            if split_sep == "\n":
                self._close_all_console_progress_lines()

    def flush(self):
        chunk = self._buffer.strip()
        self._buffer = ""
        if chunk:
            self._emit_to_handlers(chunk)

    def close(self):
        self.flush()
        self._close_all_console_progress_lines()

    def isatty(self):
        """Trick tqdm into treating this as an interactive terminal."""
        return True


######################
# AUXILIARY FUNCTIONS
######################
# -------------------------------------------------------------
# Set Profile to analyze and optimize code:
# -------------------------------------------------------------
def profile_and_print(function_to_analyze, *args, step_name_for_profile='', live_stats=True, interval=10, top_n=10, **kwargs):
    """
    Runs cProfile only around `function_to_analyze` (keeping the wrapper sleep
    out of the profiling), dumps stats to GV.LOGGER.debug if `live_stats=True`,
    and returns the result of the analyzed function.
    """
    import io
    import cProfile
    import pstats
    import threading

    profiler = cProfile.Profile()
    done_event = threading.Event()
    result_holder = {"result": None, "exc": None}

    def _profile_worker():
        try:
            result_holder["result"] = profiler.runcall(function_to_analyze, *args, **kwargs)
        except BaseException as exc:
            result_holder["exc"] = exc
        finally:
            done_event.set()

    # Daemon thread is intentional: on Ctrl+C, main thread can exit immediately
    # without waiting for profiling worker cleanup.
    worker = threading.Thread(target=_profile_worker, daemon=True, name="profile_and_print_worker")
    worker.start()

    try:
        if live_stats:
            # While the task is not finished, dump stats every `interval`
            while not done_event.wait(timeout=interval):
                stream = io.StringIO()
                stats = pstats.Stats(profiler, stream=stream)
                stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
                GV.LOGGER.debug(f"{step_name_for_profile}⏱️ Intermediate Stats (top %d):\n\n%s", top_n, stream.getvalue())
        else:
            done_event.wait()
    except KeyboardInterrupt:
        GV.LOGGER.warning(f"{step_name_for_profile}Profiling interrupted by user (Ctrl+C).")
        raise

    if result_holder["exc"] is not None:
        raise result_holder["exc"]
    final_result = result_holder["result"]

    # Final report
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
    GV.LOGGER.debug(f"{step_name_for_profile}Final Profile Report (top %d):\n\n%s", top_n, stream.getvalue())

    return final_result


def _console_stream_supports_unicode(logger) -> bool:
    """
    Best-effort detection for UTF-capable console handlers.
    """
    handlers = list(getattr(logger, "handlers", []) or [])
    found_console = False
    for handler in handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            found_console = True
            stream = getattr(handler, "stream", None)
            encoding = str(getattr(stream, "encoding", "") or "").lower()
            if "utf" in encoding:
                return True
    return not found_console


# Redefine `tqdm` to use a logger-backed stream if `file` is not specified.
def tqdm(*args, **kwargs):
    """
    Wrapper around `tqdm` that redirects progress output to the console logger handlers
    so CLI and web can render consistent progress lines.
    """
    if 'file' not in kwargs and GV.LOGGER:
        handlers = list(getattr(GV.LOGGER, "handlers", []) or [])
        can_route_tqdm = any(
            getattr(handler, "accept_tqdm", False) or (
                isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
            )
            for handler in handlers
        )
        if can_route_tqdm:
            kwargs['file'] = TqdmLoggerConsole(GV.LOGGER, logging.INFO)
            # Prefer Unicode block bars when terminal supports UTF.
            # Fallback to plain ASCII for legacy encodings.
            if 'ascii' not in kwargs:
                force_ascii = os.environ.get("PHOTOMIGRATOR_TQDM_FORCE_ASCII", "0") == "1"
                custom_ascii = os.environ.get("PHOTOMIGRATOR_TQDM_ASCII_CHARS")
                if force_ascii or custom_ascii is not None:
                    ascii_chars = custom_ascii if custom_ascii is not None else " .#"
                    if not isinstance(ascii_chars, str) or len(ascii_chars) < 2:
                        ascii_chars = " .#"
                    kwargs['ascii'] = ascii_chars
                else:
                    kwargs['ascii'] = False if _console_stream_supports_unicode(GV.LOGGER) else " .#"
    return original_tqdm(*args, **kwargs)


def run_from_synology(log_level=None):
    """Check whether the script is running on a Synology NAS."""
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        return os.path.exists('/etc.defaults/synoinfo.conf')


def clear_screen():
    """Clears the terminal screen on both POSIX and Windows systems."""
    if os.name == 'nt':
        os.system('cls')
    elif os.environ.get('TERM') and sys.stdout.isatty():
        os.system('clear')


def print_arguments_pretty(arguments, title="Arguments", step_name="", use_logger=True, use_custom_print=True):
    """
    Prints a list of command-line arguments in a structured and readable one-line-per-arg format.

    Args:
        :param arguments:
        :param step_name:
        :param title:
        :param use_custom_print:
        :param use_logger:
    """
    print("")
    indent = "    "
    i = 0
    if use_logger:
        GV.LOGGER.info(f"{step_name}{title}:")
        while i < len(arguments):
            arg = arguments[i]
            if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                GV.LOGGER.info(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                i += 2
            else:
                GV.LOGGER.info(f"{step_name}{indent}{arg}")
                i += 1
    else:
        if use_custom_print:
            from Utils.StandaloneUtils import custom_print
            custom_print(f"{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    custom_print(f"{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    custom_print(f"{step_name}{indent}{arg}")
                    i += 1
        else:
            pass
            print(f"{MSG_TAGS['INFO']}{title}:")
            while i < len(arguments):
                arg = arguments[i]
                if arg.startswith('--') and i + 1 < len(arguments) and not arguments[i + 1].startswith('--'):
                    print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}={arguments[i + 1]}")
                    i += 2
                else:
                    print(f"{MSG_TAGS['INFO']}{step_name}{indent}{arg}")
                    i += 1
    print("")


def ensure_executable(path):
    """
    Ensures a file has executable permissions on non-Windows platforms.

    Args:
        path (str | Path): Path to the file to update.
    """
    if platform.system() != "Windows":
        # Add execution permissions for user, group and others without removing existing ones
        current_permissions = os.stat(path).st_mode
        os.chmod(path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if platform.system() == "Darwin":
        try:
            subprocess.run(
                ["xattr", "-d", "com.apple.quarantine", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass


def get_os(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized operating system name (linux, macos, windows)"""
    if use_logger:
        with set_log_level(GV.LOGGER, log_level):
            current_os = platform.system()
            if current_os in ["Linux", "linux"]:
                os_label = "linux"
            elif current_os in ["Darwin", "macOS", "macos"]:
                os_label = "macos"
            elif current_os in ["Windows", "windows", "Win"]:
                os_label = "windows"
            else:
                GV.LOGGER.error(f"{step_name}Unsupported Operating System: {current_os}")
                os_label = "unknown"
            GV.LOGGER.info(f"{step_name}Detected OS: {os_label}")
    else:
        current_os = platform.system()
        if current_os in ["Linux", "linux"]:
            os_label = "linux"
        elif current_os in ["Darwin", "macOS", "macos"]:
            os_label = "macos"
        elif current_os in ["Windows", "windows", "Win"]:
            os_label = "windows"
        else:
            print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Operating System: {current_os}")
            os_label = "unknown"
        print(f"{MSG_TAGS['INFO']}{step_name}Detected OS: {os_label}")
    return os_label


def get_arch(log_level=logging.INFO, step_name="", use_logger=True):
    """Return normalized system architecture (e.g., x64, arm64)"""
    if use_logger:
        with set_log_level(GV.LOGGER, log_level):
            current_arch = platform.machine()
            if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
                arch_label = "x64"
            elif current_arch in ["aarch64", "arm64", 'ARM64']:
                arch_label = "arm64"
            else:
                GV.LOGGER.error(f"{step_name}Unsupported Architecture: {current_arch}")
                arch_label = "unknown"
            GV.LOGGER.info(f"{step_name}Detected architecture: {arch_label}")
    else:
        current_arch = platform.machine()
        if current_arch in ["x86_64", "amd64", "AMD64", "X64", "x64"]:
            arch_label = "x64"
        elif current_arch in ["aarch64", "arm64", "ARM64"]:
            arch_label = "arm64"
        else:
            print(f"{MSG_TAGS['ERROR']}{step_name}Unsupported Architecture: {current_arch}")
            arch_label = "unknown"
        print(f"{MSG_TAGS['INFO']}{step_name}Detected architecture: {arch_label}")
    return arch_label


def check_OS_and_Terminal(log_level=None):
    """Check OS, terminal type, and system architecture."""
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Detect the operating system
        current_os = get_os(log_level=logging.WARNING)
        # Detect the machine architecture
        arch_label = get_arch(log_level=logging.WARNING)
        # OS logging
        if current_os == "linux":
            if run_from_synology():
                GV.LOGGER.info(f"Script running on Linux System in a Synology NAS")
            else:
                GV.LOGGER.info(f"Script running on Linux System")
        elif current_os == "macos":
            GV.LOGGER.info(f"Script running on MacOS System")
        elif current_os == "windows":
            GV.LOGGER.info(f"Script running on Windows System")
        else:
            GV.LOGGER.error(f"Unsupported Operating System: {current_os}")
        # Architecture logging
        GV.LOGGER.info(f"Detected architecture: {arch_label}")
        # Terminal type detection
        if sys.stdout.isatty():
            GV.LOGGER.info(f"Interactive (TTY) terminal detected for stdout")
        else:
            GV.LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdout")
        if sys.stdin.isatty():
            GV.LOGGER.info(f"Interactive (TTY) terminal detected for stdin")
        else:
            GV.LOGGER.info(f"Non-Interactive (Non-TTY) terminal detected for stdin")
        GV.LOGGER.info(f"")


def confirm_continue(log_level=None, force_prompt=False):
    """
    Asks the user whether to continue unless `request-user-confirmation` is disabled,
    unless prompting is explicitly forced for action previews.

    Args:
        log_level: Optional logging level override for this operation.
        force_prompt (bool): If True, ignore the global confirmation setting and always
            try to request interactive confirmation.

    Returns:
        bool: True to continue, False to cancel.
    """
    if not GV.ARGS.get('request-user-confirmation', True) and not force_prompt:
        return True

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        allow_stdin_pipe = os.environ.get("PHOTOMIGRATOR_ALLOW_STDIN_PIPE", "0") == "1"
        # In non-interactive environments (e.g. docker exec without -it), input() usually raises EOFError.
        # Allow opt-in stdin pipe mode for web interface mediated confirmations.
        if not sys.stdin.isatty() and not allow_stdin_pipe:
            GV.LOGGER.warning(
                "Confirmation requested but stdin is non-interactive (non-TTY). "
                "Use '--request-user-confirmation=false' to run in non-interactive mode."
            )
            return False

        GV.LOGGER.info("Awaiting user confirmation (yes/no)...")
        while True:
            try:
                # input(prompt) does not reliably flush its prompt when stdout
                # is redirected by the Web Interface or another job runner.
                print("Do you want to continue? (yes/no): ", end="", flush=True)
                response = input().strip().lower()
                print("")
            except EOFError:
                GV.LOGGER.warning(
                    "No input received (EOF). Use '--request-user-confirmation=false' "
                    "to run in non-interactive mode."
                )
                return False
            if response in ['yes', 'y']:
                GV.LOGGER.info(f"Continuing...")
                return True
            elif response in ['no', 'n']:
                GV.LOGGER.info(f"Operation canceled.")
                return False
            else:
                GV.LOGGER.warning(f"Invalid input. Please enter 'yes' or 'no'.")


def remove_quotes(input_string: str, log_level=logging.INFO) -> str:
    """
    Removes all single and double quotes at the start or end of the string.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        return input_string.strip('\'"')


def remove_server_name(path, log_level=None):
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Regular expression for Linux paths (///server/)
        path = re.sub(r'///[^/]+/', '///', path)
        # Regular expression for Windows paths (\\server\)
        path = re.sub(r'\\\\[^\\]+\\', '\\\\', path)
        return path


def get_unique_items(list1, list2, key='filename', log_level=None):
    """
    Returns items that are in list1 but not in list2 based on a specified key.

    Args:
        list1 (list): First list of dictionaries.
        list2 (list): Second list of dictionaries.
        key (str): Key to compare between both lists.

    Returns:
        list: Items present in list1 but not in list2.
        :param log_level:
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        set2 = {item[key] for item in list2}  # Create a set of filenames from list2
        unique_items = [item for item in list1 if item[key] not in set2]
        return unique_items


def update_metadata(file_path, date_time, log_level=None):
    """
    Updates the metadata of a file (image, video, etc.) to set the creation date.

    Args:
        file_path (str): Path to the file.
        date_time (str): Date and time in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        file_ext = os.path.splitext(file_path)[1].lower()
        try:
            if file_ext in PHOTO_EXT:
                update_exif_date(file_path, date_time, log_level=log_level)
            elif file_ext in VIDEO_EXT:
                update_video_metadata(file_path, date_time, log_level=log_level)
            GV.LOGGER.debug(f"Metadata updated for {file_path} with timestamp {date_time}")
        except Exception as e:
            GV.LOGGER.error(f"Failed to update metadata for {file_path}. {e}")


def update_file_timestamps(file_path, asset_time, log_level=None):
    """
    Updates filesystem timestamps for any local file.

    - Always updates file modified/accessed times through ``os.utime``.
    - Updates creation time on Windows via ``SetFileTime`` when possible.
    - Attempts to update creation time on macOS via ``SetFile`` when available.

    Args:
        file_path (str): Path to the file.
        asset_time (int | float | str): Timestamp in UNIX Epoch format or
            a string in ``YYYY-MM-DD HH:MM:SS`` format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):
        try:
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
                    return

            timestamp = float(asset_time)
            os.utime(file_path, (timestamp, timestamp))

            system_name = platform.system()
            if system_name == "Windows":
                try:
                    windows_time = int((timestamp + 11644473600) * 10000000)
                    handle = ctypes.windll.kernel32.CreateFileW(file_path, 256, 0, None, 3, 128, None)
                    if handle != -1:
                        ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ctypes.c_int64(windows_time)), None, None)
                        ctypes.windll.kernel32.CloseHandle(handle)
                except Exception as exc:
                    GV.LOGGER.warning(f"Failed to update file creation time on Windows. {exc}")
            elif system_name == "Darwin":
                setfile = shutil.which("SetFile")
                if setfile:
                    try:
                        mac_creation = datetime.fromtimestamp(timestamp).strftime("%m/%d/%Y %H:%M:%S")
                        subprocess.run([setfile, "-d", mac_creation, str(file_path)], check=False, capture_output=True, text=True)
                    except Exception as exc:
                        GV.LOGGER.warning(f"Failed to update file creation time on macOS. {exc}")
        except Exception as exc:
            GV.LOGGER.warning(f"Failed to update file timestamps for {file_path}. {exc}")


def update_exif_date(image_path, asset_time, log_level=None):
    """
    Updates the EXIF metadata of an image only when content date tags are missing.

    If any of these tags already exists, the function does not overwrite EXIF dates:
      - Exif.DateTimeOriginal
      - Exif.DateTimeDigitized
      - 0th.DateTime

    Args:
        image_path (str): Path to the image file.
        asset_time (int or str): Timestamp in UNIX Epoch format or a date string in "YYYY-MM-DD HH:MM:SS".
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # If asset_time is a string in 'YYYY-MM-DD HH:MM:SS' format, convert it to a UNIX timestamp
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError as e:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}. {e}")
                    return
            # Convert UNIX timestamp to EXIF format "YYYY:MM:DD HH:MM:SS"
            date_time_exif = datetime.fromtimestamp(asset_time).strftime("%Y:%m:%d %H:%M:%S")
            date_time_bytes = date_time_exif.encode('utf-8')
            # Backup original timestamps
            original_times = os.stat(image_path)
            original_atime = original_times.st_atime
            original_mtime = original_times.st_mtime
            # Load EXIF data or create an empty dict if no metadata exists
            try:
                exif_dict = piexif.load(image_path)
            except Exception:
                # GV.LOGGER.warning(f"No EXIF metadata found in {image_path}. Creating new EXIF data.")
                # exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
                GV.LOGGER.warning(f"No EXIF metadata found in {image_path}. Skipping it....")
                return

            def _tag_has_value(ifd_name, tag_id):
                value = exif_dict.get(ifd_name, {}).get(tag_id)
                if value is None:
                    return False
                if isinstance(value, bytes):
                    return value.strip() != b""
                if isinstance(value, str):
                    return value.strip() != ""
                return True

            # Do not overwrite existing EXIF content date tags.
            has_content_date = (
                _tag_has_value("Exif", piexif.ExifIFD.DateTimeOriginal) or
                _tag_has_value("Exif", piexif.ExifIFD.DateTimeDigitized) or
                _tag_has_value("0th", piexif.ImageIFD.DateTime)
            )
            if has_content_date:
                GV.LOGGER.debug(f"EXIF date tags already exist in '{image_path}'. Skipping EXIF date overwrite.")
                return

            # Fill content date tags only when all of them were missing.
            exif_dict.setdefault("0th", {})
            exif_dict.setdefault("Exif", {})
            exif_dict["0th"][piexif.ImageIFD.DateTime] = date_time_bytes
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_time_bytes
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_time_bytes
            # Validate and fix incorrect values before inserting
            for ifd_name in ["0th", "Exif"]:
                for tag, value in exif_dict.get(ifd_name, {}).items():
                    if isinstance(value, int):
                        exif_dict[ifd_name][tag] = str(value).encode('utf-8')
            try:
                # Dump and insert updated EXIF data
                exif_bytes = piexif.dump(exif_dict)
                piexif.insert(exif_bytes, image_path)
                # Restore original file timestamps
                os.utime(image_path, (original_atime, original_mtime))
                GV.LOGGER.debug(f"EXIF metadata updated for {image_path} with timestamp {date_time_exif}")
            except Exception:
                GV.LOGGER.error(f"Error when restoring original metadata to file: '{image_path}'")
                return
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update EXIF metadata for {image_path}. {e}")


def update_video_metadata(video_path, asset_time, log_level=None):
    """
    Updates the file system timestamps of a video file to set the creation and modification dates.

    This does NOT modify embedded metadata within the file, only the timestamps visible to the OS.

    Args:
        video_path (str): Path to the video file.
        asset_time (int | str): Timestamp in UNIX Epoch format or a string in 'YYYY-MM-DD HH:MM:SS' format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # Convert asset_time to UNIX timestamp if it's in string format
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
                    return
            # Convert timestamp to system format
            mod_time = asset_time
            create_time = asset_time
            # Update last modified and last accessed time (works on all OS)
            os.utime(video_path, (mod_time, mod_time))
            # Update file creation time (Windows only)
            if platform.system() == "Windows":
                try:
                    # Convert timestamp to Windows FILETIME format (100-nanosecond intervals since 1601-01-01)
                    windows_time = int((create_time + 11644473600) * 10000000)
                    # Open the file handle
                    handle = ctypes.windll.kernel32.CreateFileW(video_path, 256, 0, None, 3, 128, None)
                    if handle != -1:
                        ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ctypes.c_int64(windows_time)), None, None)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        GV.LOGGER.debug(f"DEBUG     : File creation time updated for {video_path}")
                except Exception as e:
                    GV.LOGGER.warning(f"Failed to update file creation time on Windows. {e}")
            GV.LOGGER.debug(f"File system timestamps updated for {video_path} with timestamp {datetime.fromtimestamp(mod_time)}")
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")


def update_video_metadata_with_ffmpeg(video_path, asset_time, log_level=None):
    """
    Updates the metadata of a video file to set the creation date without modifying file timestamps.

    Args:
        video_path (str): Path to the video file.
        asset_time (int): Timestamp in UNIX Epoch format.
        log_level (logging.LEVEL): log_level for logs and console
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            # If asset_time is a string in 'YYYY-MM-DD HH:MM:SS' format, convert it to a UNIX timestamp
            if isinstance(asset_time, str):
                try:
                    asset_time = datetime.strptime(asset_time, "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    GV.LOGGER.warning(f"Invalid date format for asset_time: {asset_time}")
                    return
            # Convert asset_time (UNIX timestamp) to format used by FFmpeg (YYYY-MM-DDTHH:MM:SS)
            formatted_date = datetime.fromtimestamp(asset_time).strftime("%Y-%m-%dT%H:%M:%S")
            # Backup original file timestamps
            original_times = os.stat(video_path)
            original_atime = original_times.st_atime
            original_mtime = original_times.st_mtime
            temp_file = video_path + "_temp.mp4"
            command = [
                "ffmpeg", "-i", video_path,
                "-metadata", f"creation_time={formatted_date}",
                "-metadata", f"modify_time={formatted_date}",
                "-metadata", f"date_time_original={formatted_date}",
                "-codec", "copy", temp_file
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            os.replace(temp_file, video_path)  # Replace original file with updated one
            # Restore original file timestamps
            os.utime(video_path, (original_atime, original_mtime))
            GV.LOGGER.debug(f"Video metadata updated for {video_path} with timestamp {formatted_date}")
        except Exception as e:
            GV.LOGGER.warning(f"Failed to update video metadata for {video_path}. {e}")


# Convert to list
def convert_to_list(input_string, log_level=None):
    """Convert a string to a list."""
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        try:
            output = input_string
            if isinstance(output, list):
                pass  # output is already a list
            elif isinstance(output, str):
                if ',' in output:
                    output = [item.strip() for item in output.split(',') if item.strip()]
                else:
                    output = [output.strip()] if output.strip() else []
            elif isinstance(output, (int, float)):
                output = [output]
            elif output is None:
                output = []
            else:
                output = [output]
        except Exception as e:
            GV.LOGGER.warning(f"Failed to convert string to List for {input_string}. {e}")

        return output


def convert_asset_ids_to_str(asset_ids):
    """Converts asset_ids to strings, even if it is a list containing different types."""
    if isinstance(asset_ids, list):
        return [str(item) for item in asset_ids]
    else:
        return [str(asset_ids)]


def sha1_checksum(file_path):
    """Computes the SHA-1 hash of a file and returns both HEX and Base64 formats."""
    sha1 = hashlib.sha1()  # Create a SHA-1 object

    with open(file_path, "rb") as f:  # Read the file in binary mode
        while chunk := f.read(8192):  # Read in 8 KB chunks for efficiency
            sha1.update(chunk)

    sha1_hex = sha1.hexdigest()  # Get HEX format
    sha1_base64 = base64.b64encode(sha1.digest()).decode("utf-8")  # Convert to Base64

    return sha1_hex, sha1_base64


def match_pattern(string, pattern):
    """
    Returns True if pattern matches the given string.
    Tries regex first, then glob, then literal matching.
    """
    text = str(string or "")
    expr = str(pattern or "")
    if not expr:
        return False
    try:
        if re.search(expr, text) is not None:
            return True
    except re.error:
        pass

    if fnmatch.fnmatch(text, expr):
        return True

    # Final fallback for "plain text" patterns that may contain regex metacharacters
    # (e.g. album names with parentheses).
    return re.search(re.escape(expr), text) is not None


def replace_pattern(string, pattern, pattern_to_replace):
    """
    Replaces occurrences of pattern in string.
    Tries regex replacement first; if no effective change, falls back to
    wildcard-aware and literal replacement.
    """
    text = str(string or "")
    expr = str(pattern or "")
    repl = str(pattern_to_replace or "")
    if not expr:
        return text

    simple_glob_candidate = False
    literal_chunks = []
    if "*" in expr and "?" not in expr and "[" not in expr and "]" not in expr:
        literal_chunks = [chunk for chunk in expr.split("*") if chunk]
        simple_glob_candidate = (
            len(literal_chunks) == 1
            and not any(ch in literal_chunks[0] for ch in ".^$+?{}[]\\|()")
        )

    # Prefer simple glob-like semantics over regex for patterns such as:
    #   *--* -> replace all inner `--`
    #   --*  -> replace leading `--`
    #   *--  -> replace trailing `--`
    if simple_glob_candidate:
        token = literal_chunks[0]
        anchored_start = not expr.startswith("*")
        anchored_end = not expr.endswith("*")
        if anchored_start and not anchored_end:
            replaced = re.sub(rf"^{re.escape(token)}", repl, text)
        elif not anchored_start and anchored_end:
            replaced = re.sub(rf"{re.escape(token)}$", repl, text)
        else:
            replaced = text.replace(token, repl)
        if replaced != text:
            return replaced

    try:
        replaced = re.sub(expr, repl, text)
    except re.error:
        replaced = text

    if replaced != text:
        return replaced

    if expr and expr in text:
        return text.replace(expr, repl)

    return text


def normalize_album_name_for_matching(name):
    """
    Build a conservative canonical representation for album-name matching.

    The goal is to treat harmless formatting differences as equivalent:
    - repeated/Unicode dashes
    - extra spaces
    - different date separators such as '.', '-', '_', '/'
    - different title separators such as '--', '—', '–', '_', ':'

    It intentionally collapses punctuation into spaces instead of doing broad
    fuzzy matching, so unrelated titles are less likely to collide.
    """
    text = str(name or "")
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    if not text:
        return ""
    text = re.sub(r"[‐‑‒–—−]+", "-", text)
    text = re.sub(r"(?<=\d)[\s._/\\-]+(?=\d)", " ", text)
    text = re.sub(r"[^0-9a-z]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_album_numeric_disambiguator(name):
    """
    Remove a trailing duplicate-style numeric suffix while trying to preserve
    meaningful year/date endings.

    Examples stripped:
      - "Album (1)" -> "Album"
      - "Album_3"   -> "Album"
      - "Album-12"  -> "Album"
      - "Album7"    -> "Album"
      - "Paris - Día 3" -> "Paris"
      - "Paris_Dia_2"   -> "Paris"
      - "Viaje Parte 1" -> "Viaje"
      - "Evento Sesión 4" -> "Evento"

    Examples preserved:
      - "Trip 2024"
      - "2015-10-17 - Boda"
    """
    text = str(name or "").strip()
    if not text:
        return ""

    semantic_series_match = re.match(
        r"^(.*?)(?:[\s_\-]+)?"
        r"(?:"
        r"day|jour|giorno|tag|dia|d[ií]a|"
        r"part|parte|teil|parte|"
        r"session|sesion|sesi[oó]n|sessione|sessao|sess[aã]o|sitzung"
        r")"
        r"(?:[\s_\-]+)(\d+)\s*$",
        text,
        flags=re.IGNORECASE,
    )
    if semantic_series_match:
        base = str(semantic_series_match.group(1) or "").rstrip(" _-")
        if base:
            return base

    match = re.match(r"^(.*?)(?:\s*\((\d+)\)|([_\-]+)(\d+)|(\d+))\s*$", text)
    if not match:
        return text

    base = str(match.group(1) or "").rstrip(" _-")
    paren_digits = match.group(2)
    separator_digits = match.group(4)
    attached_digits = match.group(5)
    digits = paren_digits or separator_digits or attached_digits or ""
    if not digits:
        return text

    # Preserve common year-like endings to avoid collapsing legitimate albums
    # such as "Trip 2024" into "Trip" when the year is part of the title.
    if len(digits) == 4 and 1900 <= int(digits) <= 2100:
        return text

    return base or text


def canonicalize_album_name_for_reuse(name):
    text = strip_album_numeric_disambiguator(name)
    text = re.sub(r"_+", " ", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def album_name_reuse_key(name):
    return normalize_album_name_for_matching(canonicalize_album_name_for_reuse(name))


def album_name_preference_key(name):
    raw = str(name or "").strip()
    canonical = canonicalize_album_name_for_reuse(raw)
    stripped = strip_album_numeric_disambiguator(raw)
    has_numeric_suffix = canonicalize_album_name_for_reuse(raw) != re.sub(r"\s+", " ", raw.replace("_", " ")).strip()
    underscore_count = raw.count("_")
    punctuation_penalty = len(re.findall(r"[()]", raw))
    return (
        1 if has_numeric_suffix else 0,
        underscore_count,
        punctuation_penalty,
        len(canonical or raw),
        normalize_album_name_for_matching(canonical or raw),
    )


def prefer_canonical_album_names_enabled(args=None):
    params = args if isinstance(args, dict) else GV.ARGS
    return bool((params or {}).get("prefer-canonical-album-names", False))


def consolidate_similar_albums_enabled(args=None):
    params = args if isinstance(args, dict) else GV.ARGS
    return bool((params or {}).get("consolidate-similar-albums", False))


def _build_reusable_album_group_from_matches(target_name, exact_matches, similar_matches, allow_similar=False):
    target_name = str(target_name or "").strip()
    similarity_key = album_name_reuse_key(target_name)
    preferred_target_name = target_name
    if allow_similar and target_name:
        normalized_target_name = canonicalize_album_name_for_reuse(target_name)
        preferred_target_name = min(
            [name for name in [target_name, normalized_target_name] if name],
            key=album_name_preference_key,
        )
    empty_result = {
        "matched_album": None,
        "keeper_album": None,
        "match_kind": None,
        "ambiguous_matches": [],
        "similar_albums": [],
        "redundant_albums": [],
        "preferred_album_name": preferred_target_name,
        "similarity_key": album_name_reuse_key(target_name),
        "should_create_preferred_album": bool(preferred_target_name and preferred_target_name.casefold() != target_name.casefold()),
    }
    if not target_name:
        return empty_result

    group_albums = exact_matches or similar_matches
    if not exact_matches and not allow_similar:
        return empty_result
    if not group_albums:
        return empty_result

    # When similar-album consolidation is enabled, choose the preferred keeper
    # name from the whole reusable family, not only from the exact seed match.
    # Otherwise a seed such as "Album(1)" would incorrectly keep the suffixed
    # name even if a clean "Album" already exists in the same family.
    preferred_group_albums = similar_matches if (allow_similar and similar_matches) else group_albums

    name_candidates = [target_name] + [str((album or {}).get("albumName", "")).strip() for album in preferred_group_albums]
    if allow_similar and prefer_canonical_album_names_enabled():
        name_candidates.extend(
            canonicalize_album_name_for_reuse(name)
            for name in list(name_candidates)
            if str(name or "").strip()
        )
    name_candidates = [name for name in name_candidates if name]
    preferred_album_name = min(name_candidates, key=album_name_preference_key) if name_candidates else target_name

    keeper_album = None
    keeper_sort_key = None
    for album in preferred_group_albums:
        candidate_name = str((album or {}).get("albumName", "")).strip()
        candidate_key = (
            0 if candidate_name.casefold() == preferred_album_name.casefold() else 1,
            album_name_preference_key(candidate_name),
        )
        if keeper_sort_key is None or candidate_key < keeper_sort_key:
            keeper_sort_key = candidate_key
            keeper_album = album

    should_create_preferred_album = True
    if keeper_album:
        keeper_name = str((keeper_album or {}).get("albumName", "")).strip()
        should_create_preferred_album = keeper_name.casefold() != preferred_album_name.casefold()

    redundant_albums = []
    if keeper_album and similar_matches:
        keeper_id = str((keeper_album or {}).get("id", "")).strip()
        redundant_albums = [
            album for album in similar_matches
            if str((album or {}).get("id", "")).strip() != keeper_id
        ]

    match_kind = "exact" if exact_matches else ("similar" if similar_matches else None)
    result = dict(empty_result)
    result.update({
        "matched_album": exact_matches[0] if exact_matches else (keeper_album if similar_matches else None),
        "keeper_album": keeper_album,
        "match_kind": match_kind,
        "ambiguous_matches": [] if len(similar_matches) <= 1 else list(similar_matches),
        "similar_albums": list(similar_matches),
        "redundant_albums": redundant_albums,
        "preferred_album_name": preferred_album_name,
        "similarity_key": similarity_key,
        "should_create_preferred_album": should_create_preferred_album,
    })
    return result


def build_reusable_album_group(album_name, albums, allow_similar=False, exact_case_sensitive=False):
    """
    Returns a reusable-album plan with preferred keeper naming information.

    Result keys:
      - matched_album
      - keeper_album
      - match_kind
      - ambiguous_matches
      - similar_albums
      - redundant_albums
      - preferred_album_name
      - similarity_key
      - should_create_preferred_album
    """
    target_name = str(album_name or "").strip()
    if not target_name:
        return _build_reusable_album_group_from_matches(
            target_name="",
            exact_matches=[],
            similar_matches=[],
            allow_similar=allow_similar,
        )

    exact_matches = []
    target_casefold = target_name.casefold()
    for album in albums or []:
        candidate_name = str((album or {}).get("albumName", "")).strip()
        if not candidate_name:
            continue
        if exact_case_sensitive:
            if candidate_name == target_name:
                exact_matches.append(album)
        else:
            if candidate_name.casefold() == target_casefold:
                exact_matches.append(album)

    similar_matches = []
    similarity_key = album_name_reuse_key(target_name)
    if allow_similar and similarity_key:
        for album in albums or []:
            candidate_name = str((album or {}).get("albumName", "")).strip()
            if not candidate_name:
                continue
            if album_name_reuse_key(candidate_name) == similarity_key:
                similar_matches.append(album)
    return _build_reusable_album_group_from_matches(
        target_name=target_name,
        exact_matches=exact_matches,
        similar_matches=similar_matches,
        allow_similar=allow_similar,
    )


_ALBUM_DATE_PREFIX_RE = re.compile(
    r"^\s*(?P<year>\d{4})"
    r"(?:[._\-\u2010-\u2015]+(?P<month>0[1-9]|1[0-2]))?"
    r"(?:[._\-\u2010-\u2015]+(?P<day>0[1-9]|[12]\d|3[01]))?"
    r"\s*(?:[._\-\u2010-\u2015]{1,})\s*(?P<title>.+?)\s*$"
)
_ALBUM_DATE_ONLY_RE = re.compile(
    r"^\d{4}(?:[._\-\u2010-\u2015\s]+\d{1,2}){0,2}$"
)
_ALBUM_LEADING_DATE_RE = re.compile(
    r"^\d{4}(?:[._\-\u2010-\u2015\s]+\d{1,2}){0,2}\s*(?:[._\-\u2010-\u2015]+\s*)?"
)
_ALBUM_SPECIAL_SUFFIX_RE = re.compile(
    r"(?:\s|\()(?P<suffix>(?:sh(?:a(?:r(?:e(?:d)?)?)?)?)|(?:pub(?:l(?:i(?:c(?:o)?)?)?)?)|p(?:u|\u00fa)(?:b(?:l(?:i(?:c(?:o)?)?)?)?)|priv(?:a(?:d(?:o|a)?)?|at(?:e)?)?|selec(?:c(?:i(?:o(?:n)?)?)?)?|select(?:i(?:o(?:n)?)?)?|x)\)?\s*$",
    re.IGNORECASE,
)
_ALBUM_VIDEOS_SUFFIX_RE = re.compile(r"(?:^|[\s()_\-]+)videos\s*$", re.IGNORECASE)
_ALBUM_LEADING_YEAR_RANGE_RE = re.compile(
    r"^\s*(?P<start>\d{4})\s*[._\-\u2010-\u2015]+\s*(?P<end>\d{4})\s*(?:[._\-\u2010-\u2015]+\s*)",
)
_ALBUM_TRAILING_DATE_RE = re.compile(
    r"(?:\s|\(|[_\-]+)(?P<year>\d{4})"
    r"(?:[._\-\u2010-\u2015]+(?P<month>0[1-9]|1[0-2]))?"
    r"(?:[._\-\u2010-\u2015]+(?P<day>0[1-9]|[12]\d|3[01]))?\)?\s*$"
)


def _album_date_prefix(name):
    """Return a normalized date prefix and title for date-led album names."""
    match = _ALBUM_DATE_PREFIX_RE.match(str(name or ""))
    if not match:
        return None
    year = int(match.group("year"))
    month = int(match.group("month")) if match.group("month") else None
    day = int(match.group("day")) if match.group("day") else None
    title = str(match.group("title") or "").strip()
    title_key = album_name_reuse_key(title) or title.casefold()
    if not title_key:
        return None
    return {"year": year, "month": month, "day": day, "precision": 1 + int(month is not None) + int(day is not None), "title_key": title_key}


def _dates_are_compatible(left, right):
    """A less precise date contains a more precise date when known fields agree."""
    return (
        left["year"] == right["year"]
        and (left["month"] is None or right["month"] is None or left["month"] == right["month"])
        and (left["day"] is None or right["day"] is None or left["day"] == right["day"])
    )


def _album_truncation_key(name):
    normalized = unicodedata.normalize("NFKD", str(name or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char)).casefold().strip()
    suffix_match = _ALBUM_SPECIAL_SUFFIX_RE.search(normalized)
    special_suffix = ""
    if suffix_match:
        suffix_text = str(suffix_match.group("suffix") or "").casefold()
        if suffix_text.startswith("sh"):
            special_suffix = "shared"
        elif suffix_text.startswith("pub") or suffix_text.startswith("p\u00fab"):
            special_suffix = suffix_text
        elif suffix_text.startswith("priv"):
            special_suffix = suffix_text
        elif suffix_text.startswith("selec") or suffix_text.startswith("select"):
            special_suffix = suffix_text
        else:
            special_suffix = suffix_text
        normalized = normalized[:suffix_match.start()].strip(" ()-_.")
    normalized = re.sub(r"\s+", " ", normalized)
    # A bare date (including a trailing separator) is not a truncated album
    # title. Otherwise an album named "2015" matches every 2015-prefixed
    # album and can collapse an entire year into one family.
    if _ALBUM_DATE_ONLY_RE.fullmatch(normalized.strip(" ()-_.")):
        return "", special_suffix
    return normalized, special_suffix


def _has_meaningful_truncation_prefix(left_key, right_key):
    """Require two distinct components in the shared truncation prefix."""
    short_key = left_key if len(left_key) <= len(right_key) else right_key
    title_prefix = _ALBUM_LEADING_DATE_RE.sub("", short_key).strip(" ()-_.")
    words = re.findall(r"[^\W\d_]+", title_prefix, flags=re.UNICODE)
    distinct_words = {word.casefold() for word in words}
    if len(distinct_words) >= 2:
        return True
    # A valid leading date is a meaningful independent component. The later
    # dominant-asset-year check remains mandatory before a group is created.
    return len(distinct_words) == 1 and _album_date_prefix(short_key) is not None


def _is_videos_album_variant(album):
    name = unicodedata.normalize("NFKD", str((album or {}).get("albumName", "")))
    name = "".join(char for char in name if not unicodedata.combining(char)).casefold().strip()
    return bool(_ALBUM_VIDEOS_SUFFIX_RE.search(name))


def _has_redundant_terminal_date(album):
    """Return whether an album repeats its leading date at the end of its name."""
    name = str((album or {}).get("albumName", "")).strip()
    trailing_match = _ALBUM_TRAILING_DATE_RE.search(name)
    if not trailing_match:
        return False

    trailing_year = int(trailing_match.group("year"))
    trailing_month = trailing_match.group("month")
    trailing_day = trailing_match.group("day")
    range_match = _ALBUM_LEADING_YEAR_RANGE_RE.match(name)
    if range_match:
        # A year inside an explicit leading range, such as 2019-2021, is a
        # redundant suffix only when it does not claim a more specific date.
        return (
            trailing_month is None
            and trailing_day is None
            and int(range_match.group("start")) <= trailing_year <= int(range_match.group("end"))
        )

    leading_date = _album_date_prefix(name)
    if not leading_date or trailing_year != leading_date["year"]:
        return False
    if trailing_month is not None and int(trailing_month) != leading_date["month"]:
        return False
    return trailing_day is None or int(trailing_day) == leading_date["day"]


def _dominant_asset_year(asset_years):
    years = [year for year in (asset_years or []) if isinstance(year, int) and 1000 <= year <= 9999]
    if not years:
        return None
    counts = {}
    for year in years:
        counts[year] = counts.get(year, 0) + 1
    year, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    return year if count > len(years) / 2 else None


def extract_asset_capture_years(assets):
    """Extract a best-effort capture year from cloud asset payloads."""
    years = []
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        metadata = asset.get("mediaMetadata") or {}
        raw_value = (
            asset.get("fileCreatedAt")
            or asset.get("asset_datetime")
            or asset.get("time")
            or metadata.get("creationTime")
        )
        try:
            if isinstance(raw_value, (int, float)) or (isinstance(raw_value, str) and raw_value.strip().isdigit()):
                parsed = datetime.fromtimestamp(float(raw_value))
            else:
                parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
            years.append(parsed.year)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
    return years


def extract_asset_capture_datetimes(assets):
    """Extract best-effort capture datetimes using the shared cloud payload fields."""
    dates = []
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        metadata = asset.get("mediaMetadata") or {}
        raw_value = (
            asset.get("fileCreatedAt")
            or asset.get("asset_datetime")
            or asset.get("time")
            or metadata.get("creationTime")
        )
        try:
            if isinstance(raw_value, (int, float)) or (isinstance(raw_value, str) and raw_value.strip().isdigit()):
                parsed = datetime.fromtimestamp(float(raw_value))
            else:
                parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
            dates.append(parsed)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
    return dates


def _build_direct_consolidation_group(members, keeper_album, reason):
    keeper_id = str((keeper_album or {}).get("id", "")).strip()
    keeper_name = str((keeper_album or {}).get("albumName", "")).strip()
    return {
        "seed_album_name": keeper_name,
        "preferred_album_name": keeper_name,
        "keeper_album": keeper_album,
        "should_create_preferred_album": False,
        "redundant_albums": [
            album for album in members
            if str((album or {}).get("id", "")).strip() != keeper_id
        ],
        "similar_albums": list(members),
        "similarity_key": f"{reason}:{keeper_id}",
        "reason": reason,
        "assets_date_considered": False,
        "comment": "",
        "album_comments": {},
    }


_DATE_PREFIX_ASSET_COVERAGE_THRESHOLD = 0.95


def _asset_dates_fit_date_prefix(asset_dates, date_prefix):
    if not asset_dates:
        return False
    matching_assets = sum(
        captured.year == date_prefix["year"]
        and (date_prefix["month"] is None or captured.month == date_prefix["month"])
        and (date_prefix["day"] is None or captured.day == date_prefix["day"])
        for captured in asset_dates
    )
    return (matching_assets / len(asset_dates)) >= _DATE_PREFIX_ASSET_COVERAGE_THRESHOLD


def _scan_date_prefix_consolidation_groups(
    albums,
    excluded_ids,
    asset_dates_getter=None,
    progress_desc=None,
    progress_unit="families",
):
    by_title = {}
    for album in albums:
        album_id = str((album or {}).get("id", "")).strip()
        if not album_id or album_id in excluded_ids:
            continue
        parsed = _album_date_prefix((album or {}).get("albumName"))
        if parsed:
            by_title.setdefault(parsed["title_key"], []).append((album, parsed))

    date_families = []
    for variants in by_title.values():
        by_year = {}
        for album, parsed in variants:
            by_year.setdefault(parsed["year"], []).append((album, parsed))
        date_families.extend(by_year.values())

    groups = []
    families_iterable = (
        tqdm(date_families, desc=progress_desc, unit=progress_unit)
        if progress_desc else date_families
    )
    for year_variants in families_iterable:
        if len(year_variants) < 2:
            continue
        most_precise = max(parsed["precision"] for _, parsed in year_variants)
        precise_variants = [(album, parsed) for album, parsed in year_variants if parsed["precision"] == most_precise]
        compatible_precise = [
            (album, parsed) for album, parsed in precise_variants
            if all(_dates_are_compatible(parsed, other) for _, other in year_variants)
        ]
        if not compatible_precise:
            # A generic year cannot safely bridge conflicting months/days.
            continue
        keeper_album, keeper_date = max(
            compatible_precise,
            key=lambda item: (item[1]["precision"], len(str((item[0] or {}).get("albumName", ""))), str((item[0] or {}).get("albumName", "")).casefold()),
        )
        members = [(album, parsed) for album, parsed in year_variants if _dates_are_compatible(parsed, keeper_date)]
        broadest_precision = min(parsed["precision"] for _, parsed in members)
        assets_date_considered = False
        comment = "Compatible date prefixes"
        if keeper_date["precision"] > broadest_precision and callable(asset_dates_getter):
            assets_date_considered = True
            try:
                precise_dates = asset_dates_getter(keeper_album)
            except Exception as exc:
                if GV.LOGGER:
                    GV.LOGGER.warning(
                        f"Unable to inspect capture dates for album "
                        f"'{(keeper_album or {}).get('albumName', '')}': {exc}"
                    )
                precise_dates = []
            if not _asset_dates_fit_date_prefix(precise_dates, keeper_date):
                comment = "Specific date covers <95% of asset dates"
                broad_candidates = [
                    (album, parsed) for album, parsed in members
                    if parsed["precision"] == broadest_precision
                ]
                keeper_album, keeper_date = max(
                    broad_candidates,
                    key=lambda item: (
                        len(str((item[0] or {}).get("albumName", ""))),
                        str((item[0] or {}).get("albumName", "")).casefold(),
                    ),
                    )
            else:
                comment = "Specific date covers >=95% of asset dates"
        member_albums = [album for album, _ in members]
        if len(member_albums) > 1:
            group = _build_direct_consolidation_group(member_albums, keeper_album, "date-prefix")
            group["assets_date_considered"] = assets_date_considered
            group["comment"] = comment
            if comment != "Compatible date prefixes":
                group["album_comments"] = {
                    str((album or {}).get("id", "")).strip(): comment
                    for album in group["redundant_albums"]
                }
            groups.append(group)
    return groups


def _scan_truncated_name_consolidation_groups(
    albums,
    excluded_ids,
    asset_years_getter=None,
    progress_desc=None,
    progress_unit="albums",
):
    if not callable(asset_years_getter):
        return []
    candidates = []
    for album in albums:
        album_id = str((album or {}).get("id", "")).strip()
        name = str((album or {}).get("albumName", "")).strip()
        if not album_id or album_id in excluded_ids or len(name) < 4:
            continue
        key, special_suffix = _album_truncation_key(name)
        if len(key) >= 4:
            candidates.append((album, key, special_suffix))

    groups = []
    used_ids = set()
    candidates_iterable = (
        tqdm(candidates, desc=progress_desc, unit=progress_unit)
        if progress_desc else candidates
    )
    for index, (album, key, special_suffix) in enumerate(candidates_iterable):
        album_id = str((album or {}).get("id", "")).strip()
        if album_id in used_ids:
            continue
        matches = [album]
        for other_album, other_key, other_special_suffix in candidates[index + 1:]:
            other_id = str((other_album or {}).get("id", "")).strip()
            if other_id in used_ids or special_suffix != other_special_suffix:
                continue
            if min(len(key), len(other_key)) < 4 or not (key.startswith(other_key) or other_key.startswith(key)):
                continue
            if not _has_meaningful_truncation_prefix(key, other_key):
                continue
            matches.append(other_album)
        if len(matches) < 2:
            continue

        dominant_years = {}
        for candidate in matches:
            candidate_id = str((candidate or {}).get("id", "")).strip()
            try:
                dominant_years[candidate_id] = _dominant_asset_year(asset_years_getter(candidate))
            except Exception as exc:
                if GV.LOGGER:
                    GV.LOGGER.warning(f"Unable to inspect asset years for album '{(candidate or {}).get('albumName', '')}': {exc}")
                dominant_years[candidate_id] = None
        by_dominant_year = {}
        for candidate in matches:
            candidate_id = str((candidate or {}).get("id", "")).strip()
            year = dominant_years.get(candidate_id)
            if year is not None:
                by_dominant_year.setdefault(year, []).append(candidate)
        for same_year_matches in by_dominant_year.values():
            if len(same_year_matches) < 2:
                continue
            keeper_album = max(
                same_year_matches,
                key=lambda item: (
                    not _has_redundant_terminal_date(item),
                    not _is_videos_album_variant(item),
                    len(str((item or {}).get("albumName", ""))),
                    str((item or {}).get("albumName", "")).casefold(),
                ),
            )
            if (
                any(_has_redundant_terminal_date(candidate) for candidate in same_year_matches)
                and any(not _has_redundant_terminal_date(candidate) for candidate in same_year_matches)
            ):
                reason = "truncated-name-redundant-date"
            elif (
                any(_is_videos_album_variant(candidate) for candidate in same_year_matches)
                and any(not _is_videos_album_variant(candidate) for candidate in same_year_matches)
            ):
                reason = "truncated-name-grouping-videos"
            else:
                reason = "truncated-name"
            group = _build_direct_consolidation_group(same_year_matches, keeper_album, reason)
            group["album_comments"] = {
                str((candidate or {}).get("id", "")).strip(): (
                    "; ".join(
                        comment for comment in (
                            "Video Grouping" if _is_videos_album_variant(candidate) else "",
                            "Redundant Ending Date" if _has_redundant_terminal_date(candidate) else "",
                        ) if comment
                    )
                    or "Longest name selected"
                ) + " (Dominant assets year matched)"
                for candidate in group["redundant_albums"]
            }
            groups.append(group)
            used_ids.update(str((candidate or {}).get("id", "")).strip() for candidate in same_year_matches)
    return groups


def scan_album_consolidation_groups(albums, exact_case_sensitive=False, date_getter=None, progress_desc=None, progress_unit="albums", asset_years_getter=None, asset_dates_getter=None, asset_count_getter=None, include_asset_counts=False):
    """
    Build consolidation groups for cloud album-name consolidation in one pass.

    This avoids recalculating the full reusable-group plan for every album,
    which otherwise turns the scan into an O(n^2) operation.
    """
    eligible_albums = []
    similarity_groups = {}
    exact_groups = {}

    for album in albums or []:
        if callable(date_getter) and is_date_outside_range(date_getter(album)):
            continue
        album_name = str((album or {}).get("albumName", "")).strip()
        if not album_name:
            continue
        eligible_albums.append(album)
        similarity_key = album_name_reuse_key(album_name) or album_name.casefold()
        similarity_groups.setdefault(similarity_key, []).append(album)
        exact_key = album_name if exact_case_sensitive else album_name.casefold()
        exact_groups.setdefault(exact_key, []).append(album)

    consolidation_groups = []
    seen_similarity_keys = set()

    progress_iterable = tqdm(eligible_albums, desc=progress_desc, unit=progress_unit) if progress_desc else eligible_albums
    for album in progress_iterable:
        album_name = str((album or {}).get("albumName", "")).strip()
        try:
            similarity_key = album_name_reuse_key(album_name) or album_name.casefold()
            if similarity_key in seen_similarity_keys:
                continue
            seen_similarity_keys.add(similarity_key)

            exact_key = album_name if exact_case_sensitive else album_name.casefold()
            plan = _build_reusable_album_group_from_matches(
                target_name=album_name,
                exact_matches=list(exact_groups.get(exact_key) or []),
                similar_matches=list(similarity_groups.get(similarity_key) or []),
                allow_similar=True,
            )
            redundant_albums = list(plan.get("redundant_albums") or [])
            if not redundant_albums:
                continue
            consolidation_groups.append({
                "seed_album_name": album_name,
                "preferred_album_name": str(plan.get("preferred_album_name") or album_name).strip() or album_name,
                "keeper_album": plan.get("keeper_album") or {},
                "should_create_preferred_album": bool(plan.get("should_create_preferred_album")),
                "redundant_albums": redundant_albums,
                "similar_albums": list(plan.get("similar_albums") or []),
                "similarity_key": similarity_key,
            })
        except Exception as exc:
            if GV.LOGGER:
                GV.LOGGER.exception(
                    f"Album family scan failed for album '{album_name or '<empty>'}'. Error: {exc}"
                )
            raise

    # Keep the established canonical-name groups untouched, then add only new
    # date-prefix/truncation families that do not overlap an existing plan.
    assigned_ids = {
        str((album or {}).get("id", "")).strip()
        for group in consolidation_groups
        for album in (group.get("similar_albums") or [])
    }
    asset_dates_cache = {}

    def cached_asset_dates(album):
        album_id = str((album or {}).get("id", "")).strip()
        if not callable(asset_dates_getter):
            return []
        if album_id not in asset_dates_cache:
            asset_dates_cache[album_id] = list(asset_dates_getter(album) or [])
        return asset_dates_cache[album_id]

    def cached_asset_years(album):
        if callable(asset_dates_getter):
            return [captured.year for captured in cached_asset_dates(album)]
        return asset_years_getter(album) if callable(asset_years_getter) else []

    # Consolidation clients run their inner API work at WARNING. Write phase
    # transitions directly so a long metadata scan never appears stalled.
    print(f"{MSG_TAGS['INFO']}Scanning date-prefixed album families to consolidate...")
    date_groups = _scan_date_prefix_consolidation_groups(
        eligible_albums,
        assigned_ids,
        asset_dates_getter=cached_asset_dates if callable(asset_dates_getter) else None,
        progress_desc=f"{MSG_TAGS['INFO']}Checking date-prefixed album families",
        progress_unit="families",
    )
    assigned_ids.update(
        str((album or {}).get("id", "")).strip()
        for group in date_groups
        for album in (group.get("similar_albums") or [])
    )
    if callable(asset_years_getter) or callable(asset_dates_getter):
        print(
            f"{MSG_TAGS['INFO']}Checking truncated album-name candidates and their dominant asset years. "
            "This may require reading assets from matching albums..."
        )
        truncation_groups = _scan_truncated_name_consolidation_groups(
            eligible_albums,
            assigned_ids,
            asset_years_getter=cached_asset_years,
            progress_desc=f"{MSG_TAGS['INFO']}Checking truncated album-name candidates",
            progress_unit=progress_unit,
        )
    else:
        truncation_groups = []
    groups = consolidation_groups + date_groups + truncation_groups
    if include_asset_counts and callable(asset_count_getter) and groups:
        counted_albums = {}
        albums_to_count = {}
        for group in groups:
            keeper = group.get("keeper_album") or {}
            if keeper.get("id"):
                albums_to_count[str(keeper["id"])] = keeper
            for candidate in group.get("redundant_albums") or []:
                if candidate.get("id"):
                    albums_to_count[str(candidate["id"])] = candidate
        for album_id, album in tqdm(
            albums_to_count.items(),
            desc=f"{MSG_TAGS['INFO']}Counting assets in album consolidation preview",
            unit="albums",
        ):
            try:
                counted_albums[album_id] = max(0, int(asset_count_getter(album) or 0))
            except Exception:
                counted_albums[album_id] = 0
        for album_id, album in albums_to_count.items():
            album["_consolidation_asset_count"] = counted_albums[album_id]
    return groups


def print_album_consolidation_preview(consolidation_groups):
    groups = list(consolidation_groups or [])
    redundant_total = sum(len(group.get("redundant_albums") or []) for group in groups)

    def emit(message):
        # Consolidation runs the client with a WARNING log threshold.  Preview
        # output must bypass that threshold so it remains visible before the
        # confirmation prompt. Persist it explicitly as INFO as well because
        # that thread-local threshold would otherwise suppress FileHandlers.
        print(f"{MSG_TAGS['INFO']}{message}")
        logger = GV.LOGGER
        if not logger:
            return
        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            __file__,
            0,
            message,
            (),
            None,
        )
        for handler in list(getattr(logger, "handlers", []) or []):
            if isinstance(handler, logging.FileHandler):
                handler.handle(record)

    def album_name(album):
        if isinstance(album, dict):
            name = str(album.get("albumName", "")).strip()
            count = album.get("_consolidation_asset_count")
            return f"{name} [{count} assets]" if count is not None else name
        return str(album or "").strip()

    emit(
        f"Album consolidation preview: {len(groups)} family(ies), "
        f"{redundant_total} album(s) scheduled to merge."
    )
    table_data = []
    for group_number, group in enumerate(groups, start=1):
        keeper_name = (
            group.get("preferred_album_name")
            if group.get("should_create_preferred_album")
            else (
                album_name(group.get("keeper_album") or {})
                or str(group.get("preferred_album_name") or "").strip()
            )
        )
        redundant_albums = [
            album for album in (group.get("redundant_albums") or [])
            if album_name(album)
        ]
        redundant_album_names = [album_name(album) for album in redundant_albums]
        reason_key = str(group.get("reason") or "equivalent-name")
        reason = (
            "Truncated Name"
            if reason_key.startswith("truncated-name")
            else reason_key.replace("-", " ").title()
        )
        album_comments = group.get("album_comments") or {}
        comments = "\n".join(
            str(album_comments.get(str((album or {}).get("id", "")).strip(), "")) or "-"
            for album in redundant_albums
        )
        table_data.append([
            f"{group_number}/{len(groups)}",
            keeper_name,
            "\n".join(redundant_album_names),
            reason,
            comments,
        ])

    preview_table = tabulate(
        table_data,
        headers=["Group", "Album Keeper", "Albums to Merge", "Match Rule", "Comments"],
        tablefmt="grid",
    )
    for line in preview_table.splitlines():
        emit(line)


def find_reusable_album_candidate(album_name, albums, allow_similar=False, exact_case_sensitive=False):
    """
    Resolve an existing album candidate from a list of album dicts.

    Returns:
        tuple: (matched_album_or_none, match_kind, ambiguous_candidates)
            match_kind is one of: "exact", "similar", None
    """
    plan = build_reusable_album_group(
        album_name=album_name,
        albums=albums,
        allow_similar=allow_similar,
        exact_case_sensitive=exact_case_sensitive,
    )
    ambiguous_matches = plan.get("ambiguous_matches", [])
    if ambiguous_matches:
        return None, None, ambiguous_matches
    return plan.get("matched_album"), plan.get("match_kind"), []


def has_any_filter():
    """
    Returns True if any filtering argument is enabled in GV.ARGS.
    """
    filter_by_type = GV.ARGS.get('filter-by-type', None)
    if isinstance(filter_by_type, str) and filter_by_type.strip().lower() == "all":
        filter_by_type = None
    return filter_by_type or GV.ARGS.get('filter-from-date', None) or GV.ARGS.get('filter-to-date', None) or GV.ARGS.get('filter-by-country', None) or GV.ARGS.get('filter-by-city', None) or GV.ARGS.get('filter-by-person', None)


def get_filters():
    """
    Collects filter-related arguments from GV.ARGS into a dictionary.

    Returns:
        dict: Dictionary containing the filter keys and their current values.
    """
    filters = {}
    keys = [
        'filter-by-type',
        'filter-from-date',
        'filter-to-date',
        'filter-by-country',
        'filter-by-city',
        'filter-by-person',
    ]
    for key in keys:
        filters[key] = GV.ARGS.get(key)
    return filters


def capitalize_first_letter(text):
    """
    Capitalizes the first character of a string (if any).

    Args:
        text (str): Input string.

    Returns:
        str: Same string with the first character uppercased.
    """
    if not text:
        return text
    return text[0].upper() + text[1:]


def get_subfolders_with_exclusions(input_folder, exclude_subfolders=None):
    """
    Returns the list of direct subfolders inside `input_folder`,
    excluding those provided in `exclude_subfolders`.
    If `input_folder` does not exist or is not a directory, it returns an empty list.
    """
    if not os.path.isdir(input_folder):
        return []

    if exclude_subfolders is None:
        exclude = set()
    elif isinstance(exclude_subfolders, str):
        exclude = {exclude_subfolders}
    else:
        exclude = set(exclude_subfolders)

    return [
        entry
        for entry in os.listdir(input_folder)
        if os.path.isdir(os.path.join(input_folder, entry)) and entry not in exclude
    ]


def print_dict_pretty(result, log_level=logging.INFO):
    """
    Pretty-prints a dict (or dataclass) as aligned key/value pairs using GV.LOGGER if available.

    Args:
        result (dict | dataclass): Dictionary or dataclass to print.
        log_level (int): Logging level to use when printing via logger.

    Raises:
        TypeError: If `result` is not a dict or a dataclass.
    """
    # If it is a dataclass, convert it to a dict
    if is_dataclass(result):
        result = asdict(result)
    # Ensure it is now a dict
    if not isinstance(result, dict):
        raise TypeError(f"Expected dict or dataclass, but got {type(result).__name__}")

    # Try to get the logger
    logger = getattr(GV, "LOGGER", None)

    # If there is no logger, print to stdout
    if logger is None:
        for key, value in result.items():
            print(f"{key:35}: {value}")
        return

    # Print using the corresponding log level
    for key, value in result.items():
        if log_level == VERBOSE_LEVEL_NUM:
            logger.verbose(f"{key:35}: {value}")
        elif log_level == logging.DEBUG:
            logger.debug(f"{key:35}: {value}")
        elif log_level == logging.INFO:
            logger.info(f"{key:35}: {value}")
        elif log_level == logging.WARNING:
            logger.warning(f"{key:35}: {value}")
        elif log_level == logging.ERROR:
            logger.error(f"{key:35}: {value}")


def timed_subprocess(cmd, step_name=""):
    """
    Runs cmd with Popen, waits for it to finish, and logs only
    the total execution time at the end.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.time()
    out, err = proc.communicate()
    total = time.time() - start
    GV.LOGGER.debug(f"{step_name}✅ subprocess finished in {total:.2f}s")
    return proc.returncode, out, err


def replace_dict_key(dictionary, old_key, new_key, step_name="", log_level=None):
    """
    Replace a key in a dictionary with a new key, preserving the associated value.

    Args:
        dictionary (dict): Dictionary to modify.
        old_key (str): Key to be replaced.
        new_key (str): New key to use.
        step_name (str): Prefix for log messages.
        log_level: Logging level.
    """
    with set_log_level(GV.LOGGER, log_level):
        if old_key in dictionary:
            dictionary[new_key] = dictionary.pop(old_key)
            GV.LOGGER.debug(f"{step_name}🔁 Replaced key '{old_key}' with '{new_key}'")
        else:
            GV.LOGGER.warning(f"{step_name}⚠️ Key '{old_key}' not found in dictionary")


def batch_replace_sourcefiles_in_json(json_path, replacements, step_name="", log_level=None):
    """
    Perform replacements of 'SourceFile' keys and values in a JSON file.
    Works with two formats:
      1. List of dicts:     [ { "SourceFile": ..., ... }, ... ]
      2. Dict of entries:   { "path": { "SourceFile": ..., ... }, ... }

    Args:
        json_path: Path to the JSON file.
        replacements: List of (old_path, new_path) tuples. Supports both exact and prefix replacement.
        step_name: Optional step name for log messages.
        log_level: Optional logging level to override the default.
    """
    with set_log_level(GV.LOGGER, log_level):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            changes = 0

            # Case 1: List of dicts
            if isinstance(data, list):
                for entry in data:
                    source = entry.get("SourceFile")
                    if not isinstance(source, str):
                        continue
                    for old, new in replacements:
                        if source == old:
                            entry["SourceFile"] = new
                            changes += 1
                            break
                        elif source.startswith(old + os.sep):
                            entry["SourceFile"] = new + source[len(old):]
                            changes += 1
                            break

            # Case 2: Dict of entries
            elif isinstance(data, dict):
                new_data = {}
                for old_key, value in data.items():
                    new_key = old_key
                    for old, new in replacements:
                        if old_key == old:
                            new_key = new
                            break
                        elif old_key.startswith(old + os.sep):
                            new_key = new + old_key[len(old):]
                            break
                    sourcefile = value.get("SourceFile")
                    if isinstance(sourcefile, str):
                        for old, new in replacements:
                            if sourcefile == old:
                                value["SourceFile"] = new
                                changes += 1
                                break
                            elif sourcefile.startswith(old + os.sep):
                                value["SourceFile"] = new + sourcefile[len(old):]
                                changes += 1
                                break
                    if new_key != old_key:
                        changes += 1
                    new_data[new_key] = value
                data = new_data

            else:
                GV.LOGGER.warning(f"{step_name}⚠️ JSON format not supported (must be list or dict): {json_path}")
                return

            GV.LOGGER.info(f"{step_name}🔁 Total replacements performed: {changes}")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            GV.LOGGER.warning(f"{step_name}❌ Error processing {json_path}: {e}")
