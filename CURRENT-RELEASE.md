# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] ~~Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.~~     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

# Release Notes:

## **Release**: v3.3.0  

- ### **Release Date**: 2025-05-30
  - ~~Alpha version    : 2025-04-15~~
  - ~~Beta version     : 2025-04-30~~
  - Release Candidate: 2025-05-15
  - Official Release : 2025-05-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [x] New Tool name '**PhotoMigrator**' (former 'CloudPhotoMigrator').  
        - This change implies that docker distribution package needs to be downloaded again because the launching scripts and the dockerhub images repository have been renamed.

  - #### 🌟 New Features:
    - [x] Added Multi-Account support for all Synology Photos and Immich Photos Features (not only Automatic Mode Feature as before).
    - [x] Added Support for 3 accounts of each Cloud Photo Service (before it was only 2).
    - [x] Merged Synology/Immich arguments (now you can specify the client using a new flag _**'-client, --client \<CLIENT_NAME>'**_)
    - [x] Added new flag _**'-client, --cient \<CLIENT_NAME>'**_ to set the Cloud Photo client to use.
    - [x] Added new flag _**'-id, --account-id \<ID>'**_ to specify which account to use for Synology Photos and Immich Photos from Config.ini.
    - [x] Added new flag _**'-move, --move-assets'**_ to move assets (instead of copy) from \<SOURCE> client to \<TARGET> client during Automatic Migration process.
    - [x] Added support for 2FA in Synology Photos requesting the OTP Token if flag _**'-OTP, --one-time-password'**_ is detected. [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
      - New flag _**'-OTP, --one-time-password'**_ to allow login into Synology Photos accounts with 2FA activated.
    - [x] Added new Feature to **Remove Albums by Name Pattern** from Synology Photos and Immich Photos to remove those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-rAlb, --remove-albums \<ALBUM_NAME_PATTERN>'**_
    - [x] Added new Feature to **Rename Albums by Name Pattern** from Synology Photos and Immich Photos to rename those albums whose name matches with a provided pattern (using regular expresions). Added following new flag to execute this new features:
      - _**'-renAlb, --rename-albums \<ALBUM_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>'**_
    - [x] Added new Feature to **Merge Albums** with the same name and different assets. Added following new flag to execute this new feature:
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

  - #### 🚀 Enhancements:
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
    - [x] ~~Updated GPTH to version 4.0.0 (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts.~~     

  - #### 🐛 Bug fixes:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/PhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly).
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums".
    - [x] Fixed a bug when any input folder ends with '\' or '/' but is enclosed between double quotes (").
    - [x] Fixed a bug replacing argument provided with flag _**'-dAlb, --download-albums \<ALBUMS_NAME>'**_ in the HELP text screen.
    - [x] Minor bugs fixing.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    - [x] Renamed 'argument' by 'flag' in all help text descriptions.
    - [x] Added tool logo and emojis to documentation files.

---

## 💾 Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_macos_arm64.zip)  

**Windows:**  
  - [Download AMD 64 bits version](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_windows_amd64.zip)  

**Docker Launcher:**  
  - [Download Docker Launcher](https://github.com/jaimetur/PhotoMigrator/releases/download/v3.3.0-RC/PhotoMigrator_v3.3.0-RC_docker.zip)  

