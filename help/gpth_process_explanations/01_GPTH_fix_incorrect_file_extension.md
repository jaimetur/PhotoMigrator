# Step 1: Fix incorrect file extensions

This step identifies and fixes files where the extension doesn't match the actual MIME type, which commonly occurs when Google Photos compresses images but keeps original extensions or when web-downloaded images have incorrect extensions.

## Purpose
Google Photos Takeout often contains files with mismatched extensions:
- Images compressed to JPEG but keeping original extension (e.g., `.png`)
- HEIF files exported with `.jpeg` extension
- Web-downloaded images with generic extensions
- Files processed through various photo editing tools

## Processing Logic
1. Scans all photo/video files recursively in the input directory
2. Reads first 128 bytes of each file to determine actual MIME type
3. Compares with MIME type suggested by file extension
4. Renames files with correct extensions when mismatch detected
5. Also renames associated .json metadata files to maintain pairing
6. Provides detailed logging of all changes made

## Safety Features
- Skips TIFF-based files (RAW formats) as they're often misidentified
- Optional conservative mode skips actual JPEG files for maximum safety
- Validates target files don't already exist before renaming
- Preserves file content while only changing extension
- Maintains metadata file associations automatically

## Configuration Options
- `fixExtensions`: Standard mode, skips TIFF-based files only
- `fixExtensionsNonJpeg`: Conservative mode, also skips actual JPEG files
- `fixExtensionsSoloMode`: Runs extension fixing only, then exits

## Error Handling
- Gracefully handles filesystem permission errors
- Logs warnings for files that cannot be processed
- Continues processing other files when individual failures occur
- Provides detailed error messages for troubleshooting