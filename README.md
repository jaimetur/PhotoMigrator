<p align="center">
  <img src="/assets/logos/logo_17_1024x1024.png?raw=true" alt="PhotoMigrator Logo" width="600" height="480" />
</p>


# 📈 Repo Statistics
[![Commit activity](https://img.shields.io/github/commit-activity/y/jaimetur/PhotoMigrator?label=Commit%20activity)](https://github.com/jaimetur/PhotoMigrator/graphs/contributors)
[![Resolved Github issues](https://img.shields.io/github/issues-closed/jaimetur/PhotoMigrator?label=Resolved%20issues)](https://github.com/jaimetur/PhotoMigrator/issues?q=is%3Aissue%20state%3Aclosed)
[![Open Github issues](https://img.shields.io/github/issues/jaimetur/PhotoMigrator?label=Open%20Issues)](https://github.com/jaimetur/PhotoMigrator/issues)
[![Total Github Releases downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/total?label=Total%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases)
[![Latest version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/latest/total?label=Latest%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases/latest)
[![Pre-release version downloads](https://img.shields.io/github/downloads/jaimetur/PhotoMigrator/v4.6.0/total?label=Pre%20version%20downloads)](https://github.com/jaimetur/PhotoMigrator/releases?q=prerelease%3Atrue)


# 📸 **PhotoMigrator**
This tool has been designed to Interact and Manage different Photo Services such as Google Photos, Synology Photos, Immich Photos, NextCloud Photos, Google Takeout & Apple iCloud Takeout, and allow users to do an <span style="color:green">**Automatic Migration**</span> from one Photo Cloud service to other or from one account to a new account of the same Photo Cloud service.  

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
![Automatic Migration](assets/screenshots/web-interface-automatic-migration.png?raw=true)  

### Automatic Migration Feature (Live Dashboard):
![Automatic Migration (Live Dashboard)](assets/screenshots/web-interface-automatic-migration-live-dashboard.png?raw=true)   

### Google Takeout Feature:
![Google Takeout](assets/screenshots/web-interface-google-takeout.png?raw=true)  

### iCloud Takeout Feature:
![iCloud Takeout](assets/screenshots/web-interface-icloud-takeout.png?raw=true)  

### Synology Photos Feature:
![Synology Photos](assets/screenshots/web-interface-synology-photos.png?raw=true)  

### Immich Photos Feature:
![Immich Photos](assets/screenshots/web-interface-immich-photos.png?raw=true)  

### Other Features:
![Other Features](assets/screenshots/web-interface-other-features.png?raw=true)  

### General Arguments:
![General Arguments](assets/screenshots/web-interface-general-arguments.png?raw=true)  

### Configuration Panel:
![Configuration Panel](assets/screenshots/web-interface-configuration-panel.png?raw=true)  

### App Settings:
![App Settings](assets/screenshots/web-interface-app-settings.png?raw=true)  

## 🖥️ Automatic Migration on Terminal
![Live Dashboard](assets/screenshots/live_dashboard.jpg?raw=true)  

# 🌟 Main Modules:
## 🚀 1. Automatic Migration   
The main use case is the **Automatic Migration Feature** to migrate all your photos and videos from one Photo cloud service to other, or between different accounts of the same service.  

> [!IMPORTANT]
> Since April 1, 2025, Google Photos can no longer be used by third-party apps as a full-library `SOURCE` for Automatic Migration because Google removed the legacy read scopes from the Library API. Use Google Takeout as `--source` instead. Google Photos remains usable as an upload target with the supported scopes.

> [!TIP]
> Automatic Migration now also auto-detects raw Apple iCloud Takeout folders used as `--source`, preprocesses them first, and then migrates the resulting library to the target. If the local source contains ZIP files, they are unpacked first and the extracted folder is then classified as Google Takeout, iCloud Takeout, or a normal local folder. That automatic iCloud preprocessing enables `Memories` by default, and when a local source contains a `Memories` folder those collections are treated the same way as `Albums`.

> [!TIP]
> For local-folder based migrations and uploads, you can exclude generated thumbnails or other unwanted content using glob patterns with `--exclude-folders` and `--exclude-files`.
>
> Example:
> `--exclude-folders @eaDir .@__thumb @Recycle --exclude-files SYNOFILE_THUMB* SYNOPHOTO_THUMB* SYNOPHOTO_FILM* Thumbs.db .DS_Store`

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Automatic Migration Documentation)**](help/03-automatic-migration.md)


## 🛠️ 2. Google Takeout Fixing 
Other important feature included in the tool is the Google Takeout Fixing. 

This feature has been designed to automatically analyze your Google Photos Takeout, extract all the information from the sidecar JSON files (or guess some missing information using heuristics algorithms) and embeds all the extracted info into each asset file using EXIF tags.  

In this way your Media Library will be ready to be migrated to any other Cloud Photo services without losing any important info such as, Albums info, Original date, GPS location, Camera info, etc...

But this feature also helps you to organize and clean your Media Library removing duplicates, creating Year/Month folder structure, creating symbolic links for Albums assets, Auto renaming Albums to clean their names and include a prefix with the date of its assets, Process Motion/Live Pictures, etc...

The whole process is done in an automatic way and is divided in different steps (some of them are optionals).

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Google Takeout Fixing Documentation)**](help/04-google-takeout.md)

## 🍎 3. iCloud Takeout Fixing
Other important feature included in the tool is the iCloud Takeout Fixing.

This feature has been designed to process Apple iCloud Photos privacy exports, recover the original capture dates from `Photo Details.csv`, assign those dates to the exported assets, and rebuild Albums from Apple CSV manifests.

In this way your Media Library will be ready to be migrated to any other Cloud Photo services without losing important information such as Original date and Albums relationships.

But this feature also helps you to reconstruct the exported library structure in a more usable way, including optional `Memories` rebuilding when those manifests are present in the export.

The whole process is done in an automatic way and is independent from the cloud-service management modules.

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(iCloud Takeout Fixing Documentation)**](help/05-icloud-takeout.md)

## 🖼️ 4. Google Photos / Synology Photos / Immich Photos / NextCloud Photos
Apart from the `Automatic Migration`, `Google Takeout Fixing`, and `iCloud Takeout Fixing` features, you can also use the tool to manage Google Photos and different Photo Cloud Services.

- **Google Photos** supports direct upload/download operations through the official API.
- **Synology Photos**, **Immich Photos**, and **NextCloud Photos** provide cloud management and migration operations.

Currently, the Features Supported per each Photo Cloud Service are:

  | Feature                         | Google Photos                                   | Synology Photos                                                                        | Immich Photos                                                                      | Nextcloud Photos                                                                         |
  |---------------------------------|-------------------------------------------------|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
  | Upload Album(s) (from folder)   | [doc](help/06-google-photos.md#upload-albums)   | [doc](help/07-synology-photos.md#upload-albums-from-local-folder-into-synology-photos) | [doc](help/08-immich-photos.md#upload-albums-from-local-folder-into-immich-photos) | [doc](help/09-nextcloud-photos.md#upload-albums-from-local-folder-into-nextcloud-photos) |
  | Download Album(s) (into folder) | [doc](help/06-google-photos.md#download-albums) | [doc](help/07-synology-photos.md#download-albums-from-synology-photos)                 | [doc](help/08-immich-photos.md#download-albums-from-immich-photos)                 | [doc](help/09-nextcloud-photos.md#download-albums-from-nextcloud-photos)                 |
  | Upload ALL (from folder)        | [doc](help/06-google-photos.md#upload-all)      | [doc](help/07-synology-photos.md#upload-all-from-local-folder-into-synology-photos)    | [doc](help/08-immich-photos.md#upload-all-from-local-folder-into-immich-photos)    | [doc](help/09-nextcloud-photos.md#upload-all-from-local-folder-into-nextcloud-photos)    |
  | Download ALL (into folder)      | [doc](help/06-google-photos.md#download-all)    | [doc](help/07-synology-photos.md#download-all-from-synology-photos)                    | [doc](help/08-immich-photos.md#download-all-from-immich-photos)                    | [doc](help/09-nextcloud-photos.md#download-all-from-nextcloud-photos)                    |
  | Remove ALL Assets               | Not supported by API                            | [doc](help/07-synology-photos.md#remove-all-assets-from-synology-photos)               | [doc](help/08-immich-photos.md#remove-all-assets-from-immich-photos)               | [doc](help/09-nextcloud-photos.md#remove-all-assets-from-nextcloud-photos)               |
  | Remove ALL Albums               | Not supported by API                            | [doc](help/07-synology-photos.md#remove-all-albums-from-synology-photos)               | [doc](help/08-immich-photos.md#remove-all-albums-from-immich-photos)               | [doc](help/09-nextcloud-photos.md#remove-all-albums-from-nextcloud-photos)               |
  | Remove Albums by Name Pattern   | Not supported by API                            | [doc](help/07-synology-photos.md#remove-albums-by-name-pattern-from-synology-photos)   | [doc](help/08-immich-photos.md#remove-albums-by-name-pattern-from-immich-photos)   | [doc](help/09-nextcloud-photos.md#remove-albums-by-name-pattern-from-nextcloud-photos)   |
  | Rename Albums by Name Pattern   | Not supported by API                            | [doc](help/07-synology-photos.md#rename-albums-by-name-pattern-from-synology-photos)   | [doc](help/08-immich-photos.md#rename-albums-by-name-pattern-from-immich-photos)   | [doc](help/09-nextcloud-photos.md#rename-albums-by-name-pattern-from-nextcloud-photos)   |
  | Consolidate Albums Names        | [doc](help/06-google-photos.md#consolidate-albums-names-from-google-photos) | [doc](help/07-synology-photos.md#consolidate-albums-names-from-synology-photos) | [doc](help/08-immich-photos.md#consolidate-albums-names-from-immich-photos) | [doc](help/09-nextcloud-photos.md#consolidate-albums-names-from-nextcloud-photos) |
  | Remove Empty Albums             | Not supported by API                            | [doc](help/07-synology-photos.md#remove-empty-albums-from-synology-photos)             | [doc](help/08-immich-photos.md#remove-empty-albums-from-immich-photos)             | [doc](help/09-nextcloud-photos.md#remove-empty-albums-from-nextcloud-photos)             |
  | Remove Duplicates Albums        | Not supported by API                            | [doc](help/07-synology-photos.md#remove-duplicates-albums-from-synology-photos)        | [doc](help/08-immich-photos.md#remove-duplicates-albums-from-immich-photos)        | [doc](help/09-nextcloud-photos.md#remove-duplicates-albums-from-nextcloud-photos)        |
  | Remove Duplicates Assets        | API deletion unavailable                        | [doc](help/07-synology-photos.md#remove-duplicates-assets-from-synology-photos) | [doc](help/08-immich-photos.md#remove-duplicates-assets-from-immich-photos) | [doc](help/09-nextcloud-photos.md#remove-duplicates-assets-from-nextcloud-photos) |
  | Merge Duplicates Albums         | Not supported by API                            | [doc](help/07-synology-photos.md#merge-duplicates-albums-from-synology-photos)         | [doc](help/08-immich-photos.md#merge-duplicates-albums-from-immich-photos)         | [doc](help/09-nextcloud-photos.md#merge-duplicates-albums-from-nextcloud-photos)         |

> [!NOTE]
> For more info you can check the feature documentation in below links:
>
>- [**(Google Photos Documentation)**](help/06-google-photos.md)
>
>- [**(Synology Photos Documentation)**](help/07-synology-photos.md)
> 
>- [**(Immich Photos Documentation)**](help/08-immich-photos.md)
>
>- [**(NextCloud Photos Documentation)**](help/09-nextcloud-photos.md)

> [!IMPORTANT]  
>- **NextCloud Photos** is available since v4.0.0 using WebDAV-based integration.
>
>- **Google Photos** is available since v4.0.0 with partial support due current official API limitations. Since April 1, 2025, Google Photos full-library reads are no longer available through the public Library API, so use Google Takeout for migrations/downloads of a full library and Google Photos mainly as upload target.


## 🧩 5. Other Standalone Features  
Finally, the Tool also contains Other Useful Standalone Features such as:
  - **Metadata fixing** of any Photo Library in your local drive (not necessarily needs to be a Google Takeout folder)
  - **Library Organization** features:
    - Manage Duplicates assets
    - Organize any local folder by capture date into `year`, `year/month`, `year-month`, or `flatten`
    - Splitting of assets with and without associated albums
    - Folder structure (customizable) for `Albums`, cloud `No_Albums`, and Takeout `ALL_PHOTOS` master libraries
  - **Symbolic Links Support** for Albums folders
    - Fix Symbolic Links Broken
  - **Homogenize Albums folder's name based on content**

> [!NOTE]
> For more info you can check the feature documentation in below link:
>
> [**(Other Standalone Features Documentation)**](help/10-other-features.md)

---
#  🖥️ Tool Interfaces

## 🌐 1. Web Interface (New)
PhotoMigrator now includes a Web Interface that executes the same CLI arguments under the hood.

Main characteristics:
- Multi-tab UI separated by module:
  - Automatic Migration
  - Google Takeout
  - iCloud Takeout
  - Google Photos
  - Synology Photos
  - Immich Photos
  - NextCloud Photos
  - Other Features
- General/optional arguments available for all tabs.
- Automatic Migration and local-folder workflows support exclusion filters for unwanted folders/files such as `@eaDir`, `.@__thumb`, `@Recycle`, `SYNOFILE_THUMB*`, `SYNOPHOTO_THUMB*`, `SYNOVIDEO_THUMB*`, `SYNOPHOTO_FILM*`, `Thumbs.db`, `ehthumbs.db`, `.DS_Store`, or `._*`.
- Real command preview + execution output in the browser.
- Backend powered by `FastAPI` + `uvicorn` on port `6078`.

> [!NOTE]
> You can access to the new Web Interface (demo) on this link: 
> 
> [**PhotoMigrator Web Interface (demo)**](https://photomigrator.jaimetur.cloud)  
> 
>    Username: demo  
>    Password: demo

### Deploy Web Interface with Docker

The complete Docker guide for the Web Interface now lives in:

- [Deploy Web Interface from Docker](help/docker-deployments/deploy-web-interface-from-docker.md)

That guide includes:

- Linux, Windows, and macOS instructions
- direct download commands for `docker-compose.yml` and `.env`
- a ready-to-use `.env` that works without mandatory edits for local use
- a clear split between mandatory, recommended, and optional customization

Quick start:

```bash
cd docker-web
docker compose pull
docker compose up -d
```

Then open:

- `http://localhost:6078`

## 🪟 2. Graphical User Interface (GUI) and Terminal Interactive User Interface (TUI)
PhotoMigrator includes two local interactive interfaces in addition to the Web Interface:

- **Desktop GUI**: a native windowed interface built with `tkinter`.
- **Terminal TUI**: an interactive terminal interface built with `Textual`.

Both interfaces expose the same high-level structure:
- `Feature Selector`
- `Features Config`
- `General Arguments`
- `App Settings`
- command preview, status panel, and execution log

Default launcher behavior:
- Running `PhotoMigrator` without arguments tries to open the **Desktop GUI** first.
- If the GUI cannot be started because `tkinter` or a graphical display is not available, PhotoMigrator falls back to the **Terminal TUI**.
- If neither interactive interface can be started, PhotoMigrator falls back to the CLI and shows the arguments descriptions (same output as `--help`).

Explicit launchers:
- `PhotoMigrator --gui` opens the Desktop GUI explicitly.
- `PhotoMigrator --tui` opens the Terminal TUI explicitly.
- `PhotoMigrator --configuration-file /path/to/Config.ini` can be combined with either launcher, or used on its own, to open the default interactive UI with a different configuration file preloaded.

Config file behavior in GUI/TUI:
- If no explicit configuration path is provided, both interfaces use `./Config.ini` from the current execution folder, matching the classic CLI behavior.
- You can also change the file later inside `General Arguments > Configuration File`.

Typical use:
- Use the **Desktop GUI** on Windows, macOS, or Linux systems with graphical desktop access.
- Use the **Terminal TUI** on SSH sessions, server terminals, or environments where a graphical window is not available but the terminal supports interactive rendering.

### 2.1 Graphical User Interface (GUI):
![GUI](assets/screenshots/gui-interface.png?raw=true)  

### 2.2 Terminal Interactive User Interface (TUI):
![TUI](assets/screenshots/tui-interface.png?raw=true)  

## ⌨️ 3. Command Line Interface (CLI)
This Tool is based on commands given through the Command Line Interface (CLI), so it is important to know the syntax of that interface.  

PhotoMigrator now also includes an interactive CLI TUI that mirrors the Web Interface structure much more closely:

- Feature Selector with the same top-level modules as the Web Interface
- `General Arguments`, `Features Config`, and `App Settings` views
- Dynamic forms for `Automatic Migration`, `Google Takeout`, `iCloud Takeout`, cloud-service actions, and standalone features
- Multi-account `Features Config` selectors for `Google Photos`, `Synology Photos`, `Immich Photos`, and `NextCloud Photos`
- Live command preview and in-terminal execution log panel

Quick launch:

```bash
python ./src/PhotoMigrator.py
```

This now opens the desktop GUI by default.

Force the CLI TUI explicitly:

```bash
python ./src/PhotoMigrator.py --tui
```

Open the desktop GUI explicitly:

```bash
python ./src/PhotoMigrator.py --gui
```

Open either interactive UI with an explicit configuration file:

```bash
python ./src/PhotoMigrator.py --gui --configuration-file ./Config.ini
python ./src/PhotoMigrator.py --tui --configuration-file ~/PhotoMigrator/custom.ini
```

Launcher fallback order when no arguments are provided:
- Desktop GUI
- CLI TUI
- Command-line help (`--help`)

You can check the whole list of features and arguments with the right syntax here:
[Command Line Interface (CLI)](help/01-command-line-interface.md)

### Arguments Description
Check all arguments descriptions and usage examples in the [Arguments Description](help/02-arguments-description.md)  or in the [shorter version](help/02-arguments-description-short.md).


## 📘 All Documentation Links
- [Configuration File](help/00-configuration-file.md)  
- [Command Line Interface (CLI)](help/01-command-line-interface.md)  
- [Arguments Description](help/02-arguments-description.md)  
- [Automatic Migration Feature](help/03-automatic-migration.md)  
- [Google Takeout Management](help/04-google-takeout.md)  
- [iCloud Takeout Management](help/05-icloud-takeout.md)
- [Google Photos Management](help/06-google-photos.md)
- [Synology Photos Management](help/07-synology-photos.md)  
- [Immich Photos Management](help/08-immich-photos.md)  
- [NextCloud Photos Management](help/09-nextcloud-photos.md)  
- [Other Features](help/10-other-features.md)  
- [GPTH Tool Pipeline Description](help/11-GPTH-complete-pipeline.md)
- [Docker Deployment Documentation](help/12-docker-deployment.md)

## 📘 Docker Deployments Documentation Links
- [Deploy Web Interface from Docker](help/docker-deployments/deploy-web-interface-from-docker.md)
- [Deploy CLI Interface from Docker](help/docker-deployments/deploy-cli-interface-from-docker.md)


---

## ▶️ Execution Methods
There are four different methods to execute this Tool:
- Execute from [Compiled Binaries](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/cli-interface-from-binaries.md)
- Execute from [Source Repository](https://github.com/jaimetur/PhotoMigrator/blob/main/help/execution/cli-interface-from-source.md)
- Deploy [Web Interface (from docker)](https://github.com/jaimetur/PhotoMigrator/blob/main/help/docker-deployments/deploy-web-interface-from-docker.md)
- Deploy [CLI Interface (from docker)](https://github.com/jaimetur/PhotoMigrator/blob/main/help/docker-deployments/deploy-cli-interface-from-docker.md)

Below tables show the pros and cons of each method together with a comparative rating of each one of them for you to decide which one fits best with your needed: 

### 🆚 Execution Methods Comparison
   | Execution Method  | Difficulty | Pros                                                                                                                                             | Cons                                                                                                                                                                                                         |
   |-------------------|:----------:|--------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
   | **Binaries**      |     🟢     | ✅ Only basic knowledge on command line commands needed                                                                                           | ❌ Platform and architecture dependent<br>❌ Need basic knowledge of running command line instructions<br>❌ Some anti-virus may detect the tool as suspicious in Windows systems                               |
   | **Docker**        |     ⭐      | ✅ Platform and architecture independent<br>✅ Easy configuration via `docker.conf` <br>✅ Automatically pulls latest image if `RELEASE_TAG=latest` | ❌ Need intermediate knowledge of running command line instructions<br>❌ Need to install Docker (if not already installed)<br>❌ All paths given as arguments must be relative to the execution folder         |
   | **Source**        |     🔴     | ✅ Platform and architecture independent                                                                                                          | ❌ Need advance knowledge of running command line instructions<br>❌ Need to install Git and Python 3.8+ (if not already installed). <br>❌ Need to pull the source repository again to update to a new release |
   | **Web Interface** |    🟢⭐     | ✅ Platform and architecture independent<br>✅ Easy configuration via `.env` file <br>✅ Automatically pulls latest image if `IMAGE_TAG=latest`     | ❌ In Windows/MacOS you need to install Docker Desktop                                                                                                                                                        |

  🟢 *Easiest way*    ⭐ *Recommended*    🔴 *More difficult*


### 🆚 Execution Methods Comparison Rating
  | Feature                                               | Binaries<br>(*easiest way*) | Docker<br>(*balanced*) | Source<br>(*more difficult*) | Web Interface<br>(*recommended*) |
  |-------------------------------------------------------|-----------------------------|------------------------|------------------------------|----------------------------------|
  | Platform and architecture independence                | ⭐☆☆☆☆                       | ⭐⭐⭐⭐⭐                  | ⭐⭐⭐⭐⭐                        | ⭐⭐⭐⭐⭐                            |
  | Ease of updating to new release                       | ⭐⭐⭐☆☆                       | ⭐⭐⭐⭐⭐                  | ⭐☆☆☆☆                        | ⭐⭐⭐⭐⭐                            |
  | Allow paths arguments point outside execution folder  | ⭐⭐⭐⭐⭐                       | ⭐☆☆☆☆                  | ⭐⭐⭐⭐⭐                        | ⭐⭐⭐⭐☆                            |
  | No Requires Technical knowledge (Command line syntax) | ⭐⭐⭐⭐⭐                       | ⭐⭐⭐☆☆                  | ⭐☆☆☆☆                        | ⭐⭐⭐⭐☆                            |
  | No Requires additional tools/software                 | ⭐⭐⭐⭐⭐                       | ⭐⭐⭐☆☆                  | ⭐☆☆☆☆                        | ⭐⭐⭐⭐☆                            |
  | No Risk of Antivirus alert (especially on Windows)    | ⭐⭐☆☆☆                       | ⭐⭐⭐⭐⭐                  | ⭐⭐⭐⭐⭐                        | ⭐⭐⭐⭐⭐                            |
  | **Average Rating**                                    | ⭐⭐⭐⭐☆                       | ⭐⭐⭐⭐☆                  | ⭐⭐⭐☆☆                        | ⭐⭐⭐⭐☆                            |
  | **Average Score**                                     | 3.5                         | 3.7                    | 3.0                          | 4.5                              |


---

## 💾 Download
Download the tool either for Linux, MacOS or Windows (for both x64 and arm64 architectures) or Docker version (platform & architecture independent) as you prefer, directly from following links:

- [Latest Stable Release](https://github.com/jaimetur/PhotoMigrator/releases/latest)
- [Pre-Release](https://github.com/jaimetur/PhotoMigrator/releases?q=%22alpha%22+OR+%22beta%22+OR+%22RC%22&expanded=true)
- [All Releases](https://github.com/jaimetur/PhotoMigrator/releases)  

Or check the [Changelog](CHANGELOG.md) to choose any specific release. 

> [!NOTE]  
> The Tool is Multi-Platform and Multi-Architecture, and has been designed to be run directly from Windows systems, MacOs or within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), so feel free to download the version according to your system. 
> 
> You can also execute the Tool from a Docker container or from sources files for a better compatibility. In below sections you can find the execution instructions to run the Tool from the different methods.
>
> Compiled binary names are currently platform-specific:
> - Windows: `PhotoMigrator.exe`
> - macOS: `PhotoMigrator_vx.y.z_macos_<arch>.command`
> - Linux / Synology SSH: `PhotoMigrator_vx.y.z_linux_<arch>.bin`

> [!IMPORTANT]  
> On macOS, downloaded unsigned binaries may be blocked by Gatekeeper on first launch. If that happens, run:
> `chmod +x ./PhotoMigrator_vx.y.z_macos_<arch>.command && xattr -dr com.apple.quarantine ./PhotoMigrator_vx.y.z_macos_<arch>.command`
> and then execute that same `.command` file again from Terminal or Finder. Replace `x.y.z` and `<arch>` with the exact version and architecture you downloaded.


## ⚙️ Configuration File
In order to connect to the different Photo Cloud Services, you must configure the connection settings using the Configuration file `Config.ini` provided with the Tool.  

When running the Web Interface in Docker/Compose/Kubernetes, you can also override the same cloud-service keys through environment variables. Supported config keys can be provided directly as `KEY=value` or through Docker-secret style `KEY_FILE=/path/to/secret`. Runtime precedence is: environment variable > `Config.ini` > template default. This is useful for `IMMICH_URL`, `IMMICH_API_KEY_ADMIN`, `SYNOLOGY_*`, `NEXTCLOUD_*`, `GOOGLE_PHOTOS_*`, etc.

You can see how to configure the Configuration File in this help section:
[Configuration File](help/00-configuration-file.md) 

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

> [!CAUTION]
>- ⚠️ The project is under **very active** development.
>- ⚠️ Expect bugs and breaking changes.
  
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
