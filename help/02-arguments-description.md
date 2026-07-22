# 📚 Arguments Description

---
This section describe the different arguments and flags used by the tool.  
- An **argument** is a modifier that is followed by any parameter.
- On the other hand, a **flag** is a modifier that don't require any parameter, hence, if the flag is present the feature is enabled, otherwise, the feature is disabled.

There is also a [shorter version](02-arguments-description-short.md) of this document available.

> [!NOTE]
> For compiled binaries, macOS now uses `PhotoMigrator.command`. Linux and Synology SSH continue using `PhotoMigrator.bin`. If you are following the examples below on macOS, replace `PhotoMigrator.bin` with `PhotoMigrator.command`.

## 🖥️ Launcher Flags

These flags are handled before the normal argparse parser starts, so they are launcher controls rather than regular feature arguments.

| Argument | Parameter | Type | Valid Values | Description                        |
|----------|-----------|:----:|:------------:|------------------------------------|
| `--gui`  |           | flag |              | Force the Desktop GUI explicitly.  |
| `--tui`  |           | flag |              | Force the Terminal TUI explicitly. |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --gui
PhotoMigrator.bin --tui
PhotoMigrator.bin --gui --configuration-file ./Config.ini
PhotoMigrator.bin --gui --configuration-file /srv/PhotoMigrator/custom.ini
```

Notes:
- GUI and TUI now also read `--configuration-file` during startup so the selected interactive interface can open with a custom config path already loaded.
- If `--configuration-file` is not provided, both interfaces default to `./Config.ini` in the current execution folder.

## 🧩 Core Arguments

| Argument                                           | Parameter                    |   Type   |                          Valid Values                          | Description                                                                                                                                                                                                           |
|----------------------------------------------------|------------------------------|:--------:|:--------------------------------------------------------------:|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h`,<br>`--help`                                  |                              |   flag   |                                                                | Displays the help message and exits.                                                                                                                                                                                  |
| `-v`,<br>`--version`                               |                              |   flag   |                                                                | Shows the tool version and exits.                                                                                                                                                                                     |
| `-config`,<br>`--configuration-file`               | `<CONFIGURATION_FILE>`       | FilePath |                 `Any valid Configuration File`                 | Specify the file that contains the Configuration to connect to the different Photo Cloud Services. The same argument is also honored by GUI/TUI launch so interactive interfaces can open with that file preselected. |
| `-confirm`,<br>`--request-user-confirmation`       | `[true,false]`               | boolean  |                        `true`, `false`                         | Requests confirmation before executing a feature (default: `true`). Set `false` for unattended runs.                                                                                                                  |
| `-noLog`,<br>`--no-log-file`                       |                              |   flag   |                                                                | Disables writing to log file.                                                                                                                                                                                         |
| `-logLevel`,<br>`--log-level`                      | `<LEVEL>`                    |  string  | `VERBOSE`, <br>`DEBUG`, <br>`INFO`, <br>`WARNING`, <br>`ERROR` | Sets logging verbosity.                                                                                                                                                                                               |
| `-logFormat`,<br>`--log-format`                    | `<FORMAT>`                   |  string  |                  `LOG`, <br>`TXT`, <br>`ALL`                   | Sets log file format.                                                                                                                                                                                                 |
| `-fnAlbums`,<br>`--foldername-albums`              | `<ALBUMS_FOLDER>`            |  string  |             `any folder name` (default: `Albums`)              | Specify the folder name to store all your processed photos associated to any Album.                                                                                                                                   |
| `-fnNoAlbums`,<br>`--foldername-no-albums`         | `<NO_ALBUMS_FOLDER>`         |  string  |            `any folder name` (default: `No_Albums`)            | Specify the cloud/local-library folder name for assets without any album association.                                                                                                                                 |
| `-fnAllPhotos`,<br>`--foldername-all-photos`       | `<ALL_PHOTOS_FOLDER>`        |  string  |           `any folder name` (default: `ALL_PHOTOS`)            | Specify the Takeout master-library folder name containing all assets.                                                                                                                                                 |
| `-fnLogs`,<br>`--foldername-logs`                  | `<LOG_FOLDER>`               |   path   |              `any folder name` (default: `Logs`)               | Specify the folder name to save the execution Logs.                                                                                                                                                                   |
| `-fnDuplicat`,<br>`--foldername-duplicates-output` | `<DUPLICATES_OUTPUT_FOLDER>` |   path   |        `any folder name` (default: `Duplicates_output`)        | Specify the folder name to save the outputs of 'Find Duplicates' Feature.                                                                                                                                             |
| `-fnExtDates`,<br>`--foldername-extracted-dates`   | `<EXTRACTED_DATES_FOLDER>`   |   path   |         `any folder name` (default: `Extracted_Dates`)         | Specify the folder name to save the Metadata outputs of 'Extracted Dates'.                                                                                                                                            |
| `-exeGpthTool`,<br>`--exec-gpth-tool`              | `<GPTH_PATH>`                | FilePath |  `GPTH binary complete path` (default: `use internal binary`)  | Specify an external version of GPTH Tool binary.                                                                                                                                                                      |
| `-exeExifTool`,<br>`--exec-exif-tool`              | `<EXIFTOOL_PATH>`            | FilePath |  `EXIF binary complete path` (default: `use internal binary`)  | Specify an external version of GPTH Tool binary.                                                                                                                                                                      |

