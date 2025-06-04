# 📚 Arguments Description

---
This section describe the different arguments and flags used by the tool.  
- An **argument** is a modifier that is followed by any parameter.
- On the other hand, a **flag** is a modifier that don't requires any parameter, hence, if the flag is present the feature is enabled, otherwise, the feature is disabled.

There is also a [shorter version](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description-short.md) of this doccument available.

## 🧩 Core Arguments

| Argument    | Parameter | Type | Valid Values | Description                          |
|-------------|-----------|------|--------------|--------------------------------------|
| `--help`    |           | flag |              | Displays the help message and exits. |
| `--version` |           | flag |              | Shows the tool version and exits.    |

## 🚀 Automatic Migration
Following arguments allow you execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service.

| Argument               | Parameter  | Type              |                 Valid Values                  | Description                                             |
|------------------------|------------|-------------------|:---------------------------------------------:|---------------------------------------------------------|
| `--source`             | `<SOURCE>` | path / <br>string | `existing path`, <br>`synology`, <br>`immich` | Defines the source for the automatic migration process. |
| `--target`             | `<TARGET>` | path / <br>string | `existing path`, <br>`synology`, <br>`immich` | Defines the target for the automatic migration process. |
| `--move-assets`        | `<bool>`   | bool              |    `true`, `false` <br>`(default: false)`     | Enable / Disables move assets instead of copying them.  |
| `--dashboard`          | `<bool>`   | bool              |    `true`, `false` <br>`(default: false)`     | Enables / Disables the live dashboard during migration. |
| `--parallel-migration` | `<bool>`   | bool              |    `true`, `false` <br>`(default: false)`     | Enables / Disables parallel asset migration.            |

#### 🧪 Examples:
```bash
PhotoMigrator.run --source=immich-1 --target=synology-2
PhotoMigrator.run --source=/mnt/photos --target=/mnt/synology --move-assets=true
PhotoMigrator.run --source=synology-1 --target=immich-1 --parallel-migration=false
```

## ⚙️ General Options
Following general flags have different purposses depending on the Execution Mode.

| Argument                 | Parameter         | Type   |                  Valid Values                   | Description                                             |
|--------------------------|-------------------|--------|:-----------------------------------------------:|---------------------------------------------------------|
| `--input-folder`         | `<INPUT_FOLDER>`  | path   |                 `existing path`                 | Folder containing assets to be processed.               |
| `--output-folder`        | `<OUTPUT_FOLDER>` | path   |                  `valid path`                   | Folder where processed assets or results will be saved. |
| `--client`               | `<CLIENT>`        | string | `google-takeout`, <br>`synology`, <br>`immich`  | Specifies the service to interact with.                 |
| `--account-id`           | `<ID>`            | int    |        `1`, `2`, `3` <br>`(default: 1)`         | ID of the configured account in Config.ini.             |
| `--one-time-password`    |                   | flag   |                                                 | Enables / Disables OTP login for Synology (2FA).        |
| `--filter-from-date`     | `<FROM_DATE>`     | date   |     `yyyy-mm-dd`, <br>`yyyy-mm`, <br>`yyyy`     | Filters assets from this date onward.                   |
| `--filter-to-date`       | `<TO_DATE>`       | date   |     `yyyy-mm-dd`, <br>`yyyy-mm`, <br>`yyyy`     | Filters assets up to this date.                         |
| `--filter-by-country`    | `<COUNTRY>`       | string |                 `country-name`                  | Filters assets by country.                              |
| `--filter-by-city`       | `<CITY>`          | string |                   `city-name`                   | Filters assets by city.                                 |
| `--filter-by-person`     | `<PERSON>`        | string |                  `person-name`                  | Filters assets by person name.                          |
| `--filter-by-type`       | `<TYPE>`          | string |  `image`, `video`, `all` <br>`(default: all)`   | Filters assets by type.                                 |
| `--albums-folders`       | `<ALBUMS_FOLDER>` | path   |                 `existing path`                 | Creates albums for subfolders inside.                   |
| `--remove-albums-assets` |                   | flag   |                                                 | Removes assets inside albums when albums are removed.   |
| `--no-log-file`          |                   | flag   |                                                 | Disables writing to log file.                           |
| `--log-level`            | `<LEVEL>`         | string | `debug`, <br>`info`, <br>`warning`, <br>`error` | Sets logging verbosity.                                 |

#### 🧪 Examples:
```bash
PhotoMigrator.run --input-folder=/mnt/import --output-folder=/mnt/export
PhotoMigrator.run --filter-from-date=2022-01-01 --filter-to-date=2022-12-31
PhotoMigrator.run --filter-by-type=video --log-level=debug
```

