#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_VARS_PATH = ROOT / "src" / "Core" / "GlobalVariables.py"
DOWNLOAD_SCRIPT = ROOT / "tools" / "UpdateDownloadLinks.py"


def read_version_date() -> tuple[str, str, str]:
    content = GLOBAL_VARS_PATH.read_text(encoding="utf-8")
    version_match = re.search(r'^(TOOL_VERSION_WITHOUT_V\s*=\s*")([^"]+)(")', content, flags=re.MULTILINE)
    date_match = re.search(r'^(TOOL_DATE\s*=\s*")([^"]+)(")', content, flags=re.MULTILINE)
    if not version_match or not date_match:
        raise RuntimeError("Unable to find TOOL_VERSION_WITHOUT_V and/or TOOL_DATE in src/Core/GlobalVariables.py")
    return version_match.group(2), date_match.group(2), content


def write_version_date(content: str, new_version: str, new_date: str) -> str:
    updated = re.sub(
        r'^(TOOL_VERSION_WITHOUT_V\s*=\s*")[^"]+(")',
        rf'\g<1>{new_version}\2',
        content,
        flags=re.MULTILINE,
    )
    updated = re.sub(
        r'^(TOOL_DATE\s*=\s*")[^"]+(")',
        rf'\g<1>{new_date}\2',
        updated,
        flags=re.MULTILINE,
    )
    GLOBAL_VARS_PATH.write_text(updated, encoding="utf-8")
    return updated


def center_window(win: tk.Tk) -> None:
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max((sw - w) // 2, 0)
    y = max((sh - h) // 2, 0)
    win.geometry(f"{w}x{h}+{x}+{y}")


def clear_console() -> None:
    try:
        if sys.stdout.isatty():
            os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def run_script(path: Path, *args: str) -> None:
    result = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"{path.name} failed (exit code {result.returncode}). Check console output above.")


def main() -> None:
    current_version, current_date, _ = read_version_date()

    root = tk.Tk()
    root.title("Update PhotoMigrator Version/Date")
    root.geometry("640x220")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text=f"Current TOOL_VERSION_WITHOUT_V: {current_version}", anchor="w").pack(fill="x")
    tk.Label(frame, text=f"Current TOOL_DATE: {current_date}", anchor="w").pack(fill="x", pady=(0, 12))

    tk.Label(frame, text="New TOOL_VERSION_WITHOUT_V (X.Y.Z):", anchor="w").pack(fill="x")
    version_var = tk.StringVar(value=current_version)
    tk.Entry(frame, textvariable=version_var).pack(fill="x", pady=(0, 10))

    tk.Label(frame, text="New TOOL_DATE (YYYY-MM-DD):", anchor="w").pack(fill="x")
    date_var = tk.StringVar(value=current_date)
    tk.Entry(frame, textvariable=date_var).pack(fill="x", pady=(0, 12))

    def validate_inputs() -> tuple[str, str] | None:
        new_version = version_var.get().strip()
        new_date = date_var.get().strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", new_version):
            messagebox.showerror("Invalid version", "TOOL_VERSION_WITHOUT_V must match X.Y.Z", parent=root)
            return None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", new_date):
            messagebox.showerror("Invalid date", "TOOL_DATE must match YYYY-MM-DD", parent=root)
            return None
        return new_version, new_date

    def apply_version_date_from_inputs() -> tuple[str, str] | None:
        validated = validate_inputs()
        if not validated:
            return None
        new_version, new_date = validated
        print(f"Updating TOOL_VERSION_WITHOUT_V and TOOL_DATE to: {new_version} - {new_date}...")
        fresh = GLOBAL_VARS_PATH.read_text(encoding="utf-8")
        write_version_date(fresh, new_version, new_date)
        return new_version, new_date

    def on_update_version_date() -> None:
        clear_console()
        applied = apply_version_date_from_inputs()
        if not applied:
            return
        root.destroy()

    def on_update_download_links() -> None:
        clear_console()
        try:
            run_script(DOWNLOAD_SCRIPT)
        except Exception as exc:
            messagebox.showerror("Script execution error", str(exc), parent=root)
            return
        root.destroy()

    def on_update_all() -> None:
        clear_console()
        applied = apply_version_date_from_inputs()
        if not applied:
            return
        try:
            run_script(DOWNLOAD_SCRIPT)
        except Exception as exc:
            messagebox.showerror("Script execution error", str(exc), parent=root)
            return
        root.destroy()

    buttons = tk.Frame(frame)
    buttons.pack(fill="x")
    tk.Button(buttons, text="Cancel", command=root.destroy).pack(side="right", padx=(8, 0))
    tk.Button(buttons, text="Update Version/Date", command=on_update_version_date).pack(side="left")
    tk.Button(buttons, text="Update Download Links", command=on_update_download_links).pack(side="left", padx=(8, 0))
    tk.Button(buttons, text="Update All", command=on_update_all).pack(side="right")

    center_window(root)
    root.mainloop()


if __name__ == "__main__":
    main()