---
## ⚙️ General Options
Following general arguments have different purposes depending on the Execution Mode.

| Argument                                  | Parameter          |    Type     |                                               Valid Values                                               | Description                                                                                                                                                   |
|-------------------------------------------|--------------------|:-----------:|:--------------------------------------------------------------------------------------------------------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-i`,<br>`--input-folder`                 | `<INPUT_FOLDER>`   |    path     |                                             `existing path`                                              | Folder containing assets to be processed.                                                                                                                     |
| `-o`,<br>`--output-folder`                | `<OUTPUT_FOLDER>`  |    path     |                                               `valid path`                                               | Folder where processed assets or results will be saved.                                                                                                       |
| `-localFolder`,<br>`--local-folder`       | `<LOCAL_FOLDER>`   |    path     |                                             `existing path`                                              | Managed library root required with `--client=local-folder`. Its physical assets are stored in `No_Albums` and album membership is represented under `Albums`. |
| `-client`,<br>`--client`                  | `<CLIENT>`         |   string    | `google-takeout`, <br>`google-photos`, <br>`synology`, <br>`immich`, <br>`nextcloud`, <br>`local-folder` | Specifies the service or managed local library to interact with.                                                                                              |
| `-id`,<br>`--account-id`                  | `<ID>`             |     int     |                                     `1`, `2`, `3` <br>`(default: 1)`                                     | ID of the configured cloud account in `Config.ini`; unused by Local Folder.                                                                                   |
| `-from`,<br>`--filter-from-date`          | `<FROM_DATE>`      |    date     |                                 `yyyy-mm-dd`, <br>`yyyy-mm`, <br>`yyyy`                                  | Filters assets from this date onward.                                                                                                                         |
| `-to`,<br>`--filter-to-date`              | `<TO_DATE>`        |    date     |                                 `yyyy-mm-dd`, <br>`yyyy-mm`, <br>`yyyy`                                  | Filters assets up to this date.                                                                                                                               |
| `-type`,<br>`--filter-by-type`            | `<TYPE>`           |   string    |                               `image`, `video`, `all` <br>`(default: all)`                               | Filters assets by type.                                                                                                                                       |
| `-country`,<br>`--filter-by-country`      | `<COUNTRY>`        |   string    |                                              `country-name`                                              | Filters assets by country.                                                                                                                                    |
| `-city`,<br>`--filter-by-city`            | `<CITY>`           |   string    |                                               `city-name`                                                | Filters assets by city.                                                                                                                                       |
| `-person`,<br>`--filter-by-person`        | `<PERSON>`         |   string    |                                              `person-name`                                               | Filters assets by person name.                                                                                                                                |
| `-exFolders`,<br>`--exclude-folders`      | `<FOLDER_PATTERN>` | string/list |                                    `glob patterns` (multiple allowed)                                    | Excludes folders matching the provided glob patterns.                                                                                                         |
| `-exFiles`,<br>`--exclude-files`          | `<FILE_PATTERN>`   | string/list |                                    `glob patterns` (multiple allowed)                                    | Excludes files matching the provided glob patterns.                                                                                                           |
| `-AlbFolder`,<br>`--albums-folders`       | `<ALBUMS_FOLDER>`  |    path     |                                             `existing path`                                              | Creates albums for subfolders inside.                                                                                                                         |
| `-rAlbAsset`,<br>`--remove-albums-assets` |                    |    flag     |                                                                                                          | Removes assets inside albums when albums are removed.                                                                                                         |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --input-folder=/mnt/import --output-folder=/mnt/export
PhotoMigrator.bin --filter-from-date=2022-01-01 --filter-to-date=2022-12-31
PhotoMigrator.bin --filter-by-type=video --log-level=debug
```

