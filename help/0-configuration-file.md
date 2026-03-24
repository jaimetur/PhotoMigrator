# ⚙️ Configuration File 

You can see the default Configuration File ('Config.ini' by default) below:

>```
># Configuration for Google Takeout
>[Google Takeout]
># No configuration needed for this module for the time being.
>
># Configuration for Synology Photos
>[Synology Photos]
>SYNOLOGY_URL                       = http://192.168.1.11:5000                      # Change this IP by the IP that contains the Synology server or by your valid Synology URL
>SYNOLOGY_USERNAME_1                = username_1                                    # Account 1: Your username for Synology Photos
>SYNOLOGY_PASSWORD_1                = password_1                                    # Account 1: Your password for Synology Photos
>SYNOLOGY_USERNAME_2                = username_2                                    # Account 2: Your username for Synology Photos
>SYNOLOGY_PASSWORD_2                = password_2                                    # Account 2: Your password for Synology Photos
>SYNOLOGY_USERNAME_3                = username_3                                    # Account 3: Your username for Synology Photos
>SYNOLOGY_PASSWORD_3                = password_3                                    # Account 3: Your password for Synology Photos
>
># Configuration for Immich Photos
>[Immich Photos]
>IMMICH_URL                         = http://192.168.1.11:2283                      # Change this IP by the IP that contains the Immich server or by your valid Immich URL
>IMMICH_API_KEY_ADMIN               = YOUR_ADMIN_API_KEY                            # Your ADMIN_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_API_KEY_USER_1              = API_KEY_USER_1                                # Account 1: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_1                  = username_1                                    # Account 1: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_1                  = password_1                                    # Account 1: Your password for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_API_KEY_USER_2              = API_KEY_USER_2                                # Account 2: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_2                  = username_2                                    # Account 2: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_2                  = password_2                                    # Account 2: Your password for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_API_KEY_USER_3              = API_KEY_USER_3                                # Account 3: Your USER_API_KEY for Immich Photos (Your can create can API_KEY in your Account Settings-->API_KEY Keys)
>IMMICH_USERNAME_3                  = username_3                                    # Account 3: Your username for Immich Photos (mandatory if not API_KEY is providen)
>IMMICH_PASSWORD_3                  = password_3                                    # Account 3: Your password for Immich Photos (mandatory if not API_KEY is providen)
>
># Configuration for NextCloud Photos
>[NextCloud Photos]
>NEXTCLOUD_URL                      = http://192.168.1.11:8080                      # Your NextCloud base URL (without trailing '/')
>NEXTCLOUD_MAX_PARALLEL_UPLOADS     = 12                                            # Parallel uploads (recommended 8-16 in LAN)
>NEXTCLOUD_MAX_PARALLEL_DOWNLOADS   = 16                                            # Parallel downloads (recommended 12-24 in LAN)
>NEXTCLOUD_USE_SYSTEM_PROXY         = false                                         # false=recommended in LAN, true only if HTTP(S)_PROXY is required
>NEXTCLOUD_USERNAME_1               = username_1                                    # Account 1: Your username for NextCloud
>NEXTCLOUD_PASSWORD_1               = password_1                                    # Account 1: Your password for NextCloud
>NEXTCLOUD_PHOTOS_FOLDER_1          = /Photos/ALL_Photos                            # Account 1: Folder used for assets without albums and Download All assets scan
>NEXTCLOUD_ALBUMS_FOLDER_1          = /Photos/Albums                                # Account 1: Folder used for folder-based albums
>NEXTCLOUD_USERNAME_2               = username_2                                    # Account 2: Your username for NextCloud
>NEXTCLOUD_PASSWORD_2               = password_2                                    # Account 2: Your password for NextCloud
>NEXTCLOUD_PHOTOS_FOLDER_2          = /Photos/ALL_Photos                            # Account 2: Folder used for assets without albums and Download All assets scan
>NEXTCLOUD_ALBUMS_FOLDER_2          = /Photos/Albums                                # Account 2: Folder used for folder-based albums
>NEXTCLOUD_USERNAME_3               = username_3                                    # Account 3: Your username for NextCloud
>NEXTCLOUD_PASSWORD_3               = password_3                                    # Account 3: Your password for NextCloud
>NEXTCLOUD_PHOTOS_FOLDER_3          = /Photos/ALL_Photos                            # Account 3: Folder used for assets without albums and Download All assets scan
>NEXTCLOUD_ALBUMS_FOLDER_3          = /Photos/Albums                                # Account 3: Folder used for folder-based albums
>
># Configuration for Google Photos
>[Google Photos]
>GOOGLE_PHOTOS_ACCOUNT_NAME_1       = username_1                                   # Optional display label for Google Photos account 1
>GOOGLE_PHOTOS_CLIENT_ID_1          = client_id_1                                   # OAuth Client ID for Google Photos account 1
>GOOGLE_PHOTOS_CLIENT_SECRET_1      = client_secret_1                               # OAuth Client Secret for Google Photos account 1
>GOOGLE_PHOTOS_REFRESH_TOKEN_1      = refresh_token_1                               # OAuth Refresh Token for Google Photos account 1
>GOOGLE_PHOTOS_ACCOUNT_NAME_2       = username_2                                   # Optional display label for Google Photos account 2
>GOOGLE_PHOTOS_CLIENT_ID_2          = client_id_2                                   # OAuth Client ID for Google Photos account 2
>GOOGLE_PHOTOS_CLIENT_SECRET_2      = client_secret_2                               # OAuth Client Secret for Google Photos account 2
>GOOGLE_PHOTOS_REFRESH_TOKEN_2      = refresh_token_2                               # OAuth Refresh Token for Google Photos account 2
>GOOGLE_PHOTOS_ACCOUNT_NAME_3       = username_3                                   # Optional display label for Google Photos account 3
>GOOGLE_PHOTOS_CLIENT_ID_3          = client_id_3                                   # OAuth Client ID for Google Photos account 3
>GOOGLE_PHOTOS_CLIENT_SECRET_3      = client_secret_3                               # OAuth Client Secret for Google Photos account 3
>GOOGLE_PHOTOS_REFRESH_TOKEN_3      = refresh_token_3                               # OAuth Refresh Token for Google Photos account 3
>```