## 🗃️ Google Takeout Management
In this mode, you can use more than one optional flags from the below list.  
If only the flag -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the Tool will use the default values for the rest of the flags for this extra mode.

Following arguments allow you to interact with Google Photos Takeout Folder.   

| Argument                              | Parameter          | Type   |                                    Valid Values                                    | Description                                                        |
|---------------------------------------|--------------------|--------|:----------------------------------------------------------------------------------:|--------------------------------------------------------------------|
| `--google-takeout`                    | `<TAKEOUT_FOLDER>` | path   |                                                                                    | Path to the Takeout folder (either zipped or unzipped) to process. |
| `--google-output-folder-suffix`       | `<SUFFIX>`         | string |                              `(default: 'processed')`                              | Suffix to add to the output folder.                                |
| `--google-albums-folders-structure`   | `<STRUCTURE>`      | string | `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: flatten)` | Folder structure for Albums.                                       |
| `--google-no-albums-folder-structure` | `<STRUCTURE>`      | string | `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: flatten)` | Folder structure for No-Albums.                                    |
| `--google-create-symbolic-albums`     |                    | flag   |                                                                                    | Creates symlinks for albums instead of duplicating files.          |
| `--google-ignore-check-structure`     |                    | flag   |                                                                                    | Ignores structure check of Takeout folders.                        |
| `--google-move-takeout-folder`        |                    | flag   |                                                                                    | Moves original assets to output (risk of loss).                    |
| `--google-remove-duplicates-files`    |                    | flag   |                                                                                    | Removes duplicate files in the output folder.                      |
| `--google-rename-albums-folders`      |                    | flag   |                                                                                    | Renames albums folders based on content dates.                     |
| `--google-skip-extras-files`          |                    | flag   |                                                                                    | Skips extra Google photos like edited/effects.                     |
| `--google-skip-move-albums`           |                    | flag   |                                                                                    | Skips moving albums to 'Albums' folder.                            |
| `--google-skip-gpth-tool`             |                    | flag   |                                                                                    | Skips GPTH tool processing (not recommended).                      |
| `--show-gpth-info`                    | `<bool>`           | bool   |                       `true`, `false` <br>`(default: true)`                        | Show GPTH progress messages.                                       |
| `--show-gpth-errors`                  | `<bool>`           | bool   |                       `true`, `false` <br>`(default: true)`                        | Show GPTH error messages.                                          |

#### 🧪 Examples:
```bash
PhotoMigrator.run --google-takeout="/home/user/Takeout"
PhotoMigrator.run --google-takeout="/home/user/Takeout" --google-remove-duplicates-files --google-skip-extras-files
PhotoMigrator.run --google-takeout="/home/user/Takeout" --google-albums-folders-structure=year/month
```

## 🖼️ Synology / Immich Management
To use following features, it is mandatory to use the flag '--client=[synology, immich]' to specify which Photo Service do you want to use.  
You can optionally use the flag '--id=[1-3]' to specify the account id for a particular account defined in Config.ini.  
If more than one optional flags are detected, only the first one will be executed.  

Following arguments allow you to interact with Synology/Immich Photos.

| Argument                     | Parameter                                       |       Type        |   Valid Values   | Description                                               |
|------------------------------|-------------------------------------------------|:-----------------:|:----------------:|-----------------------------------------------------------|
| `--upload-albums`            | `<ALBUMS_FOLDER>`                               |       path        | `existing path`  | Uploads albums from folders to the selected photo client. |
| `--download-albums`          | `<ALBUM_NAMES>`                                 |       list        | `existing album` | Downloads albums by name to the output folder.            |
| `--upload-all`               | `<INPUT_FOLDER>`                                |       path        | `existing path`  | Uploads all assets and creates albums by subfolder.       |
| `--download-all`             | `<OUTPUT_FOLDER>`                               |       path        | `existing path`  | Downloads all albums and assets to this folder.           |
| `--rename-albums`            | `<ALBUMS_NAME_PATTERN>` `<PATTERN_REPLACEMENT>` | `string` `string` | `regex pattern`  | Renames albums using a name pattern.                      |
| `--remove-albums`            | `<PATTERN>`                                     |      string       | `regex pattern`  | Removes albums matching name pattern.                     |
| `--remove-empty-albums`      |                                                 |       flag        |                  | Removes empty albums.                                     |
| `--remove-duplicates-albums` |                                                 |       flag        |                  | Removes duplicate albums with same name/size.             |
| `--merge-duplicates-albums`  |                                                 |       flag        |                  | Merges duplicate albums (moves all assets).               |
| `--remove-all-assets`        |                                                 |       flag        |                  | Removes all albums and assets from the client.            |
| `--remove-all-albums`        |                                                 |       flag        |                  | Removes all albums from the photo client.                 |
| `--remove-orphan-assets`     |                                                 |       flag        |                  | Removes orphan assets (admin API key required).           |

