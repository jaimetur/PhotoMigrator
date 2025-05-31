# 📚 Arguments Description
This section describe the different arguments and flags used by the tool.  
- An **argument** is a modifier that is followed by any parameter.
- On the other hand, a **flag** is a modifier that don't requires any parameter, hence, if the flag is present the feature is enabled, otherwise, the feature is disabled.

There is also a [extended version](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description.md) of this doccument available.

## 🧩 Core Arguments

| Argument          | Description                |
|-------------------|----------------------------|
| `--help`, `-h`    | Show help and exit         |
| `--version`, `-v` | Show tool version and exit |

### 🧪 Examples
```bash
PhotoMigrator.run --help
PhotoMigrator.run --version
```

---

## 🚀 Automatic Migration Process

| Argument               | Description                                                     |
|------------------------|-----------------------------------------------------------------|
| `--source <SOURCE>`    | Source service or folder: `immich`, `synology`, or `local path` |
| `--target <TARGET>`    | Target service or folder: `immich`, `synology`, or `local path` |
| `--move-assets`        | Move instead of copy files (`true` or `false`)                  |
| `--dashboard`          | Show live dashboard during migration (`true` or `false`)        |
| `--parallel-migration` | Run migration in parallel or sequential (`true` or `false`)     |

### 🧪 Examples
```bash
PhotoMigrator.run --source=immich-1 --target=synology-2
PhotoMigrator.run --source="/home/user/Takeout" --target="/mnt/photos" --move-assets true
PhotoMigrator.run --source=immich-1 --target=synology-2 --dashboard false --parallel-migration false
```

---

## ⚙️ General Options

| Argument                              | Description                                            |
|---------------------------------------|--------------------------------------------------------|
| `--input-folder`, `-i`                | Input folder to process                                |
| `--output-folder`, `-o`               | Output folder to store results                         |
| `--client`                            | Service client: `google-takeout`, `synology`, `immich` |
| `--account-id`, `-id`                 | Account ID (1–3) from `Config.ini`                     |
| `--one-time-password`, `--OTP`        | Use 2FA login with OTP token                           |
| `--filter-from-date`, `--from`        | Filter assets from this date                           |
| `--filter-to-date`, `--to`            | Filter assets up to this date                          |
| `--filter-by-country`, `--country`    | Filter assets by country                               |
| `--filter-by-city`, `--city`          | Filter assets by city                                  |
| `--filter-by-person`, `--person`      | Filter assets by person                                |
| `--filter-by-type`, `--type`          | Filter assets by type: `image`, `video`, `all`         |
| `--albums-folders`, `--AlbFld`        | Use subfolders in folder as albums                     |
| `--remove-albums-assets`, `--rAlbAss` | Remove assets inside deleted albums                    |
| `--no-log-file`, `--nolog`            | Disable log file creation                              |
| `--log-level`, `--loglevel`           | Log level: `debug`, `info`, `warning`, `error`         |

### 🧪 Examples
```bash
PhotoMigrator.run --client=immich --input-folder "Photos" --output-folder "Exported"
PhotoMigrator.run --client=google-takeout --from 2020-01-01 --to 2021-01-01
PhotoMigrator.run --type video --country Spain --person "Ana"
```

---

## 🗃️ Google Photos Takeout Management

| Argument                                        | Description                                                           |
|-------------------------------------------------|-----------------------------------------------------------------------|
| `--google-takeout`, `--gTakeout`                | Path to Takeout folder (mandatory for this mode)                      |
| `--google-output-folder-suffix`, `--gofs`       | Suffix for output folder (default: `processed`)                       |
| `--google-albums-folders-structure`, `--gafs`   | Album folder structure: `flatten`, `year`, `year/month`, `year-month` |
| `--google-no-albums-folder-structure`, `--gnas` | No-Album folder structure (same values as above)                      |
| `--google-create-symbolic-albums`, `--gcsa`     | Use symbolic links for albums                                         |
| `--google-ignore-check-structure`, `--gics`     | Ignore Takeout structure validations                                  |
| `--google-move-takeout-folder`, `--gmtf`        | Move instead of copy assets (destructive)                             |
| `--google-remove-duplicates-files`, `--grdf`    | Remove duplicates                                                     |
| `--google-skip-extras-files`, `--gsef`          | Skip `-edited`, `-effects` images                                     |
| `--google-skip-move-albums`, `--gsma`           | Skip moving albums to "Albums" folder                                 |
| `--google-skip-gpth-tool`, `--gsgt`             | Skip processing with GPTH Tool (not recommended)                      |
| `--show-gpth-info`, `--gpthInfo`                | Show GPTH progress messages                                           |
| `--show-gpth-errors`, `--gpthErr`               | Show GPTH error messages                                              |

### 🧪 Examples
```bash
PhotoMigrator.run --gTakeout "~/Takeout" --gafs "year/month" --grdf --gsef
PhotoMigrator.run --gTakeout "~/Takeout" --gcsa --gofs "cleaned"
PhotoMigrator.run --gTakeout "Takeout" --gics --gmtf true
```

---

## 🖼️ Synology / Immich Photo Management

| Argument                                  | Description                                    |
|-------------------------------------------|------------------------------------------------|
| `--upload-albums`, `--uAlb`               | Upload all subfolders as albums                |
| `--download-albums`, `--dAlb`             | Download specific albums                       |
| `--upload-all`, `--uAll`                  | Upload all assets and albums from input folder |
| `--download-all`, `--dAll`                | Download all assets and albums                 |
| `--remove-orphan-assets`, `--rOrphan`     | Delete orphan assets                           |
| `--remove-all-assets`, `--rAll`           | Delete all assets and albums (DANGER!)         |
| `--remove-all-albums`, `--rAllAlb`        | Delete all albums (assets optional)            |
| `--remove-albums`, `--rAlb`               | Delete albums matching pattern                 |
| `--remove-empty-albums`, `--rEmpAlb`      | Delete empty albums                            |
| `--remove-duplicates-albums`, `--rDupAlb` | Delete duplicate albums                        |
| `--merge-duplicates-albums`, `--mDupAlb`  | Merge duplicate albums                         |
| `--rename-albums`, `--renAlb`             | Rename albums matching pattern                 |

### 🧪 Examples
```bash
PhotoMigrator.run --client=synology --uAlb "Albums" --id 1
PhotoMigrator.run --client=immich --dAlb "Vacaciones,Navidad" --o "Backups"
PhotoMigrator.run --client=synology --rAlb "tmp_*" --rAlbAss
```

---

## 🛠️ Other Standalone Features

| Argument                                       | Description                                                    |
|------------------------------------------------|----------------------------------------------------------------|
| `--find-duplicates`, `--findDup`               | Find duplicates in folder(s). Action: `list`, `move`, `delete` |
| `--process-duplicates`, `--procDup`            | Execute actions from a reviewed duplicates CSV file            |
| `--fix-symlinks-broken`, `--fixSym`            | Fix broken symlinks in folder                                  |
| `--rename-folders-content-based`, `--renFldcb` | Rename folders based on media content date                     |

### 🧪 Examples
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
hotoMigrator.run --rename-folders-content-based="/mnt/albums"

Renames album folders based on content creation dates.
```
