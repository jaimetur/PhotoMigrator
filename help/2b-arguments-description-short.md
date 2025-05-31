# 📸 PhotoMigrator Command Line Arguments

## 🧱 Core Arguments

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

## 🔄 Automatic Migration Process

| Argument               | Description                                                       |
|------------------------|-------------------------------------------------------------------|
| `--source <SOURCE>`    | Source service or folder: `immich-1`, `synology-2`, or local path |
| `--target <TARGET>`    | Target service or folder: same format as `--source`               |
| `--move-assets`        | Move instead of copy files (`true` or `false`)                    |
| `--dashboard`          | Show live dashboard during migration (`true` or `false`)          |
| `--parallel-migration` | Run migration in parallel or sequential (`true` or `false`)       |

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

## 📦 Google Photos Takeout Management

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

## 🧩 Other Standalone Features

| Argument                                       | Description                                                    |
|------------------------------------------------|----------------------------------------------------------------|
| `--find-duplicates`, `--findDup`               | Find duplicates in folder(s). Action: `list`, `move`, `delete` |
| `--process-duplicates`, `--procDup`            | Execute actions from a reviewed duplicates CSV file            |
| `--fix-symlinks-broken`, `--fixSym`            | Fix broken symlinks in folder                                  |
| `--rename-folders-content-based`, `--renFldcb` | Rename folders based on media content date                     |

### 🧪 Examples
```bash
PhotoMigrator.run --findDup move "Photos1" "Photos2"
PhotoMigrator.run --procDup "reviewed_duplicates.csv"
PhotoMigrator.run --fixSym "Takeout_processed_2025-05-30"
```
