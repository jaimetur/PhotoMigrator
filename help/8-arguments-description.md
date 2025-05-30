### 🔧 Core Arguments

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--help` | — | flag | — | Displays the help message and exits.
| `--version` | — | flag | — | Shows the tool version and exits.

### 🔄 Automatic Migration

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--source` | `<SOURCE>` | path / string | [existing path, synology, immich] | Defines the source for the automatic migration process.
| `--target` | `<TARGET>` | path / string | [existing path, synology, immich] | Defines the target for the automatic migration process.
| `--move-assets` | `<bool>` | bool | [true, false] (default: false) | Moves assets instead of copying them.
| `--dashboard` | `<bool>` | bool | [true, false] (default: true) | Enables the live dashboard during migration.
| `--parallel-migration` | `<bool>` | bool | [true, false] (default: true) | Enables parallel asset migration.

### ⚙️ General Options

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--input-folder` | `<INPUT_FOLDER>` | path | — | Folder containing assets to be processed.
| `--output-folder` | `<OUTPUT_FOLDER>` | path | — | Folder where processed assets or results will be saved.
| `--client` | `<CLIENT>` | string | [google-takeout, synology, immich] | Specifies the service to interact with.
| `--account-id` | `<ID>` | int | [1, 2, 3] (default: 1) | ID of the configured account in Config.ini.
| `--one-time-password` | — | flag | — | Enables OTP login for Synology (2FA).
| `--filter-from-date` | `<FROM_DATE>` | date | — | Filters assets from this date onward.
| `--filter-to-date` | `<TO_DATE>` | date | — | Filters assets up to this date.
| `--filter-by-country` | `<COUNTRY>` | string | — | Filters assets by country.
| `--filter-by-city` | `<CITY>` | string | — | Filters assets by city.
| `--filter-by-person` | `<PERSON>` | string | — | Filters assets by person name.
| `--filter-by-type` | `<TYPE>` | string | [image, video, all] (default: all) | Filters assets by type.
| `--albums-folders` | `<ALBUMS_FOLDER>` | path | — | Creates albums for subfolders inside.
| `--remove-albums-assets` | — | flag | — | Removes assets inside albums when albums are removed.
| `--no-log-file` | — | flag | — | Disables writing to log file.
| `--log-level` | `<LEVEL>` | string | [debug, info, warning, error] | Sets logging verbosity.

### 📦 Google Takeout Management

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--google-takeout` | `<TAKEOUT_FOLDER>` | path | — | Path to the Takeout folder to process.
| `--google-output-folder-suffix` | `<SUFFIX>` | string | (default: processed) | Suffix for the output folder.
| `--google-albums-folders-structure` | `<STRUCTURE>` | string | [flatten, year, year/month, year-month] (default: flatten) | Folder structure for Albums.
| `--google-no-albums-folder-structure` | `<STRUCTURE>` | string | [flatten, year, year/month, year-month] (default: year/month) | Folder structure for No-Albums.
| `--google-create-symbolic-albums` | — | flag | — | Creates symlinks for albums instead of duplicating files.
| `--google-ignore-check-structure` | — | flag | — | Ignores structure check of Takeout folders.
| `--google-move-takeout-folder` | — | flag | — | Moves original assets to output (risk of loss).
| `--google-remove-duplicates-files` | — | flag | — | Removes duplicate files in the output folder.
| `--google-skip-extras-files` | — | flag | — | Skips extra Google photos like edited/effects.
| `--google-skip-move-albums` | — | flag | — | Skips moving albums to 'Albums' folder.
| `--google-skip-gpth-tool` | — | flag | — | Skips GPTH tool processing (not recommended).
| `--show-gpth-info` | `<bool>` | bool | [true, false] (default: false) | Show GPTH progress messages.
| `--show-gpth-errors` | `<bool>` | bool | [true, false] (default: true) | Show GPTH error messages.

