# Command Line Syntax:
```
---------------------------------------------------------------------------------------------------------

usage: CloudPhotoMigrator.run/exe [-h] [-v] [-source <SOURCE>] [-target <TARGET>]
                                  [-dashboard [[true, false]]]
                                  [-i <INPUT_FOLDER>] [-o <OUTPUT_FOLDER>]
                                  [-AlbFld [<ALBUMS_FOLDER> [<ALBUMS_FOLDER> ...]]]
                                  [-rAlbAss] [-gpthProg [[true, false]]]
                                  [-gpthErr [[true, false]]] [-nolog]
                                  [-loglevel ['debug', 'info', 'warning', 'error', 'critical']]
                                  [-gitf <TAKEOUT_FOLDER>] [-gofs <SUFFIX>]
                                  [-gafs ['flatten', 'year', 'year/month', 'year-month']]
                                  [-gnas ['flatten', 'year', 'year/month', 'year-month']]
                                  [-gcsa] [-gics] [-gmtf] [-grdf] [-gsef] [-gsma] [-gsgt]
                                  [-suAlb <ALBUMS_FOLDER>]
                                  [-sdAlb <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                  [-suAll <INPUT_FOLDER>] [-sdAll <OUTPUT_FOLDER>]
                                  [-srEmpAlb] [-srDupAlb] [-srAll] [-srAllAlb]
                                  [-iuAlb <ALBUMS_FOLDER>]
                                  [-idAlb <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                  [-iuAll <INPUT_FOLDER>] [-idAll <OUTPUT_FOLDER>]
                                  [-irEmpAlb] [-irDupAlb] [-irAll] [-irAllAlb] [-irOrphan]
                                  [-findDup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                                  [-procDup <DUPLICATES_REVISED_CSV>]
                                  [-fixSym <FOLDER_TO_FIX>] [-renFldcb <ALBUMS_FOLDER>]

CloudPhotoMigrator v3.1.0-alpha - 2025-03-31

Multi-Platform/Multi-Arch toot designed to Interact and Manage different Photo Cloud Services
such as Google Photos, Synology Photos, Immich Photos & Apple Photos.

(c) 2024-2025 by Jaime Tur (@jaimetur)

optional arguments:

-h,        --help
             show this help message and exit
-v,        --version
             Show the Tool name, version, and date, then exit.


AUTOMATED MIGRATION PROCESS:
----------------------------
Following arguments allow you execute the Automated Migration Process to migrate your
assets from one Photo Cloud Service to other, or from two different accounts within the
same Photo Cloud service.

-source,   --source <SOURCE>
             Select the <SOURCE> for the AUTOMATED-MIGRATION Process to Pull all your
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
             Select the <TARGET> for the AUTOMATED-MIGRATION Process to Pull all your
             Assets (including Albums) from the <SOURCE> Cloud Service and Push them to
             the <TARGET> Cloud Service (including all Albums that you may have on the
             <SOURCE> Cloud Service).

             Possible values:
               ['synology', 'immich']-[id] or <OUTPUT_FOLDER>
               [id] = [1, 2] select which account to use from the Config.ini file.

             Examples:
              ​--source=immich-1 -> Select Immich Photos account 1 as Target.
              ​--source=synology-2 -> Select Synology Photos account 2 as Target.
              ​--source=/home/local_folder -> Select this local folder as Target.
--dashboard [true, false]
             Enable or disable Live Dashboard feature during Autometed Migration Job.
             This argument only applies if both '--source' and '--target' argument are
             given (AUTOMATED-MIGRATION MODE). (default: True).


GENERAL ARGUMENTS:
------------------
Following general arguments have different purposses depending on the Execution Mode.

-i,        --input-folder <INPUT_FOLDER>
             Specify the input folder that you want to process.
-o,        --output-folder <OUTPUT_FOLDER>
             Specify the output folder to save the result of the processing action.
-AlbFld,   --albums-folders <ALBUMS_FOLDER>
             If used together with '-iuAll, --immich-upload-all' or '-iuAll, --immich-
             upload-all', it will create an Album per each subfolder found in
             <ALBUMS_FOLDER>.
-rAlbAss,  --remove-albums-assets
             If used together with '-srAllAlb, --synology-remove-all-albums' or
             '-irAllAlb, --immich-remove-all-albums', it will also delete the assets
             (photos/videos) inside each album.
-gpthProg, --show-gpth-progress [true, false]
             Enable or disable Progress messages during GPTH Processing. (default:
             False).
-gpthErr,  --show-gpth-errors [true, false]
             Enable or disable Error messages during GPTH Processing. (default: True).
-nolog,    --no-log-file
             Skip saving output messages to execution log file.
-loglevel, --log-level ['debug', 'info', 'warning', 'error', 'critical']
             Specify the log level for logging and screen messages.


GOOGLE PHOTOS TAKEOUT MANAGEMENT:
---------------------------------
Following arguments allow you to interact with Google Photos Takeout Folder.
In this mode, you can use more than one optional arguments from the below list.
If only the argument -gtif, --google-takeout-input-folder <TAKEOUT_FOLDER> is detected,
then the Tool will use the default values for the rest of the arguments for this extra
mode.

-gitf,     --google-input-takeout-folder <TAKEOUT_FOLDER>
             Specify the Takeout folder to process. If any Zip file is found inside it,
             the Zip will be extracted to the folder 'Unzipped_Takeout_TIMESTAMP', and
             will use the that folder as input <TAKEOUT_FOLDER>.
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
             Album. (Useful to save disk space but may not be portable to other
             systems).
-gics,     --google-ignore-check-structure
             Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-
             folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to
             guess timestamp from them.
-gmtf,     --google-move-takeout-folder
             Move original assets to <OUTPUT_TAKEOUT_FOLDER>.
             CAUTION: Useful to avoid disk space duplication and improve execution
             speed, but you will lost your original unzipped files!!!.
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


SYNOLOGY PHOTOS MANAGEMENT:
---------------------------
Following arguments allow you to interact with Synology Photos.
If more than one optional arguments are detected, only the first one will be executed.

-suAlb,    --synology-upload-albums <ALBUMS_FOLDER>
             The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER>
             and will create one Album per subfolder into Synology Photos.
-sdAlb,    --synology-download-albums <ALBUMS_NAME>
             The Tool will connect to Synology Photos and will download those Albums
             whose name is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the
             argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this
             feature).
             - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
             - To download all albums mathing any pattern you can use patterns in
             <ALBUMS_NAME>, i.e: --synology-download-albums 'dron*' to download all
             albums starting with the word 'dron' followed by other(s) words.
             - To download several albums you can separate their names by comma or space
             and put the name between double quotes. i.e: --synology-download-albums
             'album1', 'album2', 'album3'.
-suAll,    --synology-upload-all <INPUT_FOLDER>
             The Tool will look for all Assets within <INPUT_FOLDER> and will upload
             them into Synology Photos.
             - The Tool will create a new Album per each Subfolder found in 'Albums'
             subfolder and all assets inside each subfolder will be associated to a new
             Album in Synology Photos with the same name as the subfolder.
             - If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also
             passed, then this function will create Albums also for each subfolder found
             in <ALBUMS_FOLDER>.
-sdAll,    --synology-download-all <OUTPUT_FOLDER>
             The Tool will connect to Synology Photos and will download all the Album
             and Assets without Albums into the folder <OUTPUT_FOLDER>.
             - All Albums will be downloaded within a subfolder of
             <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will
             be flattened into it.
             - Assets with no Albums associated will be downloaded within a subfolder
             called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure
             inside.
-srEmpAlb, --synology-remove-empty-albums
             The Tool will look for all Albums in your Synology Photos account and if any
             Album is empty, will remove it from your Synology Photos account.
-srDupAlb, --synology-remove-duplicates-albums
             The Tool will look for all Albums in your Synology Photos account and if any
             Album is duplicated, will remove it from your Synology Photos account.
-srAll,    --synology-remove-all-assets
             CAUTION!!! The Tool will delete ALL your Assets (Photos & Videos) and also
             ALL your Albums from Synology database.
-srAllAlb, --synology-remove-all-albums
             CAUTION!!! The Tool will delete ALL your Albums from Synology database.
             Optionally ALL the Assets associated to each Album can be deleted If you
             also include the argument '-rAlbAss, --remove-albums-assets' argument.


IMMICH PHOTOS MANAGEMENT:
-------------------------
Following arguments allow you to interact with Immich Photos.
If more than one optional arguments are detected, only the first one will be executed.

-iuAlb,    --immich-upload-albums <ALBUMS_FOLDER>
             The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER>
             and will create one Album per subfolder into Immich Photos.
-idAlb,    --immich-download-albums <ALBUMS_NAME>
             The Tool will connect to Immich Photos and download those Albums whose name
             is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument
             '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this
             feature).
             - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
             - To download all albums mathing any pattern you can use patterns in
             ALBUMS_NAME, i.e: --immich-download-albums 'dron*' to download all albums
             starting with the word 'dron' followed by other(s) words.
             - To download several albums you can separate their names by comma or space
             and put the name between double quotes. i.e: --immich-download-albums
             'album1', 'album2', 'album3'.
-iuAll,    --immich-upload-all <INPUT_FOLDER>
             The Tool will look for all Assets within <INPUT_FOLDER> and will upload
             them into Immich Photos.
             - The Tool will create a new Album per each Subfolder found in 'Albums'
             subfolder and all assets inside each subfolder will be associated to a new
             Album in Immich Photos with the same name as the subfolder.
             - If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also
             passed, then this function will create Albums also for each subfolder found
             in <ALBUMS_FOLDER>.
-idAll,    --immich-download-all <OUTPUT_FOLDER>
             The Tool will connect to Immich Photos and will download all the Album and
             Assets without Albums into the folder <OUTPUT_FOLDER>.
             - All Albums will be downloaded within a subfolder of
             <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will
             be flattened into it.
             - Assets with no Albums associated will be downloaded within a subfolder
             called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure
             inside.
-irEmpAlb, --immich-remove-empty-albums
             The Tool will look for all Albums in Immich your Photos account and if any
             Album is empty, will remove it from your Immich Photos account.
-irDupAlb, --immich-remove-duplicates-albums
             The Tool will look for all Albums in Immich your Photos account and if any
             Album is duplicated, will remove it from your Immich Photos account.
-irAll,    --immich-remove-all-assets
             CAUTION!!! The Tool will delete ALL your Assets (Photos & Videos) and also
             ALL your Albums from Immich database.
-irAllAlb, --immich-remove-all-albums
             CAUTION!!! The Tool will delete ALL your Albums from Immich database.
             Optionally ALL the Assets associated to each Album can be deleted If you
             also include the argument '-rAlbAss, --remove-albums-assets' argument.
-irOrphan, --immich-remove-orphan-assets
             The Tool will look for all Orphan Assets in Immich Database and will delete
             them. IMPORTANT: This feature requires a valid ADMIN_API_KEY configured in
             Config.ini.


OTHER STANDALONE FEATURES:
--------------------------
Following arguments can be used to execute the Tool in any of the usefull additionals
Extra Standalone Features included.
If more than one Feature is detected, only the first one will be executed.

-findDup,  --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
             Find duplicates in specified folders.
             <ACTION> defines the action to take on duplicates ('move', 'delete' or
             'list'). Default: 'list'
             <DUPLICATES_FOLDER> are one or more folders (string or list), where the
             Tool will look for duplicates files. The order of this list is important to
             determine the principal file of a duplicates set. First folder will have
             higher priority.
-procDup,  --process-duplicates <DUPLICATES_REVISED_CSV>
             Specify the Duplicates CSV file revised with specifics Actions in Action
             column, and the Tool will execute that Action for each duplicates found in
             CSV. Valid Actions: restore_duplicate / remove_duplicate /
             replace_duplicate.
-fixSym,   --fix-symlinks-broken <FOLDER_TO_FIX>
             The Tool will try to fix all symbolic links for Albums in <FOLDER_TO_FIX>
             folder (Useful if you have move any folder from the OUTPUT_TAKEOUT_FOLDER
             and some Albums seems to be empty.
-renFldcb, --rename-folders-content-based <ALBUMS_FOLDER>
             Usefull to rename and homogenize all Albums folders found in
             <ALBUMS_FOLDER> based on the date content found.

---------------------------------------------------------------------------------------------------------
```

## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
