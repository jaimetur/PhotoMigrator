from __future__ import annotations

import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable, Dict, List
from Core.GlobalVariables import TOOL_DATE, TOOL_VERSION

from UI.ui_shared import (
    IMMICH_AUTH_METHOD_KEY_PATTERN,
    IMMICH_AUTH_METHOD_OPTIONS,
    immich_auth_method,
    immich_field_hidden_by_auth_method,
    CLOUD_ACTIONS_AVAILABLE_BY_TAB,
    CompactLogBuffer,
    CONFIG_EDITOR_SECTIONS_ORDER,
    FEATURE_LABELS,
    GENERAL_GROUPS,
    MODULE_TAB_NAMES,
    build_external_terminal_command,
    build_windows_external_terminal_script,
    build_automatic_migration_filter_fields,
    build_ui_subprocess_env,
    build_argument_specs,
    build_full_command,
    build_parser_schema,
    automatic_migration_needs_otp,
    automatic_migration_target_is_immich,
    command_preview_string,
    command_to_string,
    compose_migration_endpoint,
    default_state_values,
    effective_interactive_field_value,
    get_field_by_dest,
    load_config_editor_model,
    load_json_file,
    normalize_field_for_context,
    normalize_organize_local_folder_ui_state,
    parse_find_duplicates_value,
    parse_migration_endpoint,
    parse_folder_list_value,
    parse_rename_albums_value,
    resolve_ui_config_path,
    save_config_editor_values,
    save_json_file,
    split_takeout_fields,
    to_list,
    ui_option_name,
    validate_ui_config_file,
)

TK_STATE_PATH = Path(os.environ.get("PHOTOMIGRATOR_TK_GUI_STATE_PATH", str(Path.home() / ".photomigrator_tk_gui_state.json")))
ANSI_CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([@-~])")
HELP_URL = "https://github.com/jaimetur/PhotoMigrator/tree/main/help"
THEME_CHOICES = [("Ocean", "ocean"), ("Emerald", "emerald"), ("Sunset", "sunset"), ("Dark", "dark")]
MODULE_TO_CONFIG_SECTION = {
    "google_photos": "Google Photos",
    "synology_photos": "Synology Photos",
    "immich_photos": "Immich Photos",
    "nextcloud_photos": "NextCloud Photos",
}
INTERACTIVE_MODULE_TAB_NAMES = {key: label for key, label in MODULE_TAB_NAMES.items() if key != "upload_folder"}
CLOUD_MODULES = {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos", "local_folder"}

# Views shown in the main area. "feature" keeps the historical persisted value for the feature form.
VIEW_HOME = "home"
VIEW_FEATURE = "feature"
VIEW_ACTIVITY = "activity"
SETTINGS_VIEWS = ("features_config", "general", "app_settings")
SETTINGS_TAB_LABELS = {
    "features_config": "Service credentials",
    "general": "General arguments",
    "app_settings": "App settings",
}

_LIGHT_BASE = {
    "root_bg": "#f4f6fa",
    "sidebar_bg": "#ffffff",
    "surface": "#ffffff",
    "surface_2": "#f7f9fc",
    "surface_3": "#eef2f7",
    "border": "#e3e8ef",
    "border_strong": "#cbd5e1",
    "text": "#0f172a",
    "text_2": "#334155",
    "muted": "#5b6576",
    "danger": "#b42318",
    "danger_soft": "#fef3f2",
    "success": "#047857",
    "success_soft": "#e7f6ef",
    "warning_text": "#78350f",
    "warning_soft": "#fffbeb",
    "entry_bg": "#ffffff",
    "entry_fg": "#0f172a",
    "code_bg": "#0f172a",
    "code_fg": "#e2e8f0",
    "log_bg": "#0b1220",
    "log_fg": "#dbe3ee",
    "switch_off": "#cbd5e1",
    "step_bg": "#0f172a",
    "step_fg": "#ffffff",
}

THEMES = {
    "ocean": {**_LIGHT_BASE, "accent": "#2563eb", "accent_strong": "#1d4ed8", "accent_soft": "#eaf1fe", "accent_fg": "#ffffff"},
    "emerald": {**_LIGHT_BASE, "accent": "#047857", "accent_strong": "#065f46", "accent_soft": "#e3f5ec", "accent_fg": "#ffffff"},
    "sunset": {
        **_LIGHT_BASE,
        "root_bg": "#faf6f2",
        "surface_2": "#fcf9f6",
        "surface_3": "#f5eee8",
        "border": "#eadfd6",
        "accent": "#c2410c",
        "accent_strong": "#9a3412",
        "accent_soft": "#fdeee4",
        "accent_fg": "#ffffff",
    },
    "dark": {
        "root_bg": "#0b1120",
        "sidebar_bg": "#0f1729",
        "surface": "#111a2e",
        "surface_2": "#0f1729",
        "surface_3": "#18233a",
        "border": "#22304a",
        "border_strong": "#31415f",
        "text": "#e6ebf3",
        "text_2": "#c6cfdd",
        "muted": "#94a0b4",
        "danger": "#f87171",
        "danger_soft": "#3a1d24",
        "success": "#34d399",
        "success_soft": "#13322a",
        "warning_text": "#fcd34d",
        "warning_soft": "#33290f",
        "entry_bg": "#0f1729",
        "entry_fg": "#e6ebf3",
        "code_bg": "#050a14",
        "code_fg": "#e2e8f0",
        "log_bg": "#050a14",
        "log_fg": "#dbe3ee",
        "switch_off": "#31415f",
        "step_bg": "#e6ebf3",
        "step_fg": "#0b1120",
        "accent": "#60a5fa",
        "accent_strong": "#93c5fd",
        "accent_soft": "#1b2c4a",
        "accent_fg": "#0b1120",
    },
}

# Tile colors per module tone: (light background, light foreground, dark background, dark foreground).
TONES = {
    "mig": ("#eef0ff", "#4338ca", "#26264a", "#a5b4fc"),
    "gto": ("#e8f0fe", "#1d4ed8", "#1b2c4a", "#93c5fd"),
    "ico": ("#e0f2fe", "#0369a1", "#14324a", "#7dd3fc"),
    "gph": ("#fdecec", "#b91c1c", "#3a1d24", "#fca5a5"),
    "syn": ("#eef2f6", "#334155", "#1e293b", "#cbd5e1"),
    "imm": ("#f3edff", "#6d28d9", "#2b2148", "#c4b5fd"),
    "nxc": ("#e3f4fc", "#075985", "#14324a", "#7dd3fc"),
    "loc": ("#fef3e2", "#92400e", "#33290f", "#fcd34d"),
    "tool": ("#f1f5f9", "#475569", "#1e293b", "#cbd5e1"),
}

# Colour layer: solid colour of each module (headers, sidebar chips, Run button) and its readable
# accent for text on cards (light theme, dark theme).
MODULE_COLORS = {
    "mig": ("#6d28d9", "#6d28d9", "#c4b5fd"),
    "gto": ("#c2410c", "#c2410c", "#fdba74"),
    "ico": ("#0369a1", "#0369a1", "#7dd3fc"),
    "gph": ("#1d4ed8", "#1d4ed8", "#93c5fd"),
    "syn": ("#3730a3", "#4338ca", "#a5b4fc"),
    "imm": ("#0f766e", "#0f766e", "#5eead4"),
    "nxc": ("#0e7490", "#0e7490", "#67e8f9"),
    "loc": ("#b45309", "#a16207", "#fcd34d"),
    "tool": ("#be185d", "#be185d", "#f9a8d4"),
    "home": ("#7c3aed", "#6d28d9", "#c4b5fd"),
    "act": ("#0d9488", "#0f766e", "#5eead4"),
    "set": ("#475569", "#334155", "#cbd5e1"),
    "help": ("#4338ca", "#4338ca", "#a5b4fc"),
}
SIDEBAR_COLORS = {
    "bg": "#1e1b4b",
    "hover": "#2c2961",
    "active": "#3b3672",
    "text": "#ffffff",
    "muted": "#c4b5fd",
    "label": "#a5b4fc",
    "border": "#35316b",
}
ACTIVITY_HEADER_COLOR = "#312e81"
SETTINGS_HEADER_COLOR = "#4c1d95"
ACTION_GROUP_INK = {
    "Transfer": ("#1d4ed8", "#93c5fd"),
    "Organize": ("#6d28d9", "#c4b5fd"),
    "Clean up": ("#b91c1c", "#fca5a5"),
    "Folders": ("#6d28d9", "#c4b5fd"),
    "Duplicates": ("#be185d", "#f9a8d4"),
}
HOME_CARD_TEXT = {
    "automatic_migration": "Source to target",
    "google_takeout": "Fix a Google export",
    "icloud_takeout": "Fix an Apple export",
    "google_photos": "Albums and assets",
    "synology_photos": "Albums and assets",
    "immich_photos": "Albums and assets",
    "nextcloud_photos": "Albums and assets",
    "local_folder": "Your own library",
    "standalone_features": "Duplicates, folders",
}


def mix_colors(color: str, other: str, amount: float) -> str:
    """Blend two #rrggbb colours; amount=0 keeps color, amount=1 returns other."""
    first = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    second = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(a + (b - a) * amount) for a, b in zip(first, second)]
    return "#" + "".join(f"{value:02x}" for value in mixed)


MODULE_GROUPS = [
    ("Migrate", ["automatic_migration"]),
    ("Process Takeout", ["google_takeout", "icloud_takeout"]),
    ("Photo libraries", ["google_photos", "synology_photos", "immich_photos", "nextcloud_photos", "local_folder"]),
    ("Tools", ["standalone_features"]),
]

MODULE_META = {
    "automatic_migration": {"label": "Automatic Migration", "glyph": "⇄", "tone": "mig", "tagline": "Copy or move every photo, video and album from a source to a target in a single run. Albums are recreated on the target."},
    "google_takeout": {"label": "Google Takeout", "glyph": "⤓", "tone": "gto", "tagline": "Fix dates and metadata of a Google Photos Takeout export and rebuild its albums into a clean library."},
    "icloud_takeout": {"label": "iCloud Takeout", "glyph": "⤓", "tone": "ico", "tagline": "Restore dates and albums of an Apple iCloud Photos export into a portable library."},
    "google_photos": {"label": "Google Photos", "glyph": "G", "tone": "gph", "tagline": "Upload, download, organize and clean up albums and assets in your Google Photos library."},
    "synology_photos": {"label": "Synology Photos", "glyph": "S", "tone": "syn", "tagline": "Upload, download, organize and clean up albums and assets in your Synology Photos library."},
    "immich_photos": {"label": "Immich Photos", "glyph": "I", "tone": "imm", "tagline": "Upload, download, organize and clean up albums and assets in your Immich library."},
    "nextcloud_photos": {"label": "NextCloud Photos", "glyph": "N", "tone": "nxc", "tagline": "Upload, download, organize and clean up albums and assets in your NextCloud Photos library."},
    "local_folder": {"label": "Local Photos Folder", "glyph": "▭", "tone": "loc", "tagline": "Treat a local folder as a photo library and run the same album and asset actions used for cloud services."},
    "standalone_features": {"label": "Other Features", "glyph": "✱", "tone": "tool", "tagline": "Local helpers: repair symlinks, rename or organize folders, and find or process duplicates."},
}

ACTION_GROUP_ORDER = ["Transfer", "Organize", "Clean up", "Folders", "Duplicates"]
ACTION_META = {
    "upload-albums": ("Transfer", "↑", "One album per subfolder", False),
    "upload-all": ("Transfer", "↑", "A whole folder, albums included", False),
    "download-albums": ("Transfer", "↓", "Selected albums to a folder", False),
    "download-all": ("Transfer", "↓", "Every album and asset", False),
    "rename-albums": ("Organize", "✎", "Pattern and replacement", False),
    "consolidate-albums-names": ("Organize", "≋", "Merge equivalent album families", False),
    "merge-duplicates-albums": ("Organize", "⇉", "Albums with the same name", False),
    "remove-duplicates-assets": ("Clean up", "⌕", "Keep the best copy of each", False),
    "remove-duplicates-albums": ("Clean up", "❐", "Same name and size", False),
    "remove-empty-albums": ("Clean up", "□", "Albums with no assets", False),
    "remove-albums": ("Clean up", "✕", "Albums matching a pattern", True),
    "remove-all-albums": ("Clean up", "✕", "Every album, optionally its assets", True),
    "remove-all-assets": ("Clean up", "⚠", "Every asset and album", True),
    "fix-symlinks-broken": ("Folders", "⛓", "Repair broken album links", False),
    "rename-folders-content-based": ("Folders", "✎", "Prefix album folders with their dates", False),
    "organize-local-folder-by-date": ("Folders", "▦", "Sort a folder into date subfolders", False),
    "find-duplicates": ("Duplicates", "⌕", "List, move or remove duplicates", False),
    "process-duplicates": ("Duplicates", "▤", "Apply a reviewed duplicates CSV", False),
}

MIGRATION_ENDPOINT_KINDS = [
    ("google", "Google", "G", "gph"),
    ("synology", "Synology", "S", "syn"),
    ("immich", "Immich", "I", "imm"),
    ("nextcloud", "NextCloud", "N", "nxc"),
    ("folder", "Folder", "▭", "loc"),
]

FIELD_LABELS = {
    "google-takeout": "Takeout folder",
    "icloud-takeout": "Takeout folder",
    "google-output-folder-suffix": "Output folder suffix",
    "icloud-output-folder-suffix": "Output folder suffix",
    "google-albums-folders-structure": "Albums folder structure",
    "icloud-albums-folders-structure": "Albums folder structure",
    "google-all-photos-folders-structure": "All photos folder structure",
    "icloud-all-photos-folders-structure": "All photos folder structure",
    "foldername-all-photos": "All photos folder name",
    "google-no-symbolic-albums": "Copy album files instead of symlinks",
    "icloud-no-symbolic-albums": "Copy album files instead of symlinks",
    "google-remove-duplicates-files": "Remove duplicate files",
    "google-rename-albums-folders": "Rename album folders by date",
    "google-skip-extras-files": "Skip extra files (-edited, -effects)",
    "google-keep-takeout-folder": "Keep an untouched Takeout copy",
    "google-process-people": "Save people labels",
    "google-ignore-check-structure": "Ignore the Takeout structure check",
    "google-skip-move-albums": "Skip moving albums",
    "google-skip-gpth-tool": "Skip GPTH tool (not recommended)",
    "google-skip-preprocess": "Skip pre-processing",
    "google-skip-postprocess": "Skip post-processing",
    "show-gpth-info": "Show GPTH info messages",
    "show-gpth-errors": "Show GPTH error messages",
    "gpth-no-log": "Do not save the GPTH log",
    "icloud-include-memories": "Include Memories as albums",
    "icloud-prefer-native-exif-writer": "Prefer the native EXIF writer",
    "push-asset-max-size-mb": "Push asset max size (MB)",
    "immich-upload-timeout-seconds": "Immich upload timeout (seconds)",
    "account-id": "Account",
    "local-photos-folder": "Local photos folder",
}

TAKEOUT_ADVANCED_DESTS = {
    "google-ignore-check-structure",
    "google-skip-move-albums",
    "google-skip-gpth-tool",
    "google-skip-preprocess",
    "google-skip-postprocess",
    "show-gpth-info",
    "show-gpth-errors",
    "gpth-no-log",
}

UI_FONT = "TkDefaultFont"
MONO_FONT = "TkFixedFont"


def humanize_label(text: str) -> str:
    raw = str(text or "").strip().lstrip("-")
    if not raw:
        return ""
    if " " in raw:
        return raw
    acronyms = {"url", "api", "id", "csv", "otp", "gps", "gpth", "exif", "zip", "mb", "utc"}
    words = []
    for word in re.split(r"[_\-]+", raw):
        if not word:
            continue
        lower = word.lower()
        if lower in acronyms:
            words.append(lower.upper())
        elif word.isupper() and len(word) > 1:
            words.append(lower)
        else:
            words.append(word)
    if not words:
        return raw
    words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words)


def short_help_text(text: str, max_length: int = 170) -> str:
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    if not flat:
        return ""
    flat = re.sub(r"^CAUTION!+\s*", "", flat, flags=re.IGNORECASE)
    flat = re.sub(r"You must provide the photo client using '--client'\.?\s*", "", flat)
    flat = re.sub(r"Requires\s+'--client'\.?\s*", "", flat)
    match = re.match(r"^(.+?[.!?])(\s|$)", flat)
    sentence = match.group(1) if match else flat
    if len(sentence) > max_length:
        sentence = sentence[: max_length - 1].rstrip() + "…"
    return sentence


def tkinter_runtime_available() -> tuple[bool, str | None]:
    try:
        import tkinter  # noqa: F401
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


class ScrollableFrame:
    def __init__(self, parent: Any, bg: str):
        import tkinter as tk
        from tkinter import ttk

        self.frame = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self.frame, highlightthickness=0, bd=0, bg=bg)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview, style="PM.Vertical.TScrollbar")
        self.body = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")

    def _on_body_configure(self, _event: Any) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._refresh_scrollbar()

    def _on_canvas_configure(self, event: Any) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)
        self._refresh_scrollbar()

    def _refresh_scrollbar(self) -> None:
        bbox = self.canvas.bbox("all")
        if not bbox:
            self.scrollbar.pack_forget()
            return
        content_height = max(0, bbox[3] - bbox[1])
        viewport_height = max(1, self.canvas.winfo_height())
        if content_height <= viewport_height + 2:
            self.scrollbar.pack_forget()
            self.canvas.yview_moveto(0)
        else:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")

    def _pointer_inside(self, event: Any) -> bool:
        try:
            widget = event.widget
            while widget is not None:
                if widget is self.canvas:
                    return True
                widget = widget.master
        except Exception:
            return False
        return False

    def _on_mousewheel(self, event: Any) -> None:
        if not self.canvas.winfo_ismapped() or not self._pointer_inside(event):
            return
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        content_height = max(0, bbox[3] - bbox[1])
        if content_height <= self.canvas.winfo_height() + 2:
            return
        raw_delta = getattr(event, "delta", 0) or 0
        if sys.platform == "darwin":
            delta = -int(raw_delta) if raw_delta else 0
        else:
            delta = int(-1 * (raw_delta / 120)) if raw_delta else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux(self, event: Any) -> None:
        if not self.canvas.winfo_ismapped() or not self._pointer_inside(event):
            return
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        content_height = max(0, bbox[3] - bbox[1])
        if content_height <= self.canvas.winfo_height() + 2:
            return
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(1, "units")

    def clear(self) -> None:
        for child in list(self.body.winfo_children()):
            child.destroy()
        self.canvas.yview_moveto(0)
        self._refresh_scrollbar()


