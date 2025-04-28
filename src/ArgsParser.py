import logging

from GlobalVariables import SCRIPT_DESCRIPTION, SCRIPT_NAME, SCRIPT_VERSION, SCRIPT_DATE, resolve_path
from CustomHelpFormatter import CustomHelpFormatter
from CustomPager import PagedParser
import argparse
import os
import re
from datetime import datetime

choices_for_message_levels          = ['debug', 'info', 'warning', 'error']
choices_for_folder_structure        = ['flatten', 'year', 'year/month', 'year-month']
choices_for_remove_duplicates       = ['list', 'move', 'remove']
choices_for_AUTOMATIC_MIGRATION_SRC = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2', 'synology-photos-3', 'synology-photos3', 'synology-3', 'synology3',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2', 'immich-photos-', 'immich-photos3', 'immich-3', 'immich3']
choices_for_AUTOMATIC_MIGRATION_TGT = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2', 'synology-photos-3', 'synology-photos3', 'synology-3', 'synology3',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2', 'immich-photos-', 'immich-photos3', 'immich-3', 'immich3']
valid_asset_types                   = ['all', 'image', 'images', 'photo', 'photos', 'video', 'videos']

PARSER = None

def parse_arguments():
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

    PARSER.add_argument("-v", "--version", action=VersionAction, nargs=0, help="Show the Tool name, version, and date, then exit.")

    # FEATURES FOR AUTOMATIC MIGRATION:
    # ---------------------------------
    PARSER.add_argument( "-source", "--source", metavar="<SOURCE>", default="",
                        help="Select the <SOURCE> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service)."
                         "\n"
                         "\nPossible values:"
                         "\n  ['synology', 'immich']-[id] or <INPUT_FOLDER>"
                         "\n  [id] = [1, 2] select which account to use from the Config.ini file."
                         "\n"    
                         "\nExamples: "
                         "\n ​--source=immich-1 -> Select Immich Photos account 1 as Source."
                         "\n ​--source=synology-2 -> Select Synology Photos account 2 as Source."
                         "\n ​--source=/home/local_folder -> Select this local folder as Source."
                         "\n ​--source=/home/Takeout -> Select this Takeout folder as Source."
                         "\n ​                      (both, zipped and unzipped format are supported)"
                         )
    PARSER.add_argument( "-target", "--target", metavar="<TARGET>", default="",
                        help="Select the <TARGET> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service)."
                         "\n"
                         "\nPossible values:"
                         "\n  ['synology', 'immich']-[id] or <OUTPUT_FOLDER>"
                         "\n  [id] = [1, 2] select which account to use from the Config.ini file."
                         "\n"    
                         "\nExamples: "
                         "\n ​--target=immich-1 -> Select Immich Photos account 1 as Target."
                         "\n ​--target=synology-2 -> Select Synology Photos account 2 as Target."
                         "\n ​--target=/home/local_folder -> Select this local folder as Target."
                         )
    PARSER.add_argument("-dashb", "--dashboard",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=True,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Enable or disable Live Dashboard feature during Autometed Migration Job. This argument only applies if both '--source' and '--target' argument are given (AUTOMATIC-MIGRATION FEATURE). (default: True)."
    )
    PARSER.add_argument("-parallel", "--parallel-migration",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=True,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Select Parallel/Secuencial Migration during Automatic Migration Job. This argument only applies if both '--source' and '--target' argument are given (AUTOMATIC-MIGRATION FEATURE). (default: True)."
    )


    # GENERAL FEATURES:
    # -----------------
    PARSER.add_argument("-i", "--input-folder", metavar="<INPUT_FOLDER>", default="", help="Specify the input folder that you want to process.")
    PARSER.add_argument("-o", "--output-folder", metavar="<OUTPUT_FOLDER>", default="", help="Specify the output folder to save the result of the processing action.")
    PARSER.add_argument("-client", "--client",
                        metavar="= ['google-takeout', 'synology', 'immich']",
                        default='google-takeout',  # Si no se pasa el argumento, se asigna 'google-takeout'
                        type=validate_client,      # Ahora espera un string con el nombre del cliente como tipo de argumento
                        help="Set the client to use for the selected feature."
                        )
    PARSER.add_argument("-id", "--account-id",
                        metavar="= [1,2,3]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=1,  # Si el usuario pasa --account-id sin valor, se asigna 1
                        default=1,  # Si no se pasa el argumento, también se asigna 1
                        type=validate_account_id,  # Ahora espera un entero como tipo de argumento
                        help="Set the account ID for Synology Photos or Immich Photos. (default: 1). This value must exist in the Configuration file as suffix of USERNAME/PASSORD or API_KEY_USER. (example for Immich ID=2: IMMICH_USERNAME_2/IMMICH_PASSWORD_2 or IMMICH_API_KEY_USER_2 entries must exist in Config.ini file)."
                        )
    PARSER.add_argument("-OTP", "--one-time-password", action="store_true", default="", help="This Flag allow you to login into Synology Photos using 2FA with an OTP Token.")

    PARSER.add_argument("-from", "--filter-from-date", metavar="<FROM_DATE>", default=None, help="Specify the initial date to filter assets in the different Photo Clients.")
    PARSER.add_argument("-to", "--filter-to-date", metavar="<TO_DATE>", default=None, help="Specify the final date to filter assets in the different Photo Clients.")
    PARSER.add_argument("-country", "--filter-by-country", metavar="<COUNTRY_NAME>", default=None, help="Specify the Country Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-city", "--filter-by-city", metavar="<CITY_NAME>", default=None, help="Specify the City Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-person", "--filter-by-person", metavar="<PERSON_NAME>", default=None, help="Specify the Person Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-type", "--filter-by-type", metavar="= [image,video,all]", default=None, help="Specify the Asset Type to filter assets in the different Photo Clients. (default: all)")
    # PARSER.add_argument("-archive", "--archive",
    #                     metavar="= [true,false]",
    #                     nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
    #                     const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
    #                     default=False,  # Si no se pasa el argumento, el valor por defecto es True
    #                     type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
    #                     help="Specify if you want to filter only Archived assets in the different Photo Clients."
    # )

    PARSER.add_argument("-AlbFld", "--albums-folders", metavar="<ALBUMS_FOLDER>", default="", nargs="*", help="If used together with '-uAll, --upload-all', it will create an Album per each subfolder found in <ALBUMS_FOLDER>.")
    PARSER.add_argument("-rAlbAss", "--remove-albums-assets", action="store_true", default=False,
                        help="If used together with '-rAllAlb, --remove-all-albums' or '-rAlb, --remove-albums', it will also remove the assets (photos/videos) inside each album.")
    PARSER.add_argument("-gpthProg", "--show-gpth-progress",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=False,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Enable or disable Progress messages during GPTH Processing. (default: False)."
    )
    PARSER.add_argument("-gpthErr", "--show-gpth-errors",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=True,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Enable or disable Error messages during GPTH Processing. (default: True)."
    )
    PARSER.add_argument("-nolog", "--no-log-file", action="store_true", help="Skip saving output messages to execution log file.")
    PARSER.add_argument("-loglevel", "--log-level", metavar=f"{choices_for_message_levels}", choices=choices_for_message_levels, default="info", help="Specify the log level for logging and screen messages.")


    # FEATURES FOR GOOGLE PHOTOS:
    # ---------------------------
    PARSER.add_argument("-gTakeout", "--google-takeout", metavar="<TAKEOUT_FOLDER>", default="",
                        help="Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata and organize assets inside it. If any Zip file is found inside it, the Zip will be extracted to the folder '<TAKEOUT_FOLDER>_unzipped_<TIMESTAMP>', and will use the that folder as input <TAKEOUT_FOLDER>."
                          "\nThe processed Takeout will be saved into the folder '<TAKEOUT_FOLDER>_processed_<TIMESTAMP>'"
                          "\nThis argument is mandatory to run the Google Takeout Processor Feature."
                        )
    PARSER.add_argument("-gofs", "--google-output-folder-suffix", metavar="<SUFFIX>", default="processed", help="Specify the suffix for the output folder. Default: 'processed'")
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


    # FEATURES FOR SYNOLOGY/IMMICH PHOTOS:
    # -------------------------------
    PARSER.add_argument("-uAlb", "--upload-albums", metavar="<ALBUMS_FOLDER>", default="",
                        help="The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into the selected Photo client.")
    PARSER.add_argument("-dAlb", "--download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Tool will connect to the selected Photo client and will download those Albums whose name is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this feature)."
                             "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                             "\n- To download all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
                             "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --download-albums 'album1', 'album2', 'album3'."
                        )
    PARSER.add_argument("-uAll", "--upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into the selected Photo client."
                             "\n- The Tool will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside each subfolder will be associated to a new Album in the selected Photo client with the same name as the subfolder."
                             "\n- If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will create Albums also for each subfolder found in <ALBUMS_FOLDER>."
                        )
    PARSER.add_argument("-dAll", "--download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Tool will connect to the selected Photo client and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
                             "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
                             "\n- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside."
                        )

    PARSER.add_argument("-rOrphan", "--remove-orphan-assets", action="store_true", default="",
                        help="The Tool will look for all Orphan Assets in the selected Photo client and will remove them. IMPORTANT: This feature requires a valid ADMIN_API_KEY configured in Config.ini.")

    PARSER.add_argument("-rAll", "--remove-all-assets", action="store_true", default="",
                        help="CAUTION!!! The Tool will remove ALL your Assets (Photos & Videos) and also ALL your Albums from the selected Photo client.")
    PARSER.add_argument("-rAllAlb", "--remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! The Tool will remove ALL your Albums from the selected Photo client."
                             "\nOptionally ALL the Assets associated to each Album can be removed If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )
    PARSER.add_argument("-rAlb", "--remove-albums", metavar="<ALBUMS_NAME_PATTERN>", default="",
                        help="CAUTION!!! The Tool will look for all Albums in the selected Photo client whose names matches with the pattern and will remove them."
                             "\nOptionally ALL the Assets associated to each Album can be removed If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )
    PARSER.add_argument("-rEmpAlb", "--remove-empty-albums", action="store_true", default="",
                        help="The Tool will look for all Albums in the selected Photo client account and if any Album is empty, will remove it from the selected Photo client account.")
    PARSER.add_argument("-rDupAlb", "--remove-duplicates-albums", action="store_true", default="",
                        help="The Tool will look for all Albums in the selected Photo client account and if any Album is duplicated (with the same name and size), will remove it from the selected Photo client account.")

    PARSER.add_argument("-mDupAlb", "--merge-duplicates-albums", action="store_true", default="",
                        help="The Tool will look for all Albums in the selected Photo client account and if any Album is duplicated (with the same name), will transfer all its assets to the most relevant album and remove it from the selected Photo client account.")

    PARSER.add_argument("-renAlb", "--rename-albums", metavar="<ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>", nargs="+", default="",
                        help="CAUTION!!! The Tool will look for all Albums in the selected Photo client whose names matches with the pattern and will rename them from with the replacement pattern."
                        )


    # OTHERS STAND-ALONE FEATURES:
    # -------------------------------
    PARSER.add_argument("-findDup", "--find-duplicates", metavar=f"<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]", nargs="+", default=["list", ""],
                        help="Find duplicates in specified folders."
                           "\n<ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list' "
                           "\n<DUPLICATES_FOLDER> are one or more folders (string or list), where the Tool will look for duplicates files. The order of this list is important to determine the principal file of a duplicates set. First folder will have higher priority."
                        )
    PARSER.add_argument("-procDup", "--process-duplicates", metavar="<DUPLICATES_REVISED_CSV>", default="", help="Specify the Duplicates CSV file revised with specifics Actions in Action column, and the Tool will execute that Action for each duplicates found in CSV. Valid Actions: restore_duplicate / remove_duplicate / replace_duplicate.")
    PARSER.add_argument("-fixSym", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="", help="The Tool will try to fix all symbolic links for Albums in <FOLDER_TO_FIX> folder (Useful if you have move any folder from the OUTPUT_TAKEOUT_FOLDER and some Albums seems to be empty.")
    PARSER.add_argument("-renFldcb", "--rename-folders-content-based", metavar="<ALBUMS_FOLDER>", default="", help="Usefull to rename and homogenize all Albums folders found in <ALBUMS_FOLDER> based on the date content found.")

    # Procesar la acción y las carpetas

    # Obtain args from PARSER and create global variable ARGS to easier manipulation of argument variables using the same string as in the argument (this facilitates futures refactors on arguments names)
    args = PARSER.parse_args()
    ARGS = create_global_variable_from_args(args)

    return ARGS, PARSER

def validate_account_id(valor):
    try:
        valor_int = int(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"The value '{valor}' is not a valid number.")
    if valor_int not in [1, 2, 3]:
        raise argparse.ArgumentTypeError("The account-id must be one of the following values: 1, 2 o 3.")
    return valor_int

def validate_client(valor):
    valid_clients = ['google-takeout', 'synology', 'immich']
    try:
        valor_lower = valor.lower()
    except ValueError:
        raise argparse.ArgumentTypeError(f"The value '{valor}' is not a valid string.")
    if valor_lower not in valid_clients:
        raise argparse.ArgumentTypeError(f"The client must be one of the following values: {valid_clients}")
    return valor_lower

def validate_client_arg(ARGS, PARSER):
    # Lista de flags que requieren --client
    client_required_flags = [
        'remove-empty-albums',
        'upload-albums',
        'download-albums',
        'upload-all',
        'download-all',
        'rename-albums',
        'remove-albums',
        'remove-duplicates-albums',
        'merge-duplicates-albums',
        'remove-all-assets',
        'remove-all-albums',
        'remove-orphan-assets'
    ]

    # Recorrer todos los flags que requieren client
    for flag in client_required_flags:
        if ARGS.get(flag):  # Si el usuario ha pasado este argumento
            if ARGS.get('client')=='google-takeout':
                PARSER.error(f"\n\n❌ ERROR   : The argument '--{flag}' requires that '--client' is also specified.\n")
                exit(1)


def checkArgs(ARGS, PARSER):
    global DEFAULT_DUPLICATES_ACTION, LOG_LEVEL

    # Check all provided arguments in the list of arguments to check to resolve the paths correctly for both, docker instance and normal instance.
    keys_to_check = ['source', 'target', 'input-folder', 'output-folder', 'albums-folder', 'google-takeout',
                     'upload-albums', 'upload-all', 'download-all',
                     'find-duplicates', 'fix-symlinks-broken', 'rename-folders-content-based',
                     ]

    resolve_all_possible_paths(args_dict=ARGS, keys_to_check=keys_to_check)

    # Remove '_' at the beginning of the string in case it has it.
    ARGS['google-output-folder-suffix'] = ARGS['google-output-folder-suffix'].lstrip('_')

    # Remove last / for all folders expected as arguments:
    ARGS['input-folder']                    = clean_path(ARGS['input-folder'])
    ARGS['output-folder']                   = clean_path(ARGS['output-folder'])
    ARGS['google-takeout']                  = clean_path(ARGS['google-takeout'])
    ARGS['upload-albums']                   = clean_path(ARGS['upload-albums'])
    ARGS['upload-all']                      = clean_path(ARGS['upload-all'])
    ARGS['download-all']                    = clean_path(ARGS['download-all'])
    ARGS['fix-symlinks-broken']             = clean_path(ARGS['fix-symlinks-broken'])
    ARGS['rename-folders-content-based']    = clean_path(ARGS['rename-folders-content-based'])

    # Set None for google-input-zip-folder argument, and only if unzip is needed will change this to the proper folder.
    ARGS['google-input-zip-folder'] = None

    # Set None for MIGRATION argument, and only if both source and target argument are providin, it will set properly.
    ARGS['AUTOMATIC-MIGRATION'] = None


    # Parse AUTOMATIC-MIGRATION Arguments
    # Manual validation of --source and --target to allow predefined values but also local folders.
    if ARGS['source'] and not ARGS['target']:
        PARSER.error(f"\n\n❌ ERROR   : Invalid syntax. Argument '--source' detected but not '--target' providen'. You must specify both, --source and --target to execute AUTOMATIC-MIGRATION task.\n")
        exit(1)
    if ARGS['target'] and not ARGS['source']:
        PARSER.error(f"\n\n❌ ERROR   : Invalid syntax. Argument '--target' detected but not '--source' providen'. You must specify both, --source and --target to execute AUTOMATIC-MIGRATION task.\n")
        exit(1)
    if ARGS['source'] and ARGS['source'] not in choices_for_AUTOMATIC_MIGRATION_SRC and not os.path.isdir(ARGS['source']):
        PARSER.error(f"\n\n❌ ERROR   : Invalid choice detected for --source='{ARGS['source']}'. \nMust be an existing local folder or one of the following values: \n{choices_for_AUTOMATIC_MIGRATION_SRC}.\n")
        exit(1)
    if ARGS['target'] and ARGS['target'] not in choices_for_AUTOMATIC_MIGRATION_TGT and not os.path.isdir(ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Invalid choice detected for --target='{ARGS['target']}'. \nMust be an existing local folder one of the following values: \n{choices_for_AUTOMATIC_MIGRATION_TGT}.\n")
        exit(1)
    if ARGS['source'] and ARGS['target']:
        ARGS['AUTOMATIC-MIGRATION'] = [ARGS['source'], ARGS['target']]


    # Check if --dashboard=True and not --source and --target have been given
    args = PARSER.parse_args()
    dashboard_provided = "--dashboard" in [arg.split("=")[0] for arg in vars(args).keys()]
    if dashboard_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Argument '--dashboard' can only be used with Automatic Migration feature. Arguments --source and --target are required.\n")
        exit(1)


    # Check if --parallel-migration=True and not --source and --target have been given
    args = PARSER.parse_args()
    dashboard_provided = "--parallel-migration" in [arg.split("=")[0] for arg in vars(args).keys()]
    if dashboard_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Argument '--parallel-migration' can only be used with Automatic Migration feature. Arguments --source and --target are required.\n")
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


    # Parse download-albums to ensure than ARGS['output-folder'] is used to specify <OUTPUT_FOLDER>
    if ARGS['download-albums'] != "" and ARGS['output-folder'] == "":
        PARSER.error(f"\n\n❌ ERROR   : When use flag -dAlb, --download-albums, you need to provide an Output folder using flag -o, -output-folder <OUTPUT_FOLDER>\n")
        exit(1)


    # Parse albums-folders Arguments to convert to a List if more than one Album folder is provide
    ARGS['albums-folders'] = parse_folders_list(ARGS['albums-folders'])


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
    ARGS['duplicates-folders'] = parse_folders_list(ARGS['duplicates-folders'])

    # Parse rename-albums
    if ARGS['rename-albums']:
        if len(ARGS['rename-albums']) != 2:
            PARSER.error(f"\n\n❌ ERROR   : --rename-albums requires two arguments <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>.\n")
            exit(1)
        for subarg in ARGS['rename-albums']:
            if subarg is None:
                PARSER.error(f"\n\n❌ ERROR   : --rename-albums requires two arguments <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>.\n")
                exit(1)


    # Parse 'remove-albums-assets' to check if 'remove-all-albums' or 'remove-albums' have been detected
    if ARGS['remove-albums-assets'] and not (ARGS['remove-all-albums'] or ARGS['remove-albums']):
        PARSER.error(f"\n\n❌ ERROR   : --remove-albums-assets is a modifier of argument. It need to be used together with one of the following arguments:"
                     f"\n--remove-all-albums"
                     f"\n--remove-albums"
                     f"\n")
        exit(1)


    # Parseamos las fechas de ARGS['filter-from-date'] y ARGS['filter-to-date'] para devolver una fecha en valida en formato iso8601 en caso de que contenga alguna fecha válida, o cadena vacía en caso contrario
    ARGS['filter-from-date'] = parse_text_to_iso8601(ARGS.get('filter-from-date', ''))
    ARGS['filter-to-date'] = parse_text_to_iso8601(ARGS.get('filter-to-date', ''))


    # Parseamos type
    if ARGS['filter-by-type'] and ARGS['filter-by-type'].lower() not in valid_asset_types:
        PARSER.error(f"\n\n❌ ERROR   : --filter-by-type argument is invalid. Valid values are:\n{valid_asset_types}")
        exit(1)

    # Validamos que se haya pasado --client cuando pasamos como argumento una feature de Synology/Immich
    validate_client_arg(ARGS, PARSER)

    return ARGS

def parse_folders_list(folders):
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
    Se puede acceder a cada argumento mediante ARGS['nombre-argumento'] o ARGS.nombre_argumento.

    :param args: Namespace con los argumentos del PARSER
    """
    ARGS = {arg_name.replace("_", "-"): arg_value for arg_name, arg_value in vars(args).items()}
    return ARGS

def getParser():
    return PARSER

def clean_path(path: str) -> str:
    """Quita barras finales de una ruta, respetando las comillas exteriores si las tiene."""
    if path.startswith('"') and path.endswith('"'):
        inner_path = path[1:-1]  # Quitamos las comillas
        inner_path = inner_path.rstrip('/\\')  # Quitamos las barras finales
        return f'"{inner_path}"'  # Volvemos a poner las comillas
    else:
        return path.rstrip('/\\')

def resolve_all_possible_paths(args_dict, keys_to_check=None):
    """
    Resolves all path-like values in args_dict (strings, lists, comma-separated strings),
    skipping values in known predefined choice lists or invalid types.

    Optional: you can restrict resolution to specific keys with `keys_to_check`.

    Modifies args_dict in-place.
    """
    skip_values = set(
        choices_for_message_levels +
        choices_for_folder_structure +
        choices_for_remove_duplicates +
        choices_for_AUTOMATIC_MIGRATION_SRC +
        choices_for_AUTOMATIC_MIGRATION_TGT
    )

    for key, value in args_dict.items():
        if keys_to_check is not None and key not in keys_to_check:
            continue  # saltar claves no incluidas

        # Saltar valores claramente no válidos
        if value is None or isinstance(value, (bool, int, float)) or value == "":
            continue

        # Si es lista de valores
        if isinstance(value, list):
            resolved_list = []
            for item in value:
                if isinstance(item, str):
                    item_clean = item.strip()
                    if item_clean == "" or item_clean in skip_values:
                        resolved_list.append(item_clean)
                    else:
                        resolved_list.append(resolve_path(item_clean))
                else:
                    resolved_list.append(item)
            args_dict[key] = resolved_list

        # Si es cadena (simple o separada por comas)
        elif isinstance(value, str):
            if value.strip() == "":
                continue  # no tocar cadena vacía
            parts = [part.strip() for part in value.split(',')]
            resolved_parts = []
            for part in parts:
                if part in skip_values:
                    resolved_parts.append(part)
                else:
                    resolved_parts.append(resolve_path(part))
            args_dict[key] = ', '.join(resolved_parts) if ',' in value else resolved_parts[0]

def parse_text_to_iso8601(date_str):
    """
    Intenta convertir una cadena de fecha a formato ISO 8601 (UTC a medianoche).

    Soporta:
    - Día/Mes/Año (varios formatos)
    - Año/Mes o Mes/Año (como '2024-03' o '03/2024')
    - Solo año (como '2024')

    Args:
        date_str (str): La cadena de fecha.

    Returns:
        str | None: Fecha en formato ISO 8601 o None si no se pudo convertir.
    """
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()

    # Lista de formatos con día, mes y año
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            continue
    # Año y mes: YYYY-MM, YYYY/MM, MM-YYYY, MM/YYYY
    try:
        match = re.fullmatch(r"(\d{4})[-/](\d{1,2})", date_str)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        match = re.fullmatch(r"(\d{1,2})[-/](\d{4})", date_str)
        if match:
            month, year = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
    except Exception:
        pass
    # Solo año
    if re.fullmatch(r"\d{4}", date_str):
        try:
            dt = datetime(int(date_str), 1, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except Exception:
            pass
    return None