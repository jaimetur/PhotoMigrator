# 📚 Arguments Description
This section describe the different arguments and flags used by the tool.  
- An **argument** is a modifier that is followed by any parameter.
- On the other hand, a **flag** is a modifier that don't require any parameter, hence, if the flag is present the feature is enabled, otherwise, the feature is disabled.

There is also a [extended version](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description.md) of this document available.

## 🧩 Core Arguments

| Argument                                          | Description                                                    |
|---------------------------------------------------|----------------------------------------------------------------|
| `-h`,<br>`--help`                                 | Show help and exit                                             |
| `-v`,<br>`--version`                              | Show tool version and exit                                     |
| `-noConfirm`,<br>`--no-request-user-confirmation` | No Request User Confirmation before to execute any Feature.    |
| `-noLog`,<br>`--no-log-file`                      | Disable log file creation                                      |
| `-logLevel`,<br>`--log-level`                     | Sets Log level: `VERBOSE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `-logFormat`,<br>`--log-format`                   | Sets log file format: `LOG`, `TXT`, `ALL`                      |

#### 🧪 Examples:
```bash
PhotoMigrator.run --help
PhotoMigrator.run --version
```

---
## ⚙️ General Options
Following general arguments have different purposes depending on the Execution Mode.

| Argument                                  | Description                                            |
|-------------------------------------------|--------------------------------------------------------|
| `-i`,<br>`--input-folder`                 | Input folder to process                                |
| `-o`,<br>`--output-folder`                | Output folder to store results                         |
| `-client`,<br>`--client`                  | Service client: `google-takeout`, `synology`, `immich` |
| `-id`,<br>`--account-id`                  | Account ID (1–3) from `Config.ini`                     |
| `-from`,<br>`--filter-from-date`          | Filter assets from this date                           |
| `-to`,<br>`--filter-to-date`              | Filter assets up to this date                          |
| `-type`,<br>`--filter-by-type`            | Filter assets by type: `image`, `video`, `all`         |
| `-country`,<br>`--filter-by-country`      | Filter assets by country                               |
| `-city`,<br>`--filter-by-city`            | Filter assets by city                                  |
| `-person`,<br>`--filter-by-person`        | Filter assets by person                                |
| `-AlbFolder`,<br>`--albums-folders`       | Use subfolders in folder as albums                     |
| `-rAlbAsset`,<br>`--remove-albums-assets` | Remove assets inside deleted albums                    |

#### 🧪 Examples:
```bash
PhotoMigrator.run --input-folder=/mnt/import --output-folder=/mnt/export
PhotoMigrator.run --filter-from-date=2022-01-01 --filter-to-date=2022-12-31
PhotoMigrator.run --filter-by-type=video --log-level=debug
```

---
## 🚀 Automatic Migration Process
Following arguments allow you to execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service.

| Argument                               | Description                                                     |
|----------------------------------------|-----------------------------------------------------------------|
| `-source`,<br>`--source` `<SOURCE>`    | Source service or folder: `immich`, `synology`, or `local path` |
| `-target`,<br>`--target` `<TARGET>`    | Target service or folder: `immich`, `synology`, or `local path` |
| `-move`,<br>`--move-assets`            | Move instead of copy files (`true` or `false`)                  |
| `-dashboard`,<br>`--dashboard`         | Show live dashboard during migration (`true` or `false`)        |
| `-parallel`,<br>`--parallel-migration` | Run migration in parallel or sequential (`true` or `false`)     |

#### 🧪 Examples:
```bash
PhotoMigrator.run --source=immich-1 --target=synology-2
PhotoMigrator.run --source="/home/user/Takeout" --target="/mnt/photos" --move-assets true
PhotoMigrator.run --source=immich-1 --target=synology-2 --dashboard false --parallel-migration false
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
| `-gnas`,<br>`--google-no-albums-folders-structure` | No-Album folder structure (same values as above)                                                                       |
| `-gics`,<br>`--google-ignore-check-structure`      | Ignore Takeout structure validations                                                                                   |
| `-gnsa`,<br>`--google-no-symbolic-albums`          | Duplicates Albums assets instead of create symlinks to original asset in <NO_ALBUMS_FOLDER>. (requires more HDD space) |
| `-grdf`,<br>`--google-remove-duplicates-files`     | Removes duplicate files in the output folder.                                                                          |
| `-graf`,<br>`--google-rename-albums-folders`       | Renames albums folders based on content dates.                                                                         |
| `-gsef`,<br>`--google-skip-extras-files`           | Skips extra Google photos like edited/effects.                                                                         |
| `-gsma`,<br>`--google-skip-move-albums`            | Skip moving albums to `<ALBUMS_FOLDER>`                                                                                |
| `-gsgt`,<br>`--google-skip-gpth-tool`              | Skip processing with GPTH Tool (not recommended)                                                                       |
| `-gKeepTkout`,<br>`--google-keep-takeout-folder`   | Copy (instead of Move) your original Takeout into <OUTPUT_TAKEOUT_FOLDER> (requires double HDD space)                  |
| `-gSkipPrep`,<br>`--google-skip-preprocess`        | Skips Pre-process Google Takeout folder (not recommended).                                                             |
| `-gpthInfo`,<br>`--show-gpth-info`                 | Show GPTH progress messages (default: true)                                                                            |
| `-gpthError`,<br>`--show-gpth-errors`              | Show GPTH error messages (default: true)                                                                               |

