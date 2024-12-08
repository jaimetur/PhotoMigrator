# OrganizeTakeoutPhotos
Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, fix metadata, organize per year/month folder, and separate Albums)

### Download Script:
Download the script either Linux, MacOS or Windows version as you prefeer directly from following links:

Linux version: [OrganizeTakeoutPhotos_v1.4.0_linux.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v1.4.0_linux.zip)

MacOS version: [OrganizeTakeoutPhotos_v1.4.0_macos.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v1.4.0_macos.zip)

Win64 version: [OrganizeTakeoutPhotos_v1.4.0_win64.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v1.4.0_win64.zip)

### Instructions:
I have prepared the attached script that you can copy and unzip into any folder of our Synology NAS.

Once downloaded the Takeout Zip's files you have to paste them on the folder called '**Zip_files**' which is the default folder or if you prefeer you can put them in any other subfolder and use the option _'-z, --zip-folder <folder_name>'_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call it depending of your environment
  - If you run it from Synology NAS (using SSH terminal) you have to call the master script '**OrganizeTakeoutPhotos.run**'.
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**OrganizeTakeoutPhotos.exe**'

### Syntax:
```
----------------------------------------------------------------------------------------------------------------------------
usage: OrganizeTakeoutPhotos.py [-h] [-z <ZIP_FOLDER>] [-t <TAKEOUT_FOLDER>] [-s <SUFIX>]
                                [-as ['flatten', 'year', 'year/month', 'year-month']]
                                [-ns ['flatten', 'year', 'year/month', 'year-month']]
                                [-sg] [-sm] [-se] [-it] [-nl] [-re] [-mt]
                                [-fd <DUPLICATES_FOLDER(s)> [<DUPLICATES_FOLDER(s)> ...]]
                                [-da ['list', 'move', 'remove']]

OrganizeTakeoutPhotos v1.4.0 - 2024-12-08

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates,
fix metadata, organize per year/month folder, and separate Albums).
(c) by Jaime Tur (@jaimetur)

options:

-h,  --help
       show this help message and exit
-z,  --zip-folder <ZIP_FOLDER>
       Specify the Zip folder where the Zip files are placed. If this option is omitted,
       unzip of input files will be skipped.
-t,  --takeout-folder <TAKEOUT_FOLDER>
       Specify the Takeout folder to process. If -z, --zip-folder is present, this will be
       the folder to unzip input files. Default: 'Takeout'
-s,  --suffix <SUFIX>
       Specify the suffix for the output folder. Default: 'fixed'
-as, --albums-structure ['flatten', 'year', 'year/month', 'year-month']
       Specify the type of folder structure for each Album folder.
-ns, --no-albums-structure ['flatten', 'year', 'year/month', 'year-month']
       Specify the type of folder structure for ALL_PHOTOS folder (Photos that are no
       contained in any Album).
-sg, --skip-gpth-tool
       Skip processing files with GPTH Tool.
-sm, --skip-move-albums
       Skip moving albums to Albums folder.
-se, --skip-extras
       Skip processing extra photos such as  -edited, -effects photos.
-it, --ignore-takeout-structure
       Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..),
       and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.
-nl, --no-log-file
       Skip saving output messages to execution log file.
-re, --run-exif-tool
       Run EXIF Tool files processing in the last step. (Useful if GPTH Tool cannot fix
       some files, but is a slow process). RECOMMENDATION: Use only if after runnning
       normal process with GPTH Tool, you still have many files with no date.
-mt, --move-takeout-folder
       Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>.
       CAUTION: Useful to avoid disk space duplication and improve execution speed, but
       you will lost your original unzipped files!!!. Use only if you keep the original
       zipped files or you have disk space limitations and you don't mind to lost your
       original unzipped files.
-fd, --find-duplicates-in-folders <DUPLICATES_FOLDER(s)>
       Specify the Folder(s) where you want to find duplicates. If found any duplicates
       within the list of folders given, the file in the first folder will be kept and the
       others will me moved or deleted according to the flag '-da, --duplicates-action'
-da, --duplicates-action ['list', 'move', 'remove']
       Specify what to do with duplicates files found.

----------------------------------------------------------------------------------------------------------------------------
```

```

Example of use:

./OrganizeTakeoutPhotos --zip-folder ./Zips --takeout-folder ./Takeout --albums-structure year/month

Withh this example, the script will unzip all zip files found under ./Zips folder into ./Takeout folder.
Then will process ./Takeout folder to fix all files found and set the correct date and time.
Finally the script will create a folder structure based on year/month for each Album found.

```

### Process Explained:
The whole process will do the next actions if all flags are false (by default):

