# Command Line Interface (CLI):
This section shows how to use the Command Line Interface (CLI) for this Tool.

Most of the argument can be given with two formats:
- Short format: '-' followed by the short name
- Long format: '--' followed by the long name

Both methods are exactly the same, long name is more conveninet in some cases to remember better what the command does, while short format is easier to write

Some arguments must be followed by a value. This value can be separated from the argument by '=' or just by space ' ', both ways are valid.

- Example 1: Following commmands are exactly the same
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
usage: PhotoMigrator.run/exe [-h] [-v] [-source <SOURCE>] [-target <TARGET>]
                                  [-move [= [true,false]]] [-dashb [= [true,false]]]
                                  [-parallel [= [true,false]]]
                                  [-i <INPUT_FOLDER>] [-o <OUTPUT_FOLDER>]
                                  [-client = ['google-takeout', 'synology', 'immich']]
                                  [-id [= [1,2,3]]] [-OTP]
                                  [-from <FROM_DATE>] [-to <TO_DATE>]
                                  [-country <COUNTRY_NAME>] [-city <CITY_NAME>]
                                  [-person <PERSON_NAME>] [-type = [image,video,all]]
                                  [-AlbFld [<ALBUMS_FOLDER> [<ALBUMS_FOLDER> ...]]]
                                  [-rAlbAss] [-nolog]
                                  [-loglevel ['debug', 'info', 'warning', 'error']]
                                  [-gTakeout <TAKEOUT_FOLDER>] [-gofs <SUFFIX>]
                                  [-gafs ['flatten', 'year', 'year/month', 'year-month']]
                                  [-gnas ['flatten', 'year', 'year/month', 'year-month']]
                                  [-gcsa] [-gics] [-gmtf] [-grdf] [-gsef] [-gsma] [-gsgt]
                                  [-gpthProg [= [true,false]]] [-gpthErr [= [true,false]]]
                                  [-uAlb <ALBUMS_FOLDER>]
                                  [-dAlb <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                  [-uAll <INPUT_FOLDER>] [-dAll <OUTPUT_FOLDER>] [-rOrphan]
                                  [-rAll] [-rAllAlb] [-rAlb <ALBUMS_NAME_PATTERN>]
                                  [-rEmpAlb] [-rDupAlb] [-mDupAlb]
                                  [-renAlb <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>]
                                  [-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                                  [-procDup <DUPLICATES_REVISED_CSV>]
                                  [-fixSym <FOLDER_TO_FIX>] [-renFldcb <ALBUMS_FOLDER>]

PhotoMigrator v3.3.0-RC - 2025-05-15

Multi-Platform/Multi-Arch tool designed to Interact and Manage different Photo Cloud Services
such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

(c) 2024-2025 by Jaime Tur (@jaimetur)

optional arguments:

-h,        --help
             show this help message and exit
-v,        --version
             Show the Tool name, version, and date, then exit.


AUTOMATIC MIGRATION PROCESS:
----------------------------
Following arguments allow you execute the Automatic Migration Process to migrate your
assets from one Photo Cloud Service to other, or from two different accounts within the
same Photo Cloud service.

-source,   --source <SOURCE>
             Select the <SOURCE> for the AUTOMATIC-MIGRATION Process to Pull all your
             Assets (including Albums) from the <SOURCE> Cloud Service and Push them to
             the <TARGET> Cloud Service (including all Albums that you may have on the
             <SOURCE> Cloud Service).

             Possible values:
               ['synology', 'immich']-[id] or <INPUT_FOLDER>
               [id] = [1, 2] select which account to use from the Config.ini file.

             Examples:
              ​--source=immich-1 -> Select Immich Photos account 1 as Source.
              ​--source=synology-2 -> Select Synology Photos account 2 as Source.
              ​--source=/home/local_folder -> Select this local folder as Source.
              ​--source=/home/Takeout -> Select this Takeout folder as Source.
              ​                      (both, zipped and unzipped format are supported)
-target,   --target <TARGET>
             Select the <TARGET> for the AUTOMATIC-MIGRATION Process to Pull all your
             Assets (including Albums) from the <SOURCE> Cloud Service and Push them to
             the <TARGET> Cloud Service (including all Albums that you may have on the
             <SOURCE> Cloud Service).

             Possible values:
               ['synology', 'immich']-[id] or <OUTPUT_FOLDER>
               [id] = [1, 2] select which account to use from the Config.ini file.

             Examples:
              ​--target=immich-1 -> Select Immich Photos account 1 as Target.
              ​--target=synology-2 -> Select Synology Photos account 2 as Target.
              ​--target=/home/local_folder -> Select this local folder as Target.
-move,     --move-assets = [true,false]
             If this argument is present, the assets will be moved from <SOURCE> to
             <TARGET> instead of copy them. (default: False).
-dashb,    --dashboard = [true,false]
             Enable or disable Live Dashboard feature during Autometed Migration Job. This
             argument only applies if both '--source' and '--target' argument are given
             (AUTOMATIC-MIGRATION FEATURE). (default: True).
-parallel, --parallel-migration = [true,false]
             Select Parallel/Secuencial Migration during Automatic Migration Job. This
             argument only applies if both '--source' and '--target' argument are given
             (AUTOMATIC-MIGRATION FEATURE). (default: True).


GENERAL ARGUMENTS:
------------------
Following general arguments have different purposses depending on the Execution Mode.

-i,        --input-folder <INPUT_FOLDER>
             Specify the input folder that you want to process.
-o,        --output-folder <OUTPUT_FOLDER>
             Specify the output folder to save the result of the processing action.
-client,   --client = ['google-takeout', 'synology', 'immich']
             Set the client to use for the selected feature.
-id,       --account-id = [1,2,3]
             Set the account ID for Synology Photos or Immich Photos. (default: 1). This
             value must exist in the Configuration file as suffix of USERNAME/PASSORD or
             API_KEY_USER. (example for Immich ID=2: IMMICH_USERNAME_2/IMMICH_PASSWORD_2
             or IMMICH_API_KEY_USER_2 entries must exist in Config.ini file).
-OTP,      --one-time-password
             This Flag allow you to login into Synology Photos using 2FA with an OTP
             Token.
-from,     --filter-from-date <FROM_DATE>
             Specify the initial date to filter assets in the different Photo Clients.
-to,       --filter-to-date <TO_DATE>
             Specify the final date to filter assets in the different Photo Clients.
-country,  --filter-by-country <COUNTRY_NAME>
             Specify the Country Name to filter assets in the different Photo Clients.
-city,     --filter-by-city <CITY_NAME>
             Specify the City Name to filter assets in the different Photo Clients.
-person,   --filter-by-person <PERSON_NAME>
             Specify the Person Name to filter assets in the different Photo Clients.
-type,     --filter-by-type = [image,video,all]
             Specify the Asset Type to filter assets in the different Photo Clients.
             (default: all)
-AlbFld,   --albums-folders <ALBUMS_FOLDER>
             If used together with '-uAll, --upload-all', it will create an Album per each
             subfolder found in <ALBUMS_FOLDER>.
-rAlbAss,  --remove-albums-assets
             If used together with '-rAllAlb, --remove-all-albums' or '-rAlb, --remove-
             albums', it will also remove the assets (photos/videos) inside each album.
-nolog,    --no-log-file
             Skip saving output messages to execution log file.
-loglevel, --log-level ['debug', 'info', 'warning', 'error']
             Specify the log level for logging and screen messages.


GOOGLE PHOTOS TAKEOUT MANAGEMENT:
---------------------------------
Following arguments allow you to interact with Google Photos Takeout Folder.
In this mode, you can use more than one optional arguments from the below list.
If only the argument -gTakeout, --google-takeout <TAKEOUT_FOLDER> is detected, then the
Tool will use the default values for the rest of the arguments for this extra mode.

-gTakeout, --google-takeout <TAKEOUT_FOLDER>
             Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata and organize
             assets inside it. If any Zip file is found inside it, the Zip will be
             extracted to the folder '<TAKEOUT_FOLDER>_unzipped_<TIMESTAMP>', and will use
             the that folder as input <TAKEOUT_FOLDER>.
             The processed Takeout will be saved into the folder
             '<TAKEOUT_FOLDER>_processed_<TIMESTAMP>'
             This argument is mandatory to run the Google Takeout Processor Feature.
-gofs,     --google-output-folder-suffix <SUFFIX>
             Specify the suffix for the output folder. Default: 'processed'
-gafs,     --google-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
             Specify the type of folder structure for each Album folder (Default:
             'flatten').
-gnas,     --google-no-albums-folder-structure ['flatten', 'year', 'year/month', 'year-month']
             Specify the type of folder structure for 'No-Albums' folder (Default:
             'year/month').
-gcsa,     --google-create-symbolic-albums
             Creates symbolic links for Albums instead of duplicate the files of each
             Album. (Useful to save disk space but may not be portable to other systems).
-gics,     --google-ignore-check-structure
             Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-
             folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess
             timestamp from them.
-gmtf,     --google-move-takeout-folder
             Move original assets to <OUTPUT_TAKEOUT_FOLDER>.
             CAUTION: Useful to avoid disk space duplication and improve execution speed,
             but you will lost your original unzipped files!!!.
             Use only if you keep the original zipped files or you have disk space
             limitations and you don't mind to lost your original unzipped files.
-grdf,     --google-remove-duplicates-files
             Remove Duplicates files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.
-gsef,     --google-skip-extras-files
             Skip processing extra photos such as  -edited, -effects photos.
-gsma,     --google-skip-move-albums
             Skip moving albums to 'Albums' folder.
-gsgt,     --google-skip-gpth-tool
             Skip processing files with GPTH Tool.
             CAUTION: This option is NOT RECOMMENDED because this is the Core of the
             Google Photos Takeout Process. Use this flag only for testing purposses.
-gpthProg, --show-gpth-progress = [true,false]
             Enable or disable Progress messages during GPTH Processing. (default: False).
-gpthErr,  --show-gpth-errors = [true,false]
             Enable or disable Error messages during GPTH Processing. (default: True).


SYNOLOGY/IMMICH PHOTOS MANAGEMENT:
----------------------------------
To use following features, it is mandatory to use the argument '--client=[synology,
immich]' to specify which Photo Service do you want to use.

You can optionally use the argument '--id=[1-3]' to specify the account id for a
particular account defined in Config.ini.

Following arguments allow you to interact with Synology/Immich Photos.
If more than one optional arguments are detected, only the first one will be executed.

-uAlb,     --upload-albums <ALBUMS_FOLDER>
             The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and
             will create one Album per subfolder into the selected Photo client.
             You must provide the Photo client using the mandatory flag '--client'.
-dAlb,     --download-albums <ALBUMS_NAME>
             The Tool will connect to the selected Photo client and will download those
             Albums whose name is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given
             by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for
             this feature).
             You must provide the Photo client using the mandatory flag '--client'.
             - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
             - To download all albums mathing any pattern you can use patterns in
             ALBUMS_NAME, i.e: --download-albums 'dron*' to download all albums starting
             with the word 'dron' followed by other(s) words.
             - To download several albums you can separate their names by comma or space
             and put the name between double quotes. i.e: --download-albums 'album1',
             'album2', 'album3'.
