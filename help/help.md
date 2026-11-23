# 📚 PhotoMigrator Help

## What is PhotoMigrator?
PhotoMigrator is a tool designed to:

- migrate photos and videos between services (for example Synology and Immich),
- process and fix Google Takeout exports,
- process and fix iCloud Photos exports,
- clean and manage media libraries (albums, filters, duplicates, etc.).

The web interface is a visual layer on top of the CLI: you choose options on screen and the tool builds/runs the command for you.

---

## Main Web Interface Areas

### 1. Sidebar
- `Home` and every feature grouped by task:
  - **Migrate:** Automatic Migration
  - **Process Takeout:** Google Takeout, iCloud Takeout
  - **Photo libraries:** Google Photos, Synology Photos, Immich Photos, NextCloud Photos, Local Photos Folder
  - **Tools:** Other Features, Upload to Server
- `Activity` (with a `Running` badge while a job runs) and `Settings`.
- Links to `Help`, `Readme`, `Release Notes` and `Roadmap`, your user, the `Admin Panel` (admins only) and `Logout`.
- On a phone, the sidebar opens from the menu button in the top bar.

### 2. Home
- Asks "What would you like to do today?" and lists the tasks as cards.
- Shows the three steps to get started and a shortcut to `Activity`.

### 3. Feature pages
- A header with the feature name, a short description and `Restore defaults`.
- For photo libraries and Other Features, a visual action picker grouped by purpose (for example Transfer, Organize and Clean up).
- Numbered option cards with plain-language labels, a short help text and the CLI flag of each field. Advanced options are collapsed.
- An `About` card with the full description of the selected feature or action, and a warning card for actions that delete or change data.
- A run bar at the bottom with the live `Command` preview, a copy button, `Run` and `Stop`.

### 4. Activity
- Status, start time, elapsed time and last update of the current or last job.
- The executed command, the Automatic Migration live dashboard and the real-time log.
- `Process input` to answer the questions a running job asks (`Send`, `Yes`, `No`).

### 5. Settings
- `Service credentials`: one entry per service with its configured accounts, account tabs and import/export of the configuration.
- `General arguments`: global arguments (logs, execution, folder names and filters).
- `App settings`: theme and time zone.

---

## Recommended Workflow
1. Add the URL and credentials of each account in `Settings > Service credentials` (or through supported environment variables if you run the Web Interface in Docker/Compose/Kubernetes).
2. Review `Settings > General arguments` (logs, shared filters, paths).
3. Choose a task from `Home` or the sidebar.
4. Validate the generated command in the `Command` preview of the run bar.
5. Press `Run` and follow the progress in `Activity`.

---

## Help Index

### Main Guides
- [CLI Overview](01-command-line-interface.md)
- [Configuration File](00-configuration-file.md)
- [Docker CLI Execution](docker-deployments/deploy-cli-interface-from-docker.md)
- [Web Interface from Docker](docker-deployments/deploy-web-interface-from-docker.md)
- [Automatic Migration](03-automatic-migration.md)
- [Google Takeout](04-google-takeout.md)
- [iCloud Takeout](05-icloud-takeout.md)
- [Google Photos](06-google-photos.md)
- [Synology Photos](07-synology-photos.md)
- [Immich Photos](08-immich-photos.md)
- [NextCloud Photos](09-nextcloud-photos.md)
- [Local Photos Folder](10-local-photos-folder.md)
- [Other Features](10-other-features.md)
- [Google Photos Takeout Helper (GPTH)](11-GPTH-complete-pipeline.md)
- [Docker Deployment](12-docker-deployment.md)

### Arguments Reference
- [Arguments Description (Short)](02-arguments-description-short.md)
- [Arguments Description (Full)](02-arguments-description.md)

---

> [!TIP]  
> - Start with `Automatic Migration` if your goal is full-library transfer.
> - If the source library is Google Photos, export it with `Google Takeout` first; direct full-library reads from Google Photos are no longer available through the public API.
> - For duplicate management, run non-destructive mode (`list`) first.
> - Create a backup before running modules that rename or remove files/albums.
