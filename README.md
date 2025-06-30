# 📈 Repo Statistics
[![Commit activity](https://img.shields.io/github/commit-activity/y/jaimetur/PhotoMigrator?label=Commit%20activity)](https://github.com/jaimetur/PhotoMigrator/graphs/contributors)
[![Resolved Github issues](https://img.shields.io/github/issues-closed/jaimetur/PhotoMigrator?label=Resolved%20issues)](https://github.com/jaimetur/PhotoMigrator/issues?q=is%3Aissue%20state%3Aclosed)
[![Open Github issues](https://img.shields.io/github/issues/jaimetur/PhotoMigrator?label=Open%20Issues)](https://github.com/jaimetur/PhotoMigrator/issues)
[![Total Github Releases downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/total?label=Total%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases)
[![Latest version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/latest/total?label=Latest%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases/latest)
[![Pre-release version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/v3.4.0/total?label=Pre%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)

# 📸 **PhotoMigrator**
<p align="center">
  <img src="https://github.com/jaimetur/PhotoMigrator/blob/main/assets/logos/logo.jpg?raw=true" alt="PhotoMigrator Logo" width="600" height="400" />
</p>

This tool has been designed to Interact and Manage different Photos Cloud services, and allow users to do an <span style="color:green">**Automatic Migration**</span> from one Photo Cloud service to other or from one account to a new account of the same Photo Cloud service. 


## 🖥️ Live Dashboard Preview
![Live Dashboard](https://github.com/jaimetur/PhotoMigrator/blob/main/assets/screenshots/live_dashboard.jpg?raw=true)  

## 🌟 Main Modules Included:
## 🚀 1. Automatic Migration   
The main use case is the **Automatic Migration Feature** to migrate all your photos and videos from one Photo cloud service to other, or between different accounts of the same service.  

[**(Automatic Migration Documentation)**](https://github.com/jaimetur/PhotoMigrator/blob/main/help/3-automatic-migration.md)


## 🛠️ 2. Google Photos Takeout Fixing 
Other important feature included in the tool is the Google Photos Takeout Fixing. 

This feature have been designed to automatically analyze your Google Photo Takeout, extract all the information from the sidecar JSON files (or guess some missing information using heuristics algorithms) and embeds all the extracted info into each asset file using EXIF tags.  

In this way your Media Library will be ready to be migrated to any other Cloud Photo services without losing any important info such as, Albums info, Original date, GPS location, Camera info, etc...

But this feature also helps you to organize and clean your Media Library removing duplicates, creating Year/Month folder structure, creating symbolic links for Albums assets, Auto renaming Albums to clean their names and include a prefix with the date of its assets, etc...

The whole process is done in an automatic way and is divided in different steps (some of them are optionals).

Below you can see the different steps of this feature:

#### 1. Pre Checks steps
  - Unpack your Takeout Zip files if needed. 
  - Create a backup of your original Takeout if needed. 
  - Calculate statistics of your original Takeout. 
#### 2. Pre Process steps
  - Merge Live picture with separate files (.HEIC and .MP4).
  - Fix  Truncations on sidecar JSON names and media files to complete truncated suffixes or extensions when the filename length is high. 
#### 3. Process steps
  - Process .json files to fix metadata (including creation date and time, GPS data, Albums info extraction, etc...) of all your assets.
  - Separate your assets per Albums (if belong to any album).
  - Create Symbolic Links for assets within any Album (to save disk space).
#### 4. Post Process steps
  - Synchronize MP4 files associated to Live pictures with the associated HEIC/JPG file. 
  - Organize your assets in a year/month structure for a better organization.
  - Separate all your Albums folders within 'Albums' subfolder from the original assets within 'ALL_PHOTOS' subfolder. 
  - Fix broken Symbolic Links. 
  - Detect and remove duplicates.
  - Auto rename Albums folders to homogenize all names based on content dates. 
  - Remove empty folders. 
  - Clean Final Media Library. 
  - Calculate statistics of your Final processed Media Library and compare it with your original Takeout statistics. 

[**(Google Takeout Fixing Documentation)**](https://github.com/jaimetur/PhotoMigrator/blob/main/help/4-google-takeout.md)

## 🖼️ 3. Synology Photos / Immich Photos / Apple Photos / Google Photos / NextCloud Memories Management
Apart from the 'Automatic Migration' and 'Google Takeout Fixing' features, you can use the tool also to manage different Photo Cloud Services. 
Currently, the Features Supported per each Photo Cloud Service are:

  | Feature                         | Synology                                                                                                                                  | Immich                                                                                                                                | Apple             | Google            | Nextcloud         |
  |---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|-------------------|-------------------|-------------------|
  | Upload Album(s) (from folder)   | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#upload-albums-from-local-folder-into-synology-photos) | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#upload-albums-from-local-folder-into-immich-photos) | Not supported yet | Not supported yet | Not supported yet |
  | Download Album(s) (into folder) | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#download-albums-from-synology-photos)                 | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#download-albums-from-immich-photos)                 | Not supported yet | Not supported yet | Not supported yet |
  | Upload ALL (from folder)        | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#upload-all-from-local-folder-into-synology-photos)    | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#upload-all-from-local-folder-into-immich-photos)    | Not supported yet | Not supported yet | Not supported yet |
  | Download ALL (into folder)      | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#download-all-from-synology-photos)                    | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#download-all-from-immich-photos)                    | Not supported yet | Not supported yet | Not supported yet |
  | Remove ALL Assets               | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#remove-all-assets-from-synology-photos)               | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-all-assets-from-immich-photos)               | Not supported yet | Not supported yet | Not supported yet |
  | Remove ALL Albums               | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#remove-all-albums-from-synology-photos)               | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-all-albums-from-immich-photos)               | Not supported yet | Not supported yet | Not supported yet |
  | Remove Albums by Name Pattern   | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#remove-albums-by-name-pattern-from-synology-photos)   | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-albums-by-name-pattern-from-immich-photos)   | Not supported yet | Not supported yet | Not supported yet |
  | Rename Albums by Name Pattern   | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#rename-albums-by-name-pattern-from-synology-photos)   | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#rename-albums-by-name-pattern-from-immich-photos)   | Not supported yet | Not supported yet | Not supported yet |
  | Remove Empty Albums             | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#remove-empty-albums-from-synology-photos)             | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-empty-albums-from-immich-photos)             | Not supported yet | Not supported yet | Not supported yet |
  | Remove Duplicates Albums        | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#remove-duplicates-albums-from-synology-photos)        | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-duplicates-albums-from-immich-photos)        | Not supported yet | Not supported yet | Not supported yet |
  | Merge Duplicates Albums         | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md#merge-duplicates-albums-from-synology-photos)         | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#merge-duplicates-albums-from-immich-photos)         | Not supported yet | Not supported yet | Not supported yet |
  | Remove Orphans Assets           | Not supported yet                                                                                                                         | [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md#remove-orphans-assets-from-immich-photos)           | Not supported yet | Not supported yet | Not supported yet |

[**(Synology Photos Documentation)**](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md)   

[**(Immich Photos Documentation)**](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md)

> [!NOTE] 
>- **Apple Photos**  
>  (not available yet but is on the [Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md) for next release)
>
>- **Google Photos**  
>  (not available yet but is on the [Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md) for next release)
>
>- **NextCloud Memories**  
>  (not available yet but is on the [Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md) for next release)


## 🧩 4. Other Standalone Features  
Finally, the Tool also contains Other Useful Standalone Features such as:
  - **Metadata fixing** of any Photo Library in your local drive (not necessarily needs to be a Google Takeout folder)
  - **Library Organization** features:
    - Manage Duplicates assets
    - Splitting of assets with and without associated albums
    - Folder Structure (customizable) for 'Albums' and 'No Albums' folders
  - **Symbolic Links Support** for Albums folders
    - Fix Symbolic Links Broken
  - **Homogenize Albums folder's name based on content**

[**(Other Standalone Features Documentation)**](https://github.com/jaimetur/PhotoMigrator/blob/main/help/7-other-features.md)


## 💾 Download
Download the tool either for Linux, MacOS or Windows (for both x64 and arm64 architectures) or Docker version (platform & architecture independent) as you prefer, directly from following links:
- [Latest Stable Release](https://github.com/jaimetur/PhotoMigrator/releases/latest)
- [Pre-Release](https://github.com/jaimetur/PhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)
- [All Releases](https://github.com/jaimetur/PhotoMigrator/releases)  

Or check the [Changelog](https://github.com/jaimetur/PhotoMigrator/blob/main/CHANGELOG.md) to choose any specific release. 

> [!NOTE]  
> The Tool is Multi-Platform and Multi-Architecture, and has been designed to be run directly within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), so feel free to download the version according to your system. 
> 
> You can also execute the Tool from a Docker container or from sources files for a better compatibility. In below sections you can find the execution instructions to run the Tool from the different methods.


## ⚙️ Configuration File
In order to connect to the different Photo Cloud Services, you must configure the connection settings using the Configuration file `Config.ini` provided with the Tool.  

You can see how to configure the Configuration File in this help section:
[Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md) 


## ⌨️ Command Line Interface
This Tool is based on commands given through the Command Line Interface (CLI), so it is important to know the syntax of that interface.  

You can check the whole list of features and arguments with the right syntax here:
[Command Line Interface (CLI)](https://github.com/jaimetur/PhotoMigrator/blob/main/help/1-command-line-interface.md)


## 📚 Arguments Description
Check all arguments descriptions and usage examples in the [Arguments Description](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description.md)  or in the [shorter version](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description-short.md).


## 📘 All Documentation Links
- [Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md)  
- [Command Line Interface (CLI)](https://github.com/jaimetur/PhotoMigrator/blob/main/help/1-command-line-interface.md)  
- [Arguments Description](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description.md)  
- [Automatic Migration Feature](https://github.com/jaimetur/PhotoMigrator/blob/main/help/3-automatic-migration.md)  
- [Google Takeout Management](https://github.com/jaimetur/PhotoMigrator/blob/main/help/4-google-takeout.md)  
- [Synology Photos Management](https://github.com/jaimetur/PhotoMigrator/blob/main/help/5-synology-photos.md)  
- [Immich Photos Management](https://github.com/jaimetur/PhotoMigrator/blob/main/help/6-immich-photos.md)  
- [Other Features](https://github.com/jaimetur/PhotoMigrator/blob/main/help/7-other-features.md)  
- [GPTH Tool Pipeline Description](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/00_GPTH_complete_pipeline.md)


## ▶️ Execution Methods
There are three different methods to execute this Tool:
- From [Compiled Binaries](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-binaries.md)
- From [Docker Container](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-docker.md)
- From [Source Repository](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-source.md)

The below tables show the pros and cons of each method together with a comparative rating of each one of them for you to decide which one fits best with your needed: 

- ### 🆚 Execution Methods Comparison

    | Execution Method | Difficulty | Pros                                                                                                                                               | Cons                                                                                                                                                                                                         |
    |------------------|:----------:|----------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | **Binaries**     |     🟢     | ✅ Only basic knowledge on command line commands needed                                                                                             | ❌ Platform and architecture dependent<br>❌ Need basic knowledge of running command line instructions<br>❌ Some anti-virus may detect the tool as suspicious in Windows systems                               |
    | **Docker**       |     ⭐      | ✅ Platform and architecture independent<br>✅ Easy configuration via `docker.config` <br>✅ Automatically pulls latest image if `RELEASE_TAG=latest` | ❌ Need intermediate knowledge of running command line instructions<br>❌ Need to install Docker (if not already installed)<br>❌ All paths given as arguments must be relative to the execution folder         |
    | **Source**       |     🔴     | ✅ Platform and architecture independent                                                                                                            | ❌ Need advance knowledge of running command line instructions<br>❌ Need to install Git and Python 3.8+ (if not already installed). <br>❌ Need to pull the source repository again to update to a new release |

  🟢 *Easiest way*    ⭐ *Recommended*    🔴 *More difficult*


- ### 🆚 Execution Methods Comparison Rating
  | Feature                                               | Binaries<br>(*easiest way*) | Docker<br>(*recommended*) | Source<br>(*more difficult*) |
  |-------------------------------------------------------|-----------------------------|---------------------------|------------------------------|
  | Platform and architecture independence                | ⭐☆☆☆☆                       | ⭐⭐⭐⭐⭐                     | ⭐⭐⭐⭐⭐                        |
  | Ease of updating to new release                       | ⭐⭐⭐☆☆                       | ⭐⭐⭐⭐⭐                     | ⭐☆☆☆☆                        |
  | Allow paths arguments point outside execution folder  | ⭐⭐⭐⭐⭐                       | ⭐☆☆☆☆                     | ⭐⭐⭐⭐⭐                        |
  | No Requires Technical knowledge (Command line syntax) | ⭐⭐⭐⭐⭐                       | ⭐⭐⭐☆☆                     | ⭐☆☆☆☆                        |
  | No Requires additional tools/software                 | ⭐⭐⭐⭐⭐                       | ⭐⭐⭐☆☆                     | ⭐☆☆☆☆                        |
  | No Risk of Antivirus alert (especially on Windows)    | ⭐⭐☆☆☆                       | ⭐⭐⭐⭐⭐                     | ⭐⭐⭐⭐⭐                        |
  | **Average Rating**                                    | ⭐⭐⭐⭐☆                       | ⭐⭐⭐⭐☆                     | ⭐⭐⭐☆☆                        |
  | **Average Score**                                     | 3.5                         | 3.7                       | 3.0                          |


---

## 📝 CHANGELOG
The Historical Change Log can be checked in the following link:
[Changelog](https://github.com/jaimetur/PhotoMigrator/blob/main/CHANGELOG.md)

---

## 📅 ROADMAP
The Planned Roadmap for futures releases can be checked in the following link:
[Planned Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md)

---

## 🛡️ CODE OF CONDUCT
By participating in this project, you agree to abide by our [Code of Conduct](https://github.com/jaimetur/PhotoMigrator/blob/main/CODE_OF_CONDUCT.md).

---

## 🎖️ Credits
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/Xentraxx/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)/[Wacheee](https://github.com/Wacheee) and v4.x.x by [Xentraxx](https://github.com/Xentraxx)


## 🙏 Donation / Sponsor
If you consider that this Tool has helped you, you can also consider donating me with a ☕  
I spent a lot of time developing this Tool for free, so donations will contribute to motivate me to continue working on this project 💖  

<a href="https://www.buymeacoffee.com/jaimetur">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="180" height="40">
</a>
<a href="https://github.com/sponsors/jaimetur">
  <img src="https://img.shields.io/github/sponsors/jaimetur?label=Sponsor&logo=GitHub" alt="Sponsor using GitHub" width="180" height="40">
</a>
<a href="https://www.paypal.me/jaimetur">
  <img src="https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal&style=for-the-badge" alt="Donate using Paypal" width="180" height="40">
</a>
