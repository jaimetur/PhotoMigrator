from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from Core.GlobalVariables import TOOL_VERSION

from UI.ui_shared import (
    CLOUD_ACTIONS_AVAILABLE_BY_TAB,
    CompactLogBuffer,
    CONFIG_EDITOR_SECTIONS_ORDER,
    FEATURE_LABELS,
    GENERAL_GROUPS,
    GENERAL_TAB_NAMES,
    MODULE_TAB_NAMES,
    TIMEZONE_CHOICES,
    build_automatic_migration_filter_fields,
    build_ui_subprocess_env,
    build_argument_specs,
    build_full_command,
    command_preview_string,
    build_parser_schema,
    command_to_string,
    compose_migration_endpoint,
    config_section_account_selector,
    default_state_values,
    effective_interactive_field_value,
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
    resolve_ui_config_path,
    to_list,
    ui_option_name,
    validate_ui_config_file,
)

TEXTUAL_IMPORT_ERROR: Exception | None = None
TEXTUAL_AVAILABLE = False

try:
    from rich.text import Text
    from textual import events
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import Button, Checkbox, DirectoryTree, Header, Input, Label, RichLog, Select, Static

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
LOG_LEVEL_PREFIX_RE = re.compile(r"^(VERBOSE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*:\s*")
FOCUS_PANEL_IDS = (
    "sidebar-features",
    "general-tabs",
    "content-body",
    "job-input-panel",
)


def preferred_tui_panel_widget_ids(panel_id: str, active_general_tab: str = "", active_module: str = "") -> List[str]:
    preferred: List[str] = []

    def push(widget_id: str) -> None:
        value = str(widget_id or "").strip()
        if value and value not in preferred:
            preferred.append(value)

    if panel_id == "sidebar-features":
        if str(active_module or "").strip():
            push(f"module-tab-{active_module}")
        for widget_id in ["module-tab-automatic_migration", "run-btn", "stop-btn", "exit-btn"]:
            push(widget_id)
        return preferred
    if panel_id == "general-tabs":
        if str(active_general_tab or "").strip():
            push(f"general-tab-{active_general_tab}")
        for widget_id in ["general-tab-feature", "load-config-btn"]:
            push(widget_id)
        return preferred
    return []


def textual_runtime_available() -> tuple[bool, str | None]:
    if TEXTUAL_AVAILABLE:
        return True, None
    return False, str(TEXTUAL_IMPORT_ERROR or "Textual is not installed")