-uAll,     --upload-all <INPUT_FOLDER>
             The Tool will look for all Assets within <INPUT_FOLDER> and will upload them
             into the selected Photo client.
             You must provide the Photo client using the mandatory flag '--client'.
             - The Tool will create a new Album per each Subfolder found in 'Albums'
             subfolder and all assets inside each subfolder will be associated to a new
             Album in the selected Photo client with the same name as the subfolder.
             - If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed,
             then this function will create Albums also for each subfolder found in
             <ALBUMS_FOLDER>.
-dAll,     --download-all <OUTPUT_FOLDER>
             The Tool will connect to the selected Photo client and will download all the
             Album and Assets without Albums into the folder <OUTPUT_FOLDER>.
             You must provide the Photo client using the mandatory flag '--client'.
             - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/
             with the same name of the Album and all files will be flattened into it.
             - Assets with no Albums associated will be downloaded within a subfolder
             called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure
             inside.
-rOrphan,  --remove-orphan-assets
             The Tool will look for all Orphan Assets in the selected Photo client and
             will remove them.
             You must provide the Photo client using the mandatory flag '--client'.
             IMPORTANT: This feature requires a valid ADMIN_API_KEY configured in
             Config.ini.
-rAll,     --remove-all-assets
             CAUTION!!! The Tool will remove ALL your Assets (Photos & Videos) and also
             ALL your Albums from the selected Photo client.
             You must provide the Photo client using the mandatory flag '--client'.
