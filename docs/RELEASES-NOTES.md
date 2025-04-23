## Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/CloudPhotoMigrator/releases/download/v3.3.0-alpha/CloudPhotoMigrator_v3.3.0-alpha_docker.zip)  

---

## Release Notes:

**Release**: v3.3.0  
**Release Date**: 2025-05-30
  - Alpha version    : 2025-05-16
  - Beta version     : 2025-05-23
  - Release Candidate: 2025-05-30
  - Official Release : 2025-05-30

### Main Changes:
- [x] Added Feature to Merge Albums with the same name and different assets. 
- [x] Added new flags _**'-sMergAlb, --synology-merge-duplicates-albums'**_ and _**'-iMergAlb, --immich-merge-duplicates-albums'**_ to activate this feature.
- [x] Improved Performance on Pull functions when no filtering options have been given
- [x] Improved performance when searching Google Takeout structure on huge local folder with many subfolders
- [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automated Mode Feature as before)
- [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2)
- [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini
- [x] Added new flag _**'-sOTP, --synology-OTP'**_ to allow login into Synology Photos accounts with 2FA activated
- [x] Support for 2FA in Synology Photos requesting the OTP Token if flag _**'-sOTP, --synology-OTP'**_ is detected. [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218)
- [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218)

---

**Release**: v3.2.0  
**Release Date**: 2025-04-30

### Main Changes:
- [x] Added options to filter assets in all Immich/Synology/LocalFolder Actions:
    - [x] by Type
    - [x] by Dates
    - [x] by Country
    - [x] by City
    - [x] by Person
- [x] Added new flag _**-type, --filter-by-type=[image, video, all]**_ to select the Asset Type to download (default: all)
- [x] Added new flag _**-from, --filter-from-date <FROM_DATE>**_ to select the Initial Date of the Assets to download
- [x] Added new flag _**-to, --filter-to-date <TO_DATE>**_ to select the Final Date of the Assets to download
- [x] Added new flag _**-country, --filter-by-country <COUNTRY_NAME>**_ to select the Country Name of the Assets to download
- [x] Added new flag _**-city, --filter-by-city <CITY_NAME>**_ to select the City Name of the Assets to download
- [x] Added new flag _**-person, --filter-by-person <PERSON_NAME>**_ to select the Person Name of the Assets to download
- [x] Added new flag _**-parallel, --parallel-migration=[true, false]**_ to select the Migration Mode (Parallel or Sequential). Default: true (parallel)
- [x] Included Live Dashboard in sequential Automated Migration
- [x] Minor bugs fixing

---

**Release**: v3.1.0  
**Release Date**: 2025-03-31

### Main Changes:
- [x] Support for running the Tool from Docker container.
- [x] Included Live Progress Dashboard in Automated Migration process for a better visualization of the job progress.
- [x] Added a new argument **'--source'** to specify the \<SOURCE> client for the Automated Migration process.
- [x] Added a new argument **'--target'** to specify the \<TARGET> client for the Automated Migration process.
- [x] Removed argument **'-AUTO, --AUTOMATED-MIGRATION \<SOURCE> \<TARGET>'** because have been replaced with two above arguments for a better visualization.
- [x] Added new flag '**-dashboard, --dashboard=[true, false]**' (default=true) to show/hide Live Dashboard during Atomated Migration Job.
- [x] Added new flag '**-gpthProg, --show-gpth-progress=[true, false]**' (default=false) to show/hide progress messages during GPTH processing.
- [x] Added new flag '**--gpthErr, --show-gpth-errors=[true, false]**' (default=true) to show/hide errors messages during GPTH processing.
- [x] Renamed flag '**-gitf, --google-input-takeout-folder**' to '**-gtProc, --google-takeout-to-process**' for a better understanding.
- [x] Completely refactored Automated Migration Process to allow parallel threads for Downloads and Uploads jobs avoiding downloading all assets before to upload them (this will save disk space and improve performance). Also objects support has been added to this mode for an easier implementation and future enhancements.
- [x] Support for 'Uploads Queue' to limit the max number of assets that the Downloader worker will store in the temporary folder to 100 (this save disk space). In this way the Downloader worker will never put more than 100 assets pending to Upload in the local folder.
- [x] Support Migration between 2 different accounts on the same Cloud Photo Service. 
> [!IMPORTANT] 
> **Breaking Change!**  
> Config.ini file has changed to support multi-accounts over the same Cloud Photo Service
- [x] Support to use Local Folders as SOURCE/TARGET during Automated Migration Process. Now the selected local folder works equal to other supported cloud services.
- [x] Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassTakeoutFolder, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
- [x] Added new Class ClassLocalFolder with the same methods as other supported Cloud Services Classes to manage Local Folders in the same way as a Photo Cloud Service.
- [x] ClassTakeoutFolder inherits all methods from ClassLocalFolder and includes specific methods to process Google Takeouts since at the end Google Takeout is a local folder structure.
- [x] Updated GPTH version to cop latest changes in Google Takeouts. 
- [x] Documentation completelly re-written and structured in different filels
- [x] Documentation is now included as part of the distribution packages.
- [x] Bug Fixing.

### Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/assets/screenshots/live_dashboard.jpg?raw=true)  

---

**Release**: v3.0.0  
**Date**: 2025-03-07

### Main Changes:
- [x] New Script name '**CloudPhotoMigrator**' (former 'GoogleTakeoutPhotos')
- [x] The Tool is now Open Source (all contributors that want to collaborate on this project are more than welcome)
- [x] Added **_Immich Photos Support_**.
- [x] Added **_New Automated Migration Feature_** to perform Fully Automated Migration Process between different Photo Cloud Services
  - #### AUTOMATED MIGRATION FEATURE:
    - **-AUTO,   --AUTOMATED-MIGRATION \<SOURCE> \<TARGET>**  
      This process will do an AUTOMATED-MIGRATION process to Download all your Assets
             (including Albums) from the \<SOURCE> Cloud Service and Upload them to the
             \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE>
             Cloud Service.
      
             possible values for:
                 <SOURCE> : ['google-photos', 'synology-photos', 'immich-photos'] or <INPUT_FOLDER>
                 <TARGET> : ['synology-photos', 'immich-photos']  

- [x] Fixed limit of 250 when search for Immich assets.
- [x] Fixed Remove Albums API call on Immich Photos to adapt to the new API changes.
- [x] Wildcards support on <ALBUMS_NAME> argument on --synology-download-albums and --immich-download-albums options.
- [x] Replaced 'ALL_PHOTOS' by 'No-Albums' as output subfolder for assets without any album associated (be careful if you already run the Tool with previous version because before, the folder for assets without albums was named 'ALL_PHOTOS')
- [x] Remove Dupplicates Assets in Immich Photos after upload any Asset. 
- [x] Support to upload assets from/to any folder into Synology Photos (no need to be indexed within the Synology Photos root Folder)
- [x] Added function to Remove empty folders when delete assets in Synology Photos
- [x] Ignored `@eaDir` folders when upload assets to Synology/Immich Photos.
- [x] Refactor and group All Google Takeout arguments in one block for 'Google Photos Takeout' Support.
- [X] Refactor normal_mode to google_takeout_mode.
- [x] Changed the logic to detect google_takeout_mode (former normal_mode)
- [x] Merged -z and -t options in just one option ('-gtProc, -google-takeout-to-process') and detect if contains Takeout Zip files, in that case Zip files will be Unzipped to <TAKEOUT_FOLDER>_<TIMESTAMP> folder.
- [x] Unificate a single Config.ini file and included tags for the different configuration sections.
- [x] Removed SYNOLOGY_ROOT_PHOTOS_PATH from Config.ini, since it is not needed anymore.
- [x] Removed Indexing Functions on ServiceSynology file (not needed anymore)
- [x] Included _RELEASES-NOTES.md_ and _ROADMAP.md_ files to the distribution package.
- [x] Set Log levels per functions and include '-loglevel, --log-level' argument to set it up.
- [x] Support for colors in --help text for a better visualization.
- [x] Support for colors in logger for a better visualization.
- [x] Added Help texts for Google Photos Mode.
- [x] Moved at the end of the help the standard option (those that are not related to any Support mode).
- [x] Updated -h, --help to reflect the new changes.
- [x] Code refactored.
- [x] Minor Bug Fixing.  

- [x] Renamed options:
  - -sca,  --synology-create-albums is now **suAlb,  --synology-upload-albums <ALBUMS_FOLDER>**.
  - -sea,  --synology-extract-albums is now **-sdAlb,  --synology-download-albums <ALBUMS_NAME>**.
  - -fsym, --fix-symlinks-broken <FOLDER_TO_FIX> is now **-fixSym, --fix-symlinks-broken <FOLDER_TO_FIX>**.
  - -fdup, --find-duplicates <ACTION> <DUPLICATES_FOLDER> is now **-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>**.
  - -pdup, --process-duplicates <DUPLICATES_REVISED> is now **-procdDup, --process-duplicates <DUPLICATES_REVISED>**.  

- [x] New Arguments Added: 
  - **-i,        --input-folder <INPUT_FOLDER>** Specify the input folder that you want to process.
  - **-o,        --output-folder <OUTPUT_FOLDER>** Specify the output folder to save the result of the processing action.
  - **-loglevel, --log-level ['debug', 'info', 'warning', 'error', 'critical']** Specify the log level for logging and screen messages.  
  - **-rAlbAss,  --remove-albums-assets** 
    If used together with '-srAllAlb, --synology-remove-all-albums' or '-irAllAlb, --immich-remove-all-albums',  
    it will also delete the assets (photos/videos) inside each album.
  - **-AlbFld,   --albums-folders <ALBUMS_FOLDER>**
    If used together with '-iuAll, --immich-upload-all' or '-iuAll, --immich- upload-all', 
    it will create an Album per each subfolder found in <ALBUMS_FOLDER>.  

- [x] Added new options to Synology Photos Support:
  - **-suAll,    --synology-upload-all <INPUT_FOLDER>**.  
  - **-sdAll,    --synology-download-all <OUTPUT_FOLDER>**.
  - **-srAll,    --synology-remove-all-assets** to remove All assets in Synology Photos.  
  - **-srAllAlb, --synology-remove-all-albums** to remove Albums in Synology Photos (optionally all associated assets can be also deleted).   

- [x] With those changes the **_Synology Photos Support_** has the following options:
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
    - Assets with no Albums associated will be downloaded within a subfolder 'OUTPUT_FOLDER/No-Albums/' and will have a year/month structure inside.
  - **-srEmpAlb  --synology-remove-empty-albums**  
    - The Tool will look for all Albums in your Synology Photos account and if any Album is empty, will remove it from your Synology Photos account.  
  - **-srDupAlb, --synology-remove-duplicates-albums**  
    - The Tool will look for all Albums in your Synology Photos account and if any Album is duplicated, will remove it from your Synology Photos account.
  - **-srAll,    --synology-remove-all-assets** to delete ALL assets in Synology Photos
  - **-srAllAlb, --synology-remove-all-albums** to delete ALL Albums in Synology Photos (optionally all associated assets can be also deleted).  

- [x] Added **_Immich Photos Support_** with the Following options to manage Immich API:
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
    - Assets with no Albums associated will be downloaded within a subfolder called '<OUTPUT_FOLDER>/No-Albums/' and will have a year/month structure inside.
  - **-irEmpAlb, --immich-remove-empty-albums**  
    - The Tool will look for all Albums in your Immich Photos account and if any Album is empty, will remove it from your Immich Photos account.  
  - **-irDupAlb  --immich-remove-duplicates-albums**  
    - The Tool will look for all Albums in Immich your Photos account and if any Album is duplicated, will remove it from your Immich Photos account.  
  - **-irAll,    --immich-remove-all-assets** to delete ALL assets in Immich Photos
  - **-irAllAlb, --immich-remove-all-albums** to delete ALL Albums in Immich Photos (optionally all associated assets can be also deleted).  
  - **-irOrphan, --immich-remove-orphan-assets**  
    - The Tool will look for all Orphan Assets in Immich Database and will delete them.  
    - **IMPORTANT!**: This feature requires a valid ADMIN_API_KEY configured in Config.ini.  

    
---

**Release**: v2.3.0  
**Date**: 2025-01-14

- Removed EXIF Tool (option -re, --run-exif-tool) for performance issues
- Added new argument to show the Tool version (-v, --version)
- Added new argument to Extract Albums from Synology Photos (-sea, --synology-extract-albums)
- Renamed argument -ca, --create-albums-synology-photos to -sca, --synology-create-albums
- Renamed argument -de, --delete-empty-albums-synology-photos to -sde, --synology-remove-empty-albums
- Renamed argument -dd, --delete-duplicates-albums-synology-photos to -sdd, --synology-remove-duplicates-albums
- Added Pagination option to Help text
- Code refactored
- Minor Bug Fixing

---

**Release**: v2.2.1  
**Date**: 2025-01-08

### Main Changes:
- Compiled version for different OS and Architectures
    - [x] Linux_amd64: ready
    - [x] Linux_arm64: ready
    - [x] MacOS_amd64: ready
    - [x] MacOS_arm64: ready
    - [x] Windows_amd64: ready
- GitHub Integration for version control and automate Actions
- Automated Compilation for all OS and supported Architectures
- Code refactored
- Minor Bug Fixing

---

**Release**: v2.2.0  
**Date**: 2025-01-04

### Main Changes:
- Compiled version for different OS and Architectures
    - [x] Linux_amd64: ready
    - [x] Linux_arm64: ready
    - [ ] MacOS_amd64: under development
    - [x] MacOS_arm64: ready
    - [x] Windows_amd64: ready
- Code Refactored
- Minor Bug Fixing

---

**Release**: v2.1.0  
**Date**: 2024-12-27

### Main Changes:
- Added ALL-IN-ONE mode to Automatically process your Google Takeout files (zipped or unzipped), process them, and move all your Photos & Videos into your Synology Photos personal folder creating all the Albums that you have in Google Photos within Synology Photos.
- New flag -ao,  --all-in-one <INPUT_FOLDER> to do all the process in just One Shot. The Tool will extract all your Takeout Zip files from <INPUT_FOLDER>, will process them, and finally will connect to your Synology Photos account to create all Albums found and import all the other photos without any Albums associated.
- Code Refactored
- Minor Bug Fixing


---

**Release**: v2.0.0  
**Date**: 2024-12-24

### Main Changes:
- Added Synology Photos Management options with three new Extra Features:
  -- New flag -ca,  --create-albums-synology-photos <ALBUMS_FOLDER> to force Mode: 'Create Albums in Synology Photos'. The Tool will look for all Albums within ALBUM_FOLDER and will create one Album per folder into Synology Photos.
  -- New flag -de,  --delete-empty-albums-synology-photos tofForce Mode: 'Delete Empty Albums in Synology Photos'. The Tool will look for all Albums in Synology your Photos account and if any Album is empty, will remove it from your Synology Photos account. 
  -- New flag -dd,  --delete-duplicates-albums-synology-photos tofForce Mode: 'Delete Duplicates Albums in Synology Photos'. The Tool will look for all Albums in your Synology Photos account and if any Album is duplicated, will remove it from your Synology Photos account. 
- New Flag: -ra, --rename-albums <ALBUMS_FOLDER> to rename all Albums subfolders and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  
- Support to run on Synology NAS running DSM 7.0 or higher
- Code refactored
- Minor bug fixed

---

**Release**: v1.6.0  
**Date**: 2024-12-18

### Main Changes:
- Included new flag '-pd, --process-duplicates-revised' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode' with 'duplicates-action=move'. In that case, the Tool will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanently removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : Use this action to replace the principal file chosen for each duplicate and select manually the principal file
        - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
        - and Original Principal file detected by the Script will be removed permanently
- Fixed some minor bugs.

---

**Release**: v1.5.1  
**Date**: 2024-12-17

### Main Changes:
- Fixed logic of Find_Duplicates algorithm and include a new field in the Duplicates.csv output file to provide the reason to decide principal file of a duplicates set.
- Improved performance in Find_Duplicates function..
- Included progress bar in most of all the steps that consume more time during the Tool execution.
- Fixed some minor bugs.

---

**Release**: v1.5.0  
**Date**: 2024-12-11

### Main Changes:
- Fixed Find_Duplicates function. Now is smarter and try to determine the principal folder and file when two or more files are duplicates within the same folder or in different folders.
- Added new flag '-rd, --remove-duplicates-after-fixing' to remove duplicates files in OUTPUT_FOLDER after fixing all the files. Files within any Album will have more priority than files within 'Photos from *' or 'ALL_PHOTOS' folders.
- Added new flag '-sa, --symbolic-albums' to create Symbolic linked Albums pointing to the original files. This is useful to safe disk space but the links might be broken if you move the output folders or change the structure.
- Now the Tool automatically fix Symbolic Albums when create Folder Structure per year or year/month and also after moving them into Albums folder. 
- Added new flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' to execute the Tool in Mode 'Fix Symbolic Links Broken' and try to fix all symbolics links broken within the <FOLDER_TO_FIX> folder. (Useful if you use Symbolic Albums and change the folders name or relative path after executing the Tool).
- Added new info to Final Summary section with the results of the execution.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: v1.4.1  
**Date**: 2024-12-10

### Main Changes:
- Modified Duplicates.txt output file. Now is a CSV file, and it has a new format with only one duplicate per row and one column to display the number of duplicates per each principal file and other column with the action taken with the duplicates. 
- Modified default value for No-Albums-Structure, before this folder had a 'flatten' structure, now by default the structure is 'year/month' but you can change it with the flag '-ns, --no-albums-structure'.
- Albums-Structure continues with 'flatten' value by default, but you can change it with the flag '-as, --albums-structure'.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: v1.4.0  
**Date**: 2024-12-08

### Main Changes:
- Added smart feature to Find Duplicates based on file size and content.
- Two news flags have been added to run the Tool in "Find Duplicates Mode": 
    '-fd,, --find-duplicates-in-folders' to specify the folder or folders where the Tool will look for duplicates files
    '-da, --duplicates-action' to specify the action to do with the duplicates files found.
- If any of those two flags are detected, the Tool will be executed in 'Fin Duplicates Mode', and will skip all the Steps for fixing photos. Only Find Duplicates function will be executed.
- Change help to include the new changes.
- Fixed some minor bugs.

```

Example of use:

./OrganizeTakeoutPhotos --find-duplicates-in-folders ./Albums ./ALL_PHOTOS --duplicates-action move

With this example, the Tool will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicated, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the Tool.

```

---

**Release**: v1.3.1  
**Date**: 2024-12-08

### Main Changes:
- Removed warnings when some .MP4 files does not belongs to any Live picture.

---

**Release**: v1.3.0  
**Date**: 2024-12-04

### Main Changes:
- Added Script version for MacOS 
- Included a Pre-process step (after unzipping the Zip files) to remove Synology metadata subfolders (if exists) and to look for .MP4 files generated by Google Photos that are extracted from Live picture files (.heic, .jpg, .jpeg) but doesn't have .json associated.
- Now the Tool by default doesn't skip extra files such as '-edited' or '-effect'.
- Included new argument '-se, --skip-extras' to skip processing extra files if desired.
- Now the Tool by default generates flatten output folders per each album and for ALL_PHOTOS folder (Photos without any album).
- Removed arguments '-fa, --flatten-albums' and '-fn, --flatten-no-albums' because now by default the Tool generates those folders flattened.
- Included a new function to generate a Date folder structure that can be applied either to each Album folder or to ALL_PHOTOS folder (Photos without any album) and that allow users to decide witch date folder structure wants. Valid options are: ['flatten', 'year', 'year/month', 'year-month']'.
- Included new argument '-as, --albums-structure ['flatten', 'year', 'year/month', 'year-month']' to  specify the type of folder structure for each Album folder.
- Included new argument '-ns, --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']' to specify the type of folder structure for ALL_PHOTOS folder (Photos that are no contained in any Album).
- Now the feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture is more robust since all files are flattened and there is more chance to find a Live picture with the same name of the .MP4 file in the same folder. 
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: v1.2.2  
**Date**: 2024-12-02

