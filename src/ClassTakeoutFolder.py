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
from dataclasses import dataclass

# Keep your existing imports for external modules:
import Utils
import MetadataFixers
from Duplicates import find_duplicates
from CustomLogger import set_log_level

# Import the global LOGGER from GlobalVariables
from GlobalVariables import LOGGER

# Import ClassLocalFolder (Parent Class of this)
from ClassLocalFolder import ClassLocalFolder
from Utils import rename_album_folders


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
        with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
            return Utils.contains_takeout_structure(input_folder=self.takeout_folder, log_level=log_level)

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
            # Unzip files
            LOGGER.info("")
            LOGGER.info(f"=====================================")
            LOGGER.info(f"INFO    : UNPACKING TAKEOUT FOLDER...")
            LOGGER.info(f"=====================================")
            LOGGER.info("")
            LOGGER.info(f"INFO    : ⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")
            LOGGER.info("")
            step_start_time = datetime.now()
            Utils.unpack_zips(input_folder, unzip_folder)
            # Make the 'Unzipped' folder as the new takeout_folder for the object
            self.unzipped_folder = Path(unzip_folder)
            # Change flag self.check_if_needs_unzip to False
            self.needs_unzip = False
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : Unzipping completed in {formatted_duration}.")
            LOGGER.info("")


    def pre_process_and_process(self, capture_output=False, capture_errors=True, skip_process=False):
        if self.needs_unzip:
            LOGGER.info("INFO    : 🗳️ Input Folder contains ZIP files and needs to be unzipped first. Unzipping it...")
            unzip_folder = Path(f"{self.takeout_folder}_unzipped_{self.TIMESTAMP}")
            # Unzip the files into unzip_folder
            self.unzip(input_folder=self.takeout_folder, unzip_folder=unzip_folder, log_level=self.log_level)
            self.needs_process = Utils.contains_takeout_structure(self.unzipped_folder)

        if not skip_process:
            if self.needs_process:
                LOGGER.info("INFO    : 🔢 Input Folder contains a Google Takeout Structure and needs to be processed first. Processing it...")
                # if self.unzipped_folder:
                #     base_folder = Path(f"{self.unzipped_folder}_{self.ARGS['google-output-folder-suffix']}_{self.TIMESTAMP}")
                # else:
                base_folder = Path(f"{self.takeout_folder}_{self.ARGS['google-output-folder-suffix']}_{self.TIMESTAMP}")
                # Process Takeout_folder and put output into base_folder
                self.process(output_takeout_folder=base_folder, capture_output=capture_output, capture_errors=capture_errors, log_level=logging.INFO)
                super().__init__(base_folder)  # Inicializar con la carpeta procesada
            else:
                base_folder = self.takeout_folder
                super().__init__(base_folder)  # Inicializar con la carpeta original si no se necesita procesamiento


    def process(self, output_takeout_folder, capture_output=True, capture_errors=True, log_level=logging.INFO):
        """
        Main method to process Google Takeout data. Follows the same steps as the original
        process() function, but uses LOGGER and self.ARGS instead of global.
        """
        @dataclass
        class ProcessingResult:
            initial_takeout_numfiles: int
            initial_takeout_total_images: int
            initial_takeout_total_videos: int
            initial_takeout_total_sidecars: int
            initial_takeout_total_metadatas: int
            initial_takeout_total_supported_files: int
            initial_takeout_total_not_supported_files: int
            valid_albums_found: int
            symlink_fixed: int
            symlink_not_fixed: int
            duplicates_found: int
            removed_empty_folders: int
            renamed_album_folders: int
            duplicates_album_folders: int
            duplicates_albums_fully_merged: int
            duplicates_albums_not_fully_merged: int

        # Initialize all fields to return
        initial_takeout_numfiles = 0
        initial_takeout_total_images = 0
        initial_takeout_total_videos = 0
        initial_takeout_total_sidecars = 0
        initial_takeout_total_metadatas = 0
        initial_takeout_total_supported_files = 0
        initial_takeout_total_not_supported_files = 0
        valid_albums_found = 0
        symlink_fixed = 0
        symlink_not_fixed = 0
        duplicates_found = 0
        removed_empty_folders = 0
        renamed_album_folders = 0
        duplicates_album_folders = 0
        duplicates_albums_fully_merged = 0
        duplicates_albums_not_fully_merged = 0

        with set_log_level(LOGGER, log_level):  # Temporarily adjust log level
            LOGGER.info("")
            LOGGER.info(f"==========================================")
            LOGGER.info(f"INFO    : 🔢 TAKEOUT PROCESSING STARTED...")
            LOGGER.info(f"==========================================")
            processing_start_time = datetime.now()

            if capture_output is None: capture_output=self.ARGS['show-gpth-info']
            if capture_errors is None: capture_errors=self.ARGS['show-gpth-errors']

            # Determine if manual copy/move is needed (for step 3)
            manual_copy_move_needed = self.ARGS['google-skip-gpth-tool'] or self.ARGS['google-ignore-check-structure']

            # step 1: Pre-Process Takeout folder
            self.step += 1
            LOGGER.info("")
            LOGGER.info("=============================================")
            LOGGER.info(f"INFO    : {self.step}. PRE-PROCESSING TAKEOUT FOLDER...")
            LOGGER.info("=============================================")
            LOGGER.info("")
            step_start_time = datetime.now()
            # Pre-process the object with skip_process=True to just unzip files in case they are zipped.
            self.pre_process_and_process(skip_process=True)
            # Select the input_folder deppending if the Takeout have been unzipped or not
            if self.unzipped_folder:
                input_folder = self.unzipped_folder
            else:
                input_folder = self.takeout_folder
            # Delete hidden subfolders '@eaDir'
            LOGGER.info("INFO    : Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
            Utils.delete_subfolders(input_folder, "@eaDir")
            # Fix .MP4 timestamps
            LOGGER.info("")
            LOGGER.info("INFO    : Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
            Utils.fix_mp4_files(input_folder)

            # Count initial files in Takeout Folder before to process with GPTH, since once process input_folder may be deleted if --google-move-takeout-folder has been given
            LOGGER.info(f"INFO    : Counting files in Input Folder: {input_folder}...")
            initial_takeout_numfiles = Utils.count_files_in_folder(input_folder)
            initial_takeout_total_images = Utils.count_images_in_folder(input_folder)
            initial_takeout_total_videos = Utils.count_videos_in_folder(input_folder)
            initial_takeout_total_sidecars = Utils.count_sidecars_in_folder(input_folder)
            initial_takeout_total_metadatas = Utils.count_metadatas_in_folder(input_folder)
            # Calculate initial_takeout_total_supported_files and initial_takeout_total_not_supported_files
            initial_takeout_total_supported_files = initial_takeout_total_images + initial_takeout_total_videos + initial_takeout_total_sidecars + initial_takeout_total_metadatas
            initial_takeout_total_not_supported_files = initial_takeout_numfiles - initial_takeout_total_supported_files

            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")


            # step 2: Process photos with GPTH tool
            if not self.ARGS['google-skip-gpth-tool']:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("=====================================================")
                LOGGER.info(f"INFO    : {self.step}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
                LOGGER.info("=====================================================")
                LOGGER.info("")
                step_start_time = datetime.now()
                LOGGER.info(f"INFO    : ⏳ This process may take long time, depending on how big is your Takeout. Be patient... 🙂")

                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning("WARNING : Ignore Google Takeout Structure detected ('-gics, --google-ignore-check-structure' flag detected).")
                else:
                    # Check Takeout structure
                    has_takeout_structure = Utils.contains_takeout_structure(input_folder)
                    if not has_takeout_structure:
                        LOGGER.warning(f"WARNING : No Takeout structure detected in input folder. The tool will process the folder ignoring Takeout structure.")
                        self.ARGS['google-ignore-check-structure'] = True

                ok = MetadataFixers.fix_metadata_with_gpth_tool(
                    input_folder=input_folder,
                    output_folder=output_takeout_folder,
                    capture_output=capture_output,
                    capture_errors=capture_errors,
                    symbolic_albums=self.ARGS['google-create-symbolic-albums'],
                    skip_extras=self.ARGS['google-skip-extras-files'],
                    move_takeout_folder=self.ARGS['google-move-takeout-folder'],
                    ignore_takeout_structure=self.ARGS['google-ignore-check-structure'],
                    log_level=log_level
                )
                if not ok:
                    LOGGER.warning(f"WARNING : Metadata fixing didn't finish properly due to GPTH error.")
                    LOGGER.warning(f"WARNING : If your Takeout does not contains Year/Month folder structure, you can use '-gics, --google-ignore-check-structure' flag.")
                    # return (0, 0, 0, 0, initial_takeout_numfiles, 0, 0, 0, 0, 0)
                    return ProcessingResult(
                        initial_takeout_numfiles=initial_takeout_numfiles,
                        initial_takeout_total_images=initial_takeout_total_images,
                        initial_takeout_total_videos=initial_takeout_total_videos,
                        initial_takeout_total_sidecars=initial_takeout_total_sidecars,
                        initial_takeout_total_metadatas=initial_takeout_total_metadatas,
                        initial_takeout_total_supported_files=initial_takeout_total_supported_files,
                        initial_takeout_total_not_supported_files=initial_takeout_total_not_supported_files,
                        valid_albums_found=valid_albums_found,
                        symlink_fixed=symlink_fixed,
                        symlink_not_fixed=symlink_not_fixed,
                        duplicates_found=duplicates_found,
                        removed_empty_folders=removed_empty_folders,
                        renamed_album_folders=renamed_album_folders,
                        duplicates_album_folders=duplicates_album_folders,
                        duplicates_albums_fully_merged=duplicates_albums_fully_merged,
                        duplicates_albums_not_fully_merged=duplicates_albums_not_fully_merged,
                    )

                # if manual copy is detected, don't delete the input folder yet, will do it in next step
                if self.ARGS['google-move-takeout-folder'] and not manual_copy_move_needed:
                    Utils.force_remove_directory(input_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")

            # step 3: Copy/Move files to output folder manually
            if manual_copy_move_needed:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("======================================================")
                LOGGER.info(f"INFO    : {self.step}. COPYING/MOVING FILES TO OUTPUT FOLDER...")
                LOGGER.info("======================================================")
                LOGGER.info("")
                step_start_time = datetime.now()
                if self.ARGS['google-skip-gpth-tool']:
                    LOGGER.warning(f"WARNING : Metadata fixing with GPTH tool skipped ('-gsgt, --google-skip-gpth-tool' flag). step {self.step}b is needed to copy files manually to output folder.")
                if self.ARGS['google-ignore-check-structure']:
                    LOGGER.warning(f"WARNING : Flag to Ignore Google Takeout Structure detected. step {self.step}b is needed to copy/move files manually to output folder.")
                if self.ARGS['google-move-takeout-folder']:
                    LOGGER.info("INFO    : Moving files from Takeout folder to Output folder...")
                else:
                    LOGGER.info("INFO    : Copying files from Takeout folder to Output folder...")

                Utils.copy_move_folder(input_folder, output_takeout_folder,
                                       ignore_patterns=['*.json', '*.j'],
                                       move=self.ARGS['google-move-takeout-folder'])
                if self.ARGS['google-move-takeout-folder']:
                    Utils.force_remove_directory(input_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step}b completed in {formatted_duration}.")

            # step 4: Sync .MP4 live pictures timestamp
            self.step += 1
            LOGGER.info("")
            LOGGER.info("========================================================================")
            LOGGER.info(f"INFO    : {self.step}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
            LOGGER.info("========================================================================")
            LOGGER.info("")
            step_start_time = datetime.now()
            LOGGER.info("INFO    : Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
            Utils.sync_mp4_timestamps_with_images(output_takeout_folder)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
            LOGGER.info("")
            LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")

            # step 5: Create Folders Year/Month or Year only structure
            if self.ARGS['google-albums-folders-structure'].lower() != 'flatten' or self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten' or (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                self.step += 1
                LOGGER.info("")
                LOGGER.info("====================================================")
                LOGGER.info(f"INFO    : {self.step}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
                LOGGER.info("====================================================")
                step_start_time = datetime.now()
                # For Albums
                if self.ARGS['google-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info("")
                    LOGGER.info(f"INFO    : Creating Folder structure '{self.ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
                    basedir = output_takeout_folder
                    type_structure = self.ARGS['google-albums-folders-structure']
                    exclude_subfolders = ['No-Albums']
                    Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders)

                # For No-Albums
                if self.ARGS['google-no-albums-folders-structure'].lower() != 'flatten':
                    LOGGER.info("")
                    LOGGER.info(f"INFO    : Creating Folder structure '{self.ARGS['google-no-albums-folders-structure'].lower()}' for 'No-Albums' folders...")
                    basedir = os.path.join(output_takeout_folder, 'No-Albums')
                    type_structure = self.ARGS['google-no-albums-folders-structure']
                    exclude_subfolders = []
                    Utils.organize_files_by_date(input_folder=basedir, type=type_structure, exclude_subfolders=exclude_subfolders)

                # If flatten
                if (self.ARGS['google-albums-folders-structure'].lower() == 'flatten' and self.ARGS['google-no-albums-folders-structure'].lower() == 'flatten'):
                    LOGGER.info("")
                    LOGGER.warning("WARNING : No argument '-gafs, --google-albums-folders-structure' and '-gnas, --google-no-albums-folders-structure' detected. All photos and videos will be flattened in their folders.")

                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")

            # step 6: Move albums
            if not self.ARGS['google-skip-move-albums']:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("====================================")
                LOGGER.info(f"INFO    : {self.step}. MOVING ALBUMS FOLDER...")
                LOGGER.info("====================================")
                LOGGER.info("")
                step_start_time = datetime.now()
                Utils.move_albums(output_takeout_folder, exclude_subfolder=['No-Albums', '@eaDir'])
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")
            else:
                LOGGER.warning("WARNING : Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")

            if not self.ARGS['google-skip-move-albums']:
                album_folder = os.path.join(output_takeout_folder, 'Albums')
                if os.path.isdir(album_folder):
                    valid_albums_found = Utils.count_valid_albums(album_folder)
            else:
                album_folder = output_takeout_folder
                if os.path.isdir(output_takeout_folder):
                    valid_albums_found = Utils.count_valid_albums(output_takeout_folder) - 1

            # step 7: Fix Broken Symbolic Links
            if self.ARGS['google-create-symbolic-albums']:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("=========================================================")
                LOGGER.info(f"INFO    : {self.step}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
                LOGGER.info("=========================================================")
                LOGGER.info("")
                LOGGER.info("INFO    : Fixing broken symbolic links. This step is needed after moving any Folder structure...")
                step_start_time = datetime.now()
                symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(output_takeout_folder)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")
            else:
                LOGGER.warning("WARNING : Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected).")

            # step 8: Remove Duplicates
            if self.ARGS['google-remove-duplicates-files']:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("====================================================")
                LOGGER.info(f"INFO    : {self.step}. REMOVING DUPLICATES IN OUTPUT_TAKEOUT_FOLDER...")
                LOGGER.info("====================================================")
                LOGGER.info("")
                LOGGER.info("INFO    : Removing duplicates from OUTPUT_TAKEOUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'No-Albums' folders)...")
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
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")

            # step 9: Rename Albums Folders based on content date
            if self.ARGS['google-rename-albums-folders']:
                self.step += 1
                LOGGER.info("")
                LOGGER.info("============================================================")
                LOGGER.info(f"INFO    : {self.step}. RENAMING ALBUMS FOLDERS BASED ON THEIR DATES...")
                LOGGER.info("============================================================")
                LOGGER.info("")
                LOGGER.info("INFO    : Renaming albums folders in <OUTPUT_TAKEOUT_FOLDER> based on their dates...")
                step_start_time = datetime.now()
                renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = rename_album_folders(input_folder=album_folder, exclude_subfolder=['No-Albums', '@eaDir'], log_level=logging.INFO)
                step_end_time = datetime.now()
                formatted_duration = str(timedelta(seconds=(step_end_time - step_start_time).seconds))
                LOGGER.info("")
                LOGGER.info(f"INFO    : step {self.step} completed in {formatted_duration}.")

            processing_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(processing_end_time - processing_start_time).seconds))
            LOGGER.info("")
            LOGGER.info("=========================================================================================================")
            LOGGER.info(f"INFO    : ✅ TAKEOUT PROCESSING FINISHED!!!")
            LOGGER.info(f"INFO    : Takeout Precessed Folder: '{output_takeout_folder}'.")
            LOGGER.info("")
            LOGGER.info(f"INFO    : Total Processing Time   :  {formatted_duration}.")
            LOGGER.info("=========================================================================================================")

            # At the end of the process, we call the super() to make this objet an sub-instance of the class ClassLocalFolder to create the same folder structure
            super().__init__(output_takeout_folder)

            # return (valid_albums_found, symlink_fixed, symlink_not_fixed, duplicates_found, initial_takeout_numfiles, removed_empty_folders, renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged)
            return ProcessingResult(
                initial_takeout_numfiles=initial_takeout_numfiles,
                initial_takeout_total_images=initial_takeout_total_images,
                initial_takeout_total_videos=initial_takeout_total_videos,
                initial_takeout_total_sidecars=initial_takeout_total_sidecars,
                initial_takeout_total_metadatas=initial_takeout_total_metadatas,
                initial_takeout_total_supported_files=initial_takeout_total_supported_files,
                initial_takeout_total_not_supported_files=initial_takeout_total_not_supported_files,
                valid_albums_found=valid_albums_found,
                symlink_fixed=symlink_fixed,
                symlink_not_fixed=symlink_not_fixed,
                duplicates_found=duplicates_found,
                removed_empty_folders=removed_empty_folders,
                renamed_album_folders=renamed_album_folders,
                duplicates_album_folders=duplicates_album_folders,
                duplicates_albums_fully_merged=duplicates_albums_fully_merged,
                duplicates_albums_not_fully_merged=duplicates_albums_not_fully_merged,
            )



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
    result = takeout.process("Output_Takeout_Folder", capture_output=True, capture_errors=True, log_level=logging.DEBUG)
    print(result)
