# 📸 NextCloud Photos Management

From version 4.0.0 onwards, the Tool can connect to your NextCloud account using WebDAV and manage your photo library.

### Features included:
1. Upload Album(s) (from folder)
2. Download Album(s) (into folder)
3. Upload ALL (from folder)
4. Download ALL (into folder)
5. Remove ALL Assets
6. Remove ALL Albums
7. Remove Albums by Name Pattern
8. Rename Albums by Name Pattern
9. Remove Empty Albums
10. Remove Duplicates Albums (currently no-op)
11. Remove Duplicates Assets
12. Merge Duplicates Albums (currently no-op)
13. Consolidate Albums Names

You can apply filters in NextCloud modules.

The available filters are:
- **by Type:**
  - argument: `-type, --filter-by-type`
  - valid values: `image`, `video`, `all`
- **by Dates:**
  - arguments:
    - `-from, --filter-from-date`
    - `-to, --filter-to-date`
  - valid formats:
    - `dd/mm/yyyy`
    - `dd-mm-yyyy`
    - `yyyy/mm/dd`
    - `yyyy-mm-dd`
    - `mm/yyyy`
    - `mm-yyyy`
    - `yyyy/mm`
    - `yyyy-mm`
    - `yyyy`
- **by Country / City / Person:**
  - arguments:
    - `-country, --filter-by-country`
    - `-city, --filter-by-city`
    - `-person, --filter-by-person`
  - currently not available in WebDAV-based NextCloud integration (they are ignored with warning).

The credentials are loaded from the `Config.ini` section below:

```ini
# Configuration for NextCloud Photos
[NextCloud Photos]
NEXTCLOUD_URL                   = http://192.168.1.11:8080
NEXTCLOUD_MAX_PARALLEL_UPLOADS  = 12
NEXTCLOUD_MAX_PARALLEL_DOWNLOADS= 16
NEXTCLOUD_USE_SYSTEM_PROXY      = false
NEXTCLOUD_USERNAME_1            = username_1
NEXTCLOUD_PASSWORD_1            = app_password_1
NEXTCLOUD_PHOTOS_FOLDER_1       = /Photos/ALL_Photos
NEXTCLOUD_ALBUMS_FOLDER_1       = /Photos/Albums
NEXTCLOUD_USERNAME_2            = username_2
NEXTCLOUD_PASSWORD_2            = app_password_2
NEXTCLOUD_PHOTOS_FOLDER_2       = /Photos/ALL_Photos
NEXTCLOUD_ALBUMS_FOLDER_2       = /Photos/Albums
NEXTCLOUD_USERNAME_3            = username_3
NEXTCLOUD_PASSWORD_3            = app_password_3
NEXTCLOUD_PHOTOS_FOLDER_3       = /Photos/ALL_Photos
NEXTCLOUD_ALBUMS_FOLDER_3       = /Photos/Albums
```

> [!NOTE]  
> To use all those features, it is mandatory to use the argument _**`--client=nextcloud`**_ to specify NextCloud Photos as the service that you want to connect.  
> 
> If you want to connect to an account ID different that 1 (suffixed with _2 or _3) you can use the argument _**`-id, -account-id`**_ to specify the account 2 or 3 as needed. 

> [!TIP]
> In Docker/Compose/Kubernetes, you can override these settings without editing `Config.ini` by using environment variables with the same key names, for example `NEXTCLOUD_URL`, `NEXTCLOUD_USERNAME_1`, `NEXTCLOUD_PASSWORD_1`, `NEXTCLOUD_PHOTOS_FOLDER_1`, `NEXTCLOUD_ALBUMS_FOLDER_1`.
> Docker-secret style variables such as `NEXTCLOUD_PASSWORD_1_FILE=/run/secrets/nextcloud_password_1` are also supported.
> Runtime precedence is: environment variable > `Config.ini` > template default.

> [!TIP]
> `NEXTCLOUD_MAX_PARALLEL_UPLOADS` controls parallel uploads.
> Recommended values in LAN are usually between `8` and `16`.

> [!NOTE]
> For compiled binaries, macOS now uses `PhotoMigrator.command`. Linux and Synology SSH continue using `PhotoMigrator.bin`. Replace the binary name accordingly when following the CLI examples below.
>
> `NEXTCLOUD_MAX_PARALLEL_DOWNLOADS` controls parallel downloads.
> Recommended values in LAN are usually between `12` and `24`.
>
> `NEXTCLOUD_USE_SYSTEM_PROXY=false` means PhotoMigrator connects directly and ignores `HTTP_PROXY` / `HTTPS_PROXY`.

> [!WARNING]
> Use `NEXTCLOUD_USE_SYSTEM_PROXY=true` only if your environment explicitly requires outbound proxy.
> In LAN setups, enabling proxy by mistake can cause large per-request latency.


