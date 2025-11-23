# Project notes


## Project Overview

PhotoMigrator is a multi-platform Python CLI tool for migrating photos and videos between different cloud photo services (Google Takeout, Synology Photos, Immich Photos, Apple Photos, NextCloud). The tool can also fix metadata from Google Takeout exports by embedding EXIF data from sidecar JSON files.

## Development Commands

### Setup and Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install as editable package (allows running 'photomigrator' command)
pip install -e .
```

### Running the Tool

```bash
# From source
python src/PhotoMigrator.py [args]

# After pip install -e .
photomigrator [args]
```

### Testing

```bash
# Run all tests
python -m unittest

# Run specific test file
python -m unittest tests/test_automatic_migration.py
```

### Building Binaries

```bash
# Build platform-specific binary using pyinstaller/nuitka
python build-binary.py
```

## Architecture Overview

### Entry Point and Initialization Sequence

The tool follows a strict initialization order defined in `src/PhotoMigrator.py:PhotoMigrator()`:

1. **Parse arguments** - `set_ARGS_PARSER()` must be called first
2. **Set global variables** - `set_GLOBAL_VARIABLES()` depends on parsed args
3. **Initialize logger** - `set_LOGGER()` depends on global variables
4. **Set help texts** - `set_HELP_TEXTS()`

**CRITICAL**: Do NOT import tool modules (except `Utils.StandaloneUtils` or `Core.GlobalVariables`) before this initialization completes, or global variables (ARGS, PARSER, LOGGER, HELP_TEXTS) will be None.

### Core Module Structure

```
src/
├── PhotoMigrator.py           # Main entry point
├── Core/                      # Core infrastructure
│   ├── ArgsParser.py          # CLI argument parsing
│   ├── GlobalVariables.py     # Global state and constants
│   ├── GlobalFunctions.py     # Global initialization functions
│   ├── ExecutionModes.py      # Mode detection and routing
│   ├── CustomLogger.py        # Logging infrastructure
│   ├── ConfigReader.py        # Config.ini parsing
│   └── DataModels.py          # Data structures
├── Features/                  # Feature implementations
│   ├── AutomaticMigration/    # Cross-service migration
│   ├── GoogleTakeout/         # Google Takeout processing
│   ├── SynologyPhotos/        # Synology Photos client
│   ├── ImmichPhotos/          # Immich Photos client
│   ├── LocalFolder/           # Local folder operations
│   └── StandAloneFeatures/    # Utility features
└── Utils/                     # Utility functions
    ├── FileUtils.py
    ├── DateUtils.py
    └── GeneralUtils.py
```

### Execution Mode Routing

The tool uses `ExecutionModes.py:detect_and_run_execution_mode()` to route based on CLI arguments:

- **Automatic Migration**: When both `-source` and `-target` are provided
- **Google Takeout**: When `-gTakeout/--google-takeout` is used
- **Cloud Upload/Download**: `-upload-albums`, `-download-all`, etc.
- **Cloud Management**: `-remove-albums`, `-rename-albums`, etc.

### Feature Class Pattern

Photo service clients follow a class-based pattern:

- `ClassSynologyPhotos` - Synology Photos API client
- `ClassImmichPhotos` - Immich Photos API client
- `ClassTakeoutFolder` / `ClassLocalFolder` - Local folder handlers

Each class handles authentication, API operations, and asset management for its service.

### Configuration System

`Config.ini` stores connection credentials for different services:

```ini
[Synology Photos]
SYNOLOGY_URL = http://192.168.1.11:5000
SYNOLOGY_USERNAME_1 = user1
SYNOLOGY_PASSWORD_1 = pass1

[Immich Photos]
IMMICH_URL = http://192.168.1.11:2283
IMMICH_API_KEY_USER_1 = key1
```

The tool supports multiple accounts per service (suffix _1, _2, _3), selected via `-id/--account-id` argument.

## Important Implementation Notes

### Global Variable Management

- Global variables are initialized in `GlobalFunctions.py` via setter functions
- ARGS, PARSER, LOGGER are populated during startup in specific order
- Custom logging levels include VERBOSE (5) below DEBUG (10)

### Path Handling

- Tool changes working directory to script location via `change_working_dir()`
- External paths (from args) are resolved via `resolve_external_path()`
- All paths should use `pathlib.Path` or `normalize_path()` for cross-platform compatibility

### Logging System

- Custom logger with in-memory handler for dashboard updates
- Log levels: VERBOSE (5), DEBUG (10), INFO (20), WARNING (30), ERROR (40), CRITICAL (50)
- Two output functions:
  - `custom_print()` - Always prints to console
  - `custom_log()` - Respects log level, writes to file

### Testing

- Test configuration in `tests/conftest.py` adds `src/` to Python path
- Test utilities in `tests/utils.py`
- Test data preparation via `tests/prepare_test_data.py`

## Common Patterns

### Adding a New Execution Mode

1. Add CLI argument in `ArgsParser.py:parse_arguments()`
2. Add mode detection logic in `ExecutionModes.py:detect_and_run_execution_mode()`
3. Implement mode function (prefix with `mode_`) in ExecutionModes.py or dedicated module
4. Update help text in `HelpTexts.py` if needed

### Adding a New Photo Service Client

1. Create class in `src/Features/[ServiceName]/Class[ServiceName].py`
2. Implement authentication, asset upload/download, album management
3. Add config section to `Config.ini`
4. Add service to choices in `ArgsParser.py`
5. Add integration to AutomaticMigration if applicable

### Working with EXIF Data

- Tool uses `piexif` for EXIF manipulation
- ExifTool is embedded (accessed via `--exec-exif-tool`)
- Date extraction utilities in `Utils/DateUtils.py`

## Project-Specific Conventions

- Function names use snake_case
- Class names use PascalCase with "Class" prefix (e.g., `ClassImmichPhotos`)
- Mode functions prefixed with `mode_` (e.g., `mode_AUTOMATIC_MIGRATION`)
- Folder name constants use UPPERCASE (e.g., `FOLDERNAME_LOGS`)
- Tool uses colorama for cross-platform colored output
- Progress bars via tqdm, interactive elements via rich

## Key Dependencies

- `requests` - HTTP API calls to photo services
- `piexif` - EXIF metadata manipulation
- `tqdm` - Progress bars
- `rich` - Dashboard and formatted output
- `pillow` - Image processing
- `python-dateutil` - Date parsing
- `pyinstaller`/`nuitka` - Binary compilation

## Known Constraints

- Requires Python 3.7+
- Google Takeout GPTH processing is embedded (see `gpth_tool/`)
- Tkinter UI is disabled by default, configurable
- Windows-specific: uses windows-curses for terminal on AMD64
- Platform-specific splash screens for compiled binaries (PyInstaller/Nuitka)
