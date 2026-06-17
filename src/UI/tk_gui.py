from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from Core.GlobalVariables import TOOL_VERSION

from UI.shared import (
    CLOUD_ACTIONS_AVAILABLE_BY_TAB,
    CompactLogBuffer,
    CONFIG_EDITOR_SECTIONS_ORDER,
    FEATURE_LABELS,
    GENERAL_GROUPS,
    GENERAL_TAB_NAMES,
    MODULE_TAB_NAMES,
    TIMEZONE_CHOICES,
    build_external_terminal_command,
    build_ui_subprocess_env,
    build_argument_specs,
    build_full_command,
    build_parser_schema,
    command_preview_string,
    command_to_string,
    compose_migration_endpoint,
    default_state_values,
    get_field_by_dest,
    load_config_editor_model,
    load_json_file,
    normalize_field_for_context,
    parse_find_duplicates_value,
    parse_migration_endpoint,
    parse_folder_list_value,
    parse_rename_albums_value,
    resolve_ui_config_path,
    save_config_editor_values,
    save_json_file,
    to_list,
    ui_option_name,
    validate_ui_config_file,
)

TK_STATE_PATH = Path(os.environ.get("PHOTOMIGRATOR_TK_GUI_STATE_PATH", str(Path.home() / ".photomigrator_tk_gui_state.json")))
ANSI_CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([@-~])")
THEME_CHOICES = [("Ocean", "ocean"), ("Emerald", "emerald"), ("Sunset", "sunset"), ("Dark", "dark")]
MODULE_GROUP_CLASSES = {
    "automatic_migration": ("#c9ebcf", "#22462a"),
    "google_takeout": ("#f8f1c8", "#7a6410"),
    "icloud_takeout": ("#f8f1c8", "#7a6410"),
    "google_photos": ("#eee0d1", "#5f432b"),
    "synology_photos": ("#eee0d1", "#5f432b"),
    "immich_photos": ("#eee0d1", "#5f432b"),
    "nextcloud_photos": ("#eee0d1", "#5f432b"),
    "standalone_features": ("#e6d8ef", "#54366f"),
    "upload_folder": ("#efc8c8", "#6c2727"),
}
MODULE_ACTIVE_STYLE_OVERRIDES = {
    "google_takeout": ("#f1cf57", "#5a4700"),
    "icloud_takeout": ("#f1cf57", "#5a4700"),
}
MODULE_TO_CONFIG_SECTION = {
    "google_photos": "Google Photos",
    "synology_photos": "Synology Photos",
    "immich_photos": "Immich Photos",
    "nextcloud_photos": "NextCloud Photos",
}
INTERACTIVE_MODULE_TAB_NAMES = {key: label for key, label in MODULE_TAB_NAMES.items() if key != "upload_folder"}
THEMES = {
    "ocean": {
        "root_bg": "#11161f",
        "panel_bg": "#152231",
        "panel_fg": "#dfeaf8",
        "log_bg": "#12202e",
        "log_fg": "#d9e8f8",
        "border": "#3b78b7",
        "sidebar_bg": "#131c28",
        "text": "#f4f7fb",
        "muted": "#8ea3bf",
        "tab_bg": "#152131",
        "tab_fg": "#d6dfeb",
        "tab_active_bg": "#2e4f78",
        "tab_active_fg": "#ffffff",
        "accent": "#7fd4ff",
        "entry_bg": "#0f1722",
        "entry_fg": "#f4f7fb",
    },
    "emerald": {
        "root_bg": "#0f1714",
        "panel_bg": "#0d1713",
        "panel_fg": "#def4e7",
        "log_bg": "#0b1411",
        "log_fg": "#def4e7",
        "border": "#3f8f72",
        "sidebar_bg": "#13201b",
        "text": "#edf7f1",
        "muted": "#9dc3b0",
        "tab_bg": "#173127",
        "tab_fg": "#d6ebe0",
        "tab_active_bg": "#2d6b55",
        "tab_active_fg": "#ffffff",
        "accent": "#7dffbf",
        "entry_bg": "#102018",
        "entry_fg": "#edf7f1",
    },
    "sunset": {
        "root_bg": "#1a1410",
        "panel_bg": "#18110d",
        "panel_fg": "#f7e6d7",
        "log_bg": "#140f0b",
        "log_fg": "#f7e6d7",
        "border": "#b26a3a",
        "sidebar_bg": "#231913",
        "text": "#fbf1e8",
        "muted": "#cfb39f",
        "tab_bg": "#35231a",
        "tab_fg": "#f0dfd1",
        "tab_active_bg": "#8d5630",
        "tab_active_fg": "#fff7f1",
        "accent": "#ffd29a",
        "entry_bg": "#221710",
        "entry_fg": "#fbf1e8",
    },
    "dark": {
        "root_bg": "#0c0f14",
        "panel_bg": "#0b1016",
        "panel_fg": "#d8e0ea",
        "log_bg": "#090d12",
        "log_fg": "#d8e0ea",
        "border": "#6d7a8d",
        "sidebar_bg": "#11161d",
        "text": "#e6ebf2",
        "muted": "#9aa7b7",
        "tab_bg": "#1a212b",
        "tab_fg": "#d0d9e4",
        "tab_active_bg": "#39485c",
        "tab_active_fg": "#ffffff",
        "accent": "#b8c7ff",
        "entry_bg": "#141a23",
        "entry_fg": "#e6ebf2",
    },
}


def tkinter_runtime_available() -> tuple[bool, str | None]:
    try:
        import tkinter  # noqa: F401
        return True, None
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


