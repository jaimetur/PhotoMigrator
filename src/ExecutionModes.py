from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION
import os, sys
from datetime import datetime, timedelta
import Utils
import logging
import cProfile
import pstats
import threading
import time
import shutil
from CustomLogger import set_log_level
from Duplicates import find_duplicates, process_duplicates_actions
from ClassTakeoutFolder import ClassTakeoutFolder
from ClassSynologyPhotos import ClassSynologyPhotos
from ClassImmichPhotos import ClassImmichPhotos
from AutomaticMode import mode_AUTOMATIC_MIGRATION

DEFAULT_DUPLICATES_ACTION = False
EXECUTION_MODE = "default"
terminal_width = shutil.get_terminal_size().columns

# -------------------------------------------------------------
# Set Profile to analyze and optimize code:
# -------------------------------------------------------------
def profile_and_print(function_to_analyze, *args, **kwargs):
    """
    Executes the profiler and displays results in real-time while the function runs.
    Supports both positional (`args`) and keyword (`kwargs`) arguments.
    """
    profiler = cProfile.Profile()
    profiler.enable()

    # Ensure the function receives arguments correctly
    thread = threading.Thread(target=function_to_analyze, args=args, kwargs=kwargs)
    thread.start()

    # While the function is running, print profiling results every 5 seconds
    while thread.is_alive():
        time.sleep(10)
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.strip_dirs().sort_stats("cumulative").print_stats(20)  # Show top 10 slowest functions
        profiler.enable()  # Re-enable profiling to continue

    profiler.disable()  # Ensure the profiler stops after execution
    print("\n🔍 **Final Profile Report:**")
    stats = pstats.Stats(profiler)
    stats.strip_dirs().sort_stats("cumulative").print_stats(20)  # Show top 20 slowest functions



