import argparse
import os
import re
import sys
from pathlib import PurePath
from typing import Any, Dict, List, Optional, Tuple, Union

from colorama import Style

from Core import GlobalVariables as GV
from Core.CustomHelpFormatter import CustomHelpFormatter
from Core.CustomPager import PagedParser
from Core.GlobalVariables import TOOL_DESCRIPTION, TOOL_NAME, TOOL_VERSION, TOOL_DATE
from Utils.DateUtils import parse_text_to_iso8601
from Utils.StandaloneUtils import resolve_external_path

choices_for_message_levels          = ['verbose', 'debug', 'info', 'warning', 'error']
choices_for_log_formats             = ['log', 'txt', 'all']
choices_for_folder_structure        = ['flatten', 'year', 'year/month', 'year-month']
choices_for_remove_duplicates       = ['list', 'move', 'remove']
choices_for_AUTOMATIC_MIGRATION_SRC = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2', 'synology-photos-3', 'synology-photos3', 'synology-3', 'synology3',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2', 'immich-photos-', 'immich-photos3', 'immich-3', 'immich3']
choices_for_AUTOMATIC_MIGRATION_TGT = ['synology-photos', 'synology', 'synology-photos-1', 'synology-photos1', 'synology-1', 'synology1', 'synology-photos-2', 'synology-photos2', 'synology-2', 'synology2', 'synology-photos-3', 'synology-photos3', 'synology-3', 'synology3',
                                       'immich-photos', 'immich', 'immich-photos-1', 'immich-photos1', 'immich-1', 'immich1', 'immich-photos-2', 'immich-photos2', 'immich-2', 'immich2', 'immich-photos-', 'immich-photos3', 'immich-3', 'immich3']
valid_asset_types                   = ['all', 'image', 'images', 'photo', 'photos', 'video', 'videos']