1. Unzip all the Takeout Zips from default zip folder "Zip_files" (you can modify the Zip_folder with the option _'-z, --zip-folder <folder_name>'_) into a subfolder named Takeout (by default) or any other folder if you specify it with the option _'-t, --takeout-folder <folder_name>'_. This step can be skipped if you ommit _'-z, --zip-folder <folder_name>'_ argument (useful in case that you already have unzip all the files manually).
   
2. Pre-Process TAKEOUT_FOLDER to delete '@eaDir' subfolders (Synology metadata subfolders with miniatures) and to Fix .MP4 files extracted from Live pictures and with no .json file associated.

3. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder (This step can be skipped using flag _'-sg, --skip-gpth-tool_').
  
   There are two flags to avoid creating year/month folder structure on this step:
    - _'-fa, --flatten-albums'_ to skip create year/month folder structuture on each album folder individually
    - _'-fn, --flatten-no-albums'_ to skip create year/month folder structuture on ALL_PHOTOS folder (Photos without albums)
  
4. Sync Timestamps of .MP4 files generated by Google Photos with Live Picture files (.heic, .jpg, .jpeg) if both files have the same name and are in the same folder

5. Create Date Folder structure ('flatten', 'year', 'year/month', 'year-month') to Albums and No Albums folders according with the options given by arguments:
   - _'-as, --albums-structure'_ <'flatten', 'year', 'year/month', 'year-month'>. Applies to each Album folder
   - _'-ns, --no-albums-structure'_ <'flatten', 'year', 'year/month', 'year-month'> Applies to ALL_PHOTOS folder (Photos without any Albums)

6. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to ALL_PHOTOS folder. This step can be skipped using flag _'-sm, --skip-move-albums'_

7. In next step, the script will use EXIF Tool as well just in case that any photo cannot be resolved by GPTH Tool. This step is disabled by default, but you can force it using flag _'-re, --run-exif-tool'_ (this step is optional)


The result will be a folder (called Takeout_fixed_{timestamp} by default, but you can specify any other with the option _'-t, --takeout-folder <folder_name>'_ or change the default suffix _'fixed'_ by any other using the option _'-s, --suffix <desired_suffix>'_) which will contains:

- ALL_PHOTOS subfolder with all the photos with year/month structure (by default).
- Albums subfolder with all the Albums without year/month structure (by default).

Finally you just need to move the output folder (Takeout_fixed_{timestamp} by default) into your /home/Photos folder and let Synology to index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (408559 files zipped, 168168 photos/video files, 740 albums) and moved it into Synology Photos. 
The whole process took around **5 hours** and this is the time split per step:
1. Extraction process --> 25m
2. Pre-processing Takeout_folder --> 3m 50s
3. GPTH Tool fixing --> 2h 12m
4. Sync .MP$ timestamps --> 10s
5. Create Date Folder Structure --> 50s
6. Moving Album Folder --> 1s
7. EXIF Tool fixing --> 2h 24m
   
(Step 7 is disabled by default, and is only recommended when GPTH Tool cannot fix many files. You can always run again the script to run only this step (using flag '-re, --run-exif-tool) and omitting the other steps with the flags '--skipt-gpth-tool --skip-move-albums' arguments)

### Find Duplicates Mode:
Additionally this script from version 1.4.0 onwards, can be used to find duplicated files in a smart way:
- In Find Duplicates Mode, yout must provide a folder (or list of foldders) using the flag '-fd, --find-duplicates-in-folder', wherre the script will look for duplicated files. If you provide more than one folders, when a duplicated file is found, the script will mainains the file found within the folder given first in the list of folders provided. If the duplicaded files are within the same folder given as an argument, the script will maitain the file whose name is shorter.
- For this mode, you must also provide an action to do with the duplicated files found. For that you can use the flag '-da, --duplicates-action' to specify what to do with duplicated files found. Valid actions are: 'list', 'move' or 'remove'. If the provided action is 'list', then the script will only create a list of duplicaed files found within the folder Duplicates. If the action is 'move' then the script will maintain the main file and move the others inside the folder Duplicates/Duplicated_timestamp. Finally, if the action is 'remove' the script will maintain the main file and remove the others.

```

Example of use:

./OrganizeTakeoutPhotos --duplicates-action move --find-duplicates-in-folder ./Albums ./ALL_PHOTOS

With this example, the script will find duplicated files within folders ./Albums and ./ALL_PHOTOS,
If finds any duplicated, will keep the file within ./Albums folder (bacause it has been passed first on the list)
and will move the otherss duplicated files into the ./Duplicated folder on the root folder of the script.

```

I hope this can be useful for any of you.

### Additional Trick! 

When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

Enjoy it!
Jaime Tur.
@jaimetur 
