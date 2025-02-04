from Globals import *
import os, sys
from datetime import datetime, timedelta
import Utils
import Fixers
from Duplicates import find_duplicates, process_duplicates_actions
from SynologyPhotos import read_synology_config, login_synology, synology_delete_empty_albums, synology_delete_duplicates_albums, synology_upload_folder, synology_upload_albums, synology_download_albums, synology_download_ALL
from ImmichPhotos import read_immich_config, login_immich, logout_immich, immich_delete_empty_albums, immich_delete_duplicates_albums, immich_upload_folder, immich_upload_albums, immich_download_albums, immich_download_ALL, immich_delete_orphan_assets, immich_delete_all_assets, immich_delete_all_albums

DEFAULT_DUPLICATES_ACTION = False
EXECUTION_MODE = "default"
# -------------------------------------------------------------
# Determine the Execution mode based on the providen arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():
    from Globals import ARGS, PARSER
    # AUTOMATED-MIGRATION MODE:
    if ARGS['AUTOMATED-MIGRATION']:
        EXECUTION_MODE = 'AUTOMATED-MIGRATION'
        mode_AUTOMATED_MIGRATION()

    # Google Photos Mode:
    elif "-gitf" in sys.argv or "--google-input-takeout-folder" in sys.argv:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()

    # Synology Photos Modes:
    elif ARGS['synology-delete-empty-albums']:
        EXECUTION_MODE = 'synology-delete-empty-albums'
        mode_synology_delete_empty_albums()
    elif ARGS['synology-delete-duplicates-albums']:
        EXECUTION_MODE = 'synology-delete-duplicates-albums'
        mode_synology_delete_duplicates_albums()
    elif ARGS['synology-upload-folder'] != "":
        EXECUTION_MODE = 'synology-upload-folder'
        mode_synology_upload_folder()
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

    # Immich Photos Modes:
    elif ARGS['immich-delete-empty-albums']:
        EXECUTION_MODE = 'immich-delete-empty-albums'
        mode_immich_delete_empty_albums()
    elif ARGS['immich-delete-duplicates-albums']:
        EXECUTION_MODE = 'immich-delete-duplicates-albums'
        mode_immich_delete_duplicates_albums()
    elif ARGS['immich-upload-folder'] != "":
        EXECUTION_MODE = 'immich-upload-folder'
        mode_immich_upload_folder()
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
    elif ARGS['immich-delete-orphan-assets'] != "":
        EXECUTION_MODE = 'immich-delete-orphan-assets'
        mode_immich_delete_orphan_assets()
    elif ARGS['immich-delete-all-assets'] != "":
        EXECUTION_MODE = 'immich-delete-all-assets'
        mode_immich_delete_all_assets()
    elif ARGS['immich-delete-all-albums'] != "":
        EXECUTION_MODE = 'immich-delete-all-albums'
        mode_immich_delete_all_albums()

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
    elif ARGS['folders-rename-content-based'] != "":
        EXECUTION_MODE = 'folders-rename-content-based'
        mode_folders_rename_content_based()

    else:
        EXECUTION_MODE = ''  # Opción por defecto si no se cumple ninguna condición
        LOGGER.error(f"ERROR: Unable to detect any valid execution mode.")
        LOGGER.error(f"ERROR: Please, run '{os.path.basename(sys.argv[0])} --help' to know more about how to invoke the Script.")
        LOGGER.error("")
        # PARSER.print_help()
        sys.exit(1)

