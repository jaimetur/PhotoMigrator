# OrganizeTakeoutPhotos
Script (based on GPTH Tool) to Process Google Takeout Photos (Fix metadata, Identify Live Pictures, Organize per year/month folders, separate Albums, Fix Symbolic Links, Find Duplicates, Manage Duplicates, Homogenize Albums folders name, Import Albums to Synology Photos, Delete Empty Synology Photos Albums and much more)

## Download Script:
Download the script either Linux, MacOS or Windows version (for both x64/amd64 or arm64 architectures) as you prefeer directly from following links:

**Linux:**:  
  - [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_linux_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_linux_arm64.zip)  

**Mac OS:**
  - [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_macos_amd64.zip)  
  - [Download ARM 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_macos_arm64.zip)  

**Windows:**  
- [Download AMD 64 bits version](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/_built_versions/2.3.0/OrganizeTakeoutPhotos_v2.3.0_windows_amd64.zip)  

## Instructions:
You can copy and unzip the downloaded Script into any local folder or to any Shared folder of our Synology NAS.

After that you have to download Takeout Zip's files from Google Takeout and paste the ZIP files onto the folder called '**Zip_files**' within the folder script which is the default folder to process Takeout ZIP files, or if you prefeer you can put them in any other subfolder and use the option _'-z, --zip-folder <folder_name>'_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call it depending on your environment:
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**OrganizeTakeoutPhotos.exe**'  


  - If you run it from Synology NAS (using SSH terminal) or from Linux/Mac, you have to call the master script '**OrganizeTakeoutPhotos.run**'.  
    Minimum version required to run the script directly from your Synology NAS (using SSH terminal) is **DSM 7.0**.

## Syntax:
```
----------------------------------------------------------------------------------------------------------------------------
usage: OrganizeTakeoutPhotos.run/exe [-h] [-v] [-z <ZIP_FOLDER>] [-t <TAKEOUT_FOLDER>] [-s <SUFIX>]
                                     [-as ['flatten', 'year', 'year/month', 'year-month']]
                                     [-ns ['flatten', 'year', 'year/month', 'year-month']]
                                     [-sg] [-se] [-sm] [-sa] [-it] [-mt] [-rd] [-nl]
                                     [-fs <FOLDER_TO_FIX>] [-ra <ALBUMS_FOLDER>]
                                     [-fd ['list', 'move', 'remove'] <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER>...]]
                                     [-pd <DUPLICATES_REVISED_CSV>] [-ea <ALBUMS_NAME> [<ALBUMS_NAME> ...]]
                                     [-ca <ALBUMS_FOLDER>] [-de] [-dd] [-ao <INPUT_FOLDER>]

OrganizeTakeoutPhotos v2.3.0 - 2025-01-13

Script (based on GPTH Tool) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) by Jaime Tur (@jaimetur)

options:

-h,   --help
        show this help message and exit
-v,   --version
        Show the script name, version, and date, then exit.
-z,   --zip-folder <ZIP_FOLDER>
        Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files
        will be skipped.
-t,   --takeout-folder <TAKEOUT_FOLDER>
        Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to
        unzip input files. Default: 'Takeout'.
-s,   --suffix <SUFIX>
        Specify the suffix for the output folder. Default: 'fixed'
-as,  --albums-structure ['flatten', 'year', 'year/month', 'year-month']
        Specify the type of folder structure for each Album folder (Default: 'flatten').
-ns,  --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']
        Specify the type of folder structure for ALL_PHOTOS folder (Default: 'year/month').
-sg,  --skip-gpth-tool
        Skip processing files with GPTH Tool. NOT RECOMMENDED!!! because this is the Core of the Script. Use
        this flag only for testing purposses.
-se,  --skip-extras
        Skip processing extra photos such as  -edited, -effects photos.
-sm,  --skip-move-albums
        Skip moving albums to Albums folder.
-sa,  --symbolic-albums
        Creates symbolic links for Albums instead of duplicate the files of each Album. (Useful to save disk
        space but may not be portable to other systems).
-it,  --ignore-takeout-structure
        Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files
        found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
-mt,  --move-takeout-folder
        Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>.
        CAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your
        original unzipped files!!!. Use only if you keep the original zipped files or you have disk space
        limitations and you don't mind to lost your original unzipped files.
-rd,  --remove-duplicates-after-fixing
        Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.
-nl,  --no-log-file
        Skip saving output messages to execution log file.

EXTRA MODES:
------------
Following optional arguments can be used to execute the Script in any of the usefull additionals Extra Modes
included. When an Extra Mode is detected only this module will be executed (ignoring the normal steps).
If more than one Extra Mode is detected, only the first one will be executed.

-fs,  --fix-symlinks-broken <FOLDER_TO_FIX>
        Force Mode: 'Fix Symbolic Links Broken'. The script will try to fix all symbolic links for Albums in
        <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_FOLDER and some Albums
        seems to be empty.
-ra,  --rename-albums-folders <ALBUMS_FOLDER>
        Force Mode: 'Rename Albums'. Rename all Albums folders found in <ALBUMS_FOLDER> to unificate the
        format.
-fd,  --find-duplicates ['list', 'move', 'remove'] <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]
        Force Mode: 'Find Duplicates'. Find duplicates in specified folders. The first argument is the action
        to take on duplicates ('move', 'delete' or 'list'). Default: 'list' The remaining arguments are one or
        more folders (string or list). where the script will look for duplicates files. The order of this list
        is important to determine the principal file of a duplicates set. First folder will have higher
        priority.
-pd,  --process-duplicates-revised <DUPLICATES_REVISED_CSV>
        Force Mode: 'Process Duplicates Revised'. Specify the Duplicates CSV file revised with specifics
        Actions in Action column, and the script will execute that Action for each duplicates found in CSV.
        Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.
-ea,  --extract-albums-synology-photos <ALBUMS_NAME>
        Force Mode: 'Extract  Album(s) Synology Photos'. The Script will connect to Synology Photos and
        extract the Album whose name is <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the
        Synology Photos root folder.
-ca,  --create-albums-synology-photos <ALBUMS_FOLDER>
        force Mode: 'Create Albums in Synology Photos'. The script will look for all Albums within
        ALBUM_FOLDER and will create one Album per folder into Synology Photos.
-de,  --delete-empty-albums-synology-photos
        Force Mode: 'Delete Empty Albums in Synology Photos'. The script will look for all Albums in Synology
        Photos database and if any Album is empty, will remove it from Synology Photos database.
-dd,  --delete-duplicates-albums-synology-photos
        Force Mode: 'Delete Duplicates Albums in Synology Photos'. The script will look for all Albums in
        Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.
-ao,  --all-in-one <INPUT_FOLDER>
        Force Mode: 'All-in-One'. The Script will do the whole process (Zip extraction, Takeout Processing,
        Remove Duplicates, Synology Photos Albums creation) in just One shot.
----------------------------------------------------------------------------------------------------------------------------
```

