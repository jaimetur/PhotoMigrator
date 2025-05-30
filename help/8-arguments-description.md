# 📸 PhotoMigrator - Command Line Arguments Documentation

---

## 🧱 Core Arguments

| Argument        | Parameter | Type | Valid Values        | Description                    |
|----------------|-----------|------|----------------------|--------------------------------|
| `--help`       | -         | -    | -                    | Show help message and exit     |
| `--version`    | -         | -    | -                    | Show version and exit          |

### 🧪 Examples

```bash
# Show help
PhotoMigrator.run --help

# Show version
PhotoMigrator.run --version
```

---

## 🔄 Automatic Migration

| Argument              | Parameter   | Type | Valid Values              | Description                                           |
|----------------------|-------------|------|----------------------------|-------------------------------------------------------|
| `--source`           | `<SOURCE>`  | path / str | existing path<br>synology<br>immich | Source: Cloud service account or local path |
| `--target`           | `<TARGET>`  | path / str | existing path<br>synology<br>immich | Target: Cloud service account or local path |
| `--move-assets`      | -           | bool | true<br>false             | Move files instead of copying                        |
| `--dashboard`        | -           | bool | true<br>false<br>(default: true) | Show live dashboard during migration         |
| `--parallel-migration` | -         | bool | true<br>false<br>(default: true) | Run migration in parallel or sequential     |

### 🧪 Examples

```bash
# Migrate from Immich to Synology
PhotoMigrator.run --source=immich-1 --target=synology-2

# Migrate using local folders and move assets
PhotoMigrator.run --source=/Takeout --target=/Photos --move-assets=true

# Migrate with dashboard disabled and sequential mode
PhotoMigrator.run --source=immich-1 --target=synology-2 --dashboard=false --parallel-migration=false
```

---

## ⚙️ General Options

| Argument              | Parameter         | Type  | Valid Values                    | Description                                      |
|----------------------|-------------------|-------|----------------------------------|--------------------------------------------------|
| `--input-folder`     | `<INPUT_FOLDER>`  | path  | -                                | Input folder with files to process               |
| `--output-folder`    | `<OUTPUT_FOLDER>` | path  | -                                | Output folder to store processed results         |
| `--client`           | `<CLIENT>`        | str   | google-takeout<br>synology<br>immich | Select the cloud service client             |
| `--account-id`       | `<ID>`            | int   | 1<br>2<br>3<br>(default: 1)       | Account ID defined in `Config.ini`               |
| `--one-time-password`| -                 | bool  | -                                | Use OTP login for Synology 2FA                   |
| `--filter-from-date` | `<FROM_DATE>`     | date  | -                                | Filter assets from this date                     |
| `--filter-to-date`   | `<TO_DATE>`       | date  | -                                | Filter assets up to this date                    |
| `--filter-by-country`| `<COUNTRY>`       | str   | -                                | Filter assets by country                         |
| `--filter-by-city`   | `<CITY>`          | str   | -                                | Filter assets by city                            |
| `--filter-by-person` | `<PERSON>`        | str   | -                                | Filter assets by person                          |
| `--filter-by-type`   | `<TYPE>`          | str   | image<br>video<br>all<br>(default: all) | Filter assets by type                    |
| `--albums-folders`   | `<ALBUMS_FOLDER>` | path  | -                                | Create one album per subfolder                   |
| `--remove-albums-assets` | -            | bool  | -                                | Remove files inside deleted albums               |
| `--no-log-file`      | -                 | bool  | -                                | Skip saving output log file                      |
| `--log-level`        | `<LEVEL>`         | str   | debug<br>info<br>warning<br>error | Set log verbosity                                |

### 🧪 Examples

```bash
# Upload content from a local folder using Immich
PhotoMigrator.run --client=immich --input-folder=Photos --output-folder=Exported

# Filter images between two dates using Google Takeout
PhotoMigrator.run --client=google-takeout --filter-from-date=2020-01-01 --filter-to-date=2021-01-01 --filter-by-type=image

# Upload album folders using Synology client
PhotoMigrator.run --client=synology --input-folder=Albums --albums-folders=Albums2022
```