class ScrollableFrame:
    def __init__(self, parent: Any, bg: str):
        import tkinter as tk

        self.frame = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self.frame, highlightthickness=0, bd=0, bg=bg)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
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

    def _on_mousewheel(self, event: Any) -> None:
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        content_height = max(0, bbox[3] - bbox[1])
        if content_height <= self.canvas.winfo_height() + 2:
            return
        delta = int(-1 * (event.delta / 120)) if getattr(event, "delta", 0) else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_linux(self, event: Any) -> None:
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
        self.ui_state = dict(self.persisted.get("ui_state") or {})
        self.active_module = str(self.ui_state.get("active_module") or self.initial_values.get("active_module") or "automatic_migration")
        self.active_general_tab = str(self.ui_state.get("active_general_tab") or "feature")
        self.cloud_action_dest = dict(self.ui_state.get("cloud_action_dest") or {})
        self.standalone_action_dest = str(self.ui_state.get("standalone_action_dest") or "")
        self.migration_endpoints_state = dict(self.ui_state.get("migration_endpoints") or {})
        self.active_config_section = str(self.ui_state.get("active_config_section") or "")
        self.active_config_account = dict(self.ui_state.get("active_config_account") or {})
        self.selected_theme = str(self.ui_state.get("theme") or "ocean")
        self.remember_state = bool(self.ui_state.get("remember_state", True))
        self.window_geometry = str(self.ui_state.get("window_geometry") or "1480x920")
        self.field_widget_map: Dict[str, Any] = {}
        self.field_help_map: Dict[str, str] = {}
        self.config_widget_map: Dict[str, tuple[str, str]] = {}
        self.running_process: subprocess.Popen[str] | None = None
        self.running_command: List[str] = []
        self.output_queue: queue.Queue[str | tuple[str, int]] = queue.Queue()
        self.log_buffer = CompactLogBuffer()
        self.bool_toggle_widgets: Dict[str, Any] = {}
        self.auto_collapsed_content_for_run = False
        self.panel_collapsed = {
            "content": False,
            "description": False,
            "preview": False,
            "log": False,
            "status": False,
        }
        if self.active_module not in INTERACTIVE_MODULE_TAB_NAMES:
            self.active_module = "automatic_migration"
        self.reload_config_model()

        self.root = tk.Tk()
        self.root.title(f"PhotoMigrator {TOOL_VERSION} - Graphical User Interface (GUI)")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.geometry(self.window_geometry)
        self.root.minsize(1220, 760)
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
        self.refresh_module_buttons()
        self.refresh_top_tabs()
        self.refresh_action_buttons()
        self.rebuild_content()
        self.update_command_preview()
        self.apply_panel_states()
        self.apply_runtime_layout()
        self.root.after(120, self.poll_process_queue)

    def preferred_config_section(self) -> str:
        mapped = MODULE_TO_CONFIG_SECTION.get(self.active_module)
        if mapped:
            return mapped
        if self.active_config_section in CONFIG_EDITOR_SECTIONS_ORDER:
            return self.active_config_section
        return CONFIG_EDITOR_SECTIONS_ORDER[0]

    def current_config_path(self) -> Path:
        return resolve_ui_config_path(self.state_values.get("configuration-file"))

    def reload_config_model(self) -> None:
        model = load_config_editor_model(self.project_root, self.current_config_path())
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

    def _create_panel_toggle(self, parent: Any, panel_key: str) -> Any:
        label = self.tk.Label(parent, text=self._toggle_label(panel_key), width=2, anchor="center", cursor="hand2", font=("TkDefaultFont", 15, "bold"), padx=6, pady=0)
        label.bind("<Button-1>", lambda _e, p=panel_key: self.toggle_panel(p), add="+")
        return label

    def _create_panel_shell(self, parent: Any, title: str, panel_key: str, *, use_grid: bool = False) -> Tuple[Any, Any, Any, Any, Any]:
        panel = self.tk.LabelFrame(parent, text="", bd=2)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        topbar = self.tk.Frame(panel, bd=0)
        panel.configure(labelwidget=topbar)

        title_label = self.tk.Label(topbar, text=title, anchor="w", font=("TkDefaultFont", 10, "bold"), padx=0, pady=0)
        title_label.pack(side="left")

        toggle = self._create_panel_toggle(panel, panel_key)
        toggle.place(relx=1.0, x=-10, y=-12, anchor="ne")

        body = self.tk.Frame(panel, bd=0)
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 8))
        if use_grid:
            body.grid_rowconfigure(0, weight=1)
            body.grid_columnconfigure(0, weight=1)

        toggle.lift()

        return panel, topbar, title_label, toggle, body

    def _build_layout(self) -> None:
        tk = self.tk
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.LabelFrame(self.root, text="Feature Selector", bd=2)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=10)
        self.sidebar.configure(width=300)
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        self.sidebar_scroll = ScrollableFrame(self.sidebar, bg="#131c28")
        self.sidebar_scroll.frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.sidebar_actions = tk.Frame(self.sidebar)
        self.sidebar_actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))
        self.sidebar_actions.grid_columnconfigure(0, weight=1)
        self.sidebar_actions.grid_columnconfigure(1, weight=1)

        self.module_buttons: Dict[str, Any] = {}
        for idx, (key, label) in enumerate(INTERACTIVE_MODULE_TAB_NAMES.items()):
            btn = self.ttk.Button(self.sidebar_scroll.body, text=label, command=lambda tab=key: self.select_module(tab))
            btn.grid(row=idx, column=0, sticky="ew", pady=(0, 6))
            self.module_buttons[key] = btn
        self.sidebar_scroll.body.grid_columnconfigure(0, weight=1)

        self.run_button = self.ttk.Button(self.sidebar_actions, text="Run", command=self.action_run_job)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stop_button = self.ttk.Button(self.sidebar_actions, text="Stop", command=self.action_stop_job)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.exit_button = self.ttk.Button(self.sidebar_actions, text="Exit", command=self.action_request_exit)
        self.exit_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.main = tk.Frame(self.root)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(6, 10), pady=10)
        self.main.grid_rowconfigure(1, weight=4)
        self.main.grid_rowconfigure(2, weight=3)
        self.main.grid_columnconfigure(0, weight=1)

        self.topbar = tk.Frame(self.main)
        self.topbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.topbar.grid_columnconfigure(0, weight=1)
        self.tabs_left = tk.Frame(self.topbar)
        self.tabs_left.grid(row=0, column=0, sticky="w")
        self.tabs_right = tk.Frame(self.topbar)
        self.tabs_right.grid(row=0, column=1, sticky="e")

        self.general_tab_buttons: Dict[str, Any] = {}
        for idx, (key, label) in enumerate(GENERAL_TAB_NAMES.items()):
            btn = self.ttk.Button(self.tabs_left, text=label, command=lambda tab=key: self.select_general_tab(tab))
            btn.grid(row=0, column=idx, sticky="w", padx=(0, 6))
            self.general_tab_buttons[key] = btn

        self.save_config_button = self.ttk.Button(self.tabs_right, text="Save Config", command=self.action_save_config)
        self.save_config_button.grid(row=0, column=0, padx=(6, 0))
        self.save_ui_button = self.ttk.Button(self.tabs_right, text="Save UI State", command=self.action_save_ui_state)
        self.save_ui_button.grid(row=0, column=1, padx=(6, 0))
        self.load_config_button = self.ttk.Button(self.tabs_right, text="Load Config", command=self.action_load_config)
        self.load_config_button.grid(row=0, column=2, padx=(6, 0))

        self.content_panel, self.content_header, self.content_title_label, self.content_toggle_button, self.content_body = self._create_panel_shell(self.main, "", "content", use_grid=True)
        self.content_panel.grid(row=1, column=0, sticky="nsew")
        self.content_scroll = ScrollableFrame(self.content_body, bg="#0d141e")
        self.content_scroll.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.bottom = tk.Frame(self.main)
        self.bottom.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        self.bottom.grid_rowconfigure(2, weight=1)
        self.bottom.grid_columnconfigure(0, weight=1)

        self.description_panel, self.description_header, self.description_title_label, self.description_toggle_button, self.description_body = self._create_panel_shell(self.bottom, "Argument Description", "description")
        self.description_panel.grid(row=0, column=0, sticky="ew")
        self.description_var = tk.StringVar(value="Move focus to a field to see its description here.")
        self.description_text = self.tk.Label(self.description_body, textvariable=self.description_var, anchor="w", justify="left", padx=0, pady=0)
        self.description_text.pack(fill="x")

        self.preview_panel, self.preview_header, self.preview_title_label, self.preview_toggle_button, self.preview_body = self._create_panel_shell(self.bottom, "Command Preview", "preview", use_grid=True)
        self.preview_panel.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.preview_text = self._readonly_text(self.preview_body, height=3, auto_fit=False)
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        self.preview_scroll = tk.Scrollbar(self.preview_body, orient="vertical", command=self.preview_text.yview)
        self.preview_scroll.grid(row=0, column=1, sticky="ns")
        self.preview_text.configure(yscrollcommand=self._on_preview_text_scroll)
        self._on_preview_text_scroll("0.0", "1.0")

        self.log_panel, self.log_header, self.log_title_label, self.log_toggle_button, self.log_body = self._create_panel_shell(self.bottom, "Execution Log", "log", use_grid=True)
        self.log_panel.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        self.log_body.grid_rowconfigure(0, weight=1)
        self.log_body.grid_columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            self.log_body,
            height=10,
            wrap="word",
            state="normal",
            relief="flat",
            bd=0,
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            spacing1=0,
            spacing2=0,
            spacing3=0,
            takefocus=0,
            insertwidth=0,
        )
        self.log_text._pm_readonly = True
        self.log_text.bind("<Key>", lambda _e: "break")
        self.log_text.bind("<<Paste>>", lambda _e: "break")
        self.log_text.bind("<<Cut>>", lambda _e: "break")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_scroll = tk.Scrollbar(self.log_body, orient="vertical", command=self.log_text.yview)
        self.log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=self._on_log_text_scroll)
        self._on_log_text_scroll("0.0", "1.0")

        self.status_panel, self.status_header, self.status_title_label, self.status_toggle_button, self.status_body = self._create_panel_shell(self.bottom, "Status", "status")
        self.status_panel.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.status_var = tk.StringVar(value="Ready.")
        self.status_text = self.tk.Label(self.status_body, textvariable=self.status_var, anchor="w", justify="left", padx=0, pady=0)
        self.status_text.pack(fill="x")

        self.input_panel, self.input_header, self.input_title_label, self.input_toggle_spacer, self.input_row = self._create_panel_shell(self.bottom, "Process Input", "status")
        self.input_panel.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.input_toggle_spacer.place_forget()
        self.input_row.grid_columnconfigure(0, weight=1)
        self.job_input_var = tk.StringVar()
        self.job_input_var.trace_add("write", lambda *_args: self.refresh_action_buttons())
        self.job_input_entry = tk.Entry(self.input_row, textvariable=self.job_input_var)
        self.job_input_entry.grid(row=0, column=0, sticky="ew")
        self.job_input_send = self.ttk.Button(self.input_row, text="Send", command=self.action_send_job_input)
        self.job_input_send.grid(row=0, column=1, padx=(6, 0))
        self._setup_context_menus()

    def apply_theme(self, rebuild: bool = True) -> None:
        theme = self.current_theme()
        tk = self.tk
        self.root.configure(bg=theme["root_bg"])
        self.style.configure(
            "PM.TCombobox",
            fieldbackground=theme["entry_bg"],
            background=theme["entry_bg"],
            foreground=theme["entry_fg"],
            selectbackground=theme["entry_bg"],
            selectforeground=theme["entry_fg"],
            arrowsize=16,
        )
        self.style.map(
            "PM.TCombobox",
            fieldbackground=[("readonly", theme["entry_bg"]), ("focus", theme["entry_bg"])],
            background=[("readonly", theme["entry_bg"]), ("focus", theme["entry_bg"])],
            foreground=[("readonly", theme["entry_fg"]), ("focus", theme["entry_fg"])],
            selectbackground=[("readonly", theme["entry_bg"]), ("focus", theme["entry_bg"])],
            selectforeground=[("readonly", theme["entry_fg"]), ("focus", theme["entry_fg"])],
        )
        self.configure_button_styles()
        self.sidebar.configure(bg=theme["sidebar_bg"], fg=theme["accent"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.sidebar_scroll.frame.configure(bg=theme["sidebar_bg"])
        self.sidebar_scroll.canvas.configure(bg=theme["sidebar_bg"])
        self.sidebar_scroll.body.configure(bg=theme["sidebar_bg"])
        self.sidebar_actions.configure(bg=theme["sidebar_bg"])
        self.main.configure(bg=theme["root_bg"])
        self.bottom.configure(bg=theme["root_bg"])
        self.topbar.configure(bg=theme["root_bg"])
        self.tabs_left.configure(bg=theme["root_bg"])
        self.tabs_right.configure(bg=theme["root_bg"])
        self.content_panel.configure(bg=theme["panel_bg"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.content_header.configure(bg=theme["root_bg"])
        self.content_title_label.configure(bg=theme["root_bg"], fg=theme["accent"])
        self.content_body.configure(bg=theme["panel_bg"])
        self.content_scroll.frame.configure(bg=theme["panel_bg"])
        self.content_scroll.canvas.configure(bg=theme["panel_bg"])
        self.content_scroll.body.configure(bg=theme["panel_bg"])
        for panel, header, title, body in (
            (self.description_panel, self.description_header, self.description_title_label, self.description_body),
            (self.preview_panel, self.preview_header, self.preview_title_label, self.preview_body),
            (self.status_panel, self.status_header, self.status_title_label, self.status_body),
        ):
            panel.configure(bg=theme["panel_bg"], highlightbackground=theme["border"], highlightcolor=theme["border"])
            header.configure(bg=theme["root_bg"])
            title.configure(bg=theme["root_bg"], fg=theme["accent"])
            body.configure(bg=theme["panel_bg"])
        self.log_panel.configure(bg=theme["log_bg"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.log_header.configure(bg=theme["root_bg"])
        self.log_title_label.configure(bg=theme["root_bg"], fg=theme["accent"])
        self.description_body.configure(bg=theme["panel_bg"])
        self.preview_body.configure(bg=theme["panel_bg"])
        self.status_body.configure(bg=theme["panel_bg"])
        self.log_body.configure(bg=theme["log_bg"])
        self.description_text.configure(bg=theme["panel_bg"], fg=theme["panel_fg"], wraplength=max(200, self.root.winfo_width() - 420))
        self.preview_text.configure(bg=theme["panel_bg"], fg=theme["panel_fg"], insertbackground=theme["panel_fg"])
        self.status_text.configure(bg=theme["panel_bg"], fg=theme["panel_fg"], wraplength=max(200, self.root.winfo_width() - 420))
        self.log_text.configure(bg=theme["log_bg"], fg=theme["log_fg"], insertbackground=theme["log_fg"])
        self._configure_log_ansi_tags()
        self.input_panel.configure(bg=theme["panel_bg"], highlightbackground=theme["border"], highlightcolor=theme["border"])
        self.input_header.configure(bg=theme["root_bg"])
        self.input_title_label.configure(bg=theme["root_bg"], fg=theme["accent"])
        self.input_row.configure(bg=theme["panel_bg"])
        self.job_input_entry.configure(bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["entry_fg"], relief="solid", bd=1)
        for button in (
            self.content_toggle_button,
            self.description_toggle_button,
            self.preview_toggle_button,
            self.log_toggle_button,
            self.status_toggle_button,
        ):
            button.configure(
                relief="solid",
                bd=1,
                highlightthickness=0,
                bg=theme["root_bg"],
                fg=theme["accent"],
                activebackground=theme["root_bg"],
                activeforeground=theme["accent"],
            )
        for dest in list(self.bool_toggle_widgets):
            current_value = self.remember_state if dest == "remember-state" else bool(self.state_values.get(dest))
            self.refresh_boolean_toggle(dest, current_value)
        self.refresh_module_buttons()
        self.refresh_top_tabs()
        self.refresh_toolbar_buttons()
        self.refresh_action_buttons()
        self.refresh_panel_toggle_buttons()
        self.refresh_log_view()
        if rebuild:
            self.rebuild_content()
            self.update_command_preview()

    def configure_button_styles(self) -> None:
        theme = self.current_theme()

        self.style.configure(
            "PM.Tab.TButton",
            background=theme["tab_bg"],
            foreground=theme["tab_fg"],
            bordercolor=theme["border"],
            darkcolor=theme["tab_bg"],
            lightcolor=theme["tab_bg"],
            padding=(10, 6),
            relief="flat",
        )
        self.style.map(
            "PM.Tab.TButton",
            background=[("active", theme["tab_active_bg"]), ("pressed", theme["tab_active_bg"])],
            foreground=[("active", theme["tab_active_fg"]), ("pressed", theme["tab_active_fg"])],
        )
        self.style.configure(
            "PM.TabActive.TButton",
            background=theme["tab_active_bg"],
            foreground=theme["tab_active_fg"],
            bordercolor=theme["border"],
            darkcolor=theme["tab_active_bg"],
            lightcolor=theme["tab_active_bg"],
            padding=(10, 6),
            relief="flat",
        )
        self.style.map(
            "PM.TabActive.TButton",
            background=[("active", theme["tab_active_bg"]), ("pressed", theme["tab_active_bg"])],
            foreground=[("active", theme["tab_active_fg"]), ("pressed", theme["tab_active_fg"])],
        )

        self.style.configure(
            "PM.ToolbarSave.TButton",
            background="#cddff3",
            foreground="#284866",
            bordercolor="#9bb8d8",
            darkcolor="#cddff3",
            lightcolor="#cddff3",
            padding=(10, 6),
            relief="flat",
        )
        self.style.map(
            "PM.ToolbarSave.TButton",
            background=[("active", "#bdd4ec"), ("pressed", "#afcae6"), ("disabled", "#cad6e2")],
            foreground=[("disabled", "#788a9d")],
        )
        self.style.configure(
            "PM.ToolbarLoad.TButton",
            background="#efc8c8",
            foreground="#6c2727",
            bordercolor="#d7aaaa",
            darkcolor="#efc8c8",
            lightcolor="#efc8c8",
            padding=(10, 6),
            relief="flat",
        )
        self.style.map(
            "PM.ToolbarLoad.TButton",
            background=[("active", "#e7b6b6"), ("pressed", "#dda4a4"), ("disabled", "#dac7c7")],
            foreground=[("disabled", "#9d7a7a")],
        )

        self.style.configure(
            "PM.Neutral.TButton",
            background=theme["tab_bg"],
            foreground=theme["panel_fg"],
            bordercolor=theme["border"],
            darkcolor=theme["tab_bg"],
            lightcolor=theme["tab_bg"],
            padding=(8, 6),
            relief="flat",
        )
        self.style.map(
            "PM.Neutral.TButton",
            background=[("active", theme["tab_active_bg"]), ("pressed", theme["tab_active_bg"]), ("disabled", theme["tab_bg"])],
            foreground=[("active", theme["tab_active_fg"]), ("pressed", theme["tab_active_fg"]), ("disabled", theme["muted"])],
        )

        self.style.configure(
            "PM.RunEnabled.TButton",
            background="#c9ebcf",
            foreground="#22462a",
            bordercolor="#8cbe95",
            darkcolor="#c9ebcf",
            lightcolor="#c9ebcf",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.RunEnabled.TButton",
            background=[("active", "#b7e1be"), ("pressed", "#a6d7af")],
            foreground=[("active", "#1d3d24"), ("pressed", "#1d3d24")],
        )
        self.style.configure(
            "PM.RunDisabled.TButton",
            background="#3a4452",
            foreground="#98a4b3",
            bordercolor="#536071",
            darkcolor="#3a4452",
            lightcolor="#3a4452",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.RunDisabled.TButton",
            background=[("disabled", "#3a4452")],
            foreground=[("disabled", "#98a4b3")],
        )

        self.style.configure(
            "PM.StopEnabled.TButton",
            background="#efc8c8",
            foreground="#6c2727",
            bordercolor="#d7aaaa",
            darkcolor="#efc8c8",
            lightcolor="#efc8c8",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.StopEnabled.TButton",
            background=[("active", "#e7b6b6"), ("pressed", "#dda4a4")],
            foreground=[("active", "#612121"), ("pressed", "#612121")],
        )
        self.style.configure(
            "PM.StopDisabled.TButton",
            background="#3a4452",
            foreground="#98a4b3",
            bordercolor="#536071",
            darkcolor="#3a4452",
            lightcolor="#3a4452",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.StopDisabled.TButton",
            background=[("disabled", "#3a4452")],
            foreground=[("disabled", "#98a4b3")],
        )

        self.style.configure(
            "PM.ExitEnabled.TButton",
            background="#efb7b7",
            foreground="#6c2727",
            bordercolor="#d79f9f",
            darkcolor="#efb7b7",
            lightcolor="#efb7b7",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.ExitEnabled.TButton",
            background=[("active", "#e7a8a8"), ("pressed", "#dc9898")],
            foreground=[("active", "#612121"), ("pressed", "#612121")],
        )
        self.style.configure(
            "PM.ExitDisabled.TButton",
            background="#3a4452",
            foreground="#98a4b3",
            bordercolor="#536071",
            darkcolor="#3a4452",
            lightcolor="#3a4452",
            padding=(12, 8),
            relief="flat",
        )
        self.style.map(
            "PM.ExitDisabled.TButton",
            background=[("disabled", "#3a4452")],
            foreground=[("disabled", "#98a4b3")],
        )

        for key, (bg, fg) in MODULE_GROUP_CLASSES.items():
            normal_style = self._module_style_name(key, active=False)
            active_style = self._module_style_name(key, active=True)
            active_bg, active_fg = MODULE_ACTIVE_STYLE_OVERRIDES.get(key, (fg, "#ffffff"))
            self.style.configure(
                normal_style,
                background=bg,
                foreground=fg,
                bordercolor=theme["border"],
                darkcolor=bg,
                lightcolor=bg,
                padding=(12, 8),
                relief="flat",
            )
            self.style.map(
                normal_style,
                background=[("active", bg), ("pressed", bg)],
                foreground=[("active", fg), ("pressed", fg)],
            )
            self.style.configure(
                active_style,
                background=active_bg,
                foreground=active_fg,
                bordercolor=theme["border"],
                darkcolor=active_bg,
                lightcolor=active_bg,
                padding=(12, 8),
                relief="flat",
            )
            self.style.map(
                active_style,
                background=[("active", active_bg), ("pressed", active_bg)],
                foreground=[("active", active_fg), ("pressed", active_fg)],
            )

    def _module_style_name(self, module_key: str, *, active: bool) -> str:
        safe = module_key.replace("-", "_")
        return f"PM.Module.{safe}.{'Active' if active else 'Normal'}.TButton"

    def refresh_module_buttons(self) -> None:
        for key, button in self.module_buttons.items():
            button.configure(style=self._module_style_name(key, active=(key == self.active_module)))

    def refresh_top_tabs(self) -> None:
        for key, button in self.general_tab_buttons.items():
            button.configure(style=("PM.TabActive.TButton" if key == self.active_general_tab else "PM.Tab.TButton"))

    def refresh_toolbar_buttons(self) -> None:
        for button in (self.save_config_button, self.save_ui_button):
            button.configure(style="PM.ToolbarSave.TButton")
        self.load_config_button.configure(style="PM.ToolbarLoad.TButton")

    def _toggle_label(self, panel_key: str) -> str:
        return "▸" if self.panel_collapsed.get(panel_key, False) else "▾"

    def refresh_panel_toggle_buttons(self) -> None:
        mapping = {
            "content": self.content_toggle_button,
            "description": self.description_toggle_button,
            "preview": self.preview_toggle_button,
            "log": self.log_toggle_button,
            "status": self.status_toggle_button,
        }
        for panel_key, button in mapping.items():
            button.configure(text=self._toggle_label(panel_key))

    def apply_panel_states(self) -> None:
        if self.panel_collapsed.get("content", False):
            self.content_body.grid_remove()
            self.content_panel.grid_propagate(False)
            self.content_panel.configure(height=34)
        else:
            self.content_panel.grid_propagate(True)
            self.content_panel.configure(height=0)
            self.content_body.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 8))
            self.content_scroll.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        if self.panel_collapsed.get("description", False):
            self.description_body.grid_remove()
            self.description_panel.grid_propagate(False)
            self.description_panel.configure(height=34)
        else:
            self.description_panel.grid_propagate(True)
            self.description_panel.configure(height=0)
            self.description_body.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 8))

        if self.panel_collapsed.get("preview", False):
            self.preview_body.grid_remove()
            self.preview_panel.grid_propagate(False)
            self.preview_panel.configure(height=34)
        else:
            self.preview_panel.grid_propagate(True)
            self.preview_panel.configure(height=0)
            self.preview_body.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 8))

        if self.panel_collapsed.get("log", False):
            self.log_body.grid_remove()
            self.log_panel.grid_propagate(False)
            self.log_panel.configure(height=34)
        else:
            self.log_panel.grid_propagate(True)
            self.log_panel.configure(height=0)
            self.log_body.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 8))

        if self.panel_collapsed.get("status", False):
            self.status_body.grid_remove()
            self.status_panel.grid_propagate(False)
            self.status_panel.configure(height=34)
        else:
            self.status_panel.grid_propagate(True)
            self.status_panel.configure(height=0)
            self.status_body.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 8))

        self.refresh_panel_toggle_buttons()

    def apply_runtime_layout(self) -> None:
        running = self.can_stop_job()
        content_weight = 0 if self.panel_collapsed.get("content", False) else (2 if running else 4)
        bottom_weight = 5 if running else 3
        self.main.grid_rowconfigure(1, weight=content_weight)
        self.main.grid_rowconfigure(2, weight=bottom_weight)
        self.log_text.configure(height=(16 if running else 10))

    def sync_content_panel_for_run_state(self, running: bool) -> None:
        if running:
            if not self.panel_collapsed.get("content", False):
                self.panel_collapsed["content"] = True
                self.auto_collapsed_content_for_run = True
                self.apply_panel_states()
        elif self.auto_collapsed_content_for_run:
            self.panel_collapsed["content"] = False
            self.auto_collapsed_content_for_run = False
            self.apply_panel_states()
        self.apply_runtime_layout()

    def toggle_panel(self, panel_key: str) -> None:
        self.panel_collapsed[panel_key] = not self.panel_collapsed.get(panel_key, False)
        self.apply_panel_states()
        self.apply_runtime_layout()

    def can_run_job(self) -> bool:
        return not (self.running_process is not None and self.running_process.poll() is None)

    def can_stop_job(self) -> bool:
        return self.running_process is not None and self.running_process.poll() is None

    def can_exit_app(self) -> bool:
        return not self.can_stop_job()

    def refresh_action_buttons(self) -> None:
        can_run = self.can_run_job()
        can_stop = self.can_stop_job()
        can_exit = self.can_exit_app()
        can_send = bool(str(self.job_input_var.get() or "").strip())
        self.run_button.configure(
            state=("normal" if can_run else "disabled"),
            style=("PM.RunEnabled.TButton" if can_run else "PM.RunDisabled.TButton"),
        )
        self.stop_button.configure(
            state=("normal" if can_stop else "disabled"),
            style=("PM.StopEnabled.TButton" if can_stop else "PM.StopDisabled.TButton"),
        )
        self.exit_button.configure(
            state=("normal" if can_exit else "disabled"),
            style=("PM.ExitEnabled.TButton" if can_exit else "PM.ExitDisabled.TButton"),
        )
        self.job_input_send.configure(
            state=("normal" if can_send else "disabled"),
            style=("PM.RunEnabled.TButton" if can_send else "PM.RunDisabled.TButton"),
        )
        self.apply_runtime_layout()

    def current_content_panel_title(self) -> str:
        if self.active_general_tab == "feature":
            return INTERACTIVE_MODULE_TAB_NAMES.get(self.active_module, MODULE_TAB_NAMES.get(self.active_module, self.active_module))
        return GENERAL_TAB_NAMES.get(self.active_general_tab, self.active_general_tab)

    def current_content_panel_description(self) -> str:
        if self.active_general_tab == "feature":
            return "Feature-specific arguments for the selected module."
        if self.active_general_tab == "general":
            return "Global arguments shared across modules."
        if self.active_general_tab == "features_config":
            return "Edit the Config.ini used by CLI executions."
        return "Desktop UI preferences and local state persistence."

    def refresh_panel_titles(self) -> None:
        title = self.current_content_panel_title()
        desc = self.current_content_panel_description()
        self.content_title_label.configure(text=(f"{title}: {desc}" if desc else title))
        self.description_title_label.configure(text="Argument Description")
        self.preview_title_label.configure(text="Command Preview")
        self.log_title_label.configure(text="Execution Log")
        self.status_title_label.configure(text="Status")
        self.refresh_panel_toggle_buttons()

    def select_module(self, module_key: str) -> None:
        self.active_module = module_key
        self.active_general_tab = "feature"
        self.active_config_section = self.preferred_config_section()
        self.ensure_config_account_selection()
        self.refresh_module_buttons()
        self.refresh_top_tabs()
        self.rebuild_content()
        self.update_command_preview()

    def select_general_tab(self, tab_key: str) -> None:
        self.active_general_tab = tab_key
        if tab_key == "features_config":
            self.reload_config_model()
        self.refresh_top_tabs()
        self.rebuild_content()
        self.update_command_preview()

    def rebuild_content(self) -> None:
        theme = self.current_theme()
        self.refresh_panel_titles()
        self.content_scroll.clear()
        self.field_widget_map = {}
        self.field_help_map = {}
        self.config_widget_map = {}
        self.bool_toggle_widgets = {}
        body = self.content_scroll.body
        body.configure(bg=theme["panel_bg"])
        self.build_content_widgets(body)
        if not body.winfo_children():
            self._empty_label(body, "No content available.").pack(anchor="w", padx=8, pady=8)
        self.content_scroll._refresh_scrollbar()
        self.apply_panel_states()
        self.apply_runtime_layout()

    def build_content_widgets(self, parent: Any) -> List[Any]:
        if self.active_general_tab == "feature":
            return self.build_feature_widgets(parent)
        if self.active_general_tab == "general":
            return self.build_general_arguments_widgets(parent)
        if self.active_general_tab == "features_config":
            return self.build_config_widgets(parent)
        return self.build_app_settings_widgets(parent)

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
            30: theme["muted"],
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
        try:
            self.preview_scroll.set(first, last)
            if float(first) <= 0.0 and float(last) >= 1.0:
                self.preview_scroll.grid_remove()
            else:
                self.preview_scroll.grid()
        except Exception:
            pass

    def update_field_description(self, text: str) -> None:
        self.description_var.set(str(text or "").strip() or "Move focus to a field to see its description here.")

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
        for widget in [self.description_text, self.preview_text, self.status_text, self.log_text, self.job_input_entry]:
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

    def _label(self, parent: Any, text: str, *, accent: bool = False, config_wide: bool = False) -> Any:
        theme = self.current_theme()
        fg = theme["accent"] if accent else theme["text"]
        width = 38 if config_wide else 28
        label = self.tk.Label(parent, text=text, width=width, anchor="w", justify="left", bg=theme["panel_bg"], fg=fg)
        return label

    def _clear_combobox_selection(self, combo: Any) -> None:
        try:
            combo.selection_clear()
        except Exception:
            pass
        try:
            combo.icursor("end")
        except Exception:
            pass

    def _section_label(self, parent: Any, text: str, *, accent: bool = False) -> Any:
        theme = self.current_theme()
        label = self.tk.Label(parent, text=text, anchor="w", justify="left", bg=theme["panel_bg"], fg=(theme["accent"] if accent else theme["text"]), font=("TkDefaultFont", 10, "bold"))
        label.pack(fill="x", padx=6, pady=(10 if accent else 6, 2))
        return label

    def _entry(self, parent: Any, text_var: Any) -> Any:
        theme = self.current_theme()
        widget = self.tk.Entry(parent, textvariable=text_var, bg=theme["entry_bg"], fg=theme["entry_fg"], insertbackground=theme["entry_fg"], relief="solid", bd=1)
        self._bind_context_menu(widget)
        return widget

    def _empty_label(self, parent: Any, text: str) -> Any:
        theme = self.current_theme()
        return self.tk.Label(parent, text=text, bg=theme["panel_bg"], fg=theme["muted"], anchor="w", justify="left")

    def build_feature_widgets(self, parent: Any) -> List[Any]:
        widgets: List[Any] = []
        if self.active_module == "upload_folder":
            self._empty_label(parent, "Upload to Server is only available in the Web Interface.").pack(anchor="w", padx=8, pady=8)
            return widgets
        if self.active_module == "automatic_migration":
            self.build_module_only_fields(parent, "automatic_migration", self.schema["tabs"]["automatic_migration"])
            return widgets
        if self.active_module in {"google_takeout", "icloud_takeout"}:
            self.build_module_only_fields(parent, self.active_module, self.schema["tabs"][self.active_module])
            return widgets
        if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
            self.build_cloud_widgets(parent)
            return widgets
        if self.active_module == "standalone_features":
            self.build_standalone_widgets(parent)
        return widgets

    def build_general_arguments_widgets(self, parent: Any) -> List[Any]:
        theme = self.current_theme()
        container = self.tk.Frame(parent, bg=theme["panel_bg"])
        container.pack(fill="both", expand=True, padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        fields_by_dest = {field["dest"]: field for field in self.schema["general_tabs"]["general"]}
        used = set()
        group_blocks: List[Any] = []
        for group in GENERAL_GROUPS:
            group_fields = [fields_by_dest[dest] for dest in group["dests"] if dest in fields_by_dest]
            if not group_fields:
                continue
            card = self.tk.Frame(container, bg=theme["panel_bg"])
            self._section_label(card, group["title"], accent=True)
            for field in group_fields:
                used.add(field["dest"])
                self.build_field_widgets(card, field, context="general")
            group_blocks.append(card)
        remaining = [field for field in self.schema["general_tabs"]["general"] if field["dest"] not in used]
        if remaining:
            card = self.tk.Frame(container, bg=theme["panel_bg"])
            self._section_label(card, "Other", accent=True)
            for field in remaining:
                self.build_field_widgets(card, field, context="general")
            group_blocks.append(card)
        for index, card in enumerate(group_blocks):
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 6, 6 if index % 2 == 0 else 0), pady=2)
        return []

    def build_module_only_fields(self, parent: Any, tab_key: str, fields: List[Dict[str, Any]]) -> None:
        if tab_key == "automatic_migration":
            self._section_label(parent, "Module Fields", accent=True)
            for field in fields:
                if str(field.get("dest") or "") in {"source", "target"}:
                    self.build_migration_endpoint_row(parent, str(field.get("dest") or ""), str(field.get("help") or "").strip())
                else:
                    self.build_field_widgets(parent, field, context=tab_key)
            return
        if tab_key in {"google_takeout", "icloud_takeout"}:
            regular_fields = [field for field in fields if str(field.get("kind") or "") not in {"flag", "bool"}]
            toggle_fields = [field for field in fields if str(field.get("kind") or "") in {"flag", "bool"}]
            if regular_fields:
                self._section_label(parent, "Module Fields", accent=True)
                for field in regular_fields:
                    self.build_field_widgets(parent, field, context=tab_key)
            if toggle_fields:
                self._section_label(parent, "Flags", accent=True)
                self.build_flags_grid(parent, toggle_fields, tab_key)
            return
        self._section_label(parent, "Module Fields", accent=True)
        for field in fields:
            self.build_field_widgets(parent, field, context=tab_key)

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
        state = self.migration_endpoint_state(dest)
        block = self.tk.Frame(parent, bg=self.current_theme()["panel_bg"])
        block.pack(fill="x", padx=6, pady=2)

        selector_row = self.tk.Frame(block, bg=self.current_theme()["panel_bg"])
        selector_row.pack(fill="x")

        self._label(selector_row, dest.title()).pack(side="left")

        kind_map = {
            "Synology Photos": "synology",
            "Immich Photos": "immich",
            "NextCloud Photos": "nextcloud",
            "Google Photos": "google",
            "Select Folder": "folder",
        }
        reverse_kind_map = {value: key for key, value in kind_map.items()}
        type_var = self.tk.StringVar(value=reverse_kind_map.get(state.get("kind") or "", "Select Folder"))
        type_combo = self.ttk.Combobox(selector_row, textvariable=type_var, values=list(kind_map.keys()), state="readonly", style="PM.TCombobox")
        type_combo.pack(fill="x", expand=True, padx=(0, 8))
        self._bind_help(type_combo, help_text)
        self._bind_context_menu(type_combo)

        secondary = self.tk.Frame(block, bg=self.current_theme()["panel_bg"])
        secondary.pack(fill="x", pady=(4, 0))

        def sync_endpoint_state() -> None:
            self.migration_endpoints_state[dest] = state
            self.state_values[dest] = compose_migration_endpoint(state)
            self.update_command_preview()

        def render_secondary() -> None:
            for child in list(secondary.winfo_children()):
                child.destroy()
            if state.get("kind") == "folder":
                self._label(secondary, "Folder Path").pack(side="left")
                path_var = self.tk.StringVar(value=str(state.get("path") or ""))
                self.field_widget_map[dest] = path_var
                entry = self._entry(secondary, path_var)
                entry.pack(side="left", fill="x", expand=True)
                self._bind_help(entry, help_text)
                btn = self.ttk.Button(secondary, text="...", width=4, command=lambda d=dest: self.browse_path(d), style="PM.Neutral.TButton")
                btn.pack(side="left", padx=(6, 8))
                self._bind_help(btn, help_text or dest.title())

                def on_path_change(*_args: Any) -> None:
                    state["path"] = path_var.get()
                    sync_endpoint_state()

                path_var.trace_add("write", on_path_change)
            else:
                self.field_widget_map.pop(dest, None)
                self._label(secondary, "Account").pack(side="left")
                account_var = self.tk.StringVar(value=str(state.get("account") or "1"))
                account_combo = self.ttk.Combobox(secondary, textvariable=account_var, values=["1", "2", "3"], state="readonly", style="PM.TCombobox", width=8)
                account_combo.pack(side="left", fill="x", padx=(0, 8))
                self._bind_help(account_combo, help_text)
                self._bind_context_menu(account_combo)

                def on_account_change(_event: Any = None) -> None:
                    state["account"] = str(account_var.get() or "1")
                    self._clear_combobox_selection(account_combo)
                    sync_endpoint_state()

                account_combo.bind("<<ComboboxSelected>>", on_account_change)

        def on_kind_change(_event: Any = None) -> None:
            state["kind"] = kind_map.get(type_var.get(), self.migration_default_kind(dest))
            self._clear_combobox_selection(type_combo)
            render_secondary()
            sync_endpoint_state()

        type_combo.bind("<<ComboboxSelected>>", on_kind_change)
        render_secondary()
        sync_endpoint_state()

    def _selected_action_for_active_module(self) -> str | None:
        if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
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
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def _launch_dashboard_job_in_external_terminal(self, command: List[str]) -> None:
        env = build_ui_subprocess_env(ui_mode="gui", embedded_ui=False)
        launcher = build_external_terminal_command(command, self.project_root, env)
        if not launcher:
            raise RuntimeError("No supported external terminal launcher was found on this system.")
        subprocess.Popen(launcher, cwd=str(self.project_root), env=env)
        self.root.after(150, self._restore_gui_focus)

    def build_flags_grid(self, parent: Any, fields: List[Dict[str, Any]], context: str) -> None:
        theme = self.current_theme()
        frame = self.tk.Frame(parent, bg=theme["panel_bg"])
        frame.pack(fill="x", padx=4, pady=2)
        columns = 3 if len(fields) >= 9 else 2
        for col in range(columns):
            frame.grid_columnconfigure(col, weight=1)
        for index, field in enumerate(fields):
            cell = self.tk.Frame(frame, bg=theme["panel_bg"])
            cell.grid(row=index // columns, column=index % columns, sticky="ew", padx=4, pady=1)
            self.build_field_widgets(cell, field, context=context)

    def build_cloud_widgets(self, parent: Any) -> None:
        self._section_label(parent, "Action", accent=True)
        actions = list(self.schema["tabs"][self.active_module])
        available = CLOUD_ACTIONS_AVAILABLE_BY_TAB.get(self.active_module)
        if available is not None:
            actions = [field for field in actions if field["dest"] in available]
        if not actions:
            self._empty_label(parent, "No cloud actions available for this module.").pack(anchor="w", padx=8, pady=8)
            return
        selected_dest = str(self.cloud_action_dest.get(self.active_module) or "")
        if selected_dest not in {field["dest"] for field in actions}:
            selected_dest = actions[0]["dest"]
            self.cloud_action_dest[self.active_module] = selected_dest
        self.build_select_row(parent, "Cloud Action", "cloud-action-select", [(ui_option_name(field), field["dest"]) for field in actions], selected_dest, help_text="Select the cloud action to configure for the current service.")
        selected = next((field for field in actions if field["dest"] == selected_dest), None)
        if selected and str(selected.get("help") or "").strip():
            self._empty_label(parent, str(selected.get("help") or "").strip()).pack(anchor="w", padx=8, pady=(0, 4))
        specs = build_argument_specs(self.schema, self.active_module, selected, True)
        account_field = get_field_by_dest(self.schema, "account-id")
        if account_field:
            normalized = normalize_field_for_context(account_field, self.active_module)
            specs = [spec for spec in specs if spec["field"]["dest"] != "account-id"]
            insert_at = next((idx for idx, spec in enumerate(specs) if not spec["required"]), len(specs))
            specs.insert(insert_at, {"field": normalized, "required": False})
        self._section_label(parent, "Action Arguments", accent=True)
        if selected and selected.get("dest") == "rename-albums":
            parsed = parse_rename_albums_value(self.state_values.get("rename-albums"))
            if not str(self.state_values.get("rename-pattern") or "").strip():
                self.state_values["rename-pattern"] = parsed.get("pattern") or ""
            if not str(self.state_values.get("replacement-pattern") or "").strip():
                self.state_values["replacement-pattern"] = parsed.get("replacement") or ""
            for spec in specs:
                if spec["field"]["dest"] not in {"rename-albums"}:
                    self.build_field_widgets(parent, spec["field"], required=spec["required"], context=self.active_module)
            self.build_pseudo_text_field(parent, "Rename Pattern", "rename-pattern", self.state_values.get("rename-pattern", ""), True, "Album name pattern (text or regex).")
            self.build_pseudo_text_field(parent, "Replacement Pattern", "replacement-pattern", self.state_values.get("replacement-pattern", ""), True, "Replacement pattern used during album rename.")
        else:
            for spec in specs:
                self.build_field_widgets(parent, spec["field"], required=spec["required"], context=self.active_module)
        otp_field = get_field_by_dest(self.schema, "one-time-password")
        if otp_field and self.active_module in {"synology_photos", "immich_photos", "nextcloud_photos", "google_photos"}:
            self._section_label(parent, "Optional", accent=True)
            self.build_field_widgets(parent, otp_field, required=False, context=self.active_module)

    def build_standalone_widgets(self, parent: Any) -> None:
        actions = list(self.schema["tabs"]["standalone_features"])
        if not actions:
            self._empty_label(parent, "No standalone actions available.").pack(anchor="w", padx=8, pady=8)
            return
        selected_dest = self.standalone_action_dest if self.standalone_action_dest in {field["dest"] for field in actions} else actions[0]["dest"]
        self.standalone_action_dest = selected_dest
        self._section_label(parent, "Action", accent=True)
        self.build_select_row(parent, "Standalone Action", "standalone-action-select", [(ui_option_name(field), field["dest"]) for field in actions], selected_dest, help_text="Select the standalone feature to configure and run.")
        selected = next((field for field in actions if field["dest"] == selected_dest), None)
        if selected and str(selected.get("help") or "").strip():
            self._empty_label(parent, str(selected.get("help") or "").strip()).pack(anchor="w", padx=8, pady=(0, 4))
        self._section_label(parent, "Action Arguments", accent=True)
        if selected and selected.get("dest") == "find-duplicates":
            parsed = parse_find_duplicates_value(self.state_values.get("find-duplicates"))
            self.state_values["find-duplicates-action"] = parsed.get("action") or "list"
            if not self.state_values.get("find-duplicates-folders"):
                self.state_values["find-duplicates-folders"] = parsed.get("folders") or []
            self.build_select_row(parent, "Duplicates Action", "find-duplicates-action-select", [("list", "list"), ("move", "move"), ("delete", "delete")], str(self.state_values.get("find-duplicates-action") or "list"), help_text="Choose what the duplicates scan should do with detected duplicates: list, move, or delete.")
            self.build_pseudo_list_field(parent, "Folder(s)", "find-duplicates-folders", self.state_values.get("find-duplicates-folders", []), True, "One or more folders separated by comma or newline.")
        else:
            specs = build_argument_specs(self.schema, "standalone_features", selected, True)
            for spec in specs:
                self.build_field_widgets(parent, spec["field"], required=spec["required"], context="standalone_features")

    def build_config_widgets(self, parent: Any) -> List[Any]:
        self.config_widget_map = {}
        section_options = [(section["name"], section["name"]) for section in self.config_sections]
        self.build_select_row(parent, "Config Section", "config-section-select", section_options, self.active_config_section, help_text="Select which Config.ini section you want to edit.", accent_label=True)
        current_section = next((section for section in self.config_sections if section["name"] == self.active_config_section), None)
        if not current_section:
            self._empty_label(parent, "No configuration section selected.").pack(anchor="w", padx=8, pady=8)
            return []
        if str(current_section.get("description") or "").strip():
            self._empty_label(parent, str(current_section.get("description") or "").strip()).pack(anchor="w", padx=8, pady=(0, 4))
        fields = list(current_section.get("fields") or [])
        global_fields = [field for field in fields if not str(field.get("account_id") or "")]
        account_fields = [field for field in fields if str(field.get("account_id") or "")]
        for field in global_fields:
            self.build_config_field_widgets(parent, current_section["name"], field)
        selector = current_section.get("account_selector") or {}
        if selector.get("enabled"):
            section_name = current_section["name"]
            account_value = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
            self.build_select_row(parent, "Configure Account", "config-account-select", [(f"Account {acc}", acc) for acc in selector.get("accounts") or []], account_value, help_text="Select which account within this service section you want to configure.", accent_label=True)
            selected_account = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
            visible_account_fields = [field for field in account_fields if str(field.get("account_id") or "") == selected_account]
            for field in visible_account_fields:
                self.build_config_field_widgets(parent, section_name, field)
        else:
            for field in account_fields:
                self.build_config_field_widgets(parent, current_section["name"], field)
        return []

    def build_app_settings_widgets(self, parent: Any) -> List[Any]:
        self.build_select_row(parent, "Theme", "theme-select", THEME_CHOICES, self.selected_theme, help_text="Select the visual theme used by the desktop GUI.")
        self.build_boolean_toggle_row(parent, "Remember UI state", "remember-state", self.remember_state, help_text="Persist the current desktop UI state, selected tabs, and entered values between sessions.")
        self._empty_label(parent, f"State file: {TK_STATE_PATH}").pack(anchor="w", padx=8, pady=(6, 0))
        self._empty_label(parent, f"Config file in use: {self.current_config_path()}").pack(anchor="w", padx=8, pady=(2, 0))
        self._empty_label(parent, "Use the Run button to execute the currently selected module.").pack(anchor="w", padx=8, pady=(2, 0))
        return []

    def build_select_row(self, parent: Any, label: str, widget_id: str, options: List[tuple[str, Any]], value: Any, *, help_text: str = "", accent_label: bool = False, config_wide: bool = False) -> None:
        row = self.tk.Frame(parent, bg=self.current_theme()["panel_bg"])
        row.pack(fill="x", padx=6, pady=2)
        self._label(row, label, accent=accent_label, config_wide=config_wide).pack(side="left")
        values = [str(label_text) for label_text, _ in options]
        mapping = {str(label_text): str(option_value) for label_text, option_value in options}
        reverse = {str(option_value): str(label_text) for label_text, option_value in options}
        current_value = str(value or "")
        selected_label = reverse.get(current_value, values[0] if values else "")
        var = self.tk.StringVar(value=selected_label)
        combo = self.ttk.Combobox(row, textvariable=var, values=values, state="readonly", style="PM.TCombobox")
        combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._bind_help(combo, help_text)
        self._bind_context_menu(combo)

        def on_change(_event: Any = None) -> None:
            selected = mapping.get(var.get(), "")
            self._clear_combobox_selection(combo)
            if widget_id == "cloud-action-select":
                if selected == str(self.cloud_action_dest.get(self.active_module) or ""):
                    return
                self.cloud_action_dest[self.active_module] = selected
                self.rebuild_content()
                self.update_command_preview()
                return
            if widget_id == "standalone-action-select":
                if selected == self.standalone_action_dest:
                    return
                self.standalone_action_dest = selected
                self.rebuild_content()
                self.update_command_preview()
                return
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
                self.state_values[dest] = selected
                self.update_command_preview()
                return
            if widget_id.startswith("config-"):
                mapped = self.config_widget_map.get(widget_id)
                if mapped:
                    section_name, key = mapped
                    self.config_values.setdefault(section_name, {})[key] = selected

        combo.bind("<<ComboboxSelected>>", on_change)

    def build_boolean_toggle_row(self, parent: Any, label: str, dest: str, value: bool, help_text: str = "") -> None:
        row = self.tk.Frame(parent, bg=self.current_theme()["panel_bg"])
        row.pack(fill="x", padx=6, pady=2)
        self._label(row, label).pack(side="left")
        holder = self.tk.Frame(row, bg=self.current_theme()["panel_bg"])
        holder.pack(side="left")
        switch = self.tk.Canvas(holder, width=40, height=20, bd=0, highlightthickness=0, cursor="hand2")
        switch.pack(side="left", padx=(0, 6))
        switch.bind("<Button-1>", lambda _e, d=dest: self.set_boolean_toggle(d, not (self.remember_state if d == "remember-state" else bool(self.state_values.get(d)))))
        self._bind_help(switch, help_text)
        self.bool_toggle_widgets[dest] = switch
        self.refresh_boolean_toggle(dest, value)

    def set_boolean_toggle(self, dest: str, value: bool) -> None:
        if dest == "remember-state":
            self.remember_state = value
        else:
            self.state_values[dest] = value
        self.refresh_boolean_toggle(dest, value)
        self.update_command_preview()

    def refresh_boolean_toggle(self, dest: str, value: bool) -> None:
        theme = self.current_theme()
        switch = self.bool_toggle_widgets.get(dest)
        if not switch:
            return
        track_fill = "#35c759" if value else "#6b7481"
        thumb_fill = "#f4f7fb"
        switch.configure(bg=theme["panel_bg"])
        switch.delete("all")
        switch.create_oval(1, 3, 15, 17, fill=track_fill, outline=track_fill)
        switch.create_rectangle(8, 3, 32, 17, fill=track_fill, outline=track_fill)
        switch.create_oval(25, 3, 39, 17, fill=track_fill, outline=track_fill)
        thumb_x = 23 if value else 3
        switch.create_oval(thumb_x, 3, thumb_x + 14, 17, fill=thumb_fill, outline=thumb_fill)

    def build_pseudo_text_field(self, parent: Any, label: str, dest: str, value: Any, required: bool, help_text: str) -> None:
        self.build_input_block(parent, label, dest, str(value or ""), required, help_text, path_hint="")

    def build_pseudo_list_field(self, parent: Any, label: str, dest: str, value: Any, required: bool, help_text: str) -> None:
        joined = ", ".join(parse_folder_list_value(value))
        self.build_input_block(parent, label, dest, joined, required, help_text, path_hint="path")

    def build_input_block(self, parent: Any, label: str, dest: str, value: str, required: bool, help_text: str, *, path_hint: str = "", password: bool = False) -> None:
        row = self.tk.Frame(parent, bg=self.current_theme()["panel_bg"])
        row.pack(fill="x", padx=6, pady=2)
        self._label(row, f"{label}{' *' if required else ''}").pack(side="left")
        var = self.tk.StringVar(value=value)
        self.field_widget_map[dest] = var
        if path_hint == "path":
            control = self.tk.Frame(row, bg=self.current_theme()["panel_bg"])
            control.pack(side="left", fill="x", expand=True)
            entry = self._entry(control, var)
            entry.pack(side="left", fill="x", expand=True)
            btn = self.ttk.Button(control, text="...", width=4, command=lambda d=dest: self.browse_path(d), style="PM.Neutral.TButton")
            btn.pack(side="left", padx=(6, 8))
            self._bind_help(btn, help_text or label)
        else:
            entry = self._entry(row, var)
            entry.configure(show="*" if password else "")
            entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._bind_help(entry, help_text)

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
            self.update_command_preview()

        var.trace_add("write", on_change)

    def build_field_widgets(self, parent: Any, field: Dict[str, Any], required: bool = False, context: str = "") -> None:
        field = normalize_field_for_context(field, context) or field
        dest = str(field.get("dest") or "")
        label = ui_option_name(field)
        help_text = str(field.get("help") or "").strip()
        kind = str(field.get("kind") or "text")
        value = self.state_values.get(dest)
        path_hint = str(field.get("path_hint") or "")
        if dest == "process-duplicates":
            path_hint = "path"
        if kind in {"flag", "bool"}:
            self.build_boolean_toggle_row(parent, f"{label}{' *' if required else ''}", dest, bool(value), help_text=help_text)
            return
        if kind == "select":
            options = [(str(choice), str(choice)) for choice in (field.get("choices") or [])]
            self.build_select_row(parent, f"{label}{' *' if required else ''}", f"field-{dest}", options, value, help_text=help_text)
            return
        if kind == "list":
            joined = ", ".join(to_list(value))
            self.build_input_block(parent, label, dest, joined, required, help_text, path_hint=path_hint)
            return
        self.build_input_block(parent, label, dest, "" if value is None else str(value), required, help_text, path_hint=path_hint, password=bool(field.get("sensitive")))

    def build_config_field_widgets(self, parent: Any, section_name: str, field: Dict[str, Any]) -> None:
        row = self.tk.Frame(parent, bg=self.current_theme()["panel_bg"])
        row.pack(fill="x", padx=6, pady=2)
        key = str(field.get("key") or "")
        help_text = str(field.get("help") or "").strip()
        value = str(self.config_values.get(section_name, {}).get(key, ""))
        self._label(row, key, config_wide=True).pack(side="left")
        widget_id = f"config-{len(self.config_widget_map)}"
        self.config_widget_map[widget_id] = (section_name, key)
        choices = field.get("choices") or []
        if choices:
            values = [str(choice) for choice in choices]
            var = self.tk.StringVar(value=value if value in values else (values[0] if values else ""))
            combo = self.ttk.Combobox(row, textvariable=var, values=values, state="readonly", style="PM.TCombobox")
            combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self._bind_help(combo, help_text)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _e, w=combo, v=var, s=section_name, k=key: (self._clear_combobox_selection(w), self.config_values.setdefault(s, {}).__setitem__(k, v.get())),
            )
            return
        var = self.tk.StringVar(value=value)
        entry = self._entry(row, var)
        entry.configure(show="*" if bool(field.get("sensitive")) else "")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._bind_help(entry, help_text)
        var.trace_add("write", lambda *_args, v=var, s=section_name, k=key: self.config_values.setdefault(s, {}).__setitem__(k, v.get()))

    def browse_path(self, dest: str) -> None:
        from tkinter import filedialog

        current = self.state_values.get(dest)
        current_path = ""
        if isinstance(current, list):
            current_path = current[0] if current else ""
        else:
            current_path = str(current or "")
        selected = filedialog.askdirectory(initialdir=str(Path(current_path).expanduser()) if current_path else str(self.project_root))
        if not selected:
            return
        if dest == "find-duplicates-folders":
            self.state_values[dest] = [selected]
        else:
            self.state_values[dest] = selected
        var = self.field_widget_map.get(dest)
        if var is not None:
            if dest == "find-duplicates-folders":
                var.set(selected)
            else:
                var.set(selected)
        self.update_command_preview()

    def update_command_preview(self) -> None:
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

    def consume_log_output(self, text: str) -> None:
        update = self.log_buffer.append_text(text)
        if update.replaced_progress or update.partial_changed or update.appended_lines:
            self.refresh_log_view()

    def poll_process_queue(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(item, tuple) and item and item[0] == "finished":
                self.running_process = None
                self.update_status(f"Job finished with exit code {item[1]}")
                self.sync_content_panel_for_run_state(False)
                self.refresh_action_buttons()
            elif isinstance(item, tuple) and item and item[0] == "output":
                self.consume_log_output(str(item[1]))
            else:
                self.append_log(str(item))
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

    def action_run_job(self) -> None:
        if self.active_module == "upload_folder":
            self.update_status("Upload to Server is only available in the Web Interface.")
            return
        if self.running_process is not None and self.running_process.poll() is None:
            self.update_status("A job is already running.")
            return
        if self._should_run_dashboard_in_external_terminal():
            from tkinter import messagebox

            confirmed = messagebox.askyesno(
                "Automatic Migration Live Dashboard",
                "Live Dashboard is enabled for Automatic Migration.\n\n"
                "If you continue, PhotoMigrator will open this run in an external terminal window so the full-screen dashboard can render there.\n\n"
                "If you choose No, the same migration will run only for this execution without Live Dashboard and the output will stay embedded in the GUI Execution Log.",
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
                self.refresh_action_buttons()
                return
            command = self._build_current_command(dashboard_enabled=False)
            self.running_command = command
            self.log_buffer.clear()
            self._set_readonly_text(self.log_text, "")
            self.append_log(f"> {command_to_string(command)}")
            self.append_log("[internal] Live Dashboard disabled for this run by user confirmation.")
        else:
            command = self._build_current_command()
        self.running_command = command
        if not self.log_buffer.entries:
            self.log_buffer.clear()
            self._set_readonly_text(self.log_text, "")
            self.append_log(f"> {command_to_string(command)}")
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.project_root),
                env=build_ui_subprocess_env(ui_mode="gui"),
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
        self.sync_content_panel_for_run_state(True)
        self.refresh_action_buttons()
        threading.Thread(target=self._job_output_worker, args=(process,), daemon=True).start()

    def action_stop_job(self) -> None:
        if self.running_process is None or self.running_process.poll() is not None:
            self.update_status("No running job to stop.")
            return
        try:
            self.running_process.terminate()
            self.update_status("Stop signal sent to job.")
            self.refresh_action_buttons()
        except Exception as exc:
            self.update_status(f"Unable to stop job: {exc}")

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

    def action_send_job_input(self) -> None:
        if self.running_process is None or self.running_process.stdin is None or self.running_process.poll() is not None:
            self.update_status("No running job is accepting input.")
            return
        text = str(self.job_input_var.get() or "").rstrip("\r\n")
        if not text:
            self.update_status("Input is empty.")
            return
        try:
            self.running_process.stdin.write(text + "\n")
            self.running_process.stdin.flush()
            self.append_log(f">>> {text}")
            self.job_input_var.set("")
            self.update_status("Input sent to job.")
        except Exception as exc:
            self.update_status(f"Unable to send input: {exc}")

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
        payload = {
            "values": self.state_values,
            "ui_state": {
                "active_module": self.active_module,
                "active_general_tab": self.active_general_tab,
                "cloud_action_dest": self.cloud_action_dest,
                "standalone_action_dest": self.standalone_action_dest,
                "migration_endpoints": self.migration_endpoints_state,
                "active_config_section": self.active_config_section,
                "active_config_account": self.active_config_account,
                "theme": self.selected_theme,
                "remember_state": self.remember_state,
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
