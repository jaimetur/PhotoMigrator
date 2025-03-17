# CloudPhotoMigrator

Welcome to <span style="color:green">**CloudPhotoMigrator** </span>Tool:

This tool has been designed to Interact and Manage different Photos Cloud Services. As of today, the Supported Photo Cloud Services are:
- **Google Photos**
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

Apart from Interact with the different Photo Cloud Services, the Tool also contains some other useful features such as:
- **Metadata fixing** of any Photo Library in your local drive
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

## Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/doc/screenshots/live_dashboard.jpg?raw=true)

## Instructions to execute from compiled version:
You can copy and unzip the downloaded compiled tool into any local folder or to any Shared folder of your server or Synology NAS.

Then you just need to call it depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**CloudPhotoMigrator.exe**'  

  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**CloudPhotoMigrator.run**'.  
    Minimum version required to run the script directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

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

## Syntax:
You can check the whole list of functions and arguments and the syntax of the Tool here:
[Syntax](http)


> [!NOTE]  
>## <span style="color:green">Automated Migration Feature</span>
>From version 3.0.0 onwards, the script supports a new Extra Mode called '**AUTOMATED-MIGRATION**' Mode. 
>
> Use the arguments **'-s'** or **'--source'** to select the \<SOURCE> and **'-t'** or **'--target'** to select \<TARGET> for the AUTOMATED-MIGRATION Process to Download all your Assets (including Albums) from the \<SOURCE> Cloud Service and Upload them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2] select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
> 
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  
> 
> By default the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Upload workers.  
> The Download worker and the different Upload workes will be executed in parallel using an assets queue to garantee that no more than 100 assets will be temporary stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default (if your terminal size has enough width and heigh) a Live Dashboard will show you all the datails about the migration process, including most relevant log messages, and counter status.  
> 
> Additionally, this Automated Migration process can also be executed secuencially instead of in parallel, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
> 
> Also, take into account that in this case, the Live Dashboard will not be displayed, so you only will see the different messages log in the screen, but not the live counters during the migration.  
> and execute this Extra Mode, the script will automatically do the whole migration job from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.  


**Examples of use:**

- **Example 1:**
```
./CloudPhotoMigrator.run --source=/homes/MyTakeout --target=synology-1
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will process the folder '/homes/MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
    correct date and time, and identifying which assets belongs to each Album created on Google Photos.  

  - Second, the script will connect to your Synology Photos account 1 (if you have configured properly the Config.ini file) and will 
    upload all the assets processed in previous step, creating a new Album per each Album found in your Takeout files and associating
    all the assets included in each Album in the same way that you had on your Google Photos account.



- **Example 2**:
```
./CloudPhotoMigrator.run --source=synology-2 target=immich-1
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will connect to your Synology Photos account 2 (if you have configured properly the Config.ini file) and 
    download all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the script will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    upload all the assets processed in previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.


