# <span style="color:green">🖼️ Synology Photos Management</span>

From version 2.0.0 onwards, the Tool can connect to your Synology NAS and login into Synology Photos App with your credentials. 

### Features included:
1. Upload Album(s) (from folder)
2. Download Album(s) (into folder)
3. Upload ALL (from folder)
4. Download ALL (into folder)
5. Remove ALL Assets
6. Remove ALL Albums
7. Remove Albums by Name Pattern
8. Rename Albums by Name Pattern
9. Remove Empty Albums
10. Remove Duplicates Albums
11. Merge Duplicates Albums

You can apply different filters on all above features to filter assets from Synology Photos.  

The available filters are: 
   - **by Type:**
     - argument: `-type, --filter-by-type`
       - Valid values are [`image`, `video`, `all`]
   - **by Dates:**
     - arguments:
       - `-from, --filter-from-date`
       - `-to, --filter-to-date`
     - Valid values are in one of those formats: 
       - `dd/mm/yyyy`
       - `dd-mm-yyyy`
       - `yyyy/mm/dd`
       - `yyyy-mm-dd`
       - `mm/yyyy`
       - `mm-yyyy`
       - `yyyy/mm`
       - `yyyy-mm`
       - `yyyy`
   - **by Country:**
     - argument: `-country, --filter-by-country`
       - Valid values are any existing country in the `<SOURCE>` client.
   - **by City:**
     - argument: `-city, --filter-by-city`
       - Valid values are any existing city in the `<SOURCE>` client.
   - **by Person:**
     - argument: `-person, --filter-by-person`
       - Valid values are any existing person in the `<SOURCE>` client.

The credentials/API Key need to be loaded from the `Config.ini` file that  have this format:

#### <span style="color:green">Example 'Config.ini' for Immich Photos:</span>

```
# Configuration for Synology Photos
[Synology Photos]
SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
SYNOLOGY_USERNAME_3         = username_3                                    # Account 3: Your username for Synology Photos
SYNOLOGY_PASSWORD_3         = password_3                                    # Account 3: Your password for Synology Photos
```

> [!NOTE]
> To use all these features, it is mandatory to use the argument _**`--client=synology`**_ to specify Synology Photos as the service that you want to connect.  
> 
> If you want to connect to an account ID different that 1 (suffixed with _2 or _3) you can use the argument _**`-id, -account-id=[1-3]`**_ to specify the account 2 or 3 as needed. 

> [!IMPORTANT]  
> If your Synology Photo Account requires 2FA Authentication, you must use the argument _**`-OTP, --one-time-password`**_ in order to enable the OTP Token request during authentication process. 


## <span style="color:blue">Upload Albums (from Local Folder) into Synology Photos:</span>
- **From:** v2.0.0 
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-uAlb, --upload-albums \<ALBUMS_FOLDER>`**_
  - Where `<ALBUMS_FOLDER>` is the folder that contains all the Albums that you want to upload,
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will create one Album per each Subfolder found in \<ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synoogy --upload-albums ./My_Albums_Folder
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder `./My_Albums_Folder` and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder
  

## <span style="color:blue">Download Albums from Synology Photos:</span>
- **From:** v2.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-dAlb, --download-albums <ALBUMS_NAME>`**_ in combination with the argument _**`-o, --output-folder <OUTPUT_FOLDER>`**_ (mandatory argument for this feature)
  - Where,
  - `<ALBUMS_NAME>` is a list of Albums names that you want to download.
  - `<OUTPUT_FOLDER>` is the folder where you want to download the Albums.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and Download those Album(s) whose name is in `<ALBUMS_NAME>` to the folder `<OUTPUT_FOLDER>`.
  - To download ALL Albums use `ALL` as `<ALBUMS_NAME>`.
  - To download all albums mathing any pattern you can use patterns in `<ALBUMS_NAME>`, i.e: `--download-albums 'dron*'` to download all albums starting with the word 'dron' followed by other(s) words.
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: `--download-albums 'album1', 'album2', 'album3'`.
- **Example of use:**
  ```
  ./PhotoMigrator.run `--client=synology --download-albums "Album 1", "Album 2", "Album 3"`
  ```
  With this example, the Tool will connect to your Synology Photos account and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of `Synology_Photos_Albums` folder

> [!WARNING]  
> \<ALBUMS_NAME> should exist within your Synology Photos Albums database, otherwise it will not extract anything. 


## <span style="color:blue">Upload All (from Local Folder) into Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-uAll, --upload-all \<INPUT_FOLDER>`**_
  - Where `<INPUT_FOLDER>` is the folder that contains all the assets that you want to upload.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will upload all the assets contained in \<INPUT_FOLDER> that are supported by Synology Photos.  
  - If you want to create Albums for some specific subfolders you have two options:
    1. Move all the Albums subfolders into a `<INPUT_FOLDER>/<ALBUMS_FOLDER>`, in this way the Tool will consider all the subfolders inside as an Album, and will create an Album in Synology Photos with the same name as the subfolder, associating all the assets inside to it.
    2. Use the complementary argument _**`-AlbFolder, --albums-folders \<ALBUMS_FOLDER>`**_, in this way the Tool will create Albums also for each subfolder found in `<ALBUMS_FOLDER>` (apart from those found inside `<INPUT_FOLDER>/Albums`)
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --upload-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder ./MyLibrary and will upload all supported assets found on it, creating a new Album per each subfolder found within `./MyLibrary/Albums` folder.