### Main Changes:
- Included new argument '-mt, --move-takeout-folder' to move (instead of copy) photos/albums from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>. This will let you save disk space and increase execution speed. CAUTION: With this option you will lost your original unzipped takeout files. Use this only if you have disk space limitation or if you don't care to lost the unzipped files because you still have the original zips files.
- Argument '-se, --skip-exif-tool' renamed to '-re, --run-exif-tool'. Now EXIF Tool will not be executed by default unless you include this argument when running the Tool.
- Argument '-sl, --skip-log' renamed to '-nl, --no-log-file' for better comprehension.
- New feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture. With this feature the Tool will look for files picure files (.HEIVC, .JPG, .JPEG) with the same name than .MP4 file and in the same folder. If found, then the .MP4 file will have the same timestamp than the original picture file.
- New feature to move_folders with better performance when you use the argument '-mt, --move-takeout-folder'.
- Now GPTH Tool / EXIF Tool outputs will be sent to console and logfile.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: v1.2.1  
**Date**: 2024-11-29

### Main Changes:
- Included new argument '-it, --ignore-takeout-structure' to Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
- Changed log engine to generate log.info, log.warning and log.error messages that can be parsed with any log viewer easily.
- Change help format for better reading
- Fixed bug when running in some linux environment where /tmp folder has noexec attributes
- Fixed some minor bugs.

---

**Release**: v1.2.0  
**Date**: 2024-11-27

### Main Changes:
- Script migrated to Python for multi-platform support.
- Improve performance
- replaced '-s, --skip-unzip' argument by '-z, --zip-folder <ZIP_FOLDER>'. Now if no use the argument -'z, --zip-folder <ZIP_FOLDER>., the Tool will skip unzip step.
- Improved flatten folders functions.
- Created standalone executable files for Linux & Windows platforms.
- Fixed some minor bugs.

---

**Release**: v1.0.0 to v1.2.0  
**Date**: 2024-11

### Main Changes:
- Preliminary not published Script in bash.

---
