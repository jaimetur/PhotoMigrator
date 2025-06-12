Simple Processing Pipeline for Google Photos Takeout Helper

This pipeline executes the 8 processing steps in their fixed order:
1. Fix Extensions - Correct mismatched file extensions
2. Discover Media - Find and classify all media files
3. Remove Duplicates - Eliminate duplicate files
4. Extract Dates - Determine accurate timestamps
5. Write EXIF - Embed metadata into files
6. Find Albums - Merge album relationships
7. Move Files - Organize files to output structure
8. Update Creation Time - Sync timestamps (Windows only)

Each step checks configuration flags to determine if it should run.
This eliminates the need for complex builder patterns while maintaining
full flexibility through configuration.