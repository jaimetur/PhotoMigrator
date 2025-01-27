## Download Latest Script:
Download the script either Linux, MacOS or Windows version (for both x64/amd64 or arm64 architectures) as you prefeer directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_macos_arm64.zip)  

**Windows:**  
- [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_windows_amd64.zip)

---

## Release Notes:

**Release**: 3.0.0  
**Date**: 2025-01-27

- Renamed options:
  - -sea, --synology-extract-albums is now **-sda, --synology-download-albums**
  - -sca, --synology-create-albums is now **-sua, --synology-upload-albums**


- Added new option to Synology Photos Support:
  - **-suf, --synology-upload-folder <FOLDER>**  
          The script will look for all Photos/Videos within <FOLDER> and will upload them into Synology Photos.


- With those changes Synology Photos support and Immich Photos support has the same options. For Synology Photos, the options are:
  - **-suf, --synology-upload-folder <FOLDER>**  
          The script will look for all Photos/Videos within <FOLDER> and will upload them into Synology Photos.
  - **-sua, --synology-upload-albums <ALBUMS_FOLDER>**  
          The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Synology Photos.
  - **-sda, --synology-download-albums <ALBUMS_NAME>**  
          The Script will connect to Synology Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder.  
          To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3".  
          To download ALL Albums use "ALL" as <ALBUMS_NAME>.  
  - **-sde, --synology-delete-empty-albums**  
          The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database.  
  - **-sdd, --synology-delete-duplicates-albums**  
          The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.
  

- Added Support for Immich Photos. Following options are available to manage Immich Photos API:
  - **-iuf, --immich-upload-folder <FOLDER>**    
          The script will look for all Photos/Videos within <FOLDER> and will upload them into Immich Photos.  
  - **-iua, --immich-upload-albums <ALBUMS_FOLDER>**  
          The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Immich Photos.  
  - **-ida, --immich-download-albums <ALBUMS_NAME>**  
          The Script will connect to Immich Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder.  
          To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums" "album1", "album2", "album3".  
          To download ALL Albums use "ALL" as <ALBUMS_NAME>.   
  **-iDA, --immich-download-all <FOLDER>**  
          The Script will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <FOLDER>.  
          - All Albums will be downloaded within a subfolder of <FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.  
          Assets with no Albums associated will be downloaded withn a subfolder called <FOLDER>/Others/ and will have a year/month structure inside.
  - **-ide, --immich-delete-empty-albums**  
          The script will look for all Albums in Immich Photos database and if any
          Album is empty, will remove it from Immich Photos database.  
  - **-idd, --immich-delete-duplicates-albums**  
          The script will look for all Albums in Immich Photos database and if any
          Album is duplicated, will remove it from Immich Photos database.


- Added support to include sidecar files when upload assts to Immich
- Get Supported media tipe from Immich using API
- Improved authentication speed in Immich
- Included **release-notes.md** file in the distribution package.
- Updated -h, --help to refflect the new changes.
- Code refactored.
- Minor Bug Fixing.

---

**Release**: 2.3.0  
**Date**: 2025-01-14

- Removed EXIF Tool (option -re, --run-exif-tool) for performance issues
- Added new argument to show script version (-v, --version)
- Added new argument to Extract Albums from Synology Photos (-sea, --synology-extract-albums)
- Renamed argument -ca, --create-albums-synology-photos to -sca, --synology-create-albums
- Renamed argument -de, --delete-empty-albums-synology-photos to -sde, --synology-delete-empty-albums
- Renamed argument -dd, --delete-duplicates-albums-synology-photos to -sdd, --synology-delete-duplicates-albums
- Added Pagination option to Help text
- Code refactored
- Minor Bug Fixing

---

**Release**: 2.2.1  
**Date**: 2025-01-08

- Compiled version for different OS and Architectures
    - [x] Linux_amd64: ready
    - [x] Linux_arm64: ready
    - [x] MacOS_amd64: ready
    - [x] MacOS_arm64: ready
    - [x] Windows_amd64: ready
- GitHub Integration for version control and automate Actions
- Automated Compilation for all OS and supported Arquitectures
- Code refactored
- Minor Bug Fixing

---

**Release**: 2.2.0  
**Date**: 2025-01-04

