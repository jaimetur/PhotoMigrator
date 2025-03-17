
> [!NOTE]  
>## <span style="color:green">Automated Migration Feature</span>
>From version 3.0.0 onwards, the script supports a new Extra Mode called '**AUTOMATED-MIGRATION**' Mode. 
>
> Use the arguments **'-s'** or **'--source'** to select the \<SOURCE> and **'-t'** or **'--target'** to select \<TARGET> for the AUTOMATED-MIGRATION Process to Download all your Assets (including Albums) from the \<SOURCE> Cloud Service and Upload them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2] select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2] select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
> 
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  
> 
> By default the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Upload workers.  
> The Download worker and the different Upload workes will be executed in parallel using an assets queue to garantee that no more than 100 assets will be temporary stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default (if your terminal size has enough width and heigh) a Live Dashboard will show you all the datails about the migration process, including most relevant log messages, and counter status.  
> 
> Additionally, this Automated Migration process can also be executed secuencially instead of in parallel, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
> 
> Also, take into account that in this case, the Live Dashboard will not be displayed, so you only will see the different messages log in the screen, but not the live counters during the migration.  
> and execute this Extra Mode, the script will automatically do the whole migration job from \<SOURCE> Cloud Service to \<TARGET> Cloud Service.  


**Examples of use:**

- **Example 1:**
```
./CloudPhotoMigrator.run --source=/homes/MyTakeout --target=synology-1
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will process the folder '/homes/MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
    correct date and time, and identifying which assets belongs to each Album created on Google Photos.  

  - Second, the script will connect to your Synology Photos account 1 (if you have configured properly the Config.ini file) and will 
    upload all the assets processed in previous step, creating a new Album per each Album found in your Takeout files and associating
    all the assets included in each Album in the same way that you had on your Google Photos account.



- **Example 2**:
```
./CloudPhotoMigrator.run --source=synology-2 target=immich-1
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will connect to your Synology Photos account 2 (if you have configured properly the Config.ini file) and 
    download all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the script will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    upload all the assets processed in previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.


- **Example 3**:
```
./CloudPhotoMigrator.run --source=immich-2 target=/homes/local_folder
```

In this example, the script will do a FULLY-AUTOMATED job which has two steps:  

  - First, the script will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and 
    download all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the script will copy all the downloaded assets into the local folder '/homes/local_folder' creating a folder structure
    with all the Albums in the subfolder 'Albums' and all the assets without albums associated into the subfolder 'No-Albums'. 
    This 'No-Albums' subfolder will have a year/month structure to store all your asset in a more organized way.  
