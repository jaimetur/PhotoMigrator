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
                     [-fnAlbums <ALBUMS_FOLDER>] [-fnNoAlbums <NO_ALBUMS_FOLDER>] [-fnLogs <LOG_FOLDER>]
                     [-fnDuplicat <DUPLICATES_OUTPUT_FOLDER>] [-fnExiftool <EXIFTOOL_OUTPUT_FOLDER>]
                     [-i <INPUT_FOLDER>] [-o <OUTPUT_FOLDER>] [-client = ['google-takeout', 'synology', 'immich']]
                     [-id [= [1-3]]] [-OTP]
                     [-from <FROM_DATE>] [-to <TO_DATE>] [-type = [image,video,all]]
                     [-country <COUNTRY_NAME>] [-city <CITY_NAME>] [-person <PERSON_NAME>]
                     [-AlbFolder [<ALBUMS_FOLDER> [<ALBUMS_FOLDER> ...]]] [-rAlbAsset]
                     [-source <SOURCE>] [-target <TARGET>]
                     [-move [= [true,false]]] [-dashboard [= [true,false]]] [-parallel [= [true,false]]]
                     [-gTakeout <TAKEOUT_FOLDER>] [-gofs <SUFFIX>]
                     [-gafs ['flatten', 'year', 'year/month', 'year-month']]
                     [-gnas ['flatten', 'year', 'year/month', 'year-month']] [-gics] [-gnsa] [-grdf] [-graf] [-gsef]
                     [-gsma] [-gsgt] [-gKeepTkout] [-gSkipPrep]
                     [-gpthInfo [= [true,false]]] [-gpthError [= [true,false]]]
                     [-uAlb <ALBUMS_FOLDER>] [-dAlb <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                     [-uAll <INPUT_FOLDER>] [-dAll <OUTPUT_FOLDER>] [-rOrphan] [-rAll] [-rAllAlb]
                     [-rAlb <ALBUMS_NAME_PATTERN>] [-rEmpAlb] [-rDupAlb] [-mDupAlb]
                     [-renAlb <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>]
                     [-fixSym <FOLDER_TO_FIX>]
                     [-renFldcb <ALBUMS_FOLDER>]
                     [-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                     [-procDup <DUPLICATES_REVISED_CSV>]

PhotoMigrator v3.4.0 - 2025-06-30

         Multi-Platform/Multi-Arch tool designed to Interact and Manage different Photo Cloud Services
         such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

         (c) 2024-2025 by Jaime Tur (@jaimetur)

optional arguments:

-h         ; --help
              show this help message and exit
-v         ; --version
              Show the Tool name, version, and date, then exit.
-config    ; --configuration-file <CONFIGURATION_FILE>
              Specify the file that contains the Configuration to connect to the different Photo Cloud Services.
-noConfirm ; --no-request-user-confirmation
              No Request User Confirmation before execute any Feature.
-noLog     ; --no-log-file
              Skip saving output messages to execution log file.
-logLevel  ; --log-level =[VERBOSE, DEBUG, INFO, WARNING, ERROR]
              Specify the log level for logging and screen messages.
-logFormat ; --log-format =[LOG, TXT, ALL]
              Specify the log file format.
-fnAlbums  ; --foldername-albums <ALBUMS_FOLDER>
              Specify the folder name to store all your processed photos associated to any Album.
-fnNoAlbums; --foldername-no-albums <NO_ALBUMS_FOLDER>
              Specify the folder name to store all your processed photos (including those associated to Albums).
-fnLogs    ; --foldername-logs <LOG_FOLDER>
              Specify the folder name to save the execution Logs.
-fnDuplicat; --foldername-duplicates-output <DUPLICATES_OUTPUT_FOLDER>
              Specify the folder name to save the outputs of 'Find Duplicates' Feature.
-fnExiftool; --foldername-exiftool-output <EXIFTOOL_OUTPUT_FOLDER>
              Specify the folder name to save the outputs of 'Exiftool' Metadata Fixer.


GENERAL ARGUMENTS:
------------------
Following general arguments have different purposses depending on the Execution Mode.

-i         ; --input-folder <INPUT_FOLDER>
              Specify the input folder that you want to process.
-o         ; --output-folder <OUTPUT_FOLDER>
              Specify the output folder to save the result of the processing action.
-client    ; --client = ['google-takeout', 'synology', 'immich']
              Set the client to use for the selected feature.
-id        ; --account-id = [1-3]
              Set the account ID for Synology Photos or Immich Photos. (default: 1). This value must exist in the
              <CONFIGURATION_FILE> as suffix of USERNAME/PASSWORD or API_KEY_USER.
              Example for Immich ID=2:
                IMMICH_USERNAME_2/IMMICH_PASSWORD_2 or IMMICH_API_KEY_USER_2 entries must exist in <CONFIGURATION_FILE>.
-OTP       ; --one-time-password
              This Flag allow you to login into Synology Photos using 2FA with an OTP Token.
-from      ; --filter-from-date <FROM_DATE>
              Specify the initial date to filter assets in the different Photo Clients.
-to        ; --filter-to-date <TO_DATE>
              Specify the final date to filter assets in the different Photo Clients.
-type      ; --filter-by-type = [image,video,all]
              Specify the Asset Type to filter assets in the different Photo Clients. (default: all)
-country   ; --filter-by-country <COUNTRY_NAME>
              Specify the Country Name to filter assets in the different Photo Clients.
-city      ; --filter-by-city <CITY_NAME>
              Specify the City Name to filter assets in the different Photo Clients.
-person    ; --filter-by-person <PERSON_NAME>
              Specify the Person Name to filter assets in the different Photo Clients.
-AlbFolder ; --albums-folders <ALBUMS_FOLDER>
              If used together with '-uAll, --upload-all', it will create an Album per each subfolder found in
              <ALBUMS_FOLDER>.
-rAlbAsset ; --remove-albums-assets
              If used together with '-rAllAlb, --remove-all-albums' or '-rAlb, --remove-albums', it will also remove the
              assets (photos/videos) inside each album.


AUTOMATIC MIGRATION PROCESS:
----------------------------
Following arguments allow you execute the Automatic Migration Process to migrate your assets from one Photo Cloud
Service to other, or from two different accounts within the same Photo Cloud service.

-source    ; --source <SOURCE>
              Select the <SOURCE> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from
              the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may
              have on the <SOURCE> Cloud Service).

              Possible values:
                ['synology', 'immich']-[id] or <INPUT_FOLDER>
                [id] = [1, 2] select which account to use from the <CONFIGURATION_FILE> file.

              Examples:
               ​--source=immich-1 -> Select Immich Photos account 1 as Source.
               ​--source=synology-2 -> Select Synology Photos account 2 as Source.
               ​--source=/home/local_folder -> Select this local folder as Source.
               ​--source=/home/Takeout -> Select this Takeout folder as Source. (zipped and unzipped format supported)
-target    ; --target <TARGET>
              Select the <TARGET> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from
              the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may
              have on the <SOURCE> Cloud Service).

              Possible values:
                ['synology', 'immich']-[id] or <OUTPUT_FOLDER>
                [id] = [1, 2] select which account to use from the <CONFIGURATION_FILE> file.

              Examples:
               ​--target=immich-1 -> Select Immich Photos account 1 as Target.
               ​--target=synology-2 -> Select Synology Photos account 2 as Target.
               ​--target=/home/local_folder -> Select this local folder as Target.