def parse_arguments():
    """
    Builds the CLI argument parser (with pager support), parses arguments,
    and returns both ARGS (dict) and the parser instance.

    Returns:
        Tuple[dict, argparse.ArgumentParser]:
            - ARGS: dict with keys normalized to use '-' instead of '_' (e.g. 'input-folder')
            - PARSER: parser instance (PagedParser)
    """
    # Parser with Pagination:
    PARSER = PagedParser(
        description=f"\n{TOOL_DESCRIPTION}",
        formatter_class=CustomHelpFormatter,  # Apply the custom formatter
    )

    # Custom action for --version
    class VersionAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            print(f"\n{TOOL_NAME} {TOOL_VERSION} {TOOL_DATE} by Jaime Tur (@jaimetur)\n")
            parser.exit()

    PARSER.add_argument("-v", "--version", action=VersionAction, nargs=0,
                        help="Show the Tool name, version, and date, then exit.")

    PARSER.add_argument("-config", "--configuration-file", metavar="<CONFIGURATION_FILE>", default="",
                        help="Specify the file that contains the Configuration to connect to the different Photo Cloud Services.")

    PARSER.add_argument("-noConfirm", "--no-request-user-confirmation", action="store_true",
                        help="Do not request user confirmation before executing any feature.")

    PARSER.add_argument("-noLog", "--no-log-file", action="store_true",
                        help="Skip saving output messages to execution log file.")

    PARSER.add_argument("-logLevel", "--log-level",
                        metavar=f"=[{', '.join(level.upper() for level in choices_for_message_levels)}]",
                        choices=choices_for_message_levels,
                        default="info",
                        type=lambda s: s.lower(),  # Convert input to lowercase
                        help="Specify the log level for logging and screen messages.")

    PARSER.add_argument("-logFormat", "--log-format",
                        metavar=f"=[{', '.join(format.upper() for format in choices_for_log_formats)}]",
                        choices=choices_for_log_formats,
                        default="log",
                        type=lambda s: s.lower(),  # Convert input to lowercase
                        help="Specify the log file format.")

    PARSER.add_argument("-dateSep", "--date-separator", metavar="<DATE_SEPARATOR>", default="-",
                        help="Specify Date Separator used by feature `Auto-Rename Albums Content Based`.")

    PARSER.add_argument("-rangeSep", "--range-separator", metavar="<RANGE_OF_DATES_SEPARATOR>", default="--",
                        help="Specify Range of Dates Separator used by feature `Auto-Rename Albums Content Based`.")

    PARSER.add_argument("-fnAlbums", "--foldername-albums", metavar="<ALBUMS_FOLDER>", default="",
                        help="Specify the folder name to store all your processed photos associated to any Album.")

    PARSER.add_argument("-fnNoAlbums", "--foldername-no-albums", metavar="<NO_ALBUMS_FOLDER>", default="",
                        help="Specify the folder name to store all your processed photos (including those associated to Albums).")

    PARSER.add_argument("-fnLogs", "--foldername-logs", metavar="<LOG_FOLDER>", default="",
                        help="Specify the folder name to save the execution Logs.")

    PARSER.add_argument("-fnDuplicat", "--foldername-duplicates-output", metavar="<DUPLICATES_OUTPUT_FOLDER>", default="",
                        help="Specify the folder name to save the outputs of 'Find Duplicates' Feature.")

    PARSER.add_argument("-fnExtDates", "--foldername-extracted-dates", metavar="<EXTRACTED_DATES_FOLDER>", default="",
                        help="Specify the folder name to save the Metadata outputs of 'Extracted Dates'.")

    PARSER.add_argument("-exeGpthTool", "--exec-gpth-tool", metavar="<GPTH_PATH>", default="",
                        help="Specify an external version of GPTH Tool binary.\n"
                             "PhotoMigrator contains an embedded version of GPTH Tool, but if you want to use a different version, you can use this argument.")

    PARSER.add_argument("-exeExifTool", "--exec-exif-tool", metavar="<EXIFTOOL_PATH>", default="",
                        help="Specify an external version of EXIF Tool binary.\n"
                             "PhotoMigrator contains an embedded version of EXIF Tool, but if you want to use a different version, you can use this argument.")

    # GENERAL FEATURES:
    # -----------------
    PARSER.add_argument("-i", "--input-folder", metavar="<INPUT_FOLDER>", default="", type=clean_path,
                        help="Specify the input folder that you want to process.")

    PARSER.add_argument("-o", "--output-folder", metavar="<OUTPUT_FOLDER>", default="", type=clean_path,
                        help="Specify the output folder to save the result of the processing action.")

    PARSER.add_argument("-client", "--client",
                        metavar="= ['google-takeout', 'synology', 'immich']",
                        default='google-takeout',  # If not provided, default is 'google-takeout'
                        type=validate_client,      # Validates client string
                        help="Set the client to use for the selected feature.")

    PARSER.add_argument("-id", "--account-id",
                        metavar="= [1-3]",
                        nargs="?",     # Optional value after the flag
                        const=1,       # If user passes --account-id with no value, use 1
                        default=1,     # If not provided, default is 1
                        type=validate_account_id,
                        help="Set the account ID for Synology Photos or Immich Photos (default: 1). "
                             "This value must exist in the Config.ini as suffix of USERNAME/PASSWORD or API_KEY_USER.\n"
                             "Example for Immich ID=2:\n"
                             "  IMMICH_USERNAME_2/IMMICH_PASSWORD_2 or IMMICH_API_KEY_USER_2 entries must exist in Config.ini.")

    PARSER.add_argument("-from", "--filter-from-date", metavar="<FROM_DATE>", default=None,
                        help="Specify the initial date to filter assets in the different Photo Clients.")

    PARSER.add_argument("-to", "--filter-to-date", metavar="<TO_DATE>", default=None,
                        help="Specify the final date to filter assets in the different Photo Clients.")

    PARSER.add_argument("-type", "--filter-by-type", metavar="= [image,video,all]", default=None,
                        help="Specify the Asset Type to filter assets in the different Photo Clients. (default: all)")

    PARSER.add_argument("-country", "--filter-by-country", metavar="<COUNTRY_NAME>", default=None,
                        help="Specify the Country Name to filter assets in the different Photo Clients.")

    PARSER.add_argument("-city", "--filter-by-city", metavar="<CITY_NAME>", default=None,
                        help="Specify the City Name to filter assets in the different Photo Clients.")

    PARSER.add_argument("-person", "--filter-by-person", metavar="<PERSON_NAME>", default=None,
                        help="Specify the Person Name to filter assets in the different Photo Clients.")

    PARSER.add_argument("-AlbFolder", "--albums-folders", metavar="<ALBUMS_FOLDER>", default="", nargs="*",
                        help="If used together with '-uAll, --upload-all', it will create an Album per each subfolder found in <ALBUMS_FOLDER>.")

    PARSER.add_argument("-rAlbAsset", "--remove-albums-assets", action="store_true", default=False,
                        help="If used together with '-rAllAlb, --remove-all-albums' or '-rAlb, --remove-albums', "
                             "it will also remove the assets (photos/videos) inside each album.")

    # FEATURES FOR AUTOMATIC MIGRATION:
    # --------------------------------
    PARSER.add_argument("-source", "--source", metavar="<SOURCE>", default="",
                        help="Select the <SOURCE> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) "
                             "from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums).\n\n"
                             "Possible values:\n"
                             "  ['synology', 'immich']-[id] or <INPUT_FOLDER>\n"
                             "  [id] = [1, 2] select which account to use from the Config.ini file.\n\n"
                             "Examples:\n"
                             "  --source=immich-1   -> Select Immich Photos account 1 as Source.\n"
                             "  --source=synology-2 -> Select Synology Photos account 2 as Source.\n"
                             "  --source=/home/local_folder -> Select this local folder as Source.\n"
                             "  --source=/home/Takeout -> Select this Takeout folder as Source. (zipped and unzipped format supported)")

    PARSER.add_argument("-target", "--target", metavar="<TARGET>", default="",
                        help="Select the <TARGET> for the AUTOMATIC-MIGRATION Process to Pull all your Assets (including Albums) "
                             "from the <SOURCE> Cloud Service and Push them to the <TARGET> Cloud Service (including all Albums).\n\n"
                             "Possible values:\n"
                             "  ['synology', 'immich']-[id] or <OUTPUT_FOLDER>\n"
                             "  [id] = [1, 2] select which account to use from the Config.ini file.\n\n"
                             "Examples:\n"
                             "  --target=immich-1   -> Select Immich Photos account 1 as Target.\n"
                             "  --target=synology-2 -> Select Synology Photos account 2 as Target.\n"
                             "  --target=/home/local_folder -> Select this local folder as Target.")

    PARSER.add_argument("-move", "--move-assets",
                        metavar="= [true,false]",
                        nargs="?",
                        const=True,
                        default=False,
                        type=str2bool,
                        help="If this argument is present, the assets will be moved from <SOURCE> to <TARGET> instead of copied.\n"
                             "(default: False).")

    PARSER.add_argument("-dashboard", "--dashboard",
                        metavar="= [true,false]",
                        nargs="?",
                        const=True,
                        default=True,
                        type=str2bool,
                        help="Enable or disable Live Dashboard feature during Automated Migration job. "
                             "This argument only applies if both '--source' and '--target' arguments are given.\n"
                             "(default: True).")

    PARSER.add_argument("-parallel", "--parallel-migration",
                        metavar="= [true,false]",
                        nargs="?",
                        const=True,
                        default=True,
                        type=str2bool,
                        help="Select Parallel/Sequential migration during Automatic Migration job.\n"
                             "This argument only applies if both '--source' and '--target' arguments are given.\n"
                             "(default: True).")

    # FEATURES FOR GOOGLE PHOTOS:
    # ---------------------------
    PARSER.add_argument("-gTakeout", "--google-takeout", metavar="<TAKEOUT_FOLDER>", default="",
                        help="Process the Takeout folder <TAKEOUT_FOLDER> to fix all metadata and organize assets inside it. "
                             "If any Zip file is found inside it, the Zip will be extracted to the folder "
                             "'<TAKEOUT_FOLDER>_unzipped_<TIMESTAMP>', and that folder will be used as input.\n"
                             "The processed Takeout will be saved into the folder '<TAKEOUT_FOLDER>_processed_<TIMESTAMP>'.\n"
                             "This argument is mandatory to run the Google Takeout Processor feature.")

    PARSER.add_argument("-gofs", "--google-output-folder-suffix", metavar="<SUFFIX>", default="processed",
                        help="Specify the suffix for the output folder. Default: 'processed'")

    PARSER.add_argument("-gafs", "--google-albums-folders-structure",
                        metavar=f"{choices_for_folder_structure}",
                        default="flatten",
                        help="Specify the folder structure type for each Album folder (Default: 'flatten').",
                        type=lambda s: s.lower(),
                        choices=choices_for_folder_structure)

    PARSER.add_argument("-gnas", "--google-no-albums-folders-structure",
                        metavar=f"{choices_for_folder_structure}",
                        default="year/month",
                        help="Specify the folder structure type for '<NO_ALBUMS_FOLDER>' folders (Default: 'year/month').",
                        type=lambda s: s.lower(),
                        choices=choices_for_folder_structure)

    PARSER.add_argument("-gics", "--google-ignore-check-structure", action="store_true",
                        help="Ignore Check Google Takeout structure ('.json' files, 'Photos from ' sub-folders, etc.), "
                             "and fix all files found on <TAKEOUT_FOLDER> trying to guess timestamps.")

    PARSER.add_argument("-gnsa", "--google-no-symbolic-albums", action="store_true",
                        help="Duplicate album assets instead of creating symlinks to the original asset within <NO_ALBUMS_FOLDER>.\n"
                             "(Makes your output portable but requires more HDD space).\n"
                             "IMPORTANT: This can considerably increase output size, especially if you have many albums.\n"
                             "Example: if one asset belongs to 3 albums, you will end up with 4 copies (original + 3).")

    PARSER.add_argument("-grdf", "--google-remove-duplicates-files", action="store_true",
                        help="Remove duplicate files in <OUTPUT_TAKEOUT_FOLDER> after fixing them.")

    PARSER.add_argument("-graf", "--google-rename-albums-folders", action="store_true",
                        help="Rename album folders in <OUTPUT_TAKEOUT_FOLDER> based on content dates after fixing them.")

    PARSER.add_argument("-gsef", "--google-skip-extras-files", action="store_true",
                        help="Skip processing extra photos such as -edited, -effects photos.")

    PARSER.add_argument("-gsma", "--google-skip-move-albums", action="store_true",
                        help="Skip moving albums to '<ALBUMS_FOLDER>'.")

    PARSER.add_argument("-gSkipGpth", "--google-skip-gpth-tool", action="store_true",
                        help="Skip processing files with GPTH Tool.\n"
                             "CAUTION: NOT RECOMMENDED (core of the Google Takeout process). Use only for testing.")

    PARSER.add_argument("-gSkipPrep", "--google-skip-preprocess", action="store_true",
                        help="Skip pre-process Google Takeout which includes:\n"
                             "  1) Clean Takeout folder\n"
                             "  2) Fix MP4/Live Picture associations\n"
                             "  3) Fix truncated filenames/extensions\n"
                             "This is important for high accuracy. If you already pre-processed the same Takeout using "
                             "'-gKeepTakeout,--google-keep-takeout-folder', you can skip it.")

    PARSER.add_argument("-gSkipPost", "--google-skip-postprocess", action="store_true",
                        help="Skip post-process Google Takeout which includes:\n"
                             "  1) Copy/Move files to output folder\n"
                             "  2) Sync MP4 files associated to Live pictures with associated HEIC/JPG\n"
                             "  3) Separate Albums folders vs original assets\n"
                             "  4) Auto rename album folders based on content dates\n"
                             "  5) Calculate statistics and compare with original Takeout\n"
                             "  6) Organize assets by year/month\n"
                             "  7) Detect and remove duplicates\n"
                             "  8) Remove empty folders\n"
                             "  9) Count albums\n"
                             " 10) Clean final media library\n"
                             "Not recommended to skip.")

    PARSER.add_argument("-gKeepTakeout", "--google-keep-takeout-folder", action="store_true",
                        help="Keep an untouched copy of original Takeout (requires double space).\n"
                             "TIP: If <TAKEOUT_FOLDER> contains the original zip files, you will preserve them anyway.")

    PARSER.add_argument("-gpthInfo", "--show-gpth-info",
                        metavar="= [true,false]",
                        nargs="?",
                        const=True,
                        default=True,
                        type=str2bool,
                        help="Enable or disable Info messages during GPTH Processing. (default: True).")

    PARSER.add_argument("-gpthError", "--show-gpth-errors",
                        metavar="= [true,false]",
                        nargs="?",
                        const=True,
                        default=True,
                        type=str2bool,
                        help="Enable or disable Error messages during GPTH Processing. (default: True).")

    PARSER.add_argument("-gpthNoLog", "--gpth-no-log", action="store_true",
                        help="Skip saving GPTH log messages into output folder.")

    # FEATURES FOR SYNOLOGY/IMMICH PHOTOS:
    # -----------------------------------
    PARSER.add_argument("-uAlb", "--upload-albums", metavar="<ALBUMS_FOLDER>", default="",
                        help="Upload albums from <ALBUMS_FOLDER>. One album per subfolder.\n"
                             "You must provide the photo client using '--client'.")

    PARSER.add_argument("-dAlb", "--download-albums", metavar="<ALBUMS_NAME>", nargs="+", default="",
                        help="Download specific albums to <OUTPUT_FOLDER> (required: -o/--output-folder).\n"
                             "You must provide the photo client using '--client'.\n"
                             "- Use 'ALL' to download ALL albums.\n"
                             "- Use patterns: e.g. --download-albums 'dron*'\n"
                             "- Multiple albums can be separated by comma or space and quoted.")

    PARSER.add_argument("-uAll", "--upload-all", metavar="<INPUT_FOLDER>", default="",
                        help="Upload all assets from <INPUT_FOLDER> to the selected client.\n"
                             "You must provide the photo client using '--client'.\n"
                             "- A new Album will be created per subfolder found in 'Albums' subfolder.\n"
                             "- If '-AlbFolder, --albums-folders <ALBUMS_FOLDER>' is also passed, it will create albums for those folders too.")

    PARSER.add_argument("-dAll", "--download-all", metavar="<OUTPUT_FOLDER>", default="",
                        help="Download all albums and all non-album assets into <OUTPUT_FOLDER>.\n"
                             "You must provide the photo client using '--client'.\n"
                             "- Albums are downloaded under <OUTPUT_FOLDER>/Albums/<AlbumName> (flattened).\n"
                             "- Non-album assets go into <OUTPUT_FOLDER>/<NO_ALBUMS_FOLDER>/ with year/month structure.")

    PARSER.add_argument("-renAlb", "--rename-albums",
                        metavar="<ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>",
                        nargs="+", default="",
                        help="CAUTION!!! Rename albums matching a pattern using replacement pattern.\n"
                             "Requires '--client'.")

    PARSER.add_argument("-rAlb", "--remove-albums", metavar="<ALBUMS_NAME_PATTERN>", default="",
                        help="CAUTION!!! Remove albums matching pattern.\n"
                             "Requires '--client'.\n"
                             "Optionally also remove assets inside albums using '-rAlbAsset, --remove-albums-assets'.")

    PARSER.add_argument("-rAllAlb", "--remove-all-albums", action="store_true", default="",
                        help="CAUTION!!! Remove ALL albums.\n"
                             "Requires '--client'.\n"
                             "Optionally also remove assets inside albums using '-rAlbAsset, --remove-albums-assets'.")

    PARSER.add_argument("-rAll", "--remove-all-assets", action="store_true", default="",
                        help="CAUTION!!! Remove ALL assets (photos/videos) and ALL albums.\n"
                             "Requires '--client'.")

    PARSER.add_argument("-rEmpAlb", "--remove-empty-albums", action="store_true", default="",
                        help="Remove empty albums.\n"
                             "Requires '--client'.")

    PARSER.add_argument("-rDupAlb", "--remove-duplicates-albums", action="store_true", default="",
                        help="Remove duplicated albums (same name and size).\n"
                             "Requires '--client'.")

    PARSER.add_argument("-mDupAlb", "--merge-duplicates-albums", action="store_true", default="",
                        help="Merge duplicated albums (same name): move assets into the most relevant album and remove duplicates.\n"
                             "Requires '--client'.")

    PARSER.add_argument("-rOrphan", "--remove-orphan-assets", action="store_true", default="",
                        help="Remove orphan assets.\n"
                             "Requires '--client'. IMPORTANT: requires a valid ADMIN_API_KEY in Config.ini.")

    PARSER.add_argument("-OTP", "--one-time-password", action="store_true", default="",
                        help="Allow login into Synology Photos using 2FA with an OTP token.")

    # OTHERS STAND-ALONE FEATURES:
    # ---------------------------
    PARSER.add_argument("-fixSym", "--fix-symlinks-broken", metavar="<FOLDER_TO_FIX>", default="",
                        help="Try to fix broken symbolic links for albums in <FOLDER_TO_FIX>.\n"
                             "Useful if you moved folders inside OUTPUT_TAKEOUT_FOLDER and some albums appear empty.")

    PARSER.add_argument("-renFldcb", "--rename-folders-content-based", metavar="<ALBUMS_FOLDER>", default="",
                        help="Rename and homogenize all album folders found in <ALBUMS_FOLDER> based on content dates.")

    PARSER.add_argument("-findDup", "--find-duplicates",
                        metavar=f"<ACTION> <DUPLICATES_FOLDER> [<DUPLICATES_FOLDER> ...]",
                        nargs="+", default=["list", ""],
                        help="Find duplicates in specified folders.\n"
                             "<ACTION> defines the action to take on duplicates ('move', 'delete' or 'list'). Default: 'list'\n"
                             "<DUPLICATES_FOLDER> are one or more folders where duplicates will be searched. "
                             "The order matters: the first folder has higher priority as the 'principal' file.")

    PARSER.add_argument("-procDup", "--process-duplicates", metavar="<DUPLICATES_REVISED_CSV>", default="",
                        help="Process a revised duplicates CSV (Action column) and execute actions per duplicate set. "
                             "Valid actions: restore_duplicate / remove_duplicate / replace_duplicate.")

    # Parse args and create a global-like ARGS dict (with '-' keys)
    args = PARSER.parse_args()
    ARGS = create_global_variable_from_args(args)

    return ARGS, PARSER