#### 🧪 Examples:
```bash
PhotoMigrator.run --client=immich --upload-all=/mnt/pictures
PhotoMigrator.run --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup
PhotoMigrator.run --client=synology --remove-empty-albums
```

## 🛠️ Standalone Features
If more than one Feature is detected, only the first one will be executed.  
Following arguments can be used to execute the Tool in any of the usefull additionals Extra Standalone Features included.  

| Argument                         | Parameter              | Type          |                  Valid Values                  | Description                                                                                                                                                               |
|----------------------------------|------------------------|---------------|:----------------------------------------------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--find-duplicates`              | `<ACTION> <FOLDER(S)>` | string + list | `move`, `delete`, `list` <br>+<br> `[folders]` | Finds duplicate files in the given folders and applies the specified action. <br><br>if action is 'list', only output csv will be generated and any file will be touched. |
| `--process-duplicates`           | `<CSV_FILE>`           | path          |                  `path to .csv`                  | Processes duplicate file actions from CSV and applies what the action set in Action column for each file.                                                                 |
| `--fix-symlinks-broken`          | `<FOLDER>`             | path          |                 `existing path`                  | Fixes broken album symbolic links.                                                                                                                                        |
| `--rename-folders-content-based` | `<ALBUMS_FOLDER>`      | path          |                 `existing path`                  | Renames folders based on internal dates.                                                                                                                                  |

#### 🧪 Examples:
```bash
PhotoMigrator.run --find-duplicates list "/mnt/folder1" "/mnt/folder2"
PhotoMigrator.run --process-duplicates revised_duplicates.csv
PhotoMigrator.run --fix-symlinks-broken="/mnt/albums"
PhotoMigrator.run --rename-folders-content-based="/mnt/albums"
```

---
## 🧪 Examples description:
Below you can find a short description of  above examples 

### 🚀 Automatic Migration

```bash
PhotoMigrator.run --source=immich-1 --target=synology-2

Migrates all content from Immich account 1 to Synology account 2.
```

```bash
PhotoMigrator.run --source=/mnt/photos --target=/mnt/synology --move-assets=true

Migrates local folder to target and removes files from the source.
```

```bash
PhotoMigrator.run --source=synology-1 --target=immich-1 --parallel-migration=false

Uses sequential migration instead of parallel.
```

---

### ⚙️ General Options

```bash
PhotoMigrator.run --input-folder=/mnt/import --output-folder=/mnt/export
    
Process input folder to fix metadatas and save the result in output folder.
```

```bash
PhotoMigrator.run --filter-from-date=2022-01-01 --filter-to-date=2022-12-31

Filters assets from 2022 only.
```

```bash
PhotoMigrator.run --filter-by-type=video --log-level=debug

Processes only video files and shows debug logs.
```

---

### 🗃️ Google Takeout Management

```bash
PhotoMigrator.run --google-takeout="/home/user/Takeout"

Processes Google Takeout folder using default options.
```

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout --google-remove-duplicates-files --google-skip-extras-files

Removes duplicates and skips extra photos like effects.
```

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout --google-albums-folders-structure=year/month

Organizes albums by year and month structure.
```

---

### 🖼️ Synology / Immich Management

```bash
PhotoMigrator.run --client=immich --upload-all=/mnt/pictures

Uploads all photos to Immich, organizing by subfolder albums.
```

```bash
PhotoMigrator.run --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup

Downloads selected albums from Synology.
```

```bash
PhotoMigrator.run --client=synology --remove-empty-albums

Removes all empty albums from Synology.
```

---

### 🛠️ Other Standalone Features

```bash
PhotoMigrator.run --find-duplicates list "/mnt/folder1" "/mnt/folder2"

Lists duplicate files across multiple folders.
```

```bash
PhotoMigrator.run --process-duplicates revised_duplicates.csv

Processes duplicates based on a CSV file with actions.
```

```bash
PhotoMigrator.run --fix-symlinks-broken="/mnt/albums"

Fix symbolic links found in the given folder
```

```bash
PhotoMigrator.run --rename-folders-content-based="/mnt/albums"

Renames album folders based on content creation dates.
```

---

## [🏠 Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main)
