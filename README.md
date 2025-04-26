# Repo Statistics
[![Commit activity](https://img.shields.io/github/commit-activity/y/jaimetur/CloudPhotoMigrator?label=Commit%20activity)](https://github.com/jaimetur/CloudPhotoMigrator/graphs/contributors)
[![Resolved Github issues](https://img.shields.io/github/issues-closed/jaimetur/CloudPhotoMigrator?label=Resolved%20issues)](https://github.com/jaimetur/CloudPhotoMigrator/issues?q=is%3Aissue%20state%3Aclosed)
[![Open Github issues](https://img.shields.io/github/issues/jaimetur/CloudPhotoMigrator?label=Open%20Issues)](https://github.com/jaimetur/CloudPhotoMigrator/issues)
[![Total Github Releases downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/total?label=Total%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases)
[![Latest version downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/latest/total?label=Latest%20version%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases/latest)
[![Pre-release version downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/v3.3.0-alpha/total?label=Pre%20version%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)

# **CloudPhotoMigrator**
This tool has been designed to Interact and Manage different Photos Cloud services, and allow users to do an <span style="color:green">[**Automatic Migration**](/help/2-automatic-migration.md) </span> from one Photo Cloud service to other or from one account to a new account of the same Photo Cloud service.  

Currently, the Supported Photo Cloud Services and included Features are:
- [**Google Photos Takeout Management**](/help/3-google-takeout.md)
  - Unpack your Takeout Zip files.
  - Process .json files to fix metadata (including creation date and time) of all your assets.
  - Merge Live picture with separate files (.HEIC and .MP4).
  - Separate your assets per Albums (if belong to any album).
  - Organize your assets in a year/month structure for a better organization.
  - Create Symbolic Links for assets within any Album (to save disk space).
  - Detect and remove duplicates.

- [**Synology Photos Management**](/help/4-synology-photos.md) - Features included:
  - Upload Album(s) (from folder) [(doc)](/help/4-synology-photos.md#upload-albums-from-local-folder-into-synology-photos)
  - Download Album(s) (into folder) [(doc)](/help/4-synology-photos.md#download-albums-from-synology-photos)
  - Upload ALL (from folder) [(doc)](/help/4-synology-photos.md#upload-all-from-local-folder-into-synology-photos)
  - Download ALL (into folder) [(doc)](/help/4-synology-photos.md#download-all-from-synology-photos)
  - Remove ALL Assets [(doc)](/help/4-synology-photos.md#remove-all-assets-from-synology-photos)
  - Remove ALL Albums [(doc)](/help/4-synology-photos.md#remove-all-albums-from-synology-photos)
  - Remove Albums by Name Pattern [(doc)](/help/4-synology-photos.md#remove-albums-by-name-pattern-from-synology-photos)
  - Rename Albums by Name Pattern [(doc)](/help/4-synology-photos.md#rename-albums-by-name-pattern-from-synology-photos)
  - Remove Empty Albums [(doc)](/help/4-synology-photos.md#remove-empty-albums-from-synology-photos)
  - Remove Duplicates Albums [(doc)](/help/4-synology-photos.md#remove-duplicates-albums-from-synology-photos)
  - Merge Duplicates Albums [(doc)](/help/4-synology-photos.md#merge-duplicates-albums-from-synology-photos)

- [**Immich Photos Management**](/help/5-immich-photos.md) - Features included:
  - Upload Album(s) (from folder) [(doc)](/help/5-immich-photos.md#upload-albums-from-local-folder-into-immich-photos)
  - Download Album(s) (into folder) [(doc)](/help/5-immich-photos.md#download-albums-from-immich-photos)
  - Upload ALL (from folder) [(doc)](/help/5-immich-photos.md#upload-all-from-local-folder-into-immich-photos)
  - Download ALL (into folder) [(doc)](/help/5-immich-photos.md#download-all-from-immich-photos)
  - Remove ALL Assets [(doc)](/help/5-immich-photos.md#remove-all-assets-from-immich-photos)
  - Remove ALL Albums [(doc)](/help/5-immich-photos.md#remove-all-albums-from-immich-photos)
  - Remove Albums by Name Pattern [(doc)](/help/5-immich-photos.md#remove-albums-by-name-pattern-from-immich-photos)
  - Rename Albums by Name Pattern [(doc)](/help/5-immich-photos.md#rename-albums-by-name-pattern-from-immich-photos)
  - Remove Empty Albums [(doc)](/help/5-immich-photos.md#remove-empty-albums-from-immich-photos)
  - Remove Duplicates Albums [(doc)](/help/5-immich-photos.md#remove-duplicates-albums-from-immich-photos)
  - Merge Duplicates Albums [(doc)](/help/5-immich-photos.md#merge-duplicates-albums-from-immich-photos)
  - Remove Orphans Assets [(doc)](/help/5-immich-photos.md#remove-orphans-assets-from-immich-photos)

- **Apple Photos Management**  
  (not available yet but is on the [Roadmap](/docs/ROADMAP.md) for next release)

- **Google Photos Management**  
  (not available yet but is on the [Roadmap](/docs/ROADMAP.md) for next release)

- [**Other Useful Features**](/help/6-other-features.md)  
Apart from Manage the different Photo Cloud Services, the Tool also contains Other Useful Features such as:
  - **Metadata fixing** of any Photo Library in your local drive (not necesarely needs to be a Google Takeout folder)
  - **Library Organization** features:
    - Manage Duplicates assets
    - Splitting of assets with and without associated albums
    - Folder Structure (customizable) for 'Albums' and 'No Albums' folders
  - **Symbolic Links Support** for Albums folders
    - Fix Symbolic Links Broken
  - **Homogenize Albums folders name based on content**

## Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/assets/screenshots/live_dashboard.jpg?raw=true)  


## Tool Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:
- [Latest Stable Release](https://github.com/jaimetur/CloudPhotoMigrator/releases/latest)
- [Pre-Release](https://github.com/jaimetur/CloudPhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)
- [All Releases](https://github.com/jaimetur/CloudPhotoMigrator/releases)  

Or check the [Historical Releases Notes](/docs/RELEASES-NOTES.md) to choose any specific release. 

> [!NOTE]  
> The Tool is Multi-Platform and Multi-Architecture, and has been designed to be run directly within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), so feel free to download the version according to your system. 
> 
> You can also execute the Tool from a Docker container or from sources files for a better compatibility. In below sections you can find the execution instructions to run the Tool from the different methods.


## Configuration File:
In order to connect to the different Photo Cloud Services, you must configure the conection settings using the Configuration file (Config.ini) provided with the Tool.  

Youn can see how to configure the Configuration File in this help section:
[Configuration File](/help/0-configuration-file.md) 


## Command Line Interface (CLI):
This Tool is based in commands given through the Command Line Interface (CLI), so it is important to know the syntax of that interface.  

You can check the whole list of all features and arguments with the right syntax here:
[Command Line Interface (CLI)](/help/1-command-line-interface.md)


## All Documentation Links:
- [Configuration File](/help/0-configuration-file.md)  
- [Command Line Interface (CLI)](/help/1-command-line-interface.md)  
- [Automatic Migration Feature](/help/2-automatic-migration.md)  
- [Google Takeout Management](/help/3-google-takeout.md)  
- [Synology Photos Management](/help/4-synology-photos.md)  
- [Immich Photos Management](/help/5-immich-photos.md)  
- [Other Features](/help/6-other-features.md)  


## Execution Methods:
There are three different methods to execute this Tool:
- From **Compiled Binaries**
- From **Docker Container**
- From **Source Repository**

The below tables show the pros and cons of each method together with a comparative rating of each one of them for you to decide wich one fits best with your needed: 

- ### Execution Methods Comparison
  | Execution Method                                                        | Instructions Link                                               | Difficulty          | Pros                                                                                                                                                                                 | Cons                                                                                                                                                                                                              |
  |-------------------------------------------------------------------------|-----------------------------------------------------------------|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
  | **[Compiled <br>Binaries](/help/execution/execution-from-binaries.md)** | **[Instructions](/help/execution/execution-from-binaries.md)**  | 🟢 *Easiest way*    | ✅ Only basic knowledge on command line commands needed.                                                                                                                             | ❌ Platform and architecture dependent.<br>❌ Need basic knowledge of running command line instructions.<br>❌ Some anti-virus may detect the tool as suspicious in Windows systems.                             |
  | **[Docker <br>Container](/help/execution/execution-from-docker.md)**    | **[Instructions](/help/execution/execution-from-docker.md)**    | ⭐ *Recommended*    | ✅ Platform and architecture independent.<br>✅ Easy configuration via `docker.config` file (RELEASE_TAG, TIMEZONE).<br>✅ Automatically pulls latest image if `RELEASE_TAG=latest`. | ❌ Need intermediate knowledge of running command line instructions.<br>❌ Need to install Docker (if not already installed).<br>❌ All paths given as arguments must be relative to the execution folder.       |
  | **[Source <br>Repository](/help/execution/execution-from-source.md)**   | **[Instructions](/help/execution/execution-from-source.md)**    | 🔴 *More difficult* | ✅ Platform and architecture independent.                                                                                                                                            | ❌ Need advance knowledge of running command line instructions.<br>❌ Need to install Git and Python 3.8+ (if not already installed). <br>❌ Need to pull the source repository again to update to a new release.|

- ### Execution Methods Comparison Rating
  | Feature                                               | [Compiled <br>Binaries](/help/execution/execution-from-binaries.md)<br>*easiest way* | [Docker <br>Container](/help/execution/execution-from-docker.md)<br>*recommended* | [Source <br>Repository](/help/execution/execution-from-source.md)<br>*more difficult* |
  |-------------------------------------------------------|--------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
  | Platform and architecture independence                | ⭐☆☆☆☆                                                                              | ⭐⭐⭐⭐⭐                                                                       | ⭐⭐⭐⭐⭐                                                                           |
  | Ease of updating to new release                       | ⭐⭐⭐☆☆                                                                            | ⭐⭐⭐⭐⭐                                                                       | ⭐☆☆☆☆                                                                               |
  | Allow paths arguments point outside execution folder  | ⭐⭐⭐⭐⭐                                                                          | ⭐☆☆☆☆                                                                           | ⭐⭐⭐⭐⭐                                                                           |
  | No Requires Technical knowledge (Command line syntax) | ⭐⭐⭐⭐⭐                                                                          | ⭐⭐⭐☆☆                                                                         | ⭐☆☆☆☆                                                                               |
  | No Requires additional tools/software                 | ⭐⭐⭐⭐⭐                                                                          | ⭐⭐⭐☆☆                                                                         | ⭐☆☆☆☆                                                                               |
  | No Risk of Antivirus alert (especially on Windows)    | ⭐⭐☆☆                                                                              | ⭐⭐⭐⭐⭐                                                                       | ⭐⭐⭐⭐⭐                                                                            |
  | **Average Rating**                                    | ⭐⭐⭐⭐☆ (3.5)                                                                     | ⭐⭐⭐⭐☆ (3.7)                                                                  | ⭐⭐⭐☆☆ (3.0)                                                                       |


## Main Use Case: Automatic Migration Feature

> [!NOTE]  
>## <span style="color:green">Automatic Migration Feature</span>
>From version 3.0.0 onwards, the Tool supports a new Feature called '**Automatic Migration**'. 
>
> Use the argument **'--source'** to select the \<SOURCE> client and the argument **'--target'** to select \<TARGET> client for the Automatic Migration Process to Pull all your Assets (including Albums) from the \<SOURCE> Cloud Service and Push them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
>
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> It is also possible to specify the account-id using the flag _**'-id, --account-id \<ID>'**_ (ie: --source=synology --account-id=2 means that Synology Photos account 2 will be used as \<SOURCE> client.)  
> 
>> ⚠️ **IMPORTANT**:  
>> Take into account that the flag _**'-id, --account-id \<ID>'**_ applies for all the Photo Cloud Services (Synology Photos and Immich Photos, so if you specify the client ID using this flag and you have more than one Photo Cloud Service, all of them will use the same client ID.)
> 
> By default, the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Push workers). The Pull worker and the different Push workes will be executed in parallel using an assets queue to guarantee that no more than 100 assets will be temporarily stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default, (if your terminal size has enough width and heigh) a Live Dashboard will show you all the details about the migration process, including most relevant log messages, and counter status. You can disable this Live Dashboard using the flag **'-dashboard=false or --dashboard=false'**.   
> 
> Additionally, this Automatic Migration process can also be executed sequentially instead of in parallel, using flag **--parallel=false**, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
>
> Finally, you can apply filters to filter assets to pull from \<SOURCE> client. The available filters are: 
>    - **by Type:**
>      - flag: -type, --filter-by-type
>        - Valid values are [image, video, all]
>    - **by Dates:**
>      - flags:
>        - -from, --filter-from-date
>        - -to, --filter-to-date
>      - Valid values are in one of those formats: 
>        - dd/mm/yyyy
>        - dd-mm-yyyy
>        - yyyy/mm/dd
>        - yyyy-mm-dd
>        - mm/yyyy
>        - mm-yyyy
>        - yyyy/mm
>        - yyyy-mm
>        - yyyy 
>    - **by Country:**
>      - flag: -country, --filter-by-country
>        - Valid values are any existing country in the \<SOURCE> client.
>    - **by City:**
>      - flag: -city, --filter-by-city
>        - Valid values are any existing city in the \<SOURCE> client.
>    - **by Person:**
>      - flag: -person, --filter-by-person
>        - Valid values are any existing person in the \<SOURCE> client.

> [!WARNING]  
> If you use a local folder <INPUT_FOLDER> as source client, all your Albums should be placed into a subfolder called *'Albums'* within <INPUT_FOLDER>, creating one Album subfolder per Album, otherwise the tool will no create any Album in the target client.  
>
> Example:  
> <INPUT_FOLDER>/Album1  
> <INPUT_FOLDER>/Album2  

> [!IMPORTANT]  
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  

---

## RELEASES-NOTES:
The Historical Releases Notes can be checked in the following link:
[RELEASES-NOTES.md](/docs/RELEASES-NOTES.md)

---

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
    - [x] Automatic filters flags detection for all Remove/Rename/Merge Albums features for Synology/Immich Photos
      - [x] remove-all-assets
      - [x] remove-all-albums
      - [x] remove-albums
      - [x] remove-empty-albums
      - [x] remove-duplicates-albums
      - [x] rename-albums
      - [x] merge-albums
    - [x] Request user confirmation before Rename/Remove/Merge massive Albums (show the affected Albums).

  - #### Enhancements:
    - [x] Improved Performance on Pull functions when no filtering options have been given.
    - [x] Improved performance when searching Google Takeout structure on huge local folder with many subfolders.
    - [x] Renamed 'Automated Mode' to 'Automatic Mode'.
    - [x] Improve performance retrieving assets when filters are detected. Use smart filtering detection to avoid person filterimg if not apply (this filter is very slow in Synology Photos)
    - [x] Avoid logout from Synology Photos when some mode uses more than one call to Synology Photos API (to avoid OTP token expiration)  
    - [x] Merge Remove All Albums & Remove Albums by name features (add the posibility to delete all using .* as pattern).
    - [x] Merge Synology/Immich execution modes using a parameter and replacing Comments and Classes based on it. 
  
  - #### Bug Fixing:
    - [x] Fixed issue when username/password cotains the special char (#) reserved for in-line comments in the configuration file (Config.ini). [#218](https://github.com/jaimetur/CloudPhotoMigrator/issues/218).
    - [x] Fixed a bug with feature **Remove All Albums** from Synology Photos and Immich Photos when the flag _**'--remove-albums-assets'**_ was selected (the assetes were not removed properly)
    - [x] Fixed a bug with feature **Synology Upload Album(s)** when the folder to upload is not named "Albums"
    - [x] Minor bugs fixing

- ### TODO:

  - [ ] Automatic filters flags detection for Upload/Dowload features for Synology/Immich Photos.
    - [x] upload-all
    - [x] upload-albums
    - [ ] download-all
    - [ ] download-albums
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

## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/TheLastGimbus/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)


## Donation / Sponsor: 
If you consideer that this Tool has helped you, you can also consider donating me with a ☕  
I spent a lot of time developping this Tool for free, so donations will contribute to motivate me to continue working on this project 💖  

<a href="https://www.buymeacoffee.com/jaimetur">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="180" height="40">
</a>
<a href="https://github.com/sponsors/jaimetur">
  <img src="https://img.shields.io/github/sponsors/jaimetur?label=Sponsor&logo=GitHub" alt="Sponsor using GitHub" width="180" height="40">
</a>
<a href="https://www.paypal.me/jaimetur">
  <img src="https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal&style=for-the-badge" alt="Donate using Paypal" width="180" height="40">
</a>

