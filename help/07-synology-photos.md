# 📸 Synology Photos Management

From version 2.0.0 onwards, the Tool can connect to your Synology NAS and login into Synology Photos App with your credentials. 

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

You can apply different filters on all above features to filter assets from Synology Photos.  

The available filters are: 
   - **by Type:**
     - argument: `-type, --filter-by-type`
       - Valid values are [`image`, `video`, `all`]
   - **by Dates:**
     - arguments:
       - `-from, --filter-from-date`
       - `-to, --filter-to-date`
     - Valid values are in one of those formats: 
       - `dd/mm/yyyy`
       - `dd-mm-yyyy`
       - `yyyy/mm/dd`
       - `yyyy-mm-dd`
       - `mm/yyyy`
       - `mm-yyyy`
       - `yyyy/mm`
       - `yyyy-mm`
       - `yyyy`
   - **by Country:**
     - argument: `-country, --filter-by-country`
       - Valid values are any existing country in the `<SOURCE>` client.
   - **by City:**
     - argument: `-city, --filter-by-city`
       - Valid values are any existing city in the `<SOURCE>` client.
   - **by Person:**
     - argument: `-person, --filter-by-person`
       - Valid values are any existing person in the `<SOURCE>` client.

The credentials/API Key need to be loaded from the `Config.ini` file that  have this format:

#### Example 'Config.ini' for Immich Photos:

```
# Configuration for Synology Photos
[Synology Photos]
SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
SYNOLOGY_USERNAME_3         = username_3                                    # Account 3: Your username for Synology Photos
SYNOLOGY_PASSWORD_3         = password_3                                    # Account 3: Your password for Synology Photos
```

> [!NOTE]
> To use all these features, it is mandatory to use the argument _**`--client=synology`**_ to specify Synology Photos as the service that you want to connect.  
> 
> If you want to connect to an account ID different that 1 (suffixed with _2 or _3) you can use the argument _**`-id, -account-id=[1-3]`**_ to specify the account 2 or 3 as needed. 

> [!TIP]
> In Docker/Compose/Kubernetes, you can override these settings without editing `Config.ini` by using environment variables with the same key names, for example `SYNOLOGY_URL`, `SYNOLOGY_USERNAME_1`, `SYNOLOGY_PASSWORD_1`.
> Docker-secret style variables such as `SYNOLOGY_PASSWORD_1_FILE=/run/secrets/synology_password_1` are also supported.
> Runtime precedence is: environment variable > `Config.ini` > template default.

> [!IMPORTANT]  
> If your Synology Photo Account requires 2FA Authentication, you must use the argument _**`-OTP, --one-time-password`**_ in order to enable the OTP Token request during authentication process. 

> [!NOTE]
> For compiled binaries, macOS now uses `PhotoMigrator.command`. Linux and Synology SSH continue using `PhotoMigrator.bin`. Replace the binary name accordingly when following the CLI examples below.


