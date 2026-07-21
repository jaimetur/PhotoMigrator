# 📚 Arguments Description
This section describe the different arguments and flags used by the tool.  
- An **argument** is a modifier that is followed by any parameter.
- On the other hand, a **flag** is a modifier that don't require any parameter, hence, if the flag is present the feature is enabled, otherwise, the feature is disabled.

There is also a [extended version](02-arguments-description.md) of this document available.

> [!NOTE]
> For compiled binaries, macOS now uses `PhotoMigrator.command`. Linux and Synology SSH continue using `PhotoMigrator.bin`. If you are following the examples below on macOS, replace `PhotoMigrator.bin` with `PhotoMigrator.command`.

## 🖥️ Launcher Flags

These flags are handled before the normal argparse parser starts, so they are launcher controls rather than regular feature arguments.

| Argument | Description                       |
|----------|-----------------------------------|
| `--gui`  | Force the Desktop GUI explicitly  |
| `--tui`  | Force the Terminal TUI explicitly |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --gui
PhotoMigrator.bin --tui
PhotoMigrator.bin --gui --configuration-file ./Config.ini
PhotoMigrator.bin --gui --configuration-file /srv/PhotoMigrator/custom.ini
```

Notes:
- GUI/TUI startup also honors `--configuration-file`.
- Without that argument, both interfaces use `./Config.ini` from the current execution folder by default.

## 🧩 Core Arguments

| Argument                                           | Description                                                                                        |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `-h`,<br>`--help`                                  | Show help and exit                                                                                 |
| `-v`,<br>`--version`                               | Show tool version and exit                                                                         |
| `-config`,<br>`--configuration-file`               | Config file path for CLI and for GUI/TUI startup                                                   |
| `-noConfirm`,<br>`--no-request-user-confirmation`  | No Request User Confirmation before to execute any Feature.                                        |
| `-noLog`,<br>`--no-log-file`                       | Disable log file creation                                                                          |
| `-logLevel`,<br>`--log-level`                      | Sets Log level: `VERBOSE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`                                     |
| `-logFormat`,<br>`--log-format`                    | Sets log file format: `LOG`, `TXT`, `ALL`                                                          |
| `-fnAlbums`,<br>`--foldername-albums`              | Specify the folder name to store all your processed photos associated to any Album.                |
| `-fnNoAlbums`,<br>`--foldername-no-albums`         | Specify the folder name to store all your processed photos (including those associated to Albums). |
| `-fnLogs`,<br>`--foldername-logs`                  | Specify the folder name to save the execution Logs.                                                |
| `-fnDuplicat`,<br>`--foldername-duplicates-output` | Specify the folder name to save the outputs of 'Find Duplicates' Feature.                          |
| `-fnExtDates`,<br>`--foldername-extracted-dates`   | Specify the folder name to save the Metadata outputs of 'Extracted Dates'.                         |
| `-exeGpthTool`,<br>`--exec-gpth-tool`              | Specify an external version of GPTH Tool binary.                                                   |
| `-exeExifTool`,<br>`--exec-exif-tool`              | Specify an external version of GPTH Tool binary.                                                   |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --help
PhotoMigrator.bin --version
```

---
## ⚙️ General Options
Following general arguments have different purposes depending on the Execution Mode.

