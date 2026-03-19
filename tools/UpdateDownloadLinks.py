#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update release/version links in project docs using the current PhotoMigrator version
from src/Core/GlobalVariables.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_VARS_PATH = ROOT / "src" / "Core" / "GlobalVariables.py"
FILES_TO_UPDATE = [
    ROOT / "DOWNLOAD.md",
    ROOT / "README.md",
    ROOT / "help" / "execution" / "execution-from-docker.md",
]


def read_tool_version_tag() -> str:
    if not GLOBAL_VARS_PATH.exists():
        raise FileNotFoundError(f"Missing file: {GLOBAL_VARS_PATH}")

    content = GLOBAL_VARS_PATH.read_text(encoding="utf-8")
    match = re.search(r'^\s*TOOL_VERSION_WITHOUT_V\s*=\s*"([^"]+)"\s*$', content, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("Unable to find TOOL_VERSION_WITHOUT_V in src/Core/GlobalVariables.py")
    return f"v{match.group(1).strip()}"


def update_release_links(content: str, tool_version: str) -> tuple[str, int]:
    version_re = r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z\.]+)?"
    total_replacements = 0
    updated = content

    # Release path segment: .../releases/download/vX.Y.Z/...
    pattern_release_path = re.compile(rf"/{version_re}/")
    updated, n1 = pattern_release_path.subn(f"/{tool_version}/", updated)
    total_replacements += n1

    # Artifact filenames: ..._vX.Y.Z_...
    pattern_filename = re.compile(rf"_({version_re})")
    updated, n2 = pattern_filename.subn(f"_{tool_version}", updated)
    total_replacements += n2

    # README pre-release download badge: .../downloads/.../vX.Y.Z/total
    pattern_badge = re.compile(rf"(github/downloads/[^/\s]+/){version_re}(/total)")
    updated, n3 = pattern_badge.subn(rf"\1{tool_version}\2", updated)
    total_replacements += n3

    return updated, total_replacements


def main() -> int:
    try:
        tool_version = read_tool_version_tag()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Updating download links to version: {tool_version}")
    total_changed_files = 0
    total_replacements = 0

    for path in FILES_TO_UPDATE:
        if not path.exists():
            print(f"  - Skipping missing file: {path}")
            continue
        original = path.read_text(encoding="utf-8")
        updated, count = update_release_links(original, tool_version)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            total_changed_files += 1
            total_replacements += count
            print(f"  - Updated: {path} ({count} replacements)")
        else:
            print(f"  - No changes: {path}")

    print(f"Done. Changed files: {total_changed_files}, total replacements: {total_replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

