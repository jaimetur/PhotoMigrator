# ROADMAP:

## 3.0.0 (14/02/2025):
### TODO:

- [ ] Set Log levels per functions
- [ ] Upload assets to PhotoLibrary folder
- [ ] Remove empty folders when delete assets
- [ ] Support to upload/download assets from/to any folder (no need to be indexed within the Synology Photos root Folder
- [ ] Refactor -suAll, -sdAll, -iuAll, -idAll
- [ ] Removed SYNOLOGY_PHOTOS_ROOT_FOLDER from CONFIG.ini file (not needed anymore)
- [ ] Refactor CONFIG.ini to config.ini
- [ ] Remove Indexing Functions on ServiceSynology file
- [x] Complete function -suAlb/-suAll to upload external folders to Synology photos. Make sure to ignore @eaDir folders in all of them
- [ ] Allow users to choose the folder where download the assets for option -sdAlb and -sdAll 
  - Current implementation of -sdAlb / -sdAll does not allow this ==> Investigate other implementation

- #### Tests Pending:
- [x] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MIGRATION MODE


### DONE:

- Done tasks have been already moved to RELEASES-NOTES.md

## 4.0.0 (No estimated date):
- [ ] Include Apple Support (just for downloading)
    - [ ] -adAlb, --apple-download-albums
    - [ ] -adAll, --apple-download-all
- [ ] Include native support for Google Photos through API
    - See: https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef
- [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATED-MODE
- [ ] Add option to filter in all Immich Actions:
    - [ ] by Dates
    - [ ] by Country
    - [ ] by City
    - [ ] by Archive
    - [ ] by Person
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in GitHub Production Repo