| Argument                                  | Description                                                                          |
|-------------------------------------------|--------------------------------------------------------------------------------------|
| `-i`,<br>`--input-folder`                 | Input folder to process                                                              |
| `-o`,<br>`--output-folder`                | Output folder to store results                                                       |
| `-client`,<br>`--client`                  | Service client: `google-takeout`, `google-photos`, `synology`, `immich`, `nextcloud` |
| `-id`,<br>`--account-id`                  | Account ID (1–3) from `Config.ini` (default: `1`)                                    |
| `-from`,<br>`--filter-from-date`          | Filter assets from this date                                                         |
| `-to`,<br>`--filter-to-date`              | Filter assets up to this date                                                        |
| `-type`,<br>`--filter-by-type`            | Filter assets by type: `image`, `video`, `all`                                       |
| `-country`,<br>`--filter-by-country`      | Filter assets by country                                                             |
| `-city`,<br>`--filter-by-city`            | Filter assets by city                                                                |
| `-person`,<br>`--filter-by-person`        | Filter assets by person                                                              |
| `-exFolders`,<br>`--exclude-folders`      | Exclude folder patterns during local-folder processing/migration                     |
| `-exFiles`,<br>`--exclude-files`          | Exclude file patterns during local-folder processing/migration                       |
| `-AlbFolder`,<br>`--albums-folders`       | Use subfolders in folder as albums                                                   |
| `-rAlbAsset`,<br>`--remove-albums-assets` | Remove assets inside deleted albums                                                  |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --input-folder=/mnt/import --output-folder=/mnt/export
PhotoMigrator.bin --filter-from-date=2022-01-01 --filter-to-date=2022-12-31
PhotoMigrator.bin --filter-by-type=video --log-level=debug
```

---
## 🚀 Automatic Migration Process
Following arguments allow you to execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service.

| Argument                               | Description                                                                                   |
|----------------------------------------|-----------------------------------------------------------------------------------------------|
| `-source`,<br>`--source` `<SOURCE>`    | Source service or folder: `immich`, `synology`, `nextcloud`, `google-photos`, or `local path` |
| `-target`,<br>`--target` `<TARGET>`    | Target service or folder: `immich`, `synology`, `nextcloud`, `google-photos`, or `local path` |
| `-move`,<br>`--move-assets`            | Move instead of copy files (`true` or `false`)                                                |
| `-dashboard`,<br>`--dashboard`         | Show live dashboard during migration (`true` or `false`)                                      |
| `-parallel`,<br>`--parallel-migration` | Run migration in parallel or sequential (`true` or `false`)                                   |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --source=immich-1 --target=synology-2
PhotoMigrator.bin --source="/home/user/Takeout" --target="/mnt/photos" --move-assets true
PhotoMigrator.bin --source=immich-1 --target=synology-2 --dashboard false --parallel-migration false
```

---
## 🗃️ Google Photos Takeout Management
In this mode, you can use more than one optional arguments and flags from the below list.  
If only the argument `-gTakeout, --google-takeout <TAKEOUT_FOLDER>` is detected, then the Tool will use the default values for the rest of the flags for this extra mode.

Following arguments allow you to interact with Google Photos Takeout Folder.  

| Argument                                           | Description                                                                                                            |
|----------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `-gTakeout`,<br>`--google-takeout`                 | Path to Takeout folder (mandatory for this mode)                                                                       |
| `-gofs`,<br>`--google-output-folder-suffix`        | Suffix for output folder (default: `processed`)                                                                        |
| `-gafs`,<br>`--google-albums-folders-structure`    | Album folder structure: `flatten`, `year`, `year/month`, `year-month`                                                  |
| `-gnas`,<br>`--google-no-albums-folders-structure` | No-Album folder structure (same values as above; default: `year/month`)                                                |
| `-gics`,<br>`--google-ignore-check-structure`      | Ignore Takeout structure validations                                                                                   |
| `-gnsa`,<br>`--google-no-symbolic-albums`          | Duplicates Albums assets instead of create symlinks to original asset in <NO_ALBUMS_FOLDER>. (requires more HDD space) |
| `-grdf`,<br>`--google-remove-duplicates-files`     | Removes duplicate files in the output folder.                                                                          |
| `-graf`,<br>`--google-rename-albums-folders`       | Renames albums folders based on content dates.                                                                         |
| `-gsef`,<br>`--google-skip-extras-files`           | Skips extra Google photos like edited/effects.                                                                         |
| `-gsma`,<br>`--google-skip-move-albums`            | Skip moving albums to `<ALBUMS_FOLDER>`                                                                                |
| `-gSkipGpth`,<br>`--google-skip-gpth-tool`         | Skip processing with GPTH Tool (not recommended)                                                                       |
| `-gSkipPrep`,<br>`--google-skip-preprocess`        | Skips Pre-process Google Takeout folder (not recommended).                                                             |
| `-gSkipPost`,<br>`--google-skip-postprocess`       | Skips Post-process Google Takeout folder (not recommended).                                                            |
| `-gKeepTakeout`,<br>`--google-keep-takeout-folder` | Keeps a untouched copy of your original Takeout folder. (requires double HDD space).                                   |
| `-gpthInfo`,<br>`--show-gpth-info`                 | Show GPTH progress messages (default: true).                                                                           |
| `-gpthError`,<br>`--show-gpth-errors`              | Show GPTH error messages (default: true).                                                                              |
| `-gpthNoLog`,<br>`--gpth-no-log`                   | Skip Save GPTH log messages into output folder.                                                                        |
| `-gPeople`,<br>`--google-process-people` `<bool>`  | Process Google JSON people labels and write `takeout_people_metadata.json` (default: `true`). Set `false` to skip it.  |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --google-takeout="/home/user/Takeout"
PhotoMigrator.bin --google-takeout="/home/user/Takeout" --google-remove-duplicates-files --google-skip-extras-files
PhotoMigrator.bin --google-takeout="/home/user/Takeout" --google-albums-folders-structure=year/month