## Upload Albums (from Local Folder) into NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --upload-albums <ALBUMS_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud URL and account credentials (App Password recommended).
- **Explanation:**
  - The Tool creates one album per subfolder inside `<ALBUMS_FOLDER>` and uploads supported assets.
  - In NextCloud implementation, files are uploaded under `NEXTCLOUD_ALBUMS_FOLDER_<id>/<AlbumName>`, and native Photos album association is handled automatically when supported.
  - By default only exact existing album names are reused and newly created albums keep the original source name.
  - Add `--prefer-canonical-album-names` if you want new destination albums to be created directly as the preferred clean keeper name.
  - Add `--consolidate-similar-albums` to also treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - When these behaviors are active, PhotoMigrator prefers the clean keeper name, merges the assets from numbered/underscored variants into that keeper, and reuses it for the incoming upload.
  - After the consolidation is confirmed, redundant NextCloud albums are removed automatically.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --upload-albums ./My_Albums_Folder
  ./PhotoMigrator.bin --client=nextcloud --upload-albums ./My_Albums_Folder --prefer-canonical-album-names --consolidate-similar-albums
  ```
  Example: if `New_Album`, `New Album`, and `New_Album 1` exist, PhotoMigrator prefers `New Album` as the keeper, merges the assets from the other variants into it, uploads the incoming album there, and then removes the redundant variants.
  If no equivalent album already exists in the target and you upload `New_Album 1`, the same flag creates `New Album` directly.


## Download Albums from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --download-albums <ALBUMS_NAME> --output-folder <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Downloads albums matching `<ALBUMS_NAME>` into `<OUTPUT_FOLDER>/Albums`.
  - You can use:
    - `ALL` to download all albums.
    - Patterns (for example `--download-albums "Trip*"`).
    - Multiple names in the same argument.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --download-albums "Album 1, Album 2" --output-folder ./Downloads
  ```

> [!WARNING]
> `<ALBUMS_NAME>` must exist in your NextCloud library, otherwise nothing is downloaded.


## Upload All (from Local Folder) into NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --upload-all <INPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials and `NEXTCLOUD_PHOTOS_FOLDER_<id>` / `NEXTCLOUD_ALBUMS_FOLDER_<id>`.
- **Explanation:**
  - Uploads all supported assets from `<INPUT_FOLDER>`.
  - If `<INPUT_FOLDER>/Albums` exists, each subfolder is treated as an album.
  - Assets outside `Albums` are uploaded into `NEXTCLOUD_PHOTOS_FOLDER_<id>`.
  - Album subfolders are uploaded into `NEXTCLOUD_ALBUMS_FOLDER_<id>`.
  - You can also provide extra albums folders via `-AlbFolder, --albums-folders`.
  - Add `--prefer-canonical-album-names` if you want new destination album names inside this flow to be normalized to the preferred clean keeper.
  - Add `--consolidate-similar-albums` if you want album uploads inside this flow to treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - When these behaviors are active, PhotoMigrator prefers the clean keeper name, merges the assets from redundant variants into that keeper, and removes the redundant NextCloud albums afterwards.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --upload-all ./MyLibrary
  ./PhotoMigrator.bin --client=nextcloud --upload-all ./MyLibrary --prefer-canonical-album-names --consolidate-similar-albums
  ```


## Download All from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --download-all <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Downloads all albums and assets from `NEXTCLOUD_PHOTOS_FOLDER_<id>`.
  - Albums are downloaded under `<OUTPUT_FOLDER>/Albums`.
  - Assets are downloaded under `<OUTPUT_FOLDER>/ALL_PHOTOS`.
  - If `NEXTCLOUD_ALBUMS_FOLDER_<id>` is inside `NEXTCLOUD_PHOTOS_FOLDER_<id>`, the albums subtree is excluded from the assets scan to avoid duplicate downloads.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --download-all ./MyLibrary
  ```


## Remove All Assets from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --remove-all-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes all assets from albums and non-album areas.
  - After removing assets, empty album folders are also removed.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --remove-all-assets
  ```

> [!CAUTION]
> This process is irreversible.


## Remove All Albums from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --remove-all-albums --remove-albums-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes all albums.
  - If `--remove-albums-assets` is set, it also removes assets associated to those albums.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --remove-all-albums --remove-albums-assets
  ```

> [!CAUTION]
> This process is irreversible.


## Remove Albums by Name Pattern from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --remove-albums <ALBUMS_NAME_PATTERN> --remove-albums-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes albums whose name matches `<ALBUMS_NAME_PATTERN>`.
  - The remove pattern can be plain text, a wildcard expression (for example `*Temp*` or `Temp*`), or a regular expression.
  - If `--remove-albums-assets` is set, assets inside removed albums are also removed.
  - If `--preview-album-actions` is set, the matching albums are listed and the tool asks for confirmation before deleting them.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --remove-albums "Temp" --preview-album-actions
  ./PhotoMigrator.bin --client=nextcloud --remove-albums "*Temp*" --preview-album-actions
  ./PhotoMigrator.bin --client=nextcloud --remove-albums "^Temp" --remove-albums-assets
  ```

> [!CAUTION]
> This process is irreversible.


## Rename Albums by Name Pattern from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --rename-albums <ALBUMS_NAME_PATTERN> <ALBUMS_NAME_REPLACEMENT_PATTERN>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Renames albums whose names match the provided pattern.
  - The rename pattern can be plain text (for example `--`), a wildcard expression (for example `*--*` or `--*`), or a regular expression.
  - If `--preview-album-actions` is set, the matching albums are listed and the tool asks for confirmation before renaming them.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --rename-albums "--" "-" --preview-album-actions
  ./PhotoMigrator.bin --client=nextcloud --rename-albums "--" "-"
  ./PhotoMigrator.bin --client=nextcloud --rename-albums "*--*" "-"
  ./PhotoMigrator.bin --client=nextcloud --rename-albums "\\d{4}-\\d{2}-\\d{2}" "DATE"
  ```


