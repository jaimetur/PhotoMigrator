## <span style="color:green">Other Standalone Features Documentation:</span>

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


## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  