or using short arguments, 
PhotoMigrator.bin -gTakeout="/home/user/Takeout" -gafs="year/month" -grdf -gsef
PhotoMigrator.bin -gTakeout="/home/user/Takeout" -gnsa -gofs="cleaned"
PhotoMigrator.bin -gTakeout="/home/user/Takeout" -gics -gKeepTakeout=true
```

---
## 🍎 iCloud Takeout Management
In this mode, you can use more than one optional arguments and flags from the below list.
If only the argument `-iTakeout, --icloud-takeout <ICLOUD_EXPORT_FOLDER>` is detected, then the Tool will use the default values for the rest of the flags for this extra mode.

Following arguments allow you to interact with Apple iCloud Photos export folders.

| Argument                                           | Description                                                                                                          |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `-iTakeout`,<br>`--icloud-takeout`                 | Path to the iCloud export folder (mandatory for this mode)                                                           |
| `-iofs`,<br>`--icloud-output-folder-suffix`        | Suffix for the iCloud processed output folder (default: `processed`)                                                 |
| `-iafs`,<br>`--icloud-albums-folders-structure`    | Reconstructed album folder structure: `flatten`, `year`, `year/month`, `year-month`                                  |
| `-inas`,<br>`--icloud-no-albums-folders-structure` | No-Album folder structure (same values as above; default: `year/month`)                                              |
| `-insa`,<br>`--icloud-no-symbolic-albums`          | Duplicate reconstructed iCloud album assets instead of creating symlinks in `<NO_ALBUMS_FOLDER>` (default: symlinks) |
| `-iMem`,<br>`--icloud-include-memories`            | Also reconstruct iCloud `Memories` CSV collections as folders. Pre-selected by default in Web/TUI/GUI                |
| `-iNExif`,<br>`--icloud-prefer-native-exif-writer` | Prefer the native EXIF writer when possible. Pre-selected by default in Web/TUI/GUI                                  |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport"
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-no-symbolic-albums
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-include-memories
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-prefer-native-exif-writer

or using short arguments,
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -iofs="cleaned"
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -iafs="year/month" -inas="year/month"
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -insa -iMem
```

---
## 🖼️ Google Photos / Synology / Immich / NextCloud Management
To use following features, it is mandatory to use the argument `--client=[synology, immich, nextcloud, google-photos]` to specify which Photo Service do you want to use.  
You can optionally use the argument `--id=[1-3]` to specify the account id for a particular account defined in Config.ini.  
If more than one optional arguments are detected, only the first one will be executed.  

Following arguments allow you to interact with Google Photos, Synology, Immich, and NextCloud.

