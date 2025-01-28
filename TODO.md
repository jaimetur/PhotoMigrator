# ROADMAP:

## 2.4.0 (31/01/2025):
### TODO:
- [ ] Change version to 2.4.0
- [ ] Refactor release-notes.md to RELEASES-NOTES.md
- [ ] Refactor TODO.md to ROADMAP.md
- [ ] Refactor -iDA, --immich-download-all to -idA, --immich-download-ALL

- [ ] Ignore @eaDir folders on -suf, -sua, -iuf, -iua
- [ ] Add TQDM support on ImmichPhotos.py
- [ ] Test function -ida to download Albums from immich
- [ ] Change -sda and -ida to support wildcards on Albums name to download
- [ ] Unificate a single Config.conf file and include tags for the different purposses
- [ ] Complete function -suf to upload folders (without Albums) to Synology photos
- [ ] Allow user to choose between Synology Photos or Immich Photos in --all-in-one mode

### DONE:
- [x] Add Support for Immich Photos
    - [x] Add support to include sidecar files when upload assts to Immich
    - [x] Improve authentication speed in Immich
    - [x] Get Supported media type from Immich using API
    - [x] Translate into English all Immich fuctions
- [x] Add release-notes.md file to the distribution package.
- [x] Renamed options of Synology Photos support to homogenize with Immich Photos support

## 2.5.0 (No estimated date):
- [ ] Add -sdA, --synology-download-ALL
- [ ] Allow users to choose the folder where dowonload the assets for option -ida (-sda does not allow this)
- [ ] Try to upload folders outside Synology Photos ROOT folder

## 3.0.0 (No estimated date):
- [ ] Change repository name to PhotosMigrationTool or GooglePhotosMigration
    - [ ] Change both, prod snd dev repos
    - [ ] Change build.yml in dev repo to point to new prod repo
    - [ ] Change PyCharm origin in case of use a new repo instead of rename the current one
- [ ] Include iCloud Support (just for downloading)
    - [ ] -ada, --apple-download-albums
    - [ ] -adA, --apple-download-ALL
- [ ] Refactor and group All Google Takeout options in one block for Google Photos Takeout Support
- [ ] Put at the beginning the standard option (thise that are not related to any Support mode)
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

