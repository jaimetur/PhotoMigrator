# <span style="color:green">Automated Migration Feature Documentation:</span>

> [!NOTE]  
>## <span style="color:green">Automated Migration Feature</span>
>From version 3.0.0 onwards, the Tool supports a new Extra Mode called '**AUTOMATED-MIGRATION**' Mode. 
>
> Use the argument **'--source'** to select the \<SOURCE> and the argument **'--target'** to select \<TARGET> for the AUTOMATED-MIGRATION Process to Pull all your Assets (including Albums) from the \<SOURCE> Cloud Service and Push them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2] to select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
> 
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  
> 
> By default, the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Push workers.  
> The Pull worker and the different Push workes will be executed in parallel using an assets queue to garantee that no more than 100 assets will be temporarily stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default, (if your terminal size has enough width and heigh) a Live Dashboard will show you all the datails about the migration process, including most relevant log messages, and counter status. You can disable this Libe Dashboard using the flag **'--dashboard=false'**.   
> 
> Additionally, this Automated Migration process can also be executed secuencially instead of in parallel, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
> 
> Also, take into account that in this case, the Live Dashboard will not be displayed, so you only will see the different messages log in the screen, but not the live counters during the migration.  
> and execute this feature, the Tool will automatically do the whole migration job from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.  

> [!IMPORTANT]  
> If you use a local folder <INPUT_FOLDER> as source client, all your Albums should be placed into a subfolder called *'Albums'* within <INPUT_FOLDER>, creating one Album subfolder per Album, otherwise the tool will no create any Album in the target client.  
>
> Example:  
> <INPUT_FOLDER>/Album1  
> <INPUT_FOLDER>/Album2  

## Live Dashboard Preview:
![Live Dashboard](/assets/screenshots/live_dashboard.jpg)


## **Examples of use:**

- **Example 1:**
```
./CloudPhotoMigrator.run --source=/homes/MyTakeout --target=synology-1
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will process the folder '/homes/MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
    correct date and time, and identifying which assets belongs to each Album created on Google Photos.  

  - Second, the Tool will connect to your Synology Photos account 1 (if you have configured properly the Config.ini file) and will 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Takeout files and associating
    all the assets included in each Album in the same way that you had on your Google Photos account.



- **Example 2**:
```
./CloudPhotoMigrator.run --source=synology-2 target=immich-1
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Synology Photos account 2 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.


- **Example 3**:
```
./CloudPhotoMigrator.run --source=immich-2 target=/homes/local_folder
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will push all the pulled assets into the local folder '/homes/local_folder' creating a folder structure
    with all the Albums in the subfolder 'Albums' and all the assets without albums associated into the subfolder 'No-Albums'. 
    This 'No-Albums' subfolder will have a year/month structure to store all your asset in a more organized way.  


- **Example 4**:
```
./CloudPhotoMigrator.run --source=immich-1 target=immich-2
```

In this example, the Tool will do an Automated Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.



## Config.ini
>```
># Configuration for Google Takeout
>[Google Takeout]
># No configuration needed for this module for the time being.
>
># Configuration for Synology Photos
>[Synology Photos]
>SYNOLOGY_URL                = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>SYNOLOGY_USERNAME_1         = username_1                                    # Account 1: Your username for Synology Photos
>SYNOLOGY_PASSWORD_1         = password_1                                    # Account 1: Your password for Synology Photos
>SYNOLOGY_USERNAME_2         = username_2                                    # Account 2: Your username for Synology Photos
>SYNOLOGY_PASSWORD_2         = password_2                                    # Account 2: Your password for Synology Photos
>
># Configuration for Immich Photos
>[Immich Photos]
>IMMICH_URL                  = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>IMMICH_API_KEY_ADMIN        = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>
>IMMICH_API_KEY_USER_1       = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_1           = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_1           = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
>
>IMMICH_API_KEY_USER_2       = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_2           = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_2           = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
>
>IMMICH_FILTER_ARCHIVE       = False                                         # Optional: Used as Filter Criteria for Assets downloading (True/False)
>IMMICH_FILTER_FROM          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>IMMICH_FILTER_TO            = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: 2024-10-01)
>IMMICH_FILTER_COUNTRY       = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: Spain)
>IMMICH_FILTER_CITY          = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Madrid', 'Málaga'])
>IMMICH_FILTER_PERSON        = *                                             # Optional: Used as Filter Criteria for Assets downloading (i.e: ['Mery', 'James'])
>```

## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
