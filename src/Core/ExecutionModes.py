import logging
import os
import shutil
import sys
from datetime import datetime, timedelta

from Core import GlobalVariables as GV
from Core.CustomLogger import set_log_level
from Features import AutoRenameAlbumsFolders as REN_ALB
from Features.AutomaticMigration.AutomaticMigration import mode_AUTOMATIC_MIGRATION
from Features.Duplicates.Duplicates import find_duplicates, process_duplicates_actions
from Features.GoogleTakeout.ClassTakeoutFolder import ClassTakeoutFolder
from Features.ImmichPhotos.ClassImmichPhotos import ClassImmichPhotos
from Features.SynologyPhotos.ClassSynologyPhotos import ClassSynologyPhotos

DEFAULT_DUPLICATES_ACTION = False
EXECUTION_MODE = "default"
terminal_width = shutil.get_terminal_size().columns

# -------------------------------------------------------------
# Determine the Execution mode based on the provide arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():
    # AUTOMATIC-MIGRATION MODE:
    if GV.ARGS['source'] and GV.ARGS['target']:
        EXECUTION_MODE = 'AUTOMATIC-MIGRATION'

        if LOG_LEVEL in [logging.DEBUG, VERBOSE_LEVEL_NUM]:
            step_name = ''
            # Configura y arranca el profiler justo antes de la llamada que quieres medir
            GV.LOGGER.debug(f"{step_name}Profiling Function mode_AUTOMATIC_MIGRATION")
            Utils.profile_and_print(mode_AUTOMATIC_MIGRATION, show_dashboard=False, show_gpth_info=GV.ARGS['show-gpth-info'], step_name=step_name)
        else:
            mode_AUTOMATIC_MIGRATION(show_gpth_info=GV.ARGS['show-gpth-info'])

    # Google Photos Mode:
    # elif "-gTakeout" in sys.argv or "--google-takeout" in sys.argv:
    elif GV.ARGS['google-takeout']:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()


    # Synology/Immich Photos Modes:
    elif GV.ARGS['upload-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to upload (default albums_to_upload='all')
        EXECUTION_MODE = 'upload-albums'
        mode_cloud_upload_albums(client=GV.ARGS['client'])
    elif GV.ARGS['upload-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'upload-all'
        mode_cloud_upload_ALL(client=GV.ARGS['client'])
    elif GV.ARGS['download-albums'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time. Need to add an argument to specify wich albums to download (default albums_to_download='all')
        EXECUTION_MODE = 'download-albums'
        mode_cloud_download_albums(client=GV.ARGS['client'])
    elif GV.ARGS['download-all'] != "":
        # TODO: Launch this with -AUTO MODE and compare execution time
        EXECUTION_MODE = 'download-all'
        mode_cloud_download_ALL(client=GV.ARGS['client'])
    elif GV.ARGS['remove-albums']:
        EXECUTION_MODE = 'remove-albums'
        mode_cloud_remove_albums_by_name_pattern(client=GV.ARGS['client'])
    elif GV.ARGS['rename-albums']:
        EXECUTION_MODE = 'rename-albums'
        mode_cloud_rename_albums(client=GV.ARGS['client'])
    elif GV.ARGS['remove-empty-albums']:
        EXECUTION_MODE = 'remove-empty-albums'
        mode_cloud_remove_empty_albums(client=GV.ARGS['client'])
    elif GV.ARGS['remove-duplicates-albums']:
        EXECUTION_MODE = 'remove-duplicates-albums'
        mode_cloud_remove_duplicates_albums(client=GV.ARGS['client'])
    elif GV.ARGS['merge-duplicates-albums']:
        EXECUTION_MODE = 'merge-duplicates-albums'
        mode_cloud_merge_duplicates_albums(client=GV.ARGS['client'])
    elif GV.ARGS['remove-all-albums'] != "":
        EXECUTION_MODE = 'remove-all-albums'
        # mode_cloud_remove_all_albums(client=GV.ARGS['client'])
        mode_cloud_remove_albums_by_name_pattern(client=GV.ARGS['client'])
    elif GV.ARGS['remove-all-assets'] != "":
        EXECUTION_MODE = 'remove-all-assets'
        mode_cloud_remove_ALL(client=GV.ARGS['client'])
    elif GV.ARGS['remove-orphan-assets'] != "":
        EXECUTION_MODE = 'remove-orphan-assets'
        mode_cloud_remove_orphan_assets(client=GV.ARGS['client'])


    # Other Stand-alone Extra Features:
    elif GV.ARGS['fix-symlinks-broken'] != "":
        EXECUTION_MODE = 'fix-symlinks'
        mode_fix_symlinkgs()
    elif GV.ARGS['find-duplicates'] != ['list', '']:
        EXECUTION_MODE = 'find_duplicates'
        mode_find_duplicates()
    elif GV.ARGS['process-duplicates'] != "":
        EXECUTION_MODE = 'process-duplicates'
        mode_process_duplicates()
    elif GV.ARGS['rename-folders-content-based'] != "":
        EXECUTION_MODE = 'rename-folders-content-based'
        mode_folders_rename_content_based()

    else:
        EXECUTION_MODE = ''  # Opción por defecto si no se cumple ninguna condición
        GV.LOGGER.error(f"Unable to detect any valid execution mode.")
        GV.LOGGER.error(f"Please, run '{os.path.basename(sys.argv[0])} --help' to know more about how to invoke the Script.")
        GV.LOGGER.error(f"")
        # PARSER.print_help()
        sys.exit(1)

###################################
# FEATURE: GOOGLE PHOTOS TAKEOUT: #
###################################
def mode_google_takeout(user_confirmation=True, log_level=None):
    # Configure default arguments for mode_google_takeout() execution
    GV.LOGGER.info(f"=============================================================")
    GV.LOGGER.info(f"Starting Google Takeout Photos Processor Feature...")
    GV.LOGGER.info(f"=============================================================")
    GV.LOGGER.info(f"")

    # Create the Object
    takeout = ClassTakeoutFolder(GV.ARGS['google-takeout'])

    input_folder = GV.ARGS['google-takeout']
    if GV.ARGS['output-folder']:
        OUTPUT_TAKEOUT_FOLDER = GV.ARGS['output-folder']
    else:
        OUTPUT_TAKEOUT_FOLDER = f"{GV.ARGS['google-takeout']}_{GV.ARGS['google-output-folder-suffix']}_{GV.TIMESTAMP}"

    if not Utils.dir_exists(input_folder):
        GV.LOGGER.error(f"The Input Folder {input_folder} does not exists. Exiting...")
        sys.exit(-1)
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        GV.ARGS['google-input-zip-folder'] = input_folder
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"ZIP files have been detected in {input_folder}'. Files will be unziped first...")

    # Mensajes informativos
    GV.LOGGER.info(f"")
    GV.LOGGER.info(f"Folders for Google Takeout Photos Feature:")
    GV.LOGGER.info(f"-------------------------------------------")
    if GV.ARGS['google-input-zip-folder']:
        GV.LOGGER.info(f"Input Takeout folder (zipped detected)   : '{GV.ARGS['google-input-zip-folder']}'")
        GV.LOGGER.info(f"Input Takeout will be unzipped to folder : '{input_folder}_unzipped_{GV.TIMESTAMP}'")
    else:
        GV.LOGGER.info(f"Input Takeout folder                     : '{GV.ARGS['google-takeout']}'")
    GV.LOGGER.info(f"Output Takeout folder                    : '{OUTPUT_TAKEOUT_FOLDER}'")
    GV.LOGGER.info(f"")

    GV.LOGGER.info(f"Settings for Google Takeout Photos Feature:")
    GV.LOGGER.info(f"-------------------------------------------")
    GV.LOGGER.info(f"Using Suffix                             : '{GV.ARGS['google-output-folder-suffix']}'")
    GV.LOGGER.info(f"Albums Folder Structure                  : '{GV.ARGS['google-albums-folders-structure']}'")
    GV.LOGGER.info(f"No Albums Folder Structure               : '{GV.ARGS['google-no-albums-folders-structure']}'")
    GV.LOGGER.info(f"Creates symbolic links for Albums        : '{GV.ARGS['google-create-symbolic-albums']}'")
    GV.LOGGER.info(f"Ignore Check Google Takeout Structure    : '{GV.ARGS['google-ignore-check-structure']}'")
    GV.LOGGER.info(f"Move Original Assets to Output Folder    : '{GV.ARGS['google-move-takeout-folder']}'")
    GV.LOGGER.info(f"Remove Duplicates files in Output folder : '{GV.ARGS['google-remove-duplicates-files']}'")
    GV.LOGGER.info(f"Rename Albums folders in Output folder   : '{GV.ARGS['google-rename-albums-folders']}'")
    GV.LOGGER.info(f"Skip Extra Assets (-edited,-effects...)  : '{GV.ARGS['google-skip-extras-files']}'")
    GV.LOGGER.info(f"Skip Moving Albums to 'Albums' folder    : '{GV.ARGS['google-skip-move-albums']}'")
    GV.LOGGER.info(f"Skip GPTH Tool                           : '{GV.ARGS['google-skip-gpth-tool']}'")
    GV.LOGGER.info(f"Show GPTH Progress                       : '{GV.ARGS['show-gpth-info']}'")
    GV.LOGGER.info(f"Show GPTH Errors                         : '{GV.ARGS['show-gpth-errors']}'")
    GV.LOGGER.info(f"")

    if user_confirmation:
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        GV.LOGGER.warning(GV.HELP_TEXTS["google-photos-takeout"].replace('<TAKEOUT_FOLDER>',f"'{GV.ARGS['google-takeout']}'"))
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            GV.LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        if GV.ARGS['google-input-zip-folder']=="":
            GV.LOGGER.warning(f"No argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if GV.ARGS['google-albums-folders-structure'].lower()!='flatten':
            GV.LOGGER.warning(f"Flag detected '-gafs, --google-albums-folders-structure'. Folder structure '{GV.ARGS['google-albums-folders-structure']}' will be applied on each Album folder...")
        if GV.ARGS['google-no-albums-folders-structure'].lower()!='year/month':
            GV.LOGGER.warning(f"Flag detected '-gnaf, --google-no-albums-folders-structure'. Folder structure '{GV.ARGS['google-no-albums-folders-structure']}' will be applied on 'No-Albums' folder (Photos without Albums)...")
        if GV.ARGS['google-skip-gpth-tool']:
            GV.LOGGER.warning(f"Flag detected '-gsgt, --google-skip-gpth-tool'. Skipping Processing photos with GPTH Tool...")
        if GV.ARGS['google-skip-extras-files']:
            GV.LOGGER.warning(f"Flag detected '-gsef, --google-skip-extras-files'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if GV.ARGS['google-skip-move-albums']:
            GV.LOGGER.warning(f"Flag detected '-gsma, --google-skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if GV.ARGS['google-create-symbolic-albums']:
            GV.LOGGER.warning(f"Flag detected '-gcsa, --google-create-symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if GV.ARGS['google-ignore-check-structure']:
            GV.LOGGER.warning(f"Flag detected '-gics, --google-ignore-check-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if GV.ARGS['google-move-takeout-folder']:
            GV.LOGGER.warning(f"Flag detected '-gmtf, --google-move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_TAKEOUT_FOLDER>...")
        if GV.ARGS['google-remove-duplicates-files']:
            GV.LOGGER.warning(f"Flag detected '-grdf, --google-remove-duplicates-files'. All duplicates files within OUTPUT_TAKEOUT_FOLDER will be removed after fixing them...")
        if GV.ARGS['google-rename-albums-folders']:
            GV.LOGGER.warning(f"Flag detected '-graf, --google-rename-albums-folders'. All albums subfolders within OUTPUT_TAKEOUT_FOLDER will be renamed after fixing them based on their content data...")
        if GV.ARGS['no-log-file']:
            GV.LOGGER.warning(f"Flag detected '-noLog, --no-log-file'. Skipping saving output into log file...")

        # Call the Function
        result = takeout.process(output_folder=OUTPUT_TAKEOUT_FOLDER, capture_output=GV.ARGS['show-gpth-info'], capture_errors=GV.ARGS['show-gpth-errors'], print_messages=True, create_localfolder_object=False, log_level=log_level)
        # result = takeout.process(capture_output=GV.ARGS['show-gpth-info'], capture_errors=GV.ARGS['show-gpth-errors'], print_messages=True, create_localfolder_object=False, log_level=log_level)

        # print result for debugging
        if GV.LOG_LEVEL == logging.DEBUG:
            Utils.print_dict_pretty(asdict(result))

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
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        if result['output_counters']['total_files'] == 0:
            # FINAL SUMMARY
            GV.LOGGER.info(f"")
            GV.LOGGER.error(f"=====================================================")
            GV.LOGGER.error(f"            PROCESS COMPLETED WITH ERRORS!           ")
            GV.LOGGER.error(f"=====================================================")
            GV.LOGGER.info(f"")
            GV.LOGGER.error(f"No files found in Output Folder  : '{OUTPUT_TAKEOUT_FOLDER}'")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
            GV.LOGGER.info(f"============================================================================================================================")
            GV.LOGGER.info(f"")
        else:
            # FINAL SUMMARY
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"============================================================================================================================")
            GV.LOGGER.info(f"PROCESS COMPLETED SUCCESSFULLY!")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"All the Photos/Videos Fixed can be found on folder: '{OUTPUT_TAKEOUT_FOLDER}'")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"FINAL SUMMARY & STATISTICS:")
            GV.LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            GV.LOGGER.info(f"Total Size of Takeout folder                : {result['input_counters']['total_size_mb']} MB")
            GV.LOGGER.info(f"Total Files in Takeout folder               : {result['input_counters']['total_files']:<7}")
            GV.LOGGER.info(f"Total Non-Supported files in Takeout folder : {result['input_counters']['unsupported_files']:<7}")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"Total Supported files in Takeout folder     : {result['input_counters']['supported_files']:<7}")
            GV.LOGGER.info(f"  - Total Media files in Takeout folder     : {result['input_counters']['media_files']:<7}")
            GV.LOGGER.info(f"    - Total Images in Takeout folder        : {result['input_counters']['photo_files']:<7}")
            GV.LOGGER.info(f"      - Correct Date                        : {result['input_counters']['photos']['with_date']:<7} ({result['input_counters']['photos']['pct_with_date']:>5.1f}% of total photos) ")
            GV.LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['photos']['without_date']:<7} ({result['input_counters']['photos']['pct_without_date']:>5.1f}% of total photos) ")
            GV.LOGGER.info(f"    - Total Videos in Takeout folder        : {result['input_counters']['video_files']:<7}")
            GV.LOGGER.info(f"      - Correct Date                        : {result['input_counters']['videos']['with_date']:<7} ({result['input_counters']['videos']['pct_with_date']:>5.1f}% of total videos) ")
            GV.LOGGER.info(f"      - Incorrect Date                      : {result['input_counters']['videos']['without_date']:<7} ({result['input_counters']['videos']['pct_without_date']:>5.1f}% of total videos) ")
            GV.LOGGER.info(f"  - Total Non-Media files in Takeout folder : {result['input_counters']['non_media_files']:<7}")
            GV.LOGGER.info(f"    - Total Metadata in Takeout folder      : {result['input_counters']['metadata_files']:<7}")
            GV.LOGGER.info(f"    - Total Sidecars in Takeout folder      : {result['input_counters']['sidecar_files']:<7}")
            GV.LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            GV.LOGGER.info(f"Total Size of Output folder                 : {result['output_counters']['total_size_mb']} MB")
            GV.LOGGER.info(f"Total Files in Output folder                : {result['output_counters']['total_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_files:>5})  |  ({perc_of_input_total_files:>5.1f}% of input) ")
            GV.LOGGER.info(f"Total Non-Supported files in Output folder  : {result['output_counters']['unsupported_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_unsupported_files:>5})  |  ({perc_of_input_total_unsupported_files:>5.1f}% of input) ")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"Total Supported files in Output folder      : {result['output_counters']['supported_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_supported_files:>5})  |  ({perc_of_input_total_supported_files:>5.1f}% of input) ")
            GV.LOGGER.info(f"  - Total Media files in Output folder      : {result['output_counters']['media_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_media:>5})  |  ({perc_of_input_total_media:>5.1f}% of input) ")
            GV.LOGGER.info(f"    - Total Images in Output folder         : {result['output_counters']['photo_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_images:>5})  |  ({perc_of_input_total_images:>5.1f}% of input) ")
            GV.LOGGER.info(f"      - Correct Date                        : {result['output_counters']['photos']['with_date']:<7}" f" {f'({output_perc_photos_with_date:>5.1f}% of total photos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_photos_with_date:>5})  |  ({perc_of_input_total_photos_with_date:>5.1f}% of input)'.rjust(40)} ")
            GV.LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['photos']['without_date']:<7}" f" {f'({output_perc_photos_without_date:>5.1f}% of total photos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_photos_without_date:>5})  |  ({perc_of_input_total_photos_without_date:>5.1f}% of input)'.rjust(40)} ")
            GV.LOGGER.info(f"    - Total Videos in Output folder         : {result['output_counters']['video_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_videos:>5})  |  ({perc_of_input_total_videos:>5.1f}% of input) ")
            GV.LOGGER.info(f"      - With Date                           : {result['output_counters']['videos']['with_date']:<7}" f" {f'({output_perc_videos_with_date:>5.1f}% of total videos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_videos_with_date:>5})  |  ({perc_of_input_total_videos_with_date:>5.1f}% of input)'.rjust(40)} ")
            GV.LOGGER.info(f"      - Incorrect Date                      : {result['output_counters']['videos']['without_date']:<7}" f" {f'({output_perc_videos_without_date:>5.1f}% of total videos)'.ljust(30)}" f"{f'|   (diff: {diff_output_input_total_videos_without_date:>5})  |  ({perc_of_input_total_videos_without_date:>5.1f}% of input)'.rjust(40)} ")
            GV.LOGGER.info(f"  - Total Non-Media files in Output folder  : {result['output_counters']['non_media_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_non_media:>5})  |  ({perc_of_input_total_non_media:>5.1f}% of input) ")
            GV.LOGGER.info(f"    - Total Metadata in Output folder       : {result['output_counters']['metadata_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_metadata:>5})  |  ({perc_of_input_total_metadata:>5.1f}% of input) ")
            GV.LOGGER.info(f"    - Total Sidecars in Output folder       : {result['output_counters']['sidecar_files']:<7} {''.ljust(30)} |   (diff: {diff_output_input_total_sidecars:>5})  |  ({perc_of_input_total_sidecars:>5.1f}% of input) ")
            GV.LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            GV.LOGGER.info(f"Total Albums folders found in Output folder : {result['valid_albums_found']}")
            if GV.ARGS['google-rename-albums-folders']:
                GV.LOGGER.info(f"Total Albums Renamed                        : {result['renamed_album_folders']}")
                GV.LOGGER.info(f"Total Albums Duplicated                     : {result['duplicates_album_folders']}")
                GV.LOGGER.info(f"   - Total Albums Fully Merged              : {result['duplicates_albums_fully_merged']}")
                GV.LOGGER.info(f"   - Total Albums Not Fully Merged          : {result['duplicates_albums_not_fully_merged']}")
            if GV.ARGS['google-create-symbolic-albums']:
                GV.LOGGER.info(f"")
                GV.LOGGER.info(f"Total Symlinks Fixed                        : {result['symlink_fixed']}")
                GV.LOGGER.info(f"Total Symlinks Not Fixed                    : {result['symlink_not_fixed']}")
            if GV.ARGS['google-remove-duplicates-files']:
                GV.LOGGER.info(f"")
                GV.LOGGER.info(f"Total Duplicates Removed                    : {result['duplicates_found']}")
                GV.LOGGER.info(f"Total Empty Folders Removed                 : {result['removed_empty_folders']}")
            GV.LOGGER.info(f"")
            GV.LOGGER.info(f"Total time elapsed                          : {formatted_duration}")
            GV.LOGGER.info(f"----------------------------------------------------------------------------------------------------------------------------")
            GV.LOGGER.info(f"============================================================================================================================")
            GV.LOGGER.info(f"")


