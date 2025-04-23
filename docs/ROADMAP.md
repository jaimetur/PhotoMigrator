# ROADMAP:

## v3.3.0  
### Release Date:
  - Alpha version    : 2025-05-16
  - Beta version     : 2025-05-23
  - Release Candidate: 2025-05-30
  - Official Release : 2025-05-30

### TODO:
- [x] Add Feature to Merge Albums with the same name and different assets. 
- [x] Add new flags _**'-sMergAlb, --synology-merge-duplicates-albums'**_ and _**'-iMergAlb, --immich-merge-duplicates-albums'**_ to activate this feature.
- [x] Improve Performance on Pull functions when no filtering options have been given
- [x] Improve performance when searching Google Takeout structure on huge local folder with many subfolders
- [x] Add Multi-Account support for all Synology Photos and Immich Photos Features (not only Automated Mode Feature as before)
- [x] Add Support for 3 accounts of each Cloud Photo Service (before it was only 2)
- [x] Support for 2FA in Synology Photos requesting the OTP Token if flag _**'-sOTP, --synology-OTP'**_ is detected. [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218)
- [x] Fix issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218)
- [ ] Rename Albums using regular expresions. 


## v4.0.0:
### Release Date: (estimated)
  - Alpha version    : (No estimated date)
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
- [ ] Update Documentation
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md
