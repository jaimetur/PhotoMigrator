# <span style="color:green">🛠️ Other Standalone Extra Features</span>

Additionally, this Tool can be executed with 4 Standalone Extra Features: 
 
1. **Find Duplicates**
2. **Process Duplicates**
3. **Fix Symbolic Links Broken**
4. **Folder Rename Content Based** 

If more than one Stand Alone Extra Feature is detected, only the first one will be executed


# <span style="color:blue"> Find Duplicates (Extra Feature)</span>
- **From:** v1.4.0
- **Usage:**
  - To run this feature you have to use the argument `-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>`
  - where, 
      - `<DUPLICATES_FOLDER>` is the folder (or list of folders) where the Tool will look for duplicates files. If you provide more than one folder, when a duplicated file is found, the Tool will maintain the file found within the folder given first in the list of folders provided. If the duplicated files are within the same folder, then the Tool will maintain the file whose name is shorter.
      - `<ACTION>` is an action to specify what to do with duplicates files found. You can include any of the valid actions. 
        - Valid actions are: `list`, `move` or `remove`. If not action is detected, `list` will be the default action.
- **Pre-Requisites:**
  - None
- **Explanation:**
  - With this feature, the Tool will find duplicates files in a smart way based on file size and content and will perform the action based on the <ACTION> selected:
    - If `<ACTION>` is `list`, then the Tool will only generate a CSV file with all the duplicates found and store it within the folder `<DUPLICATES_FOLDER>`. 
    - If `<ACTION>` is `move` then the Tool will maintain the main file and move the others inside the folder <DUPLICATES_FOLDER>/Duplicates_timestamp and also, will generate a CSV file with all the duplicates found and store it within the folder `Duplicates`. 
    - If `<ACTION>` is `remove` the Tool will maintain the main file and remove the others and also will generate a CSV file with all the duplicates found and store it within the folder `<DUPLICATES_FOLDER>`.
- **Example of use:**
  ```
  ./PhotoMigrator --find-duplicatess move ./Albums ./ALL_PHOTOS move
  ```
  With this example, the Tool will find duplicates files within folders ./Albums and ./ALL_PHOTOS,
  If it finds any duplicates, will keep the file within ./Albums folder (because it has been passed first on the list)
  and will move (because the selected action is `move`) the others duplicates files into the ´<DUPLICATES_FOLDER>´ folder.


# <span style="color:blue"> Process Duplicates (Extra Feature)</span>
- **From:** v1.6.0
- **Usage:**
  - To run this feature you have to use the argument `-procDup, --process-duplicates <DUPLICATES_REVISED_CSV>`
  - where `<DUPLICATES_REVISED_CSV>` is the output file generated after execution of the 'Find Duplicates' feature.
- **Pre-Requisites:**
  - None
- **Explanation:**
  - With this feature, the Tool will process the CSV generated during execution of 'Find Duplicates' feature and will perform the Action given in column Action for each duplicated file.
  - You can revise and change the Action column values of the `<DUPLICATES_REVISED_CSV>` file.
  - Possible Actions in revised CSV file are:
      - `remove_duplicate`  : Duplicated file moved to `<DUPLICATES_FOLDER>` will be permanently removed
      - `restore_duplicate` : Duplicated file moved to `<DUPLICATES_FOLDER>` will be restored to its original location
      - `replace_duplicate` : Use this action to replace the principal file chosen for each duplicate and select manually the principal file
          - Duplicated file moved to `<DUPLICATES_FOLDER>` will be restored to its original location as principal file
          - and Original Principal file detected by the Script will be removed permanently
- **Example of use:**
  ```
  ./PhotoMigrator --process-duplicates ./Duplicates/Duplicates_revised.csv
  ```
  With this example, the Tool will process the file ./Duplicates/Duplicates_revised.csv
  and for each duplicate, will do the given action according to Action column


# <span style="color:blue"> Fix Symbolic Links Broken (Extra Feature)</span>
- **From:** v1.5.0
- **Usage:**
  - To run this feature you have to use the argument `-fixSym, --fix-symlinks-broken <FOLDER_TO_FIX>`.
  - where `<FOLDER_TO_FIX>` is the folder that contains the Symbolic Links to fix.
- **Pre-Requisites:**
  - None
- **Explanation:**
  - With this feature the Tool will try to look for all symbolic links within `<FOLDER_TO_FIX>` and will try to find the target file within the same folder.
- **Example of use:**
  ```
  ./PhotoMigrator --fix-symlinks-broken ./OUTPUT_FOLDER 
  ```
  With this example, the Tool will look for all symbolic links within `OUTPUT_FOLDER` and if any is broken,
  the Tool will try to fix it finding the target of the symlink within the same `OUTPUT_FOLDER` structure.

> [!TIP]  
> This is useful when you run the Tool without the argument _**`-gnsa, --google-no-symbolic-albums`**_ to create symbolic Albums instead of duplicate copies of the files contained on '<ALBUMS_FOLDER>'.  
> 
> If you run the Tool without this argument and after that you rename original folders or change the folder structure of the OUTPUT_FOLDER, your symbolic links may be broken, and you will need to use this feature to fix them.


# <span style="color:blue"> Folder Rename Content Based (Extra Feature)</span>
- **From:** v2.0.0
- **Usage:**
  - To run this feature you have to use the argument `-renFldcb, --rename-folders-content-based <ALBUMS_FOLDER>`.
  - where `<ALBUMS_FOLDER>` is the folder that contains all the Albums subfolders to rename.
- **Pre-Requisites:**
  - None
- **Explanation:**
  - With this feature, the Tool will rename all Albums subfolders (if they contain a flatten file structure) and homogenize all your Albums names with this format:  
  - New Album Name: **`yyyy - Album Name` or `yyyy-yyyy - Album Name`**  
  - where `yyyy` is the year of the files contained in each Album folder (if more than one year is found, then `yyyy-yyyy` will indicate the range of years for the files contained in the Album folder.
- **Example of use:**
  ```
  ./PhotoMigrator.run ---rename-folders-content-based ./MyLocalPhotoLibrary
  ```
  In this example, the Tool will Process your Library of photos in folder `./MyLocalPhotoLibrary` (need to be unzipped), and will rename all the subfolders found on to homogenize all the folder's name with the following template:  
  `yyyy - Cleaned Subfolder Name` or `yyyy-yyyy - Cleaned Subfolder Name`  
   where, 
  - `yyyy` is the year of the assets found in that folder
  - `yyyy-yyyy` is the range of years for the assets found (if more than one year is found)  
  - `Cleaned Subfolder Name` is the name of the folder cleaned and homogenized.  

> [!TIP]  
> Use this feature before to upload this folder to any Photo Cloud service in order to have a clean Albums structure in your Photo Cloud service database.  
> 
> This feature is useful if you want to Upload all your Albums to a new Cloud Service and you would like to start with all the new Albums in a cleaner homogeneous way.  

> [!CAUTION]  
> This Feature will modify the original subfolder names found in <ALBUMS_FOLDER>. 
> 
> If you don't want to lose your original subfolder names, you should make a backup before to run this feature.

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)


---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
