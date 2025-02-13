def set_help_texts():
    import textwrap
    HELP_TEXTS = {}

    ###################################
    # EXTRA MODE: AUTOMATED-MIGRATION #
    ###################################
    HELP_TEXTS["AUTOMATED-MIGRATION"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will do an AUTOMATED-MIGRATION process, Downloading all your Assets (including Albums) from the <SOURCE> Cloud Service
        
        and Uploading them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service.
        """)

    ################################
    # EXTRA MODE: GOOGLE PHOTOS #
    ################################
    HELP_TEXTS["google-photos-takeout"] = textwrap.dedent(f"""
        ATTENTION!!!: This nodule will process your <TAKEOUT_FOLDER> to fix metadata of all your assets and organize them according with the settings defined by user (above settings).
        """)

    ################################
    # EXTRA MODES: SYNOLOGY PHOTOS #
    ################################

    HELP_TEXTS["synology-remove-empty-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Empty Albums found in Synology Photos database.
        """)

    HELP_TEXTS["synology-remove-duplicates-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Duplicates Albums found in Synology Photos database.
        """)

    HELP_TEXTS["synology-upload-folder"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will upload all Photos/Videos found within <FOLDER> (including subfolders, except 'Albums' subfolder).
        
        Due to Synology Photos limitations, o Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos.
        """)

    HELP_TEXTS["synology-upload-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
        
        Due to Synology Photos limitations, to Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos. 
        """)

    HELP_TEXTS["synology-upload-all"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your Synology Photos account and will Upload all Assets found in <INPUT_FOLDER> 
        
        All the Subfolders with valid assets inside <INPUT_FOLDER> will be considered as an Album, and will create new Album in Synology Photos with the name of the Subfolder.
        
        If the <INPUT_FOLDER> contains a Subfolder called 'No-Albums' then, all assets inside each that subfolder will be uploaded without creating any Album for them.
        """)

    HELP_TEXTS["synology-download-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Synology Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the SYNOLOGY_ROOT_FOLDER. 
        
        If the file already exists, it will be OVERWRITTEN!!!
        
        To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: dron* to download all albums starting with the word 'dron' followed by other(s) words.
        
        To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3" 
        
        To extract ALL Albums within in Synology Photos database use 'ALL' as ALBUMS_NAME.
        """)

    HELP_TEXTS["synology-download-all"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Synology Photos and will download all the Album and Assets without Albums into the folder '<OUTPUT_FOLDER>' within the SYNOLOGY_ROOT_FOLDER. 
        
        If the file already exists, it will be OVERWRITTEN!!!
        
        All Albums will be downloaded within a subfolder of '<OUTPUT_FOLDER>/Albums' with the same name of the Album and all files will be flattened into it.
        
        Assets with no Albums associated will be downloaded within a subfolder '<OUTPUT_FOLDER>/No-Albums' and will have a year/month structure inside.
        """)

    HELP_TEXTS["synology-remove-all-assets"]  = textwrap.dedent(f"""
        CAUTION!!! The script will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Synology database.         
        """)

    HELP_TEXTS["synology-remove-all-albums"] = textwrap.dedent(f"""
        CAUTION!!! The script will delete ALL your Albums from Synology database.

        Optionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument.
        """)

    ##############################
    # EXTRA MODES: IMMICH PHOTOS #
    ##############################
    HELP_TEXTS["immich-remove-empty-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Empty Albums found in Immich Photos database.
        """)

    HELP_TEXTS["immich-remove-duplicates-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Duplicates Albums found in Immich Photos database.
        """)

    HELP_TEXTS["immich-upload-folder"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will upload all Photos/Videos found within <INPUT_FOLDER> (including subfolders, except 'Albums' subfolder).
        """)

    HELP_TEXTS["immich-upload-albums"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
        """)

    HELP_TEXTS["immich-upload-all"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will Upload all Assets found in <INPUT_FOLDER> 
        
        All the Subfolders with valid assets inside <INPUT_FOLDER> will be considered as an Album, and will create new Album in Immich Photos with the name of the Subfolder.
        
        If the <INPUT_FOLDER> contains a Subfolder called 'No-Albums' then, all assets inside each that subfolder will be uploaded without creating any Album for them.
        """)

    HELP_TEXTS["immich-download-albums"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Immich Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder './Downloads_Immich' within the Script execution folder. 
       
        If the file already exists, it will be OVERWRITTEN!!!
       
        To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: dron* to download all albums starting with the word 'dron' followed by other(s) words.
       
        To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums "album1", "album2", "album3" 
       
        To extract ALL Albums within in Immich Photos database use 'ALL' as ALBUMS_NAME.
        """)

    HELP_TEXTS["immich-download-all"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Immich Photos and will download all the Album and Assets without Albums into the folder './<OUTPUT_FOLDER>'. 
       
        If the file already exists, it will be OVERWRITTEN!!!.
       
        All Albums will be downloaded within a subfolder of './<OUTPUT_FOLDER>/Albums' with the same name of the Album and all files will be flattened into it.
       
        Assets with no Albums associated will be downloaded withn a subfolder './<OUTPUT_FOLDER>/No-Albums' and will have a year/month structure inside.
        """)

    HELP_TEXTS["immich-remove-orphan-assets"]  = textwrap.dedent(f"""
        ATTENTION!!!: In this process, the script will look for all Orphan Assets in Immich Database and will delete them. 
        
        IMPORTANT!!!: This feature requires a valid ADMIN_API_KEY configured in Config.ini.
        """)

    HELP_TEXTS["immich-remove-all-assets"]  = textwrap.dedent(f"""
        CAUTION!!! The script will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Immich database.         
        """)

    HELP_TEXTS["immich-remove-all-albums"]  = textwrap.dedent(f"""
        CAUTION!!! The script will delete ALL your Albums from Immich database.
        
        Optionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument.
        """)

    ##############################
    # OTHER STANDALONE EXTRA MODES:
    ##############################
    HELP_TEXTS["find-duplicates"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will process all Duplicates files found in <DUPLICATES_FOLDER> and will apply the given action.
        
        You must take into account that if not valid action is detected within the arguments of '-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>', then 'list' will be the default action.
        
        Possible duplicates-action are:
            - list   : This action is not dangerous, just list all duplicates files found in a Duplicates.csv file.
            - move   : This action could be dangerous but is easily reversible if you find that any duplicated file have been moved to Duplicates folder and you want to restore it later
                       You can easily restore it using option -pd, --process-duplicates
            - remove : This action could be dangerous and is irreversible, since the script will remove all duplicates found and will keep only a Principal file per each duplicates set. 
                       The principal file is chosen carefully based on some heuristic methods
        """)

    HELP_TEXTS["process-duplicates"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will process all Duplicates files found with option '-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>' 
        based on the Action column value of 'Duplicates.csv' file generated in 'Find Duplicates Mode'. 
        
        You can modify individually each Action column value for each duplicate found, but take into account that the below actions list are irreversible:
        
        Possible Actions in revised CSV file are:
            - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanently removed
            - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
            - replace_duplicate : This action can be used to replace the principal file chosen for each duplicates and select manually other principal file
                                  Duplicated file moved to Duplicates folder will be restored to its original location as principal file
                                  and Original Principal file detected by the Script will be removed permanently
        """)

    HELP_TEXTS["fix-symlinks-broken"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will look for all Symbolic Links broken in <FOLDER_TO_FIX> and will try to find the destination file within the same folder.
        """)

    HELP_TEXTS["rename-folders-content-based"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will clean each Subfolder found in <ALBUMS_FOLDER> with an homogeneous name starting with album year followed by a cleaned subfolder name without underscores nor middle dashes.
        
        New Album name format: 'yyyy - Cleaned Subfolder name'
        """)

    return HELP_TEXTS