---
## 🚀 Automatic Migration
Following arguments allow you to execute the Automatic Migration Process to migrate your assets from one Photo Cloud Service to other, or from two different accounts within the same Photo Cloud service.

| Argument                               | Parameter  |       Type        |                                    Valid Values                                     | Description                                             |
|----------------------------------------|------------|:-----------------:|:-----------------------------------------------------------------------------------:|---------------------------------------------------------|
| `-source`,<br>`--source`               | `<SOURCE>` | path / <br>string | `existing path`, <br>`synology`, <br>`immich`, <br>`nextcloud`, <br>`google-photos` | Defines the source for the automatic migration process. |
| `-target`,<br>`--target`               | `<TARGET>` | path / <br>string | `existing path`, <br>`synology`, <br>`immich`, <br>`nextcloud`, <br>`google-photos` | Defines the target for the automatic migration process. |
| `-move`,<br>`--move-assets`            | `<bool>`   |       bool        |                       `true`, `false` <br>`(default: false)`                        | Enable / Disables move assets instead of copying them.  |
| `-dashboard`,<br>`--dashboard`         | `<bool>`   |       bool        |                        `true`, `false` <br>`(default: true)`                        | Enables / Disables the live dashboard during migration. |
| `-parallel`,<br>`--parallel-migration` | `<bool>`   |       bool        |                        `true`, `false` <br>`(default: true)`                        | Enables / Disables parallel asset migration.            |

#### 🧪 Examples:
```bash
PhotoMigrator.bin --source=immich-1 --target=synology-2
PhotoMigrator.bin --source=/mnt/photos --target=/mnt/synology --move-assets=true
PhotoMigrator.bin --source=synology-1 --target=immich-1 --parallel-migration=false
```

---
## 🗃️ Google Takeout Management
In this mode, you can use more than one optional arguments and flags from the below list.  
If only the argument `-gTakeout, --google-takeout <TAKEOUT_FOLDER>` is detected, then the Tool will use the default values for the rest of the flags for this extra mode.

Following arguments allow you to interact with Google Photos Takeout Folder.   

