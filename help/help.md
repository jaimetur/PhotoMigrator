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

### Sign in and accounts
- Sign in with your username or with the email of your account. The site root (`/`) is the PhotoMigrator website; `Sign in` there, or `/app/`, opens the Web Interface. `Website` (and the logo) on the login page goes back to the website. The documentation (`/docs/view/help`, with the README and the release notes) can be read without an account; only the view of your own `Config.ini` needs to sign in. It is written in English: use the translate option of your browser to read it in your language.
- `Request an account` asks for a username, an email (required), a password and an optional message. The account stays inactive until an admin activates it (`Approve`) or rejects it (`Reject`) in the Administration Panel.
- When email is configured (`SMTP_*` variables or `Admin Panel > Email (SMTP)`), PhotoMigrator emails account requests to the admins and notices to the user when the request is received, the account is created, activated or disabled, the request is rejected or the password changes.
- Every account needs an email. Admins add or change it with `Email` in the users list.
- The Administration Panel (admins only) has one tab per section:
  - `Users`: every field is changed in place and saved on its own (email, new password, role, `Active`, `Must change password` and folders). The list shows the last sign-in and who is online, can be searched and filtered by role or status (including `Pending access requests`), and several users can be activated, deactivated, deleted or given a role at once. `New user` opens a form; the key button sets a temporary password (emailed to the user, or shown once to you when email is not configured); approving a request is switching `Active` on.
  - `Email (SMTP)`: server, account and sender of the emails, and a test email. The saved password is never shown; leave the field empty to keep it.
  - `Database`: pick a table, filter any column by its values, edit a row in place and save it with ✓, delete it with × or add one with `Add row`.
  - `Backups`: stored backups, size, free space, last and next backup; `Back up now`, download, delete or restore a backup (the current data is saved first as a pre-restore backup), and recurring backups (hourly, every 4 hours, daily, weekly or monthly, at a chosen time, keeping the scheduled backups of the last N days; backups made with `Back up now` are never deleted automatically).
  - `Access logs`: sign-ins, failed sign-ins and the changes made from the Administration Panel, filtered by period, user and event.
  - `Cloud service`: turns the cloud service on, sets its prices and limits, the Stripe keys and the Dropbox and OneDrive apps, and lists every task with its payment and state (see [Cloud service](13-cloud-service.md)).
- Choose the language of the interface (and of your emails) with the language picker on the login page, next to your user in the sidebar, or in the Administration Panel. By default the Web Interface uses the language of your browser.

### 1. Sidebar
- `Home` and every feature grouped by task:
  - **Migrate:** Automatic Migration
  - **Process Takeout:** Google Takeout, iCloud Takeout
  - **Photo libraries:** Google Photos, Synology Photos, Immich Photos, NextCloud Photos, Local Photos Folder
  - **Tools:** Other Features, Upload to Server
- `Cloud service > My tasks` when the server offers the cloud service: migrations and Takeout processing that run on the server, with resumable uploads, quote, payment, progress and download (see [Cloud service](13-cloud-service.md)).
- `Activity` (with a `Running` badge while a job runs) and `Settings`.
- Links to `Help`, `Readme`, `Release Notes` and `Roadmap`, your user, the `Admin Panel` (admins only) and `Logout`.
- On a phone, the sidebar opens from the menu button in the top bar.

### 2. Home
- Asks "What do you want to move today?" and shows a `Start a migration` shortcut with the source and target of your last Automatic Migration, and the state of the job linked to your session (with a link to `Activity`).
- `Libraries & tools` shows a card for every feature, each with its own colour and icon.
- The three steps to get started and a few quick tools.

### 3. Feature pages
- A header in the colour of the feature with its name, a short description and `Restore defaults`.
- For photo libraries and Other Features, a visual action picker grouped by purpose (for example Transfer, Organize and Clean up).
- Numbered option cards with plain-language labels, a short help text and the CLI flag of each field. Advanced options are collapsed.
- An `About` card for the selected feature or action: a short summary, the details as a list, an example, the options you need and a one-line description of each optional one. A warning card is added for actions that delete or change data.
- A run panel with the live `Command` preview, a copy button, `Email me when it finishes`, `Run` and `Stop`, at the top of the right-hand column on wide screens and as a bar at the bottom on smaller screens. With `Email me when it finishes` on, you get an email with the result, the duration and the last lines of the log when the task ends (it needs an email in your account and email configured on the server).

### 4. Activity
- Status, start time, elapsed time and last update of the current or last job.
- The executed command, the Automatic Migration live dashboard and the real-time log.
- `Process input` to answer the questions a running job asks (`Send`, `Yes`, `No`).

### 5. Settings
- `Service credentials`: one entry per service with its configured accounts, account tabs and import/export of the configuration.
- `General arguments`: global arguments in four sections chosen from a side menu (`Filters`, `Logs`, `Execution`, `Folders`); a dot marks the sections changed from the default. Each option shows its name, a one-line help and its control. `Filters` has a date range, an `All / Photos / Videos` selector, country, city and person, and the excluded folders and files as removable chips. Changes are saved automatically; `Restore defaults` resets them and `Show CLI flags` shows the command-line flag of each option.
- `App settings`: theme (four previews), time zone (searchable, with the current time in that zone) and language. Changes are applied and saved at once.

---

## Recommended Workflow
1. Add the URL and credentials of each account in `Settings > Service credentials` (or through supported environment variables if you run the Web Interface in Docker/Compose/Kubernetes).
2. Review `Settings > General arguments` (logs, shared filters, paths).
3. Choose a task from `Home` or the sidebar.
4. Validate the generated command in the `Command` preview of the run panel.
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
