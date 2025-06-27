# ClassGoogleTakeout.py
# -*- coding: utf-8 -*-

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from Core.CustomLogger import set_log_level
from Core.FileStatistics import count_files_per_type_and_extract_dates_multi_threads
from Core.GlobalVariables import ARGS, LOG_LEVEL, LOGGER, START_TIME, FOLDERNAME_ALBUMS, FOLDERNAME_NO_ALBUMS
from Features.GoogleTakeout import MetadataFixers
# Import ClassLocalFolder (Parent Class of this)
from Features.GoogleTakeout.ClassLocalFolder import ClassLocalFolder
from Features.GoogleTakeout.GoogleTakeoutFunctions import contains_takeout_structure, unpack_zips
from Features.GoogleTakeout.GoogleTakeoutFunctions import fix_mp4_files, fix_truncations, sync_mp4_timestamps_with_images, force_remove_directory, copy_move_folder, organize_files_by_date, move_albums, count_valid_albums
from Features.StandAlone.AutoRenameAlbumsFolders import rename_album_folders
from Features.StandAlone.Duplicates import find_duplicates
from Features.StandAlone.FixSymLinks import fix_symlinks_broken
from Utils.FileUtils import delete_subfolders, remove_empty_dirs
from Utils.GeneralUtils import print_dict_pretty
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
                # Determine the input_folder deppending if the Takeout have been unzipped or not
                input_folder = self.get_input_folder()
                step_name = '🔍 [PRE-CHECKS]-[Takeout Clonning] : '
                self.substep += 1
                sub_step_start_time = datetime.now()
                LOGGER.info(f"")
                LOGGER.info(f"{step_name}Clonning Takeout Folder: {input_folder}...")
                # Call the clonning functuon
                tmp_folder = clone_backup_if_needed (self.input_folder, step_name=step_name, log_level=log_level)
                if tmp_folder != self.input_folder:
                    ARGS['google-takeout'] = tmp_folder
                    self.input_folder = tmp_folder
                    LOGGER.info(f"{step_name}Takeout folder clonned succesfully as working folder: '{tmp_folder}' ")
                sub_step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=round((sub_step_end_time - sub_step_start_time).total_seconds())))
                LOGGER.info(f"")
                step_name_cleaned = ' '.join(step_name.replace(' : ', '').split()).replace(' ]', ']')
                LOGGER.info(f"{step_name}Sub-Step {self.step}.{self.substep}: {step_name_cleaned} completed in {formatted_duration}.")
                self.steps_duration.append({'step_id': f"{self.step}.{self.substep}", 'step_name': step_name_cleaned, 'duration': formatted_duration})
    
    
            # Sub-Step 2: Count initial files in Takeout Folder before to process with GPTH and modify any original file
            # ----------------------------------------------------------------------------------------------------------------------
            # Determine the input_folder deppending if the Takeout have been unzipped or not
            input_folder = self.get_input_folder()
            step_name = '🔍 [PRE-CHECKS]-[Count Files  ] : '
            self.substep += 1
            sub_step_start_time = datetime.now()
            LOGGER.info(f"")
            LOGGER.info(f"{step_name}Counting files in Takeout Folder: {input_folder}...")

            # New function to count all file types and extract also date info
            initial_takeout_counters, dates = count_files_per_type_and_extract_dates_multi_threads(input_folder=input_folder, output_file=f"input_dates_metadata.json", step_name=step_name, log_level=LOG_LEVEL)

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

                # if manual copy is detected, don't delete the input folder yet, will do it in next step
                if not self.ARGS['google-keep-takeout-folder'] and not manual_copy_move_needed:
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
                if not self.ARGS['google-keep-takeout-folder']:
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
                LOGGER.info(f"{step_name}Moving All your albums into f'{FOLDERNAME_ALBUMS}' folder for a better organization...")
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

            # New function to count all file types and extract also date info
            # output_counters = count_files_per_type_and_extract_dates_multi_threads(input_folder=output_folder, skip_exif=False, skip_json=True, step_name=step_name, log_level=LOG_LEVEL)

            # New function to count all file types and extract also date info
            output_counters, dates = count_files_per_type_and_extract_dates_multi_threads(input_folder=output_folder, output_file=f"output_dates_metadata.json", step_name=step_name, log_level=LOG_LEVEL)

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
            if not ARGS['google-keep-takeout-folder']:
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
            if LOG_LEVEL <= logging.DEBUG:
                LOGGER.debug (f"Process Output:")
                print_dict_pretty(result, log_level=LOG_LEVEL)

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
                LOGGER.info(f"All the Photos/Videos Fixed can be found on folder: '{output_folder}'")
                LOGGER.info(f"")
                LOGGER.info(f"📊 FINAL SUMMARY & STATISTICS:")
                LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
                LOGGER.info(f"Total Size of Takeout folder                : {result['input_counters']['total_size_mb']} MB")
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
                LOGGER.info(f"Total Size of Output folder                 : {result['output_counters']['total_size_mb']} MB")
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