| Argument                                            | Parameter          |  Type  |                                     Valid Values                                      | Description                                                                                                               |
|-----------------------------------------------------|--------------------|:------:|:-------------------------------------------------------------------------------------:|---------------------------------------------------------------------------------------------------------------------------|
| `-gTakeout`,<br>`--google-takeout`                  | `<TAKEOUT_FOLDER>` |  path  |                                                                                       | Path to the Takeout folder (either zipped or unzipped) to process.                                                        |
| `-gofs`,<br>`--google-output-folder-suffix`         | `<SUFFIX>`         | string |                               `(default: 'processed')`                                | Suffix to add to the output folder.                                                                                       |
| `-gafs`,<br>`--google-albums-folders-structure`     | `<STRUCTURE>`      | string |  `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: flatten)`   | Folder structure for <ALBUMS_FOLDER>.                                                                                     |
| `-gaps`,<br>`--google-all-photos-folders-structure` | `<STRUCTURE>`      | string | `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: year/month)` | Folder structure for the Takeout `<ALL_PHOTOS_FOLDER>` master library.                                                    |
| `-gics`,<br>`--google-ignore-check-structure`       |                    |  flag  |                                                                                       | Ignores structure check of Takeout folders.                                                                               |
| `-gnsa`,<br>`--google-no-symbolic-albums`           |                    |  flag  |                                                                                       | Duplicates Albums assets instead of create symlinks to original asset in `<ALL_PHOTOS_FOLDER>`. (requires more HDD space) |
| `-grdf`,<br>`--google-remove-duplicates-files`      |                    |  flag  |                                                                                       | Removes duplicate files in the output folder.                                                                             |
| `-graf`,<br>`--google-rename-albums-folders`        |                    |  flag  |                                                                                       | Renames albums folders based on content dates.                                                                            |
| `-gsef`,<br>`--google-skip-extras-files`            |                    |  flag  |                                                                                       | Skips extra Google photos like edited/effects.                                                                            |
| `-gsma`,<br>`--google-skip-move-albums`             |                    |  flag  |                                                                                       | Skips moving albums to `<ALBUMS_FOLDER>`.                                                                                 |
| `-gSkipGpth`,<br>`--google-skip-gpth-tool`          |                    |  flag  |                                                                                       | Skips GPTH tool processing (not recommended).                                                                             |
| `-gSkipPrep`,<br>`--google-skip-preprocess`         |                    |  flag  |                                                                                       | Skips Pre-process Google Takeout folder (not recommended).                                                                |
| `-gSkipPost`,<br>`--google-skip-postprocess`        |                    |  flag  |                                                                                       | Skips Post-process Google Takeout folder (not recommended).                                                               |
| `-gKeepTakeout`,<br>`--google-keep-takeout-folder`  |                    |  flag  |                                                                                       | Keeps a untouched copy of your original Takeout folder. (requires double HDD space).                                      |
| `-gpthInfo`,<br>`--show-gpth-info`                  | `<bool>`           |  bool  |                         `true`, `false` <br>`(default: true)`                         | Show GPTH progress messages.                                                                                              |
| `-gpthError`,<br>`--show-gpth-errors`               | `<bool>`           |  bool  |                         `true`, `false` <br>`(default: true)`                         | Show GPTH error messages.                                                                                                 |
| `-gpthNoLog`,<br>`--gpth-no-log`                    |                    |  flag  |                                                                                       | Skip Save GPTH log messages into output folder.                                                                           |
| `-gPeople`,<br>`--google-process-people`            | `<bool>`           |  bool  |                        `true`,<br>`false`<br>`(default: true)`                        | Processes Google JSON people labels and writes `takeout_people_metadata.json`. Set `false` to skip people processing.     |


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

| Argument                                            | Parameter                |  Type  |                                     Valid Values                                      | Description                                                                                                                                                                      |
|-----------------------------------------------------|--------------------------|:------:|:-------------------------------------------------------------------------------------:|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-iTakeout`,<br>`--icloud-takeout`                  | `<ICLOUD_EXPORT_FOLDER>` |  path  |                                                                                       | Path to the iCloud export folder (either zipped or unzipped) to process.                                                                                                         |
| `-iofs`,<br>`--icloud-output-folder-suffix`         | `<SUFFIX>`               | string |                               `(default: 'processed')`                                | Suffix to add to the iCloud processed output folder.                                                                                                                             |
| `-iafs`,<br>`--icloud-albums-folders-structure`     | `<STRUCTURE>`            | string |  `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: flatten)`   | Folder structure for reconstructed iCloud album folders.                                                                                                                         |
| `-iaps`,<br>`--icloud-all-photos-folders-structure` | `<STRUCTURE>`            | string | `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: year/month)` | Folder structure for the iCloud Takeout `<ALL_PHOTOS_FOLDER>` master library.                                                                                                    |
| `-insa`,<br>`--icloud-no-symbolic-albums`           |                          |  flag  |                                                                                       | Duplicate reconstructed iCloud album assets instead of creating symlinks to original assets in `<ALL_PHOTOS_FOLDER>`. By default, `Albums` and `Memories` are built as symlinks. |
| `-iMem`,<br>`--icloud-include-memories`             |                          |  flag  |                                                                                       | Also reconstruct iCloud `Memories` CSV collections as folders. In the Web Interface, TUI, and GUI this option is pre-selected by default.                                        |
| `-iNExif`,<br>`--icloud-prefer-native-exif-writer`  |                          |  flag  |                                                                                       | Prefer the native EXIF writer for supported iCloud photo files before falling back to `ExifTool`. In the Web Interface, TUI, and GUI this option is pre-selected by default.     |


#### 🧪 Examples:
```bash
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport"
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-no-symbolic-albums
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-include-memories --icloud-albums-folders-structure=year/month
PhotoMigrator.bin --icloud-takeout="/home/user/iCloudExport" --icloud-prefer-native-exif-writer