class PhotoMigratorTkGUI:
    def __init__(self, project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.project_root = project_root.resolve()
        self.cli_entrypoint = cli_entrypoint.resolve()
        self.initial_values = dict(initial_values or {})
        self.schema = build_parser_schema()
        self.persisted = load_json_file(TK_STATE_PATH, {})
        self.state_values = default_state_values(self.schema)
        self.state_values.update(self.persisted.get("values") or {})
        self.state_values.update(self.initial_values)
        normalize_organize_local_folder_ui_state(self.state_values, self.schema)
        self.ui_state = dict(self.persisted.get("ui_state") or {})
        self.active_module = str(self.ui_state.get("active_module") or self.initial_values.get("active_module") or "automatic_migration")
        self.active_general_tab = str(self.ui_state.get("active_general_tab") or VIEW_HOME)
        if self.initial_values.get("active_module"):
            self.active_general_tab = VIEW_FEATURE
        if self.active_general_tab not in {VIEW_HOME, VIEW_FEATURE, VIEW_ACTIVITY, *SETTINGS_VIEWS}:
            self.active_general_tab = VIEW_HOME
        self.cloud_action_dest = dict(self.ui_state.get("cloud_action_dest") or {})
        self.standalone_action_dest = str(self.ui_state.get("standalone_action_dest") or "")
        self.migration_endpoints_state = dict(self.ui_state.get("migration_endpoints") or {})
        self.active_config_section = str(self.ui_state.get("active_config_section") or "")
        self.active_config_account = dict(self.ui_state.get("active_config_account") or {})
        self.selected_theme = str(self.ui_state.get("theme") or "ocean")
        if self.selected_theme not in THEMES:
            self.selected_theme = "ocean"
        self.remember_state = bool(self.ui_state.get("remember_state", True))
        self.expanded_sections = dict(self.ui_state.get("expanded_sections") or {})
        self.window_geometry = str(self.ui_state.get("window_geometry") or "1440x900")
        self.launch_cwd = Path.cwd().resolve()
        self.field_widget_map: Dict[str, Any] = {}
        self.field_help_map: Dict[str, str] = {}
        self.config_widget_map: Dict[str, tuple[str, str]] = {}
        self.running_process: subprocess.Popen[str] | None = None
        self.run_started_at: float | None = None
        self.run_finished_at: float | None = None
        self.run_last_updated_at: float | None = None
        self.run_module = ""
        self.run_action_dest = ""
        self.run_exit_code: int | None = None
        self.external_dashboard_active = False
        self.external_dashboard_status_file: Path | None = None
        self.external_dashboard_launcher_file: Path | None = None
        self.external_dashboard_pid_file: Path | None = None
        self.running_command: List[str] = []
        self.output_queue: queue.Queue[str | tuple[str, int]] = queue.Queue()
        self.log_buffer = CompactLogBuffer()
        self.bool_toggle_widgets: Dict[str, Any] = {}
        self.wrap_labels: List[Any] = []
        self.nav_items: Dict[str, Dict[str, Any]] = {}
        self.images: Dict[str, Any] = {}
        if self.active_module not in INTERACTIVE_MODULE_TAB_NAMES:
            self.active_module = "automatic_migration"
        self.reload_config_model()

        self.root = tk.Tk()
        self._resolve_fonts()
        self.root.title(f"PhotoMigrator {TOOL_VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.geometry(self.window_geometry)
        self.root.minsize(1100, 720)
        icon_path = self.project_root / "assets" / "ico" / "PhotoMigrator.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_layout()
        self.apply_theme(rebuild=False)
        self.refresh_navigation()
        self.refresh_action_buttons()
        self.rebuild_content()
        self.update_command_preview()
        self.refresh_run_metadata()
        self.root.after(0, self._restore_gui_focus)
        self.root.after(250, self._restore_gui_focus)
        self.root.after(120, self.poll_process_queue)

    def _resolve_fonts(self) -> None:
        """Use the platform UI and monospace families so text matches the operating system."""
        global UI_FONT, MONO_FONT
        try:
            from tkinter import font as tkfont

            UI_FONT = str(tkfont.nametofont("TkDefaultFont").actual("family") or UI_FONT)
            MONO_FONT = str(tkfont.nametofont("TkFixedFont").actual("family") or MONO_FONT)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Config model helpers
    # ------------------------------------------------------------------
    def preferred_config_section(self) -> str:
        mapped = MODULE_TO_CONFIG_SECTION.get(self.active_module)
        if mapped:
            return mapped
        if self.active_config_section in CONFIG_EDITOR_SECTIONS_ORDER:
            return self.active_config_section
        return CONFIG_EDITOR_SECTIONS_ORDER[0]

    def current_config_path(self) -> Path:
        return resolve_ui_config_path(self.state_values.get("configuration-file"), base_dir=self.launch_cwd)

    def reload_config_model(self) -> None:
        model = load_config_editor_model(self.project_root, self.current_config_path(), launch_cwd=self.launch_cwd)
        self.config_template_text = model["template_text"]
        self.config_schema = model["schema"]
        self.config_values = model["values"]
        self.config_sections = model["sections"]
        valid_sections = {str(section.get("name") or "") for section in self.config_sections}
        preferred = self.preferred_config_section()
        if self.active_config_section not in valid_sections:
            self.active_config_section = preferred if preferred in valid_sections else next(iter(valid_sections), "")
        if not self.active_config_section and valid_sections:
            self.active_config_section = next(iter(valid_sections))
        self.ensure_config_account_selection()

    def ensure_config_account_selection(self) -> None:
        for section in self.config_sections:
            section_name = str(section.get("name") or "")
            selector = section.get("account_selector") or {}
            if not selector.get("enabled"):
                self.active_config_account.pop(section_name, None)
                continue
            accounts = [str(item) for item in selector.get("accounts") or []]
            current = str(self.active_config_account.get(section_name) or "")
            if current not in accounts:
                self.active_config_account[section_name] = str(selector.get("default_account") or (accounts[0] if accounts else ""))

    def current_theme(self) -> Dict[str, str]:
        return THEMES.get(self.selected_theme, THEMES["ocean"])

    def is_dark_theme(self) -> bool:
        return self.selected_theme == "dark"

    def tone_colors(self, tone: str) -> tuple[str, str]:
        light_bg, light_fg, dark_bg, dark_fg = TONES.get(tone, TONES["tool"])
        return (dark_bg, dark_fg) if self.is_dark_theme() else (light_bg, light_fg)

    def module_color(self, tone: str) -> str:
        return MODULE_COLORS.get(tone, MODULE_COLORS["home"])[0]

    def tone_ink(self, tone: str) -> str:
        _solid, light_ink, dark_ink = MODULE_COLORS.get(tone, MODULE_COLORS["home"])
        return dark_ink if self.is_dark_theme() else light_ink

    def active_tone(self) -> str:
        if self.active_general_tab == VIEW_FEATURE:
            return MODULE_META.get(self.active_module, {}).get("tone", "home")
        if self.active_general_tab == VIEW_ACTIVITY:
            return MODULE_META.get(self.run_module or self.active_module, {}).get("tone", "home")
        return "home"

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        tk = self.tk
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(self.root, width=248, bd=0, highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)
        self.sidebar_border = tk.Frame(self.root, width=1, bd=0)
        self.sidebar_border.grid(row=0, column=0, sticky="nse")

        self.brand = tk.Frame(self.sidebar, bd=0)
        self.brand.pack(fill="x", padx=14, pady=(16, 10))
        logo_path = self.project_root / "assets" / "logos" / "logo_18_1024x1024.png"
        self.brand_logo = tk.Label(self.brand, bd=0)
        if logo_path.exists():
            try:
                image = tk.PhotoImage(file=str(logo_path)).subsample(28)
                self.images["logo"] = image
                self.brand_logo.configure(image=image)
                self.brand_logo.pack(side="left", padx=(0, 10))
            except Exception:
                pass
        brand_text = tk.Frame(self.brand, bd=0)
        brand_text.pack(side="left", fill="x")
        self.brand_name = tk.Label(brand_text, text="PhotoMigrator", anchor="w", font=(UI_FONT, 14, "bold"))
        self.brand_name.pack(fill="x")
        self.brand_version = tk.Label(brand_text, text=f"{TOOL_VERSION} · {TOOL_DATE}", anchor="w", font=(UI_FONT, 9))
        self.brand_version.pack(fill="x")
        self.brand_text = brand_text

        self.nav_frame = tk.Frame(self.sidebar, bd=0)
        self.nav_frame.pack(fill="both", expand=True, padx=10)
        self.nav_labels: List[Any] = []
        self._add_nav_item(self.nav_frame, "view:home", "⌂", "Home", "home", lambda: self.select_view(VIEW_HOME))
        for group_title, modules in MODULE_GROUPS:
            label = tk.Label(self.nav_frame, text=group_title.upper(), anchor="w", font=(UI_FONT, 8, "bold"))
            label.pack(fill="x", padx=8, pady=(12, 3))
            self.nav_labels.append(label)
            for module_key in modules:
                meta = MODULE_META[module_key]
                self._add_nav_item(self.nav_frame, f"module:{module_key}", meta["glyph"], meta["label"], meta["tone"], lambda key=module_key: self.select_module(key))

        self.sidebar_footer = tk.Frame(self.sidebar, bd=0)
        self.sidebar_footer.pack(fill="x", side="bottom", padx=10, pady=(6, 12))
        self.sidebar_footer_border = tk.Frame(self.sidebar_footer, height=1, bd=0)
        self.sidebar_footer_border.pack(fill="x", pady=(0, 8))
        self._add_nav_item(self.sidebar_footer, "view:activity", "◔", "Activity", "act", lambda: self.select_view(VIEW_ACTIVITY))
        self._add_nav_item(self.sidebar_footer, "view:settings", "⚙", "Settings", "set", lambda: self.select_view(self.last_settings_view()))
        self._add_nav_item(self.sidebar_footer, "view:help", "?", "Help", "help", self.action_open_help)
        self.exit_button = self.ttk.Button(self.sidebar_footer, text="Exit", command=self.action_request_exit, style="PM.Sidebar.TButton")
        self.exit_button.pack(fill="x", pady=(8, 0))

        self.main = tk.Frame(self.root, bd=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        # Header with the current view title.
        self.header = tk.Frame(self.main, bd=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(1, weight=1)
        self.header_icon = tk.Label(self.header, text="", width=3, font=(UI_FONT, 18, "bold"), bd=0)
        self.header_icon.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(28, 14), pady=(22, 12))
        self.header_eyebrow = tk.Label(self.header, text="", anchor="w", font=(UI_FONT, 9, "bold"))
        self.header_eyebrow.grid(row=0, column=1, sticky="ew", pady=(20, 0))
        self.header_title = tk.Label(self.header, text="", anchor="w", font=(UI_FONT, 20, "bold"))
        self.header_title.grid(row=1, column=1, sticky="ew")
        self.header_tagline = tk.Label(self.header, text="", anchor="w", justify="left", font=(UI_FONT, 11))
        self.header_tagline.grid(row=2, column=1, sticky="ew", pady=(2, 14))
        self.wrap_labels.append(self.header_tagline)
        self.header_actions = tk.Frame(self.header, bd=0)
        self.header_actions.grid(row=0, column=2, rowspan=3, sticky="ne", padx=(12, 28), pady=(22, 0))
        self.header_border = tk.Frame(self.main, height=1, bd=0)
        self.header_border.grid(row=0, column=0, sticky="sew")

        # Scrollable content used by Home, feature and settings views.
        self.content_area = tk.Frame(self.main, bd=0)
        self.content_area.grid(row=1, column=0, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_scroll = ScrollableFrame(self.content_area, bg=_LIGHT_BASE["root_bg"])
        self.content_scroll.frame.grid(row=0, column=0, sticky="nsew")

        # Activity view with the run summary, log and process input.
        self.activity_area = tk.Frame(self.main, bd=0)
        self.activity_area.grid(row=1, column=0, sticky="nsew")
        self.activity_area.grid_columnconfigure(0, weight=1)
        self.activity_area.grid_rowconfigure(2, weight=1)
        self._build_activity_area()
        self.activity_area.grid_remove()

        # Field help strip, run bar and status bar.
        self.hint_bar = tk.Frame(self.main, bd=0)
        self.hint_bar.grid(row=2, column=0, sticky="ew")
        self.description_var = tk.StringVar(value="Hover or focus a field to see its full description here.")
        self.description_text = tk.Label(self.hint_bar, textvariable=self.description_var, anchor="w", justify="left", font=(UI_FONT, 10), padx=28, pady=6)
        self.description_text.pack(fill="x")
        self.wrap_labels.append(self.description_text)

        self.run_bar = tk.Frame(self.main, bd=0)
        self.run_bar.grid(row=3, column=0, sticky="ew")
        self.run_bar.grid_columnconfigure(1, weight=1)
        self.run_bar_border = tk.Frame(self.run_bar, height=1, bd=0)
        self.run_bar_border.grid(row=0, column=0, columnspan=6, sticky="ew")
        self.preview_label = tk.Label(self.run_bar, text="COMMAND", font=(UI_FONT, 8, "bold"), padx=10)
        self.preview_label.grid(row=1, column=0, sticky="w", padx=(28, 0), pady=12)
        self.preview_text = self._readonly_text(self.run_bar, height=1, auto_fit=False)
        self.preview_text.configure(wrap="none", font=(MONO_FONT, 11), padx=10, pady=8)
        self.preview_text.grid(row=1, column=1, sticky="ew", pady=12)
        self.preview_scroll = None
        self.copy_command_button = self.ttk.Button(self.run_bar, text="Copy", command=self.action_copy_command, style="PM.Secondary.TButton")
        self.copy_command_button.grid(row=1, column=2, padx=(10, 0), pady=12)
        self.stop_button = self.ttk.Button(self.run_bar, text="■  Stop", command=self.action_stop_job, style="PM.Danger.TButton")
        self.stop_button.grid(row=1, column=3, padx=(10, 0), pady=12)
        self.run_button = self.ttk.Button(self.run_bar, text="▶  Run", command=self.action_run_job, style="PM.Primary.TButton")
        self.run_button.grid(row=1, column=4, padx=(10, 28), pady=12)

        self.status_bar = tk.Frame(self.main, bd=0)
        self.status_bar.grid(row=4, column=0, sticky="ew")
        self.status_dot = tk.Label(self.status_bar, text="●", font=(UI_FONT, 9), padx=0)
        self.status_dot.pack(side="left", padx=(28, 6), pady=5)
        self.status_var = tk.StringVar(value="Ready.")
        self.status_text = tk.Label(self.status_bar, textvariable=self.status_var, anchor="w", font=(UI_FONT, 9))
        self.status_text.pack(side="left", pady=5)
        self.config_path_var = tk.StringVar(value="")
        self.config_path_label = tk.Label(self.status_bar, textvariable=self.config_path_var, anchor="e", font=(UI_FONT, 9))
        self.config_path_label.pack(side="right", padx=(6, 28), pady=5)
        self.main.bind("<Configure>", lambda _e: self._sync_all_wrap_labels(), add="+")
        self._setup_context_menus()

    def _build_activity_area(self) -> None:
        tk = self.tk
        area = self.activity_area
        summary = tk.Frame(area, bd=0)
        summary.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 10))
        self.activity_summary = summary
        self.activity_status_var = tk.StringVar(value="Status: idle")
        self.activity_status_chip = tk.Label(summary, textvariable=self.activity_status_var, font=(UI_FONT, 10, "bold"), padx=12, pady=5)
        self.activity_status_chip.pack(side="left")
        self.run_meta_var = tk.StringVar(value="Elapsed Time: 00:00:00    Last Updated: -")
        self.run_meta_text = tk.Label(summary, textvariable=self.run_meta_var, font=(UI_FONT, 10), padx=12, pady=5)
        self.run_meta_text.pack(side="left", padx=(8, 0))

        self.activity_command_frame = tk.Frame(area, bd=0)
        self.activity_command_frame.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 12))
        self.activity_command_label = tk.Label(self.activity_command_frame, text="COMMAND", font=(UI_FONT, 8, "bold"), padx=10)
        self.activity_command_label.pack(side="left", pady=8)
        self.activity_command_var = tk.StringVar(value="-")
        self.activity_command_text = tk.Label(self.activity_command_frame, textvariable=self.activity_command_var, anchor="w", justify="left", font=(MONO_FONT, 10))
        self.activity_command_text.pack(side="left", fill="x", expand=True, pady=8, padx=(0, 10))

        self.log_card = tk.Frame(area, bd=0, highlightthickness=1)
        self.log_card.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 12))
        self.log_card.grid_rowconfigure(1, weight=1)
        self.log_card.grid_columnconfigure(0, weight=1)
        self.log_header = tk.Frame(self.log_card, bd=0)
        self.log_header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 8))
        self.log_title_label = tk.Label(self.log_header, text="Log", font=(UI_FONT, 12, "bold"))
        self.log_title_label.pack(side="left")
        self.copy_log_button = self.ttk.Button(self.log_header, text="Copy log", command=self.action_copy_log, style="PM.Secondary.TButton")
        self.copy_log_button.pack(side="right")
        self.log_text = tk.Text(
            self.log_card,
            height=16,
            wrap="word",
            state="normal",
            relief="flat",
            bd=0,
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            spacing1=0,
            spacing2=0,
            spacing3=0,
            takefocus=0,
            insertwidth=0,
            font=(MONO_FONT, 11),
        )
        self.log_text._pm_readonly = True
        self.log_text.bind("<Key>", lambda _e: "break")
        self.log_text.bind("<<Paste>>", lambda _e: "break")
        self.log_text.bind("<<Cut>>", lambda _e: "break")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 14))
        self.log_scroll = self.ttk.Scrollbar(self.log_card, orient="vertical", command=self.log_text.yview, style="PM.Vertical.TScrollbar")
        self.log_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 14), pady=(0, 14))
        self.log_text.configure(yscrollcommand=self._on_log_text_scroll)
        self._on_log_text_scroll("0.0", "1.0")

        self.input_panel = tk.Frame(area, bd=0, highlightthickness=1)
        self.input_panel.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 16))
        self.input_panel.grid_columnconfigure(1, weight=1)
        self.input_title_label = tk.Label(self.input_panel, text="Process input", font=(UI_FONT, 10, "bold"))
        self.input_title_label.grid(row=0, column=0, sticky="w", padx=(14, 10), pady=10)
        self.job_input_var = tk.StringVar()
        self.job_input_var.trace_add("write", lambda *_args: self.refresh_action_buttons())
        self.job_input_entry = tk.Entry(self.input_panel, textvariable=self.job_input_var, relief="flat", bd=0, highlightthickness=1, font=(UI_FONT, 11))
        self.job_input_entry.grid(row=0, column=1, sticky="ew", pady=10, ipady=5)
        self.job_input_entry.bind("<Return>", lambda _e: self.action_send_job_input())
        self.job_input_send = self.ttk.Button(self.input_panel, text="Send", command=self.action_send_job_input, style="PM.Primary.TButton")
        self.job_input_send.grid(row=0, column=2, padx=(8, 0), pady=10)
        self.job_input_yes = self.ttk.Button(self.input_panel, text="Yes", command=lambda: self.action_send_job_input("yes"), style="PM.Secondary.TButton")
        self.job_input_yes.grid(row=0, column=3, padx=(8, 0), pady=10)
        self.job_input_no = self.ttk.Button(self.input_panel, text="No", command=lambda: self.action_send_job_input("no"), style="PM.Secondary.TButton")
        self.job_input_no.grid(row=0, column=4, padx=(8, 14), pady=10)

    def _add_nav_item(self, parent: Any, key: str, glyph: str, label: str, tone: str, command: Callable[[], None]) -> None:
        tk = self.tk
        row = tk.Frame(parent, bd=0, cursor="hand2")
        row.pack(fill="x", pady=1)
        icon = tk.Label(row, text=glyph, width=2, font=(UI_FONT, 11, "bold"), cursor="hand2")
        icon.pack(side="left", padx=(8, 10), pady=6, ipadx=3, ipady=1)
        text = tk.Label(row, text=label, anchor="w", font=(UI_FONT, 11), cursor="hand2")
        text.pack(side="left", fill="x", expand=True, pady=6)
        badge = tk.Label(row, text="", font=(UI_FONT, 8, "bold"), padx=6)
        badge.pack(side="right", padx=(0, 8))
        for widget in (row, icon, text, badge):
            widget.bind("<Button-1>", lambda _e, cmd=command: cmd(), add="+")
            widget.bind("<Enter>", lambda _e, k=key: self._on_nav_hover(k, True), add="+")
            widget.bind("<Leave>", lambda _e, k=key: self._on_nav_hover(k, False), add="+")
        self.nav_items[key] = {"row": row, "icon": icon, "text": text, "badge": badge, "tone": tone, "hover": False}

    def _on_nav_hover(self, key: str, hovering: bool) -> None:
        item = self.nav_items.get(key)
        if not item:
            return
        item["hover"] = hovering
        self._paint_nav_item(key)

    def _nav_item_active(self, key: str) -> bool:
        if key == f"module:{self.active_module}":
            return self.active_general_tab == VIEW_FEATURE
        if key == "view:home":
            return self.active_general_tab == VIEW_HOME
        if key == "view:activity":
            return self.active_general_tab == VIEW_ACTIVITY
        if key == "view:settings":
            return self.active_general_tab in SETTINGS_VIEWS
        return False

    def _paint_nav_item(self, key: str) -> None:
        theme = self.current_theme()
        item = self.nav_items.get(key)
        if not item:
            return
        active = self._nav_item_active(key)
        if active:
            bg = SIDEBAR_COLORS["active"]
        elif item.get("hover"):
            bg = SIDEBAR_COLORS["hover"]
        else:
            bg = SIDEBAR_COLORS["bg"]
        fg = SIDEBAR_COLORS["text"]
        item["row"].configure(bg=bg)
        item["icon"].configure(bg=self.module_color(item["tone"]), fg="#ffffff")
        item["text"].configure(bg=bg, fg=fg, font=(UI_FONT, 11, "bold" if active else "normal"))
        badge_text = str(item["badge"].cget("text") or "")
        item["badge"].configure(
            bg=("#22c55e" if badge_text else bg),
            fg="#052e16",
        )

    def refresh_navigation(self) -> None:
        running = self.can_stop_job()
        activity = self.nav_items.get("view:activity")
        if activity:
            activity["badge"].configure(text=("Running" if running else ""))
        for key in self.nav_items:
            self._paint_nav_item(key)

    # Kept for backwards compatibility with callers of the previous layout.
    def refresh_module_buttons(self) -> None:
        self.refresh_navigation()

    def refresh_top_tabs(self) -> None:
        self.refresh_navigation()

    def last_settings_view(self) -> str:
        last = str(self.ui_state.get("last_settings_view") or "features_config")
        return last if last in SETTINGS_VIEWS else "features_config"

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def apply_theme(self, rebuild: bool = True) -> None:
        theme = self.current_theme()
        self.root.configure(bg=theme["root_bg"])
        self.configure_ttk_styles()
        side_bg = SIDEBAR_COLORS["bg"]
        self.sidebar.configure(bg=side_bg)
        self.sidebar_border.configure(bg=side_bg)
        for widget in (self.brand, self.brand_text, self.nav_frame, self.sidebar_footer):
            widget.configure(bg=side_bg)
        self.brand_logo.configure(bg=side_bg)
        self.brand_name.configure(bg=side_bg, fg=SIDEBAR_COLORS["text"])
        self.brand_version.configure(bg=side_bg, fg=SIDEBAR_COLORS["muted"])
        for label in self.nav_labels:
            label.configure(bg=side_bg, fg=SIDEBAR_COLORS["label"])
        self.sidebar_footer_border.configure(bg=SIDEBAR_COLORS["border"])
        self.main.configure(bg=theme["root_bg"])
        self.header.configure(bg=theme["surface"])
        self.header_border.configure(bg=theme["border"])
        self.header_eyebrow.configure(bg=theme["surface"], fg=theme["muted"])
        self.header_title.configure(bg=theme["surface"], fg=theme["text"])
        self.header_tagline.configure(bg=theme["surface"], fg=theme["text_2"])
        self.header_actions.configure(bg=theme["surface"])
        self.content_area.configure(bg=theme["root_bg"])
        self.content_scroll.frame.configure(bg=theme["root_bg"])
        self.content_scroll.canvas.configure(bg=theme["root_bg"])
        self.content_scroll.body.configure(bg=theme["root_bg"])
        self.activity_area.configure(bg=theme["root_bg"])
        self.activity_summary.configure(bg=theme["root_bg"])
        self.run_meta_text.configure(bg=theme["surface"], fg=theme["text_2"])
        self.activity_command_frame.configure(bg=theme["code_bg"])
        self.activity_command_label.configure(bg=theme["code_bg"], fg="#94a3b8")
        self.activity_command_text.configure(bg=theme["code_bg"], fg=theme["code_fg"])
        self.log_card.configure(bg=theme["surface"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.log_header.configure(bg=theme["surface"])
        self.log_title_label.configure(bg=theme["surface"], fg=theme["text"])
        self.log_text.configure(bg=theme["log_bg"], fg=theme["log_fg"], insertbackground=theme["log_fg"], selectbackground="#334155")
        self._configure_log_ansi_tags()
        self.input_panel.configure(bg=theme["surface_2"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.input_title_label.configure(bg=theme["surface_2"], fg=theme["text_2"])
        self.job_input_entry.configure(
            bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["entry_fg"],
            highlightbackground=theme["border_strong"], highlightcolor=theme["accent"],
        )
        self.hint_bar.configure(bg=theme["surface_2"])
        self.description_text.configure(bg=theme["surface_2"], fg=theme["muted"])
        self.run_bar.configure(bg=theme["surface"])
        self.run_bar_border.configure(bg=theme["border"])
        self.preview_label.configure(bg=theme["code_bg"], fg="#94a3b8")
        self.preview_text.configure(bg=theme["code_bg"], fg=theme["code_fg"], insertbackground=theme["code_fg"], selectbackground="#334155")
        self.status_bar.configure(bg=theme["surface_3"])
        self.status_text.configure(bg=theme["surface_3"], fg=theme["text_2"])
        self.config_path_label.configure(bg=theme["surface_3"], fg=theme["muted"])
        for dest in list(self.bool_toggle_widgets):
            current_value = self.remember_state if dest == "remember-state" else bool(self.state_values.get(dest))
            self.refresh_boolean_toggle(dest, current_value)
        self.refresh_navigation()
        self.refresh_header()
        self.refresh_action_buttons()
        self.refresh_run_metadata()
        self.refresh_log_view()
        if rebuild:
            self.rebuild_content()
        self.update_command_preview()

    def configure_ttk_styles(self) -> None:
        theme = self.current_theme()
        style = self.style
        base_font = (UI_FONT, 11)
        style.configure(
            "PM.TCombobox",
            fieldbackground=theme["entry_bg"],
            background=theme["surface"],
            foreground=theme["entry_fg"],
            bordercolor=theme["border_strong"],
            lightcolor=theme["entry_bg"],
            darkcolor=theme["entry_bg"],
            arrowcolor=theme["text_2"],
            selectbackground=theme["entry_bg"],
            selectforeground=theme["entry_fg"],
            padding=(8, 6),
            arrowsize=14,
        )
        style.map(
            "PM.TCombobox",
            fieldbackground=[("readonly", theme["entry_bg"]), ("focus", theme["entry_bg"])],
            background=[("readonly", theme["surface"]), ("active", theme["surface_3"])],
            foreground=[("readonly", theme["entry_fg"]), ("focus", theme["entry_fg"])],
            selectbackground=[("readonly", theme["entry_bg"]), ("focus", theme["entry_bg"])],
            selectforeground=[("readonly", theme["entry_fg"]), ("focus", theme["entry_fg"])],
            bordercolor=[("focus", theme["accent"])],
        )
        self.root.option_add("*TCombobox*Listbox.background", theme["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", theme["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", theme["accent_soft"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", theme["accent_strong"])

        def button_style(name: str, bg: str, fg: str, border: str, hover_bg: str, *, bold: bool = True, padding: tuple[int, int] = (16, 8)) -> None:
            style.configure(
                name,
                background=bg,
                foreground=fg,
                bordercolor=border,
                lightcolor=bg,
                darkcolor=bg,
                focuscolor=bg,
                padding=padding,
                relief="flat",
                font=(UI_FONT, 11, "bold" if bold else "normal"),
            )
            style.map(
                name,
                background=[("disabled", theme["surface_3"]), ("pressed", hover_bg), ("active", hover_bg)],
                foreground=[("disabled", theme["muted"])],
                bordercolor=[("disabled", theme["border"])],
                lightcolor=[("disabled", theme["surface_3"]), ("active", hover_bg)],
                darkcolor=[("disabled", theme["surface_3"]), ("active", hover_bg)],
            )

        button_style("PM.Primary.TButton", theme["accent"], theme["accent_fg"], theme["accent"], theme["accent_strong"])
        button_style("PM.Secondary.TButton", theme["surface"], theme["text"], theme["border_strong"], theme["surface_3"])
        button_style("PM.Danger.TButton", theme["surface"], theme["danger"], theme["border_strong"], theme["danger_soft"])
        button_style("PM.Segment.TButton", theme["surface"], theme["text_2"], theme["border_strong"], theme["surface_3"], bold=False, padding=(12, 6))
        button_style("PM.SegmentActive.TButton", theme["accent"], theme["accent_fg"], theme["accent"], theme["accent_strong"], padding=(12, 6))
        button_style("PM.Sidebar.TButton", SIDEBAR_COLORS["active"], SIDEBAR_COLORS["text"], SIDEBAR_COLORS["border"], SIDEBAR_COLORS["hover"])
        button_style("PM.OnColor.TButton", "#ffffff", "#1e1b4b", "#ffffff", "#ede9fe")
        self.button_style = button_style
        style.configure(
            "PM.Vertical.TScrollbar",
            troughcolor=theme["root_bg"],
            background=theme["border_strong"],
            bordercolor=theme["root_bg"],
            lightcolor=theme["border_strong"],
            darkcolor=theme["border_strong"],
            arrowcolor=theme["muted"],
            gripcount=0,
        )
        style.configure("PM.TButton", font=base_font)

    def refresh_header(self) -> None:
        theme = self.current_theme()
        view = self.active_general_tab
        for child in list(self.header_actions.winfo_children()):
            child.destroy()
        icon_glyph = "⌂"
        tone = "tool"
        if view == VIEW_FEATURE:
            meta = MODULE_META.get(self.active_module, {})
            eyebrow = self.module_group_title(self.active_module).upper()
            title = meta.get("label", self.active_module)
            tagline = meta.get("tagline", "")
            icon_glyph = meta.get("glyph", "•")
            tone = meta.get("tone", "tool")
            self.ttk.Button(self.header_actions, text="⟲  Restore defaults", command=self.restore_feature_defaults, style="PM.OnColor.TButton").pack(side="right")
        elif view == VIEW_ACTIVITY:
            module_key = self.run_module or self.active_module
            meta = MODULE_META.get(module_key, {})
            eyebrow = "CURRENT RUN" if self.can_stop_job() else "LAST RUN"
            action_name = FEATURE_LABELS.get(self.run_action_dest or "", "")
            title = meta.get("label", "Activity") + (f"  ›  {action_name}" if action_name else "")
            tagline = "Follow the progress and the log of the job you run from any feature."
            icon_glyph = "◔"
        elif view in SETTINGS_VIEWS:
            eyebrow = "WORKSPACE"
            title = "Settings"
            tagline = "Service credentials, shared arguments and preferences used by every feature."
            icon_glyph = "⚙"
        else:
            eyebrow = "PHOTOMIGRATOR"
            title = "What do you want to move today?"
            tagline = "Pick a task. PhotoMigrator only shows the options that task needs and the exact command before anything runs."
        if view == VIEW_FEATURE:
            header_bg = self.module_color(tone)
        elif view == VIEW_ACTIVITY:
            header_bg = ACTIVITY_HEADER_COLOR
        elif view in SETTINGS_VIEWS:
            header_bg = SETTINGS_HEADER_COLOR
        else:
            header_bg = self.module_color("home")
        self.header_icon.configure(text=icon_glyph, bg=mix_colors(header_bg, "#ffffff", 0.22), fg="#ffffff")
        self.header_eyebrow.configure(text=eyebrow, bg=header_bg, fg=mix_colors(header_bg, "#ffffff", 0.8))
        self.header_title.configure(text=title, bg=header_bg, fg="#ffffff")
        self.header_tagline.configure(text=tagline, bg=header_bg, fg=mix_colors(header_bg, "#ffffff", 0.88))
        self.header.configure(bg=header_bg)
        self.header_actions.configure(bg=header_bg)
        self.header_border.configure(bg=header_bg)
        run_color = self.module_color(self.active_tone())
        if hasattr(self, "button_style"):
            self.button_style("PM.Primary.TButton", run_color, "#ffffff", run_color, mix_colors(run_color, "#000000", 0.15))
        self._sync_all_wrap_labels()

    def module_group_title(self, module_key: str) -> str:
        for group_title, modules in MODULE_GROUPS:
            if module_key in modules:
                return group_title
        return "Features"

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def select_module(self, module_key: str) -> None:
        self.active_module = module_key
        self.active_general_tab = VIEW_FEATURE
        self.active_config_section = self.preferred_config_section()
        self.ensure_config_account_selection()
        self.refresh_navigation()
        self.rebuild_content()
        self.update_command_preview()
        self.refresh_run_metadata()

    def select_view(self, view: str) -> None:
        if view in SETTINGS_VIEWS:
            self.ui_state["last_settings_view"] = view
            if view == "features_config":
                self.reload_config_model()
        self.active_general_tab = view
        self.refresh_navigation()
        self.rebuild_content()
        self.update_command_preview()
        self.refresh_run_metadata()

    def select_general_tab(self, tab_key: str) -> None:
        self.select_view(tab_key)

    def apply_view_layout(self) -> None:
        view = self.active_general_tab
        if view == VIEW_ACTIVITY:
            self.content_area.grid_remove()
            self.activity_area.grid()
        else:
            self.activity_area.grid_remove()
            self.content_area.grid()
        if view in {VIEW_FEATURE, VIEW_ACTIVITY}:
            self.run_bar.grid()
        else:
            self.run_bar.grid_remove()
        if view == VIEW_FEATURE or view in SETTINGS_VIEWS:
            self.hint_bar.grid()
        else:
            self.hint_bar.grid_remove()

    def rebuild_content(self) -> None:
        theme = self.current_theme()
        self.refresh_header()
        self.apply_view_layout()
        self.content_scroll.clear()
        self.field_widget_map = {}
        self.field_help_map = {}
        self.config_widget_map = {}
        self.bool_toggle_widgets = {}
        self.wrap_labels = [label for label in self.wrap_labels if self._widget_exists(label)]
        body = self.content_scroll.body
        body.configure(bg=theme["root_bg"])
        if self.active_general_tab != VIEW_ACTIVITY:
            container = self.tk.Frame(body, bg=theme["root_bg"])
            container.pack(fill="both", expand=True, padx=28, pady=(20, 28))
            self.build_content_widgets(container)
            if not container.winfo_children():
                self._muted_label(container, "No content available.").pack(anchor="w")
        self.content_scroll._refresh_scrollbar()
        self.root.after_idle(self._sync_all_wrap_labels)

    def build_content_widgets(self, parent: Any) -> List[Any]:
        view = self.active_general_tab
        if view == VIEW_HOME:
            return self.build_home_widgets(parent)
        if view == VIEW_FEATURE:
            return self.build_feature_widgets(parent)
        if view in SETTINGS_VIEWS:
            return self.build_settings_widgets(parent)
        return []

    # ------------------------------------------------------------------
    # Generic widgets
    # ------------------------------------------------------------------
    def _widget_exists(self, widget: Any) -> bool:
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def _card(self, parent: Any, *, pady: tuple[int, int] = (0, 16), bg: str | None = None) -> Any:
        theme = self.current_theme()
        outer = self.tk.Frame(parent, bg=bg or theme["surface"], highlightthickness=1, highlightbackground=theme["border"], highlightcolor=theme["border"], bd=0)
        outer.pack(fill="x", pady=pady)
        inner = self.tk.Frame(outer, bg=bg or theme["surface"], bd=0)
        inner.pack(fill="both", expand=True, padx=20, pady=18)
        return inner

    def _step_header(self, parent: Any, number: int | None, title: str, *, extra: str = "") -> Any:
        theme = self.current_theme()
        row = self.tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", pady=(0, 12))
        if number:
            badge = self.tk.Label(row, text=str(number), width=2, bg=self.module_color(self.active_tone()), fg="#ffffff", font=(UI_FONT, 10, "bold"))
            badge.pack(side="left", padx=(0, 10), ipady=2)
        self.tk.Label(row, text=title, bg=parent.cget("bg"), fg=theme["text"], font=(UI_FONT, 13, "bold"), anchor="w").pack(side="left")
        if extra:
            self.tk.Label(row, text=extra, bg=theme["surface_3"], fg=theme["text_2"], font=(UI_FONT, 9, "bold"), padx=8, pady=2).pack(side="left", padx=(10, 0))
        return row

    def _collapsible_card(self, parent: Any, key: str, title: str, summary: str = "") -> Any:
        theme = self.current_theme()
        outer = self.tk.Frame(parent, bg=theme["surface"], highlightthickness=1, highlightbackground=theme["border"], bd=0)
        outer.pack(fill="x", pady=(0, 16))
        expanded = bool(self.expanded_sections.get(key, False))
        header = self.tk.Frame(outer, bg=theme["surface"], cursor="hand2")
        header.pack(fill="x", padx=20, pady=14)
        arrow = self.tk.Label(header, text=("▾" if expanded else "▸"), bg=theme["surface"], fg=theme["muted"], font=(UI_FONT, 12, "bold"), cursor="hand2")
        arrow.pack(side="left", padx=(0, 8))
        title_label = self.tk.Label(header, text=title, bg=theme["surface"], fg=theme["text"], font=(UI_FONT, 13, "bold"), cursor="hand2")
        title_label.pack(side="left")
        if summary:
            self.tk.Label(header, text=summary, bg=theme["surface_3"], fg=theme["text_2"], font=(UI_FONT, 9, "bold"), padx=8, pady=2).pack(side="left", padx=(10, 0))

        def toggle(_event: Any = None) -> None:
            self.expanded_sections[key] = not bool(self.expanded_sections.get(key, False))
            self.rebuild_content()

        for widget in (header, arrow, title_label):
            widget.bind("<Button-1>", toggle, add="+")
        body = self.tk.Frame(outer, bg=theme["surface"])
        if expanded:
            body.pack(fill="x", padx=20, pady=(0, 18))
        return body

    def _muted_label(self, parent: Any, text: str, *, size: int = 10, wrap: bool = True) -> Any:
        theme = self.current_theme()
        label = self.tk.Label(parent, text=text, bg=parent.cget("bg"), fg=theme["muted"], anchor="w", justify="left", font=(UI_FONT, size))
        if wrap:
            self.wrap_labels.append(label)
        return label

    def _sync_all_wrap_labels(self) -> None:
        alive = []
        for label in self.wrap_labels:
            if not self._widget_exists(label):
                continue
            alive.append(label)
            try:
                width = int(label.master.winfo_width())
            except Exception:
                width = 0
            if width > 40:
                try:
                    label.configure(wraplength=max(120, width - 24))
                except Exception:
                    pass
        self.wrap_labels = alive

    def _field_title(self, parent: Any, label: str, required: bool) -> Any:
        theme = self.current_theme()
        row = self.tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x")
        self.tk.Label(row, text=label, bg=parent.cget("bg"), fg=theme["text"], font=(UI_FONT, 11, "bold"), anchor="w").pack(side="left")
        if required:
            self.tk.Label(row, text="Required", bg=theme["danger_soft"], fg=theme["danger"], font=(UI_FONT, 8, "bold"), padx=6, pady=1).pack(side="left", padx=(8, 0))
        return row

    def _field_meta(self, parent: Any, help_text: str, flag: str) -> None:
        theme = self.current_theme()
        short = short_help_text(help_text)
        if short:
            self._muted_label(parent, short, size=10).pack(fill="x", pady=(4, 0))
        if flag:
            self.tk.Label(parent, text=flag, bg=parent.cget("bg"), fg=theme["muted"], font=(MONO_FONT, 9), anchor="w").pack(fill="x")

    def _field_container(self, parent: Any) -> Any:
        container = self.tk.Frame(parent, bg=parent.cget("bg"))
        container.pack(fill="x", pady=(0, 14))
        return container

    def _bind_help(self, widget: Any, help_text: str) -> None:
        text = str(help_text or "").strip()
        if not text:
            return
        self.field_help_map[str(widget)] = text
        widget.bind("<Enter>", lambda _e, t=text: self.update_field_description(t), add="+")
        widget.bind("<FocusIn>", lambda _e, t=text: self.update_field_description(t), add="+")

    def _readonly_text(self, parent: Any, height: int, *, auto_fit: bool = True) -> Any:
        widget = self.tk.Text(parent, height=height, wrap="word", state="normal", relief="flat", borderwidth=0, bd=0, highlightthickness=0, cursor="xterm", padx=0, pady=0, spacing1=0, spacing2=0, spacing3=0, takefocus=0, insertwidth=0)
        widget._pm_readonly = True
        widget._pm_auto_fit_readonly = auto_fit
        widget.bind("<Key>", lambda _e: "break")
        widget.bind("<<Paste>>", lambda _e: "break")
        widget.bind("<<Cut>>", lambda _e: "break")
        if auto_fit:
            widget.bind("<Configure>", lambda _e, w=widget: self._schedule_fit_readonly_text_height(w), add="+")
        self._bind_context_menu(widget)
        return widget

    def _set_readonly_text(self, widget: Any, text: str) -> None:
        body = str(text or "")
        setattr(widget, "_pm_text_body", body)
        widget.delete("1.0", "end")
        if widget is getattr(self, "log_text", None):
            self._insert_ansi_log_text(body)
        else:
            widget.insert("1.0", body)
        if widget is getattr(self, "preview_text", None):
            self._on_preview_text_scroll("0.0", "1.0")
        elif widget is not getattr(self, "log_text", None):
            self._schedule_fit_readonly_text_height(widget)
        if widget is getattr(self, "log_text", None):
            self._on_log_text_scroll("0.0", "1.0")

    def _log_ansi_palette(self) -> Dict[int, str]:
        theme = self.current_theme()
        return {
            30: "#8ea3bf",
            31: "#ff6b6b",
            32: "#4cff7a",
            33: "#ffd166",
            34: "#7fb8ff",
            35: "#d6a2ff",
            36: "#6fe7ff",
            37: theme["log_fg"],
            90: "#8ea3bf",
            91: "#ff8e8e",
            92: "#8dff9f",
            93: "#ffe08a",
            94: "#a8cfff",
            95: "#e2b7ff",
            96: "#9cf2ff",
            97: "#ffffff",
        }

    def _configure_log_ansi_tags(self) -> None:
        palette = self._log_ansi_palette()
        for code, color in palette.items():
            self.log_text.tag_configure(f"pm_log_fg_{code}", foreground=color)

    def _insert_ansi_log_text(self, body: str) -> None:
        active_fg: int | None = None
        cursor = 0
        for match in ANSI_CSI_RE.finditer(body):
            segment = body[cursor:match.start()]
            if segment:
                if active_fg is None:
                    self.log_text.insert("end", segment)
                else:
                    self.log_text.insert("end", segment, (f"pm_log_fg_{active_fg}",))
            params = str(match.group(1) or "")
            final = str(match.group(2) or "")
            if final == "m":
                raw_codes = [item for item in params.split(";") if item != ""]
                codes = [0] if not raw_codes else []
                for item in raw_codes:
                    try:
                        codes.append(int(item))
                    except ValueError:
                        continue
                for code in codes:
                    if code == 0:
                        active_fg = None
                    elif code == 39:
                        active_fg = None
                    elif code in self._log_ansi_palette():
                        active_fg = code
            cursor = match.end()
        tail = body[cursor:]
        if tail:
            if active_fg is None:
                self.log_text.insert("end", tail)
            else:
                self.log_text.insert("end", tail, (f"pm_log_fg_{active_fg}",))

    def _schedule_fit_readonly_text_height(self, widget: Any) -> None:
        if widget is getattr(self, "log_text", None) or not getattr(widget, "_pm_auto_fit_readonly", True):
            return
        token = getattr(widget, "_pm_fit_after", None)
        if token is not None:
            try:
                widget.after_cancel(token)
            except Exception:
                pass
        try:
            widget._pm_fit_after = widget.after_idle(lambda w=widget: self._fit_readonly_text_height(w))
        except Exception:
            pass

    def _fit_readonly_text_height(self, widget: Any) -> None:
        if widget is getattr(self, "log_text", None) or not getattr(widget, "_pm_auto_fit_readonly", True):
            return
        try:
            widget._pm_fit_after = None
        except Exception:
            pass
        body = str(getattr(widget, "_pm_text_body", "") or "")
        try:
            line_count = int(widget.count("1.0", "end-1c", "displaylines")[0]) if body else 1
        except Exception:
            line_count = body.count("\n") + 1 if body else 1
        try:
            widget.configure(height=max(1, min(4, line_count)))
        except Exception:
            pass

    def _sync_wrapped_label_width(self, widget: Any, width: int | None = None) -> None:
        try:
            effective_width = int(width if width is not None else widget.winfo_width())
        except Exception:
            effective_width = 0
        if effective_width <= 1:
            try:
                widget.after_idle(lambda w=widget: self._sync_wrapped_label_width(w))
            except Exception:
                pass
            return
        try:
            widget.configure(wraplength=max(80, effective_width - 4))
        except Exception:
            pass

    def _on_log_text_scroll(self, first: str, last: str) -> None:
        try:
            self.log_scroll.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                self.log_scroll.grid_remove()
            else:
                self.log_scroll.grid()
        except Exception:
            pass

    def _on_preview_text_scroll(self, first: str, last: str) -> None:
        # The command preview is a single horizontal line; it scrolls with the keyboard or the mouse.
        return None

    def update_field_description(self, text: str) -> None:
        self.description_var.set(re.sub(r"\s+", " ", str(text or "")).strip() or "Hover or focus a field to see its full description here.")

    def update_status(self, text: str) -> None:
        self.status_var.set(str(text or "").strip() or "Ready.")

    def _widget_is_editable_text(self, widget: Any) -> bool:
        if widget is None:
            return False
        if isinstance(widget, self.tk.Entry):
            return str(widget.cget("state")) not in {"disabled", "readonly"}
        if isinstance(widget, self.tk.Text):
            if getattr(widget, "_pm_readonly", False):
                return False
            return str(widget.cget("state")) != "disabled"
        return False

    def _setup_context_menus(self) -> None:
        menu = self.tk.Menu(self.root, tearoff=0)
        self.context_menu = menu

        def popup(event: Any) -> str:
            widget = event.widget
            can_paste = self._widget_is_editable_text(widget)
            menu.delete(0, "end")
            menu.add_command(label="Copy", command=lambda w=widget: self._copy_widget_text(w))
            menu.add_command(label="Paste", command=lambda w=widget: self._paste_widget_text(w), state=("normal" if can_paste else "disabled"))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        self._popup_context_menu = popup
        for widget in [self.description_text, self.preview_text, self.status_text, self.log_text, self.job_input_entry, self.activity_command_text]:
            self._bind_context_menu(widget)

    def _bind_context_menu(self, widget: Any) -> None:
        popup = getattr(self, "_popup_context_menu", None)
        if popup is None or widget is None:
            return
        widget.bind("<Button-3>", popup, add="+")
        widget.bind("<Button-2>", popup, add="+")
        widget.bind("<Control-Button-1>", popup, add="+")

    def _copy_widget_text(self, widget: Any) -> None:
        text = ""
        try:
            if isinstance(widget, self.tk.Entry):
                try:
                    text = widget.selection_get()
                except Exception:
                    text = widget.get()
            elif isinstance(widget, self.tk.Label):
                text = str(widget.cget("text") or "")
            elif isinstance(widget, self.tk.Text):
                try:
                    text = widget.get("sel.first", "sel.last")
                except Exception:
                    text = widget.get("1.0", "end-1c")
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.update_status("Text copied to clipboard.")
        except Exception as exc:
            self.update_status(f"Unable to copy text: {exc}")

    def _paste_widget_text(self, widget: Any) -> None:
        if not self._widget_is_editable_text(widget):
            self.update_status("Paste is only available on editable fields.")
            return
        try:
            text = str(self.root.clipboard_get() or "")
        except Exception:
            self.update_status("Clipboard is empty or not accessible.")
            return
        if not text:
            self.update_status("Clipboard is empty or not accessible.")
            return
        try:
            if isinstance(widget, self.tk.Entry):
                widget.insert("insert", text)
            elif isinstance(widget, self.tk.Text):
                widget.insert("insert", text)
            self.update_status("Clipboard pasted into the current field.")
        except Exception as exc:
            self.update_status(f"Unable to paste text: {exc}")

    def _clear_combobox_selection(self, combo: Any) -> None:
        try:
            combo.selection_clear()
        except Exception:
            pass
        try:
            combo.icursor("end")
        except Exception:
            pass

    def _entry(self, parent: Any, text_var: Any) -> Any:
        theme = self.current_theme()
        widget = self.tk.Entry(
            parent,
            textvariable=text_var,
            bg=theme["entry_bg"],
            fg=theme["entry_fg"],
            insertbackground=theme["entry_fg"],
            disabledbackground=theme["surface_3"],
            disabledforeground=theme["muted"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=theme["border_strong"],
            highlightcolor=theme["accent"],
            font=(UI_FONT, 11),
        )
        self._bind_context_menu(widget)
        return widget

    def _empty_label(self, parent: Any, text: str) -> Any:
        return self._muted_label(parent, text)

    # ------------------------------------------------------------------
    # Home view
    # ------------------------------------------------------------------
    def build_home_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        hero_bg = self.module_color("mig")
        hero_outer = self.tk.Frame(parent, bg=hero_bg, bd=0)
        hero_outer.pack(fill="x", pady=(0, 18))
        hero = self.tk.Frame(hero_outer, bg=hero_bg, bd=0)
        hero.pack(fill="x", padx=24, pady=22)
        self.ttk.Button(hero, text="⇄  Start a migration", command=lambda: self.select_module("automatic_migration"), style="PM.OnColor.TButton").pack(side="right", padx=(16, 0))
        text = self.tk.Frame(hero, bg=hero_bg)
        text.pack(side="left", fill="x", expand=True)
        self.tk.Label(text, text="START HERE", bg=mix_colors(hero_bg, "#ffffff", 0.18), fg="#ffffff", font=(UI_FONT, 9, "bold"), padx=8, pady=2).pack(anchor="w")
        self.tk.Label(text, text="Move a whole library in one run", bg=hero_bg, fg="#ffffff", font=(UI_FONT, 17, "bold"), anchor="w").pack(fill="x", pady=(8, 2))
        subtitle = self.tk.Label(text, text="Photos, videos and albums from a source to a target, with a live dashboard.", bg=hero_bg, fg=mix_colors(hero_bg, "#ffffff", 0.85), font=(UI_FONT, 11), anchor="w", justify="left")
        subtitle.pack(fill="x")
        self.wrap_labels.append(subtitle)

        self.tk.Label(parent, text="LIBRARIES & TOOLS", bg=theme["root_bg"], fg=self.tone_ink("mig"), font=(UI_FONT, 10, "bold"), anchor="w").pack(fill="x", pady=(0, 8))
        grid = self.tk.Frame(parent, bg=theme["root_bg"])
        grid.pack(fill="x")
        modules = [key for _title, keys in MODULE_GROUPS for key in keys if key in MODULE_META]
        modules = [key for key in modules if key != "automatic_migration"] + [key for key in modules if key == "automatic_migration"]
        available_width = max(int(self.main.winfo_width() or 0) - 80, 600)
        columns = max(2, min(5, available_width // 230))
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="home-cards")
        for index, module_key in enumerate(modules):
            self._home_tile(grid, module_key, index // columns, index % columns, columns)

        steps = self._card(parent, pady=(18, 0))
        self.tk.Label(steps, text="Get started in three steps", bg=theme["surface"], fg=theme["text"], font=(UI_FONT, 13, "bold"), anchor="w").pack(fill="x", pady=(0, 10))
        for number, title, body in (
            (1, "Connect your services", "Add the URL and credentials of each account in Settings › Service credentials."),
            (2, "Choose a task", "Fill the required fields. Advanced options keep their defaults unless you open them."),
            (3, "Run and follow the progress", "Check the command preview, press Run and follow it live in Activity."),
        ):
            row = self.tk.Frame(steps, bg=theme["surface"])
            row.pack(fill="x", pady=4)
            self.tk.Label(row, text=str(number), width=2, bg=self.module_color("home"), fg="#ffffff", font=(UI_FONT, 10, "bold")).pack(side="left", padx=(0, 12), ipady=2)
            column = self.tk.Frame(row, bg=theme["surface"])
            column.pack(side="left", fill="x", expand=True)
            self.tk.Label(column, text=title, bg=theme["surface"], fg=theme["text"], font=(UI_FONT, 11, "bold"), anchor="w").pack(fill="x")
            self._muted_label(column, body, size=10).pack(fill="x")
        buttons = self.tk.Frame(steps, bg=theme["surface"])
        buttons.pack(fill="x", pady=(10, 0))
        self.ttk.Button(buttons, text="Open Settings", command=lambda: self.select_view("features_config"), style="PM.Secondary.TButton").pack(side="left")
        self.ttk.Button(buttons, text="Open Activity", command=lambda: self.select_view(VIEW_ACTIVITY), style="PM.Secondary.TButton").pack(side="left", padx=(8, 0))
        return []

    def _home_tile(self, parent: Any, module_key: str, row: int, column: int, columns: int) -> None:
        """Module card (style F): coloured title, short underline and the module glyph on the right."""
        theme = self.current_theme()
        meta = MODULE_META[module_key]
        ink = self.tone_ink(meta["tone"])
        tile = self.tk.Frame(parent, bg=theme["surface"], highlightthickness=1, highlightbackground=theme["border"], cursor="hand2")
        tile.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0 if column == columns - 1 else 6), pady=6)
        body = self.tk.Frame(tile, bg=theme["surface"], cursor="hand2")
        body.pack(fill="both", expand=True, padx=16, pady=16)
        text = self.tk.Frame(body, bg=theme["surface"], cursor="hand2")
        text.pack(side="left", fill="x", expand=True)
        name = self.tk.Label(text, text=meta["label"], bg=theme["surface"], fg=ink, font=(UI_FONT, 12, "bold"), anchor="w", cursor="hand2")
        name.pack(fill="x")
        desc = self.tk.Label(text, text=HOME_CARD_TEXT.get(module_key, ""), bg=theme["surface"], fg=theme["muted"], font=(UI_FONT, 10), anchor="w", cursor="hand2")
        desc.pack(fill="x", pady=(2, 0))
        underline_row = self.tk.Frame(text, bg=theme["surface"], cursor="hand2")
        underline_row.pack(fill="x", pady=(8, 0))
        underline = self.tk.Frame(underline_row, bg=ink, width=28, height=3, cursor="hand2")
        underline.pack(side="left")
        glyph = self.tk.Label(body, text=meta["glyph"], bg=theme["surface"], fg=ink, font=(UI_FONT, 22, "bold"), cursor="hand2")
        glyph.pack(side="right", padx=(8, 0))
        surfaces = (tile, body, text, name, desc, underline_row, glyph)

        def hover(on: bool) -> None:
            tile.configure(highlightbackground=ink if on else theme["border"])

        for widget in surfaces + (underline,):
            widget.bind("<Button-1>", lambda _e, key=module_key: self.select_module(key), add="+")
            widget.bind("<Enter>", lambda _e: hover(True), add="+")
            widget.bind("<Leave>", lambda _e: hover(False), add="+")

    # ------------------------------------------------------------------
    # Feature views
    # ------------------------------------------------------------------
    def build_feature_widgets(self, parent: Any) -> List[Any]:
        widgets: List[Any] = []
        if self.active_module == "upload_folder":
            self._muted_label(parent, "Upload to Server is only available in the Web Interface.").pack(anchor="w")
        elif self.active_module == "automatic_migration":
            self.build_module_only_fields(parent, "automatic_migration", self.schema["tabs"]["automatic_migration"])
        elif self.active_module in {"google_takeout", "icloud_takeout"}:
            self.build_module_only_fields(parent, self.active_module, self.schema["tabs"][self.active_module])
        elif self.active_module in CLOUD_MODULES:
            self.build_cloud_widgets(parent)
        elif self.active_module == "standalone_features":
            self.build_standalone_widgets(parent)
        return widgets

    def restore_general_arguments_defaults(self) -> None:
        """Restore the currently visible general arguments without touching feature state."""
        for field in self.schema["general_tabs"]["general"]:
            default_value = field.get("default")
            self.state_values[field["dest"]] = list(default_value) if isinstance(default_value, list) else default_value
        self.persist_ui_state()
        self.rebuild_content()
        self.update_command_preview()

    def restore_feature_defaults(self) -> None:
        """Restore only the current feature's parameters and local overrides."""
        selected = None
        if self.active_module in {"google_takeout", "icloud_takeout", "automatic_migration"}:
            fields = self.schema["tabs"][self.active_module]
        elif self.active_module in CLOUD_MODULES:
            selected = next((field for field in self.schema["tabs"][self.active_module] if field["dest"] == self.cloud_action_dest.get(self.active_module)), None)
            fields = [spec["field"] for spec in build_argument_specs(self.schema, self.active_module, selected, True)]
            primary_field = get_field_by_dest(self.schema, "local-photos-folder" if self.active_module == "local_folder" else "account-id")
            if primary_field:
                fields.append(primary_field)
        elif self.active_module == "standalone_features":
            selected = next((field for field in self.schema["tabs"]["standalone_features"] if field["dest"] == self.standalone_action_dest), None)
            fields = [spec["field"] for spec in build_argument_specs(self.schema, "standalone_features", selected, True)]
        else:
            fields = []
        for field in fields:
            default_value = field.get("default")
            self.state_values[field["dest"]] = list(default_value) if isinstance(default_value, list) else default_value
        if self.active_module in CLOUD_MODULES and selected and selected.get("dest") == "rename-albums":
            self.state_values["rename-pattern"] = ""
            self.state_values["replacement-pattern"] = ""
        if self.active_module == "automatic_migration":
            self.migration_endpoints_state.pop("source", None)
            self.migration_endpoints_state.pop("target", None)
            for field in build_automatic_migration_filter_fields(self.schema):
                self.state_values.pop(f"am-{field['dest']}", None)
        if self.active_module == "standalone_features":
            if selected and selected.get("dest") == "find-duplicates":
                self.state_values["find-duplicates-action"] = "list"
                self.state_values["find-duplicates-folders"] = []
            for dest in ("date-separator", "range-separator"):
                self.state_values.pop(f"sfrcb-{dest}", None)
        self.persist_ui_state()
        self.rebuild_content()
        self.update_command_preview()
        self.update_status("Feature arguments restored to defaults.")

    def build_module_only_fields(self, parent: Any, tab_key: str, fields: List[Dict[str, Any]]) -> None:
        if tab_key == "automatic_migration":
            regular_fields = [field for field in fields if str(field.get("kind") or "") not in {"flag", "bool"}]
            toggle_fields = [
                field for field in fields
                if str(field.get("kind") or "") in {"flag", "bool"} and str(field.get("dest") or "") not in {"one-time-password", "import-people", "create-stacks"}
            ]
            otp_field = get_field_by_dest(self.schema, "one-time-password")
            if otp_field and automatic_migration_needs_otp(self.state_values, self.migration_endpoints_state):
                toggle_fields.append(otp_field)
            people_field = get_field_by_dest(self.schema, "import-people")
            if people_field and automatic_migration_target_is_immich(self.state_values, self.migration_endpoints_state):
                toggle_fields.append(people_field)
            stacks_field = get_field_by_dest(self.schema, "create-stacks")
            if stacks_field and automatic_migration_target_is_immich(self.state_values, self.migration_endpoints_state):
                toggle_fields.append(stacks_field)
            migration_filter_fields = build_automatic_migration_filter_fields(self.schema)
            endpoint_fields = [field for field in regular_fields if str(field.get("dest") or "") in {"source", "target"}]
            other_regular_fields = [field for field in regular_fields if str(field.get("dest") or "") not in {"source", "target"}]
            if endpoint_fields:
                card = self._card(parent)
                self._step_header(card, 1, "Where from and where to")
                endpoints = self.tk.Frame(card, bg=card.cget("bg"))
                endpoints.pack(fill="x")
                endpoints.grid_columnconfigure(0, weight=1, uniform="endpoints")
                endpoints.grid_columnconfigure(2, weight=1, uniform="endpoints")
                for index, field in enumerate(endpoint_fields):
                    column = self.tk.Frame(endpoints, bg=card.cget("bg"))
                    column.grid(row=0, column=index * 2, sticky="new")
                    self.build_migration_endpoint_row(column, str(field.get("dest") or ""), str(field.get("help") or "").strip())
                    if index == 0 and len(endpoint_fields) > 1:
                        self.tk.Label(endpoints, text="→", bg=card.cget("bg"), fg=self.current_theme()["muted"], font=(UI_FONT, 18)).grid(row=0, column=1, padx=16, pady=(28, 0), sticky="n")
            if toggle_fields:
                card = self._card(parent)
                self._step_header(card, 2, "How to migrate")
                self.build_flags_grid(card, toggle_fields, tab_key)
            if migration_filter_fields:
                set_count = sum(1 for field in migration_filter_fields if str(self.state_values.get(field["dest"]) or "").strip())
                body = self._collapsible_card(parent, "migration_filters", "Filters", f"{set_count} set for this migration" if set_count else "Using Settings defaults")
                self._muted_label(body, "If empty, the value from Settings › General arguments is used.").pack(fill="x", pady=(0, 10))
                for field in migration_filter_fields:
                    self.build_field_widgets(body, field, context=tab_key)
            if other_regular_fields:
                summary_parts = []
                for field in other_regular_fields:
                    value = effective_interactive_field_value(field, self.state_values)
                    summary_parts.append(f"{humanize_label(FIELD_LABELS.get(field['dest'], ui_option_name(field)))}: {value}")
                body = self._collapsible_card(parent, "migration_recovery", "Advanced · push recovery", " · ".join(summary_parts[:2]))
                for field in other_regular_fields:
                    self.build_field_widgets(body, field, context=tab_key)
            return
        if tab_key in {"google_takeout", "icloud_takeout"}:
            regular_fields = [field for field in fields if str(field.get("kind") or "") not in {"flag", "bool"}]
            toggle_fields = [field for field in fields if str(field.get("kind") or "") in {"flag", "bool"}]
            module_fields, structure_fields = split_takeout_fields(regular_fields)
            processing_fields = [field for field in toggle_fields if str(field.get("dest") or "") not in TAKEOUT_ADVANCED_DESTS]
            advanced_fields = [field for field in toggle_fields if str(field.get("dest") or "") in TAKEOUT_ADVANCED_DESTS]
            step = 0
            if module_fields:
                step += 1
                card = self._card(parent)
                self._step_header(card, step, "Takeout input and output")
                for field in module_fields:
                    required = str(field.get("dest") or "") in {"google-takeout", "icloud-takeout"}
                    self.build_field_widgets(card, field, required=required, context=tab_key)
            if structure_fields:
                step += 1
                card = self._card(parent)
                self._step_header(card, step, "Folder structure")
                for field in structure_fields:
                    self.build_field_widgets(card, field, context=tab_key)
            if processing_fields:
                step += 1
                card = self._card(parent)
                self._step_header(card, step, "Processing")
                self.build_flags_grid(card, processing_fields, tab_key)
            if advanced_fields:
                body = self._collapsible_card(parent, f"{tab_key}_advanced", "Advanced options", f"{len(advanced_fields)} options")
                self.build_flags_grid(body, advanced_fields, tab_key)
            return
        card = self._card(parent)
        self._step_header(card, 1, "Options")
        for field in fields:
            self.build_field_widgets(card, field, context=tab_key)

    def migration_default_kind(self, dest: str) -> str:
        return "synology" if dest == "source" else "immich"

    def migration_endpoint_state(self, dest: str) -> Dict[str, str]:
        fallback_kind = self.migration_default_kind(dest)
        persisted = self.migration_endpoints_state.get(dest) or {}
        parsed = parse_migration_endpoint(self.state_values.get(dest, ""), fallback_kind)
        state = {
            "kind": str(persisted.get("kind") or parsed.get("kind") or fallback_kind),
            "account": str(persisted.get("account") or parsed.get("account") or "1"),
            "path": str(persisted.get("path") or parsed.get("path") or ""),
        }
        self.migration_endpoints_state[dest] = state
        self.state_values[dest] = compose_migration_endpoint(state)
        return state

    def build_migration_endpoint_row(self, parent: Any, dest: str, help_text: str) -> None:
        theme = self.current_theme()
        state = self.migration_endpoint_state(dest)
        block = self._field_container(parent)
        self._field_title(block, dest.title(), True)

        picker = self.tk.Frame(block, bg=block.cget("bg"))
        picker.pack(fill="x", pady=(8, 0))

        def sync_endpoint_state() -> None:
            self.migration_endpoints_state[dest] = state
            self.state_values[dest] = compose_migration_endpoint(state)
            self.update_command_preview()

        def choose(kind: str) -> None:
            if state.get("kind") == kind:
                return
            state["kind"] = kind
            sync_endpoint_state()
            self.rebuild_content()

        for index, (kind, label, glyph, tone) in enumerate(MIGRATION_ENDPOINT_KINDS):
            picker.grid_columnconfigure(index, weight=1, uniform=f"svc-{dest}")
            selected = state.get("kind") == kind
            tone_solid = self.module_color(tone)
            option = self.tk.Frame(
                picker,
                bg=(tone_solid if selected else theme["surface"]),
                highlightthickness=(2 if selected else 1),
                highlightbackground=(tone_solid if selected else theme["border"]),
                cursor="hand2",
            )
            option.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 3, 0 if index == len(MIGRATION_ENDPOINT_KINDS) - 1 else 3))
            if selected:
                icon_bg, icon_fg = mix_colors(tone_solid, "#ffffff", 0.22), "#ffffff"
            else:
                icon_bg, icon_fg = tone_solid, "#ffffff"
            icon = self.tk.Label(option, text=glyph, width=2, bg=icon_bg, fg=icon_fg, font=(UI_FONT, 11, "bold"), cursor="hand2")
            icon.pack(pady=(8, 4), ipady=2)
            name = self.tk.Label(option, text=label, bg=option.cget("bg"), fg=("#ffffff" if selected else self.tone_ink(tone)), font=(UI_FONT, 9, "bold"), cursor="hand2")
            name.pack(pady=(0, 8))
            for widget in (option, icon, name):
                widget.bind("<Button-1>", lambda _e, k=kind: choose(k), add="+")
            self._bind_help(option, help_text)

        secondary = self.tk.Frame(block, bg=block.cget("bg"))
        secondary.pack(fill="x", pady=(10, 0))
        if state.get("kind") == "folder":
            self.tk.Label(secondary, text="Folder path", bg=block.cget("bg"), fg=theme["text"], font=(UI_FONT, 10, "bold"), anchor="w").pack(fill="x")
            row = self.tk.Frame(secondary, bg=block.cget("bg"))
            row.pack(fill="x", pady=(4, 0))
            path_var = self.tk.StringVar(value=str(state.get("path") or ""))
            self.field_widget_map[dest] = path_var
            entry = self._entry(row, path_var)
            entry.pack(side="left", fill="x", expand=True, ipady=6)
            self._bind_help(entry, help_text)
            btn = self.ttk.Button(row, text="Browse…", command=lambda d=dest: self.browse_path(d), style="PM.Secondary.TButton")
            btn.pack(side="left", padx=(8, 0))

            def on_path_change(*_args: Any) -> None:
                state["path"] = path_var.get()
                sync_endpoint_state()

            path_var.trace_add("write", on_path_change)
        else:
            self.field_widget_map.pop(dest, None)
            self.tk.Label(secondary, text="Account", bg=block.cget("bg"), fg=theme["text"], font=(UI_FONT, 10, "bold"), anchor="w").pack(fill="x")
            account_var = self.tk.StringVar(value=f"Account {state.get('account') or '1'}")
            account_combo = self.ttk.Combobox(secondary, textvariable=account_var, values=["Account 1", "Account 2", "Account 3"], state="readonly", style="PM.TCombobox", font=(UI_FONT, 11))
            account_combo.pack(fill="x", pady=(4, 0))
            self._bind_help(account_combo, help_text)
            self._bind_context_menu(account_combo)

            def on_account_change(_event: Any = None) -> None:
                state["account"] = str(account_var.get() or "Account 1").replace("Account", "").strip() or "1"
                self._clear_combobox_selection(account_combo)
                sync_endpoint_state()

            account_combo.bind("<<ComboboxSelected>>", on_account_change)
        self.tk.Label(block, text=f"--{dest}", bg=block.cget("bg"), fg=theme["muted"], font=(MONO_FONT, 9), anchor="w").pack(fill="x", pady=(6, 0))
        sync_endpoint_state()

    def _selected_action_for_active_module(self) -> str | None:
        if self.active_module in CLOUD_MODULES:
            return self.cloud_action_dest.get(self.active_module)
        if self.active_module == "standalone_features":
            return self.standalone_action_dest
        return None

    def _build_current_command(self, *, dashboard_enabled: bool | None = None) -> List[str]:
        values = dict(self.state_values)
        if self.active_module == "automatic_migration" and dashboard_enabled is not None:
            values["dashboard"] = bool(dashboard_enabled)
        return build_full_command(
            self.cli_entrypoint,
            self.schema,
            self.active_module,
            values,
            self._selected_action_for_active_module(),
        )

    def _should_run_dashboard_in_external_terminal(self) -> bool:
        return self.active_module == "automatic_migration" and bool(self.state_values.get("dashboard", False))

    def _restore_gui_focus(self) -> None:
        try:
            self.root.deiconify()
        except Exception:
            return
        try:
            self.root.lift()
        except Exception:
            pass
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass
        try:
            self.root.focus_force()
        except Exception:
            pass
        self.root.after(250, self._clear_topmost_hint)

    def _clear_topmost_hint(self) -> None:
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

    def _launch_dashboard_job_in_external_terminal(self, command: List[str]) -> None:
        env = build_ui_subprocess_env(ui_mode="gui", embedded_ui=False)
        status_path = Path(tempfile.gettempdir()) / f"photomigrator_dashboard_exit_{time.time_ns()}.txt"
        pid_path = Path(tempfile.gettempdir()) / f"photomigrator_dashboard_pid_{time.time_ns()}.txt"
        # The Rich dashboard may remain open for final-statistics inspection after
        # the migration itself ends. Let it report that milestone to the GUI.
        env["PHOTOMIGRATOR_DASHBOARD_COMPLETION_FILE"] = str(status_path)
        self.external_dashboard_status_file = status_path
        self.external_dashboard_pid_file = pid_path
        launcher_file: Path | None = None
        creationflags = 0
        launcher: List[str] | str
        if sys.platform.startswith("win"):
            launcher_file = Path(tempfile.gettempdir()) / f"photomigrator_dashboard_job_{time.time_ns()}.cmd"
            launcher_file.write_text(
                build_windows_external_terminal_script(command, self.launch_cwd, env, completion_file=status_path),
                encoding="utf-8",
            )
            launcher = ["cmd", "/v:on", "/c", str(launcher_file)]
            creationflags = int(getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        else:
            launcher = build_external_terminal_command(command, self.launch_cwd, env, completion_file=status_path, pid_file=pid_path)
        if not launcher:
            self.external_dashboard_status_file = None
            self.external_dashboard_pid_file = None
            raise RuntimeError("No supported external terminal launcher was found on this system.")
        self.external_dashboard_launcher_file = launcher_file
        try:
            launcher_process = subprocess.Popen(launcher, cwd=str(self.launch_cwd), env=env, creationflags=creationflags)
        except Exception:
            self.external_dashboard_status_file = None
            self.external_dashboard_launcher_file = None
            self.external_dashboard_pid_file = None
            if launcher_file is not None:
                try:
                    launcher_file.unlink(missing_ok=True)
                except Exception:
                    pass
            raise
        self.external_dashboard_active = True
        self.mark_run_started()
        threading.Thread(target=self._external_dashboard_watcher, args=(status_path, pid_path, launcher_process, launcher_file), daemon=True).start()

    def _external_dashboard_watcher(
        self,
        status_path: Path,
        pid_path: Path,
        launcher_process: subprocess.Popen[str] | None = None,
        launcher_file: Path | None = None,
    ) -> None:
        exit_code = -1
        try:
            while True:
                if status_path.exists():
                    payload = status_path.read_text(encoding="utf-8", errors="replace").strip()
                    if payload:
                        try:
                            exit_code = int(payload)
                        except ValueError:
                            exit_code = -1
                        break
                if launcher_process is not None and launcher_process.poll() not in (None, 0):
                    exit_code = int(launcher_process.returncode or -1)
                    break
                time.sleep(0.2)
        finally:
            try:
                status_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                pid_path.unlink(missing_ok=True)
            except Exception:
                pass
            if launcher_file is not None:
                try:
                    launcher_file.unlink(missing_ok=True)
                except Exception:
                    pass
        self.output_queue.put(("dashboard_finished", exit_code))

    def build_flags_grid(self, parent: Any, fields: List[Dict[str, Any]], context: str) -> None:
        frame = self.tk.Frame(parent, bg=parent.cget("bg"))
        frame.pack(fill="x")
        columns = 2 if len(fields) > 1 else 1
        for col in range(columns):
            frame.grid_columnconfigure(col, weight=1, uniform=f"flags-{id(frame)}")
        for index, field in enumerate(fields):
            cell = self.tk.Frame(frame, bg=parent.cget("bg"))
            cell.grid(row=index // columns, column=index % columns, sticky="new", padx=(0 if index % columns == 0 else 14, 0))
            self.build_field_widgets(cell, field, context=context)

    def _action_picker(self, parent: Any, actions: List[Dict[str, Any]], selected_dest: str, on_select: Callable[[str], None]) -> None:
        theme = self.current_theme()
        module_ink = self.tone_ink(self.active_tone())
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for action in actions:
            group = ACTION_META.get(action["dest"], ("Other", "•", "", False))[0]
            grouped.setdefault(group, []).append(action)
        order = [group for group in ACTION_GROUP_ORDER if group in grouped] + [group for group in grouped if group not in ACTION_GROUP_ORDER]
        for group in order:
            if len(grouped) > 1:
                light_ink, dark_ink = ACTION_GROUP_INK.get(group, (theme["muted"], theme["muted"]))
                self.tk.Label(parent, text=group.upper(), bg=parent.cget("bg"), fg=(dark_ink if self.is_dark_theme() else light_ink), font=(UI_FONT, 9, "bold"), anchor="w").pack(fill="x", pady=(4, 6))
            grid = self.tk.Frame(parent, bg=parent.cget("bg"))
            grid.pack(fill="x", pady=(0, 8))
            columns = 3
            for col in range(columns):
                grid.grid_columnconfigure(col, weight=1, uniform=f"actions-{group}")
            for index, action in enumerate(grouped[group]):
                _group, glyph, description, danger = ACTION_META.get(action["dest"], ("Other", "•", "", False))
                selected = action["dest"] == selected_dest
                light_ink, dark_ink = ACTION_GROUP_INK.get(group, ("#6d28d9", "#c4b5fd"))
                group_ink = dark_ink if self.is_dark_theme() else light_ink
                ink = module_ink if selected else group_ink
                tile_bg = theme["surface"]
                tile = self.tk.Frame(
                    grid,
                    bg=tile_bg,
                    highlightthickness=(2 if selected else 1),
                    highlightbackground=(module_ink if selected else theme["border"]),
                    cursor="hand2",
                )
                tile.grid(row=index // columns, column=index % columns, sticky="nsew", padx=(0 if index % columns == 0 else 4, 0 if index % columns == columns - 1 else 4), pady=4)
                head = self.tk.Frame(tile, bg=tile_bg, cursor="hand2")
                head.pack(fill="both", expand=True, padx=14, pady=12)
                text = self.tk.Frame(head, bg=tile_bg, cursor="hand2")
                text.pack(side="left", fill="x", expand=True)
                name = self.tk.Label(text, text=FEATURE_LABELS.get(action["dest"], humanize_label(action["dest"])), bg=tile_bg, fg=ink, font=(UI_FONT, 11, "bold"), anchor="w", justify="left", cursor="hand2")
                name.pack(fill="x")
                desc = self.tk.Label(text, text=description or short_help_text(str(action.get("help") or ""), 60), bg=tile_bg, fg=theme["muted"], font=(UI_FONT, 9), anchor="w", justify="left", cursor="hand2")
                desc.pack(fill="x", pady=(1, 0))
                underline_row = self.tk.Frame(text, bg=tile_bg, cursor="hand2")
                underline_row.pack(fill="x", pady=(6, 0))
                self.tk.Frame(underline_row, bg=ink, width=28, height=3).pack(side="left")
                icon = self.tk.Label(head, text=glyph, bg=tile_bg, fg=ink, font=(UI_FONT, 16, "bold"), cursor="hand2")
                icon.pack(side="right", padx=(8, 0))
                for widget in (tile, head, text, icon, name, desc, underline_row):
                    widget.bind("<Button-1>", lambda _e, dest=action["dest"]: on_select(dest), add="+")
                self._bind_help(tile, str(action.get("help") or ""))

    def _danger_notice(self, parent: Any, text: str) -> None:
        theme = self.current_theme()
        notice = self.tk.Frame(parent, bg=theme["danger_soft"], highlightthickness=1, highlightbackground=theme["danger"])
        notice.pack(fill="x", pady=(0, 16))
        self.tk.Label(notice, text="⚠  Changes your library", bg=theme["danger_soft"], fg=theme["danger"], font=(UI_FONT, 11, "bold"), anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        label = self.tk.Label(notice, text=text, bg=theme["danger_soft"], fg=theme["danger"], font=(UI_FONT, 10), anchor="w", justify="left")
        label.pack(fill="x", padx=14, pady=(0, 10))
        self.wrap_labels.append(label)

    def build_cloud_widgets(self, parent: Any) -> None:
        actions = list(self.schema["tabs"][self.active_module])
        available = CLOUD_ACTIONS_AVAILABLE_BY_TAB.get(self.active_module)
        if available is not None:
            actions = [field for field in actions if field["dest"] in available]
        if not actions:
            self._muted_label(parent, "No cloud actions available for this module.").pack(anchor="w")
            return
        selected_dest = str(self.cloud_action_dest.get(self.active_module) or "")
        if selected_dest not in {field["dest"] for field in actions}:
            selected_dest = actions[0]["dest"]
            self.cloud_action_dest[self.active_module] = selected_dest

        def on_select(dest: str) -> None:
            if dest == str(self.cloud_action_dest.get(self.active_module) or ""):
                return
            self.cloud_action_dest[self.active_module] = dest
            self.rebuild_content()
            self.update_command_preview()

        card = self._card(parent)
        self._step_header(card, 1, "Choose an action")
        self._action_picker(card, actions, selected_dest, on_select)

        selected = next((field for field in actions if field["dest"] == selected_dest), None)
        if selected and selected.get("dest", "").startswith("remove-"):
            self._danger_notice(parent, f"{FEATURE_LABELS.get(selected['dest'], selected['dest'])} deletes data in {MODULE_META[self.active_module]['label']}. Review the options carefully before you run it.")

        options = self._card(parent)
        self._step_header(options, 2, f"Options for {FEATURE_LABELS.get(selected_dest, humanize_label(selected_dest))}")
        if selected and str(selected.get("help") or "").strip():
            self._muted_label(options, short_help_text(str(selected.get("help") or ""), 260), size=10).pack(fill="x", pady=(0, 12))
        if self.active_module == "local_folder":
            local_folder_field = get_field_by_dest(self.schema, "local-photos-folder")
            if local_folder_field:
                self.build_field_widgets(options, normalize_field_for_context(local_folder_field, self.active_module), required=True, context=self.active_module)
        specs = build_argument_specs(self.schema, self.active_module, selected, True)
        primary_dest = "local-photos-folder" if self.active_module == "local_folder" else "account-id"
        primary_field = get_field_by_dest(self.schema, primary_dest)
        if primary_field:
            normalized = normalize_field_for_context(primary_field, self.active_module)
            specs = [spec for spec in specs if spec["field"]["dest"] != primary_dest]
            if self.active_module != "local_folder":
                is_immich_duplicate_assets = self.active_module == "immich_photos" and selected and selected.get("dest") == "remove-duplicates-assets"
                insert_at = len(specs) if is_immich_duplicate_assets else next(
                    (idx for idx, spec in enumerate(specs) if not spec["required"]), len(specs)
                )
                specs.insert(insert_at, {"field": normalized, "required": False})
        if selected and selected.get("dest") == "rename-albums":
            parsed = parse_rename_albums_value(self.state_values.get("rename-albums"))
            if not str(self.state_values.get("rename-pattern") or "").strip():
                self.state_values["rename-pattern"] = parsed.get("pattern") or ""
            if not str(self.state_values.get("replacement-pattern") or "").strip():
                self.state_values["replacement-pattern"] = parsed.get("replacement") or ""
            for spec in specs:
                if spec["field"]["dest"] not in {"rename-albums"}:
                    self.build_field_widgets(options, spec["field"], required=spec["required"], context=self.active_module)
            self.build_pseudo_text_field(options, "Rename pattern", "rename-pattern", self.state_values.get("rename-pattern", ""), True, "Album name pattern (text, wildcard, or regex).")
            self.build_pseudo_text_field(options, "Replacement pattern", "replacement-pattern", self.state_values.get("replacement-pattern", ""), True, "Replacement text used during album rename.")
        elif not specs:
            self._muted_label(options, "No extra arguments required.").pack(fill="x")
        else:
            for spec in specs:
                self.build_field_widgets(options, spec["field"], required=spec["required"], context=self.active_module)

    def build_standalone_widgets(self, parent: Any) -> None:
        actions = list(self.schema["tabs"]["standalone_features"])
        if not actions:
            self._muted_label(parent, "No standalone actions available.").pack(anchor="w")
            return
        selected_dest = self.standalone_action_dest if self.standalone_action_dest in {field["dest"] for field in actions} else actions[0]["dest"]
        self.standalone_action_dest = selected_dest

        def on_select(dest: str) -> None:
            if dest == self.standalone_action_dest:
                return
            self.standalone_action_dest = dest
            self.rebuild_content()
            self.update_command_preview()

        card = self._card(parent)
        self._step_header(card, 1, "Choose a tool")
        self._action_picker(card, actions, selected_dest, on_select)
        selected = next((field for field in actions if field["dest"] == selected_dest), None)
        options = self._card(parent)
        self._step_header(options, 2, f"Options for {FEATURE_LABELS.get(selected_dest, humanize_label(selected_dest))}")
        if selected and str(selected.get("help") or "").strip():
            self._muted_label(options, short_help_text(str(selected.get("help") or ""), 260), size=10).pack(fill="x", pady=(0, 12))
        if selected and selected.get("dest") == "find-duplicates":
            parsed = parse_find_duplicates_value(self.state_values.get("find-duplicates"))
            self.state_values["find-duplicates-action"] = parsed.get("action") or "list"
            if not self.state_values.get("find-duplicates-folders"):
                self.state_values["find-duplicates-folders"] = parsed.get("folders") or []
            self.build_pseudo_list_field(options, "Folders to scan", "find-duplicates-folders", self.state_values.get("find-duplicates-folders", []), True, "One or more folders separated by comma or newline.")
            self.build_select_row(options, "What to do with duplicates", "find-duplicates-action-select", [("list", "list"), ("move", "move"), ("delete", "delete")], str(self.state_values.get("find-duplicates-action") or "list"), help_text="Choose what the duplicates scan should do with detected duplicates: list, move, or delete.", required=True, flag="--find-duplicates <action> <folders>")
        else:
            specs = build_argument_specs(self.schema, "standalone_features", selected, True)
            if not specs:
                self._muted_label(options, "No extra arguments required.").pack(fill="x")
            for spec in specs:
                self.build_field_widgets(options, spec["field"], required=spec["required"], context="standalone_features")

    # ------------------------------------------------------------------
    # Settings views
    # ------------------------------------------------------------------
    def build_settings_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        tabs = self.tk.Frame(parent, bg=theme["root_bg"])
        tabs.pack(fill="x", pady=(0, 16))
        for key in SETTINGS_VIEWS:
            style = "PM.SegmentActive.TButton" if key == self.active_general_tab else "PM.Segment.TButton"
            self.ttk.Button(tabs, text=SETTINGS_TAB_LABELS[key], command=lambda k=key: self.select_view(k), style=style).pack(side="left", padx=(0, 6))
        if self.active_general_tab == "general":
            return self.build_general_arguments_widgets(parent)
        if self.active_general_tab == "features_config":
            return self.build_config_widgets(parent)
        return self.build_app_settings_widgets(parent)

    def build_general_arguments_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        self._muted_label(parent, "Global arguments shared by every feature: logging, execution, folder names and filters. They are the baseline for each run; a feature can override some of them, for example the migration filters.", size=11).pack(fill="x", pady=(0, 14))
        container = self.tk.Frame(parent, bg=theme["root_bg"])
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1, uniform="general")
        container.grid_columnconfigure(1, weight=1, uniform="general")
        fields_by_dest = {field["dest"]: field for field in self.schema["general_tabs"]["general"]}
        used = set()
        group_blocks: List[tuple[str, List[Dict[str, Any]]]] = []
        for group in GENERAL_GROUPS:
            group_fields = [fields_by_dest[dest] for dest in group["dests"] if dest in fields_by_dest]
            if not group_fields:
                continue
            used.update(field["dest"] for field in group_fields)
            group_blocks.append((group["title"], group_fields))
        remaining = [field for field in self.schema["general_tabs"]["general"] if field["dest"] not in used]
        if remaining:
            group_blocks.append(("Other", remaining))
        for index, (title, group_fields) in enumerate(group_blocks):
            outer = self.tk.Frame(container, bg=theme["surface"], highlightthickness=1, highlightbackground=theme["border"])
            outer.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 8, 8 if index % 2 == 0 else 0), pady=8)
            card = self.tk.Frame(outer, bg=theme["surface"])
            card.pack(fill="both", expand=True, padx=20, pady=18)
            self._step_header(card, None, title)
            for field in group_fields:
                self.build_field_widgets(card, field, context="general")
        actions = self.tk.Frame(parent, bg=theme["root_bg"])
        actions.pack(fill="x", pady=(12, 0))
        self.ttk.Button(actions, text="⟲  Restore defaults", command=self.restore_general_arguments_defaults, style="PM.Secondary.TButton").pack(side="left")
        return []

    def _config_section_has_credentials(self, section: Dict[str, Any], account_id: str) -> bool:
        section_name = str(section.get("name") or "")
        values = self.config_values.get(section_name, {})
        for field in section.get("fields") or []:
            if str(field.get("account_id") or "") != str(account_id):
                continue
            key = str(field.get("key") or "")
            if not re.search(r"(USERNAME|PASSWORD|API_KEY|CLIENT_ID|CLIENT_SECRET|REFRESH_TOKEN|TOKEN)", key, re.IGNORECASE):
                continue
            if str(values.get(key, "") or "").strip():
                return True
        return False

    def build_config_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        self.config_widget_map = {}
        toolbar = self.tk.Frame(parent, bg=theme["root_bg"])
        toolbar.pack(fill="x", pady=(0, 14))
        self._muted_label(toolbar, f"Editing {self.current_config_path()}", size=10, wrap=False).pack(side="left")
        self.save_config_button = self.ttk.Button(toolbar, text="Save config", command=self.action_save_config, style="PM.Primary.TButton")
        self.save_config_button.pack(side="right")
        self.load_config_button = self.ttk.Button(toolbar, text="Load config…", command=self.action_load_config, style="PM.Secondary.TButton")
        self.load_config_button.pack(side="right", padx=(0, 8))

        layout = self.tk.Frame(parent, bg=theme["root_bg"])
        layout.pack(fill="both", expand=True)
        layout.grid_columnconfigure(1, weight=1)
        section_list = self.tk.Frame(layout, bg=theme["root_bg"], width=240)
        section_list.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        for section in self.config_sections:
            name = str(section.get("name") or "")
            selected = name == self.active_config_section
            item_bg = theme["surface"] if selected else theme["root_bg"]
            item = self.tk.Frame(section_list, bg=item_bg, highlightthickness=1, highlightbackground=(theme["accent"] if selected else theme["root_bg"]), cursor="hand2")
            item.pack(fill="x", pady=2)
            label = self.tk.Label(item, text=name, bg=item_bg, fg=theme["text"], font=(UI_FONT, 11, "bold" if selected else "normal"), anchor="w", width=20, cursor="hand2")
            label.pack(side="left", padx=12, pady=10)
            selector = section.get("account_selector") or {}
            accounts = [str(acc) for acc in selector.get("accounts") or []]
            if accounts:
                configured = sum(1 for acc in accounts if self._config_section_has_credentials(section, acc))
                status_text = f"{configured} account{'s' if configured != 1 else ''}" if configured else "Not set"
                self.tk.Label(item, text=status_text, bg=(theme["success_soft"] if configured else theme["surface_3"]), fg=(theme["success"] if configured else theme["muted"]), font=(UI_FONT, 8, "bold"), padx=6).pack(side="right", padx=10)

            def select_section(_event: Any = None, section_name: str = name) -> None:
                if section_name == self.active_config_section:
                    return
                self.active_config_section = section_name
                self.ensure_config_account_selection()
                self.rebuild_content()

            for widget in (item, label):
                widget.bind("<Button-1>", select_section, add="+")

        form_outer = self.tk.Frame(layout, bg=theme["surface"], highlightthickness=1, highlightbackground=theme["border"])
        form_outer.grid(row=0, column=1, sticky="new")
        form = self.tk.Frame(form_outer, bg=theme["surface"])
        form.pack(fill="both", expand=True, padx=20, pady=18)
        current_section = next((section for section in self.config_sections if section["name"] == self.active_config_section), None)
        if not current_section:
            self._muted_label(form, "No configuration section selected.").pack(anchor="w")
            return []
        self._step_header(form, None, str(current_section["name"]))
        if str(current_section.get("description") or "").strip():
            self._muted_label(form, str(current_section.get("description") or "").strip()).pack(fill="x", pady=(0, 10))
        fields = list(current_section.get("fields") or [])
        global_fields = [field for field in fields if not str(field.get("account_id") or "")]
        account_fields = [field for field in fields if str(field.get("account_id") or "")]
        for field in global_fields:
            self.build_config_field_widgets(form, current_section["name"], field)
        selector = current_section.get("account_selector") or {}
        if selector.get("enabled"):
            section_name = current_section["name"]
            selected_account = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
            tabs = self.tk.Frame(form, bg=theme["surface"])
            tabs.pack(fill="x", pady=(4, 12))
            self.tk.Label(tabs, text="Account", bg=theme["surface"], fg=theme["text"], font=(UI_FONT, 11, "bold")).pack(side="left", padx=(0, 10))
            for account in [str(acc) for acc in selector.get("accounts") or []]:
                configured = self._config_section_has_credentials(current_section, account)
                style = "PM.SegmentActive.TButton" if account == selected_account else "PM.Segment.TButton"
                text = f"{'●' if configured else '○'}  Account {account}"

                def select_account(acc: str = account, sec: str = section_name) -> None:
                    if acc == str(self.active_config_account.get(sec) or ""):
                        return
                    self.active_config_account[sec] = acc
                    self.rebuild_content()

                self.ttk.Button(tabs, text=text, command=select_account, style=style).pack(side="left", padx=(0, 6))
            section_values = self.config_values.get(section_name, {})
            visible_account_fields = [
                field for field in account_fields
                if str(field.get("account_id") or "") == selected_account
                and not immich_field_hidden_by_auth_method(section_name, str(field.get("key") or ""), section_values)
            ]
            for field in visible_account_fields:
                self.build_config_field_widgets(form, section_name, field)
        else:
            for field in account_fields:
                self.build_config_field_widgets(form, current_section["name"], field)
        return []

    def build_app_settings_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        card = self._card(parent)
        self._step_header(card, None, "Appearance")
        self.build_select_row(card, "Theme", "theme-select", THEME_CHOICES, self.selected_theme, help_text="Select the visual theme used by the desktop GUI.", segmented=True)
        card = self._card(parent)
        self._step_header(card, None, "Session")
        self.build_boolean_toggle_row(card, "Remember UI state", "remember-state", self.remember_state, help_text="Persist the current desktop UI state, selected tabs, and entered values between sessions.")
        self._muted_label(card, f"State file: {TK_STATE_PATH}").pack(fill="x", pady=(8, 0))
        self._muted_label(card, f"Config file in use: {self.current_config_path()}").pack(fill="x", pady=(2, 0))
        buttons = self.tk.Frame(card, bg=theme["surface"])
        buttons.pack(fill="x", pady=(12, 0))
        self.save_ui_button = self.ttk.Button(buttons, text="Save UI state", command=self.action_save_ui_state, style="PM.Secondary.TButton")
        self.save_ui_button.pack(side="left")
        return []

    # ------------------------------------------------------------------
    # Field builders
    # ------------------------------------------------------------------
    def build_select_row(
        self,
        parent: Any,
        label: str,
        widget_id: str,
        options: List[tuple[str, Any]],
        value: Any,
        *,
        help_text: str = "",
        accent_label: bool = False,
        config_wide: bool = False,
        required: bool = False,
        flag: str = "",
        segmented: bool | None = None,
    ) -> None:
        container = self._field_container(parent)
        self._field_title(container, label, required)
        values = [str(label_text) for label_text, _ in options]
        mapping = {str(label_text): str(option_value) for label_text, option_value in options}
        reverse = {str(option_value): str(label_text) for label_text, option_value in options}
        current_value = str(value or "")
        selected_label = reverse.get(current_value, values[0] if values else "")
        var = self.tk.StringVar(value=selected_label)

        def on_change(_event: Any = None) -> None:
            selected = mapping.get(var.get(), "")
            if widget_id == "find-duplicates-action-select":
                self.state_values["find-duplicates-action"] = selected
                self.update_command_preview()
                return
            if widget_id == "config-section-select":
                if selected == self.active_config_section:
                    return
                self.active_config_section = selected
                self.ensure_config_account_selection()
                self.rebuild_content()
                return
            if widget_id == "config-account-select":
                if selected == str(self.active_config_account.get(self.active_config_section) or ""):
                    return
                self.active_config_account[self.active_config_section] = selected
                self.rebuild_content()
                return
            if widget_id == "theme-select":
                if selected == self.selected_theme:
                    return
                self.selected_theme = selected or "ocean"
                self.apply_theme(rebuild=True)
                self.persist_ui_state()
                return
            if widget_id.startswith("field-"):
                dest = widget_id.replace("field-", "", 1)
                if (
                    dest == "dup-asset-keeper"
                    and bool(self.state_values.get("dup-immich-native-deletion", False))
                    and selected != "better-quality"
                ):
                    var.set(reverse.get("better-quality", "better-quality"))
                    return
                self.state_values[dest] = selected
                if dest == "dup-asset-keeper":
                    self.rebuild_content()
                self.update_command_preview()
                return
            if widget_id.startswith("config-"):
                mapped = self.config_widget_map.get(widget_id)
                if mapped:
                    section_name, key = mapped
                    previous = str(self.config_values.get(section_name, {}).get(key, "") or "")
                    self.config_values.setdefault(section_name, {})[key] = selected
                    if IMMICH_AUTH_METHOD_KEY_PATTERN.match(key) and selected != previous:
                        self.rebuild_content()

        use_segmented = segmented if segmented is not None else (
            widget_id.startswith("field-") and 1 < len(values) <= 5 and all(len(item) <= 14 for item in values)
        )
        if use_segmented:
            row = self.tk.Frame(container, bg=container.cget("bg"))
            row.pack(fill="x", pady=(6, 0))
            buttons: Dict[str, Any] = {}

            def pick(option_label: str) -> None:
                var.set(option_label)
                on_change()
                for text, button in buttons.items():
                    if self._widget_exists(button):
                        button.configure(style=("PM.SegmentActive.TButton" if text == var.get() else "PM.Segment.TButton"))

            for option_label in values:
                button = self.ttk.Button(
                    row,
                    text=option_label,
                    command=lambda text=option_label: pick(text),
                    style=("PM.SegmentActive.TButton" if option_label == selected_label else "PM.Segment.TButton"),
                )
                button.pack(side="left", padx=(0, 4))
                self._bind_help(button, help_text)
                buttons[option_label] = button
        else:
            combo_height = min(max(len(values), 1), 25)
            combo = self.ttk.Combobox(
                container,
                textvariable=var,
                values=values,
                state="readonly",
                style="PM.TCombobox",
                height=combo_height,
                font=(UI_FONT, 11),
            )
            combo.pack(fill="x", pady=(6, 0))
            self._bind_help(combo, help_text)
            self._bind_context_menu(combo)

            def on_combo_change(_event: Any = None) -> None:
                self._clear_combobox_selection(combo)
                on_change()

            combo.bind("<<ComboboxSelected>>", on_combo_change)
        self._field_meta(container, help_text, flag)

    def build_boolean_toggle_row(self, parent: Any, label: str, dest: str, value: bool, help_text: str = "", *, required: bool = False, flag: str = "") -> None:
        theme = self.current_theme()
        row = self.tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", pady=(0, 14))
        switch = self.tk.Canvas(row, width=42, height=24, bd=0, highlightthickness=0, cursor="hand2", bg=parent.cget("bg"))
        switch.pack(side="left", anchor="n", padx=(0, 12), pady=(1, 0))

        def toggle(_event: Any = None, d: str = dest) -> None:
            self.set_boolean_toggle(d, not (self.remember_state if d == "remember-state" else bool(self.state_values.get(d))))

        switch.bind("<Button-1>", toggle)
        text = self.tk.Frame(row, bg=parent.cget("bg"))
        text.pack(side="left", fill="x", expand=True)
        title = self.tk.Label(text, text=label, bg=parent.cget("bg"), fg=theme["text"], font=(UI_FONT, 11, "bold"), anchor="w", cursor="hand2")
        title.pack(fill="x")
        title.bind("<Button-1>", toggle)
        if required:
            self.tk.Label(text, text="Required", bg=theme["danger_soft"], fg=theme["danger"], font=(UI_FONT, 8, "bold"), padx=6).pack(anchor="w")
        self._field_meta(text, help_text, flag)
        self._bind_help(switch, help_text)
        self._bind_help(title, help_text)
        self.bool_toggle_widgets[dest] = switch
        self.refresh_boolean_toggle(dest, value)

    def set_boolean_toggle(self, dest: str, value: bool) -> None:
        if dest == "dup-immich-native-deletion" and not (
            bool(self.state_values.get("dup-immich-native-algorithm", True))
        ):
            value = False
        if dest == "merge-duplicate-locations" and bool(
            self.state_values.get("dup-immich-native-deletion", False)
        ):
            value = False
        if dest == "remember-state":
            self.remember_state = value
        else:
            self.state_values[dest] = value
        if dest == "dup-immich-native-algorithm":
            self.state_values["dup-immich-native-deletion"] = False
            self.state_values["dup-asset-keeper"] = (
                "more-people/tags-then-better-quality" if value else "more-people/tags-then-oldest"
            )
            self.refresh_boolean_toggle("dup-immich-native-deletion", bool(value))
            self.rebuild_content()
        elif dest == "dup-immich-native-deletion":
            if value:
                self.state_values["dup-asset-keeper"] = "better-quality"
                self.state_values["merge-duplicate-locations"] = False
            self.rebuild_content()
        elif dest == "try-small-albums-grouping":
            self.rebuild_content()
        self.refresh_boolean_toggle(dest, value)
        self.update_command_preview()

    def refresh_boolean_toggle(self, dest: str, value: bool) -> None:
        theme = self.current_theme()
        switch = self.bool_toggle_widgets.get(dest)
        if not switch or not self._widget_exists(switch):
            return
        disabled = (
            dest == "dup-immich-native-deletion" and not (
                bool(self.state_values.get("dup-immich-native-algorithm", True))
            )
        ) or (
            dest == "merge-duplicate-locations"
            and bool(self.state_values.get("dup-immich-native-deletion", False))
        )
        if disabled:
            track_fill = theme["surface_3"]
        else:
            track_fill = self.tone_ink(self.active_tone()) if value else theme["switch_off"]
        thumb_fill = "#ffffff"
        switch.configure(cursor="arrow" if disabled else "hand2")
        switch.delete("all")
        switch.create_oval(1, 1, 23, 23, fill=track_fill, outline=track_fill)
        switch.create_rectangle(12, 1, 30, 23, fill=track_fill, outline=track_fill)
        switch.create_oval(19, 1, 41, 23, fill=track_fill, outline=track_fill)
        thumb_x = 21 if value else 4
        switch.create_oval(thumb_x, 4, thumb_x + 16, 20, fill=thumb_fill, outline=thumb_fill)

    def build_pseudo_text_field(self, parent: Any, label: str, dest: str, value: Any, required: bool, help_text: str) -> None:
        self.build_input_block(parent, label, dest, str(value or ""), required, help_text, path_hint="", flag="--rename-albums <pattern> <replacement>")

    def build_pseudo_list_field(self, parent: Any, label: str, dest: str, value: Any, required: bool, help_text: str) -> None:
        joined = ", ".join(parse_folder_list_value(value))
        self.build_input_block(parent, label, dest, joined, required, help_text, path_hint="path", flag="--find-duplicates <action> <folders>")

    def build_input_block(self, parent: Any, label: str, dest: str, value: str, required: bool, help_text: str, *, path_hint: str = "", password: bool = False, disabled: bool = False, flag: str = "") -> None:
        container = self._field_container(parent)
        self._field_title(container, label, required)
        var = self.tk.StringVar(value=value)
        self.field_widget_map[dest] = var
        control = self.tk.Frame(container, bg=container.cget("bg"))
        control.pack(fill="x", pady=(6, 0))
        entry = self._entry(control, var)
        entry.configure(show="*" if password else "")
        entry.configure(state="disabled" if disabled else "normal")
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        if path_hint == "path":
            btn = self.ttk.Button(control, text="Browse…", command=lambda d=dest: self.browse_path(d), style="PM.Secondary.TButton")
            btn.configure(state="disabled" if disabled else "normal")
            btn.pack(side="left", padx=(8, 0))
            self._bind_help(btn, help_text or label)
        elif password:
            def reveal() -> None:
                entry.configure(show=("" if entry.cget("show") else "*"))

            self.ttk.Button(control, text="Show", command=reveal, style="PM.Secondary.TButton").pack(side="left", padx=(8, 0))
        self._bind_help(entry, help_text)
        self._field_meta(container, help_text, flag)

        def on_change(*_args: Any) -> None:
            field = get_field_by_dest(self.schema, dest)
            raw = var.get()
            if dest in {"rename-pattern", "replacement-pattern"}:
                self.state_values[dest] = raw
            elif dest == "find-duplicates-folders":
                self.state_values[dest] = parse_folder_list_value(raw)
            elif field and field.get("kind") == "list":
                self.state_values[dest] = to_list(raw)
            else:
                self.state_values[dest] = raw
            if dest in {"output-folder", "organize-output-folder-suffix"}:
                normalize_organize_local_folder_ui_state(self.state_values, self.schema)
                suffix_var = self.field_widget_map.get("organize-output-folder-suffix")
                normalized_suffix = str(self.state_values.get("organize-output-folder-suffix") or "")
                if suffix_var is not None and str(suffix_var.get() or "") != normalized_suffix:
                    suffix_var.set(normalized_suffix)
            self.update_command_preview()

        var.trace_add("write", on_change)

    def _field_display_label(self, field: Dict[str, Any]) -> str:
        dest = str(field.get("dest") or "")
        base_dest = dest[3:] if dest.startswith("am-") else (dest[6:] if dest.startswith("sfrcb-") else dest)
        if base_dest in FIELD_LABELS:
            return FIELD_LABELS[base_dest]
        return humanize_label(str(field.get("label") or ui_option_name(field) or dest))

    def build_field_widgets(self, parent: Any, field: Dict[str, Any], required: bool = False, context: str = "") -> None:
        field = normalize_field_for_context(field, context) or field
        dest = str(field.get("dest") or "")
        label = self._field_display_label(field)
        help_text = str(field.get("help") or "").strip()
        kind = str(field.get("kind") or "text")
        value = effective_interactive_field_value(field, self.state_values)
        path_hint = str(field.get("path_hint") or "")
        flag = str(field.get("long_option") or "")
        if dest == "process-duplicates":
            path_hint = "path"
        if kind in {"flag", "bool"}:
            if dest == "dup-immich-native-deletion" and not (
                bool(self.state_values.get("dup-immich-native-algorithm", True))
            ):
                value = False
                self.state_values[dest] = False
            if dest == "merge-duplicate-locations" and bool(
                self.state_values.get("dup-immich-native-deletion", False)
            ):
                value = False
                self.state_values[dest] = False
            self.build_boolean_toggle_row(parent, label, dest, bool(value), help_text=help_text, required=required, flag=flag)
            return
        if kind == "select":
            choices = list(field.get("choices") or [])
            if dest == "dup-asset-keeper" and not (
                self.active_module == "immich_photos" and bool(self.state_values.get("dup-immich-native-algorithm", True))
            ):
                choices = [choice for choice in choices if choice not in {"better-quality", "more-people/tags-then-better-quality"}]
                if value not in choices:
                    value = "more-people/tags-then-oldest"
                    self.state_values[dest] = value
            native_deletion_enabled = dest == "dup-asset-keeper" and bool(
                self.state_values.get("dup-immich-native-deletion", False)
            )
            if dest == "account-id":
                options = [(f"Account {choice}", str(choice)) for choice in choices]
            else:
                options = [
                    (
                        str(choice) if not native_deletion_enabled or choice == "better-quality"
                        else f"{choice} (unavailable while native deletion is enabled)",
                        str(choice),
                    )
                    for choice in choices
                ]
            self.build_select_row(parent, label, f"field-{dest}", options, value, help_text=help_text, required=required, flag=flag, segmented=(False if dest in {"account-id", "dup-asset-keeper"} else None))
            return
        if kind == "list":
            joined = ", ".join(to_list(value))
            self.build_input_block(parent, label, dest, joined, required, help_text, path_hint=path_hint, flag=flag)
            return
        disabled = dest == "small-album-max-assets" and not bool(
            self.state_values.get("try-small-albums-grouping", True)
        )
        self.build_input_block(parent, label, dest, "" if value is None else str(value), required, help_text,
                               path_hint=path_hint, password=bool(field.get("sensitive")), disabled=disabled, flag=flag)

    def build_config_field_widgets(self, parent: Any, section_name: str, field: Dict[str, Any]) -> None:
        theme = self.current_theme()
        key = str(field.get("key") or "")
        help_text = str(field.get("help") or "").strip()
        value = str(self.config_values.get(section_name, {}).get(key, ""))
        auth_match = IMMICH_AUTH_METHOD_KEY_PATTERN.match(key)
        if auth_match:
            # Immich accounts sign in with an API key or with username and password: only those fields are shown.
            widget_id = f"config-{len(self.config_widget_map)}"
            self.config_widget_map[widget_id] = (section_name, key)
            method = immich_auth_method(self.config_values.get(section_name, {}), auth_match.group(1))
            self.build_select_row(parent, "Sign in with", widget_id, IMMICH_AUTH_METHOD_OPTIONS, method, help_text=help_text, segmented=True)
            return
        container = self._field_container(parent)
        friendly = re.sub(r"_\d+$", "", key)
        for prefix in ("GOOGLE_PHOTOS_", "SYNOLOGY_", "IMMICH_", "NEXTCLOUD_", "APPLE_PHOTOS_", "APPLE_"):
            if friendly.startswith(prefix) and len(friendly) > len(prefix):
                friendly = friendly[len(prefix):]
                break
        self._field_title(container, humanize_label(friendly) if key != "timezone" else "Time zone", False)
        widget_id = f"config-{len(self.config_widget_map)}"
        self.config_widget_map[widget_id] = (section_name, key)
        choices = field.get("choices") or []
        if choices:
            values = [str(choice) for choice in choices]
            var = self.tk.StringVar(value=value if value in values else (values[0] if values else ""))
            combo = self.ttk.Combobox(container, textvariable=var, values=values, state="readonly", style="PM.TCombobox", font=(UI_FONT, 11))
            combo.pack(fill="x", pady=(6, 0))
            self._bind_help(combo, help_text)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _e, w=combo, v=var, s=section_name, k=key: (self._clear_combobox_selection(w), self.config_values.setdefault(s, {}).__setitem__(k, v.get())),
            )
        else:
            var = self.tk.StringVar(value=value)
            control = self.tk.Frame(container, bg=container.cget("bg"))
            control.pack(fill="x", pady=(6, 0))
            entry = self._entry(control, var)
            sensitive = bool(field.get("sensitive"))
            entry.configure(show="*" if sensitive else "")
            entry.pack(side="left", fill="x", expand=True, ipady=6)
            if sensitive:
                self.ttk.Button(control, text="Show", command=lambda e=entry: e.configure(show=("" if e.cget("show") else "*")), style="PM.Secondary.TButton").pack(side="left", padx=(8, 0))
            self._bind_help(entry, help_text)
            var.trace_add("write", lambda *_args, v=var, s=section_name, k=key: self.config_values.setdefault(s, {}).__setitem__(k, v.get()))
        self._field_meta(container, help_text, key)
        _ = theme

    def browse_path(self, dest: str) -> None:
        from tkinter import filedialog

        current = self.state_values.get(dest)
        current_path = ""
        if isinstance(current, list):
            current_path = current[0] if current else ""
        else:
            current_path = str(current or "")
        selected = filedialog.askdirectory(initialdir=str(Path(current_path).expanduser()) if current_path else str(self.launch_cwd))
        if not selected:
            return
        if dest == "find-duplicates-folders":
            self.state_values[dest] = [selected]
        else:
            self.state_values[dest] = selected
        var = self.field_widget_map.get(dest)
        if var is not None:
            var.set(selected)
        self.update_command_preview()

    # ------------------------------------------------------------------
    # Command preview, log and run state
    # ------------------------------------------------------------------
    def update_command_preview(self) -> None:
        self.config_path_var.set(f"Config: {self.current_config_path()}")
        if self.active_module == "upload_folder":
            self._set_readonly_text(self.preview_text, "Upload to Server is only available in the Web Interface.")
            self.refresh_action_buttons()
            return
        command = self._build_current_command()
        self._set_readonly_text(self.preview_text, command_preview_string(command))
        self.running_command = command
        self.refresh_action_buttons()

    def append_log(self, line: str) -> None:
        self.consume_log_output(f"{line}\n")

    def refresh_log_view(self) -> None:
        self._set_readonly_text(self.log_text, self.log_buffer.render_text(include_partial=True))
        self.log_text.see("end")

    def refresh_run_metadata(self) -> None:
        theme = self.current_theme()
        running = self.can_stop_job()
        if running:
            status = "Running"
            chip_bg, chip_fg = theme["success_soft"], theme["success"]
        elif self.run_exit_code is not None:
            status = "Finished" if self.run_exit_code == 0 else f"Failed (exit code {self.run_exit_code})"
            chip_bg, chip_fg = (theme["success_soft"], theme["success"]) if self.run_exit_code == 0 else (theme["danger_soft"], theme["danger"])
        else:
            status = "No job running"
            chip_bg, chip_fg = theme["surface_3"], theme["text_2"]
        self.activity_status_var.set(f"Status: {status}")
        self.activity_status_chip.configure(bg=chip_bg, fg=chip_fg)
        self.status_dot.configure(bg=theme["surface_3"], fg=(theme["success"] if running else (chip_fg if self.run_exit_code not in (None, 0) else theme["muted"])))
        elapsed_until = self.run_finished_at if self.run_finished_at is not None else time.time()
        elapsed_seconds = max(0, int(elapsed_until - self.run_started_at)) if self.run_started_at is not None else 0
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        last_updated = time.strftime("%H:%M:%S", time.localtime(self.run_last_updated_at)) if self.run_last_updated_at else "-"
        started = time.strftime("%H:%M:%S", time.localtime(self.run_started_at)) if self.run_started_at else "-"
        if self.external_dashboard_active:
            self.run_meta_var.set("Live Dashboard running in an external terminal window.")
        else:
            self.run_meta_var.set(f"Started: {started}    Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}    Last updated: {last_updated}")
        if self.running_command and (running or self.run_started_at is not None):
            self.activity_command_var.set(command_preview_string(self.running_command))

    def consume_log_output(self, text: str) -> None:
        update = self.log_buffer.append_text(text)
        if text:
            self.run_last_updated_at = time.time()
        self.refresh_run_metadata()
        if update.replaced_progress or update.partial_changed or update.appended_lines:
            self.refresh_log_view()

    def mark_run_started(self) -> None:
        self.run_module = self.active_module
        self.run_action_dest = str(self._selected_action_for_active_module() or "")
        self.run_started_at = time.time()
        self.run_finished_at = None
        self.run_exit_code = None
        self.run_last_updated_at = self.run_started_at
        self.activity_command_var.set(command_preview_string(self.running_command))
        self.refresh_run_metadata()
        self.refresh_action_buttons()
        self.select_view(VIEW_ACTIVITY)

    def mark_run_finished(self, exit_code: int) -> None:
        self.run_finished_at = time.time()
        self.run_last_updated_at = self.run_finished_at
        self.run_exit_code = int(exit_code)
        self.refresh_run_metadata()
        self.update_status(f"Job finished with exit code {exit_code}")
        self.refresh_action_buttons()
        if self.active_general_tab == VIEW_ACTIVITY:
            self.refresh_header()

    def poll_process_queue(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, tuple) and item and item[0] == "finished":
                self.running_process = None
                self.mark_run_finished(int(item[1]))
            elif isinstance(item, tuple) and item and item[0] == "dashboard_finished":
                self.external_dashboard_active = False
                self.external_dashboard_status_file = None
                self.external_dashboard_launcher_file = None
                self.external_dashboard_pid_file = None
                self.append_log(f"[internal] Live Dashboard finished with exit code {item[1]}")
                self.mark_run_finished(int(item[1]))
                self.root.after(0, self._restore_gui_focus)
            elif isinstance(item, tuple) and item and item[0] == "output":
                self.consume_log_output(str(item[1]))
            else:
                self.append_log(str(item))
        if self.can_stop_job():
            self.refresh_run_metadata()
        self.root.after(120, self.poll_process_queue)

    def _job_output_worker(self, process: subprocess.Popen[str]) -> None:
        try:
            if process.stdout is not None:
                pending: List[str] = []
                last_flush = time.monotonic()
                while True:
                    chunk = process.stdout.read(1)
                    if chunk == "":
                        break
                    pending.append(chunk)
                    now = time.monotonic()
                    if chunk in "\r\n" or (now - last_flush) >= 0.05:
                        self.output_queue.put(("output", "".join(pending)))
                        pending = []
                        last_flush = now
                if pending:
                    self.output_queue.put(("output", "".join(pending)))
            return_code = process.wait()
        except Exception as exc:
            self.output_queue.put(f"[internal] {exc}")
            return_code = -1
        self.output_queue.put(("finished", return_code))

    def can_run_job(self) -> bool:
        return not self.can_stop_job() and not self.external_dashboard_active

    def can_stop_job(self) -> bool:
        return (
            (self.running_process is not None and self.running_process.poll() is None)
            or self.external_dashboard_active
        )

    def can_exit_app(self) -> bool:
        return not self.can_stop_job() and not self.external_dashboard_active

    def refresh_action_buttons(self) -> None:
        if not hasattr(self, "run_button"):
            return
        can_run = self.can_run_job()
        can_stop = self.can_stop_job()
        can_exit = self.can_exit_app()
        can_send = bool(str(self.job_input_var.get() or "").strip())
        accepting_input = self.running_process is not None and self.running_process.poll() is None
        self.run_button.configure(state=("normal" if can_run else "disabled"))
        self.stop_button.configure(state=("normal" if can_stop else "disabled"))
        self.exit_button.configure(state=("normal" if can_exit else "disabled"))
        self.job_input_send.configure(state=("normal" if can_send and accepting_input else "disabled"))
        self.job_input_yes.configure(state=("normal" if accepting_input else "disabled"))
        self.job_input_no.configure(state=("normal" if accepting_input else "disabled"))
        self.refresh_navigation()

    # Compatibility no-ops for the collapsible panels of the previous layout.
    def apply_panel_states(self) -> None:
        return None

    def apply_runtime_layout(self) -> None:
        return None

    def sync_content_panel_for_run_state(self, running: bool) -> None:
        self.refresh_action_buttons()

    def action_run_job(self) -> None:
        if self.active_module == "upload_folder":
            self.update_status("Upload to Server is only available in the Web Interface.")
            return
        if self.running_process is not None and self.running_process.poll() is None:
            self.update_status("A job is already running.")
            return
        if self.external_dashboard_active:
            self.update_status("A Live Dashboard run is already active in an external terminal.")
            return
        if self._should_run_dashboard_in_external_terminal():
            from tkinter import messagebox

            confirmed = messagebox.askyesno(
                "Automatic Migration Live Dashboard",
                "Live Dashboard is enabled for Automatic Migration.\n\n"
                "If you continue, PhotoMigrator will open this run in an external terminal window so the full-screen dashboard can render there.\n\n"
                "If you choose No, the same migration will run only for this execution without Live Dashboard and the output will stay embedded in the GUI Activity log.",
                parent=self.root,
            )
            if confirmed:
                command = self._build_current_command(dashboard_enabled=True)
                self.running_command = command
                self.log_buffer.clear()
                self._set_readonly_text(self.log_text, "")
                self.append_log(f"> {command_to_string(command)}")
                try:
                    self._launch_dashboard_job_in_external_terminal(command)
                except Exception as exc:
                    self.update_status(f"Unable to launch Live Dashboard in external terminal: {exc}")
                    self.append_log(f"[internal] External Live Dashboard launch failed: {exc}")
                    return
                self.append_log("[internal] Live Dashboard launched in an external terminal window.")
                self.update_status("Live Dashboard launched in an external terminal window.")
                return
            command = self._build_current_command(dashboard_enabled=False)
            self.running_command = command
            self.log_buffer.clear()
            self._set_readonly_text(self.log_text, "")
            self.append_log(f"> {command_to_string(command)}")
            self.append_log("[internal] Live Dashboard disabled for this run by user confirmation.")
        else:
            command = self._build_current_command()
            self.log_buffer.clear()
            self._set_readonly_text(self.log_text, "")
            self.append_log(f"> {command_to_string(command)}")
        self.running_command = command
        env = build_ui_subprocess_env(ui_mode="gui")
        # Confirmation prompts are answered from the Activity view through the piped stdin.
        env["PHOTOMIGRATOR_ALLOW_STDIN_PIPE"] = "1"
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.launch_cwd),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception as exc:
            self.update_status(f"Unable to start job: {exc}")
            self.append_log(f"[internal] Unable to start job: {exc}")
            return
        self.running_process = process
        self.update_status("Job running...")
        self.mark_run_started()
        threading.Thread(target=self._job_output_worker, args=(process,), daemon=True).start()

    def action_stop_job(self) -> None:
        if self.external_dashboard_active:
            self._stop_external_dashboard_job()
            return
        if self.running_process is None or self.running_process.poll() is not None:
            self.update_status("No running job to stop.")
            return
        try:
            self.running_process.terminate()
            self.update_status("Stop signal sent to job.")
            self.refresh_action_buttons()
        except Exception as exc:
            self.update_status(f"Unable to stop job: {exc}")

    def _stop_external_dashboard_job(self) -> None:
        pid_path = self.external_dashboard_pid_file
        if pid_path is None or not pid_path.exists():
            self.update_status("Live Dashboard is starting; wait a moment and try Stop again.")
            return
        try:
            process_id = int(pid_path.read_text(encoding="utf-8", errors="replace").strip())
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", str(process_id), "/T", "/F"], check=True, capture_output=True)
            else:
                os.kill(process_id, signal.SIGTERM)
            self.update_status("Stop signal sent to Live Dashboard job.")
            self.refresh_action_buttons()
        except Exception as exc:
            self.update_status(f"Unable to stop Live Dashboard job: {exc}")

    def action_request_exit(self) -> None:
        if not self.can_exit_app():
            self.update_status("Stop the running job before exiting.")
            self.refresh_action_buttons()
            return
        from tkinter import messagebox

        confirmed = messagebox.askyesno("Exit PhotoMigrator", "Are you sure you want to close the tool?", parent=self.root)
        if not confirmed:
            self.update_status("Exit canceled.")
            return
        self.persist_ui_state()
        try:
            self.root.destroy()
        except Exception:
            pass

    def action_send_job_input(self, preset: str | None = None) -> None:
        if self.running_process is None or self.running_process.stdin is None or self.running_process.poll() is not None:
            self.update_status("No running job is accepting input.")
            return
        text = str(preset if preset is not None else (self.job_input_var.get() or "")).rstrip("\r\n")
        if not text:
            self.update_status("Input is empty.")
            return
        try:
            self.running_process.stdin.write(text + "\n")
            self.running_process.stdin.flush()
            self.append_log(f">>> {text}")
            if preset is None:
                self.job_input_var.set("")
            self.update_status("Input sent to job.")
        except Exception as exc:
            self.update_status(f"Unable to send input: {exc}")

    def action_copy_command(self) -> None:
        text = str(getattr(self.preview_text, "_pm_text_body", "") or "").strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.update_status("Command copied to clipboard.")

    def action_copy_log(self) -> None:
        text = self.log_text.get("1.0", "end-1c")
        if not text.strip():
            self.update_status("The log is empty.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.update_status("Log copied to clipboard.")

    def action_open_help(self) -> None:
        help_index = self.project_root / "help"
        target = HELP_URL
        try:
            webbrowser.open(target)
            self.update_status(f"Opening help: {target}" if not help_index.exists() else f"Opening help: {target} (local copy in {help_index})")
        except Exception as exc:
            self.update_status(f"Unable to open help: {exc}")

    def action_save_config(self) -> None:
        from tkinter import messagebox

        target = self.current_config_path()
        confirmed = messagebox.askyesno(
            "Save Config",
            f"This will save the current configuration editor values to:\n\n{target}",
            parent=self.root,
        )
        if not confirmed:
            self.update_status("Save Config canceled.")
            return
        save_config_editor_values(target, self.config_values, self.config_template_text, self.config_schema)
        self.update_status(f"Config.ini saved to {target}")
        if self.active_general_tab == "features_config":
            self.rebuild_content()

    def action_load_config(self) -> None:
        from tkinter import filedialog, messagebox

        selected = filedialog.askopenfilename(
            title="Load Config",
            initialdir=str(self.current_config_path().parent),
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            parent=self.root,
        )
        if not selected:
            self.update_status("Load Config canceled.")
            return
        try:
            selected_path = validate_ui_config_file(Path(selected))
        except Exception as exc:
            messagebox.showerror("Invalid Config", f"Unable to load the selected config file:\n\n{exc}", parent=self.root)
            self.update_status(f"Invalid config file: {exc}")
            return

        current_path = self.current_config_path()
        selected_text = selected_path.read_text(encoding="utf-8", errors="replace")
        current_text = current_path.read_text(encoding="utf-8", errors="replace") if current_path.exists() else ""
        try:
            if selected_path.samefile(current_path):
                self.reload_config_model()
                if self.active_general_tab == "features_config":
                    self.rebuild_content()
                messagebox.showinfo(
                    "Load Config",
                    "The selected config file is already the active file:\n\n"
                    f"{current_path}\n\n"
                    "No overwrite is needed because the content is the same.",
                    parent=self.root,
                )
                self.update_status(f"Selected config is already the active file: {current_path}")
                return
        except Exception:
            pass

        if selected_text == current_text:
            messagebox.showinfo(
                "Load Config",
                "The selected config file has the same content as the current active config file.\n\n"
                f"Current file:\n{current_path}\n\n"
                f"Selected file:\n{selected_path}\n\n"
                "No overwrite is needed.",
                parent=self.root,
            )
            self.update_status("Selected config has the same content as the current active config.")
            return

        confirmed = messagebox.askyesno(
            "Load Config",
            "This will overwrite the current configuration file:\n\n"
            f"{current_path}\n\n"
            "with the selected file:\n\n"
            f"{selected_path}\n\n"
            "Do you want to continue?",
            parent=self.root,
        )
        if not confirmed:
            self.update_status("Load Config canceled.")
            return

        current_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(selected_path, current_path)
        self.reload_config_model()
        if self.active_general_tab == "features_config":
            self.rebuild_content()
        self.update_status(f"Loaded config from {selected_path} into {current_path}")

    def action_save_ui_state(self) -> None:
        from tkinter import messagebox

        confirmed = messagebox.askyesno(
            "Save UI State",
            f"This will save the current desktop UI state to:\n\n{TK_STATE_PATH}",
            parent=self.root,
        )
        if not confirmed:
            self.update_status("Save UI State canceled.")
            return
        self.persist_ui_state(force=True)
        self.update_status(f"UI state saved to {TK_STATE_PATH}")

    def persist_ui_state(self, force: bool = False) -> None:
        if not self.remember_state and not force:
            return
        try:
            self.window_geometry = str(self.root.winfo_geometry() or self.window_geometry)
        except Exception:
            pass
        persisted_view = self.active_general_tab if self.active_general_tab != VIEW_ACTIVITY else VIEW_FEATURE
        payload = {
            "values": self.state_values,
            "ui_state": {
                "active_module": self.active_module,
                "active_general_tab": persisted_view,
                "last_settings_view": self.ui_state.get("last_settings_view", "features_config"),
                "cloud_action_dest": self.cloud_action_dest,
                "standalone_action_dest": self.standalone_action_dest,
                "migration_endpoints": self.migration_endpoints_state,
                "active_config_section": self.active_config_section,
                "active_config_account": self.active_config_account,
                "theme": self.selected_theme,
                "remember_state": self.remember_state,
                "expanded_sections": self.expanded_sections,
                "window_geometry": self.window_geometry,
            },
        }
        save_json_file(TK_STATE_PATH, payload)

    def on_close(self) -> None:
        self.action_request_exit()

    def mainloop(self) -> None:
        self.root.mainloop()


def run_tk_gui(project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None) -> None:
    app = PhotoMigratorTkGUI(project_root=project_root, cli_entrypoint=cli_entrypoint, initial_values=initial_values)
    app.mainloop()
