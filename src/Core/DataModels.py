#####################################
# FUNCTIONS TO INITIALIZE DATA MODELS
#####################################
# Initialize Dataclass to return by process() within ClassTakeoutFolder Class
def init_process_results ():
    return {
            'input_counters': init_count_files_counters(),
            'output_counters': init_count_files_counters(),
            'valid_albums_found': 0,
            'symlink_fixed': 0,
            'symlink_not_fixed': 0,
            'duplicates_found': 0,
            'removed_empty_folders': 0,
            'renamed_album_folders': 0,
            'duplicates_album_folders': 0,
            'duplicates_albums_fully_merged': 0,
            'duplicates_albums_not_fully_merged': 0,
            'fix_truncations': init_fix_truncations_counters(),
        }

# Initialize Dataclass to return by count_files_per_type()
def init_count_files_counters ():
    return {
        'total_files': 0,
        'total_symlinks': 0,
        'total_size_mb': 0,
        'unsupported_files': 0,
        'supported_files': 0,
        'supported_symlinks': 0,
        'media_files': 0,
        'media_symlinks': 0,
        'photo_files': 0,
        'photo_symlinks': 0,
        'video_files': 0,
        'video_symlinks': 0,
        'non_media_files': 0,
        'metadata_files': 0,
        'sidecar_files': 0,
        'photos': {
            'total': 0,
            'symlinks': 0,
            'with_date': 0,
            'without_date': 0,
            'pct_with_date': 100,
            'pct_without_date': 100,
        },
        'videos': {
            'total': 0,
            'symlinks': 0,
            'with_date': 0,
            'without_date': 0,
            'pct_with_date': 100,
            'pct_without_date': 100,
        }
    }

# Initialize Dataclass to return by fix_truncations()
def init_fix_truncations_counters ():
    return {
        "total_files": 0,
        "total_files_fixed": 0,
        "json_files_fixed": 0,
        "non_json_files_fixed": 0,
        "supplemental_metadata_fixed": 0,
        "extensions_fixed": 0,
        "special_suffixes_fixed": 0,
        "edited_suffixes_fixed": 0,
    }