def str2bool(v):
    """
    Convert various string representations into bool.
    If value is None (flag provided without explicit value), returns True.

    Accepted True values: yes, y, true, on, 1
    Accepted False values: no, n, false, off, 0
    """
    if v is None:
        # When user writes "--flag" with no value
        return True

    v_low = v.lower()
    if v_low in ('yes', 'y', 'true', 'on', '1'):
        return True
    if v_low in ('no', 'n', 'false', 'off', '0'):
        return False

    raise argparse.ArgumentTypeError(f"Expected boolean value, received '{v}'!")


def validate_account_id(valor):
    """
    Validate account ID as integer in [1,2,3].
    """
    try:
        valor_int = int(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"The value '{valor}' is not a valid number.")
    if valor_int not in [1, 2, 3]:
        raise argparse.ArgumentTypeError("The account-id must be one of the following values: 1, 2 or 3.")
    return valor_int


def validate_client(valor):
    """
    Validate the photo client selection.
    """
    valid_clients = ['google-takeout', 'synology', 'immich']
    try:
        valor_lower = valor.lower()
    except Exception:
        raise argparse.ArgumentTypeError(f"The value '{valor}' is not a valid string.")
    if valor_lower not in valid_clients:
        raise argparse.ArgumentTypeError(f"The client must be one of the following values: {valid_clients}")
    return valor_lower


