import os
import argparse
import platform
from datetime import datetime, timedelta
import re
import Utils

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v1.6.0"
SCRIPT_DATE         = "2024-12-18"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) by Jaime Tur (@jaimetur)
"""

PROCESS_DUPLICATES_HELP = \
f"""
Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : This action can be used to replace the principal file chosen for each duplicates and select manually other principal file
                          Duplicated file moved to Duplicates folder will be restored to its original location as principal file
                          and Original Principal file detected by the Script will be removed permanently
"""

# List of Folder to Desprioritize when looking for duplicates.
DEPRIORITIZE_FOLDERS_PATTERNS = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

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
    def parse_folders(value):
        """
        Parse the input string and split it into a list of folders.
        Supports space, comma, or semicolon as separators.
        """
        if isinstance(value, list):
            # If multiple arguments are passed, return them as a list
            return value
        return [folder.strip() for folder in re.split(r'[ ,;]+', value) if folder.strip()]


    def parse_arguments():
        choices_for_folder_structure  = ['flatten', 'year', 'year/month', 'year-month']
        choices_for_remove_duplicates = ['list', 'move', 'remove']
        parser = argparse.ArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=Utils.WideHelpFormatter,  # Aplica el formatter
        )
        parser.add_argument("-z",  "--zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
        parser.add_argument("-t",  "--takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to unzip input files. Default: 'Takeout'.")
        parser.add_argument("-s",  "--suffix", metavar="<SUFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
        parser.add_argument("-as", "--albums-structure", metavar=f"{choices_for_folder_structure}", default="flatten", help="Specify the type of folder structure for each Album folder (Default: 'flatten')."
                            , type=lambda s: s.lower()  # Convert input to lowercase
                            , choices=choices_for_folder_structure  # Valid choices
        )
        parser.add_argument("-ns", "--no-albums-structure", metavar=f"{choices_for_folder_structure}", default="year/month", help="Specify the type of folder structure for ALL_PHOTOS folder (Default: 'year/month')."
                            , type=lambda s: s.lower()  # Convert input to lowercase
                            , choices=choices_for_folder_structure  # Valid choices
        )
        parser.add_argument("-sg", "--skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool. NOT RECOMMENDED!!! because this is the Core of the Script. Use this flag only for testing purposses.")
        parser.add_argument("-se", "--skip-extras", action="store_true", help="Skip processing extra photos such as  -edited, -effects photos.")
        parser.add_argument("-sm", "--skip-move-albums", action="store_true", help="Skip moving albums to Albums folder.")
        parser.add_argument("-sa", "--symbolic-albums", action="store_true", help="Creates symbolic links for Albums instead of duplicate the files of each Album. (Useful to save disk space but may not be portable to other systems).")
        parser.add_argument("-it", "--ignore-takeout-structure", action="store_true", help="Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.")
        parser.add_argument("-mt", "--move-takeout-folder", action="store_true", help="Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>.       CAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!. Use only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
        parser.add_argument("-rd", "--remove-duplicates-after-fixing", action="store_true", help="Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.")
        parser.add_argument("-re", "--run-exif-tool", action="store_true", help="Run EXIF Tool files processing in the last step. (Useful if GPTH Tool cannot fix some files, but is a slow process). RECOMMENDATION: Use only if after runnning normal process with GPTH Tool, you still have many files with no date.")
        parser.add_argument("-nl", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")
        parser.add_argument("-fs", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="Execute the Script in Mode 'Fix Symbolic Links Broken' and try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_FOLDER and some Albums seems to be empty.")
        parser.add_argument("-fd", "--find-duplicates-in-folders", metavar="<DUPLICATES_FOLDER>", default="", nargs="+", help="Execute the Script in Mode 'Find Duplicates' (All other steps will be skipped). Specify the Folder(s) where you want to find duplicates. If found any duplicates within the list of folders given, the file in the first folder will be kept and the others will me moved or deleted according to the flag '-da, --duplicates-action'.")
        parser.add_argument("-da", "--duplicates-action", metavar=f"{choices_for_remove_duplicates}", default="", help="Execute the Script in Mode 'Find Duplicates' (All other steps will be skipped). Specify what to do with duplicates files found."
                            , type=lambda s: s.lower()  # Convert input to lowercase
                            , choices=choices_for_remove_duplicates  # Valid choices
        )
        parser.add_argument("-pd", "--process-duplicates-revised", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Execute the Script in Mode 'Process Duplicates Revised' (All other steps will be skipped). Specify the Duplicates CSV file revised with specifics Actions in Action column, and the script will execute that Action for each duplicates found in CSV. Valid Actions are: 'restore_duplicate', 'remove_duplicate' and 'replace_duplicate'.")
        # parser.add_argument("-pd", "--process-duplicates-revised", metavar="<DUPLICATES_REVISED_CSV>", default="", help=PROCESS_DUPLICATES_HELP)
        args = parser.parse_args()
        args.zip_folder = args.zip_folder.rstrip('/\\')
        args.takeout_folder = args.takeout_folder.rstrip('/\\')
        args.suffix = args.suffix.lstrip('_')
        return args

def main():
    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')
    args = parse_arguments()

    # Create timestamp, start_time and define OUTPUT_FOLDER
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_time = datetime.now()
    OUTPUT_FOLDER = f"{args.takeout_folder}_{args.suffix}_{timestamp}"

    # Set a global variable for logger and Set up logger based on the skip-log argument
    global logger
    log_filename=f"execution_log_{timestamp}"
    log_folder="Logs"
    log_folder_filename = os.path.join(log_folder,log_filename+'.log')
    logger = Utils.log_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=args.no_log_file, plain_log=False)

    logger.info(SCRIPT_DESCRIPTION)
    logger.info("")
    logger.info("===================")
    logger.info("STARTING PROCESS...")
    logger.info("===================")
    logger.info("")

    # If not 'Find Duplicates' / 'Process Duplicates' / 'Fix Symbolic Links' Modes detected, we run the normal Scripts Steps
    if args.find_duplicates_in_folders=="" and args.duplicates_action=="" and args.fix_symlinks_broken=="" and args.process_duplicates_revised=="":
        # Mensajes informativos
        if not args.zip_folder=="": logger.info(f"INFO: Using Zip folder           : '{args.zip_folder}'")
        logger.info(f"INFO: Using Takeout folder       : '{args.takeout_folder}'")
        logger.info(f"INFO: Using Suffix               : '{args.suffix}'")
        logger.info(f"INFO: Using Output folder        : '{OUTPUT_FOLDER}'")
        logger.info(f"INFO: Albums Folder Structure    : '{args.albums_structure}'")
        logger.info(f"INFO: No Albums Folder Structure : '{args.no_albums_structure}'")
        if not args.no_log_file:
            logger.info(f"INFO: Execution Log file         : '{log_folder_filename}'")

        logger.info(f"")
        if args.zip_folder=="":
            logger.warning(f"WARNING: No argument '-z or --zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if args.move_takeout_folder:
            logger.warning(f"WARNING: Flag detected '-mt, --move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_FOLDER>...")
        if args.symbolic_albums:
            logger.warning(f"WARNING: Flag detected '-sa, --symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if args.skip_gpth_tool:
            logger.warning(f"WARNING: Flag detected '-sg, --skip-gpth-toot'. Skipping Processing photos with GPTH Tool...")
        if args.skip_move_albums:
            logger.warning(f"WARNING: Flag detected '-sm, --skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if args.albums_structure.lower()!='flatten':
            logger.warning(f"WARNING: Flag detected '-as, --albums-structure'. Folder structure '{args.albums_structure}' will be applied on each Album folder...")
        if args.no_albums_structure.lower()!='year/month':
            logger.warning(f"WARNING: Flag detected '-ns, --no-albums-structure'. Folder structure '{args.no_albums_structure}' will be applied on ALL_PHOTOS folder (Photos without Albums)...")
        if args.ignore_takeout_structure:
            logger.warning(f"WARNING: Flag detected '-it, --ignore-takeout-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if args.run_exif_tool:
            logger.warning(f"WARNING: Flag detected '-re, --run-exif-tool'. EXIF tool will be run in last step to try to fix photos metadata...")
        if args.remove_duplicates_after_fixing:
            logger.warning(f"WARNING: Flag detected '-rd, --remove-duplicates-after-fixing'. All duplicates files within OUTPUT_FOLDER will be removed after fixing them...")
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
        logger.info("===================================")
        logger.info(f"{STEP}. PRE-PROCESSING TAKEOUT FOLDER...")
        logger.info("===================================")
        logger.info("")
        step_start_time = datetime.now()
        # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
        logger.info("INFO: Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
        Utils.delete_subfolders(args.takeout_folder, "@eaDir")
        # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
        logger.info("")
        logger.info("INFO: Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
        Utils.fix_mp4_files(args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        logger.info("")
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
                output_folder=OUTPUT_FOLDER,
                symbolic_albums=args.symbolic_albums,
                skip_extras=args.skip_extras,
                move_takeout_folder=args.move_takeout_folder,
                ignore_takeout_structure=args.ignore_takeout_structure
            )
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
            logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
        if args.skip_gpth_tool or args.ignore_takeout_structure:
            logger.info("")
            logger.info("============================================")
            logger.info(f"{STEP}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
            logger.info("============================================")
            logger.info("")
            if args.skip_gpth_tool:
                logger.warning(f"WARNING: Metadata fixing with GPTH tool skipped ('-sg, --skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
            elif args.ignore_takeout_structure:
                logger.warninf(f"WARNING: Flag to Ignore Google Takeout Structure have been detected ('-it, --ignore-takeout-structure'). Step {STEP}b is needed to copy/move files manually to output folder.")
            if args.move_takeout_folder:
                logger.info("INFO: Moving files from Takeout folder to Output folder manually...")
            else:
                logger.info("INFO: Copying files from Takeout folder to Output folder manually...")
            step_start_time = datetime.now()
            Utils.copy_move_folder (args.takeout_folder, OUTPUT_FOLDER, ignore_patterns=['*.json', '*.j'], move=args.move_takeout_folder)
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
        Utils.sync_mp4_timestamps_with_images(OUTPUT_FOLDER)
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
            logger.info(f"INFO: Creating Folder structure '{args.albums_structure.lower()}' for each Album folder...")
            basedir=OUTPUT_FOLDER
            type=args.albums_structure
            exclude_subfolders=['ALL_PHOTOS']
            Utils.organize_files_by_date(base_dir=basedir, type=type, exclude_subfolders=exclude_subfolders)
        # For No Albums:
        if args.no_albums_structure.lower()!='flatten':
            logger.info("")
            logger.info(f"INFO: Creating Folder structure '{args.no_albums_structure.lower()}' for ALL_PHOTOS folder...")
            basedir=os.path.join(OUTPUT_FOLDER, 'ALL_PHOTOS')
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
            Utils.move_albums(OUTPUT_FOLDER, exclude_subfolder=["ALL_PHOTOS", "@eaDir"])
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
            logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
        else:
            logger.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --skip-move-albums' flag detected).")

        # STEP 7: Fix Broken Symbolic Links after moving
        STEP+=1
        symlink_fixed = 0
        symlink_not_fixed = 0
        logger.info("")
        logger.info("===============================================")
        logger.info(f"{STEP}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
        logger.info("===============================================")
        logger.info("")
        if args.symbolic_albums:
            logger.info("INFO: Fixing broken symbolic links. This step is needed after moving any Folder structure...")
            step_start_time = datetime.now()
            symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(OUTPUT_FOLDER)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
            logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
        else:
            logger.warning("WARNING: Fixing broken symbolic links skipped ('-sa, --symbolic-albums' flag not detected, so this step is not needed.)")

        # STEP 8: Fix metadata with EXIF Tool
        STEP+=1
        logger.info("")
        logger.info("===========================================")
        logger.info(f"{STEP}. FIXING PHOTOS METADATA WITH EXIF TOOL...")
        logger.info("===========================================")
        logger.info("")
        if args.run_exif_tool:
            step_start_time = datetime.now()
            Utils.fix_metadata_with_exif_tool(OUTPUT_FOLDER)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
            logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
        else:
            logger.warning("WARNING: Metadata fixing with EXIF tool skipped ('-re, --run-exif-tool' flag not detected).")

        # STEP 9: Remove Duplicates in OUTPUT_FOLDER after Fixing
        STEP+=1
        duplicates_found = 0
        if args.remove_duplicates_after_fixing:
            logger.info("")
            logger.info("==========================================")
            logger.info(f"{STEP}. REMOVING DUPLICATES IN OUTPUT_FOLDER...")
            logger.info("==========================================")
            logger.info("")
            logger.info("INFO: Removing duplicates from OUTPUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'ALL_PHOTOS' folders)...")
            step_start_time = datetime.now()
            duplicates_found = Utils.find_duplicates(duplicates_action='remove', find_duplicates_in_folders=OUTPUT_FOLDER, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS, timestamp=timestamp)
            step_end_time = datetime.now()
            formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
            logger.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

        # FINAL SUMMARY
        end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(end_time-start_time).seconds))
        logger.info("")
        logger.info("==================================================")
        logger.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
        logger.info("==================================================")
        logger.info("")
        logger.info(f"INFO: All the Photos/Videos Fixed can be found on folder: '{OUTPUT_FOLDER}'")
        logger.info("")
        logger.info("===============================================")
        logger.info("                FINAL SUMMARY:                 ")
        logger.info("===============================================")
        logger.info(f"Total files in Takeout folder        : {Utils.count_files_in_folder(args.takeout_folder)}")
        logger.info(f"Total final files in Output folder   : {Utils.count_files_in_folder(OUTPUT_FOLDER)}")
        albums_found = 0
        if not args.skip_move_albums:
            album_folder = os.path.join(OUTPUT_FOLDER, 'Albums')
            if os.path.isdir(album_folder):
                albums_found = len(os.listdir(album_folder))
        else:
            if os.path.isdir(OUTPUT_FOLDER):
                albums_found = len(os.listdir(OUTPUT_FOLDER))-1
        logger.info(f"Total Albums folders found           : {albums_found}")
        if args.symbolic_albums:
            logger.info(f"Total Symlinks Fixed                 : {symlink_fixed}")
            logger.info(f"Total Symlinks Not Fixed             : {symlink_not_fixed}")
        if args.remove_duplicates_after_fixing:
            logger.info(f"Total Duplicates Removed             : {duplicates_found}")
        logger.info("")
        logger.info(f"Total time elapsed                   : {formatted_duration}")
        logger.info("===============================================")
        logger.info("")

    # If detect Fix Symlink Mode:
    elif args.fix_symlinks_broken:
        logger.info(f"INFO: Fixing broken symbolic links Mode detected. Only this module will be run!!!")
        logger.info(f"INFO: Fixing broken symbolic links in folder '{args.fix_symlinks_broken}'...")
        symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(args.fix_symlinks_broken)
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
        logger.info(f"Total Fixed Symbolic Links              : {symlinks_fixed}")
        logger.info(f"Total No Fixed Symbolic Links           : {symlinks_not_fixed}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If detect Process Duplicates Revised Mode:
    elif args.process_duplicates_revised:
        logger.info(f"INFO: Flag detected '-pd, --process-duplicates-revised'. The Script will process the {os.path.basename(args.process_duplicates_revised)} file and do the specified action given on Action Column. ")
        logger.info(PROCESS_DUPLICATES_HELP)

        logger.info(f"INFO: Processing Duplicates Files based on Actions given in {os.path.basename(args.process_duplicates_revised)} file...")
        removed_duplicates, restored_duplicates, replaced_duplicates = Utils.process_duplicates_actions(args.process_duplicates_revised)
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
        logger.info(f"Total Removed Duplicates                : {removed_duplicates}")
        logger.info(f"Total Restored Duplicates               : {restored_duplicates}")
        logger.info(f"Total Replaced Duplicates               : {replaced_duplicates}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If Detect Find Duplicates Mode:
    else:
        if args.find_duplicates_in_folders=="" and  args.duplicates_action!="":
            logger.error(f"ERROR: Find Duplicates Mode detected with the argument '{args.duplicates_action}' but not argument '-fd, --find-duplicates-in-folders' given. Exiting...")
            logger.info("")
            return -1
        elif args.find_duplicates_in_folders!="" and  args.duplicates_action=="":
            logger.warning(f"WARNING: Find Duplicates Mode detected with the argument '{args.find_duplicates_in_folders}' but not argument '-da, --duplicates-action' given. Using 'list' as default duplicates-action...")
            logger.info("")
            args.duplicates_action = 'list'

        logger.info(f"INFO: Duplicates Action             : '{args.duplicates_action}'")
        logger.info(f"INFO: Find Duplicates in Folders    : {args.find_duplicates_in_folders}")
        logger.info("")
        logger.info(f"INFO: Find Duplicates Mode detected. Only this module will be run!!!")
        logger.info("")
        duplicates_files_found = Utils.find_duplicates(duplicates_action=args.duplicates_action, find_duplicates_in_folders=args.find_duplicates_in_folders, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            logger.error("ERROR: Exiting because some of the folder(s) given in argument '-fd, --find-duplicates-in-folders' does not exists.")
            return -1

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
        logger.info(f"Total duplicates files found            : {duplicates_files_found}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

if __name__ == "__main__":
    main()
