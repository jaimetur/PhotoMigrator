# <span style="color:green">Immich Photos Management:</span>

> [!NOTE]
> ## <span style="color:green">Immich Photos Support</span>
>From version 3.0.0 onwards, the Tool can connect to your Immich Photos account with your credentials or using a pre-created API Key.  
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
>>
>>IMMICH_FILTER_ARCHIVE       = False                                         # Optional: Used as Filter Criteria for Assets downloading (True/False)
>>IMMICH_FILTER_FROM          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>>IMMICH_FILTER_TO            = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>>IMMICH_FILTER_COUNTRY       = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: Spain)
>>IMMICH_FILTER_CITY          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Madrid', 'Málaga'])
>>IMMICH_FILTER_PERSON        = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Mery', 'James'])
>>```
>### Features included:
> - Upload Album(s) (from folder)
> - Download Album(s) (into folder)
> - Upload ALL (from folder)
> - Download ALL (into folder)
> - Remove ALL Assets
> - Remove ALL Albums
> - Remove Empty Albums
> - Remove Duplicates Albums
> - Remove Orphans Assets

## <span style="color:blue">Upload Albums (from Local Folder) into Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Create Albums in Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect automatically to your Immich Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Immich Photos and with the same Album name as Album folder.  
- The folder <ALBUMS_FOLDER> can be passed using the Flag: _'-iuAlb,  --immich-upload-albums <ALBUMS_FOLDER>'_

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-upload-albums ./My_Albums_Folder
  ```
  With this example, the Tool will connect to Immich Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Immich Photos, will create a new Album in Immich Photos with the same name of the Album Folder
  

## <span style="color:blue">Download Albums from Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Download Albums from Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect to Immich Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this mode).
- To download ALL Albums use 'ALL' as <ALBUMS_NAME>.
- To download all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --immich-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words.
- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums 'album1', 'album2', 'album3'.
> [!IMPORTANT]
> <ALBUMS_NAME> should exist within your Immich Photos Albums database, otherwise it will no extract anything. 

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-download-albums "Album 1", "Album 2", "Album 3"
  ```
  With this example, the Tool will connect to Immich Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Immich_Photos_Albums' folder


## <span style="color:blue">Upload All (from Local Folder) into Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Upload Folder into Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect automatically to your Immich Photos database and will upload all the assets contained in <INPUT_FOLDER> that are supported by Immich Photos.  
- The folder <INPUT_FOLDER> can be passed using the Flag: _'-iuAll,  --immich-upload-all <INPUT_FOLDER>'_

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-upload-all ./MyLibrary
  ```
  With this example, the Tool will connect to Immich Photos database and process the folder ./MyLibrary and will upload all supported assets found on it, creating a new Album per each subfolder found within '<INPUT_FOLDER>/Albums' folder.


## <span style="color:blue">Download All from Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Download All from Immich Photos'.
- If you configure properly the file 'Config.ini' and execute this Mode, The Tool will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>.
- To execute this feature, you can use the Flag: _'-idAll, --immich-download-all <OUTPUT_FOLDER>'_
- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.
- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside.

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-download-all ./MyLibrary
  ```
  With this example, the Tool will connect to Immich Photos database and download ALL your library into the local folder ./MyLibrary.
  

## <span style="color:blue">Remove All Assets from Immich Photos:</span>
- From version 3.0.0 onwards, the Tool supports a feature to 'Remove All Assets from Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this feature, the Tool will connect automatically to your Immich Photos database and will remove ALL the assets and Albums found.  
- To execute this feature, you can use the Flag: _'-irAll, --immich-remove-all-assets'_
> [!IMPORTANT]
> This process is irreversible and will clean all from your Immich Photos account. Use it if you are completelly sure of what you are doing.
      
  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-remove-duplicates-albums
  ```
  With this example, the Tool will connect to Immich Photos database and will delete all Duplicates Albums found.
  

## <span style="color:blue">Remove All Albums from Immich Photos:</span>
- From version 3.0.0 onwards, the Tool can be executed a feature to 'Remove All Albums from Immich Photos' from Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this feature, the Tool will connect automatically to your Immich Photos database and will remove ALL the Albums found.
- To execute this feature, you can use the Flag: _'-irAll, --immich-remove-all-assets'_
- Optionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets'
> [!IMPORTANT]
> This process is irreversible and will clean all the Albums (and optionally also all the assets included) from your Immich Photos account. Use it if you are completelly sure of what you are doing.
      
  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-remove-duplicates-albums
  ```
  With this example, the Tool will connect to Immich Photos database and will delete all Duplicates Albums found.


## <span style="color:blue">Delete Empty Albums in Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Delete Empty Albums from Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect automatically to your Immich Photos database and will look for all Empty Albums in Immich Photos database.  
- If any Empty Album is found, the Tool will remove it from Immich Photos.  
- To execute this feature, you can use the Flag: _'--immich-remove-empty-albums'_

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --delete-empty-albums-immich-photos
  ```
  With this example, the Tool will connect to Immich Photos database and will delete all Empty Albums found.


## <span style="color:blue">Delete Duplicates Albums in Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Delete Duplicates Albums from Immich Photos'. 
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect automatically to your Immich Photos database and will look for all Duplicates Albums in Immich Photos database.  
- If any Duplicated Album is found, the Tool will remove it from Immich Photos.  
- To execute this feature, you can use the Flag: _'--immich-remove-duplicates-albums'_

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --delete-duplicates-albums-immich-photos
  ```
  With this example, the Tool will connect to Immich Photos database and will delete all Duplicates Albums found.


## <span style="color:blue">Delete Orphans Assets in Immich Photos:</span>
- From version 3.0.0 onwards, the Tool has a feature to 'Delete Orphans Assets from Immich Photos'.  
- An Orphan asset is an asset that is in your Immich Photos database but is pointing to a non-existing file.  
- If you configure properly the file 'Config.ini' and execute this Mode, the Tool will connect automatically to your Immich Photos database and will look for Orphan assets  Duplicates Albums in Immich Photos database.
- If any Duplicated Album is found, the Tool will remove it from Immich Photos.
- To execute this feature, you can use the Flag: _'--immich-remove-orphan-assets'_

  ### Example of use:
  ```
  ./CloudPhotoMigrator.run --immich-remove-orphan-assets
  ```
  With this example, the Tool will connect to Immich Photos database and will delete all Orphan Assets found.
  

## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
