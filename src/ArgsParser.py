import logging

from GlobalVariables import SCRIPT_DESCRIPTION, SCRIPT_NAME, SCRIPT_VERSION, SCRIPT_DATE, resolve_path
from CustomHelpFormatter import CustomHelpFormatter
from CustomPager import PagedParser
import argparse
import os
from datetime import datetime

choices_for_message_levels          = ['debug', 'info', 'warning', 'error', 'critical']
choices_for_folder_structure        = ['flatten', 'year', 'year/month', 'year-month']
choices_for_remove_duplicates       = ['list', 'move', 'remove']
choices_for_AUTOMATED_MIGRATION_SRC = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']
choices_for_AUTOMATED_MIGRATION_TGT = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2']
valid_asset_types                         = ['all', 'image', 'images', 'photo', 'photos', 'video', 'videos']

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


    PARSER.add_argument("-v", "--version", action=VersionAction, nargs=0, help="Show the Tool name, version, and date, then exit.")


    # FEATURES FOR AUTOMATED MIGRATION:
    # ---------------------------------
    PARSER.add_argument( "-source", "--source", metavar="<SOURCE>", default="",
                        help="Select the <SOURCE> for the AUTOMATED-MIGRATION Process to Pull all your Assets (including Albums) from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service)."
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
                        help="Select the <TARGET> for the AUTOMATED-MIGRATION Process to Pull all your Assets (including Albums) from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums that you may have on the <SOURCE> Cloud Service)."
                         "\n"
                         "\nPossible values:"
                         "\n  ['synology', 'immich']-[id] or <OUTPUT_FOLDER>"
                         "\n  [id] = [1, 2] select which account to use from the Config.ini file."
                         "\n"    
                         "\nExamples: "
                         "\n ​--source=immich-1 -> Select Immich Photos account 1 as Target."
                         "\n ​--source=synology-2 -> Select Synology Photos account 2 as Target."
                         "\n ​--source=/home/local_folder -> Select this local folder as Target."
                         )
    PARSER.add_argument("-dashb", "--dashboard",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=True,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Enable or disable Live Dashboard feature during Autometed Migration Job. This argument only applies if both '--source' and '--target' argument are given (AUTOMATED-MIGRATION FEATURE). (default: True)."
    )
    PARSER.add_argument("-parallel", "--parallel-migration",
                        metavar="= [true,false]",
                        nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
                        const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
                        default=True,  # Si no se pasa el argumento, el valor por defecto es True
                        type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
                        help="Select Parallel/Secuencial Migration during Automated Migration Job. This argument only applies if both '--source' and '--target' argument are given (AUTOMATED-MIGRATION FEATURE). (default: True)."
    )

    PARSER.add_argument("-from", "--from-date", metavar="<FROM_DATE>", default="", help="Specify the initial date to filter assets in the different Photo Clients.")
    PARSER.add_argument("-to", "--to-date", metavar="<TO_DATE>", default="", help="Specify the final date to filter assets in the different Photo Clients.")
    PARSER.add_argument("-country", "--country", metavar="<COUNTRY_NAME>", default="", help="Specify the Country Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-city", "--city", metavar="<CITY_NAME>", default="", help="Specify the City Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-person", "--person", metavar="<PEOPLE_NAME>", default="", help="Specify the People Name to filter assets in the different Photo Clients.")
    PARSER.add_argument("-type", "--asset-type", metavar="= [image,video,all]", default="all", help="Specify the Asset Type to filter assets in the different Photo Clients. (default: all)")
    # PARSER.add_argument("-archive", "--archive",
    #                     metavar="= [true,false]",
    #                     nargs="?",  # Permite que el argumento sea opcionalmente seguido de un valor
    #                     const=True,  # Si el usuario pasa --dashboard sin valor, se asigna True
    #                     default=False,  # Si no se pasa el argumento, el valor por defecto es True
    #                     type=lambda v: v.lower() in ("true", "1", "yes", "on"),  # Convierte "true", "1", "yes" en True; cualquier otra cosa en False
    #                     help="Specify if you want to filter only Archived assets in the different Photo Clients."
    # )


    # GENERAL FEATURES:
    # -----------------
    PARSER.add_argument("-i", "--input-folder", metavar="<INPUT_FOLDER>", default="", help="Specify the input folder that you want to process.")
    PARSER.add_argument("-o", "--output-folder", metavar="<OUTPUT_FOLDER>", default="", help="Specify the output folder to save the result of the processing action.")
    PARSER.add_argument("-AlbFld", "--albums-folders", metavar="<ALBUMS_FOLDER>", default="", nargs="*", help="If used together with '-suAll, --synology-upload-all' or '-iuAll, --immich-upload-all', it will create an Album per each subfolder found in <ALBUMS_FOLDER>.")
    PARSER.add_argument("-rAlbAss", "--remove-albums-assets", action="store_true", default=False, help="If used together with '-srAllAlb, --synology-remove-all-albums' or '-irAllAlb, --immich-remove-all-albums', it will also delete the assets (photos/videos) inside each album.")
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
    # PARSER.add_argument("-gizf", "--google-input-zip-folder", metavar="<ZIP_FOLDER>", default="", help="Specify the Zip folder where the Zip files are placed. If this option is omitted, unzip of input files will be skipped.")
    PARSER.add_argument("-gtProc", "--google-takeout-to-process", metavar="<TAKEOUT_FOLDER>", default="",
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


    # FEATURES FOR SYNOLOGY PHOTOS:
    # --------------------------------
    PARSER.add_argument("-suAlb", "--synology-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Synology Photos.")
    PARSER.add_argument("-sdAlb", "--synology-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Tool will connect to Synology Photos and will download those Albums whose name is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this feature)."
                           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                           "\n- To download all albums mathing any pattern you can use patterns in <ALBUMS_NAME>, i.e: --synology-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
                           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --synology-download-albums 'album1', 'album2', 'album3'."
                        )
    PARSER.add_argument("-suAll", "--synology-upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into Synology Photos."
                           "\n- The Tool will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside each subfolder will be associated to a new Album in Synology Photos with the same name as the subfolder."
                           "\n- If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will create Albums also for each subfolder found in <ALBUMS_FOLDER>."
                        )
    PARSER.add_argument("-sdAll", "--synology-download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Tool will connect to Synology Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
                           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
                           "\n- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside."
                        )
    PARSER.add_argument("-srEmpAlb", "--synology-remove-empty-albums", action="store_true", default="", help="The Tool will look for all Albums in your Synology Photos account and if any Album is empty, will remove it from your Synology Photos account.")
    PARSER.add_argument("-srDupAlb", "--synology-remove-duplicates-albums", action="store_true", default="", help="The Tool will look for all Albums in your Synology Photos account and if any Album is duplicated, will remove it from your Synology Photos account.")
    PARSER.add_argument("-srAll", "--synology-remove-all-assets", action="store_true", default="", help="CAUTION!!! The Tool will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Synology database.")
    PARSER.add_argument("-srAllAlb", "--synology-remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! The Tool will delete ALL your Albums from Synology database."
                           "\nOptionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )


    # FEATURES FOR IMMICH PHOTOS:
    # -------------------------------
    PARSER.add_argument("-iuAlb", "--immich-upload-albums", metavar="<ALBUMS_FOLDER>", default="", help="The Tool will look for all Subfolders with assets within <ALBUMS_FOLDER> and will create one Album per subfolder into Immich Photos.")
    PARSER.add_argument("-idAlb", "--immich-download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="The Tool will connect to Immich Photos and will download those Albums whose name is in '<ALBUMS_NAME>' to the folder <OUTPUT_FOLDER> given by the argument '-o, --output-folder <OUTPUT_FOLDER>' (mandatory argument for this feature)."
                           "\n- To download ALL Albums use 'ALL' as <ALBUMS_NAME>."
                           "\n- To download all albums mathing any pattern you can use patterns in ALBUMS_NAME, i.e: --immich-download-albums 'dron*' to download all albums starting with the word 'dron' followed by other(s) words."
                           "\n- To download several albums you can separate their names by comma or space and put the name between double quotes. i.e: --immich-download-albums 'album1', 'album2', 'album3'."
                        )
    PARSER.add_argument("-iuAll", "--immich-upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="The Tool will look for all Assets within <INPUT_FOLDER> and will upload them into Immich Photos."
                           "\n- The Tool will create a new Album per each Subfolder found in 'Albums' subfolder and all assets inside each subfolder will be associated to a new Album in Immich Photos with the same name as the subfolder."
                           "\n- If the argument '-AlbFld, --albums-folders <ALBUMS_FOLDER>' is also passed, then this function will create Albums also for each subfolder found in <ALBUMS_FOLDER>."
                        )
    PARSER.add_argument("-idAll", "--immich-download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="The Tool will connect to Immich Photos and will download all the Album and Assets without Albums into the folder <OUTPUT_FOLDER>."
                           "\n- All Albums will be downloaded within a subfolder of <OUTPUT_FOLDER>/Albums/ with the same name of the Album and all files will be flattened into it."
                           "\n- Assets with no Albums associated will be downloaded within a subfolder called <OUTPUT_FOLDER>/No-Albums/ and will have a year/month structure inside."
                        )
    PARSER.add_argument("-irEmpAlb", "--immich-remove-empty-albums", action="store_true", default="", help="The Tool will look for all Albums in your Immich Photos account and if any Album is empty, will remove it from your Immich Photos account.")
    PARSER.add_argument("-irDupAlb", "--immich-remove-duplicates-albums", action="store_true", default="", help="The Tool will look for all Albums in your Immich Photos account and if any Album is duplicated, will remove it from your Immich Photos account.")
    PARSER.add_argument("-irAll", "--immich-remove-all-assets", action="store_true", default="", help="CAUTION!!! The Tool will delete ALL your Assets (Photos & Videos) and also ALL your Albums from Immich database.")
    PARSER.add_argument("-irAllAlb", "--immich-remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! The Tool will delete ALL your Albums from Immich database."
                           "\nOptionally ALL the Assets associated to each Album can be deleted If you also include the argument '-rAlbAss, --remove-albums-assets' argument."
                        )
    PARSER.add_argument("-irOrphan", "--immich-remove-orphan-assets", action="store_true", default="", help="The Tool will look for all Orphan Assets in Immich Database and will delete them. IMPORTANT: This feature requires a valid ADMIN_API_KEY configured in Config.ini.")



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


def checkArgs(ARGS, PARSER):
    global DEFAULT_DUPLICATES_ACTION, LOG_LEVEL

    # Check all provided arguments in the list of arguments to check to resolve the paths correctly for both, docker instance and normal instance.
    keys_to_check = ['source', 'target', 'input-folder', 'output-folder', 'albums-folder', 'google-takeout-to-process',
                     'synology-upload-albums', 'synology-download-albums', 'synology-upload-all', 'synology-download-all',
                     'immich-upload-albums', 'immich-download-albums', 'immich-upload-all', 'immich-download-all',
                     'find-duplicates', 'fix-symlinks-broken', 'rename-folders-content-based',
                     ]

    resolve_all_possible_paths(args_dict=ARGS, keys_to_check=keys_to_check)

    # Remove '_' at the beginning of the string in case it has it.
    ARGS['google-output-folder-suffix'] = ARGS['google-output-folder-suffix'].lstrip('_')

    # Remove last / for all folders expected as arguments:
    ARGS['input-folder']                    = ARGS['input-folder'].rstrip('/\\')
    ARGS['output-folder']                   = ARGS['output-folder'].rstrip('/\\')
    ARGS['google-takeout-to-process']       = ARGS['google-takeout-to-process'].rstrip('/\\')
    ARGS['synology-upload-albums']          = ARGS['synology-upload-albums'].rstrip('/\\')
    ARGS['synology-upload-all']             = ARGS['synology-upload-all'].rstrip('/\\')
    ARGS['synology-download-all']           = ARGS['synology-download-all'].rstrip('/\\')
    ARGS['immich-upload-albums']            = ARGS['immich-upload-albums'].rstrip('/\\')
    ARGS['immich-upload-all']               = ARGS['immich-upload-all'].rstrip('/\\')
    ARGS['immich-download-all']             = ARGS['immich-download-all'].rstrip('/\\')
    ARGS['fix-symlinks-broken']             = ARGS['fix-symlinks-broken'].rstrip('/\\')
    ARGS['rename-folders-content-based']    = ARGS['rename-folders-content-based'].rstrip('/\\')

    # Set None for google-input-zip-folder argument, and only if unzip is needed will change this to the proper folder.
    ARGS['google-input-zip-folder'] = None

    # Set None for MIGRATION argument, and only if both source and target argument are providin, it will set properly.
    ARGS['AUTOMATED-MIGRATION'] = None


    # Parse AUTOMATED-MIGRATION Arguments
    # Manual validation of --source and --target to allow predefined values but also local folders.
    if ARGS['source'] and not ARGS['target']:
        PARSER.error(f"\n\n❌ ERROR   : Invalid syntax. Argument '--source' detected but not '--target' providen'. You must specify both, --source and --target to execute AUTOMATED-MIGRATION task.\n")
        exit(1)
    if ARGS['target'] and not ARGS['source']:
        PARSER.error(f"\n\n❌ ERROR   : Invalid syntax. Argument '--target' detected but not '--source' providen'. You must specify both, --source and --target to execute AUTOMATED-MIGRATION task.\n")
        exit(1)
    if ARGS['source'] and ARGS['source'] not in choices_for_AUTOMATED_MIGRATION_SRC and not os.path.isdir(ARGS['source']):
        PARSER.error(f"\n\n❌ ERROR   : Invalid choice detected for --source='{ARGS['source']}'. \nMust be an existing local folder or one of the following values: \n{choices_for_AUTOMATED_MIGRATION_SRC}.\n")
        exit(1)
    if ARGS['target'] and ARGS['target'] not in choices_for_AUTOMATED_MIGRATION_TGT and not os.path.isdir(ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Invalid choice detected for --target='{ARGS['target']}'. \nMust be an existing local folder one of the following values: \n{choices_for_AUTOMATED_MIGRATION_TGT}.\n")
        exit(1)
    if ARGS['source'] and ARGS['target']:
        ARGS['AUTOMATED-MIGRATION'] = [ARGS['source'], ARGS['target']]


    # Check if --dashboard=True and not --source and --target have been given
    args = PARSER.parse_args()
    dashboard_provided = "--dashboard" in [arg.split("=")[0] for arg in vars(args).keys()]
    if dashboard_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Argument '--dashboard' can only be used with Automated Migration feature. Arguments --source and --target are required.\n")
        exit(1)


    # Check if --parallel-migration=True and not --source and --target have been given
    args = PARSER.parse_args()
    dashboard_provided = "--parallel-migration" in [arg.split("=")[0] for arg in vars(args).keys()]
    if dashboard_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(f"\n\n❌ ERROR   : Argument '--parallel-migration' can only be used with Automated Migration feature. Arguments --source and --target are required.\n")
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
        PARSER.error(f"\n\n❌ ERROR   : When use flag -sdAlb, --synology-download-albums, you need to provide an Output folder using flag -o, -output-folder <OUTPUT_FOLDER>\n")
        exit(1)
    if ARGS['immich-download-albums'] != "" and ARGS['output-folder'] == "":
        PARSER.error(f"\n\n❌ ERROR   : When use flag -idAlb, --immich-download-albums, you need to provide an Output folder using flag -o, -output-folder <OUTPUT_FOLDER>\n")
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


    # Parse 'immich-remove-all-albums in combination with 'including-albums-assets'
    if ARGS['remove-albums-assets'] and not ARGS['immich-remove-all-albums']:
        PARSER.error(f"\n\n❌ ERROR   : --remove-albums-assets is a modifier of argument --immich-remove-all-albums and cannot work alone.\n")
        exit(1)


    # Parseamos las fechas de ARGS['from-date'] y ARGS['to-date'] para devolver una fecha en valida en formato iso8601 en caso de que contenga alguna fecha válida, o cadena vacía en caso contrario
    ARGS['from-date'] = parse_to_iso8601(ARGS.get('from-date', ''))
    ARGS['to-date'] = parse_to_iso8601(ARGS.get('to-date', ''))


    # Parseamos type
    if ARGS['asset-type'].lower() not in valid_asset_types:
        PARSER.error(f"\n\n❌ ERROR   : --asset-type argument is invalid. Valid values are:\n{valid_asset_types}")
        exit(1)

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
    Se puede acceder a cada argumento mediante ARGS["nombre-argumento"] o ARGS.nombre_argumento.

    :param args: Namespace con los argumentos del PARSER
    """
    ARGS = {arg_name.replace("_", "-"): arg_value for arg_name, arg_value in vars(args).items()}
    return ARGS

def getParser():
    return PARSER

def parse_to_iso8601(date_str):
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    # Lista de formatos a probar
    date_formats = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            continue
    # Si no se pudo convertir, devuelve None
    return None

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
        choices_for_AUTOMATED_MIGRATION_SRC +
        choices_for_AUTOMATED_MIGRATION_TGT
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
