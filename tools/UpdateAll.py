#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date
from enum import Enum
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_VARS_PATH = ROOT / "src" / "Core" / "GlobalVariables.py"
DOWNLOAD_SCRIPT = ROOT / "tools" / "UpdateDownloadLinks.py"
CLI_DOC_PATH = ROOT / "help" / "01-command-line-interface.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
VERSION_DATE_PATHS = (GLOBAL_VARS_PATH, CLI_DOC_PATH, CHANGELOG_PATH)


class DirtyTreeAction(Enum):
    """Available ways to handle uncommitted work before creating a release branch."""

    COMMIT_AND_PUSH = "commit_and_push"
    CARRY_TO_NEW_BRANCH = "carry_to_new_branch"
    DISCARD = "discard"
    CANCEL = "cancel"


class GitCommandError(RuntimeError):
    """Raised when a Git command cannot be completed."""


def run_git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run Git in the project root and return its completed process."""
    result = subprocess.run(
        ["git", *arguments],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unknown Git error."
        raise GitCommandError(f"git {' '.join(arguments)} failed:\n{detail}")
    return result


def current_branch() -> str:
    """Return the checked-out branch, failing clearly for a detached HEAD."""
    result = run_git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise GitCommandError("A named Git branch must be checked out before creating a release.")
    return result.stdout.strip()


def working_tree_changes() -> str:
    """Return porcelain status for tracked, staged and untracked files."""
    return run_git("status", "--porcelain=v1").stdout.rstrip()


def ensure_release_branch_is_available(branch: str) -> None:
    """Ensure a release branch does not already exist locally or on origin."""
    run_git("check-ref-format", "--branch", branch)
    local = run_git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    if local.returncode == 0:
        raise GitCommandError(f"Local branch {branch!r} already exists.")
    if local.returncode != 1:
        raise GitCommandError(f"Unable to check whether local branch {branch!r} exists.")

    run_git("remote", "get-url", "origin")
    remote = run_git("ls-remote", "--exit-code", "--heads", "origin", branch, check=False)
    if remote.returncode == 0:
        raise GitCommandError(f"Remote branch origin/{branch} already exists.")
    if remote.returncode != 2:
        detail = remote.stderr.strip() or remote.stdout.strip() or "Unknown Git error."
        raise GitCommandError(f"Unable to check origin/{branch}:\n{detail}")


def prepare_working_tree(action: DirtyTreeAction, source_branch: str, version: str) -> None:
    """Apply the selected policy to pending work on the source branch."""
    if action is DirtyTreeAction.COMMIT_AND_PUSH:
        run_git("add", "--all")
        run_git("commit", "-m", f"Save work before creating release v{version}")
        run_git("push", "origin", f"HEAD:refs/heads/{source_branch}")
    elif action is DirtyTreeAction.DISCARD:
        run_git("reset", "--hard", "HEAD")
        run_git("clean", "-fd")
    elif action is DirtyTreeAction.CANCEL:
        raise RuntimeError("Release creation cancelled.")


def create_release(version: str, release_date: str, dirty_action: DirtyTreeAction) -> None:
    """Create the X.Y.Z release branch, apply version/date and download links, then commit and push it."""
    source_branch = current_branch()
    ensure_release_branch_is_available(version)

    if working_tree_changes():
        prepare_working_tree(dirty_action, source_branch, version)

    print(f"Creating release branch {version} from {source_branch}...")
    run_git("switch", "--create", version)
    apply_version_date(version, release_date)
    run_script(DOWNLOAD_SCRIPT)

    run_git("add", "--all")
    run_git("commit", "-m", f"Create release v{version}")
    print(f"Pushing branch {version} to origin...")
    run_git("push", "--set-upstream", "origin", version)
    print(f"Release v{version} was committed and pushed to origin/{version}.")


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


def write_cli_doc_version_date(new_version: str, new_date: str) -> None:
    content = CLI_DOC_PATH.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"^PhotoMigrator v\d+\.\d+\.\d+ - \d{4}-\d{2}-\d{2}$",
        f"PhotoMigrator v{new_version} - {new_date}",
        content,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError(
            "Unable to update version/date in help/01-command-line-interface.md"
        )
    CLI_DOC_PATH.write_text(updated, encoding="utf-8")


def write_changelog_release_date(new_version: str, new_date: str) -> None:
    """Set the release date of the CHANGELOG section of the given version, when that section exists."""
    content = CHANGELOG_PATH.read_text(encoding="utf-8")
    updated, count = re.subn(
        rf"^(## Release: v{re.escape(new_version)}[ \t]*\r?\n### Release Date:[ \t]*)\S.*$",
        rf"\g<1>{new_date}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        print(f"WARNING: CHANGELOG.md has no 'Release: v{new_version}' section; its release date was not updated.")
        return
    if updated != content:
        CHANGELOG_PATH.write_text(updated, encoding="utf-8")


def apply_version_date(new_version: str, new_date: str) -> None:
    """Write the version/date everywhere it is shown: GlobalVariables.py, the CLI help and the CHANGELOG."""
    print(f"Updating TOOL_VERSION_WITHOUT_V and TOOL_DATE to: {new_version} - {new_date}...")
    write_version_date(GLOBAL_VARS_PATH.read_text(encoding="utf-8"), new_version, new_date)
    write_cli_doc_version_date(new_version, new_date)
    write_changelog_release_date(new_version, new_date)


def download_link_paths() -> tuple[Path, ...]:
    """Files rewritten by UpdateDownloadLinks.py."""
    sys.path.insert(0, str(DOWNLOAD_SCRIPT.parent))
    try:
        import UpdateDownloadLinks  # noqa: E402 - tools/ is not a package
    finally:
        sys.path.pop(0)
    return tuple(UpdateDownloadLinks.FILES_TO_UPDATE)


def commit_and_push(paths: tuple[Path, ...], message: str) -> str:
    """Commit only the given files (other pending work is left untouched) and push them to the current branch."""
    branch = current_branch()
    relative = [str(path.relative_to(ROOT)) for path in paths if path.exists()]
    run_git("add", "--", *relative)
    if run_git("diff", "--cached", "--quiet", "--", *relative, check=False).returncode == 0:
        print("Nothing changed; nothing to commit.")
        return "Nothing changed, so nothing was committed or pushed."
    run_git("commit", "-m", message, "--", *relative)
    print(f"Pushing to origin/{branch}...")
    run_git("push", "origin", f"HEAD:refs/heads/{branch}")
    return f"The changes were committed and pushed to origin/{branch}."


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


def ask_dirty_tree_action(parent: tk.Misc, changes: str) -> DirtyTreeAction:
    """Ask how pending work should be handled and return the selected action."""
    selection = DirtyTreeAction.CANCEL
    dialog = tk.Toplevel(parent)
    dialog.title("Uncommitted changes found")
    dialog.geometry("820x430")
    dialog.minsize(620, 360)
    dialog.transient(parent)
    dialog.grab_set()

    frame = tk.Frame(dialog, padx=18, pady=18)
    frame.pack(fill="both", expand=True)
    tk.Label(
        frame,
        text="Choose what to do with the current branch changes before creating the release:",
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(0, 10))

    status = tk.Text(frame, height=10, wrap="none")
    status.insert("1.0", changes)
    status.configure(state="disabled")
    status.pack(fill="both", expand=True, pady=(0, 14))

    tk.Label(
        frame,
        text="Discard permanently resets tracked files and removes untracked files.",
        anchor="w",
        fg="#9a3412",
    ).pack(fill="x", pady=(0, 10))

    def choose(action: DirtyTreeAction) -> None:
        nonlocal selection
        selection = action
        dialog.destroy()

    actions = tk.Frame(frame)
    actions.pack(fill="x")
    tk.Button(actions, text="Cancel", command=lambda: choose(DirtyTreeAction.CANCEL)).pack(side="right")
    tk.Button(actions, text="Discard Changes", command=lambda: choose(DirtyTreeAction.DISCARD)).pack(
        side="right", padx=(0, 8)
    )
    tk.Button(
        actions,
        text="Carry to New Branch",
        command=lambda: choose(DirtyTreeAction.CARRY_TO_NEW_BRANCH),
    ).pack(side="right", padx=(0, 8))
    tk.Button(
        actions,
        text="Commit and Push Current Branch",
        command=lambda: choose(DirtyTreeAction.COMMIT_AND_PUSH),
    ).pack(side="right", padx=(0, 8))

    dialog.protocol("WM_DELETE_WINDOW", lambda: choose(DirtyTreeAction.CANCEL))
    parent.wait_window(dialog)
    return selection


def main() -> None:
    current_version, current_date, _ = read_version_date()

    root = tk.Tk()
    root.title("Update PhotoMigrator (Version/Date, Download Links, Release)")
    dialog_width = 900 if sys.platform == "darwin" else 780
    dialog_height = 240 if sys.platform == "darwin" else 220
    root.geometry(f"{dialog_width}x{dialog_height}")
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
        try:
            date.fromisoformat(new_date)
        except ValueError:
            messagebox.showerror("Invalid date", "TOOL_DATE is not a valid calendar date", parent=root)
            return None
        return new_version, new_date

    def apply_version_date_from_inputs() -> tuple[str, str] | None:
        validated = validate_inputs()
        if not validated:
            return None
        new_version, new_date = validated
        apply_version_date(new_version, new_date)
        return new_version, new_date

    def publish(paths: tuple[Path, ...], message: str) -> bool:
        try:
            result = commit_and_push(paths, message)
        except Exception as exc:
            messagebox.showerror("Git commit/push failed", f"The files were updated but not pushed.\n\n{exc}", parent=root)
            return False
        messagebox.showinfo("Changes pushed", result, parent=root)
        return True

    def on_update_version_date() -> None:
        clear_console()
        applied = apply_version_date_from_inputs()
        if not applied:
            return
        if publish(VERSION_DATE_PATHS, f"Update version/date to v{applied[0]} ({applied[1]})"):
            root.destroy()

    def on_update_download_links() -> None:
        clear_console()
        try:
            run_script(DOWNLOAD_SCRIPT)
            paths = download_link_paths()
        except Exception as exc:
            messagebox.showerror("Script execution error", str(exc), parent=root)
            return
        if publish(paths, "Update download links"):
            root.destroy()

    def on_update_all() -> None:
        clear_console()
        applied = apply_version_date_from_inputs()
        if not applied:
            return
        try:
            run_script(DOWNLOAD_SCRIPT)
            paths = VERSION_DATE_PATHS + download_link_paths()
        except Exception as exc:
            messagebox.showerror("Script execution error", str(exc), parent=root)
            return
        if publish(paths, f"Update version/date to v{applied[0]} ({applied[1]}) and download links"):
            root.destroy()

    def on_create_release() -> None:
        clear_console()
        validated = validate_inputs()
        if not validated:
            return
        new_version, new_date = validated
        try:
            changes = working_tree_changes()
        except Exception as exc:
            messagebox.showerror("Git check failed", str(exc), parent=root)
            return

        action = DirtyTreeAction.CARRY_TO_NEW_BRANCH
        if changes:
            action = ask_dirty_tree_action(root, changes)
            if action is DirtyTreeAction.CANCEL:
                return

        try:
            create_release(new_version, new_date, action)
        except Exception as exc:
            messagebox.showerror("Release creation failed", str(exc), parent=root)
            return

        messagebox.showinfo(
            "Release created",
            f"Release v{new_version} was committed and pushed to origin/{new_version}.",
            parent=root,
        )
        root.destroy()

    buttons = tk.Frame(frame)
    buttons.pack(fill="x")
    tk.Button(buttons, text="Cancel", command=root.destroy).pack(side="right", padx=(8, 0))
    tk.Button(buttons, text="Update Version/Date", command=on_update_version_date).pack(side="left")
    tk.Button(buttons, text="Update Download Links", command=on_update_download_links).pack(side="left", padx=(8, 0))
    tk.Button(buttons, text="Create New Release", command=on_create_release).pack(side="right", padx=(8, 0))
    tk.Button(buttons, text="Update All", command=on_update_all).pack(side="right")

    center_window(root)
    root.mainloop()


if __name__ == "__main__":
    main()
