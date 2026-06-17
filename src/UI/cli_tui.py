from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List

from UI.shared import (
    CLOUD_ACTIONS_AVAILABLE_BY_TAB,
    CONFIG_EDITOR_SECTIONS_ORDER,
    FEATURE_LABELS,
    GENERAL_GROUPS,
    GENERAL_TAB_NAMES,
    MODULE_TAB_NAMES,
    TIMEZONE_CHOICES,
    build_argument_specs,
    build_full_command,
    build_parser_schema,
    command_to_string,
    compose_migration_endpoint,
    config_section_account_selector,
    default_state_values,
    get_field_by_dest,
    load_config_editor_model,
    load_json_file,
    normalize_field_for_context,
    parse_find_duplicates_value,
    parse_migration_endpoint,
    parse_folder_list_value,
    parse_rename_albums_value,
    prepare_values_for_command,
    save_config_editor_values,
    save_json_file,
    to_list,
    ui_option_name,
)

TEXTUAL_IMPORT_ERROR: Exception | None = None
TEXTUAL_AVAILABLE = False

try:
    from textual import events
    from textual.app import App, ComposeResult
    from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import Button, Checkbox, DirectoryTree, Footer, Header, Input, Label, RichLog, Select, Static

    TEXTUAL_AVAILABLE = True
except Exception as exc:  # pragma: no cover - dependency may be optional in test envs
    TEXTUAL_IMPORT_ERROR = exc


TUI_STATE_PATH = Path(os.environ.get("PHOTOMIGRATOR_TUI_STATE_PATH", str(Path.home() / ".photomigrator_tui_state.json")))
THEME_CHOICES = [("Ocean", "ocean"), ("Emerald", "emerald"), ("Sunset", "sunset"), ("Dark", "dark")]
MODULE_GROUP_CLASSES = {
    "automatic_migration": "module-tab--migration",
    "google_takeout": "module-tab--takeout",
    "icloud_takeout": "module-tab--takeout",
    "google_photos": "module-tab--cloud",
    "synology_photos": "module-tab--cloud",
    "immich_photos": "module-tab--cloud",
    "nextcloud_photos": "module-tab--cloud",
    "standalone_features": "module-tab--standalone",
    "upload_folder": "module-tab--upload",
}
MODULE_TO_CONFIG_SECTION = {
    "google_photos": "Google Photos",
    "synology_photos": "Synology Photos",
    "immich_photos": "Immich Photos",
    "nextcloud_photos": "NextCloud Photos",
}
INTERACTIVE_MODULE_TAB_NAMES = {key: label for key, label in MODULE_TAB_NAMES.items() if key != "upload_folder"}


def textual_runtime_available() -> tuple[bool, str | None]:
    if TEXTUAL_AVAILABLE:
        return True, None
    return False, str(TEXTUAL_IMPORT_ERROR or "Textual is not installed")


