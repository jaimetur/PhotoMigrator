# Google Photos Management

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

> [!IMPORTANT]
> Google Photos public API has functional limits with scope and capability restrictions.
> Unsupported management actions are exposed for CLI/UI compatibility but run as no-op with warning.
> ⚠️ ** Some operations in PhotoMigrator are intentionally no-op for Google Photos because the public API does not support them.**

## How to get Google OAuth credentials
To use Google Photos modules you need:
- `GOOGLE_PHOTOS_CLIENT_ID_<N>`
- `GOOGLE_PHOTOS_CLIENT_SECRET_<N>`
- `GOOGLE_PHOTOS_REFRESH_TOKEN_<N>`

Follow these steps:
1. Create or select a project in Google Cloud Console.
2. Enable **Google Photos Library API** for that project.
3. Configure **OAuth consent screen** (External/Internal as needed).
4. Create an OAuth client in **Credentials**:
   - Recommended for local testing: **Desktop app**.
5. Copy generated values:
   - `Client ID` -> `GOOGLE_PHOTOS_CLIENT_ID_<N>`
   - `Client Secret` -> `GOOGLE_PHOTOS_CLIENT_SECRET_<N>`
6. Generate a refresh token with OAuth authorization flow:
   - Request OAuth with `access_type=offline` and `prompt=consent`.
   - Authorize with the Google account you want to use in PhotoMigrator.
   - Exchange authorization code for tokens and copy `refresh_token`.
7. Put all three values in `Config.ini` under `[Google Photos]`.

Example:
```ini
[Google Photos]
GOOGLE_PHOTOS_CLIENT_ID_1       = 1234567890-abcdefg.apps.googleusercontent.com
GOOGLE_PHOTOS_CLIENT_SECRET_1   = GOCSPX-xxxxxxxxxxxxxxxx
GOOGLE_PHOTOS_REFRESH_TOKEN_1   = 1//0gxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> [!NOTE]
> If the OAuth app is in **Testing** mode, only configured test users can authorize it.
> Refresh tokens may be invalidated if you revoke app access or rotate client secrets.


## Upload Albums:
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


## Download Albums:
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

> [!NOTE]
> Due current Google Photos API restrictions/scopes, download operations can be limited to media items accessible by the app context (commonly app-created data, depending on granted scopes).


## Upload All:
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


## Download All:
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

> [!NOTE]
> Due current Google Photos API restrictions/scopes, download operations can be limited to media items accessible by the app context (commonly app-created data, depending on granted scopes).


## Remove All Assets:
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


## Remove All Albums:
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


## Remove Albums by Name Pattern:
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


## Rename Albums by Name Pattern:
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


## Remove Empty Albums:
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


## Remove Duplicates Albums:
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


## Merge Duplicates Albums:
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
## ⚙️ Config.ini
You can see how to configure the Config.ini file in this help section:
[Configuration File](/help/0-configuration-file.md) 

---
## 🏠 [Back to Main Page](/README.md)
    
---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
