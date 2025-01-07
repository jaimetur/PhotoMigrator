import os
import argparse
import platform
from datetime import datetime, timedelta
import Utils

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v1.2.2"
SCRIPT_DATE         = "2024-12-02"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos (remove duplicates, 
fix metadata, organize per year/month folder, and separate Albums).
(c) by Jaime Tur (@jaimetur)
"""

# Detect the operating system
current_os = platform.system()

# Determine the script name based on the OS
if current_os == "Linux":
    print ("Script running on Linux system")
elif current_os == "Darwin":
    print ("Script running on MacOS system")
elif current_os == "Windows":
    print ("Script running on Windows system")
else:
    print(f"Unsupported operating system: {current_os}")



if __name__ == "__main__":
    def parse_arguments():
        parser = argparse.ArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=Utils.WideHelpFormatter,  # Aplica el formatter
        )
        parser.add_argument("-z",  "--zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
        parser.add_argument("-t",  "--takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to unzip input files. Default: 'Takeout'")
        parser.add_argument("-s",  "--suffix", metavar="<SUFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
        parser.add_argument("-sg", "--skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool.")
        parser.add_argument("-sm", "--skip-move-albums", action="store_true", help="Skip moving albums to Albums folder.")
        parser.add_argument("-fa", "--flatten-albums", action="store_true", help="Flatten photos/videos within each album folder.")
        parser.add_argument("-fn", "--flatten-no-albums", action="store_true", help="Flatten photos/videos within ALL_PHOTOS folder.")
        parser.add_argument("-it", "--ignore-takeout-structure", action="store_true", help="Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.")
        parser.add_argument("-nl", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")
        parser.add_argument("-re", "--run-exif-tool", action="store_true", help="Run EXIF Tool files processing in the last step. (Useful if GPTH Tool cannot fix some files, but is a slow process). RECOMMENDATION: Use only if after runnning normal process with GPTH Tool, you still have many files with no date.")
        parser.add_argument("-mt", "--move-takeout-folder", action="store_true", help="Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>.       CAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!. Use only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
        args = parser.parse_args()
        args.zip_folder = args.zip_folder.rstrip('/\\')
        args.takeout_folder = args.takeout_folder.rstrip('/\\')
        args.suffix = args.suffix.lstrip('_')
        return args

def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')
    args = parse_arguments()

    # Create timestamp, start_time and define output_folder
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_time = datetime.now()
    output_folder = f"{args.takeout_folder}_{args.suffix}_{timestamp}"

    # Set a global variable for logger and Set up logger based on the skip-log argument
    global logger
    log_filename=f"execution_log_{timestamp}"
    log_folder="Logs"
    log_folder_filename = os.path.join(log_folder,log_filename+'.log')
    logger = Utils.logger_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=args.no_log_file, plain_log=False)

    logger.info(SCRIPT_DESCRIPTION)
    logger.info("")
    logger.info("====================")
    logger.info("STARTING PROCESS...")
    logger.info("====================")
    logger.info("")

    # Mensajes informativos
    if not args.zip_folder=="": logger.info(f"INFO: Using Zip folder     : '{args.zip_folder}'")
    logger.info(f"INFO: Using Takeout folder : '{args.takeout_folder}'")
    logger.info(f"INFO: Using Suffix         : '{args.suffix}'")
    logger.info(f"INFO: Using Output folder  : '{output_folder}'")
    if not args.no_log_file:
        logger.info(f"INFO: Execution Log file   : '{log_folder_filename}'")

    logger.info(f"")
    if args.zip_folder=="":
        logger.warning(f"WARNING: No argument '-z or --zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
    if args.move_takeout_folder:
        logger.warning(f"WARNING: Flag detected '-mt, --move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_FOLDER>...")
    if args.skip_gpth_tool:
        logger.warning(f"WARNING: Flag detected '-sg, --skip-gpth-toot'. Skipping Processing photos with GPTH Tool...")
    if args.skip_move_albums:
        logger.warning(f"WARNING: Flag detected '-sm, --skip-move-albums'. Skipping Moving Albums to Albums folder...")
    if args.flatten_albums:
        logger.warning(f"WARNING: Flag detected '-fa, --flatten-albums'. All files within each album folder will be flattened (without year/month folder structure)...")
    if args.flatten_no_albums:
        logger.warning(f"WARNING: Flag detected '-fn, --flatten-no-albums'. All files within ALL_PHOTOS folder will be flattened on ALL_PHOTOS folder (without year/month folder structure)...")
    if args.ignore_takeout_structure:
        logger.warning(f"WARNING: Flag detected '-it, --ignore-takeout-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
    if args.run_exif_tool:
        logger.warning(f"WARNING: Flag detected '-re, --run-exif-tool'. EXIF tool will be run in last step to try to fix photos metadata...")
    if args.no_log_file:
        logger.warning(f"WARNING: Flag detected '-sl, --skip-log'. Skipping saving output into log file...")

    # Step 1: Unzip files
    logger.info("")
    logger.info("==============================")
    logger.info("1. UNPACKING TAKEOUT FOLDER...")
    logger.info("==============================")
    logger.info("")
    if not args.zip_folder=="":
        step_start_time = datetime.now()
        Utils.unpack_zips(args.zip_folder, args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 1 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Unzipping skipped (no argument '-z or --zip-folder <ZIP_FOLDER>' given).")

    # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
    logger.info("INFO: Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
    Utils.delete_subfolders(args.takeout_folder, "@eaDir")

    # Step 2: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    logger.info("")
    logger.info("===========================================")
    logger.info("2. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    logger.info("===========================================")
    logger.info("")
    if not args.skip_gpth_tool:
        if args.ignore_takeout_structure:
            logger.warning("WARNING: Ignore Google Takeout Structure detected ('-it, --ignore-takeout-structure' flag detected).")
        step_start_time = datetime.now()
        # Change file extension from .MP4 to .mp4 because it seems that GPTH Tool does not process files with extension .MP4 (uppercase)
        # logger.info("INFO: Converting extension 'MP4' to 'mp4' to avoid GPTH Tool exclude those files...")
        # Utils.change_file_extension(args.takeout_folder, 'MP4', 'mp4')
        Utils.fix_metadata_with_gpth_tool(
            input_folder=args.takeout_folder,
            output_folder=output_folder,
            flatten_albums=args.flatten_albums,
            flatten_no_albums=args.flatten_no_albums,
            move_takeout_folder=args.move_takeout_folder,
            ignore_takeout_structure=args.ignore_takeout_structure
        )
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 2 completed in {formatted_duration}.")
    if args.skip_gpth_tool or args.ignore_takeout_structure:
        logger.info("")
        logger.info("=====================================")
        logger.info("2b. COPYING FILES TO OUTPUT FOLDER...")
        logger.info("=====================================")
        logger.info("")
        if args.skip_gpth_tool:
            logger.warning("WARNING: Metadata fixing with GPTH tool skipped ('-sg, --skip-gpth-tool' flag detected). Step 2b is needed to copy files manually to output folder.")
        elif args.ignore_takeout_structure:
            logger.info("INFO: Flag to Ignore Google Takeout Structure have been detected ('-it, --ignore-takeout-structure'). Step 2b is needed to copy files manually to output folder.")
        logger.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder (args.takeout_folder, output_folder, ignore_patterns=['*.json', '*.j'], move=args.move_takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 2b completed in {formatted_duration}.")

    # Step 3: Flatten Folders
    logger.info("")
    logger.info("========================")
    logger.info("3. FLATTENING FOLDERS...")
    logger.info("========================")
    logger.info("")
    if args.flatten_albums or args.flatten_no_albums:
        step_start_time = datetime.now()
        # Only flatten albums
        if args.flatten_albums and not args.flatten_no_albums:
            Utils.flatten_subfolders(input_folder=output_folder, exclude_subfolders=["ALL_PHOTOS"], max_depth=0, flatten_root_folder=False)
        # Only flatten no albums
        elif not args.flatten_albums and args.flatten_no_albums:
            Utils.flatten_subfolders(input_folder=os.path.join(output_folder, 'ALL_PHOTOS'), max_depth=1, flatten_root_folder=True)
        # If flatten both but gpth tool is not skipped, then the output of gpth tool is already flattened
        elif args.flatten_albums and args.flatten_no_albums and args.skip_gpth_tool:
            Utils.flatten_subfolders(input_folder=output_folder, exclude_subfolders=["ALL_PHOTOS"], max_depth=0, flatten_root_folder=False)
            Utils.flatten_subfolders(input_folder=os.path.join(output_folder, 'ALL_PHOTOS'), max_depth=1, flatten_root_folder=True)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 3 completed in {formatted_duration}.")
    # No flatten anything
    else:
        logger.warning("WARNING: Flattening skipped. No flatten arguments ('-fa, --flatten-albums' / '-fn, --flatten-no-albums') found.")

    # Step 4: Move albums
    logger.info("")
    logger.info("==========================")
    logger.info("4. MOVING ALBUMS FOLDER...")
    logger.info("==========================")
    logger.info("")
    if not args.skip_move_albums:
        step_start_time = datetime.now()
        Utils.move_albums(output_folder, exclude_subfolder=["ALL_PHOTOS", "@eaDir"])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 4 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --skip-move-albums' flag detected).")

    # Step 5: Fix metadata with EXIF Tool
    logger.info("")
    logger.info("===========================================")
    logger.info("5. FIXING PHOTOS METADATA WITH EXIF TOOL...")
    logger.info("===========================================")
    logger.info("")
    if args.run_exif_tool:
        step_start_time = datetime.now()
        Utils.fix_metadata_with_exif_tool(output_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step 5 completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Metadata fixing with EXIF tool skipped ('-re, --run-exif-tool' flag not detected).")

    # Step 6: Fix metadata with EXIF Tool
    logger.info("")
    logger.info("==============================================================")
    logger.info("6. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
    logger.info("==============================================================")
    logger.info("")
    step_start_time = datetime.now()
    # Change file extension from .MP4 to .mp4 because it seems that GPTH Tool does not process files with extension .MP4 (uppercase)
    logger.info("INFO: Fixing Timestamps of files '.MP4' with images files '.HEIC, .JPG, .JPEG' if they are in the same folders and have the same name (in those cases the .MP4 have been generated by Google Photos to reproduce the Live Content of the image file)...")
    Utils.sync_mp4_timestamps_with_images(output_folder)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    logger.info(f"INFO: Step 6 completed in {formatted_duration}.")

    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time-start_time).seconds))
    logger.info("")
    logger.info("==================================================")
    logger.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    logger.info("==================================================")
    logger.info("")
    logger.info("==================================================")
    logger.info("                  FINAL SUMMARY:                  ")
    logger.info("==================================================")
    logger.info(f"Total files in Takeout folder           : {Utils.count_files_in_folder(args.takeout_folder)}")
    logger.info(f"Total files processed by GPTH/EXIF TooL : {Utils.count_files_in_folder(output_folder)}")
    albums_found = 0
    if not args.skip_move_albums:
        album_folder = os.path.join(output_folder, 'Albums')
        if os.path.isdir(album_folder):
            albums_found = len(os.listdir(album_folder))
    else:
        if os.path.isdir(output_folder):
            albums_found = len(os.listdir(output_folder))-1
    logger.info(f"Total Albums folders found              : {albums_found}")

    logger.info("")
    logger.info(f"Total time elapsed                      : {formatted_duration}")
    logger.info("==================================================")
    logger.info("")

if __name__ == "__main__":
    main()