### 🖼️ Synology / Immich Management

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--upload-albums` | `<ALBUMS_FOLDER>` | path | — | Uploads albums from folders to the selected photo client.
| `--download-albums` | `<ALBUM_NAMES>` | list | — | Downloads albums by name to the output folder.
| `--upload-all` | `<INPUT_FOLDER>` | path | — | Uploads all assets and creates albums by subfolder.
| `--download-all` | `<OUTPUT_FOLDER>` | path | — | Downloads all albums and assets to this folder.
| `--remove-orphan-assets` | — | flag | — | Removes orphan assets (admin API key required).
| `--remove-all-assets` | — | flag | — | Removes all albums and assets from the client.
| `--remove-all-albums` | — | flag | — | Removes all albums from the photo client.
| `--remove-albums` | `<PATTERN>` | string | — | Removes albums matching name pattern.
| `--remove-empty-albums` | — | flag | — | Removes empty albums.
| `--remove-duplicates-albums` | — | flag | — | Removes duplicate albums with same name/size.
| `--merge-duplicates-albums` | — | flag | — | Merges duplicate albums (moves all assets).
| `--rename-albums` | `<PATTERN,REPLACEMENT>` | string | — | Renames albums using a name pattern.

### 🧩 Standalone Features

| Argument | Parameter | Type | Valid Values | Description |
|----------|-----------|------|--------------|-------------|
| `--find-duplicates` | `<ACTION> <FOLDER(S)>` | string + list | [move, delete, list] | Finds duplicate files in the given folders.
| `--process-duplicates` | `<CSV_FILE>` | path | — | Processes duplicate file actions from CSV.
| `--fix-symlinks-broken` | `<FOLDER>` | path | — | Fixes broken album symbolic links.
| `--rename-folders-content-based` | `<ALBUMS_FOLDER>` | path | — | Renames folders based on internal dates.


## 🧪 Examples

---

### 🔄 Automatic Migration

```bash
PhotoMigrator.run --source=immich-1 --target=synology-2
```
_Migrates all content from Immich account 1 to Synology account 2._

```bash
PhotoMigrator.run --source=/mnt/photos --target=/mnt/synology --move-assets=true
```
_Migrates local folder to target and removes files from the source._

```bash
PhotoMigrator.run --source=synology-1 --target=immich-1 --parallel-migration=false
```
_Uses sequential migration instead of parallel._

---

### ⚙️ General Options

```bash
PhotoMigrator.run --client=synology --account-id=2 --input-folder=/mnt/import --output-folder=/mnt/export
```
_Specifies Synology client with ID 2 and sets input/output folders._

```bash
PhotoMigrator.run --filter-from-date=2022-01-01 --filter-to-date=2022-12-31
```
_Filters assets from 2022 only._

```bash
PhotoMigrator.run --filter-by-type=video --log-level=debug
```
_Processes only video files and shows debug logs._

---

### 📦 Google Takeout Management

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout
```
_Processes Google Takeout folder using default options._

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout --google-remove-duplicates-files --google-skip-extras-files
```
_Removes duplicates and skips extra photos like effects._

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout --google-albums-folders-structure=year/month
```
_Organizes albums by year and month structure._

---

### 🖼️ Synology / Immich Management

```bash
PhotoMigrator.run --client=immich --upload-all=/mnt/pictures
```
_Uploads all photos to Immich, organizing by subfolder albums._

```bash
PhotoMigrator.run --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup
```
_Downloads selected albums from Synology._

```bash
PhotoMigrator.run --client=synology --remove-empty-albums
```
_Removes all empty albums from Synology._

---

### 🧩 Standalone Features

```bash
PhotoMigrator.run --find-duplicates list /mnt/folder1 /mnt/folder2
```
_Lists duplicate files across multiple folders._

```bash
PhotoMigrator.run --process-duplicates revised_duplicates.csv
```
_Processes duplicates based on a CSV file with actions._

```bash
PhotoMigrator.run --rename-folders-content-based=/mnt/albums
```
_Renames album folders based on content creation dates._