or using short arguments,
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -iofs="cleaned"
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -iafs="year/month" -inas="year/month"
PhotoMigrator.bin -iTakeout="/home/user/iCloudExport" -insa -iMem
```

---
## 🖼️ Google Photos / Synology / Immich / NextCloud / Local Folder Management
To use the following features, use `--client=[synology, immich, nextcloud, google-photos, local-folder]`. Local Folder additionally requires `--local-folder <LOCAL_FOLDER>` as its managed library root.
Cloud clients can optionally use `--id=[1-3]` to select an account defined in `Config.ini`. `--account-id` is not used by Local Folder.
If more than one optional arguments are detected, only the first one will be executed.  

The same modules are available for Google Photos, Synology, Immich, NextCloud, and Local Folder.

| Argument                                             | Parameter                                       |       Type        |                                                                     Valid Values                                                                      | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|------------------------------------------------------|-------------------------------------------------|:-----------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------:|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-uAlb`,<br>`--upload-albums`                        | `<ALBUMS_FOLDER>`                               |       path        |                                                                    `existing path`                                                                    | Uploads albums from folders to the selected photo client.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `-dAlb`,<br>`--download-albums`                      | `<ALBUM_NAMES>`                                 |       list        |                                                                   `existing album`                                                                    | Downloads albums by name to the output folder.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `-uAll`,<br>`--upload-all`                           | `<INPUT_FOLDER>`                                |       path        |                                                                    `existing path`                                                                    | Uploads all assets and creates albums by subfolder.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `-iPeople`,<br>`--import-people`                     | `<bool>`                                        |       bool        |                                                         `true`, `false`<br>`(default: true)`                                                          | Immich Upload All, Upload Albums, or Automatic Migration with an Immich target only. Imports Google Takeout people labels from `takeout_people_metadata.json` or raw Google JSON sidecars.                                                                                                                                                                                                                                                                                                                                                                                                         |
| `-cStacks`,<br>`--create-stacks`                     | `<bool>`                                        |       bool        |                                                         `true`, `false`<br>`(default: true)`                                                          | Immich Upload All, Upload Albums, or Automatic Migration with an Immich target only. Creates stacks for burst-like photos after upload.                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `-prefCanAlb`,<br>`--prefer-canonical-album-names`   |                                                 |       flag        |                                                                                                                                                       | Normalizes newly created destination album names to the preferred clean keeper form during cloud uploads and Automatic Migration, even when the target does not already contain a similar album (for example `Album_1` -> `Album`, `New_Album 1` -> `New Album`).                                                                                                                                                                                                                                                                                                                                  |
| `-consSimAlb`,<br>`--consolidate-similar-albums`     |                                                 |       flag        |                                                                                                                                                       | Reuses and consolidates equivalent album families during cloud uploads and Automatic Migration. In addition to canonical names, it supports compatible `YYYY`/`YYYY-MM`/`YYYY-MM-DD` prefixes (specific dates require at least 95% asset-date coverage) and guarded end truncation (two shared words and the same dominant asset year). Supported cloud targets merge redundant variants into the preferred keeper. `Immich`, `Synology`, and `NextCloud` then remove redundant albums; `Google Photos` keeps them because its API cannot delete albums.                                           |
| `-consAlbNames`,<br>`--consolidate-albums-names`     |                                                 |       flag        |                                                                                                                                                       | Consolidates the same guarded equivalent-name, date-prefix, and end-truncation families directly in the target service without uploading new assets. Its preview table shows the group, match rule, keeper, candidates, and comments explaining the applied keeper decision. `Immich`, `Synology`, and `NextCloud` remove redundant albums afterwards; `Google Photos` keeps them because its API cannot delete albums.                                                                                                                                                                            |
| `-dAll`,<br>`--download-all`                         | `<OUTPUT_FOLDER>`                               |       path        |                                                                    `existing path`                                                                    | Downloads all albums and assets to this folder.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `-renAlb`,<br>`--rename-albums`                      | `<ALBUMS_NAME_PATTERN>` `<PATTERN_REPLACEMENT>` | `string` `string` |                                                               `text / wildcard / regex`                                                               | Renames albums using a name pattern.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `-rAlb`,<br>`--remove-albums`                        | `<PATTERN>`                                     |      string       |                                                               `text / wildcard / regex`                                                               | Removes albums matching name pattern.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `-prevAlbAct`,<br>`--preview-album-actions`          | `<true\|false>`                                 |      boolean      |                                                                   `(default: true)`                                                                   | Previews rename/remove/consolidation matches and asks for confirmation. Use `--no-preview-album-actions` to disable it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `-rEmpAlb`,<br>`--remove-empty-albums`               |                                                 |       flag        |                                                                                                                                                       | Removes empty albums.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `-rDupAlb`,<br>`--remove-duplicates-albums`          |                                                 |       flag        |                                                                                                                                                       | Removes duplicate albums with same name/size.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `-rDupAst`,<br>`--remove-duplicates-assets`          |                                                 |       flag        |                                                                                                                                                       | Removes duplicate physical assets. Immich uses native visual duplicate groups by default; other cloud services and Local Folder group exact filename-and-size matches. Requires `--client` and `--dup-asset-keeper`. Google Photos reports its public API deletion limitation and makes no changes.                                                                                                                                                                                                                                                                                                |
| `-immichDupAlgo`,<br>`--dup-immich-native-algorithm` | `<true\|false>`                                 |      boolean      |                                                                   `(default: true)`                                                                   | Immich `Remove Duplicates Assets` only. Native detection compares asset similarity rather than filename or size. When disabled, PhotoMigrator groups exact filename-and-size matches, useful when the same processed Takeout was uploaded on different dates and an EXIF tag difference prevented Immich from rejecting the later upload.                                                                                                                                                                                                                                                          |
| `-immichDupDel`,<br>`--dup-immich-native-deletion`   | `<true\|false>`                                 |      boolean      |                                                        `(default: true with native detection)`                                                        | Immich `Remove Duplicates Assets` only. `true` uses Immich's Alpha resolver: it merges albums, favorites, highest rating, combined descriptions, most restrictive visibility, matching locations, and tags, then moves redundant assets to trash. `false` uses PhotoMigrator's guarded manual merge: the same fields plus missing capture date, stacks, and safely transferable assigned faces/persons, then permanently deletes redundant assets. Unsafe face transfers are omitted without blocking deletion of the group. It cannot be supplied whenever `--dup-immich-native-algorithm=false`. |
| `-dupKeeper`,<br>`--dup-asset-keeper`                | `<KEEPER>`                                      |      string       | `more-people/tags-then-better-quality`,<br>`more-people/tags-then-oldest`,<br>`more-people/tags-then-newest`,<br>`better-quality`, `oldest`, `newest` | Required module selector for `--remove-duplicates-assets`. The three `more-people/tags-*` strategies retain the asset with the largest distinct people count, then tag count, then use the named tie breaker. `more-people/tags-then-better-quality` is available only with Immich native detection. Immich defaults to `better-quality` with native detection and `more-people/tags-then-newest` without it.                                                                                                                                                                                      |
| `-mDupAlb`,<br>`--merge-duplicates-albums`           |                                                 |       flag        |                                                                                                                                                       | Merges duplicate albums (moves all assets).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `-rAll`,<br>`--remove-all-assets`                    |                                                 |       flag        |                                                                                                                                                       | Removes all albums and assets from the client.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `-rAllAlb`,<br>`--remove-all-albums`                 |                                                 |       flag        |                                                                                                                                                       | Removes all albums from the photo client.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `-OTP`,<br>`--one-time-password`                     |                                                 |       flag        |                                                                                                                                                       | Enables / Disables OTP login for Synology (2FA).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |


