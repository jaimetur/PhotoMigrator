# Local Photos Folder Management

`Local Photos Folder` is a managed local-photo library exposed through the same modules used by the cloud-service tabs. Select it with `--client=local-photos-folder` and provide the required managed-library root with `-lPhotosFolder, --local-photos-folder <LOCAL_PHOTOS_FOLDER>`.

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
10. Remove Duplicates Albums
11. Remove Duplicates Assets
12. Merge Duplicates Albums
13. Consolidate Albums Names

Local Photos Folder does not require `Config.ini` credentials or `--account-id`. It supports the common type, date, country, city, person, folder, and file-exclusion filters where the selected workflow can use them. The source folder passed to upload commands can be a regular local folder or a managed Local Photos Folder library.

> [!NOTE]
> `--client=local-photos-folder` and `--local-photos-folder <LOCAL_PHOTOS_FOLDER>` are required for every Local Photos Folder module. `--account-id` and cloud credentials are not used.

> [!TIP]
> The common filters can limit media processed by upload/download workflows. `--created-from` and `--created-to` are specific to `Remove Albums` and filter the album-directory creation date, independently from media date filters.

> [!IMPORTANT]
> Local operations modify the filesystem directly. Keep `--request-user-confirmation=true` when reviewing destructive operations, and use `--preview-album-actions` for Rename Albums, Remove Albums, and Consolidate Albums Names. Preview is enabled by default.

> [!NOTE]
> For compiled binaries, macOS uses `PhotoMigrator.command`. Linux continues using `PhotoMigrator.bin`. Replace the executable name accordingly in the examples below.

## Local Photos Folder Layout

The managed root uses this layout:

```text
<LOCAL_PHOTOS_FOLDER>/
  Albums/<album name>/
  No_Albums/<year>/<month>/
```

Physical assets are retained in `No_Albums`. Album entries link to those physical files where the filesystem supports symbolic links, so a file can belong to several albums without duplicating its contents. Do not rename or move the managed `Albums` and `No_Albums` roots manually while a job is running.

> [!WARNING]
> Treat the managed layout as PhotoMigrator-owned while it is in use. Moving individual album entries or physical files outside PhotoMigrator can break membership links and make later cleanup or duplicate operations incomplete.

## Upload Albums (from Local Folder) into Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --upload-albums <ALBUMS_FOLDER>`
- **Pre-Requisites:** `<ALBUMS_FOLDER>` must contain one subfolder per album.
- **Explanation:** Imports supported media from each source album folder. The physical media is retained once in `No_Albums`, and the destination album records membership without an additional physical copy. Existing destination albums are reused by exact name by default.
  - `--prefer-canonical-album-names` creates new destination albums with the preferred clean name.
  - `--consolidate-similar-albums` detects equivalent destination album names, moves their memberships into the selected keeper, and removes the redundant album containers after confirmation.
- **Examples:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-albums ./AlbumsToImport
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-albums ./AlbumsToImport --prefer-canonical-album-names --consolidate-similar-albums
```

> [!NOTE]
> Reusing an album adds memberships to the existing album. It does not create a second physical copy of a matching managed asset.

## Download Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --download-albums <ALBUM_NAMES> --output-folder <OUTPUT_FOLDER>`
- **Pre-Requisites:** `--output-folder` is required.
- **Explanation:** Copies selected managed albums to `<OUTPUT_FOLDER>/Albums`. Use `ALL` for every album, a wildcard pattern such as `Trip*`, or several comma-separated album names. Downloading does not alter the managed library.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --download-albums "Holidays, Family" --output-folder ./ExportedAlbums
```

> [!WARNING]
> `<ALBUM_NAMES>` must match existing managed albums. An unmatched literal name or pattern exports no album.

## Upload All (from Local Folder) into Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --upload-all <INPUT_FOLDER>`
- **Explanation:** Imports every supported physical asset below `<INPUT_FOLDER>`. When `<INPUT_FOLDER>/Albums` exists, each direct subfolder becomes an album. `--albums-folders <FOLDER>` can additionally designate source folders whose subfolders must become albums. Assets outside album folders remain in `No_Albums` under the managed year/month organization.
  - `--prefer-canonical-album-names` and `--consolidate-similar-albums` apply to albums created or reused by this workflow.
