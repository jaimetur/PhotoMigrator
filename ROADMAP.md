# ROADMAP:

## 3.0.0 (10/02/2025):
### TODO:
- -irEmpAlb
- -irDupAlb
- -irOrphan
- -irAllAlb
- -irAllAss / -irALL

- -srEmpAlb
- -srDupAlb
- -srAllAlb
- -srAllAss / -srALL

- [ ] Replace -sdea to -srea and -synology-delete-empty-albums to -synology-remove-empty-albums
- [ ] Replace -sdda to -srda and -synology-delete-duplicates-albums to -synology-remove-duplicates-albums
- [ ] Replace -idea to -irea and -immich-delete-empty-albums to -immich-remove-empty-albums
- [ ] Replace -idda to -irda and -immich-delete-duplicates-albums to -immich-remove-duplicates-albums
- [ ] Replace -idoa to -iroa and -immich-delete-orphan-assets to -immich-remove-orphan-assets
- [ ] Replace -ideAll to -irAll and -immich-delete-all-assets to -immich-remove-all-assets
- [ ] Replace -ideAlb to -irAlb and -immich-delete-all-albums to -immich-remove-all-albums
- [ ] Group all remove options together at the end

- [ ] Add option -srAll to remove All assets in Synology Photos
- [ ] Add option -srAlb to remove Albums in Synology Photos (optionally all associated assets can be also deleted)

- [ ] Check if makes sense to keep current -suFld / iuFld, renaming them to -sunoAlb / -iunoAlb or is enough with the options -suAll / -iuAll adding a flag -woAlb, --without-albums to avoid create Albums

- [ ] Allow users to choose the folder where dowonload the assets for option -sdAlb and -sdAll 
  - current implementation of -sdAlb does not allow this ==> Investigate other implementation
- [ ] Complete function -suFld / -suAll to upload external folders (without Albums) to Synology photos. Make sure than ignore @eaDir folders
  - Try to upload folders outside Synology Photos ROOT folder

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
- [ ] Add option to filter by dates in all Immich Actions
- [ ] Add option to filter by person in all Immich Actions
- [ ] Add option to filter by city/country in all Immich Actions
- [ ] Add option to filter Archive in all Immich Actions
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
- [ ] Create a New Release in Github Production Repo