## Upload Albums (from Local Folder) into Synology Photos:
- **From:** v2.0.0 
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-uAlb, --upload-albums \<ALBUMS_FOLDER>`**_
  - Where `<ALBUMS_FOLDER>` is the folder that contains all the Albums that you want to upload,
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will create one Album per each Subfolder found in \<ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.
  - By default only exact existing album names are reused and newly created albums keep the original source name.
  - Add `--prefer-canonical-album-names` if you want new destination albums to be created directly with the preferred clean keeper name.
  - Add `--consolidate-similar-albums` to also treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - On Synology, when these behaviors are active, PhotoMigrator prefers the clean keeper name without a numeric suffix and with spaces instead of underscores. If needed, it merges the assets from the redundant variants into that keeper and then removes the redundant albums after the consolidation is confirmed.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --upload-albums ./My_Albums_Folder
  ./PhotoMigrator.bin --client=synology --upload-albums ./My_Albums_Folder --prefer-canonical-album-names --consolidate-similar-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder `./My_Albums_Folder` and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder
  If the target already contains `Album_1`, `Album (2)`, and `Album_5`, uploading `Album` with `--consolidate-similar-albums` consolidates all those variants into the preferred keeper `Album`.
  If the target does not contain any `Album*` variant and you upload `Album_1`, `--prefer-canonical-album-names` creates `Album` directly.
  If you enable only `--prefer-canonical-album-names` and the target already contains an exact `Album`, uploading `Album_1` reuses `Album`.
  

## Download Albums from Synology Photos:
- **From:** v2.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-dAlb, --download-albums <ALBUMS_NAME>`**_ in combination with the argument _**`-o, --output-folder <OUTPUT_FOLDER>`**_ (mandatory argument for this feature)
  - Where,
  - `<ALBUMS_NAME>` is a list of Albums names that you want to download.
  - `<OUTPUT_FOLDER>` is the folder where you want to download the Albums.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and Download those Album(s) whose name is in `<ALBUMS_NAME>` to the folder `<OUTPUT_FOLDER>`.
  - To download ALL Albums use `ALL` as `<ALBUMS_NAME>`.
  - To download all albums mathing any pattern you can use patterns in `<ALBUMS_NAME>`, i.e: `--download-albums 'dron*'` to download all albums starting with the word 'dron' followed by other(s) words.
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: `--download-albums 'album1', 'album2', 'album3'`.
  - For shared/collaborative Synology albums, PhotoMigrator now resolves the shared-album access details before listing album contents. This avoids cases where only the current user's contributed items were visible or where the tool logged `Failed to list photos in the album ...` for albums shared across multiple Synology users.
- **Example of use:**
  ```
  ./PhotoMigrator.bin `--client=synology --download-albums "Album 1", "Album 2", "Album 3"`
  ```
  With this example, the Tool will connect to your Synology Photos account and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of `Synology_Photos_Albums` folder

> [!WARNING]  
> \<ALBUMS_NAME> should exist within your Synology Photos Albums database, otherwise it will not extract anything. 


## Upload All (from Local Folder) into Synology Photos:
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-uAll, --upload-all \<INPUT_FOLDER>`**_
  - Where `<INPUT_FOLDER>` is the folder that contains all the assets that you want to upload.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will upload all the assets contained in \<INPUT_FOLDER> that are supported by Synology Photos.  
  - If you want to create Albums for some specific subfolders you have two options:
    1. Move all the Albums subfolders into a `<INPUT_FOLDER>/<ALBUMS_FOLDER>`, in this way the Tool will consider all the subfolders inside as an Album, and will create an Album in Synology Photos with the same name as the subfolder, associating all the assets inside to it.
    2. Use the complementary argument _**`-AlbFolder, --albums-folders \<ALBUMS_FOLDER>`**_, in this way the Tool will create Albums also for each subfolder found in `<ALBUMS_FOLDER>` (apart from those found inside `<INPUT_FOLDER>/Albums`)
  - Add `--prefer-canonical-album-names` if you want new destination album names inside this flow to be normalized to the preferred clean keeper.
  - Add `--consolidate-similar-albums` if you want album uploads inside this flow to treat equivalent names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` as the same reusable album family.
  - On Synology, these behaviors can be enabled independently or together. Consolidation merges redundant variants into the preferred clean keeper and removes the old variants after the merge is confirmed.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --upload-all ./MyLibrary
  ./PhotoMigrator.bin --client=synology --upload-all ./MyLibrary --prefer-canonical-album-names --consolidate-similar-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder ./MyLibrary and will upload all supported assets found on it, creating a new Album per each subfolder found within `./MyLibrary/Albums` folder.


