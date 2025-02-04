# ROADMAP:

## 3.0.0 (10/02/2025):
### TODO:
- [ ] Add option to remove All assets in Synology Photos
- [ ] Add option to remove Albums in Synology Photos (optinally all associated assets can be also deleted)

- #### Tests Pending:
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MiGRATION MODE


### DONE:

- Done tasks have been already moved to RELEASES-NOTES.md

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