- Compiled version for different OS and Architectures
    - [x] Linux_amd64: ready
    - [x] Linux_arm64: ready
    - [ ] MacOS_amd64: under development
    - [x] MacOS_arm64: ready
    - [x] Windows_amd64: ready
- Code Refactored
- Minor Bug Fixing

---

**Release**: 2.1.0  
**Date**: 2024-12-27

- Added ALL-IN-ONE mode to Automatically process your Google Takeout files (zipped or unzipped), process them, and move all your Photos & Videos into your Synology Photos personal folder creating all the Albums that you have in Google Photos within Synology Photos.
- New flag -ao,  --all-in-one <INPUT_FOLDER> to do all the process in just One Shot. The script will extract all your Takeout Zip files from <INPUT_FOLDER>, will process them, and finally will connect to Synology Photos database to create all Albums found and import all the other photos without any Albums associated.
- Code Refactored
- Minor Bug Fixing


---

**Release**: 2.0.0  
**Date**: 2024-12-24

- Added Synology Photos Management options with three new Extra Modes:
  -- New flag -ca,  --create-albums-synology-photos <ALBUMS_FOLDER> to force Mode: 'Create Albums in Synology Photos'. The script will look for all Albums within ALBUM_FOLDER and will create one Album per folder into Synology Photos.
  -- New flag -de,  --delete-empty-albums-synology-photos tofForce Mode: 'Delete Empty Albums in Synology Photos'. The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database. 
  -- New flag -dd,  --delete-duplicates-albums-synology-photos tofForce Mode: 'Delete Diplicates Albums in Synology Photos'. The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database. 
- New Flag: -ra, --rename-albums <ALBUMS_FOLDER> to rename all Albums subfolders and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  
- Support to run on Synology NAS running DSM 7.0 or higher
- Code refactored
- Minor bug fixed

---

**Release**: 1.6.0  
**Date**: 2024-12-18

- Included new flag '-pd, --process-duplicates-revised' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode' with 'duplicates-action=move'. In that case, the script will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : Use this action to replace the principal file chosen for each duplicates and select manually the principal file
        - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
        - and Original Principal file detected by the Script will be removed permanently
- Fixed some minor bugs.

---

**Release**: 1.5.1  
**Date**: 2024-12-17

- Fixed logic of Find_Duplicates algorithm and include a new field in the Duplicates.csv output file to provide the reasson to decide principal file of a duplicates set.
- Improved performance in Find_Duplicates function..
- Included progress bar in most of all the steps that consume more time during script execution.
- Fixed some minor bugs.

---

**Release**: 1.5.0  
**Date**: 2024-12-11

- Fixed Find_Duplicates function. Now is more smart and try to determine the principal folder and file when two or more files are duplicates within the same folder or in different folders.
- Added new flag '-rd, --remove-duplicates-after-fixing' to remove duplicates files in OUTPUT_FOLDER after fixing all the files. Files within any Album will have more priority than files within 'Photos from *' or 'ALL_PHOTOS' folders.
- Added new flag '-sa, --symbolic-albums' to create Symbolik linked Albums pointing to the original files. This is useful to safe disk space but the links might be broken if you move the output folders or change the structure.
- Now the script automatically fix Symbolic Albums when create Folder Structure per year or year/month and also after moving them into Albums folder. 
- Added new flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' to execute the script in Mode 'Fix Symbolic Links Broken' and try to fix all symbolics links broken within the <FOLDER_TO_FIX> folder. (Useful if you use Symbolic Albums and change the folders name or relative path after executing the script).
- Added new info to Final Summary section with the results of the execution.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: 1.4.1  
**Date**: 2024-12-10

- Modified Duplicates.txt output file. Now is a CSV file and it has a new format with only one duplicate per row and one column to display the number of duplicates per each principal file and other column with the action taken with the duplicates. 
- Modified default value for No-Albums-Structure, before this folder had a 'flatten' structure, now by default the structure is 'year/month' but you can change it with the flag '-ns, --no-albums-structure'.
- Albums-Structure continues with 'flatten' value by default but you can change it with the flag '-as, --albums-structure'.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: 1.4.0  
**Date**: 2024-12-08

