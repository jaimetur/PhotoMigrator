#####################################
# FUNCTIONS TO INITIALIZE DATA MODELS
#####################################

# Initialize Dataclass to return by count_files_per_type()
def init_count_files_counters ():
    return {
        'total_files': 0,
        'unsupported_files': 0,
        'supported_files': 0,
        'media_files': 0,
        'photo_files': 0,
        'video_files': 0,
        'non_media_files': 0,
        'metadata_files': 0,
        'sidecar_files': 0,
        'photos': {
            'total': 0,
            'with_date': 0,
            'without_date': 0,
            'pct_with_date': 100,
            'pct_without_date': 100,
        },
        'videos': {
            'total': 0,
            'with_date': 0,
            'without_date': 0,
            'pct_with_date': 100,
            'pct_without_date': 100,
        }
    }

# Initialize Dataclass to return by process() eithin ClassTakeoutFolder Class
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
        }