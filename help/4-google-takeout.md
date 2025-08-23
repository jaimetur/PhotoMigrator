# <span style="color:green">🗃️ Google Takeout Management</span>

From version 1.0.0 onwards, the Tool can process your Google Photos Takeout files to embed timestamp and GPS data among to other tags within each photo/video found on it.

But also this Feature can handle albums associations, remove duplicates, organize files per year/month, organize assets within album(s) in subfolders, auto rename albums, etc...

The CORE of this Feature is the Tool Google Photos Takeout Helper ([GPTH Tool](https://github.com/Xentraxx/GooglePhotosTakeoutHelper) by [TheLastGimbus](https://github.com/TheLastGimbus)/[Wacheee](https://github.com/Wacheee) and v4.x.x by [Xentraxx](https://github.com/Xentraxx)).

Also, GPTH uses internally EXIF Tool to embed EXIF tags inside each photo/video processed.

**PhotoMigrator** already includes embedded both tools GPTH and EXIF Tool, so you don't need to install any additional software to use them. 

This feature has been designed to automatically analyze your Google Photos Takeout, extract all the information from the sidecar JSON files (or guess some missing information using heuristics algorithms) and embeds all the extracted info into each asset file using EXIF tags.  

In this way your Media Library will be ready to be migrated to any other Cloud Photo services without losing any important info such as, Albums info, Original date, GPS location, Camera info, etc...

But this feature also helps you to organize and clean your Media Library removing duplicates, creating Year/Month folder structure, creating symbolic links for Albums assets, Auto renaming Albums to clean their names and include a prefix with the date of its assets, etc...

The whole process is done in an automatic way and is divided in different steps (some of them are optionals).

In the following link you can find the [Complete Pipeline and features of GPTH Tool](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/00_GPTH_complete_pipeline.md).


## Process Explained

- To execute the Google Takeout Processing, you need to call the tool with the argument _**`-gTakeout, --google-takeout <INPUT_TAKEOUT_FOLDER>`**_.   

- Where, `<INPUT_TAKEOUT_FOLDER>` is the folder that content the Google Takeout to process (if the Takeout is in Zip files, it will be extracted first into folder `<INPUT_TAKEOUT_FOLDER>_unzipped`.  

- If you execute the tool without arguments or with your Takeout folder as unique argument by default the tool will execute the Feature **Google Takeout Process** (requesting the user to select the Takeout folder if not detected). 

- The Takeout Processing can be configured with different settings, depending on the arguments used during the call to the Tool.

- The whole process will do the following posible Steps (depending on which flag/arguments are enabled):  

### Steps during Takeout Processing:
Below you can see the different steps of this feature:

#### 1. 🔍 Pre Checks steps
  - 1.1. 📦 Unpack your Takeout Zip files if needed.  
  - 1.2. 🗃️ Create a backup of your original Takeout if needed.  

#### 2. 🪛 Pre Process steps 
`(default=enabled. Can be disabled using flag '-gSkipPrep; --google-skip-preprocess')`
  - 2.1. 🧹 Clean Input folder to delete `@eaDir` subfolders (Synology metadata subfolders with miniatures).
  - 2.2. 🧬 Merge Live pictures (.heic, .jpg, .jpeg) with the associated video (.mp4).
  - 2.3. ✂️ Fix Truncations on sidecar JSON names and media files to complete truncated suffixes or extensions when the filename length is high. 

#### 3. 🔢 Calculate statistics of your original Takeout

#### 4. 🧠 Process steps 
  - 4.1. 🧠 GPTH Processing (Core of this Module) which includes the following sub-steps:  
          `(default=enabled. Can be disabled using flag 'gSkipGpth, --google-skip-gpth-tool')`
    - ✂️ Fix Extensions
    - 🔍 Discovering Media
    - 👥 Remove Duplicates
    - 🧾 Extract Metadata (Process .json files to extract metadata, including creation date and time, GPS data, Albums info extraction, etc... of all your assets.)
    - ✍️ Write EXIF
    - 📚 Find Albums (Separate your assets per Albums).
    - 🔗 Create Symbolic Links for assets within any Album (to save disk space).   
       `(default=enabled. Can be disabled using flag '-gnsa, --google-no-symbolic-albums')`
    - 📁 Move Files
    - 🕒 Update Creation Time
  - 4.2. ➡️ <span style="color:grey">Copy/Move files to Output folder manually.   
         `(default=disabled. It is automatically enabled if detect that Step 3.1 has been skipped)`</span>

#### 5. 🔢 Calculate statistics of your Final processed Media Library

#### 6. ✅ Post Process steps
  - 6.1. 🕒 Synchronize MP4 files associated to Live pictures with the associated HEIC/JPG file. 
  - 6.2. 📚 Separate all your Albums folders within 'Albums' subfolder from the original assets within 'ALL_PHOTOS' subfolder. `(default=enabled. Can be disabled using flag '-gsma, --google-skip-move-albums')`
  - 6.3. 📁 Organize your assets in a year/month structure for a better organization. 
    - Can be customized using the flags: `-gafs, --google-albums-folders-structure` and `-gnas, --google-no-albums-folders-structure`  
    - `(default: 'flatten' for Albums; 'year/month' for ALL_PHOTOS)`  
  - 6.4. 📝 <span style="color:grey">Auto rename Albums folders to homogenize all names based on content dates.</span>  
         `(default=disabled. Can be enabled using flag '-graf, --google-rename-albums-folders')`
  - 6.5. 👥 <span style="color:grey">Detect and remove duplicates.</span>  
         `(default=disabled. Can be enabled using flag '-grdf, --google-remove-duplicates-files')`
  - 6.6. 🔢 Count Albums.
  - 6.7. 🧹 Remove empty folders. 

#### 7. ✅ Final steps
  - 7.1. 🧹 Clean Final Media Library.
  - 7.2. ❔ Show Files Without Dates.
  - 7.3. 🔢 Show and Compare Initial / Final statistics.

> [!NOTE]  
> Step 4.2 is disabled by default, but It is automatically enabled if detect that Step 3.1 has been skipped.
> 
> Step 6.4 is disabled by default, but it is very useful if you want to homogenize all your albums folders names cleaning the name and adding a prefix based on the date range of its content. [see Folder Rename Content Based Extra Feature](https://github.com/jaimetur/PhotoMigrator/blob/main/help/7-other-features.md#-folder-rename-content-based-extra-feature).
>
> Step 6.5 is disabled by default, and is only recommended if you don't use Symbolic Links for Albums assets, and you want to save disk space avoiding having the same physical file in more than one folder (in case that the same file belongs to multiples Albums).   

> [!NOTE]
> It was very useful for me when I run it to process more than **300 GB** of Photos and Albums from Google Photos (423807 files zipped, 220224 photos/video files, 900 albums) and moved it into Synology Photos.  
> 
> The whole process took around **~10 hours** (It could vary depending on the number of optional steps that have been enabled). This is the time split per steps:  
> 
> Processing Time per Step:
> -------------------------------------------------------------------
> 
> STEP 1    : 🔍 [PRE-CHECKS]-[TOTAL DURATION]             :  1:01:01
> Step 1.1  : 🔍 [PRE-CHECKS]-[Unzip Takeout]              :  1:01:01
> Step 1.2  : 🔍 [PRE-CHECKS]-[Clone Takeout]              :  Skipped
> 
> STEP 2    : 🪛 [PRE-PROCESS]-[TOTAL DURATION]            :  0:36:42
> Step 2.1  : 🪛 [PRE-PROCESS]-[Clean Takeout Folder]      :  0:00:02
> Step 2.2  : 🪛 [PRE-PROCESS]-[MP4/Live Pics. Fixer]      :  0:04:34
> Step 2.3  : 🪛 [PRE-PROCESS]-[Truncations Fixer]         :  0:32:05
> 
> STEP 3    : 🔢 [PRE]-[Analyze Takeout]                   :  0:24:55
> 
> STEP 4    : 🧠 [PROCESS]-[TOTAL DURATION]                :  7:34:13
> Step 4.1  : 🧠 [PROCESS]-[Metadata Processing]           :  7:34:13
> Step 4.2  : 📁 [PROCESS]-[Copy/Move]                     :  Skipped
> 
> STEP 5    : 🔢 [POST]-[Analyze Output]                   :  0:22:21
> 
> STEP 6    : ✅ [POST-PROCESS]-[TOTAL DURATION]           :  0:14:47
> Step 6.1  : 🕒 [POST-PROCESS]-[MP4 Timestamp Synch]      :  0:00:12
> Step 6.2  : 📚 [POST-PROCESS]-[Albums Moving]            :  0:01:34
> Step 6.3  : 📁 [POST-PROCESS]-[Create year/month struct] :  0:12:15
> Step 6.4  : 📝 [POST-PROCESS]-[Albums Renaming]          :  0:00:41
> Step 6.5  : 👥 [POST-PROCESS]-[Remove Duplicates]        :  Skipped
> Step 6.6  : 🔢 [POST-PROCESS]-[Count Albums]             :  0:00:03
> Step 6.7  : 🧹 [POST-PROCESS]-[Remove Empty Folders]     :  0:00:02
> 
> STEP 7    : 🏁 [FINAL-STEPS]-[TOTAL DURATION]            :  0:07:49
> Step 7.1  : 🧹 [FINAL-STEPS]-[Final Cleaning]            :  0:07:47
> Step 7.2  : ❔ [FINAL-STEPS]-[Files without dates]       :  0:00:01
> 
> TOTAL PROCESSING TIME                                    :  10:38:28
>
> NOTE: Above times are approximates and were measured running the tool on Linux using a Synology NAS DS920+.


### Output of Takeout Processing:
The result will be a folder named `<TAKEOUT_FOLDER>_<SUFFIX>_<TIMESTAMP>` by default. 
  - It is possible to change the default suffix _`processed`_ by any other using the option _`-gofs, --google-output-folder-suffix <SUFFIX>`_).  

The final `<OUTPUT_FOLDER>` will include:
- `Albums` subfolder with all the Albums without year/month structure (by default).
- `<NO_ALBUMS_FOLDER>` subfolder with all the photos with year/month structure (by default).

### Complete list of Flags/Arguments admitted:
- [Arguments](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description.md)
- [Arguments short version](https://github.com/jaimetur/PhotoMigrator/blob/main/help/2-arguments-description-short.md)

> [!TIP]
> If you want to use your processed assets within Synology Photos, you just need to move `OUTPUT_FOLDER` into your /home/Photos folder and let Synology index all files (it will take long time). 
>
> After that you will be able to explore your photos chronologically on the Synology Photos App, and all your Albums will be there when you explore the library by folder instead of chronologically.


## **Examples of use:**

- **Example 1:**
```
./PhotoMigrator.run --google-takeout ./MyTakeout --google-remove-duplicates-files
```
 
In this example, the tool will do the Takeout Processing with the following steps:
1. Process you Takeout Files found in folder `./MyTakeout` (Unzipping them if needed) and fix all files found to set the correct date and time, and identifying which assets belongs to each Album created on Google Photos. 
2. Create a folder structure based on year/month for the folder `<OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER>` (by default).  
3. Create a flatten folder structure for each Album subfolder found in `<OUTPUT_TAKEOUT_FOLDER>/Albums` (by default).    
4. Move the files will into `./MyTakeout_processed_timestamp` folder where timestamp is the timestamp of the execution.
5. Remove any duplicates files found in `./MyTakeout_processed_timestamp` folder


- **Example 2:**
```
./PhotoMigrator.run --google-takeout ./MyTakeout --google-remove-duplicates-files --google-no-symbolic-albums
```
 
In this example, the tool will do the Takeout Processing with the following steps:
1. Process you Takeout Files found in folder `./MyTakeout` (Unzipping them if needed) and fix all files found to set the correct date and time, and identifying which assets belongs to each Album created on Google Photos to create symbolic links for each asset in any Album to the original file stored in `<NO_ALBUMS_FOLDER>` subfolder.  
2. Create a folder structure based on year/month for the folder `<OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER>` (by default).  
3. Create a flatten folder structure for each Album subfolder found in `<OUTPUT_TAKEOUT_FOLDER>/<ALBUMS_FOLDER>` (by default).    
4. Move the files will into `./MyTakeout_processed_timestamp` folder where timestamp is the timestamp of the execution.
5. Remove any duplicates files found in `./MyTakeout_processed_timestamp` folder


## Get Your Photos from Google Takeout
1. Go to Google Photos Takeout [link here](https://takeout.google.com/takeout/custom/photos)
2. Deselect all, then select only Google Photos
3. Select all your Albums and Year folders that you want to export
4. Download all ZIP files (use .zip format and 50 GB of filesize)

> [!TIP]
> ## <span style="color:dark">Additional Tip</span>
> When prepare Google Takeout to export all your Photos and Albums, select 50GB for the zip file size and select Google Drive as output for those Zip files.  
>
> On this way you can just Download all the big Zip files directly on your Synology NAS by using the Tool Cloud Sync (included on Synology App Store) and creating a new synchronization task from your Google Drive account (/Takeout folder) to any local folder of your Synology NAS.

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)


---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
