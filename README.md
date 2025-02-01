# CloudPhotoMigrator

Welcome to the powerful <span style="color:green">**CloudPhotoMigrator** </span>Tool:

This tool has been designed to Interact and Manage different Photo Cloud Services. As of today, the Supported Photo Cloud Services are:
- **Google Photos** (by means of Google Takeout Files)
- **Synology Photos**
- **Immich Photos**
- **Apple Photos** (is on the ROADMAP.md for next release)

Apart from Interact with the different Photo Cloud Services, the Tool also contains some other useful features such as:
- **Metadata fixing** of any Photo Library in your local drive
- **Lirary Organization** features:
  - Manage Duplicates assets
  - Splitting of assets with and without associated albums
  - Folder Structure (customizable) for 'Albums' and 'No Albums' folders
- **Symbolic Links Support** for Albums folders
  - Fix Symbolic Links Broken
- **Homogenize Albums folders name based on content**
- **Remove Empty Albums in Photo Cloud Services** 
- **Remove Duplicates Albums in Photo Cloud Services** 
- ...

## Download Latest Version:
Download the script either Linux, MacOS or Windows version (for both x64/amd64 or arm64 architectures) as you prefeer directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/raw/refs/heads/main/_built_versions/2.3.0/CloudPhotoMigrator_v3.0.0-alpha_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/raw/refs/heads/main/_built_versions/2.3.0/CloudPhotoMigrator_v3.0.0-alpha_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/raw/refs/heads/main/_built_versions/2.3.0/CloudPhotoMigrator_v3.0.0-alpha_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/raw/refs/heads/main/_built_versions/2.3.0/CloudPhotoMigrator_v3.0.0-alpha_macos_arm64.zip)  

