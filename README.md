# OrganizeTakeoutPhotos
Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, fix metadata, organize per year/month folder, and separate Albums)

### Download Script:
Download the script either Linux or Windows version as you prefeer directly from following links:

Linux version: [OrganizeTakeoutPhotos_v1.2.1_linux.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v1.2.1_linux.zip)

Win64 version: [OrganizeTakeoutPhotos_v1.2.1_win64.zip](https://github.com/jaimetur/OrganizeTakeoutPhotos/raw/refs/heads/main/built_versions/OrganizeTakeoutPhotos_v1.2.1_win64.zip)


### Instructions:
I have prepared the attached scripts pack that you can copy and unzip into any folder of our Synology NAS.

Once download the Takeout Zip's files you have to paste them on the folder called '**Zip_files**' which is the default folder or if you prefeer you can put them in any other subfolder and use the option _'-z, --zip-folder <folder_name>'_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call it depending of your environment
  - If you run it from Synology NAS (using SSH terminal) you have to call the master script '**OrganizeTakeoutPhotos.run**'.
  - If you run it from Windows (using Shell or PowerShell terminal) you have to call the master script '**OrganizeTakeoutPhotos.exe**'

### Syntax:
```
----------------------------------------------------------------------------------------------------------------------------
usage: OrganizeTakeoutPhotos.run/exe [-h] [-z <ZIP_FOLDER>] [-t <TAKEOUT_FOLDER>] [-s <SUFIX>]
                                     [-sl] [-sg] [-se] [-sm] [-fa] [-fn] [-it]

OrganizeTakeoutPhotos v1.2.1 - 2024-11-29

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
-sl, --skip-log
       Skip saving output messages to log file.
-sg, --skip-gpth-tool
       Skip processing files with GPTH Tool.
-se, --skip-exif-tool
       Skip processing files with EXIF Tool.
-sm, --skip-move-albums
       Skip moving albums to Albums folder.
-fa, --flatten-albums
       Flatten photos/videos within each album folder.
-fn, --flatten-no-albums
       Flatten photos/videos within ALL_PHOTOS folder.
-it, --ignore-takeout-structure
       Ignore Google Takeout structure, and fix all files found on <TAKEOUT_FOLDER>.
----------------------------------------------------------------------------------------------------------------------------
```
### Process Explained:
The whole process will do the next actions if all flags are false (by default):

1. Unzip all the Takeout Zips from default zip folder "Zip_files" (you can modify the Zip_folder with the option _'-z, --zip-folder <folder_name>'_) into a subfolder named Takeout (by default) or any other folder if you specify it with the option _'-t, --takeout-folder <folder_name>'_. This step can be skipped if you ommit _'-z, --zip-folder <folder_name>'_ argument (useful in case that you already have unzip all the files manually).

2. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder using a year/month folder structure (This step can be skipped using flag _'-sg, --skip-gpth-tool_'). There are two flags to avoid creating year/month folder structure on this step:
    - _'-fa, --flatten-albums'_ to skip create year/month folder structuture on each album folder individually
    - _'-fn, --flatten-no-albums'_ to skip create year/month folder structuture on ALL_PHOTOS folder (Photos without albums)

3. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to ALL_PHOTOS folder. This step can be skipped using flag _'-sm, --skip-move-albums'_

4.  Finally the script will use EXIF Tool as well just in case that any photo cannot be resolved by GPTH Tool. This step can be skipped using flag _'-se, --skip-exif-tool'_

The result will be a folder (called Takeout_fixed_{timestamp} by default, but you can specify any other with the option _'-t, --takeout-folder <folder_name>'_ or change the default suffix _'fixed'_ by any other using the option _'-s, --suffix <desired_suffix>'_) which will contains:

- ALL_PHOTOS subfolder with all the photos with year/month structure (by default).
- Albums subfolder with all the Albums without year/month structure (by default).

Finally you just need to move the output folder (Takeout_fixed_{timestamp} by default) into your /home/Photos folder and let Synology to index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (408559 files zipped, 168168 photos/video files, 740 albums) and moved it into Synology Photos. 
The whole process took around **5 hours** and this is the time split per step:
1. Extraction process --> 25m
2. GPTH Tool fixing --> 2h 12m
3. Flattening & Moving Album Folder --> 10s
4. EXIF Tool fixing --> 2h 24m
   
(The last step can be skipped if most of your files have been already fixed with GPTH Tool, if not, you can always run again the script to run only this step by omitting the other steps with '--skipt-gpth-tool --skip-move-albums' arguments)

I hope this can be useful for any of you.

### Additional Trick! 

When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

Enjoy it!
Jaime Tur.
@jaimetur 