def mode_AUTOMATED_MIGRATION(info_messages=True):
    SOURCE = ARGS['AUTOMATED-MIGRATION'][0]
    TARGET = ARGS['AUTOMATED-MIGRATION'][1]
    intermediate_folder = ''

    LOGGER.info(f"INFO: -AUTO, --AUTOMATED-MIGRATION Mode detected")
    if not ARGS['SOURCE-TYPE-TAKEOUT-FOLDER']:
        LOGGER.info(HELP_TEXTS["--AUTOMATED-MIGRATION"].replace('<SOURCE>', f"'{ARGS['AUTOMATED-MIGRATION'][0]}'").replace('<TARGET>', f"'{ARGS['AUTOMATED-MIGRATION'][1]}'"))
    else:
        LOGGER.info(HELP_TEXTS["--AUTOMATED-MIGRATION"].replace('<SOURCE> Cloud Service', f"folder '{ARGS['AUTOMATED-MIGRATION'][0]}'").replace('<TARGET>', f"'{ARGS['AUTOMATED-MIGRATION'][1]}'").replace('Downloading', 'Analyzing and Fixing'))
    LOGGER.info(f"INFO: Selected SOURCE : {SOURCE}")
    LOGGER.info(f"INFO: Selected TARGET : {TARGET}")
    LOGGER.info("")
    if not Utils.confirm_continue():
        LOGGER.info(f"INFO: Exiting program.")
        sys.exit(0)


    # If the SOURCE is 'google-photos' or a valid Takeout Folder
    if SOURCE.lower() == 'google-photos' or ARGS['SOURCE-TYPE-TAKEOUT-FOLDER']:
        # Configure default arguments for mode_google_takeout() execution and RUN it
        if SOURCE.lower() == 'google-photos':
            input_folder = ARGS['input-folder']
        elif ARGS['SOURCE-TYPE-TAKEOUT-FOLDER']:
            input_folder = SOURCE

        # For the time being we set the global OUTPUT_TAKEOUT_FOLDER within Synology Photos root folder (otherwise Synology Photos will not see it)
        # TODO: Change this logic to avoid Synology Photos dependency
        config = read_synology_config(config_file='Config.ini', show_info=False)
        if not config['SYNOLOGY_ROOT_PHOTOS_PATH']:
            LOGGER.warning(f"WARNING: Caanot find 'SYNOLOGY_ROOT_PHOTOS_PATH' info in 'nas.config' file. Albums will not be created into Synology Photos database")
        else:
            ARGS['output-folder'] = os.path.join(config['SYNOLOGY_ROOT_PHOTOS_PATH'], f'Google Photos_{TIMESTAMP}')
            intermediate_folder = ARGS['output-folder']

        # Check if already exists an 'Albums' subfolder within input_folder, in that case, the input_folder have been already processed by CloudPhotoMigrator and no need to execute GPTH step again
        # but in that case, we need to move the folder to the intermediate folder
        if os.path.isdir(os.path.join(input_folder,'Albums')):
            if not Utils.copy_move_folder(input_folder, intermediate_folder, move=False):
                LOGGER.error(f"ERROR: Unable to copy Folder '{input_folder}' to '{intermediate_folder}'. Exiting...")
                sys.exit(-1)
        else:
            ARGS['google-input-takeout-folder'] = input_folder
            ARGS['google-remove-duplicates-files'] = True
            need_unzip = Utils.contains_zip_files(input_folder)
            if need_unzip:
                ARGS['google-move-takeout-folder'] = True
            mode_google_takeout(user_confirmation=False, info_messages=True)

    # If the SOURCE is 'synology-photos'
    elif SOURCE.lower() == 'synology-photos':
        # For the time being we set the global OUTPUT_TAKEOUT_FOLDER within Synology Photos root folder (otherwise Synology Photos will not see it)
        # TODO: Change this logic to avoid Synology Photos dependency
        config = read_synology_config(config_file='Config.ini', show_info=False)
        if not config['SYNOLOGY_ROOT_PHOTOS_PATH']:
            LOGGER.warning(f"WARNING: Caanot find 'SYNOLOGY_ROOT_PHOTOS_PATH' info in 'nas.config' file. Albums will not be created into Synology Photos database")
        else:
            ARGS['immich-synology-ALL'] = os.path.join(config['SYNOLOGY_ROOT_PHOTOS_PATH'], f'Google Photos_{TIMESTAMP}')
            intermediate_folder = ARGS['immich-synology-ALL']
        mode_synology_download_ALL(user_confirmation=False, info_messages=True)

    # If the SOURCE is 'immich-photos'
    elif SOURCE.lower() == 'immich-photos':
        # For the time being we set the global OUTPUT_TAKEOUT_FOLDER within Synology Photos root folder (otherwise Synology Photos will not see it)
        # TODO: Change this logic to avoid Synology Photos dependency
        config = read_synology_config(config_file='Config.ini', show_info=False)
        if not config['SYNOLOGY_ROOT_PHOTOS_PATH']:
            LOGGER.warning(f"WARNING: Caanot find 'SYNOLOGY_ROOT_PHOTOS_PATH' info in 'nas.config' file. Albums will not be created into Synology Photos database")
        else:
            ARGS['immich-download-all'] = os.path.join(config['SYNOLOGY_ROOT_PHOTOS_PATH'], f'Google Photos_{TIMESTAMP}')
            intermediate_folder = ARGS['immich-download-all']
        mode_immich_download_ALL(user_confirmation=False, info_messages=False)

    # if the TARGET is 'synology-photos'
    if TARGET.lower() == 'synology-photos':
        ARGS['synology-upload-all'] = intermediate_folder
        mode_synology_upload_ALL(user_confirmation=False, info_messages=True)

    # If the TARGET is 'immich-photos'
    elif TARGET.lower() == 'immich-photos':
        ARGS['immich-upload-all'] = intermediate_folder
        mode_immich_upload_ALL(user_confirmation=False, info_messages=True)


