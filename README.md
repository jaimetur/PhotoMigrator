# Repo Statistics
[![Commit activity](https://img.shields.io/github/commit-activity/y/jaimetur/CloudPhotoMigrator?label=Commit%20activity)](https://github.com/jaimetur/CloudPhotoMigrator/graphs/contributors)
[![Resolved Github issues](https://img.shields.io/github/issues-closed/jaimetur/CloudPhotoMigrator?label=Resolved%20issues)](https://github.com/jaimetur/CloudPhotoMigrator/issues?q=is%3Aissue%20state%3Aclosed)
[![Open Github issues](https://img.shields.io/github/issues/jaimetur/CloudPhotoMigrator?label=Open%20Issues)](https://github.com/jaimetur/CloudPhotoMigrator/issues)
[![Total Github Releases downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/total?label=Total%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases)
[![Latest version downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/latest/total?label=Latest%20version%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases/latest)
[![Pre-release version downloads](https://img.shields.io/github/downloads/jaimetur/CloudPhotoMigrator/v3.2.0-alpha/total?label=Pre%20version%20downloads)](https://github.com/jaimetur/CloudPhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)

# **CloudPhotoMigrator**
This tool has been designed to Interact and Manage different Photos Cloud services, and allow users to do an <span style="color:green">**Automated Migration** </span> from one Photo Cloud service to other or from one account to a new account of the same Photo Cloud service.  

As of today, the Supported Photo Cloud Services are:
- **Google Photos Takeout**
  - Unpack your Takeout Zip files.
  - Process .json files to fix metadata (including creation date and time) of all your assets.
  - Merge Live picture with separate files (.HEIC and .MP4).
  - Separate your assets per Albums (if belong to any album).
  - Organize your assets in a year/month structure for a better organization.
  - Create Symbolic Links for assets within any Album (to save disk space).
  - Detect and remove duplicates.

- **Synology Photos** - Features included:
  - Upload Album(s)
  - Upload ALL (from folder)
  - Download Album(s)
  - Download ALL (into folder)
  - Remove ALL Assets
  - Remove ALL Albums
  - Remove Empty Albums
  - Remove Duplicates Albums

- **Immich Photos** - Features included:
  - Upload Album(s)
  - Upload ALL (from folder)
  - Download Album(s)
  - Download ALL (into folder)
  - Remove ALL Assets
  - Remove ALL Albums
  - Remove Empty Albums
  - Remove Duplicates Albums
  - Remove Orphans Assets

- **Apple Photos**  
  (not available yet but is on the [ROADMAP.md](/docs/ROADMAP.md) for next release)

- **Google Photos**  
  (not available yet but is on the [ROADMAP.md](/docs/ROADMAP.md) for next release)


Apart from Manage the different Photo Cloud Services, the Tool also contains some other useful features such as:
- **Metadata fixing** of any Photo Library in your local drive (not necesarely needs to be a Google Takeout folder)
- **Library Organization** features:
  - Manage Duplicates assets
  - Splitting of assets with and without associated albums
  - Folder Structure (customizable) for 'Albums' and 'No Albums' folders
- **Symbolic Links Support** for Albums folders
  - Fix Symbolic Links Broken
- **Homogenize Albums folders name based on content**
- **Remove Empty Albums in Photo Cloud Services** 
- **Remove Duplicates Albums in Photo Cloud Services** 


## Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/assets/screenshots/live_dashboard.jpg?raw=true)  


## Download:
Download the tool either for Linux, MacOS or Windows (for both x64/amd64 or arm64 architectures) or Docker version (plattform & architecture independent) as you prefer, directly from following links:
- [Latest Stable Release](https://github.com/jaimetur/CloudPhotoMigrator/releases/latest)
- [Pre-Release](https://github.com/jaimetur/CloudPhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)
- [All Releases](https://github.com/jaimetur/CloudPhotoMigrator/releases)


## Configuration File:
Youn can see how to configure the Config.ini file in this help section:
[Configuration File](/help/0-configuration-file.md) 


## Command Line Syntax:
You can check the whole list of functions and arguments with the right syntax here:
[Command Line Syntax](/help/1-command-line-syntax.md)


## All Documentation Links:
- [Configuration File](/help/0-configuration-file.md)  
- [Command Line Syntax](/help/1-command-line-syntax.md)  
- [Automated Migration Feature](/help/2-automated-migration.md)  
- [Google Takeout Management](/help/3-google-takeout.md)  
- [Synology Photos Management](/help/4-synology-photos.md)  
- [Immich Photos Management](/help/5-immich-photos.md)  
- [Other Features](/help/6-other-features.md)  


> [!NOTE]  
> The Tool is Multi-Platform and Multi-Architecture, and has been designed to be run directly within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), so feel free to download the version according to your system. 
> 
> You can also execute the Tool from a Docker container or from sources files for a better compatibility. In below sections you can find the execution instructions to run the Tool from the different methods.


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


## Main Use Case: Automated Migration Feature
> [!NOTE]  
>## <span style="color:green">Automated Migration Feature</span>
>From version 3.0.0 onwards, the Tool supports a new Feature called '**Automated Migration**'. 
>
> Use the argument **'--source'** to select the \<SOURCE> and the argument **'--target'** to select \<TARGET> for the Automated Migration Process to Pull all your Assets (including Albums) from the \<SOURCE> Cloud Service and Push them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
> 
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> By default, the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Push workers.  
> The Pull worker and the different Push workes will be executed in parallel using an assets queue to guarantee that no more than 100 assets will be temporarily stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default, (if your terminal size has enough width and heigh) a Live Dashboard will show you all the details about the migration process, including most relevant log messages, and counter status. You can disable this Live Dashboard using the flag **'-dashboard=false or --dashboard=false'**.   
> 
> Additionally, this Automated Migration process can also be executed secuencially instead of in parallel, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
> 
> Also, take into account that in this case, the Live Dashboard will not be displayed, so you only will see the different messages log in the screen, but not the live counters during the migration.  
> and execute this feature, the Tool will automatically do the whole migration job from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.  

> [!WARNING]  
> If you use a local folder <INPUT_FOLDER> as source client, all your Albums should be placed into a subfolder called *'Albums'* within <INPUT_FOLDER>, creating one Album subfolder per Album, otherwise the tool will no create any Album in the target client.  
>
> Example:  
> <INPUT_FOLDER>/Album1  
> <INPUT_FOLDER>/Album2  

> [!IMPORTANT]  
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Services.  


# ROADMAP:

## v3.2.0  
### Release Date: (estimated)
  - Alpha version    : 2025-04-07
  - Beta version     : 2025-04-14
  - Release Candidate: 2025-04-25
  - Official Release : 2025-04-30

### TODO:
- [ ] Add option to filter assets in all Immich/Synology/LocalFolder Actions:
    - [x] by Dates
    - [x] by Country
    - [x] by City
    - [ ] by People
    - [ ] by Type
- [ ] Test Filters in other Synology/Immich Features
- [x] Include Live Dashboard in secuential Automated Migration
- [x] Test secuential Automated Migration
- [x] Minor bugs fixing
- [ ] Update Documentation
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md


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

