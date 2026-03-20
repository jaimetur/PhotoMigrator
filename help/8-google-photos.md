# <span style="color:green">🖼️ Google Photos Management</span>

From version 4.0.0 onwards, the Tool can connect to Google Photos using the official Library API (OAuth).

## API Scope and Current Limits
Google Photos Library API supports upload, album creation, album listing, and media download.  
It does **not** provide full management capabilities for destructive operations in the same way as Synology/Immich.

### Supported in PhotoMigrator
1. Upload Album(s) (from folder)
2. Download Album(s) (into folder)
3. Upload ALL (from folder)
4. Download ALL (into folder)
5. Automatic Migration source/target endpoint integration

### Limited / Not supported by current API
1. Remove ALL Assets
2. Remove ALL Albums
3. Remove Albums by Name Pattern
4. Rename Albums by Name Pattern
5. Remove Empty Albums
6. Remove Duplicates Albums
7. Merge Duplicates Albums
8. Remove Orphan Assets

These modules are exposed for UI/CLI compatibility but currently execute as no-op with an explicit warning.

## Configuration
`Config.ini` must include credentials for the selected account:

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

## Usage Examples

### Upload albums
```bash
./PhotoMigrator.run --client=google-photos --upload-albums ./My_Albums_Folder
```

### Download albums
```bash
./PhotoMigrator.run --client=google-photos --download-albums "Album 1, Album 2" --output-folder ./Downloads
```

### Upload all
```bash
./PhotoMigrator.run --client=google-photos --upload-all ./MyLibrary
```

### Download all
```bash
./PhotoMigrator.run --client=google-photos --download-all ./MyLibrary
```

---

## ⚙️ Config.ini
Configuration details:
[Configuration File](/help/0-configuration-file.md)

---

## 🏠 [Back to Main Page](/README.md)