Example of use:
```
./OrganizeTakeoutPhotos --zip-folder ./Zips --takeout-folder ./Takeout --remove-duplicates-after-fixing
```

Withh this example, the script will unzip all zip files found under ./Zips folder into ./Takeout folder.  
Then will process ./Takeout folder to fix all files found and set the correct date and time.  
Finally the script will create a folder structure based on year/month for OUTPUT_FOLDER/ALL_PHOTOS folder (by default).  
Also, the script will create a flatten folder structure for each Album subfolder found in OUTPUT_FOLDER/Albums.  
The output files will be placed into ./Takeout_fixed_timestamp folder whre timestamp is the timestamp of the execution.


## <span style="color:blue">Normal Mode: Process Explained:</span>

The whole process will do the next actions if all flags are false (by default):

1. Unzip all the Takeout Zips from default zip folder "Zip_files" (you can modify the Zip_folder with the option _'-z, --zip-folder <folder_name>'_) into a subfolder named Takeout (by default) or any other folder if you specify it with the option _'-t, --takeout-folder <folder_name>'_. This step can be skipped if you ommit _'-z, --zip-folder <folder_name>'_ argument (useful in case that you already have unzip all the files manually).
   
2. Pre-Process TAKEOUT_FOLDER to delete '@eaDir' subfolders (Synology metadata subfolders with miniatures) and to Fix .MP4 files extracted from Live pictures and with no .json file associated.

3. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder (This step can be skipped using flag _'-sg, --skip-gpth-tool_').
  
4. Sync Timestamps of .MP4 files generated by Google Photos with Live Picture files (.heic, .jpg, .jpeg) if both files have the same name and are in the same folder

5. Create Date Folder structure ('flatten', 'year', 'year/month', 'year-month') to Albums and No Albums folders according with the options given by arguments:
   - _'-as, --albums-structure'_ <'flatten', 'year', 'year/month', 'year-month'>. Applies to each Album folder. Default is ‘flatten’ for Albums
   - _'-ns, --no-albums-structure'_ <'flatten', 'year', 'year/month', 'year-month'> Applies to ALL_PHOTOS folder (Photos without any Albums). Default is ‘year/month’ for No-Albums. 

6. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to ALL_PHOTOS folder. This step can be skipped using flag _'-sm, --skip-move-albums'_

7. Finally the script will look in OUTPUT_FOLDER for any symbolic link broken and will try to fix it by looking for the original file where the symlink is pointing to.