- **Example 3**:
```
./CloudPhotoMigrator.run --source=immich-2 target=/homes/local_folder
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and 
    download all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the script will copy all the downloaded assets into the local folder '/homes/local_folder' creating a folder structure
    with all the Albums in the subfolder 'Albums' and all the assets without albums associated into the subfolder 'No-Albums'. 
    This 'No-Albums' subfolder will have a year/month structure to store all your asset in a more organized way.  


>[!NOTE]
>## <span style="color:green">Google Photos Support</span>
>From version 1.0.0 onwards, the script can process your Google Photos Takeout files to fix timestamp, geodata, organize files per year/month, organize assets within album(s) in subfolders, etc...
>
>>#### <span style="color:green">Example 'Config.ini' for Synology Photos:</span>
>>
>>```
>># Configuration for Google Photos
>>[Google Photos]
>>```
>For the time being, Google Photos Takeout support, does not need to include anything in the Config.ini, but it has it own section for futures features.

### <span style="color:blue">Google Takeout Mode: Process Explained:</span>

The whole process will do the next actions if all flags are false (by default):

0. Unzip all the Takeout Zips from the <INPUT_TAKEOUT_FOLDER> into a subfolder named './Unzipped_Takeout_{TIMESTAMP}' (by default). This step will be skipped if you already have your Takeout folder unzipped.
   
1. Pre-Process <INPUT_TAKEOUT_FOLDER> unzipped to delete '`@eaDir`' subfolders (Synology metadata subfolders with miniatures) and to Fix .MP4 files extracted from Live pictures and with no .json file associated.

2. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder (This step can be skipped using flag _'gsgt, --google-skip-gpth-tool_').

3. (Optional) Copy/Move files to output folder manually if GPTH processing was skipped in previous step
  
4. Sync Timestamps of .MP4 files generated by Google Photos with Live Picture files (.heic, .jpg, .jpeg) if both files have the same name and are in the same folder

5. Create Date Folder structure ('flatten', 'year', 'year/month', 'year-month') to Albums and No Albums folders according to the options given by arguments:
   - _'-gafs, --google-albums-folders-structure'_ <'flatten', 'year', 'year/month', 'year-month'>. Applies to each Album folder. Default is ‘flatten’ for Albums
   - _'gnas, --google-no-albums-folder-structure'_ <'flatten', 'year', 'year/month', 'year-month'> Applies to ALL_PHOTOS folder (Photos without any Albums). Default is ‘year/month’ for No-Albums. 

6. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to '<OUTPUT_FOLDER>/No-Albums' folder. This step can be skipped using flag _'-gsma, --google-skip-move-albums'_

7. Finally, the script will look in <OUTPUT_TAKEOUT_FOLDER> for any symbolic link broken and will try to fix it by looking for the original file where the symlink is pointing to.

8. (Optional) In this step, the script will look for any duplicate file on OUTPUT_FOLDER (ignoring symbolic links), and will remove all duplicates keeping only the principal file (giving more priority to duplicates files found into any album folder than those found on 'ALL_PHOTOS' folder. 


The result will be a folder (NAMED '<INPUT_TAKEOUT_FOLDER>_{SUFFIX}_{TIMESTAMP}' by default, but you can or change the default suffix _'fixed'_ by any other using the option _'-gofs, --google-output-folder-suffix <SUFFIX>'_) 
The final OUTPUT_FOLDER will include:
- 'Albums' subfolder with all the Albums without year/month structure (by default).
- 'No-Albums' subfolder with all the photos with year/month structure (by default).

Finally, if you want to use your processed assets within Synology Photos, you just need to move OUTPUT_FOLDER into your /home/Photos folder and let Synology index all files (it will take long time). After that you will be able to explore your photos chronologically on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologically.

It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (408559 files zipped, 168168 photos/video files, 740 albums) and moved it into Synology Photos.  

The whole process took around **~8.5 hours** (or **~3 hours without last two optional steps) and this is the time split per steps**):
0. Extraction process --> 25m
1. Pre-processing Takeout_folder --> 3m 50s
2. GPTH Tool fixing --> 2h 12m
3. <span style="color:grey">(Optional) Copy/Move files to output folder manually if GPTH processing was skipped --> 0h</span>
4. Sync .MP$ timestamps --> 10s
5. Create Date Folder Structure --> 50s
6. Moving Album Folder --> 1s
7. Fix Broken Symlinks --> 10m
8. <span style="color:grey">(Optional) Remove Duplicates after fixing --> 3h</span>
   
NOTE: Step 8 is disabled by default, and is only recommended if you want to save disk space and want to avoid having the same physical file in more than one folder (in case that the same file belongs to multiples Albums).


**Examples of use:**

- **Example 1:**
```
./CloudPhotoMigrator.run --google-input-takeout-folder ./MyTakeout --google-remove-duplicates-files
```
 
In this example, the script will Process you Takeout Files found in folder './MyTakeout' (Unzipping them if needed) and fix
all files found to set the correct date and time, and identifying which assets belongs to each Album created on Google Photos. 
  - After that, the script will create a folder structure based on year/month for the folder '<OUTPUT_TAKEOUT_FOLDER>/No-Albums' (by default).  
  - Also, the script will create a flatten folder structure for each Album subfolder found in '<OUTPUT_TAKEOUT_FOLDER>/Albums.'  
  - Finally, the output files will be placed into './MyTakeout_fixed_timestamp' folder where timestamp is the timestamp of the execution.


>[!NOTE]
>## <span style="color:green">Synology Photos Support</span>
>From version 2.0.0 onwards, the script can connect to your Synology NAS and login into Synology Photos App with your credentials. The credentials need to be loaded from 'Config.ini' file and will have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Synology Photos:</span>
>>
>>```
>># Configuration for Synology Photos
>>[Synology Photos]
>>SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>>SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
>>SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
>>SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
>>SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
>>```
>### Features included:
> - Upload Album(s)
> - Upload ALL (from folder)
> - Download Album(s)
> - Download ALL (into folder)
> - Remove ALL Assets
> - Remove ALL Albums
> - Remove Empty Albums
> - Remove Duplicates Albums

### <span style="color:blue">Delete Empty Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Empty Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Empty Albums in Synology Photos database.  

If any Empty Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-remove-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Duplicates Albums in Synology Photos database.  

If any Duplicated Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-remove-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Synology Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will upload all the assets contained in <INPUT_FOLDER> that are supported by Synology Photos.  

The folder <INPUT_FOLDER> can be passed using the Flag: _'-suf,  --synology-upload-folder <INPUT_FOLDER>'_ 

> [!IMPORTANT]
> <INPUT_FOLDER> should be stored within your Synology Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <INPUT_FOLDER> should have been already indexed by Synology Photos before you can add them to a Synology Photos Album.  
>
>You can check if the files have been already indexed accessing Synology Photos mobile app or Synology Photos web portal and change to Folder View.  
>
>If you can't see your <INPUT_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Synology Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --synology-upload-folder ./MyLibrary
```
With this example, the script will connect to Synology Photos database and process the folder ./MyLibrary and will upload all supported assets found on it.


