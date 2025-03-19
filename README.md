# CloudPhotoMigrator

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
  (not available yet but is on the ROADMAP.md for next release)

- **Google Photos**  
  (not available yet but is on the ROADMAP.md for next release)


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

The Script is Multi-Platform and Multi-Architecture, and has been designed to be run directly within a Linux Server or NAS such as Synology NAS (Compatible with DSM 7.0 or higher), 
so feel free to download the version according to your system.

## Download:
Download the tool either for Linux, MacOS or Windows version (for both x64/amd64 or arm64 architectures) as you prefer directly from following links:

- [Latest Stable Release](https://github.com/jaimetur/CloudPhotoMigrator/releases/tag/v3.0.0)
- [Pre-Release](https://github.com/jaimetur/CloudPhotoMigrator/releases/tag/v3.1.0-alpha)
- [All Releases](https://github.com/jaimetur/CloudPhotoMigrator/releases)

## Documentation Links:
- [Command Line Syntax](/help/0-command-line-syntax.md)  
- [Automated Migration Feature](/help/1-automated-migration.md)  
- [Google Takeout Management](/help/2-google-takeout.md)  
- [Synology Photos Management](/help/3-synology-photos.md)  
- [Immich Photos Management](/help/4-immich-photos.md)  
- [Other Features](/help/5-other-features.md)  

## Live Dashboard Preview:
![Live Dashboard](/assets/screenshots/live_dashboard.jpg)


## Instructions to execute from compiled version:
You can copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

Then you just need to call it depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**CloudPhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**CloudPhotoMigrator.run**'.  
    Minimum version required to run the Tool directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

## Instructions to execute from source repository:
Here are simple instructions to clone the GitHub repository, create a Python virtual environment, install dependencies, and run the main script:

1. Clone the repository
   ```
   git clone https://github.com/jaimetur/CloudPhotoMigrator.git
   cd CloudPhotoMigrator
   ```

2. Create a virtual environment:  
   ```
   python3 -m venv venv
   ```

3. Activate the virtual environment:  
   - On macOS/Linux:  
     ```
     source venv/bin/activate
     ```

   - On Windows (Command Prompt):  
     ```
     venv\Scripts\activate
     ```

   - On Windows (PowerShell):  
     ```
     venv\Scripts\Activate.ps1
     ```

4. Install dependencies:  
   ```
   pip3 install -r requirements.txt
   ```

5. Run the main script:  
   ```
   python3 ./src/CloudPhotoMigrator.py
   ```

## Command Line Syntax:
You can check the whole list of functions and arguments with the right syntax here:  
[Command Line Syntax](help/0-command-line-syntax.md)

## Main Use Case: Automated Migration Feature

> [!NOTE]  
>## <span style="color:green">Automated Migration Feature</span>
>From version 3.0.0 onwards, the Tool supports a new Extra Mode called '**AUTOMATED-MIGRATION**' Mode. 
>
> Use the argument **'--source'** to select the \<SOURCE> and the argument **'--target'** to select \<TARGET> for the AUTOMATED-MIGRATION Process to Pull all your Assets (including Albums) from the \<SOURCE> Cloud Service and Push them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
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
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  
> 
> By default, the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Push workers.  
> The Pull worker and the different Push workes will be executed in parallel using an assets queue to garantee that no more than 100 assets will be temporarily stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default, (if your terminal size has enough width and heigh) a Live Dashboard will show you all the datails about the migration process, including most relevant log messages, and counter status. You can disable this Libe Dashboard using the flag **'--dashboard=false'**.   
> 
> Additionally, this Automated Migration process can also be executed secuencially instead of in parallel, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
> 
> Also, take into account that in this case, the Live Dashboard will not be displayed, so you only will see the different messages log in the screen, but not the live counters during the migration.  
> and execute this Extra Mode, the Tool will automatically do the whole migration job from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.  

> [!IMPORTANT]  
> If you use a local folder <INPUT_FOLDER> as source client, all your Albums should be placed into a subfolder called *'Albums'* within <INPUT_FOLDER>, creating one Album subfolder per Album, otherwise the tool will no create any Album in the target client.  
>
> Example:  
> <INPUT_FOLDER>/Album1  
> <INPUT_FOLDER>/Album2  

## Live Dashboard Preview:
![Live Dashboard](/assets/screenshots/live_dashboard.jpg)


## **Examples of use:**

- **Example 1:**
```
./CloudPhotoMigrator.run --source=/homes/MyTakeout --target=synology-1
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will process the folder '/homes/MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
    correct date and time, and identifying which assets belongs to each Album created on Google Photos.  

  - Second, the Tool will connect to your Synology Photos account 1 (if you have configured properly the Config.ini file) and will 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Takeout files and associating
    all the assets included in each Album in the same way that you had on your Google Photos account.



- **Example 2**:
```
./CloudPhotoMigrator.run --source=synology-2 target=immich-1
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Synology Photos account 2 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.


- **Example 3**:
```
./CloudPhotoMigrator.run --source=immich-2 target=/homes/local_folder
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will push all the pulled assets into the local folder '/homes/local_folder' creating a folder structure
    with all the Albums in the subfolder 'Albums' and all the assets without albums associated into the subfolder 'No-Albums'. 
    This 'No-Albums' subfolder will have a year/month structure to store all your asset in a more organized way.  


- **Example 4**:
```
./CloudPhotoMigrator.run --source=immich-1 target=immich-2
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.



## Config.ini
>```
># Configuration for Google Takeout
>[Google Takeout]
># No configuration needed for this module for the time being.
>
># Configuration for Synology Photos
>[Synology Photos]
>SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
>SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
>SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
>SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
>
># Configuration for Immich Photos
>[Immich Photos]
>IMMICH_URL                  = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>IMMICH_API_KEY_ADMIN        = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>
>IMMICH_API_KEY_USER_1       = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_1           = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_1           = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
>
>IMMICH_API_KEY_USER_2       = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_2           = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_2           = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
>
>IMMICH_FILTER_ARCHIVE       = False                                         # Optional: Used as Filter Criteria for Assets downloading (True/False)
>IMMICH_FILTER_FROM          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>IMMICH_FILTER_TO            = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>IMMICH_FILTER_COUNTRY       = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: Spain)
>IMMICH_FILTER_CITY          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Madrid', 'Málaga'])
>IMMICH_FILTER_PERSON        = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Mery', 'James'])
>```


# ROADMAP:

## v3.1.0
### Release Date: (estimated)
  - Alpha version.   : 2025-03-14
  - Beta version     : 2025-03-21
  - Release Candidate: 2025-03-28
  - Official Release : 2025-03-31

### TODO:
- [x] Included Live Progress Dashboard in Automated Migration process for a better visualization of the job progress.
- [x] Added a new argument **'--source'** to specify the \<SOURCE> client for the Automated Migration process.
- [x] Added a new argument **'--target'** to specify the \<SOURCE> client for the Automated Migration process.
- [x] Added new flag '**--dashboard=[true, false]**' (default=true) to show/hide Live Dashboard during Atomated Migration Job.
- [x] Removed argument **'-AUTO, --AUTOMATED-MIGRATION \<SOURCE> \<TARGET>'** because have been replaced with two above arguments for a better visualization.
- [x] Completelly refactored Automated Migration Process to allow parallel threads for Downloads and Uploads jobs avoiding downloading all assets before to upload them (this will save disk space and improve performance). Also objects support has been added to this mode for an easier implementation and future enhancements.
- [x] Support for 'Uploads Queue' to limit the max number of assets that the Downloader worker will store in the temporary folder to 100 (this save disk space). In this way the Downloader worker will never put more than 100 assets pending to Upload in the local folder.
- [x] Support Migration between 2 different accounts on the same Cloud Photo Service. 
- [x] Support to use Local Folders as SOURCE/TARGET during Automated Migration Process. Now the selected local folder works equal to other supported cloud services.
- [x] Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassTakeoutFolder, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
- [x] Added new Class ClassLocalFolder with the same methods as other supported Cloud Services Classes to manage Local Folders in the same way as a Photo Cloud Service.
- [x] ClassTakeoutFolder inherits all methods from ClassLocalFolder and includes specific methods to process Google Takeouts since at the end Google Takeout is a local folder structure.
- [x] Updated GPTH version to cop latest changes in Google Takeouts. 
- [x] Minor Bug Fixing.

- [ ] Tests Pending:
  - [ ] Deep Test on Immich Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Synology Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Google Takeout functions. (volunteers are welcomed)
  - [x] Deep Test on Automated Migration Mode. (volunteers are welcomed)


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

## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/TheLastGimbus/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)
