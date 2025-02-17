import logging

from GlobalVariables import SCRIPT_DESCRIPTION, SCRIPT_NAME, SCRIPT_VERSION, SCRIPT_DATE

from CustomHelpFormatter import CustomHelpFormatter
from CustomPager import PagedParser
import argparse
import os

choices_for_message_levels          = ['debug', 'info', 'warning', 'error', 'critical']
choices_for_folder_structure        = ['flatten', 'year', 'year/month', 'year-month']
choices_for_remove_duplicates       = ['list', 'move', 'remove']
choices_for_AUTOMATED_MIGRATION_SRC = ['google-photos', 'synology-photos', 'immich-photos']
choices_for_AUTOMATED_MIGRATION_TGT = ['synology-photos', 'immich-photos']

PARSER = None

def parse_arguments():
    # # Regular Parser without Pagination
    # PARSER = argparse.ArgumentParser(
    #         description=SCRIPT_DESCRIPTION,
    #         formatter_class=CustomHelpFormatter,  # Aplica el formatter
    # )

    # Parser with Pagination:
    PARSER = PagedParser(
        description=SCRIPT_DESCRIPTION,
        formatter_class=CustomHelpFormatter,  # Aplica el formatter
    )

    # Acción personalizada para --version
    class VersionAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print(f"\n{SCRIPT_NAME} {SCRIPT_VERSION} {SCRIPT_DATE} by Jaime Tur (@jaimetur)\n")
            parser.exit()

    PARSER.add_argument("-v", "--version", action=VersionAction, nargs=0, help="Show the script name, version, and date, then exit.")
    PARSER.add_argument("-i", "--input-folder", metavar="<INPUT_FOLDER>", default="", help="Specify the input folder that you want to process.")
    PARSER.add_argument("-o", "--output-folder", metavar="<OUTPUT_FOLDER>", default="", help="Specify the output folder to save the result of the processing action.")
    PARSER.add_argument("-AlbFld", "--albums-folders", metavar="<ALBUMS_FOLDER>", default="", nargs="*", help="If used together with '-iuAll, --immich-upload-all' or '-iuAll, --immich-upload-all', it will create an Album per each subfolder found in <ALBUMS_FOLDER>.")
    PARSER.add_argument("-rAlbAss", "--remove-albums-assets", action="store_true", default=False, help="If used together with '-srAllAlb, --synology-remove-all-albums' or '-irAllAlb, --immich-remove-all-albums', it will also delete the assets (photos/videos) inside each album.")
    # PARSER.add_argument("-woAlb", "--without-albums", action="store_true", default=False, help="If used together with '-iuAll, --immich-upload-all' or '-iuAll, --immich-upload-all', it will avoid create an Album per each subfolder found in <INPUT_FOLDER>.")
    PARSER.add_argument("-loglevel", "--log-level", metavar=f"{choices_for_message_levels}", choices=choices_for_message_levels, default="info", help="Specify the log level for logging and screen messages.")
    PARSER.add_argument("-nolog", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")

    PARSER.add_argument("-AUTO", "--AUTOMATED-MIGRATION", metavar=("<SOURCE>", "<TARGET>"), nargs=2, default="",
                        help="This process will do an AUTOMATED-MIGRATION process to Download all your Assets (including Albums) from the <SOURCE> Cloud Service and Upload them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service."
                           "\n"
                           "\npossible values for:"
                           "\n    <SOURCE> : ['google-photos', 'synology-photos', 'immich-photos']"
                           "\n    <TARGET> : ['synology-photos', 'immich-photos']"
                        )

    # EXTRA MODES FOR GOOGLE PHOTOS:
    # ------------------------------
    # PARSER.add_argument("-gizf", "--google-input-zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
    PARSER.add_argument("-gitf", "--google-input-takeout-folder", metavar="<TAKEOUT_FOLDER>", default="Takeout", help="Specify the Takeout folder to process. If any Zip file is found inside it, the Zip will be extracted to the folder 'Unzipped_Takeout_TIMESTAMP', and will use the that folder as input <TAKEOUT_FOLDER>. Default: 'Takeout'.")
    PARSER.add_argument("-gofs", "--google-output-folder-suffix", metavar="<SUFFIX>", default="fixed", help="Specify the suffix for the output folder. Default: 'fixed'")
    PARSER.add_argument("-gafs", "--google-albums-folders-structure", metavar=f"{choices_for_folder_structure}", default="flatten", help="Specify the type of folder structure for each Album folder (Default: 'flatten')."
                        , type=lambda s: s.lower()  # Convert input to lowercase
                        , choices=choices_for_folder_structure  # Valid choices
                        )
    PARSER.add_argument("-gnas", "--google-no-albums-folder-structure", metavar=f"{choices_for_folder_structure}", default="year/month", help="Specify the type of folder structure for 'No-Albums' folder (Default: 'year/month')."
                        , type=lambda s: s.lower()  # Convert input to lowercase
                        , choices=choices_for_folder_structure  # Valid choices
                        )
    PARSER.add_argument("-gcsa", "--google-create-symbolic-albums", action="store_true", help="Creates symbolic links for Albums instead of duplicate the files of each Album. (Useful to save disk space but may not be portable to other systems).")
    PARSER.add_argument("-gics", "--google-ignore-check-structure", action="store_true", help="Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc..), and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamp from them.")
    PARSER.add_argument("-gmtf", "--google-move-takeout-folder", action="store_true", help=f"Move original assets to <OUTPUT_TAKEOUT_FOLDER>. \nCAUTION: Useful to avoid disk space duplication and improve execution speed, but you will lost your original unzipped files!!!.\nUse only if you keep the original zipped files or you have disk space limitations and you don't mind to lost your original unzipped files.")
    PARSER.add_argument("-grdf", "--google-remove-duplicates-files", action="store_true", help="Remove Duplicates files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.")
    PARSER.add_argument("-gsef", "--google-skip-extras-files", action="store_true", help="Skip processing extra photos such as  -edited, -effects photos.")
    PARSER.add_argument("-gsma", "--google-skip-move-albums", action="store_true", help="Skip moving albums to 'Albums' folder.")
    PARSER.add_argument("-gsgt", "--google-skip-gpth-tool", action="store_true", help="Skip processing files with GPTH Tool. \nCAUTION: This option is NOT RECOMMENDED because this is the Core of the Google Photos Takeout Process. Use this flag only for testing purposses.")

    # EXTRA MODES FOR SYNOLOGY PHOTOS:
    # --------------------------------
    PARSER.add_argument("-suAlb", "--synology-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Synology Photos.")
    PARSER.add_argument("-suAll", "--synology-upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="The script will look for all Assets within <INPUT_FOLDER> and will upload them into Synology Photos."
                           "\n- The script will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside each subfolder will be associated to a new Album in Synology Photos with the same name as the subfolder."
                           "\n- If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will create Albums also for each subfolder found in <ALBUMS_FOLDER>."
                        )
    PARSER.add_argument("-sdAlb", "--synology-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Script will connect to Synology Photos and download the Album whose name is '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this mode)."
                           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                           "\n- To download all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --synology-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
                           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums 'album1', 'album2', 'album3'."
                        )
    PARSER.add_argument("-sdAll", "--synology-download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Script will connect to Synology Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
                           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
                           "\n- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside."
                        )
    PARSER.add_argument("-srEmpAlb", "--synology-remove-empty-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is empty, will remove it from Synology Photos database.")
    PARSER.add_argument("-srDupAlb", "--synology-remove-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Synology Photos database and if any Album is duplicated, will remove it from Synology Photos database.")
    PARSER.add_argument("-srAll", "--synology-remove-all-assets", action="store_true", default="", help="CAUTION!!! The script will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Synology database.")
    PARSER.add_argument("-srAllAlb", "--synology-remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! The script will delete ALL your Albums from Synology database."
                           "\nOptionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )

    # EXTRA MODES FOR IMMICH PHOTOS:
    # -------------------------------
    PARSER.add_argument("-iuAlb", "--immich-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The script will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Immich Photos.")
    PARSER.add_argument("-iuAll", "--immich-upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="The script will look for all Assets within <INPUT_FOLDER> and will upload them into Immich Photos."
                           "\n- The script will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside each subfolder will be associated to a new Album in Immich Photos with the same name as the subfolder."
                           "\n- If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will create Albums also for each subfolder found in <ALBUMS_FOLDER>."
                        )
    PARSER.add_argument("-idAlb", "--immich-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Script will connect to Immich Photos and download the Album whose name is '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this mode)."
                           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                           "\n- To download all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --immich-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
                           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums 'album1', 'album2', 'album3'."
                        )
    PARSER.add_argument("-idAll", "--immich-download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Script will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
                           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
                           "\n- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside."
                        )
    PARSER.add_argument("-irEmpAlb", "--immich-remove-empty-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is empty, will remove it from Immich Photos database.")
    PARSER.add_argument("-irDupAlb", "--immich-remove-duplicates-albums", action="store_true", default="", help="The script will look for all Albums in Immich Photos database and if any Album is duplicated, will remove it from Immich Photos database.")
    PARSER.add_argument("-irAll", "--immich-remove-all-assets", action="store_true", default="", help="CAUTION!!! The script will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Immich database.")
    PARSER.add_argument("-irAllAlb", "--immich-remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! The script will delete ALL your Albums from Immich database."
                           "\nOptionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )
    PARSER.add_argument("-irOrphan", "--immich-remove-orphan-assets", action="store_true", default="", help="The script will look for all Orphan Assets in Immich Database and will delete them. IMPORTANT: This feature requires a valid ADMIN_API_KEY configured in Config.ini.")



    # OTHERS STAND-ALONE EXTRA MODES:
    # -------------------------------
    PARSER.add_argument("-findDup", "--find-duplicates", metavar=f"<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]", nargs="+", default=["list", ""],
                        help="Find duplicates in specified folders."
                           "\n<ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list' "
                           "\n<DUPLICATES_FOLDER> are one or more folders (string or list), where the script will look for duplicates files. The order of this list is important to determine the principal file of a duplicates set. First folder will have higher priority."
                        )
    PARSER.add_argument("-procDup", "--process-duplicates", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Specify the Duplicates CSV file revised with specifics Actions in Action column, and the script will execute that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.")
    PARSER.add_argument("-fixSym", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="The script will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_TAKEOUT_FOLDER and some Albums seems to be empty.")
    PARSER.add_argument("-renFldcb", "--rename-folders-content-based", metavar="<ALBUMS_FOLDER>", default="", help="Usefull to rename and homogenize all Albums folders found in <ALBUMS_FOLDER> based on the date content found.")

    # Procesar la acción y las carpetas

    # Obtain args from PARSER and create global variable ARGS to easier manipulation of argument variables using the same string as in the argument (this facilitates futures refactors on arguments names)
    args = PARSER.parse_args()
    ARGS = create_global_variable_from_args(args)
    return ARGS


def checkArgs(ARGS):
    global DEFAULT_DUPLICATES_ACTION, LOG_LEVEL

    # Remove '_' at the begining of the string in case it has it.
    ARGS['google-output-folder-suffix'] = ARGS['google-output-folder-suffix'].lstrip('_')

    # Remove last / for all folders expected as arguments:
    ARGS['input-folder']                    = ARGS['input-folder'].rstrip('/\\')
    ARGS['output-folder']                   = ARGS['output-folder'].rstrip('/\\')
    ARGS['google-input-takeout-folder']     = ARGS['google-input-takeout-folder'].rstrip('/\\')
    ARGS['synology-upload-albums']          = ARGS['synology-upload-albums'].rstrip('/\\')
    ARGS['synology-upload-all']             = ARGS['synology-upload-all'].rstrip('/\\')
    ARGS['synology-download-all']           = ARGS['synology-download-all'].rstrip('/\\')
    ARGS['immich-upload-albums']            = ARGS['immich-upload-albums'].rstrip('/\\')
    ARGS['immich-upload-all']               = ARGS['immich-upload-all'].rstrip('/\\')
    ARGS['immich-download-all']             = ARGS['immich-download-all'].rstrip('/\\')
    ARGS['fix-symlinks-broken']             = ARGS['fix-symlinks-broken'].rstrip('/\\')
    ARGS['rename-folders-content-based']    = ARGS['rename-folders-content-based'].rstrip('/\\')

    # Parse AUTOMATED-MIGRATION Arguments
    ARGS['google-input-zip-folder'] = None
    ARGS['SOURCE-TYPE-TAKEOUT-FOLDER'] = None
    if len(ARGS['AUTOMATED-MIGRATION']) >0:
        source = ARGS['AUTOMATED-MIGRATION'][0]
        target = ARGS['AUTOMATED-MIGRATION'][1]
        # If source is 'google-photos' we need to check if an valid <INPUT_FOLDER> have been given with argument -i <INPUT_FOLDER>
        if source.lower() == 'google-photos':
            input_folder = ARGS['input-folder']
            if not os.path.isdir(input_folder):
                print(f"ERROR   : 'google-photos' detected as Source for the Automated Migration process, but not valid <INPUT_FOLDER> have been providen. ")
                print(f"Please use -i <INPUT_FOLDER> to specify where your Google Photos Takeout is located.")
        # If source is not in the list of valid sources choices, then if it is a valid Input Takeout Folder from Google Photos
        elif source.lower() not in choices_for_AUTOMATED_MIGRATION_SRC:
            print(f"WARNING : Source value '{source}' is not in the list of valid values: {choices_for_AUTOMATED_MIGRATION_SRC}...")
            print(f"WARNING : Assuming that it is the input takeout folder for 'google-photos'")
            if not os.path.isdir(source):
                print(f"❌ ERROR   : Source Path '{source}' is not a valid Input Takeout Folder for 'google-photos' migration. Exiting...")
                exit(1)
            ARGS['SOURCE-TYPE-TAKEOUT-FOLDER'] = True
        # If the target is not in the list of valid targets choices, exit.
        if target.lower() not in choices_for_AUTOMATED_MIGRATION_TGT:
            print(f"❌ ERROR   : Target value '{target}' is not valid. Must be one of {choices_for_AUTOMATED_MIGRATION_TGT}")
            exit(1)

    # Parse log-levels
    if ARGS['log-level'].lower() == 'debug':
        LOG_LEVEL = logging.DEBUG
    elif ARGS['log-level'].lower() == 'info':
        LOG_LEVEL = logging.INFO
    elif ARGS['log-level'].lower() == 'warning':
        LOG_LEVEL = logging.WARNING
    elif ARGS['log-level'].lower() == 'error':
        LOG_LEVEL = logging.ERROR
    elif ARGS['log-level'].lower() == 'critical':
        LOG_LEVEL = logging.CRITICAL

    # Parse synology-download-albums and immich-download-albums to ensure than ARGS['output-folder'] is used to specify <OUTPUT_FOLDER>
    if ARGS['synology-download-albums'] != "" and ARGS['output-folder'] == "":
        print(f"❌ ERROR   : When use flag -sdAlb, --synology-download-albums, you need to provide an Output folder using flag -o, -output-folder <OUTPUT_FOLDER>")
        exit(1)
    if ARGS['immich-download-albums'] != "" and ARGS['output-folder'] == "":
        print(f"❌ ERROR   : When use flag -idAlb, --immich-download-albums, you need to provide an Output folder using flag -o, -output-folder <OUTPUT_FOLDER>")
        exit(1)

    # Parse albums-folders Arguments to convert to a List if more than one Album folder is provide
    ARGS['albums-folders'] = parse_folders(ARGS['albums-folders'])
    # if ARGS['albums-folders'] == []:
    #     ARGS['albums-folders'] = 'Albums'

    # Parse duplicates-folders Arguments
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

    # Parse 'immich-remove-all-albums in combination with 'including-albums-assets'
    if ARGS['remove-albums-assets'] and not ARGS['immich-remove-all-albums']:
        PARSER.error("--remove-albums-assets is a modifier of argument --immich-remove-all-albums and cannot work alone.")

    return ARGS

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
                flattened.append(item.rstrip(','))
        return flattened

    # Si no es ni lista ni string, devolver lista vacía
    return []

def create_global_variable_from_args(args):
    """
    Crea una única variable global ARGS que contenga todos los argumentos proporcionados en un objeto Namespace.
    Se puede acceder a cada argumento mediante ARGS["nombre-argumento"] o ARGS.nombre_argumento.

    :param args: Namespace con los argumentos del PARSER
    """
    ARGS = {arg_name.replace("_", "-"): arg_value for arg_name, arg_value in vars(args).items()}
    return ARGS

def getParser():
    return PARSER