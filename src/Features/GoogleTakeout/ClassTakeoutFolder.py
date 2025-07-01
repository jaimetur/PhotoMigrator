# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-
import fnmatch
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import zipfile
from datetime import datetime, timedelta
from os.path import dirname, basename
from pathlib import Path

from colorama import init

from Core.CustomLogger import set_log_level, custom_print
from Core.FileStatistics import count_files_and_extract_dates
from Core.GlobalVariables import ARGS, LOG_LEVEL, LOGGER, START_TIME, FOLDERNAME_ALBUMS, FOLDERNAME_NO_ALBUMS, TIMESTAMP, SUPPLEMENTAL_METADATA, MSG_TAGS, SPECIAL_SUFFIXES, EDITTED_SUFFIXES, PHOTO_EXT, VIDEO_EXT
from Features.GoogleTakeout import MetadataFixers
# Import ClassLocalFolder (Parent Class of this)
from Features.LocalFolder.ClassLocalFolder import ClassLocalFolder
from Features.StandAlone.AutoRenameAlbumsFolders import rename_album_folders
from Features.StandAlone.Duplicates import find_duplicates
from Features.StandAlone.FixSymLinks import fix_symlinks_broken
from Utils.FileUtils import delete_subfolders, remove_empty_dirs, is_valid_path
from Utils.GeneralUtils import print_dict_pretty, tqdm
from Utils.StandaloneUtils import change_working_dir


##############################################################################
#                              START OF CLASS                                #
##############################################################################
class ClassTakeoutFolder(ClassLocalFolder):
    def __init__(self, takeout_folder):
        """
        Inicializa la clase con la carpeta base (donde se guardan los archivos ya procesados)
        y la carpeta de entrada (donde se encuentran los archivos sin procesar).
        """
        from Core.GlobalVariables import ARGS, TIMESTAMP, DEPRIORITIZE_FOLDERS_PATTERNS
        from Core.DataModels import init_process_results

        self.ARGS = ARGS
        self.TIMESTAMP = TIMESTAMP
        self.DEPRIORITIZE_FOLDERS_PATTERNS = DEPRIORITIZE_FOLDERS_PATTERNS
        self.log_level = logging.INFO

        # # Create atributes from the ARGS given:
        # self.skip_gpth                      = self.ARGS['google-skip-gpth-tool']
        # self.ignore_takeout_structure       = self.ARGS['google-ignore-check-structure']

        # Assign takeout_folder from the given argument when create the object
        self.takeout_folder = Path(takeout_folder)  # Folder given when create the object
        self.takeout_folder.mkdir(parents=True, exist_ok=True)  # Asegurar que takeout_folder existe

        # Verificar si la carpeta necesita ser descomprimida
        self.needs_unzip = self.check_if_needs_unzip(log_level=logging.WARNING)
        self.unzipped_folder = None # Only will have value if the Takeout have been already unzipped

        # Backup_folder in case of needed
        self.backup_takeout_folder = None

        # Verificar si la carpeta necesita ser procesada
        self.needs_process = self.check_if_needs_process(log_level=logging.WARNING)

        # Set input_folder as the input for the Preprocessing and Processing Phases
        self.input_folder = self.get_input_folder()

        # Initiate the output_folder
        self.output_folder = self.get_output_folder()

        # Set Albums Folder
        self.albums_folder = self.get_albums_folder()

        # Contador de pasos durante el procesamiento
        self.step = 0
        self.substep = 0

        # Create steps_duration list
        self.steps_duration = []

        # Create and init self.result dict
        self.result = init_process_results()

        self.CLIENT_NAME = f'Google Takeout Folder ({self.takeout_folder.name})'

