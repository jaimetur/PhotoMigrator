@echo off
setlocal enabledelayedexpansion

REM Load variables from .env file
set "RELEASE_TAG=latest"

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="RELEASE_TAG" (
        set "RELEASE_TAG=%%B"
    )
)

REM Get the current directory
set CURRENT_DIR=%cd%

echo 🐳 Pulling Docker image: jaimetur/cloudphotomigrator:%RELEASE_TAG%
docker pull jaimetur/cloudphotomigrator:%RELEASE_TAG%

echo 🚀 Launching container with tag: %RELEASE_TAG%
docker run -it --rm ^
  -v "%CURRENT_DIR%":/data ^
  jaimetur/cloudphotomigrator:%RELEASE_TAG% %*