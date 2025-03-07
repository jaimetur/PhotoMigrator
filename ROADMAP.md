# ROADMAP:

## 3.1.0 (No estimated date):
### TODO:
- [ ] Included Progress Dashboard for AUTOMATED MIGRATION MODE for a better visualization.
- [x] Added Threads suppport on AUTOMATED MIGRATION MODE to parallelize Downloads and Uploads and avoid to download All assets before to upload them (this will safe disk space and improve performance).
- [x] Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassGoogleTakeout, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
- [x] Minor Bug Fixing.

- #### Tests Pending:
- [ ] Deep Test on Immich Support functions
- [ ] Deep Test on Synology Support functions
- [ ] Deep Test on Google Photos function
- [ ] Deep Test on --AUTOMATED-MIGRATION MODE

### DONE:
- Done tasks have been already moved to RELEASES-NOTES.md

## 4.0.0 (No estimated date):
- [ ] Include Apple Support (just for downloading)
    - [ ] -adAlb, --apple-download-albums
    - [ ] -adAll, --apple-download-all
    - [ ] -auAlb, --apple-upload-albums
    - [ ] -auAll, --apple-upload-all
- [ ] Include native support for Google Photos through API  
  (See: https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef)
    - [ ] -gdAlb, --google-download-albums
    - [ ] -gdAll, --google-download-all
    - [ ] -guAlb, --google-upload-albums
    - [ ] -guAll, --google-upload-all
- [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATED-MODE
- [ ] Add option to filter in all Immich Actions:
    - [ ] by Dates
    - [ ] by Country
    - [ ] by City
    - [ ] by Archive
    - [ ] by Person
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md