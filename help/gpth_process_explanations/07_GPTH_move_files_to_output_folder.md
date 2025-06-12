Step 7: Move files to output directory

This critical final step organizes and relocates all processed media files from the
Google Photos Takeout structure to the user's desired output organization. It applies
all configuration choices including album behavior, date organization, and file operation modes.

## File Organization Strategies

### Album Behavior Modes

#### Shortcut Mode (Recommended)
- **Primary Location**: Creates `ALL_PHOTOS` with all files organized by date
- **Album Organization**: Creates album folders with shortcuts/symlinks to primary files
- **Advantages**: Space efficient, maintains chronological and album organization
- **File Operations**: Moves primary files, creates links for album references
- **Compatibility**: Works on Windows (shortcuts), macOS/Linux (symlinks)

#### Duplicate-Copy Mode
- **Primary Location**: Creates `ALL_PHOTOS` with chronologically organized files
- **Album Organization**: Creates album folders with actual file copies
- **Advantages**: Universal compatibility, album folders contain real files
- **File Operations**: Moves primary files, copies files to album folders
- **Disk Usage**: Higher due to file duplication across albums

#### Reverse Shortcut Mode
- **Primary Location**: Files remain in their album folders
- **Unified Access**: Creates `ALL_PHOTOS` with shortcuts to album files
- **Advantages**: Preserves album-centric organization
- **File Operations**: Moves files to album folders, creates shortcuts in ALL_PHOTOS
- **Use Case**: When album organization is more important than chronological

#### JSON Mode
- **Primary Location**: Creates `ALL_PHOTOS` with all files organized by date
- **Album Information**: Creates `albums-info.json` with metadata mapping
- **Advantages**: Most space efficient, programmatically accessible album data
- **File Operations**: Only moves files to ALL_PHOTOS, no album folders created
- **Use Case**: For developers or users with custom photo management software

#### Nothing Mode
- **Primary Location**: Creates only `ALL_PHOTOS` with chronological organization
- **Album Information**: Completely discarded for simplest possible structure
- **Advantages**: Fastest processing, simplest result, maximum compatibility
- **File Operations**: Moves files to date-organized folders only
- **Use Case**: Users who don't care about album information

### Date-Based Organization

#### Date Division Levels
- **Level 0**: Single `ALL_PHOTOS` folder (no date division)
- **Level 1**: Year folders (`2023`, `2024`, etc.)
- **Level 2**: Year/Month folders (`2023/01_January`, `2023/02_February`)
- **Level 3**: Year/Month/Day folders (`2023/01_January/01`, `2023/01_January/02`)

#### Date Handling Logic
- **Accurate Dates**: Files with reliable date metadata are organized precisely
- **Approximate Dates**: Files with lower accuracy are grouped appropriately
- **Unknown Dates**: Files without date information go to special folders
- **Date Conflicts**: Uses date accuracy to resolve conflicts between sources

## File Operation Modes

### Copy Mode
- **Operation**: Creates copies of files in output location
- **Source Preservation**: Original takeout structure remains intact
- **Disk Usage**: Requires double the space during processing
- **Safety**: Safest option as original files are preserved
- **Use Case**: When original takeout should be kept as backup

### Move Mode (Default)
- **Operation**: Moves files from source to destination
- **Source Modification**: Original takeout structure is modified
- **Disk Usage**: No additional space required beyond final organization
- **Performance**: Faster than copy mode for large collections
- **Use Case**: When original takeout can be safely modified

## Advanced Features

### Filename Sanitization
- **Special Characters**: Removes/replaces characters incompatible with file systems
- **Unicode Handling**: Properly handles international characters and emoji
- **Length Limits**: Ensures filenames don't exceed system limits
- **Collision Prevention**: Automatically handles filename conflicts

### Path Generation
- **Cross-Platform Compatibility**: Generates paths compatible with target OS
- **Deep Directory Support**: Handles nested folder structures efficiently
- **Name Cleaning**: Sanitizes album and folder names for file system compatibility
- **Duplicate Prevention**: Ensures unique paths for all files

### Progress Tracking
- **Real-Time Updates**: Reports progress during file operations
- **Performance Metrics**: Tracks files per second and estimated completion
- **Error Reporting**: Provides detailed information about any issues
- **Batch Processing**: Efficiently handles large photo collections

## Error Handling and Recovery

### File System Issues
- **Permission Errors**: Gracefully handles access-denied situations
- **Disk Space**: Monitors available space and warns before running out
- **Path Length Limits**: Automatically shortens paths that exceed OS limits
- **Network Storage**: Handles timeouts and connection issues for network drives

### Data Integrity Protection
- **Verification**: Optionally verifies file integrity after move/copy operations
- **Rollback Capability**: Can undo operations if critical errors occur
- **Atomic Operations**: Ensures partial failures don't leave inconsistent state
- **Backup Creation**: Can create backups before destructive operations

### Conflict Resolution
- **Filename Conflicts**: Automatically renames conflicting files
- **Metadata Preservation**: Maintains file timestamps and attributes
- **Link Creation**: Handles symlink/shortcut creation failures gracefully
- **Album Association**: Maintains proper album relationships even with conflicts

## Configuration Integration

### User Preferences
- **Album Behavior**: Applies user's chosen album organization strategy
- **Date Organization**: Uses selected date division level
- **File Operations**: Respects copy vs. move preference
- **Verbose Output**: Provides detailed progress when requested

### System Adaptation
- **OS Detection**: Adapts link creation to target operating system
- **File System**: Handles different file system capabilities and limitations
- **Performance Tuning**: Adjusts batch sizes based on system performance
- **Memory Management**: Manages memory usage for large file operations

## Quality Assurance

### Validation
- **File Count Verification**: Ensures all files are properly moved/copied
- **Metadata Preservation**: Verifies file timestamps and attributes are maintained
- **Link Integrity**: Validates that created shortcuts/symlinks work correctly
- **Album Completeness**: Confirms all album relationships are preserved

### Statistics Collection
- **Processing Metrics**: Tracks files processed, time taken, errors encountered
- **Organization Results**: Reports folder structure created and file distribution
- **Space Usage**: Calculates disk space used by final organization
- **Performance Data**: Provides insights for future processing optimizations