**Windows:**  
- [Download AMD 64 bits version](https://github.com/jaimetur/CloudPhotoMigrator/raw/refs/heads/main/_built_versions/2.3.0/CloudPhotoMigrator_v3.0.0-alpha_windows_amd64.zip)  

## Instructions:
You can copy and unzip the downloaded Script into any local folder or to any Shared folder of our Synology NAS.

After that you have to download Takeout Zip's files from Google Takeout and paste the ZIP files onto the folder called '**Zip_files**' within the folder script which is the default folder to process Takeout ZIP files, or if you prefeer you can put them in any other subfolder and use the option _'-z, --zip-folder <folder_name>'_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call it depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**CloudPhotoMigrator.exe**'  


  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**CloudPhotoMigrator.run**'.  
    Minimum version required to run the script directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

## Syntax:
```
---------------------------------------------------------------------------------------------------------
usage: CloudPhotoMigrator.py [-h] [-v] [-nlog] [-i <INPUT_FOLDER>] [-o <OUTPUT_FOLDER>]
                                [-AUTO <SOURCE> <TARGET>]
                                [-gitf <TAKEOUT_FOLDER>] [-gofs <SUFIX>]
                                [-gafs ['flatten', 'year', 'year/month', 'year-month']]
                                [-gnas ['flatten', 'year', 'year/month', 'year-month']]
                                [-gcsa] [-gics] [-gmtf] [-grdf] [-gsef] [-gsma] [-gsgt]
                                [-sde] [-sdd] [-suf <INPUT_FOLDER>]
                                [-sua <ALBUMS_FOLDER>] [-suA <INPUT_FOLDER>]
                                [-sda <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                [-sdA <OUTPUT_FOLDER>] [-ide] [-idd]
                                [-iuf <INPUT_FOLDER>] [-iua <ALBUMS_FOLDER>]
                                [-iuA <INPUT_FOLDER>]
                                [-ida <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                [-idA <OUTPUT_FOLDER>]
                                [-fdup <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                                [-pdup <DUPLICATES_REVISED_CSV>]
                                [-fsym <FOLDER_TO_FIX>] [-frcb <ALBUMS_FOLDER>]

CloudPhotoMigrator v3.0.0-alpha - 2025-02-01

Script (based on GPTH Tool) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) 2024-2025 by Jaime Tur (@jaimetur)

options:

-h,    --help
         show this help message and exit
-v,    --version
         Show the script name, version, and date, then exit.
-nlog, --no-log-file
         Skip saving output messages to execution log file.
-i,    --input-folder <INPUT_FOLDER>
         Specify the input folder that you want to process.
-o,    --output-folder <OUTPUT_FOLDER>
         Specify the output folder to save the result of the processing action.
-AUTO, --AUTOMATED-MIGRATION ('<SOURCE>', '<TARGET>')
         This process will do an AUTOMATED-MIGRATION process to Download all your Assets
         (including Albums) from the <SOURCE> Cloud Service and Upload them to the
         <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE>
         Cloud Service.

         Posible values for:
             <SOURCE> : ['google-photos', 'synology-photos', 'immich-photos']
             <TARGET> : ['synology-photos', 'immich-photos']


EXTRA MODES: Google Photos Takeout Management:
----------------------------------------------
Following arguments allow you to interact with Google Photos Takeout Folder.
In this mode, you can use more than one optional arguments from the below list.
If only the argument -gtif, --google-takeout-input-folder <TAKEOUT_FOLDER> is detected,
then the script will use the default values for the rest of the arguments for this extra
mode.

-gitf, --google-input-takeout-folder <TAKEOUT_FOLDER>
         Specify the Takeout folder to process. If any Zip file is found inside it, the
         Zip will be extracted to the folder 'Unzipped_Takeout_TIMESTAMP', and will use
         the that folder as input <TAKEOUT_FOLDER>. Default: 'Takeout'.
-gofs, --google-output-folder-suffix <SUFIX>
         Specify the suffix for the output folder. Default: 'fixed'
-gafs, --google-albums-folders-structure ['flatten', 'year', 'year/month', 'year-month']
         Specify the type of folder structure for each Album folder (Default:
         'flatten').
-gnas, --google-no-albums-folder-structure ['flatten', 'year', 'year/month', 'year-month']
         Specify the type of folder structure for 'Others' folder (Default:
         'year/month').
-gcsa, --google-create-symbolic-albums
         Creates symbolic links for Albums instead of duplicate the files of each Album.
         (Useful to save disk space but may not be portable to other systems).
-gics, --google-ignore-check-structure
         Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-
         folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess
         timestamp from them.
-gmtf, --google-move-takeout-folder
         Move original assets to <OUTPUT_TAKEOUT_FOLDER>.
         CAUTION: Useful to avoid disk space duplication and improve execution speed,
         but you will lost your original unzipped files!!!.
         Use only if you keep the original zipped files or you have disk space
         limitations and you don't mind to lost your original unzipped files.
-grdf, --google-remove-duplicates-files
         Remove Duplicates files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.
-gsef, --google-skip-extras-files
         Skip processing extra photos such as  -edited, -effects photos.
-gsma, --google-skip-move-albums
         Skip moving albums to 'Albums' folder.
-gsgt, --google-skip-gpth-tool
         Skip processing files with GPTH Tool.
         CAUTION: This option is NOT RECOMMENDED because this is the Core of the Google
         Photos Takeout Process. Use this flag only for testing purposses.


EXTRA MODES: Synology Photos Takeout Management:
------------------------------------------------
Following arguments allow you to interact with Synology Photos.
If more than one optional arguments are detected, only the first one will be executed.

-sde,  --synology-delete-empty-albums
         The script will look for all Albums in Synology Photos database and if any
         Album is empty, will remove it from Synology Photos database.
-sdd,  --synology-delete-duplicates-albums
         The script will look for all Albums in Synology Photos database and if any
         Album is duplicated, will remove it from Synology Photos database.
-suf,  --synology-upload-folder <INPUT_FOLDER>
         The script will look for all Photos/Videos within <INPUT_FOLDER> and will
         upload them into Synology Photos.
-sua,  --synology-upload-albums <ALBUMS_FOLDER>
         The script will look for all Albums within <ALBUMS_FOLDER> and will create one
         Album per folder into Synology Photos.
-suA,  --synology-upload-ALL <INPUT_FOLDER>
         The script will look for all Assets within <INPUT_FOLDER> and will upload them
         into Synology Photos.
         - If the <INPUT_FOLDER> contains a Subfolder called 'Albums' then, all assets
         inside each subfolder of Albums willl be associated to a new Album in Synology
         Photos with the same name as the subfolder
-sda,  --synology-download-albums <ALBUMS_NAME>
         The Script will connect to Synology Photos and download the Album whose name is
         <ALBUMS_NAME> to the folder 'Download_Synology' within the Synology Photos root
         folder.
         - To extract all albums mathing any pattern you can use patterns in
         ALBUMS_NAME, i.e: --synology-download-albums 'dron*' to download all albums
         starting with the word 'dron' followed by other(s) words.
         - To download several albums you can separate their names by comma or space and
         put the name between double quotes. i.e: --synology-download-albums 'album1',
         'album2', 'album3'.
         - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
-sdA,  --synology-download-ALL <OUTPUT_FOLDER>
         The Script will connect to Synology Photos and will download all the Album and
         Assets without Albums into the folder <OUTPUT_FOLDER>.
         - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/
         with the same name of the Album and all files will be flattened into it.
         - Assets with no Albums associated will be downloaded withn a subfolder called
         <OUTPUT_FOLDER>/Others/ and will have a year/month structure inside.


EXTRA MODES: Immich Photos Takeout Management:
----------------------------------------------
Following arguments allow you to interact with Immich Photos.
If more than one optional arguments are detected, only the first one will be executed.

-ide,  --immich-delete-empty-albums
         The script will look for all Albums in Immich Photos database and if any Album
         is empty, will remove it from Immich Photos database.
-idd,  --immich-delete-duplicates-albums
         The script will look for all Albums in Immich Photos database and if any Album
         is duplicated, will remove it from Immich Photos database.
-iuf,  --immich-upload-folder <INPUT_FOLDER>
         The script will look for all Photos/Videos within <INPUT_FOLDER> and will
         upload them into Immich Photos.
-iua,  --immich-upload-albums <ALBUMS_FOLDER>
         The script will look for all Albums within <ALBUMS_FOLDER> and will create one
         Album per folder into Immich Photos.
-iuA,  --immich-upload-ALL <INPUT_FOLDER>
         The script will look for all Assets within <INPUT_FOLDER> and will upload them
         into Immich Photos.
         - If the <INPUT_FOLDER> contains a Subfolder called 'Albums' then, all assets
         inside each subfolder of Albums willl be associated to a new Album in Synology
         Photos with the same name as the subfolder
-ida,  --immich-download-albums <ALBUMS_NAME>
         The Script will connect to Immich Photos and download the Album whose name is
         <ALBUMS_NAME> to the folder 'Download_Immich' within the script execution
         folder.
         - To extract all albums mathing any pattern you can use patterns in
         ALBUMS_NAME, i.e: --immich-download-albums 'dron*' to download all albums
         starting with the word 'dron' followed by other(s) words.
         - To download several albums you can separate their names by comma or space and
         put the name between double quotes. i.e: --immich-download-albums 'album1',
         'album2', 'album3'.
         - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
-idA,  --immich-download-ALL <OUTPUT_FOLDER>
         The Script will connect to Immich Photos and will download all the Album and
         Assets without Albums into the folder <OUTPUT_FOLDER>.
         - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/
         with the same name of the Album and all files will be flattened into it.
         - Assets with no Albums associated will be downloaded withn a subfolder called
         <OUTPUT_FOLDER>/Others/ and will have a year/month structure inside.


OTHER STAND-ALONE EXTRA MODES:
------------------------------
Following arguments can be used to execute the Script in any of the usefull additionals
Extra Modes included.
If more than one Extra Mode is detected, only the first one will be executed.

-fdup, --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
         Find duplicates in specified folders.
         <ACTION> defines the action to take on duplicates ('move', 'delete' or 'list').
         Default: 'list'
         <DUPLICATES_FOLDER> are one or more folders (string or list), where the script
         will look for duplicates files. The order of this list is important to
         determine the principal file of a duplicates set. First folder will have higher
         priority.
-pdup, --process-duplicates <DUPLICATES_REVISED_CSV>
         Specify the Duplicates CSV file revised with specifics Actions in Action
         column, and the script will execute that Action for each duplicates found in
         CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.
-fsym, --fix-symlinks-broken <FOLDER_TO_FIX>
         The script will try to fix all symbolic links for Albums in <FOLDER_TO_FIX>
         folder (Useful if you have move any folder from the OUTPUT_TAKEOUT_FOLDER and
         some Albums seems to be empty.
-frcb, --folders-rename-content-based <ALBUMS_FOLDER>
         Usefull to rename and homogenize all Albums folders found in <ALBUMS_FOLDER> 
         based on the date content found.
---------------------------------------------------------------------------------------------------------
```
Example of use:
> [!NOTE]  
> - **Example 1**:
>> ```
>> ./CloudPhotoMigrator.run --google-input-takeout-folder ./MyTakeout --google-remove-duplicates-files
>> ```
> 
>> In this example, the script will Process you Takeout Files found in folder './MyTakeout' (Unzipping them if needed) and fix
>> all files found to set the correct date and time, and identifying wich assets belongs to each Album created on Google Photos. 
>>   - After that, the script will create a folder structure based on year/month for the folder '<OUTPUT_TAKEOUT_FOLDER>/Others' (by default).  
>>   - Also, the script will create a flatten folder structure for each Album subfolder found in '<OUTPUT_TAKEOUT_FOLDER>/Albums.'  
>>   - Finally, the output files will be placed into './MyTakeout_fixed_timestamp' folder whre timestamp is the timestamp of the execution.


> [!NOTE]  
> - **Example 2**:
>> ```
>>./CloudPhotoMigrator.run --folders-rename-content-based ./MyTakeout
>>```
>
>>In this example, the script will Process your Takeout or Library of photos in folder './MyTakeout' (need to be unzipped) and will rename
>>all the subfolders found on to homogenize all the folder's name with the following template:
>>  - '**yyyy - Cleaned Subfolder Name**' or '**yyyy-yyyy - Cleaned Subfolder Name**'
>>    - where yyyy is the year of the assets found in that folder or yyyy-yyyy is the range of years for the assets found (if more than one year is found)
>>    - and Cleaned Subfolder Name just make the folder name cleaner.  
>    
>>This step is useful if you want to Upload all your Albums to a new Cloud Service and you would like to start with all the new Albums in a cleaner and
>>homogeneus way.



## <span style="color:green">Extra Mode: AUTOMATED-MIGRATION:</span>
From version 3.3.0 onwards, the script can be executed in  a FULLY-AUTOMATED MIGRATION Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will automatically do the whole migration jon from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.
>>The script will do a FULLY-AUTOMATED job which has two steps:  
>>  - First, the script will Download all your assets from \<SOURCE> Cloud Service (if you have configured properly the Config.ini file), or process the \<SOURCE> folder in case that you specify a path.
>>    - In this step, the output will be a \<OUTPUT_FOLDER> containing two subfolders:
>>      - 'Albums': Contains all the assets associated to some Album(s) within your \<SOURCE> Cloud Service
>>      - 'Others': Contains all the assets with no Album(s) assciated within your \<SOURCE> Cloud Service
>>  - Second, the script will connect to yourto \<TARGET> Cloud Service (if you have configured properly the Config.ini file) and will 
>>    upload all the assets processed in previous step, creating a new Album per each Album found in your \<SOURCE> Cloud Service (or \<SOURCE> folder if you specifyy a path), 
>>    and will associate all the assets included in each Album in the same way that you had on your \<SOURCE> Cloud Service.

To execute this Extra Mode, you can use the new Flag: '-AUTO, --AUTOMATED-MIGRATION \<SOURCE> \<TARGET>'


Example of use:
> [!NOTE]  
> - **Example 1:**
>> ```
>> ./CloudPhotoMigrator.run --AUTOMATED-MIGRATION ./MyTakeout synology-photos
>>```
>
>>In this example, the script will do a FULLY-AUTOMATED job which has two steps:  
>>  - First, the script will process the folder './MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
>>    correct date and time, and identifying wich assets belongs to each Album created on Google Photos. 
>>  - Second, the script will connect to your Synology Photos account (if you have configured properly the Config.ini file) and will 
>>    upload all the assets processed in previous step, creating a new Album per each Album found in your Takeout files and associating
>>    all the assets included in each Album in the same way that you had on your Google Photos account.


> [!NOTE]  
> - **Example 2**:
>> ```
>>./CloudPhotoMigrator.run --AUTOMATED-MIGRATION synology-photos immich-photos
>>```
>
>>Withh this example, the script will do a FULLY-AUTOMATED job which has two steps:  
>>  - First, the script will process connect to your Synology Photos account (if you have configured properly the Config.ini file) and will 
>>    download all the assets found in your account (sepparating those associated to som Album(s), of those without any Album associated).
>>  - Second, the script will connect to your Immich Photos account (if you have configured properly the Config.ini file) and will 
>>    upload all the assets processed in previous step, creating a new Album per each Album found in your Synology Photos and associating
>>    all the assets included in each Album in the same way that you had on your Synology Photos account.

> [!NOTE]
> ## <span style="color:green">Google Photos Takeout Support</span>
>The script can process your Google Takeout files to fix timestamp, geodata, organize files per year/month, organize assets within album(s) in subfolders, etc...
>
>>#### <span style="color:green">Example 'Config.ini' for Synology Photos:</span>
>>
>>```
>># Configuration for Google Photos
>>[Google Photos]
>>```
For the time being, Google Photos Takeout support, does not need to include anything in the Config.ini, but it has it own section for futures features.

### <span style="color:blue">Google Takeout Mode: Process Explained:</span>

The whole process will do the next actions if all flags are false (by default):

1. Unzip all the Takeout Zips from the <INPUT_TAKEOUT_FOLDER> into a subfolder named './Unzipped_Takeout_{TIMESTAMP}' (by default). This step will be skipped if you already have your Takeout folder unziped.
   
2. Pre-Process <INPUT_TAKEOUT_FOLDER> unzipped to delete '@eaDir' subfolders (Synology metadata subfolders with miniatures) and to Fix .MP4 files extracted from Live pictures and with no .json file associated.

3. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder (This step can be skipped using flag _'gsgt, --google-skip-gpth-tool_').
  
4. Sync Timestamps of .MP4 files generated by Google Photos with Live Picture files (.heic, .jpg, .jpeg) if both files have the same name and are in the same folder

5. Create Date Folder structure ('flatten', 'year', 'year/month', 'year-month') to Albums and No Albums folders according to the options given by arguments:
   - _'-gafs, --google-albums-folders-structure'_ <'flatten', 'year', 'year/month', 'year-month'>. Applies to each Album folder. Default is ‘flatten’ for Albums
   - _'gnas, --google-no-albums-folder-structure'_ <'flatten', 'year', 'year/month', 'year-month'> Applies to ALL_PHOTOS folder (Photos without any Albums). Default is ‘year/month’ for No-Albums. 

6. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to '<OUTPUT_FOLDER>/Others' folder. This step can be skipped using flag _'-gsma, --google-skip-move-albums'_

7. Finally, the script will look in <OUTPUT_TAKEOUT_FOLDER> for any symbolic link broken and will try to fix it by looking for the original file where the symlink is pointing to.

8. (Optional) In this step, the script will look for any duplicate file on OUTPUT_FOLDER (ignoring symbolic links), and will remove all duplicates keeping only the principal file (giving more priority to duplicates files found into any album folder than those found on 'ALL_PHOTOS' folder. 


The result will be a folder (NAMED '<INPUT_TAKEOUT_FOLDER>_{SUFIX}_{TIMESTAMP}' by default, but you can or change the default suffix _'fixed'_ by any other using the option _'-gofs, --google-output-folder-suffix <SUFIX>'_) 
The final OUTPUT_FOLDER will include:
- 'Albums' subfolder with all the Albums without year/month structure (by default).
- 'Others' subfolder with all the photos with year/month structure (by default).

Finally, if you want to use your processed assets within Synology Photos, you just need to move OUTPUT_FOLDER into your /home/Photos folder and let Synology index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (408559 files zipped, 168168 photos/video files, 740 albums) and moved it into Synology Photos.  

The whole process took around **~8.5 hours** (or **~3 hours without last two optional steps) and this is the time split per steps**):
1. Extraction process --> 25m
2. Pre-processing Takeout_folder --> 3m 50s
3. GPTH Tool fixing --> 2h 12m
4. Sync .MP$ timestamps --> 10s
5. Create Date Folder Structure --> 50s
6. Moving Album Folder --> 1s
7. Fix Broken Symlinks --> 10m
8. <span style="color:grey">(Optional) Remove Duplicates after fixing --> 3h</span>
   
NOTE: Step 8 is disabled by default, and is only recommended if you want to save disk space and want to avoid having the same physical file in more than one folder (in case that the same file belongs to multiples Albums).

> [!NOTE]
> ## <span style="color:green">Synology Photos Support</span>
>From version 2.0.0 onwards, the script can connect to your Synology NAS and login into Synology Photos App with your credentials. The credentials need to be loaded from 'Config.ini' file and will have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Synology Photos:</span>
>>
>>```
>># Configuration for Synology Photos
>>[Synology Photos]
>>SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>>SYNOLOGY_USERNAME           = username                                      # Your username for Synology Photos
>>SYNOLOGY_PASSWORD           = password                                      # Your password for Synology Photos
>>SYNOLOGY_ROOT_PHOTOS_PATH   = /volume1/homes/your_username/Photos           # Your root path to Synology Photos main folder. Tipically is /volume1/homes/your_username/Photos
>>```

### <span style="color:blue">Delete Empty Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Empty Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Empty Albums in Synology Photos database.  

If any Empty Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-delete-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Duplicates Albums in Synology Photos database.  

If any Duplicated Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-delete-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Synology Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will upload all the asseets contained in <INPUT_FOLDER> that are supported by Synology Photos.  

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
>From version 3.0.0 onwards, the script can connect to your Immich NAS and login into Immich Photos App with your credentials. The credentials need to be loaded from 'Config.ini' file and will have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Immich Photos:</span>
>>
>>```
>># Configuration for Immich Photos
>>[Immich Photos]
>>IMMICH_URL                = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>>IMMICH_USERNAME           = username                                      # Your username for Immich Photos
>>IMMICH_PASSWORD           = password                                      # Your password for Immich Photos
>>```

### <span style="color:blue">Delete Empty Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Empty Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Empty Albums in Immich Photos database.  

If any Empty Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-delete-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Duplicates Albums in Immich Photos database.  

If any Duplicated Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-delete-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will upload all the asseets contained in <INPUT_FOLDER> that are supported by Immich Photos.  

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
> ## <span style="color:green">ADDITIONAL STANDALONE EXTRA MODES</span>
>Additionally, this script can be executed with 4 Standalone Extra Modes: 
> 
> - **Find Duplicates** (-fdup, --find-duplicates <ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...])
> - **Process Duplicates** (-pdup, --process-duplicates <DUPLICATES_REVISED_CSV>)
> - **Fix Symbolic Links Broken** (-fsym, --fix-symlinks-broken <FOLDER_TO_FIX>)
> - **Folder Rename Content Based** (-frcb, --folders-rename-content-based <ALBUMS_FOLDER>)
>
> If more than one Stand Alone Extra Mode is detected, only the first one will be executed




