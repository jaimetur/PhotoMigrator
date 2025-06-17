####################################
# FUNCTIONS TO INITIALIZE DATA MODELS
#####################################
def create_counters():
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