## 2.4.0 (28/01/2025):
### TODO:
- [ ] Ignore @eaDir folders on -suf, -sua, -iuf, -iua
- [ ] Allow user to choose between Synology Photos or Immich Photos in --all-in-one mode
- [ ] Refactor -iDA, --immich-download-all to -idA, --immich-download-ALL
- [ ] Add TQDM support on ImmichPhotos.py
- [ ] Change -sda and -ida to support wildcards on Albums name to download
- [ ] Complete function -ida to download Albums from immich
- [ ] Unificate a single Config.conf file and include tags for the different purposses
- [ ] Change version to 2.4.0

### DONE:
- [x] Add support to include sidecar files when upload assts to Immich
- [x] Improve authentication speed in Immich
- [x] Get Supported media tipe from Immich using API
- [x] Translate into English all Immich fuctions
- [x] Add release-notes.md file to the distribution package.


## 2.5.0 (No estimated date):
- [ ] Add -sdA, --synology-download-ALL
- [ ] Allow users to choose the folder where dowonload the assets for option -ida (-sda does not allow this)
- [ ] Complete function -suf to upload folders (without Albums) to Synology photos
    - [ ] Try to upload folders outside Synology Photos ROOT folder

## 3.0.0 (No estimated date):
- [ ] Support for automated migration process with the following direction;
    - [ ] Add -msrc, --migration-source (any of the 4 supported sources)
    - [ ] Add -mtgt, --migration-target (any of the 2 supported target)
    - [ ] Google Photos -> Synology Photos
    - [ ] Google Photos -> Immich Photos
    - [ ] Apple Photos -> Synology Photos
    - [ ] Apple Photos -> Immich Photos
    - [ ] Synology Photos -> Immich Photos
    - [ ] Immich Photos -> Synology Photos
- [ ] Cange repository name to PhotosMigrationTool or GooglePhotosMigration
    - [ ] Change both, prod snd dev repos
    - [ ] Change build.yml in dev repo to point to new prod repo
    - [ ] Change PyCharm origin in case of use a new repo instead of rename the current one
- [ ] Include iCloud Support (just for downloading)
    - [ ] -ada, --apple-download-albums
    - [ ] -adA, --apple-download-ALL

