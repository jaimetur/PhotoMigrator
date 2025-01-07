import os
import argparse
import platform
from datetime import datetime, timedelta
import Utils

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v1.3.0"
SCRIPT_DATE         = "2024-12-04"

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
        choices_for_folder_structure = ['flatten', 'year', 'year/month', 'year-month']
        parser = argparse.ArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=Utils.WideHelpFormatter,  # Aplica el formatter
        )
        parser.add_argument("-z",  "--zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
        parser.add_argument("-t",  "--takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to unzip input files. Default: 'Takeout'")
        parser.add_argument("-s",  "--suffix", metavar="<SUFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
        parser.add_argument("-as", "--albums-structure", metavar=f"{choices_for_folder_structure}", default="flatten", help="Specify the type of folder structure for each Album folder."
                            , type=lambda s: s.lower()  # Convert input to lowercase
                            , choices=choices_for_folder_structure  # Valid choices
        )
        parser.add_argument("-ns", "--no-albums-structure", metavar=f"{choices_for_folder_structure}", default="flatten", help="Specify the type of folder structure for ALL_PHOTOS folder (Photos that are no contained in any Album)."
                            , type=lambda s: s.lower()  # Convert input to lowercase
                            , choices=choices_for_folder_structure  # Valid choices
        )
        parser.add_argument("-sg", "--skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool.")
        parser.add_argument("-sm", "--skip-move-albums", action="store_true", help="Skip moving albums to Albums folder.")
        parser.add_argument("-se", "--skip-extras", action="store_true", help="Skip processing extra photos such as  -edited, -effects photos.")
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
    if not args.zip_folder=="": logger.info(f"INFO: Using Zip folder           : '{args.zip_folder}'")
    logger.info(f"INFO: Using Takeout folder       : '{args.takeout_folder}'")
    logger.info(f"INFO: Using Suffix               : '{args.suffix}'")
    logger.info(f"INFO: Using Output folder        : '{output_folder}'")
    logger.info(f"INFO: Albums Folder Structure    : '{args.albums_structure}'")
    logger.info(f"INFO: No Albums Folder Structure : '{args.no_albums_structure}'")
    if not args.no_log_file:
        logger.info(f"INFO: Execution Log file         : '{log_folder_filename}'")

    logger.info(f"")
    if args.zip_folder=="":
        logger.warning(f"WARNING: No argument '-z or --zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
    if args.move_takeout_folder:
        logger.warning(f"WARNING: Flag detected '-mt, --move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_FOLDER>...")
    if args.skip_gpth_tool:
        logger.warning(f"WARNING: Flag detected '-sg, --skip-gpth-toot'. Skipping Processing photos with GPTH Tool...")
    if args.skip_move_albums:
        logger.warning(f"WARNING: Flag detected '-sm, --skip-move-albums'. Skipping Moving Albums to Albums folder...")
    if args.albums_structure.lower()!='flatten':
        logger.warning(f"WARNING: Flag detected '-as, --albums-structure'. Folder structure '{args.albums_structure}' will be applied on each Album folder...")
    if args.no_albums_structure.lower()!='flatten':
        logger.warning(f"WARNING: Flag detected '-ns, --no-albums-structure'. Folder structure '{args.no_albums_structure}' will be applied on ALL_PHOTOS folder (Photos without Albums)...")
    if args.ignore_takeout_structure:
        logger.warning(f"WARNING: Flag detected '-it, --ignore-takeout-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
    if args.run_exif_tool:
        logger.warning(f"WARNING: Flag detected '-re, --run-exif-tool'. EXIF tool will be run in last step to try to fix photos metadata...")
    if args.no_log_file:
        logger.warning(f"WARNING: Flag detected '-sl, --skip-log'. Skipping saving output into log file...")
        

    # STEP 1: Unzip files
    STEP=1
    logger.info("")
    logger.info("==============================")
    logger.info(f"{STEP}. UNPACKING TAKEOUT FOLDER...")
    logger.info("==============================")
    logger.info("")
    if not args.zip_folder=="":
        step_start_time = datetime.now()
        Utils.unpack_zips(args.zip_folder, args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Unzipping skipped (no argument '-z or --zip-folder <ZIP_FOLDER>' given).")
    
    # STEP 2: Pre-Process Takeout folder
    STEP+=1
    logger.info("")
    logger.info("===========================================")
    logger.info(f"{STEP}. PRE-PROCESSING TAKEOUT FOLDER...")
    logger.info("===========================================")
    logger.info("")
    step_start_time = datetime.now()
    # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
    logger.info("INFO: Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
    Utils.delete_subfolders(args.takeout_folder, "@eaDir")
    # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
    logger.info("INFO: Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
    Utils.fix_mp4_files(args.takeout_folder)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 3: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    STEP+=1
    logger.info("")
    logger.info("===========================================")
    logger.info(f"{STEP}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    logger.info("===========================================")
    logger.info("")
    if not args.skip_gpth_tool:
        if args.ignore_takeout_structure:
            logger.warning("WARNING: Ignore Google Takeout Structure detected ('-it, --ignore-takeout-structure' flag detected).")
        step_start_time = datetime.now()
        Utils.fix_metadata_with_gpth_tool(
            input_folder=args.takeout_folder,
            output_folder=output_folder,
            skip_extras=args.skip_extras,
            flatten_albums=args.flatten_albums,
            flatten_no_albums=args.flatten_no_albums,
            move_takeout_folder=args.move_takeout_folder,
            ignore_takeout_structure=args.ignore_takeout_structure
        )
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    if args.skip_gpth_tool or args.ignore_takeout_structure:
        logger.info("")
        logger.info("=====================================")
        logger.info(f"{STEP}b. COPYING FILES TO OUTPUT FOLDER...")
        logger.info("=====================================")
        logger.info("")
        if args.skip_gpth_tool:
            logger.warning(f"WARNING: Metadata fixing with GPTH tool skipped ('-sg, --skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
        elif args.ignore_takeout_structure:
            logger.warninf(f"WARNING: Flag to Ignore Google Takeout Structure have been detected ('-it, --ignore-takeout-structure'). Step {STEP}b is needed to copy files manually to output folder.")
        logger.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder (args.takeout_folder, output_folder, ignore_patterns=['*.json', '*.j'], move=args.move_takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP}b completed in {formatted_duration}.")

    # STEP 4: Sync .MP4 live pictures timestamp
    STEP+=1
    logger.info("")
    logger.info("==============================================================")
    logger.info(f"{STEP}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
    logger.info("==============================================================")
    logger.info("")
    step_start_time = datetime.now()
    logger.info("INFO: Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
    Utils.sync_mp4_timestamps_with_images(output_folder)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    

    # STEP 5: Create Folders Year/Month or Year only structure
    STEP+=1
    logger.info("")
    logger.info("==========================================")
    logger.info(f"{STEP}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
    logger.info("==========================================")
    step_start_time = datetime.now()
    # For Albums:
    if args.albums_structure.lower()!='flatten':
        logger.info("")
        logger.info(f"INFO: argument '-as, --albums-structure' detected with value: {args.albums_structure.lower()}")
        logger.info("INFO: Creating Folder structure for each Album folder...")
        basedir=output_folder
        type=args.albums_structure
        exclude_subfolders=['ALL_PHOTOS']
        Utils.organize_files_by_date(base_dir=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # For No Albums:
    if args.no_albums_structure.lower()!='flatten':
        logger.info("")
        logger.info(f"INFO: argument '-ns, --no-albums-structure' detected with value: {args.no_albums_structure.lower()}")
        logger.info("INFO: Creating Folder structure for ALL_PHOTOS folder (Photos with no Album associated)...")
        basedir=os.path.join(output_folder, 'ALL_PHOTOS')
        type=args.no_albums_structure
        exclude_subfolders=[]
        Utils.organize_files_by_date(base_dir=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # If no fiolder structure is detected:
    if args.albums_structure.lower()=='flatten' and args.no_albums_structure.lower()=='flatten' :
        logger.info("")
        logger.warning("WARNING: No argument '-as, --albums-structure' and '-ns, --no-albums-structure' detected. All photos and videos will be flattened within their folders without any date organization.")
    else:
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 6: Move albums
    STEP+=1
    logger.info("")
    logger.info("==========================")
    logger.info(f"{STEP}. MOVING ALBUMS FOLDER...")
    logger.info("==========================")
    logger.info("")
    if not args.skip_move_albums:
        step_start_time = datetime.now()
        Utils.move_albums(output_folder, exclude_subfolder=["ALL_PHOTOS", "@eaDir"])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --skip-move-albums' flag detected).")

    # STEP 7: Fix metadata with EXIF Tool
    STEP+=1
    logger.info("")
    logger.info("===========================================")
    logger.info(f"{STEP}. FIXING PHOTOS METADATA WITH EXIF TOOL...")
    logger.info("===========================================")
    logger.info("")
    if args.run_exif_tool:
        step_start_time = datetime.now()
        Utils.fix_metadata_with_exif_tool(output_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        logger.warning("WARNING: Metadata fixing with EXIF tool skipped ('-re, --run-exif-tool' flag not detected).")


    # FINAL SUMMARY
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