# -------------------------------------------------------------
# Determine the Execution mode based on the provide arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():
    # # AUTOMATIC-MIGRATION MODE:
    # if ARGS['AUTOMATIC-MIGRATION']:
    #     EXECUTION_MODE = 'AUTOMATIC-MIGRATION'
    #     mode_AUTOMATIC_MIGRATION()
    #     # profile_and_print(function_to_analyze=mode_AUTOMATIC_MIGRATION, show_dashboard=False)  # Profiler to analyze and optimize each function.

    # AUTOMATIC-MIGRATION MODE:
    if ARGS['source'] and ARGS['target']:
        EXECUTION_MODE = 'AUTOMATIC-MIGRATION'
        mode_AUTOMATIC_MIGRATION(show_gpth_progress=ARGS['show-gpth-progress'])
        # profile_and_print(function_to_analyze=mode_AUTOMATIC_MIGRATION, show_dashboard=False)  # Profiler to analyze and optimize each function.

    # Google Photos Mode:
    # elif "-gtProc" in sys.argv or "--google-takeout-to-process" in sys.argv:
    elif ARGS['google-takeout-to-process']:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()

    # Synology Photos Modes:
    elif ARGS['synology-remove-albums']:
        EXECUTION_MODE = 'synology-remove-albums'
        mode_cloud_remove_albums_by_name_pattern(cloud='Synology')
    elif ARGS['synology-rename-albums'][0]:
        EXECUTION_MODE = 'synology-rename-albums'
        mode_cloud_rename_albums(cloud='Synology')
    elif ARGS['synology-remove-empty-albums']:
        EXECUTION_MODE = 'synology-remove-empty-albums'
        mode_cloud_remove_empty_albums(cloud='Synology')
    elif ARGS['synology-remove-duplicates-albums']:
        EXECUTION_MODE = 'synology-remove-duplicates-albums'
        mode_cloud_remove_duplicates_albums(cloud='Synology')
    elif ARGS['synology-merge-duplicates-albums']:
        EXECUTION_MODE = 'synology-merge-duplicates-albums'
        mode_cloud_merge_duplicates_albums(cloud='Synology')
    elif ARGS['synology-remove-all-albums'] != "":
        EXECUTION_MODE = 'synology-remove-all-albums'
        # mode_cloud_remove_all_albums(cloud='Synology')
        mode_cloud_remove_albums_by_name_pattern(cloud='Synology')
    elif ARGS['synology-remove-all-assets'] != "":
        EXECUTION_MODE = 'synology-remove-all-assets'
        mode_cloud_remove_ALL(cloud='Synology')
    elif ARGS['synology-upload-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to upload (default albums_to_upload='all')
        EXECUTION_MODE = 'synology-upload-albums'
        mode_cloud_upload_albums(cloud='Synology')
    elif ARGS['synology-upload-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'synology-upload-all'
        mode_cloud_upload_ALL(cloud='Synology')
    elif ARGS['synology-download-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to download (default albums_to_download='all')
        EXECUTION_MODE = 'synology-download-albums'
        mode_cloud_download_albums(cloud='Synology')
    elif ARGS['synology-download-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'synology-download-all'
        mode_cloud_download_ALL(cloud='Synology')


    # Immich Photos Modes:
    elif ARGS['immich-remove-albums']:
        EXECUTION_MODE = 'immich-remove-albums'
        mode_cloud_remove_albums_by_name_pattern(cloud='Immich')
    elif ARGS['immich-rename-albums'][0]:
        EXECUTION_MODE = 'immich-rename-albums'
        mode_cloud_rename_albums(cloud='Immich')
    elif ARGS['immich-remove-empty-albums']:
        EXECUTION_MODE = 'immich-remove-empty-albums'
        mode_cloud_remove_empty_albums(cloud='Immich')
    elif ARGS['immich-remove-duplicates-albums']:
        EXECUTION_MODE = 'immich-remove-duplicates-albums'
        mode_cloud_remove_duplicates_albums(cloud='Immich')
    elif ARGS['immich-merge-duplicates-albums']:
        EXECUTION_MODE = 'immich-merge-duplicates-albums'
        mode_cloud_merge_duplicates_albums(cloud='Immich')
    elif ARGS['immich-remove-all-albums'] != "":
        EXECUTION_MODE = 'immich-remove-all-albums'
        # mode_cloud_remove_all_albums(cloud='Immich')
        mode_cloud_remove_albums_by_name_pattern(cloud='Immich')
    elif ARGS['immich-remove-all-assets'] != "":
        EXECUTION_MODE = 'immich-remove-all-assets'
        mode_cloud_remove_ALL(cloud='Immich')
    elif ARGS['immich-remove-orphan-assets'] != "":
        EXECUTION_MODE = 'immich-remove-orphan-assets'
        mode_cloud_remove_orphan_assets(cloud='Immich')
    elif ARGS['immich-upload-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to upload (default albums_to_upload='all')
        EXECUTION_MODE = 'immich-upload-albums'
        mode_cloud_upload_albums(cloud='Immich')
    elif ARGS['immich-upload-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'immich-upload-all'
        mode_cloud_upload_ALL(cloud='Immich')
    elif ARGS['immich-download-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to download (default albums_to_download='all')
        EXECUTION_MODE = 'immich-download-albums'
        mode_cloud_download_albums(cloud='Immich')
    elif ARGS['immich-download-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'immich-download-all'
        mode_cloud_download_ALL(cloud='Immich')


    # Other Stand-alone Extra Features:
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

###################################
# FEATURE: GOOGLE PHOTOS TAKEOUT: #
###################################
def mode_google_takeout(user_confirmation=True, log_level=logging.INFO):
    # Configure default arguments for mode_google_takeout() execution
    LOGGER.info(f"Starting Google Takeout Photos Processor Feature...")
    LOGGER.info("")
    if ARGS['output-folder']:
        OUTPUT_TAKEOUT_FOLDER = ARGS['output-folder']
    else:
        OUTPUT_TAKEOUT_FOLDER = f"{ARGS['google-takeout-to-process']}_{ARGS['google-output-folder-suffix']}_{TIMESTAMP}"
    input_folder = ARGS['google-takeout-to-process']
    if not Utils.dir_exists(input_folder):
        LOGGER.error(f"ERROR   : The Input Folder {input_folder} does not exists. Exiting...")
        sys.exit(-1)
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        ARGS['google-input-zip-folder'] = input_folder
        LOGGER.info("")
        LOGGER.info(f"INFO    : ZIP files have been detected in {input_folder}'. Files will be unziped first...")
        LOGGER.info("")

    # Mensajes informativos
    LOGGER.info(f"Folders for Google Takeout Photos Feature:")
    LOGGER.info(f"-------------------------------------------")
    if ARGS['google-input-zip-folder']:
        LOGGER.info(f"INFO    : Input Takeout folder (zipped detected)   : '{ARGS['google-input-zip-folder']}'")
        LOGGER.info(f"INFO    : Input Takeout will be unzipped to folder : '{input_folder}_unzipped_{TIMESTAMP}'")
    else:
        LOGGER.info(f"INFO    : Input Takeout folder                     : '{ARGS['google-takeout-to-process']}'")
    LOGGER.info(f"INFO    : Output Takeout folder                    : '{OUTPUT_TAKEOUT_FOLDER}'")
    LOGGER.info(f"")

    LOGGER.info(f"Settings for Google Takeout Photos Feature:")
    LOGGER.info(f"-------------------------------------------")
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
    LOGGER.info(f"INFO    : Show GPTH Progress                       : '{ARGS['show-gpth-progress']}'")
    LOGGER.info(f"INFO    : Show GPTH Errors                         : '{ARGS['show-gpth-errors']}'")
    LOGGER.info("")

    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["google-photos-takeout"].replace('<TAKEOUT_FOLDER>',f"'{ARGS['google-takeout-to-process']}'"))
        LOGGER.warning('-' * terminal_width)
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
        # Create the Object
        takeout = ClassTakeoutFolder(ARGS['google-takeout-to-process'])
        # Call the Function
        albums_found, symlink_fixed, symlink_not_fixed, duplicates_found, initial_takeout_numfiles, removed_empty_folders = takeout.process(output_takeout_folder=OUTPUT_TAKEOUT_FOLDER, capture_output=ARGS['show-gpth-progress'], capture_errors=ARGS['show-gpth-errors'], log_level=log_level)

        # Count files in Takeout Folder
        if need_unzip:
            input_folder = f"{input_folder}_unzipped_{TIMESTAMP}"
        # initial_takeout_total_files = Utils.count_files_in_folder(input_folder)
        initial_takeout_total_images = Utils.count_images_in_folder(input_folder)
        initial_takeout_total_videos = Utils.count_videos_in_folder(input_folder)
        initial_takeout_total_sidecars = Utils.count_sidecars_in_folder(input_folder)
        initial_takeout_total_metadata = Utils.count_metadatas_in_folder(input_folder)
        initial_takeout_total_supported_files = initial_takeout_total_images + initial_takeout_total_videos + initial_takeout_total_sidecars + initial_takeout_total_metadata

        # Count Files in Output Folder
        total_files = Utils.count_files_in_folder(OUTPUT_TAKEOUT_FOLDER)
        total_images = Utils.count_images_in_folder(OUTPUT_TAKEOUT_FOLDER)
        total_videos = Utils.count_videos_in_folder(OUTPUT_TAKEOUT_FOLDER)
        total_sidecars = Utils.count_sidecars_in_folder(OUTPUT_TAKEOUT_FOLDER)
        total_metadata = Utils.count_metadatas_in_folder(OUTPUT_TAKEOUT_FOLDER)
        total_supported_files = total_images + total_videos + total_sidecars + total_metadata

        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("=====================================================")
        LOGGER.info("           PROCESS COMPLETED SUCCESSFULLY!           ")
        LOGGER.info("=====================================================")
        LOGGER.info("")
        LOGGER.info(f"INFO    : All the Photos/Videos Fixed can be found on folder: '{OUTPUT_TAKEOUT_FOLDER}'")
        LOGGER.info("")
        LOGGER.info("=====================================================")
        LOGGER.info("                    FINAL SUMMARY:                   ")
        LOGGER.info("=====================================================")
        LOGGER.info(f"Total Files files in Takeout folder         : {initial_takeout_numfiles}")
        LOGGER.info(f"Total Supported files in Takeout folder     : {initial_takeout_total_supported_files}")
        LOGGER.info(f"   - Total Images in Takeout folder         : {initial_takeout_total_images}")
        LOGGER.info(f"   - Total Videos in Takeout folder         : {initial_takeout_total_videos}")
        LOGGER.info(f"   - Total Sidecars in Takeout folder       : {initial_takeout_total_sidecars}")
        LOGGER.info(f"   - Total Metadata in Takeout folder       : {initial_takeout_total_metadata}")
        LOGGER.info(f"Total Non-Supported files in Takeout folder : {initial_takeout_numfiles-initial_takeout_total_supported_files}")
        LOGGER.info("")
        LOGGER.info(f"Total Files in Output folder                : {total_files}")
        LOGGER.info(f"Total Supported files in Output folder      : {total_supported_files}")
        LOGGER.info(f"   - Total Images in Output folder          : {total_images}")
        LOGGER.info(f"   - Total Videos in Output folder          : {total_videos}")
        LOGGER.info(f"   - Total Sidecars in Output folder        : {total_sidecars}")
        LOGGER.info(f"   - Total Metadata in Output folder        : {total_metadata}")
        LOGGER.info(f"Total Non-Supported files in Output folder  : {total_files-total_supported_files}")
        LOGGER.info(f"Total Albums folders found in Output folder : {albums_found}")
        LOGGER.info("")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.info(f"Total Symlinks Fixed                        : {symlink_fixed}")
            LOGGER.info(f"Total Symlinks Not Fixed                    : {symlink_not_fixed}")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.info(f"Total Duplicates Removed                    : {duplicates_found}")
            LOGGER.info(f"Total Empty Folders Removed                 : {removed_empty_folders}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
        LOGGER.info("=====================================================")
        LOGGER.info("")


#############################
# SYNOLOGY/IMMICH FEATURES: #
#############################
def mode_cloud_upload_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud=='Immich':
        input_folder = ARGS['immich-upload-albums']
        LOGGER.info(f"INFO    : Flag detected '-iuAlb, --immich-upload-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['immich-upload-albums']}'"))
        LOGGER.warning('-' * terminal_width)
    elif cloud=='Synology':
        input_folder = ARGS['synology-upload-albums']
        LOGGER.info(f"INFO    : Flag detected '-suAlb, --synology-upload-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['synology-upload-albums']}'"))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"INFO    : Reading Configuration file and Login into {cloud} Photos...")
        cloud_client.login(log_level=logging.WARNING)
        LOGGER.info(f"INFO    : Find Albums in Folder    : {input_folder}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client.push_albums(input_folder=input_folder, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"INFO    : Cleaning-up {cloud} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info("INFO    : Removing Empty Albums...")
        total_empty_albums_removed = cloud_client.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info("INFO    : Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        LOGGER.info("INFO    : Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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
        LOGGER.info(f"Total Assets                            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        LOGGER.info(f"Total Assets skipped (Duplicated)       : {total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        LOGGER.info(f"Total Empty Albums removed              : {total_empty_albums_removed}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_cloud_upload_ALL(cloud=None, user_confirmation=True, log_level=logging.INFO):
    albums_folders = ARGS['albums-folders']
    if albums_folders:
        LOGGER.info(f"INFO    : Flag detected '-AlbFld, --albums-folders'.")

    if cloud == 'Immich':
        input_folder = ARGS['immich-upload-all']
        LOGGER.info(f"INFO    : Flag detected '-iuAll, --immich-upload-all'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-upload-all"].replace('<INPUT_FOLDER>', f"{input_folder}"))
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        input_folder = ARGS['synology-upload-all']
        LOGGER.info(f"INFO    : Flag detected '-suAll, --synology-upload-all'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-upload-all"].replace('<INPUT_FOLDER>', f"{input_folder}"))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        LOGGER.info(f"INFO    : Uploading Assets in Folder    : {ARGS['immich-upload-all']}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client.push_ALL(input_folder=input_folder, albums_folders=albums_folders, remove_duplicates=False, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"INFO    : Cleaning-up {cloud} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info("INFO    : Removing Empty Albums...")
        total_empty_albums_removed = cloud_client.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info("INFO    : Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute merge_duplicates_assets
        LOGGER.info("INFO    : Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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
        LOGGER.info(f"Total Assets                            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        LOGGER.info(f"Total Assets skipped (Duplicated)       : {total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded_within_albums}")
        LOGGER.info(f"Total Assets added without Albums       : {total_assets_uploaded_without_albums}")
        LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        LOGGER.info(f"Total Empty Albums removed              : {total_empty_albums_removed}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_cloud_download_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        albums_name = ARGS['immich-download-albums']
        output_folder = ARGS['output-folder']
        LOGGER.info(f"INFO    : Flag detected '-idAlb, --immich-download-albums <ALBUMS_NAME>'.".replace("'<ALBUMS_NAME>'", albums_name))
        LOGGER.info(f"INFO    : Albums to extract   : {albums_name}")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-download-albums"].replace("'<ALBUMS_NAME>'", f"{ARGS['immich-download-albums']}").replace("<OUTPUT_FOLDER>", output_folder))
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        albums_name = ARGS['synology-download-albums']
        output_folder = ARGS['output-folder']
        LOGGER.info(f"INFO    : Flag detected '-sdAlb, --synology-download-albums <ALBUMS_NAME>'.".replace("'<ALBUMS_NAME>'", albums_name))
        LOGGER.info(f"INFO    : Albums to extract   : {albums_name}")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-download-albums"].replace("'<ALBUMS_NAME>'", f"{ARGS['synology-download-albums']}").replace("<OUTPUT_FOLDER>", output_folder))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info("")
        LOGGER.info("INFO    : Cleaning-up Immich Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info("")
        LOGGER.info("INFO    : Removing Empty Albums...")
        total_empty_albums_removed = cloud_client.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info("")
        LOGGER.info("INFO    : Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        LOGGER.info("")
        LOGGER.info("INFO    : Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded = cloud_client.pull_albums(albums_name=albums_name, output_folder=output_folder, log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_cloud_download_ALL(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        output_folder = ARGS['immich-download-all']
        LOGGER.info(f"INFO    : Flag detected '-idAll, --immich-download-all'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-download-all"].replace('<OUTPUT_FOLDER>', output_folder))
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        output_folder = ARGS['synology-download-all']
        LOGGER.info(f"INFO    : Flag detected '-sdAll, --synology-download-all'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-download-all"].replace('<OUTPUT_FOLDER>', output_folder))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info("INFO    : Cleaning-up Immich Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        total_empty_albums_removed = cloud_client.remove_empty_albums(log_level=logging.WARNING)
        # Execute merge_duplicates_albums
        total_duplicates_albums_removed = cloud_client.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        duplicates_assets_removed = cloud_client.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums = cloud_client.pull_ALL(output_folder=output_folder, log_level=logging.WARNING)
        # logout
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_remove_empty_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        LOGGER.info(f"INFO    : Flag detected '-irEmpAlb, --immich-remove-empty-albums'.")
        LOGGER.info(f"INFO    : The Tool will look for any empty album in your {cloud} Photos account and will remove them (if any empty album is found).")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-empty-albums"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        LOGGER.info(f"INFO    : Flag detected '-srEmpAlb, --synology-remove-empty-albums'.")
        LOGGER.info(f"INFO    : The Tool will look for any empty album in your {cloud} Photos account and will remove them (if any empty album is found).")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-empty-albums"])
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Remove Empty Album' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client.remove_empty_albums(log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_remove_duplicates_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        LOGGER.info(f"INFO    : Flag detected '-irDupAlb, --immich-remove-duplicates-albums'.")
        LOGGER.info(f"INFO    : The Tool will look for any duplicated album (based on assets counts and assets size) in your {cloud} Photos account and will remove them (if any duplicated album is found).")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-duplicates-albums"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        LOGGER.info(f"INFO    : Flag detected '-srDupAlb, --synology-remove-duplicates-albums'")
        LOGGER.info(f"INFO    : The Tool will look for any duplicated album (based on assets counts and assets size) in your {cloud} Photos account and will remove them (if any duplicated album is found).")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-duplicates-albums"])
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Remove Duplicates Album' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client.remove_duplicates_albums(log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_merge_duplicates_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        LOGGER.info(f"INFO    : Flag detected '-iMergAlb, --immich-merge-duplicates-albums'.")
        LOGGER.info(f"INFO    : The Tool will look for any duplicated album in your {cloud} Photos account, merge their content into the most relevant one, and remove the duplicates.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-merge-duplicates-albums"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        LOGGER.info(f"INFO    : Flag detected '-sMergAlb, --synology-merge-duplicates-albums'.")
        LOGGER.info(f"INFO    : The Tool will look for any duplicated album in your {cloud} Photos account, merge their content into the most relevant one, and remove the duplicates.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-merge-duplicates-albums"])
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Immich Photos: 'Merge Duplicates Album' Mode detected. Only this module will be run!!!")

        # Login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)

        # Call the Function using 'count' as strategy (you can change to 'size')
        albums_removed = cloud_client.merge_duplicates_albums(strategy='count', log_level=logging.INFO)

        # Logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)

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
        LOGGER.info(f"Total Duplicate Albums merged and removed : {albums_removed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                        : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_cloud_remove_orphan_assets(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        LOGGER.info(f"INFO    : Flag detected '-irOrphan, --immich-remove-orphan-assets'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-orphan-assets"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        LOGGER.warning(f"WARNING : Flag detected '-srOrphan, --synology-remove-orphan-assets'. But this feature is not available for Synology Photos. Exiting program.")
        sys.exit(0)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Remove Orphan Assets' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed = cloud_client.remove_orphan_assets(user_confirmation=False, log_level=logging.WARNING)
        #logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_remove_ALL(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        LOGGER.info(f"INFO    : Flag detected '-irAll, --immich-remove-all-assets'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-all-assets"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        LOGGER.info(f"INFO    : Flag detected '-srAll, --synology-remove-all-assets'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-all-assets"])
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Remove ALL Assets' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed, albums_removed = cloud_client.remove_all_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_rename_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        albums_name_pattern = ARGS['immich-rename-albums'][0]
        albums_name_replacement_pattern = ARGS['immich-rename-albums'][1]
        LOGGER.info(f"INFO    : Flag detected '-iRenAlb, --immich-rename-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-rename-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern).replace('<ALBUMS_NAME_REPLACEMENT_PATTERN>',albums_name_replacement_pattern))
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        albums_name_pattern = ARGS['synology-rename-albums'][0]
        albums_name_replacement_pattern = ARGS['synology-rename-albums'][1]
        LOGGER.info(f"INFO    : Flag detected '-sRenAlb, --synology-rename-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-rename-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern).replace('<ALBUMS_NAME_REPLACEMENT_PATTERN>',albums_name_replacement_pattern))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Rename Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        albums_renamed = cloud_client.rename_albums(pattern=ARGS['immich-rename-albums'][0], pattern_to_replace=ARGS['immich-rename-albums'][1], log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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
        LOGGER.info(f"Total Albums renamed                    : {albums_renamed}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_cloud_remove_albums_by_name_pattern(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        if ARGS['immich-remove-all-albums'] != "":
            albums_name_pattern = '.*'
        else:
            albums_name_pattern = ARGS['immich-remove-albums']
        remove_albums_assets = ARGS['remove-albums-assets']
        LOGGER.info(f"INFO    : Flag detected '-iRemAlb, --immich-remove-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern))
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        if ARGS['synology-remove-all-albums'] != "":
            albums_name_pattern = '.*'
        else:
            albums_name_pattern = ARGS['synology-remove-albums']
        remove_albums_assets = ARGS['remove-albums-assets']
        LOGGER.info(f"INFO    : Flag detected '-iRemAlb, --synology-remove-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern))
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if ARGS['remove-albums-assets']:
        LOGGER.info(f"INFO    : Flag detected '-rAlbAss, --remove-albums-assets'.")
        LOGGER.info(f"Since, flag '-rAlbAss, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        LOGGER.info("")
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Delete Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client.remove_albums_by_name(pattern=albums_name_pattern, removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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


def mode_cloud_remove_all_albums(cloud=None, user_confirmation=True, log_level=logging.INFO):
    if cloud == 'Immich':
        remove_albums_assets = ARGS['remove-albums-assets']
        LOGGER.info(f"INFO    : Flag detected '-irAllAlb, --immich-remove-all-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-all-albums"])
        LOGGER.warning('-' * terminal_width)
    elif cloud == 'Synology':
        remove_albums_assets = ARGS['remove-albums-assets']
        LOGGER.info(f"INFO    : Flag detected '-srAllAlb, --synology-remove-all-albums'.")
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["cloud-remove-all-albums"])
        LOGGER.warning('-' * terminal_width)
    else:
        LOGGER.info(f"INFO    : Cloud service not valid ({cloud}). Valid clients are ['Immich', 'Synology']. Exiting program.")
        sys.exit(0)
    if ARGS['remove-albums-assets']:
        LOGGER.info(f"INFO    : Flag detected '-rAlbAss, --remove-albums-assets'.")
        LOGGER.info(f"Since, flag '-rAlbAss, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        LOGGER.info("")
    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"INFO    : Exiting program.")
        sys.exit(0)

    # Create the cloud_client Object
    if cloud == 'Immich':
        cloud_client = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif cloud == 'Synology':
        cloud_client = ClassSynologyPhotos(account_id=ARGS['account-id'])

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : {cloud} Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info("")
        LOGGER.info("INFO    : Reading Configuration file and Login into Immich Photos...")
        cloud_client.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client.remove_all_albums(removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        LOGGER.info("")
        LOGGER.info("INFO    : Logged out from Immich Photos.")
        cloud_client.logout(log_level=logging.WARNING)
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
# OTHER STANDALONE FEATURES: #
#################################
def mode_fix_symlinkgs(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["fix-symlinks-broken"].replace('<FOLDER_TO_FIX>', f"'{ARGS['fix-symlinks-broken']}'"))
        LOGGER.warning('-' * terminal_width)
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
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["find-duplicates"].replace('<DUPLICATES_FOLDER>', f"'{ARGS['duplicates-folders']}'"))
        LOGGER.warning('-' * terminal_width)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"WARNING : Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
        duplicates_files_found, removed_empty_folders = find_duplicates(duplicates_action=ARGS['duplicates-action'], duplicates_folders=ARGS['duplicates-folders'], deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            LOGGER.error("ERROR   : Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exist.")
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
        LOGGER.info(f"Total Empty Folders Removed             : {removed_empty_folders}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_process_duplicates(user_confirmation=True, log_level=logging.INFO):
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["process-duplicates"])
        LOGGER.warning('-' * terminal_width)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Flag detected '-procDup, --process-duplicates'. The Tool will process the '{ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
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
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["rename-folders-content-based"].replace('<ALBUMS_FOLDER>', f"'{ARGS['rename-folders-content-based']}'"))
        LOGGER.warning('-' * terminal_width)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO    : Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"INFO    : Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO    : Flag detected '-ra, --rename-folders-content-based'. The Tool will look for any Subfolder in '{ARGS['rename-folders-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
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