| Argument                                             | Description                                                                                                                                                                                                                                                                                                                      |
|------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-uAlb`,<br>`--upload-albums`                        | Upload all subfolders as albums                                                                                                                                                                                                                                                                                                  |
| `-dAlb`,<br>`--download-albums`                      | Download specific albums                                                                                                                                                                                                                                                                                                         |
| `-uAll`,<br>`--upload-all`                           | Upload all assets and albums from input folder                                                                                                                                                                                                                                                                                   |
| `-iPeople`,<br>`--import-people`                     | Immich Upload All, Upload Albums, or Immich-target Automatic Migration only: import Takeout people labels                                                                                                                                                                                                                        |
| `-prefCanAlb`,<br>`--prefer-canonical-album-names`   | Normalize new destination album names during cloud uploads and Automatic Migration                                                                                                                                                                                                                                               |
| `-consSimAlb`,<br>`--consolidate-similar-albums`     | Reuse and consolidate equivalent album families during cloud uploads and Automatic Migration                                                                                                                                                                                                                                     |
| `-consAlbNames`,<br>`--consolidate-albums-names`     | Consolidate equivalent existing cloud album families directly in the target service                                                                                                                                                                                                                                              |
| `-dAll`,<br>`--download-all`                         | Download all assets and albums                                                                                                                                                                                                                                                                                                   |
| `-renAlb`,<br>`--rename-albums`                      | Rename albums using text, wildcard, or regex                                                                                                                                                                                                                                                                                     |
| `-rAlb`,<br>`--remove-albums`                        | Delete albums using text, wildcard, or regex                                                                                                                                                                                                                                                                                     |
| `-prevAlbAct`,<br>`--preview-album-actions`          | Preview rename/remove/consolidation matches and confirm                                                                                                                                                                                                                                                                          |
| `-rEmpAlb`,<br>`--remove-empty-albums`               | Delete empty albums                                                                                                                                                                                                                                                                                                              |
| `-rDupAlb`,<br>`--remove-duplicates-albums`          | Delete duplicate albums                                                                                                                                                                                                                                                                                                          |
| `-rDupAst`,<br>`--remove-duplicates-assets`          | Delete duplicate assets; Immich uses native visual groups by default                                                                                                                                                                                                                                                             |
| `-immichDupAlgo`,<br>`--immich-duplicates-algorithm` | Immich only: similarity detection; disable for exact filename/size Takeout re-upload checks (default: `true`)                                                                                                                                                                                                                    |
| `-immichDupDel`,<br>`--immich-duplicates-deletion`   | Immich only: `true` uses Immich's Alpha resolver (albums, favorites, rating, descriptions, visibility, matching location, tags; moves to trash); `false` uses PhotoMigrator's guarded merge (+ capture date, stacks, safe faces/persons; permanent delete). Unsafe face transfers do not block deletion. Unavailable with native detection off (default: `true` when enabled) |
| `-dupKeeper`,<br>`--duplicate-asset-keeper`          | Keeper: `better-quality`, `oldest`, or `newest` (`better-quality` is the Immich default)                                                                                                                                                                                                                                         |
| `-mDupAlb`,<br>`--merge-duplicates-albums`           | Merge duplicate albums                                                                                                                                                                                                                                                                                                           |
| `-rAll`,<br>`--remove-all-assets`                    | Delete all assets and albums (DANGER!)                                                                                                                                                                                                                                                                                           |
| `-rAllAlb`,<br>`--remove-all-albums`                 | Delete all albums (assets optional)                                                                                                                                                                                                                                                                                              |
| `-OTP`,<br>`--one-time-password`                     | Use 2FA login with OTP token                                                                                                                                                                                                                                                                                                     |


#### 🧪 Examples:
```bash
PhotoMigrator.bin --client=immich --upload-all=/mnt/pictures
PhotoMigrator.bin --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup
PhotoMigrator.bin --client=synology --remove-empty-albums --one-time-password

