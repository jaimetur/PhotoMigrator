Step 2: Discover and classify media files

This comprehensive step handles the discovery and initial classification of all media files
in the Google Photos Takeout structure. It processes both year-based organization and
album folders to build a complete inventory of media files.

## Discovery Process

### Year Folder Processing
- Scans "Photos from YYYY" directories for chronologically organized media
- Extracts individual media files (photos, videos) from these primary folders
- Handles various year folder naming patterns and international characters
- Processes nested directory structures within year folders

### Album Folder Processing
- Identifies album directories that exist separately from year folders
- Creates media entries for album-specific files that may not exist in year folders
- Handles duplicate relationships between year and album folder files
- Preserves album metadata and relationship information for later processing

### Media Classification
- Distinguishes between photos, videos, and other media types
- Identifies associated JSON metadata files for each media file
- Handles special file types like Live Photos, Motion Photos, and edited versions
- Filters out non-media files and system artifacts

## Processing Logic

### Comprehensive File Discovery
The step performs a deep scan of the input directory structure to identify:
- All valid media files (photos, videos) with supported extensions
- Associated JSON metadata files containing Google Photos metadata
- Album folder structures and their contained media files
- Relationship mapping between files in different locations

### Duplicate Detection Setup
During discovery, the step identifies potential duplicate relationships:
- Files that appear in both year folders and album folders
- Multiple copies of the same file across different album locations
- Sets up the foundation for later duplicate resolution processing

### Media Object Creation
For each discovered media file, creates appropriate Media objects:
- Associates files with their album context (if applicable)
- Links JSON metadata files with their corresponding media files
- Preserves original file paths for later processing steps
- Maintains album relationship information for organization

## Configuration Handling

### Input Validation
- Validates that the input directory exists and is accessible
- Ensures the directory structure matches expected Google Photos Takeout format
- Handles various Takeout export formats and structures
- Provides meaningful error messages for invalid input structures

### Progress Reporting
- Reports discovery progress for large photo collections
- Provides detailed statistics about discovered media counts
- Shows breakdown of files found in year folders vs. album folders
- Estimates processing time based on collection size

## Error Handling

### Access and Permission Issues
- Gracefully handles files with restricted access permissions
- Skips corrupted or inaccessible files without stopping processing
- Reports permission issues for user awareness
- Continues processing when individual files cannot be accessed

### Malformed Export Handling
- Detects and handles incomplete or corrupted Google Photos exports
- Adapts to various export formats and edge cases
- Provides fallback strategies for unusual directory structures
- Reports structural issues found in the export

## Integration with Other Steps

### Media Collection Population
- Populates the MediaCollection with all discovered media files
- Provides the foundation for all subsequent processing steps
- Ensures comprehensive coverage of all media in the export
- Sets up proper data structures for efficient processing

### Album Relationship Setup
- Establishes the groundwork for album finding and merging
- Preserves album context information for later processing
- Creates the data structures needed for album organization options
- Enables proper handling of files that exist in multiple albums