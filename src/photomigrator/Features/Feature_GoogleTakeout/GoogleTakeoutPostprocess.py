import fnmatch
import json
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ExifTags

from photomigrator.Core import GlobalVariables as GV, Utils
from photomigrator.Core.CustomLogger import set_log_level
from photomigrator.Core.DataModels import init_count_files_counters


# ---------------------------------------------------------------------------------------------------------------------------
# GOOGLE TAKEOUT POST-PROCESSING FUNCTIONS:
# ---------------------------------------------------------------------------------------------------------------------------
def sync_mp4_timestamps_with_images(input_folder, step_name="", log_level=None):
    """
    Look for .MP4 files with the same base name as any Live Picture file (.HEIC, .JPG, .JPEG)
    in the same folder. If found, set the date and time of the .MP4 file (or the symlink itself)
    to match the original Live Picture.
    """
    # Set logging level for this operation
    with set_log_level(GV.LOGGER, log_level):
        # Count total files for progress bar
        total_files = sum(len(files) for _, _, files in os.walk(input_folder))
        with Utils.tqdm(
                total=total_files,
                smoothing=0.1,
                desc=f"{GV.TAG_INFO}{step_name}Synchronizing .MP4 files with Live Pictures in '{input_folder}'",
                unit=" files"
        ) as pbar:
            # Walk through all directories and files
            for path, _, files in os.walk(input_folder):
                # Build a mapping from base filename to its extensions
                file_dict = {}
                for filename in files:
                    pbar.update(1)
                    name, ext = os.path.splitext(filename)
                    base_name = name.lower()
                    ext = ext.lower()
                    file_dict.setdefault(base_name, {})[ext] = filename
                # For each group of files sharing the same base name
                for base_name, ext_file_map in file_dict.items():
                    if '.mp4' not in ext_file_map:
                        continue
                    mp4_filename = ext_file_map['.mp4']
                    mp4_file_path = os.path.join(path, mp4_filename)
                    # Detect if the .mp4 is a symlink
                    is_mp4_link = os.path.islink(mp4_file_path)
                    # Look for a matching Live Picture image
                    image_exts = ['.heic', '.jpg', '.jpeg']
                    for image_ext in image_exts:
                        if image_ext not in ext_file_map:
                            continue
                        image_filename = ext_file_map[image_ext]
                        image_file_path = os.path.join(path, image_filename)
                        try:
                            # Get the image's atime and mtime
                            image_stats = os.stat(image_file_path)
                            atime, mtime = image_stats.st_atime, image_stats.st_mtime
                            if is_mp4_link:
                                # Apply timestamps to the symlink itself
                                os.utime(mp4_file_path, (atime, mtime), follow_symlinks=False)
                                GV.LOGGER.debug(f"{step_name}Timestamps applied to symlink: {os.path.relpath(mp4_file_path, input_folder)}")
                            else:
                                # Apply timestamps to the regular .mp4 file
                                os.utime(mp4_file_path, (atime, mtime))
                                GV.LOGGER.debug(f"{step_name}Timestamps applied to file: {os.path.relpath(mp4_file_path, input_folder)}")
                        except FileNotFoundError:
                            # Warn if either the .mp4 or the image file is missing
                            GV.LOGGER.warning(f"{step_name}File not found. MP4: {mp4_file_path} | Image: {image_file_path}")
                        except Exception as e:
                            # Log any other errors encountered
                            GV.LOGGER.error(f"{step_name}Error syncing {mp4_file_path}: {e}")
                        # Only sync with the first matching image
                        break


def force_remove_directory(folder, log_level=None):
    def onerror(func, path, exc_info):
        # Cambia los permisos y vuelve a intentar
        os.chmod(path, stat.S_IWRITE)
        func(path)

    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        if os.path.exists(folder):
            shutil.rmtree(folder, onerror=onerror)
            GV.LOGGER.info(f"The folder '{folder}' and all its contant have been deleted.")
        else:
            GV.LOGGER.warning(f"Cannot delete the folder '{folder}'.")