or using short arguments,
PhotoMigrator.bin -client=synology -uAlb="Albums" -id=1
PhotoMigrator.bin -client=immich -dAlb="Vacaciones,Navidad" -o="Backups"
PhotoMigrator.bin -client=synology -rAlb="tmp_*" -rAlbAsset -OTP
```

---
## 🛠️ Standalone Features
If more than one Feature is detected, only the first one will be executed.  
Following arguments can be used to execute the Tool in any of the usefully additional Extra Standalone Features included.  

| Argument                                         | Description                                                                                                  |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `-fixSym`,<br>`--fix-symlinks-broken`            | Fix broken symlinks in folder                                                                                |
| `-renFldcb`,<br>`--rename-folders-content-based` | Rename folders based on media content date                                                                   |
| `-orgDate`,<br>`--organize-local-folder-by-date` | Create a processed copy of a local folder and reorganize its media by date                                   |
| `-olfs`,<br>`--organize-output-folder-suffix`    | Change generated suffix for `--organize-local-folder-by-date` when no explicit `--output-folder` is provided |
| `-olstr`,<br>`--organize-folder-structure`       | Select layout for organized output: `flatten`, `year`, `year/month`, `year-month`                            |
| `-omove`,<br>`--move-original-files`             | Move original files instead of copying them first when organizing a local folder by date                     |
| `-findDup`,<br>`--find-duplicates`               | Find duplicates in folder(s). Action: `list`, `move`, `remove`                                               |
| `-procDup`,<br>`--process-duplicates`            | Execute actions from a reviewed duplicates CSV file                                                          |


#### 🧪 Examples:
```bash
PhotoMigrator.bin --fix-symlinks-broken="/mnt/albums"
PhotoMigrator.bin --rename-folders-content-based="/mnt/albums"
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --organize-folder-structure=year/month
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --output-folder="/mnt/organized"
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --move-original-files --organize-output-folder-suffix=archive
PhotoMigrator.bin --find-duplicates list "/mnt/folder1" "/mnt/folder2"
PhotoMigrator.bin --process-duplicates revised_duplicates.csv
```


---
## 🧪 Examples description:
Below you can find a short description of  above examples 

### ⚙️ General Options

```bash
PhotoMigrator.bin --input-folder=/mnt/import --output-folder=/mnt/export
    
Process input folder to fix metadatas and save the result in output folder.
```

```bash
PhotoMigrator.bin --filter-from-date=2022-01-01 --filter-to-date=2022-12-31

Filters assets from 2022 only.
```

```bash
PhotoMigrator.bin --filter-by-type=video --log-level=debug

Processes only video files and shows debug logs.
```

---

### 🚀 Automatic Migration

```bash
PhotoMigrator.bin --source=immich-1 --target=synology-2

Migrates all content from Immich account 1 to Synology account 2.
```

```bash
PhotoMigrator.bin --source=/mnt/photos --target=/mnt/synology --move-assets=true

Migrates local folder to target and removes files from the source.
```

```bash
PhotoMigrator.bin --source=synology-1 --target=immich-1 --parallel-migration=false

Uses sequential migration instead of parallel.
```

---

### 🗃️ Google Takeout Management

```bash
PhotoMigrator.bin --google-takeout=/home/user/Takeout

Processes Google Takeout folder using default options.
```

```bash
PhotoMigrator.bin --google-takeout=/home/user/Takeout --google-remove-duplicates-files --google-skip-extras-files

Removes duplicates and skips extra photos like effects.
```

```bash
PhotoMigrator.bin --google-takeout=/home/user/Takeout --google-albums-folders-structure=year/month

Organizes albums by year and month structure.
```

---

### 🖼️ Synology / Immich Management

```bash
PhotoMigrator.bin --client=immich --upload-all=/mnt/pictures

Uploads all photos to Immich, organizing by subfolder albums.
```

```bash
PhotoMigrator.bin --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup

Downloads selected albums from Synology.
```

```bash
PhotoMigrator.bin --client=synology --remove-empty-albums --one-time-password

Removes all empty albums from Synology.
```

---

### 🛠️ Other Standalone Features

```bash
PhotoMigrator.bin --fix-symlinks-broken="/mnt/albums"

Fix symbolic links found in the given folder
```

```bash
hotoMigrator.run --rename-folders-content-based="/mnt/albums"

Renames album folders based on content creation dates.
```

```bash
PhotoMigrator.bin --find-duplicates list "/mnt/folder1" "/mnt/folder2"

Lists duplicate files across multiple folders.
```

```bash
PhotoMigrator.bin --process-duplicates revised_duplicates.csv

Processes duplicates based on a CSV file with actions.
```

---
## 🏠 [Back to Main Page](../README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
