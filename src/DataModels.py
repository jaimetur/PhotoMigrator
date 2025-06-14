from dataclasses import dataclass, field
from typing import List

@dataclass
class ProcessingResult:
    initial_takeout_numfiles:                       int = 0
    initial_takeout_total_images:                   int = 0
    initial_takeout_total_videos:                   int = 0
    initial_takeout_total_sidecars:                 int = 0
    initial_takeout_total_metadatas:                int = 0
    initial_takeout_total_supported_files:          int = 0
    initial_takeout_total_not_supported_files:      int = 0
    valid_albums_found:                             int = 0
    symlink_fixed:                                  int = 0
    symlink_not_fixed:                              int = 0
    duplicates_found:                               int = 0
    removed_empty_folders:                          int = 0
    renamed_album_folders:                          int = 0
    duplicates_album_folders:                       int = 0
    duplicates_albums_fully_merged:                 int = 0
    duplicates_albums_not_fully_merged:             int = 0


@dataclass
class RenameAlbumResult:
    renamed_album_folders:                          int = 0
    duplicates_album_folders:                       int = 0
    duplicates_albums_fully_merged:                 int = 0
    duplicates_albums_not_fully_merged:             int = 0


@dataclass
class FixSpecialSuffixes:
    total_files:                                    int = 0
    counter_json_files_changed:                     int = 0
    counter_non_json_files_changed:                 int = 0
    counter_supplemental_metadata_changes:          int = 0
    counter_special_suffixes_changes:               int = 0


