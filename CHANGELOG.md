# 🗓️ CHANGELOG
[Planned Roadmap](/ROADMAP.md) for the following releases
[Changelog](/CHANGELOG.md) for the past releases

---

## Release: v4.0.0
### Release Date: 2026-03-20
  
#### 🚨 Breaking Changes:
  
#### 🌟 New Features:
  - Added full NextCloud Photos integration (WebDAV-based) across CLI, execution modes, automatic migration, and web interface (Issue: #567).
  - Added a dedicated `NextCloud Photos` tab in the web interface, placed between `Immich Photos` and `Other Features` (Issue: #567).
  - Added `ClassNextCloudPhotos` backend service with album/assets upload, download, cleanup, and rename/remove workflows.
  - Added Google Photos integration (official Library API based) across CLI, execution modes, automatic migration, and web interface.
  - Added a dedicated `Google Photos` tab in the web interface (next to `Google Takeout`).
  - Added Administration Panel for admin users to create/edit/delete users and configure per-user subpaths for `/app/data` and `/app/volumes`.
  - Added per-user `Config.ini` persistence in SQLite database, encrypting sensitive values at rest.
  - Added structured Configuration File tab editor based on sections/fields (Google Takeout, Google Photos, Synology Photos, Immich Photos, NextCloud Photos, TimeZone) with per-field help extracted from config comments.
  - Added a new `Upload to Server` tab in the web interface with destination-folder picker, separate `Upload Local Folder` and `Upload Local Zip` actions, and optional ZIP extraction mode (`Extract ZIPs on upload`: Yes/No).
  - Added `ClassGooglePhotos` backend service with OAuth refresh-token auth and supported upload/download modules.
  - Added secure multi-user mode in Docker Web Interface with login/session authentication and bootstrap admin credentials (`admin` / `admin123` by default).
  - Added a dedicated `Background Progress` panel in Automatic Migration Live Dashboard to render Local Folder analysis progress (folder scan + files scan in current folder) without polluting the logs panel. (Issue #1037)

#### 🚀 Enhancements:
  - Extended automatic migration endpoint parsing in web UI to support `nextcloud[-photos][-1..3]` for both source and target.
  - Added Google Photos OAuth credentials support in `Config.ini` and config loader (`[Google Photos]` section with account 1/2/3).
  - Extended automatic migration endpoint parsing in web UI to support `google[-photos][-1..3]` for both source and target.
  - Updated CLI/source-target validation and help text to include `nextcloud` and `google-photos` as cloud clients.
  - Improved name-pattern handling across cloud modules: wildcard-only patterns like `*` are now accepted for album selection, and literal patterns with special regex characters (for example album names containing parentheses) now work for matching/replacing without requiring manual escaping.
  - Improved album rename matching for literal album names containing regex metacharacters (such as parentheses), so rename workflows work without manual escaping.
  - Improved markdown render to detect italic font and bold+italic.
  - Improved album download progress visualization for cloud clients (NextCloud, Synology, Immich, Google Photos) by showing a nested per-album assets progress bar labeled as `Downloading '<AlbumName>' Assets`.
  - Improved album upload progress visualization for cloud clients (NextCloud, Synology, Immich, Google Photos) by showing a nested per-album assets progress bar labeled as `Uploading '<AlbumName>' Assets`.
  - Restricted folder/file browser API access to each user's assigned subfolders only, and enforced the same path restrictions at command execution time.
  - Enhancements in Web UI.
  - Forbidden Import/Export/Save configuration file in demo roles.
  - Added NextCloud dual-folder configuration in `Config.ini` and config loader with per-account `NEXTCLOUD_PHOTOS_FOLDER_<id>` (assets/no-albums) and `NEXTCLOUD_ALBUMS_FOLDER_<id>` (folder-based albums).
  - Separated markdown render in a new static file
  - Smoothed Automatic Migration Live Dashboard rendering by switching to manual refresh-on-change updates (dirty panels only), stabilizing Background Progress row order, and reducing completion-row churn to minimize panel flicker/tremor in CLI.
  - Added vertical scroll to the `Access Logs` table in the Administration Panel, limiting visible height (about 20 recent entries) while keeping older entries accessible by scrolling.
  - Improved `Background Progress` label normalization to keep only text after `:`, trim trailing `:` variants (`:`, ` :`, ` : `), and remove trailing path clauses such as `in ...` / `in folder ...` (Linux/Windows paths, quoted or unquoted).
  - Improved `Background Progress` title normalization to keep only the text after `:` (when present) and then trim surrounding whitespace.
  - Improved CLI Live Dashboard Background Progress routing for Takeout post-processing `tqdm` lines by accepting additional prefixes (including `TQDM ...`) and indeterminate progress frames (for example `81 files [00:00, ...]`) so those updates are rendered in the `Background Progress` panel instead of the logs panel.
  - Improved CLI Live Dashboard responsiveness on terminal resize by syncing layout dimensions on each refresh cycle and recalculating visible `Logs Panel` rows from the current panel height.
  - Refined CLI Live Dashboard log coloring rules to style only explicit Automatic Migration events (`Asset Pulled`, `Asset Pushed`, `Asset Duplicated`, `Album Created`, `Album Pulled`, `Album Pushed`, `Asset Fail/Failed`) instead of broad keyword matches.
  - Updated GPTH to version 6.1.0 which includes several enhancements and bug fixing.

#### 🚀 GPTH Enhancements:
  - Added `--all-photos-dir` CLI option to customize the non-album output directory name (default remains `ALL_PHOTOS`). Set it to an empty string (`--all-photos-dir ""`) to remove that extra directory level entirely. This makes album links more portable when migrating into existing folder structures.
  - `--transform-pixel-mp` now accepts an explicit output format: `mp4`, `jpg`, or `still`.
  - Step 6 Pixel motion-photo transformation now supports two modes:
    - `mp4`: rename `.MP` / `.MV` primary files to `.mp4`.
    - `jpg`: create motion `.jpg` files from Pixel motion photos.
    - `still`: keep only a still image (prefers sidecar `*.MP.jpg`, otherwise extracts embedded JPEG) and remove related `.MP` / `.MV` source files.
    - `--transform-pixel-mp jpg` is currently **preview/experimental** and may be unstable depending on source file structure.
  - **Step 1: Pixel Motion Photo files (.MP, .MV) no longer unconditionally converted to .mp4** — Pixel Motion Photo files have `video/mp4` MIME type but `.MP`/`.MV` extensions. Previously, Step 1 unconditionally renamed them to `.mp4` due to the MIME/extension mismatch, making the `--transform-pixel-mp` flag ineffective. Step 1 now preserves `.MP`/`.MV` files, deferring to Step 6 which respects the flag: with `--transform-pixel-mp`, they are converted to `.mp4`; without the flag, they are left as-is.
  - Added progress bar to Step 5 (Find Albums) to show album association processing progress
  - **Step 1: Extension fixing now replaces the incorrect extension instead of appending** — Previously, a file like `vacation_sunset.heic` (actually JPEG) would be renamed to `vacation_sunset.heic.jpg`. Now it becomes `vacation_sunset.jpg`. The associated JSON sidecar and any supplemental-metadata JSON files are atomically renamed to match. This produces cleaner output filenames with no change in metadata accuracy, since all downstream steps already used only the final extension. The double-extension handling in the truncated filename fixer (Step 4) has been kept for natural Pixel-style suffixes (`.PANO.jpg`, `.MP.mp4`, etc.) which are not affected by this change.
  - **Step 3 progress bar now fills in real time** — Previously the hashing phase (`groupIdenticalFast2`) only printed a text message every 50 size groups (and only in verbose mode), so the progress bar appeared to jump to 100% instantly at the end. A `FillingBar` is now created before the bucket-processing loop and updated after each slice of size groups finishes, giving continuous visual feedback during the (potentially long) deduplication hashing phase.
  - **Step 7 progress bar unified** — The two separate bars ("Writing EXIF data" and "Flushing pending EXIF writes") are now a single bar that tracks all output files from start to finish. The total is pre-counted before processing begins, so the bar fills steadily across the whole step without a surprise second bar appearing at the end.
  - **Overall pipeline performance is approximately 3× faster** on a modern PC with an SSD compared to the previous version, based on real-world tests (400GB takeout now 38m instead of 1h 20m) due to the following changes:
    - **Step 1 (Fix Extensions): single-pass collection + parallel processing** — Previously the directory was traversed twice: once to count files (for the progress bar) and once to process them. A single `toList()` now serves both purposes, and `_processFile` (128-byte header read + MIME check + optional rename) runs in parallel `Future.wait` batches at `diskOptimized` concurrency.
    - **Step 2 (Discover Media): parallel JSON partner-sharing checks** — `jsonPartnerSharingExtractor` was called sequentially per file inside the stream loop. Files are now collected first, then processed with `Future.wait` in batches of `diskOptimized` concurrency, reducing total I/O wait from a sum of latencies to roughly one batch-time per `N/batchSize` iterations.
    - **Step 6 (Move Files): parallel file operations** — `moveAll` now calls the parallel variant of the move engine (`moveMediaEntitiesParallel`) with `diskOptimized` concurrency (`cores × 8`, max 32) instead of the sequential one-entity-at-a-time loop. The parallel implementation already existed but was dead code. For cross-drive copy operations this is the single largest win.
    - **Step 7 EXIF batch write throughput dramatically improved** — `stableTagsetKey` previously grouped files by tag names *and* values, so every file landed in its own 1-entry bucket (unique date string = unique key). The threshold check never fired, and the final flush called one ExifTool process per file. The batch queue now groups by tag *names only*; all files needing the same tag set (e.g. `DateTimeOriginal + DateTimeDigitized + DateTime`) land in a single bucket. ExifTool's batch mode already supports different values per file by interleaving per-file args before each filename, so correctness is unchanged. This results in a large reduction in ExifTool process spawns for typical collections.
    - **7-Zip extraction speed improved** — The 7-Zip extractor now uses `-mmt=N` (explicit thread count equal to `Platform.numberOfProcessors`) instead of `-mmt=on`, and suppresses stdout/stderr/progress pipe output (`-bso0 -bse0 -bsp0`) to reduce I/O overhead. For large archives with many files this avoids unnecessary process pipe traffic and lets 7-Zip use all available CPU cores.
    - **Step 7: ExifTool stay-open IPC — zero Perl startup overhead** — All ExifTool write operations (single-file and batch) are now routed through a single long-running `exiftool -stay_open True` process started once at launch. On Linux / WSL, Perl startup costs ~1-2 s per invocation; every write now takes only the actual I/O time. The argfile batch path also no longer needs a temp file when stay-open is active, as stdin has no command-line length limit. Falls back transparently to one-shot invocations if the persistent process fails to start.
    - **Parallel ZIP extraction** — When 7-Zip is available and multiple ZIPs are present, archives are now extracted concurrently. Concurrency scales with core count (`max(2, N÷4)`, capped at 4) so 4-core machines run 2 in parallel, 8-core run 3, 16-core run 4, etc. Since extraction is I/O-bound (JPEGs are already compressed, so Deflate adds negligible CPU work), each process receives the full processor count (`-mmt=N`) rather than a split share — threads mostly block on I/O and don't compete for CPU. Native Dart extraction remains sequential to avoid simultaneous heap pressure from two large ZIPs.
    - **Step 7: Large MOV/MP4 files with oversized QuickTime atoms are no longer retried** — ExifTool emits `atom is too large for rewriting` when a video file's data block exceeds its internal rewrite limit (e.g. a 676 MB MOV file). Previously this produced 4–6 noisy log lines and a pointless single-file retry. The error is now recognised as unrecoverable: the batch-level "retrying" message is suppressed, no per-file retry is attempted, and a single clear `[WARNING]` is emitted per affected file stating that the file was still sorted correctly.
    - **JSON sidecar read consolidated (Steps 4 + 7)** — Each media file's `.json` sidecar was previously parsed up to three times: once for the date, once for GPS coordinates, and again in Step 7 to retrieve coordinates for EXIF writing. GPS is now extracted alongside the date in a single read during Step 4 and cached on the entity, so Step 7 requires no additional file I/O for GPS data.
    - **GPS data from `geoDataExif` now correctly used** — The coordinate extractor previously only read from the `geoData` field of the JSON sidecar. Google Photos also stores the original camera-recorded GPS in `geoDataExif`, which is often the only source of valid coordinates (e.g. for videos, photos edited by third-party apps that strip EXIF, or photos tagged after upload). The extractor now prefers `geoDataExif` and falls back to `geoData`, significantly increasing the number of files that receive GPS in their output EXIF..
    - **Step 3: XXH3 replaces hand-rolled FNV-1a for quick-signature and fingerprint hashing** — The 32-bit FNV-1a closure used in `_quickSignature` and the 64-bit FNV-1a method used in `_triSampleFingerprint` are replaced by XXH3 (via `package:xxh3`). XXH3 is approximately 10× faster than SHA-256 and significantly faster than FNV-1a on the 4 KiB slices read per bucket candidate, while providing 64-bit hash quality.
    - **Full-file content hashing uses XXH3 instead of SHA-256** — `MediaHashService.calculateFileHash` (the definitive byte-for-byte equality check used before any file is discarded) now uses `xxh3String` for small files and the `xxh3Stream` chunked API for large files. This replaces the previous `package:crypto` SHA-256 implementation. The `package:crypto` dependency has been removed.
  - **Step 1: Extension collision resolved with unique filename instead of skip** — When fixing a file's extension would produce a name that already exists (e.g. `teams_jens.png` → `teams_jens.jpg` but `teams_jens.jpg` already exists due to storage-saver mode), the file is now renamed to the next available unique name (`teams_jens(1).jpg`) using the same `(N)` counter logic as the move step. Files with an existing counter suffix are handled correctly: `teams_jens(1).png` → `teams_jens(1)(1).jpg`. Previously such files were silently left with the wrong extension, which later caused ExifTool batch failures ("Not a valid PNG — looks more like a JPEG") with a noisy multi-round binary-split cascade in Step 7.
  - **Windows: emoji album folders no longer cause pipeline failures** — On Windows, `Directory.list()` throws when a path contains certain emoji characters. Album directories with emoji names (e.g. `Holiday Memories 🎄`) are now temporarily renamed to a hex-encoded form at the start of the pipeline and restored immediately after all steps complete. Output album folders always use the original emoji name. If the process crashes mid-run, the hex-encoded names are detected and restored automatically on the next run via `progress.json`.
  - **Step 1: Extension fixing no longer skips edited files by default** — Files with language-specific "edited" suffixes (e.g.`-edited`) were unconditionally skipped during extension fixing, regardless of the `--skip-extras` flag. This meant a file like `IMG_3376-bearbeitet.HEIC` that was actually a JPEG would keep its wrong extension and fail later with `Not a valid HEIC (looks more like a JPEG)`. The guard is now conditional: edited files are only skipped during extension fixing when `--skip-extras` is explicitly set.
  - Added `archiveren` as a recognised Dutch and `archivieren` as a German special folder name (Google Photos exports this as a mistranslation of "Archive" for NL/GER users).
  - **Windows: trailing backslash in quoted paths** — `--input "path\"` and `--output "path\"` now work correctly. The trailing path separator is stripped before processing; previously the C-runtime interpreted `\"` as an escaped quote, causing subsequent flags to be swallowed into the path value. If the resulting path value still appears to contain embedded flags (e.g. `--input "path\" --output ...`), GPTH now exits with a clear diagnostic message instead of silently failing.
  - Suppressed a misleading batch-level ExifTool warning for InteropIFD errors. Those files are already retried individually (introduced in v5.1.1), so logging the whole batch as failed gave the false impression that every file in the batch was broken.
  - **Step 7: UTC offset tags now written natively for JPEGs, fixing InteropIFD corruption warnings** — `OffsetTime`, `OffsetTimeOriginal`, and `OffsetTimeDigitized` are now written inside the native JPEG write methods (`writeDateTimeNativeJpeg` / `writeCombinedNativeJpeg`) together with the date tags, eliminating the second ExifTool invocation that previously followed every successful native write. This is also more resilient for files with a corrupt InteropIFD: the `image` library's sub-IFD reader wraps each sub-IFD in a `try/catch` and silently drops any that fail to parse, then the writer removes the dangling `0xA005` pointer — so the output JPEG has a clean EXIF block with no corrupt InteropIFD, rather than triggering ExifTool's `Truncated InteropIFD directory` error. The ExifTool fallback path (used when the native write itself fails) is untouched and still includes the strip-and-retry logic from v5.1.1. This addresses an issue introduced in version 5.0.9, during the fix of the UTC bug.
  - **Step 7: Large MOV/MP4 files with oversized QuickTime atoms are no longer retried** — ExifTool emits `atom is too large for rewriting` when a video file's data block exceeds its internal rewrite limit (e.g. a 676 MB MOV file). Previously this produced 4–6 noisy log lines and a pointless single-file retry. The error is now recognised as unrecoverable: the batch-level "retrying" message is suppressed, no per-file retry is attempted, and a single clear `[WARNING]` is emitted per affected file stating that the file was still sorted correctly.
  - **Step 4: Truncated filename fixer no longer duplicates Pixel suffixes** — Files with double extensions containing Pixel-specific suffixes (`.PANO.jpg`, `.MP.mp4`, `.NIGHT.jpg`, `.vr.jpg`) had the suffix doubled when the truncated filename fixer restored the full name from JSON metadata (e.g. `PXL_20230518_095458599.PANO.PANO.jpg`). The title's extension is now stripped symmetrically with the filename's, preventing the duplication.
  - **7-Zip detection logged once** — The 7-Zip executable path is now resolved once per extraction session (cached in the service instance) and reported via a single `[ INFO ]` message. Previously the path was re-detected for every ZIP file, producing no visible confirmation at all in CLI mode.
  - Removed noise in verbose logs and ensured more accurate representation of errors/warnings
  - **Step 7: MTS, M2TS, WMV, AVI, MPEG, and BMP files are now skipped before ExifTool is called** — ExifTool does not support writing metadata to these formats. Previously they were passed to ExifTool individually, producing `[WARNING] ExifTool command failed` noise for every such file. They are now detected upfront by extension and MIME type and silently skipped (a single warning is still logged per file unless warnings are silenced).
  - Refactoring, offloading complex logic in separate files for maintainability and removed legacy code.
  - Replaced custom `_Mutex` class with `Pool(1)` from `package:pool` in `MediaHashService` — same single-access semantics with less custom code.
  - Replaced hand-rolled `LinkedHashMap` LRU cache (~60 lines) with `LruCache` from `package:lru` in `MediaHashService`.
  - Added type-safe `toJson()` / `fromJson()` serialization to `MediaEntity`, `FileEntity`, and `AlbumEntity`, replacing ~260 lines of duck-typed `dynamic` casting in `ProgressSaverService`.
  - Fixed a bug where non-english year folder names could cause them to be classified as albums
  - Fixed ExifTool failing with `Bad format (282) for InteropIFD entry` or `Truncated InteropIFD directory` errors on certain images (Google Photos edited files with `-edited` suffix, WhatsApp images). Root cause: the UTC timezone offset tags (`OffsetTime*`) introduced in v5.0.9 trigger ExifTool's IFD traversal, which aborts on files with a corrupted InteropIFD structure. Fix: when either error is detected, the offset tags are stripped and the write is retried — date and GPS data are still written successfully, matching v5.0.8 behaviour for these files. (#108)
  - Improved error messaging for InteropIFD failures: the per-file warning now correctly distinguishes between a UTC timezone offset tag failure (date was already written natively — no data loss) and an actual date metadata write failure. A step-level summary is printed when one or more files are affected, with a description and the total count of affected files.
  - Upgraded mime package to 2.0.0 (contains bugfix)
  - Added german and spanish "Photos from" localization.
  - Fixed an issue with MacOS unicode normalisation (#99)
  - Fixed a possible endless loop (#102)
  - Made Exiftool discovery on Windows more robust when installed via chocolatey and not added to PATH.
  - Added -editada suffix for spanish
  - bumped some dependencies
  - Will not allow any mode which requires symlink on a filesystem which does not support symlinks (#105)
  - Fixed a UTC conversion bug
  - Fixed that geodata was removed from exif
  - fixed a bug where a path join used a unix path seperator instead of being platform agnostic.
  - Updated upstream library to image 4.7.2 which contains fixes to the native writeExif() method.
  - ZIP extraction no longer deletes an existing extraction directory. GPTH Neo now refuses to extract into a non-empty folder to prevent accidental deletion of unrelated files.
  - Interactive mode: Added an explicit **DANGER** warning before confirming output directory cleanup (deletes recursively inside the chosen output folder).
  - Restore truncated media filenames from JSON sidecars (uses the JSON `title` field) after date extraction, renaming both the media file and its JSON metadata so later steps use the original name.
  - Fixed german unknown folder name from "unbekannt" to "Unbenannt" to correctly identify unknown folders (please create a bug report if those folders are exported in your language and provide us with the correct translation)
  - fixed unit tests
  - fixed partner sharing logic
  - Added Auto-Resume support to avoid repeat successful steps when tool is interrupted and executed again on the same output folder. (#87).
  - Untitled Albums now are detected and moved to `Untitled Albums` forder. (only if albums strategy is `shortcut`, `reversed-shortcut` or `duplicate-copy`, the rest of albums strategies don't creates albums folders). (#86).
  - Upgraded exif_reader package to the newest version.
  - Fixed #90 (duplicated output in interactive mode)
  - Fixed major error which led to native exif write methods not being used when exiftool was not installed.
  - Fixed issue with App1 marker in image library when jpg has no exif block. Using own fork of image library until pull request to the source repo is accepted. Fixes issue #95
  - Minor Bug Fixing.



#### 🐛 Bug fixes:
  - Fixed web command/help text normalization so `--client=nextcloud` examples are parsed consistently in UI descriptions.
  - Fixed `Automatic Migration` cloud-session initialization for NextCloud and Google Photos clients by enabling lazy thread-safe auto-login on first API call, preventing `session is not initialized. Call login() first` errors in source/target worker flows.
  - Fixed `Automatic Migration` dashboard crash in frozen binaries when Rich unicode tables are missing (`ModuleNotFoundError: rich._unicode_data.unicode17-0-0`) by adding packaging includes for `rich._unicode_data` and graceful dashboard fallback.
  - Fixed NextCloud `Download All`/`Download Assets` path behavior to scan `NEXTCLOUD_PHOTOS_FOLDER_<id>` recursively while excluding `NEXTCLOUD_ALBUMS_FOLDER_<id>` when nested, preventing duplicate album downloads and supporting direct `/Photos` layouts.
  - Fixed `--no-log-file` behavior so Google Takeout runs no longer create the logs folder or log file when that flag is enabled.
  - Other bug fixing.

#### 📚 Documentation: 
  - Added NextCloud Photos help page and linked it from README/help index.
  - Added Google Photos help page and linked it from README/help index.
  - Updated CLI/configuration/automatic-migration docs to include NextCloud and Google Photos support.
  - Changed header styles in help documents.
  - Updated documentation with all changes.

---

## Release: v3.8.0
### Release Date: 2026-03-17
  
#### 🚨 Breaking Changes:
  
#### 🌟 New Features:
  - New Web Interface to configure and execute the different features & modules directly.
  - Added themes support to Web Interface.
  - Docker support to deploy the tool in docker and expose the new Web Interface (default port: 6078).
  - New docker-compose.yml and .env file to easily configure and deploy the tool with docker compose.
  - Added deterministic Live Photo upload support for Immich by pairing photo+video companions (same basename) and linking them through Immich API (`livePhotoVideoId`) across Immich upload features and Automatic Migration.
  - Added automatic burst stacking for Immich uploads (including Automatic Migration) using conservative heuristics (same folder, normalized basename, short time window, and size-ratio guard), creating Immich stacks with preferred primary asset ordering.
    
#### 🚀 Enhancements:
  - Web Live Dashboard on Automatic Migration feature.
  - Adjusted Goggle Photos Panel layout.
  - Enhancements in Execution Log windows to parse progress bar properly.
  - Allow page reload while task is running.
  - Enhancements in Web interface layout and feature descriptions.
  - Added confirmation dialog on those modules that remove/rename/merge assets/albums on Synology/Immich Photos features.
  - Added confirmation dialog on Auto Rename Folders Content Based feature.
  - Improved Immich `Remove Orphan Assets` module to detect unsupported newer Immich API versions and abort gracefully with a clear message instead of failing with a raw 404 error.
  - Added a safeguard in `organize_files_by_date` to skip files already organized in the expected date folder structure (`year`, `year/month`, `year-month`) and avoid redundant re-nesting.
  - Improved Web Interface execution log buffering for long-running jobs with progress bars: progress refresh updates no longer flood line history, the in-memory log is compacted by progress key, and default web log buffer size was increased and made configurable via `PHOTOMIGRATOR_WEB_MAX_JOB_OUTPUT_LINES`.
  - Simplified docker-compose.yml file.
  - Horizontal scroll on log panel when lines are too large.
  - Improved markdown render for code blocks.

#### 🐛 Bug fixes:
  - Added validation for `--google-takeout` path to block reserved special-folder names (`Archive`, `Trash`, `Locked folder`) and abort early with a clear message; same validation is enforced in Web UI folder selection (Issue #1008).
  - Fixed a queue accounting bug in `Automatic Migration` that could stall execution when processing album folders still marked as active (`.active`) in parallel workers (Issue #1009).
  - Fixed `Automatic Migration` startup with `--log-level=DEBUG` by passing profiling label arguments correctly to `profile_and_print` (Issue #1009).
  - Fixed Google Takeout GPTH input root normalization to handle direct `Google Photos` paths reliably (without copy fallback), preventing "Discover Media = 0" scenarios on NAS layouts (Issue #1013).
  - Fixed `LocalFolder.get_albums_owned_by_user()` raising `UnboundLocalError` (`albums_filtered`) when called with `filter_assets=False` during automatic migration album checks (Issue #1014).
  - Fixed Synology Live Photo downloads where ZIP payloads could be saved with `.HEIF` extension; ZIP payloads are now detected and extracted properly (Issue #1028).
  - Fixed download/migration EXIF date overwrite behavior: EXIF date tags are now only filled when missing, preserving existing shooting dates (Issue #1029).
  - Fixed Exiftool command line overflowing max length (#1052).
  - Fixed Exiftool not embebed on docker-dev version.
  - Fixed `Download All` (Immich/Synology) creating redundant `ALL_PHOTOS/YYYY/MM/YYYY/MM` folders by avoiding a duplicate date-organization pass after assets are already downloaded directly into `YYYY/MM`.
  - Fixed Immich album deletion status handling to treat HTTP `204 No Content` (and any `2xx`) as success, avoiding false warnings like `Failed to remove album ... Status: 204`.
  - Fixed Immich Live Photo linking reliability during uploads by retrying transient `404` responses when setting `livePhotoVideoId`, and skipping link attempts when either media component was uploaded as duplicate.
  - Fixed Web Interface log color classification to prioritize the explicit line log level prefix (e.g. `WARNING:`), preventing warning lines from being painted as errors when message text contains words like `Client Error`.
  - Fixed Web Interface active-job reconnect endpoint routing conflict by prioritizing `/api/jobs/_active` over dynamic `/api/jobs/{job_id}` matching, preventing false `{"detail":"Job not found"}` responses when querying active jobs.
  - Other bug fixing.

#### 📚 Documentation: 
  - Included Documentation links on Web interface.
  - Made link relatives to current release.
  - Updated documentation with all changes.

---

## Release: v3.7.1
### Release Date: 2026-03-16
  
#### 🚨 Breaking Changes:
  
#### 🌟 New Features:
    
#### 🚀 Enhancements:
  
#### 🐛 Bug fixes:
  - Fixed stream Immich multipart upload to avoid OOM.

#### 📚 Documentation: 

---

## Release: v3.7.0
### Release Date: 2026-01-09
  
#### 🚨 Breaking Changes:
  
#### 🌟 New Features:
    
#### 🚀 Enhancements:
  - Most of the Code Translated into English.
  
#### 🐛 Bug fixes:

#### 📚 Documentation: 
  - Most of the Comments Translated into English.
  - Updated documentation with all changes.
    
---

## Release: v3.6.2
### Release Date: 2025-09-11

#### 🚨 Breaking Changes:
  - Now your special folders (`Archive`, `Trash`, `Locked folder`) will be directly moved to `Special Folders` subfolder within the output directory in `Google Takeout Processing` feature.
  
#### 🌟 New Features:
  - Added support for Special Folders management such as `Archive`, `Trash`, `Locked folder` during `Google Takeout Processing` feature.
    
#### 🚀 Enhancements:
  - Added new function to Sanitize (fix folders/files ending with spaces or dosts to avoid SMB mingling names) your Takeout input folder during `Google Takeout Procesing Feature`. 
  - Improved `Folder Analyzer` to read date tags from groups EXIF/XMP/QuickTime/Track/Media/Matroska/RIFF only (other groups are not reliable).
  - Improved `Folder Analyzer` to choose the oldest date with time when two or more candidates has the same date but one has time o other not.
  - Improved `Auto Rename Albums` feature to read date tags from groups EXIF/XMP/QuickTime/Track/Media/Matroska/RIFF only (other groups are not reliable).
  - Improved `Auto Rename Albums` feature to choose the oldest date with time when two or more candidates has the same date but one has time o other not.
  - Updated **GPTH** to version `5.0.5` (by @Xentraxx & @jaimetur) which includes new features, performance improvements and bugs fixing extracting metadata info from Google Takeouts.

#### 🐛 Bug fixes:
  - Fixed bug in guess dates from filepath where it was looking into the grandparents folder even if the parent folder was not a month folder.
  - Fixed bug in guess dates from filename where it was detecting false positives in filenames as hashnames (i.e.: "5752a2c4-1908-4696-9117-fdfa750fbd88.jpg" --> incorrect 1908).
  - Fixed bug when extract zips that contains non-supporting folders for special system such as Synology NAS or SMB mounted devices such as folders ending with Whitespace that was renamed by the system as `*_ADMIN_Whitespace_conflict*`. Now native extractor makes an intelligent sanitization of folder names before to extract the archive.

#### 📚 Documentation: 
  - Updated documentation with all changes.

#### ✨ **GPTH New Features**
  - Added support for Special Folders management such as `Archive`, `Trash`, `Locked folder`. Now those folders are excluded from all album strategies and are moved directly to the output folder.

#### 🚀 **GPTH Improvements**
  - Moved logic of each Step to step's service module. Now each step has a service associated to it which includes all the logic and interation with other services used by this step.
  - Added percentages to all progress bars.
  - Added Total time to Telemetry Summary in Step 3.
  - Fixed _extractBadPathsFromExifError method to detect from exiftool output bad files with relative paths.
  - Performance Improvements in `step_03_merge_media_entities_service.dart`.
  - Now grouping method can be easily changed. Internal `_fullHashGroup` is now used instead of 'groupIdenticalFast' to avoid calculate buckets again.

#### 🐛 GPTH Bug fixes:
  - Fixed duplicated files/symlinks in Albums when a file belong to more than 1 album (affected strategies: shortcut, reverse-shortcut & duplicate-copy).
  - Fixed error decoding Exiftool output with UTF-8/latin chars.

---

## Release: v3.6.1
### Release Date: 2025-09-09

#### 🚨 Breaking Changes:
  
#### 🌟 New Features:
    
#### 🚀 Enhancements:
  - Now `Logs`, `Extracted_dates_metadata.json` and `Duplcicates.csv` files are saved at Output folder by default when `Google Takeout Processing` feature is detected.
  - Improved FixSymLinks to be case-insensitive when looking for real files of symlinks.
  - Improvements in Analysis Output Statistics to separate Physical and Symlinks files.
  - Show GPTH Tool and EXIF Tool version in Global Configuration settings at the beginning of the tool.
  - Updated **GPTH** to version `5.0.4` (by @Xentraxx & @jaimetur) which includes new features, performance improvements and bugs fixing extracting metadata info from Google Takeouts.

#### 🐛 **Bug Fixes**
  - Fixed albums_input_folder in Move Albums step within `Google Takeout Processing` feature.
  
#### 📚 Documentation: 
  - Updated documentation with all changes.
      
#### ✨ **GPTH New Features**
  - New album moving strategy `ignore` to completely ignore all Albums content. The difference with `nothing` strategy is that `nothing` don't create Albums folders but process and move all Albums content into `ALL_PHOTOS` folder.

#### 🚀 **GPTH Improvements**
  - Replace all `print()` functions by `logPrint()` method from LoggerMixin class. In this way all messages are registered both on screen and also on the logger (and saved to disk if flag `--save-log` is enabled).
  - All console messages have now a Step prefix to identify from which step or service they come from.
  - Moving Strategies re-defined
  - Included Timeouts on ExifTool operations.
  - Log saving enabled by default. Use flag `--no-save-log` to disable it.
  - Changed log name from `gpth-{version}_{timestamp}.log` to `gpth_{version}_{timestamp}.log`.
  - Added progress bar to Step 3 (Merge Media Entities).
  - Changed default value for flag `--update-creation-time. Now is enabled by default.
  - Smart split in writeBatchSafe: we parse stderr, separate only the conflicting files, retry the rest in a single batch, and write the conflicting ones per-file (without blocking progress). If paths can’t be extracted, we fall back to your original recursive split.
  - Added Progress bar on Step 1 & Step 2.

#### 🐛 **GPTH Bug Fixes**
  - Added `reverse-shortcut` strategy to interactive mode.
  - Fixed some moving strategies that was missing some files in the input folder
  - Fixed exiftool_service.dart to avoid IFD0 pointer references.
  - Fixed exiftool_service.dart to avoid use of -common_args when -@ ARGFILE is used.
  - Fixed PNG management writting XMP instead of EXIF for those files.  
  - (ExifToolService): I added -F to the common arguments (_commonWriteArgs). It’s an immediate patch that often turns “Truncated InteropIFD” into a success.
  - (Step 7): If we detect a “problematic” JPEG, we force XMP (CreateDate/DateTimeOriginal/ModifyDate + signed GPS), both when initially building the tags (via _forceJpegXmp) and again on retry when a batch fails and stderr contains Truncated InteropIFD (in-place conversion of those entries with _retagEntryToXmpIfJpeg).

---

## Release: v3.6.0
### Release Date: 2025-08-31

#### 🚨 Breaking Changes:
  - `Auto-Rename Albums content based` now uses as dates separator `-` instead of `.` and as group of dates separator `--` instead of `-`. Those separators can be customized using two new parameters (see below).

#### 🌟 New Features:
  - Added new parameter `-dateSep, --date-separator <DATE_SEPARATOR>` to specify the Dates Separator for the Feature `Auto-Rename Albums Content Based`.
  - Added new parameter `-rangeSep, --range-separator <RANGE_OF_DATES_SEPARATOR>` to specify the Range of Dates Separator for the Feature `Auto-Rename Albums Content Based`.
  - Added new parameter `-gpthNoLog, --gpth-no-log` to Skip Save GPTH log messages into output folder.
    
#### 🚀 Enhancements:
  - Improvements in `Auto Rename Albums Folders` feature to Compute the best 'oldest_date' per file using the following priority:
      1. date_dict
      2. EXIF native (piexif)
      3. EXIF exiftool
      4. Filesystem ctime
      5. Filesystem mtime 
  - Updated **GPTH** to version `5.0.2` (by @Xentraxx & @jaimetur) which includes new features, performance improvements and bugs fixing extracting metadata info from Google Takeouts.

#### 🐛 Bug fixes:
  - Fixed albums_input_folder in Move Albums step within `Google Takeout Processing` feature.

#### 📚 Documentation: 
  - Updated documentation with all changes.

#### ✨ **GPTH New Features**
  - Support for 7zip and unzip extractors (if found in your system). This is because the native extractor does not extract properly filenames or dirnames with UTF-8/latin1 chars.
  - Support new `Extra` files from Google Takeout with following suffixes: `-motion`, `-animation`, `-collage`.
  - New flag `--keep-input` to Work on a temporary sibling copy of --input (suffix _tmp), keeping the original untouched.
  - New flag `--keep-duplicates` to keep duplicates files in `_Duplicates` subfolder within output folder.
  - New flag `--save-log` to save log messages into disk file.
  - Created GitHub Action `build-and-create-release.yml` to Automatically build all binaries, create new release (stable or pre-release), update it wiht the release-notes and upload the binaries to the new release.
  - Step 8 (Update creation time) is now multi-platform. Also update creation date for physical files and symlinks on linux/macos.

#### 🚀 **GPTH Improvements**
  - Created a single package gpth-lib with all the exported modules for an easier way to manage imports and refactoring.
  - Added new flag `fallbackToExifToolOnNativeMiss`in `GlobalConfigService` Class to specify if we want to fallback to ExifTool on Native EXIF reader fail. (Normally if Native fails is because EXIF is corrupt, so fallback to ExifTool does not help).
  - Added new flag `enableExifToolBatch`in `GlobalConfigService` Class to specify if we want to enable/disable call ExifTool with batches of files instead of one call per file (this speed-up a lot the EXIF writting time with ExifTool).
  - Added new flag `maxExifImageBatchSize`in `GlobalConfigService` Class to specify the maximum number of Images for each batch passed in any call to ExifTool.
  - Added new flag `maxExifVideoBatchSize`in `GlobalConfigService` Class to specify the maximum number of Videos for each batch passed in any call to ExifTool.
  - Added new flag `forceProcessUnsupportedFormats`in `GlobalConfigService` Class to specify if we want to forze process unsupported format such as `.AVI`, `.MPG`or `.BMP` files with ExifTool.
  - Added new flag `silenceUnsupportedWarnings`in `GlobalConfigService` Class to specify if we want to recive or silence warnings due to unsupported format on ExifTool calls.
  - Added new flag `enableTelemetryInMergeMediaEntitiesStep`in `GlobalConfigService` Class to enable/disable Telemetry in Step 3: Merge Media Entities.
  - Code Structure refactored for a better understanding and easier way to find each module.
  - Code Refactored to isolate the execution logic of each step into the .execute() function of the step's class. In this way the media_entity_collection module is much clearer and easy to understand and maintain.
  - Adapted all methods to work with this new structure
  - Homogenized logs for all steps.
  - New code re-design to include a new `MediaEntity` model with the following attributes:
   - `albumsMap`: List of AlbumsInfo obects,  where each object represent the album where each file of the media entity have been found. This List which can contain many usefull info related to the Album.
   - `dateTaken`: a single dataTaken for all the files within the entity
   - `dateAccuracy`: a single dateAccuracy for all the files within the entity (based on which extraction method have been used to extract the date)
   - `dateTimeExtractionMethod`: a single dateTimeExtractionMethod for all the files within the entity (method used to extract the dataTaken assigned to the entity)
   - `partnerShared`: true if the entity is partnerShared
   - `primaryFile`: contains the best ranked file within all the entity files (canonical first, then secondaries ranked by lenght of basename, then lenght of pathname)
   - `secondaryFiles`: contains all the secondary files in the entity
   - `duplicatesFiles`: contains files which has at least one more file within the entity in the same folder (duplicates within folder)
  - Created internal/external methods for Class `MediaEntity` for an easy utilization.
  - All modules have been adapted to the new `MediaEntity` structure.
  - All Tests have been adapted to the new `MediaEntity` structure.
  - Removed `files` attribute from `MediaEntity` Class.
  - Merged `media_entity_moving_strategy.dart` module with `media_entity_moving_service.dart` module and now it is stored under `lib/steps/step_06_moving_files/services` folder.
  - New behaviour during `Find Duplicates` step:
   - Now, all identical content files are collected within the same MediaEntity.
     - In a typical Takeout, you might have the same file within `Photos from yyyy` folder and within one or more Album folder
     - So, both of them are collected within the same entity and will not be considered as duplicated because one of them could have associated json and the others not
     - So, we should extract dates for all the files within the same media entity.
   - If one media entity contains two or more files within the same folder, then this is a duplicated file (based on content), even if they have different names, and the tool will remove the worst ranked duplicated file.
  - Moved `Write EXIF` step to Step 7 (after Move Files step) in order to write EXIF data only to those physical files in output folder (skipping shortcuts). 
   - This changed was needed because until Step 6 (based on the selected album strategy), don't create the output physical files, we don't know which files need EXIF write. 
   - With this change we reduce a lot the number of EXIF files to write because we can skip writing EXIF for shortcut files created by shorcut or reverse-shortcut strategy, but also we can skip all secondaryFiles if selected strategy is None or Json. 
   - The only strategy that has no benefit from this change is duplicate-copy, because in this strategy all files in output folder are physical files and all of them need to have EXIF written.
  - Renamed `Step 3: Remove Duplicates` to `Step 3: Merge Media Entities` because this represents much better the main purpose of this step. 
  - **Performance Optimization in `Step 3: Merge Media Entities`.**
  - `Step 3: Merge Media Entities` now only consider within-folder duplicates. And take care of the primaryFile/secondaryFiles based on a ranking for the rest of the pipeline.
  - `Step 7: Write EXIF` now take into account all the files in the MediaEntity file except duplicatesFiles and files with `isShortcut=true` attribute. 
  - `Step 6: Move Files` now manage hardlinks/juntions as fallback of native shorcuts using API to `WindowsSymlinkService` when no admin rights are granted.
  - `Step 8: Update Creation Time`now take into account all the files in the MediaEntity file except duplicatesFiles.
  - `Step 8: Update Creation Time`now update creation time also for shortcuts.
  - Improvements on Statistics results.
   - Added more statistics to `Step 3: Remove Duplicate` 
   - Added more statistics to `Step 6: Move Files` 
   - Added more statistics to `Step 8: Update Creation Time`.
   - Total execution time is now shown as hh:mm:ss instead of only minutes.
 
#### 🐛 **GPTH Bug Fixes**
  - Fixed #65: Now all supported media files are moved from input folder to output folder. So after running GPTH input folder should only contain .json files and unsupported media types.
  - Fixed #76: Now interactive mode ask for album strategy.
  - Changed zip_extraction_service.dart to support extract UTF-8/latin1 chars on folder/files names.

---

## Release: v3.5.2
### Release Date: 2025-08-24

#### 🚀 Enhancements:
  - Separate Steps for Analyze Input Takeout files and Analyze Output files in feature `Google Takeout Fixing`. Now the Analyzer for the Input Takeout folder is executed after Pre-Processing steps, in this way the extracted dates JSON dictionary will match for all input files during GPTH processing phase even if any file was renamed during any pre-processing step.
  - Show dictMiss files in GPTH log to see those files that have not been found in dates dictionary when it was passed as argument using --fileDates

#### 🐛 Bug fixes:
  - Fixed a bug in GPTH in JSON Matcher service when the JSON filename lenght is longer than 51 chars. In those cases the tool was trying to find a truncated JSON variant and never try to match with the full filename, but PhotoMigrator fixes Truncations during Pre-process, so it was never found.
  - Fixed a bug in GPTH Step 7 (Move Files) that progress bar was not showing the correct number of operations.

#### 📚 Documentation: 
  - Updated documentation with all changes.

---

## Release: v3.5.1
### Release Date: 2025-08-20

#### 🚀 Enhancements:
  - Extracted Dates JSON now contains all Dates in Local UTC format.
  - Extracted Dates JSON now includes ExecutionTimestamp Tag for reference.
  - Extracted Dates JSON Tags renamed for a better understanding.
  - Enhancements in extract_dates() function to avoid guess date from file path when the file path cotains the execution timestamp.
  - Included support in GPTH to use the Extracted Dates JSON dictionary. This will speed-up GPTH Date extraction a lot.
  - Updated **GPTH** to version `4.3.0` (by @Xentraxx & @jaimetur) which includes new features, performance improvements and bugs fixing extracting metadata info from Google Takeouts.

#### 🐛 Bug fixes:
   - Fixed a bug when guessed date from filepath extract the same date than TIMESTAMP (if the path contains the current TIMESTAMP). 

#### 📚 Documentation: 
  - Updated documentation with all changes.

#### 🚀 **GPTH Improvements**
  - **Improved non-zero exit code quitting behaviour** - Now with nice descriptive error messages because I was tired of looking up what is responsible for a certain exit code. 

##### Step 4 (Extract Dates) & 5 (Write EXIF) Optimization
###### ⚡ Performance
  - Step 4 (READ-EXIF) now support --fileDates flag to provide a JSON dictionary with the Extracted dates per file (PhotoMigrator creates this file and can now be used by GPTH Tool).
  - Step 4 (READ-EXIF) now uses batch reads and a fast native mode, with ExifTool only as fallback → about 3x faster metadata extraction.  
  - Step 5 (WRITE-EXIF) supports batch writes and argfile mode, plus native JPEG writers → up to 5x faster on large collections.
###### 🔧 API
  - Added batch write methods in `ExifToolService`.  
  - Updated `MediaEntityCollection` to use new helpers for counting written tags.
###### 📊 Logging
  - Statistics are clearer: calls, hits, misses, fallback attempts, timings.  
  - Date, GPS, and combined writes are reported separately.  
  - Removed extra blank lines for cleaner output.
###### 🧪 Testing
  - Extended mocks with batch support and error simulation.  
  - Added tests for GPS writing, batch operations, and non-image handling.
###### ✅ Benefits
  - Much faster EXIF processing with less ExifTool overhead.  
  - More reliable and structured API.  
  - Logging is easier to read and interpret.  
  - Stronger test coverage across edge cases.  

##### Step 6 (Find Albums) Optimization
###### ⚡ Performance
  - Replaced `_groupIdenticalMedia` with `_groupIdenticalMediaOptimized`.  
   - Two-phase strategy:  
     - First group by file **size** (cheap).  
     - Only hash files that share the same size.  
   - Switched from `readAsBytes()` (full memory load) to **streaming hashing** with `md5.bind(file.openRead())`.  
   - Files are processed in **parallel batches** instead of sequentially.  
   - Concurrency defaults to number of CPU cores, configurable via `maxConcurrent`.
###### 🔧 Implementation
  - Added an in-memory **hash cache** keyed by `(path|size|mtime)` to avoid recalculating.  
   - Introduced a custom **semaphore** to limit concurrent hashing and prevent I/O overload.  
   - Errors are handled gracefully: unprocessable files go into dedicated groups without breaking the process.
###### ✅ Benefits
  - Processing time reduced from **1m20s → 4s** on large collections.  
   - Greatly reduced memory usage.  
   - Scales better on multi-core systems.  
   - More robust and fault-tolerant album detection.  

#### 🐛 **Bug Fixes in GPTH Tool:**
  - **Changed exif tags to be utilized** 
   - Before we used the following lists of tags in this exact order to find a date to set: 
  - Exiftool reading: 'DateTimeOriginal', 'MediaCreateDate', 'CreationDate', 'TrackCreateDate', 'CreateDate', 'DateTimeDigitized', 'GPSDateStamp' and 'DateTime'.
  - Native dart exif reading: 'Image DateTime', 'EXIF DateTimeOriginal', 'EXIF DateTimeDigitized'.  
   - Some of those values are prone to deliver wrong dates (e.g. DateTimeDigitized) and the order did not completely make sense. We therefore now read those tags and the oldest DateTime we can find:
  - Exiftool reading: 'DateTimeOriginal','DateTime','CreateDate','DateCreated','CreationDate','MediaCreateDate','TrackCreateDate','EncodedDate','MetadataDate','ModifyDate'.
  - Native dart exif reading: same as above.
  - **Fixed typo in partner sharing** - Functionality was fundamentally broken due to a typo.
  - **Fixed small bug in interactive mode in the options of the limit filezise dialogue**
  - **Fixed unzipping through command line by automatically detecting if input directory contains zip files**
    
---

## Release: v3.5.0
### Release Date: 2025-07-30

#### 🚀 Enhancements:
  - Updated **GPTH** to version `4.1.0` (by @Xentraxx) which includes several new features, improvements and bugs fixing extracting metadata info from Google Takeouts. 

#### ✨ **New Features in GPTH Tool:**
   - **Partner Sharing Support** - Added `--divide-partner-shared` flag to separate partner shared media from personal uploads into dedicated `PARTNER_SHARED` folder (Issue #56)
  - Automatically detects partner shared photos from JSON metadata (`googlePhotoOrigin.fromPartnerSharing`)
  - Creates separate folder structure while maintaining date division and album organization
  - Works with all album handling modes (shortcut, duplicate-copy, reverse-shortcut, json, nothing)
  - Preserves album relationships for partner shared media
   - **Added folder year date extraction strategy** - New fallback date extractor that extracts year from parent folder names like "Photos from 2005" when other extraction methods fail (Issue #28)
   - **Centralized concurrency management** - Introduced `ConcurrencyManager` for consistent concurrency calculations across all services, eliminating hardcoded multipliers scattered throughout the codebase
   - **Displaying version of Exiftool when found** - Instead of just displaying that Exif tool was found, we display the version now as well.
      
#### 🚀 **Performance Improvements in GPTH Tool:**
  - **EXIF processing optimization** - Native `exif_reader` library integration for 15-40% performance improvement in EXIF data extraction
   - Uses fast native library for supported formats (JPEG, TIFF, HEIC, PNG, WebP, AVIF, JXL, CR3, RAF, ARW, DNG, CRW, NEF, NRW)
   - Automatic fallback to ExifTool for unsupported formats or when native extraction fails
   - Centralized MIME type constants verified against actual library source code
   - Improved error logging with GitHub issue reporting guidance when native extraction fails
  - **GPS coordinate extraction optimization** - Dedicated coordinate extraction service with native library support
   - 15-40% performance improvement for GPS-heavy photo collections
   - Clean architectural separation between date and coordinate extraction
   - Centralized MIME type support across all EXIF processing operations
  - **Significantly increased parallelization** - Changed CPU concurrency multiplier from ×2 to ×8 for most operations, dramatically improving performance on multi-core systems
  - **Removed concurrency caps** - Eliminated `.clamp()` limits that were artificially restricting parallelization on high-core systems
  - **Platform-optimized concurrency**:
   - **Linux**: Improved from `CPU cores + 1` to `CPU cores × 8` (massive improvement for Linux users)
   - **macOS**: Improved from `CPU cores + 1` to `CPU cores × 6` 
   - **Windows**: Maintained at `CPU cores × 8` (already optimized)
  - **Operation-specific concurrency tuning**:
   - **Hash operations**: `CPU cores × 4` (balanced for CPU + I/O workload)
   - **EXIF/Metadata**: `CPU cores × 6` (I/O optimized for modern SSDs)
   - **Duplicate detection**: `CPU cores × 6` (memory intensive, conservative)
   - **Network operations**: `CPU cores × 16` (high for I/O waiting)
  - **Adaptive concurrency scaling** - Dynamic performance-based concurrency adjustment that scales up to ×24 for high-performance scenarios
    
#### 🐛 **Bug Fixes in GPTH Tool:**
  - **Fixed memory exhaustion during ZIP extraction** - Implemented streaming extraction to handle large ZIP files without running out of memory
  - **Fixed atomic file operations** - Changed to atomic file rename operations to resolve situations where only the json was renamed in file extension correction (Issue #60)
  - **Fixed album relationship processing** - Improved album relationship service to handle edge cases properly (Issue #61)
  - **Fixed interactive presenter display** - Corrected display issue in interactive mode (Issue #62)
  - **Fixed date division behavior for albums** - The `--divide-to-dates` flag now only applies to ALL_PHOTOS folder, leaving album folders flattened without date subfolders (Issue #55)
  - **Reaorganised ReadMe for a more intuitive structure** - First Installation, then prerequisites and then the quickstart.
  - **Step 8 now also uses a progress bar instead of simple print statements**
  - **Supressed some unnecessary ouput**

#### 📚 Documentation: 
  - Updated documentation with all changes.

---

## Release: v3.4.4  
### Release Date: 2025-07-25

#### 🌟 New Features:
  - Added new Feature to create a Graphical User Interface (if supported) or Interactive Prompts (if Graphical Interface is not supported) to configure `Google Takeout Fixing` feature if the tool is called without arguments.

#### 🚀 Enhancements:
  - Enhancement [#866](https://github.com/jaimetur/PhotoMigrator/issues/866) to Improve performance of Input Info Analysis in 'Automatic Migration Feature' using an object from class FolderAnalyzer instead of performing read/write disk operations on LocalFolder class methods.
  - Enhancement on 'Album Pulled' / 'Album Pushed' dashboard messages during `Automatic Migration Feature`. Now Album messages are displayed in bright color to highlight it vs normal asset pull/push operations. 
  - Enhancement on `ClassLocalFolder`. Now all methods of this class uses an object analyzer from FolderAnalyzer class to speed-up any file operations. 
  - Enhancement on `Automatic Migration Feature` when using Live Dashboard. Now it catch any exception during processing.
  - Enhancement on `Automatic Migration Feature` when using Live Dashboard. Now it restore the cursor back if the process is interrupted.
  - Enhancement on `FolderAnalyzer`. Now it can construct the object from 3 different ways (base_folder, extracted_dates dictionary or extracted_dates JSON file.
  - Enhancement on `FolderAnalyzer`. Now it handles date and type filters to only process those assets matching the filter criteria.
  - Enhancement on `FolderAnalyzer`. Now Exiftool command does not include `-fast2` argument to avoid skipp useful tags.
  - Enhancement on `FolderAnalyzer`. Now Exiftool block only process tag `FileModifyDate` as final fallback, in that way the logic is the following:
      1. Extract following tags `['DateTimeOriginal', 'DateTime', 'CreateDate', 'DateCreated', 'CreationDate', 'MediaCreateDate', 'TrackCreateDate', 'EncodedDate', 'MetadataDate', 'ModifyDate', 'FileModifyDate']` with EXIFTOOL (if detected) or tags `['DateTimeOriginal', 'DateTime']` with PIL if EXIFTOOL is not detected.
      2. Process all of them except `FileModifyDate` to get the oldest date found.
      3. Guess date from filename/pathname if none of above Tags contains a valid date.
      4. Calculate `ReferenceForModifyDate` in a smart way based on the date of Takeout Unzip and the date of execution.
      5. Get tag `FileModifyDate` if still there is not a valid date found even with guess date from file algorithm and check if it is valid (should not be older than `ReferenceForModifyDate` otherwise will not pass validation.
      6. Finally, if `FileModifyDate` still not contains a valid date,  get Filesystem `CreationTime` (ctime) and FileSystem `ModifyTime` (mtime) and if any of them pass the validation (older than `ReferenceForModifyDate`) it will be taken as valid_date.
      7. Of none of above methods detect a valid date, the file will be count as 'no valid date' file.

#### 🐛 Bug fixes:
  - Fixed bug [#865](https://github.com/jaimetur/PhotoMigrator/issues/865) to avoid Albums Duplication on 'Automatic Migration Feature' due to race conditions when more than 1 pusher_workers try to create the same Album in parallel. Now, to avoid this race conditions, only pusher_worker with id=1 is allowed to create new Albums. If the Album does not exists and the id>1 then the asset is returned back to pusher_queue.
  - Fixed bug [#879](https://github.com/jaimetur/PhotoMigrator/issues/879) in `guess_date_from_filename` function when the filename contains a number starting with 19 or 20 followed by 2 or more digits without checking if the following digits matches with a real month or month+day.
  - Fixed Bug [#884](https://github.com/jaimetur/PhotoMigrator/issues/884) in 'Google Takeout Processing' feature when flag `-gics, --google-ignore-check-structure` is detected causing that Output Folder is the same as Input Takeout Folder and deleting that at the end of the process.
  - Fixed Bug in `mode_folders_rename_content_based` function. It was not updated to the new output dictionary.    
  - Fixed Bug in `FolderAnalyzer` when create the extracted_dates dictionary on Windows system, and you have any path with unicode characters accents or special chars.    

#### 📚 Documentation: 
  - Updated documentation with all changes.

---

## Release: v3.4.3  
### Release Date: 2025-07-15

#### 🌟 New Features:
  - Added a new step `Show Files without dates` in 'Google Takeout Processing' to show a summary of files without associated date found.
  - Added heuristic function to try to guess file date from filename (and also filepath) when is not possible to extract any date from EXIF and before to fallback to extract system date.
  - Added Feature to Automatically Publish New Release Announcement on Discord Channels.
    
#### 🚀 Enhancements:
  - Enhancements in 'Google Takeout Processing' feature to improve the performance.
   - Created a new Class `FolderAnalyzer` to analyze any folder and:
  - Extract dates of all media files found using Exiftool if is found, or PIL library as fallback or guess from filename as second fallback or filesystem date as final fallback if any of previous method is able to find dates for each media file.
  - Get the oldest date between all date tags found in EXIF metadata of the media file.
  - Keep the analyzer object in memory for faster date extraction during the code.
  - Save extracted dates into a JSON file when finished the process.
  - Update the index of the extracted dates when any file is moved/renamed to other folder.
  - Update the index of the extracted dates when any folder is renamed.
  - Count the files per type (supported/non-supported/media/photos/videos, etc...) and also count which files has valid/invalid dates.
   - Enhancements in 'Analyze Folder' function. Execution time reduced more than **65%** using the new object of Class `FolderAnalyzer`.
   - Enhancements in 'Create year/month folder structure' function. Execution time reduced more than **95%** using the new object of Class `FolderAnalyzer`.
   - Enhancements in 'Album renaming' function. Execution time reduced more than **85%** using the new object of Class `FolderAnalyzer`.
   - Enhancements in 'Cleaning Step' within 'Google Photos Takeout Process'. Now the final clean is **75%** faster.
   - Enhancements in Overall pipeline execution of feature 'Google Takeout Processing'. Execution time reduced more than **50%** thanks to above enhancements.
   - Enhancements in Steps execution order and logger messages. Now is clearer to follow the process pipeline.
  - Enhancements in `build.py` module to reduce the Anti-Virus warning probability on Windows systems.
  - Renamed flag `-exeExifTool, --exec-exif-tool` by `-fnExtDates, --foldername-extracted-dates` to be more specific in the content of that output folder.
  - Enhancement in function `contains_takeout_structure()`. Now it stop checking subfolders when find any subfolder with 5 or more subfolder inside. This speed-up a lot the performance.
    
#### 🐛 Bug fixes:
  - Fixed minor issues in Logger module. 
  - Fixed a bug in function 'Guess date from filename' when filename or filepath contains some digits that were parsed as year of the file . Fixed in [#867](https://github.com/jaimetur/PhotoMigrator/issues/867).
  - Fixed bug [#864](https://github.com/jaimetur/PhotoMigrator/issues/864) in Push asset to Immich when the asset to push has not os.stat().st_mtime returning -1. Now those files returns first epoch (1970-01-01) as fallback. Fixed in [#867](https://github.com/jaimetur/PhotoMigrator/issues/867).

#### 📚 Documentation: 
  - Updated documentation with all changes.

---

## Release: v3.4.2  
### Release Date: 2025-07-10

#### 🚀 Enhancements:
  - Show skipped steps in 'Total Duration Summary' within 'Google Takeout Processing'. 
  - Maintain Step ids in 'Google Takeout Processing'.
    
#### 🐛 Bug fixes:
  - Fixed a bug in function get_file_date() function affecting files with EXIF tags in different format (UTC naive and UTC aware). Now all EXIF date tags are converted to UTC aware before extracting the oldest date.
  - Fixed a bug [#730](https://github.com/jaimetur/PhotoMigrator/issues/730) when the tool was executed without arguments and the input folder was selected using windows dialog pop-up.
  - Fixed a bug [#739](https://github.com/jaimetur/PhotoMigrator/issues/739) in function resolve_internal_path() that after code refactoring on v3.4.0, the function was not resolving properly the paths when te tool were executed from compiled binary file.

---

## Release: v3.4.1  
### Release Date: 2025-07-08

#### 🚀 Enhancements:
  - Banner included when loading Tool.
  - Renamed `Script` by `Tool` in all internal variables.
  - Changed order of Post-Process function in `Goolge Takeout Fixing` feature. Now Organize output folder by year/month structure have been moved to the end (after Analyze Output). In this way the date of each file can be loaded from the cached date dict generated during Analysys Phase).
  - Separate GPTH Tool folder from EXIF Tool folder.    
  - Improvement in Analysis Summary info (now it shows the number of Symbolic Links detected in Input/Output folders)

#### 🐛 Bug fixes:
  - Fixed a bug in function get_file_date() function affecting files with EXIF tags in different format (UTC naive and UTC aware). Now all EXIF date tags are converted to UTC aware before extracting the oldest date.
  - Fixed a bug [#649](https://github.com/jaimetur/PhotoMigrator/issues/649) in function resolve_internal_path() that after code refactoring on v3.4.0, the function was not resolving properly the paths when te tool were executed from compiled binary file.
  - Fixed a bug [#663](https://github.com/jaimetur/PhotoMigrator/issues/663) in function is_date_outside_range() when no date filters have been provided.

#### 📚 Documentation:
  - New logo design (thanks to @mbarbero).
  - Updated `Google Takeout Management` documentation to update Steps names and new times per steps based on latest changes.
  - Enhancement in README.md file to include Disclaimer, Repository Activity, Star History, Contributors and Related Projects.
  - Added CONTRIBUTING.md to the project.

---

## Release: v3.4.0  
### Release Date: 2025-06-30

#### 🚨 Breaking Changes:
  - Replaced argument `-gmtf, --google-move-takeout-folder` by `-gKeepTakeout, --google-keep-takeout-folder` argument and inverted the logic for Google Takeout Processing.  
           **NOTE: Now the tool moves assets from `TAKEOUT_FOLDER` to `<OUTPUT_FOLDER` by default.**
  - Replaced argument `-gcsa, --google-create-symbolic-albums` by `-gnsa, --google-no-symbolic-albums` argument and inverted the logic for Google Takeout Processing.  
           **NOTE: Now the tool creates Albums as symlinks/shortcuts to the original assets in `ALL_PHOTOS` folder by default.**
    
#### 🌟 New Features:
  - Created GitHub Forms on New Issues.
   - Auto-Update Issues Templates with new published releases.
   - Auto-Label Issues with selected Tool Version.
  - Added Step duration summary at the end of `Google Takeout Processing` feature.
  - Implemented logic for `-gKeepTakeout, --google-keep-takeout-folder` feature including an ultra fast and smart clonning folder algorithm. 
  - Call GPTH with `--verbose` argument when PhotoMigrator logLevel is VERBOSE.
  - Added new `VERBOSE` value for `-logLevel` argument.
  - Added new argument `-logFormat, --log-format` to define the format of the Log File. Valid values: `[LOG, TXT, ALL]`.
  - Added new argument `-config, --configuration-file` to Allow user to define configuration file (path and name).
  - Added new argument `-fnAlbums, --foldername-albums` to Allow user to define folder name for 'Albums'.
  - Added new argument `-fnNoAlbums, --foldername-no/albums` to Allow user to define folder name for 'No-Albums'.
  - Added new argument `-fnLogs, --foldername-logs` to Allow user to define folder name for 'Logs'.
  - Added new argument `-fnDuplicat, --foldername-duplicates-output` to Allow user to define folder name for 'Duplicates Outputs'.
  - Added new argument `-fnExtDates, --foldername-extracted-dates` to Allow user to define folder name for 'Exiftool Outputs'.
  - Added new argument `-exeGpthTool, --exec-gpth-tool` to Allow user to specify an external version of GPTH Tool binary.
  - Added new argument `-exeExifTool, --exec-exif-tool` to Allow user to specify an external version of EXIF Tool binary.
  - Added new argument `-gSkipPrep, --google-skip-preprocess` to Skipp Preprocess steps during Google Takeout Processing feature.
  
#### 🚀 Enhancements:
  - Code totally refactored and structured in a Single Package called `photomigrator` for a better portability and maintenance.
  - Code organized per packages modules within Core/Features/Utils Sub-Packages.
  - Reorganized Pre-checks/Pre-process/Process steps for a clearer maintenance and better visualization. 
  - New FileStatistics module have been added to completely redesign Counting files and extracting dates.
   - Improved performance on Counting files and extracting dates during Google Takeout Processing using an optimized multi-thread function.
   - Added Fallback to PIL when EXIFTOOL is not found during FileStatistics generation.
  - The Feature `Google Takeout Processing` is no longer called using the Pre-checks functions but always using the Process() function from ClassTakeoutFolder.
  - Included Input/Output folder size in Google Takeout Statistics.
  - Improved Logging messages and screen messages prefixes using Global Variables instead of hardcoded strings.
  - Improved Logging messages type detection when running GPTH (automatically detects warning messages and log them as warnings instead of info).
  - Inserted Profiler support to Profile any function and optimize it.
  - Removed `input_folder` after successfully completion of `Google Takeout Processing` if the user didn't use the flag `-gKeepTakeout, --google-keep-takeout-folder`. Note that this only remove the `input_folder` with a valid Takeout Structure, this will not remove your original Takeout Zip folder with your Takeout Zips.
  - Increased the number of threads to 2 * number of cpu cores in all multi-threads processing. 
  - Renamed argument `-loglevel` to `-logLevel`.
  - Renamed argument `-dashb` to `-dashboard`.
  - Renamed argument `-AlbFld` to `-AlbFolder`.
  - Renamed argument `-rAlbAss` to `-rAlbAsset`.
  - Renamed argument `-gpthErr` to `-gpthError`.
  - Replaced argument `-confirm, --request-user-confirmation` by `-noConfirm, --no-request-user-confirmation` and inverted logic. 
  - Updated **GPTH** to version `4.0.9` (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts. 
   - This release represents a fundamental restructuring of the codebase following **Clean Architecture** principles, providing better maintainability, testability, and performance.
###### 🚨 **Critical Bug Fixes**
  - **CRITICAL FIX**: Nothing mode now processes ALL files, preventing data loss in move mode
  - **FIXED: Data loss in Nothing mode** - Album-only files are now properly moved in Nothing mode instead of being silently skipped, preventing potential data loss when using move mode with `--album-behavior=nothing`
###### 🚀 **Improvements**
  - ##### **Performance & Reliability Improvements**
   - **Stream-based file I/O operations** replacing synchronous access
   - **Persistent ExifTool process** management (10-50x faster EXIF operations)
   - **Concurrent media processing** with race condition protection
   - **Memory optimization** - up to 99.4% reduction for large file operations
   - **Streaming hash calculations** (20% faster with reduced memory usage)
   - **Optimized directory scanning** (50% fewer I/O operations)
   - **Parallel file moving operations** (40-50% performance improvement)
   - **Smart duplicate detection** with memory-efficient algorithms
  - ##### **Domain-Driven Design Implementation**
   - **Reorganized codebase into distinct layers**: Domain, Infrastructure, and Presentation
   - **Introduced service-oriented architecture** with dependency injection container
   - **Implemented immutable domain entities** for better data integrity and performance
   - **Added comprehensive test coverage** with over 200+ unit and integration tests   
  - ##### **Service Consolidation & Modernization**
   - **Unified service interfaces** through consolidated service pattern
   - **Implemented ServiceContainer** for centralized dependency management
   - **Refactored moving logic** into strategy pattern with pluggable implementations
   - **Enhanced error handling** with proper exception hierarchies and logging
  - ##### **Intelligent Extension Correction**
   - **MIME type validation** with file header detection
   - **RAW format protection** - prevents corruption of TIFF-based files
   - **Comprehensive safety modes** for different use cases
   - **JSON metadata synchronization** after extension fixes
  - ##### **Enhanced Data Processing**
   - **MediaEntity immutable models** for thread-safe operations
   - **Coordinate processing** with validation and conversion
   - **JSON metadata matching** with truncated filename support
   - **Album relationship management** with shortcut strategies
  - ##### **Bug Fixes & Stability**
   - **Race condition elimination** in concurrent operations
   - **JSON file matching improvements** for truncated names
   - **Memory leak prevention** in long-running processes
   - **Cross-platform filename handling** improvements
  - ##### **Eight-Step Pipeline Architecture**
          1. **Extension Fixing** - Intelligent MIME type correction
          2. **Media Discovery** - Optimized file system scanning
          3. **Duplicate Removal** - Content-based deduplication
          4. **Date Extraction** - Multi-source timestamp resolution
          5. **EXIF Writing** - Metadata synchronization
          6. **Album Detection** - Smart folder classification
          7. **File Moving** - Strategy-based organization
          8. **Creation Time Updates** - Final timestamp alignment
        
#### 🐛 Bug fixes:
  - Fixed LOG_LEVEL change in `Google Takeout Processing Feature`.
  - Fixed a bug setting lovLevel because it wasn't read from GlobalVariables in set_log_level() function.
  - Fixed a bug in `Auto Rename Albums content based` when an Albums only contains Videos because the list of TAGS where search dates didn't include valid TAGs for Video files.
  - Fixed issue in MP4/Live Pictures Fixers when the original picture's json has .supplemental-metadata suffix.
  - Fixed issue with GPTH/EXIFTOOL paths when running the tool from docker

#### 📚 Documentation:
  - Modified 'Execution from Source' documentation to support the new package structure.
  - Renamed RELEASES-NOTES.md by CHANGELOG.md
  - Included CODE_OF_CONDUCT.md
  - Moved CHANGELOG.md, ROADMAP.md, DOWNLOADS.md, README.md and CODE_OF_CONDUCT.md to the root of the repository for more visibility.
  - Updated documentation with all changes.

---

## Release: v3.3.2  

### Release Date: 2025-06-16

#### 🌟 New Features:

#### 🚀 Enhancements:
  - Performance Improvements: 
   - Enhanced `MP4 from Live picture Fixing` during Google Takeout Processing to avoid check other candidates when the first one match. 
   - Enhanced `Google Takeout Processing` when launched by `Automatic Migration feature`. In this case, Albums are created as symbolic links to the original files within `<NO_ALBUMS_FOLDER>` folder to save disk space and processing time.
  - Ensure that filenames length are at least 40 chars before to Fix truncated special suffixes or truncated extensions during Google Takeout Processing. 
  - Workflows Improvements.
  - Enhanced Results Statistics in Google Takeout Processing to include differences and percentags of assets between Takeout folder and Output folder.
  - Created DataModels for a better structure on those functions that returns multiples values.
  - Enhanced Feature `Find Duplicates` during Google Takeout Processing.
   - Now the Tool will not detect as duplicates, those assets found in `<NO_ALBUMS_FOLDER>` folder and within any `Albums` subfolder.
  - Enhanced `Truncated Special Suffixees Fixing` during Google Takeout Processing to fix at the same time truncated `supplemental-metadata` and `other-special-suffixes` within a file. 
  - Enhanced `Truncated Extension Fixing` during Google Takeout Processing to avoid fixing truncated `supplemental-metadata` and `other-special-suffixes` because this is already done in above step. 
  - Updated GPTH to version `4.0.8` (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts. 
   - Fixed a bug in the `--fix-extension` feature.
   - Fixed a bug with truncated special suffixes or truncated extensions.
    

#### 🐛 Bug fixes:
  - Fixed unhandled exception in function `sync_mp4_timestamps_with_images()` when the image have been moved from output folder before to complete MP4 timestamp syncing.
  - Fixed 'Rename Albums' Feature when no date range is found in its name. Before it removed any date found, now, if is not possible to extract a date range, just keep the cleaned name (without date range prefix). 
  - Fixed Docker Version to include EXIF Tool.
  - Fixed an issue in `Google Takeout Processing` feature creating output folder when automatically switch to `--google-ignore-check-structure` when no detecting a valid Takeout Structure.
  - Fixed a bug [#649](https://github.com/jaimetur/PhotoMigrator/issues/649) in function resolve_internal_path() that after code refactoring on v3.4.0, the function was not resolving properly the paths when te tool were executed from compiled binary file.
  - Fixed a bug [#663](https://github.com/jaimetur/PhotoMigrator/issues/663) in function is_date_outside_range() when no date filters have been provided.

#### 📚 Documentation:
  - Improved Google Takeout Feature documentation.
  - Included GPTH Process Explanation documentation within Google Takeout Feature documentation.
  - Updated documentation with all changes.
  
---

## Release: v3.3.1

### Release Date: 2025-06-12

#### 🌟 New Features:
  - Added new argument _**`-graf, --google-rename-albums-folders`**_ to rename all albums folders based on content dates when finish Google Takeout Processing.
  - Added new flag _**`-noConfirm, --no-request-user-confirmation`**_ to Skip User Confirmation before to execute any Feature. (Requested by @VictorAcon).

#### 🚀 Enhancements:
  - Replace return arguments of `ClassTakeoutFolder.process()` method by a new object with all the arguments.
  - Added more info while running Google Takeout Processing feature.
  - Improved messages visualization of GPTH Processing in Automatic Migration Feature disabling progress bars within this Feature.
  - Improved Pre-Process steps in Google Takeout Processing with those new sub-steps:
   - Fixed JSON Metadata for MP4 videos associated to Live Pictures (Now also take into account the `.supplemental-metadata` suffix and any posible variation/truncation of it (i.e: `IMG_0159.HEIC.supplemental-metad.json -> IMG_0159.MP4.supplemental-metadata.json)`.
   - Fixed truncated special suffixes at the end of the file (i.e: `filename-edi.jpg -> filename-edited.jpg`). Also take into account the `.supplemental-metadata` suffix and  any posible variation/truncation of it
   - Fixed truncated extensions in JSON files (i.e: `filename.jp.json -> filename.jpg.json`). Also take into account the `.supplemental-metadata` suffix and  any posible variation/truncation of it
  - Updated **GPTH** to version `4.0.8` (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts. 
   - Fixed a bug in the albums folders creation when the album name start with a number.
   - Fixed skipping files whose content does not match with their extension.
  - Added Steps Names Info in Logs during Google Takeout Processing Feature.

#### 🐛 Bug fixes:
  - Fixed name of Takeout folder in info message while looking for Takeout folder structure. Before it showed the name of the first subfolder inside it instead of the name of the Takeout folder.
  - Fixed info while showing elapsed time on unpacking step. Before it said step 1 instead of unpacking step.
  - Fixed a bug in Automatic Migration Feature when `<SOURCE>` is a Zipped Takeout (before no assets to push were found during filtering process).
  - Fixed bug while moving assets to no-flatten folder structure if the asset has no system date. Now try to extract date from EXIF first, and if not found, get system date, if any date is found in any method, then assign a generic value.
  - Fixed bug while rename albums folders based on its content dates if some assets inside the folder has no system date. Now try to extract date from EXIF first, and if not found, get system date, if any date is found in any method, then assign a generic value.
  - Fixed a bug when using flag `--google-ignore-takeout-structure` in combination with `--google-move-takeout-folder` since when ignoring Takeout Structure, GPTH does not copy/move the assets to the output folder, so a manual copy/move is needed but input folder was deleted after step 2.
  - Fixed a bug showing stats when using flag `--google-move-takeout-folder` since original Takeout folder stats was calculated after GPTH delete it.
  
#### 📚 Documentation:
  - Removed NOTE blocks im main documentation description for all features. 
  - Updated Arguments Description documentation.
  - Removed **Automatic Migration** instructions from the main README.md (replaced by a link to the documentation file)
  - Removed **Planned Roadmap** from the main README.md (replaced by a link to Planned Roadmap file)
  - Updated documentation with all changes.

---

## Release: v3.3.0  

### Release Date: 2025-05-30

#### 🚨 Breaking Changes:
  - New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
  - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

#### 🌟 New Features:
  - Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
  - Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
  - Merged Synology/Immich arguments (now you can specify the client using a new argument _**`-client, --client \<CLIENT_NAME>`**_)
  - Added new argument _**`-client, --cient \<CLIENT_NAME>`**_ to set the Cloud Photo client to use.
  - Added new argument _**`-id, --account-id \<ID>`**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
  - Added new argument _**`-move, --move-assets`**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
  - Added support for 2FA in Synology Photos requesting the OTP Token if flag _**`-OTP, --one-time-password`**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
   - New flag _**`-OTP, --one-time-password`**_ to allow login into Synology Photos accounts with 2FA activated.
  - Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expressions). Added following new flag to execute this new features:
   - _**`-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>`**_
  - Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expressions). Added following new flag to execute this new features:
   - _**`-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>`**_
  - Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
   - _**`-mDupAlb, --merge-duplicates-albums`**_ 
  - Automatic filters flags detection for all Remove/Rename/Merge Albums features for Synology/Immich Photos
   - remove-all-assets
   - remove-all-albums
   - remove-albums
   - remove-empty-albums
   - remove-duplicates-albums
   - rename-albums
   - merge-albums
  - Automatic filters flags detection in Download features for Synology/Immich Photos.
   - download-all
   - download-albums
  - Request user confirmation before Rename/Remove/Merge massive Albums (show the affected Albums).
  - Run Google Takeout Photos Processor Feature by default when running the tool with a valid folder as unique argument.
  - Run Google Takeout Photos Processor Feature by default when running the tool without arguments, requesting the user to introduce Google Takeout folder. 

#### 🚀 Enhancements:
  - Improved Performance on Pull functions when no filtering options have been given.
  - Improved performance when searching Google Takeout structure on huge local folder with many subfolders.
  - Renamed `Automated Mode` to `Automatic Mode`.
  - Improved performance retrieving assets when filters are detected. Use smart filtering detection to avoid person filtering if not apply (this filter is very slow in Synology Photos)
  - Avoid logout from Synology Photos when some mode uses more than one call to Synology Photos API (to avoid OTP token expiration)  
  - Merged Features 'Remove All Albums' & 'Remove Albums by name' (You can remove ALL Albums using '.*' as pattern).
  - Merged Synology/Immich features using a parameter and replacing Comments and Classes based on it. 
  - Merged Synology/Immich HELP texts showed when running the different features.
  - Renamed All arguments starting with 's' (for synology) or 'i' (for immich) to remove the prefix, since now you can specify the client using the new flag _**`-client, --client`**_
  - Renamed flag _**`-gtProc, --google-takeout-to-process`**_ to _**`-gTakeout, --google-takeout`**_ to activate the Feature 'Google Takeout Processing'.
  - Renamed short argument _**`-RemAlb`**_ to _**`-rAlb`**_ to activate the Feature 'Remove Albums'.
  - Renamed short argument _**`-RenAlb`**_ to _**`-renAlb`**_ to activate the Feature 'Rename Albums'.
  - Renamed short argument _**`-MergAlb`**_ to _**`-mDupAlb`**_ to activate the Feature 'Merge Duplicates Albums'.
  - Updated GPTH to version `4.0.5` (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     
   - Re-written most of the code to clean screen logs and make it more easy to read (divided by steps). 
   - GPTH is now enhanced with EXIF Tool support for a better metadata fixing (supporting geolocations update, almost all media formats, multiple camera brands, etc...).     
   - EXIF Tool have been integrated into the binary file for GPTH to make use of it. 
  - Improved build-binary.py to support both compilers (Pyinstaller and Nuitka).     
  - Added Splash logo at the loading screen when execute from binaries on Windows.  
  - Renamed binaries files for architecture `amd64` from `amd64` to `x64`.     
  - Included binary for 'Windows arm64' architecture.     
  - Changed Compiler from **Pyinstaller** to **Nuitka** (better performance) to generate compiled binaries for all supported platforms.     
  - Many improvements and automations in GitHub Actions to generate new builds and releases.     

#### 🐛 Bug fixes:
  - Fixed issue when username/password contains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
  - Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**`--remove-albums-assets`**_ was selected (the assets were not removed properly).
  - Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
  - Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
  - Fixed a bug replacing argument provided with flag _**`-dAlb, --download-albums \<ALBUMS_NAME>`**_ in the HELP text screen.
  - Fixed a bug when using interactive pager for _**`-h, --help`**_ if terminal does not support it.
  - Minor bugs fixing.

#### 📚 Documentation:
  - Distinction between **arguments** and **flags** in documentation.
  - Included Arguments Description section with all **arguments** and **flags** description.
  - Updated arguments format in documentation.
  - Updated documentation with all changes.
  - Added tool logo and emojis to documentation files.

---

## Release: v3.2.0  

### Release Date: 2025-04-30

#### 🌟 New Features:
  - Added options to filter assets in all Immich/Synology/LocalFolder Actions:
  - by Type
  - by Dates
  - by Country
  - by City
  - by Person
  - Added new flag _**`-type, --filter-by-type=[image, video, all]`**_ to select the Asset Type to download (default: all)
  - Added new flag _**`-from, --filter-from-date <FROM_DATE>`**_ to select the Initial Date of the Assets to download
  - Added new flag _**`-to, --filter-to-date <TO_DATE>`**_ to select the Final Date of the Assets to download
  - Added new flag _**`-country, --filter-by-country <COUNTRY_NAME>`**_ to select the Country Name of the Assets to download
  - Added new flag _**`-city, --filter-by-city <CITY_NAME>`**_ to select the City Name of the Assets to download
  - Added new flag _**`-person, --filter-by-person <PERSON_NAME>`**_ to select the Person Name of the Assets to download
  - Added new flag _**`-parallel, --parallel-migration=[true, false]`**_ to select the Migration Mode (Parallel or Sequential). Default: true (parallel)
  - Included Live Dashboard in sequential Automatic Migration
  
#### 🐛 Bug fixes:
  - Minor bugs fixing

---

## Release: v3.1.0  

### Release Date: 2025-03-31

#### 🚨 Breaking Changes:
  - Config.ini file has changed to support multi-accounts over the same Cloud Photo Service. 

#### 🌟 New Features:
  - Support for running the Tool from Docker container.
  - Included Live Progress Dashboard in Automatic Migration process for a better visualization of the job progress.
  - Added a new argument **'--source'** to specify the \<SOURCE> client for the Automatic Migration process.
  - Added a new argument **'--target'** to specify the \<TARGET> client for the Automatic Migration process.
  - Added new flag '**-dashboard, --dashboard=[true, false]**' (default=true) to show/hide Live Dashboard during Automated Migration Job.
  - Added new flag '**-gpthInfo, --show-gpth-info=[true, false]**' (default=false) to show/hide progress messages during GPTH processing.
  - Added new flag '**--gpthError, --show-gpth-errors=[true, false]**' (default=true) to show/hide errors messages during GPTH processing.
  - Support for 'Uploads Queue' to limit the max number of assets that the Puller worker will store in the temporary folder to 100 (this save disk space). In this way the Puller worker will never put more than 100 assets pending to Upload in the temporary folder.
  - Support to use Local Folders as SOURCE/TARGET during Automatic Migration Process. Now the selected local folder works equal to other supported cloud services.
  - Support Migration between 2 different accounts on the same Cloud Photo Service. 

#### 🚀 Enhancements:
  - Completely refactored Automatic Migration Process to allow parallel threads for Downloads and Uploads jobs avoiding downloading all assets before to upload them (this will save disk space and improve performance). Also objects support has been added to this mode for an easier implementation and future enhancements.
  - Removed argument **'-AUTO, --AUTOMATIC-MIGRATION \<SOURCE> \<TARGET>'** because have been replaced with two above arguments for a better visualization.
  - Renamed flag '**-gitf, --google-input-takeout-folder**' to '**-gtProc, --google-takeout-to-process**' for a better understanding.
  - Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassTakeoutFolder, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
  - Added new Class ClassLocalFolder with the same methods as other supported Cloud Services Classes to manage Local Folders in the same way as a Photo Cloud Service.
  - ClassTakeoutFolder inherits all methods from ClassLocalFolder and includes specific methods to process Google Takeouts since at the end Google Takeout is a local folder structure.
  - Updated GPTH to version 3.6.0 (by @Wacheee) to cop latest changes in Google Takeouts. 

#### 🐛 Bug fixes:
  - Bug Fixing.

#### 📚 Documentation:
  - Documentation completely re-written and structured in different files
  - Documentation is now included as part of the distribution packages.

#### 🖥️ Live Dashboard Preview:
    ![Live Dashboard](/assets/screenshots/live_dashboard.jpg?raw=true)  

---

## Release: v3.0.0  

### Release Date: 2025-03-07

#### 🚨 Breaking Changes:
  - Unificate a single Config.ini file and included tags for the different configuration sections.

#### 🌟 New Features:
  - Added **_Immich Photos Support_**.
  - Added **_New Automatic Migration Feature_** to perform Fully Automatic Migration Process between different Photo Cloud Services
   - **-AUTO,   --AUTOMATIC-MIGRATION \<SOURCE> \<TARGET>**  
      This process will do an AUTOMATIC-MIGRATION process to Download all your Assets
      (including Albums) from the \<SOURCE> Cloud Service and Upload them to the
      \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE>
      Cloud Service.

      possible values for:
      <SOURCE> : ['google-photos', 'synology-photos', 'immich-photos'] or <INPUT_FOLDER>
      <TARGET> : ['synology-photos', 'immich-photos']  

  - Wildcards support on <ALBUMS_NAME> argument on --synology-download-albums and --immich-download-albums options.
  - Support to upload assets from/to any folder into Synology Photos (no need to be indexed within the Synology Photos root Folder)
  - Remove Duplicates Assets in Immich Photos after upload any Asset.
  - Added function to Remove empty folders when delete assets in Synology Photos
  - Set Log levels per functions and include '-logLevel, --log-level' argument to set it up.
  - Support for colors in --help text for a better visualization.
  - Support for colors in logger for a better visualization.
  - New Arguments Added: 
   - **-i,    --input-folder <INPUT_FOLDER>** Specify the input folder that you want to process.
   - **-o,    --output-folder <OUTPUT_FOLDER>** Specify the output folder to save the result of the processing action.
   - **-logLevel, --log-level ['debug', 'info', 'warning', 'error', 'critical']** Specify the log level for logging and screen messages.  
   - **-rAlbAsset,  --remove-albums-assets** 
      If used together with '-srAllAlb, --synology-remove-all-albums' or '-irAllAlb, --immich-remove-all-albums',  
      it will also delete the assets (photos/videos) inside each album.
   - **-AlbFolder,--albums-folders <ALBUMS_FOLDER>**
      If used together with '-iuAll, --immich-upload-all' or '-iuAll, --immich- upload-all', 
      it will create an Album per each subfolder found in <ALBUMS_FOLDER>. 

  - Added new options to Synology Photos Support:
   - **-suAll,    --synology-upload-all <INPUT_FOLDER>**.  
   - **-sdAll,    --synology-download-all <OUTPUT_FOLDER>**.
   - **-srAll,    --synology-remove-all-assets** to remove All assets in Synology Photos.  
   - **-srAllAlb, --synology-remove-all-albums** to remove Albums in Synology Photos (optionally all associated assets can be also deleted).   

  - With those changes the **_Synology Photos Support_** has the following options:
   - **-suAlb,    --synology-upload-albums <ALBUMS_FOLDER>**  
  - The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Synology Photos.
   - **-sdAlb,    --synology-download-albums <ALBUMS_NAME>**
  - The Tool will connect to Synology Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Download_Synology' within the Synology Photos root folder.
  - To extract all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --synology-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words.
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums 'album1', 'album2', 'album3'.
  - To download ALL Albums use 'ALL' as <ALBUMS_NAME>. 
   - **-suAll,    --synology-upload-all <INPUT_FOLDER>**  
  - The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into Synology Photos.  
  - If the <INPUT_FOLDER> contains a Subfolder called 'Albums' then, all assets inside each subfolder of 'Albums' will be associated to a new Album in Synology Photos with the same name as the subfolder
   - **-sdAll,    --synology-download-all <OUTPUT_FOLDER>**  
  - The Tool will connect to Synology Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>.  
  - Albums will be downloaded within a subfolder '<OUTPUT_FOLDER>/Albums/' with the same name of the Album and all files will be flattened into it.  
  - Assets with no Albums associated will be downloaded within a subfolder '<OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>/' and will have a year/month structure inside.
   - **-srEmpAlb  --synology-remove-empty-albums**  
  - The Tool will look for all Albums in your Synology Photos account and if any Album is empty, will remove it from your Synology Photos account.  
   - **-srDupAlb, --synology-remove-duplicates-albums**  
  - The Tool will look for all Albums in your Synology Photos account and if any Album is duplicated, will remove it from your Synology Photos account.
   - **-srAll,    --synology-remove-all-assets** to delete ALL assets in Synology Photos
   - **-srAllAlb, --synology-remove-all-albums** to delete ALL Albums in Synology Photos (optionally all associated assets can be also deleted).  

  - Added **_Immich Photos Support_** with the Following options to manage Immich API:
   - **-iuAlb,    --immich-upload-albums <ALBUMS_FOLDER>**  
  - The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Immich Photos.  
   - **-idAlb,    --immich-download-albums <ALBUMS_NAME>**  
  - The Tool will connect to Immich Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder.  
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums" "album1", "album2", "album3".  
  - To download ALL Albums use "ALL" as <ALBUMS_NAME>.   
   - **-iuAll,    --immich-upload-all <INPUT_FOLDER>**
  - The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into Immich Photos.  
  - If the <INPUT_FOLDER> contains a Subfolder called 'Albums' then, all assets inside each subfolder of 'Albums' will be associated to a new Album in Immich Photos with the same name as the subfolder
   - **-idAll,    --immich-download-all <OUTPUT_FOLDER>>**  
  - The Tool will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>.  
  - Albums will be downloaded within a subfolder of '<OUTPUT_FOLDER>/Albums/' with the same name of the Album and all files will be flattened into it.  
  - Assets with no Albums associated will be downloaded within a subfolder called '<OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>/' and will have a year/month structure inside.
   - **-irEmpAlb, --immich-remove-empty-albums**  
  - The Tool will look for all Albums in your Immich Photos account and if any Album is empty, will remove it from your Immich Photos account.  
   - **-irDupAlb  --immich-remove-duplicates-albums**  
  - The Tool will look for all Albums in Immich your Photos account and if any Album is duplicated, will remove it from your Immich Photos account.  
   - **-irAll,    --immich-remove-all-assets** to delete ALL assets in Immich Photos
   - **-irAllAlb, --immich-remove-all-albums** to delete ALL Albums in Immich Photos (optionally all associated assets can be also deleted).  
   - **-irOrphan, --immich-remove-orphan-assets**  
  - The Tool will look for all Orphan Assets in Immich Database and will delete them.  
  - **IMPORTANT!**: This feature requires a valid ADMIN_API_KEY configured in Config.ini.

#### 🚀 Enhancements:
  - New Script name '**PhotoMigrator**' (former 'GoogleTakeoutPhotos')
  - The Tool is now Open Source (all contributors that want to collaborate on this project are more than welcome)
  - Replaced 'ALL_PHOTOS' by '<NO_ALBUMS_FOLDER>' as output subfolder for assets without any album associated (be careful if you already run the Tool with previous version because before, the folder for assets without albums was named 'ALL_PHOTOS')
  - Ignored `@eaDir` folders when upload assets to Synology/Immich Photos.
  - Refactor and group All Google Takeout arguments in one block for 'Google Photos Takeout' Support.
  - [X] Refactor normal_mode to google_takeout_mode.
  - Changed the logic to detect google_takeout_mode (former normal_mode)
  - Merged -z and -t options in just one option ('-gtProc, -google-takeout-to-process') and detect if contains Takeout Zip files, in that case Zip files will be Unzipped to <TAKEOUT_FOLDER>_<TIMESTAMP> folder.
  - Removed SYNOLOGY_ROOT_PHOTOS_PATH from Config.ini, since it is not needed anymore.
  - Removed Indexing Functions on ServiceSynology file (not needed anymore)
  - Code refactored.
  - Renamed options:
   - -sca,  --synology-create-albums is now **-suAlb,  --synology-upload-albums <ALBUMS_FOLDER>**.
   - -sea,  --synology-extract-albums is now **-sdAlb,  --synology-download-albums <ALBUMS_NAME>**.
   - -fsym, --fix-symlinks-broken <FOLDER_TO_FIX> is now **-fixSym, --fix-symlinks-broken <FOLDER_TO_FIX>**.
   - -fdup, --find-duplicates <ACTION> <DUPLICATES_FOLDER> is now **-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>**.
   - -pdup, --process-duplicates <DUPLICATES_REVISED> is now **-procDup, --process-duplicates <DUPLICATES_REVISED>**.

#### 🐛 Bug fixes:
  - Fixed limit of 250 when search for Immich assets.
  - Fixed Remove Albums API call on Immich Photos to adapt to the new API changes.
  - Minor Bug Fixing.  

#### 📚 Documentation:
  - Added Help texts for Google Photos Mode.
  - Updated -h, --help to reflect the new changes.
  - Moved at the end of the help the standard option (those that are not related to any Support mode).
  - Included _CHANGELOG.md_ and _ROADMAP.md_ files to the distribution package.

---

## Release: v2.3.0  

### Release Date: 2025-01-14

#### New Features:
  - Added new argument to show the Tool version (-v, --version)
  - Added new argument to Extract Albums from Synology Photos (-sea, --synology-extract-albums)
  - Added Pagination option to Help text
#### Enhancements:
  - Removed EXIF Tool (option -re, --run-exif-tool) for performance issues
  - Renamed argument -ca, --create-albums-synology-photos to -sca, --synology-create-albums
  - Renamed argument -de, --delete-empty-albums-synology-photos to -sde, --synology-remove-empty-albums
  - Renamed argument -dd, --delete-duplicates-albums-synology-photos to -sdd, --synology-remove-duplicates-albums
  - Code refactored
#### Bug Fixing:
  - Minor Bug Fixing

---

## Release: v2.2.1  

### Release Date: 2025-01-08

#### New Features:
  - Compiled version for different OS and Architectures
  - Linux_amd64: ready
  - Linux_arm64: ready
  - MacOS_amd64: ready
  - MacOS_arm64: ready
  - Windows_amd64: ready
#### Enhancements:
  - GitHub Integration for version control and automate Actions
  - Automatic Compilation for all OS and supported Architectures
  - Code refactored
#### Bug Fixing:
  - Minor Bug Fixing

---

## Release: v2.2.0  

### Release Date: 2025-01-04

#### New Features:
  - Compiled version for different OS and Architectures
  - Linux_amd64: ready
  - Linux_arm64: ready
  - [ ] MacOS_amd64: under development
  - MacOS_arm64: ready
  - Windows_amd64: ready
#### Enhancements:
  - Code Refactored
#### Bug Fixing:
  - Minor Bug Fixing

---

## Release: v2.1.0  

### Release Date: 2024-12-27

#### New Features:
  - Added ALL-IN-ONE mode to Automatically process your Google Takeout files (zipped or unzipped), process them, and move all your Photos & Videos into your Synology Photos personal folder creating all the Albums that you have in Google Photos within Synology Photos.
  - New flag -ao,  --all-in-one <INPUT_FOLDER> to do all the process in just One Shot. The Tool will extract all your Takeout Zip files from <INPUT_FOLDER>, will process them, and finally will connect to your Synology Photos account to create all Albums found and import all the other photos without any Albums associated.
#### Enhancements:
  - Code Refactored
#### Bug Fixing:
  - Minor Bug Fixing

---

## Release: v2.0.0  

### Release Date: 2024-12-24

#### New Features:
  - Added Synology Photos Management options with three new Extra Features:
  -- New flag -ca,  --create-albums-synology-photos <ALBUMS_FOLDER> to force Mode: 'Create Albums in Synology Photos'. The Tool will look for all Albums within ALBUM_FOLDER and will create one Album per folder into Synology Photos.
  -- New flag -de,  --delete-empty-albums-synology-photos tofForce Mode: 'Delete Empty Albums in Synology Photos'. The Tool will look for all Albums in Synology your Photos account and if any Album is empty, will remove it from your Synology Photos account. 
  -- New flag -dd,  --delete-duplicates-albums-synology-photos tofForce Mode: 'Delete Duplicates Albums in Synology Photos'. The Tool will look for all Albums in your Synology Photos account and if any Album is duplicated, will remove it from your Synology Photos account. 
  - New Argument: -ra, --rename-albums <ALBUMS_FOLDER> to rename all Albums subfolders and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  
#### Enhancements:
  - Support to run on Synology NAS running DSM 7.0 or higher
  - Code refactored
#### Bug Fixing:
  - Minor bug fixed

---

## Release: v1.6.0  

### Release Date: 2024-12-18

#### New Features:
  - Included new flag '-pd, --process-duplicates-revised' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode' with 'duplicates-action=move'. In that case, the Tool will move all duplicates found to `<DUPLICATES_FOLDER>` and will generate a CSV file that can be revised and change the Action column values.
    Possible Actions in revised CSV file are:
  - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanently removed
  - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
  - replace_duplicate : Use this action to replace the principal file chosen for each duplicate and select manually the principal file
     - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
     - and Original Principal file detected by the Script will be removed permanently
#### Bug Fixing:
  - Fixed some minor bugs.

---

## Release: v1.5.1  

### Release Date: 2024-12-17

#### New Features:
  - Included progress bar in most of all the steps that consume more time during the Tool execution.
#### Enhancements:
  - Improved performance in Find_Duplicates function..
#### Bug Fixing:
  - Fixed logic of Find_Duplicates algorithm and include a new field in the Duplicates.csv output file to provide the reason to decide principal file of a duplicates set.
  - Fixed some minor bugs.

---

## Release: v1.5.0  
### Release Date: 2024-12-11

#### New Features:
  - Added new flag '-rd, --remove-duplicates-after-fixing' to remove duplicates files in OUTPUT_FOLDER after fixing all the files. Files within any Album will have more priority than files within 'Photos from *' or 'ALL_PHOTOS' folders.
  - Added new flag '-sa, --symbolic-albums' to create Symbolic linked Albums pointing to the original files. This is useful to safe disk space but the links might be broken if you move the output folders or change the structure.
  - Added new flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' to execute the Tool in Mode 'Fix Symbolic Links Broken' and try to fix all symbolics links broken within the <FOLDER_TO_FIX> folder. (Useful if you use Symbolic Albums and change the folders name or relative path after executing the Tool).
  - Added new info to Final Summary section with the results of the execution.
#### Enhancements:
  - Now the Tool automatically fix Symbolic Albums when create Folder Structure per year or year/month and also after moving them into Albums folder.
  - Change help to include the new changes.
#### Bug Fixing:
  - Fixed Find_Duplicates function. Now is smarter and try to determine the principal folder and file when two or more files are duplicates within the same folder or in different folders.
  - Fixed some minor bugs.

---

## Release: v1.4.1  
### Release Date: 2024-12-10

#### Enhancements:
  - Modified Duplicates.txt output file. Now is a CSV file, and it has a new format with only one duplicate per row and one column to display the number of duplicates per each principal file and other column with the action taken with the duplicates. 
  - Modified default value for No-Albums-Structure, before this folder had a 'flatten' structure, now by default the structure is 'year/month' but you can change it with the flag '-ns, --no-albums-structure'.
  - Albums-Structure continues with 'flatten' value by default, but you can change it with the flag '-as, --albums-structure'.
  - Change help to include the new changes.
#### Bug Fixing:
  - Fixed some minor bugs.

---

## Release: v1.4.0  
### Release Date: 2024-12-08

#### New Features:
  - Added smart feature to Find Duplicates based on file size and content.
  - Two news flags have been added to run the Tool in "Find Duplicates Mode": 
        '-fd,, --find-duplicates-in-folders' to specify the folder or folders where the Tool will look for duplicates files
        '-da, --duplicates-action' to specify the action to do with the duplicates files found.
  - If any of those two flags are detected, the Tool will be executed in 'Fin Duplicates Mode', and will skip all the Steps for fixing photos. Only Find Duplicates function will be executed.
#### Enhancements:
  - Change help to include the new changes.
#### Bug Fixing:
  - Fixed some minor bugs.

  ```
  
  Example of use:
  
  ./OrganizeTakeoutPhotos --find-duplicates-in-folders ./Albums ./ALL_PHOTOS --duplicates-action move
  
  With this example, the Tool will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
  If finds any duplicated, will keep the file within ./Albums folder (bacause it has been passed first on the list)
  and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the Tool.
  
  ```

---

## Release: v1.3.1  
### Release Date: 2024-12-08

#### Enhancements:
  - Removed warnings when some .MP4 files does not belongs to any Live picture.

---

## Release: v1.3.0  
### Release Date: 2024-12-04

#### New Features:
  - Added Script version for MacOS 
  - Included a Pre-process step (after unzipping the Zip files) to remove Synology metadata subfolders (if exists) and to look for .MP4 files generated by Google Photos that are extracted from Live picture files (.heic, .jpg, .jpeg) but doesn't have .json associated.
  - Now the Tool by default doesn't skip extra files such as '-edited' or '-effect'.
  - Included new argument '-se, --skip-extras' to skip processing extra files if desired.
  - Now the Tool by default generates flatten output folders per each album and for ALL_PHOTOS folder (Photos without any album).
  - Included a new function to generate a Date folder structure that can be applied either to each Album folder or to ALL_PHOTOS folder (Photos without any album) and that allow users to decide witch date folder structure wants. Valid options are: ['flatten', 'year', 'year/month', 'year-month']'.
  - Included new argument '-as, --albums-structure ['flatten', 'year', 'year/month', 'year-month']' to  specify the type of folder structure for each Album folder.
  - Included new argument '-ns, --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']' to specify the type of folder structure for ALL_PHOTOS folder (Photos that are no contained in any Album).
  - Now the feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture is more robust since all files are flattened and there is more chance to find a Live picture with the same name of the .MP4 file in the same folder. 
#### Enhancements:
  - Removed arguments '-fa, --flatten-albums' and '-fn, --flatten-no-albums' because now by default the Tool generates those folders flattened.
  - Change help to include the new changes.
#### Bug Fixing:
  - Fixed some minor bugs.

---

## Release: v1.2.2  
### Release Date: 2024-12-02

#### New Features:
  - Included new argument '-mt, --move-takeout-folder' to move (instead of copy) photos/albums from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>. This will let you save disk space and increase execution speed. CAUTION: With this option you will lost your original unzipped takeout files. Use this only if you have disk space limitation or if you don't care to lost the unzipped files because you still have the original zips files.
  - Argument '-se, --skip-exif-tool' renamed to '-re, --run-exif-tool'. Now EXIF Tool will not be executed by default unless you include this argument when running the Tool.
  - Argument '-sl, --skip-log' renamed to '-nl, --no-log-file' for better comprehension.
  - New feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture. With this feature the Tool will look for files picture files (.HEIVC, .JPG, .JPEG) with the same name than .MP4 file and in the same folder. If found, then the .MP4 file will have the same timestamp than the original picture file.
  - New feature to move_folders with better performance when you use the argument '-mt, --move-takeout-folder'.
#### Enhancements:
  - Now GPTH Tool / EXIF Tool outputs will be sent to console and logfile.
  - Change help to include the new changes.
#### Bug Fixing:
  - Fixed some minor bugs.

---

## Release: v1.2.1  
### Release Date: 2024-11-29

#### New Features:
  - Included new argument '-it, --ignore-takeout-structure' to Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
  - Changed log engine to generate log.info, log.warning and log.error messages that can be parsed with any log viewer easily.
#### Enhancements:
  - Change help format for better reading
#### Bug Fixing:
  - Fixed bug when running in some linux environment where /tmp folder has no exec attributes
  - Fixed some minor bugs.

---

## Release: v1.2.0  
### Release Date: 2024-11-27

#### New Features:
  - Created standalone executable files for Linux & Windows platforms.
#### Enhancements:
  - Script migrated to Python for multi-platform support.
  - Improve performance
  - replaced '-s, --skip-unzip' argument by '-z, --zip-folder <ZIP_FOLDER>'. Now if no use the argument -'z, --zip-folder <ZIP_FOLDER>., the Tool will skip unzip step.
  - Improved flatten folders functions.
#### Bug Fixing:
  - Fixed some minor bugs.

---

## Release: v1.0.0 to v1.2.0  
### Release Date: 2024-11

  - Preliminary not published Script in bash.

---
