# Local Folder Management

The **Local Folder** tab exposes the same library-management modules as the cloud-service tabs, but operates on a managed folder on disk. It is selected with `--client=local-folder` and requires `--local-folder`.

The managed root uses this layout:

```text
<LOCAL_FOLDER>/
  Albums/<album name>/
  No_Albums/<year>/<month>/
```

Album entries link to their physical files in `No_Albums` where the filesystem permits symbolic links. This keeps a file physical only once while allowing it to belong to albums.

## Examples

Upload a complete local library:

```bash
PhotoMigrator --client local-folder --local-folder ./ManagedLibrary --upload-all ./SourceLibrary
```

Upload directories as albums:

```bash
PhotoMigrator --client local-folder --local-folder ./ManagedLibrary --upload-albums ./AlbumsToImport
```

Download the managed library:

```bash
PhotoMigrator --client local-folder --local-folder ./ManagedLibrary --download-all ./ExportedLibrary
```

All common album modules are available: upload/download albums, upload/download all, rename/remove albums, remove empty or duplicate albums, consolidate album names, remove all assets, and remove duplicate physical assets. `--dup-asset-keeper` is required for duplicate-asset removal.

`--local-folder` identifies the managed library; upload arguments continue to identify the source folder, and download arguments continue to identify the destination folder.

## Consolidate Albums Names

`--consolidate-albums-names` applies the same album-family rules used by the cloud services without uploading media: canonical equivalent names, compatible `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` prefixes, and guarded end-truncated names. Date components can be separated by dots, underscores, hyphens, long dashes, or spaces. A specific date remains the keeper only when at least 95% of its album assets are inside that date range; otherwise the compatible broader date is retained.

Truncated names require at least two distinct shared title words and the same dominant asset year. Bare dates do not qualify as titles. Plain names are kept separate from `Shared`, `Share`, `Public`, `Público`, `X`, and partial forms of those suffixes; if only `Videos` differs, the non-`Videos` name is the keeper. The default preview table shows the group, match rule, keeper, candidates to merge, and `Assets Date Considered`; confirmation is requested by default.
