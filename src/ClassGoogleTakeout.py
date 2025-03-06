# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-

"""
Single-class version of ServiceGooglePhotos.py:
 - Preserves original log messages without altering their text.
 - Replaces the global LOGGER usage with self.logger from GlobalVariables.
 - Docstrings / comments are now in English.
"""

import os
import sys
from datetime import datetime, timedelta
import logging

# Keep your existing imports for external modules:
import Utils
import ExifFixers
from Duplicates import find_duplicates
from CustomLogger import set_log_level

##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassGoogleTakeout:
    """
    Encapsulates the logic from ServiceGooglePhotos.py in a single class.
    Replaces global LOGGER references with self.logger, preserving the original log text.
    """

    def __init__(self):
        """
        Constructor that imports the global LOGGER and other relevant variables from GlobalVariables,
        storing them as attributes for use inside methods.
        """
        from GlobalVariables import LOGGER, ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS
        self.logger = LOGGER
        self.ARGS = ARGS
        self.TIMESTAMP = TIMESTAMP
        self.DEPRIORITIZE_FOLDERS_PATTERNS = DEPRIORITIZE_FOLDERS_PATTERNS

    def google_takeout_processor(self, output_takeout_folder, log_level=logging.INFO):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        google_takeout_processor() function, but uses self.logger and self.ARGS instead of global.
        """
        with set_log_level(self.logger, log_level):  # Temporarily adjust log level
            # step 1: Unzip files
            step = 1
            self.logger.info("")
            self.logger.info("==============================")
            self.logger.info(f"{step}. UNPACKING TAKEOUT FOLDER...")
            self.logger.info("==============================")
            self.logger.info("")

            if self.ARGS['google-input-zip-folder']:
                step_start_time = datetime.now()
                Utils.unpack_zips(self.ARGS['google-input-zip-folder'], self.ARGS['google-input-takeout-folder'])
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")
            else:
                self.logger.info(f"INFO    : Unzipping skipped (no ZIP files detected in INPUT_FOLDER).")

            if not os.path.isdir(self.ARGS['google-input-takeout-folder']):
                self.logger.error(f"ERROR   : Cannot Find INPUT_FOLDER: '{self.ARGS['google-input-takeout-folder']}'. Exiting...")
                sys.exit(-1)

            # step 2: Pre-Process Takeout folder
            step += 1
            self.logger.info("")
            self.logger.info("===================================")
            self.logger.info(f"{step}. PRE-PROCESSING TAKEOUT FOLDER...")
            self.logger.info("===================================")
            self.logger.info("")
            step_start_time = datetime.now()
            # Delete hidden subfolders '@eaDir'
            self.logger.info("INFO    : Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
            Utils.delete_subfolders(self.ARGS['google-input-takeout-folder'], "@eaDir")
            # Fix .MP4 timestamps
            self.logger.info("")
            self.logger.info("INFO    : Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
            Utils.fix_mp4_files(self.ARGS['google-input-takeout-folder'])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            self.logger.info("")
            self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")

            # step 3: Process photos with GPTH tool
            step += 1
            self.logger.info("")
            self.logger.info("===========================================")
            self.logger.info(f"{step}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
            self.logger.info("===========================================")
            self.logger.info("")
            # Count initial files
            initial_takeout_numfiles = Utils.count_files_in_folder(self.ARGS['google-input-takeout-folder'])

            if not self.ARGS['google-skip-gpth-tool']:
                if self.ARGS['google-ignore-check-structure']:
                    self.logger.warning("WARNING : Ignore Google Takeout Structure detected ('-gics, --google-ignore-check-structure' flag detected).")
                else:
                    # Check Takeout structure
                    has_takeout_structure = self.contains_takeout_structure(self.ARGS['google-input-takeout-folder'])
                    if not has_takeout_structure:
                        self.logger.warning(f"WARNING : No Takeout structure detected in input folder. The tool will process the folder ignoring Takeout structure.")
                        self.ARGS['google-ignore-check-structure'] = True

                step_start_time = datetime.now()
                ok = ExifFixers.fix_metadata_with_gpth_tool(
                    input_folder=self.ARGS['google-input-takeout-folder'],
                    output_folder=output_takeout_folder,
                    symbolic_albums=self.ARGS['google-create-symbolic-albums'],
                    skip_extras=self.ARGS['google-skip-extras-files'],
                    move_takeout_folder=self.ARGS['google-move-takeout-folder'],
                    ignore_takeout_structure=self.ARGS['google-ignore-check-structure'],
                    log_level=logging.WARNING
                )
                if not ok:
                    self.logger.warning(f"WARNING : Metadata fixing didn't finish properly due to GPTH error.")
                    self.logger.warning(f"WARNING : If your Takeout does not contains Year/Month folder structure, you can use '-gics, --google-ignore-check-structure' flag.")
                if self.ARGS['google-move-takeout-folder']:
                    Utils.force_remove_directory(self.ARGS['google-input-takeout-folder'])
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")
            if self.ARGS['google-skip-gpth-tool'] or self.ARGS['google-ignore-check-structure']:
                self.logger.info("")
                self.logger.info("============================================")
                self.logger.info(f"{step}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
                self.logger.info("============================================")
                self.logger.info("")
                if self.ARGS['google-skip-gpth-tool']:
                    self.logger.warning(f"WARNING : Metadata fixing with GPTH tool skipped ('-gsgt, --google-skip-gpth-tool' flag). step {step}b is needed to copy files manually to output folder.")
                elif self.ARGS['google-ignore-check-structure']:
                    self.logger.warning(f"WARNING : Flag to Ignore Google Takeout Structure detected. step {step}b is needed to copy/move files manually to output folder.")
                if self.ARGS['google-move-takeout-folder']:
                    self.logger.info("INFO    : Moving files from Takeout folder to Output folder...")
                else:
                    self.logger.info("INFO    : Copying files from Takeout folder to Output folder...")

                step_start_time = datetime.now()
                Utils.copy_move_folder(self.ARGS['google-input-takeout-folder'], output_takeout_folder,
                                       ignore_patterns=['*.json', '*.j'],
                                       move=self.ARGS['google-move-takeout-folder'])
                if self.ARGS['google-move-takeout-folder']:
                    Utils.force_remove_directory(self.ARGS['takeout-folder'])
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step}b completed in {formatted_duration}.")

            # step 4: Sync .MP4 live pictures timestamp
            step += 1
            self.logger.info("")
            self.logger.info("==============================================================")
            self.logger.info(f"{step}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
            self.logger.info("==============================================================")
            self.logger.info("")
            step_start_time = datetime.now()
            self.logger.info("INFO    : Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
            Utils.sync_mp4_timestamps_with_images(output_takeout_folder)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")

            # step 5: Create Folders Year/Month or Year only structure
            step += 1
            self.logger.info("")
            self.logger.info("==========================================")
            self.logger.info(f"{step}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
            self.logger.info("==========================================")
            step_start_time = datetime.now()
            # For Albums
            if self.ARGS['google-albums-folders-structure'].lower() != 'flatten':
                self.logger.info("")
                self.logger.info(f"INFO    : Creating Folder structure '{self.ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
                basedir = output_takeout_folder
                type_structure = self.ARGS['google-albums-folders-structure']
                exclude_subfolders = ['No-Albums']
                Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders)

            # For No-Albums
            if self.ARGS['google-no-albums-folder-structure'].lower() != 'flatten':
                self.logger.info("")
                self.logger.info(f"INFO    : Creating Folder structure '{self.ARGS['google-no-albums-folder-structure'].lower()}' for 'No-Albums' folder...")
                basedir = os.path.join(output_takeout_folder, 'No-Albums')
                type_structure = self.ARGS['google-no-albums-folder-structure']
                exclude_subfolders = []
                Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders)

            # If flatten
            if (self.ARGS['google-albums-folders-structure'].lower() == 'flatten'
                and self.ARGS['google-no-albums-folder-structure'].lower() == 'flatten'):
                self.logger.info("")
                self.logger.warning("WARNING : No argument '-as, --google-albums-folders-structure' and '-ns, --google-no-albums-folder-structure' detected. All photos and videos will be flattened in their folders.")
            else:
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")

            # step 6: Move albums
            step += 1
            self.logger.info("")
            self.logger.info("==========================")
            self.logger.info(f"{step}. MOVING ALBUMS FOLDER...")
            self.logger.info("==========================")
            self.logger.info("")
            if not self.ARGS['google-skip-move-albums']:
                step_start_time = datetime.now()
                Utils.move_albums(output_takeout_folder, exclude_subfolder=['No-Albums', '@eaDir'])
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")
            else:
                self.logger.warning("WARNING : Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")

            valid_albums_found = 0
            if not self.ARGS['google-skip-move-albums']:
                album_folder = os.path.join(output_takeout_folder, 'Albums')
                if os.path.isdir(album_folder):
                    valid_albums_found = Utils.count_valid_albums(album_folder)
            else:
                if os.path.isdir(output_takeout_folder):
                    valid_albums_found = Utils.count_valid_albums(output_takeout_folder)

            # step 7: Fix Broken Symbolic Links
            step += 1
            symlink_fixed = 0
            symlink_not_fixed = 0
            self.logger.info("")
            self.logger.info("===============================================")
            self.logger.info(f"{step}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
            self.logger.info("===============================================")
            self.logger.info("")
            if self.ARGS['google-create-symbolic-albums']:
                self.logger.info("INFO    : Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                step_start_time = datetime.now()
                symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(output_takeout_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")
            else:
                self.logger.warning("WARNING : Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected).")

            # step 8: Remove Duplicates
            step += 1
            duplicates_found = 0
            removed_empty_folders = 0
            if self.ARGS['google-remove-duplicates-files']:
                self.logger.info("")
                self.logger.info("==========================================")
                self.logger.info(f"{step}. REMOVING DUPLICATES IN OUTPUT_TAKEOUT_FOLDER...")
                self.logger.info("==========================================")
                self.logger.info("")
                self.logger.info("INFO    : Removing duplicates from OUTPUT_TAKEOUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'No-Albums' folders)...")
                step_start_time = datetime.now()
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=output_takeout_folder,
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    log_level=logging.INFO
                )
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                self.logger.info(f"INFO    : step {step} completed in {formatted_duration}.")

            return (valid_albums_found, symlink_fixed, symlink_not_fixed, duplicates_found,
                    initial_takeout_numfiles, removed_empty_folders)

    @staticmethod
    def contains_takeout_structure(input_folder):
        """
        Recursively traverses all subfolders in the given input directory and checks
        if any subfolder starts with 'Photos from ' followed by four digits.

        Returns True if at least one matching subfolder is found, False otherwise.
        """
        for root, dirs, _ in os.walk(input_folder):
            for folder in dirs:
                if folder.startswith("Photos from ") and len(folder) >= 15 and folder[12:16].isdigit():
                    return True
        return False

##############################################################################
#                                END OF CLASS                                #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
# Example main usage
if __name__ == "__main__":
    import sys
    from Utils import change_workingdir
    change_workingdir()

    takeout = ClassGoogleTakeout()
    result = takeout.google_takeout_processor("Output_Takeout_Folder", log_level=logging.DEBUG)
    print(result)
