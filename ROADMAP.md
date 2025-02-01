# ROADMAP:

## 3.0.0 (10/02/2025):
### TODO:
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo

- #### Tests Pending:
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MiGRATION MODE


### DONE:
- [x] Change repository name to CloudPhotoMigrator
      - [x] Change both, prod and dev repos
      - [x] Change build.yml in dev repo to point to new prod repo
      - [x] Change Script name
      - [x] Change Script file name
      - [x] Change PyCharm origin
- [x] New Script name 'CloudPhotoMigrator' (former 'GoogleTakeoutPhotos')
- [x] Added Support for Immich Photos
    - [x] Added support to include sidecar files when upload assts to Immich
    - [x] Improved authentication speed in Immich
    - [x] Got Supported media type from Immich using API
    - [x] Translated into English all Immich fuctions
    - [x] Tested function -ida to download Albums from immich
- [x] Added new option( -suf, --synology-upload-folder') in Synology Photos Support to upload asets without a local folder without associate them to ant album. 
- [x] Added new option( -sdA, --synology-download-ALL') in Synology Photos Support to download ALL asets (with and without Albums assciated). 
- [x] Renamed options of Synology Photos support to homogenize with Immich Photos support
- [x] Changed -sda/-ida to support wildcards on Albums name to download
- [x] Changed version to 3.0.0-alpha
- [x] Created local and remote branches for 3.0.0
- [x] Created GLOBAL variable ARG to map arguments into it in ParseArguments() in order to facilitate future refactoring of arguments.
- [x] Added TQDM support on ImmichPhotos.py
- [x] Ignored @eaDir folders on -iuf, -iua, -sua
- [x] Replaced 'ALL_PHOTOS' by 'Others' as output subfolder for assets without any album associated (be careful if you already run the script with previous version because before, the folder for assets without albums was named 'ALL_PHOTOS')
- [x] Added colors to --help text for a better visualization.
- [x] Refactor and group All Google Takeout arguments in one block for 'Google Photos Takeout' Support
- [X] Refactor normal_mode to google_takeout_mode
- [x] Merged -z and -t options in just one option ('-gitf, -google-input-takeout-folder') and detect if contains Takeout Zip files, in that case Zip files will be Unzipped to <TAKEOUT_FOLDER>_TIMESTAMP folder
- [x] Unificated a single Config.ini file and included tags for the different configuration sections
- [x] Changed Help for HELP_MODE_GOOGLE_TAKEOUT
- [x] Changed the logic to detect google_takeout_mode (former normal_mode)
- [x] Put at the end of the help the standard option (those that are not related to any Support mode)
- [x] Added RELEASES-NOTES.md file to the distribution package.
- [x] Modified build.yml to update RELEASE-NOTES.md and ROADMAP.md into production repository
- [x] Change Script description on README.md
- [x] Update README.md
- #### Automated Migration:
- [x] Create functions synology_upload_ALL(input_folder) and immich_upload_ALL(input_folder) to upload:
    - 1. Album folder (if exists) with synology_upload_albums() and immich_upload_albums()
    - 2. Others folder (if exists), if not, upload All input_folder with synology_upload_folder() and immich_upload_folder()
- [x] Refactor -ao, --all-in-one <INPUT_FOLDER> to -AUTO, --AUTOMATED-MODE <SRC> <TGT> with the following ALLOWED_SRC and ALLOWED_TGT:
    - ALLOWED_SRC=['google-photos', 'synology-photos', 'immich-photos'] or <INPUT_FOLDER>, in that case directly will upload ALL to <TGT>  
    - ALLOWED_TGT=['synology-photos', 'immich-photos']. --> Call synology_upload_ALL() or immich_upload_ALL() with the <INPUT_FOLDER>  
    - If is 'google-photos' look for -i <INPUT_FOLDER> argument to define the Google Takeout Folder


## 3.1.0 (No estimated date):
- [ ] Include iCloud Support (just for downloading)
    - [ ] -ada, --apple-download-albums
    - [ ] -adA, --apple-download-ALL
- [ ] Allow users to choose the folder where dowonload the assets for option -ida/-sda and -idA/-sdA 
  - current implementation of -sda does not allow this ==> Investigate other implementation
- [ ] Change -sdA to Download assets with no albums to an external folder
  - current implementation of -sda does not allow this ==> Investigate other implementation
- [ ] Complete function -suf to upload external folders (without Albums) to Synology photos. Make sure than ignore @eaDir folders
  - Try to upload folders outside Synology Photos ROOT folder (for -suf option)
- [ ] Add options to delete All Albums and delete All Assets for Immich/Synology Photos
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo



