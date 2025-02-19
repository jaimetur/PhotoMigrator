from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION
import os, sys
from datetime import datetime, timedelta
import Utils
import logging
from CustomLogger import set_log_level
from Duplicates import find_duplicates, process_duplicates_actions
from ServiceGooglePhotos import google_takeout_processor
from ServiceSynologyPhotos import read_synology_config, logout_synology, synology_upload_albums, synology_upload_ALL, synology_download_albums, synology_download_ALL, synology_remove_empty_albums, synology_remove_duplicates_albums, synology_remove_all_assets, synology_remove_all_albums
from ServiceImmichPhotos import read_immich_config, logout_immich, immich_upload_albums, immich_upload_ALL, immich_download_albums, immich_download_ALL, immich_remove_empty_albums, immich_remove_duplicates_albums, immich_remove_all_assets, immich_remove_all_albums, immich_remove_orphan_assets

DEFAULT_DUPLICATES_ACTION = False
EXECUTION_MODE = "default"
# -------------------------------------------------------------
# Determine the Execution mode based on the provide arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():

    # AUTOMATED-MIGRATION MODE:
    if ARGS['AUTOMATED-MIGRATION']:
        EXECUTION_MODE = 'AUTOMATED-MIGRATION'
        mode_AUTOMATED_MIGRATION()

    # Google Photos Mode:
    elif "-gitf" in sys.argv or "--google-input-takeout-folder" in sys.argv:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()

    # Synology Photos Modes:
    elif ARGS['synology-remove-empty-albums']:
        EXECUTION_MODE = 'synology-remove-empty-albums'
        mode_synology_remove_empty_albums()
    elif ARGS['synology-remove-duplicates-albums']:
        EXECUTION_MODE = 'synology-remove-duplicates-albums'
        mode_synology_remove_duplicates_albums()
    elif ARGS['synology-upload-albums'] != "":
        EXECUTION_MODE = 'synology-upload-albums'
        mode_synology_upload_albums()
    elif ARGS['synology-upload-all'] != "":
        EXECUTION_MODE = 'synology-upload-all'
        mode_synology_upload_ALL()
    elif ARGS['synology-download-albums'] != "":
        EXECUTION_MODE = 'synology-download-albums'
        mode_synology_download_albums()
    elif ARGS['synology-download-all'] != "":
        EXECUTION_MODE = 'synology-download-all'
        mode_synology_download_ALL()
    elif ARGS['synology-remove-all-assets'] != "":
        EXECUTION_MODE = 'synology-remove-all-assets'
        mode_synology_remove_all_assets()

    # Immich Photos Modes:
    elif ARGS['immich-remove-empty-albums']:
        EXECUTION_MODE = 'immich-remove-empty-albums'
        mode_immich_remove_empty_albums()
    elif ARGS['immich-remove-duplicates-albums']:
        EXECUTION_MODE = 'immich-remove-duplicates-albums'
        mode_immich_remove_duplicates_albums()
    elif ARGS['immich-upload-albums'] != "":
        EXECUTION_MODE = 'immich-upload-albums'
        mode_immich_upload_albums()
    elif ARGS['immich-upload-all'] != "":
        EXECUTION_MODE = 'immich-upload-all'
        mode_immich_upload_ALL()
    elif ARGS['immich-download-albums'] != "":
        EXECUTION_MODE = 'immich-download-albums'
        mode_immich_download_albums()
    elif ARGS['immich-download-all'] != "":
        EXECUTION_MODE = 'immich-download-all'
        mode_immich_download_ALL()
    elif ARGS['immich-remove-orphan-assets'] != "":
        EXECUTION_MODE = 'immich-remove-orphan-assets'
        mode_immich_remove_orphan_assets()
    elif ARGS['immich-remove-all-assets'] != "":
        EXECUTION_MODE = 'immich-remove-all-assets'
        mode_immich_remove_all_assets()
    elif ARGS['immich-remove-all-albums'] != "":
        EXECUTION_MODE = 'immich-remove-all-albums'
        mode_immich_remove_all_albums()

    # Other Stand-alone Extra Modes:
    elif ARGS['fix-symlinks-broken'] != "":
        EXECUTION_MODE = 'fix-symlinks'
        mode_fix_symlinkgs()
    elif ARGS['find-duplicates'] != ['list', '']:
        EXECUTION_MODE = 'find_duplicates'
        mode_find_duplicates()
    elif ARGS['process-duplicates'] != "":
        EXECUTION_MODE = 'process-duplicates'
        mode_process_duplicates()
    elif ARGS['rename-folders-content-based'] != "":
        EXECUTION_MODE = 'rename-folders-content-based'
        mode_folders_rename_content_based()

    else:
        EXECUTION_MODE = ''  # Opción por defecto si no se cumple ninguna condición
        LOGGER.error(f"ERROR   : Unable to detect any valid execution mode.")
        LOGGER.error(f"ERROR   : Please, run '{os.path.basename(sys.argv[0])} --help' to know more about how to invoke the Script.")
        LOGGER.error("")
        # PARSER.print_help()
        sys.exit(1)