## <span style="color:blue">Download All from Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-dAll, --download-all \<OUTPUT_FOLDER>`**_
  - Where `<OUTPUT_FOLDER>` is the folder where you want to download all your assets.
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and will download all the Album and Assets without Albums into the folder `<OUTPUT_FOLDER>`.
  - All Albums will be downloaded within a subfolder of `<OUTPUT_FOLDER>/Albums` with the same name of the Album and all files will be flattened into it.
  - Assets with no Albums associated will be downloaded within a subfolder called `<OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>` and will have a `year/month` structure inside.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --download-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Synology Photos account and download ALL your library into the local folder ./MyLibrary.
  

## <span style="color:blue">Remove All Assets from Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-rAll, --remove-all-assets`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url.
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove ALL the assets and Albums found.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --remove-all-assets
  ```
  With this example, the Tool will connect to Synology Photos account and will remove all assets found (including Albums).

> [!CAUTION]  
> This process is irreversible and will clean all from your Synology Photos account. Use it if you are completely sure of what you are doing.
  

## <span style="color:blue">Remove All Albums from Synology Photos:</span>
- **From:** v3.0.0 
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`-rAllAlb, --remove-all-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all the Albums found.
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
  - Optionally ALL the Assets associated to each Album can be removed If you also include the complementary argument _**`-rAlbAsset, --remove-albums-assets`**_
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --remove-all-albums --remove-albums-assets
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Albums found (including all the assets contained on them, because we are using the complementary argument).

> [!CAUTION]  
> This process is irreversible and will clean all the Albums (and optionally also all the assets included) from your Synology Photos account. Use it if you are completely sure of what you are doing.


## <span style="color:blue">Remove Albums by Name Pattern from Synology Photos:</span>
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-albums \<ALBUMS_NAME_PATTERN>`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will rename all Albums whose name matches with the provided pattern.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
  - Optionally ALL the Assets associated to each removed Album can be removed If you also include the complementary argument _**`-rAlbAsset, --remove-albums-assets`**_
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --rename-albums "\d{4}-\d{2}-\d{2}" --remove-albums-assets
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Albums whose name contains a date like this ("2023-08-15 - Vacation photos"), including all the assets contained on them, because we are using the complementary argument.

> [!CAUTION]  
> This process is irreversible and will remove all the Albums (and optionally also all the assets included) whose name matches with the provided pattern from your Synology Photos account. Use it if you are completely sure of what you are doing.
      

## <span style="color:blue">Rename Albums by Name Pattern from Synology Photos:</span>
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--rename-albums \<ALBUMS_NAME_PATTERN>, \<ALBUMS_NAME_REPLACEMENT_PATTERN>`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will rename all Albums whose name matches with the provided pattern.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be renamed.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synoogy --rename-albums "\d{4}-\d{2}-\d{2}", "DATE"
  ```
  With this example, the Tool will connect to your Synology Photos account and will rename all Albums whose name contains a date like this ("2023-08-15 - Vacation photos") replacing the date with the string "DATE", as a result the new album name would be: "DATE - Vacation photos".
   

## <span style="color:blue">Remove Empty Albums from Synology Photos:</span>
- **From:** v2.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-empty-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Empty Albums found.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --remove-empty-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Empty Albums found.


## <span style="color:blue">Remove Duplicates Albums from Synology Photos:</span>
- **From:** v2.0.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _**`--remove-duplicates-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Duplicates Albums found except the first one (but will not remove the assets associated to them, because they will still be associated with the first Album).  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be removed.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --remove-duplicates-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Duplicates Albums found except the first one.


## <span style="color:blue">Merge Duplicates Albums from Synology Photos:</span>
- **From:** v3.3.0
- **Usage:**
  - To run this feature, first, is mandatory that you set `synology` as client using the argument _**`-client=synology`**_ or _**`--client=synology`**_
  - Also, you have to use the argument _`--merge-duplicates-albums`**_
- **Pre-Requisites:**
  - Configure properly the file `Config.ini` to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Duplicates Albums found except the most relevant one (with highest number of assets) and will transfer all the assets associated to the other albums into the main one.  
  - If you specify any date filter with arguments _**`-from, --filter-from-date`**_ or _**`-to, --filter-to-date`**_ then, only those albums whose creation date matches with the filters will be merged.
- **Example of use:**
  ```
  ./PhotoMigrator.run --client=synology --merge-duplicates-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Duplicates Albums found except the first one transferring all the assets from the removed albums into the main one.

## ⚙️ Config.ini
You can see how to configure the Config.ini file in this help section:
[Configuration File](https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md) 

---

## 🏠 [Back to Main Page](https://github.com/jaimetur/PhotoMigrator/blob/main/README.md)


---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