#---------------------------------------------- CLASS METHODS ----------------------------------------------
    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_process(self, log_level=None):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return contains_takeout_structure(input_folder=self.takeout_folder, log_level=log_level)

    # @staticmethod # if use this flag, the method is static and no need to include self in the arguments
    def check_if_needs_unzip(self, log_level=None):
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            for file in os.listdir(self.takeout_folder):
                if file.endswith('.zip'):
                    return True
            return False

    def get_input_folder(self):
        if self.unzipped_folder:
            self.input_folder = self.unzipped_folder
        else:
            self.input_folder = self.takeout_folder
        return self.input_folder

    def get_albums_folder(self):
        if not self.ARGS['google-skip-move-albums']:
            self.albums_folder = os.path.join(self.output_folder, FOLDERNAME_ALBUMS)
        else:
            self.albums_folder = self.output_folder
        return self.albums_folder

    def get_output_folder(self):
        if self.needs_process or self.ARGS['google-ignore-check-structure']:
            if self.ARGS['output-folder']:
                self.output_folder = Path(self.ARGS['output-folder'])
            else:
                self.output_folder = Path(f"{self.takeout_folder}_{self.ARGS['google-output-folder-suffix']}_{self.TIMESTAMP}")
        else:
            self.output_folder = self.takeout_folder
        # Call get_albums_folder to update it with the new output_folder
        self.get_albums_folder()
        return self.output_folder


    def precheck_takeout_and_calculate_initial_counters(self, log_level=None):
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            # Start Pre-Checking
            self.step += 1
            self.substep = 0
            step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"=============================================")
            LOGGER.info(f"{self.step}. PRE-CHECKING TAKEOUT FOLDER...  ")
            LOGGER.info(f"=============================================")
            LOGGER.info(f"")

            # Sub-Step 1: Extraction Process
            # ----------------------------------------------------------------------------------------------------------------------
            if self.needs_unzip:
                step_name = '🔍 [PRE-CHECKS]-[Unzip Takeout] : '
                self.substep += 1
                sub_step_start_time = datetime.now()
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}📦 Input Folder contains ZIP files and needs to be unzipped first.")
                LOGGER.info(f"{step_name}📦 This process might take long time, depending on how big is your Takeout.")
                LOGGER.info(f"{step_name}📦 Unzipping Takeout Folder...Be patient... 🙂")
                # Make the 'Unzipped' folder as the new takeout_folder for the object
                self.unzipped_folder= Path(f"{self.takeout_folder}_unzipped_{self.TIMESTAMP}")
                # Unzip the files into unzip_folder
                unpack_zips(input_folder=self.takeout_folder, unzip_folder=self.unzipped_folder, step_name=step_name, log_level=self.log_level)
                # Update input_folder to take the new unzipped folder as reference
                self.input_folder = self.unzipped_folder
                # Change flag self.check_if_needs_unzip to False
                self.needs_unzip = False
                self.needs_process = contains_takeout_structure(input_folder=self.input_folder, step_name=step_name)
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Sub-Step 2: create_backup_if_needed
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS.get('google-keep-takeout-folder'):
                # Determine the input_folder depending if the Takeout have been unzipped or not
                input_folder = self.get_input_folder()
                step_name = '🔍 [PRE-CHECKS]-[Clone Takeout] : '
                self.substep += 1
                sub_step_start_time = datetime.now()
                LOGGER.info(f"")
                LOGGER.warning(f"{step_name}Flag '-gKeepTkout, --google-keep-takeout-folder' detected. Cloning Takeout Folder...")
                # Generate the target temporary folder path
                parent_dir = dirname(self.takeout_folder)
                folder_name = basename(self.takeout_folder)
                cloned_folder = os.path.join(parent_dir, f"{folder_name}_tmp_{TIMESTAMP}")
                # Call the cloning function
                tmp_folder = clone_folder_fast (input_folder=self.input_folder, cloned_folder=cloned_folder, step_name=step_name, log_level=log_level)
                if tmp_folder != self.input_folder:
                    ARGS['google-takeout'] = tmp_folder
                    self.unzipped_folder = tmp_folder
                    self.backup_takeout_folder = input_folder
                    LOGGER.info(f"{step_name}Takeout folder cloned successfully and will be used as working folder for next steps. ")
                    LOGGER.info(f"{step_name}Your original Takeout files have been safely preserved in the folder: '{self.backup_takeout_folder}' ")
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 3: Count initial files in Takeout Folder before to process with GPTH and modify any original file
            # ----------------------------------------------------------------------------------------------------------------------
            # Determine the input_folder depending if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()
            step_name = '🔍 [PRE-CHECKS]-[Count Files  ] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Counting files in Takeout Folder: {input_folder}...")
            # New function to count all file types and extract also date info
            initial_takeout_counters, dates = count_files_and_extract_dates(input_folder=input_folder, output_file=f"input_dates_metadata.json", step_name=step_name, log_level=LOG_LEVEL)
            # Clean input dict
            self.result['input_counters'].clear()
            # Assign all pairs key-value from initial_takeout_counters to counter['input_counters'] dict
            self.result['input_counters'].update(initial_takeout_counters)
            LOGGER.info(f"{step_name}Counting Files finished!")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"{step_name}Total Files in Takeout folder                    : {self.result['input_counters']['total_files']:<7}")
            LOGGER.info(f"{step_name}Total Non-Supported files in Takeout folder      : {self.result['input_counters']['unsupported_files']:<7}")
            LOGGER.info(f"{step_name}Total Supported files in Takeout folder          : {self.result['input_counters']['supported_files']:<7}")
            LOGGER.info(f"{step_name}  - Total Non-Media files in Takeout folder      : {self.result['input_counters']['non_media_files']:<7}")
            LOGGER.info(f"{step_name}    - Total Metadata in Takeout folder           : {self.result['input_counters']['metadata_files']:<7}")
            LOGGER.info(f"{step_name}    - Total Sidecars in Takeout folder           : {self.result['input_counters']['sidecar_files']:<7}")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"{step_name}  - Total Media files in Takeout folder          : {self.result['input_counters']['media_files']:<7}")
            LOGGER.info(f"{step_name}    - Total Photos in Takeout folder             : {self.result['input_counters']['photo_files']:<7}")
            LOGGER.info(f"{step_name}      - Correct Date                             : {self.result['input_counters']['photos']['with_date']:<7} ({self.result['input_counters']['photos']['pct_with_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"{step_name}      - Incorrect Date                           : {self.result['input_counters']['photos']['without_date']:<7} ({self.result['input_counters']['photos']['pct_without_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"{step_name}    - Total Videos in Takeout folder             : {self.result['input_counters']['video_files']:<7}")
            LOGGER.info(f"{step_name}      - Correct Date                             : {self.result['input_counters']['videos']['with_date']:<7} ({self.result['input_counters']['videos']['pct_with_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"{step_name}      - Incorrect Date                           : {self.result['input_counters']['videos']['without_date']:<7} ({self.result['input_counters']['videos']['pct_without_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})


            # Finally show TOTAL DURATION OF PRE-CHECKS PHASE
            step_name = '🔍 [PRE-CHECKS] : '
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})

            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '- TOTAL DURATION', 'duration': formatted_duration})


    def preprocess(self, log_level=None):
        # Start Pre-Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            self.step += 1
            self.substep = 0
            step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"=============================================")
            LOGGER.info(f"{self.step}. PRE-PROCESSING TAKEOUT FOLDER...")
            LOGGER.info(f"=============================================")
            LOGGER.info(f"")

            # Determine the input_folder deppending if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()

            # Sub-Step 1: Delete hidden subfolders '@eaDir'
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[Clean Takeout Folder] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Cleaning hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
            delete_subfolders(input_folder=input_folder, folder_name_to_delete="@eaDir", step_name=step_name, log_level=LOG_LEVEL)
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 2: Fix .MP4 JSON
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[MP4/Live Pics. Fixer] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
            total_mp4_files_fixed = fix_mp4_files(input_folder=input_folder, step_name=step_name, log_level=LOG_LEVEL)
            LOGGER.info(f"{step_name}Fixing MP4 from live pictures metadata finished!")
            LOGGER.info(f"{step_name}Total MP4 from live pictures Files fixed         : {total_mp4_files_fixed}")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Sub-Step 3: Fix truncated suffixes (such as '-ha edit.jpg' or '-ha e.jpg', or '-effec', or '-supplemen',...)
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🪛 [PRE-PROCESS]-[Truncations Fixer   ] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Fixing Truncated Special Suffixes from Google Photos and rename files to include complete special suffix...")
            fix_truncations_output = fix_truncations(input_folder=input_folder, step_name=step_name, log_level=LOG_LEVEL)

            # Clean input dict
            self.result['fix_truncations'].clear()
            # Assign all pairs key-value from output_counters to counter['output_counters'] dict
            self.result['fix_truncations'].update(fix_truncations_output)

            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Fixing Truncated Files finished!")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            LOGGER.info(f"{step_name}Total Files files in Takeout folder              : {fix_truncations_output['total_files']}")
            LOGGER.info(f"{step_name}  - Total Fixed Files files in Takeout folder    : {total_mp4_files_fixed + fix_truncations_output['total_files_fixed']:<7}")
            LOGGER.info(f"{step_name}    - Total MP4 from live pictures Files fixed   : {total_mp4_files_fixed:<7}")
            LOGGER.info(f"{step_name}    - Total Truncated files fixed                : {fix_truncations_output['total_files_fixed']:<7}")
            LOGGER.info(f"{step_name}      - Total JSON files fixed                   : {fix_truncations_output['json_files_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Supplemental-metadata changes          : {fix_truncations_output['supplemental_metadata_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Extensions changes                     : {fix_truncations_output['extensions_fixed']:<7}")
            LOGGER.info(f"{step_name}      - Total Images/Videos files fixed          : {fix_truncations_output['non_json_files_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Special Suffixes changes               : {fix_truncations_output['special_suffixes_fixed']:<7}")
            LOGGER.info(f"{step_name}        - Edited Suffixes changes                : {fix_truncations_output['edited_suffixes_fixed']:<7}")
            LOGGER.info(f"{step_name}-----------------------------------------------------------------------------------")
            sub_step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
            LOGGER.info(f"")
            step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
            LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})

            # Finally show TOTAL DURATION OF PRE-PROCESS PHASE
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            step_name = '🪛 [PRE-PROCESS] : '
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            # Índice self.substep posiciones antes del final
            idx = len(self.steps_duration) - self.substep
            if idx < 0:  idx = 0  # si la lista tiene menos de self.substep elementos, lo ponemos al inicio
            # Insertamos ahí el nuevo registro (sin sobrescribir ninguno)
            self.steps_duration.insert(idx, {'step_id': self.step, 'step_name': step_name + '- TOTAL DURATION', 'duration': formatted_duration})

    def process(self, output_folder=None, capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=True, log_level=None):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        process() function, but uses LOGGER and self.ARGS instead of global.
        """
        # Start the Process
        with (set_log_level(LOGGER, log_level)):  # Temporarily adjust log level
            LOGGER.info(f"")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"🔢 TAKEOUT PROCESSING STARTED...")
            LOGGER.info(f"==========================================")
            processing_start_time = datetime.now()

            if capture_output is None: capture_output=self.ARGS['show-gpth-info']
            if capture_errors is None: capture_errors=self.ARGS['show-gpth-errors']

            # Step 1: Pre-check the object with skip_process=True to just unzip files in case they are zipped
            # ----------------------------------------------------------------------------------------------------------------------
            self.precheck_takeout_and_calculate_initial_counters(log_level=log_level)

            # Step 2: Pre-Process Takeout folder
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-skip-preprocess']:
                # Call preprocess() with the same log_level as process()
                self.preprocess(log_level=log_level)

            # Step 3: Process photos with GPTH tool
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-skip-gpth-tool']:
                step_name = '🧠 [PROCESS]-[Metadata Processing] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"=====================================================")
                LOGGER.info(f"{self.step}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
                LOGGER.info(f"=====================================================")
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")

                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"{step_name}Google Takeout Structure detected ('-gics, --google-ignore-check-structure' flag detected).")
                else:
                    if not self.needs_process:
                        LOGGER.warning(f"{step_name}No Takeout structure detected in input folder. The tool will process the folder ignoring Takeout structure.")
                        self.ARGS['google-ignore-check-structure'] = True

                # --------------------------------------------------------------------------------------------------------------------------------------------------------
                # DETERMINE BASIC FOLDERS AND INIT SUPER CLASS
                # This need to be done after Pre-checks because if takeout folders have been unzipped, the input_folder, output_folder and albums_folder need to be updated
                # --------------------------------------------------------------------------------------------------------------------------------------------------------
                # If the user have passed an output_folder directly to the process() method, then update the object with this output_folder
                if output_folder:
                    self.output_folder = output_folder
                # Determine the output_folder if it has not been given in the call to process() method
                output_folder = self.get_output_folder()
                # Determine the input_folder depending on if the Takeout have been unzipped or not
                input_folder = self.get_input_folder()
                # Determine where the Albums will be located
                albums_folder = self.get_albums_folder()

                # Now Call GPTH Tool
                ok = MetadataFixers.fix_metadata_with_gpth_tool(
                    input_folder=self.input_folder,
                    output_folder=output_folder,
                    capture_output=capture_output,
                    capture_errors=capture_errors,
                    print_messages=print_messages,
                    no_symbolic_albums=self.ARGS['google-no-symbolic-albums'],
                    skip_extras=self.ARGS['google-skip-extras-files'],
                    keep_takeout_folder=self.ARGS['google-keep-takeout-folder'],
                    ignore_takeout_structure=self.ARGS['google-ignore-check-structure'],
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                if not ok:
                    LOGGER.warning(f"{step_name}Metadata fixing didn't finish properly due to GPTH error.")
                    LOGGER.warning(f"{step_name}If your Takeout does not contains Year/Month folder structure, you can use '-gics, --google-ignore-check-structure' flag.")
                    return self.result

                # Determine if manual copy/move is needed (for step 4)
                manual_copy_move_needed = self.ARGS['google-skip-gpth-tool'] or self.ARGS['google-ignore-check-structure']
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 4: Copy/Move files to output folder manually
            # ----------------------------------------------------------------------------------------------------------------------
            if manual_copy_move_needed:
                step_name = '📁 [POST-PROCESS]-[Copy/Move] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"======================================================")
                LOGGER.info(f"{self.step}. COPYING/MOVING FILES TO OUTPUT FOLDER...")
                LOGGER.info(f"======================================================")
                LOGGER.info(f"")
                if self.ARGS['google-skip-gpth-tool']:
                    LOGGER.warning(f"{step_name}Metadata fixing with GPTH tool skipped ('-gsgt, --google-skip-gpth-tool' flag). step {self.step} is needed to copy files manually to output folder.")
                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"{step_name}Flag to Ignore Google Takeout Structure detected. step {self.step} is needed to copy/move files manually to output folder.")
                if not self.ARGS['google-keep-takeout-folder']:
                    LOGGER.info(f"{step_name}Moving files from Takeout folder to Output folder...")
                else:
                    LOGGER.info(f"{step_name}Copying files from Takeout folder to Output folder...")
                copy_move_folder(input_folder, output_folder, ignore_patterns=['*.json', '*.j'], move=not self.ARGS['google-keep-takeout-folder'], step_name=step_name, log_level=LOG_LEVEL)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 5: Sync .MP4 live pictures timestamp
            # ----------------------------------------------------------------------------------------------------------------------
            self.step += 1
            step_name = '🕒 [POST-PROCESS]-[MP4 Timestamp Synch] : '
            step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"========================================================================")
            LOGGER.info(f"{self.step}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
            LOGGER.info(f"========================================================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
            sync_mp4_timestamps_with_images(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 6: Create Folders Year/Month or Year only structure
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-albums-folders-structure'].lower() != 'flatten' or self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten' or (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                step_name = '📁 [POST-PROCESS]-[Create year/month struct] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"====================================================")
                LOGGER.info(f"{self.step}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
                LOGGER.info(f"====================================================")
                # For Albums
                if self.ARGS['google-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Creating Folder structure '{self.ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
                    basedir = output_folder
                    type_structure = self.ARGS['google-albums-folders-structure']
                    exclude_subfolders = [FOLDERNAME_NO_ALBUMS]
                    organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders, step_name=step_name, log_level=LOG_LEVEL)

                # For No-Albums
                if self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info(f"")
                    LOGGER.info(f"{step_name}Creating Folder structure '{self.ARGS['google-no-albums-folders-structure'].lower()}' for '{FOLDERNAME_NO_ALBUMS}' folder...")
                    basedir = os.path.join(output_folder, FOLDERNAME_NO_ALBUMS)
                    type_structure = self.ARGS['google-no-albums-folders-structure']
                    exclude_subfolders = []
                    organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders, step_name=step_name, log_level=LOG_LEVEL)

                # If flatten
                if (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                    LOGGER.info(f"")
                    LOGGER.warning(f"{step_name}No argument '-gafs, --google-albums-folders-structure' and '-gnas, --google-no-albums-folders-structure' detected. All photos and videos will be flattened in their folders.")

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 7: Move albums
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-skip-move-albums']:
                step_name = '📚 [POST-PROCESS]-[Move Albums] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"====================================")
                LOGGER.info(f"{self.step}. MOVING ALBUMS FOLDER...")
                LOGGER.info(f"====================================")
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Moving All your albums into '{FOLDERNAME_ALBUMS}' subfolder for a better organization...")
                move_albums(input_folder=output_folder, exclude_subfolder=[FOLDERNAME_NO_ALBUMS, '@eaDir'], step_name=step_name, log_level=LOG_LEVEL)
                step_end_time = datetime.now()
                LOGGER.info(f"{step_name}All your albums have been moved successfully!")
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 8: Remove Duplicates
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-remove-duplicates-files']:
                step_name = '👥 [POST-PROCESS]-[Remove Duplicates] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"==============================================================")
                LOGGER.info(f"{self.step}. REMOVING DUPLICATES IN <OUTPUT_TAKEOUT_FOLDER>...")
                LOGGER.info(f"==============================================================")
                LOGGER.info(f"")

                # First Remove Duplicates from OUTPUT_TAKEOUT_FOLDER (excluding '<NO_ALBUMS_FOLDER>' folder)
                LOGGER.info(f"{step_name}1. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>', excluding '<NO_ALBUMS_FOLDER>' folder...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=output_folder,
                    exclusion_folders=[FOLDERNAME_NO_ALBUMS],    # Exclude '<NO_ALBUMS_FOLDER>' folder since it will contain duplicates of all the assets within 'Albums' subfolders.
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                self.result['duplicates_found'] += duplicates_found
                self.result['removed_empty_folders'] += removed_empty_folders

                # Second Remove Duplicates from <OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER> (excluding any other folder outside it).
                LOGGER.info(f"{step_name}2. Removing duplicates from '<OUTPUT_TAKEOUT_FOLDER>/<NO_ALBUMS_FOLDER>', excluding any other folders outside it...")
                duplicates_found, removed_empty_folders = find_duplicates(
                    duplicates_action='remove',
                    duplicates_folders=os.path.join(output_folder, FOLDERNAME_NO_ALBUMS),
                    deprioritize_folders_patterns=self.DEPRIORITIZE_FOLDERS_PATTERNS,
                    timestamp=self.TIMESTAMP,
                    step_name=step_name,
                    log_level=LOG_LEVEL
                )
                self.result['duplicates_found'] += duplicates_found
                self.result['removed_empty_folders'] += removed_empty_folders

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 9: Fix Broken Symbolic Links
            # ----------------------------------------------------------------------------------------------------------------------
            if not self.ARGS['google-no-symbolic-albums']:
                step_name = '🔗 [POST-PROCESS]-[Fix Symlinks] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"=========================================================")
                LOGGER.info(f"{self.step}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
                LOGGER.info(f"=========================================================")
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                self.result['symlink_fixed'], self.result['symlink_not_fixed'] = fix_symlinks_broken(input_folder=output_folder, step_name=step_name, log_level=LOG_LEVEL)

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 10: Rename Albums Folders based on content date
            # ----------------------------------------------------------------------------------------------------------------------
            if self.ARGS['google-rename-albums-folders']:
                step_name = '📝 [POST-PROCESS]-[Album Renaming] : '
                step_start_time = datetime.now()
                self.step += 1
                LOGGER.info(f"")
                LOGGER.info(f"============================================================")
                LOGGER.info(f"{self.step}. RENAMING ALBUMS FOLDERS BASED ON THEIR DATES...")
                LOGGER.info(f"============================================================")
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Renaming albums folders in <OUTPUT_TAKEOUT_FOLDER> based on their dates...")
                rename_output = rename_album_folders(input_folder=albums_folder, exclude_subfolder=[FOLDERNAME_NO_ALBUMS, '@eaDir'], step_name=step_name, log_level=LOG_LEVEL)
                # Merge all counts from rename_output into self.result in one go
                self.result.update(rename_output)

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 11: Remove Empty Folders
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🧹 [POST-PROCESS]-[Remove Empty Folders] : '
            step_start_time = datetime.now()
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"======================================")
            LOGGER.info(f"{self.step}. REMOVING EMPTY FOLDERS...")
            LOGGER.info(f"======================================")
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Removing empty folders in <OUTPUT_TAKEOUT_FOLDER>...")
            remove_empty_dirs(input_folder=output_folder, log_level=LOG_LEVEL)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})


            # Step 12: Count Albums
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🔢 [POST-PROCESS]-[Count Files & Albums] : '
            step_start_time = datetime.now()
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"{self.step}. COUNTING FILES AND ALBUMS... ")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"")

            # 1. First count all Files in output Folder
            output_counters, dates = count_files_and_extract_dates(input_folder=output_folder, output_file=f"output_dates_metadata.json", step_name=step_name, log_level=LOG_LEVEL)

            # Clean input dict
            self.result['output_counters'].clear()
            # Assign all pairs key-value from output_counters to counter['output_counters'] dict
            self.result['output_counters'].update(output_counters)

            # 2. Now count the Albums in output Folder
            if os.path.isdir(albums_folder):
                excluded_folders = [FOLDERNAME_NO_ALBUMS, "ALL_PHOTOS"]
                self.result['valid_albums_found'] = count_valid_albums(albums_folder, excluded_folders=excluded_folders, step_name=step_name, log_level=LOG_LEVEL)
            LOGGER.info(f"{step_name}Valid Albums Found {self.result['valid_albums_found']}.")
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})

            # Step 13: FINAL CLEANING
            # ----------------------------------------------------------------------------------------------------------------------
            step_name = '🧹 [FINAL-CLEANING] : '
            step_start_time = datetime.now()
            self.step += 1
            LOGGER.info(f"")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"{self.step}. FINAL CLEANING... ")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"")
            # Removes completely the input_folder because all the files (except JSON) have been already moved to output folder
            removed = force_remove_directory(folder=input_folder, step_name=step_name, log_level=logging.ERROR)
            if removed:
                LOGGER.info(f"{step_name}The folder '{input_folder}' have been successfully deleted.")
            else:
                LOGGER.info(f"{step_name}Nothing to Clean. The folder '{input_folder}' have been already deleted by a previous step.")
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((step_end_time - step_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Step {self.step} completed in {formatted_duration}.")
            self.steps_duration.append({'step_id': self.step, 'step_name': step_name, 'duration': formatted_duration})

            # FINISH
            # ----------------------------------------------------------------------------------------------------------------------
            processing_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((processing_end_time - processing_start_time).total_seconds())))
            LOGGER.info(f"")
            LOGGER.info(f"============================================================================================================================")
            LOGGER.info(f"✅ TAKEOUT PROCESSING FINISHED!!!")
            LOGGER.info(f"{'Takeout Precessed Folder'.ljust(55)}  : '{output_folder}'.")
            LOGGER.info(f"")
            LOGGER.info(f"Processing Time per Step:")
            for entry in self.steps_duration:
                label_cleaned = ' '.join(entry['step_name'].replace(' : ', '').split()).replace(' ]', ']')
                step_id_and_label = f"Step {(str(entry['step_id'])).ljust(4)} : {label_cleaned}"
                LOGGER.info(f"{step_id_and_label.ljust(55)} : {entry['duration'].rjust(8)}")
            LOGGER.info(f"")
            LOGGER.info(f"{'TOTAL PROCESSING TIME'.ljust(55)}  : {formatted_duration.rjust(8)}")
            LOGGER.info(f"============================================================================================================================")

            # PRINT RESULTS
            # ----------------------------------------------------------------------------------------------------------------------
            result = self.result
            if LOG_LEVEL == logging.VERBOSE:
                LOGGER.verbose (f"Process Output:")
                print_dict_pretty(result, log_level=logging.VERBOSE)

            # Extract percentages of totals
            output_perc_photos_with_date = result['output_counters']['photos']['pct_with_date']
            output_perc_photos_without_date = result['output_counters']['photos']['pct_without_date']
            output_perc_videos_with_date = result['output_counters']['videos']['pct_with_date']
            output_perc_videos_without_date = result['output_counters']['videos']['pct_without_date']

            # Calculate percentages from output vs input
            perc_of_input_total_files               = 100 * result['output_counters']['total_files']           / result['input_counters']['total_files']             if result['input_counters']['total_files']           != 0 else 100
            perc_of_input_total_unsupported_files   = 100 * result['output_counters']['unsupported_files']     / result['input_counters']['unsupported_files']       if result['input_counters']['unsupported_files']     != 0 else 100
            perc_of_input_total_supported_files     = 100 * result['output_counters']['supported_files']       / result['input_counters']['supported_files']         if result['input_counters']['supported_files']       != 0 else 100
            perc_of_input_total_media               = 100 * result['output_counters']['media_files']           / result['input_counters']['media_files']             if result['input_counters']['media_files']           != 0 else 100
            perc_of_input_total_images              = 100 * result['output_counters']['photo_files']           / result['input_counters']['photo_files']             if result['input_counters']['photo_files']           != 0 else 100
            perc_of_input_total_photos_with_date    = 100 * result['output_counters']['photos']['with_date']   / result['input_counters']['photos']['with_date']     if result['input_counters']['photos']['with_date']   != 0 else 100
            perc_of_input_total_photos_without_date = 100 * result['output_counters']['photos']['without_date']/ result['input_counters']['photos']['without_date']  if result['input_counters']['photos']['without_date']!= 0 else 100
            perc_of_input_total_videos              = 100 * result['output_counters']['video_files']           / result['input_counters']['video_files']             if result['input_counters']['video_files']           != 0 else 100
            perc_of_input_total_videos_with_date    = 100 * result['output_counters']['videos']['with_date']   / result['input_counters']['videos']['with_date']     if result['input_counters']['videos']['with_date']   != 0 else 100
            perc_of_input_total_videos_without_date = 100 * result['output_counters']['videos']['without_date']/ result['input_counters']['videos']['without_date']  if result['input_counters']['videos']['without_date']!= 0 else 100
            perc_of_input_total_non_media           = 100 * result['output_counters']['non_media_files']       / result['input_counters']['non_media_files']         if result['input_counters']['non_media_files']       != 0 else 100
            perc_of_input_total_metadata            = 100 * result['output_counters']['metadata_files']        / result['input_counters']['metadata_files']          if result['input_counters']['metadata_files']        != 0 else 100
            perc_of_input_total_sidecars            = 100 * result['output_counters']['sidecar_files']         / result['input_counters']['sidecar_files']           if result['input_counters']['sidecar_files']         != 0 else 100

            # Calculate differences from output vs input
            diff_output_input_total_files               = result['output_counters']['total_files']           - result['input_counters']['total_files']
            diff_output_input_total_unsupported_files   = result['output_counters']['unsupported_files']     - result['input_counters']['unsupported_files']
            diff_output_input_total_supported_files     = result['output_counters']['supported_files']       - result['input_counters']['supported_files']          
            diff_output_input_total_media               = result['output_counters']['media_files']           - result['input_counters']['media_files']
            diff_output_input_total_images              = result['output_counters']['photo_files']           - result['input_counters']['photo_files']
            diff_output_input_total_photos_with_date    = result['output_counters']['photos']['with_date']   - result['input_counters']['photos']['with_date']
            diff_output_input_total_photos_without_date = result['output_counters']['photos']['without_date']- result['input_counters']['photos']['without_date']   
            diff_output_input_total_videos              = result['output_counters']['video_files']           - result['input_counters']['video_files']
            diff_output_input_total_videos_with_date    = result['output_counters']['videos']['with_date']   - result['input_counters']['videos']['with_date']
            diff_output_input_total_videos_without_date = result['output_counters']['videos']['without_date']- result['input_counters']['videos']['without_date']
            diff_output_input_total_non_media           = result['output_counters']['non_media_files']       - result['input_counters']['non_media_files']
            diff_output_input_total_metadata            = result['output_counters']['metadata_files']        - result['input_counters']['metadata_files']
            diff_output_input_total_sidecars            = result['output_counters']['sidecar_files']         - result['input_counters']['sidecar_files']

            end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
            if result['output_counters']['total_files'] == 0:
                # FINAL SUMMARY
                LOGGER.info(f"")
                LOGGER.error(f"=====================================================")
                LOGGER.error(f"❌ PROCESS COMPLETED WITH ERRORS!           ")
                LOGGER.error(f"=====================================================")
                LOGGER.info(f"")
                LOGGER.error(f"No files found in Output Folder  : '{output_folder}'")
                LOGGER.info(f"")
                LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
                LOGGER.info(f"============================================================================================================================")
                LOGGER.info(f"")
            else:
                # FINAL SUMMARY
                LOGGER.info(f"")
                LOGGER.info(f"============================================================================================================================")
                LOGGER.info(f"✅ PROCESS COMPLETED SUCCESSFULLY!")
                LOGGER.info(f"")
                LOGGER.info(f"Processed Takeout have been saved to folder : '{output_folder}'")
                if self.ARGS.get('google-keep-takeout-folder'):
                    LOGGER.info(f"Original Takeout is safely preserved in     : '{self.backup_takeout_folder}' ")
                else:
                    LOGGER.info(f"")
                LOGGER.info(f"")
                LOGGER.info(f"📊 FINAL SUMMARY & STATISTICS:")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"Total Size of Takeout folder                : {result['input_counters']['total_size_mb']:.1f} MB")
                LOGGER.info(f"Total Files in Takeout folder               : {result['input_counters']['total_files']:<7}")
                LOGGER.info(f"Total Non-Supported files in Takeout folder : {result['input_counters']['unsupported_files']:<7}")
                LOGGER.info(f"Total Supported files in Takeout folder     : {result['input_counters']['supported_files']:<7}")
                LOGGER.info(f"  - Total Non-Media files in Takeout folder : {result['input_counters']['non_media_files']:<7}")
                LOGGER.info(f"    - Total Metadata in Takeout folder      : {result['input_counters']['metadata_files']:<7}")
                LOGGER.info(f"    - Total Sidecars in Takeout folder      : {result['input_counters']['sidecar_files']:<7}")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"  - Total Media files in Takeout folder     : {result['input_counters']['media_files']:<7}")
                LOGGER.info(f"    - Total Photos in Takeout folder        : {result['input_counters']['photo_files']:<7}")
                LOGGER.info(f"      - Correct Date                        : {result['input_counters']['photos']['with_date']:<7}  ({result['input_counters']['photos']['pct_with_date']:>5.1f}% of total photos) ")
                LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['photos']['without_date']:<7}  ({result['input_counters']['photos']['pct_without_date']:>5.1f}% of total photos) ")
                LOGGER.info(f"    - Total Videos in Takeout folder        : {result['input_counters']['video_files']:<7}")
                LOGGER.info(f"      - Correct Date                        : {result['input_counters']['videos']['with_date']:<7}  ({result['input_counters']['videos']['pct_with_date']:>5.1f}% of total videos) ")
                LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['videos']['without_date']:<7}  ({result['input_counters']['videos']['pct_without_date']:>5.1f}% of total videos) ")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"Total Size of Output folder                 : {result['output_counters']['total_size_mb']:.1f} MB")
                LOGGER.info(f"Total Files in Output folder                : {result['output_counters']['total_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_files:>7})  |  ({perc_of_input_total_files:>5.1f}% of input) ")
                LOGGER.info(f"Total Non-Supported files in Output folder  : {result['output_counters']['unsupported_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_unsupported_files:>7})  |  ({perc_of_input_total_unsupported_files:>5.1f}% of input) ")
                LOGGER.info(f"Total Supported files in Output folder      : {result['output_counters']['supported_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_supported_files:>7})  |  ({perc_of_input_total_supported_files:>5.1f}% of input) ")
                LOGGER.info(f"  - Total Non-Media files in Output folder  : {result['output_counters']['non_media_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_non_media:>7})  |  ({perc_of_input_total_non_media:>5.1f}% of input) ")
                LOGGER.info(f"    - Total Metadata in Output folder       : {result['output_counters']['metadata_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_metadata:>7})  |  ({perc_of_input_total_metadata:>5.1f}% of input) ")
                LOGGER.info(f"    - Total Sidecars in Output folder       : {result['output_counters']['sidecar_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_sidecars:>7})  |  ({perc_of_input_total_sidecars:>5.1f}% of input) ")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"  - Total Media files in Output folder      : {result['output_counters']['media_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_media:>7})  |  ({perc_of_input_total_media:>5.1f}% of input) ")
                LOGGER.info(f"    - Total Photos in Output folder         : {result['output_counters']['photo_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_images:>7})  |  ({perc_of_input_total_images:>5.1f}% of input) ")
                LOGGER.info(f"      - Correct Date                        : {result['output_counters']['photos']['with_date']:<7}" f"   {f'({output_perc_photos_with_date:>5.1f}% of total photos)'.ljust(28)}" f"{f'|  (diff: {diff_output_input_total_photos_with_date:>7})  |  ({perc_of_input_total_photos_with_date:>5.1f}% of input)'.rjust(40)} ")
                LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['photos']['without_date']:<7}" f"   {f'({output_perc_photos_without_date:>5.1f}% of total photos)'.ljust(28)}" f"{f'|  (diff: {diff_output_input_total_photos_without_date:>7})  |  ({perc_of_input_total_photos_without_date:>5.1f}% of input)'.rjust(40)} ")
                LOGGER.info(f"    - Total Videos in Output folder         : {result['output_counters']['video_files']:<7} {''.ljust(28)}  |  (diff: {diff_output_input_total_videos:>7})  |  ({perc_of_input_total_videos:>5.1f}% of input) ")
                LOGGER.info(f"      - Correct Date                        : {result['output_counters']['videos']['with_date']:<7}" f"   {f'({output_perc_videos_with_date:>5.1f}% of total videos)'.ljust(28)}" f"{f'|  (diff: {diff_output_input_total_videos_with_date:>7})  |  ({perc_of_input_total_videos_with_date:>5.1f}% of input)'.rjust(40)} ")
                LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['videos']['without_date']:<7}" f"   {f'({output_perc_videos_without_date:>5.1f}% of total videos)'.ljust(28)}" f"{f'|  (diff: {diff_output_input_total_videos_without_date:>7})  |  ({perc_of_input_total_videos_without_date:>5.1f}% of input)'.rjust(40)} ")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"Total Albums folders found in Output folder : {result['valid_albums_found']}")
                if ARGS['google-rename-albums-folders']:
                    LOGGER.info(f"Total Albums Renamed                        : {result['renamed_album_folders']}")
                    LOGGER.info(f"Total Albums Duplicated                     : {result['duplicates_album_folders']}")
                    LOGGER.info(f"   - Total Albums Fully Merged              : {result['duplicates_albums_fully_merged']}")
                    LOGGER.info(f"   - Total Albums Not Fully Merged          : {result['duplicates_albums_not_fully_merged']}")
                if not ARGS['google-no-symbolic-albums']:
                    LOGGER.info(f"")
                    LOGGER.info(f"Total Symlinks Fixed                        : {result['symlink_fixed']}")
                    LOGGER.info(f"Total Symlinks Not Fixed                    : {result['symlink_not_fixed']}")
                if ARGS['google-remove-duplicates-files']:
                    LOGGER.info(f"")
                    LOGGER.info(f"Total Duplicates Removed                    : {result['duplicates_found']}")
                    LOGGER.info(f"Total Empty Folders Removed                 : {result['removed_empty_folders']}")
                LOGGER.info(f"")
                LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"============================================================================================================================")
                LOGGER.info(f"")



            # At the end of the process, we call the super() to make this objet a sub-instance of the class ClassLocalFolder to create the same folder structure
            if create_localfolder_object:
                super().__init__(output_folder)

            return self.result



    # sobreescribimos el método get_takeout_assets_by_filters() para que obtenga los assets de takeout_folder directamente en lugar de base_folder, para poder hacer el recuento de metadatos, sidecar, y archivos no soportados.
    def get_takeout_assets_by_filters(self, type='all', log_level=None):
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

            LOGGER.info(f"Retrieving {type} assets from the base folder: '{base_folder}'.")

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

            LOGGER.info(f"Found {len(assets)} {type} assets in the base folder.")
            return assets
##############################################################################
#                                END OF CLASS                                #
##############################################################################


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-CHECKS FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def unpack_zips(input_folder, unzip_folder, step_name="", log_level=None):
    """ Unzips all ZIP files from a folder into another """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if not os.path.exists(input_folder):
            LOGGER.error(f"{step_name}ZIP folder '{input_folder}' does not exist.")
            return
        os.makedirs(unzip_folder, exist_ok=True)
        for zip_file in os.listdir(input_folder):
            if zip_file.endswith(".zip"):
                zip_path = os.path.join(input_folder, zip_file)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        LOGGER.info(f"{step_name}Unzipping: {zip_file}")
                        zip_ref.extractall(unzip_folder)
                except zipfile.BadZipFile:
                    LOGGER.error(f"{step_name}Could not unzip file: {zip_file}")


def contains_takeout_structure(input_folder, step_name="", log_level=None):
    """
    Iteratively scans directories using a manual stack instead of recursion or os.walk.
    This can reduce overhead in large, nested folder structures.
    """
    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"")
        LOGGER.info(f"{step_name}Looking for Google Takeout structure in input folder...")
        stack = [input_folder]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            name = entry.name
                            if name.startswith("Photos from ") and name[12:16].isdigit():
                                # LOGGER.info(f"Found Takeout structure in folder: {entry.path}")
                                LOGGER.info(f"{step_name}Found Takeout structure in folder: {current}")
                                return True
                            stack.append(entry.path)
            except PermissionError:
                LOGGER.warning(f"{step_name}Permission denied accessing: {current}")
            except Exception as e:
                LOGGER.warning(f"{step_name}Error scanning {current}: {e}")
        LOGGER.info(f"{step_name}No Takeout structure found in input folder.")
        return False


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PRE-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def fix_mp4_files(input_folder, step_name="", log_level=None):
    """
    Busca archivos .MP4/.MOV/.AVI sin su JSON correspondiente. Si existe un archivo .HEIC/.JPG/.JPEG
    con el mismo nombre base y sí tiene JSON (posiblemente truncado con .supplemental-metadata),
    copia ese JSON renombrándolo con el nombre del vídeo, completando el sufijo si es necesario.

    Args:
        input_folder: Carpeta raíz donde buscar.
        step_name: Prefijo de mensajes de log.
        log_level: Nivel de log.
    """
    with set_log_level(LOGGER, log_level):
        counter_mp4_files_changed = 0
        video_exts = ['.mp4', '.mov', '.avi']
        image_exts = ['.heic', '.jpg', '.jpeg']
        supplemental = SUPPLEMENTAL_METADATA  # ya definido globalmente como 'supplemental-metadata'
        disable_tqdm = log_level < logging.WARNING

        all_video_files = []
        for _, _, files in os.walk(input_folder):
            all_video_files += [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

        if not all_video_files:
            return 0

        with tqdm(total=len(all_video_files), smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Fixing video JSONs", unit=" files", disable=disable_tqdm) as pbar:
            for root, _, files in os.walk(input_folder):
                file_set = set(files)

                video_files = [f for f in files if os.path.splitext(f)[1].lower() in video_exts]

                for video_file in video_files:
                    pbar.update(1)
                    base_name, ext = os.path.splitext(video_file)
                    target_json = f"{video_file}.json"

                    if target_json in file_set:
                        continue

                    # Buscar posibles imágenes con el mismo nombre base
                    matched_candidate = None
                    for image_ext in image_exts:
                        candidate_base = f"{base_name}{image_ext}"

                        # Buscar json exacto o con posible truncación del supplemental
                        for f in files:
                            if not f.lower().endswith('.json'):
                                continue

                            json_base = f[:-5]  # sin el .json
                            if not json_base.lower().startswith(candidate_base.lower()):
                                continue

                            # ¿Tiene .supplemental-metadata (truncado o completo)?
                            suffix = json_base[len(candidate_base):]
                            if suffix == '':
                                matched_candidate = f
                                break
                            elif supplemental.startswith(suffix.lstrip('.')):
                                matched_candidate = f
                                break

                        if matched_candidate:
                            break  # no seguir buscando si ya tenemos uno

                    if matched_candidate:
                        src_path = os.path.join(root, matched_candidate)
                        dst_path = os.path.join(root, target_json)
                        shutil.copy(src_path, dst_path)
                        LOGGER.debug(f"{step_name}Copied: {matched_candidate} → {target_json}")
                        counter_mp4_files_changed += 1

        return counter_mp4_files_changed


def fix_truncations(input_folder, step_name="", log_level=logging.INFO, name_length_threshold=46):
    """
    Recursively traverses `input_folder` and fixes:
      1) .json files with a truncated '.supplemental-metadata' suffix.
      2) .json files whose original extension is truncated (e.g. .jp.json → .jpg.json),
         by finding the real asset file in the same directory.
      3) Non-.json files with truncated special suffixes (based on SPECIAL_SUFFIXES).
      4) Non-.json files with truncated edited suffixes in multiple languages (based on EDITTED).

    Only processes files whose base name (without extension) exceeds `name_length_threshold` characters.

    Args:
        input_folder (str): Path to the root folder to scan.
        step_name (str): Prefix for log messages (e.g. "DEBUG   : ").
        log_level (int): Logging level for this operation.
        name_length_threshold (int): Minimum length of the base filename (sans extension) to consider.

    Returns:
        dict: Counters of changes made, with keys:
          - total_files: total number of files found
          - total_files_fixed: number of files that were renamed at least once
          - json_files_fixed: number of .json files modified
          - non_json_files_fixed: number of non-.json files modified
          - supplemental_metadata_fixed: count of '.supplemental-metadata' fixes
          - extensions_fixed: count of JSON extension corrections
          - special_suffixes_fixed: count of special-suffix completions
          - edited_suffixes_fixed: count of edited-suffix completions
    """
    def repl(m):
        tail = m.group(0)[len(sub):-len(ext)]
        return suf + tail + ext

    # 1) Pre-count all files for reporting
    total_files = sum(len(files) for _, _, files in os.walk(input_folder))

    counters = {
        "total_files": total_files,
        "total_files_fixed": 0,
        "json_files_fixed": 0,
        "non_json_files_fixed": 0,
        "supplemental_metadata_fixed": 0,
        "extensions_fixed": 0,
        "special_suffixes_fixed": 0,
        "edited_suffixes_fixed": 0,
    }

    # 2) Build a combined regex for ANY truncated prefix of any special or edited suffix
    def make_variant_pattern(suffix_list):
        variants = set(suffix_list)
        for s in suffix_list:
            for i in range(2, len(s)):
                variants.add(s[:i])
        # sort longest first so regex matches the largest truncation before smaller ones
        return '|'.join(sorted(map(re.escape, variants), key=len, reverse=True))

    variants_specials_pattern = make_variant_pattern(SPECIAL_SUFFIXES)
    variants_editted_pattern = make_variant_pattern(EDITTED_SUFFIXES)
    optional_counter = r'(?:\(\d+\))?'  # allow "(n)" counters
    with set_log_level(LOGGER, log_level):
        # --------------------------
        # --- Case A: JSON files ---
        # --------------------------
        # Precompute suffix and regex to fix any truncated '.supplemental-metadata' (preserves '(n)' counters)
        SUPPLEMENTAL_METADATA_WITH_DOT = '.' + SUPPLEMENTAL_METADATA
        # Calculate max allowed truncation length (excluding the initial '.su')
        MAX_TRUNC = len(SUPPLEMENTAL_METADATA_WITH_DOT) - len('.su')
        # Compile pattern to capture truncated stub and optional counter like '(1)'
        pattern = re.compile(
            rf'(?P<base>.*?)(?P<stub>\.su[\w-]{{0,{MAX_TRUNC}}})(?P<counter>\(\d+\))?$',
            re.IGNORECASE
        )

        # Walk through all subdirectories to process only JSON files
        for root, _, files in os.walk(input_folder):
            files_set = set(files)  # for matching JSON sidecars
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() == '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # A.1) Fix truncated '.supplemental-metadata' suffix
                    match = pattern.match(name)
                    if match and '.su' in name.lower():  # quick sanity check before applying the pattern
                        base = match.group('base')
                        counter = match.group('counter') or ''  # preserve any '(n)' counter
                        new_name = f"{base}{SUPPLEMENTAL_METADATA_WITH_DOT}{counter}{ext}"
                        new_path = Path(root) / new_name
                        if str(old_path).lower() != str(new_path).lower():
                            os.rename(old_path, new_path)
                            LOGGER.verbose(f"{step_name}Fixed JSON Supplemental Ext: {file} → {new_name}")
                            counters["supplemental_metadata_fixed"] += 1
                            # We need to medify file and old_path for next steps
                            file = new_name
                            old_path = new_path
                            name, ext = os.path.splitext(file)  # Refresh name and ext
                            files_set = set(os.listdir(root))   # Refresh to include any renamed files
                            if not file_modified:
                                counters["json_files_fixed"] += 1
                                counters["total_files_fixed"] += 1
                                file_modified = True
                    # end A.1

                    # A.2) Fix truncated original extension by locating the real asset file
                    parts = name.split('.')
                    if len(parts) >= 2:
                        # determine base_name and raw truncated ext (with possible "(n)")
                        if len(parts) == 2:
                            base_name, raw_trunc = parts
                        else:
                            base_name = '.'.join(parts[:-2])
                            raw_trunc = parts[-2]

                        # strip counter from raw_trunc, but save it
                        m_cnt = re.match(r'^(?P<ext>.*?)(\((?P<num>\d+)\))?$', raw_trunc)
                        trunc_ext = m_cnt.group('ext')
                        counter = f"({m_cnt.group('num')})" if m_cnt.group('num') else ''

                        # look for a matching asset: stem starts with base_name, ext starts with trunc_ext
                        full_ext = None
                        for cand in files_set:
                            if cand.lower().endswith('.json'):
                                continue
                            cand_stem = Path(cand).stem
                            if not cand_stem.lower().startswith(base_name.lower()):
                                continue
                            ext_cand = Path(cand).suffix.lstrip('.')
                            if ext_cand.lower().startswith(trunc_ext.lower()):
                                full_ext = Path(cand).suffix  # e.g. ".JPG"
                                break # Once a candidate has matched, skipp looping other candidates

                        if full_ext:
                            # replace the first ".trunc_ext" in the JSON name with the full_ext, leaving any "(n)" counter at the end untouched, then append ".json"
                            new_core = name.replace(f'.{trunc_ext}', full_ext, 1)
                            if counter and new_core.endswith(counter):
                                # If the counter is already present in `name`, don't re-append it
                                new_name = f"{new_core}{ext}"
                            else:
                                # re-attach the counter just before the ".json"
                                new_name = f"{new_core}{counter}{ext}"
                            new_path = Path(root) / new_name
                            if not new_path.exists() and str(old_path).lower() != str(new_path).lower():
                                os.rename(old_path, new_path)
                                LOGGER.verbose(f"{step_name}Fixed JSON Origin File Ext : {file} → {new_name}")
                                counters["extensions_fixed"] += 1
                                if not file_modified:
                                    counters["json_files_fixed"] += 1
                                    counters["total_files_fixed"] += 1
                                    file_modified = True
                    # end A.2

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed JSON File  : {original_file} → {new_name}")

        # ------------------------------------------------------------
        # --- Case B: Non-JSON files (special suffixes or editted) ---
        # ------------------------------------------------------------
        # Walk through all subdirectories to process only Non-JSON files
        for root, _, files in os.walk(input_folder):
            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() != '.json' and len(name) >= name_length_threshold:
                    # Set file_modified = False in each file
                    file_modified = False
                    # Save original_file and original_path for final message
                    original_file = file
                    old_path = Path(root) / file

                    # B.1) Fix Special Suffixes: '-effects', '-smile', '-mix', 'collage'
                    for suf in SPECIAL_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}(?=(-|_|\.|{variants_editted_pattern}|{SUPPLEMENTAL_METADATA})?(?:\(\d+\))?{re.escape(ext)}$)",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                match = pattern.search(file)
                                if match:
                                    start = match.start()
                                    end = match.end()
                                    tail = file[end:]  # everything after the matched truncation
                                    new_name = file[:start] + suf + tail
                                    new_path = Path(root) / new_name
                                    if str(old_path).lower() != str(new_path).lower():
                                        os.rename(old_path, new_path)
                                        LOGGER.verbose(f"{step_name}Fixed ORIGIN Special Suffix: {file} → {new_name}")
                                        counters["special_suffixes_fixed"] += 1
                                        # We need to modify file and old_path for next steps and to keep changes if other suffixes are found
                                        file = new_name
                                        old_path = new_path
                                        if not file_modified:
                                            counters["non_json_files_fixed"] += 1
                                            counters["total_files_fixed"] += 1
                                            file_modified = True
                                    break # Once one truncation of the current suf is applied, stop trying shorter ones

                    # B.2) Fix Edited Suffixes (multi-language): '-edited', '-edytowane', '-bearbeitet', '-bewerkt', '-編集済み', '-modificato', '-modifié', '-ha editado', '-editat'
                    for suf in EDITTED_SUFFIXES:
                        # try all truncations from longest to shortest
                        for i in range(len(suf), 1, -1):
                            sub = suf[:i]
                            pattern = re.compile(
                                rf"{re.escape(sub)}"
                                rf"(?:(?:{variants_editted_pattern}){optional_counter})*"
                                rf"{optional_counter}"
                                rf"{re.escape(ext)}$",
                                flags=re.IGNORECASE
                            )
                            if pattern.search(file):
                                new_name = pattern.sub(repl, file)
                                new_path = Path(root) / new_name
                                if str(old_path).lower() != str(new_path).lower():
                                    os.rename(old_path, new_path)
                                    LOGGER.verbose(f"{step_name}Fixed ORIGIN Edited Suffix : {file} → {new_name}")
                                    counters["edited_suffixes_fixed"] += 1
                                    # We need to medify file and old_path for next steps and to keep changes if other suffixes are found
                                    file = new_name
                                    old_path = new_path
                                    if not file_modified:
                                        counters["non_json_files_fixed"] += 1
                                        counters["total_files_fixed"] += 1
                                        file_modified = True
                                break # Once one truncation of the current suf is applied, stop trying shorter ones

                    if file_modified:
                        LOGGER.debug(f"{step_name}Fixed MEDIA File : {original_file} → {new_name}")
    return counters


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def run_command(command, capture_output=False, capture_errors=True, print_messages=True, step_name=""):
    """
    Ejecuta un comando. Muestra en consola actualizaciones de progreso sin loguearlas.
    Loguea solo líneas distintas a las de progreso. Corrige pegado de líneas en consola.
    """
    from Core.CustomLogger import suppress_console_output_temporarily
    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    def handle_stream(stream, is_error=False):
        init(autoreset=True)

        progress_re = re.compile(r': .*?(\d+)\s*/\s*(\d+)$')
        last_was_progress = False
        printed_final = set()

        while True:
            raw = stream.readline()
            if not raw:
                break

            # Limpiar ANSI y espacios finales
            ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', raw).rstrip()

            # Prefijo para agrupar barras
            common_part = line.split(' : ')[0] if ' : ' in line else line

            # 1) ¿Es barra de progreso?
            m = progress_re.search(line)
            if m:
                n, total = int(m.group(1)), int(m.group(2))

                # 1.a) Barra vacía (0/x)
                if n == 0:
                    if not print_messages:
                        # Log inicial
                        log_msg = f"{step_name}{line}"
                        if is_error:
                            LOGGER.error(log_msg)
                        else:
                            LOGGER.info(log_msg)
                    # nunca imprimo 0/x en pantalla
                    last_was_progress = True
                    continue

                # 1.b) Progreso intermedio (1 <= n < total)
                if n < total:
                    if print_messages:
                        print(f"\r{MSG_TAGS['INFO']}{step_name}{line}", end='', flush=True)
                        # custom_print(f"\r{step_name}{line}", end='', flush=True, log_level=logging.INFO)
                    last_was_progress = True
                    # no logueamos intermedias
                    continue

                # 1.c) Barra completa (n >= total), solo una vez
                if common_part not in printed_final:
                    # impresión en pantalla
                    if print_messages:
                        print(f"\r{MSG_TAGS['INFO']}{step_name}{line}", end='', flush=True)
                        # custom_print(f"\r{step_name}{line}", end='', flush=True, log_level=logging.INFO)
                        print()
                    # log final
                    log_msg = f"{step_name}{line}"
                    if is_error:
                        LOGGER.error(log_msg)
                    else:
                        LOGGER.info(log_msg)

                    printed_final.add(common_part)

                last_was_progress = False
                continue

            # 2) Mensaje normal: si venía de progreso vivo, forzamos salto
            if last_was_progress and print_messages:
                print()
            last_was_progress = False

            # 3) Impresión normal
            warning_keywords = [
                "WARNING",
                "ExifTool command failed with exit code",
                "Error output",
            ]
            if print_messages:
                if is_error:
                    # print(f"{MSG_TAGS_COLORED['ERROR']}{step_name}{line}{Style.RESET_ALL}")
                    custom_print(f"{step_name}{line}", log_level=logging.ERROR)
                else:
                    if "VERBOSE" in line:
                        # print(f"{MSG_TAGS_COLORED['VERBOSE']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.VERBOSE)         # Could raise error if we have not previously set logging.VERBOSE properly
                        # custom_print(f"{step_name}{line}", log_level=VERBOSE_LEVEL_NUM)
                    elif "DEBUG" in line:
                        # print(f"{MSG_TAGS_COLORED['DEBUG']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.DEBUG)
                    elif "WARNING" in line:
                        # print(f"{MSG_TAGS_COLORED['WARNING']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.WARNING)
                    elif any(kw in line for kw in warning_keywords):
                        # print(f"{MSG_TAGS_COLORED['WARNING']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.WARNING)
                    elif "ERROR" in line:
                        # print(f"{MSG_TAGS_COLORED['ERROR']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.ERROR)
                    else:
                        # print(f"{MSG_TAGS_COLORED['INFO']}{step_name}{line}{Style.RESET_ALL}")
                        custom_print(f"{step_name}{line}", log_level=logging.INFO)

            # 4) Logging normal
            if is_error:
                LOGGER.error(f"{step_name}{line}")
            else:
                if "ERROR" in line:
                    LOGGER.error(f"{step_name}{line}")
                elif "WARNING" in line:
                    LOGGER.warning(f"{step_name}{line}")
                elif "DEBUG" in line:
                    LOGGER.debug(f"{step_name}{line}")
                elif "VERBOSE" in line:
                    LOGGER.verbose(f"{step_name}{line}")
                elif any(kw in line for kw in warning_keywords):
                    LOGGER.warning(f"{step_name}{line}")
                else:
                    LOGGER.info(f"{step_name}{line}")

        # 5) Al cerrar stream, si quedó un progreso vivo, cerramos línea
        if last_was_progress and print_messages:
            print()

    # ------------------------------------------------------------------------------------------------------------------------------------------------------------
    with suppress_console_output_temporarily(LOGGER):
        if not capture_output and not capture_errors:
            return subprocess.run(command, check=False, text=True, encoding="utf-8", errors="replace").returncode
        else:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture_errors else subprocess.DEVNULL,
                text=True, encoding = "utf-8", errors = "replace"
            )
            if capture_output:
                handle_stream(process.stdout, is_error=False)
            if capture_errors:
                handle_stream(process.stderr, is_error=True)

            process.wait()  # Esperar a que el proceso termine
            return process.returncode


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT POST-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sync_mp4_timestamps_with_images(input_folder, step_name="", log_level=None):
    """
    Look for .MP4 files with the same base name as any Live Picture file (.HEIC, .JPG, .JPEG)
    in the same folder. If found, set the date and time of the .MP4 file (or the symlink itself)
    to match the original Live Picture.
    """
    # Set logging level for this operation
    with set_log_level(LOGGER, log_level):
        # Count total files for progress bar
        total_files = sum(len(files) for _, _, files in os.walk(input_folder))
        with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'", unit=" files"
                  ) as pbar:
            # Walk through all directories and files
            for path, _, files in os.walk(input_folder):
                # Build a mapping from base filename to its extensions
                file_dict = {}
                for filename in files:
                    pbar.update(1)
                    name, ext = os.path.splitext(filename)
                    base_name = name.lower()
                    ext = ext.lower()
                    file_dict.setdefault(base_name, {})[ext] = filename
                # For each group of files sharing the same base name
                for base_name, ext_file_map in file_dict.items():
                    if '.mp4' not in ext_file_map:
                        continue
                    mp4_filename = ext_file_map['.mp4']
                    mp4_file_path = os.path.join(path, mp4_filename)
                    # Detect if the .mp4 is a symlink
                    is_mp4_link = os.path.islink(mp4_file_path)
                    # Look for a matching Live Picture image
                    image_exts = ['.heic', '.jpg', '.jpeg']
                    for image_ext in image_exts:
                        if image_ext not in ext_file_map:
                            continue
                        image_filename = ext_file_map[image_ext]
                        image_file_path = os.path.join(path, image_filename)
                        try:
                            # Get the image's atime and mtime
                            image_stats = os.stat(image_file_path)
                            atime, mtime = image_stats.st_atime, image_stats.st_mtime
                            if is_mp4_link:
                                # Apply timestamps to the symlink itself
                                os.utime(mp4_file_path, (atime, mtime), follow_symlinks=False)
                                LOGGER.debug(f"{step_name}Timestamps applied to symlink: {os.path.relpath(mp4_file_path, input_folder)}")
                            else:
                                # Apply timestamps to the regular .mp4 file
                                os.utime(mp4_file_path, (atime, mtime))
                                LOGGER.debug(f"{step_name}Timestamps applied to file: {os.path.relpath(mp4_file_path, input_folder)}")
                        except FileNotFoundError:
                            # Warn if either the .mp4 or the image file is missing
                            LOGGER.warning(f"{step_name}File not found. MP4: {mp4_file_path} | Image: {image_file_path}")
                        except Exception as e:
                            # Log any other errors encountered
                            LOGGER.error(f"{step_name}Error syncing {mp4_file_path}: {e}")
                        # Only sync with the first matching image
                        break


def force_remove_directory(folder, step_name='', log_level=None):
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(folder):
            shutil.rmtree(folder, onerror=onerror)
            LOGGER.info(f"{step_name}The folder '{folder}' and all its content have been deleted.")
            return True
        else:
            LOGGER.info(f"{step_name}Cannot delete the folder '{folder}'.")
            return False


def copy_move_folder(src, dst, ignore_patterns=None, move=False, step_name="", log_level=None):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param step_name:
    :param log_level:
    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        # Ignore function
        action = 'Moving' if move else 'Copying'
        try:
            if not is_valid_path(src):
                LOGGER.error(f"{step_name}The path '{src}' is not valid for the execution platform. Cannot copy/move folders from it.")
                return False
            if not is_valid_path(dst):
                LOGGER.error(f"{step_name}The path '{dst}' is not valid for the execution platform. Cannot copy/move folders to it.")
                return False

            def ignore_function(files, ignore_patterns):
                if ignore_patterns:
                    # Convert to a list if a single pattern is provided
                    patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
                    ignored = []
                    for pattern in patterns:
                        ignored.extend(fnmatch.filter(files, pattern))
                    return set(ignored)
                return set()

            # Ensure the source folder exists
            if not os.path.exists(src):
                raise FileNotFoundError(f"{step_name}Source folder does not exist: '{src}'")
            # Create the destination folder if it doesn't exist
            os.makedirs(dst, exist_ok=True)

            if move:
                # Contar el total de carpetas
                total_files = sum([len(files) for _, _, files in os.walk(src)])
                # Mostrar la barra de progreso basada en carpetas
                with tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                    for path, dirs, files in os.walk(src, topdown=True):
                        pbar.update(1)
                        # Compute relative path
                        rel_path = os.path.relpath(path, src)
                        # Destination path
                        dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        # Apply ignore function to files and dirs
                        ignore = ignore_function(files + dirs, ignore_patterns=ignore_patterns)
                        # Filter dirs in-place to skip ignored directories
                        dirs[:] = [d for d in dirs if d not in ignore]
                        # Create destination directory
                        os.makedirs(dest_path, exist_ok=True)
                        # Move files
                        for file in files:
                            if file not in ignore:
                                src_file = os.path.join(path, file)
                                dst_file = os.path.join(dest_path, file)
                                shutil.move(src_file, dst_file)
                    LOGGER.info(f"{step_name}Folder moved successfully from {src} to {dst}")
            else:
                system = platform.system()
                try:
                    if system in ("Linux", "Darwin"):
                        LOGGER.info(f"{step_name}Trying fast copy with cp --reflink=auto...")
                        subprocess.run([
                            "cp", "-a", "--reflink=auto", os.path.join(src, "."), dst
                        ], check=True)
                        LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using cp --reflink.")
                        return True
                except Exception as e:
                    LOGGER.warning(f"{step_name}cp --reflink failed: {e}")

                try:
                    if system == "Windows":
                        LOGGER.info(f"{step_name}Trying fast copy with robocopy...")
                        result = subprocess.run([
                            "robocopy", src, dst, "/MIR", "/R:0", "/W:0", "/NFL", "/NDL", "/NJH", "/NJS"
                        ], capture_output=True, text=True)
                        if result.returncode <= 7:
                            LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using robocopy.")
                            return True
                        else:
                            raise Exception(f"robocopy error code {result.returncode}: {result.stderr}")
                    elif system in ("Linux", "Darwin"):
                        LOGGER.info(f"{step_name}Trying fast copy with rsync...")
                        subprocess.run([
                            "rsync", "-a", "--info=progress2", src + "/", dst
                        ], check=True)
                        LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using rsync.")
                        return True
                except Exception as e:
                    LOGGER.warning(f"{step_name}Fast copy methods failed: {e}, falling back to copytree.")

                # Copy the folder contents with fallback
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
                LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst} using shutil.copytree.")
                return True

        except Exception as e:
            LOGGER.error(f"{step_name}Error {action} folder: {e}")
            return False


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[], step_name="", log_level=None):
    """
    Organizes files into subfolders based on their EXIF or modification date.

    Args:
        input_folder (str, Path): The base directory containing the files.
        type: 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (str, Path or list): A list of subfolder names to exclude from processing.

    Raises:
        ValueError: If the value of `type` is invalid.
        :param step_name:
        :param log_level:
    """
    import os
    import shutil
    from datetime import datetime
    import piexif
    def get_exif_date(image_path):
        try:
            exif_dict = piexif.load(image_path)
            for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                tag_id = piexif.ExifIFD.__dict__.get(tag)
                value = exif_dict["Exif"].get(tag_id)
                if value:
                    return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    with set_log_level(LOGGER, log_level):
        if type not in ['year', 'year/month', 'year-month']:
            raise ValueError(f"{step_name}The 'type' parameter must be 'year', 'year/month' or 'year-month'.")
        total_files = 0
        for _, dirs, files in os.walk(input_folder):
            dirs[:] = [d for d in dirs if d not in exclude_subfolders]
            total_files += len(files)
        with tqdm(total=total_files, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_subfolders]
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                    mod_time = None
                    ext = os.path.splitext(file)[1].lower()
                    # Intentar obtener fecha EXIF si es imagen
                    if ext in PHOTO_EXT:
                        try:
                            mod_time = get_exif_date(file_path)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Error reading EXIF from {file_path}: {e}")
                    # Si no hay EXIF o no es imagen, usar fecha de sistema
                    if not mod_time:
                        try:
                            mtime = os.path.getmtime(file_path)
                            mod_time = datetime.fromtimestamp(mtime if mtime > 0 else 0)
                        except Exception as e:
                            LOGGER.warning(f"{step_name}Error reading mtime for {file_path}: {e}")
                            mod_time = datetime(1970, 1, 1)
                    LOGGER.verbose(f"{step_name}Using date {mod_time} for file {file_path}")
                    # Determinar carpeta destino
                    if type == 'year':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'))
                    elif type == 'year/month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'), mod_time.strftime('%m'))
                    elif type == 'year-month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y-%m'))
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(file_path, os.path.join(target_dir, file))
        LOGGER.info(f"{step_name}Organization completed. Folder structure per '{type}' created in '{input_folder}'.")


def move_albums(input_folder, albums_subfolder=f"{FOLDERNAME_ALBUMS}", exclude_subfolder=None, step_name="", log_level=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str, Path): Path to the input folder containing the albums.
        albums_subfolder (str, Path): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
        :param step_name:
        :param log_level:
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        def safe_move(folder_path, albums_path):
            destination = os.path.join(albums_path, os.path.basename(folder_path))
            if os.path.exists(destination):
                if os.path.isdir(destination):
                    shutil.rmtree(destination)
                else:
                    os.remove(destination)
            shutil.move(folder_path, albums_path)

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]
        albums_path = os.path.join(input_folder, albums_subfolder)
        exclude_subfolder_paths = [os.path.abspath(os.path.join(input_folder, sub)) for sub in (exclude_subfolder or [])]
        subfolders = os.listdir(input_folder)
        subfolders = [subfolder for subfolder in subfolders if not subfolder == '@eaDir' and not subfolder == FOLDERNAME_NO_ALBUMS]

        # for subfolder in tqdm(subfolders, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Moving Albums in '{input_folder}' to Subfolder '{albums_subfolder}'", unit=" albums"):
        for subfolder in tqdm(subfolders, smoothing=0.1, desc=f"{MSG_TAGS['INFO']}{step_name}Moving Albums in '{os.path.basename(input_folder)}' to Subfolder '{os.path.basename(albums_subfolder)}'", unit=" albums"):
            folder_path = os.path.join(input_folder, subfolder)
            # if os.path.isdir(folder_path) and subfolder != albums_subfolder and os.path.abspath(folder_path) not in exclude_subfolder_paths:
            if (
                    os.path.isdir(folder_path)
                    and subfolder != albums_subfolder
                    and os.path.abspath(folder_path) != os.path.abspath(input_folder)
                    and os.path.abspath(folder_path) not in exclude_subfolder_paths
            ):
                LOGGER.debug(f"{step_name}Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'")
                os.makedirs(albums_path, exist_ok=True)
                safe_move(folder_path, albums_path)
        # Finally Move Albums to Albums root folder (removing 'Takeout' and 'Google Fotos' / 'Google Photos' folders if exists
        move_albums_to_root(albums_path, step_name=step_name, log_level=logging.INFO)


def move_albums_to_root(albums_root, step_name="", log_level=None):
    """
    Moves all albums from nested subdirectories ('Takeout/Google Fotos' or 'Takeout/Google Photos')
    directly into the 'Albums' folder, removing unnecessary intermediate folders.
    """
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        possible_google_folders = ["Google Fotos", "Google Photos"]
        takeout_path = os.path.join(albums_root, "Takeout")
        # Check if 'Takeout' exists
        if not os.path.exists(takeout_path):
            LOGGER.debug(f"{step_name}'Takeout' folder not found at {takeout_path}. Exiting.")
            return
        # Find the actual Google Photos folder name
        google_photos_path = None
        for folder in possible_google_folders:
            path = os.path.join(takeout_path, folder)
            if os.path.exists(path):
                google_photos_path = path
                break
        if not google_photos_path:
            LOGGER.debug(f"{step_name}No valid 'Google Fotos' or 'Google Photos' folder found inside 'Takeout'. Exiting.")
            return
        LOGGER.debug(f"{step_name}Found Google Photos folder: {google_photos_path}")
        LOGGER.info(f"{step_name}Moving Albums to Albums root folder...")
        # Move albums to the root 'Albums' directory
        for album in os.listdir(google_photos_path):
            album_path = os.path.join(google_photos_path, album)
            target_path = os.path.join(albums_root, album)
            if os.path.isdir(album_path):  # Ensure it's a directory (album)
                new_target_path = target_path
                count = 1
                # Handle naming conflicts by adding a suffix
                while os.path.exists(new_target_path):
                    new_target_path = f"{target_path}_{count}"
                    count += 1
                # Move the album
                shutil.move(album_path, new_target_path)
                LOGGER.debug(f"{step_name}Moved: {album_path} → {new_target_path}")
        # Attempt to remove empty folders
        try:
            shutil.rmtree(takeout_path)
            LOGGER.debug(f"{step_name}'Takeout' folder successfully removed.")
        except Exception as e:
            LOGGER.error(f"{step_name}Failed to remove 'Takeout': {e}")


def count_valid_albums(folder_path, excluded_folders=None, step_name="", log_level=None):
    """
    Walk every sub-folder in *folder_path* and count how many of them contain at
    least one photo or video (direct file, POSIX symlink, or Windows .lnk).
    """
    if excluded_folders is None:
        excluded_folders = ()

    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    MEDIA_EXT = set(PHOTO_EXT) | set(VIDEO_EXT)         # union once → O(1) lookup

    valid_albums = 0
    visited_dirs = set()

    with set_log_level(LOGGER, log_level):
        for root, dirs, files in os.walk(folder_path, followlinks=True):
            real_root = os.path.realpath(root)
            if real_root in visited_dirs:               # avoid loops with symlinked dirs
                continue
            visited_dirs.add(real_root)

            folder_name = os.path.basename(root)

            # ── skip folders by name ────────────────────────────────────────────
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()
                continue

            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]

            # ── inspect files inside this folder ───────────────────────────────
            for fname in files:
                fpath = Path(root) / fname
                link_ext = fpath.suffix.lower()                 # ext of the file itself
                target_ext = ''                                 # will be filled below

                try:
                    if fpath.is_symlink():                      # POSIX / NTFS symlink
                        target_ext = fpath.resolve(strict=False).suffix.lower()

                    elif os.name == 'nt' and link_ext == '.lnk':
                        # Windows shortcut (.lnk): try to infer inner extension from its stem
                        target_ext = Path(fpath.stem).suffix.lower()
                        # NOTE: we don't parse the .lnk binary; good enough if names keep the ext.

                    else:
                        target_ext = link_ext                   # normal file (no link)

                    if link_ext in MEDIA_EXT or target_ext in MEDIA_EXT:
                        valid_albums += 1
                        LOGGER.debug(f"{step_name}✅ Valid album at: {root}")
                        break                                   # next folder

                except Exception as exc:
                    LOGGER.warning(f"{step_name}⚠️ Cannot inspect {fpath}: {exc}")

    return valid_albums


def clone_folder_fast(input_folder, cloned_folder, step_name="", log_level=None):
    """
    Clones input_folder into cloned_folder using the fastest method available:
    - Tries CoW (cp --reflink=auto) on Linux/macOS.
    - Uses robocopy on Windows.
    - Uses rsync on Unix-like systems if reflink is not available.
    - Falls back to shutil.copytree.

    Returns:
        str: Path to the cloned folder (or input_folder if all methods fail).
    """
    with set_log_level(LOGGER, log_level):
        LOGGER.info(f"{step_name}Creating temporary working folder at: {cloned_folder}")

        system = platform.system()

        try:
            # 1. Attempt cp --reflink (Linux/macOS with Btrfs, APFS, etc.)
            if system in ("Linux", "Darwin"):
                LOGGER.info(f"{step_name}Trying fast clone with cp --reflink=auto...")
                subprocess.run([
                    "cp", "-a", "--reflink=auto", input_folder, cloned_folder
                ], check=True)
                LOGGER.info(f"{step_name}✅ CoW clone succeeded with cp --reflink.")
                return cloned_folder

        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ cp --reflink failed: {e}")

        try:
            if system == "Windows":
                LOGGER.info(f"{step_name}Trying fast clone with robocopy...")
                result = subprocess.run([
                    "robocopy", input_folder, cloned_folder, "/MIR", "/R:0", "/W:0", "/NFL", "/NDL", "/NJH", "/NJS"
                ], capture_output=True, text=True)
                if result.returncode <= 7:
                    LOGGER.info(f"{step_name}✅ Clone succeeded with robocopy.")
                    return cloned_folder
                else:
                    raise Exception(f"robocopy error code {result.returncode}: {result.stderr}")

            elif system in ("Linux", "Darwin"):
                LOGGER.info(f"{step_name}Trying fast clone with rsync...")
                subprocess.run([
                    "rsync", "-a", "--info=progress2", input_folder + "/", cloned_folder
                ], check=True)
                LOGGER.info(f"{step_name}✅ Clone succeeded with rsync.")
                return cloned_folder

        except Exception as e:
            LOGGER.warning(f"{step_name}⚠️ Fast method failed, falling back to copytree: {e}")

        try:
            shutil.copytree(input_folder, cloned_folder)
            LOGGER.info(f"{step_name}✅ Clone succeeded with shutil.copytree.")
            return cloned_folder
        except Exception as e:
            LOGGER.warning(f"{step_name}❌ All cloning methods failed: {e}")
            return input_folder




##############################################################################
#                            MAIN TESTS FUNCTION                             #
##############################################################################
# Example main usage
if __name__ == "__main__":
    change_working_dir()

    input_folder = Path(r"r:\jaimetur\PhotoMigrator\Takeout")
    # timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # base_folder = input_folder.parent / f"Takeout_processed_{timestamp}"

    takeout = ClassTakeoutFolder(input_folder)
    res = takeout.process("Output_Takeout_Folder", capture_output=True, capture_errors=True, print_messages=True, create_localfolder_object=False, log_level=logging.DEBUG)
    print(res)

