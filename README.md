# OrganizeTakeoutPhotos
Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (Fix metadata, Identify Live Pictures, Organize per year/month folders, separate Albums, Fix Symbolic Links, Find Duplicates, Manage Duplicates, Homogenize Albums folders name, Import Albums to Synology Photos, Delete Empty Synology Photos Albums and much more)

## Download Script:
Download the script either Linux, MacOS or Windows version as you prefeer directly from following links:

Linux version: [OrganizeTakeoutPhotos_v2.0.0_linux.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v2.0.0_linux.zip)

MacOS version: [OrganizeTakeoutPhotos_v2.0.0_macos.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v2.0.0_macos.zip)

Win64 version: [OrganizeTakeoutPhotos_v2.0.0_win64.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v2.0.0_win64.zip)

## Instructions:
I have prepared the attached script that you can copy and unzip into any folder of our Synology NAS.

Once downloaded the Takeout Zip's files you have to paste them on the folder called '**Zip_files**' which is the default folder or if you prefeer you can put them in any other subfolder and use the option _'-z, --zip-folder <folder_name>'_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call it depending of your environment
  - If you run it from Synology NAS (using SSH terminal) you have to call the master script '**OrganizeTakeoutPhotos.run**'. Minimum DSM version required is 7.1.0.
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**OrganizeTakeoutPhotos.exe**'

## Syntax:
```
----------------------------------------------------------------------------------------------------------------------------
usage: OrganizeTakeoutPhotos.run/exe [-h] [-z <ZIP_FOLDER>] [-t <TAKEOUT_FOLDER>] [-s <SUFIX>]
                                     [-as ['flatten', 'year', 'year/month', 'year-month']]
                                     [-ns ['flatten', 'year', 'year/month', 'year-month']]
                                     [-sg] [-se] [-sm] [-sa] [-it] [-mt] [-rd] [-re]
                                     [-da ['list', 'move', 'remove']] [-nl]
                                     [-fs <FOLDER_TO_FIX>] [-ra <ALBUMS_FOLDER>]
                                     [-fd <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]]
                                     [-pd <DUPLICATES_REVISED_CSV>] [-ca <ALBUMS_FOLDER>] [-de]

OrganizeTakeoutPhotos v2.0.0 - 2024-12-22

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) by Jaime Tur (@jaimetur)

optional arguments:

-h,   --help
        show this help message and exit
-z,   --zip-folder <ZIP_FOLDER>
        Specify the Zip folder where the Zip files are placed. If this option is omitted,
        unzip of input files will be skipped.
-t,   --takeout-folder <TAKEOUT_FOLDER>
        Specify the Takeout folder to process. If -z, --zip-folder is present, this will
        be the folder to unzip input files. Default: 'Takeout'.
-s,   --suffix <SUFIX>
        Specify the suffix for the output folder. Default: 'fixed'
-as,  --albums-structure ['flatten', 'year', 'year/month', 'year-month']
        Specify the type of folder structure for each Album folder (Default: 'flatten').
-ns,  --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']
        Specify the type of folder structure for ALL_PHOTOS folder (Default:
        'year/month').
-sg,  --skip-gpth-tool
        Skip processing files with GPTH Tool. NOT RECOMMENDED!!! because this is the Core
        of the Script. Use this flag only for testing purposses.
-se,  --skip-extras
        Skip processing extra photos such as  -edited, -effects photos.
-sm,  --skip-move-albums
        Skip moving albums to Albums folder.
-sa,  --symbolic-albums
        Creates symbolic links for Albums instead of duplicate the files of each Album.
        (Useful to save disk space but may not be portable to other systems).
-it,  --ignore-takeout-structure
        Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders,
        etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from
        them.
-mt,  --move-takeout-folder
        Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>.
        CAUTION: Useful to avoid disk space duplication and improve execution speed, but
        you will lost your original unzipped files!!!. Use only if you keep the original
        zipped files or you have disk space limitations and you don't mind to lost your
        original unzipped files.
-rd,  --remove-duplicates-after-fixing
        Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.
-re,  --run-exif-tool
        Run EXIF Tool files processing in the last step. (Useful if GPTH Tool cannot fix
        some files, but is a slow process). RECOMMENDATION: Use only if after runnning
        normal process with GPTH Tool, you still have many files with no date.
-da,  --duplicates-action ['list', 'move', 'remove']
        Specify what to do with duplicates files found. This argument is a complementary
        argument for '-fd, --find-duplicates' and will force the script to run in Mode
        'Find Duplicates' (All other steps will be skipped).
-nl,  --no-log-file
        Skip saving output messages to execution log file.

EXTRA MODES:
------------
Following optional arguments can be used to execute the Script in any of the usefull
additionals Extra Modes included. When an Extra Mode is detected only this module will be
executed (ignoring the normal steps). If more than one Extra Mode is detected, only the
first one will be executed.

-fs,  --fix-symlinks-broken <FOLDER_TO_FIX>
        Force Mode: 'Fix Symbolic Links Broken'. The script will try to fix all symbolic
        links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder
        from the OUTPUT_FOLDER and some Albums seems to be empty.
-ra,  --rename-albums <ALBUMS_FOLDER>
        Force Mode: 'Rename Albums'. Rename all Albums folders found in <ALBUMS_FOLDER> to
        unificate the format.
-fd,  --find-duplicates-in-folders <DUPLICATES_FOLDER>
        Force Mode: 'Find Duplicates'. Specify the Folder(s) where you want to find
        duplicates. If found any duplicates within the list of folders given, the file in
        the first folder will be kept and the others will me moved or deleted according to
        the flag '-da, --duplicates-action'.
-pd,  --process-duplicates-revised <DUPLICATES_REVISED_CSV>
        Force Mode: 'Process Duplicates Revised'. Specify the Duplicates CSV file revised
        with specifics Actions in Action column, and the script will execute that Action
        for each duplicates found in CSV. Valid Actions: restore_duplicate /
        remove_duplicate / replace_duplicate.
-ca,  --create-albums-synology-photos <ALBUMS_FOLDER>
        force Mode: 'Create Albums in Synology Photos'. The script will look for all
        Albums within ALBUM_FOLDER and will create one Album per folder into Synology
        Photos.
-de,  --delete-empty-albums-synology-photos
        Force Mode: 'Remove Empty Albums in Synology Photos'. The script will look for all
        Albums in Synology Photos database and if any Album is empty, will remove it from
        Synology Photos database.
----------------------------------------------------------------------------------------------------------------------------
```