-rAllAlb,  --remove-all-albums
             CAUTION!!! The Tool will remove ALL your Albums from the selected Photo
             client.
             You must provide the Photo client using the mandatory flag '--client'.
             Optionally ALL the Assets associated to each Album can be removed If you also
             include the argument '-rAlbAss, --remove-albums-assets' argument.
-rAlb,     --remove-albums <ALBUMS_NAME_PATTERN>
             CAUTION!!! The Tool will look for all Albums in the selected Photo client
             whose names matches with the pattern and will remove them.
             You must provide the Photo client using the mandatory flag '--client'.
             Optionally ALL the Assets associated to each Album can be removed If you also
             include the argument '-rAlbAss, --remove-albums-assets' argument.
-rEmpAlb,  --remove-empty-albums
             The Tool will look for all Albums in the selected Photo client account and if
             any Album is empty, will remove it from the selected Photo client account.
             You must provide the Photo client using the mandatory flag '--client'.
-rDupAlb,  --remove-duplicates-albums
             The Tool will look for all Albums in the selected Photo client account and if
             any Album is duplicated (with the same name and size), will remove it from
             the selected Photo client account.
             You must provide the Photo client using the mandatory flag '--client'.
-mDupAlb,  --merge-duplicates-albums
             The Tool will look for all Albums in the selected Photo client account and if
             any Album is duplicated (with the same name), will transfer all its assets to
             the most relevant album and remove it from the selected Photo client account.
             You must provide the Photo client using the mandatory flag '--client'.
