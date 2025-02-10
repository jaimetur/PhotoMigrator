import Utils
import os, sys
from datetime import datetime, timedelta
from Duplicates import find_duplicates
import Fixers

def google_takeout_processor(OUTPUT_TAKEOUT_FOLDER):
    from GLOBALS import LOGGER  # Import global LOGGER
    from GLOBALS import ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS

    # STEP 1: Unzip files
    STEP = 1
    LOGGER.info("")
    LOGGER.info("==============================")
    LOGGER.info(f"{STEP}. UNPACKING TAKEOUT FOLDER...")
    LOGGER.info("==============================")
    LOGGER.info("")
    if ARGS['google-input-zip-folder']:
        step_start_time = datetime.now()
        Utils.unpack_zips(ARGS['google-input-zip-folder'], ARGS['google-input-takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning(
            "WARNING : Unzipping skipped (no argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' given or Running Mode All-in-One with input folder directly unzipped).")

    if not os.path.isdir(ARGS['google-input-takeout-folder']):
        LOGGER.error(f"ERROR   : Cannot Find INPUT_FOLDER: '{ARGS['google-input-takeout-folder']}'. Exiting...")
        sys.exit(-1)

    # STEP 2: Pre-Process Takeout folder
    STEP += 1
    LOGGER.info("")
    LOGGER.info("===================================")
    LOGGER.info(f"{STEP}. PRE-PROCESSING TAKEOUT FOLDER...")
    LOGGER.info("===================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
    LOGGER.info(
        "INFO    : Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
    Utils.delete_subfolders(ARGS['google-input-takeout-folder'], "@eaDir")
    # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
    LOGGER.info("")
    LOGGER.info("INFO    : Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
    Utils.fix_mp4_files(ARGS['google-input-takeout-folder'])
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
    LOGGER.info("")
    LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")

    # STEP 3: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    STEP += 1
    LOGGER.info("")
    LOGGER.info("===========================================")
    LOGGER.info(f"{STEP}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    LOGGER.info("===========================================")
    LOGGER.info("")
    if not ARGS['google-skip-gpth-tool']:
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning(
                "WARNING : Ignore Google Takeout Structure detected ('-it, --google-ignore-check-structure' flag detected).")
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
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")
    if ARGS['google-skip-gpth-tool'] or ARGS['google-ignore-check-structure']:
        LOGGER.info("")
        LOGGER.info("============================================")
        LOGGER.info(f"{STEP}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
        LOGGER.info("============================================")
        LOGGER.info("")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(
                f"WARNING : Metadata fixing with GPTH tool skipped ('-sg, --google-skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
        elif ARGS['google-ignore-check-structure']:
            LOGGER.warninf(
                f"WARNING : Flag to Ignore Google Takeout Structure have been detected ('-it, --google-ignore-check-structure'). Step {STEP}b is needed to copy/move files manually to output folder.")
        if ARGS['google-move-takeout-folder']:
            LOGGER.info("INFO    : Moving files from Takeout folder to Output folder manually...")
        else:
            LOGGER.info("INFO    : Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder(ARGS['google-input-takeout-folder'], OUTPUT_TAKEOUT_FOLDER,
                               ignore_patterns=['*.json', '*.j'], move=ARGS['google-move-takeout-folder'])
        if ARGS['google-move-takeout-folder']:
            Utils.force_remove_directory(ARGS['takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP}b completed in {formatted_duration}.")

    # STEP 4: Sync .MP4 live pictures timestamp
    STEP += 1
    LOGGER.info("")
    LOGGER.info("==============================================================")
    LOGGER.info(f"{STEP}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
    LOGGER.info("==============================================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    LOGGER.info(
        "INFO    : Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
    Utils.sync_mp4_timestamps_with_images(OUTPUT_TAKEOUT_FOLDER)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
    LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")

    # STEP 5: Create Folders Year/Month or Year only structure
    STEP += 1
    LOGGER.info("")
    LOGGER.info("==========================================")
    LOGGER.info(f"{STEP}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
    LOGGER.info("==========================================")
    step_start_time = datetime.now()
    # For Albums:
    if ARGS['google-albums-folders-structure'].lower() != 'flatten':
        LOGGER.info("")
        LOGGER.info(
            f"INFO    : Creating Folder structure '{ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
        basedir = OUTPUT_TAKEOUT_FOLDER
        type = ARGS['google-albums-folders-structure']
        exclude_subfolders = ['No-Albums']
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # For No Albums:
    if ARGS['google-no-albums-folder-structure'].lower() != 'flatten':
        LOGGER.info("")
        LOGGER.info(
            f"INFO    : Creating Folder structure '{ARGS['google-no-albums-folder-structure'].lower()}' for 'No-Albums' folder...")
        basedir = os.path.join(OUTPUT_TAKEOUT_FOLDER, 'No-Albums')
        type = ARGS['google-no-albums-folder-structure']
        exclude_subfolders = []
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # If no fiolder structure is detected:
    if ARGS['google-albums-folders-structure'].lower() == 'flatten' and ARGS[
        'google-no-albums-folder-structure'].lower() == 'flatten':
        LOGGER.info("")
        LOGGER.warning(
            "WARNING : No argument '-as, --google-albums-folders-structure' and '-ns, --google-no-albums-folder-structure' detected. All photos and videos will be flattened within their folders without any date organization.")
    else:
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")

    # STEP 6: Move albums
    STEP += 1
    LOGGER.info("")
    LOGGER.info("==========================")
    LOGGER.info(f"{STEP}. MOVING ALBUMS FOLDER...")
    LOGGER.info("==========================")
    LOGGER.info("")
    if not ARGS['google-skip-move-albums']:
        step_start_time = datetime.now()
        Utils.move_albums(OUTPUT_TAKEOUT_FOLDER, exclude_subfolder=['No-Albums', '@eaDir'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING : Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")
    albums_found = 0
    if not ARGS['google-skip-move-albums']:
        album_folder = os.path.join(OUTPUT_TAKEOUT_FOLDER, 'Albums')
        if os.path.isdir(album_folder):
            albums_found = len(os.listdir(album_folder))
    else:
        if os.path.isdir(OUTPUT_TAKEOUT_FOLDER):
            albums_found = len(os.listdir(OUTPUT_TAKEOUT_FOLDER)) - 1

    # STEP 7: Fix Broken Symbolic Links after moving
    STEP += 1
    symlink_fixed = 0
    symlink_not_fixed = 0
    LOGGER.info("")
    LOGGER.info("===============================================")
    LOGGER.info(f"{STEP}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
    LOGGER.info("===============================================")
    LOGGER.info("")
    if ARGS['google-create-symbolic-albums']:
        LOGGER.info("INFO    : Fixing broken symbolic links. This step is needed after moving any Folder structure...")
        step_start_time = datetime.now()
        symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(OUTPUT_TAKEOUT_FOLDER)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning(
            "WARNING : Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected, so this step is not needed.)")

    # STEP 8: Remove Duplicates in OUTPUT_TAKEOUT_FOLDER after Fixing
    STEP += 1
    duplicates_found = 0
    if ARGS['google-remove-duplicates-files']:
        LOGGER.info("")
        LOGGER.info("==========================================")
        LOGGER.info(f"{STEP}. REMOVING DUPLICATES IN OUTPUT_TAKEOUT_FOLDER...")
        LOGGER.info("==========================================")
        LOGGER.info("")
        LOGGER.info(
            "INFO    : Removing duplicates from OUTPUT_TAKEOUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'No-Albums' folders)...")
        step_start_time = datetime.now()
        duplicates_found = find_duplicates(duplicates_action='remove', duplicates_folders=OUTPUT_TAKEOUT_FOLDER,
                                           deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS,
                                           timestamp=TIMESTAMP)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : Step {STEP} completed in {formatted_duration}.")

    # Return Outputs
    return albums_found, symlink_fixed, symlink_not_fixed, duplicates_found