### <span style="color:blue">Upload Albums into Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Create Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.  

The folder <ALBUMS_FOLDER> can be passed using the Flag: _'-sua,  --synology-upload-albums <ALBUMS_FOLDER>'_ 

> [!IMPORTANT]
> <ALBUMS_FOLDER> should be stored within your Synology Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <ALBUMS_FOLDER> should have been already indexed by Synology Photos before you can add them to a Synology Photos Album.  
>
>You can check if the files have been already indexed accessing Synology Photos mobile app or Synology Photos web portal and change to Folder View.  
>
>If you can't see your <ALBUMS_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Synology Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --synology-upload-albums ./My_Albums_Folder
```
With this example, the script will connect to Synology Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder


### <span style="color:blue">Download Albums from Synology Photos:</span>
From version 2.3.0 onwards, the script can be executed in 'Download Albums from Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect to Synology Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder.  

To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3".  

You can also use wildcarts. i.e --synology-download-albums *Mery*

To extract ALL Albums within in Synology Photos database use 'ALL' as <ALBUMS_NAME>.  

The album(s) name <ALBUMS_NAME> can be passed using the Flag: _'-sda,  --synology-download-albums <ALBUMS_NAME>'_  

> [!IMPORTANT]
> <ALBUMS_NAME> should exist within your Synology Photos Albums database, otherwise it will no extract anything. 
> Extraction will be done in background task, so it could take time to complete. Even if the Script finish with success the extraction process could be still running on background, so take this into account.

Example of use:
```
./CloudPhotoMigrator.run --synology-download-albums "Album 1", "Album 2", "Album 3"
```
With this example, the script will connect to Synology Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Synology_Photos_Albums' folder



> [!NOTE]
> ## <span style="color:green">Immich Photos Support</span>
>From version 3.0.0 onwards, the script can connect to your Immich Photos account with your credentials or API. The credentials/API need to be loaded from 'Config.ini' file and will have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Immich Photos:</span>
>>
>>```
>># Configuration for Immich Photos
>>[Immich Photos]
>>IMMICH_URL                  = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>>IMMICH_API_KEY_ADMIN        = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>
>>IMMICH_API_KEY_USER_1       = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>IMMICH_USERNAME_1           = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
>>IMMICH_PASSWORD_1           = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
>>
>>IMMICH_API_KEY_USER_2       = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>IMMICH_USERNAME_2           = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
>>IMMICH_PASSWORD_2           = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
>>
>>IMMICH_FILTER_ARCHIVE       = False                                         # Optional: Used as Filter Criteria for Assets downloading (True/False)
>>IMMICH_FILTER_FROM          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>>IMMICH_FILTER_TO            = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>>IMMICH_FILTER_COUNTRY       = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: Spain)
>>IMMICH_FILTER_CITY          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Madrid', 'Málaga'])
>>IMMICH_FILTER_PERSON        = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Mery', 'James'])
>>```
>### Features included:
> - Upload Album(s)
> - Upload ALL (from folder)
> - Download Album(s)
> - Download ALL (into folder)
> - Remove ALL Assets
> - Remove ALL Albums
> - Remove Empty Albums
> - Remove Duplicates Albums
> - Remove Orphans Assets

### <span style="color:blue">Delete Empty Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Empty Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Empty Albums in Immich Photos database.  

If any Empty Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-remove-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Duplicates Albums in Immich Photos database.  

If any Duplicated Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-remove-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will upload all the assets contained in <INPUT_FOLDER> that are supported by Immich Photos.  

The folder <INPUT_FOLDER> can be passed using the Flag: _'-iuf,  --immich-upload-folder <INPUT_FOLDER>'_ 

> [!IMPORTANT]
> <INPUT_FOLDER> should be stored within your Immich Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <INPUT_FOLDER> should have been already indexed by Immich Photos before you can add them to a Immich Photos Album.  
>
>You can check if the files have been already indexed accessing Immich Photos mobile app or Immich Photos web portal and change to Folder View.  
>
>If you can't see your <INPUT_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Immich Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --immich-upload-folder ./MyLibrary
```
With this example, the script will connect to Immich Photos database and process the folder ./MyLibrary and will upload all supported assets found on it.


