import os,sys
import argparse
import platform
from datetime import datetime, timedelta
import Utils
import Fixers
import textwrap
from Duplicates import find_duplicates, process_duplicates_actions
from SynologyPhotos import read_synology_config, login_synology, synology_delete_empty_albums, synology_delete_duplicates_albums, synology_upload_folder, synology_upload_albums, synology_download_albums, synology_download_ALL
from ImmichPhotos import read_immich_config, login_immich, immich_delete_empty_albums, immich_delete_duplicates_albums, immich_upload_folder, immich_upload_albums, immich_download_albums, immich_download_ALL
from CustomHelpFormatter import CustomHelpFormatter, PagedArgumentParser
from LoggerConfig import log_setup

# Script version & date
SCRIPT_NAME         = "CloudPhotoMigrator"
SCRIPT_VERSION      = "v3.0.0-alpha"
SCRIPT_DATE         = "2025-02-01"

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
    global HELP_MODE_GOOGLE_TAKEOUT
    global HELP_MODE_FIX_SYMLINKS
    global HELP_MODE_FIND_DUPLICATES
    global HELP_MODE_PROCESS_DUPLICATES
    global HELP_MODE_RENAME_ALBUMS_FOLDERS
    global HELP_MODE_ALL_IN_ONE

    global HELP_MODE_SYNOLOGY_DELETE_EMPTY_ALBUMS
    global HELP_MODE_SYNOLOGY_DELETE_DUPLICATES_ALBUMS
    global HELP_MODE_SYNOLOGY_UPLOAD_FOLDER
    global HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS
    global HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS
    global HELP_MODE_SYNOLOGY_DOWNLOAD_ALL

    global HELP_MODE_IMMICH_DELETE_EMPTY_ALBUMS
    global HELP_MODE_IMMICH_DELETE_DUPLICATES_ALBUMS
    global HELP_MODE_IMMICH_UPLOAD_FOLDER
    global HELP_MODE_IMMICH_UPLOAD_ALBUMS
    global HELP_MODE_IMMICH_DOWNLOAD_ALBUMS
    global HELP_MODE_IMMICH_DOWNLOAD_ALL

    HELP_MODE_GOOGLE_TAKEOUT = textwrap.dedent(f"""
        ATTENTION!!!: This process will process your <TAKEOUT_FOLDER> to fix metadata of all your asets and organize them according with the settings defined by user (above settings).
        """)

    HELP_MODE_FIX_SYMLINKS = textwrap.dedent(f"""
        ATTENTION!!!: This process will look for all Symbolic Links broken in <FOLDER_TO_FIX> and will try to find the destination file within the same folder.
        """)

    HELP_MODE_FIND_DUPLICATES = textwrap.dedent(f"""
        ATTENTION!!!: This process will process all Duplicates files found in <DUPLICATES_FOLDER> and will apply the given action.
                      You must take into account that if not valid action is detected within the arguments of -fd, --find-duplicates, then 'list' will be the default action.
        
        Possible duplicates-action are:
            - list   : This action is not dangerous, just list all duplicates files found in a Duplicates.csv file.
            - move   : This action could be dangerous but is easily reversible if you find that any duplicated file have been moved to Duplicates folder and you want to restore it later
                       You can easily restore it using option -pd, --process-duplicates
            - remove : This action could be dangerous and is irreversible, since the script will remove all duplicates found and will keep only a Principal file per each duplicates set. 
                       The principal file is chosen carefilly based on some heuristhic methods
        """)

    HELP_MODE_PROCESS_DUPLICATES = textwrap.dedent(f"""
        ATTENTION!!!: This process will process all Duplicates files found with -fd, --find-duplicates <DUPLICATES_FOLDER> option based on the Action column value of Duplicates.csv file generated in 'Find Duplicates Mode'. 
        
        You can modify individually each Action column value for each duplicate found, but take into account that the below actions list are irreversible:
        
        Possible Actions in revised CSV file are:
            - remove_duplicate  : Duplicated file moved to Duplicates folder will be permanentely removed
            - restore_duplicate : Duplicated file moved to Duplicates folder will be restored to its original location
            - replace_duplicate : This action can be used to replace the principal file chosen for each duplicates and select manually other principal file
                                  Duplicated file moved to Duplicates folder will be restored to its original location as principal file
                                  and Original Principal file detected by the Script will be removed permanently
        """)

    HELP_MODE_RENAME_ALBUMS_FOLDERS = textwrap.dedent(f"""
        ATTENTION!!!: This process will clean each Subfolder found in <ALBUMS_FOLDER> with an homogeneous name starting with album year followed by a cleaned subfolder name without underscores nor middle dashes.
        New Album name format: 'yyyy - Cleaned Subfolder name'
        """)

    HELP_MODE_ALL_IN_ONE = textwrap.dedent(f"""
        ATTENTION!!!: This process will do Automatically all the steps in One Shot.
        The script will extract all your Takeout Zip files (if found any .zip) from <INPUT_FOLDER>, after that, will process them, and finally will connect to Synology Photos database to create all Albums found in the Takeout and import all the other photos without any Albums associated.
        """)

    ################################
    # EXTRA MODES: SYNOLOGY PHOTOS #
    ################################
    HELP_MODE_SYNOLOGY_DELETE_EMPTY_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Empty Albums found in Synology Photos database.
        """)

    HELP_MODE_SYNOLOGY_DELETE_DUPLICATES_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will delete all Duplicates Albums found in Synology Photos database.
        """)
    
    HELP_MODE_SYNOLOGY_UPLOAD_FOLDER = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will upload all Photos/Videos found within <FOLDER> (including subfolders).
                      Due to Synology Photos limitations, o Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos.
        """)

    HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Synology Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
                      Due to Synology Photos limitations, to Upload any folder, it must be placed inside SYNOLOGY_ROOT_FOLDER and all its content must have been indexed before to add any asset to Synology Photos. 
        """)

    HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Synology Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder 'Synology_Photos_Albums' within the SYNOLOGY_ROOT_FOOLDER. 
                      If the file already exists, it will be OVERWRITTEN!!!
                      To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: dron* to download all albums starting with the word 'dron' followed by other(s) words.
                      To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums "album1", "album2", "album3" 
                      To extract ALL Albums within in Synology Photos database use 'ALL' as ALBUMS_NAME.
        """)
    
    HELP_MODE_SYNOLOGY_DOWNLOAD_ALL = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Synology Photos and will download all the Album and Assets without Albums into the folder '<OUTPUT_FOLDER>' within the SYNOLOGY_ROOT_FOOLDER. 
                      If the file already exists, it will be OVERWRITTEN!!!
                      All Albums will be downloaded within a subfolder of '<OUTPUT_FOLDER>/Albums' with the same name of the Album and all files will be flattened into it.
                      Assets with no Albums associated will be downloaded withn a subfolder '<OUTPUT_FOLDER>/Others' and will have a year/month structure inside.
        """)


    ##############################
    # EXTRA MODES: IMMICH PHOTOS #
    ##############################
    HELP_MODE_IMMICH_DELETE_EMPTY_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Empty Albums found in Immich Photos database.
        """)

    HELP_MODE_IMMICH_DELETE_DUPLICATES_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will delete all Duplicates Albums found in Immich Photos database.
        """)
    
    HELP_MODE_IMMICH_UPLOAD_FOLDER = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will upload all Photos/Videos found within <FOLDER> (including subfolders).
        """)

    HELP_MODE_IMMICH_UPLOAD_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to your to your Immich Photos account and will create a new Album for each Subfolder found in <ALBUMS_FOLDER> and will include all Photos and Videos included in that Subfolder.
        """)

    HELP_MODE_IMMICH_DOWNLOAD_ALBUMS = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Immich Photos and extract those Album(s) whose name is in <ALBUMS_NAME> to the folder './Downloads_Immich' within the Script execution folder. 
                      If the file already exists, it will be OVERWRITTEN!!!
                      To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: dron* to download all albums starting with the word 'dron' followed by other(s) words.
                      To extract several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums "album1", "album2", "album3" 
                      To extract ALL Albums within in Immich Photos database use 'ALL' as ALBUMS_NAME.
        """)

    HELP_MODE_IMMICH_DOWNLOAD_ALL = textwrap.dedent(f"""
        ATTENTION!!!: This process will connect to Immich Photos and will download all the Album and Assets without Albums into the folder './<OUTPUT_FOLDER>'. 
                      If the file already exists, it will be OVERWRITTEN!!!.
                      All Albums will be downloaded within a subfolder of './<OUTPUT_FOLDER>/Albums' with the same name of the Album and all files will be flattened into it.
                      Assets with no Albums associated will be downloaded withn a subfolder './<OUTPUT_FOLDER>/Others' and will have a year/month structure inside.
        """)

def create_global_variable_from_args(args):
    """
    Crea una única variable global ARGS que contenga todos los argumentos proporcionados en un objeto Namespace.
    Se puede acceder a cada argumento mediante ARGS["nombre-argumento"] o ARGS.nombre_argumento.

    :param args: Namespace con los argumentos del PARSER
    """
    ARGS = {arg_name.replace("_", "-"): arg_value for arg_name, arg_value in vars(args).items()}
    return ARGS


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

    # # Regular Parser without Pagination
    # PARSER = argparse.ArgumentParser(
    #         description=SCRIPT_DESCRIPTION,
    #         formatter_class=CustomHelpFormatter,  # Aplica el formatter
    # )

    # Parser with Pagination:
    global PARSER
    PARSER = PagedArgumentParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=CustomHelpFormatter,  # Aplica el formatter
    )

    # Acción personalizada para --version
    class VersionAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print(f"\n{SCRIPT_NAME} {SCRIPT_VERSION} {SCRIPT_DATE} by Jaime Tur (@jaimetur)\n")
            parser.exit()

    PARSER.add_argument("-v", "--version", action=VersionAction, nargs=0, help="Show the script name, version, and date, then exit.")
    PARSER.add_argument("-nlog", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")
    PARSER.add_argument("-AUTO", "--AUTOMATED-MIGRATION", metavar="<INPUT_FOLDER>", default="", help="The Script will do the whole migration process (Zip extraction, Takeout Processing, Remove Duplicates, Synology Photos Albums creation) in just One Shot.")

    # EXTRA MODES FOR GOOGLE PHOTOS:
    # ------------------------------
    # PARSER.add_argument("-gizf", "--google-input-zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
    PARSER.add_argument("-gitf", "--google-input-takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If -z, --zip-folder is present, this will be the folder to unzip input files. Default: 'Takeout'.")
    PARSER.add_argument("-gofs", "--google-output-folder-suffix", metavar="<SUFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
    PARSER.add_argument("-gafs", "--google-albums-folders-structure", metavar=f"{choices_for_folder_structure}", default="flatten", help="Specify the type of folder structure for each Album folder (Default: 'flatten')."
                        , type=lambda s: s.lower()  # Convert input to lowercase
                        , choices=choices_for_folder_structure  # Valid choices
                        )
    PARSER.add_argument("-gnas", "--google-no-albums-folder-structure", metavar=f"{choices_for_folder_structure}", default="year/month", help="Specify the type of folder structure for 'Others' folder (Default: 'year/month')."
                        , type=lambda s: s.lower()  # Convert input to lowercase
                        , choices=choices_for_folder_structure  # Valid choices
                        )
    PARSER.add_argument("-gcsa", "--google-create-symbolic-albums", action="store_true", help="Creates symbolic links for Albums instead of duplicate the files of each Album. (Useful to save disk space but may not be portable to other systems).")
    PARSER.add_argument("-gics", "--google-ignore-check-structure", action="store_true", help="Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.")
    PARSER.add_argument("-gmtf", "--google-move-takeout-folder", action="store_true", help=f"Move original assets to <OUTPUT_FOLDER>. \nCAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!.\nUse only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
    PARSER.add_argument("-grdf", "--google-remove-duplicates-files", action="store_true", help="Remove Duplicates files in <OUTPUT_FOLDER> after fixing them.")
    PARSER.add_argument("-gsef", "--google-skip-extras-files", action="store_true", help="Skip processing extra photos such as  -edited, -effects photos.")
    PARSER.add_argument("-gsma", "--google-skip-move-albums", action="store_true", help="Skip moving albums to 'Albums' folder.")
    PARSER.add_argument("-gsgt", "--google-skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool. \nCAUTION: This option is NOT RECOMMENDED because this is the Core of the Google Photos Takeout Process. Use this flag only for testing purposses.")

    # EXTRA MODES FOR SYNOLOGY PHOTOS:
    # --------------------------------
    PARSER.add_argument("-sde", "--synology-delete-empty-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database.")
    PARSER.add_argument("-sdd", "--synology-delete-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.")
    PARSER.add_argument("-suf", "--synology-upload-folder", metavar="<FOLDER>", default="", help="The script will look for all Photos/Videos within <FOLDER> and will upload them into Synology Photos.")
    PARSER.add_argument("-sua", "--synology-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Synology Photos.")
    PARSER.add_argument("-sda", "--synology-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Script will connect to Synology Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Download_Synology' within the Synology Photos root folder."
           "\n- To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --synology-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums 'album1', 'album2', 'album3'."
           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                        )
    PARSER.add_argument("-sdA", "--synology-download-ALL", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Script will connect to Synology Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
           "\n- Assets with no Albums associated will be downloaded withn a subfolder called <OUTPUT_FOLDER>/Others/ and will have a year/month structure inside."
                        )
    
    # EXTRA MODES FOR IMMINCH PHOTOS:
    # -------------------------------
    PARSER.add_argument("-ide", "--immich-delete-empty-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is empty, will remove it from Immich Photos database.")
    PARSER.add_argument("-idd", "--immich-delete-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is duplicated, will remove it from Immich Photos database.")
    PARSER.add_argument("-iuf", "--immich-upload-folder", metavar="<FOLDER>", default="", help="The script will look for all Photos/Videos within <FOLDER> and will upload them into Immich Photos.")
    PARSER.add_argument("-iua", "--immich-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Albums within <ALBUMS_FOLDER> and will create one Album per folder into Immich Photos.")
    PARSER.add_argument("-ida", "--immich-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Script will connect to Immich Photos and download the Album whose name is <ALBUMS_NAME> to the folder 'Download_Immich' within the script execution folder."
           "\n- To extract all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --immich-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums 'album1', 'album2', 'album3'."
           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                        )
    PARSER.add_argument("-idA", "--immich-download-ALL", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Script will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
           "\n- Assets with no Albums associated will be downloaded withn a subfolder called <OUTPUT_FOLDER>/Others/ and will have a year/month structure inside."
                        )

    # OTHERS STAND-ALONE EXTRA MODES:
    # -------------------------------
    PARSER.add_argument("-fdup", "--find-duplicates", metavar=f"<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]", nargs="+", default=["list", ""],
                        help="Find duplicates in specified folders."
           "\n<ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list' "
           "\n<DUPLICATES_FOLDER> are one or more folders (string or list), where the script will look for duplicates files. The order of this list is important to determine the principal file of a duplicates set. First folder will have higher priority."
                        )
    PARSER.add_argument("-pdup", "--process-duplicates", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Specify the Duplicates CSV file revised with specifics Actions in Action column, and the script will execute that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.")
    PARSER.add_argument("-fsym", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="The script will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_FOLDER and some Albums seems to be empty.")
    PARSER.add_argument("-frcb", "--folders-rename-content-based", metavar="<ALBUMS_FOLDER>", default="", help="Usefull to rename all Albums folders found in <ALBUMS_FOLDER> based on the date content found homogenize the name.")

    # Procesar la acción y las carpetas
    global DEFAULT_DUPLICATES_ACTION

    # Obtain args from PARSER and create global variable ARGS to easier manipulation of argument variables using the same string as in the argument (this facilitates futures refactors on arguments names)
    args = PARSER.parse_args()
    ARGS = create_global_variable_from_args(args)

    ARGS['duplicates-folders'] = []
    ARGS['duplicates-action'] = ""
    for subarg in ARGS['find-duplicates']:
        if subarg.lower() in choices_for_remove_duplicates:
            ARGS['duplicates-action'] = subarg
        else:
            if subarg != "":
                ARGS['duplicates-folders'].append(subarg)
    if ARGS['duplicates-action'] == "" and ARGS['duplicates-folders'] !=[]:
        ARGS['duplicates-action'] = 'list'  # Valor por defecto
        DEFAULT_DUPLICATES_ACTION = True

    ARGS['duplicates-folders'] = parse_folders(ARGS['duplicates-folders'] )

    # ARGS['google-input-zip-folder'] = ARGS['google-input-zip-folder'].rstrip('/\\')
    ARGS['google-input-takeout-folder'] = ARGS['google-input-takeout-folder'].rstrip('/\\')
    ARGS['google-output-folder-suffix'] = ARGS['google-output-folder-suffix'].lstrip('_')
    return ARGS

# -------------------------------------------------------------
# Determine the Execution mode based on the providen arguments:
# -------------------------------------------------------------
def detect_and_run_execution_mode():
    global EXECUTION_MODE

    # AUTOMATED-MIGRATION MODE:
    if ARGS['AUTOMATED-MIGRATION']:
        EXECUTION_MODE = 'AUTOMATED-MIGRATION'
        mode_AUTOMATED_MIGRATION()

    # Google Photos Mode:
    elif "-gitf" in sys.argv or "--google-input-takeout-folder" in sys.argv:
        EXECUTION_MODE = 'google-takeout'
        mode_google_takeout()


    # Synology Photos Modes:
    elif ARGS['synology-delete-empty-albums']:
        EXECUTION_MODE = 'synology-delete-empty-albums'
        mode_synology_delete_empty_albums()
    elif ARGS['synology-delete-duplicates-albums']:
        EXECUTION_MODE = 'synology-delete-duplicates-albums'
        mode_synology_delete_duplicates_albums()
    elif ARGS['synology-upload-folder'] != "":
        EXECUTION_MODE = 'synology-upload-folder'
        mode_synology_upload_folder()
    elif ARGS['synology-upload-albums'] != "":
        EXECUTION_MODE = 'synology-upload-albums'
        mode_synology_upload_albums()
    elif ARGS['synology-download-albums'] != "":
        EXECUTION_MODE = 'synology-download-albums'
        mode_synology_download_albums()
    elif ARGS['synology-download-ALL'] != "":
        EXECUTION_MODE = 'synology-download-ALL'
        mode_synology_download_ALL()

    # Immich Photos Modes:
    elif ARGS['immich-delete-empty-albums']:
        EXECUTION_MODE = 'immich-delete-empty-albums'
        mode_immich_delete_empty_albums()
    elif ARGS['immich-delete-duplicates-albums']:
        EXECUTION_MODE = 'immich-delete-duplicates-albums'
        mode_immich_delete_duplicates_albums()
    elif ARGS['immich-upload-folder'] != "":
        EXECUTION_MODE = 'immich-upload-folder'
        mode_immich_upload_folder()
    elif ARGS['immich-upload-albums'] != "":
        EXECUTION_MODE = 'immich-upload-albums'
    elif ARGS['immich-download-albums'] != "":
        EXECUTION_MODE = 'immich-download-albums'
        mode_immich_download_albums()
    elif ARGS['immich-download-ALL'] != "":
        EXECUTION_MODE = 'immich-download-ALL'
        mode_immich_download_ALL()

    # Other Stand-alone Extra Modes:
    elif ARGS['fix-symlinks-broken'] != "":
        EXECUTION_MODE = 'fix-symlinks'
        mode_fix_symlinkgs()
    elif ARGS['find-duplicates'] != ['list', '']:
        EXECUTION_MODE = 'find_duplicates'
        mode_find_duplicates()
    elif ARGS['process-duplicates'] != "":
        EXECUTION_MODE = 'process-duplicates'
        mode_process_duplicates()
    elif ARGS['folders-rename-content-based'] != "":
        EXECUTION_MODE = 'folders-rename-content-based'
        mode_folders_rename_content_based()

    else:
        EXECUTION_MODE = ''  # Opción por defecto si no se cumple ninguna condición
        LOGGER.error("ERROR: Unable to detect any valid execution mode.")
        LOGGER.error("ERROR: Please, read the --help to know more about how to invoke the Script.")
        LOGGER.error("")
        PARSER.print_help()
        sys.exit(1)

# -------------------------------------------------------------
# Configure the LOGGER
# -------------------------------------------------------------
def log_init():
    global LOGGER
    global TIMESTAMP
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    log_filename=f"{script_name}_{TIMESTAMP}"
    log_folder="Logs"
    LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename)

# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
def main():
    global args
    global LOGGER
    global START_TIME
    global TIMESTAMP
    global OUTPUT_FOLDER
    global LOG_FOLDER_FILENAME
    global DEFAULT_DUPLICATES_ACTION
    global DEPRIORITIZE_FOLDERS_PATTERNS
    global ARGS

    # Limpiar la pantalla y parseamos argumentos de entrada
    os.system('cls' if os.name == 'nt' else 'clear')

    DEFAULT_DUPLICATES_ACTION = False

    ARGS = parse_arguments()

    # List of Folder to Desprioritize when looking for duplicates.
    DEPRIORITIZE_FOLDERS_PATTERNS = ['*Photos from [1-2][0-9]{3}$', '*ALL_PHOTOS', '*Others', '*Variad[oa]*', '*Vari[oa]*', '*Miscellaneous*', '*M[oó]vil*', r'\bfotos\b\s+(\w+)\s*$', r'fotos de \w y \w\s*$', r'fotos de \w\s*$', '*Fotos_de*', '*Fotos_con', '*Fotos de*', '*Fotos con*']

    # Create timestamp, start_time and define OUTPUT_FOLDER
    START_TIME = datetime.now()
    OUTPUT_FOLDER = f"{ARGS['google-input-takeout-folder']}_{ARGS['google-output-folder-suffix']}_{TIMESTAMP}"

    # # Set a global variable for logger and Set up logger based on the no-log-file argument
    # TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    # log_filename=f"{SCRIPT_NAME}_{TIMESTAMP}"
    # log_folder="Logs"
    # LOG_FOLDER_FILENAME = os.path.join(log_folder, log_filename + '.log')
    # LOGGER = log_setup(log_folder=log_folder, log_filename=log_filename, skip_logfile=ARGS['no-log-file'], plain_log=False)

    # Initialize the logger.
    log_init()

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
    detect_and_run_execution_mode()

def mode_AUTOMATED_MIGRATION():
    global OUTPUT_FOLDER
    LOGGER.info(f"INFO: -AUTO, --AUTOMATED-MIGRATION Mode detected")
    LOGGER.info(HELP_MODE_ALL_IN_ONE.replace('<INPUT_FOLDER>', f"'{ARGS['AUTOMATED-MIGRATION']}'"))
    if not Utils.confirm_continue():
        LOGGER.info(f"INFO: Exiting program.")
        sys.exit(0)

    config = read_synology_config(show_info=False)
    if not config['SYNOLOGY_ROOT_PHOTOS_PATH']:
        LOGGER.warning(f"WARNING: Caanot find 'SYNOLOGY_ROOT_PHOTOS_PATH' info in 'nas.config' file. Albums will not be created into Synology Photos database")
    else:
        OUTPUT_FOLDER = os.path.join(config['SYNOLOGY_ROOT_PHOTOS_PATH'], f'Google Photos_{TIMESTAMP}')

    res, _ = login_synology()
    if res==-1:
        LOGGER.warning(f"WARNING: Cannot connect to Synology Photos. Albums will not be created into Synology Photos database")

    # Configure default arguments for mode_google_takeout() execution and RUN it
    input_folder = ARGS['AUTOMATED-MIGRATION']
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        ARGS['google-input-zip-folder'] = input_folder
        ARGS['google-input-takeout-folder'] = os.path.join(os.path.dirname(input_folder),f'Unzipped_Takeout_{TIMESTAMP}')
        ARGS['google-move-takeout-folder'] = True
    else:
        ARGS['google-input-takeout-folder'] = input_folder
    ARGS['google-remove-duplicates-files'] = True
    mode_google_takeout(user_confirmation=False)

    # Configure the Create_Synology_Albums and run create_synology_albums()
    albums_folder = os.path.join(OUTPUT_FOLDER, f'Albums')
    ARGS['synology-upload-albums'] = albums_folder
    LOGGER.info("")
    mode_synology_upload_albums(user_confirmation=False)

    # Finally Execute mode_delete_duplicates_albums & mode_delete_empty_albums
    mode_synology_delete_duplicates_albums(user_confirmation=False)
    mode_synology_delete_empty_albums(user_confirmation=False)



def mode_google_takeout(user_confirmation=True):
    # Configure default arguments for mode_google_takeout() execution
    input_folder = ARGS['google-input-takeout-folder']
    need_unzip = Utils.contains_zip_files(input_folder)
    if need_unzip:
        ARGS['google-input-zip-folder'] = input_folder
        ARGS['google-input-takeout-folder'] = os.path.join(os.path.dirname(input_folder),f'Unzipped_Takeout_{TIMESTAMP}')
        LOGGER.info(f"INFO: ZIP files have been detected in {input_folder}'. Files will be unziped first...")
        LOGGER.info("")
    else:
        ARGS['google-input-takeout-folder'] = input_folder

    # Mensajes informativos
    LOGGER.info(f"Settings for Google Takeout Photos Module:")
    LOGGER.info(f"------------------------------------------")
    LOGGER.info(f"INFO: Using Suffix                             : '{ARGS['google-output-folder-suffix']}'")
    LOGGER.info(f"INFO: Albums Folder Structure                  : '{ARGS['google-albums-folders-structure']}'")
    LOGGER.info(f"INFO: No Albums Folder Structure               : '{ARGS['google-no-albums-folder-structure']}'")
    LOGGER.info(f"INFO: Creates symbolic links for Albums        : '{ARGS['google-create-symbolic-albums']}'")
    LOGGER.info(f"INFO: Ignore Check Google Takeout Structure    : '{ARGS['google-ignore-check-structure']}'")
    LOGGER.info(f"INFO: Move Original Assets to Output Folder    : '{ARGS['google-move-takeout-folder']}'")
    LOGGER.info(f"INFO: Remove Duplicates files in Output folder : '{ARGS['google-remove-duplicates-files']}'")
    LOGGER.info(f"INFO: Skip Extra Assets (-edited,-effects...)  : '{ARGS['google-skip-extras-files']}'")
    LOGGER.info(f"INFO: Skip Moving Albums to 'Albums' folder    : '{ARGS['google-skip-move-albums']}'")
    LOGGER.info(f"INFO: Skip GPTH Tool                           : '{ARGS['google-skip-gpth-tool']}'")

    LOGGER.info("")
    LOGGER.info(f"Folders for Google Takeout Photos Module:")
    LOGGER.info(f"------------------------------------------")
    if not ARGS['no-log-file']:
        LOGGER.info(f"INFO: Execution Log file                       : '{LOG_FOLDER_FILENAME}'")
    if ARGS['google-input-zip-folder']!="":
        LOGGER.info(f"INFO: Input Takeout folder (zipped detected)   : '{ARGS['google-input-zip-folder']}'")
        LOGGER.info(f"INFO: Input Takeout will be unziped to folder  : '{ARGS['google-input-takeout-folder']}'")
    else:
        LOGGER.info(f"INFO: Input Takeout folder                     : '{ARGS['google-input-takeout-folder']}'")
    LOGGER.info(f"INFO: OUTPUT folder                            : '{OUTPUT_FOLDER}'")


    LOGGER.info(f"")
    if user_confirmation:
        LOGGER.info(HELP_MODE_GOOGLE_TAKEOUT)
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        if ARGS['google-input-zip-folder']=="":
            LOGGER.warning(f"WARNING: No argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' detected. Skipping Unzipping files...")
        if ARGS['google-albums-folders-structure'].lower()!='flatten':
            LOGGER.warning(f"WARNING: Flag detected '-gafs, --google-albums-folders-structure'. Folder structure '{ARGS['google-albums-folders-structure']}' will be applied on each Album folder...")
        if ARGS['google-no-albums-folder-structure'].lower()!='year/month':
            LOGGER.warning(f"WARNING: Flag detected '-gnaf, --google-no-albums-folder-structure'. Folder structure '{ARGS['google-no-albums-folder-structure']}' will be applied on 'Others' folder (Photos without Albums)...")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"WARNING: Flag detected '-gsgt, --google-skip-gpth-tool'. Skipping Processing photos with GPTH Tool...")
        if ARGS['google-skip-extras-files']:
            LOGGER.warning(f"WARNING: Flag detected '-gsef, --google-skip-extras-files'. Skipping Processing extra Photos from Google Photos such as -effects, -editted, etc...")
        if ARGS['google-skip-move-albums']:
            LOGGER.warning(f"WARNING: Flag detected '-gsma, --google-skip-move-albums'. Skipping Moving Albums to Albums folder...")
        if ARGS['google-create-symbolic-albums']:
            LOGGER.warning(f"WARNING: Flag detected '-gcsa, --google-create-symbolic-albums'. Albums files will be symlinked to the original files instead of duplicate them.")
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning(f"WARNING: Flag detected '-gics, --google-ignore-check-structure'. All files in <TAKEOUT_FOLDER> will be processed ignoring Google Takeout Structure...")
        if ARGS['google-move-takeout-folder']:
            LOGGER.warning(f"WARNING: Flag detected '-gmtf, --google-move-takeout-folder'. Photos/Videos in <TAKEOUT_FOLDER> will be moved (instead of copied) to <OUTPUT_FOLDER>...")
        if ARGS['google-remove-duplicates-files']:
            LOGGER.warning(f"WARNING: Flag detected '-grdf, --google-remove-duplicates-files'. All duplicates files within OUTPUT_FOLDER will be removed after fixing them...")
        if ARGS['no-log-file']:
            LOGGER.warning(f"WARNING: Flag detected '-nlog, --no-log-file'. Skipping saving output into log file...")

    # STEP 1: Unzip files
    STEP=1
    LOGGER.info("")
    LOGGER.info("==============================")
    LOGGER.info(f"{STEP}. UNPACKING TAKEOUT FOLDER...")
    LOGGER.info("==============================")
    LOGGER.info("")
    if not ARGS['google-input-zip-folder']=="":
        step_start_time = datetime.now()
        Utils.unpack_zips(ARGS['google-input-zip-folder'], ARGS['google-input-takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Unzipping skipped (no argument '-gizf or --google-input-zip-folder <ZIP_FOLDER>' given or Running Mode All-in-One with input folder directly unzipped).")

    if not os.path.isdir(ARGS['google-input-takeout-folder']):
        LOGGER.error(f"ERROR: Cannot Find INPUT_FOLDER: '{ARGS['google-input-takeout-folder']}'. Exiting...")
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
    Utils.delete_subfolders(ARGS['google-input-takeout-folder'], "@eaDir")
    # Look for .MP4 files extracted from Live pictures and create a .json for them in order to fix their date and time
    LOGGER.info("")
    LOGGER.info("INFO: Looking for .MP4 files from live pictures and asociate date and time with live picture file...")
    Utils.fix_mp4_files(ARGS['google-input-takeout-folder'])
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
    if not ARGS['google-skip-gpth-tool']:
        if ARGS['google-ignore-check-structure']:
            LOGGER.warning("WARNING: Ignore Google Takeout Structure detected ('-it, --google-ignore-check-structure' flag detected).")
        step_start_time = datetime.now()
        Fixers.fix_metadata_with_gpth_tool(
            input_folder=ARGS['google-input-takeout-folder'],
            output_folder=OUTPUT_FOLDER,
            symbolic_albums=ARGS['google-create-symbolic-albums'],
            skip_extras=ARGS['google-skip-extras-files'],
            move_takeout_folder=ARGS['google-move-takeout-folder'],
            ignore_takeout_structure=ARGS['google-ignore-check-structure']
        )
        if ARGS['google-move-takeout-folder']:
            Utils.force_remove_directory(ARGS['google-input-takeout-folder'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    if ARGS['google-skip-gpth-tool'] or ARGS['google-ignore-check-structure']:
        LOGGER.info("")
        LOGGER.info("============================================")
        LOGGER.info(f"{STEP}b. COPYING/MOVING FILES TO OUTPUT FOLDER...")
        LOGGER.info("============================================")
        LOGGER.info("")
        if ARGS['google-skip-gpth-tool']:
            LOGGER.warning(f"WARNING: Metadata fixing with GPTH tool skipped ('-sg, --google-skip-gpth-tool' flag detected). Step {STEP}b is needed to copy files manually to output folder.")
        elif ARGS['google-ignore-check-structure']:
            LOGGER.warninf(f"WARNING: Flag to Ignore Google Takeout Structure have been detected ('-it, --google-ignore-check-structure'). Step {STEP}b is needed to copy/move files manually to output folder.")
        if ARGS['google-move-takeout-folder']:
            LOGGER.info("INFO: Moving files from Takeout folder to Output folder manually...")
        else:
            LOGGER.info("INFO: Copying files from Takeout folder to Output folder manually...")
        step_start_time = datetime.now()
        Utils.copy_move_folder (ARGS['google-input-takeout-folder'], OUTPUT_FOLDER, ignore_patterns=['*.json', '*.j'], move=ARGS['google-move-takeout-folder'])
        if ARGS['google-move-takeout-folder']:
            Utils.force_remove_directory(ARGS['takeout-folder'])
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
    if ARGS['google-albums-folders-structure'].lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{ARGS['google-albums-folders-structure'].lower()}' for each Album folder...")
        basedir=OUTPUT_FOLDER
        type=ARGS['google-albums-folders-structure']
        exclude_subfolders=['Others']
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # For No Albums:
    if ARGS['google-no-albums-folder-structure'].lower()!='flatten':
        LOGGER.info("")
        LOGGER.info(f"INFO: Creating Folder structure '{ARGS['google-no-albums-folder-structure'].lower()}' for 'Others' folder...")
        basedir=os.path.join(OUTPUT_FOLDER, 'Others')
        type=ARGS['google-no-albums-folder-structure']
        exclude_subfolders=[]
        Utils.organize_files_by_date(input_folder=basedir, type=type, exclude_subfolders=exclude_subfolders)
    # If no fiolder structure is detected:
    if ARGS['google-albums-folders-structure'].lower()=='flatten' and ARGS['google-no-albums-folder-structure'].lower()=='flatten' :
        LOGGER.info("")
        LOGGER.warning("WARNING: No argument '-as, --google-albums-folders-structure' and '-ns, --google-no-albums-folder-structure' detected. All photos and videos will be flattened within their folders without any date organization.")
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
    if not ARGS['google-skip-move-albums']:
        step_start_time = datetime.now()
        Utils.move_albums(OUTPUT_FOLDER, exclude_subfolder=['Others', '@eaDir'])
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Moving albums to 'Albums' folder skipped ('-sm, --google-skip-move-albums' flag detected).")

    # STEP 7: Fix Broken Symbolic Links after moving
    STEP+=1
    symlink_fixed = 0
    symlink_not_fixed = 0
    LOGGER.info("")
    LOGGER.info("===============================================")
    LOGGER.info(f"{STEP}. FIXING BROKEN SYMBOLIC LINKS AFTER MOVING...")
    LOGGER.info("===============================================")
    LOGGER.info("")
    if ARGS['google-create-symbolic-albums']:
        LOGGER.info("INFO: Fixing broken symbolic links. This step is needed after moving any Folder structure...")
        step_start_time = datetime.now()
        symlink_fixed, symlink_not_fixed = Utils.fix_symlinks_broken(OUTPUT_FOLDER)
        step_end_time = datetime.now()
        formatted_duration = str(timedelta(seconds=(step_end_time-step_start_time).seconds))
        LOGGER.info(f"INFO: Step {STEP} completed in {formatted_duration}.")
    else:
        LOGGER.warning("WARNING: Fixing broken symbolic links skipped ('-sa, --google-create-symbolic-albums' flag not detected, so this step is not needed.)")

    # STEP 8: Remove Duplicates in OUTPUT_FOLDER after Fixing
    STEP+=1
    duplicates_found = 0
    if ARGS['google-remove-duplicates-files']:
        LOGGER.info("")
        LOGGER.info("==========================================")
        LOGGER.info(f"{STEP}. REMOVING DUPLICATES IN OUTPUT_FOLDER...")
        LOGGER.info("==========================================")
        LOGGER.info("")
        LOGGER.info("INFO: Removing duplicates from OUTPUT_FOLDER (Files within any Album will have more priority than files within 'Photos from *' or 'Others' folders)...")
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
    LOGGER.info(f"Total files in Takeout folder        : {Utils.count_files_in_folder(ARGS['google-input-takeout-folder'])}")
    LOGGER.info(f"Total final files in Output folder   : {Utils.count_files_in_folder(OUTPUT_FOLDER)}")
    albums_found = 0
    if not ARGS['google-skip-move-albums']:
        album_folder = os.path.join(OUTPUT_FOLDER, 'Albums')
        if os.path.isdir(album_folder):
            albums_found = len(os.listdir(album_folder))
    else:
        if os.path.isdir(OUTPUT_FOLDER):
            albums_found = len(os.listdir(OUTPUT_FOLDER))-1
    LOGGER.info(f"Total Albums folders found           : {albums_found}")
    if ARGS['google-create-symbolic-albums']:
        LOGGER.info(f"Total Symlinks Fixed                 : {symlink_fixed}")
        LOGGER.info(f"Total Symlinks Not Fixed             : {symlink_not_fixed}")
    if ARGS['google-remove-duplicates-files']:
        LOGGER.info(f"Total Duplicates Removed             : {duplicates_found}")
    LOGGER.info("")
    LOGGER.info(f"Total time elapsed                   : {formatted_duration}")
    LOGGER.info("===============================================")
    LOGGER.info("")

def mode_fix_symlinkgs(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(HELP_MODE_FIX_SYMLINKS.replace('<FOLDER_TO_FIX>', f"'{ARGS['fix-symlinks-broken']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Fixing broken symbolic links Mode detected. Only this module will be run!!!")
    LOGGER.info(f"INFO: Fixing broken symbolic links in folder '{ARGS['fix-symlinks-broken']}'...")
    symlinks_fixed, symlinks_not_fixed = Utils.fix_symlinks_broken(ARGS['fix-symlinks-broken'])
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
    LOGGER.info(f"INFO: Duplicates Action             : {ARGS['duplicates-action']}")
    LOGGER.info(f"INFO: Find Duplicates in Folders    : {ARGS['duplicates-folders']}")
    LOGGER.info("")
    if interactive_mode:
        LOGGER.info(HELP_MODE_FIND_DUPLICATES.replace('<DUPLICATES_FOLDER>', f"'{ARGS['duplicates-folders']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Find Duplicates Mode detected. Only this module will be run!!!")
        if DEFAULT_DUPLICATES_ACTION:
            LOGGER.warning(f"WARNING: Detected Flag '-fd, --find-duplicates' but no valid <DUPLICATED_ACTION> have been detected. Using 'list' as default <DUPLICATED_ACTION>")
            LOGGER.warning("")
    duplicates_files_found = find_duplicates(duplicates_action=ARGS['duplicates-action'], duplicates_folders=ARGS['duplicates-folders'], deprioritize_folders_patterns=DEPRIORITIZE_FOLDERS_PATTERNS)
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
        LOGGER.info(f"INFO: Flag detected '-pd, --process-duplicates'. The Script will process the '{ARGS['process-duplicates']}' file and do the specified action given on Action Column. ")
    LOGGER.info(f"INFO: Processing Duplicates Files based on Actions given in {os.path.basename(ARGS['process-duplicates'])} file...")
    removed_duplicates, restored_duplicates, replaced_duplicates = process_duplicates_actions(ARGS['process-duplicates'])
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


def mode_folders_rename_content_based(user_confirmation=True):
    LOGGER.info(SCRIPT_DESCRIPTION)
    LOGGER.info("")
    LOGGER.info("===================")
    LOGGER.info("STARTING PROCESS...")
    LOGGER.info("===================")
    LOGGER.info("")
    if user_confirmation:
        LOGGER.info(HELP_MODE_RENAME_ALBUMS_FOLDERS.replace('<ALBUMS_FOLDER>', f"'{ARGS['folders-rename-content-based']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Rename Albums Mode detected. Only this module will be run!!!")
        LOGGER.info(f"INFO: Flag detected '-ra, --folders-rename-content-based'. The Script will look for any Subfolder in '{ARGS['folders-rename-content-based']}' and will rename the folder name in order to unificate all the Albums names.")
    renamed_album_folders, duplicates_album_folders, duplicates_albums_fully_merged, duplicates_albums_not_fully_merged = Utils.rename_album_folders(ARGS['folders-rename-content-based'])
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

def mode_synology_upload_folder(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-suf, --synology-upload-folder'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_UPLOAD_FOLDER.replace('<FOLDER>', f"'{ARGS['synology-upload-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {ARGS['synology-upload-folder']}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = synology_upload_folder(ARGS['synology-upload-folder'])
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
        LOGGER.info(HELP_MODE_SYNOLOGY_UPLOAD_ALBUMS.replace('<ALBUMS_FOLDER>', f"'{ARGS['synology-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['synology-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = synology_upload_albums(ARGS['synology-upload-albums'])
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
        LOGGER.info(HELP_MODE_SYNOLOGY_DOWNLOAD_ALBUMS.replace('<ALBUMS_NAME>', f"'{ARGS['synology-download-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Albums to extract       : {ARGS['synology-download-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, photos_downloaded = synology_download_albums(ARGS['synology-download-albums'])
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

def mode_synology_download_ALL(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iDA, --immich-download-all'.")
        LOGGER.info(HELP_MODE_SYNOLOGY_DOWNLOAD_ALL.replace('<OUTPUT_FOLDER>', f"{ARGS['synology-download-ALL']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Synology Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = synology_download_ALL(ARGS['synology-download-ALL'])
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


###############################
# EXTRA MODES: IMMICH PHOTOS: #
###############################
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

def mode_immich_upload_folder(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iua, --immich-upload-albums'.")
        LOGGER.info(HELP_MODE_IMMICH_UPLOAD_FOLDER.replace('<FOLDER>', f"'{ARGS['immich-upload-folder']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Folder' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Upload Photos/Videos in Folder    : {ARGS['immich-upload-folder']}")
    LOGGER.info("")
    # Call the Funxtion
    photos_added = immich_upload_folder(ARGS['immich-upload-folder'])
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
        LOGGER.info(HELP_MODE_IMMICH_UPLOAD_ALBUMS.replace('<ALBUMS_FOLDER>', f"'{ARGS['immich-upload-albums']}'"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Upload Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_crated, albums_skipped, photos_added = immich_upload_albums(ARGS['immich-upload-albums'])
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
        LOGGER.info(HELP_MODE_IMMICH_DOWNLOAD_ALBUMS.replace('<ALBUMS_NAME>', f"{ARGS['immich-download-albums']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download Albums' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_albums(ARGS['immich-download-albums'])
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

def mode_immich_download_ALL(user_confirmation=True):
    if user_confirmation:
        LOGGER.info(f"INFO: Flag detected '-iDA, --immich-download-all'.")
        LOGGER.info(HELP_MODE_IMMICH_DOWNLOAD_ALL.replace('<OUTPUT_FOLDER>', f"{ARGS['immich-download-ALL']}"))
        if not Utils.confirm_continue():
            LOGGER.info(f"INFO: Exiting program.")
            sys.exit(0)
        LOGGER.info(f"INFO: Immich Photos: 'Download ALL' Mode detected. Only this module will be run!!!")
    LOGGER.info("")
    # LOGGER.info(f"INFO: Find Albums in Folder    : {ARGS['immich-upload-albums']}")
    LOGGER.info("")
    # Call the Funxtion
    albums_downloaded, assets_downloaded = immich_download_ALL(ARGS['immich-download-ALL'])
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


if __name__ == "__main__":
    # Verificar si el script se ejecutó sin argumentos
    # if len(sys.argv) == 1:
    #     # Agregar argumento predeterminado
    #     sys.argv.append("-z")
    #     sys.argv.append("Zip_folder")
    #     print(f"INFO: No argument detected. Using default value '{sys.argv[2]}' for <ZIP_FOLDER>'.")
    main()