####################################
# EXTRA MODE: AUTOMATED-MIGRATION: #
####################################
def mode_AUTOMATED_MIGRATION(log_level=logging.INFO):
    SOURCE = ARGS['AUTOMATED-MIGRATION'][0]
    TARGET = ARGS['AUTOMATED-MIGRATION'][1]
    INTERMEDIATE_FOLDER = ''

    LOGGER.info(f"INFO    : -AUTO, --AUTOMATED-MIGRATION Mode detected")
    if not ARGS['SOURCE-TYPE-TAKEOUT-FOLDER']:
        LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE>', f"'{ARGS['AUTOMATED-MIGRATION'][0]}'").replace('<TARGET>', f"'{ARGS['AUTOMATED-MIGRATION'][1]}'"))
    else:
        LOGGER.info(HELP_TEXTS["AUTOMATED-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{ARGS['AUTOMATED-MIGRATION'][0]}'").replace('<TARGET>', f"'{ARGS['AUTOMATED-MIGRATION'][1]}'").replace('Downloading', 'Analyzing and Fixing'))
    LOGGER.info(f"INFO    : Selected SOURCE : {SOURCE}")
    LOGGER.info(f"INFO    : Selected TARGET : {TARGET}")
    LOGGER.info("")
    if not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # =========================
        # FIRST PROCESS THE SOURCE:
        # =========================
        LOGGER.info(f'INFO    : Downloading/Processing Asset from {SOURCE}...')
        # If the SOURCE is 'google-photos' or a valid Takeout Folder
        if SOURCE.lower() == 'google-photos' or ARGS['SOURCE-TYPE-TAKEOUT-FOLDER']:
            # Configure default arguments for mode_google_takeout() execution and RUN it
            if SOURCE.lower() == 'google-photos':
                input_folder = ARGS['input-folder']
            else:
                input_folder = SOURCE

            # Define the INTERMEDIATE_FOLDER
            if ARGS['output-folder']:
                INTERMEDIATE_FOLDER = ARGS['output-folder']
            else:
                INTERMEDIATE_FOLDER = f"{ARGS['input-folder']}_{TIMESTAMP}"
            # Set ARGS['output-folder'] to INTERMEDIATE_FOLDER
            ARGS['output-folder'] = INTERMEDIATE_FOLDER

            # Check if already exists an 'Albums' subfolder within input_folder, in that case, the input_folder have been already processed by CloudPhotoMigrator and no need to execute GPTH step again
            # but in that case, we need to move the folder to the intermediate folder
            if os.path.isdir(os.path.join(input_folder,'Albums')):
                if not Utils.copy_move_folder(input_folder, INTERMEDIATE_FOLDER, move=False):
                    LOGGER.error(f"ERROR   : Unable to copy Folder '{input_folder}' to '{INTERMEDIATE_FOLDER}'. Exiting...")
                    sys.exit(-1)
            else:
                # Set other settings for mode_google_takeout()
                ARGS['google-input-takeout-folder'] = input_folder
                ARGS['google-remove-duplicates-files'] = True
                need_unzip = Utils.contains_zip_files(input_folder)
                if need_unzip:
                    ARGS['google-move-takeout-folder'] = True
                # Execute Mode mode_google_takeout()
                mode_google_takeout(user_confirmation=False, log_level=logging.INFO)

        # If the SOURCE is 'synology-photos'
        elif SOURCE.lower() == 'synology-photos':
            # Define the INTERMEDIATE_FOLDER
            if ARGS['output-folder']:
                INTERMEDIATE_FOLDER = ARGS['output-folder']
            else:
                INTERMEDIATE_FOLDER = f"Synology_Download_ALL_{TIMESTAMP}"
            # Set ARGS['synology-download-all'] to INTERMEDIATE_FOLDER
            ARGS['synology-download-all'] = INTERMEDIATE_FOLDER
            # Execute Mode mode_synology_download_ALL()
            mode_synology_download_ALL(user_confirmation=False, log_level=logging.INFO)

        # If the SOURCE is 'immich-photos'
        elif SOURCE.lower() == 'immich-photos':
            # Define the INTERMEDIATE_FOLDER
            if ARGS['output-folder']:
                INTERMEDIATE_FOLDER = ARGS['output-folder']
            else:
                INTERMEDIATE_FOLDER = f"Immich_Download_ALL_{TIMESTAMP}"
            # Set ARGS['immich-download-all'] to INTERMEDIATE_FOLDER
            ARGS['immich-download-all'] = INTERMEDIATE_FOLDER
            # Execute Mode mode_immich_download_ALL()
            mode_immich_download_ALL(user_confirmation=False, log_level=logging.INFO)

        # =========================
        # SECOND PROCESS THE TARGET:
        # =========================
        LOGGER.info(f'INFO    : Uploading/Processing Asset to {TARGET}...')
        # if the TARGET is 'synology-photos'
        if TARGET.lower() == 'synology-photos':
            ARGS['synology-upload-all'] = INTERMEDIATE_FOLDER
            mode_synology_upload_ALL(user_confirmation=False, log_level=logging.INFO)

        # If the TARGET is 'immich-photos'
        elif TARGET.lower() == 'immich-photos':
            ARGS['immich-upload-all'] = INTERMEDIATE_FOLDER
            mode_immich_upload_ALL(user_confirmation=False, log_level=logging.INFO)


