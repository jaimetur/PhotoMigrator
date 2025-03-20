# <span style="color:green">Synology Photos Management Documentation:</span>

>[!NOTE]
>## <span style="color:green">Synology Photos Support</span>
>From version 2.0.0 onwards, the Tool can connect to your Synology NAS and login into Synology Photos App with your credentials. The credentials need to be loaded from 'Config.ini' file and will have this format:
>
>>#### <span style="color:green">Example 'Config.ini' for Synology Photos:</span>
>>
>>```
>># Configuration for Synology Photos
>>[Synology Photos]
>>SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>>SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
>>SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
>>SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
>>SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
>>```
>### Features included:
> 1. Upload Album(s) (from folder)
> 2. Download Album(s) (into folder)
> 3. Upload ALL (from folder)
> 4. Download ALL (into folder)
> 5. Remove ALL Assets
> 6. Remove ALL Albums
> 7. Remove Empty Albums
> 8. Remove Duplicates Albums


## <span style="color:blue">Upload Albums (from Local Folder) into Synology Photos:</span>
- **From:** v2.0.0 
- **Usage:**
  - To run this feature you have to use the flag _'-suAlb,  --synology-upload-albums <ALBUMS_FOLDER>'_
  - Where \<ALBUMS_FOLDER> is the folder that contains all the Albums that you want to upload,
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-upload-albums ./My_Albums_Folder
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder
  

## <span style="color:blue">Download Albums from Synology Photos:</span>
- **From:** v2.3.0
- **Usage:**
  - To run this feature you have to use the flag _'-sdAlb,  --synology-download-albums <ALBUMS_NAME'_ in combination with the flag _'-o, --output-folder <OUTPUT_FOLDER>'_ (mandatory argument for this feature)
  - Where,
  - \<ALBUMS_NAME> is a list of Albubs names that you want to download.
  - \<OUTPUT_FOLDER> is the folder where you want to download the Albums.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder <OUTPUT_FOLDER>.
  - To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
  - To download all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --synology-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words.
  - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums 'album1', 'album2', 'album3'.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-download-albums "Album 1", "Album 2", "Album 3"
  ```
  With this example, the Tool will connect to your Synology Photos account and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Synology_Photos_Albums' folder

> [!IMPORTANT]
> ⚠ <ALBUMS_NAME> should exist within your Synology Photos Albums database, otherwise it will not extract anything. 


## <span style="color:blue">Upload All (from Local Folder) into Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-suAll,  --synology-upload-all <INPUT_FOLDER>'_
  - Where \<INPUT_FOLDER> is the folder that contains all the assets that you want to upload.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will upload all the assets contained in <INPUT_FOLDER> that are supported by Synology Photos.  
  - If you want to create Albums for some specific subfolders you have two options:
    1. Move all the Albums subfolders into a '<INPUT_FOLDER>/Albums', in this way the Tool will consideer all the subfolders inside as an Album, and will create an Album in Synology Photos with the same name as the subfolder, associating all the assets inside to it.
    2. Use the complementary argument _'-AlbFld, --albums-folders <ALBUMS_FOLDER>'_, in this way the Tool will create Albums also for each subfolder found in '<ALBUMS_FOLDER>' (apart from those found inside '<INPUT_FOLDER>/Albums')
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-upload-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Synology Photos account and process the folder ./MyLibrary and will upload all supported assets found on it, creating a new Album per each subfolder found within './MyLibrary/Albums' folder.


## <span style="color:blue">Download All from Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-sdAll, --synology-download-all <OUTPUT_FOLDER>'_
  - Where \<OUTPUT_FOLDER> is the folder where you want to download all your assets.
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect to Synology Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>.
  - All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.
  - Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside.
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-download-all ./MyLibrary
  ```
  With this example, the Tool will connect to your Synology Photos account and download ALL your library into the local folder ./MyLibrary.
  

## <span style="color:blue">Remove All Assets from Synology Photos:</span>
- **From:** v3.0.0
- **Usage:**
  - To run this feature you have to use the flag _'-srAll, --synology-remove-all-assets'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove ALL the assets and Albums found.  
      
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-remove-all-assets
  ```
  With this example, the Tool will connect to Synology Photos account and will remove all assets found (including Albums).

> [!IMPORTANT]
> ⚠ This process is irreversible and will clean all from your Synology Photos account. Use it if you are completelly sure of what you are doing.
  

## <span style="color:blue">Remove All Albums from Synology Photos:</span>
- **From:** v3.0.0 
- **Usage:**
  - To run this feature you have to use the flag _'-srAllAlb, --synology-remove-all-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all the Albums found.
  - Optionally ALL the Assets associated to each Album can be removed If you also include the complementary argument _'-rAlbAss, --remove-albums-assets'_
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-remove-all-albums --remove-albums-assets
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Albums found (including all the assets contained on them, because we are using the complementary flag).

 
> This process is irreversible and will clean all the Albums (and optionally also all the assets included) from your Synology Photos account. Use it if you are completelly sure of what you are doing.
      

## <span style="color:blue">Remove Empty Albums from Synology Photos:</span>
- **From:** v2.0.0
- **Usage:**
  - To run this feature you have to use the flag _'--synology-remove-empty-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Empty Albums found.  
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-remove-empty-albums
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Empty Albums found.


## <span style="color:blue">Remove Duplicates Albums from Synology Photos:</span>
- **From:** v2.0.0
- **Usage:**
  - To run this feature you have to use the flag _'--synology-remove-duplicates-albums'_
- **Pre-Requisites:**
  - Configure properly the file 'Config.ini' to include your Synology account credentials and url. 
- **Explanation:**
  - The Tool will connect automatically to your Synology Photos account and will remove all Duplicates Albums found except the first one (but will not remove the assets associated to them, because they will still be associated with the first Album).  
- **Example of use:**
  ```
  ./CloudPhotoMigrator.run --synology-remove-duplicates-albums'
  ```
  With this example, the Tool will connect to your Synology Photos account and will remove all Duplicates Albums found except the first one.
  


## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  