-move      ; --move-assets = [true,false]
              If this argument is present, the assets will be moved from <SOURCE> to <TARGET> instead of copy them.
              (default: False).
-dashboard ; --dashboard = [true,false]
              Enable or disable Live Dashboard feature during Autometed Migration Job. This argument only applies if
              both '--source' and '--target' arguments are given (AUTOMATIC-MIGRATION FEATURE). (default: True).
-parallel  ; --parallel-migration = [true,false]
              Select Parallel/Secuencial Migration during Automatic Migration Job.
              This argument only applies if both '--source' and '--target' arguments are given (AUTOMATIC-MIGRATION
              FEATURE). (default: True).


GOOGLE PHOTOS TAKEOUT MANAGEMENT:
---------------------------------
Following arguments allow you to interact with Google Photos Takeout Folder.
In this mode, you can use more than one optional arguments from the below list.
If only the argument -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the Tool will use the default values
for the rest of the arguments for this extra mode.

-gTakeout  ; --google-takeout <TAKEOUT_FOLDER>
              Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata and organize assets inside it. If any Zip
              file is found inside it, the Zip will be extracted to the folder '<TAKEOUT_FOLDER>_unzipped_<TIMESTAMP>',
              and will use the that folder as input <TAKEOUT_FOLDER>.
              The processed Takeout will be saved into the folder '<TAKEOUT_FOLDER>_processed_<TIMESTAMP>'
              This argument is mandatory to run the Google Takeout Processor Feature.
