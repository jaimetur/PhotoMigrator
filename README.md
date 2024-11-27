# OrganizeTakeoutPhotos
Script to fix metadata of all your Google Photos extracted with Google Takeout

### Download Script:
Download the script from above files either Linux/Mac version or Windows version as you prefeer.

### Instructions:
I have prepared the attached scripts pack that you can copy and unzip into any folder of our Synology NAS.

Once unzipped you have to paste the Takeout Zip files on the folder called '**Zip_files**' which is the default folder or if you prefeer you can put them in any other subfolder and use the option _--zip-folder <folder_name>_ to indicate it. (Note: paste all Zip files downloaded from Google Takeout directly on that folder, without subfolders inside it).

Then you just need to call from SSH terminal the master script '**OrganizeTakeoutPhotos.runme**' (ensure that it has execution permissons) and that's it.

### Syntax:
```
-----------------------------------------------------------------------------------------------------------------------------------------------------------------
OrganizeTakeoutPhotos v1.2.0 - 2024-11-27
Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, fix metadata, organize per year/month folder, and separate Albums)
(c) by Jaime Tur (@jaimetur)

Usage: OrganizeTakeoutPhotos.run [Options]
Options:
  -z,  --zip-folder          Specify the Zip folder where the Zip files downloaded with Google Takeout are placed (default: Zip_files)
  -t,  --takeout-folder      Specify the Takeout folder where all the Zip files downloaded with Google Takeout will be unpacked (default: Takeout)
  -s,  --suffix              Specify the suffix for the output folder. Output folder will be Takeout folder followed by _{suffix}_{timestamp} (default: fixed)

  -sl, --skip-log            Flag to skip saving output messages into log file
  -su, --skip-unzip          Flag to skip unzip files (useful if you have already unzipped all the Takeout Zip files manually)
  -sg, --skip-gpth-tool      Flag to skip process files with GPTH Tool (not recommended since this tool do the main job)
  -se, --skip-exif-tool      Flag to skip process files with EXIF Tool
  -sm, --skip-move-albums    Flag to skip move all albums into Albums folder (not recommended)
  -fa, --flatten-albums      Flag to skip create year/month folder structuture on each album folder individually (recommended)
  -fn, --flatten-no-albums   Flag to skip create year/month folder structuture on ALL_PHOTOS folder (Photos without albums) (not recommended)

  -h , --help                Show this help message and exit
-----------------------------------------------------------------------------------------------------------------------------------------------------------------
```
### Process Explained:
The whole process will do the next actions if all flags are false (by default):

1. Unzip all the Takeout Zips from default zip folder "Zip_files" (you can modify the Zip_folder with the option _--zip-folder <folder_name>_) into a subfolder named Takeout (by default) or any other folder if you specify it with the option _--takeout-folder <folder_name>_. This step can be skipped using flag _--skip-unzip_ in case that you already have unzip all the files manually.

2. Use GPTH Tool to process all .json files and fix date of all photos/videos found on Takeout folder and organize them into the output folder using  a year/month folder structure. There are two flags to avoid creating year/month folder structure on this step:
    - _--flatten-albums_ to skip create year/month folder structuture on each album folder individually
    - _--flatten-no-albums_ to skip create year/month folder structuture on ALL_PHOTOS folder (Photos without albums)

3. Then all the Albums will be moved into Albums subfolder and the Photos that does not belong to any album will be moved to ALL_PHOTOS folder. This step can be skipped using flag _--skip-move-albums_

4.  Finally the script will use EXIF Tool as well just in case that any photo cannot be resolved by GPTH Tool. This step can be skipped using flag _--skip-exif-tool_

The result will be a folder (called Takeout_fixed_{timestamp} by default, but you can specify any other with the option _--takeout-folder <folder_name>_ or change the default suffix _'fixed'_ by any other using the option _--suffix <desired_suffix>_) which will contains:

- ALL_PHOTOS subfolder with all the photos with year/month structure (by default).
- Albums subfolder with all the Albums without year/month structure (by default).

Finally you just need to move the output folder (Takeout_fixed_{timestamp} by default) into your /home/Photos folder and let Synology to index all files (it will take long time). After that you will be able to explore your photos chronologycally on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologycally.

I hope this can be useful for any of you. It was very useful for me when I used it to retrieve more than **300 GB** of Photos and Albums from Google Photos to move it into Synology Photos. The whole process took around **2.5 hours** (extraction process around 1.5h while fixing and sorting process around 1h) to complete runing it directly on a Synology NAS DS920+ using SSH terminal.

### Additional Trick! 

When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files. On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS (I recommend to use the default folder called '**Zip_files**' within this script folder structure)

Enjoy it!
Jaime Tur.
@jaimetur 