#### 🧪 Examples:
```bash
PhotoMigrator.run --google-takeout="/home/user/Takeout"
PhotoMigrator.run --google-takeout="/home/user/Takeout" --google-remove-duplicates-files --google-skip-extras-files
PhotoMigrator.run --google-takeout="/home/user/Takeout" --google-albums-folders-structure=year/month

or using short arguments, 
PhotoMigrator.run -gTakeout="/home/user/Takeout" -gafs="year/month" -grdf -gsef
PhotoMigrator.run -gTakeout="/home/user/Takeout" -gnsa -gofs="cleaned"
PhotoMigrator.run -gTakeout="/home/user/Takeout" -gics -gKeepTkout=true
```

---
## 🖼️ Synology / Immich Photo Management
To use following features, it is mandatory to use the argument `--client=[synology, immich]` to specify which Photo Service do you want to use.  
You can optionally use the argument `--id=[1-3]` to specify the account id for a particular account defined in Config.ini.  
If more than one optional arguments are detected, only the first one will be executed.  

Following arguments allow you to interact with Synology/Immich Photos.

| Argument                                    | Description                                    |
|---------------------------------------------|------------------------------------------------|
| `-uAlb`,<br>`--upload-albums`               | Upload all subfolders as albums                |
| `-dAlb`,<br>`--download-albums`             | Download specific albums                       |
| `-uAll`,<br>`--upload-all`                  | Upload all assets and albums from input folder |
| `-dAll`,<br>`--download-all`                | Download all assets and albums                 |
| `-renAlb`,<br>`--rename-albums`             | Rename albums matching pattern                 |
| `-rAlb`,<br>`--remove-albums`               | Delete albums matching pattern                 |
| `-rEmpAlb`,<br>`--remove-empty-albums`      | Delete empty albums                            |
| `-rDupAlb`,<br>`--remove-duplicates-albums` | Delete duplicate albums                        |
| `-mDupAlb`,<br>`--merge-duplicates-albums`  | Merge duplicate albums                         |
| `-rAll`,<br>`--remove-all-assets`           | Delete all assets and albums (DANGER!)         |
| `-rAllAlb`,<br>`--remove-all-albums`        | Delete all albums (assets optional)            |
| `-rOrphan`,<br>`--remove-orphan-assets`     | Delete orphan assets                           |
| `-OTP`,<br>`--one-time-password`            | Use 2FA login with OTP token                   |


#### 🧪 Examples:
```bash
PhotoMigrator.run --client=immich --upload-all=/mnt/pictures
PhotoMigrator.run --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup
PhotoMigrator.run --client=synology --remove-empty-albums --one-time-password

or using short arguments,
PhotoMigrator.run -client=synology -uAlb="Albums" -id=1
PhotoMigrator.run -client=immich -dAlb="Vacaciones,Navidad" -o="Backups"
PhotoMigrator.run -client=synology -rAlb="tmp_*" -rAlbAsset -OTP
```

---
## 🛠️ Standalone Features
If more than one Feature is detected, only the first one will be executed.  
Following arguments can be used to execute the Tool in any of the usefully additional Extra Standalone Features included.  

| Argument                                         | Description                                                    |
|--------------------------------------------------|----------------------------------------------------------------|
| `-fixSym`,<br>`--fix-symlinks-broken`            | Fix broken symlinks in folder                                  |
| `-renFldcb`,<br>`--rename-folders-content-based` | Rename folders based on media content date                     |
| `-findDup`,<br>`--find-duplicates`               | Find duplicates in folder(s). Action: `list`, `move`, `delete` |
| `-procDup`,<br>`--process-duplicates`            | Execute actions from a reviewed duplicates CSV file            |


#### 🧪 Examples:
```bash
PhotoMigrator.run --fix-symlinks-broken="/mnt/albums"
PhotoMigrator.run --rename-folders-content-based="/mnt/albums"
PhotoMigrator.run --find-duplicates list "/mnt/folder1" "/mnt/folder2"
PhotoMigrator.run --process-duplicates revised_duplicates.csv
```


---
## 🧪 Examples description:
Below you can find a short description of  above examples 

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

### 🗃️ Google Takeout Management

```bash
PhotoMigrator.run --google-takeout=/home/user/Takeout

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
PhotoMigrator.run --client=synology --remove-empty-albums --one-time-password

Removes all empty albums from Synology.
```

---

### 🛠️ Other Standalone Features

```bash
PhotoMigrator.run --fix-symlinks-broken="/mnt/albums"

Fix symbolic links found in the given folder
```

```bash
hotoMigrator.run --rename-folders-content-based="/mnt/albums"

Renames album folders based on content creation dates.
```

```bash
PhotoMigrator.run --find-duplicates list "/mnt/folder1" "/mnt/folder2"

Lists duplicate files across multiple folders.
```

```bash
PhotoMigrator.run --process-duplicates revised_duplicates.csv

Processes duplicates based on a CSV file with actions.
```

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  