def validate_client_arg(ARGS, PARSER):
    """
    Validates that Synology/Immich feature flags are not used with client='google-takeout'.

    Note:
        Your parser defaults client to 'google-takeout'. This validation effectively forces
        the user to override '--client' to 'synology' or 'immich' when any of these flags are used.
    """
    # Flags that require a Synology/Immich client
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

    # Iterate through all flags requiring client
    for flag in client_required_flags:
        if ARGS.get(flag):
            if ARGS.get('client') == 'google-takeout':
                PARSER.error(
                    f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
                    f"The flag '--{flag}' requires that '--client' is also specified "
                    f"(synology or immich).\n{Style.RESET_ALL}"
                )
                exit(1)


def checkArgs(ARGS, PARSER):
    """
    Post-parse validation and normalization for ARGS.

    - Derives google-takeout from input-folder if needed
    - Normalizes folder paths (trailing slash removal, quotes)
    - Resolves container/host external paths using resolve_external_path
    - Validates Automatic Migration syntax and related modifiers
    - Parses special list-like arguments and validates combos
    - Parses/normalizes filters (dates and types)
    """
    # Assign ARGS['google-takeout'] = ARGS['input-folder'] if --input-folder is provided and --google-takeout is not
    if ARGS['input-folder'] != '' and ARGS['google-takeout'] == '':
        ARGS['google-takeout'] = ARGS['input-folder']

    # Remove last slash for all folder arguments:
    ARGS['foldername-albums']               = fix_path(ARGS['foldername-albums'])
    ARGS['foldername-no-albums']            = fix_path(ARGS['foldername-no-albums'])
    ARGS['foldername-logs']                 = fix_path(ARGS['foldername-logs'])
    ARGS['foldername-duplicates-output']    = fix_path(ARGS['foldername-duplicates-output'])
    ARGS['foldername-extracted-dates']      = fix_path(ARGS['foldername-extracted-dates'])
    ARGS['input-folder']                    = fix_path(ARGS['input-folder'])
    ARGS['output-folder']                   = fix_path(ARGS['output-folder'])
    ARGS['google-takeout']                  = fix_path(ARGS['google-takeout'])
    ARGS['upload-albums']                   = fix_path(ARGS['upload-albums'])
    ARGS['upload-all']                      = fix_path(ARGS['upload-all'])
    ARGS['download-all']                    = fix_path(ARGS['download-all'])
    ARGS['fix-symlinks-broken']             = fix_path(ARGS['fix-symlinks-broken'])
    ARGS['rename-folders-content-based']    = fix_path(ARGS['rename-folders-content-based'])

    # Resolve paths (docker vs normal instance). Only for selected keys.
    keys_to_check = [
        'source',
        'target',
        'input-folder',
        'output-folder',
        'albums-folders',  # FIX: was 'albums-folder' (typo) and it prevented resolving this argument
        'google-takeout',
        'upload-albums',
        'upload-all',
        'download-all',
        'find-duplicates',
        'fix-symlinks-broken',
        'rename-folders-content-based',
        'configuration-file',
        'exec-gpth-tool',
        'exec-exif-tool',
        'foldername-extracted-dates',
        'foldername-duplicates-output',
        # 'foldername-albums',      # Not included because it depends on <OUTPUT_FOLDER>
        # 'foldername-no-albums',   # Not included because it depends on <OUTPUT_FOLDER>
        'foldername-logs',
    ]
    resolve_all_possible_paths(args_dict=ARGS, keys_to_check=keys_to_check)

    # Remove '_' at the beginning of the string in case it has it.
    ARGS['google-output-folder-suffix'] = ARGS['google-output-folder-suffix'].lstrip('_')

    # Set None for google-input-zip-folder (will be set only if unzip is needed)
    ARGS['google-input-zip-folder'] = None

    # Set None for MIGRATION argument (will be set only if both source and target are provided)
    ARGS['AUTOMATIC-MIGRATION'] = None

    # Parse AUTOMATIC-MIGRATION arguments
    # Manual validation of --source and --target to allow predefined values AND local folders.
    if ARGS['source'] and not ARGS['target']:
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Invalid syntax. Argument '--source' detected but not '--target' provided'. "
            f"You must specify both --source and --target to execute AUTOMATIC-MIGRATION.\n{Style.RESET_ALL}"
        )
        exit(1)

    if ARGS['target'] and not ARGS['source']:
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Invalid syntax. Argument '--target' detected but not '--source' provided'. "
            f"You must specify both --source and --target to execute AUTOMATIC-MIGRATION.\n{Style.RESET_ALL}"
        )
        exit(1)

    if ARGS['source'] and ARGS['source'] not in choices_for_AUTOMATIC_MIGRATION_SRC and not os.path.isdir(ARGS['source']):
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Invalid choice detected for --source='{ARGS['source']}'.\n"
            f"Must be an existing local folder or one of the following values:\n"
            f"{choices_for_AUTOMATIC_MIGRATION_SRC}.\n{Style.RESET_ALL}"
        )
        exit(1)

    if ARGS['target'] and ARGS['target'] not in choices_for_AUTOMATIC_MIGRATION_TGT and not os.path.isdir(ARGS['target']):
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Invalid choice detected for --target='{ARGS['target']}'.\n"
            f"Must be an existing local folder or one of the following values:\n"
            f"{choices_for_AUTOMATIC_MIGRATION_TGT}.\n{Style.RESET_ALL}"
        )
        exit(1)

    if ARGS['source'] and ARGS['target']:
        ARGS['AUTOMATIC-MIGRATION'] = [ARGS['source'], ARGS['target']]

    # Check if --dashboard was provided but source/target are missing
    dashboard_provided = any(
        re.match(r"^-{1,2}dashboard(?:$|=)", tok)
        for tok in sys.argv[1:]
    )
    if dashboard_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Argument '--dashboard' can only be used with Automatic Migration. "
            f"Arguments --source and --target are required.\n{Style.RESET_ALL}"
        )
        exit(1)

    # Check if --parallel-migration was provided but source/target are missing
    parallel_provided = any(
        re.match(r"^-{1,2}parallel(?:$|=)", tok)
        for tok in sys.argv[1:]
    )
    if parallel_provided and not (ARGS['source'] or ARGS['target']):
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"Argument '--parallel-migration' can only be used with Automatic Migration. "
            f"Arguments --source and --target are required.\n{Style.RESET_ALL}"
        )
        exit(1)

    # download-albums requires output-folder
    if ARGS['download-albums'] != "" and ARGS['output-folder'] == "":
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"When using -dAlb/--download-albums, you must provide an output folder using "
            f"-o/--output-folder <OUTPUT_FOLDER>.\n{Style.RESET_ALL}"
        )
        exit(1)

    # Parse albums-folders: ensure list
    ARGS['albums-folders'] = parse_folders_list(ARGS['albums-folders'])

    # Parse find-duplicates: extract action + folders
    ARGS['duplicates-folders'] = []
    ARGS['duplicates-action'] = ""
    for subarg in ARGS['find-duplicates']:
        if isinstance(subarg, str) and subarg.lower() in choices_for_remove_duplicates:
            ARGS['duplicates-action'] = subarg
        else:
            if subarg != "":
                ARGS['duplicates-folders'].append(subarg)

    if ARGS['duplicates-action'] == "" and ARGS['duplicates-folders'] != []:
        ARGS['duplicates-action'] = 'list'  # default value
        GV.DEFAULT_DUPLICATES_ACTION = True

    ARGS['duplicates-folders'] = parse_folders_list(ARGS['duplicates-folders'])

    # Parse rename-albums (must have exactly 2 args)
    if ARGS['rename-albums']:
        if len(ARGS['rename-albums']) != 2:
            PARSER.error(
                f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
                f"--rename-albums requires two arguments <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>.\n{Style.RESET_ALL}"
            )
            exit(1)
        for subarg in ARGS['rename-albums']:
            if subarg is None:
                PARSER.error(
                    f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
                    f"--rename-albums requires two arguments <ALBUMS_NAME_PATTERN>, <ALBUMS_NAME_REPLACEMENT_PATTERN>.\n{Style.RESET_ALL}"
                )
                exit(1)

    # remove-albums-assets must be used together with remove-all-albums or remove-albums
    if ARGS['remove-albums-assets'] and not (ARGS['remove-all-albums'] or ARGS['remove-albums']):
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"--remove-albums-assets is a modifier flag. It must be used together with one of:\n"
            f"--remove-all-albums\n"
            f"--remove-albums\n"
            f"{Style.RESET_ALL}"
        )
        exit(1)

    # Parse dates: return ISO8601 if valid, otherwise empty string
    ARGS['filter-from-date'] = parse_text_to_iso8601(ARGS.get('filter-from-date', ''))
    ARGS['filter-to-date'] = parse_text_to_iso8601(ARGS.get('filter-to-date', ''))

    # Parse filter-by-type
    if ARGS['filter-by-type'] and ARGS['filter-by-type'].lower() not in valid_asset_types:
        PARSER.error(
            f"\n\n❌ {GV.MSG_TAGS_COLORED['ERROR']}"
            f"--filter-by-type flag is invalid. Valid values are:\n{valid_asset_types}{Style.RESET_ALL}"
        )
        exit(1)

    # Validate client for Synology/Immich feature flags
    validate_client_arg(ARGS, PARSER)

    return ARGS


