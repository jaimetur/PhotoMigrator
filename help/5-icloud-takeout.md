# 🍎 iCloud Takeout Management

From version 4.2.0 onwards, PhotoMigrator can process an Apple iCloud Photos export and recover asset dates from the CSV metadata that Apple includes in that export.

This feature is independent from the Google Takeout pipeline:
- it reads `Photo Details.csv` files from the iCloud export,
- it assigns those dates to the photo/video files,
- it builds a portable output library with `ALL_PHOTOS` and `Albums`.

> [!TIP]
> **How to request the export from Apple**
>
> Start from Apple's Data & Privacy portal:
> - `https://privacy.apple.com/`  
>
> Recommended workflow:
> 1. Sign in to `privacy.apple.com` with the Apple Account that owns the iCloud Photos library.
> 2. Request a copy of your data and include the Photos data export.
> 3. Use the largest export chunk size Apple offers. In the related user report, `25 GB` chunks were preferred because they reduce the number of ZIP parts you need to manage.
> 4. Download all delivered ZIP parts into a single local folder.
> 5. Run PhotoMigrator against that folder.

## What this feature reads from the iCloud export

PhotoMigrator currently uses these files from the export:
- `Photo Details.csv`
  Contains the key metadata used to recover dates. The relevant columns are:
  - `imgName`
  - `fileChecksum`
  - `originalCreationDate`
  - `importDate`
- `Albums/*.csv`
  Used to reconstruct album membership.
- `Memories/*.csv`
  Optional. Disabled by default because some exports contain a very large number of memory CSV files.

Typical headers seen in real exports:
- `Photo Details.csv`: `imgName,fileChecksum,favorite,hidden,deleted,originalCreationDate,viewCount,importDate`
- `Albums/*.csv`: `imgName`, `imageName`, or `Images`
- `Memories/*.csv`: usually `imageName`

## What PhotoMigrator does

1. Unzips the iCloud export if ZIP files are found in the input folder.
2. Scans all `Photo Details.csv` files found inside the export and keeps each one scoped to its own export folder instead of merging them into a single global index.
3. Matches CSV rows against media files using:
   - the same `Photos` folder first,
   - the same export block as fallback,
   - checksum when the filename is not unique.
4. Writes recovered dates into the output files.
   - Photos: EXIF dates are written with ExifTool when available.
   - Videos: QuickTime date tags are written with ExifTool when available; filesystem timestamps are also updated.
5. Builds a clean output structure:
   - `ALL_PHOTOS`
   - `Albums`
   - optional `Memories`
6. Organizes `ALL_PHOTOS` by date according to the selected folder structure.

## CLI usage

Basic usage:

```bash
./PhotoMigrator.run --icloud-takeout /path/to/iCloudExport
```

Choose a custom output folder:

```bash
./PhotoMigrator.run --icloud-takeout /path/to/iCloudExport --output-folder /path/to/output
```

Duplicate album assets instead of symlinks:

```bash
./PhotoMigrator.run --icloud-takeout /path/to/iCloudExport --icloud-no-symbolic-albums
```

Include `Memories/*.csv` collections too:

```bash
./PhotoMigrator.run --icloud-takeout /path/to/iCloudExport --icloud-include-memories
```

Customize output structures:

```bash
./PhotoMigrator.run \
  --icloud-takeout /path/to/iCloudExport \
  --icloud-albums-folders-structure flatten \
  --icloud-no-albums-folders-structure year/month
```

## Web Interface

In the Web Interface, use the new `iCloud Takeout` tab.
It is placed after `GOOGLE TAKEOUT` and before `GOOGLE PHOTOS`.

Tip:
- In Docker/Compose deployments, you can pre-fill the input path field with `PHOTOMIGRATOR_DEFAULT_ICLOUD_TAKEOUT_PATH`.

Main fields:
- `--icloud-takeout`: input export folder
- `--output-folder`: optional explicit output folder
- `--icloud-output-folder-suffix`: suffix used when `--output-folder` is not provided
- `--icloud-albums-folders-structure`: structure for album folders
- `--icloud-no-albums-folders-structure`: structure for `ALL_PHOTOS`
- `--icloud-no-symbolic-albums`: copy files instead of creating symlinks in albums
- `--icloud-include-memories`: also build folders from `Memories/*.csv`

## Expected output

By default the processed output is created as:

```text
<ICLOUD_EXPORT_FOLDER>_processed_<TIMESTAMP>
```

Inside it, PhotoMigrator creates:
- `ALL_PHOTOS`
- `Albums`
- optional `Memories`

## Notes and limitations

- This feature does not require Google Takeout or GPTH.
- `Memories` is optional because exports can contain thousands of memory CSV files.
- `Photo Details.csv` files are interpreted per export folder, which avoids mixing assets that share the same basename across different iCloud export blocks.
- If the export contains the same basename multiple times inside the same export block, PhotoMigrator tries to disambiguate using `fileChecksum`.
- If Apple exports multiple files with the same basename and there is not enough metadata to disambiguate album membership, some album reconstruction cases can still be ambiguous.

## Related sources

- Apple Data & Privacy portal: `https://privacy.apple.com/`
- Apple Support: `https://support.apple.com/en-us/118257`
- PhotoMigrator discussion with sample CSV/ZIP structure: `https://github.com/jaimetur/PhotoMigrator/discussions/1118`

---
## Back to Main Page

- [README](/README.md)
- [Help Index](/docs/view/help/help.md)