- Added smart feature to Find Duplicates based on file size and content.
- Two news flags have been added to run the script in "Find Duplicates Mode": 
    '-fd,, --find-duplicates-in-folders' to specify the folder or folders where the script will look for duplicates files
    '-da, --duplicates-action' to specify the action to do with the duplicates files found.
- If any of those two flags are detected, the script will be executed in 'Fin Duplicates Mode', and will skip all the Steps for fixing photos. Only Find Duplicates function will be executed.
- Change help to include the new changes.
- Fixed some minor bugs.

```

Example of use:

./OrganizeTakeoutPhotos --find-duplicates-in-folders ./Albums ./ALL_PHOTOS --duplicates-action move

With this example, the script will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicated, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the script.

```

---

**Release**: 1.3.1  
**Date**: 2024-12-08

- Removed warnings when some .MP4 files does not belongs to any Live picture.

---

**Release**: 1.3.0  
**Date**: 2024-12-04

- Added Script version for MacOS 
- Included a Pre-process step (after unzipping the Zip files) to remove Synoglogy metadata subfolders (if exists) and to look for .MP4 files generated by Google Photos that are extracted from Live picture files (.heic, .jpg, .jpeg) but doesn't have .json associated.
- Now the script by default doesn't skip extra files such as '-edited' or '-effect'.
- Included new argument '-se, --skip-extras' to skip processing extra files if desired.
- Now the script by default generates flatten output folders per each album and for ALL_PHOTOS folder (Photos without any album).
- Removed arguments '-fa, --flatten-albums' and '-fn, --flatten-no-albums' because now by default the script generates those folders flattened.
- Included a new function to generate a Date folder structure that can be applied either to each Album folder or to ALL_PHOTOS folder (Photos without any album) and that allow users to decide witch date folder structure wants. Valid options are: ['flatten', 'year', 'year/month', 'year-month']'.
- Included new argument '-as, --albums-structure ['flatten', 'year', 'year/month', 'year-month']' to  specify the type of folder structure for each Album folder.
- Included new argument '-ns, --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']' to specify the type of folder structure for ALL_PHOTOS folder (Photos that are no contained in any Album).
- Now the feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture is more robust since all files are flattened and there is more chance to find a Live picture with the same name of the .MP4 file in the same folder. 
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: 1.2.2  
**Date**: 2024-12-02

- Included new argument '-mt, --move-takeout-folder' to move (instead of copy) photos/albums from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>. This will let you save disk space and increase execution speed. CAUTION: With this option you will lost your original unzipped takeout files. Use this only if you have disk space limitation or if you don't care to lost the unzipped files because you still have the original zips files.
- Argument '-se, --skip-exif-tool' renamed to '-re, --run-exif-tool'. Now EXIF Tool will not be executed by default unless you include this argument when running the script.
- Argument '-sl, --skip-log' renamed to '-nl, --no-log-file' for better comprenhension.
- New feature to auto-sync timestamp of .MP4 files generated for Google Photos when a picture is a Live picture. With this feature the script will look for files picure files (.HEIVC, .JPG, .JPEG) with the same name than .MP4 file and in the same folder. If found, then the .MP4 file will have the same timestamp than the original picture file.
- New feature to move_folders with better performance when you use the argument '-mt, --move-takeout-folder'.
- Now GPTH Tool / EXIF Tool outputs will be send to console and logfile.
- Change help to include the new changes.
- Fixed some minor bugs.

---

**Release**: 1.2.1  
**Date**: 2024-11-29

- Included new argument '-it, --ignore-takeout-structure' to Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
- Changed log engine to generate log.info, log.warning and log.error messages that can be parsed with any log viewer easily.
- Change help format for better reading
- Fixed bug when running in some linux environment where /tmp folder has noexec attributes
- Fixed some minor bugs.

---

**Release**: 1.2.0  
**Date**: 2024-11-27

- Script migrated to Python for multi-plattform support.
- Improve performance
- replaced '-s, --skip-unzip' argument by '-z, --zip-folder <ZIP_FOLDER>'. Now if no use the argument -'z, --zip-folder <ZIP_FOLDER>., the script will skip unzip step.
- Improved flatten folders functions.
- Created standalone executable files for Linux & Windows platforms.
- Fixed some minor bugs.

---

**Release**: 1.0.0 to 1.2.0  
**Date**: 2024-11

- Preeliminary not published Script in bash.

---