-renAlb,   --rename-albums <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>
             CAUTION!!! The Tool will look for all Albums in the selected Photo client
             whose names matches with the pattern and will rename them from with the
             replacement pattern.
             You must provide the Photo client using the mandatory flag '--client'.


OTHER STANDALONE FEATURES:
--------------------------
Following arguments can be used to execute the Tool in any of the usefull additionals
Extra Standalone Features included.
If more than one Feature is detected, only the first one will be executed.

-findDup,  --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
             Find duplicates in specified folders.
             <ACTION> defines the action to take on duplicates ('move', 'delete' or
             'list'). Default: 'list'
             <DUPLICATES_FOLDER> are one or more folders (string or list), where the Tool
             will look for duplicates files. The order of this list is important to
             determine the principal file of a duplicates set. First folder will have
             higher priority.
-procDup,  --process-duplicates <DUPLICATES_REVISED_CSV>
             Specify the Duplicates CSV file revised with specifics Actions in Action
             column, and the Tool will execute that Action for each duplicates found in
             CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.
-fixSym,   --fix-symlinks-broken <FOLDER_TO_FIX>
             The Tool will try to fix all symbolic links for Albums in <FOLDER_TO_FIX>
             folder (Useful if you have move any folder from the OUTPUT_TAKEOUT_FOLDER and
             some Albums seems to be empty.
-renFldcb, --rename-folders-content-based <ALBUMS_FOLDER>
             Useful to rename and homogenize all Albums folders found in <ALBUMS_FOLDER>
             based on the date content found.
---------------------------------------------------------------------------------------------------------
```

---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