#### 🧪 Examples:
```bash
PhotoMigrator.bin --client=immich --upload-all=/mnt/pictures
PhotoMigrator.bin --client=synology --download-albums "album1 album2 album3" --output-folder=/mnt/backup
PhotoMigrator.bin --client=synology --remove-empty-albums --one-time-password
PhotoMigrator.bin --client=local-folder --local-folder=/mnt/managed-library --upload-all=/mnt/pictures

or using short arguments,
PhotoMigrator.bin -client=synology -uAlb="Albums" -id=1
PhotoMigrator.bin -client=immich -dAlb="Vacaciones,Navidad" -o="Backups"
PhotoMigrator.bin -client=synology -rAlb="tmp_*" -rAlbAsset -OTP
```

---
## 🛠️ Standalone Features
If more than one Feature is detected, only the first one will be executed.  
Following arguments can be used to execute the Tool in any of the usefully additionals Extra Standalone Features included.  

| Argument                                         | Parameter              | Type          |                                     Valid Values                                      | Description                                                                                                                                                                    |
|--------------------------------------------------|------------------------|---------------|:-------------------------------------------------------------------------------------:|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-fixSym` ,<br>`--fix-symlinks-broken`           | `<FOLDER>`             | path          |                                    `existing path`                                    | Fixes broken album symbolic links.                                                                                                                                             |
| `-renFldcb`,<br>`--rename-folders-content-based` | `<ALBUMS_FOLDER>`      | path          |                                    `existing path`                                    | Renames folders based on internal dates.                                                                                                                                       |
| `-orgDate`,<br>`--organize-local-folder-by-date` | `<INPUT_FOLDER>`       | path          |                                    `existing path`                                    | Creates a processed local copy of the input folder and reorganizes its media by date. If `--output-folder` is omitted, the tool creates `<INPUT_FOLDER>_<SUFFIX>_<TIMESTAMP>`. |
| `-olfs`,<br>`--organize-output-folder-suffix`    | `<SUFFIX>`             | string        |                        `any suffix` <br>`(default: processed)`                        | Changes the generated suffix used by `--organize-local-folder-by-date` when no explicit `--output-folder` is provided. Ignored if `--output-folder` is set.                    |
| `-olstr`,<br>`--organize-folder-structure`       | `<STRUCTURE>`          | string        | `flatten`, <br>`year`, <br>`year/month`, <br>`year-month` <br>`(default: year/month)` | Selects the folder layout used by `--organize-local-folder-by-date`.                                                                                                           |
| `-omove`,<br>`--move-original-files`             |                        | flag          |                                                                                       | Used together with `--organize-local-folder-by-date`, move the original files into the destination folder instead of copying them first.                                       |
| `-findDup`,<br>`--find-duplicates`               | `<ACTION> <FOLDER(S)>` | string + list |                    `move`, `remove`, `list` <br>+<br> `[folders]`                     | Finds duplicate files in the given folders and applies the specified action. <br><br>If action is `list`, only the output CSV will be generated and no file will be touched.   |
| `-procDup`,<br>`--process-duplicates`            | `<CSV_FILE>`           | path          |                                    `path to .csv`                                     | Processes duplicate file actions from CSV and applies what the action set in Action column for each file.                                                                      |

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
PhotoMigrator.bin --google-takeout="/home/user/Takeout"

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
PhotoMigrator.bin --rename-folders-content-based="/mnt/albums"

Renames album folders based on content creation dates.
```

```bash
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --organize-folder-structure=year/month

Creates a processed copy of the input folder and organizes media into a year/month structure.
```

```bash
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --output-folder="/mnt/organized"

Creates the organized library directly in the explicit output folder, without generating a suffix/timestamp folder name.
```

```bash
PhotoMigrator.bin --organize-local-folder-by-date="/mnt/unsorted" --move-original-files --organize-output-folder-suffix=archive

Moves the original files into a generated '<INPUT_FOLDER>_archive_<TIMESTAMP>' output folder before reorganizing them by date.
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
