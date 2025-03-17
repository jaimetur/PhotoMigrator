## <span style="color:green">Synology Photos Management Documentation:</span>

>[!NOTE]
>## <span style="color:green">Synology Photos Support</span>
>From version 2.0.0 onwards, the script can connect to your Synology NAS and login into Synology Photos App with your credentials. The credentials need to be loaded from 'Config.ini' file and will have this format:
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
> - Upload Album(s)
> - Upload ALL (from folder)
> - Download Album(s)
> - Download ALL (into folder)
> - Remove ALL Assets
> - Remove ALL Albums
> - Remove Empty Albums
> - Remove Duplicates Albums

### <span style="color:blue">Delete Empty Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Empty Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Empty Albums in Synology Photos database.  

If any Empty Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-remove-empty-albums'_ 

Example of use:
```
./CloudPhotoMigrator.run --delete-empty-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Empty Albums found.


### <span style="color:blue">Delete Duplicates Albums in Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Delete Duplicates Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will look for all Duplicates Albums in Synology Photos database.  

If any Duplicated Album is found, the script will remove it from Synology Photos.  

To execute this Extra Mode, you can use the Flag: _'--synology-remove-duplicates-albums'_

Example of use:
```
./CloudPhotoMigrator.run --delete-duplicates-albums-synology-photos
```
With this example, the script will connect to Synology Photos database and will delete all Duplicates Albums found.


### <span style="color:blue">Upload Folder into Synology Photos:</span>
From version 3.0.0 onwards, the script can be executed in 'Upload Folder into Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will upload all the assets contained in <INPUT_FOLDER> that are supported by Synology Photos.  

The folder <INPUT_FOLDER> can be passed using the Flag: _'-suf,  --synology-upload-folder <INPUT_FOLDER>'_ 

> [!IMPORTANT]
> <INPUT_FOLDER> should be stored within your Synology Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <INPUT_FOLDER> should have been already indexed by Synology Photos before you can add them to a Synology Photos Album.  
>
>You can check if the files have been already indexed accessing Synology Photos mobile app or Synology Photos web portal and change to Folder View.  
>
>If you can't see your <INPUT_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Synology Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --synology-upload-folder ./MyLibrary
```
With this example, the script will connect to Synology Photos database and process the folder ./MyLibrary and will upload all supported assets found on it.


### <span style="color:blue">Upload Albums into Synology Photos:</span>
From version 2.0.0 onwards, the script can be executed in 'Create Albums in Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect automatically to your Synology Photos database and will create one Album per each Subfolder found in <ALBUMS_FOLDER> that contains at least one file supported by Synology Photos and with the same Album name as Album folder.  

The folder <ALBUMS_FOLDER> can be passed using the Flag: _'-sua,  --synology-upload-albums <ALBUMS_FOLDER>'_ 

> [!IMPORTANT]
> <ALBUMS_FOLDER> should be stored within your Synology Photos main folder in your NAS. Typically, it is '/volume1/homes/your_username/Photos' and all files within <ALBUMS_FOLDER> should have been already indexed by Synology Photos before you can add them to a Synology Photos Album.  
>
>You can check if the files have been already indexed accessing Synology Photos mobile app or Synology Photos web portal and change to Folder View.  
>
>If you can't see your <ALBUMS_FOLDER> most probably is because it has not been indexed yet or because you didn't move it within Synology Photos root folder. 

Example of use:
```
./CloudPhotoMigrator.run --synology-upload-albums ./My_Albums_Folder
```
With this example, the script will connect to Synology Photos database and process the folder ./My_Albums_Folder and per each subfolder found on it that contains at least one file supported by Synology Photos, will create a new Album in Synology Photos with the same name of the Album Folder


### <span style="color:blue">Download Albums from Synology Photos:</span>
From version 2.3.0 onwards, the script can be executed in 'Download Albums from Synology Photos' Mode. 

If you configure properly the file 'Config.ini' and execute this Extra Mode, the script will connect to Synology Photos and Download those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder.  

To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3".  

You can also use wildcarts. i.e --synology-download-albums *Mery*

To extract ALL Albums within in Synology Photos database use 'ALL' as <ALBUMS_NAME>.  

The album(s) name <ALBUMS_NAME> can be passed using the Flag: _'-sda,  --synology-download-albums <ALBUMS_NAME>'_  

> [!IMPORTANT]
> <ALBUMS_NAME> should exist within your Synology Photos Albums database, otherwise it will no extract anything. 
> Extraction will be done in background task, so it could take time to complete. Even if the Script finish with success the extraction process could be still running on background, so take this into account.

Example of use:
```
./CloudPhotoMigrator.run --synology-download-albums "Album 1", "Album 2", "Album 3"
```
With this example, the script will connect to Synology Photos database and extract the Albums "Album 1", "Album 2", "Album 3" with all the photos and videos included on them into a subfolder of 'Synology_Photos_Albums' folder


## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  