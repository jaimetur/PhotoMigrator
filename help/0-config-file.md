## Config.ini

You can see the default Config.ini file here

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

## Google Takeout Section:
In this section you don't have to provide to provide any settings (it is here for futures purposses:

## Synology Photos Section:
In this section you have to provide:
- **SYNOLOGY_URL:** In the format that you have above (change only your IP address)
- **SYNOLOGY_USERNAME_1:** The username for the Synology Account 1
- **SYNOLOGY_PASSWORD_1:** The password for the Synology Account 1
- **SYNOLOGY_USERNAME_2:** The username for the Synology Account 1 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **SYNOLOGY_PASSWORD_2:** The password for the Synology Account 1 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)

## Immich Photos Section:
In this section you have to provide:
- **IMMICH_URL:** In the format that you have above (change only your IP address)
- **IMMICH_API_KEY_ADMIN:** The API_KEY for the Immich Administrator Account (Optional: Only needed in case that you want to run 'Remove Orphan Assets' feature.)


- **IMMICH_USERNAME_1:** The username for the Immich Account 1
- **IMMICH_PASSWORD_1:** The password for the Immich Account 1
- **IMMICH_API_KEY_USER_1:** The API_KEY for the Immich Account 1  


- **IMMICH_USERNAME_2:** The username for the Immich Account 1 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **IMMICH_PASSWORD_2:** The password for the Immich Account 1 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **IMMICH_API_KEY_USER_1:** The API_KEY for the Immich Account 1

> [!NOTE]  
> In Immich you can choose if you want to login with username/password or you prefeer to use an API_KEY instead.
> If you choose username/password authentification method, then, you don't need to provide any API_KEY for that account.
> If you choose API_KEY authentification method, then, you don't need to provide any username/password for htat account.

- **IMMICH_FILTER_ARCHIVE:** This field is not used yet
- **IMMICH_FILTER_FROM:** This field is not used yet
- **IMMICH_FILTER_TO:** This field is not used yet
- **IMMICH_FILTER_COUNTRY:** This field is not used yet
- **IMMICH_FILTER_CITY:** This field is not used yet
- **IMMICH_FILTER_PERSON:** This field is not used yet


## Credits
I hope this can be useful for any of you.  
Enjoy it!

<span style="color:grey">(c) 2024-2025 by Jaime Tur (@jaimetur).</span>  