## Google Takeout Section:
In this section you don't have to provide any settings (it is here for futures purposes):

## Synology Photos Section:
In this section you have to provide:
- **SYNOLOGY_URL:** In the format that you have above (change only your IP address)
- **SYNOLOGY_USERNAME_1:** The username for the Synology Account 1
- **SYNOLOGY_PASSWORD_1:** The password for the Synology Account 1
- **SYNOLOGY_USERNAME_2:** The username for the Synology Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **SYNOLOGY_PASSWORD_2:** The password for the Synology Account 2 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **SYNOLOGY_USERNAME_3:** The username for the Synology Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 3)
- **SYNOLOGY_PASSWORD_3:** The password for the Synology Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 3)

## Immich Photos Section:
In this section you have to provide:
- **IMMICH_URL:** In the format that you have above (change only your IP address)
- **IMMICH_API_KEY_ADMIN:** The API_KEY for the Immich Administrator Account (Optional: Only needed in case that you want to run 'Remove Orphan Assets' feature.)


- **IMMICH_USERNAME_1:** The username for the Immich Account 1
- **IMMICH_PASSWORD_1:** The password for the Immich Account 1
- **IMMICH_API_KEY_USER_1:** The API_KEY for the Immich Account 1  


- **IMMICH_USERNAME_2:** The username for the Immich Account 2 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **IMMICH_PASSWORD_2:** The password for the Immich Account 2 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)
- **IMMICH_API_KEY_USER_2:** The API_KEY for the Immich Account 2 (Optional: just in case that you need to migrate assets from Account 1 to Account 2)


- **IMMICH_USERNAME_3:** The username for the Immich Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 3)
- **IMMICH_PASSWORD_3:** The password for the Immich Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 3)
- **IMMICH_API_KEY_USER_3:** The API_KEY for the Immich Account 3 (Optional: just in case that you need to migrate assets from Account 1 to Account 3)

> [!NOTE]  
> In Immich you can choose if you want to login with username/password or you prefer to use an API_KEY instead.  
>
> If you choose username/password authentication method, then, you don't need to provide any API_KEY for that account.  
>
> If you choose API_KEY authentication method, then, you don't need to provide any username/password for that account.  

## NextCloud Photos Section:
In this section you have to provide:
- **NEXTCLOUD_URL:** NextCloud base URL (for example `http://192.168.1.11`).
- **NEXTCLOUD_MAX_PARALLEL_UPLOADS:** Number of parallel uploads (global default for all accounts).
- **NEXTCLOUD_MAX_PARALLEL_DOWNLOADS:** Number of parallel downloads (global default for all accounts).
- **NEXTCLOUD_USE_SYSTEM_PROXY:** Whether PhotoMigrator should use system/container proxy variables (`HTTP_PROXY`/`HTTPS_PROXY`).
- **NEXTCLOUD_USERNAME_1/2/3:** NextCloud username per account id.
- **NEXTCLOUD_PASSWORD_1/2/3:** NextCloud password per account id.
- **NEXTCLOUD_PHOTOS_FOLDER_1/2/3:** Folder for assets without albums. `Download All` scans this folder recursively.
- **NEXTCLOUD_ALBUMS_FOLDER_1/2/3:** Folder where PhotoMigrator creates/reads folder-based albums.

> [!NOTE]
> NextCloud support is based on WebDAV operations and does not require API keys.
>
> For best performance in local networks, use `NEXTCLOUD_USE_SYSTEM_PROXY = false` and tune `NEXTCLOUD_MAX_PARALLEL_UPLOADS` (usually `8-16`) and `NEXTCLOUD_MAX_PARALLEL_DOWNLOADS` (usually `12-24`).

> [!WARNING]
> Setting `NEXTCLOUD_MAX_PARALLEL_UPLOADS` / `NEXTCLOUD_MAX_PARALLEL_DOWNLOADS` too high can saturate the server or trigger throttling/errors.
> If stability drops, reduce them (for example from `16` to `8`).
>
> Enable `NEXTCLOUD_USE_SYSTEM_PROXY = true` only when an outbound proxy is explicitly required by your environment.

## Google Photos Section:
In this section you have to provide:
- **GOOGLE_PHOTOS_ACCOUNT_NAME_1/2/3:** Optional label shown in dashboard/logs (for example your Google account email or alias).
- **GOOGLE_PHOTOS_CLIENT_ID_1/2/3:** OAuth client id per account.
- **GOOGLE_PHOTOS_CLIENT_SECRET_1/2/3:** OAuth client secret per account.
- **GOOGLE_PHOTOS_REFRESH_TOKEN_1/2/3:** OAuth refresh token per account.

> [!NOTE]
> Google Photos support is limited by current official Library API capabilities.

---
## 🏠 [Back to Main Page](/README.md)

---
## 🎖️ Credits:
I hope this can be useful for any of you. Enjoy it!

<span style="color:grey">(c) 2024-2026 by Jaime Tur (@jaimetur).</span>  
