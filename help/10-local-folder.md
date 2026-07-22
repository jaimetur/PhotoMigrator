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
