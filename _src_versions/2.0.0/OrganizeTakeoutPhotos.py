import os,sys
import argparse
import platform
from datetime import datetime, timedelta
import re
import Utils
from Duplicates import find_duplicates, process_duplicates_actions
from SynologyPhotos import create_synology_albums, delete_empty_albums, delete_duplicates_albums
from CustomHelpFormatter import CustomHelpFormatter
from LoggerConfig import log_setup

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v2.0.0"
SCRIPT_DATE         = "2024-12-24"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Script (based on GPTH and EXIF Tools) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) by Jaime Tur (@jaimetur)
"""

PROCESS_FIX_SYMLINKS_HELP = \
f"""
ATTENTION!!!: This process will look for all Symbolic Links broken in <FOLDER_TO_FIX> and will try to find the destination file within the same folder.
"""

FIND_DUPLICATES_HELP = \
f"""
ATTENTION!!!: This process will process all Duplicates files found in <DUPLICATES_FOLDER> and will apply the action provided with mandatory argument -da, --duplicates-action
You must take into account 

Possible duplicates-action in -da, --duplicates-action argument are:
    - list   : This action is not dangerous, just list all duplicates files found in a Duplicates.csv file.
    - move   : This action could be dangerous but is easily reversible if you find that any duplicated file have been moved to Duplicates folder and you want to restore it later
               You can easily restore it using option -pd, --process-duplicates-revised
    - remove : This action could be dangerous and is irreversible, since the script will remove all duplicates found and will keep only a Principal file per each duplicates set. 
               The principal file is chosen carefilly based on some heuristhic methods
"""

PROCESS_DUPLICATES_HELP = \
f"""
ATTENTION!!!: This process will process all Duplicates files found with -fd, --find-duplicates <DUPLICATES_FOLDER> option based on the Action column value of Duplicates.csv file generated in 'Find Duplicates Mode'. 

You can modify individually each Action column value for each duplicate found, but take into account that the below actions list are irreversible:

Possible Actions in revised CSV file are:
    - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
    - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
    - replace_duplicate : This action can be used to replace the principal file chosen for each duplicates and select manually other principal file
                          Duplicated file moved to Duplicates folder will be restored to its original location as principal file
                          and Original Principal file detected by the Script will be removed permanently
"""

PROCESS_RENAME_ALBUMS_HELP = \
f"""
ATTENTION!!!: This process will clean each Subfolder found in <ALBUMS_FOLDER> with an homogeneous name starting with album year followed by a cleaned subfolder name without underscores nor middle dashes.
New Album name format: 'yyyy - Cleaned Subfolder name'
"""

PROCESS_CREATE_ALBUMS_HELP = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
"""