#############################
# SYNOLOGY/IMMICH FEATURES: #
#############################
def mode_cloud_upload_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    input_folder = GV.ARGS['upload-albums']
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Argument detected  : '-uAlb, --upload-albums'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["upload-albums"].replace('<ALBUMS_FOLDER>', f"'{GV.ARGS['upload-albums']}'"))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"Reading Configuration file and Login into {client} Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        GV.LOGGER.info(f"Find Albums in Folder    : {input_folder}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client_obj.push_albums(input_folder=input_folder, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        GV.LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        GV.LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        GV.LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        GV.LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets                            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        GV.LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        GV.LOGGER.info(f"Total Assets skipped (Duplicated)       : {total_dupplicated_assets_skipped}")
        GV.LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        GV.LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        GV.LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        GV.LOGGER.info(f"Total Empty Albums removed              : {total_empty_albums_removed}")
        GV.LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        GV.LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_upload_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    input_folder = GV.ARGS['upload-all']
    albums_folders = GV.ARGS['albums-folders']
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Argument detected  : '-uAll, --upload-all'.")
    if albums_folders:
        GV.LOGGER.info(f"Argument detected  : '-AlbFolder, --albums-folders'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["upload-all"].replace('<INPUT_FOLDER>', f"{input_folder}"))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Upload ALL' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        GV.LOGGER.info(f"Uploading Assets in Folder    : {input_folder}")
        # Call the Function
        total_albums_uploaded, total_albums_skipped, total_assets_uploaded, total_assets_uploaded_within_albums, total_assets_uploaded_without_albums, duplicates_assets_removed, total_dupplicated_assets_skipped = cloud_client_obj.push_ALL(input_folder=input_folder, albums_folders=albums_folders, remove_duplicates=False, log_level=logging.WARNING)
        # After Upload Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        GV.LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        GV.LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        GV.LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute merge_duplicates_assets
        GV.LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets                            : {total_assets_uploaded + total_dupplicated_assets_skipped}")
        GV.LOGGER.info(f"Total Assets uploaded                   : {total_assets_uploaded}")
        GV.LOGGER.info(f"Total Assets skipped (Duplicated)       : {total_dupplicated_assets_skipped}")
        GV.LOGGER.info(f"Total Assets added to Albums            : {total_assets_uploaded_within_albums}")
        GV.LOGGER.info(f"Total Assets added without Albums       : {total_assets_uploaded_without_albums}")
        GV.LOGGER.info(f"Total Albums uploaded                   : {total_albums_uploaded}")
        GV.LOGGER.info(f"Total Albums skipped                    : {total_albums_skipped}")
        GV.LOGGER.info(f"Total Empty Albums removed              : {total_empty_albums_removed}")
        GV.LOGGER.info(f"Total Duplicated Albums removed         : {total_duplicates_albums_removed}")
        GV.LOGGER.info(f"Total Duplicated Assets removed         : {duplicates_assets_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_download_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    albums_name = GV.ARGS['download-albums']
    output_folder = GV.ARGS['output-folder']
    albums_str = ", ".join(albums_name)

    GV.LOGGER.info(f"Client detected  : '{client} Photos'.")
    GV.LOGGER.info(f"Argument detected    : '-dAlb, --download-albums {albums_str}'.")
    GV.LOGGER.info(f"Albums to extract: {albums_name}")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["download-albums"].replace("<ALBUMS_NAME>", albums_str).replace("<OUTPUT_FOLDER>", output_folder))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Client not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Removing Empty Albums...")
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute mode_merge_duplicates_albums
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Merging Duplicates Albums...")
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Removing Duplicates Assets...")
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded = cloud_client_obj.pull_albums(albums_name=albums_name, output_folder=output_folder, log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        GV.LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_download_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    output_folder = GV.ARGS['download-all']
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Argument detected  : 'dAll, --download-all'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["download-all"].replace('<OUTPUT_FOLDER>', output_folder))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Before to Download Assets/Albums from Immich Photos, we will perform a clean-up of the database removing, Empty Albums, Duplicates Albums and Duplicates Assets
        GV.LOGGER.info(f"Cleaning-up {client} Photos account (Removing Empty/Duplicates Albums and Duplicates Assets)...")
        # Execute mode_remove_empty_albums
        total_empty_albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # Execute merge_duplicates_albums
        total_duplicates_albums_removed = cloud_client_obj.merge_duplicates_albums(request_user_confirmation=False, log_level=logging.WARNING)
        # Execute remove_duplicates_assets
        duplicates_assets_removed = cloud_client_obj.remove_duplicates_assets(log_level=logging.WARNING)
        # Call the Function
        albums_downloaded, assets_downloaded, total_assets_downloaded_within_albums, total_assets_downloaded_without_albums = cloud_client_obj.pull_ALL(output_folder=output_folder, log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
        GV.LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
        GV.LOGGER.info(f"Total Assets downloaded within albums   : {total_assets_downloaded_within_albums}")
        GV.LOGGER.info(f"Total Assets downloaded without albums  : {total_assets_downloaded_without_albums}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_empty_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-rEmpAlb, --remove-empty-albums'.")
    GV.LOGGER.info(f"The Tool will look for any empty album in your {client} Photos account and will remove them (if any empty album is found).")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-empty-albums"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Remove Empty Album' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client_obj.remove_empty_albums(log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Empty Albums removed              : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_duplicates_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-rDupAlb, --remove-duplicates-albums'.")
    GV.LOGGER.info(f"The Tool will look for any duplicated album (based on assets counts and assets size) in your {client} Photos account and will remove them (if any duplicated album is found).")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-duplicates-albums"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Remove Duplicates Album' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed = cloud_client_obj.remove_duplicates_albums(log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Duplicates Albums removed         : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_merge_duplicates_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-mDupAlb, --merge-duplicates-albums'.")
    GV.LOGGER.info(f"The Tool will look for any duplicated album in your {client} Photos account, merge their content into the most relevant one, and remove the duplicates.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["merge-duplicates-albums"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Merge Duplicates Album' Mode detected. Only this module will be run!!!")

        # Login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)

        # Call the Function using 'count' as strategy (you can change to 'size')
        albums_removed = cloud_client_obj.merge_duplicates_albums(strategy='count', log_level=logging.INFO)

        # Logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)

        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Duplicate Albums merged and removed : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                        : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_orphan_assets(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-rOrphan, --remove-orphan-assets'.")

    if client.lower() == 'synology':
        GV.LOGGER.warning(f"This feature is not available for {client} Photos. Exiting program.")
        sys.exit(0)

    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-orphan-assets"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Remove Orphan Assets' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed = cloud_client_obj.remove_orphan_assets(user_confirmation=False, log_level=logging.WARNING)
        #logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Orphan Assets removed             : {assets_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_ALL(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-rAll, --remove-all-assets'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-all-assets"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Remove ALL Assets' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        assets_removed, albums_removed = cloud_client_obj.remove_all_assets(log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        GV.LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_rename_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    albums_name_pattern = GV.ARGS['rename-albums'][0]
    albums_name_replacement_pattern = GV.ARGS['rename-albums'][1]
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Argument detected  : '-renAlb, --rename-albums'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["rename-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern).replace('<ALBUMS_NAME_REPLACEMENT_PATTERN>',albums_name_replacement_pattern))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Rename Albums' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_renamed = cloud_client_obj.rename_albums(pattern=albums_name_pattern, pattern_to_replace=albums_name_replacement_pattern, log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Albums renamed                    : {albums_renamed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_albums_by_name_pattern(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    if GV.ARGS['remove-all-albums'] != "":
        albums_name_pattern = '.*'
    else:
        albums_name_pattern = GV.ARGS['remove-albums']

    remove_albums_assets = GV.ARGS['remove-albums-assets']
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Argument detected  : '-rAlb, --remove-albums'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-albums"].replace('<ALBUMS_NAME_PATTERN>', albums_name_pattern))
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
    if remove_albums_assets:
        GV.LOGGER.info(f"Flag detected  : '-rAlbAsset, --remove-albums-assets'.")
        GV.LOGGER.info(f"Since, flag '-rAlbAsset, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        GV.LOGGER.info(f"")

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Delete Albums' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into Immich Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client_obj.remove_albums_by_name(pattern=albums_name_pattern, removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        GV.LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_cloud_remove_all_albums(client=None, user_confirmation=True, log_level=None):
    client = Utils.capitalize_first_letter(client)
    remove_albums_assets = GV.ARGS['remove-albums-assets']
    GV.LOGGER.info(f"Client detected: '{client} Photos' (Account ID={GV.ARGS['account-id']}).")
    GV.LOGGER.info(f"Flag detected  : '-rAllAlb, --remove-all-albums'.")
    GV.LOGGER.warning('\n' + '-' * terminal_width)
    GV.LOGGER.warning(GV.HELP_TEXTS["remove-all-albums"])
    GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
    if remove_albums_assets:
        GV.LOGGER.info(f"Flag detected  : '-rAlbAsset, --remove-albums-assets'.")
        GV.LOGGER.info(f"Since, flag '-rAlbAsset, --remove-albums-assets' have been detected, ALL the Assets associated to any removed Albums will also be removed.")
        GV.LOGGER.info(f"")

    if user_confirmation and not Utils.confirm_continue():
        GV.LOGGER.info(f"Exiting program.")
        sys.exit(0)

    # Create the cloud_client_obj Object
    if client.lower() == 'immich':
        cloud_client_obj = ClassImmichPhotos(account_id=GV.ARGS['account-id'])
    elif client.lower() == 'synology':
        cloud_client_obj = ClassSynologyPhotos(account_id=GV.ARGS['account-id'])
    else:
        GV.LOGGER.info(f"Cloud service not valid ({client}). Valid clients are ['immich', 'synology']. Exiting program.")
        sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"{client} Photos: 'Delete ALL Albums' Mode detected. Only this module will be run!!!")
        # login
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Reading Configuration file and Login into {client} Photos...")
        cloud_client_obj.login(log_level=logging.WARNING)
        # Call the Function
        albums_removed, assets_removed = cloud_client_obj.remove_all_albums(removeAlbumsAssets=remove_albums_assets, log_level=logging.WARNING)
        # logout
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Logged out from {client} Photos.")
        cloud_client_obj.logout(log_level=logging.WARNING)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Assets removed                    : {assets_removed}")
        GV.LOGGER.info(f"Total Albums removed                    : {albums_removed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


#################################
# OTHER STANDALONE FEATURES: #
#################################
def mode_fix_symlinkgs(user_confirmation=True, log_level=None):
    if user_confirmation:
        GV.LOGGER.warning('\n' + '-' * terminal_width)
        GV.LOGGER.warning(GV.HELP_TEXTS["fix-symlinks-broken"].replace('<FOLDER_TO_FIX>', f"'{GV.ARGS['fix-symlinks-broken']}'"))
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            GV.LOGGER.info(f"Exiting program.")
            sys.exit(0)
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"Fixing broken symbolic links Mode detected. Only this module will be run!!!")
        GV.LOGGER.info(f"Fixing broken symbolic links in folder '{GV.ARGS['fix-symlinks-broken']}'...")
        symlinks_fixed, symlinks_not_fixed = FixSymLinks.fix_symlinks_broken(GV.ARGS['fix-symlinks-broken'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Fixed Symbolic Links              : {symlinks_fixed}")
        GV.LOGGER.info(f"Total No Fixed Symbolic Links           : {symlinks_not_fixed}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_find_duplicates(user_confirmation=True, log_level=None):
    GV.LOGGER.info(f"Duplicates Action             : {GV.ARGS['duplicates-action']}")
    GV.LOGGER.info(f"Find Duplicates in Folders    : {GV.ARGS['duplicates-folders']}")
    GV.LOGGER.info(f"")
    if user_confirmation:
        GV.LOGGER.warning('\n' + '-' * terminal_width)
        GV.LOGGER.warning(GV.HELP_TEXTS["find-duplicates"].replace('<DUPLICATES_FOLDER>', f"'{GV.ARGS['duplicates-folders']}'"))
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            GV.LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            GV.LOGGER.warning(f"Detected Argument '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            GV.LOGGER.warning("")
        duplicates_files_found, removed_empty_folders = find_duplicates(duplicates_action=GV.ARGS['duplicates-action'], duplicates_folders=GV.ARGS['duplicates-folders'], deprioritize_folders_patterns=GV.DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            GV.LOGGER.error(f"Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exist.")
            sys.exit(-1)
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Duplicates Found                  : {duplicates_files_found}")
        GV.LOGGER.info(f"Total Empty Folders Removed             : {removed_empty_folders}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_process_duplicates(user_confirmation=True, log_level=None):
    if user_confirmation:
        GV.LOGGER.warning('\n' + '-' * terminal_width)
        GV.LOGGER.warning(GV.HELP_TEXTS["process-duplicates"])
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            GV.LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"Argument detected '-procDup, --process-duplicates'. The Tool will process the '{GV.ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
        GV.LOGGER.info(f"Processing Duplicates Files based on Actions given in {os.path.basename(GV.ARGS['process-duplicates'])} file...")
        removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(GV.ARGS['process-duplicates'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Removed Duplicates                : {removed_duplicates}")
        GV.LOGGER.info(f"Total Restored Duplicates               : {restored_duplicates}")
        GV.LOGGER.info(f"Total Replaced Duplicates               : {replaced_duplicates}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")


def mode_folders_rename_content_based(user_confirmation=True, log_level=None):
    if user_confirmation:
        GV.LOGGER.warning('\n' + '-' * terminal_width)
        GV.LOGGER.warning(GV.HELP_TEXTS["rename-folders-content-based"].replace('<ALBUMS_FOLDER>', f"'{GV.ARGS['rename-folders-content-based']}'"))
        GV.LOGGER.warning('\n' + '-' * (terminal_width-11))
        if not Utils.confirm_continue():
            GV.LOGGER.info(f"Exiting program.")
            sys.exit(0)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        GV.LOGGER.info(f"Rename Albums Mode detected. Only this module will be run!!!")
        GV.LOGGER.info(f"Argument detected '-ra, --rename-folders-content-based'. The Tool will look for any Subfolder in '{GV.ARGS['rename-folders-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
        renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = REN_ALB.rename_album_folders(GV.ARGS['rename-folders-content-based'])
        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=round((end_time - GV.START_TIME).total_seconds())))
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"         PROCESS COMPLETED SUCCESSFULLY!          ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"                  FINAL SUMMARY:                  ")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"Total Albums folders renamed             : {renamed_album_folders}")
        GV.LOGGER.info(f"Total Albums folders duplicated          : {duplicates_album_folders}")
        GV.LOGGER.info(f"Total Albums duplicated fully merged     : {duplicates_albums_fully_merged}")
        GV.LOGGER.info(f"Total Albums duplicated not fully merged : {duplicates_albums_not_fully_merged}")
        GV.LOGGER.info(f"")
        GV.LOGGER.info(f"Total time elapsed                       : {formatted_duration}")
        GV.LOGGER.info(f"==================================================")
        GV.LOGGER.info(f"")