def parse_folders_list(folders):
    """
    Normalize folders input into a flat list of folder strings.

    Supports:
      - string: splits by commas/spaces
      - list: flattens one level and strips trailing commas
    """
    # If "folders" is a string, split by commas/spaces
    if isinstance(folders, str):
        return folders.replace(',', ' ').split()

    # If "folders" is a list, flatten one level
    if isinstance(folders, list):
        flattened = []
        for item in folders:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                # remove trailing comma if present
                flattened.append(item.rstrip(',') if isinstance(item, str) else item)
        return flattened

    # Otherwise return empty list
    return []


def create_global_variable_from_args(args):
    """
    Create a dict ARGS containing all parser arguments from the Namespace.

    Keys use '-' instead of '_' so you can access them like:
      ARGS['input-folder'] instead of args.input_folder

    Args:
        args (argparse.Namespace): Parsed arguments.

    Returns:
        dict: Normalized ARGS dict.
    """
    ARGS = {arg_name.replace("_", "-"): arg_value for arg_name, arg_value in vars(args).items()}
    return ARGS


def fix_path(path: str) -> str:
    """
    Clean a path string:
      - Remove wrapping quotes (if properly closed)
      - Remove a dangling trailing quote (escaped final quote case)
      - Remove trailing slash/backslash (except for root paths like "C:\\")

    Args:
        path (str): Raw path string.

    Returns:
        str: Cleaned path.
    """
    path = path.strip()

    # Special case: dangling ending quote
    if path.endswith('"') and not path.startswith('"'):
        path = path.rstrip('"')

    # Remove outer quotes if properly wrapped
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]

    # Remove trailing slash if not a root path (e.g. "C:\")
    if len(path) > 3 and path[-1] in ('\\', '/'):
        path = path[:-1]

    return path