-gofs      ; --google-output-folder-suffix <SUFFIX>
              Specify the suffix for the output folder. Default: 'processed'
-gafs      ; --google-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
              Specify the type of folder structure for each Album folder (Default: 'flatten').
-gnas      ; --google-no-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
              Specify the type of folder structure for '<NO_ALBUMS_FOLDER>' folders (Default: 'year/month').
-gics      ; --google-ignore-check-structure
              Ignores Check Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all
              files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
-gnsa      ; --google-no-symbolic-albums
              Duplicates Albums assets instead of create symlinks to original asset within <NO_ALBUMS_FOLDER>.
              (Makes your Output Takeout Folder portable to other systems, but requires more HDD space).
              IMPORTANT: This increments considerably the Output Takeout Folder size, specially if you have many Albums.
              For instance, if one asset belongs to 3 different albums, then you will have 4 copies of the same asset
              (the original, and one per album).
-grdf      ; --google-remove-duplicates-files
              Removes Duplicates files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.
-graf      ; --google-rename-albums-folders
              Renames Albums Folders in <OUTPUT_TAKEOUT_FOLDER> based on content date of each album after fixing them.
-gsef      ; --google-skip-extras-files
              Skips processing extra photos such as  -edited, -effects photos.
-gsma      ; --google-skip-move-albums
              Skips moving albums to '<ALBUMS_FOLDER>'.
-gsgt      ; --google-skip-gpth-tool
              Skips processing files with GPTH Tool.
              CAUTION: This option is NOT RECOMMENDED because this is the Core of the Google Photos Takeout Process. Use
              this flag only for testing purposes.
-gKeepTkout; --google-keep-takeout-folder
              Keeps a copy of your original Takeout before to start to process it (requires double HDD space).
              TIP: If you use as <TAKEOUT_FOLDER>, the folder that contains your Takeout's Zip files,
              you will always conserve the original Zips and don't need to use this flag.
-gSkipPrep ; --google-skip-preprocess
              Skip Pre-process Google Takeout to 1.Clean Takeout Folder, 2.Fix MP4/Live Picture associations and 3.Fix
              Truncated filenames/extensions.
              This Pre-process is very important for a high accuracy on the Output, but if you have already done this
              Pre-Processing in a previous execution using the flag '-gKeepTkout,--google-keep-takeout-folder' then you
              can skip it for that <TAKEOUT_FOLDER>.
-gpthInfo  ; --show-gpth-info = [true,false]
              Enable or disable Info messages during GPTH Processing. (default: True).
-gpthError ; --show-gpth-errors = [true,false]
              Enable or disable Error messages during GPTH Processing. (default: True).


SYNOLOGY/IMMICH PHOTOS MANAGEMENT:
----------------------------------
To use following features, it is mandatory to use the argument '--client=[synology, immich]' to specify which Photo
Service do you want to use.

You can optionally use the argument '--id=[1-3]' to specify the account id for a particular account defined in
<CONFIGURATION_FILE>.

Following arguments allow you to interact with Synology/Immich Photos.
If more than one optional arguments are detected, only the first one will be executed.

-uAlb      ; --upload-albums <ALBUMS_FOLDER>
              The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per
              subfolder into the selected Photo client.
              You must provide the Photo client using the mandatory argument '--client'.
-dAlb      ; --download-albums <ALBUMS_NAME>
              The Tool will connect to the selected Photo client and will download those Albums whose name is in
              '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>'
              (mandatory argument for this feature).
              You must provide the Photo client using the mandatory argument '--client'.
              - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
              - To download all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --download-albums
              'dron*' to download all albums starting with the word 'dron' followed by other(s) words.
              - To download several albums you can separate their names by comma or space and put the name between
              double quotes. i.e: --download-albums 'album1', 'album2', 'album3'.
