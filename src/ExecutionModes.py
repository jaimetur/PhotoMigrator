from GlobalVariables import LOGGER, ARGS, TIMESTAMP, START_TIME, HELP_TEXTS, DEPRIORITIZE_FOLDERS_PATTERNS, SCRIPT_DESCRIPTION
import os, sys
from datetime import datetime, timedelta
import Utils
import logging
import time
import shutil
from dataclasses import asdict
from CustomLogger import set_log_level
from Duplicates import find_duplicates, process_duplicates_actions
from ClassTakeoutFolder import ClassTakeoutFolder
from ClassSynologyPhotos import ClassSynologyPhotos
from ClassImmichPhotos import ClassImmichPhotos
from AutomaticMigration import mode_AUTOMATIC_MIGRATION

DEFAULT_DUPLICATES_ACTION = False
EXECUTION_MODE = "default"
terminal_width = shutil.get_terminal_size().columns

# -------------------------------------------------------------
# Determine the Execution mode based on the provide arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():
    # AUTOMATIC-MIGRATION MODE:
    if ARGS['source'] and ARGS['target']:
        EXECUTION_MODE = 'AUTOMATIC-MIGRATION'

        if LOG_LEVEL in [logging.DEBUG, VERBOSE_LEVEL_NUM]:
            step_name = ''
            # Configura y arranca el profiler justo antes de la llamada que quieres medir
            LOGGER.debug(f"{step_name}Profiling Function mode_AUTOMATIC_MIGRATION")
            initial_takeout_counters = Utils.profile_and_print(mode_AUTOMATIC_MIGRATION, show_dashboard=False, show_gpth_info=ARGS['show-gpth-info'], step_name=step_name)
        else:
            mode_AUTOMATIC_MIGRATION(show_gpth_info=ARGS['show-gpth-info'])

    # Google Photos Mode:
    # elif "-gTakeout" in sys.argv or "--google-takeout" in sys.argv:
    elif ARGS['google-takeout']:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()


    # Synology/Immich Photos Modes:
    elif ARGS['upload-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to upload (default albums_to_upload='all')
        EXECUTION_MODE = 'upload-albums'
        mode_cloud_upload_albums(client=ARGS['client'])
    elif ARGS['upload-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'upload-all'
        mode_cloud_upload_ALL(client=ARGS['client'])
    elif ARGS['download-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to download (default albums_to_download='all')
        EXECUTION_MODE = 'download-albums'
        mode_cloud_download_albums(client=ARGS['client'])
    elif ARGS['download-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'download-all'
        mode_cloud_download_ALL(client=ARGS['client'])
    elif ARGS['remove-albums']:
        EXECUTION_MODE = 'remove-albums'
        mode_cloud_remove_albums_by_name_pattern(client=ARGS['client'])
    elif ARGS['rename-albums']:
        EXECUTION_MODE = 'rename-albums'
        mode_cloud_rename_albums(client=ARGS['client'])
    elif ARGS['remove-empty-albums']:
        EXECUTION_MODE = 'remove-empty-albums'
        mode_cloud_remove_empty_albums(client=ARGS['client'])
    elif ARGS['remove-duplicates-albums']:
        EXECUTION_MODE = 'remove-duplicates-albums'
        mode_cloud_remove_duplicates_albums(client=ARGS['client'])
    elif ARGS['merge-duplicates-albums']:
        EXECUTION_MODE = 'merge-duplicates-albums'
        mode_cloud_merge_duplicates_albums(client=ARGS['client'])
    elif ARGS['remove-all-albums'] != "":
        EXECUTION_MODE = 'remove-all-albums'
        # mode_cloud_remove_all_albums(client=ARGS['client'])
        mode_cloud_remove_albums_by_name_pattern(client=ARGS['client'])
    elif ARGS['remove-all-assets'] != "":
        EXECUTION_MODE = 'remove-all-assets'
        mode_cloud_remove_ALL(client=ARGS['client'])
    elif ARGS['remove-orphan-assets'] != "":
        EXECUTION_MODE = 'remove-orphan-assets'
        mode_cloud_remove_orphan_assets(client=ARGS['client'])


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
        LOGGER.error(f"Unable to detect any valid execution mode.")
        LOGGER.error(f"Please, run '{os.path.basename(sys.argv[0])} --help' to know more about how to invoke the Script.")
        LOGGER.error(f"")
        # PARSER.print_help()
        sys.exit(1)

###################################
# FEATURE: GOOGLE PHOTOS TAKEOUT: #
###################################
def mode_google_takeout(user_confirmation=True, log_level=None):
    def print_result_pretty(result):
        for key, value in result.items():
            print(f"{key:35}: {value}")

    # Configure default arguments for mode_google_takeout() execution
    LOGGER.info(f"=============================================================")
    LOGGER.info(f"Starting Google Takeout Photos Processor Feature...")
    LOGGER.info(f"=============================================================")
    LOGGER.info(f"")

    # Create the Object
    takeout = ClassTakeoutFolder(ARGS['google-takeout'])

    input_folder = ARGS['google-takeout']
    if ARGS['output-folder']:
        OUTPUT_TAKEOUT_FOLDER = ARGS['output-folder']
    else:
        OUTPUT_TAKEOUT_FOLDER = f"{ARGS['google-takeout']}_{ARGS['google-output-folder-suffix']}_{TIMESTAMP}"

    if not Utils.dir_exists(input_folder):
        LOGGER.error(f"The Input Folder {input_folder} does not exists. Exiting...")
        sys.exit(-1)
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        ARGS['google-input-zip-folder'] = input_folder
        LOGGER.info(f"")
        LOGGER.info(f"ZIP files have been detected in {input_folder}'. Files will be unziped first...")

    # Mensajes informativos
    LOGGER.info(f"")
    LOGGER.info(f"Folders for Google Takeout Photos Feature:")
    LOGGER.info(f"-------------------------------------------")
    if ARGS['google-input-zip-folder']:
        LOGGER.info(f"Input Takeout folder (zipped detected)   : '{ARGS['google-input-zip-folder']}'")
        LOGGER.info(f"Input Takeout will be unzipped to folder : '{input_folder}_unzipped_{TIMESTAMP}'")
    else:
        LOGGER.info(f"Input Takeout folder                     : '{ARGS['google-takeout']}'")
    LOGGER.info(f"Output Takeout folder                    : '{OUTPUT_TAKEOUT_FOLDER}'")
    LOGGER.info(f"")

    LOGGER.info(f"Settings for Google Takeout Photos Feature:")
    LOGGER.info(f"-------------------------------------------")
    LOGGER.info(f"Using Suffix                             : '{ARGS['google-output-folder-suffix']}'")
    LOGGER.info(f"Albums Folder Structure                  : '{ARGS['google-albums-folders-structure']}'")
    LOGGER.info(f"No Albums Folder Structure               : '{ARGS['google-no-albums-folders-structure']}'")
    LOGGER.info(f"Creates symbolic links for Albums        : '{ARGS['google-create-symbolic-albums']}'")
    LOGGER.info(f"Ignore Check Google Takeout Structure    : '{ARGS['google-ignore-check-structure']}'")
    LOGGER.info(f"Move Original Assets to Output Folder    : '{ARGS['google-move-takeout-folder']}'")
    LOGGER.info(f"Remove Duplicates files in Output folder : '{ARGS['google-remove-duplicates-files']}'")
    LOGGER.info(f"Rename Albums folders in Output folder   : '{ARGS['google-rename-albums-folders']}'")
    LOGGER.info(f"Skip Extra Assets (-edited,-effects...)  : '{ARGS['google-skip-extras-files']}'")
    LOGGER.info(f"Skip Moving Albums to 'Albums' folder    : '{ARGS['google-skip-move-albums']}'")
    LOGGER.info(f"Skip GPTH Tool                           : '{ARGS['google-skip-gpth-tool']}'")
    LOGGER.info(f"Show GPTH Progress                       : '{ARGS['show-gpth-info']}'")
    LOGGER.info(f"Show GPTH Errors                         : '{ARGS['show-gpth-errors']}'")
    LOGGER.info(f"")

    if user_confirmation:
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        LOGGER.warning(HELP_TEXTS["google-photos-takeout"].replace('<TAKEOUT_FOLDER>',f"'{ARGS['google-takeout']}'"))
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        if ARGS['google-input-zip-folder']=="":
            LOGGER.warning(f"No argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if ARGS['google-albums-folders-structure'].lower()!='flatten':
            LOGGER.warning(f"Flag detected '-gafs, --google-albums-folders-structure'. Folder structure '{ARGS['google-albums-folders-structure']}' will be applied on each Album folder...")
        if ARGS['google-no-albums-folders-structure'].lower()!='year/month':
            LOGGER.warning(f"Flag detected '-gnaf, --google-no-albums-folders-structure'. Folder structure '{ARGS['google-no-albums-folders-structure']}' will be applied on 'No-Albums' folder (Photos without Albums)...")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"Flag detected '-gsgt, --google-skip-gpth-tool'. Skipping Processing photos with GPTH Tool...")
        if ARGS['google-skip-extras-files']:
            LOGGER.warning(f"Flag detected '-gsef, --google-skip-extras-files'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if ARGS['google-skip-move-albums']:
            LOGGER.warning(f"Flag detected '-gsma, --google-skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.warning(f"Flag detected '-gcsa, --google-create-symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning(f"Flag detected '-gics, --google-ignore-check-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if ARGS['google-move-takeout-folder']:
            LOGGER.warning(f"Flag detected '-gmtf, --google-move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_TAKEOUT_FOLDER>...")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.warning(f"Flag detected '-grdf, --google-remove-duplicates-files'. All duplicates files within OUTPUT_TAKEOUT_FOLDER will be removed after fixing them...")
        if ARGS['google-rename-albums-folders']:
            LOGGER.warning(f"Flag detected '-graf, --google-rename-albums-folders'. All albums subfolders within OUTPUT_TAKEOUT_FOLDER will be renamed after fixing them based on their content data...")
        if ARGS['no-log-file']:
            LOGGER.warning(f"Flag detected '-noLog, --no-log-file'. Skipping saving output into log file...")

        # Call the Function
        result = takeout.process(output_folder=OUTPUT_TAKEOUT_FOLDER, capture_output=ARGS['show-gpth-info'], capture_errors=ARGS['show-gpth-errors'], print_messages=True, create_localfolder_object=False, log_level=log_level)
        # result = takeout.process(capture_output=ARGS['show-gpth-info'], capture_errors=ARGS['show-gpth-errors'], print_messages=True, create_localfolder_object=False, log_level=log_level)

        # print result for debugging
        # print_result_pretty(asdict(result))

        # Extract percentages of totals
        output_perc_photos_with_date = result['output_counters']['photos']['pct_with_date']
        output_perc_photos_without_date = result['output_counters']['photos']['pct_without_date']
        output_perc_videos_with_date = result['output_counters']['videos']['pct_with_date']
        output_perc_videos_without_date = result['output_counters']['videos']['pct_without_date']

        # Calculate percentages from output vs input
        perc_of_input_total_files               = 100 * result['output_counters']['total_files']           / result['input_counters']['total_files']             if result['input_counters']['total_files']           != 0 and result['output_counters']['total_files']           != 0 else 100
        perc_of_input_total_unsupported_files   = 100 * result['output_counters']['unsupported_files']     / result['input_counters']['unsupported_files']       if result['input_counters']['unsupported_files']     != 0 and result['output_counters']['unsupported_files']     != 0 else 100
        perc_of_input_total_supported_files     = 100 * result['output_counters']['supported_files']       / result['input_counters']['supported_files']         if result['input_counters']['supported_files']       != 0 and result['output_counters']['supported_files']       != 0 else 100
        perc_of_input_total_media               = 100 * result['output_counters']['media_files']           / result['input_counters']['media_files']             if result['input_counters']['media_files']           != 0 and result['output_counters']['media_files']           != 0 else 100
        perc_of_input_total_images              = 100 * result['output_counters']['photo_files']           / result['input_counters']['photo_files']             if result['input_counters']['photo_files']           != 0 and result['output_counters']['photo_files']           != 0 else 100
        perc_of_input_total_photos_with_date    = 100 * result['output_counters']['photos']['with_date']   / result['input_counters']['photos']['with_date']     if result['input_counters']['photos']['with_date']   != 0 and result['output_counters']['photos']['with_date']   != 0 else 100
        perc_of_input_total_photos_without_date = 100 * result['output_counters']['photos']['without_date']/ result['input_counters']['photos']['without_date']  if result['input_counters']['photos']['without_date']!= 0 and result['output_counters']['photos']['without_date']!= 0 else 100
        perc_of_input_total_videos              = 100 * result['output_counters']['video_files']           / result['input_counters']['video_files']             if result['input_counters']['video_files']           != 0 and result['output_counters']['video_files']           != 0 else 100
        perc_of_input_total_videos_with_date    = 100 * result['output_counters']['videos']['with_date']   / result['input_counters']['videos']['with_date']     if result['input_counters']['videos']['with_date']   != 0 and result['output_counters']['videos']['with_date']   != 0 else 100
        perc_of_input_total_videos_without_date = 100 * result['output_counters']['videos']['without_date']/ result['input_counters']['videos']['without_date']  if result['input_counters']['videos']['without_date']!= 0 and result['output_counters']['videos']['without_date']!= 0 else 100
        perc_of_input_total_non_media           = 100 * result['output_counters']['non_media_files']       / result['input_counters']['non_media_files']         if result['input_counters']['non_media_files']       != 0 and result['output_counters']['non_media_files']       != 0 else 100
        perc_of_input_total_metadata            = 100 * result['output_counters']['metadata_files']        / result['input_counters']['metadata_files']          if result['input_counters']['metadata_files']        != 0 and result['output_counters']['metadata_files']        != 0 else 100
        perc_of_input_total_sidecars            = 100 * result['output_counters']['sidecar_files']         / result['input_counters']['sidecar_files']           if result['input_counters']['sidecar_files']         != 0 and result['output_counters']['sidecar_files']         != 0 else 100

        # Calculate differences from output vs input
        diff_output_input_total_files               = result['output_counters']['total_files']           - result['input_counters']['total_files']              if result['input_counters']['total_files']           != 0 and result['output_counters']['total_files']           != 0 else 0
        diff_output_input_total_unsupported_files   = result['output_counters']['unsupported_files']     - result['input_counters']['unsupported_files']        if result['input_counters']['unsupported_files']     != 0 and result['output_counters']['unsupported_files']     != 0 else 0
        diff_output_input_total_supported_files     = result['output_counters']['supported_files']       - result['input_counters']['supported_files']          if result['input_counters']['supported_files']       != 0 and result['output_counters']['supported_files']       != 0 else 0
        diff_output_input_total_media               = result['output_counters']['media_files']           - result['input_counters']['media_files']              if result['input_counters']['media_files']           != 0 and result['output_counters']['media_files']           != 0 else 0
        diff_output_input_total_images              = result['output_counters']['photo_files']           - result['input_counters']['photo_files']              if result['input_counters']['photo_files']           != 0 and result['output_counters']['photo_files']           != 0 else 0
        diff_output_input_total_photos_with_date    = result['output_counters']['photos']['with_date']   - result['input_counters']['photos']['with_date']      if result['input_counters']['photos']['with_date']   != 0 and result['output_counters']['photos']['with_date']   != 0 else 0
        diff_output_input_total_photos_without_date = result['output_counters']['photos']['without_date']- result['input_counters']['photos']['without_date']   if result['input_counters']['photos']['without_date']!= 0 and result['output_counters']['photos']['without_date']!= 0 else 0
        diff_output_input_total_videos              = result['output_counters']['video_files']           - result['input_counters']['video_files']              if result['input_counters']['video_files']           != 0 and result['output_counters']['video_files']           != 0 else 0
        diff_output_input_total_videos_with_date    = result['output_counters']['videos']['with_date']   - result['input_counters']['videos']['with_date']      if result['input_counters']['videos']['with_date']   != 0 and result['output_counters']['videos']['with_date']   != 0 else 0
        diff_output_input_total_videos_without_date = result['output_counters']['videos']['without_date']- result['input_counters']['videos']['without_date']   if result['input_counters']['videos']['without_date']!= 0 and result['output_counters']['videos']['without_date']!= 0 else 0
        diff_output_input_total_non_media           = result['output_counters']['non_media_files']       - result['input_counters']['non_media_files']          if result['input_counters']['non_media_files']       != 0 and result['output_counters']['non_media_files']       != 0 else 0
        diff_output_input_total_metadata            = result['output_counters']['metadata_files']        - result['input_counters']['metadata_files']           if result['input_counters']['metadata_files']        != 0 and result['output_counters']['metadata_files']        != 0 else 0
        diff_output_input_total_sidecars            = result['output_counters']['sidecar_files']         - result['input_counters']['sidecar_files']            if result['input_counters']['sidecar_files']         != 0 and result['output_counters']['sidecar_files']         != 0 else 0

        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        if result['output_counters']['total_files'] == 0:
            # FINAL SUMMARY
            LOGGER.info(f"")
            LOGGER.error(f"=====================================================")
            LOGGER.error(f"            PROCESS COMPLETED WITH ERRORS!           ")
            LOGGER.error(f"=====================================================")
            LOGGER.info(f"")
            LOGGER.error(f"No files found in Output Folder  : '{OUTPUT_TAKEOUT_FOLDER}'")
            LOGGER.info(f"")
            LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
            LOGGER.info(f"============================================================================================================================")
            LOGGER.info(f"")
        else:
            # FINAL SUMMARY
            LOGGER.info(f"")
            LOGGER.info(f"============================================================================================================================")
            LOGGER.info(f"PROCESS COMPLETED SUCCESSFULLY!")
            LOGGER.info(f"")
            LOGGER.info(f"All the Photos/Videos Fixed can be found on folder: '{OUTPUT_TAKEOUT_FOLDER}'")
            LOGGER.info(f"")
            LOGGER.info(f"FINAL SUMMARY & STATISTICS:")
            LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            LOGGER.info(f"Total Size of Takeout folder                : {result['input_counters']['total_size_mb']} MB")
            LOGGER.info(f"Total Files in Takeout folder               : {result['input_counters']['total_files']:<7}")
            LOGGER.info(f"Total Non-Supported files in Takeout folder : {result['input_counters']['unsupported_files']:<7}")
            LOGGER.info(f"")
            LOGGER.info(f"Total Supported files in Takeout folder     : {result['input_counters']['supported_files']:<7}")
            LOGGER.info(f"  - Total Media files in Takeout folder     : {result['input_counters']['media_files']:<7}")
            LOGGER.info(f"    - Total Images in Takeout folder        : {result['input_counters']['photo_files']:<7}")
            LOGGER.info(f"      - Correct Date                        : {result['input_counters']['photos']['with_date']:<7} ({result['input_counters']['photos']['pct_with_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['photos']['without_date']:<7} ({result['input_counters']['photos']['pct_without_date']:>5.1f}% of total photos) ")
            LOGGER.info(f"    - Total Videos in Takeout folder        : {result['input_counters']['video_files']:<7}")
            LOGGER.info(f"      - Correct Date                        : {result['input_counters']['videos']['with_date']:<7} ({result['input_counters']['videos']['pct_with_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['videos']['without_date']:<7} ({result['input_counters']['videos']['pct_without_date']:>5.1f}% of total videos) ")
            LOGGER.info(f"  - Total Non-Media files in Takeout folder : {result['input_counters']['non_media_files']:<7}")
            LOGGER.info(f"    - Total Metadata in Takeout folder      : {result['input_counters']['metadata_files']:<7}")
            LOGGER.info(f"    - Total Sidecars in Takeout folder      : {result['input_counters']['sidecar_files']:<7}")
            LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            LOGGER.info(f"Total Size of Output folder                 : {result['output_counters']['total_size_mb']} MB")
            LOGGER.info(f"Total Files in Output folder                : {result['output_counters']['total_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_files:>5})  |  ({perc_of_input_total_files:>5.1f}% of input) ")
            LOGGER.info(f"Total Non-Supported files in Output folder  : {result['output_counters']['unsupported_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_unsupported_files:>5})  |  ({perc_of_input_total_unsupported_files:>5.1f}% of input) ")
            LOGGER.info(f"")
            LOGGER.info(f"Total Supported files in Output folder      : {result['output_counters']['supported_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_supported_files:>5})  |  ({perc_of_input_total_supported_files:>5.1f}% of input) ")
            LOGGER.info(f"  - Total Media files in Output folder      : {result['output_counters']['media_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_media:>5})  |  ({perc_of_input_total_media:>5.1f}% of input) ")
            LOGGER.info(f"    - Total Images in Output folder         : {result['output_counters']['photo_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_images:>5})  |  ({perc_of_input_total_images:>5.1f}% of input) ")
            LOGGER.info(f"      - Correct Date                        : {result['output_counters']['photos']['with_date']:<7}" f" {f'({output_perc_photos_with_date:>5.1f}% of total photos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_photos_with_date:>5})  |  ({perc_of_input_total_photos_with_date:>5.1f}% of input)'.rjust(40)} ")
            LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['photos']['without_date']:<7}" f" {f'({output_perc_photos_without_date:>5.1f}% of total photos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_photos_without_date:>5})  |  ({perc_of_input_total_photos_without_date:>5.1f}% of input)'.rjust(40)} ")
            LOGGER.info(f"    - Total Videos in Output folder         : {result['output_counters']['video_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_videos:>5})  |  ({perc_of_input_total_videos:>5.1f}% of input) ")
            LOGGER.info(f"      - With Date                           : {result['output_counters']['videos']['with_date']:<7}" f" {f'({output_perc_videos_with_date:>5.1f}% of total videos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_videos_with_date:>5})  |  ({perc_of_input_total_videos_with_date:>5.1f}% of input)'.rjust(40)} ")
            LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['videos']['without_date']:<7}" f" {f'({output_perc_videos_without_date:>5.1f}% of total videos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_videos_without_date:>5})  |  ({perc_of_input_total_videos_without_date:>5.1f}% of input)'.rjust(40)} ")
            LOGGER.info(f"  - Total Non-Media files in Output folder  : {result['output_counters']['non_media_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_non_media:>5})  |  ({perc_of_input_total_non_media:>5.1f}% of input) ")
            LOGGER.info(f"    - Total Metadata in Output folder       : {result['output_counters']['metadata_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_metadata:>5})  |  ({perc_of_input_total_metadata:>5.1f}% of input) ")
            LOGGER.info(f"    - Total Sidecars in Output folder       : {result['output_counters']['sidecar_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_sidecars:>5})  |  ({perc_of_input_total_sidecars:>5.1f}% of input) ")
            LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            LOGGER.info(f"")
            LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            LOGGER.info(f"Total Albums folders found in Output folder : {result['valid_albums_found']}")
            if ARGS['google-rename-albums-folders']:
                LOGGER.info(f"Total Albums Renamed                        : {result['renamed_album_folders']}")
                LOGGER.info(f"Total Albums Duplicated                     : {result['duplicates_album_folders']}")
                LOGGER.info(f"   - Total Albums Fully Merged              : {result['duplicates_albums_fully_merged']}")
                LOGGER.info(f"   - Total Albums Not Fully Merged          : {result['duplicates_albums_not_fully_merged']}")
            if ARGS['google-create-symbolic-albums']:
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


#############################
# SYNOLOGY/IMMICH FEATURES: #
#############################
def mode_cloud_upload_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    input_folder = ARGS['upload-albums']
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Argument detected  : '-uAlb, --upload-albums'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["upload-albums"].replace('<ALBUMS_FOLDER>', f"'{ARGS['upload-albums']}'"))
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"Reading Configuration file and Login into {client} Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        LOGGER.info(f"Find Albums in Folder    : {input_folder}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client_obj.push_albums(input_folder=input_folder, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Assets                            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        LOGGER.info(f"Total Assets skipped (Duplicated)       : {total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        LOGGER.info(f"Total Empty Albums removed              : {total_empty_albums_removed}")
        LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_upload_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    input_folder = ARGS['upload-all']
    albums_folders = ARGS['albums-folders']
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Argument detected  : '-uAll, --upload-all'.")
    if albums_folders:
        LOGGER.info(f"Argument detected  : '-AlbFolder, --albums-folders'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["upload-all"].replace('<INPUT_FOLDER>', f"{input_folder}"))
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        LOGGER.info(f"Uploading Assets in Folder    : {input_folder}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client_obj.push_ALL(input_folder=input_folder, albums_folders=albums_folders, remove_duplicates=False, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute merge_duplicates_assets
        LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
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
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_download_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    albums_name = ARGS['download-albums']
    output_folder = ARGS['output-folder']
    albums_str = ", ".join(albums_name)

    LOGGER.info(f"Client detected  : '{client} Photos'.")
    LOGGER.info(f"Argument detected    : '-dAlb, --download-albums {albums_str}'.")
    LOGGER.info(f"Albums to extract: {albums_name}")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["download-albums"].replace("<ALBUMS_NAME>", albums_str).replace("<OUTPUT_FOLDER>", output_folder))
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"")
        LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        LOGGER.info(f"")
        LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        LOGGER.info(f"")
        LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        LOGGER.info(f"")
        LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded = cloud_client_obj.pull_albums(albums_name=albums_name, output_folder=output_folder, log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_download_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    output_folder = ARGS['download-all']
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Argument detected  : 'dAll, --download-all'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["download-all"].replace('<OUTPUT_FOLDER>', output_folder))
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute merge_duplicates_albums
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums = cloud_client_obj.pull_ALL(output_folder=output_folder, log_level=logging.WARNING)
        # logout
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        LOGGER.info(f"Total Assets downloaded within albums   : {total_assets_downloaded_within_albums}")
        LOGGER.info(f"Total Assets downloaded without albums  : {total_assets_downloaded_without_albums}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_empty_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-rEmpAlb, --remove-empty-albums'.")
    LOGGER.info(f"The Tool will look for any empty album in your {client} Photos account and will remove them (if any empty album is found).")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-empty-albums"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Remove Empty Album' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Empty Albums removed              : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_duplicates_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-rDupAlb, --remove-duplicates-albums'.")
    LOGGER.info(f"The Tool will look for any duplicated album (based on assets counts and assets size) in your {client} Photos account and will remove them (if any duplicated album is found).")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-duplicates-albums"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Remove Duplicates Album' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client_obj.remove_duplicates_albums(log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Duplicates Albums removed         : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_merge_duplicates_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-mDupAlb, --merge-duplicates-albums'.")
    LOGGER.info(f"The Tool will look for any duplicated album in your {client} Photos account, merge their content into the most relevant one, and remove the duplicates.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["merge-duplicates-albums"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Merge Duplicates Album' Mode detected. Only this module will be run!!!")

        # Login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)

        # Call the Function using 'count' as strategy (you can change to 'size')
        albums_removed = cloud_client_obj.merge_duplicates_albums(strategy='count', log_level=logging.INFO)

        # Logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)

        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Duplicate Albums merged and removed : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                        : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_orphan_assets(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-rOrphan, --remove-orphan-assets'.")

    if client.lower() == 'synology':
        LOGGER.warning(f"This feature is not available for {client} Photos. Exiting program.")
        sys.exit(0)

    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-orphan-assets"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Remove Orphan Assets' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed = cloud_client_obj.remove_orphan_assets(user_confirmation=False, log_level=logging.WARNING)
        #logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Orphan Assets removed             : {assets_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-rAll, --remove-all-assets'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-all-assets"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Remove ALL Assets' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed, albums_removed = cloud_client_obj.remove_all_assets(log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_rename_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    albums_name_pattern = ARGS['rename-albums'][0]
    albums_name_replacement_pattern = ARGS['rename-albums'][1]
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Argument detected  : '-renAlb, --rename-albums'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["rename-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern).replace('<ALBUMS_NAME_REPLACEMENT_PATTERN>',albums_name_replacement_pattern))
    LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Rename Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_renamed = cloud_client_obj.rename_albums(pattern=albums_name_pattern, pattern_to_replace=albums_name_replacement_pattern, log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Albums renamed                    : {albums_renamed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_albums_by_name_pattern(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    if ARGS['remove-all-albums'] != "":
        albums_name_pattern = '.*'
    else:
        albums_name_pattern = ARGS['remove-albums']

    remove_albums_assets = ARGS['remove-albums-assets']
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Argument detected  : '-rAlb, --remove-albums'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern))
    LOGGER.warning('\n' + '-' * (terminal_width-11))
    if remove_albums_assets:
        LOGGER.info(f"Flag detected  : '-rAlbAsset, --remove-albums-assets'.")
        LOGGER.info(f"Since, flag '-rAlbAsset, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        LOGGER.info(f"")

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Delete Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client_obj.remove_albums_by_name(pattern=albums_name_pattern, removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_cloud_remove_all_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    remove_albums_assets = ARGS['remove-albums-assets']
    LOGGER.info(f"Client detected: '{client} Photos' (Account ID={ARGS['account-id']}).")
    LOGGER.info(f"Flag detected  : '-rAllAlb, --remove-all-albums'.")
    LOGGER.warning('\n' + '-' * terminal_width)
    LOGGER.warning(HELP_TEXTS["remove-all-albums"])
    LOGGER.warning('\n' + '-' * (terminal_width-11))
    if remove_albums_assets:
        LOGGER.info(f"Flag detected  : '-rAlbAsset, --remove-albums-assets'.")
        LOGGER.info(f"Since, flag '-rAlbAsset, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        LOGGER.info(f"")

    if user_confirmation and not Utils.confirm_continue():
        LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=ARGS['account-id'])
    else:
        LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"{client} Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
        # login
        LOGGER.info(f"")
        LOGGER.info(f"Reading Configuration file and Login into {client} Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client_obj.remove_all_albums(removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        LOGGER.info(f"")
        LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


#################################
# OTHER STANDALONE FEATURES: #
#################################
def mode_fix_symlinkgs(user_confirmation=True, log_level=None):
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["fix-symlinks-broken"].replace('<FOLDER_TO_FIX>', f"'{ARGS['fix-symlinks-broken']}'"))
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)
    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Fixing broken symbolic links Mode detected. Only this module will be run!!!")
        LOGGER.info(f"Fixing broken symbolic links in folder '{ARGS['fix-symlinks-broken']}'...")
        symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(ARGS['fix-symlinks-broken'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Fixed Symbolic Links              : {symlinks_fixed}")
        LOGGER.info(f"Total No Fixed Symbolic Links           : {symlinks_not_fixed}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_find_duplicates(user_confirmation=True, log_level=None):
    LOGGER.info(f"Duplicates Action             : {ARGS['duplicates-action']}")
    LOGGER.info(f"Find Duplicates in Folders    : {ARGS['duplicates-folders']}")
    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["find-duplicates"].replace('<DUPLICATES_FOLDER>', f"'{ARGS['duplicates-folders']}'"))
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"Detected Argument '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
        duplicates_files_found, removed_empty_folders = find_duplicates(duplicates_action=ARGS['duplicates-action'], duplicates_folders=ARGS['duplicates-folders'], deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            LOGGER.error(f"Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exist.")
            sys.exit(-1)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Duplicates Found                  : {duplicates_files_found}")
        LOGGER.info(f"Total Empty Folders Removed             : {removed_empty_folders}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_process_duplicates(user_confirmation=True, log_level=None):
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["process-duplicates"])
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Argument detected '-procDup, --process-duplicates'. The Tool will process the '{ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
        LOGGER.info(f"Processing Duplicates Files based on Actions given in {os.path.basename(ARGS['process-duplicates'])} file...")
        removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(ARGS['process-duplicates'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Removed Duplicates                : {removed_duplicates}")
        LOGGER.info(f"Total Restored Duplicates               : {restored_duplicates}")
        LOGGER.info(f"Total Replaced Duplicates               : {replaced_duplicates}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")


def mode_folders_rename_content_based(user_confirmation=True, log_level=None):
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info(f"")
    LOGGER.info(f"===================")
    LOGGER.info(f"STARTING PROCESS...")
    LOGGER.info(f"===================")
    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.warning('\n' + '-' * terminal_width)
        LOGGER.warning(HELP_TEXTS["rename-folders-content-based"].replace('<ALBUMS_FOLDER>', f"'{ARGS['rename-folders-content-based']}'"))
        LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(LOGGER, log_level):  # Change Log Level to log_level for this function
        LOGGER.info(f"Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"Argument detected '-ra, --rename-folders-content-based'. The Tool will look for any Subfolder in '{ARGS['rename-folders-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
        renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(ARGS['rename-folders-content-based'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - START_TIME).total_seconds())))
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"                  FINAL SUMMARY:                  ")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"Total Albums folders renamed             : {renamed_album_folders}")
        LOGGER.info(f"Total Albums folders duplicated          : {duplicates_album_folders}")
        LOGGER.info(f"Total Albums duplicated fully merged     : {duplicates_albums_fully_merged}")
        LOGGER.info(f"Total Albums duplicated not fully merged : {duplicates_albums_not_fully_merged}")
        LOGGER.info(f"")
        LOGGER.info(f"Total time elapsed                       : {formatted_duration}")
        LOGGER.info(f"==================================================")
        LOGGER.info(f"")