## Remove Empty Albums from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --remove-empty-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes albums that contain zero assets.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --remove-empty-albums
  ```


## Remove Duplicates Albums from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --remove-duplicates-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Current WebDAV integration keeps this operation as no-op.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --remove-duplicates-albums
  ```

> [!WARNING]
> This operation is currently a no-op in NextCloud integration.


## Remove Duplicates Assets from NextCloud Photos:
- **From:** v4.6.0
- **Usage:**
  - Set NextCloud as the client using _**`--client=nextcloud`**_.
  - Use _**`--remove-duplicates-assets`**_.
  - Select the file to retain with `more-people/tags-then-oldest`, `more-people/tags-then-newest`, `newest`, or `oldest`. The people/tags-first variants prefer the largest available distinct-person count, then distinct tag count, then use their named chronological tie breaker. The default is `newest`.
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials and a writable configured photos root.
  - The account must have WebDAV permission to list and delete files in that root.
- **Explanation:**
  - The Tool scans the configured NextCloud photos root through WebDAV. It uses each physical file's exact filename and WebDAV content length to form duplicate groups.
  - `newest` and `oldest` use the WebDAV last-modified timestamp. A missing or invalid timestamp is treated as older than a valid timestamp.
  - For each group, the Tool logs the proposed keeper and redundant file paths before requesting confirmation. Use _**`--request-user-confirmation=false`**_ only for unattended executions.
  - This module operates on physical files in the configured photos root. WebDAV does not provide a portable asset-metadata merge for albums, faces, tags, favorites, descriptions, or ratings, so none of those are merged before deletion.
- **Examples:**
  ```
  ./PhotoMigrator.bin --client=nextcloud --remove-duplicates-assets
  ./PhotoMigrator.bin --client=nextcloud --remove-duplicates-assets --dup-asset-keeper oldest
  ```

> [!CAUTION]
> This process permanently deletes redundant physical files from the configured NextCloud photos root after confirmation. Review the logged groups and proposed keeper before continuing.


## Merge Duplicates Albums from NextCloud Photos:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --merge-duplicates-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Current WebDAV integration keeps this operation as no-op.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --merge-duplicates-albums
  ```

> [!WARNING]
> This operation is currently a no-op in NextCloud integration.


## Consolidate Albums Names from NextCloud Photos:
- **From:** v4.5.0
- **Usage:**
  - `./PhotoMigrator.bin --client=nextcloud --consolidate-albums-names --preview-album-actions`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - The Tool connects to NextCloud Photos and scans the albums that already exist in the cloud looking for equivalent album-name families.
  - It uses the same family-detection logic as `--consolidate-similar-albums`, so names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` are treated as the same family.
  - Date-led families accept `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` prefixes, with dots, underscores, hyphens, long dashes, or spaces as separators. Different years or conflicting month/day values remain separate. The most precise compatible date is retained only when at least 95% of that album's assets fall inside its date range; otherwise the compatible broader date prefix is the keeper.
  - End-truncated names are considered only when their shared title prefix has at least two distinct words and every candidate has the same dominant asset year (more than half of its dated assets). A bare date is never treated as a truncated title. A plain name is never merged with a terminal `Shared`, `Share`, `Public`, `Público`, `X`, or truncated equivalent; two variants that both carry that suffix may be merged. When variants differ only by a terminal `Videos`, the non-`Videos` album is retained. A terminal date already covered by the leading date or leading year range is redundant, so the version without it is retained.
  - Albums with up to three assets can also be consolidated into a larger similarly named keeper when their complete capture-date range fits within the keeper range.
  - Equivalent-name, date-prefix, truncated-name, and small-album matching are independently enabled by default through `--try-equivalent-albums-grouping`, `--try-date-prefix-albums-grouping`, `--try-truncated-albums-grouping`, and `--try-small-albums-grouping`; use the corresponding `--no-...` option to skip one rule.
  - Assets from redundant variants are reassigned directly in NextCloud Photos to the preferred keeper album without uploading any new asset.
  - Once the reassignment is confirmed, the redundant album variants are removed.
  - `--preview-album-actions` (enabled by default) displays a table with the group, match rule, keeper, albums to merge, and comments explaining the applied keeper decision. With `--request-user-confirmation=true` (the default), the table is shown and the tool asks for confirmation before applying changes.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=nextcloud --consolidate-albums-names --preview-album-actions
  ```

---
## ⚙️ Config.ini
You can see how to configure the Config.ini file in this help section:
[Configuration File](00-configuration-file.md) 

---
## 🏠 [Back to Main Page](../README.md)
    
---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
