# ☁️ Google Photos Management

From version 4.0.0 onwards, the Tool can connect to Google Photos using the official Library API (OAuth).

### Features currently supported in practice:
1. Upload Album(s) (from folder)
2. Upload ALL (from folder)
3. Automatic Migration target endpoint integration

### Features affected by Google's Library API changes (April 1, 2025):
1. Download Album(s) (into folder) for a user's full library
2. Download ALL (into folder) for a user's full library
3. Automatic Migration with Google Photos as source endpoint for a user's full library

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

> [!TIP]
> In Docker/Compose/Kubernetes, you can override these settings without editing `Config.ini` by using environment variables with the same key names, for example `GOOGLE_PHOTOS_CLIENT_ID_1`, `GOOGLE_PHOTOS_CLIENT_SECRET_1`, `GOOGLE_PHOTOS_REFRESH_TOKEN_1`.
> Docker-secret style variables such as `GOOGLE_PHOTOS_CLIENT_SECRET_1_FILE=/run/secrets/google_photos_client_secret_1` are also supported.
> Runtime precedence is: environment variable > `Config.ini` > template default.

> [!IMPORTANT]
> Google Photos public API has functional limits with scope and capability restrictions.
> Unsupported management actions are exposed for CLI/UI compatibility but run as no-op with warning.
> ⚠️ ** Some operations in PhotoMigrator are intentionally no-op for Google Photos because the public API does not support them.**

> [!NOTE]
> For compiled binaries, macOS now uses `PhotoMigrator.command`. Linux and Synology SSH continue using `PhotoMigrator.bin`. Replace the binary name accordingly when following the CLI examples below.
>
> Effective **2025-04-01**, Google removed the legacy Library API scopes `photoslibrary`, `photoslibrary.readonly`, and `photoslibrary.sharing` for full-library access. As a result, PhotoMigrator cannot read a user's full Google Photos library through the official API anymore. For full-library export/migration, use **Google Takeout** as source.

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
  - `./PhotoMigrator.bin --client=google-photos --upload-albums <ALBUMS_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - The Tool creates one Google Photos album per subfolder in `<ALBUMS_FOLDER>`.
  - Supported assets in each subfolder are uploaded and associated to that album.
  - By default only exact existing album names are reused.
  - Add `--reuse-similar-existing-albums` to also treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - With this flag enabled, PhotoMigrator prefers the clean keeper name, merges the assets from numbered/underscored variants into that keeper, and reuses it for the incoming upload.
  - Google Photos redundant variants are not deleted afterwards because the public Library API does not support album deletion.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --upload-albums ./My_Albums_Folder
  ./PhotoMigrator.bin --client=google-photos --upload-albums ./My_Albums_Folder --reuse-similar-existing-albums
  ```
  Example: if `New_Album`, `New Album`, and `New_Album 1` exist, PhotoMigrator prefers `New Album` as the keeper, merges the assets it can into that keeper, and uploads the incoming album there. The redundant variants remain because Google Photos does not allow album deletion via the public API.


## Download Albums:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --download-albums <ALBUMS_NAME> --output-folder <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Downloads albums matching `<ALBUMS_NAME>` into `<OUTPUT_FOLDER>/Albums`.
  - You can use `ALL`, patterns, or multiple names.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --download-albums "Album 1, Album 2" --output-folder ./Downloads
  ```

> [!WARNING]
> Since **2025-04-01**, full-library download from Google Photos is no longer supported by the official Library API for third-party apps. In practice, this operation is only useful for app-created content still accessible with the remaining scopes. For normal user-library export, use Google Takeout.


## Upload All:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --upload-all <INPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Uploads all supported assets from `<INPUT_FOLDER>`.
  - If `<INPUT_FOLDER>/Albums` exists, each subfolder is treated as an album.
  - Assets outside `Albums` are uploaded as no-album assets.
  - Add `--reuse-similar-existing-albums` if you want album uploads inside this flow to treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - With this flag enabled, PhotoMigrator prefers the clean keeper name and merges the assets from redundant variants into that keeper before continuing with the incoming upload.
  - Redundant Google Photos albums are not deleted afterwards because the public Library API does not support album deletion.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --upload-all ./MyLibrary
  ./PhotoMigrator.bin --client=google-photos --upload-all ./MyLibrary --reuse-similar-existing-albums
  ```


## Download All:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --download-all <OUTPUT_FOLDER>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Downloads all albums and non-album assets.
  - Albums are stored in `<OUTPUT_FOLDER>/Albums`.
  - Assets without albums are stored in `<OUTPUT_FOLDER>/ALL_PHOTOS`.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --download-all ./MyLibrary
  ```

> [!WARNING]
> Since **2025-04-01**, full-library download from Google Photos is no longer supported by the official Library API for third-party apps. In practice, this operation is only useful for app-created content still accessible with the remaining scopes. For normal user-library export, use Google Takeout.


## Remove All Assets:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --remove-all-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
  - For supported cloud clients, the rename pattern can now be plain text, a wildcard expression, or a regular expression, and `--preview-album-actions` can be used to preview and confirm the affected albums before renaming.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --remove-all-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Remove All Albums:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --remove-all-albums --remove-albums-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --remove-all-albums --remove-albums-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Remove Albums by Name Pattern:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --remove-albums <ALBUMS_NAME_PATTERN> --remove-albums-assets`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
  - For supported cloud clients, the remove pattern can now be plain text, a wildcard expression, or a regular expression, and `--preview-album-actions` can be used to preview and confirm the affected albums before deletion.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --remove-albums "^Temp" --remove-albums-assets
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Rename Albums by Name Pattern:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --rename-albums <ALBUMS_NAME_PATTERN> <ALBUMS_NAME_REPLACEMENT_PATTERN>`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --rename-albums "\\d{4}-\\d{2}-\\d{2}" "DATE"
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Remove Empty Albums:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --remove-empty-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --remove-empty-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Remove Duplicates Albums:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --remove-duplicates-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --remove-duplicates-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.


## Merge Duplicates Albums:
- **From:** v4.0.0
- **Usage:**
  - `./PhotoMigrator.bin --client=google-photos --merge-duplicates-albums`
- **Pre-Requisites:**
  - Configure OAuth credentials in `Config.ini`.
- **Explanation:**
  - Not supported by current Google Photos public API.
- **Example of use:**
  ```bash
  ./PhotoMigrator.bin --client=google-photos --merge-duplicates-albums
  ```

> [!WARNING]
> Currently a no-op for Google Photos integration.

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
