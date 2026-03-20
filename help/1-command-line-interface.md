# 💻 Command Line Interface (CLI)
This section shows how to use the Command Line Interface (CLI) for this Tool.

Most of the argument can be given with two formats:
- Short format: '-' followed by the short name
- Long format: '--' followed by the long name

Both methods are exactly the same, long name is more convenient in some cases to remember better what the command does, while short format is easier to write

Some arguments must be followed by a value. This value can be separated from the argument by '=' or just by space ' ', both ways are valid.

- Example 1: Following commands are exactly the same
  - -country Spain
  - -country=Spain
  - --filter-by-country Spain
  - --filter-by-country=Spain
    

- Example 2: Following commands are exactly the same
  - -source synology-photos
  - -source=synology-photos

## Command Line Syntax:
Below you can find the list of all commands that the Tool can receive to execute any of the implemented features:

```
---------------------------------------------------------------------------------------------------------
usage: PhotoMigrator [-h] [-v] [-config <CONFIGURATION_FILE>] [-noConfirm] [-noLog]
                     [-logLevel =[VERBOSE, DEBUG, INFO, WARNING, ERROR]] [-logFormat =[LOG, TXT, ALL]]
                     [-dateSep <DATE_SEPARATOR>] [-rangeSep <RANGE_OF_DATES_SEPARATOR>] [-fnAlbums <ALBUMS_FOLDER>]
                     [-fnNoAlbums <NO_ALBUMS_FOLDER>] [-fnLogs <LOG_FOLDER>] [-fnDuplicat <DUPLICATES_OUTPUT_FOLDER>]
                     [-fnExtDates <EXTRACTED_DATES_FOLDER>] [-exeGpthTool <GPTH_PATH>] [-exeExifTool <EXIFTOOL_PATH>]
                     [-i <INPUT_FOLDER>] [-o <OUTPUT_FOLDER>] [-client = ['google-takeout', 'google-photos', 'synology', 'immich', 'nextcloud']]
                     [-id [= [1-3]]]
                     [-from <FROM_DATE>] [-to <TO_DATE>] [-type = [image,video,all]]
                     [-country <COUNTRY_NAME>] [-city <CITY_NAME>] [-person <PERSON_NAME>]
                     [-AlbFolder [<ALBUMS_FOLDER> ...]] [-rAlbAsset]
                     [-source <SOURCE>] [-target <TARGET>]
                     [-move [= [true,false]]] [-dashboard [= [true,false]]] [-parallel [= [true,false]]]
                     [-gTakeout <TAKEOUT_FOLDER>] [-gofs <SUFFIX>]
                     [-gafs ['flatten', 'year', 'year/month', 'year-month']]
                     [-gnas ['flatten', 'year', 'year/month', 'year-month']] [-gics] [-gnsa] [-grdf] [-graf] [-gsef]
                     [-gsma] [-gSkipGpth] [-gSkipPrep] [-gSkipPost] [-gKeepTakeout]
                     [-gpthInfo [= [true,false]]] [-gpthError [= [true,false]]] [-gpthNoLog]
                     [-uAlb <ALBUMS_FOLDER>] [-dAlb <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                     [-uAll <INPUT_FOLDER>] [-dAll <OUTPUT_FOLDER>]
                     [-renAlb <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>] [-rAlb <ALBUMS_NAME_PATTERN>]
                     [-rAllAlb] [-rAll] [-rEmpAlb] [-rDupAlb] [-mDupAlb] [-rOrphan] [-OTP]
                     [-fixSym <FOLDER_TO_FIX>] [-renFldcb <ALBUMS_FOLDER>]
                     [-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                     [-procDup <DUPLICATES_REVISED_CSV>]

PhotoMigrator v3.8.0 - 2026-03-17

          Multi-Platform/Multi-Arch tool designed to Interact and Manage different Photo Cloud Services
          such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

          ©️ 2024-2026 by Jaime Tur (@jaimetur)

options:

-h           ; --help
               show this help message and exit
-v           ; --version
               Show the Tool name, version, and date, then exit.
-config      ; --configuration-file <CONFIGURATION_FILE>
               Specify the file that contains the Configuration to connect to the different Photo Cloud Services.
-noConfirm   ; --no-request-user-confirmation
               Do not request user confirmation before executing any feature.
-noLog       ; --no-log-file
               Skip saving output messages to execution log file.
-logLevel    ; --log-level =[VERBOSE, DEBUG, INFO, WARNING, ERROR]
               Specify the log level for logging and screen messages.
-logFormat   ; --log-format =[LOG, TXT, ALL]
               Specify the log file format.
-dateSep     ; --date-separator <DATE_SEPARATOR>
               Specify Date Separator used by feature `Auto-Rename Albums Content Based`.
-rangeSep    ; --range-separator <RANGE_OF_DATES_SEPARATOR>
               Specify Range of Dates Separator used by feature `Auto-Rename Albums Content Based`.
-fnAlbums    ; --foldername-albums <ALBUMS_FOLDER>
               Specify the folder name to store all your processed photos associated to any Album.
-fnNoAlbums  ; --foldername-no-albums <NO_ALBUMS_FOLDER>
               Specify the folder name to store all your processed photos (including those associated to Albums).
-fnLogs      ; --foldername-logs <LOG_FOLDER>
               Specify the folder name to save the execution Logs.
-fnDuplicat  ; --foldername-duplicates-output <DUPLICATES_OUTPUT_FOLDER>
               Specify the folder name to save the outputs of 'Find Duplicates' Feature.
-fnExtDates  ; --foldername-extracted-dates <EXTRACTED_DATES_FOLDER>
               Specify the folder name to save the Metadata outputs of 'Extracted Dates'.
-exeGpthTool ; --exec-gpth-tool <GPTH_PATH>
               Specify an external version of GPTH Tool binary.
               PhotoMigrator contains an embedded version of GPTH Tool, but if you want to use a different version, you
               can use this argument.
-exeExifTool ; --exec-exif-tool <EXIFTOOL_PATH>
               Specify an external version of EXIF Tool binary.
               PhotoMigrator contains an embedded version of EXIF Tool, but if you want to use a different version, you
               can use this argument.


GENERAL ARGUMENTS:
------------------
Following general arguments have different purposses depending on the Execution Mode.

-i           ; --input-folder <INPUT_FOLDER>
               Specify the input folder that you want to process.
-o           ; --output-folder <OUTPUT_FOLDER>
               Specify the output folder to save the result of the processing action.
-client      ; --client = ['google-takeout', 'google-photos', 'synology', 'immich', 'nextcloud']
               Set the client to use for the selected feature.
-id          ; --account-id = [1-3]
               Set the account ID for Synology Photos, Immich Photos, NextCloud Photos or Google Photos (default: 1). This value must exist in the
               Config.ini as suffix of USERNAME/PASSWORD or API_KEY_USER.
               Example for Immich ID=2:
                 IMMICH_USERNAME_2/IMMICH_PASSWORD_2 or IMMICH_API_KEY_USER_2 entries must exist in Config.ini.
-from        ; --filter-from-date <FROM_DATE>
               Specify the initial date to filter assets in the different Photo Clients.
-to          ; --filter-to-date <TO_DATE>
               Specify the final date to filter assets in the different Photo Clients.
-type        ; --filter-by-type = [image,video,all]
               Specify the Asset Type to filter assets in the different Photo Clients. (default: all)
-country     ; --filter-by-country <COUNTRY_NAME>
               Specify the Country Name to filter assets in the different Photo Clients.
-city        ; --filter-by-city <CITY_NAME>
               Specify the City Name to filter assets in the different Photo Clients.
-person      ; --filter-by-person <PERSON_NAME>
               Specify the Person Name to filter assets in the different Photo Clients.
-AlbFolder   ; --albums-folders <ALBUMS_FOLDER>
               If used together with '-uAll, --upload-all', it will create an Album per each subfolder found in
               <ALBUMS_FOLDER>.
-rAlbAsset   ; --remove-albums-assets
               If used together with '-rAllAlb, --remove-all-albums' or '-rAlb, --remove-albums', it will also remove
               the assets (photos/videos) inside each album.


AUTOMATIC MIGRATION PROCESS:
----------------------------
Following arguments allow you execute the Automatic Migration Process to migrate your assets from one Photo Cloud
Service to other, or from two different accounts within the same Photo Cloud service.

-source      ; --source <SOURCE>
               Select the <SOURCE> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from
               the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums).

               Possible values:
                 ['synology', 'immich', 'nextcloud', 'google-photos']-[id] or <INPUT_FOLDER>
                 [id] = [1, 2] select which account to use from the Config.ini file.

                Examples:
                  --source=immich-1   -> Select Immich Photos account 1 as Source.
                  --source=synology-2 -> Select Synology Photos account 2 as Source.
                  --source=nextcloud-3 -> Select NextCloud Photos account 3 as Source.
                  --source=/home/local_folder -> Select this local folder as Source.
                  --source=/home/Takeout -> Select this Takeout folder as Source. (zipped and unzipped format supported)
-target      ; --target <TARGET>
               Select the <TARGET> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from
               the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums).

               Possible values:
                 ['synology', 'immich', 'nextcloud', 'google-photos']-[id] or <OUTPUT_FOLDER>
                 [id] = [1, 2] select which account to use from the Config.ini file.

                Examples:
                  --target=immich-1   -> Select Immich Photos account 1 as Target.
                  --target=synology-2 -> Select Synology Photos account 2 as Target.
                  --target=nextcloud-1 -> Select NextCloud Photos account 1 as Target.
                  --target=/home/local_folder -> Select this local folder as Target.
-move        ; --move-assets = [true,false]
               If this argument is present, the assets will be moved from <SOURCE> to <TARGET> instead of copied.
               (default: False).
-dashboard   ; --dashboard = [true,false]
               Enable or disable Live Dashboard feature during Automated Migration job. This argument only applies if
               both '--source' and '--target' arguments are given.
               (default: True).
-parallel    ; --parallel-migration = [true,false]
               Select Parallel/Sequential migration during Automatic Migration job.
               This argument only applies if both '--source' and '--target' arguments are given.
               (default: True).


GOOGLE PHOTOS TAKEOUT MANAGEMENT:
---------------------------------
Following arguments allow you to interact with Google Photos Takeout Folder.
In this mode, you can use more than one optional arguments from the below list.
If only the argument -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the Tool will use the default values
for the rest of the arguments for this extra mode.

-gTakeout    ; --google-takeout <TAKEOUT_FOLDER>
               Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata and organize assets inside it.
               If any Zip file is found inside it, the Zip will be extracted to the folder
               '<TAKEOUT_FOLDER>_unzipped_<TIMESTAMP>', and that folder will be used as input.
               The processed Takeout will be saved into the folder '<TAKEOUT_FOLDER>_processed_<TIMESTAMP>'.
               This argument is mandatory to run the Google Takeout Processor feature.
-gofs        ; --google-output-folder-suffix <SUFFIX>
               Specify the suffix for the output folder. Default: 'processed'
               The output folder will have the same name as input folder followed by this suffix and the execution
               timestamp.
-gafs        ; --google-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
               Specify the folder structure type for each Album folder (Default: 'flatten').
-gnas        ; --google-no-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
               Specify the folder structure type for '<NO_ALBUMS_FOLDER>' folders (Default: 'year/month').
-gics        ; --google-ignore-check-structure
               Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc.), and fix all
               files found on <TAKEOUT_FOLDER> trying to guess timestamps.
-gnsa        ; --google-no-symbolic-albums
               Duplicate album assets instead of creating symlinks to the original asset within <NO_ALBUMS_FOLDER>.
               (Makes your output portable but requires more HDD space).
               IMPORTANT: This can considerably increase output size, especially if you have many albums.
               Example: if one asset belongs to 3 albums, you will end up with 4 copies (original + 3).
-grdf        ; --google-remove-duplicates-files
               Remove duplicate files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.
-graf        ; --google-rename-albums-folders
               Rename album folders in <OUTPUT_TAKEOUT_FOLDER> based on content dates after fixing them.
-gsef        ; --google-skip-extras-files
               Skip processing extra photos such as -edited, -effects photos.
-gsma        ; --google-skip-move-albums
               Skip moving albums to '<ALBUMS_FOLDER>'.
-gSkipGpth   ; --google-skip-gpth-tool
               Skip processing files with GPTH Tool.
               CAUTION: NOT RECOMMENDED (core of the Google Takeout process). Use only for testing.
-gSkipPrep   ; --google-skip-preprocess
               Skip pre-process Google Takeout which includes:
                 1) Clean Takeout folder
                 2) Fix MP4/Live Picture associations
                 3) Fix truncated filenames/extensions
               This is important for high accuracy. If you already pre-processed the same Takeout using '-gKeepTakeout,
               --google-keep-takeout-folder', you can skip it.
-gSkipPost   ; --google-skip-postprocess
               Skip post-process Google Takeout which includes:
                 1) Copy/Move files to output folder
                 2) Sync MP4 files associated to Live pictures with associated HEIC/JPG
                 3) Separate Albums folders vs original assets
                 4) Auto rename album folders based on content dates
                 5) Calculate statistics and compare with original Takeout
                 6) Organize assets by year/month
                 7) Detect and remove duplicates
                 8) Remove empty folders
                 9) Count albums
                10) Clean final media library
               Not recommended to skip.
-gKeepTakeout; --google-keep-takeout-folder
               Keep an untouched copy of original Takeout (requires double space).
               TIP: If <TAKEOUT_FOLDER> contains the original zip files, you will preserve them anyway.
-gpthInfo    ; --show-gpth-info = [true,false]
               Enable or disable Info messages during GPTH Processing. (default: True).
-gpthError   ; --show-gpth-errors = [true,false]
               Enable or disable Error messages during GPTH Processing. (default: True).
-gpthNoLog   ; --gpth-no-log
               Skip saving GPTH log messages into output folder.


SYNOLOGY/IMMICH/NEXTCLOUD/GOOGLE PHOTOS MANAGEMENT:
----------------------------------
To use following features, it is mandatory to use the argument '--client=[synology, immich, nextcloud, google-photos]' to specify which Photo
Service do you want to use.

You can optionally use the argument '--id=[1-3]' to specify the account id for a particular account defined in
Config.ini.

Following arguments allow you to interact with Synology/Immich/NextCloud/Google Photos.
If more than one optional arguments are detected, only the first one will be executed.

-uAlb        ; --upload-albums <ALBUMS_FOLDER>
               Upload albums from <ALBUMS_FOLDER>. One album per subfolder.
               You must provide the photo client using '--client'.
               Example: --client=immich --upload-albums ./My_Albums_Folder
-dAlb        ; --download-albums <ALBUMS_NAME>
               Download specific albums to <OUTPUT_FOLDER> (required: -o/--output-folder).
               You must provide the photo client using '--client'.
               - Use 'ALL' to download ALL albums.
               - Use patterns: e.g. --download-albums 'dron*'
               - Multiple albums can be separated by comma or space and quoted.
               Example: --client=synology --download-albums "Album 1", "Album 2" -o ./MyLibrary
-uAll        ; --upload-all <INPUT_FOLDER>
               Upload all assets from <INPUT_FOLDER> to the selected client.
               You must provide the photo client using '--client'.
               - A new Album will be created per subfolder found in 'Albums' subfolder.
               - If '-AlbFolder, --albums-folders <ALBUMS_FOLDER>' is also passed, it will create albums for those
               folders too.
               Example: --client=immich --upload-all ./MyLibrary
-dAll        ; --download-all <OUTPUT_FOLDER>
               Download all albums and all non-album assets into <OUTPUT_FOLDER>.
               You must provide the photo client using '--client'.
               - Albums are downloaded under <OUTPUT_FOLDER>/Albums/<AlbumName> (flattened).
               - Non-album assets go into <OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>/ with year/month structure.
               Example: --client=synology --download-all ./MyLibrary
-renAlb      ; --rename-albums <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>
               CAUTION!!! Rename albums matching a pattern using replacement pattern.
               Requires '--client'.
               Arguments must be passed as two values separated by comma.
               Example: --rename-albums "\b(\d{4})\.(\d{2})\.(\d{2})\b", "\1-\2-\3"
               This converts dates from YYYY.MM.DD format to YYYY-MM-DD.
-rAlb        ; --remove-albums <ALBUMS_NAME_PATTERN>
               CAUTION!!! Remove albums matching pattern.
               Requires '--client'.
               Optionally also remove assets inside albums using '-rAlbAsset, --remove-albums-assets'.
               Example: --client=synology --remove-albums "^Temp" --remove-albums-assets
-rAllAlb     ; --remove-all-albums
               CAUTION!!! Remove ALL albums.
               Requires '--client'.
               Optionally also remove assets inside albums using '-rAlbAsset, --remove-albums-assets'.
               Example: --client=immich --remove-all-albums --remove-albums-assets
-rAll        ; --remove-all-assets
               CAUTION!!! Remove ALL assets (photos/videos) and ALL albums.
               Requires '--client'.
               Example: --client=synology --remove-all-assets
-rEmpAlb     ; --remove-empty-albums
               Remove empty albums.
               Requires '--client'.
               Example: --client=immich --remove-empty-albums
-rDupAlb     ; --remove-duplicates-albums
               Remove duplicated albums (same name and size).
               Requires '--client'.
               Example: --client=synology --remove-duplicates-albums
-mDupAlb     ; --merge-duplicates-albums
               Merge duplicated albums (same name): move assets into the most relevant album and remove duplicates.
               Requires '--client'.
               Example: --client=immich --merge-duplicates-albums
-rOrphan     ; --remove-orphan-assets
               Remove orphan assets.
               Requires '--client'. IMPORTANT: requires a valid ADMIN_API_KEY in Config.ini.
               Example: --client=immich --remove-orphan-assets
-OTP         ; --one-time-password
               Allow login into Synology Photos using 2FA with an OTP token.
               Example: --client=synology --download-all ./MyLibrary --one-time-password


OTHER STANDALONE FEATURES:
--------------------------
Following arguments can be used to execute the Tool in any of the useful Extra Standalone Features included.
If more than one Feature is detected, only the first one will be executed.

-fixSym      ; --fix-symlinks-broken <FOLDER_TO_FIX>
               Scan <FOLDER_TO_FIX> recursively and try to repair broken symbolic links.
               Useful after moving/renaming folders in OUTPUT_TAKEOUT_FOLDER when some albums appear empty.
               The tool searches for valid target files within the same folder tree and relinks when possible.
               IMPORTANT: Links are only fixed when a valid target can be inferred from current files.
               Example: --fix-symlinks-broken ./OUTPUT_FOLDER
-renFldcb    ; --rename-folders-content-based <ALBUMS_FOLDER>
               Rename and homogenize album folder names in <ALBUMS_FOLDER> using content dates.
               Output format is: 'yyyy - Album Name' or 'yyyy--yyyy - Album Name' when a range is detected.
               Date and range separators can be customized with '--date-separator' and '--range-separator'.
               IMPORTANT: This modifies original folder names in place; create a backup if needed.
               Example: --rename-folders-content-based ./MyLocalPhotoLibrary
-findDup     ; --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
               Find duplicates in one or more folders using file size and content checks.
               <ACTION> can be 'list', 'move' or 'delete' (CLI internally uses 'remove'). Default: 'list'.
               When multiple folders are provided, order matters: files in the first folder have priority to be kept.
               Result is exported to a CSV to review duplicates and selected action per item.
               IMPORTANT: 'move' and 'delete' modify files; start with 'list' if you want to review first.
               Example: --find-duplicates move ./Albums ./ALL_PHOTOS
-procDup     ; --process-duplicates <DUPLICATES_REVISED_CSV>
               Process a revised duplicates CSV and execute actions from the 'Action' column.
               Use this after '--find-duplicates' to apply manual decisions in your reviewed CSV.
               Valid actions: restore_duplicate / remove_duplicate / replace_duplicate.
               IMPORTANT: remove_duplicate and replace_duplicate are irreversible operations.
               Example: --process-duplicates ./Duplicates/Duplicates_revised.csv
---------------------------------------------------------------------------------------------------------
```

---

## 🏠 [Back to Main Page](/README.md)


---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
