# ROADMAP:

## 3.0.0 (10/02/2025):
### TODO:
- [ ] Add option to remove All assets in Synology Photos
- [ ] Add option to remove Albums in Synology Photos (optinally all associated assets can be also deleted)
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in GitHub Production Repo

- #### Tests Pending:
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MiGRATION MODE


### DONE:

- [x] New Script name 'CloudPhotoMigrator' (former 'GoogleTakeoutPhotos')
- [x] Added Support for Immich Photos
- [x] Added new option ( -suf, --synology-upload-folder') in Synology Photos Support to upload asets without a local folder without associate them to ant album. 
- [x] Added new option ( -sdA, --synology-download-ALL') in Synology Photos Support to download ALL asets (with and without Albums assciated). 
- [x] Added new option ( -ido, --immich-delete-orphan-assets) to delete orphan assets in Immich Photos
- [x] Added new option ( -idas, --immich-delete-ALL-assets) to delete ALL assets in Immich Photos
- [x] Added new option ( -idal, --immich-delete-ALL-albums) to delete ALL Albums in Immich Photos (optinally all associated assets can be also deleted)
- [x] Renamed options of Synology Photos support to homogenize with Immich Photos support
- [x] Changed -sda/-ida to support wildcards on Albums name to download
- [x] Ignored @eaDir folders on -iuf, -iua, -sua
- [x] Replaced 'ALL_PHOTOS' by 'Others' as output subfolder for assets without any album associated (be careful if you already run the script with previous version because before, the folder for assets without albums was named 'ALL_PHOTOS')
- [x] Added colors to --help text for a better visualization.
- [x] Refactor and group All Google Takeout arguments in one block for 'Google Photos Takeout' Support
- [X] Refactor normal_mode to google_takeout_mode
- [x] Merged -z and -t options in just one option ('-gitf, -google-input-takeout-folder') and detect if contains Takeout Zip files, in that case Zip files will be Unzipped to <TAKEOUT_FOLDER>_TIMESTAMP folder
- [x] Unificated a single Config.ini file and included tags for the different configuration sections
- [x] Added Help text for Google Photos Mode
- [x] Changed the logic to detect google_takeout_mode (former normal_mode)
- [x] Put at the end of the help the standard option (those that are not related to any Support mode)
- [x] Added RELEASES-NOTES.md file to the distribution package.
- [x] Updated README.md
- #### Automated Migration:
- [x] Created functions synology_upload_ALL(input_folder) and immich_upload_ALL(input_folder) to upload:
    - 1. Album folder (if exists) with synology_upload_albums() and immich_upload_albums()
    - 2. Others folder (if exists), if not, upload All input_folder with synology_upload_folder() and immich_upload_folder()
- [x] Changed Option -ao, --all-in-one <INPUT_FOLDER> to -AUTO, --AUTOMATED-MODE <SRC> <TGT> with the following ALLOWED_SRC and ALLOWED_TGT:
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
- [ ] Add option to filter by dates in all Immich Actions
- [ ] Add option to filter by person in all Immich Actions
- [ ] Add option to filter by city/country in all Immich Actions
- [ ] Add option to filter Archive in all Immich Actions
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo



