# <span style="color:green">🚀 Automatic Migration Feature:</span>

> [!NOTE]  
>## <span style="color:green">Automatic Migration Feature</span>
>From version 3.0.0 onwards, the Tool supports a new Feature called '**Automatic Migration**'. 
>
> Use the argument **'--source'** to select the \<SOURCE> client and the argument **'--target'** to select \<TARGET> client for the Automatic Migration Process to Pull all your Assets (including Albums) from the \<SOURCE> Cloud Service and Push them to the \<TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
> 
>  - Possible values for:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos']-[id] or <INPUT_FOLDER>  (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos']-[id] or <OUTPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    
> 
>  - The idea is complete above list to allow also Google Photos and Apple Photos (iCloud), so when this is done, the allowed values will be:
>    - **\<SOURCE\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <INPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>    - **\<TARGET\>** : ['synology-photos', 'immich-photos', 'google-photos', 'apple-photos']-[id]  or <OUTPUT_FOLDER> (id=[1, 2, 3] to select which account to use from the Config.ini file).  
>
> If you ommit the suffix -[id], the tool will assume that account 1 will be used for the specified client (ie: --source=synology-photos means that Synology Photos account 1 will be used as \<SOURCE> client.)  
>
> Also, you can ommit the suffix -photos in both \<SOURCE> and \<TARGET> clients, so, you can just use --source=synology --target=immich to set Synology Photos account 1 as \<SOURCE> client and Immich Photos account 1 as \<TARGET> client.  
> 
> It is also possible to specify the account-id using the flag _**'-id, --account-id \<ID>'**_ (ie: --source=synology --account-id=2 means that Synology Photos account 2 will be used as \<SOURCE> client.)  
> 
>> ⚠️ **IMPORTANT**:  
>> Take into account that the flag _**'-id, --account-id \<ID>'**_ applies for all the Photo Cloud Services (Synology Photos and Immich Photos, so if you specify the client ID using this flag and you have more than one Photo Cloud Service, all of them will use the same client ID.)
> 
> By default, the whole Migration process is executed in parallel using multi-threads (it will detect automatically the number of threads of the CPU to set properly the number of Push workers). The Pull worker and the different Push workes will be executed in parallel using an assets queue to guarantee that no more than 100 assets will be temporarily stored on your local drive, so you don't need to care about the hard disk space needed during this migration process.  
> 
> By default, (if your terminal size has enough width and heigh) a Live Dashboard will show you all the details about the migration process, including most relevant log messages, and counter status. You can disable this Live Dashboard using the flag **'-dashboard=false or --dashboard=false'**.   
> 
> Additionally, this Automatic Migration process can also be executed sequentially instead of in parallel, using flag **--parallel=false**, so first, all the assets will be pulled from <SOURCE> and when finish, they will be pushed into <TARGET>, but take into account that in this case, you will need enough disk space to store all your assets pulled from <SOURCE> service.
>
> Finally, you can apply filters to filter assets to pull from \<SOURCE> client. The available filters are: 
>    - **by Type:**
>      - flag: -type, --filter-by-type
>        - Valid values are [image, video, all]
>    - **by Dates:**
>      - flags:
>        - -from, --filter-from-date
>        - -to, --filter-to-date
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
>    - **by Country:**
>      - flag: -country, --filter-by-country
>        - Valid values are any existing country in the \<SOURCE> client.
>    - **by City:**
>      - flag: -city, --filter-by-city
>        - Valid values are any existing city in the \<SOURCE> client.
>    - **by Person:**
>      - flag: -person, --filter-by-person
>        - Valid values are any existing person in the \<SOURCE> client.

> [!WARNING]  
> If you use a local folder <INPUT_FOLDER> as source client, all your Albums should be placed into a subfolder called *'Albums'* within <INPUT_FOLDER>, creating one Album subfolder per Album, otherwise the tool will no create any Album in the target client.  
>
> Example:  
> <INPUT_FOLDER>/Album1  
> <INPUT_FOLDER>/Album2  

> [!IMPORTANT]  
> It is important that you configure properly the file 'Config.ini' (included with the tool), to set properly the accounts for your Photo Cloud Service.  


## Config.ini
Youn can see how to configure the Config.ini file in this help section:
[Configuration File](.https://github.com/jaimetur/PhotoMigrator/blob/main/help/0-configuration-file.md) 


## Live Dashboard Preview:
![Live Dashboard](.https://github.com/jaimetur/PhotoMigrator/blob/main/assets/screenshots/live_dashboard.jpg)


## **Examples of use:**

- **Example 1:**
```
./PhotoMigrator.run --source=/homes/MyTakeout --target=synology-1
```

In this example, the Tool will do an Automatic Migration Process which has two steps:  

  - First, the Tool will process the folder '/homes/MyTakeout' (Unzipping them if needed), fixing all files found on it, to set the
    correct date and time, and identifying which assets belongs to each Album created on Google Photos.  

  - Second, the Tool will connect to your Synology Photos account 1 (if you have configured properly the Config.ini file) and will 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Takeout files and associating
    all the assets included in each Album in the same way that you had on your Google Photos account.



- **Example 2**:
```
./PhotoMigrator.run --source=synology-2 --target=immich-1
```

In this example, the Tool will do an Automatic Migration Process which has two steps:  

  - First, the Tool will connect to your Synology Photos account 2 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.


- **Example 3**:
```
./PhotoMigrator.run --source=immich-2 --target=/homes/local_folder --filter-by-person=Peter --filter-from-date=2024
```

In this example, the Tool will do an Automatic Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account where Peter have been labeled as person, and whose date is after 01/02/2024 (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will push all the pulled assets into the local folder '/homes/local_folder' creating a folder structure
    with all the Albums in the subfolder 'Albums' and all the assets without albums associated into the subfolder 'No-Albums'. 
    This 'No-Albums' subfolder will have a year/month structure to store all your asset in a more organized way.  


- **Example 4**:
```
./PhotoMigrator.run --source=immich-1 --target=immich-2 --filter-by-city=Rome --filter-by-person=Mery
```

In this example, the Tool will do an Automatic Migration Process which has two steps:  

  - First, the Tool will connect to your Immich Photos account 1 (if you have configured properly the Config.ini file) and will
    pull all the assets found in your account that have been taken in Rome and where Mery have been labeled as person (separating those associated to som Album(s), of those without any Album associated).  

  - In parallel, the Tool will connect to your Immich Photos account 2 (if you have configured properly the Config.ini file) and 
    push all the assets pulled from previous step, creating a new Album per each Album found in your Synology Photos and associating
    all the assets included in each Album in the same way that you had on your Synology Photos account.

    
---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>   