8. (Optional) In this step, the script will look for any duplicate file on OUTPUT_FOLDER (ignoring symbolic links), and will remove all duplicates keeping only the principal file (giving more priority to duplicates files found into any album folder than those found on 'ALL_PHOTOS' folder. 


The result will be a folder (called Takeout_fixed_{timestamp} by default, but you can specify any other with the option _'-t, --takeout-folder <folder_name>'_ or change the default suffix _'fixed'_ by any other using the option _'-s, --suffix <desired_suffix>'_) which will contains:

- ALL_PHOTOS subfolder with all the photos with year/month structure (by default).
- Albums subfolder with all the Albums without year/month structure (by default).

Finally you just need to move the output folder (Takeout_fixed_{timestamp} by default) into your /home/Photos folder and let Synology to index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

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

## <span style="color:blue">EXTRA MODES:</span>

Additionally, this script can be executed with 9 Extra Modes:

### <span style="color:blue">Extra Mode: Fix Symbolic Links Broken:</span>

From version 1.5.0 onwards, the script can be executed in 'Fix Symbolic Links Broken' Mode. 
- You can use the flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' and provide a FOLDER_TO_FIX and the script will try to look for all symbolic links within FOLDER_TO_FIX and will try to find the target file within the same folder.
- This is useful when you run the main script using flag '-sa, --symbolic-albums' to create symbolic Albums instead of duplicate copies of the files contained on Albums.
- If you run the script with this flag and after that you rename original folders or change the folder structure of the OUTPUT_FOLDER, your symbolic links may be broken and you will need to use this feature to fix them.


Example of use:
```
./OrganizeTakeoutPhotos --fix-symlinks-broken ./OUTPUT_FOLDER 
```
With this example, the script will look for all symbolic links within OUTPUT_FOLDER and if any is broken,
the script will try to fix it finding the target of the symlink within the same OUTPUT_FOLDER structure.


### <span style="color:blue">Extra Mode: Find Duplicates:</span>
From version 1.4.0 onwards, the script can be executed in 'Find Duplicates' Mode. In this mode, the script will find duplicates files in a smart way based on file size and content:
- In Find Duplicates Mode, yout must provide a folder (or list of foldders) using the flag '-fd, --find-duplicates', wherre the script will look for duplicates files. If you provide more than one folders, when a duplicated file is found, the script will mainains the file found within the folder given first in the list of folders provided. If the duplicaded files are within the same folder given as an argument, the script will maitain the file whose name is shorter.
- For this mode, you can also provide an action to specify what to do with duplicates files found. You can include any of the valid actions with the flag '-fd, --find-duplicates'. Valid actions are: 'list', 'move' or 'remove'. If not action is detected, 'list' will be the default action.
  - If the duplicates action is 'list', then the script will only create a list of duplicaed files found within the folder Duplicates. 
  - If the duplicates actio is 'move' then the script will maintain the main file and move the others inside the folder Duplicates/Duplicates_timestamp. 
  - Finally, If the duplicates action is 'remove' the script will maintain the main file and remove the others.


Example of use:
```
./OrganizeTakeoutPhotos --find-duplicatess ./Albums ./ALL_PHOTOS move
```

With this example, the script will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicates, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the script.


### <span style="color:blue">Extra Mode: Process Duplicates:</span>
From version 1.6.0 onwards, the script can be executed in 'Process Duplicates' Mode. In this mode, the script will process the CSV generated during 'Find Duplicates' mode and will perform the Action given in column Action for each duplicated file.
- Included new flag '-pd, --process-duplicates-revised' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode'. In that case, the script will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : Use this action to replace the principal file chosen for each duplicates and select manually the principal file
        - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
        - and Original Principal file detected by the Script will be removed permanently


Example of use:
```
./OrganizeTakeoutPhotos --process-duplicates-revised ./Duplicates/Duplicates_revised.csv
```

With this example, the script will process the file ./Duplicates/Duplicates_revised.csv
and for each duplicate, will do the given action according with Action column

### <span style="color:blue">Extra Mode: Rename Albums Folders Mode:</span>
With this Extra Mode, you can rename all Albums subfolders (if they contains a flatten file structure) and homogenize all your Albums names with this format: 'yyyy - Album Name' or 'yyyy-yyyy - Album Name', where yyyy is the year of the files contained in each Album folder (if more than one year is found, then yyyy-yyyy will indicate the range of years for the files contained in the Album folder.)  

To define the <ALBUMS_FOLDER> you can use the new Flag: -ra, --rename-albums <ALBUMS_FOLDER>

Recommendation: Use this Extra Mode before to create Synology Photos Albums in order to have a clean Albums structure in your Synology Photos database.


Example of use:
```
./OrganizeTakeoutPhotos.run --rename-albums ./My_Albums_Folder
```
With this example, the script will rename all subfolders within ./My_Albums_Folder (only first subfolder level) according to the format described above. If the subfolder does not contains any file, the folder will not be renamed.

> [!NOTE]
> ## <span style="color:green">Synology Photos Support</span>
>From version 2.0.0 onwards, the script can connect to your Synology NAS and login into Synology Photos App with your credentials. The credentials need to be loaded from 'Synology.config' file and will have this format:
>
>#### <span style="color:green">Example 'Synology.config':</span>
>
>```
># Synology.config for Synology NAS
>
>NAS_IP              = 192.168.1.11                          # Change this IP by your Synology NAS IP
>USERNAME            = username                              # Your username for Synology Photos
>PASSWORD            = password                              # Your password for Synology Photos
>ROOT_PHOTOS_PATH    = /volume1/homes/your_username/Photos   # Your root path to Synology Photos main folder. Tipically is /volume1/homes/your_username/Photos
>```


## <span style="color:green">Extra Mode: All in One Shot:</span>
From version 2.1.0 onwards, the script can be executed in 'All in One Shot' Mode. 

If you configure properly the file 'Synology.config' and execute this Extra Mode, the script will process your Takeout Zip files, will process them, and will connect automatically to your Synology Photos database to import all your Photos & Videos automatically to Synology Photos database creating the same Albums that you have exported in your Takeout files.  

To execute this Extra Mode, you can use the new Flag: -ao, --all-in-one  


Example of use:
```
./OrganizeTakeoutPhotos.run --all-in-one ./Zip_files
```
With this example, the script will extract all your Takeout Zip files from ./Zip_files folder, will process them, and finally will connect to Synology Photos database to create all Albums found and import all the other photos without any Albums associated.

### <span style="color:blue">Extra Mode: Extract Albums from Synology Photos:</span>
From version 2.3.0 onwards, the script can be executed in 'Extract Albums from Synology Photos' Mode. 

If you configure properly the file 'Synology.config' and execute this Extra Mode, the script will connect to Synology Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder.  

To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --extract-albums-synology-photos "album1", "album2", "album3".  

To extract ALL Albums within in Synology Photos database use 'ALL' as <ALBUMS_NAME>.  

The album(s) name <ALBUMS_NAME> can be passed using the new Flag: -ea, --extract-albums-synology-photos <ALBUMS_NAME>  

> [!IMPORTANT]
> <ALBUMS_NAME> should be exists within your Synology Photos Albums database, otherwise it will no extract anything.
> Extraction will be done in background task, so it could take time to complete. Even if the Script finish with success the extraction process could be still running on background, so take this into account.

Example of use:
```
./OrganizeTakeoutPhotos.run --extract-albums-synology-photos "Album 1", "Album 2", "Album 3"
```
With this example, the script will connect to Synology Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Synology_Photos_Albums' folder

### <span style="color:blue">Extra Mode: Create Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Create Albums in Synology Photos' Mode. 

If you configure properly the file 'Synology.config' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.  

The folder <ALBUMS_FOLDER> can be passed using the new Flag: -ca, --create-albums-synology-photos <ALBUMS_FOLDER>  

> [!IMPORTANT]
> <ALBUMS_FOLDER> should be stored within your Synology Photos main folder in your NAS. Typically it is '/volume1/homes/your_username/Photos' and all files within <ALBUMS_FOLDER> should have been already indexed by Synology Photos before you can add them to a Synology Photos Album.  
>
>You can check if the files have been already indexed accessing Synology Photos mobile app or Synology Photos web portal and change to Folder View.  
>
>If you can't see your <ALBUMS_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Synology Photos root folder. 


Example of use:
```
./OrganizeTakeoutPhotos.run --create-albums-synology-photos ./My_Albums_Folder
```
With this example, the script will connect to Synology Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder

### <span style="color:blue">Extra Mode: Delete Empty Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Empty Albums in Synology Photos' Mode. 

If you configure properly the file 'Synology.config' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Empty Albums in Synology Photos database.  

If any Empty Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the new Flag: -de, --delete-empty-albums-synology-photos  


Example of use:
```
./OrganizeTakeoutPhotos.run --delete-empty-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Empty Albums found.

### <span style="color:blue">Extra Mode: Delete Duplicates Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Synology Photos' Mode. 

If you configure properly the file 'Synology.config' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Duplicates Albums in Synology Photos database.  

If any Duplicated Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the new Flag: -dd, --delete-duplicates-albums-synology-photos  


Example of use:
```
./OrganizeTakeoutPhotos.run --delete-duplicates-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Duplicates Albums found.



> [!TIP]
> ## <span style="color:dark">Additional Trick!</span>
> When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">Jaime Tur (@jaimetur) - 2024.</span>
