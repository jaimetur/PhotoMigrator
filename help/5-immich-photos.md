# <span style="color:green">Immich Photos Management:</span>

>[!NOTE]
>## <span style="color:green">Immich Photos Support</span>
>From version 3.0.0 onwards, the Tool can connect to your Immich Photos account with your credentials or using a pre-created API Key.  
>### Features included:
> 1. Upload Album(s) (from folder)
> 2. Download Album(s) (into folder)
> 3. Upload ALL (from folder)
> 4. Download ALL (into folder)
> 5. Remove ALL Assets
> 6. Remove ALL Albums
> 7. Remove Empty Albums
> 8. Remove Duplicates Albums
> 9. Remove Orphans Assets
> 
> You can apply filters to filter assets to download from Immich Photos using any Download feature included.  
> 
> The available filters are: 
>    - by Type
>      - flag: -type, --type
>        - Valid values are [image, video, all]
>    - by Dates
>      - flags
>        - from-date
>        - to-date
>      - Valid values are in one of those formats: 
>        - dd/mm/yyyy
>        - dd-mm-yyyy
>        - yyyy/mm/dd
>        - yyyy-mm-dd
>        - mm/yyyy
>        - mm-yyyy
>        - yyyy/mm
>        - yyyy-mm
>        - yyyy 
>    - by Country
>      - flag: -country, --country
>        - Valid values are any existing country in the \<SOURCE> client.
>    - by City
>      - flag: -city, --city
>        - Valid values are any existing city in the \<SOURCE> client.
>    - by Person
>      - flag: -person, --person
>        - Valid values are any existing person in the \<SOURCE> client.
>
>The credentials/API Key need to be loaded from the 'Config.ini' file that  have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Immich Photos:</span>
>>
>>```
>># Configuration for Immich Photos
>>[Immich Photos]
>>IMMICH_URL                  = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>>IMMICH_API_KEY_ADMIN        = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>
>>IMMICH_API_KEY_USER_1       = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>IMMICH_USERNAME_1           = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
>>IMMICH_PASSWORD_1           = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
>>
>>IMMICH_API_KEY_USER_2       = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>>IMMICH_USERNAME_2           = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
>>IMMICH_PASSWORD_2           = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
>>```


## <span style="color:blue">Upload Albums (from Local Folder) into Immich Photos:</span>
- **From:** v3.0.0 
- **Usage:**
  - To run this feature you have to use the flag _'-iuAlb,  --immich-upload-albums <ALBUMS_FOLDER>'_
  - Where \<ALBUMS_FOLDER> is the folder that contains all the Albums that you want to upload,
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Immich Photos and with the same Album name as Album folder.

- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-upload-albums ./My_Albums_Folder
  ```
  With this example, the Tool will connect to your Immich Photos account and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Immich Photos, will create a new Album in Immich Photos with the same name of the Album Folder
    

## <span style="color:blue">Download Albums from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-idAlb,  --immich-download-albums <ALBUMS_NAME'_ in combination with the flag _'-o, --output-folder <OUTPUT_FOLDER>'_ (mandatory argument for this feature)
  - Where,
  - \<ALBUMS_NAME> is a list of Albubs names that you want to download.
  - \<OUTPUT_FOLDER> is the folder where you want to download the Albums.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect to Immich Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder <OUTPUT_FOLDER>.
  - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
  - To download all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --immich-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words.
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums 'album1', 'album2', 'album3'.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-download-albums "Album 1", "Album 2", "Album 3"
  ```
  With this example, the Tool will connect to your Immich Photos account and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Immich_Photos_Albums' folder

> [!WARNING]  
> <ALBUMS_NAME> should exist within your Immich Photos Albums database, otherwise it will not extract anything. 
  

## <span style="color:blue">Upload All (from Local Folder) into Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-iuAll,  --immich-upload-all <INPUT_FOLDER>'_
  - Where \<INPUT_FOLDER> is the folder that contains all the assets that you want to upload.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will upload all the assets contained in <INPUT_FOLDER> that are supported by Immich Photos.  
  - If you want to create Albums for some specific subfolders you have two options:
    1. Move all the Albums subfolders into a '<INPUT_FOLDER>/Albums', in this way the Tool will consideer all the subfolders inside as an Album, and will create an Album in Immich Photos with the same name as the subfolder, associating all the assets inside to it.
    2. Use the complementary argument _'-AlbFld, --albums-folders <ALBUMS_FOLDER>'_, in this way the Tool will create Albums also for each subfolder found in '<ALBUMS_FOLDER>' (apart from those found inside '<INPUT_FOLDER>/Albums')
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-upload-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Immich Photos account and process the folder ./MyLibrary and will upload all supported assets found on it, creating a new Album per each subfolder found within './MyLibrary/Albums' folder.


## <span style="color:blue">Download All from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-idAll, --immich-download-all <OUTPUT_FOLDER>'_
  - Where \<OUTPUT_FOLDER> is the folder where you want to download all your assets.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>.
  - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.
  - Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-download-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Immich Photos account and download ALL your library into the local folder ./MyLibrary.
  

## <span style="color:blue">Remove All Assets from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-irAll, --immich-remove-all-assets'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will remove ALL the assets and Albums found.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-remove-all-assets
  ```
  With this example, the Tool will connect to Immich Photos account and will remove all assets found (including Albums).

> [!CAUTION]  
> This process is irreversible and will clean all from your Immich Photos account. Use it if you are completelly sure of what you are doing.
  

## <span style="color:blue">Remove All Albums from Immich Photos:</span>
- **From:** v3.0.0 
- **Usage:**
  - To run this feature you have to use the flag _'-irAllAlb, --immich-remove-all-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will remove all the Albums found.
  - Optionally ALL the Assets associated to each Album can be removed If you also include the complementary argument _'-rAlbAss, --remove-albums-assets'_
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-remove-all-albums --remove-albums-assets
  ```
  With this example, the Tool will connect to your Immich Photos account and will remove all Albums found (including all the assets contained on them, because we are using the complementary flag).

> [!CAUTION]  
> This process is irreversible and will clean all the Albums (and optionally also all the assets included) from your Immich Photos account. Use it if you are completelly sure of what you are doing.
    

## <span style="color:blue">Remove Empty Albums from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'--immich-remove-empty-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will remove all Empty Albums found.  
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-remove-empty-albums
  ```
  With this example, the Tool will connect to your Immich Photos account and will remove all Empty Albums found.


## <span style="color:blue">Remove Duplicates Albums from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'--immich-remove-duplicates-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Immich Photos account and will remove all Duplicates Albums found except the first one (but will not remove the assets associated to them, because they will still be associated with the first Album).  
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-remove-duplicates-albums'
  ```
  With this example, the Tool will connect to your Immich Photos account and will remove all Duplicates Albums found except the first one.


## <span style="color:blue">Remove Orphans Assets from Immich Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'--immich-remove-orphan-assets'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Immich account credentials and the administrator credential (mandatory for this feature)
- **Explanation:**
  - An Orphan asset is an asset that is in your Immich Photos account but is pointing to a non-existing file.  
  - The Tool will connect automatically to your Immich Photos account and will remove all Orphan assets found.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --immich-remove-orphan-assets
  ```
  With this example, the Tool will connect to your Immich Photos account and will remove all Orphan Assets found.
  

## Config.ini
Youn can see how to configure the Config.ini file in this help section:
[Configuration File](/help/0-configuration-file.md) 

---
## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
