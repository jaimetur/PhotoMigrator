<p align="center">
  <img src="/assets/logos/logo_17_1024x1024.png?raw=true" alt="PhotoMigrator Logo" width="600" height="480" />
</p>


# 📈 Repo Statistics
[![Commit activity](https://img.shields.io/github/commit-activity/y/jaimetur/PhotoMigrator?label=Commit%20activity)](https://github.com/jaimetur/PhotoMigrator/graphs/contributors)
[![Resolved Github issues](https://img.shields.io/github/issues-closed/jaimetur/PhotoMigrator?label=Resolved%20issues)](https://github.com/jaimetur/PhotoMigrator/issues?q=is%3Aissue%20state%3Aclosed)
[![Open Github issues](https://img.shields.io/github/issues/jaimetur/PhotoMigrator?label=Open%20Issues)](https://github.com/jaimetur/PhotoMigrator/issues)
[![Total Github Releases downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/total?label=Total%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases)
[![Latest version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/latest/total?label=Latest%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases/latest)
[![Pre-release version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/v3.8.0/total?label=Pre%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)


# 📸 **PhotoMigrator**
This tool has been designed to Interact and Manage different Photo Services such as Google Photos, Synology Photos, Immich Photos, Apple Photos & NextCloud, and allow users to do an <span style="color:green">**Automatic Migration**</span> from one Photo Cloud service to other or from one account to a new account of the same Photo Cloud service.  

The Tool supports multiple accounts for the same service, so you can migrate your assets between different accounts of the same service.

<p align="center"> 
  <br/>
  <a href="https://discord.gg/wTJ62qh5UC" target="_blank">
    <img src="https://img.shields.io/discord/1391921771770286110.svg?label=Discord&logo=Discord&style=for-the-badge&logoColor=ffffff&labelColor=5865F2" alt="Discord"/>
  </a>
  <br/>
  <br/>
</p>

# 📸 Tool Screenshots

## 🌐 Web Interface
### Automatic Migration Feature:
![Automatic Migration](/assets/screenshots/web-interface-automatic-migration.png?raw=true)  

### Google Photos Feature:
![Google Photos](/assets/screenshots/web-interface-google-photos.png?raw=true)  

### Synology Photos Feature:
![Synology Photos](/assets/screenshots/web-interface-synology-photos.png?raw=true)  

### Immich Photos Feature:
![Immich Photos](/assets/screenshots/web-interface-immich-photos.png?raw=true)  

### Other Features:
![Other Features](/assets/screenshots/web-interface-other-features.png?raw=true)  

### General Arguments:
![General Arguments](/assets/screenshots/web-interface-general-arguments.png?raw=true)  

### Configuration File:
![Configuration File](/assets/screenshots/web-interface-configuration-file.png?raw=true)  

### Theme Selector:
![Theme Selector](/assets/screenshots/web-interface-theme-selector.png?raw=true)  

## 🖥️ Automatic Migration on Terminal
![Live Dashboard](/assets/screenshots/live_dashboard.jpg?raw=true)  

# 🌟 Main Modules:
## 🚀 1. Automatic Migration   
The main use case is the **Automatic Migration Feature** to migrate all your photos and videos from one Photo cloud service to other, or between different accounts of the same service.  

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Automatic Migration Documentation)**](/help/3-automatic-migration.md)


## 🛠️ 2. Google Takeout Fixing 
Other important feature included in the tool is the Google Takeout Fixing. 

This feature has been designed to automatically analyze your Google Photos Takeout, extract all the information from the sidecar JSON files (or guess some missing information using heuristics algorithms) and embeds all the extracted info into each asset file using EXIF tags.  

In this way your Media Library will be ready to be migrated to any other Cloud Photo services without losing any important info such as, Albums info, Original date, GPS location, Camera info, etc...

But this feature also helps you to organize and clean your Media Library removing duplicates, creating Year/Month folder structure, creating symbolic links for Albums assets, Auto renaming Albums to clean their names and include a prefix with the date of its assets, Process Motion/Live Pictures, etc...

The whole process is done in an automatic way and is divided in different steps (some of them are optionals).

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Google Takeout Fixing Documentation)**](/help/4-google-takeout.md)

## 🖼️ 3. Synology Photos / Immich Photos / Apple Photos / Google Photos / NextCloud Photos Management
Apart from the 'Automatic Migration' and 'Google Takeout Fixing' features, you can use the tool also to manage different Photo Cloud Services. 
Currently, the Features Supported per each Photo Cloud Service are:

  | Feature                         | Synology                                                                                                                                  | Immich                                                                                                                                | Apple             | Google            | Nextcloud         |
  |---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|-------------------|-------------------|-------------------|
  | Upload Album(s) (from folder)   | [doc](/help/5-synology-photos.md#upload-albums-from-local-folder-into-synology-photos) | [doc](/help/6-immich-photos.md#upload-albums-from-local-folder-into-immich-photos) | Not supported yet | Not supported yet | Not supported yet |
  | Download Album(s) (into folder) | [doc](/help/5-synology-photos.md#download-albums-from-synology-photos)                 | [doc](/help/6-immich-photos.md#download-albums-from-immich-photos)                 | Not supported yet | Not supported yet | Not supported yet |
  | Upload ALL (from folder)        | [doc](/help/5-synology-photos.md#upload-all-from-local-folder-into-synology-photos)    | [doc](/help/6-immich-photos.md#upload-all-from-local-folder-into-immich-photos)    | Not supported yet | Not supported yet | Not supported yet |
  | Download ALL (into folder)      | [doc](/help/5-synology-photos.md#download-all-from-synology-photos)                    | [doc](/help/6-immich-photos.md#download-all-from-immich-photos)                    | Not supported yet | Not supported yet | Not supported yet |
  | Remove ALL Assets               | [doc](/help/5-synology-photos.md#remove-all-assets-from-synology-photos)               | [doc](/help/6-immich-photos.md#remove-all-assets-from-immich-photos)               | Not supported yet | Not supported yet | Not supported yet |
  | Remove ALL Albums               | [doc](/help/5-synology-photos.md#remove-all-albums-from-synology-photos)               | [doc](/help/6-immich-photos.md#remove-all-albums-from-immich-photos)               | Not supported yet | Not supported yet | Not supported yet |
  | Remove Albums by Name Pattern   | [doc](/help/5-synology-photos.md#remove-albums-by-name-pattern-from-synology-photos)   | [doc](/help/6-immich-photos.md#remove-albums-by-name-pattern-from-immich-photos)   | Not supported yet | Not supported yet | Not supported yet |
  | Rename Albums by Name Pattern   | [doc](/help/5-synology-photos.md#rename-albums-by-name-pattern-from-synology-photos)   | [doc](/help/6-immich-photos.md#rename-albums-by-name-pattern-from-immich-photos)   | Not supported yet | Not supported yet | Not supported yet |
  | Remove Empty Albums             | [doc](/help/5-synology-photos.md#remove-empty-albums-from-synology-photos)             | [doc](/help/6-immich-photos.md#remove-empty-albums-from-immich-photos)             | Not supported yet | Not supported yet | Not supported yet |
  | Remove Duplicates Albums        | [doc](/help/5-synology-photos.md#remove-duplicates-albums-from-synology-photos)        | [doc](/help/6-immich-photos.md#remove-duplicates-albums-from-immich-photos)        | Not supported yet | Not supported yet | Not supported yet |
  | Merge Duplicates Albums         | [doc](/help/5-synology-photos.md#merge-duplicates-albums-from-synology-photos)         | [doc](/help/6-immich-photos.md#merge-duplicates-albums-from-immich-photos)         | Not supported yet | Not supported yet | Not supported yet |
  | Remove Orphans Assets           | Not supported yet                                                                                                                         | [doc](/help/6-immich-photos.md#remove-orphans-assets-from-immich-photos)           | Not supported yet | Not supported yet | Not supported yet |

> [!NOTE]
> For more info you can check the feature documentation in below links:
>
>- [**(Synology Photos Documentation)**](/help/5-synology-photos.md)
> 
>- [**(Immich Photos Documentation)**](/help/6-immich-photos.md)

> [!IMPORTANT]  
>- **Apple Photos**  is not available yet but is on the [Roadmap](/ROADMAP.md) for next release.
>
>- **Google Photos** is not available yet but is on the [Roadmap](/ROADMAP.md) for next release.
>
>- **NextCloud Photos**  is not available yet but is on the [Roadmap](/ROADMAP.md) for next release.


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

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Other Standalone Features Documentation)**](/help/7-other-features.md)


## 💾 Download
Download the tool either for Linux, MacOS or Windows (for both x64 and arm64 architectures) or Docker version (platform & architecture independent) as you prefer, directly from following links:

- [Latest Stable Release](https://github.com/jaimetur/PhotoMigrator/releases/latest)
- [Pre-Release](https://github.com/jaimetur/PhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)
- [All Releases](https://github.com/jaimetur/PhotoMigrator/releases)  

Or check the [Changelog](/CHANGELOG.md) to choose any specific release. 

> [!NOTE]  
> The Tool is Multi-Platform and Multi-Architecture, and has been designed to be run directly from Windows systems, MacOs or within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), so feel free to download the version according to your system. 
> 
> You can also execute the Tool from a Docker container or from sources files for a better compatibility. In below sections you can find the execution instructions to run the Tool from the different methods.


## ⚙️ Configuration File
In order to connect to the different Photo Cloud Services, you must configure the connection settings using the Configuration file `Config.ini` provided with the Tool.  

You can see how to configure the Configuration File in this help section:
[Configuration File](/help/0-configuration-file.md) 


## ⌨️ Command Line Interface
This Tool is based on commands given through the Command Line Interface (CLI), so it is important to know the syntax of that interface.  

You can check the whole list of features and arguments with the right syntax here:
[Command Line Interface (CLI)](/help/1-command-line-interface.md)


## 🌐 Web Interface (New)
PhotoMigrator now includes a Web Interface that executes the same CLI arguments under the hood.

Main characteristics:
- Multi-tab UI separated by module:
  - Automatic Migration
  - Google Photos
  - Synology Photos
  - Immich Photos
  - Other Features
- General/optional arguments available for all tabs.
- Real command preview + execution output in the browser.
- Backend powered by `FastAPI` + `uvicorn` on port `6078`.

Web interface source code:
- `src/web_interface/app.py`
- `src/web_interface/html/index.html`
- `src/web_interface/html/doc_view.html`
- `src/web_interface/static/style.css`

## Deploy Web Interface with Docker Compose
### 0) Install Docker first (Windows / Linux / macOS)

Before running Docker Compose, install Docker on your host:

- **Windows (recommended):** Install Docker Desktop  
  https://docs.docker.com/desktop/setup/install/windows-install/

- **macOS (recommended):** Install Docker Desktop  
  https://docs.docker.com/desktop/setup/install/mac-install/

- **Linux:** Install Docker Engine + Docker Compose plugin  
  https://docs.docker.com/engine/install/

After installation, verify Docker is working:

```bash
docker --version
docker compose version
```

If you are on Linux and want to run Docker without `sudo`, follow:
https://docs.docker.com/engine/install/linux-postinstall/

### 1) Configure Docker deployment files
Create or download to 'docker' folder the following files:
- `docker/docker-compose.yml`
- `docker/.env`

Example `.env`:

```env
# Timezone
TZ=Europe/Madrid

# <you must find out your PUID/PGID through SSH, run in terminal: id $user. If needed, change $user to the user you created.>
PUID=1001
PGID=1001

# Container Name
CONTAINER_NAME=photomigrator

# Host Port
PORT=6078
PORT_DEV=6071

# Config dir, where the config is stored (host paths)
CONFIG_DIR=../config

# Data dir, where the tool will look for inputs, and save the outputs and intermediate files (host paths)
DATA_DIR=../data

# Volumes dir, other folder that you may want to mount on the tool (host paths)
VOLUMES_DIR=/volume1

# App dir, whith the source code (for docker-compose-env.yml only)
APP_DIR=../

# Comma-separated list of allowed base folders for "Remove Selected" in the web folder picker.
# Any delete request outside these roots will be rejected.
PHOTOMIGRATOR_WEB_DELETE_ROOTS=/app/data,/app/config,/app/volumes

# Docker image tag to pull
IMAGE_TAG=latest-stable
```

Example `docker-compose.yml`:

```yaml
# PhotoMigrator Web Interface compose file for production.
services:
  photomigrator:
    image: jaimetur/photomigrator:${IMAGE_TAG}
    container_name: ${CONTAINER_NAME}
    ports:
      - "${PORT}:6078"
    env_file:
      - .env
    environment:
      - PUID=${PUID}
      - PGID=${PGID}
      - TZ=${TZ}
      - PHOTOMIGRATOR_WEB_DELETE_ROOTS=${PHOTOMIGRATOR_WEB_DELETE_ROOTS}
    volumes:
      - ${CONFIG_DIR}:/app/config
      - ${DATA_DIR}:/app/data
      - ${VOLUMES_DIR}:/app/volumes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import os,sys,urllib.request; port=os.getenv('PORT','6078'); urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=5); sys.exit(0)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

### 2) Start it

```bash
cd docker
docker compose pull
docker compose up -d
```

Then open:
- `http://localhost:6078`

## Arguments Description
Check all arguments descriptions and usage examples in the [Arguments Description](/help/2-arguments-description.md)  or in the [shorter version](/help/2-arguments-description-short.md).


## 📘 All Documentation Links
- [Configuration File](/help/0-configuration-file.md)  
- [Command Line Interface (CLI)](/help/1-command-line-interface.md)  
- [Arguments Description](/help/2-arguments-description.md)  
- [Automatic Migration Feature](/help/3-automatic-migration.md)  
- [Google Takeout Management](/help/4-google-takeout.md)  
- [Synology Photos Management](/help/5-synology-photos.md)  
- [Immich Photos Management](/help/6-immich-photos.md)  
- [Other Features](/help/7-other-features.md)  
- [GPTH Tool Pipeline Description](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/00_GPTH_complete_pipeline.md)


## ▶️ Execution Methods
There are three different methods to execute this Tool:
- From [Compiled Binaries](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-binaries.md)
- From [Docker Container](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-docker.md)
- From [Source Repository](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/execution-from-source.md)
- From [Web Interface (docker)](#deploy-web-interface-with-docker-compose)  

Below tables show the pros and cons of each method together with a comparative rating of each one of them for you to decide which one fits best with your needed: 

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

## 📅 ROADMAP
The Planned Roadmap for futures releases can be checked in the following link:
[Planned Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/ROADMAP.md)

## 🛡️ CODE OF CONDUCT
By participating in this project, you agree to abide by our [Code of Conduct](https://github.com/jaimetur/PhotoMigrator/blob/main/CODE_OF_CONDUCT.md).

## 📢 Disclaimer

- ⚠️ The project is under **very active** development.
- ⚠️ Expect bugs and breaking changes.
  
---

## 📊 Repository activity
![Alt](https://repobeats.axiom.co/api/embed/b3021f0fd0db11466b473e34c9de04cc5d85f110.svg "Repobeats analytics image")

## 📈 Star History
<a href="https://www.star-history.com/#jaimetur/PhotoMigrator&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=jaimetur/PhotoMigrator&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=jaimetur/PhotoMigrator&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=jaimetur/PhotoMigrator&type=Date" />
 </picture>
</a>

## 👥 Contributors
<a href="https://github.com/jaimetur/PhotoMigrator/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=jaimetur/PhotoMigrator" width="15%"/>
</a>

If you want to Contribute to this project please, first read the file [CONTRIBUTING.md](https://github.com/jaimetur/PhotoMigrator/blob/main/CONTRIBUTING.md)

---

## 🤝 Related Projects
- [Synology Photos](https://www.synology.com/es-mx/dsm/feature/photos) Create albums full of precious moments, share your perfectly framed photos, and store them securely on your Synology NAS. 
- [Immich Photos](https://github.com/immich-app/immich) High performance self-hosted photo and video management solution.
- [NextCloud Photos](https://github.com/nextcloud/photos) Your memories under your control. 
- [Google Photos Takeout Helper (GPTH)](https://github.com/Xentraxx/GooglePhotosTakeoutHelper) Script that organizes the Google Takeout archive into one big chronological folder. 
- [Exiftool](https://github.com/exiftool/exiftool) Metadata information reader/writer. 
    
---

## 🎖️ Credits
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/Xentraxx/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)/[Wacheee](https://github.com/Wacheee) and v4.x.x by [Xentraxx](https://github.com/Xentraxx)
  
---

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
