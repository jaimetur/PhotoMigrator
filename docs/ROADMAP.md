## ROADMAP:
Planed Roadmap for the following releases

---

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - Alpha version    : 2025-05-16
  - Beta version     : 2025-05-23
  - Release Candidate: 2025-05-30
  - Official Release : 2025-05-30

- ### DONE:
  - #### New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-sOTP, --synology-OTP'**_ is detected. [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218).
      - New flag _**'-sOTP, --synology-OTP'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flags to execute this new features:
      - _**'-sRemAlb, --synology-remove-albums \<ALBUM_NAME_PATTERN>'**_
      - _**'-iRemAlb, --immich-remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flags to execute this new features:
      - _**'-sRenAlb, --synology-rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
      - _**'-iRenAlb, --immich-rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flags to execute this new feature:
      - _**'-sMergAlb, --synology-merge-duplicates-albums'**_ 
      - _**'-iMergAlb, --immich-merge-duplicates-albums'**_.
  
  - #### Enhancements:
    - [x] Improved Performance on Pull functions when no filtering options have been given.
    - [x] Improved performance when searching Google Takeout structure on huge local folder with many subfolders.
    - [x] Renamed Automated Mode to Automatic Mode.
  
  - #### Bug Fixing:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly)
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums"
    - [x] Minor bugs fixing

- ### TODO:
  - [ ] Allow filter by date in Remove/Rename/Merge Albums features for Synology/Immich Photos
  - [ ] Automatic filters flags detection for all Remove/Rename/Merge Albums features for Synology/Immich Photos
    - [ ] remove-all-assets
    - [ ] remove-all-albums
    - [ ] remove-albums
    - [ ] remove-empty-albums
    - [ ] remove-duplicates-albums
    - [ ] rename-albums
    - [ ] merge-albums
  - [ ] Automatic filters flags detection for Upload/Dowload features for Synology/Immich Photos
    - [ ] upload-all
    - [ ] upload-albums
    - [ ] download-all
    - [ ] download-albums
  - [ ] Improve performance retrieving assets when filters are detected. Use smart filtering detection to avoid person filterimg if not apply (this filter is very slow in Synology Photos)
  - [ ] Deep Tests for new Features
  - [ ] Deep Test for upload-albums/upload-all features
  - [ ] Bug Fixing

---

## **Release**: v4.0.0 

- ### Release Date: (estimated)
  - Alpha version    : (No estimated date)
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

- ### TODO:
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
  - [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATIC-MODE
  - [ ] Update Documentation
  - [ ] Update README.md
  - [ ] Update RELEASES-NOTES.md
