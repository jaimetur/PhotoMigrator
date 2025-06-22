## 📅 ROADMAP
[Planned Roadmap](https://github.com/jaimetur/PhotoMigrator/blob/main/docs/ROADMAP.md) for the following releases
[Changelog](https://github.com/jaimetur/PhotoMigrator/blob/main/docs/CHANGELOG.md) for the past releases

---

## Release: v3.4.0  
- ### Release Date: 2025-06-30
  - Alpha version    : 2025-06-18
  - Beta version     : 2025-06-23
  - Release Candidate: 2025-06-27
  - Official Release : 2025-06-30

- ### Main Changes:
  - #### 🚨 Breaking Changes:
    - [ ] Replaced argument `-gmtf, --google-move-takeout-folder` by `-gKeepTake, --google-keep-takeout-folder` argument and inverted the logic for Google Takeout Processing.
    - [ ] Replaced argument `-gnsa, --google-create-symbolic-albums` by `-gcsa, --google-no-symbolic-albums` argument and inverted the logic for Google Takeout Processing.
    - [x] Replaced argument `-confirm, --request-user-confirmation` by `-noConfirm, --no-request-user-confirmation` and inverted logic. 
    
  - #### 🌟 New Features:
    - [x] Created GitHub Forms on New Issues.
      - [ ] Auto-Update Issues Templates with new published releases.
    - [x] Added Step duration summary at the end of `Google Takeout Processing` feature.
    - [x] Added new `VERBOSE` value for `-logLevel` argument.
    - [x] Added new argument `-logFormat, --log-format` to define the format of the Log File. Valid values: `[LOG, TXT, ALL]`.
    - [x] Call GPTH with `--verbose` when PhotoMigrator logLevel is VERBOSE or DEBUG.
    - [x] Add argument `-gSkipPrep,--google-skip-preprocess` to Skipp Preproces steps during Google Takeout Processing feature.
  
  - #### 🚀 Enhancements:
    - [x] Code totally refactored and organized per modules within Gloal and Features Subfolders.
    - [x] Reorganized Pre-checks/Pre-process/Process steps for a clearer maintainance and better visualization. 
    - [x] The Feature `Google Takeout Processing` is no longer called using the Pre-checks functions but always using the Process() function from ClassTakeoutFolder.
    - [x] Included Input/Output folder size in Google Takeout Statistics.
    - [x] Improved performance on Counting files during Google Takeout Processing.
    - [x] Improved Logging messages type detection when running GPTH.
    - [x] Improved Logging messages and screen messages prefixes using Global Variables instead of hardcoded strings.
    - [x] Inserted Profiler support to Profile any function and optimize it.
    - [x] Removed `input_folder` after successfull completion of `Google Takeout Processing` if the user used the flag `-gmtf, --google-move-takeout-folder`. Note that this only remove the `input_folder` with a valid Takeout Structure, this will not remove your original Takeout Zip folder with your Takeout Zips.
    - [x] Renamed argument `-loglevel` to `-logLevel`.
    - [x] Renamed argument `-dashb` to `-dashboard`.
    - [x] Renamed argument `-AlbFld` to `-AlbFolder`.
    - [x] Renamed argument `-rAlbAss` to `-rAlbAsset`.
    - [x] Renamed argument `-gpthErr` to `-gpthError`.
    - [x] Updated GPTH to version `4.0.9` (by @Xentraxx) which includes several improvements extracting metadata info from Google Takeouts. 
      - This release represents a fundamental restructuring of the codebase following **Clean Architecture** principles, providing better maintainability, testability, and performance.
      - ##### 🚨 **Critical Bug Fixes**
        - **CRITICAL FIX**: Nothing mode now processes ALL files, preventing data loss in move mode
        - **FIXED: Data loss in Nothing mode** - Album-only files are now properly moved in Nothing mode instead of being silently skipped, preventing potential data loss when using move mode with `--album-behavior=nothing`
      - ##### 🚀 **Improvements**
        - ##### **Performance & Reliability Improvements**
          - **Stream-based file I/O operations** replacing synchronous access
          - **Persistent ExifTool process** management (10-50x faster EXIF operations)
          - **Concurrent media processing** with race condition protection
          - **Memory optimization** - up to 99.4% reduction for large file operations
          - **Streaming hash calculations** (20% faster with reduced memory usage)
          - **Optimized directory scanning** (50% fewer I/O operations)
          - **Parallel file moving operations** (40-50% performance improvement)
          - **Smart duplicate detection** with memory-efficient algorithms
        - ##### **Domain-Driven Design Implementation**
          - **Reorganized codebase into distinct layers**: Domain, Infrastructure, and Presentation
          - **Introduced service-oriented architecture** with dependency injection container
          - **Implemented immutable domain entities** for better data integrity and performance
          - **Added comprehensive test coverage** with over 200+ unit and integration tests   
        - ##### **Service Consolidation & Modernization**
          - **Unified service interfaces** through consolidated service pattern
          - **Implemented ServiceContainer** for centralized dependency management
          - **Refactored moving logic** into strategy pattern with pluggable implementations
          - **Enhanced error handling** with proper exception hierarchies and logging
        - ##### **Intelligent Extension Correction**
          - **MIME type validation** with file header detection
          - **RAW format protection** - prevents corruption of TIFF-based files
          - **Comprehensive safety modes** for different use cases
          - **JSON metadata synchronization** after extension fixes
        - ##### **Enhanced Data Processing**
          - **MediaEntity immutable models** for thread-safe operations
          - **Coordinate processing** with validation and conversion
          - **JSON metadata matching** with truncated filename support
          - **Album relationship management** with shortcut strategies
        - ##### **Bug Fixes & Stability**
          - **Race condition elimination** in concurrent operations
          - **JSON file matching improvements** for truncated names
          - **Memory leak prevention** in long-running processes
          - **Cross-platform filename handling** improvements
        - ##### **Eight-Step Pipeline Architecture**
          1. **Extension Fixing** - Intelligent MIME type correction
          2. **Media Discovery** - Optimized file system scanning
          3. **Duplicate Removal** - Content-based deduplication
          4. **Date Extraction** - Multi-source timestamp resolution
          5. **EXIF Writing** - Metadata synchronization
          6. **Album Detection** - Smart folder classification
          7. **File Moving** - Strategy-based organization
          8. **Creation Time Updates** - Final timestamp alignment
        
  - #### 🐛 Bug fixes:
    - [x] Fixed LOG_LEVEL change in `Google Takeout Processing Feature`.
    - [x] Fixed a bug setting lovLevel because it wasn't read from GlobalVariables in set_log_level() function.

  - #### 📚 Documentation:
    - [x] Updated documentation with all changes.
    
---

## Release: v4.0.0 
- ### Release Date   : (estimated)
  - Alpha version    : (No estimated date)
  - Beta version     : (No estimated date)
  - Release Candidate: (No estimated date)
  - Official Release : (No estimated date)

- ### TODO:
  - #### 🌟 New Features:
    - [ ] Include Apple Support (initially just for downloading)
        - [ ] Create Class ClassApplePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Include native support for Google Photos through API  
      (See [this link](https://max-coding.medium.com/loading-photos-and-metadata-using-google-photos-api-with-python-7fb5bd8886ef))
        - [ ] Create Class ClassGooglePhotos with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Include Nextcloud Support (initially just for downloading)
        - [ ] Create Class ClassNextCloud with the same methods and behaviour as ClassSynologyPhotos or ClassImmichPhotos. (volunteers are welcomed)
    - [ ] Allow Google Photos and Apple Photos as TARGET in AUTOMATIC-MODE
    - [ ] Include Test Cases to check all features
    - [ ] Add Github Action to execute all Test Cases

