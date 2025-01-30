# ROADMAP:

## 2.4.0 (31/01/2025):
### TODO:
- [ ] Refactor and group All Google Takeout arguments in one block for 'Google Photos Takeout' Support
- [ ] Merge -z and -t options in just one -gtf, -google-takeout-folder and detect if contains Takeout Zip files, in that case Unzip to Takeout folder, if not, make Takeout folder = Input folder
- [ ] Change the logic to detect google_takeout_mode (former normal_mode)


- [ ] Unificate a single Config.conf file and include tags for the different purposses
- [ ] _DEPRECATED_: Allow user to choose between Synology Photos or Immich Photos in --all-in-one mode
- [ ] Change Help for HELP_MODE_GOOGLE_TAKEOUT

- [ ] Change Script description on README.md
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo

- #### Testing:
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function

### DONE:
- [x] Added Support for Immich Photos
  - [x] Added support to include sidecar files when upload assts to Immich
  - [x] Improved authentication speed in Immich
  - [x] Got Supported media type from Immich using API
  - [x] Translated into English all Immich fuctions
  - [x] Tested function -ida to download Albums from immich
- [x] Changed version to 2.4.0-alpha
- [x] Created local and remote branches for 2.4.0, 2.5.0 and 3.0.0
- [x] Created GLOBAL variable ARG to map arguments into it in ParseArguments() in order to facilitate future refactoring of arguments.
- [x] Added TQDM support on ImmichPhotos.py
- [x] Ignored @eaDir folders on -iuf, -iua, -sua
- [x] Replaced 'ALL_PHOTOS' by 'Others' as output subfolder for assets without any album associated (be careful if you already run the script with previous version because before, the folder for assets without albums was named 'ALL_PHOTOS')
- [x] Added colors to --help text for a better visualization.
- [X] Refactor normal_mode to google_takeout_mode
- [x] Put at the beginning the standard option (those that are not related to any Support mode)
- [x] Changed -sda/-ida to support wildcards on Albums name to download
- [x] Renamed options of Synology Photos support to homogenize with Immich Photos support
- [x] Added RELEASES-NOTES.md file to the distribution package.
- [x] Modified build.yml to update RELEASE-NOTES.md and ROADMAP.md into production repository

## 2.5.0 (No estimated date):
- [x] Add -sdA, --synology-download-ALL
- [ ] Allow users to choose the folder where dowonload the assets for option -ida/-sda and -idA/-sdA 
  - current implementation of -sda does not allow this ==> Investigate other implementation
- [ ] Change -sdA to Download assets with no albums to an external folder
  - current implementation of -sda does not allow this ==> Investigate other implementation
- [ ] Complete function -suf to upload external folders (without Albums) to Synology photos. Make sure than ignore @eaDir folders
  - Try to upload folders outside Synology Photos ROOT folder (for -suf option)
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo
  
## 3.0.0 (No estimated date):
- [ ] Change repository name to PhotosMigrationTool or GooglePhotosMigration
    - [ ] Change both, prod and dev repos
    - [ ] Change build.yml in dev repo to point to new prod repo
    - [ ] Change PyCharm origin in case of use a new repo instead of rename the current one
- [ ] Include iCloud Support (just for downloading)
    - [ ] -ada, --apple-download-albums
    - [ ] -adA, --apple-download-ALL
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo

- #### Automated Migration:
- [ ] Create functions synology_upload_ALL(input_folder) and immich_upload_ALL(input_folder) to upload:
  - 1. Album folder (if exists) with synology_upload_albums() and immich_upload_albums()
  - 2. Others folder (if exists), if not, upload All imput_folder with synology_upload_folder() and immich_upload_folder()
- [ ] Refactor -ao, --all-in-one <INPUT_FOLDER> to -am, --automated-migration <SRC> <TGT> with the following ALLOWED_SRC and ALLOWED_TGT:
  - ALLOWED_SRC=['google-photos', 'apple-photos', 'synology-photos', 'immich-photos'] or <INPUT_FOLDER>, in that case directly will upload ALL to <TGT>  
  - ALLOWED_TGT=['synology-photos', 'immich-photos']. --> Call synology_upload_ALL() or immich_upload_ALL() with the <INPUT_FOLDER>  
  - If is 'google-photos' look for -t or -z arguments or prompt to the user to introduce the Google Takeout Folder



