# ROADMAP:

## 2.4.0 (31/01/2025):
### TODO:
- [ ] Unificate a single Config.conf file and include tags for the different purposses
- [ ] Merge -z and -t options in just one -gtf, -google-photos-takeout-folder and detect if contains Takeout Zip files, in that case Unzip to Takeout folder, if not, make Takeout folder = Input folder
- [ ] Create GLOBAL variables to map arguments into them in ParseArguments() or separate in a new function

- [ ] DEPRECATE: Allow user to choose between Synology Photos or Immich Photos in --all-in-one mode
- [ ] Refactor -ao, --all-in-one to -am, --automated-migration <SRC> <TGT> and identify if <SRC> is an <INPUT_FOLDER> or one of the ALLOWED_SOURCES=['google-photos', 'apple-photos', 'synology-photos', 'immich-photos']. If is 'google-photos' look for -t or -z arguments or prompt to the user to introduce the Google Takeout Folder
- [ ] Refactor Google Photos arguments
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function

### DONE:
- [x] Add Support for Immich Photos
  - [x] Add support to include sidecar files when upload assts to Immich
  - [x] Improve authentication speed in Immich
  - [x] Get Supported media type from Immich using API
  - [x] Translate into English all Immich fuctions
  - [x] Test function -ida to download Albums from immich
- [x] Change version to 2.4.0-alpha
- [x] Create local and remote branches for 2.4.0, 2.5.0 and 3.0.0
- [x] Add TQDM support on ImmichPhotos.py
- [x] Ignore @eaDir folders on -iuf, -iua, -sua
- [x] Replaced ALL_PHOTOS by Others in all the project files (be careful)
- [x] Add RELEASES-NOTES.md file to the distribution package.
- [x] Change -sda and -ida to support wildcards on Albums name to download
- [x] Modify build.yml to update RELEASE-NOTES.md and ROADMAP.md into production repository
- [x] Renamed options of Synology Photos support to homogenize with Immich Photos support
- [x] Put at the beginning the standard option (those that are not related to any Support mode)

## 2.5.0 (No estimated date):
- [x] Add -sdA, --synology-download-ALL
- [ ] Allow users to choose the folder where dowonload the assets for option -ida (-sda does not allow this)
- [ ] Try to upload folders outside Synology Photos ROOT folder
- [ ] Complete function -suf to upload external folders (without Albums) to Synology photos. Make sure than ignore @eaDir folders
- [ ] Change -sdA to Download assets with no albums to an external folder
  
## 3.0.0 (No estimated date):
- [ ] Change repository name to PhotosMigrationTool or GooglePhotosMigration
    - [ ] Change both, prod and dev repos
    - [ ] Change build.yml in dev repo to point to new prod repo
    - [ ] Change PyCharm origin in case of use a new repo instead of rename the current one
- [ ] Include iCloud Support (just for downloading)
    - [ ] -ada, --apple-download-albums
    - [ ] -adA, --apple-download-ALL
- [ ] Refactor and group All Google Takeout options in one block for Google Photos Takeout Support
- [ ] Refactor normal_mode to google_takeout_mode
- [ ] Change the logic to detect google_takeout_mode (former normal_mode)
- [ ] Change README.md to reflect all changes and change Script description
- [ ] Replace -al, --all-in-one-shot by following Automated Migration Process
- [ ] Support for Automated Migration process with the following direction:
    - [ ] Add -msrc, --migration-source (any of the 4 supported sources)
    - [ ] Add -mtgt, --migration-target (any of the 2 supported target)
    - [ ] Google Photos -> Synology Photos
    - [ ] Google Photos -> Immich Photos
    - [ ] Apple Photos -> Synology Photos
    - [ ] Apple Photos -> Immich Photos
    - [ ] Synology Photos -> Immich Photos
    - [ ] Immich Photos -> Synology Photos

