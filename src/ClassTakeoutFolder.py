# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-

"""
Single-class version of ServiceGooglePhotos.py:
 - Preserves original log messages without altering their text.
 - Replaces the global LOGGER usage with LOGGER from GlobalVariables.
 - Docstrings / comments are now in English.
"""

import os
import sys
from datetime import datetime, timedelta
import logging
import inspect
import shutil
from pathlib import Path

# Keep your existing imports for external modules:
import Utils
from Utils import rename_album_folders
import MetadataFixers
from Duplicates import find_duplicates
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER

# Import ClassLocalFolder (Parent Class of this)
from ClassLocalFolder import ClassLocalFolder


##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassTakeoutFolder(ClassLocalFolder):
    def __init__(self, takeout_folder):
        """
        Inicializa la clase con la carpeta base (donde se guardan los archivos ya procesados)
        y la carpeta de entrada (donde se encuentran los archivos sin procesar).
        """

        from GlobalVariables import ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS

        self.ARGS = ARGS
        self.TIMESTAMP = TIMESTAMP
        self.DEPRIORITIZE_FOLDERS_PATTERNS = DEPRIORITIZE_FOLDERS_PATTERNS
        self.log_level = logging.INFO

        # # Create atributes from the ARGS given:
        # self.skip_gpth                      = self.ARGS['google-skip-gpth-tool']
        # self.ignore_takeout_structure       = self.ARGS['google-ignore-check-structure']

        self.takeout_folder = Path(takeout_folder)
        self.takeout_folder.mkdir(parents=True, exist_ok=True)  # Asegurar que input_folder existe

        # Verificar si la carpeta necesita ser descomprimida
        self.needs_unzip = self.check_if_needs_unzip()
        self.unzipped_folder = None

        # Verificar si la carpeta necesita ser procesada
        self.needs_process = self.check_if_needs_process()

        # Contador de pasos durante el procesamiento
        self.step = 0

        self.CLIENT_NAME = f'Google Takeout Folder ({self.takeout_folder.name})'

