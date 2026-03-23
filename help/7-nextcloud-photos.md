# <span style="color:green">NextCloud Photos Management</span>

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
11. Merge Duplicates Albums (currently no-op)

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
> `NEXTCLOUD_MAX_PARALLEL_UPLOADS` controls parallel uploads.
> Recommended values in LAN are usually between `8` and `16`.
>
> `NEXTCLOUD_MAX_PARALLEL_DOWNLOADS` controls parallel downloads.
> Recommended values in LAN are usually between `12` and `24`.
>
> `NEXTCLOUD_USE_SYSTEM_PROXY=false` means PhotoMigrator connects directly and ignores `HTTP_PROXY` / `HTTPS_PROXY`.

> [!WARNING]
> Use `NEXTCLOUD_USE_SYSTEM_PROXY=true` only if your environment explicitly requires outbound proxy.
> In LAN setups, enabling proxy by mistake can cause large per-request latency.


## <span style="color:blue">Upload Albums (from Local Folder) into NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --upload-albums <ALBUMS_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud URL and account credentials (App Password recommended).
- **Explanation:**
  - The Tool creates one album per subfolder inside `<ALBUMS_FOLDER>` and uploads supported assets.
  - In NextCloud implementation, files are uploaded under `NEXTCLOUD_ALBUMS_FOLDER_<id>/<AlbumName>`, and native Photos album association is handled automatically when supported.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --upload-albums ./My_Albums_Folder
  ```


## <span style="color:blue">Download Albums from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --download-albums <ALBUMS_NAME> --output-folder <OUTPUT_FOLDER>`
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
  ./PhotoMigrator.run --client=nextcloud --download-albums "Album 1, Album 2" --output-folder ./Downloads
  ```

> [!WARNING]
> `<ALBUMS_NAME>` must exist in your NextCloud library, otherwise nothing is downloaded.


## <span style="color:blue">Upload All (from Local Folder) into NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --upload-all <INPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials and `NEXTCLOUD_PHOTOS_FOLDER_<id>` / `NEXTCLOUD_ALBUMS_FOLDER_<id>`.
- **Explanation:**
  - Uploads all supported assets from `<INPUT_FOLDER>`.
  - If `<INPUT_FOLDER>/Albums` exists, each subfolder is treated as an album.
  - Assets outside `Albums` are uploaded into `NEXTCLOUD_PHOTOS_FOLDER_<id>`.
  - Album subfolders are uploaded into `NEXTCLOUD_ALBUMS_FOLDER_<id>`.
  - You can also provide extra albums folders via `-AlbFolder, --albums-folders`.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --upload-all ./MyLibrary
  ```


## <span style="color:blue">Download All from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --download-all <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Downloads all albums and assets from `NEXTCLOUD_PHOTOS_FOLDER_<id>`.
  - Albums are downloaded under `<OUTPUT_FOLDER>/Albums`.
  - Assets are downloaded under `<OUTPUT_FOLDER>/ALL_PHOTOS`.
  - If `NEXTCLOUD_ALBUMS_FOLDER_<id>` is inside `NEXTCLOUD_PHOTOS_FOLDER_<id>`, the albums subtree is excluded from the assets scan to avoid duplicate downloads.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --download-all ./MyLibrary
  ```


## <span style="color:blue">Remove All Assets from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-all-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes all assets from albums and non-album areas.
  - After removing assets, empty album folders are also removed.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --remove-all-assets
  ```

> [!CAUTION]
> This process is irreversible.


## <span style="color:blue">Remove All Albums from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-all-albums --remove-albums-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes all albums.
  - If `--remove-albums-assets` is set, it also removes assets associated to those albums.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --remove-all-albums --remove-albums-assets
  ```

> [!CAUTION]
> This process is irreversible.


## <span style="color:blue">Remove Albums by Name Pattern from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-albums <ALBUMS_NAME_PATTERN> --remove-albums-assets`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes albums whose name matches `<ALBUMS_NAME_PATTERN>`.
  - If `--remove-albums-assets` is set, assets inside removed albums are also removed.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --remove-albums "^Temp" --remove-albums-assets
  ```

> [!CAUTION]
> This process is irreversible.


## <span style="color:blue">Rename Albums by Name Pattern from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --rename-albums <ALBUMS_NAME_PATTERN> <ALBUMS_NAME_REPLACEMENT_PATTERN>`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Renames albums whose names match the provided pattern.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --rename-albums "\\d{4}-\\d{2}-\\d{2}" "DATE"
  ```


## <span style="color:blue">Remove Empty Albums from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-empty-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Removes albums that contain zero assets.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --remove-empty-albums
  ```


## <span style="color:blue">Remove Duplicates Albums from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-duplicates-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Current WebDAV integration keeps this operation as no-op.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --remove-duplicates-albums
  ```

> [!WARNING]
> This operation is currently a no-op in NextCloud integration.


## <span style="color:blue">Merge Duplicates Albums from NextCloud Photos:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --merge-duplicates-albums`
- **Pre-Requisites:**
  - Configure `Config.ini` with valid NextCloud credentials.
- **Explanation:**
  - Current WebDAV integration keeps this operation as no-op.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=nextcloud --merge-duplicates-albums
  ```

> [!WARNING]
> This operation is currently a no-op in NextCloud integration.

---

## Config.ini
You can see how to configure `Config.ini` here:
[Configuration File](/help/0-configuration-file.md)

---

## [Back to Main Page](/README.md)