## Download All from Synology Photos:
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-dAll, --download-all \<OUTPUT_FOLDER>`**_
  - Where `<OUTPUT_FOLDER>` is the folder where you want to download all your assets.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and will download all the Album and Assets without Albums into the folder `<OUTPUT_FOLDER>`.
  - All Albums will be downloaded within a subfolder of `<OUTPUT_FOLDER>/Albums` with the same name of the Album and all files will be flattened into it.
  - Assets with no Albums associated will be downloaded within a subfolder called `<OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>` and will have a `year/month` structure inside.
  - Shared/collaborative albums are now handled more robustly as well: when Synology omits the shared `passphrase` from the album list response, PhotoMigrator performs an extra album-details lookup so it can still enumerate and migrate the full album membership instead of silently falling back to only the current user's visible items.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --download-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Synology Photos account and download ALL your library into the local folder ./MyLibrary.
  

## Remove All Assets from Synology Photos:
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-rAll, --remove-all-assets`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url.
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove ALL the assets and Albums found.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-all-assets
  ```
  With this example, the Tool will connect to Synology Photos account and will remove all assets found (including Albums).

> [!CAUTION]  
> This process is irreversible and will clean all from your Synology Photos account. Use it if you are completely sure of what you are doing.
  

## Remove All Albums from Synology Photos:
- **From:** v3.0.0 
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-rAllAlb, --remove-all-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all the Albums found.
  - `-createdFrom, --created-from` and `-createdTo, --created-to` optionally filter by album creation date. The lower and upper bounds are inclusive; either boundary can be omitted, and date formats `YYYY`, `YYYY-MM`, and `YYYY-MM-DD` are accepted.
  - Optionally ALL the Assets associated to each Album can be removed If you also include the complementary argument _**`-rAlbAsset, --remove-albums-assets`**_
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-all-albums --remove-albums-assets
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Albums found (including all the assets contained on them, because we are using the complementary argument).

> [!CAUTION]  
> This process is irreversible and will clean all the Albums (and optionally also all the assets included) from your Synology Photos account. Use it if you are completely sure of what you are doing.


## Remove Albums by Name Pattern from Synology Photos:
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-albums \<ALBUMS_NAME_PATTERN>`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Albums whose name matches with the provided pattern.
  - The remove pattern can be plain text, a wildcard expression (for example `*Temp*` or `Temp*`), or a regular expression.
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
  - Optionally ALL the Assets associated to each removed Album can be removed If you also include the complementary argument _**`-rAlbAsset, --remove-albums-assets`**_
  - If you also include _**`--preview-album-actions`**_ then the matching albums will be listed and the tool will ask for confirmation before deleting them.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-albums "Temp" --preview-album-actions
  ./PhotoMigrator.bin --client=synology --remove-albums "*Temp*" --preview-album-actions
  ./PhotoMigrator.bin --client=synology --remove-albums "\d{4}-\d{2}-\d{2}" --remove-albums-assets
  ./PhotoMigrator.bin --client=synology --remove-albums "*Temp*" --created-from 2024-01-01 --created-to 2024-12-31
  ```
  With these examples, the Tool can remove albums by literal text, simple wildcard patterns, or regular expressions. When `--preview-album-actions` is used, it first shows the affected albums and asks for confirmation before proceeding.

> [!CAUTION]  
> This process is irreversible and will remove all the Albums (and optionally also all the assets included) whose name matches with the provided pattern from your Synology Photos account. Use it if you are completely sure of what you are doing.
      

## Rename Albums by Name Pattern from Synology Photos:
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--rename-albums \<ALBUMS_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will rename all Albums whose name matches with the provided pattern.
  - The rename pattern can be plain text (for example `--`), a wildcard expression (for example `*--*` or `--*`), or a regular expression.
  - If you also include _**`--preview-album-actions`**_ then the matching albums will be listed and the tool will ask for confirmation before renaming them.
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be renamed.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --rename-albums "--" "-" --preview-album-actions
  ./PhotoMigrator.bin --client=synology --rename-albums "--", "-"
  ./PhotoMigrator.bin --client=synology --rename-albums "*--*", "-"
  ./PhotoMigrator.bin --client=synology --rename-albums "\d{4}-\d{2}-\d{2}", "DATE"
  ```
  With these examples, the Tool can replace literal text such as double dashes, use simple wildcards to target leading or inner matches, or apply a regular-expression replacement such as turning "2023-08-15 - Vacation photos" into "DATE - Vacation photos".


## Remove Empty Albums from Synology Photos:
- **From:** v2.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-empty-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Empty Albums found.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-empty-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Empty Albums found.


## Remove Duplicates Albums from Synology Photos:
- **From:** v2.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-duplicates-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Duplicates Albums found except the first one (but will not remove the assets associated to them, because they will still be associated with the first Album).  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-duplicates-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Duplicates Albums found except the first one.