### <span style="color:blue">Extra Mode: Find Duplicates:</span>
From version 1.4.0 onwards, the script can be executed in 'Find Duplicates' Mode. In this mode, the script will find duplicates files in a smart way based on file size and content:
- In Find Duplicates Mode, yout must provide a folder (or list of foldders) using the flag '-fd, --find-duplicates', wherre the script will look for duplicates files. If you provide more than one folders, when a duplicated file is found, the script will mainains the file found within the folder given first in the list of folders provided. If the duplicaded files are within the same folder given as an argument, the script will maitain the file whose name is shorter.
- For this mode, you can also provide an action to specify what to do with duplicates files found. You can include any of the valid actions with the flag '-fd, --find-duplicates'. Valid actions are: 'list', 'move' or 'remove'. If not action is detected, 'list' will be the default action.
  - If the duplicates action is 'list', then the script will only create a list of duplicaed files found within the folder Duplicates. 
  - If the duplicates actio is 'move' then the script will maintain the main file and move the others inside the folder Duplicates/Duplicates_timestamp. 
  - Finally, If the duplicates action is 'remove' the script will maintain the main file and remove the others.


Example of use:
```
./CloudPhotoMigrator --find-duplicatess ./Albums ./ALL_PHOTOS move
```

With this example, the script will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicates, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the script.


### <span style="color:blue">Extra Mode: Process Duplicates:</span>
From version 1.6.0 onwards, the script can be executed in 'Process Duplicates' Mode. In this mode, the script will process the CSV generated during 'Find Duplicates' mode and will perform the Action given in column Action for each duplicated file.
- Included new flag '-pd, --process-duplicates' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode'. In that case, the script will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
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

With this Extra Mode, you can rename all Albums subfolders (if they contains a flatten file structure) and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  

To define the <ALBUMS_FOLDER> you can use the new Flag: -ra, --rename-albums <ALBUMS_FOLDER>

Recommendation: Use this Extra Mode before to create Synology Photos Albums in order to have a clean Albums structure in your Synology Photos database.


Example of use:
```
./CloudPhotoMigrator.run ---folders-rename-content-based ./My_Albums_Folder
```
With this example, the script will rename all subfolders within ./My_Albums_Folder (only first subfolder level) according to the format described above. If the subfolder does not contain any file, the folder will not be renamed.


> [!TIP]
> ## <span style="color:dark">Additional Trick!</span>
> When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

I hope this can be useful for any of you.  
Enjoy it!

## Credits

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
Part of this Tool is based on [GPTH Tool](https://github.com/TheLastGimbus/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)
