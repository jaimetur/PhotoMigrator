def set_help_texts():
    import textwrap
    HELP_TEXTS = {}

    ################################
    # FEATURE: AUTOMATIC-MIGRATION #
    ################################
    HELP_TEXTS["AUTOMATIC-MIGRATION"] = textwrap.dedent(f"""
        ATTENTION!!!: This process will do an AUTOMATIC-MIGRATION process, Pulling all your Assets (including Albums) from the <SOURCE> Cloud Service
        and Pushing them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service).
        """)

    ##########################
    # FEATURE: GOOGLE PHOTOS #
    ##########################
    HELP_TEXTS["google-photos-takeout"] = textwrap.dedent(f"""
        ATTENTION!!!: This module will process your <TAKEOUT_FOLDER> to fix metadata of all your assets and organize them according with the settings defined by user (above settings).
        """)


    ####################################
    # FEATURES: SYNOLOGY/IMMICH PHOTOS #
    ####################################
    HELP_TEXTS["cloud-remove-empty-albums"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will remove all Empty Albums found in it.
            """)

    HELP_TEXTS["cloud-remove-duplicates-albums"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will remove all Duplicates Albums (based on assets counts and assets size) found in it.
            """)

    HELP_TEXTS["cloud-merge-duplicates-albums"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will merge all Duplicates Albums (with the same name) found in it, removing all of them except the albums with highest number of assets and assigning all assets from removed albums to it.
            """)

    HELP_TEXTS["cloud-upload-folder"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will upload all Photos/Videos found within <INPUT_FOLDER> (including subfolders, except 'Albums' subfolder).
            """)

    HELP_TEXTS["cloud-upload-albums"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
            """)

    HELP_TEXTS["cloud-upload-all"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your to your Photos account and will Upload all Assets found in <INPUT_FOLDER> 
            All the Subfolders with valid assets inside '<INPUT_FOLDER>/Albums' will be considered as an Album, and will create new Album in your Photos account with the name of the Subfolder.
            If the folder '<INPUT_FOLDER>' contains a Subfolder called 'No-Albums' then, all assets inside each that subfolder will be uploaded without creating any Album for them.
            """)

    HELP_TEXTS["cloud-download-albums"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your Photos account and download those Album(s) whose name is in: '<ALBUMS_NAME>' 
            to the output folder: '<OUTPUT_FOLDER>'.  If the file already exists, it will be OVERWRITTEN!!!
            - To download ALL Albums within your Photos account use 'ALL' as ALBUMS_NAME.
            - To download all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: dron* to download all albums starting with the word 'dron' followed by other(s) words.
            - To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --cloud-download-albums "album1", "album2", "album3"        
            """)

    HELP_TEXTS["cloud-download-all"] = textwrap.dedent(f"""
            ATTENTION!!!: This process will connect to your Photos account and will download all the Albums Assets and also 
            Assets without Albums into the folder '<OUTPUT_FOLDER>'. If the file already exists, it will be OVERWRITTEN!!!
            - All Albums Assets will be downloaded within a subfolder of '<OUTPUT_FOLDER>/Albums' with the same name of the Album and all files will be flattened into it.
            - All Assets with no Albums associated will be downloaded within a subfolder '<OUTPUT_FOLDER>/No-Albums' and will have a year/month structure inside.
            """)

    HELP_TEXTS["cloud-remove-orphan-assets"] = textwrap.dedent(f"""
            ATTENTION!!!: In this process, the Tool will look for all Orphan Assets in your Photos account Database and will remove them. 
            IMPORTANT!!!: This feature requires a valid ADMIN_API_KEY configured in Config.ini.
            """)

    HELP_TEXTS["cloud-remove-all-assets"] = textwrap.dedent(f"""
            CAUTION!!! The Tool will remove ALL your Assets (Photos & Videos) and also ALL your Albums from your Photos account database.         
            """)

    HELP_TEXTS["cloud-remove-all-albums"] = textwrap.dedent(f"""
            CAUTION!!! The Tool will remove ALL your Albums from your Photos account Database.
            Optionally ALL the Assets associated to each Album can be removed If you also include the argument '-rAlbAss, --remove-albums-assets' argument.
            """)

    HELP_TEXTS["cloud-remove-albums"] = textwrap.dedent(f"""
            CAUTION!!! The Tool will remove those Albums from your Photos account Database whose name matches with the provided pattern '<ALBUMS_NAME_PATTERN>'.
            Optionally ALL the Assets associated to each Album can be removed If you also include the argument '-rAlbAss, --remove-albums-assets' argument.
            """)

    HELP_TEXTS["cloud-rename-albums"] = textwrap.dedent(f"""
            CAUTION!!! The Tool will rename those Albums from your Photos account Database whose name matches with the provided pattern '<ALBUMS_NAME_PATTERN>' and will replace them with the pattern '<ALBUMS_NAME_REPLACEMENT_PATTERN>'.
            """)

    ############################
    # OTHER STANDALONE FEATURES:
    ############################
    HELP_TEXTS["find-duplicates"]  = textwrap.dedent(f"""
        ATTENTION!!!: This process will process all Duplicates files found in <DUPLICATES_FOLDER> and will apply the given action.
        You must take into account that if not valid action is detected within the arguments of '-findDup, --find-duplicates <ACTION> <DUPLICATES_FOLDER>', then 'list' will be the default action.
        Possible duplicates-action are:
            - list   : This action is not dangerous, just list all duplicates files found in a Duplicates.csv file.
            - move   : This action could be dangerous but is easily reversible if you find that any duplicated file have been moved to Duplicates folder and you want to restore it later
                       You can easily restore it using option -procDup, --process-duplicates
            - remove : This action could be dangerous and is irreversible, since the Tool will remove all duplicates found and will keep only a Principal file per each duplicates set. 
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