if TEXTUAL_AVAILABLE:
    class NavigableInput(Input):
        def on_key(self, event: events.Key) -> None:
            app = getattr(self, "app", None)
            if event.key == "tab":
                next_panel = getattr(app, "action_focus_next_panel", None)
                if callable(next_panel):
                    next_panel()
                    event.stop()
                    return
            if event.key in {"shift+tab", "backtab"}:
                previous_panel = getattr(app, "action_focus_previous_panel", None)
                if callable(previous_panel):
                    previous_panel()
                    event.stop()
                    return
            if event.key == "up":
                move_up = getattr(app, "action_move_up", None)
                if callable(move_up):
                    move_up()
                    event.stop()
                    return
            if event.key == "down":
                move_down = getattr(app, "action_move_down", None)
                if callable(move_down):
                    move_down()
                    event.stop()
                    return
            if event.key == "left":
                move_left = getattr(app, "action_move_left", None)
                if callable(move_left):
                    move_left()
                    event.stop()
                    return
            if event.key == "right":
                move_right = getattr(app, "action_move_right", None)
                if callable(move_right):
                    move_right()
                    event.stop()
                    return
            if event.key == "enter" and str(getattr(self, "id", "") or "") == "job-input":
                send_input = getattr(app, "action_send_job_input", None)
                if callable(send_input):
                    send_input()
                    event.stop()
                    return
            if event.key in {"escape", "enter"}:
                exit_widget = getattr(app, "_exit_focused_widget", None)
                if callable(exit_widget) and exit_widget():
                    event.stop()
                    return


    class NavigableSelect(Select):
        def _is_open(self) -> bool:
            for attr in ("expanded", "overlay_visible", "menu_open", "is_expanded"):
                try:
                    if bool(getattr(self, attr)):
                        return True
                except Exception:
                    continue
            return False

        def _call_first(self, method_names: List[str]) -> bool:
            for method_name in method_names:
                method = getattr(self, method_name, None)
                if callable(method):
                    try:
                        method()
                        return True
                    except Exception:
                        continue
            return False

        def on_key(self, event: events.Key) -> None:
            app = getattr(self, "app", None)
            if not self._is_open():
                if event.key == "tab":
                    next_panel = getattr(app, "action_focus_next_panel", None)
                    if callable(next_panel):
                        next_panel()
                        event.stop()
                        return
                if event.key in {"shift+tab", "backtab"}:
                    previous_panel = getattr(app, "action_focus_previous_panel", None)
                    if callable(previous_panel):
                        previous_panel()
                        event.stop()
                        return
                if event.key == "up":
                    move_up = getattr(app, "action_move_up", None)
                    if callable(move_up):
                        move_up()
                        event.stop()
                        return
                if event.key == "down":
                    move_down = getattr(app, "action_move_down", None)
                    if callable(move_down):
                        move_down()
                        event.stop()
                        return
                if event.key == "left":
                    move_left = getattr(app, "action_move_left", None)
                    if callable(move_left):
                        move_left()
                        event.stop()
                        return
                if event.key == "right":
                    move_right = getattr(app, "action_move_right", None)
                    if callable(move_right):
                        move_right()
                        event.stop()
                        return
                if event.key == "enter":
                    if self._call_first(["action_show_overlay", "action_toggle_overlay", "action_expand", "action_open"]):
                        event.stop()
                        return
                if event.key in {"escape", "backspace", "delete"}:
                    exit_widget = getattr(app, "_exit_focused_widget", None)
                    if callable(exit_widget) and exit_widget():
                        event.stop()
                        return
            else:
                if event.key in {"escape", "backspace", "delete"}:
                    if self._call_first(["action_dismiss", "action_hide_overlay", "action_collapse", "action_close"]):
                        event.stop()
                        return


    class PathPickerScreen(ModalScreen[Dict[str, str] | None]):
        BINDINGS = [
            Binding("escape", "cancel", "Cancel", priority=True),
            Binding("tab", "focus_next_widget", "Next", priority=True),
            Binding("shift+tab", "focus_previous_widget", "Previous", priority=True),
            Binding("backtab", "focus_previous_widget", "Previous", priority=True),
            Binding("left", "focus_previous_widget", "Previous", priority=True),
            Binding("right", "focus_next_widget", "Next", priority=True),
            Binding("ctrl+v", "paste_text", "Paste", priority=True),
        ]

        def __init__(self, dest: str, title: str, start_path: str = "", home_path: Path | None = None, subtitle: str | None = None):
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
            self.subtitle = subtitle or "Select a file or folder and press Enter."

        def compose(self) -> ComposeResult:
            root_value = str(self.initial_path.resolve())
            yield Vertical(
                Static(self.title, classes="modal-title"),
                Static(self.subtitle, classes="modal-subtitle"),
                Input(value=root_value, id="picker-path-input"),
                Horizontal(
                    Button("↑ Up", id="picker-up"),
                    Button("⌂ Home", id="picker-home"),
                    id="picker-nav-actions",
                ),
                DirectoryTree(root_value, id="picker-tree"),
                Horizontal(
                    Button("Cancel", id="picker-cancel", classes="modal-btn modal-btn-cancel"),
                    Button("Select", id="picker-select", variant="primary", classes="modal-btn modal-btn-primary"),
                    id="picker-actions",
                ),
                id="picker-dialog",
            )

        def _refresh_modal_button_focus(self) -> None:
            try:
                focused = self.focused
            except Exception:
                focused = None
            try:
                for button in self.query("Button"):
                    button.set_class(button is focused, "is-focused")
            except Exception:
                pass

        def _focusable_widgets(self) -> List[Any]:
            widgets: List[Any] = []
            for widget_id in (
                "picker-path-input",
                "picker-up",
                "picker-home",
                "picker-tree",
                "picker-cancel",
                "picker-select",
            ):
                try:
                    widget = self.query_one(f"#{widget_id}")
                except Exception:
                    continue
                if bool(getattr(widget, "can_focus", False)):
                    widgets.append(widget)
            return widgets

        def _focus_widget_by_delta(self, delta: int) -> None:
            widgets = self._focusable_widgets()
            if not widgets:
                return
            try:
                focused = self.focused
            except Exception:
                focused = None
            try:
                current_index = widgets.index(focused) if focused in widgets else 0
            except ValueError:
                current_index = 0
            next_index = (current_index + delta) % len(widgets)
            try:
                self.set_focus(widgets[next_index])
            except Exception:
                return
            self._refresh_modal_button_focus()

        def action_cancel(self) -> None:
            self.dismiss(None)

        def action_confirm(self) -> None:
            selected = self._selected_path()
            self.dismiss({"dest": self.dest, "path": selected})

        def on_mount(self) -> None:
            try:
                self.set_focus(self.query_one("#picker-path-input", Input))
            except Exception:
                pass
            self._refresh_modal_button_focus()

        def action_focus_next_widget(self) -> None:
            self._focus_widget_by_delta(1)

        def action_focus_previous_widget(self) -> None:
            self._focus_widget_by_delta(-1)

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

        def _read_system_clipboard(self) -> str:
            commands: List[List[str]] = []
            if sys.platform == "darwin" and shutil.which("pbpaste"):
                commands.append(["pbpaste"])
            elif sys.platform.startswith("win"):
                if shutil.which("powershell"):
                    commands.append(["powershell", "-NoProfile", "-Command", "Get-Clipboard"])
                if shutil.which("pwsh"):
                    commands.append(["pwsh", "-NoProfile", "-Command", "Get-Clipboard"])
            else:
                if shutil.which("wl-paste"):
                    commands.append(["wl-paste", "-n"])
                if shutil.which("xclip"):
                    commands.append(["xclip", "-selection", "clipboard", "-o"])
                if shutil.which("xsel"):
                    commands.append(["xsel", "--clipboard", "--output"])
            for command in commands:
                try:
                    result = subprocess.run(command, capture_output=True, text=True, check=True)
                    text = str(result.stdout or "")
                    if text:
                        return text
                except Exception:
                    continue
            return ""

        def action_paste_text(self) -> None:
            text = self._read_system_clipboard()
            if not text:
                return
            try:
                input_widget = self.query_one("#picker-path-input", Input)
                input_widget.value = text.strip()
                input_widget.focus()
            except Exception:
                pass

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

        def on_descendant_focus(self, event: events.DescendantFocus) -> None:
            self._refresh_modal_button_focus()

        def on_descendant_blur(self, event: events.DescendantBlur) -> None:
            self._refresh_modal_button_focus()

        async def on_key(self, event: events.Key) -> None:
            if event.key == "enter":
                focused = self.focused
                if isinstance(focused, Button):
                    try:
                        focused.press()
                    except Exception:
                        pass
                    event.stop()
                    return
                if isinstance(focused, Input):
                    return
                self.action_confirm()
                event.stop()
                return
            if event.key == "tab":
                self.action_focus_next_widget()
                event.stop()
                return
            if event.key in {"shift+tab", "backtab"}:
                self.action_focus_previous_widget()
                event.stop()
                return
            if event.key == "left":
                focused = self.focused
                if isinstance(focused, Button):
                    self.action_focus_previous_widget()
                    event.stop()
                    return
            if event.key == "right":
                focused = self.focused
                if isinstance(focused, Button):
                    self.action_focus_next_widget()
                    event.stop()
                    return

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "picker-cancel":
                self.dismiss(None)
            elif event.button.id == "picker-select":
                self.action_confirm()
            elif event.button.id == "picker-up":
                self.action_go_up()
            elif event.button.id == "picker-home":
                self.action_go_home()


    class ConfirmActionScreen(ModalScreen[bool]):
        BINDINGS = [
            Binding("escape", "cancel", "Cancel", priority=True),
            Binding("tab", "focus_next_button", "Next", priority=True),
            Binding("shift+tab", "focus_previous_button", "Previous", priority=True),
            Binding("backtab", "focus_previous_button", "Previous", priority=True),
            Binding("left", "focus_previous_button", "Previous", priority=True),
            Binding("right", "focus_next_button", "Next", priority=True),
        ]

        def __init__(self, title: str, message: str, confirm_label: str = "Confirm", cancel_label: str = "Cancel"):
            super().__init__()
            self.title = title
            self.message = message
            self.confirm_label = confirm_label
            self.cancel_label = cancel_label

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static(self.title, classes="modal-title"),
                Static(self.message, classes="modal-subtitle"),
                Horizontal(
                    Button(self.cancel_label, id="confirm-cancel", classes="modal-btn modal-btn-cancel"),
                    Button(self.confirm_label, id="confirm-accept", variant="primary", classes="modal-btn modal-btn-primary"),
                    id="picker-actions",
                ),
                id="picker-dialog",
            )

        def on_mount(self) -> None:
            self.set_focus(self.query_one("#confirm-accept", Button))
            self._refresh_modal_button_focus()

        def action_cancel(self) -> None:
            self.dismiss(False)

        def action_confirm(self) -> None:
            self.dismiss(True)

        def _focus_button_by_delta(self, delta: int) -> None:
            buttons = list(self.query("#picker-actions Button"))
            if not buttons:
                return
            try:
                focused = self.focused
            except Exception:
                focused = None
            try:
                current_index = buttons.index(focused) if focused in buttons else 0
            except ValueError:
                current_index = 0
            next_index = (current_index + delta) % len(buttons)
            self.set_focus(buttons[next_index])
            self._refresh_modal_button_focus()

        def _refresh_modal_button_focus(self) -> None:
            try:
                focused = self.focused
            except Exception:
                focused = None
            try:
                for button in self.query("#picker-actions Button"):
                    button.set_class(button is focused, "is-focused")
            except Exception:
                pass

        def action_focus_previous_button(self) -> None:
            self._focus_button_by_delta(-1)

        def action_focus_next_button(self) -> None:
            self._focus_button_by_delta(1)

        def on_descendant_focus(self, event: events.DescendantFocus) -> None:
            self._refresh_modal_button_focus()

        def on_descendant_blur(self, event: events.DescendantBlur) -> None:
            self._refresh_modal_button_focus()

        async def on_key(self, event: events.Key) -> None:
            if event.key == "enter":
                try:
                    focused = self.focused
                except Exception:
                    focused = None
                if isinstance(focused, Button):
                    try:
                        focused.press()
                    except Exception:
                        pass
                else:
                    self.action_confirm()
                event.stop()
                return
            if event.key == "tab":
                self.action_focus_next_button()
                event.stop()
                return
            if event.key in {"shift+tab", "backtab"}:
                self.action_focus_previous_button()
                event.stop()
                return

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "confirm-cancel":
                self.dismiss(False)
            elif event.button.id == "confirm-accept":
                self.dismiss(True)


    class InfoMessageScreen(ModalScreen[None]):
        BINDINGS = [
            Binding("escape", "close", "Close", priority=True),
            Binding("tab", "focus_ok", "OK", priority=True),
            Binding("shift+tab", "focus_ok", "OK", priority=True),
            Binding("backtab", "focus_ok", "OK", priority=True),
            Binding("left", "focus_ok", "OK", priority=True),
            Binding("right", "focus_ok", "OK", priority=True),
        ]

        def __init__(self, title: str, message: str, ok_label: str = "OK"):
            super().__init__()
            self.title = title
            self.message = message
            self.ok_label = ok_label

        def compose(self) -> ComposeResult:
            yield Vertical(
                Static(self.title, classes="modal-title"),
                Static(self.message, classes="modal-subtitle"),
                Horizontal(
                    Button(self.ok_label, id="info-ok", variant="primary", classes="modal-btn modal-btn-primary"),
                    id="picker-actions",
                ),
                id="picker-dialog",
            )

        def on_mount(self) -> None:
            try:
                self.set_focus(self.query_one("#info-ok", Button))
            except Exception:
                pass
            self._refresh_modal_button_focus()

        def _refresh_modal_button_focus(self) -> None:
            try:
                focused = self.focused
            except Exception:
                focused = None
            try:
                button = self.query_one("#info-ok", Button)
                button.set_class(button is focused, "is-focused")
            except Exception:
                pass

        def action_focus_ok(self) -> None:
            try:
                self.set_focus(self.query_one("#info-ok", Button))
            except Exception:
                return
            self._refresh_modal_button_focus()

        def action_close(self) -> None:
            self.dismiss(None)

        def on_descendant_focus(self, event: events.DescendantFocus) -> None:
            self._refresh_modal_button_focus()

        def on_descendant_blur(self, event: events.DescendantBlur) -> None:
            self._refresh_modal_button_focus()

        async def on_key(self, event: events.Key) -> None:
            if event.key == "enter":
                try:
                    button = self.query_one("#info-ok", Button)
                    button.press()
                except Exception:
                    self.action_close()
                event.stop()
                return

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "info-ok":
                self.dismiss(None)


    class ExecutionLogView(RichLog):
        ALLOW_SELECT = False
        FOCUS_ON_CLICK = True
        can_focus = True

        def __init__(self, *args: Any, auto_scroll: bool = True, **kwargs: Any) -> None:
            super().__init__(*args, auto_scroll=auto_scroll, wrap=False, **kwargs)
            self.auto_scroll = auto_scroll
            self._lines: List[Text] = []
            self._manual_selection_start: tuple[int, int] | None = None
            self._manual_selection_end: tuple[int, int] | None = None
            self._manual_selection_active = False

        @property
        def allow_select(self) -> bool:
            return False

        def _as_text(self, renderable: Any) -> Text:
            if isinstance(renderable, Text):
                try:
                    text = renderable.copy()
                    text.no_wrap = True
                    text.overflow = "ignore"
                    return text
                except Exception:
                    text = Text(str(renderable))
                    text.no_wrap = True
                    text.overflow = "ignore"
                    return text
            raw = str(renderable or "").replace("\ufe0f", "")
            try:
                text = Text.from_ansi(raw)
            except Exception:
                text = Text(raw)
            text.no_wrap = True
            text.overflow = "ignore"
            return text

        def _line_plain(self, index: int) -> str:
            if index < 0 or index >= len(self._lines):
                return ""
            try:
                return str(self._lines[index].plain or "")
            except Exception:
                return str(self._lines[index] or "")

        def _selection_coord(self, point: Any) -> tuple[int, int]:
            if point is None:
                return 0, 0
            x = getattr(point, "x", None)
            y = getattr(point, "y", None)
            if x is None:
                x = getattr(point, "column", None)
            if x is None:
                x = getattr(point, "col", None)
            if y is None:
                y = getattr(point, "row", None)
            if y is None:
                y = getattr(point, "line", None)
            return max(0, int(x or 0)), max(0, int(y or 0))

        def _selected_text_from_selection(self, selection: Any) -> str:
            manual_text = self.get_manual_selection_text()
            if manual_text:
                return manual_text
            start_point = getattr(selection, "start", None) or getattr(selection, "anchor", None)
            end_point = getattr(selection, "end", None) or getattr(selection, "cursor", None)
            if start_point is None or end_point is None:
                return ""
            start_x, start_y = self._selection_coord(start_point)
            end_x, end_y = self._selection_coord(end_point)
            if (end_y, end_x) < (start_y, start_x):
                start_x, end_x = end_x, start_x
                start_y, end_y = end_y, start_y
            if not self._lines:
                return ""
            start_y = max(0, min(start_y, len(self._lines) - 1))
            end_y = max(0, min(end_y, len(self._lines) - 1))
            selected_lines: List[str] = []
            for row in range(start_y, end_y + 1):
                line = self._line_plain(row)
                if row == start_y == end_y:
                    selected_lines.append(line[start_x:end_x])
                elif row == start_y:
                    selected_lines.append(line[start_x:])
                elif row == end_y:
                    selected_lines.append(line[:end_x])
                else:
                    selected_lines.append(line)
            return "\n".join(selected_lines)

        def get_selection(self, selection: Any) -> tuple[str, str] | None:
            selected_text = self._selected_text_from_selection(selection)
            return (selected_text, "") if selected_text else None

        def get_selection_text(self, selection: Any) -> str | None:
            selected_text = self._selected_text_from_selection(selection)
            return selected_text or None

        def _manual_selection_bounds(self) -> tuple[tuple[int, int], tuple[int, int]] | None:
            start = self._manual_selection_start
            end = self._manual_selection_end
            if start is None or end is None:
                return None
            if end < start:
                start, end = end, start
            return start, end

        def get_manual_selection_text(self) -> str:
            bounds = self._manual_selection_bounds()
            if bounds is None or not self._lines:
                return ""
            (start_x, start_y), (end_x, end_y) = bounds
            start_y = max(0, min(start_y, len(self._lines) - 1))
            end_y = max(0, min(end_y, len(self._lines) - 1))
            selected_lines: List[str] = []
            for row in range(start_y, end_y + 1):
                line = self._line_plain(row)
                if row == start_y == end_y:
                    selected_lines.append(line[start_x:end_x])
                elif row == start_y:
                    selected_lines.append(line[start_x:])
                elif row == end_y:
                    selected_lines.append(line[:end_x])
                else:
                    selected_lines.append(line)
            return "\n".join(selected_lines)

        def _event_content_coord(self, event: Any) -> tuple[int, int]:
            local_x = int(getattr(event, "x", 0) or 0)
            local_y = int(getattr(event, "y", 0) or 0)
            scroll_x = int(float(getattr(self, "scroll_x", 0) or 0))
            scroll_y = int(float(getattr(self, "scroll_y", 0) or 0))
            return max(0, local_x + scroll_x), max(0, local_y + scroll_y)

        def _style_line_for_selection(self, text: Text, row_index: int) -> Text:
            styled = text.copy()
            bounds = self._manual_selection_bounds()
            if bounds is None:
                return styled
            (start_x, start_y), (end_x, end_y) = bounds
            if row_index < start_y or row_index > end_y:
                return styled
            line_length = len(styled.plain)
            if line_length <= 0:
                return styled
            if start_y == end_y:
                sel_start = max(0, min(start_x, line_length))
                sel_end = max(0, min(end_x, line_length))
            elif row_index == start_y:
                sel_start = max(0, min(start_x, line_length))
                sel_end = line_length
            elif row_index == end_y:
                sel_start = 0
                sel_end = max(0, min(end_x, line_length))
            else:
                sel_start = 0
                sel_end = line_length
            if sel_end > sel_start:
                styled.stylize("reverse", sel_start, sel_end)
            return styled

        def _line_render_width(self, text: Text) -> int:
            try:
                return max(1, len(text.plain or ""))
            except Exception:
                return max(1, len(str(text or "")))

        def _sync_horizontal_extent(self) -> None:
            try:
                widest_line = max((self._line_render_width(line) for line in self._lines), default=1)
                self.min_width = max(1, int(widest_line))
            except Exception:
                pass
            try:
                self.refresh(layout=True)
            except Exception:
                pass

        def _redraw_lines(self, *, scroll_end: bool | None = None) -> None:
            self._sync_horizontal_extent()
            try:
                super().clear()
            except Exception:
                pass
            last_index = len(self._lines) - 1
            for index, line in enumerate(self._lines):
                styled_line = self._style_line_for_selection(line, index)
                try:
                    super().write(
                        styled_line,
                        width=self._line_render_width(styled_line),
                        shrink=False,
                        scroll_end=(self.auto_scroll if scroll_end is None else bool(scroll_end)) and index == last_index,
                    )
                except TypeError:
                    super().write(styled_line, width=self._line_render_width(styled_line), shrink=False)
            self._scroll_to_end_if_needed(scroll_end)

        def clear_manual_selection(self) -> None:
            if self._manual_selection_start is None and self._manual_selection_end is None:
                return
            self._manual_selection_start = None
            self._manual_selection_end = None
            self._manual_selection_active = False
            self._redraw_lines(scroll_end=False)

        def _scroll_to_end_if_needed(self, scroll_end: bool | None) -> None:
            if scroll_end is False or not self.auto_scroll:
                return
            try:
                scroll_end_fn = getattr(self, "scroll_end", None)
                if callable(scroll_end_fn):
                    self.call_after_refresh(lambda: scroll_end_fn(animate=False, immediate=True))
                    return
            except Exception:
                pass
            try:
                def _scroll() -> None:
                    max_y = float(getattr(self, "max_scroll_y", 0) or 0)
                    scroll_to = getattr(self, "scroll_to", None)
                    if callable(scroll_to):
                        scroll_to(x=None, y=max_y, animate=False, immediate=True, force=True)
                self.call_after_refresh(_scroll)
            except Exception:
                pass

        def clear(self) -> None:
            self._lines = []
            self._manual_selection_start = None
            self._manual_selection_end = None
            self._manual_selection_active = False
            try:
                super().clear()
            except Exception:
                pass

        def write(self, renderable: Any, *, scroll_end: bool | None = None) -> None:
            text = self._as_text(renderable)
            self._lines.append(text)
            self._sync_horizontal_extent()
            styled_line = self._style_line_for_selection(text, len(self._lines) - 1)
            try:
                super().write(
                    styled_line,
                    width=self._line_render_width(styled_line),
                    shrink=False,
                    scroll_end=self.auto_scroll if scroll_end is None else bool(scroll_end),
                )
            except TypeError:
                super().write(styled_line, width=self._line_render_width(styled_line), shrink=False)
                self._scroll_to_end_if_needed(scroll_end)

        def set_lines(self, lines: List[Any], *, scroll_end: bool | None = None) -> None:
            self._lines = [self._as_text(line) for line in lines]
            self._redraw_lines(scroll_end=scroll_end)

        def on_mouse_down(self, event: events.MouseDown) -> None:
            if int(getattr(event, "button", 0) or 0) == 1:
                try:
                    self.focus()
                except Exception:
                    pass
                self._manual_selection_start = self._event_content_coord(event)
                self._manual_selection_end = self._manual_selection_start
                self._manual_selection_active = True
                try:
                    self.capture_mouse(True)
                except Exception:
                    pass
                self._redraw_lines(scroll_end=False)
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass
                return
            try:
                super().on_mouse_down(event)
            except Exception:
                pass

        def on_mouse_move(self, event: events.MouseMove) -> None:
            if not self._manual_selection_active:
                return
            next_coord = self._event_content_coord(event)
            if next_coord == self._manual_selection_end:
                return
            self._manual_selection_end = next_coord
            self._redraw_lines(scroll_end=False)
            event.stop()
            try:
                event.prevent_default()
            except Exception:
                pass

        def on_mouse_up(self, event: events.MouseUp) -> None:
            if not self._manual_selection_active or int(getattr(event, "button", 0) or 0) != 1:
                return
            self._manual_selection_end = self._event_content_coord(event)
            self._manual_selection_active = False
            try:
                self.capture_mouse(False)
            except Exception:
                try:
                    self.release_mouse()
                except Exception:
                    pass
            self._redraw_lines(scroll_end=False)
            event.stop()
            try:
                event.prevent_default()
            except Exception:
                pass

        def _scroll_horizontally(self, delta: int) -> bool:
            try:
                max_scroll_x = float(getattr(self, "max_scroll_x", 0) or 0)
            except Exception:
                max_scroll_x = 0
            if max_scroll_x <= 0:
                try:
                    visible_width = int(getattr(getattr(self, "size", None), "width", 0) or 0)
                    content_width = max((len(self._line_plain(index)) for index in range(len(self._lines))), default=0)
                    if visible_width > 0 and content_width > visible_width:
                        max_scroll_x = float(content_width - visible_width)
                except Exception:
                    max_scroll_x = 0
            if max_scroll_x <= 0:
                return False
            try:
                if delta > 0:
                    scroll_right = getattr(self, "scroll_right", None)
                    if callable(scroll_right):
                        for _ in range(abs(int(delta))):
                            scroll_right(animate=False)
                        return True
                elif delta < 0:
                    scroll_left = getattr(self, "scroll_left", None)
                    if callable(scroll_left):
                        for _ in range(abs(int(delta))):
                            scroll_left(animate=False)
                        return True
            except Exception:
                pass
            try:
                scroll_relative = getattr(self, "scroll_relative", None)
                if callable(scroll_relative):
                    scroll_relative(x=delta, animate=False, immediate=True, force=True)
                    return True
            except Exception:
                pass
            try:
                current_x = float(getattr(self, "scroll_x", 0) or 0)
                scroll_to = getattr(self, "scroll_to", None)
                if callable(scroll_to):
                    next_x = max(0, min(max_scroll_x, current_x + delta))
                    scroll_to(x=next_x, y=None, animate=False, immediate=True, force=True)
                    return True
            except Exception:
                pass
            return False

        def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
            if getattr(event, "shift", False) and self._scroll_horizontally(4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
            if getattr(event, "shift", False) and self._scroll_horizontally(-4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_left(self, event: events.MouseScrollLeft) -> None:
            if self._scroll_horizontally(-4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_right(self, event: events.MouseScrollRight) -> None:
            if self._scroll_horizontally(4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass


    class PhotoMigratorTUI(App[None]):
        TITLE = f"PhotoMigrator {TOOL_VERSION} - Terminal Interactive User Interface (TUI)"
        ALLOW_SELECT = True
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
            color: #d6dfeb;
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
        .module-tab:focus {
            border: round #495c73;
            text-style: bold;
        }
        .module-tab.is-active {
            border: heavy #d7a35a;
            text-style: bold;
        }
        .module-tab.is-active:focus {
            border: heavy #f0c88b;
            text-style: bold;
        }
        .module-tab--migration { background: #c9ebcf; color: #22462a; }
        .module-tab--migration:focus { background: #9fdcab; color: #17351e; }
        .module-tab--migration.is-active { background: #8fd89d; color: #17351e; }
        .module-tab--migration.is-active:focus { background: #7fcb8d; color: #122816; }
        .module-tab--takeout { background: #f4edbe; color: #5e5420; }
        .module-tab--takeout:focus { background: #efd97d; color: #5a4700; }
        .module-tab--takeout.is-active { background: #f1cf57; color: #5a4700; }
        .module-tab--takeout.is-active:focus { background: #e7c44a; color: #473700; }
        .module-tab--cloud { background: #eee0d1; color: #5f432b; }
        .module-tab--cloud:focus { background: #dcc1a6; color: #432c1a; }
        .module-tab--cloud.is-active { background: #d5b290; color: #432c1a; }
        .module-tab--cloud.is-active:focus { background: #c89e79; color: #301f12; }
        .module-tab--standalone { background: #e6d8ef; color: #54366f; }
        .module-tab--standalone:focus { background: #d4bce5; color: #3e2257; }
        .module-tab--standalone.is-active { background: #c6addf; color: #3e2257; }
        .module-tab--standalone.is-active:focus { background: #b594d4; color: #2c183e; }
        .module-tab--upload { background: #efc8c8; color: #6c2727; }
        .module-tab--upload:focus { background: #e4acac; color: #581e1e; }
        .module-tab--upload.is-active { background: #e59a9a; color: #581e1e; }
        .module-tab--upload.is-active:focus { background: #d98686; color: #451515; }
        #content-stack {
            width: 1fr;
            height: 1fr;
            padding-left: 1;
        }
        #content-host {
            height: 2fr;
            min-height: 8;
        }
        #general-tabs {
            height: auto;
            margin-bottom: 0;
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
        .general-tab:focus {
            border: round #43566d;
            background: #2b4769;
            color: #f6fbff;
            text-style: bold;
        }
        .general-tab.is-active {
            background: #2e4f78;
            color: #ffffff;
            border: heavy #d7a35a;
            text-style: bold;
        }
        .general-tab.is-active:focus {
            border: heavy #d7a35a;
            background: #3a628f;
            text-style: bold;
        }
        .toolbar-btn {
            margin-left: 1;
            border: round #8a5b5b;
            background: #efc8c8;
            color: #6c2727;
            text-style: bold;
        }
        .toolbar-btn:focus,
        .sidebar-action:focus,
        .panel-toggle:focus {
            border: round #495c73;
            text-style: bold;
        }
        .toolbar-btn-save {
            border: round #6f95bf;
            background: #cddff3;
            color: #284866;
            text-style: bold;
        }
        .toolbar-btn-save:focus {
            background: #9fc4e5;
            color: #18344d;
        }
        .toolbar-btn-load {
            border: round #8a5b5b;
            background: #efc8c8;
            color: #6c2727;
            text-style: bold;
        }
        .toolbar-btn-load:focus {
            background: #e0aaaa;
            color: #531b1b;
        }
        .sidebar-action--run:focus {
            background: #8fd89d;
            color: #17351e;
        }
        .sidebar-action--stop:focus {
            background: #e59a9a;
            color: #581e1e;
        }
        .sidebar-action--exit:focus {
            background: #de8b8b;
            color: #4f1717;
        }
        #content-panel {
            height: 1fr;
            min-height: 10;
            border: round #37547b;
            padding: 0 1 0 1;
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
            padding: 0;
        }
        .config-section-description {
            margin-top: 1;
        }
        .section-title {
            color: #cfe0f5;
            text-style: bold;
            margin: 0;
        }
        .feature-section-title {
            color: #f0c88b;
            margin: 0;
        }
        .feature-section-title--spaced {
            margin-top: 1;
        }
        .field-row--spaced {
            margin-top: 1;
        }
        .field-row--config-account {
            margin-top: 2;
        }
        .config-section-spacer {
            height: 1;
            min-height: 1;
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
            align-vertical: middle;
        }
        .bool-toggle {
            width: auto;
            height: 1;
            min-height: 1;
            margin-top: 0;
        }
        .bool-switch {
            width: 7;
            min-width: 7;
            height: 1;
            min-height: 1;
            border: none;
            background: transparent;
            color: #98a4b3;
            padding: 0;
            text-style: none;
            tint: transparent;
        }
        .bool-switch:hover {
            border: none;
            background: transparent;
            tint: transparent;
        }
        .bool-switch:focus {
            border: none;
            background: transparent;
            tint: transparent;
        }
        .bool-switch.-active {
            border: none;
            background: transparent;
            tint: transparent;
        }
        .bool-switch.-on {
            border: none;
            background: transparent;
            color: #4cff7a;
        }
        .bool-switch.-off {
            border: none;
            background: transparent;
            color: #98a4b3;
        }
        .field-label {
            width: 29;
            min-width: 29;
            height: 1;
            min-height: 1;
            padding-top: 0;
            color: #d6dfeb;
        }
        .field-label--config-accent {
            color: #f0c88b;
            text-style: bold;
        }
        .field-label--config {
            width: 34;
            min-width: 34;
        }
        .field-main {
            width: 1fr;
            min-width: 0;
            height: 1;
            min-height: 1;
            content-align: center middle;
        }
        .field-path-control {
            width: 1fr;
            min-width: 0;
            height: 1;
            min-height: 1;
            layout: grid;
            grid-size: 2 1;
            grid-columns: 1fr 5;
            grid-gutter: 1 0;
            padding-right: 1;
            content-align: center middle;
        }
        .field-control {
            width: 1fr;
            min-width: 0;
            height: 1;
            min-height: 1;
            padding-right: 1;
            content-align: center middle;
        }
        .field-control--select {
            height: 1;
            min-height: 1;
        }
        .field-main > Input,
        .field-path-control > Input,
        .field-control > Input,
        .field-input-widget {
            width: 1fr;
            min-width: 0;
            height: 1;
            min-height: 1;
            border: none;
            padding: 0 1;
        }
        .field-main > Input:focus,
        .field-path-control > Input:focus,
        .field-control > Input:focus,
        .field-input-widget:focus,
        .field-main > Select.field-select-widget:focus,
        .field-control > Select.field-select-widget:focus,
        .path-button:focus,
        .bool-switch:focus {
            background: #223a57;
            color: #ffffff;
            text-style: bold;
        }
        .field-row:focus-within .field-label {
            color: #fff3c4;
            text-style: bold;
        }
        .field-select-widget {
            width: 1fr;
            min-width: 0;
            height: 1;
            min-height: 1;
            border: none;
            padding: 0;
        }
        .field-main > Select.field-select-widget,
        .field-control > Select.field-select-widget {
            height: 1;
            min-height: 1;
            border: none;
            padding: 0;
        }
        .field-help {
            color: #7f93ab;
            margin-left: 25;
            margin-bottom: 0;
            padding: 0;
        }
        .app-settings-spacer {
            height: 1;
            min-height: 1;
        }
        .app-settings-note {
            margin-left: 0;
            padding: 0;
        }
        .path-button {
            width: 5;
            min-width: 5;
            height: 1;
            min-height: 1;
            margin-left: 0;
            border: none;
            padding: 0;
            content-align: center middle;
        }
        .card {
            border: round #2f3f54;
            padding: 0 1;
            margin-bottom: 0;
            background: #121d2b;
        }
        .flags-grid {
            height: auto;
            min-height: 1;
            margin-bottom: 1;
            align-vertical: top;
        }
        .flags-column {
            width: 1fr;
            height: auto;
            min-height: 1;
            padding-right: 1;
        }
        .panel-shell {
            border: round #37547b;
            background: #0d141e;
            padding: 0 1 0 1;
            margin-bottom: 0;
        }
        .panel-shell-log {
            border: round #37547b;
            background: #0b1119;
            padding: 0 1 0 1;
            margin-bottom: 0;
        }
        .panel-topbar {
            height: auto;
            margin-bottom: 0;
            align-vertical: middle;
        }
        .panel-topbar-spacer {
            width: 1fr;
        }
        .panel-toggle {
            width: 3;
            min-width: 3;
            height: 1;
            min-height: 1;
            border: none;
            background: transparent;
            color: #dfeaf8;
            text-style: bold;
            padding: 0;
        }
        .panel-toggle:focus {
            background: #365d88;
            color: #ffffff;
        }
        .context-menu-btn {
            width: 1fr;
            min-width: 10;
            height: 3;
            min-height: 3;
            border: round #4f6b92;
            background: #162234;
            color: #f4f7fb;
            text-style: bold;
            padding: 0 1;
            margin: 0;
        }
        .context-menu-btn:disabled {
            background: #101824;
            color: #7f93ab;
            border: round #33465f;
        }
        #bottom-panels {
            height: 4fr;
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
        #status-panel {
            height: auto;
            min-height: 1;
        }
        #field-description-panel {
            height: auto;
            min-height: 2;
        }
        #command-preview-panel {
            height: auto;
            min-height: 2;
        }
        #log-panel-container {
            height: 1fr;
            min-height: 3;
            padding: 0;
        }
        #field-description,
        #command-preview,
        #status-line {
            height: auto;
            min-height: 1;
            background: transparent;
            color: #dfeaf8;
            padding: 0;
            margin-bottom: 0;
        }
        #log-panel {
            height: 1fr;
            min-height: 4;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
            text-wrap: nowrap;
            overflow-x: auto;
            overflow-y: auto;
            scrollbar-gutter: stable;
            scrollbar-size-horizontal: 1;
            scrollbar-size-vertical: 1;
            scrollbar-background: #060a10;
            scrollbar-background-hover: #060a10;
            scrollbar-background-active: #060a10;
            scrollbar-color: #0d4b79;
            scrollbar-color-hover: #0d4b79;
            scrollbar-color-active: #0d4b79;
            scrollbar-corner-color: #060a10;
        }
        #job-input-row {
            height: auto;
            margin-top: 0;
        }
        #job-input-panel {
            height: auto;
            min-height: 2;
        }
        #job-input {
            width: 1fr;
            height: 3;
            min-height: 3;
            border: none;
            padding: 0 1;
        }
        #send-input-btn {
            width: 8;
            min-width: 8;
            height: 3;
            min-height: 3;
        }
        #shortcut-bar {
            dock: bottom;
            layout: horizontal;
            height: 1;
            min-height: 1;
            background: #1b2432;
            color: #dfeaf8;
            padding: 0 1;
            text-wrap: nowrap;
        }
        .shortcut-key {
            width: auto;
            color: #f1cf57;
            background: transparent;
            text-style: bold;
            padding: 0;
        }
        .shortcut-desc {
            width: auto;
            color: #cfd9e6;
            background: transparent;
            padding: 0 2 0 1;
        }
        #picker-path-input {
            height: 1;
            min-height: 1;
            border: none;
            padding: 0 1;
        }
        #picker-dialog {
            width: 80%;
            height: 80%;
            border: round #4f6b92;
            padding: 1 1;
            background: #0f1722;
            align: center middle;
        }
        #context-dialog {
            width: 26;
            height: auto;
            border: round #4f6b92;
            padding: 1 1;
            background: #0f1722;
            align: center middle;
        }
        #context-actions {
            height: auto;
            margin-top: 0;
            align-horizontal: center;
        }
        #context-popup {
            layer: overlay;
            position: absolute;
            width: 16;
            height: 8;
            border: round #4f6b92;
            padding: 0 1;
            background: #0f1722;
            display: none;
            offset: 0 0;
        }
        #context-popup-actions {
            height: auto;
            layout: vertical;
        }
        .modal-title { text-style: bold; color: #ffffff; margin-bottom: 1; }
        .modal-subtitle { color: #92a8c3; margin-bottom: 1; }
        #picker-nav-actions { height: auto; margin: 0 0 0 0; }
        #picker-tree { height: 1fr; margin: 0; }
        #picker-actions {
            height: auto;
            align-horizontal: right;
            margin-top: 1;
        }
        .modal-btn {
            min-width: 22;
            height: 3;
            min-height: 3;
            text-style: bold;
            padding: 0 1;
            margin-right: 1;
        }
        .modal-btn:focus {
            text-style: bold;
        }
        .modal-btn-primary {
            background: #cce4f3;
            color: #244862;
            border: round #6f92b0;
        }
        .modal-btn-primary:focus {
            background: #8fbfe3;
            color: #102b3d;
            border: round #5f8fb2;
        }
        .modal-btn-primary.is-focused {
            background: #7aa8cb;
            color: #0f2a3b;
            border: heavy #4a7699;
        }
        .modal-btn-cancel {
            background: #e8c5c5;
            color: #703131;
            border: round #b97d7d;
        }
        .modal-btn-cancel:focus {
            background: #de9f9f;
            color: #4d1717;
            border: round #b57070;
        }
        .modal-btn-cancel.is-focused {
            background: #c98585;
            color: #451515;
            border: heavy #9c5c5c;
        }
        #picker-up:focus,
        #picker-home:focus,
        #picker-up.is-focused,
        #picker-home.is-focused {
            background: #27496f;
            color: #ffffff;
            border: heavy #3f6994;
            text-style: bold;
        }
        .danger-note { color: #ffb4b4; }
        .empty-note { color: #8da4be; margin-top: 1; }
        .theme-ocean {
            background: #11161f;
            color: #f4f7fb;
        }
        .theme-ocean #sidebar { background: #131c28; border: round #3b78b7; }
        .theme-ocean #content-panel { background: #0d141e; border: round #3b78b7; color: #dfeaf8; }
        .theme-ocean .panel-shell { background: #0d141e; border: round #3b78b7; }
        .theme-ocean .panel-shell-log { background: #0b1119; border: round #3b78b7; }
        .theme-ocean #field-description, .theme-ocean #status-line, .theme-ocean #command-preview { color: #dfeaf8; }
        .theme-ocean #log-panel, .theme-ocean .panel-toggle { color: #d9e8f8; }
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
        .theme-emerald #sidebar { background: #13201b; border: round #3f8f72; }
        .theme-emerald #content-panel { background: #0d1713; border: round #3f8f72; color: #def4e7; }
        .theme-emerald .panel-shell { background: #0d1713; border: round #3f8f72; }
        .theme-emerald .panel-shell-log { background: #0b1411; border: round #3f8f72; }
        .theme-emerald #field-description, .theme-emerald #status-line, .theme-emerald #command-preview, .theme-emerald #log-panel, .theme-emerald .panel-toggle { color: #def4e7; }
        .theme-emerald .general-tab { background: #173127; color: #d6ebe0; border: round #406a58; }
        .theme-emerald .general-tab.is-active { background: #2d6b55; color: #ffffff; }
        .theme-emerald .field-label, .theme-emerald .section-title, .theme-emerald .panel-title { color: #daf0e4; }
        .theme-emerald .field-label--config-accent { color: #7dffbf; }
        .theme-emerald .general-group-title { color: #7dffbf; }
        .theme-emerald .feature-section-title { color: #7dffbf; }
        .theme-emerald .field-help, .theme-emerald .panel-description { color: #9dc3b0; }
        .theme-emerald .toolbar-btn-save { background: #cce4f3; color: #244862; border: round #6f92b0; }
        .theme-emerald .toolbar-btn-load { background: #e8c5c5; color: #703131; border: round #875858; }

        .theme-sunset {
            background: #1a1410;
            color: #fbf1e8;
        }
        .theme-sunset #sidebar { background: #231913; border: round #b26a3a; }
        .theme-sunset #content-panel { background: #18110d; border: round #b26a3a; color: #f7e6d7; }
        .theme-sunset .panel-shell { background: #18110d; border: round #b26a3a; }
        .theme-sunset .panel-shell-log { background: #140f0b; border: round #b26a3a; }
        .theme-sunset #field-description, .theme-sunset #status-line, .theme-sunset #command-preview, .theme-sunset #log-panel, .theme-sunset .panel-toggle { color: #f7e6d7; }
        .theme-sunset .general-tab { background: #35231a; color: #f0dfd1; border: round #7f5d47; }
        .theme-sunset .general-tab.is-active { background: #8d5630; color: #fff7f1; }
        .theme-sunset .field-label, .theme-sunset .section-title, .theme-sunset .panel-title { color: #f2e1d3; }
        .theme-sunset .field-label--config-accent { color: #ffd29a; }
        .theme-sunset .general-group-title { color: #ffd29a; }
        .theme-sunset .feature-section-title { color: #ffd29a; }
        .theme-sunset .field-help, .theme-sunset .panel-description { color: #cfb39f; }
        .theme-sunset .toolbar-btn-save { background: #d8e8f6; color: #294b6d; border: round #6f8fac; }
        .theme-sunset .toolbar-btn-load { background: #efc8c8; color: #7a2c2c; border: round #9a6161; }

        .theme-dark {
            background: #0c0f14;
            color: #e6ebf2;
        }
        .theme-dark #sidebar { background: #11161d; border: round #6d7a8d; }
        .theme-dark #content-panel { background: #0b1016; border: round #6d7a8d; color: #d8e0ea; }
        .theme-dark .panel-shell { background: #0b1016; border: round #6d7a8d; }
        .theme-dark .panel-shell-log { background: #090d12; border: round #6d7a8d; }
        .theme-dark #field-description, .theme-dark #status-line, .theme-dark #command-preview, .theme-dark #log-panel, .theme-dark .panel-toggle { color: #d8e0ea; }
        .theme-dark .general-tab { background: #1a212b; color: #d0d9e4; border: round #526072; }
        .theme-dark .general-tab.is-active { background: #39485c; color: #ffffff; }
        .theme-dark .field-label, .theme-dark .section-title, .theme-dark .panel-title { color: #dbe3ee; }
        .theme-dark .field-label--config-accent { color: #b8c7ff; }
        .theme-dark .general-group-title { color: #b8c7ff; }
        .theme-dark .feature-section-title { color: #b8c7ff; }
        .theme-dark .field-help, .theme-dark .panel-description { color: #9aa7b7; }
        .theme-dark .toolbar-btn-save { background: #bed2ea; color: #203c5a; border: round #6784a2; }
        .theme-dark .toolbar-btn-load { background: #dcb8b8; color: #5e2323; border: round #7d5252; }
        """

        BINDINGS = [
            Binding("tab", "focus_next_panel", "Next Panel", priority=True),
            Binding("shift+tab", "focus_previous_panel", "Previous Panel", priority=True),
            Binding("backtab", "focus_previous_panel", "Previous Panel", priority=True),
            Binding("up", "move_up", "Move Up", priority=True),
            Binding("left", "move_left", "Move Left", priority=True),
            Binding("down", "move_down", "Move Down", priority=True),
            Binding("right", "move_right", "Move Right", priority=True),
            Binding("ctrl+r", "run_job", "Run"),
            Binding("ctrl+s", "save_config", "Save Config"),
            Binding("ctrl+l", "load_config", "Load Config"),
            Binding("ctrl+c", "copy_text", "Copy", key_display="^C", priority=True),
            Binding("ctrl+v", "paste_text", "Paste", key_display="^V"),
            Binding("ctrl+q", "quit", "Quit"),
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
            self.last_context_widget_id = ""
            self.context_menu_target_widget_id = ""
            self.context_menu_visible = False
            self.panel_collapsed = {
                "content": False,
                "description": False,
                "preview": False,
                "log": False,
                "status": False,
            }
            self.selected_theme = str(self.ui_state.get("theme") or "ocean")
            self.remember_state = bool(self.ui_state.get("remember_state", True))
            self.launch_cwd = Path.cwd().resolve()
            self.running_process: subprocess.Popen[str] | None = None
            self.running_command: List[str] = []
            self.log_buffer = CompactLogBuffer()
            self.log_history: List[str] = []
            self.job_starting = False
            self.current_status_text = "Ready."
            self.current_command_preview_text = ""
            self.current_field_description_text = "Move focus to a field to see its description here."
            self.auto_collapsed_content_for_run = False
            if self.active_module not in INTERACTIVE_MODULE_TAB_NAMES:
                self.active_module = "automatic_migration"
            self.reload_config_model()

        def _modal_screen_active(self) -> bool:
            try:
                current_screen = self.screen
            except Exception:
                return False
            return current_screen is not self and isinstance(current_screen, ModalScreen)

        def check_action(self, action: str, parameters: tuple[object, ...]) -> bool:
            if self._modal_screen_active() and action in {
                "focus_next_panel",
                "focus_previous_panel",
                "move_up",
                "move_down",
                "move_left",
                "move_right",
            }:
                return False
            return True

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

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="workspace"):
                with Vertical(id="sidebar"):
                    yield Static("Select Feature:", id="sidebar-title")
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
                            yield Button("Save Config", id="save-config-btn", classes="toolbar-btn toolbar-btn-save")
                            yield Button("Save UI State", id="save-ui-state-btn", classes="toolbar-btn toolbar-btn-save")
                            yield Button("Load Config", id="load-config-btn", classes="toolbar-btn toolbar-btn-load")
                    yield Vertical(id="content-host")
                    with Vertical(id="bottom-panels"):
                        with Vertical(id="field-description-panel", classes="panel-shell"):
                            with Horizontal(classes="panel-topbar"):
                                yield Static("", classes="panel-topbar-spacer")
                                yield Button("−", id="toggle-description-panel", classes="panel-toggle")
                            yield Static("Move focus to a field to see its description here.", id="field-description")
                        with Vertical(id="command-preview-panel", classes="panel-shell"):
                            with Horizontal(classes="panel-topbar"):
                                yield Static("", classes="panel-topbar-spacer")
                                yield Button("−", id="toggle-preview-panel", classes="panel-toggle")
                            yield Static("", id="command-preview")
                        with Vertical(id="log-panel-container", classes="panel-shell-log"):
                            with Horizontal(classes="panel-topbar"):
                                yield Static("", classes="panel-topbar-spacer")
                                yield Button("−", id="toggle-log-panel", classes="panel-toggle")
                            yield ExecutionLogView(id="log-panel", auto_scroll=True)
                        with Vertical(id="status-panel", classes="panel-shell"):
                            with Horizontal(classes="panel-topbar"):
                                yield Static("", classes="panel-topbar-spacer")
                                yield Button("−", id="toggle-status-panel", classes="panel-toggle")
                            yield Static("Ready.", id="status-line")
                        with Vertical(id="job-input-panel", classes="panel-shell"):
                            yield Static("", classes="panel-topbar-spacer")
                            with Horizontal(id="job-input-row"):
                                yield NavigableInput(placeholder="Send input to running job if it requests confirmation", id="job-input")
                                yield Button("Send", id="send-input-btn", classes="sidebar-action sidebar-action--run")
                with Vertical(id="context-popup"):
                    with Vertical(id="context-popup-actions"):
                        yield Button("Copy", id="context-copy", classes="context-menu-btn")
                        yield Button("Paste", id="context-paste", classes="context-menu-btn")
            with Horizontal(id="shortcut-bar"):
                yield Static("Tab", classes="shortcut-key")
                yield Static("Panel+", classes="shortcut-desc")
                yield Static("S-Tab", classes="shortcut-key")
                yield Static("Panel-", classes="shortcut-desc")
                yield Static("↑↓←→", classes="shortcut-key")
                yield Static("Fields", classes="shortcut-desc")
                yield Static("Enter", classes="shortcut-key")
                yield Static("Open", classes="shortcut-desc")
                yield Static("Esc", classes="shortcut-key")
                yield Static("Back", classes="shortcut-desc")
                yield Static("^R", classes="shortcut-key")
                yield Static("Run", classes="shortcut-desc")
                yield Static("^S", classes="shortcut-key")
                yield Static("Save Config", classes="shortcut-desc")
                yield Static("^L", classes="shortcut-key")
                yield Static("Load Config", classes="shortcut-desc")
                yield Static("^C", classes="shortcut-key")
                yield Static("Copy", classes="shortcut-desc")
                yield Static("^V", classes="shortcut-key")
                yield Static("Paste", classes="shortcut-desc")
                yield Static("^Q", classes="shortcut-key")
                yield Static("Quit", classes="shortcut-desc")

        async def on_mount(self) -> None:
            try:
                self.screen.ALLOW_SELECT = True
            except Exception:
                pass
            self.apply_theme()
            self.refresh_tab_styles()
            await self.rebuild_content()
            self.update_command_preview()
            self.refresh_action_buttons()
            self.apply_panel_states()
            self.refresh_runtime_layout()
            self.set_interval(0.15, self.sync_field_description_from_focus)
            self.set_timer(0.05, self._focus_default_widget)

        async def rebuild_content(self) -> None:
            host = self.query_one("#content-host", Vertical)
            await host.remove_children()
            self.field_help_map = {}
            self.last_focused_widget_id = ""
            self.last_hovered_widget_id = ""
            widgets: List[Any] = []
            widgets.extend(self.build_content_widgets())
            content_panel = Vertical(id="content-panel", classes="panel-shell")
            header_row = Horizontal(
                Static("", classes="panel-topbar-spacer"),
                Button("−", id="toggle-content-panel", classes="panel-toggle"),
                classes="panel-topbar",
            )
            content_body: Any = VerticalScroll(id="content-body")
            await host.mount(content_panel)
            await content_panel.mount(header_row, content_body)
            if widgets:
                await content_body.mount(*widgets)
            self.refresh_panel_titles()
            self.update_field_description("Move focus to a field to see its description here.")
            self.apply_panel_states()
            self.refresh_runtime_layout()
            self.call_after_refresh(self.refresh_panel_titles)
            self.call_after_refresh(self.refresh_content_scrollbar)
            self.call_after_refresh(self._focus_default_widget)
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

        def _toggle_label(self, panel_key: str) -> str:
            return "▸" if self.panel_collapsed.get(panel_key, False) else "▾"

        def refresh_toggle_buttons(self) -> None:
            button_map = {
                "content": "toggle-content-panel",
                "description": "toggle-description-panel",
                "preview": "toggle-preview-panel",
                "log": "toggle-log-panel",
                "status": "toggle-status-panel",
            }
            for panel_key, widget_id in button_map.items():
                try:
                    self.query_one(f"#{widget_id}", Button).label = self._toggle_label(panel_key)
                except Exception:
                    pass
        def apply_panel_states(self) -> None:
            body_map = {
                "content": "content-body",
                "description": "field-description",
                "preview": "command-preview",
                "log": "log-panel",
                "status": "status-line",
            }
            shell_map = {
                "content": "content-panel",
                "description": "field-description-panel",
                "preview": "command-preview-panel",
                "log": "log-panel-container",
                "status": "status-panel",
            }
            for panel_key, widget_id in body_map.items():
                try:
                    widget = self.query_one(f"#{widget_id}")
                    widget.styles.display = "none" if self.panel_collapsed.get(panel_key, False) else "block"
                except Exception:
                    pass
            for panel_key, shell_id in shell_map.items():
                try:
                    shell = self.query_one(f"#{shell_id}")
                    if self.panel_collapsed.get(panel_key, False):
                        shell.styles.height = 4
                        shell.styles.min_height = 4
                    else:
                        if panel_key == "content":
                            shell.styles.height = "1fr"
                            shell.styles.min_height = 8
                        elif panel_key == "log":
                            shell.styles.height = "1fr"
                            shell.styles.min_height = 4
                        else:
                            shell.styles.height = "auto"
                            shell.styles.min_height = 2
                except Exception:
                    pass
            self.refresh_toggle_buttons()

        def toggle_panel(self, panel_key: str) -> None:
            self.panel_collapsed[panel_key] = not self.panel_collapsed.get(panel_key, False)
            self.apply_panel_states()
            self.refresh_runtime_layout()
            self.call_after_refresh(self.refresh_content_scrollbar)

        def refresh_runtime_layout(self) -> None:
            running = self.can_stop_job()
            try:
                content_host = self.query_one("#content-host", Vertical)
                if self.panel_collapsed.get("content", False):
                    content_host.styles.height = "auto"
                    content_host.styles.min_height = 4
                else:
                    content_host.styles.height = "2fr" if running else "3fr"
                    content_host.styles.min_height = 7
            except Exception:
                pass

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
            self.refresh_runtime_layout()
            self.call_after_refresh(self.refresh_content_scrollbar)
            try:
                bottom_panels = self.query_one("#bottom-panels", Vertical)
                bottom_panels.styles.height = "5fr" if running else "4fr"
            except Exception:
                pass
            try:
                log_container = self.query_one("#log-panel-container", Vertical)
                log_container.styles.height = "1fr"
                log_container.styles.min_height = 4
            except Exception:
                pass

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
                self.query_one("#field-description-panel", Vertical).border_title = "Argument Description"
            except Exception:
                pass
            try:
                self.query_one("#status-panel", Vertical).border_title = "Status"
            except Exception:
                pass
            try:
                self.query_one("#command-preview-panel", Vertical).border_title = "Command Preview"
            except Exception:
                pass
            try:
                self.query_one("#log-panel-container", Vertical).border_title = "Execution Log"
            except Exception:
                pass
            try:
                self.query_one("#job-input-panel", Vertical).border_title = "Process Input"
            except Exception:
                pass
            self.refresh_toggle_buttons()

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
                regular_fields = [field for field in fields if str(field.get("kind") or "") not in {"flag", "bool"}]
                toggle_fields = [field for field in fields if str(field.get("kind") or "") in {"flag", "bool"}]
                migration_filter_fields = build_automatic_migration_filter_fields(self.schema)

                if regular_fields:
                    widgets.append(Static("Module Fields", classes="section-title feature-section-title"))
                    for field in regular_fields:
                        if str(field.get("dest") or "") in {"source", "target"}:
                            widgets.append(self.build_migration_endpoint_row(str(field.get("dest") or ""), str(field.get("help") or "").strip()))
                        else:
                            widgets.extend(self.build_field_widgets(field, context=tab_key))

                if toggle_fields:
                    widgets.append(Static("Flags", classes="section-title feature-section-title feature-section-title--spaced"))
                    widgets.append(self.build_flags_columns(toggle_fields, tab_key))

                if migration_filter_fields:
                    widgets.append(Static("Migration Filters", classes="section-title feature-section-title feature-section-title--spaced"))
                    widgets.append(Static("If empty, value from General Arguments will be used.", classes="field-help"))
                    for field in migration_filter_fields:
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
                    widgets.append(Static("Flags", classes="section-title feature-section-title feature-section-title--spaced"))
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
                input_widget = Input(value=path_value, id=f"field-{dest}", classes="field-input-widget")
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
            if context in {"automatic_migration", "google_takeout", "icloud_takeout"}:
                num_columns = 3
            else:
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
            widgets.append(Static("Action Arguments", classes="section-title feature-section-title feature-section-title--spaced"))
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
                widgets.append(Static("Optional", classes="section-title feature-section-title feature-section-title--spaced"))
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
            widgets.append(Static("Action Arguments", classes="section-title feature-section-title feature-section-title--spaced"))
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
            widgets.append(Static(str(current_section.get("description") or "").strip(), classes="panel-description config-section-description"))
            fields = list(current_section.get("fields") or [])
            global_fields = [field for field in fields if not str(field.get("account_id") or "")]
            account_fields = [field for field in fields if str(field.get("account_id") or "")]
            for field in global_fields:
                widgets.extend(self.build_config_field_widgets(current_section["name"], field))
            selector = current_section.get("account_selector") or {}
            if selector.get("enabled"):
                section_name = current_section["name"]
                account_value = str(self.active_config_account.get(section_name) or selector.get("default_account") or "")
                widgets.append(Static("", classes="config-section-spacer"))
                widgets.append(
                    self.build_select_row(
                        "Configure Account",
                        "config-account-select",
                        [(f"Account {acc}", acc) for acc in selector.get("accounts") or []],
                        account_value,
                        help_text="Select which account within this service section you want to configure.",
                        label_classes="field-label field-label--config-accent",
                        row_classes="field-row field-row--spaced field-row--config-account",
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
                Static("", classes="app-settings-spacer"),
                Static(f"State file: {TUI_STATE_PATH}", classes="field-help app-settings-note"),
                Static(f"Config file in use: {self.current_config_path()}", classes="field-help app-settings-note"),
                Static("Use Ctrl+S to save Config.ini, Ctrl+L to load a Config.ini file, and Ctrl+R to run the current module.", classes="field-help app-settings-note"),
            ]
            return widgets

        def register_field_help(self, widget_id: str, help_text: str) -> None:
            text = str(help_text or "").strip()
            if text:
                self.field_help_map[widget_id] = text

        def update_field_description(self, text: str) -> None:
            self.current_field_description_text = str(text or "").strip() or "Move focus to a field to see its description here."
            self.query_one("#field-description", Static).update(self.current_field_description_text)

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
            if widget_id:
                self.last_context_widget_id = widget_id
            if help_text:
                self.update_field_description(help_text)
                return
            self.sync_field_description_from_focus()

        def _resolve_widget_by_id(self, widget_id: str) -> Any | None:
            if not widget_id:
                return None
            try:
                return self.query_one(f"#{widget_id}")
            except Exception:
                return None

        def _context_widget(self) -> Any | None:
            for widget_id in [self.context_menu_target_widget_id, self.last_context_widget_id, self.last_hovered_widget_id, self.last_focused_widget_id]:
                widget = self._resolve_widget_by_id(widget_id)
                if widget is not None:
                    return widget
            try:
                return getattr(self.screen, "focused", None)
            except Exception:
                return None

        def _selected_log_text(self) -> str:
            try:
                log_widget = self.query_one("#log-panel", ExecutionLogView)
            except Exception:
                return ""
            try:
                return str(log_widget.get_manual_selection_text() or "")
            except Exception:
                return ""

        def _copy_text_for_widget(self, widget: Any | None) -> str:
            if widget is None:
                return ""
            if isinstance(widget, Input):
                selected_text = ""
                candidate = getattr(widget, "selected_text", "")
                if callable(candidate):
                    try:
                        candidate = candidate()
                    except Exception:
                        candidate = ""
                if isinstance(candidate, str):
                    selected_text = candidate
                return selected_text or str(getattr(widget, "value", "") or "")
            if isinstance(widget, ExecutionLogView):
                selected_text = widget.get_manual_selection_text()
                if selected_text:
                    return selected_text
                return "\n".join(self.log_buffer.render_lines(include_partial=True))
            widget_id = str(getattr(widget, "id", "") or "")
            if widget_id == "command-preview":
                return self.current_command_preview_text
            if widget_id == "field-description":
                return self.current_field_description_text
            if widget_id == "status-line":
                return self.current_status_text
            if widget_id == "log-panel":
                return "\n".join(self.log_history)
            for attr in ("renderable", "content", "value"):
                candidate = getattr(widget, attr, None)
                if candidate:
                    return str(candidate)
            return str(widget or "")

        def _widget_accepts_paste(self, widget: Any | None) -> bool:
            return isinstance(widget, Input)

        def _copy_to_system_clipboard(self, text: str) -> bool:
            if not text:
                return False
            try:
                if sys.platform == "darwin" and shutil.which("pbcopy"):
                    subprocess.run(["pbcopy"], input=text, text=True, check=True)
                    return True
                if sys.platform.startswith("win") and shutil.which("clip"):
                    subprocess.run(["clip"], input=text, text=True, check=True, shell=False)
                    return True
                if shutil.which("wl-copy"):
                    subprocess.run(["wl-copy"], input=text, text=True, check=True)
                    return True
                if shutil.which("xclip"):
                    subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
                    return True
                if shutil.which("xsel"):
                    subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, check=True)
                    return True
            except Exception:
                return False
            return False

        def _read_from_system_clipboard(self) -> str:
            commands: List[List[str]] = []
            if sys.platform == "darwin" and shutil.which("pbpaste"):
                commands.append(["pbpaste"])
            elif sys.platform.startswith("win"):
                if shutil.which("powershell"):
                    commands.append(["powershell", "-NoProfile", "-Command", "Get-Clipboard"])
                if shutil.which("pwsh"):
                    commands.append(["pwsh", "-NoProfile", "-Command", "Get-Clipboard"])
            else:
                if shutil.which("wl-paste"):
                    commands.append(["wl-paste", "-n"])
                if shutil.which("xclip"):
                    commands.append(["xclip", "-selection", "clipboard", "-o"])
                if shutil.which("xsel"):
                    commands.append(["xsel", "--clipboard", "--output"])
            for command in commands:
                try:
                    result = subprocess.run(command, capture_output=True, text=True, check=True)
                    text = str(result.stdout or "")
                    if text:
                        return text
                except Exception:
                    continue
            return ""

        def _paste_text_into_widget(self, widget: Any | None, text: str) -> bool:
            if not isinstance(widget, Input) or not text:
                return False
            try:
                if hasattr(widget, "insert_text_at_cursor"):
                    widget.insert_text_at_cursor(text)
                else:
                    widget.value = f"{widget.value}{text}"
                return True
            except Exception:
                try:
                    widget.value = f"{widget.value}{text}"
                    return True
                except Exception:
                    return False

        def hide_context_popup(self) -> None:
            try:
                popup = self.query_one("#context-popup", Vertical)
                popup.styles.display = "none"
            except Exception:
                pass
            self.context_menu_visible = False
            self.context_menu_target_widget_id = ""

        def show_context_popup(self, screen_x: int, screen_y: int, *, can_copy: bool, can_paste: bool, target_widget_id: str = "") -> None:
            try:
                popup = self.query_one("#context-popup", Vertical)
                copy_button = self.query_one("#context-copy", Button)
                paste_button = self.query_one("#context-paste", Button)
                copy_button.disabled = not can_copy
                paste_button.disabled = not can_paste
                popup.styles.offset = (max(0, int(screen_x) - 1), max(0, int(screen_y) - 1))
                popup.styles.display = "block"
                self.context_menu_visible = True
                self.context_menu_target_widget_id = str(target_widget_id or "")
            except Exception:
                self.context_menu_visible = False
                self.context_menu_target_widget_id = ""

        def _widget_is_in_context_popup(self, widget: Any | None) -> bool:
            current = widget
            while current is not None:
                if str(getattr(current, "id", "") or "") == "context-popup":
                    return True
                current = getattr(current, "parent", None)
            return False

        def action_copy_text(self) -> None:
            selected_log_text = self._selected_log_text()
            if selected_log_text:
                if self._copy_to_system_clipboard(selected_log_text):
                    self.update_status("Selected text copied to system clipboard.")
                else:
                    self.update_status("Unable to access the system clipboard from this terminal environment.")
                return
            try:
                get_selected_text = getattr(self.screen, "get_selected_text", None)
                if callable(get_selected_text):
                    selected_text = str(get_selected_text() or "")
                    if selected_text:
                        if self._copy_to_system_clipboard(selected_text):
                            self.update_status("Selected text copied to system clipboard.")
                        else:
                            self.update_status("Unable to access the system clipboard from this terminal environment.")
                        return
            except Exception:
                pass
            widget = self._context_widget()
            text = self._copy_text_for_widget(widget)
            if not text:
                self.update_status("No text available to copy from the current context.")
                return
            if self._copy_to_system_clipboard(text):
                self.update_status("Text copied to system clipboard.")
            else:
                self.update_status("Unable to access the system clipboard from this terminal environment.")

        def action_paste_text(self) -> None:
            widget = self._context_widget()
            if not self._widget_accepts_paste(widget):
                self.update_status("Paste is only available on editable fields.")
                return
            text = self._read_from_system_clipboard()
            if not text:
                self.update_status("System clipboard is empty or not accessible.")
                return
            if self._paste_text_into_widget(widget, text):
                self.update_status("Clipboard pasted into the current field.")
                if isinstance(widget, Input):
                    self.last_context_widget_id = str(getattr(widget, "id", "") or "")
            else:
                self.update_status("Unable to paste clipboard text into the current field.")

        def on_mouse_down(self, event: events.MouseDown) -> None:
            clicked_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            if int(getattr(event, "button", 0) or 0) != 3 and self.context_menu_visible and not self._widget_is_in_context_popup(clicked_widget):
                self.hide_context_popup()
            if int(getattr(event, "button", 0) or 0) != 3:
                return
            current = clicked_widget
            target = None
            while current is not None:
                current_id = str(getattr(current, "id", "") or "")
                if isinstance(current, (Input, Static, ExecutionLogView)) and current_id:
                    target = current
                    break
                current = getattr(current, "parent", None)
            if target is None:
                return
            self.last_context_widget_id = str(getattr(target, "id", "") or "")
            clipboard_text = self._read_from_system_clipboard() if self._widget_accepts_paste(target) else ""
            self.show_context_popup(
                event.screen_x,
                event.screen_y,
                can_copy=bool(self._copy_text_for_widget(target)),
                can_paste=self._widget_accepts_paste(target) and bool(str(clipboard_text or "")),
                target_widget_id=str(getattr(target, "id", "") or ""),
            )
            event.stop()
            try:
                event.prevent_default()
            except Exception:
                pass

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

        def _log_scroll_target(self, widget: Any | None) -> Any | None:
            current = widget
            while current is not None:
                current_id = str(getattr(current, "id", "") or "")
                if current_id == "log-panel" and isinstance(current, ExecutionLogView):
                    return current
                if current_id == "log-panel-container":
                    try:
                        return self.query_one("#log-panel", ExecutionLogView)
                    except Exception:
                        return None
                current = getattr(current, "parent", None)
            try:
                focused = getattr(self.screen, "focused", None)
                if isinstance(focused, ExecutionLogView):
                    return focused
            except Exception:
                pass
            try:
                return self.query_one("#log-panel", ExecutionLogView)
            except Exception:
                return None

        def _scroll_modifier_active(self, event: Any) -> bool:
            return any(bool(getattr(event, attr, False)) for attr in ("shift", "ctrl", "meta", "alt"))

        def _content_panel_overflows(self) -> bool:
            try:
                container = self.query_one("#content-body")
                if not isinstance(container, VerticalScroll):
                    return False
                return int(getattr(container, "max_scroll_y", 0) or 0) > 1
            except Exception:
                return True

        def refresh_content_scrollbar(self) -> None:
            try:
                container = self.query_one("#content-body")
                if isinstance(container, VerticalScroll):
                    container.styles.scrollbar_visibility = "visible" if self._content_panel_overflows() else "hidden"
            except Exception:
                pass

        def on_resize(self, event: events.Resize) -> None:
            self.call_after_refresh(self.refresh_content_scrollbar)

        def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            log_target = self._log_scroll_target(hovered_widget)
            if self._scroll_modifier_active(event) and log_target is not None:
                if self._scroll_widget_horizontally(log_target, 4):
                    event.stop()
                    try:
                        event.prevent_default()
                    except Exception:
                        pass
                    return
            if self._widget_is_within(hovered_widget, "content-body") and not self._content_panel_overflows():
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            log_target = self._log_scroll_target(hovered_widget)
            if self._scroll_modifier_active(event) and log_target is not None:
                if self._scroll_widget_horizontally(log_target, -4):
                    event.stop()
                    try:
                        event.prevent_default()
                    except Exception:
                        pass
                    return
            if self._widget_is_within(hovered_widget, "content-body") and not self._content_panel_overflows():
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_left(self, event: events.MouseScrollLeft) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            log_target = self._log_scroll_target(hovered_widget)
            if log_target is not None and self._scroll_widget_horizontally(log_target, -4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def on_mouse_scroll_right(self, event: events.MouseScrollRight) -> None:
            hovered_widget = self._widget_under_pointer(event.screen_x, event.screen_y)
            log_target = self._log_scroll_target(hovered_widget)
            if log_target is not None and self._scroll_widget_horizontally(log_target, 4):
                event.stop()
                try:
                    event.prevent_default()
                except Exception:
                    pass

        def _scroll_widget_horizontally(self, widget: Any | None, delta: int) -> bool:
            current = widget
            target = None
            while current is not None:
                if str(getattr(current, "id", "") or "") == "log-panel":
                    target = current
                    break
                current = getattr(current, "parent", None)
            if target is None:
                return False
            try:
                max_scroll_x = float(getattr(target, "max_scroll_x", 0) or 0)
            except Exception:
                max_scroll_x = 0
            if max_scroll_x <= 0 and isinstance(target, ExecutionLogView):
                try:
                    visible_width = int(getattr(getattr(target, "size", None), "width", 0) or 0)
                    content_width = max((len(target._line_plain(index)) for index in range(len(target._lines))), default=0)
                    if visible_width > 0 and content_width > visible_width:
                        max_scroll_x = float(content_width - visible_width)
                except Exception:
                    max_scroll_x = 0
            if max_scroll_x <= 0:
                return False
            try:
                if delta > 0:
                    scroll_right = getattr(target, "scroll_right", None)
                    if callable(scroll_right):
                        for _ in range(abs(int(delta))):
                            scroll_right(animate=False)
                        return True
                elif delta < 0:
                    scroll_left = getattr(target, "scroll_left", None)
                    if callable(scroll_left):
                        for _ in range(abs(int(delta))):
                            scroll_left(animate=False)
                        return True
            except Exception:
                pass
            try:
                scroll_relative = getattr(target, "scroll_relative", None)
                if callable(scroll_relative):
                    scroll_relative(x=delta, animate=False, immediate=True, force=True)
                    return True
            except Exception:
                pass
            try:
                current_x = float(getattr(target, "scroll_x", 0) or 0)
                scroll_to = getattr(target, "scroll_to", None)
                if callable(scroll_to):
                    next_x = max(0, min(max_scroll_x, current_x + delta))
                    scroll_to(x=next_x, y=None, animate=False, immediate=True, force=True)
                    return True
            except Exception:
                pass
            return False

        def build_select_row(
            self,
            label: str,
            widget_id: str,
            options: List[tuple[str, Any]],
            value: Any,
            help_text: str = "",
            label_classes: str = "field-label",
            row_classes: str = "field-row",
        ) -> Horizontal:
            normalized_options = [(str(label_text), str(option_value)) for label_text, option_value in options]
            current_value = str(value or "")
            if current_value and all(option_value != current_value for _, option_value in normalized_options):
                normalized_options = [*normalized_options, (current_value, current_value)]
            select = NavigableSelect(
                normalized_options,
                value=current_value or (normalized_options[0][1] if normalized_options else None),
                id=widget_id,
                classes="field-control-widget field-select-widget",
                compact=True,
            )
            self.register_field_help(widget_id, help_text)
            return Horizontal(Label(label, classes=label_classes), Horizontal(select, classes="field-control field-control--select"), classes=row_classes)

        def build_checkbox_row(self, label: str, widget_id: str, value: bool, help_text: str = "") -> Horizontal:
            self.register_field_help(widget_id, help_text)
            return Horizontal(Label(label, classes="field-label"), Checkbox(value=bool(value), id=widget_id), classes="field-row")

        def build_boolean_toggle_row(self, label: str, dest: str, value: bool, help_text: str = "") -> Horizontal:
            toggle_id = f"bool-{dest}-toggle"
            self.register_field_help(toggle_id, help_text)
            toggle_button = Button("", id=toggle_id, classes="bool-switch")
            self._set_boolean_toggle_visual(toggle_button, bool(value))
            return Horizontal(
                Label(label, classes="field-label"),
                Horizontal(toggle_button, classes="bool-toggle"),
                classes="field-row",
            )

        def build_pseudo_text_field(self, label: str, dest: str, value: Any, required: bool, help_text: str) -> List[Any]:
            return self.build_input_block(label, dest, str(value or ""), required, help_text, path_hint="")

        def build_pseudo_list_field(self, label: str, dest: str, value: Any, required: bool, help_text: str) -> List[Any]:
            joined = ", ".join(parse_folder_list_value(value))
            return self.build_input_block(label, dest, joined, required, help_text, path_hint="path", browse_title=f"Select paths for {label}")

        def build_input_block(self, label: str, dest: str, value: str, required: bool, help_text: str, path_hint: str = "", browse_title: str | None = None, password: bool = False) -> List[Any]:
            label_text = f"{label}{' *' if required else ''}"
            input_widget = NavigableInput(value=value, password=password, id=f"field-{dest}", classes="field-input-widget")
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
            label = ui_option_name(field)
            help_text = str(field.get("help") or "").strip()
            kind = str(field.get("kind") or "text")
            value = effective_interactive_field_value(field, self.state_values)
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
            input_widget = NavigableInput(value=value, password=bool(field.get("sensitive")), id=widget_id, classes="field-input-widget")
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

        def _focused_widget(self) -> Any | None:
            try:
                return getattr(self.screen, "focused", None)
            except Exception:
                return None

        def _widget_is_focus_candidate(self, widget: Any) -> bool:
            if not isinstance(widget, (Button, Input, Select, Checkbox)):
                return False
            if getattr(widget, "disabled", False):
                return False
            try:
                if widget.styles.display == "none":
                    return False
            except Exception:
                pass
            if self._widget_is_in_context_popup(widget) and not self.context_menu_visible:
                return False
            return True

        def _focusable_widgets_in_order(self) -> List[Any]:
            widgets: List[Any] = []
            try:
                for widget in self.screen.query("*"):
                    if self._widget_is_focus_candidate(widget):
                        widgets.append(widget)
            except Exception:
                return []
            return widgets

        def _focus_default_widget(self) -> None:
            focused = self._focused_widget()
            if focused is not None and self._widget_is_focus_candidate(focused):
                return
            preferred_ids = [
                f"general-tab-{self.active_general_tab}",
                f"module-tab-{self.active_module}",
                "run-btn",
            ]
            for widget_id in preferred_ids:
                try:
                    widget = self.query_one(f"#{widget_id}")
                except Exception:
                    continue
                if self._widget_is_focus_candidate(widget):
                    try:
                        self.screen.set_focus(widget)
                        return
                    except Exception:
                        continue
            widgets = self._focusable_widgets_in_order()
            if widgets:
                try:
                    self.screen.set_focus(widgets[0])
                except Exception:
                    pass

        def _widget_panel_id(self, widget: Any | None) -> str:
            current = widget
            while current is not None:
                widget_id = str(getattr(current, "id", "") or "")
                if widget_id == "sidebar-actions":
                    return "sidebar-features"
                if widget_id in FOCUS_PANEL_IDS:
                    return widget_id
                current = getattr(current, "parent", None)
            return ""

        def _panel_widgets(self, panel_id: str) -> List[Any]:
            widgets: List[Any] = []
            if not panel_id:
                return widgets
            try:
                for widget in self.screen.query("*"):
                    if not self._widget_is_focus_candidate(widget):
                        continue
                    if self._widget_panel_id(widget) == panel_id:
                        widgets.append(widget)
            except Exception:
                return []
            return widgets

        def _available_panel_ids(self) -> List[str]:
            panel_ids: List[str] = []
            for panel_id in FOCUS_PANEL_IDS:
                if self._panel_widgets(panel_id):
                    panel_ids.append(panel_id)
            return panel_ids

        def _focus_panel_by_delta(self, delta: int) -> None:
            panel_ids = self._available_panel_ids()
            if not panel_ids:
                return
            focused = self._focused_widget()
            current_panel = self._widget_panel_id(focused)
            try:
                current_index = panel_ids.index(current_panel) if current_panel in panel_ids else (-1 if delta > 0 else 0)
            except ValueError:
                current_index = -1 if delta > 0 else 0
            next_index = (current_index + delta) % len(panel_ids)
            target_panel = panel_ids[next_index]
            panel_widgets = self._panel_widgets(target_panel)
            if not panel_widgets:
                return
            target_widget = None
            preferred_ids = preferred_tui_panel_widget_ids(
                target_panel,
                active_general_tab=self.active_general_tab,
                active_module=self.active_module,
            )
            for widget_id in preferred_ids:
                candidate = next((widget for widget in panel_widgets if str(getattr(widget, "id", "") or "") == widget_id), None)
                if candidate is not None:
                    target_widget = candidate
                    break
            if target_widget is None:
                target_widget = panel_widgets[0]
            try:
                self.screen.set_focus(target_widget)
            except Exception:
                pass

        def _focus_widget_by_delta(self, delta: int) -> None:
            focused = self._focused_widget()
            panel_id = self._widget_panel_id(focused)
            widgets = self._panel_widgets(panel_id) if panel_id else []
            if not widgets:
                widgets = self._focusable_widgets_in_order()
            if not widgets:
                return
            try:
                current_index = widgets.index(focused) if focused in widgets else (-1 if delta > 0 else 0)
            except ValueError:
                current_index = -1 if delta > 0 else 0
            next_index = (current_index + delta) % len(widgets)
            try:
                self.screen.set_focus(widgets[next_index])
            except Exception:
                pass

        def _widget_is_open_or_editing(self, widget: Any | None) -> bool:
            if widget is None:
                return False
            try:
                if isinstance(widget, Input):
                    return True
            except Exception:
                pass
            for attr in ("expanded", "overlay_visible", "menu_open", "is_expanded"):
                try:
                    if bool(getattr(widget, attr)):
                        return True
                except Exception:
                    continue
            return False

        def action_focus_next_widget(self) -> None:
            self._focus_widget_by_delta(1)

        def action_focus_previous_widget(self) -> None:
            self._focus_widget_by_delta(-1)

        def action_focus_next_panel(self) -> None:
            self._focus_panel_by_delta(1)

        def action_focus_previous_panel(self) -> None:
            self._focus_panel_by_delta(-1)

        def action_move_up(self) -> None:
            panel_id = self._widget_panel_id(self._focused_widget())
            if panel_id == "sidebar-features":
                self.action_focus_previous_widget()
            elif panel_id in {"content-body", "job-input-panel"}:
                self.action_focus_previous_widget()

        def action_move_down(self) -> None:
            panel_id = self._widget_panel_id(self._focused_widget())
            if panel_id == "sidebar-features":
                self.action_focus_next_widget()
            elif panel_id in {"content-body", "job-input-panel"}:
                self.action_focus_next_widget()

        def action_move_left(self) -> None:
            panel_id = self._widget_panel_id(self._focused_widget())
            if panel_id == "general-tabs":
                self.action_focus_previous_widget()
            elif panel_id in {"content-body", "job-input-panel"}:
                self.action_focus_previous_widget()

        def action_move_right(self) -> None:
            panel_id = self._widget_panel_id(self._focused_widget())
            if panel_id == "general-tabs":
                self.action_focus_next_widget()
            elif panel_id in {"content-body", "job-input-panel"}:
                self.action_focus_next_widget()

        def _activate_focused_widget(self) -> bool:
            focused = self._focused_widget()
            if focused is None:
                self.action_focus_next_widget()
                return True
            if isinstance(focused, Button):
                try:
                    focused.press()
                    return True
                except Exception:
                    return False
            if isinstance(focused, Checkbox):
                try:
                    focused.value = not bool(getattr(focused, "value", False))
                    return True
                except Exception:
                    return False
            for method_name in ("action_show_overlay", "action_toggle_overlay", "action_expand", "action_open", "action_press"):
                method = getattr(focused, method_name, None)
                if callable(method):
                    try:
                        method()
                        return True
                    except Exception:
                        continue
            return False

        def _exit_focused_widget(self) -> bool:
            if self.context_menu_visible:
                self.hide_context_popup()
                return True
            focused = self._focused_widget()
            if focused is None:
                return False
            if isinstance(focused, Input):
                try:
                    self.screen.set_focus(None)
                    return True
                except Exception:
                    return False
            for method_name in ("action_dismiss", "action_hide_overlay", "action_collapse", "action_close"):
                method = getattr(focused, method_name, None)
                if callable(method):
                    try:
                        method()
                        return True
                    except Exception:
                        continue
            try:
                self.screen.set_focus(None)
                return True
            except Exception:
                return False

        def can_run_job(self) -> bool:
            return not self.job_starting and not (self.running_process is not None and self.running_process.poll() is None)

        def module_buttons(self) -> List[str]:
            return list(INTERACTIVE_MODULE_TAB_NAMES.keys())

        def can_stop_job(self) -> bool:
            return not self.job_starting and self.running_process is not None and self.running_process.poll() is None

        def can_exit_app(self) -> bool:
            return not self.job_starting and not self.can_stop_job()

        def _should_run_dashboard_fullscreen(self) -> bool:
            return self.active_module == "automatic_migration" and bool(self.state_values.get("dashboard"))

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

        def _reset_log_for_command(self, command: List[str]) -> None:
            self.running_command = command
            self.log_buffer.clear()
            self.log_history = []
            self.query_one("#log-panel", ExecutionLogView).clear()
            self.append_log(f"> {command_to_string(command)}")

        def _start_embedded_job(self, command: List[str]) -> None:
            self.job_starting = True
            self.update_status("Preparing job...")
            self.sync_content_panel_for_run_state(True)
            self.refresh_action_buttons()
            self.call_after_refresh(lambda: self._start_job_after_layout(command))

        def _confirm_dashboard_fullscreen_run(self) -> None:
            message = (
                "Live Dashboard is enabled for Automatic Migration.\n\n"
                "If you continue, the current Textual screen will temporarily switch to the Rich Live Dashboard "
                "for the duration of the process.\n\n"
                "When the migration finishes, PhotoMigrator will return automatically to the main TUI screen.\n\n"
                "Do you want to use the Live Dashboard for this run?"
            )
            self.push_screen(
                ConfirmActionScreen(
                    "Automatic Migration Live Dashboard",
                    message,
                    confirm_label="Use Live Dashboard",
                    cancel_label="Run Without Dashboard",
                ),
                callback=self.handle_dashboard_fullscreen_confirmation,
            )

        def handle_dashboard_fullscreen_confirmation(self, confirmed: bool) -> None:
            if confirmed:
                command = self._build_current_command(dashboard_enabled=True)
                self._reset_log_for_command(command)
                self.job_starting = True
                self.update_status("Launching full-screen dashboard...")
                self.refresh_action_buttons()
                self.call_after_refresh(lambda: self._run_dashboard_job_in_terminal(command))
                return
            command = self._build_current_command(dashboard_enabled=False)
            self._reset_log_for_command(command)
            self.append_log("[internal] Live Dashboard disabled for this run by user confirmation.")
            self.update_status("Running Automatic Migration without Live Dashboard.")
            self._start_embedded_job(command)

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
            try:
                send_button = self.query_one("#send-input-btn", Button)
                can_send = bool(str(self.query_one("#job-input", Input).value or "").strip())
                send_button.disabled = not can_send
                send_button.set_class(can_send, "is-enabled")
                send_button.set_class(not can_send, "is-disabled")
            except Exception:
                pass
            self.refresh_runtime_layout()

        def refresh_boolean_toggle(self, dest: str, value: bool) -> None:
            try:
                toggle_button = self.query_one(f"#bool-{dest}-toggle", Button)
                self._set_boolean_toggle_visual(toggle_button, bool(value))
            except Exception:
                pass

        def _set_boolean_toggle_visual(self, button: Button, value: bool) -> None:
            button.label = "(──◉)" if value else "(◉──)"
            button.set_class(bool(value), "-on")
            button.set_class(not bool(value), "-off")

        def apply_theme(self) -> None:
            for theme in ["ocean", "emerald", "sunset", "dark"]:
                self.set_class(False, f"theme-{theme}")
            self.set_class(True, f"theme-{self.selected_theme}")

        def update_status(self, text: str) -> None:
            self.current_status_text = str(text or "")
            self.query_one("#status-line", Static).update(self.current_status_text)

        def update_command_preview(self) -> None:
            if self.active_module == "upload_folder":
                self.current_command_preview_text = "Upload to Server is only available in the Web Interface."
                self.query_one("#command-preview", Static).update(self.current_command_preview_text)
                self.refresh_action_buttons()
                return
            selected_action = None
            if self.active_module in {"google_photos", "synology_photos", "immich_photos", "nextcloud_photos"}:
                selected_action = self.cloud_action_dest.get(self.active_module)
            elif self.active_module == "standalone_features":
                selected_action = self.standalone_action_dest
            command = build_full_command(self.cli_entrypoint, self.schema, self.active_module, self.state_values, selected_action)
            self.current_command_preview_text = command_preview_string(command)
            self.query_one("#command-preview", Static).update(self.current_command_preview_text)
            self.running_command = command
            self.refresh_action_buttons()

        def persist_ui_state(self, force: bool = False) -> None:
            if not self.remember_state and not force:
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

        async def on_key(self, event: events.Key) -> None:
            focused = self._focused_widget()
            if event.key == "enter":
                if isinstance(focused, Input) and str(getattr(focused, "id", "") or "") == "job-input":
                    self.action_send_job_input()
                    event.stop()
                    return
                if not isinstance(focused, Input) and self._activate_focused_widget():
                    event.stop()
                return
            if event.key == "escape":
                if self._exit_focused_widget():
                    event.stop()
                return
            if event.key in {"backspace", "delete"}:
                if not isinstance(focused, Input) and self._exit_focused_widget():
                    event.stop()
                return

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            button_id = event.button.id or ""
            if button_id.startswith("bool-"):
                payload = button_id.replace("bool-", "", 1)
                if payload.endswith("-toggle"):
                    dest = payload[: -len("-toggle")]
                    current_value = self.remember_state if dest == "remember-state" else bool(self.state_values.get(dest))
                    value = not bool(current_value)
                else:
                    try:
                        dest, mode = payload.rsplit("-", 1)
                    except ValueError:
                        dest, mode = "", ""
                    value = mode == "on" if dest and mode in {"on", "off"} else None
                if dest and value is not None:
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
            if button_id == "context-copy":
                self.action_copy_text()
                self.hide_context_popup()
                return
            if button_id == "context-paste":
                self.action_paste_text()
                self.hide_context_popup()
                return
            if button_id == "toggle-content-panel":
                self.toggle_panel("content")
                return
            if button_id == "toggle-description-panel":
                self.toggle_panel("description")
                return
            if button_id == "toggle-preview-panel":
                self.toggle_panel("preview")
                return
            if button_id == "toggle-log-panel":
                self.toggle_panel("log")
                return
            if button_id == "toggle-status-panel":
                self.toggle_panel("status")
                return
            if button_id == "save-config-btn":
                self.action_save_config()
                return
            if button_id == "load-config-btn":
                self.action_load_config()
                return
            if button_id == "save-ui-state-btn":
                self.action_save_ui_state()
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
                self.refresh_action_buttons()
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
            self.consume_log_output(f"{line}\n")

        def _render_log_line(self, line: str) -> Text:
            raw = str(line or "").replace("\ufe0f", "")
            try:
                text = Text.from_ansi(raw)
            except Exception:
                text = Text(raw)
            match = LOG_LEVEL_PREFIX_RE.match(text.plain)
            if not match:
                return text
            styles = {
                "VERBOSE": "dim cyan",
                "DEBUG": "bright_cyan",
                "INFO": "bright_white",
                "WARNING": "yellow",
                "ERROR": "bold red",
                "CRITICAL": "bold white on dark_red",
            }
            level_name = match.group(1)
            style = styles.get(level_name)
            if style:
                try:
                    text.stylize(style, 0, len(text.plain))
                except Exception:
                    pass
            return text

        def _write_log_line(self, line: str, *, scroll_end: bool | None = None) -> None:
            self.query_one("#log-panel", ExecutionLogView).write(self._render_log_line(line), scroll_end=scroll_end)

        def _log_view_dimensions(self) -> tuple[int, int]:
            width = 0
            height = 0
            try:
                active_widget = self.query_one("#log-panel")
                size = getattr(active_widget, "size", None)
                width = int(getattr(size, "width", 0) or 0)
                height = int(getattr(size, "height", 0) or 0)
            except Exception:
                pass
            if width > 0 and height > 0:
                return width, height
            try:
                container = self.query_one("#log-panel-container", Vertical)
                size = getattr(container, "size", None)
                width = max(width, int(getattr(size, "width", 0) or 0))
                height = max(height, int(getattr(size, "height", 0) or 0) - 2)
            except Exception:
                pass
            return max(1, width), max(1, height)

        def refresh_log_view(self) -> None:
            self.log_history = self.log_buffer.render_lines()
            lines = self.log_buffer.render_lines(include_partial=True)
            log = self.query_one("#log-panel", ExecutionLogView)
            if not lines:
                log.clear()
                return
            log.set_lines([self._render_log_line(line) for line in lines], scroll_end=True)

        def consume_log_output(self, text: str) -> None:
            update = self.log_buffer.append_text(text)
            if update.replaced_progress or update.partial_changed:
                self.refresh_log_view()
                return
            if not update.appended_lines:
                return
            self.log_history.extend(update.appended_lines)
            last_index = len(update.appended_lines) - 1
            for index, line in enumerate(update.appended_lines):
                self._write_log_line(line, scroll_end=index == last_index)

        def on_job_finished(self, return_code: int) -> None:
            self.job_starting = False
            self.update_status(f"Job finished with exit code {return_code}")
            self.running_process = None
            self.sync_content_panel_for_run_state(False)
            self.refresh_action_buttons()

        def _start_job_after_layout(self, command: List[str]) -> None:
            env = build_ui_subprocess_env(ui_mode="tui")
            log_width, log_height = self._log_view_dimensions()
            env["PHOTOMIGRATOR_TUI_LOG_WIDTH"] = str(log_width)
            env["PHOTOMIGRATOR_TUI_LOG_HEIGHT"] = str(log_height)
            env["COLUMNS"] = str(log_width)
            env["LINES"] = str(log_height)
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
                self.job_starting = False
                self.sync_content_panel_for_run_state(False)
                self.update_status(f"Unable to start job: {exc}")
                self.append_log(f"[internal] Unable to start job: {exc}")
                self.refresh_action_buttons()
                return
            self.running_process = process
            self.job_starting = False
            self.update_status("Job running...")
            self.refresh_action_buttons()
            threading.Thread(target=self._job_output_worker, args=(process,), daemon=True).start()

        def _run_dashboard_job_in_terminal(self, command: List[str]) -> None:
            env = build_ui_subprocess_env(ui_mode="tui", embedded_ui=False)
            try:
                with self.suspend():
                    return_code = subprocess.run(
                        command,
                        cwd=str(self.launch_cwd),
                        env=env,
                        check=False,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    ).returncode
            except Exception as exc:
                self.job_starting = False
                self.update_status(f"Unable to launch full-screen dashboard: {exc}")
                self.append_log(f"[internal] Full-screen dashboard launch failed: {exc}")
                self.refresh_action_buttons()
                return
            self.job_starting = False
            self.append_log(f"[internal] Full-screen dashboard finished with exit code {return_code}")
            self.update_status(f"Job finished with exit code {return_code}")
            self.refresh_action_buttons()

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
                            payload = "".join(pending)
                            pending = []
                            last_flush = now
                            self.call_from_thread(self.consume_log_output, payload)
                    if pending:
                        self.call_from_thread(self.consume_log_output, "".join(pending))
                return_code = process.wait()
            except Exception as exc:
                self.call_from_thread(self.append_log, f"[internal] {exc}")
                return_code = -1
            self.call_from_thread(self.on_job_finished, return_code)

        def action_run_job(self) -> None:
            if self.active_module == "upload_folder":
                self.update_status("Upload to Server is only available in the Web Interface.")
                return
            if self.job_starting or (self.running_process is not None and self.running_process.poll() is None):
                self.update_status("A job is already running.")
                return
            if self._should_run_dashboard_fullscreen():
                self.update_status("Waiting for Live Dashboard confirmation...")
                self.refresh_action_buttons()
                self._confirm_dashboard_fullscreen_run()
                return
            command = self._build_current_command()
            self._reset_log_for_command(command)
            self._start_embedded_job(command)

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
            self.push_screen(
                ConfirmActionScreen("Exit PhotoMigrator", "Are you sure you want to close the tool?", "Exit"),
                callback=self.handle_exit_confirmation,
            )

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
            target = self.current_config_path()
            self.push_screen(
                ConfirmActionScreen(
                    "Save Config",
                    f"This will save the current configuration editor values to:\n{target}",
                    "Save",
                ),
                callback=self.handle_save_config_confirmation,
            )

        def handle_save_config_confirmation(self, confirmed: bool) -> None:
            if not confirmed:
                self.update_status("Save Config canceled.")
                return
            target = self.current_config_path()
            save_config_editor_values(target, self.config_values, self.config_template_text, self.config_schema)
            self.update_status(f"Config.ini saved to {target}")

        def action_load_config(self) -> None:
            self.push_screen(
                PathPickerScreen(
                    dest="load-config-file",
                    title="Load Config",
                    subtitle="Select or type a .ini file to validate and load.",
                    start_path=str(self.current_config_path()),
                    home_path=self.launch_cwd,
                ),
                callback=self.handle_load_config_selection,
            )

        def handle_load_config_selection(self, result: Dict[str, str] | None) -> None:
            if not result:
                self.update_status("Load Config canceled.")
                return
            raw_path = str(result.get("path") or "").strip()
            if not raw_path:
                self.update_status("Load Config canceled: empty path.")
                return
            try:
                selected_path = validate_ui_config_file(Path(raw_path))
            except Exception as exc:
                self.update_status(f"Invalid config file: {exc}")
                return
            current_path = self.current_config_path()
            selected_text = selected_path.read_text(encoding="utf-8", errors="replace")
            current_text = current_path.read_text(encoding="utf-8", errors="replace") if current_path.exists() else ""
            try:
                if selected_path.samefile(current_path):
                    self.reload_config_model()
                    if self.active_general_tab == "features_config":
                        self.call_after_refresh(lambda: self.run_worker(self.rebuild_content()))
                    message = f"The selected config file is already the active file:\n{current_path}\n\nNo overwrite is needed because the content is the same."
                    self.push_screen(InfoMessageScreen("Load Config", message))
                    self.update_status(f"Selected config is already the active file: {current_path}")
                    return
            except Exception:
                pass
            if selected_text == current_text:
                message = (
                    "The selected config file has the same content as the current active config file.\n\n"
                    f"Current file:\n{current_path}\n\nSelected file:\n{selected_path}\n\nNo overwrite is needed."
                )
                self.push_screen(InfoMessageScreen("Load Config", message))
                self.update_status("Selected config has the same content as the current active config.")
                return
            message = f"This will overwrite the current configuration file:\n{current_path}\n\nwith the selected file:\n{selected_path}"
            self.push_screen(
                ConfirmActionScreen("Load Config", message, "Overwrite"),
                callback=lambda confirmed, src=selected_path: self.handle_load_config_confirmation(confirmed, src),
            )

        def handle_load_config_confirmation(self, confirmed: bool, source_path: Path) -> None:
            if not confirmed:
                self.update_status("Load Config canceled.")
                return
            target = self.current_config_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            self.reload_config_model()
            self.call_after_refresh(self._rebuild_features_config_if_needed)
            self.update_status(f"Loaded config from {source_path} into {target}")

        def _rebuild_features_config_if_needed(self) -> None:
            if self.active_general_tab == "features_config":
                self.run_worker(self.rebuild_content())

        def action_save_ui_state(self) -> None:
            self.push_screen(
                ConfirmActionScreen(
                    "Save UI State",
                    f"This will save the current terminal UI state to:\n{TUI_STATE_PATH}",
                    "Save",
                ),
                callback=self.handle_save_ui_state_confirmation,
            )

        def handle_save_ui_state_confirmation(self, confirmed: bool) -> None:
            if not confirmed:
                self.update_status("Save UI State canceled.")
                return
            self.persist_ui_state(force=True)
            self.update_status(f"UI state saved to {TUI_STATE_PATH}")


    def run_cli_tui(project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None) -> None:
        app = PhotoMigratorTUI(project_root=project_root, cli_entrypoint=cli_entrypoint, initial_values=initial_values)
        app.run()
else:
    def run_cli_tui(project_root: Path, cli_entrypoint: Path, initial_values: Dict[str, Any] | None = None) -> None:  # pragma: no cover - only used without textual
        raise RuntimeError(str(TEXTUAL_IMPORT_ERROR or "Textual is not installed"))