def copy_move_folder(src, dst, ignore_patterns=None, move=False, step_name="", log_level=None):
    """
    Copies or moves an entire folder, including subfolders and files, to another location,
    while ignoring files that match one or more specific patterns.

    :param src: Path to the source folder.
    :param dst: Path to the destination folder.
    :param ignore_patterns: A pattern (string) or a list of patterns to ignore (e.g., '*.json' or ['*.json', '*.txt']).
    :param move: If True, moves the files instead of copying them.
    :return: None
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        # Ignore function
        action = 'Moving' if move else 'Copying'
        try:
            if not Utils.is_valid_path(src):
                GV.LOGGER.error(f"{step_name}The path '{src}' is not valid for the execution plattform. Cannot copy/move folders from it.")
                return False
            if not Utils.is_valid_path(dst):
                GV.LOGGER.error(f"{step_name}The path '{dst}' is not valid for the execution plattform. Cannot copy/move folders to it.")
                return False

            def ignore_function(files, ignore_patterns):
                if ignore_patterns:
                    # Convert to a list if a single pattern is provided
                    patterns = ignore_patterns if isinstance(ignore_patterns, list) else [ignore_patterns]
                    ignored = []
                    for pattern in patterns:
                        ignored.extend(fnmatch.filter(files, pattern))
                    return set(ignored)
                return set()

            # Ensure the source folder exists
            if not os.path.exists(src):
                raise FileNotFoundError(f"{step_name}Source folder does not exist: '{src}'")
            # Create the destination folder if it doesn't exist
            os.makedirs(dst, exist_ok=True)

            if move:
                # Contar el total de carpetas
                total_files = sum([len(files) for _, _, files in os.walk(src)])
                # Mostrar la barra de progreso basada en carpetas
                with Utils.tqdm(total=total_files, ncols=120, smoothing=0.1, desc=f"{GV.TAG_INFO}{step_name}{action} Folders in '{src}' to Folder '{dst}'", unit=" files") as pbar:
                    for path, dirs, files in os.walk(src, topdown=True):
                        pbar.update(1)
                        # Compute relative path
                        rel_path = os.path.relpath(path, src)
                        # Destination path
                        dest_path = os.path.join(dst, rel_path) if rel_path != '.' else dst
                        # Apply ignore function to files and dirs
                        ignore = ignore_function(files + dirs, ignore_patterns=ignore_patterns)
                        # Filter dirs in-place to skip ignored directories
                        dirs[:] = [d for d in dirs if d not in ignore]
                        # Create destination directory
                        os.makedirs(dest_path, exist_ok=True)
                        # Move files
                        for file in files:
                            if file not in ignore:
                                src_file = os.path.join(path, file)
                                dst_file = os.path.join(dest_path, file)
                                shutil.move(src_file, dst_file)
                    GV.LOGGER.info(f"{step_name}Folder moved successfully from {src} to {dst}")
            else:
                # Copy the folder contents
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_function)
                GV.LOGGER.info(f"{step_name}Folder copied successfully from {src} to {dst}")
                return True
        except Exception as e:
            GV.LOGGER.error(f"{step_name}Error {action} folder: {e}")
            return False


def organize_files_by_date(input_folder, type='year', exclude_subfolders=[], step_name="", log_level=None):
    """
    Organizes files into subfolders based on their EXIF or modification date.

    Args:
        input_folder (str, Path): The base directory containing the files.
        type: 'year' to organize by year, or 'year-month' to organize by year and month.
        exclude_subfolders (str, Path or list): A list of subfolder names to exclude from processing.

    Raises:
        ValueError: If the value of `type` is invalid.
    """
    import os
    import shutil
    from datetime import datetime
    import piexif
    def get_exif_date(image_path):
        try:
            exif_dict = piexif.load(image_path)
            for tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
                tag_id = piexif.ExifIFD.__dict__.get(tag)
                value = exif_dict["Exif"].get(tag_id)
                if value:
                    return datetime.strptime(value.decode(), "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    with set_log_level(GV.LOGGER, log_level):
        if type not in ['year', 'year/month', 'year-month']:
            raise ValueError(f"{step_name}The 'type' parameter must be 'year', 'year/month' or 'year-month'.")
        total_files = 0
        for _, dirs, files in os.walk(input_folder):
            dirs[:] = [d for d in dirs if d not in exclude_subfolders]
            total_files += len(files)
        with Utils.tqdm(total=total_files, smoothing=0.1, desc=f"{GV.TAG_INFO}{step_name}Organizing files with {type} structure in '{os.path.basename(os.path.normpath(input_folder))}'", unit=" files") as pbar:
            for path, dirs, files in os.walk(input_folder, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_subfolders]
                for file in files:
                    pbar.update(1)
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                    mod_time = None
                    ext = os.path.splitext(file)[1].lower()
                    # Intentar obtener fecha EXIF si es imagen
                    if ext in GV.PHOTO_EXT:
                        try:
                            mod_time = get_exif_date(file_path)
                        except Exception as e:
                            GV.LOGGER.warning(f"{step_name}Error reading EXIF from {file_path}: {e}")
                    # Si no hay EXIF o no es imagen, usar fecha de sistema
                    if not mod_time:
                        try:
                            mtime = os.path.getmtime(file_path)
                            mod_time = datetime.fromtimestamp(mtime if mtime > 0 else 0)
                        except Exception as e:
                            GV.LOGGER.warning(f"{step_name}Error reading mtime for {file_path}: {e}")
                            mod_time = datetime(1970, 1, 1)
                    GV.LOGGER.verbose(f"{step_name}Using date {mod_time} for file {file_path}")
                    # Determinar carpeta destino
                    if type == 'year':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'))
                    elif type == 'year/month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y'), mod_time.strftime('%m'))
                    elif type == 'year-month':
                        target_dir = os.path.join(path, mod_time.strftime('%Y-%m'))
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.move(file_path, os.path.join(target_dir, file))
        GV.LOGGER.info(f"{step_name}Organization completed. Folder structure per '{type}' created in '{input_folder}'.")


def move_albums(input_folder, albums_subfolder="Albums", exclude_subfolder=None, step_name="", log_level=None):
    """
    Moves album folders to a specific subfolder, excluding the specified subfolder(s).

    Parameters:
        input_folder (str, Path): Path to the input folder containing the albums.
        albums_subfolder (str, Path): Name of the subfolder where albums should be moved.
        exclude_subfolder (str or list, optional): Subfolder(s) to exclude. Can be a single string or a list of strings.
    """
    # Ensure exclude_subfolder is a list, even if a single string is passed
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        def safe_move(folder_path, albums_path):
            destination = os.path.join(albums_path, os.path.basename(folder_path))
            if os.path.exists(destination):
                if os.path.isdir(destination):
                    shutil.rmtree(destination)
                else:
                    os.remove(destination)
            shutil.move(folder_path, albums_path)

        if isinstance(exclude_subfolder, str):
            exclude_subfolder = [exclude_subfolder]
        albums_path = os.path.join(input_folder, albums_subfolder)
        exclude_subfolder_paths = [os.path.abspath(os.path.join(input_folder, sub)) for sub in (exclude_subfolder or [])]
        subfolders = os.listdir(input_folder)
        subfolders = [subfolder for subfolder in subfolders if not subfolder == '@eaDir' and not subfolder == 'No-Albums']
        for subfolder in Utils.tqdm(subfolders, smoothing=0.1, desc=f"{GV.TAG_INFO}{step_name}Moving Albums in '{input_folder}' to Subolder '{albums_subfolder}'", unit=" albums"):
            folder_path = os.path.join(input_folder, subfolder)
            if os.path.isdir(folder_path) and subfolder != albums_subfolder and os.path.abspath(folder_path) not in exclude_subfolder_paths:
                GV.LOGGER.debug(f"{step_name}Moving to '{os.path.basename(albums_path)}' the folder: '{os.path.basename(folder_path)}'")
                os.makedirs(albums_path, exist_ok=True)
                safe_move(folder_path, albums_path)
        # Finally Move Albums to Albums root folder (removing 'Takeout' and 'Google Fotos' / 'Google Photos' folders if exists
        move_albums_to_root(albums_path, step_name=step_name, log_level=logging.INFO)


def move_albums_to_root(albums_root, step_name="", log_level=None):
    """
    Moves all albums from nested subdirectories ('Takeout/Google Fotos' or 'Takeout/Google Photos')
    directly into the 'Albums' folder, removing unnecessary intermediate folders.
    """
    with set_log_level(GV.LOGGER, log_level):  # Change Log Level to log_level for this function
        possible_google_folders = ["Google Fotos", "Google Photos"]
        takeout_path = os.path.join(albums_root, "Takeout")
        # Check if 'Takeout' exists
        if not os.path.exists(takeout_path):
            GV.LOGGER.debug(f"{step_name}'Takeout' folder not found at {takeout_path}. Exiting.")
            return
        # Find the actual Google Photos folder name
        google_photos_path = None
        for folder in possible_google_folders:
            path = os.path.join(takeout_path, folder)
            if os.path.exists(path):
                google_photos_path = path
                break
        if not google_photos_path:
            GV.LOGGER.debug(f"{step_name}No valid 'Google Fotos' or 'Google Photos' folder found inside 'Takeout'. Exiting.")
            return
        GV.LOGGER.debug(f"{step_name}Found Google Photos folder: {google_photos_path}")
        GV.LOGGER.info(f"{step_name}Moving Albums to Albums root folder...")
        # Move albums to the root 'Albums' directory
        for album in os.listdir(google_photos_path):
            album_path = os.path.join(google_photos_path, album)
            target_path = os.path.join(albums_root, album)
            if os.path.isdir(album_path):  # Ensure it's a directory (album)
                new_target_path = target_path
                count = 1
                # Handle naming conflicts by adding a suffix
                while os.path.exists(new_target_path):
                    new_target_path = f"{target_path}_{count}"
                    count += 1
                # Move the album
                shutil.move(album_path, new_target_path)
                GV.LOGGER.debug(f"{step_name}Moved: {album_path} → {new_target_path}")
        # Attempt to remove empty folders
        try:
            shutil.rmtree(takeout_path)
            GV.LOGGER.debug(f"{step_name}'Takeout' folder successfully removed.")
        except Exception as e:
            GV.LOGGER.error(f"{step_name}Failed to remove 'Takeout': {e}")


def count_valid_albums(folder_path, excluded_folders=[], step_name="", log_level=None):
    """
    Counts the number of subfolders within folder_path and its sublevels
    that contain at least one valid image or video file.

    A folder is considered valid if it contains at least one file with an extension
    defined in GV.PHOTO_EXT or GV.VIDEO_EXT.

    The following folders (and all their subfolders) are excluded from the count:
    - Any folder named 'Photos from YYYY' where YYYY starts with 1 or 2.
    - Folders named exactly as excluded_folder list.
    """
    YEAR_PATTERN = re.compile(r'^Photos from [12]\d{3}$')
    with set_log_level(GV.LOGGER, log_level):  # Change log level temporarily
        valid_albums = 0
        for root, dirs, files in os.walk(folder_path):
            folder_name = os.path.basename(root)
            # Skip current folder if it matches any exclusion rule
            if folder_name in excluded_folders or YEAR_PATTERN.fullmatch(folder_name):
                dirs.clear()  # Prevent descending into subdirectories
                continue
            # Also remove excluded subfolders from being walked into
            dirs[:] = [
                d for d in dirs
                if d not in excluded_folders and not YEAR_PATTERN.fullmatch(d)
            ]
            # Check for at least one valid image or video file
            if any(os.path.splitext(file)[1].lower() in GV.PHOTO_EXT or os.path.splitext(file)[1].lower() in GV.VIDEO_EXT for file in files):
                valid_albums += 1
        return valid_albums


def get_oldest_date(file_path, extensions, tag_ids, skip_exif=True, skip_json=True, log_level=None):
    """
    Return the earliest valid timestamp found by:
      1) Birthtime/mtime for video files (early exit if ext in GV.VIDEO_EXT)
      2) EXIF tags (if skip_exif=False and ext in extensions)
      3) JSON sidecar (<file>.json) (if skip_json=False)
      4) File birthtime and modification time via one os.stat() fallback
    Caches results per (file_path, skip_exif, skip_json) on the function.
    """
    # initialize per‐call cache
    if not hasattr(get_oldest_date, "_cache"):
        get_oldest_date._cache = {}
    cache = get_oldest_date._cache
    key = (file_path, bool(skip_exif), bool(skip_json))
    if key in cache:
        return cache[key]

    with set_log_level(GV.LOGGER, log_level):
        ext = Path(file_path).suffix.lower()

        # 1) Videos → no EXIF/JSON, just return birthtime or mtime
        if ext in GV.VIDEO_EXT:
            try:
                st = os.stat(file_path, follow_symlinks=False)
                bt = getattr(st, "st_birthtime", None)
                result = datetime.fromtimestamp(bt) if bt else datetime.fromtimestamp(st.st_mtime)
            except Exception:
                result = None
            cache[key] = result
            return result

        dates = []

        # 2) EXIF extraction for supported extensions
        if not skip_exif and ext in extensions:
            try:
                exif = Image.open(file_path).getexif()
                if len(exif) > 0:
                    for tag_id in tag_ids:
                        raw = exif.get(tag_id)
                        if isinstance(raw, str) and len(raw) >= 19:
                            # fast parse 'YYYY:MM:DD HH:MM:SS'
                            y, mo, d = int(raw[0:4]), int(raw[5:7]), int(raw[8:10])
                            hh, mm, ss = int(raw[11:13]), int(raw[14:16]), int(raw[17:19])
                            dates.append(datetime(y, mo, d, hh, mm, ss))
                            break
            except Exception:
                pass

        # 3) JSON sidecar parsing
        if not skip_json:
            js = Path(file_path).with_suffix(ext + ".json")
            if js.exists():
                try:
                    data = json.loads(js.read_text(encoding="utf-8"))
                    for name in ("photoTakenTime", "creationTime", "creationTimestamp"):
                        ts = data.get(name)
                        if isinstance(ts, dict):
                            ts = ts.get("timestamp")
                        if ts:
                            dates.append(datetime.fromtimestamp(int(ts)))
                            break
                except Exception:
                    pass

        # 4) Fallback to birthtime + mtime
        try:
            st = os.stat(file_path, follow_symlinks=False)
            bt = getattr(st, "st_birthtime", None)
            if bt is not None:
                dates.append(datetime.fromtimestamp(bt))
            dates.append(datetime.fromtimestamp(st.st_mtime))
        except Exception:
            pass

        result = min(dates) if dates else None
        cache[key] = result
        return result


def get_embedded_datetime(file_path, step_name=''):
    """
    Devuelve la fecha embebida más antigua encontrada como datetime.datetime,
    usando exiftool desde ./gpth_tool/exif_tool/. Si no hay fechas embebidas válidas, retorna None.

    Usa GV.PHOTO_EXT, GV.VIDEO_EXT y GV.LOGGER.

    Args:
        file_path (str, Literal or Path): Ruta al archivo.

    Returns:
        datetime.datetime or None
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext not in GV.PHOTO_EXT and ext not in GV.VIDEO_EXT:
        return None

    is_windows = platform.system().lower() == 'windows'
    exiftool_path = Path("gpth_tool/exif_tool/exiftool.exe" if is_windows else "gpth_tool/exif_tool/exiftool").resolve()

    if not exiftool_path.exists():
        GV.LOGGER.debug(f"{step_name}[get_embedded_datetime] exiftool not found at: {exiftool_path}")
        return None

    try:
        result = subprocess.run(
            [str(exiftool_path), '-j', '-time:all', '-s', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding='utf-8',
            check=True
        )
        metadata_list = json.loads(result.stdout)
        if not metadata_list or not isinstance(metadata_list, list) or not metadata_list[0]:
            GV.LOGGER.debug(f"{step_name}[get_embedded_datetime] No metadata returned for: {file_path.name}")
            return None

        metadata = metadata_list[0]

        candidate_tags = [
            'DateTimeOriginal',
            'CreateDate',
            'MediaCreateDate',
            'TrackCreateDate',
            'EncodedDate',
            'MetadataDate',
        ]

        available_tags = [tag for tag in candidate_tags if tag in metadata]
        if not available_tags:
            GV.LOGGER.debug(f"{step_name}[get_embedded_datetime] No embedded date tags found in metadata for: {file_path.name}")
            return None

        date_formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d",
            "%Y-%m-%d",
        ]

        found_dates = []

        for tag in available_tags:
            raw_value = metadata[tag].strip()
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(raw_value, fmt)
                    found_dates.append((tag, parsed_date))
                    break
                except ValueError:
                    continue

        if not found_dates:
            GV.LOGGER.debug(f"{step_name}[get_embedded_datetime] None of the embedded date fields could be parsed for: {file_path.name}")
            return None

        oldest = min(found_dates, key=lambda x: x[1])
        GV.LOGGER.debug(f"{step_name}[get_embedded_datetime] Selected tag '{oldest[0]}' with date {oldest[1]} for: {file_path.name}")
        return oldest[1]

    except Exception as e:
        GV.LOGGER.error(f"{step_name}[get_embedded_datetime] Error processing '{file_path}': {e}")
        return None