def mode_google_takeout(user_confirmation=True, info_messages=True):
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
        LOGGER.info(f"INFO: ZIP files have been detected in {input_folder}'. Files will be unziped first...")
        LOGGER.info("")
    else:
        ARGS['google-input-takeout-folder'] = input_folder

    if info_messages:
        # Mensajes informativos
        LOGGER.info(f"Settings for Google Takeout Photos Module:")
        LOGGER.info(f"------------------------------------------")
        LOGGER.info(f"INFO: Using Suffix                             : '{ARGS['google-output-folder-suffix']}'")
        LOGGER.info(f"INFO: Albums Folder Structure                  : '{ARGS['google-albums-folders-structure']}'")
        LOGGER.info(f"INFO: No Albums Folder Structure               : '{ARGS['google-no-albums-folder-structure']}'")
        LOGGER.info(f"INFO: Creates symbolic links for Albums        : '{ARGS['google-create-symbolic-albums']}'")
        LOGGER.info(f"INFO: Ignore Check Google Takeout Structure    : '{ARGS['google-ignore-check-structure']}'")
        LOGGER.info(f"INFO: Move Original Assets to Output Folder    : '{ARGS['google-move-takeout-folder']}'")
        LOGGER.info(f"INFO: Remove Duplicates files in Output folder : '{ARGS['google-remove-duplicates-files']}'")
        LOGGER.info(f"INFO: Skip Extra Assets (-edited,-effects...)  : '{ARGS['google-skip-extras-files']}'")
        LOGGER.info(f"INFO: Skip Moving Albums to 'Albums' folder    : '{ARGS['google-skip-move-albums']}'")
        LOGGER.info(f"INFO: Skip GPTH Tool                           : '{ARGS['google-skip-gpth-tool']}'")

        LOGGER.info("")
        LOGGER.info(f"Folders for Google Takeout Photos Module:")
        LOGGER.info(f"------------------------------------------")
        if ARGS['google-input-zip-folder']!="":
            LOGGER.info(f"INFO: Input Takeout folder (zipped detected)   : '{ARGS['google-input-zip-folder']}'")
            LOGGER.info(f"INFO: Input Takeout will be unziped to folder  : '{ARGS['google-input-takeout-folder']}'")
        else:
            LOGGER.info(f"INFO: Input Takeout folder                     : '{ARGS['google-input-takeout-folder']}'")
        LOGGER.info(f"INFO: OUTPUT folder                            : '{OUTPUT_TAKEOUT_FOLDER}'")

    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["--google-photos-takeout"].replace('<TAKEOUT_FOLDER>',f"'{ARGS['google-input-takeout-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)

    if info_messages:
        if ARGS['google-input-zip-folder']=="":
            LOGGER.warning(f"WARNING: No argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if ARGS['google-albums-folders-structure'].lower()!='flatten':
            LOGGER.warning(f"WARNING: Flag detected '-gafs, --google-albums-folders-structure'. Folder structure '{ARGS['google-albums-folders-structure']}' will be applied on each Album folder...")
        if ARGS['google-no-albums-folder-structure'].lower()!='year/month':
            LOGGER.warning(f"WARNING: Flag detected '-gnaf, --google-no-albums-folder-structure'. Folder structure '{ARGS['google-no-albums-folder-structure']}' will be applied on 'No-Albums' folder (Photos without Albums)...")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"WARNING: Flag detected '-gsgt, --google-skip-gpth-tool'. Skipping Processing photos with GPTH Tool...")
        if ARGS['google-skip-extras-files']:
            LOGGER.warning(f"WARNING: Flag detected '-gsef, --google-skip-extras-files'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if ARGS['google-skip-move-albums']:
            LOGGER.warning(f"WARNING: Flag detected '-gsma, --google-skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.warning(f"WARNING: Flag detected '-gcsa, --google-create-symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning(f"WARNING: Flag detected '-gics, --google-ignore-check-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if ARGS['google-move-takeout-folder']:
            LOGGER.warning(f"WARNING: Flag detected '-gmtf, --google-move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_TAKEOUT_FOLDER>...")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.warning(f"WARNING: Flag detected '-grdf, --google-remove-duplicates-files'. All duplicates files within OUTPUT_TAKEOUT_FOLDER will be removed after fixing them...")
        if ARGS['no-log-file']:
            LOGGER.warning(f"WARNING: Flag detected '-nolog, --no-log-file'. Skipping saving output into log file...")

    # STEP 1: Unzip files
    STEP=1
    LOGGER.info("")
    LOGGER.info("==============================")
    LOGGER.info(f"{STEP}. UNPACKING TAKEOUT FOLDER...")
    LOGGER.info("==============================")
    LOGGER.info("")
    if ARGS['google-input-zip-folder']:
        step_start_time = datetime.now()
        Utils.unpack_zips(ARGS['google-input-zip-folder'], ARGS['google-input-takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Unzipping skipped (no argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' given or Running Mode All-in-One with input folder directly unzipped).")

    if not os.path.isdir(ARGS['google-input-takeout-folder']):
        LOGGER.error(f"ERROR: Cannot Find INPUT_FOLDER: '{ARGS['google-input-takeout-folder']}'. Exiting...")
        sys.exit(-1)

    # STEP 2: Pre-Process Takeout folder
    STEP+=1
    LOGGER.info("")
    LOGGER.info("===================================")
    LOGGER.info(f"{STEP}. PRE-PROCESSING TAKEOUT FOLDER...")
    LOGGER.info("===================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
    LOGGER.info("INFO: Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
    Utils.delete_subfolders(ARGS['google-input-takeout-folder'], "@eaDir")
    # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
    LOGGER.info("")
    LOGGER.info("INFO: Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
    Utils.fix_mp4_files(ARGS['google-input-takeout-folder'])
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    LOGGER.info("")
    LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 3: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    STEP+=1
    LOGGER.info("")
    LOGGER.info("===========================================")
    LOGGER.info(f"{STEP}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    LOGGER.info("===========================================")
    LOGGER.info("")
    if not ARGS['google-skip-gpth-tool']:
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning("WARNING: Ignore Google Takeout Structure detected ('-it, --google-ignore-check-structure' flag detected).")
        step_start_time = datetime.now()
        Fixers.fix_metadata_with_gpth_tool(
            input_folder=ARGS['google-input-takeout-folder'],
            output_folder=OUTPUT_TAKEOUT_FOLDER,
            symbolic_albums=ARGS['google-create-symbolic-albums'],
            skip_extras=ARGS['google-skip-extras-files'],
            move_takeout_folder=ARGS['google-move-takeout-folder'],
            ignore_takeout_structure=ARGS['google-ignore-check-structure']
        )
        if ARGS['google-move-takeout-folder']:
            Utils.force_remove_directory(ARGS['google-input-takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    if ARGS['google-skip-gpth-tool'] or ARGS['google-ignore-check-structure']:
        LOGGER.info("")
        LOGGER.info("============================================")
        LOGGER.info(f"{STEP}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
        LOGGER.info("============================================")
        LOGGER.info("")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"WARNING: Metadata fixing with GPTH tool skipped ('-sg, --google-skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
        elif ARGS['google-ignore-check-structure']:
            LOGGER.warninf(f"WARNING: Flag to Ignore Google Takeout Structure have been detected ('-it, --google-ignore-check-structure'). Step {STEP}b is needed to copy/move files manually to output folder.")
        if ARGS['google-move-takeout-folder']:
            LOGGER.info("INFO: Moving files from Takeout folder to Output folder manually...")
        else:
            LOGGER.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder (ARGS['google-input-takeout-folder'], OUTPUT_TAKEOUT_FOLDER, ignore_patterns=['*.json', '*.j'], move=ARGS['google-move-takeout-folder'])
        if ARGS['google-move-takeout-folder']:
            Utils.force_remove_directory(ARGS['takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP}b completed in {formatted_duration}.")

    # STEP 4: Sync .MP4 live pictures timestamp
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==============================================================")
    LOGGER.info(f"{STEP}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
    LOGGER.info("==============================================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    LOGGER.info("INFO: Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
    Utils.sync_mp4_timestamps_with_images(OUTPUT_TAKEOUT_FOLDER)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")


    # STEP 5: Create Folders Year/Month or Year only structure
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==========================================")
    LOGGER.info(f"{STEP}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
    LOGGER.info("==========================================")
    step_start_time = datetime.now()
    # For Albums:
    if ARGS['google-albums-folders-structure'].lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
        basedir=OUTPUT_TAKEOUT_FOLDER
        type=ARGS['google-albums-folders-structure']
        exclude_subfolders=['No-Albums']
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # For No Albums:
    if ARGS['google-no-albums-folder-structure'].lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{ARGS['google-no-albums-folder-structure'].lower()}' for 'No-Albums' folder...")
        basedir=os.path.join(OUTPUT_TAKEOUT_FOLDER, 'No-Albums')
        type=ARGS['google-no-albums-folder-structure']
        exclude_subfolders=[]
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # If no fiolder structure is detected:
    if ARGS['google-albums-folders-structure'].lower()=='flatten' and ARGS['google-no-albums-folder-structure'].lower()=='flatten' :
        LOGGER.info("")
        LOGGER.warning("WARNING: No argument '-as, --google-albums-folders-structure' and '-ns, --google-no-albums-folder-structure' detected. All photos and videos will be flattened within their folders without any date organization.")
    else:
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 6: Move albums
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==========================")
    LOGGER.info(f"{STEP}. MOVING ALBUMS FOLDER...")
    LOGGER.info("==========================")
    LOGGER.info("")
    if not ARGS['google-skip-move-albums']:
        step_start_time = datetime.now()
        Utils.move_albums(OUTPUT_TAKEOUT_FOLDER, exclude_subfolder=['No-Albums', '@eaDir'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")

    # STEP 7: Fix Broken Symbolic Links after moving
    STEP+=1
    symlink_fixed = 0
    symlink_not_fixed = 0
    LOGGER.info("")
    LOGGER.info("===============================================")
    LOGGER.info(f"{STEP}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
    LOGGER.info("===============================================")
    LOGGER.info("")
    if ARGS['google-create-symbolic-albums']:
        LOGGER.info("INFO: Fixing broken symbolic links. This step is needed after moving any Folder structure...")
        step_start_time = datetime.now()
        symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(OUTPUT_TAKEOUT_FOLDER)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected, so this step is not needed.)")

    # STEP 8: Remove Duplicates in OUTPUT_TAKEOUT_FOLDER after Fixing
    STEP+=1
    duplicates_found = 0
    if ARGS['google-remove-duplicates-files']:
        LOGGER.info("")
        LOGGER.info("==========================================")
        LOGGER.info(f"{STEP}. REMOVING DUPLICATES IN OUTPUT_TAKEOUT_FOLDER...")
        LOGGER.info("==========================================")
        LOGGER.info("")
        LOGGER.info("INFO: Removing duplicates from OUTPUT_TAKEOUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'No-Albums' folders)...")
        step_start_time = datetime.now()
        duplicates_found = find_duplicates(duplicates_action='remove', duplicates_folders=OUTPUT_TAKEOUT_FOLDER, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS, timestamp=TIMESTAMP)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    if info_messages:
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
        LOGGER.info("")
        LOGGER.info("==================================================")
        LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info("==================================================")
        LOGGER.info("")
        LOGGER.info(f"INFO: All the Photos/Videos Fixed can be found on folder: '{OUTPUT_TAKEOUT_FOLDER}'")
        LOGGER.info("")
        LOGGER.info("===============================================")
        LOGGER.info("                FINAL SUMMARY:                 ")
        LOGGER.info("===============================================")
        LOGGER.info(f"Total files in Takeout folder        : {Utils.count_files_in_folder(ARGS['google-input-takeout-folder'])}")
        LOGGER.info(f"Total final files in Output folder   : {Utils.count_files_in_folder(OUTPUT_TAKEOUT_FOLDER)}")
        albums_found = 0
        if not ARGS['google-skip-move-albums']:
            album_folder = os.path.join(OUTPUT_TAKEOUT_FOLDER, 'Albums')
            if os.path.isdir(album_folder):
                albums_found = len(os.listdir(album_folder))
        else:
            if os.path.isdir(OUTPUT_TAKEOUT_FOLDER):
                albums_found = len(os.listdir(OUTPUT_TAKEOUT_FOLDER)) - 1
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

def mode_fix_symlinkgs(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["--fix-symlinks-broken"].replace('<FOLDER_TO_FIX>', f"'{ARGS['fix-symlinks-broken']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Fixing broken symbolic links Mode detected. Only this module will be run!!!")
    LOGGER.info(f"INFO: Fixing broken symbolic links in folder '{ARGS['fix-symlinks-broken']}'...")
    symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(ARGS['fix-symlinks-broken'])

    if info_messages:
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

def mode_find_duplicates(interactive_mode=True, info_messages=True):
    LOGGER.info(f"INFO: Duplicates Action             : {ARGS['duplicates-action']}")
    LOGGER.info(f"INFO: Find Duplicates in Folders    : {ARGS['duplicates-folders']}")
    LOGGER.info("")
    if interactive_mode:
        LOGGER.info(HELP_TEXTS["--find-duplicates"].replace('<DUPLICATES_FOLDER>', f"'{ARGS['duplicates-folders']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"WARNING: Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
    duplicates_files_found = find_duplicates(duplicates_action=ARGS['duplicates-action'], duplicates_folders=ARGS['duplicates-folders'], deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
    if duplicates_files_found == -1:
        LOGGER.error("ERROR: Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exists.")
        sys.exit(-1)

    if info_messages:
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

def mode_process_duplicates(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["--process-duplicates"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Flag detected '-pd, --process-duplicates'. The Script will process the '{ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
    LOGGER.info(f"INFO: Processing Duplicates Files based on Actions given in {os.path.basename(ARGS['process-duplicates'])} file...")
    removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(ARGS['process-duplicates'])

    if info_messages:
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


def mode_folders_rename_content_based(user_confirmation=True, info_messages=True):
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")
    if user_confirmation:
        LOGGER.info(HELP_TEXTS["--folders-rename-content-based"].replace('<ALBUMS_FOLDER>', f"'{ARGS['folders-rename-content-based']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-ra, --folders-rename-content-based'. The Script will look for any Subfolder in '{ARGS['folders-rename-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
    renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(ARGS['folders-rename-content-based'])

    if info_messages:
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

#################################
# EXTRA MODES: SYNOLOGY PHOTOS: #
#################################
def mode_synology_delete_empty_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sdea, --synology-delete-empty-albums'.")
        LOGGER.info(HELP_TEXTS["--synology-delete-empty-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Delete Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-sdea, --synology-delete-empty-albums'. The Script will look for any empty album in Synology Photos database and will detelte them (if any enpty album is found).")
    # Call the Funxtion
    albums_deleted = synology_delete_empty_albums()

    if info_messages:
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
        LOGGER.info(f"Total Empty Albums deleted              : {albums_deleted}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_delete_duplicates_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sdda, --synology-delete-deuplicates-albums'.")
        LOGGER.info(HELP_TEXTS["--synology-delete-duplicates-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Delete Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-sdda, --synology-delete-duplicates-albums'. The Script will look for any duplicated album in Synology Photos database and will detelte them (if any duplicated album is found).")
    # Call the Funxtion
    albums_deleted = synology_delete_duplicates_albums()

    if info_messages:
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
        LOGGER.info(f"Total Duplicates Albums deleted         : {albums_deleted}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_upload_folder(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-suFld, --synology-upload-folder'.")
        LOGGER.info(HELP_TEXTS["--synology-upload-folder"].replace('<INPUT_FOLDER>', f"'{ARGS['synology-upload-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {ARGS['synology-upload-folder']}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = synology_upload_folder(ARGS['synology-upload-folder'])

    if info_messages:
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
        LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_synology_upload_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-suAlb, --synology-upload-albums'.")
        LOGGER.info(HELP_TEXTS["--synology-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['synology-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['synology-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = synology_upload_albums(ARGS['synology-upload-albums'])

    if info_messages:
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
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_upload_ALL( user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-suAll, --synology-upload-all'.")
        LOGGER.info(HELP_TEXTS["--immich-upload-all"].replace('<INPUT_FOLDER>', f"'{ARGS['synology-upload-all']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Assets in Folder    : {ARGS['synology-upload-all']}")
    LOGGER.info("")

    input_folder = ARGS['synology-upload-all']

    # Set the counters
    photos_added_without_albums = 0
    photos_added_within_albums = 0
    albums_crated = 0
    albums_skipped = 0

    album_folder = os.path.join(input_folder,'Albums')
    # if not exists input_folder exits, then upload all assets within input_folder without album creation ('Albums' subfolder will be skipped by this function)
    if os.path.isdir(input_folder):
        # TODO: synology_upload_folder() is not yet complete
        LOGGER.info(f"INFO: Uploading Assets of '{input_folder}' (excluding 'Albums' subfolder) into Synology Photos...")
        photos_added_without_albums = synology_upload_folder(input_folder)
    # If 'Albums' folder exists within input_folder, then run upload_albums() function to create one album per subfolder
    if os.path.isdir(album_folder):
        LOGGER.info(f"INFO: Uploading Assets within '{album_folder}' into Synology Photos and associating them to the corresponding Album...")
        albums_crated, albums_skipped, photos_added_within_albums = synology_upload_albums(album_folder)
    else:
        LOGGER.error(f"ERROR: The folder '{input_folder}' does not exist. We cannot execute Synology Upload Actions. Exiting...")
        sys.exit(-1)
    total_photos_added = photos_added_without_albums + photos_added_within_albums

    # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
    mode_synology_delete_duplicates_albums(user_confirmation=user_confirmation, info_messages=False)
    mode_synology_delete_empty_albums(user_confirmation=user_confirmation, info_messages=False)

    if info_messages:
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
        LOGGER.info(f"Total Photos added                      : {total_photos_added}")
        LOGGER.info(f"Total Photos added to Albums            : {photos_added_within_albums}")
        LOGGER.info(f"Total Photos added wihtout Albums       : {photos_added_without_albums}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")


def mode_synology_download_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sdAlb, --synology-download-albums'.")
        LOGGER.info(HELP_TEXTS["--synology-download-albums"].replace("'<ALBUMS_NAME>'", f"'{ARGS['synology-download-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Albums to extract       : {ARGS['synology-download-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, photos_downloaded = synology_download_albums(ARGS['synology-download-albums'])

    if info_messages:
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
        LOGGER.info(f"Total Photos downlaoded from Albums     : {photos_downloaded}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_synology_download_ALL(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idAll, --immich-download-all'.")
        LOGGER.info(HELP_TEXTS["--synology-download-all"].replace('<OUTPUT_FOLDER>', f"{ARGS['synology-download-all']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = synology_download_ALL(output_folder=ARGS['synology-download-all'])

    if info_messages:
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


###############################
# EXTRA MODES: IMMICH PHOTOS: #
###############################
def mode_immich_delete_empty_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idea, --immich-delete-empty-albums'.")
        LOGGER.info(HELP_TEXTS["--immich-delete-empty-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-idea, --immich-delete-empty-albums'. The Script will look for any empty album in Immich Photos database and will detelte them (if any enpty album is found).")
    # Call the Funxtion
    albums_deleted = immich_delete_empty_albums()
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Empty Albums deleted              : {albums_deleted}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_delete_duplicates_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idda, --immich-delete-deuplicates-albums'.")
        LOGGER.info(HELP_TEXTS["--immich-delete-duplicates-albums"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-idda, --immich-delete-duplicates-albums'. The Script will look for any duplicated album in Immich Photos database and will detelte them (if any duplicated album is found).")
    # Call the Funxtion
    albums_deleted = immich_delete_duplicates_albums()
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Duplicates Albums deleted         : {albums_deleted}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_upload_folder(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iuAlb, --immich-upload-albums'.")
        LOGGER.info(HELP_TEXTS["--immich-upload-folder"].replace('<INPUT_FOLDER>', f"'{ARGS['immich-upload-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {ARGS['immich-upload-folder']}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = immich_upload_folder(ARGS['immich-upload-folder'])
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Photos/Videos Uploaded            : {photos_added}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_upload_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iuAlb, --immich-upload-albums'.")
        LOGGER.info(HELP_TEXTS["--immich-upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['immich-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = immich_upload_albums(ARGS['immich-upload-albums'])
    logout_immich()

    if info_messages:
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
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_upload_ALL(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iuAll, --immich-upload-all'.")
        LOGGER.info(HELP_TEXTS["--immich-upload-all"].replace('<INPUT_FOLDER>', f"'{ARGS['immich-upload-all']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Assets in Folder    : {ARGS['immich-upload-all']}")
    LOGGER.info("")

    login_immich()

    input_folder = ARGS['immich-upload-all']

    # Set the counters
    photos_added_without_albums = 0
    photos_added_within_albums = 0
    albums_crated = 0
    albums_skipped = 0

    album_folder = os.path.join(input_folder,'Albums')
    # if not exists input_folder exits, then upload all assets within input_folder without album creation ('Albums' subfolder will be skipped by this function)
    if os.path.isdir(input_folder):
        LOGGER.info("")
        LOGGER.info(f"INFO: Uploading Assets of '{input_folder}' (excluding 'Albums' subfolder) into Immich Photos...")
        photos_added_without_albums = immich_upload_folder(input_folder)
    # If 'Albums' folder exists within input_folder, then run upload_albums() function to create one album per subfolder
    if os.path.isdir(album_folder):
        LOGGER.info("")
        LOGGER.info(f"INFO: Uploading Assets within '{album_folder}' into Immich Photos and associating them to the corresponding Album...")
        albums_crated, albums_skipped, photos_added_within_albums = immich_upload_albums(album_folder)
    else:
        LOGGER.error(f"ERROR: The folder '{input_folder}' does not exist. We cannot execute Immich Upload Actions. Exiting...")
        sys.exit(-1)
    total_photos_added = photos_added_without_albums + photos_added_within_albums

    # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
    LOGGER.info("")
    mode_immich_delete_duplicates_albums(user_confirmation=user_confirmation, info_messages=False)
    LOGGER.info("")
    mode_immich_delete_empty_albums(user_confirmation=user_confirmation, info_messages=False)

    if info_messages:
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
        LOGGER.info(f"Total Photos added                      : {total_photos_added}")
        LOGGER.info(f"Total Photos added to Albums            : {photos_added_within_albums}")
        LOGGER.info(f"Total Photos added wihtout Albums       : {photos_added_without_albums}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_download_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idAlb, --immich-download-albums'.")
        LOGGER.info(HELP_TEXTS["--immich-download-albums"].replace("'<ALBUMS_NAME>'", f"{ARGS['immich-download-albums']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_albums(ARGS['immich-download-albums'])
    logout_immich()

    if info_messages:
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

def mode_immich_download_ALL(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idAll, --immich-download-all'.")
        LOGGER.info(HELP_TEXTS["--immich-download-all"].replace('<OUTPUT_FOLDER>', f"{ARGS['immich-download-all']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_ALL(output_folder=ARGS['immich-download-all'])
    logout_immich()

    if info_messages:
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

def mode_immich_delete_orphan_assets(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idoa, --immich-delete-orphan-assets'.")
        LOGGER.info(HELP_TEXTS["--immich-delete-orphan-assets"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    delete_assets = immich_delete_orphan_assets(user_confirmation=user_confirmation)
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Orphan Assets deleted             : {delete_assets}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_delete_all_assets(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idAlbs, --immich-delete-all-assets'.")
        LOGGER.info(HELP_TEXTS["--immich-delete-all-assets"])
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete ALL Assets' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    delete_assets = immich_delete_all_assets()
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Assets deleted                    : {delete_assets}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")

def mode_immich_delete_all_albums(user_confirmation=True, info_messages=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-ideAlb, --immich-delete-all-albums'.")
        if ARGS['including-albums-assets']:
            LOGGER.info(f"INFO: Flag detected '-iiaa, --include-albums-assets'.")
        LOGGER.info(HELP_TEXTS["--immich-delete-all-albums"])
        if ARGS['including-albums-assets']:
            LOGGER.info(f"Since, flag '-iiaa, --include-albums-assets' have been detected, ALL the Assets associated to any Albums will also be deleted.")
            LOGGER.info("")
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    delete_albums, delete_assets = immich_delete_all_albums(deleteAlbumsAssets = ARGS['including-albums-assets'])
    logout_immich()

    if info_messages:
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
        LOGGER.info(f"Total Albums deleted                    : {delete_albums}")
        LOGGER.info(f"Total Assets deleted                    : {delete_assets}")
        LOGGER.info("")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info("==================================================")
        LOGGER.info("")