##############################
# EXTRA MODE: GOOGLE PHOTOS: #
##############################
def mode_google_takeout(user_confirmation=True, log_level=logging.INFO):
    # Configure default arguments for mode_google_takeout() execution
    if ARGS['output-folder']:
        OUTPUT_TAKEOUT_FOLDER = ARGS['output-folder']
    else:
        OUTPUT_TAKEOUT_FOLDER = f"{ARGS['google-input-takeout-folder']}_{ARGS['google-output-folder-suffix']}_{TIMESTAMP}"
    input_folder = ARGS['google-input-takeout-folder']
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        ARGS['google-input-zip-folder'] = input_folder
        ARGS['google-input-takeout-folder'] = os.path.join(os.path.dirname(input_folder),f'Unzipped_Takeout_{TIMESTAMP}')
        LOGGER.info("")
        LOGGER.info(f"INFO    : ZIP files have been detected in {input_folder}'. Files will be unziped first...")
        LOGGER.info("")
    else:
        ARGS['google-input-takeout-folder'] = input_folder
    # Mensajes informativos
    LOGGER.info(f"Settings for Google Takeout Photos Module:")
    LOGGER.info(f"------------------------------------------")
    LOGGER.info(f"INFO    : Using Suffix                             : '{ARGS['google-output-folder-suffix']}'")
    LOGGER.info(f"INFO    : Albums Folder Structure                  : '{ARGS['google-albums-folders-structure']}'")
    LOGGER.info(f"INFO    : No Albums Folder Structure               : '{ARGS['google-no-albums-folder-structure']}'")
    LOGGER.info(f"INFO    : Creates symbolic links for Albums        : '{ARGS['google-create-symbolic-albums']}'")
    LOGGER.info(f"INFO    : Ignore Check Google Takeout Structure    : '{ARGS['google-ignore-check-structure']}'")
    LOGGER.info(f"INFO    : Move Original Assets to Output Folder    : '{ARGS['google-move-takeout-folder']}'")
    LOGGER.info(f"INFO    : Remove Duplicates files in Output folder : '{ARGS['google-remove-duplicates-files']}'")
    LOGGER.info(f"INFO    : Skip Extra Assets (-edited,-effects...)  : '{ARGS['google-skip-extras-files']}'")
    LOGGER.info(f"INFO    : Skip Moving Albums to 'Albums' folder    : '{ARGS['google-skip-move-albums']}'")
    LOGGER.info(f"INFO    : Skip GPTH Tool                           : '{ARGS['google-skip-gpth-tool']}'")
    LOGGER.info("")
    LOGGER.info(f"Folders for Google Takeout Photos Module:")
    LOGGER.info(f"------------------------------------------")
    if ARGS['google-input-zip-folder']!="":
        LOGGER.info(f"INFO    : Input Takeout folder (zipped detected)   : '{ARGS['google-input-zip-folder']}'")
        LOGGER.info(f"INFO    : Input Takeout will be unziped to folder  : '{ARGS['google-input-takeout-folder']}'")
    else:
        LOGGER.info(f"INFO    : Input Takeout folder                     : '{ARGS['google-input-takeout-folder']}'")
    LOGGER.info(f"INFO    : OUTPUT folder                            : '{OUTPUT_TAKEOUT_FOLDER}'")
    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["google-photos-takeout"].replace('<TAKEOUT_FOLDER>',f"'{ARGS['google-input-takeout-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if ARGS['google-input-zip-folder']=="":
            LOGGER.warning(f"WARNING : No argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if ARGS['google-albums-folders-structure'].lower()!='flatten':
            LOGGER.warning(f"WARNING : Flag detected '-gafs, --google-albums-folders-structure'. Folder structure '{ARGS['google-albums-folders-structure']}' will be applied on each Album folder...")
        if ARGS['google-no-albums-folder-structure'].lower()!='year/month':
            LOGGER.warning(f"WARNING : Flag detected '-gnaf, --google-no-albums-folder-structure'. Folder structure '{ARGS['google-no-albums-folder-structure']}' will be applied on 'No-Albums' folder (Photos without Albums)...")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"WARNING : Flag detected '-gsgt, --google-skip-gpth-tool'. Skipping Processing photos with GPTH Tool...")
        if ARGS['google-skip-extras-files']:
            LOGGER.warning(f"WARNING : Flag detected '-gsef, --google-skip-extras-files'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if ARGS['google-skip-move-albums']:
            LOGGER.warning(f"WARNING : Flag detected '-gsma, --google-skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.warning(f"WARNING : Flag detected '-gcsa, --google-create-symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning(f"WARNING : Flag detected '-gics, --google-ignore-check-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if ARGS['google-move-takeout-folder']:
            LOGGER.warning(f"WARNING : Flag detected '-gmtf, --google-move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_TAKEOUT_FOLDER>...")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.warning(f"WARNING : Flag detected '-grdf, --google-remove-duplicates-files'. All duplicates files within OUTPUT_TAKEOUT_FOLDER will be removed after fixing them...")
        if ARGS['no-log-file']:
            LOGGER.warning(f"WARNING : Flag detected '-nolog, --no-log-file'. Skipping saving output into log file...")
        # Call the Function
        albums_found, symlink_fixed, symlink_not_fixed, duplicates_found = google_takeout_processor(OUTPUT_TAKEOUT_FOLDER=OUTPUT_TAKEOUT_FOLDER)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info(f"INFO    : All the Photos/Videos Fixed can be found on folder: '{OUTPUT_TAKEOUT_FOLDER}'")
        LOGGER.info("")
        LOGGER.info("===============================================")
        LOGGER.info("                FINAL SUMMARY:                 ")
        LOGGER.info("===============================================")
        if not ARGS['google-move-takeout-folder']:
            LOGGER.info(f"Total files in Takeout folder        : {Utils.count_files_in_folder(ARGS['google-input-takeout-folder'])}")
        LOGGER.info(f"Total final files in Output folder   : {Utils.count_files_in_folder(OUTPUT_TAKEOUT_FOLDER)}")
        LOGGER.info(f"Total Albums folders found           : {albums_found}")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.info(f"Total Symlinks Fixed                 : {symlink_fixed}")
            LOGGER.info(f"Total Symlinks Not Fixed             : {symlink_not_fixed}")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.info(f"Total Duplicates Removed             : {duplicates_found}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                   : {formatted_duration}")
        LOGGER.info("===============================================")
        LOGGER.info("")


#################################
# EXTRA MODES: SYNOLOGY PHOTOS: #
#################################
def mode_synology_upload_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-suAlb, --synology-upload-albums'.")
        LOGGER.info(HELP_TEXTS["synology-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['synology-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO    : Synology Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO    : Find Albums in Folder    : {ARGS['synology-upload-albums']}")
    LOGGER.info("")

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Call the Function
        albums_crated, albums_skipped, photos_added = synology_upload_albums(ARGS['synology-upload-albums'], log_level=logging.WARNING)
        # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
        LOGGER.info("")
        total_duplicates_albums_removed = synology_remove_duplicates_albums(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums created                    : {albums_crated}")
        LOGGER.info(f"Total Albums skipped                    : {albums_skipped}")
        LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_upload_ALL(user_confirmation=True, log_level=logging.INFO):
    albums_folders = ARGS['albums-folders']
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-suAll, --synology-upload-all'.")
        if albums_folders:
            LOGGER.info(f"INFO    : Flag detected '-AlbFld, --albums-folders' = ['{albums_folders}'].")
        LOGGER.info(HELP_TEXTS["synology-upload-all"].replace('<INPUT_FOLDER>', f"'{ARGS['synology-upload-all']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Synology Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        LOGGER.info(f"INFO    : Find Assets in Folder    : {ARGS['synology-upload-all']}")
        LOGGER.info("")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums = synology_upload_ALL (ARGS['synology-upload-all'], albums_folders=albums_folders, log_level=logging.WARNING)
        # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
        LOGGER.info("")
        total_duplicates_albums_removed = synology_remove_duplicates_albums(log_level=logging.WARNING)
        # logout from Synology Photos.
        LOGGER.info("")
        logout_synology()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded_within_albums}")
        LOGGER.info(f"Total Assets added without Albums       : {total_assets_uploaded_without_albums}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_synology_download_albums(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(f"INFO    : Synology Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info(f"INFO    : Albums to extract   : {ARGS['synology-download-albums']}")
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-sdAlb, --synology-download-albums <ALBUMS_NAME>'.".replace("'<ALBUMS_NAME>'", f"{ARGS['synology-download-albums']}"))
        LOGGER.info(HELP_TEXTS["synology-download-albums"].replace("'<ALBUMS_NAME>'", f"{ARGS['synology-download-albums']}").replace("<OUTPUT_FOLDER>", ARGS['output-folder']))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Call the Function
        albums_downloaded, photos_downloaded = synology_download_albums(albums_name=ARGS['synology-download-albums'], output_folder=ARGS['output-folder'], log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"Total Photos downloaded from Albums     : {photos_downloaded}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_download_ALL(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(f"INFO    : Synology Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-sdAll, --synology-download-all'.")
        LOGGER.info(HELP_TEXTS["synology-download-all"].replace('<OUTPUT_FOLDER>', f"{ARGS['synology-download-all']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Call the Function
        albums_downloaded, assets_downloaded, assets_downloaded_within_albums, assets_downloaded_without_albums = synology_download_ALL(output_folder=ARGS['synology-download-all'], log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info(f"Total Assets downloaded within albums   : {assets_downloaded_within_albums}")
        LOGGER.info(f"Total Assets downloaded without albums  : {assets_downloaded_without_albums}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_remove_empty_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-srEmpAlb, --synology-remove-empty-albums'.")
        LOGGER.info(HELP_TEXTS["synology-remove-empty-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Synology Photos: 'Remove Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-srEmpAlb, --synology-remove-empty-albums'. The Script will look for any empty album in Synology Photos database and will delete them (if any empty album is found).")
        # Call the Function
        albums_removed = synology_remove_empty_albums(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Empty Albums removed              : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_remove_duplicates_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-srDupAlb, --synology-remove-duplicates-albums'.")
        LOGGER.info(HELP_TEXTS["synology-remove-duplicates-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Synology Photos: 'Remove Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-srDupAlb, --synology-remove-duplicates-albums'. The Script will look for any duplicated album in Synology Photos database and will delete them (if any duplicated album is found).")
        # Call the Function
        albums_removed, folders_removed = synology_remove_duplicates_albums(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Duplicates Albums removed         : {albums_removed}")
        LOGGER.info(f"Total Folders removed                   : {folders_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_synology_remove_all_assets(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-srAll, --synology-remove-all-assets'.")
        LOGGER.info(HELP_TEXTS["synology-remove-all-assets"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Synology Photos: 'Remove ALL Assets' Mode detected. Only this module will be run!!!")
        # Call the Function
        assets_removed, albums_removed, folders_removed = synology_remove_all_assets(log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info(f"Total Folders removed                   : {folders_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_remove_all_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-srAllAlb, --synology-remove-all-albums'.")
        if ARGS['remove-albums-assets']:
            LOGGER.info(f"INFO    : Flag detected '-rAlbAss, --remove-albums-assets'.")
        LOGGER.info(HELP_TEXTS["synology-remove-all-albums"])
        if ARGS['remove-albums-assets']:
            LOGGER.info(f"Since, flag '-rAlbAss, --remove-albums-assets' have been detected, ALL the Assets associated to any Albums will also be deleted.")
            LOGGER.info("")
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Synology Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        LOGGER.info("")
        # Call the Function
        assets_removed, albums_removed, folders_removed = synology_remove_all_albums(removeAlbumsAssets= ARGS['remove-albums-assets'], log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info(f"Total Folders removed                   : {folders_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


###############################
# EXTRA MODES: IMMICH PHOTOS: #
###############################
def mode_immich_upload_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-iuAlb, --immich-upload-albums'.")
        LOGGER.info(HELP_TEXTS["immich-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['immich-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        LOGGER.info(f"INFO    : Find Albums in Folder    : {ARGS['immich-upload-albums']}")
        LOGGER.info("")
        # Call the Function
        albums_crated, albums_skipped, photos_added, duplicates_assets_removed = immich_upload_albums(ARGS['immich-upload-albums'], log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums created                    : {albums_crated}")
        LOGGER.info(f"Total Albums skipped                    : {albums_skipped}")
        LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
        LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_upload_ALL(user_confirmation=True, log_level=logging.INFO):
    albums_folders = ARGS['albums-folders']
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-iuAll, --immich-upload-all'.")
        if albums_folders:
            LOGGER.info(f"INFO    : Flag detected '-AlbFld, --albums-folders'.")
        LOGGER.info(HELP_TEXTS["immich-upload-all"].replace('<INPUT_FOLDER>', f"'{ARGS['immich-upload-all']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        LOGGER.info(f"INFO    : Find Assets in Folder    : {ARGS['immich-upload-all']}")
        LOGGER.info("")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, duplicates_assets_removed = immich_upload_ALL(ARGS['immich-upload-all'], albums_folders=albums_folders, log_level=logging.WARNING)
        # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
        LOGGER.info("")
        total_duplicates_albums_removed = immich_remove_duplicates_albums(log_level=logging.WARNING)
        LOGGER.info("")
        immich_remove_empty_albums()
        # logout from Immich Photos.
        LOGGER.info("")
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded_within_albums}")
        LOGGER.info(f"Total Assets added without Albums       : {total_assets_uploaded_without_albums}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_download_albums(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(f"INFO    : Immich Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info(f"INFO    : Albums to extract   : {ARGS['immich-download-albums']}")
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-idAlb, --immich-download-albums <ALBUMS_NAME>'.".replace("'<ALBUMS_NAME>'", f"{ARGS['immich-download-albums']}"))
        LOGGER.info(HELP_TEXTS["immich-download-albums"].replace("'<ALBUMS_NAME>'", f"{ARGS['immich-download-albums']}").replace("<OUTPUT_FOLDER>", ARGS['output-folder']))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Call the Function
        albums_downloaded, assets_downloaded = immich_download_albums(albums_name=ARGS['immich-download-albums'], output_folder=ARGS['output-folder'], log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_download_ALL(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(f"INFO    : Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-idAll, --immich-download-all'.")
        LOGGER.info(HELP_TEXTS["immich-download-all"].replace('<OUTPUT_FOLDER>', f"{ARGS['immich-download-all']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Call the Function
        albums_downloaded, assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums = immich_download_ALL(output_folder=ARGS['immich-download-all'], log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info(f"Total Assets downloaded within albums   : {total_assets_downloaded_within_albums}")
        LOGGER.info(f"Total Assets downloaded without albums  : {total_assets_downloaded_without_albums}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_remove_empty_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-irEmpAlb, --immich-remove-empty-albums'.")
        LOGGER.info(HELP_TEXTS["immich-remove-empty-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Delete Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-irEmpAlb, --immich-remove-empty-albums'. The Script will look for any empty album in Immich Photos database and will delete them (if any empty album is found).")
        # Call the Function
        albums_removed = immich_remove_empty_albums(log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Empty Albums removed              : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_remove_duplicates_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-irDupAlb, --immich-remove-duplicates-albums'.")
        LOGGER.info(HELP_TEXTS["immich-remove-duplicates-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Delete Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-irDupAlb, --immich-remove-duplicates-albums'. The Script will look for any duplicated album in Immich Photos database and will delete them (if any duplicated album is found).")
        # Call the Function
        albums_removed = immich_remove_duplicates_albums(log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Duplicates Albums removed         : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_remove_orphan_assets(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-irOrphan, --immich-remove-orphan-assets'.")
        LOGGER.info(HELP_TEXTS["immich-remove-orphan-assets"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        # LOGGER.info(f"INFO    : Find Albums in Folder    : {ARGS['immich-upload-albums']}")
        LOGGER.info("")
        # Call the Function
        assets_removed = immich_remove_orphan_assets(user_confirmation=user_confirmation, log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Orphan Assets removed             : {assets_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_remove_all_assets(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-irAll, --immich-remove-all-assets'.")
        LOGGER.info(HELP_TEXTS["immich-remove-all-assets"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Delete ALL Assets' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        # LOGGER.info(f"INFO    : Find Albums in Folder    : {ARGS['immich-upload-albums']}")
        LOGGER.info("")
        # Call the Function
        assets_removed, albums_removed = immich_remove_all_assets(log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_remove_all_albums(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(f"INFO    : Flag detected '-irAllAlb, --immich-remove-all-albums'.")
        if ARGS['remove-albums-assets']:
            LOGGER.info(f"INFO    : Flag detected '-rAlbAss, --remove-albums-assets'.")
        LOGGER.info(HELP_TEXTS["immich-remove-all-albums"])
        if ARGS['remove-albums-assets']:
            LOGGER.info(f"Since, flag '-rAlbAss, --remove-albums-assets' have been detected, ALL the Assets associated to any Albums will also be deleted.")
            LOGGER.info("")
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
        LOGGER.info("")
        # LOGGER.info(f"INFO    : Find Albums in Folder    : {ARGS['immich-upload-albums']}")
        LOGGER.info("")
        # Call the Function
        albums_removed, assets_removed = immich_remove_all_albums(deleteAlbumsAssets = ARGS['remove-albums-assets'], log_level=logging.WARNING)
        logout_immich()
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


#################################
# OTHER STANDALONE EXTRA MODES: #
#################################
def mode_fix_symlinkgs(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["fix-symlinks-broken"].replace('<FOLDER_TO_FIX>', f"'{ARGS['fix-symlinks-broken']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Fixing broken symbolic links Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Fixing broken symbolic links in folder '{ARGS['fix-symlinks-broken']}'...")
        symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(ARGS['fix-symlinks-broken'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Fixed Symbolic Links              : {symlinks_fixed}")
        LOGGER.info(f"Total No Fixed Symbolic Links           : {symlinks_not_fixed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_find_duplicates(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(f"INFO    : Duplicates Action             : {ARGS['duplicates-action']}")
    LOGGER.info(f"INFO    : Find Duplicates in Folders    : {ARGS['duplicates-folders']}")
    LOGGER.info("")
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["find-duplicates"].replace('<DUPLICATES_FOLDER>', f"'{ARGS['duplicates-folders']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"WARNING : Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
        duplicates_files_found = find_duplicates(duplicates_action=ARGS['duplicates-action'], duplicates_folders=ARGS['duplicates-folders'], deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            LOGGER.error("ERROR   : Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exists.")
            sys.exit(-1)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Duplicates Found                  : {duplicates_files_found}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_process_duplicates(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["process-duplicates"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Flag detected '-pd, --process-duplicates'. The Script will process the '{ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
        LOGGER.info(f"INFO    : Processing Duplicates Files based on Actions given in {os.path.basename(ARGS['process-duplicates'])} file...")
        removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(ARGS['process-duplicates'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Removed Duplicates                : {removed_duplicates}")
        LOGGER.info(f"Total Restored Duplicates               : {restored_duplicates}")
        LOGGER.info(f"Total Replaced Duplicates               : {replaced_duplicates}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_folders_rename_content_based(user_confirmation=True, log_level=logging.INFO):
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["rename-folders-content-based"].replace('<ALBUMS_FOLDER>', f"'{ARGS['rename-folders-content-based']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-ra, --rename-folders-content-based'. The Script will look for any Subfolder in '{ARGS['rename-folders-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
        renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(ARGS['rename-folders-content-based'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("                  FINAL SUMMARY:                  ")
        LOGGER.info("==================================================")
        LOGGER.info(f"Total Albums folders renamed             : {renamed_album_folders}")
        LOGGER.info(f"Total Albums folders duplicated          : {duplicates_album_folders}")
        LOGGER.info(f"Total Albums duplicated fully merged     : {duplicates_albums_fully_merged}")
        LOGGER.info(f"Total Albums duplicated not fully merged : {duplicates_albums_not_fully_merged}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                       : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")
