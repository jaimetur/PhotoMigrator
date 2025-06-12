# Simple Processing Pipeline for Google Photos Takeout Helper (GPTH)

This pipeline executes the 8 processing steps in their fixed order:
1. Fix Extensions - Correct mismatched file extensions - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/01_GPTH_fix_incorrect_file_extension.md)
2. Discover Media - Find and classify all media files - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/02_GPTH_discover_and_clasify_media_files.md)
3. Remove Duplicates - Eliminate duplicate files - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/03_GPTH_remove_duplicates_media_files.md)
4. Extract Dates - Determine accurate timestamps - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/04_GPTH_extract_dates_from_media_files.md)
5. Write EXIF - Embed metadata into files - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/05_GPTG_write_EXIF_data.md)
6. Find Albums - Merge album relationships - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/06_GPTH_find_and_merge_album_relationships.md)
7. Move Files - Organize files to output structure - [doc](https://github.com/jaimetur/PhotoMigrator/blob/main/help/gpth_process_explanations/07_GPTH_move_files_to_output_folder.md)
8. Update Creation Time - Sync timestamps (Windows only) - [doc]()

Each step checks configuration flags to determine if it should run.  

This eliminates the need for complex builder patterns while maintaining full flexibility through configuration.