def get_embedded_datetimes_bulk(folder, step_name=''):
    """
    Devuelve un diccionario con la fecha embebida más antigua de cada archivo multimedia en la carpeta y subcarpetas.

    Args:
        folder (str or Path): Carpeta raíz

    Returns:
        dict[Path, datetime.datetime]: mapping de archivo → fecha más antigua encontrada
    """
    folder = Path(folder).resolve()
    step_name = f"{step_name}[get_embedded_datetimes_bulk] : "

    is_windows = platform.system().lower() == 'windows'
    exiftool_path = Path("gpth_tool/exif_tool/exiftool.exe" if is_windows else "gpth_tool/exif_tool/exiftool").resolve()
    if not exiftool_path.exists():
        GV.LOGGER.error(f"{step_name}❌ exiftool not found at: {exiftool_path}")
        return {}

    try:
        # result = subprocess.run(
        #     [str(exiftool_path), "-r", "-j", "-time:all", "-s", str(folder)],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.DEVNULL,
        #     encoding='utf-8',
        #     check=False  # <== importante
        # )
        return_code, out, err = timed_subprocess(
            [str(exiftool_path), "-r", "-j", "-time:all", "-s", str(folder)],
            step_name=step_name
        )
        if return_code != 0:
            GV.LOGGER.warning(f"{step_name}❌ exiftool return code: %d", return_code)

        # Decodifica el stdout:
        output = out.decode("utf-8")

        metadata_list = json.loads(output)
    except Exception as e:
        GV.LOGGER.error(f"{step_name}❌ Failed to run exiftool: {e}")
        return {}

    date_formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d",
        "%Y-%m-%d",
    ]

    candidate_tags = [
        'DateTimeOriginal',
        'CreateDate',
        'MediaCreateDate',
        'TrackCreateDate',
        'EncodedDate',
        'MetadataDate',
    ]

    result_dict = {}

    for entry in metadata_list:
        source_file = entry.get("SourceFile")
        if not source_file:
            continue
        file_path = Path(source_file)
        ext = file_path.suffix.lower()
        if ext not in GV.PHOTO_EXT and ext not in GV.VIDEO_EXT:
            continue

        found_dates = []
        for tag in candidate_tags:
            if tag in entry:
                raw_value = str(entry[tag]).strip()
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(raw_value, fmt)
                        found_dates.append(dt)
                        break
                    except ValueError:
                        continue

        if found_dates:
            oldest = min(found_dates)
            result_dict[file_path] = oldest
            GV.LOGGER.debug(f"{step_name}✅ {oldest} →  {file_path.name}")

    return result_dict


