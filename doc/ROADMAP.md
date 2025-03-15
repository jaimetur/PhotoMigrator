# ROADMAP:

## v3.1.0
### Release Date: (estimated)
  - Alpha version.   : 2025-03-14
  - Beta version     : 2025-03-21
  - Release Candidate: 2025-03-28
  - Official Release : 2025-03-31

### TODO:
- [x] Included Live Progress Dashboard in AUTOMATED MIGRATION MODE for a better visualization of the job progress.
- [x] Added new flag '**--dashboard=[true, false]**' (default=true) to show/hide Live Dashboard during Atomated Migration Job.
- [x] Completelly refactored AUTOMATED-MIGRATION MODE to allow parallel threads for Downloads and Uploads jobs avoiding downloading all assets before to upload them (this will save disk space and improve performance). Also objects support has been added to this mode for an easier implementation and future enhancements.
- [x] Support for 'Uploads Queue' to limit the max number of assets that the Downloader worker will store in the temporary folder to 100 (this save disk space). In this way the Downloader worker will never put more than 100 assets pending to Upload in the local folder.
- [x] Support Migration between 2 different accounts on the same Cloud Photo Service. 
- [x] Support to use Local Folders as SOURCE/TARGET during AUTOMATED-MIGRATION MODE. Now the selected local folder works equal to other supported cloud services.
- [x] Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassTakeoutFolder, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
- [x] Added new Class ClassLocalFolder with the same methods as other supported Cloud Services Classes to manage Local Folders in the same way as a Photo Cloud Service.
- [x] ClassTakeoutFolder inherits all methods from ClassLocalFolder and includes specific methods to process Google Takeouts since at the end Google Takeout is a local folder structure.
- [x] Updated GPTH version to cop latest changes in Google Takeouts. 
- [x] Minor Bug Fixing.

- [ ] Tests Pending:
  - [ ] Deep Test on Immich Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Synology Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Google Takeout functions. (volunteers are welcomed)
  - [ ] Deep Test on --AUTOMATED-MIGRATION MODE. (volunteers are welcomed)

### Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/doc/screenshots/live_dashboard.jpg?raw=true)

## v4.0.0:
### Release Date: (estimated)
  - Alpha version.   : (No estimated date)
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

### TODO:
- [ ] Include Apple Support (initially just for downloading)
    - [ ] Create Class ClassApplePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] -adAlb, --apple-download-albums
    - [ ] -adAll, --apple-download-all
    - [ ] -auAlb, --apple-upload-albums
    - [ ] -auAll, --apple-upload-all
- [ ] Include native support for Google Photos through API  
  (See: https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef)
    - [ ] Create Class ClassGooglePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] -gdAlb, --google-download-albums
    - [ ] -gdAll, --google-download-all
    - [ ] -guAlb, --google-upload-albums
    - [ ] -guAll, --google-upload-all
- [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATED-MODE
- [ ] Add option to filter assets in all Immich Actions:
    - [ ] by Dates
    - [ ] by Country
    - [ ] by City
    - [ ] by Archive
    - [ ] by Person
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
