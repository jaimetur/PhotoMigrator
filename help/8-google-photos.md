# <span style="color:green">Google Photos Management</span>

From version 4.0.0 onwards, the Tool can connect to Google Photos using the official Library API (OAuth).

### Features included:
1. Upload Album(s) (from folder)
2. Download Album(s) (into folder)
3. Upload ALL (from folder)
4. Download ALL (into folder)
5. Automatic Migration source/target endpoint integration

### Limited / Not supported by current API:
1. Remove ALL Assets
2. Remove ALL Albums
3. Remove Albums by Name Pattern
4. Rename Albums by Name Pattern
5. Remove Empty Albums
6. Remove Duplicates Albums
7. Merge Duplicates Albums
8. Remove Orphan Assets

You can apply filters in Google Photos modules.

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
  - currently not available in Google Photos integration (ignored with warning).

The credentials are loaded from `Config.ini`:

```ini
[Google Photos]
GOOGLE_PHOTOS_CLIENT_ID_1       = your_client_id_1
GOOGLE_PHOTOS_CLIENT_SECRET_1   = your_client_secret_1
GOOGLE_PHOTOS_REFRESH_TOKEN_1   = your_refresh_token_1
GOOGLE_PHOTOS_CLIENT_ID_2       = your_client_id_2
GOOGLE_PHOTOS_CLIENT_SECRET_2   = your_client_secret_2
GOOGLE_PHOTOS_REFRESH_TOKEN_2   = your_refresh_token_2
GOOGLE_PHOTOS_CLIENT_ID_3       = your_client_id_3
GOOGLE_PHOTOS_CLIENT_SECRET_3   = your_client_secret_3
GOOGLE_PHOTOS_REFRESH_TOKEN_3   = your_refresh_token_3
```

> [!NOTE]  
> To use all those features, it is mandatory to use the argument _**`--client=google-photos`**_ to specify Google Photos as the service that you want to connect.  
> 
> If you want to connect to an account ID different that 1 (suffixed with _2 or _3) you can use the argument _**`-id, -account-id`**_ to specify the account 2 or 3 as needed. 

> [!WARNING]
> Google Photos public API has functional limits.
> Unsupported management actions are exposed for CLI/UI compatibility but run as no-op with warning.


## <span style="color:blue">Upload Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --upload-albums <ALBUMS_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - The Tool creates one Google Photos album per subfolder in `<ALBUMS_FOLDER>`.
  - Supported assets in each subfolder are uploaded and associated to that album.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --upload-albums ./My_Albums_Folder
  ```


## <span style="color:blue">Download Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --download-albums <ALBUMS_NAME> --output-folder <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Downloads albums matching `<ALBUMS_NAME>` into `<OUTPUT_FOLDER>/Albums`.
  - You can use `ALL`, patterns, or multiple names.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --download-albums "Album 1, Album 2" --output-folder ./Downloads
  ```


## <span style="color:blue">Upload All:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --upload-all <INPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Uploads all supported assets from `<INPUT_FOLDER>`.
  - If `<INPUT_FOLDER>/Albums` exists, each subfolder is treated as an album.
  - Assets outside `Albums` are uploaded as no-album assets.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --upload-all ./MyLibrary
  ```


## <span style="color:blue">Download All:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --download-all <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Downloads all albums and non-album assets.
  - Albums are stored in `<OUTPUT_FOLDER>/Albums`.
  - Assets without albums are stored in `<OUTPUT_FOLDER>/ALL_PHOTOS`.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --download-all ./MyLibrary
  ```


## <span style="color:blue">Remove All Assets:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --remove-all-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --remove-all-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Remove All Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --remove-all-albums --remove-albums-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --remove-all-albums --remove-albums-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Remove Albums by Name Pattern:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --remove-albums <ALBUMS_NAME_PATTERN> --remove-albums-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --remove-albums "^Temp" --remove-albums-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Rename Albums by Name Pattern:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --rename-albums <ALBUMS_NAME_PATTERN> <ALBUMS_NAME_REPLACEMENT_PATTERN>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --rename-albums "\\d{4}-\\d{2}-\\d{2}" "DATE"
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Remove Empty Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --remove-empty-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --remove-empty-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Remove Duplicates Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --remove-duplicates-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --remove-duplicates-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## <span style="color:blue">Merge Duplicates Albums:</span>
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.run --client=google-photos --merge-duplicates-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.run --client=google-photos --merge-duplicates-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.

---

## Config.ini
Configuration details:
[Configuration File](/help/0-configuration-file.md)

---

## [Back to Main Page](/README.md)