## Remove Duplicates Assets from Synology Photos:
- **From:** v4.6.0
- **Usage:**
  - Set Synology as the client using _**`--client=synology`**_.
  - Use _**`--remove-duplicates-assets`**_.
  - Select the asset to retain with `more-people/tags-then-oldest`, `more-people/tags-then-newest`, `newest`, or `oldest`. The people/tags-first variants prefer the largest available distinct-person count, then distinct tag count, then use their named chronological tie breaker. The default is `newest`.
- **Pre-Requisites:**
  - Configure `Config.ini` with a Synology account that can list and delete assets.
  - Check that the account has access to the Photo Library that will be scanned.
- **Explanation:**
  - The Tool retrieves the Synology library in paginated requests and groups physical assets with the same exact filename and file size.
  - `newest` and `oldest` use the timestamp returned by Synology for the asset. If an asset has no usable timestamp, it is treated as older than assets with a valid timestamp.
  - Before deleting anything, the Tool logs every duplicate group, its proposed keeper, and the IDs selected for deletion. With normal confirmation enabled, it waits for confirmation after this preview. Use _**`--request-user-confirmation=false`**_ only for unattended executions.
  - Synology does not expose a portable metadata-merge operation for this flow. Album membership, people, labels, favorites, ratings, descriptions, and other server metadata are not merged; the module deletes only the redundant physical assets after confirmation.
- **Examples:**
  ```
  ./PhotoMigrator.bin --client=synology --remove-duplicates-assets
  ./PhotoMigrator.bin --client=synology --remove-duplicates-assets --dup-asset-keeper oldest
  ```

> [!CAUTION]
> This process permanently deletes redundant assets after confirmation. Review the logged groups and proposed keeper before continuing.


## Merge Duplicates Albums from Synology Photos:
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--merge-duplicates-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Duplicates Albums found except the most relevant one (with highest number of assets) and will transfer all the assets associated to the other albums into the main one.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be merged.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --merge-duplicates-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Duplicates Albums found except the first one transferring all the assets from the removed albums into the main one.


## Consolidate Albums Names from Synology Photos:
- **From:** v4.5.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--consolidate-albums-names`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url.
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will scan the albums that already exist in the cloud looking for equivalent album-name families.
  - It uses the same family-detection logic as _**`--consolidate-similar-albums`**_, so names such as `Album`, `Album_1`, `Album (2)`, `New_Album`, `New Album`, and `New_Album 1` are treated as the same family.
  - Date-led families accept `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` prefixes, with dots, underscores, hyphens, long dashes, or spaces as separators. Different years or conflicting month/day values remain separate. The most precise compatible date is retained only when at least 95% of that album's assets fall inside its date range; otherwise the compatible broader date prefix is the keeper.
  - End-truncated names are considered only when their shared title prefix has at least two distinct words and every candidate has the same dominant asset year (more than half of its dated assets). A bare date is never treated as a truncated title. A plain name is never merged with a terminal `Shared`, `Share`, `Public`, `Público`, `X`, or truncated equivalent; two variants that both carry that suffix may be merged. When variants differ only by a terminal `Videos`, the non-`Videos` album is retained. A terminal date already covered by the leading date or leading year range is redundant, so the version without it is retained.
  - Albums with up to the configurable `--small-album-max-assets` limit (default `3`) can also be consolidated into a larger similarly named keeper when their complete capture-date range fits within the keeper range. The limit is used only when `--try-small-albums-grouping` is enabled.
  - Equivalent-name, date-prefix, truncated-name, and small-album matching are independently enabled by default through `--try-equivalent-albums-grouping`, `--try-date-prefix-albums-grouping`, `--try-truncated-albums-grouping`, and `--try-small-albums-grouping`; use the corresponding `--no-...` option to skip one rule.
  - Assets from redundant variants are reassigned directly in Synology Photos to the preferred keeper album without uploading any new asset.
  - Once the reassignment is confirmed, the redundant album variants are removed.
  - _**`--preview-album-actions`**_ (enabled by default) displays a table with the group, match rule, keeper, albums to merge, and comments explaining the applied keeper decision. With _**`--request-user-confirmation=true`**_ (the default), the table is shown and the tool asks for confirmation before consolidating them.
- **Example of use:**
  ```
  ./PhotoMigrator.bin --client=synology --consolidate-albums-names --preview-album-actions
  ```

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
