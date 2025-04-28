## ROADMAP:
Planed Roadmap for the following releases

---

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - Alpha version    : 2025-04-15
  - Beta version     : 2025-04-30
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### DONE:
  - #### New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --cient \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flags to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flags to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flags to execute this new feature:
      - _**'-mDupAlb, --merge-duplicates-albums'**_ 
    - [x] Automatic filters flags detection for all Remove/Rename/Merge Albums features for Synology/Immich Photos
      - [x] remove-all-assets
      - [x] remove-all-albums
      - [x] remove-albums
      - [x] remove-empty-albums
      - [x] remove-duplicates-albums
      - [x] rename-albums
      - [x] merge-albums
    - [x] Automatic filters flags detection in Dowload features for Synology/Immich Photos.
      - [x] download-all
      - [x] download-albums
    - [x] Request user confirmation before Rename/Remove/Merge massive Albums (show the affected Albums).
    - [x] Run Google Takeout Photos Processor Feature by default when running the tool with a valid folder as unique argument.
    - [x] Run Google Takeout Photos Processor Feature by default when running the tool without arguments, requesting the user to introduce Google Takeout folder. 

  - #### Enhancements:
    - [x] Improved Performance on Pull functions when no filtering options have been given.
    - [x] Improved performance when searching Google Takeout structure on huge local folder with many subfolders.
    - [x] Renamed 'Automated Mode' to 'Automatic Mode'.
    - [x] Improved performance retrieving assets when filters are detected. Use smart filtering detection to avoid person filterimg if not apply (this filter is very slow in Synology Photos)
    - [x] Avoid logout from Synology Photos when some mode uses more than one call to Synology Photos API (to avoid OTP token expiration)  
    - [x] Merged Features 'Remove All Albums' & 'Remove Albums by name' (You can remove ALL Albums using '.*' as pattern).
    - [x] Merged Synology/Immich features using a parameter and replacing Comments and Classes based on it. 
    - [x] Merged Synology/Immich HELP texts showed when running the different features.
    - [x] Renamed All flags starting with 's' (for synology) or 'i' (for immich) to remove the prefix, since now you can specify the client using the new flag _**'-client, --client'**_
    - [x] Renamed flag _**'-gtProc, --google-takeout-to-process'**_ to _**'-gTakeout, --google-takeout'**_ to activate the Feature 'Google Takeout Processing'.
    - [x] Renamed short name flag _**'-RemAlb'**_ to _**'-rAlb'**_ to activate the Feature 'Remove Albums'.
    - [x] Renamed short name flag _**'-RenAlb'**_ to _**'-renAlb'**_ to activate the Feature 'Rename Albums'.
    - [x] Renamed short name flag _**'-MergAlb'**_ to _**'-mDupAlb'**_ to activate the Feature 'Merge Duplicates Albums'.
    
  - #### Bug Fixing:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Minor bugs fixing.

- ### TODO:
  - [ ] Deep Tests for new Features.
  - [ ] Deep Test for upload-albums/upload-all features.
  - [ ] Bug Fixing.

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