if TEXTUAL_AVAILABLE:
    class PathPickerScreen(ModalScreen[Dict[str, str] | None]):
        BINDINGS = [("escape", "cancel", "Cancel"), ("enter", "confirm", "Select")]

        def __init__(self, dest: str, title: str, start_path: str = "", home_path: Path | None = None):
            super().__init__()
            self.home_path = (home_path or Path.cwd()).expanduser()
            if not self.home_path.exists():
                self.home_path = Path.cwd()
            raw = str(start_path or "").strip()
            if raw:
                candidate = Path(raw).expanduser()
                self.initial_path = candidate if candidate.exists() else candidate.parent
            else:
                self.initial_path = self.home_path
            if not self.initial_path.exists():
                self.initial_path = self.home_path
            self.dest = dest
            self.title = title

        def compose(self) -> ComposeResult:
            root_value = str(self.initial_path.resolve())
            yield Vertical(
                Static(self.title, classes="modal-title"),
                Static("Select a file or folder and press Enter.", classes="modal-subtitle"),
                Input(value=root_value, id="picker-path-input"),
                Horizontal(
                    Button("↑ Up", id="picker-up"),
                    Button("⌂ Home", id="picker-home"),
                    id="picker-nav-actions",
                ),
                DirectoryTree(root_value, id="picker-tree"),
                Horizontal(
                    Button("Cancel", id="picker-cancel"),
                    Button("Select", id="picker-select", variant="primary"),
                    id="picker-actions",
                ),
                id="picker-dialog",
            )

        def action_cancel(self) -> None:
            self.dismiss(None)

        def action_confirm(self) -> None:
            selected = self._selected_path()
            self.dismiss({"dest": self.dest, "path": selected})

        def _selected_path(self) -> str:
            try:
                tree = self.query_one("#picker-tree", DirectoryTree)
                selected = getattr(tree, "cursor_node", None)
                if selected is not None and getattr(selected, "data", None) is not None:
                    data = selected.data.path if hasattr(selected.data, "path") else selected.data
                    if data:
                        return str(Path(data).resolve())
            except Exception:
                pass
            return str(self.query_one("#picker-path-input", Input).value or "")

        def _set_tree_root(self, path: Path) -> None:
            candidate = path.expanduser()
            if not candidate.exists():
                return
            root = candidate if candidate.is_dir() else candidate.parent
            if not root.exists():
                return
            resolved = root.resolve()
            self.query_one("#picker-tree", DirectoryTree).path = str(resolved)
            self.query_one("#picker-path-input", Input).value = str(resolved)

        def action_go_up(self) -> None:
            raw = str(self.query_one("#picker-path-input", Input).value or "").strip()
            current = Path(raw).expanduser() if raw else self.initial_path
            base = current if current.is_dir() else current.parent
            parent = base.parent if base.parent != base else base
            self._set_tree_root(parent)

        def action_go_home(self) -> None:
            self._set_tree_root(self.home_path)

        def on_input_submitted(self, event: Input.Submitted) -> None:
            if event.input.id == "picker-path-input":
                raw = str(event.value or "").strip()
                if not raw:
                    return
                path = Path(raw).expanduser()
                self._set_tree_root(path)

        def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
            self.query_one("#picker-path-input", Input).value = str(event.path)

        def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
            self.query_one("#picker-path-input", Input).value = str(event.path)

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "picker-cancel":
                self.dismiss(None)
            elif event.button.id == "picker-select":
                self.action_confirm()
            elif event.button.id == "picker-up":
                self.action_go_up()
            elif event.button.id == "picker-home":
                self.action_go_home()


    class ConfirmExitScreen(ModalScreen[bool]):
        BINDINGS = [("escape", "cancel", "Cancel"), ("enter", "confirm", "Confirm")]

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static("Exit PhotoMigrator", classes="modal-title"),
                Static("Are you sure you want to close the tool?", classes="modal-subtitle"),
                Horizontal(
                    Button("Cancel", id="exit-cancel"),
                    Button("Exit", id="exit-confirm", variant="error"),
                    id="picker-actions",
                ),
                id="picker-dialog",
            )

        def action_cancel(self) -> None:
            self.dismiss(False)

        def action_confirm(self) -> None:
            self.dismiss(True)

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "exit-cancel":
                self.dismiss(False)
            elif event.button.id == "exit-confirm":
                self.dismiss(True)


    class PhotoMigratorTUI(App[None]):
        CSS = """
        Screen {
            layout: vertical;
            background: #11161f;
            color: #f4f7fb;
        }
        #workspace {
            height: 1fr;
        }
        #sidebar {
            width: 32;
            min-width: 28;
            border: round #31465f;
            padding: 1 1;
            background: #131c28;
        }
        #sidebar-features {
            height: 1fr;
            margin-bottom: 1;
        }
        #sidebar-actions {
            height: auto;
            margin-top: 1;
        }
        #sidebar-run-stop {
            height: auto;
            layout: grid;
            grid-size: 2 1;
            grid-columns: 1fr 1fr;
            grid-gutter: 1 0;
            margin-bottom: 1;
        }
        .sidebar-action {
            width: 100%;
            height: 3;
            min-height: 3;
            text-style: bold;
            border: round #495c73;
        }
        .sidebar-action--run.is-enabled {
            background: #c9ebcf;
            color: #22462a;
        }
        .sidebar-action--stop.is-enabled {
            background: #efc8c8;
            color: #6c2727;
        }
        .sidebar-action--exit.is-enabled {
            background: #efb7b7;
            color: #6c2727;
        }
        .sidebar-action.is-disabled {
            background: #3a4452;
            color: #98a4b3;
        }
        #sidebar-title {
            text-style: bold;
            color: #f4f7fb;
            margin-bottom: 1;
        }
        .sidebar-caption {
            color: #8ea3bf;
            margin-bottom: 1;
        }
        .module-tab {
            width: 100%;
            margin: 0 0 1 0;
            text-style: bold;
            border: round #495c73;
        }
        .module-tab.is-active {
            border: heavy #ffffff;
            text-style: bold;
        }
        .module-tab--migration { background: #c9ebcf; color: #22462a; }
        .module-tab--migration.is-active { background: #8fd89d; color: #17351e; }
        .module-tab--takeout { background: #f4edbe; color: #5e5420; }
        .module-tab--takeout.is-active { background: #f1cf57; color: #5a4700; }
        .module-tab--cloud { background: #eee0d1; color: #5f432b; }
        .module-tab--cloud.is-active { background: #d5b290; color: #432c1a; }
        .module-tab--standalone { background: #e6d8ef; color: #54366f; }
        .module-tab--standalone.is-active { background: #c6addf; color: #3e2257; }
        .module-tab--upload { background: #efc8c8; color: #6c2727; }
        .module-tab--upload.is-active { background: #e59a9a; color: #581e1e; }
        #content-stack {
            width: 1fr;
            height: 1fr;
            padding-left: 1;
        }
        #content-host {
            height: 4fr;
            min-height: 10;
        }
        #general-tabs {
            height: auto;
            margin-bottom: 1;
        }
        #general-tabs-left {
            width: 1fr;
            height: auto;
        }
        #general-tabs-right {
            width: auto;
            height: auto;
        }
        .general-tab {
            margin-right: 1;
            border: round #43566d;
            background: #152131;
            color: #d6dfeb;
        }
        .general-tab.is-active {
            background: #2e4f78;
            color: #ffffff;
            text-style: bold;
        }
        .toolbar-btn {
            margin-left: 1;
            border: round #8a5b5b;
            background: #efc8c8;
            color: #6c2727;
            text-style: bold;
        }
        #content-panel {
            height: 1fr;
            min-height: 10;
            border: round #37547b;
            padding: 1 1 0 1;
            background: #0d141e;
        }
        .panel-title {
            color: #ffffff;
            text-style: bold;
            margin-bottom: 0;
        }
        .panel-description {
            color: #9ab0c9;
            margin-bottom: 0;
        }
        .section-title {
            color: #cfe0f5;
            text-style: bold;
            margin: 0 0 1 0;
        }
        .feature-section-title {
            color: #f0c88b;
            margin: 1 0 0 0;
        }
        .form-columns {
            width: 1fr;
            height: auto;
        }
        .form-column {
            width: 1fr;
            min-width: 0;
            padding-right: 1;
        }
        .form-groups-grid {
            width: 1fr;
            height: auto;
            grid-size: 2;
            grid-columns: 1fr 1fr;
            grid-gutter: 1 0;
        }
        .general-group-card {
            width: 1fr;
            min-width: 0;
            height: auto;
        }
        .general-group-title {
            color: #f0c88b;
        }
        .field-row {
            height: auto;
            margin-bottom: 0;
        }
        .bool-toggle {
            width: auto;
            height: 1;
            min-height: 1;
            margin-top: 1;
        }
        .bool-toggle-btn {
            width: 3;
            min-width: 3;
            height: 1;
            min-height: 1;
            margin-right: 1;
            border: none;
            background: transparent;
            color: #9aa6b4;
            text-style: bold;
            padding: 0;
        }
        .bool-toggle-btn.is-active {
            border: none;
        }
        .bool-toggle-off.is-active {
            background: transparent;
            color: #ff5a5a;
        }
        .bool-toggle-on.is-active {
            background: transparent;
            color: #4cff7a;
        }
        .field-label {
            width: 28;
            min-width: 28;
            padding-top: 1;
            color: #d6dfeb;
        }
        .field-label--config-accent {
            color: #f0c88b;
            text-style: bold;
        }
        .field-label--config {
            width: 40;
            min-width: 40;
        }
        .field-main {
            width: 1fr;
            min-width: 0;
            height: 3;
            min-height: 3;
        }
        .field-path-control {
            width: 1fr;
            min-width: 0;
            height: 3;
            min-height: 3;
            layout: grid;
            grid-size: 2 1;
            grid-columns: 1fr 5;
            grid-gutter: 1 0;
            padding-right: 1;
        }
        .field-control {
            width: 1fr;
            min-width: 0;
            height: 3;
            min-height: 3;
            padding-right: 1;
        }
        .field-main > Input, .field-main > Select,
        .field-path-control > Input,
        .field-control > Input, .field-control > Select,
        .field-control-widget {
            width: 1fr;
            min-width: 0;
        }
        .field-help {
            color: #7f93ab;
            margin-left: 28;
            margin-bottom: 1;
        }
        .path-button {
            width: 5;
            min-width: 5;
            height: 3;
            margin-left: 0;
            content-align: center middle;
        }
        .card {
            border: round #2f3f54;
            padding: 1 1;
            margin-bottom: 1;
            background: #121d2b;
        }
        .flags-grid {
            height: auto;
            margin-bottom: 0;
        }
        .flags-column {
            width: 1fr;
            padding-right: 1;
        }
        #bottom-panels {
            height: 3fr;
            min-height: 0;
            margin-top: 0;
        }
        #control-row {
            height: auto;
            margin-bottom: 0;
        }
        #control-row Button {
            height: 3;
            min-height: 3;
        }
        #status-line {
            height: auto;
            min-height: 2;
            border: round #37547b;
            padding: 0 1;
            margin-bottom: 0;
            background: #0d141e;
            color: #dfeaf8;
        }
        #field-description {
            height: auto;
            min-height: 3;
            border: round #37547b;
            padding: 0 1;
            margin-bottom: 0;
            background: #0d141e;
            color: #dfeaf8;
        }
        #command-preview {
            height: auto;
            min-height: 3;
            border: round #37547b;
            padding: 0 1;
            margin-bottom: 0;
            background: #0d141e;
        }
        #log-panel {
            height: 1fr;
            min-height: 12;
            border: round #37547b;
            background: #0b1119;
        }
        #job-input-row {
            height: auto;
            margin-top: 0;
        }
        #job-input {
            width: 1fr;
        }
        #picker-dialog {
            width: 80%;
            height: 80%;
            border: round #4f6b92;
            padding: 1 1;
            background: #0f1722;
            align: center middle;
        }
        .modal-title { text-style: bold; color: #ffffff; margin-bottom: 1; }
        .modal-subtitle { color: #92a8c3; margin-bottom: 1; }
        #picker-nav-actions { height: auto; margin: 0 0 0 0; }
        #picker-tree { height: 1fr; margin: 0; }
        #picker-actions { height: auto; }
        .danger-note { color: #ffb4b4; }
        .empty-note { color: #8da4be; margin-top: 1; }
        .theme-ocean {
            background: #11161f;
            color: #f4f7fb;
        }
        .theme-ocean #sidebar { background: #131c28; border: round #31465f; }
        .theme-ocean #content-panel { background: #0d141e; border: round #3b78b7; color: #dfeaf8; }
        .theme-ocean #field-description, .theme-ocean #status-line { background: #0d141e; border: round #3b78b7; color: #dfeaf8; }
        .theme-ocean #command-preview { background: #0d141e; border: round #3b78b7; color: #dfeaf8; }
        .theme-ocean #log-panel { background: #0b1119; border: round #3b78b7; color: #d9e8f8; }
        .theme-ocean .general-tab { background: #152131; color: #d6dfeb; border: round #43566d; }
        .theme-ocean .general-tab.is-active { background: #2e4f78; color: #ffffff; }
        .theme-ocean .field-label, .theme-ocean .section-title, .theme-ocean .panel-title { color: #d6dfeb; }
        .theme-ocean .field-label--config-accent { color: #7fd4ff; }
        .theme-ocean .general-group-title { color: #7fd4ff; }
        .theme-ocean .feature-section-title { color: #7fd4ff; }
        .theme-ocean .field-help, .theme-ocean .panel-description { color: #8ea3bf; }

        .theme-emerald {
            background: #0f1714;
            color: #edf7f1;
        }
        .theme-emerald #sidebar { background: #13201b; border: round #3f6f5a; }
        .theme-emerald #content-panel { background: #0d1713; border: round #3f8f72; color: #def4e7; }
        .theme-emerald #field-description, .theme-emerald #status-line { background: #0d1713; border: round #3f8f72; color: #def4e7; }
        .theme-emerald #command-preview { background: #0d1713; border: round #3f8f72; color: #def4e7; }
        .theme-emerald #log-panel { background: #0b1411; border: round #3f8f72; color: #def4e7; }
        .theme-emerald .general-tab { background: #173127; color: #d6ebe0; border: round #406a58; }
        .theme-emerald .general-tab.is-active { background: #2d6b55; color: #ffffff; }
        .theme-emerald .field-label, .theme-emerald .section-title, .theme-emerald .panel-title { color: #daf0e4; }
        .theme-emerald .field-label--config-accent { color: #7dffbf; }
        .theme-emerald .general-group-title { color: #7dffbf; }
        .theme-emerald .feature-section-title { color: #7dffbf; }
        .theme-emerald .field-help, .theme-emerald .panel-description { color: #9dc3b0; }
        .theme-emerald .toolbar-btn { background: #e8c5c5; color: #703131; border: round #875858; }

        .theme-sunset {
            background: #1a1410;
            color: #fbf1e8;
        }
        .theme-sunset #sidebar { background: #231913; border: round #7d5a42; }
        .theme-sunset #content-panel { background: #18110d; border: round #b26a3a; color: #f7e6d7; }
        .theme-sunset #field-description, .theme-sunset #status-line { background: #18110d; border: round #b26a3a; color: #f7e6d7; }
        .theme-sunset #command-preview { background: #18110d; border: round #b26a3a; color: #f7e6d7; }
        .theme-sunset #log-panel { background: #140f0b; border: round #b26a3a; color: #f7e6d7; }
        .theme-sunset .general-tab { background: #35231a; color: #f0dfd1; border: round #7f5d47; }
        .theme-sunset .general-tab.is-active { background: #8d5630; color: #fff7f1; }
        .theme-sunset .field-label, .theme-sunset .section-title, .theme-sunset .panel-title { color: #f2e1d3; }
        .theme-sunset .field-label--config-accent { color: #ffd29a; }
        .theme-sunset .general-group-title { color: #ffd29a; }
        .theme-sunset .feature-section-title { color: #ffd29a; }
        .theme-sunset .field-help, .theme-sunset .panel-description { color: #cfb39f; }
        .theme-sunset .toolbar-btn { background: #efc8c8; color: #7a2c2c; border: round #9a6161; }

        .theme-dark {
            background: #0c0f14;
            color: #e6ebf2;
        }
        .theme-dark #sidebar { background: #11161d; border: round #4c5867; }
        .theme-dark #content-panel { background: #0b1016; border: round #6d7a8d; color: #d8e0ea; }
        .theme-dark #field-description, .theme-dark #status-line { background: #0b1016; border: round #6d7a8d; color: #d8e0ea; }
        .theme-dark #command-preview { background: #0b1016; border: round #6d7a8d; color: #d8e0ea; }
        .theme-dark #log-panel { background: #090d12; border: round #6d7a8d; color: #d8e0ea; }
        .theme-dark .general-tab { background: #1a212b; color: #d0d9e4; border: round #526072; }
        .theme-dark .general-tab.is-active { background: #39485c; color: #ffffff; }
        .theme-dark .field-label, .theme-dark .section-title, .theme-dark .panel-title { color: #dbe3ee; }
        .theme-dark .field-label--config-accent { color: #b8c7ff; }
        .theme-dark .general-group-title { color: #b8c7ff; }
        .theme-dark .feature-section-title { color: #b8c7ff; }
        .theme-dark .field-help, .theme-dark .panel-description { color: #9aa7b7; }
        .theme-dark .toolbar-btn { background: #dcb8b8; color: #5e2323; border: round #7d5252; }
        """

        BINDINGS = [
            ("ctrl+r", "run_job", "Run"),
            ("ctrl+s", "save_config", "Save Config"),
            ("ctrl+l", "reload_config", "Reload Config"),
            ("ctrl+q", "quit", "Quit"),
        ]

        def __init__(self, project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None):
            super().__init__()
            self.project_root = project_root.resolve()
            self.cli_entrypoint = cli_entrypoint.resolve()
            self.initial_values = dict(initial_values or {})
            self.schema = build_parser_schema()
            self.persisted = load_json_file(TUI_STATE_PATH, {})
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
            self.config_widget_map: Dict[str, tuple[str, str]] = {}
            self.field_help_map: Dict[str, str] = {}
            self.last_focused_widget_id = ""
            self.last_hovered_widget_id = ""
            self.selected_theme = str(self.ui_state.get("theme") or "ocean")
            self.remember_state = bool(self.ui_state.get("remember_state", True))
            self.launch_cwd = Path.cwd().resolve()
            self.running_process: subprocess.Popen[str] | None = None
            self.running_command: List[str] = []
            if self.active_module not in INTERACTIVE_MODULE_TAB_NAMES:
                self.active_module = "automatic_migration"
            self.reload_config_model()

        def preferred_config_section(self) -> str:
            mapped = MODULE_TO_CONFIG_SECTION.get(self.active_module)
            if mapped:
                return mapped
            if self.active_config_section in CONFIG_EDITOR_SECTIONS_ORDER:
                return self.active_config_section
            return CONFIG_EDITOR_SECTIONS_ORDER[0]

        def current_config_path(self) -> Path:
            raw = str(self.state_values.get("configuration-file") or "").strip()
            if raw:
                return Path(raw).expanduser()
            return self.project_root / "Config.ini"

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

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="workspace"):
                with Vertical(id="sidebar"):
                    yield Static("PhotoMigrator CLI TUI", id="sidebar-title")
                    with VerticalScroll(id="sidebar-features"):
                        for key, label in INTERACTIVE_MODULE_TAB_NAMES.items():
                            classes = f"module-tab {MODULE_GROUP_CLASSES.get(key, '')}"
                            yield Button(label, id=f"module-tab-{key}", classes=classes)
                    with Vertical(id="sidebar-actions"):
                        with Horizontal(id="sidebar-run-stop"):
                            yield Button("Run", id="run-btn", classes="sidebar-action sidebar-action--run")
                            yield Button("Stop", id="stop-btn", classes="sidebar-action sidebar-action--stop")
                        yield Button("Exit", id="exit-btn", classes="sidebar-action sidebar-action--exit")
                with Vertical(id="content-stack"):
                    with Horizontal(id="general-tabs"):
                        with Horizontal(id="general-tabs-left"):
                            for key, label in GENERAL_TAB_NAMES.items():
                                yield Button(label, id=f"general-tab-{key}", classes="general-tab")
                        with Horizontal(id="general-tabs-right"):
                            yield Button("Save Config", id="save-config-btn", classes="toolbar-btn")
                            yield Button("Reload Config", id="reload-config-btn", classes="toolbar-btn")
                            yield Button("Save UI State", id="save-ui-state-btn", classes="toolbar-btn")
                    yield Vertical(id="content-host")
                    with Vertical(id="bottom-panels"):
                        yield Static("Move focus to a field to see its description here.", id="field-description")
                        yield Static("", id="command-preview")
                        yield RichLog(id="log-panel", wrap=True, markup=False, highlight=False)
                        yield Static("Ready.", id="status-line")
                        with Horizontal(id="job-input-row"):
                            yield Input(placeholder="Send input to running job if it requests confirmation", id="job-input")
                            yield Button("Send", id="send-input-btn")
            yield Footer()

        async def on_mount(self) -> None:
            self.apply_theme()
            self.refresh_tab_styles()
            await self.rebuild_content()
            self.update_command_preview()
            self.refresh_action_buttons()
            self.set_interval(0.15, self.sync_field_description_from_focus)

        async def rebuild_content(self) -> None:
            host = self.query_one("#content-host", Vertical)
            await host.remove_children()
            self.field_help_map = {}
            self.last_focused_widget_id = ""
            self.last_hovered_widget_id = ""
            widgets: List[Any] = []
            widgets.extend(self.build_content_widgets())
            content_panel: Any
            if self.active_general_tab == "feature":
                content_panel = Vertical(id="content-panel")
            else:
                content_panel = VerticalScroll(id="content-panel")
            await host.mount(content_panel)
            if widgets:
                await content_panel.mount(*widgets)
            self.refresh_panel_titles()
            self.update_field_description("Move focus to a field to see its description here.")
            self.call_after_refresh(self.refresh_panel_titles)
            self.call_after_refresh(self.refresh_content_scrollbar)
            self.set_timer(0.05, self.refresh_panel_titles)
            self.set_timer(0.05, self.refresh_content_scrollbar)

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
            return "Terminal UI preferences and local state persistence."

        def refresh_panel_titles(self) -> None:
            try:
                self.query_one("#sidebar", Vertical).border_title = "Feature Selector"
            except Exception:
                pass
            try:
                title = self.current_content_panel_title()
                description = self.current_content_panel_description()
                self.query_one("#content-panel").border_title = f"{title}: {description}" if description else title
            except Exception:
                pass
            try:
                self.query_one("#field-description", Static).border_title = "Argument Description"
            except Exception:
                pass
            try:
                self.query_one("#status-line", Static).border_title = "Status"
            except Exception:
                pass
            try:
                self.query_one("#command-preview", Static).border_title = "Command Preview"
            except Exception:
                pass
            try:
                self.query_one("#log-panel", RichLog).border_title = "Execution Log"
            except Exception:
                pass

        def build_content_widgets(self) -> List[Any]:
            if self.active_general_tab == "feature":
                return self.build_feature_widgets()
            if self.active_general_tab == "general":
                return self.build_general_arguments_widgets()
            if self.active_general_tab == "features_config":
                return self.build_config_widgets()
            return self.build_app_settings_widgets()

        def build_feature_widgets(self) -> List[Any]:
            widgets: List[Any] = []
            if self.active_module == "upload_folder":
                widgets.append(Static("Upload to Server is only available in the Web Interface.", classes="empty-note"))
                return widgets

            if self.active_module == "automatic_migration":
                widgets.extend(self.build_module_only_fields("automatic_migration", self.schema["tabs"]["automatic_migration"]))
                return widgets
            if self.active_module in {"google_takeout", "icloud_takeout"}:
                widgets.extend(self.build_module_only_fields(self.active_module, self.schema["tabs"][self.active_module]))
                return widgets
            if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
                widgets.extend(self.build_cloud_widgets())
                return widgets
            if self.active_module == "standalone_features":
                widgets.extend(self.build_standalone_widgets())
                return widgets
            return widgets

        def build_general_arguments_widgets(self) -> List[Any]:
            groups_grid = self.build_general_groups_grid()
            return [
                groups_grid,
            ]

        def build_general_groups_grid(self) -> Grid:
            fields_by_dest = {field["dest"]: field for field in self.schema["general_tabs"]["general"]}
            used = set()
            group_cards: List[Vertical] = []
            for group in GENERAL_GROUPS:
                group_fields = [fields_by_dest[dest] for dest in group["dests"] if dest in fields_by_dest]
                if not group_fields:
                    continue
                block: List[Any] = [Static(group["title"], classes="section-title general-group-title")]
                for field in group_fields:
                    used.add(field["dest"])
                    block.extend(self.build_field_widgets(field, context="general"))
                group_cards.append(Vertical(*block, classes="general-group-card"))
            remaining = [field for field in self.schema["general_tabs"]["general"] if field["dest"] not in used]
            if remaining:
                block = [Static("Other", classes="section-title")]
                for field in remaining:
                    block.extend(self.build_field_widgets(field, context="general"))
                group_cards.append(Vertical(*block, classes="general-group-card"))
            return Grid(*group_cards, classes="form-groups-grid")

        def build_module_only_fields(self, tab_key: str, fields: List[Dict[str, Any]]) -> List[Any]:
            widgets = []
            if tab_key == "automatic_migration":
                widgets.append(Static("Module Fields", classes="section-title feature-section-title"))
                for field in fields:
                    if str(field.get("dest") or "") in {"source", "target"}:
                        widgets.append(self.build_migration_endpoint_row(str(field.get("dest") or ""), str(field.get("help") or "").strip()))
                    else:
                        widgets.extend(self.build_field_widgets(field, context=tab_key))
                return widgets
            if tab_key in {"google_takeout", "icloud_takeout"}:
                regular_fields = [field for field in fields if str(field.get("kind") or "") not in {"flag", "bool"}]
                toggle_fields = [field for field in fields if str(field.get("kind") or "") in {"flag", "bool"}]

                if regular_fields:
                    widgets.append(Static("Module Fields", classes="section-title feature-section-title"))
                    for field in regular_fields:
                        widgets.extend(self.build_field_widgets(field, context=tab_key))

                if toggle_fields:
                    widgets.append(Static("Flags", classes="section-title feature-section-title"))
                    widgets.append(self.build_flags_columns(toggle_fields, tab_key))
                return widgets

            widgets.append(Static("Module Fields", classes="section-title feature-section-title"))
            for field in fields:
                widgets.extend(self.build_field_widgets(field, context=tab_key))
            return widgets

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

        def build_migration_endpoint_row(self, dest: str, help_text: str) -> Horizontal:
            state = self.migration_endpoint_state(dest)
            kind_options = [
                ("Synology Photos", "synology"),
                ("Immich Photos", "immich"),
                ("NextCloud Photos", "nextcloud"),
                ("Google Photos", "google"),
                ("Select Folder", "folder"),
            ]
            kind_select = self.build_select_row(
                dest.title(),
                f"migration-kind-{dest}",
                kind_options,
                state.get("kind") or self.migration_default_kind(dest),
                help_text=help_text,
            )
            secondary: Any
            if state.get("kind") == "folder":
                path_value = str(state.get("path") or "")
                input_widget = Input(value=path_value, id=f"field-{dest}", classes="field-control-widget")
                self.register_field_help(f"field-{dest}", help_text)
                self.register_field_help(f"browse-{dest}", help_text or dest.title())
                secondary = Horizontal(
                    Label("Folder Path", classes="field-label"),
                    Grid(input_widget, Button("...", id=f"browse-{dest}", classes="path-button"), classes="field-path-control"),
                    classes="field-row",
                )
            else:
                account_options = [("Account 1", "1"), ("Account 2", "2"), ("Account 3", "3")]
                secondary = self.build_select_row(
                    "Account",
                    f"migration-account-{dest}",
                    account_options,
                    state.get("account") or "1",
                    help_text=help_text,
                )
            return Vertical(kind_select, secondary, classes="general-group-card")

        def build_flags_columns(self, fields: List[Dict[str, Any]], context: str) -> Horizontal:
            total = len(fields or [])
            num_columns = 3 if total >= 9 else 2
            num_columns = min(num_columns, total) if total > 0 else 1
            columns: List[List[Dict[str, Any]]] = [[] for _ in range(max(1, num_columns))]
            for index, field in enumerate(fields or []):
                columns[index % len(columns)].append(field)

            children: List[Vertical] = []
            for items in columns:
                column_widgets: List[Any] = []
                for field in items:
                    column_widgets.extend(self.build_field_widgets(field, context=context))
                children.append(Vertical(*column_widgets, classes="flags-column"))
            return Horizontal(*children, classes="flags-grid")

        def build_cloud_widgets(self) -> List[Any]:
            widgets = []
            widgets.append(Static("Action", classes="section-title feature-section-title"))
            actions = list(self.schema["tabs"][self.active_module])
            available = CLOUD_ACTIONS_AVAILABLE_BY_TAB.get(self.active_module)
            if available is not None:
                actions = [field for field in actions if field["dest"] in available]
            if not actions:
                widgets.append(Static("No cloud actions available for this module.", classes="empty-note"))
                return widgets
            selected_dest = str(self.cloud_action_dest.get(self.active_module) or "")
            if selected_dest not in {field["dest"] for field in actions}:
                selected_dest = actions[0]["dest"]
                self.cloud_action_dest[self.active_module] = selected_dest
            select_options = [(ui_option_name(field), field["dest"]) for field in actions]
            widgets.append(self.build_select_row("Cloud Action", "cloud-action-select", select_options, selected_dest, help_text="Select the cloud action to configure for the current service."))
            selected = next((field for field in actions if field["dest"] == selected_dest), None)
            if selected:
                widgets.append(Static(str(selected.get("help") or "").strip(), classes="panel-description"))
            specs = build_argument_specs(self.schema, self.active_module, selected, True)
            account_field = get_field_by_dest(self.schema, "account-id")
            if account_field:
                normalized = normalize_field_for_context(account_field, self.active_module)
                specs = [spec for spec in specs if spec["field"]["dest"] != "account-id"]
                insert_at = next((idx for idx, spec in enumerate(specs) if not spec["required"]), len(specs))
                specs.insert(insert_at, {"field": normalized, "required": False})
            widgets.append(Static("Action Arguments", classes="section-title feature-section-title"))
            if selected and selected.get("dest") == "rename-albums":
                parsed = parse_rename_albums_value(self.state_values.get("rename-albums"))
                if not str(self.state_values.get("rename-pattern") or "").strip():
                    self.state_values["rename-pattern"] = parsed.get("pattern") or ""
                if not str(self.state_values.get("replacement-pattern") or "").strip():
                    self.state_values["replacement-pattern"] = parsed.get("replacement") or ""
                for spec in specs:
                    if spec["field"]["dest"] not in {"rename-albums"}:
                        widgets.extend(self.build_field_widgets(spec["field"], required=spec["required"], context=self.active_module))
                widgets.extend(self.build_pseudo_text_field("Rename Pattern", "rename-pattern", self.state_values.get("rename-pattern", ""), True, "Album name pattern (text or regex)."))
                widgets.extend(self.build_pseudo_text_field("Replacement Pattern", "replacement-pattern", self.state_values.get("replacement-pattern", ""), True, "Replacement pattern used during album rename."))
            else:
                for spec in specs:
                    widgets.extend(self.build_field_widgets(spec["field"], required=spec["required"], context=self.active_module))
            otp_field = get_field_by_dest(self.schema, "one-time-password")
            if otp_field and self.active_module in {"synology_photos", "immich_photos", "nextcloud_photos", "google_photos"}:
                widgets.append(Static("Optional", classes="section-title feature-section-title"))
                widgets.extend(self.build_field_widgets(otp_field, required=False, context=self.active_module))
            return widgets

        def build_standalone_widgets(self) -> List[Any]:
            widgets = []
            actions = list(self.schema["tabs"]["standalone_features"])
            if not actions:
                widgets.append(Static("No standalone actions available.", classes="empty-note"))
                return widgets
            selected_dest = self.standalone_action_dest if self.standalone_action_dest in {field["dest"] for field in actions} else actions[0]["dest"]
            self.standalone_action_dest = selected_dest
            widgets.append(Static("Action", classes="section-title feature-section-title"))
            widgets.append(self.build_select_row("Standalone Action", "standalone-action-select", [(ui_option_name(field), field["dest"]) for field in actions], selected_dest, help_text="Select the standalone feature to configure and run."))
            selected = next((field for field in actions if field["dest"] == selected_dest), None)
            if selected:
                widgets.append(Static(str(selected.get("help") or "").strip(), classes="panel-description"))
            widgets.append(Static("Action Arguments", classes="section-title feature-section-title"))
            if selected and selected.get("dest") == "find-duplicates":
                parsed = parse_find_duplicates_value(self.state_values.get("find-duplicates"))
                self.state_values["find-duplicates-action"] = parsed.get("action") or "list"
                if not self.state_values.get("find-duplicates-folders"):
                    self.state_values["find-duplicates-folders"] = parsed.get("folders") or []
                widgets.append(self.build_select_row("Duplicates Action", "find-duplicates-action-select", [("list", "list"), ("move", "move"), ("delete", "delete")], str(self.state_values.get("find-duplicates-action") or "list"), help_text="Choose what the duplicates scan should do with detected duplicates: list, move, or delete."))
                widgets.extend(self.build_pseudo_list_field("Folder(s)", "find-duplicates-folders", self.state_values.get("find-duplicates-folders", []), True, "One or more folders separated by comma or newline."))
            else:
                specs = build_argument_specs(self.schema, "standalone_features", selected, True)
                for spec in specs:
                    widgets.extend(self.build_field_widgets(spec["field"], required=spec["required"], context="standalone_features"))
                if selected and selected.get("dest") == "rename-folders-content-based":
                    widgets.append(Static("This action renames folders in place. Review date and range separators before running it.", classes="danger-note"))
            return widgets

        def build_config_widgets(self) -> List[Any]:
            self.config_widget_map = {}
            widgets: List[Any] = []
            section_options = [(section["name"], section["name"]) for section in self.config_sections]
            widgets.append(
                self.build_select_row(
                    "Config Section",
                    "config-section-select",
                    section_options,
                    self.active_config_section,
                    help_text="Select which Config.ini section you want to edit.",
                    label_classes="field-label field-label--config-accent",
                )
            )
            current_section = next((section for section in self.config_sections if section["name"] == self.active_config_section), None)
            if not current_section:
                widgets.append(Static("No configuration section selected.", classes="empty-note"))
                return widgets
            widgets.append(Static(str(current_section.get("description") or "").strip(), classes="panel-description"))
            fields = list(current_section.get("fields") or [])
            global_fields = [field for field in fields if not str(field.get("account_id") or "")]
            account_fields = [field for field in fields if str(field.get("account_id") or "")]
            for field in global_fields:
                widgets.extend(self.build_config_field_widgets(current_section["name"], field))
            selector = current_section.get("account_selector") or {}
            if selector.get("enabled"):
                section_name = current_section["name"]
                account_value = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
                widgets.append(
                    self.build_select_row(
                        "Configure Account",
                        "config-account-select",
                        [(f"Account {acc}", acc) for acc in selector.get("accounts") or []],
                        account_value,
                        help_text="Select which account within this service section you want to configure.",
                        label_classes="field-label field-label--config-accent",
                    )
                )
                selected_account = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
                visible_account_fields = [field for field in account_fields if str(field.get("account_id") or "") == selected_account]
                for field in visible_account_fields:
                    widgets.extend(self.build_config_field_widgets(section_name, field))
            else:
                for field in account_fields:
                    widgets.extend(self.build_config_field_widgets(current_section["name"], field))
            return widgets

        def build_app_settings_widgets(self) -> List[Any]:
            widgets: List[Any] = [
                self.build_select_row("Theme", "theme-select", THEME_CHOICES, self.selected_theme, help_text="Select the visual theme used by the CLI TUI."),
                self.build_boolean_toggle_row("Remember UI state", "remember-state", self.remember_state, help_text="Persist the current terminal UI state, selected tabs, and entered values between sessions."),
                Static(f"State file: {TUI_STATE_PATH}", classes="field-help"),
                Static(f"Config file in use: {self.current_config_path()}", classes="field-help"),
                Static("Use Ctrl+S to save Config.ini and Ctrl+R to run the current module.", classes="field-help"),
            ]
            return widgets

        def register_field_help(self, widget_id: str, help_text: str) -> None:
            text = str(help_text or "").strip()
            if text:
                self.field_help_map[widget_id] = text

        def update_field_description(self, text: str) -> None:
            self.query_one("#field-description", Static).update(str(text or "").strip() or "Move focus to a field to see its description here.")

        def _resolve_help_for_widget_id(self, widget_id: str) -> str:
            return str(self.field_help_map.get(str(widget_id or ""), "") or "").strip()

        def sync_field_description_from_focus(self) -> None:
            try:
                focused = getattr(self.screen, "focused", None)
                widget_id = str(getattr(focused, "id", "") or "")
            except Exception:
                widget_id = ""
            if widget_id == self.last_focused_widget_id and self.last_hovered_widget_id:
                return
            self.last_focused_widget_id = widget_id
            if self.last_hovered_widget_id:
                help_text = self._resolve_help_for_widget_id(self.last_hovered_widget_id)
                if help_text:
                    self.update_field_description(help_text)
                    return
            help_text = self._resolve_help_for_widget_id(widget_id)
            if help_text:
                self.update_field_description(help_text)
            else:
                self.update_field_description("Move focus to a field to see its description here.")

        def on_mouse_move(self, event: events.MouseMove) -> None:
            widget_id = ""
            help_text = ""
            try:
                widget_info = self.screen.get_widget_at(event.screen_x, event.screen_y)
                hovered_widget = widget_info[0] if isinstance(widget_info, tuple) else widget_info
                current = hovered_widget
                while current is not None:
                    candidate_id = str(getattr(current, "id", "") or "")
                    help_text = self._resolve_help_for_widget_id(candidate_id)
                    if help_text:
                        widget_id = candidate_id
                        break
                    current = getattr(current, "parent", None)
            except Exception:
                widget_id = ""
                help_text = ""

            if widget_id == self.last_hovered_widget_id:
                return

            self.last_hovered_widget_id = widget_id
            if help_text:
                self.update_field_description(help_text)
                return
            self.sync_field_description_from_focus()

        def _widget_under_pointer(self, screen_x: int, screen_y: int) -> Any | None:
            try:
                widget_info = self.screen.get_widget_at(screen_x, screen_y)
                return widget_info[0] if isinstance(widget_info, tuple) else widget_info
            except Exception:
                return None

        def _widget_is_within(self, widget: Any | None, ancestor_id: str) -> bool:
            current = widget
            while current is not None:
                if str(getattr(current, "id", "") or "") == ancestor_id:
                    return True
                current = getattr(current, "parent", None)
            return False

        def _content_panel_overflows(self) -> bool:
            try:
                container = self.query_one("#content-panel")
                if not isinstance(container, VerticalScroll):
                    return False
                return int(getattr(container, "max_scroll_y", 0) or 0) > 1
            except Exception:
                return True

        def refresh_content_scrollbar(self) -> None:
            try:
                container = self.query_one("#content-panel")
                if isinstance(container, VerticalScroll):
                    container.styles.scrollbar_visibility = "visible" if self._content_panel_overflows() else "hidden"
            except Exception:
                pass

        def on_resize(self, event: events.Resize) -> None:
            self.call_after_refresh(self.refresh_content_scrollbar)

        def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            if self._widget_is_within(hovered_widget, "content-panel") and not self._content_panel_overflows():
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            if self._widget_is_within(hovered_widget, "content-panel") and not self._content_panel_overflows():
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def build_select_row(
            self,
            label: str,
            widget_id: str,
            options: List[tuple[str, Any]],
            value: Any,
            help_text: str = "",
            label_classes: str = "field-label",
        ) -> Horizontal:
            normalized_options = [(str(label_text), str(option_value)) for label_text, option_value in options]
            current_value = str(value or "")
            if current_value and all(option_value != current_value for _, option_value in normalized_options):
                normalized_options = [*normalized_options, (current_value, current_value)]
            select = Select(
                normalized_options,
                value=current_value or (normalized_options[0][1] if normalized_options else None),
                id=widget_id,
                classes="field-control-widget",
            )
            self.register_field_help(widget_id, help_text)
            return Horizontal(Label(label, classes=label_classes), Horizontal(select, classes="field-control"), classes="field-row")

        def build_checkbox_row(self, label: str, widget_id: str, value: bool, help_text: str = "") -> Horizontal:
            self.register_field_help(widget_id, help_text)
            return Horizontal(Label(label, classes="field-label"), Checkbox(value=bool(value), id=widget_id), classes="field-row")

        def build_boolean_toggle_row(self, label: str, dest: str, value: bool, help_text: str = "") -> Horizontal:
            off_id = f"bool-{dest}-off"
            on_id = f"bool-{dest}-on"
            self.register_field_help(off_id, help_text)
            self.register_field_help(on_id, help_text)
            off_button = Button("✕", id=off_id, classes="bool-toggle-btn bool-toggle-off")
            on_button = Button("✓", id=on_id, classes="bool-toggle-btn bool-toggle-on")
            off_button.set_class(not bool(value), "is-active")
            on_button.set_class(bool(value), "is-active")
            return Horizontal(
                Label(label, classes="field-label"),
                Horizontal(off_button, on_button, classes="bool-toggle"),
                classes="field-row",
            )

        def build_pseudo_text_field(self, label: str, dest: str, value: Any, required: bool, help_text: str) -> List[Any]:
            return self.build_input_block(label, dest, str(value or ""), required, help_text, path_hint="")

        def build_pseudo_list_field(self, label: str, dest: str, value: Any, required: bool, help_text: str) -> List[Any]:
            joined = ", ".join(parse_folder_list_value(value))
            return self.build_input_block(label, dest, joined, required, help_text, path_hint="path", browse_title=f"Select paths for {label}")

        def build_input_block(self, label: str, dest: str, value: str, required: bool, help_text: str, path_hint: str = "", browse_title: str | None = None, password: bool = False) -> List[Any]:
            label_text = f"{label}{' *' if required else ''}"
            input_widget = Input(value=value, password=password, id=f"field-{dest}", classes="field-control-widget")
            self.register_field_help(f"field-{dest}", help_text)
            if path_hint == "path":
                row = Horizontal(
                    Label(label_text, classes="field-label"),
                    Grid(input_widget, Button("...", id=f"browse-{dest}", classes="path-button"), classes="field-path-control"),
                    classes="field-row",
                )
                self.register_field_help(f"browse-{dest}", help_text or browse_title or label)
            else:
                row = Horizontal(Label(label_text, classes="field-label"), Horizontal(input_widget, classes="field-control"), classes="field-row")
            return [row]

        def build_field_widgets(self, field: Dict[str, Any], required: bool = False, context: str = "") -> List[Any]:
            field = normalize_field_for_context(field, context) or field
            dest = str(field.get("dest") or "")
            label = ui_option_name(field) if dest in FEATURE_LABELS else dest.replace("-", " ").strip().title()
            help_text = str(field.get("help") or "").strip()
            kind = str(field.get("kind") or "text")
            value = self.state_values.get(dest)
            path_hint = str(field.get("path_hint") or "")
            if dest == "process-duplicates":
                path_hint = "path"
            if kind == "flag":
                return [self.build_boolean_toggle_row(f"{label}{' *' if required else ''}", dest, bool(value), help_text=help_text)]
            if kind == "bool":
                return [self.build_boolean_toggle_row(f"{label}{' *' if required else ''}", dest, bool(value), help_text=help_text)]
            if kind == "select":
                options = [(str(choice), str(choice)) for choice in (field.get("choices") or [])]
                return [self.build_select_row(f"{label}{' *' if required else ''}", f"field-{dest}", options, value, help_text=help_text)]
            if kind == "list":
                joined = ", ".join(to_list(value))
                return self.build_input_block(label, dest, joined, required, help_text, path_hint=path_hint, browse_title=label)
            return self.build_input_block(label, dest, "" if value is None else str(value), required, help_text, path_hint=path_hint, browse_title=label)

        def build_config_field_widgets(self, section_name: str, field: Dict[str, Any]) -> List[Any]:
            key = str(field.get("key") or "")
            label = key
            help_text = str(field.get("help") or "").strip()
            value = str(self.config_values.get(section_name, {}).get(key, ""))
            label_classes = "field-label field-label--config"
            choices = field.get("choices") or []
            widget_id = f"config-{len(self.config_widget_map)}"
            self.config_widget_map[widget_id] = (section_name, key)
            if choices:
                options = [(str(choice), str(choice)) for choice in choices]
                return [self.build_select_row(label, widget_id, options, value, help_text=help_text, label_classes=label_classes)]
            input_widget = Input(value=value, password=bool(field.get("sensitive")), id=widget_id, classes="field-control-widget")
            self.register_field_help(widget_id, help_text)
            row = Horizontal(Label(label, classes=label_classes), Horizontal(input_widget, classes="field-control"), classes="field-row")
            return [row]

        def refresh_tab_styles(self) -> None:
            for key in self.module_buttons():
                try:
                    button = self.query_one(f"#module-tab-{key}", Button)
                    button.set_class(key == self.active_module, "is-active")
                except Exception:
                    pass
            for key in GENERAL_TAB_NAMES:
                try:
                    button = self.query_one(f"#general-tab-{key}", Button)
                    button.set_class(key == self.active_general_tab, "is-active")
                except Exception:
                    pass

        def can_run_job(self) -> bool:
            return not (self.running_process is not None and self.running_process.poll() is None)

        def module_buttons(self) -> List[str]:
            return list(INTERACTIVE_MODULE_TAB_NAMES.keys())

        def can_stop_job(self) -> bool:
            return self.running_process is not None and self.running_process.poll() is None

        def can_exit_app(self) -> bool:
            return not self.can_stop_job()

        def refresh_action_buttons(self) -> None:
            try:
                run_button = self.query_one("#run-btn", Button)
                can_run = self.can_run_job()
                run_button.disabled = not can_run
                run_button.set_class(can_run, "is-enabled")
                run_button.set_class(not can_run, "is-disabled")
            except Exception:
                pass
            try:
                stop_button = self.query_one("#stop-btn", Button)
                can_stop = self.can_stop_job()
                stop_button.disabled = not can_stop
                stop_button.set_class(can_stop, "is-enabled")
                stop_button.set_class(not can_stop, "is-disabled")
            except Exception:
                pass
            try:
                exit_button = self.query_one("#exit-btn", Button)
                can_exit = self.can_exit_app()
                exit_button.disabled = not can_exit
                exit_button.set_class(can_exit, "is-enabled")
                exit_button.set_class(not can_exit, "is-disabled")
            except Exception:
                pass

        def refresh_boolean_toggle(self, dest: str, value: bool) -> None:
            try:
                off_button = self.query_one(f"#bool-{dest}-off", Button)
                off_button.set_class(not bool(value), "is-active")
            except Exception:
                pass
            try:
                on_button = self.query_one(f"#bool-{dest}-on", Button)
                on_button.set_class(bool(value), "is-active")
            except Exception:
                pass

        def apply_theme(self) -> None:
            for theme in ["ocean", "emerald", "sunset", "dark"]:
                self.set_class(False, f"theme-{theme}")
            self.set_class(True, f"theme-{self.selected_theme}")

        def update_status(self, text: str) -> None:
            self.query_one("#status-line", Static).update(text)

        def update_command_preview(self) -> None:
            if self.active_module == "upload_folder":
                self.query_one("#command-preview", Static).update("Upload to Server is only available in the Web Interface.")
                self.refresh_action_buttons()
                return
            selected_action = None
            if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
                selected_action = self.cloud_action_dest.get(self.active_module)
            elif self.active_module == "standalone_features":
                selected_action = self.standalone_action_dest
            command = build_full_command(self.cli_entrypoint, self.schema, self.active_module, self.state_values, selected_action)
            self.query_one("#command-preview", Static).update(command_to_string(command))
            self.running_command = command
            self.refresh_action_buttons()

        def persist_ui_state(self) -> None:
            if not self.remember_state:
                return
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
                },
            }
            save_json_file(TUI_STATE_PATH, payload)

        def on_unmount(self) -> None:
            self.persist_ui_state()

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            button_id = event.button.id or ""
            if button_id.startswith("bool-"):
                payload = button_id.replace("bool-", "", 1)
                try:
                    dest, mode = payload.rsplit("-", 1)
                except ValueError:
                    dest, mode = "", ""
                if dest and mode in {"on", "off"}:
                    value = mode == "on"
                    if dest == "remember-state":
                        self.remember_state = value
                    else:
                        self.state_values[dest] = value
                    self.refresh_boolean_toggle(dest, value)
                    self.update_command_preview()
                return
            if button_id.startswith("module-tab-"):
                self.active_module = button_id.replace("module-tab-", "", 1)
                self.active_general_tab = "feature"
                self.active_config_section = self.preferred_config_section()
                self.ensure_config_account_selection()
                self.refresh_tab_styles()
                await self.rebuild_content()
                self.update_command_preview()
                return
            if button_id.startswith("general-tab-"):
                self.active_general_tab = button_id.replace("general-tab-", "", 1)
                if self.active_general_tab == "features_config":
                    self.reload_config_model()
                self.refresh_tab_styles()
                await self.rebuild_content()
                self.update_command_preview()
                return
            if button_id.startswith("browse-"):
                dest = button_id.replace("browse-", "", 1)
                current_value = ""
                if dest.startswith("config-"):
                    current_value = ""
                else:
                    raw_value = self.state_values.get(dest)
                    if isinstance(raw_value, list):
                        current_value = ", ".join(raw_value)
                    else:
                        current_value = str(raw_value or "")
                self.push_screen(
                    PathPickerScreen(
                        dest=dest,
                        title=f"Select path for {dest}",
                        start_path=current_value,
                        home_path=self.launch_cwd,
                    ),
                    callback=self.handle_path_picker_result,
                )
                return
            if button_id == "run-btn":
                self.action_run_job()
                return
            if button_id == "stop-btn":
                self.action_stop_job()
                return
            if button_id == "exit-btn":
                self.request_exit()
                return
            if button_id == "save-config-btn":
                self.action_save_config()
                return
            if button_id == "reload-config-btn":
                self.action_reload_config()
                if self.active_general_tab == "features_config":
                    await self.rebuild_content()
                return
            if button_id == "save-ui-state-btn":
                self.persist_ui_state()
                self.update_status(f"UI state saved to {TUI_STATE_PATH}")
                return
            if button_id == "send-input-btn":
                self.action_send_job_input()
                return

        def handle_path_picker_result(self, result: Dict[str, str] | None) -> None:
            if not result:
                return
            dest = str(result.get("dest") or "")
            path = str(result.get("path") or "")
            if not dest:
                return
            if dest == "find-duplicates-folders":
                self.state_values[dest] = [path]
            else:
                self.state_values[dest] = path
            try:
                widget = self.query_one(f"#field-{dest}", Input)
                widget.value = path
            except Exception:
                pass
            self.update_command_preview()

        async def on_input_changed(self, event: Input.Changed) -> None:
            widget_id = event.input.id or ""
            if widget_id == "job-input":
                return
            if widget_id.startswith("field-"):
                dest = widget_id.replace("field-", "", 1)
                field = get_field_by_dest(self.schema, dest)
                if dest in {"source", "target"}:
                    state = self.migration_endpoint_state(dest)
                    state["path"] = event.value
                    self.state_values[dest] = compose_migration_endpoint(state)
                    self.update_command_preview()
                    return
                if dest == "rename-pattern" or dest == "replacement-pattern":
                    self.state_values[dest] = event.value
                elif dest == "find-duplicates-folders":
                    self.state_values[dest] = parse_folder_list_value(event.value)
                elif field and field.get("kind") == "list":
                    self.state_values[dest] = to_list(event.value)
                else:
                    self.state_values[dest] = event.value
                self.update_command_preview()
                return
            if widget_id.startswith("config-"):
                mapped = self.config_widget_map.get(widget_id)
                if mapped:
                    section_name, key = mapped
                    self.config_values.setdefault(section_name, {})[key] = event.value

        async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
            widget_id = event.checkbox.id or ""
            if widget_id.startswith("field-"):
                dest = widget_id.replace("field-", "", 1)
                self.state_values[dest] = bool(event.value)
                self.update_command_preview()
                return

        async def on_select_changed(self, event: Select.Changed) -> None:
            widget_id = event.select.id or ""
            value = "" if event.value is None else str(event.value)
            if widget_id == "cloud-action-select":
                if value == str(self.cloud_action_dest.get(self.active_module) or ""):
                    return
                self.cloud_action_dest[self.active_module] = value
                await self.rebuild_content()
                self.update_command_preview()
                return
            if widget_id == "standalone-action-select":
                if value == self.standalone_action_dest:
                    return
                self.standalone_action_dest = value
                await self.rebuild_content()
                self.update_command_preview()
                return
            if widget_id == "find-duplicates-action-select":
                if value == str(self.state_values.get("find-duplicates-action") or ""):
                    return
                self.state_values["find-duplicates-action"] = value
                self.update_command_preview()
                return
            if widget_id == "config-section-select":
                if value == self.active_config_section:
                    return
                self.active_config_section = value
                self.ensure_config_account_selection()
                await self.rebuild_content()
                return
            if widget_id == "config-account-select":
                if value == str(self.active_config_account.get(self.active_config_section) or ""):
                    return
                self.active_config_account[self.active_config_section] = value
                await self.rebuild_content()
                return
            if widget_id == "theme-select":
                if value == self.selected_theme:
                    return
                self.selected_theme = value if value else "ocean"
                self.apply_theme()
                self.persist_ui_state()
                return
            if widget_id.startswith("migration-kind-"):
                dest = widget_id.replace("migration-kind-", "", 1)
                state = self.migration_endpoint_state(dest)
                if value == state.get("kind"):
                    return
                state["kind"] = value or self.migration_default_kind(dest)
                self.migration_endpoints_state[dest] = state
                self.state_values[dest] = compose_migration_endpoint(state)
                await self.rebuild_content()
                self.update_command_preview()
                return
            if widget_id.startswith("migration-account-"):
                dest = widget_id.replace("migration-account-", "", 1)
                state = self.migration_endpoint_state(dest)
                if value == state.get("account"):
                    return
                state["account"] = value or "1"
                self.migration_endpoints_state[dest] = state
                self.state_values[dest] = compose_migration_endpoint(state)
                self.update_command_preview()
                return
            if widget_id.startswith("field-"):
                if value == str(self.state_values.get(widget_id.replace("field-", "", 1)) or ""):
                    return
                dest = widget_id.replace("field-", "", 1)
                self.state_values[dest] = value
                self.update_command_preview()
                return
            if widget_id.startswith("config-"):
                mapped = self.config_widget_map.get(widget_id)
                if mapped:
                    section_name, key = mapped
                    self.config_values.setdefault(section_name, {})[key] = value

        def append_log(self, line: str) -> None:
            self.query_one("#log-panel", RichLog).write(line)

        def on_job_finished(self, return_code: int) -> None:
            self.update_status(f"Job finished with exit code {return_code}")
            self.running_process = None
            self.refresh_action_buttons()

        def _job_output_worker(self, process: subprocess.Popen[str]) -> None:
            try:
                if process.stdout is not None:
                    for raw_line in process.stdout:
                        self.call_from_thread(self.append_log, raw_line.rstrip("\n"))
                return_code = process.wait()
            except Exception as exc:
                self.call_from_thread(self.append_log, f"[internal] {exc}")
                return_code = -1
            self.call_from_thread(self.on_job_finished, return_code)

        def action_run_job(self) -> None:
            if self.active_module == "upload_folder":
                self.update_status("Upload to Server is only available in the Web Interface.")
                return
            if self.running_process is not None and self.running_process.poll() is None:
                self.update_status("A job is already running.")
                return
            selected_action = None
            if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
                selected_action = self.cloud_action_dest.get(self.active_module)
            elif self.active_module == "standalone_features":
                selected_action = self.standalone_action_dest
            command = build_full_command(self.cli_entrypoint, self.schema, self.active_module, self.state_values, selected_action)
            self.running_command = command
            log = self.query_one("#log-panel", RichLog)
            log.clear()
            self.append_log(f"> {command_to_string(command)}")
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(self.project_root),
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

        def request_exit(self) -> None:
            if not self.can_exit_app():
                self.update_status("Stop the running job before exiting.")
                self.refresh_action_buttons()
                return
            self.push_screen(ConfirmExitScreen(), callback=self.handle_exit_confirmation)

        def handle_exit_confirmation(self, confirmed: bool) -> None:
            if not confirmed:
                self.update_status("Exit canceled.")
                return
            self.persist_ui_state()
            self.exit()

        def action_quit(self) -> None:
            self.request_exit()

        def action_send_job_input(self) -> None:
            if self.running_process is None or self.running_process.stdin is None or self.running_process.poll() is not None:
                self.update_status("No running job is accepting input.")
                return
            input_widget = self.query_one("#job-input", Input)
            text = str(input_widget.value or "").rstrip("\r\n")
            if not text:
                self.update_status("Input is empty.")
                return
            try:
                self.running_process.stdin.write(text + "\n")
                self.running_process.stdin.flush()
                self.append_log(f">>> {text}")
                input_widget.value = ""
                self.update_status("Input sent to job.")
            except Exception as exc:
                self.update_status(f"Unable to send input: {exc}")

        def action_save_config(self) -> None:
            save_config_editor_values(self.current_config_path(), self.config_values, self.config_template_text, self.config_schema)
            self.update_status(f"Config.ini saved to {self.current_config_path()}")

        def action_reload_config(self) -> None:
            self.reload_config_model()
            self.update_status(f"Config.ini reloaded from {self.current_config_path()}")


    def run_cli_tui(project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None) -> None:
        app = PhotoMigratorTUI(project_root=project_root, cli_entrypoint=cli_entrypoint, initial_values=initial_values)
        app.run()
else:
    def run_cli_tui(project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None) -> None:  # pragma: no cover - only used without textual
        raise RuntimeError(str(TEXTUAL_IMPORT_ERROR or "Textual is not installed"))
