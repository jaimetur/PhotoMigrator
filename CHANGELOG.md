# 🗓️ CHANGELOG
[Planned Roadmap](/ROADMAP.md) for the following releases
[Changelog](/CHANGELOG.md) for the past releases

---

## Release: v4.6.0
### Release Date: 2026-07-21
  
#### 🚨 Breaking Changes:
  - Replaced `--no-request-user-confirmation` with `--request-user-confirmation=true|false`. Confirmation remains enabled by default; unattended runs must now use `--request-user-confirmation=false`.

#### 🌟 New Features:
  - Extended `Remove Duplicate Assets` to the cloud-service modules for Synology Photos, Immich Photos, and NextCloud Photos. All cloud interfaces now expose the required `--duplicate-asset-keeper {oldest, newest}` selector (default: `newest`). Google Photos also exposes the module and selector consistently, but reports that no deletion can be performed because its public Library API has no media-item deletion operation.
  - Added `--google-process-people=true|false` to the Google Takeout `Processing Flags` section in the Web Interface, GUI, and TUI. It defaults to enabled and controls whether Google Takeout JSON person metadata is processed and whether the reusable people map is generated.
  - Added opt-in Google Takeout people-label import for Immich. Google Takeout processing now preserves `takeout_people_metadata.json` in the processed output, keyed by normalized asset filename with its person labels plus taken, creation, and modification dates. Step 4.1 logs the unique people count and writes the map immediately; Final Cleaning writes it again after GPTH in case its output initialization removed the first copy. Identical filenames retain independent entries and are resolved through the nearest distance between the processed asset's EXIF/filesystem dates and the three Takeout dates; equal nearest candidates merge their people labels and are logged. With `--import-people` enabled, Automatic Migration logs `People found: N` for every pushed or duplicated Immich asset, including zero; the field is absent when the flag is disabled. The final summaries for Automatic Migration, Immich Upload All, and Immich Upload Albums now report the unique Takeout people successfully assigned to at least one asset. `--google-process-people=true|false` controls this Takeout-side processing and defaults to enabled; disabled runs ignore people sidecars and do not generate the map. `--import-people` is available for Immich `Upload All`, `Upload Albums`, and Automatic Migration when its destination is Immich. Following immich-go's `--people-tag` behavior, the importer creates/reuses `people/<name>` tags and attaches them to matching assets without changing Immich face assignments.
  - Added the Immich metadata-preserving implementation of `Remove Duplicate Assets` (`--remove-duplicates-assets`). Its original exact filename-and-size detector remains available as a fallback, it displays every detected group and proposed keeper, and it requests confirmation before deletion when confirmations are enabled. It merges available albums, tags, favorites, descriptions, ratings, and safely transferable assigned faces into the keeper before permanently deleting redundant assets.

#### 🚀 Enhancements:
  - Scoped `--one-time-password` to Synology Photos throughout the Web Interface, GUI, and TUI. It is now available as an optional argument for every Synology module and in Automatic Migration only when either endpoint is Synology.
  - Made people import controls contextual in every interactive interface. `--import-people` is shown for Immich `Upload All` and `Upload Albums`, and in Automatic Migration only when the selected target is Immich. The control remains available to CLI users as an optional argument.
  - Improved `Remove Duplicate Assets` inventory feedback across cloud backends. Immich uses `/api/search/statistics` for an exact user-visible total before its determinate 1,000-asset-page bar; Synology reads the native paginated result total for the same purpose; and NextCloud displays the real received-file count while traversing WebDAV without performing a wasteful second recursive scan, because WebDAV exposes no reliable recursive total. All scans now state clearly that large libraries can take several minutes; unsupported statistics endpoints fall back safely to indeterminate progress.
  - Moved `--prefer-canonical-album-names` and `--consolidate-similar-albums` out of the Web Interface `Configuration > General Arguments` panel into the features that implement them: cloud uploads and Automatic Migration.
  - Applied the same contextual placement for `--prefer-canonical-album-names` and `--consolidate-similar-albums` in the TUI and desktop GUI: they no longer appear in General Arguments and are available only in cloud upload and Automatic Migration forms.
  - Optimized Immich `Remove Duplicate Assets` inventory retrieval by omitting person associations from the full paginated scan. Complete relationship metadata is now retrieved only for the small set of duplicate candidates before confirmation and deletion, retaining the face-safety check while avoiding an expensive people join and payload expansion for every library asset.
  - Removed inactive `--prefer-canonical-album-names` and `--consolidate-similar-albums` controls from Google Takeout and iCloud Takeout in the Web Interface, TUI, and desktop GUI. The codebase has no Takeout-side reads of these flags; they remain available only where their behavior is implemented.
  - Changed the Google Takeout Web controls for `--show-gpth-info`, `--show-gpth-errors`, and `--google-process-people` from true/false comboboxes to boolean checkboxes, matching the existing TUI and desktop GUI behavior while preserving their default-enabled state.
  - Restored Immich `Remove Duplicate Assets` inventory pages to 1,000 assets after compatibility testing showed that the target server rejects larger metadata pages.
  - Enhanced Immich `Remove Duplicate Assets` to preserve assigned people when deleting a duplicate group. The manual merge transfers faces only when every asset has the same Immich checksum and compatible normalized geometry, creating only faces missing from the keeper. Unsafe or unavailable face transfers are reported but no longer block deletion of the rest of the duplicate group.
  - Added Immich-native duplicate detection to `Remove Duplicate Assets` through `--immich-duplicates-algorithm=true|false` (default: enabled). The module uses Immich's visually similar duplicate groups by default; native deletion delegates the supported merge to Immich, while disabling it uses PhotoMigrator's guarded manual merge. `--duplicate-asset-keeper` adds the `better-quality` strategy, selected by default with native detection and based on Immich's suggested quality keeper; `oldest` and `newest` remain available.
  - Placed the `Immich Remove Duplicate Assets` account selector after its native-detection and keeper controls in the Web Interface, GUI, and TUI, and clarified that disabling native detection uses exact filename-and-size groups for cases such as repeated processed-Takeout uploads whose differing EXIF tag values prevented Immich duplicate rejection.
  - Added a runtime notice before Immich native duplicate detection explaining that retrieval time depends on library size and the number of duplicate groups found.
  - Renamed the Immich native duplicate-detection flag to `--immich-duplicates-algorithm`.
  - Expanded Immich `Remove Duplicate Assets` metadata preservation and its pre-deletion review. The preview now hydrates every candidate and reports visibility/archived state, capture date, coordinates, stack membership, and face references. Before deletion, the selected keeper preserves the most restrictive visibility (including archived assets), fills missing capture date and geolocation, and reconstructs affected stacks around the keeper; groups whose stack or metadata operations cannot be completed are skipped rather than deleted.
  - Added the optional Immich-only `--immich-duplicates-deletion=true|false` flag to `Remove Duplicate Assets` across CLI, Web, TUI, and GUI. It defaults to enabled with `--immich-duplicates-algorithm=true`, and is disabled when native detection is off; when enabled, PhotoMigrator sends the selected keeper and redundant native duplicate assets to Immich's Alpha resolver, which merges its supported metadata and moves redundant assets to trash. The default without native detection keeps PhotoMigrator's guarded manual merge and permanent deletion path.
  - Linked the Immich duplicate-resolution controls across CLI, Web, TUI, and GUI: disabling `--immich-duplicates-algorithm` now disables `--immich-duplicates-deletion` and selects PhotoMigrator's manual flow; enabling native detection defaults the native-deletion control back to enabled.
  - Hardened the CLI dependency between the Immich duplicate flags: `--immich-duplicates-deletion` defaults to `true` with native detection, but an explicitly enabled native-deletion flag is rejected when `--immich-duplicates-algorithm=false`.
  - Documented the `--immich-duplicates-deletion` trade-off across the Immich guide and CLI argument references: native resolution merges Immich's documented fields and moves assets to trash, while disabling it invokes PhotoMigrator's guarded manual merge with additional capture-date, stack, and safe face/person preservation before permanent deletion.
  - Prevented interactive Immich manual duplicate runs from emitting the disabled native-deletion option. With native detection off, Web, GUI, and TUI previews now omit `--immich-duplicates-deletion`; CLI validation also accepts an explicit `false` value while continuing to reject native deletion enabled without native detection.
  - Finalized Immich duplicate-review metadata loading with a bounded 100-worker asset pool. It loads complete asset details and album memberships concurrently, preserving group order while reporting real completed-candidate progress; the manual merge applies Immich's same-coordinate rule for locations.
  - Finalized duplicate-review name resolution for albums, tags, and people. It reads cached catalog maps, falls back to legacy `/api/people` pagination where required, resolves remaining people directly and through the Faces API, and retains a UUID only when Immich has no display name.
  - Reworked the Immich duplicate-review preview into a side-by-side ASCII table. Metadata fields are rows and the keeper plus redundant assets are columns; long values wrap within cells, collections show their count and one name per line, and optional rows appear only when at least one candidate supplies the value.
  - Parallelized the known-page Immich inventory scan used by duplicate analysis with up to 100 concurrent 1,000-asset metadata requests while preserving page order in the resulting inventory. Servers that cannot provide an inventory total keep the existing sequential pagination fallback.
  - Added a per-candidate `Size` row below `ID` in the Immich duplicate-review comparison table, so keeper and redundant asset file sizes can be compared directly.
  - Added the effective keeper criterion, such as `newest`, `oldest`, or `better-quality`, to the Immich duplicate-review table's keeper-column header.
  - Disabled per-candidate album-membership reads during the Immich duplicate-review preview to reduce review latency. The `Albums` row is omitted from that preview; PhotoMigrator's manual deletion flow still loads and merges album memberships before deletion, while Immich's native resolver preserves them server-side.
  - Marked `--immich-duplicates-algorithm` and `--immich-duplicates-deletion` as required selections for Immich `Remove Duplicate Assets` in Web, GUI, and TUI. Active native-detection commands now include both values explicitly; native deletion remains unavailable when detection is disabled.
  - Reclassified startup configuration logging: `Optional Flags Provided` now lists every effective optional flag owned by the selected feature/module, while the former `Optional Flags Default` section is now `General Arguments` and contains the tool-wide shared arguments.
  - Added `--remove-albums-assets` to the startup `General Arguments` listing, while keeping `--albums-folders` scoped to `Upload All` and `--preview-album-actions` scoped to its supported album modules.
  - Added a red `Restore Default` action below the `General Arguments` cards in Web, GUI, and TUI. It restores all visible general fields to their defaults, persists the reset state where enabled, and refreshes the command preview without changing feature-specific values.
  - Set the real default for `--filter-by-type` to `all`, aligning CLI parsing, General Arguments restoration, and interactive selectors with the documented behavior.

#### 🐛 Bug fixes:
  - Fixed Immich people import during Automatic Migration for mapped duplicate assets. PhotoMigrator now resolves the existing Immich asset ID only for assets with Takeout labels, attempts the import, and logs the map load, person count, and resulting import/skip outcome at `INFO` level.
  - Fixed Automatic Migration desktop GUI flag alignment: conditional `--import-people` and `--one-time-password` controls are now added to the shared three-column flags grid and use the remaining slot in the preceding row when available.
  - Fixed the Web Interface discarding the `--one-time-password` field after building Synology module arguments, which prevented the optional 2FA control from being displayed.
  - Fixed Immich `Remove Duplicate Assets` detection to use the current `exifInfo.fileSizeInByte` response field, with fallback support for older size fields. Duplicate groups are no longer silently discarded when the legacy `fileSize` field is absent, and the analysis now reports assets that genuinely lack a usable size.
  - Fixed `Synology Photos` `Shared Space` assets without albums being omitted from `Download All` and `Automatic Migration` when asset filters were active (issue `#1173`). When Shared Space albums are detected, PhotoMigrator now supplements the personal-space global inventory with a paginated `folder_id` inventory from the Synology Photos folder API, applies the configured filters to that recovered inventory, merges assets by their stable Synology ID, and only then excludes assets already represented by albums. This keeps the existing album APIs as the primary source for album contents while recovering the `ALL_PHOTOS` assets that Synology's global timeline request does not expose in Shared Space.
  - Fixed Immich duplicate-review metadata names for face associations. The preview now resolves the associated person ID rather than the face-record ID and accepts the wrapped `/people` response used by current Immich versions, so named people are shown instead of unresolved UUIDs. Its metadata dictionary now uses `keeper` and `remove_N` labels instead of repeating asset UUIDs already displayed in the proposed deletion list.
  - Fixed Immich duplicate-review completeness by loading each candidate's album memberships through the stable `GET /albums?assetId=...` API, which is not included in `AssetResponseDto`. The review now also falls back to `GET /people/{id}` when the paginated people list omits a referenced person, so album and person names remain visible and the guarded manual merge receives the full album set.
  - Fixed the cloud upload contextual help for `--prefer-canonical-album-names` to describe uploaded albums consistently in the Web Interface, GUI, and TUI.
  - Fixed the Web Interface `Immich Remove Duplicate Assets` controls so `--immich-duplicates-algorithm` and `--immich-duplicates-deletion` are rendered as required selections, while an explicit `false` value is accepted and emitted instead of being mistaken for a missing argument.
  - Fixed `--request-user-confirmation` rendering as a boolean toggle in Web, GUI, and TUI. The `foldername-*` fields now render as plain text with their effective default names and no longer expose folder-picker controls.

#### 📚 Documentation:
  - Updated documentation with all changes.
  - Documented `Remove Duplicate Assets` in the cloud-feature matrix and all cloud-service guides, including keeper selection, confirmation, backend-specific metadata limitations, and deletion safeguards.
  - Documented the Google Takeout people-processing flag, Immich-only people-import visibility, and Synology-only OTP visibility in the relevant interface and feature guides.
  - Documented Google Takeout people-map processing, including its dedicated pre-GPTH `Step 4.1` capture phase, Immich `--import-people` uploads, and the corresponding Automatic Migration behavior and limitations.
  - Added `Remove Duplicate Assets` and `--duplicate-asset-keeper {oldest, newest}` to the CLI syntax, full/short arguments references, and Automatic Migration guide, including its independent-module scope.
  - Added the Google Takeout people-processing and Immich people-import flags to the CLI syntax and both full/short argument references, and updated the Automatic Migration guide with their scope, map lifecycle, duplicate-resolution behavior, and logging details.
  - Updated CLI, cloud-feature, and Docker deployment documentation for `--request-user-confirmation=true|false`.

---

## Release: v4.5.0
### Release Date: 2026-07-18
  
#### 🚨 Breaking Changes:
  - Removed the discontinued `Immich Photos -> Remove Orphan Assets` module from all exposed interfaces (`Web`, `CLI`, `TUI`, and `GUI`) and from the related `Immich` documentation, while keeping the underlying implementation paths commented/preserved in code for possible future reuse.