```

Example of use:

./OrganizeTakeoutPhotos --zip-folder ./Zips --takeout-folder ./Takeout --albums-structure year/month

Withh this example, the script will unzip all zip files found under ./Zips folder into ./Takeout folder.
Then will process ./Takeout folder to fix all files found and set the correct date and time.
Finally the script will create a folder structure based on year/month for each Album found.
The output files will be placed into ./Takeout_fixed_timestamp folder.

```

## Process Explained:
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

8. (Optional) In this step, the script will use EXIF Tool as well just in case that any photo cannot be resolved by GPTH Tool. This step is disabled by default, but you can force it using flag _'-re, --run-exif-tool'_ (this step is optional)

8. (Optional) In this step, the script will look for any duplicate file on OUTPUT_FOLDER (ignoring symbolic links), and will remove all duplicates keeping only the principal file (giving more priority to duplicates files found into any album folder than those found on 'ALL_PHOTOS' folder. 


The result will be a folder (called Takeout_fixed_{timestamp} by default, but you can specify any other with the option _'-t, --takeout-folder <folder_name>'_ or change the default suffix _'fixed'_ by any other using the option _'-s, --suffix <desired_suffix>'_) which will contains:

- ALL_PHOTOS subfolder with all the photos with year/month structure (by default).
- Albums subfolder with all the Albums without year/month structure (by default).

Finally you just need to move the output folder (Takeout_fixed_{timestamp} by default) into your /home/Photos folder and let Synology to index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (408559 files zipped, 168168 photos/video files, 740 albums) and moved it into Synology Photos. 
The whole process took around **10 hours** and this is the time split per step:
1. Extraction process --> 25m
2. Pre-processing Takeout_folder --> 3m 50s
3. GPTH Tool fixing --> 2h 12m
4. Sync .MP$ timestamps --> 10s
5. Create Date Folder Structure --> 50s
6. Moving Album Folder --> 1s
7. Fix Broken Symlinks --> 10m
8. (Optional) EXIF Tool fixing --> 2h 24m
9. (Optional) Remove Duplicates after fixing --> 3h
   
NOTE: Step 8 is disabled by default, and is only recommended when GPTH Tool cannot fix many files. You can always run again the script to run only this step (using flag '-re, --run-exif-tool) and omitting the other steps with the flags '--skipt-gpth-tool --skip-move-albums' arguments.

NOTE: Step 9 is disabled by default, and is only recommended if you want to save disk space and want to avoid having the same physical file in more than one folder (in case that the same file belongs to multiples Albums).

## EXTRA MODES:
Additionally, this script can be executed with 6 Extra Modes:

### Fix Symbolic Links Broken:
From version 1.5.0 onwards, the script can be executed in 'Fix Symbolic Links Broken' Mode. 
- You can use the flag '-fs, --fix-symlinks-broken <FOLDER_TO_FIX>' and provide a FOLDER_TO_FIX and the script will try to look for all symbolic links within FOLDER_TO_FIX and will try to find the target file within the same folder.
- This is useful when you run the main script using flag '-sa, --symbolic-albums' to create symbolic Albums instead of duplicate copies of the files contained on Albums.
- If you run the script with this flag and after that you rename original folders or change the folder structure of the OUTPUT_FOLDER, your symbolic links may be broken and you will need to use this feature to fix them.

```

Example of use:

./OrganizeTakeoutPhotos --fix-symlinks-broken ./OUTPUT_FOLDER 

With this example, the script will look for all symbolic links within OUTPUT_FOLDER and if any is broken,
the script will try to fix it finding the target of the symlink within the same OUTPUT_FOLDER structure.

```

### Find Duplicates Mode:
From version 1.4.0 onwards, the script can be executed in 'Find Duplicates' Mode. In this mode, the script will find duplicates files in a smart way based on file size and content:
- In Find Duplicates Mode, yout must provide a folder (or list of foldders) using the flag '-fd, --find-duplicates-in-folder', wherre the script will look for duplicates files. If you provide more than one folders, when a duplicated file is found, the script will mainains the file found within the folder given first in the list of folders provided. If the duplicaded files are within the same folder given as an argument, the script will maitain the file whose name is shorter.
- For this mode, you must also provide an action to do with the duplicates files found. For that you can use the flag '-da, --duplicates-action' to specify what to do with duplicates files found. Valid actions are: 'list', 'move' or 'remove'. If the provided action is 'list', then the script will only create a list of duplicaed files found within the folder Duplicates. If the action is 'move' then the script will maintain the main file and move the others inside the folder Duplicates/Duplicates_timestamp. Finally, if the action is 'remove' the script will maintain the main file and remove the others.

```

Example of use:

./OrganizeTakeoutPhotos --find-duplicates-in-folders ./Albums ./ALL_PHOTOS --duplicates-action move

With this example, the script will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicates, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicates files into the ./Duplicates folder on the root folder of the script.

```

### Process Duplicates Mode:
From version 1.6.0 onwards, the script can be executed in 'Process Duplicates' Mode. In this mode, the script will process the CSV generated during 'Find Duplicates' mode and will perform the Action given in column Action for each duplicated file.
- Included new flag '-pd, --process-duplicates-revised' to process the Duplicates.csv output file after execute the 'Find Duplicates Mode'. In that case, the script will move all duplicates found to Duplicates folder and will generate a CSV file that can be revised and change the Action column values.
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : Use this action to replace the principal file chosen for each duplicates and select manually the principal file
        - Duplicated file moved to Duplicates folder will be restored to its original location as principal file
        - and Original Principal file detected by the Script will be removed permanently

```

Example of use:

./OrganizeTakeoutPhotos --process-duplicates-revised ./Duplicates/Duplicates_revised.csv

With this example, the script will process the file ./Duplicates/Duplicates_revised.csv
and for each duplicate, will do the given action according with Action column

```

### Rename Albums Folders Mode:
TODO: Describe this mode

### Create Albums in Synology Photos Mode:
TODO: Describe this mode

### Delete Empty Albums in Synology Photos Mode:
TODO: Describe this mode

I hope this can be useful for any of you.

## Additional Trick! 

When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

Enjoy it!
Jaime Tur.
@jaimetur 