#---------------------------------------------- CLASS METHODS ----------------------------------------------
    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_process(self, log_level=logging.INFO):
        step_name = '[CHECKS/UNZIP]-[Check Takeout Structure] : '
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return Utils.contains_takeout_structure(input_folder=self.takeout_folder, step_name=step_name, log_level=log_level)

    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_unzip(self, log_level=logging.INFO):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            for file in os.listdir(self.takeout_folder):
                if file.endswith('.zip'):
                    return True
            return False

    def unzip(self, input_folder, unzip_folder, log_level=logging.INFO):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        process() function, but uses LOGGER and self.ARGS instead of global.
        """
        with set_log_level(LOGGER, log_level):  # Temporarily adjust log level
            step_name = '[CHECKS/UNZIP]-[Check Takeout Structure] : '
            # Unzip files
            LOGGER.info(f"INFO    : {step_name}Unpacking Takeout Folder...")
            LOGGER.info(f"INFO    : {step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")
            LOGGER.info("")
            step_start_time = datetime.now()
            Utils.unpack_zips(input_folder, unzip_folder, step_name=step_name)
            # Make the 'Unzipped' folder as the new takeout_folder for the object
            self.unzipped_folder = Path(unzip_folder)
            # Change flag self.check_if_needs_unzip to False
            self.needs_unzip = False
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Unzipping completed in {formatted_duration}.")
            LOGGER.info("")


    def precheck_takeout_and_process(self, capture_output=False, capture_errors=True, print_messages=True, skip_process=False):

        # Step 1: Pre-Checks & Extraction Process
        # ----------------------------------------------------------------------------------------------------------------------
        step_name = '[CHECKS/UNZIP]-[Check/Unzip Takeout Structure] : '
        self.step += 1
        LOGGER.info("")
        LOGGER.info("=============================================")
        LOGGER.info(f"INFO    : {self.step}. CHECK/UNZIP TAKEOUT STRUCTURE...")
        LOGGER.info("=============================================")
        LOGGER.info("")
        step_start_time = datetime.now()
        if self.needs_unzip:
            LOGGER.info(f"INFO    : {step_name}🗳️ Input Folder contains ZIP files and needs to be unzipped first. Unzipping it...")
            unzip_folder = Path(f"{self.takeout_folder}_unzipped_{self.TIMESTAMP}")
            # Unzip the files into unzip_folder
            self.unzip(input_folder=self.takeout_folder, unzip_folder=unzip_folder, log_level=self.log_level)
            self.needs_process = Utils.contains_takeout_structure(input_folder=self.unzipped_folder, step_name=step_name)

        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
        LOGGER.info("")
        LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")

        if not skip_process:
            if self.needs_process:
                LOGGER.info(f"INFO    : {step_name}🔢 Input Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")
                # if self.unzipped_folder:
                #     base_folder = Path(f"{self.unzipped_folder}_{self.ARGS['google-output-folder-suffix']}_{self.TIMESTAMP}")
                # else:
                base_folder = Path(f"{self.takeout_folder}_{self.ARGS['google-output-folder-suffix']}_{self.TIMESTAMP}")
                # Process Takeout_folder and put output into base_folder
                self.process(output_takeout_folder=base_folder, capture_output=capture_output, capture_errors=capture_errors, print_messages=print_messages, log_level=logging.INFO)
                super().__init__(base_folder)  # Inicializar con la carpeta procesada
            else:
                base_folder = self.takeout_folder
                super().__init__(base_folder)  # Inicializar con la carpeta original si no se necesita procesamiento


    def process(self, output_takeout_folder, capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=True, log_level=logging.INFO):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        process() function, but uses LOGGER and self.ARGS instead of global.
        """
        from GlobalVariables import LOGGER
        from DataModels import init_process_results
        
        result = init_process_results()
        
        # Determine where the Albums will be located
        if not self.ARGS['google-skip-move-albums']:
            album_folder = os.path.join(output_takeout_folder, 'Albums')
        else:
            album_folder = output_takeout_folder

        # Start the Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            LOGGER.info("")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"INFO    : 🔢 TAKEOUT PROCESSING STARTED...")
            LOGGER.info(f"==========================================")
            processing_start_time = datetime.now()

            if capture_output is None: capture_output=self.ARGS['show-gpth-info']
            if capture_errors is None: capture_errors=self.ARGS['show-gpth-errors']

            # Pre-check the object with skip_process=True to just unzip files in case they are zipped.
            self.precheck_takeout_and_process(skip_process=True)


            # Step 2: Pre-Process Takeout folder
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            LOGGER.info("")
            LOGGER.info("=============================================")
            LOGGER.info(f"INFO    : {self.step}. PRE-PROCESSING TAKEOUT FOLDER...")
            LOGGER.info("=============================================")
            LOGGER.info("")
            step_start_time = datetime.now()
            # Select the input_folder deppending if the Takeout have been unzipped or not
            if self.unzipped_folder:
                input_folder = self.unzipped_folder
            else:
                input_folder = self.takeout_folder

            # Delete hidden subfolders '@eaDir'
            step_name = '[PRE-PROCESS]-[Clean Takeout Folder] : '
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Cleaning hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
            Utils.delete_subfolders(input_folder=input_folder, folder_name_to_delete="@eaDir", step_name=step_name)

            # Fix .MP4 JSON
            step_name = '[PRE-PROCESS]-[MP4 Fixer        ] : '
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
            result_mp4_files_fixed = Utils.fix_mp4_files(input_folder=input_folder, step_name=step_name, log_level=logging.INFO)
            LOGGER.info(f"INFO    : {step_name}Fixing MP4 from live pictures metadata finished!")
            LOGGER.info(f"INFO    : {step_name}Total MP4 from live pictures Files fixed         : {result_mp4_files_fixed}")

            # Fix truncated suffixes (such as '-ha edit.jpg' or '-ha e.jpg', or '-effec', or '-supplemen',...)
            step_name = '[PRE-PROCESS]-[Truncations Fixer] : '
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Fixing Truncated Special Suffixes from Google Photos and rename files to include complete special suffix...")
            result_fix_truncations = Utils.fix_truncations(input_folder=input_folder, step_name=step_name, log_level=logging.INFO)
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Fixing Truncated Files finished!")
            LOGGER.info(f"INFO    : {step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"INFO    : {step_name}Total Files files in Takeout folder              : {result_fix_truncations['total_files']}")
            LOGGER.info(f"INFO    : {step_name}  - Total Fixed Files files in Takeout folder    : {result_mp4_files_fixed + result_fix_truncations['total_files_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}    - Total MP4 from live pictures Files fixed   : {result_mp4_files_fixed:<7}")
            LOGGER.info(f"INFO    : {step_name}    - Total Truncated files fixed                : {result_fix_truncations['total_files_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}      - Total JSON files fixed                   : {result_fix_truncations['json_files_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}        - Supplemental-metadata changes          : {result_fix_truncations['supplemental_metadata_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}        - Extensions changes                     : {result_fix_truncations['extensions_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}      - Total Images/Videos files fixed          : {result_fix_truncations['non_json_files_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}        - Special Suffixes changes               : {result_fix_truncations['special_suffixes_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}        - Edited Suffixes changes                : {result_fix_truncations['edited_suffixes_fixed']:<7}")
            LOGGER.info(f"INFO    : {step_name}-----------------------------------------------------------------------------------")

            # Count initial files in Takeout Folder before to process with GPTH, since once process input_folder may be deleted if --google-move-takeout-folder has been given
            step_name = '[PRE-PROCESS]-[Statistics       ] : '
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Counting files in Takeout Folder: {input_folder}...")
            # New function to count all file types and extract also date info
            initial_takeout_counters = Utils.count_files_per_type_and_date(input_folder=input_folder, within_json_sidecar=False, log_level=log_level)
            # Clean input dict
            result['input_counters'].clear()
            # Assign all pairs key-value from initial_takeout_counters to counter['input_counters'] dict
            result['input_counters'].update(initial_takeout_counters)

            LOGGER.info(f"INFO    : {step_name}Counting Files finished!")
            LOGGER.info(f"INFO    : {step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"INFO    : {step_name}Total Files in Takeout folder                    : {result['input_counters']['total_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}Total Non-Supported files in Takeout folder      : {result['input_counters']['unsupported_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}Total Supported files in Takeout folder          : {result['input_counters']['supported_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}  - Total Media files in Takeout folder          : {result['input_counters']['media_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}    - Total Images in Takeout folder             : {result['input_counters']['photo_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}      - With Date                                : {result['input_counters']['photos']['with_date']:<7} ({result['input_counters']['photos']['pct_with_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"INFO    : {step_name}      - Without Date                             : {result['input_counters']['photos']['without_date']:<7} ({result['input_counters']['photos']['pct_without_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"INFO    : {step_name}    - Total Videos in Takeout folder             : {result['input_counters']['video_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}      - With Date                                : {result['input_counters']['videos']['with_date']:<7} ({result['input_counters']['videos']['pct_with_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"INFO    : {step_name}      - Without Date                             : {result['input_counters']['videos']['without_date']:<7} ({result['input_counters']['videos']['pct_without_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"INFO    : {step_name}  - Total Non-Media files in Takeout folder      : {result['input_counters']['non_media_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}    - Total Metadata in Takeout folder           : {result['input_counters']['metadata_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}    - Total Sidecars in Takeout folder           : {result['input_counters']['sidecar_files']:<7}")
            LOGGER.info(f"INFO    : {step_name}-----------------------------------------------------------------------------------")


            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            step_name = '[PRE-PROCESS] : '
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 3: Process photos with GPTH tool
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-skip-gpth-tool']:
                step_name = '[PROCESS]-[Metadata Processing] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("=====================================================")
                LOGGER.info(f"INFO    : {self.step}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
                LOGGER.info("=====================================================")
                LOGGER.info("")
                step_start_time = datetime.now()
                LOGGER.info(f"INFO    : {step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")

                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"WARNING : {step_name}Google Takeout Structure detected ('-gics, --google-ignore-check-structure' flag detected).")
                else:
                    # Check Takeout structure
                    has_takeout_structure = Utils.contains_takeout_structure(input_folder=input_folder, step_name=step_name)
                    if not has_takeout_structure:
                        LOGGER.warning(f"WARNING : {step_name}No Takeout structure detected in input folder. The tool will process the folder ignoring Takeout structure.")
                        self.ARGS['google-ignore-check-structure'] = True

                ok = MetadataFixers.fix_metadata_with_gpth_tool(
                    input_folder=input_folder,
                    output_folder=output_takeout_folder,
                    capture_output=capture_output,
                    capture_errors=capture_errors,
                    print_messages=print_messages,
                    symbolic_albums=self.ARGS['google-create-symbolic-albums'],
                    skip_extras=self.ARGS['google-skip-extras-files'],
                    move_takeout_folder=self.ARGS['google-move-takeout-folder'],
                    ignore_takeout_structure=self.ARGS['google-ignore-check-structure'],
                    step_name=step_name,
                    log_level=log_level
                )
                if not ok:
                    LOGGER.warning(f"WARNING : {step_name}Metadata fixing didn't finish properly due to GPTH error.")
                    LOGGER.warning(f"WARNING : {step_name}If your Takeout does not contains Year/Month folder structure, you can use '-gics, --google-ignore-check-structure' flag.")
                    # return (0, 0, 0, 0, initial_takeout_numfiles, 0, 0, 0, 0, 0)
                    return result

                # Determine if manual copy/move is needed (for step 4)
                manual_copy_move_needed = self.ARGS['google-skip-gpth-tool'] or self.ARGS['google-ignore-check-structure']

                # if manual copy is detected, don't delete the input folder yet, will do it in next step
                if self.ARGS['google-move-takeout-folder'] and not manual_copy_move_needed:
                    Utils.force_remove_directory(input_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 4: Copy/Move files to output folder manually
            # ----------------------------------------------------------------------------------------------------------------------
            if manual_copy_move_needed:
                step_name = '[POST]-[Copy/Move] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("======================================================")
                LOGGER.info(f"INFO    : {self.step}. COPYING/MOVING FILES TO OUTPUT FOLDER...")
                LOGGER.info("======================================================")
                LOGGER.info("")
                step_start_time = datetime.now()
                if self.ARGS['google-skip-gpth-tool']:
                    LOGGER.warning(f"WARNING : {step_name}Metadata fixing with GPTH tool skipped ('-gsgt, --google-skip-gpth-tool' flag). step {self.step} is needed to copy files manually to output folder.")
                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"WARNING : {step_name}Flag to Ignore Google Takeout Structure detected. step {self.step} is needed to copy/move files manually to output folder.")
                if self.ARGS['google-move-takeout-folder']:
                    LOGGER.info(f"INFO    : {step_name}Moving files from Takeout folder to Output folder...")
                else:
                    LOGGER.info(f"INFO    : {step_name}Copying files from Takeout folder to Output folder...")

                Utils.copy_move_folder(input_folder, output_takeout_folder, ignore_patterns=['*.json', '*.j'], move=self.ARGS['google-move-takeout-folder'], step_name=step_name)
                if self.ARGS['google-move-takeout-folder']:
                    Utils.force_remove_directory(input_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 5: Sync .MP4 live pictures timestamp
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            step_name = '[POST]-[MP4 Timestamp Synch] : '
            LOGGER.info("")
            LOGGER.info("========================================================================")
            LOGGER.info(f"INFO    : {self.step}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
            LOGGER.info("========================================================================")
            LOGGER.info("")
            step_start_time = datetime.now()
            LOGGER.info(f"INFO    : {step_name}Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
            Utils.sync_mp4_timestamps_with_images(input_folder=output_takeout_folder, step_name=step_name)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 6: Create Folders Year/Month or Year only structure
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-albums-folders-structure'].lower() != 'flatten' or self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten' or (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                step_name = '[POST]-[Create year/month struct] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("====================================================")
                LOGGER.info(f"INFO    : {self.step}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
                LOGGER.info("====================================================")
                step_start_time = datetime.now()
                # For Albums
                if self.ARGS['google-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info("")
                    LOGGER.info(f"INFO    : {step_name}Creating Folder structure '{self.ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
                    basedir = output_takeout_folder
                    type_structure = self.ARGS['google-albums-folders-structure']
                    exclude_subfolders = ['No-Albums']
                    Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders, step_name=step_name)

                # For No-Albums
                if self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info("")
                    LOGGER.info(f"INFO    : {step_name}Creating Folder structure '{self.ARGS['google-no-albums-folders-structure'].lower()}' for 'No-Albums' folders...")
                    basedir = os.path.join(output_takeout_folder, 'No-Albums')
                    type_structure = self.ARGS['google-no-albums-folders-structure']
                    exclude_subfolders = []
                    Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders, step_name=step_name)

                # If flatten
                if (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                    LOGGER.info("")
                    LOGGER.warning(f"WARNING : {step_name}No argument '-gafs, --google-albums-folders-structure' and '-gnas, --google-no-albums-folders-structure' detected. All photos and videos will be flattened in their folders.")

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 7: Move albums
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-skip-move-albums']:
                step_name = '[POST]-[Move Albums] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("====================================")
                LOGGER.info(f"INFO    : {self.step}. MOVING ALBUMS FOLDER...")
                LOGGER.info("====================================")
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Moving All your albums into 'Albums' folder for a better organization...")
                step_start_time = datetime.now()
                Utils.move_albums(input_folder=output_takeout_folder, exclude_subfolder=['No-Albums', '@eaDir'], step_name=step_name)
                step_end_time = datetime.now()
                LOGGER.info(f"INFO    : {step_name}All your albums have been moved successfully!")
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 8: Remove Duplicates
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-remove-duplicates-files']:
                step_name = '[POST]-[Remove Duplicates] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("==============================================================")
                LOGGER.info(f"INFO    : {self.step}. REMOVING DUPLICATES IN <OUTPUT_TAKEOUT_FOLDER>...")
                LOGGER.info("==============================================================")
                LOGGER.info("")
                step_start_time = datetime.now()

                # First Remove Duplicates from OUTPUT_TAKEOUT_FOLDER (excluding 'No-Albums' folder)
                LOGGER.info(f"INFO    : {step_name}1. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>', excluding 'No-Albums' folder...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=output_takeout_folder,
                    exclusion_folders=['No-Albums'],    # Exclude 'No-Albums' folder since it will contain duplicates of all the assets withini 'Albums' subfolders.
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=logging.INFO
                )
                result['duplicates_found'] += duplicates_found
                result['removed_empty_folders'] += removed_empty_folders

                # Second Remove Duplicates from OUTPUT_TAKEOUT_FOLDER/No-Albums (excluding any other folder outside it).
                LOGGER.info(f"INFO    : {step_name}2. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>/No-Albums', excluding any other folders outside it...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=os.path.join(output_takeout_folder, 'No-Albums'),
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=logging.INFO
                )
                result['duplicates_found'] += duplicates_found
                result['removed_empty_folders'] += removed_empty_folders

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 9: Fix Broken Symbolic Links
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-create-symbolic-albums']:
                step_name = '[POST]-[Fix Symlinks] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("=========================================================")
                LOGGER.info(f"INFO    : {self.step}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
                LOGGER.info("=========================================================")
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                step_start_time = datetime.now()
                result['symlink_fixed'], result['symlink_not_fixed'] = Utils.fix_symlinks_broken(input_folder=output_takeout_folder, step_name=step_name)

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 10: Rename Albums Folders based on content date
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-rename-albums-folders']:
                step_name = '[POST]-[Album Renaming] : '
                self.step += 1
                LOGGER.info("")
                LOGGER.info("============================================================")
                LOGGER.info(f"INFO    : {self.step}. RENAMING ALBUMS FOLDERS BASED ON THEIR DATES...")
                LOGGER.info("============================================================")
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Renaming albums folders in <OUTPUT_TAKEOUT_FOLDER> based on their dates...")
                step_start_time = datetime.now()
                result_rename = rename_album_folders(input_folder=album_folder, exclude_subfolder=['No-Albums', '@eaDir'], step_name=step_name, log_level=logging.INFO)
                # Merge all counts from result_rename into result in one go
                result.update(result_rename)

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 11: Renamove Empty Folders
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '[POST]-[Remove Empty Folders] : '
            self.step += 1
            LOGGER.info("")
            LOGGER.info("======================================")
            LOGGER.info(f"INFO    : {self.step}. REMOVING EMPTY FOLDERS...")
            LOGGER.info("======================================")
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Removing empty folders in <OUTPUT_TAKEOUT_FOLDER>...")
            step_start_time = datetime.now()
            Utils.remove_empty_dirs(input_folder=output_takeout_folder, log_level=logging.INFO)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # Step 11: Count Albums
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '[POST]-[Counting Albums] : '
            self.step += 1
            LOGGER.info("")
            LOGGER.info("==========================================")
            LOGGER.info(f"INFO    : {self.step}. COUNTING ALBUMS AND FILES...")
            LOGGER.info("==========================================")
            LOGGER.info("")
            # 1. First count all Files in output Folder
            # New function to count all file types and extract also date info
            output_counters = Utils.count_files_per_type_and_date(input_folder=output_takeout_folder, within_json_sidecar=False, log_level=log_level)
            # Clean input dict
            result['output_counters'].clear()
            # Assign all pairs key-value from output_counters to counter['output_counters'] dict
            result['output_counters'].update(output_counters)

            # 2. Now count the Albums in output Folder
            if os.path.isdir(output_takeout_folder):
                excluded_folders = ["No-Albums", "ALL_PHOTOS"]
                result['valid_albums_found'] = Utils.count_valid_albums(album_folder, excluded_folders=excluded_folders, step_name=step_name)
            LOGGER.info(f"INFO    : {step_name}Valid Albums Found {result['valid_albums_found']}.")
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : {step_name}Step {self.step} completed in {formatted_duration}.")


            # FINISH
            # ----------------------------------------------------------------------------------------------------------------------
            processing_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(processing_end_time - processing_start_time).seconds))
            LOGGER.info("")
            LOGGER.info("============================================================================================================================")
            LOGGER.info(f"INFO    : ✅ TAKEOUT PROCESSING FINISHED!!!")
            LOGGER.info(f"INFO    : Takeout Precessed Folder: '{output_takeout_folder}'.")
            LOGGER.info("")
            LOGGER.info(f"INFO    : Total Processing Time   :  {formatted_duration}.")
            LOGGER.info("============================================================================================================================")

            # At the end of the process, we call the super() to make this objet a sub-instance of the class ClassLocalFolder to create the same folder structure
            if create_localfolder_object:
                super().__init__(output_takeout_folder)

            return result



    # sobreescribimos el método get_takeout_assets_by_filters() para que obtenga los assets de takeout_folder directamente en lugar de base_folder, para poder hacer el recuento de metadatos, sidecar, y archivos no soportados.
    def get_takeout_assets_by_filters(self, type='all', log_level=logging.INFO):
        """
        Retrieves assets stored in the base folder, filtering by type.

        Args:
            log_level (int): Logging level.
            type (str): Type of assets to retrieve. Options are 'all', 'photo', 'image', 'video', 'media', 'metadata', 'sidecar', 'unsupported'.

        Returns:
            list[dict]: A list of asset dictionaries, each containing:
                        - 'id': Absolute path to the file.
                        - 'time': Creation timestamp of the file.
                        - 'filename': File name (no path).
                        - 'filepath': Absolute path to the file.
                        - 'type': Type of the file (image, video, metadata, sidecar, unknown).
        """
        with set_log_level(LOGGER, log_level):
            if self.unzipped_folder:
                base_folder = self.unzipped_folder
            else:
                base_folder = self.takeout_folder

            LOGGER.info(f"INFO    : Retrieving {type} assets from the base folder: '{base_folder}'.")

            # Determine allowed extensions based on the type
            if type in ['photo', 'image']:
                selected_type_extensions = self.ALLOWED_PHOTO_EXTENSIONS
            elif type == 'video':
                selected_type_extensions = self.ALLOWED_VIDEO_EXTENSIONS
            elif type == 'media':
                selected_type_extensions = self.ALLOWED_MEDIA_EXTENSIONS
            elif type == 'metadata':
                selected_type_extensions = self.ALLOWED_METADATA_EXTENSIONS
            elif type == 'sidecar':
                selected_type_extensions = self.ALLOWED_SIDECAR_EXTENSIONS
            elif type == 'unsupported':
                selected_type_extensions = None  # Special case to filter unsupported files
            else:  # 'all' or unrecognized type defaults to all supported extensions
                selected_type_extensions = self.ALLOWED_EXTENSIONS

            assets = [
                {
                    "id": str(file.resolve()),
                    "time": file.stat().st_ctime,
                    "filename": file.name,
                    "filepath": str(file.resolve()),
                    "type": self._determine_file_type(file),
                }
                for file in base_folder.rglob("*")
                if file.is_file() and (
                    (selected_type_extensions is None and file.suffix.lower() not in self.ALLOWED_EXTENSIONS) or
                    (selected_type_extensions is not None and file.suffix.lower() in selected_type_extensions)
                )
            ]

            LOGGER.info(f"INFO    : Found {len(assets)} {type} assets in the base folder.")
            return assets
##############################################################################
#                                END OF CLASS                                #
##############################################################################

##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
# Example main usage
if __name__ == "__main__":
    import sys
    from ChangeWrkingDir import change_workingdir
    change_workingdir()

    input_folder = Path(r"r:\jaimetur\PhotoMigrator\Takeout")
    # timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # base_folder = input_folder.parent / f"Takeout_processed_{timestamp}"

    takeout = ClassTakeoutFolder(input_folder)
    result = takeout.process("Output_Takeout_Folder", capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=False, log_level=logging.DEBUG)
    print(result)