### <span style="color:blue">Upload Albums into Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Create Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Immich Photos and with the same Album name as Album folder.  

The folder <ALBUMS_FOLDER> can be passed using the Flag: _'-iua,  --immich-upload-albums <ALBUMS_FOLDER>'_ 

> [!IMPORTANT]
> <ALBUMS_FOLDER> should be stored within your Immich Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <ALBUMS_FOLDER> should have been already indexed by Immich Photos before you can add them to a Immich Photos Album.  
>
>You can check if the files have been already indexed accessing Immich Photos mobile app or Immich Photos web portal and change to Folder View.  
>
>If you can't see your <ALBUMS_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Immich Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --immich-upload-albums ./My_Albums_Folder
```
With this example, the script will connect to Immich Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Immich Photos, will create a new Album in Immich Photos with the same name of the Album Folder


### <span style="color:blue">Download Albums from Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Download Albums from Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect to Immich Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder.  

To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums "album1", "album2", "album3".  

You can also use wildcarts. i.e --immich-download-albums *Mery*

To extract ALL Albums within in Immich Photos database use 'ALL' as <ALBUMS_NAME>.  

The album(s) name <ALBUMS_NAME> can be passed using the Flag: _'-ida,  --immich-download-albums <ALBUMS_NAME>'_  

> [!IMPORTANT]
> <ALBUMS_NAME> should exist within your Immich Photos Albums database, otherwise it will no extract anything. 
> Extraction will be done in background task, so it could take time to complete. Even if the Script finish with success the extraction process could be still running on background, so take this into account.

Example of use:
```
./CloudPhotoMigrator.run --immich-download-albums "Album 1", "Album 2", "Album 3"
```
With this example, the script will connect to Immich Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Immich_Photos_Albums' folder




> [!NOTE]
> ## <span style="color:green">Other Standalone Features</span>
>Additionally, this script can be executed with 4 Standalone Extra Modes: 
> 
> - **Find Duplicates** (-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...])
> - **Process Duplicates** (-procDup, --process-duplicates <DUPLICATES_REVISED_CSV>)
> - **Fix Symbolic Links Broken** (-fixSym, --fix-symlinks-broken <FOLDER_TO_FIX>)
> - **Folder Rename Content Based** (-renFldcb, --rename-folders-content-based <ALBUMS_FOLDER>)
>
> If more than one Stand Alone Extra Mode is detected, only the first one will be executed




### <span style="color:blue">Extra Mode: Find Duplicates:</span>
From version 1.4.0 onwards, the script can be executed in 'Find Duplicates' Mode. In this mode, the script will find duplicates files in a smart way based on file size and content:
- In Find Duplicates Mode, your must provide a folder (or list of folders) using the flag '-fd, --find-duplicates', where the script will look for duplicates files. If you provide more than one folders, when a duplicated file is found, the script will maintains the file found within the folder given first in the list of folders provided. If the duplicated files are within the same folder given as an argument, the script will maintain the file whose name is shorter.
- For this mode, you can also provide an action to specify what to do with duplicates files found. You can include any of the valid actions with the flag '-fd, --find-duplicates'. Valid actions are: 'list', 'move' or 'remove'. If not action is detected, 'list' will be the default action.
  - If the duplicates action is 'list', then the script will only create a list of duplicated files found within the folder Duplicates. 
  - If the duplicates actio is 'move' then the script will maintain the main file and move the others inside the folder Duplicates/Duplicates_timestamp. 
  - Finally, If the duplicates action is 'remove' the script will maintain the main file and remove the others.


Example of use:
```
./CloudPhotoMigrator --find-duplicatess ./Albums ./ALL_PHOTOS move
```

With this example, the script will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicates, will keep the file within ./Albums folder (because it has been passed first on the list)
and will move the others duplicates files into the ./Duplicates folder on the root folder of the script.


### <span style="color:blue">Extra Mode: Process Duplicates:</span>
From version 1.6.0 onwards, the script can be executed in 'Process Duplicates' Mode. In this mode, the script will process the CSV generated during 'Find Duplicates' mode and will perform the Action given in column Action for each duplicated file.
- Included new flag '-pd, --process-duplicates' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode'. In that case, the script will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanently removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : Use this action to replace the principal file chosen for each duplicates and select manually the principal file
        - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
        - and Original Principal file detected by the Script will be removed permanently


Example of use:
```
./CloudPhotoMigrator --process-duplicates ./Duplicates/Duplicates_revised.csv
```

With this example, the script will process the file ./Duplicates/Duplicates_revised.csv
and for each duplicate, will do the given action according to Action column

### <span style="color:blue">Extra Mode: Fix Symbolic Links Broken:</span>

From version 1.5.0 onwards, the script can be executed in 'Fix Symbolic Links Broken' Mode. 
- You can use the flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' and provide a FOLDER_TO_FIX and the script will try to look for all symbolic links within FOLDER_TO_FIX and will try to find the target file within the same folder.
- This is useful when you run the main script using flag '-sa, --symbolic-albums' to create symbolic Albums instead of duplicate copies of the files contained on Albums.
- If you run the script with this flag and after that you rename original folders or change the folder structure of the OUTPUT_FOLDER, your symbolic links may be broken and you will need to use this feature to fix them.

Example of use:
```
./CloudPhotoMigrator --fix-symlinks-broken ./OUTPUT_FOLDER 
```
With this example, the script will look for all symbolic links within OUTPUT_FOLDER and if any is broken,
the script will try to fix it finding the target of the symlink within the same OUTPUT_FOLDER structure.


### <span style="color:blue">Extra Mode: Folder Rename Content Based:</span>
From version 2.0.0 onwards, the script can be executed in 'Rename Albums Folders' Mode. 

With this Extra Mode, you can rename all Albums subfolders (if they contain a flatten file structure) and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  

To define the <ALBUMS_FOLDER> you can use the new Flag: -ra, --rename-albums <ALBUMS_FOLDER>

Recommendation: Use this Extra Mode before to create Synology Photos Albums in order to have a clean Albums structure in your Synology Photos database.


Example of use:
```
./CloudPhotoMigrator.run ---rename-folders-content-based ./MyTakeout
```
In this example, the script will Process your Takeout or Library of photos in folder './MyTakeout' (need to be unzipped), 
and will rename all the subfolders found on to homogenize all the folder's name with the following template:
  - '**yyyy - Cleaned Subfolder Name**' or '**yyyy-yyyy - Cleaned Subfolder Name**'
  - where yyyy is the year of the assets found in that folder or yyyy-yyyy is the range of years for the assets found (if more than one year is found)
  - and Cleaned Subfolder Name just make the folder name cleaner.  

This step is useful if you want to Upload all your Albums to a new Cloud Service and you would like to start with all the new Albums in a cleaner homogeneus way.  



> [!TIP]
> ## <span style="color:dark">Additional Trick!</span>
> When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

I hope this can be useful for any of you.  
Enjoy it!

# ROADMAP:

## v3.1.0
### Release Date: (estimated)
  - Alpha version.   : 2025-03-14
  - Beta version     : 2025-03-21
  - Release Candidate: 2025-03-28
  - Official Release : 2025-03-31

### TODO:
- [x] Included Live Progress Dashboard in AUTOMATED MIGRATION MODE for a better visualization of the job progress.
- [x] Added new flag '**--dashboard=[true, false]**' (default=true) to show/hide Live Dashboard during Atomated Migration Job.
- [x] Completelly refactored AUTOMATED-MIGRATION MODE to allow parallel threads for Downloads and Uploads jobs avoiding downloading all assets before to upload them (this will save disk space and improve performance). Also objects support has been added to this mode for an easier implementation and future enhancements.
- [x] Support for 'Uploads Queue' to limit the max number of assets that the Downloader worker will store in the temporary folder to 100 (this save disk space). In this way the Downloader worker will never put more than 100 assets pending to Upload in the local folder.
- [x] Support Migration between 2 different accounts on the same Cloud Photo Service. 
- [x] Support to use Local Folders as SOURCE/TARGET during AUTOMATED-MIGRATION MODE. Now the selected local folder works equal to other supported cloud services.
- [x] Code Refactored to convert ServiceGooglePhotos, ServiceSynologyPhotos and ServiceImmichPhotos into Classes (ClassTakeoutFolder, ClassSynologyPhotos, ClassImmichPhotos) and homogenized all functions of all these classes.
- [x] Added new Class ClassLocalFolder with the same methods as other supported Cloud Services Classes to manage Local Folders in the same way as a Photo Cloud Service.
- [x] ClassTakeoutFolder inherits all methods from ClassLocalFolder and includes specific methods to process Google Takeouts since at the end Google Takeout is a local folder structure.
- [x] Updated GPTH version to cop latest changes in Google Takeouts. 
- [x] Minor Bug Fixing.

- [ ] Tests Pending:
  - [ ] Deep Test on Immich Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Synology Support functions. (volunteers are welcomed)
  - [ ] Deep Test on Google Takeout functions. (volunteers are welcomed)
  - [ ] Deep Test on Automated Migration Feature. (volunteers are welcomed)
  - [x] Deep Test on Live Dashboard Feature. (volunteers are welcomed)

### Live Dashboard Preview:
![Live Dashboard](https://github.com/jaimetur/CloudPhotoMigrator/blob/main/doc/screenshots/live_dashboard.jpg?raw=true)

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
- [ ] Allow Google Photos and Apple Photos as \<TARGET> in Automated Migration Process
- [ ] Add option to filter assets in all Immich Actions:
    - [ ] by Dates
    - [ ] by Country
    - [ ] by City
    - [ ] by Archive
    - [ ] by Person
- [ ] Update README.md
- [ ] Update RELEASES-NOTES.md

## Credits

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/TheLastGimbus/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)
