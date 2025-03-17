> [!NOTE]
> ## <span style="color:green">Immich Photos Support</span>
>From version 3.0.0 onwards, the script can connect to your Immich Photos account with your credentials or API. The credentials/API need to be loaded from 'Config.ini' file and will have this format:
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
> - Upload Album(s)
> - Upload ALL (from folder)
> - Download Album(s)
> - Download ALL (into folder)
> - Remove ALL Assets
> - Remove ALL Albums
> - Remove Empty Albums
> - Remove Duplicates Albums
> - Remove Orphans Assets

### <span style="color:blue">Delete Empty Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Empty Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Empty Albums in Immich Photos database.  

If any Empty Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-remove-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will look for all Duplicates Albums in Immich Photos database.  

If any Duplicated Album is found, the script will remove it from Immich Photos.  

To execute this Extra Mode, you can use the Flag: _'--immich-remove-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-immich-photos
```
With this example, the script will connect to Immich Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will upload all the assets contained in <INPUT_FOLDER> that are supported by Immich Photos.  

The folder <INPUT_FOLDER> can be passed using the Flag: _'-iuf,  --immich-upload-folder <INPUT_FOLDER>'_ 

> [!IMPORTANT]
> <INPUT_FOLDER> should be stored within your Immich Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <INPUT_FOLDER> should have been already indexed by Immich Photos before you can add them to a Immich Photos Album.  
>
>You can check if the files have been already indexed accessing Immich Photos mobile app or Immich Photos web portal and change to Folder View.  
>
>If you can't see your <INPUT_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Immich Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --immich-upload-folder ./MyLibrary
```
With this example, the script will connect to Immich Photos database and process the folder ./MyLibrary and will upload all supported assets found on it.


### <span style="color:blue">Upload Albums into Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Create Albums in Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Immich Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Immich Photos and with the same Album name as Album folder.  

The folder <ALBUMS_FOLDER> can be passed using the Flag: _'-iua,  --immich-upload-albums <ALBUMS_FOLDER>'_ 

> [!IMPORTANT]
> <ALBUMS_FOLDER> should be stored within your Immich Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <ALBUMS_FOLDER> should have been already indexed by Immich Photos before you can add them to a Immich Photos Album.  
>
>You can check if the files have been already indexed accessing Immich Photos mobile app or Immich Photos web portal and change to Folder View.  
>
>If you can't see your <ALBUMS_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Immich Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --immich-upload-albums ./My_Albums_Folder
```
With this example, the script will connect to Immich Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Immich Photos, will create a new Album in Immich Photos with the same name of the Album Folder


### <span style="color:blue">Download Albums from Immich Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Download Albums from Immich Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect to Immich Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder.  

To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums "album1", "album2", "album3".  

You can also use wildcarts. i.e --immich-download-albums *Mery*

To extract ALL Albums within in Immich Photos database use 'ALL' as <ALBUMS_NAME>.  

The album(s) name <ALBUMS_NAME> can be passed using the Flag: _'-ida,  --immich-download-albums <ALBUMS_NAME>'_  

> [!IMPORTANT]
> <ALBUMS_NAME> should exist within your Immich Photos Albums database, otherwise it will no extract anything. 
> Extraction will be done in background task, so it could take time to complete. Even if the Script finish with success the extraction process could be still running on background, so take this into account.

Example of use:
```
./CloudPhotoMigrator.run --immich-download-albums "Album 1", "Album 2", "Album 3"
```
With this example, the script will connect to Immich Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Immich_Photos_Albums' folder