- **Examples:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-all ./SourceLibrary
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-all ./SourceLibrary --albums-folders ./ExtraAlbums
```

> [!TIP]
> Keep source folders outside the managed destination root. Using the destination itself as the source can make the intended import scope ambiguous.

## Download All from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --download-all <OUTPUT_FOLDER>`
- **Explanation:** Exports the complete managed library to `<OUTPUT_FOLDER>`, including `Albums` and `No_Albums`. Album membership is preserved in the exported layout; the source managed library is not changed.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --download-all ./ExportedLibrary
```

> [!NOTE]
> Download All copies the library. It does not remove files or album memberships from the managed source.

## Remove All Assets from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-all-assets`
- **Explanation:** Permanently removes every physical managed asset and clears album references that point to them.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-all-assets
```

> [!CAUTION]
> This operation is irreversible for the managed library.

## Remove All Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-all-albums [--remove-albums-assets]`
- **Explanation:** Removes all managed album containers. By default, physical files in `No_Albums` are retained. With the managed layout, `--remove-albums-assets` removes the album entries before their containers are removed; the linked physical files in `No_Albums` remain intact.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-all-albums
```

> [!CAUTION]
> This removes every managed album container. Review the preview and confirmation request before continuing; the original album hierarchy cannot be reconstructed automatically.

## Remove Albums by Name Pattern from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-albums <PATTERN>`
- **Explanation:** Removes albums whose names match literal text, a wildcard such as `*Temp*`, or a regular expression. In the managed layout, `--remove-albums-assets` removes the album entries while the linked physical files in `No_Albums` remain intact. `--created-from` and `--created-to` restrict the selection to album directories created in an inclusive date range; either date can be omitted and `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` are accepted.
- **Examples:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-albums "*Temp*"
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-albums "^2019" --created-from 2019-01-01 --created-to 2019-12-31
```

> [!CAUTION]
> In a managed Local Photos Folder library, removing an album never deletes the linked `No_Albums` physical file. Use `--remove-all-assets` when the physical library itself must be deleted.

## Rename Albums by Name Pattern from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --rename-albums <PATTERN> <REPLACEMENT>`
- **Explanation:** Renames managed album directories that match literal text, wildcard, or regular-expression patterns. The action is previewed by default and a conflicting destination directory is skipped rather than overwritten.
- **Examples:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --rename-albums "--" "-"
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --rename-albums "\\b(\\d{4})\\.(\\d{2})\\.(\\d{2})\\b" "\\1-\\2-\\3"
```

> [!WARNING]
> A rename whose destination directory already exists is skipped. The tool does not overwrite or merge that destination implicitly.

## Remove Empty Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-empty-albums`
- **Explanation:** Removes album directories without effective media entries. Empty auxiliary directories are cleaned after the album removal.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-empty-albums
```

> [!NOTE]
> Only effectively empty album directories are removed. The operation does not delete physical media from `No_Albums`.

## Remove Duplicates Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-duplicates-albums`
- **Explanation:** Detects redundant album containers using the local album representation and removes redundant copies without deleting the retained physical media.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-duplicates-albums
```

> [!WARNING]
> Review the detected duplicate-album groups before confirmation. Album containers are removed, even though retained physical media is not.

## Remove Duplicates Assets from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-duplicates-assets --dup-asset-keeper <STRATEGY>`
- **Explanation:** Detects duplicate physical files and removes redundant copies according to `--dup-asset-keeper`. Supported strategies are `more-people/tags-then-oldest`, `more-people/tags-then-newest`, `oldest`, and `newest`. The people/tags-first strategies prefer the largest available distinct-people count, then distinct tag count, before their chronological tie breaker.
- **Examples:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-duplicates-assets
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --remove-duplicates-assets --dup-asset-keeper oldest
```

> [!CAUTION]
> This operation permanently deletes redundant physical files after confirmation.

## Merge Duplicates Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --merge-duplicates-albums`
- **Explanation:** Chooses a duplicate album keeper, associates the redundant memberships with it, and removes the redundant album containers. Physical media remains in the managed library.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --merge-duplicates-albums
```

> [!CAUTION]
> The redundant album containers are removed once their memberships have been merged into the selected keeper.

## Consolidate Albums Names from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --consolidate-albums-names`
- **Explanation:** Consolidates equivalent local album families without uploading media. The same four detectors used by cloud services are enabled by default:
  - `--try-equivalent-albums-grouping` handles canonical-equivalent names such as `Album`, `Album_1`, and `Album (2)`.
  - `--try-date-prefix-albums-grouping` handles compatible `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` name prefixes. The specific keeper date is retained only when at least 95% of its assets are inside that date range.
  - `--try-truncated-albums-grouping` handles guarded title truncation, including video-grouping and redundant-date cases, while preserving protected terminal suffix categories.
  - `--try-small-albums-grouping` merges small albums into a larger similarly named keeper when their capture-date range fits. `--small-album-max-assets` defaults to `3` and applies only to this detector.
  - `--preview-album-actions` displays the keeper, candidates, rules, and comments before confirmation. It is enabled by default.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --consolidate-albums-names --preview-album-actions
```

> [!IMPORTANT]
> The preview table lists the selected keeper, merge candidates, matching rule, and comments before any operation. With normal confirmation enabled, no consolidation proceeds until the displayed plan is accepted.

---
## 🏠 [Back to Main Page](../README.md)

---
## 🎖️ Credits

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>
