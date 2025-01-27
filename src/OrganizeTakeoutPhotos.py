import os,sys
import argparse
import platform
from datetime import datetime, timedelta
import Utils
import Fixers
from Duplicates import find_duplicates, process_duplicates_actions
from SynologyPhotos import read_synology_config, login_synology, synology_upload_folder, synology_upload_albums, synology_download_albums, synology_delete_empty_albums, synology_delete_duplicates_albums
from ImmichPhotos import read_immich_config, login_immich, immich_upload_folder, immich_upload_albums, immich_download_albums, immich_delete_empty_albums, immich_delete_duplicates_albums, immich_download_all
from CustomHelpFormatter import CustomHelpFormatter, PagedArgumentParser
from LoggerConfig import log_setup

# Script version & date
SCRIPT_NAME         = "OrganizeTakeoutPhotos"
SCRIPT_VERSION      = "v3.0.0-alpha"
SCRIPT_DATE         = "2025-01-26"

SCRIPT_NAME_VERSION = f"{SCRIPT_NAME} {SCRIPT_VERSION}"
SCRIPT_DESCRIPTION  = f"""
{SCRIPT_NAME_VERSION} - {SCRIPT_DATE}

Script (based on GPTH Tool) to Process Google Takeout Photos and much more useful features
(remove duplicates, fix metadata, organize per year/month folder, separate Albums, fix symlinks, etc...).
(c) 2024-2025 by Jaime Tur (@jaimetur)
"""

def check_OS_and_Terminal():
    # Detect the operating system
    current_os = platform.system()
    # Determine the script name based on the OS
    if current_os == "Linux":
        if Utils.run_from_synology():
            LOGGER.info(f"INFO: Script running on Linux System in a Synology NAS")
        else:
            LOGGER.info(f"INFO: Script running on Linux System")
    elif current_os == "Darwin":
        LOGGER.info(f"INFO: Script running on MacOS System")
    elif current_os == "Windows":
        LOGGER.info(f"INFO: Script running on Windows System")
    else:
        LOGGER.error(f"ERROR: Unsupported Operating System: {current_os}")

    if sys.stdout.isatty():
        LOGGER.info("INFO: Interactive (TTY) terminal detected for stdout")
    else:
        LOGGER.info("INFO: Non-Interactive (Non-TTY) terminal detected for stdout")
    if sys.stdin.isatty():
        LOGGER.info("INFO: Interactive (TTY) terminal detected for stdin")
    else:
        LOGGER.info("INFO: Non-Interactive (Non-TTY) terminal detected for stdin")
    LOGGER.info("")

def set_help_texts():
    global HELP_MODE_NORMAL
    global HELP_MODE_FIX_SYMLINKS
    global HELP_MODE_FIND_DUPLICATES
    global HELP_MODE_PROCESS_DUPLICATES
    global HELP_MODE_RENAME_ALBUMS_FOLDERS
    global HELP_MODE_ALL_IN_ONE

    global HELP_MODE_SYNOLOGY_UPLOAD_FOLDER
    global HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS
    global HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS
    global HELP_MODE_SYNOLOGY_DELETE_EMPTY_ALBUMS
    global HELP_MODE_SYNOLOGY_DELETE_DUPLICATES_ALBUMS

    global HELP_MODE_IMMICH_UPLOAD_FOLDER
    global HELP_MODE_IMMICH_UPLOAD_ALBUMS
    global HELP_MODE_IMMICH_DOWNLOAD_ALBUMS
    global HELP_MODE_IMMICH_DOWNLOAD_ALL
    global HELP_MODE_IMMICH_DELETE_EMPTY_ALBUMS
    global HELP_MODE_IMMICH_DELETE_DUPLICATES_ALBUMS

    HELP_MODE_NORMAL = ""

    HELP_MODE_FIX_SYMLINKS = \
f"""
ATTENTION!!!: This process will look for all Symbolic Links broken in <FOLDER_TO_FIX> and will try to find the destination file within the same folder.
"""

    HELP_MODE_FIND_DUPLICATES = \
f"""
ATTENTION!!!: This process will process all Duplicates files found in <DUPLICATES_FOLDER> and will apply the given action.
              You must take into account that if not valid action is detected within the arguments of -fd, --find-duplicates, then 'list' will be the default action.

Possible duplicates-action are:
    - list   : This action is not dangerous, just list all duplicates files found in a Duplicates.csv file.
    - move   : This action could be dangerous but is easily reversible if you find that any duplicated file have been moved to Duplicates folder and you want to restore it later
               You can easily restore it using option -pd, --process-duplicates-revised
    - remove : This action could be dangerous and is irreversible, since the script will remove all duplicates found and will keep only a Principal file per each duplicates set. 
               The principal file is chosen carefilly based on some heuristhic methods
"""

    HELP_MODE_PROCESS_DUPLICATES = \
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

    HELP_MODE_RENAME_ALBUMS_FOLDERS = \