-uAll      ; --upload-all <INPUT_FOLDER>
              The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into the selected Photo
              client.
              You must provide the Photo client using the mandatory argument '--client'.
              - The Tool will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside
              each subfolder will be associated to a new Album in the selected Photo client with the same name as the
              subfolder.
              - If the argument '-AlbFolder, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will
              create Albums also for each subfolder found in <ALBUMS_FOLDER>.
-dAll      ; --download-all <OUTPUT_FOLDER>
              The Tool will connect to the selected Photo client and will download all the Album and Assets without
              Albums into the folder <OUTPUT_FOLDER>.
              You must provide the Photo client using the mandatory argument '--client'.
              - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the
              Album and all files will be flattened into it.
              - Assets with no Albums associated will be downloaded within a subfolder called
              <OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>/ and will have a year/month structure inside.
-rOrphan   ; --remove-orphan-assets
              The Tool will look for all Orphan Assets in the selected Photo client and will remove them.
              You must provide the Photo client using the mandatory argument '--client'. IMPORTANT: This feature
              requires a valid ADMIN_API_KEY configured in <CONFIGURATION_FILE>.
-rAll      ; --remove-all-assets
              CAUTION!!! The Tool will remove ALL your Assets (Photos & Videos) and also ALL your Albums from the
              selected Photo client.
              You must provide the Photo client using the mandatory flag '--client'.
-rAllAlb   ; --remove-all-albums
              CAUTION!!! The Tool will remove ALL your Albums from the selected Photo client.
              You must provide the Photo client using the mandatory flag '--client'.
              Optionally ALL the Assets associated to each Album can be removed If you also include the flag
              '-rAlbAsset, --remove-albums-assets'.
-rAlb      ; --remove-albums <ALBUMS_NAME_PATTERN>
              CAUTION!!! The Tool will look for all Albums in the selected Photo client whose names matches with the
              pattern and will remove them.
              You must provide the Photo client using the mandatory flag '--client'.
              Optionally ALL the Assets associated to each Album can be removed If you also include the flag
              '-rAlbAsset, --remove-albums-assets' flag.
-rEmpAlb   ; --remove-empty-albums
              The Tool will look for all Albums in the selected Photo client account and if any Album is empty, will
              remove it from the selected Photo client account.
              You must provide the Photo client using the mandatory flag '--client'.
-rDupAlb   ; --remove-duplicates-albums
              The Tool will look for all Albums in the selected Photo client account and if any Album is duplicated
              (with the same name and size), will remove it from the selected Photo client account.
              You must provide the Photo client using the mandatory flag '--client'.
-mDupAlb   ; --merge-duplicates-albums
              The Tool will look for all Albums in the selected Photo client account and if any Album is duplicated
              (with the same name), will transfer all its assets to the most relevant album and remove it from the
              selected Photo client account.
              You must provide the Photo client using the mandatory flag '--client'.
-renAlb    ; --rename-albums <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>
              CAUTION!!! The Tool will look for all Albums in the selected Photo client whose names matches with the
              pattern and will rename them from with the replacement pattern.
              You must provide the Photo client using the mandatory flag '--client'.


OTHER STANDALONE FEATURES:
--------------------------
Following arguments can be used to execute the Tool in any of the useful Extra Standalone Features included.
If more than one Feature is detected, only the first one will be executed.

-fixSym    ; --fix-symlinks-broken <FOLDER_TO_FIX>
              The Tool will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move
              any folder from the OUTPUT_TAKEOUT_FOLDER and some Albums seems to be empty.
-renFldcb  ; --rename-folders-content-based <ALBUMS_FOLDER>
              Useful to rename and homogenize all Albums folders found in <ALBUMS_FOLDER> based on the date content
              found.
-findDup   ; --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
              Find duplicates in specified folders.
              <ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list'
              <DUPLICATES_FOLDER> are one or more folders (string or list), where the Tool will look for duplicates
              files. The order of this list is important to determine the principal file of a duplicates set. First
              folder will have higher priority.
-procDup   ; --process-duplicates <DUPLICATES_REVISED_CSV>
              Specify the Duplicates CSV file revised with specifics Actions in Action column, and the Tool will execute
              that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate /
              replace_duplicate.
---------------------------------------------------------------------------------------------------------
```

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)


---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
