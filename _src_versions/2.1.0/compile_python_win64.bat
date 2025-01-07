@echo off
cls

setlocal enabledelayedexpansion

REM Variables
set "SCRIPT_NAME=OrganizeTakeoutPhotos"
set "PLATTFORM=win64"
set "SCRIPT_ORIGINAL=%SCRIPT_NAME%.py"
set "SCRIPT_COMPILED=%SCRIPT_NAME%.exe"

REM Initialize SCRIPT_VERSION
set "SCRIPT_VERSION="

    REM Debug: Read SCRIPT_VERSION from the file
    for /f "tokens=*" %%A in ('findstr "SCRIPT_VERSION" "%SCRIPT_ORIGINAL%" ^| findstr /v "SCRIPT_NAME_VERSION"') do (
        echo Found line: %%A
        REM Remove excess spaces and extract the value after "="
        for /f "tokens=1,* delims==" %%B in ("%%A") do (
            set "RAW_VERSION=%%~C"
            REM echo Raw version before cleaning: !RAW_VERSION!
            REM Trim spaces and quotes
            for /f "tokens=* delims= " %%D in ("!RAW_VERSION!") do set "SCRIPT_VERSION=%%~D"
            set "SCRIPT_VERSION=!SCRIPT_VERSION:"=!"
        )
    )
    REM Debug: Check what SCRIPT_VERSION contains
    echo Final SCRIPT_VERSION extracted: "%SCRIPT_VERSION%"
    echo SCRIPT_VERSION found: %SCRIPT_VERSION%
    )

set "SCRIPT_NAME_VERSION=%SCRIPT_NAME%_%SCRIPT_VERSION%"
set "SCRIPT_ZIP_FILE=..\_built_versions\%SCRIPT_NAME_VERSION%_%PLATTFORM%.zip"

REM Clean up previous build artifacts
echo Cleaning up previous build artifacts...
del "%SCRIPT_NAME%.spec" /q 2>nul
rmdir "build" /s /q 2>nul
rmdir "dist" /s /q 2>nul

REM Compile Python script to executable
echo Compiling the script %SCRIPT_ORIGINAL% to %SCRIPT_COMPILED%...
pip install -r requirements.txt
set COMMAND=--onefile --hidden-import os,sys,tqdm,argparse,platform,shutil,re,textwrap,logging,collections,csv,time,datetime,hashlib,fnmatch,requests,urllib3 --add-data ..\gpth_tool_%PLATTFORM%;gpth_tool --add-data ..\exif_tool_%PLATTFORM%;exif_tool %SCRIPT_ORIGINAL%
echo pyinstaller %COMMAND%
pyinstaller %COMMAND%
move "dist\%SCRIPT_NAME%.exe" "..\%SCRIPT_COMPILED%"

if errorlevel 1 (
    echo Error occurred during compilation.
    exit /b 1
)

REM Create zip file for the compiled executable
echo Compressing compiled script "%SCRIPT_COMPILED%" to "%SCRIPT_ZIP_FILE%"...
mkdir "%SCRIPT_NAME_VERSION%" 2>nul
mkdir "%SCRIPT_NAME_VERSION%\Zip_files" 2>nul
copy "..\%SCRIPT_COMPILED%" "%SCRIPT_NAME_VERSION%\" /y >nul
copy "nas.config" "%SCRIPT_NAME_VERSION%\" /y >nul
copy "README.md" "%SCRIPT_NAME_VERSION%\" /y >nul

REM Using built-in Windows compression
powershell Compress-Archive -Path "%SCRIPT_NAME_VERSION%" -DestinationPath "%SCRIPT_ZIP_FILE%" -Force

if errorlevel 1 (
    echo Error occurred during compression.
    exit /b 1
)

REM Clean up temporary files
echo Cleaning up temporary files...
del "%SCRIPT_NAME%.spec" /q 2>nul
rmdir "build" /s /q 2>nul
rmdir "dist" /s /q 2>nul
rmdir %SCRIPT_NAME_VERSION% /s /q 2>nul

echo.
echo Compilation completed successfully.
echo Compiled script  : %SCRIPT_COMPILED%
echo Compressed script: %SCRIPT_ZIP_FILE%
echo.
exit /b 0