def clean_path(raw: str) -> str:
    """
    Normalize a CLI path argument:
      - Strip whitespace and quotes
      - Remove trailing slash unless it's root

    Args:
        raw (str): Raw string from CLI.

    Returns:
        str: Clean path string.
    """
    if raw == '':
        return raw

    raw = raw.strip().strip("\"'")
    clean = str(PurePath(raw).with_name(PurePath(raw).name))  # removes trailing slash unless root
    return clean


def resolve_all_possible_paths(args_dict, keys_to_check=None):
    """
    Resolve all path-like values in args_dict (strings, lists, comma-separated strings),
    skipping values in known predefined choice lists or invalid types.

    Optional:
        Restrict resolution to specific keys via `keys_to_check`.

    Notes:
        - Modifies args_dict in-place
        - Uses resolve_external_path() for path normalization (docker/host aware)

    Args:
        args_dict (dict): Arguments dict to mutate.
        keys_to_check (list[str] | None): Optional subset of keys to process.
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
            continue  # skip keys not selected

        # Skip clearly invalid values
        if value is None or isinstance(value, (bool, int, float)) or value == "":
            continue

        # If list of values
        if isinstance(value, list):
            resolved_list = []
            for item in value:
                if isinstance(item, str):
                    item_clean = item.strip()
                    if item_clean == "" or item_clean in skip_values:
                        resolved_list.append(item_clean)
                    else:
                        resolved_list.append(resolve_external_path(item_clean))
                else:
                    resolved_list.append(item)
            args_dict[key] = resolved_list

        # If string (simple or comma-separated)
        elif isinstance(value, str):
            if value.strip() == "":
                continue  # do not touch empty string

            parts = [part.strip() for part in value.split(',')]
            resolved_parts = []
            for part in parts:
                if part in skip_values:
                    resolved_parts.append(part)
                else:
                    resolved_parts.append(resolve_external_path(part))

            args_dict[key] = ', '.join(resolved_parts) if ',' in value else resolved_parts[0]
