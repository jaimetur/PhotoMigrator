# .github/update_version_dropdown.py

import requests
import yaml
from pathlib import Path

# CONFIGURACIÓN
REPO = "jaimeturg/PhotoMigrator"
DROPDOWN_ID = "version"
MAX_RELEASES = 50

YAML_FILES = [
    Path(".github/ISSUE_TEMPLATE/bug_form.yml"),
    Path(".github/ISSUE_TEMPLATE/feature_request.yml"),
]

def get_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()[:MAX_RELEASES]

def format_versions(releases):
    options = []
    latest = releases[0]
    latest_is_prerelease = latest["prerelease"]

    if latest_is_prerelease:
        options.append(f'{latest["tag_name"]} (latest)')
        stable = next((r for r in releases[1:] if not r["prerelease"]), None)
        if stable:
            options.append(f'{stable["tag_name"]} (latest-stable)')
    else:
        options.append(f'{latest["tag_name"]} (latest-stable)')

    added_tags = {r.split()[0] for r in options}
    for r in releases:
        tag = r["tag_name"]
        if tag not in added_tags:
            options.append(tag)
            added_tags.add(tag)

    return options

def update_file(yaml_path, dropdown_id, options):
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)

    modified = False
    fields = content.get("body") or content.get("on", {}).get("workflow_dispatch", {}).get("inputs") or []

    if isinstance(fields, dict):  # workflow_dispatch.inputs
        for key, val in fields.items():
            if key == dropdown_id or val.get("label", "").lower() == "version":
                val["options"] = options
                modified = True
    elif isinstance(fields, list):  # issue form
        for field in fields:
            if isinstance(field, dict) and field.get("id") == dropdown_id:
                field["attributes"]["options"] = options
                modified = True

    if modified:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, sort_keys=False, allow_unicode=True)

    return modified

if __name__ == "__main__":
    releases = get_releases(REPO)
    options = format_versions(releases)

    updated_files = []
    for yaml_file in YAML_FILES:
        if update_file(yaml_file, DROPDOWN_ID, options):
            updated_files.append(str(yaml_file))

    if updated_files:
        print("✅ Archivos actualizados:")
        for f in updated_files:
            print(f"- {f}")
        print("\n📌 Últimas versiones insertadas:")
        for opt in options:
            print(f"- {opt}")
    else:
        print("ℹ️ No hubo cambios en los archivos YAML.")