f"""
ATTENTION!!!: This process will clean each Subfolder found in <ALBUMS_FOLDER> with an homogeneous name starting with album year followed by a cleaned subfolder name without underscores nor middle dashes.
New Album name format: 'yyyy - Cleaned Subfolder name'
"""

    HELP_MODE_ALL_IN_ONE = \
f"""
ATTENTION!!!: This process will do Automatically all the steps in One Shot.
The script will extract all your Takeout Zip files (if found any .zip) from <INPUT_FOLDER>, after that, will process them, and finally will connect to Synology Photos database to create all Albums found in the Takeout and import all the other photos without any Albums associated.
"""

    ################################
    # EXTRA MODES: SYNOLOGY PHOTOS #
    ################################
    HELP_MODE_SYNOLOGY_UPLOAD_FOLDER = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will upload all Photos/Videos found within <FOLDER> (including subfolders).
              Due to Synology Photos limitations, o Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos.
"""

    HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
              Due to Synology Photos limitations, to Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos. 
"""

    HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to Synology Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder.
              To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3" 
              To extract ALL Albums within in Synology Photos database use 'ALL' as ALBUMS_NAME.
"""

    HELP_MODE_SYNOLOGY_DELETE_EMPTY_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Empty Albums found in Synology Photos database.
"""

    HELP_MODE_SYNOLOGY_DELETE_DUPLICATES_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Duplicates Albums found in Synology Photos database.
"""

    ##############################
    # EXTRA MODES: IMMICH PHOTOS #
    ##############################
    HELP_MODE_IMMICH_UPLOAD_FOLDER = \
f"""
ATTENTION!!!: This process will connect to your to your Immich Photos account and will upload all Photos/Videos found within <FOLDER> (including subfolders).
"""

    HELP_MODE_IMMICH_UPLOAD_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Immich Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
"""

    HELP_MODE_IMMICH_DOWNLOAD_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to Immich Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder.
              To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums "album1", "album2", "album3" 
              To extract ALL Albums within in Immich Photos database use 'ALL' as ALBUMS_NAME.
"""
    HELP_MODE_IMMICH_DOWNLOAD_ALL = \
f"""
ATTENTION!!!: This process will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <FOLDER>..
              All Albums will be downloaded within a subfolder of <FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.
              Assets with no Albums associated will be downloaded withn a subfolder called <FOLDER>/Others/ and will have a year/month structure inside.
"""

    HELP_MODE_IMMICH_DELETE_EMPTY_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Empty Albums found in Immich Photos database.
"""

    HELP_MODE_IMMICH_DELETE_DUPLICATES_ALBUMS = \
