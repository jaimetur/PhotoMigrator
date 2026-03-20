# <span style="color:green">🖼️ NextCloud Photos Management</span>

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

> [!NOTE]
> To use these features, set _**`--client=nextcloud`**_.
>
> To select account 2 or 3, use _**`-id, --account-id [1-3]`**_.

The credentials are loaded from the `Config.ini` section below:

```ini
# Configuration for NextCloud Photos
[NextCloud Photos]
NEXTCLOUD_URL               = http://192.168.1.11:8080
NEXTCLOUD_USERNAME_1        = username_1
NEXTCLOUD_PASSWORD_1        = password_1
NEXTCLOUD_WEBDAV_ROOT_1     = /Photos
NEXTCLOUD_USERNAME_2        = username_2
NEXTCLOUD_PASSWORD_2        = password_2
NEXTCLOUD_WEBDAV_ROOT_2     = /Photos
NEXTCLOUD_USERNAME_3        = username_3
NEXTCLOUD_PASSWORD_3        = password_3
NEXTCLOUD_WEBDAV_ROOT_3     = /Photos
```

## <span style="color:blue">Upload Album(s) from local folder into NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --upload-albums ./My_Albums_Folder`
- The tool creates one remote album per subfolder and uploads supported media files.

## <span style="color:blue">Download Album(s) from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --download-albums "Album 1, Album 2" --output-folder ./Downloads`
- Use `ALL` to download all albums.

## <span style="color:blue">Upload ALL from local folder into NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --upload-all ./MyLibrary`
- Files in `Albums` are uploaded as albums; remaining files are uploaded as no-album assets.

## <span style="color:blue">Download ALL from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --download-all ./MyLibrary`

## <span style="color:blue">Remove ALL Assets from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-all-assets`

## <span style="color:blue">Remove ALL Albums from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-all-albums --remove-albums-assets`

## <span style="color:blue">Remove Albums by Name Pattern from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-albums "^Temp" --remove-albums-assets`

## <span style="color:blue">Rename Albums by Name Pattern from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --rename-albums "\\d{4}-\\d{2}-\\d{2}" "DATE"`

## <span style="color:blue">Remove Empty Albums from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-empty-albums`

## <span style="color:blue">Remove Duplicates Albums from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --remove-duplicates-albums`
- This operation is currently a no-op in the WebDAV-based implementation.

## <span style="color:blue">Merge Duplicates Albums from NextCloud Photos</span>
- **Usage:**
  - `./PhotoMigrator.run --client=nextcloud --merge-duplicates-albums`
- This operation is currently a no-op in the WebDAV-based implementation.

---

## ⚙️ Config.ini
You can see how to configure `Config.ini` here:
[Configuration File](/help/0-configuration-file.md)

---

## 🏠 [Back to Main Page](/README.md)