def timed_subprocess(cmd, step_name=""):
    """
    Ejecuta cmd con Popen, espera a que termine y registra sólo
    el tiempo total de ejecución al final.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start = time.time()
    out, err = proc.communicate()
    total = time.time() - start
    GV.LOGGER.debug(f"{step_name}✅ subprocess finished in {total:.2f}s")
    return proc.returncode, out, err


def count_files_per_type_and_date(input_folder, skip_exif=True, skip_json=True, step_name='', log_level=None):
    """
    Analyze all files in `input_folder`, counting:
      - total files
      - supported vs unsupported files based on global extension lists
      - image files vs video files vs metadata files vs sidecar files
      - media files (images + videos)
      - non-media files (metadata + sidecar)
      - for photos and videos, how many have an assigned date vs. not
      - percentage of photos/videos with and without date
    Uses global GV.PHOTO_EXT, GV.VIDEO_EXT, GV.METADATA_EXT, GV.SIDECAR_EXT, and GV.TiMESTAMP.
    """
    with set_log_level(GV.LOGGER, log_level):
        # This is used to check if files had any date before Takeout Processing started.
        timestamp_dt = datetime.strptime(GV.TiMESTAMP, "%Y%m%d-%H%M%S")

        # Initialize overall counters with pct keys for media
        counters = init_count_files_counters()

        # Inicializa contador de tamaño en bytes
        total_size_bytes = 0

        # Get total supported extensions
        supported_exts = set(GV.PHOTO_EXT + GV.VIDEO_EXT + GV.METADATA_EXT + GV.SIDECAR_EXT)

        # 1) Set de extensiones soportadas para EXIF
        MEDIA_EXT = set(ext.lower() for ext in GV.PHOTO_EXT + GV.VIDEO_EXT)

        # 2) IDs de EXIF para DateTimeOriginal, DateTimeDigitized, DateTime
        WANTED_TAG_IDS = {
            tag_id
            for tag_id, tag_name in ExifTags.TAGS.items()
            if tag_name in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime')
        }

        # Create a dictionary with all files dates using exiftool
        dates_dict = get_embedded_datetimes_bulk(folder=input_folder, step_name=step_name)

        # Walk through all subdirectories and files
        for root, dirs, files in os.walk(input_folder):
            for filename in files:
                file_path = os.path.join(root, filename)

                # Saltar enlaces simbólicos
                if os.path.islink(file_path):
                    continue  # Skip symbolic links

                # Sumar tamaño
                try:
                    total_size_bytes += os.path.getsize(file_path)
                except Exception:
                    pass

                _, ext = os.path.splitext(filename)
                ext = ext.lower()

                # Count every file
                counters['total_files'] += 1

                # Determine support status
                if ext in supported_exts:
                    counters['supported_files'] += 1
                else:
                    counters['unsupported_files'] += 1

                # Categorize by extension
                if ext in GV.PHOTO_EXT:
                    counters['photo_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'photos'
                elif ext in GV.VIDEO_EXT:
                    counters['video_files'] += 1
                    counters['media_files'] += 1
                    media_type = 'videos'
                else:
                    media_type = None

                # Count metadata and sidecar
                if ext in GV.METADATA_EXT:
                    counters['metadata_files'] += 1
                if ext in GV.SIDECAR_EXT:
                    counters['sidecar_files'] += 1
                if ext in GV.METADATA_EXT or ext in GV.SIDECAR_EXT:
                    counters['non_media_files'] += 1

                # Skip date logic for non-media
                if not media_type:
                    continue

                counters[media_type]['total'] += 1

                # file_date = get_oldest_date(file_path=file_path, skip_exif=skip_exif, skip_json=skip_json)
                # file_date = get_oldest_date(file_path=file_path, extensions=MEDIA_EXT, tag_ids=WANTED_TAG_IDS, skip_exif=skip_exif, skip_json=skip_json)
                # file_date = get_embedded_datetime(file_path=file_path)
                file_date = dates_dict.get(Path(file_path))
                has_date = file_date is not None and file_date <= timestamp_dt

                if has_date:
                    counters[media_type]['with_date'] += 1
                else:
                    counters[media_type]['without_date'] += 1

        # Calculate percentages for photos based on totals
        total_photos = counters['photos']['total']
        if total_photos > 0:
            counters['photos']['pct_with_date'] = (counters['photos']['with_date'] / total_photos) * 100
            counters['photos']['pct_without_date'] = (counters['photos']['without_date'] / total_photos) * 100

        # Calculate percentages for videos based on totals
        total_videos = counters['videos']['total']
        if total_videos > 0:
            counters['videos']['pct_with_date'] = (counters['videos']['with_date'] / total_videos) * 100
            counters['videos']['pct_without_date'] = (counters['videos']['without_date'] / total_videos) * 100

        # Añade el tamaño total en MB al resultado
        counters['total_size_mb'] = round(total_size_bytes / (1024 * 1024), 1)

        return counters