f"""
ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Duplicates Albums found in Immich Photos database.
"""

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
    parser = PagedArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=CustomHelpFormatter,  # Aplica el formatter
    )

    # Acción personalizada para --version
    class VersionAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print(f"\n{SCRIPT_NAME} {SCRIPT_VERSION} {SCRIPT_DATE} by Jaime Tur (@jaimetur)\n")
            parser.exit()

    parser.add_argument("-v",  "--version", action=VersionAction, nargs=0, help="Show the script name, version, and date, then exit.")
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
    parser.add_argument("-sg", "--skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool. \nNOT RECOMMENDED!!! because this is the Core of the Script. \nUse this flag only for testing purposses.")
    parser.add_argument("-se", "--skip-extras", action="store_true", help="Skip processing extra photos such as  -edited, -effects photos.")
    parser.add_argument("-sm", "--skip-move-albums", action="store_true", help="Skip moving albums to Albums folder.")
    parser.add_argument("-sa", "--symbolic-albums", action="store_true", help="Creates symbolic links for Albums instead of duplicate the files of each Album. (Useful to save disk space but may not be portable to other systems).")
    parser.add_argument("-it", "--ignore-takeout-structure", action="store_true", help="Ignore Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.")
    parser.add_argument("-mt", "--move-takeout-folder", action="store_true", help=f"Move original photos/videos from <TAKEOUT_FOLDER> to <OUTPUT_FOLDER>. \nCAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!.\nUse only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
    parser.add_argument("-rd", "--remove-duplicates-after-fixing", action="store_true", help="Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.")
    parser.add_argument("-nl", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")

    # EXTRA MODES ARGUMENTS:
    parser.add_argument("-fs", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="The script will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_FOLDER and some Albums seems to be empty.")
    parser.add_argument("-ra", "--rename-albums-folders", metavar="<ALBUMS_FOLDER>", default="", help="Rename all Albums folders found in <ALBUMS_FOLDER> to unificate the format.")
    parser.add_argument("-fd", "--find-duplicates", metavar=f"<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]", nargs="+", default=["list", ""],
        help="Find duplicates in specified folders."
           "\n<ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list' "
           "\n<DUPLICATES_FOLDER> are one or more folders (string or list), where the script will look for duplicates files. The order of this list is important to determine the principal file of a duplicates set. First folder will have higher priority."
        )
    parser.add_argument("-pd", "--process-duplicates-revised", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Specify the Duplicates CSV file revised with specifics Actions in Action column, and the script will execute that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.")
    parser.add_argument("-ao", "--all-in-one", metavar="<INPUT_FOLDER>", default="", help="The Script will do the whole process (Zip extraction, Takeout Processing, Remove Duplicates, Synology Photos Albums creation) in just One Shot.")

    # EXTRA MODES FOR SYNOLOGY PHOTOS
    parser.add_argument("-sde", "--synology-delete-empty-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database.")
    parser.add_argument("-sdd", "--synology-delete-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.")
    parser.add_argument("-suf", "--synology-upload-folder", metavar="<FOLDER>", default="", help="The script will look for all Photos/Videos within <FOLDER> and will upload them into Synology Photos.")
    parser.add_argument("-sua", "--synology-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Synology Photos.")
    parser.add_argument("-sda", "--synology-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
        help="The Script will connect to Synology Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the Synology Photos root folder."
           '\nTo download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3".'
           '\nTo download ALL Albums use "ALL" as <ALBUMS_NAME>.'
        )

    # EXTRA MODES FOR IMMINCH PHOTOS
    parser.add_argument("-ide", "--immich-delete-empty-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is empty, will remove it from Immich Photos database.")
    parser.add_argument("-idd", "--immich-delete-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is duplicated, will remove it from Immich Photos database.")
    parser.add_argument("-iuf", "--immich-upload-folder", metavar="<FOLDER>", default="", help="The script will look for all Photos/Videos within <FOLDER> and will upload them into Immich Photos.")
    parser.add_argument("-iua", "--immich-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Immich Photos.")
    parser.add_argument("-ida", "--immich-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
        help="The Script will connect to Immich Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Immich_Photos_Albums' within the Immich Photos root folder."
           '\nTo download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums" "album1", "album2", "album3".'
           '\nTo download ALL Albums use "ALL" as <ALBUMS_NAME>.'
        )
    parser.add_argument("-iDA", "--immich-download-all", metavar="<FOLDER>", default="",
        help="The Script will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <FOLDER>."
           '\nAll Albums will be downloaded within a subfolder of <FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it.'
           '\nAssets with no Albums associated will be downloaded withn a subfolder called <FOLDER>/Others/ and will have a year/month structure inside.'
        )

    args = parser.parse_args()
    # Procesar la acción y las carpetas
    global DEFAULT_DUPLICATES_ACTION
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
        DEFAULT_DUPLICATES_ACTION = True

    args.duplicates_folders = parse_folders(args.duplicates_folders)

    # Eliminar el argumento original para evitar confusión
    del args.find_duplicates

    args.zip_folder = args.zip_folder.rstrip('/\\')
    args.takeout_folder = args.takeout_folder.rstrip('/\\')
    args.suffix = args.suffix.lstrip('_')
    return args

def get_and_run_execution_mode():
    global EXECUTION_MODE

    # Determine the Execution mode based on the providen arguments:
    if args.fix_symlinks_broken != "":
        EXECUTION_MODE = 'fix_symlinks'
    elif args.duplicates_folders != []:
        EXECUTION_MODE = 'find_duplicates'
    elif args.process_duplicates_revised != "":
        EXECUTION_MODE = 'process_duplicates'
    elif args.rename_albums_folders != "":
        EXECUTION_MODE = 'rename_albums_folders'
    elif args.all_in_one:
        EXECUTION_MODE = 'all_in_one'
    # Synology Photos Modes:
    elif args.synology_upload_folder != "":
        EXECUTION_MODE = 'synology_upload_folder'
    elif args.synology_upload_albums != "":
        EXECUTION_MODE = 'synology_upload_albums'
    elif args.synology_download_albums != "":
        EXECUTION_MODE = 'synology_download_albums'
    elif args.synology_delete_empty_albums:
        EXECUTION_MODE = 'synology_delete_empty_albums'
    elif args.synology_delete_duplicates_albums:
        EXECUTION_MODE = 'synology_delete_duplicates_albums'
    # Immich Photos Modes:
    elif args.immich_upload_folder != "":
        EXECUTION_MODE = 'immich_upload_folder'
    elif args.immich_upload_albums != "":
        EXECUTION_MODE = 'immich_upload_albums'
    elif args.immich_download_albums != "":
        EXECUTION_MODE = 'immich_download_albums'
    elif args.immich_download_all != "":
        EXECUTION_MODE = 'immich_download_all'
    elif args.immich_delete_empty_albums:
        EXECUTION_MODE = 'immich_delete_empty_albums'
    elif args.immich_delete_duplicates_albums:
        EXECUTION_MODE = 'immich_delete_duplicates_albums'
    else:
        EXECUTION_MODE = 'normal'  # Opción por defecto si no se cumple ninguna condición


    # CALL THE DETECTED MODE:
    if EXECUTION_MODE == 'normal':
        mode_normal()
    elif EXECUTION_MODE == 'fix_symlinks':
        mode_fix_symlinkgs()
    elif EXECUTION_MODE == 'find_duplicates':
        mode_find_duplicates()
    elif EXECUTION_MODE == 'process_duplicates':
        mode_process_duplicates()
    elif EXECUTION_MODE == 'rename_albums_folders':
        mode_rename_albums_folders()
    elif EXECUTION_MODE == 'all_in_one':
        mode_all_in_one()
    # Synology Photos Modes:
    elif EXECUTION_MODE == 'synology_upload_folder':
        mode_synology_upload_folder()
    elif EXECUTION_MODE == 'synology_upload_albums':
        mode_synology_upload_albums()
    elif EXECUTION_MODE == 'synology_download_albums':
        mode_synology_download_albums()
    elif EXECUTION_MODE == 'synology_delete_empty_albums':
        mode_synology_delete_empty_albums()
    elif EXECUTION_MODE == 'synology_delete_duplicates_albums':
        mode_synology_delete_duplicates_albums()
    # Immich Photos Modes:
    elif EXECUTION_MODE == 'immich_upload_folder':
        mode_immich_upload_folder()
    elif EXECUTION_MODE == 'immich_upload_albums':
        mode_immich_upload_albums()
    elif EXECUTION_MODE == 'immich_download_albums':
        mode_immich_download_albums()
    elif EXECUTION_MODE == 'immich_download_all':
        mode_immich_download_all()
    elif EXECUTION_MODE == 'immich_delete_empty_albums':
        mode_immich_delete_empty_albums()
    elif EXECUTION_MODE == 'immich_delete_duplicates_albums':
        mode_immich_delete_duplicates_albums()
    else:
        print("Invalid execution mode.")

def main():
    global args
    global LOGGER
    global START_TIME
    global TIMESTAMP
    global OUTPUT_FOLDER
    global LOG_FOLDER_FILENAME
    global DEFAULT_DUPLICATES_ACTION
    global DEPRIORITIZE_FOLDERS_PATTERNS

    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    DEFAULT_DUPLICATES_ACTION = False

    args = parse_arguments()

    # List of Folder to Desprioritize when looking for duplicates.
    DEPRIORITIZE_FOLDERS_PATTERNS = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

    # Create timestamp, start_time and define OUTPUT_FOLDER
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    START_TIME = datetime.now()
    OUTPUT_FOLDER = f"{args.takeout_folder}_{args.suffix}_{TIMESTAMP}"

    # Set a global variable for logger and Set up logger based on the skip-log argument
    log_filename=f"execution_log_{TIMESTAMP}"
    log_folder="Logs"
    LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=args.no_log_file, plain_log=False)

    # Print the Header (common for all modules)
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")

    # Check OS and Terminal
    check_OS_and_Terminal()

    # Set HELP Texts
    set_help_texts()

    # Get the execution mode and run it.
    get_and_run_execution_mode()

def mode_normal(user_confirmation=True):
    # Mensajes informativos
    if not args.zip_folder=="": LOGGER.info(f"INFO: Using Zip folder           : '{args.zip_folder}'")
    LOGGER.info(f"INFO: Using Takeout folder       : '{args.takeout_folder}'")
    LOGGER.info(f"INFO: Using Suffix               : '{args.suffix}'")
    LOGGER.info(f"INFO: Using Output folder        : '{OUTPUT_FOLDER}'")
    LOGGER.info(f"INFO: Albums Folder Structure    : '{args.albums_structure}'")
    LOGGER.info(f"INFO: No Albums Folder Structure : '{args.no_albums_structure}'")
    if not args.no_log_file:
        LOGGER.info(f"INFO: Execution Log file         : '{LOG_FOLDER_FILENAME}'")

    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.info(HELP_MODE_NORMAL)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        if args.zip_folder=="":
            LOGGER.warning(f"WARNING: No argument '-z or --zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if args.move_takeout_folder:
            LOGGER.warning(f"WARNING: Flag detected '-mt, --move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_FOLDER>...")
        if args.symbolic_albums:
            LOGGER.warning(f"WARNING: Flag detected '-sa, --symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if args.skip_gpth_tool:
            LOGGER.warning(f"WARNING: Flag detected '-sg, --skip-gpth-toot'. Skipping Processing photos with GPTH Tool...")
        if args.skip_extras:
            LOGGER.warning(f"WARNING: Flag detected '-se, --skip-extras'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if args.skip_move_albums:
            LOGGER.warning(f"WARNING: Flag detected '-sm, --skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if args.albums_structure.lower()!='flatten':
            LOGGER.warning(f"WARNING: Flag detected '-as, --albums-structure'. Folder structure '{args.albums_structure}' will be applied on each Album folder...")
        if args.no_albums_structure.lower()!='year/month':
            LOGGER.warning(f"WARNING: Flag detected '-ns, --no-albums-structure'. Folder structure '{args.no_albums_structure}' will be applied on ALL_PHOTOS folder (Photos without Albums)...")
        if args.ignore_takeout_structure:
            LOGGER.warning(f"WARNING: Flag detected '-it, --ignore-takeout-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if args.remove_duplicates_after_fixing:
            LOGGER.warning(f"WARNING: Flag detected '-rd, --remove-duplicates-after-fixing'. All duplicates files within OUTPUT_FOLDER will be removed after fixing them...")
        if args.no_log_file:
            LOGGER.warning(f"WARNING: Flag detected '-sl, --skip-log'. Skipping saving output into log file...")


    # STEP 1: Unzip files
    STEP=1
    LOGGER.info("")
    LOGGER.info("==============================")
    LOGGER.info(f"{STEP}. UNPACKING TAKEOUT FOLDER...")
    LOGGER.info("==============================")
    LOGGER.info("")
    if not args.zip_folder=="":
        step_start_time = datetime.now()
        Utils.unpack_zips(args.zip_folder, args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Unzipping skipped (no argument '-z or --zip-folder <ZIP_FOLDER>' given or Running Mode All-in-One with input folder directly unzipped).")

    if not os.path.isdir(args.takeout_folder):
        LOGGER.error(f"ERROR: Cannot Find TAKEOUT_FOLDER: '{args.takeout_folder}'. Exiting...")
        sys.exit(-1)

    # STEP 2: Pre-Process Takeout folder
    STEP+=1
    LOGGER.info("")
    LOGGER.info("===================================")
    LOGGER.info(f"{STEP}. PRE-PROCESSING TAKEOUT FOLDER...")
    LOGGER.info("===================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    # Delete hidden subgolders '€eaDir' (Synology metadata folder) if exists
    LOGGER.info("INFO: Deleting hidden subfolders '@eaDir' (Synology metadata folders) from Takeout Folder if exists...")
    Utils.delete_subfolders(args.takeout_folder, "@eaDir")
    # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
    LOGGER.info("")
    LOGGER.info("INFO: Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
    Utils.fix_mp4_files(args.takeout_folder)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    LOGGER.info("")
    LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 3: Process photos with GPTH Tool or copy directly to output folder if GPTH tool is skipped
    STEP+=1
    LOGGER.info("")
    LOGGER.info("===========================================")
    LOGGER.info(f"{STEP}. FIXING PHOTOS METADATA WITH GPTH TOOL...")
    LOGGER.info("===========================================")
    LOGGER.info("")
    if not args.skip_gpth_tool:
        if args.ignore_takeout_structure:
            LOGGER.warning("WARNING: Ignore Google Takeout Structure detected ('-it, --ignore-takeout-structure' flag detected).")
        step_start_time = datetime.now()
        Fixers.fix_metadata_with_gpth_tool(
            input_folder=args.takeout_folder,
            output_folder=OUTPUT_FOLDER,
            symbolic_albums=args.symbolic_albums,
            skip_extras=args.skip_extras,
            move_takeout_folder=args.move_takeout_folder,
            ignore_takeout_structure=args.ignore_takeout_structure
        )
        if args.move_takeout_folder:
            Utils.force_remove_directory(args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    if args.skip_gpth_tool or args.ignore_takeout_structure:
        LOGGER.info("")
        LOGGER.info("============================================")
        LOGGER.info(f"{STEP}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
        LOGGER.info("============================================")
        LOGGER.info("")
        if args.skip_gpth_tool:
            LOGGER.warning(f"WARNING: Metadata fixing with GPTH tool skipped ('-sg, --skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
        elif args.ignore_takeout_structure:
            LOGGER.warninf(f"WARNING: Flag to Ignore Google Takeout Structure have been detected ('-it, --ignore-takeout-structure'). Step {STEP}b is needed to copy/move files manually to output folder.")
        if args.move_takeout_folder:
            LOGGER.info("INFO: Moving files from Takeout folder to Output folder manually...")
        else:
            LOGGER.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder (args.takeout_folder, OUTPUT_FOLDER, ignore_patterns=['*.json', '*.j'], move=args.move_takeout_folder)
        if args.move_takeout_folder:
            Utils.force_remove_directory(args.takeout_folder)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP}b completed in {formatted_duration}.")

    # STEP 4: Sync .MP4 live pictures timestamp
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==============================================================")
    LOGGER.info(f"{STEP}. SYNC TIMESTAMPS OF .MP4 with IMAGES (.HEIC, .JPG, .JPEG)...")
    LOGGER.info("==============================================================")
    LOGGER.info("")
    step_start_time = datetime.now()
    LOGGER.info("INFO: Fixing Timestamps of '.MP4' file with Live pictures files (.HEIC, .JPG, .JPEG) if both files have the same name and are in the same folder...")
    Utils.sync_mp4_timestamps_with_images(OUTPUT_FOLDER)
    step_end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
    LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")


    # STEP 5: Create Folders Year/Month or Year only structure
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==========================================")
    LOGGER.info(f"{STEP}. CREATING YEAR/MONTH FOLDER STRUCTURE...")
    LOGGER.info("==========================================")
    step_start_time = datetime.now()
    # For Albums:
    if args.albums_structure.lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{args.albums_structure.lower()}' for each Album folder...")
        basedir=OUTPUT_FOLDER
        type=args.albums_structure
        exclude_subfolders=['ALL_PHOTOS']
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # For No Albums:
    if args.no_albums_structure.lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{args.no_albums_structure.lower()}' for ALL_PHOTOS folder...")
        basedir=os.path.join(OUTPUT_FOLDER, 'ALL_PHOTOS')
        type=args.no_albums_structure
        exclude_subfolders=[]
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # If no fiolder structure is detected:
    if args.albums_structure.lower()=='flatten' and args.no_albums_structure.lower()=='flatten' :
        LOGGER.info("")
        LOGGER.warning("WARNING: No argument '-as, --albums-structure' and '-ns, --no-albums-structure' detected. All photos and videos will be flattened within their folders without any date organization.")
    else:
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # STEP 6: Move albums
    STEP+=1
    LOGGER.info("")
    LOGGER.info("==========================")
    LOGGER.info(f"{STEP}. MOVING ALBUMS FOLDER...")
    LOGGER.info("==========================")
    LOGGER.info("")
    if not args.skip_move_albums:
        step_start_time = datetime.now()
        Utils.move_albums(OUTPUT_FOLDER, exclude_subfolder=["ALL_PHOTOS", "@eaDir"])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --skip-move-albums' flag detected).")

    # STEP 7: Fix Broken Symbolic Links after moving
    STEP+=1
    symlink_fixed = 0
    symlink_not_fixed = 0
    LOGGER.info("")
    LOGGER.info("===============================================")
    LOGGER.info(f"{STEP}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
    LOGGER.info("===============================================")
    LOGGER.info("")
    if args.symbolic_albums:
        LOGGER.info("INFO: Fixing broken symbolic links. This step is needed after moving any Folder structure...")
        step_start_time = datetime.now()
        symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(OUTPUT_FOLDER)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Fixing broken symbolic links skipped ('-sa, --symbolic-albums' flag not detected, so this step is not needed.)")

    # STEP 8: Remove Duplicates in OUTPUT_FOLDER after Fixing
    STEP+=1
    duplicates_found = 0
    if args.remove_duplicates_after_fixing:
        LOGGER.info("")
        LOGGER.info("==========================================")
        LOGGER.info(f"{STEP}. REMOVING DUPLICATES IN OUTPUT_FOLDER...")
        LOGGER.info("==========================================")
        LOGGER.info("")
        LOGGER.info("INFO: Removing duplicates from OUTPUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'ALL_PHOTOS' folders)...")
        step_start_time = datetime.now()
        duplicates_found = find_duplicates(duplicates_action='remove', duplicates_folders=OUTPUT_FOLDER, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS, timestamp=TIMESTAMP)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")

    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info(f"INFO: All the Photos/Videos Fixed can be found on folder: '{OUTPUT_FOLDER}'")
    LOGGER.info("")
    LOGGER.info("===============================================")
    LOGGER.info("                FINAL SUMMARY:                 ")
    LOGGER.info("===============================================")
    LOGGER.info(f"Total files in Takeout folder        : {Utils.count_files_in_folder(args.takeout_folder)}")
    LOGGER.info(f"Total final files in Output folder   : {Utils.count_files_in_folder(OUTPUT_FOLDER)}")
    albums_found = 0
    if not args.skip_move_albums:
        album_folder = os.path.join(OUTPUT_FOLDER, 'Albums')
        if os.path.isdir(album_folder):
            albums_found = len(os.listdir(album_folder))
    else:
        if os.path.isdir(OUTPUT_FOLDER):
            albums_found = len(os.listdir(OUTPUT_FOLDER))-1
    LOGGER.info(f"Total Albums folders found           : {albums_found}")
    if args.symbolic_albums:
        LOGGER.info(f"Total Symlinks Fixed                 : {symlink_fixed}")
        LOGGER.info(f"Total Symlinks Not Fixed             : {symlink_not_fixed}")
    if args.remove_duplicates_after_fixing:
        LOGGER.info(f"Total Duplicates Removed             : {duplicates_found}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                   : {formatted_duration}")
    LOGGER.info("===============================================")
    LOGGER.info("")

def mode_fix_symlinkgs(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(HELP_MODE_FIX_SYMLINKS.replace('<FOLDER_TO_FIX>', f"'{args.fix_symlinks_broken}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Fixing broken symbolic links Mode detected. Only this module will be run!!!")
    LOGGER.info(f"INFO: Fixing broken symbolic links in folder '{args.fix_symlinks_broken}'...")
    symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(args.fix_symlinks_broken)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Fixed Symbolic Links              : {symlinks_fixed}")
    LOGGER.info(f"Total No Fixed Symbolic Links           : {symlinks_not_fixed}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_find_duplicates(interactive_mode=True):
    LOGGER.info(f"INFO: Duplicates Action             : {args.duplicates_action}")
    LOGGER.info(f"INFO: Find Duplicates in Folders    : {args.duplicates_folders}")
    LOGGER.info("")
    if interactive_mode:
        LOGGER.info(HELP_MODE_FIND_DUPLICATES.replace('<DUPLICATES_FOLDER>', f"'{args.duplicates_folders}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"WARNING: Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
    duplicates_files_found = find_duplicates(duplicates_action=args.duplicates_action, duplicates_folders=args.duplicates_folders, deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
    if duplicates_files_found == -1:
        LOGGER.error("ERROR: Exiting because some of the folder(s) given in argument '-fd, --find-duplicates' does not exists.")
        sys.exit(-1)

    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Duplicates Found                  : {duplicates_files_found}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_process_duplicates(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(HELP_MODE_PROCESS_DUPLICATES)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Flag detected '-pd, --process-duplicates-revised'. The Script will process the '{args.process_duplicates_revised}' file and do the specified action given on Action Column. ")
    LOGGER.info(f"INFO: Processing Duplicates Files based on Actions given in {os.path.basename(args.process_duplicates_revised)} file...")
    removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(args.process_duplicates_revised)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Removed Duplicates                : {removed_duplicates}")
    LOGGER.info(f"Total Restored Duplicates               : {restored_duplicates}")
    LOGGER.info(f"Total Replaced Duplicates               : {replaced_duplicates}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")


def mode_rename_albums_folders(user_confirmation=True):
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")
    if user_confirmation:
        LOGGER.info(HELP_MODE_RENAME_ALBUMS_FOLDERS.replace('<ALBUMS_FOLDER>', f"'{args.rename_albums_folders}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-ra, --rename-albums-folders'. The Script will look for any Subfolder in '{args.rename_albums_folders}' and will rename the folder name in order to unificate all the Albums names.")
    renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(args.rename_albums_folders)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums folders renamed             : {renamed_album_folders}")
    LOGGER.info(f"Total Albums folders duplicated          : {duplicates_album_folders}")
    LOGGER.info(f"Total Albums duplicated fully merged     : {duplicates_albums_fully_merged}")
    LOGGER.info(f"Total Albums duplicated not fully merged : {duplicates_albums_not_fully_merged}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                       : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")


#################################
# EXTRA MODES: SYNOLOGY PHOTOS: #
#################################
def mode_synology_upload_folder(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-suf, --synology-upload-folder'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_UPLOAD_FOLDER.replace('<FOLDER>', f"'{args.synology_upload_folder}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {args.synology_upload_folder}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = synology_upload_folder(args.synology_upload_folder)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")


def mode_synology_upload_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sua, --synology-upload-albums'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS.replace('<ALBUMS_FOLDER>', f"'{args.synology_upload_albums}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {args.synology_upload_albums}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = synology_upload_albums(args.synology_upload_albums)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums created                    : {albums_crated}")
    LOGGER.info(f"Total Albums skipped                    : {albums_skipped}")
    LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_synology_download_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sda, --synology-download-albums'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS.replace('<ALBUMS_NAME>', f"'{args.synology_download_albums}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Albums to extract       : {args.synology_download_albums}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, photos_downloaded = synology_download_albums(args.synology_download_albums)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
    LOGGER.info(f"Total Photos downlaoded from Albums     : {photos_downloaded}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_synology_delete_empty_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sde, --synology-delete-empty-albums'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_DELETE_EMPTY_ALBUMS)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Delete Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-sde, --synology-delete-empty-albums'. The Script will look for any empty album in Synology Photos database and will detelte them (if any enpty album is found).")
    # Call the Funxtion
    albums_deleted = synology_delete_empty_albums()
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Empty Albums deleted              : {albums_deleted}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_synology_delete_duplicates_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-sdd, --synology-delete-deuplicates-albums'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_DELETE_DUPLICATES_ALBUMS)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Delete Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-sdd, --synology-delete-duplicates-albums'. The Script will look for any duplicated album in Synology Photos database and will detelte them (if any duplicated album is found).")
    # Call the Funxtion
    albums_deleted = synology_delete_duplicates_albums()
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Duplicates Albums deleted         : {albums_deleted}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")


###############################
# EXTRA MODES: IMMICH PHOTOS: #
###############################
def mode_immich_upload_folder(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iua, --immich-upload-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_UPLOAD_FOLDER.replace('<FOLDER>', f"'{args.immich_upload_folder}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {args.immich_upload_folder}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = immich_upload_folder(args.immich_upload_folder)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Photos/Videos Uploaded            : {photos_added}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_immich_upload_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iua, --immich-upload-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_UPLOAD_ALBUMS.replace('<ALBUMS_FOLDER>', f"'{args.immich_upload_albums}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {args.immich_upload_albums}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = immich_upload_albums(args.immich_upload_albums)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums created                    : {albums_crated}")
    LOGGER.info(f"Total Albums skipped                    : {albums_skipped}")
    LOGGER.info(f"Total Photos added to Albums            : {photos_added}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_immich_download_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-ida, --immich-download-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_DOWNLOAD_ALBUMS.replace('<ALBUMS_NAME>', f"{args.immich_download_albums}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {args.immich_upload_albums}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_albums(args.immich_download_albums)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
    LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_immich_download_all(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iDA, --immich-download-all'.")
        LOGGER.info(HELP_MODE_IMMICH_DOWNLOAD_ALL.replace('<FOLDER>', f"{args.immich_download_all}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {args.immich_upload_albums}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_all(args.immich_download_all)
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Albums downloaded                 : {albums_downloaded}")
    LOGGER.info(f"Total Assets downloaded                 : {assets_downloaded}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_immich_delete_empty_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-ide, --immich-delete-empty-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_DELETE_EMPTY_ALBUMS)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete Empty Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-ide, --immich-delete-empty-albums'. The Script will look for any empty album in Immich Photos database and will detelte them (if any enpty album is found).")
    # Call the Funxtion
    albums_deleted = immich_delete_empty_albums()
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Empty Albums deleted              : {albums_deleted}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_immich_delete_duplicates_albums(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-idd, --immich-delete-deuplicates-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_DELETE_DUPLICATES_ALBUMS)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Delete Duplicates Album' Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-idd, --immich-delete-duplicates-albums'. The Script will look for any duplicated album in Immich Photos database and will detelte them (if any duplicated album is found).")
    # Call the Funxtion
    albums_deleted = immich_delete_duplicates_albums()
    # FINAL SUMMARY
    end_time = datetime.now()
    formatted_duration = str(timedelta(seconds=(end_time - START_TIME).seconds))
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("         PROCESS COMPLETED SUCCESSFULLY!          ")
    LOGGER.info("==================================================")
    LOGGER.info("")
    LOGGER.info("==================================================")
    LOGGER.info("                  FINAL SUMMARY:                  ")
    LOGGER.info("==================================================")
    LOGGER.info(f"Total Duplicates Albums deleted         : {albums_deleted}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                      : {formatted_duration}")
    LOGGER.info("==================================================")
    LOGGER.info("")

def mode_all_in_one():
    global OUTPUT_FOLDER
    LOGGER.info(f"INFO: All-in-One Mode detected")
    LOGGER.info(HELP_MODE_ALL_IN_ONE.replace('<INPUT_FOLDER>', f"'{args.all_in_one}'"))
    if not Utils.confirm_continue():
        LOGGER.info(f"INFO: Exiting program.")
        sys.exit(0)

    config = read_synology_config(show_info=False)
    if not config['ROOT_PHOTOS_PATH']:
        LOGGER.warning(f"WARNING: Caanot find 'ROOT_PHOTOS_PATH' info in 'nas.config' file. Albums will not be created into Synology Photos database")
    else:
        OUTPUT_FOLDER = os.path.join(config['ROOT_PHOTOS_PATH'], f'Google Photos_{TIMESTAMP}')

    res, _ = login_synology()
    if res==-1:
        LOGGER.warning(f"WARNING: Cannot connect to Synology Photos. Albums will not be created into Synology Photos database")

    # Configure the Normal Execution Arguments and RUN Normal Execution
    input_folder = args.all_in_one
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        args.zip_folder = input_folder
        args.move_takeout_folder = True
    else:
        args.takeout_folder = input_folder
    args.remove_duplicates_after_fixing = True
    mode_normal(user_confirmation=False)

    # Configure the Create_Synology_Albums and run create_synology_albums()
    albums_folder = os.path.join(OUTPUT_FOLDER, f'Albums')
    args.synology_upload_albums = albums_folder
    LOGGER.info("")
    mode_synology_upload_albums(user_confirmation=False)

    # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
    mode_synology_delete_duplicates_albums(user_confirmation=False)
    mode_synology_delete_empty_albums(user_confirmation=False)


if __name__ == "__main__":
    # Verificar si el script se ejecutó sin argumentos
    if len(sys.argv) == 1:
        # Agregar argumento predeterminado
        sys.argv.append("-z")
        sys.argv.append("Zip_folder")
        print(f"INFO: No argument detected. Using default value '{sys.argv[2]}' for <ZIP_FOLDER'.")
    main()