#### 🌟 New Features:
  - Added a new cloud-only `Consolidate Albums Names` feature for `Google Photos`, `Synology Photos`, `Immich Photos`, and `NextCloud Photos`, available from CLI, Web Interface, TUI, and desktop GUI. This action reuses the same equivalent-album-family detection logic as `--consolidate-similar-albums` but operates entirely in the destination cloud without uploading new assets. On targets that support album deletion (`Immich`, `Synology`, `NextCloud`), redundant albums are removed after confirmed reassignment; on `Google Photos`, redundant variants are kept because the public API cannot delete albums.
  - Added an `Estimated Time` indicator to the `Automatic Migration` live dashboard in both the terminal UI and the Web Interface. The estimate is computed from the current elapsed time, the number of already `pulled` assets, and the remaining pending assets (`total_assets - pulled_assets`), so long-running migrations now show an approximate remaining duration without being skewed by duplicate-heavy push phases.
  - Added the optional `--one-time-password` flag to `Automatic Migration` across the Web Interface, CLI TUI, and desktop GUI whenever either the selected `source` or `target` is `Synology`, so Synology 2FA migrations can be configured directly from those UIs instead of only from the Synology-specific cloud module. (Issue #1174).
  - Split the Docker Web Interface main workspace into two dedicated pages, `Features` and `Configuration`, while keeping the shared hero/header and authentication flow. The root web route now redirects to the `Features` workspace, and users can switch between both pages from a dedicated top-level tab navigation.
  - Added a dedicated top-level Web Interface tab-strip for `Features` and `Configuration`, visually separated from the documentation buttons and styled as a workspace selector instead of a generic button row. This makes the active working context much clearer when moving between execution and configuration tasks.
  - Added a new descriptive card above `Configuration Panel -> General Arguments`, explaining the purpose of shared/global arguments and listing them grouped by the same categories used in the editor cards (`Logs`, `Execution`, `Naming & Folders`, `Filters`, and `Other`).
  - Added new descriptive cards above `Configuration Panel -> Features Config` and `Configuration Panel -> App Settings`, so all three configuration sub-tabs now include an inline help summary consistent with the documentation cards already used by Takeout and cloud feature panels.
  - Replaced the previous top-level `Features` / `Configuration` navigation buttons in the Web Interface with integrated tab-style selectors attached to their corresponding panels, so workspace switching now follows the same visual language as the internal feature/configuration tab systems.
  - Added a dedicated `Process Input` panel to the Web Interface `Output Panel`, placed below the live log and above the `Run` / `Stop` buttons. When a running job requests interactive input, the web UI can now send free-form text directly to the process stdin, while still preserving the existing quick `Yes` / `No` shortcuts.
  - Promoted the Web Interface `Output Panel` into its own top-level workspace tab and page, placed between `Features` and `Configuration`, so execution output can now be opened independently while preserving the same natural tab navigation style as the other main workspaces.

#### 🚀 Enhancements:
  - Added targeted `DEBUG` performance traces for `Automatic Migration` local-folder pipelines and the Web Interface live log/dashboard path. Debug logs now include per-asset pull/push/album-association timing plus backend dashboard snapshot/output processing timings, and the browser can emit optional `console.debug` render timings when `debug_web_perf=1` or `localStorage.photomigrator_web_perf_debug = \"1\"` is enabled.
  - Reworked the Web Interface `Automatic Migration` live dashboard so its counters no longer depend on reparsing the execution log. The migration subprocess now emits structured dashboard snapshots, the backend persists them per job, and every browser session receives the same synchronized counters after refresh or from another device without needing the full log history.
  - Refined the Web Interface operator flow around module execution. The `Execution Output` panel now includes its own `Run module` / `Stop module` button pair in addition to the existing controls in `Feature Selector`, and the `Feature Selector` title now shows the currently selected module name (for example `Feature Selector: Automatic Migration` or `Feature Selector: Immich Photos`) so the active working context stays visible while scrolling elsewhere in the page.
  - Refined `Automatic Migration` `DEBUG` performance logs so the real destination upload time is now emitted separately as `automatic_migration.asset.upload`, while the end-to-end asset lifecycle is reported as `automatic_migration.asset.pipeline`. This makes it much easier to distinguish backend upload cost from queue wait, album-association batching, and post-upload cleanup/finalization delays.
  - Restricted live `cProfile` dumps during `Automatic Migration` to `VERBOSE` mode only, and preserved the effective runtime log level inside the migration pipeline so `DEBUG` diagnostics such as `[PERF]` pull/push traces remain visible when `--log-level debug` is used.
  - Refined reusable/similar album consolidation so semantic split suffixes such as `Día 1`, `Day 2`, `Jour 3`, `Parte 4`, `Part 5`, `Session 6`, and their common variants in major languages (with or without spaces, dashes, or underscores before the suffix) are normalized back to the shared base album name during similar-album grouping, while post-reassignment confirmation now refreshes keeper-album membership each time before deciding whether a redundant album can be removed.
  - Reworked `Consolidate Albums Names` family discovery into a shared cloud utility used by `Google Photos`, `Synology Photos`, `Immich Photos`, and `NextCloud Photos`. The scan now groups albums by reusable-name family in a single pass instead of rebuilding the full family plan for every album, which reduces duplicate work on large libraries and keeps the preview/keeper-selection logic consistent across all cloud targets.
  - Hardened `Automatic Migration` album-association confirmation for targets such as `Immich` and `Synology`. After associating a batch, PhotoMigrator now re-reads the destination album membership and, when needed, performs a short delayed second refresh before warning and scheduling a delayed retry, avoiding false negatives when the target actually associated the asset but exposes the new membership with a small delay.
  - Reworked `Automatic Migration` album association into a hybrid flow. When the destination upload immediately returns a reusable target asset id, PhotoMigrator now associates that asset to its destination album right away inside the push worker so an interrupted migration still leaves most already-uploaded assets attached to their album. Only the expensive duplicate-id resolution path and the assets that still do not have a reusable destination id are deferred for later recovery/finalization.
  - Deferred only the unresolved portion of `Automatic Migration` album association until the source album has finished pulling by default. Album-bound uploads that already have a reusable destination id are associated immediately during the hot push path, while duplicate-heavy or unresolved assets are accumulated and resolved once the puller marks that source album as complete. This keeps interruption safety for already-uploaded assets while still removing the expensive duplicate-id lookup work from the main hot path.
  - Disabled automatic `Automatic Migration` push retries and album-association verification retries by default. Failed uploads are now treated as single-attempt failures unless the user explicitly re-enables retries, which keeps the hot path free of delayed re-enqueues and leaves failed files in the `Automatic_Migration_Push_Failed_*` temp folder for manual inspection or a later rerun.
  - Added automatic multi-worker album association with per-destination-album locking for the new `Automatic Migration` album-association stage, together with target-specific auto-tuned batching/flush behavior.
  - Split `Automatic Migration` retries into two separate behaviors: real upload failures still use the normal delayed push-retry pipeline, while unconfirmed album associations now use short verification retries without being counted as upload retry attempts. This avoids misleading `attempt 1/3` push retries for duplicate-resolved assets whose upload already succeeded but whose album membership was not yet confirmed by the target.
  - Hardened `Automatic Migration` album association recovery for `Immich` targets when `POST /api/albums/{id}/assets` returns ambiguous `400`/`500` responses. Before warning that album membership was not confirmed, PhotoMigrator now refreshes the destination album membership, retries unresolved assets individually, and performs one last membership refresh so assets that were actually associated by Immich are confirmed instead of being left as false-negative warnings or unnecessary follow-up retries.
  - Reduced the default `Immich` album-association batch size and now use API-confirmed per-asset add-to-album results before forcing a full destination album re-list, which lowers queue stalls and avoids unnecessary full membership refreshes on large duplicate-heavy migrations.
  - Prioritized `Automatic Migration` push scheduling so photo/live-photo uploads are drained ahead of regular video uploads by default. This does not change the raw network/server upload speed, but it reduces artificial queue buildup from long-running video uploads monopolizing push workers while faster photo uploads are waiting.
  - Added explicit `Album Finalize Waiting` progress diagnostics during `Automatic Migration` whenever an album cannot yet be counted as `Album Pushed` because it is still active, still has pending local files, or is waiting on duplicate-resolution/association cleanup. This makes stalled album progress visible in logs instead of failing silently while the album is still legitimately incomplete.
  - Reduced the default `Automatic Migration` album-association verification retry delays from `2s/10s/30s` to `2s/5s/10s`. These retries are only used to re-check delayed album membership confirmation after a successful upload or duplicate resolution, while real push-failure retries still keep their longer independent delay policy.
  - Reworked cloud `Automatic Migration` album handling across `Immich`, `Synology`, `Google Photos`, and the other cloud targets so the hot upload path now creates/reuses the exact working album first, immediately associates assets whose upload already returned a reusable destination asset id, and defers only the expensive duplicate-id resolution plus final canonical/similar-album consolidation to album-finalization time. Duplicate uploads rejected without a returned destination id are now kept in a per-album pending-resolution list and are resolved only once the source album finishes, which removes per-asset remote duplicate lookups from the main upload path while preserving correct album membership before the temporary album folder is cleaned up.
  - Extended the `Automatic Migration` final summary with album-reuse stats (`Consolidated Albums`, `Canonicalized Albums`) and now auto-runs target `remove_empty_albums()` at the end when the destination client supports it.
  - Reduced the Web Interface `Execution Output` refresh interval to `250 ms`, so live job output appears closer to real time while preserving the current structured-dashboard and compact-log pipeline.
  - Formalized and expanded the shared photo-client public contract used by cross-backend features such as `Automatic Migration` and the other cloud/local modules. A new base client contract now defines the common polymorphic operations and broader shared API surface, including album creation/listing, album asset listing, add-to-album, push/pull operations, upload/download workflows, album-maintenance actions, and common helpers such as `album_exists`, `get_album_assets_count`, `get_album_assets_size`, and `get_assets_by_filters`. The concrete `Local Folder`, `Synology Photos`, `Immich Photos`, `NextCloud Photos`, and `Google Photos` clients were updated to expose homogeneous public method names and argument names across operations such as `push_albums`, `push_no_albums`, `push_all`, `pull_albums`, `pull_no_albums`, `pull_all`, `remove_all_albums`, `remove_empty_albums`, `remove_duplicates_albums`, `merge_duplicates_albums`, and `remove_all_assets`. Optional context parameters that only matter for specific backends (for example Synology album context) are now accepted consistently as no-ops by the other clients where applicable, and the contract-signature test was extended to catch future interface drift automatically before it becomes a runtime failure.
  - Extended `Automatic Migration` album-completion logging so each `Album Pushed` line now includes a per-album asset summary with `Total Assets`, `Pushed`, and `Duplicates`, plus `Failed` when applicable. These counters are accumulated from the real migration events per source album, so long-running runs now expose the final per-album outcome directly in the log without having to infer it from scattered asset-level lines.
  - Optimized the Web Interface live polling path for very low refresh intervals. Job polling now runs as a chained single in-flight loop instead of `setInterval`, so the browser never overlaps multiple `/api/jobs/{id}` requests when a previous poll is still being processed. The polling endpoint also supports a compact response path and now exposes an `output_version` counter, allowing the frontend to skip log repaints and dashboard refreshes when neither the compact log buffer nor the structured dashboard snapshot changed. This reduces unnecessary backend recomposition, JSON serialization, and frontend render work during progress-heavy runs and avoids the severe execution slowdown previously observed when aggressively lowering the poll interval to `25-50 ms`.
  - Simplified the Web Interface live log pipeline to the minimum processing model. The backend now keeps only complete visible log lines plus in-place progress-line replacement on `\\r`, strips embedded `__PHOTOMIGRATOR_DASHBOARD__` snapshots from the visible stream, and avoids the previous extra log repairs such as orphan level-prefix reconstruction, GPTH-specific prefix stitching, embedded progress/log line splitting, and paginated log-history APIs. The frontend now just polls the compact `output_lines`, colors each complete line by type, preserves manual selection freeze, and applies the existing auto-scroll / near-bottom behavior without virtualized history windows or additional client-side progress reinterpretation.
  - Added a cheap fast-path to the Web Interface live log parser so the expensive GPTH/progress repair heuristics now run only for lines that actually look like progress bars or progress-followup records. Regular log lines now bypass the progress-specific splitting, prefix inheritance, and progress-key reconstruction logic, reducing backend overhead during high-frequency `Automatic Migration` polling while preserving the corrected GPTH bar rendering.
  - Enhanced the Web Interface live log progress detection so indeterminate tqdm-style counters such as `Organizing files with year/month structure ... 128557 files [02:01, 1346.55 files/s]` are now recognized as progress updates and compacted in place instead of flooding the visible log with one line per refresh during long post-processing phases.
  - Refined the `Automatic Migration` live dashboard `Estimated Time` calculation so it now starts from the real beginning of the asset transfer phase (pull/push workers launch) instead of the earlier module/job start. This prevents long Google Takeout or other preprocessing stages from inflating the ETA by hours before the first assets actually begin to move.
  - Extended the defensive Google Takeout post-GPTH special-folder reclassification to normal GPTH `--input/--output` runs as well. PhotoMigrator now also scans the final processed output of standard GPTH executions and moves localized `Archive` / `Trash` / `Locked Folder` variants such as `Carpeta privada` out of `Albums` into `Special Folders` before publishing the processed library.
  - Added a lightweight hot cleanup pass for `Automatic Migration --move-assets true` local sources so once an album is truly finalized as `Album Pushed`, PhotoMigrator now also tries to remove the corresponding emptied source album folder immediately instead of waiting only for the final cleanup pass. The final local-source cleanup was also hardened to treat runtime housekeeping markers such as `.active` and `*.lock` as ignorable emptiness artifacts together with the existing excluded Synology/system files.
  - Reworked the Web Interface live log transport and renderer to use incremental output operations instead of full log snapshots on every poll. The backend now keeps a lightweight append/replace operation stream for completed visible lines, while the frontend applies only the delta to persistent DOM nodes and groups historical lines into content-visibility blocks. This preserves the current progress-bar rendering, copy/selection behavior, and immediate scrolling across all already painted lines, but avoids the previous O(total visible log) HTML rebuild on each refresh as long-running jobs grow their output.
  - Refined `Automatic Migration` live dashboards across the Web Interface and terminal dashboard so queue/backlog metrics are now split into three explicit bars: `Assets in Queue` (real push queue only), `Album Assoc Queue`, and `Delayed Retries`. The dashboard also now shows `Blocked Assets` immediately below `Blocked Albums`, renames `Invalid Files` to `Unknown Files`, moves the elapsed/remaining timers into the Pull panel with a visual separator, adds `Delayed Recovered` / `Delayed Failed` counters to the Push panel, and counts real iCloud metadata CSV inputs as `Total Metadata` while excluding generic generated reports such as `Photo Details.csv` mismatches, `Unresolved_Assets.csv`, or `No_Date_Assets.csv`.
  - Reworked `Automatic Migration` physical asset accounting and post-upload cleanup semantics. Pull/push/duplicate/failure counters now stay aligned to the real physical files represented by each staged upload bundle, including `Immich` live-photo pairs where one queued photo item also carries a companion video. In addition, assets whose upload succeeded but whose destination album association still could not be confirmed are no longer deleted from the temp staging area: PhotoMigrator now removes them from the source when `--move-assets true` is enabled, preserves the staged files under `Automatic_Migration_Push_Failed_*/Album Association Failed/<AlbumName>/`, and keeps `Album Assoc Unconfirmed` as an informational follow-up counter instead of folding it into the hard `Push Failed Assets` total.
  - Extended the shared valid-photo extension handling so `.webp` files (for example `IMG_20210805_112248_719.webp`) are now treated as supported photo/image assets consistently across the local-folder and Synology-backed workflows instead of being classified as unknown/unsupported files.
  - Refined the Web Interface tab theming so the main workspace tabs (`Features`, `Output`, `Configuration`) and the secondary `Configuration` tabs now use stronger theme-aware color palettes, making the active workspace and configuration context more visually prominent while preserving the attached natural-tab layout.
  - Refined the Web Interface execution controls so the `Features` and `Output` workspaces now use compact, uniform-width `Run` / `Stop` action buttons, dangerous-run confirmations use the same shorter wording, and starting a job from `Features` now switches automatically to the `Output` workspace as soon as execution begins.
  - Improved `Immich Photos` long-running module feedback so operations that spend noticeable time listing albums, gathering album assets, collecting assets without albums, or scanning local upload trees now emit an explicit progress message before the first `tqdm` bar appears. This removes the silent waiting period previously seen in modules such as `Remove Empty Albums`, `Remove Duplicate Albums`, `Remove All Albums`, `Pull Albums`, `Pull All`, and the upload flows, without adding extra parsing load to the Web Interface log pipeline.
  - Refined the Web Interface `Command Preview` so it now displays a compact `PhotoMigrator ...` command instead of the full Python interpreter and `.py` launcher path, and aligned the real execution order with that same preview ordering. Context-defining arguments such as `--client`, `--account-id`, `--source`, `--target`, and the main action flag are now shown and executed first, while secondary album-normalization flags such as `--consolidate-similar-albums` and `--prefer-canonical-album-names` are pushed near the end just before `--configuration-file`.
  - Refined the Web Interface cloud `User Description` cards so the `Supported modules` list is now displayed as a cleaner two-column layout without inline `|` separators, making the available cloud actions easier to scan at a glance.
  - Updated the Web Interface `Output Panel` header so it now reflects the currently selected feature and, when applicable, the selected module as well (for example: `Output Panel: Immich Photos - Upload All`).
  - Web Interface: while a job is running, the `Output Panel` now stays bound to the feature/module that is actually executing instead of following later selections made in the `Features` tab. This also keeps the `Output Panel` title aligned with the active job context until the execution finishes.
  - Reworked `Automatic Migration` staging into `Automatic_Migration_<TIMESTAMP>/Push_Queue/`. Local-folder sources now preserve their original relative directory hierarchy while assets are copied there, or moved there immediately when `--move-assets=true`, instead of using the old `Automatic_Migration_Push_Failed_*` working folder.
  - Added persistent `Automatic Migration` queue folders: failed uploads move from `Push_Queue/` to `Push_Delayed_Queue/`, are retried three times at five-minute intervals, and move to `Push_Failed/` after the final unsuccessful retry. Push workers now prioritize timer-ready delayed retries ahead of new `Push_Queue/` work. Duplicate uploads without a reusable destination asset ID are stored in `Album_Association_Queue/` and processed by dedicated album-association workers.
  - Fixed `Album Assoc Queue` dashboard depth to report the physical files retained in `Album_Association_Queue/`, including assets already held by an album-association worker for batching, instead of showing only the in-memory queue entries waiting to be claimed.
  - Moved duplicate uploads that require remote target-id resolution into `Album_Association_Queue/` as well. The dedicated album-association workers now resolve the existing destination asset first and then associate it to the album, so no album-bound duplicate work remains hidden in a separate in-memory pending set.
  - Restored immediate album association for uploads and duplicates that already have a reusable destination asset id. `Album_Association_Queue/` is reserved exclusively for duplicate assets that first require remote target-id resolution.
  - Updated all `Automatic Migration` live dashboards (Web, CLI, TUI, and GUI) so `Delayed Retries Queue` and `Album Assoc Queue` use the total number of migration assets as their progress maximum. `Album Assoc Queue` now appears directly below `Delayed Retries Queue`.
  - Grouped each Push dashboard outcome summary directly below its corresponding Assets, Photos, Videos, or Albums progress bar as `Total <type> (New / Duplicates / Failed)`, widened Info Panel labels to keep queue names on one line, and renamed the backlog indicator to `Delayed Retries Queue`.
  - Changed the `Delayed Retries Queue` and `Album Assoc Queue` progress maxima to the physical assets admitted to each queue during the migration, rather than the full migration asset count. Repeated retries of the same asset do not inflate either maximum.
  - Reworked `Automatic Migration` Push dashboards across Web, CLI, TUI, and GUI. The `Pushed Assets`, `Pushed Photos`, and `Pushed Videos` bars now track physical assets once a pusher worker has removed them from `Push_Queue`, while `New`, `Duplicates`, and final `Failed` outcomes are displayed separately for each media type. Added cumulative `Delayed Retries` and `Delayed Recovered` counters; album-association follow-up failures remain excluded from hard push failures.
  - Updated `Automatic Migration` Pull dashboards across Web, CLI, TUI, and GUI so each indented `Failed Assets`, `Failed Photos`, `Failed Videos`, and `Failed Albums` counter is displayed directly below its matching progress bar.
  - Added an indented `🔢` counter marker to each `New / Duplicates / Failed` Push outcome summary across Web, CLI, TUI, and GUI.
  - Moved the Rich terminal `Automatic Migration` Live Dashboard renderer out of `AutomaticMigration.py` into `LiveDashboard.py`, keeping the migration orchestration and web-dashboard snapshots isolated from terminal presentation code.
  - Expanded the startup log for every feature with the selected feature and its required flags before `Global Settings`, followed by `Optional Flags Used` and `Optional Flags Default` sections. The latter reports effective defaults for optional flags applicable to the selected feature that were not supplied by the caller. Modular cloud and Other Features runs now also identify their selected module. Configurable flag values were removed from `Global Settings`, leaving only hardcoded or runtime-derived settings there.
  - Reduced the Rich `Automatic Migration` Live Dashboard Info, Pull, and Push panel band by one terminal row, giving the live log panel more vertical space.
  - Improved the Web Interface mobile layout for Google Takeout and iCloud Takeout by resetting their desktop card placement to a single column, and made cloud `Supported modules` lists render in one column on narrow screens.
  - Automatic Migration now prunes empty relative-path folders immediately after assets move between persistent staging queues or are deleted after successful processing, while retaining the queue roots themselves.
  - Corrected the initial `Delayed Retries Queue` and `Album Assoc Queue` dashboard totals so they display `0/0` before any asset enters either queue instead of showing a synthetic total of `1`.
  - Reworked Local Folder symlink staging for Automatic Migration: album symlinks now materialize their target content under the album-relative queue path. With `--move-assets`, PhotoMigrator copies that content, removes only the original symlink, and never moves its shared physical target away from other album links.
  - Fixed Album Association Queue worker coordination: album-complete markers are now shared across all association workers, so assets claimed by a different worker no longer remain pending until the end of the migration. Immich HTTP-level album-association failures now skip wasteful immediate per-asset verification calls, retry as a batch, and log the response status/body for diagnosis.
  - Added `Estimated End` to every Automatic Migration live dashboard: it appears after `Remaining Time` in the Web dashboard header and beneath it in the Pull panel across Rich CLI, TUI, and GUI dashboards.
  - Fixed Automatic Migration album progress accounting: direct Album Association Queue admissions now increment their physical-file total, and albums whose assets finish as New, Duplicate, or final Failed are reconciled into `Pushed Albums` once the pipeline drains.
  - Corrected Album Association Queue outcome accounting: `Album Assoc Retry Scheduled` now counts the physical files admitted to `Album_Association_Queue/` once rather than every retry attempt, and `Album Assoc Retry Recovered` only counts files whose association is actually confirmed after a retry.
  - Made Automatic Migration Pull and Push dashboard maxima consistently physical-file based. Live Photo companions now expand the effective media total instead of overflowing progress bars; Push uses successfully pulled physical files as its maximum, excluding Pull failures.
  - Standardized Automatic Migration file counters on physical files across retry, recovery, final retry failure, album-association recovery, and album-association unconfirmed outcomes. A Live Photo photo/video pair now contributes two files consistently to every applicable asset counter and queue metric.
  - Fixed Automatic Migration Album Association Queue recovery: destination-album lookup or creation failures are no longer cached as empty IDs and now retry with an explicit reason. Duplicates reported by Immich without an immediate remote ID are counted immediately as duplicates and retried in `Album_Association_Queue/` instead of being moved to `Push_Failed/`; unresolved terminal cases are reported as album-association failures. Remote duplicate lookup now indexes the destination library by filename to avoid repeatedly scanning every asset.
  - Added Automatic Migration Pull failure auditing under `Pull_Failed/`: every failed pull is written to `pull_failed_assets.csv` with its filename, album, source/staging paths, preserved-file path, and reason. Any partial staged file is copied there with its relative hierarchy. The terminal cleanup now also removes orphaned files left in `Push_Queue/` only after every push worker has stopped.
  - Raised the Automatic Migration delayed-retry eligibility limit from 50 MB to 200 MB, so files up to 200 MB can enter `Push_Delayed_Queue/` and use the configured retry policy instead of moving directly to `Push_Failed/`.
  - Reduced Automatic Migration end-of-run log noise by suppressing only the final reconciliation `Album Pushed` lines. Albums now re-evaluate their normal finalization as soon as pulling completes, so their regular `Album Pushed` summary is emitted during the migration instead of being deferred to the final reconciliation. When album consolidation or canonical naming is enabled, each completed consolidation/canonicalization also logs its source and destination names together with the original and final destination asset counts.
  - Fixed Automatic Migration album-finalization and Album Assoc Queue reporting for local folders: albums whose drained staging directory was already pruned can now emit their normal `Album Pushed` summary during the migration, and queue depth ignores Synology `@eaDir` / `__MACOSX` artifacts. Immich album-association retries now invalidate and re-resolve a destination ID that returns `Album not found`, with an explicit protected-folder diagnostic for names such as `Carpeta privada`.
  - Clarified Immich Automatic Migration album-association warnings and terminal failures: they now identify assets in Immich `Locked Folder` without an unlocked API session as a common possible cause when association cannot be confirmed.
  - Refined Automatic Migration album association failure handling: `Album_Association_Queue/` now receives only duplicate assets whose push did not return a reusable destination ID. Its workers perform the initial remote-ID lookup plus one retry by default; failures with an already known target ID remain in the hot path and move directly to `Album_Association_Failed/`. Repeated retry diagnostics are reduced to `DEBUG`, and terminal queue assets preserve their relative hierarchy in `Album_Association_Failed/`.
  - Corrected the `Album Assoc Queue` dashboard total to count only physical files actually admitted to `Album_Association_Queue/`; known-ID hot-path association failures are no longer represented as queued assets.
  - Renamed the Automatic Migration physical delayed upload-retry folder from `Delayed_Queue/` to `Push_Delayed_Queue/`.
  - Added an `🚩 Album Assoc Failed` terminal-outcome row to the Push panel in the Web and Rich Automatic Migration live dashboards.

#### 🐛 Bug fixes:
  - Fixed the cloud `Automatic Migration` regression introduced after `v4.0.0` where duplicate-heavy album uploads could become dramatically slower because the migration pipeline tried to resolve reusable destination asset ids and apply album-family consolidation in the hot path for every asset. Known-id assets are now still associated during the normal migration flow, while duplicate uploads without an immediate reusable id are postponed to a final per-album resolution pass instead of forcing repeated remote lookups during each upload.
  - Fixed the `Synology Photos` shared-album/shared-space follow-up regression originally surfaced from issue `#1159` and later tracked as issue `#1173`. Shared album requests are now scoped by the current `album_id` instead of listing against only the shared passphrase context, which prevents runs from reusing the same unrelated asset across many albums and restores proper asset discovery for shared-space album migrations. Also stopped treating `--filter-by-type all` as an active filter, so `Automatic Migration` analysis no longer accidentally falls back into personal-space-only Synology filtering when the user explicitly wants all asset types. In addition, Synology album classification now distinguishes albums merely shared by their owner from true `shared with me` albums, so owner-shared albums keep using the normal owned-album asset listing flow and are no longer incorrectly blocked just because their invitees have `view` permissions.
  - Fixed an `Automatic Migration` regression introduced by the new Synology blocked-shared-album guard. Non-Synology sources such as `Local Folder` and processed `Google Takeout` no longer call Synology-only helpers during album analysis/pull, so local migrations no longer abort with `AttributeError: 'ClassLocalFolder' object has no attribute 'is_blocked_shared_album'`.
  - Fixed an `Automatic Migration` race in the local/Takeout staging pipeline where a duplicate-detected asset could delete a staged file or live-photo companion that had already been dequeued by another push worker but was still being uploaded. Staged files are now treated as reserved both while queued and while actively in-flight, preventing `File not found: .../Album/<name>.MP4` failures caused by premature cleanup during duplicate handling.
  - Fixed another `Automatic Migration` local/Takeout live-photo staging bug for `Immich` targets. When a photo was enqueued together with a same-stem video companion for `push_live_photo()`, that companion path could still be discovered later as a standalone video asset, copied back into the temp album folder, and only fail much later with `File not found` or leave orphan `.MP4` files after the photo workflow had already consumed and cleaned it. Live-photo companion paths are now reserved as consumed as soon as the paired photo is queued, so they are no longer re-enqueued later as independent video uploads.
  - Fixed an additional `Automatic Migration` `Immich` live-photo staging edge case where a same-stem companion video could already be sitting in the push queue as a standalone asset before the paired photo later claimed it for `push_live_photo()`. Those consumed companion paths are now explicitly marked and skipped both while enqueuing and again inside the push worker, so they no longer survive long enough to fail later with `File not found: .../<name>.MP4` after the paired photo workflow has already consumed and cleaned them.
  - Fixed Synology Photos album-context handling for `Shared Space`, true `shared with me` albums, and regular owned albums. PhotoMigrator now documents and follows the browser-observed Synology API behavior more closely: albums surfaced under `normal_share_with_me` are no longer blindly treated as passphrase-based shared albums, Shared Space albums owned by the current user prefer the browser-style `SYNO.Foto.Browse.Item` `version=7` listing flow with `album_id`, and album downloads now also include `album_id` context with passphrase fallback only for true shared-with-me cases. This resolves the remaining `#1173` gap where Shared Space albums were detected but their assets could not be listed/downloaded correctly. (Issue #1173).
  - Fixed `Synology Photos` owner-id learning for `Shared Space` albums so `normal_share_with_me` albums can still be reclassified as owned even when no personal albums were seen first. (Issue #1173).
  - Fixed Synology album asset listing fallbacks so `Automatic Migration` and `Download Albums` keep trying alternate item-list variants when album counts are missing instead of treating the first empty success response as a truly empty album. (Issue #1173).
  - Fixed the Web Interface log stream so inline `__PHOTOMIGRATOR_DASHBOARD__` snapshots no longer leak into progress lines, create blank lines, or leave stray `INFO :` fragments in `Execution Output`.
  - Fixed the Web Interface `Execution Output` panel so manual text selection is preserved while `Auto Scroll` is disabled even if a live progress bar keeps updating, and added `Ctrl+C` / `Cmd+C` copying for the currently selected log text.
  - Fixed local-source cleanup so folders containing only excluded Synology artifacts such as `@eaDir`, `@Recycle`, `.DS_Store`, or thumbnail files are now treated as empty and can be removed both during album completion and in the final cleanup pass.
  - Fixed another `Synology Photos` / `Automatic Migration` follow-up around issue `#1173`. `--filter-by-type all` is now treated consistently as “no active filter” inside the migration pipeline as well, so Synology Shared Space runs no longer fall into the filtered album-validation path during analysis or pulling. In addition, Synology shared-album classification now also reads owner/permission details when `sharing_info` is returned at the top level of the album payload instead of only under `additional`, which improves reclassification of `normal_share_with_me` albums that are actually owned by the current user and keeps them on the correct Shared Space listing/download flow. (Issue #1173).
  - Fixed the Web Interface `Execution Output` auto-scroll behavior so scrolling upward now disables live tail following automatically, and returning near the latest visible lines re-enables `Auto Scroll` automatically without requiring a manual toggle.
  - Fixed the Web Interface module-launch flow so starting any new execution now re-enables `Auto Scroll` automatically before the fresh job output begins, preventing a previous manual scroll-up state from leaving the new run stuck without live tail following.
  - Fixed an `Automatic Migration` client-interface regression where Synology-specific album context arguments such as `album_scope`, `album_expected_count`, and `album_id` could leak into generic source-client calls during album pulling, breaking non-Synology sources like `Local Folder` with `unexpected keyword argument` errors. The migration pipeline now only sends those extra kwargs when the active source client is actually `Synology Photos`, and the public album/pull method signatures across `Local Folder`, `Immich Photos`, `NextCloud Photos`, and `Google Photos` were also aligned to tolerate the shared optional album-context parameters as no-ops for stronger cross-feature compatibility.
  - Fixed a regression in `Automatic Migration` introduced while adding per-album `Album Pushed` summaries. The new album-stat counters were originally wired through local helper closures, which could fail with `NameError` inside threaded `puller_worker` / `pusher_worker` execution in some runtime environments. Album summary counters are now updated through module-level helpers with explicit shared state, so threaded migrations no longer abort with `_ensure_album_stats` / `_increment_album_stat` lookup failures while building the final per-album summary line.
  - Fixed another `Synology Photos` `Shared Space` follow-up around issue `#1173` by aligning the affected album-detail, album-list, item-list, count, and download requests with the browser-observed `POST` transport used by Synology Photos, while keeping `GET` as a compatibility fallback. Shared Space runtime album-detail hydration now also requests the same extra fields observed in the browser (`flex_section` and `provider_count` in addition to `sharing_info` and `thumbnail`), which helps keep owner-shared album classification and item discovery aligned with the real web client. (Issue #1173).
  - Fixed `Automatic Migration` similar-album consolidation confirmation for targets such as `Immich`. The consolidation path now reuses the same robust album-association verification flow already used by normal asset pushes, including confirmed-id tracking and follow-up membership refreshes, instead of relying on a single immediate album reread. This prevents false `Album Consolidation Partial` results such as repeated `N-1 / N confirmed` cases where the keeper album had actually accepted the missing asset but the simplified consolidation check undercounted it.
  - Fixed another `Synology Photos` `Shared Space` follow-up around issue `#1173` where album-scoped item listings could still be emptied after retrieval by being revalidated against the global `get_assets_by_filters()` result set even when no explicit filters were active. Synology album listings now keep the assets returned by the album API unless real user filters must be applied, which avoids discarding valid `Shared Space` assets just because the global library listing exposes a different namespace than the album context. Also fixed Synology user-id normalization so `owner_user_id=0` is preserved instead of being dropped, which keeps `Shared Space` owner metadata available for diagnostics and future classification logic.
  - Fixed the Web Interface `Execution Output` panel scroll handling after the incremental log renderer refactor. Horizontal scroll is now preserved while new log deltas arrive, reaching the bottom manually with the mouse wheel no longer forces an unexpected snap/repaint cycle, and re-enabling `Auto Scroll` now jumps reliably to the latest visible log lines instead of rebuilding a full snapshot unnecessarily.
  - Fixed an `Automatic Migration` regression in the `Album Association Failed` fallback cleanup path. Assets whose upload had already succeeded but whose destination album membership could not be confirmed were calling `_finalize_album_association_failed_asset(...)` with the newer shared finalization kwargs (`asset_type`, `count_push_stats`), while that helper still exposed the older narrower signature. The fallback cleanup path is now aligned to the new signature and additionally guarded so any internal cleanup/move error is logged as an album-association cleanup issue instead of incorrectly degrading an already uploaded asset to `Push Failed`. This prevents false `Pushed + Failed` double-counting for cases such as video assets inside localized special albums like `Carpeta privada`.
  - Fixed `Local Folder` initial file-type analysis so unsupported uppercase `.MP` files are now classified consistently as `unknown` / non-supported assets instead of being filtered inconsistently by suffix-only logic, and auxiliary JSON files such as `progress.json` are no longer counted as real metadata assets during the initial Takeout/local analysis.
  - Fixed `Automatic Migration` local-source asset selection so files already classified as `unknown` / unsupported (for example `progress.json` or unsupported `.MP` files) are no longer returned by the generic `type='all'` no-album scan and therefore are no longer pulled, staged, or pushed as if they were migrable assets. Also fixed the `Local Folder` no-album asset cache so results are now isolated per requested type instead of leaking a previous `all` query into later `unsupported` / `metadata` lookups.
  - Fixed the Web Interface `Import Config` flow so importing a `.ini/.cfg/.txt` configuration now preserves the original path values declared inside the imported file instead of rewriting them immediately to the active web user's allowed roots during import. Runtime execution still re-sanitizes effective path arguments per user as before.
  - Fixed `Synology Photos` owned-album listing for modules such as `Remove Empty Albums` by routing the `SYNO.Foto.Browse.NormalAlbum -> list` call through the same resilient `entry.cgi` transport fallback used by the newer Synology shared-space code paths, instead of relying only on the older direct `GET` request. Also fixed the associated error log so failed album-list responses now include the real Synology payload for diagnosis.
  - Fixed the Web Interface cloud-feature state handling so `account-id` is now persisted independently for each cloud module (`Google Photos`, `Synology Photos`, `Immich Photos`, `NextCloud Photos`) instead of being shared globally across all of them. Changing the selected account in one cloud feature no longer overwrites the account used by the others.
  - Refined the Web Interface `Command Preview` and matching execution command formatting so the visible command now uses a compact `PhotoMigrator ...` prefix instead of the full Python interpreter and `.py` launcher path, orders context-defining arguments first (`--client`, `--account-id`, `--source`, `--target`, main action flags), moves secondary album-normalization flags such as `--consolidate-similar-albums` and `--prefer-canonical-album-names` near the end before `--configuration-file`, and renders single-value options in `--flag=value` form for better readability while keeping multi-value options space-separated.
  - Refined the Web Interface command ordering again so both `Command Preview` and the real execution command now follow the same argument order as the upper Web Interface panels instead of a separate manual priority list. This also guarantees that `--prefer-canonical-album-names` is emitted before `--consolidate-similar-albums` whenever both are present, matching the order shown in `General Arguments -> Execution`.
  - Added another `Synology Photos` `Shared Space` diagnostic and recovery follow-up around issue `#1173` for the remaining `No Albums` path. The global Synology asset listing used to derive assets without albums now emits targeted `DEBUG` summaries per request variant and after the final merge, including counts plus sampled `id` / `filename` / `owner_user_id` / `provider_user_id` values so mismatches between personal-space and `Shared Space` universes can be inspected from a normal debug log. In addition, the global asset scan now tries an extra browser-style `SYNO.Foto.Browse.Item` `version=7` / `method=list` variant and merges successful results by asset `id`, while the downstream `No Albums` difference now also uses asset `id` instead of `filename` to avoid false matches when different assets share the same file name. (Issue #1173).
  - Fixed the extracted `Automatic Migration` Rich Live Dashboard failing on its first render with `NameError: _compute_dashboard_estimated_time`. The dashboard timing helpers now live with the terminal renderer and remain shared with the web snapshot path.
  - Fixed the GUI `Stop` button being disabled for `Automatic Migration` runs launched in an external Live Dashboard terminal. The GUI now tracks the external migration PID and sends the stop signal to that process rather than only tracking the terminal launcher.
  - Fixed `Automatic Migration` Live Dashboard startup after its renderer extraction. Its estimated-time calculation, UTC timezone dependency, background progress parser, and visible-progress-row selection now reside in `LiveDashboard.py`, preventing `NameError` failures while rendering or consuming `tqdm` progress lines.
  - Fixed the Rich `Automatic Migration` Live Dashboard layout so the Info Panel has enough height to render `Assets in Queue`, `Delayed Retries Queue`, and `Album Assoc Queue` together. Pull failure rows and Push `🔢 Total (New / Duplicates / Failed)` summaries now remain on one line below their matching bars.
  - Aligned the Rich `Automatic Migration` Live Dashboard panels with the web layout: `Blocked Albums` and `Blocked Assets` now remain only in Info, the queue label uses a consistent-width timer emoji, and full-width separators now precede Info queues, Pull timing, and Push delayed-retry counters.
  - Fixed the macOS GUI external-terminal launcher for `Automatic Migration` Live Dashboard runs. PhotoMigrator now stays in the foreground terminal job while its PID is still reported to the GUI for `Stop`, preventing `zsh` `suspended (tty output)` / `terminated` job-control messages from shifting the final Rich dashboard.
  - Refined Rich `Automatic Migration` Live Dashboard panel alignment: the Push delayed-retry divider now has matching vertical spacing, both delayed counters use the same-width emoji, and the shared panel height was reduced after the layout fit was corrected.
  - Prevented Terminal.app `zsh` job-control suspension of the external Rich `Automatic Migration` Live Dashboard by disabling shell job monitoring before the foreground launch. Rich panel separators now also size themselves to their current panel width instead of overflowing fixed-length divider strings.
  - Fixed the Rich `Automatic Migration` Live Dashboard finalization and layout: GUI-launched dashboards now report migration completion back to the GUI before waiting for `Ctrl+C`, so final statistics remain visible while the GUI `Run` / `Stop` controls reset correctly. The completion prompt is shown inside the dashboard log panel, and the Info, Pull, and Push panel dividers are now rendered as full-width Rich rules instead of split table-cell fragments.
  - Fixed a Python syntax error in the POSIX external Live Dashboard launcher caused by escaped quotes inside an `f-string` expression.

#### 📚 Documentation:
  - Updated documentation with all changes.
  - Expanded the `Automatic Migration` documentation to explain the current physical-file counter semantics, the meaning of each live dashboard counter, and how to interpret leftovers in `Automatic_Migration_Push_Failed_*`, especially the new `Album Association Failed/<AlbumName>` preservation path. Also updated the Web Interface documentation panels so `Automatic Migration` now lists `--one-time-password` under `Optional arguments`, and `Google Takeout` / `iCloud Takeout` now expose their feature documentation panel directly above the argument form.

---

## Release: v4.4.1
### Release Date: 2026-07-09
  
#### 🚨 Breaking Changes:

#### 🌟 New Features:
  - Added a local Web Interface launcher script at `src/PhotoMigrator_Web.py` so the FastAPI web UI can be started directly from source in IDEs such as PyCharm without Docker-specific setup. The launcher auto-creates its local workspace under `.web-dev` and injects development-safe defaults only when those environment variables are not already defined.

#### 🚀 Enhancements:
  - Improved `Google Takeout` post-process video XMP date normalization. The repair step now reports the total number of conflicting videos before starting, shows a live progress bar during the normalization, and reuses a persistent `ExifTool` session to reduce per-file process startup overhead.
  - Updated GPTH to v6.1.9 which includes an important Bug Fix.
  - Optimized `Automatic Migration` album association for duplicate-resolved uploads. Destination album membership is now cached per resolved target album so assets that already belong to the final destination album are no longer re-added repeatedly, which significantly reduces redundant `add to album` calls on `Immich`/`Synology` when migrating processed `Google Takeout` or other album-heavy sources with many duplicates.

#### 🚀 GPTH Enhancements:
##### 🐛 GPTH Bug Fixes
  - Fixed Alnum's orphan assets association: When any album folder only contains .json metadata file but not the corresponding asset, now GPTH try to find the original asset into the ALL_PHOTOS/year folder. This issue happens because when one asset belongs to different albums, Google Takeout just copy the original asset into the Year folder and in every album it only put the associated .json metadata file. 
  - **Numbered orphan album sidecars now resolve to the correct duplicate** — When two same-named photos were in one album, Takeout numbers only the sidecar *filenames* (`pic.jpg.supplemental-metadata(1).json`) while the JSON `title` field keeps the plain original name for every copy. The issue #133 orphan-recovery lookup checked `title` first, so a "(1)" sidecar attached its album membership to the plain `pic.jpg` in the year folder instead of the `pic(1).jpg` it actually references. The lookup now derives the numbered name from the full-length `title` (which, unlike the sidecar filename, survives Takeout's 51-character truncation) and tries it before the plain name. Because the "(N)" numbering is per-directory — an album's `pic(1).jpg` and a year folder's `pic(1).jpg` can be different photos — a numbered match is only accepted when its year folder agrees with the sidecar's `photoTakenTime`; otherwise the lookup falls through to the plain name, and when the numbered twin exists nowhere the membership still falls back to the plain copy rather than being lost. Follow-up to issue #133.

#### 🐛 Bug fixes:
  - Fixed the Synology shared-album follow-up regression from issue `#1159`. Shared albums matched by filters now use the correct shared-album listing flow instead of the normal album endpoint.
  - Shared-album access resolution is now cached during `Automatic Migration`. This avoids redundant per-album API lookups on reruns and prevents the initial analysis step from slowing down badly.
  - Fixed `Google Takeout` `GPTH --fix` execution so PhotoMigrator now passes GPTH the direct parent folder of the album and asset subfolders, instead of mixing `--fix` with `--input/--output`.
  - After `GPTH --fix`, PhotoMigrator now relocates the generated `ALL_PHOTOS`, `Albums`, and `Special Folders` / `Special_Folders` trees into the configured output folder.
  - When `--google-keep-takeout-folder` is active, PhotoMigrator now creates a temporary working copy only if the current `--fix` input still points to the original Takeout tree.
  - If the source Takeout came from ZIP files and PhotoMigrator is already working on the intermediate unzipped staging folder, no extra clone is created because the original ZIP Takeout is already preserved.
  - The automatic `album-only` detection flow still forces `GPTH --fix` when no year folders exist but localized `Google Photos` plus album JSON sidecars and `archive_browser.html` are present.
  - Fixed the Web Interface `Command Preview` for `Google Takeout` processing flags `--google-remove-duplicates-files`, `--google-rename-albums-folders`, `--google-skip-extras-files`, `--google-keep-takeout-folder`, and the general flag `--no-log-file`. The backend preview path sanitizer was incorrectly treating those boolean flags as filesystem paths because of their names, so toggling them changed the checkbox state and preview request payload but did not update the rendered command.
  - Fixed `Google Takeout` `GPTH --fix` working-input remapping when `--google-keep-takeout-folder` is active. If PhotoMigrator had already cloned the Takeout earlier in the pipeline, the later `GPTH --fix` target resolution could still keep using stale detection paths from the original tree. The detected `container_path` / `matched_path` entries are now remapped to the cloned working root before selecting the folder passed to GPTH.
  - Restricted `Google Takeout` orphan album JSON recovery to Takeouts that actually contain year folders. Album-only Takeouts without `Photos from YYYY` / localized year folders no longer run the orphan-asset recovery step, because that recovery path depends on assets being materialized under the processed year-based library.
  - Preserved GPTH log files generated during `Google Takeout` `GPTH --fix` runs whenever GPTH writes into a working root that is later relocated into the final processed output folder. When PhotoMigrator moves `ALL_PHOTOS`, `Albums`, and the other fix-mode artifacts into the final output, it now also relocates the GPTH log, regardless of whether GPTH had been working on the original Takeout root or on a temporary cloned root.
  - Fixed the Web Interface log panel handling for GPTH progress bars. When a progress update reaches the frontend without a real newline before the next `INFO` / `WARNING` / `ERROR` / `[web-interface]` prefix, the renderer now inserts the missing break before collapsing and painting the log lines, and while that progress bar is still below `100%` it is kept as the last visible line so no later log entries are shown underneath it prematurely.
  - Fixed the Web Interface log panel so disabling `Auto Scroll` no longer freezes live log updates. The panel now keeps repainting incoming output while only suppressing the automatic jump to the bottom.
  - Reduced false `Automatic Migration` album-association warnings on `Immich` and `Synology`. When those targets report that an asset is already present in the destination album (`duplicate` / `already`), PhotoMigrator now treats that response as “already associated” instead of warning and scheduling an unnecessary retry.
  - Fixed `Synology` album reassignment during similar-album consolidation and canonical-name reuse. PhotoMigrator now sends `SYNO.Foto.Browse.NormalAlbum add_item` the album item list as real JSON and splits large reassignment batches into smaller requests, instead of passing a Python-style list string in one large query. This restores reassignment of assets from redundant albums such as `_`/`-` name variants into the chosen keeper album.
  - Reduced `Google Takeout` orphan album recovery log noise. Per-album `Album JSON Recovery` lines are now only emitted when an album actually recovers assets or leaves unresolved entries, and the message now includes the final album asset total after recovery.
  - `Automatic Migration` no longer schedules delayed push retries for large staged assets above `50 MB`. When one of those uploads fails, the asset now remains in `Automatic_Migration_Push_Failed_<TIMESTAMP>` without being re-enqueued, reducing repeated disk I/O on large video failures.
  - `Google Takeout` post-processing now defensively reclassifies localized special folders left behind by GPTH under `Albums` or the processed root, moving recognized `Archive`, `Trash`, and `Locked Folder` variants (for example `Archivo`, `Papelera`, and `Carpeta privada`) into `Special Folders` before the final processed output is published.
  - Fixed `Automatic Migration` album push progress accounting so `Album Pushed` is emitted during the migration as soon as the last staged asset of an album has been processed and removed from the temp folder, restoring correct live dashboard progress in the web UI.

#### 📚 Documentation:
  - Corrected the `Google Takeout` documentation so orphan album JSON recovery is documented in its real position as `Step 4.3` (right after `Copy/Move files to Output folder`) instead of under the later post-process section. The example step timeline was updated accordingly.
  - Corrected the `Google Takeout` step numbering to match the current code and logs: `Step 6.2` is now documented as `Repair Video XMP Dates`, `Step 6.3` as `Albums Moving`, the later post-process steps were renumbered through `6.8`, and the obsolete `Step 7.3` final-statistics entry was removed from the pipeline description.
  - Updated documentation with all changes.

---

## Release: v4.4.0
### Release Date: 2026-07-08
  
#### 🚨 Breaking Changes:

#### 🌟 New Features:

#### 🚀 Enhancements:
  - Restored full album compatibility with `Immich v3` by adapting album owner detection and album asset retrieval to the new API responses. Owned albums are now detected through `albumUsers` when `ownerId` is absent, and album contents now fall back to `POST /api/search/metadata` when `GET /api/albums/{id}` no longer returns inline `assets`, preventing silent migrations of empty albums on `Immich v3` while keeping backward compatibility with older Immich servers.
  - Expanded cloud `Rename Albums` pattern handling across supported services so album renames now accept plain-text replacements (for example `--` -> `-`) and simple wildcard forms such as `*--*`, `--*`, and `*--`, while keeping existing regular-expression replacements available for advanced cases.
  - Expanded cloud `Remove Albums` pattern handling across supported services so album deletion now accepts plain text, simple wildcard patterns, and regular expressions, and added a shared `--preview-album-actions` flag for `Rename Albums` and `Remove Albums` across CLI, GUI, TUI, and Web Interface to list the affected albums and request confirmation before applying the change.
  - Hardened cloud album uploads and `Automatic Migration` so duplicate-detected assets can still be attached to every destination album that references them instead of only the first one. `Immich` and `Synology` now first reuse cached asset IDs from the current run and, when needed, also resolve pre-existing destination assets remotely by metadata before album association. `Google Photos` now resolves the already-existing media item before album association and uses the same add-to-album flow for both fresh and duplicate uploads, and the migration worker now assigns any reusable destination asset ID to the source album regardless of whether the upload was new or deduplicated.
  - Added support for equivalent album-family reuse in cloud `Upload Albums`, cloud `Upload All`, and `Automatic Migration` across CLI, GUI, TUI, and Web Interface. By default PhotoMigrator still reuses only exact existing album names, but this capability now allows equivalent destination album families to be reused instead of creating duplicate albums, and is currently exposed through `--consolidate-similar-albums`.
  - Preserved `archive_browser.html` in processed `Google Takeout` outputs and added generation of a compact `automatic_migration_album_manifest.json` alongside it, so later `Automatic Migration` runs can reuse the exported album membership map even after GPTH removes the intermediate `Takeout` tree.
  - Extended `Automatic Migration` for managed `Local Folder` / processed `Google Takeout` sources so album asset enumeration can now fall back to the preserved `archive_browser` manifest when a processed album folder is missing some shortcut entries but the corresponding media still exists elsewhere in the processed library (typically under `ALL_PHOTOS`), regardless of whether the destination target is `Immich`, `Synology`, or another supported service.
  - Hardened `Immich` duplicate resolution for album-associated uploads whose processed canonical media was renamed with a numbered suffix such as `(1)`. Existing destination assets are now matched by both exact filename and normalized filename, reducing cases where duplicate responses without an embedded asset id could not be reassociated back to the source album.
  - Hardened `Synology` duplicate resolution for album-associated uploads whose processed canonical media was renamed with a numbered suffix such as `(1)`. Existing destination assets are now matched by both exact filename and normalized filename, reducing cases where duplicate responses without an embedded asset id could not be reassociated back to the source album.
  - Improved `Immich` album-association tracing so partial or rejected `add assets to album` responses are now logged explicitly instead of being silently collapsed into a zero-added count.
  - Added delayed automatic requeues for transient `Automatic Migration` push failures so assets that fail while the target server is temporarily unreachable are retried a few minutes later, multiple times, before being counted as final push failures.
  - Tightened `Automatic Migration --move-assets true` source deletion semantics so local source assets are now removed only after the destination upload was actually resolved to a reusable target asset id, avoiding premature source deletion when a duplicate or failed upload did not leave a usable destination reference.
  - Added a final local-source cleanup pass for `Automatic Migration --move-assets true` that removes metadata-only leftovers, deletes empty album/source folders, and drops the source root itself when it becomes fully empty after a successful move-based migration.
  - Expanded `--consolidate-similar-albums` for `Immich`, `Synology`, `Google Photos`, `NextCloud`, and `Automatic Migration` so album groups such as `Album`, `Album_1`, `Album (2)`, `Album_5`, `New_Album`, and `New Album` are now treated as the same reusable album family. When this flag is enabled PhotoMigrator prefers the clean keeper name without a numeric suffix and with spaces instead of underscores, merges the assets from the discarded variants into that preferred keeper, and then removes the redundant albums when the target service supports album deletion. On `Google Photos`, redundant variants are kept because the public API cannot delete albums.
  - Added `--prefer-canonical-album-names` so new destination albums now also use the preferred normalized keeper name even when the target has no prior redundant/similar albums. This means source albums such as `Album_1` or `New_Album 1` are now created directly as `Album` / `New Album` instead of preserving the duplicate-like suffix when no conflicting target family exists yet.
  - Split the previous combined similar-album behavior into two independent flags across cloud `Upload Albums`, cloud `Upload All`, and `Automatic Migration`: `--prefer-canonical-album-names` controls normalization of newly created destination album names (for example `Album_1` -> `Album`), while `--consolidate-similar-albums` controls reuse/consolidation of equivalent existing album families.
  - Updated GPTH to v6.1.6 which includes several New Features and Bug Fixes.
  - Added a post-GPTH Google Takeout repair step that scans original album-side `.json` metadata entries which were left without a materialized media file in the processed album output, locates the real asset under `ALL_PHOTOS` using the JSON `title` and timestamp-derived date, and recreates the missing album entry automatically as a symbolic link/hardlink or copied file depending on the selected album-link mode.
  - Moved Google Takeout orphan album asset recovery earlier into the main processing pipeline so recovered album entries are already present before `Analyze Output Files`, which now counts them in the output totals and includes them in the cached date dictionaries used by later steps. The recovery pass now ignores album-level metadata JSONs such as `metadata.json`/localized equivalents, groups its logging by album instead of warning once per unresolved asset, and prefers nearest-year fallbacks when the expected asset is not under the exact `ALL_PHOTOS/<year>` bucket.
  - Expanded Google Takeout structure detection so PhotoMigrator now also recognizes album-only exports that do not contain `Photos from YYYY` year folders, as long as it finds a localized `Google Photos`/`Google Fotos` container, album-side `.json` metadata, and `archive_browser.html` next to that container. When this album-only layout is detected, PhotoMigrator now runs GPTH automatically in `--fix` mode instead of requiring the user to force `--google-ignore-check-structure` manually.

#### 🚀 GPTH Enhancements:
✨ GPTH New Features
  - New --no-resume flag — GPTH automatically resumes a previous run when the output folder contains a progress.json. Pass --no-resume to discard that saved progress and always start fresh (--resume remains the default). When resume is disabled, the step-resume state is wiped at pipeline start so later runs cannot pick up a half-stale mixture of old and new step records.
  - Interactive mode now asks before resuming a previous run — When the selected output folder contains saved progress from an earlier run, interactive mode shows which steps were already completed and asks whether to resume or start fresh, instead of resuming silently. Part of the fix for issue #131.

🐛 GPTH Bug Fixes
  - Reusing folders from a previous run no longer aborts interactive mode — Selecting an extraction folder that still contained data from an earlier run made GPTH exit with a fatal error right after the disk-space notice, before any of the processing questions were asked. Interactive mode now validates the extraction folder the same way CLI mode does: a completed previous extraction of the same ZIP set is reused (extraction is skipped entirely), and any unsafe state (leftover data, a different ZIP set, an interrupted extraction) is explained with a prompt to select a different folder. Interactive runs also record the extraction sentinel in progress.json now, so future runs can safely detect and reuse the extracted data. This resolves issue #131.
  - Stale resume state is detected and discarded — If a previous run's progress.json marked processing as completed but the recorded output files no longer exist (e.g. the output folder was emptied between runs), GPTH used to "resume" by skipping every step and reporting success within seconds while doing nothing. The saved state is now validated against the files on disk at pipeline start and discarded with a clear warning when it is stale, so the run processes everything fresh. This resolves issue #131.
  - --fix mode no longer exits with ERROR_CODE_13 — In fix mode the output directory is the input directory, so the non-empty-output safety check always triggered and refused to run. The check is now skipped when output equals input. This resolves issue #128.
  - Partner-shared companion videos and numbered files are now sorted into PARTNER_SHARED — MP4/MOV companion videos paired with HEIC/JPG stills, and numbered files like IMG_1976(1).MP4 (whose sidecar is IMG_1976.HEIC.supplemental-metadata(1).json) or x(1).jpg, were not flagged as partner-shared because the cross-extension and numbered JSON matching strategies were not applied during discovery. JSON sidecar matching now supports numbered suffixes and cross-extension pairing, using three-level matching (exact, dot-boundary, first match) to prevent false positives such as photo matching photograph. This resolves issue #123.
  - ZIP selection no longer crashes when the file picker returns files without paths — On certain system configurations the file picker returns ZIP entries with a null path, which crashed interactive ZIP selection with a null-check exception. Null-path entries are now filtered out with a visible warning (also when only some of the selected files are affected, which previously dropped them silently), and a clear error message guides the user to extract manually if no usable ZIPs remain. This resolves issue #129.

#### 🐛 Bug fixes:
  - Fixed the `--preview-album-actions` flow for cloud `Rename Albums` and `Remove Albums` so the preview confirmation now takes precedence over the global `--no-request-user-confirmation` flag. When preview mode is enabled, PhotoMigrator now always waits for an explicit user decision before applying the rename or delete action, including Web Interface jobs that send confirmation through the running-job input channel.
  - Improved cloud `Rename Albums` preview feedback so wildcard patterns that do match albums but produce no effective name change (for example `*-*` replaced by `-`) are now reported explicitly as no-op renames instead of looking like zero matches. 
  - Fixed the Web Interface parsed help renderer so both `Example:` and `Examples:` lines are highlighted consistently.
  - Fixed CLI parsing for `--rename-albums` when the replacement value itself starts with `--`. PhotoMigrator now accepts the safe single comma-separated form (for example `--rename-albums "*-*, --"`), avoiding `argparse` confusion with the end-of-options marker while keeping the normal two-argument form working for replacements such as `-`.
  - Fixed `Google Takeout` video metadata repair helpers so they now tolerate test/runtime environments where `dateutil.parser.parse()` is stubbed or returns a plain string. The metadata-date normalizer now falls back to `datetime.fromisoformat()` for ISO timestamps instead of crashing with `AttributeError: 'str' object has no attribute 'tzinfo'`.
  - Fixed `Google Takeout` output-folder naming when the processing input already points to a generated `..._unzipped_<TIMESTAMP>` folder, so PhotoMigrator now collapses that staging suffix before creating the processed folder and produces `Takeout_processed_<TIMESTAMP>` instead of `Takeout_unzipped_<TIMESTAMP>_processed_<TIMESTAMP>`.
  - Fixed Web Interface command generation for `Rename Albums` so replacement values that start with `-` or `--` are now kept as a single comma-separated `--rename-albums` argument in both the command preview and the executed job, matching the parser behavior already used by the shared CLI/TUI/GUI command builder.
  - Fixed the Web Interface `Automatic Migration` Live Dashboard so totals and progress bars now survive page refreshes and reconnections from another device. The backend now persists a structured per-job dashboard snapshot while the migration is running, and the frontend rehydrates counters and progress from that snapshot instead of re-inferring them only from the compact rolling log buffer, which previously lost the original fixed totals and could make bars jump to `100%` mid-run after refresh.
  - Fixed the Windows desktop GUI `Automatic Migration` `Live Dashboard` external-terminal launcher so the dashboard window now opens correctly instead of failing on the window-title command parsing, and the GUI now also restores its controls if that external launch fails before reporting a completion status. (Issue #1156).
  - Fixed early-import logger binding bugs in `FileUtils`, `ConfigReader`, and `FileStatistics` so helper paths that can be imported before the global logger is initialized now resolve the active logger dynamically at runtime instead of crashing later with `'NoneType' object has no attribute info/warning/error'`. This fixes the pre-detection ZIP unpack step used by `Automatic Migration` local-folder sources and hardens similar startup-time execution paths that rely on configuration loading or file-statistics helpers.
  - Hardened similar-album consolidation across `Automatic Migration`, `Immich`, `Synology`, `Google Photos`, and `NextCloud` so the log now reports how many assets were requested and confirmed during album reassignment, and redundant albums are no longer deleted when the reassignment is only partial.
  - Fixed `Automatic Migration` and Synology shared-album handling so collaborative Synology Photos albums are no longer treated as normal albums just because the initial list response omitted `passphrase`. PhotoMigrator now resolves shared-album access details before listing album assets, which avoids `Failed to list photos in the album ...` errors and preserves album membership for items contributed by multiple Synology users during migrations to targets such as `Immich`. (Issue #1159).

#### 📚 Documentation:
  - Updated documentation with all changes.

---

## Release: v4.3.3
### Release Date: 2026-06-30
  
#### 🚨 Breaking Changes:

#### 🌟 New Features:
  - Added a new standalone `Organize Local Folder By Date` feature under `Other Features`, available from CLI, GUI, TUI, and Web Interface. It can reorganize a local folder into `year`, `year/month`, `year-month`, or `flatten` output structures, optionally write into an explicit `--output-folder`, generate a processed output folder using a configurable suffix when no explicit output is provided, and optionally `--move-original-files` instead of copying to avoid duplicating disk usage. (Discussion #1118).

#### 🚀 Enhancements:
  - Improved `iCloud Takeout` handling of media that cannot be dated from `Photo Details.csv` so those assets are no longer left to fall back into misleading current-month folders. After `ALL_PHOTOS` date organization, unresolved items are now moved under `ALL_PHOTOS/Unknown Date/No CSV Match` and `ALL_PHOTOS/Unknown Date/Ambiguous Match`, while ambiguous CSV rows are no longer written blindly to multiple files. This keeps the processed library auditable and still fully compatible with `Automatic Migration`, which already ingests everything placed under `ALL_PHOTOS`. (Discussion #1118).
  - Added a narrow global fallback for `iCloud Takeout` `Photo Details.csv` matching so rows that still fail their normal same-folder / same-scope lookup can now recover against the staged media pool only by checksum or, when there is no ambiguity, by a globally unique filename. This improves recovery of split or oddly structured exports without reintroducing the broad cross-folder matching that previously caused duplicate associations. (Discussion #1118).
  - Expanded the `iCloud Takeout` album and memories rebuild report so it now tracks fully resolved, partially resolved, and unresolved member counts, and changed collection materialization to always create the destination album/memory folder whenever its CSV contains members even if none of them can be resolved. That makes empty collections explicit instead of silently hiding them, which is more useful for support and user verification. (Discussion #1118).
  - Fixed reverse `Shift+Tab` panel navigation in the CLI TUI so entering the `Feature Selector` or `General Tabs` panels now focuses the panel's primary control instead of the last button in that panel. This prevents backward navigation from landing on `Exit` instead of `Automatic Migration`, or on `Load Config` instead of `FEATURE`, while keeping normal forward `Tab` behavior unchanged.
  - `iCloud Takeout` now exports an `Unresolved_Assets.csv` report into the processed output folder whenever any `Album` or `Memory` collection is only partially resolved or ends up empty. The CSV lists the collection type, collection name, collection status, unresolved asset name, source CSV, and per-collection resolved/unresolved counts so support and end users can identify exactly which members were missing from the final rebuild.
  - `iCloud Takeout` now also exports a `No_Date_Assets.csv` report into the processed output folder whenever any staged media asset cannot be assigned a usable CSV date and is therefore moved under `ALL_PHOTOS/Unknown Date/...`. The CSV lists each affected asset together with the reason (`No CSV Match` or `Ambiguous Match`) and its source/output paths for easier audit and follow-up.

#### 🐛 Bug fixes:
  - Fixed the Web Interface form for the standalone `Organize Local Folder By Date` feature so its action-scoped optional arguments now render correctly (`Output Folder`, `Output Folder Suffix`, `Folder Structure`, and `Move Original Files`) instead of only showing the generic output folder field. The browser-side form builder now resolves those auxiliary arguments from the full parser `fields_by_dest` schema instead of only from the visible tab lists. The interactive UI schema now defaults `Output Folder Suffix` to `processed`, while the generated folder name still keeps the final underscore separator and becomes `<INPUT_FOLDER>_processed_<TIMESTAMP>` when no explicit output folder is provided, and automatically clears that suffix again when an explicit `Output Folder` is selected.
  - Fixed the local TUI and desktop GUI forms for the standalone `Organize Local Folder By Date` feature so `Output Folder Suffix` now shows the effective `processed` default whenever `Output Folder` is empty, even if an older persisted UI state had previously stored that suffix as blank, and automatically clears the suffix when an explicit output folder is set.
  - Fixed the Web Interface `Help Navigation` sidebar so `Other Features` now includes the new `Organize Local Folder By Date` subentry that jumps directly to its dedicated section inside `help/10-other-features.md`.
  - Fixed a Web Interface regression in the `Features Selector` panel that left `Google Photos`, `Synology Photos`, `Immich Photos`, `NextCloud Photos`, and `Other Features` blank after selection. The shared module-argument renderer had been wired against a non-existent frontend constant, causing the browser-side render path to fail before painting those action selectors.
  - Replaced the Web Interface FastAPI startup hook based on deprecated `@app.on_event("startup")` with a proper `lifespan` initializer and shutdown cleanup for the backup scheduler thread, removing the repeated deprecation warnings emitted during web-interface test runs and aligning the app lifecycle with current FastAPI recommendations.

#### 📚 Documentation:
  - Documented the new standalone `Organize Local Folder By Date` feature in `help/01-command-line-interface.md`, `help/02-arguments-description.md`, and `help/02-arguments-description-short.md`, including its CLI syntax, folder-structure options, generated output-folder suffix behavior, explicit `--output-folder` behavior, and `--move-original-files` mode.
  - Expanded `help/10-other-features.md` with a full section for `Organize Local Folder By Date` and updated the `README.md` `Other Standalone Features` overview so that local date-based library organization is explicitly listed there as well.
  - Expanded `help/05-icloud-takeout.md` so the `iCloud Takeout` documentation now also covers the `ALL_PHOTOS/Unknown Date/...` fallback flow and the audit CSV reports `Unresolved_Assets.csv` and `No_Date_Assets.csv`, including when each report is emitted and which fields it contains.
  - Updated documentation with all changes.

---

## Release: v4.3.2
### Release Date: 2026-06-25

#### 🐛 Bug fixes:
  - Finished hardening Windows non-UTF console output for Google Takeout so GPTH progress lines are no longer written through a raw `print()` path that can still crash GUI/desktop runs with `UnicodeEncodeError` inside `colorama` when the progress text includes emoji or other characters outside `cp1252`. (Issue #1141).
  - Fixed the GPTH `CreateFile failed ... (error=2)` warning compactor so Windows creation-time warnings are now collapsed before the generic progress parser runs; this prevents mixed `n/total` warning lines from bypassing compaction and still flooding the live console even when the log file already stays clean. (Issue #1142).
  - Added a Google Takeout post-process repair for processed videos whose native container date remains correct but GPTH leaves conflicting `XMP` date tags behind, so `Automatic Migration` targets such as Immich no longer misgroup those videos under the wrong day/month. The final extracted-dates metadata snapshot is now updated in-memory as part of that repair as well. (Issue #1145).
  - Fixed `Automatic Migration` from processed Google Takeout sources so album discovery is now rebuilt from the processed folder tree on disk instead of the final dates JSON snapshot. This preserves albums made only of shortcuts/symlinks into `ALL_PHOTOS`, allowing destination album creation to include those Takeout albums as expected. Also fixed the downstream album-push accounting race so albums are still counted when the last asset finishes before the puller removes the temporary `.active` marker, hardened duplicate upload handling for destinations that rely on returned asset IDs (`Immich` and `Synology`) so duplicate responses without an existing asset ID are treated as failures instead of being silently consumed, and on Windows now force GPTH `shortcut` albums to use `--hardlink` so processed album entries are created as real filesystem links instead of `.lnk` shortcut files that the migration pipeline cannot reuse as media assets. (Issue #1146).
  - Fixed the `Automatic Migration` Live Dashboard progress capture used from CLI and from the TUI launcher when GPTH is running in the background. Carriage-return-only GPTH progress frames are now captured correctly, the dashboard now understands both tqdm-style progress lines and simple `step : current/total` GPTH counters, and the background-progress panel now shows 5 rows while prioritizing the most recent active steps so phases such as `Processing album associations`, `Moving entities`, `Writing EXIF data`, and `Updating creation times` no longer stall visually at `0%`, disappear behind older completed rows, or only jump at the end. The progress normalizer now also treats GPTH prefixes like `[INFO]` and `[ INFO ]` as the same step key, preventing near-complete bars from getting stuck on stale duplicates when the final `100%` frame arrives with a slightly different prefix format. Empty GPTH output frames also no longer generate repeated blank `[PROCESS]-[Metadata Processing]` entries in the log panel. (Issue #1147).

#### 📚 Documentation:
  - Updated `UpdateAll.py` so changing the tool version/date now also synchronizes the version banner shown in `help/01-command-line-interface.md`.
  - Updated documentation with all changes.

---

## Release: v4.3.1
### Release Date: 2026-06-18
  
#### 🚀 Enhancements:
  - Optimized `iCloud Takeout` date writing by switching from one `ExifTool` process per asset to a persistent shared `ExifTool` session reused across the whole run, which should significantly reduce the runtime of the `Write Dates` step on large exports. (Issue #1133).
  - Extended `iCloud Takeout` date application so it now also updates filesystem timestamps for processed assets: file modified dates are refreshed for all supported platforms, and file creation dates are also updated where the platform provides support (`Windows` directly, `macOS` when `SetFile` is available, plus `ExifTool` file-date tags on supported systems). (Issue #1133).
  - The iCloud `Memories` option is now pre-selected by default in the Web Interface, TUI, and GUI, while CLI semantics remain unchanged and still use the existing `-iMem, --icloud-include-memories` flag.
  - Removed the iCloud embedded-date pre-read skip pass during `Write Dates` because it added extra metadata reads and, in practice, was not producing useful skips on real exports. The processor now writes the target CSV date directly and only performs the lightweight filesystem timestamp comparison needed to avoid redundant timestamp updates.
  - Added a new iCloud Takeout flag `-iNExif, --icloud-prefer-native-exif-writer` to prefer the native EXIF writer for supported photo files and fall back to the shared persistent `ExifTool` session otherwise. This option is opt-in in CLI and pre-selected by default in the Web Interface, TUI, and GUI so performance can be compared without hard-coding one strategy.
  - Added `Migration Filters` to `Automatic Migration` in the desktop GUI and CLI TUI, matching the Web Interface behavior with per-migration override fields that fall back to `General Arguments` when left empty.
  - Improved CLI TUI keyboard ergonomics so the interface can now be navigated with `Tab` / `Shift+Tab` and arrow keys, while `Enter`, `Esc`, and `Backspace` / `Delete` can be used to activate controls or leave the current non-text control more consistently.
  - `Automatic Migration` now auto-detects raw Apple iCloud Takeout folders used as local `--source` paths, preprocesses them first with the iCloud pipeline, and only then uploads the resulting library to the selected target.
  - When `Automatic Migration` auto-detects a raw Apple iCloud Takeout local folder and preprocesses it through the iCloud pipeline, `Memories` are now included by default for that automatic preprocessing pass even if the CLI invocation did not explicitly add `--icloud-include-memories`.
  - Local-folder and processed-takeout sources now treat a top-level `Memories` folder the same way as `Albums`, so each memory collection is migrated to the target as an album-like collection.
  - Hardened raw iCloud Takeout auto-detection for local folders and ZIP containers so it now also inspects iCloud CSV metadata headers, not just known file names, which keeps detection working even when users rename the extracted folder tree or the CSV filenames.
  - Changed `Automatic Migration` local-folder classification so ZIP-based sources are now unpacked first and only then classified as Google Takeout, iCloud Takeout, or normal local folders. This avoids relying on ZIP-content inspection during the initial source-type detection pass for large exports.

#### 🐛 Bug fixes:
  - Hardened `iCloud Takeout` date parsing so Apple `Photo Details.csv` timestamps are now parsed with strict known formats before any heuristic fallback, preventing explicit years like `2023` from being silently replaced by the current year during EXIF and filesystem date writes. Added regression coverage for the reported `December 27,2023 3:42 AM GMT` case. (Issue #1133).
  - Hardened shared console output so Windows GUI/desktop runs no longer crash with `UnicodeEncodeError` when GPTH progress messages include Unicode symbols on non-UTF consoles such as `cp1252`. (Issue #1141).
  - Compacted repeated GPTH Windows `CreateFile failed ... (error=2)` warnings during the final creation-time update step into a single summary message so large Takeout runs no longer flood the console/log with thousands of near-identical lines. (Issue #1142).
  - Fixed iCloud reconstructed album and memory symlinks to use relative targets instead of container-only absolute paths, so exported folders remain valid outside Docker mounts and on macOS/Linux filesystems.
  - Stopped emitting misleading `Error reading EXIF ... Given file is neither JPEG nor TIFF` warnings during iCloud `ALL_PHOTOS` organization for PNG/GIF files whose date already comes from CSV metadata plus filesystem timestamps.
  - Improved Web Interface job logs so indeterminate `tqdm` progress lines are compacted instead of being appended repeatedly, and each finished job now writes an explicit completion line with final status and exit code.
  - Hardened Web Interface multi-user config isolation so web sessions can no longer override `--configuration-file` with an arbitrary path, command previews/jobs no longer expose the physical generated `Config_*.ini` cache path, and imported config values are now revalidated against the authenticated user's allowed roots before being persisted.

#### 📚 Documentation:
  - Clarified the iCloud Takeout documentation so it now states explicitly that reconstructed `Albums` and `Memories` use symlinks by default, and that `--icloud-no-symbolic-albums` switches that behavior to duplicated copies.
  - Updated documentation with all changes.

---

## Release: v4.3.0
### Release Date: 2026-06-17
  
#### 🚨 Breaking Changes:
  - Changed the compiled binary artifact naming on Unix-like platforms so macOS releases now use `.command` for better Finder integration while Linux and Synology SSH releases now use `.bin` instead of `.run`.

#### 🌟 New Features:
  - Added a new native desktop GUI powered by `tkinter`, built on top of the same shared UI/model layer as the CLI TUI so it can expose the same module structure, dynamic forms, configuration editor, command preview, and in-app execution log through a graphical windowed interface. (Issue #1123)
  - Added a new interactive CLI TUI powered by `Textual`, designed to be much closer to the Web Interface layout. The new terminal UI includes the same top-level feature selector modules, `General Arguments`, `Features Config`, and `App Settings` views, dynamic module-specific forms, multi-account configuration selectors for cloud services, live command preview, and in-terminal execution logs. (Issue #1122).

#### 🚀 Enhancements:
  - Replaced the previous Google-only Tkinter configuration window with a full multi-module desktop GUI that reuses the same parser schema, config editor model, and command-building pipeline as the CLI TUI.
  - Updated the CLI launch flow so running PhotoMigrator without arguments now opens the new desktop GUI by default, falls back to the CLI TUI when `tkinter` or a graphical display is not available, and finally falls back to command-line help if no interactive UI can be started. Running it with a single Takeout folder argument still opens the terminal UI with `Google Takeout` prefilled, and `--tui` / `--gui` remain available as explicit launcher flags.
  - Added a shared UI/model layer for parser schema generation, config-form parsing, command composition, and special field handling so the CLI TUI reuses the same data-driven concepts already used by the Web Interface instead of hardcoding a Google-only form.
  - Kept backward-compatible fallback behavior for environments where `Textual` or the required interactive terminal capabilities are not available, preserving the previous legacy GUI/console configuration flow.
  - Refined the CLI TUI navigation so selecting a module now shows only that module's fields in the main panel, while `General Arguments` is displayed as its own separate view instead of being rendered above every feature form.
  - Polished the CLI TUI layout and theming so the terminal interface is now visually closer to the Web Interface, including improved panel structure, dynamic themed colors, better sidebar actions, clearer section accents, compact boolean toggles, multi-column general arguments, and more consistent field spacing and alignment.
  - Added dedicated `Exit` actions to both the desktop GUI and the CLI TUI, including confirmation dialogs and automatic disabling while a job is still running.
  - Improved the TUI path picker with quick navigation buttons to go to the parent folder or return to the launch working directory.
  - Removed the `Upload to Server` module from the local GUI/TUI feature selectors because that workflow only makes sense in the Web Interface.
  - Refined the desktop GUI visual styling so themed buttons, module tabs, panel titles, and boolean toggles are more consistent with the TUI and Web Interface presentation.
  - Updated `Automatic Migration` in both the desktop GUI and the CLI TUI so `source` and `target` now use the same endpoint selector concept as the Web Interface, allowing users to choose between local folders and supported cloud services, and to pick account `1` / `2` / `3` whenever a cloud endpoint is selected.
  - Updated GUI and TUI config-file handling so both interactive interfaces now honor `--configuration-file` at startup and preload that file before rendering the configuration editor or running any module. Their default `Config.ini` resolution was also aligned with classic CLI behavior, so if no explicit path is given they use `./Config.ini` from the current execution folder.
  - Simplified the GUI and TUI `Command Preview` panels so they now display a compact `PhotoMigrator <args>` representation instead of the full absolute Python executable path and absolute `PhotoMigrator.py` entrypoint path.
  - Added basic clipboard ergonomics to the CLI TUI with `Ctrl+C` / `Ctrl+V` actions for the current text context, plus a right-click context menu that exposes `Copy` everywhere there is copyable text and enables `Paste` only on editable input fields.
  - Added collapsible panel controls to the desktop GUI and CLI TUI, and updated both layouts so running a module temporarily shrinks the upper content area and expands the `Execution Log` area for better runtime visibility before restoring the default proportions when the job finishes.
  - Refined clipboard and panel UX in both local interfaces: the TUI now uses a smaller floating context popup instead of a large modal-style dialog, and the desktop GUI now exposes native right-click `Copy` / `Paste` menus plus selectable read-only text panels for `Argument Description`, `Command Preview`, `Status`, and `Execution Log`. The desktop GUI also now remembers the last saved window geometry between sessions.
  - Reworked the GUI/TUI configuration toolbar so `Load Config` now validates an external `.ini` file before asking permission to overwrite the active configuration file, while `Save Config` and `Save UI State` now go through explicit confirmation dialogs and the save-oriented toolbar actions use a distinct pastel-blue visual treatment.
  - Improved runtime behavior in the desktop GUI and CLI TUI so the upper `Feature` panel now auto-collapses while a job is running, `Execution Log` compactly rewrites progress-bar updates instead of appending a new line for every refresh, and the TUI log panel now supports context-aware copy actions via `Ctrl+C` and the right-click context menu.
  - Renamed the local interactive window titles so the terminal interface now identifies itself as `Terminal Interactive User Interface (TUI)` and the desktop window as `Graphical User Interface (GUI)`, both keeping the current PhotoMigrator version in the title bar.
  - Updated the desktop GUI so `Automatic Migration` runs launched with `Live Dashboard` in an external terminal now report their exit code back into the GUI `Execution Log`, restore the GUI window to the foreground when the dashboard finishes, and raise the main `tkinter` window to the foreground on startup.
  - Increased the vertical spacing between `Feature Selector` buttons in the desktop GUI so the different feature entries are visually separated more clearly.

#### 🐛 Bug fixes:
  - Fixed the CLI TUI `Features Config` view so config sections no longer rebuild in a visible loop, theme selection behaves more predictably, and `Config.ini` fields can be edited and saved correctly from the terminal interface.
  - Fixed multiple CLI TUI rendering issues affecting panel titles, scroll behavior, main-panel layout balancing, sidebar feature scrolling, and terminal form presentation across `Feature`, `General Arguments`, `Features Config`, and `App Settings`.
  - Fixed the desktop GUI `Automatic Migration` endpoint editor so cloud-based `source` / `target` selectors now show the `Account` label correctly in front of the account combobox, matching the TUI layout.
  - Fixed GUI/TUI interactive runtime regressions so `ExifTool` discovery now also falls back to executables available in the system `PATH`, the embedded `exif_tool` bundle auto-recovers missing Perl library files from `others.zip` before use, the CLI TUI `Execution Log` now uses an explicit drag-selection layer plus non-wrapped long lines for reliable selected-text copying from both `Ctrl+C` and the context-menu `Copy` action and for better horizontal mouse-wheel scrolling, and the desktop GUI now clears persistent readonly `Combobox` text highlighting after a selection is made.
  - Fixed the desktop GUI `Execution Log` so ANSI-colored runtime output is now rendered with its original colors instead of being flattened to plain text.
  - Fixed the CLI TUI `Execution Log` so ANSI-colored runtime output is now rendered with its original colors and the log automatically stays pinned to the latest output while a job is running.
  - Fixed GUI/TUI child-process color handling so interactive jobs now keep emitting ANSI-colored output even when launched through piped `Execution Log` panels instead of a native TTY.
  - Fixed bundled `ExifTool` execution in `FolderAnalyzer`, `FileStatistics`, and standalone rename flows by ensuring the binary is executable before use; on macOS bundled tool execution also now attempts to clear the `com.apple.quarantine` attribute first.
  - Improved the CLI TUI `Execution Log` with non-wrapping long lines, horizontal overflow support, and horizontal mouse scrolling support for log inspection.
  - Fixed the CLI TUI startup crash caused by assigning to Textual's read-only `allow_horizontal_scroll` property while constructing the custom `Execution Log` widget.
  - Updated CLI TUI `Automatic Migration` Live Dashboard behavior so fullscreen Rich dashboard runs now require an explicit confirmation dialog explaining the temporary terminal handoff; rejecting that dialog runs the same migration without `Live Dashboard` for that execution only and returns to the normal embedded TUI log flow.
  - Updated desktop GUI `Automatic Migration` to mirror the TUI `Live Dashboard` flow: the GUI now warns before fullscreen dashboard runs, launches confirmed dashboard executions in an external terminal window, returns focus to the GUI, and aligns `source` / `target` endpoint labels with the TUI (`Folder Path` for local folders and left-aligned `Account` for cloud services).
  - Adjusted the desktop GUI `Live Dashboard` external-terminal handoff so the newly opened terminal window now stays in the foreground when the dashboard starts, while the GUI window is still brought back to the foreground automatically once that external dashboard run finishes.
  - Fixed local GUI/TUI execution from compiled binaries so child jobs and external-terminal dashboard runs now execute from the user's real launch working directory instead of the temporary extracted bundle folder, the command relaunch path now correctly targets the current frozen executable instead of trying to re-run `PhotoMigrator.py`, and the `Config.ini` editor now falls back to the active launch-folder config file when the packaged template is unavailable so `Save Config` no longer empties the file in binary builds.
  - Updated the local interactive dependency baseline from legacy `textual~=0.72.0` to `textual>=8.2.7,<9` so compiled TUI builds use the same modern CSS-capable Textual generation already validated in the development environment
  - Adjusted frozen-binary relaunch detection to prefer the original `sys.argv[0]` launcher path over the temporary bundle `python3` runtime on macOS onefile builds.
  - Hardened the GUI/TUI subprocess relaunch logic in frozen binaries so it now captures the original launcher context at startup, prefers the real `PhotoMigrator` packaged artifact path, and rejects temporary `python` runtime executables when composing child commands. This reduces false relaunches against `python3.exe` / `python3` extracted into onefile temp folders on Windows, macOS, and Linux.
  - Fixed the desktop GUI `Argument Description` panel so wrapped text now uses the actual panel body width instead of an approximate root-window width, avoiding premature line breaks before the available horizontal space is filled.
  - Adjusted the desktop GUI `GOOGLE TAKEOUT` and `iCLOUD TAKEOUT` feature buttons again so they now use a pastel blue palette, including matching active-state styling.

#### 📚 Documentation:
  - Added desktop GUI documentation to the README and execution/help pages, including the explicit `--gui` launcher flag and the fact that the desktop GUI is now the default startup experience when PhotoMigrator is executed without arguments.
  - Added CLI TUI documentation to the main `Command Line Interface` help page, including the `--tui` launcher flag and the updated GUI → TUI → help fallback order.
  - Updated execution guides for source and binary usage to document how to launch the new interactive CLI TUI on Windows, macOS, Linux, and Synology SSH terminals.
  - Updated the compiled-binary execution guide, README, argument references, and the main feature help pages to document the new macOS `PhotoMigrator.command` and Linux/Synology `PhotoMigrator.bin` binary names, and to explain the Gatekeeper first-launch unblock step using `xattr -dr com.apple.quarantine`.
  - Updated `Google Takeout` documentation and `README.md` so the default no-argument CLI behavior now references the new terminal UI instead of only the legacy prompt flow.
  - Refined the `README.md` GUI/TUI overview section to clarify the purpose of each interactive interface, the default launcher order, and the explicit `--gui` / `--tui` entrypoints.
  - Documented that GUI and TUI now accept `--configuration-file` during startup, and clarified across `README`, CLI help, argument descriptions, configuration-file help, and source/binary execution guides that the interactive UIs use `./Config.ini` from the execution folder by default.
  - Clarified the compiled-binaries documentation for macOS and Linux so the examples now use generic versioned artifact names like `PhotoMigrator_vx.y.z_macos_<arch>.command` and explicitly instruct users to replace them with the exact downloaded release filename, avoiding confusion with non-versioned placeholder names.
  - Updated Issues Templates.
  - Updated documentation with all changes.

---

## Release: v4.2.0
### Release Date: 2026-06-16

#### 🌟 New Features:
  - Added a new `iCloud Takeout` feature across CLI and Web Interface to process Apple iCloud Photos exports without GPTH, recovering dates from `Photo Details.csv`, assigning those dates to the exported media files, rebuilding `Albums` from Apple CSV manifests, and optionally reconstructing `Memories` collections. The Web Interface now includes a dedicated `iCloud Takeout` tab placed after `Google Takeout` and before `Google Photos`.

#### 🚀 Enhancements:
  - Reordered feature navigation consistently across the Web Interface, documentation, README, help index, and documentation sidebar so the current module order is: `Google Takeout` → `iCloud Takeout` → `Google Photos` → `Synology Photos` → `Immich Photos` → `NextCloud Photos` → `Other Features`.
  - Improved `iCloud Takeout` matching so `Photo Details.csv`, `Albums/*.csv`, and optional `Memories/*.csv` are now resolved per export folder/scope instead of being merged into a single global index, preventing collisions when different iCloud export parts contain assets with the same basename.
  - Added `iCloud Takeout` section generation to the auto-formatted `--help` output through `CustomHelpFormatter`, matching how the other top-level features are grouped in CLI help.
  - Updated the Web Interface so `Features Config` no longer shows `Google Takeout` and `iCloud Takeout` configuration tabs, and normalized the feature selector label to `iCLOUD TAKEOUT`.
  - Improved `Features Config` for multi-account services (`Google Photos`, `Synology Photos`, `Immich Photos`, `NextCloud Photos`) by adding an account selector that shows only the global fields plus the selected account fields instead of rendering all accounts at once.
  - Refined the `Features Config` account selector layout so global fields are shown first, the account combobox appears immediately below them, and the selected account fields are rendered underneath.
  - Adjusted the `Features Config` account selector width and alignment so the combobox matches the same field grid and visual width as the rest of the configuration inputs.
  - Tightened the `Features Config` account selector combobox width while keeping its right edge aligned with the account fields below it, improving the visual balance of the configuration panel.
  - Reduced the `Features Config` account selector combobox to a much narrower width while preserving right-edge alignment with the account fields below it.
  - Added pastel color grouping to the Web Interface `Feature Selector` tabs: green for `Automatic Migration`, yellow for both `Takeout` tabs, blue for cloud-service tabs, purple for `Other Features`, and red for `Upload to Server`.
  - Updated the `Feature Selector` cloud-service tabs (`Google Photos`, `Synology Photos`, `Immich Photos`, `NextCloud Photos`) from blue pastel to brown pastel to better differentiate them from the other tab groups.

#### 🐛 Bug fixes:
  - Fixed `contains_zip_files()` so it no longer crashes in unit-test or lightweight execution contexts where the global `LOGGER` has not been initialized yet.

#### 📚 Documentation:
  - Added dedicated `iCloud Takeout` documentation, including Apple export/download guidance, supported CSV/ZIP structure details, CLI/Web Interface usage, and output behavior.
  - Added `iCloud Takeout` arguments and examples to `Command Line Interface`, `Arguments Description`, and `Arguments Description (Short)` help pages, and moved the Apple export request guidance to the top of the dedicated `iCloud Takeout` documentation inside a `TIP` block.
  - Renumbered and reordered the help sections to place `iCloud Takeout` as section `5` and `Google Photos` as section `6`, keeping links and documentation navigation aligned with the current feature order.
  - Fixed the Web Help Navigation label for `5. iCloud Takeout` so the product name casing is rendered correctly in the documentation sidebar.
  - Reworked the `README` main modules structure so `iCloud Takeout Fixing` now appears as its own section `3`, separate from the cloud-service management section, and renumbered the following sections accordingly.
  - Renamed all top-level `/help` markdown files from single-digit prefixes to zero-padded prefixes (`00`-`09`) and updated all project references so documentation links, README links, and the web help navigation continue to resolve correctly.
  - Replaced absolute documentation links in `README.md` and `/help` markdown files with GitHub-friendly relative links, and updated the web help viewer resolver so those same relative links continue to work inside the Web Interface documentation viewer.
  - Updated Screenshots.
  - Updated documentation with all changes.

---

## Release: v4.1.0
### Release Date: 2026-06-01
   
#### 🌟 New Features:
  - Added configurable exclusion patterns for local-folder based processing and migrations through `--exclude-folders` and `--exclude-files`, and exposed them in the web interface filters. (Issue #1095).
  - Added environment-variable overrides for cloud-service configuration keys loaded from `Config.ini`, including support for `*_FILE` secrets files, plus a new `PHOTOMIGRATOR_DEFAULT_GOOGLE_TAKEOUT_PATH` web default to pre-populate the Google Takeout source path in the job form. (Issue #1093).
  - Added multilingual Google Takeout structure detection for localized Google Photos exports, including year folders such as `Photos from 2020`, `Fotos de 2020`, `Fotos del 2020`, `Photos de 2020`, `Fotos von 2020`, `Foto del 2020`, plus major non-Latin variants (Chinese, Japanese, Korean, Russian). Detection now also keeps scanning likely `Google Photos` subfolders even when the Takeout root contains many sibling services.
  - Added Automatic Migration support for GPTH layouts containing `PARTNER_SHARED` and `Special Folders`: partner shared albums under `PARTNER_SHARED/Albums` are now migrated as albums, partner shared loose assets under `PARTNER_SHARED/ALL_PHOTOS` are migrated as non-album assets, and each subfolder under `Special Folders` is migrated as an album except the localized Trash/Papelera folder, which is ignored in both CLI and Web Interface flows.
  - Added a unit test suite to validate the different modules of the tool, and created a GitHub Actions workflow to install dependencies, validate Python syntax, and execute those tests automatically on every `push` and `pull_request`.
    - Config Reader: tests configuration loading and environment variable overrides for configuration values.
    - PhotoMigrator CLI: tests argument parsing, normalization of exclusions, and validation of automatic-migration related flags.
    - Automatic Migration: tests helper functions, local-folder source/target dispatch, and Takeout preprocessing invocation before the shared migration flow.
    - Google Takeout: tests localized Takeout year-folder detection, forbidden special-folder path validation, and nested Takeout structure discovery.
    - Local Folder Takeout Layouts: tests GPTH-generated layouts including `Albums`, `Albums-shared`, `PARTNER_SHARED`, and `Special Folders`, ensuring correct album/non-album classification.
    - Local Folder Asset Deletion: tests `remove_assets()` analyzer initialization, supported refresh-method usage, extracted-date cleanup, and cache invalidation after file deletions.
    - Execution Modes: tests dispatch to the correct execution mode depending on the parsed arguments.
    - Exclusion Patterns: tests folder/file exclusion helpers and pattern matching behavior for local processing.
    - Immich Photos: tests asset type filtering and burst normalization / prioritization helper logic.
    - Immich Upload Streaming: tests multipart streaming uploads and sidecar attachment handling without using the deprecated `files` argument path.
    - Synology Photos: tests asset type/date/place filtering helper logic.
    - Logging: tests logger setup when log file generation is disabled.
    - Web Interface Path Restrictions: tests that web path sanitization enforces user-root restrictions while not treating exclusion patterns as filesystem paths.

#### 🚀 Enhancements:
  - Added fail-fast handling for `Automatic Migration` when `Google Photos` is used as `<SOURCE>`, returning a non-zero exit code with a clear workaround message after Google's Library API scope removal on April 1, 2025. Also stopped probing Google Photos read endpoints during login so upload-target flows can continue to use valid upload scopes. (Issue #1091).
  - Improved Automatic Migration in Web Interface mode so GPTH output is streamed into the browser log panel during Google Takeout preprocessing, while preserving the current CLI Live Dashboard behavior.
  - Updated GPTH from version 6.1.1 to version 6.1.5 which includes several enhancements and bug fixing.
  - Refactored Docker-related project structure by separating CLI assets into `docker-cli/` and Web Interface assets into `docker-web/`, and moved Docker deployment guides into `help/docker-deployments/` to keep CLI and Web deployment documentation clearly separated. (#1110, #1112)
  - Improved `Local Folder` handling in `Automatic Migration` so plain local-folder sources are treated without forcing managed subfolder creation, and destination `Albums-shared` is now created lazily only when a shared album actually needs to be downloaded there.
  - Improved `Local Folder` analyzer initialization in `Automatic Migration` so date extraction is skipped when no date filters are active, avoiding unnecessary per-file date analysis for plain local-folder to cloud migrations while still preserving date-based filtering behavior when `--filter-from-date` or `--filter-to-date` are used.
  - Expanded the default Synology thumbnail-file exclusion patterns across local-folder processing, uploads, and `Automatic Migration` to include `SYNOFILE_THUMB*`, `SYNOPHOTO_THUMB*`, and `SYNOVIDEO_THUMB*`, keeping thumbnail skips consistent across those local-source workflows.
  - Expanded the default local exclusion patterns to also skip `SYNOPHOTO_FILM*`, `Thumbs.db`, `ehthumbs.db`, `.DS_Store`, `._*`, and the `@Recycle` folder across local-folder processing, uploads, and `Automatic Migration`, and now print the effective `exclude-folders` / `exclude-files` lists in the startup `Global Settings` log block.

#### 🚀 GPTH Enhancements:

#### 6.1.2
  - Apple Live Photo pairs (HEIC + MP4) merged into motion JPEG — When --transform-pixel-mp jpg is active and a .HEIC/.HEIF file has a same-stem .MP4 companion in the same folder (as exported by Google Takeout for Apple Live Photos), the pair is merged into a single Google-style motion JPEG. Only storage-saver HEIC files are supported: Google re-encodes the still to JPEG bytes under a .HEIC extension, and the merge simply concatenates those bytes with the MP4. Original-quality (true) HEIC files cannot be merged — they are ISO-BMFF containers, and concatenating them with an MP4 produces a file ExifTool correctly rejects as MOV. Decoding true HEIC to JPEG requires a native libheif decoder which is not available in a Dart CLI context; both files are moved as-is.
  - When standard extension fixing renames a JPEG-encoded .HEIC to .jpg before Step 6 runs, the resulting .jpg + .mp4 pair is also recognised and merged (guarded by isMotionPhoto() to avoid double-merging files that are already motion photos).
  - Interactive mode log header now shows effective flags — The Args (argv): line in the log session header previously showed [] in interactive mode (because no CLI arguments are passed). It now shows the equivalent CLI flags that the user selected through the interactive prompts.

#### 6.1.3
  - Album symlinks for Pixel Motion Photos now use the correct extension — When a .MP/.MV file was transformed to .jpg or a still image, the moving step only updated the primary file's path. Secondary references to the same file (album copies used for shortcut/symlink creation) still referenced the old .MP path, so album symlinks ended up named PXL_….MP pointing at a .jpg file. All secondary references are now updated in-place immediately after each transform, ensuring album symlinks use the correct filename.
  - Apple Live Photo .jpg siblings no longer appear as orphaned MP4 companions — When a Google Storage-Saver HEIC was fixed to .jpg (e.g. PXL_20230101.heic → PXL_20230101.jpg), the companion .MP4 suppression logic only looked for a .heic sibling, not a .jpg sibling. The .MP4 was therefore not suppressed and ended up as a stray file in the output. The check now also looks for an existing .jpg sibling.
  - Pixel Motion Photo video-index lookup made more robust — The motion_photos package's getMotionVideoIndex() method searches for an ftyp mp42 MP4 header pattern and falls back to XMP parsing. For Pixel .MP.jpg files that use a different MP4 container brand or a slightly different XMP attribute format, both lookups returned null, causing extraction to fail. A pure-Dart fallback parser now reads the GCamera:MicroVideoOffset attribute directly from the JPEG XMP segment via regex, so extraction works reliably across all Pixel motion photo variants.
  - Still-mode output .jpg files are no longer detected as motion photos — The JPEG extracted from a Pixel .MP file contains a stale XMP segment with GCamera:MicroVideoOffset and MicroVideo markers. Because no MP4 is appended to the extracted still, the offset is invalid, but the motion_photos package does not bounds-check it — isMotionPhoto() returns true for the plain JPEG. GPTH now strips the entire XMP APP1 segment from the extracted bytes before writing the output file, so photo managers no longer misidentify the still as an unplayable motion photo.

#### 6.1.5
  - Fixed that existing DateTime values in Exif were overwritten with json values, even if they already existed. This caused local timestamps to be overwritten with UTC timestamps from the jsons. It introduces another read operation for all media files, but also it means that less exif data is being written, which should balance each other out performance wise.

#### 🐛 Bug fixes:
  - Fixed automatic migration CLI validation for Immich account 3 by restoring the missing `immich-photos-3` target/source alias in `--source` and `--target` accepted values.
  - Fixed Google Takeout GPTH execution flow to treat only exit code `0` as success, and to pre-stage files into the output folder before running GPTH `--fix` mode so later output-based steps operate on the actual processed files.
  - Fixed `Local Folder` asset deletion during `Automatic Migration` with `--move-assets true` so the analyzer refresh uses supported `FolderAnalyzer` methods, reapplies filters, recomputes folder sizes, and invalidates stale local caches after deletions. (Issue #1102).
  - Fixed Web Interface Google Takeout argument handling so `--google-output-folder-suffix` is treated as a plain suffix string instead of a path, preventing values like `processed` from being rewritten to a data-folder path.
  - Fixed `Automatic Migration` with plain `Local Folder` sources so instantiating the source no longer creates `Albums`, `Albums-shared`, or `ALL_PHOTOS` inside the input folder, root-level files are migrated as non-album assets, top-level subfolders are treated as albums, and `--move-assets true` no longer floods Web/CLI logs with repeated local-deletion refresh/progress noise that could overwrite the visible progress bar.
  - Fixed Docker Web Interface `healthcheck` so it always probes the internal container port `6078` instead of the published host `PORT`, preventing false unhealthy status when exposing the service on a different host port such as `6079`.

#### 📚 Documentation:
  - Corrected the documentation to align argument names, defaults, examples, and feature descriptions with the current code behavior.
  - Corrected `README.md` to align Docker-related file names and references with the current codebase and deployment files.
  - Reorganized Docker documentation and launcher assets into separate `docker-cli/` and `docker-web/` folders, clarified CLI vs Web image usage, and fixed the Windows batch launcher/docs to use the published Docker image instead of the unpublished Windows image. (#1110, #1112)
  - Updated Screenshots.
  - Added a new Web Help section `11. Docker Deployment` that summarizes and links the two supported Docker deployment modes: Web Interface and CLI Interface.
  - Updated documentation with all changes.

---

## Release: v4.0.0
### Release Date: 2026-03-28
   
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
  - Updated GPTH from version 5.0.5 to version 6.1.1 which includes several enhancements and bug fixing.

#### 🚀 GPTH Enhancements:

#### 6.1.1
  - Added `archiver` as correct french translation of archive.

#### 6.1.0
  - Added `--all-photos-dir` CLI option to customize the non-album output directory name (default remains `ALL_PHOTOS`). Set it to an empty string (`--all-photos-dir ""`) to remove that extra directory level entirely. This makes album links more portable when migrating into existing folder structures.
  - Added `--hardlink` flag (Windows only) for `shortcut` and `reverse-shortcut` album modes. When enabled, GPTH creates hard links instead of symlinks for shortcut entries.
  - `--transform-pixel-mp` now accepts an explicit output format: `mp4`, `jpg`, or `still`.
  - Step 6 Pixel motion-photo transformation now supports two modes:
    - `mp4`: rename `.MP` / `.MV` primary files to `.mp4`.
    - `jpg`: create motion `.jpg` files from Pixel motion photos.
    - `still`: keep only a still image (prefers sidecar `*.MP.jpg`, otherwise extracts embedded JPEG) and remove related `.MP` / `.MV` source files.
  - ⚠️ `--transform-pixel-mp jpg` is currently **preview/experimental** and may be unstable depending on source file structure.
  - **Step 1: Pixel Motion Photo files (.MP, .MV) no longer unconditionally converted to .mp4** — Pixel Motion Photo files have `video/mp4` MIME type but `.MP`/`.MV` extensions. Previously, Step 1 unconditionally renamed them to `.mp4` due to the MIME/extension mismatch, making the `--transform-pixel-mp` flag ineffective. Step 1 now preserves `.MP`/`.MV` files, deferring to Step 6 which respects the flag: with `--transform-pixel-mp`, they are converted to `.mp4`; without the flag, they are left as-is.

#### 6.0.0
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

#### 5.1.1
  - Fixed a bug where non-english year folder names could cause them to be classified as albums
  - Fixed ExifTool failing with `Bad format (282) for InteropIFD entry` or `Truncated InteropIFD directory` errors on certain images (Google Photos edited files with `-edited` suffix, WhatsApp images). Root cause: the UTC timezone offset tags (`OffsetTime*`) introduced in v5.0.9 trigger ExifTool's IFD traversal, which aborts on files with a corrupted InteropIFD structure. Fix: when either error is detected, the offset tags are stripped and the write is retried — date and GPS data are still written successfully, matching v5.0.8 behaviour for these files. (#108)
  - Improved error messaging for InteropIFD failures: the per-file warning now correctly distinguishes between a UTC timezone offset tag failure (date was already written natively — no data loss) and an actual date metadata write failure. A step-level summary is printed when one or more files are affected, with a description and the total count of affected files.

#### 5.1.0
  - Upgraded mime package to 2.0.0 (contains bugfix)
  - Added german and spanish "Photos from" localization.
  - Fixed an issue with MacOS unicode normalisation (#99)
  - Fixed a possible endless loop (#102)
  - Made Exiftool discovery on Windows more robust when installed via chocolatey and not added to PATH.
  - Added -editada suffix for spanish
  - bumped some dependencies
  - Will not allow any mode which requires symlink on a filesystem which does not support symlinks (#105)

#### 5.0.9
  - Fixed a UTC conversion bug
  - Fixed that geodata was removed from exif
  - fixed a bug where a path join used a unix path seperator instead of being platform agnostic.

#### 5.0.8
  - Updated upstream library to image 4.7.2 which contains fixes to the native writeExif() method.

#### 5.0.7
  - ZIP extraction no longer deletes an existing extraction directory. GPTH Neo now refuses to extract into a non-empty folder to prevent accidental deletion of unrelated files.
  - Interactive mode: Added an explicit **DANGER** warning before confirming output directory cleanup (deletes recursively inside the chosen output folder).
  - Restore truncated media filenames from JSON sidecars (uses the JSON `title` field) after date extraction, renaming both the media file and its JSON metadata so later steps use the original name.

#### 5.0.6
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
  - Fixed Web Interface path validation to reject using the user's root `DATA_DIR`/`VOLUMES_DIR` directly as any input/output path, requiring a subfolder and showing a warning dialog before execution.
  - Fixed local album linking in `Automatic Migration`/`LocalFolder` targets by using the correct exclusion helper and caching the created album path instead of the resolved source path, avoiding `Album Push Fail` errors such as `'FolderAnalyzer' object has no attribute '_should_exclude'`.
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
  
#### 🐛 Bug fixes:
  - Fixed stream Immich multipart upload to avoid OOM.

---

## Release: v3.7.0
### Release Date: 2026-01-09
    
#### 🚀 Enhancements:
  - Most of the Code Translated into English.

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
