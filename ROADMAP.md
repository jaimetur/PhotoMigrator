# ROADMAP:

## 3.0.0 (10/02/2025):
### TODO:
- [ ] Add option -srAll to remove All assets in Synology Photos
- [ ] Add option -srAlb to remove Albums in Synology Photos (optionally all associated assets can be also deleted)

- [ ] Complete function -suFld/-suAlb/-suAll to upload external folders to Synology photos. Make sure to ignore @eaDir folders in all of them
  - Try to upload folders outside Synology Photos ROOT folder
- [ ] Allow users to choose the folder where dowonload the assets for option -sdAlb and -sdAll 
  - Current implementation of -sdAlb / -sdAll does not allow this ==> Investigate other implementation

- #### Tests Pending:
- [x] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MiGRATION MODE


### DONE:

- Done tasks have been already moved to RELEASES-NOTES.md

## 3.1.0 (No estimated date):
- [ ] Include iCloud Support (just for downloading)
    - [ ] -adAlb, --apple-download-albums
    - [ ] -adAll, --apple-download-all
- [ ] Add option to filter in all Immich Actions:
    - [ ] by Dates
    - [ ] by Country
    - [ ] by City
    - [ ] by Archive
    - [ ] by Person
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo



