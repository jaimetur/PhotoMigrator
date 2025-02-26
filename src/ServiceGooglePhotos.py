import Utils
import os, sys
from datetime import datetime, timedelta
from Duplicates import find_duplicates
import ExifFixers
import logging
from CustomLogger import set_log_level

def google_takeout_processor(output_takeout_folder, log_level=logging.INFO):
    from GlobalVariables import LOGGER  # Import global LOGGER
    from GlobalVariables import ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # step 1: Unzip files
        step = 1
        LOGGER.info("")
        LOGGER.info("==============================")
        LOGGER.info(f"{step}. UNPACKING TAKEOUT FOLDER...")
        LOGGER.info("==============================")
        LOGGER.info("")

        if ARGS['google-input-zip-folder']:
            step_start_time = datetime.now()
            Utils.unpack_zips(ARGS['google-input-zip-folder'], ARGS['google-input-takeout-folder'])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")
        else:
            LOGGER.info(f"INFO    : Unzipping skipped (no ZIP files detected in INPUT_FOLDER).")

        if not os.path.isdir(ARGS['google-input-takeout-folder']):
            LOGGER.error(f"ERROR   : Cannot Find INPUT_FOLDER: '{ARGS['google-input-takeout-folder']}'. Exiting...")
            sys.exit(-1)

        # step 2: Pre-Process Takeout folder
        step += 1
        LOGGER.info("")
        LOGGER.info("===================================")
        LOGGER.info(f"{step}. PRE-PROCESSING TAKEOUT FOLDER...")
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
        LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")

        # step 3: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
        step += 1
        LOGGER.info("")
        LOGGER.info("===========================================")
        LOGGER.info(f"{step}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
        LOGGER.info("===========================================")
        LOGGER.info("")
        # Number of files in the original takeout folder
        initial_takeout_numfiles = Utils.count_files_in_folder (ARGS['google-input-takeout-folder'])

        if not ARGS['google-skip-gpth-tool']:
            if ARGS['google-ignore-check-structure']:
                LOGGER.warning("WARNING : Ignore Google Takeout Structure detected ('-gics, --google-ignore-check-structure' flag detected).")
            step_start_time = datetime.now()
            ok = ExifFixers.fix_metadata_with_gpth_tool(
                input_folder=ARGS['google-input-takeout-folder'],
                output_folder=output_takeout_folder,
                symbolic_albums=ARGS['google-create-symbolic-albums'],
                skip_extras=ARGS['google-skip-extras-files'],
                move_takeout_folder=ARGS['google-move-takeout-folder'],
                ignore_takeout_structure=ARGS['google-ignore-check-structure']
            )
            if not ok:
                LOGGER.warning(f"WARNING : Metadata fixing didn't finish properly due to GPTH error.")
                LOGGER.warning(f"WARNING : If your Takeout does not contains Year/Month folder structure, you can use the flag '-gics, --google-ignore-check-structure' to avoid this check.")
            if ARGS['google-move-takeout-folder']:
                Utils.force_remove_directory(ARGS['google-input-takeout-folder'])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")
        if ARGS['google-skip-gpth-tool'] or ARGS['google-ignore-check-structure']:
            LOGGER.info("")
            LOGGER.info("============================================")
            LOGGER.info(f"{step}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
            LOGGER.info("============================================")
            LOGGER.info("")
            if ARGS['google-skip-gpth-tool']:
                LOGGER.warning(
                    f"WARNING : Metadata fixing with GPTH tool skipped ('-sg, --google-skip-gpth-tool' flag detected). step {step}b is needed to copy files manually to output folder.")
            elif ARGS['google-ignore-check-structure']:
                LOGGER.warning(
                    f"WARNING : Flag to Ignore Google Takeout Structure have been detected ('-it, --google-ignore-check-structure'). step {step}b is needed to copy/move files manually to output folder.")
            if ARGS['google-move-takeout-folder']:
                LOGGER.info("INFO    : Moving files from Takeout folder to Output folder manually...")
            else:
                LOGGER.info("INFO    : Copying files from Takeout folder to Output folder manually...")
            step_start_time = datetime.now()
            Utils.copy_move_folder(ARGS['google-input-takeout-folder'], output_takeout_folder,
                                   ignore_patterns=['*.json', '*.j'], move=ARGS['google-move-takeout-folder'])
            if ARGS['google-move-takeout-folder']:
                Utils.force_remove_directory(ARGS['takeout-folder'])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step}b completed in {formatted_duration}.")

        # step 4: Sync .MP4 live pictures timestamp
        step += 1
        LOGGER.info("")
        LOGGER.info("==============================================================")
        LOGGER.info(f"{step}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
        LOGGER.info("==============================================================")
        LOGGER.info("")
        step_start_time = datetime.now()
        LOGGER.info(
            "INFO    : Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
        Utils.sync_mp4_timestamps_with_images(output_takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")

        # step 5: Create Folders Year/Month or Year only structure
        step += 1
        LOGGER.info("")
        LOGGER.info("==========================================")
        LOGGER.info(f"{step}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
        LOGGER.info("==========================================")
        step_start_time = datetime.now()
        # For Albums:
        if ARGS['google-albums-folders-structure'].lower() != 'flatten':
            LOGGER.info("")
            LOGGER.info(
                f"INFO    : Creating Folder structure '{ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
            basedir = output_takeout_folder
            type = ARGS['google-albums-folders-structure']
            exclude_subfolders = ['No-Albums']
            Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
        # For No Albums:
        if ARGS['google-no-albums-folder-structure'].lower() != 'flatten':
            LOGGER.info("")
            LOGGER.info(
                f"INFO    : Creating Folder structure '{ARGS['google-no-albums-folder-structure'].lower()}' for 'No-Albums' folder...")
            basedir = os.path.join(output_takeout_folder, 'No-Albums')
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
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")

        # step 6: Move albums
        step += 1
        LOGGER.info("")
        LOGGER.info("==========================")
        LOGGER.info(f"{step}. MOVING ALBUMS FOLDER...")
        LOGGER.info("==========================")
        LOGGER.info("")
        if not ARGS['google-skip-move-albums']:
            step_start_time = datetime.now()
            Utils.move_albums(output_takeout_folder, exclude_subfolder=['No-Albums', '@eaDir'])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")
        else:
            LOGGER.warning("WARNING : Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")
        albums_found = 0
        if not ARGS['google-skip-move-albums']:
            album_folder = os.path.join(output_takeout_folder, 'Albums')
            if os.path.isdir(album_folder):
                albums_found = len(os.listdir(album_folder))
        else:
            if os.path.isdir(output_takeout_folder):
                albums_found = len(os.listdir(output_takeout_folder)) - 1

        # step 7: Fix Broken Symbolic Links after moving
        step += 1
        symlink_fixed = 0
        symlink_not_fixed = 0
        LOGGER.info("")
        LOGGER.info("===============================================")
        LOGGER.info(f"{step}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
        LOGGER.info("===============================================")
        LOGGER.info("")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.info("INFO    : Fixing broken symbolic links. This step is needed after moving any Folder structure...")
            step_start_time = datetime.now()
            symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(output_takeout_folder)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")
        else:
            LOGGER.warning(
                "WARNING : Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected, so this step is not needed.)")

        # step 8: Remove Duplicates in OUTPUT_TAKEOUT_FOLDER after Fixing
        step += 1
        duplicates_found = 0
        removed_empty_folders = 0
        if ARGS['google-remove-duplicates-files']:
            LOGGER.info("")
            LOGGER.info("==========================================")
            LOGGER.info(f"{step}. REMOVING DUPLICATES IN OUTPUT_TAKEOUT_FOLDER...")
            LOGGER.info("==========================================")
            LOGGER.info("")
            LOGGER.info(f"INFO    : Removing duplicates from OUTPUT_TAKEOUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'No-Albums' folders)...")
            step_start_time = datetime.now()
            duplicates_found, removed_empty_folders = find_duplicates(duplicates_action='remove', duplicates_folders=output_takeout_folder,
                                                                      deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS,
                                                                      timestamp=TIMESTAMP,
                                                                      log_level=logging.INFO)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info(f"INFO    : step {step} completed in {formatted_duration}.")

        # Return Outputs
        return albums_found, symlink_fixed, symlink_not_fixed, duplicates_found, initial_takeout_numfiles, removed_empty_folders


