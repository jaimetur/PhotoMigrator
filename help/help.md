# 📚 PhotoMigrator Help

## What is PhotoMigrator?
PhotoMigrator is a tool designed to:

- migrate photos and videos between services (for example Synology and Immich),
- process and fix Google Takeout exports,
- clean and manage media libraries (albums, filters, duplicates, etc.).

The web interface is a visual layer on top of the CLI: you choose options on screen and the tool builds/runs the command for you.

---

## Main Web Interface Areas

### 1. Top Header
- Tool name, tool version, tool description
- Quick links to: `Readme`, `Release Notes`, and `Help`.

### 2. General Panel
- Global arguments (logging, filters, paths,...).
- Configuration file editor.
- Theme selector

### 3. Feature Selector
- Main module selection:
  - Automatic Migration
  - Google Takeout
  - Synology Photos
  - Immich Photos
  - Other Features
- Includes `Live Command Preview` so you can verify the exact CLI command before execution.

### 4. Execution Output
- Real-time terminal output.
- Job status, logs, and interaction controls.

---

## Recommended Workflow
1. Configure accounts and credentials in `Config.ini`.
2. Review `General Arguments` (logs, shared filters, paths).
3. Select a module in `Feature Selector`.
4. Validate the generated command in `Command Preview`.
5. Run the module and monitor progress in `Execution Output`.

---

## Help Index

### Main Guides
- [CLI Overview](/docs/view/help/1-command-line-interface.md)
- [Configuration File](/docs/view/help/0-configuration-file.md)
- [Automatic Migration](/docs/view/help/3-automatic-migration.md)
- [Google Takeout](/docs/view/help/4-google-takeout.md)
- [Synology Photos](/docs/view/help/5-synology-photos.md)
- [Immich Photos](/docs/view/help/6-immich-photos.md)
- [Other Features](/docs/view/help/7-other-features.md)
- [Google Photos Takeout Helper (GPTH)](/docs/view/help/gpth_process_explanations/00_GPTH_complete_pipeline.md)

### Arguments Reference
- [Arguments Description (Short)](/docs/view/help/2-arguments-description-short.md)
- [Arguments Description (Full)](/docs/view/help/2-arguments-description.md)

---

> [!TIP]  
> - Start with `Automatic Migration` if your goal is full-library transfer.
> - For duplicate management, run non-destructive mode (`list`) first.
> - Create a backup before running modules that rename or remove files/albums.
