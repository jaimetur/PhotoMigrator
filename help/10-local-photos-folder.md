# Local Photos Folder Management

The **Local Photos Folder** service provides the same library-management workflow as the cloud-service tabs, while storing the library in a managed local folder. Select it with `--client=local-photos-folder` and provide its required root with `-lPhotosFolder, --local-photos-folder <LOCAL_PHOTOS_FOLDER>`.

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

The common type, date, country, city, person, folder, and file-exclusion filters are available where the selected module supports them. Local Photos Folder does not use `--account-id` or `Config.ini` credentials.

## Local Photos Folder Layout

The managed root uses this layout:

```text
<LOCAL_PHOTOS_FOLDER>/
  Albums/<album name>/
  No_Albums/<year>/<month>/
```

Physical assets are retained in `No_Albums`. Album entries link to those physical files where the filesystem supports symbolic links, allowing one file to belong to multiple albums without duplicating its contents.

## Upload Albums (from Local Folder) into Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --upload-albums <ALBUMS_FOLDER>`
- **Explanation:** Creates or reuses an album for every supported-media subfolder in `<ALBUMS_FOLDER>`. Physical media is stored once in `No_Albums`; each album records its membership without a second physical copy.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-albums ./AlbumsToImport
```

`--prefer-canonical-album-names` and `--consolidate-similar-albums` have the same behavior as on the cloud upload modules.

## Download Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --download-albums <ALBUM_NAMES> --output-folder <OUTPUT_FOLDER>`
- **Explanation:** Copies the selected managed albums into `<OUTPUT_FOLDER>`. Use `ALL` to download every album, or comma-separated names and supported patterns to select individual albums.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --download-albums "Holidays, Family" --output-folder ./ExportedAlbums
```

## Upload All (from Local Folder) into Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --upload-all <INPUT_FOLDER>`
- **Explanation:** Imports every supported physical asset below `<INPUT_FOLDER>`. `--albums-folders` can designate source subfolders that must also become albums.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --upload-all ./SourceLibrary
```

## Download All from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --download-all <OUTPUT_FOLDER>`
- **Explanation:** Exports the managed `Albums` and `No_Albums` content into `<OUTPUT_FOLDER>`, preserving the local-library organization.
- **Example:**

```bash
PhotoMigrator --client=local-photos-folder --local-photos-folder ./ManagedLibrary --download-all ./ExportedLibrary
```

## Remove All Assets from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-all-assets`
- **Explanation:** Permanently removes every physical asset in the managed library. Album references to removed assets are also cleared.

## Remove All Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-all-albums`
- **Explanation:** Removes all managed album containers. With `--remove-albums-assets`, also removes their referenced assets.

## Remove Albums by Name Pattern from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-albums <PATTERN>`
- **Explanation:** Removes albums matching the supplied name or pattern. `--remove-albums-assets` also removes associated physical assets; `--preview-album-actions` shows the selected albums first. `--created-from` and `--created-to` optionally restrict the selection to album directories created within an inclusive date range; either date may be omitted and `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` are accepted.

## Rename Albums by Name Pattern from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --rename-albums <PATTERN> --replacement-pattern <REPLACEMENT>`
- **Explanation:** Renames managed albums matching the pattern. `--preview-album-actions` previews the proposed names before changes are applied.

## Remove Empty Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-empty-albums`
- **Explanation:** Removes album directories that contain no effective media entries.

## Remove Duplicates Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-duplicates-albums`
- **Explanation:** Detects duplicate album containers and removes redundant copies without deleting the retained physical media.

## Remove Duplicates Assets from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --remove-duplicates-assets --dup-asset-keeper <STRATEGY>`
- **Explanation:** Detects duplicate physical files and removes redundant copies according to `--dup-asset-keeper`. This operation changes the managed library and should be reviewed carefully.

## Merge Duplicates Albums from Local Photos Folder

- **Usage:** `--client=local-photos-folder --local-photos-folder <LOCAL_PHOTOS_FOLDER> --merge-duplicates-albums <STRATEGY>`
- **Explanation:** Merges duplicate album memberships using the selected strategy while retaining the chosen album container.

## Consolidate Albums Names from Local Photos Folder

`--consolidate-albums-names` applies the same album-family rules used by cloud services without uploading media: canonical equivalent names, compatible `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` prefixes, guarded end-truncated names, and small albums whose complete capture-date range fits in a larger similarly named keeper.

All four detectors are independently enabled by default: `--try-equivalent-albums-grouping`, `--try-date-prefix-albums-grouping`, `--try-truncated-albums-grouping`, and `--try-small-albums-grouping`. `--small-album-max-assets` defaults to `3`; it applies only when small-album grouping is enabled. `--preview-album-actions` shows the keeper and candidates, and confirmation is requested by default before consolidation.

## 🏠 [Back to Main Page](../README.md)