PROCESS_DELETE_EMPTY_ALBUMS_HELP = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Empty Albums found in Synology Photos database.
"""

PROCESS_DELETE_DUPLICATES_ALBUMS_HELP = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Duplicates Albums found in Synology Photos database.
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

LOGGER = None
if __name__ == "__main__":
    def parse_arguments():
        def parse_folders(folders):
            # Si "folders" es un string, separar por comas o espacios
            if isinstance(folders, str):
                return folders.replace(',', ' ').split()

            # Si "folders" es una lista, aplanar un nivel
            if isinstance(folders, list):
                flattened = []
                for item in folders:
                    if isinstance(item, list):
                        flattened.extend(item)
                    else:
                        flattened.append(item)
                return flattened

            # Si no es ni lista ni string, devolver lista vacía
            return []

        choices_for_folder_structure  = ['flatten', 'year', 'year/month', 'year-month']
        choices_for_remove_duplicates = ['list', 'move', 'remove']
        parser = argparse.ArgumentParser(
            description=SCRIPT_DESCRIPTION,
            formatter_class=CustomHelpFormatter,  # Aplica el formatter
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
        parser.add_argument("-mt", "--move-takeout-folder", action="store_true", help=f"Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>. \nCAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!. Use only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
        parser.add_argument("-rd", "--remove-duplicates-after-fixing", action="store_true", help="Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.")
        parser.add_argument("-re", "--run-exif-tool", action="store_true", help="Run EXIF Tool files processing in the last step. (Useful if GPTH Tool cannot fix some files, but is a slow process). RECOMMENDATION: Use only if after runnning normal process with GPTH Tool, you still have many files with no date.")
        # parser.add_argument("-da", "--duplicates-action", metavar=f"{choices_for_remove_duplicates}", default="", help="Specify what to do with duplicates files found. This argument is a complementary argument for '-fd, --find-duplicates' and will force the script to run in Mode 'Find Duplicates' (All other steps will be skipped)."
        #                     , type=lambda s: s.lower()  # Convert input to lowercase
        #                     , choices=choices_for_remove_duplicates  # Valid choices
        #                     )
        parser.add_argument("-nl", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")

        # EXTRA MODES ARGUMENTS:
        parser.add_argument("-fs", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="Force Mode: 'Fix Symbolic Links Broken'. The script will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_FOLDER and some Albums seems to be empty.")
        parser.add_argument("-ra", "--rename-albums", metavar="<ALBUMS_FOLDER>", default="", help="Force Mode: 'Rename Albums'. Rename all Albums folders found in <ALBUMS_FOLDER> to unificate the format.")
        parser.add_argument("-fd", "--find-duplicates", metavar=f"{choices_for_remove_duplicates} <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]", nargs="+", default=["list", ""],
                            help="Force Mode: 'Find Duplicates'. Find duplicates in specified folders. "
                                 "The first argument is the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list' "
                                 "The remaining arguments are one or more folders (string or list). where the script will look for duplicates files. The order of this list is important to determine the principal file of a duplicates set. First folder will have higher priority."
                            )

        # parser.add_argument("-fd", "--find-duplicates", metavar="<DUPLICATES_FOLDER>", default="", nargs="+", help="Force Mode: 'Find Duplicates'. Specify the Folder(s) where you want to find duplicates. If found any duplicates within the list of folders given, the file in the first folder will be kept and the others will me moved or deleted according to the flag '-da, --duplicates-action'.")
        parser.add_argument("-pd", "--process-duplicates-revised", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Force Mode: 'Process Duplicates Revised'. Specify the Duplicates CSV file revised with specifics Actions in Action column, and the script will execute that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.")
        parser.add_argument("-ca", "--create-albums-synology-photos", metavar="<ALBUMS_FOLDER>", default="", help="force Mode: 'Create Albums in Synology Photos'. The script will look for all Albums within ALBUM_FOLDER and will create one Album per folder into Synology Photos.")
        parser.add_argument("-de", "--delete-empty-albums-synology-photos", action="store_true", default="", help="Force Mode: 'Delete Empty Albums in Synology Photos'. The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database.")
        parser.add_argument("-dd", "--delete-duplicates-albums-synology-photos", action="store_true", default="", help="Force Mode: 'Delete Duplicates Albums in Synology Photos'. The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.")
        args = parser.parse_args()
        # Procesar la acción y las carpetas
        global default_duplicates_action
        args.duplicates_folders = []
        args.duplicates_action = ""
        for subarg in args.find_duplicates:
            if subarg.lower() in choices_for_remove_duplicates:
                args.duplicates_action = subarg
            else:
                if subarg != "":
                    args.duplicates_folders.append(subarg)
        if args.duplicates_action == "" and args.duplicates_folders !=[]:
            args.duplicates_action = 'list'  # Valor por defecto
            default_duplicates_action = True

        args.duplicates_folders = parse_folders(args.duplicates_folders)

        # Eliminar el argumento original para evitar confusión
        del args.find_duplicates

        args.zip_folder = args.zip_folder.rstrip('/\\')
        args.takeout_folder = args.takeout_folder.rstrip('/\\')
        args.suffix = args.suffix.lstrip('_')
        return args

def main():
    def get_server_data():
        server_data = {}
        if args.url_synology_server!="":
            server_data['url'] = args.url_synology_server
        else:
            logger.error(f"ERROR: Missing mandatory argument -url, --url-synology-server. Exiting...")
            logger.error("")
            exit(-1)
        if args.user_synology_server!="":
            server_data['usr'] = args.user_synology_server
        else:
            logger.error(f"ERROR: Missing mandatory argument -usr, --user-synology-server. Exiting...")
            logger.error("")
            exit(-1)
        if args.password_synology_server!="":
            server_data['pwd'] = args.password_synology_server
        else:
            logger.error(f"ERROR: Missing mandatory argument -pwd, --password-synology-server. Exiting...")
            logger.error("")
            exit(-1)
        return server_data

    global default_duplicates_action
    default_duplicates_action = False

    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')
    args = parse_arguments()

    # Create timestamp, start_time and define OUTPUT_FOLDER
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    start_time = datetime.now()
    OUTPUT_FOLDER = f"{args.takeout_folder}_{args.suffix}_{timestamp}"

    # Set a global variable for logger and Set up logger based on the skip-log argument
    log_filename=f"execution_log_{timestamp}"
    log_folder="Logs"
    log_folder_filename = os.path.join(log_folder,log_filename+'.log')
    logger = log_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=args.no_log_file, plain_log=False)

    logger.info(SCRIPT_DESCRIPTION)
    logger.info("")
    logger.info("===================")
    logger.info("STARTING PROCESS...")
    logger.info("===================")
    logger.info("")

    # Determine the Execution mode based on the providen arguments:
    if args.fix_symlinks_broken != "":
        EXECUTION_MODE = 'fix_symlinks'
    elif args.duplicates_folders != []:
        EXECUTION_MODE = 'find_duplicates'
    elif args.process_duplicates_revised != "":
        EXECUTION_MODE = 'process_duplicates'
    elif args.rename_albums != "":
        EXECUTION_MODE = 'rename_albums'
    elif args.create_albums_synology_photos != "":
        EXECUTION_MODE = 'create_albums'
    elif args.delete_empty_albums_synology_photos:
        EXECUTION_MODE = 'delete_empty_albums'
    elif args.delete_duplicates_albums_synology_photos:
        EXECUTION_MODE = 'delete_duplicates_albums'
    else:
        EXECUTION_MODE = 'normal'  # Opción por defecto si no se cumple ninguna condición
    
    # If Execution Mode is Normal
    if EXECUTION_MODE == 'normal':
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
        if args.skip_extras:
            logger.warning(f"WARNING: Flag detected '-se, --skip-extras'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
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

        if not os.path.isdir(args.takeout_folder):
            logger.error(f"ERROR: Cannot Find TAKEOUT_FOLDER: '{args.takeout_folder}'. Exiting...")
            sys.exit(-1)

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
            Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
        # For No Albums:
        if args.no_albums_structure.lower()!='flatten':
            logger.info("")
            logger.info(f"INFO: Creating Folder structure '{args.no_albums_structure.lower()}' for ALL_PHOTOS folder...")
            basedir=os.path.join(OUTPUT_FOLDER, 'ALL_PHOTOS')
            type=args.no_albums_structure
            exclude_subfolders=[]
            Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
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
            duplicates_found = find_duplicates(duplicates_action='remove', duplicates_folders=OUTPUT_FOLDER, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS, timestamp=timestamp)
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
    elif EXECUTION_MODE == 'fix_symlinks':
        logger.info(f"INFO: Fixing broken symbolic links Mode detected. Only this module will be run!!!")
        logger.info(PROCESS_FIX_SYMLINKS_HELP.replace('<FOLDER_TO_FIX>', f"'{args.fix_symlinks_broken}'"))
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
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

    # If Detect Find Duplicates Mode:
    elif EXECUTION_MODE == 'find_duplicates':
        if default_duplicates_action:
            logger.warning(f"WARNING: Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
        logger.info(FIND_DUPLICATES_HELP.replace('<DUPLICATES_FOLDER>', f"'{args.duplicates_folders}'"))
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)

        logger.info(f"INFO: Duplicates Action             : {args.duplicates_action}")
        logger.info(f"INFO: Find Duplicates in Folders    : {args.duplicates_folders}")
        logger.info("")
        logger.info(f"INFO: Find Duplicates Mode detected. Only this module will be run!!!")
        logger.info("")
        duplicates_files_found = find_duplicates(duplicates_action=args.duplicates_action, duplicates_folders=args.duplicates_folders, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
        if duplicates_files_found == -1:
            logger.error("ERROR: Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exists.")
            sys.exit(-1)

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
        logger.info(f"Total Duplicates Found                  : {duplicates_files_found}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If detect Process Duplicates Revised Mode:
    elif EXECUTION_MODE == 'process_duplicates':
        logger.info(f"INFO: Flag detected '-pd, --process-duplicates-revised'. The Script will process the '{args.process_duplicates_revised}' file and do the specified action given on Action Column. ")
        logger.info(PROCESS_DUPLICATES_HELP)
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
        logger.info(f"INFO: Processing Duplicates Files based on Actions given in {os.path.basename(args.process_duplicates_revised)} file...")
        removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(args.process_duplicates_revised)
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

    # If Detect Create Albyms Mode:
    elif EXECUTION_MODE == 'rename_albums':
        logger.info(f"INFO: Rename Albums Mode detected. Only this module will be run!!!")
        logger.info(f"INFO: Flag detected '-ra, --rename-albums'. The Script will look for any Subfolder in '{args.rename_albums}' and will rename the folder name in order to unificate all the Albums names.")
        logger.info(PROCESS_RENAME_ALBUMS_HELP.replace('<ALBUMS_FOLDER>', f"'{args.rename_albums}'"))
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
        renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(args.rename_albums)
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
        logger.info(f"Total Albums folders renamed             : {renamed_album_folders}")
        logger.info(f"Total Albums folders duplicated          : {duplicates_album_folders}")
        logger.info(f"Total Albums duplicated fully merged     : {duplicates_albums_fully_merged}")
        logger.info(f"Total Albums duplicated not fully merged : {duplicates_albums_not_fully_merged}")
        logger.info("")
        logger.info(f"Total time elapsed                       : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If Detect Create Albyms Mode:
    elif EXECUTION_MODE == 'create_albums':
        logger.info(f"INFO: Create Albums Mode detected. Only this module will be run!!!")
        logger.info(f"INFO: Flag detected '-ca, --create-albums-synology-photos'. The Script will look for any Subfolder in '{args.create_albums_synology_photos}' and create an Album with each subfolder name in Synology Photos database.")
        logger.info(PROCESS_CREATE_ALBUMS_HELP.replace('<ALBUMS_FOLDER>', f"'{args.create_albums_synology_photos}'"))
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
        logger.info("")
        logger.info(f"INFO: Find Albums in Folder    : {args.create_albums_synology_photos}")
        logger.info("")
        albums_crated, albums_skipped, photos_added = create_synology_albums(args.create_albums_synology_photos)
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
        logger.info(f"Total Albums created                    : {albums_crated}")
        logger.info(f"Total Albums skipped                    : {albums_skipped}")
        logger.info(f"Total Photos added to Albums            : {photos_added}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If Detect Delete Empty Albums Mode:
    elif EXECUTION_MODE == 'delete_empty_albums':
        logger.info(f"INFO: Delete Empty Album Mode detected. Only this module will be run!!!")
        logger.info(f"INFO: Flag detected '-de, --delete-empty-albums-synology-photos'. The Script will look for any empty album in Synology Photos database and will detelte them (if any enpty album is found).")
        logger.info(PROCESS_DELETE_EMPTY_ALBUMS_HELP)
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
        albums_deleted = delete_empty_albums()
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
        logger.info(f"Total Empty Albums deleted              : {albums_deleted}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

    # If Detect Delete Duplicates Albums Mode:
    elif EXECUTION_MODE == 'delete_duplicates_albums':
        logger.info(f"INFO: Delete Duplicates Album Mode detected. Only this module will be run!!!")
        logger.info(f"INFO: Flag detected '-dd, --delete-duplicates-albums-synology-photos'. The Script will look for any duplicated album in Synology Photos database and will detelte them (if any duplicated album is found).")
        logger.info(PROCESS_DELETE_DUPLICATES_ALBUMS_HELP)
        if not Utils.confirm_continue():
            logger.info(f"INFO: Exiting program.")
            sys.exit(0)
        albums_deleted = delete_duplicates_albums()
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
        logger.info(f"Total Duplicates Albums deleted         : {albums_deleted}")
        logger.info("")
        logger.info(f"Total time elapsed                      : {formatted_duration}")
        logger.info("==================================================")
        logger.info("")

if __name__ == "__main__":
    main()
